"""add_fact_predictions

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-07-21

Creates the fact_predictions table, which records every inference
result produced by the ml-service.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_predictions (
            prediction_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            upload_job_id   UUID        NULL,
            model_name      VARCHAR(120) NOT NULL,
            model_version   VARCHAR(40)  NULL,
            prediction_value NUMERIC(12,4) NULL,
            is_anomaly      BOOLEAN      NULL,
            region_id       INTEGER      NULL,
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL
                            DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fact_predictions")
