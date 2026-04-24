# Deploy runbook — mercadofranquia

Production: EC2 `ubuntu@18.230.68.207` behind nginx, public at `https://mercadofranquia.com.br`.

Two systemd services on the same host:

| Service | Port | Source dir on EC2 | Notes |
|---|---|---|---|
| `mf-web` | 3000 | `/home/ubuntu/mercadofranquia-web/.next/standalone/` | Next.js standalone server. **WorkingDirectory is `.next/standalone/` (not the parent).** |
| `mf-api` | 4000 | `/home/ubuntu/mercadofranquia-api/app/` | FastAPI via uvicorn. Bare routes (no `/api` prefix); nginx adds `/api/` externally. |

## Pre-build checklist (frontend)

1. `web/.env.production.local` exists with prod values:

   ```
   NEXT_PUBLIC_API_URL=https://mercadofranquia.com.br
   NEXT_PUBLIC_SITE_URL=https://mercadofranquia.com.br
   NODE_ENV=production
   ```

2. Build (from inside `web/`):

   ```bash
   npm run build:deploy
   ```

   This runs `scripts/build-standalone.sh`, which validates `.env.production.local`, cleans `.next/`, runs `next build` with `NODE_OPTIONS='--max-old-space-size=2048'`, and copies the 3 artefacts the standalone bundle doesn't include by default into `.next/standalone/`:

   - `.env` (copied from `.env.production.local` — prod values)
   - `public/` (static assets served by Next)
   - `.next/static/` (built JS/CSS chunks served at `/_next/static/*`)

   Don't run `npm run build` directly for a deploy — the standalone bundle ends up missing those 3 artefacts and the site serves broken HTML without CSS/JS or with wrong env.

### Why the script exists

Next 15 in `output: 'standalone'` mode produces a minimal `.next/standalone/` with `server.js` + `node_modules`, but **does not include** `public/`, `.next/static/`, or any `.env.*.local`. Those must be copied post-build for the rsync destination to have everything needed at runtime. The 3 manual copies are easy to forget; the script makes forgetting impossible.

### Sanity grep (optional, post-build)

```bash
grep -rl "localhost:3050" web/.next/standalone/   # expect empty
grep -rl "mercadofranquia.com.br" web/.next/standalone/ | head  # expect chunks
```

`localhost:4000` matches in `server.js`, `routes-manifest.json`, `required-server-files.json` are benign (they come from `next.config.js` rewrites; nginx intercepts `/api/*` before it reaches Next in prod).

## Rsync paths (THE source of truth)

**Frontend** — destination has `.next/standalone/` suffix:

```bash
rsync -az --delete \
  --exclude='node_modules' \
  --exclude='.next/cache' \
  --exclude='.git' \
  web/.next/standalone/ \
  ubuntu@18.230.68.207:/home/ubuntu/mercadofranquia-web/.next/standalone/
```

Why the suffix matters: the `mf-web.service` unit hardcodes `WorkingDirectory=/home/ubuntu/mercadofranquia-web/.next/standalone`. Rsync into the parent dir leaves `server.js` one level above where systemd looks → `MODULE_NOT_FOUND` and the service crashloops (502 on the public site). This bit us during the Sprint 3 Phase 3 deploy — see incident note below.

**Backend**:

```bash
rsync -az --delete \
  --exclude='__pycache__' \
  --exclude='main_local.py' \
  --exclude='.env.local' \
  --exclude='*.pyc' \
  deploy/ec2/app/ \
  ubuntu@18.230.68.207:/home/ubuntu/mercadofranquia-api/app/
```

`main_local.py` and `.env.local` are dev-only (see `deploy/ec2/dev-start.sh`). Always exclude.

## Restart + verify

```bash
ssh ubuntu@18.230.68.207 "sudo systemctl restart mf-web && sudo systemctl restart mf-api"
ssh ubuntu@18.230.68.207 "sudo systemctl is-active mf-web && sudo systemctl is-active mf-api"
```

Both should print `active`. If `mf-web` shows `activating` more than ~10s it is in a restart loop — pull logs immediately:

```bash
ssh ubuntu@18.230.68.207 "sudo journalctl -u mf-web -n 50 --no-pager --since '2 minutes ago'"
```

## Smoke tests

Internal (on EC2):

```bash
ssh ubuntu@18.230.68.207 "
  curl -s -o /dev/null -w 'web=%{http_code}\n' http://localhost:3000
  curl -s http://localhost:4000/health   # FastAPI runs WITHOUT /api prefix; nginx adds it
"
```

External (public):

```bash
curl -s -o /dev/null -w 'web=%{http_code}\n' https://mercadofranquia.com.br/
curl -s https://mercadofranquia.com.br/api/health
```

Expected: web=200, api returns `{"status":"ok"}`.

## Local backend dev

`deploy/ec2/dev-start.sh` boots a local FastAPI on port 4000 with `app/main_local.py` (gitignored wrapper that mounts the prod `app` under `/api` to mirror nginx). `.env.local` (gitignored) supplies `DATABASE_URL`, `JWT_SECRET=desenvolvimento-local-nao-usar-em-producao`, `SES_ENABLED=false`. Frontend points at it via `web/.env.local` (`NEXT_PUBLIC_API_URL=http://localhost:4000`).

**`main_local.py` must also mount `/uploads` as static files** — in prod nginx serves `/uploads/*` directly from disk (bypassing FastAPI), so the prod app itself has no mount. In dev there is no nginx, so without this mount every uploaded logo/thumbnail/gallery image 404s in the browser (broken image icon in the editor and everywhere else that displays user-uploaded media). Minimal working wrapper:

```python
# deploy/ec2/app/main_local.py  (gitignored — exists only on dev machines)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.main import app as base_app
from app.storage import UPLOAD_ROOT

app = FastAPI(
    title="Mercado Franquia API (local wrapper)",
    docs_url=None,
    redoc_url=None,
)

app.mount("/api", base_app)

# Mirror the nginx `location /uploads/` alias so uploaded images render in dev.
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)))
```

Verify with `curl -I http://localhost:4000/uploads/franchises/<any-existing-file>.png` → expect `200 OK`, not `404`.

## Known backlog

- `web/.env` (repo root) still has legacy NestJS values (`localhost:3050`). Cleanup deferred — only matters if someone reads `.env` directly without overriding via `.env.local` / `.env.production.local`.
- `next.config.js` `rewrites()` proxies `/api/*` to `localhost:4000`. Nginx intercepts before this fires in prod, so it's only used in `npm run dev`. Can be made conditional on `NODE_ENV !== 'production'` if we want a cleaner build.

## Incident log

**2026-04-22, ~40min downtime on `mf-web` during Sprint 3 Phase 3 deploy.**
Root cause: rsync destination was `/home/ubuntu/mercadofranquia-web/` instead of `/home/ubuntu/mercadofranquia-web/.next/standalone/`. `server.js` landed in the parent dir; systemd `WorkingDirectory` is the standalone subdir, so node couldn't find the entrypoint. Recovery: re-rsynced to the correct path; mf-web came back in <5s. Lesson: **the destination always has `.next/standalone/` suffix** (now codified above).
