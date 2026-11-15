"""Route optimization, mission planning, return feasibility, reroute, report."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.core.exceptions import InvalidInputError, NotFoundError
from app.schemas.models import (
    MissionPlanRequest,
    MissionPlanResponse,
    MissionReturnRequest,
    ReportRequest,
    ReportResponse,
    RerouteRequest,
    RerouteResponse,
    ReturnFeasibilityResponse,
    RouteOptimizeRequest,
    RouteOptimizeResponse,
)
from app.services.mission_service import get_mission_service
from app.services.route_planner import REGION_ID, STRATEGY_WEIGHTS, get_route_planner

router = APIRouter(tags=["planning"])


@router.post("/route/optimize", response_model=RouteOptimizeResponse)
def route_optimize(payload: RouteOptimizeRequest):
    if payload.region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": payload.region_id})
    strategies: List[str] = []
    for strategy in payload.strategies or ["shortest", "safest_estimated", "balanced"]:
        if strategy not in STRATEGY_WEIGHTS:
            raise InvalidInputError(
                "Unknown route strategy",
                details={"strategy": strategy, "supported": sorted(STRATEGY_WEIGHTS)},
            )
        if strategy not in strategies:
            strategies.append(strategy)
    if not strategies:
        raise InvalidInputError("At least one route strategy is required")

    planner = get_route_planner()
    routes: List[Dict[str, Any]] = []
    failures: List[str] = []
    for strategy in strategies:
        try:
            routes.append(
                planner.plan(
                    start=(payload.start.x, payload.start.y),
                    destination=(payload.destination.x, payload.destination.y),
                    strategy=strategy,
                    max_difficulty=payload.max_difficulty,
                    speed_m_per_min=payload.travel_speed_m_per_min,
                    region_id=payload.region_id,
                )
            )
        except InvalidInputError as exc:
            failures.append(f"{strategy}: {exc.message}")
    if not routes:
        first = failures[0] if failures else "No traversable route exists for these coordinates."
        raise InvalidInputError("No route could be computed", details={"failures": failures or [first]})

    warnings = [f"{failure}" for failure in failures]
    if payload.risk_weight != 1.0:
        warnings.append(
            "risk_weight is not used by the fixed strategy cost model; use the strategy "
            "selection instead. The value was accepted for API compatibility."
        )
    return {
        "region_id": payload.region_id,
        "routes": routes,
        "algorithm": {
            "name": "A*",
            "version": "2.0",
            "cost_model": {
                "strategy_weights": STRATEGY_WEIGHTS,
                "class2_uncertainty_penalty": 0.35,
                "grid": "MOLA 463 m/px coverage grid",
            },
            "strategies_requested": strategies,
        },
        "warnings": warnings,
    }


@router.post("/route/reroute", response_model=RerouteResponse)
def route_reroute(payload: RerouteRequest):
    return get_mission_service().reroute(
        mission_id=payload.mission_id,
        original_route_id=payload.original_route_id,
        blocked_geometry=payload.blocked_geometry,
        scenario_status=payload.scenario_status,
        remaining_time_min=payload.remaining_time_min,
        strategy=payload.strategy,
        buffer_m=payload.buffer_m,
    )


@router.post("/mission/plan", response_model=MissionPlanResponse)
def mission_plan(payload: MissionPlanRequest):
    return get_mission_service().plan(payload.model_dump())


@router.post("/mission/return", response_model=ReturnFeasibilityResponse)
def mission_return(payload: MissionReturnRequest):
    return get_mission_service().return_feasibility(
        mission_id=payload.mission_id,
        current_location=payload.current_location.model_dump(),
        remaining_time_min=payload.remaining_time_min,
        reserve_time_min=payload.reserve_time_min,
    )


@router.post("/mission/report", response_model=ReportResponse)
def mission_report(payload: ReportRequest):
    report = get_mission_service().report(payload.mission_id, report_format=payload.format)
    return {
        "report_id": report["report_id"],
        "format": report["format"],
        "status": report["status"],
        "download_url": report["download_url"],
        "provenance": report["provenance"],
        "warnings": report["warnings"],
        "mission_id": payload.mission_id,
        "generated_at": report["generated_at"],
        "content": report,
    }
