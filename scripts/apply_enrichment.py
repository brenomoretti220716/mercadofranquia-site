#!/usr/bin/env python3
"""Apply enrichment ABF -> Mercado Franquia DB.

Cruza 191 fichas ABF parseadas com franquias do DB. Pra cada ficha:
  1. Tenta match contra Franchise existente (3 estrategias: slug, nome, fuzzy)
  2. Se match e franquia esta REIVINDICADA (ownerId IS NOT NULL OU
     dataSource IN ('manual','claimed')) -> SKIP TOTAL.
  3. Se match e nao-reivindicada -> UPDATE so campos NULL + always-update
     pra abfUpdatedAt/lastScrapedAt/dataSource.
  4. Se nao tem match -> INSERT nova Franchise com dataSource='abf-portaldofranchising'.

DRY-RUN por padrao — gera enrichment_diff.json + summary.txt SEM tocar DB.
--apply executa os UPSERTs reais (usa transacao por franquia).
--limit N processa so as primeiras N fichas (debug / smoke).

Politica de UPSERT (consolidada das 6 perguntas editoriais):
  - Por FRANQUIA: skip total se reivindicada (nao toca em campo, imagem,
    BusinessModel, nada).
  - Para nao-reivindicadas:
    - Campos com valor no DB: NAO sobrescreve (preserva trabalho anterior).
    - Campos NULL no DB: scraper preenche.
    - dataSource: set apenas em INSERTs ou rows com dataSource IS NULL.
    - abfUpdatedAt e lastScrapedAt: sempre atualiza (sao fatos).

BusinessModel:
  - Pra cada franquia (matched OU created), insere os business_models do
    ABF apenas se a franquia atual tem 0 BMs no DB. Se ja tem qualquer
    BM, pula (preserva trabalho anterior + idempotencia em re-execucao).
  - Campos NULL no INSERT pra description e photoUrl (migration tornou
    nullable). Frontend deve ter fallback.

Uso:
    .venv/bin/python scripts/apply_enrichment.py --limit 10            # smoke
    .venv/bin/python scripts/apply_enrichment.py                       # dry-run completo
    .venv/bin/python scripts/apply_enrichment.py --apply               # execucao real
"""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
import uuid
from datetime import datetime, date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import create_engine, text


# ============================================================================
# Paths + config
# ============================================================================
SCRAPER_ROOT = Path(__file__).resolve().parent / "abf_scraper"
PARSED_DIR = SCRAPER_ROOT / "output" / "parsed"
OUTPUT_DIR = SCRAPER_ROOT / "output"

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://mf_user:dev_password_local@localhost:5432/mercadofranquia"
)


# ============================================================================
# Normalizacao + matching
# ============================================================================
def normalize_for_match(s: Optional[str]) -> str:
    """lowercase + strip accents + alphanumeric only. Para fuzzy match."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def normalize_abf_slug(slug: str) -> str:
    """ABF slugs vem como 'franquia-cacau-show-valor'. DB tem 'cacau-show'.

    Strip prefix 'franquia-' e suffixes comuns ('-valor', '-oportunidade',
    '-oportunidades', '-investimento'). Apos isso, normalize_for_match
    pra comparar.
    """
    s = slug.lower()
    s = re.sub(r"^franquia[-_]", "", s)
    s = re.sub(r"[-_](valor|oportunidades?|investimento)$", "", s)
    return s


def find_match(
    abf: dict, db_franchises: list[dict]
) -> tuple[Optional[dict], float, str]:
    """Encontra melhor match no DB. Retorna (db_franchise|None, score, strategy)."""
    abf_slug_norm = normalize_for_match(normalize_abf_slug(abf["slug"]))
    abf_name_norm = normalize_for_match(abf["name"])

    # 1. Slug exact (apos normalize)
    for db in db_franchises:
        if db.get("slug") and normalize_for_match(db["slug"]) == abf_slug_norm:
            return (db, 1.0, "slug_exact")

    # 2. Name exact (apos normalize)
    for db in db_franchises:
        if db.get("name") and normalize_for_match(db["name"]) == abf_name_norm:
            return (db, 0.95, "name_exact")

    # 3. Fuzzy ratio em nome (threshold 0.85 — conservador pra evitar false
    # positives. Validado em smoke contra prod-snapshot 1404 franquias:
    # zero matches caem na faixa 0.85-0.94, entao 0.85 nao perde matches reais
    # e elimina os falsos positivos da faixa 0.75-0.84 [Blow→flow, etc])
    best, best_score = None, 0.0
    for db in db_franchises:
        if not db.get("name"):
            continue
        score = SequenceMatcher(
            None, abf_name_norm, normalize_for_match(db["name"])
        ).ratio()
        if score > best_score:
            best_score = score
            best = db

    if best_score >= 0.85:
        return (best, round(best_score, 3), "fuzzy_name")

    return (None, 0.0, "no_match")


# ============================================================================
# Parsers
# ============================================================================
def parse_numeric(val: Any) -> tuple[Optional[float], Optional[str]]:
    """Tenta extrair numero de string. Retorna (numero|None, observation|None).

    >>> parse_numeric("5%")
    (5.0, None)
    >>> parse_numeric("5,5%")
    (5.5, None)
    >>> parse_numeric("VARIAVEL")
    (None, 'VARIAVEL')
    >>> parse_numeric(None)
    (None, None)
    >>> parse_numeric("Variavel ate 5%")
    (5.0, 'Variavel ate 5%')
    """
    if val is None:
        return (None, None)
    s = str(val).strip()
    if not s:
        return (None, None)

    m = re.search(r"(\d+(?:[.,]\d+)?)", s)
    if not m:
        return (None, s)

    num = float(m.group(1).replace(",", "."))
    # Se string e' so o numero (eventualmente com %) -> sem observation
    clean = re.sub(r"[\s%]", "", s)
    if clean == m.group(1).replace(",", "."):
        return (num, None)
    return (num, s)


def normalize_rate(
    rate_raw: Any, base_raw: Any, max_pct: float
) -> tuple[Optional[float], Optional[str]]:
    """Normaliza taxa percentual (royalties ou advertising) com sanity check.

    Retorna (numero|None, observation|None):
    - Se rate/base contem "fixo", "r$", "reais" -> retorna (None, rate_raw)
      e o numero fica fora do NUMERIC pra evitar corrupcao silenciosa.
    - Se parse_numeric falha -> (None, rate_raw) — texto livre tipo "VARIAVEL".
    - Se valor extraido cai fora de [0, max_pct] -> (None, rate_raw) —
      sanity check, % acima desse limite e' quase certeza valor fixo
      mal-rotulado (royalties historicamente 0-30%, ad fee 0-10%).
    - Caso contrario -> (numero, observation_se_houver_texto_extra).

    max_pct: 30 pra royalties, 10 pra advertisingFee (limites empiricos do
    franchising brasileiro).
    """
    rate_str = str(rate_raw).strip() if rate_raw is not None else ""
    base_str = str(base_raw).strip() if base_raw is not None else ""

    if not rate_str and not base_str:
        return (None, None)

    # Sinal explicito de valor fixo (R$, "reais", "fixo")
    combined_lower = (rate_str + " " + base_str).lower()
    is_fixed = any(
        kw in combined_lower for kw in ("fixo", "r$", "reais")
    )
    if is_fixed:
        return (None, rate_str or None)

    # Tenta extrair numero (parse_numeric ja existe pra outros usos)
    num, obs_from_parser = parse_numeric(rate_str)
    if num is None:
        # Texto livre tipo "VARIAVEL" ou vazio
        return (None, rate_str or None)

    # Sanity check: % deve estar na faixa esperada
    if num < 0 or num > max_pct:
        return (None, rate_str)

    # Numero valido. Se rate tem texto alem do numero (ex: "5% sobre faturamento"),
    # mantem texto bruto em observation pra contexto.
    return (num, obs_from_parser)


def parse_date_br(s: Optional[str]) -> Optional[date]:
    """Parse 'DD/MM/YYYY' -> date. Retorna None em qualquer falha."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def parse_iso_datetime(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime do scraper (e.g. '2026-04-29T11:18:08Z')."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


# ============================================================================
# Skip-claimed
# ============================================================================
def is_claimed(db_franchise: dict) -> bool:
    """Retorna True se franquia esta reivindicada — scraper deve pular total."""
    if db_franchise.get("ownerId") is not None:
        return True
    if db_franchise.get("dataSource") in ("manual", "claimed"):
        return True
    return False


# ============================================================================
# Diff computation
# ============================================================================
# Mapeamento direto ABF -> Franchise (1:1, sem transformacao)
DIRECT_FRANCHISE = [
    ("name", "name"),
    ("scraped_website", "scrapedWebsite"),
    ("logo_url", "logoUrl"),
    ("minimum_investment", "minimumInvestment"),
    ("maximum_investment", "maximumInvestment"),
    ("total_units", "totalUnits"),
    ("headquarter", "headquarter"),
]


def compute_diff_update(abf: dict, db: dict) -> dict[str, dict]:
    """Diff pra UPDATE de Franchise existente nao-reivindicada.

    So preenche fields onde DB esta NULL. Excecoes (sempre-atualiza):
    abfUpdatedAt, lastScrapedAt. dataSource so se NULL.
    """
    diff: dict[str, dict] = {}

    # Direct fields — preencher so se DB NULL
    for abf_key, db_key in DIRECT_FRANCHISE:
        abf_val = abf.get(abf_key)
        if abf_val is None or abf_val == "":
            continue
        if db.get(db_key) is None:
            diff[db_key] = {
                "db_current": None,
                "abf_value": abf_val,
                "action": "set_if_null",
            }

    # gallery_urls (list -> JSON string)
    abf_gallery = abf.get("gallery_urls") or []
    if abf_gallery and not db.get("galleryUrls"):
        diff["galleryUrls"] = {
            "db_current": None,
            "abf_value": json.dumps(abf_gallery),
            "action": "set_if_null",
        }

    # description — meta_description ABF, so se DB NULL
    abf_desc = abf.get("meta_description")
    if abf_desc and not db.get("description"):
        diff["description"] = {
            "db_current": None,
            "abf_value": abf_desc,
            "action": "set_if_null",
        }

    # Always-update fields
    abf_updated = parse_date_br(abf.get("abf_updated_at"))
    if abf_updated:
        diff["abfUpdatedAt"] = {
            "db_current": str(db.get("abfUpdatedAt"))
            if db.get("abfUpdatedAt")
            else None,
            "abf_value": abf_updated.isoformat(),
            "action": "set_always",
        }

    abf_scraped = parse_iso_datetime(abf.get("scraped_at"))
    if abf_scraped:
        diff["lastScrapedAt"] = {
            "db_current": str(db.get("lastScrapedAt"))
            if db.get("lastScrapedAt")
            else None,
            "abf_value": abf_scraped.isoformat(),
            "action": "set_always",
        }

    # dataSource — set so se NULL (politica: nao sobrescreve)
    if db.get("dataSource") is None:
        diff["dataSource"] = {
            "db_current": None,
            "abf_value": "abf-portaldofranchising",
            "action": "set_if_null",
        }

    return diff


def build_business_model_payload(
    bm: dict, franchise_id: str
) -> dict[str, Any]:
    """Constroi payload pra INSERT de 1 BusinessModel a partir do JSON ABF.

    Politica de ranges: usa _min como valor unico (decisao 3 do gap analysis,
    _max descartado nesta fatia). Politica de royalties/advertising: parser
    tenta extrair numero do .._rate; se falha, fica NULL e o texto vai pra
    ..Observation.
    """
    # Normaliza royalties com sanity range 0-30%
    royalties_num, royalties_obs = normalize_rate(
        bm.get("royalties_rate"), bm.get("royalties_base"), max_pct=30
    )
    # Normaliza advertising fee com sanity range 0-10%
    ad_num, ad_obs = normalize_rate(
        bm.get("advertising_fee_rate"),
        bm.get("advertising_fee_base"),
        max_pct=10,
    )

    # Se ABF traz uma 'observation' propria, mescla com texto bruto do rate
    royalties_obs_extra = bm.get("royalties_observation")
    if royalties_obs_extra:
        royalties_obs = (
            f"{royalties_obs} ({royalties_obs_extra})"
            if royalties_obs
            else royalties_obs_extra
        )
    ad_obs_extra = bm.get("advertising_fee_observation")
    if ad_obs_extra:
        ad_obs = f"{ad_obs} ({ad_obs_extra})" if ad_obs else ad_obs_extra

    area_min = bm.get("area_m2_min")

    return {
        "id": uuid.uuid4().hex,
        "name": bm.get("name") or "Modelo",
        "description": None,  # nullable apos migration; franqueador preenche no claim
        "photoUrl": None,  # idem
        "franchiseId": franchise_id,
        "franchiseFee": bm.get("franchise_fee_min"),
        "royalties": royalties_num,
        "royaltiesObservation": royalties_obs,
        "advertisingFee": ad_num,
        "advertisingFeeObservation": ad_obs,
        "workingCapital": bm.get("working_capital_min"),
        "setupCapital": bm.get("capital_installation_min"),
        "averageMonthlyRevenue": None,  # ABF nao traz por modelo
        "storeArea": int(area_min) if area_min is not None else None,
        "calculationBaseRoyaltie": bm.get("royalties_base"),
        "calculationBaseAdFee": bm.get("advertising_fee_base"),
        "investment": bm.get("investment_total_min"),
        "payback": bm.get("payback_months_min"),
        "profitability": None,  # ABF nao traz
        "headquarter": bm.get("headquarter"),
        "totalUnits": bm.get("total_units"),
    }


def compute_diff_insert(abf: dict) -> dict[str, Any]:
    """Diff pra INSERT de Franchise nova (sem match no DB)."""
    return {
        "name": abf["name"],
        "slug": normalize_abf_slug(abf["slug"]),
        "scrapedWebsite": abf.get("scraped_website"),
        "logoUrl": abf.get("logo_url"),
        "minimumInvestment": abf.get("minimum_investment"),
        "maximumInvestment": abf.get("maximum_investment"),
        "totalUnits": abf.get("total_units"),
        "headquarter": abf.get("headquarter"),
        "galleryUrls": json.dumps(abf.get("gallery_urls") or []),
        "description": abf.get("meta_description"),
        "abfUpdatedAt": parse_date_br(abf.get("abf_updated_at")),
        "lastScrapedAt": parse_iso_datetime(abf.get("scraped_at")),
        "dataSource": "abf-portaldofranchising",
        "isAbfAssociated": True,
    }


# ============================================================================
# DB IO
# ============================================================================
def load_db_franchises(engine) -> list[dict]:
    sql = text(
        """
        SELECT id, slug, name, "ownerId", "dataSource",
               description, "logoUrl", "scrapedWebsite", "lastScrapedAt",
               "minimumInvestment", "maximumInvestment", "totalUnits",
               headquarter, "headquarterState", "galleryUrls",
               "isAbfAssociated", "abfUpdatedAt"
        FROM "Franchise"
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
    return [dict(r._mapping) for r in rows]


def load_business_model_counts(engine) -> dict[str, int]:
    """Retorna {franchiseId: count} pra todos os BMs existentes."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                'SELECT "franchiseId", COUNT(*) AS n FROM "BusinessModel" '
                'GROUP BY "franchiseId"'
            )
        ).all()
    return {r._mapping["franchiseId"]: r._mapping["n"] for r in rows}


def apply_update(engine, db_id: str, diff: dict) -> None:
    """Aplica UPDATE em uma Franchise. Caller controla transacao externa."""
    if not diff:
        return
    sets = []
    params: dict[str, Any] = {"id": db_id}
    for col, info in diff.items():
        sets.append(f'"{col}" = :p_{col}')
        params[f"p_{col}"] = info["abf_value"]
    sql = text(
        f'UPDATE "Franchise" SET {", ".join(sets)}, "updatedAt" = NOW() WHERE id = :id'
    )
    with engine.begin() as conn:
        conn.execute(sql, params)


def apply_insert_business_model(engine, payload: dict) -> None:
    """Insert 1 BusinessModel. Caller controla transacao."""
    cols = list(payload.keys())
    placeholders = [f":p_{c}" for c in cols]
    quoted = ", ".join(f'"{c}"' for c in cols)
    params = {f"p_{c}": v for c, v in payload.items()}
    sql = text(
        f"""
        INSERT INTO "BusinessModel" ({quoted}, "createdAt", "updatedAt")
        VALUES ({", ".join(placeholders)}, NOW(), NOW())
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, params)


def apply_insert(engine, payload: dict) -> str:
    """Insere Franchise nova. Retorna o id gerado."""
    new_id = uuid.uuid4().hex  # 32 chars, cabe em VARCHAR(191)
    payload = dict(payload)
    payload["id"] = new_id
    cols = list(payload.keys())
    placeholders = [f":p_{c}" for c in cols]
    quoted = ", ".join(f'"{c}"' for c in cols)
    params = {f"p_{c}": v for c, v in payload.items()}
    # Defaults exigidos pelo schema
    sql = text(
        f"""
        INSERT INTO "Franchise" ({quoted}, "isActive", "isReview",
                                  "favoritesCount", "isSponsored",
                                  "sponsorPlacements", "ratingSum",
                                  "reviewCount", status, "createdAt",
                                  "updatedAt")
        VALUES ({", ".join(placeholders)}, true, true,
                0, false, '{{}}'::jsonb, 0, 0, 'APPROVED',
                NOW(), NOW())
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, params)
    return new_id


# ============================================================================
# Reporters
# ============================================================================
def write_summary(summary: dict, mode: str) -> str:
    lines = []
    lines.append("=== Enrichment Diff Summary ===")
    lines.append(f"Mode: {mode}")
    lines.append("")
    lines.append(f"Total ABF processed: {summary['total_abf']}")
    lines.append(f"  Matched in DB:      {summary['matched']}")
    lines.append(f"    -> skipped_claimed: {summary['skipped_claimed']}")
    lines.append(f"    -> will_enrich:     {summary['will_enrich']}")
    lines.append(f"  No match:           {summary['will_create']} (will_create)")
    lines.append("")
    lines.append("Score distribution:")
    for bucket, n in summary["score_distribution"].items():
        lines.append(f"  {bucket}: {n}")
    lines.append("")
    lines.append("BusinessModels:")
    lines.append(
        f"  Will insert:      {summary['business_models_to_insert']}"
    )
    lines.append(
        f"  Skipped (DB ja tem): {summary['business_models_skipped_existing']}"
    )
    lines.append("")
    if summary.get("applied"):
        lines.append(f"APPLIED to DB:")
        lines.append(f"  Franchise UPDATE:    {summary['applied']['updates']}")
        lines.append(f"  Franchise INSERT:    {summary['applied']['inserts']}")
        lines.append(
            f"  BusinessModel INSERT: {summary['applied']['bm_inserts']}"
        )
        if summary["applied"].get("errors"):
            lines.append(f"  Errors:           {len(summary['applied']['errors'])}")
            for e in summary["applied"]["errors"][:5]:
                lines.append(f"    - {e}")
    lines.append("")
    lines.append("Outputs:")
    lines.append("  output/enrichment_diff.json")
    lines.append("  output/enrichment_summary.txt")
    if mode == "DRY-RUN":
        lines.append("")
        lines.append("Re-run with --apply to mutate DB.")
    return "\n".join(lines)


# ============================================================================
# Main
# ============================================================================
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Processar so as primeiras N fichas (debug/smoke).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Executa UPSERTs reais. Default: dry-run (so gera diff).",
    )
    p.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Connection string. Default usa DATABASE_URL env ou local dev.",
    )
    args = p.parse_args()

    is_dry_run = not args.apply
    mode = "DRY-RUN" if is_dry_run else "APPLY"
    print(f"=== apply_enrichment.py — Mode: {mode} ===\n")
    if args.limit:
        print(f"Limit: {args.limit} fichas\n")

    engine = create_engine(args.database_url)

    # 1. Load
    print("[1/3] Loading...")
    abf_samples = sorted(
        [json.loads(p.read_text()) for p in PARSED_DIR.glob("*.json")],
        key=lambda x: x.get("slug", ""),
    )
    if args.limit:
        abf_samples = abf_samples[: args.limit]
    db_franchises = load_db_franchises(engine)
    bm_counts = load_business_model_counts(engine)
    print(f"  ABF: {len(abf_samples)} fichas")
    print(f"  DB:  {len(db_franchises)} franquias, "
          f"{sum(bm_counts.values())} BusinessModels")

    # 2. Match + diff
    print("\n[2/3] Matching + diff...")
    items = []
    summary = {
        "total_abf": len(abf_samples),
        "matched": 0,
        "skipped_claimed": 0,
        "will_enrich": 0,
        "will_create": 0,
        "business_models_to_insert": 0,
        "business_models_skipped_existing": 0,
        "score_distribution": {
            "1.00": 0,
            "0.95": 0,
            "0.85-0.94": 0,
            "0.75-0.84": 0,
            "no_match": 0,
        },
    }

    for abf in abf_samples:
        db_match, score, strategy = find_match(abf, db_franchises)

        # Bucket
        if score == 0:
            summary["score_distribution"]["no_match"] += 1
        elif score >= 1.0:
            summary["score_distribution"]["1.00"] += 1
        elif score >= 0.95:
            summary["score_distribution"]["0.95"] += 1
        elif score >= 0.85:
            summary["score_distribution"]["0.85-0.94"] += 1
        else:
            summary["score_distribution"]["0.75-0.84"] += 1

        item: dict[str, Any] = {
            "abf_slug": abf["slug"],
            "abf_name": abf["name"],
            "match_score": score,
            "match_strategy": strategy,
        }

        if db_match is None:
            item["match_status"] = "will_create"
            item["match_db_id"] = None
            item["match_db_slug"] = None
            item["insert_payload"] = compute_diff_insert(abf)
            summary["will_create"] += 1
        else:
            item["match_db_id"] = db_match["id"]
            item["match_db_slug"] = db_match.get("slug")
            item["owner_id"] = db_match.get("ownerId")
            item["data_source"] = db_match.get("dataSource")
            summary["matched"] += 1

            if is_claimed(db_match):
                item["match_status"] = "skipped_claimed"
                item["diff"] = {}
                summary["skipped_claimed"] += 1
            else:
                item["match_status"] = "will_enrich"
                item["diff"] = compute_diff_update(abf, db_match)
                summary["will_enrich"] += 1

        # ----------------------------------------------------------------
        # BusinessModels — insere apenas se franquia tem 0 BMs no DB.
        # Skipped_claimed nao recebe BMs (skip total da franquia).
        # ----------------------------------------------------------------
        abf_bms = abf.get("business_models") or []
        item["business_models"] = []

        if item["match_status"] == "skipped_claimed":
            item["business_models_action"] = "skipped_claimed"
        elif not abf_bms:
            item["business_models_action"] = "no_abf_bms"
        else:
            existing_bm_count = (
                bm_counts.get(item["match_db_id"], 0) if db_match else 0
            )
            if existing_bm_count > 0:
                item["business_models_action"] = "skipped_existing"
                item["business_models_existing_count"] = existing_bm_count
                summary["business_models_skipped_existing"] += existing_bm_count
            else:
                item["business_models_action"] = "will_insert"
                # franchise_id placeholder pra will_create — resolvido em apply
                franchise_id = item["match_db_id"] or "<NEW_FRANCHISE_ID>"
                payloads = [
                    build_business_model_payload(bm, franchise_id)
                    for bm in abf_bms
                ]
                item["business_models"] = payloads
                summary["business_models_to_insert"] += len(payloads)

        items.append(item)

    # 3. Apply (se --apply)
    if not is_dry_run:
        print("\n[3/3] Applying to DB...")
        applied = {
            "updates": 0,
            "inserts": 0,
            "bm_inserts": 0,
            "errors": [],
        }
        for item in items:
            try:
                franchise_id = None
                if item["match_status"] == "will_enrich" and item.get("diff"):
                    apply_update(engine, item["match_db_id"], item["diff"])
                    applied["updates"] += 1
                    franchise_id = item["match_db_id"]
                elif item["match_status"] == "will_create":
                    new_id = apply_insert(engine, item["insert_payload"])
                    item["created_db_id"] = new_id
                    applied["inserts"] += 1
                    franchise_id = new_id

                # Insere BMs se policy permite e franchise foi tocada
                if (
                    franchise_id is not None
                    and item.get("business_models_action") == "will_insert"
                ):
                    for bm_payload in item["business_models"]:
                        # Resolve <NEW_FRANCHISE_ID> placeholder
                        bm_payload = dict(bm_payload)
                        bm_payload["franchiseId"] = franchise_id
                        apply_insert_business_model(engine, bm_payload)
                        applied["bm_inserts"] += 1
            except Exception as e:
                applied["errors"].append(f"{item['abf_slug']}: {e}")
        summary["applied"] = applied
    else:
        print("\n[3/3] Skipping APPLY (dry-run).")

    # Outputs (sempre)
    output = {"summary": summary, "items": items}
    diff_path = OUTPUT_DIR / "enrichment_diff.json"
    diff_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str)
    )

    summary_text = write_summary(summary, mode)
    summary_path = OUTPUT_DIR / "enrichment_summary.txt"
    summary_path.write_text(summary_text)

    print()
    print(summary_text)


if __name__ == "__main__":
    main()
