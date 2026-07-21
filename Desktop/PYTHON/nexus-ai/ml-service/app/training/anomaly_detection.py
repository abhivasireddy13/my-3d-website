"""
Train an Isolation Forest anomaly detector on numeric sales features.
Run manually or via the n8n ML-trigger workflow once enough data exists.
"""
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

def train(df: pd.DataFrame, feature_cols: list[str], out_path: str = "model_anomaly.joblib"):
    model = IsolationForest(contamination=0.03, random_state=42)
    model.fit(df[feature_cols])
    joblib.dump(model, out_path)
    return out_path

if __name__ == "__main__":
    # Replace with a real query against PostgreSQL fact_sales in production
    demo = pd.DataFrame({"revenue": [100, 120, 98, 400, 110], "units": [10, 12, 9, 5, 11]})
    train(demo, ["revenue", "units"])
    print("trained demo anomaly model")
