"""
Baseline sales forecasting model: gradient boosting on lag features.
Swap for Prophet/statsmodels if you want a time-series-native approach.
"""
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
import joblib

def make_lag_features(series: pd.Series, lags: int = 3) -> pd.DataFrame:
    df = pd.DataFrame({"y": series})
    for lag in range(1, lags + 1):
        df[f"lag_{lag}"] = series.shift(lag)
    return df.dropna()

def train(series: pd.Series, out_path: str = "model_forecast.joblib"):
    df = make_lag_features(series)
    X, y = df.drop(columns="y"), df["y"]
    model = GradientBoostingRegressor(random_state=42)
    model.fit(X, y)
    joblib.dump(model, out_path)
    return out_path

if __name__ == "__main__":
    demo = pd.Series([100, 110, 105, 130, 125, 140, 138, 150])
    train(demo)
    print("trained demo forecast model")
