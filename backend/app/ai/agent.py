"""Deterministic-orchestrated mission assistant with optional LLM explanation.

Design contract
---------------
1. The backend computes every fact. The agent selects allowlisted tools, runs
   them against real services, and records the actual calls.
2. The language model is only used to phrase the evidence. It never supplies a
   value, source, unit, trend, or confidence level of its own.
3. When the model is disabled, missing, or times out, the agent returns the
   deterministic evidence-based answer and marks the response as a fallback.
4. Unsupported requests are answered with guidance and **no** tool call, so the
   visible tool activity never claims work that did not happen.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.ai.llm_client import LLMError, get_llm_client
from app.ai.schemas import (
    AssistantHealthResponse,
    AssistantRequest,
    AssistantResponse,
    Confidence,
    Observation,
    ToolCallRecord,
)
from app.ai.tools import DEFAULT_REGION, TOOL_NAMES, ToolOutcome, run_tool
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Gale Crater AOI (planetocentric lon/lat). General text pairs are only accepted
# as coordinates inside this window; labelled coordinates are always passed
# through so the terrain tool can report an out-of-coverage result honestly.
AOI_LON_MIN, AOI_LON_MAX = 135.5, 140.5
AOI_LAT_MIN, AOI_LAT_MAX = -8.0, -3.0

_LABELLED_LON = re.compile(
    r"(?:lon(?:gitude)?|x)\s*[:=]?\s*(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([EW])?", re.IGNORECASE
)
_LABELLED_LAT = re.compile(
    r"(?:lat(?:itude)?|y)\s*[:=]?\s*(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([NS])?", re.IGNORECASE
)
_PAIR = re.compile(
    r"(?<![\d.])(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([NSEW])?\s*(?:,|/|;)\s*"
    r"(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([NSEW])?",
    re.IGNORECASE,
)
_SPACE_PAIR = re.compile(
    r"(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([EW])\s*,?\s*(-?\d{1,2}(?:\.\d+)?)\s*°?\s*([NS])",
    re.IGNORECASE,
)
_SPACE_PAIR_REVERSED = re.compile(
    r"(-?\d{1,2}(?:\.\d+)?)\s*°?\s*([NS])\s*,?\s*(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([EW])",
    re.IGNORECASE,
)
_SOL = re.compile(r"\bsol\s*(\d{1,3})\b", re.IGNORECASE)

_REMS_SOLS = (9, 11)
_RAD_SOLS = (1, 2, 3)

_ROUTE_WORDS = (
    "route",
    "traverse",
    "path",
    "drive",
    "navigate",
    "itinerary",
    "distance",
    "duration",
    "how long",
    "feasible",
    "feasibility",
)
_PROFILE_WORDS = ("profile", "transect", "along", "between", "cross-section", "cross section")
_COVERAGE_WORDS = ("coverage", "no data", "nodata", "mask", "gap", "uncovered", "class 2", "valid")
_TERRAIN_WORDS = ("terrain", "elevation", "slope", "roughness", "hazard", "steep", "altitude")
_REMS_WORDS = (
    "rems",
    "weather",
    "temperature",
    "pressure",
    "humidity",
    "wind",
    "environment",
    "atmosphere",
    "uv ",
)
_RAD_WORDS = ("radiation", "rad ", "dose", "dosimeter", "microgray", "gray")


# --------------------------------------------------------------- coordinates
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _apply_hemisphere(value: float, hemisphere: Optional[str], axis: str) -> float:
    if not hemisphere:
        return value
    hemisphere = hemisphere.upper()
    if axis == "lon" and hemisphere == "W":
        return -abs(value)
    if axis == "lat" and hemisphere == "S":
        return -abs(value)
    return value


def _coord_dict(value: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(value, dict):
        return None
    x = value.get("x", value.get("lon", value.get("longitude")))
    y = value.get("y", value.get("lat", value.get("latitude")))
    if _is_number(x) and _is_number(y):
        return float(x), float(y)
    return None


def _in_aoi(lon: float, lat: float) -> bool:
    return AOI_LON_MIN <= lon <= AOI_LON_MAX and AOI_LAT_MIN <= lat <= AOI_LAT_MAX


def _dedupe(pairs: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    seen = set()
    ordered: List[Tuple[float, float]] = []
    for pair in pairs:
        key = (round(pair[0], 6), round(pair[1], 6))
        if key not in seen:
            seen.add(key)
            ordered.append((round(pair[0], 6), round(pair[1], 6)))
    return ordered


def extract_coordinates(message: str, context: Optional[Dict[str, Any]] = None) -> List[Tuple[float, float]]:
    """Extract plausible (lon, lat) pairs from a message and its context."""
    context = context or {}
    pairs: List[Tuple[float, float]] = []

    for key in ("coordinate", "start", "destination", "current_location"):
        located = _coord_dict(context.get(key))
        if located:
            pairs.append(located)
    for key in ("coordinates", "waypoints"):
        sequence = context.get(key)
        if isinstance(sequence, (list, tuple)):
            for item in sequence:
                located = _coord_dict(item)
                if located:
                    pairs.append(located)

    lon_match = _LABELLED_LON.search(message)
    lat_match = _LABELLED_LAT.search(message)
    if lon_match and lat_match:
        pairs.append(
            (
                _apply_hemisphere(float(lon_match.group(1)), lon_match.group(2), "lon"),
                _apply_hemisphere(float(lat_match.group(1)), lat_match.group(2), "lat"),
            )
        )

    for match in _PAIR.finditer(message):
        lon = _apply_hemisphere(float(match.group(1)), match.group(2), "lon")
        lat = _apply_hemisphere(float(match.group(3)), match.group(4), "lat")
        if _in_aoi(lon, lat):
            pairs.append((lon, lat))

    for match in _SPACE_PAIR.finditer(message):
        lon = _apply_hemisphere(float(match.group(1)), match.group(2), "lon")
        lat = _apply_hemisphere(float(match.group(3)), match.group(4), "lat")
        if _in_aoi(lon, lat):
            pairs.append((lon, lat))

    for match in _SPACE_PAIR_REVERSED.finditer(message):
        lat = _apply_hemisphere(float(match.group(1)), match.group(2), "lat")
        lon = _apply_hemisphere(float(match.group(3)), match.group(4), "lon")
        if _in_aoi(lon, lat):
            pairs.append((lon, lat))

    return _dedupe(pairs)


def _endpoints(
    coordinates: Sequence[Tuple[float, float]], context: Dict[str, Any]
) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
    start = _coord_dict(context.get("start"))
    destination = _coord_dict(context.get("destination"))
    if start and destination:
        return start, destination
    if len(coordinates) >= 2:
        return coordinates[0], coordinates[1]
    if len(coordinates) == 1:
        if destination:
            return coordinates[0], destination
        if start:
            return start, coordinates[0]
    return start, destination


def _extract_sol(message: str, allowed: Sequence[int]) -> Optional[int]:
    match = _SOL.search(message)
    if not match:
        return None
    sol = int(match.group(1))
    return sol if sol in allowed else None


# -------------------------------------------------------------- intent plan
def _plan_tools(
    message: str, context: Dict[str, Any]
) -> Tuple[str, List[Tuple[str, Dict[str, Any]]], List[str]]:
    lower = message.casefold()
    coordinates = extract_coordinates(message, context)
    start, destination = _endpoints(coordinates, context)
    mission_id = context.get("mission_id")
    region_id = context.get("region_id", DEFAULT_REGION)
    notes: List[str] = []

    def route_args() -> Dict[str, Any]:
        args: Dict[str, Any] = {
            "start_lon": start[0],
            "start_lat": start[1],
            "destination_lon": destination[0],
            "destination_lat": destination[1],
            "region_id": region_id,
        }
        if context.get("strategy"):
            args["strategy"] = context["strategy"]
        if context.get("travel_speed_m_per_min") is not None:
            args["speed_m_per_min"] = context["travel_speed_m_per_min"]
        if context.get("max_difficulty") is not None:
            args["max_difficulty"] = context["max_difficulty"]
        return args

    # 1. Explicit report request.
    if any(word in lower for word in ("report", "export", "summary document")):
        return "mission_report", [("generate_mission_report", {"mission_id": mission_id, "region_id": region_id})], notes

    # 2. Radiation (historical point measurement).
    if any(word in lower for word in _RAD_WORDS):
        sol = _extract_sol(message, _RAD_SOLS)
        if sol is None and _SOL.search(message):
            notes.append("Only RAD sols 1, 2, and 3 are available in the package.")
        args: Dict[str, Any] = {"region_id": region_id}
        if sol is not None:
            args["sol"] = sol
        return "radiation_summary", [("get_radiation_summary", args)], notes

    # 3. REMS / environment (historical point measurement).
    if any(word in lower for word in _REMS_WORDS):
        sol = _extract_sol(message, _REMS_SOLS)
        if sol is None and _SOL.search(message):
            notes.append("Only REMS sols 9 and 11 are available in the package.")
        args = {"region_id": region_id}
        if sol is not None:
            args["sol"] = sol
        return "environment_summary", [("get_rems_summary", args)], notes

    # 4. Return-to-base feasibility.
    if any(word in lower for word in ("return", "back to base", "get back", "come back", "rtb")):
        args = {"mission_id": mission_id, "region_id": region_id}
        if coordinates:
            args["current_lon"], args["current_lat"] = coordinates[-1]
        for key in ("remaining_time_min", "reserve_time_min"):
            if context.get(key) is not None:
                args[key] = context[key]
        if not mission_id:
            notes.append("Return feasibility needs a planned mission_id so the backend knows the base location.")
        if "current_lon" not in args:
            notes.append("Return feasibility also needs the current coordinate.")
        return "return_feasibility", [("evaluate_return_feasibility", args)], notes

    # 5. Route comparison.
    if "compare" in lower or "versus" in lower or " vs " in lower:
        if not (start and destination):
            notes.append("Route comparison needs two coordinates (start and destination) in the message or context.")
            return "route_comparison", [], notes
        return "route_comparison", [("compare_routes", route_args())], notes

    # 6. Route planning / mission feasibility.
    if any(word in lower for word in _ROUTE_WORDS):
        if start and destination:
            return "route_plan", [("calculate_route", route_args())], notes
        if mission_id:
            return "mission_evaluation", [("evaluate_mission", {"mission_id": mission_id, "region_id": region_id})], notes
        notes.append(
            "Route planning needs start and destination coordinates, or a mission_id for an existing plan."
        )
        return "route_plan", [], notes

    # 7. Coverage status.
    if any(word in lower for word in _COVERAGE_WORDS):
        args = {"region_id": region_id}
        if coordinates:
            args["lon"], args["lat"] = coordinates[0]
        return "coverage_status", [("get_coverage_status", args)], notes

    # 8. Terrain point or profile.
    if any(word in lower for word in _TERRAIN_WORDS):
        if start and destination and any(word in lower for word in _PROFILE_WORDS):
            return (
                "terrain_profile",
                [
                    (
                        "get_terrain_profile",
                        {
                            "start_lon": start[0],
                            "start_lat": start[1],
                            "end_lon": destination[0],
                            "end_lat": destination[1],
                            "region_id": region_id,
                        },
                    )
                ],
                notes,
            )
        if coordinates:
            return (
                "terrain_point",
                [("get_terrain_at_coordinate", {"lon": coordinates[0][0], "lat": coordinates[0][1], "region_id": region_id})],
                notes,
            )
        notes.append("A terrain reading needs a longitude/latitude coordinate.")
        return "terrain_point", [], notes

    # 9. Fallbacks: mission evaluation, coordinate reading, or coverage summary.
    if mission_id:
        return "mission_evaluation", [("evaluate_mission", {"mission_id": mission_id, "region_id": region_id})], notes
    if coordinates:
        return (
            "terrain_point",
            [("get_terrain_at_coordinate", {"lon": coordinates[0][0], "lat": coordinates[0][1], "region_id": region_id})],
            notes,
        )
    notes.append(
        "I can read terrain, coverage, REMS, radiation, routes, mission feasibility, return feasibility, "
        "and reports. Provide coordinates or a mission_id for a specific answer."
    )
    return "unknown", [], notes


# ------------------------------------------------------------- answer helpers
def _format_value(value: Any) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"{value:,.2f}".rstrip("0").rstrip(".")
        return f"{value:,}"
    if isinstance(value, (list, tuple)):
        return " to ".join(_format_value(item) for item in value)
    return str(value)


def _format_observation(observation: Dict[str, Any]) -> str:
    value = _format_value(observation.get("value"))
    unit = observation.get("unit")
    if value == "unavailable" or not unit:
        return f"{observation['label']}: {value}"
    return f"{observation['label']}: {value} {unit}"


def _deterministic_answer(
    intent: str,
    outcomes: Sequence[ToolOutcome],
    observations: Sequence[Dict[str, Any]],
    notes: Sequence[str],
) -> str:
    completed = [outcome for outcome in outcomes if outcome.status == "completed"]
    errors = [outcome for outcome in outcomes if outcome.status == "error"]

    if not outcomes:
        if notes:
            return notes[0]
        return (
            "I can only answer from backend data. Provide a coordinate, a mission_id, or ask about "
            "terrain, coverage, REMS, radiation, routes, or reports."
        )

    if errors and not observations:
        detail = "; ".join(f"{error.tool}: {error.error}" for error in errors)
        return (
            "The requested backend tool did not return usable data, so I cannot answer with values. "
            f"Details: {detail}."
        )

    usable = [observation for observation in observations if observation.get("value") is not None]
    if usable:
        body = "; ".join(_format_observation(observation) for observation in usable[:8])
        prefix = {
            "terrain_point": "Terrain reading from the NASA MOLA package",
            "terrain_profile": "Terrain profile from the NASA MOLA package",
            "coverage_status": "Coverage status from the NASA MOLA package",
            "environment_summary": "Historical REMS point measurements (not live or forecast)",
            "radiation_summary": "Historical RAD point measurements (not route-specific)",
            "route_plan": "Deterministic route result from the NASA MOLA grid",
            "route_comparison": "Deterministic route comparison from the NASA MOLA grid",
            "mission_evaluation": "Mission feasibility from the planned route",
            "return_feasibility": "Return feasibility from the planned route",
            "mission_report": "Mission report generated by the backend",
        }.get(intent, "Backend result")
        answer = f"{prefix}: {body}."
        unavailable = len(observations) - len(usable)
        if unavailable:
            answer += f" {unavailable} requested value(s) are unavailable and were not replaced with estimates."
        if errors:
            answer += f" Some tools failed: {'; '.join(error.tool for error in errors)}."
        return answer

    if completed:
        return (
            "The backend tool completed but reported no usable values for this request. "
            "No value was fabricated to fill the gap."
        )
    return "No backend tool produced an answer for this request."


def _merge_sources(outcomes: Sequence[ToolOutcome]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for outcome in outcomes:
        for source in outcome.sources:
            key = (source.get("product_id"), source.get("name"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(source)
    return merged


def _merge_units(outcomes: Sequence[ToolOutcome]) -> Dict[str, str]:
    units: Dict[str, str] = {}
    for outcome in outcomes:
        for key, value in (outcome.units or {}).items():
            if isinstance(value, str):
                units.setdefault(key, value)
    return units


def _merge_unique(values: Sequence[str]) -> List[str]:
    ordered: List[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def _confidence(outcomes: Sequence[ToolOutcome], observations: Sequence[Dict[str, Any]]) -> Confidence:
    errors = [outcome for outcome in outcomes if outcome.status == "error"]
    missing = [observation for observation in observations if observation.get("value") is None]
    completed = [outcome for outcome in outcomes if outcome.status == "completed"]

    if not outcomes:
        return Confidence(
            level="low",
            basis="No backend tool was called, so there is no evidence to support a factual answer.",
            limitations=["Ask for terrain, coverage, REMS, radiation, a route, a mission, or a report."],
        )
    if errors and not completed:
        return Confidence(
            level="low",
            basis="All requested backend tools failed; no evidence was produced.",
            limitations=[error.error or "Tool failed" for error in errors],
        )
    if errors or missing:
        return Confidence(
            level="medium",
            basis=(
                "At least one backend tool completed, but some values are unavailable or some "
                "tools failed. Only returned values are reported."
            ),
            limitations=[observation["label"] for observation in missing][:5],
        )
    return Confidence(
        level="high",
        basis="All requested backend tools completed and returned values directly from the installed NASA package.",
        limitations=[],
    )


def _recommendations(intent: str, outcomes: Sequence[ToolOutcome], mission_id: Optional[str]) -> Dict[str, Any]:
    report_outcome = next((outcome for outcome in outcomes if outcome.tool == "generate_mission_report"), None)
    if report_outcome and isinstance(report_outcome.data, dict):
        return {
            "availability": report_outcome.status,
            "download_url": report_outcome.data.get("download_url"),
            "next_steps": ["Download the generated JSON report", "Attach it to the mission record"],
        }
    next_steps = {
        "terrain_point": ["Inspect the same point in the Martian Map", "Check coverage class before planning a route"],
        "terrain_profile": ["Compare with the route corridor", "Look for coverage class 2 samples"],
        "coverage_status": ["Treat class 2 as unknown derivatives, not safe terrain", "Avoid class 0 cells"],
        "environment_summary": ["Treat REMS as historical point reference only", "Do not extrapolate along the traverse"],
        "radiation_summary": ["Keep detectors B and E separate", "Do not use RAD for route-specific predictions"],
        "route_plan": ["Compare shortest, balanced, and safest routes", "Check the time budget before execution"],
        "route_comparison": ["Choose a strategy that fits the mission time budget", "Inspect slope and coverage warnings"],
        "mission_evaluation": ["Check the return feasibility before departure", "Review the route warnings"],
        "return_feasibility": ["Reduce exploration time if the margin is tight", "Re-evaluate after moving"],
        "mission_report": ["Download the report and verify the warnings"],
    }.get(intent, ["Ask a more specific mission question"])
    payload: Dict[str, Any] = {"availability": "available", "next_steps": next_steps}
    if mission_id:
        payload["mission_id"] = mission_id
    return payload


# --------------------------------------------------------------------- agent
class MissionAssistant:
    def __init__(self, client=None) -> None:
        self._client = client or get_llm_client()

    # ----------------------------------------------------------------- health
    def health(self) -> AssistantHealthResponse:
        health = self._client.health(force=True)
        error = health.error
        if settings.LLM_PROVIDER not in {"groq", "ollama"}:
            error = f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'; only 'groq' and 'ollama' are implemented."
        return AssistantHealthResponse(
            status="ok" if health.available else "degraded",
            llm_enabled=settings.LLM_ENABLED,
            provider=settings.LLM_PROVIDER,
            model=health.model,
            available=bool(health.available and settings.LLM_PROVIDER in {"groq", "ollama"}),
            base_url=health.base_url,
            error=error,
            tools=list(TOOL_NAMES),
            fallback_available=True,
        )

    # -------------------------------------------------------------------- ask
    def ask(self, request: AssistantRequest) -> AssistantResponse:
        context = dict(request.context or {})
        if request.mission_id:
            context.setdefault("mission_id", request.mission_id)

        intent, plan, notes = _plan_tools(request.message, context)
        outcomes: List[ToolOutcome] = []
        tool_records: List[ToolCallRecord] = []
        for tool_name, arguments in plan:
            outcome = run_tool(tool_name, arguments, context)
            outcomes.append(outcome)
            tool_records.append(
                ToolCallRecord(
                    tool=outcome.tool,
                    status=outcome.status,
                    arguments=arguments,
                    duration_ms=outcome.duration_ms,
                    error=outcome.error,
                )
            )

        observations: List[Dict[str, Any]] = []
        warnings: List[str] = []
        limitations: List[str] = []
        for outcome in outcomes:
            observations.extend(outcome.observations)
            warnings.extend(outcome.warnings)
            limitations.extend(outcome.limitations)
        limitations.extend(
            [
                "The assistant reports backend values only; it does not estimate missing terrain or environment data.",
                "REMS and RAD are historical point measurements at the Curiosity rover, not traverse conditions.",
            ]
        )

        mission_id = context.get("mission_id")
        for outcome in outcomes:
            data = outcome.data
            if isinstance(data, dict):
                if data.get("mission_id"):
                    mission_id = str(data["mission_id"])
                route = data.get("route")
                if isinstance(route, dict) and route.get("mission_id"):
                    mission_id = str(route["mission_id"])
                alternative = data.get("alternative_route")
                if isinstance(alternative, dict) and alternative.get("mission_id"):
                    mission_id = str(alternative["mission_id"])

        deterministic = _deterministic_answer(intent, outcomes, observations, notes)
        answer = deterministic
        fallback = True
        model_used: Optional[str] = None
        llm_error: Optional[str] = None

        health = self._client.health()
        if outcomes and health.available and settings.LLM_PROVIDER in {"groq", "ollama"}:
            try:
                answer = self._phrase_with_model(request.message, intent, outcomes, observations, warnings, limitations)
                fallback = False
                model_used = health.model
            except LLMError as exc:
                llm_error = str(exc)
                logger.warning("Assistant model phrasing failed: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive boundary
                llm_error = f"{type(exc).__name__}: {exc}"
                logger.exception("Unexpected assistant model failure")
        else:
            llm_error = health.error or "No backend tool was called, so the model had no evidence to explain."

        if fallback:
            if llm_error:
                warnings.append(f"Deterministic fallback used: {llm_error}")
            else:
                warnings.append("Deterministic fallback used: model phrasing was not available.")

        warnings = _merge_unique(warnings)
        limitations = _merge_unique(limitations)
        confidence = _confidence(outcomes, observations)
        sources = _merge_sources(outcomes)
        units = _merge_units(outcomes)
        recommendations = _recommendations(intent, outcomes, mission_id)

        response = AssistantResponse(
            message=answer,
            answer=answer,
            intent=intent,
            recommendation=recommendations,
            tool_activity=tool_records,
            evidence=[outcome.data for outcome in outcomes],
            warnings=warnings,
            sources=sources,
            actions=list(recommendations.get("next_steps", [])),
            tools_used=[record.tool for record in tool_records],
            observations=[Observation(**observation) for observation in observations],
            units=units,
            limitations=limitations,
            confidence=confidence,
            fallback=fallback,
            model=model_used,
            mission_id=mission_id,
            grounding={
                "version": "1.0",
                "intent": intent,
                "tool_count": len(outcomes),
                "completed": sum(1 for outcome in outcomes if outcome.status == "completed"),
                "errors": sum(1 for outcome in outcomes if outcome.status == "error"),
                "observation_count": len(observations),
                "llm_used": model_used is not None,
                "llm_error": llm_error,
            },
        )
        return response

    # ------------------------------------------------------------- LLM prompt
    def _phrase_with_model(
        self,
        message: str,
        intent: str,
        outcomes: Sequence[ToolOutcome],
        observations: Sequence[Dict[str, Any]],
        warnings: Sequence[str],
        limitations: Sequence[str],
    ) -> str:
        evidence = {
            "intent": intent,
            "observations": [
                {
                    "label": item.get("label"),
                    "value": item.get("value"),
                    "unit": item.get("unit"),
                    "provenance": item.get("provenance"),
                    "coverage": item.get("coverage"),
                }
                for item in list(observations)[:10]
            ],
            "warnings": list(warnings)[:4],
            "limitations": list(limitations)[:4],
            "tool_status": [{"tool": outcome.tool, "status": outcome.status} for outcome in outcomes],
        }
        evidence_text = json.dumps(evidence, ensure_ascii=False, default=str)
        if len(evidence_text) > 4000:
            evidence_text = evidence_text[:4000] + "...[truncated]"

        system = (
            "You are the DHRUVION Mars mission assistant. Explain the supplied backend evidence "
            "in 2-3 short sentences of plain prose.\n"
            "Hard rules:\n"
            "- Use ONLY the EVIDENCE JSON. Never invent or round a value, unit, source, trend, "
            "tool result, or confidence level.\n"
            "- If a value is null or marked unavailable/insufficient_data, say it is unavailable.\n"
            "- REMS and RAD are historical point measurements at the Curiosity rover; never call "
            "them live, a forecast, or route-specific.\n"
            "- Slope and roughness are derived at the ~463 m MOLA baseline, not rover-scale trafficability.\n"
            "- Keep detectors B and E separate for RAD.\n"
            "- Do not claim a tool ran unless tool_status lists it as completed.\n"
            "- Do not use markdown, headings, or bullet lists.\n"
            "- If the evidence is insufficient, say what is missing instead of guessing.\n"
            f"EVIDENCE JSON:\n{evidence_text}"
        )
        reply = self._client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            timeout=settings.LLM_ANSWER_TIMEOUT_S,
            options={"num_predict": settings.LLM_MAX_TOKENS, "num_ctx": 4096},
        )
        content = str(reply.get("content") or "").strip()
        if not content:
            raise LLMError("Model returned an empty explanation")
        return content


_assistant: Optional[MissionAssistant] = None


def get_assistant() -> MissionAssistant:
    global _assistant
    if _assistant is None:
        _assistant = MissionAssistant()
    return _assistant
