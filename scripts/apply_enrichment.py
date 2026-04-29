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

Limitacao da v1:
  - Insert/update de BusinessModel NAO esta implementado nesta versao.
    Aparece no diff (planejado) mas nao executa em --apply. Proxima
    iteracao depois de validar Franchise.

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
SCRAPER_ROOT = Path("/Users/brenomoretti/Developer/mercadofranquia/scripts/abf_scraper")
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
    if summary.get("applied"):
        lines.append(f"APPLIED to DB:")
        lines.append(f"  Franchise UPDATE: {summary['applied']['updates']}")
        lines.append(f"  Franchise INSERT: {summary['applied']['inserts']}")
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
    print(f"  ABF: {len(abf_samples)} fichas")
    print(f"  DB:  {len(db_franchises)} franquias")

    # 2. Match + diff
    print("\n[2/3] Matching + diff...")
    items = []
    summary = {
        "total_abf": len(abf_samples),
        "matched": 0,
        "skipped_claimed": 0,
        "will_enrich": 0,
        "will_create": 0,
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

        items.append(item)

    # 3. Apply (se --apply)
    if not is_dry_run:
        print("\n[3/3] Applying to DB...")
        applied = {"updates": 0, "inserts": 0, "errors": []}
        for item in items:
            try:
                if item["match_status"] == "will_enrich" and item.get("diff"):
                    apply_update(engine, item["match_db_id"], item["diff"])
                    applied["updates"] += 1
                elif item["match_status"] == "will_create":
                    new_id = apply_insert(engine, item["insert_payload"])
                    item["created_db_id"] = new_id
                    applied["inserts"] += 1
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
