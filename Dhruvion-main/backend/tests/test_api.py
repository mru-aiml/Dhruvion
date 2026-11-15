from fastapi.testclient import TestClient
from app.main import app
from app.api import routes

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_terrain_available_when_raster_adapter_returns_values(monkeypatch):
    values = iter([-4500.0, 4.2, 0.3])
    monkeypatch.setattr(routes, "_sample", lambda *_: next(values))

    r = client.get("/api/terrain?region_id=gale_crater&x=137.4&y=-5.4")
    assert r.status_code == 200
    body = r.json()
    assert body["availability"] == "available"
    assert body["values"] == {"elevation_m": -4500.0, "slope_deg": 4.2, "roughness": 0.3}
    assert body["values"]["elevation_m"] is not None

def test_terrain_outside_coverage():
    r = client.get("/api/terrain?region_id=gale_crater&x=0&y=0")
    assert r.status_code == 200
    body = r.json()
    assert body["availability"] == "unavailable"

def test_tile_proxy_uses_the_configured_provider_without_network(monkeypatch):
    class FakeTileResponse:
        headers = {"Content-Type": "image/jpeg"}

        def read(self):
            return b"fake-tile"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(routes.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeTileResponse())

    r = client.get("/api/tiles/mars_trek_mola_colorshade/0/0/0.png")
    assert r.status_code == 200
    assert r.content == b"fake-tile"
    assert r.headers["content-type"] == "image/jpeg"
