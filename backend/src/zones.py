"""
Simplified Zone generation service for agricultural management.
"""

from __future__ import annotations

import json
import os
import io
import zipfile
import tempfile
from typing import Any

import numpy as np
import geopandas as gpd
from shapely.geometry import shape

from .geo import (
    bound_json,
    reproject_poly,
    utmzone,
    interpolate_raster,
    classify_raster,
    polygonize_classes_fast,
    gvf_array,
    gvf_json,
    json_legend,
    get_active_profile
)


def _extract_geometry(boundary: dict) -> dict:
    """Extract a raw geometry dict from various GeoJSON structures."""
    if boundary.get('type') == 'FeatureCollection':
        return boundary['features'][0]['geometry']
    if boundary.get('type') == 'Feature':
        return boundary['geometry']
    if 'geometry' in boundary and isinstance(boundary['geometry'], dict):
        return boundary['geometry']
    return boundary  # raw geometry (Polygon, etc.)


def get_metadata(
    x: np.ndarray,
    y: np.ndarray,
    in_projection: str = 'epsg:4326',
    boundary_geojson: str | dict | None = None
) -> dict:
    """Return a WGS84 boundary and point count without heavy processing."""
    if boundary_geojson is None:
        boundary = bound_json(x, y, in_projection=in_projection, out_projection='epsg:4326')
    else:
        boundary = json.loads(boundary_geojson) if isinstance(boundary_geojson, str) else boundary_geojson

    return {
        'boundary': boundary,
        'num_points': len(x)
    }


def generate_zones(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    in_projection: str = 'epsg:4326',
    boundary_geojson: str | dict | None = None,
    num_classes: int = 3,
    z_col: str = 'value',
) -> dict[str, Any]:
    """
    Generate zones from point data; boundary GeoJSON is always WGS84.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)

    # Create or use boundary (always irregular/convex hull now)
    if boundary_geojson is None:
        boundary = bound_json(x, y, in_projection=in_projection, out_projection='epsg:4326')
    else:
        boundary = json.loads(boundary_geojson) if isinstance(boundary_geojson, str) else boundary_geojson

    boundary_geom = _extract_geometry(boundary)

    # API and map boundaries are WGS84, independent of the uploaded points' CRS.
    boundary_wgs84 = reproject_poly(shape(boundary_geom), in_projection='epsg:4326', out_projection='epsg:4326')
    utm_crs = utmzone(boundary_wgs84)
    boundary_utm = reproject_poly(boundary_wgs84, in_projection='epsg:4326', out_projection=utm_crs)

    # Interpolate point data to raster
    array, raster_bounds = interpolate_raster(x, y, z, in_projection, utm_crs, boundary_utm)

    # Compute GVF for 2-8 classes based on sampled pixel values (to speed up "elbow" detection)
    flat_values = array.ravel()
    valid_values = flat_values[~np.isnan(flat_values)]
    
    # Sample based on active profile
    profile = get_active_profile()
    max_gvf = profile['gvf_samples']
    if len(valid_values) > max_gvf:
        sampled_values = np.random.choice(valid_values, max_gvf, replace=False)
    else:
        sampled_values = valid_values
    
    gvf_arr = gvf_array(sampled_values, 8)
    # Release the full-raster sample before classification allocates its arrays.
    del flat_values, valid_values, sampled_values

    # Classify raster pixels and polygonize
    classified, class_breaks, class_ranges = classify_raster(array, num_classes)
    gdf = polygonize_classes_fast(classified, raster_bounds, boundary_utm, utm_crs)

    # Embed per-zone value ranges as columns before converting to GeoJSON
    range_min = {cls: rng[0] for cls, rng in enumerate(class_ranges, start=1)}
    range_max = {cls: rng[1] for cls, rng in enumerate(class_ranges, start=1)}
    gdf[f"{z_col}_min"] = gdf['zone'].map(range_min)
    gdf[f"{z_col}_max"] = gdf['zone'].map(range_max)

    zones_geojson = json.loads(gdf.to_json())
    legend = json_legend(class_breaks)

    return {
        'zones': zones_geojson,
        'gvf': gvf_json(gvf_arr),
        'class_breaks': class_breaks,
        'boundary': boundary,
        'grid_stats': {
            'num_polys': len(gdf),
            'num_zones': len(class_breaks)
        },
        'legend': legend,
    }

def export_zones(
    zones_geojson: dict,
    format: str = 'geojson'
) -> str | bytes:
    """Export zones to different formats."""
    if format == 'geojson':
        return json.dumps(zones_geojson)
    elif format == 'shapefile':
        gdf = gpd.GeoDataFrame.from_features(zones_geojson['features'], crs='epsg:4326')
        with tempfile.TemporaryDirectory() as tmpdir:
            outpath = f"{tmpdir}/zones.shp"
            # Let the Shapefile driver shorten and disambiguate DBF field names.
            # Truncating first can make the min and max columns identical.
            gdf.to_file(outpath)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fname in os.listdir(tmpdir):
                    zf.write(os.path.join(tmpdir, fname), fname)
            return buf.getvalue()
    raise ValueError(f"Unsupported format: {format}")
