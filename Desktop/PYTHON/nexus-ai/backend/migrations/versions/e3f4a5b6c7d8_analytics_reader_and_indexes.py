"""analytics_reader_role_and_warehouse_indexes

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-21

1. Adds performance indexes to fact_sales and fact_predictions for analytics
   queries (supports vw_revenue_trend, vw_region_sales, vw_anomaly_timeline
   and Superset's cross-filter queries).
2. On PostgreSQL only: creates the analytics_reader NOLOGIN role and grants
   SELECT on all dim_* / fact_* tables so Superset can use a read-only
   warehouse connection.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Analytics indexes (safe for both PostgreSQL and SQLite) ───────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_sales_region_key   ON fact_sales (region_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_sales_product_key  ON fact_sales (product_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_sales_customer_key ON fact_sales (customer_key)"
    )
    # Composite index: powers date-range + region filter used by Superset
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_sales_date_region "
        "ON fact_sales (date_key, region_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_predictions_is_anomaly "
        "ON fact_predictions (is_anomaly)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_predictions_created_at "
        "ON fact_predictions (created_at)"
    )

    # ── PostgreSQL-only: analytics_reader role ────────────────────────────
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Create role if it doesn't exist (idempotent via DO block)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analytics_reader') THEN
                CREATE ROLE analytics_reader NOLOGIN;
            END IF;
        END
        $$;
    """)

    op.execute("GRANT USAGE ON SCHEMA public TO analytics_reader")

    for tbl in [
        "dim_date", "dim_product", "dim_region", "dim_customer",
        "fact_sales", "fact_predictions", "upload_jobs", "reports",
    ]:
        op.execute(f"GRANT SELECT ON {tbl} TO analytics_reader")

    # Grant SELECT on the analytics views as well (CREATE OR REPLACE views
    # are run separately via analytics/sql/views.sql, but the grant is safe
    # to add even before the views exist).
    op.execute("""
        DO $$
        DECLARE
            v TEXT;
        BEGIN
            FOR v IN
                SELECT viewname FROM pg_views
                WHERE schemaname = 'public'
                  AND viewname LIKE 'vw_%'
            LOOP
                EXECUTE format('GRANT SELECT ON %I TO analytics_reader', v);
            END LOOP;
        END
        $$;
    """)

    # Future tables/views inherit SELECT for analytics_reader
    op.execute("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO analytics_reader;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_fact_sales_region_key")
    op.execute("DROP INDEX IF EXISTS ix_fact_sales_product_key")
    op.execute("DROP INDEX IF EXISTS ix_fact_sales_customer_key")
    op.execute("DROP INDEX IF EXISTS ix_fact_sales_date_region")
    op.execute("DROP INDEX IF EXISTS ix_fact_predictions_is_anomaly")
    op.execute("DROP INDEX IF EXISTS ix_fact_predictions_created_at")

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP ROLE IF EXISTS analytics_reader")
