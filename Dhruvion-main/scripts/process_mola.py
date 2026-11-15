"""Reproducible MOLA terrain processing pipeline.

This script is a documented template. It requires:
  - rasterio, numpy, scipy
  - A locally obtained MOLA MEGDR GeoTIFF or PDS product converted to GeoTIFF.

It does not download data automatically and does not fabricate measurements.
"""

import sys
from pathlib import Path

try:
    import numpy as np
    import rasterio
    from rasterio.warp import transform_bounds
    from scipy.ndimage import generic_filter
except Exception as e:
    print(f"Missing dependency: {e}")
    print("Install rasterio, numpy, scipy in the backend Python environment before running.")
    sys.exit(1)

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/mola_elevation.tif")
OUT_DIR = Path("data/processed/mola")
OUT_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT.exists():
    print(f"Input raster not found: {INPUT}")
    print("Obtain MOLA MEGDR data from NASA PDS and place it at the input path.")
    sys.exit(1)

with rasterio.open(INPUT) as src:
    print("CRS:", src.crs)
    print("Bounds:", src.bounds)
    print("Resolution:", src.res)
    print("NoData:", src.nodata)
    print("Shape:", src.shape)
    data = src.read(1)
    profile = src.profile.copy()

# Crop to Gale Crater region (approx). Adjust to verified bounds.
# Example bounds in degrees (lon_min, lat_min, lon_max, lat_max):
GALE_BOUNDS = (137.0, -6.0, 138.0, -4.5)

# Save cropped elevation (placeholder for actual crop logic)
elev_path = OUT_DIR / "gale_elevation.tif"
with rasterio.open(INPUT) as src:
    # NOTE: implement windowed read based on verified transform; this is a template.
    profile.update(count=1)
    with rasterio.open(elev_path, "w", **profile) as dst:
        dst.write(src.read(1), 1)
        if src.nodata is not None:
            dst.nodata = src.nodata

print(f"Wrote {elev_path}")
print("Slope/roughness derivation should be added here using documented formulas.")
print("NoData masks must be preserved through all calculations.")
