from fastapi import FastAPI
from pydantic import BaseModel
import joblib, os

app = FastAPI(title="NEXUS AI - ML Service", version="0.1.0")

class ForecastRequest(BaseModel):
    recent_values: list[float]

class AnomalyRequest(BaseModel):
    revenue: float
    units: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict/sales-forecast")
def predict_forecast(req: ForecastRequest):
    path = "model_forecast.joblib"
    if not os.path.exists(path):
        return {"error": "model not trained yet - run app/training/sales_forecast.py"}
    model = joblib.load(path)
    lags = req.recent_values[-3:]
    pred = model.predict([lags])[0]
    return {"forecast": float(pred)}

@app.post("/predict/anomaly")
def predict_anomaly(req: AnomalyRequest):
    path = "model_anomaly.joblib"
    if not os.path.exists(path):
        return {"error": "model not trained yet - run app/training/anomaly_detection.py"}
    model = joblib.load(path)
    score = model.predict([[req.revenue, req.units]])[0]  # -1 = anomaly, 1 = normal
    return {"is_anomaly": bool(score == -1)}
