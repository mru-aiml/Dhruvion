"""
rad_rdr.py - label-driven reader for MSL RAD calibrated RDR dosimetry.

Each RAD RDR .TXT holds one sol of observations (RAD RDR SIS v3.2 sec. 4.2.1).
For every observation NN the label defines OBSNN_TOT_DOSE_B_ELEMENT and
OBSNN_TOT_DOSE_E_ELEMENT objects (pointer byte offset, START_BYTE, BYTES,
DATA_TYPE, UNIT = "microGray / Hour"). Values are read at the label offsets
AND cross-checked against the text section [DOSIMETRY_TOTAL_DOSE_B: NN];
any disagreement is reported as invalid.

Observation headers ([OBSERVATION: NN] with START_OBS_MARS, START_OBS_UTC, QC,
ROVER_*) are parsed from the text. Per SIS v3.2 sec. 4.2.1.2, rover position
and QC are PLACEHOLDERS ("not yet implemented"), so they are reported but never
used to filter or locate data.

Counter, histogram, LET and PHA objects are not parsed (outside the scope of
dose-rate charts) and are listed as such.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import pvl

OBS_RX = re.compile(r"\[OBSERVATION:\s*(\d+)\]\s*\r?\n(.*?)(?:\r?\n[ \t]*\r?\n)", re.S)
SPECIAL = {"UNK", "NULL", "N/A"}


def _plain(v):
    return v.value if hasattr(v, "value") and hasattr(v, "units") else v


def parse_observation_headers(text: str) -> dict:
    out = {}
    for m in OBS_RX.finditer(text):
        kv = {}
        for line in m.group(2).splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip().strip('"')
        out[int(m.group(1))] = kv
    return out


def _locate(name: str, folder: Path) -> Path:
    for p in folder.iterdir():
        if p.name.lower() == name.lower():
            return p
    raise FileNotFoundError(f"{name} not found beside label in {folder}")


def read_rad_rdr(label_path: Path, suffixes=("TOT_DOSE_B_ELEMENT", "TOT_DOSE_E_ELEMENT")) -> dict:
    label_path = Path(label_path)
    label = pvl.load(str(label_path))
    items = list(label.items())
    pointers = {k[1:]: v for k, v in items if k.startswith("^")}
    kinds = Counter()
    elements, cache = [], {}
    for k, obj in items:
        m = re.match(r"OBS(\d+)_(.+)$", k)
        if not m or not hasattr(obj, "items"):
            continue
        kinds[m.group(2)] += 1
        if m.group(2) not in suffixes:
            continue
        ptr = pointers.get(k)
        if not isinstance(ptr, (list, tuple)) or len(ptr) != 2 or not hasattr(ptr[1], "units"):
            raise ValueError(f"{k}: expected (file, offset <BYTES>) pointer, got {ptr!r}")
        path = _locate(str(ptr[0]), label_path.parent)
        raw = cache.setdefault(path, path.read_bytes())
        off = int(ptr[1].value) - 1 + int(_plain(obj["START_BYTE"])) - 1
        tok = raw[off: off + int(_plain(obj["BYTES"]))].decode("latin-1").strip()
        try:
            val = math.nan if tok.upper() in SPECIAL else float(tok)
        except ValueError:
            val = math.nan
        obs = int(m.group(1))
        sec_name = m.group(2).replace("TOT_", "TOTAL_").replace("_ELEMENT", "")
        sm = re.search(rf"\[DOSIMETRY_{sec_name}:\s*{obs:02d}\]\s*\r?\n\s*\r?\n\s*([^\r\n]+)",
                       raw.decode("latin-1"))
        xval = None
        if sm:
            try:
                xval = float(sm.group(1).strip())
            except ValueError:
                xval = None
        elements.append({"obs": obs, "object": k, "suffix": m.group(2), "value": val,
                         "raw_token": tok, "unit": str(_plain(obj.get("UNIT"))),
                         "data_type": str(_plain(obj.get("DATA_TYPE"))),
                         "description": " ".join(str(obj.get("DESCRIPTION", "")).split()),
                         "label_name": str(_plain(obj.get("NAME"))),
                         "data_file": path.name, "byte_offset_1based": off + 1,
                         "crosscheck_section_value": xval,
                         "crosscheck_ok": (xval is not None and not math.isnan(val)
                                           and abs(xval - val) < 1e-9)
                         or (xval is None and math.isnan(val))})
    data_files = sorted(cache) or [label_path.with_suffix(".TXT")]
    text = data_files[0].read_bytes().decode("latin-1") if data_files[0].exists() else ""
    kw = {k: str(_plain(v)) for k, v in items if not hasattr(v, "items") and not k.startswith("^")}
    return {"label": str(label_path), "data_files": [str(p) for p in data_files],
            "keywords": kw, "object_kinds": dict(kinds), "elements": elements,
            "headers": parse_observation_headers(text)}


def obs_sol_lmst(h: dict):
    s = (h or {}).get("START_OBS_MARS", "")
    m = re.match(r"\s*(\d+)\s+(\d{2}:\d{2}:\d{2})", s)
    return (int(m.group(1)), m.group(2)) if m else (None, None)


def validate_rad_label(label: Path, rec: dict, root: Path) -> dict:
    """Fill a Step-3 validation record for one RAD RDR label."""
    try:
        r = read_rad_rdr(label)
    except FileNotFoundError as exc:
        rec["reasons_incomplete"].append(str(exc))
        return rec
    except Exception as exc:
        rec["reasons_invalid"].append(f"RAD label/data parse error: {type(exc).__name__}: {exc}")
        return rec
    el, hd = r["elements"], r["headers"]
    if not el:
        rec["reasons_invalid"].append("No TOT_DOSE_B/E ELEMENT objects found in label")
        return rec
    bad = [e["object"] for e in el if not e["crosscheck_ok"]]
    if bad:
        rec["reasons_invalid"].append(f"{len(bad)} dose value(s) disagree between label offsets "
                                      f"and text sections: {bad[:5]}")
    obs_el = sorted({e["obs"] for e in el})
    missing_hdr = [o for o in obs_el if o not in hd]
    if missing_hdr:
        rec["reasons_incomplete"].append(f"Dose elements without observation header: {missing_hdr}")
    no_dose = sorted(set(hd) - set(obs_el))
    units = sorted({e["unit"] for e in el})
    vals = [e["value"] for e in el]
    n_nan = sum(math.isnan(v) for v in vals)
    n_neg = sum((not math.isnan(v)) and v < 0 for v in vals)
    sols = sorted({obs_sol_lmst(h)[0] for h in hd.values() if obs_sol_lmst(h)[0] is not None})
    utc = sorted(h.get("START_OBS_UTC", "") for h in hd.values() if h.get("START_OBS_UTC"))
    qc = Counter(h.get("QC", "?") for h in hd.values())
    rec["tables"] = [{
        "object": "OBSnn_TOT_DOSE_B_ELEMENT / OBSnn_TOT_DOSE_E_ELEMENT",
        "data_file": r["data_files"][0], "n_observation_headers": len(hd),
        "n_dose_elements": len(el), "observations_without_dose": no_dose,
        "units_from_label": units, "n_missing_values": n_nan, "n_negative_values": n_neg,
        "crosscheck_label_vs_text": f"{len(el) - len(bad)}/{len(el)} agree",
        "temporal_coverage": {"sols_from_START_OBS_MARS": sols,
                              "utc_first": utc[0] if utc else None,
                              "utc_last": utc[-1] if utc else None},
        "qc_values": dict(qc), "object_kinds_in_label": r["object_kinds"]}]
    rec["limitations"] += [
        "QC and ROVER_LAT/LON/ELEV are placeholders per RAD RDR SIS v3.2 sec. 4.2.1.2 - "
        "not used as quality flags or location",
        "Only TOT_DOSE_B/E dose-rate elements are parsed; counters, histograms, LET arrays "
        "and PHA tables are present but not parsed",
    ]
    if no_dose:
        rec["limitations"].append(f"Observations without dose elements: {no_dose}")
    if n_nan:
        rec["limitations"].append(f"{n_nan} dose value(s) missing")
    docs = list((root / "raw/rad/documentation").glob("*")) if (root / "raw/rad/documentation").exists() else []
    rec["documentation_files_found"] = [str(p) for p in docs]
    if not docs:
        rec["limitations"].append("No SIS/documentation found alongside the data")
    rec["spatial_coverage"] = ("Curiosity rover location only (single-point, rover-local "
                               "measurements; not a map)")
    from dhruvion_common import write_json
    dpath = root / "metadata/column_dictionaries/rad" / f"{Path(label).stem}__dose_elements.json"
    write_json(dpath, {"label": str(label), "keywords": r["keywords"],
                       "object_kinds": r["object_kinds"],
                       "dose_element_definition": {k: el[0][k] for k in
                                                   ("unit", "data_type", "description")},
                       "elements": el})
    rec["tables"][0]["column_dictionary"] = str(dpath.relative_to(root))
    return rec
