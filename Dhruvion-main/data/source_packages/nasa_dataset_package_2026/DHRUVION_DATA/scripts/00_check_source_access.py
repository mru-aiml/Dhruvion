#!/usr/bin/env python3
"""
00_check_source_access.py - probe every authoritative data endpoint and log
DNS resolution and HTTP status as evidence.

Run this FIRST on any machine. If an endpoint is unreachable, the downloader
(02_download_datasets.py) will fail for that source and the reason is
recorded here.

Usage
-----
    python 00_check_source_access.py \
        --endpoints config/source_endpoints.json \
        --out-json ../metadata/network_access_log.json \
        --out-csv  ../metadata/network_access_log.csv

Nothing is downloaded beyond HTTP response headers (HEAD, or a GET that is
closed immediately after the headers arrive).
"""
from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, read_json, setup_logging,  # noqa: E402
                             utc_now_iso, write_csv, write_json)


def probe(url: str, timeout: float) -> dict:
    import requests

    host = urlparse(url).hostname or ""
    rec = {"url": url, "host": host, "checked_utc": utc_now_iso(),
           "dns_resolved": False, "resolved_ips": "", "http_status": None,
           "x_deny_reason": None, "content_type": None,
           "content_length": None, "error": None, "reachable": False}
    try:
        infos = socket.getaddrinfo(host, 443)
        rec["dns_resolved"] = True
        rec["resolved_ips"] = ";".join(sorted({i[4][0] for i in infos}))
    except socket.gaierror as exc:
        rec["error"] = f"DNS resolution failed: {exc}"
        return rec
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code in (403, 405, 501):  # some servers reject HEAD
            resp = requests.get(url, timeout=timeout, stream=True,
                                allow_redirects=True)
            resp.close()
        rec["http_status"] = resp.status_code
        rec["x_deny_reason"] = resp.headers.get("x-deny-reason")
        rec["content_type"] = resp.headers.get("Content-Type")
        rec["content_length"] = resp.headers.get("Content-Length")
        rec["reachable"] = 200 <= resp.status_code < 400
    except Exception as exc:  # network errors are evidence, not crashes
        rec["error"] = f"{type(exc).__name__}: {exc}"[:500]
    return rec


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoints", type=Path,
                    default=root / "scripts/config/source_endpoints.json")
    ap.add_argument("--out-json", type=Path,
                    default=root / "metadata/network_access_log.json")
    ap.add_argument("--out-csv", type=Path,
                    default=root / "metadata/network_access_log.csv")
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args(argv)

    log = setup_logging("access_check", root / "metadata/logs/00_check_source_access.log")
    cfg = read_json(args.endpoints)
    if not cfg or "endpoints" not in cfg:
        log.error("No endpoints found in %s", args.endpoints)
        return 2

    results = []
    for ep in cfg["endpoints"]:
        rec = probe(ep["url"], args.timeout)
        rec.update({"id": ep["id"], "role": ep.get("role"),
                    "url_evidence": ep.get("evidence")})
        status = "REACHABLE" if rec["reachable"] else "UNREACHABLE"
        log.info("%-20s %-11s http=%s %s", ep["id"], status,
                 rec["http_status"], rec["error"] or "")
        results.append(rec)

    summary = {"generated_utc": utc_now_iso(),
               "hostname": socket.gethostname(),
               "n_endpoints": len(results),
               "n_reachable": sum(r["reachable"] for r in results),
               "results": results}
    write_json(args.out_json, summary)
    order = ["id", "host", "url", "dns_resolved", "http_status", "reachable",
             "x_deny_reason", "error", "checked_utc", "role", "url_evidence"]
    write_csv(args.out_csv, results, fieldnames=order)
    log.info("Reachable: %d / %d", summary["n_reachable"], summary["n_endpoints"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
