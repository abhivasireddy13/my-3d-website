"""
Minimal SQLAlchemy model for the fact_predictions table.
The table is created / migrated by the backend service.
The ml-service only writes prediction rows; it never creates the table.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FactPrediction(Base):
    __tablename__ = "fact_predictions"

    prediction_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_job_id = Column(UUID(as_uuid=True), nullable=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    prediction_value = Column(Numeric(12, 4), nullable=True)
    is_anomaly = Column(Boolean, nullable=True)
    region_id = Column(Integer, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
