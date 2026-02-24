"""
Flask app for generating agricultural management zones from CSV point data.
Designed for PythonAnywhere hosting.
"""

from flask import render_template, request, Response, Flask, jsonify, session
from werkzeug.utils import secure_filename
import mz
import numpy as np
import pandas as pd
import geopandas as gpd
import os
import pickle
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


def _state_path():
    sid = session.get('sid')
    return os.path.join(UPLOAD_FOLDER, f'session_{sid}.pkl') if sid else None


def load_state():
    path = _state_path()
    if path and os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    return {}


def save_state(state):
    path = _state_path()
    if path:
        with open(path, 'wb') as f:
            pickle.dump(state, f)


@app.route('/')
def index():
    return render_template('index2.html')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    session['sid'] = str(uuid.uuid4())
    state = {}

    fileup = request.files['file']
    if fileup:
        if allowed_file(fileup.filename):
            filename = secure_filename(fileup.filename)
            filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            fileup.save(filename)
            try:
                file = pd.read_csv(filename, sep=None, engine='python')
            except Exception:
                try:
                    file = pd.read_csv(filename)
                except Exception:
                    return render_template('badFile.html')

            xcol = request.form['X']
            if file[xcol].dtype != 'float64':
                x = pd.to_numeric(file[xcol].astype(str).str.replace(',', '.'), errors='coerce')
            else:
                x = file[xcol]

            ycol = request.form['Y']
            if file[ycol].dtype != 'float64':
                y = pd.to_numeric(file[ycol].astype(str).str.replace(',', '.'), errors='coerce')
            else:
                y = file[ycol]

            zcol = request.form['Z']
            if file[zcol].dtype != 'float64':
                z = pd.to_numeric(file[zcol].astype(str).str.replace(',', '.'), errors='coerce')
            else:
                z = file[zcol]

            os.remove(filename)
            inp = 'epsg:' + str(request.form['coord'])
            field_type = int(request.form['field'])
            unit_type = request.form['units']
            print(unit_type)

            if field_type == 1:
                try:
                    row_spacing = float(request.form['row']) * (.3048 if unit_type == 'f' else 1)
                except ValueError:
                    return render_template('badParam.html')
                try:
                    json_bound = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
                except RuntimeError:
                    return render_template('badEpsg.html')
                state.update({'x': x, 'y': y, 'z': z, 'inp': inp, 'field_type': field_type,
                              'row_spacing': row_spacing})
                save_state(state)
                return render_template('rect.html', string=json_bound)

            if field_type == 2:
                try:
                    pivot_spacing = float(request.form['spacing']) * (.3048 if unit_type == 'f' else 1)
                except ValueError:
                    return render_template('badParam.html')
                try:
                    pivot_length = float(request.form['length']) * (.3048 if unit_type == 'f' else 1)
                except ValueError:
                    return render_template('badParam.html')
                try:
                    json_bound = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
                except RuntimeError:
                    return render_template('badEpsg.html')
                state.update({'x': x, 'y': y, 'z': z, 'inp': inp, 'field_type': field_type,
                              'pivot_spacing': pivot_spacing, 'pivot_length': pivot_length})
                save_state(state)
                return render_template('vri.html', string=json_bound)

            if field_type == 3:
                try:
                    row_spacing = float(request.form['row']) * (.3048 if unit_type == 'f' else 1)
                except ValueError:
                    return render_template('badParam.html')
                try:
                    json_bound = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
                except RuntimeError:
                    return render_template('badEpsg.html')
                state.update({'x': x, 'y': y, 'z': z, 'inp': inp, 'field_type': field_type,
                              'row_spacing': row_spacing})
                save_state(state)
                return render_template('irreg.html', string=json_bound)
        else:
            return render_template('badFile.html')

    # demo file
    x, y, z = np.loadtxt(TEST_FILE, skiprows=1, delimiter=",", unpack=True)
    inp = 'epsg:' + str(request.form['coord'])
    field_type = int(request.form['field'])
    unit_type = request.form['units']
    print(unit_type)

    if field_type == 1:
        try:
            row_spacing = float(request.form['row'])
        except ValueError:
            return render_template('badParam.html')
        try:
            json_bound = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
        except RuntimeError:
            return render_template('badEpsg.html')
        state.update({'x': x, 'y': y, 'z': z, 'inp': inp, 'field_type': field_type,
                      'row_spacing': row_spacing})
        save_state(state)
        return render_template('rect.html', string=json_bound)

    if field_type == 2:
        try:
            pivot_spacing = float(request.form['spacing'])
        except ValueError:
            return render_template('badParam.html')
        try:
            pivot_length = float(request.form['length'])
        except ValueError:
            return render_template('badParam.html')
        try:
            json_bound = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
        except RuntimeError:
            return render_template('badEpsg.html')
        state.update({'x': x, 'y': y, 'z': z, 'inp': inp, 'field_type': field_type,
                      'pivot_spacing': pivot_spacing, 'pivot_length': pivot_length})
        save_state(state)
        return render_template('vri.html', string=json_bound)

    if field_type == 3:
        try:
            row_spacing = float(request.form['row'])
        except ValueError:
            return render_template('badParam.html')
        try:
            json_bound = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
        except RuntimeError:
            return render_template('badEpsg.html')
        state.update({'x': x, 'y': y, 'z': z, 'inp': inp, 'field_type': field_type,
                      'row_spacing': row_spacing})
        save_state(state)
        return render_template('irreg.html', string=json_bound)


@app.route('/createRect', methods=['POST'])
def createRect():
    state = load_state()
    x, y, z = state['x'], state['y'], state['z']
    inp = state['inp']
    row_spacing = state['row_spacing']

    content = str(request.form['jsonval'])
    bound = mz.geojson_fc_parser(content, "Polygon")
    bound = mz.reproject_poly(obj=bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(obj=bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_rect(bound, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound, row_space)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats, 10)
    gvf_json = mz.gvf_json(gvf_arr)

    state.update({'utm_pyproj': utm_pyproj, 'row_space': row_space,
                  'poly_stats': poly_stats, 'polys2': polys2})
    save_state(state)
    return render_template('chart.html', string=gvf_json)


@app.route('/createVri', methods=['POST'])
def createVri():
    state = load_state()
    x, y, z = state['x'], state['y'], state['z']
    inp = state['inp']
    pivot_spacing = state['pivot_spacing']
    pivot_length = state['pivot_length']

    content = str(request.form['jsonval'])
    bound = mz.geojson_fc_parser(content, 'Polygon')
    point = mz.geojson_fc_parser(content, 'Point')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    point = mz.reproject_point(point)
    point = mz.reproject_point(obj=point, in_projection='epsg:4326', out_projection=utm_pyproj)
    polys = mz.grid_circ(pivot_spacing, pivot_length, point, bound)
    print('here')
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats, 10)
    gvf_json = mz.gvf_json(gvf_arr)

    # row_space=0 for VRI: simplification is a no-op (matches original behaviour)
    state.update({'utm_pyproj': utm_pyproj, 'row_space': 0,
                  'poly_stats': poly_stats, 'polys2': polys2})
    save_state(state)
    return render_template('chart.html', string=gvf_json)


@app.route('/createIrreg', methods=['POST'])
def createIrreg():
    state = load_state()
    x, y, z = state['x'], state['y'], state['z']
    inp = state['inp']
    row_spacing = state['row_spacing']

    content = str(request.form['jsonval'])
    bound = mz.geojson_fc_parser(content, 'Polygon')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    try:
        line = mz.geojson_fc_parser(content, 'LineString')
        line = mz.reproject_line(line)
        line = mz.reproject_line(line, in_projection='epsg:4326', out_projection=utm_pyproj)
    except Exception:
        line = None
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_irreg(bound, line, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats, 10)
    gvf_json = mz.gvf_json(gvf_arr)

    state.update({'utm_pyproj': utm_pyproj, 'row_space': row_space,
                  'poly_stats': poly_stats, 'polys2': polys2})
    save_state(state)
    return render_template('chart.html', string=gvf_json)


@app.route('/createZones', methods=['POST'])
def createZones():
    state = load_state()
    poly_stats = state['poly_stats']
    polys2 = state['polys2']
    row_space = state['row_space']
    utm_pyproj = state['utm_pyproj']
    field_type = state['field_type']

    classes = int(request.form['classes'])
    poly_comb, class_breaks = mz.get_poly_jenks(poly_stats, polys2, classes)
    poly_comb = mz.simplify_polys(poly_comb, row_space, 1)
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, class_breaks, inp=utm_pyproj)
    cmap_def, cmap_sel = mz.json_color_codes(classes)
    legend = mz.json_legend(class_breaks)

    state.update({'poly_comb': poly_comb, 'class_breaks': class_breaks})
    save_state(state)
    return render_template('displayZones.html', string={1: gjson_obj}, cmap_def=cmap_def,
                           cmap_sel=cmap_sel, legend=legend, field_type=field_type)


@app.route('/sendFile', methods=['POST'])
def sendFile():
    content = str(request.form['jsonval'])
    if request.form['filetype'] == "Save as GeoJSON":
        return Response(content,
                        mimetype='application/json',
                        headers={'Content-Disposition': 'attachment;filename=zones.geojson'})

    # export as shapefile zip using geopandas
    gdf = gpd.GeoDataFrame.from_features(json_mod.loads(content)['features'], crs='epsg:4326')
    with tempfile.TemporaryDirectory() as tmpdir:
        outpath = os.path.join(tmpdir, 'zones.shp')
        gdf.to_file(outpath)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmpdir):
                zf.write(os.path.join(tmpdir, fname), fname)
    return Response(buf.getvalue(),
                    mimetype='application/zip',
                    headers={'Content-Disposition': 'attachment;filename=zones.zip'})


@app.route('/simplify', methods=['GET'])
def simplify_polys():
    state = load_state()
    poly_comb = state['poly_comb']
    class_breaks = state['class_breaks']
    row_space = state['row_space']
    utm_pyproj = state['utm_pyproj']

    smooth = request.args.get('smooth', 1, type=int)
    new_poly_comb = mz.simplify_polys(poly_comb, row_space, smooth)
    new_poly_comb = mz.simplify_polys(new_poly_comb, row_space, smooth)
    gjson_obj = mz.zones_to_geojson_fc(new_poly_comb, class_breaks, inp=utm_pyproj)
    return jsonify(result=gjson_obj)


if __name__ == '__main__':
    app.run(debug=True)
