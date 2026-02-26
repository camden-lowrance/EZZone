"""
Unit tests for the core zone generation algorithm.
Tests are decoupled from Flask and test the algorithm directly.
"""

import json
import os
import numpy as np
import pytest

from src.zones import generate_zones, export_zones


# ── Test data ──────────────────────────────────────────────────────────────────

# Small 10x10 grid with linear gradient (same as test_integration.py)
_LONS = np.linspace(-0.460, -0.450, 10)
_LATS = np.linspace(52.070, 52.080, 10)
_LON_GRID, _LAT_GRID = np.meshgrid(_LONS, _LATS)
_Z_GRID = (_LON_GRID + 0.455) * 400 + (_LAT_GRID - 52.075) * 600 + 6.0

FIXTURE_X = _LON_GRID.flatten()
FIXTURE_Y = _LAT_GRID.flatten()
FIXTURE_Z = _Z_GRID.flatten()


# ── Basic tests ────────────────────────────────────────────────────────────────

def test_generate_zones_basic():
    """Test basic zone generation with 3 classes."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        in_projection='epsg:4326',
        num_classes=3
    )

    assert 'zones' in result
    assert 'gvf' in result
    assert 'class_breaks' in result
    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0
    assert len(result['gvf']) > 0


def test_generate_zones_two_classes():
    """Test zone generation with 2 classes."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        in_projection='epsg:4326',
        num_classes=2
    )

    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0


def test_gvf_in_result():
    """Test that GVF values are computed and returned."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        in_projection='epsg:4326',
        num_classes=3
    )

    assert isinstance(result['gvf'], list)
    assert len(result['gvf']) > 0
    for pair in result['gvf']:
        assert isinstance(pair, list) and len(pair) == 2
        assert isinstance(pair[0], int)
        assert isinstance(pair[1], float)
        assert 0 <= pair[1] <= 1


def test_export_geojson():
    """Test GeoJSON export."""
    result = generate_zones(
        x=FIXTURE_X,
        y=FIXTURE_Y,
        z=FIXTURE_Z,
        in_projection='epsg:4326',
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
        in_projection='epsg:4326',
        num_classes=2
    )

    exported = export_zones(result['zones'], format='shapefile')
    assert exported[:2] == b'PK'  # ZIP magic bytes


def test_with_sample_data():
    """Test with the real scott_harvest_2023 sample data."""
    import geopandas as gpd
    geojson = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'fixtures', 'scott_harvest_2023.geojson')
    gdf = gpd.read_file(geojson)
    x, y, z = gdf.geometry.x.values, gdf.geometry.y.values, gdf['harvestMoisture'].values

    result = generate_zones(
        x=x, y=y, z=z,
        in_projection='epsg:4326',
        num_classes=3
    )

    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0
    assert len(result['gvf']) > 0
