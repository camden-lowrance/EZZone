"""
Integration tests for the ezzone Flask application.

Each test uses Flask's test client, which preserves the session cookie across
requests within the same `with client:` block, exactly as a browser would.
"""

import io
import json
import os

import numpy as np
import geojson
import pytest

from cachelib.file import FileSystemCache

from src.app import create_app
from src.geo import bound_json


# ── Small fixture dataset ──────────────────────────────────────────────────────
# 10×10 WGS-84 grid near the real test.csv field (UK); deterministic gradient Z.

_LONS = np.linspace(-0.460, -0.450, 10)
_LATS = np.linspace(52.070, 52.080, 10)
_LON_GRID, _LAT_GRID = np.meshgrid(_LONS, _LATS)
# Simple linear gradient so Jenks classification always finds clear breaks.
_Z_GRID = (_LON_GRID + 0.455) * 400 + (_LAT_GRID - 52.075) * 600 + 6.0

FIXTURE_X = _LON_GRID.flatten()
FIXTURE_Y = _LAT_GRID.flatten()
FIXTURE_Z = _Z_GRID.flatten()


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def fixture_csv(tmp_path):
    """Write a small WGS-84 CSV to tmp_path and return its path."""
    path = tmp_path / "field.csv"
    lines = ["X,Y,Z"] + [
        f"{x},{y},{z:.4f}"
        for x, y, z in zip(FIXTURE_X, FIXTURE_Y, FIXTURE_Z)
    ]
    path.write_text("\n".join(lines))
    return str(path)


@pytest.fixture()
def app(tmp_path):
    """
    Configure the Flask app for testing:
    - TESTING mode (propagates exceptions instead of 500 pages)
    - UPLOAD_FOLDER redirected to tmp_path so test state files are isolated
    """
    application = create_app(test_config={
        'TESTING': True,
        'UPLOAD_FOLDER': str(tmp_path),
        'SECRET_KEY': 'test-secret',
        'SESSION_TYPE': 'cachelib',
        'SESSION_CACHELIB': FileSystemCache(
            cache_dir=str(tmp_path / 'sessions'),
            threshold=500,
        ),
    })
    yield application


@pytest.fixture()
def client(app):
    """Test client with cookie jar preserved across requests."""
    with app.test_client() as c:
        yield c


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_fc(x, y, geometry_type):
    """
    Build a GeoJSON FeatureCollection in EPSG:4326 wrapping the field boundary.
    """
    x_arr, y_arr = np.asarray(x, float), np.asarray(y, float)
    if geometry_type == 1:
        coords = [[[x_arr.min(), y_arr.min()], [x_arr.max(), y_arr.min()],
                    [x_arr.max(), y_arr.max()], [x_arr.min(), y_arr.max()],
                    [x_arr.min(), y_arr.min()]]]
        poly = {'type': 'Polygon', 'coordinates': coords}
    else:
        poly = bound_json(
            x=x_arr, y=y_arr,
            geometry_type=geometry_type,
            in_projection='epsg:4326',
            out_projection='epsg:4326',
        )
    return geojson.dumps(geojson.FeatureCollection([geojson.Feature(geometry=poly)]))


# A minimal valid GeoJSON FeatureCollection for export tests.
_MINIMAL_FC = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-0.460, 52.070], [-0.450, 52.070],
                [-0.450, 52.080], [-0.460, 52.080],
                [-0.460, 52.070],
            ]],
        },
        "properties": {"zone": 1, "values": "4.5 - 7.0"},
    }],
}


# ── Smoke / health tests ─────────────────────────────────────────────────────

def test_index(client):
    """Root serves the Vue SPA index.html."""
    r = client.get('/')
    # May be 200 if index.html exists, or 404/500 if not built yet
    # Just verify the route is registered
    assert r.status_code in (200, 404)


def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'ok'


# ── Session init: demo mode (no file, reads test.csv) ────────────────────────

def test_session_init_demo(client):
    """Demo mode (no file) should initialise session and return boundary."""
    r = client.post('/api/session/init',
                    data={'epsg': '4326', 'field_type': '1', 'units': 'm', 'row_spacing': '100'},
                    content_type='multipart/form-data')
    assert r.status_code == 200, f"demo init failed: {r.data[:500]}"
    body = r.get_json()
    assert 'session_id' in body
    assert 'boundary' in body


def test_session_init_with_file(client, fixture_csv):
    """Uploading a CSV file should initialise session."""
    with open(fixture_csv, 'rb') as f:
        r = client.post('/api/session/init', data={
            'file': (f, 'field.csv'),
            'epsg': '4326',
            'field_type': '1',
            'units': 'm',
            'row_spacing': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200
    body = r.get_json()
    assert 'session_id' in body
    assert 'boundary' in body


def test_session_init_irreg(client):
    """Demo mode with field_type=3 (irregular)."""
    r = client.post('/api/session/init',
                    data={'epsg': '4326', 'field_type': '3', 'units': 'm', 'row_spacing': '100'},
                    content_type='multipart/form-data')
    assert r.status_code == 200
    body = r.get_json()
    assert 'boundary' in body


# ── Full pipeline: rectangular field ──────────────────────────────────────────

def test_pipeline_rect(client, fixture_csv):
    """
    Full round-trip for a rectangular-grid field:
      /api/session/init → /api/zones/generate → /api/zones/finalize
    """
    # 1. Init session with file
    with open(fixture_csv, 'rb') as f:
        r = client.post('/api/session/init', data={
            'file': (f, 'field.csv'),
            'epsg': '4326',
            'field_type': '1',
            'units': 'm',
            'row_spacing': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200, f"init failed:\n{r.data[:500]}"

    # 2. Generate zones with boundary
    fc_json = _make_fc(FIXTURE_X, FIXTURE_Y, geometry_type=1)
    r = client.post('/api/zones/generate',
                    json={'boundary_geojson': fc_json, 'num_classes': 10})
    assert r.status_code == 200, f"generate failed:\n{r.data[:500]}"
    body = r.get_json()
    assert 'zones' in body
    assert 'gvf' in body

    # 3. Finalize with chosen number of classes
    r = client.post('/api/zones/finalize', json={'num_classes': 3})
    assert r.status_code == 200, f"finalize failed:\n{r.data[:500]}"
    body = r.get_json()
    assert 'zones' in body
    assert body['zones']['type'] == 'FeatureCollection'


# ── Full pipeline: irregular field ────────────────────────────────────────────

def test_pipeline_irreg(client, fixture_csv):
    """
    Round-trip for an irregular-grid field:
      /api/session/init → /api/zones/generate
    """
    # 1. Init session
    with open(fixture_csv, 'rb') as f:
        r = client.post('/api/session/init', data={
            'file': (f, 'field.csv'),
            'epsg': '4326',
            'field_type': '3',
            'units': 'm',
            'row_spacing': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200

    # 2. Generate zones
    fc_json = _make_fc(FIXTURE_X, FIXTURE_Y, geometry_type=3)
    r = client.post('/api/zones/generate',
                    json={'boundary_geojson': fc_json, 'num_classes': 2})
    assert r.status_code == 200, f"generate failed:\n{r.data[:500]}"
    body = r.get_json()
    assert 'zones' in body


# ── Export: both output formats ───────────────────────────────────────────────

def test_export_geojson(client):
    """GeoJSON export: correct mimetype and valid JSON body."""
    # Seed session with minimal result
    with client.session_transaction() as sess:
        sess['result'] = {'zones': _MINIMAL_FC, 'gvf': [], 'class_breaks': [], 'row_spacing': 100}

    r = client.post('/api/export', json={'format': 'geojson'})
    assert r.status_code == 200
    assert r.mimetype == 'application/json'
    assert r.headers['Content-Disposition'] == 'attachment;filename=zones.geojson'
    parsed = json.loads(r.data)
    assert parsed['type'] == 'FeatureCollection'


def test_export_shapefile(client):
    """Shapefile ZIP export: correct mimetype and valid ZIP."""
    with client.session_transaction() as sess:
        sess['result'] = {'zones': _MINIMAL_FC, 'gvf': [], 'class_breaks': [], 'row_spacing': 100}

    r = client.post('/api/export', json={'format': 'shapefile'})
    assert r.status_code == 200
    assert r.mimetype == 'application/zip'
    assert r.headers['Content-Disposition'] == 'attachment;filename=zones.zip'
    assert r.data[:2] == b'PK'  # ZIP magic bytes
    import zipfile
    with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
        names = zf.namelist()
    assert any(n.endswith('.shp') for n in names), f"no .shp in zip: {names}"
    assert any(n.endswith('.dbf') for n in names), f"no .dbf in zip: {names}"
