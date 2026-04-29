#!/usr/bin/env python3
"""Gap analysis ABF Scraper x Schema atual do Mercado Franquia.

Compara fields do JSON parseado pelo scraper ABF com colunas reais das
tabelas Franchise e BusinessModel no Postgres. Produz 3 outputs:

- output/schema_current.json — schema atual (introspeccao via psql)
- output/gap_report.md — relatorio markdown com 4 secoes:
  1. Mapeamentos diretos (1:1)
  2. Mapeamentos semanticos (precisam transformacao)
  3. Gaps reais (campos ABF sem destino — propor migration)
  4. Campos DB sem correspondencia ABF (so contexto, nao tem acao)
- output/proposed_migration.sql — DDL Alembic-style com colunas novas

NAO toma decisao estrutural. So mapeia. As 6 perguntas editoriais ficam
explicitas no final do relatorio pra o Breno responder antes da migration.

Uso:
    cd scripts/abf_scraper
    /Users/brenomoretti/Developer/mercadofranquia/.venv/bin/python ../gap_analysis.py

Pre-reqs:
- DB local rodando com schema sincronizado a prod (revision 9e73d144e686)
- output/parsed/*.json com 191 fichas ABF parseadas
- DATABASE_URL ou variaveis PG no env (default: dev_password_local)
"""
from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

# ============================================================================
# Paths
# ============================================================================
SCRAPER_ROOT = Path("/Users/brenomoretti/Developer/mercadofranquia/scripts/abf_scraper")
PARSED_DIR = SCRAPER_ROOT / "output" / "parsed"
OUTPUT_DIR = SCRAPER_ROOT / "output"

DB_USER = os.environ.get("PGUSER", "mf_user")
DB_NAME = os.environ.get("PGDATABASE", "mercadofranquia")
DB_HOST = os.environ.get("PGHOST", "localhost")
DB_PASSWORD = os.environ.get("PGPASSWORD", "dev_password_local")


# ============================================================================
# Schema introspection
# ============================================================================
def fetch_schema(table_name: str) -> list[dict[str, Any]]:
    """Le schema de uma tabela via psql."""
    sql = f"""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = '{table_name}'
    ORDER BY ordinal_position;
    """
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    result = subprocess.run(
        ["psql", "-h", DB_HOST, "-U", DB_USER, "-d", DB_NAME, "-A", "-F", "|", "-t", "-c", sql],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    cols = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        cols.append(
            {
                "name": parts[0],
                "type": parts[1],
                "nullable": parts[2] == "YES",
                "default": parts[3] if len(parts) > 3 else None,
            }
        )
    return cols


# ============================================================================
# Mapping rules — decisoes de dominio (hardcoded, baseadas em leitura do JSON
# scraper + schema atual). NAO inferido dinamicamente. As decisoes editoriais
# de "como aplicar" ficam pra resposta do Breno.
# ============================================================================

# Mapeamento direto ABF -> Franchise (1:1, mesmo significado, basta UPSERT)
DIRECT_FRANCHISE = {
    "slug": "slug",
    "name": "name",
    "scraped_website": "scrapedWebsite",
    "scraped_at": "lastScrapedAt",
    "logo_url": "logoUrl",
    "minimum_investment": "minimumInvestment",
    "maximum_investment": "maximumInvestment",
    "total_units": "totalUnits",
    "headquarter": "headquarter",  # ABF traz texto livre, DB aceita string
}

# Mapeamento direto ABF business_models -> BusinessModel (1:1)
DIRECT_BUSINESS_MODEL = {
    "name": "name",
    # ABF business_models[].capital_installation_min -> setupCapital (usar min)
    # ABF business_models[].franchise_fee_min -> franchiseFee (usar min)
    # esses sao SEMANTIC abaixo
}

# Mapeamento semantico — campos casam mas precisam transformacao/normalizacao
SEMANTIC_FRANCHISE = {
    "segment_abf_name": {
        "db_col": "segment",
        "transform": "ABF traz nome legivel ('Alimentacao'), DB tem string livre. Pode salvar direto OU normalizar pra sigla.",
    },
    "meta_description": {
        "db_col": "description ou detailedDescription",
        "transform": "ABF meta_description e ~155 chars. Cabe em description (text). Decidir qual coluna alvo.",
    },
    "gallery_urls": {
        "db_col": "galleryUrls",
        "transform": "DB armazena como TEXT (string JSON). Scraper traz list[str]. UPSERT precisa json.dumps().",
    },
}

SEMANTIC_BUSINESS_MODEL = {
    "investment_total_min/max": {
        "db_col": "investment (NUMERIC, single)",
        "transform": "DB tem 1 valor; ABF tem range. Decidir: usar min, expandir pra _min/_max, ou string range.",
    },
    "payback_months_min/max": {
        "db_col": "payback (INTEGER, single)",
        "transform": "Mesma decisao. ABF traz meses (e.g., 18-24); DB ja em meses (integer). Confirmar unidade.",
    },
    "area_m2_min/max": {
        "db_col": "storeArea (INTEGER, single)",
        "transform": "DB single integer; ABF range float. Mesma decisao de range.",
    },
    "franchise_fee_min/max": {
        "db_col": "franchiseFee (NUMERIC, single)",
        "transform": "Mesma decisao de range.",
    },
    "working_capital_min/max": {
        "db_col": "workingCapital (NUMERIC, single)",
        "transform": "Mesma decisao de range.",
    },
    "capital_installation_min/max": {
        "db_col": "setupCapital (NUMERIC, single)",
        "transform": "Mesma decisao de range.",
    },
    "advertising_fee_rate": {
        "db_col": "advertisingFee (NUMERIC) + calculationBaseAdFee (string)",
        "transform": "ABF traz string ('VARIAVEL', '2%', '5,5%') que NAO bate com NUMERIC do DB. Precisa parser OU coluna text nova.",
    },
    "advertising_fee_base": {
        "db_col": "calculationBaseAdFee",
        "transform": "Direto, mas DB e VARCHAR(191). Verificar tamanho dos valores ABF.",
    },
    "royalties_rate": {
        "db_col": "royalties (NUMERIC) + calculationBaseRoyaltie",
        "transform": "Mesma situacao do advertising_fee_rate.",
    },
    "royalties_base": {
        "db_col": "calculationBaseRoyaltie",
        "transform": "Direto.",
    },
}

# Gaps reais — campos ABF que NAO tem destino no DB atual
GAPS = [
    {
        "abf_field": "abf_updated_at",
        "abf_type": "string (DD/MM/YYYY)",
        "where": "Franchise (top-level)",
        "proposed_col": "abfUpdatedAt",
        "proposed_type": "DATE",
        "rationale": "Rastreabilidade de quando associado atualizou ficha na ABF. Diferente de lastScrapedAt (que e quando NOSSO scraper rodou).",
    },
    {
        "abf_field": "(meta) dataSource",
        "abf_type": "string ('abf-portaldofranchising')",
        "where": "Franchise (novo)",
        "proposed_col": "dataSource",
        "proposed_type": "VARCHAR(50)",
        "rationale": "Diferenciar origem dos dados (manual, claimed, abf-portaldofranchising, encontresua-franquia, etc.). Permite politica de UPSERT diferenciada.",
    },
    {
        "abf_field": "business_models[].headquarter",
        "abf_type": "string",
        "where": "BusinessModel",
        "proposed_col": "headquarter",
        "proposed_type": "VARCHAR(191)",
        "rationale": "ABF traz HQ por modelo (pode diferir entre Quiosque vs Loja). DB BM nao tem.",
    },
    {
        "abf_field": "business_models[].total_units",
        "abf_type": "integer",
        "where": "BusinessModel",
        "proposed_col": "totalUnits",
        "proposed_type": "INTEGER",
        "rationale": "ABF traz total por modelo (Quiosque tem 52, Loja tem 4656). DB BM nao tem.",
    },
    {
        "abf_field": "business_models[].advertising_fee_observation",
        "abf_type": "string ou null",
        "where": "BusinessModel",
        "proposed_col": "advertisingFeeObservation",
        "proposed_type": "TEXT",
        "rationale": "Texto livre que ABF traz junto da fee. Hoje nao tem destino.",
    },
    {
        "abf_field": "business_models[].royalties_observation",
        "abf_type": "string ou null",
        "where": "BusinessModel",
        "proposed_col": "royaltiesObservation",
        "proposed_type": "TEXT",
        "rationale": "Idem.",
    },
    {
        "abf_field": "(impl) BusinessModel.description",
        "abf_type": "n/a",
        "where": "BusinessModel — campo EXISTENTE",
        "proposed_col": "description",
        "proposed_type": "ALTER NOT NULL -> NULL",
        "rationale": "Hoje description e NOT NULL. Scraper nao tem description por modelo. Bloquea inserts via scraper. Decidir: alter pra nullable OU placeholder vazio.",
    },
    {
        "abf_field": "(impl) BusinessModel.photoUrl",
        "abf_type": "n/a",
        "where": "BusinessModel — campo EXISTENTE",
        "proposed_col": "photoUrl",
        "proposed_type": "ALTER NOT NULL -> NULL",
        "rationale": "Hoje photoUrl e NOT NULL. Scraper nao tem photoUrl por modelo. Mesmo bloqueio. Decidir igual a description.",
    },
]

# Campos do DB sem correspondencia ABF (so pra contexto)
DB_ONLY_FRANCHISE = [
    "id",
    "sku",
    "createdAt",
    "updatedAt",
    "contactId",
    "ownerId",
    "isActive",
    "isReview",
    "averageRating",
    "ratingSum",
    "reviewCount",
    "favoritesCount",
    "isSponsored",
    "sponsorPlacements",
    "tagline",
    "differentials",
    "idealFranchiseeProfile",
    "processSteps",
    "testimonials",
    "phone",
    "whatsapp",
    "publicEmail",
    "instagramUrl",
    "facebookUrl",
    "linkedinUrl",
    "totalUnitsUpdatedAt",
    "totalUnitsLastConfirmedAt",
    "averageMonthlyRevenue",
    "minimumReturnOnInvestment",  # Franchise level — ABF traz por BM
    "maximumReturnOnInvestment",
    "videoUrl",
    "thumbnailUrl",
    "bannerUrl",
    "businessType",
    "isAbfAssociated",  # ja existe boolean — scraper pode marcar TRUE
    "abfSince",  # ja existe integer — scraper pode preencher se vier no JSON
    "subsegment",
    "headquarterState",  # ABF tem so headquarter (livre)
    "totalUnitsInBrazil",
    "unitsEvolution",
    "franchiseStartYear",
    "brandFoundationYear",
    "status",
]


# ============================================================================
# Carrega samples ABF
# ============================================================================
def load_parsed_jsons() -> list[dict[str, Any]]:
    """Carrega todos os JSONs parseados."""
    out = []
    for p in sorted(PARSED_DIR.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception as e:
            print(f"  WARN: skip {p.name}: {e}")
    return out


def field_presence_stats(samples: list[dict[str, Any]]) -> dict[str, int]:
    """Conta quantos JSONs tem cada field nao-null/nao-vazio."""
    counter: Counter = Counter()
    total = len(samples)
    for s in samples:
        for k, v in s.items():
            if v is None or v == "" or v == [] or v == {}:
                continue
            counter[k] += 1
        # business_models nested
        for bm in s.get("business_models") or []:
            for k, v in bm.items():
                if v is None or v == "" or v == [] or v == {}:
                    continue
                counter[f"business_models[].{k}"] += 1
    return dict(counter), total


# ============================================================================
# Outputs
# ============================================================================
def write_schema_json(franchise_cols, bm_cols):
    out = {
        "Franchise": franchise_cols,
        "BusinessModel": bm_cols,
    }
    (OUTPUT_DIR / "schema_current.json").write_text(json.dumps(out, indent=2))
    print(f"  -> output/schema_current.json ({len(franchise_cols)} + {len(bm_cols)} colunas)")


def write_gap_report(franchise_cols, bm_cols, samples, presence, total_samples):
    franchise_col_names = {c["name"] for c in franchise_cols}
    bm_col_names = {c["name"] for c in bm_cols}

    lines = []
    lines.append("# Gap Analysis — ABF Scraper × Schema Mercado Franquia")
    lines.append("")
    lines.append(f"**Total de fichas ABF analisadas:** {total_samples}")
    lines.append(f"**Schema versao:** Alembic head 9e73d144e686 (sincronizado prod+local)")
    lines.append(f"**Franchise:** {len(franchise_cols)} colunas")
    lines.append(f"**BusinessModel:** {len(bm_cols)} colunas")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ====== Secao 1: Mapeamentos diretos ======
    lines.append("## 1. Mapeamentos diretos (ABF -> DB, 1:1)")
    lines.append("")
    lines.append(
        "Campos onde tipo e semantica casam. UPSERT pode rodar sem transformacao."
    )
    lines.append("")
    lines.append("### 1a. ABF top-level -> Franchise")
    lines.append("")
    lines.append("| ABF field | Franchise col | Presenca em ABF | Existe no DB |")
    lines.append("|---|---|---|---|")
    for abf, db in DIRECT_FRANCHISE.items():
        n = presence.get(abf, 0)
        pct = f"{n}/{total_samples} ({n*100//total_samples if total_samples else 0}%)"
        exists = "OK" if db in franchise_col_names else "FALTA"
        lines.append(f"| `{abf}` | `{db}` | {pct} | {exists} |")
    lines.append("")
    lines.append("### 1b. ABF business_models[] -> BusinessModel")
    lines.append("")
    lines.append("| ABF field | BusinessModel col | Presenca | Existe |")
    lines.append("|---|---|---|---|")
    for abf, db in DIRECT_BUSINESS_MODEL.items():
        n = presence.get(f"business_models[].{abf}", 0)
        pct = f"{n}/{total_samples} ({n*100//total_samples if total_samples else 0}%)"
        exists = "OK" if db in bm_col_names else "FALTA"
        lines.append(f"| `{abf}` | `{db}` | {pct} | {exists} |")
    lines.append("")

    # ====== Secao 2: Mapeamentos semanticos ======
    lines.append("---")
    lines.append("")
    lines.append("## 2. Mapeamentos semanticos (precisam transformacao)")
    lines.append("")
    lines.append("Campos onde dado existe nos 2 lados mas formato/tipagem divergem.")
    lines.append("")
    lines.append("### 2a. Franchise")
    lines.append("")
    for abf, info in SEMANTIC_FRANCHISE.items():
        n = presence.get(abf, 0)
        pct = f"{n}/{total_samples}"
        lines.append(f"- **`{abf}`** ({pct}) -> `{info['db_col']}`")
        lines.append(f"  - {info['transform']}")
    lines.append("")
    lines.append("### 2b. BusinessModel")
    lines.append("")
    for abf, info in SEMANTIC_BUSINESS_MODEL.items():
        # ABF business_models[].field — usa primeira parte do _min/_max
        base_field = abf.split("_min/_max")[0].split("/")[0]
        n = presence.get(f"business_models[].{base_field}", 0)
        n_min = presence.get(f"business_models[].{base_field}_min", 0)
        n_count = max(n, n_min)
        pct = f"{n_count}/{total_samples}"
        lines.append(f"- **`{abf}`** ({pct}) -> `{info['db_col']}`")
        lines.append(f"  - {info['transform']}")
    lines.append("")

    # ====== Secao 3: Gaps reais ======
    lines.append("---")
    lines.append("")
    lines.append("## 3. Gaps reais (ABF tem, DB nao tem)")
    lines.append("")
    lines.append("Cada gap propoe coluna nova OU alteracao. Migration vira da soma dessas decisoes.")
    lines.append("")
    lines.append("| ABF field | Onde vai | Coluna proposta | Tipo proposto | Justificativa |")
    lines.append("|---|---|---|---|---|")
    for g in GAPS:
        lines.append(
            f"| `{g['abf_field']}` | {g['where']} | `{g['proposed_col']}` | `{g['proposed_type']}` | {g['rationale']} |"
        )
    lines.append("")

    # ====== Secao 4: DB only ======
    lines.append("---")
    lines.append("")
    lines.append("## 4. Campos DB sem correspondencia ABF")
    lines.append("")
    lines.append(
        "Sem acao — esses ficam como estao. ABF nao trara dados pra eles via enrichment."
    )
    lines.append("")
    lines.append("### 4a. Franchise")
    lines.append("")
    for c in sorted(DB_ONLY_FRANCHISE):
        col = next((cc for cc in franchise_cols if cc["name"] == c), None)
        if col:
            lines.append(f"- `{c}` ({col['type']})")
    lines.append("")
    lines.append("### 4b. BusinessModel — todas as colunas (alem das mapeadas) ficam intactas via scraper")
    lines.append("")

    # ====== Secao 5: 6 perguntas editoriais ======
    lines.append("---")
    lines.append("")
    lines.append("## 5. Decisoes editoriais pendentes (6 perguntas pro Breno)")
    lines.append("")
    lines.append(
        "**Importante:** nao abrir migration nem rodar enrichment_diff antes de receber resposta a essas."
    )
    lines.append("")
    lines.append(
        "1. **Politica de UPSERT por campo.** Pra cada campo do scraper, qual estrategia?"
    )
    lines.append("   - (A) Scraper e fonte de verdade (sempre sobrescreve)")
    lines.append("   - (B) Scraper preenche so se DB esta NULL")
    lines.append("   - (C) Scraper descartado se DB tem qualquer valor")
    lines.append("   - (D) Caso a caso (ver exemplos)")
    lines.append("")
    lines.append(
        "   *Sugestao default: (B), exceto pra `abfUpdatedAt`, `lastScrapedAt`, `dataSource` que sao (A) sempre.*"
    )
    lines.append("")
    lines.append(
        "2. **BusinessModel.description e photoUrl sao NOT NULL.** Como tratar?"
    )
    lines.append(
        "   - (i) Migration ALTER pra nullable em ambos. Permite criar BM via scraper sem placeholder."
    )
    lines.append(
        "   - (ii) Scraper preenche `description = ''` e `photoUrl = ''` (placeholder vazio)."
    )
    lines.append(
        "   - (iii) Skip BusinessModel inteiro nesta fatia — popular so Franchise. BM via scraper fica pra fatia futura."
    )
    lines.append("")
    lines.append(
        "3. **Modelagem de ranges (`_min`/`_max`).** Hoje BusinessModel tem singles (`investment`, `payback`, `franchiseFee`, etc.). ABF traz range. O que fazer?"
    )
    lines.append("   - (i) Usar `_min` como valor unico, descartar `_max` (perda de informacao)")
    lines.append(
        "   - (ii) Migration: trocar single col -> 2 cols `_min`/`_max` em todos os 6 campos afetados (mais correto, custo: migration grande)"
    )
    lines.append(
        "   - (iii) Manter single + nova string `range` pra exibicao (gambiarra)"
    )
    lines.append("")
    lines.append(
        "4. **Royalties/propaganda com `rate` textual ('VARIAVEL') + `observation`.** ABF traz `royalties_rate=\"VARIAVEL\"`, `royalties_base=\"Compras\"`, `royalties_observation=null`. DB tem `royalties NUMERIC` + `calculationBaseRoyaltie VARCHAR`. O que fazer com rate textual e observation?"
    )
    lines.append(
        "   - (i) Criar colunas `royaltiesObservation TEXT` e mudar `royalties` pra texto livre"
    )
    lines.append(
        "   - (ii) Manter `royalties NUMERIC` (parser tenta extrair numero, descarta se nao consegue) + nova `royaltiesObservation TEXT`"
    )
    lines.append(
        "   - (iii) Concatenar tudo em `description` (gambiarra, perde tipagem)"
    )
    lines.append("")
    lines.append(
        "5. **Pacote de rastreabilidade.** Adicionar 3 colunas novas em Franchise: `abfUpdatedAt DATE`, `dataSource VARCHAR(50)`, `lastScrapedAt` ja existe. OK juntar tudo numa migration?"
    )
    lines.append(
        "   - (i) Sim — migration `abf_traceability` com 2 ALTER ADD COLUMN (`abfUpdatedAt`, `dataSource`)"
    )
    lines.append(
        "   - (ii) So `dataSource` agora; `abfUpdatedAt` deferido pra fatia ABF mais madura"
    )
    lines.append("")
    lines.append("6. **Imagens — onde sincar e como nomear no DB?**")
    lines.append(
        "   - Path EC2 proposto: `/home/ubuntu/mercadofranquia-uploads/abf/{slug}/`"
    )
    lines.append(
        "   - URL publica: `https://mercadofranquia.com.br/uploads/abf/{slug}/...`"
    )
    lines.append(
        "   - DB salva URL absoluta OU path relativo `/uploads/abf/{slug}/logo.jpg`?"
    )
    lines.append(
        "   *Sugerido: path relativo (segue padrao de `logoUrl` atual em `/uploads/...`).*"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Estatisticas dos 191 JSONs")
    lines.append("")
    lines.append("Top 25 campos por presenca (descartando null/empty):")
    lines.append("")
    lines.append("| Campo | Presenca |")
    lines.append("|---|---|")
    for k, v in sorted(presence.items(), key=lambda x: -x[1])[:25]:
        lines.append(f"| `{k}` | {v}/{total_samples} ({v*100//total_samples}%) |")
    lines.append("")

    (OUTPUT_DIR / "gap_report.md").write_text("\n".join(lines))
    print(f"  -> output/gap_report.md ({len(lines)} linhas)")


def write_proposed_migration(franchise_cols, bm_cols):
    """DDL Alembic-style — so as colunas claramente novas (gaps reais).

    NAO inclui ALTER de NOT NULL -> NULL nem mudanca de single -> _min/_max
    porque essas dependem das decisoes editoriais.
    """
    franchise_col_names = {c["name"] for c in franchise_cols}
    bm_col_names = {c["name"] for c in bm_cols}

    lines = []
    lines.append("-- Proposed migration — Fatia ABF enrichment")
    lines.append("-- Apenas colunas claramente novas (gaps reais, nao-controversos).")
    lines.append("-- Decisoes pendentes (ranges, NOT NULL alters) NAO estao aqui.")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")
    lines.append("-- 1. Rastreabilidade ABF na Franchise")
    if "abfUpdatedAt" not in franchise_col_names:
        lines.append('ALTER TABLE "Franchise" ADD COLUMN "abfUpdatedAt" DATE;')
    if "dataSource" not in franchise_col_names:
        lines.append(
            "ALTER TABLE \"Franchise\" ADD COLUMN \"dataSource\" VARCHAR(50);"
        )
    lines.append("")
    lines.append("-- 2. BusinessModel — gaps confirmados")
    if "headquarter" not in bm_col_names:
        lines.append(
            "ALTER TABLE \"BusinessModel\" ADD COLUMN \"headquarter\" VARCHAR(191);"
        )
    if "totalUnits" not in bm_col_names:
        lines.append(
            "ALTER TABLE \"BusinessModel\" ADD COLUMN \"totalUnits\" INTEGER;"
        )
    if "advertisingFeeObservation" not in bm_col_names:
        lines.append(
            'ALTER TABLE "BusinessModel" ADD COLUMN "advertisingFeeObservation" TEXT;'
        )
    if "royaltiesObservation" not in bm_col_names:
        lines.append(
            'ALTER TABLE "BusinessModel" ADD COLUMN "royaltiesObservation" TEXT;'
        )
    lines.append("")
    lines.append("COMMIT;")
    lines.append("")
    lines.append("-- 3. NAO incluido — depende de decisao editorial:")
    lines.append("--   - ALTER BusinessModel.description SET NULL (decisao 2)")
    lines.append("--   - ALTER BusinessModel.photoUrl SET NULL (decisao 2)")
    lines.append("--   - Migration de ranges _min/_max (decisao 3)")
    lines.append("--   - royalties: NUMERIC -> TEXT (decisao 4)")

    (OUTPUT_DIR / "proposed_migration.sql").write_text("\n".join(lines))
    print(f"  -> output/proposed_migration.sql ({len(lines)} linhas)")


# ============================================================================
# Main
# ============================================================================
def main():
    print("=== Gap Analysis ABF Scraper x Mercado Franquia ===\n")

    print("[1/4] Schema introspection...")
    franchise_cols = fetch_schema("Franchise")
    bm_cols = fetch_schema("BusinessModel")
    print(f"  Franchise: {len(franchise_cols)} colunas")
    print(f"  BusinessModel: {len(bm_cols)} colunas")

    print("\n[2/4] Loading parsed JSONs...")
    samples = load_parsed_jsons()
    print(f"  Loaded {len(samples)} fichas")

    print("\n[3/4] Field presence stats...")
    presence, total = field_presence_stats(samples)
    print(f"  {len(presence)} fields distinct")

    print("\n[4/4] Writing outputs...")
    write_schema_json(franchise_cols, bm_cols)
    write_gap_report(franchise_cols, bm_cols, samples, presence, total)
    write_proposed_migration(franchise_cols, bm_cols)

    print("\nOK. Veja output/gap_report.md\n")


if __name__ == "__main__":
    main()
