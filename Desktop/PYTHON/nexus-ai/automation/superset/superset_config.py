"""
Superset configuration for NEXUS AI.

Mounted into the Superset container at /app/pythonpath/superset_config.py
so Superset auto-discovers it via SUPERSET_CONFIG_PATH or by import.
"""
import os

# ─── Core security ────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv(
    "SUPERSET_SECRET_KEY",
    "nexus_superset_secret_CHANGE_ME_in_production_32chars",
)

# ─── Metadata database (Superset's own state) ─────────────────────────────────
_pg_user = os.getenv("POSTGRES_USER", "nexus")
_pg_pass = os.getenv("POSTGRES_PASSWORD", "nexus")
_pg_host = os.getenv("POSTGRES_HOST", "postgres")

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{_pg_user}:{_pg_pass}@{_pg_host}:5432/superset_meta"
)

# ─── Embedded dashboards ──────────────────────────────────────────────────────
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ALERT_REPORTS": False,   # keeps startup clean without Celery
}

# ─── CORS — allow iframe embedding from the frontend ─────────────────────────
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": {"/*": {"origins": ["*"]}},
}

# ─── Session / security ───────────────────────────────────────────────────────
# Disable CSRF so n8n / backend can call Superset APIs without a browser session
WTF_CSRF_ENABLED = False
WTF_CSRF_EXEMPT_LIST = []

# Disable Flask-Talisman so dashboards can be embedded in iframes
TALISMAN_ENABLED = False
TALISMAN_CONFIG = {}

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False    # dev only — set True behind TLS in production
SESSION_COOKIE_HTTPONLY = True

# Allow iframe embedding (X-Frame-Options)
HTTP_HEADERS = {}  # empty → no X-Frame-Options header

# ─── Cache (use Redis when available, in-memory fallback) ────────────────────
_redis_host = os.getenv("REDIS_HOST", "redis")
_redis_port = int(os.getenv("REDIS_PORT", 6379))

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": _redis_host,
    "CACHE_REDIS_PORT": _redis_port,
    "CACHE_REDIS_DB": 2,   # DB 0 = app, DB 1 = ml-service, DB 2 = superset
}

# ─── Row limits ───────────────────────────────────────────────────────────────
ROW_LIMIT = 50_000
VIZ_ROW_LIMIT = 10_000
SQL_MAX_ROW = 100_000

# ─── Misc ─────────────────────────────────────────────────────────────────────
ENABLE_PROXY_FIX = True   # trust X-Forwarded-* headers when behind reverse proxy
PUBLIC_ROLE_LIKE = "Gamma" # default public role maps to Gamma (limited access)
