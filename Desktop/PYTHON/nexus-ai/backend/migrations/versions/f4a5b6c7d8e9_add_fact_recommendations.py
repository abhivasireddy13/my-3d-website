"""add_fact_recommendations

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-22

Creates fact_recommendations — one row per AI recommendation episode.
Stores the full audit trail: trigger reason, prompt sent, model used,
actions returned, and whether the Claude call succeeded or fell back
to rule-based suggestions.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS fact_recommendations (
            recommendation_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            prediction_id      UUID        NOT NULL,
            upload_job_id      UUID        NULL,
            actions            JSON        NOT NULL DEFAULT '[]',
            model_used         VARCHAR(100) NULL,
            prompt_used        TEXT        NULL,
            triggered_by       VARCHAR(50) NULL,
            metric_name        VARCHAR(120) NULL,
            metric_value       NUMERIC(12,4) NULL,
            metric_delta       NUMERIC(8,4)  NULL,
            confidence_score   NUMERIC(6,4)  NULL,
            status             VARCHAR(40) NOT NULL DEFAULT 'generated',
            error_message      TEXT        NULL,
            created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_recommendations_prediction_id "
        "ON fact_recommendations (prediction_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_recommendations_upload_job_id "
        "ON fact_recommendations (upload_job_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_recommendations_created_at "
        "ON fact_recommendations (created_at)"
    )

    # Grant analytics_reader access (PostgreSQL only — safe to fail silently)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'analytics_reader') THEN
                    GRANT SELECT ON fact_recommendations TO analytics_reader;
                END IF;
            END
            $$;
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fact_recommendations")
