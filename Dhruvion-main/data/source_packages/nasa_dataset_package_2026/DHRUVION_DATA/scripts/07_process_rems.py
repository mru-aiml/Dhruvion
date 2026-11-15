#!/usr/bin/env python3
"""
07_process_rems.py - Step 4 processing of Curiosity REMS PDS3 tables.

Modes
-----
--suggest-mapping   Read one approved REMS label and write
                    config/rems_column_map.SUGGESTED.json listing every label
                    column (name, unit, description) with keyword hints. This
                    file is NEVER used for processing.
(default)           Process all Step-3-approved REMS labels with the CONFIRMED
                    column map config/rems_column_map.json. Outputs go to
                    processed/rems/: clean observations (CSV/JSON), per-sol
                    and per-session summaries, missing-value report, descriptive
                    trends and a provenance file.

See rover_tables.py for the integrity rules (confirmed maps only, units from
labels, NaN never zero, quality fields preserved).

Usage
-----
    python 07_process_rems.py --suggest-mapping
    python 07_process_rems.py --column-map config/rems_column_map.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhruvion_common import data_root_default, read_json, setup_logging, write_json  # noqa: E402
from rover_tables import (MappingError, approved_labels, process,  # noqa: E402
                          suggest_mapping)

INSTRUMENT = "rems"


def main(argv=None) -> int:
    root = data_root_default()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=root)
    ap.add_argument("--column-map", type=Path, default=None)
    ap.add_argument("--labels", type=Path, nargs="*", default=None)
    ap.add_argument("--fmt-dir", type=Path, action="append", default=[])
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--suggest-mapping", action="store_true")
    ap.add_argument("--skip-validation-gate", action="store_true",
                    help="ONLY for tests: process labels not approved in Step 3")
    args = ap.parse_args(argv)
    root = args.data_root.resolve()
    log = setup_logging(INSTRUMENT, root / f"metadata/logs/07_process_{INSTRUMENT}.log")
    cmap = args.column_map or root / f"scripts/config/{INSTRUMENT}_column_map.json"
    out_dir = args.out_dir or root / f"processed/{INSTRUMENT}"
    doc = root / f"raw/{INSTRUMENT}/documentation"
    fmt_dirs = list(args.fmt_dir) + ([doc] + [d for d in doc.rglob("*") if d.is_dir()]
                                     if doc.exists() else [])
    try:
        if args.suggest_mapping:
            labels = args.labels or approved_labels(
                read_json(root / "metadata/validation_pds_tables.json"), INSTRUMENT)
            if not labels:
                log.error("No approved %s labels found - run Step 3 first", INSTRUMENT.upper())
                return 3
            out = root / f"scripts/config/{INSTRUMENT}_column_map.SUGGESTED.json"
            write_json(out, suggest_mapping(Path(labels[0]), INSTRUMENT, fmt_dirs))
            log.info("Suggestions written to %s - review against the SIS", out)
            return 0
        prov = process(INSTRUMENT, cmap, root, out_dir, log, labels=args.labels,
                       fmt_dirs=fmt_dirs, skip_validation_gate=args.skip_validation_gate)
        log.info("%s processed: %d rows; %d product(s) skipped",
                 INSTRUMENT.upper(), prov["n_clean_rows"], len(prov["skipped"]))
        return 0
    except MappingError as exc:
        log.error("%s", exc)
        return 4


if __name__ == "__main__":
    sys.exit(main())
