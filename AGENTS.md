# Agent Development Guide

Guidelines for AI agents working on the ezzone-pyanywhere project.

## Project Overview

**ezzone-pyanywhere** is an agricultural management zone generation web application. Users upload point-sampled field data (soil EC, yield, NDVI, etc.), draw a field boundary, classify into management zones, and export.

- **Frontend:** Vue 3 + Vite, OpenLayers (maps), Chart.js, Pinia (state)
- **Backend:** Python Flask API
- **Geospatial:** GDAL, rasterio, shapely, geopandas, scipy
- **Environment:** Pixi (conda-forge)

## Commands

```bash
pixi install                               # Install all dependencies
pixi run dev                               # Frontend + backend dev servers
pixi run dev-be                            # Backend only (Flask --reload --debug)
pixi run dev-fe                            # Frontend only (Vite)
pixi run start                             # Build frontend, then serve via Flask
pixi run build                             # Build frontend only
pixi run test                              # pytest tests/
pixi run test-cov                          # pytest with HTML coverage
pytest tests/test_mz_api.py                # Single test file
pytest tests/test_mz_api.py::test_name     # Single test
pixi add package_name                      # Add Python dependency
npm install package-name                   # Add JS dependency
```

## Project Structure

```
backend/src/
├── app.py          # Flask factory (create_app), serves Vue SPA from dist/
├── api.py          # REST endpoints, diskcache session storage (24hr, UUID-keyed)
├── geo.py          # Core geospatial: boundaries, reprojection, interpolation, classification, polygonization
├── zones.py        # Zone generation orchestrator + GVF computation
└── io_service.py   # Multi-format file loading (CSV, Excel, Shapefile, GeoJSON, KML)

frontend/
├── App.vue                    # Root component: 4-step wizard container
├── main.js                    # Vue entry point (Pinia setup)
├── style.css                  # Global dark theme
├── stores/zoneStore.js        # Pinia store: UI state + API calls
└── views/
    ├── HomeView.vue           # Step 1: File upload + Z-column config
    ├── DrawBoundaryView.vue   # Step 2: OpenLayers boundary editing
    ├── ZonesView.vue          # Step 3: GVF chart + zone preview
    └── FinalizeView.vue       # Step 4: Export (GeoJSON/Shapefile)

tests/
├── test_mz_api.py             # Core algorithm unit tests
├── test_integration.py        # Flask end-to-end tests
└── fixtures/test.csv          # Sample dataset
```

## Architecture

### API Endpoints

- `POST /api/session/init` — Upload file → load to GeoDataFrame → auto-detect CRS/Z-column → compute boundary → cache
- `POST /api/zones/generate` — Generate zones from cached data with custom boundary + num_classes
- `POST /api/export` — Export cached zones as GeoJSON or Shapefile (.zip)
- `GET /api/health` — Health check

### Processing Pipeline

```
Upload → load_to_gdf (auto-detect CRS/columns)
  → convex hull boundary → user edits boundary
  → reproject to UTM → interpolate to 5m raster (scipy)
  → classify (Natural Breaks / jenkspy) → polygonize (GDAL)
  → reproject to EPSG:4326 → serve as GeoJSON FeatureCollection
```

### Frontend

4-step wizard SPA. No Vue Router — step state managed in Pinia store (`zoneStore.js`). Vite proxies `/api` to `localhost:5000` in dev.

### State Management

- **Frontend:** Pinia store holds step, loading, error, dataId, config, results
- **Backend:** Stateless endpoints; diskcache stores session data keyed by UUID (24hr expiry)

## Key Constraints

- **GDAL is required** — no fallbacks. Pinned to 3.12.2 in pixi.toml.
- Fixed **5m raster resolution** for performance (target <1s polygonization).
- All spatial output is **EPSG:4326 GeoJSON**; internal processing uses UTM.
- Use `polygonize_classes_fast()` — not GDAL's built-in polygonize.
- Frontend uses **Vue 3 Composition API** and dark theme CSS variables.
- `conftest.py` adds `backend/` to `sys.path` so tests can `import src`.

## Code Style

- Python: PEP 8, type hints on function signatures, GDAL imported directly
- JavaScript: Vue 3 Composition API, component-based architecture
- Prefer in-memory processing over file I/O
- Use vectorized numpy operations for performance
