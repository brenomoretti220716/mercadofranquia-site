#!/usr/bin/env python3
"""Apply ABF refresh — override total + BMs DELETE+INSERT.

Politica diferente do apply_enrichment.py original (que era set-if-null).
Esta versao assume "tudo e teste, sem dados manuais reais em prod" e
sobrescreve qualquer Franchise matched do scrape novo, incluindo:
  - 3 campos novos (videoUrl, detailedDescription, idealFranchiseeProfile)
  - galleryUrls replace completo
  - BusinessModels DELETE+INSERT (nao merge)
  - royaltyType/royaltyFixedAmount/adFeeType/adFeeFixedAmount populados via
    derive_rate_fields() — alinhado com migration business_model_royalty_v2

Politica de skip:
  - Apenas slugs em SKIP_SLUGS (pizza-teste, star-point) — testes E2E.
  - Fichas claimed/manual sao SOBRESCRITAS mas reportadas como warning
    no dry-run pra revisao.

Politica de stale:
  - Fichas em prod com abfUpdatedAt setado mas AUSENTES do scrape novo
    sao reportadas em "stale_fichas" mas NAO deletadas/marcadas.

Uso:
    .venv/bin/python scripts/apply_abf_refresh.py             # dry-run
    .venv/bin/python scripts/apply_abf_refresh.py --apply     # exec real
    .venv/bin/python scripts/apply_abf_refresh.py --limit 5   # smoke
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
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

SKIP_SLUGS = {"pizza-teste", "star-point"}

# Campos do Franchise sobrescritos (override total) quando ABF traz valor.
# Campos NAO listados aqui sao preservados no UPDATE.
OVERRIDE_FIELD_MAP = [
    # (abf_key, db_key)
    ("name", "name"),
    ("meta_description", "description"),
    ("detailed_description", "detailedDescription"),
    ("ideal_franchisee_profile", "idealFranchiseeProfile"),
    ("tagline", "tagline"),
    ("logo_url", "logoUrl"),
    ("banner_url", "bannerUrl"),
    ("video_url", "videoUrl"),
    ("minimum_investment", "minimumInvestment"),
    ("maximum_investment", "maximumInvestment"),
    ("total_units", "totalUnits"),
    ("headquarter", "headquarter"),
    ("scraped_website", "scrapedWebsite"),
    ("segment_abf_name", "segment"),
]


# ============================================================================
# Normalizacao + matching (reuse pattern de apply_enrichment.py)
# ============================================================================
def normalize_for_match(s: Optional[str]) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def normalize_abf_slug(slug: str) -> str:
    s = slug.lower()
    s = re.sub(r"^franquia[-_]", "", s)
    s = re.sub(r"[-_](valor|oportunidades?|investimento)$", "", s)
    return s


def find_match(
    abf: dict, db_franchises: list[dict]
) -> tuple[Optional[dict], float, str]:
    abf_slug_norm = normalize_for_match(normalize_abf_slug(abf["slug"]))
    abf_name_norm = normalize_for_match(abf["name"])

    for db in db_franchises:
        if db.get("slug") and normalize_for_match(db["slug"]) == abf_slug_norm:
            return (db, 1.0, "slug_exact")

    for db in db_franchises:
        if db.get("name") and normalize_for_match(db["name"]) == abf_name_norm:
            return (db, 0.95, "name_exact")

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
def parse_date_br(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def parse_iso_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def derive_rate_fields(
    rate_text: Optional[str],
) -> tuple[Optional[str], Optional[float], Optional[int]]:
    """Parse rate text from parser into (type, pct, fixed_cents).

    Patterns observados em 233 BMs (cobertura 100%):
        '3 %' / '12 %' / '30 %'   -> ('PERCENTAGE', float, None)
        'R$ 400' / 'R$ 1.160'     -> ('FIXED', None, cents)
        'VARIÁVEL'                -> ('VARIABLE', None, None)
        'Não Cobra'               -> ('NONE', None, None)
        None / ''                 -> (None, None, None)
    """
    if not rate_text:
        return (None, None, None)
    rl = rate_text.lower().strip()

    if rl in ("variável", "variavel"):
        return ("VARIABLE", None, None)

    if any(x in rl for x in ("não cobra", "nao cobra", "isento")):
        return ("NONE", None, None)

    # Fixo: 'R$ 400' ou 'R$ 1.160' (BR thousands separator)
    m_fixed = re.match(r"r\$\s*([\d.,]+)", rl)
    if m_fixed:
        raw = m_fixed.group(1)
        if "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "." in raw and len(raw.split(".")[-1]) == 3:
            # '1.160' -> 1160 (thousands separator BR)
            raw = raw.replace(".", "")
        try:
            return ("FIXED", None, int(round(float(raw) * 100)))
        except ValueError:
            return (None, None, None)

    # Percentual: '3 %' / '12 %' / '38,4 %'
    m_pct = re.search(r"(\d+(?:[.,]\d+)?)\s*%", rate_text)
    if m_pct:
        try:
            return ("PERCENTAGE", float(m_pct.group(1).replace(",", ".")), None)
        except ValueError:
            return (None, None, None)

    return (None, None, None)


# ============================================================================
# DB IO
# ============================================================================
def load_db_franchises(engine) -> list[dict]:
    sql = text(
        """
        SELECT id, slug, name, "ownerId", "dataSource",
               description, "detailedDescription", "idealFranchiseeProfile",
               tagline, "logoUrl", "bannerUrl", "videoUrl",
               "scrapedWebsite", "lastScrapedAt", "abfUpdatedAt",
               "minimumInvestment", "maximumInvestment", "totalUnits",
               headquarter, segment, "galleryUrls", "isAbfAssociated"
        FROM "Franchise"
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
    return [dict(r._mapping) for r in rows]


# ============================================================================
# Plan computation
# ============================================================================
def build_business_model_payload(bm: dict, franchise_id: str) -> dict[str, Any]:
    """Constroi payload pra INSERT de 1 BusinessModel.

    Diferenca vs apply_enrichment.py original:
      - Popula royaltyType / royaltyFixedAmount / adFeeType / adFeeFixedAmount
      - Quando type=PERCENTAGE: royalties tem o pct, royaltyFixedAmount=NULL
      - Quando type=FIXED: royalties=NULL, royaltyFixedAmount tem centavos
      - Quando type=VARIABLE/NONE: royalties=NULL, royaltyFixedAmount=NULL
      - Observation preservada como vem do parser
    """
    royalty_type, royalty_pct, royalty_fixed = derive_rate_fields(
        bm.get("royalties_rate")
    )
    ad_type, ad_pct, ad_fixed = derive_rate_fields(bm.get("advertising_fee_rate"))

    area_min = bm.get("area_m2_min")

    return {
        "id": uuid.uuid4().hex,
        "name": bm.get("name") or "Modelo",
        "description": None,
        "photoUrl": None,
        "franchiseId": franchise_id,
        "franchiseFee": bm.get("franchise_fee_min"),
        "royalties": royalty_pct,
        "royaltyType": royalty_type,
        "royaltyFixedAmount": royalty_fixed,
        "calculationBaseRoyaltie": bm.get("royalties_base"),
        "royaltiesObservation": bm.get("royalties_observation"),
        "advertisingFee": ad_pct,
        "adFeeType": ad_type,
        "adFeeFixedAmount": ad_fixed,
        "calculationBaseAdFee": bm.get("advertising_fee_base"),
        "advertisingFeeObservation": bm.get("advertising_fee_observation"),
        "workingCapital": bm.get("working_capital_min"),
        "setupCapital": bm.get("capital_installation_min"),
        "averageMonthlyRevenue": None,
        "storeArea": int(area_min) if area_min is not None else None,
        "investment": bm.get("investment_total_min"),
        "payback": bm.get("payback_months_min"),
        "profitability": None,
        "headquarter": bm.get("headquarter"),
        "totalUnits": bm.get("total_units"),
    }


def compute_franchise_update(abf: dict, db: dict) -> dict[str, Any]:
    """Diff de UPDATE override — substitui campo se ABF traz valor non-null.

    Retorna dict {db_col: novo_valor} pra UPDATE. abfUpdatedAt e lastScrapedAt
    sempre atualizados. dataSource preservado (nao re-seta).
    """
    diff: dict[str, Any] = {}
    for abf_key, db_key in OVERRIDE_FIELD_MAP:
        abf_val = abf.get(abf_key)
        if abf_val is None or abf_val == "":
            continue
        if db.get(db_key) != abf_val:
            diff[db_key] = abf_val

    abf_gallery = abf.get("gallery_urls") or []
    if abf_gallery:
        diff["galleryUrls"] = json.dumps(abf_gallery)

    diff["isAbfAssociated"] = True
    diff["abfUpdatedAt"] = parse_date_br(abf.get("abf_updated_at"))
    diff["lastScrapedAt"] = parse_iso_datetime(abf.get("scraped_at"))

    return diff


def compute_franchise_insert(abf: dict) -> dict[str, Any]:
    """Payload pra INSERT de Franchise nova (sem match)."""
    payload: dict[str, Any] = {}
    for abf_key, db_key in OVERRIDE_FIELD_MAP:
        v = abf.get(abf_key)
        if v is not None and v != "":
            payload[db_key] = v
    payload["slug"] = normalize_abf_slug(abf["slug"])
    payload["galleryUrls"] = json.dumps(abf.get("gallery_urls") or [])
    payload["abfUpdatedAt"] = parse_date_br(abf.get("abf_updated_at"))
    payload["lastScrapedAt"] = parse_iso_datetime(abf.get("scraped_at"))
    payload["dataSource"] = "abf-portaldofranchising"
    payload["isAbfAssociated"] = True
    return payload


# ============================================================================
# DB write helpers
# ============================================================================
def update_franchise(conn, db_id: str, diff: dict) -> None:
    if not diff:
        return
    sets = []
    params: dict[str, Any] = {"id": db_id}
    for col, val in diff.items():
        sets.append(f'"{col}" = :p_{col}')
        params[f"p_{col}"] = val
    sql = text(
        f'UPDATE "Franchise" SET {", ".join(sets)}, "updatedAt" = NOW() '
        f'WHERE id = :id'
    )
    conn.execute(sql, params)


def delete_business_models(conn, franchise_id: str) -> int:
    res = conn.execute(
        text('DELETE FROM "BusinessModel" WHERE "franchiseId" = :id'),
        {"id": franchise_id},
    )
    return res.rowcount


def insert_business_model(conn, payload: dict) -> None:
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
    conn.execute(sql, params)


def insert_franchise(conn, payload: dict) -> str:
    new_id = uuid.uuid4().hex
    payload = dict(payload)
    payload["id"] = new_id
    cols = list(payload.keys())
    placeholders = [f":p_{c}" for c in cols]
    quoted = ", ".join(f'"{c}"' for c in cols)
    params = {f"p_{c}": v for c, v in payload.items()}
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
    conn.execute(sql, params)
    return new_id


# ============================================================================
# Main pipeline
# ============================================================================
def load_scrape() -> list[dict]:
    files = sorted(PARSED_DIR.glob("*.json"))
    return [json.loads(f.read_text()) for f in files]


def compute_plan(scrape: list[dict], db_franchises: list[dict]) -> dict:
    """Constroi plano completo de execucao (sem tocar DB)."""
    plan: dict[str, list] = {
        "skip_whitelist": [],
        "override": [],
        "create": [],
        "claimed_warning": [],
    }

    db_by_id = {d["id"]: d for d in db_franchises}

    for abf in scrape:
        match, score, strategy = find_match(abf, db_franchises)

        if match:
            db_slug = match.get("slug")
            if db_slug in SKIP_SLUGS:
                plan["skip_whitelist"].append(
                    {"abf_slug": abf["slug"], "db_slug": db_slug}
                )
                continue

            is_claimed = (
                match.get("ownerId") is not None
                or match.get("dataSource") in ("manual", "claimed")
            )

            franchise_diff = compute_franchise_update(abf, match)
            bm_payloads = [
                build_business_model_payload(bm, match["id"])
                for bm in (abf.get("business_models") or [])
            ]

            entry = {
                "abf_slug": abf["slug"],
                "db_slug": db_slug,
                "db_id": match["id"],
                "match_strategy": strategy,
                "match_score": score,
                "franchise_diff_keys": sorted(franchise_diff.keys()),
                "bm_count_old": None,  # filled later via load_business_model_counts
                "bm_count_new": len(bm_payloads),
                "_franchise_diff": franchise_diff,
                "_bm_payloads": bm_payloads,
            }

            if is_claimed:
                plan["claimed_warning"].append(entry)
            plan["override"].append(entry)
        else:
            franchise_payload = compute_franchise_insert(abf)
            bm_payloads = [
                build_business_model_payload(bm, "<placeholder>")
                for bm in (abf.get("business_models") or [])
            ]
            plan["create"].append(
                {
                    "abf_slug": abf["slug"],
                    "abf_name": abf.get("name"),
                    "_franchise_payload": franchise_payload,
                    "_bm_payloads": bm_payloads,
                }
            )

    # Stale: fichas em DB com abfUpdatedAt setado mas AUSENTES do scrape novo
    scrape_db_slugs = {
        d.get("db_slug")
        for entry_list in (plan["override"], plan["skip_whitelist"])
        for d in entry_list
    }
    plan["stale_fichas"] = [
        {"db_slug": d.get("slug"), "name": d.get("name")}
        for d in db_franchises
        if d.get("abfUpdatedAt")
        and d.get("slug") not in scrape_db_slugs
        and d.get("slug") not in SKIP_SLUGS
    ]

    return plan


def fill_bm_counts_old(plan: dict, engine) -> None:
    franchise_ids = [e["db_id"] for e in plan["override"]]
    if not franchise_ids:
        return
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                'SELECT "franchiseId", COUNT(*) AS n FROM "BusinessModel" '
                'WHERE "franchiseId" = ANY(:ids) GROUP BY "franchiseId"'
            ),
            {"ids": franchise_ids},
        ).all()
    counts = {r._mapping["franchiseId"]: r._mapping["n"] for r in rows}
    for e in plan["override"]:
        e["bm_count_old"] = counts.get(e["db_id"], 0)


def report_dry_run(plan: dict, scrape: list[dict]) -> str:
    """Gera relatorio textual do plano. Retorna string pra print + write."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("=== ABF Refresh — Apply Plan ===")
    lines.append("=" * 78)
    lines.append("")

    total_bms = sum(len(d.get("business_models") or []) for d in scrape)
    lines.append(f"Scrape novo: {len(scrape)} fichas, {total_bms} BMs")
    lines.append("")

    lines.append(f"WILL_SKIP (whitelist): {len(plan['skip_whitelist'])}")
    for e in plan["skip_whitelist"]:
        lines.append(f"  - {e['db_slug']} (abf={e['abf_slug']})")
    lines.append("")

    lines.append(f"WILL_OVERRIDE (matched): {len(plan['override'])}")
    lines.append(f"WILL_CREATE (no match): {len(plan['create'])}")
    for e in plan["create"]:
        lines.append(f"  + {e['abf_slug']} ({e['abf_name']})")
    lines.append("")

    if plan["claimed_warning"]:
        lines.append(
            f"CLAIMED_OVERRIDDEN (warning — sera sobrescrito): {len(plan['claimed_warning'])}"
        )
        for e in plan["claimed_warning"]:
            lines.append(f"  ⚠ {e['db_slug']}")
        lines.append("")

    # Field-level overrides count
    field_counts: dict[str, int] = {}
    for e in plan["override"]:
        for k in e["franchise_diff_keys"]:
            field_counts[k] = field_counts.get(k, 0) + 1
    lines.append("CAMPOS_OVERRIDE counts:")
    for k in sorted(field_counts.keys(), key=lambda x: -field_counts[x]):
        lines.append(f"  {k:30} {field_counts[k]}")
    lines.append("")

    bms_delete = sum(e.get("bm_count_old", 0) or 0 for e in plan["override"])
    bms_insert_override = sum(e["bm_count_new"] for e in plan["override"])
    bms_insert_create = sum(len(e["_bm_payloads"]) for e in plan["create"])
    lines.append(f"BMs DELETE (override targets): {bms_delete}")
    lines.append(
        f"BMs INSERT: {bms_insert_override + bms_insert_create} "
        f"({bms_insert_override} override + {bms_insert_create} create)"
    )
    lines.append("")

    # Royalty type breakdown
    type_counts_roy: dict[str, int] = {}
    type_counts_ad: dict[str, int] = {}
    for entry_list in (plan["override"], plan["create"]):
        for e in entry_list:
            for bm in e["_bm_payloads"]:
                rt = bm.get("royaltyType") or "(none)"
                at = bm.get("adFeeType") or "(none)"
                type_counts_roy[rt] = type_counts_roy.get(rt, 0) + 1
                type_counts_ad[at] = type_counts_ad.get(at, 0) + 1
    lines.append("Royalty type breakdown (BMs novos):")
    for t in ("PERCENTAGE", "FIXED", "VARIABLE", "NONE", "(none)"):
        if t in type_counts_roy:
            lines.append(f"  {t:12} {type_counts_roy[t]}")
    lines.append("")
    lines.append("Ad fee type breakdown:")
    for t in ("PERCENTAGE", "FIXED", "VARIABLE", "NONE", "(none)"):
        if t in type_counts_ad:
            lines.append(f"  {t:12} {type_counts_ad[t]}")
    lines.append("")

    if plan["stale_fichas"]:
        lines.append(
            f"STALE (em prod com abfUpdatedAt mas ausentes do scrape novo): "
            f"{len(plan['stale_fichas'])}"
        )
        for e in plan["stale_fichas"]:
            lines.append(f"  ~ {e['db_slug']} ({e['name']})")
        lines.append("  (NÃO TOCADAS, log only)")
        lines.append("")

    return "\n".join(lines)


def apply_plan(engine, plan: dict) -> dict:
    """Executa o plano em prod. Cada ficha em sua propria transacao."""
    stats = {
        "updated": 0,
        "created": 0,
        "bms_deleted": 0,
        "bms_inserted": 0,
        "errors": [],
    }

    # Override
    for entry in plan["override"]:
        try:
            with engine.begin() as conn:
                update_franchise(conn, entry["db_id"], entry["_franchise_diff"])
                deleted = delete_business_models(conn, entry["db_id"])
                stats["bms_deleted"] += deleted
                for bm_payload in entry["_bm_payloads"]:
                    insert_business_model(conn, bm_payload)
                    stats["bms_inserted"] += 1
                stats["updated"] += 1
        except Exception as e:
            stats["errors"].append(
                {"slug": entry["db_slug"], "phase": "override", "error": str(e)[:200]}
            )

    # Create
    for entry in plan["create"]:
        try:
            with engine.begin() as conn:
                new_id = insert_franchise(conn, entry["_franchise_payload"])
                for bm_payload in entry["_bm_payloads"]:
                    bm_payload["franchiseId"] = new_id
                    insert_business_model(conn, bm_payload)
                    stats["bms_inserted"] += 1
                stats["created"] += 1
        except Exception as e:
            stats["errors"].append(
                {"slug": entry["abf_slug"], "phase": "create", "error": str(e)[:200]}
            )

    return stats


# ============================================================================
# Entry
# ============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="ABF refresh apply (override total).")
    ap.add_argument("--apply", action="store_true", help="Executa em prod (default: dry-run)")
    ap.add_argument("--limit", type=int, help="Processa so as primeiras N fichas (smoke)")
    ap.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Postgres URL (env DATABASE_URL ou default local)",
    )
    args = ap.parse_args()

    scrape = load_scrape()
    if args.limit:
        scrape = scrape[: args.limit]
    print(f"[load] {len(scrape)} fichas em {PARSED_DIR}")

    engine = create_engine(args.database_url)
    db_franchises = load_db_franchises(engine)
    print(f"[load] {len(db_franchises)} fichas em DB")

    plan = compute_plan(scrape, db_franchises)
    fill_bm_counts_old(plan, engine)

    report = report_dry_run(plan, scrape)
    print(report)

    summary_path = OUTPUT_DIR / (
        "abf_refresh_apply_summary.txt" if args.apply else "abf_refresh_dry_run.txt"
    )
    summary_path.write_text(report)
    print(f"\n[report] gravado em {summary_path}")

    # Plano serializado pra debug (sem _franchise_payload em prod por seguranca)
    diff_path = OUTPUT_DIR / "abf_refresh_plan.json"
    diff_path.write_text(
        json.dumps(
            {
                "skip_whitelist": plan["skip_whitelist"],
                "override_count": len(plan["override"]),
                "create_count": len(plan["create"]),
                "claimed_warning": [
                    {"slug": e["db_slug"]} for e in plan["claimed_warning"]
                ],
                "stale_fichas": plan["stale_fichas"],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    print(f"[plan]   serializado em {diff_path}")

    if not args.apply:
        print("\n=== DRY-RUN — nenhuma alteracao no DB ===")
        return 0

    print("\n=== APPLY MODE — executando em DB ===")
    stats = apply_plan(engine, plan)
    print(f"\n[apply] updated={stats['updated']} created={stats['created']}")
    print(
        f"[apply] BMs deleted={stats['bms_deleted']} inserted={stats['bms_inserted']}"
    )
    if stats["errors"]:
        print(f"[apply] ERRORS ({len(stats['errors'])}):")
        for e in stats["errors"]:
            print(f"  - {e['slug']} [{e['phase']}]: {e['error']}")

    summary_path.write_text(
        report
        + f"\n\n=== APPLY EXECUTADO ===\n"
        + json.dumps(stats, ensure_ascii=False, indent=2, default=str)
    )
    print(f"\n[apply] summary atualizado em {summary_path}")

    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
