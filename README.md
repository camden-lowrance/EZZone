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
7. **Output** — Zones are dissolved, smoothed, reprojected to EPSG:4326, and returned as a GeoJSON FeatureCollection. Users can export as `.geojson` or Shapefile (via external `ogre.adc4gis.com` conversion service).

---

## File Inventory

| File | Purpose |
|---|---|
| `mz.py` | Core geospatial library — grid generation, interpolation, classification, GeoJSON export |
| `panywhere.py` | Flask app — routes, file upload handling |
| `pixi.toml` | Dependency manifest for [pixi](https://prefix.dev/docs/pixi/) (conda-forge) |
| `templates/` | Jinja2 HTML templates (OpenLayers maps, GVF chart, file download) |
| `static/` | OpenLayers JS, CSS, test CSV |

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

### 1. Global Mutable State in Flask

`panywhere.py` stores all per-request data in module-level globals (`x`, `y`, `z`, `poly_stats`, `polys2`, `utm_pyproj`, etc.). This makes the app single-user only — any concurrent request corrupts state.

### 2. External HTTP Dependency for Shapefile Export

`/sendFile` route POSTs to `http://ogre.adc4gis.com/convertJson` for Shapefile conversion. This service is not guaranteed to be available and uses plain HTTP. Should be replaced with a local `geopandas` export.

### 3. Hardcoded Flask Secret Key

`app.secret_key = '12ad432gfd'` is hardcoded in `panywhere.py`. Should be loaded from an environment variable.

### 4. No Test Suite

Integration test cases existed historically but were Python 2-only with hardcoded local paths and have been removed. No automated tests exist.

### 5. Duplicate Logic in `mz.py`

The six `s_polys_*` functions (`s_polys_up`, `s_polys_down`, `s_polys_up_med`, `s_polys_down_med`, `s_polys_up_two`, `s_polys_down_two`) are near-identical and should be consolidated into a single parameterized function.

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

### Phase 3 — Eliminate Global State

`panywhere.py` stores per-session data in module globals. Three options, increasing in complexity:

**Option A (simple):** Use Flask's `session` to store a job ID, serialize intermediate results (grid polys, stats) to disk keyed by session ID.

**Option B (clean):** Refactor the multi-step workflow into a single stateless endpoint that accepts all parameters and runs the full pipeline in one request. Eliminates intermediate state entirely but requires frontend rework.

**Option C (scalable):** Add a task queue (Celery + Redis) for long-running computations. Return a job ID immediately; poll for results.

### Phase 4 — Code Quality

1. Consolidate the six `s_polys_*` functions in `mz.py` into a single parameterized function.
2. Replace bare `except Exception` blocks with specific exception types.
3. Add a `pytest` test suite with fixture CSVs covering the three field types (rectangular, irregular, center-pivot).
4. Load Flask secret key from environment variable.
5. Replace the `ogre.adc4gis.com` Shapefile converter with a local `geopandas` export (`GeoDataFrame.to_file()`).

### Phase 5 — Dependency Cleanup

- Pin major library versions in `pixi.toml` once Phase 3–4 are complete.
- Add `pytest` and `pytest-flask` to `pixi.toml` for the test suite.
- Evaluate replacing `gdal`/`osr` in `create_geotiff` with `rasterio` to reduce the GDAL build dependency.

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
