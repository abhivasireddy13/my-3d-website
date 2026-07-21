"""initial_users_upload_jobs

Revision ID: d508bd67d5b3
Revises:
Create Date: 2026-07-21 07:37:08.069972

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "d508bd67d5b3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum idempotently (Postgres lacks IF NOT EXISTS for types).
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE role AS ENUM ('admin', 'analyst', 'viewer');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            email VARCHAR NOT NULL,
            hashed_password VARCHAR NOT NULL,
            role role NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS upload_jobs (
            id UUID PRIMARY KEY,
            filename VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'pending',
            error_detail JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)


def downgrade() -> None:
    op.drop_table("upload_jobs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS role")
