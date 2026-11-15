"""Derived hazard classification from the MOLA slope/roughness layers.

Hazards here are *derived* indicators at the ~463 m DEM baseline. They are not
observed rover-scale obstacles, and class-2 cells (elevation only) are reported
as unknown derivatives rather than safe terrain.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List

import numpy as np

from app.core.exceptions import UnavailableError
from app.services.terrain_service import get_terrain_service

HAZARD_THRESHOLDS = {
    "slope_moderate_deg": 15.0,
    "slope_high_deg": 25.0,
    "roughness_moderate_m": 120.0,
    "roughness_high_m": 250.0,
}

LIMITATIONS = [
    "Hazard classes are derived from MOLA slope and TRI roughness at ~463 m/px; "
    "they are regional indicators, not rover-scale obstacle maps.",
    "Coverage class 2 cells have no slope/roughness and are reported as unknown, never safe.",
    "An empty hazard class does not prove the terrain is safe.",
]


def _classify(slope: Any, roughness: Any) -> Dict[str, Any]:
    if slope is None or roughness is None:
        return {"class": "unknown", "reason": "slope/roughness unavailable (coverage class 2)"}
    slope = float(slope)
    roughness = float(roughness)
    if slope >= HAZARD_THRESHOLDS["slope_high_deg"] or roughness >= HAZARD_THRESHOLDS["roughness_high_m"]:
        return {"class": "high", "reason": "steep slope or high roughness at the DEM baseline"}
    if slope >= HAZARD_THRESHOLDS["slope_moderate_deg"] or roughness >= HAZARD_THRESHOLDS["roughness_moderate_m"]:
        return {"class": "moderate", "reason": "moderate slope or roughness at the DEM baseline"}
    return {"class": "low", "reason": "below moderate thresholds at the DEM baseline"}


class HazardService:
    def __init__(self) -> None:
        self._terrain = get_terrain_service()
        self._lock = threading.RLock()
        self._summary: Dict[str, Any] = {}

    def point(self, lon: float, lat: float) -> Dict[str, Any]:
        terrain = self._terrain.point(lon, lat)
        slope = terrain["values"]["slope_deg"]
        roughness = terrain["values"]["roughness"]
        classification = _classify(slope, roughness)
        return {
            "region_id": "gale_crater",
            "coordinate": terrain["coordinate"],
            "hazard_class": classification["class"],
            "reason": classification["reason"],
            "values": {"slope_deg": slope, "roughness": roughness},
            "units": terrain["units"],
            "coverage": terrain["coverage"],
            "availability": "partial" if classification["class"] == "unknown" else "available",
            "provenance": "derived",
            "source": terrain["source"],
            "warnings": terrain["warnings"],
            "limitations": [*LIMITATIONS, *terrain["limitations"]],
            "thresholds": HAZARD_THRESHOLDS,
        }

    def summary(self, max_features: int = 400) -> Dict[str, Any]:
        with self._lock:
            if self._summary:
                return self._summary
            grid = self._terrain.grid()
            slope = grid["slope"]
            roughness = grid["roughness"]
            coverage = grid["coverage"]
            classes = {"low": 0, "moderate": 0, "high": 0, "unknown": 0}
            valid = coverage == 1
            high = valid & (
                (slope >= HAZARD_THRESHOLDS["slope_high_deg"])
                | (roughness >= HAZARD_THRESHOLDS["roughness_high_m"])
            )
            moderate = valid & ~high & (
                (slope >= HAZARD_THRESHOLDS["slope_moderate_deg"])
                | (roughness >= HAZARD_THRESHOLDS["roughness_moderate_m"])
            )
            low = valid & ~high & ~moderate
            unknown = coverage != 1
            classes["high"] = int(np.count_nonzero(high))
            classes["moderate"] = int(np.count_nonzero(moderate))
            classes["low"] = int(np.count_nonzero(low))
            classes["unknown"] = int(np.count_nonzero(unknown))

            rows, cols = np.where(high)
            features: List[Dict[str, Any]] = []
            step = max(1, len(rows) // max_features) if len(rows) else 1
            for index in range(0, len(rows), step):
                row, col = int(rows[index]), int(cols[index])
                lon, lat = self._terrain.latlon_for_pixel(row, col)
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                        "properties": {
                            "hazard_class": "high",
                            "slope_deg": round(float(slope[row, col]), 2),
                            "roughness_m": round(float(roughness[row, col]), 2),
                            "row": row,
                            "col": col,
                        },
                    }
                )
                if len(features) >= max_features:
                    break

            self._summary = {
                "region_id": "gale_crater",
                "features": {"type": "FeatureCollection", "features": features},
                "summary": {
                    "total_cells": int(coverage.size),
                    "class_counts": classes,
                    "identified_high_hazard_cells": classes["high"],
                    "unknown_derivative_cells": classes["unknown"],
                    "unknown_coverage": classes["unknown"] > 0,
                    "feature_sample_note": "High-hazard cells are sampled as point features for display; counts cover the full grid.",
                },
                "thresholds": HAZARD_THRESHOLDS,
                "provenance": ["derived"],
                "availability": "available",
                "source": self._terrain.source(),
                "warnings": [
                    "Hazard classes are derived at the ~463 m baseline and are not rover-scale obstacles.",
                    "Unknown cells remain unknown and must not be interpreted as safe.",
                ],
                "limitations": LIMITATIONS,
            }
            return self._summary


_service: HazardService | None = None
_lock = threading.Lock()


def get_hazard_service() -> HazardService:
    global _service
    with _lock:
        if _service is None:
            _service = HazardService()
        return _service
