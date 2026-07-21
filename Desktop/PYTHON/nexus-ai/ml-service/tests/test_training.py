"""
Tests for the ML training pipelines.

Both sales_forecast.train_and_register and anomaly_detection.train_and_register
are exercised using an in-memory SQLite fact_sales table so no live Postgres or
MLflow server is needed.
"""
import pytest
import pandas as pd

from app.training import sales_forecast, anomaly_detection


# ─── Sales forecast ───────────────────────────────────────────────────────────

class TestSalesForecastTraining:
    def test_train_returns_expected_keys(self, db_with_sales):
        result = sales_forecast.train_and_register(session_factory=db_with_sales)
        assert set(result.keys()) >= {
            "run_id", "version", "mae", "promoted", "lags_used", "n_training_samples"
        }

    def test_train_promotes_first_model(self, db_with_sales):
        result = sales_forecast.train_and_register(session_factory=db_with_sales)
        assert result["promoted"] is True

    def test_mae_is_non_negative(self, db_with_sales):
        result = sales_forecast.train_and_register(session_factory=db_with_sales)
        assert result["mae"] >= 0.0

    def test_second_run_may_not_promote(self, db_with_sales):
        """Second training on same data may or may not promote — just check it runs."""
        sales_forecast.train_and_register(session_factory=db_with_sales)
        result2 = sales_forecast.train_and_register(session_factory=db_with_sales)
        assert isinstance(result2["promoted"], bool)

    def test_lags_adapted_for_small_dataset(self):
        """With 3 data points, lags must be at most 2 (n_rows - 1)."""
        tiny = pd.Series([100.0, 200.0, 150.0])
        result = sales_forecast.train_and_register(series=tiny)
        assert result["lags_used"] <= 2

    def test_too_few_rows_raises(self):
        two_rows = pd.Series([100.0, 200.0])
        with pytest.raises(ValueError, match="at least"):
            sales_forecast.train_and_register(series=two_rows)

    def test_empty_fact_sales_raises(self, sqlite_session_factory):
        """An empty fact_sales table raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            sales_forecast.train_and_register(session_factory=sqlite_session_factory)

    def test_fetch_training_data_returns_series(self, db_with_sales):
        series = sales_forecast.fetch_training_data(session_factory=db_with_sales)
        assert len(series) > 0
        assert series.dtype.kind == "f"  # float


# ─── Anomaly detection ────────────────────────────────────────────────────────

class TestAnomalyDetectionTraining:
    def test_train_returns_expected_keys(self, db_with_sales):
        result = anomaly_detection.train_and_register(session_factory=db_with_sales)
        assert set(result.keys()) >= {
            "run_id", "version", "mean_anomaly_score",
            "anomaly_rate", "promoted", "n_training_samples",
        }

    def test_train_promotes_first_model(self, db_with_sales):
        result = anomaly_detection.train_and_register(session_factory=db_with_sales)
        assert result["promoted"] is True

    def test_anomaly_rate_between_0_and_1(self, db_with_sales):
        result = anomaly_detection.train_and_register(session_factory=db_with_sales)
        assert 0.0 <= result["anomaly_rate"] <= 1.0

    def test_mean_score_is_negative(self, db_with_sales):
        """IsolationForest score_samples returns negative values."""
        result = anomaly_detection.train_and_register(session_factory=db_with_sales)
        assert result["mean_anomaly_score"] < 0.0

    def test_second_run_may_not_promote(self, db_with_sales):
        anomaly_detection.train_and_register(session_factory=db_with_sales)
        result2 = anomaly_detection.train_and_register(session_factory=db_with_sales)
        assert isinstance(result2["promoted"], bool)

    def test_passes_dataframe_directly(self):
        import pandas as pd
        df = pd.DataFrame({"revenue": [1000.0, 2000.0, 3000.0],
                           "units": [10, 20, 30]})
        result = anomaly_detection.train_and_register(df=df)
        assert result["n_training_samples"] == 3

    def test_empty_fact_sales_raises(self, sqlite_session_factory):
        with pytest.raises(ValueError, match="empty"):
            anomaly_detection.train_and_register(session_factory=sqlite_session_factory)

    def test_fetch_training_data_returns_dataframe(self, db_with_sales):
        df = anomaly_detection.fetch_training_data(session_factory=db_with_sales)
        assert list(df.columns) == ["revenue", "units"]
        assert len(df) > 0
