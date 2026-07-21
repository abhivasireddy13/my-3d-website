#!/usr/bin/env bash
# entrypoint.sh — install the cron schedule and keep the container alive.
set -euo pipefail

SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"

echo "[entrypoint] Installing cron schedule: ${SCHEDULE}"

# Write the crontab for the current (non-root) user
echo "${SCHEDULE} /backup.sh >> /proc/1/fd/1 2>&1" | crontab -

echo "[entrypoint] Running initial backup on startup …"
/backup.sh || echo "[entrypoint] Initial backup failed (non-fatal)"

echo "[entrypoint] Starting crond …"
exec crond -f -d 8
