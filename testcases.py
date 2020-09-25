__author__ = 'camden'
import numpy as np
import mz
import os
import datetime
import geojson
import simplify_polys as sf

def ec_circ_mzd():
    start = datetime.datetime.now()
    path = "C:\\Users\\camden\\Documents\\mzproj\\testcases"
    os.chdir(path)    
    points = 'ecCirc.csv'
    geoj   = {"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[-9412807.5739833,3692835.2294269],[-9412872.0677259,3692883.0025696],[-9412942.5331114,3692871.0592839],[-9413030.090307293,3692872.012304822],[-9413073.17095023,3692889.500030657],[-9413139.628686234,3692922.3874634416],[-9413163.22841828,3692936.0905865547],[-9413188.163984219,3692954.100428878],[-9413244.6982388,3693064.5405117],[-9413373.51093639,3693172.1782349],[-9413374.178853335,3693173.613828802],[-9413425.0418523,3693248.467111],[-9413420.2645381,3693316.5438393],[-9413472.814995,3693400.146839],[-9413469.245698472,3693460.605488081],[-9413470.35889338,3693464.129302051],[-9413470.581532363,3693465.1733952714],[-9413470.692851853,3693465.695441918],[-9413474.70035352,3693590.3347167717],[-9413471.026810324,3693634.578702308],[-9413463.345765458,3693671.253041847],[-9413455.998679068,3693704.664635618],[-9413446.75916133,3693732.8557389337],[-9413426.721652988,3693784.4090822125],[-9413403.233240431,3693828.392739457],[-9413391.099415936,3693848.753180402],[-9413366.49780847,3693888.2995184176],[-9413315.736120667,3693961.649830794],[-9413301.598545337,3693977.8339447854],[-9413227.905042432,3694041.787508205],[-9413212.208994228,3694051.96790225],[-9413026.750722568,3694125.188678563],[-9412981.945954,3694135.8532362],[-9412984.3346112,3694083.3027793],[-9413027.3304396,3694057.0275508],[-9413008.2211825,3694004.4770938],[-9412929.3954971,3693947.1493226],[-9412841.0151831,3693978.2018654],[-9412723.9709836,3694090.4687507],[-9412743.0802407,3694174.0717503],[-9412762.1894977,3694186.015036],[-9412800.4080119,3694123.9099505],[-9412879.2336973,3694095.2460649],[-9412955.6707256,3694133.4645791],[-9412928.121653726,3694163.822277505],[-9412826.709597614,3694199.9761277167],[-9412794.2043063,3694206.2410657075],[-9412672.754741844,3694178.3099086066],[-9412592.604708476,3694155.73009464],[-9412526.703569924,3694136.02173621],[-9412507.77925649,3694124.66660374],[-9412478.724869393,3694106.3939989298],[-9412437.3321276,3694028.3636652],[-9412380.0043564,3694042.695608],[-9412337.008528,3693999.6997796],[-9412305.957019683,3693926.9323682683],[-9412229.5189569,3693815.7731803],[-9412423.0001848,3693815.7731803],[-9412449.2754132,3693901.7648371],[-9412542.4330414,3693935.206037],[-9412630.8133554,3693908.9308085],[-9412618.8700697,3693806.2185518],[-9412566.3196128,3693653.3444952],[-9412554.3763271,3693543.4662671],[-9412575.8742413,3693467.0292388],[-9412549.5990128,3693395.3695248],[-9412458.8300418,3693455.0859531],[-9412504.2145273,3693631.846581],[-9412465.9960132,3693801.4412375],[-9412227.1302998,3693791.886609],[-9412188.069678932,3693737.423747907],[-9412185.398011154,3693729.984419879],[-9412183.950857772,3693725.807957006],[-9412143.319243632,3693607.1709047733],[-9412141.872090252,3693602.86397075],[-9412129.515626773,3693563.05753119],[-9412128.179792885,3693558.750612717],[-9412125.396805616,3693549.7452426343],[-9412123.727013255,3693487.2298854585],[-9412128.513751358,3693439.0710914615],[-9412132.521253025,3693401.4838719363],[-9412146.992786828,3693329.4420243627],[-9412164.581266373,3693271.1041003373],[-9412185.843289116,3693221.5105584506],[-9412207.884548293,3693175.440948561],[-9412220.686289735,3693154.690104526],[-9412246.067133635,3693117.886807438],[-9412311.856952693,3693033.4484560573],[-9412432.5548133,3693013.1843834],[-9412521.582873348,3692930.0873116795],[-9412547.2103557,3692920.0267552],[-9412563.9309556,3692977.3545264],[-9412571.096927,3692910.4721267],[-9412618.65346932,3692885.5848659803],[-9412687.114956157,3692855.3076348593],[-9412807.5739833,3692835.2294269]]]}},{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[-9412801.6023405,3693511.9658513]}}]}
    x, y, z = np.loadtxt(points, skiprows=1, delimiter=',', unpack=True)
    pivot_spacing = 25
    pivot_length = 800
    inp = 'epsg:4326'
    bound = mz.geojson_fc_parser(geoj, 'Polygon')
    point = mz.geojson_fc_parser(geoj, 'Point')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    point = mz.reproject_point(point)
    point = mz.reproject_point(obj=point, in_projection='epsg:4326', out_projection=utm_pyproj)
    polys = mz.grid_circ(pivot_spacing, pivot_length, point, bound)
    #polys = mz.grid_irreg(bound,row_space=20)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    #mz.create_geotiff('ecCircIrreg.tif', array, bounds, utm_pyproj)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats,10)
    opt_gvf, zones = mz.optimal_gfv(gvf_arr)    
    poly_comb = mz.get_poly_jenks(poly_stats, polys2, zones)
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, utm_pyproj)
    with open('ecCircIrreg.geojson', 'w') as f:
        f.write(geojson.dumps(gjson_obj))
    end = datetime.datetime.now()
    print end - start
    
    return gvf_arr


def ec_irreg_mzd():
    
    path = "C:\\Users\\camden\\Documents\\mzproj\\testcases"
    os.chdir(path)
    points = 'ecIrreg.csv'
    geoj   = {"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[-9434396.5832979,3654805.6754097],[-9434394.1946408,3654849.8655667],[-9434269.9844698,3654885.6954237],[-9434274.7617841,3654974.0757376],[-9434174.4381845,3655032.5978374],[-9434077.6975706,3655005.1282804],[-9434023.9527851,3655023.0432089],[-9434028.7300993,3655036.1808231],[-9434083.6692134,3655027.8205231],[-9434136.2196703,3655042.1524659],[-9434203.1020701,3655040.9581374],[-9434283.122084,3655018.2658946],[-9434339.2555267,3655049.3184373],[-9434394.1946408,3655045.7354516],[-9434420.4698692,3655017.071566],[-9434421.6641978,3654872.5578094],[-9434487.352269,3654841.5052667],[-9434552.155379301,3654807.8451190363],[-9434602.47178914,3654814.740481513],[-9434624.7000541,3654892.8613951],[-9434679.6391682,3654978.8530519],[-9434951.681031758,3655085.874396765],[-9434967.37707996,3655103.1782512614],[-9435005.670984792,3655149.625559799],[-9435037.508359158,3655194.5117806215],[-9435060.10621579,3655227.6886576237],[-9435067.7959524,3655251.1599651],[-9434702.331411,3655276.240865],[-9434658.141254,3655236.8280223],[-9434625.8943827,3655272.6578793],[-9434668.8902111,3655310.8763934],[-9434597.462412054,3655423.3689964428],[-9434552.600657264,3655432.8668579254],[-9434549.149753049,3655433.5173966503],[-9434486.922157696,3655443.795913074],[-9434377.383778756,3655429.874380229],[-9434308.03173599,3655409.4474866814],[-9434251.036156705,3655386.0281599504],[-9434212.4082934,3655358.4454544415],[-9434180.459599542,3655329.1714241556],[-9434154.1345988,3655242.7996651],[-9434131.4423561,3655221.3017509],[-9434087.2521991,3655204.581151],[-9434076.598514633,3655168.230553227],[-9434012.033209972,3655013.927051776],[-9434000.122024458,3654983.2227069438],[-9433994.89000839,3654967.220049074],[-9433983.869378801,3654933.133156061],[-9433986.429727089,3654899.43666366],[-9434059.677952033,3654875.367796931],[-9434062.460939301,3654874.5871858243],[-9434065.466565553,3654873.806574767],[-9434071.811776528,3654872.3754546237],[-9434103.315192422,3654865.3499581474],[-9434262.056786295,3654830.6128399875],[-9434284.09804547,3654825.7990897666],[-9434355.342519578,3654810.447142163],[-9434360.908494117,3654809.2762316875],[-9434396.5832979,3654805.6754097]]]}},{"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":[[-9434341.6441838,3655222.4960795],[-9434683.2221539,3655144.8647227]]}}]}
    x, y, z = np.loadtxt(points, skiprows=1, delimiter=',', unpack=True)
    row_spacing = 2.75
    inp = 'epsg:4326'
    bound = mz.geojson_fc_parser(geoj, 'Polygon')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    #if a line is drawn then do the same
    try:
        line = mz.geojson_fc_parser(geoj, 'LineString')
        line = mz.reproject_line(line)
        line = mz.reproject_line(line, in_projection='epsg:4326', out_projection=utm_pyproj)
    except Exception:
        line = None
    #create grid, interpolate, get grid stats, create geojson
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_irreg(bound, line, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats,10)
    opt_gvf, zones = mz.optimal_gfv(gvf_arr)    
    poly_comb = mz.get_poly_jenks(poly_stats, polys2, zones)
    poly_comb = mz.simplify_polys(poly_comb,row_space,5)
    end = datetime.datetime.now()
    
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, utm_pyproj)
    with open('ecIrregZones_Smoothed.geojson', 'w') as f:
        f.write(geojson.dumps(gjson_obj))
    
    return gvf_arr



def ec_rect_mzd():
    start = datetime.datetime.now()
    path = "C:\\Users\\camden\\Documents\\mzproj\\testcases"
    os.chdir(path)
    points = 'ecRect.csv'
    geoj   = {"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[2531363.0536617,4759844.7940697],[2531291.3939477,4759872.2636267],[2531211.971098,4759688.3370275],[2531282.4364834,4759660.2703061],[2531363.0536617,4759844.7940697]]]}}]}
    x, y, z = np.loadtxt(points, skiprows=1, delimiter=',', unpack=True)
    #z = np.log(z)
    row_spacing = 2
    inp = 'epsg:4326'
    bound = mz.geojson_fc_parser(geoj, "Polygon")
    bound = mz.reproject_poly(obj=bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(obj=bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    #create grid, interpolate, get grid stats, create geojson
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_rect(bound, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound, row_space)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats,10)
    opt_gvf, zones = mz.optimal_gfv(gvf_arr)    
    poly_comb = mz.get_poly_jenks(poly_stats, polys2, zones)
    poly_comb = mz.simplify_polys(poly_comb,row_space,2)
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, utm_pyproj)
    with open('ecRectZones.geojson', 'w') as f:
        f.write(geojson.dumps(gjson_obj))
    end = datetime.datetime.now()
    print end - start

    return gvf_arr
        
def yield_irreg_mzd():
    
    path = "C:\\Users\\camden\\Documents\\mzproj\\testcases"
    os.chdir(path)
    points = 'yieldIrreg.csv'
    geoj   = {"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[-9301117.823225545,3698999.468813305],[-9301144.651222827,3698999.7299549505],[-9301155.337893942,3699013.17875722],[-9301238.8859146,3699299.2413527],[-9301086.0118581,3699333.2797168],[-9301093.1778295,3699349.4031525],[-9301246.6490504,3699317.7534456],[-9301301.5881644,3699527.9552734],[-9301299.1995073,3699536.3155733],[-9301308.7541358,3699575.728416],[-9301331.4463786,3699634.2505158],[-9301344.469708798,3699687.3352849274],[-9301306.398442948,3699692.0361003606],[-9301277.73367407,3699693.7336174906],[-9301186.24797695,3699694.56017784],[-9301172.258456543,3699693.3418827453],[-9301172.035817562,3699692.8195697754],[-9301166.692482002,3699674.799785951],[-9301132.40607884,3699553.623959805],[-9300994.369910255,3699060.314967614],[-9300990.58504757,3699046.082685456],[-9300990.251089094,3699019.707307354],[-9300999.935884796,3699006.911352375],[-9301025.428048186,3699004.561076389],[-9301117.823225545,3698999.468813305]]]}},{"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":[[-9301226.6440468,3699463.4615306],[-9301199.1744898,3699367.318081],[-9301199.1744898,3699367.318081]]}}]}
    x, y, z = np.loadtxt(points, skiprows=1, delimiter=',', unpack=True)
    row_spacing = 1
    inp = 'epsg:4326'
    bound = mz.geojson_fc_parser(geoj, 'Polygon')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    #if a line is drawn then do the same
    try:
        line = mz.geojson_fc_parser(geoj, 'LineString')
        line = mz.reproject_line(line)
        line = mz.reproject_line(line, in_projection='epsg:4326', out_projection=utm_pyproj)
    except Exception:
        line = None
    #create grid, interpolate, get grid stats, create geojson
    row_space = mz.get_spacing(bound, row_spacing)
    polys = mz.grid_irreg(bound, line, row_space)
    array, bounds = mz.interpolate_raster(x, y, z, inp, utm_pyproj, bound)
    poly_stats, polys2 = mz.get_poly_stats(array, polys, bounds)
    gvf_arr = mz.gvf_array(poly_stats,10)
    opt_gvf, zones = mz.optimal_gfv(gvf_arr)    
    poly_comb = mz.get_poly_jenks(poly_stats, polys2, zones)    
    start = datetime.datetime.now()    
    #for i in range(2):
    
    poly_comb = mz.simplify_polys(poly_comb, row_space, 5)
    end = datetime.datetime.now()
    print end - start    
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, utm_pyproj)
    with open('yieldIrregZones', 'w') as f:
        f.write(geojson.dumps(gjson_obj))
    
    return gvf_arr
    
def yield_irreg2_mzd():
    start = datetime.datetime.now()
    path = "C:\\Users\\camden\\Documents\\mzproj\\testcases"
    os.chdir(path)
    points = 'yieldIrreg2.csv'
    geoj   = {"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[-51301.168900579,6812468.4146543],[-51365.662643187,6812563.9609397],[-51418.213100124,6812688.1711106],[-51496.8675805614,6812792.613483321],[-51486.748667676446,6812810.310445585],[-51294.002929177,6813034.526395],[-51217.565900903,6813177.845823],[-51128.81997214916,6813299.364303405],[-51082.25739381777,6813350.483997039],[-51031.581696823974,6813365.690180661],[-50964.368244745,6813282.9467369],[-50897.485845003,6813206.5097086],[-50735.057159923,6813122.9067089],[-50589.520279748474,6812994.761911179],[-50655.04755461804,6812891.944158894],[-50762.748799750545,6812791.6545526525],[-51022.837453083375,6812551.318586232],[-51162.626786832,6812587.847511],[-51301.168900579,6812468.4146543]]]}},{"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":[[-50880.765245069,6813067.9675948],[-51272.505014978,6812731.166939],[-51272.505014978,6812731.166939]]}}]}
    x, y, z = np.loadtxt(points, skiprows=1, delimiter=',', unpack=True)
    row_spacing = 1
    inp = 'epsg:27700'
    bound = mz.geojson_fc_parser(geoj, 'Polygon')
    bound = mz.reproject_poly(bound)
    utm_pyproj = mz.utmzone(bound)
    bound = mz.reproject_poly(bound, in_projection='epsg:4326', out_projection=utm_pyproj)
    #if a line is drawn then do the same
    try:
        line = mz.geojson_fc_parser(geoj, 'LineString')
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
    opt_gvf, zones = mz.optimal_gfv(gvf_arr)
    poly_comb = mz.get_poly_jenks(poly_stats, polys2, zones)
    poly_comb = mz.simplify_polys(poly_comb, row_space, 10)
    gjson_obj = mz.zones_to_geojson_fc(poly_comb, utm_pyproj)
    with open('yieldIrreg2Zones_Smoothed.geojson', 'w') as f:
        f.write(geojson.dumps(gjson_obj))

    end = datetime.datetime.now()
    print end - start
    return gvf_arr
    
