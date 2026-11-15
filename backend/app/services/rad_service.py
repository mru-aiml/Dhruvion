"""RAD radiation service for the supplied NASA package.

Detectors B and E are independent instruments and are never combined. Dose
rates are reported in the package unit ``microGray / Hour``. The package
``qc_placeholder`` field is an 8-character placeholder, **not** a quality flag,
and is never interpreted as one.

Only sols 1-3 of the Curiosity RAD RDR are present. Values are historical
point measurements at the rover location and must not be used for
route-specific radiation predictions.
"""

from __future__ import annotations

import json
import math
import threading
from typing import Any, Dict, List, Optional

from app.core.exceptions import NotFoundError, UnavailableError
from app.data_pipeline.dataset_paths import get_dataset_paths
from app.services.terrain_service import RAD_SOURCE

DETECTOR_LABELS = {
    "dose_rate_B": "B (silicon detector)",
    "dose_rate_E": "E (BC-432 plastic scintillator)",
}

LIMITATIONS = [
    "RAD values are historical point measurements from the Curiosity rover (sols 1-3), "
    "not a route-specific radiation forecast or a spatial field.",
    "Detectors B and E measure different quantities and are reported separately; they are never merged.",
    "Only three sols are present, so no trend is computed.",
    "qc_placeholder is a placeholder field, not a quality indicator, and is not used to filter data.",
    "Dose rates must not be extrapolated to other locations or used to certify traverse safety.",
]


def _read_json(path) -> Any:
    if path is None or not path.exists():
        raise UnavailableError("RAD file unavailable", details={"file": getattr(path, "name", None)})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - corrupt handover file
        raise UnavailableError(f"Unable to read RAD file: {exc}") from exc


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class RadService:
    """Read-only access to the RAD sol summary, observations, and trends."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sol_summary: Optional[Dict[str, Any]] = None
        self._observations: Optional[Dict[str, Any]] = None
        self._trends: Optional[Dict[str, Any]] = None

    def _paths(self):
        paths = get_dataset_paths()
        if paths is None:
            raise UnavailableError(
                "NASA DHRUVION_DATA package not found. Set DHRUVION_DATA_DIR to the package root."
            )
        return paths

    def _data(self, key: str) -> Dict[str, Any]:
        with self._lock:
            cached = {
                "sol": self._sol_summary,
                "observations": self._observations,
                "trends": self._trends,
            }[key]
            if cached is not None:
                return cached
            paths = self._paths()
            mapping = {
                "sol": paths.rad_sol_summary,
                "observations": paths.rad_observations,
                "trends": paths.rad_trends,
            }
            data = _read_json(mapping[key])
            if key == "sol":
                self._sol_summary = data
            elif key == "observations":
                self._observations = data
            else:
                self._trends = data
            return data

    def available(self) -> bool:
        try:
            paths = self._paths()
        except UnavailableError:
            return False
        return not paths.missing("rad_sol_summary", "rad_observations", "rad_trends")

    def sols(self) -> List[int]:
        rows = self._data("sol").get("rows", [])
        return sorted({int(row["sol"]) for row in rows if row.get("sol") is not None})

    def sol_summary(self, sol: Optional[int] = None) -> Dict[str, Any]:
        data = self._data("sol")
        rows = [
            row
            for row in data.get("rows", [])
            if sol is None or int(row.get("sol", -1)) == int(sol)
        ]
        if sol is not None and not rows:
            raise NotFoundError("No RAD data for this sol", details={"sol": sol, "available_sols": self.sols()})

        detectors: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            measurement = row.get("measurement", "unknown")
            detector = row.get("detector") or DETECTOR_LABELS.get(measurement, measurement)
            detectors.setdefault(measurement, {
                "measurement": measurement,
                "detector": detector,
                "unit": row.get("unit", "microGray / Hour"),
                "filter": row.get("filter", "all_observations"),
                "sols": {},
            })
            detectors[measurement]["sols"][str(int(row["sol"]))] = {
                "sol": int(row["sol"]),
                "n_observations": row.get("n_observations"),
                "n_valid": row.get("n_valid"),
                "n_missing": row.get("n_missing"),
                "mean": _num(row.get("mean")),
                "min": _num(row.get("min")),
                "max": _num(row.get("max")),
                "median": _num(row.get("median")),
                "std": _num(row.get("std")),
                "utc_first": row.get("utc_first"),
                "utc_last": row.get("utc_last"),
            }

        return {
            "sols": [int(sol)] if sol is not None else self.sols(),
            "detectors": detectors,
            "unit": "microGray / Hour",
            "note": "Detectors are reported separately and are never combined.",
        }

    def observations(
        self,
        detector: Optional[str] = None,
        sol: Optional[int] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        data = self._data("observations")
        records = data.get("records", [])
        selected = []
        for record in records:
            if sol is not None and int(record.get("sol", -1)) != int(sol):
                continue
            if detector and detector not in str(record.get("detector", "")):
                continue
            selected.append(
                {
                    "sol": record.get("sol"),
                    "measurement": record.get("measurement"),
                    "detector": record.get("detector"),
                    "utc_start": record.get("utc_start"),
                    "lmst_start": record.get("lmst_start"),
                    "value": _num(record.get("value")),
                    "unit": record.get("unit", "microGray / Hour"),
                    "label_vs_text_crosscheck": record.get("label_vs_text_crosscheck"),
                }
            )
        limit = max(1, min(int(limit), 500))
        return {
            "total_records": len(records),
            "matched_records": len(selected),
            "returned": min(len(selected), limit),
            "qc_placeholder_note": "qc_placeholder is a placeholder field, not a quality flag.",
            "items": selected[:limit],
        }

    def trends(self) -> Dict[str, Any]:
        return {
            "items": self._data("trends").get("trends", []),
            "note": "Fewer than five sols are present, so trend values are not computed.",
        }

    def radiation(self, sol: Optional[int] = None, include_observations: bool = False) -> Dict[str, Any]:
        summary = self.sol_summary(sol)
        payload: Dict[str, Any] = {
            "instrument": "RAD",
            "region_id": "gale_crater",
            "availability": "available",
            "observation_type": "historical_point_measurement",
            "sols": summary["sols"],
            "detectors": summary["detectors"],
            "unit": "microGray / Hour",
            "trends": self.trends()["items"],
            "location": {
                "name": "Curiosity rover, Gale Crater, Mars",
                "type": "rover_point",
                "note": "Single rover location; not a traverse radiation model.",
            },
            "coverage": {
                "type": "point",
                "spatial": "Curiosity rover location only",
                "temporal": "Historical sols 1-3",
                "sols": self.sols(),
                "live": False,
                "route_specific": False,
            },
            "provenance": "observed",
            "source": dict(RAD_SOURCE),
            "warnings": [
                "Historical rover measurements, not route-specific radiation predictions.",
                "qc_placeholder is not a quality flag and was not used for filtering.",
            ],
            "limitations": LIMITATIONS,
        }
        if include_observations:
            payload["observations"] = self.observations(sol=sol)
        return payload


_rad_service: Optional[RadService] = None
_lock = threading.Lock()


def get_rad_service() -> RadService:
    global _rad_service
    with _lock:
        if _rad_service is None:
            _rad_service = RadService()
        return _rad_service
