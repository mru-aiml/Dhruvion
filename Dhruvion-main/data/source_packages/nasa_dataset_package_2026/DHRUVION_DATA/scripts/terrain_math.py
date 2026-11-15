"""
terrain_math.py - slope, roughness and pixel-spacing computations for Mars DEMs.

Pixel spacing (never treat degrees as metres)
---------------------------------------------
Ground spacing is the GEODESIC distance between neighbouring pixel centres on
the raster's own body ellipsoid/sphere (read from its CRS), computed with
pyproj.Geod:
* geographic CRS (degrees): dx(row) = geodesic(lon, lat_row) -> (lon+dlon, lat_row),
  dy(row) = geodesic(lon, lat_row - dlat/2) -> (lon, lat_row + dlat/2).
* projected CRS (metres): pixel centres are inverse-projected to lon/lat and
  the geodesic distance to the right/lower neighbour is measured. This
  corrects projection scale distortion (e.g. equirectangular east-west
  stretching away from the standard parallel). If spacing varies across
  columns by more than 0.1 %, spacing is computed per pixel.
Rotated / sheared geotransforms are rejected.

Slope - Horn (1981)
-------------------
Horn, B.K.P. (1981) Hill shading and the reflectance map. Proc. IEEE 69(1),
14-47. Third-order finite difference over the 3x3 neighbourhood:
    dz/dx = ((c + 2f + i) - (a + 2d + g)) / (8 dx)
    dz/dy = ((g + 2h + i) - (a + 2b + c)) / (8 dy)
    slope = atan(sqrt(dz/dx^2 + dz/dy^2))   [degrees]
The centre row's dx is used for the window (standard approximation).

Roughness
---------
'tri_riley'     Terrain Ruggedness Index, Riley, DeGloria & Elliot (1999)
                Intermountain J. Sci. 5:23-27:
                TRI = sqrt( sum_{8 neighbours} (z_n - z_0)^2 )   [metres]
'detrended_rms' RMS of residuals after a least-squares plane fit in an
                N x N window (N odd), i.e. local relief with the regional
                slope removed so it is not double-counted with slope [metres].
Both are SCALE-DEPENDENT: values describe relief at the DEM's pixel baseline
(e.g. ~463 m for MOLA) and are not rover-scale roughness.

NoData
------
Any window containing NaN (or touching the raster edge) yields NaN. No
interpolation, no zero-filling.
"""
from __future__ import annotations

import numpy as np
from pyproj import CRS, Geod, Transformer
from scipy import ndimage


class TerrainError(ValueError):
    pass


_METRE = {"m", "metre", "metres", "meter", "meters"}
_KM = {"km", "kilometre", "kilometres", "kilometer", "kilometers"}


def units_to_metre_factor(units: str | None) -> float | None:
    """1.0 for metre aliases, 1000.0 for kilometre aliases, else None.

    Only exact (case-insensitive) unit names are accepted - no guessing.
    """
    if not units:
        return None
    u = units.strip().lower().strip("<>").strip()
    if u in _METRE:
        return 1.0
    if u in _KM:
        return 1000.0
    return None


def _geod_for(crs: CRS) -> Geod:
    e = crs.ellipsoid
    if e is None:
        raise TerrainError("CRS has no ellipsoid; cannot compute ground distances")
    return Geod(a=e.semi_major_metre, b=e.semi_minor_metre)


def pixel_ground_spacing(crs: CRS, transform, height: int, width: int,
                         rel_tol: float = 1e-3):
    """Return (dx, dy) ground spacing in metres.

    Arrays have shape (height, 1) when spacing depends on row only, or
    (height, width) otherwise.
    """
    if abs(transform.b) > 0 or abs(transform.d) > 0:
        raise TerrainError("Rotated/sheared geotransform not supported")
    geod = _geod_for(crs)
    a, e = transform.a, transform.e
    rows = np.arange(height) + 0.5

    if crs.is_geographic:
        unit = crs.axis_info[0].unit_name.lower()
        if "degree" not in unit:
            raise TerrainError(f"Geographic CRS with unexpected angular unit {unit}")
        lat = transform.f + rows * e
        lat = np.clip(lat, -90.0, 90.0)
        lon0 = np.full_like(lat, transform.c + 0.5 * a)
        _, _, dx = geod.inv(lon0, lat, lon0 + abs(a), lat)
        lat_a = np.clip(lat - abs(e) / 2, -90, 90)
        lat_b = np.clip(lat + abs(e) / 2, -90, 90)
        _, _, dy = geod.inv(lon0, lat_a, lon0, lat_b)
        return np.asarray(dx)[:, None], np.asarray(dy)[:, None]

    unit = (crs.axis_info[0].unit_name or "").lower()
    if unit not in ("metre", "meter", "m"):
        raise TerrainError(f"Projected CRS linear unit is '{unit}', expected metre")
    to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)

    def spacing_at(cols, rr):
        X = transform.c + (cols + 0.5) * a
        Y = transform.f + rr * e
        lon, lat = to_geo.transform(X, Y)
        lonx, latx = to_geo.transform(X + abs(a), Y)
        lony, laty = to_geo.transform(X, Y + abs(e))
        _, _, dx = geod.inv(lon, lat, lonx, latx)
        _, _, dy = geod.inv(lon, lat, lony, laty)
        return np.asarray(dx), np.asarray(dy)

    probe_cols = np.array([0, width // 2, width - 1], dtype=float)
    C, R = np.meshgrid(probe_cols, rows)
    dxp, dyp = spacing_at(C.ravel(), R.ravel())
    dxp = dxp.reshape(height, 3)
    dyp = dyp.reshape(height, 3)
    var_x = np.nanmax(np.abs(dxp - dxp[:, 1:2]) / dxp[:, 1:2])
    var_y = np.nanmax(np.abs(dyp - dyp[:, 1:2]) / dyp[:, 1:2])
    if max(var_x, var_y) <= rel_tol:
        return dxp[:, 1:2], dyp[:, 1:2]
    dx = np.empty((height, width))
    dy = np.empty((height, width))
    cols = np.arange(width, dtype=float)
    for r0 in range(0, height, 256):
        r1 = min(height, r0 + 256)
        C, R = np.meshgrid(cols, rows[r0:r1])
        bx, by = spacing_at(C.ravel(), R.ravel())
        dx[r0:r1] = bx.reshape(r1 - r0, width)
        dy[r0:r1] = by.reshape(r1 - r0, width)
    return dx, dy


# ---------------------------------------------------------------------------
def _blockwise(func, z: np.ndarray, halo: int, block_rows: int = 1024, **kw):
    """Apply func to row blocks with a halo; NaN-padded at raster edges."""
    H, W = z.shape
    out = np.full((H, W), np.nan, dtype=np.float32)
    for r0 in range(0, H, block_rows):
        r1 = min(H, r0 + block_rows)
        a0, a1 = max(0, r0 - halo), min(H, r1 + halo)
        blk = z[a0:a1].astype(np.float64)
        pad_top = halo - (r0 - a0)
        pad_bot = halo - (a1 - r1)
        blk = np.pad(blk, ((pad_top, pad_bot), (halo, halo)),
                     constant_values=np.nan)
        res = func(blk, r0=r0, r1=r1, **kw)
        out[r0:r1] = res[halo:-halo, halo:-halo].astype(np.float32)
    return out


def _horn_block(P, r0, r1, dx, dy):
    a, b, c = P[:-2, :-2], P[:-2, 1:-1], P[:-2, 2:]
    d, f = P[1:-1, :-2], P[1:-1, 2:]
    g, h, i = P[2:, :-2], P[2:, 1:-1], P[2:, 2:]
    dxb = dx[r0:r1] if dx.shape[0] > 1 else dx
    dyb = dy[r0:r1] if dy.shape[0] > 1 else dy
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8.0 * dxb)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8.0 * dyb)
    s = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    return np.pad(s, 1, constant_values=np.nan)


def horn_slope_deg(z: np.ndarray, dx: np.ndarray, dy: np.ndarray,
                   block_rows: int = 1024) -> np.ndarray:
    """Slope in degrees (Horn 1981). z in metres; dx, dy in metres."""
    dx = np.asarray(dx, dtype=np.float64)
    dy = np.asarray(dy, dtype=np.float64)
    if np.any(~np.isfinite(dx)) or np.any(dx <= 0) or np.any(~np.isfinite(dy)) \
            or np.any(dy <= 0):
        raise TerrainError("Non-positive or non-finite pixel spacing")
    out = _blockwise(_horn_block, z, 1, block_rows, dx=dx, dy=dy)
    # Horn's formula does not use the centre cell, so explicitly keep NoData
    # input cells as NoData in the output.
    out[~np.isfinite(z)] = np.nan
    return out


def _tri_block(P, r0, r1):
    z0 = P[1:-1, 1:-1]
    acc = np.zeros_like(z0)
    for di in (0, 1, 2):
        for dj in (0, 1, 2):
            if di == 1 and dj == 1:
                continue
            n = P[di:di + z0.shape[0], dj:dj + z0.shape[1]]
            acc += (n - z0) ** 2
    return np.pad(np.sqrt(acc), 1, constant_values=np.nan)


def tri_riley(z: np.ndarray, block_rows: int = 1024) -> np.ndarray:
    """Terrain Ruggedness Index (Riley et al. 1999), metres."""
    out = _blockwise(_tri_block, z, 1, block_rows)
    out[~np.isfinite(z)] = np.nan
    return out


def _rms_block(P, r0, r1, window):
    r = window // 2
    ref = np.nanmean(P) if np.isfinite(P).any() else 0.0
    Q = P - ref  # offset removal limits floating-point cancellation
    k = np.arange(-r, r + 1, dtype=np.float64)
    U = np.tile(k, (window, 1))          # column offset u
    V = U.T.copy()                        # row offset v
    ones = np.ones((window, window))
    n = window * window
    suu = window * np.sum(k ** 2)
    kw = dict(mode="constant", cval=np.nan)
    s1 = ndimage.correlate(Q, ones, **kw)
    s2 = ndimage.correlate(Q * Q, ones, **kw)
    su = ndimage.correlate(Q, U, **kw)
    sv = ndimage.correlate(Q, V, **kw)
    mean = s1 / n
    ss = s2 - n * mean ** 2 - (su ** 2) / suu - (sv ** 2) / suu
    # NaN propagates through correlate (cval=NaN), so any window touching
    # NoData or the raster edge is already NaN here.
    return np.sqrt(np.clip(ss, 0, None) / n)


def detrended_rms(z: np.ndarray, window: int = 3, block_rows: int = 1024) -> np.ndarray:
    """RMS residual (metres) about a least-squares plane in a window x window box."""
    if window < 3 or window % 2 == 0:
        raise TerrainError("window must be an odd integer >= 3")
    out = _blockwise(_rms_block, z, window // 2, block_rows, window=window)
    out[~np.isfinite(z)] = np.nan
    return out


ROUGHNESS_METHODS = {
    "tri_riley": "Terrain Ruggedness Index, Riley, DeGloria & Elliot (1999): "
                 "sqrt(sum over 8 neighbours of (z_n - z_0)^2), metres",
    "detrended_rms": "RMS of residuals from a least-squares plane fitted in an "
                     "N x N moving window (regional slope removed), metres",
}


# ---------------------------------------------------------------------------
def rgba_overlay(arr: np.ndarray, cmap_name: str, vmin: float, vmax: float) -> np.ndarray:
    """Colour-map an array to RGBA uint8; NaN pixels fully transparent."""
    import matplotlib
    cmap = matplotlib.colormaps[cmap_name]
    valid = np.isfinite(arr)
    span = (vmax - vmin) if vmax > vmin else 1.0
    norm = np.clip((np.where(valid, arr, vmin) - vmin) / span, 0, 1)
    rgba = (cmap(norm) * 255).astype(np.uint8)
    rgba[..., 3] = np.where(valid, 255, 0).astype(np.uint8)
    return rgba


def valid_stats(arr: np.ndarray) -> dict:
    v = arr[np.isfinite(arr)]
    if v.size == 0:
        return {"n_valid": 0, "n_nodata": int(arr.size)}
    p = np.percentile(v, [1, 2, 25, 50, 75, 98, 99])
    return {"n_valid": int(v.size), "n_nodata": int(arr.size - v.size),
            "min": float(v.min()), "max": float(v.max()), "mean": float(v.mean()),
            "std": float(v.std()), "p01": float(p[0]), "p02": float(p[1]),
            "p25": float(p[2]), "median": float(p[3]), "p75": float(p[4]),
            "p98": float(p[5]), "p99": float(p[6])}
