#!/usr/bin/env python3
"""
00_inventory_workspace.py - Step 1 inventory of a workspace.

* Walks one or more directories and lists candidate planetary data files
  (GeoTIFF, PDS3/PDS4 labels and tables, ISIS cubes, JPEG2000, archives).
* Flags names suggesting MOLA / CTX / HiRISE / DTM / slope / roughness /
  REMS / RAD content (name matching only - content is validated in Step 3).
* Records Python version, scientific/geospatial library versions, and free
  disk space.

Usage
-----
    python 00_inventory_workspace.py --scan /path/to/DHRUVION /another/path \
        --out ../metadata/workspace_inventory.json
"""
from __future__ import annotations

import argparse
import importlib
import platform
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, setup_logging, utc_now_iso,  # noqa: E402
                             write_json)

DATA_EXT = {".tif", ".tiff", ".img", ".lbl", ".tab", ".fmt", ".cub", ".jp2",
            ".xml", ".csv", ".dat", ".zip", ".tar", ".gz", ".vrt", ".png",
            ".pgw", ".tfw", ".aux"}
KEYWORDS = {
    "mola": r"mola|megdr|megt|pedr",
    "ctx": r"(^|[_\-])ctx|murray|blockadj|[a-z]\d\d_\d{6}_\d{4}",
    "hirise": r"hirise|esp_\d{6}|psp_\d{6}|dteec|dtems",
    "dtm_dem": r"dtm|dem|elev|topo",
    "slope": r"slope",
    "roughness": r"rough|tri\b",
    "rems": r"rems|rme_|modrdr|envrdr",
    "rad": r"(^|[_\-])rad([_\-]|$)|radrdr|rad_rdr",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache",
             "site-packages", "dist-packages"}
LIBS = ["numpy", "pandas", "scipy", "rasterio", "pyproj", "pvl", "matplotlib",
        "PIL", "requests", "geopandas", "shapely", "xarray", "rioxarray",
        "pds4_tools", "planetaryimage", "astropy", "skimage", "pytest"]


def scan(root: Path, max_files: int) -> list[dict]:
    hits = []
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file() or p.suffix.lower() not in DATA_EXT:
            continue
        name = p.name.lower()
        tags = [k for k, rx in KEYWORDS.items() if re.search(rx, name)]
        hits.append({"path": str(p), "size_bytes": p.stat().st_size,
                     "extension": p.suffix.lower(), "name_tags": tags})
        if len(hits) >= max_files:
            break
    return hits


def lib_versions() -> dict:
    out = {}
    for name in LIBS:
        try:
            mod = importlib.import_module(name)
            out[name] = getattr(mod, "__version__", "installed")
        except Exception:
            out[name] = None
    try:
        import rasterio
        out["gdal_via_rasterio"] = rasterio.__gdal_version__
    except Exception:
        out["gdal_via_rasterio"] = None
    try:
        import pyproj
        out["proj"] = pyproj.proj_version_str
    except Exception:
        out["proj"] = None
    return out


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", type=Path, nargs="+", default=[Path.cwd()])
    ap.add_argument("--out", type=Path, default=root / "metadata/workspace_inventory.json")
    ap.add_argument("--max-files", type=int, default=20000)
    args = ap.parse_args(argv)
    log = setup_logging("inventory", root / "metadata/logs/00_inventory_workspace.log")

    report = {"generated_utc": utc_now_iso(),
              "python": sys.version.split()[0],
              "platform": platform.platform(),
              "python_executable": sys.executable,
              "libraries": lib_versions(),
              "scanned_roots": [], "disk": {}}
    for r in args.scan:
        r = r.resolve()
        if not r.exists():
            log.warning("Scan root does not exist: %s", r)
            continue
        files = scan(r, args.max_files)
        tagged = [f for f in files if f["name_tags"]]
        log.info("%s: %d candidate data files, %d with Mars-product name tags",
                 r, len(files), len(tagged))
        report["scanned_roots"].append({"root": str(r), "n_files": len(files),
                                        "n_tagged": len(tagged), "files": files})
        du = shutil.disk_usage(r)
        report["disk"][str(r)] = {"total_bytes": du.total, "used_bytes": du.used,
                                  "free_bytes": du.free}
    write_json(args.out, report)
    log.info("Inventory written to %s", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
