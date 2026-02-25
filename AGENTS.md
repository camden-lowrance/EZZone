# Agent Development Guide

This document provides guidelines for AI agents working on the ezzone-pyanywhere project.

## Project Overview

**ezzone-pyanywhere** is an agricultural management zone generation web application built with:
- **Frontend:** Vue.js with Vite
- **Backend:** Python Flask API
- **Geospatial:** GDAL, rasterio, shapely, geopandas
- **Environment:** Pixi for dependency management

## Development Environment Setup

### Using Pixi (Recommended)

1. **Install Pixi** (if not already installed):
   ```bash
   # Windows
   winget install prefix-dev.pixi
   
   # Or download from https://pixi.sh/install
   ```

2. **Install dependencies:**
   ```bash
   pixi install
   ```

3. **Start development environment:**
   ```bash
   # Full stack development (frontend + backend)
   pixi run dev
   
   # Backend only
   pixi run dev-be
   
   # Frontend only  
   pixi run dev-fe
   
   # Production server
   pixi run start
   ```

### Alternative: Direct Python

If Pixi is not available:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Flask development server
python -m flask --app src.app:create_app run --reload --debug
```

## Project Structure

```
ezzone-pyanywhere/
├── backend/
│   └── src/                # Python backend code
│       ├── app.py          # Flask application entry point
│       ├── api.py          # API endpoints
│       ├── geo/            # Geospatial processing core
│       │   ├── geo_core.py # Main geospatial algorithms
│       │   └── __init__.py
│       ├── zones/          # Zone generation service
│       │   ├── service.py  # Zone generation logic
│       │   └── __init__.py
│       └── static/         # Backend static assets
├── frontend/               # Vue.js frontend code
│   ├── App.vue            # Main Vue component
│   ├── main.js            # Vue entry point
│   ├── style.css          # Global styles
│   ├── components/        # Vue components
│   ├── router/            # Vue router
│   ├── stores/            # Vue state management
│   └── views/             # Vue views
├── static/                # Shared web assets (OpenLayers, etc.)
├── tests/                 # Test suite
├── pixi.toml             # Environment configuration
└── package.json          # Frontend dependencies
```

## Key Technologies

### Backend (Python)
- **Flask**: Web framework
- **GDAL**: Geospatial data processing (required dependency)
- **rasterio**: Raster data processing
- **shapely**: Geometric operations
- **geopandas**: GeoDataFrame operations
- **numpy/scipy**: Scientific computing
- **jenkspy**: Statistical classification

### Frontend (JavaScript/Vue)
- **Vue 3**: Frontend framework
- **Vite**: Build tool
- **OpenLayers**: Map rendering
- **Bootstrap**: UI components

## Development Guidelines

### Python Code Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Import GDAL directly (no fallbacks)
- Use in-memory processing where possible

### Geospatial Processing
- **GDAL is required** - no fallback mechanisms
- Use `polygonize_classes_fast()` for raster polygonization
- Maintain 5m fixed resolution for performance
- Use vectorized operations with numpy

### API Development
- Use Flask blueprints for organization
- Return GeoJSON for spatial data
- Handle coordinate system transformations properly
- Use consistent error handling

### Frontend Development
- Use Vue 3 Composition API
- Follow component-based architecture
- Handle map interactions through OpenLayers
- Use reactive state management

## Common Tasks

### Adding New Dependencies

**Python dependencies:**
```bash
# Add to pixi.toml
pixi add package_name

# Or specify version
pixi add package_name=1.2.3
```

**JavaScript dependencies:**
```bash
npm install package-name
```

### Running Tests
```bash
# Python tests
pixi run test

# Python tests with coverage
pixi run test-cov

# Frontend tests (if configured)
npm test
```

### Building for Production
```bash
# Build frontend
pixi run build

# Start production server
pixi run start
```

### Development Workflow
```bash
# 1. Install dependencies
pixi install

# 2. Start development servers
pixi run dev

# 3. Make changes to code

# 4. Run tests
pixi run test

# 5. Build for production
pixi run build
```

## Important Notes

### GDAL Dependency
- GDAL version 3.12.2 is pinned in `pixi.toml`
- **No fallback mechanisms** - GDAL is required
- Fast polygonization uses `polygonize_classes_fast()` exclusively
- Ensure GDAL is properly installed in all environments

### Performance Considerations
- Target: <1 second polygonization for typical datasets
- Use fixed 5m resolution for consistent performance
- Prefer in-memory processing over file I/O
- Use vectorized numpy operations

### Coordinate Systems
- Input coordinates typically in EPSG:4326 (WGS84)
- Processing done in UTM zones for accuracy
- Output GeoJSON in EPSG:4326
- Use `pyproj` for transformations

### Error Handling
- Handle GDAL import errors gracefully
- Validate input data before processing
- Return meaningful error messages in API responses
- Log errors appropriately

## Troubleshooting

### Common Issues

**GDAL Import Errors:**
```bash
# Reinstall GDAL
pixi remove gdal
pixi add gdal=3.12.2
```

**Python Path Issues:**
```bash
# Ensure pixi environment is activated
pixi shell
python -c "import gdal; print(gdal.__version__)"
```

**Frontend Build Issues:**
```bash
# Clean and rebuild
rm -rf node_modules dist
npm install
pixi run build
```

### Debug Commands
```bash
# Check installed versions
pixi list

# Check Python environment
python --version
python -c "import sys; print(sys.path)"

# Test GDAL functionality
python -c "from osgeo import gdal; print('GDAL OK')"
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make changes following guidelines**
4. **Run tests and build**
5. **Submit pull request**

### Code Review Checklist
- [ ] Follows Python/JavaScript style guides
- [ ] Includes appropriate type hints
- [ ] Handles GDAL dependencies correctly
- [ ] Maintains performance standards
- [ ] Includes tests for new functionality
- [ ] Updates documentation if needed

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [GDAL Python API](https://gdal.org/python/)
- [Vue 3 Guide](https://vuejs.org/guide/introduction.html)
- [Pixi Documentation](https://pixi.sh/)
- [OpenLayers Documentation](https://openlayers.org/)