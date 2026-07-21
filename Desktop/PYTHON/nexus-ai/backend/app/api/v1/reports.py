"""
Reports API — generate and download per-job PDF summary reports.

POST /api/v1/reports/generate/{job_id}
  Assembles a PDF from KPIs, ML predictions, and ETL recommendations.
  Stores the file in STORAGE_DIR/{job_id}/report.pdf.
  Idempotent: re-running overwrites the file and updates the DB row.

GET  /api/v1/reports/{job_id}/download
  Returns the PDF as an application/pdf FileResponse.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.db.mongo import pipeline_results
from app.db.postgres import get_db
from app.models.fact_predictions import FactPrediction
from app.models.fact_sales import FactSales
from app.models.report import Report
from app.models.upload_job import UploadJob
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


# ─── PDF helper ───────────────────────────────────────────────────────────────

def _generate_pdf(
    path: str,
    job_id: str,
    filename: str,
    kpis: dict,
    predictions: list[dict],
    recommendation: Optional[str],
) -> None:
    """Write a reportlab PDF to *path*."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm,
                             topMargin=2 * cm, bottomMargin=2 * cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"],
                                  fontSize=20, spaceAfter=6, textColor=colors.HexColor("#0A2540"))
    h2_style = ParagraphStyle("h2", parent=styles["Heading2"],
                               fontSize=13, spaceAfter=4, textColor=colors.HexColor("#0A2540"))
    body_style = styles["Normal"]

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("NEXUS AI — Pipeline Report", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#00C9FF")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"<b>Job ID:</b> {job_id}", body_style))
    story.append(Paragraph(f"<b>File:</b> {filename}", body_style))
    story.append(Paragraph(f"<b>Generated:</b> {now_str}", body_style))
    story.append(Spacer(1, 0.5 * cm))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Key Performance Indicators", h2_style))
    kpi_data = [
        ["Metric", "Value"],
        ["Total Revenue", f"${kpis.get('total_revenue', 0):,.2f}"],
        ["Total Units Sold", f"{kpis.get('total_units', 0):,}"],
        ["Records Processed", str(kpis.get('n_records', 0))],
        ["Date Range", f"{kpis.get('first_date', 'N/A')} → {kpis.get('last_date', 'N/A')}"],
    ]
    kpi_table = Table(kpi_data, colWidths=[8 * cm, 9 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2540")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F0F4FF"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C0C8D8")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── ML Predictions ────────────────────────────────────────────────────────
    story.append(Paragraph("ML Predictions", h2_style))
    if predictions:
        pred_data = [["Model", "Value", "Anomaly", "Version"]]
        for p in predictions:
            pred_data.append([
                p.get("model_name", ""),
                f"{p.get('prediction_value', 'N/A')}",
                "YES ⚠" if p.get("is_anomaly") else "No",
                p.get("model_version", ""),
            ])
        pred_table = Table(pred_data, colWidths=[5 * cm, 4 * cm, 3 * cm, 5 * cm])
        pred_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2540")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F0F4FF"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C0C8D8")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(pred_table)
    else:
        story.append(Paragraph("No predictions available for this job.", body_style))
    story.append(Spacer(1, 0.5 * cm))

    # ── ETL Recommendations ───────────────────────────────────────────────────
    if recommendation:
        story.append(Paragraph("ETL Recommendations", h2_style))
        story.append(Paragraph(str(recommendation), body_style))
        story.append(Spacer(1, 0.5 * cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        f"<font size='8'>Generated by NEXUS AI · {now_str}</font>",
        body_style,
    ))

    doc.build(story)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", summary="List all generated reports")
def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    total = db.query(Report).count()
    rows = (
        db.query(Report, UploadJob)
        .join(UploadJob, UploadJob.id == Report.job_id, isouter=True)
        .order_by(Report.generated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "reports": [
            {
                "report_id": str(r.report_id),
                "job_id": str(r.job_id),
                "filename": j.filename if j else None,
                "download_url": r.download_url,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "notified_at": r.notified_at.isoformat() if r.notified_at else None,
                "status": r.status,
            }
            for r, j in rows
        ],
    }


@router.post("/generate/{job_id}", summary="Generate or regenerate the PDF report for a job")
async def generate_report(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Idempotent: calling this endpoint multiple times for the same job_id
    overwrites the existing PDF and updates the DB row — no duplicate records.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job = db.query(UploadJob).filter(UploadJob.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not done yet (current status: {job.status}). "
                   f"Reports can only be generated for completed jobs.",
        )

    # ── KPIs from fact_sales — use ORM so SQLAlchemy handles UUID conversion ──
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

    # ── ML predictions — ORM so UUID binding is correct in both PG and SQLite ─
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

    # ── ETL recommendation from MongoDB ──────────────────────────────────────
    mongo_doc = await pipeline_results.find_one({"job_id": job_id})
    recommendation: Optional[str] = None
    if mongo_doc:
        recs = mongo_doc.get("recommendations", [])
        if recs:
            recommendation = " | ".join(str(r) for r in recs[:5])

    # ── Generate PDF ──────────────────────────────────────────────────────────
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

    # ── Upsert report record ─────────────────────────────────────────────────
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
        report = Report(
            job_id=job_uuid,
            report_path=pdf_path,
            download_url=download_url,
        )
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


@router.get("/{job_id}/download", summary="Download the PDF report for a job")
def download_report(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    report = db.query(Report).filter(Report.job_id == job_uuid).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found. Generate it first.")
    if not os.path.exists(report.report_path):
        raise HTTPException(status_code=404, detail="Report file missing from storage.")

    return FileResponse(
        path=report.report_path,
        media_type="application/pdf",
        filename=f"nexus-report-{job_id[:8]}.pdf",
    )
