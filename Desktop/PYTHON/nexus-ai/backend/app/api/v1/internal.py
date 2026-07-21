"""
Internal API — called only by n8n workflows and other backend services.
All endpoints require the x-internal-secret header.
"""
import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.reports import _generate_pdf
from app.services.recommendations import generate_recommendations_for_job
from app.core.config import settings
from app.db.mongo import pipeline_results, workflow_logs
from app.db.postgres import get_db
from app.models.fact_predictions import FactPrediction
from app.models.fact_sales import FactSales
from app.models.report import Report
from app.models.upload_job import UploadJob

router = APIRouter(prefix="/internal", tags=["internal"])


def _check_secret(x_internal_secret: Optional[str]) -> None:
    if x_internal_secret != settings.N8N_WEBHOOK_SECRET:
        raise HTTPException(401, "Unauthorized internal call")


# ─── Pydantic models ──────────────────────────────────────────────────────────

class CallbackPayload(BaseModel):
    job_id: uuid.UUID
    status: str
    error_detail: Optional[dict] = None
    stage: Optional[str] = None       # for workflow_logs audit
    metadata: Optional[dict] = None   # extra fields logged to MongoDB


class NotifyPayload(BaseModel):
    job_id: str
    subject: str
    body: str
    to_email: Optional[str] = None    # defaults to settings.NOTIFICATION_EMAIL


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/pipeline-callback")
async def pipeline_callback(
    payload: CallbackPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_internal_secret: Optional[str] = Header(None),
):
    """
    Update job status and write an audit entry to MongoDB workflow_logs.
    Called by every n8n workflow node at each pipeline stage.
    """
    _check_secret(x_internal_secret)

    job = db.query(UploadJob).filter(UploadJob.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    job.status = payload.status
    job.error_detail = payload.error_detail
    db.commit()

    # Audit to MongoDB — non-fatal if it fails
    try:
        audit: dict[str, Any] = {
            "job_id": str(payload.job_id),
            "stage": payload.stage or payload.status,
            "status": "success" if not payload.error_detail else "error",
            "source": "n8n",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if payload.metadata:
            audit.update(payload.metadata)
        if payload.error_detail:
            audit["error_detail"] = payload.error_detail
        await workflow_logs.insert_one(audit)
    except Exception:
        pass  # never block the pipeline over a log write

    # Kick off AI recommendation generation in the background when the
    # report stage has completed and the job is ready for analysis.
    if payload.status == "recommending":
        background_tasks.add_task(
            generate_recommendations_for_job,
            str(payload.job_id),
        )

    return {"ok": True, "status": payload.status}


@router.post("/notify")
async def send_notification(
    payload: NotifyPayload,
    db: Session = Depends(get_db),
    x_internal_secret: Optional[str] = Header(None),
):
    """
    Send an email notification summarising pipeline results.

    Idempotent: if workflow_logs already contains stage=notification-sent
    for this job_id, the email is skipped and {sent: false} is returned.
    SMTP sending is skipped (logged only) when SMTP_USER is not configured.
    """
    _check_secret(x_internal_secret)

    # Idempotency check — skip if already notified
    existing = await workflow_logs.find_one(
        {"job_id": payload.job_id, "stage": "notification-sent"}
    )
    if existing:
        return {"sent": False, "message": "Notification already sent for this job."}

    to_addr = payload.to_email or settings.NOTIFICATION_EMAIL
    sent = False
    message = "SMTP not configured — notification logged only."

    if settings.SMTP_USER and to_addr:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = payload.subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = to_addr
            msg.attach(MIMEText(payload.body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to_addr, msg.as_string())

            sent = True
            message = f"Email sent to {to_addr}."
        except Exception as exc:
            message = f"SMTP error: {exc}"

    # Mark report as notified (best-effort)
    try:
        job_uuid = uuid.UUID(payload.job_id)
        report = db.query(Report).filter(Report.job_id == job_uuid).first()
        if report:
            report.notified_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        pass

    # Audit log
    try:
        await workflow_logs.insert_one({
            "job_id": payload.job_id,
            "stage": "notification-sent",
            "status": "sent" if sent else "skipped",
            "source": "n8n",
            "to_email": to_addr,
            "smtp_configured": bool(settings.SMTP_USER),
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return {"sent": sent, "message": message}


@router.post("/generate-report/{job_id}", summary="Internal: generate PDF report (no JWT required)")
async def internal_generate_report(
    job_id: str,
    db: Session = Depends(get_db),
    x_internal_secret: Optional[str] = Header(None),
):
    """
    Called by n8n workflow 05 after ML predictions are written.
    Idempotent: re-running overwrites the file and updates the DB row.
    """
    _check_secret(x_internal_secret)

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job = db.query(UploadJob).filter(UploadJob.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Allow report generation once ML modeling is complete (or already done/recommending).
    # All earlier pipeline stages (validating, cleaning, processing, etc.) are rejected.
    _REPORT_ALLOWED_STATUSES = {"modeling", "done", "recommending"}
    if job.status not in _REPORT_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Job status is '{job.status}' — report generation is only allowed "
                f"after ML modeling completes"
            ),
        )

    # KPIs from fact_sales
    kpi_row = (
        db.query(
            func.sum(FactSales.revenue).label("total_revenue"),
            func.sum(FactSales.units).label("total_units"),
            func.count().label("n_records"),
            func.min(FactSales.date_key).label("first_date"),
            func.max(FactSales.date_key).label("last_date"),
        )
        .filter(FactSales.job_id == job_uuid)
        .first()
    )
    kpis: dict = {}
    if kpi_row:
        kpis = {
            "total_revenue": float(kpi_row.total_revenue or 0),
            "total_units": int(kpi_row.total_units or 0),
            "n_records": int(kpi_row.n_records or 0),
            "first_date": str(kpi_row.first_date) if kpi_row.first_date else "N/A",
            "last_date": str(kpi_row.last_date) if kpi_row.last_date else "N/A",
        }

    # ML predictions
    pred_rows = (
        db.query(FactPrediction)
        .filter(FactPrediction.upload_job_id == job_uuid)
        .order_by(FactPrediction.created_at.desc())
        .limit(10)
        .all()
    )
    predictions = [
        {
            "model_name": r.model_name,
            "model_version": r.model_version,
            "prediction_value": float(r.prediction_value) if r.prediction_value is not None else None,
            "is_anomaly": r.is_anomaly,
        }
        for r in pred_rows
    ]

    # ETL recommendations from MongoDB
    mongo_doc = await pipeline_results.find_one({"job_id": job_id})
    recommendation: Optional[str] = None
    if mongo_doc:
        recs = mongo_doc.get("recommendations", [])
        if recs:
            recommendation = " | ".join(str(r) for r in recs[:5])

    pdf_path = os.path.join(settings.STORAGE_DIR, job_id, "report.pdf")
    _generate_pdf(
        path=pdf_path,
        job_id=job_id,
        filename=job.filename,
        kpis=kpis,
        predictions=predictions,
        recommendation=recommendation,
    )

    download_url = f"/api/v1/reports/{job_id}/download"

    existing = db.query(Report).filter(Report.job_id == job_uuid).first()
    if existing:
        existing.report_path = pdf_path
        existing.download_url = download_url
        existing.generated_at = datetime.now(timezone.utc)
        existing.status = "ready"
        db.commit()
        db.refresh(existing)
        report = existing
    else:
        report = Report(job_id=job_uuid, report_path=pdf_path, download_url=download_url)
        db.add(report)
        db.commit()
        db.refresh(report)

    return {
        "report_id": str(report.report_id),
        "job_id": job_id,
        "download_url": download_url,
        "generated_at": report.generated_at.isoformat(),
        "kpis": kpis,
        "n_predictions": len(predictions),
    }
