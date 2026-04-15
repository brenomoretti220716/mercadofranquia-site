#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/.env"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/opt/mf-backup/data}"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-7}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# --- MySQL dump ---
DUMP_FILE="${BACKUP_DIR}/mysql_${TIMESTAMP}.sql.gz"
docker exec "$MYSQL_CONTAINER" \
  mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
  --single-transaction --quick --routines --triggers --no-tablespaces \
  "$MYSQL_DATABASE" | gzip > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "[$(date)] MySQL dump: $DUMP_FILE ($DUMP_SIZE)"

# --- Redis snapshot ---
REDIS_FILE="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" --no-auth-warning BGSAVE > /dev/null 2>&1
sleep 2
docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "$REDIS_FILE" 2>/dev/null && \
  echo "[$(date)] Redis snapshot: $REDIS_FILE" || \
  echo "[$(date)] Redis snapshot skipped (no dump.rdb)"

# --- Uploads directory ---
UPLOADS_SRC="${PROJECT_DIR:-/home/ubuntu/mercadofranquia-site}/api/uploads"
if [ -d "$UPLOADS_SRC" ] && [ "$(ls -A "$UPLOADS_SRC" 2>/dev/null)" ]; then
  UPLOADS_FILE="${BACKUP_DIR}/uploads_${TIMESTAMP}.tar.gz"
  tar czf "$UPLOADS_FILE" -C "$(dirname "$UPLOADS_SRC")" uploads
  UPLOADS_SIZE=$(du -h "$UPLOADS_FILE" | cut -f1)
  echo "[$(date)] Uploads archive: $UPLOADS_FILE ($UPLOADS_SIZE)"
else
  echo "[$(date)] Uploads directory empty or missing, skipped"
fi

# --- Cleanup old backups ---
find "$BACKUP_DIR" -type f -mtime +"$RETAIN_DAYS" -delete 2>/dev/null
REMAINING=$(ls -1 "$BACKUP_DIR" | wc -l)
echo "[$(date)] Cleanup done. $REMAINING files retained (keep ${RETAIN_DAYS}d)."

echo "[$(date)] Backup complete."
