# Agent Development Guide

Guidelines for AI agents working in the EZZone repository.

## Project Overview

EZZone is an agricultural management zone generator. Users upload point-sampled field data, review the detected CRS and value column, refine a field boundary, generate management zones, and export the result.

- Frontend: Vue 3 + Vite + Pinia + OpenLayers + Chart.js
- Backend: Flask API
- Geospatial stack: GDAL, GeoPandas, rasterio, shapely, pyproj, scipy
- Environment: Pixi on conda-forge

## Commands

```bash
pixi install
pixi run dev
pixi run dev-be
pixi run dev-fe
pixi run build
pixi run start
pixi run test
pixi run test-cov
pytest tests/test_integration.py
pytest tests/test_mz_api.py
pytest tests/test_mz_api.py::test_generate_zones_basic
```

## Project Structure

```text
backend/src/
|-- app.py          # Flask app factory + SPA serving
|-- api.py          # API endpoints, DiskCache-backed upload state, exports
|-- geo.py          # CRS helpers, interpolation, GVF, classification, polygonization
|-- zones.py        # Zone generation orchestration and export helpers
`-- io_service.py   # File loading, CRS detection, schema checks

frontend/
|-- App.vue
|-- main.js
|-- style.css
|-- steps.js
|-- stores/zoneStore.js
`-- views/
    |-- HomeView.vue
    |-- DataView.vue
    |-- DrawBoundaryView.vue
    |-- ZonesView.vue
    `-- FinalizeView.vue

tests/
|-- test_integration.py
|-- test_mz_api.py
`-- fixtures/test.csv
```

## Architecture

### Frontend flow

The UI is a 5-step SPA with store-driven navigation:

1. `HomeView.vue` - upload files or use sample data
2. `DataView.vue` - review detected CRS, preview rows, and choose the value column
3. `DrawBoundaryView.vue` - edit the working boundary on an OpenLayers map
4. `ZonesView.vue` - inspect generated zones, GVF, and class breaks
5. `FinalizeView.vue` - export outputs and review the summary

There is no Vue Router. `frontend/stores/zoneStore.js` owns the active step, current `data_id`, and API-backed results.

### Backend flow

- `POST /api/session/init`
  - Loads uploaded files or sample data
  - Detects CRS and candidate value columns
  - Returns `data_id`, preview metadata, and a default convex-hull boundary
- `POST /api/zones/generate`
  - Looks up cached raw data by `data_id`
  - Re-runs zone generation for the submitted boundary and class count
- `POST /api/export`
  - Returns cached zone output as GeoJSON or zipped Shapefile
- `GET /api/health`
  - Health check for local dev and deployment

### State model

- Frontend state is local to the browser and keyed by the returned `data_id`
- Backend requests are effectively stateless from Flask's perspective
- Raw upload data is cached in DiskCache for 24 hours
- Generated zones are cached for 1 hour
- Uploaded files are written to a per-request temporary directory before loading, which avoids same-filename collisions across users

## Processing Pipeline

```text
Upload/sample data
  -> load_to_gdf() / load_multiple_to_gdf()
  -> detect CRS + value column
  -> derive default convex-hull boundary
  -> reproject into UTM
  -> interpolate an adaptive-resolution raster
  -> compute GVF with MiniBatchKMeans
  -> classify raster values with KMeans
  -> polygonize and clip classes
  -> reproject to EPSG:4326
  -> export GeoJSON or zipped Shapefile
```

## Key Constraints

- GDAL is required. Do not add "lightweight fallback" code paths.
- API responses should stay EPSG:4326 GeoJSON.
- Internal processing should happen in projected CRS.
- Prefer in-memory processing over long-lived intermediate files.
- `SENTRY_DSN` is optional and should remain optional; local dev and tests must still run cleanly without it.
- Keep frontend changes aligned with the existing Pinia-driven wizard flow.
- Tests rely on `conftest.py` adding `backend/` to `sys.path`, so imports use `from src...`.

## Code Style

- Python: PEP 8, type hints on public function signatures, user-facing errors should prefer `DataError`
- JavaScript: Vue 3 Composition API, component-oriented structure
- Geospatial logic: prefer vectorized numpy / geopandas operations over Python loops when possible
- Docs: keep README and this file aligned with the actual code path, not stale architecture notes
