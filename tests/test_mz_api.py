"""
Unit tests for the core zone generation algorithm.
Tests are decoupled from Flask and test the algorithm directly.
"""

import json
import os
import numpy as np
import pytest

from src.zones import generate_zones, export_zones
from src.geo import classify_raster, interpolate_raster


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

def test_interpolation_matches_dense_grid_with_nearest_fallback(monkeypatch):
    """Broadcast grid coordinates must match dense coordinates, including fallback."""
    from rasterio import features
    from rasterio.transform import from_bounds
    from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
    from shapely.geometry import Polygon

    monkeypatch.setenv('EZZONE_PROFILE', 'fast')
    x = np.array([0., 8., 0., 8., 4.])
    y = np.array([0., 0., 8., 8., 4.])
    z = np.array([3., 5., 7., 10., 6.])
    poly = Polygon([(-1, -1), (9, -1), (9, 9), (-1, 9)])
    result, bounds = interpolate_raster(x, y, z, 'epsg:32617', 'epsg:32617', poly)
    ny, nx = result.shape
    gridx, gridy = np.meshgrid(np.linspace(bounds[0], bounds[2], nx),
                               np.linspace(bounds[1], bounds[3], ny))
    points = np.column_stack([x, y])
    expected = LinearNDInterpolator(points, z)(gridx, gridy)
    missing = np.isnan(expected)
    assert missing.any()
    expected[missing] = NearestNDInterpolator(points, z)(gridx[missing], gridy[missing])
    mask = features.geometry_mask([poly], out_shape=(ny, nx), transform=from_bounds(*bounds, nx, ny), invert=True)
    expected[~np.flipud(mask)] = np.nan
    np.testing.assert_array_equal(result, expected)


def test_classification_orders_zones_by_value():
    """Class numbers and reported ranges should increase with raster values."""
    raster = np.tile(np.repeat([30.0, 10.0, 20.0], 8), (12, 1))
    classified, breaks, ranges = classify_raster(raster, 3)

    assert classified.shape == raster.shape
    assert classified[5, 3] == 3
    assert classified[5, 11] == 1
    assert classified[5, 20] == 2
    assert len(breaks) == 3
    assert [r[0] for r in ranges] == [10.0, 20.0, 30.0]


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
    """Test zone generation with the test.csv fixture."""
    import pandas as pd
    csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'fixtures', 'test.csv')
    df = pd.read_csv(csv)
    x, y, z = df['X'].values, df['Y'].values, df['Yield'].values

    result = generate_zones(
        x=x, y=y, z=z,
        in_projection='epsg:4326',
        num_classes=3
    )

    assert result['zones']['type'] == 'FeatureCollection'
    assert len(result['zones']['features']) > 0
    assert len(result['gvf']) > 0
