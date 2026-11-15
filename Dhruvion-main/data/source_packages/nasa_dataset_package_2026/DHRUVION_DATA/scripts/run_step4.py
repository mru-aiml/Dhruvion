#!/usr/bin/env python3
"""
run_step4.py - run every Step 4 processor on Step-3-APPROVED inputs only.

* Elevation rasters  -> 05_process_terrain.py (units taken from Step 3 record)
* Imagery rasters    -> 06_process_ctx.py (alignment reported vs first approved DEM)
* Existing slope / roughness rasters that passed Step 3 -> REUSED, not recomputed
* REMS / RAD labels  -> 07 / 08 (only if their column map is CONFIRMED)
Every dataset that is not approved is logged as SKIPPED with its reason.
Log: metadata/step4_run_log.json

Usage:  python run_step4.py
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, read_json, setup_logging,  # noqa: E402
                             utc_now_iso, write_json)

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    log = setup_logging("step4", root / "metadata/logs/run_step4.log")
    cat = read_json(root / "metadata/validated_dataset_catalog.json")
    if not cat:
        log.error("validated_dataset_catalog.json missing - run Step 3 (09_build_catalogs.py)")
        return 2
    rasters = {Path(r["file"]).resolve(): r for r in
               (read_json(root / "metadata/validation_rasters.json", {}) or {}).get("rasters", [])}
    labels = {Path(p["label"]).resolve(): p for p in
              (read_json(root / "metadata/validation_pds_tables.json", {}) or {}).get("products", [])}
    entries, dems, images, insts = [], [], [], set()
    for d in cat.get("datasets", []):
        approved = [f for f in d.get("files", []) if f.get("approved_for_processing")]
        if not approved:
            entries.append({"dataset": d["candidate_id"], "name": d["dataset_name"],
                            "action": "SKIPPED",
                            "reason": f"Step 3 status {d['validation_status']}: "
                                      f"{d.get('not_available_reason') or 'no approved file'}"})
            continue
        for f in approved:
            p = (root / f["file"]).resolve()
            if p in rasters:
                role = rasters[p]["role"]
                if role == "elevation":
                    dems.append((d["candidate_id"], p, rasters[p]["units"]))
                elif role == "imagery":
                    images.append((d["candidate_id"], p))
                else:
                    entries.append({"dataset": d["candidate_id"], "file": f["file"],
                                    "action": "REUSED",
                                    "reason": f"Existing validated {role} raster - not recomputed"})
            elif p in labels:
                insts.add(labels[p]["instrument"])
    for cid, p, units in dems:
        rc = load("05_process_terrain.py").main(["--data-root", str(root), "--dem", str(p),
                                                 "--elevation-units", str(units)])
        entries.append({"dataset": cid, "file": str(p), "script": "05_process_terrain.py",
                        "action": "PROCESSED" if rc == 0 else "FAILED", "exit_code": rc})
    for cid, p in images:
        a = ["--data-root", str(root), "--image", str(p)]
        if dems:
            a += ["--reference-dem", str(dems[0][1])]
        rc = load("06_process_ctx.py").main(a)
        entries.append({"dataset": cid, "file": str(p), "script": "06_process_ctx.py",
                        "action": "PROCESSED" if rc == 0 else "FAILED", "exit_code": rc})
    for inst, script in (("rems", "07_process_rems.py"), ("rad", "08_process_rad.py")):
        if inst not in insts:
            continue
        rc = load(script).main(["--data-root", str(root)])
        entries.append({"instrument": inst, "script": script, "exit_code": rc,
                        "action": "PROCESSED" if rc == 0 else "SKIPPED",
                        "reason": None if rc == 0 else
                        "Column map not CONFIRMED or no usable columns - see script log"})
    n_proc = sum(e["action"] == "PROCESSED" for e in entries)
    write_json(root / "metadata/step4_run_log.json",
               {"generated_utc": utc_now_iso(), "n_processed": n_proc,
                "n_skipped": sum(e["action"] == "SKIPPED" for e in entries),
                "n_failed": sum(e["action"] == "FAILED" for e in entries),
                "entries": entries})
    log.info("Step 4: %d processed, %d entries total", n_proc, len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
