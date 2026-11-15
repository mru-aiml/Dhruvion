#!/usr/bin/env python3
"""
06_process_ctx.py - Step 4 CTX imagery preparation for the Gale map.

* Clips a VALIDATED, map-projected CTX raster (mosaic tile, orthoimage) to the
  Gale AOI. Pixel values, data type, NoData and CRS are preserved exactly.
* Writes a transparent PNG overlay (only DECLARED NoData becomes transparent;
  no value is assumed to be NoData). Non-8-bit data are linearly stretched
  between the 2nd and 98th percentiles FOR DISPLAY ONLY.
* PNGs larger than --max-png-px on a side are produced at reduced resolution
  (average resampling); the decimation factor is recorded.
* Optional --reference-dem reports alignment (SAME_GRID / SAME_CRS_DIFFERENT_GRID
  / DIFFERENT_CRS / NO_OVERLAP). Imagery is NOT resampled onto the DEM grid.

Raw CTX EDRs (.IMG) are NOT map-projected; they require USGS ISIS3
(mroctx2isis, spiceinit, ctxcal, cam2map) before this script can use them.

Usage
-----
    python 06_process_ctx.py --image raw/ctx/<tile>.tif --reference-dem raw/terrain/<dem>.tif
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (approved_in_catalog, data_root_default,  # noqa: E402
                             file_hashes, parse_aoi, read_json, setup_logging,
                             snap_window_outward, utc_now_iso, write_json)

SCRIPT_VERSION = "1.0.0"


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--aoi", default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--reference-dem", type=Path, default=None)
    ap.add_argument("--max-png-px", type=int, default=8192)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-catalog-check", action="store_true",
                    help="ONLY for tests: bypass the validated-catalog gate")
    args = ap.parse_args(argv)

    import rasterio
    from PIL import Image
    from pyproj import CRS, Transformer
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    root = args.data_root.resolve()
    out_dir = (args.out_dir or root / "processed/ctx").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log = setup_logging("ctx", root / "metadata/logs/06_process_ctx.log")
    img = args.image if args.image.is_absolute() else root / args.image
    if not img.exists():
        log.error("Image not found: %s", img)
        return 2
    if not args.skip_catalog_check:
        ok, why = approved_in_catalog(
            read_json(root / "metadata/validated_dataset_catalog.json"), img, root)
        if not ok:
            log.error("Image not approved for processing (%s)", why)
            return 3

    aoi = parse_aoi(args.aoi)
    out_tif = out_dir / f"{img.stem}__GaleAOI_clip.tif"
    if out_tif.exists() and not args.force:
        log.info("Exists, not overwritten (use --force): %s", out_tif)
        return 0

    with rasterio.open(img) as src:
        crs = CRS.from_wkt(src.crs.to_wkt())
        from dhruvion_common import crs_max_offset_m, planetocentric_lonlat
        to_ll, from_ll = planetocentric_lonlat(crs)
        LON, LAT = np.meshgrid(np.linspace(aoi["min_lon_e"], aoi["max_lon_e"], 21),
                               np.linspace(aoi["min_lat"], aoi["max_lat"], 21))
        xs, ys = from_ll(LON.ravel(), LAT.ravel())
        win = from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform)
        win = snap_window_outward(win, src.width, src.height)
        data = src.read(window=win)
        prof = src.profile.copy()
        wt = src.window_transform(win)
        prof.update(driver="GTiff", width=int(win.width), height=int(win.height),
                    transform=wt, compress="deflate", tiled=False)
        prof.pop("blockxsize", None)
        prof.pop("blockysize", None)
        nod = src.nodata
        tags = src.tags()
    with rasterio.open(out_tif, "w", **prof) as dst:
        dst.write(data)
        dst.update_tags(**tags, DHRUVION_SOURCE=img.name,
                        DHRUVION_METHOD="AOI clip only; pixel values unchanged",
                        DHRUVION_PROVENANCE="OBSERVED (clipped)",
                        DHRUVION_CREATED_UTC=utc_now_iso())
    log.info("Clipped %s -> %s (%dx%d)", img.name, out_tif.name, win.width, win.height)

    # PNG overlay
    band = data[0].astype(np.float64)
    nodata_mask = np.zeros(band.shape, bool) if nod is None else (band == nod)
    nodata_mask |= ~np.isfinite(band)
    factor = max(1, int(np.ceil(max(band.shape) / args.max_png_px)))
    if factor > 1:
        with rasterio.open(out_tif) as c:
            shape = (c.height // factor, c.width // factor)
            band = c.read(1, out_shape=shape, resampling=Resampling.average).astype(np.float64)
            m = c.read_masks(1, out_shape=shape, resampling=Resampling.nearest)
            nodata_mask = (m == 0) | ~np.isfinite(band)
    valid = band[~nodata_mask]
    if prof["dtype"] == "uint8":
        gray, stretch = np.clip(band, 0, 255).astype(np.uint8), "none (8-bit DN as stored)"
    else:
        lo, hi = (np.percentile(valid, [2, 98]) if valid.size else (0, 1))
        gray = (np.clip((band - lo) / max(hi - lo, 1e-12), 0, 1) * 255).astype(np.uint8)
        stretch = f"linear p2..p98 ({lo:.6g}..{hi:.6g}) for display only"
    rgba = np.dstack([gray, gray, gray, np.where(nodata_mask, 0, 255).astype(np.uint8)])
    png = out_dir / f"{img.stem}__GaleAOI.png"
    Image.fromarray(rgba, "RGBA").save(png, optimize=True)

    l, t_ = wt.c, wt.f
    r, b = l + wt.a * win.width, t_ + wt.e * win.height
    lon, lat = to_ll([l, r, r, l], [b, b, t_, t_])
    lon, lat = [float(v) for v in lon], [float(v) for v in lat]
    meta = {"png": png.name, "geotiff": out_tif.name,
            "leaflet_bounds": [[min(lat), min(lon)], [max(lat), max(lon)]],
            "latitude_type": "planetocentric", "longitude_direction": "east-positive",
            "image_projection": crs.name, "decimation_factor": factor,
            "stretch": stretch,
            "nodata_handling": "declared NoData -> transparent" if nod is not None
            else "NO NoData declared in source: no pixel made transparent; verify black areas",
            "provenance": "OBSERVED imagery (clipped); PNG is a display product"}

    if args.reference_dem:
        dem = args.reference_dem if args.reference_dem.is_absolute() else root / args.reference_dem
        with rasterio.open(dem) as d, rasterio.open(out_tif) as c:
            dc, cc = CRS.from_wkt(d.crs.to_wkt()), CRS.from_wkt(c.crs.to_wkt())
            off = 0.0 if d.crs == c.crs else crs_max_offset_m(dc, cc)
            tol = 0.1 * min(list(d.res) + list(c.res))
            if d.crs != c.crs and off >= 5 * tol:   # >= half of the finer pixel
                res = "DIFFERENT_CRS"
            elif d.transform == c.transform and d.shape == c.shape:
                res = "SAME_GRID"
            else:
                db, cb = d.bounds, c.bounds
                overlap = not (db.right < cb.left or cb.right < db.left
                               or db.top < cb.bottom or cb.top < db.bottom)
                res = (("SAME_CRS_DIFFERENT_GRID" if d.crs == c.crs else
                        "EQUIVALENT_CRS_DIFFERENT_GRID" if off < tol else
                        "NEAR_EQUIVALENT_CRS_DIFFERENT_GRID") if overlap else "NO_OVERLAP")
            meta["alignment_with_dem"] = {"dem": dem.name, "result": res,
                                          "max_coordinate_offset_m": round(off, 3),
                                          "equivalence_tolerance_m": round(tol, 3),
                                          "dem_res": list(d.res), "image_res": list(c.res)}
        log.info("Alignment with DEM: %s", res)
    write_json(out_dir / f"{img.stem}__GaleAOI_overlay_metadata.json", meta)
    write_json(out_dir / f"{img.stem}__ctx_provenance.json",
               {"created_utc": utc_now_iso(), "script": f"06_process_ctx.py v{SCRIPT_VERSION}",
                "input": {"path": str(img), **file_hashes(img)}, "aoi": aoi,
                "window": {"col_off": int(win.col_off), "row_off": int(win.row_off),
                           "width": int(win.width), "height": int(win.height)},
                "outputs": [out_tif.name, png.name], "overlay": meta})
    return 0


if __name__ == "__main__":
    sys.exit(main())
