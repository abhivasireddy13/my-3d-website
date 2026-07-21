"""
Tests for the AI recommendations service and the predictions API.

Covers:
- Threshold evaluation (anomaly, forecast decline, small decline, no model match)
- Claude call mocking (success, fallback on error, fallback when key absent)
- Idempotency guarantee
- Auditability fields (prompt_used, model_used, confidence_score)
- GET /api/v1/predictions/ — listing with inline recommendations
- GET /api/v1/predictions/{id}/recommendation — individual fetch
- POST /internal/pipeline-callback status="recommending" — background task execution
"""
import uuid
from datetime import datetime, timezone

import pytest

import app.services.recommendations as recs_mod
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.fact_predictions import FactPrediction
from app.models.fact_recommendations import FactRecommendation
from app.models.upload_job import UploadJob
from app.models.user import Role, User
from tests.conftest import TestingSession


# ─── Test helpers ─────────────────────────────────────────────────────────────

def _make_analyst_token(email: str = "analyst@rec.test") -> str:
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


def _make_job(status: str = "recommending") -> uuid.UUID:
    db = TestingSession()
    jid = uuid.uuid4()
    db.add(UploadJob(id=jid, filename="test.csv", status=status))
    db.commit()
    db.close()
    return jid


def _make_prediction(
    *,
    upload_job_id=None,
    model_name: str = "sales_forecast_v1",
    prediction_value: float = 1000.0,
    is_anomaly=None,
    created_at=None,
) -> uuid.UUID:
    db = TestingSession()
    pid = uuid.uuid4()
    kwargs = dict(
        prediction_id=pid,
        upload_job_id=upload_job_id,
        model_name=model_name,
        model_version="1.0",
        prediction_value=prediction_value,
        is_anomaly=is_anomaly,
    )
    if created_at is not None:
        kwargs["created_at"] = created_at
    db.add(FactPrediction(**kwargs))
    db.commit()
    db.close()
    return pid


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mock_claude_client(actions: list[str]):
    """Build a mock Anthropic client that returns the given actions as JSON."""
    import json
    from unittest.mock import MagicMock

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(actions))]
    mock_msg.model = recs_mod.CLAUDE_MODEL

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


# ─── Threshold evaluation ─────────────────────────────────────────────────────

class TestThresholdEvaluation:
    def test_non_forecast_non_anomaly_returns_none(self, monkeypatch):
        """No threshold breached → evaluate_prediction returns None."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        db = TestingSession()
        try:
            pid = _make_prediction(model_name="not_a_forecast_model", is_anomaly=None)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            result = recs_mod.evaluate_prediction(pred, db)
            assert result is None
        finally:
            db.close()

    def test_anomaly_flag_triggers_recommendation(self, monkeypatch):
        """is_anomaly=True → recommendation created, triggered_by='anomaly_detected'."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        db = TestingSession()
        try:
            pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert rec.triggered_by == "anomaly_detected"
            assert len(rec.actions) >= 2
        finally:
            db.close()

    def test_forecast_decline_above_threshold_triggers(self, monkeypatch):
        """Forecast value 20% below prior average → recommendation created."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        db = TestingSession()
        try:
            # Prior prediction at higher value
            db.add(FactPrediction(
                prediction_id=uuid.uuid4(),
                model_name="sales_forecast_v1",
                prediction_value=1000.0,
                is_anomaly=None,
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ))
            db.commit()

            new_pid = uuid.uuid4()
            db.add(FactPrediction(
                prediction_id=new_pid,
                model_name="sales_forecast_v1",
                prediction_value=800.0,  # −20%
                is_anomaly=None,
                created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            ))
            db.commit()

            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == new_pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert rec.triggered_by == "forecast_decline"
            assert float(rec.metric_delta) < -0.10
        finally:
            db.close()

    def test_small_decline_below_threshold_skipped(self, monkeypatch):
        """Forecast decline < 10% → no recommendation generated."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        db = TestingSession()
        try:
            db.add(FactPrediction(
                prediction_id=uuid.uuid4(),
                model_name="sales_forecast_v1",
                prediction_value=1000.0,
                is_anomaly=None,
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ))
            db.commit()

            new_pid = uuid.uuid4()
            db.add(FactPrediction(
                prediction_id=new_pid,
                model_name="sales_forecast_v1",
                prediction_value=960.0,  # −4% — below threshold
                is_anomaly=None,
                created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            ))
            db.commit()

            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == new_pid).first()
            result = recs_mod.evaluate_prediction(pred, db)
            assert result is None
        finally:
            db.close()

    def test_idempotency_skips_second_call(self, monkeypatch):
        """Calling evaluate_prediction twice returns the same recommendation row."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        db = TestingSession()
        try:
            pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()

            rec1 = recs_mod.evaluate_prediction(pred, db)
            rec2 = recs_mod.evaluate_prediction(pred, db)

            assert rec1 is not None and rec2 is not None
            assert str(rec1.recommendation_id) == str(rec2.recommendation_id)

            # Only one row in the DB
            count = db.query(FactRecommendation).filter(
                FactRecommendation.prediction_id == pid
            ).count()
            assert count == 1
        finally:
            db.close()


# ─── Claude integration ───────────────────────────────────────────────────────

class TestClaudeIntegration:
    def test_claude_actions_stored_on_success(self, monkeypatch):
        """When API key is set and Claude responds, status='generated', confidence=1.0."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
        expected_actions = ["Action A", "Action B", "Action C"]
        monkeypatch.setattr(recs_mod, "_get_client", lambda: _mock_claude_client(expected_actions))

        db = TestingSession()
        try:
            pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert rec.status == "generated"
            assert rec.actions == expected_actions
            assert rec.model_used == recs_mod.CLAUDE_MODEL
            assert float(rec.confidence_score) == 1.0
        finally:
            db.close()

    def test_fallback_when_claude_errors(self, monkeypatch):
        """If _get_client raises, fallback actions stored with status='fallback'."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

        def _bad_client():
            raise RuntimeError("simulated network error")

        monkeypatch.setattr(recs_mod, "_get_client", _bad_client)

        db = TestingSession()
        try:
            pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert rec.status == "fallback"
            assert float(rec.confidence_score) == 0.5
            assert rec.error_message is not None
        finally:
            db.close()

    def test_fallback_when_no_api_key(self, monkeypatch):
        """Empty ANTHROPIC_API_KEY → rule-based fallback, model_used='rule-based'."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")

        db = TestingSession()
        try:
            pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert rec.status == "fallback"
            assert "rule-based" in rec.model_used
        finally:
            db.close()

    def test_prompt_stored_for_reproducibility(self, monkeypatch):
        """prompt_used is always recorded so recommendations can be replayed."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")

        db = TestingSession()
        try:
            pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert rec.prompt_used is not None
            assert len(rec.prompt_used) > 50
            assert "anomaly" in rec.prompt_used.lower()
        finally:
            db.close()

    def test_triggered_by_and_metric_delta_recorded(self, monkeypatch):
        """Forecast-decline recommendation stores metric_delta < 0."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        db = TestingSession()
        try:
            db.add(FactPrediction(
                prediction_id=uuid.uuid4(),
                model_name="sales_forecast_v1",
                prediction_value=1000.0,
                is_anomaly=None,
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ))
            db.commit()

            new_pid = uuid.uuid4()
            db.add(FactPrediction(
                prediction_id=new_pid,
                model_name="sales_forecast_v1",
                prediction_value=800.0,
                is_anomaly=None,
                created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            ))
            db.commit()

            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == new_pid).first()
            rec = recs_mod.evaluate_prediction(pred, db)

            assert rec is not None
            assert float(rec.metric_delta) == pytest.approx(-0.2, abs=0.01)
            assert rec.metric_name == "sales_forecast_v1"
        finally:
            db.close()


# ─── Predictions API endpoints ────────────────────────────────────────────────

class TestListPredictionsAPI:
    def test_empty_list(self, client):
        token = _make_analyst_token()
        resp = client.get("/api/v1/predictions/", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["predictions"] == []

    def test_lists_all_predictions(self, client):
        token = _make_analyst_token()
        _make_prediction(model_name="forecast_model")
        _make_prediction(model_name="anomaly_detector", is_anomaly=True)

        resp = client.get("/api/v1/predictions/", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_recommendation_nested_inline(self, client, monkeypatch):
        """Predictions with recommendations include nested recommendation object."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        token = _make_analyst_token()
        pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)

        db = TestingSession()
        try:
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            recs_mod.evaluate_prediction(pred, db)
        finally:
            db.close()

        resp = client.get("/api/v1/predictions/", headers=_auth(token))
        assert resp.status_code == 200
        preds = resp.json()["predictions"]
        anomaly = next(p for p in preds if p["is_anomaly"] is True)
        assert anomaly["recommendation"] is not None
        assert isinstance(anomaly["recommendation"]["actions"], list)
        assert len(anomaly["recommendation"]["actions"]) >= 2

    def test_filter_by_upload_job_id(self, client):
        token = _make_analyst_token()
        jid = _make_job()
        _make_prediction(upload_job_id=jid, model_name="forecast_v1")
        _make_prediction(model_name="other_model")

        resp = client.get(f"/api/v1/predictions/?upload_job_id={jid}", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["predictions"][0]["upload_job_id"] == str(jid)

    def test_filter_invalid_job_id_returns_400(self, client):
        token = _make_analyst_token()
        resp = client.get("/api/v1/predictions/?upload_job_id=not-a-uuid", headers=_auth(token))
        assert resp.status_code == 400

    def test_limit_param_respected(self, client):
        token = _make_analyst_token()
        for _ in range(5):
            _make_prediction()

        resp = client.get("/api/v1/predictions/?limit=3", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/predictions/")
        assert resp.status_code == 422


class TestGetRecommendationAPI:
    def test_get_recommendation_200(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        token = _make_analyst_token()
        pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)

        db = TestingSession()
        try:
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            recs_mod.evaluate_prediction(pred, db)
        finally:
            db.close()

        resp = client.get(f"/api/v1/predictions/{pid}/recommendation", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "recommendation_id" in body
        assert body["triggered_by"] == "anomaly_detected"
        assert isinstance(body["actions"], list)
        assert len(body["actions"]) >= 2

    def test_404_when_prediction_not_found(self, client):
        token = _make_analyst_token()
        resp = client.get(
            f"/api/v1/predictions/{uuid.uuid4()}/recommendation", headers=_auth(token)
        )
        assert resp.status_code == 404

    def test_404_when_no_recommendation_exists(self, client):
        """Prediction exists but threshold was not breached → 404."""
        token = _make_analyst_token()
        pid = _make_prediction(model_name="regular_model", is_anomaly=None)

        resp = client.get(f"/api/v1/predictions/{pid}/recommendation", headers=_auth(token))
        assert resp.status_code == 404

    def test_400_for_invalid_uuid(self, client):
        token = _make_analyst_token()
        resp = client.get(
            "/api/v1/predictions/not-a-valid-uuid/recommendation", headers=_auth(token)
        )
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.get(f"/api/v1/predictions/{uuid.uuid4()}/recommendation")
        assert resp.status_code == 422

    def test_response_includes_audit_fields(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        token = _make_analyst_token()
        pid = _make_prediction(model_name="anomaly_detector", is_anomaly=True)

        db = TestingSession()
        try:
            pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pid).first()
            recs_mod.evaluate_prediction(pred, db)
        finally:
            db.close()

        resp = client.get(f"/api/v1/predictions/{pid}/recommendation", headers=_auth(token))
        body = resp.json()
        # Auditability fields
        assert "model_used" in body
        assert "triggered_by" in body
        assert "status" in body
        assert "created_at" in body
        assert body["confidence_score"] is not None


# ─── Pipeline-callback → recommendations integration ─────────────────────────

class TestPipelineCallbackRecommending:
    def _callback(self, client, job_id: str, status: str) -> dict:
        resp = client.post(
            "/internal/pipeline-callback",
            json={"job_id": job_id, "status": status, "stage": "report-ready"},
            headers={"x-internal-secret": settings.N8N_WEBHOOK_SECRET},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_recommending_transitions_job_to_done(self, client, monkeypatch):
        """After status='recommending', background task sets job.status='done'."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        jid = _make_job(status="modeling")

        result = self._callback(client, str(jid), "recommending")
        assert result["status"] == "recommending"

        # TestClient runs BackgroundTasks synchronously before returning — job should be 'done'
        db = TestingSession()
        job = db.query(UploadJob).filter(UploadJob.id == jid).first()
        db.close()
        assert job.status == "done"

    def test_recommending_generates_recs_for_anomaly_predictions(self, client, monkeypatch):
        """Background task creates FactRecommendation for each qualifying prediction."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        jid = _make_job(status="modeling")
        pid = _make_prediction(upload_job_id=jid, model_name="anomaly_detector", is_anomaly=True)

        self._callback(client, str(jid), "recommending")

        db = TestingSession()
        rec = (
            db.query(FactRecommendation)
            .filter(FactRecommendation.prediction_id == pid)
            .first()
        )
        db.close()

        assert rec is not None
        assert rec.triggered_by == "anomaly_detected"
        assert len(rec.actions) >= 2

    def test_recommending_skips_non_qualifying_predictions(self, client, monkeypatch):
        """Normal predictions (no anomaly, no decline) produce no recommendations."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        jid = _make_job(status="modeling")
        pid = _make_prediction(upload_job_id=jid, model_name="normal_model", is_anomaly=None)

        self._callback(client, str(jid), "recommending")

        db = TestingSession()
        rec = (
            db.query(FactRecommendation)
            .filter(FactRecommendation.prediction_id == pid)
            .first()
        )
        db.close()
        assert rec is None

    def test_done_status_does_not_trigger_recommendations(self, client, monkeypatch):
        """Plain status='done' must NOT trigger the recommendations background task."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        jid = _make_job(status="modeling")
        pid = _make_prediction(upload_job_id=jid, model_name="anomaly_detector", is_anomaly=True)

        self._callback(client, str(jid), "done")

        db = TestingSession()
        rec = (
            db.query(FactRecommendation)
            .filter(FactRecommendation.prediction_id == pid)
            .first()
        )
        db.close()
        assert rec is None

    def test_generate_recommendations_batch_is_idempotent(self, client, monkeypatch):
        """Calling pipeline-callback with 'recommending' twice generates only one recommendation."""
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        jid = _make_job(status="modeling")
        pid = _make_prediction(upload_job_id=jid, model_name="anomaly_detector", is_anomaly=True)

        self._callback(client, str(jid), "recommending")
        # Reset job to 'recommending' so the second callback is accepted
        db = TestingSession()
        job = db.query(UploadJob).filter(UploadJob.id == jid).first()
        job.status = "recommending"
        db.commit()
        db.close()

        self._callback(client, str(jid), "recommending")

        db = TestingSession()
        count = (
            db.query(FactRecommendation)
            .filter(FactRecommendation.prediction_id == pid)
            .count()
        )
        db.close()
        assert count == 1
