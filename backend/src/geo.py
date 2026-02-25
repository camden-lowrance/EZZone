"""
Core geospatial library for agricultural management zone generation.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pyproj
from scipy.interpolate import griddata
import geopandas as gpd
from shapely.geometry import Polygon, shape, mapping, MultiPoint, MultiPolygon
import geojson
from jenkspy import jenks_breaks as jenks
import matplotlib as mpl
import matplotlib.colors as mcolors
from osgeo import gdal
from osgeo import osr
from osgeo import ogr

gdal.UseExceptions()


def extrapolate_nans(x: np.ndarray, y: np.ndarray, v: np.ndarray) -> np.ndarray | None:
    """Extrapolate NaN values in a grid using nearest neighbor interpolation."""
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


def bound_json(
    x: np.ndarray,
    y: np.ndarray,
    geometry_type: int = 3,
    in_projection: str = 'epsg:4326',
    out_projection: str = 'epsg:3857'
) -> dict:
    """Create a convex-hull polygon GeoJSON boundary from x and y coordinate arrays."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    crs = {"type": "name", "properties": {"name": out_projection}}

    transformer = pyproj.Transformer.from_crs(in_projection, out_projection, always_xy=True)
    points = MultiPoint(np.column_stack([x, y]))
    hull = mapping(points.convex_hull)
    jfeat = []
    for ring in hull['coordinates']:
        for coord in ring:
            jfeat.append(list(transformer.transform(coord[0], coord[1])))
    geoj = geojson.Polygon([jfeat], crs=crs)

    return geojson.loads(geojson.dumps(geoj))


def reproject_poly(
    obj: Any,
    in_projection: str = 'epsg:3857',
    out_projection: str = 'epsg:4326'
) -> Polygon:
    """Reproject a polygon from one CRS to another."""
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


def reproject_array(x: np.ndarray, y: np.ndarray, inp: str, outp: str) -> np.ndarray:
    """Reproject arrays of x and y coordinates."""
    transformer = pyproj.Transformer.from_crs(inp, outp, always_xy=True)
    xs, ys = transformer.transform(x, y)
    return np.column_stack([xs, ys])


def utmzone(xy: tuple | Polygon) -> pyproj.CRS:
    """Get the UTM CRS for the given coordinates."""
    if isinstance(xy, Polygon):
        xy = xy.exterior.coords[0]
    
    zone_num = int(math.floor((xy[0] + 180) / 6) + 1)
    south = xy[1] < 0
    proj_str = f'+proj=utm +zone={zone_num} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    if south:
        proj_str += ' +south'
    
    return pyproj.CRS.from_proj4(proj_str)


DEFAULT_RESOLUTION = 5.0

def interpolate_raster(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    inp: str,
    outp: str,
    poly: Polygon
) -> tuple[np.ndarray, list[float]]:
    """Interpolate point data to a regular raster grid."""
    points = reproject_array(x, y, inp, outp)
    xmin, ymin, xmax, ymax = poly.bounds
    
    width = xmax - xmin
    height = ymax - ymin
    resolution = DEFAULT_RESOLUTION
    
    nx = max(2, round(width / resolution))
    ny = max(2, round(height / resolution))

    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    gridx, gridy = np.meshgrid(xi, yi)

    gridz = griddata(points, z, (gridx, gridy), method='linear')
    extrapolate_nans(gridx, gridy, gridz)

    return gridz, [xmin, ymin, xmax, ymax]


def classify(value: float, breaks: list[float]) -> int:
    """Classify a value using Jenks breaks."""
    for i in range(1, len(breaks)):
        if value < breaks[i]:
            return i
    return len(breaks) - 1


def goodness_of_variance_fit(array: np.ndarray, classes: int) -> float:
    """Calculate the Goodness of Variance Fit (GVF) for a classification."""
    classes_vals = jenks(array, classes)
    classified = np.array([classify(i, classes_vals) for i in array])
    maxz = max(classified)
    zone_indices = [[idx for idx, val in enumerate(classified) if zone + 1 == val] for zone in range(maxz)]
    sdam = np.sum((array - array.mean()) ** 2)
    array_sort = [np.array([array[index] for index in zone]) for zone in zone_indices]
    sdcm = sum([np.sum((zone_vals - zone_vals.mean()) ** 2) for zone_vals in array_sort if len(zone_vals) > 0])
    gvf = (sdam - sdcm) / sdam if sdam > 0 else 0
    return gvf


def gvf_array(stats: np.ndarray, max_class: int) -> list[float]:
    """Calculate GVF values for 2 to max_class classes."""
    n_unique = len(np.unique(stats))
    gvf_arr = []
    for i in range(2, min(max_class, n_unique) + 1):
        gvf = goodness_of_variance_fit(stats, i)
        gvf_arr.append(round(gvf, 2))
        if gvf >= .9:
            break
    return gvf_arr


def gvf_json(array_of_gvf_values: list[float]) -> list[list[int | float]]:
    """Convert GVF array to JSON-suitable format."""
    return [[idx + 2, val] for idx, val in enumerate(array_of_gvf_values)]


def zones_to_geojson_fc_gdf(
    zones: list[Polygon],
    class_breaks: list[str],
    inp: str | None = None,
    outp: str = 'epsg:4326'
) -> dict:
    """Convert zones to GeoJSON FeatureCollection using geopandas."""
    gdf = gpd.GeoDataFrame({
        'zone': range(1, len(zones) + 1),
        'values': class_breaks,
        'geometry': zones
    })

    if inp:
        gdf = gdf.set_crs(inp, allow_override=True).to_crs(outp)

    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    return geojson.loads(gdf.to_json())


def json_legend(class_breaks: list[str]) -> list[list[str]]:
    """Create legend data with colors for frontend display."""
    num_classes = len(class_breaks)
    if num_classes == 2:
        colors = ['#0000FF', '#FF0000']
        return [[colors[i], class_breaks[i]] for i in range(num_classes)]
    else:
        cmap = mpl.colormaps['RdBu_r'].resampled(num_classes)
        hex_colors = [mcolors.to_hex(cmap(i)) for i in range(num_classes)]
        return [[hex_colors[i], class_breaks[i]] for i in range(num_classes)]


def json_color_codes(num_classes: int) -> tuple[dict, dict]:
    """Create color codes for OpenLayers display."""
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


def classify_raster(
    array: np.ndarray,
    num_classes: int
) -> tuple[np.ndarray, list[str]]:
    """Classify raster pixels directly using Jenks Natural Breaks."""
    flat = array.flatten()
    valid_mask = ~np.isnan(flat)
    valid_values = flat[valid_mask]
    
    if len(valid_values) == 0:
        raise ValueError("No valid values in raster for classification")
    
    actual_classes = min(num_classes, len(np.unique(valid_values)))
    breaks = jenks(valid_values, actual_classes)
    
    valid_classification = np.digitize(valid_values, breaks)
    valid_classification = np.clip(valid_classification, 1, actual_classes)
    
    classified = np.zeros(array.shape, dtype=np.int32)
    classified.flat[valid_mask] = valid_classification
    
    breaks = [round(b, 1) for b in breaks]
    class_break_labels = []
    for idx in range(len(breaks) - 1):
        class_break_labels.append(f"{breaks[idx]} - {breaks[idx + 1]}")
    
    return classified, class_break_labels


def polygonize_classes_fast(
    classified: np.ndarray,
    bounds: list[float],
    boundary_utm: Polygon,
    utm_crs: pyproj.CRS
) -> gpd.GeoDataFrame:
    """Fast polygonization using GDAL directly with numpy array."""
    xmin, ymin, xmax, ymax = bounds
    nrows, ncols = classified.shape
    
    xres = (xmax - xmin) / ncols
    yres = (ymax - ymin) / nrows
    geotransform = (xmin, xres, 0, ymax, 0, -yres)
    
    driver = gdal.GetDriverByName('MEM')
    ds = driver.Create('', ncols, nrows, 1, gdal.GDT_Byte)
    ds.SetGeoTransform(geotransform)
    ds.SetProjection(utm_crs.to_wkt())
    
    band = ds.GetRasterBand(1)
    band.WriteArray(np.flipud(classified.astype(np.uint8)))
    
    mem_driver = ogr.GetDriverByName('MEM')
    vector_ds = mem_driver.CreateDataSource('mem_data')
    
    srs = osr.SpatialReference()
    srs.ImportFromWkt(utm_crs.to_wkt())
    layer = vector_ds.CreateLayer('polygons', srs=srs, geom_type=ogr.wkbMultiPolygon)
    
    field_defn = ogr.FieldDefn("DN", ogr.OFTInteger)
    layer.CreateField(field_defn)
    field_index = layer.GetLayerDefn().GetFieldIndex("DN")
    
    gdal.Polygonize(band, None, layer, field_index, [], callback=None)
    
    features = []
    layer.ResetReading()
    
    for feature in layer:
        geom = feature.GetGeometryRef()
        class_label = feature.GetFieldAsInteger("DN")
        if class_label == 0: continue
            
        geom_json = geom.ExportToJson()
        shapely_geom = shape(geojson.loads(geom_json))
        
        if shapely_geom.intersects(boundary_utm):
            clipped = shapely_geom.intersection(boundary_utm)
            if not clipped.is_empty:
                if isinstance(clipped, MultiPolygon):
                    for p in clipped.geoms:
                        if not p.is_empty:
                            features.append({'zone': class_label, 'geometry': p})
                elif isinstance(clipped, Polygon) and not clipped.is_empty:
                    features.append({'zone': class_label, 'geometry': clipped})
    
    ds = None
    vector_ds = None
    
    if not features:
        raise ValueError("No valid zone geometries after polygonization")
    
    gdf_utm = gpd.GeoDataFrame(features, crs=utm_crs)
    gdf_wgs84 = gdf_utm.to_crs('epsg:4326')
    return gdf_wgs84.sort_values('zone').reset_index(drop=True)
