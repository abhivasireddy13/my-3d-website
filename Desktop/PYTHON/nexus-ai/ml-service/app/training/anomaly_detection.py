"""
Anomaly detection — Isolation Forest on (revenue, units) feature pairs.

Training pipeline:
  1. Query (revenue, units) rows from fact_sales (PostgreSQL).
  2. Train IsolationForest.
  3. Compute mean_anomaly_score = mean(score_samples(X_train)).
     Higher (less negative) → model considers training data more "normal".
  4. Log params, metrics, and the artifact to MLflow.
  5. Register to the MLflow model registry.
  6. Promote to "production" alias if new score > current production score.
"""

import logging
from typing import Callable

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.postgres import SessionLocal

logger = logging.getLogger(__name__)

MODEL_NAME = "nexus-anomaly-detection"
EXPERIMENT_NAME = "nexus-anomaly-detection"
MIN_ROWS = 2
CONTAMINATION = 0.05   # expected fraction of outliers in training data


# ─── Data helpers ─────────────────────────────────────────────────────────────

def fetch_training_data(
    session_factory: Callable[[], Session] | None = None,
) -> pd.DataFrame:
    """Return a DataFrame with columns [revenue, units] from fact_sales."""
    factory = session_factory or SessionLocal
    db = factory()
    try:
        result = db.execute(
            text("SELECT revenue, units FROM fact_sales ORDER BY date_key")
        )
        rows = result.fetchall()
    finally:
        db.close()

    if not rows:
        raise ValueError(
            "fact_sales is empty — upload and process at least one CSV first"
        )

    df = pd.DataFrame(rows, columns=["revenue", "units"]).astype(float)
    logger.info("Fetched %d rows from fact_sales for anomaly training", len(df))
    return df


# ─── MLflow helpers ───────────────────────────────────────────────────────────

def _get_production_score(client: mlflow.MlflowClient) -> float:
    """Return mean_anomaly_score of the current production model.

    Returns -infinity if no production model exists so the first
    trained model is always promoted.
    """
    try:
        prod = client.get_model_version_by_alias(MODEL_NAME, "production")
        metrics = client.get_run(prod.run_id).data.metrics
        return float(metrics.get("mean_anomaly_score", float("-inf")))
    except Exception:
        return float("-inf")


def _configure_mlflow() -> None:
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)


# ─── Public entry point ───────────────────────────────────────────────────────

def train_and_register(
    df: pd.DataFrame | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> dict:
    """Train, evaluate, log to MLflow, register, and conditionally promote.

    Args:
        df: DataFrame with [revenue, units] columns (optional).
            Queries fact_sales when None.
        session_factory: SQLAlchemy session factory (testing seam).

    Returns:
        dict with keys: run_id, version, mean_anomaly_score, anomaly_rate, promoted.
    """
    _configure_mlflow()

    if df is None:
        df = fetch_training_data(session_factory)

    feature_cols = ["revenue", "units"]
    X = df[feature_cols].values

    if len(X) < MIN_ROWS:
        raise ValueError(
            f"Need at least {MIN_ROWS} rows to train; got {len(X)}"
        )

    params = {
        "contamination": CONTAMINATION,
        "n_estimators": 100,
        "random_state": 42,
        "feature_cols": str(feature_cols),
        "n_training_samples": len(X),
    }

    with mlflow.start_run() as run:
        model = IsolationForest(
            contamination=CONTAMINATION,
            n_estimators=100,
            random_state=42,
        )
        model.fit(X)

        # mean of score_samples: higher (less negative) = data is more "normal".
        scores = model.score_samples(X)
        mean_score = float(np.mean(scores))

        labels = model.predict(X)   # -1 = anomaly, 1 = normal
        anomaly_rate = float(np.mean(labels == -1))

        mlflow.log_params(params)
        mlflow.log_metric("mean_anomaly_score", mean_score)
        mlflow.log_metric("anomaly_rate", anomaly_rate)
        mlflow.log_metric("n_training_samples", len(X))

        model_info = mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )
        new_version = model_info.registered_model_version
        run_id = run.info.run_id

    logger.info(
        "Anomaly training complete | run=%s version=%s "
        "mean_score=%.4f anomaly_rate=%.4f",
        run_id, new_version, mean_score, anomaly_rate,
    )

    # Promotion rule: promote if new model's score is higher than production's.
    client = mlflow.MlflowClient()
    prod_score = _get_production_score(client)

    if mean_score > prod_score:
        client.set_registered_model_alias(MODEL_NAME, "production", str(new_version))
        promoted = True
        logger.info(
            "Promoted %s v%s to production (score %.4f > prod %.4f)",
            MODEL_NAME, new_version, mean_score, prod_score,
        )
    else:
        promoted = False
        logger.info(
            "Not promoting v%s (score %.4f <= prod %.4f)",
            new_version, mean_score, prod_score,
        )

    return {
        "run_id": run_id,
        "version": str(new_version),
        "mean_anomaly_score": mean_score,
        "anomaly_rate": anomaly_rate,
        "promoted": promoted,
        "n_training_samples": len(X),
    }
