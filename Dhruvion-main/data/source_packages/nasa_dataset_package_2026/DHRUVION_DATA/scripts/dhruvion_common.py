"""
dhruvion_common.py - shared helpers for the DHRUVION dataset pipeline.

Contents
--------
* Area-of-interest (AOI) constants for Gale Crater.
* Logging setup that writes to console and to a log file.
* File hashing (SHA-256 and MD5) for provenance and integrity checks.
* JSON / CSV writers used for manifests and catalogs.
* A no-overwrite guard: the pipeline never replaces an existing file
  unless the caller explicitly passes ``overwrite=True``.

Nothing in this module creates, alters or simulates scientific data.
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Area of interest
# ---------------------------------------------------------------------------
# Centre supplied by the DHRUVION project brief (planetocentric latitude,
# east-positive longitude).
GALE_CENTER_LAT = -5.4
GALE_CENTER_LON_E = 137.8

# Default AOI half-width in degrees. Gale Crater is roughly 154 km across;
# on the Mars reference sphere (R = 3 396 190 m) one degree of latitude is
# about 59.3 km, so +/-1.6 deg (~95 km from centre) encloses the crater rim
# with a margin. Override with --aoi on every script if needed.
DEFAULT_AOI_HALF_WIDTH_DEG = 1.6
DEFAULT_AOI = {
    "min_lat": round(GALE_CENTER_LAT - DEFAULT_AOI_HALF_WIDTH_DEG, 6),
    "max_lat": round(GALE_CENTER_LAT + DEFAULT_AOI_HALF_WIDTH_DEG, 6),
    "min_lon_e": round(GALE_CENTER_LON_E - DEFAULT_AOI_HALF_WIDTH_DEG, 6),
    "max_lon_e": round(GALE_CENTER_LON_E + DEFAULT_AOI_HALF_WIDTH_DEG, 6),
}

# IAU 2015 Mars reference sphere radius (metres). Used only as a sanity check
# that a raster's CRS is a Mars CRS; real computations use the radius / axes
# declared in each raster's own CRS.
MARS_SPHERE_RADIUS_M = 3_396_190.0

# Allowed validation status vocabulary (Step 3 brief).
VALIDATION_STATUSES = (
    "VALIDATED",
    "VALIDATED WITH LIMITATIONS",
    "INVALID",
    "INCOMPLETE",
    "NOT AVAILABLE",
)

# Provenance vocabulary (project brief).
PROVENANCE_CLASSES = ("OBSERVED", "DERIVED", "SIMULATED", "UNAVAILABLE")


def parse_aoi(text: str | None) -> dict:
    """Parse 'min_lat,max_lat,min_lon_e,max_lon_e' or return the default AOI."""
    if not text:
        return dict(DEFAULT_AOI)
    parts = [float(p) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("--aoi must be 'min_lat,max_lat,min_lon_e,max_lon_e'")
    min_lat, max_lat, min_lon, max_lon = parts
    if not (-90 <= min_lat < max_lat <= 90):
        raise ValueError(f"Invalid latitude range in AOI: {text}")
    if not (min_lon < max_lon):
        raise ValueError(f"Invalid longitude range in AOI: {text}")
    return {"min_lat": min_lat, "max_lat": max_lat,
            "min_lon_e": min_lon, "max_lon_e": max_lon}


# ---------------------------------------------------------------------------
# Paths, time, logging
# ---------------------------------------------------------------------------
def data_root_default() -> Path:
    """DHRUVION_DATA directory = parent of the scripts/ folder."""
    return Path(__file__).resolve().parent.parent


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def setup_logging(name: str, log_file: Path | None = None,
                  level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------
def file_hashes(path: Path, chunk: int = 4 * 1024 * 1024) -> dict:
    """Return {'sha256': ..., 'md5': ..., 'size_bytes': ...} for a file."""
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    size = 0
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            sha.update(block)
            md5.update(block)
            size += len(block)
    return {"sha256": sha.hexdigest(), "md5": md5.hexdigest(), "size_bytes": size}


class OverwriteRefused(FileExistsError):
    """Raised when an output path already exists and overwrite is not allowed."""


def ensure_writable(path: Path, overwrite: bool = False) -> Path:
    """Refuse to replace an existing file unless overwrite=True."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise OverwriteRefused(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# JSON / CSV writers
# ---------------------------------------------------------------------------
def _json_default(obj: Any):
    try:
        import numpy as np  # local import keeps module light
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return None if not np.isfinite(obj) else float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    return str(obj)


def _sanitize(obj: Any) -> Any:
    """Recursively replace NaN/Inf floats with None so output is strict JSON.

    Missing values become JSON null - never zero.
    """
    import math
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, np.floating):
            return float(obj) if np.isfinite(obj) else None
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return _sanitize(obj.tolist())
    except ImportError:
        pass
    return obj


def write_json(path: Path, data: Any, overwrite: bool = True) -> Path:
    path = ensure_writable(Path(path), overwrite=overwrite)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(_sanitize(data), fh, indent=2, default=_json_default,
                  allow_nan=False)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str] | None = None,
              overwrite: bool = True) -> Path:
    rows = list(rows)
    if fieldnames is None:
        fieldnames = []
        for r in rows:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
    path = ensure_writable(Path(path), overwrite=overwrite)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _flatten(r.get(k)) for k in fieldnames})
    os.replace(tmp, path)
    return path


def _flatten(v: Any) -> Any:
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, default=_json_default)
    return v


def read_json(path: Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Validation gate (Step 4 may only use Step 3-approved files)
# ---------------------------------------------------------------------------
def approved_in_catalog(catalog: dict, path: Path, root: Path) -> tuple[bool, str]:
    """Return (approved, status) for a file listed in validated_dataset_catalog.json."""
    if not catalog:
        return False, "validated_dataset_catalog.json not found"
    target = Path(path).resolve()
    for ds in catalog.get("datasets", []):
        for f in ds.get("files", []):
            p = Path(f.get("file", ""))
            p = p if p.is_absolute() else Path(root) / p
            if p.resolve() == target:
                ok = bool(f.get("approved_for_processing")) and f.get("validation_status") in (
                    "VALIDATED", "VALIDATED WITH LIMITATIONS")
                return ok, f.get("validation_status", "?")
    return False, "file not listed in validated catalog"


def snap_window_outward(win, max_width: int, max_height: int):
    """Expand a fractional rasterio Window to whole pixels (floor start, ceil end)
    and clip it to the raster extent. Explicit math - independent of rasterio
    version-specific rounding behaviour."""
    import math
    from rasterio.windows import Window
    c0 = max(0, math.floor(win.col_off))
    r0 = max(0, math.floor(win.row_off))
    c1 = min(max_width, math.ceil(win.col_off + win.width))
    r1 = min(max_height, math.ceil(win.row_off + win.height))
    if c1 <= c0 or r1 <= r0:
        raise ValueError("AOI window does not intersect the raster")
    return Window(c0, r0, c1 - c0, r1 - r0)


# ---------------------------------------------------------------------------
# Latitude convention: DHRUVION uses PLANETOCENTRIC latitude, east-positive
# longitude everywhere. For ellipsoidal Mars CRSs (e.g. the Murray Lab CTX
# "Mars_2015_Ocentric" CRS, a=3396190, b=3376200) PROJ may report geodetic
# (planetographic) latitude, which differs by up to ~0.06 deg near Gale.
# These helpers convert explicitly: tan(lat_c) = (b/a)^2 * tan(lat_g).
# ---------------------------------------------------------------------------
def planetocentric_lonlat(crs):
    """Return (to_lonlat, from_lonlat) using planetocentric latitude for any CRS."""
    import numpy as np
    from pyproj import Transformer
    base = crs.source_crs if crs.is_projected and crs.source_crs is not None else crs.geodetic_crs
    if base is None or not base.is_geographic:
        base = crs.geodetic_crs
    e = base.ellipsoid
    ocentric = any("planetocentric" in (ax.name or "").lower() for ax in base.axis_info)
    k = 1.0 if (ocentric or e is None) else (e.semi_minor_metre / e.semi_major_metre) ** 2
    fwd = Transformer.from_crs(crs, base, always_xy=True)
    inv = Transformer.from_crs(base, crs, always_xy=True)

    def to_lonlat(x, y):
        lon, lat = fwd.transform(x, y)
        return lon, np.degrees(np.arctan(k * np.tan(np.radians(lat))))

    def from_lonlat(lon, lat_c):
        lat_b = np.degrees(np.arctan(np.tan(np.radians(lat_c)) / k))
        return inv.transform(lon, lat_b)
    return to_lonlat, from_lonlat


def crs_max_offset_m(c1, c2, aoi: dict | None = None) -> float:
    """Largest difference (metres; geographic CRSs scaled at ~59 km/deg) between the
    projected coordinates two CRSs assign to the same planetocentric points in the AOI."""
    import numpy as np
    if c1 == c2:
        return 0.0
    a = aoi or DEFAULT_AOI
    L, T = np.meshgrid(np.linspace(a["min_lon_e"], a["max_lon_e"], 7),
                       np.linspace(a["min_lat"], a["max_lat"], 7))
    x1, y1 = planetocentric_lonlat(c1)[1](L.ravel(), T.ravel())
    x2, y2 = planetocentric_lonlat(c2)[1](L.ravel(), T.ravel())
    d = max(float(np.nanmax(np.abs(np.asarray(x1) - x2))), float(np.nanmax(np.abs(np.asarray(y1) - y2))))
    return d * 59000.0 if c1.is_geographic else d


def crs_equivalent(c1, c2, aoi: dict | None = None, tol_m: float = 1.0) -> bool:
    """True when both CRSs map the same planetocentric lon/lat points (over the AOI)
    to the same projected coordinates within tol_m - i.e. coordinates are interchangeable."""
    import numpy as np
    if c1 == c2:
        return True
    if c1.is_geographic != c2.is_geographic:
        return False
    a = aoi or DEFAULT_AOI
    L, T = np.meshgrid(np.linspace(a["min_lon_e"], a["max_lon_e"], 7),
                       np.linspace(a["min_lat"], a["max_lat"], 7))
    x1, y1 = planetocentric_lonlat(c1)[1](L.ravel(), T.ravel())
    x2, y2 = planetocentric_lonlat(c2)[1](L.ravel(), T.ravel())
    tol = tol_m if not c1.is_geographic else tol_m / 59000.0
    return bool(np.nanmax(np.abs(np.asarray(x1) - x2)) < tol and np.nanmax(np.abs(np.asarray(y1) - y2)) < tol)
