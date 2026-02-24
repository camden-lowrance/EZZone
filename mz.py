"""
Core geospatial library for agricultural management zone generation.

This module provides functions for:
- Boundary creation from point data
- Grid generation (rectangular, irregular, center-pivot)
- Raster interpolation
- Zonal statistics
- Jenks classification
- GeoJSON export
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
import pyproj
import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon, shape, LineString, mapping, MultiPoint, Point
from shapely.ops import unary_union
from shapely.affinity import rotate
import geojson
from jenkspy import jenks_breaks as jenks
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from osgeo import gdal
from osgeo import osr


def extrapolate_nans(x: np.ndarray, y: np.ndarray, v: np.ndarray) -> np.ndarray | None:
    """
    Extrapolate NaN values in a grid using nearest neighbor interpolation.

    Args:
        x: Array with the x coordinates of the data points.
        y: Array with the y coordinates of the data points.
        v: Array with the scalar value assigned to the data points.

    Returns:
        Array with NaN's replaced by nearest neighbor function, or None if interpolation fails.
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
        return None


def geojson_fc_parser(obj: str | dict, geomtype: str) -> dict | str:
    """
    Parse a geometry from a GeoJSON FeatureCollection.

    Args:
        obj: The FeatureCollection object to parse a geometry from.
            Can be a string, geojson.FeatureCollection, or dict.
        geomtype: The desired geometry type to extract.
            Must be one of: "Point", "MultiPoint", "LineString",
            "MultiLineString", "Polygon", "MultiPolygon".

    Returns:
        The desired geometry as a dict, or an error message string.
    """
    if geomtype not in ("Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"):
        return 'Invalid GeomType'
    if isinstance(obj, str):
        obj = geojson.loads(obj)
    for feature in obj['features']:
        for key, value in feature.items():
            if isinstance(value, dict) and geomtype in value.values():
                return value
    return 'GeomType not in FeatureCollection'


def bound_json(
    x: np.ndarray,
    y: np.ndarray,
    geometry_type: int = 1,
    in_projection: str = 'epsg:4326',
    out_projection: str = 'epsg:3857'
) -> dict:
    """
    Create a polygon GeoJSON boundary from x and y coordinate arrays.

    Args:
        x: x coordinate array.
        y: y coordinate array.
        geometry_type: Type of field geometry.
            1 = rectangular, 2 = VRI, 3 = irregular (convex hull).
        in_projection: The EPSG value for the input x, y points (e.g., 'epsg:4326').
        out_projection: The EPSG value for the desired created boundary (e.g., 'epsg:3857').

    Returns:
        GeoJSON boundary polygon as a dict.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    g = geometry_type
    jfeat = []
    crs = {
        "type": "name",
        "properties": {
            "name": out_projection
        }
    }

    transformer = pyproj.Transformer.from_crs(in_projection, out_projection, always_xy=True)
    points = np.column_stack([x, y])

    if g == 1:
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
        return {"error": "Invalid geomtype"}
    
    return geojson.loads(geojson.dumps(geoj))


def get_spacing(boundary: Polygon, row_spacing: float) -> float:
    """
    Calculate adjusted row spacing based on boundary size.

    Args:
        boundary: Shapely polygon representing the field boundary.
        row_spacing: Desired row spacing in meters.

    Returns:
        Adjusted row spacing that fits within the boundary.
    """
    new = row_spacing
    while new < (math.sqrt(boundary.area) / 100):
        new = new + row_spacing
    return new


def unique(a: np.ndarray) -> np.ndarray:
    """
    Remove duplicate rows from a 2D numpy array while preserving order.

    Args:
        a: 2D numpy array.

    Returns:
        Array with duplicate rows removed.
    """
    order = np.lexsort(a.T)
    a = a[order]
    diff = np.diff(a, axis=0)
    ui = np.ones(len(a), 'bool')
    ui[1:] = (diff != 0).any(axis=1)
    return a[ui]


def deltax(xy1: tuple, xy2: tuple) -> float:
    """
    Calculate the x difference between two points.

    Args:
        xy1: First point as (x, y) tuple.
        xy2: Second point as (x, y) tuple.

    Returns:
        The difference in x coordinates (xy2[0] - xy1[0]).
    """
    return xy2[0] - xy1[0]


def epsg_int(string_epsg: str) -> int:
    """
    Extract numeric EPSG code from a string.

    Args:
        string_epsg: String containing EPSG code (e.g., 'epsg:4326').

    Returns:
        The numeric EPSG code as an integer.
    """
    li = []
    for l in string_epsg:
        if l.isdigit():
            li.append(l)
    return int(''.join(li))


def reproject_poly(
    obj: Any,
    in_projection: str = 'epsg:3857',
    out_projection: str = 'epsg:4326'
) -> Polygon:
    """
    Reproject a polygon from one CRS to another.

    Args:
        obj: Polygon as geojson, shapely geometry, or dict.
        in_projection: Input CRS (e.g., 'epsg:3857').
        out_projection: Output CRS (e.g., 'epsg:4326').

    Returns:
        Reprojected Shapely polygon.
    """
    if isinstance(obj, geojson.geometry.Polygon):
        poly = shape(obj)
    elif isinstance(obj, str):
        poly = shape(geojson.loads(obj))
    elif isinstance(obj, dict):
        try:
            poly = shape(obj['geometry'])
        except KeyError:
            poly = shape(obj)
    else:
        poly = obj
    
    if not poly.is_valid:
        poly = poly.buffer(0)
    
    return gpd.GeoSeries([poly], crs=in_projection).to_crs(out_projection).iloc[0]


def reproject_multip(
    obj: list[Polygon],
    in_projection: str = 'epsg:3857',
    out_projection: str = 'epsg:4326'
) -> list[Polygon]:
    """
    Reproject multiple polygons from one CRS to another.

    Args:
        obj: List of Shapely polygons.
        in_projection: Input CRS.
        out_projection: Output CRS.

    Returns:
        List of reprojected Shapely polygons.
    """
    return list(gpd.GeoSeries(obj, crs=in_projection).to_crs(out_projection))


def reproject_point(
    obj: Any,
    in_projection: str = 'epsg:3857',
    out_projection: str = 'epsg:4326'
) -> Point:
    """
    Reproject a point from one CRS to another.

    Args:
        obj: Point as geojson, shapely geometry, or dict.
        in_projection: Input CRS.
        out_projection: Output CRS.

    Returns:
        Reprojected Shapely point.
    """
    if isinstance(obj, geojson.geometry.Point):
        point = shape(obj)
    elif isinstance(obj, str):
        point = shape(geojson.loads(obj))
    elif isinstance(obj, dict):
        try:
            point = shape(obj['geometry'])
        except KeyError:
            point = shape(obj)
    else:
        point = obj
    
    return gpd.GeoSeries([point], crs=in_projection).to_crs(out_projection).iloc[0]


def reproject_line(
    obj: Any,
    in_projection: str = 'epsg:3857',
    out_projection: str = 'epsg:4326'
) -> LineString:
    """
    Reproject a line from one CRS to another.

    Args:
        obj: Line as geojson, shapely geometry, or dict.
        in_projection: Input CRS.
        out_projection: Output CRS.

    Returns:
        Reprojected Shapely line.
    """
    if isinstance(obj, geojson.geometry.LineString):
        line = shape(obj)
    elif isinstance(obj, str):
        line = shape(geojson.loads(obj))
    elif isinstance(obj, dict):
        try:
            line = shape(obj['geometry'])
        except KeyError:
            line = shape(obj)
    else:
        line = obj
    
    return gpd.GeoSeries([line], crs=in_projection).to_crs(out_projection).iloc[0]


def reproject_array(
    x: np.ndarray,
    y: np.ndarray,
    inp: str,
    outp: str
) -> np.ndarray:
    """
    Reproject arrays of x and y coordinates.

    Args:
        x: Array of x coordinates.
        y: Array of y coordinates.
        inp: Input CRS.
        outp: Output CRS.

    Returns:
        Nx2 array of reprojected coordinates.
    """
    transformer = pyproj.Transformer.from_crs(inp, outp, always_xy=True)
    xs, ys = transformer.transform(x, y)
    return np.column_stack([xs, ys])


def utmzone(xy: tuple | Polygon) -> pyproj.CRS:
    """
    Get the UTM CRS for the given coordinates.

    Args:
        xy: Tuple of (x, y) coordinates or a Shapely polygon.

    Returns:
        pyproj CRS object for the appropriate UTM zone.
    """
    if isinstance(xy, Polygon):
        xy = xy.exterior.coords[0]
    
    zone_num = int(math.floor((xy[0] + 180) / 6) + 1)
    south = xy[1] < 0
    proj_str = f'+proj=utm +zone={zone_num} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    if south:
        proj_str += ' +south'
    
    return pyproj.CRS.from_proj4(proj_str)


def grid_rect(polygon: Polygon, row_space: float = 2) -> list[Polygon]:
    """
    Create a rectangular grid of polygons within a boundary.

    Args:
        polygon: Shapely polygon in UTM coordinates representing the field boundary.
        row_space: Spacing between grid cells in meters.

    Returns:
        List of Shapely polygons representing the grid cells.
    """
    poly_coords = list(polygon.exterior.coords)
    xy = np.array(poly_coords)
    xy = unique(xy)

    maxy = xy[3]
    nmaxy = xy[2]
    dxtop = deltax(maxy, nmaxy)

    if dxtop > 0:
        first_pt_top = maxy
        last_pt_top = nmaxy
        last_pt_side = xy[1]
    elif dxtop < 0:
        first_pt_top = nmaxy
        last_pt_top = maxy
        last_pt_side = xy[0]
    else:
        return []

    top_field = LineString([first_pt_top, last_pt_top])
    side_field = LineString([first_pt_top, last_pt_side])
    row_cube = top_field.length / row_space
    col_cube = side_field.length / row_space

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
    polys: list[Polygon] = []

    for j in range(1, int(math.ceil(row_cube))):
        for i in range(1, int(math.ceil(col_cube))):
            if i == 1:
                first_poly = [first_poly_pt]
                x2 = first_poly_pt[0] + math.cos(angle1) * row_space
                y2 = first_poly_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]
                first_poly.append(second_pt)

                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]
                first_poly.append(third_pt)

                x4 = x3 + math.cos(angle3) * row_space
                y4 = y3 + math.sin(angle3) * row_space
                fourth_pt = [x4, y4]
                first_poly.append(fourth_pt)

                poly = Polygon(first_poly)
                if poly.within(polygon):
                    polys.append(poly)
                elif poly.intersects(polygon):
                    polys.append(poly.intersection(polygon))
                old_poly = first_poly
                first_poly_pt = fourth_pt
            else:
                first_pt = old_poly[1]
                x2 = first_pt[0] + math.cos(angle1) * row_space
                y2 = first_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]

                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]

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

    return polys


def grid_irreg(boundary: Polygon, row_line: LineString | None = None, row_space: float = 2) -> list[Polygon]:
    """
    Create an irregular grid of polygons within a boundary.

    Args:
        boundary: Shapely polygon in UTM coordinates representing the field boundary.
        row_line: Optional line to determine grid rotation angle.
        row_space: Spacing between grid cells in meters.

    Returns:
        List of Shapely polygons representing the grid cells.
    """
    bbox = boundary.bounds
    pxmin, pymin, pxmax, pymax = bbox
    
    angle = 0.0
    if row_line:
        cent = boundary.centroid
        pxmin -= 200
        pymin -= 200
        pxmax += 200
        pymax += 200

        linec = list(row_line.coords)
        linec = unique(np.array(linec))
        maxy = linec[0]
        miny = linec[1]
        angle = math.atan2((maxy[1] - miny[1]), (maxy[0] - miny[0]))

    first_pt_top = (pxmin, pymax)
    last_pt_top = (pxmax, pymax)
    last_pt_side = (pxmin, pymin)

    top_field = LineString([first_pt_top, last_pt_top])
    side_field = LineString([first_pt_top, last_pt_side])
    row_cube = math.ceil(top_field.length) / math.floor(row_space)
    col_cube = math.ceil(side_field.length) / math.floor(row_space)

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
    polys: list[Polygon] = []

    for j in range(1, int(math.ceil(row_cube) + 1)):
        for i in range(1, int(math.ceil(col_cube) + 1)):
            if i == 1:
                first_poly = [first_poly_pt]
                x2 = first_poly_pt[0] + math.cos(angle1) * row_space
                y2 = first_poly_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]
                first_poly.append(second_pt)

                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]
                first_poly.append(third_pt)

                x4 = x3 + math.cos(angle3) * row_space
                y4 = y3 + math.sin(angle3) * row_space
                fourth_pt = [x4, y4]
                first_poly.append(fourth_pt)

                poly = Polygon(first_poly)
                if row_line:
                    poly = rotate(poly, angle, cent, use_radians=True)
                if poly.within(boundary):
                    polys.append(poly)
                elif poly.intersects(boundary):
                    polys.append(poly.intersection(boundary))
                old_poly = first_poly
                first_poly_pt = fourth_pt
            else:
                first_pt = old_poly[1]
                x2 = first_pt[0] + math.cos(angle1) * row_space
                y2 = first_pt[1] + math.sin(angle1) * row_space
                second_pt = [x2, y2]

                x3 = x2 + math.cos(angle2) * row_space
                y3 = y2 + math.sin(angle2) * row_space
                third_pt = [x3, y3]

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

    return polys


def polar_point(origin_point: Point, angle: float, distance: float) -> list[float]:
    """
    Calculate a point from relative polar coordinates.

    Args:
        origin_point: The origin point.
        angle: Angle in degrees.
        distance: Distance from the origin.

    Returns:
        [x, y] coordinates of the calculated point.
    """
    return [
        origin_point.x + math.sin(math.radians(angle)) * distance,
        origin_point.y + math.cos(math.radians(angle)) * distance
    ]


def grid_circ(spacing: float, length: float, center: Point, boundary: Polygon) -> list[Polygon]:
    """
    Create a circular (center-pivot) grid of polygons.

    Args:
        spacing: Spacing between grid cells in meters.
        length: Length of the pivot arm in meters.
        center: Center point of the pivot.
        boundary: Shapely polygon representing the field boundary.

    Returns:
        List of Shapely polygons representing the grid cells.
    """
    radius = spacing
    radius_end = int(math.ceil(length / radius))
    sector_width = 4.0
    polys: list[Polygon] = []

    for x in range(0, int(360.0 / sector_width)):
        for r in range(1, radius_end + 1):
            if r == 1:
                segment_vertices = []
                center_point = polar_point(center, 0, 0)
                segment_vertices.append(center_point)

                first_vertex = polar_point(center, x * sector_width, r * radius)
                segment_vertices.append(first_vertex)

                second_vertex = polar_point(center, x * sector_width + sector_width, r * radius)
                segment_vertices.append(second_vertex)

                segment_vertices.append(center_point)
                old_vertices = segment_vertices

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

                poly = Polygon(new_vertices)
                if poly.within(boundary):
                    polys.append(poly)

                old_vertices = new_vertices

    return polys


def interpolate_raster(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    inp: str,
    outp: str,
    poly: Polygon,
    spacing: float | None = None
) -> tuple[np.ndarray, list[float]]:
    """
    Interpolate point data to a regular raster grid.

    Args:
        x: Array of x coordinates.
        y: Array of y coordinates.
        z: Array of values to interpolate.
        inp: Input CRS.
        outp: Output CRS (should be UTM for accurate distances).
        poly: Boundary polygon in the output CRS.
        spacing: Optional spacing parameter (used if provided).

    Returns:
        Tuple of (interpolated grid as numpy array, bounds [xmin, ymin, xmax, ymax]).
    """
    points = reproject_array(x, y, inp, outp)
    xmin, ymin, xmax, ymax = poly.bounds

    if ((xmax - xmin) <= 200) or ((ymax - ymin) <= 200):
        if spacing is not None and spacing <= 2:
            nx = round((xmax - xmin) * 2)
            ny = round((ymax - ymin) * 2)
        else:
            nx = round((xmax - xmin) / 2)
            ny = round((ymax - ymin) / 2)
    else:
        nx = round((xmax - xmin) / 2)
        ny = round((ymax - ymin) / 2)

    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    gridx, gridy = np.meshgrid(xi, yi)

    gridz = griddata(points, z, (gridx, gridy), method='linear')
    extrapolate_nans(gridx, gridy, gridz)

    return gridz, [xmin, ymin, xmax, ymax]


def get_poly_stats(
    array: np.ndarray,
    polys: list[Polygon],
    bounds: list[float],
    stat: str = 'mean'
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate zonal statistics for grid polygons.

    Args:
        array: numpy array of raster values.
        polys: list of Shapely polygons.
        bounds: bounds of the raster [xmin, ymin, xmax, ymax].
        stat: statistic to calculate (default 'mean').

    Returns:
        Tuple of (numpy array of stats, numpy array of valid polygons).
    """
    from rasterstats import zonal_stats
    
    xmin, ymin, xmax, ymax = bounds
    nrows, ncols = np.shape(array)
    xres = (xmax - xmin) / float(ncols)
    yres = (ymax - ymin) / float(nrows)
    geotransform = (xmin, xres, 0, ymax, 0, -yres)
    array = np.flipud(array)

    stats = []
    valid_polys = []

    for idx, poly in enumerate(polys):
        try:
            st = zonal_stats(poly, array, stats=stat, transform=geotransform)
            stats.append(st)
            valid_polys.append(poly)
        except Exception:
            continue

    stats = np.array([i.get('mean') for j in stats for i in j])
    stats = stats.astype('float')
    boolm = np.isfinite(stats)
    valid_polys = np.array(valid_polys)[boolm]
    stats = stats[boolm]
    return stats, valid_polys


def classify(value: float, breaks: list[float]) -> int:
    """
    Classify a value using Jenks breaks.

    Args:
        value: The value to classify.
        breaks: List of break points from Jenks classification.

    Returns:
        The class index (1-based).
    """
    for i in range(1, len(breaks)):
        if value < breaks[i]:
            return i
    return len(breaks) - 1


def plot_multip(polys: list[Polygon] | Polygon) -> None:
    """
    Plot polygons using geopandas.

    Args:
        polys: Single polygon or list of polygons to plot.
    """
    plt.close('all')
    try:
        gdf = gpd.GeoDataFrame(geometry=list(polys))
    except TypeError:
        gdf = gpd.GeoDataFrame(geometry=[polys])
    gdf.plot(cmap='tab10', figsize=(8, 8))
    plt.show()


def small_polys(multip: MultiPolygon | Polygon, area: float, multip2: MultiPolygon | Polygon) -> MultiPolygon:
    """
    Find small polygons that intersect with larger polygons.

    Args:
        multip: The multipolygon to check.
        area: Minimum area threshold.
        multip2: The reference multipolygon to check intersections against.

    Returns:
        MultiPolygon containing small intersecting polygons.
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


def _s_polys(
    polys: list[Polygon],
    spacing: float,
    *,
    reverse: bool = False,
    step: int = 1,
    half: bool = False
) -> list[Polygon]:
    """
    Move small polygons at zone boundaries into the adjacent zone.

    Args:
        polys: List of Shapely geometries (one per Jenks zone).
        spacing: Grid spacing used to produce polys; area threshold = ceil(spacing**2).
        reverse: Iterate from high index to low (True) or low to high (False).
        step: Index offset to neighbour (1 or 2).
        half: Restrict iteration to first half (forward) or second half (reverse).

    Returns:
        Modified list of polygons.
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


def remove_sliver(poly: Polygon) -> Polygon:
    """
    Remove sliver polygons by buffering.

    Args:
        poly: Input polygon.

    Returns:
        Cleaned polygon.
    """
    eps = .001
    return poly.buffer(eps, 1, join_style=2).buffer(-eps, 1, join_style=2)


def simplify_polys(polys: list[Polygon], spacing: float, smooth: int) -> list[Polygon]:
    """
    Simplify and smooth polygons by merging small slivers.

    Args:
        polys: List of Shapely polygons.
        spacing: Grid spacing used for area threshold.
        smooth: Smoothing factor (1-10).

    Returns:
        List of simplified polygons.
    """
    new_polys = polys[:]
    for sm in range(1, smooth + 1):
        new_polys = _s_polys(new_polys, sm * spacing, reverse=False, step=1, half=True)
        new_polys = _s_polys(new_polys, sm * spacing, reverse=True, step=1, half=True)
    for sm in range(1, smooth + 1):
        new_polys = _s_polys(new_polys, sm * spacing, reverse=False, step=1)
        new_polys = _s_polys(new_polys, sm * spacing, reverse=True, step=1)
    for sm in range(1, smooth + 1):
        new_polys = _s_polys(new_polys, sm * spacing, reverse=False, step=2)
        new_polys = _s_polys(new_polys, sm * spacing, reverse=True, step=2)
    try:
        new_polys = [remove_sliver(poly).simplify(.01) for poly in new_polys]
    except ValueError:
        pass
    return new_polys


def goodness_of_variance_fit(array: np.ndarray, classes: int) -> float:
    """
    Calculate the Goodness of Variance Fit (GVF) for a classification.

    Args:
        array: Array of values to classify.
        classes: Number of classes for Jenks classification.

    Returns:
        GVF value between 0 and 1.
    """
    classes = jenks(array, classes)
    classified = np.array([classify(i, classes) for i in array])
    maxz = max(classified)
    zone_indices = [[idx for idx, val in enumerate(classified) if zone + 1 == val] for zone in range(maxz)]
    sdam = np.sum((array - array.mean()) ** 2)
    array_sort = [np.array([array[index] for index in zone]) for zone in zone_indices]
    sdcm = sum([np.sum((classified - classified.mean()) ** 2) for classified in array_sort])
    gvf = (sdam - sdcm) / sdam
    return gvf


def gvf_array(stats: np.ndarray, max_class: int) -> list[float]:
    """
    Calculate GVF values for 2 to max_class classes.

    Args:
        stats: Array of polygon statistics.
        max_class: Maximum number of classes to evaluate.

    Returns:
        List of GVF values (rounded to 2 decimal places).
    """
    n_unique = len(np.unique(stats))
    gvf_arr = []
    for i in range(2, min(max_class, n_unique) + 1):
        gvf = goodness_of_variance_fit(stats, i)
        gvf_arr.append(round(gvf, 2))
        if gvf >= .9:
            break
    return gvf_arr


def optimal_gfv(array_of_gvf_values: list[float]) -> tuple[float, int]:
    """
    Find the optimal number of zones based on GVF.

    Args:
        array_of_gvf_values: List of GVF values for different class counts.

    Returns:
        Tuple of (GVF value, number of classes).
    """
    for idx, val in enumerate(array_of_gvf_values):
        if val > .8:
            return val, idx + 2
    return array_of_gvf_values[-1], len(array_of_gvf_values) + 1


def gvf_json(array_of_gvf_values: list[float]) -> list[list[int | float]]:
    """
    Convert GVF array to JSON-suitable format.

    Args:
        array_of_gvf_values: List of GVF values.

    Returns:
        List of [num_classes, gvf_value] pairs.
    """
    return [[idx + 2, val] for idx, val in enumerate(array_of_gvf_values)]


def get_poly_jenks(
    poly_stats: np.ndarray,
    polys: np.ndarray,
    classes: int
) -> tuple[list[Polygon], list[str]]:
    """
    Classify polygons using Jenks Natural Breaks.

    Args:
        poly_stats: Array of statistics for each polygon.
        polys: Array of Shapely polygons.
        classes: Number of desired classes.

    Returns:
        Tuple of (list of merged polygons, list of class break labels).
    """
    classes = min(classes, len(np.unique(poly_stats)))
    classes = jenks(poly_stats, classes)
    classified = np.array([classify(i, classes) for i in poly_stats])
    maxz = max(classified)
    zone_indices = [[idx for idx, val in enumerate(classified) if zone + 1 == val] for zone in range(maxz)]
    poly_sort = [[polys[index] for index in zone] for zone in zone_indices]
    poly_comb = [unary_union(polyz) for polyz in poly_sort]

    classes = [round(i, 1) for i in classes]
    class_breaks = []
    for idx, val in enumerate(classes):
        try:
            class_breaks.append(str(val) + ' - ' + str(classes[idx + 1]))
        except IndexError:
            break

    return poly_comb, class_breaks


def zones_to_geojson_fc(
    zones: list[Polygon],
    class_breaks: list[str],
    inp: str | None = None,
    outp: str = 'epsg:4326'
) -> dict:
    """
    Convert zones to GeoJSON FeatureCollection.

    Args:
        zones: List of Shapely polygons.
        class_breaks: List of class break labels.
        inp: Input CRS (optional).
        outp: Output CRS (default 'epsg:4326').

    Returns:
        GeoJSON FeatureCollection as dict.
    """
    if inp:
        zones = reproject_multip(zones, in_projection=inp, out_projection=outp)

    features = [
        geojson.Feature(
            geometry=mapping(zones[idx]),
            id=idx,
            properties={"zone": idx + 1, "values": val}
        )
        for idx, val in enumerate(class_breaks)
    ]

    crs = {
        "type": "name",
        "properties": {
            "name": "EPSG:4326"
        }
    }

    feature_coll = geojson.FeatureCollection(features, crs=crs)
    return geojson.loads(geojson.dumps(feature_coll))


def zones_to_geojson_fc_gdf(
    zones: list[Polygon],
    class_breaks: list[str],
    inp: str | None = None,
    outp: str = 'epsg:4326'
) -> dict:
    """
    Convert zones to GeoJSON FeatureCollection using geopandas.

    Args:
        zones: List of Shapely polygons.
        class_breaks: List of class break labels.
        inp: Input CRS (optional).
        outp: Output CRS (default 'epsg:4326').

    Returns:
        GeoJSON FeatureCollection as dict.
    """
    gdf = gpd.GeoDataFrame({
        'zone': range(1, len(zones) + 1),
        'values': class_breaks,
        'geometry': zones
    })
    
    if inp:
        gdf = gdf.set_crs(inp, allow_override=True).to_crs(outp)
    
    return geojson.loads(gdf.to_json())


def json_legend(class_breaks: list[str]) -> list[list[str]]:
    """
    Create legend data with colors for frontend display.

    Args:
        class_breaks: List of class break labels.

    Returns:
        List of [color_hex, label] pairs.
    """
    num_classes = len(class_breaks)
    if num_classes == 2:
        colors = ['#0000FF', '#FF0000']
        return [[colors[i], class_breaks[i]] for i in range(num_classes)]
    else:
        cmap = mpl.colormaps['RdBu_r'].resampled(num_classes)
        hex_colors = [mcolors.to_hex(cmap(i)) for i in range(num_classes)]
        return [[hex_colors[i], class_breaks[i]] for i in range(num_classes)]


def json_color_codes(num_classes: int) -> tuple[dict, dict]:
    """
    Create color codes for OpenLayers display.

    Args:
        num_classes: Number of classes.

    Returns:
        Tuple of (default color codes, select color codes) dictionaries.
    """
    if num_classes == 2:
        colors = ['#0000FF', '#FF0000']
        default = {key + 1: {'fillColor': value} for key, value in enumerate(colors)}
        select = {key + 1: {'fillColor': value, 'strokeColor': value} for key, value in enumerate(colors)}
        return default, select
    else:
        cmap = mpl.colormaps['RdBu_r'].resampled(num_classes)
        hex_colors = [mcolors.to_hex(cmap(i)) for i in range(num_classes)]
        default = {key + 1: {'fillColor': value} for key, value in enumerate(hex_colors)}
        select = {key + 1: {'fillColor': value, 'strokeColor': value} for key, value in enumerate(hex_colors)}
        return default, select


def create_geotiff(
    filename: str,
    array: np.ndarray,
    bounds: list[float],
    pyproj_object: pyproj.CRS
) -> None:
    """
    Create a GeoTIFF file from a numpy array.

    Args:
        filename: Output filename.
        array: 2D numpy array of values.
        bounds: [xmin, ymin, xmax, ymax].
        pyproj_object: pyproj CRS object for the output.
    """
    nrows, ncols = array.shape
    xmin, ymin, xmax, ymax = bounds
    xres = (xmax - xmin) / float(ncols)
    yres = (ymax - ymin) / float(nrows)
    geotransform = (xmin, xres, 0, ymin, 0, yres)
    
    output_raster = gdal.GetDriverByName('GTiff').Create(
        filename, ncols, nrows, 1,
        gdal.GDT_Float32, ['TFW=YES', 'COMPRESS=PACKBITS']
    )
    output_raster.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromProj4(pyproj_object.to_proj4())
    output_raster.SetProjection(srs.ExportToWkt())
    output_raster.GetRasterBand(1).WriteArray(array)
    output_raster = None


def asshape(geoj: dict) -> Polygon:
    """
    Convert GeoJSON to Shapely geometry.

    Args:
        geoj: GeoJSON geometry dict.

    Returns:
        Shapely geometry.
    """
    return shape(geoj)
