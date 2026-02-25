"""
Zone generation service for agricultural management.

This package provides:
- generate_zones: Main zone generation function
- simplify_zones: Zone simplification/smoothing
- compute_gvf: Goodness of Variance Fit calculation
- export_zones: Export to GeoJSON or Shapefile
"""

from src.zones.service import (
    generate_zones,
    simplify_zones,
    compute_gvf,
    export_zones,
)

__all__ = [
    "generate_zones",
    "simplify_zones",
    "compute_gvf",
    "export_zones",
]
