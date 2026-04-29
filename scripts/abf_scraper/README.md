# ABF Scraper — Mercado Franquia

Pipeline pra extrair dados estruturados das **191 fichas ativas** do Portal do Franchising da ABF
(`franquias.portaldofranchising.com.br`) e enriquecer o DB do Mercado Franquia.

## Estado de entrega

Tudo já validado e rodado. Este pacote vem com:

- `output/franchises_index.json` — 191 fichas indexadas (slug, segmento, URL fonte)
- `html_cache/*.html` — 191 HTMLs limpos, sem o pageModel de 28MB (~25MB total)
- `output/parsed/*.json` — 191 JSONs estruturados com modelos, investimento, royalties, imagens
- `output/report.json` — relatório consolidado com estatísticas
- `assets/{slug}/*` — 1.839 imagens baixadas (logo + galeria), 101MB total

## Resultados de extração

| Métrica | Valor |
|---|---|
| Franquias indexadas | 191 |
| Com modelo de negócio extraído | 185 (97%) |
| Com investimento mín/máx | 185 |
| Com total de unidades | 184 |
| Com logo | 175 (92%) |
| Com galeria (≥3 imgs) | 172 (90%) |
| Total de imagens baixadas | 1.839 |
| Tamanho total cache | 25 MB |
| Tamanho total imagens | 101 MB |

## Estrutura do JSON parseado

```json
{
  "slug": "franquia-cacau-show-valor",
  "name": "Cacau Show",
  "segment_abf_name": "Alimentação",
  "abf_updated_at": "08/04/2026",
  "scraped_website": "https://www.cacaushow.com.br/franquia.html",
  "logo_url": "https://static.portaldofranchising.com.br/.../franquia-cacau-show-logo.jpg",
  "gallery_urls": [...17 URLs...],
  "minimum_investment": 64900,
  "maximum_investment": 310000,
  "total_units": 4708,
  "headquarter": "São Paulo",
  "business_models": [
    {
      "name": "Quiosque",
      "investment_total_min": 64900,
      "investment_total_max": 64900,
      "payback_months_min": 18,
      "payback_months_max": 24,
      "area_m2_min": 12,
      "area_m2_max": 15,
      "total_units": 52,
      "advertising_fee_rate": "VARIÁVEL",
      "advertising_fee_base": "Faturamento",
      "royalties_rate": "VARIÁVEL",
      "royalties_base": "Compras",
      ...
    },
    { "name": "Loja", ... }
  ]
}
```

## Como usar localmente no Mac

### 1. Instalar dependências

No seu Mac, em `~/Developer/mercadofranquia/`:

```bash
.venv/bin/pip install beautifulsoup4 lxml
```

### 2. Re-rodar tudo do zero (se quiser)

Não precisa, o pacote já vem com o cache pronto. Mas se quiser regenerar:

```bash
cd ~/Developer/mercadofranquia/scripts/abf_scraper

python3 scripts/abf_scraper.py discover         # ~30s, gera franchises_index.json
python3 scripts/abf_scraper.py fetch             # ~7min, baixa 191 HTMLs
python3 scripts/compress_cache.py                # comprime de ~5GB pra ~25MB
python3 scripts/abf_scraper.py parse             # ~10s, gera parsed/*.json
python3 scripts/download_assets_parallel.py      # ~3min, baixa 1839 imgs
```

### 3. Rodar o enrichment_diff (precisa do dump do DB)

Esse passo cruza com seu DB pra ver o que vai ser preenchido.

**No EC2** (ou local, conectado ao DB de prod):

```bash
psql $DATABASE_URL -t -c "
  SELECT json_agg(row_to_json(f)) FROM (
    SELECT id, slug, name, segment, \"minimumInvestment\", \"maximumInvestment\",
           \"totalUnits\", \"headquarter\", \"logoUrl\", \"scrapedWebsite\",
           description, \"franchiseFee\", royalties
    FROM \"Franchise\"
  ) f;
" > scripts/abf_scraper/output/db_franchises.json
```

Depois, no Mac:

```bash
cd ~/Developer/mercadofranquia/scripts/abf_scraper
python3 scripts/enrichment_diff.py
```

Vai gerar:
- `output/enrichment_diff.json` — diff completo por franquia
- `output/enrichment_summary.txt` — sumário humano

### 4. Próxima fatia (não está aqui, fica para outra sessão)

Depois de revisar o `enrichment_summary.txt`:

- Validar matches com score baixo (<0.85)
- Decidir o que fazer com unmatched (criar nova ou ignorar)
- Rodar script de aplicação no DB (UPSERT em Franchise + INSERT em BusinessModel)
- Sincar imagens pra `/home/ubuntu/mercadofranquia-uploads/abf/{slug}/` no EC2

## Arquivos do scraper

```
scripts/
  abf_scraper.py                  # pipeline principal: discover, fetch, parse, download-assets
  compress_cache.py               # remove pageModel dos HTMLs cacheados (28MB -> 130KB)
  download_assets_parallel.py     # download com 10 workers (3min vs 9min sequencial)
  enrichment_diff.py              # cruza ABF vs DB e gera diff
```

## Premissas e limites

- **Cobertura: ~192 marcas** (associadas premium ABF). Não é o universo total de 1.700 associados,
  mas cobre as marcas relevantes (Cacau Show, Boticário, Casa de Bolos, Fisk, Spoleto, etc).
- **Dados de descrição vêm como imagens narrativas** em algumas fichas (Cacau Show, etc).
  São PNG/JPG que não dão pra extrair texto sem OCR. Decisão: usar como imagens da galeria.
- **Disclaimer ABF**: dados são fornecidos pelo associado, ABF não responde. Logo no DB,
  marcar `dataSource = 'abf-portaldofranchising'` + `scrapedAt = NOW()` pra rastreabilidade.
- **Imagens de marcas registradas**: exibir com atribuição na fonte. Quando o franqueador
  fizer claim via `/anuncie-sua-franquia`, ele substitui pelo conteúdo dele.

## Bugs conhecidos / melhorias

- Algumas fichas (~6) têm 0 modelos e 0 imagens — provavelmente mini-sites incompletos.
  São páginas-categoria que vazaram pelo filtro (já corrigi alguns no `JUNK_SLUGS`).
- Logo extraction tem ~92% de cobertura. Os 8% restantes têm logo em padrão de URL não-padrão.
  Pode-se melhorar com OCR ou inspeção manual.
- Sufixos de slugs ABF não batem com seus slugs (`franquia-cacau-show-valor` vs `cacau-show`).
  O `enrichment_diff.py` faz normalização agressiva pra resolver isso.
