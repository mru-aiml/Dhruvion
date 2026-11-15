#!/usr/bin/env python3
"""
crop_for_upload.py - cut big Mars rasters down to the Gale Crater area so they
fit in an upload. Originals are never modified.

* Crops to Gale AOI: planetocentric latitude -7.0 to -3.8, longitude 136.2 to 139.4 E
  (v1.1: planetocentric latitude handled explicitly for ellipsoidal CRSs).
* If the crop is larger than --max-px pixels on its longest side, it is
  shrunk by a whole-number factor using AVERAGE resampling (NoData ignored).
  Small crops (e.g. MOLA 463 m) keep their original pixel values unchanged.
* Accepts .tif files or the Murray Lab CTX .zip directly (reads the .tif inside).
* Writes <name>__GaleAOI[_xN].tif plus a .provenance.json describing exactly
  what was done (source file, SHA-256, window, shrink factor).

Install once:   py -m pip install rasterio pyproj
Run:            py crop_for_upload.py "D:\\mars\\file1.tif" "D:\\mars\\ctx_tile.zip" --out "D:\\mars\\upload"
"""
import argparse
import hashlib
import json
import math
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds

AOI = (136.2, -7.0, 139.4, -3.8)  # west, south, east, north (deg, east-positive)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def gdal_path(p: Path) -> str:
    if p.suffix.lower() != ".zip":
        return str(p)
    with zipfile.ZipFile(p) as z:
        tifs = [n for n in z.namelist() if n.lower().endswith((".tif", ".tiff"))]
    if not tifs:
        raise ValueError("no .tif inside zip")
    return f"/vsizip/{p.as_posix()}/{max(tifs, key=len)}"


def crop(src_path: Path, out_dir: Path, max_px: int, do_hash: bool) -> None:
    with rasterio.open(gdal_path(src_path)) as src:
        crs = CRS.from_wkt(src.crs.to_wkt())
        base = crs.source_crs if crs.is_projected and crs.source_crs is not None else crs.geodetic_crs
        ocentric = any("planetocentric" in (ax.name or "").lower() for ax in base.axis_info)
        e = base.ellipsoid
        k = 1.0 if ocentric else (e.semi_minor_metre / e.semi_major_metre) ** 2
        to_r = Transformer.from_crs(base, crs, always_xy=True)
        pg = lambda lat_c: math.degrees(math.atan(math.tan(math.radians(lat_c)) / k))
        lons = [AOI[0] + (AOI[2] - AOI[0]) * i / 20 for i in range(21)]
        lats = [AOI[1] + (AOI[3] - AOI[1]) * i / 20 for i in range(21)]
        pts = [to_r.transform(lo, pg(la)) for lo in lons for la in lats]  # AOI is planetocentric
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w = from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform)
        c0, r0 = max(0, math.floor(w.col_off)), max(0, math.floor(w.row_off))
        c1 = min(src.width, math.ceil(w.col_off + w.width))
        r1 = min(src.height, math.ceil(w.row_off + w.height))
        if c1 <= c0 or r1 <= r0:
            print(f"SKIP {src_path.name}: does not overlap the Gale area")
            return
        win = Window(c0, r0, c1 - c0, r1 - r0)
        factor = max(1, math.ceil(max(win.width, win.height) / max_px))
        h, wd = math.ceil(win.height / factor), math.ceil(win.width / factor)
        data = src.read(window=win, out_shape=(src.count, h, wd),
                        resampling=Resampling.average if factor > 1 else Resampling.nearest)
        tr = src.window_transform(win) * rasterio.Affine.scale(win.width / wd, win.height / h)
        prof = src.profile.copy()
        prof.update(driver="GTiff", width=wd, height=h, transform=tr, compress="deflate",
                    tiled=True, blockxsize=256, blockysize=256, BIGTIFF="IF_SAFER")
        suffix = "" if factor == 1 else f"_x{factor}"
        out = out_dir / f"{src_path.stem}__GaleAOI{suffix}.tif"
        if out.exists():
            print(f"SKIP {out.name}: already exists")
            return
        with rasterio.open(out, "w", **prof) as dst:
            dst.write(data)
            dst.update_tags(**src.tags(), CROP_SOURCE=src_path.name,
                            CROP_NOTE="values unchanged" if factor == 1 else
                            f"average of {factor}x{factor} source pixels (NoData ignored)")
            if any(src.units):
                dst.units = src.units
        prov = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "script": "crop_for_upload.py", "source_file": str(src_path),
                "source_size_bytes": src_path.stat().st_size,
                "source_sha256": sha256(src_path) if do_hash else None,
                "aoi_west_south_east_north": AOI,
                "source_window": {"col_off": c0, "row_off": r0, "width": int(win.width),
                                  "height": int(win.height)},
                "source_pixel_size": list(src.res), "shrink_factor": factor,
                "output_pixel_size": [src.res[0] * win.width / wd, src.res[1] * win.height / h],
                "resampling": "none (values unchanged)" if factor == 1 else "average",
                "nodata": src.nodata, "crs": crs.name, "output": out.name}
    out.with_suffix(".provenance.json").write_text(json.dumps(prov, indent=2))
    mb = out.stat().st_size / 1e6
    print(f"OK   {src_path.name} -> {out.name}  ({wd}x{h} px, factor {factor}, {mb:.1f} MB)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("upload"))
    ap.add_argument("--max-px", type=int, default=4000, help="longest side of output")
    ap.add_argument("--no-hash", action="store_true", help="skip source SHA-256 (faster)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for f in a.files:
        try:
            crop(f, a.out, a.max_px, not a.no_hash)
        except Exception as e:
            print(f"FAIL {f.name}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
