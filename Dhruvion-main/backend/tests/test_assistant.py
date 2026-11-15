from app.services.assistant_service import AssistantService


class _TerrainResult:
    region_id = "gale_crater"
    coordinate = {"x": 137.4, "y": -5.4, "crs": "urn:ogc:def:crs:IAU2000::104905"}
    values = {"elevation_m": -4500.0, "slope_deg": 4.2, "roughness": 0.3}
    provenance = ["observed", "derived"]
    availability = "available"
    warnings = []


def test_terrain_question_calls_the_terrain_tool():
    calls = []

    def terrain_query(region_id, x, y):
        calls.append((region_id, x, y))
        return _TerrainResult()

    result = AssistantService(terrain_query=terrain_query).ask(
        "What is the terrain here?",
        {"region_id": "gale_crater", "coordinate": {"x": 137.4, "y": -5.4}},
    )

    assert calls == [("gale_crater", 137.4, -5.4)]
    assert result.intent == "terrain_info"
    assert result.tool_activity == [{"tool": "query_terrain", "status": "completed"}]
    assert result.evidence[0]["values"]["slope_deg"] == 4.2


def test_terrain_question_without_coordinates_does_not_claim_a_tool_call():
    result = AssistantService().ask("Tell me about terrain", {"region_id": "gale_crater"})

    assert result.intent == "terrain_info"
    assert result.tool_activity == []
    assert "coordinates" in result.message.casefold()
