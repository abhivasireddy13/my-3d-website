# Data Dictionary — NEXUS AI

All tables live in the `nexus` PostgreSQL database unless noted otherwise.
MongoDB collections live in the `nexus` Mongo database.

---

## PostgreSQL Tables

### `users`
Authentication and authorisation.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NO | Primary key (uuid4) |
| `email` | VARCHAR | NO | Unique user email |
| `hashed_password` | VARCHAR | NO | argon2id hash |
| `role` | ENUM(`admin`,`analyst`,`viewer`) | NO | RBAC role |
| `created_at` | TIMESTAMP | YES | Row creation time (UTC) |

---

### `upload_jobs`
One row per CSV upload. Tracks pipeline status.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NO | Primary key (uuid4) |
| `filename` | VARCHAR | NO | Original uploaded filename |
| `status` | VARCHAR | YES | Pipeline stage: `pending` → `validating` → `cleaning` → `storing` → `modeling` → `recommending` → `done` \| `failed` |
| `error_detail` | JSON | YES | Structured error when `status = failed` — includes `stage` and `detail` keys |
| `created_at` | TIMESTAMP | YES | Upload time (UTC) |
| `updated_at` | TIMESTAMP | YES | Last status change time (UTC) |

---

### `sales_data` *(staging)*
Flat, cleaned rows from each CSV upload. Kept for Phase 2 backward compatibility and as an intermediate staging layer before the star schema.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | SERIAL | NO | Primary key |
| `job_id` | UUID | NO | FK → `upload_jobs.id` (CASCADE) |
| `sale_date` | DATE | NO | Normalised sale date |
| `revenue` | NUMERIC(12,2) | NO | Daily revenue |
| `units` | INTEGER | NO | Units sold |
| `created_at` | TIMESTAMP | NO | Row insertion time (UTC) |

---

## Dimensional Model (Star Schema)

### `dim_date`
Calendar date dimension. Pre-populated 2020-01-01 → 2030-12-31.
Primary key is a YYYYMMDD integer (e.g. `20240601` for 2024-06-01).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `date_key` | INTEGER | NO | PK — YYYYMMDD integer |
| `full_date` | DATE | NO | Calendar date |
| `year` | SMALLINT | NO | 4-digit year |
| `quarter` | SMALLINT | NO | 1–4 |
| `month` | SMALLINT | NO | 1–12 |
| `month_name` | VARCHAR(10) | NO | e.g. `January` |
| `day` | SMALLINT | NO | Day of month 1–31 |
| `day_of_week` | SMALLINT | NO | 0 = Monday … 6 = Sunday |
| `day_name` | VARCHAR(10) | NO | e.g. `Monday` |
| `is_weekend` | BOOLEAN | NO | True for Saturday and Sunday |
| `week_of_year` | SMALLINT | NO | ISO week number 1–53 |

---

### `dim_product`
Product dimension. `product_key = 1` (`Unspecified`) is the default surrogate used when uploaded CSV data carries no product identifier.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `product_key` | SERIAL | NO | Surrogate PK |
| `product_name` | VARCHAR | NO | Product name |
| `category` | VARCHAR | YES | Product category |
| `created_at` | TIMESTAMP | NO | Row creation time (UTC) |

---

### `dim_region`
Region dimension. `region_key = 1` (`Unspecified`) is the default surrogate.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `region_key` | SERIAL | NO | Surrogate PK |
| `region_name` | VARCHAR | NO | Region name |
| `country` | VARCHAR | YES | Country name |
| `created_at` | TIMESTAMP | NO | Row creation time (UTC) |

---

### `dim_customer`
Customer dimension. `customer_key = 1` (`Unspecified`) is the default surrogate.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `customer_key` | SERIAL | NO | Surrogate PK |
| `customer_name` | VARCHAR | NO | Customer name |
| `segment` | VARCHAR | YES | Customer segment (e.g. `Retail`, `Enterprise`) |
| `created_at` | TIMESTAMP | NO | Row creation time (UTC) |

---

### `fact_sales`
Central fact table. One row per daily sales event, joined to all four dimension tables.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `sale_key` | BIGSERIAL | NO | Surrogate PK |
| `job_id` | UUID | NO | FK → `upload_jobs.id` (CASCADE) |
| `date_key` | INTEGER | NO | FK → `dim_date.date_key` |
| `product_key` | INTEGER | NO | FK → `dim_product.product_key` |
| `region_key` | INTEGER | NO | FK → `dim_region.region_key` |
| `customer_key` | INTEGER | NO | FK → `dim_customer.customer_key` |
| `revenue` | NUMERIC(12,2) | NO | Daily revenue |
| `units` | INTEGER | NO | Units sold |
| `created_at` | TIMESTAMP | NO | Row insertion time (UTC) |

#### Common analytical queries

```sql
-- Daily revenue with calendar attributes
SELECT d.full_date, d.day_name, d.week_of_year, f.revenue, f.units
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.job_id = '<uuid>'
ORDER BY d.full_date;

-- Monthly revenue rollup
SELECT d.year, d.month, d.month_name, SUM(f.revenue) AS total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- Weekend vs weekday revenue split
SELECT d.is_weekend, SUM(f.revenue), COUNT(*) AS days
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.is_weekend;
```

---

## MongoDB Collections

### `raw_uploads`
Stores file metadata for every uploaded CSV before ETL processing.

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Matches `upload_jobs.id` |
| `filename` | string | Original filename |
| `size_bytes` | number | File size in bytes |
| `file_path` | string | Absolute path on the storage volume |
| `uploaded_by` | string | User UUID who triggered the upload |

---

### `pipeline_results`
ETL output per completed job — natural-language summary and statistics.
Keyed by `job_id` (upserted; one document per job).

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Matches `upload_jobs.id` |
| `summary` | string | Human-readable recommendation paragraph |
| `stats.row_count` | number | Cleaned row count |
| `stats.date_range_start` | string | Earliest sale date |
| `stats.date_range_end` | string | Latest sale date |
| `stats.total_revenue` | number | Sum of revenue across all days |
| `stats.avg_revenue_per_day` | number | Mean daily revenue |
| `stats.max_revenue` | number | Highest single-day revenue |
| `stats.min_revenue` | number | Lowest single-day revenue |
| `stats.revenue_std_dev` | number | Standard deviation of daily revenue |
| `stats.total_units` | number | Sum of units sold |
| `stats.avg_units_per_day` | number | Mean daily units sold |
| `stats.peak_date` | string | Date of highest revenue |
| `stats.peak_revenue` | number | Revenue on peak date |
| `stats.revenue_trend_per_day` | number | Linear slope (revenue/day) |
| `generated_at` | string | ISO 8601 timestamp of recommendation generation |

---

### `workflow_logs`
Audit trail — one document per stage transition in the ETL pipeline.

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Matches `upload_jobs.id` |
| `stage` | string | Pipeline stage name (`validating`, `cleaning`, etc.) |
| `status` | string | `started` \| `passed` \| `failed` |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `detail` | object \| null | Additional context (row counts, error messages) |

---

### `validation_errors`
Reserved for future use — will store per-row validation failures for detailed error reporting.

---

## ETL CSV Input Schema

Uploaded CSV files must contain the following columns (header names are case-insensitive, extra columns are ignored):

| Column | Type | Example | Notes |
|---|---|---|---|
| `date` | Date string | `2024-06-01` | Accepted formats: `YYYY-MM-DD`, `YYYY/MM/DD`, `MM/DD/YYYY`, `DD/MM/YYYY` |
| `revenue` | Numeric | `1200.50` | Parsed as float, rounded to 2 decimal places |
| `units` | Integer | `42` | Parsed as int (float input is truncated) |

Minimum 2 data rows required. Rows with null/empty values in any required column are silently dropped during cleaning. Duplicate dates are deduplicated (first occurrence kept).
