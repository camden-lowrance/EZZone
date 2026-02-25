# ezzone-pyanywhere

A Flask + Vue 3 web application that generates agricultural management zones from point-sampled field data (e.g., soil EC, yield monitor data, NDVI). Users upload a file, draw or confirm a field boundary on a map, and the app returns classified GeoJSON zones ready for use in variable-rate application systems.

---

## How It Works

1. **Upload** — User uploads any supported vector file (CSV, Excel, Shapefile, GeoJSON, KML, etc.) with point data. The app auto-detects coordinate columns and CRS.
2. **Boundary** — A convex-hull boundary is computed from the point cloud and displayed on an OpenLayers satellite map for the user to adjust.
3. **Interpolation** — Z values are interpolated to a 5m resolution raster grid using scipy `griddata` (linear), with NaN extrapolation at edges.
4. **Classification** — Raster pixels are classified directly using Jenks Natural Breaks. Goodness of Variance Fit (GVF) is computed for 2–10 classes to suggest an optimal number of zones.
5. **Polygonization** — The classified raster is polygonized via GDAL, clipped to the field boundary, and reprojected to EPSG:4326.
6. **Output** — Zones are returned as a GeoJSON FeatureCollection. Users can export as `.geojson` or Shapefile (`.zip`).

---

## Project Structure

```
backend/src/
├── app.py          # Flask factory, serves Vue SPA from dist/
├── api.py          # REST endpoints, diskcache session storage (UUID-keyed)
├── geo.py          # Core geospatial: boundaries, reprojection, interpolation, classification, polygonization
├── zones.py        # Zone generation orchestrator
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

---

## Environment Setup

Dependencies are managed with [pixi](https://prefix.dev/docs/pixi/) (conda-forge).

```bash
pixi install          # Install all dependencies (Python + Node)
pixi run dev          # Frontend (Vite) + backend (Flask) dev servers
pixi run dev-be       # Backend only (Flask --reload --debug)
pixi run dev-fe       # Frontend only (Vite)
pixi run start        # Build frontend, then serve via Flask
pixi run test         # pytest tests/
```

---

## Processing Pipeline

```
File Upload (any GDAL vector format)
    │
    ▼
load_to_gdf()         — auto-detect CRS, X/Y/Z columns
    │
    ▼
bound_json()           — convex hull boundary from point cloud (geopandas)
    │
    ▼
[User adjusts boundary on map]
    │
    ▼
reproject_poly()       — reproject boundary to UTM (geopandas)
    │
    ▼
interpolate_raster()   — scipy griddata → 5m 2D numpy raster
    │
    ▼
gvf_array()            — GVF for 2–10 classes (numpy + jenkspy)
    │
    ▼
[User selects number of zones from GVF chart]
    │
    ▼
classify_raster()      — Jenks Natural Breaks on raster pixels
    │
    ▼
polygonize_classes_fast() — GDAL polygonize → clip to boundary
    │
    ▼
GeoJSON FeatureCollection → export GeoJSON or Shapefile
```
