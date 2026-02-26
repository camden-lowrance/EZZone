"""
Truly stateless Universal Vector API.
"""

from __future__ import annotations
import json
import os
import uuid
import numpy as np
from flask import Blueprint, request, Response, jsonify, current_app
from werkzeug.utils import secure_filename
from diskcache import Cache
from .zones import generate_zones, export_zones
from .io_service import load_to_gdf

api_bp = Blueprint('api', __name__, url_prefix='/api')

def get_cache():
    return Cache(current_app.config['CACHE_FOLDER'])

@api_bp.route('/session/init', methods=['POST'])
def init_session():
    """Initialize session with any supported file."""
    file = request.files.get('file')
    z_col_req = request.form.get('z_column')
    crs_override = request.form.get('crs') or None

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            gdf, z_col = load_to_gdf(filepath, z_col_req, crs_override=crs_override)
            in_projection = f"epsg:{gdf.crs.to_epsg()}" if gdf.crs.to_epsg() else gdf.crs.to_string()
            x, y, z = gdf.geometry.x.values, gdf.geometry.y.values, gdf[z_col].values
            all_cols = gdf.columns.tolist()
            if 'geometry' in all_cols: all_cols.remove('geometry')
            numeric_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
            preview_data = gdf[all_cols].head(5).to_dict(orient='records')
        except Exception as e:
            return jsonify({'error': str(e)}), 400
        finally:
            if not current_app.config.get('TESTING') and os.path.exists(filepath):
                os.remove(filepath)
    else:
        # Sample data
        test_file = os.path.join(current_app.root_path, '..', '..', 'tests', 'fixtures', 'scott_harvest_2023.geojson')
        gdf, z_col = load_to_gdf(test_file, z_col_req)
        in_projection = 'epsg:4326'
        x, y, z = gdf.geometry.x.values, gdf.geometry.y.values, gdf[z_col].values
        all_cols = gdf.columns.tolist()
        if 'geometry' in all_cols: all_cols.remove('geometry')
        numeric_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
        preview_data = gdf[all_cols].head(5).to_dict(orient='records')
    
    data_id = str(uuid.uuid4())
    with get_cache() as cache:
        cache.set(data_id, {'x': x, 'y': y, 'z': z, 'crs': in_projection}, expire=86400)
    
    res = generate_zones(x, y, z, in_projection=in_projection)
    return jsonify({
        'data_id': data_id,
        'boundary': res['boundary'],
        'grid_stats': res['grid_stats'],
        'detected_crs': in_projection,
        'detected_z': z_col,
        'all_columns': all_cols,
        'numeric_columns': numeric_cols,
        'preview_data': preview_data
    })

@api_bp.route('/zones/generate', methods=['POST'])
def generate():
    """Stateless zone generation."""
    data = request.json
    data_id = data.get('data_id')
    with get_cache() as cache:
        raw = cache.get(data_id)
    if not raw: return jsonify({'error': 'Data expired'}), 404
    
    res = generate_zones(
        raw['x'], raw['y'], raw['z'],
        in_projection=raw['crs'],
        boundary_geojson=data.get('boundary_geojson'),
        num_classes=int(data.get('num_classes', 3))
    )
    
    with get_cache() as cache:
        cache.set(f"zones_{data_id}", res['zones'], expire=3600)
    
    return jsonify({'zones': res['zones'], 'gvf': res['gvf'], 'class_breaks': res['class_breaks'], 'legend': res['legend']})

@api_bp.route('/export', methods=['POST'])
def api_export():
    data_id = request.json.get('data_id')
    with get_cache() as cache:
        zones = cache.get(f"zones_{data_id}")
    if not zones: return jsonify({'error': 'Expired'}), 404
    
    fmt = request.json.get('format', 'geojson')
    if fmt == 'geojson':
        return Response(json.dumps(zones), mimetype='application/json', headers={'Content-Disposition': 'attachment;filename=zones.geojson'})
    return Response(export_zones(zones, format='shapefile'), mimetype='application/zip', headers={'Content-Disposition': 'attachment;filename=zones.zip'})

@api_bp.route('/health', methods=['GET'])
def health(): return jsonify({'status': 'ok'})
