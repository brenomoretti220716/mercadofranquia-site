# Handoff — ABF Refresh DEPLOYED (Fatia A)

**Data deploy:** 2026-05-04
**Branch:** `feat/abf-enrichment` (PR #10 draft, ainda não merged)
**Commit:** `17915f6`
**Predecessor:** `HANDOFF_ABF_DEPLOYED.md` (deploy original ABF v1, 2026-04-29/30)

## TL;DR

Refresh completo dos dados ABF em prod. Override total (não set-if-null), nova
migration `business_model_royalty_v2` adicionando 4 colunas em BusinessModel,
3 campos editoriais novos no parser (`videoUrl`, `detailedDescription`,
`idealFranchiseeProfile`).

## Estado prod consolidado pós-refresh

| Métrica | Valor |
|---|---|
| Franchises totais | **1.411** (inalterado) |
| BusinessModels totais | **237** (233 ABF refresh + 4 não-ABF preservados) |
| Franchises tocadas pelo refresh | 183 (override total) |
| Franchises skipped_claimed | **0** (post-cleanup, ninguém claimed) |
| Whitelist (não tocadas) | 2 (`pizza-teste`, `star-point`) — não estão no ABF |
| `bannerUrl` em /uploads/abf/ | **177** (todos hot-linked → /uploads/) |
| `logoUrl` em /uploads/abf/ | 173 |
| `galleryUrls` em /uploads/abf/ | 174 |
| `videoUrl` (YouTube) | 156 (150 do refresh + 6 preservados) |
| `detailedDescription` populated | 183 (median 1.762 chars) |
| `idealFranchiseeProfile` populated | 139 |
| `dataSource = 'imported-legacy'` | 1.404 |
| `dataSource = 'abf-portaldofranchising'` | 7 |

## Migration aplicada

**`3c59cb1b21a4`** (alembic, head atual):

```sql
ALTER TABLE "BusinessModel"
  ADD COLUMN "royaltyType" varchar(20),
  ADD COLUMN "royaltyFixedAmount" integer,
  ADD COLUMN "adFeeType" varchar(20),
  ADD COLUMN "adFeeFixedAmount" integer;

ALTER TABLE "BusinessModel"
  ADD CONSTRAINT "BusinessModel_royaltyType_check"
    CHECK ("royaltyType" IS NULL OR "royaltyType" IN
           ('PERCENTAGE','FIXED','VARIABLE','NONE'));

ALTER TABLE "BusinessModel"
  ADD CONSTRAINT "BusinessModel_adFeeType_check"
    CHECK ("adFeeType" IS NULL OR "adFeeType" IN
           ('PERCENTAGE','FIXED','VARIABLE','NONE'));
```

Backfill defensivo aplicado (validado via Query 3 prévia ao apply):
- 148 BMs PERCENTAGE
- 29 BMs FIXED (com `royaltyFixedAmount` extraído de observation, faixa R$ 300–4.165)
- 59 BMs NULL (truly unknown, preservada ambiguidade)

Pós-refresh, distribuição final mudou (BMs deletados+recriados):
- 151 PERCENTAGE / 38 FIXED / 31 NONE / 13 VARIABLE para royalty
- 122 PERCENTAGE / 37 FIXED / 62 NONE / 12 VARIABLE para ad_fee
- 0 NULL (todos os BMs do scrape têm tipo derivado)

## 3 fichas stale (preservadas)

```
franquia-blow              → blow              (saiu do portal ABF)
franquia-evolve-energia-solar → evolve-energia-solar
franquia-giuliana-flores   → giuliana-flores
```

Estado em prod:
- DB tem `abfUpdatedAt` da rodada anterior
- URLs apontam pra `/uploads/abf/{db_slug}/` (preservadas)
- Dirs renomeadas no filesystem pra alinhar (`franquia-blow → blow` etc)
- Não tocadas pelo refresh (não estão no scrape novo)

Decisão: **deixa intactas**. Saída do portal pode ser temporária (franquia
atualizando). Se confirmar descontinuidade, decisão futura caso a caso.

## Arquivos físicos em prod

`/home/ubuntu/mercadofranquia-api/uploads/abf/` — **186 dirs renomeadas** (`{db_slug}/`):
- 183 ABF refresh (todas com `franquia-{abf_slug}` original renomeada pra `{db_slug}`)
- 3 stale (idem)
- 6 placeholders vazios de segmentos (0B, ignoráveis)

Conteúdo típico:
- `logo.{ext}` (svg, png ou jpg)
- `banner.{ext}` (jpg ou png)
- `gallery_NN.{ext}` (avg ~9 fotos)

## Mudanças no parser (`scripts/abf_scraper/scripts/abf_scraper.py`)

1. **SSL fix**: `import certifi` + `SSL_CTX = ssl.create_default_context(cafile=certifi.where())` em `http_get` e `http_get_binary`. Mesma correção do scrape ESF.

2. **Gap 1 — videoUrl**: regex YouTube/Vimeo, primeiro match, normalizado pra `https://...`.

3. **Gap 2 — detailedDescription**: extrai bloco `<h2>Sobre a franquia X</h2>` até próximo `<h2>` ou `<hr class="border-separator">`. Threshold mínimo 200 chars (descarta placeholder + imagem).

4. **Gap 3 — idealFranchiseeProfile**: mesma técnica, marker `<h2>Perfil do franqueado X</h2>`. Threshold 150 chars.

5. **Gap 4 — processSteps**: **skipado**. Cobertura ~30% das fichas (maioria usa infográfico em imagem), schema `{title, description}` exigiria descriptions inventadas. Backlog estratégico.

6. **CLI `--slugs`**: filtro por slug pra parse de subset. Útil pra validação.

7. **Helper `_extract_section_text`**: HTML → texto limpo (decode entities, `<br>` → `\n`, `</p>` → `\n\n`, strip remaining tags).

## Scripts versionados (commit 17915f6)

- `scripts/abf_scraper/scripts/abf_scraper.py` — parser + 5 patches
- `scripts/apply_abf_refresh.py` — **NEW** (685 linhas) override total + skip whitelist + populate royalty types
- `scripts/apply_post_enrichment.py` — **Patch A**: banner agora reescreve hot-linked (não só NULL), UPDATE sem filtro de NULL, rowcount-based reporting

## Bug encontrado durante apply (corrigido)

Patch A original tinha sido aplicado só na lógica de **preflight**. UPDATE em
`apply_db()` mantinha `WHERE slug = :slug AND "bannerUrl" IS NULL`. Resultado:
primeiro `--apply` reportou "Banner: 177 OK" mas `rowcount = 0`. Fix posterior
removeu o filtro NULL no UPDATE + passou a contar via `res.rowcount`.

Sem dano permanente. Re-execução do apply pegou os 177 banners corretamente.
Renames de filesystem são idempotentes (segunda execução fez `0/0 renames`).

## Backups

- `/home/ubuntu/backups/backup_pre_business_model_royalty_v2_20260504_123305.sql` (3.1MB) — pré-migration
- `/home/ubuntu/backups/backup_pre_abf_refresh_20260504_143535.sql` (3.1MB) — pré-apply
- `/home/ubuntu/backups/backup_pre_abf_enrichment_20260429_165108.sql` (1.9MB) — original deploy v1

## Smoke test 3 URLs (todos HTTP 200)

| URL | Resultado |
|---|---|
| `/ranking/cacau-show` | banner + logo + gallery + video YouTube embed (`bJ2pw45Vz64`) |
| `/ranking/chilli-beans` | banner + video + 2 BMs visíveis (Loja, Quiosque) |
| `/ranking/pizza-teste` | 0 refs a `/uploads/abf/` (whitelist preservada) |

## Backlog frontend (não bloqueia)

🟡 **2 campos populados em DB sem componente que renderize:**

1. **`detailedDescription`** (text editorial 1.5K chars median, 183 fichas) — esperando block "Sobre a marca" ou similar
2. **`idealFranchiseeProfile`** (139 fichas) — esperando block "Perfil ideal de franqueado" ou similar

Próxima fatia frontend pode adicionar esses 2 blocks na página de detalhe.
Conteúdo já está no DB esperando.

## Próximos passos

### Imediato (próxima sessão)

**Volta pra branch `feat/encontresua-enrichment`** (commit `29c72a1`, intacta no remote).

Continua plano original de Deploy 1 + Deploy 2 EncontreSuaFranquia:
- 800 fichas scraped (87.2% overlap com prod = 698 enrich + 102 will_create)
- Etapa 2: Refatora parser ESF pra royalty types (similar derive_rate_fields)
- Etapa 3: Regenera descrições via Claude API (claude-haiku-4-5-20251001, ~$4 USD)
- Etapa 4: Apply Deploy 1 (campos estruturados)
- Etapa 5: Apply Deploy 2 (descriptions regeneradas)

### Futuro

- **Frontend:** componentes pra `detailedDescription` + `idealFranchiseeProfile`
- **Cleanup:** 6 dirs vazios (`franquia-casa`, `franquia-comunicacao`, etc) em `/uploads/abf/` — placeholders de segmentos, descartar
- **3 stale:** decisão sobre Blow/Evolve/Giuliana Flores se mantiverem fora do portal por mais tempo
- **CHECK constraint** em `calculationBaseRoyaltie`/`calculationBaseAdFee`: adiada — long tail tem 14 valores distintos com noise não-normalizável
- **PR #9 (Reviews v2)** + **PR #10 (ABF refresh)**: ainda em draft, não merged
