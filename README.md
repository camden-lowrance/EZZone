# ezzone-pyanywhere

A Flask web application that generates agricultural management zones from point-sampled field data (e.g., soil EC, yield monitor data). Users upload a CSV, draw or confirm a field boundary on a map, and the app returns classified GeoJSON zones ready for use in variable-rate application systems.

---

## How It Works

1. **Upload** — User uploads a CSV with X, Y, Z columns (coordinates + measurement value) and selects field type and spacing parameters.
2. **Boundary** — The app builds a convex-hull or rectangular boundary from the point data and displays it on an OpenLayers map for the user to adjust.
3. **Grid** — A spatial grid of small polygons is generated over the boundary (rectangular, irregular, or center-pivot circular layouts).
4. **Interpolation** — The Z values are interpolated to a raster using scipy's `griddata` (linear), with NaN extrapolation at edges.
5. **Zonal Stats** — Mean raster values are extracted for each grid polygon via `rasterstats`.
6. **Classification** — Jenks Natural Breaks classifies the polygon stats. Goodness of Variance Fit (GVF) is computed to suggest an optimal number of zones.
7. **Output** — Zones are dissolved, smoothed, reprojected to EPSG:4326, and returned as a GeoJSON FeatureCollection. Users can export as `.geojson` or Shapefile (via local `geopandas` export).

---

## File Inventory

| File | Purpose |
|---|---|
| `mz.py` | Core geospatial library — grid generation, interpolation, classification, GeoJSON export |
| `panywhere.py` | Flask app — routes, file upload handling |
| `pixi.toml` | Dependency manifest for [pixi](https://prefix.dev/docs/pixi/) (conda-forge) |
| `templates/` | Jinja2 HTML templates (OpenLayers maps, GVF chart, file download) |
| `static/` | OpenLayers JS, CSS, test CSV |
| `tests/` | Integration test suite using pytest |

---

## Environment Setup

Dependencies are managed with [pixi](https://prefix.dev/docs/pixi/) targeting `win-64` and Python ≥ 3.11.

```bash
pixi install
pixi run python panywhere.py
```

---

## Known Issues

The app runs and imports cleanly. The following issues remain before it is production-ready:

### 1. External HTTP Dependency for Shapefile Export (FIXED)

`/sendFile` route now uses local `geopandas` export (`GeoDataFrame.to_file()`) instead of the external `ogre.adc4gis.com` conversion service.

---

## Refactoring Plan

### ~~Phase 1 — Fix Broken APIs~~ ✓ Complete

All deprecated library APIs updated to run on Python 3.11+ with current library versions:

- `pyproj.Proj(init=...)` and `pyproj.transform()` replaced with `pyproj.Transformer` and `pyproj.CRS`
- `utmzone()` now returns `pyproj.CRS` instead of `pyproj.Proj`
- All five reprojection functions (`reproject_poly`, `reproject_multip`, `reproject_point`, `reproject_line`, `reproject_array`) rewritten using `geopandas.GeoSeries.to_crs()`
- `shapely.geometry.asShape()` replaced with `shapely.geometry.shape()`
- `xrange()` in `grid_circ()` replaced with `range()`
- `descartes.PolygonPatch` replaced with `geopandas.GeoDataFrame.plot()`
- `shapely.geometry.JOIN_STYLE` replaced with integer join style value
- `brewer2mpl` replaced with `matplotlib.colormaps`
- `pixi.toml`: removed `descartes` and `brewer2mpl`, added `geopandas`

### ~~Phase 2 — Remove Dead Code~~ ✓ Complete

Deleted all obsolete files:

- `panywhereAlt.py` — superseded by `panywhere.py`; referenced nonexistent `mz` functions
- `simplify_polys.py` — logic fully duplicated in `mz.py`; used removed `cascaded_union`
- `mztest.py`, `testcases.py`, `tcase_comp.py` — Python 2 only, hardcoded local paths
- `__init__.py` — imported from nonexistent `sapp` package

### ~~Phase 3 — Eliminate Global State~~ ✓ Complete

Refactored `panywhere.py` to use Flask's `session` with serialized disk storage:

- Added `session['sid']` to store a unique session ID per request
- Implemented `load_state()` and `save_state()` functions that serialize intermediate results (grid polys, stats) to pickle files keyed by session ID
- The app now handles concurrent requests correctly without state corruption

### ~~Phase 4 — Code Quality~~ ✓ Complete

1. Consolidated the six `s_polys_*` functions in `mz.py` into a single parameterized `_s_polys()` function with `reverse`, `step`, and `half` parameters.
2. Replaced bare `except Exception` blocks with specific exception handling where applicable.
3. Added a `pytest` test suite in `tests/test_integration.py` with fixture CSVs covering the three field types (rectangular, irregular, center-pivot).
4. Flask secret key now loaded from environment variable: `app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-in-production')`.
5. Replaced the `ogre.adc4gis.com` Shapefile converter with local `geopandas` export (`GeoDataFrame.to_file()`).

### ~~Phase 5 — Dependency Cleanup~~ ✓ Complete

- Added `pytest` and `pytest-flask` to `pixi.toml` for the test suite.
- GDAL is still used for `create_geotiff`; evaluated and kept for now due to existing implementation.

---

## Processing Pipeline

```
CSV Upload
    │
    ▼
bound_json()           — build GeoJSON boundary from point cloud
    │
    ▼
[User adjusts boundary on map]
    │
    ▼
reproject_poly()       — 3857 → 4326 → UTM (via geopandas)
    │
    ▼
grid_rect / grid_irreg / grid_circ   — generate spatial grid
    │
    ▼
interpolate_raster()   — scipy griddata → 2D numpy array
    │
    ▼
get_poly_stats()       — rasterstats zonal_stats per grid cell
    │
    ▼
gvf_array()            — compute GVF for 2–10 classes
    │
    ▼
[User selects number of zones from chart]
    │
    ▼
get_poly_jenks()       — Jenks breaks → dissolve grid cells
    │
    ▼
simplify_polys()       — merge slivers between adjacent zones
    │
    ▼
zones_to_geojson_fc()  — reproject back to 4326, dump GeoJSON
    │
    ▼
[User downloads GeoJSON or Shapefile]
```
