"""Deterministic A* route planning on the real MOLA coverage grid.

The planner works directly on the 410x410 terrain package grid:

- Coverage class 0 and NaN elevation cells are impassable.
- Coverage class 2 cells are traversable only with an explicit uncertainty
  penalty; their slope/roughness are NaN and are never treated as zero.
- Distances use the raster ground spacing, not a spherical shortcut.
- Unknown cells never become zero-cost.
- The default travel speed is a planning assumption, not rover telemetry.

Every numeric value returned here is computed by this module from the
package rasters. No value is invented to fill a gap.
"""

from __future__ import annotations

import heapq
import math
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.core.config import settings
from app.core.exceptions import InvalidInputError, NotFoundError, UnavailableError
from app.services.terrain_service import get_terrain_service

REGION_ID = "gale_crater"
REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"

STRATEGY_WEIGHTS = {
    "shortest": 0.0,
    "balanced": 1.0,
    "safest_estimated": 3.0,
}
CLASS2_UNCERTAINTY_PENALTY = 0.35
HAZARD_SLOPE_DEG = 15.0
CAUTION_SLOPE_DEG = 20.0

LIMITATIONS = [
    "Routes are planned on the ~463 m MOLA grid; this is a regional traverse model, "
    "not rover-scale trafficability.",
    "Coverage class 2 cells have no valid slope/roughness and are crossed only with an "
    "explicit uncertainty penalty, never as zero risk.",
    "Travel speed is a configurable planning assumption, not measured rover performance.",
]

ASSUMPTIONS = [
    "Travel speed is a planning assumption supplied by the mission configuration.",
    "Outbound and return traverse the same route unless an alternative is computed.",
    "Terrain cost uses MOLA-derived slope and TRI roughness at the DEM pixel baseline.",
]

_ROUTE_STORE: Dict[str, Dict[str, Any]] = {}
_STORE_LOCK = threading.RLock()


def _store_route(record: Dict[str, Any]) -> None:
    with _STORE_LOCK:
        _ROUTE_STORE[record["id"]] = record


def get_route(route_id: str) -> Optional[Dict[str, Any]]:
    with _STORE_LOCK:
        return _ROUTE_STORE.get(route_id)


def all_routes() -> List[Dict[str, Any]]:
    with _STORE_LOCK:
        return list(_ROUTE_STORE.values())


def travel_speed(value: Optional[float]) -> float:
    speed = value if value is not None else settings.DEFAULT_TRAVEL_SPEED_M_PER_MIN
    if not math.isfinite(speed) or speed <= 0:
        raise InvalidInputError("travel_speed_m_per_min must be a positive number")
    return float(speed)


class RoutePlanner:
    """Coverage-aware A* planner bound to the immutable terrain grid."""

    def __init__(self) -> None:
        self._terrain = get_terrain_service()

    # --------------------------------------------------------------- helpers
    def _grid(self) -> Dict[str, Any]:
        try:
            return self._terrain.grid()
        except UnavailableError:
            raise

    def _pixel(self, lon: float, lat: float, grid: Dict[str, Any], label: str) -> Tuple[int, int]:
        located = self._terrain.pixel_for_latlon(lon, lat)
        if located is None:
            raise InvalidInputError(
                f"{label} coordinate is outside the MOLA coverage.",
                details={
                    "coordinate": {"x": lon, "y": lat},
                    "bounds_latlon": self._terrain.bounds_latlon(),
                },
            )
        row, col = located
        if not self._terrain.is_usable(row, col):
            raise InvalidInputError(
                f"{label} coordinate has no usable elevation (coverage class 0).",
                details={"coordinate": {"x": lon, "y": lat}, "row": row, "col": col},
            )
        return row, col

    @staticmethod
    def _cell_risk(
        coverage_class: int,
        slope: float,
        roughness: float,
        max_difficulty: Optional[float],
    ) -> Tuple[float, bool]:
        """Return ``(risk, blocked)`` for a class-1 cell."""
        if coverage_class == 2:
            return CLASS2_UNCERTAINTY_PENALTY, False
        if coverage_class != 1:
            return 0.0, True
        if not math.isfinite(slope):
            return CLASS2_UNCERTAINTY_PENALTY, False
        if max_difficulty is not None and slope > float(max_difficulty):
            return 0.0, True
        slope_risk = min(max(slope / 30.0, 0.0), 1.5)
        rough_risk = min(max(roughness / 150.0, 0.0), 1.0) if math.isfinite(roughness) else 0.0
        return 0.6 * slope_risk + 0.4 * rough_risk, False

    # ---------------------------------------------------------------- search
    def _astar(
        self,
        grid: Dict[str, Any],
        start: Tuple[int, int],
        goal: Tuple[int, int],
        strategy: str,
        max_difficulty: Optional[float],
        blocked: Optional[np.ndarray],
    ) -> Optional[List[Tuple[int, int]]]:
        elevation = grid["elevation"]
        slope = grid["slope"]
        roughness = grid["roughness"]
        coverage = grid["coverage"]
        height, width = grid["height"], grid["width"]
        res_x, res_y = grid["resolution_x_m"], grid["resolution_y_m"]
        lam = STRATEGY_WEIGHTS.get(strategy, 1.0)

        sr, sc = start
        gr, gc = goal
        if blocked is not None and (blocked[sr, sc] or blocked[gr, gc]):
            return None

        size = height * width
        g_score = np.full(size, np.inf, dtype=np.float64)
        came = np.full(size, -1, dtype=np.int64)
        start_idx = sr * width + sc
        goal_idx = gr * width + gc
        g_score[start_idx] = 0.0

        heuristic = lambda r, c: math.hypot((r - gr) * res_y, (c - gc) * res_x)
        open_heap: List[Tuple[float, int]] = [(heuristic(sr, sc), start_idx)]
        closed = np.zeros(size, dtype=bool)
        neighbours = (
            (-1, -1, math.hypot(res_y, res_x)),
            (-1, 0, res_y),
            (-1, 1, math.hypot(res_y, res_x)),
            (0, -1, res_x),
            (0, 1, res_x),
            (1, -1, math.hypot(res_y, res_x)),
            (1, 0, res_y),
            (1, 1, math.hypot(res_y, res_x)),
        )
        iterations = 0

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if closed[current]:
                continue
            closed[current] = True
            if current == goal_idx:
                path: List[Tuple[int, int]] = []
                node = current
                while node != -1:
                    path.append((node // width, node % width))
                    node = came[node]
                path.reverse()
                return path

            r, c = divmod(current, width)
            iterations += 1
            if iterations > 2_000_000:  # pragma: no cover - defensive guard
                return None

            for dr, dc, step in neighbours:
                nr, nc = r + dr, c + dc
                if nr < 0 or nr >= height or nc < 0 or nc >= width:
                    continue
                idx = nr * width + nc
                if closed[idx]:
                    continue
                if blocked is not None and blocked[nr, nc]:
                    continue
                coverage_class = int(coverage[nr, nc])
                if coverage_class not in (1, 2):
                    continue
                elevation_value = elevation[nr, nc]
                if not np.isfinite(elevation_value):
                    continue
                risk, cell_blocked = self._cell_risk(
                    coverage_class,
                    float(slope[nr, nc]) if np.isfinite(slope[nr, nc]) else float("nan"),
                    float(roughness[nr, nc]) if np.isfinite(roughness[nr, nc]) else float("nan"),
                    max_difficulty,
                )
                if cell_blocked:
                    continue
                edge = step * (1.0 + lam * risk)
                tentative = g_score[current] + edge
                if tentative < g_score[idx]:
                    g_score[idx] = tentative
                    came[idx] = current
                    heapq.heappush(open_heap, (tentative + heuristic(nr, nc), idx))
        return None

    # --------------------------------------------------------------- metrics
    def _metrics(
        self,
        grid: Dict[str, Any],
        path: Sequence[Tuple[int, int]],
        speed: float,
    ) -> Dict[str, Any]:
        elevation = grid["elevation"]
        slope = grid["slope"]
        roughness = grid["roughness"]
        coverage = grid["coverage"]
        res_x, res_y = grid["resolution_x_m"], grid["resolution_y_m"]

        distance = 0.0
        gain = 0.0
        loss = 0.0
        previous: Optional[Tuple[int, int]] = None
        slopes: List[float] = []
        roughness_values: List[float] = []
        classes: Dict[str, int] = {"0": 0, "1": 0, "2": 0, "other": 0}
        elevations: List[float] = []
        hazard_cells = 0

        for r, c in path:
            cls = int(coverage[r, c])
            key = str(cls) if cls in (0, 1, 2) else "other"
            classes[key] += 1
            value = float(elevation[r, c])
            if np.isfinite(value):
                elevations.append(value)
                if previous is not None:
                    previous_value = float(elevation[previous[0], previous[1]])
                    if np.isfinite(previous_value):
                        delta = value - previous_value
                        if delta > 0:
                            gain += delta
                        else:
                            loss -= delta
            if cls == 1:
                slope_value = float(slope[r, c])
                if np.isfinite(slope_value):
                    slopes.append(slope_value)
                    if slope_value > HAZARD_SLOPE_DEG:
                        hazard_cells += 1
                rough_value = float(roughness[r, c])
                if np.isfinite(rough_value):
                    roughness_values.append(rough_value)
            if previous is not None:
                pr, pc = previous
                distance += math.hypot((r - pr) * res_y, (c - pc) * res_x)
            previous = (r, c)

        max_slope = max(slopes) if slopes else None
        mean_slope = sum(slopes) / len(slopes) if slopes else None
        mean_roughness = (
            sum(roughness_values) / len(roughness_values) if roughness_values else None
        )
        unknown_cells = classes["2"] + classes["0"] + classes["other"]
        duration = distance / speed if speed > 0 else None

        if max_slope is None:
            difficulty = None
        else:
            difficulty = round(0.7 * mean_slope + 0.3 * max_slope, 2)

        feasibility = "feasible"
        if unknown_cells:
            feasibility = "caution"
        elif max_slope is not None and max_slope > CAUTION_SLOPE_DEG:
            feasibility = "caution"

        return {
            "distance_m": round(distance, 1),
            "estimated_duration_min": round(duration, 1) if duration is not None else None,
            "terrain_difficulty": difficulty,
            "hazard_count": hazard_cells,
            "mean_slope_deg": round(mean_slope, 2) if mean_slope is not None else None,
            "max_slope_deg": round(max_slope, 2) if max_slope is not None else None,
            "mean_roughness_m": round(mean_roughness, 2) if mean_roughness is not None else None,
            "elevation_min_m": round(min(elevations), 1) if elevations else None,
            "elevation_max_m": round(max(elevations), 1) if elevations else None,
            "elevation_gain_m": round(gain, 1),
            "elevation_loss_m": round(loss, 1),
            "coverage_class_counts": classes,
            "unknown_derivative_cells": unknown_cells,
            "valid_derivative_cells": classes["1"],
            "cell_count": len(path),
            "feasibility_status": feasibility,
        }

    def _geometry(self, grid: Dict[str, Any], path: Sequence[Tuple[int, int]], max_points: int = 160) -> List[List[float]]:
        stride = max(1, len(path) // max_points)
        sampled = list(path[::stride])
        if sampled[-1] != path[-1]:
            sampled.append(path[-1])
        coordinates = []
        for r, c in sampled:
            lon, lat = self._terrain.latlon_for_pixel(r, c)
            coordinates.append([round(lon, 6), round(lat, 6)])
        return coordinates

    # ----------------------------------------------------------------- public
    def plan(
        self,
        start: Tuple[float, float],
        destination: Tuple[float, float],
        strategy: str = "balanced",
        max_difficulty: Optional[float] = None,
        speed_m_per_min: Optional[float] = None,
        blocked: Optional[np.ndarray] = None,
        region_id: str = REGION_ID,
    ) -> Dict[str, Any]:
        if region_id != REGION_ID:
            raise NotFoundError("Unknown region", details={"region_id": region_id})
        if strategy not in STRATEGY_WEIGHTS:
            raise InvalidInputError(
                "Unknown route strategy",
                details={"strategy": strategy, "supported": sorted(STRATEGY_WEIGHTS)},
            )

        grid = self._grid()
        speed = travel_speed(speed_m_per_min)
        start_lon, start_lat = start
        dest_lon, dest_lat = destination
        start_rc = self._pixel(start_lon, start_lat, grid, "Start")
        goal_rc = self._pixel(dest_lon, dest_lat, grid, "Destination")

        path = self._astar(grid, start_rc, goal_rc, strategy, max_difficulty, blocked)
        if path is None:
            raise InvalidInputError(
                "No traversable route exists for these coordinates and constraints.",
                details={
                    "start": {"x": start_lon, "y": start_lat},
                    "destination": {"x": dest_lon, "y": dest_lat},
                    "strategy": strategy,
                    "max_difficulty": max_difficulty,
                    "coverage_classes": {
                        "0": "impassable",
                        "1": "valid derivatives",
                        "2": "elevation only, uncertainty penalty",
                    },
                },
            )

        metrics = self._metrics(grid, path, speed)
        route_id = f"route-{strategy}-{uuid.uuid4().hex[:8]}"
        coverage_block = {
            "start": self._terrain.coverage_at(start_lon, start_lat)["coverage"],
            "destination": self._terrain.coverage_at(dest_lon, dest_lat)["coverage"],
            "route_counts": metrics["coverage_class_counts"],
        }
        warnings = ["Route computed from MOLA elevation/slope/roughness (OBSERVED + DERIVED)."]
        if metrics["unknown_derivative_cells"]:
            warnings.append(
                f"{metrics['unknown_derivative_cells']} route cells have no slope/roughness (coverage class 2); "
                "they were traversed with an uncertainty penalty, not as zero risk."
            )
        if metrics["feasibility_status"] == "caution":
            warnings.append(
                "Terrain caution: the route either crosses coverage class 2 cells or exceeds "
                f"{CAUTION_SLOPE_DEG:g}° slope at the 463 m baseline."
            )

        rationale = {
            "shortest": "Minimises ground distance with no terrain-risk weighting; class 2 cells still carry an uncertainty penalty.",
            "balanced": "Trade-off between ground distance and MOLA-derived slope/roughness risk.",
            "safest_estimated": "Strongly penalises slope and roughness; estimated terrain risk, not a certified safe route.",
        }[strategy]

        route = {
            "id": route_id,
            "strategy": strategy,
            "geometry": {"type": "LineString", "coordinates": self._geometry(grid, path)},
            "distance_m": metrics["distance_m"],
            "estimated_duration_min": metrics["estimated_duration_min"],
            "terrain_difficulty": metrics["terrain_difficulty"],
            "hazard_count": metrics["hazard_count"],
            "feasibility_status": metrics["feasibility_status"],
            "rationale": rationale,
            "provenance": ["observed", "derived"],
            "warnings": warnings,
            "start": {"x": start_lon, "y": start_lat, "crs": REGION_CRS},
            "destination": {"x": dest_lon, "y": dest_lat, "crs": REGION_CRS},
            "metrics": metrics,
            "coverage": coverage_block,
            "assumptions": [
                *ASSUMPTIONS,
                f"Travel speed {speed:g} m/min (planning assumption, not rover-verified).",
            ],
            "limitations": LIMITATIONS,
            "units": {
                "distance_m": "m",
                "estimated_duration_min": "min",
                "terrain_difficulty": "index",
                "slope": "degree",
                "roughness": "m (TRI, Riley 1999)",
                "elevation": "m",
            },
            "source": self._terrain.source(),
            "classification": "DERIVED",
            "algorithm": {
                "name": "A*",
                "version": "2.0",
                "heuristic": "Euclidean ground distance in metres",
                "strategy_weights": STRATEGY_WEIGHTS,
                "class2_uncertainty_penalty": CLASS2_UNCERTAINTY_PENALTY,
                "max_difficulty_deg": max_difficulty,
                "travel_speed_m_per_min": speed,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "region_id": REGION_ID,
            "pixel_start": [int(start_rc[0]), int(start_rc[1])],
            "pixel_goal": [int(goal_rc[0]), int(goal_rc[1])],
        }
        _store_route(route)
        return route

    def compare(
        self,
        start: Tuple[float, float],
        destination: Tuple[float, float],
        strategies: Sequence[str],
        max_difficulty: Optional[float] = None,
        speed_m_per_min: Optional[float] = None,
        region_id: str = REGION_ID,
    ) -> List[Dict[str, Any]]:
        routes: List[Dict[str, Any]] = []
        for strategy in strategies:
            routes.append(
                self.plan(
                    start=start,
                    destination=destination,
                    strategy=strategy,
                    max_difficulty=max_difficulty,
                    speed_m_per_min=speed_m_per_min,
                    region_id=region_id,
                )
            )
        return routes

    # ------------------------------------------------------------- rerouting
    def blocked_mask_from_geometry(
        self,
        geometry: Dict[str, Any],
        buffer_m: Optional[float] = None,
    ) -> np.ndarray:
        grid = self._grid()
        height, width = grid["height"], grid["width"]
        res = max(grid["resolution_x_m"], grid["resolution_y_m"])
        radius_cells = max(1, int(math.ceil((buffer_m or 2.0 * res) / res)))
        mask = np.zeros((height, width), dtype=bool)

        coordinates: List[Sequence[float]] = []
        geom_type = str(geometry.get("type", "")).lower()
        raw = geometry.get("coordinates")
        if geom_type == "point" and isinstance(raw, (list, tuple)) and len(raw) >= 2:
            coordinates = [raw]
        elif geom_type == "linestring" and isinstance(raw, (list, tuple)):
            coordinates = list(raw)
        elif geom_type == "polygon" and isinstance(raw, (list, tuple)) and raw:
            ring = raw[0] if isinstance(raw[0], (list, tuple)) else raw
            coordinates = list(ring)
        else:
            raise InvalidInputError(
                "blocked_geometry must be a GeoJSON Point, LineString, or Polygon",
                details={"type": geometry.get("type")},
            )

        if not coordinates:
            raise InvalidInputError("blocked_geometry contains no coordinates")

        def mark(row: int, col: int) -> None:
            r0, r1 = max(0, row - radius_cells), min(height, row + radius_cells + 1)
            c0, c1 = max(0, col - radius_cells), min(width, col + radius_cells + 1)
            mask[r0:r1, c0:c1] = True

        points: List[Tuple[int, int]] = []
        for coordinate in coordinates:
            if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 2:
                continue
            row, col = self._terrain.pixel_for_latlon(float(coordinate[0]), float(coordinate[1])) or (-1, -1)
            if row < 0:
                continue
            points.append((row, col))
        if not points:
            raise InvalidInputError("blocked_geometry falls outside the terrain grid")

        if geom_type == "polygon":
            rows = [p[0] for p in points]
            cols = [p[1] for p in points]
            for row in range(max(0, min(rows) - radius_cells), min(height, max(rows) + radius_cells + 1)):
                for col in range(max(0, min(cols) - radius_cells), min(width, max(cols) + radius_cells + 1)):
                    mask[row, col] = True
        else:
            for row, col in points:
                mark(row, col)
            for first, second in zip(points, points[1:]):
                steps = max(abs(second[0] - first[0]), abs(second[1] - first[1]))
                for index in range(1, steps):
                    row = round(first[0] + (second[0] - first[0]) * index / steps)
                    col = round(first[1] + (second[1] - first[1]) * index / steps)
                    mark(row, col)
        if mask.all():  # pragma: no cover - defensive
            raise InvalidInputError("blocked_geometry blocks the entire terrain grid")
        return mask


_planner: Optional[RoutePlanner] = None
_lock = threading.Lock()


def get_route_planner() -> RoutePlanner:
    global _planner
    with _lock:
        if _planner is None:
            _planner = RoutePlanner()
        return _planner
