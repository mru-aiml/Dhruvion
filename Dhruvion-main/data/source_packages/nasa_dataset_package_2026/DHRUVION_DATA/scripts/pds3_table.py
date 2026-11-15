"""
pds3_table.py - label-driven reader for PDS3 ASCII TABLE / SPREADSHEET products.

Design rules (DHRUVION scientific-integrity requirements)
--------------------------------------------------------
* Column names, positions, data types, units and special constants come ONLY
  from the PDS3 label and its ^STRUCTURE format (.FMT) files. Nothing is
  hard-coded for REMS or RAD.
* PDS3 special values "UNK", "NULL", "N/A" and any MISSING_CONSTANT /
  INVALID_CONSTANT / NULL_CONSTANT / UNKNOWN_CONSTANT /
  NOT_APPLICABLE_CONSTANT declared for a column are converted to NaN (numeric)
  or None (text) - NEVER to zero - and each occurrence is counted.
* Values that cannot be parsed according to the declared DATA_TYPE become NaN
  and are counted as 'unparseable'.
* Binary tables are rejected with an explicit error (use calibrated ASCII
  RDRs; RAD EDR binaries are out of scope).

Public API
----------
read_label(path)                  -> pvl module
find_tables(label)                -> list of (object_name, pvl object, pointer)
read_pds3_tables(label_path, fmt_dirs=None) -> list[TableResult]
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pvl

SPECIAL_TOKENS = {"UNK": "unk", "NULL": "null", "N/A": "not_applicable"}
CONSTANT_KEYS = {
    "MISSING_CONSTANT": "missing_constant",
    "INVALID_CONSTANT": "invalid_constant",
    "NULL_CONSTANT": "null_constant",
    "UNKNOWN_CONSTANT": "unknown_constant",
    "NOT_APPLICABLE_CONSTANT": "not_applicable_constant",
}
NUMERIC_TYPES = ("ASCII_REAL", "ASCII_INTEGER", "ASCII_COMPLEX", "REAL",
                 "INTEGER", "FLOAT")
DELIMITERS = {"COMMA": ",", "SEMICOLON": ";", "TAB": "\t", "VERTICAL_BAR": "|"}


class UnsupportedProduct(ValueError):
    pass


@dataclass
class ColumnDef:
    name: str
    data_type: str
    start_byte: int | None
    bytes: int | None
    unit: str | None
    description: str | None
    constants: dict = field(default_factory=dict)
    field_number: int | None = None

    @property
    def numeric(self) -> bool:
        return any(t in self.data_type.upper() for t in NUMERIC_TYPES)


@dataclass
class TableResult:
    label_path: str
    data_path: str
    object_name: str
    declared_rows: int | None
    columns: list[ColumnDef]
    data: pd.DataFrame
    qc: dict
    label_keywords: dict

    def column_dictionary(self) -> list[dict]:
        out = []
        for c in self.columns:
            out.append({"name": c.name, "data_type": c.data_type,
                        "unit_from_label": c.unit, "description": c.description,
                        "start_byte": c.start_byte, "bytes": c.bytes,
                        "special_constants": c.constants,
                        "qc": self.qc["columns"].get(c.name)})
        return out


# ---------------------------------------------------------------------------
def _plain(v: Any) -> Any:
    """Strip pvl Quantity wrappers and whitespace."""
    if hasattr(v, "value") and hasattr(v, "units"):
        return v.value
    if isinstance(v, str):
        return v.strip()
    return v


def _items(obj) -> list[tuple[str, Any]]:
    return list(obj.items()) if hasattr(obj, "items") else []


def read_label(path: Path):
    path = Path(path)
    try:
        return pvl.load(str(path))
    except Exception:
        # Attached label: parse only the text up to the END statement.
        raw = path.read_bytes()
        txt = raw.decode("latin-1")
        idx = _end_statement_index(txt)
        if idx is None:
            raise
        return pvl.loads(txt[:idx] + "\nEND\n")


def _end_statement_index(txt: str) -> int | None:
    pos = 0
    for line in txt.splitlines(keepends=True):
        if line.strip().upper() == "END":
            return pos
        pos += len(line)
    return None


def find_tables(label) -> list[tuple[str, Any, Any]]:
    """Return (object_name, object, pointer_value) for TABLE/SPREADSHEET objects."""
    pointers = {k[1:].upper(): v for k, v in _items(label) if k.startswith("^")}
    out = []
    for k, v in _items(label):
        ku = k.upper()
        if ku.endswith("TABLE") or ku.endswith("SPREADSHEET") or ku == "SERIES":
            if hasattr(v, "items"):
                out.append((k, v, pointers.get(ku)))
    return out


def _locate(name: str, search_dirs: list[Path]) -> Path | None:
    """Case-insensitive file lookup across search directories."""
    target = name.lower()
    for d in search_dirs:
        if not d or not d.exists():
            continue
        for p in d.iterdir():
            if p.name.lower() == target:
                return p
    return None


def _pointer_to_file_offset(pointer, label_path: Path, label, search_dirs) -> tuple[Path, int]:
    """Resolve a PDS3 pointer to (data file, byte offset)."""
    rec_bytes = _plain(label.get("RECORD_BYTES")) if hasattr(label, "get") else None
    if pointer is None:
        raise UnsupportedProduct("No ^TABLE pointer found in label")
    p = pointer
    if isinstance(p, (list, tuple)) and len(p) == 2:
        fname, off = p[0], p[1]
        path = _locate(str(_plain(fname)), search_dirs)
        if path is None:
            raise FileNotFoundError(f"Data file {fname} not found near {label_path}")
        return path, _offset_bytes(off, rec_bytes)
    if isinstance(_plain(p), str):
        path = _locate(_plain(p), search_dirs)
        if path is None:
            raise FileNotFoundError(f"Data file {p} not found near {label_path}")
        return path, 0
    # integer / quantity -> attached label in the same file
    return label_path, _offset_bytes(p, rec_bytes)


def _offset_bytes(off, rec_bytes) -> int:
    if hasattr(off, "units") and str(off.units).upper().startswith("BYTE"):
        return int(off.value) - 1
    off = int(_plain(off))
    if rec_bytes is None:
        raise UnsupportedProduct("Record-based pointer but RECORD_BYTES missing")
    return (off - 1) * int(rec_bytes)


def _column_defs(obj, search_dirs: list[Path]) -> list[ColumnDef]:
    cols: list[ColumnDef] = []
    for k, v in _items(obj):
        ku = k.upper()
        if ku == "^STRUCTURE":
            fmt = _locate(str(_plain(v)), search_dirs)
            if fmt is None:
                raise FileNotFoundError(f"Format file {v} not found in {search_dirs}")
            cols.extend(_column_defs(read_label(fmt), search_dirs))
        elif ku in ("COLUMN", "FIELD"):
            cols.extend(_expand_column(v))
        elif ku == "CONTAINER":
            raise UnsupportedProduct("CONTAINER objects are not supported; "
                                     "inspect this label manually")
    return cols


def _expand_column(v) -> list[ColumnDef]:
    name = str(_plain(v.get("NAME")))
    dtype = str(_plain(v.get("DATA_TYPE", "CHARACTER"))).upper()
    unit = v.get("UNIT")
    unit = None if unit is None else str(_plain(unit))
    desc = v.get("DESCRIPTION")
    desc = None if desc is None else " ".join(str(desc).split())
    consts = {CONSTANT_KEYS[k]: _plain(v.get(k)) for k in CONSTANT_KEYS if k in v}
    start = v.get("START_BYTE")
    nbytes = v.get("BYTES")
    fnum = v.get("FIELD_NUMBER")
    items = v.get("ITEMS")
    if items:
        ib = int(_plain(v.get("ITEM_BYTES")))
        io_ = int(_plain(v.get("ITEM_OFFSET", ib)))
        return [ColumnDef(f"{name}_{i + 1}", dtype, int(_plain(start)) + i * io_, ib,
                          unit, desc, consts) for i in range(int(_plain(items)))]
    return [ColumnDef(name, dtype,
                      None if start is None else int(_plain(start)),
                      None if nbytes is None else int(_plain(nbytes)),
                      unit, desc, consts,
                      None if fnum is None else int(_plain(fnum)))]


def _convert(raw: list[str], col: ColumnDef) -> tuple[list, dict]:
    qc = {"n_rows": len(raw), "n_valid": 0, "unk": 0, "null": 0,
          "not_applicable": 0, "unparseable": 0, "empty": 0}
    for v in CONSTANT_KEYS.values():
        qc[v] = 0
    numeric_consts = {}
    for key, cval in col.constants.items():
        try:
            numeric_consts[key] = float(cval)
        except (TypeError, ValueError):
            pass
    out = []
    for s in raw:
        tok = s.strip().strip('"').strip()
        if tok == "":
            qc["empty"] += 1
            out.append(np.nan if col.numeric else None)
            continue
        if tok.upper() in SPECIAL_TOKENS:
            qc[SPECIAL_TOKENS[tok.upper()]] += 1
            out.append(np.nan if col.numeric else None)
            continue
        str_hit = [k for k, cv in col.constants.items()
                   if isinstance(cv, str) and tok == cv.strip()]
        if str_hit:
            qc[str_hit[0]] += 1
            out.append(np.nan if col.numeric else None)
            continue
        if col.numeric:
            try:
                val = float(tok)
            except ValueError:
                qc["unparseable"] += 1
                out.append(np.nan)
                continue
            hit = [k for k, cv in numeric_consts.items()
                   if math.isclose(val, cv, rel_tol=0, abs_tol=0)]
            if hit:
                qc[hit[0]] += 1
                out.append(np.nan)
                continue
            qc["n_valid"] += 1
            out.append(val)
        else:
            qc["n_valid"] += 1
            out.append(tok)
    return out, qc


def read_pds3_tables(label_path: Path, fmt_dirs: list[Path] | None = None) -> list[TableResult]:
    label_path = Path(label_path)
    label = read_label(label_path)
    search = [label_path.parent, label_path.parent.parent / "LABEL",
              label_path.parent.parent / "label", *(fmt_dirs or [])]
    if str(_plain(label.get("INTERCHANGE_FORMAT", "ASCII"))).upper() == "BINARY":
        raise UnsupportedProduct("Binary interchange format - not supported")
    results = []
    for name, obj, pointer in find_tables(label):
        fmt = str(_plain(obj.get("INTERCHANGE_FORMAT",
                                 label.get("INTERCHANGE_FORMAT", "ASCII")))).upper()
        if fmt == "BINARY":
            raise UnsupportedProduct(f"{name}: binary table - not supported")
        data_path, offset = _pointer_to_file_offset(pointer, label_path, label, search)
        cols = _column_defs(obj, search)
        if not cols:
            raise UnsupportedProduct(f"{name}: no COLUMN/FIELD definitions found")
        declared_rows = obj.get("ROWS")
        declared_rows = None if declared_rows is None else int(_plain(declared_rows))
        text = data_path.read_bytes()[offset:].decode("latin-1")
        lines = [l.rstrip("\r") for l in text.split("\n")]
        if declared_rows is not None:
            lines = lines[:declared_rows]
        else:
            while lines and lines[-1].strip() == "":
                lines.pop()
        is_sheet = name.upper().endswith("SPREADSHEET") or all(
            c.start_byte is None for c in cols)
        if is_sheet:
            delim = DELIMITERS.get(str(_plain(obj.get("FIELD_DELIMITER", "COMMA"))).upper(), ",")
            rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
            cols = sorted(cols, key=lambda c: c.field_number or 0)
            raw_cols = {c.name: [r[i] if i < len(r) else "" for r in rows]
                        for i, c in enumerate(cols)}
        else:
            raw_cols = {c.name: [l[c.start_byte - 1: c.start_byte - 1 + c.bytes]
                                 for l in lines] for c in cols}
        data, colqc = {}, {}
        for c in cols:
            data[c.name], colqc[c.name] = _convert(raw_cols[c.name], c)
        df = pd.DataFrame(data)
        qc = {"declared_rows": declared_rows, "rows_read": len(df),
              "row_count_matches_label": (declared_rows is None
                                          or declared_rows == len(df)),
              "columns": colqc}
        kw = {k: str(_plain(v)) for k, v in _items(label)
              if not hasattr(v, "items") and not k.startswith("^")}
        results.append(TableResult(str(label_path), str(data_path), name,
                                   declared_rows, cols, df, qc, kw))
    if not results:
        raise UnsupportedProduct("No TABLE or SPREADSHEET objects in label")
    return results
