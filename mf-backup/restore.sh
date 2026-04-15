#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/.env"

BACKUP_DIR="${BACKUP_DIR:-/opt/mf-backup/data}"

# --- Find latest files or use argument ---
if [ "${1:-}" != "" ]; then
  # Restore specific timestamp: ./restore.sh 20260415_120000
  TS="$1"
  DUMP_FILE="${BACKUP_DIR}/mysql_${TS}.sql.gz"
  REDIS_FILE="${BACKUP_DIR}/redis_${TS}.rdb"
  UPLOADS_FILE="${BACKUP_DIR}/uploads_${TS}.tar.gz"
else
  DUMP_FILE=$(ls -t "$BACKUP_DIR"/mysql_*.sql.gz 2>/dev/null | head -1)
  REDIS_FILE=$(ls -t "$BACKUP_DIR"/redis_*.rdb 2>/dev/null | head -1)
  UPLOADS_FILE=$(ls -t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null | head -1)
fi

if [ -z "$DUMP_FILE" ] || [ ! -f "$DUMP_FILE" ]; then
  echo "ERROR: No MySQL dump found in $BACKUP_DIR"
  exit 1
fi

echo "[$(date)] Restoring from: $(basename "$DUMP_FILE")"
echo ""
read -p "This will OVERWRITE the current database. Continue? [y/N] " confirm
[ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || { echo "Aborted."; exit 0; }

# --- MySQL restore ---
echo "[$(date)] Restoring MySQL..."
gunzip -c "$DUMP_FILE" | docker exec -i "$MYSQL_CONTAINER" \
  mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"
echo "[$(date)] MySQL restored."

# --- Redis restore ---
if [ -n "$REDIS_FILE" ] && [ -f "$REDIS_FILE" ]; then
  echo "[$(date)] Restoring Redis..."
  docker cp "$REDIS_FILE" "${REDIS_CONTAINER}:/data/dump.rdb"
  docker restart "$REDIS_CONTAINER"
  echo "[$(date)] Redis restored and restarted."
else
  echo "[$(date)] No Redis snapshot found, skipping."
fi

# --- Uploads restore ---
UPLOADS_DST="${PROJECT_DIR:-/home/ubuntu/mercadofranquia-site}/api"
if [ -n "$UPLOADS_FILE" ] && [ -f "$UPLOADS_FILE" ]; then
  echo "[$(date)] Restoring uploads..."
  tar xzf "$UPLOADS_FILE" -C "$UPLOADS_DST"
  echo "[$(date)] Uploads restored to ${UPLOADS_DST}/uploads/"
else
  echo "[$(date)] No uploads archive found, skipping."
fi

echo "[$(date)] Restore complete."
