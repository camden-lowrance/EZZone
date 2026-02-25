"""
IO Service for handling various data formats and converting them to GeoDataFrames.
"""

from __future__ import annotations
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

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

def load_to_gdf(filepath: str, z_col_req: str | None = None) -> tuple[gpd.GeoDataFrame, str]:
    """
    Universally load a file (Vector, CSV, Excel) and return a GeoDataFrame 
    and the name of the selected Z column.
    """
    ext = filepath.rsplit('.', 1)[-1].lower()
    
    if ext in ('csv', 'txt'):
        df = pd.read_csv(filepath, sep=None, engine='python')
    elif ext in ('xlsx', 'xls'):
        df = pd.read_excel(filepath)
    else:
        # Direct vector read (Shapefile, GeoJSON, etc.)
        gdf = gpd.read_file(filepath, engine='pyogrio')
        df = None

    if df is not None:
        coords = _detect_coord_cols(df.columns.tolist())
        if not coords:
            raise ValueError('Could not find X/Y or Lat/Lon columns in file.')
        
        # Clean numeric values (handle common string formats like commas for decimals)
        for col in coords:
            if df[col].dtype == object:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        df = df.dropna(subset=list(coords))
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[coords[0]], df[coords[1]]))
        gdf.set_crs('epsg:4326', inplace=True) # Default assumption for flat files

    # Ensure point geometries
    if not all(gdf.geometry.type == 'Point'):
        gdf.geometry = gdf.geometry.centroid
    
    if gdf.crs is None:
        gdf.set_crs('epsg:4326', inplace=True)
    
    # Identify Z column
    z_col = z_col_req if z_col_req in gdf.columns else _detect_z_col(gdf, exclude=[gdf.geometry.name])
    if not z_col:
        raise ValueError('No numeric data column found.')

    return gdf, str(z_col)
