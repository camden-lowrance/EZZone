"""
API blueprints for ezzone Flask application.

This module provides pure JSON API endpoints for the Vue SPA frontend.
"""

from __future__ import annotations

import json
import os
import uuid

import numpy as np
import pandas as pd
from flask import (
    Blueprint,
    request,
    Response,
    jsonify,
    session,
    current_app,
)
from werkzeug.utils import secure_filename

from src.zones import (
    generate_zones,
    simplify_zones,
    compute_gvf,
    export_zones,
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def allowed_file(filename: str) -> bool:
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def _parse_column(df: pd.DataFrame, col_name: str) -> np.ndarray:
    """Parse a DataFrame column to numeric array."""
    if df[col_name].dtype != 'float64':
        return pd.to_numeric(
            df[col_name].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).values
    return df[col_name].values


# ==================== Session Management ====================

@api_bp.route('/session/init', methods=['POST'])
def init_session():
    """
    Initialize a new session with uploaded data.
    
    Request JSON:
        {
            "file": file (multipart),
            "columns": {"x": "X", "y": "Y", "z": "Z"},
            "epsg": "4326",
            "field_type": 1,
            "units": "m",
            "row_spacing": 100,
            "pivot_spacing": 50,    // for VRI
            "pivot_length": 500     // for VRI
        }
    
    Returns:
        JSON with session_id and initial boundary for drawing
    """
    session_id = str(uuid.uuid4())
    session['sid'] = session_id
    
    test_file = os.path.join(current_app.root_path, 'static/test.csv')
    
    file = request.files.get('file')
    columns = request.json.get('columns', {}) if request.is_json else {}
    
    # Parse X, Y, Z column names
    x_col = columns.get('x', 'X')
    y_col = columns.get('y', 'Y')
    z_col = columns.get('z', 'Z')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            df = pd.read_csv(filepath, sep=None, engine='python')
        except Exception:
            try:
                df = pd.read_csv(filepath)
            except Exception:
                os.remove(filepath)
                return jsonify({'error': 'Could not parse CSV file'}), 400
        
        os.remove(filepath)
        
        x = _parse_column(df, x_col)
        y = _parse_column(df, y_col)
        z = _parse_column(df, z_col)
    else:
        # Use test data
        x, y, z = np.loadtxt(test_file, skiprows=1, delimiter=",", unpack=True)
    
    # Get parameters from request
    if request.is_json:
        data = request.json
    else:
        data = request.form.to_dict()
    
    epsg = data.get('epsg', '4326')
    field_type = int(data.get('field_type', 1))
    units = data.get('units', 'm')
    in_projection = f'epsg:{epsg}'
    
    factor = 0.3048 if units == 'f' else 1
    
    # Store in session
    session['x'] = x.tolist()
    session['y'] = y.tolist()
    session['z'] = z.tolist()
    session['inp'] = in_projection
    session['field_type'] = field_type
    
    # Field-specific parameters
    if field_type == 1 or field_type == 3:
        row_spacing = float(data.get('row_spacing', 100)) * factor
        session['row_spacing'] = row_spacing
        session['pivot_spacing'] = None
        session['pivot_length'] = None
    elif field_type == 2:
        pivot_spacing = float(data.get('pivot_spacing', 50)) * factor
        pivot_length = float(data.get('pivot_length', 500)) * factor
        session['pivot_spacing'] = pivot_spacing
        session['pivot_length'] = pivot_length
        session['row_spacing'] = None
    
    # Generate initial boundary for display
    try:
        result = generate_zones(
            x, y, z, field_type, in_projection,
            row_spacing=session.get('row_spacing'),
            pivot_spacing=session.get('pivot_spacing'),
            pivot_length=session.get('pivot_length'),
            num_classes=3
        )
        return jsonify({
            'session_id': session_id,
            'boundary': result['boundary'],
            'field_type': field_type,
            'grid_stats': result['grid_stats']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Zone Generation ====================

@api_bp.route('/zones/generate', methods=['POST'])
def create_zones():
    """
    Generate zones with boundary drawn by user.
    
    Request JSON:
        {
            "boundary_geojson": {...},
            "num_classes": 10
        }
    
    Returns:
        JSON with zones, gvf, class_breaks for chart display
    """
    x = np.array(session.get('x', []))
    y = np.array(session.get('y', []))
    z = np.array(session.get('z', []))
    inp = session.get('inp')
    field_type = session.get('field_type')
    
    if request.is_json:
        data = request.json
    else:
        data = request.form.to_dict()
    
    boundary_geojson = data.get('boundary_geojson')
    num_classes = int(data.get('num_classes', 10))
    
    # Get field-specific parameters
    if field_type == 1:
        row_spacing = session.get('row_spacing')
        result = generate_zones(
            x, y, z,
            field_type=field_type,
            in_projection=inp,
            row_spacing=row_spacing,
            boundary_geojson=boundary_geojson,
            num_classes=num_classes
        )
    elif field_type == 2:
        pivot_spacing = session.get('pivot_spacing')
        pivot_length = session.get('pivot_length')
        result = generate_zones(
            x, y, z,
            field_type=field_type,
            in_projection=inp,
            pivot_spacing=pivot_spacing,
            pivot_length=pivot_length,
            boundary_geojson=boundary_geojson,
            num_classes=num_classes
        )
    else:
        row_spacing = session.get('row_spacing')
        result = generate_zones(
            x, y, z,
            field_type=field_type,
            in_projection=inp,
            row_spacing=row_spacing,
            boundary_geojson=boundary_geojson,
            num_classes=num_classes
        )
    
    # Store result in session for later use
    session['result'] = {
        'zones': result['zones'],
        'gvf': result['gvf'],
        'class_breaks': result['class_breaks'],
        'row_spacing': result['grid_stats']['row_spacing']
    }
    
    return jsonify({
        'zones': result['zones'],
        'gvf': result['gvf'],
        'class_breaks': result['class_breaks'],
        'legend': result.get('legend'),
        'cmap_def': result.get('cmap_def')
    })


@api_bp.route('/zones/finalize', methods=['POST'])
def finalize_zones():
    """
    Create final zones with selected number of classes.
    
    Request JSON:
        {
            "num_classes": 3
        }
    
    Returns:
        JSON with final zones, legend, color maps
    """
    if request.is_json:
        data = request.json
    else:
        data = request.form.to_dict()
    
    num_classes = int(data.get('num_classes', 3))
    
    x = np.array(session.get('x', []))
    y = np.array(session.get('y', []))
    z = np.array(session.get('z', []))
    inp = session.get('inp')
    field_type = session.get('field_type')
    
    # Get field-specific parameters
    if field_type == 1:
        row_spacing = session.get('row_spacing')
        final_result = generate_zones(
            x, y, z, field_type, inp,
            row_spacing=row_spacing,
            num_classes=num_classes
        )
    elif field_type == 2:
        pivot_spacing = session.get('pivot_spacing')
        pivot_length = session.get('pivot_length')
        final_result = generate_zones(
            x, y, z, field_type, inp,
            pivot_spacing=pivot_spacing,
            pivot_length=pivot_length,
            num_classes=num_classes
        )
    else:
        row_spacing = session.get('row_spacing')
        final_result = generate_zones(
            x, y, z, field_type, inp,
            row_spacing=row_spacing,
            num_classes=num_classes
        )
    
    # Update session
    session['result'] = {
        'zones': final_result['zones'],
        'gvf': session.get('result', {}).get('gvf', []),
        'class_breaks': final_result['class_breaks'],
        'row_spacing': final_result['grid_stats']['row_spacing']
    }
    
    return jsonify({
        'zones': final_result['zones'],
        'class_breaks': final_result['class_breaks'],
        'legend': final_result['legend'],
        'cmap_def': final_result['cmap_def'],
        'cmap_sel': final_result['cmap_sel']
    })


# ==================== GVF Computation ====================

@api_bp.route('/zones/gvf', methods=['POST'])
def api_compute_gvf():
    """
    Compute GVF values for analysis.
    
    Request JSON:
        {
            "x": [...],
            "y": [...],
            "z": [...],
            "field_type": 1,
            "in_projection": "epsg:4326",
            "row_spacing": 100
        }
    
    Returns:
        JSON with GVF array
    """
    data = request.get_json()
    
    x = np.array(data.get('x', []))
    y = np.array(data.get('y', []))
    z = np.array(data.get('z', []))
    
    try:
        gvf = compute_gvf(
            x=x,
            y=y,
            z=z,
            field_type=data.get('field_type', 1),
            in_projection=data.get('in_projection', 'epsg:4326'),
            row_spacing=data.get('row_spacing', 100)
        )
        return jsonify({'gvf': gvf})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'GVF computation failed: {str(e)}'}), 500


# ==================== Zone Simplification ====================

@api_bp.route('/zones/simplify', methods=['POST'])
def api_simplify_zones():
    """
    Simplify zones.
    
    Request JSON:
        {
            "smooth": 1-10
        }
    
    Returns:
        JSON with simplified GeoJSON
    """
    result = session.get('result', {})
    zones = result.get('zones', {})
    row_spacing = result.get('row_spacing', 0)
    
    if request.is_json:
        data = request.json
    else:
        data = request.form.to_dict()
    
    smooth = int(data.get('smooth', 1))
    
    try:
        simplified = simplify_zones(zones, row_spacing, smooth)
        # Update session
        session['result']['zones'] = simplified
        return jsonify({'zones': simplified})
    except Exception as e:
        return jsonify({'error': f'Simplification failed: {str(e)}'}), 500


# ==================== Export ====================

@api_bp.route('/export', methods=['POST'])
def api_export():
    """
    Export zones to file.
    
    Request JSON:
        {
            "format": "geojson" | "shapefile"
        }
    
    Returns:
        File download response
    """
    result = session.get('result', {})
    zones = result.get('zones', {})
    
    if request.is_json:
        data = request.json
    else:
        data = request.form.to_dict()
    
    format_type = data.get('format', 'geojson')
    
    try:
        if format_type == 'geojson':
            return Response(
                json.dumps(zones),
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment;filename=zones.geojson'}
            )
        else:
            export_data = export_zones(zones, format='shapefile')
            return Response(
                export_data,
                mimetype='application/zip',
                headers={'Content-Disposition': 'attachment;filename=zones.zip'}
            )
    except Exception as e:
        return Response(f'Export failed: {str(e)}', status=500)


# ==================== Health Check ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})
