"""
Idempotent Superset dashboard provisioner.

Called by docker-entrypoint.sh after Superset is running.
Creates the warehouse database connection, SQL-view-based datasets,
charts, and three dashboards via the Superset REST API.

Pre-assigned dashboard UUIDs — stable across restarts so the backend
embed-token endpoint can reference them without reading Superset's DB.
"""
import json
import os
import sys
import time

import requests

# ─── Config ───────────────────────────────────────────────────────────────────
SUPERSET_URL  = "http://localhost:8088"
ADMIN_USER    = os.getenv("SUPERSET_ADMIN_USERNAME", "admin")
ADMIN_PASS    = os.getenv("SUPERSET_ADMIN_PASSWORD", "admin")

PG_USER = os.getenv("POSTGRES_USER", "nexus")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "nexus")
PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_DB   = os.getenv("POSTGRES_DB", "nexus")

WAREHOUSE_URI = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}"

# Pre-assigned UUIDs — must match backend/app/core/config.py SUPERSET_DASHBOARD_*
DASH_EXEC_UUID    = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
DASH_SALES_UUID   = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
DASH_ANOMALY_UUID = "c3d4e5f6-a7b8-9012-cdef-123456789012"


# ─── Auth helper ──────────────────────────────────────────────────────────────

def _login() -> dict:
    resp = requests.post(
        f"{SUPERSET_URL}/api/v1/security/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASS,
              "provider": "db", "refresh": True},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_csrf(headers: dict) -> str:
    resp = requests.get(f"{SUPERSET_URL}/api/v1/security/csrf_token/",
                        headers=headers, timeout=15)
    if resp.ok:
        return resp.json().get("result", "")
    return ""


# ─── Database (warehouse connection) ──────────────────────────────────────────

def ensure_database(headers: dict) -> int:
    """Return existing database id or create one. Returns the database id."""
    resp = requests.get(
        f"{SUPERSET_URL}/api/v1/database/",
        headers=headers,
        params={"q": json.dumps({"filters": [{"col": "database_name", "opr": "eq",
                                               "val": "NEXUS Warehouse"}]})},
        timeout=30,
    )
    resp.raise_for_status()
    existing = resp.json().get("result", [])
    if existing:
        db_id = existing[0]["id"]
        print(f"  [db] Using existing database id={db_id}")
        return db_id

    print("  [db] Creating NEXUS Warehouse connection...")
    payload = {
        "database_name": "NEXUS Warehouse",
        "sqlalchemy_uri": WAREHOUSE_URI,
        "expose_in_sqllab": True,
        "allow_run_async": False,
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
    }
    resp = requests.post(f"{SUPERSET_URL}/api/v1/database/",
                         headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    db_id = resp.json()["id"]
    print(f"  [db] Created database id={db_id}")
    return db_id


# ─── Datasets (one per view) ──────────────────────────────────────────────────

_VIEW_NAMES = [
    "vw_revenue_trend",
    "vw_region_sales",
    "vw_product_sales",
    "vw_customer_segments",
    "vw_forecast_vs_actual",
    "vw_anomaly_timeline",
    "vw_kpi_per_job",
]


def ensure_datasets(headers: dict, db_id: int) -> dict[str, int]:
    """Return mapping {view_name: dataset_id}, creating missing ones."""
    resp = requests.get(
        f"{SUPERSET_URL}/api/v1/dataset/",
        headers=headers,
        params={"q": json.dumps({"page_size": 100})},
        timeout=30,
    )
    resp.raise_for_status()
    existing: dict[str, int] = {
        row["table_name"]: row["id"]
        for row in resp.json().get("result", [])
    }

    dataset_ids: dict[str, int] = {}
    for view_name in _VIEW_NAMES:
        if view_name in existing:
            dataset_ids[view_name] = existing[view_name]
            print(f"  [dataset] {view_name} already exists (id={existing[view_name]})")
            continue

        print(f"  [dataset] Creating {view_name}...")
        payload = {
            "database": db_id,
            "schema": "public",
            "table_name": view_name,
            "owners": [],
        }
        r = requests.post(f"{SUPERSET_URL}/api/v1/dataset/",
                          headers=headers, json=payload, timeout=30)
        if r.ok:
            dataset_ids[view_name] = r.json()["id"]
            print(f"  [dataset] Created id={dataset_ids[view_name]}")
        else:
            print(f"  [dataset] WARN: failed to create {view_name}: {r.text[:200]}")

    return dataset_ids


# ─── Charts ───────────────────────────────────────────────────────────────────

def _chart_exists(headers: dict, name: str) -> int | None:
    resp = requests.get(
        f"{SUPERSET_URL}/api/v1/chart/",
        headers=headers,
        params={"q": json.dumps({"filters": [{"col": "slice_name", "opr": "eq",
                                               "val": name}]})},
        timeout=30,
    )
    if resp.ok:
        results = resp.json().get("result", [])
        if results:
            return results[0]["id"]
    return None


def _create_chart(headers: dict, payload: dict) -> int | None:
    name = payload.get("slice_name", "?")
    existing_id = _chart_exists(headers, name)
    if existing_id:
        print(f"  [chart] '{name}' already exists (id={existing_id})")
        return existing_id

    resp = requests.post(f"{SUPERSET_URL}/api/v1/chart/",
                         headers=headers, json=payload, timeout=30)
    if resp.ok:
        cid = resp.json()["id"]
        print(f"  [chart] Created '{name}' id={cid}")
        return cid
    print(f"  [chart] WARN: failed '{name}': {resp.text[:200]}")
    return None


def _kpi_params(metric_expr: str, fmt: str = ",.2f", suffix: str = "") -> str:
    return json.dumps({
        "viz_type": "big_number_total",
        "metric": {
            "expressionType": "SQL",
            "sqlExpression": metric_expr,
            "label": metric_expr,
        },
        "subheader": suffix,
        "time_range": "No filter",
        "y_axis_format": fmt,
        "force_timestamp_formatting": False,
    })


def _line_params(metric_expr: str, label: str, granularity: str = "date") -> str:
    return json.dumps({
        "viz_type": "echarts_timeseries_line",
        "metrics": [{
            "expressionType": "SQL",
            "sqlExpression": metric_expr,
            "label": label,
        }],
        "groupby": [],
        "granularity_sqla": granularity,
        "time_grain_sqla": "P1D",
        "time_range": "No filter",
        "show_value": False,
        "rich_tooltip": True,
    })


def _bar_params(metric_expr: str, label: str, group_by: list[str]) -> str:
    return json.dumps({
        "viz_type": "echarts_bar",
        "metrics": [{
            "expressionType": "SQL",
            "sqlExpression": metric_expr,
            "label": label,
        }],
        "groupby": group_by,
        "time_range": "No filter",
        "row_limit": 20,
        "show_value": True,
    })


def _pie_params(metric_expr: str, label: str, group_by: list[str]) -> str:
    return json.dumps({
        "viz_type": "pie",
        "metric": {
            "expressionType": "SQL",
            "sqlExpression": metric_expr,
            "label": label,
        },
        "groupby": group_by,
        "time_range": "No filter",
        "row_limit": 10,
        "show_legend": True,
        "donut": False,
    })


def _table_params(cols: list[str]) -> str:
    return json.dumps({
        "viz_type": "table",
        "query_mode": "raw",
        "all_columns": cols,
        "time_range": "No filter",
        "row_limit": 50,
        "show_cell_bars": True,
    })


def ensure_charts(headers: dict, ds: dict[str, int]) -> dict[str, int]:
    """Create all charts and return {chart_name: chart_id}."""
    chart_ids: dict[str, int] = {}

    def add(name: str, payload: dict) -> None:
        cid = _create_chart(headers, payload)
        if cid:
            chart_ids[name] = cid

    # ── Executive Overview charts ──────────────────────────────────────────
    add("Total Revenue", {
        "slice_name": "Total Revenue",
        "datasource_id": ds["vw_kpi_per_job"],
        "datasource_type": "table",
        "viz_type": "big_number_total",
        "params": _kpi_params("SUM(total_revenue)", "$,.0f", "All time"),
    })
    add("Total Units Sold", {
        "slice_name": "Total Units Sold",
        "datasource_id": ds["vw_kpi_per_job"],
        "datasource_type": "table",
        "viz_type": "big_number_total",
        "params": _kpi_params("SUM(total_units)", ",.0f", "All time"),
    })
    add("Completed Upload Jobs", {
        "slice_name": "Completed Upload Jobs",
        "datasource_id": ds["vw_kpi_per_job"],
        "datasource_type": "table",
        "viz_type": "big_number_total",
        "params": _kpi_params("COUNT(DISTINCT job_id)", ",.0f", "Jobs processed"),
    })
    add("Total Anomalies Detected", {
        "slice_name": "Total Anomalies Detected",
        "datasource_id": ds["vw_kpi_per_job"],
        "datasource_type": "table",
        "viz_type": "big_number_total",
        "params": _kpi_params("SUM(n_anomalies)", ",.0f", "ML flagged"),
    })
    add("Revenue over Time", {
        "slice_name": "Revenue over Time",
        "datasource_id": ds["vw_revenue_trend"],
        "datasource_type": "table",
        "viz_type": "echarts_timeseries_line",
        "params": _line_params("SUM(revenue)", "Revenue ($)"),
    })
    add("Sales by Region", {
        "slice_name": "Sales by Region",
        "datasource_id": ds["vw_region_sales"],
        "datasource_type": "table",
        "viz_type": "echarts_bar",
        "params": _bar_params("SUM(total_revenue)", "Revenue", ["region_name"]),
    })
    add("Customer Segment Distribution", {
        "slice_name": "Customer Segment Distribution",
        "datasource_id": ds["vw_customer_segments"],
        "datasource_type": "table",
        "viz_type": "pie",
        "params": _pie_params("SUM(total_revenue)", "Revenue", ["segment"]),
    })

    # ── Sales Deep Dive charts ─────────────────────────────────────────────
    add("Forecast vs Actual Revenue", {
        "slice_name": "Forecast vs Actual Revenue",
        "datasource_id": ds["vw_forecast_vs_actual"],
        "datasource_type": "table",
        "viz_type": "echarts_timeseries_line",
        "params": json.dumps({
            "viz_type": "echarts_timeseries_line",
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "SUM(actual_revenue)",
                 "label": "Actual Revenue"},
                {"expressionType": "SQL", "sqlExpression": "SUM(forecasted_revenue)",
                 "label": "Forecasted Revenue"},
            ],
            "groupby": [],
            "granularity_sqla": "date",
            "time_grain_sqla": "P1D",
            "time_range": "No filter",
            "rich_tooltip": True,
        }),
    })
    add("Sales by Product", {
        "slice_name": "Sales by Product",
        "datasource_id": ds["vw_product_sales"],
        "datasource_type": "table",
        "viz_type": "echarts_bar",
        "params": _bar_params("SUM(total_revenue)", "Revenue", ["product_name"]),
    })
    add("Top Products Table", {
        "slice_name": "Top Products Table",
        "datasource_id": ds["vw_product_sales"],
        "datasource_type": "table",
        "viz_type": "table",
        "params": _table_params(["product_name", "category",
                                  "total_revenue", "total_units", "revenue_rank"]),
    })
    add("Revenue by Region and Product", {
        "slice_name": "Revenue by Region and Product",
        "datasource_id": ds["vw_forecast_vs_actual"],
        "datasource_type": "table",
        "viz_type": "echarts_bar",
        "params": _bar_params("SUM(actual_revenue)", "Actual Revenue", ["region_name"]),
    })
    add("Units Sold over Time", {
        "slice_name": "Units Sold over Time",
        "datasource_id": ds["vw_revenue_trend"],
        "datasource_type": "table",
        "viz_type": "echarts_timeseries_line",
        "params": _line_params("SUM(units)", "Units Sold"),
    })

    # ── Anomaly / Ops Monitor charts ───────────────────────────────────────
    add("Anomaly Count over Time", {
        "slice_name": "Anomaly Count over Time",
        "datasource_id": ds["vw_anomaly_timeline"],
        "datasource_type": "table",
        "viz_type": "echarts_timeseries_line",
        "params": json.dumps({
            "viz_type": "echarts_timeseries_line",
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "SUM(n_anomalies)",
                 "label": "Anomalies"},
                {"expressionType": "SQL", "sqlExpression": "SUM(n_normal)",
                 "label": "Normal"},
            ],
            "groupby": [],
            "granularity_sqla": "anomaly_date",
            "time_grain_sqla": "P1D",
            "time_range": "No filter",
            "rich_tooltip": True,
        }),
    })
    add("KPI: Total Anomalies", {
        "slice_name": "KPI: Total Anomalies",
        "datasource_id": ds["vw_anomaly_timeline"],
        "datasource_type": "table",
        "viz_type": "big_number_total",
        "params": _kpi_params("SUM(n_anomalies)", ",.0f", "All time"),
    })
    add("Anomaly Score Distribution", {
        "slice_name": "Anomaly Score Distribution",
        "datasource_id": ds["vw_anomaly_timeline"],
        "datasource_type": "table",
        "viz_type": "echarts_timeseries_line",
        "params": json.dumps({
            "viz_type": "echarts_timeseries_line",
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "AVG(avg_score)",
                 "label": "Avg Anomaly Score"},
                {"expressionType": "SQL", "sqlExpression": "MIN(min_score)",
                 "label": "Min Score"},
            ],
            "groupby": [],
            "granularity_sqla": "anomaly_date",
            "time_grain_sqla": "P1D",
            "time_range": "No filter",
        }),
    })
    add("Pipeline Jobs Status", {
        "slice_name": "Pipeline Jobs Status",
        "datasource_id": ds["vw_kpi_per_job"],
        "datasource_type": "table",
        "viz_type": "table",
        "params": _table_params(["filename", "status", "n_records",
                                  "total_revenue", "n_anomalies", "job_created_at"]),
    })
    add("Anomaly Rate by Model", {
        "slice_name": "Anomaly Rate by Model",
        "datasource_id": ds["vw_anomaly_timeline"],
        "datasource_type": "table",
        "viz_type": "echarts_bar",
        "params": _bar_params("SUM(n_anomalies)", "Anomalies", ["model_name"]),
    })

    return chart_ids


# ─── Dashboards ───────────────────────────────────────────────────────────────

def _dashboard_exists(headers: dict, slug: str) -> int | None:
    resp = requests.get(
        f"{SUPERSET_URL}/api/v1/dashboard/",
        headers=headers,
        params={"q": json.dumps({"filters": [{"col": "slug", "opr": "eq",
                                               "val": slug}]})},
        timeout=30,
    )
    if resp.ok:
        results = resp.json().get("result", [])
        if results:
            return results[0]["id"]
    return None


def _create_dashboard(headers: dict, title: str, slug: str, uuid: str,
                       chart_ids: list[int]) -> int | None:
    existing_id = _dashboard_exists(headers, slug)
    if existing_id:
        print(f"  [dash] '{title}' already exists (id={existing_id})")
        return existing_id

    # Build a simple grid layout: 2 charts per row
    CHART_W, CHART_H = 12, 50  # Superset grid units (24-wide grid)
    CHARTS_PER_ROW = 2
    components: dict = {
        "GRID_ID": {
            "id": "GRID_ID",
            "type": "GRID",
            "children": [],
            "parents": ["ROOT_ID"],
        },
        "HEADER_ID": {
            "id": "HEADER_ID",
            "type": "HEADER",
            "meta": {"text": title},
        },
    }
    row_ids: list[str] = []
    for row_idx in range(0, len(chart_ids), CHARTS_PER_ROW):
        row_id = f"ROW_{slug}_{row_idx}"
        row_chart_ids = chart_ids[row_idx: row_idx + CHARTS_PER_ROW]
        chart_comp_ids: list[str] = []
        for col_idx, cid in enumerate(row_chart_ids):
            comp_id = f"CHART_{slug}_{row_idx}_{col_idx}"
            components[comp_id] = {
                "id": comp_id,
                "type": "CHART",
                "meta": {
                    "chartId": cid,
                    "width": CHART_W,
                    "height": CHART_H,
                    "sliceName": "",
                },
                "parents": [row_id],
            }
            chart_comp_ids.append(comp_id)

        components[row_id] = {
            "id": row_id,
            "type": "ROW",
            "children": chart_comp_ids,
            "parents": ["GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        row_ids.append(row_id)

    components["GRID_ID"]["children"] = row_ids

    layout_json = json.dumps({**components, "ROOT_ID": {
        "id": "ROOT_ID",
        "type": "ROOT",
        "children": ["GRID_ID"],
    }})

    payload = {
        "dashboard_title": title,
        "slug": slug,
        "published": True,
        "json_metadata": json.dumps({
            "show_native_filters": True,
            "refresh_frequency": 0,  # live queries
            "color_scheme": "supersetColors",
        }),
        "position_json": layout_json,
    }

    # Pass pre-assigned UUID so embed URLs stay stable
    try:
        payload["uuid"] = uuid
    except Exception:
        pass  # older Superset versions don't accept uuid in POST — will be auto-assigned

    resp = requests.post(f"{SUPERSET_URL}/api/v1/dashboard/",
                         headers=headers, json=payload, timeout=30)
    if resp.ok:
        did = resp.json()["id"]
        print(f"  [dash] Created '{title}' id={did}")

        # Attach charts (some Superset versions require explicit chart association)
        for cid in chart_ids:
            requests.post(
                f"{SUPERSET_URL}/api/v1/dashboard/{did}/chart",
                headers=headers,
                json={"chart_id": cid},
                timeout=15,
            )

        # Enable embedding on this dashboard
        requests.post(
            f"{SUPERSET_URL}/api/v1/dashboard/{did}/embedded",
            headers=headers,
            json={"allowed_domains": []},  # allow all
            timeout=15,
        )
        return did
    print(f"  [dash] WARN: failed '{title}': {resp.text[:300]}")
    return None


def ensure_dashboards(headers: dict, chart_ids: dict[str, int]) -> None:
    """Create the three NEXUS AI dashboards."""

    cid = chart_ids  # alias

    exec_charts = [
        cid.get("Total Revenue"),
        cid.get("Total Units Sold"),
        cid.get("Completed Upload Jobs"),
        cid.get("Total Anomalies Detected"),
        cid.get("Revenue over Time"),
        cid.get("Sales by Region"),
        cid.get("Customer Segment Distribution"),
    ]

    sales_charts = [
        cid.get("Forecast vs Actual Revenue"),
        cid.get("Sales by Product"),
        cid.get("Revenue by Region and Product"),
        cid.get("Units Sold over Time"),
        cid.get("Top Products Table"),
    ]

    anomaly_charts = [
        cid.get("KPI: Total Anomalies"),
        cid.get("Anomaly Count over Time"),
        cid.get("Anomaly Score Distribution"),
        cid.get("Anomaly Rate by Model"),
        cid.get("Pipeline Jobs Status"),
    ]

    for title, slug, uuid, charts in [
        ("Executive Overview",  "exec-overview",  DASH_EXEC_UUID,    exec_charts),
        ("Sales Deep Dive",     "sales-deep-dive", DASH_SALES_UUID,   sales_charts),
        ("Anomaly & Ops Monitor", "anomaly-monitor", DASH_ANOMALY_UUID, anomaly_charts),
    ]:
        valid_charts = [c for c in charts if c is not None]
        _create_dashboard(headers, title, slug, uuid, valid_charts)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("[setup_dashboards] Starting Superset provisioner...")

    # Retry login for a few seconds in case Superset is still warming up
    headers: dict = {}
    for attempt in range(10):
        try:
            headers = _login()
            break
        except Exception as exc:
            if attempt == 9:
                print(f"FATAL: Could not authenticate with Superset: {exc}")
                sys.exit(1)
            print(f"  login attempt {attempt + 1} failed — retrying in 5 s...")
            time.sleep(5)

    print("[setup_dashboards] Logged in. Provisioning warehouse connection...")
    db_id = ensure_database(headers)

    print("[setup_dashboards] Provisioning datasets from SQL views...")
    dataset_ids = ensure_datasets(headers, db_id)

    print("[setup_dashboards] Provisioning charts...")
    chart_ids = ensure_charts(headers, dataset_ids)

    print("[setup_dashboards] Provisioning dashboards...")
    ensure_dashboards(headers, chart_ids)

    print("[setup_dashboards] Done.")


if __name__ == "__main__":
    main()
