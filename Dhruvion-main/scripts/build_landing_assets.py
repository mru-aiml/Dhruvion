"""Build the landing-page hero raster assets from real NASA-derived data.

Outputs (served directly by Vite from frontend/public):
  frontend/public/assets/gale-ctx-mosaic.jpg
      Gale Crater CTX panchromatic mosaic, fetched from the NASA Mars Trek
      WMTS layer Gale_CTX_BlockAdj_dd at zoom 8 and composited locally.
  frontend/public/assets/gale-elevation-relief.jpg
      Hypsometric relief rendered from the local MOLA MEGDR crop
      (data/raw/mola/megt00n090hb.img), hillshaded, with NoData excluded.

No matplotlib plot output is written: the rasters are rendered with numpy/PIL.
"""

from __future__ import annotations

import io
import json
import math
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
RAW_MOLA = ROOT / "data/raw/mola/megt00n090hb.img"
TILE_CACHE = ROOT / "data/raw/trek/gale_ctx_z8"
OUT = ROOT / "frontend/public/assets"
OUT.mkdir(parents=True, exist_ok=True)
TILE_CACHE.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- CTX mosaic
Z = 8
# CTX coverage around Gale is a finite block; this window is fully populated
# and has a clean 3:2 aspect for the hero terrain viewport.
X0, X1 = 448, 454  # 135.0 E -> 139.21875 E
Y0, Y1 = 133, 137  # 3.515625 S -> 6.328125 S
TILE_URL = (
    "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/"
    "default/default028mm/{z}/{y}/{x}.png"
)
USER_AGENT = "DHRUVION/1.0 (NASA Space Apps Challenge prototype)"


def fetch_tile(z: int, x: int, y: int) -> tuple[int, int, np.ndarray, np.ndarray]:
    cached = TILE_CACHE / f"{z}_{y}_{x}.png"
    if cached.exists():
        payload = cached.read_bytes()
    else:
        url = TILE_URL.format(z=z, x=x, y=y)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            payload = b""
        if not payload:
            return x, y, np.zeros((256, 256), np.float32), np.zeros((256, 256), np.float32)
        if not payload.startswith(b"\x89PNG"):
            raise RuntimeError(f"Non-PNG response for tile {z}/{y}/{x}")
        cached.write_bytes(payload)
    image = Image.open(io.BytesIO(payload))
    if image.mode == "LA":
        lum = np.asarray(image.getchannel(0), dtype=np.float32)
        alpha = np.asarray(image.getchannel(1), dtype=np.float32)
    else:
        rgba = image.convert("RGBA")
        arr = np.asarray(rgba, dtype=np.float32)
        lum = arr[:, :, 0]
        alpha = arr[:, :, 3]
    return x, y, lum, alpha


def build_ctx_mosaic() -> dict:
    coords = [(x, y) for y in range(Y0, Y1) for x in range(X0, X1)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tiles = list(pool.map(lambda p: fetch_tile(Z, p[0], p[1]), coords))

    width = (X1 - X0) * 256
    height = (Y1 - Y0) * 256
    mosaic = np.zeros((height, width), dtype=np.float32)
    alpha = np.zeros((height, width), dtype=np.float32)
    for x, y, lum, tile_alpha in tiles:
        top = (y - Y0) * 256
        left = (x - X0) * 256
        mosaic[top : top + 256, left : left + 256] = lum
        alpha[top : top + 256, left : left + 256] = tile_alpha

    # The western tile of this block is only partly populated. Crop to the
    # observed alpha footprint instead of shipping transparent edges.
    ys, xs = np.nonzero(alpha > 0)
    top, bottom = int(ys.min()), int(ys.max()) + 1
    left, right = int(xs.min()), int(xs.max()) + 1
    mosaic = mosaic[top:bottom, left:right]
    alpha = alpha[top:bottom, left:right]

    coverage = float((alpha > 0).mean())
    if coverage < 0.97:
        raise RuntimeError(f"CTX mosaic coverage too low: {coverage:.3f}")

    valid = mosaic[alpha > 0]
    lo, hi = np.percentile(valid, [1.0, 99.0])
    stretched = np.clip((mosaic - lo) / max(hi - lo, 1e-6), 0.0, 1.0) ** 0.92
    stretched[alpha <= 0] = 0.0

    # Very slight warm bias so the panchromatic CTX mosaic sits in the HUD
    # palette. It stays labelled as observed CTX imagery, not colour data.
    rgb = np.stack(
        [
            np.clip(stretched * 1.045, 0, 1),
            np.clip(stretched * 0.985, 0, 1),
            np.clip(stretched * 0.930, 0, 1),
        ],
        axis=-1,
    )
    image = Image.fromarray((rgb * 255.0).round().astype(np.uint8), "RGB")
    image = image.filter(ImageFilter.UnsharpMask(radius=1.4, percent=55, threshold=3))
    target_h = round(1800 * mosaic.shape[0] / mosaic.shape[1])
    image.resize((1800, target_h), Image.LANCZOS).save(
        OUT / "gale-ctx-mosaic.jpg", quality=88, optimize=True, progressive=True
    )

    deg_per_tile_lon = 360.0 / (2 ** (Z + 1))
    deg_per_tile_lat = 180.0 / (2**Z)
    deg_per_px_lon = deg_per_tile_lon / 256.0
    deg_per_px_lat = deg_per_tile_lat / 256.0
    bounds = {
        "lon_min": X0 * deg_per_tile_lon - 180.0 + left * deg_per_px_lon,
        "lon_max": X0 * deg_per_tile_lon - 180.0 + right * deg_per_px_lon,
        "lat_max": 90.0 - Y0 * deg_per_tile_lat - top * deg_per_px_lat,
        "lat_min": 90.0 - Y0 * deg_per_tile_lat - bottom * deg_per_px_lat,
    }
    # Mars equatorial circumference ~21,339 km (radius 3,396 km).
    m_per_px = (2 * math.pi * 3_396_000 / 360.0) * deg_per_px_lon
    return {
        "asset": "/assets/gale-ctx-mosaic.jpg",
        "source": "NASA Mars Trek — Gale Crater CTX Block Adjacency mosaic",
        "product_id": "Gale_CTX_BlockAdj_dd",
        "provider": "NASA Mars Trek / JPL",
        "zoom": Z,
        "tile_range": {"x": [X0, X1 - 1], "y": [Y0, Y1 - 1]},
        "bounds": bounds,
        "mosaic_px": [int(mosaic.shape[1]), int(mosaic.shape[0])],
        "m_per_px": round(m_per_px, 1),
        "coverage": round(coverage, 4),
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Panchromatic CTX mosaic; slight warm bias applied for display only.",
    }

# ----------------------------------------------------------- Elevation relief
LON_MIN, LON_MAX = 135.5, 139.5
LAT_MIN, LAT_MAX = -6.8, -4.2
PX_DEG = 128
PIXEL_M = 463.0576672

PALETTE_STOPS = [
    (0.00, (42, 11, 46)),      # deep purple
    (0.18, (78, 16, 47)),      # burgundy
    (0.34, (124, 27, 44)),     # wine red
    (0.50, (166, 49, 44)),     # rust red
    (0.64, (198, 81, 46)),     # red-orange
    (0.78, (222, 124, 53)),    # orange
    (0.90, (238, 176, 92)),    # amber
    (1.00, (250, 225, 166)),   # pale gold
]


def palette(t: np.ndarray) -> np.ndarray:
    out = np.zeros(t.shape + (3,), dtype=np.float32)
    stops = np.array([s[0] for s in PALETTE_STOPS], dtype=np.float32)
    colors = np.array([s[1] for s in PALETTE_STOPS], dtype=np.float32) / 255.0
    for channel in range(3):
        out[:, :, channel] = np.interp(t, stops, colors[:, channel])
    return out


def build_elevation_relief() -> dict:
    raw = np.fromfile(RAW_MOLA, dtype=">i2").reshape(5632, 11520).astype(np.float64)
    row0 = int(round((0.0 - LAT_MAX) * PX_DEG))
    row1 = int(round((0.0 - LAT_MIN) * PX_DEG))
    col0 = int(round((LON_MIN - 90.0) * PX_DEG))
    col1 = int(round((LON_MAX - 90.0) * PX_DEG))
    elev = raw[row0:row1, col0:col1].copy()

    nodata = elev == 0.0
    valid = ~nodata
    vmin = float(elev[valid].min())
    vmax = float(elev[valid].max())

    # Fill the handful of NoData pixels from their nearest valid neighbour so
    # that gradients are well defined. NoData never becomes a fake zero value.
    if nodata.any():
        _, indices = distance_transform_edt(nodata, return_indices=True)
        filled = elev[tuple(indices)]
    else:
        filled = elev
    filled = np.where(nodata, np.nan, filled)

    gy, gx = np.gradient(filled, PIXEL_M)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    azimuth = math.radians(315.0)
    altitude = math.radians(42.0)
    shade = (
        np.sin(altitude) * np.cos(slope)
        + np.cos(altitude) * np.sin(slope) * np.cos(azimuth - aspect)
    )
    shade = np.clip(np.nan_to_num(shade, nan=0.7), 0.0, 1.0)

    t = np.clip((filled - vmin) / max(vmax - vmin, 1e-6), 0.0, 1.0)
    rgb = palette(t)
    rgb *= (0.42 + 0.88 * (shade ** 0.85))[:, :, None]
    rgb = np.clip(rgb, 0.0, 1.0)
    rgb[nodata] = (0.09, 0.055, 0.045)

    image = Image.fromarray((rgb * 255.0).round().astype(np.uint8), "RGB")
    image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=35, threshold=2))
    image.resize((1800, 1170), Image.LANCZOS).save(
        OUT / "gale-elevation-relief.jpg", quality=90, optimize=True, progressive=True
    )

    return {
        "asset": "/assets/gale-elevation-relief.jpg",
        "source": "MGS MOLA MEGDR topography tile megt00n090hb",
        "provider": "NASA PDS Geosciences",
        "coverage": {
            "lon_min": LON_MIN,
            "lon_max": LON_MAX,
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
        },
        "source_px": [int(elev.shape[1]), int(elev.shape[0])],
        "pixel_size_m": PIXEL_M,
        "min_m": round(vmin),
        "max_m": round(vmax),
        "nodata": 0.0,
        "nodata_pixels": int(nodata.sum()),
        "provenance": "observed MOLA elevation; hillshade and colour ramp are derived",
        "note": "NoData pixels are excluded from the elevation range and rendered dark.",
    }


def main() -> None:
    terrain = build_ctx_mosaic()
    elevation = build_elevation_relief()
    payload = {"terrain": terrain, "elevation": elevation}
    (OUT / "landing-visuals.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
