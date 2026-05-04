#!/usr/bin/env python3
"""Parse HTML cache → output/parsed/{slug}.json.

Reads /tmp/encontresua_html/*.html, writes per-ficha JSON.
Multi-BM aware: BM-specific fields go into business_models list.
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "output" / "parsed"
PARSED.mkdir(parents=True, exist_ok=True)
CACHE = Path("/tmp/encontresua_html")

LABEL_RE = re.compile(
    r'directorist-single-info__label__text"[^>]*>([^<]+)<.*?'
    r'directorist-single-info__value[^"]*"[^>]*>([^<]*)<',
    re.DOTALL,
)
H1_RE = re.compile(
    r'directorist-listing-details__listing-title"[^>]*>([^<]+)<'
)
DESC_RE = re.compile(
    r'directorist-listing-details__text[^>]*>(.*?)(?=<div[^>]*class="[^"]*directorist-card)',
    re.DOTALL,
)
OG_IMG_RE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"')
OG_DESC_RE = re.compile(r'<meta\s+property="og:description"\s+content="([^"]+)"')

# BM-aware split: only between closing paren and next non-empty token
MULTI_BM_SPLIT_RE = re.compile(r"(?<=\))\s*/\s*(?=\S)")
TRAILING_TAG_RE = re.compile(r"\(([^)]+)\)\s*$")

KNOWN_BM_TAGS = {"loja", "quiosque", "home based", "online", "loja/quiosque"}

TEMPLATE_PATTERNS = [
    r"\bé uma franquia que (atua|opera) no segmento\b",
    r"\bé uma marca brasileira que\b",
    r"\bFundada em \d{4}\b",
    r"\brapidamente (se destacou|conquistou)\b",
    r"\bmodelo de (crescimento|negócios?|negocio)\b",
    r"\bA marca não apenas\b",
    r"\bse destaca no segmento\b",
    r"\bmercado de \w+ no Brasil\b",
]


def clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def first_int(s: str) -> int | None:
    m = re.search(r"(\d{1,4})", s)
    return int(m.group(1)) if m else None


def normalize_pct_token(raw: str) -> float | None:
    """'6,00' / '38,4' / '3.00' → float. Brazilian or US-style decimal."""
    raw = raw.strip()
    if not raw:
        return None
    has_comma = "," in raw
    has_dot = "." in raw
    if has_comma and has_dot:
        raw = raw.replace(".", "").replace(",", ".")
    elif has_comma:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_money(s: str) -> int | None:
    """'R$ 370.000' -> 370000 ; 'R$ 5 mil' -> 5000 ; '500' -> 500."""
    s = s.strip()
    if not s:
        return None
    s_low = s.lower()
    has_mil = " mil" in s_low or s_low.endswith("mil")
    has_milhao = "milh" in s_low
    m = re.search(r"r\$\s*([\d.,]+)", s_low)
    if not m:
        m = re.search(r"([\d.,]+)", s_low)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        v = float(raw)
    except ValueError:
        return None
    if has_milhao:
        v *= 1_000_000
    elif has_mil:
        v *= 1_000
    return int(round(v))


def split_multi_bm(text: str) -> list[str]:
    """Split a field into BM-tagged parts.

    Only splits on '/' that follows a closing paren, so '(loja/quiosque)' stays intact.
    """
    if not text:
        return []
    return MULTI_BM_SPLIT_RE.split(text)


def part_tag_and_body(part: str) -> tuple[str | None, str]:
    """Strip trailing '(tag)' and return (tag, body)."""
    m = TRAILING_TAG_RE.search(part)
    if m:
        tag = m.group(1).strip().lower()
        body = part[: m.start()].strip()
        return (tag, body)
    return (None, part.strip())


def parse_rate_body(body: str) -> tuple[float | None, str | None, bool, list[str]]:
    """Parse the body of a rate field (no parens tag).

    Returns (pct, base, is_fixed, flags).
    """
    flags: list[str] = []
    body = body.strip()
    if not body or body.lower() in ("não informado", "nao informado"):
        return (None, None, False, flags)
    low = body.lower()
    if "não cobra" in low or "nao cobra" in low or "isento" in low:
        return (0.0, None, False, flags)
    if "r$" in low or "fixo" in low or "reais" in low:
        return (None, body, True, flags)
    m = re.search(r"([\d.,]+)\s*%", body)
    if not m:
        flags.append("rate_unparseable")
        return (None, body or None, False, flags)
    pct = normalize_pct_token(m.group(1))
    if pct is None:
        flags.append("rate_unparseable")
        return (None, body or None, False, flags)
    after = body[m.end():].strip(" -")
    return (pct, after or None, False, flags)


def parse_payback_body(body: str) -> tuple[int | None, int | None, list[str]]:
    """Parse a payback body like '24 a 36' (parens already stripped)."""
    flags: list[str] = []
    if not body or "não informado" in body.lower():
        return (None, None, flags)
    m = re.search(r"(\d+)\s*a\s*(\d+)", body)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > b:
            flags.append("payback_range_swapped")
            a, b = b, a
        return (a, b, flags)
    m = re.search(r"(\d+)", body)
    if m:
        v = int(m.group(1))
        return (v, v, flags)
    return (None, None, flags)


def parse_investment_range(text: str) -> tuple[int | None, int | None, list[str]]:
    """Investment total is ficha-wide (not BM-specific). Splits on ' / ' as min/max."""
    flags: list[str] = []
    if not text or text.lower().strip() in ("não informado", "nao informado", ""):
        return (None, None, flags)
    if "/" in text:
        parts = [p.strip() for p in text.split("/")]
        vals = [parse_money(p) for p in parts]
        vals = [v for v in vals if v is not None]
        if len(vals) >= 2:
            mn, mx = min(vals[0], vals[1]), max(vals[0], vals[1])
            if vals[0] > vals[1]:
                flags.append("investment_range_swapped")
            return (mn, mx, flags)
        if len(vals) == 1:
            flags.append("investment_only_one_side_parseable")
            return (vals[0], vals[0], flags)
        flags.append("investment_unparseable")
        return (None, None, flags)
    v = parse_money(text)
    if v is None:
        flags.append("investment_unparseable")
        return (None, None, flags)
    return (v, v, flags)


def is_valid_bm_tag(tag: str) -> bool:
    """Reject tags that look like garbage (URLs, query strings, overly long)."""
    if not tag or len(tag) > 30:
        return False
    low = tag.lower()
    if any(x in low for x in ("http", "wp-admin", "?", "=", "&", ".com", ".php")):
        return False
    return True


def expand_compound_tags(tags: list[str]) -> list[str]:
    """'loja/quiosque' → ['loja', 'quiosque'], filtering garbage and dedup."""
    out: list[str] = []
    for t in tags:
        if not is_valid_bm_tag(t):
            continue
        if "/" in t:
            for s in t.split("/"):
                s = s.strip()
                if s and is_valid_bm_tag(s) and s not in out:
                    out.append(s)
        elif t not in out:
            out.append(t)
    return out


def collect_bm_tags_ordered(fields: dict[str, str], bm_field_names: list[str]) -> list[str]:
    """Collect distinct BM tags from BM-specific fields, in order of first appearance.

    Drops tags that appear in only 1 field when another tag appears in >=2 fields
    — defends against single-field typos (e.g. instituto-gourmet's '(Inja)').
    """
    field_counts: dict[str, int] = {}
    ordered: list[str] = []
    for fname in bm_field_names:
        text = fields.get(fname, "")
        if not text:
            continue
        seen_in_this_field: set[str] = set()
        for part in split_multi_bm(text):
            tag, _ = part_tag_and_body(part)
            if tag and tag not in seen_in_this_field:
                seen_in_this_field.add(tag)
                field_counts[tag] = field_counts.get(tag, 0) + 1
                if tag not in ordered:
                    ordered.append(tag)

    if len(ordered) <= 1:
        return ordered
    max_count = max(field_counts.values())
    if max_count >= 2:
        return [t for t in ordered if field_counts.get(t, 0) >= 2]
    return ordered


def build_business_models(fields: dict[str, str], flags_out: list[str]) -> list[dict]:
    """Build a list of BM dicts. Single-BM fichas → list of 1. Multi-BM → N entries."""
    bm_field_names = [
        "Royalties",
        "Taxa de publicidade",
        "Faturamento médio",
        "Lucro médio",
        "Prazo de retorno (meses)",
    ]
    raw_tags = collect_bm_tags_ordered(fields, bm_field_names)
    tags = expand_compound_tags(raw_tags)

    if not tags:
        # No BM tags anywhere: defend against typo or missing parens by majority voting
        # (instituto-gourmet had a single typo "(Inja)")
        all_paren_tags: list[str] = []
        for fname in bm_field_names:
            text = fields.get(fname, "")
            for m in re.finditer(r"\(([^)]+)\)", text):
                all_paren_tags.append(m.group(1).strip().lower())
        if all_paren_tags:
            counts = Counter(all_paren_tags)
            best = counts.most_common(1)[0][0]
            tags = expand_compound_tags([best])

    if not tags:
        return []

    # Pre-split each BM field into list of (tag, body) parts
    field_parts: dict[str, list[tuple[str | None, str]]] = {}
    for fname in bm_field_names:
        text = fields.get(fname, "")
        if not text:
            field_parts[fname] = []
            continue
        parts = [part_tag_and_body(p) for p in split_multi_bm(text)]
        field_parts[fname] = parts

    bms: list[dict] = []
    for idx, tag in enumerate(tags):
        bm = {"tag": tag}
        for fname, parts in field_parts.items():
            value_text = None
            if not parts:
                pass
            elif len(parts) == 1:
                # Single value applies to current BM if tag matches/absent,
                # OR if we only have 1 BM (single-BM ficha; tag mismatch = source typo)
                ptag, body = parts[0]
                if (
                    ptag is None
                    or ptag == tag
                    or tag in expand_compound_tags([ptag])
                    or len(tags) == 1
                ):
                    value_text = parts[0][1]
            else:
                # Multi-part: try tag match first
                matched = None
                for ptag, body in parts:
                    if ptag and (ptag == tag or tag in expand_compound_tags([ptag])):
                        matched = body
                        break
                if matched is None and idx < len(parts):
                    # Fall back to position
                    matched = parts[idx][1]
                value_text = matched

            # Now parse the value_text by field type
            bm[f"{slug_of_field(fname)}_text"] = value_text
            if fname == "Royalties":
                if value_text is None:
                    bm["royalties_pct"] = None
                    bm["royalties_base"] = None
                    bm["royalties_is_fixed"] = False
                else:
                    pct, base, fixed, fs = parse_rate_body(value_text)
                    bm["royalties_pct"] = pct if not fixed else None
                    bm["royalties_base"] = base
                    bm["royalties_is_fixed"] = fixed
                    flags_out.extend(fs)
                    if fixed:
                        flags_out.append("royalties_fixed_value")
                    if pct is not None and pct > 30 and not fixed:
                        flags_out.append("royalties_pct_above_30_sanity")
            elif fname == "Taxa de publicidade":
                if value_text is None:
                    bm["ad_fee_pct"] = None
                    bm["ad_fee_base"] = None
                    bm["ad_fee_is_fixed"] = False
                else:
                    pct, base, fixed, fs = parse_rate_body(value_text)
                    bm["ad_fee_pct"] = pct if not fixed else None
                    bm["ad_fee_base"] = base
                    bm["ad_fee_is_fixed"] = fixed
                    flags_out.extend(fs)
                    if fixed:
                        flags_out.append("ad_fee_fixed_value")
                    if pct is not None and pct > 10 and not fixed:
                        flags_out.append("ad_fee_pct_above_10_sanity")
            elif fname == "Faturamento médio":
                bm["avg_revenue"] = parse_money(value_text) if value_text else None
            elif fname == "Lucro médio":
                bm["avg_profit"] = parse_money(value_text) if value_text else None
            elif fname == "Prazo de retorno (meses)":
                if value_text is None:
                    bm["payback_min_months"] = None
                    bm["payback_max_months"] = None
                else:
                    a, b, fs = parse_payback_body(value_text)
                    bm["payback_min_months"] = a
                    bm["payback_max_months"] = b
                    flags_out.extend(fs)
        bms.append(bm)
    return bms


def slug_of_field(fname: str) -> str:
    mapping = {
        "Royalties": "royalties",
        "Taxa de publicidade": "ad_fee",
        "Faturamento médio": "avg_revenue",
        "Lucro médio": "avg_profit",
        "Prazo de retorno (meses)": "payback",
    }
    return mapping.get(fname, fname)


def detect_templated(desc: str | None) -> bool:
    if not desc or len(desc) < 200:
        return False
    hits = 0
    for pat in TEMPLATE_PATTERNS:
        if re.search(pat, desc, re.IGNORECASE):
            hits += 1
    return hits >= 2


def has_corruption(fields: dict[str, str]) -> bool:
    """Detect upstream data corruption (e.g. lupo's embedded URL)."""
    for v in fields.values():
        for m in re.finditer(r"\(([^)]+)\)", v):
            tag = m.group(1)
            if "http" in tag.lower() or "wp-admin" in tag.lower():
                return True
    return False


def parse_one(slug: str, html_text: str) -> dict:
    parsed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    m = H1_RE.search(html_text)
    name = clean_html(m.group(1)) if m else slug

    desc_long = None
    m = DESC_RE.search(html_text)
    if m:
        desc_long = clean_html(m.group(1))
        if len(desc_long) < 50:
            desc_long = None

    desc_short = None
    m = OG_DESC_RE.search(html_text)
    if m:
        desc_short = html.unescape(m.group(1)).strip()

    logo_url = None
    m = OG_IMG_RE.search(html_text)
    if m:
        logo_url = m.group(1).strip()

    pairs = LABEL_RE.findall(html_text)
    fields: dict[str, str] = {}
    for label, value in pairs:
        fields[clean_html(label)] = clean_html(value)

    inv_text = fields.get("Investimento total", "")
    franchise_fee_text = fields.get("Taxa de franquia", "")
    working_cap_text = fields.get("Capital de giro", "")
    tier_text = fields.get("Faixa de Investimento", "")

    flags_all: list[str] = []
    mn, mx, f = parse_investment_range(inv_text)
    flags_all.extend(f)

    franchise_fee = parse_money(franchise_fee_text) if franchise_fee_text else None
    working_cap = parse_money(working_cap_text) if working_cap_text else None

    own_units = first_int(fields.get("Unidades próprias", ""))
    franchised_units = first_int(fields.get("Unidades franqueadas", ""))
    total_units = None
    if own_units is not None and franchised_units is not None:
        total_units = own_units + franchised_units
    elif franchised_units is not None:
        total_units = franchised_units

    founded = first_int(fields.get("Fundação", ""))
    franchise_start = first_int(fields.get("Início da franquia", ""))

    business_models = build_business_models(fields, flags_all)

    investment_tier = None
    if tier_text and "não informado" not in tier_text.lower():
        m = re.search(r"R\$\s*([\d.,]+\s*(?:mil|milh\w+)?)", tier_text, re.IGNORECASE)
        if m:
            investment_tier = f"Até R$ {m.group(1).strip()}"
        else:
            investment_tier = tier_text

    not_informed_fields = [
        k for k, v in fields.items() if "não informado" in v.lower() or "nao informado" in v.lower()
    ]

    if len(fields) == 0:
        flags_all.append("layout_unrecognized")

    corruption = has_corruption(fields)
    if corruption:
        flags_all.append("source_data_corruption")

    seen = set()
    flags_all = [x for x in flags_all if not (x in seen or seen.add(x))]

    # fields_filled: count of top-level structured fields with valid values.
    # For BM-specific fields, count if ANY BM has a value.
    def any_bm_has(key: str) -> bool:
        return any(bm.get(key) is not None for bm in business_models)

    counted = [
        founded,
        franchise_start,
        own_units,
        franchised_units,
        mn,
        mx,
        franchise_fee,
        working_cap,
    ]
    fields_filled = sum(1 for v in counted if v is not None)
    if any_bm_has("royalties_pct") or any(bm.get("royalties_is_fixed") for bm in business_models):
        fields_filled += 1
    if any_bm_has("ad_fee_pct") or any(bm.get("ad_fee_is_fixed") for bm in business_models):
        fields_filled += 1
    if any_bm_has("avg_revenue"):
        fields_filled += 1
    if any_bm_has("avg_profit"):
        fields_filled += 1
    if any_bm_has("payback_min_months"):
        fields_filled += 1

    desc_templated = detect_templated(desc_long)
    desc_usable = bool(desc_long) and fields_filled >= 6

    quality = {
        "has_logo": bool(logo_url),
        "has_description_long": bool(desc_long),
        "has_description_short": bool(desc_short),
        "has_investment": mn is not None,
        "has_units": franchised_units is not None,
        "has_payback": any_bm_has("payback_min_months"),
        "bm_count": len(business_models),
        "fields_extracted": len(fields),
        "fields_total_known": 13,
        "fields_filled": fields_filled,
        "fields_not_informed": not_informed_fields,
        "description_usable": desc_usable,
        "description_appears_templated": desc_templated,
        "layout_unrecognized": "layout_unrecognized" in flags_all,
        "has_corruption": corruption,
        "parser_flags": flags_all,
    }

    return {
        "slug": slug,
        "name": name,
        "url_source": f"https://encontresuafranquia.com.br/franquia/{slug}/",
        "scraped_at": parsed_at,
        "logo_url": logo_url,
        "description_short": desc_short,
        "description_long": desc_long,
        "founded_year": founded,
        "franchise_start_year": franchise_start,
        "own_units": own_units,
        "franchised_units": franchised_units,
        "total_units": total_units,
        "min_investment": mn,
        "max_investment": mx,
        "investment_range_text": inv_text or None,
        "franchise_fee": franchise_fee,
        "franchise_fee_text": franchise_fee_text or None,
        "working_capital": working_cap,
        "working_capital_text": working_cap_text or None,
        "investment_tier": investment_tier,
        "business_models": business_models,
        "_quality_flags": quality,
        "_raw_fields": fields,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slugs", help="comma-separated; default = all in cache")
    ap.add_argument("--limit", type=int, help="limit count")
    args = ap.parse_args()

    if args.slugs:
        slugs = [s.strip() for s in args.slugs.split(",")]
        files = [CACHE / f"{s}.html" for s in slugs]
        files = [f for f in files if f.exists()]
    else:
        files = sorted(CACHE.glob("*.html"))

    if args.limit:
        files = files[: args.limit]

    print(f"Parsing {len(files)} HTML files…")
    ok, err = 0, 0
    err_samples = []
    for f in files:
        slug = f.stem
        try:
            data = parse_one(slug, f.read_text(encoding="utf-8", errors="replace"))
            (PARSED / f"{slug}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            ok += 1
        except Exception as e:
            err += 1
            if len(err_samples) < 5:
                err_samples.append((slug, str(e)[:120]))

    print(f"Parsed: ok={ok} err={err}")
    if err_samples:
        for s, m in err_samples:
            print(f"  {s}: {m}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
