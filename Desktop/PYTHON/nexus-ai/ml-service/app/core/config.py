from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+psycopg://nexus:nexus@postgres:5432/nexus"
    )
    # SQLite-backed MLflow tracking — no extra service required.
    # The DB file lives inside the volume-mounted /app dir so it persists.
    MLFLOW_TRACKING_URI: str = "sqlite:////app/mlflow.db"
    MLFLOW_ARTIFACT_ROOT: str = "/app/mlruns"

    class Config:
        env_file = ".env"


settings = Settings()
