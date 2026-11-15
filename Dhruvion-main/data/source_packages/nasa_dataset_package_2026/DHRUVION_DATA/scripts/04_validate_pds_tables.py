#!/usr/bin/env python3
"""
04_validate_pds_tables.py - Step 3 validation of REMS and RAD PDS3 products.

For every label (*.LBL, or *.TAB/*.TXT with an attached label):
* parse the label and its ^STRUCTURE .FMT files (pds3_table.py);
* list every column with NAME, DATA_TYPE, UNIT and DESCRIPTION exactly as
  written in the label;
* count UNK / NULL / N/A tokens and declared special constants per column
  (converted to NaN / None, never to zero);
* compare rows read with the label's ROWS;
* identify candidate time fields (SOL, LMST, LTST, SCLK, UTC, TIME, DATE)
  and candidate quality/confidence fields (QUALITY, FLAG, CONFIDENCE,
  UNCERTAINTY, ERROR, STATUS). These are NAME-BASED identifications and must
  be confirmed against the Software Interface Specification (SIS);
* report temporal coverage when a sol or time column is identified;
* note whether documentation (SIS, FMT) is present next to the data.

Per-product column dictionaries are written to
metadata/column_dictionaries/<instrument>/<label stem>.json.

Status vocabulary: VALIDATED, VALIDATED WITH LIMITATIONS, INVALID, INCOMPLETE.

Usage
-----
    python 04_validate_pds_tables.py                     # scans raw/rems, raw/rad
    python 04_validate_pds_tables.py --labels raw/rad/X.LBL --instrument rad \
        --fmt-dir raw/rad/documentation
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import (data_root_default, setup_logging, utc_now_iso,  # noqa: E402
                             write_json)
from pds3_table import UnsupportedProduct, read_pds3_tables  # noqa: E402

TIME_RX = re.compile(r"(^|_)(SOL|LMST|LTST|SCLK|UTC|TIME|DATE|TIMESTAMP)(_|$)", re.I)
QUAL_RX = re.compile(r"QUALITY|FLAG|CONFIDENCE|UNCERTAINTY|ERROR|STATUS|VALID", re.I)
SENTINEL_CANDIDATES = (-999.0, -9999.0, -99999.0, 9999.0, 99999.0, -1.0e30, -1.0e32)
DOC_RX = re.compile(r"\.(pdf|txt|cat|fmt)$", re.I)


def coverage_from(df, time_cols):
    cov = {}
    for c in time_cols:
        s = df[c]
        if s.dtype.kind in "fi":
            v = s.dropna()
            if len(v):
                cov[c] = {"min": float(v.min()), "max": float(v.max()),
                          "n_distinct": int(v.nunique())}
        else:
            v = s.dropna().astype(str)
            if len(v):
                cov[c] = {"first": v.iloc[0], "last": v.iloc[-1],
                          "lexical_min": v.min(), "lexical_max": v.max()}
    return cov


def validate_label(label: Path, instrument: str, fmt_dirs: list[Path], root: Path) -> dict:
    rec = {"label": str(label), "instrument": instrument,
           "checked_utc": utc_now_iso(), "reasons_invalid": [],
           "reasons_incomplete": [], "limitations": [], "tables": []}
    if instrument == "rad":
        from rad_rdr import validate_rad_label
        return finalize(validate_rad_label(label, rec, root))
    try:
        tables = read_pds3_tables(label, fmt_dirs)
    except FileNotFoundError as exc:
        rec["reasons_incomplete"].append(f"Referenced file missing: {exc}")
        return finalize(rec)
    except UnsupportedProduct as exc:
        rec["reasons_invalid"].append(f"Unsupported product: {exc}")
        return finalize(rec)
    except Exception as exc:
        rec["reasons_invalid"].append(f"Label/table parse error: {type(exc).__name__}: {exc}")
        return finalize(rec)

    for t in tables:
        df = t.data
        names = [c.name for c in t.columns]
        time_cols = [n for n in names if TIME_RX.search(n)]
        qual_cols = [n for n in names if QUAL_RX.search(n)]
        numeric = [c for c in t.columns if c.numeric]
        no_unit = [c.name for c in numeric if not c.unit or c.unit.upper() in ("N/A", "NONE", "UNK")]
        mostly_missing = [c.name for c in numeric
                          if t.qc["columns"][c.name]["n_rows"]
                          and t.qc["columns"][c.name]["n_valid"] / t.qc["columns"][c.name]["n_rows"] < 0.5]
        tinfo = {"object": t.object_name, "data_file": t.data_path,
                 "declared_rows": t.declared_rows, "rows_read": len(df),
                 "row_count_matches_label": t.qc["row_count_matches_label"],
                 "n_columns": len(names),
                 "candidate_time_columns_name_based": time_cols,
                 "candidate_quality_columns_name_based": qual_cols,
                 "numeric_columns_without_unit": no_unit,
                 "numeric_columns_mostly_missing": mostly_missing,
                 "temporal_coverage": coverage_from(df, time_cols),
                 "usable_rows_any_numeric_valid": int(np.isfinite(
                     df[[c.name for c in numeric]].to_numpy(dtype=float)).any(axis=1).sum())
                 if numeric else 0}
        sentinels = {}
        for c in numeric:
            v = df[c.name]
            hits = {str(x): int((v == x).sum()) for x in SENTINEL_CANDIDATES if (v == x).any()}
            if hits:
                sentinels[c.name] = hits
        tinfo["undeclared_sentinel_candidates"] = sentinels
        if sentinels:
            rec["limitations"].append(
                f"{t.object_name}: {len(sentinels)} numeric column(s) contain values such as -999 "
                "that the label does not declare as missing - treat them as missing only where "
                "the SIS documents it")
        kw = t.label_keywords
        if (kw.get("RECORD_TYPE", "").upper() == "FIXED_LENGTH"
                and Path(t.data_path).resolve() != Path(t.label_path).resolve()
                and kw.get("FILE_RECORDS") and kw.get("RECORD_BYTES")):
            exp = int(kw["FILE_RECORDS"]) * int(kw["RECORD_BYTES"])
            act = Path(t.data_path).stat().st_size
            tinfo["file_size_check"] = {"expected_bytes": exp, "actual_bytes": act,
                                        "ok": exp == act}
            if exp != act:
                rec["reasons_incomplete"].append(
                    f"{Path(t.data_path).name}: size {act} B != FILE_RECORDS x RECORD_BYTES = {exp} B")
        rec["tables"].append(tinfo)
        if not t.qc["row_count_matches_label"]:
            rec["reasons_incomplete"].append(
                f"{t.object_name}: label ROWS={t.declared_rows} but {len(df)} rows read")
        if no_unit:
            rec["limitations"].append(
                f"{t.object_name}: {len(no_unit)} numeric column(s) have no UNIT in label "
                "- units must come from the SIS before use")
        if mostly_missing:
            rec["limitations"].append(
                f"{t.object_name}: {len(mostly_missing)} numeric column(s) are >50% missing")
        dict_path = (root / "metadata/column_dictionaries" / instrument
                     / f"{label.stem}__{t.object_name}.json")
        write_json(dict_path, {"label": str(label), "object": t.object_name,
                               "label_keywords": t.label_keywords,
                               "qc": {k: v for k, v in t.qc.items() if k != "columns"},
                               "columns": t.column_dictionary()})
        tinfo["column_dictionary"] = str(dict_path.relative_to(root))

    docs = [p for p in label.parent.parent.rglob("*") if p.is_file() and DOC_RX.search(p.name)
            and "documentation" in str(p).lower()]
    rec["documentation_files_found"] = [str(p) for p in docs[:50]]
    if not docs:
        rec["limitations"].append("No SIS/documentation files found alongside the data")
    rec["spatial_coverage"] = ("Curiosity rover location only (single-point, rover-local "
                               "measurements; not a map)")
    return finalize(rec)


def finalize(rec: dict) -> dict:
    if rec["reasons_invalid"]:
        s = "INVALID"
    elif rec["reasons_incomplete"]:
        s = "INCOMPLETE"
    elif rec["limitations"]:
        s = "VALIDATED WITH LIMITATIONS"
    else:
        s = "VALIDATED"
    rec["validation_status"] = s
    rec["approved_for_processing"] = s in ("VALIDATED", "VALIDATED WITH LIMITATIONS")
    return rec


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--labels", type=Path, nargs="*")
    ap.add_argument("--instrument", default="auto", choices=["auto", "rems", "rad"])
    ap.add_argument("--fmt-dir", type=Path, action="append", default=[])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    out = args.out or root / "metadata/validation_pds_tables.json"
    log = setup_logging("validate_pds", root / "metadata/logs/04_validate_pds_tables.log")

    if args.labels:
        labels = [(p, args.instrument) for p in args.labels]
    else:
        labels = [(p, inst) for inst in ("rems", "rad")
                  for p in sorted((root / "raw" / inst).rglob("*"))
                  if p.is_file() and p.suffix.lower() == ".lbl"
                  and "documentation" not in str(p).lower()]
    results = []
    for path, inst in labels:
        if inst == "auto":
            inst = "rad" if "/rad" in str(path).lower() else "rems"
        fmt_dirs = list(args.fmt_dir) + [root / "raw" / inst / "documentation"]
        fmt_dirs += [d for d in (root / "raw" / inst / "documentation").rglob("*") if d.is_dir()] \
            if (root / "raw" / inst / "documentation").exists() else []
        rec = validate_label(Path(path), inst, fmt_dirs, root)
        log.info("%-28s %s", rec["validation_status"], path)
        results.append(rec)
    write_json(out, {"generated_utc": utc_now_iso(), "n_labels": len(results),
                     "products": results})
    log.info("Validated %d labels -> %s", len(results), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
