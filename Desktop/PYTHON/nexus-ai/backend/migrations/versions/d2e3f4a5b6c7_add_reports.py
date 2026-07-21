"""add_reports

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-21

Creates the reports table that tracks generated PDF reports.
Each row maps one upload_job to one PDF file on disk plus a download URL.
notified_at is set when the 06-notifications workflow sends the email so
re-runs can skip duplicate emails.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            report_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id       UUID        NOT NULL,
            report_path  TEXT        NOT NULL,
            download_url TEXT        NOT NULL,
            status       VARCHAR(40) NOT NULL DEFAULT 'ready',
            generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            notified_at  TIMESTAMP WITH TIME ZONE NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_reports_job_id ON reports (job_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reports")
