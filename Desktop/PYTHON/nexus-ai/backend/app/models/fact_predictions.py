"""
SQLAlchemy model for the fact_predictions table.

The table stores every inference result from the ml-service so
analysts can audit what was predicted, by which model version, and
when — tied back to an upload job when available.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgres import Base


class FactPrediction(Base):
    __tablename__ = "fact_predictions"

    prediction_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    upload_job_id = Column(UUID(as_uuid=True), nullable=True)
    model_name = Column(String(120), nullable=False)
    model_version = Column(String(40), nullable=True)
    prediction_value = Column(Numeric(12, 4), nullable=True)
    is_anomaly = Column(Boolean, nullable=True)
    region_id = Column(Integer, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
