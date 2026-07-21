import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgres import Base


class SalesData(Base):
    """One cleaned row from an uploaded CSV, linked to its upload job."""

    __tablename__ = "sales_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("upload_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sale_date = Column(Date, nullable=False)
    revenue = Column(Numeric(12, 2), nullable=False)
    units = Column(Integer, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
