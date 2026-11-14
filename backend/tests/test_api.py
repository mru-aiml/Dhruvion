from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_terrain_available():
    r = client.get("/api/terrain?region_id=gale_crater&x=137.4&y=-5.4")
    assert r.status_code == 200
    body = r.json()
    assert body["availability"] == "available"
    assert body["values"]["elevation_m"] is not None

def test_terrain_outside_coverage():
    r = client.get("/api/terrain?region_id=gale_crater&x=0&y=0")
    assert r.status_code == 200
    body = r.json()
    assert body["availability"] == "unavailable"

def test_tile_proxy():
    r = client.get("/api/tiles/mars_trek_mola_colorshade/0/0/0.png")
    assert r.status_code == 200
