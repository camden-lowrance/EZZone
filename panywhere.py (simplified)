"""
Flask app for generating agricultural management zones.
Thin wrapper around mz_api - the core algorithm is decoupled.
"""

from flask import render_template, request, Response, Flask, jsonify, session
from werkzeug.utils import secure_filename
import mz_api
import numpy as np
import pandas as pd
import os
import uuid
import io
import json as json_mod
import zipfile
import tempfile

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
TEST_FILE = os.path.join(APP_ROOT, 'static/test.csv')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'csv'}
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-in-production')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return render_template('index2.html')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
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
        # Demo mode - use static/test.csv
        x, y, z = np.loadtxt(TEST_FILE, skiprows=1, delimiter=",", unpack=True)
    
    inp = 'epsg:' + str(request.form['coord'])
    field_type = int(request.form['field'])
    unit_type = request.form['units']
    
    # Convert units if needed
    if unit_type == 'f':
        factor = 0.3048
    else:
        factor = 1
    
    # Store in session for subsequent steps
    session['x'] = x.tolist()
    session['y'] = y.tolist()
    session['z'] = z.tolist()
    session['inp'] = inp
    session['field_type'] = field_type
    
    # Handle field-type specific parameters
    if field_type == 1:
        try:
            row_spacing = float(request.form['row']) * factor
        except ValueError:
            return render_template('badParam.html')
        session['row_spacing'] = row_spacing
        session['pivot_spacing'] = None
        session['pivot_length'] = None
        
        try:
            json_bound = mz_api.generate_zones(x, y, z, field_type, inp, row_spacing=row_spacing, num_classes=3)
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
            json_bound = mz_api.generate_zones(x, y, z, field_type, inp, pivot_spacing=pivot_spacing, pivot_length=pivot_length, num_classes=3)
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
            json_bound = mz_api.generate_zones(x, y, z, field_type, inp, row_spacing=row_spacing, num_classes=3)
            boundary = json_bound['boundary']
        except RuntimeError:
            return render_template('badEpsg.html')
        
        return render_template('irreg.html', string=boundary)
    
    return render_template('badFile.html')


def _parse_column(df, col_name):
    """Parse a DataFrame column to numeric array."""
    if df[col_name].dtype != 'float64':
        return pd.to_numeric(df[col_name].astype(str).str.replace(',', '.'), errors='coerce').values
    return df[col_name].values


@app.route('/createRect', methods=['POST'])
def createRect():
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
        num_classes=10  # Get max for GVF chart
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
def createVri():
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
        'row_spacing': 0  # VRI uses pivot spacing
    }
    
    gvf_json = json_mod.dumps(result['gvf'])
    return render_template('chart.html', string=gvf_json)


@app.route('/createIrreg', methods=['POST'])
def createIrreg():
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
def createZones():
    result = session['result']
    classes = int(request.form['classes'])
    
    # Regenerate with selected number of classes
    x = np.array(session['x'])
    y = np.array(session['y'])
    z = np.array(session['z'])
    inp = session['inp']
    field_type = session['field_type']
    
    if field_type == 1:
        row_spacing = session['row_spacing']
        final_result = mz_api.generate_zones(x, y, z, field_type, inp, row_spacing=row_spacing, num_classes=classes)
    elif field_type == 2:
        pivot_spacing = session['pivot_spacing']
        pivot_length = session['pivot_length']
        final_result = mz_api.generate_zones(x, y, z, field_type, inp, pivot_spacing=pivot_spacing, pivot_length=pivot_length, num_classes=classes)
    else:
        row_spacing = session['row_spacing']
        final_result = mz_api.generate_zones(x, y, z, field_type, inp, row_spacing=row_spacing, num_classes=classes)
    
    session['result']['zones'] = final_result['zones']
    session['result']['class_breaks'] = final_result['class_breaks']
    
    return render_template('displayZones.html', 
                           string={1: final_result['zones']},
                           cmap_def=final_result['cmap_def'],
                           cmap_sel=final_result['cmap_sel'],
                           legend=final_result['legend'],
                           field_type=field_type)


@app.route('/sendFile', methods=['POST'])
def sendFile():
    result = session['result']
    zones = result['zones']
    
    if request.form['filetype'] == "Save as GeoJSON":
        return Response(json_mod.dumps(zones),
                        mimetype='application/json',
                        headers={'Content-Disposition': 'attachment;filename=zones.geojson'})
    
    # Export as Shapefile
    data = mz_api.export_zones(zones, format='shapefile')
    return Response(data,
                    mimetype='application/zip',
                    headers={'Content-Disposition': 'attachment;filename=zones.zip'})


@app.route('/simplify', methods=['GET'])
def simplify_polys():
    result = session['result']
    zones = result['zones']
    row_spacing = result['row_spacing']
    smooth = request.args.get('smooth', 1, type=int)
    
    simplified = mz_api.simplify_zones(zones, row_spacing, smooth)
    return jsonify(result=simplified)


if __name__ == '__main__':
    app.run(debug=True)
