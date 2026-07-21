"""
Auth system tests:
  - register success
  - duplicate email rejection
  - login success
  - login wrong password
  - expired access token rejected
  - role-protected endpoint rejects wrong role
"""
from datetime import timedelta

from app.core.security import create_token


REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
UPLOAD_STATUS = "/api/v1/uploads/00000000-0000-0000-0000-000000000001/status"

USER = {"email": "test@example.com", "password": "secret123"}


# ---------- helpers ----------

def _register_and_login(client):
    client.post(REGISTER, json=USER)
    resp = client.post(LOGIN, json=USER)
    return resp.json()["access_token"]


# ---------- tests ----------

def test_register_success(client):
    resp = client.post(REGISTER, json=USER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == USER["email"]
    assert body["role"] == "viewer"
    assert "id" in body


def test_register_duplicate_email(client):
    client.post(REGISTER, json=USER)
    resp = client.post(REGISTER, json=USER)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_success(client):
    client.post(REGISTER, json=USER)
    resp = client.post(LOGIN, json=USER)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post(REGISTER, json=USER)
    resp = client.post(LOGIN, json={"email": USER["email"], "password": "wrong"})
    assert resp.status_code == 401


def test_expired_access_token_rejected(client):
    client.post(REGISTER, json=USER)
    # create a token that expired 1 second ago
    expired_token = create_token(
        subject="fake-id",
        role="viewer",
        expires_delta=timedelta(seconds=-1),
        token_type="access",
    )
    resp = client.get(ME, headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_me_returns_profile(client):
    token = _register_and_login(client)
    resp = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == USER["email"]


def test_role_protected_rejects_wrong_role(client):
    """viewer cannot POST to /uploads/ (requires admin or analyst)."""
    token = _register_and_login(client)  # registers as viewer
    resp = client.post(
        "/api/v1/uploads/",
        files={"file": ("data.csv", b"col1,col2\n1,2", "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
