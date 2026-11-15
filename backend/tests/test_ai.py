"""Assistant and allowlisted-tool tests.

These tests never contact a real language model. Fake clients exercise the three
model states that matter for the contract: unavailable, timeout, and success.
The deterministic tool layer always runs against the real NASA dataset package.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ai.agent import MissionAssistant
from app.ai.groq_client import GroqClient
from app.ai.llm_client import LLMHealth, LLMTimeout
from app.ai.schemas import AssistantRequest
from app.ai.tools import TOOL_NAMES, ToolOutcome, ollama_tools, run_tool
from app.main import app
from app.services.terrain_service import get_terrain_service

client = TestClient(app)

EXPECTED_TOOLS = {
    "get_terrain_at_coordinate",
    "get_terrain_profile",
    "get_coverage_status",
    "get_rems_summary",
    "get_radiation_summary",
    "calculate_route",
    "compare_routes",
    "evaluate_mission",
    "evaluate_return_feasibility",
    "generate_mission_report",
}


class FakeLLM:
    """Minimal stand-in for OllamaClient with a scripted outcome."""

    def __init__(self, available: bool = False, reply: str | None = None, error: Exception | None = None):
        self.available = available
        self.reply = reply
        self.error = error
        self.chat_calls = 0

    def health(self, force: bool = False) -> LLMHealth:
        return LLMHealth(
            enabled=True,
            provider="ollama",
            model="fake-model",
            base_url="http://127.0.0.1:11434",
            available=self.available,
            error=None if self.available else "Fake model is not installed",
        )

    def chat(self, messages, tools=None, timeout=None, options=None):
        self.chat_calls += 1
        if self.error is not None:
            raise self.error
        return {"role": "assistant", "content": self.reply or ""}


# ------------------------------------------------------------------ allowlist
def test_allowlist_is_exact():
    assert set(TOOL_NAMES) == EXPECTED_TOOLS
    assert [tool["function"]["name"] for tool in ollama_tools()] == TOOL_NAMES


def test_unknown_tool_is_rejected():
    outcome = run_tool("os_shell", {"command": "dir"})
    assert outcome.status == "error"
    assert "not in the allowlist" in (outcome.error or "")


# --------------------------------------------------------------- real tools
def test_terrain_tool_returns_real_observed_and_derived_values():
    outcome = run_tool("get_terrain_at_coordinate", {"lon": 137.4, "lat": -5.4})
    assert outcome.status == "completed"
    labels = {item["label"]: item for item in outcome.observations}
    assert labels["Elevation"]["value"] is not None
    assert labels["Elevation"]["provenance"] == "OBSERVED"
    assert labels["Elevation"]["unit"] == "m"
    assert labels["Slope"]["provenance"] == "DERIVED"
    assert outcome.sources, "terrain tool must propagate its NASA source"
    assert outcome.units.get("elevation_m") == "m"


def test_terrain_tool_does_not_fabricate_outside_coverage():
    outcome = run_tool("get_terrain_at_coordinate", {"lon": 0.0, "lat": 0.0})
    assert outcome.status == "completed"
    assert outcome.observations == []
    assert outcome.data["availability"] == "unavailable"


def test_coverage_tool_reports_grid_classes():
    outcome = run_tool("get_coverage_status", {})
    assert outcome.status == "completed"
    assert outcome.data["total_cells"] > 0
    counts = outcome.data["counts"]
    assert counts.get("1", 0) > 0


def test_mission_tool_requires_identifier():
    outcome = run_tool("evaluate_mission", {})
    assert outcome.status == "error"
    assert "mission_id" in (outcome.error or "")


# ------------------------------------------------------------------- assistant
def _terrain_question() -> str:
    return "What is the elevation and slope at lon 137.4, lat -5.4?"


def test_assistant_falls_back_when_model_unavailable():
    fake = FakeLLM(available=False)
    response = MissionAssistant(client=fake).ask(AssistantRequest(message=_terrain_question()))

    assert response.fallback is True
    assert response.model is None
    assert fake.chat_calls == 0
    assert response.tools_used == ["get_terrain_at_coordinate"]
    assert response.tool_activity[0].status == "completed"

    elevation = next(item for item in response.observations if item.label == "Elevation")
    expected = get_terrain_service().point(137.4, -5.4)["values"]["elevation_m"]
    assert elevation.value == expected
    assert any("Deterministic fallback used" in warning for warning in response.warnings)
    assert response.confidence.level == "high"


def test_assistant_falls_back_when_model_times_out():
    fake = FakeLLM(available=True, error=LLMTimeout("Model 'fake-model' timed out after 30s"))
    response = MissionAssistant(client=fake).ask(AssistantRequest(message=_terrain_question()))

    assert fake.chat_calls == 1
    assert response.fallback is True
    assert response.model is None
    assert response.answer == response.message
    assert "Terrain reading" in response.answer
    assert any("timed out" in warning for warning in response.warnings)
    assert response.grounding["llm_used"] is False
    assert "timed out" in (response.grounding["llm_error"] or "")


def test_assistant_uses_model_phrasing_when_available():
    fake = FakeLLM(available=True, reply="Elevation and slope come from the installed NASA MOLA package.")
    response = MissionAssistant(client=fake).ask(AssistantRequest(message=_terrain_question()))

    assert fake.chat_calls == 1
    assert response.fallback is False
    assert response.model == "fake-model"
    assert response.answer == "Elevation and slope come from the installed NASA MOLA package."
    assert response.message == response.answer
    assert response.grounding["llm_used"] is True


def test_assistant_does_not_call_tools_for_unsupported_request():
    fake = FakeLLM(available=True, reply="should not be used")
    response = MissionAssistant(client=fake).ask(AssistantRequest(message="Tell me a joke about Mars."))

    assert response.intent == "unknown"
    assert response.tools_used == []
    assert response.observations == []
    assert response.fallback is True
    assert fake.chat_calls == 0
    assert response.confidence.level == "low"


def test_assistant_tool_failure_is_reported_without_values(monkeypatch):
    def failing_tool(name, arguments=None, context=None):
        return ToolOutcome(tool=name, status="error", error="Raster unavailable")

    monkeypatch.setattr("app.ai.agent.run_tool", failing_tool)
    response = MissionAssistant(client=FakeLLM(available=False)).ask(
        AssistantRequest(message=_terrain_question())
    )

    assert response.observations == []
    assert response.confidence.level == "low"
    assert "Raster unavailable" in response.answer
    assert response.evidence == [None]
    assert all(item.value is None for item in response.observations)


def test_assistant_route_question_returns_deterministic_route():
    fake = FakeLLM(available=False)
    response = MissionAssistant(client=fake).ask(
        AssistantRequest(message="Plan a route from 137.2, -4.5 to 137.3, -4.55")
    )

    assert response.tools_used == ["calculate_route"]
    assert response.intent == "route_plan"
    route = response.evidence[0]
    assert route["distance_m"] > 0
    assert route["id"].startswith("route-")
    distance = next(item for item in response.observations if item.label == "Route distance")
    assert distance.value == route["distance_m"]


def test_assistant_rems_question_is_point_reference():
    response = MissionAssistant(client=FakeLLM(available=False)).ask(
        AssistantRequest(message="What was the REMS temperature on sol 9?")
    )

    assert response.tools_used == ["get_rems_summary"]
    assert response.intent == "environment_summary"
    assert "not live or forecast" in response.answer
    limitations = " ".join(response.limitations).lower()
    assert "historical" in limitations
    assert "not traverse conditions" in limitations


def test_assistant_radiation_keeps_detectors_separate():
    response = MissionAssistant(client=FakeLLM(available=False)).ask(
        AssistantRequest(message="What is the radiation dose on sol 2?")
    )

    assert response.tools_used == ["get_radiation_summary"]
    labels = {item.label for item in response.observations}
    assert any("silicon detector" in label for label in labels)
    assert any("BC-432" in label for label in labels)


# ------------------------------------------------------------------ endpoints
def test_assistant_ask_endpoint_returns_structured_response(monkeypatch):
    fake = FakeLLM(available=False)
    monkeypatch.setattr("app.api.routes_assistant.get_assistant", lambda: MissionAssistant(client=fake))
    response = client.post("/api/assistant/ask", json={"message": _terrain_question()})
    assert response.status_code == 200
    body = response.json()
    for key in (
        "answer",
        "intent",
        "tools_used",
        "observations",
        "units",
        "sources",
        "recommendation",
        "warnings",
        "limitations",
        "confidence",
        "fallback",
    ):
        assert key in body
    assert body["tools_used"] == ["get_terrain_at_coordinate"]
    assert body["answer"]
    assert body["observations"]


def test_assistant_health_endpoint_lists_allowlist(monkeypatch):
    fake = FakeLLM(available=False)
    monkeypatch.setattr("app.api.routes_assistant.get_assistant", lambda: MissionAssistant(client=fake))
    response = client.get("/api/assistant/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["fallback_available"] is True
    assert set(body["tools"]) == EXPECTED_TOOLS


# --------------------------------------------------------------------- Groq
class FakeGroqResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": "Groq explains the verified terrain result."}}]}


def test_groq_client_without_api_key_is_unavailable():
    client = GroqClient(api_key="", model="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1")
    health = client.health()
    assert health.available is False
    assert health.provider == "groq"


def test_groq_client_returns_mocked_chat_content(monkeypatch):
    client = GroqClient(api_key="test-key", model="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1", timeout=5.0)

    class FakeModelsResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "llama-3.3-70b-versatile"}]}

    monkeypatch.setattr("app.ai.groq_client.httpx.get", lambda *args, **kwargs: FakeModelsResponse())
    monkeypatch.setattr("app.ai.groq_client.httpx.post", lambda *args, **kwargs: FakeGroqResponse())

    health = client.health()
    assert health.available is True
    reply = client.chat(
        messages=[{"role": "user", "content": "What is the elevation?"}],
        timeout=5.0,
        options={"num_predict": 100},
    )
    assert reply["content"] == "Groq explains the verified terrain result."
    assert reply["model"] == "llama-3.3-70b-versatile"
