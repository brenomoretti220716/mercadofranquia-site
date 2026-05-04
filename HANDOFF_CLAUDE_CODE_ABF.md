# Handoff — Enriquecimento ABF (Claude Code)

**Origem:** sessão Claude.ai 2026-04-29 — scraper completo das 191 fichas ABF executado e validado.
**Pacotes baixados pelo Breno:** `abf_scraper_essencial.tar.gz` + `abf_scraper_html_cache.tar.gz` + `abf_scraper_assets.tar.gz` (em `~/Downloads/`).

## Objetivo desta fatia

Operação pontual: cruzar 191 fichas ABF com 1.403 franquias do Postgres, fazer gap analysis (campos vs schema atual), aplicar enriquecimento.

**Não é parte da Fatia 1.10 (Reviews).** É paralelo. Roda quando der.

## Contexto resumido do scraper

Fonte: `franquias.portaldofranchising.com.br`. Universo total de fichas ativas no portal: **191** (não 1.700 — esse é o número de associados ABF totais, mas só uma fração paga pelo mini-site público). Resultados:

| Métrica | Valor |
|---|---|
| Fichas indexadas | 191 |
| Com modelo de negócio extraído | 185 (97%) |
| Com investimento mín/máx | 185 |
| Com total de unidades | 184 |
| Com logo | 175 (92%) |
| Com galeria (≥3 imgs) | 172 (90%) |
| Imagens baixadas | 1.839 |

## Estrutura completa de uma ficha ABF parseada

Esse é o ponto crítico pra gap analysis. Ler com atenção.

```json
{
  "slug": "franquia-cacau-show-valor",
  "scraped_at": "2026-04-29T11:18:08Z",
  "source_url": "https://franquias.portaldofranchising.com.br/...",

  "name": "Cacau Show",
  "tagline": "...",
  "meta_description": "A franquia Cacau Show é a maior rede...",

  "segment_abf_id": "alimentacao",
  "segment_abf_name": "Alimentação",
  "abf_updated_at": "08/04/2026",

  "scraped_website": "https://www.cacaushow.com.br/franquia.html",
  "scraped_website_with_utm": "...",

  "logo_url": "https://static.portaldofranchising.com.br/.../logo.jpg",
  "og_image": "https://static.portaldofranchising.com.br/.../banner.jpg",
  "gallery_urls": ["url1", "url2", ...],

  "minimum_investment": 64900,
  "maximum_investment": 310000,
  "total_units": 4708,
  "headquarter": "São Paulo",

  "business_models": [
    {
      "name": "Quiosque",
      "headquarter": "São Paulo",
      "total_units": 52,
      "capital_installation_min": 39900,
      "capital_installation_max": 39900,
      "franchise_fee_min": 10000,
      "franchise_fee_max": 10000,
      "working_capital_min": 15000,
      "working_capital_max": 15000,
      "investment_total_min": 64900,
      "investment_total_max": 64900,
      "payback_months_min": 18,
      "payback_months_max": 24,
      "area_m2_min": 12,
      "area_m2_max": 15,
      "advertising_fee_rate": "VARIÁVEL",
      "advertising_fee_base": "Faturamento",
      "advertising_fee_observation": null,
      "royalties_rate": "VARIÁVEL",
      "royalties_base": "Compras",
      "royalties_observation": null
    },
    { "name": "Loja", ... }
  ]
}
```

## Pré-requisitos antes de começar

```bash
# 1. Tarballs em ~/Downloads
ls -lh ~/Downloads/abf_scraper_*.tar.gz
# esperado: 91 KB + 3.2 MB + 95 MB

# 2. Ambiente OK
cd ~/Developer/mercadofranquia
.venv/bin/python --version  # 3.14
psql -U mf_user -d mercadofranquia -c 'SELECT COUNT(*) FROM "Franchise";'
# esperado: 1403
```

## Etapas de execução

### Etapa 1 — Setup

```bash
cd ~/Developer/mercadofranquia
mkdir -p scripts && cd scripts

tar xzf ~/Downloads/abf_scraper_essencial.tar.gz
cd abf_scraper
tar xzf ~/Downloads/abf_scraper_html_cache.tar.gz --strip-components=1
tar xzf ~/Downloads/abf_scraper_assets.tar.gz --strip-components=1

cd ~/Developer/mercadofranquia
.venv/bin/pip install beautifulsoup4 lxml

# validação
ls scripts/abf_scraper/output/parsed | wc -l        # 191
ls scripts/abf_scraper/html_cache | wc -l           # 191
find scripts/abf_scraper/assets -type f | wc -l     # 1839
cat scripts/abf_scraper/README.md                   # leia antes de continuar
```

### Etapa 2 — Dump da tabela Franchise + BusinessModel

```bash
cd ~/Developer/mercadofranquia/scripts/abf_scraper

# dump completo de Franchise
psql -U mf_user -d mercadofranquia -t -c '
  SELECT json_agg(row_to_json(f)) FROM (
    SELECT id, slug, name, segment, subsegment, "businessType",
           "minimumInvestment", "maximumInvestment",
           "totalUnits", "totalUnitsInBrazil", "unitsEvolution",
           "headquarter", "headquarterState",
           "logoUrl", "thumbnailUrl", "videoUrl", "galleryUrls",
           "scrapedWebsite",
           description, "detailedDescription",
           "franchiseFee", royalties, "advertisingFee",
           "calculationBaseRoyaltie", "calculationBaseAdFee",
           "setupCapital", "workingCapital", "storeArea",
           "isAbfAssociated", "abfSince",
           "averageMonthlyRevenue",
           "minimumReturnOnInvestment", "maximumReturnOnInvestment",
           "franchiseStartYear", "brandFoundationYear"
    FROM "Franchise"
  ) f;' > output/db_franchises.json

# dump de BusinessModel (se existir tabela separada)
psql -U mf_user -d mercadofranquia -t -c '
  SELECT json_agg(row_to_json(b)) FROM (SELECT * FROM "BusinessModel") b;
' > output/db_business_models.json 2>/dev/null || echo "BusinessModel não existe ou está vazia"

# validação
python3 -c 'import json; print(f"Franchise: {len(json.load(open(\"output/db_franchises.json\")))}")'
# esperado: 1403
```

### Etapa 3 — GAP ANALYSIS (etapa nova, importante)

**Antes de rodar enrichment_diff**, criar script `scripts/gap_analysis.py` que faz o seguinte:

1. **Schema introspection** — pega colunas reais de `Franchise` e `BusinessModel` (se existir):
   ```sql
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name = 'Franchise';
   ```

2. **Mapeamento ABF → schema atual** — pra cada campo do JSON ABF, marca:
   - ✅ existe no DB (com nome correspondente)
   - ⚠️ existe semanticamente mas com nome diferente (ex: `payback_months_min` vs `minimumReturnOnInvestment` — qual unidade?)
   - ❌ não existe no DB — **gap**

3. **Lista de gaps com proposta de migration**:

   Pelo que sei do schema atual, esses campos do ABF **provavelmente não existem**:
   - `business_models[].capital_installation_min/max` — DB tem só `setupCapital` (sem range)
   - `business_models[].franchise_fee_min/max` — DB tem só `franchiseFee` (sem range)
   - `business_models[].working_capital_min/max` — DB tem só `workingCapital` (sem range)
   - `business_models[].investment_total_min/max` — DB tem `minimumInvestment`/`maximumInvestment` mas só na Franchise, não por modelo
   - `business_models[].payback_months_min/max` — DB tem `minimum/maximumReturnOnInvestment` (qual unidade? meses ou anos?)
   - `business_models[].area_m2_min/max` — DB tem `storeArea` (string, sem range)
   - `business_models[].advertising_fee_observation` — provavelmente não existe
   - `business_models[].royalties_observation` — provavelmente não existe
   - `abf_updated_at` — não existe (campo novo importante pra rastreabilidade)
   - `og_image` — DB tem `thumbnailUrl` mas semanticamente é diferente (banner vs thumb pequeno)

   E campos que **podem existir** mas com nome diferente:
   - ABF `headquarter` (texto livre tipo "São Paulo") vs DB `headquarter` + `headquarterState` (separados)
   - ABF `total_units` (por modelo) vs DB `totalUnits` (agregado na Franchise)

4. **Output do gap_analysis.py** deve ser:

   - `output/schema_current.json` — schema atual de `Franchise` e `BusinessModel`
   - `output/gap_report.md` — relatório markdown com 4 seções:
     1. **Campos ABF que casam direto com DB** (mapeamento 1-1)
     2. **Campos ABF que casam semanticamente mas precisam normalização** (com proposta de transformação)
     3. **Campos ABF sem correspondência no DB** (gaps reais — propor migration)
     4. **Campos do DB que ABF não tem** (não tem ação, só pra contexto — esses ficam como estão)
   - `output/proposed_migration.sql` — DDL Alembic-style com colunas novas sugeridas

5. **Pontos críticos que o gap analysis deve responder explicitamente**:
   - **Tabela BusinessModel existe?** Se não, decisão: criar agora (essa fatia tem nome `BusinessModel` na memória, mas confirmar) ou achatar tudo na Franchise como JSON?
   - **Como modelar ranges?** Hoje DB tem só 1 valor por campo financeiro. Migrar pra `_min`/`_max` em todos? Manter 1 valor e usar `min` como fonte de verdade? Decisão antes de qualquer migration.
   - **Como modelar royalties/propaganda com base de cálculo dinâmica?** ABF traz `rate` + `base` + `observation` — texto livre. DB tem `royalties` (number) + `calculationBaseRoyaltie` (string). Precisa expandir?

**Esse passo de gap analysis é pré-requisito de qualquer migration.** Não tomar decisão estrutural antes de ver o relatório completo.

### Etapa 4 — Rodar enrichment_diff (depois do gap analysis decidido)

```bash
cd ~/Developer/mercadofranquia/scripts/abf_scraper
.venv/bin/python scripts/enrichment_diff.py
```

Output:
- `output/enrichment_diff.json` — diff por franquia
- `output/enrichment_summary.txt` — sumário humano

Critérios de avaliação:
- **Matches com score ≥ 0.95** → aplicar UPSERT direto
- **Matches com score 0.85–0.94** → revisar visualmente, confirmar e aplicar
- **Matches com score 0.75–0.84** → revisar manualmente cada um
- **Unmatched (~20-30 esperados)** → criar novas Franchises com origem `dataSource = 'abf-portaldofranchising'`

### Etapa 5 — Aplicar (depois das decisões da etapa 3 e 4)

Estratégia em fatias:
1. Migration com colunas novas (resultado do gap analysis)
2. Aplicar local primeiro com transação aberta — validar contagens
3. Backup do prod (`pg_dump` da `Franchise` e `BusinessModel`)
4. Aplicar prod via `rsync` da migration + `alembic upgrade head`
5. Sincar imagens: `rsync -avz scripts/abf_scraper/assets/ ubuntu@18.230.68.207:/home/ubuntu/mercadofranquia-uploads/abf/`

## Premissas e regras

- Disclaimer ABF: dados são fornecidos pelo associado, ABF não responde. Logo no DB, marcar `dataSource = 'abf-portaldofranchising'` + `scrapedAt = NOW()` pra rastreabilidade.
- **Nunca sobrescrever campo já preenchido pelo franqueador** (origem `manual` ou `claimed`). Só preencher campos `NULL`.
- Imagens: tratar como acervo "rascunho". Quando franqueador fizer claim via `/anuncie-sua-franquia`, ele substitui pelo conteúdo dele.
- Antes de qualquer migration, conferir CHECK constraints legadas Prisma (memória do Breno: elas são invisíveis ao ORM e quebram migrations).

## Decisões editoriais que o Breno vai precisar dar na Etapa 3

O Claude Code não deve tentar inferir nada disso. Pergunte ao Breno **antes** de propor migration ou estratégia de UPSERT. São 6 perguntas:

1. **Política de UPSERT por campo** — pra cada campo do scraper, qual estratégia?
   - (A) Scraper é fonte de verdade — sempre sobrescreve
   - (B) Scraper preenche só se DB está NULL
   - (C) Scraper é descartado se DB tem qualquer valor
   - (D) Caso a caso (preciso ver os exemplos)
   *Sugerido como default: (B), exceto pra `abf_updated_at` que é (A) sempre.*

2. **Tabela `BusinessModel` — descobrir no DB primeiro, depois decidir.**
   - Se existe: scraper popula 1:N (cada modelo ABF = 1 row)
   - Se não existe: criar agora ou achatar tudo na `Franchise` como `business_models JSON`?

3. **Modelagem de ranges (`_min`/`_max`)** — descoberta antes da decisão.
   - Se DB tem só `franchiseFee` (1 valor), o que fazer com `franchise_fee_min/max` do ABF?
     (i) usar `min` como `franchiseFee`, descartar `max`
     (ii) migrar coluna pra `_min`/`_max` (mais correto, custa migration)
     (iii) string concatenada "10000-15000" (gambiarra, evita migration mas perde tipagem)

4. **Royalties/propaganda com observação textual** — ABF traz `rate` + `base` + `observation` (livre). DB tem `royalties` numérico + `calculationBaseRoyaltie` string. O que fazer com `observation`?
   - Criar coluna `royaltiesObservation` text?
   - Concatenar em `description`?
   - Descartar?

5. **`abf_updated_at`** — campo novo importante. Como nomear?
   - `abfUpdatedAt` (timestamp) — segue padrão camelCase do schema
   - Adicionar junto com `dataSource` (string) e `scrapedAt` (timestamp) na mesma migration
   *Sugerido como pacote único, pra rastreabilidade completa.*

6. **Imagens — onde sincar e como nomear no DB?**
   - Path proposto no EC2: `/home/ubuntu/mercadofranquia-uploads/abf/{slug}/`
   - URL pública: `https://mercadofranquia.com.br/uploads/abf/{slug}/logo.jpg` (nginx já serve `/uploads/`)
   - DB salva URL absoluta ou path relativo `/uploads/abf/{slug}/logo.jpg`?
   *Sugerido: path relativo, segue padrão atual de `logoUrl` que tem `/uploads/...`*

**Não comece a Etapa 4 antes de receber resposta às 6.** São decisões de negócio + arquitetura que só o Breno tem contexto pra dar.

## Ordem recomendada de PRs

1. **PR 1** — script `gap_analysis.py` + `output/gap_report.md` commitado em `scripts/abf_scraper/`. Não toca DB ainda.
2. **PR 2** — discussão das decisões de modelagem (tabela `BusinessModel`? ranges min/max? royalties expandido?). Pode ser conversa com Breno antes do PR 3.
3. **PR 3** — migration Alembic com colunas novas (após decisão).
4. **PR 4** — script `apply_enrichment.py` + execução local + relatório de aplicação.
5. **PR 5** — deploy prod (migration + apply + rsync de imagens).

## Bugs/limitações conhecidos do scraper

- ~6 fichas têm 0 modelos e 0 imagens (mini-sites incompletos do associado). OK descartar.
- Logo extraction tem 92% de cobertura. Os 8% sem logo, ignorar — o scraped_website tem o link pro site oficial, dá pra puxar logo de lá depois se quiser.
- Texto descritivo nas fichas ABF vem frequentemente como **imagens narrativas** (PNG/JPG com texto embutido). Não dá pra OCR sem custo. Decisão: tratar como imagens da galeria, não tentar extrair `description`.

## Como reportar progresso

Ao final de cada etapa, atualizar `HANDOFF.md` na raiz do projeto com:
- O que foi feito
- O que decidiu
- Próximo passo

Pra que se a sessão for interrompida, a próxima retoma sem perder contexto.
