#!/usr/bin/env python3
"""
02_download_datasets.py - download authoritative datasets listed in a plan.

Item types (see config/download_plan.json)
------------------------------------------
http_file      Download one file. Original filename is preserved.
pds_directory  Read an Apache-style PDS directory listing and download the
               files whose names match include_regex (max_files cap).
raster_subset  Read only the AOI pixel window of a remote GeoTIFF through
               GDAL /vsicurl/ (HTTP range requests). Pixel values, data type,
               NoData, CRS and units are copied unchanged; the window offsets
               and source URL are written into the GeoTIFF tags.

Guarantees
----------
* Never overwrites: an existing destination is hashed and recorded as
  SKIPPED_EXISTS.
* Never re-downloads a source URL already recorded as DOWNLOADED in the
  manifest (SKIPPED_DUPLICATE).
* Downloads go to <name>.part and are renamed only after the byte count
  matches Content-Length (when the server sends it).
* SHA-256 and MD5 recorded for every file; archives extracted safely
  (path-traversal guarded) next to the preserved original.
* Every attempt - including failures - is appended to
  metadata/download_manifest.{json,csv}.

Usage
-----
    python 02_download_datasets.py                       # run enabled plan items
    python 02_download_datasets.py --only MOLA_463M_GALE_SUBSET
    python 02_download_datasets.py --url https://.../FILE.TAB --dest raw/rems \
        --dataset-name "REMS MODRDR" --product-id RME_...
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, file_hashes, parse_aoi,  # noqa: E402
                             read_json, setup_logging, snap_window_outward,
                             utc_now_iso, write_csv, write_json)

MANIFEST_FIELDS = [
    "record_id", "item_id", "dataset_name", "product_id", "status",
    "source_url", "url_evidence", "local_path", "original_filename",
    "access_utc", "http_status", "content_length_header", "size_bytes",
    "size_verified", "sha256", "md5", "last_modified", "etag",
    "parent_archive", "documented_units", "file_role", "error", "notes",
]


class Manifest:
    def __init__(self, root: Path):
        self.json_path = root / "metadata/download_manifest.json"
        self.csv_path = root / "metadata/download_manifest.csv"
        existing = read_json(self.json_path, default={}) or {}
        self.records: list[dict] = existing.get("records", [])

    def downloaded_urls(self) -> set:
        return {r["source_url"] for r in self.records
                if r.get("status") in ("DOWNLOADED", "SUBSET_EXTRACTED")}

    def add(self, rec: dict) -> dict:
        rec = {k: rec.get(k) for k in MANIFEST_FIELDS}
        rec["record_id"] = f"DL{len(self.records) + 1:04d}"
        self.records.append(rec)
        return rec

    def save(self):
        write_json(self.json_path, {"generated_utc": utc_now_iso(),
                                    "n_records": len(self.records),
                                    "status_vocabulary": [
                                        "DOWNLOADED", "SUBSET_EXTRACTED", "EXTRACTED",
                                        "USER_SUPPLIED",
                                        "SKIPPED_EXISTS", "SKIPPED_DUPLICATE",
                                        "FAILED", "NOT_ATTEMPTED"],
                                    "records": self.records})
        write_csv(self.csv_path, self.records, fieldnames=MANIFEST_FIELDS)


def _base_rec(item: dict, url: str | None) -> dict:
    return {"item_id": item.get("id"), "dataset_name": item.get("dataset_name"),
            "product_id": item.get("product_id"), "source_url": url,
            "url_evidence": item.get("url_evidence"),
            "documented_units": item.get("documented_units"),
            "access_utc": utc_now_iso(), "notes": item.get("notes")}


# ---------------------------------------------------------------------------
def download_http(url: str, dest_dir: Path, item: dict, manifest: Manifest,
                  log, timeout: float, root: Path) -> dict:
    import requests

    fname = unquote(Path(urlparse(url).path).name) or "download.bin"
    dest = dest_dir / fname
    rec = _base_rec(item, url)
    rec.update({"original_filename": fname,
                "local_path": str(dest.relative_to(root))})
    if url in manifest.downloaded_urls():
        rec.update(status="SKIPPED_DUPLICATE",
                   notes="Source URL already downloaded per manifest")
        log.info("Duplicate source URL, skipped: %s", url)
        return manifest.add(rec)
    if dest.exists():
        rec.update(status="SKIPPED_EXISTS", **file_hashes(dest))
        log.info("Exists, not overwritten: %s", dest)
        return manifest.add(rec)

    dest_dir.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            rec.update(http_status=r.status_code,
                       content_length_header=r.headers.get("Content-Length"),
                       last_modified=r.headers.get("Last-Modified"),
                       etag=r.headers.get("ETag"))
            r.raise_for_status()
            with open(part, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
        h = file_hashes(part)
        expected = rec["content_length_header"]
        if expected is not None and int(expected) != h["size_bytes"]:
            raise IOError(f"Size mismatch: header {expected} vs got {h['size_bytes']}")
        os.replace(part, dest)
        rec.update(status="DOWNLOADED", size_verified=expected is not None, **h)
        log.info("Downloaded %s (%d bytes)", dest, h["size_bytes"])
    except Exception as exc:
        if part.exists():
            part.unlink()
        rec.update(status="FAILED", error=f"{type(exc).__name__}: {exc}"[:500])
        log.error("FAILED %s: %s", url, rec["error"])
        return manifest.add(rec)

    out = manifest.add(rec)
    if item.get("extract") and re.search(r"\.(zip|tar|tar\.gz|tgz)$", fname, re.I):
        extract_archive(dest, item, manifest, log, root)
    return out


def extract_archive(archive: Path, item: dict, manifest: Manifest, log, root: Path):
    out_dir = archive.with_name(re.sub(r"\.(zip|tar\.gz|tgz|tar)$", "", archive.name,
                                       flags=re.I) + "_extracted")
    if out_dir.exists():
        log.info("Extraction dir exists, not re-extracting: %s", out_dir)
        return
    out_dir.mkdir(parents=True)
    base = out_dir.resolve()
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            if bad:
                raise IOError(f"Corrupt member in {archive}: {bad}")
            for m in zf.infolist():
                target = (out_dir / m.filename).resolve()
                if not str(target).startswith(str(base)):
                    raise IOError(f"Unsafe path in archive: {m.filename}")
            zf.extractall(out_dir)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(out_dir, filter="data")  # blocks traversal/devices
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            rec = _base_rec(item, None)
            rec.update(status="EXTRACTED", local_path=str(p.relative_to(root)),
                       original_filename=p.name,
                       parent_archive=str(archive.relative_to(root)),
                       **file_hashes(p))
            manifest.add(rec)
    log.info("Extracted %s -> %s", archive, out_dir)


def download_pds_directory(item: dict, manifest: Manifest, log, timeout: float,
                           root: Path):
    import requests

    url = item.get("index_url")
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
    except Exception as exc:
        rec = _base_rec(item, url)
        rec.update(status="FAILED", error=f"Index fetch failed: {exc}"[:500])
        manifest.add(rec)
        log.error("Index fetch failed for %s: %s", url, exc)
        return
    rx = re.compile(item.get("include_regex", "."))
    links = []
    for href in re.findall(r'href="([^"]+)"', r.text, flags=re.I):
        if href.startswith("?") or href.startswith("../") or href.endswith("/"):
            continue
        full = urljoin(url if url.endswith("/") else url + "/", href)
        if rx.search(href) and full not in links:
            links.append(full)
    links = links[: int(item.get("max_files", 10))]
    log.info("%s: %d matching files listed", url, len(links))
    for link in links:
        download_http(link, root / item["dest_dir"], item, manifest, log, timeout, root)


def raster_subset(item: dict, aoi: dict, manifest: Manifest, log, root: Path):
    rec = _base_rec(item, item["url"])
    dest = root / item["dest_dir"] / item["dest_name"]
    rec.update(local_path=str(dest.relative_to(root)),
               original_filename=Path(urlparse(item["url"]).path).name)
    if dest.exists():
        rec.update(status="SKIPPED_EXISTS", **file_hashes(dest))
        log.info("Exists, not overwritten: %s", dest)
        return manifest.add(rec)
    try:
        import numpy as np
        import rasterio
        from pyproj import CRS
        from rasterio.windows import from_bounds

        env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                   CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
                   GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2")
        with rasterio.Env(**env), rasterio.open("/vsicurl/" + item["url"]) as src:
            crs = CRS.from_wkt(src.crs.to_wkt())
            from dhruvion_common import planetocentric_lonlat
            from_ll = planetocentric_lonlat(crs)[1]
            lons = np.linspace(aoi["min_lon_e"], aoi["max_lon_e"], 21)
            lats = np.linspace(aoi["min_lat"], aoi["max_lat"], 21)
            LON, LAT = np.meshgrid(lons, lats)
            xs, ys = from_ll(LON.ravel(), LAT.ravel())
            win = from_bounds(min(xs), min(ys), max(xs), max(ys), src.transform)
            win = snap_window_outward(win, src.width, src.height)
            data = src.read(window=win)
            profile = src.profile.copy()
            profile.update(driver="GTiff", width=int(win.width),
                           height=int(win.height),
                           transform=src.window_transform(win),
                           compress="deflate", tiled=True, blockxsize=256,
                           blockysize=256)
            tags = src.tags()
            units = src.units
            src_info = (f"source {src.width}x{src.height} px, window col_off="
                        f"{int(win.col_off)} row_off={int(win.row_off)} "
                        f"w={int(win.width)} h={int(win.height)}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        with rasterio.open(part, "w", **profile) as dst:
            dst.write(data)
            dst.update_tags(**tags)
            dst.update_tags(DHRUVION_SOURCE_URL=item["url"],
                            DHRUVION_SUBSET=src_info,
                            DHRUVION_ACCESS_UTC=rec["access_utc"],
                            DHRUVION_NOTE="Pixel values copied unchanged from source window")
            if any(units):
                dst.units = units
        os.replace(part, dest)
        rec.update(status="SUBSET_EXTRACTED", size_verified=True,
                   notes=f"{item.get('notes', '')} [{src_info}]", **file_hashes(dest))
        log.info("Subset written %s (%s)", dest, src_info)
    except Exception as exc:
        rec.update(status="FAILED", error=f"{type(exc).__name__}: {exc}"[:500])
        log.error("FAILED raster subset %s: %s", item["url"], rec["error"])
    return manifest.add(rec)


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--plan", type=Path, default=root / "scripts/config/download_plan.json")
    ap.add_argument("--only", nargs="*", help="item ids to run")
    ap.add_argument("--aoi", default=None)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--record-disabled", action="store_true",
                    help="record disabled / URL-less items as NOT_ATTEMPTED")
    ap.add_argument("--url", help="ad-hoc single-file download")
    ap.add_argument("--dest", default="raw/misc")
    ap.add_argument("--dataset-name", default=None)
    ap.add_argument("--product-id", default=None)
    args = ap.parse_args(argv)

    root = args.data_root.resolve()
    log = setup_logging("download", root / "metadata/logs/02_download_datasets.log")
    manifest = Manifest(root)
    aoi = parse_aoi(args.aoi)

    if args.url:
        item = {"id": "ADHOC", "dataset_name": args.dataset_name,
                "product_id": args.product_id, "url_evidence": "user_supplied"}
        download_http(args.url, root / args.dest, item, manifest, log, args.timeout, root)
        manifest.save()
        return 0

    plan = read_json(args.plan) or {}
    for item in plan.get("items", []):
        if args.only and item["id"] not in args.only:
            continue
        url = item.get("url") or item.get("index_url") or (item.get("urls") or [None])[0]
        if not item.get("enabled") or not url:
            log.info("Not attempted (disabled or URL unconfirmed): %s", item["id"])
            if args.record_disabled:
                rec = _base_rec(item, url)
                rec.update(status="NOT_ATTEMPTED",
                           error="Entry disabled: exact product URL not confirmed "
                                 "against the authoritative archive")
                manifest.add(rec)
            continue
        if item["type"] == "http_file":
            for u in (item.get("urls") or [item["url"]]):
                dest = root / item.get("dest_dirs", {}).get(u, item["dest_dir"])
                download_http(u, dest, item, manifest, log, args.timeout, root)
        elif item["type"] == "pds_directory":
            download_pds_directory(item, manifest, log, args.timeout, root)
        elif item["type"] == "raster_subset":
            raster_subset(item, aoi, manifest, log, root)
        else:
            log.error("Unknown item type %s", item["type"])
    manifest.save()
    n_fail = sum(r["status"] == "FAILED" for r in manifest.records)
    log.info("Manifest: %d records (%d FAILED)", len(manifest.records), n_fail)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
