"""
Tests for the analytics / Superset embedding API.

GET /api/v1/analytics/dashboards  — list pre-provisioned dashboards
GET /api/v1/analytics/embed-token — get guest token from Superset

Superset calls are mocked via monkeypatch so no running Superset instance
is needed. The internal embed-token endpoint is tested for secret enforcement.
"""
import uuid

import pytest
import httpx

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.user import Role, User
from tests.conftest import TestingSession


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_user_token(email: str = "analytics@test.com") -> str:
    db = TestingSession()
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        user = User(email=email, hashed_password=hash_password("P@ss!1"), role=Role.analyst)
        db.add(user)
        db.commit()
        db.refresh(user)
        uid, role = str(user.id), user.role.value
    else:
        uid, role = str(existing.id), existing.role.value
    db.close()
    return create_access_token(uid, role)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


FAKE_GUEST_TOKEN = "fake.guest.jwt.token"
FAKE_ACCESS_TOKEN = "fake.admin.access.token"


# ─── Mock Superset HTTP calls ────────────────────────────────────────────────

@pytest.fixture
def mock_superset(monkeypatch):
    """
    Replace outbound httpx calls to Superset with fixed responses.
    Uses pytest's monkeypatch to patch the analytics module's httpx.AsyncClient.
    """
    import app.api.v1.analytics as analytics_mod

    async def _mock_login(*args, **kwargs):
        return httpx.Response(200, json={"access_token": FAKE_ACCESS_TOKEN})

    async def _mock_guest_token(*args, **kwargs):
        return httpx.Response(200, json={"token": FAKE_GUEST_TOKEN})

    class _MockClient:
        def __init__(self, *args, **kwargs): pass

        async def __aenter__(self): return self

        async def __aexit__(self, *a): pass

        async def post(self, url, **kwargs):
            if "/security/login" in url:
                return httpx.Response(200, json={"access_token": FAKE_ACCESS_TOKEN})
            if "/security/guest_token" in url:
                return httpx.Response(200, json={"token": FAKE_GUEST_TOKEN})
            return httpx.Response(404, json={"detail": "not found"})

    monkeypatch.setattr(analytics_mod.httpx, "AsyncClient", _MockClient)
    return _MockClient


@pytest.fixture
def mock_superset_down(monkeypatch):
    """Superset is unreachable — all requests raise ConnectionError."""
    import app.api.v1.analytics as analytics_mod

    class _DownClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(analytics_mod.httpx, "AsyncClient", _DownClient)
    return _DownClient


# ─── Dashboard list endpoint ──────────────────────────────────────────────────

class TestListDashboards:
    def test_returns_three_dashboards(self, client):
        token = _make_user_token("list@test.com")
        resp = client.get("/api/v1/analytics/dashboards", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "dashboards" in body
        assert len(body["dashboards"]) == 3

    def test_includes_expected_slugs(self, client):
        token = _make_user_token("slugs@test.com")
        resp = client.get("/api/v1/analytics/dashboards", headers=_auth(token))
        slugs = {d["slug"] for d in resp.json()["dashboards"]}
        assert slugs == {"exec-overview", "sales-deep-dive", "anomaly-monitor"}

    def test_includes_superset_url(self, client):
        token = _make_user_token("url@test.com")
        resp = client.get("/api/v1/analytics/dashboards", headers=_auth(token))
        assert "superset_url" in resp.json()

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/analytics/dashboards")
        assert resp.status_code == 422  # missing Authorization header


# ─── Embed-token endpoint ──────────────────────────────────────────────────────

class TestEmbedToken:
    def test_returns_guest_token(self, client, mock_superset):
        token = _make_user_token("embed@test.com")
        resp = client.get(
            "/api/v1/analytics/embed-token?dashboard_id=exec-overview",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "token" in body
        assert body["token"] == FAKE_GUEST_TOKEN
        assert "embed_url" in body
        assert "expires_in" in body

    def test_accepts_slug(self, client, mock_superset):
        token = _make_user_token("slug_embed@test.com")
        for slug in ("exec-overview", "sales-deep-dive", "anomaly-monitor"):
            resp = client.get(
                f"/api/v1/analytics/embed-token?dashboard_id={slug}",
                headers=_auth(token),
            )
            assert resp.status_code == 200, f"Slug {slug!r}: {resp.text}"

    def test_accepts_uuid(self, client, mock_superset):
        token = _make_user_token("uuid_embed@test.com")
        resp = client.get(
            f"/api/v1/analytics/embed-token"
            f"?dashboard_id={settings.SUPERSET_DASH_EXEC_UUID}",
            headers=_auth(token),
        )
        assert resp.status_code == 200

    def test_rejects_unknown_dashboard(self, client, mock_superset):
        token = _make_user_token("unknown@test.com")
        resp = client.get(
            "/api/v1/analytics/embed-token?dashboard_id=does-not-exist",
            headers=_auth(token),
        )
        assert resp.status_code == 400

    def test_requires_auth(self, client, mock_superset):
        resp = client.get("/api/v1/analytics/embed-token?dashboard_id=exec-overview")
        assert resp.status_code == 422

    def test_superset_down_returns_503(self, client, mock_superset_down):
        token = _make_user_token("down@test.com")
        resp = client.get(
            "/api/v1/analytics/embed-token?dashboard_id=exec-overview",
            headers=_auth(token),
        )
        assert resp.status_code == 503

    def test_embed_url_contains_dashboard_uuid(self, client, mock_superset):
        token = _make_user_token("url_check@test.com")
        resp = client.get(
            "/api/v1/analytics/embed-token?dashboard_id=exec-overview",
            headers=_auth(token),
        )
        body = resp.json()
        # embed_url must include the exec UUID
        assert settings.SUPERSET_DASH_EXEC_UUID in body["embed_url"]

    def test_response_includes_all_fields(self, client, mock_superset):
        token = _make_user_token("fields@test.com")
        resp = client.get(
            "/api/v1/analytics/embed-token?dashboard_id=anomaly-monitor",
            headers=_auth(token),
        )
        body = resp.json()
        for field in ("token", "dashboard_id", "expires_in", "embed_url"):
            assert field in body, f"Missing field: {field}"


# ─── Internal embed-token (x-internal-secret, no JWT) ────────────────────────

class TestInternalEmbedToken:
    def _secret_header(self) -> dict:
        return {"x-internal-secret": settings.N8N_WEBHOOK_SECRET}

    def test_returns_token_with_valid_secret(self, client, mock_superset):
        resp = client.get(
            "/api/v1/analytics/internal/embed-token?dashboard_id=exec-overview",
            headers=self._secret_header(),
        )
        assert resp.status_code == 200
        assert resp.json()["token"] == FAKE_GUEST_TOKEN

    def test_rejects_wrong_secret(self, client, mock_superset):
        resp = client.get(
            "/api/v1/analytics/internal/embed-token?dashboard_id=exec-overview",
            headers={"x-internal-secret": "wrong"},
        )
        assert resp.status_code == 401

    def test_rejects_missing_secret(self, client, mock_superset):
        resp = client.get(
            "/api/v1/analytics/internal/embed-token?dashboard_id=exec-overview"
        )
        assert resp.status_code == 401

    def test_rejects_unknown_dashboard(self, client, mock_superset):
        resp = client.get(
            "/api/v1/analytics/internal/embed-token?dashboard_id=bad-id",
            headers=self._secret_header(),
        )
        assert resp.status_code == 400
