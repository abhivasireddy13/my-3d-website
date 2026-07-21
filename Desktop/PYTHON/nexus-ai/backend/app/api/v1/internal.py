import uuid
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.models.upload_job import UploadJob
from app.core.config import settings

router = APIRouter(prefix="/internal", tags=["internal"])


class CallbackPayload(BaseModel):
    job_id: uuid.UUID
    status: str
    error_detail: dict | None = None


@router.post("/pipeline-callback")
def pipeline_callback(
    payload: CallbackPayload,
    db: Session = Depends(get_db),
    x_internal_secret: str = Header(None),
):
    if x_internal_secret != settings.N8N_WEBHOOK_SECRET:
        raise HTTPException(401, "Unauthorized internal call")
    job = db.query(UploadJob).filter(UploadJob.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    job.status = payload.status
    job.error_detail = payload.error_detail
    db.commit()
    return {"ok": True}
