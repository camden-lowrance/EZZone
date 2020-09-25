"""
local app was changed to include a run.py and __init__.py file.
"""

#from app import app  # added this for local app
# noinspection PyUnresolvedReferences
from flask import render_template, request, Response, Flask, jsonify
from werkzeug import secure_filename
import mz
import numpy as np
import pandas as pd
import os
import requests

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
TEST_FILE = os.path.join(APP_ROOT, 'static/test.csv')
# noinspection PyUnresolvedReferences
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# noinspection PySetFunctionToLiteral
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'csv'])
# global variables
inp = 0
field_type = 0
x = 0
y = 0
z = 0
row_spacing = 0
pivot_length = 0
pivot_spacing = 0
fieldBound = 0
smooth = 0
poly_stats = 0
polys2 = 0
utm_pyproj = 0
row_space = 0
poly_comb = 0
class_breaks = 0


def allowed_file(filename):
    """

    :param filename:
    :return:
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


# noinspection PyDocstring
@app.route('/')
def index():
    return render_template('index2.html')


# noinspection PyDocstring
@app.route('/upload', methods=['POST', 'GET'])
def upload():
    # global variables
    global inp, field_type, x, y, z, row_spacing, pivot_spacing, pivot_length, fieldBound, smooth
    # get uploaded file, if ok then continue, else render badfile template

    fileup = request.files['file']
    if fileup:
        if allowed_file(fileup.filename):
            filename = secure_filename(fileup.filename)
            filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            fileup.save(filename)
            #unpack values from file, else render badfile template
            try:
                file = pd.read_csv(filename, sep = None)
            except Error:
                try:
                    file = pd.read_csv(filename)
                except CParserError:
                    return render_template('badFile.html')
            x = request.form['X']
            if file[x].dtype != 'float64':
                x = file[x].str.replace(',', '.').convert_objects(convert_numeric=True)
            else:
                x = file[x]

            y = request.form['Y']
            if file[y].dtype != 'float64':
                y = file[y].str.replace(',', '.').convert_objects(convert_numeric=True)
            else:
                y = file[y]

            z = request.form['Z']
            if file[z].dtype != 'float64':
                z = file[z].str.replace(',', '.').convert_objects(convert_numeric=True)
            else:
                z = file[z]
            os.remove(filename)
            inp = request.form['coord']
            inp = 'epsg:' + str(inp)
            field_type = request.form['field']
            field_type = int(field_type)
            unit_type = request.form['units']
            print unit_type
            #render templates according to field type
            if field_type == 1:
                #check for row spacing value
                try:
                    if unit_type == 'f':
                        row_spacing = float(request.form['row']) * .3048
                    else:
                        row_spacing = float(request.form['row'])
                except ValueError:
                    return render_template('badParam.html')
                #check for valid epsg
                try:
                    json = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
                except RuntimeError:
                    return render_template('badEpsg.html')
                #render in browser
                return render_template('rect.html', string=json)
            if field_type == 2:
                #check for valid
                try:
                    if unit_type == 'f':
                        pivot_spacing = float(request.form['spacing']) * .3048
                    else:
                        pivot_spacing = float(request.form['spacing'])
                except ValueError:
                    return render_template('badParam.html')
                try:
                    if unit_type == 'f':
                        pivot_length = float(request.form['length']) * .3048
                    else:
                        pivot_length = float(request.form['length'])
                except ValueError:
                    return render_template('badParam.html')
                try:
                    json = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
                    fieldBound = mz.asshape(json)
                except RuntimeError:
                    return render_template('badEpsg.html')
                return render_template('vri.html', string=json)
            if field_type == 3:
                #check for row spacing value
                try:
                    if unit_type == 'f':
                        row_spacing = float(request.form['row']) * .3048
                    else:
                        row_spacing = float(request.form['row'])
                except ValueError:
                    return render_template('badParam.html')
                #check for valid epsg
                try:
                    json = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
                except RuntimeError:
                    return render_template('badEpsg.html')
                #render in browser
                return render_template('irreg.html', string=json)
        else:
            return render_template('badFile.html')
    #demo file example
    x, y, z = np.loadtxt(TEST_FILE, skiprows=1, delimiter=",", unpack=True)
    inp = request.form['coord']
    inp = 'epsg:' + str(inp)
    field_type = request.form['field']
    field_type = int(field_type)
    unit_type = request.form['units']
    print unit_type
    #render templates according to field type
    if field_type == 1:
        #check for row spacing value
        try:
            if unit_type == 'f':
                row_spacing = float(request.form['row']) * .3048
            else:
                row_spacing = float(request.form['row'])
        except ValueError:
            return render_template('badParam.html')
        #check for valid epsg
        try:
            json = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
        except RuntimeError:
            return render_template('badEpsg.html')
        #render in browser
        return render_template('rect.html', string=json)
    if field_type == 2:
        #check for valid
        try:
            pivot_spacing = float(request.form['spacing'])
        except ValueError:
            return render_template('badParam.html')
        try:
            pivot_length = float(request.form['length'])
        except ValueError:
            return render_template('badParam.html')
        try:
            json = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
            fieldBound = mz.asshape(json)
        except RuntimeError:
            return render_template('badEpsg.html')
        return render_template('vri.html', string=json)
    if field_type == 3:
        #check for row spacing value
        try:
            row_spacing = float(request.form['row'])
        except ValueError:
            return render_template('badParam.html')
        #check for valid epsg
        try:
            json = mz.bound_json(x=x, y=y, geometry_type=field_type, in_projection=inp)
        except RuntimeError:
            return render_template('badEpsg.html')
        #render in browser
        return render_template('irreg.html', string=json)


# noinspection PyDocstring,PyPep8Naming
@app.route('/createRect', methods=['POST'])
def createRect():
    global utm_pyproj, row_space, poly_stats, polys2
    # get the customized geojson, reproject to 4326, get utmzone, reproject to utm
    content = str(request.form['jsonval'])
    bound = mz.geojson_fc_parser(content, "Polygon")
    bound = mz.reproject_poly(obj=bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(obj=bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    # create grid, interpolate, get grid stats, create geojson
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_rect(bound, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound, row_space)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats, 10)
    gvf_json = mz.gvf_json(gvf_arr)

    return render_template('chart.html', string=gvf_json)


# noinspection PyDocstring,PyPep8Naming
@app.route('/createVri', methods=['POST'])
def createVri():
    global utm_pyproj, row_space, poly_stats, polys2
    # get the customized geojson, reproject to 4326, get utmzone, reproject to utm
    content = str(request.form['jsonval'])

    bound = mz.geojson_fc_parser(content, 'Polygon')
    point = mz.geojson_fc_parser(content, 'Point')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    point = mz.reproject_point(point)
    point = mz.reproject_point(obj=point, in_projection='epsg:4326', out_projection=utm_pyproj)
    # create grid, interpolate, get grid stats, create geojson
    polys = mz.grid_circ(pivot_spacing, pivot_length, point, bound)
    print 'here'
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats, 10)
    gvf_json = mz.gvf_json(gvf_arr)

    return render_template('chart.html', string=gvf_json)


# noinspection PyDocstring,PyPep8Naming
@app.route('/createIrreg', methods=['POST'])
def createIrreg():
    global utm_pyproj, row_space, poly_stats, polys2
    # get the customized polygon, reproject to 4326, get utmzone, reproject to utm
    content = str(request.form['jsonval'])
    bound = mz.geojson_fc_parser(content, 'Polygon')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    # if a line is drawn then do the same
    try:
        line = mz.geojson_fc_parser(content, 'LineString')
        line = mz.reproject_line(line)
        line = mz.reproject_line(line, in_projection='epsg:4326', out_projection=utm_pyproj)
    except Exception:
        line = None
    #create grid, interpolate, get grid stats, create geojson
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_irreg(bound, line, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats, 10)
    gvf_json = mz.gvf_json(gvf_arr)

    return render_template('chart.html', string=gvf_json)


@app.route('/createZones', methods=['POST'])
def createZones():
    classes = int(request.form['classes'])
    global poly_comb, class_breaks, field_type
    poly_comb, class_breaks = mz.get_poly_jenks(poly_stats, polys2, classes)
    poly_comb = mz.simplify_polys(poly_comb, row_space, 1)
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, class_breaks, inp=utm_pyproj)
    # create colormap
    cmap_def, cmap_sel = mz.json_color_codes(classes)
    legend = mz.json_legend(class_breaks)
    #render in browser
    return render_template('displayZones.html', string={1: gjson_obj}, cmap_def=cmap_def, cmap_sel=cmap_sel,
                           legend=legend, field_type = field_type)


# noinspection PyDocstring,PyPep8Naming
@app.route('/sendFile', methods=['POST'])
def sendFile():
    content = str(request.form['jsonval'])
    if request.form['filetype'] == "Save as GeoJSON":
        return Response(content,
                        mimetype='application/json',
                        headers={'Content-Disposition': 'attachment;filename=zones.geojson'})
    else:
        data = {'json': content}
        r = requests.post('http://ogre.adc4gis.com/convertJson', data=data)
        if r.status_code == 200:
            return Response(r.content,
                            mimetype='application/zip',
                            headers={'Content-Disposition': 'attachment;filename=zones.zip'})

@app.route('/simplify', methods=['GET'])
def simplify_polys():
    global poly_comb, class_breaks
    smooth = request.args.get('smooth', 1, type=int)
    new_poly_comb = mz.simplify_polys(poly_comb, row_space, smooth)
    new_poly_comb = mz.simplify_polys(new_poly_comb, row_space, smooth)
    gjson_obj = mz.zones_to_geojson_fc(new_poly_comb, class_breaks, inp=utm_pyproj)
    return jsonify(result = gjson_obj)


app.secret_key = '12ad432gfd'
if __name__ == '__main__':
    app.run(debug=True)