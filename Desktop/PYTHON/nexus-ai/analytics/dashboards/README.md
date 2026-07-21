# NEXUS AI — Superset Dashboard Definitions

Three dashboards are provisioned automatically when Superset starts via
`automation/superset/setup_dashboards.py`. Each dashboard has a stable UUID
and slug that the backend uses for guest-token generation.

---

## Dashboard Registry

| # | Name | Slug | UUID |
|---|------|------|------|
| 1 | Executive Overview | `exec-overview` | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| 2 | Sales Deep Dive | `sales-deep-dive` | `b2c3d4e5-f6a7-8901-bcde-f12345678901` |
| 3 | Anomaly & Ops Monitor | `anomaly-monitor` | `c3d4e5f6-a7b8-9012-cdef-123456789012` |

---

## Dashboard 1 — Executive Overview

**Purpose:** High-level KPIs for stakeholders who want a single-page view of the pipeline output.

### KPI Cards
- Total Revenue (SUM of `fact_sales.revenue`)
- Total Units Sold (SUM of `fact_sales.units`)
- Completed Upload Jobs (COUNT of `upload_jobs` where `status='done'`)
- Total Anomalies Detected (COUNT of `fact_predictions` where `is_anomaly=true`)

### Charts
- **Revenue over Time** — line chart from `vw_revenue_trend` (daily granularity)
- **Sales by Region** — horizontal bar chart from `vw_region_sales`
- **Customer Segment Distribution** — pie chart from `vw_customer_segments`

### Filters
- Date range (native Superset filter)
- Region (cross-filter from the bar chart)

---

## Dashboard 2 — Sales Deep Dive

**Purpose:** Analysts comparing forecast accuracy and product/region mix.

### Charts
- **Forecast vs Actual Revenue** — dual-line chart from `vw_forecast_vs_actual`
  showing `actual_revenue` and `forecasted_revenue` over time
- **Sales by Product** — bar chart from `vw_product_sales`
- **Revenue by Region** — breakdown chart from `vw_forecast_vs_actual`
- **Units Sold over Time** — line chart from `vw_revenue_trend`
- **Top Products Table** — sortable table from `vw_product_sales` (rank, units, revenue)

### Filters
- Date range
- Region (cross-filter)
- Product category

---

## Dashboard 3 — Anomaly & Ops Monitor

**Purpose:** Operations team tracking ML anomaly flags and pipeline health.

### KPI Cards
- Total Anomalies (from `vw_anomaly_timeline`)

### Charts
- **Anomaly Count over Time** — dual-line chart (anomalies vs. normal predictions)
  from `vw_anomaly_timeline`
- **Anomaly Score Distribution** — avg/min score per day from `vw_anomaly_timeline`
- **Anomaly Rate by Model** — bar chart grouped by `model_name`
- **Pipeline Jobs Status** — table showing all upload jobs with status and KPIs

---

## SQL Views (Source of Truth)

All datasets are backed by views defined in `../sql/views.sql`.
Re-apply views after schema changes:

```bash
psql -h localhost -U nexus -d nexus -f analytics/sql/views.sql
```

---

## Exporting Dashboards

After making UI changes in Superset, export the updated definitions:

```bash
docker exec nexus-ai-superset-1 superset export-dashboards \
  -f /tmp/dashboards.zip --dashboard-ids 1,2,3
docker cp nexus-ai-superset-1:/tmp/dashboards.zip analytics/dashboards/
```

Re-import after a fresh start:
```bash
docker exec nexus-ai-superset-1 superset import-dashboards \
  -p /app/pythonpath/dashboards.zip
```

---

## Embedding

The frontend at `/dashboard` embeds each dashboard via the Superset guest token flow:

1. `GET /api/analytics/embed-token?dashboard_id={slug}` (Next.js → FastAPI backend)
2. Backend authenticates to Superset as admin, requests a 5-minute guest token
3. Frontend embeds `<iframe src="http://localhost:8088/superset/dashboard/{uuid}/?guest_token={token}&standalone=3">`

Guest tokens expire after 5 minutes. The frontend auto-refreshes every 4 minutes.
