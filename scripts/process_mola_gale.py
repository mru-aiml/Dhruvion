"""Process the MOLA MEGDR tile megt00n090hb.img into Gale Crater terrain products."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.transform import from_origin

RAW = Path("data/raw/mola/megt00n090hb.img")
HDR = Path("data/raw/mola/megt00n090hb.hdr")
OUT = Path("data/processed/mola/gale")
OUT.mkdir(parents=True, exist_ok=True)

# Read raw big-endian int16
data = np.fromfile(RAW, dtype=">i2").reshape(5632, 11520).astype("int32")

# Crop to Gale Crater region (lon 137-138 E, lat -4.0 to -6.5)
# 128 px/deg
col0 = int((137.0 - 90.0) * 128)
col1 = int((138.0 - 90.0) * 128)
row0 = int((0.0 - (-4.0)) * 128)
row1 = int((0.0 - (-6.5)) * 128)
elev = data[row0:row1, col0:col1].copy()

# NoData = 0 (per ENVI header)
nodata = 0
mask = elev == nodata
elev = elev.astype("float32")
elev[mask] = np.nan

# CRS WKT from ENVI header
wkt = None
for line in HDR.read_text().splitlines():
    if line.strip().startswith("coordinate system string"):
        wkt = line.split("=", 1)[1].strip().strip("{}")
        break
crs = rasterio.crs.CRS.from_wkt(wkt)

# Transform for cropped region
transform = from_origin(137.0, -4.0, 1.0 / 128.0, 1.0 / 128.0)

profile = {
    "driver": "GTiff",
    "height": elev.shape[0],
    "width": elev.shape[1],
    "count": 1,
    "dtype": "float32",
    "crs": crs,
    "transform": transform,
    "nodata": float("nan"),
}

# Write elevation.tif (store 0 as nodata? use nan; but spec says preserve NoData. We'll use nan and also keep a 0 mask? GeoTIFF nodata nan)
with rasterio.open(OUT / "elevation.tif", "w", **profile) as dst:
    dst.write(np.where(np.isnan(elev), 0.0, elev).astype("float32"), 1)
    dst.nodata = 0.0

# Slope (degrees)
px_m = 463.0576672  # meters per pixel (Mars, 128 px/deg)
gy, gx = np.gradient(elev)
# np.gradient returns per-pixel; convert to per meter
slope_rad = np.arctan(np.sqrt((gx / px_m) ** 2 + (gy / px_m) ** 2))
slope_deg = np.degrees(slope_rad)
slope_deg[np.isnan(elev)] = np.nan
with rasterio.open(OUT / "slope.tif", "w", **profile) as dst:
    dst.write(np.where(np.isnan(slope_deg), 0.0, slope_deg).astype("float32"), 1)
    dst.nodata = 0.0

# Roughness (local std 3x3)
from scipy.ndimage import generic_filter
def _std(w):
    return np.std(w)
rough = generic_filter(elev, _std, size=3, mode="nearest")
rough[np.isnan(elev)] = np.nan
with rasterio.open(OUT / "roughness.tif", "w", **profile) as dst:
    dst.write(np.where(np.isnan(rough), 0.0, rough).astype("float32"), 1)
    dst.nodata = 0.0

# PNGs
def save_png(arr, name, cmap):
    fig, ax = plt.subplots(figsize=(8, 5))
    vmin = np.nanmin(arr)
    vmax = np.nanmax(arr)
    im = ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(name)
    fig.colorbar(im, ax=ax)
    fig.savefig(OUT / f"{name}.png", dpi=120, bbox_inches="tight")
    plt.close(fig)

save_png(elev, "elevation", "terrain")
save_png(slope_deg, "slope", "viridis")
save_png(rough, "roughness", "magma")

metadata = {
    "source_file": "megt00n090hb.img",
    "source_url": "https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.img",
    "instrument": "MOLA",
    "spacecraft": "Mars Global Surveyor",
    "product": "MEGDR topography tile, 128 px/deg",
    "coverage": {"lon_min": 137.0, "lon_max": 138.0, "lat_min": -6.5, "lat_max": -4.0},
    "crs": "Mars simple cylindrical (planetocentric), center longitude 180, radius 3396 km",
    "units": "meters",
    "nodata": 0.0,
    "resolution_px_per_deg": 128,
    "pixel_size_m": 463.0576672,
    "processing": {
        "crop": "integer pixel window",
        "slope": "arctan(sqrt(dz/dx^2+dz/dy^2)) in degrees, 463.0577 m/px",
        "roughness": "3x3 local standard deviation of elevation",
    },
    "provenance": "observed (MOLA) for elevation; derived for slope and roughness",
}
(OUT / "metadata.json").write_text(json.dumps(metadata, indent=2))
print("Done. Outputs in", OUT)
print("Elevation shape", elev.shape, "min", np.nanmin(elev), "max", np.nanmax(elev))
