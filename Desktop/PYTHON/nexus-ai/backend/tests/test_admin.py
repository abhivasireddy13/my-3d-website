"""
Tests for the admin API.

GET /api/v1/admin/users       — list all users (admin only)
GET /api/v1/admin/jobs        — list all upload jobs (admin only)
GET /api/v1/admin/trace/{id}  — full pipeline trace (admin only)
GET /api/v1/reports/          — list generated reports (any authenticated user)
"""
import uuid

import pytest

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.fact_predictions import FactPrediction
from app.models.fact_recommendations import FactRecommendation
from app.models.report import Report
from app.models.upload_job import UploadJob
from app.models.user import Role, User
from tests.conftest import TestingSession


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_user(email: str, role: Role) -> tuple[str, str]:
    """Create user, return (id_str, jwt_token)."""
    db = TestingSession()
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        u = User(email=email, hashed_password=hash_password("P@ss1234"), role=role)
        db.add(u)
        db.commit()
        db.refresh(u)
        uid = str(u.id)
    else:
        uid = str(existing.id)
    db.close()
    return uid, create_access_token(uid, role.value)


def _make_job(status: str = "done") -> uuid.UUID:
    db = TestingSession()
    jid = uuid.uuid4()
    db.add(UploadJob(id=jid, filename="admin_test.csv", status=status))
    db.commit()
    db.close()
    return jid


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── /admin/users ─────────────────────────────────────────────────────────────

class TestAdminUsers:
    def test_admin_can_list_users(self, client):
        _, tok = _make_user("admin1@test.com", Role.admin)
        _make_user("analyst1@test.com", Role.analyst)

        resp = client.get("/api/v1/admin/users", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        emails = [u["email"] for u in body["users"]]
        assert "admin1@test.com" in emails
        assert "analyst1@test.com" in emails

    def test_user_object_contains_required_fields(self, client):
        _, tok = _make_user("admin2@test.com", Role.admin)
        resp = client.get("/api/v1/admin/users", headers=_auth(tok))
        assert resp.status_code == 200
        user = resp.json()["users"][0]
        assert {"id", "email", "role", "created_at"}.issubset(user.keys())

    def test_analyst_cannot_list_users(self, client):
        _, tok = _make_user("analyst2@test.com", Role.analyst)
        resp = client.get("/api/v1/admin/users", headers=_auth(tok))
        assert resp.status_code == 403

    def test_viewer_cannot_list_users(self, client):
        _, tok = _make_user("viewer1@test.com", Role.viewer)
        resp = client.get("/api/v1/admin/users", headers=_auth(tok))
        assert resp.status_code == 403

    def test_unauthenticated_returns_422(self, client):
        resp = client.get("/api/v1/admin/users")
        assert resp.status_code == 422


# ─── /admin/jobs ──────────────────────────────────────────────────────────────

class TestAdminJobs:
    def test_admin_can_list_jobs(self, client):
        _, tok = _make_user("admin3@test.com", Role.admin)
        _make_job("done")
        _make_job("failed")

        resp = client.get("/api/v1/admin/jobs", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        assert "jobs" in body

    def test_status_filter_works(self, client):
        _, tok = _make_user("admin4@test.com", Role.admin)
        _make_job("done")
        _make_job("failed")

        resp = client.get("/api/v1/admin/jobs?status=failed", headers=_auth(tok))
        assert resp.status_code == 200
        for job in resp.json()["jobs"]:
            assert job["status"] == "failed"

    def test_non_admin_rejected(self, client):
        _, tok = _make_user("viewer2@test.com", Role.viewer)
        resp = client.get("/api/v1/admin/jobs", headers=_auth(tok))
        assert resp.status_code == 403


# ─── /admin/trace/{job_id} ────────────────────────────────────────────────────

class TestAdminTrace:
    def test_trace_returns_job_info(self, client):
        _, tok = _make_user("admin5@test.com", Role.admin)
        jid = _make_job("done")

        resp = client.get(f"/api/v1/admin/trace/{jid}", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == str(jid)
        assert body["job"]["filename"] == "admin_test.csv"
        assert body["job"]["status"] == "done"

    def test_trace_includes_timeline(self, client):
        _, tok = _make_user("admin6@test.com", Role.admin)
        jid = _make_job("done")

        resp = client.get(f"/api/v1/admin/trace/{jid}", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        assert "timeline" in body
        assert body["event_count"] == len(body["timeline"])
        # At minimum: job_created event
        assert body["event_count"] >= 1
        types = [e["event_type"] for e in body["timeline"]]
        assert "job_created" in types

    def test_trace_includes_predictions(self, client):
        _, tok = _make_user("admin7@test.com", Role.admin)
        jid = _make_job("done")

        db = TestingSession()
        pid = uuid.uuid4()
        db.add(FactPrediction(
            prediction_id=pid,
            upload_job_id=jid,
            model_name="test_forecast",
            prediction_value=100.0,
            is_anomaly=True,
        ))
        db.commit()
        db.close()

        resp = client.get(f"/api/v1/admin/trace/{jid}", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        pred_events = [e for e in body["timeline"] if e["source"] == "fact_predictions"]
        assert len(pred_events) == 1
        assert pred_events[0]["data"]["is_anomaly"] is True

    def test_trace_includes_recommendations(self, client, monkeypatch):
        from app.core.config import settings as s
        monkeypatch.setattr(s, "ANTHROPIC_API_KEY", "")
        _, tok = _make_user("admin8@test.com", Role.admin)
        jid = _make_job("done")

        db = TestingSession()
        pid = uuid.uuid4()
        pred = FactPrediction(
            prediction_id=pid,
            upload_job_id=jid,
            model_name="anomaly_detector",
            prediction_value=99.0,
            is_anomaly=True,
        )
        db.add(pred)
        db.commit()

        import app.services.recommendations as recs_mod
        recs_mod.evaluate_prediction(pred, db)
        db.close()

        resp = client.get(f"/api/v1/admin/trace/{jid}", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        rec_events = [e for e in body["timeline"] if e["source"] == "fact_recommendations"]
        assert len(rec_events) == 1
        assert "actions" in rec_events[0]["data"]

    def test_trace_404_for_unknown_job(self, client):
        _, tok = _make_user("admin9@test.com", Role.admin)
        resp = client.get(f"/api/v1/admin/trace/{uuid.uuid4()}", headers=_auth(tok))
        assert resp.status_code == 404

    def test_trace_400_for_invalid_uuid(self, client):
        _, tok = _make_user("admin10@test.com", Role.admin)
        resp = client.get("/api/v1/admin/trace/not-a-uuid", headers=_auth(tok))
        assert resp.status_code == 400

    def test_non_admin_cannot_access_trace(self, client):
        _, tok = _make_user("analyst3@test.com", Role.analyst)
        resp = client.get(f"/api/v1/admin/trace/{uuid.uuid4()}", headers=_auth(tok))
        assert resp.status_code == 403

    def test_trace_source_counts(self, client):
        _, tok = _make_user("admin11@test.com", Role.admin)
        jid = _make_job("done")

        resp = client.get(f"/api/v1/admin/trace/{jid}", headers=_auth(tok))
        assert resp.status_code == 200
        sources = resp.json()["sources"]
        assert "upload_jobs" in sources
        assert "workflow_logs" in sources
        assert "fact_predictions" in sources
        assert "fact_recommendations" in sources


# ─── GET /api/v1/reports/ ────────────────────────────────────────────────────

class TestReportsList:
    def _make_report(self, jid: uuid.UUID) -> None:
        db = TestingSession()
        db.add(Report(
            job_id=jid,
            report_path=f"/storage/{jid}/report.pdf",
            download_url=f"/api/v1/reports/{jid}/download",
        ))
        db.commit()
        db.close()

    def test_lists_reports(self, client):
        _, tok = _make_user("analyst4@test.com", Role.analyst)
        jid = _make_job()
        self._make_report(jid)

        resp = client.get("/api/v1/reports/", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert "reports" in body

    def test_report_object_has_required_fields(self, client):
        _, tok = _make_user("analyst5@test.com", Role.analyst)
        jid = _make_job()
        self._make_report(jid)

        resp = client.get("/api/v1/reports/", headers=_auth(tok))
        r = resp.json()["reports"][0]
        assert {"report_id", "job_id", "download_url", "generated_at", "status"}.issubset(r.keys())

    def test_reports_empty_when_none_exist(self, client):
        _, tok = _make_user("analyst6@test.com", Role.analyst)
        resp = client.get("/api/v1/reports/", headers=_auth(tok))
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_pagination_works(self, client):
        _, tok = _make_user("analyst7@test.com", Role.analyst)
        for _ in range(5):
            jid = _make_job()
            self._make_report(jid)

        resp = client.get("/api/v1/reports/?per_page=3", headers=_auth(tok))
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["reports"]) <= 3

    def test_unauthenticated_returns_422(self, client):
        resp = client.get("/api/v1/reports/")
        assert resp.status_code == 422
