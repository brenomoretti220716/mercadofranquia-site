#!/usr/bin/env python3
"""
Enrichment Diff — cruza dados ABF com o DB do Mercado Franquia
e gera relatório do que vai ser preenchido em cada franquia.

INPUT:
  output/parsed/*.json       — 191 fichas ABF parseadas
  output/db_franchises.json  — dump de Franchise da sua DB (você gera com SQL)

OUTPUT:
  output/enrichment_diff.json — relatório por franquia: {match, fields_to_fill, conflicts}
  output/enrichment_summary.txt — overview legível humano

Como gerar db_franchises.json no EC2 (ou local):
  psql $DATABASE_URL -c '\\copy (
    SELECT json_agg(row_to_json(f)) FROM (
      SELECT id, slug, name, segment, "minimumInvestment", "maximumInvestment",
             "totalUnits", "headquarter", "logoUrl", "scrapedWebsite",
             "averageMonthlyRevenue", description, "franchiseFee", royalties
      FROM "Franchise"
    ) f
  ) TO STDOUT' > output/db_franchises.json
"""
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent.parent
PARSED = ROOT / "output" / "parsed"
OUT_DIFF = ROOT / "output" / "enrichment_diff.json"
OUT_SUM = ROOT / "output" / "enrichment_summary.txt"
DB_DUMP = ROOT / "output" / "db_franchises.json"


def normalize_name(s: str) -> str:
    """Cacau Show -> 'cacau show'; remove acentos, lowercase, etc."""
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s)
    # remove palavras comuns
    for w in ["franquia", "ltda", "me", "sa", "eireli"]:
        s = re.sub(rf"\b{w}\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_slug(s: str) -> str:
    """franquia-cacau-show-valor -> 'cacau show'"""
    if not s: return ""
    s = s.replace("franquia-", "").replace("-valor", "")
    # remove sufixos de segmento
    for suf in [
        "-alimentacao", "-saude-beleza-e-bem-estar", "-saude", "-doces",
        "-educacao-e-treinamento", "-educacao", "-moda", "-servicos",
        "-bebidas", "-estetica", "-comunicacao", "-limpeza-e-conservacao",
        "-casa-e-construcao", "-entretenimento-e-lazer", "-hotelaria-e-turismo",
        "-servicos-automotivos", "-servicos-e-outros-negocios",
    ]:
        if s.endswith(suf):
            s = s[: -len(suf)]
    return s.replace("-", " ").strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def find_best_match(abf_data: dict, db_franchises: list[dict]) -> dict | None:
    """Encontra a melhor correspondência DB pra uma franquia ABF."""
    abf_normalized = normalize_slug(abf_data["slug"])
    abf_name_normalized = normalize_name(abf_data.get("name", ""))

    candidates = []
    for db in db_franchises:
        db_slug_n = normalize_slug(db.get("slug", ""))
        db_name_n = normalize_name(db.get("name", ""))

        # múltiplas estratégias
        score = max(
            similarity(abf_normalized, db_slug_n),
            similarity(abf_normalized, db_name_n),
            similarity(abf_name_normalized, db_slug_n),
            similarity(abf_name_normalized, db_name_n),
        )
        # exact slug match = score 1.0 forçado
        if abf_normalized == db_slug_n or abf_name_normalized == db_name_n:
            score = 1.0
        candidates.append((score, db))

    candidates.sort(key=lambda x: -x[0])
    if candidates and candidates[0][0] >= 0.75:
        return {
            "match": candidates[0][1],
            "score": candidates[0][0],
            "second_best": candidates[1] if len(candidates) > 1 else None,
        }
    return None


def diff_fields(abf: dict, db: dict) -> dict:
    """Retorna o que vai mudar (campos vazios no DB que ABF preenche)."""
    will_fill = {}
    conflicts = {}

    # mapeamentos abf_key -> db_key
    mappings = {
        "name": "name",
        "minimum_investment": "minimumInvestment",
        "maximum_investment": "maximumInvestment",
        "total_units": "totalUnits",
        "headquarter": "headquarter",
        "logo_url": "logoUrl",
        "scraped_website": "scrapedWebsite",
        "meta_description": "description",
    }

    for abf_key, db_key in mappings.items():
        abf_val = abf.get(abf_key)
        db_val = db.get(db_key)
        if abf_val and not db_val:
            will_fill[db_key] = abf_val
        elif abf_val and db_val and abf_val != db_val:
            # conflito: comparar — se forem números, ver diferença
            if isinstance(abf_val, (int, float)) and isinstance(db_val, (int, float)):
                if abs(abf_val - db_val) / max(abs(db_val), 1) > 0.1:  # > 10% de diferença
                    conflicts[db_key] = {"abf": abf_val, "db": db_val}
            elif isinstance(abf_val, str) and isinstance(db_val, str):
                if abf_val.strip().lower() != db_val.strip().lower():
                    conflicts[db_key] = {"abf": abf_val, "db": db_val}

    return {"will_fill": will_fill, "conflicts": conflicts}


def main():
    if not DB_DUMP.exists():
        print(f"! {DB_DUMP} não existe. Crie um dump da sua tabela Franchise.")
        print("Exemplo de SQL:")
        print('  SELECT json_agg(row_to_json(f)) FROM (SELECT id,slug,name,...) f')
        return

    db_data = json.loads(DB_DUMP.read_text())
    abf_files = sorted(PARSED.glob("*.json"))
    print(f"DB franchises: {len(db_data)}")
    print(f"ABF franchises: {len(abf_files)}\n")

    matched, unmatched, conflicts_count = [], [], 0
    diff_report = []

    for f in abf_files:
        abf = json.loads(f.read_text())
        match_info = find_best_match(abf, db_data)

        if not match_info:
            unmatched.append(abf["slug"])
            diff_report.append({
                "abf_slug": abf["slug"],
                "abf_name": abf.get("name"),
                "match": None,
                "action": "create_new",
            })
            continue

        db = match_info["match"]
        diff = diff_fields(abf, db)
        matched.append((abf["slug"], db.get("slug"), match_info["score"]))
        if diff["conflicts"]:
            conflicts_count += 1

        diff_report.append({
            "abf_slug": abf["slug"],
            "abf_name": abf.get("name"),
            "db_id": db.get("id"),
            "db_slug": db.get("slug"),
            "db_name": db.get("name"),
            "match_score": round(match_info["score"], 2),
            "will_fill": diff["will_fill"],
            "conflicts": diff["conflicts"],
            "abf_models_count": len(abf.get("business_models", [])),
            "abf_gallery_count": len(abf.get("gallery_urls", [])),
            "abf_has_logo": bool(abf.get("logo_url")),
            "abf_updated_at": abf.get("abf_updated_at"),
        })

    OUT_DIFF.write_text(json.dumps(diff_report, ensure_ascii=False, indent=2))

    # summary text
    lines = []
    lines.append("=" * 70)
    lines.append("ABF Enrichment Diff Report")
    lines.append("=" * 70)
    lines.append(f"DB franchises:  {len(db_data):>4d}")
    lines.append(f"ABF franchises: {len(abf_files):>4d}")
    lines.append(f"")
    lines.append(f"Matches:        {len(matched):>4d} ({len(matched)*100//len(abf_files)}%)")
    lines.append(f"Unmatched:      {len(unmatched):>4d}  -> nova marca a criar")
    lines.append(f"Conflicts:      {conflicts_count:>4d}  -> dados ABF divergem do DB")
    lines.append("")

    # matches por score
    score_bins = {"1.0 (exact)": 0, "0.9-1.0": 0, "0.8-0.9": 0, "0.75-0.8": 0}
    for _, _, score in matched:
        if score >= 1.0: score_bins["1.0 (exact)"] += 1
        elif score >= 0.9: score_bins["0.9-1.0"] += 1
        elif score >= 0.8: score_bins["0.8-0.9"] += 1
        else: score_bins["0.75-0.8"] += 1
    lines.append("Quality dos matches:")
    for k, v in score_bins.items():
        lines.append(f"  {k:>15s}: {v}")

    lines.append("\nCampos preenchíveis (top):")
    field_counts = {}
    for r in diff_report:
        for k in r.get("will_fill", {}).keys():
            field_counts[k] = field_counts.get(k, 0) + 1
    for k, v in sorted(field_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {k:>22s}: {v} franquias")

    lines.append("\nUnmatched (primeiras 20):")
    for slug in unmatched[:20]:
        lines.append(f"  {slug}")
    if len(unmatched) > 20:
        lines.append(f"  ... e mais {len(unmatched)-20}")

    lines.append("\nMatches com baixo score (<0.85, primeiros 10):")
    low = [(a,b,s) for a,b,s in matched if s < 0.85][:10]
    for abf_s, db_s, score in low:
        lines.append(f"  {score:.2f}  {abf_s}  -> {db_s}")

    OUT_SUM.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\n→ {OUT_DIFF}")
    print(f"→ {OUT_SUM}")


if __name__ == "__main__":
    main()
