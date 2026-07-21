"""
Fact table — AI-generated recommendations linked to ML predictions.

Each row records the full audit trail for one recommendation episode:
prompt sent to Claude, model version used, actions returned, what
threshold triggered the call, and whether the call succeeded or fell
back to rule-based suggestions.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON

from app.db.postgres import Base


class FactRecommendation(Base):
    __tablename__ = "fact_recommendations"

    recommendation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to the prediction that triggered this recommendation
    prediction_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # Denormalised for efficient job-level queries
    upload_job_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Output
    actions = Column(JSON, nullable=False)          # list[str] — the recommended actions
    model_used = Column(String(100), nullable=True) # e.g. "claude-sonnet-4-6"

    # Full audit trail
    prompt_used = Column(Text, nullable=True)       # exact prompt sent to the LLM
    triggered_by = Column(String(50), nullable=True)# "anomaly_detected" | "forecast_decline"
    metric_name = Column(String(120), nullable=True)
    metric_value = Column(Numeric(12, 4), nullable=True)
    metric_delta = Column(Numeric(8, 4), nullable=True)  # fractional change, e.g. -0.12 = -12%
    confidence_score = Column(Numeric(6, 4), nullable=True)  # 1.0 = LLM, 0.5 = fallback

    # Execution outcome
    status = Column(String(40), nullable=False, default="generated")
    # "generated" = LLM succeeded, "fallback" = rule-based used, "failed" = all attempts failed
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
