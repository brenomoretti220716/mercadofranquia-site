# Handoff — ABF Enrichment DEPLOYED

**Data deploy:** 2026-04-29 (apply enrichment) e 2026-04-30 (banner + post-enrichment)
**Branch:** `feat/abf-enrichment` (PR #10 draft, baseada em `feat/fatia-1-10-1-reviews-backend`)

## Estado prod consolidado

| Métrica | Valor |
|---|---|
| Franchises totais | **1.411** (1.404 base + 7 will_create) |
| BusinessModels totais | **233** (todos novos via apply enrichment) |
| Franchises tocadas pelo ABF | 183 (176 will_enrich + 7 will_create) |
| Franchises skipped_claimed | 2 (Cacau Show, Market4U) |
| `bannerUrl` populados | 176 |
| `dataSource = 'abf-portaldofranchising'` | 7 (will_create) |
| `dataSource = 'imported-legacy'` | 1.404 (backfill data migration) |
| `dataSource IN ('manual', 'claimed')` | 0 (ninguém reivindicou ainda) |

## Arquivos físicos em prod

`/home/ubuntu/mercadofranquia-api/uploads/abf/` — **183 dirs renomeados** (`{db_slug}/`), cada um com:
- `logo.{ext}` (em geral .svg ou .png; 175 cobertura ~)
- `banner.{ext}` (174 jpg + 4 png; 178/179 baixados, 1 falha em tz-viagens)
- `gallery_NN.{ext}` (~10 fotos por franquia, ordem do scraper preservada)

**2 dirs órfãos no filesystem** (não usados, podem ser limpos no backlog):
- `franquia-cacau-show-valor/`
- `franquia-market4u/`

Ambos são skipped_claimed — assets foram baixados pelo scraper mas o DB não foi tocado.

## Decisões editoriais aplicadas

1. **Skip-claimed por franquia** (não por campo): se `ownerId IS NOT NULL` OU `dataSource IN ('manual', 'claimed')`, scraper não toca em nada da franquia — nem campo, nem asset, nem BM.

2. **`set_if_null` pros campos do scraper**: scraper só preenche campos que estavam NULL no DB. Preserva trabalho anterior.

3. **`set_always` pra rastreabilidade**: `abfUpdatedAt`, `lastScrapedAt` sempre atualizados (são fatos).

4. **`dataSource` set apenas em INSERT ou rows com `dataSource IS NULL`**: rows pré-migration ficaram `imported-legacy` no data migration, e não foram sobrescritas.

5. **Ranges no BusinessModel**: usado `_min` como valor único, `_max` descartado nesta fatia. Decisão de não fazer migration `_min`/`_max` agora.

6. **Royalties / advertisingFee parser context-aware**:
   - `is_fixed`: rate ou base contendo "fixo", "r$", "reais" → NULL no NUMERIC + texto bruto na observation
   - Sanity range: royalties 0-30%, ad 0-10% (% acima é certeza valor fixo mal-rotulado)
   - Parser numérico passa só com 2 checks
   - Resultado: 147 royalties NUMERIC válidos + 86 NULL+observation

## Migration deployed

**`349aae4b13f8`** (alembic):
- `Franchise.abfUpdatedAt DATE`, `Franchise.dataSource VARCHAR(50)` + CHECK constraint com 5 valores: `manual`, `claimed`, `abf-portaldofranchising`, `encontresua-franquia`, `imported-legacy`
- Data migration: backfill `dataSource='imported-legacy'` em 1.404 rows pré-existentes
- `BusinessModel.description` e `photoUrl` viraram nullable (eram NOT NULL — bloqueavam insert via scraper)
- `BusinessModel`: 4 colunas novas (`headquarter`, `totalUnits`, `advertisingFeeObservation`, `royaltiesObservation`)

## Backlog conhecido

### 7 fichas sem banner

```
franquia-aslan-idiomas-educacao
franquia-club-kids
franquia-happy-hub-educacional
franquia-naopelonovello
franquia-tcharge
franquia-vcautor
franquia-tz-viagens (download deu 403 isolado)
```

`bannerUrl` permanece NULL pra essas. Frontend deve ter fallback. Investigar layouts alternativos do portal ABF se valer.

### 2 dirs órfãos no `uploads/abf/`

Já mencionados acima. Decisão consciente: deixar pra limpeza futura.

### `og_image` ignorado

Parser captura mas não vai pro DB (sem coluna). Fica no `output/parsed/*.json` se decidir usar depois.

### Bug do scraper SSL

`download_assets_parallel.py` precisava de `ssl.create_default_context(cafile=certifi.where())` explícito — fix incluído no PR. Sem isso, banners novos (que não estavam no skip-existing) falhavam com `CERTIFICATE_VERIFY_FAILED`.

### Bug do macOS sidecars (`._*.json`)

Tar do Mac inclui resource forks `._*` se arquivos têm extended attributes. Em `glob("*.json")` do Python, esses entram. Mitigação: `tar --exclude='._*'` e `find /destination -name '._*' -delete` pós-extract. Lição pra próximos deploys.

## Scripts versionados (PR #10)

- `scripts/abf_scraper/scripts/abf_scraper.py` — parser + report (com banner extraction via `img.main-img.lazyload`)
- `scripts/abf_scraper/scripts/download_assets_parallel.py` — download paralelo (com SSL context fix + banner support)
- `scripts/gap_analysis.py` — script reproduzível
- `scripts/apply_enrichment.py` — UPSERT com skip-claimed + parser context-aware
- `scripts/apply_post_enrichment.py` — rename + rewrite URLs + populate bannerUrl (3 fases)

## Arquivos NÃO commitados (em `.gitignore`)

- `scripts/abf_scraper/html_cache/` (24 MB, regenerável)
- `scripts/abf_scraper/assets/` (124 MB locais, vão pro EC2 via rsync)
- `scripts/abf_scraper/output/parsed/` (185 JSONs, dados editoriais ABF)
- `scripts/abf_scraper/output/db_*.json` (snapshots locais)
- `scripts/abf_scraper/output/enrichment_diff.json` (~150KB, regenerável)
- `scripts/abf_scraper/output/enrichment_summary.txt`

## Backups

- `/home/ubuntu/backups/backup_pre_abf_enrichment_20260429_165108.sql` (1.9 MB) — Franchise + BusinessModel + alembic_version pré-apply

## Próxima sessão (sugestões)

1. **Mergear PR #10** (depois de PR #9 da Fatia 1.10.1 mergear primeiro — dependência alembic).
2. **Cleanup tarballs originais em `/tmp/` do Mac** (95 MB total) ou arquivar offsite.
3. **Investigar 7 fichas sem banner** se valer (provável layout legacy do portal ABF).
4. **Considerar implementar `apply_enrichment.py --apply` com BusinessModel inserts diretos** se quiser rodar pra outras fontes de dados (`encontresua-franquia` mencionada na CHECK constraint).
5. **Cleanup os 2 dirs órfãos** (`franquia-cacau-show-valor`, `franquia-market4u`) se preferir filesystem limpo.
6. **Auditar Reviews em prod** pra ver se as 7 reviews seedadas em cacau-show (do trabalho da Fatia 1.10.1) estão renderizando corretamente após o ABF enrichment não ter tocado nela (skipped_claimed).
