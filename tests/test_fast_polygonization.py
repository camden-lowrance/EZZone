"""
Test script for fast polygonization implementation.

This script tests the performance and correctness of the new fast polygonization
function compared to the original implementation.
"""

import time
import numpy as np
from shapely.geometry import Polygon
import pyproj
from src.geo.geo_core import polygonize_classes, polygonize_classes_fast, classify_raster
from src.geo.geo_core import interpolate_raster, reproject_poly, utmzone, bound_json


def create_test_data():
    """Create test data for polygonization."""
    # Create a simple test boundary in WGS84 coordinates
    boundary_coords = [
        (-84.0, 34.0), (-83.9, 34.0), (-83.9, 34.1), (-84.0, 34.1), (-84.0, 34.0)
    ]
    boundary = Polygon(boundary_coords)
    
    # Create test point data
    np.random.seed(42)
    x = np.random.uniform(-84.0, -83.9, 100)
    y = np.random.uniform(34.0, 34.1, 100)
    z = np.random.uniform(0, 100, 100)
    
    return x, y, z, boundary


def test_polygonization_performance():
    """Test the performance of both polygonization methods."""
    print("Testing polygonization performance...")
    
    # Create test data
    x, y, z, boundary = create_test_data()
    
    # Get UTM CRS and reproject boundary
    utm_crs = utmzone(boundary)
    boundary_utm = reproject_poly(boundary, in_projection='epsg:4326', out_projection=utm_crs)
    
    # Interpolate to raster
    array, bounds = interpolate_raster(x, y, z, 'epsg:4326', utm_crs, boundary_utm)
    
    # Classify raster
    classified, class_breaks = classify_raster(array, 3)
    
    print(f"Raster size: {array.shape}")
    print(f"Number of classes: {len(class_breaks)}")
    
    # Test original method
    print("\nTesting original polygonization method...")
    start_time = time.time()
    try:
        gdf_original = polygonize_classes(classified, bounds, boundary_utm, utm_crs)
        original_time = time.time() - start_time
        print(f"Original method time: {original_time:.4f} seconds")
        print(f"Original method polygons: {len(gdf_original)}")
    except Exception as e:
        print(f"Original method failed: {e}")
        original_time = None
        gdf_original = None
    
    # Test fast method
    print("\nTesting fast polygonization method...")
    start_time = time.time()
    try:
        gdf_fast = polygonize_classes_fast(classified, bounds, boundary_utm, utm_crs)
        fast_time = time.time() - start_time
        print(f"Fast method time: {fast_time:.4f} seconds")
        print(f"Fast method polygons: {len(gdf_fast)}")
    except Exception as e:
        print(f"Fast method failed: {e}")
        fast_time = None
        gdf_fast = None
    
    # Compare results
    if gdf_original is not None and gdf_fast is not None:
        print(f"\nPerformance improvement: {original_time / fast_time:.2f}x faster")
        
        # Check if results are similar (they should be)
        original_area = sum(gdf_original.geometry.area)
        fast_area = sum(gdf_fast.geometry.area)
        area_diff = abs(original_area - fast_area) / original_area
        
        print(f"Area difference: {area_diff:.4f}")
        if area_diff < 0.01:  # Less than 1% difference
            print("✓ Results are consistent")
        else:
            print("⚠ Results differ significantly")
    
    return original_time, fast_time


def test_large_dataset():
    """Test with a larger dataset to see performance scaling."""
    print("\n" + "="*50)
    print("Testing with larger dataset...")
    
    # Create larger test data
    np.random.seed(42)
    x = np.random.uniform(0, 1000, 1000)
    y = np.random.uniform(0, 1000, 1000)
    z = np.random.uniform(0, 100, 1000)
    
    # Create larger boundary
    boundary_coords = [
        (0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)
    ]
    boundary = Polygon(boundary_coords)
    
    # Get UTM CRS and reproject boundary
    utm_crs = utmzone(boundary)
    boundary_utm = reproject_poly(boundary, in_projection='epsg:4326', out_projection=utm_crs)
    
    # Interpolate to raster
    array, bounds = interpolate_raster(x, y, z, 'epsg:4326', utm_crs, boundary_utm)
    
    # Classify raster
    classified, class_breaks = classify_raster(array, 5)
    
    print(f"Large raster size: {array.shape}")
    print(f"Number of classes: {len(class_breaks)}")
    
    # Test fast method with larger dataset
    start_time = time.time()
    try:
        gdf_fast = polygonize_classes_fast(classified, bounds, boundary_utm, utm_crs)
        fast_time = time.time() - start_time
        print(f"Fast method time (large dataset): {fast_time:.4f} seconds")
        print(f"Fast method polygons (large dataset): {len(gdf_fast)}")
        
        if fast_time < 1.0:
            print("✓ Performance goal achieved: <1 second")
        else:
            print("⚠ Performance goal not met: >1 second")
            
    except Exception as e:
        print(f"Fast method failed on large dataset: {e}")


if __name__ == "__main__":
    print("Fast Polygonization Test Script")
    print("="*50)
    
    # Test basic performance
    original_time, fast_time = test_polygonization_performance()
    
    # Test with larger dataset
    test_large_dataset()
    
    print("\n" + "="*50)
    print("Test completed!")