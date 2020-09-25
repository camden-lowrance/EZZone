'''
local app was changed to include a run.py and __init__.py file.
'''


from app import app   #added this for local app
from flask import render_template, request, send_file, Response, Flask
from werkzeug import secure_filename
import mz
import numpy as np
import os

#app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
TEST_FILE = os.path.join(APP_ROOT, 'static/test.csv')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'csv'])
#global variables
inp = 0
field_type = 0
x = 0
y = 0
z = 0
row_spacing = 0
pivot_length = 0
pivot_spacing = 0
classes = 0
fieldBound = 0
smooth = 0

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST','GET'])
def upload():
    #global variables
    global inp, field_type, x, y, z, classes, row_spacing, pivot_spacing, pivot_length, fieldBound, smooth
    #get uploaded file, if ok then continue, else render badfile template
    fileup = request.files['file']
    if fileup:
        if allowed_file(fileup.filename):
            filename = secure_filename(fileup.filename)
            filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            fileup.save(filename)
            #unpack values from file, else render badfile template
            try :
                x,y,z = np.loadtxt(filename,skiprows=1,delimiter=",", unpack=True)
                os.remove(filename)
            except ValueError:
                return render_template('badFile.html') 
            #grab rest of values from form, modify to correct type              
            classes = int(request.form['classes'])        
            inP = request.form['coord']
            inP = 'epsg:' + str(inP)
            fieldType = request.form['field']
            fieldType = int(fieldType)
            #render templates according to field type
            if fieldType == 1:
                #check for row spacing value
                try:
                    rowSpacing = float(request.form['row'])
                    smooth = int(request.form['smooth'])
                except ValueError:
                    return render_template('badParam.html')
                #check for valid epsg
                try:
                    json = mz.boundJson(x = x, y = y,geometryType = fieldType, inProjection =inP)
                except RuntimeError:
                    return render_template('badEpsg.html')
                #render in browser
                return render_template('rect.html',string=json)
            if fieldType == 2:
                #check for valid 
                try:
                    pivotSpacing = float(request.form['spacing'])
                except ValueError:
                    return render_template('badParam.html')
                try:
                    pivotLength = float(request.form['length'])
                except ValueError:
                    return render_template('badParam.html')
                try:
                    json = mz.boundJson(x = x, y = y,geometryType = fieldType, inProjection =inP)
                    fieldBound = mz.asshape(json)
                except RuntimeError:
                    return render_template('badEpsg.html')
                return render_template('vri.html', string = json)
            if fieldType == 3:
                #check for row spacing value
                try:
                    rowSpacing = float(request.form['row'])
                    smooth = int(request.form['smooth'])
                except ValueError:
                    return render_template('badParam.html')
                #check for valid epsg
                try:
                    json = mz.boundJson(x = x, y = y,geometryType = fieldType, inProjection =inP)
                except RuntimeError:
                    return render_template('badEpsg.html')
                #render in browser
                return render_template('irreg.html',string=json)
        else:
            return render_template('badFile.html')
    #unpack values from file, else render badfile template
    x,y,z = np.loadtxt(TEST_FILE,skiprows=1,delimiter=",", unpack=True)
    #grab rest of values from form, modify to correct type              
    classes = int(request.form['classes'])        
    inP = request.form['coord']
    inP = 'epsg:' + str(inP)
    fieldType = request.form['field']
    fieldType = int(fieldType)
    #render templates according to field type
    if fieldType == 1:
        #check for row spacing value
        try:
            rowSpacing = float(request.form['row'])
            smooth = int(request.form['smooth'])
        except ValueError:
            return render_template('badParam.html')
        #check for valid epsg
        try:
            json = mz.boundJson(x = x, y = y,geometryType = fieldType, inProjection =inP)
        except RuntimeError:
            return render_template('badEpsg.html')
        #render in browser
        return render_template('rect.html',string=json)
    if fieldType == 2:
        #check for valid 
        try:
            pivotSpacing = float(request.form['spacing'])
        except ValueError:
            return render_template('badParam.html')
        try:
            pivotLength = float(request.form['length'])
        except ValueError:
            return render_template('badParam.html')
        try:
            json = mz.boundJson(x = x, y = y,geometryType = fieldType, inProjection =inP)
            fieldBound = mz.asshape(json)
        except RuntimeError:
            return render_template('badEpsg.html')
        return render_template('vri.html', string = json)
    if fieldType == 3:
        #check for row spacing value
        try:
            rowSpacing = float(request.form['row'])
            smooth = int(request.form['smooth'])
        except ValueError:
            return render_template('badParam.html')
        #check for valid epsg
        try:
            json = mz.boundJson(x = x, y = y,geometryType = fieldType, inProjection =inP)
        except RuntimeError:
            return render_template('badEpsg.html')
        #render in browser
        return render_template('irreg.html',string=json)
@app.route('/createRect', methods=['POST'])
def createRect():
    #get the customized geojson, reproject to 4326, get utmzone, reproject to utm
    content = str(request.form['jsonval'])
    bound = mz.reprojectPoly(obj = content)
    utmPyProj = mz.utmzone(bound)
    bound = mz.reprojectPoly(obj = bound, in_projection= 'epsg:4326', out_projection= utmPyProj)
    #create grid, interpolate, get grid stats, create geojson
    rSpace = mz.getSpacing(bound, row_spacing)
    polys = mz.grid_rect(bound, rSpace)
    array, bounds = mz.interpolate_raster(x,y,z,inp, utmPyProj, bound)
    polyStats, polys2 = mz.get_poly_stats(array,polys,bounds)
    gjsonObj = mz.gjsonJenks(polyStats,polys2,utmPyProj,classes, (rSpace*smooth))
    #create colormap
    cmap = mz.json_color_codes(classes)
    #render in browser
    return render_template('displayZones.html', string = gjsonObj, cmap = cmap)
    
@app.route('/createVri', methods=['POST'])
def createVri():
    #get the customized geojson, reproject to 4326, get utmzone, reproject to utm
    content = str(request.form['jsonval'])
    bound = mz.geojFCparser(content, 'Polygon')
    point = mz.geojFCparser(content, 'Point')
    bound = mz.reprojectPoly(bound)
    utmPyProj = mz.utmzone(bound)
    bound = mz.reprojectPoly(bound, in_projection= 'epsg:4326', out_projection= utmPyProj)
    point = mz.reproject_point(point)
    point = mz.reproject_point(obj = point, in_projection= 'epsg:4326', out_projection= utmPyProj)
    #create grid, interpolate, get grid stats, create geojson    
    polys = mz.grid_circ(pivot_spacing, pivot_length, point, bound)
    array, bounds = mz.interpolate_raster(x,y,z, inp, utmPyProj, bound)
    polyStats, polys2 = mz.get_poly_stats(array,polys,bounds)
    gjsonObj = mz.gjsonJenks(polyStats,polys2,utmPyProj,classes)
    #create colormap
    cmap = mz.json_color_codes(classes)
    #render in browser
    return render_template('displayZones.html', string = gjsonObj, cmap = cmap)
    
@app.route('/createIrreg', methods=['POST'])
def createIrreg():
    #get the customized geojson, reproject to 4326, get utmzone, reproject to utm
    content = str(request.form['jsonval'])
    bound = mz.geojFCparser(content, 'Polygon')
    line  = mz.geojFCparser(content, 'LineString')
    bound = mz.reprojectPoly(bound)
    line  = mz.reproject_line(line)
    utmPyProj = mz.utmzone(bound)
    bound = mz.reprojectPoly(bound, in_projection= 'epsg:4326', out_projection= utmPyProj)
    line  = mz.reproject_line(line, in_projection= 'epsg:4326', out_projection= utmPyProj)
    #create grid, interpolate, get grid stats, create geojson
    rSpacing = mz.getSpacing(bound, row_spacing)
    polys = mz.grid_irreg(bound, line, rSpacing)
    array, bounds = mz.interpolate_raster(x,y,z, inp, utmPyProj, bound)
    polyStats, polys2 = mz.get_poly_stats(array,polys,bounds)
    gjsonObj = mz.gjsonJenks(polyStats,polys2,utmPyProj,classes, (rSpacing*smooth))
    #create colormap
    cmap = mz.json_color_codes(classes)
    #render in browser
    return render_template('displayZones.html', string = gjsonObj, cmap = cmap)

@app.route('/sendFile', methods=['POST'])
def sendFile():
    content = str(request.form['jsonval'])
    return Response(content, 
            mimetype='application/json',
            headers={'Content-Disposition':'attachment;filename=zones.geojson'})

app.secret_key = '12ad432gfd' 