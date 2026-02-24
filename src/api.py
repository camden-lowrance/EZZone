"""
API blueprints for ezzone Flask application.

This module contains:
- main_bp: Routes for HTML page rendering
- api_bp: Routes for JSON API endpoints
"""

from __future__ import annotations

import io
import json
import os
import uuid
import zipfile
import tempfile

import numpy as np
import pandas as pd
from flask import (
    Blueprint,
    render_template,
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


main_bp = Blueprint('main', __name__)
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


# ==================== Main Routes ====================

@main_bp.route('/')
def index() -> str:
    """Render the main index page."""
    return render_template('index2.html')


@main_bp.route('/upload', methods=['POST', 'GET'])
def upload() -> str:
    """Handle file upload and initialize session with point data."""
    session['sid'] = str(uuid.uuid4())
    
    test_file = os.path.join(current_app.root_path, 'static/test.csv')
    
    fileup = request.files.get('file')
    if fileup and allowed_file(fileup.filename):
        filename = secure_filename(fileup.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        fileup.save(filepath)
        
        try:
            df = pd.read_csv(filepath, sep=None, engine='python')
        except Exception:
            try:
                df = pd.read_csv(filepath)
            except Exception:
                os.remove(filepath)
                return render_template('badFile.html')
        
        os.remove(filepath)
        
        x = _parse_column(df, request.form['X'])
        y = _parse_column(df, request.form['Y'])
        z = _parse_column(df, request.form['Z'])
    else:
        x, y, z = np.loadtxt(test_file, skiprows=1, delimiter=",", unpack=True)
    
    inp = f"epsg:{request.form['coord']}"
    field_type = int(request.form['field'])
    unit_type = request.form['units']
    
    factor = 0.3048 if unit_type == 'f' else 1
    
    session['x'] = x.tolist()
    session['y'] = y.tolist()
    session['z'] = z.tolist()
    session['inp'] = inp
    session['field_type'] = field_type
    
    if field_type == 1:
        try:
            row_spacing = float(request.form['row']) * factor
        except ValueError:
            return render_template('badParam.html')
        session['row_spacing'] = row_spacing
        session['pivot_spacing'] = None
        session['pivot_length'] = None
        
        try:
            json_bound = generate_zones(
                x, y, z, field_type, inp,
                row_spacing=row_spacing,
                num_classes=3
            )
            boundary = json_bound['boundary']
        except RuntimeError:
            return render_template('badEpsg.html')
        
        return render_template('rect.html', string=boundary)
    
    elif field_type == 2:
        try:
            pivot_spacing = float(request.form['spacing']) * factor
            pivot_length = float(request.form['length']) * factor
        except ValueError:
            return render_template('badParam.html')
        session['pivot_spacing'] = pivot_spacing
        session['pivot_length'] = pivot_length
        session['row_spacing'] = None
        
        try:
            json_bound = generate_zones(
                x, y, z, field_type, inp,
                pivot_spacing=pivot_spacing,
                pivot_length=pivot_length,
                num_classes=3
            )
            boundary = json_bound['boundary']
        except RuntimeError:
            return render_template('badEpsg.html')
        
        return render_template('vri.html', string=boundary)
    
    elif field_type == 3:
        try:
            row_spacing = float(request.form['row']) * factor
        except ValueError:
            return render_template('badParam.html')
        session['row_spacing'] = row_spacing
        session['pivot_spacing'] = None
        session['pivot_length'] = None
        
        try:
            json_bound = generate_zones(
                x, y, z, field_type, inp,
                row_spacing=row_spacing,
                num_classes=3
            )
            boundary = json_bound['boundary']
        except RuntimeError:
            return render_template('badEpsg.html')
        
        return render_template('irreg.html', string=boundary)
    
    return render_template('badFile.html')


@main_bp.route('/createRect', methods=['POST'])
def create_rect() -> str:
    """Create zones for rectangular field."""
    x = np.array(session.get('x', []))
    y = np.array(session.get('y', []))
    z = np.array(session.get('z', []))
    inp = session.get('inp')
    row_spacing = session.get('row_spacing')
    content = str(request.form.get('jsonval', '{}'))
    
    result = generate_zones(
        x, y, z,
        field_type=1,
        in_projection=inp,
        row_spacing=row_spacing,
        boundary_geojson=content,
        num_classes=10
    )
    
    session['result'] = {
        'zones': result['zones'],
        'gvf': result['gvf'],
        'class_breaks': result['class_breaks'],
        'row_spacing': result['grid_stats']['row_spacing']
    }
    
    gvf_json = json.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@main_bp.route('/createVri', methods=['POST'])
def create_vri() -> str:
    """Create zones for VRI (center-pivot) field."""
    x = np.array(session.get('x', []))
    y = np.array(session.get('y', []))
    z = np.array(session.get('z', []))
    inp = session.get('inp')
    pivot_spacing = session.get('pivot_spacing')
    pivot_length = session.get('pivot_length')
    content = str(request.form.get('jsonval', '{}'))
    
    result = generate_zones(
        x, y, z,
        field_type=2,
        in_projection=inp,
        pivot_spacing=pivot_spacing,
        pivot_length=pivot_length,
        boundary_geojson=content,
        num_classes=10
    )
    
    session['result'] = {
        'zones': result['zones'],
        'gvf': result['gvf'],
        'class_breaks': result['class_breaks'],
        'row_spacing': 0
    }
    
    gvf_json = json.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@main_bp.route('/createIrreg', methods=['POST'])
def create_irreg() -> str:
    """Create zones for irregular field."""
    x = np.array(session.get('x', []))
    y = np.array(session.get('y', []))
    z = np.array(session.get('z', []))
    inp = session.get('inp')
    row_spacing = session.get('row_spacing')
    content = str(request.form.get('jsonval', '{}'))
    
    result = generate_zones(
        x, y, z,
        field_type=3,
        in_projection=inp,
        row_spacing=row_spacing,
        boundary_geojson=content,
        num_classes=10
    )
    
    session['result'] = {
        'zones': result['zones'],
        'gvf': result['gvf'],
        'class_breaks': result['class_breaks'],
        'row_spacing': result['grid_stats']['row_spacing']
    }
    
    gvf_json = json.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@main_bp.route('/createZones', methods=['POST'])
def create_zones() -> str:
    """Create final zones with selected number of classes."""
    result = session.get('result', {})
    classes = int(request.form.get('classes', 3))
    
    x = np.array(session.get('x', []))
    y = np.array(session.get('y', []))
    z = np.array(session.get('z', []))
    inp = session.get('inp')
    field_type = session.get('field_type')
    
    if field_type == 1:
        row_spacing = session.get('row_spacing')
        final_result = generate_zones(
            x, y, z, field_type, inp,
            row_spacing=row_spacing,
            num_classes=classes
        )
    elif field_type == 2:
        pivot_spacing = session.get('pivot_spacing')
        pivot_length = session.get('pivot_length')
        final_result = generate_zones(
            x, y, z, field_type, inp,
            pivot_spacing=pivot_spacing,
            pivot_length=pivot_length,
            num_classes=classes
        )
    else:
        row_spacing = session.get('row_spacing')
        final_result = generate_zones(
            x, y, z, field_type, inp,
            row_spacing=row_spacing,
            num_classes=classes
        )
    
    session['result']['zones'] = final_result['zones']
    session['result']['class_breaks'] = final_result['class_breaks']
    
    return render_template(
        'displayZones.html',
        string={1: final_result['zones']},
        cmap_def=final_result['cmap_def'],
        cmap_sel=final_result['cmap_sel'],
        legend=final_result['legend'],
        field_type=field_type
    )


@main_bp.route('/sendFile', methods=['POST'])
def send_file() -> Response:
    """Export zones as GeoJSON or Shapefile."""
    result = session.get('result', {})
    zones = result.get('zones', {})
    
    if request.form.get('filetype') == "Save as GeoJSON":
        return Response(
            json.dumps(zones),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment;filename=zones.geojson'}
        )
    
    data = export_zones(zones, format='shapefile')
    return Response(
        data,
        mimetype='application/zip',
        headers={'Content-Disposition': 'attachment;filename=zones.zip'}
    )


@main_bp.route('/simplify', methods=['GET'])
def simplify_polys() -> dict:
    """Apply smoothing to zones."""
    result = session.get('result', {})
    zones = result.get('zones', {})
    row_spacing = result.get('row_spacing', 0)
    smooth = request.args.get('smooth', 1, type=int)
    
    simplified = simplify_zones(zones, row_spacing, smooth)
    return jsonify(result=simplified)


# ==================== JSON API Routes ====================

@api_bp.route('/zones', methods=['POST'])
def api_generate_zones() -> dict:
    """
    Generate zones via JSON API.
    
    Request JSON:
        {
            "x": [...],
            "y": [...],
            "z": [...],
            "field_type": 1,  // 1=rect, 2=VRI, 3=irreg
            "in_projection": "epsg:4326",
            "row_spacing": 100,      // for rect/irreg
            "pivot_spacing": 50,     // for VRI
            "pivot_length": 500,     // for VRI
            "boundary_geojson": {...}, // optional
            "num_classes": 3
        }
    
    Returns:
        JSON response with zones, gvf, class_breaks, boundary, legend, etc.
    """
    data = request.get_json()
    
    x = np.array(data.get('x', []))
    y = np.array(data.get('y', []))
    z = np.array(data.get('z', []))
    
    try:
        result = generate_zones(
            x=x,
            y=y,
            z=z,
            field_type=data.get('field_type', 1),
            in_projection=data.get('in_projection', 'epsg:4326'),
            row_spacing=data.get('row_spacing'),
            pivot_spacing=data.get('pivot_spacing'),
            pivot_length=data.get('pivot_length'),
            boundary_geojson=data.get('boundary_geojson'),
            num_classes=data.get('num_classes', 3)
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Zone generation failed: {str(e)}'}), 500


@api_bp.route('/zones/gvf', methods=['POST'])
def api_compute_gvf() -> dict:
    """
    Compute GVF values via JSON API.
    
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
        JSON response with GVF array.
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


@api_bp.route('/zones/simplify', methods=['POST'])
def api_simplify_zones() -> dict:
    """
    Simplify zones via JSON API.
    
    Request JSON:
        {
            "zones": {...},    // GeoJSON FeatureCollection
            "row_spacing": 100,
            "smooth": 1
        }
    
    Returns:
        JSON response with simplified GeoJSON.
    """
    data = request.get_json()
    
    zones = data.get('zones', {})
    row_spacing = data.get('row_spacing', 0)
    smooth = data.get('smooth', 1)
    
    try:
        simplified = simplify_zones(zones, row_spacing, smooth)
        return jsonify({'zones': simplified})
    except Exception as e:
        return jsonify({'error': f'Simplification failed: {str(e)}'}), 500


@api_bp.route('/zones/export', methods=['POST'])
def api_export_zones() -> Response:
    """
    Export zones via JSON API.
    
    Request JSON:
        {
            "zones": {...},    // GeoJSON FeatureCollection
            "format": "geojson" // or "shapefile"
        }
    
    Returns:
        File download response.
    """
    data = request.get_json()
    
    zones = data.get('zones', {})
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
    except ValueError as e:
        return Response(str(e), status=400)
    except Exception as e:
        return Response(f'Export failed: {str(e)}', status=500)
