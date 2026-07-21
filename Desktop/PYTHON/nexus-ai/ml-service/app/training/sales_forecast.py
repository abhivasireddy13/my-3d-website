"""
Sales forecasting — gradient boosting on lag features.

Training pipeline:
  1. Query revenue time-series from fact_sales (PostgreSQL).
  2. Build lag features adaptively (lags = min(3, n_rows - 1)).
  3. Train GradientBoostingRegressor, evaluate MAE on held-out tail.
  4. Log params, metrics, and the model artifact to MLflow.
  5. Register to the MLflow model registry.
  6. Promote to "production" alias if new MAE < current production MAE.
"""

import logging
from typing import Callable

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.postgres import SessionLocal

logger = logging.getLogger(__name__)

MODEL_NAME = "nexus-sales-forecast"
EXPERIMENT_NAME = "nexus-sales-forecast"
MIN_ROWS = 3        # need at least this many rows to produce any lag feature
LAG_COUNT = 3       # default lags; reduced automatically on small datasets


# ─── Data helpers ─────────────────────────────────────────────────────────────

def fetch_training_data(
    session_factory: Callable[[], Session] | None = None,
) -> pd.Series:
    """Return daily revenue as a pandas Series ordered by date_key.

    Queries fact_sales grouped by date_key. Raises ValueError if the
    table is empty (no CSVs have been uploaded and processed yet).
    """
    factory = session_factory or SessionLocal
    db = factory()
    try:
        result = db.execute(
            text(
                "SELECT date_key, SUM(revenue) AS revenue "
                "FROM fact_sales "
                "GROUP BY date_key "
                "ORDER BY date_key"
            )
        )
        rows = result.fetchall()
    finally:
        db.close()

    if not rows:
        raise ValueError(
            "fact_sales is empty — upload and process at least one CSV first"
        )

    df = pd.DataFrame(rows, columns=["date_key", "revenue"])
    logger.info("Fetched %d aggregated date rows from fact_sales", len(df))
    return df["revenue"].astype(float).reset_index(drop=True)


def make_lag_features(series: pd.Series, lags: int) -> pd.DataFrame:
    """Build a supervised DataFrame from a revenue time-series."""
    df = pd.DataFrame({"y": series})
    for lag in range(1, lags + 1):
        df[f"lag_{lag}"] = series.shift(lag)
    return df.dropna().reset_index(drop=True)


# ─── MLflow helpers ───────────────────────────────────────────────────────────

def _get_production_mae(client: mlflow.MlflowClient) -> float:
    """Return the MAE of the current production-aliased model version.

    Returns infinity if no production model exists so any first training
    run is automatically promoted.
    """
    try:
        prod = client.get_model_version_by_alias(MODEL_NAME, "production")
        metrics = client.get_run(prod.run_id).data.metrics
        return float(metrics.get("mae", float("inf")))
    except Exception:
        return float("inf")


def _configure_mlflow() -> None:
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)


# ─── Public entry point ───────────────────────────────────────────────────────

def train_and_register(
    series: pd.Series | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> dict:
    """Train, evaluate, log to MLflow, register, and conditionally promote.

    Args:
        series: Revenue time-series (optional). Queries fact_sales when None.
        session_factory: SQLAlchemy session factory (testing seam).

    Returns:
        dict with keys: run_id, version, mae, promoted.
    """
    _configure_mlflow()

    if series is None:
        series = fetch_training_data(session_factory)

    n_rows = len(series)
    if n_rows < MIN_ROWS:
        raise ValueError(
            f"Need at least {MIN_ROWS} data rows to train; got {n_rows}"
        )

    # Ensure lag count leaves at least 2 rows after building lag features.
    # n_rows - lags ≥ 2  →  lags ≤ n_rows - 2; also always ≥ 1.
    lags = min(LAG_COUNT, max(1, n_rows - 2))
    df = make_lag_features(series, lags)

    if len(df) < 2:
        raise ValueError(
            f"Not enough samples after lag feature creation: "
            f"{len(df)} rows with lag={lags}"
        )

    # 80 / 20 train-test split (minimum 1 test row).
    split = max(1, int(len(df) * 0.8))
    X_train, X_test = df.drop(columns="y").iloc[:split], df.drop(columns="y").iloc[split:]
    y_train, y_test = df["y"].iloc[:split], df["y"].iloc[split:]

    params = {
        "n_estimators": 100,
        "max_depth": 3,
        "learning_rate": 0.1,
        "lags": lags,
        "random_state": 42,
    }

    with mlflow.start_run() as run:
        model = GradientBoostingRegressor(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            random_state=params["random_state"],
        )
        model.fit(X_train, y_train)

        # Evaluate — fall back to train-set MAE when test set is too small.
        eval_X = X_test if len(X_test) > 0 else X_train
        eval_y = y_test if len(y_test) > 0 else y_train
        preds = model.predict(eval_X)
        mae = float(np.mean(np.abs(preds - eval_y.values)))

        mlflow.log_params(params)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("n_training_samples", len(X_train))
        mlflow.log_metric("n_eval_samples", len(eval_X))

        model_info = mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )
        new_version = model_info.registered_model_version
        run_id = run.info.run_id

    logger.info(
        "Training complete | run=%s version=%s mae=%.4f",
        run_id, new_version, mae,
    )

    # Promotion rule: promote only if new MAE beats the production model.
    client = mlflow.MlflowClient()
    prod_mae = _get_production_mae(client)

    if mae < prod_mae:
        client.set_registered_model_alias(MODEL_NAME, "production", str(new_version))
        promoted = True
        logger.info(
            "Promoted %s v%s to production (MAE %.4f < prod MAE %.4f)",
            MODEL_NAME, new_version, mae, prod_mae,
        )
    else:
        promoted = False
        logger.info(
            "Not promoting v%s (MAE %.4f >= prod MAE %.4f)",
            new_version, mae, prod_mae,
        )

    return {
        "run_id": run_id,
        "version": str(new_version),
        "mae": mae,
        "promoted": promoted,
        "lags_used": lags,
        "n_training_samples": len(X_train),
    }
