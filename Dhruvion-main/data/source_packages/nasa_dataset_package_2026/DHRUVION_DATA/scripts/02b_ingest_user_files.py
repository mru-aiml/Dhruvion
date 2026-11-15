#!/usr/bin/env python3
"""
02b_ingest_user_files.py - ingest files that a person downloaded manually
(e.g. when the build environment cannot reach the archives).

An explicit, auditable spec (JSON) lists every received file:
  {"files": [{"src": "rems/X.TAB.txt", "dest": "raw/rems/SOL00009/X.TAB",
              "item_id": "REMS_RDR_SAMPLE", "file_role": "data|label|support",
              "source_url": "...", "url_evidence": "...", "notes": "..."}],
   "skip":  [{"src": "...", "reason": "..."}]}
Each file is copied (never moved, never overwritten) into raw/, hashed, and
appended to metadata/download_manifest.{json,csv} with status USER_SUPPLIED.
Renames (e.g. browser-added '.txt') are recorded in the notes. Skipped files
are recorded with their reason and hash.

Usage:  python 02b_ingest_user_files.py --source-dir <unzipped upload> --spec <spec.json>
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, file_hashes, read_json,  # noqa: E402
                             setup_logging, utc_now_iso)


def _manifest_cls():
    spec = importlib.util.spec_from_file_location(
        "dl", Path(__file__).resolve().parent / "02_download_datasets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Manifest


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    log = setup_logging("ingest", root / "metadata/logs/02b_ingest_user_files.log")
    spec = read_json(args.spec)
    man = _manifest_cls()(root)
    n_ok = n_fail = 0
    for f in spec.get("files", []):
        src = args.source_dir / f["src"]
        dest = root / f["dest"]
        rec = {k: f.get(k) for k in ("item_id", "dataset_name", "product_id", "source_url",
                                     "url_evidence", "documented_units", "file_role", "notes")}
        rec.update(access_utc=utc_now_iso(), original_filename=Path(f["src"]).name,
                   local_path=str(dest.relative_to(root)))
        if not src.is_file():
            rec.update(status="FAILED", error=f"source file missing: {f['src']}")
            n_fail += 1
        elif dest.exists():
            rec.update(status="SKIPPED_EXISTS", **file_hashes(dest))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            h_src, h_dst = file_hashes(src), file_hashes(dest)
            if h_src["sha256"] != h_dst["sha256"]:
                dest.unlink()
                rec.update(status="FAILED", error="copy verification failed")
                n_fail += 1
            else:
                rec.update(status="USER_SUPPLIED", size_verified=True, **h_dst)
                n_ok += 1
        man.add(rec)
        log.info("%-16s %s -> %s", rec["status"], f["src"], f["dest"])
    for s in spec.get("skip", []):
        src = args.source_dir / s["src"]
        rec = {"item_id": s.get("item_id"), "status": "SKIPPED_DUPLICATE",
               "original_filename": Path(s["src"]).name, "access_utc": utc_now_iso(),
               "notes": s["reason"], **(file_hashes(src) if src.is_file() else {})}
        man.add(rec)
        log.info("SKIPPED          %s (%s)", s["src"], s["reason"])
    man.save()
    log.info("Ingested %d file(s), %d failure(s)", n_ok, n_fail)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
