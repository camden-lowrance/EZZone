# EZZone

EZZone is a Flask + Vue 3 web application for generating agricultural management zones from point-sampled field data such as yield, EC, and NDVI. Users upload one or more supported files, review the detected CRS and value column, adjust a field boundary, generate classified zones, and export the result as GeoJSON or Shapefile.

## Current Flow

1. Upload files or use sample data.
2. Review the detected CRS and value column in the data summary step.
3. Draw or refine the field boundary in OpenLayers.
4. Generate zones and inspect the GVF chart plus class breaks.
5. Finalize and export GeoJSON or zipped Shapefile output.

## Multi-User Behavior

The app is no longer driven by Flask server-side sessions. `POST /api/session/init` returns a UUID `data_id`, and the frontend sends that ID back to `/api/zones/generate` and `/api/export`.

- Raw point data is cached in DiskCache for 24 hours under the returned `data_id`.
- Generated zone GeoJSON is cached for 1 hour under `zones_<data_id>`.
- Uploaded files are processed inside a per-request temporary directory so two users can upload the same filename without clobbering each other.

## Supported Inputs

- CSV and TXT with detectable coordinate columns (`X/Y`, `Lon/Lat`, `Longitude/Latitude`, `Easting/Northing`)
- Excel (`.xlsx`, `.xls`)
- Vector formats readable by GeoPandas / GDAL such as Shapefile, GeoJSON, GeoPackage, KML, and GML
- Multiple files with matching schemas
- ZIP uploads that contain supported vector data

## Project Structure

```text
backend/src/
|-- app.py          # Flask app factory + SPA serving
|-- api.py          # API endpoints, per-upload cache lifecycle, exports
|-- geo.py          # CRS helpers, interpolation, GVF, classification, polygonization
|-- zones.py        # Zone generation orchestration + export helpers
`-- io_service.py   # Multi-format loading and schema validation

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

## Commands

Dependencies are managed with [pixi](https://prefix.dev/docs/pixi/).

```bash
pixi install
pixi run dev
pixi run dev-be
pixi run dev-fe
pixi run build
pixi run start
pixi run test
pixi run test-cov
```

Useful direct test commands:

```bash
pytest tests/test_integration.py
pytest tests/test_mz_api.py
pytest tests/test_mz_api.py::test_generate_zones_basic
```

## API Summary

- `POST /api/session/init`
  - Accepts uploaded files or `use_sample=1`
  - Detects coordinate columns, CRS, and candidate value columns
  - Returns `data_id`, preview rows, detected metadata, and a default boundary
- `POST /api/zones/generate`
  - Accepts `data_id`, `boundary_geojson`, and `num_classes`
  - Returns zone GeoJSON, GVF values, class breaks, and legend colors
- `POST /api/export`
  - Accepts `data_id` and `format`
  - Returns GeoJSON or zipped Shapefile output
- `GET /api/health`
  - Basic health check for local dev and deployment

## Processing Pipeline

```text
Upload/sample data
  -> load_to_gdf() / load_multiple_to_gdf()
  -> detect CRS + value column
  -> derive convex-hull boundary for initial review
  -> reproject to field UTM CRS
  -> interpolate an adaptive-resolution raster
  -> compute GVF curve with MiniBatchKMeans
  -> classify raster cells with KMeans
  -> polygonize and clip zone geometries
  -> reproject to EPSG:4326
  -> export GeoJSON or zipped Shapefile
```

## Development Notes

- Frontend state lives in Pinia and tracks the active step plus the current `data_id`.
- The SPA does not use Vue Router; step transitions are store-driven.
- Internal geoprocessing happens in projected CRS, while API responses are EPSG:4326 GeoJSON.
- Runtime quality/performance is controlled by `EZZONE_PROFILE` in `backend/src/geo.py`.
- Production container builds the Vite frontend first, then serves it through Flask.

## Deployment

- Local production-style run: `pixi run start`
- Linux container entrypoint: `pixi run start-prod`
- Railway health check: `/api/health`
- Optional app-level error tracking: set `SENTRY_DSN` to enable Flask exception reporting via `sentry-sdk`

## Railway Notifications

There are two easy paths:

- Railway-native monitoring for service health, logs, and metrics
- Sentry for actual Flask exception notifications

For EZZone specifically, `SENTRY_DSN` is the quickest route to "tell me when the app throws" because it captures unhandled backend exceptions without requiring a custom polling service.
