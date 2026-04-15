#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/.env"

EXIT_CODE=0

check() {
  local name="$1" status="$2"
  if [ "$status" = "OK" ]; then
    printf "  %-20s %s\n" "$name" "OK"
  else
    printf "  %-20s %s\n" "$name" "FAIL - $status"
    EXIT_CODE=1
  fi
}

echo "=== Mercado Franquia Health Check ==="
echo ""

# --- Docker containers ---
echo "Containers:"
for c in franchise_mysql franchise_redis franchise_api franchise_web; do
  status=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo "not found")
  if [ "$status" = "running" ]; then
    check "$c" "OK"
  else
    check "$c" "$status"
  fi
done
echo ""

# --- MySQL connectivity ---
echo "Services:"
mysql_ping=$(docker exec "$MYSQL_CONTAINER" mysqladmin ping -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --silent 2>/dev/null)
if echo "$mysql_ping" | grep -qi alive; then
  check "MySQL" "OK"
else
  check "MySQL" "unreachable"
fi

# --- MySQL row counts ---
FRANCHISE_COUNT=$(docker exec "$MYSQL_CONTAINER" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -sNe "SELECT COUNT(*) FROM Franchise" 2>/dev/null || echo "0")
printf "  %-20s %s\n" "Franchises" "${FRANCHISE_COUNT} rows"

# --- Redis connectivity ---
redis_ping=$(docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping 2>/dev/null || echo "")
if [ "$redis_ping" = "PONG" ]; then
  check "Redis" "OK"
else
  check "Redis" "unreachable"
fi

# --- API health ---
api_status=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:4000/statistics 2>/dev/null || echo "down")
if [ "$api_status" = "200" ]; then
  check "API (NestJS)" "OK"
else
  check "API (NestJS)" "HTTP $api_status"
fi

# --- Web health ---
web_status=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:3050/ 2>/dev/null || echo "down")
if [ "$web_status" = "200" ] || [ "$web_status" = "302" ]; then
  check "Web (Next.js)" "OK"
else
  check "Web (Next.js)" "HTTP $web_status"
fi

# --- Nginx ---
nginx_status=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
if [ "$nginx_status" = "active" ]; then
  check "Nginx" "OK"
else
  check "Nginx" "$nginx_status"
fi

# --- Disk usage ---
echo ""
echo "Disk:"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5 " used (" $4 " free)"}')
printf "  %-20s %s\n" "Root filesystem" "$DISK_USAGE"

# --- Last backup ---
BACKUP_DIR="${BACKUP_DIR:-/opt/mf-backup/data}"
LAST_BACKUP=$(ls -t "$BACKUP_DIR"/mysql_*.sql.gz 2>/dev/null | head -1)
if [ -n "$LAST_BACKUP" ]; then
  LAST_DATE=$(stat -c %y "$LAST_BACKUP" 2>/dev/null | cut -d. -f1 || stat -f %Sm "$LAST_BACKUP" 2>/dev/null)
  printf "  %-20s %s\n" "Last backup" "$LAST_DATE"
else
  printf "  %-20s %s\n" "Last backup" "NONE"
  EXIT_CODE=1
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo "All checks passed."
else
  echo "Some checks FAILED."
fi

exit $EXIT_CODE
