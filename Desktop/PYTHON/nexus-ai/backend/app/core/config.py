from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://nexus:nexus@localhost:5432/nexus"
    MONGO_URL: str = "mongodb://localhost:27017"
    REDIS_URL: str = "redis://localhost:6379/0"
    N8N_URL: str = "http://localhost:5678"
    N8N_WEBHOOK_SECRET: str = "change_me_shared_secret"
    STORAGE_DIR: str = "/storage"
    JWT_SECRET: str = "dev_secret_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # SMTP — leave SMTP_USER empty to disable email notifications
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = ""  # recipient; defaults to SMTP_USER when empty
    # Anthropic — AI recommendations
    ANTHROPIC_API_KEY: str = ""
    # Superset — analytics / BI
    SUPERSET_URL: str = "http://localhost:8088"
    SUPERSET_ADMIN_USERNAME: str = "admin"
    SUPERSET_ADMIN_PASSWORD: str = "admin"
    # Pre-assigned dashboard UUIDs — must match automation/superset/setup_dashboards.py
    SUPERSET_DASH_EXEC_UUID: str    = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    SUPERSET_DASH_SALES_UUID: str   = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    SUPERSET_DASH_ANOMALY_UUID: str = "c3d4e5f6-a7b8-9012-cdef-123456789012"

    class Config:
        env_file = ".env"

settings = Settings()
