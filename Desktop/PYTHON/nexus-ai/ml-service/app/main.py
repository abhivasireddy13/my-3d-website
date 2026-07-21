"""
NEXUS AI — ML Service

Endpoints
---------
GET  /health
POST /train/sales-forecast    — trigger training + MLflow registration
POST /train/anomaly-detection — trigger training + MLflow registration
POST /predict/sales-forecast  — load production model from registry, predict
POST /predict/anomaly         — load production model from registry, predict
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import mlflow
import mlflow.sklearn
import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import configure_logging, set_correlation_id
from app.db.postgres import SessionLocal, get_db
from app.training import anomaly_detection, sales_forecast

configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="NEXUS AI - ML Service", version="1.0.0")


class _CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = cid
        return response


app.add_middleware(_CorrelationMiddleware)

# ─── MLflow helpers ───────────────────────────────────────────────────────────

def _load_production_model(model_name: str):
    """Load the production alias model from the MLflow registry."""
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    uri = f"models:/{model_name}@production"
    try:
        return mlflow.sklearn.load_model(uri)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No production model registered for '{model_name}'. "
                f"Trigger POST /train/{model_name.removeprefix('nexus-')} first. "
                f"Inner error: {exc}"
            ),
        )


def _get_model_version(model_name: str) -> Optional[str]:
    """Return the version string of the current production alias, or None."""
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    try:
        client = mlflow.MlflowClient()
        mv = client.get_model_version_by_alias(model_name, "production")
        return str(mv.version)
    except Exception:
        return None


# ─── Fact predictions writer ──────────────────────────────────────────────────

def _write_prediction(
    db: Session,
    *,
    model_name: str,
    model_version: Optional[str],
    prediction_value: Optional[float],
    is_anomaly: Optional[bool],
    upload_job_id: Optional[str],
) -> None:
    """Insert a row into fact_predictions (best-effort, non-fatal on failure)."""
    try:
        from sqlalchemy import text

        db.execute(
            text(
                """
                INSERT INTO fact_predictions
                  (prediction_id, upload_job_id, model_name, model_version,
                   prediction_value, is_anomaly, created_at)
                VALUES
                  (:pid, :job_id, :model_name, :model_version,
                   :pred_val, :is_anomaly, :now)
                """
            ),
            {
                "pid": str(uuid.uuid4()),
                "job_id": upload_job_id,
                "model_name": model_name,
                "model_version": model_version,
                "pred_val": prediction_value,
                "is_anomaly": is_anomaly,
                "now": datetime.now(timezone.utc),
            },
        )
        db.commit()
        logger.info(
            "Wrote fact_prediction",
            extra={
                "model_name": model_name,
                "is_anomaly": is_anomaly,
                "upload_job_id": upload_job_id,
            },
        )
    except Exception as exc:
        db.rollback()
        logger.warning("Could not write to fact_predictions: %s", exc)


# ─── Request / response models ────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    recent_values: list[float]
    upload_job_id: Optional[str] = None


class AnomalyRequest(BaseModel):
    revenue: float
    units: float
    upload_job_id: Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# Training endpoints
@app.post("/train/sales-forecast", summary="Train & register the sales-forecast model")
def train_sales_forecast():
    """
    Run the training pipeline for `nexus-sales-forecast`.

    Queries fact_sales from PostgreSQL, trains GradientBoostingRegressor,
    logs to MLflow, registers, and promotes to 'production' alias if MAE improves.
    """
    try:
        result = sales_forecast.train_and_register()
        return {"status": "success", **result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Sales forecast training failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/train/anomaly-detection", summary="Train & register the anomaly-detection model")
def train_anomaly_detection():
    """
    Run the training pipeline for `nexus-anomaly-detection`.

    Queries fact_sales from PostgreSQL, trains IsolationForest,
    logs to MLflow, registers, and promotes to 'production' alias
    if mean_anomaly_score improves.
    """
    try:
        result = anomaly_detection.train_and_register()
        return {"status": "success", **result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Anomaly detection training failed")
        raise HTTPException(status_code=500, detail=str(exc))


# Prediction endpoints
@app.post("/predict/sales-forecast", summary="Predict next-period revenue")
def predict_forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    """
    Load the production `nexus-sales-forecast` model from MLflow registry
    and return a single-step forecast.

    `recent_values` must contain at least as many values as the lags
    the model was trained with (up to 3).  The last min(3, len) values
    are used as lag features.
    """
    model_name = sales_forecast.MODEL_NAME
    model = _load_production_model(model_name)
    version = _get_model_version(model_name)

    # Determine the number of lag features this model expects.
    n_features = model.n_features_in_
    if len(req.recent_values) < n_features:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Model expects {n_features} lag values; "
                f"got {len(req.recent_values)}."
            ),
        )

    lags = req.recent_values[-n_features:]
    forecast = float(model.predict([lags])[0])

    _write_prediction(
        db,
        model_name=model_name,
        model_version=version,
        prediction_value=forecast,
        is_anomaly=None,
        upload_job_id=req.upload_job_id,
    )

    return {
        "forecast": forecast,
        "model_version": version,
        "lags_used": lags,
    }


@app.post("/predict/anomaly", summary="Detect anomalous (revenue, units) pairs")
def predict_anomaly(req: AnomalyRequest, db: Session = Depends(get_db)):
    """
    Load the production `nexus-anomaly-detection` model from MLflow registry
    and score a single (revenue, units) observation.
    """
    model_name = anomaly_detection.MODEL_NAME
    model = _load_production_model(model_name)
    version = _get_model_version(model_name)

    X = [[req.revenue, req.units]]
    label = int(model.predict(X)[0])     # -1 = anomaly, 1 = normal
    is_anomaly = label == -1
    score = float(model.score_samples(X)[0])

    _write_prediction(
        db,
        model_name=model_name,
        model_version=version,
        prediction_value=score,
        is_anomaly=is_anomaly,
        upload_job_id=req.upload_job_id,
    )

    return {
        "is_anomaly": is_anomaly,
        "score": score,
        "model_version": version,
    }
