"""add_dimensional_model

Revision ID: b7c8d9e0f1a2
Revises: a3f1c2d4e5b6
Create Date: 2026-07-21

Creates the star-schema dimensional tables:
  dim_date, dim_product, dim_region, dim_customer, fact_sales

dim_date is pre-populated for 2020-01-01 → 2030-12-31 using
PostgreSQL's generate_series, making it idempotent via ON CONFLICT.

Default "Unspecified" surrogate rows (key=1) are seeded into
dim_product, dim_region, and dim_customer so the ETL can load
fact_sales rows for CSVs that carry no product/region/customer data.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a3f1c2d4e5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Dimension tables ──────────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS dim_date (
            date_key     INTEGER     PRIMARY KEY,
            full_date    DATE        NOT NULL UNIQUE,
            year         SMALLINT    NOT NULL,
            quarter      SMALLINT    NOT NULL,
            month        SMALLINT    NOT NULL,
            month_name   VARCHAR(10) NOT NULL,
            day          SMALLINT    NOT NULL,
            day_of_week  SMALLINT    NOT NULL,
            day_name     VARCHAR(10) NOT NULL,
            is_weekend   BOOLEAN     NOT NULL,
            week_of_year SMALLINT    NOT NULL
        )
    """)

    # Pre-populate dim_date for 2020-01-01 → 2030-12-31 (~3 653 rows).
    # ON CONFLICT ensures this is safe to re-run.
    op.execute("""
        INSERT INTO dim_date (
            date_key, full_date, year, quarter, month, month_name,
            day, day_of_week, day_name, is_weekend, week_of_year
        )
        SELECT
            TO_CHAR(d, 'YYYYMMDD')::INTEGER,
            d::DATE,
            EXTRACT(YEAR    FROM d)::SMALLINT,
            EXTRACT(QUARTER FROM d)::SMALLINT,
            EXTRACT(MONTH   FROM d)::SMALLINT,
            TRIM(TO_CHAR(d, 'Month')),
            EXTRACT(DAY     FROM d)::SMALLINT,
            (EXTRACT(ISODOW FROM d) - 1)::SMALLINT,
            TRIM(TO_CHAR(d, 'Day')),
            EXTRACT(ISODOW  FROM d) IN (6, 7),
            EXTRACT(WEEK    FROM d)::SMALLINT
        FROM generate_series(
            '2020-01-01'::DATE,
            '2030-12-31'::DATE,
            '1 day'::INTERVAL
        ) AS d
        ON CONFLICT (date_key) DO NOTHING
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dim_product (
            product_key  SERIAL      PRIMARY KEY,
            product_name VARCHAR     NOT NULL,
            category     VARCHAR,
            created_at   TIMESTAMP   NOT NULL DEFAULT NOW()
        )
    """)

    # Seed default surrogate (key=1 reserved for "Unspecified").
    op.execute("""
        INSERT INTO dim_product (product_key, product_name, category)
        VALUES (1, 'Unspecified', NULL)
        ON CONFLICT (product_key) DO NOTHING
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dim_region (
            region_key   SERIAL      PRIMARY KEY,
            region_name  VARCHAR     NOT NULL,
            country      VARCHAR,
            created_at   TIMESTAMP   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        INSERT INTO dim_region (region_key, region_name, country)
        VALUES (1, 'Unspecified', NULL)
        ON CONFLICT (region_key) DO NOTHING
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_key  SERIAL    PRIMARY KEY,
            customer_name VARCHAR   NOT NULL,
            segment       VARCHAR,
            created_at    TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        INSERT INTO dim_customer (customer_key, customer_name, segment)
        VALUES (1, 'Unspecified', NULL)
        ON CONFLICT (customer_key) DO NOTHING
    """)

    # ── Fact table ────────────────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS fact_sales (
            sale_key     SERIAL      PRIMARY KEY,
            job_id       UUID        NOT NULL REFERENCES upload_jobs(id) ON DELETE CASCADE,
            date_key     INTEGER     NOT NULL REFERENCES dim_date(date_key),
            product_key  INTEGER     NOT NULL REFERENCES dim_product(product_key),
            region_key   INTEGER     NOT NULL REFERENCES dim_region(region_key),
            customer_key INTEGER     NOT NULL REFERENCES dim_customer(customer_key),
            revenue      NUMERIC(12,2) NOT NULL,
            units        INTEGER     NOT NULL,
            created_at   TIMESTAMP   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_sales_job_id   ON fact_sales (job_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fact_sales_date_key ON fact_sales (date_key)"
    )


def downgrade() -> None:
    op.drop_table("fact_sales")
    op.drop_table("dim_customer")
    op.drop_table("dim_region")
    op.drop_table("dim_product")
    op.drop_table("dim_date")
