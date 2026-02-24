"""
Pure Python API for agricultural management zone generation.
Decoupled from Flask for use in modern SPA (Vue, etc.).

Usage:
    from mz_api import generate_zones
    
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

import json
import math
import os
import numpy as np
import pyproj
import geopandas as gpd
from shapely.geometry import shape, Point
from shapely.ops import unary_union

import mz


def generate_zones(
    x, y, z,
    field_type,
    in_projection='epsg:4326',
    row_spacing=None,
    pivot_spacing=None,
    pivot_length=None,
    boundary_geojson=None,
    num_classes=3
):
    """
    Generate agricultural management zones from point data.
    
    Args:
        x, y, z: Arrays of coordinates and measurement values
        field_type: 1=rectangular, 2=VRI (center-pivot), 3=irregular
        in_projection: EPSG code of input coordinates (e.g., 'epsg:4326')
        row_spacing: Row spacing in meters (for rect/irreg)
        pivot_spacing: Pivot spacing in meters (for VRI)
        pivot_length: Pivot arm length in meters (for VRI)
        boundary_geojson: Optional boundary GeoJSON from client (if None, computed from points)
        num_classes: Number of zones to create
        
    Returns:
        dict with keys: 'zones' (GeoJSON), 'gvf' (list), 'class_breaks' (list),
                        'boundary' (GeoJSON), 'grid_stats' (dict)
    """
    # Convert to numpy arrays
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    
    # Determine UTM zone for the data
    bounds = {
        'xmin': x.min(), 'xmax': x.max(),
        'ymin': y.min(), 'ymax': y.max()
    }
    
    # Get or create boundary
    if boundary_geojson is None:
        boundary = mz.bound_json(x, y, geometry_type=field_type, in_projection=in_projection)
    else:
        if isinstance(boundary_geojson, str):
            boundary = json.loads(boundary_geojson)
        else:
            boundary = boundary_geojson
    
    # Reproject boundary to UTM
    boundary_shp = mz.reproject_poly(shape(boundary['geometry']), in_projection=in_projection, out_projection='epsg:3857')
    utm_crs = mz.utmzone(boundary_shp)
    boundary_utm = mz.reproject_poly(shape(boundary['geometry']), in_projection=in_projection, out_projection=utm_crs)
    
    # Generate grid based on field type
    if field_type == 1:  # Rectangular
        if row_spacing is None:
            raise ValueError("row_spacing required for rectangular fields")
        row_space = mz.get_spacing(boundary_utm, row_spacing)
        polys = mz.grid_rect(boundary_utm, row_space)
    elif field_type == 2:  # VRI (center-pivot)
        if pivot_spacing is None or pivot_length is None:
            raise ValueError("pivot_spacing and pivot_length required for VRI fields")
        # Extract center point from boundary or use centroid
        center = boundary_utm.centroid
        polys = mz.grid_circ(pivot_spacing, pivot_length, center, boundary_utm)
        row_space = 0  # VRI doesn't use row spacing
    elif field_type == 3:  # Irregular
        if row_spacing is None:
            raise ValueError("row_spacing required for irregular fields")
        row_space = mz.get_spacing(boundary_utm, row_spacing)
        polys = mz.grid_irreg(boundary_utm, None, row_space)
    else:
        raise ValueError(f"Invalid field_type: {field_type}")
    
    # Interpolate raster
    array, raster_bounds = mz.interpolate_raster(x, y, z, in_projection, utm_crs, boundary_utm)
    
    # Get polygon statistics
    poly_stats, polys2 = mz.get_poly_stats(array, polys, raster_bounds)
    
    # Calculate GVF for different class counts
    gvf_arr = mz.gvf_array(poly_stats, 10)
    
    # Classify into zones
    num_classes = min(num_classes, len(np.unique(poly_stats)))
    poly_comb, class_breaks = mz.get_poly_jenks(poly_stats, polys2, num_classes)
    
    # Convert to GeoJSON
    zones_geojson = mz.zones_to_geojson_fc(poly_comb, class_breaks, inp=utm_crs)
    
    # Get color codes for frontend
    cmap_def, cmap_sel = mz.json_color_codes(num_classes)
    legend = mz.json_legend(class_breaks)
    
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


def simplify_zones(zones_geojson, row_spacing, smooth=1):
    """
    Apply smoothing/simplification to existing zones.
    
    Args:
        zones_geojson: GeoJSON FeatureCollection from generate_zones
        row_spacing: Original row spacing used
        smooth: Smoothing factor (1-10)
        
    Returns:
        Simplified GeoJSON FeatureCollection
    """
    # Parse features back to shapely geometries
    features = zones_geojson['features']
    polys = []
    class_breaks = []
    
    for feat in features:
        geom = shape(feat['geometry'])
        polys.append(geom)
        class_breaks.append(feat['properties'].get('values', ''))
    
    # Apply simplification
    new_polys = mz.simplify_polys(polys, row_spacing, smooth)
    
    # Convert back to GeoJSON
    return mz.zones_to_geojson_fc(new_polys, class_breaks)


def compute_gvf(x, y, z, field_type, in_projection='epsg:4326', row_spacing=100):
    """
    Compute GVF values for 2-10 classes without generating full zones.
    Useful for the chart display before user selects number of classes.
    
    Returns:
        List of [num_classes, gvf_value] pairs
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    
    # Create boundary
    boundary = mz.bound_json(x, y, geometry_type=field_type, in_projection=in_projection)
    
    # Reproject to UTM
    boundary_shp = mz.reproject_poly(shape(boundary['geometry']), in_projection=in_projection, out_projection='epsg:3857')
    utm_crs = mz.utmzone(boundary_shp)
    boundary_utm = mz.reproject_poly(shape(boundary['geometry']), in_projection=in_projection, out_projection=utm_crs)
    
    # Generate grid
    if field_type == 1:
        row_space = mz.get_spacing(boundary_utm, row_spacing)
        polys = mz.grid_rect(boundary_utm, row_space)
    elif field_type == 3:
        row_space = mz.get_spacing(boundary_utm, row_spacing)
        polys = mz.grid_irreg(boundary_utm, None, row_space)
    else:
        raise ValueError("compute_gvf only supports rect (1) and irreg (3) field types")
    
    # Interpolate and get stats
    array, raster_bounds = mz.interpolate_raster(x, y, z, in_projection, utm_crs, boundary_utm)
    poly_stats, _ = mz.get_poly_stats(array, polys, raster_bounds)
    
    # Compute GVF array
    return mz.gvf_array(poly_stats, 10)


def export_zones(zones_geojson, format='geojson'):
    """
    Export zones to different formats.
    
    Args:
        zones_geojson: GeoJSON FeatureCollection
        format: 'geojson' or 'shapefile'
        
    Returns:
        For geojson: dict ready for JSON response
        For shapefile: bytes (ZIP archive)
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
