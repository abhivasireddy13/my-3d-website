"""
ETL pipeline tests.

Coverage:
- Valid CSV → all stages complete → status "done", sales_data rows persisted
- CSV with missing required columns → status "failed" at validating
- CSV where every row has bad data → status "failed" at cleaning
- Duplicate dates are deduplicated (only one row per date stored)
- GET /uploads/{id}/result returns recommendation after done
- Phase 2 backward compat: POST /uploads/ still returns job_id + status immediately
"""

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.security import create_access_token, hash_password
from app.models.sales_data import SalesData
from app.models.upload_job import UploadJob
from app.models.user import Role, User

from tests.conftest import TestingSession

# ─── CSV fixtures ──────────────────────────────────────────────────────────────

VALID_CSV = (
    b"date,revenue,units\n"
    b"2024-01-01,100.00,10\n"
    b"2024-01-02,150.00,15\n"
    b"2024-01-03,120.00,12\n"
)

# Should fail at validating — "units" column renamed to "qty"
MISSING_COLUMN_CSV = (
    b"date,revenue,qty\n"
    b"2024-01-01,100,10\n"
    b"2024-01-02,150,15\n"
)

# All rows have non-parseable dates and non-numeric revenue → fail at cleaning
BAD_DATA_CSV = (
    b"date,revenue,units\n"
    b"not-a-date,not-a-number,abc\n"
    b"also-bad,xyz,def\n"
)

# Three rows but two share the same date → only 2 unique rows stored
DUPLICATE_DATES_CSV = (
    b"date,revenue,units\n"
    b"2024-01-01,100.00,10\n"
    b"2024-01-01,200.00,20\n"  # duplicate — should be dropped
    b"2024-01-02,150.00,15\n"
)

UPLOAD_URL = "/api/v1/uploads/"

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_csv(tmp_path):
    """Return a factory that writes CSV bytes to a temp file and returns the path."""

    def _make(content: bytes, name: str = "test.csv") -> str:
        p = tmp_path / name
        p.write_bytes(content)
        return str(p)

    return _make


@pytest.fixture
def admin_token():
    """Create an admin user directly in the test DB and return a valid JWT."""
    db = TestingSession()
    user = User(
        email="admin@etl.test",
        hashed_password=hash_password("secret"),
        role=Role.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), "admin")
    db.close()
    return token


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _upload(client, auth_headers, csv_bytes: bytes, filename="test.csv"):
    return client.post(
        UPLOAD_URL,
        files={"file": (filename, csv_bytes, "text/csv")},
        headers=auth_headers,
    )


def _job_from_db(job_id: str) -> UploadJob:
    db = TestingSession()
    job = db.query(UploadJob).filter(UploadJob.id == uuid.UUID(job_id)).first()
    db.close()
    return job


def _sales_rows_for_job(job_id: str) -> list[SalesData]:
    db = TestingSession()
    rows = (
        db.query(SalesData)
        .filter(SalesData.job_id == uuid.UUID(job_id))
        .order_by(SalesData.sale_date)
        .all()
    )
    db.close()
    return rows


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_valid_csv_completes_all_stages(client, auth_headers, tmp_csv, mock_mongo):
    """Full happy path: valid CSV → done, 3 rows in sales_data."""
    # Write CSV to a real file so the ETL stage can open it
    file_path = tmp_csv(VALID_CSV)

    resp = _upload(client, auth_headers, VALID_CSV)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "job_id" in body

    job_id = body["job_id"]

    # BackgroundTasks run synchronously in TestClient
    job = _job_from_db(job_id)
    assert job.status == "done", f"Expected done, got: {job.status} | {job.error_detail}"

    rows = _sales_rows_for_job(job_id)
    assert len(rows) == 3
    assert float(rows[0].revenue) == 100.00
    assert rows[0].units == 10
    assert str(rows[1].sale_date) == "2024-01-02"

    # Recommendation should be in the mock MongoDB store
    assert job_id in mock_mongo, "pipeline_results document missing"
    doc = mock_mongo[job_id]
    assert "summary" in doc
    assert "stats" in doc
    assert doc["stats"]["row_count"] == 3


def test_missing_required_column_fails_at_validating(client, auth_headers, tmp_csv):
    """CSV missing 'units' column → job failed at validating stage."""
    resp = _upload(client, auth_headers, MISSING_COLUMN_CSV)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    job = _job_from_db(job_id)
    assert job.status == "failed"
    assert job.error_detail["stage"] == "validating"
    assert "units" in job.error_detail["detail"]

    # No rows should be stored
    assert _sales_rows_for_job(job_id) == []


def test_all_rows_invalid_fails_at_cleaning(client, auth_headers, tmp_csv):
    """CSV where every row has unparseable values → failed at cleaning."""
    resp = _upload(client, auth_headers, BAD_DATA_CSV)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    job = _job_from_db(job_id)
    assert job.status == "failed"
    assert job.error_detail["stage"] == "cleaning"

    assert _sales_rows_for_job(job_id) == []


def test_duplicate_dates_are_deduplicated(client, auth_headers, tmp_csv):
    """Three CSV rows with two sharing a date → only 2 rows stored."""
    resp = _upload(client, auth_headers, DUPLICATE_DATES_CSV)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    job = _job_from_db(job_id)
    assert job.status == "done", job.error_detail

    rows = _sales_rows_for_job(job_id)
    assert len(rows) == 2  # duplicate date dropped
    assert str(rows[0].sale_date) == "2024-01-01"
    assert str(rows[1].sale_date) == "2024-01-02"


def test_result_endpoint_returns_recommendation(client, auth_headers, mock_mongo):
    """GET /uploads/{id}/result returns the stats doc after pipeline completes."""
    resp = _upload(client, auth_headers, VALID_CSV)
    job_id = resp.json()["job_id"]

    # Populate mock_mongo so find_one returns the document
    # (the ETL already did this via the autouse fixture's replace_one)
    result_resp = client.get(
        f"/api/v1/uploads/{job_id}/result",
        headers=auth_headers,
    )
    assert result_resp.status_code == 200, result_resp.text
    data = result_resp.json()
    assert "summary" in data
    assert "stats" in data
    assert data["stats"]["row_count"] == 3


def test_result_endpoint_409_if_not_done(client, auth_headers):
    """GET /result on a job still validating returns 409 Conflict."""
    # Create a job directly in the DB with status "validating"
    db = TestingSession()
    job = UploadJob(filename="pending.csv", status="validating")
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = str(job.id)
    db.close()

    resp = client.get(
        f"/api/v1/uploads/{job_id}/result",
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "not yet complete" in resp.json()["detail"]


def test_phase2_upload_returns_job_id_and_validating_status(client, auth_headers):
    """Backward compat: POST /uploads/ still returns job_id + status immediately."""
    resp = _upload(client, auth_headers, VALID_CSV)
    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body
    # The response always says "validating" (set synchronously before bg task runs)
    assert body["status"] == "validating"


def test_upload_rejects_non_csv(client, auth_headers):
    """Non-CSV extension is rejected before ETL runs (Phase 2 behaviour unchanged)."""
    resp = client.post(
        UPLOAD_URL,
        files={"file": ("data.json", b'{"a":1}', "application/json")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "CSV" in resp.json()["detail"]


def test_viewer_cannot_upload(client):
    """Viewer role is still forbidden from uploading (Phase 1 RBAC unchanged)."""
    # Register as viewer
    client.post("/api/v1/auth/register", json={"email": "v@test.com", "password": "x"})
    token = client.post(
        "/api/v1/auth/login", json={"email": "v@test.com", "password": "x"}
    ).json()["access_token"]
    resp = _upload(client, {"Authorization": f"Bearer {token}"}, VALID_CSV)
    assert resp.status_code == 403
