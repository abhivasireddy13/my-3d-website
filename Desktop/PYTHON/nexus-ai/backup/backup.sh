#!/usr/bin/env bash
# backup.sh — dump PostgreSQL and MongoDB to /backups with date-stamped filenames.
# Runs as a non-root user; the /backups directory is volume-mounted.

set -euo pipefail

STAMP="$(date -u '+%Y%m%d_%H%M%S')"
DEST="/backups/${STAMP}"
mkdir -p "${DEST}"

echo "[$(date -u +%FT%TZ)] Starting backup → ${DEST}"

# ── PostgreSQL ────────────────────────────────────────────────────────────────
PG_FILE="${DEST}/postgres_${POSTGRES_DB}.sql.gz"
echo "  pg_dump ${POSTGRES_DB} …"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT:-5432}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-privileges \
  | gzip > "${PG_FILE}"
echo "  Written: ${PG_FILE} ($(du -sh "${PG_FILE}" | cut -f1))"

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_DIR="${DEST}/mongo"
echo "  mongodump …"
mongodump \
    --host="${MONGO_HOST:-mongo}" \
    --port="${MONGO_PORT:-27017}" \
    --username="${MONGO_USER}" \
    --password="${MONGO_PASSWORD}" \
    --authenticationDatabase=admin \
    --out="${MONGO_DIR}" \
    --quiet
# Compress the dump directory into a single archive
tar -czf "${DEST}/mongo.tar.gz" -C "${DEST}" mongo
rm -rf "${MONGO_DIR}"
echo "  Written: ${DEST}/mongo.tar.gz ($(du -sh "${DEST}/mongo.tar.gz" | cut -f1))"

# ── Retention: remove backups older than RETENTION_DAYS ──────────────────────
RETENTION_DAYS="${RETENTION_DAYS:-7}"
echo "  Pruning backups older than ${RETENTION_DAYS} days …"
find /backups -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true

echo "[$(date -u +%FT%TZ)] Backup complete."
