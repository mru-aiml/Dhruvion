"""Mission planning, return feasibility, rerouting, and report assembly.

All calculations delegate to the deterministic route planner and the terrain
service. This module only combines their outputs into mission-level decisions;
it never invents terrain, route, or environmental values.
"""

from __future__ import annotations

import json
import math
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import InvalidInputError, NotFoundError, UnavailableError
from app.services.rad_service import get_rad_service
from app.services.rems_service import get_rems_service
from app.services.route_planner import (
    LIMITATIONS as ROUTE_LIMITATIONS,
    REGION_CRS,
    REGION_ID,
    RoutePlanner,
    get_route,
    get_route_planner,
    travel_speed,
)
from app.services.terrain_service import get_terrain_service

_MISSIONS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.RLock()

MISSION_LIMITATIONS = [
    *ROUTE_LIMITATIONS,
    "Time budget assumes a constant travel speed and the same path outbound and return.",
    "Environmental values are historical point measurements at the rover, not traverse conditions.",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_mission(mission_id: str) -> Dict[str, Any]:
    with _LOCK:
        mission = _MISSIONS.get(mission_id)
    if mission is None:
        raise NotFoundError(
            "Unknown mission. Plan a mission first so the backend has a start/base location.",
            details={"mission_id": mission_id},
        )
    return mission


def list_missions() -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_MISSIONS.values())


def _store_mission(mission: Dict[str, Any]) -> None:
    with _LOCK:
        _MISSIONS[mission["mission_id"]] = mission


def _start_end(payload: Dict[str, Any]) -> tuple:
    try:
        start = payload["start"]
        destination = payload["destination"]
        start_pair = (float(start["x"]), float(start["y"]))
        destination_pair = (float(destination["x"]), float(destination["y"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInputError("start and destination require numeric x (longitude) and y (latitude)") from exc
    return start_pair, destination_pair


def _feasibility(total: Optional[float], limit: float, route_status: str) -> tuple:
    if total is None:
        return "unverified", ["Time budget is unavailable because the route duration is unknown."]
    if total > limit:
        return "not_feasible", [f"Total time {total:.1f} min exceeds the {limit:.1f} min limit."]
    reasons = []
    status = "feasible"
    if total > limit * 0.9:
        status = "caution"
        reasons.append(f"Total time {total:.1f} min is within 10% of the {limit:.1f} min limit.")
    if route_status == "caution":
        status = "caution"
        reasons.append("The underlying route is marked caution (coverage class 2 or steep terrain).")
    if not reasons:
        reasons.append(f"Total time {total:.1f} min fits within the {limit:.1f} min limit.")
    return status, reasons


class MissionService:
    def __init__(self) -> None:
        self._planner: RoutePlanner = get_route_planner()
        self._terrain = get_terrain_service()

    # ------------------------------------------------------------------ plan
    def plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        region_id = payload.get("region_id", REGION_ID)
        start, destination = _start_end(payload)
        strategy = payload.get("route_strategy", "balanced")
        speed = travel_speed(payload.get("travel_speed_m_per_min"))
        route = self._planner.plan(
            start=start,
            destination=destination,
            strategy=strategy,
            speed_m_per_min=speed,
            region_id=region_id,
        )

        time_limit = float(payload.get("time_limit_min", 240.0))
        exploration = float(payload.get("exploration_time_min", 30.0))
        reserve = float(payload.get("reserve_time_min", 30.0))
        if time_limit <= 0:
            raise InvalidInputError("time_limit_min must be greater than zero")
        if exploration < 0 or reserve < 0:
            raise InvalidInputError("exploration_time_min and reserve_time_min must not be negative")

        outbound = route["estimated_duration_min"]
        return_min = outbound  # same traverse back
        total = None if outbound is None else round(outbound + exploration + return_min + reserve, 1)
        feasibility, reasons = _feasibility(total, time_limit, route["feasibility_status"])

        mission_id = payload.get("mission_id") or f"mission-{uuid.uuid4().hex[:10]}"
        route["mission_id"] = mission_id
        route["role"] = "outbound"

        time_budget = {
            "outbound_min": outbound,
            "exploration_min": exploration,
            "return_min": return_min,
            "reserve_min": reserve,
            "total_min": total,
            "limit_min": time_limit,
            "remaining_after_plan_min": None if total is None else round(time_limit - total, 1),
        }
        warnings = list(route.get("warnings", []))
        warnings.append("Time budget uses a constant planning speed, not rover-verified mobility.")
        if total is not None and total > time_limit:
            warnings.append("The plan exceeds the configured time limit; it is not executable as-is.")

        mission = {
            "mission_id": mission_id,
            "region_id": region_id,
            "name": payload.get("name") or "Mission plan",
            "start": route["start"],
            "destination": route["destination"],
            "route": route,
            "route_strategy": strategy,
            "travel_speed_m_per_min": speed,
            "time_budget": time_budget,
            "feasibility_status": feasibility,
            "reasons": reasons,
            "assumptions": route.get("assumptions", []),
            "warnings": warnings,
            "limitations": MISSION_LIMITATIONS,
            "classification": "DERIVED",
            "source": route.get("source"),
            "coverage": route.get("coverage"),
            "created_at": _now(),
        }
        _store_mission(mission)
        return {
            **mission,
            "route": route,
            "provenance": ["observed", "derived"],
        }

    # ---------------------------------------------------------------- return
    def return_feasibility(
        self,
        mission_id: str,
        current_location: Dict[str, Any],
        remaining_time_min: float,
        reserve_time_min: float = 20.0,
        speed_m_per_min: Optional[float] = None,
    ) -> Dict[str, Any]:
        mission = get_mission(mission_id)
        try:
            current = (float(current_location["x"]), float(current_location["y"]))
            base = (float(mission["start"]["x"]), float(mission["start"]["y"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidInputError("current_location requires numeric x (longitude) and y (latitude)") from exc

        speed = travel_speed(speed_m_per_min or mission.get("travel_speed_m_per_min"))
        route = self._planner.plan(
            start=current,
            destination=base,
            strategy="balanced",
            speed_m_per_min=speed,
            region_id=mission["region_id"],
        )
        route["mission_id"] = mission_id
        route["role"] = "return"
        duration = route["estimated_duration_min"]
        required = None if duration is None else round(duration + reserve_time_min, 1)

        if duration is None:
            feasibility = "unverified"
            reasons = ["Return duration is unknown."]
        elif required > remaining_time_min:
            feasibility = "not_feasible"
            reasons = [
                f"Return requires {required:.1f} min (including {reserve_time_min:g} min reserve) "
                f"but only {remaining_time_min:.1f} min remain."
            ]
        elif required > remaining_time_min * 0.9:
            feasibility = "caution"
            reasons = [f"Tight margin: {required:.1f} min required of {remaining_time_min:.1f} min remaining."]
        else:
            feasibility = "feasible"
            reasons = [f"Return fits within the remaining {remaining_time_min:.1f} min."]

        mission["return_route"] = route
        mission["last_return_evaluation"] = {
            "evaluated_at": _now(),
            "feasibility_status": feasibility,
            "remaining_time_min": remaining_time_min,
        }

        return {
            "mission_id": mission_id,
            "return_route": route,
            "estimated_return_min": duration,
            "required_time_min": required,
            "remaining_time_min": remaining_time_min,
            "reserve_time_min": reserve_time_min,
            "feasibility_status": feasibility,
            "reasons": reasons,
            "assumptions": route.get("assumptions", []),
            "warnings": [
                *route.get("warnings", []),
                "Base location is the mission's recorded start coordinate.",
            ],
            "limitations": MISSION_LIMITATIONS,
            "provenance": ["observed", "derived"],
            "classification": "DERIVED",
            "source": route.get("source"),
        }

    # --------------------------------------------------------------- reroute
    def reroute(
        self,
        mission_id: str,
        original_route_id: str,
        blocked_geometry: Dict[str, Any],
        scenario_status: str = "simulated",
        remaining_time_min: float = 120.0,
        strategy: str = "balanced",
        buffer_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        if scenario_status not in ("observed", "simulated"):
            raise InvalidInputError("scenario_status must be 'observed' or 'simulated'")
        mission = get_mission(mission_id)
        original = get_route(original_route_id)
        if original is None and mission.get("route", {}).get("id") == original_route_id:
            original = mission["route"]
        if original is None:
            raise NotFoundError(
                "Unknown original route for this mission",
                details={"mission_id": mission_id, "original_route_id": original_route_id},
            )

        traffic = self._planner.blocked_mask_from_geometry(blocked_geometry, buffer_m=buffer_m)
        start = (float(original["start"]["x"]), float(original["start"]["y"]))
        destination = (float(original["destination"]["x"]), float(original["destination"]["y"]))
        warnings = [
            "Emergency reroute is a planning simulation based on a user-supplied blockage geometry.",
            "The blockage is not an observed hazard unless scenario_status is 'observed'.",
        ]

        try:
            alternative = self._planner.plan(
                start=start,
                destination=destination,
                strategy=strategy,
                speed_m_per_min=mission.get("travel_speed_m_per_min"),
                blocked=traffic,
                region_id=mission["region_id"],
            )
        except InvalidInputError as exc:
            return {
                "mission_id": mission_id,
                "original_route_id": original_route_id,
                "alternative_route": {},
                "distance_delta_m": None,
                "duration_delta_min": None,
                "feasibility_status": "not_feasible",
                "scenario_status": scenario_status,
                "reason": "No traversable alternative exists around the supplied blockage.",
                "provenance": ["derived"],
                "warnings": [*warnings, str(exc)],
                "limitations": MISSION_LIMITATIONS,
                "classification": "DERIVED",
                "source": original.get("source"),
            }

        alternative["mission_id"] = mission_id
        alternative["role"] = "reroute"
        distance_delta = round(alternative["distance_m"] - original["distance_m"], 1)
        duration_delta = (
            round(alternative["estimated_duration_min"] - original["estimated_duration_min"], 1)
            if alternative["estimated_duration_min"] is not None
            and original["estimated_duration_min"] is not None
            else None
        )
        duration = alternative["estimated_duration_min"]
        if duration is not None and duration > remaining_time_min:
            feasibility = "not_feasible"
            reason = (
                f"Alternative route needs {duration:.1f} min but only {remaining_time_min:.1f} min remain."
            )
        elif duration is not None and duration > remaining_time_min * 0.9:
            feasibility = "caution"
            reason = "Alternative route fits but leaves less than a 10% time margin."
        else:
            feasibility = "feasible"
            reason = "Alternative route avoids the supplied blockage and fits the remaining time."
        if alternative["feasibility_status"] == "caution":
            feasibility = "caution" if feasibility == "feasible" else feasibility
            warnings.append("Alternative route crosses coverage class 2 or steep terrain.")

        mission["reroute"] = {
            "evaluated_at": _now(),
            "original_route_id": original_route_id,
            "alternative_route_id": alternative["id"],
            "scenario_status": scenario_status,
        }

        return {
            "mission_id": mission_id,
            "original_route_id": original_route_id,
            "alternative_route": alternative,
            "distance_delta_m": distance_delta,
            "duration_delta_min": duration_delta,
            "feasibility_status": feasibility,
            "scenario_status": scenario_status,
            "reason": reason,
            "provenance": ["derived"],
            "warnings": warnings,
            "limitations": MISSION_LIMITATIONS,
            "classification": "DERIVED",
            "source": alternative.get("source"),
        }

    # -------------------------------------------------------------- evaluate
    def evaluate(self, mission_id: str) -> Dict[str, Any]:
        mission = get_mission(mission_id)
        route = mission["route"]
        return {
            "mission_id": mission_id,
            "region_id": mission["region_id"],
            "feasibility_status": mission["feasibility_status"],
            "time_budget": mission["time_budget"],
            "route_summary": {
                "distance_m": route["distance_m"],
                "estimated_duration_min": route["estimated_duration_min"],
                "terrain_difficulty": route["terrain_difficulty"],
                "max_slope_deg": route.get("metrics", {}).get("max_slope_deg"),
                "hazard_count": route["hazard_count"],
                "coverage_class_counts": route.get("metrics", {}).get("coverage_class_counts"),
                "feasibility_status": route["feasibility_status"],
            },
            "reasons": mission["reasons"],
            "assumptions": mission["assumptions"],
            "warnings": mission["warnings"],
            "limitations": mission["limitations"],
            "provenance": ["observed", "derived"],
            "classification": "DERIVED",
            "source": mission.get("source"),
        }

    # ---------------------------------------------------------------- report
    def report(self, mission_id: Optional[str], report_format: str = "json") -> Dict[str, Any]:
        report_id = uuid.uuid4().hex
        mission = None
        warnings: List[str] = []
        if mission_id:
            mission = get_mission(mission_id)

        environment: Dict[str, Any] = {}
        radiation: Dict[str, Any] = {}
        try:
            if get_rems_service().available():
                environment = get_rems_service().environment()
        except UnavailableError as exc:
            warnings.append(f"REMS unavailable in report: {exc}")
        try:
            if get_rad_service().available():
                radiation = get_rad_service().radiation()
        except UnavailableError as exc:
            warnings.append(f"RAD unavailable in report: {exc}")

        terrain_summary = None
        try:
            terrain_summary = get_terrain_service().coverage_summary()
        except UnavailableError as exc:
            warnings.append(f"Terrain coverage unavailable in report: {exc}")

        content: Dict[str, Any] = {
            "report_id": report_id,
            "generated_at": _now(),
            "format": report_format,
            "status": "generated",
            "mission": mission,
            "terrain_coverage": terrain_summary,
            "environment": {
                "availability": environment.get("availability", "unavailable"),
                "sols": environment.get("sols"),
                "measurements": environment.get("measurements", {}),
                "wind": environment.get("wind", {}),
                "coverage": environment.get("coverage"),
                "warnings": environment.get("warnings", []),
                "limitations": environment.get("limitations", []),
                "source": environment.get("source"),
            },
            "radiation": {
                "availability": radiation.get("availability", "unavailable"),
                "sols": radiation.get("sols"),
                "detectors": radiation.get("detectors", {}),
                "unit": radiation.get("unit"),
                "coverage": radiation.get("coverage"),
                "warnings": radiation.get("warnings", []),
                "limitations": radiation.get("limitations", []),
                "source": radiation.get("source"),
            },
            "provenance": ["observed", "derived"],
            "warnings": [
                *warnings,
                "Report contains only data returned by backend services; simulated scenario data is excluded.",
            ],
            "limitations": [
                "This is a planning-phase report, not a certified mission plan.",
                "Historical REMS/RAD point measurements are not traverse conditions.",
            ],
        }

        settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = settings.REPORTS_DIR / f"{report_id}.json"
        path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
        content["download_url"] = f"/static/reports/{report_id}.json"
        content["report_path"] = path.name
        return content


_service: Optional[MissionService] = None
_lock = threading.Lock()


def get_mission_service() -> MissionService:
    global _service
    with _lock:
        if _service is None:
            _service = MissionService()
        return _service
