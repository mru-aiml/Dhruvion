"""Allowlisted mission-assistant tools.

Every tool in this module is a thin, read-only adapter over an existing backend
service. There is no shell, SQL, filesystem, or unrestricted URL tool, and no
tool invents values: if a service reports ``unavailable`` the tool returns that
state unchanged. The language model can only explain the evidence produced here.

Tool names are fixed by the DHRUVION contract:

- get_terrain_at_coordinate
- get_terrain_profile
- get_coverage_status
- get_rems_summary
- get_radiation_summary
- calculate_route
- compare_routes
- evaluate_mission
- evaluate_return_feasibility
- generate_mission_report
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.exceptions import ApiError
from app.core.logging_config import get_logger
from app.services.mission_service import get_mission_service
from app.services.rad_service import get_rad_service
from app.services.rems_service import get_rems_service
from app.services.route_planner import get_route_planner
from app.services.terrain_service import REGION_ID, get_terrain_service

logger = get_logger(__name__)

DEFAULT_REGION = REGION_ID


@dataclass
class ToolOutcome:
    tool: str
    status: str = "completed"
    data: Any = None
    observations: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    coverage: Any = None
    provenance: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any], Dict[str, Any]], ToolOutcome]


# --------------------------------------------------------------------- helpers
def _obs(
    tool: str,
    label: str,
    value: Any,
    unit: Optional[str] = None,
    provenance: Optional[str] = None,
    coverage: Optional[str] = None,
    source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "tool": tool,
        "label": label,
        "value": value,
        "unit": unit,
        "provenance": provenance,
        "coverage": coverage,
        "source": (source or {}).get("name") if isinstance(source, dict) else None,
    }


def _source_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    source = payload.get("source")
    if isinstance(source, dict) and source:
        return [dict(source)]
    return []


def _coverage_text(payload: Dict[str, Any]) -> Optional[str]:
    coverage = payload.get("coverage")
    if isinstance(coverage, dict):
        for key in ("label", "type", "spatial", "temporal"):
            if coverage.get(key):
                return str(coverage[key])
        if coverage.get("class") is not None:
            return f"coverage class {coverage.get('class')}"
    return None


def _number(args: Dict[str, Any], key: str) -> float:
    value = args.get(key)
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{key} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number") from exc


def _region(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return str(args.get("region_id") or context.get("region_id") or DEFAULT_REGION)


def _mission_id(args: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
    value = args.get("mission_id") or context.get("mission_id")
    return str(value) if value else None


def _start_destination(args: Dict[str, Any], context: Dict[str, Any]):
    start = context.get("start") if isinstance(context.get("start"), dict) else {}
    destination = context.get("destination") if isinstance(context.get("destination"), dict) else {}
    start_lon = args.get("start_lon", start.get("x"))
    start_lat = args.get("start_lat", start.get("y"))
    dest_lon = args.get("destination_lon", destination.get("x"))
    dest_lat = args.get("destination_lat", destination.get("y"))
    if None in (start_lon, start_lat, dest_lon, dest_lat):
        raise ValueError("start_lon, start_lat, destination_lon and destination_lat are required")
    return (float(start_lon), float(start_lat)), (float(dest_lon), float(dest_lat))


# ---------------------------------------------------------------------- tools
def _get_terrain_at_coordinate(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    lon = _number(args, "lon")
    lat = _number(args, "lat")
    payload = get_terrain_service().point(lon, lat, region_id=_region(args, context))
    values = payload.get("values", {})
    observations = []
    if values.get("elevation_m") is not None:
        observations.append(_obs("get_terrain_at_coordinate", "Elevation", values["elevation_m"], "m", "OBSERVED", _coverage_text(payload), payload.get("source")))
    if values.get("slope_deg") is not None:
        observations.append(_obs("get_terrain_at_coordinate", "Slope", values["slope_deg"], "degree", "DERIVED", _coverage_text(payload), payload.get("source")))
    if values.get("roughness") is not None:
        observations.append(_obs("get_terrain_at_coordinate", "Roughness (TRI)", values["roughness"], "m", "DERIVED", _coverage_text(payload), payload.get("source")))
    return ToolOutcome(
        tool="get_terrain_at_coordinate",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units=payload.get("units", {}),
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage=payload.get("coverage"),
        provenance=list(payload.get("provenance", [])),
    )


def _get_terrain_profile(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    start_lon = _number(args, "start_lon")
    start_lat = _number(args, "start_lat")
    end_lon = _number(args, "end_lon")
    end_lat = _number(args, "end_lat")
    samples = int(args.get("samples") or 25)
    payload = get_terrain_service().profile(start_lon, start_lat, end_lon, end_lat, samples=samples)
    summary = payload.get("summary", {})
    observations = [
        _obs("get_terrain_profile", "Profile distance", payload.get("distance_m"), "m", "DERIVED", None, payload.get("source")),
        _obs("get_terrain_profile", "Valid elevation samples", summary.get("valid_elevation_samples"), "count", "DERIVED", None, payload.get("source")),
        _obs("get_terrain_profile", "Elevation range", [summary.get("min_elevation_m"), summary.get("max_elevation_m")], "m", "OBSERVED", None, payload.get("source")),
    ]
    if summary.get("max_slope_deg") is not None:
        observations.append(_obs("get_terrain_profile", "Maximum slope", summary["max_slope_deg"], "degree", "DERIVED", None, payload.get("source")))
    return ToolOutcome(
        tool="get_terrain_profile",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units=payload.get("points", [{}])[0].get("units", {}) if payload.get("points") else {},
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage={"sampled_classes": summary.get("coverage_class_counts")},
        provenance=list(payload.get("provenance", [])),
    )


def _get_coverage_status(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    terrain = get_terrain_service()
    if args.get("lon") is not None and args.get("lat") is not None:
        payload = terrain.coverage_at(_number(args, "lon"), _number(args, "lat"))
        class_value = (payload.get("coverage") or {}).get("class")
        observations = [
            _obs("get_coverage_status", "Coverage class", class_value, "class", "DERIVED", payload.get("label"), payload.get("source")),
        ]
        return ToolOutcome(
            tool="get_coverage_status",
            data=payload,
            observations=observations,
            sources=_source_list(payload),
            units={"coverage": "class"},
            warnings=list(payload.get("warnings", [])),
            limitations=list(payload.get("limitations", [])),
            coverage=payload.get("coverage"),
            provenance=["derived"],
        )

    payload = terrain.coverage_summary()
    counts = payload.get("counts", {})
    observations = [
        _obs("get_coverage_status", "Valid derivative cells (class 1)", counts.get("1"), "cells", "DERIVED", "grid", payload.get("source")),
        _obs("get_coverage_status", "Elevation-only cells (class 2)", counts.get("2"), "cells", "DERIVED", "grid", payload.get("source")),
        _obs("get_coverage_status", "No-data cells (class 0)", counts.get("0"), "cells", "DERIVED", "grid", payload.get("source")),
        _obs("get_coverage_status", "Total cells", payload.get("total_cells"), "cells", "DERIVED", "grid", payload.get("source")),
    ]
    return ToolOutcome(
        tool="get_coverage_status",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units={"counts": "cells", "resolution": "m"},
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage={"class_counts": counts},
        provenance=["derived"],
    )


def _get_rems_summary(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    sol = args.get("sol")
    payload = get_rems_service().environment(sol=int(sol) if sol is not None else None)
    observations: List[Dict[str, Any]] = []
    for sol_key, measurements in (payload.get("measurements") or {}).items():
        for measurement in ("air_temperature", "pressure", "relative_humidity"):
            block = measurements.get(measurement)
            if not block or block.get("mean") is None:
                continue
            label = f"{block.get('label', measurement)} (sol {sol_key})"
            observations.append(
                _obs("get_rems_summary", label, block["mean"], block.get("unit"), "OBSERVED", "point", payload.get("source"))
            )
    for sol_key, wind in (payload.get("wind") or {}).items():
        speed = (wind or {}).get("speed", {})
        observations.append(
            _obs(
                "get_rems_summary",
                f"Wind speed (sol {sol_key})",
                speed.get("mean"),
                speed.get("unit"),
                "OBSERVED",
                speed.get("availability", "point"),
                payload.get("source"),
            )
        )
    return ToolOutcome(
        tool="get_rems_summary",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units=payload.get("units", {}),
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage=payload.get("coverage"),
        provenance=["observed", "derived statistics"],
    )


def _get_radiation_summary(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    sol = args.get("sol")
    payload = get_rad_service().radiation(sol=int(sol) if sol is not None else None)
    observations: List[Dict[str, Any]] = []
    for measurement, detector in (payload.get("detectors") or {}).items():
        for sol_key, block in (detector.get("sols") or {}).items():
            if block.get("mean") is None:
                continue
            observations.append(
                _obs(
                    "get_radiation_summary",
                    f"{detector.get('detector', measurement)} dose rate (sol {sol_key})",
                    block["mean"],
                    detector.get("unit", "microGray / Hour"),
                    "OBSERVED",
                    "point",
                    payload.get("source"),
                )
            )
    return ToolOutcome(
        tool="get_radiation_summary",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units={"dose_rate": payload.get("unit", "microGray / Hour")},
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage=payload.get("coverage"),
        provenance=["observed"],
    )


def _calculate_route(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    start, destination = _start_destination(args, context)
    strategy = str(args.get("strategy") or context.get("strategy") or "balanced")
    speed = args.get("speed_m_per_min", context.get("travel_speed_m_per_min"))
    max_difficulty = args.get("max_difficulty", context.get("max_difficulty"))
    route = get_route_planner().plan(
        start=start,
        destination=destination,
        strategy=strategy,
        max_difficulty=float(max_difficulty) if max_difficulty is not None else None,
        speed_m_per_min=float(speed) if speed is not None else None,
        region_id=_region(args, context),
    )
    metrics = route.get("metrics", {})
    observations = [
        _obs("calculate_route", "Route distance", route.get("distance_m"), "m", "DERIVED", route.get("feasibility_status"), route.get("source")),
        _obs("calculate_route", "Estimated travel time", route.get("estimated_duration_min"), "min", "DERIVED", route.get("feasibility_status"), route.get("source")),
        _obs("calculate_route", "Terrain difficulty index", route.get("terrain_difficulty"), "index", "DERIVED", route.get("feasibility_status"), route.get("source")),
        _obs("calculate_route", "Coverage class 2 cells on route", metrics.get("coverage_class_counts", {}).get("2"), "cells", "DERIVED", "route", route.get("source")),
    ]
    if metrics.get("max_slope_deg") is not None:
        observations.append(_obs("calculate_route", "Maximum slope on route", metrics["max_slope_deg"], "degree", "DERIVED", "route", route.get("source")))
    return ToolOutcome(
        tool="calculate_route",
        data=route,
        observations=observations,
        sources=_source_list(route),
        units=route.get("units", {}),
        warnings=list(route.get("warnings", [])),
        limitations=list(route.get("limitations", [])),
        coverage=route.get("coverage"),
        provenance=list(route.get("provenance", [])),
    )


def _compare_routes(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    start, destination = _start_destination(args, context)
    strategies = args.get("strategies") or ["shortest", "balanced", "safest_estimated"]
    if not isinstance(strategies, (list, tuple)):
        raise ValueError("strategies must be a list of strategy names")
    speed = args.get("speed_m_per_min", context.get("travel_speed_m_per_min"))
    routes = get_route_planner().compare(
        start=start,
        destination=destination,
        strategies=[str(strategy) for strategy in strategies],
        speed_m_per_min=float(speed) if speed is not None else None,
        region_id=_region(args, context),
    )
    observations = []
    for route in routes:
        observations.append(
            _obs(
                "compare_routes",
                f"{route['strategy']} route distance",
                route.get("distance_m"),
                "m",
                "DERIVED",
                route.get("feasibility_status"),
                route.get("source"),
            )
        )
        observations.append(
            _obs(
                "compare_routes",
                f"{route['strategy']} estimated time",
                route.get("estimated_duration_min"),
                "min",
                "DERIVED",
                route.get("feasibility_status"),
                route.get("source"),
            )
        )
    sources = _source_list(routes[0]) if routes else []
    limitations = routes[0].get("limitations", []) if routes else []
    warnings = []
    for route in routes:
        warnings.extend(route.get("warnings", []))
    return ToolOutcome(
        tool="compare_routes",
        data={"routes": routes, "strategies": list(strategies)},
        observations=observations,
        sources=sources,
        units=routes[0].get("units", {}) if routes else {},
        warnings=list(dict.fromkeys(warnings)),
        limitations=limitations,
        coverage={"routes": [route.get("coverage") for route in routes]},
        provenance=["derived"],
    )


def _evaluate_mission(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    mission_id = _mission_id(args, context)
    if not mission_id:
        raise ValueError("mission_id is required; plan a mission first")
    payload = get_mission_service().evaluate(mission_id)
    summary = payload.get("route_summary", {})
    budget = payload.get("time_budget", {})
    observations = [
        _obs("evaluate_mission", "Feasibility", payload.get("feasibility_status"), None, "DERIVED", None, payload.get("source")),
        _obs("evaluate_mission", "Route distance", summary.get("distance_m"), "m", "DERIVED", None, payload.get("source")),
        _obs("evaluate_mission", "One-way travel time", summary.get("estimated_duration_min"), "min", "DERIVED", None, payload.get("source")),
        _obs("evaluate_mission", "Total mission time", budget.get("total_min"), "min", "DERIVED", None, payload.get("source")),
        _obs("evaluate_mission", "Time limit", budget.get("limit_min"), "min", "DERIVED", None, payload.get("source")),
    ]
    return ToolOutcome(
        tool="evaluate_mission",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units={"distance": "m", "time": "min"},
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage=None,
        provenance=list(payload.get("provenance", [])),
    )


def _evaluate_return_feasibility(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    mission_id = _mission_id(args, context)
    if not mission_id:
        raise ValueError("mission_id is required; plan a mission first")
    current = context.get("current_location") if isinstance(context.get("current_location"), dict) else {}
    lon = args.get("current_lon", current.get("x"))
    lat = args.get("current_lat", current.get("y"))
    if lon is None or lat is None:
        raise ValueError("current_lon and current_lat are required")
    payload = get_mission_service().return_feasibility(
        mission_id=mission_id,
        current_location={"x": float(lon), "y": float(lat)},
        remaining_time_min=float(args.get("remaining_time_min", context.get("remaining_time_min", 120.0))),
        reserve_time_min=float(args.get("reserve_time_min", context.get("reserve_time_min", 20.0))),
    )
    observations = [
        _obs("evaluate_return_feasibility", "Return feasibility", payload.get("feasibility_status"), None, "DERIVED", None, payload.get("source")),
        _obs("evaluate_return_feasibility", "Estimated return time", payload.get("estimated_return_min"), "min", "DERIVED", None, payload.get("source")),
        _obs("evaluate_return_feasibility", "Required time with reserve", payload.get("required_time_min"), "min", "DERIVED", None, payload.get("source")),
        _obs("evaluate_return_feasibility", "Remaining time", payload.get("remaining_time_min"), "min", None, None, payload.get("source")),
    ]
    return ToolOutcome(
        tool="evaluate_return_feasibility",
        data=payload,
        observations=observations,
        sources=_source_list(payload),
        units={"time": "min"},
        warnings=list(payload.get("warnings", [])),
        limitations=list(payload.get("limitations", [])),
        coverage=None,
        provenance=list(payload.get("provenance", [])),
    )


def _generate_mission_report(args: Dict[str, Any], context: Dict[str, Any]) -> ToolOutcome:
    mission_id = _mission_id(args, context)
    report = get_mission_service().report(mission_id, report_format=str(args.get("format") or "json"))
    observations = [
        _obs("generate_mission_report", "Report status", report.get("status"), None, "DERIVED", None, None),
        _obs("generate_mission_report", "Report format", report.get("format"), None, "DERIVED", None, None),
        _obs("generate_mission_report", "Download URL", report.get("download_url"), None, "DERIVED", None, None),
    ]
    return ToolOutcome(
        tool="generate_mission_report",
        data={
            "report_id": report.get("report_id"),
            "generated_at": report.get("generated_at"),
            "status": report.get("status"),
            "format": report.get("format"),
            "download_url": report.get("download_url"),
            "mission_id": mission_id,
            "terrain_coverage": report.get("terrain_coverage"),
            "environment": report.get("environment"),
            "radiation": report.get("radiation"),
            "provenance": report.get("provenance"),
            "warnings": report.get("warnings"),
            "limitations": report.get("limitations"),
        },
        observations=observations,
        sources=[],
        units={},
        warnings=list(report.get("warnings", [])),
        limitations=list(report.get("limitations", [])),
        coverage=None,
        provenance=list(report.get("provenance", [])),
    )


# ------------------------------------------------------------------- registry
TOOL_SPECS: Dict[str, ToolSpec] = {
    "get_terrain_at_coordinate": ToolSpec(
        name="get_terrain_at_coordinate",
        description=(
            "Read observed elevation and derived slope/roughness at one planetocentric "
            "longitude/latitude from the NASA MOLA package. Never use for other planets."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lon": {"type": "number", "description": "Longitude in degrees, east-positive (e.g. 137.4)"},
                "lat": {"type": "number", "description": "Latitude in degrees (e.g. -4.6)"},
            },
            "required": ["lon", "lat"],
        },
        handler=_get_terrain_at_coordinate,
    ),
    "get_terrain_profile": ToolSpec(
        name="get_terrain_profile",
        description="Sample elevation/slope/roughness along a straight line between two coordinates.",
        parameters={
            "type": "object",
            "properties": {
                "start_lon": {"type": "number"},
                "start_lat": {"type": "number"},
                "end_lon": {"type": "number"},
                "end_lat": {"type": "number"},
                "samples": {"type": "integer", "minimum": 2, "maximum": 200, "default": 25},
            },
            "required": ["start_lon", "start_lat", "end_lon", "end_lat"],
        },
        handler=_get_terrain_profile,
    ),
    "get_coverage_status": ToolSpec(
        name="get_coverage_status",
        description=(
            "Report the MOLA coverage class at a coordinate or the coverage class counts for "
            "the whole grid. Class 2 means elevation only; no slope/roughness."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lon": {"type": "number"},
                "lat": {"type": "number"},
            },
            "required": [],
        },
        handler=_get_coverage_status,
    ),
    "get_rems_summary": ToolSpec(
        name="get_rems_summary",
        description=(
            "Historical Curiosity REMS point measurements (sols 9 and 11). Not live, not a "
            "forecast, not spatially distributed. Wind may be insufficient_data."
        ),
        parameters={
            "type": "object",
            "properties": {"sol": {"type": "integer", "enum": [9, 11]}},
            "required": [],
        },
        handler=_get_rems_summary,
    ),
    "get_radiation_summary": ToolSpec(
        name="get_radiation_summary",
        description=(
            "Historical Curiosity RAD dose rates for detectors B and E separately (sols 1-3). "
            "Never combine detectors and never use for route-specific predictions."
        ),
        parameters={
            "type": "object",
            "properties": {"sol": {"type": "integer", "enum": [1, 2, 3]}},
            "required": [],
        },
        handler=_get_radiation_summary,
    ),
    "calculate_route": ToolSpec(
        name="calculate_route",
        description=(
            "Compute one deterministic A* route on the real MOLA coverage grid with a named "
            "strategy. Returns distance, duration, terrain metrics, and coverage classes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_lon": {"type": "number"},
                "start_lat": {"type": "number"},
                "destination_lon": {"type": "number"},
                "destination_lat": {"type": "number"},
                "strategy": {"type": "string", "enum": ["shortest", "balanced", "safest_estimated"]},
                "speed_m_per_min": {"type": "number", "exclusiveMinimum": 0},
            },
            "required": ["start_lon", "start_lat", "destination_lon", "destination_lat"],
        },
        handler=_calculate_route,
    ),
    "compare_routes": ToolSpec(
        name="compare_routes",
        description="Compute and compare the shortest, balanced, and safest A* routes for the same endpoints.",
        parameters={
            "type": "object",
            "properties": {
                "start_lon": {"type": "number"},
                "start_lat": {"type": "number"},
                "destination_lon": {"type": "number"},
                "destination_lat": {"type": "number"},
                "strategies": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["shortest", "balanced", "safest_estimated"]},
                },
            },
            "required": ["start_lon", "start_lat", "destination_lon", "destination_lat"],
        },
        handler=_compare_routes,
    ),
    "evaluate_mission": ToolSpec(
        name="evaluate_mission",
        description="Evaluate a previously planned mission's time budget and route feasibility.",
        parameters={
            "type": "object",
            "properties": {"mission_id": {"type": "string"}},
            "required": [],
        },
        handler=_evaluate_mission,
    ),
    "evaluate_return_feasibility": ToolSpec(
        name="evaluate_return_feasibility",
        description=(
            "Check whether a planned mission can return to its recorded start from the current "
            "coordinate within the remaining time."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mission_id": {"type": "string"},
                "current_lon": {"type": "number"},
                "current_lat": {"type": "number"},
                "remaining_time_min": {"type": "number", "exclusiveMinimum": 0},
                "reserve_time_min": {"type": "number", "minimum": 0},
            },
            "required": ["current_lon", "current_lat"],
        },
        handler=_evaluate_return_feasibility,
    ),
    "generate_mission_report": ToolSpec(
        name="generate_mission_report",
        description="Generate the backend mission report (JSON) with terrain, REMS, and RAD evidence.",
        parameters={
            "type": "object",
            "properties": {
                "mission_id": {"type": "string"},
                "format": {"type": "string", "enum": ["json"]},
            },
            "required": [],
        },
        handler=_generate_mission_report,
    ),
}

TOOL_NAMES = list(TOOL_SPECS)


def ollama_tools() -> List[Dict[str, Any]]:
    """Return the allowlisted tools in Ollama's function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }
        for spec in TOOL_SPECS.values()
    ]


def run_tool(name: str, arguments: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> ToolOutcome:
    """Execute one allowlisted tool, converting every failure into a record."""
    spec = TOOL_SPECS.get(name)
    if spec is None:
        return ToolOutcome(
            tool=str(name),
            status="error",
            error=f"Tool '{name}' is not in the allowlist.",
        )

    started = time.perf_counter()
    try:
        outcome = spec.handler(dict(arguments or {}), dict(context or {}))
    except ApiError as exc:
        outcome = ToolOutcome(tool=name, status="error", error=exc.message, warnings=[exc.message])
    except (TypeError, ValueError) as exc:
        outcome = ToolOutcome(tool=name, status="error", error=str(exc), warnings=[str(exc)])
    except Exception as exc:  # pragma: no cover - defensive boundary
        logger.exception("Assistant tool %s failed", name)
        outcome = ToolOutcome(tool=name, status="error", error=f"{type(exc).__name__}: {exc}")
    outcome.tool = name
    outcome.duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
    return outcome
