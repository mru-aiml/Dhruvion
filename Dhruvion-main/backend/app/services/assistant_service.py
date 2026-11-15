"""Deterministic, allowlisted tools for the mission assistant.

This module deliberately does not call an LLM.  It turns a small, explicit
set of requests into calls to backend services and returns evidence from those
calls.  A future LLM integration can choose a tool, but it must continue to
use these functions for all mission facts.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.exceptions import ApiError
from app.services.terrain_data_service import get_terrain_data_service


@dataclass
class AssistantResult:
    message: str
    intent: str
    recommendation: Optional[Dict[str, Any]] = None
    tool_activity: List[Dict[str, str]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)


class AssistantService:
    """Routes only allowlisted, deterministic assistant capabilities."""

    def __init__(self, terrain_query: Optional[Callable[..., Any]] = None):
        self._terrain_query = terrain_query or get_terrain_data_service().query_terrain

    @staticmethod
    def _intent(message: str) -> str:
        lower_message = message.casefold()
        if any(word in lower_message for word in ("terrain", "elevation", "slope", "roughness")):
            return "terrain_info"
        if any(word in lower_message for word in ("hazard", "obstruction", "reroute", "emergency")):
            return "emergency_navigation"
        if any(word in lower_message for word in ("target", "science", "geology")):
            return "science_targets"
        if any(word in lower_message for word in ("route", "reach", "return", "feasible", "time limit")):
            return "mission_feasibility"
        return "unknown"

    def ask(self, message: str, context: Dict[str, Any]) -> AssistantResult:
        """Answer using a real tool call when the required inputs are present."""
        intent = self._intent(message)
        if intent != "terrain_info":
            return AssistantResult(
                message=(
                    "I can provide a terrain reading when the request includes x and y "
                    "coordinates. Other assistant tools are not connected yet."
                ),
                intent=intent,
                warnings=["No backend tool was called because the requested capability is unavailable."],
                actions=["Provide terrain coordinates", "Use route planner for deterministic route calculations"],
            )

        coordinate = context.get("coordinate", context)
        x, y = coordinate.get("x"), coordinate.get("y")
        region_id = context.get("region_id", "gale_crater")
        if not isinstance(x, (int, float)) or isinstance(x, bool) or not isinstance(y, (int, float)) or isinstance(y, bool):
            return AssistantResult(
                message="Terrain lookup needs numeric x and y coordinates in the request context.",
                intent=intent,
                warnings=["No terrain tool call was made because coordinates were missing or invalid."],
                actions=["Provide context.coordinate.x and context.coordinate.y"],
            )

        try:
            result = self._terrain_query(region_id, float(x), float(y))
        except ApiError as error:
            return AssistantResult(
                message="Terrain data could not be retrieved.",
                intent=intent,
                tool_activity=[{"tool": "query_terrain", "status": "unavailable"}],
                warnings=[error.message],
                actions=["Check dataset availability"],
            )

        evidence = {
            "type": "terrain_query",
            "region_id": result.region_id,
            "coordinate": result.coordinate,
            "values": result.values,
            "availability": result.availability,
            "provenance": result.provenance,
        }
        if result.availability == "available":
            message_text = "Terrain reading retrieved from the configured terrain dataset."
        else:
            message_text = "No terrain values are available for this coordinate."

        return AssistantResult(
            message=message_text,
            intent=intent,
            recommendation={"availability": result.availability},
            tool_activity=[{"tool": "query_terrain", "status": "completed"}],
            evidence=[evidence],
            warnings=result.warnings,
            sources=[{"provenance": value} for value in result.provenance],
            actions=["Inspect terrain layers", "Choose another coordinate"],
        )


_assistant_service: Optional[AssistantService] = None


def get_assistant_service() -> AssistantService:
    global _assistant_service
    if _assistant_service is None:
        _assistant_service = AssistantService()
    return _assistant_service
