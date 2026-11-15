#!/usr/bin/env python3
"""
08_process_rad.py - Step 4C processing of MSL RAD calibrated RDR dose rates.

Uses rad_rdr.py to read, for every Step-3-approved RAD label, the per-observation
dose-rate elements named in the CONFIRMED map config/rad_column_map.json
(TOT_DOSE_B_ELEMENT -> detector B, TOT_DOSE_E_ELEMENT -> detector E).

Rules: units come from the label and must equal expected_unit; detectors are
never combined (long-format output, one row per observation per detector);
missing values stay null; QC/rover position are placeholders (SIS v3.2) and
are carried but never used to filter. Per-sol statistics are the UNWEIGHTED
mean/min/max/median/std of observation dose rates (observation durations are
not used). Trends are computed only with >= 5 sols.

Outputs (processed/rad/): rad_observations_clean.csv/.json,
rad_sol_summary.csv/.json, rad_trends.json, rad_processing_provenance.json

Usage:  python 08_process_rad.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, read_json, setup_logging,  # noqa: E402
                             utc_now_iso, write_csv, write_json)
from rad_rdr import obs_sol_lmst, read_rad_rdr  # noqa: E402
from rover_tables import MappingError, approved_labels  # noqa: E402


def load_map(path: Path) -> dict:
    m = read_json(path)
    if not m or str(m.get("status", "")).upper() != "CONFIRMED":
        raise MappingError(f"RAD map {path} missing or not CONFIRMED")
    meas = m.get("measurements") or {}
    for k, v in meas.items():
        if not v.get("label_object_suffix") or not v.get("detector"):
            raise MappingError(f"{k}: label_object_suffix and detector are required")
    return m


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--column-map", type=Path, default=None)
    ap.add_argument("--labels", type=Path, nargs="*", default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--skip-validation-gate", action="store_true",
                    help="ONLY for tests: process labels not approved in Step 3")
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    log = setup_logging("rad", root / "metadata/logs/08_process_rad.log")
    out_dir = args.out_dir or root / "processed/rad"
    try:
        cmap = load_map(args.column_map or root / "scripts/config/rad_column_map.json")
    except MappingError as exc:
        log.error("%s", exc)
        return 4
    approved = approved_labels(read_json(root / "metadata/validation_pds_tables.json"), "rad")
    labels = args.labels if args.labels is not None else approved
    if args.labels is not None and not args.skip_validation_gate:
        ok = {str(Path(p).resolve()) for p in approved}
        labels = [l for l in labels if str(Path(l).resolve()) in ok]
    if not labels:
        log.error("No Step-3-approved RAD labels to process")
        return 3

    rows, processed, skipped = [], [], []
    for lbl in labels:
        try:
            r = read_rad_rdr(Path(lbl))
        except Exception as exc:
            skipped.append({"label": str(lbl), "reason": f"{type(exc).__name__}: {exc}"})
            continue
        by = {(e["obs"], e["suffix"]): e for e in r["elements"]}
        for obs, h in sorted(r["headers"].items()):
            sol, lmst = obs_sol_lmst(h)
            for key, spec in cmap["measurements"].items():
                e = by.get((obs, spec["label_object_suffix"]))
                if e is None:
                    continue
                if spec.get("expected_unit") and e["unit"] != spec["expected_unit"]:
                    skipped.append({"label": str(lbl), "obs": obs, "measurement": key,
                                    "reason": f"unit '{e['unit']}' != expected '{spec['expected_unit']}'"})
                    continue
                rows.append({"source_product": Path(r["data_files"][0]).name, "obs_index": obs,
                             "sol": sol, "lmst_start": lmst,
                             "utc_start": h.get("START_OBS_UTC"),
                             "measurement": key, "detector": spec["detector"],
                             "quantity": spec.get("quantity"),
                             "value": None if math.isnan(e["value"]) else e["value"],
                             "unit": e["unit"], "label_object": e["object"],
                             "label_vs_text_crosscheck": e["crosscheck_ok"],
                             "qc_placeholder": h.get("QC"),
                             "edr_filename": h.get("EDR_FILENAME")})
        processed.append({"label": str(lbl), "n_observations": len(r["headers"]),
                          "n_dose_elements": len(r["elements"])})
        log.info("Processed %s: %d observations", Path(lbl).name, len(r["headers"]))
    if not rows:
        log.error("No dose rows extracted")
        return 5
    df = pd.DataFrame(rows)
    summ = []
    for (sol, key), g in df.groupby(["sol", "measurement"], dropna=False):
        v = pd.to_numeric(g["value"], errors="coerce").dropna()
        summ.append({"sol": sol, "measurement": key, "detector": g["detector"].iloc[0],
                     "unit": g["unit"].iloc[0],
                     "filter": "all_observations (unweighted mean of observation dose rates)",
                     "n_observations": int(len(g)), "n_valid": int(len(v)),
                     "n_missing": int(len(g) - len(v)),
                     "mean": float(v.mean()) if len(v) else None,
                     "min": float(v.min()) if len(v) else None,
                     "max": float(v.max()) if len(v) else None,
                     "median": float(v.median()) if len(v) else None,
                     "std": float(v.std(ddof=1)) if len(v) > 1 else None,
                     "utc_first": g["utc_start"].min(), "utc_last": g["utc_start"].max()})
    trends = []
    sdf = pd.DataFrame(summ)
    for key, g in sdf.groupby("measurement"):
        g = g.dropna(subset=["sol", "mean"]).sort_values("sol")
        t = {"measurement": key, "detector": g["detector"].iloc[0], "unit": g["unit"].iloc[0],
             "n_sols": int(len(g)), "sols": [int(s) for s in g["sol"]]}
        if len(g) >= 5:
            sl, ic = np.polyfit(g["sol"].astype(float), g["mean"].astype(float), 1)
            t.update(ols_slope_per_sol=float(sl), ols_intercept=float(ic),
                     note="Descriptive trend of per-sol means; not a forecast")
        else:
            t["note"] = "Fewer than 5 sols - trend not computed"
        trends.append(t)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "rad_observations_clean.csv", index=False, na_rep="")
    write_json(out_dir / "rad_observations_clean.json",
               {"note": "One row per observation per detector. Detectors are never combined. "
                        "Missing values are null. qc_placeholder is NOT a quality flag "
                        "(RAD RDR SIS v3.2 sec. 4.2.1.2).",
                "records": df.replace({np.nan: None}).to_dict(orient="records")})
    write_csv(out_dir / "rad_sol_summary.csv", summ)
    write_json(out_dir / "rad_sol_summary.json", {"rows": summ})
    write_json(out_dir / "rad_trends.json", {"trends": trends})
    write_json(out_dir / "rad_processing_provenance.json", {
        "created_utc": utc_now_iso(), "instrument": "rad",
        "provenance_class": "DERIVED (statistics) from OBSERVED rover measurements",
        "spatial_coverage": "Curiosity rover location only - not a map, not live, not a forecast",
        "column_map_confirmed_by": cmap.get("confirmed_by"),
        "column_map_confirmed_against": cmap.get("confirmed_against"),
        "methods": {"extraction": "label byte offsets, cross-checked against text sections",
                    "per_sol": "unweighted mean/min/max/median/std of observation dose rates; "
                               "each detector separately"},
        "outputs": ["rad_observations_clean.csv", "rad_observations_clean.json",
                    "rad_sol_summary.csv", "rad_sol_summary.json", "rad_trends.json"],
        "processed": processed, "skipped": skipped, "n_clean_rows": int(len(df))})
    log.info("RAD: %d rows, %d sol-summary rows", len(df), len(summ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
