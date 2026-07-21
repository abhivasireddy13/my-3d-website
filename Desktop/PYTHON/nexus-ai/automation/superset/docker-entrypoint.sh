#!/bin/bash
# Superset initialization and startup script.
# Runs every container start; idempotent — safe to re-run.
set -euo pipefail

PG_HOST="${POSTGRES_HOST:-postgres}"
PG_USER="${POSTGRES_USER:-nexus}"
PG_PASS="${POSTGRES_PASSWORD:-nexus}"

echo "==> [superset] Creating superset_meta database (if not exists)..."
PGPASSWORD="$PG_PASS" psql \
    -h "$PG_HOST" -U "$PG_USER" -d postgres \
    -c "CREATE DATABASE superset_meta;" 2>/dev/null \
  || echo "    superset_meta already exists — skipping."

echo "==> [superset] Running Alembic migrations (superset db upgrade)..."
superset db upgrade

echo "==> [superset] Creating admin user (idempotent)..."
superset fab create-admin \
    --username  "${SUPERSET_ADMIN_USERNAME:-admin}" \
    --firstname "Admin" \
    --lastname  "Admin" \
    --email     "${SUPERSET_ADMIN_EMAIL:-admin@nexus.ai}" \
    --password  "${SUPERSET_ADMIN_PASSWORD:-admin}" \
  2>/dev/null || echo "    Admin already exists — skipping."

echo "==> [superset] Initializing Superset roles and permissions..."
superset init

echo "==> [superset] Starting Gunicorn (background)..."
gunicorn \
    --bind "0.0.0.0:8088" \
    --workers 4 \
    --timeout 180 \
    --keep-alive 5 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    "superset.app:create_app()" &
GUNICORN_PID=$!

echo "==> [superset] Waiting for Superset to accept requests..."
TRIES=0
until curl -sf "http://localhost:8088/health" > /dev/null 2>&1; do
    TRIES=$((TRIES + 1))
    if [ $TRIES -gt 60 ]; then
        echo "ERROR: Superset did not start within 120 s. Aborting."
        kill $GUNICORN_PID 2>/dev/null
        exit 1
    fi
    sleep 2
done
echo "==> [superset] Superset is up."

echo "==> [superset] Running dashboard setup (idempotent)..."
python /app/pythonpath/setup_dashboards.py \
  || echo "    Dashboard setup returned non-zero (non-fatal — dashboards may need re-import)."

echo "==> [superset] Ready. Forwarding to Gunicorn PID $GUNICORN_PID."
wait $GUNICORN_PID
