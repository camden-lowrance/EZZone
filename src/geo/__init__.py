"""
Geospatial core library for agricultural management zone generation.

This module provides functions for:
- Boundary creation from point data
- Grid generation (rectangular, irregular, center-pivot)
- Raster interpolation
- Zonal statistics
- Jenks classification
- GeoJSON export
"""

# Re-export main functions for convenient imports
from src.geo.geo_core import (
    extrapolate_nans,
    geojson_fc_parser,
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

__all__ = [
    "extrapolate_nans",
    "geojson_fc_parser",
    "bound_json",
    "reproject_poly",
    "utmzone",
    "get_spacing",
    "grid_rect",
    "grid_irreg",
    "grid_circ",
    "interpolate_raster",
    "get_poly_stats",
    "gvf_array",
    "get_poly_jenks",
    "zones_to_geojson_fc_gdf",
    "json_color_codes",
    "json_legend",
    "simplify_polys",
]
