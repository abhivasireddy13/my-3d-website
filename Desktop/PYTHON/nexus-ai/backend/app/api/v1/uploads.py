import asyncio
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.mongo import raw_uploads
from app.db.postgres import get_db
from app.models.upload_job import UploadJob
from app.services.deps import require_role

router = APIRouter(prefix="/uploads", tags=["uploads"])

_ALLOWED_EXTENSIONS = {".csv"}
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB hard limit


async def _save_file(job_id: str, filename: str, content: bytes) -> str:
    """Write upload bytes to local storage and return the absolute path.

    TODO: swap the Path.write_bytes call for an S3-compatible put_object
    (e.g. boto3 / aiobotocore pointing at MinIO or AWS S3) before production.
    The rest of this function's interface stays the same.
    """
    dest = Path(settings.STORAGE_DIR) / job_id
    await asyncio.to_thread(dest.mkdir, parents=True, exist_ok=True)
    file_path = dest / filename
    await asyncio.to_thread(file_path.write_bytes, content)
    return str(file_path)


@router.post("/")
async def create_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "analyst")),
):
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

    job.status = "validating"
    db.commit()

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(
                f"{settings.N8N_URL}/webhook/validate-upload",
                json={"job_id": job_id_str, "filename": file.filename},
            )
        except httpx.HTTPError:
            pass  # n8n unreachable in dev is non-fatal

    return {"job_id": job_id_str, "status": job.status}


@router.get("")
def list_uploads(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "analyst", "viewer")),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
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
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "error_detail": job.error_detail,
    }
