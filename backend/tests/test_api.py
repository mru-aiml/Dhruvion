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

def test_tile_proxy(monkeypatch):
    class FakeResponse:
        headers = {"Content-Type": "image/png"}
        body = b"\x89PNG\r\n\x1a\nfake-tile"

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    requested = {}

    def fake_urlopen(url, timeout=None):
        requested["url"] = url
        return FakeResponse()

    monkeypatch.setattr("app.api.routes.urllib.request.urlopen", fake_urlopen)
    r = client.get("/api/tiles/mars_trek_mola_colorshade/0/0/0.png")
    assert r.status_code == 200
    assert r.content == FakeResponse.body
    assert requested["url"].startswith("https://trek.nasa.gov/tiles/Mars/EQ/")
