"""
Flask app for generating agricultural management zones.
Thin wrapper around mz_api - the core algorithm is decoupled.
"""

from __future__ import annotations

import os
import uuid
import io
import json as json_mod
import zipfile
import tempfile

import numpy as np
import pandas as pd
from flask import (
    Flask,
    render_template,
    request,
    Response,
    jsonify,
    session
)
from werkzeug.utils import secure_filename

import mz_api


app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
TEST_FILE = os.path.join(APP_ROOT, 'static/test.csv')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'csv'}
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-in-production')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """
    Check if a filename has an allowed extension.

    Args:
        filename: The filename to check.

    Returns:
        True if the file extension is allowed, False otherwise.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index() -> str:
    """
    Render the main index page.

    Returns:
        Rendered HTML template.
    """
    return render_template('index2.html')


def _parse_column(df: pd.DataFrame, col_name: str) -> np.ndarray:
    """
    Parse a DataFrame column to numeric array.

    Args:
        df: Pandas DataFrame.
        col_name: Name of the column to parse.

    Returns:
        NumPy array of numeric values.
    """
    if df[col_name].dtype != 'float64':
        return pd.to_numeric(
            df[col_name].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).values
    return df[col_name].values


@app.route('/upload', methods=['POST', 'GET'])
def upload() -> str:
    """
    Handle file upload and initialize session with point data.

    Returns:
        Rendered template (rect.html, vri.html, irreg.html, or error template).
    """
    session['sid'] = str(uuid.uuid4())
    
    fileup = request.files['file']
    if fileup and allowed_file(fileup.filename):
        filename = secure_filename(fileup.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
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
        x, y, z = np.loadtxt(TEST_FILE, skiprows=1, delimiter=",", unpack=True)
    
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
            json_bound = mz_api.generate_zones(
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
            json_bound = mz_api.generate_zones(
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
            json_bound = mz_api.generate_zones(
                x, y, z, field_type, inp,
                row_spacing=row_spacing,
                num_classes=3
            )
            boundary = json_bound['boundary']
        except RuntimeError:
            return render_template('badEpsg.html')
        
        return render_template('irreg.html', string=boundary)
    
    return render_template('badFile.html')


@app.route('/createRect', methods=['POST'])
def createRect() -> str:
    """
    Create zones for rectangular field.

    Returns:
        Rendered chart.html template with GVF data.
    """
    x = np.array(session['x'])
    y = np.array(session['y'])
    z = np.array(session['z'])
    inp = session['inp']
    row_spacing = session['row_spacing']
    content = str(request.form['jsonval'])
    
    result = mz_api.generate_zones(
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
    
    gvf_json = json_mod.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@app.route('/createVri', methods=['POST'])
def createVri() -> str:
    """
    Create zones for VRI (center-pivot) field.

    Returns:
        Rendered chart.html template with GVF data.
    """
    x = np.array(session['x'])
    y = np.array(session['y'])
    z = np.array(session['z'])
    inp = session['inp']
    pivot_spacing = session['pivot_spacing']
    pivot_length = session['pivot_length']
    content = str(request.form['jsonval'])
    
    result = mz_api.generate_zones(
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
    
    gvf_json = json_mod.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@app.route('/createIrreg', methods=['POST'])
def createIrreg() -> str:
    """
    Create zones for irregular field.

    Returns:
        Rendered chart.html template with GVF data.
    """
    x = np.array(session['x'])
    y = np.array(session['y'])
    z = np.array(session['z'])
    inp = session['inp']
    row_spacing = session['row_spacing']
    content = str(request.form['jsonval'])
    
    result = mz_api.generate_zones(
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
    
    gvf_json = json_mod.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@app.route('/createZones', methods=['POST'])
def createZones() -> str:
    """
    Create final zones with selected number of classes.

    Returns:
        Rendered displayZones.html template.
    """
    result = session['result']
    classes = int(request.form['classes'])
    
    x = np.array(session['x'])
    y = np.array(session['y'])
    z = np.array(session['z'])
    inp = session['inp']
    field_type = session['field_type']
    
    if field_type == 1:
        row_spacing = session['row_spacing']
        final_result = mz_api.generate_zones(
            x, y, z, field_type, inp,
            row_spacing=row_spacing,
            num_classes=classes
        )
    elif field_type == 2:
        pivot_spacing = session['pivot_spacing']
        pivot_length = session['pivot_length']
        final_result = mz_api.generate_zones(
            x, y, z, field_type, inp,
            pivot_spacing=pivot_spacing,
            pivot_length=pivot_length,
            num_classes=classes
        )
    else:
        row_spacing = session['row_spacing']
        final_result = mz_api.generate_zones(
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


@app.route('/sendFile', methods=['POST'])
def sendFile() -> Response:
    """
    Export zones as GeoJSON or Shapefile.

    Returns:
        Flask Response with file download.
    """
    result = session['result']
    zones = result['zones']
    
    if request.form['filetype'] == "Save as GeoJSON":
        return Response(
            json_mod.dumps(zones),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment;filename=zones.geojson'}
        )
    
    data = mz_api.export_zones(zones, format='shapefile')
    return Response(
        data,
        mimetype='application/zip',
        headers={'Content-Disposition': 'attachment;filename=zones.zip'}
    )


@app.route('/simplify', methods=['GET'])
def simplify_polys() -> dict:
    """
    Apply smoothing to zones.

    Returns:
        JSON response with simplified zones.
    """
    result = session['result']
    zones = result['zones']
    row_spacing = result['row_spacing']
    smooth = request.args.get('smooth', 1, type=int)
    
    simplified = mz_api.simplify_zones(zones, row_spacing, smooth)
    return jsonify(result=simplified)


if __name__ == '__main__':
    app.run(debug=True)
