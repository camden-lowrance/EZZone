"""
Integration tests for the ezzone Flask application.

Each test uses Flask's test client, which preserves the session cookie across
requests within the same `with client:` block, exactly as a browser would.

Session state is stored as pickled files in a pytest tmp_path directory
(panywhere.UPLOAD_FOLDER is monkey-patched per test).
"""

import io
import json
import os
import sys

import numpy as np
import geojson
import pytest

# ensure repo root is on sys.path so `import panywhere` / `import mz` work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import panywhere  # noqa: E402 (after sys.path manipulation)
import mz         # noqa: E402


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
    panywhere.app.config['TESTING'] = True
    panywhere.app.config['UPLOAD_FOLDER'] = str(tmp_path)
    original_folder = panywhere.UPLOAD_FOLDER
    panywhere.UPLOAD_FOLDER = str(tmp_path)
    yield panywhere.app
    panywhere.UPLOAD_FOLDER = original_folder


@pytest.fixture()
def client(app):
    """Test client with cookie jar preserved across requests."""
    with app.test_client() as c:
        yield c


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_fc(x, y, geometry_type):
    """
    Build a GeoJSON FeatureCollection in EPSG:3857 wrapping the field boundary,
    simulating what the browser submits after the OpenLayers boundary-edit step.

    For rect (geometry_type=1) we build an explicit 4-corner bounding rectangle
    rather than calling bound_json, which can produce a degenerate 3-point polygon
    when the input data are on a perfectly regular grid (xmax and ymin corners
    coincide).  The irreg/VRI path uses bound_json's convex-hull branch which
    handles regular grids correctly.
    """
    import pyproj as _pp
    x_arr, y_arr = np.asarray(x, float), np.asarray(y, float)
    t = _pp.Transformer.from_crs('epsg:4326', 'epsg:3857', always_xy=True)
    x0, y0 = t.transform(x_arr.min(), y_arr.min())
    x1, y1 = t.transform(x_arr.max(), y_arr.max())
    if geometry_type == 1:
        # Explicit axis-aligned rectangle (SW→SE→NE→NW→SW)
        coords = [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]
        poly = {'type': 'Polygon', 'coordinates': coords}
    else:
        poly = mz.bound_json(
            x=x_arr, y=y_arr,
            geometry_type=geometry_type,
            in_projection='epsg:4326',
        )
    return geojson.dumps(geojson.FeatureCollection([geojson.Feature(geometry=poly)]))


# A minimal valid GeoJSON FeatureCollection for sendFile tests that don't
# need the actual computed zones.
_MINIMAL_FC = json.dumps({
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
})


# ── Smoke / error-condition tests ──────────────────────────────────────────────

def test_index(client):
    r = client.get('/')
    assert r.status_code == 200


def test_upload_unsupported_file_type(client):
    """Uploading a .png file must return the badFile template."""
    r = client.post('/upload', data={
        'file': (io.BytesIO(b'\x89PNG'), 'image.png'),
        'X': 'X', 'Y': 'Y', 'Z': 'Z',
        'coord': '4326', 'field': '1', 'units': 'm', 'row': '100',
    }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'unsupported file type' in r.data


def test_upload_bad_epsg(client, fixture_csv):
    """An unrecognised EPSG code must return the badEpsg template."""
    with open(fixture_csv, 'rb') as f:
        r = client.post('/upload', data={
            'file': (f, 'field.csv'),
            'X': 'X', 'Y': 'Y', 'Z': 'Z',
            'coord': '99999',   # not a real EPSG
            'field': '1', 'units': 'm', 'row': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'EPSG' in r.data


def test_upload_bad_row_spacing(client, fixture_csv):
    """A non-numeric row parameter must return the badParam template."""
    with open(fixture_csv, 'rb') as f:
        r = client.post('/upload', data={
            'file': (f, 'field.csv'),
            'X': 'X', 'Y': 'Y', 'Z': 'Z',
            'coord': '4326', 'field': '1', 'units': 'm', 'row': 'abc',
        }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'invalid spacing parameter' in r.data


# ── Upload: demo mode (no file, reads static/test.csv) ────────────────────────

def test_upload_demo_rect(client):
    """Demo mode with field_type=1 renders rect.html and sets a session sid."""
    r = client.post('/upload', data={
        'file': (io.BytesIO(b''), ''),   # empty → falls through to demo path
        'coord': '4326', 'field': '1', 'units': 'm', 'row': '100',
    }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'Polygon' in r.data          # boundary GeoJSON embedded in rect.html
    with client.session_transaction() as sess:
        assert 'sid' in sess


def test_upload_demo_irreg(client):
    """Demo mode with field_type=3 renders irreg.html."""
    r = client.post('/upload', data={
        'file': (io.BytesIO(b''), ''),
        'coord': '4326', 'field': '3', 'units': 'm', 'row': '100',
    }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'Polygon' in r.data


# ── Upload: file-based ─────────────────────────────────────────────────────────

def test_upload_file_rect(client, fixture_csv):
    """Uploading the fixture CSV for a rect field renders rect.html."""
    with open(fixture_csv, 'rb') as f:
        r = client.post('/upload', data={
            'file': (f, 'field.csv'),
            'X': 'X', 'Y': 'Y', 'Z': 'Z',
            'coord': '4326', 'field': '1', 'units': 'm', 'row': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'Polygon' in r.data


def test_upload_file_feet(client, fixture_csv):
    """Unit conversion from feet should not crash (row=328 ft ≈ 100 m)."""
    with open(fixture_csv, 'rb') as f:
        r = client.post('/upload', data={
            'file': (f, 'field.csv'),
            'X': 'X', 'Y': 'Y', 'Z': 'Z',
            'coord': '4326', 'field': '1', 'units': 'f', 'row': '328',
        }, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b'Polygon' in r.data


# ── Full pipeline: rectangular field ──────────────────────────────────────────

def test_pipeline_rect(client, fixture_csv):
    """
    Full round-trip for a rectangular-grid field:
      /upload → /createRect → /createZones → /simplify → /sendFile (both formats)
    """
    # 1. Upload
    with open(fixture_csv, 'rb') as f:
        r = client.post('/upload', data={
            'file': (f, 'field.csv'),
            'X': 'X', 'Y': 'Y', 'Z': 'Z',
            'coord': '4326', 'field': '1', 'units': 'm', 'row': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200, f"upload failed:\n{r.data[:500]}"
    assert b'Polygon' in r.data

    # 2. createRect — pass the computed boundary back as a FeatureCollection
    fc_json = _make_fc(FIXTURE_X, FIXTURE_Y, geometry_type=1)
    r = client.post('/createRect',
                    data={'jsonval': fc_json},
                    content_type='application/x-www-form-urlencoded')
    assert r.status_code == 200, f"createRect failed:\n{r.data[:500]}"
    assert b'Goodness of Variance Fit' in r.data   # chart.html

    # 3. createZones
    r = client.post('/createZones',
                    data={'classes': '3'},
                    content_type='application/x-www-form-urlencoded')
    assert r.status_code == 200, f"createZones failed:\n{r.data[:500]}"
    assert b'FeatureCollection' in r.data           # zones embedded in displayZones.html

    # 4. simplify (reads from session state; no POST body needed)
    r = client.get('/simplify?smooth=1')
    assert r.status_code == 200, f"simplify failed:\n{r.data[:500]}"
    payload = json.loads(r.data)
    assert 'result' in payload
    assert payload['result']['type'] == 'FeatureCollection'
    assert len(payload['result']['features']) > 0


# ── Full pipeline: irregular field ─────────────────────────────────────────────

def test_pipeline_irreg(client, fixture_csv):
    """
    Round-trip for an irregular-grid field (no row-line drawn):
      /upload → /createIrreg → /createZones
    """
    # 1. Upload
    with open(fixture_csv, 'rb') as f:
        r = client.post('/upload', data={
            'file': (f, 'field.csv'),
            'X': 'X', 'Y': 'Y', 'Z': 'Z',
            'coord': '4326', 'field': '3', 'units': 'm', 'row': '100',
        }, content_type='multipart/form-data')
    assert r.status_code == 200

    # 2. createIrreg — FeatureCollection contains only the boundary polygon
    fc_json = _make_fc(FIXTURE_X, FIXTURE_Y, geometry_type=3)
    r = client.post('/createIrreg',
                    data={'jsonval': fc_json},
                    content_type='application/x-www-form-urlencoded')
    assert r.status_code == 200, f"createIrreg failed:\n{r.data[:500]}"
    assert b'Goodness of Variance Fit' in r.data

    # 3. createZones (2 classes keeps jenks happy with a small dataset)
    r = client.post('/createZones',
                    data={'classes': '2'},
                    content_type='application/x-www-form-urlencoded')
    assert r.status_code == 200, f"createZones failed:\n{r.data[:500]}"
    assert b'FeatureCollection' in r.data


# ── sendFile: both output formats ─────────────────────────────────────────────

def test_sendfile_geojson(client):
    """GeoJSON download: correct mimetype, filename header, and valid JSON body."""
    r = client.post('/sendFile', data={
        'jsonval': _MINIMAL_FC,
        'filetype': 'Save as GeoJSON',
    }, content_type='application/x-www-form-urlencoded')
    assert r.status_code == 200
    assert r.mimetype == 'application/json'
    assert r.headers['Content-Disposition'] == 'attachment;filename=zones.geojson'
    parsed = json.loads(r.data)
    assert parsed['type'] == 'FeatureCollection'


def test_sendfile_shapefile(client):
    """Shapefile ZIP download: correct mimetype, filename, and valid ZIP magic bytes."""
    r = client.post('/sendFile', data={
        'jsonval': _MINIMAL_FC,
        'filetype': 'Save as Shapefile',
    }, content_type='application/x-www-form-urlencoded')
    assert r.status_code == 200
    assert r.mimetype == 'application/zip'
    assert r.headers['Content-Disposition'] == 'attachment;filename=zones.zip'
    assert r.data[:2] == b'PK'   # ZIP magic bytes
    # ZIP should contain the expected shapefile components
    import zipfile, io as _io
    with zipfile.ZipFile(_io.BytesIO(r.data)) as zf:
        names = zf.namelist()
    assert any(n.endswith('.shp') for n in names), f"no .shp in zip: {names}"
    assert any(n.endswith('.dbf') for n in names), f"no .dbf in zip: {names}"
