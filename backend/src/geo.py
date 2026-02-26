"""
Core geospatial library for agricultural management zone generation.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pyproj
import geopandas as gpd
import matplotlib as mpl
import matplotlib.colors as mcolors
from shapely.geometry import Polygon, shape
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.spatial import ConvexHull
from scipy.ndimage import median_filter
from jenkspy import jenks_breaks as jenks
from osgeo import gdal, osr, ogr
from rasterio import features
from rasterio.transform import from_bounds

gdal.UseExceptions()

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_CRS = 'epsg:4326'
WEB_MERCATOR_CRS = 'epsg:3857'

JENKS_SAMPLE_SIZE = 10000
GVF_THRESHOLD = 0.95
SMOOTHING_KERNEL_SIZE = 3
RESOLUTION_STEP = 0.25

# ── Outlier Suppression ───────────────────────────────────────────────────────
# Clipping to these percentiles ensures extreme spikes don't skew the zones.
OUTLIER_PERCENTILE_LOW = 2
OUTLIER_PERCENTILE_HIGH = 98

# ── Processing Profiles ───────────────────────────────────────────────────────

PROFILES = {
    'fast': {
        'max_points': 1000,
        'target_pixels': 250,
        'min_res': 1.0,
        'gvf_samples': 5000,
    },
    'high': {
        'max_points': 10000,
        'target_pixels': 1500,
        'min_res': 0.5,
        'gvf_samples': 50000,
    }
}

def get_active_profile():
    name = os.environ.get('EZZONE_PROFILE', 'high').lower()
    return PROFILES.get(name, PROFILES['high'])

# ── Functions ────────────────────────────────────────────────────────────────

def bound_json(
    x: np.ndarray,
    y: np.ndarray,
    in_projection: str = DEFAULT_CRS,
    out_projection: str = WEB_MERCATOR_CRS
) -> dict:
    """Create a convex-hull polygon GeoJSON boundary from x and y coordinate arrays."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # Use scipy for extremely fast convex hull calculation on raw points
    points_coords = np.column_stack([x, y])
    hull = ConvexHull(points_coords)
    hull_points = points_coords[hull.vertices]
    
    # Create the polygon and reproject
    poly = Polygon(hull_points)
    hull_gs = gpd.GeoSeries([poly], crs=in_projection).to_crs(out_projection)

    return hull_gs.iloc[0].__geo_interface__


def reproject_poly(
    obj: Any,
    in_projection: str = WEB_MERCATOR_CRS,
    out_projection: str = DEFAULT_CRS
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
        gdf = gpd.GeoDataFrame(geometry=[xy], crs=DEFAULT_CRS)
    else:
        gdf = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([xy[0]], [xy[1]]),
            crs=DEFAULT_CRS,
        )
    return gdf.estimate_utm_crs()


def interpolate_raster(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    inp: str,
    outp: str,
    poly: Polygon
) -> tuple[np.ndarray, list[float]]:
    """Interpolate point data to a regular raster grid with adaptive resolution and masking."""
    profile = get_active_profile()
    target_pixels = profile['target_pixels']
    min_res = profile['min_res']

    points = reproject_array(x, y, inp, outp)
    xmin, ymin, xmax, ymax = poly.bounds

    width = xmax - xmin
    height = ymax - ymin
    
    raw_res = max(min_res, max(width, height) / target_pixels)
    resolution = np.ceil(raw_res / RESOLUTION_STEP) * RESOLUTION_STEP

    nx = max(2, round(width / resolution))
    ny = max(2, round(height / resolution))

    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    gridx, gridy = np.meshgrid(xi, yi)
    
    # Fast interpolation
    lin_interp = LinearNDInterpolator(points, z)
    gridz = lin_interp(gridx, gridy)
    
    # Fill Nans using nearest neighbor (Extrapolation)
    if np.isnan(gridz).any():
        near_interp = NearestNDInterpolator(points, z)
        nan_mask = np.isnan(gridz)
        gridz[nan_mask] = near_interp(gridx[nan_mask], gridy[nan_mask])

    # ── Masking ──
    # Ensure pixels outside the boundary are NaN so they don't influence classification
    mask = features.geometry_mask([poly], out_shape=(ny, nx), 
                                  transform=from_bounds(xmin, ymin, xmax, ymax, nx, ny),
                                  invert=True)
    gridz[~mask] = np.nan

    return gridz, [xmin, ymin, xmax, ymax]


def gvf_array(stats: np.ndarray, max_class: int) -> list[float]:
    """Calculate GVF values for 2 to max_class classes using sampled Jenks."""
    # Filter to valid (inside boundary) values only
    valid_stats = stats[~np.isnan(stats)]
    if len(valid_stats) == 0:
        return [0.0]

    # ── Outlier Suppression ──
    low, high = np.percentile(valid_stats, [OUTLIER_PERCENTILE_LOW, OUTLIER_PERCENTILE_HIGH])
    valid_stats = np.clip(valid_stats, low, high)

    n_unique = len(np.unique(valid_stats))
    sdam = np.sum((valid_stats - valid_stats.mean()) ** 2)
    if sdam == 0:
        return [0.0]

    # Sample for GVF to keep it fast
    if len(valid_stats) > JENKS_SAMPLE_SIZE:
        sampled = np.random.choice(valid_stats, JENKS_SAMPLE_SIZE, replace=False)
        sampled_sdam = np.sum((sampled - sampled.mean()) ** 2)
    else:
        sampled = valid_stats
        sampled_sdam = sdam

    gvf_arr = []
    for i in range(2, min(max_class, n_unique) + 1):
        breaks = jenks(sampled, i)
        classified = np.digitize(sampled, breaks)
        classified = np.clip(classified, 1, i)
        sdcm = sum(
            np.sum((group - group.mean()) ** 2)
            for cls in range(1, i + 1)
            for group in [sampled[classified == cls]]
            if len(group) > 0
        )
        gvf = (sampled_sdam - sdcm) / sampled_sdam
        gvf_arr.append(round(gvf, 3))
        if gvf >= GVF_THRESHOLD:
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
    """Classify raster pixels using Jenks Natural Breaks on a masked dataset."""
    # ── Smoothing Step First ──
    # Smooth before classification to remove interpolation noise
    array_smoothed = median_filter(array, size=SMOOTHING_KERNEL_SIZE)
    
    flat = array_smoothed.flatten()
    valid_mask = ~np.isnan(flat)
    valid_values = flat[valid_mask]

    if len(valid_values) == 0:
        raise ValueError("No valid values in raster for classification")

    # ── Outlier Suppression ──
    low, high = np.percentile(valid_values, [OUTLIER_PERCENTILE_LOW, OUTLIER_PERCENTILE_HIGH])
    valid_values = np.clip(valid_values, low, high)

    # Sample for calculating breaks (10k is robust for 1D distribution estimation)
    if len(valid_values) > JENKS_SAMPLE_SIZE:
        sampled_for_breaks = np.random.choice(valid_values, JENKS_SAMPLE_SIZE, replace=False)
    else:
        sampled_for_breaks = valid_values

    actual_classes = min(num_classes, len(np.unique(sampled_for_breaks)))
    breaks = jenks(sampled_for_breaks, actual_classes)

    # Use NumPy's vectorized digitize to apply the breaks to the FULL dataset
    valid_classification = np.digitize(valid_values, breaks)
    valid_classification = np.clip(valid_classification, 1, actual_classes)

    classified = np.zeros(array.shape, dtype=np.int32)
    classified.flat[valid_mask] = valid_classification
    
    # Format legend labels using the actual min/max of the masked data
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

    gdf_wgs84 = gdf_clipped.to_crs(DEFAULT_CRS)
    return gdf_wgs84.sort_values('zone').reset_index(drop=True)
