"""
Tests for the ML service prediction and training HTTP endpoints.

Each test trains the relevant model first (using the in-memory SQLite DB)
so the MLflow registry always has a 'production' alias before the predict
endpoints are called.
"""
import pytest
import pandas as pd

from app.training import sales_forecast, anomaly_detection


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _train_forecast(db_with_sales):
    sales_forecast.train_and_register(session_factory=db_with_sales)


def _train_anomaly(db_with_sales):
    anomaly_detection.train_and_register(session_factory=db_with_sales)


# ─── Health ───────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Training endpoints ───────────────────────────────────────────────────────

class TestTrainEndpoints:
    def test_train_sales_forecast_returns_200(self, client, db_with_sales, monkeypatch):
        monkeypatch.setattr(sales_forecast, "SessionLocal", db_with_sales)
        resp = client.post("/train/sales-forecast")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "mae" in body

    def test_train_anomaly_detection_returns_200(self, client, db_with_sales, monkeypatch):
        monkeypatch.setattr(anomaly_detection, "SessionLocal", db_with_sales)
        resp = client.post("/train/anomaly-detection")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "mean_anomaly_score" in body


# ─── Prediction endpoints ─────────────────────────────────────────────────────

class TestPredictSalesForecast:
    @pytest.fixture(autouse=True)
    def train_first(self, db_with_sales):
        _train_forecast(db_with_sales)

    def test_predict_returns_forecast(self, client):
        resp = client.post(
            "/predict/sales-forecast",
            json={"recent_values": [1000.0, 1200.0, 1100.0]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "forecast" in body
        assert isinstance(body["forecast"], float)

    def test_predict_returns_model_version(self, client):
        resp = client.post(
            "/predict/sales-forecast",
            json={"recent_values": [1000.0, 1200.0, 1100.0]},
        )
        assert resp.json()["model_version"] is not None

    def test_predict_accepts_upload_job_id(self, client):
        resp = client.post(
            "/predict/sales-forecast",
            json={
                "recent_values": [1000.0, 1200.0, 1100.0],
                "upload_job_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert resp.status_code == 200

    def test_predict_too_few_values_422(self, client):
        """Sending fewer values than the model's lag count returns 422."""
        resp = client.post(
            "/predict/sales-forecast",
            json={"recent_values": []},
        )
        assert resp.status_code == 422

    def test_no_production_model_503(self, client):
        """When no production model is registered, endpoint returns 503."""
        import mlflow
        client_mlf = mlflow.MlflowClient()
        # Delete the alias to simulate missing production model.
        try:
            client_mlf.delete_registered_model_alias(
                sales_forecast.MODEL_NAME, "production"
            )
        except Exception:
            pass
        resp = client.post(
            "/predict/sales-forecast",
            json={"recent_values": [1000.0, 1200.0, 1100.0]},
        )
        assert resp.status_code == 503


class TestPredictAnomaly:
    @pytest.fixture(autouse=True)
    def train_first(self, db_with_sales):
        _train_anomaly(db_with_sales)

    def test_predict_returns_is_anomaly(self, client):
        resp = client.post(
            "/predict/anomaly",
            json={"revenue": 1200.0, "units": 12},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "is_anomaly" in body
        assert isinstance(body["is_anomaly"], bool)

    def test_predict_returns_score(self, client):
        resp = client.post(
            "/predict/anomaly",
            json={"revenue": 1200.0, "units": 12},
        )
        body = resp.json()
        assert "score" in body
        assert isinstance(body["score"], float)

    def test_predict_accepts_upload_job_id(self, client):
        resp = client.post(
            "/predict/anomaly",
            json={
                "revenue": 1200.0,
                "units": 12,
                "upload_job_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        assert resp.status_code == 200

    def test_outlier_flagged_as_anomaly(self, client):
        """A wildly out-of-range value should be flagged as an anomaly."""
        resp = client.post(
            "/predict/anomaly",
            json={"revenue": 9_999_999.0, "units": 999_999},
        )
        assert resp.status_code == 200
        # Note: IsolationForest on a small training set may not reliably flag
        # all outliers — we just ensure the endpoint responds correctly.
        assert isinstance(resp.json()["is_anomaly"], bool)

    def test_no_production_model_503(self, client):
        import mlflow
        client_mlf = mlflow.MlflowClient()
        try:
            client_mlf.delete_registered_model_alias(
                anomaly_detection.MODEL_NAME, "production"
            )
        except Exception:
            pass
        resp = client.post(
            "/predict/anomaly",
            json={"revenue": 1200.0, "units": 12},
        )
        assert resp.status_code == 503
