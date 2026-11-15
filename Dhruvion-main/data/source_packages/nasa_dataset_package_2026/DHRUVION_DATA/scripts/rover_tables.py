"""
rover_tables.py - shared Step 4 processing for Curiosity REMS and RAD tables.

Scientific-integrity rules enforced here
----------------------------------------
1. Statistics are computed ONLY for columns listed in a column-map file whose
   "status" is "CONFIRMED" (i.e. a person checked each mapping against the
   instrument SIS). Suggested maps (status "SUGGESTED...") are refused.
2. Units come from the PDS label (COLUMN UNIT). If the map gives an
   expected_unit that differs from the label, that measurement is SKIPPED.
3. Missing / special values are NaN (never zero); counts are reported.
4. Quality / confidence columns named in the map are carried into the clean
   output unchanged; quality-filtered statistics are reported ALONGSIDE
   unfiltered ones, never instead of them.
5. Each measurement key is summarised separately. Nothing is averaged across
   measurement keys, detectors or units (RAD requires a 'detector' per key).
6. Only Step-3-approved labels are processed (metadata/validation_pds_tables.json),
   unless the caller passes skip_validation_gate=True (tests only).

Column-map format (config/<instrument>_column_map.json)
------------------------------------------------------
{
  "status": "CONFIRMED",
  "confirmed_by": "...", "confirmed_against": "SIS document name/version",
  "time": {"sol_column": null, "sol_from_path_regex": "SOL(\\d{4,5})",
           "session_time_column": null, "session_time_type": "numeric_seconds"|"iso_utc",
           "session_gap_seconds": 600},
  "measurements": {
     "<key>": {"column": "<NAME exactly as in label>", "quantity": "...",
               "expected_unit": "<unit string as in label, optional>",
               "detector": "<RAD only>",
               "quality_column": "<optional>", "good_quality_values": [..]}
  },
  "preserve_columns": ["<extra label columns to copy unchanged>"]
}
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from dhruvion_common import read_json, utc_now_iso, write_csv, write_json
from pds3_table import read_pds3_tables

SUGGEST_RX = {
    "rems": {
        "air_temperature": r"AIR.*TEMP|TEMP.*AIR|\bATS\b",
        "ground_temperature": r"GROUND.*TEMP|\bGTS\b|BRIGHTNESS",
        "pressure": r"PRESS",
        "wind_speed": r"WIND.*SPEED|HORIZONTAL.*WIND",
        "wind_direction": r"WIND.*DIR",
        "relative_humidity": r"HUMID|\bRH\b",
        "uv": r"\bUV",
        "sol": r"(^|_)SOL(_|$)",
        "time": r"LMST|LTST|TIMESTAMP|SCLK|UTC",
        "quality": r"CONFIDENCE|QUALITY|FLAG|UNCERTAINTY",
    },
    "rad": {
        "dose_rate": r"DOSE",
        "flux": r"FLUX",
        "let": r"\bLET\b|LINEAR_ENERGY",
        "sol": r"(^|_)SOL(_|$)",
        "time": r"SCLK|UTC|TIME|LMST",
        "quality": r"QUALITY|FLAG|STATUS|VALID",
    },
}


class MappingError(ValueError):
    pass


def _qtoken(s) -> str:
    return s.replace(" ", "") if isinstance(s, str) else ""


# Rules for multi-character confidence codes (e.g. REMS: '1' optimal, '0' not
# optimal, 'X' unknown - REMS RDR SIS section 3.1.6).
QUALITY_RULES = {
    "all_ones": lambda s: _qtoken(s) != "" and set(_qtoken(s)) == {"1"},
    "no_zeros": lambda s: _qtoken(s) != "" and "0" not in _qtoken(s),
}


def load_mapping(path: Path, instrument: str) -> dict:
    m = read_json(path)
    if not m:
        raise MappingError(f"Column map not found: {path}")
    status = str(m.get("status", "")).upper()
    if status != "CONFIRMED":
        raise MappingError(
            f"Column map {path.name} has status '{m.get('status')}'. Fill it in from the "
            "PDS labels/SIS and set status to CONFIRMED (suggested maps are never used).")
    meas = {k: v for k, v in (m.get("measurements") or {}).items() if v and v.get("column")}
    if not meas:
        raise MappingError("No measurement has a 'column' set in the map")
    if instrument == "rad":
        missing = [k for k, v in meas.items() if not v.get("detector")]
        if missing:
            raise MappingError("RAD measurements must name their detector "
                               f"(missing for: {missing}) - detectors are never combined")
    m["measurements"] = meas
    return m


def approved_labels(validation: dict, instrument: str) -> list[Path]:
    out = []
    for p in (validation or {}).get("products", []):
        if p.get("instrument") == instrument and p.get("approved_for_processing"):
            out.append(Path(p["label"]))
    return out


def suggest_mapping(label: Path, instrument: str, fmt_dirs: list[Path]) -> dict:
    tables = read_pds3_tables(label, fmt_dirs)
    cols = []
    for t in tables:
        for c in t.columns:
            hits = [k for k, rx in SUGGEST_RX[instrument].items()
                    if re.search(rx, c.name, re.I) or (c.description and k not in ("sol", "time")
                                                       and re.search(rx, c.description, re.I))]
            cols.append({"table": t.object_name, "name": c.name, "unit": c.unit,
                         "data_type": c.data_type, "description": c.description,
                         "keyword_hits": hits})
    return {"status": "SUGGESTED - REQUIRES HUMAN CONFIRMATION AGAINST THE SIS",
            "generated_utc": utc_now_iso(), "from_label": str(label),
            "warning": "Keyword hits are NOT definitions. Read each DESCRIPTION and the SIS, "
                       "then copy confirmed column names into the column map.",
            "label_columns": cols}


def _sol_series(df, table_path: str, tcfg: dict) -> tuple[pd.Series, str]:
    scr = tcfg.get("sol_from_column_regex")
    if scr and scr.get("column") in df.columns:
        s = df[scr["column"]].astype("string").str.extract(scr["regex"], expand=False)
        return pd.to_numeric(s, errors="coerce"), \
            f"regex {scr['regex']} applied to label column {scr['column']}"
    col = tcfg.get("sol_column")
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce"), f"label column {col}"
    rx = tcfg.get("sol_from_path_regex")
    if rx:
        m = re.search(rx, table_path, re.I)
        if m:
            return pd.Series(int(m.group(1)), index=df.index, dtype="float64"), \
                f"archive path regex {rx}"
    return pd.Series(np.nan, index=df.index), "UNAVAILABLE"


def _session_ids(df, product: str, tcfg: dict) -> tuple[pd.Series, str]:
    col = tcfg.get("session_time_column")
    gap = float(tcfg.get("session_gap_seconds", 600))
    if col and col in df.columns:
        if tcfg.get("session_time_type") == "iso_utc":
            t = pd.to_datetime(df[col], errors="coerce", utc=True)
            secs = (t - t.min()).dt.total_seconds()
        else:
            secs = pd.to_numeric(df[col], errors="coerce")
        order = secs.dropna().sort_values(kind="stable")
        new = order.diff().fillna(np.inf) > gap
        sid = pd.Series(product + "#UNTIMED", index=df.index, dtype=object)
        sid.loc[order.index] = product + "#S" + new.cumsum().astype(int).astype(str)
        return sid, f"gap > {gap:g} s in {col}; rows without a valid time -> #UNTIMED"
    return pd.Series(product + "#S1", index=df.index), "one session per product file (no time column mapped)"


def _stats(v: pd.Series, circular: bool = False) -> dict:
    v = pd.to_numeric(v, errors="coerce")
    ok = v.dropna()
    d = {"n_rows": int(len(v)), "n_valid": int(len(ok)), "n_missing": int(len(v) - len(ok))}
    if circular:
        if len(ok):
            r = np.radians(ok.to_numpy(float))
            c, s = np.cos(r).mean(), np.sin(r).mean()
            d.update(circular_mean_deg=float((np.degrees(np.arctan2(s, c)) + 360) % 360),
                     resultant_length=float(np.hypot(c, s)),
                     note="circular statistics (arithmetic mean is invalid for angles)")
        return d
    if len(ok):
        d.update(mean=float(ok.mean()), min=float(ok.min()), max=float(ok.max()),
                 median=float(ok.median()), std=float(ok.std(ddof=1)) if len(ok) > 1 else None)
    return d


def process(instrument: str, mapping_path: Path, root: Path, out_dir: Path, log,
            labels: list[Path] | None = None, fmt_dirs: list[Path] | None = None,
            skip_validation_gate: bool = False) -> dict:
    mapping = load_mapping(mapping_path, instrument)
    tcfg = mapping.get("time", {})
    if labels is None:
        labels = approved_labels(read_json(root / "metadata/validation_pds_tables.json"),
                                 instrument)
    elif not skip_validation_gate:
        ok = set(map(str, approved_labels(
            read_json(root / "metadata/validation_pds_tables.json"), instrument)))
        labels = [l for l in labels if str(l) in ok]
    if not labels:
        raise MappingError(f"No Step-3-approved {instrument.upper()} labels to process")
    fmt_dirs = fmt_dirs or []
    sent = mapping.get("missing_value_sentinels") or {}
    svals = [float(x) for x in sent.get("values", [])]

    frames, processed, skipped, units, missing_report = [], [], [], {}, []
    for label in labels:
        try:
            tables = read_pds3_tables(label, fmt_dirs)
        except Exception as exc:
            skipped.append({"label": str(label), "reason": f"{type(exc).__name__}: {exc}"})
            log.warning("Skipped %s: %s", label, exc)
            continue
        for t in tables:
            colmap = {c.name: c for c in t.columns}
            keep = {}
            for key, spec in mapping["measurements"].items():
                col = spec["column"]
                if col not in colmap:
                    continue
                label_unit = colmap[col].unit
                exp = spec.get("expected_unit")
                if exp and (label_unit or "").strip() != exp.strip():
                    skipped.append({"label": str(label), "measurement": key,
                                    "reason": f"unit mismatch: label '{label_unit}' vs "
                                              f"expected '{exp}'"})
                    log.warning("Unit mismatch for %s in %s - skipped", key, label.name)
                    continue
                keep[key] = col
                prev = units.get(key)
                if prev is not None and prev != label_unit:
                    raise MappingError(f"Measurement {key} has inconsistent units across "
                                       f"products ({prev} vs {label_unit}) - refusing to merge")
                units[key] = label_unit
                q = dict(t.qc["columns"][col])
                if svals:  # documented sentinels (e.g. REMS -999) -> NaN, counted
                    num = pd.to_numeric(t.data[col], errors="coerce")
                    hit = num.isin(svals)
                    q["documented_sentinel"] = int(hit.sum())
                    q["n_valid"] = int(q["n_valid"]) - int(hit.sum())
                    t.data[col] = num.mask(hit)
                missing_report.append({"product": Path(t.data_path).name, "measurement": key,
                                       "column": col, **{k: v for k, v in q.items()}})
            if not keep:
                skipped.append({"label": str(label), "table": t.object_name,
                                "reason": "no mapped measurement columns present"})
                continue
            df = t.data
            out = pd.DataFrame(index=df.index)
            out["source_product"] = Path(t.data_path).name
            out["sol"], sol_src = _sol_series(df, t.data_path, tcfg)
            out["session_id"], sess_src = _session_ids(df, Path(t.data_path).stem, tcfg)
            extra = list(dict.fromkeys(
                [c for c in [tcfg.get("sol_column"), tcfg.get("session_time_column")]
                 if c and c in df.columns]
                + [s.get("quality_column") for s in mapping["measurements"].values()
                   if s.get("quality_column") in df.columns]
                + [c for c in mapping.get("preserve_columns", []) if c in df.columns]))
            for c in extra:
                col_s = df[c]
                if svals and col_s.dtype.kind in "fi":
                    col_s = col_s.mask(col_s.isin(svals))
                out[c] = col_s
            for key, col in keep.items():
                out[col] = df[col]
            frames.append(out)
            processed.append({"label": str(label), "table": t.object_name,
                              "rows": len(df), "measurements": keep,
                              "sol_source": sol_src, "session_rule": sess_src})
            log.info("Processed %s (%d rows, %d measurements)", label.name, len(df), len(keep))

    if not frames:
        raise MappingError("Nothing processed - see skipped list")
    clean = pd.concat(frames, ignore_index=True)

    def summarise(group_cols):
        rows = []
        for gkey, g in clean.groupby(group_cols, dropna=False):
            gkey = gkey if isinstance(gkey, tuple) else (gkey,)
            for key, spec in mapping["measurements"].items():
                col = spec["column"]
                if col not in g.columns or key not in units:
                    continue
                base = dict(zip(group_cols, gkey))
                base.update(measurement=key, column=col, quantity=spec.get("quantity"),
                            detector=spec.get("detector"), unit=units[key])
                circ = bool(spec.get("circular"))
                rows.append({**base, "filter": "all_valid_values", **_stats(g[col], circ)})
                qc, good = spec.get("quality_column"), spec.get("good_quality_values")
                if qc and qc in g.columns and good is not None:
                    sel = g[qc].isin(good)
                    rows.append({**base, "filter": f"{qc} in {good}",
                                 "n_excluded_by_quality": int((~sel).sum()),
                                 **_stats(g.loc[sel, col], circ)})
                for rule in spec.get("quality_rules") or []:
                    if qc and qc in g.columns:
                        sel = g[qc].map(QUALITY_RULES[rule]).astype(bool)
                        rows.append({**base, "filter": f"{qc}: {rule}",
                                     "n_excluded_by_quality": int((~sel).sum()),
                                     **_stats(g.loc[sel, col], circ)})
        return rows

    sol_rows = summarise(["sol"])
    sess_rows = summarise(["sol", "session_id"])
    trends = []
    sdf = pd.DataFrame(sol_rows)
    if not sdf.empty:
        for (key, filt), g in sdf[sdf["n_valid"] > 0].groupby(["measurement", "filter"]):
            if "mean" not in g.columns:
                continue
            g = g.dropna(subset=["sol", "mean"]).sort_values("sol")
            rec = {"measurement": key, "filter": filt, "unit": units.get(key),
                   "n_sols": int(len(g)),
                   "sol_min": float(g["sol"].min()) if len(g) else None,
                   "sol_max": float(g["sol"].max()) if len(g) else None}
            if len(g) >= 5:
                slope, intercept = np.polyfit(g["sol"].to_numpy(float), g["mean"].to_numpy(float), 1)
                rec.update(ols_slope_per_sol=float(slope), ols_intercept=float(intercept),
                           note="Descriptive least-squares trend of per-sol means; "
                                "not a forecast; seasonal cycles not removed")
            else:
                rec["note"] = "Fewer than 5 sols - trend not computed"
            trends.append(rec)

    prefix = instrument
    out_dir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out_dir / f"{prefix}_observations_clean.csv", index=False, na_rep="")
    write_json(out_dir / f"{prefix}_observations_clean.json",
               {"note": "Missing values are null (never zero). Column names are exactly as "
                        "in the PDS labels.", "units": units,
                "records": clean.replace({np.nan: None}).to_dict(orient="records")})
    write_csv(out_dir / f"{prefix}_sol_summary.csv", sol_rows)
    write_json(out_dir / f"{prefix}_sol_summary.json", {"units": units, "rows": sol_rows})
    write_csv(out_dir / f"{prefix}_session_summary.csv", sess_rows)
    write_json(out_dir / f"{prefix}_session_summary.json", {"units": units, "rows": sess_rows})
    write_csv(out_dir / f"{prefix}_missing_values_report.csv", missing_report)
    write_json(out_dir / f"{prefix}_trends.json", {"trends": trends})
    prov = {"created_utc": utc_now_iso(), "instrument": instrument,
            "provenance_class": "DERIVED (statistics) from OBSERVED rover measurements",
            "spatial_coverage": "Curiosity rover location only - not a map, not live, not a forecast",
            "column_map": str(mapping_path), "column_map_confirmed_by": mapping.get("confirmed_by"),
            "column_map_confirmed_against": mapping.get("confirmed_against"),
            "units_from_labels": units, "processed": processed, "skipped": skipped,
            "n_clean_rows": int(len(clean))}
    write_json(out_dir / f"{prefix}_processing_provenance.json", prov)
    return prov
