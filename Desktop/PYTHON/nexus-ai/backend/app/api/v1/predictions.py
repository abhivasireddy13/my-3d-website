"""
Predictions API.

GET /api/v1/predictions/
  Returns the most recent fact_predictions rows (up to 100), each
  with its associated recommendation if one exists.

GET /api/v1/predictions/{prediction_id}/recommendation
  Returns the FactRecommendation for a specific prediction.
  404 if none exists (threshold was not breached for that prediction).
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.postgres import get_db
from app.models.fact_predictions import FactPrediction
from app.models.fact_recommendations import FactRecommendation
from app.models.user import User

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _serialize_prediction(pred: FactPrediction, rec: Optional[FactRecommendation]) -> dict:
    return {
        "prediction_id": str(pred.prediction_id),
        "upload_job_id": str(pred.upload_job_id) if pred.upload_job_id else None,
        "model_name": pred.model_name,
        "model_version": pred.model_version,
        "prediction_value": float(pred.prediction_value) if pred.prediction_value is not None else None,
        "is_anomaly": pred.is_anomaly,
        "created_at": pred.created_at.isoformat() if pred.created_at else None,
        "recommendation": _serialize_rec(rec) if rec else None,
    }


def _serialize_rec(rec: FactRecommendation) -> dict:
    return {
        "recommendation_id": str(rec.recommendation_id),
        "actions": rec.actions or [],
        "model_used": rec.model_used,
        "triggered_by": rec.triggered_by,
        "metric_delta": float(rec.metric_delta) if rec.metric_delta is not None else None,
        "confidence_score": float(rec.confidence_score) if rec.confidence_score is not None else None,
        "status": rec.status,
        "error_message": rec.error_message,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@router.get("/", summary="List recent predictions with recommendations")
def list_predictions(
    limit: int = Query(50, ge=1, le=200),
    upload_job_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(FactPrediction)

    if upload_job_id:
        try:
            jid = uuid.UUID(upload_job_id)
        except ValueError:
            raise HTTPException(400, "Invalid upload_job_id format")
        query = query.filter(FactPrediction.upload_job_id == jid)

    predictions = (
        query
        .order_by(FactPrediction.created_at.desc())
        .limit(limit)
        .all()
    )

    # Batch-load recommendations to avoid N+1
    pred_ids = [p.prediction_id for p in predictions]
    rec_map: dict[uuid.UUID, FactRecommendation] = {}
    if pred_ids:
        recs = (
            db.query(FactRecommendation)
            .filter(FactRecommendation.prediction_id.in_(pred_ids))
            .all()
        )
        rec_map = {r.prediction_id: r for r in recs}

    return {
        "total": len(predictions),
        "predictions": [
            _serialize_prediction(p, rec_map.get(p.prediction_id))
            for p in predictions
        ],
    }


@router.get("/{prediction_id}/recommendation", summary="Get recommendation for a prediction")
def get_recommendation(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        pred_uuid = uuid.UUID(prediction_id)
    except ValueError:
        raise HTTPException(400, "Invalid prediction_id format")

    pred = db.query(FactPrediction).filter(FactPrediction.prediction_id == pred_uuid).first()
    if not pred:
        raise HTTPException(404, "Prediction not found")

    rec = (
        db.query(FactRecommendation)
        .filter(FactRecommendation.prediction_id == pred_uuid)
        .first()
    )
    if not rec:
        raise HTTPException(
            404,
            "No recommendation for this prediction — threshold was not breached "
            "or the recommending stage has not completed yet.",
        )

    return _serialize_rec(rec)
