from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_MISSION = {
    "name": "Gale Traverse Alpha",
    "description": "Persistent mission test",
    "region_id": "gale_crater",
    "mission_type": "traverse",
    "start": {"x": 137.2, "y": -4.5},
    "destination": {"x": 137.3, "y": -4.55},
    "time_budget_min": 600,
    "objectives": ["Reach science target", "Return safely"],
    "notes": "Created by automated test",
    "status": "draft",
}


def test_create_mission():
    response = client.post("/api/missions", json=VALID_MISSION)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == VALID_MISSION["name"]
    assert body["id"]
    assert body["region_id"] == "gale_crater"
    assert body["start"]["x"] == 137.2
    assert body["destination"]["y"] == -4.55
    assert body["status"] == "draft"
    assert body["created_at"]
    return body["id"]


def test_list_missions():
    created_id = test_create_mission()
    response = client.get("/api/missions")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert created_id in ids


def test_get_mission():
    created_id = test_create_mission()
    response = client.get(f"/api/missions/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id


def test_update_mission():
    created_id = test_create_mission()
    response = client.patch(
        f"/api/missions/{created_id}",
        json={"name": "Renamed Mission", "status": "planned", "time_budget_min": 480},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Renamed Mission"
    assert body["status"] == "planned"
    assert body["time_budget_min"] == 480


def test_delete_draft_mission():
    created_id = test_create_mission()
    response = client.delete(f"/api/missions/{created_id}")
    assert response.status_code == 204
    assert client.get(f"/api/missions/{created_id}").status_code == 404


def test_delete_active_mission_blocked():
    created_id = test_create_mission()
    client.patch(f"/api/missions/{created_id}", json={"status": "active"})
    response = client.delete(f"/api/missions/{created_id}")
    assert response.status_code == 409


def test_create_mission_missing_name():
    payload = dict(VALID_MISSION)
    del payload["name"]
    response = client.post("/api/missions", json=payload)
    assert response.status_code == 422


def test_create_mission_invalid_coordinates():
    payload = dict(VALID_MISSION)
    payload["start"] = {"x": 0.0, "y": 0.0}
    response = client.post("/api/missions", json=payload)
    assert response.status_code == 422


def test_create_mission_out_of_coverage_destination():
    payload = dict(VALID_MISSION)
    payload["destination"] = {"x": 1.0, "y": 1.0}
    response = client.post("/api/missions", json=payload)
    assert response.status_code == 422


def test_create_mission_unsupported_region():
    payload = dict(VALID_MISSION)
    payload["region_id"] = "mars_unknown"
    response = client.post("/api/missions", json=payload)
    assert response.status_code == 422


def test_get_unknown_mission():
    response = client.get("/api/missions/does-not-exist")
    assert response.status_code == 404


def test_filter_and_search():
    mid = test_create_mission()
    client.patch(f"/api/missions/{mid}", json={"status": "planned", "name": "Filterable Mission"})
    response = client.get("/api/missions?status=planned&search=Filterable")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert mid in ids
    response2 = client.get("/api/missions?status=draft&search=Filterable")
    assert mid not in [item["id"] for item in response2.json()]


def test_mission_plan_route_integration():
    created_id = test_create_mission()
    response = client.post(f"/api/missions/{created_id}/plan", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mission_id"] == created_id
    assert body["route"]["distance_m"] > 0
    assert body["feasibility_status"] in {"feasible", "caution", "not_feasible"}


def test_mission_report_integration():
    created_id = test_create_mission()
    client.post(f"/api/missions/{created_id}/plan", json={})
    response = client.post(f"/api/missions/{created_id}/report", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mission"]["mission_id"] == created_id
    assert body["status"] == "generated"
    assert body["download_url"]