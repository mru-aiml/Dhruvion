#!/usr/bin/env python3
"""
01_discover_ode_products.py - query the Mars Orbital Data Explorer (ODE) REST
interface for products intersecting the Gale Crater AOI.

For every query (IHID:IID:PT, e.g. MRO:CTX:EDR) the raw ODE response is saved
VERBATIM, then products are flattened into a CSV with footprint bounds and
file URLs so they can be reviewed before anything is downloaded.

Parameter names follow the ODE REST Interface Manual v2.1.6 (Feb 2024,
https://oderest.rsl.wustl.edu/ODE_REST_V2.1.6.pdf, confirmed by user research
2026-11-14): query=products, westernlon/easternlon/minlat/maxlat, loc=b
(bounding boxes intersect), results codes c,o,p,m,f,b,t,l,x, output XML|JSON.
A live query has still not been executed from the build environment; the raw
response is always saved so any error can be inspected.

Usage
-----
    python 01_discover_ode_products.py --query MRO:CTX:EDR --query MRO:HIRISE:DTM
    python 01_discover_ode_products.py --query MRO:CTX:EDR --results fp \
        --aoi -7.0,-3.8,136.2,139.4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (GALE_CENTER_LAT, GALE_CENTER_LON_E,  # noqa: E402
                             data_root_default, parse_aoi, setup_logging,
                             utc_now_iso, write_csv, write_json)

ODE_REST = "https://oderest.rsl.wustl.edu/live2/"


def find_products(obj) -> list[dict]:
    """Return every dict that carries a 'pdsid' key, wherever it is nested."""
    found = []
    if isinstance(obj, dict):
        if any(k.lower() == "pdsid" for k in obj):
            found.append(obj)
        for v in obj.values():
            found.extend(find_products(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(find_products(v))
    return found


def _get(d: dict, *names):
    lower = {k.lower(): v for k, v in d.items()}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def flatten(prod: dict, aoi: dict) -> dict:
    files = _get(prod, "Product_files") or {}
    flist = files.get("Product_file", []) if isinstance(files, dict) else files
    if isinstance(flist, dict):
        flist = [flist]
    urls = [f"{_get(f, 'Type') or ''}|{_get(f, 'FileName') or ''}|"
            f"{_get(f, 'KBytes') or ''}KB|{_get(f, 'URL') or ''}"
            for f in flist if isinstance(f, dict)]
    min_lat = _num(_get(prod, "Minimum_latitude"))
    max_lat = _num(_get(prod, "Maximum_latitude"))
    west = _num(_get(prod, "Westernmost_longitude"))
    east = _num(_get(prod, "Easternmost_longitude"))
    contains_center = None
    if None not in (min_lat, max_lat, west, east):
        contains_center = (min_lat <= GALE_CENTER_LAT <= max_lat
                           and west <= GALE_CENTER_LON_E <= east)
    return {
        "pdsid": _get(prod, "pdsid"),
        "ihid": _get(prod, "ihid"), "iid": _get(prod, "iid"),
        "pt": _get(prod, "pt"), "data_set_id": _get(prod, "Data_Set_Id"),
        "center_lat": _num(_get(prod, "Center_latitude")),
        "center_lon": _num(_get(prod, "Center_longitude")),
        "min_lat": min_lat, "max_lat": max_lat,
        "west_lon": west, "east_lon": east,
        "contains_gale_center_bbox": contains_center,
        "utc_start": _get(prod, "UTC_start_time"),
        "map_scale": _get(prod, "Map_scale"),
        "emission_angle": _get(prod, "Emission_angle"),
        "label_url": _get(prod, "LabelURL"),
        "product_url": _get(prod, "ProductURL"),
        "files": urls,
    }


def run_query(spec: str, aoi: dict, results: str, extra: dict, timeout: float, log):
    import requests
    ihid, iid, pt = spec.split(":")
    params = {"query": "products", "results": results, "output": "JSON", "loc": "b",
              "target": "mars", "ihid": ihid, "iid": iid, "pt": pt,
              "westernlon": aoi["min_lon_e"], "easternlon": aoi["max_lon_e"],
              "minlat": aoi["min_lat"], "maxlat": aoi["max_lat"]}
    params.update(extra)
    log.info("ODE query %s params=%s", spec, params)
    resp = requests.get(ODE_REST, params=params, timeout=timeout)
    return resp.url, resp.status_code, resp.text


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", action="append", default=[],
                    help="IHID:IID:PT, repeatable (default MRO:CTX:EDR)")
    ap.add_argument("--aoi", default=None, help="min_lat,max_lat,min_lon_e,max_lon_e")
    ap.add_argument("--results", default="fp",
                    help="ODE 'results' code (verify against ODE docs)")
    ap.add_argument("--extra", default="{}", help="JSON dict of extra ODE params")
    ap.add_argument("--out-dir", type=Path, default=root / "metadata/ode_discovery")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args(argv)

    log = setup_logging("ode_discovery", root / "metadata/logs/01_discover_ode_products.log")
    aoi = parse_aoi(args.aoi)
    queries = args.query or ["MRO:CTX:EDR"]
    extra = json.loads(args.extra)
    failures = 0
    for spec in queries:
        tag = spec.replace(":", "_")
        try:
            url, status, text = run_query(spec, aoi, args.results, extra,
                                          args.timeout, log)
        except Exception as exc:
            log.error("ODE query %s failed: %s", spec, exc)
            write_json(args.out_dir / f"ode_{tag}_ERROR.json",
                       {"query": spec, "aoi": aoi, "error": str(exc),
                        "when_utc": utc_now_iso()})
            failures += 1
            continue
        raw_path = args.out_dir / f"ode_{tag}_raw_response.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(text, encoding="utf-8")
        log.info("HTTP %s, raw response saved: %s", status, raw_path)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.error("Response is not JSON; first 500 chars:\n%s", text[:500])
            failures += 1
            continue
        prods = [flatten(p, aoi) for p in find_products(data)]
        if not prods:
            log.warning("No products parsed. Inspect %s (may be an ODE error "
                        "message or a parameter-name mismatch).", raw_path)
        write_csv(args.out_dir / f"ode_{tag}_products.csv", prods)
        write_json(args.out_dir / f"ode_{tag}_products.json",
                   {"query": spec, "request_url": url, "aoi": aoi,
                    "retrieved_utc": utc_now_iso(), "n_products": len(prods),
                    "products": prods})
        log.info("%s: %d products parsed", spec, len(prods))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
