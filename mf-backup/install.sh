#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/mf-backup"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing mf-backup ==="

# --- Copy files ---
mkdir -p "$INSTALL_DIR/data"
cp "$SCRIPT_DIR/backup.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/restore.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/healthcheck.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/*.sh

# --- Create .env from example if not exists ---
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/.env"
  echo "Created $INSTALL_DIR/.env from example — review and adjust if needed."
else
  echo "$INSTALL_DIR/.env already exists, not overwriting."
fi

# --- Install cron job (daily at 03:00 UTC) ---
CRON_LINE="0 3 * * * $INSTALL_DIR/backup.sh >> /var/log/mf-backup.log 2>&1"
CRON_EXISTS=$(crontab -l 2>/dev/null | grep -F "$INSTALL_DIR/backup.sh" || true)
if [ -z "$CRON_EXISTS" ]; then
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
  echo "Cron job installed: daily backup at 03:00 UTC"
else
  echo "Cron job already exists, skipping."
fi

# --- Verify ---
echo ""
echo "Installed to: $INSTALL_DIR"
ls -la "$INSTALL_DIR"/*.sh "$INSTALL_DIR/.env"
echo ""
echo "Crontab:"
crontab -l | grep mf-backup
echo ""

# --- Run first backup now ---
echo "Running first backup..."
bash "$INSTALL_DIR/backup.sh"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Commands:"
echo "  sudo bash $INSTALL_DIR/backup.sh        # Manual backup"
echo "  sudo bash $INSTALL_DIR/restore.sh        # Restore latest"
echo "  sudo bash $INSTALL_DIR/restore.sh <TS>   # Restore specific timestamp"
echo "  sudo bash $INSTALL_DIR/healthcheck.sh    # Health check"
echo "  ls -lh $INSTALL_DIR/data/               # List backups"
