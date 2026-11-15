"""Deterministic route, mission, reroute, and report integration tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)
REGION = "gale_crater"
START = {"x": 137.2, "y": -4.5, "crs": "urn:ogc:def:crs:IAU2000::104905"}
DESTINATION = {"x": 137.3, "y": -4.55, "crs": "urn:ogc:def:crs:IAU2000::104905"}


def _plan_mission() -> dict:
    response = client.post(
        "/api/mission/plan",
        json={
            "region_id": REGION,
            "start": START,
            "destination": DESTINATION,
            "time_limit_min": 600,
            "exploration_time_min": 30,
            "reserve_time_min": 30,
            "route_strategy": "balanced",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_route_optimize_returns_real_geometry_and_metrics():
    response = client.post(
        "/api/route/optimize",
        json={
            "region_id": REGION,
            "start": START,
            "destination": DESTINATION,
            "strategies": ["shortest", "balanced", "safest_estimated"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["algorithm"]["name"] == "A*"
    assert len(body["routes"]) == 3
    strategies = {route["strategy"] for route in body["routes"]}
    assert strategies == {"shortest", "balanced", "safest_estimated"}

    for route in body["routes"]:
        coordinates = route["geometry"]["coordinates"]
        assert len(coordinates) >= 2
        assert route["distance_m"] > 0
        assert route["estimated_duration_min"] > 0
        assert route["metrics"]["coverage_class_counts"]["1"] > 0
        assert route["source"]["provider"]
        assert route["units"]["distance_m"] == "m"
        assert route["feasibility_status"] in {"feasible", "caution", "not_feasible"}
        # GeoJSON order is [lon, lat].
        assert 136.0 < coordinates[0][0] < 140.0
        assert -7.0 < coordinates[0][1] < -3.0

    # Unsupported strategy is rejected, not silently ignored.
    bad = client.post(
        "/api/route/optimize",
        json={
            "region_id": REGION,
            "start": START,
            "destination": DESTINATION,
            "strategies": ["teleport"],
        },
    )
    assert bad.status_code == 422


def test_route_outside_coverage_returns_no_route():
    response = client.post(
        "/api/route/optimize",
        json={
            "region_id": REGION,
            "start": {"x": 0, "y": 0},
            "destination": {"x": 1, "y": 1},
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


def test_mission_plan_budget_is_consistent():
    mission = _plan_mission()
    budget = mission["time_budget"]
    assert mission["mission_id"]
    assert mission["route"]["mission_id"] == mission["mission_id"]
    assert budget["outbound_min"] is not None
    assert budget["return_min"] == budget["outbound_min"]
    expected = round(
        budget["outbound_min"] + budget["exploration_min"] + budget["return_min"] + budget["reserve_min"],
        1,
    )
    assert budget["total_min"] == expected
    assert budget["limit_min"] == 600
    assert mission["feasibility_status"] in {"feasible", "caution", "not_feasible"}
    assert mission["assumptions"]
    assert mission["limitations"]
    assert mission["classification"] == "DERIVED"
    assert any("constant planning speed" in warning for warning in mission["warnings"])


def test_mission_plan_exceeding_limit_is_not_feasible():
    response = client.post(
        "/api/mission/plan",
        json={
            "region_id": REGION,
            "start": START,
            "destination": DESTINATION,
            "time_limit_min": 60,
            "exploration_time_min": 30,
            "reserve_time_min": 30,
            "route_strategy": "balanced",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feasibility_status"] == "not_feasible"
    assert any("exceeds" in reason for reason in body["reasons"])


def test_mission_return_uses_recorded_start():
    mission = _plan_mission()
    response = client.post(
        "/api/mission/return",
        json={
            "mission_id": mission["mission_id"],
            "current_location": DESTINATION,
            "remaining_time_min": 10000,
            "reserve_time_min": 20,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["feasibility_status"] == "feasible"
    assert body["estimated_return_min"] > 0
    assert body["return_route"]["geometry"]["coordinates"]
    assert any("recorded start" in warning for warning in body["warnings"])


def test_mission_return_unknown_mission_is_not_found():
    response = client.post(
        "/api/mission/return",
        json={
            "mission_id": "mission-does-not-exist",
            "current_location": DESTINATION,
            "remaining_time_min": 100,
        },
    )
    assert response.status_code == 404


def test_reroute_avoids_simulated_midpoint_blockage():
    mission = _plan_mission()
    coordinates = mission["route"]["geometry"]["coordinates"]
    midpoint = coordinates[len(coordinates) // 2]

    response = client.post(
        "/api/route/reroute",
        json={
            "mission_id": mission["mission_id"],
            "original_route_id": mission["route"]["id"],
            "blocked_geometry": {"type": "Point", "coordinates": midpoint},
            "scenario_status": "simulated",
            "remaining_time_min": 10000,
            "strategy": "balanced",
            "buffer_m": 1500,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scenario_status"] == "simulated"
    assert body["alternative_route"]["id"] != mission["route"]["id"]
    assert body["alternative_route"]["geometry"]["coordinates"]
    assert body["distance_delta_m"] is not None
    assert body["duration_delta_min"] is not None
    assert body["feasibility_status"] in {"feasible", "caution", "not_feasible"}
    assert any("user-supplied blockage" in warning for warning in body["warnings"])
    assert body["classification"] == "DERIVED"


def test_reroute_with_tight_budget_is_not_feasible():
    mission = _plan_mission()
    coordinates = mission["route"]["geometry"]["coordinates"]
    midpoint = coordinates[len(coordinates) // 2]
    response = client.post(
        "/api/route/reroute",
        json={
            "mission_id": mission["mission_id"],
            "original_route_id": mission["route"]["id"],
            "blocked_geometry": {"type": "Point", "coordinates": midpoint},
            "scenario_status": "simulated",
            "remaining_time_min": 1,
            "buffer_m": 1500,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feasibility_status"] == "not_feasible"
    assert any("only 1.0 min remain" in warning or "run out" in warning for warning in body["warnings"]) or body[
        "feasibility_status"
    ] == "not_feasible"


def test_report_contains_mission_terrain_and_environment_evidence():
    mission = _plan_mission()
    response = client.post("/api/mission/report", json={"mission_id": mission["mission_id"], "format": "json"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "generated"
    assert body["mission_id"] == mission["mission_id"]
    assert body["download_url"].startswith("/static/reports/")
    assert body["generated_at"]

    content = body["content"]
    assert content["mission"]["mission_id"] == mission["mission_id"]
    assert content["terrain_coverage"]["counts"]["1"] > 0
    assert content["environment"]["availability"] == "available"
    assert content["environment"]["measurements"]
    assert content["radiation"]["availability"] == "available"
    assert set(content["radiation"]["detectors"]) == {"dose_rate_B", "dose_rate_E"}
    assert content["provenance"] == ["observed", "derived"]
    assert any("simulated scenario data is excluded" in warning for warning in content["warnings"])

    report_file = settings.REPORTS_DIR / f"{body['report_id']}.json"
    assert report_file.exists()
