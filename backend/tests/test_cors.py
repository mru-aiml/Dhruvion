"""CORS middleware tests for production frontend origin."""
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

PRODUCTION_ORIGIN = "https://dhruvion.vercel.app"
DEVELOPMENT_ORIGIN = "http://localhost:5173"
UNAUTHORIZED_ORIGIN = "https://evil.example.com"


def test_cors_preflight_register():
    """OPTIONS preflight for /api/auth/register from production origin."""
    response = client.options(
        "/api/auth/register",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")
    assert "content-type" in response.headers.get("access-control-allow-headers", "").lower()


def test_cors_preflight_login():
    """OPTIONS preflight for /api/auth/login from production origin."""
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_me():
    """OPTIONS preflight for /api/auth/me from production origin."""
    response = client.options(
        "/api/auth/me",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_post_register_from_production_origin():
    """POST /api/auth/register from production origin includes CORS headers."""
    import uuid
    email = f"{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"full_name": "Test", "email": email, "password": "password123"},
        headers={"Origin": PRODUCTION_ORIGIN},
    )
    assert response.status_code == 201
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_post_login_from_production_origin():
    """POST /api/auth/login from production origin includes CORS headers."""
    import uuid
    email = f"{uuid.uuid4().hex}@example.com"
    # Register first
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    # Login from production origin
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
        headers={"Origin": PRODUCTION_ORIGIN},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_get_me_from_production_origin():
    """GET /api/auth/me from production origin includes CORS headers."""
    response = client.get("/api/auth/me", headers={"Origin": PRODUCTION_ORIGIN})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_error_response_includes_headers():
    """Error responses from production origin include CORS headers."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrongpass"},
        headers={"Origin": PRODUCTION_ORIGIN},
    )
    assert response.status_code == 401
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_unauthorized_origin_rejected():
    """Requests from unauthorized origin do not get CORS headers."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"},
        headers={"Origin": UNAUTHORIZED_ORIGIN},
    )
    # The request may succeed or fail, but CORS headers should not allow the unauthorized origin
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != UNAUTHORIZED_ORIGIN
    # Should not have credentials allowed for unauthorized origin
    if allow_origin:
        assert response.headers.get("access-control-allow-credentials") != "true"


def test_cors_development_origin_allowed():
    """Development origin is still allowed."""
    response = client.options(
        "/api/auth/register",
        headers={
            "Origin": DEVELOPMENT_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == DEVELOPMENT_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_allowed_origins_include_production():
    """Settings allowed_origins includes production origin."""
    assert PRODUCTION_ORIGIN in settings.allowed_origins
    assert DEVELOPMENT_ORIGIN in settings.allowed_origins


def test_cors_preflight_generic_endpoint():
    """OPTIONS preflight for generic API endpoint from production origin."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"