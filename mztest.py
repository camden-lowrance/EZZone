import numpy as np
import mz
import os
import timeit

path = "C:\\Users\\camden\\Documents\\mzproj\\"
os.chdir(path)
data = "ecdata.csv"
x, y, z = np.loadtxt(data, skiprows=1, delimiter=',', unpack=True)
line = {"type": "Feature", "properties": {}, "geometry": {"type": "LineString",
                                                          "coordinates": [[-9413014.1928254, 3693676.1860292],
                                                                          [-9412760.9951693, 3692926.1476893]]},
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}}}
gjbound = {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [
    [[-9412798.545766443, 3692811.718994205], [-9413030.090307293, 3692872.012304822],
     [-9413073.17095023, 3692889.500030657], [-9413139.628686234, 3692922.3874634416],
     [-9413163.22841828, 3692936.0905865547], [-9413188.163984219, 3692954.100428878],
     [-9413373.51093639, 3693172.1782349], [-9413374.178853335, 3693173.613828802],
     [-9413469.245698472, 3693460.605488081], [-9413470.35889338, 3693464.129302051],
     [-9413470.581532363, 3693465.1733952714], [-9413470.692851853, 3693465.695441918],
     [-9413474.70035352, 3693590.3347167717], [-9413471.026810324, 3693634.578702308],
     [-9413463.345765458, 3693671.253041847], [-9413455.998679068, 3693704.664635618],
     [-9413446.75916133, 3693732.8557389337], [-9413426.721652988, 3693784.4090822125],
     [-9413403.233240431, 3693828.392739457], [-9413391.099415936, 3693848.753180402],
     [-9413366.49780847, 3693888.2995184176], [-9413315.736120667, 3693961.649830794],
     [-9413301.598545337, 3693977.8339447854], [-9413227.905042432, 3694041.787508205],
     [-9413212.208994228, 3694051.96790225], [-9413026.750722568, 3694125.188678563],
     [-9412928.121653726, 3694163.822277505], [-9412826.709597614, 3694199.9761277167],
     [-9412770.5497978, 3694194.5246273], [-9412780.1044263, 3694132.4195418], [-9412870.8733974, 3694096.5896848],
     [-9412978.3629684, 3694132.4195418], [-9412980.7516255, 3694082.257742], [-9413028.5247682, 3694046.427885],
     [-9412940.1444543, 3693955.6589139], [-9412851.7641403, 3693974.768171], [-9412729.9426265, 3694079.8690848],
     [-9412744.2745693, 3694187.3586559], [-9412672.754741844, 3694178.3099086066],
     [-9412592.604708476, 3694155.73009464], [-9412526.703569924, 3694136.02173621],
     [-9412507.77925649, 3694124.66660374], [-9412478.724869393, 3694106.3939989298],
     [-9412381.320314948, 3694037.871974295], [-9412305.957019683, 3693926.9323682683],
     [-9412233.1019427, 3693819.5054573], [-9412395.5306278, 3693819.5054573], [-9412505.408856, 3693926.9950283],
     [-9412593.7891699, 3693929.3836854], [-9412627.2303698, 3693829.0600858], [-9412555.5706558, 3693673.7973721],
     [-9412541.238713, 3693415.8224017], [-9412462.4130276, 3693439.708973], [-9412495.8542274, 3693649.9108008],
     [-9412462.4130276, 3693805.1735145], [-9412204.4380571, 3693786.0642574], [-9412188.069678932, 3693737.423747907],
     [-9412185.398011154, 3693729.984419879], [-9412183.950857772, 3693725.807957006],
     [-9412143.319243632, 3693607.1709047733], [-9412141.872090252, 3693602.86397075],
     [-9412129.515626773, 3693563.05753119], [-9412128.179792885, 3693558.750612717],
     [-9412125.396805616, 3693549.7452426343], [-9412123.727013255, 3693487.2298854585],
     [-9412128.513751358, 3693439.0710914615], [-9412132.521253025, 3693401.4838719363],
     [-9412146.992786828, 3693329.4420243627], [-9412164.581266373, 3693271.1041003373],
     [-9412185.843289116, 3693221.5105584506], [-9412207.884548293, 3693175.440948561],
     [-9412220.686289735, 3693154.690104526], [-9412246.067133635, 3693117.886807438],
     [-9412311.856952693, 3693033.4484560573], [-9412521.582873348, 3692930.0873116795],
     [-9412618.65346932, 3692885.5848659803], [-9412687.114956157, 3692855.3076348593],
     [-9412748.118037114, 3692829.337138623], [-9412763.702765824, 3692823.0729065877],
     [-9412780.289369952, 3692816.808677764], [-9412798.545766443, 3692811.718994205]]]},
           "crs": {"type": "name", "properties": {"name": "EPSG:3857"}}}
poly = mz.reproject_poly(gjbound)
utmz = mz.utmzone(poly)
poly = mz.reproject_poly(poly, 'epsg:4326', utmz)
line = mz.reproject_line(line)
line = mz.reproject_line(line, 'epsg:4326', utmz)
spacing = 5
classes = 2
row_space = mz.get_spacing(poly, spacing)
smooth = 1
polys = mz.grid_irreg(poly, line, spacing)
gridz, bounds = mz.interpolate_raster(x, y, z, 'epsg:4326', utmz, poly)
poly_stats, polys2 = mz.get_poly_stats(gridz, polys, bounds)
gvf = mz.goodness_of_variance_fit(poly_stats, classes)
poly_comb = mz.get_poly_jenks(poly_stats, polys2, classes)
for i in range(2):
    try:
        poly_comb = mz.simplify_polys(poly_comb, (row_space * smooth))
    except TypeError:
        break
gjson_obj = mz.zones_to_geojson_fc(poly_comb, inp=utmz)

#timing calls
grid_gen = timeit.Timer(lambda: mz.grid_irreg(poly, line, spacing))
rast_gen = timeit.Timer(lambda: mz.interpolate_raster(x, y, z, 'epsg:4326', utmz, poly))
p_stats  = timeit.Timer(lambda: mz.get_poly_stats(gridz, polys, bounds))
gvf_time = timeit.Timer(lambda: mz.goodness_of_variance_fit(poly_stats, classes))
pcomb    = timeit.Timer(lambda: mz.get_poly_jenks(poly_stats, polys2, classes))
simpl    = timeit.Timer(lambda: mz.simplify_polys(poly_comb, (row_space * smooth)))
gjson    = timeit.Timer(lambda: mz.zones_to_geojson_fc(poly_comb, inp=utmz))

print "Polygon grid generation time: ", grid_gen.timeit(number = 1)
print ""
print "Raster generation time: ", rast_gen.timeit(number = 1)
print ""
print "Polygon stats exctraction time: ", p_stats.timeit(number = 1)
print ""
print "GVF time: ", gvf_time.timeit(number = 1)
print ""
print "Polygon classification time: ", pcomb.timeit(number = 1)
print ""
print "Polygon simplificaiton time: ", simpl.timeit(number = 1)
print ""
print "GeoJSON FC generation time: ", gjson.timeit(number = 1)
print ""




'''
with open('g2.json', 'w') as f:
    f.write(geojson.dumps(polyComb))
'''