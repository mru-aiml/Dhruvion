#!/usr/bin/env python3
"""
03_validate_rasters.py - Step 3 validation of terrain and CTX rasters.

Checks per raster
-----------------
CRS present and a MARS CRS (ellipsoid semi-major axis 3.37e6-3.40e6 m),
real georeferencing (non-identity, unrotated geotransform), native and ground
resolution (metres, geodesic), dimensions, data type, band count, NoData,
NaN/Inf/NoData pixel counts, units (file metadata -> manifest documentation ->
'NOT DECLARED'), Gale AOI coverage (41x41 sample grid, valid pixels only),
Gale centre coverage, and - for elevation rasters - physical plausibility
(Mars surface elevations lie roughly between -8.5 km and +21.3 km relative to
the areoid; values far outside indicate wrong units or scaling).

Pairwise alignment between elevation and imagery rasters is reported as
SAME_GRID, SAME_CRS_DIFFERENT_GRID, DIFFERENT_CRS or NO_OVERLAP.

Status vocabulary: VALIDATED, VALIDATED WITH LIMITATIONS, INVALID, INCOMPLETE.
(NOT AVAILABLE is assigned by 09_build_catalogs.py to datasets with no file.)

Usage
-----
    python 03_validate_rasters.py                          # scans raw/terrain, raw/ctx
    python 03_validate_rasters.py --rasters a.tif b.tif --role elevation
"""
from __future__ import annotations

import argparse
import itertools
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (GALE_CENTER_LAT, GALE_CENTER_LON_E,  # noqa: E402
                             data_root_default, parse_aoi, read_json,
                             setup_logging, utc_now_iso, write_json)

RASTER_EXT = {".tif", ".tiff", ".jp2", ".img", ".cub", ".vrt"}
MARS_A_RANGE = (3.37e6, 3.40e6)
ELEV_PLAUSIBLE_M = (-9000.0, 22000.0)


def guess_role(path: Path) -> str:
    n = path.name.lower()
    if re.search(r"slope", n):
        return "slope"
    if re.search(r"rough|tri", n):
        return "roughness"
    if re.search(r"dem|dtm|mola|elev|topo|megt|blenddem", n):
        return "elevation"
    return "imagery"


def documented_units(manifest: dict, root: Path, path: Path) -> str | None:
    try:
        rel = str(path.resolve().relative_to(root))
    except ValueError:
        rel = str(path)
    for r in (manifest or {}).get("records", []):
        if r.get("local_path") == rel and r.get("documented_units"):
            return r["documented_units"]
    return None


def validate_one(path: Path, role: str, aoi: dict, manifest: dict, root: Path, log) -> dict:
    import rasterio
    from pyproj import CRS, Transformer
    from terrain_math import TerrainError, pixel_ground_spacing

    rec = {"file": str(path), "role": role, "checked_utc": utc_now_iso(),
           "reasons_invalid": [], "reasons_incomplete": [], "limitations": []}
    try:
        src = rasterio.open(path)
    except Exception as exc:
        rec["reasons_invalid"].append(f"Cannot open with GDAL: {exc}")
        return finalize(rec)
    with src:
        rec.update(driver=src.driver, width=src.width, height=src.height,
                   band_count=src.count, dtype=src.dtypes[0], nodata=src.nodata,
                   transform=list(src.transform)[:6],
                   native_bounds=list(src.bounds))
        if src.crs is None:
            rec["reasons_invalid"].append("No CRS defined")
            return finalize(rec)
        crs = CRS.from_wkt(src.crs.to_wkt())
        rec["crs_name"] = crs.name
        rec["crs_wkt"] = crs.to_wkt()
        rec["crs_is_geographic"] = crs.is_geographic
        a = crs.ellipsoid.semi_major_metre if crs.ellipsoid else None
        rec["ellipsoid_semi_major_m"] = a
        rec["ellipsoid_semi_minor_m"] = crs.ellipsoid.semi_minor_metre if crs.ellipsoid else None
        if a is None or not (MARS_A_RANGE[0] <= a <= MARS_A_RANGE[1]):
            rec["reasons_invalid"].append(
                f"CRS body is not Mars (semi-major axis {a} m)")
            return finalize(rec)
        t = src.transform
        if t.is_identity:
            rec["reasons_invalid"].append("Identity geotransform - not georeferenced")
            return finalize(rec)
        if t.b or t.d:
            rec["limitations"].append("Rotated/sheared geotransform")
        rec["native_resolution"] = [abs(t.a), abs(t.e)]
        rec["native_units"] = crs.axis_info[0].unit_name
        try:
            dx, dy = pixel_ground_spacing(crs, t, src.height, src.width)
            rec["ground_spacing_m"] = {"dx_min": float(np.min(dx)),
                                       "dx_max": float(np.max(dx)),
                                       "dy_min": float(np.min(dy)),
                                       "dy_max": float(np.max(dy))}
        except TerrainError as exc:
            rec["limitations"].append(f"Ground spacing not computable: {exc}")

        # geographic bounds (densified edges)
        from dhruvion_common import crs_equivalent, planetocentric_lonlat  # noqa: F401
        to_ll, from_ll = planetocentric_lonlat(crs)
        l, b, r_, tp = src.bounds
        xs = np.concatenate([np.linspace(l, r_, 50), np.full(50, r_),
                             np.linspace(l, r_, 50), np.full(50, l)])
        ys = np.concatenate([np.full(50, b), np.linspace(b, tp, 50),
                             np.full(50, tp), np.linspace(b, tp, 50)])
        lon, lat = to_ll(xs, ys)
        rec["geographic_bounds"] = {"min_lon": float(np.nanmin(lon)),
                                    "max_lon": float(np.nanmax(lon)),
                                    "min_lat": float(np.nanmin(lat)),
                                    "max_lat": float(np.nanmax(lat)),
                                    "longitude_convention":
                                        "0-360 E" if np.nanmax(lon) > 180 else "-180..180 E",
                                    "latitude_type": "planetocentric"}

        # units
        file_units = [u for u in (src.units or ()) if u]
        doc_units = documented_units(manifest, root, path)
        if file_units:
            rec["units"], rec["units_source"] = file_units[0], "raster metadata"
        elif doc_units:
            rec["units"], rec["units_source"] = doc_units, "source documentation (download manifest)"
            rec["limitations"].append("Units not stored in file; taken from source documentation")
        else:
            rec["units"], rec["units_source"] = None, "NOT DECLARED"
            if role in ("elevation", "slope", "roughness"):
                rec["limitations"].append("Units not declared in file or documentation")

        # pixel statistics (block-wise, band 1)
        n_total = n_nodata = n_nan = n_inf = 0
        vmin, vmax, vsum, vcount = np.inf, -np.inf, 0.0, 0
        nod = src.nodata
        for _, win in src.block_windows(1):
            arr = src.read(1, window=win, masked=False).astype(np.float64)
            n_total += arr.size
            isnan = np.isnan(arr)
            isinf = np.isinf(arr)
            isnod = (arr == nod) if (nod is not None and not np.isnan(nod)) else np.zeros_like(isnan)
            n_nan += int(isnan.sum())
            n_inf += int(isinf.sum())
            n_nodata += int(isnod.sum())
            good = arr[~(isnan | isinf | isnod)]
            if good.size:
                vmin, vmax = min(vmin, good.min()), max(vmax, good.max())
                vsum += good.sum()
                vcount += good.size
        rec["pixel_counts"] = {"total": n_total, "valid": vcount,
                               "nodata_value": n_nodata, "nan": n_nan, "inf": n_inf,
                               "invalid_fraction": (1 - vcount / n_total) if n_total else None}
        if vcount == 0:
            rec["reasons_invalid"].append("No valid pixels")
            return finalize(rec)
        rec["value_range"] = {"min": vmin, "max": vmax, "mean": vsum / vcount}
        if role == "elevation":
            from terrain_math import units_to_metre_factor
            fac = units_to_metre_factor(rec["units"])
            if fac is not None:
                vmin_m, vmax_m = vmin * fac, vmax * fac
                if vmin_m < ELEV_PLAUSIBLE_M[0] or vmax_m > ELEV_PLAUSIBLE_M[1]:
                    rec["reasons_invalid"].append(
                        f"Elevation range {vmin:.1f}..{vmax:.1f} m is outside plausible "
                        f"Mars range {ELEV_PLAUSIBLE_M} - check units/scale/offset")
            if src.tags(1).get("scale_factor") or (src.scales and src.scales[0] != 1):
                rec["limitations"].append(
                    f"Band has scale/offset {src.scales[0]}/{src.offsets[0]}; apply before use")

        # AOI coverage on valid pixels
        glon = np.linspace(aoi["min_lon_e"], aoi["max_lon_e"], 41)
        glat = np.linspace(aoi["min_lat"], aoi["max_lat"], 41)
        GL, GT = np.meshgrid(glon, glat)
        pts_lon = np.concatenate([GL.ravel(), [GALE_CENTER_LON_E]])
        pts_lat = np.concatenate([GT.ravel(), [GALE_CENTER_LAT]])
        if rec["geographic_bounds"]["longitude_convention"] == "-180..180 E":
            pts_lon = np.where(pts_lon > 180, pts_lon - 360, pts_lon)
        X, Y = from_ll(pts_lon, pts_lat)
        rows, cols = rasterio.transform.rowcol(t, X, Y)
        rows, cols = np.asarray(rows), np.asarray(cols)
        inside = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        valid_pt = np.zeros(inside.shape, bool)
        idx = np.where(inside)[0]
        if idx.size:
            vals = np.array([v[0] for v in src.sample(list(zip(np.asarray(X)[idx],
                                                               np.asarray(Y)[idx])), 1)],
                            dtype=np.float64)
            ok = np.isfinite(vals)
            if nod is not None and not np.isnan(nod):
                ok &= vals != nod
            valid_pt[idx] = ok
        rec["aoi"] = aoi
        rec["aoi_valid_coverage_fraction"] = float(valid_pt[:-1].mean())
        rec["gale_center_covered_valid"] = bool(valid_pt[-1])

    if not rec["gale_center_covered_valid"]:
        rec["reasons_incomplete"].append(
            f"Gale centre ({GALE_CENTER_LAT}, {GALE_CENTER_LON_E}E) not covered by valid pixels")
    if rec["aoi_valid_coverage_fraction"] < 0.05:
        rec["reasons_incomplete"].append("Less than 5% of the Gale AOI covered by valid pixels")
    elif rec["aoi_valid_coverage_fraction"] < 0.99:
        rec["limitations"].append(
            f"Partial AOI coverage: {rec['aoi_valid_coverage_fraction']:.1%} of sample points valid")
    inv = rec["pixel_counts"]["invalid_fraction"] or 0
    if inv > 0.01:
        rec["limitations"].append(f"{inv:.1%} of pixels are NoData/NaN/Inf")
    if role == "imagery" and rec["units"] is None:
        rec["limitations"].append("Imagery DN units not declared (display use only)")
    return finalize(rec)


def finalize(rec: dict) -> dict:
    if rec["reasons_invalid"]:
        status = "INVALID"
    elif rec["reasons_incomplete"]:
        status = "INCOMPLETE"
    elif rec["limitations"]:
        status = "VALIDATED WITH LIMITATIONS"
    else:
        status = "VALIDATED"
    rec["validation_status"] = status
    from terrain_math import units_to_metre_factor
    units_ok = units_to_metre_factor(rec.get("units")) is not None
    rec["approved_for_processing"] = status in ("VALIDATED", "VALIDATED WITH LIMITATIONS") and (
        rec.get("role") != "elevation" or units_ok)
    if status.startswith("VALIDATED") and rec.get("role") == "elevation" and not units_ok:
        rec["limitations"].append("NOT approved for terrain derivatives: elevation units unconfirmed")
    return rec


def alignment(a: dict, b: dict) -> dict:
    out = {"a": a["file"], "b": b["file"]}
    if "crs_wkt" not in a or "crs_wkt" not in b:
        out["result"] = "NOT_ASSESSED"
        return out
    ga, gb = a["geographic_bounds"], b["geographic_bounds"]
    overlap = not (ga["max_lon"] < gb["min_lon"] or gb["max_lon"] < ga["min_lon"]
                   or ga["max_lat"] < gb["min_lat"] or gb["max_lat"] < ga["min_lat"])
    if not overlap:
        out["result"] = "NO_OVERLAP"
    else:
        from pyproj import CRS
        from dhruvion_common import crs_max_offset_m
        same = a["crs_wkt"] == b["crs_wkt"]
        off = 0.0 if same else crs_max_offset_m(CRS.from_wkt(a["crs_wkt"]), CRS.from_wkt(b["crs_wkt"]))
        tol = 0.1 * min(list(a["native_resolution"]) + list(b["native_resolution"]))
        equiv = same or off < 5 * tol          # < half of the finer pixel
        out.update(max_coordinate_offset_m=off, equivalence_tolerance_m=tol)
        if not equiv:
            out["result"] = "DIFFERENT_CRS"
        elif a["transform"] == b["transform"] and (a["width"], a["height"]) == (b["width"], b["height"]):
            out["result"] = "SAME_GRID"
        else:
            out["result"] = ("SAME_CRS_DIFFERENT_GRID" if same else
                             "EQUIVALENT_CRS_DIFFERENT_GRID" if off < tol else
                             "NEAR_EQUIVALENT_CRS_DIFFERENT_GRID")
            out["note"] = ("Coordinates are interchangeable (checked numerically); grids differ, "
                           "so combine by coordinates, never by array index") if not same else None
        out["resolution_ratio"] = [a["native_resolution"][0] / b["native_resolution"][0],
                                   a["native_resolution"][1] / b["native_resolution"][1]]
    return out


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--rasters", type=Path, nargs="*")
    ap.add_argument("--role", default="auto",
                    choices=["auto", "elevation", "imagery", "slope", "roughness"])
    ap.add_argument("--aoi", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    out = args.out or root / "metadata/validation_rasters.json"
    log = setup_logging("validate_rasters", root / "metadata/logs/03_validate_rasters.log")
    aoi = parse_aoi(args.aoi)
    manifest = read_json(root / "metadata/download_manifest.json", default={})

    files = args.rasters or sorted(
        p for d in ("raw/terrain", "raw/ctx") for p in (root / d).rglob("*")
        if p.is_file() and p.suffix.lower() in RASTER_EXT and not p.name.endswith(".part"))
    results = []
    for f in files:
        role = guess_role(f) if args.role == "auto" else args.role
        try:
            rec = validate_one(Path(f), role, aoi, manifest, root, log)
        except Exception as exc:
            rec = finalize({"file": str(f), "role": role, "reasons_invalid":
                            [f"Validator error: {type(exc).__name__}: {exc}"],
                            "reasons_incomplete": [], "limitations": []})
        log.info("%-28s %s", rec["validation_status"], f)
        results.append(rec)
    pairs = [alignment(a, b) for a, b in itertools.combinations(results, 2)
             if {a.get("role"), b.get("role")} & {"elevation"}]
    write_json(out, {"generated_utc": utc_now_iso(), "aoi": aoi,
                     "n_rasters": len(results), "rasters": results,
                     "alignment_checks": pairs})
    log.info("Validated %d rasters -> %s", len(results), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
