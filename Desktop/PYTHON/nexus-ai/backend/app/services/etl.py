"""
ETL pipeline for uploaded CSV files.

Stages (matching the stepper UI):
  validating  → parse CSV, check required columns + minimum rows
  cleaning    → normalise dates, cast types, drop nulls/dupes
  storing     → bulk-insert cleaned rows into sales_data (Postgres)
  modeling    → compute descriptive statistics
  recommending→ write summary + stats to MongoDB pipeline_results
  done

On any unhandled exception the job is marked "failed" with a structured
error_detail so the frontend can surface it.
"""

import csv
import io
import logging
import statistics
import uuid as _uuid
from datetime import date, datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db.mongo import pipeline_results
from app.db.postgres import SessionLocal
from app.models.sales_data import SalesData
from app.models.upload_job import UploadJob

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS: frozenset[str] = frozenset({"date", "revenue", "units"})
MIN_ROWS = 2

# Date formats accepted during cleaning (tried in order).
_DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]


# ─── Internal helpers ─────────────────────────────────────────────────────────

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
        logger.error(
            "ETL job %s failed | error=%s", job.id, error_detail, stacklevel=2
        )
    else:
        logger.info("ETL job %s → %s", job.id, status)


def _parse_date(value: str) -> date | None:
    """Try each accepted date format; return None if none match."""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


# ─── Pipeline stages ──────────────────────────────────────────────────────────

def _stage_validate(content: bytes) -> list[dict[str, str]]:
    """Parse CSV bytes and assert required columns + minimum row count.

    Returns the raw row list (list of dicts) on success.
    Raises ValueError with a human-readable message on any structural problem.
    """
    try:
        # utf-8-sig strips the UTF-8 BOM that Excel adds to exported CSVs.
        text = content.decode("utf-8-sig")
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

    Rules:
    - Rows with empty date, revenue, or units are dropped.
    - Dates are normalised to a Python date object (any of _DATE_FORMATS).
    - Rows whose date cannot be parsed are dropped.
    - Revenue is cast to float and rounded to 2 dp; units to int.
    - Rows with non-numeric revenue or units are dropped.
    - Duplicate dates are deduplicated (first occurrence wins).
    - Output is sorted ascending by sale_date.

    Raises ValueError if no valid rows remain after cleaning.
    """
    seen: set[date] = set()
    cleaned: list[dict[str, date | float | int]] = []

    for raw in raw_rows:
        # Normalise keys and strip whitespace from values.
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}

        if not row.get("date") or not row.get("revenue") or not row.get("units"):
            continue  # skip rows with null/empty required fields

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


def _stage_store(
    rows: list[dict[str, date | float | int]],
    job_id: _uuid.UUID,
    db: Session,
) -> None:
    """Bulk-insert cleaned rows into the sales_data Postgres table."""
    objects = [
        SalesData(
            job_id=job_id,
            sale_date=r["sale_date"],
            revenue=r["revenue"],
            units=r["units"],
        )
        for r in rows
    ]
    db.bulk_save_objects(objects)
    db.commit()
    logger.info("ETL job %s: stored %d rows into sales_data", job_id, len(objects))


def _stage_model(
    rows: list[dict[str, date | float | int]],
    job_id: _uuid.UUID,
) -> dict[str, Any]:
    """Compute descriptive statistics over the cleaned dataset.

    In production this would call ml-service for forecasting/anomaly detection.
    Returns a stats dict consumed by the recommendation stage.
    """
    revenues = [float(r["revenue"]) for r in rows]
    units_list = [int(r["units"]) for r in rows]

    # Linear revenue trend (slope = revenue-per-day).
    if len(revenues) >= 2:
        first_day: date = rows[0]["sale_date"]  # type: ignore[assignment]
        xs = [
            (r["sale_date"] - first_day).days  # type: ignore[operator]
            for r in rows
        ]
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
        "revenue_std_dev": round(statistics.stdev(revenues), 4) if len(revenues) > 1 else 0.0,
        "total_units": sum(units_list),
        "avg_units_per_day": round(statistics.mean(units_list), 2),
        "peak_date": str(peak_row["sale_date"]),
        "peak_revenue": float(peak_row["revenue"]),
        "revenue_trend_per_day": round(slope, 4),
    }

    logger.info(
        "ETL job %s: model complete | rows=%d total_revenue=%.2f trend=%.4f",
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
    """Build a natural-language summary and persist it to MongoDB."""
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

    Designed to be called via FastAPI BackgroundTasks — creates its own DB
    session because the request session is closed before this runs.

    The optional `_session_factory` parameter is a testing seam: pass
    `TestingSession` in tests to avoid hitting the real Postgres instance.
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
        try:
            content = open(file_path, "rb").read()
            raw_rows = _stage_validate(content)
        except (ValueError, OSError) as exc:
            _set_status(db, job, "failed", {"stage": "validating", "detail": str(exc)})
            return
        _set_status(db, job, "cleaning")

        # ── Stage 2: Clean ───────────────────────────────────────────────────
        try:
            clean_rows = _stage_clean(raw_rows)
        except ValueError as exc:
            _set_status(db, job, "failed", {"stage": "cleaning", "detail": str(exc)})
            return
        _set_status(db, job, "storing")

        # ── Stage 3: Store ───────────────────────────────────────────────────
        try:
            _stage_store(clean_rows, job_uuid, db)
        except Exception as exc:
            logger.exception("ETL job %s: storage error", job_id)
            _set_status(db, job, "failed", {"stage": "storing", "detail": str(exc)})
            return
        _set_status(db, job, "modeling")

        # ── Stage 4: Model ───────────────────────────────────────────────────
        try:
            stats = _stage_model(clean_rows, job_uuid)
        except Exception as exc:
            logger.exception("ETL job %s: modeling error", job_id)
            _set_status(db, job, "failed", {"stage": "modeling", "detail": str(exc)})
            return
        _set_status(db, job, "recommending")

        # ── Stage 5: Recommend ───────────────────────────────────────────────
        try:
            await _stage_recommend(stats, job_uuid)
        except Exception as exc:
            # MongoDB unavailability is non-fatal: log and complete anyway.
            logger.warning(
                "ETL job %s: recommendation write failed (non-fatal): %s",
                job_id,
                exc,
            )
        _set_status(db, job, "done")

    except Exception as exc:
        # Catch-all: ensure the job never stays stuck in a transient state.
        logger.exception("ETL job %s: unexpected error", job_id)
        try:
            _set_status(
                db, job, "failed", {"stage": "unknown", "detail": str(exc)}
            )
        except Exception:
            pass
    finally:
        db.close()
