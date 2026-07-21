"""
AI Recommendation Service.

Evaluates ML predictions against business-rule thresholds and, when a
threshold is breached, calls Claude to generate 2–4 concrete actionable
recommendations.  Every call is fully audited: the exact prompt, the
model version, the trigger reason, and the LLM output are all stored in
fact_recommendations so the business can replay or challenge any advice.

Threshold rules (configurable via constants):
  • is_anomaly=True → "anomaly_detected"
  • forecast value < (1 − FORECAST_DECLINE_THRESHOLD) × prior_avg → "forecast_decline"

Failure modes:
  1. ANTHROPIC_API_KEY not set → skip LLM, use rule-based fallback
  2. LLM raises an error after MAX_RETRIES → use rule-based fallback
  3. LLM returns malformed JSON → extract actions heuristically, still store

All three modes persist a FactRecommendation row with the appropriate status.
"""
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.postgres import SessionLocal
from app.models.fact_predictions import FactPrediction
from app.models.fact_recommendations import FactRecommendation
from app.models.upload_job import UploadJob

logger = logging.getLogger(__name__)

# ─── Tunable constants ────────────────────────────────────────────────────────
CLAUDE_MODEL            = "claude-sonnet-4-6"
MAX_RETRIES             = 3
RETRY_DELAYS            = (1, 2, 4)          # seconds between attempts
FORECAST_DECLINE_THRESHOLD = 0.10            # 10% decline triggers a recommendation
MAX_ACTIONS             = 4
MIN_ACTIONS             = 2


# ─── Anthropic client (lazy, so key can be injected in tests) ────────────────

def _get_client() -> anthropic.Anthropic:
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ─── Threshold evaluation ─────────────────────────────────────────────────────

def _check_thresholds(prediction: FactPrediction, db: Session) -> tuple[bool, dict]:
    """
    Return (triggered, context_dict).

    triggered=True means at least one business rule was breached and a
    recommendation should be generated.
    """
    context: dict = {
        "model_name": prediction.model_name,
        "model_version": prediction.model_version or "unknown",
        "prediction_value": float(prediction.prediction_value or 0),
        "is_anomaly": prediction.is_anomaly,
        "triggered_by": None,
        "metric_delta": None,
        "prior_avg": None,
    }

    # Rule 1 — anomaly flag
    if prediction.is_anomaly is True:
        context["triggered_by"] = "anomaly_detected"
        return True, context

    # Rule 2 — significant forecast decline vs. prior period
    if "forecast" in (prediction.model_name or "").lower():
        prior_avg = (
            db.query(func.avg(FactPrediction.prediction_value))
            .filter(
                FactPrediction.model_name == prediction.model_name,
                FactPrediction.prediction_id != prediction.prediction_id,
                FactPrediction.is_anomaly.is_(None),   # only forecast rows
                FactPrediction.created_at < prediction.created_at,
            )
            .scalar()
        )
        if prior_avg and float(prior_avg) > 0:
            delta = (float(prediction.prediction_value or 0) - float(prior_avg)) / float(prior_avg)
            context["metric_delta"] = round(delta, 4)
            context["prior_avg"] = float(prior_avg)
            if delta < -FORECAST_DECLINE_THRESHOLD:
                context["triggered_by"] = "forecast_decline"
                return True, context

    return False, context


# ─── Prompt builder ───────────────────────────────────────────────────────────

def _build_prompt(context: dict) -> str:
    trigger_desc = {
        "anomaly_detected": "an anomaly was detected in the sales data",
        "forecast_decline": (
            f"the sales forecast declined by "
            f"{abs(context['metric_delta'] or 0) * 100:.1f}% "
            f"vs the prior-period average"
        ),
    }.get(context["triggered_by"] or "", "a threshold was breached")

    prior_line = ""
    if context.get("prior_avg") is not None:
        prior_line = f"- Prior-period average: {context['prior_avg']:.2f}\n"

    delta_line = ""
    if context.get("metric_delta") is not None:
        pct = context["metric_delta"] * 100
        delta_line = f"- Change vs prior: {pct:+.1f}%\n"

    return f"""You are a senior business intelligence analyst reviewing automated pipeline results.

## Alert context
- Trigger: {trigger_desc}
- Model: {context['model_name']} (version {context['model_version']})
- Current value: {context['prediction_value']:.4f}
{prior_line}{delta_line}- Anomaly flag: {context['is_anomaly']}

## Task
Provide {MIN_ACTIONS}–{MAX_ACTIONS} concrete, actionable business recommendations
to address this alert. Each recommendation should be specific, measurable, and
executable by a business or data team.

Return ONLY a valid JSON array of strings — no markdown, no explanations, just
the array. Example:
["Investigate stock levels in affected region", "Schedule emergency pricing review"]
"""


# ─── JSON extraction (robust against noisy LLM output) ───────────────────────

def _extract_actions(raw: str) -> list[str]:
    """Parse a JSON array from LLM output; fall back to line-splitting."""
    try:
        result = json.loads(raw.strip())
        if isinstance(result, list) and result:
            return [str(s).strip() for s in result[:MAX_ACTIONS]]
    except json.JSONDecodeError:
        pass

    # Find first [...] block in the text
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list) and result:
                return [str(s).strip() for s in result[:MAX_ACTIONS]]
        except json.JSONDecodeError:
            pass

    # Last resort: treat non-empty lines as individual actions
    lines = [
        ln.strip().strip('"').strip("'").strip("-").strip()
        for ln in raw.splitlines()
        if ln.strip() and not ln.strip().startswith(("[", "]"))
    ]
    return [l for l in lines if l][:MAX_ACTIONS] or [
        "Review the flagged metric with the analytics team",
        "Re-run the ETL pipeline to validate data quality",
    ]


# ─── Rule-based fallback ──────────────────────────────────────────────────────

def _fallback_actions(context: dict) -> list[str]:
    if context.get("triggered_by") == "anomaly_detected":
        return [
            f"Investigate the anomaly flagged by {context['model_name']}",
            "Check source data for ingestion errors or schema drift",
            "Alert the data engineering team for manual review",
            "Consider retraining the anomaly detection model with recent data",
        ]
    if context.get("triggered_by") == "forecast_decline":
        pct = abs(context.get("metric_delta") or 0) * 100
        return [
            f"Review root causes of the {pct:.1f}% forecast decline",
            "Assess inventory and supply chain impacts",
            "Schedule a sales leadership briefing on the forecast shortfall",
            "Evaluate whether promotional activity can offset the decline",
        ]
    return [
        "Review the flagged prediction with the analytics team",
        "Validate source data quality before taking action",
    ]


# ─── LLM call with retry ─────────────────────────────────────────────────────

def _call_claude(prompt: str) -> tuple[list[str], str]:
    """
    Call Claude with retry + exponential back-off.
    Returns (actions, model_id_used).
    Raises the last exception if all retries are exhausted.
    """
    client = _get_client()
    last_exc: Exception = RuntimeError("No attempts made")

    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            logger.debug("Claude attempt %d/%d", attempt, MAX_RETRIES)
            msg = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text
            actions = _extract_actions(raw)
            logger.info("Claude returned %d actions on attempt %d", len(actions), attempt)
            return actions, msg.model
        except anthropic.RateLimitError as exc:
            logger.warning("Claude rate limit (attempt %d): %s", attempt, exc)
            last_exc = exc
        except anthropic.APIStatusError as exc:
            logger.warning("Claude API error (attempt %d): %s %s", attempt, exc.status_code, exc.message)
            last_exc = exc
        except Exception as exc:
            logger.warning("Claude unexpected error (attempt %d): %s", attempt, exc)
            last_exc = exc

        if attempt < MAX_RETRIES:
            time.sleep(delay)

    raise last_exc


# ─── Main public function ─────────────────────────────────────────────────────

def evaluate_prediction(
    prediction: FactPrediction,
    db: Session,
) -> Optional[FactRecommendation]:
    """
    Evaluate a prediction against business-rule thresholds.
    If a threshold is breached, call Claude for recommendations and persist
    the result.  Returns the FactRecommendation row, or None if no threshold
    was triggered.

    Idempotent: if a recommendation already exists for this prediction_id,
    the existing row is returned without re-calling Claude.
    """
    # Idempotency check
    existing = (
        db.query(FactRecommendation)
        .filter(FactRecommendation.prediction_id == prediction.prediction_id)
        .first()
    )
    if existing:
        logger.debug("Recommendation already exists for prediction %s", prediction.prediction_id)
        return existing

    triggered, context = _check_thresholds(prediction, db)
    if not triggered:
        logger.debug(
            "No threshold breached for prediction %s (%s)",
            prediction.prediction_id, prediction.model_name,
        )
        return None

    prompt = _build_prompt(context)
    actions: list[str] = []
    model_used: Optional[str] = None
    status = "generated"
    confidence_score = 1.0
    error_message: Optional[str] = None

    if not settings.ANTHROPIC_API_KEY:
        logger.warning(
            "ANTHROPIC_API_KEY not set — using rule-based fallback for prediction %s",
            prediction.prediction_id,
        )
        actions = _fallback_actions(context)
        status = "fallback"
        confidence_score = 0.5
    else:
        try:
            actions, model_used = _call_claude(prompt)
        except Exception as exc:
            logger.error(
                "Claude failed for prediction %s after %d retries: %s",
                prediction.prediction_id, MAX_RETRIES, exc,
            )
            actions = _fallback_actions(context)
            model_used = None
            status = "fallback"
            confidence_score = 0.5
            error_message = str(exc)[:500]

    rec = FactRecommendation(
        prediction_id=prediction.prediction_id,
        upload_job_id=prediction.upload_job_id,
        actions=actions,
        model_used=model_used or (CLAUDE_MODEL if settings.ANTHROPIC_API_KEY else "rule-based"),
        prompt_used=prompt,
        triggered_by=context.get("triggered_by"),
        metric_name=prediction.model_name,
        metric_value=prediction.prediction_value,
        metric_delta=context.get("metric_delta"),
        confidence_score=confidence_score,
        status=status,
        error_message=error_message,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    logger.info(
        "Recommendation stored for prediction %s (status=%s, actions=%d)",
        prediction.prediction_id, status, len(actions),
    )
    return rec


# ─── Job-level batch function (called from background task) ──────────────────

def generate_recommendations_for_job(
    job_id: str,
    session_factory=None,
) -> None:
    """
    Evaluate all predictions linked to job_id, generate recommendations
    for any that breach thresholds, then transition the job to status='done'.

    Designed to run as a Starlette BackgroundTask (sync → executed in
    thread pool so it doesn't block the event loop).
    """
    if session_factory is None:
        session_factory = SessionLocal

    job_uuid = uuid.UUID(job_id)
    db: Session = session_factory()
    try:
        predictions = (
            db.query(FactPrediction)
            .filter(FactPrediction.upload_job_id == job_uuid)
            .all()
        )
        logger.info(
            "[recommendations] Evaluating %d predictions for job %s",
            len(predictions), job_id,
        )

        for pred in predictions:
            try:
                evaluate_prediction(pred, db)
            except Exception as exc:
                logger.error(
                    "[recommendations] Failed for prediction %s: %s",
                    pred.prediction_id, exc,
                )

        # Transition job to done
        job = db.query(UploadJob).filter(UploadJob.id == job_uuid).first()
        if job and job.status == "recommending":
            job.status = "done"
            db.commit()
            logger.info("[recommendations] Job %s transitioned to 'done'", job_id)

    except Exception as exc:
        logger.error("[recommendations] Batch failed for job %s: %s", job_id, exc)
    finally:
        db.close()
