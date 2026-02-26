"""
Truly stateless Universal Vector API.
"""

from __future__ import annotations
import json
import os
import uuid
import numpy as np
from flask import Blueprint, request, Response, current_app
from werkzeug.utils import secure_filename
from diskcache import Cache
from .zones import generate_zones, export_zones
from .io_service import load_to_gdf, load_multiple_to_gdf, extract_zip_contents, DataError

api_bp = Blueprint('api', __name__, url_prefix='/api')

def get_cache():
    return Cache(current_app.config['CACHE_FOLDER'])

@api_bp.route('/session/init', methods=['POST'])
def init_session():
    """Initialize session with any supported file."""
    z_col_req = request.form.get('z_column')
    crs_override = request.form.get('crs') or None
    files = request.files.getlist('file')
    use_sample = request.form.get('use_sample') == '1'
    if files and files[0].filename:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        saved_paths = []
        tmpdir = None
        for f in files:
            filename = secure_filename(f.filename)
            filepath = os.path.join(upload_folder, filename)
            f.save(filepath)
            saved_paths.append(filepath)
        tmpdirs = []
        try:
            load_paths = []
            for p in saved_paths:
                if p.lower().endswith('.zip'):
                    shp_paths, td = extract_zip_contents(p)
                    if not shp_paths:
                        raise ValueError(f'No shapefiles found inside {os.path.basename(p)}.')
                    load_paths.extend(shp_paths)
                    tmpdirs.append(td)
                else:
                    load_paths.append(p)

            gdf, z_col = load_multiple_to_gdf(load_paths, z_col_req, crs_override=crs_override)
            in_projection = f"epsg:{gdf.crs.to_epsg()}" if gdf.crs.to_epsg() else gdf.crs.to_string()
            x, y, z = gdf.geometry.x.values, gdf.geometry.y.values, gdf[z_col].values
            all_cols = gdf.columns.tolist()
            if 'geometry' in all_cols: all_cols.remove('geometry')
            numeric_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
            preview_data = gdf[all_cols].head(5).to_dict(orient='records')
        except DataError as e:
            return e.to_json(), 422
        except Exception as e:
            return {'error': f'Unexpected error processing file: {e}', 'code': 'SERVER_ERROR'}, 500
        finally:
            if not current_app.config.get('TESTING'):
                for p in saved_paths:
                    if os.path.exists(p): os.remove(p)
            import shutil
            for td in tmpdirs:
                shutil.rmtree(td, ignore_errors=True)
    elif use_sample:
        # Sample data (only when explicitly requested)
        test_file = os.path.join(current_app.root_path, '..', '..', 'tests', 'fixtures', 'blount_harvest_agi.zip')
        shp_paths, tmpdir_sample = extract_zip_contents(test_file)
        try:
            gdf, z_col = load_multiple_to_gdf(shp_paths, z_col_req)
        finally:
            import shutil; shutil.rmtree(tmpdir_sample, ignore_errors=True)
        in_projection = 'epsg:4326'
        x, y, z = gdf.geometry.x.values, gdf.geometry.y.values, gdf[z_col].values
        all_cols = gdf.columns.tolist()
        if 'geometry' in all_cols: all_cols.remove('geometry')
        numeric_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
        preview_data = gdf[all_cols].head(5).to_dict(orient='records')
    else:
        return {'error': 'No valid files found in your upload. Please upload a supported vector file (Shapefile, GeoJSON, CSV, etc.).', 'code': 'NO_VALID_FILES'}, 400

    data_id = str(uuid.uuid4())
    with get_cache() as cache:
        cache.set(data_id, {'x': x, 'y': y, 'z': z, 'crs': in_projection}, expire=86400)
    
    res = generate_zones(x, y, z, in_projection=in_projection)
    return {
        'data_id': data_id,
        'boundary': res['boundary'],
        'grid_stats': res['grid_stats'],
        'detected_crs': in_projection,
        'detected_z': z_col,
        'all_columns': all_cols,
        'numeric_columns': numeric_cols,
        'preview_data': preview_data
    }

@api_bp.route('/zones/generate', methods=['POST'])
def generate():
    """Stateless zone generation."""
    data = request.json
    data_id = data.get('data_id')
    with get_cache() as cache:
        raw = cache.get(data_id)
    if not raw: return {'error': 'Session expired. Please re-upload your data.', 'code': 'SESSION_EXPIRED'}, 404
    
    res = generate_zones(
        raw['x'], raw['y'], raw['z'],
        in_projection=raw['crs'],
        boundary_geojson=data.get('boundary_geojson'),
        num_classes=int(data.get('num_classes', 3))
    )
    
    with get_cache() as cache:
        cache.set(f"zones_{data_id}", res['zones'], expire=3600)
    
    return {'zones': res['zones'], 'gvf': res['gvf'], 'class_breaks': res['class_breaks'], 'legend': res['legend']}

@api_bp.route('/export', methods=['POST'])
def api_export():
    data_id = request.json.get('data_id')
    with get_cache() as cache:
        zones = cache.get(f"zones_{data_id}")
    if not zones: return {'error': 'Session expired. Please re-upload your data.', 'code': 'SESSION_EXPIRED'}, 404
    
    fmt = request.json.get('format', 'geojson')
    if fmt == 'geojson':
        return Response(json.dumps(zones), mimetype='application/json', headers={'Content-Disposition': 'attachment;filename=zones.geojson'})
    return Response(export_zones(zones, format='shapefile'), mimetype='application/zip', headers={'Content-Disposition': 'attachment;filename=zones.zip'})

@api_bp.route('/health', methods=['GET'])
def health(): return {'status': 'ok'}
