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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
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

# ── Spatial Clustering ───────────────────────────────────────────────────────
# Higher weight makes zones more contiguous/compact but less sensitive to yield.
# Lower weight (e.g. 0.1) stays closer to the yield values.
SPATIAL_WEIGHT = 0.4 

# ── Outlier Suppression ───────────────────────────────────────────────────────
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

    points_coords = np.column_stack([x, y])
    hull = ConvexHull(points_coords)
    hull_points = points_coords[hull.vertices]
    
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
    
    lin_interp = LinearNDInterpolator(points, z)
    gridz = lin_interp(gridx, gridy)
    
    if np.isnan(gridz).any():
        near_interp = NearestNDInterpolator(points, z)
        nan_mask = np.isnan(gridz)
        gridz[nan_mask] = near_interp(gridx[nan_mask], gridy[nan_mask])

    mask = features.geometry_mask([poly], out_shape=(ny, nx), 
                                  transform=from_bounds(xmin, ymin, xmax, ymax, nx, ny),
                                  invert=True)
    gridz[~mask] = np.nan

    return gridz, [xmin, ymin, xmax, ymax]


def gvf_array(stats: np.ndarray, max_class: int) -> list[float]:
    """Calculate GVF values for 2 to max_class classes using sampled Jenks."""
    valid_stats = stats[~np.isnan(stats)]
    if len(valid_stats) == 0:
        return [0.0]

    low, high = np.percentile(valid_stats, [OUTLIER_PERCENTILE_LOW, OUTLIER_PERCENTILE_HIGH])
    valid_stats = np.clip(valid_stats, low, high)

    n_unique = len(np.unique(valid_stats))
    sdam = np.sum((valid_stats - valid_stats.mean()) ** 2)
    if sdam == 0:
        return [0.0]

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
    num_classes: int,
    bounds: list[float]
) -> tuple[np.ndarray, list[str]]:
    """
    Classify raster pixels using Spatial-Spectral K-Means clustering.
    Includes X, Y, and Value in the classification space.
    """
    # ── Pre-Classification Smoothing ──
    array_smoothed = median_filter(array, size=SMOOTHING_KERNEL_SIZE)
    
    ny, nx = array.shape
    xmin, ymin, xmax, ymax = bounds
    
    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    gridx, gridy = np.meshgrid(xi, yi)

    valid_mask = ~np.isnan(array_smoothed)
    z_vals = array_smoothed[valid_mask]
    x_vals = gridx[valid_mask]
    y_vals = gridy[valid_mask]

    if len(z_vals) == 0:
        raise ValueError("No valid values in raster for classification")

    # ── Outlier Suppression ──
    low, high = np.percentile(z_vals, [OUTLIER_PERCENTILE_LOW, OUTLIER_PERCENTILE_HIGH])
    z_clipped = np.clip(z_vals, low, high)

    # ── Feature Vector Preparation ──
    # [X, Y, Z]
    features_raw = np.column_stack([x_vals, y_vals, z_clipped])
    
    # Scale features to comparable ranges
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features_raw)
    
    # Apply Spatial Weighting
    # X and Y are indices 0 and 1. We multiply them by weight.
    scaled[:, 0:2] *= SPATIAL_WEIGHT

    # ── K-Means Clustering ──
    # Since we use spatial coordinates, Jenks (1D only) is no longer suitable.
    # K-Means works perfectly for this multi-dimensional space.
    kmeans = KMeans(n_clusters=num_classes, n_init=10, random_state=42)
    labels = kmeans.fit_predict(scaled)
    
    # Order labels by mean Yield (Z) so Zone 1 is always lowest yield
    centers_orig_scale = scaler.inverse_transform(kmeans.cluster_centers_)
    z_centers = centers_orig_scale[:, 2]
    rank_map = {old_label: new_rank + 1 for new_rank, old_label in enumerate(np.argsort(z_centers))}
    
    ranked_labels = np.array([rank_map[l] for l in labels], dtype=np.int32)

    classified = np.zeros(array.shape, dtype=np.int32)
    classified.flat[valid_mask.ravel()] = ranked_labels
    
    # ── Final Smoothing ──
    classified = median_filter(classified, size=SMOOTHING_KERNEL_SIZE)

    # ── Determine Natural Breaks for Legend ──
    # Even though we used K-Means, users expect Jenks-like legend ranges.
    # We find the min/max of the resulting clusters.
    class_break_labels = []
    for cls in range(1, num_classes + 1):
        cluster_data = z_vals[ranked_labels == cls]
        if len(cluster_data) > 0:
            c_min, c_max = round(cluster_data.min(), 1), round(cluster_data.max(), 1)
            class_break_labels.append(f"{c_min} - {c_max}")
        else:
            class_break_labels.append("N/A")

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

    features_list = []
    layer.ResetReading()
    for feature in layer:
        geom = feature.GetGeometryRef()
        class_label = feature.GetFieldAsInteger("DN")
        if class_label == 0:
            continue
        geom_json = geom.ExportToJson()
        shapely_geom = shape(json.loads(geom_json))
        features_list.append({'zone': class_label, 'geometry': shapely_geom})

    ds = None
    vector_ds = None

    if not features_list:
        raise ValueError("No valid zone geometries after polygonization")

    gdf_raw = gpd.GeoDataFrame(features_list, crs=utm_crs)
    gdf_clipped = gpd.clip(gdf_raw, boundary_utm)
    gdf_clipped = gdf_clipped[~gdf_clipped.geometry.is_empty & gdf_clipped.geometry.notna()]

    gdf_clipped = gdf_clipped.explode(index_parts=False).reset_index(drop=True)
    gdf_clipped = gdf_clipped[gdf_clipped.geometry.type == 'Polygon']

    if gdf_clipped.empty:
        raise ValueError("No valid zone geometries after clipping")

    gdf_wgs84 = gdf_clipped.to_crs(DEFAULT_CRS)
    return gdf_wgs84.sort_values('zone').reset_index(drop=True)
