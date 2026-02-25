"""
Core geospatial library for agricultural management zone generation.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pyproj
from scipy.interpolate import griddata
import geopandas as gpd
from shapely.geometry import Polygon, shape
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
    in_projection: str = 'epsg:4326',
    out_projection: str = 'epsg:3857'
) -> dict:
    """Create a convex-hull polygon GeoJSON boundary from x and y coordinate arrays."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    points = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=in_projection)
    hull = gpd.GeoSeries(
        [points.union_all().convex_hull],
        crs=in_projection,
    ).to_crs(out_projection).iloc[0]

    return hull.__geo_interface__


def reproject_poly(
    obj: Any,
    in_projection: str = 'epsg:3857',
    out_projection: str = 'epsg:4326'
) -> Polygon:
    """Reproject a polygon from one CRS to another."""
    if isinstance(obj, dict):
        if 'coordinates' in obj and 'type' in obj:
            poly = shape(obj)
        else:
            try:
                poly = shape(obj['geometry'])
            except KeyError:
                poly = shape(obj)
    elif isinstance(obj, str):
        poly = shape(json.loads(obj))
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
        gdf = gpd.GeoDataFrame(geometry=[xy], crs='epsg:4326')
    else:
        gdf = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([xy[0]], [xy[1]]),
            crs='epsg:4326',
        )
    return gdf.estimate_utm_crs()


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


def gvf_array(stats: np.ndarray, max_class: int) -> list[float]:
    """Calculate GVF values for 2 to max_class classes using vectorized numpy."""
    n_unique = len(np.unique(stats))
    sdam = np.sum((stats - stats.mean()) ** 2)
    if sdam == 0:
        return [0.0]

    gvf_arr = []
    for i in range(2, min(max_class, n_unique) + 1):
        breaks = jenks(stats, i)
        classified = np.digitize(stats, breaks)
        classified = np.clip(classified, 1, i)
        sdcm = sum(
            np.sum((group - group.mean()) ** 2)
            for cls in range(1, i + 1)
            for group in [stats[classified == cls]]
            if len(group) > 0
        )
        gvf = (sdam - sdcm) / sdam
        gvf_arr.append(round(gvf, 2))
        if gvf >= 0.9:
            break
    return gvf_arr


def gvf_json(array_of_gvf_values: list[float]) -> list[list[int | float]]:
    """Convert GVF array to JSON-suitable format."""
    return [[idx + 2, val] for idx, val in enumerate(array_of_gvf_values)]


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

    # Collect all polygonized features into a GeoDataFrame and batch-clip
    features = []
    layer.ResetReading()
    for feature in layer:
        geom = feature.GetGeometryRef()
        class_label = feature.GetFieldAsInteger("DN")
        if class_label == 0:
            continue
        geom_json = geom.ExportToJson()
        shapely_geom = shape(json.loads(geom_json))
        features.append({'zone': class_label, 'geometry': shapely_geom})

    ds = None
    vector_ds = None

    if not features:
        raise ValueError("No valid zone geometries after polygonization")

    gdf_raw = gpd.GeoDataFrame(features, crs=utm_crs)
    gdf_clipped = gpd.clip(gdf_raw, boundary_utm)
    gdf_clipped = gdf_clipped[~gdf_clipped.geometry.is_empty & gdf_clipped.geometry.notna()]

    # Explode any MultiPolygons to individual Polygon rows
    gdf_clipped = gdf_clipped.explode(index_parts=False).reset_index(drop=True)
    gdf_clipped = gdf_clipped[gdf_clipped.geometry.type == 'Polygon']

    if gdf_clipped.empty:
        raise ValueError("No valid zone geometries after clipping")

    gdf_wgs84 = gdf_clipped.to_crs('epsg:4326')
    return gdf_wgs84.sort_values('zone').reset_index(drop=True)
