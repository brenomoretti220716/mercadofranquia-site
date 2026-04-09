#!/usr/bin/env bash
set -euo pipefail

# Importa MYSQL_DUMP_FILE no banco apenas se a tabela de checagem estiver vazia.
# Uso: compose monta o dump em /dump.sql (somente leitura).

SKIP="${SKIP_MYSQL_IMPORT:-0}"
if [ "$SKIP" = "1" ] || [ "$SKIP" = "true" ] || [ "$SKIP" = "yes" ]; then
  echo "[mysql-import] SKIP_MYSQL_IMPORT set — pulando importacao."
  exit 0
fi

DUMP="${MYSQL_DUMP_FILE:-/dump.sql}"
if [ ! -f "$DUMP" ] || [ ! -s "$DUMP" ]; then
  echo "[mysql-import] Arquivo de dump ausente ou vazio ($DUMP) — pulando importacao."
  exit 0
fi

HOST="${MYSQL_HOST:-mysql}"
USER="${MYSQL_USER:-franchise_user}"
PASS="${MYSQL_PASSWORD:-franchise_password}"
DB="${MYSQL_DATABASE:-franchise_db}"
TABLE="${MYSQL_SEED_CHECK_TABLE:-User}"

export MYSQL_PWD="$PASS"
trap 'unset MYSQL_PWD' EXIT

COUNT="$(mysql -h"$HOST" -u"$USER" -N -e "SELECT COUNT(*) FROM \`${DB}\`.\`${TABLE}\`" 2>/dev/null || true)"
if [ -z "${COUNT}" ] || ! [[ "${COUNT}" =~ ^[0-9]+$ ]]; then
  echo "[mysql-import] Nao foi possivel consultar a tabela \`${TABLE}\` (schema aplicado?)."
  exit 1
fi

if [ "${COUNT}" -gt 0 ]; then
  echo "[mysql-import] Banco ja possui dados em \`${TABLE}\` (${COUNT} linhas) — importacao ignorada."
  exit 0
fi

echo "[mysql-import] Importando ${DUMP} em ${DB} ..."
mysql -h"$HOST" -u"$USER" "$DB" <"$DUMP"
echo "[mysql-import] Importacao concluida."
