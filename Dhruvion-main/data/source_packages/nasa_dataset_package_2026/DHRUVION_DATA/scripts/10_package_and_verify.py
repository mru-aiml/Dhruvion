#!/usr/bin/env python3
"""
10_package_and_verify.py - build and verify DHRUVION_NASA_DATASET_PACKAGE.zip.

1. Collect every file under DHRUVION_DATA/ except caches/temporaries
   (__pycache__, *.pyc, .pytest_cache, *.part, *.tmp, virtualenvs,
   node_modules). Files above --max-file-mb (if given) and any file that looks
   like a credential are EXCLUDED AND LISTED in metadata/EXCLUDED_FROM_PACKAGE.json
   - never silently dropped.
2. Scan text files for credential patterns; abort if any are found.
3. Check required deliverables exist.
4. Write metadata/PACKAGE_MANIFEST.json (path, size, SHA-256 of every file).
5. Write the ZIP (deflate, ZIP64-capable) with top-level folder DHRUVION_DATA/.
6. Verify: archive opens, CRC test passes, member list == intended list,
   SHA-256 of every member read back from the ZIP == manifest.
7. Copy the ZIP to each --copy-to directory and verify the copy's SHA-256.
Writes <zip>.sha256 and <zip>.verification.json next to the ZIP.

Usage
-----
    python 10_package_and_verify.py --zip-path ./DHRUVION_NASA_DATASET_PACKAGE.zip \
        --copy-to .. --copy-to /some/share
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, file_hashes, setup_logging,  # noqa: E402
                             utc_now_iso, write_json)

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".venv", "venv", "env",
                "node_modules", ".git", ".ipynb_checkpoints"}
EXCLUDE_GLOBS = ["*.pyc", "*.pyo", "*.part", "*.tmp", ".DS_Store", "Thumbs.db"]
CREDENTIAL_GLOBS = [".env", "*.pem", "*.key", "*.p12", "id_rsa*", "*credentials*",
                    "*secret*", ".netrc", "*.kdbx"]
CREDENTIAL_RX = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]{10,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|"
    r"-----BEGIN (RSA |EC )?PRIVATE KEY-----|"
    r"(api[_-]?key|password|secret[_-]?key)\s*[:=]\s*['\"][^'\"\s]{8,})", re.I)
TEXT_EXT = {".py", ".md", ".json", ".csv", ".txt", ".sh", ".log", ".cfg", ".ini",
            ".yaml", ".yml", ".lbl", ".fmt", ".tab"}
REQUIRED = [
    "documentation/README.md", "documentation/TEAM_HANDOVER.md",
    "documentation/FINAL_REPORT.md", "metadata/FINAL_DATASET_CATALOG.json",
    "metadata/dataset_discovery_catalog.csv", "metadata/dataset_discovery_catalog.json",
    "metadata/download_manifest.csv", "metadata/download_manifest.json",
    "metadata/validated_dataset_catalog.json", "metadata/validation_summary.csv",
    "reports/phase1_inspection_report.md", "reports/phase2_download_report.md",
    "reports/phase3_validation_report.md", "reports/phase4_processing_report.md",
    "requirements.txt", "scripts/run_pipeline.sh", "scripts/tests/test_pipeline.py",
]
REQUIRED_DIRS = ["raw/terrain", "raw/ctx", "raw/rems", "raw/rad", "processed/terrain",
                 "processed/ctx", "processed/rems", "processed/rad", "scripts",
                 "metadata", "reports", "documentation"]


def sha256_bytes_stream(fh) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: fh.read(1 << 20), b""):
        h.update(block)
    return h.hexdigest()


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--zip-path", type=Path,
                    default=Path.cwd() / "DHRUVION_NASA_DATASET_PACKAGE.zip")
    ap.add_argument("--copy-to", type=Path, action="append", default=[])
    ap.add_argument("--max-file-mb", type=float, default=None)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    zpath = args.zip_path.resolve()
    log = setup_logging("package", root / "metadata/logs/10_package_and_verify.log")
    if zpath.exists() and not args.overwrite:
        log.error("ZIP exists (use --overwrite): %s", zpath)
        return 2

    include, excluded = [], []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue  # caches / virtualenvs: never deliverables
        if any(fnmatch.fnmatch(p.name, g) for g in EXCLUDE_GLOBS):
            excluded.append({"path": str(rel), "reason": "temporary/cache file"})
            continue
        if any(fnmatch.fnmatch(p.name.lower(), g) for g in CREDENTIAL_GLOBS):
            excluded.append({"path": str(rel), "reason": "possible credential file"})
            continue
        if args.max_file_mb and p.stat().st_size > args.max_file_mb * 1e6:
            excluded.append({"path": str(rel), "location": str(p),
                             "size_bytes": p.stat().st_size,
                             "reason": f"larger than --max-file-mb {args.max_file_mb}"})
            continue
        include.append(p)

    hits = []
    for p in include:
        if p.suffix.lower() in TEXT_EXT and p.stat().st_size < 50e6:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for m in CREDENTIAL_RX.finditer(txt):
                if "CREDENTIAL_RX" in txt[max(0, m.start() - 400):m.start()]:
                    continue  # the pattern definition in this script
                hits.append({"file": str(p.relative_to(root)), "match": m.group(0)[:12] + "..."})
    if hits:
        log.error("Possible credentials found - aborting: %s", hits)
        return 3

    missing = [r for r in REQUIRED if not (root / r).is_file()]
    missing += [d + "/" for d in REQUIRED_DIRS if not (root / d).is_dir()]
    if missing:
        log.error("Missing required deliverables: %s", missing)
        return 4

    write_json(root / "metadata/EXCLUDED_FROM_PACKAGE.json",
               {"generated_utc": utc_now_iso(), "excluded": excluded,
                "not_in_data_root_by_design": [
                    "Application frontend/backend code (not part of the dataset package)",
                    "Uploaded planning documents (.docx) - project notes, not datasets"]})
    manifest_path = root / "metadata/PACKAGE_MANIFEST.json"
    entries = []
    for p in include:
        if p == manifest_path:
            continue
        h = file_hashes(p)
        entries.append({"path": "DHRUVION_DATA/" + str(p.relative_to(root)),
                        "size_bytes": h["size_bytes"], "sha256": h["sha256"]})
    write_json(manifest_path, {"generated_utc": utc_now_iso(),
                               "note": "SHA-256 of every packaged file except this manifest",
                               "n_files": len(entries), "files": entries})
    if manifest_path not in include:
        include.append(manifest_path)
    for extra in ("metadata/EXCLUDED_FROM_PACKAGE.json",):
        ep = root / extra
        if ep not in include:
            include.append(ep)

    tmp = zpath.with_name(zpath.name + ".part")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9,
                         allowZip64=True) as zf:
        zf.writestr(zipfile.ZipInfo("DHRUVION_DATA/"), b"")
        for d in sorted({p.parent for p in include} | {root / x for x in REQUIRED_DIRS}):
            if d != root:
                zf.writestr(zipfile.ZipInfo("DHRUVION_DATA/" + str(d.relative_to(root)) + "/"), b"")
        for p in sorted(include):
            zf.write(p, "DHRUVION_DATA/" + str(p.relative_to(root)))
    tmp.replace(zpath)

    # ------------------------------ verification
    expected = {e["path"]: e["sha256"] for e in entries}
    with zipfile.ZipFile(zpath) as zf:
        bad = zf.testzip()
        names = [n for n in zf.namelist() if not n.endswith("/")]
        dirs = [n for n in zf.namelist() if n.endswith("/")]
        mism = []
        for n, sha in expected.items():
            with zf.open(n) as fh:
                if sha256_bytes_stream(fh) != sha:
                    mism.append(n)
        intended = {"DHRUVION_DATA/" + str(p.relative_to(root)) for p in include}
        uncompressed = sum(i.file_size for i in zf.infolist())
    req_ok = all("DHRUVION_DATA/" + r in names for r in REQUIRED) and all(
        "DHRUVION_DATA/" + d + "/" in dirs for d in REQUIRED_DIRS)
    zh = file_hashes(zpath)
    ver = {"zip_path": str(zpath), "zip_size_bytes": zh["size_bytes"], "zip_sha256": zh["sha256"],
           "verified_utc": utc_now_iso(), "opens": True, "crc_test_first_bad_member": bad,
           "n_files": len(names), "n_directories": len(dirs),
           "uncompressed_bytes": uncompressed,
           "member_list_equals_intended": set(names) == intended,
           "missing_from_zip": sorted(intended - set(names)),
           "unexpected_in_zip": sorted(set(names) - intended),
           "sha256_mismatches": mism, "required_deliverables_present": req_ok,
           "excluded_files": excluded, "copies": []}
    ok = bad is None and not mism and ver["member_list_equals_intended"] and req_ok
    for dest in args.copy_to:
        dest = dest.resolve()
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / zpath.name
        shutil.copy2(zpath, target)
        same = file_hashes(target)["sha256"] == zh["sha256"]
        ver["copies"].append({"path": str(target), "sha256_matches": same})
        ok &= same
    ver["overall_ok"] = ok
    zpath.with_name(zpath.name + ".sha256").write_text(f"{zh['sha256']}  {zpath.name}\n")
    write_json(zpath.with_name(zpath.stem + ".verification.json"), ver, overwrite=True)
    log.info("ZIP %s: %d files, %d bytes, verification %s", zpath, len(names),
             zh["size_bytes"], "PASSED" if ok else "FAILED")
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())
