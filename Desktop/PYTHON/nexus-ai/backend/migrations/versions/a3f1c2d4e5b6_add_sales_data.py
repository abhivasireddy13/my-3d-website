"""add_sales_data

Revision ID: a3f1c2d4e5b6
Revises: d508bd67d5b3
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a3f1c2d4e5b6"
down_revision: Union[str, None] = "d508bd67d5b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales_data (
            id          SERIAL PRIMARY KEY,
            job_id      UUID        NOT NULL REFERENCES upload_jobs(id) ON DELETE CASCADE,
            sale_date   DATE        NOT NULL,
            revenue     NUMERIC(12,2) NOT NULL,
            units       INTEGER     NOT NULL,
            created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sales_data_job_id ON sales_data (job_id)"
    )


def downgrade() -> None:
    op.drop_index("ix_sales_data_job_id", table_name="sales_data")
    op.drop_table("sales_data")
