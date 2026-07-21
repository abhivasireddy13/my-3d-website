"""
Admin API — endpoints for administrative operations.

All endpoints require the caller to have role=admin (enforced via JWT).
Never exposed to non-admin users; the backend enforces this regardless of
what the frontend shows or hides.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.mongo import workflow_logs
from app.db.postgres import get_db
from app.models.fact_predictions import FactPrediction
from app.models.fact_recommendations import FactRecommendation
from app.models.upload_job import UploadJob
from app.models.user import Role, User

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Auth helper ──────────────────────────────────────────────────────────────

def _require_admin(user_data=Depends(get_current_user)) -> dict:
    if user_data.get("role") != Role.admin.value:
        raise HTTPException(403, "Admin role required")
    return user_data


# ─── Users endpoint ───────────────────────────────────────────────────────────

@router.get("/users", summary="List all users (admin only)")
def list_users(
    db: Session = Depends(get_db),
    _: dict = Depends(_require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "total": len(users),
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role.value,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


# ─── Jobs endpoint ────────────────────────────────────────────────────────────

@router.get("/jobs", summary="List all upload jobs (admin only)")
def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: Session = Depends(get_db),
    _: dict = Depends(_require_admin),
):
    query = db.query(UploadJob)
    if status:
        query = query.filter(UploadJob.status == status)
    total = query.count()
    jobs = (
        query.order_by(UploadJob.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "jobs": [
            {
                "id": str(j.id),
                "filename": j.filename,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
                "error_detail": j.error_detail,
            }
            for j in jobs
        ],
    }


# ─── Trace endpoint ───────────────────────────────────────────────────────────

@router.get("/trace/{job_id}", summary="Full pipeline trace for a job (admin only)")
async def get_trace(
    job_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(_require_admin),
):
    """
    Assembles every event for this job_id across:
      1. upload_jobs (Postgres) — creation and current state
      2. workflow_logs (MongoDB) — n8n stage events
      3. fact_predictions (Postgres) — ML inference rows
      4. fact_recommendations (Postgres) — AI recommendation rows

    Returns a chronologically sorted timeline, making the full
    Upload→ETL→ML→Automation→Analytics→AI→Report chain visible in one view.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, "Invalid job_id format")

    job = db.query(UploadJob).filter(UploadJob.id == job_uuid).first()
    if not job:
        raise HTTPException(404, "Job not found")

    timeline: list[dict[str, Any]] = []

    # ── 1. Job creation ───────────────────────────────────────────────────────
    timeline.append({
        "timestamp": job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat(),
        "source": "upload_jobs",
        "event_type": "job_created",
        "label": f"CSV uploaded: {job.filename}",
        "icon": "upload",
        "data": {"filename": job.filename},
    })

    # ── 2. Workflow log events from MongoDB ───────────────────────────────────
    try:
        docs = await workflow_logs.find({"job_id": job_id}).to_list(length=200)
        for doc in docs:
            ts = doc.get("timestamp", "")
            stage = doc.get("stage", "workflow_event")
            status_val = doc.get("status", "")
            payload: dict[str, Any] = {
                k: v
                for k, v in doc.items()
                if k not in ("_id", "job_id", "timestamp", "source")
                and not isinstance(v, bytes)
            }
            timeline.append({
                "timestamp": ts,
                "source": "workflow_logs",
                "event_type": stage,
                "label": _stage_label(stage, status_val),
                "icon": _stage_icon(stage),
                "data": payload,
            })
    except Exception:
        pass  # MongoDB unavailable in tests — skip without failing

    # ── 3. ML predictions ─────────────────────────────────────────────────────
    predictions = (
        db.query(FactPrediction)
        .filter(FactPrediction.upload_job_id == job_uuid)
        .order_by(FactPrediction.created_at)
        .all()
    )
    for pred in predictions:
        anomaly_flag = " ⚠ ANOMALY" if pred.is_anomaly else ""
        timeline.append({
            "timestamp": pred.created_at.isoformat() if pred.created_at else "",
            "source": "fact_predictions",
            "event_type": "prediction_generated",
            "label": f"ML prediction: {pred.model_name}{anomaly_flag}",
            "icon": "brain",
            "data": {
                "prediction_id": str(pred.prediction_id),
                "model_name": pred.model_name,
                "model_version": pred.model_version,
                "prediction_value": (
                    float(pred.prediction_value) if pred.prediction_value is not None else None
                ),
                "is_anomaly": pred.is_anomaly,
                "region_id": pred.region_id,
            },
        })

    # ── 4. AI recommendations ─────────────────────────────────────────────────
    if predictions:
        recs = (
            db.query(FactRecommendation)
            .filter(FactRecommendation.upload_job_id == job_uuid)
            .order_by(FactRecommendation.created_at)
            .all()
        )
        for rec in recs:
            timeline.append({
                "timestamp": rec.created_at.isoformat() if rec.created_at else "",
                "source": "fact_recommendations",
                "event_type": "recommendation_generated",
                "label": f"AI recommendation ({rec.triggered_by or 'unknown trigger'})",
                "icon": "sparkles",
                "data": {
                    "recommendation_id": str(rec.recommendation_id),
                    "triggered_by": rec.triggered_by,
                    "actions": rec.actions,
                    "model_used": rec.model_used,
                    "status": rec.status,
                    "confidence_score": (
                        float(rec.confidence_score) if rec.confidence_score is not None else None
                    ),
                    "error_message": rec.error_message,
                },
            })

    # ── 5. Final job state (if updated after creation) ────────────────────────
    if job.updated_at and job.updated_at != job.created_at:
        timeline.append({
            "timestamp": job.updated_at.isoformat(),
            "source": "upload_jobs",
            "event_type": "status_changed",
            "label": f"Pipeline status → {job.status}",
            "icon": "check" if job.status == "done" else ("x" if job.status == "failed" else "clock"),
            "data": {
                "status": job.status,
                "error_detail": job.error_detail,
            },
        })

    # Sort chronologically; empty timestamps sort to front (pre-dated events)
    timeline.sort(key=lambda x: x.get("timestamp") or "")

    return {
        "job_id": job_id,
        "job": {
            "filename": job.filename,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "error_detail": job.error_detail,
        },
        "event_count": len(timeline),
        "sources": {
            "upload_jobs": sum(1 for e in timeline if e["source"] == "upload_jobs"),
            "workflow_logs": sum(1 for e in timeline if e["source"] == "workflow_logs"),
            "fact_predictions": sum(1 for e in timeline if e["source"] == "fact_predictions"),
            "fact_recommendations": sum(1 for e in timeline if e["source"] == "fact_recommendations"),
        },
        "timeline": timeline,
    }


# ─── Label / icon helpers ─────────────────────────────────────────────────────

def _stage_label(stage: str, status: str = "") -> str:
    labels = {
        "etl-complete": "ETL pipeline complete",
        "ml-predictions": "ML predictions written",
        "dashboard-refresh": "Analytics dashboards refreshed",
        "report-ready": "PDF report generated",
        "notification-sent": "Email notification sent",
        "anomaly_detected": "Anomaly threshold triggered",
        "forecast_decline": "Forecast decline threshold triggered",
        "validating": "Data validation started",
        "cleaning": "Data cleaning & normalisation",
        "storing": "Storing to data warehouse",
        "modeling": "ML inference running",
        "recommending": "AI recommendations generating",
        "done": "Pipeline complete",
    }
    base = labels.get(stage, stage.replace("-", " ").title())
    if status == "error":
        return f"{base} (error)"
    return base


def _stage_icon(stage: str) -> str:
    icons = {
        "etl-complete": "database",
        "ml-predictions": "brain",
        "dashboard-refresh": "bar-chart",
        "report-ready": "file-text",
        "notification-sent": "mail",
        "notification-skipped": "mail",
    }
    return icons.get(stage, "activity")
