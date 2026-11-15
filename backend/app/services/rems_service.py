"""REMS environmental service for the supplied NASA package.

The package only contains two historical sols (9 and 11) of Curiosity REMS
MODRDR data. Everything returned here is a point observation or a statistic
derived from those observations at the rover location. It is never live,
forecast, or spatially distributed.

Rules implemented in this service:

- ``all_valid_values`` is the default statistics filter.
- Missing values stay missing (``None``); they are never converted to zero.
- Wind direction is summarised with circular statistics, and wind is reported
  as ``insufficient_data`` when the number of valid samples is too small.
- Trends are passed through as authored in the package; no trend is invented
  from two sols.
"""

from __future__ import annotations

import json
import math
import threading
from typing import Any, Dict, List, Optional

from app.core.exceptions import NotFoundError, UnavailableError
from app.core.logging_config import get_logger
from app.data_pipeline.dataset_paths import get_dataset_paths
from app.services.terrain_service import REMS_SOURCE

logger = get_logger(__name__)

DEFAULT_FILTER = "all_valid_values"
MIN_WIND_SAMPLES = 3

MEASUREMENT_LABELS = {
    "air_temperature": "Air temperature",
    "ground_temperature": "Ground brightness temperature",
    "pressure": "Pressure",
    "relative_humidity": "Relative humidity",
    "horizontal_wind_speed": "Horizontal wind speed",
    "wind_direction": "Wind direction",
    "uv_a": "UV-A irradiance",
    "uv_b": "UV-B irradiance",
    "uv_c": "UV-C irradiance",
    "uv_abc": "UV-ABC irradiance",
    "uv_d": "UV-D irradiance",
    "uv_e": "UV-E irradiance",
}

WIND_MEASUREMENTS = ("horizontal_wind_speed", "wind_direction")

LIMITATIONS = [
    "REMS values are historical measurements from the Curiosity rover at Gale Crater, "
    "not live telemetry, a forecast, or a spatially distributed field.",
    "Only sols 9 and 11 are present in the package; fewer than five sols means no trend is computed.",
    "Wind speed and direction have very few valid samples, so wind summaries are marked insufficient_data.",
    "Do not extrapolate these point values along a traverse or to another location.",
]


def _read_json(path) -> Any:
    if path is None or not path.exists():
        raise UnavailableError("REMS file unavailable", details={"file": getattr(path, "name", None)})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - corrupt handover file
        raise UnavailableError(f"Unable to read REMS file: {exc}") from exc


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class RemsService:
    """Read-only access to the REMS summary and observation files."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sol_summary: Optional[Dict[str, Any]] = None
        self._session_summary: Optional[Dict[str, Any]] = None
        self._observations: Optional[Dict[str, Any]] = None
        self._trends: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ files
    def _paths(self):
        paths = get_dataset_paths()
        if paths is None:
            raise UnavailableError(
                "NASA DHRUVION_DATA package not found. Set DHRUVION_DATA_DIR to the package root."
            )
        return paths

    def _data(self, key: str) -> Dict[str, Any]:
        with self._lock:
            if key == "sol" and self._sol_summary is not None:
                return self._sol_summary
            if key == "session" and self._session_summary is not None:
                return self._session_summary
            if key == "observations" and self._observations is not None:
                return self._observations
            if key == "trends" and self._trends is not None:
                return self._trends
            paths = self._paths()
            mapping = {
                "sol": paths.rems_sol_summary,
                "session": paths.rems_session_summary,
                "observations": paths.rems_observations,
                "trends": paths.rems_trends,
            }
            data = _read_json(mapping[key])
            if key == "sol":
                self._sol_summary = data
            elif key == "session":
                self._session_summary = data
            elif key == "observations":
                self._observations = data
            else:
                self._trends = data
            return data

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _sol_rows(sol: Optional[int] = None, filter_name: str = DEFAULT_FILTER) -> List[Dict[str, Any]]:
        data = get_rems_service()._data("sol")
        rows = data.get("rows", [])
        selected = [
            row
            for row in rows
            if row.get("filter") == filter_name and (sol is None or int(row.get("sol", -1)) == int(sol))
        ]
        return selected

    def sols(self) -> List[int]:
        rows = self._data("sol").get("rows", [])
        return sorted({int(row["sol"]) for row in rows if row.get("sol") is not None})

    def available(self) -> bool:
        try:
            paths = self._paths()
        except UnavailableError:
            return False
        required = ("rems_sol_summary", "rems_session_summary", "rems_observations", "rems_trends")
        return not paths.missing(*required)

    # ----------------------------------------------------------- sol summary
    def sol_summary(self, sol: Optional[int] = None) -> Dict[str, Any]:
        data = self._data("sol")
        rows = data.get("rows", [])
        unit_map = data.get("units", {})
        selected = [
            row
            for row in rows
            if row.get("filter") == DEFAULT_FILTER and (sol is None or int(row["sol"]) == int(sol))
        ]
        if sol is not None and not selected:
            raise NotFoundError("No REMS data for this sol", details={"sol": sol, "available_sols": self.sols()})

        by_sol: Dict[str, Dict[str, Any]] = {}
        for row in selected:
            sol_key = str(int(row["sol"]))
            measurement = row.get("measurement", "unknown")
            by_sol.setdefault(sol_key, {})[measurement] = {
                "measurement": measurement,
                "label": MEASUREMENT_LABELS.get(measurement, measurement),
                "quantity": row.get("quantity"),
                "unit": row.get("unit") or unit_map.get(measurement),
                "filter": DEFAULT_FILTER,
                "n_rows": row.get("n_rows"),
                "n_valid": row.get("n_valid"),
                "n_missing": row.get("n_missing"),
                "mean": _num(row.get("mean")),
                "min": _num(row.get("min")),
                "max": _num(row.get("max")),
                "median": _num(row.get("median")),
                "std": _num(row.get("std")),
            }

        return {
            "sols": sorted(int(value) for value in by_sol),
            "default_filter": DEFAULT_FILTER,
            "measurements": by_sol,
        }

    # ------------------------------------------------------- session summary
    def session_summary(self, sol: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
        data = self._data("session")
        rows = [
            row
            for row in data.get("rows", [])
            if row.get("filter") == DEFAULT_FILTER and (sol is None or int(row["sol"]) == int(sol))
        ]
        limit = max(1, min(int(limit), 500))
        sessions = []
        for row in rows[:limit]:
            sessions.append(
                {
                    "sol": row.get("sol"),
                    "session_id": row.get("session_id"),
                    "measurement": row.get("measurement"),
                    "label": MEASUREMENT_LABELS.get(row.get("measurement"), row.get("measurement")),
                    "unit": row.get("unit"),
                    "n_rows": row.get("n_rows"),
                    "n_valid": row.get("n_valid"),
                    "n_missing": row.get("n_missing"),
                    "mean": _num(row.get("mean")),
                    "min": _num(row.get("min")),
                    "max": _num(row.get("max")),
                }
            )
        return {"filter": DEFAULT_FILTER, "total_rows": len(rows), "returned": len(sessions), "items": sessions}

    # ------------------------------------------------------------ wind stats
    @staticmethod
    def _circular_stats(directions: List[float]) -> Optional[Dict[str, Any]]:
        if not directions:
            return None
        radians = [math.radians(value) for value in directions]
        sin_sum = sum(math.sin(value) for value in radians)
        cos_sum = sum(math.cos(value) for value in radians)
        count = len(radians)
        mean = math.degrees(math.atan2(sin_sum / count, cos_sum / count)) % 360.0
        resultant = math.hypot(sin_sum / count, cos_sum / count)
        return {
            "circular_mean_deg": round(mean, 2),
            "resultant_length": round(resultant, 3),
            "n_directions": count,
        }

    def wind(self, sol: Optional[int] = None) -> Dict[str, Any]:
        data = self._data("observations")
        records = [
            record
            for record in data.get("records", [])
            if sol is None or int(record.get("sol", -1)) == int(sol)
        ]
        speeds = [
            _num(record.get("HORIZONTAL_WIND_SPEED"))
            for record in records
            if _num(record.get("HORIZONTAL_WIND_SPEED")) is not None
        ]
        directions = [
            _num(record.get("WIND_DIRECTION"))
            for record in records
            if _num(record.get("WIND_DIRECTION")) is not None
        ]
        direction_values = [value for value in directions if value is not None]
        circular = self._circular_stats(direction_values)

        def block(values: List[float], unit: str) -> Dict[str, Any]:
            if not values:
                return {
                    "availability": "unavailable",
                    "n_valid": 0,
                    "unit": unit,
                    "warnings": ["No valid wind samples in the supplied sols."],
                }
            summary = {
                "availability": "insufficient_data" if len(values) < MIN_WIND_SAMPLES else "available",
                "n_valid": len(values),
                "unit": unit,
                "mean": round(sum(values) / len(values), 3),
                "min": round(min(values), 3),
                "max": round(max(values), 3),
            }
            if len(values) < MIN_WIND_SAMPLES:
                summary["warnings"] = [
                    f"Only {len(values)} valid sample(s); wind requires at least {MIN_WIND_SAMPLES} "
                    "for a meaningful summary and is reported as insufficient_data."
                ]
            return summary

        return {
            "sol": sol,
            "speed": block(speeds, "m/s"),
            "direction": {**block(direction_values, "degree"), "circular": circular},
            "provenance": "observed",
            "note": "Circular statistics are used for direction. Scattered directions yield a low resultant length.",
        }

    # -------------------------------------------------------------- trends
    def trends(self, measurement: Optional[str] = None) -> Dict[str, Any]:
        data = self._data("trends")
        trends = data.get("trends", [])
        if measurement:
            trends = [trend for trend in trends if trend.get("measurement") == measurement]
        return {
            "items": trends,
            "note": "The package contains fewer than five sols, so trend values are not computed.",
        }

    # ---------------------------------------------------- observations subset
    def observations(
        self,
        sol: Optional[int] = None,
        measurement: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        data = self._data("observations")
        records = data.get("records", [])
        selected = []
        for record in records:
            if sol is not None and int(record.get("sol", -1)) != int(sol):
                continue
            if measurement:
                field = {
                    "air_temperature": "AMBIENT_TEMP",
                    "ground_temperature": "BRIGHTNESS_TEMP",
                    "pressure": "PRESSURE",
                    "horizontal_wind_speed": "HORIZONTAL_WIND_SPEED",
                    "wind_direction": "WIND_DIRECTION",
                    "relative_humidity": "LOCAL_RELATIVE_HUMIDITY",
                }.get(measurement, measurement)
                selected.append(
                    {
                        "sol": record.get("sol"),
                        "session_id": record.get("session_id"),
                        "LMST": record.get("LMST"),
                        "value": _num(record.get(field)),
                        "field": field,
                        "unit": data.get("units", {}).get(measurement),
                    }
                )
            else:
                selected.append(record)
        limit = max(1, min(int(limit), 500))
        return {
            "total_records": len(records),
            "matched_records": len(selected),
            "returned": min(len(selected), limit),
            "unit_note": "Units follow the PDS labels; see the package unit map.",
            "items": selected[:limit],
        }

    # ------------------------------------------------------------------ API
    def environment(self, sol: Optional[int] = None, include_observations: bool = False) -> Dict[str, Any]:
        sols = self.sols()
        if sol is not None and int(sol) not in sols:
            raise NotFoundError("No REMS data for this sol", details={"sol": sol, "available_sols": sols})
        summary = self.sol_summary(sol)

        wind = {}
        for wind_sol in ([int(sol)] if sol is not None else sols):
            wind[str(wind_sol)] = self.wind(wind_sol)

        payload: Dict[str, Any] = {
            "instrument": "REMS",
            "region_id": "gale_crater",
            "availability": "available",
            "observation_type": "historical_point_measurement",
            "sols": [int(sol)] if sol is not None else sols,
            "default_filter": DEFAULT_FILTER,
            "location": {
                "name": "Curiosity rover, Gale Crater, Mars",
                "type": "rover_point",
                "note": "Single rover location; not spatially distributed.",
            },
            "units": self._data("sol").get("units", {}),
            "measurements": summary["measurements"],
            "wind": wind,
            "trends": self.trends()["items"],
            "coverage": {
                "type": "point",
                "spatial": "Curiosity rover location only",
                "temporal": "Historical sols 9 and 11",
                "sols": sols,
                "live": False,
                "forecast": False,
                "spatially_distributed": False,
            },
            "provenance": "observed + derived statistics",
            "source": dict(REMS_SOURCE),
            "warnings": [
                "Historical rover measurements, not live or forecast conditions.",
                "Wind samples are sparse; see the per-sol availability flags.",
            ],
            "limitations": LIMITATIONS,
        }
        if include_observations:
            payload["observations"] = self.observations(sol=sol, limit=100)
        return payload


_rems_service: Optional[RemsService] = None
_lock = threading.Lock()


def get_rems_service() -> RemsService:
    global _rems_service
    with _lock:
        if _rems_service is None:
            _rems_service = RemsService()
        return _rems_service
