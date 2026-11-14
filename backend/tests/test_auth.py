import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_password, verify_password

client = TestClient(app)

def _email():
    return f"{uuid.uuid4().hex}@example.com"

def test_register_and_me():
    email = _email()
    r = client.post("/api/auth/register", json={"full_name": "A", "email": email, "password": "password123"})
    assert r.status_code == 201
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    data = r2.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == email

def test_duplicate_email():
    email = _email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 409

def test_invalid_email():
    r = client.post("/api/auth/register", json={"email": "not-an-email", "password": "password123"})
    assert r.status_code == 422

def test_password_hashing():
    h = hash_password("secret")
    assert h != "secret"
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)

def test_login_success_and_wrong_password():
    email = _email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    r = client.post("/api/auth/login", json={"email": email, "password": "wrongpass"})
    assert r.status_code == 401

def test_unauthenticated_me():
    c = TestClient(app)
    r = c.get("/api/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["authenticated"] is False

def test_logout():
    c = TestClient(app)
    email = _email()
    c.post("/api/auth/register", json={"email": email, "password": "password123"})
    r = c.post("/api/auth/logout")
    assert r.status_code == 200
    r = c.get("/api/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["authenticated"] is False