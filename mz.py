import math
import numpy as np
from scipy.interpolate import griddata
import pyproj
import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon, shape, LineString, mapping, MultiPoint, Point
from shapely.ops import unary_union
from shapely.affinity import rotate
from rasterstats import zonal_stats
import geojson
from jenkspy import jenks_breaks as jenks
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from osgeo import gdal
from osgeo import osr



# noinspection PyUnresolvedReferences
def extrapolate_nans(x, y, v):
    """
    ###FROM fatiando PROJECT ON GITHUB###

    Extrapolate the NaNs or masked values in a grid INPLACE using nearest neighbor interpolant

    .. warning:: Replaces the NaN or masked values of the original array!

    :param x: Array with the x coordinates of the data points.
    :type x: np.array
    :param y: Array with the y coordinates of the data points.
    :type y: np.array
    :param v: Array with the scalar value assigned to the data points.
    :type v: np.array
    :returns: Array with NaN's replaced by nearest neighbor function
    :rtype : np.array
    """

    if np.ma.is_masked(v):
        nans = v.mask
    else:
        nans = np.isnan(v)
    notnans = np.logical_not(nans)
    try:
        v[nans] = griddata((x[notnans], y[notnans]), v[notnans],
                           (x[nans], y[nans]), method='nearest').ravel()
        return v
    except ValueError:
        return


def geojson_fc_parser(obj, geomtype):
    """
    Parse a geometry from a GeoJSON FeatureCollection

    :param obj: the FeatureCollection object to parse a geometry from
    :type obj: str or geojson.FeatureCollection or dict
    :param geomtype: the desired geometry type to extract
            must be one of the following:("Point", "MultiPoint", "LineString",
            "MultiLineString", "Polygon", "MultiPolygon")
    :type geomtype: str
    :returns: desired geometry from FeatureCollection
    :rtype: geojson object
    """

    if geomtype not in ("Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"):
        return 'Invalid GeomType'
    # if our object is a raw string
    if type(obj) == str:
        obj = geojson.loads(obj)
    # noinspection PyTypeChecker
    for i in obj['features']:
        for v in i.items():
            for x in v:
                if isinstance(x, dict) and geomtype in x.values():
                    return x
    return 'GeomType not in FeatureCollection'


# noinspection PyUnusedLocal
def bound_json(x, y, geometry_type=1, in_projection='epsg:4326', out_projection='epsg:3857'):
    """
    Create a polygon GeoJSON boundary from x and y coordinate arrays

    :param x: x coordinate array
    :type  x: numpy array

    :param y: y coordinate array
    :type  y: numpy array

    :param geometry_type: type of field geometry, 1 for rectangular, 2 for VRI, and 3 for all others
    :type  geometry_type: int

    :param in_projection: the epsg value for the input x, y points
    :type  in_projection: string in the form of 'epsg:XXXX'

    :param out_projection: the epsg value for the desired created boundary
    :type  out_projection: string in the form of 'epsg:XXXX'

    :returns: GeoJSON boundary polygon as a dict
    :rtype: dict
    """
    # Ensure plain numpy arrays so fancy indexing (np.where) works on both
    # numpy arrays (demo path via np.loadtxt) and pandas Series (file-upload path).
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    g = geometry_type
    jfeat = []
    crs = {
        "type": "name",
        "properties": {
            "name": out_projection
        }}

    transformer = pyproj.Transformer.from_crs(in_projection, out_projection, always_xy=True)

    # get the point coordinates
    points = np.column_stack([x, y])

    # if rectangular desired, find corresponding point for xmin, ymin, xmax, ymax
    if g == 1:
        print("in function")
        xmax = list(transformer.transform(x.max(), y[np.where(x == x.max())].item(0)))
        ymax = list(transformer.transform(x[np.where(y == y.max())].item(0), y.max()))
        xmin = list(transformer.transform(x.min(), y[np.where(x == x.min())].item(0)))
        ymin = list(transformer.transform(x[np.where(y == y.min())].item(0), y.min()))

        geoj = geojson.Polygon([[xmax, ymax, xmin, ymin, xmax]], crs=crs)

    elif g == 2 or g == 3:
        points = MultiPoint(points)
        m = mapping(points.convex_hull)
        for i in m['coordinates']:
            for j in i:
                jfeat.append(list(transformer.transform(j[0], j[1])))

        geoj = geojson.Polygon([jfeat], crs=crs)
    else:
        return "Invalid geomtype"
    # return geoJson
    return geojson.loads(geojson.dumps(geoj))


def get_spacing(boundary, row_spacing):
    """

    :param boundary:
    :param row_spacing:
    :return:
    """
    new = row_spacing
    while new < (math.sqrt(boundary.area) / 100):
        new = new + row_spacing
    return new


# orders y elements least to greatest of a 2d numpy array and eliminates duplicate values,
# returning the new array
# noinspection PyUnresolvedReferences
def unique(a):
    """

    :param a:
    :return:
    """
    order = np.lexsort(a.T)
    a = a[order]
    diff = np.diff(a, axis=0)
    ui = np.ones(len(a), 'bool')
    ui[1:] = (diff != 0).any(axis=1)
    return a[ui]


# returns the difference between two x points
def deltax(xy1, xy2):
    """

    :param xy1:
    :param xy2:
    :return:
    """
    return xy2[0] - xy1[0]


# returns integer of epsg coordinates:
def epsg_int(string_epsg):
    """

    :param string_epsg:
    :return:
    """
    li = []
    for l in string_epsg:
        if l.isdigit():
            li.append(l)
    return int(''.join(li))


# reproject geojson object/string, shapely polygon/multip and return a shapely polygon
def reproject_poly(obj, in_projection='epsg:3857', out_projection='epsg:4326'):
    if isinstance(obj, geojson.geometry.Polygon):
        poly = shape(obj)
    elif type(obj) == str:
        poly = shape(geojson.loads(obj))
    elif type(obj) == dict:
        try:
            poly = shape(obj['geometry'])
        except KeyError:
            poly = shape(obj)
    else:
        poly = obj
    if not poly.is_valid:
        poly = poly.buffer(0)
    return gpd.GeoSeries([poly], crs=in_projection).to_crs(out_projection).iloc[0]


def reproject_multip(obj, in_projection='epsg:3857', out_projection='epsg:4326'):
    return list(gpd.GeoSeries(obj, crs=in_projection).to_crs(out_projection))


# reproject geojson/shapely point
def reproject_point(obj, in_projection='epsg:3857', out_projection='epsg:4326'):
    if isinstance(obj, geojson.geometry.Point):
        point = shape(obj)
    elif type(obj) == str:
        point = shape(geojson.loads(obj))
    elif type(obj) == dict:
        try:
            point = shape(obj['geometry'])
        except KeyError:
            point = shape(obj)
    else:
        point = obj
    return gpd.GeoSeries([point], crs=in_projection).to_crs(out_projection).iloc[0]


# reproject geojson/shapely line
def reproject_line(obj, in_projection='epsg:3857', out_projection='epsg:4326'):
    if isinstance(obj, geojson.geometry.LineString):
        line = shape(obj)
    elif type(obj) == str:
        line = shape(geojson.loads(obj))
    elif type(obj) == dict:
        try:
            line = shape(obj['geometry'])
        except KeyError:
            line = shape(obj)
    else:
        line = obj
    return gpd.GeoSeries([line], crs=in_projection).to_crs(out_projection).iloc[0]


# reproject arrays of separate x and y values
def reproject_array(x, y, inp, outp):
    transformer = pyproj.Transformer.from_crs(inp, outp, always_xy=True)
    xs, ys = transformer.transform(x, y)
    return np.column_stack([xs, ys])


# return a pyproj CRS object for the UTM zone containing the given coordinates
def utmzone(xy):
    if isinstance(xy, Polygon):
        xy = xy.exterior.coords[0]
    zone_num = int(math.floor((xy[0] + 180) / 6) + 1)
    south = xy[1] < 0
    proj_str = f'+proj=utm +zone={zone_num} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    if south:
        proj_str += ' +south'
    return pyproj.CRS.from_proj4(proj_str)


# create a rectangular grid of polygons given a shapely polygon in UTM coords and a row spacing variable
# noinspection PyUnboundLocalVariable,PyUnusedLocal
def grid_rect(polygon, row_space=2):
    """
    ----------------------------
    POLYGON GRID CREATION
    ----------------------------
    """
    # grab coordinates from shapely object
    poly_coords = list(polygon.exterior.coords)

    # eliminate duplicate closing polygon point
    xy = np.array(poly_coords)
    xy = unique(xy)

    # find max y and second to max y to find top line of polygon, min to find side line
    maxy = xy[3]
    nmaxy = xy[2]

    # find delta x between two top points, if positive, maxy is top left, if negative, nmaxy is top left
    # moving from left -------> right always,
    # use last_pt_side and last_pt_top/first_pt_top to calculate side line length
    dxtop = deltax(maxy, nmaxy)

    # find first point and top and side points from dxtop
    if dxtop > 0:
        first_pt_top = maxy
        last_pt_top = nmaxy
        last_pt_side = xy[1]
    elif dxtop < 0:
        first_pt_top = nmaxy
        last_pt_top = maxy
        last_pt_side = xy[0]

    # calculate top and side of field lines to use for number of row and column cubes
    top_field = LineString([first_pt_top, last_pt_top])
    side_field = LineString([first_pt_top, last_pt_side])
    row_cube = top_field.length / row_space
    col_cube = side_field.length / row_space

    # array of completed polys, structured as so:
    '''
    12345
    12345
    12345
    12345
    12345
    '''

    # calculate delta x and delta y for angle calculations, these angles don't change
    dxt = last_pt_top[0] - first_pt_top[0]
    dyt = last_pt_top[1] - first_pt_top[1]
    top_line_angle = math.atan2(dyt, dxt)

    dxs = last_pt_side[0] - first_pt_top[0]
    dys = last_pt_side[1] - first_pt_top[1]
    side_line_angle = math.atan2(dys, dxs)

    angle1 = side_line_angle
    angle2 = top_line_angle
    angle3 = math.pi + angle1

    first_poly_pt = first_pt_top
    polys = []

    # iterate through rows and columns and create polygons, column by column
    for j in range(1, int(math.ceil(row_cube))):
        for i in range(1, int(math.ceil(col_cube))):
            # special case for first entry
            if i == 1:
                # first polygon is special, needed for next column of polygons
                first_poly = [first_poly_pt]

                # second point
                x2 = first_poly_pt[0] + math.cos(angle1) * row_space
                y2 = first_poly_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]
                first_poly.append(second_pt)

                # third point
                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]
                first_poly.append(third_pt)

                # fourth point
                x4 = x3 + math.cos(angle3) * row_space
                y4 = y3 + math.sin(angle3) * row_space
                fourth_pt = [x4, y4]
                first_poly.append(fourth_pt)

                # create a shapely polygon and append to polys list, prepare to repeat
                poly = Polygon(first_poly)
                if poly.within(polygon):
                    polys.append(poly)
                elif poly.intersects(polygon):
                    polys.append(poly.intersection(polygon))
                old_poly = first_poly

                # first polygon point for next column is fourth point of polygon
                first_poly_pt = fourth_pt

            else:
                # first polygon point for next row is second point of previous polygon
                first_pt = old_poly[1]

                # second point
                x2 = first_pt[0] + math.cos(angle1) * row_space
                y2 = first_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]

                # third point
                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]

                # fourth point
                x4 = x3 + math.cos(angle3) * row_space
                y4 = y3 + math.sin(angle3) * row_space
                fourth_pt = [x4, y4]

                next_poly = [first_pt, second_pt, third_pt, fourth_pt]
                poly = Polygon(next_poly)
                if poly.within(polygon):
                    polys.append(poly)
                elif poly.intersects(polygon):
                    polys.append(poly.intersection(polygon))
                old_poly = next_poly
                next_poly = []
    return polys

    # create a irregular grid of polygons given a shapely polygon in UTM coords and a row spacing variable


# noinspection PyUnboundLocalVariable,PyUnusedLocal
def grid_irreg(boundary, row_line=None, row_space=2):
    """
    ----------------------------
    POLYGON GRID CREATION
    ----------------------------
    """
    # grab coordinates from boundary, calculate centroid for point of rotation
    bbox = boundary.bounds
    pxmin, pymin, pxmax, pymax = bbox
    if row_line:
        cent = boundary.centroid
        pxmin -= 200
        pymin -= 200
        pxmax += 200
        pymax += 200

        # calculate angle of rotation from line
        linec = list(row_line.coords)
        linec = unique(np.array(linec))
        maxy = linec[0]
        miny = linec[1]
        angle = math.atan2((maxy[1] - miny[1]), (maxy[0] - miny[0]))

    # first and last points of grid
    first_pt_top = (pxmin, pymax)
    last_pt_top = (pxmax, pymax)
    last_pt_side = (pxmin, pymin)

    # calculate top and side of field lines to use for number of row and column cubes
    top_field = LineString([first_pt_top, last_pt_top])
    side_field = LineString([first_pt_top, last_pt_side])
    row_cube = math.ceil(top_field.length) / math.floor(row_space)
    col_cube = math.ceil(side_field.length) / math.floor(row_space)

    # array of completed polys, structured as so:
    '''
    12345
    12345
    12345
    12345
    12345
    '''

    # calculate delta x and delta y for angle calculations, these angles don't change
    dxt = last_pt_top[0] - first_pt_top[0]
    dyt = last_pt_top[1] - first_pt_top[1]
    top_line_angle = math.atan2(dyt, dxt)

    dxs = last_pt_side[0] - first_pt_top[0]
    dys = last_pt_side[1] - first_pt_top[1]
    side_line_angle = math.atan2(dys, dxs)

    angle1 = side_line_angle
    angle2 = top_line_angle
    angle3 = math.pi + angle1

    first_poly_pt = first_pt_top
    polys = []

    # iterate through rows and columns and create polygons, column by column
    for j in range(1, int(math.ceil(row_cube) + 1)):
        for i in range(1, int(math.ceil(col_cube) + 1)):
            # special case for first entry
            if i == 1:
                # first polygon is special, needed for next column of polygons
                first_poly = [first_poly_pt]

                # second point
                x2 = first_poly_pt[0] + math.cos(angle1) * row_space
                y2 = first_poly_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]
                first_poly.append(second_pt)

                # third point
                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]
                first_poly.append(third_pt)

                # fourth point
                x4 = x3 + math.cos(angle3) * row_space
                y4 = y3 + math.sin(angle3) * row_space
                fourth_pt = [x4, y4]
                first_poly.append(fourth_pt)

                # create a shapely polygon and append to polys list, prepare to repeat
                poly = Polygon(first_poly)
                if row_line:
                    poly = rotate(poly, angle, cent, use_radians=True)
                if poly.within(boundary):
                    polys.append(poly)
                elif poly.intersects(boundary):
                    polys.append(poly.intersection(boundary))
                old_poly = first_poly

                # first polygon point for next column is fourth point of polygon
                first_poly_pt = fourth_pt

            else:
                # first polygon point for next row is second point of previous polygon
                first_pt = old_poly[1]

                # second point
                x2 = first_pt[0] + math.cos(angle1) * row_space
                y2 = first_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]

                # third point
                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]

                # fourth point
                x4 = x3 + math.cos(angle3) * row_space
                y4 = y3 + math.sin(angle3) * row_space
                fourth_pt = [x4, y4]

                next_poly = [first_pt, second_pt, third_pt, fourth_pt]
                poly = Polygon(next_poly)
                if row_line:
                    poly = rotate(poly, angle, cent, use_radians=True)
                if poly.within(boundary):
                    polys.append(poly)
                elif poly.intersects(boundary):
                    polys.append(poly.intersection(boundary))
                old_poly = next_poly
                next_poly = []
    return polys


# helper function to calculate point from relative polar coordinates (degrees)
def polar_point(origin_point, angle, distance):
    return [origin_point.x + math.sin(math.radians(angle)) * distance,
            origin_point.y + math.cos(math.radians(angle)) * distance]


# noinspection PyUnboundLocalVariable
def grid_circ(spacing, length, center, boundary):
    # circle radius
    radius = spacing
    # end of radius
    radius_end = int(math.ceil(length / radius))
    # width of sector in degrees
    sector_width = 4.0
    polys = []  # array for storing features to plot

    for x in range(0, int(360.0 / sector_width)):
        for r in range(1, radius_end + 1):
            if r == 1:
                segment_vertices = []
                # first point is center
                center_point = polar_point(center, 0, 0)
                segment_vertices.append(center_point)

                # second point
                first_vertex = polar_point(center, x * sector_width, r * radius)
                segment_vertices.append(first_vertex)

                # third point
                second_vertex = polar_point(center, x * sector_width + sector_width, r * radius)
                segment_vertices.append(second_vertex)

                # center point ends polygon
                segment_vertices.append(center_point)
                old_vertices = segment_vertices

                # add to polys if in field boundary
                poly = Polygon(segment_vertices)
                if poly.within(boundary):
                    polys.append(poly)
            else:
                new_vertices = []
                first_vertex = old_vertices[1]
                new_vertices.append(first_vertex)

                second_vertex = polar_point(center, x * sector_width, r * radius)
                new_vertices.append(second_vertex)

                third_vertex = polar_point(center, x * sector_width + sector_width, r * radius)
                new_vertices.append(third_vertex)

                fourth_vertex = old_vertices[2]
                new_vertices.append(fourth_vertex)

                # add to polys if in field boundary
                poly = Polygon(new_vertices)
                if poly.within(boundary):
                    polys.append(poly)

                old_vertices = new_vertices

    return polys


# interpolate point dataset to gridded surface covering boundary of input polygon, input poly should be in UTM
def interpolate_raster(x, y, z, inp, outp, poly, spacing=None):
    # reproject x and y points to match poly projection
    points = reproject_array(x, y, inp, outp)

    # get dimensions for grid
    xmin, ymin, xmax, ymax = poly.bounds

    # if row spacing is smaller than or equal to 2 m grid spacing
    if ((xmax - xmin) <= 200) or ((ymax - ymin) <= 200):
        # and spacing is smaller than  or equal to 2 m
        if spacing <= 2:
            # create grid with size of .5 m grid assuming utm coordinates inputted
            nx = round((xmax - xmin) * 2)
            ny = round((ymax - ymin) * 2)
        else:
            # create grid with size of 2 m grid assuming utm coordinates inputted
            nx = round((xmax - xmin) / 2)
            ny = round((ymax - ymin) / 2)
    # else use 2 m spacing
    else:
        # create grid with size of 2 m grid assuming utm coordinates inputted
        nx = round((xmax - xmin) / 2)
        ny = round((ymax - ymin) / 2)

    # Generate a regular grid to interpolate the data.
    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    gridx, gridy = np.meshgrid(xi, yi)

    # interpolate to grid
    gridz = griddata(points, z, (gridx, gridy), method='linear')

    # extrapolate beyond boundaries
    extrapolate_nans(gridx, gridy, gridz)

    # return interpolated grid plus bounds for use in raster transformation
    return gridz, [xmin, ymin, xmax, ymax]


# get stats that correspond to shapely polygon coverage of a numpy array ie raster
# noinspection PyBroadException,PyUnreachableCode
def get_poly_stats(array, polys, bounds, stat='mean'):
    # get individual bounds variables
    xmin, ymin, xmax, ymax = bounds

    # get transform for raster stats
    nrows, ncols = np.shape(array)
    xres = (xmax - xmin) / float(ncols)
    yres = (ymax - ymin) / float(nrows)
    # rasterstats requires GDAL convention: origin at top-left (ymax), yres negative.
    # The interpolated array has row 0 at ymin, so flip it to match.
    geotransform = (xmin, xres, 0, ymax, 0, -yres)
    array = np.flipud(array)

    stats = []

    for idx, poly in enumerate(polys):
        try:
            st = zonal_stats(poly, array, stats=stat, transform=geotransform)
            stats.append(st)
        except Exception:
            continue

    stats = np.array([i.get('mean') for j in stats for i in j])
    stats = stats.astype('float')
    boolm = np.isfinite(stats)
    polys = np.array(polys)[boolm]
    stats = stats[boolm]
    return stats, polys


def classify(value, breaks):
    for i in range(1, len(breaks)):
        if value < breaks[i]:
            return i
    return len(breaks) - 1


def plot_multip(polys):
    plt.close('all')
    try:
        gdf = gpd.GeoDataFrame(geometry=list(polys))
    except TypeError:
        gdf = gpd.GeoDataFrame(geometry=[polys])
    gdf.plot(cmap='tab10', figsize=(8, 8))
    plt.show()


def small_polys(multip, area, multip2):
    """
    Helper function for simplify_polys
    :param multip:
    :param area:
    :param multip2:
    :return:
    """
    small_p = []
    try:
        for p in multip:
            if p.area < area and p.intersects(multip2):
                try:
                    for p2 in multip2:
                        if p2.area > area and p.intersects(p2):
                            small_p.append(p)
                except TypeError:
                    if multip2.area > area:
                        small_p.append(p)
    except TypeError:
        if multip.area < area and multip.intersects(multip2):
            try:
                for p2 in multip2:
                    if p2.area > area and multip.intersects(p2):
                        small_p.append(multip)
            except TypeError:
                if multip2.area > area:
                    small_p.append(multip)
    return MultiPolygon(small_p)


def _s_polys(polys, spacing, *, reverse=False, step=1, half=False):
    """Move small polygons at zone boundaries into the adjacent zone.

    Args:
        polys:   list of shapely geometries (one per Jenks zone)
        spacing: grid spacing used to produce polys; area threshold = ceil(spacing**2)
        reverse: iterate from high index to low (True) or low to high (False)
        step:    index offset to neighbour (1 or 2)
        half:    restrict iteration to the first half (forward) or second half (reverse)
    """
    area = math.ceil(spacing ** 2)
    med = np.median(range(len(polys))) if half else None
    items = reversed(list(enumerate(polys))) if reverse else enumerate(polys)
    for idx, multip in items:
        if half:
            if not reverse and idx > med:
                break
            if reverse and idx < med:
                break
        neighbor = idx - step if reverse else idx + step
        try:
            area_inters = small_polys(multip, area, polys[neighbor])
        except IndexError:
            break
        if area_inters.area > 0:
            polys[idx] = polys[idx].difference(area_inters)
            polys[neighbor] = unary_union([polys[neighbor], area_inters])
    return polys


def remove_sliver(poly):
    eps = .001
    return poly.buffer(eps, 1, join_style=2).buffer(-eps, 1, join_style=2)


def simplify_polys(polys, spacing, smooth):
    new_polys = polys[:]
    for sm in range(1, smooth + 1):
        new_polys = _s_polys(new_polys, sm * spacing, reverse=False, step=1, half=True)
        new_polys = _s_polys(new_polys, sm * spacing, reverse=True,  step=1, half=True)
    for sm in range(1, smooth + 1):
        new_polys = _s_polys(new_polys, sm * spacing, reverse=False, step=1)
        new_polys = _s_polys(new_polys, sm * spacing, reverse=True,  step=1)
    for sm in range(1, smooth + 1):
        new_polys = _s_polys(new_polys, sm * spacing, reverse=False, step=2)
        new_polys = _s_polys(new_polys, sm * spacing, reverse=True,  step=2)
    try:
        new_polys = [remove_sliver(poly).simplify(.01) for poly in new_polys]
    except ValueError:
        pass
    return new_polys


def goodness_of_variance_fit(array, classes):
    """
    """
    # get the break points
    classes = jenks(array, classes)

    # do the actual classification
    classified = np.array([classify(i, classes) for i in array])

    # max value of zones
    maxz = max(classified)

    # nested list of zone indices
    zone_indices = [[idx for idx, val in enumerate(classified) if zone + 1 == val] for zone in range(maxz)]

    # sum of squared deviations from array mean
    sdam = np.sum((array - array.mean()) ** 2)

    # sorted polygon stats
    array_sort = [np.array([array[index] for index in zone]) for zone in zone_indices]

    # sum of squared deviations of class means
    sdcm = sum([np.sum((classified - classified.mean()) ** 2) for classified in array_sort])

    # goodness of variance fit
    gvf = (sdam - sdcm) / sdam

    return gvf


def gvf_array(stats, max_class):
    n_unique = len(np.unique(stats))
    gvf_arr = []
    for i in range(2, min(max_class, n_unique) + 1):
        gvf = goodness_of_variance_fit(stats, i)
        gvf_arr.append(round(gvf, 2))
        if gvf >= .9:
            break
    return gvf_arr


def optimal_gfv(array_of_gvf_values):
    for idx, val in enumerate(array_of_gvf_values):
        if val > .8:
            return val, idx + 2
            # return array_of_gvf_values[-1], len(array_of_gvf_values) + 1


def gvf_json(array_of_gvf_values):
    return [[idx + 2, val] for idx, val in enumerate(array_of_gvf_values)]


def get_poly_jenks(poly_stats, polys, classes):
    """

    """

    # cap classes to the number of unique values jenks can work with
    classes = min(classes, len(np.unique(poly_stats)))
    # get the break points
    classes = jenks(poly_stats, classes)

    # do the actual classification
    classified = np.array([classify(i, classes) for i in poly_stats])

    # max value of zones
    maxz = max(classified)

    # nested list of zone indices
    zone_indices = [[idx for idx, val in enumerate(classified) if zone + 1 == val] for zone in range(maxz)]

    # nested list of polygons corresponding to each zone number
    poly_sort = [[polys[index] for index in zone] for zone in zone_indices]

    # merge geometries, generate list of zones, create geojson feature collection from list
    poly_comb = [unary_union(polyz) for polyz in poly_sort]

    classes = [round(i,1) for i in classes]
    class_breaks = []
    for idx, val in enumerate(classes):
        try:
            class_breaks.append(str(val) + ' - ' + str(classes[idx + 1]))
        except IndexError:
            break

    return poly_comb, class_breaks


def zones_to_geojson_fc(zones, class_breaks, inp=None, outp='epsg:4326'):
    """

    """
    if inp:
        # reproject multipolygons to epsg:4326
        zones = reproject_multip(zones, in_projection=inp, out_projection=outp)

    # create features and dump geojson
    features = [geojson.Feature(geometry=mapping(zones[idx]), id=idx, properties={"zone": idx + 1, "values": val}) for
                idx, val in enumerate(class_breaks)]

    crs = {
        "type": "name",
        "properties": {
            "name": "EPSG:4326"
        }}

    feature_coll = geojson.FeatureCollection(features, crs=crs)
    return geojson.loads(geojson.dumps(feature_coll))

def json_legend(class_breaks):
    num_classes = len(class_breaks)
    if num_classes == 2:
        colors = ['#0000FF', '#FF0000']
        return [[colors[i], class_breaks[i]] for i in range(num_classes)]
    else:
        cmap = mpl.colormaps['RdBu_r'].resampled(num_classes)
        hex_colors = [mcolors.to_hex(cmap(i)) for i in range(num_classes)]
        return [[hex_colors[i], class_breaks[i]] for i in range(num_classes)]


def json_color_codes(num_classes):
    '''

    :param num_classes: number of classes to create a color map for
    :return: two dictionaries, first dict is for default openlayers display, second for select openlayers display
    '''
    if num_classes == 2:
        colors = ['#0000FF', '#FF0000']
        return {key + 1: {'fillColor': value} for (key, value) in enumerate(colors)}, {
            key + 1: {'fillColor': value, 'strokeColor': value} for (key, value) in enumerate(colors)}
    else:
        cmap = mpl.colormaps['RdBu_r'].resampled(num_classes)
        hex_colors = [mcolors.to_hex(cmap(i)) for i in range(num_classes)]
        return {key + 1: {'fillColor': value} for (key, value) in enumerate(hex_colors)}, {
            key + 1: {'fillColor': value, 'strokeColor': value} for (key, value) in enumerate(hex_colors)}


# noinspection PyUnusedLocal
def create_geotiff(filename, array, bounds, pyproj_object):
    # found here: http://hydrogeotools.blogspot.com/2013/11/gridding-interpolate-xyz-data.html
    nrows, ncols = array.shape
    xmin, ymin, xmax, ymax = bounds
    xres = (xmax - xmin) / float(ncols)
    yres = (ymax - ymin) / float(nrows)
    geotransform = (xmin, xres, 0, ymin, 0, yres)
    output_raster = gdal.GetDriverByName('GTiff').Create(filename, ncols, nrows, 1,
                                                         gdal.GDT_Float32, ['TFW=YES', 'COMPRESS=PACKBITS'])
    output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
    srs = osr.SpatialReference()  # Establish its coordinate encoding
    srs.ImportFromProj4(pyproj_object.to_proj4())  # import from pyproj CRS object
    output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system to the file
    output_raster.GetRasterBand(1).WriteArray(array)  # Writes my array to the raster
    output_raster = None


def asshape(geoj):
    return shape(geoj)