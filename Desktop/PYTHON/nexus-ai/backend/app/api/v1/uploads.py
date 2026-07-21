import uuid, httpx
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.db.mongo import raw_uploads
from app.models.upload_job import UploadJob
from app.services.deps import require_role
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/")
async def create_upload(file: UploadFile = File(...), db: Session = Depends(get_db),
                         user=Depends(require_role("admin", "analyst"))):
    content = await file.read()
    job = UploadJob(filename=file.filename, status="pending")
    db.add(job); db.commit(); db.refresh(job)

    await raw_uploads.insert_one({
        "job_id": str(job.id),
        "filename": file.filename,
        "size_bytes": len(content),
        "uploaded_by": user["user_id"],
    })

    job.status = "validating"
    db.commit()

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(f"{settings.N8N_URL}/webhook/validate-upload",
                               json={"job_id": str(job.id), "filename": file.filename})
        except httpx.HTTPError:
            pass  # n8n unreachable in dev is non-fatal for scaffold purposes

    return {"job_id": str(job.id), "status": job.status}

@router.get("/{job_id}/status")
def get_status(job_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_role("admin", "analyst", "viewer"))):
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return {"job_id": str(job.id), "status": job.status, "error_detail": job.error_detail}
