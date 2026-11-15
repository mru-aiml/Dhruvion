#!/usr/bin/env python3
"""
09_build_catalogs.py - assemble the Step 3 and Step 5 catalogs.

Inputs (all under metadata/ unless noted)
-----------------------------------------
dataset_discovery_catalog.json   Step 1 candidates
download_manifest.json           Step 2 attempts and files
validation_rasters.json          Step 3 raster results      (optional)
validation_pds_tables.json       Step 3 REMS/RAD results    (optional)
processed/**/_provenance.json    Step 4 outputs              (optional)

Outputs
-------
validated_dataset_catalog.json   one entry per candidate with per-file status
validation_summary.csv           one row per candidate and per validated file
FINAL_DATASET_CATALOG.json       every dataset (raw + derived) with provenance

A candidate with no local file is NOT AVAILABLE, with the reason taken from
the download manifest. Local raster/table files that are not linked to any
candidate are listed as UNCATALOGUED so nothing is silently dropped.

Usage
-----
    python 09_build_catalogs.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, read_json, setup_logging,  # noqa: E402
                             utc_now_iso, write_csv, write_json)

LOCAL_STATES = {"DOWNLOADED", "SUBSET_EXTRACTED", "EXTRACTED", "SKIPPED_EXISTS",
                "USER_SUPPLIED"}


def rel(p: str | None, root: Path) -> str | None:
    if not p:
        return None
    pp = Path(p)
    try:
        return str((pp if pp.is_absolute() else root / pp).resolve().relative_to(root))
    except ValueError:
        return str(pp)


def dataset_status(files: list[dict]) -> str:
    st = [f["validation_status"] for f in files]
    if st and all(s == "VALIDATED" for s in st):
        return "VALIDATED"
    if any(f.get("approved_for_processing") for f in files):
        return "VALIDATED WITH LIMITATIONS"
    if "INCOMPLETE" in st:
        return "INCOMPLETE"
    if "INVALID" in st:
        return "INVALID"
    return "INCOMPLETE"  # local files present but never validated


def _classify(prov: str | None) -> str:
    """Nominal OBSERVED/DERIVED class of a dataset (independent of availability)."""
    p = str(prov or "").upper()
    if "OBSERVED" in p and "DERIVED" in p:
        return "OBSERVED + DERIVED"
    return "DERIVED" if p.startswith("DERIVED") else "OBSERVED"


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    md = root / "metadata"
    log = setup_logging("catalogs", md / "logs/09_build_catalogs.log")

    disc = read_json(md / "dataset_discovery_catalog.json", default={}) or {}
    man = read_json(md / "download_manifest.json", default={}) or {}
    vr = read_json(md / "validation_rasters.json", default={}) or {}
    vt = read_json(md / "validation_pds_tables.json", default={}) or {}

    vfiles: dict[str, dict] = {}
    for r in vr.get("rasters", []):
        vfiles[rel(r["file"], root)] = {"kind": "raster", **r}
    for p in vt.get("products", []):
        vfiles[rel(p["label"], root)] = {"kind": "pds_table", "file": p["label"], **p}

    linked: set[str] = set()
    datasets, summary = [], []
    for c in disc.get("candidates", []):
        recs = [r for r in man.get("records", []) if c.get("plan_item_id")
                and r.get("item_id") == c["plan_item_id"]]
        doc_item = str(c.get("plan_item_id") or "").replace("_SAMPLE", "_DOCUMENTATION")
        recs_all = recs + [r for r in man.get("records", []) if doc_item
                           and doc_item != c.get("plan_item_id") and r.get("item_id") == doc_item]
        local_all = [r for r in recs_all if r.get("status") in LOCAL_STATES
                     and r.get("local_path") and (root / r["local_path"]).exists()]
        local = [r for r in local_all if (r.get("file_role") or "data") != "support"]
        support = sorted({r["local_path"] for r in local_all
                          if (r.get("file_role") or "data") == "support"})
        files = []
        for r in local:
            lp = r["local_path"]
            v = vfiles.get(lp)
            if v is None and lp.lower().endswith((".tab", ".txt")):
                v = vfiles.get(str(Path(lp).with_suffix(".LBL"))) or \
                    vfiles.get(str(Path(lp).with_suffix(".lbl")))
            linked.add(lp)
            if v:
                linked.add(rel(v["file"], root))
            files.append({"file": lp, "sha256": r.get("sha256"), "size_bytes": r.get("size_bytes"),
                          "validation_status": v["validation_status"] if v else "INCOMPLETE",
                          "approved_for_processing": bool(v and v.get("approved_for_processing")),
                          "limitations": (v or {}).get("limitations",
                                                       ["Not yet validated (run Step 3)"]),
                          "reasons": (v or {}).get("reasons_invalid", []) +
                                     (v or {}).get("reasons_incomplete", [])})
        if files:
            status, reason = dataset_status(files), None
        else:
            status = "NOT AVAILABLE"
            if not recs:
                reason = ("Not selected for download in this run (duplicate, deferred or no "
                          "plan entry): " + str(c.get("recommendation")))
                if c["candidate_id"] == "C01":
                    reason = "Files not supplied to this environment; nothing to validate"
            else:
                last = recs[-1]
                reason = f"Download {last['status']}: {last.get('error') or ''}".strip()
        entry = {"candidate_id": c["candidate_id"], "dataset_name": c["dataset_name"],
                 "category": c["category"], "validation_status": status,
                 "not_available_reason": reason, "files": files,
                 "support_files": support,
                 "approved_files": [f["file"] for f in files if f["approved_for_processing"]]}
        datasets.append(entry)
        summary.append({"level": "dataset", "candidate_id": c["candidate_id"],
                        "name_or_file": c["dataset_name"], "validation_status": status,
                        "approved_for_processing": bool(entry["approved_files"]),
                        "reason_or_limitations": reason or "; ".join(
                            sorted({l for f in files for l in f["limitations"]}))})
        for f in files:
            summary.append({"level": "file", "candidate_id": c["candidate_id"],
                            "name_or_file": f["file"], "validation_status": f["validation_status"],
                            "approved_for_processing": f["approved_for_processing"],
                            "reason_or_limitations": "; ".join(f["reasons"] + f["limitations"])})

    unc = [v for k, v in vfiles.items() if k not in linked]
    if unc:
        files = [{"file": rel(v["file"], root), "validation_status": v["validation_status"],
                  "approved_for_processing": v.get("approved_for_processing", False),
                  "limitations": v.get("limitations", []),
                  "reasons": v.get("reasons_invalid", []) + v.get("reasons_incomplete", [])}
                 for v in unc]
        datasets.append({"candidate_id": "UNCATALOGUED", "dataset_name":
                         "Local files not linked to a discovery candidate",
                         "category": "mixed", "validation_status": dataset_status(files),
                         "files": files,
                         "approved_files": [f["file"] for f in files if f["approved_for_processing"]]})
        for f in files:
            summary.append({"level": "file", "candidate_id": "UNCATALOGUED",
                            "name_or_file": f["file"], "validation_status": f["validation_status"],
                            "approved_for_processing": f["approved_for_processing"],
                            "reason_or_limitations": "; ".join(f["reasons"] + f["limitations"])})

    counts = {}
    for d in datasets:
        counts[d["validation_status"]] = counts.get(d["validation_status"], 0) + 1
    write_json(md / "validated_dataset_catalog.json",
               {"generated_utc": utc_now_iso(), "status_counts": counts,
                "status_vocabulary": ["VALIDATED", "VALIDATED WITH LIMITATIONS", "INVALID",
                                      "INCOMPLETE", "NOT AVAILABLE"], "datasets": datasets})
    write_csv(md / "validation_summary.csv", summary,
              fieldnames=["level", "candidate_id", "name_or_file", "validation_status",
                          "approved_for_processing", "reason_or_limitations"])

    # ---------------- FINAL catalog -------------------------------------
    final = []
    cand = {c["candidate_id"]: c for c in disc.get("candidates", [])}
    for d in datasets:
        c = cand.get(d["candidate_id"], {})
        final.append({
            "dataset_name": d["dataset_name"], "candidate_id": d["candidate_id"],
            "product_id": c.get("product_id"), "data_set_id": c.get("data_set_id"),
            "source_url": c.get("source_url"), "file_paths": [f["file"] for f in d["files"]],
            "support_files": d.get("support_files", []),
            "file_format": c.get("format"), "coverage": c.get("spatial_coverage"),
            "temporal_coverage": c.get("temporal_coverage"), "resolution": c.get("resolution"),
            "units": c.get("units"), "processing_level": c.get("processing_level"),
            "classification": _classify(c.get("provenance_class")),
            "availability": ("NOT AVAILABLE - no file in this package"
                             if d["validation_status"] == "NOT AVAILABLE" else "PRESENT"),
            "validation_status": d["validation_status"],
            "not_available_reason": d.get("not_available_reason"),
            "evidence_level": c.get("evidence_level"),
            "limitations": c.get("limitations")})
    for prov_path in sorted((root / "processed").rglob("*provenance.json")):
        p = read_json(prov_path) or {}
        outs = p.get("outputs") or {}
        outs = list(outs.values()) if isinstance(outs, dict) else outs
        final.append({
            "dataset_name": f"Derived products: {prov_path.stem}",
            "product_id": None, "source_url": None,
            "derived_from": (p.get("input") or {}).get("path") or p.get("column_map"),
            "file_paths": [rel(str(prov_path.parent / o), root) for o in outs] + [rel(str(prov_path), root)],
            "file_format": "GeoTIFF/PNG/JSON/CSV", "classification": "DERIVED",
            "methods": p.get("methods"), "validation_status": "DERIVED FROM APPROVED INPUT",
            "limitations": p.get("scale_note") or p.get("spatial_coverage")})
    write_json(md / "FINAL_DATASET_CATALOG.json",
               {"generated_utc": utc_now_iso(),
                "classification_vocabulary": ["OBSERVED", "DERIVED", "SIMULATED", "UNAVAILABLE"],
                "n_datasets": len(final), "datasets": final})
    log.info("Catalogs written: %d candidates, status counts %s", len(datasets), counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
