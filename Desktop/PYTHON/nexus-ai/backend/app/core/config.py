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

    class Config:
        env_file = ".env"

settings = Settings()
