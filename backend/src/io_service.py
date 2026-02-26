"""
IO Service for handling various data formats and converting them to GeoDataFrames.
"""

from __future__ import annotations
import os
import tempfile
import shutil
import zipfile
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


class DataError(Exception):
    """User-facing data validation error with a code for the frontend."""
    def __init__(self, message: str, code: str = 'DATA_ERROR'):
        super().__init__(message)
        self.code = code

    def to_json(self) -> dict:
        return {'error': str(self), 'code': self.code}

def _detect_coord_cols(columns: list[str]) -> tuple[str, str] | None:
    """Find likely X/Y or Lat/Lon columns."""
    cols = [c.lower() for c in columns]
    x_names = {'x', 'lon', 'longitude', 'easting', 'long'}
    y_names = {'y', 'lat', 'latitude', 'northing'}
    
    x_col = next((c for i, c in enumerate(columns) if cols[i] in x_names), None)
    y_col = next((c for i, c in enumerate(columns) if cols[i] in y_names), None)
    
    return (x_col, y_col) if (x_col and y_col) else None

def _detect_z_col(df: pd.DataFrame, exclude: list[str]) -> str | None:
    """Choose the best numeric column for values."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude_lower = {c.lower() for c in exclude}
    candidates = [c for c in numeric_cols if c.lower() not in exclude_lower]
    return candidates[0] if candidates else (numeric_cols[0] if numeric_cols else None)

def load_to_gdf(filepath: str, z_col_req: str | None = None, crs_override: str | None = None) -> tuple[gpd.GeoDataFrame, str]:
    """
    Universally load a file (Vector, CSV, Excel) and return a GeoDataFrame 
    and the name of the selected Z column.
    """
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''

    if ext in ('csv', 'txt'):
        df = pd.read_csv(filepath, sep=None, engine='python')
    elif ext in ('xlsx', 'xls'):
        df = pd.read_excel(filepath)
    else:
        # Direct vector read (Shapefile, GeoJSON, etc.)
        try:
            gdf = gpd.read_file(filepath, engine='pyogrio')
        except Exception:
            raise DataError(
                f'Could not read "{os.path.basename(filepath)}".\n'
                f'Please upload a supported vector format: Shapefile (.zip), GeoJSON, GeoPackage, KML, CSV, or Excel.',
                'UNREADABLE_FILE'
            )
        df = None

    if df is not None:
        coords = _detect_coord_cols(df.columns.tolist())
        if not coords:
            raise DataError('Could not find X/Y or Lat/Lon columns. Expected columns named X, Y, Lon, Lat, Longitude, Latitude, Easting, or Northing.', 'MISSING_COORDS')
        
        # Clean numeric values (handle common string formats like commas for decimals)
        for col in coords:
            if df[col].dtype == object:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        df = df.dropna(subset=list(coords))
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[coords[0]], df[coords[1]]))
        gdf.set_crs(crs_override or 'epsg:4326', inplace=True)
        # Store coordinate column names to exclude them from Z detection later
        gdf._coord_cols = list(coords)
    else:
        gdf._coord_cols = []

    # Ensure point geometries
    if not all(gdf.geometry.type == 'Point'):
        gdf.geometry = gdf.geometry.centroid
    
    if gdf.crs is None:
        gdf.set_crs('epsg:4326', inplace=True)
    
    # Identify Z column
    if z_col_req in gdf.columns:
        z_col = z_col_req
        if not pd.api.types.is_numeric_dtype(gdf[z_col]):
            gdf[z_col] = pd.to_numeric(gdf[z_col].astype(str).str.replace(',', '.'), errors='coerce')
    else:
        exclude_cols = [gdf.geometry.name] + getattr(gdf, '_coord_cols', [])
        z_col = _detect_z_col(gdf, exclude=exclude_cols)
    
    if not z_col or gdf[z_col].isna().all():
        raise DataError(f'No valid numeric data found in column "{z_col_req or z_col}". Check that the column exists and contains numbers.', 'MISSING_Z_COL')

    return gdf, str(z_col)


# Extensions that load_to_gdf can handle directly
_VECTOR_EXTS = {'.shp', '.geojson', '.json', '.gpkg', '.kml', '.gml', '.csv', '.txt', '.xlsx', '.xls'}
# Sidecar extensions that belong to shapefiles — skip these as standalone files
_SHAPEFILE_SIDECARS = {'.dbf', '.shx', '.prj', '.cpg', '.sbn', '.sbx', '.fbn', '.fbx', '.ain', '.aih', '.atx', '.ixs', '.mxs', '.qix'}

def extract_zip_contents(zip_path: str) -> tuple[list[str], str]:
    """Extract a zip and return paths to all loadable vector files, plus the temp dir."""
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmpdir)
    found = []
    for root, _, files in os.walk(tmpdir):
        for f in files:
            if f.startswith('._'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in _SHAPEFILE_SIDECARS:
                found.append(os.path.join(root, f))
    if not found:
        raise DataError(f'No files found inside "{os.path.basename(zip_path)}".', 'EMPTY_ZIP')
    return found, tmpdir


def load_multiple_to_gdf(filepaths: list[str], z_col_req: str | None = None, crs_override: str | None = None) -> tuple[gpd.GeoDataFrame, str]:
    """Load multiple files with the same schema and concatenate them."""
    if len(filepaths) == 1:
        return load_to_gdf(filepaths[0], z_col_req, crs_override)

    gdfs = []
    skipped = []
    ref_cols = None
    for path in filepaths:
        try:
            gdf, _ = load_to_gdf(path, z_col_req, crs_override)
        except DataError:
            skipped.append(os.path.basename(path))
            continue
        cols = sorted(c for c in gdf.columns if c != gdf.geometry.name)
        if ref_cols is None:
            ref_cols = cols
        elif cols != ref_cols:
            missing = set(ref_cols) - set(cols)
            extra = set(cols) - set(ref_cols)
            detail = ''
            if missing: detail += f' Missing: {", ".join(sorted(missing))}.'
            if extra: detail += f' Extra: {", ".join(sorted(extra))}.'
            raise DataError(
                f'"{os.path.basename(path)}" has a different schema than the first file and cannot be merged.{detail}',
                'SCHEMA_MISMATCH'
            )
        gdfs.append(gdf)

    if not gdfs:
        skipped_names = ', '.join(skipped) if skipped else 'unknown files'
        raise DataError(f'No loadable vector files found. Skipped: {skipped_names}', 'NO_LOADABLE_FILES')

    combined = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
    combined._coord_cols = getattr(gdfs[0], '_coord_cols', [])

    # Re-detect z col on combined
    if z_col_req in combined.columns:
        z_col = z_col_req
    else:
        exclude_cols = [combined.geometry.name] + combined._coord_cols
        z_col = _detect_z_col(combined, exclude=exclude_cols)

    if not z_col or combined[z_col].isna().all():
        raise ValueError(f'No valid numeric data found in column "{z_col_req or z_col}"')

    return combined, str(z_col)
