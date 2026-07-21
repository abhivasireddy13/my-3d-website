import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.mongo import pipeline_results, raw_uploads
from app.db.postgres import get_db
from app.models.upload_job import UploadJob
from app.services.deps import require_role
from app.services.etl import run_etl

import asyncio

router = APIRouter(prefix="/uploads", tags=["uploads"])

_ALLOWED_EXTENSIONS = {".csv"}
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB hard limit


async def _save_file(job_id: str, filename: str, content: bytes) -> str:
    """Write upload bytes to local storage and return the absolute path.

    TODO: swap Path.write_bytes for an S3-compatible put_object
    (boto3 / aiobotocore pointing at MinIO or AWS S3) before production.
    """
    dest = Path(settings.STORAGE_DIR) / job_id
    await asyncio.to_thread(dest.mkdir, parents=True, exist_ok=True)
    file_path = dest / filename
    await asyncio.to_thread(file_path.write_bytes, content)
    return str(file_path)


@router.post("/")
async def create_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "analyst")),
):
    """Accept a CSV upload, persist it to disk, and start the ETL pipeline."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only CSV files are accepted")

    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(413, "File exceeds 50 MB limit")

    job = UploadJob(filename=file.filename, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id_str = str(job.id)

    file_path = await _save_file(job_id_str, file.filename, content)

    await raw_uploads.insert_one(
        {
            "job_id": job_id_str,
            "filename": file.filename,
            "size_bytes": len(content),
            "file_path": file_path,
            "uploaded_by": user["user_id"],
        }
    )

    # Mark validating before returning so the stepper shows the first step.
    job.status = "validating"
    db.commit()

    # Kick off the local ETL pipeline as a background task.
    # The job ID and file path are all it needs; it creates its own DB session.
    background_tasks.add_task(run_etl, job_id_str, file_path)

    return {"job_id": job_id_str, "status": job.status}


@router.get("")
def list_uploads(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "analyst", "viewer")),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Return a paginated list of upload jobs, newest first."""
    offset = (page - 1) * per_page
    total = db.query(UploadJob).count()
    jobs = (
        db.query(UploadJob)
        .order_by(UploadJob.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "job_id": str(j.id),
                "filename": j.filename,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/{job_id}/status")
def get_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "analyst", "viewer")),
):
    """Return the current pipeline status for a single job."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "error_detail": job.error_detail,
    }


@router.get("/{job_id}/result")
async def get_result(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "analyst", "viewer")),
):
    """Return the ETL recommendation and statistics for a completed job."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "done":
        raise HTTPException(
            409, f"Job not yet complete (status: {job.status})"
        )

    doc = await pipeline_results.find_one({"job_id": str(job_id)})
    if not doc:
        raise HTTPException(404, "Result document not found")

    doc.pop("_id", None)  # MongoDB ObjectId is not JSON-serialisable
    return doc
