"""
Unit tests for the mz_api module.
These tests are decoupled from Flask and test the core algorithm directly.
"""

import json
import os
import numpy as np
import pytest

from src.zones import generate_zones, compute_gvf, export_zones


# ── Test data ──────────────────────────────────────────────────────────────────

# Small 10×10 grid with linear gradient (same as test_integration.py)
_LONS = np.linspace(-0.460, -0.450, 10)
_LATS = np.linspace(52.070, 52.080, 10)
_LON_GRID, _LAT_GRID = np.meshgrid(_LONS, _LATS)
_Z_GRID = (_LON_GRID + 0.455) * 400 + (_LAT_GRID - 52.075) * 600 + 6.0

FIXTURE_X = _LON_GRID.flatten()
FIXTURE_Y = _LAT_GRID.flatten()
FIXTURE_Z = _Z_GRID.flatten()


# ── Basic tests ────────────────────────────────────────────────────────────────

def test_generate_zones_rect():
    """Test rectangular field zone generation."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        field_type=1,
        in_projection='epsg:4326',
        row_spacing=100,
        num_classes=3
    )
    
    assert 'zones' in result
    assert 'gvf' in result
    assert 'class_breaks' in result
    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0
    assert len(result['gvf']) > 0


def test_generate_zones_irreg():
    """Test irregular field zone generation."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        field_type=3,
        in_projection='epsg:4326',
        row_spacing=100,
        num_classes=2
    )
    
    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0


def test_generate_zones_vri():
    """Test VRI (center-pivot) field zone generation."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        field_type=2,
        in_projection='epsg:4326',
        pivot_spacing=50,
        pivot_length=500,
        num_classes=2
    )
    
    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0


def test_compute_gvf():
    """Test GVF computation without full zone generation."""
    gvf = compute_gvf(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        field_type=1,
        in_projection='epsg:4326',
        row_spacing=100
    )
    
    assert isinstance(gvf, list)
    assert len(gvf) > 0
    assert all(isinstance(v, float) for v in gvf)
    assert all(0 <= v <= 1 for v in gvf)


def test_export_geojson():
    """Test GeoJSON export."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        field_type=1,
        in_projection='epsg:4326',
        row_spacing=100,
        num_classes=2
    )
    
    exported = export_zones(result['zones'], format='geojson')
    parsed = json.loads(exported)
    assert parsed['type'] == 'FeatureCollection'


def test_export_shapefile():
    """Test Shapefile export."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        field_type=1,
        in_projection='epsg:4326',
        row_spacing=100,
        num_classes=2
    )
    
    exported = export_zones(result['zones'], format='shapefile')
    assert exported[:2] == b'PK'  # ZIP magic bytes


def test_with_sample_data():
    """Test with the real static/test.csv sample data."""
    test_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'test.csv')
    x, y, z = np.loadtxt(test_csv, skiprows=1, delimiter=",", unpack=True)
    
    result = generate_zones(
        x=x, y=y, z=z,
        field_type=1,
        in_projection='epsg:4326',
        row_spacing=100,
        num_classes=3
    )
    
    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0
    assert len(result['gvf']) > 0


def test_error_handling_missing_params():
    """Test error handling for missing required parameters."""
    with pytest.raises(ValueError, match="row_spacing required"):
        generate_zones(
            x=FIXTURE_X, y=FIXTURE_Y, z=FIXTURE_Z,
            field_type=1,
            in_projection='epsg:4326',
            num_classes=3
        )
    
    with pytest.raises(ValueError, match="pivot_spacing and pivot_length required"):
        generate_zones(
            x=FIXTURE_X, y=FIXTURE_Y, z=FIXTURE_Z,
            field_type=2,
            in_projection='epsg:4326',
            num_classes=3
        )
    
    with pytest.raises(ValueError, match="compute_gvf only supports"):
        compute_gvf(
            x=FIXTURE_X, y=FIXTURE_Y, z=FIXTURE_Z,
            field_type=2,  # VRI not supported
            in_projection='epsg:4326',
            row_spacing=100
        )
