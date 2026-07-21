"""
Tests for the reports and notifications APIs.

POST /api/v1/reports/generate/{job_id}  — generate PDF, upsert reports row
GET  /api/v1/reports/{job_id}/download  — return PDF FileResponse
POST /internal/notify                   — idempotent email notification
POST /internal/pipeline-callback        — updated: writes to workflow_logs
"""

import os
import uuid

import pytest

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.upload_job import UploadJob
from app.models.user import Role, User
from tests.conftest import TestingSession


# ─── Helpers (follow test_etl.py pattern — open, write, close, then request) ──

def _make_uploader_token(email: str = "reporter@test.com") -> str:
    """Create an uploader user and return a JWT. Session closed before returning."""
    db = TestingSession()
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        user = User(email=email, hashed_password=hash_password("P@ssw0rd1"), role=Role.analyst)
        db.add(user)
        db.commit()
        db.refresh(user)
        uid, role = str(user.id), user.role.value
    else:
        uid, role = str(existing.id), existing.role.value
    db.close()
    return create_access_token(uid, role)


def _make_done_job(filename: str = "sales.csv") -> uuid.UUID:
    """Insert a completed UploadJob row. Session closed before returning."""
    db = TestingSession()
    jid = uuid.uuid4()
    db.add(UploadJob(id=jid, filename=filename, status="done"))
    db.commit()
    db.close()
    return jid


def _make_pending_job(filename: str = "pending.csv", status: str = "validating") -> uuid.UUID:
    db = TestingSession()
    jid = uuid.uuid4()
    db.add(UploadJob(id=jid, filename=filename, status=status))
    db.commit()
    db.close()
    return jid


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Report generation ────────────────────────────────────────────────────────

class TestGenerateReport:
    def test_generate_creates_pdf_and_returns_url(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("gen1@test.com")
        job_id = _make_done_job()

        resp = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "download_url" in body
        assert "report_id" in body
        assert body["download_url"] == f"/api/v1/reports/{job_id}/download"

        # PDF file must exist on disk
        assert os.path.exists(os.path.join(str(tmp_path), str(job_id), "report.pdf"))

    def test_generate_is_idempotent(self, client, tmp_path, monkeypatch):
        """Calling generate twice returns same report_id — no duplicate DB rows."""
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("idem@test.com")
        job_id = _make_done_job()

        r1 = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        r2 = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["report_id"] == r2.json()["report_id"]

    def test_generate_404_for_unknown_job(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("notfound@test.com")
        resp = client.post(f"/api/v1/reports/generate/{uuid.uuid4()}", headers=_auth(token))
        assert resp.status_code == 404

    def test_generate_409_when_job_not_done(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("notdone@test.com")
        job_id = _make_pending_job(status="validating")

        resp = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        assert resp.status_code == 409

    def test_generate_400_for_invalid_uuid(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("baduuid@test.com")
        resp = client.post("/api/v1/reports/generate/not-a-valid-uuid", headers=_auth(token))
        assert resp.status_code == 400

    def test_generate_requires_auth(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        # Missing Authorization header → FastAPI returns 422 (required header missing)
        resp = client.post(f"/api/v1/reports/generate/{uuid.uuid4()}")
        assert resp.status_code == 422

    def test_kpis_in_response_with_fact_sales(self, client, tmp_path, monkeypatch):
        """When fact_sales rows exist for the job, KPIs reflect them."""
        from app.models.fact_sales import FactSales
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("kpi@test.com")
        job_id = _make_done_job()

        # Insert a fact_sales row via ORM so Python-level defaults (created_at) run.
        # SQLite FK constraints are off by default, so no dim_date row is needed.
        db = TestingSession()
        try:
            db.add(FactSales(
                date_key=20230101, revenue=1500.0, units=10,
                job_id=job_id, product_key=1, region_key=1, customer_key=1,
            ))
            db.commit()
        finally:
            db.close()

        resp = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["kpis"]["total_revenue"] == 1500.0
        assert body["kpis"]["total_units"] == 10
        assert body["kpis"]["n_records"] == 1

    def test_generate_returns_prediction_count(self, client, tmp_path, monkeypatch):
        """n_predictions is 0 when no fact_predictions exist for the job."""
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("pred@test.com")
        job_id = _make_done_job()

        resp = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert "n_predictions" in resp.json()


# ─── Report download ──────────────────────────────────────────────────────────

class TestDownloadReport:
    def test_download_returns_pdf(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        token = _make_uploader_token("dl@test.com")
        job_id = _make_done_job()

        # Generate first
        gen = client.post(f"/api/v1/reports/generate/{job_id}", headers=_auth(token))
        assert gen.status_code == 200

        resp = client.get(f"/api/v1/reports/{job_id}/download", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF magic bytes
        assert resp.content[:4] == b"%PDF"

    def test_download_404_if_not_generated(self, client):
        token = _make_uploader_token("nodl@test.com")
        resp = client.get(f"/api/v1/reports/{uuid.uuid4()}/download", headers=_auth(token))
        assert resp.status_code == 404

    def test_download_requires_auth(self, client):
        # Missing Authorization header → 422 (required header missing in FastAPI)
        resp = client.get(f"/api/v1/reports/{uuid.uuid4()}/download")
        assert resp.status_code == 422


# ─── Internal notify ──────────────────────────────────────────────────────────

class TestNotifyEndpoint:
    def _notify(self, client, job_id: str, subject="Test", body="Test body"):
        return client.post(
            "/internal/notify",
            json={"job_id": job_id, "subject": subject, "body": body},
            headers={"x-internal-secret": settings.N8N_WEBHOOK_SECRET},
        )

    def test_notify_skips_email_when_smtp_not_configured(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SMTP_USER", "")
        job_id = str(uuid.uuid4())
        resp = self._notify(client, job_id)
        assert resp.status_code == 200
        assert resp.json()["sent"] is False
        assert "not configured" in resp.json()["message"].lower()

    def test_notify_is_idempotent(self, client, monkeypatch, mock_mongo):
        monkeypatch.setattr(settings, "SMTP_USER", "")
        job_id = str(uuid.uuid4())

        # Seed workflow_logs mock with an existing notification-sent entry
        # The mock's find_one looks up by job_id key
        mock_mongo[job_id] = {
            "job_id": job_id,
            "stage": "notification-sent",
            "status": "sent",
        }

        resp = self._notify(client, job_id)
        assert resp.status_code == 200
        assert resp.json()["sent"] is False
        assert "already" in resp.json()["message"].lower()

    def test_notify_rejects_wrong_secret(self, client):
        resp = client.post(
            "/internal/notify",
            json={"job_id": str(uuid.uuid4()), "subject": "X", "body": "Y"},
            headers={"x-internal-secret": "wrong_secret"},
        )
        assert resp.status_code == 401

    def test_notify_rejects_missing_secret(self, client):
        resp = client.post(
            "/internal/notify",
            json={"job_id": str(uuid.uuid4()), "subject": "X", "body": "Y"},
        )
        assert resp.status_code == 401


# ─── Pipeline callback (updated with workflow_logs audit) ────────────────────

class TestPipelineCallbackAudit:
    def test_callback_updates_job_status(self, client):
        jid = _make_pending_job(status="validating")
        resp = client.post(
            "/internal/pipeline-callback",
            json={"job_id": str(jid), "status": "done"},
            headers={"x-internal-secret": settings.N8N_WEBHOOK_SECRET},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

        db = TestingSession()
        job = db.query(UploadJob).filter(UploadJob.id == jid).first()
        db.close()
        assert job.status == "done"

    def test_callback_accepts_extra_metadata(self, client):
        jid = _make_pending_job(status="cleaning")
        resp = client.post(
            "/internal/pipeline-callback",
            json={
                "job_id": str(jid),
                "status": "modeling",
                "stage": "etl-complete",
                "metadata": {"n_rows": 42},
            },
            headers={"x-internal-secret": settings.N8N_WEBHOOK_SECRET},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_callback_rejects_wrong_secret(self, client):
        jid = _make_pending_job(status="cleaning")
        resp = client.post(
            "/internal/pipeline-callback",
            json={"job_id": str(jid), "status": "done"},
            headers={"x-internal-secret": "bad_secret"},
        )
        assert resp.status_code == 401

    def test_callback_404_for_unknown_job(self, client):
        resp = client.post(
            "/internal/pipeline-callback",
            json={"job_id": str(uuid.uuid4()), "status": "done"},
            headers={"x-internal-secret": settings.N8N_WEBHOOK_SECRET},
        )
        assert resp.status_code == 404


# ─── Internal generate-report endpoint ───────────────────────────────────────

class TestInternalGenerateReport:
    def _secret(self) -> dict:
        return {"x-internal-secret": settings.N8N_WEBHOOK_SECRET}

    def test_internal_generate_creates_report(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        job_id = _make_done_job()

        resp = client.post(f"/internal/generate-report/{job_id}", headers=self._secret())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "download_url" in body
        assert body["download_url"] == f"/api/v1/reports/{job_id}/download"
        assert os.path.exists(os.path.join(str(tmp_path), str(job_id), "report.pdf"))

    def test_internal_generate_is_idempotent(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        job_id = _make_done_job()

        r1 = client.post(f"/internal/generate-report/{job_id}", headers=self._secret())
        r2 = client.post(f"/internal/generate-report/{job_id}", headers=self._secret())
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["report_id"] == r2.json()["report_id"]

    def test_internal_generate_rejects_wrong_secret(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        job_id = _make_done_job()
        resp = client.post(f"/internal/generate-report/{job_id}",
                           headers={"x-internal-secret": "wrong"})
        assert resp.status_code == 401

    def test_internal_generate_409_when_not_done(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        job_id = _make_pending_job(status="validating")
        resp = client.post(f"/internal/generate-report/{job_id}", headers=self._secret())
        assert resp.status_code == 409

    def test_internal_generate_404_for_unknown_job(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
        resp = client.post(f"/internal/generate-report/{uuid.uuid4()}", headers=self._secret())
        assert resp.status_code == 404
