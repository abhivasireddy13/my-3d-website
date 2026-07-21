import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgres import Base


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    report_path = Column(Text, nullable=False)       # absolute filesystem path
    download_url = Column(Text, nullable=False)       # public relative URL
    generated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notified_at = Column(DateTime, nullable=True)     # set when 06 sends email
    status = Column(String(40), default="ready", nullable=False)  # ready | failed
