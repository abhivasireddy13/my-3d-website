"""
Test fixtures for the ML service.

Strategy
--------
- Use a temporary MLflow tracking directory so tests don't pollute the
  production SQLite DB.
- Replace the DB session with an in-memory SQLite engine so tests don't
  need a live PostgreSQL instance.
- Monkeypatch all module-level SessionLocal references so training
  functions use the test DB.
"""
import os
import tempfile
from typing import Generator

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

import mlflow


# ─── MLflow temp directory ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def temp_mlflow(tmp_path, monkeypatch):
    """Point MLflow at a temp directory for each test."""
    tracking_uri = f"sqlite:///{tmp_path}/mlflow.db"
    artifact_root = str(tmp_path / "mlruns")
    os.makedirs(artifact_root, exist_ok=True)

    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)
    monkeypatch.setenv("MLFLOW_ARTIFACT_ROOT", artifact_root)

    # Patch settings object used inside training modules.
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "MLFLOW_TRACKING_URI", tracking_uri)
    monkeypatch.setattr(cfg.settings, "MLFLOW_ARTIFACT_ROOT", artifact_root)

    mlflow.set_tracking_uri(tracking_uri)
    yield tracking_uri


# ─── In-memory SQLite DB ──────────────────────────────────────────────────────

@pytest.fixture()
def sqlite_engine():
    # StaticPool forces all connections to share one underlying connection,
    # which is required for in-memory SQLite so that tables created in one
    # call are visible to sessions created later in the same test.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create the minimal tables the training code reads from.
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE fact_sales (
                    sale_key       INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_key       INTEGER NOT NULL,
                    revenue        REAL    NOT NULL,
                    units          INTEGER NOT NULL,
                    job_id         TEXT,
                    product_key    INTEGER,
                    region_key     INTEGER,
                    customer_key   INTEGER
                )
                """
            )
        )
    return engine


@pytest.fixture()
def sqlite_session_factory(sqlite_engine):
    factory = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    return factory


@pytest.fixture()
def db_with_sales(sqlite_session_factory) -> sessionmaker:
    """Populate fact_sales with enough rows for training."""
    session: Session = sqlite_session_factory()
    rows = [
        (20230101, 1000.0, 10),
        (20230102, 1200.0, 12),
        (20230103, 1100.0, 11),
        (20230104, 1300.0, 13),
        (20230105, 1250.0, 12),
        (20230106, 1400.0, 14),
        (20230107, 1350.0, 13),
        (20230108, 1500.0, 15),
        (20230109, 1450.0, 14),
        (20230110, 1600.0, 16),
    ]
    for dk, rev, units in rows:
        session.execute(
            text(
                "INSERT INTO fact_sales (date_key, revenue, units) "
                "VALUES (:dk, :rev, :units)"
            ),
            {"dk": dk, "rev": rev, "units": units},
        )
    session.commit()
    session.close()
    return sqlite_session_factory


# ─── Minimal fact_predictions table ──────────────────────────────────────────

@pytest.fixture()
def db_with_predictions_table(sqlite_engine, sqlite_session_factory):
    """Add fact_predictions table so predict endpoints can write to it."""
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS fact_predictions (
                    prediction_id    TEXT PRIMARY KEY,
                    upload_job_id    TEXT,
                    model_name       TEXT NOT NULL,
                    model_version    TEXT,
                    prediction_value REAL,
                    is_anomaly       INTEGER,
                    region_id        INTEGER,
                    created_at       TEXT NOT NULL
                )
                """
            )
        )
    return sqlite_session_factory


# ─── FastAPI TestClient ───────────────────────────────────────────────────────

@pytest.fixture()
def client(db_with_predictions_table):
    """TestClient with DB override pointing to in-memory SQLite."""
    from app.main import app
    from app.db.postgres import get_db

    def override_get_db():
        db = db_with_predictions_table()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
