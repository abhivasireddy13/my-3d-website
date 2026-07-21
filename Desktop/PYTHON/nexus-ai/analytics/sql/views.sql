-- ============================================================
-- NEXUS AI Analytics Views
-- Version-controlled source of truth for Superset datasets.
-- Run with: psql -h postgres -U nexus -d nexus -f views.sql
-- ============================================================

-- ── Revenue trend (time-series backbone) ─────────────────────────────────────
CREATE OR REPLACE VIEW vw_revenue_trend AS
SELECT
    dd.full_date                          AS date,
    dd.year,
    dd.quarter,
    dd.month,
    dd.month_name,
    dd.week_of_year                       AS week,
    dd.is_weekend,
    SUM(fs.revenue)                       AS revenue,
    SUM(fs.units)                         AS units,
    COUNT(*)                              AS n_transactions,
    AVG(fs.revenue)                       AS avg_revenue_per_tx
FROM fact_sales fs
JOIN dim_date dd ON fs.date_key = dd.date_key
GROUP BY
    dd.full_date, dd.year, dd.quarter, dd.month,
    dd.month_name, dd.week_of_year, dd.is_weekend;

-- ── Regional performance ──────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_region_sales AS
SELECT
    dr.region_name,
    dr.country,
    SUM(fs.revenue)                       AS total_revenue,
    SUM(fs.units)                         AS total_units,
    COUNT(*)                              AS n_sales,
    AVG(fs.revenue)                       AS avg_revenue,
    COUNT(DISTINCT fs.job_id)             AS n_upload_jobs
FROM fact_sales fs
JOIN dim_region dr ON fs.region_key = dr.region_key
GROUP BY dr.region_name, dr.country;

-- ── Product performance ───────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_product_sales AS
SELECT
    dp.product_name,
    dp.category,
    SUM(fs.revenue)                       AS total_revenue,
    SUM(fs.units)                         AS total_units,
    AVG(fs.revenue)                       AS avg_revenue,
    COUNT(*)                              AS n_sales,
    RANK() OVER (ORDER BY SUM(fs.revenue) DESC) AS revenue_rank
FROM fact_sales fs
JOIN dim_product dp ON fs.product_key = dp.product_key
GROUP BY dp.product_name, dp.category;

-- ── Customer segment analysis ─────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_customer_segments AS
SELECT
    COALESCE(dc.segment, 'Unspecified')   AS segment,
    COUNT(DISTINCT dc.customer_key)       AS n_customers,
    SUM(fs.revenue)                       AS total_revenue,
    SUM(fs.units)                         AS total_units,
    AVG(fs.revenue)                       AS avg_revenue_per_tx,
    COUNT(*)                              AS n_transactions
FROM fact_sales fs
JOIN dim_customer dc ON fs.customer_key = dc.customer_key
GROUP BY dc.segment;

-- ── Forecast vs actuals overlay ───────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_forecast_vs_actual AS
SELECT
    dd.full_date                          AS date,
    dr.region_name,
    SUM(fs.revenue)                       AS actual_revenue,
    SUM(fs.units)                         AS actual_units,
    -- latest forecast for the same job (NULL when no model run yet)
    MAX(fp.prediction_value)
        FILTER (WHERE fp.model_name ILIKE '%sales%forecast%')
                                          AS forecasted_revenue,
    COUNT(fp.prediction_id)
        FILTER (WHERE fp.is_anomaly = TRUE)
                                          AS n_anomalies_in_job
FROM fact_sales fs
JOIN dim_date   dd ON fs.date_key   = dd.date_key
JOIN dim_region dr ON fs.region_key = dr.region_key
LEFT JOIN fact_predictions fp
       ON fs.job_id = fp.upload_job_id
GROUP BY dd.full_date, dr.region_name
ORDER BY dd.full_date;

-- ── Anomaly timeline ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_anomaly_timeline AS
SELECT
    fp.created_at::date                   AS anomaly_date,
    fp.model_name,
    fp.model_version,
    COUNT(*) FILTER (WHERE fp.is_anomaly = TRUE)   AS n_anomalies,
    COUNT(*) FILTER (WHERE fp.is_anomaly = FALSE)  AS n_normal,
    COUNT(*) FILTER (WHERE fp.is_anomaly IS NULL)  AS n_forecast,
    AVG(fp.prediction_value)              AS avg_score,
    MIN(fp.prediction_value)              AS min_score,
    MAX(fp.prediction_value)              AS max_score
FROM fact_predictions fp
GROUP BY fp.created_at::date, fp.model_name, fp.model_version
ORDER BY anomaly_date DESC;

-- ── Executive KPI summary (one row per upload job) ────────────────────────────
CREATE OR REPLACE VIEW vw_kpi_per_job AS
SELECT
    uj.id                                 AS job_id,
    uj.filename,
    uj.status,
    uj.created_at                         AS job_created_at,
    COUNT(fs.sale_key)                    AS n_records,
    SUM(fs.revenue)                       AS total_revenue,
    SUM(fs.units)                         AS total_units,
    MIN(dd.full_date)                     AS first_sale_date,
    MAX(dd.full_date)                     AS last_sale_date,
    COUNT(fp.prediction_id)
        FILTER (WHERE fp.is_anomaly = TRUE)    AS n_anomalies,
    COUNT(fp.prediction_id)
        FILTER (WHERE fp.model_name ILIKE '%sales%forecast%')
                                          AS n_forecasts
FROM upload_jobs uj
LEFT JOIN fact_sales       fs ON uj.id = fs.job_id
LEFT JOIN dim_date         dd ON fs.date_key = dd.date_key
LEFT JOIN fact_predictions fp ON uj.id = fp.upload_job_id
GROUP BY uj.id, uj.filename, uj.status, uj.created_at
ORDER BY uj.created_at DESC;

-- ── Top products by revenue (leaderboard) ────────────────────────────────────
CREATE OR REPLACE VIEW vw_top_products AS
SELECT
    dp.product_name,
    dp.category,
    SUM(fs.revenue)   AS total_revenue,
    SUM(fs.units)     AS total_units
FROM fact_sales fs
JOIN dim_product dp ON fs.product_key = dp.product_key
GROUP BY dp.product_name, dp.category
ORDER BY total_revenue DESC
LIMIT 20;
