"""
ETL pipeline for uploaded CSV files.

Stages (matching the stepper UI):
  validating   → parse CSV, check required columns (date/revenue/units) + min rows
  cleaning     → normalise dates, cast types, drop nulls/dupes, sort by date
  storing      → write to staging (sales_data) then load star schema (fact_sales)
  modeling     → compute descriptive statistics
  recommending → write summary + stats to MongoDB pipeline_results
  done

Every stage transition is audited to the MongoDB workflow_logs collection
(non-fatal — ETL continues even if MongoDB is temporarily unavailable).
"""

import csv
import io
import logging
import statistics
import uuid as _uuid
from datetime import date, datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db.mongo import pipeline_results, workflow_logs
from app.db.postgres import SessionLocal
from app.models.dim_customer import DimCustomer
from app.models.dim_date import DimDate
from app.models.dim_product import DimProduct
from app.models.dim_region import DimRegion
from app.models.fact_sales import FactSales
from app.models.sales_data import SalesData
from app.models.upload_job import UploadJob

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS: frozenset[str] = frozenset({"date", "revenue", "units"})
MIN_ROWS = 2

_DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]

# Surrogate key used when the CSV carries no product / region / customer data.
_DEFAULT_SURROGATE_KEY = 1


# ─── Audit helper ─────────────────────────────────────────────────────────────

async def _audit(job_id: str, stage: str, status: str, detail: dict | None = None) -> None:
    """Write a non-blocking audit entry to MongoDB workflow_logs."""
    try:
        await workflow_logs.insert_one(
            {
                "job_id": job_id,
                "stage": stage,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detail": detail,
            }
        )
    except Exception as exc:
        logger.warning("workflow_logs write failed (non-fatal): %s", exc)


# ─── Status helper ────────────────────────────────────────────────────────────

def _set_status(
    db: Session,
    job: UploadJob,
    status: str,
    error_detail: dict[str, Any] | None = None,
) -> None:
    """Persist a status transition and emit a structured log line."""
    job.status = status
    job.error_detail = error_detail
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    if status == "failed":
        logger.error("ETL job %s failed | error=%s", job.id, error_detail)
    else:
        logger.info("ETL job %s → %s", job.id, status)


# ─── Date helpers ─────────────────────────────────────────────────────────────

def _parse_date(value: str) -> date | None:
    """Try each accepted date format; return None if none match."""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _date_to_key(d: date) -> int:
    """Convert a date to the YYYYMMDD integer used as dim_date primary key."""
    return int(d.strftime("%Y%m%d"))


def _build_dim_date_record(d: date) -> DimDate:
    return DimDate(
        date_key=_date_to_key(d),
        full_date=d,
        year=d.year,
        quarter=(d.month - 1) // 3 + 1,
        month=d.month,
        month_name=d.strftime("%B"),
        day=d.day,
        day_of_week=d.weekday(),       # 0 = Monday … 6 = Sunday
        day_name=d.strftime("%A"),
        is_weekend=d.weekday() >= 5,
        week_of_year=d.isocalendar()[1],
    )


# ─── Pipeline stages ──────────────────────────────────────────────────────────

def _stage_validate(content: bytes) -> list[dict[str, str]]:
    """Parse CSV bytes and assert required columns + minimum row count.

    Returns raw row list on success; raises ValueError on any structural issue.
    """
    try:
        text = content.decode("utf-8-sig")  # strip Excel BOM
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("CSV appears to be empty — no header row found")

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. "
            f"Expected: {sorted(REQUIRED_COLUMNS)}"
        )

    rows = list(reader)
    if len(rows) < MIN_ROWS:
        raise ValueError(
            f"CSV must contain at least {MIN_ROWS} data rows; got {len(rows)}"
        )

    return rows


def _stage_clean(
    raw_rows: list[dict[str, str]],
) -> list[dict[str, date | float | int]]:
    """Normalise, type-cast, and deduplicate raw CSV rows.

    - Rows with empty date / revenue / units are dropped.
    - Dates are normalised to a Python date (any of _DATE_FORMATS).
    - Revenue cast to float (2 dp); units cast to int.
    - Rows with unparseable numerics or dates are dropped.
    - Duplicate sale_dates are deduplicated (first occurrence wins).
    - Output sorted ascending by sale_date.

    Raises ValueError if no valid rows remain.
    """
    seen: set[date] = set()
    cleaned: list[dict[str, date | float | int]] = []

    for raw in raw_rows:
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}

        if not row.get("date") or not row.get("revenue") or not row.get("units"):
            continue

        parsed_date = _parse_date(row["date"])
        if parsed_date is None:
            logger.debug("Dropping row — unparseable date: %r", row["date"])
            continue

        if parsed_date in seen:
            logger.debug("Dropping row — duplicate date: %s", parsed_date)
            continue

        try:
            revenue = round(float(row["revenue"]), 2)
            units = int(float(row["units"]))
        except ValueError:
            logger.debug("Dropping row — non-numeric revenue/units: %r", row)
            continue

        seen.add(parsed_date)
        cleaned.append({"sale_date": parsed_date, "revenue": revenue, "units": units})

    if not cleaned:
        raise ValueError(
            "No valid rows remain after cleaning. "
            "Check that date, revenue, and units columns contain parseable values."
        )

    cleaned.sort(key=lambda r: r["sale_date"])  # type: ignore[arg-type]
    return cleaned


def _ensure_default_dimensions(db: Session) -> None:
    """Seed the default 'Unspecified' surrogate rows if they are absent.

    Required in test environments where Alembic migrations don't run and
    the dimension tables are created empty by Base.metadata.create_all.
    """
    if not db.get(DimProduct, _DEFAULT_SURROGATE_KEY):
        db.add(DimProduct(product_key=_DEFAULT_SURROGATE_KEY, product_name="Unspecified"))
        db.flush()

    if not db.get(DimRegion, _DEFAULT_SURROGATE_KEY):
        db.add(DimRegion(region_key=_DEFAULT_SURROGATE_KEY, region_name="Unspecified"))
        db.flush()

    if not db.get(DimCustomer, _DEFAULT_SURROGATE_KEY):
        db.add(DimCustomer(customer_key=_DEFAULT_SURROGATE_KEY, customer_name="Unspecified"))
        db.flush()

    db.commit()


def _ensure_dim_date(db: Session, d: date) -> int:
    """Return date_key for d, inserting a new dim_date record if missing."""
    key = _date_to_key(d)
    if not db.get(DimDate, key):
        db.add(_build_dim_date_record(d))
        db.flush()
    return key


def _stage_store(
    rows: list[dict[str, date | float | int]],
    job_id: _uuid.UUID,
    db: Session,
) -> None:
    """Write cleaned rows to both staging (sales_data) and star schema (fact_sales).

    sales_data  — flat staging table, kept for Phase 2 backward compatibility.
    fact_sales  — star-schema fact table linked to all four dimension tables.
    """
    # Ensure default dimension surrogates exist (no-op on Postgres after migration).
    _ensure_default_dimensions(db)

    # ── Staging load ─────────────────────────────────────────────────────────
    staging_objects = [
        SalesData(
            job_id=job_id,
            sale_date=r["sale_date"],
            revenue=r["revenue"],
            units=r["units"],
        )
        for r in rows
    ]
    db.bulk_save_objects(staging_objects)
    db.flush()
    logger.info("ETL job %s: %d rows → sales_data (staging)", job_id, len(rows))

    # ── Star-schema load ──────────────────────────────────────────────────────
    fact_objects = []
    for r in rows:
        date_key = _ensure_dim_date(db, r["sale_date"])  # type: ignore[arg-type]
        fact_objects.append(
            FactSales(
                job_id=job_id,
                date_key=date_key,
                product_key=_DEFAULT_SURROGATE_KEY,
                region_key=_DEFAULT_SURROGATE_KEY,
                customer_key=_DEFAULT_SURROGATE_KEY,
                revenue=r["revenue"],
                units=r["units"],
            )
        )

    db.bulk_save_objects(fact_objects)
    db.commit()
    logger.info("ETL job %s: %d rows → fact_sales (star schema)", job_id, len(rows))


def _stage_model(
    rows: list[dict[str, date | float | int]],
    job_id: _uuid.UUID,
) -> dict[str, Any]:
    """Compute descriptive statistics over the cleaned dataset.

    In production this stage would call ml-service for forecasting /
    anomaly detection. Here it returns a comprehensive stats dict.
    """
    revenues = [float(r["revenue"]) for r in rows]
    units_list = [int(r["units"]) for r in rows]

    # Linear revenue trend (slope = revenue / day).
    if len(revenues) >= 2:
        first_day: date = rows[0]["sale_date"]  # type: ignore[assignment]
        xs = [(r["sale_date"] - first_day).days for r in rows]  # type: ignore[operator]
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(revenues)
        numerator = sum(
            (x - x_mean) * (y - y_mean) for x, y in zip(xs, revenues)
        )
        denominator = sum((x - x_mean) ** 2 for x in xs)
        slope = numerator / denominator if denominator else 0.0
    else:
        slope = 0.0

    peak_row = max(rows, key=lambda r: r["revenue"])

    stats: dict[str, Any] = {
        "row_count": len(rows),
        "date_range_start": str(rows[0]["sale_date"]),
        "date_range_end": str(rows[-1]["sale_date"]),
        "total_revenue": round(sum(revenues), 2),
        "avg_revenue_per_day": round(statistics.mean(revenues), 2),
        "max_revenue": round(max(revenues), 2),
        "min_revenue": round(min(revenues), 2),
        "revenue_std_dev": (
            round(statistics.stdev(revenues), 4) if len(revenues) > 1 else 0.0
        ),
        "total_units": sum(units_list),
        "avg_units_per_day": round(statistics.mean(units_list), 2),
        "peak_date": str(peak_row["sale_date"]),
        "peak_revenue": float(peak_row["revenue"]),
        "revenue_trend_per_day": round(slope, 4),
    }

    logger.info(
        "ETL job %s: model | rows=%d total_revenue=%.2f trend=%.4f",
        job_id,
        stats["row_count"],
        stats["total_revenue"],
        stats["revenue_trend_per_day"],
    )
    return stats


async def _stage_recommend(
    stats: dict[str, Any],
    job_id: _uuid.UUID,
) -> None:
    """Generate a natural-language summary and persist it to MongoDB."""
    trend = stats["revenue_trend_per_day"]
    if trend > 0.5:
        trend_text = f"growing (+${trend:.2f}/day)"
    elif trend < -0.5:
        trend_text = f"declining (${trend:.2f}/day)"
    else:
        trend_text = "stable"

    summary = (
        f"Analysed {stats['row_count']} days of sales data "
        f"({stats['date_range_start']} to {stats['date_range_end']}). "
        f"Total revenue: ${stats['total_revenue']:,.2f} "
        f"(avg ${stats['avg_revenue_per_day']:,.2f}/day). "
        f"Revenue trend is {trend_text}. "
        f"Peak day: {stats['peak_date']} (${stats['peak_revenue']:,.2f}). "
        f"Total units sold: {stats['total_units']}."
    )

    document = {
        "job_id": str(job_id),
        "summary": summary,
        "stats": stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await pipeline_results.replace_one(
        {"job_id": str(job_id)},
        document,
        upsert=True,
    )
    logger.info("ETL job %s: recommendation written to MongoDB", job_id)


# ─── Public entry point ───────────────────────────────────────────────────────

async def run_etl(
    job_id: str,
    file_path: str,
    _session_factory: Callable[[], Session] | None = None,
) -> None:
    """Run the full ETL pipeline for a completed file upload.

    Creates its own DB session — the request session is already closed
    by the time BackgroundTasks fires. Pass `_session_factory` in tests
    to route through the SQLite TestingSession instead of real Postgres.
    """
    factory = _session_factory or SessionLocal
    db: Session = factory()
    job_uuid = _uuid.UUID(job_id)

    try:
        job: UploadJob | None = (
            db.query(UploadJob).filter(UploadJob.id == job_uuid).first()
        )
        if job is None:
            logger.error("ETL: job %s not found in database — aborting", job_id)
            return

        # ── Stage 1: Validate ────────────────────────────────────────────────
        await _audit(job_id, "validating", "started")
        try:
            content = open(file_path, "rb").read()
            raw_rows = _stage_validate(content)
        except (ValueError, OSError) as exc:
            err = {"stage": "validating", "detail": str(exc)}
            _set_status(db, job, "failed", err)
            await _audit(job_id, "validating", "failed", err)
            return
        _set_status(db, job, "cleaning")
        await _audit(job_id, "validating", "passed", {"row_count": len(raw_rows)})

        # ── Stage 2: Clean ───────────────────────────────────────────────────
        await _audit(job_id, "cleaning", "started")
        try:
            clean_rows = _stage_clean(raw_rows)
        except ValueError as exc:
            err = {"stage": "cleaning", "detail": str(exc)}
            _set_status(db, job, "failed", err)
            await _audit(job_id, "cleaning", "failed", err)
            return
        _set_status(db, job, "storing")
        await _audit(job_id, "cleaning", "passed", {"clean_row_count": len(clean_rows)})

        # ── Stage 3: Store (staging + star schema) ───────────────────────────
        await _audit(job_id, "storing", "started")
        try:
            _stage_store(clean_rows, job_uuid, db)
        except Exception as exc:
            logger.exception("ETL job %s: storage error", job_id)
            err = {"stage": "storing", "detail": str(exc)}
            _set_status(db, job, "failed", err)
            await _audit(job_id, "storing", "failed", err)
            return
        _set_status(db, job, "modeling")
        await _audit(job_id, "storing", "passed", {"rows_stored": len(clean_rows)})

        # ── Stage 4: Model ───────────────────────────────────────────────────
        await _audit(job_id, "modeling", "started")
        try:
            stats = _stage_model(clean_rows, job_uuid)
        except Exception as exc:
            logger.exception("ETL job %s: modeling error", job_id)
            err = {"stage": "modeling", "detail": str(exc)}
            _set_status(db, job, "failed", err)
            await _audit(job_id, "modeling", "failed", err)
            return
        _set_status(db, job, "recommending")
        await _audit(job_id, "modeling", "passed", {"stats": stats})

        # ── Stage 5: Recommend ───────────────────────────────────────────────
        await _audit(job_id, "recommending", "started")
        try:
            await _stage_recommend(stats, job_uuid)
        except Exception as exc:
            # MongoDB unavailability is non-fatal: mark done anyway.
            logger.warning(
                "ETL job %s: recommend write failed (non-fatal): %s", job_id, exc
            )
        _set_status(db, job, "done")
        await _audit(job_id, "recommending", "passed")

    except Exception as exc:
        logger.exception("ETL job %s: unexpected error", job_id)
        try:
            _set_status(db, job, "failed", {"stage": "unknown", "detail": str(exc)})
            await _audit(job_id, "unknown", "failed", {"detail": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
