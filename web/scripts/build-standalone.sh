#!/usr/bin/env bash
#
# Build Next.js standalone + copy the 3 artefacts the standalone bundle
# doesn't include by default (env, public/, .next/static/). Output is a
# self-contained web/.next/standalone/ ready to rsync to prod.
#
# Usage (from inside web/):  npm run build:deploy
#
# See deploy/RUNBOOK.md § "Pre-build checklist (frontend)" for context.

set -euo pipefail

# ---- Sanity -----------------------------------------------------------------

if [[ ! -f package.json ]] || ! grep -q '"name": "franchise-web"' package.json; then
  echo "✗ Rode esse script de dentro de web/." >&2
  exit 1
fi

if [[ ! -f .env.production.local ]]; then
  echo "✗ .env.production.local não existe. Crie com os valores de prod antes do build." >&2
  exit 1
fi
echo "✓ .env.production.local OK"

# ---- Build ------------------------------------------------------------------

echo "→ Limpando .next/…"
rm -rf .next

echo "→ Rodando next build (NODE_OPTIONS='--max-old-space-size=2048')…"
NODE_OPTIONS='--max-old-space-size=2048' npm run build
echo "✓ Build OK"

# ---- Copy artefacts ---------------------------------------------------------

cp .env.production.local .next/standalone/.env
echo "✓ Copiado .env.production.local → .next/standalone/.env"

cp -r public .next/standalone/
echo "✓ Copiado public/ → .next/standalone/public/"

cp -r .next/static .next/standalone/.next/
echo "✓ Copiado .next/static/ → .next/standalone/.next/static/"

echo ""
echo "✓ Standalone pronto em web/.next/standalone/ — rsync conforme RUNBOOK."
