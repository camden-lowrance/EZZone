"""
Zone generation service for agricultural management zone generation.
Decoupled from Flask for use in modern SPA (Vue, etc.).

Usage:
    from src.zones import generate_zones
    
    result = generate_zones(
        x=[...], y=[...], z=[...],  # coordinates and values
        field_type=1,               # 1=rect, 2=VRI, 3=irreg
        in_projection='epsg:4326',
        row_spacing=100,            # for rect/irreg
        pivot_spacing=50,           # for VRI
        pivot_length=500,           # for VRI
        boundary_geojson=...,       # optional boundary from client
        num_classes=3
    )
    
    # result contains:
    # - 'zones': GeoJSON FeatureCollection
    # - 'gvf': Goodness of Variance Fit array
    # - 'class_breaks': legend labels
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import geopandas as gpd
from shapely.geometry import shape

def _extract_geometry(boundary: dict) -> dict:
    """Extract a raw geometry dict from various GeoJSON structures."""
    if boundary.get('type') == 'FeatureCollection':
        return boundary['features'][0]['geometry']
    if boundary.get('type') == 'Feature':
        return boundary['geometry']
    if 'geometry' in boundary and isinstance(boundary['geometry'], dict):
        return boundary['geometry']
    return boundary  # raw geometry (Polygon, etc.)


from src.geo import (
    bound_json,
    reproject_poly,
    utmzone,
    get_spacing,
    grid_rect,
    grid_irreg,
    grid_circ,
    interpolate_raster,
    get_poly_stats,
    gvf_array,
    get_poly_jenks,
    zones_to_geojson_fc_gdf,
    json_color_codes,
    json_legend,
    simplify_polys,
)


def generate_zones(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    field_type: int,
    in_projection: str = 'epsg:4326',
    row_spacing: float | None = None,
    pivot_spacing: float | None = None,
    pivot_length: float | None = None,
    boundary_geojson: str | dict | None = None,
    num_classes: int = 3
) -> dict[str, Any]:
    """
    Generate agricultural management zones from point data.

    Args:
        x: Array of x coordinates.
        y: Array of y coordinates.
        z: Array of measurement values.
        field_type: Field geometry type (1=rectangular, 2=VRI, 3=irregular).
        in_projection: EPSG code of input coordinates (e.g., 'epsg:4326').
        row_spacing: Row spacing in meters (for rect/irreg).
        pivot_spacing: Pivot spacing in meters (for VRI).
        pivot_length: Pivot arm length in meters (for VRI).
        boundary_geojson: Optional boundary GeoJSON from client.
        num_classes: Number of zones to create.

    Returns:
        Dictionary with keys:
            - 'zones': GeoJSON FeatureCollection
            - 'gvf': List of GVF values
            - 'class_breaks': List of class break labels
            - 'boundary': GeoJSON boundary
            - 'grid_stats': Dictionary with grid statistics
            - 'legend': Legend data for frontend
            - 'cmap_def': Default color map
            - 'cmap_sel': Selected color map
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    
    if boundary_geojson is None:
        boundary = bound_json(x, y, geometry_type=field_type, in_projection=in_projection, out_projection=in_projection)
    else:
        if isinstance(boundary_geojson, str):
            boundary = json.loads(boundary_geojson)
        else:
            boundary = boundary_geojson
    
    boundary_geom = _extract_geometry(boundary)

    boundary_wgs84 = reproject_poly(
        shape(boundary_geom),
        in_projection=in_projection,
        out_projection='epsg:4326'
    )
    utm_crs = utmzone(boundary_wgs84)
    boundary_utm = reproject_poly(
        shape(boundary_geom),
        in_projection=in_projection,
        out_projection=utm_crs
    )
    
    if field_type == 1:
        if row_spacing is None:
            raise ValueError("row_spacing required for rectangular fields")
        row_space = get_spacing(boundary_utm, row_spacing)
        polys = grid_rect(boundary_utm, row_space)
    elif field_type == 2:
        if pivot_spacing is None or pivot_length is None:
            raise ValueError("pivot_spacing and pivot_length required for VRI fields")
        center = boundary_utm.centroid
        polys = grid_circ(pivot_spacing, pivot_length, center, boundary_utm)
        row_space = 0
    elif field_type == 3:
        if row_spacing is None:
            raise ValueError("row_spacing required for irregular fields")
        row_space = get_spacing(boundary_utm, row_spacing)
        polys = grid_irreg(boundary_utm, None, row_space)
    else:
        raise ValueError(f"Invalid field_type: {field_type}")
    
    array, raster_bounds = interpolate_raster(x, y, z, in_projection, utm_crs, boundary_utm)
    poly_stats, polys2 = get_poly_stats(array, polys, raster_bounds)
    gvf_arr = gvf_array(poly_stats, 10)
    
    num_classes = min(num_classes, len(np.unique(poly_stats)))
    poly_comb, class_breaks = get_poly_jenks(poly_stats, polys2, num_classes)
    zones_geojson = zones_to_geojson_fc_gdf(poly_comb, class_breaks, inp=utm_crs)
    
    cmap_def, cmap_sel = json_color_codes(num_classes)
    legend = json_legend(class_breaks)
    
    return {
        'zones': zones_geojson,
        'gvf': gvf_arr,
        'class_breaks': class_breaks,
        'boundary': boundary,
        'grid_stats': {
            'num_polys': len(polys),
            'num_zones': len(poly_comb),
            'row_spacing': row_space if field_type != 2 else pivot_spacing
        },
        'legend': legend,
        'cmap_def': cmap_def,
        'cmap_sel': cmap_sel
    }


def simplify_zones(
    zones_geojson: dict,
    row_spacing: float,
    smooth: int = 1
) -> dict:
    """
    Apply smoothing/simplification to existing zones.

    Args:
        zones_geojson: GeoJSON FeatureCollection from generate_zones.
        row_spacing: Original row spacing used.
        smooth: Smoothing factor (1-10).

    Returns:
        Simplified GeoJSON FeatureCollection.
    """
    features = zones_geojson['features']
    polys = []
    class_breaks = []
    
    for feat in features:
        geom = shape(feat['geometry'])
        polys.append(geom)
        class_breaks.append(feat['properties'].get('values', ''))
    
    new_polys = simplify_polys(polys, row_spacing, smooth)
    return zones_to_geojson_fc_gdf(new_polys, class_breaks)


def compute_gvf(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    field_type: int,
    in_projection: str = 'epsg:4326',
    row_spacing: float = 100
) -> list[float]:
    """
    Compute GVF values for 2-10 classes without generating full zones.

    Useful for the chart display before user selects number of classes.

    Args:
        x: Array of x coordinates.
        y: Array of y coordinates.
        z: Array of measurement values.
        field_type: Field geometry type (1=rectangular, 3=irregular).
        in_projection: EPSG code of input coordinates.
        row_spacing: Row spacing in meters.

    Returns:
        List of GVF values.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    
    boundary = bound_json(x, y, geometry_type=field_type, in_projection=in_projection, out_projection=in_projection)
    boundary_geom = boundary.get('geometry', boundary)

    boundary_wgs84 = reproject_poly(
        shape(boundary_geom),
        in_projection=in_projection,
        out_projection='epsg:4326'
    )
    utm_crs = utmzone(boundary_wgs84)
    boundary_utm = reproject_poly(
        shape(boundary_geom),
        in_projection=in_projection,
        out_projection=utm_crs
    )

    if field_type == 1:
        row_space = get_spacing(boundary_utm, row_spacing)
        polys = grid_rect(boundary_utm, row_space)
    elif field_type == 3:
        row_space = get_spacing(boundary_utm, row_spacing)
        polys = grid_irreg(boundary_utm, None, row_space)
    else:
        raise ValueError("compute_gvf only supports rect (1) and irreg (3) field types")
    
    array, raster_bounds = interpolate_raster(x, y, z, in_projection, utm_crs, boundary_utm)
    poly_stats, _ = get_poly_stats(array, polys, raster_bounds)
    return gvf_array(poly_stats, 10)


def export_zones(
    zones_geojson: dict,
    format: str = 'geojson'
) -> str | bytes:
    """
    Export zones to different formats.

    Args:
        zones_geojson: GeoJSON FeatureCollection.
        format: Export format ('geojson' or 'shapefile').

    Returns:
        For geojson: JSON string.
        For shapefile: ZIP archive as bytes.
    """
    if format == 'geojson':
        return json.dumps(zones_geojson)
    elif format == 'shapefile':
        import io
        import zipfile
        import tempfile
        
        gdf = gpd.GeoDataFrame.from_features(zones_geojson['features'], crs='epsg:4326')
        with tempfile.TemporaryDirectory() as tmpdir:
            outpath = f"{tmpdir}/zones.shp"
            gdf.to_file(outpath)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fname in os.listdir(tmpdir):
                    zf.write(os.path.join(tmpdir, fname), fname)
        return buf.getvalue()
    else:
        raise ValueError(f"Unsupported format: {format}")
