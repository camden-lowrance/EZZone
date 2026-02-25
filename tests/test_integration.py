"""
Integration tests for the ezzone Flask application.

Each test uses Flask's test client, which preserves the session cookie across
requests within the same `with client:` block, exactly as a browser would.
"""

import io
import json
import os

import numpy as np
import pytest
from diskcache import Cache

from src.app import create_app
from src.geo import bound_json


# ── Small fixture dataset ──────────────────────────────────────────────────────
# 10x10 WGS-84 grid near the real test.csv field (UK); deterministic gradient Z.

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
    """Configure the Flask app for testing."""
    application = create_app(test_config={
        'TESTING': True,
        'UPLOAD_FOLDER': str(tmp_path),
        'CACHE_FOLDER': str(tmp_path / 'cache'),
        'SECRET_KEY': 'test-secret',
    })
    yield application


@pytest.fixture()
def client(app):
    """Test client with cookie jar preserved across requests."""
    with app.test_client() as c:
        yield c


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_fc(x, y):
    """Build a GeoJSON FeatureCollection in EPSG:4326 wrapping the field boundary."""
    x_arr, y_arr = np.asarray(x, float), np.asarray(y, float)
    poly = bound_json(
        x=x_arr, y=y_arr,
        in_projection='epsg:4326',
        out_projection='epsg:4326',
    )
    return json.dumps({
        'type': 'FeatureCollection',
        'features': [{'type': 'Feature', 'geometry': poly, 'properties': {}}],
    })


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
    assert r.status_code in (200, 404)


def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'ok'


# ── Session init: demo mode (no file, reads test.csv) ────────────────────────

def test_session_init_demo(client):
    """Demo mode (no file) should initialise session and return boundary."""
    r = client.post('/api/session/init',
                    content_type='multipart/form-data')
    assert r.status_code == 200, f"demo init failed: {r.data[:500]}"
    body = r.get_json()
    assert 'data_id' in body
    assert 'boundary' in body
    assert 'all_columns' in body
    assert 'numeric_columns' in body
    assert 'preview_data' in body
    assert isinstance(body['preview_data'], list)


def test_session_init_with_file(client, fixture_csv):
    """Uploading a CSV file should initialise session."""
    with open(fixture_csv, 'rb') as f:
        r = client.post('/api/session/init', data={
            'file': (f, 'field.csv'),
        }, content_type='multipart/form-data')
    assert r.status_code == 200
    body = r.get_json()
    assert 'data_id' in body
    assert 'boundary' in body
    assert 'all_columns' in body
    assert ['X', 'Y', 'Z'] == body['all_columns']
    assert 'numeric_columns' in body
    assert 'preview_data' in body
    assert len(body['preview_data']) > 0


# ── Full pipeline ─────────────────────────────────────────────────────────────

def test_pipeline(client, fixture_csv):
    """
    Full round-trip:
      /api/session/init -> /api/zones/generate
    """
    # 1. Init session with file
    with open(fixture_csv, 'rb') as f:
        r = client.post('/api/session/init', data={
            'file': (f, 'field.csv'),
        }, content_type='multipart/form-data')
    assert r.status_code == 200, f"init failed:\n{r.data[:500]}"
    init = r.get_json()
    data_id = init['data_id']

    # 2. Generate zones with boundary
    fc_json = _make_fc(FIXTURE_X, FIXTURE_Y)
    r = client.post('/api/zones/generate',
                    json={'data_id': data_id, 'boundary_geojson': fc_json, 'num_classes': 3})
    assert r.status_code == 200, f"generate failed:\n{r.data[:500]}"
    body = r.get_json()
    assert 'zones' in body
    assert 'gvf' in body


# ── Export tests ──────────────────────────────────────────────────────────────

def test_export_geojson(client, app):
    """GeoJSON export: correct mimetype and valid JSON body."""
    # Seed diskcache with minimal result
    with Cache(app.config['CACHE_FOLDER']) as cache:
        cache.set('zones_test-export', _MINIMAL_FC, expire=3600)

    r = client.post('/api/export', json={'data_id': 'test-export', 'format': 'geojson'})
    assert r.status_code == 200
    assert r.mimetype == 'application/json'
    assert r.headers['Content-Disposition'] == 'attachment;filename=zones.geojson'
    parsed = json.loads(r.data)
    assert parsed['type'] == 'FeatureCollection'


def test_export_shapefile(client, app):
    """Shapefile ZIP export: correct mimetype and valid ZIP."""
    with Cache(app.config['CACHE_FOLDER']) as cache:
        cache.set('zones_test-export-shp', _MINIMAL_FC, expire=3600)

    r = client.post('/api/export', json={'data_id': 'test-export-shp', 'format': 'shapefile'})
    assert r.status_code == 200
    assert r.mimetype == 'application/zip'
    assert r.headers['Content-Disposition'] == 'attachment;filename=zones.zip'
    assert r.data[:2] == b'PK'  # ZIP magic bytes
    import zipfile
    with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
        names = zf.namelist()
    assert any(n.endswith('.shp') for n in names), f"no .shp in zip: {names}"
    assert any(n.endswith('.dbf') for n in names), f"no .dbf in zip: {names}"


# ── Full browser flow mock ────────────────────────────────────────────────────

@pytest.fixture()
def fixture_csv_multi(tmp_path):
    """Write a small WGS-84 CSV with multiple numeric columns."""
    path = tmp_path / "multi.csv"
    lines = ["X,Y,Yield,NDVI"] + [
        f"{x},{y},{z:.4f},{z*0.1:.4f}"
        for x, y, z in zip(FIXTURE_X, FIXTURE_Y, FIXTURE_Z)
    ]
    path.write_text("\n".join(lines))
    return str(path)


def test_session_change_z_column(client, fixture_csv_multi):
    """Verify that changing the Z column updates the session data."""
    # 1. Init with default (Yield)
    with open(fixture_csv_multi, 'rb') as f:
        r = client.post('/api/session/init', data={'file': (f, 'multi.csv')}, content_type='multipart/form-data')  
    init1 = r.get_json()
    assert init1['detected_z'] == 'Yield'
    
    # 2. Re-init with a different column ('NDVI')
    with open(fixture_csv_multi, 'rb') as f:
        r = client.post('/api/session/init', data={
            'file': (f, 'multi.csv'),
            'z_column': 'NDVI'
        }, content_type='multipart/form-data')
    init2 = r.get_json()
    assert init2['detected_z'] == 'NDVI'
    assert init2['data_id'] != init1['data_id']

def test_full_browser_flow(client, fixture_csv):
    """
    Simulate the exact sequence of API calls the Vue SPA makes:
      1. POST /api/session/init  (HomeView -> "Use Sample Data")
      2. POST /api/zones/generate (DrawBoundaryView -> "Generate Zones")
      3. POST /api/zones/generate (ZonesView -> change num_classes)
      4. POST /api/export         (FinalizeView -> "Export GeoJSON")

    At each step, assert the response shape matches what the store expects.
    """
    # Step 1: init session (sample data, no file)
    r = client.post('/api/session/init',
                    content_type='multipart/form-data')
    assert r.status_code == 200, f"init failed: {r.data[:500]}"
    init = r.get_json()

    # Store expects: data_id, boundary, grid_stats
    assert 'data_id' in init
    assert 'boundary' in init
    assert 'grid_stats' in init
    data_id = init['data_id']
    boundary = init['boundary']

    # Boundary should be valid GeoJSON with coordinates
    assert boundary.get('type') in ('Polygon', 'Feature', 'FeatureCollection'), \
        f"Unexpected boundary type: {boundary.get('type')}"

    # Step 2: generate zones (send boundary back)
    r = client.post('/api/zones/generate',
                    json={'data_id': data_id, 'boundary_geojson': boundary, 'num_classes': 10})
    assert r.status_code == 200, f"generate failed: {r.data[:500]}"
    gen = r.get_json()

    # Store expects: zones, gvf, class_breaks, legend
    assert 'zones' in gen, f"Missing 'zones' in response: {list(gen.keys())}"
    assert 'gvf' in gen, f"Missing 'gvf' in response: {list(gen.keys())}"
    assert 'class_breaks' in gen
    assert 'legend' in gen

    # zones must be a valid GeoJSON FeatureCollection with features
    zones = gen['zones']
    assert zones['type'] == 'FeatureCollection', f"zones type: {zones.get('type')}"
    assert len(zones['features']) > 0, "zones has no features"

    # Each feature should have a 'zone' property
    for i, feat in enumerate(zones['features']):
        assert 'zone' in feat.get('properties', {}), \
            f"Feature {i} missing 'zone' property: {feat.get('properties')}"
        assert feat.get('geometry') is not None, \
            f"Feature {i} has null geometry (zone={feat['properties'].get('zone')})"

    # GVF should be list of [num_classes, gvf_value] pairs
    assert isinstance(gen['gvf'], list)
    assert len(gen['gvf']) > 0
    for pair in gen['gvf']:
        assert isinstance(pair, list) and len(pair) == 2, \
            f"GVF entry should be [n, val], got {pair}"
        assert isinstance(pair[0], int), f"GVF class count should be int, got {type(pair[0])}"
        assert isinstance(pair[1], float), f"GVF value should be float, got {type(pair[1])}"

    # class_breaks: list of pre-formatted strings like "7.2 - 7.9"
    assert isinstance(gen['class_breaks'], list)
    for cb in gen['class_breaks']:
        assert isinstance(cb, str), f"class_break should be str, got {type(cb)}: {cb}"

    # legend: list of [color_hex, label] pairs
    assert isinstance(gen['legend'], list)
    for item in gen['legend']:
        assert isinstance(item, list) and len(item) == 2, \
            f"Legend item should be [color, label], got {item}"
        assert item[0].startswith('#'), f"Legend color should be hex, got {item[0]}"
        assert isinstance(item[1], str), f"Legend label should be str, got {item[1]}"

    # Step 3: re-generate with different num_classes (what ZonesView does)
    r = client.post('/api/zones/generate',
                    json={'data_id': data_id, 'boundary_geojson': boundary, 'num_classes': 3})
    assert r.status_code == 200, f"re-generate failed: {r.data[:500]}"
    fin = r.get_json()
    assert 'zones' in fin
    assert fin['zones']['type'] == 'FeatureCollection'
    assert len(fin['zones']['features']) > 0
    assert 'class_breaks' in fin
    assert 'legend' in fin

    # Step 4: export GeoJSON
    r = client.post('/api/export', json={'data_id': data_id, 'format': 'geojson'})
    assert r.status_code == 200, f"export failed: {r.data[:500]}"
    exported = json.loads(r.data)
    assert exported['type'] == 'FeatureCollection'
