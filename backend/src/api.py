"""
Truly stateless Universal Vector API.
"""

from __future__ import annotations
import json
import os
import shutil
import tempfile
import uuid
import numpy as np
from flask import Blueprint, request, Response, current_app
from werkzeug.utils import secure_filename
from diskcache import Cache
from .geo import get_active_profile
from .zones import generate_zones, export_zones, get_metadata
from .io_service import load_multiple_to_gdf, extract_zip_contents, DataError

api_bp = Blueprint('api', __name__, url_prefix='/api')

def get_cache():
    return Cache(current_app.config['CACHE_FOLDER'])

def _process_gdf_to_res(gdf, z_col_req):
    """Common logic to extract data from GDF and cache it."""
    # Identify Z column
    if z_col_req in gdf.columns:
        z_col = z_col_req
        if not np.issubdtype(gdf[z_col].dtype, np.number):
            import pandas as pd
            gdf[z_col] = pd.to_numeric(gdf[z_col].astype(str).str.replace(',', '.'), errors='coerce')
    else:
        from .io_service import _detect_z_col
        exclude_cols = [gdf.geometry.name] + getattr(gdf, '_coord_cols', [])
        z_col = _detect_z_col(gdf, exclude=exclude_cols)
    
    if not z_col or gdf[z_col].isna().all():
        raise DataError(f'No valid numeric data found in column "{z_col_req or z_col}".', 'MISSING_Z_COL')

    in_projection = f"epsg:{gdf.crs.to_epsg()}" if (gdf.crs and gdf.crs.to_epsg()) else (gdf.crs.to_string() if gdf.crs else 'epsg:4326')
    x, y, z = gdf.geometry.x.values, gdf.geometry.y.values, gdf[z_col].values
    geom_col = gdf.geometry.name
    all_cols = [c for c in gdf.columns.tolist() if c != geom_col]
    all_cols = list(dict.fromkeys(all_cols))
    numeric_cols = [c for c in gdf.select_dtypes(include=[np.number]).columns.tolist() if c != geom_col]
    preview_data = gdf[all_cols].head(5).to_dict(orient='records')

    data_id = str(uuid.uuid4())
    with get_cache() as cache:
        cache.set(data_id, {
            'x': x, 'y': y, 'z': z,
            'crs': in_projection,
            'z_col': z_col,
        }, expire=86400)
    
    meta = get_metadata(x, y, in_projection=in_projection)
    return {
        'data_id': data_id,
        'boundary': meta['boundary'],
        'num_points': meta['num_points'],
        'original_num_points': gdf.attrs.get('original_num_points', meta['num_points']),
        'points_used': min(meta['num_points'], get_active_profile()['max_points']),
        'detected_crs': in_projection,
        'is_crs_guessed': gdf.attrs.get('is_crs_guessed', False),
        'detected_z': z_col,
        'all_columns': all_cols,
        'numeric_columns': numeric_cols,
        'preview_data': preview_data
    }

@api_bp.route('/session/init', methods=['POST'])
def init_session():
    """Initialize per-upload cached data from any supported file."""
    z_col_req = request.form.get('z_column')
    crs_override = request.form.get('crs') or None
    files = request.files.getlist('file')
    use_sample = request.form.get('use_sample') == '1'

    # Case 1: New Upload
    if files and files[0].filename:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        request_upload_dir = tempfile.mkdtemp(prefix='upload_', dir=upload_folder)
        saved_paths = []
        tmpdirs = []
        try:
            for index, f in enumerate(files, start=1):
                filename = secure_filename(f.filename) or f'upload-{index}'
                filepath = os.path.join(request_upload_dir, filename)
                f.save(filepath)
                saved_paths.append(filepath)
            
            load_paths = []
            for p in saved_paths:
                if p.lower().endswith('.zip'):
                    shp_paths, td = extract_zip_contents(p)
                    load_paths.extend(shp_paths)
                    tmpdirs.append(td)
                else:
                    load_paths.append(p)

            gdf, _ = load_multiple_to_gdf(load_paths, z_col_req, crs_override=crs_override)
            return _process_gdf_to_res(gdf, z_col_req)
        except DataError as e:
            return e.to_json(), 422
        except Exception as e:
            return {'error': f'Unexpected error processing file: {e}', 'code': 'SERVER_ERROR'}, 500
        finally:
            shutil.rmtree(request_upload_dir, ignore_errors=True)
            for td in tmpdirs:
                shutil.rmtree(td, ignore_errors=True)
                
    # Case 2: Sample Data
    elif use_sample:
        test_file = os.path.join(current_app.root_path, '..', '..', 'tests', 'fixtures', 'test.csv')
        gdf, _ = load_multiple_to_gdf([test_file], z_col_req)
        return _process_gdf_to_res(gdf, z_col_req)
            
    return {'error': 'No valid files found in your upload.', 'code': 'NO_VALID_FILES'}, 400

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
        num_classes=int(data.get('num_classes', 3)),
        z_col=raw.get('z_col', 'value'),
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
