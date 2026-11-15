#!/usr/bin/env python3
"""
05_process_terrain.py - Step 4A terrain derivatives from a VALIDATED DEM.

Outputs (in --out-dir, prefix = DEM file stem)
----------------------------------------------
<p>_elevation_m.tif          float32, NoData = NaN, metres (unit-converted only)
<p>_slope_deg.tif            float32, NoData = NaN, degrees (Horn 1981)
<p>_roughness_<method>_m.tif float32, NoData = NaN, metres
<p>_coverage_mask.tif        uint8: 0 = no elevation data,
                             1 = elevation + slope + roughness valid,
                             2 = elevation valid but derivative undefined
                                 (raster edge or adjacent to NoData)
<p>_{elevation,slope,roughness,coverage}.png   RGBA overlays, NoData transparent
<p>_overlay_metadata.json    lat/lon bounds, colour stretch, units, legend
<p>_terrain_provenance.json  input SHA-256, CRS, spacing, methods, statistics

All rasters share the input grid exactly (same CRS, transform, shape); this is
re-checked after writing. Inputs must be approved in
metadata/validated_dataset_catalog.json unless --skip-catalog-check is given.
Outputs are not recomputed when provenance shows the same input hash and
parameters (use --force to recompute).

Usage
-----
    python 05_process_terrain.py --dem raw/terrain/X.tif --elevation-units metre
    python 05_process_terrain.py --dem X.tif --roughness-method detrended_rms --window 5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (approved_in_catalog, data_root_default,  # noqa: E402
                             file_hashes, read_json, setup_logging,
                             utc_now_iso, write_json)
from terrain_math import (ROUGHNESS_METHODS, TerrainError, detrended_rms,  # noqa: E402
                          horn_slope_deg, pixel_ground_spacing, rgba_overlay,
                          tri_riley, units_to_metre_factor, valid_stats)

SCRIPT_VERSION = "1.0.0"


def write_raster(path: Path, arr, profile, dtype, nodata, tags: dict, units: str | None):
    import rasterio
    prof = profile.copy()
    prof.update(driver="GTiff", dtype=dtype, count=1, nodata=nodata,
                compress="deflate", predictor=3 if dtype == "float32" else 2,
                tiled=True, blockxsize=256, blockysize=256, BIGTIFF="IF_SAFER")
    if prof["width"] < 256 or prof["height"] < 256:
        prof.update(tiled=False)
        prof.pop("blockxsize", None)
        prof.pop("blockysize", None)
    tmp = path.with_name(path.name + ".part")
    with rasterio.open(tmp, "w", **prof) as dst:
        dst.write(arr.astype(dtype), 1)
        dst.update_tags(**tags)
        if units:
            dst.units = (units,)
    tmp.replace(path)


def save_png(path: Path, rgba: np.ndarray):
    from PIL import Image
    Image.fromarray(rgba, mode="RGBA").save(path, optimize=True)


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--dem", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--elevation-units", required=True,
                    help="Units documented for the DEM (e.g. metre). Required - never guessed.")
    ap.add_argument("--band", type=int, default=1)
    ap.add_argument("--roughness-method", default="tri_riley", choices=list(ROUGHNESS_METHODS))
    ap.add_argument("--window", type=int, default=3, help="window for detrended_rms (odd)")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-catalog-check", action="store_true",
                    help="ONLY for tests: bypass the validated-catalog gate")
    args = ap.parse_args(argv)

    import rasterio
    from pyproj import CRS, Transformer

    root = args.data_root.resolve()
    out_dir = (args.out_dir or root / "processed/terrain").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log = setup_logging("terrain", root / "metadata/logs/05_process_terrain.log")
    dem = args.dem if args.dem.is_absolute() else (root / args.dem)
    if not dem.exists():
        dem = args.dem.resolve()
    if not dem.exists():
        log.error("DEM not found: %s", args.dem)
        return 2

    if not args.skip_catalog_check:
        ok, why = approved_in_catalog(read_json(root / "metadata/validated_dataset_catalog.json"),
                                      dem, root)
        if not ok:
            log.error("DEM not approved for processing (%s). Run Step 3 first.", why)
            return 3

    fac = units_to_metre_factor(args.elevation_units)
    if fac is None:
        log.error("Elevation units '%s' not recognised as metre/kilometre - refusing.",
                  args.elevation_units)
        return 4

    prefix = dem.stem
    rmeth = args.roughness_method + (f"_w{args.window}" if args.roughness_method == "detrended_rms" else "")
    paths = {"elevation": out_dir / f"{prefix}_elevation_m.tif",
             "slope": out_dir / f"{prefix}_slope_deg.tif",
             "roughness": out_dir / f"{prefix}_roughness_{rmeth}_m.tif",
             "coverage": out_dir / f"{prefix}_coverage_mask.tif"}
    prov_path = out_dir / f"{prefix}_terrain_provenance.json"
    in_hash = file_hashes(dem)
    params = {"band": args.band, "elevation_units": args.elevation_units,
              "unit_factor_to_metre": fac, "roughness_method": args.roughness_method,
              "window": args.window, "script_version": SCRIPT_VERSION}
    prev = read_json(prov_path)
    if (prev and not args.force and prev.get("input", {}).get("sha256") == in_hash["sha256"]
            and prev.get("parameters") == params and all(p.exists() for p in paths.values())):
        log.info("Outputs up to date for %s (same input hash and parameters) - skipped", dem)
        return 0

    with rasterio.open(dem) as src:
        profile = src.profile.copy()
        crs = CRS.from_wkt(src.crs.to_wkt())
        transform = src.transform
        z = src.read(args.band).astype(np.float64)
        nod = src.nodata
        scale = src.scales[args.band - 1] if src.scales else 1.0
        offset = src.offsets[args.band - 1] if src.offsets else 0.0
        geo_bounds_native = src.bounds
    invalid = ~np.isfinite(z)
    if nod is not None and not np.isnan(nod):
        invalid |= (z == nod)
    z = z * scale + offset            # documented band scale/offset, if any
    z = z * fac                       # documented unit -> metres
    z[invalid] = np.nan               # NoData stays NoData (never zero)
    log.info("DEM %s: %dx%d, %d NoData px, scale=%s offset=%s",
             dem.name, z.shape[1], z.shape[0], int(invalid.sum()), scale, offset)

    try:
        dx, dy = pixel_ground_spacing(crs, transform, z.shape[0], z.shape[1])
    except TerrainError as exc:
        log.error("Cannot compute ground spacing: %s", exc)
        return 5
    slope = horn_slope_deg(z, dx, dy)
    rough = tri_riley(z) if args.roughness_method == "tri_riley" else detrended_rms(z, args.window)
    elev = z.astype(np.float32)
    cov = np.zeros(z.shape, np.uint8)
    ev = np.isfinite(elev)
    cov[ev & np.isfinite(slope) & np.isfinite(rough)] = 1
    cov[ev & ~(np.isfinite(slope) & np.isfinite(rough))] = 2

    base_tags = {"DHRUVION_SOURCE_DEM": str(dem.name),
                 "DHRUVION_SOURCE_SHA256": in_hash["sha256"],
                 "DHRUVION_CREATED_UTC": utc_now_iso(),
                 "DHRUVION_SCRIPT": f"05_process_terrain.py v{SCRIPT_VERSION}",
                 "DHRUVION_PROVENANCE": "DERIVED"}
    write_raster(paths["elevation"], elev, profile, "float32", float("nan"),
                 {**base_tags, "DHRUVION_METHOD": "Source elevation; NoData->NaN; "
                  f"x scale {scale} + offset {offset}; x {fac} to metres",
                  "DHRUVION_PROVENANCE": "OBSERVED (reformatted)"}, "metre")
    write_raster(paths["slope"], slope, profile, "float32", float("nan"),
                 {**base_tags, "DHRUVION_METHOD": "Horn (1981) 3x3; geodesic pixel spacing"},
                 "degree")
    write_raster(paths["roughness"], rough, profile, "float32", float("nan"),
                 {**base_tags, "DHRUVION_METHOD": ROUGHNESS_METHODS[args.roughness_method]},
                 "metre")
    write_raster(paths["coverage"], cov, profile, "uint8", None,
                 {**base_tags, "DHRUVION_METHOD": "0=no elevation;1=all valid;"
                  "2=elevation valid, derivative undefined"}, None)

    # Alignment re-check of every output against the input grid
    with rasterio.open(dem) as src:
        for k, p in paths.items():
            with rasterio.open(p) as o:
                if (o.crs != src.crs or o.transform != src.transform
                        or o.shape != src.shape):
                    log.error("ALIGNMENT FAILURE for %s", p)
                    return 6
    log.info("All outputs share the input grid (CRS, transform, shape)")

    stats = {"elevation_m": valid_stats(elev), "slope_deg": valid_stats(slope),
             "roughness_m": valid_stats(rough),
             "coverage_counts": {str(v): int((cov == v).sum()) for v in (0, 1, 2)}}

    # geographic bounds for web overlays
    from dhruvion_common import planetocentric_lonlat
    l, b, r, t = geo_bounds_native
    lon, lat = planetocentric_lonlat(crs)[0]([l, r, r, l], [b, b, t, t])
    overlay = {"bounds_latlon": {"south": float(min(lat)), "north": float(max(lat)),
                                 "west": float(min(lon)), "east": float(max(lon))},
               "leaflet_bounds": [[float(min(lat)), float(min(lon))],
                                  [float(max(lat)), float(max(lon))]],
               "latitude_type": "planetocentric",
               "longitude_direction": "east-positive",
               "image_projection": crs.name,
               "note": "PNG pixels are on the source raster grid. For an equirectangular "
                       "source a lat/lon image overlay is geometrically exact; do NOT place "
                       "it on a Web-Mercator (EPSG:3857) map without reprojection.",
               "layers": {}}
    if not args.no_png:
        specs = {"elevation": (elev, "terrain", "metre", "p02", "p98"),
                 "slope": (slope, "magma", "degree", None, None),
                 "roughness": (rough, "viridis", "metre", "p02", "p98")}
        for k, (arr, cmap, unit, lo, hi) in specs.items():
            st = valid_stats(arr)
            if st["n_valid"] == 0:
                continue
            vmin = st[lo] if lo else 0.0
            vmax = st[hi] if hi else min(45.0, st["p99"])
            png = out_dir / f"{prefix}_{k}.png"
            save_png(png, rgba_overlay(arr, cmap, vmin, vmax))
            overlay["layers"][k] = {"png": png.name, "colormap": cmap, "units": unit,
                                    "display_vmin": vmin, "display_vmax": vmax,
                                    "stretch": "linear; values outside clipped for display only"}
        rgba = np.zeros(cov.shape + (4,), np.uint8)
        rgba[cov == 0] = (90, 90, 90, 170)    # no data: grey
        rgba[cov == 2] = (230, 160, 30, 170)  # derivative undefined: amber
        png = out_dir / f"{prefix}_coverage.png"
        save_png(png, rgba)
        overlay["layers"]["coverage"] = {"png": png.name, "legend": {
            "transparent": "elevation, slope and roughness valid",
            "grey": "no elevation data", "amber": "elevation valid, slope/roughness undefined"}}
    write_json(out_dir / f"{prefix}_overlay_metadata.json", overlay)

    ground = {"dx_m_min": float(np.min(dx)), "dx_m_max": float(np.max(dx)),
              "dy_m_min": float(np.min(dy)), "dy_m_max": float(np.max(dy))}
    prov = {"created_utc": utc_now_iso(), "script": "05_process_terrain.py",
            "parameters": params,
            "input": {"path": str(dem), **in_hash, "crs": crs.name,
                      "crs_wkt": crs.to_wkt(), "transform": list(transform)[:6],
                      "shape": list(z.shape), "nodata": nod},
            "ground_spacing": ground,
            "methods": {"slope": "Horn (1981), 3x3 third-order finite difference, "
                                 "geodesic ground spacing on the CRS ellipsoid",
                        "roughness": ROUGHNESS_METHODS[args.roughness_method],
                        "nodata": "Windows containing NoData or the raster edge -> NaN"},
            "scale_note": "Derivatives are at the DEM pixel baseline "
                          f"(~{ground['dy_m_min']:.1f} m); not rover-scale.",
            "outputs": {k: p.name for k, p in paths.items()},
            "statistics": stats}
    write_json(prov_path, prov)
    log.info("Terrain outputs written to %s", out_dir)
    log.info(json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()
                             if kk in ("min", "max", "mean")} for k, v in stats.items()
                         if k != "coverage_counts"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
