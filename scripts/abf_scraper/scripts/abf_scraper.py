#!/usr/bin/env python3
"""
ABF Portal Scraper — Mercado Franquia
Extrai dados estruturados das 192 fichas ativas em
franquias.portaldofranchising.com.br para enriquecimento do DB.

Uso:
    python3 abf_scraper.py discover           # 1) descobre slugs varrendo segmentos
    python3 abf_scraper.py fetch              # 2) baixa todas as fichas pra cache
    python3 abf_scraper.py parse              # 3) parseia cache e gera JSONs
    python3 abf_scraper.py download-assets    # 4) baixa imagens
    python3 abf_scraper.py all                # tudo de uma vez

Estrutura:
    output/
      franchises_index.json     -- {slug, source_url, segment} por franquia
      parsed/{slug}.json        -- dados estruturados (modelos, descrição, imagens)
      assets/{slug}/*.jpg|png   -- imagens baixadas
      report.json               -- estatísticas e erros do batch

Premissas:
- HTML do portal é "consistente" — mesma estrutura em todas as 192 fichas
- pageModel ocupa ~28MB de lixo .NET serializado; HTML real são ~100KB depois de remover
- Tabelas financeiras seguem padrão: 4 linhas (Capital instalação, Taxa franquia, Capital giro, Investimento total)
- Cada modelo de negócio gera 1 bloco completo no HTML
"""
import argparse
import html
import json
import os
import re
import ssl
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional

import certifi
from bs4 import BeautifulSoup

# SSL context com bundle do certifi pra evitar
# CERTIFICATE_VERIFY_FAILED em macOS (Python framework usa cacert antigo).
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT = Path(__file__).parent.parent  # /home/claude/abf_scraper
OUTPUT = ROOT / "output"
HTML_CACHE = ROOT / "html_cache"
ASSETS = ROOT / "assets"

OUTPUT.mkdir(exist_ok=True)
(OUTPUT / "parsed").mkdir(exist_ok=True)
HTML_CACHE.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
BASE = "https://franquias.portaldofranchising.com.br"

SEGMENTS = [
    ("alimentacao",                            "Alimentação"),
    ("casa-e-construcao",                      "Casa e Construção"),
    ("comunicacao-informatica-e-eletronicos",  "Comunicação, Informática e Eletrônicos"),
    ("servicos-educacionais",                  "Educação"),
    ("entretenimento-e-lazer",                 "Entretenimento e Lazer"),
    ("hotelaria-e-turismo",                    "Hotelaria e Turismo"),
    ("limpeza-e-conservacao",                  "Limpeza e Conservação"),
    ("moda",                                   "Moda"),
    ("saude-beleza-e-bem-estar",               "Saúde, Beleza e Bem-Estar"),
    ("servicos-automotivos",                   "Serviços Automotivos"),
    ("servicos-e-outros-negocios",             "Serviços e Outros Negócios"),
]

# slugs que aparecem nas listagens mas são páginas-categoria, não fichas
JUNK_SLUGS = {
    "franquia-alimentacao", "franquia-de-alimentacao", "franquia-de-servicos",
    "franquia-de-moda", "franquia-moda", "franquia-de-comunicacao",
    "franquia-casa", "franquia-comunicacao", "franquia-de-limpeza",
    "franquia-educacao", "franquia-entretenimento", "franquia-hotelaria",
    "franquia-saude", "franquia-de-saude", "franquia-automotivos",
    "franquia-servicos", "franquia-limpeza",
}


# ═══════════════════════════════════════════════════════════════════
# Fetcher
# ═══════════════════════════════════════════════════════════════════

def http_get(url: str, timeout: int = 30) -> Optional[str]:
    """GET simples com user-agent. Retorna None em erro."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            data = resp.read()
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin-1")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ! HTTP error: {e}")
        return None


def http_get_binary(url: str, timeout: int = 30) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ! HTTP error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# 1. DISCOVERY — varre os 11 segmentos pra montar o índice
# ═══════════════════════════════════════════════════════════════════

def discover() -> list[dict]:
    """Retorna lista de {slug, segment, segment_name, source_url}."""
    by_slug: dict[str, dict] = {}

    for seg_slug, seg_name in SEGMENTS:
        url = f"{BASE}/franquias-de-{seg_slug}/"
        print(f"[discover] {seg_name}…")
        html = http_get(url)
        if html is None:
            continue

        # extrai todos os hrefs apontando pra fichas
        slugs = set(re.findall(
            r'href="https://franquias\.portaldofranchising\.com\.br/(franquia-[^"/]+)/?"',
            html
        ))
        # filtrar páginas-categoria
        slugs = slugs - JUNK_SLUGS
        # filtrar slugs que terminam com o próprio segmento (genéricos)
        bad_suffix = f"-{seg_slug}".replace("-e-", "-e-")  # heurística simples
        slugs = {s for s in slugs if s != f"franquia-{seg_slug}"}

        for slug in slugs:
            # se já vimos esse slug em outro segmento, mantemos o primeiro (segmento principal)
            if slug not in by_slug:
                by_slug[slug] = {
                    "slug": slug,
                    "segment": seg_slug,
                    "segment_name": seg_name,
                    "source_url": f"{BASE}/{slug}/",
                }

        print(f"    encontradas {len(slugs)} fichas (total único até agora: {len(by_slug)})")
        time.sleep(2)

    franchises = sorted(by_slug.values(), key=lambda x: x["slug"])
    out = OUTPUT / "franchises_index.json"
    out.write_text(json.dumps(franchises, ensure_ascii=False, indent=2))
    print(f"\n[discover] {len(franchises)} fichas salvas em {out}")
    return franchises


# ═══════════════════════════════════════════════════════════════════
# 2. FETCH — baixa cada ficha pro cache local
# ═══════════════════════════════════════════════════════════════════

def fetch_all(skip_existing: bool = True):
    index_path = OUTPUT / "franchises_index.json"
    if not index_path.exists():
        print("! Rode `discover` primeiro")
        return
    franchises = json.loads(index_path.read_text())

    successes, failures = 0, []
    for i, f in enumerate(franchises, 1):
        cache_path = HTML_CACHE / f"{f['slug']}.html"
        if skip_existing and cache_path.exists() and cache_path.stat().st_size > 1000:
            successes += 1
            continue

        print(f"[fetch {i}/{len(franchises)}] {f['slug']}")
        html = http_get(f["source_url"])
        if html is None:
            failures.append(f["slug"])
            continue
        cache_path.write_text(html)
        successes += 1
        time.sleep(2)

    print(f"\n[fetch] {successes} ok / {len(failures)} falhas")
    if failures:
        (OUTPUT / "fetch_failures.json").write_text(json.dumps(failures, indent=2))


# ═══════════════════════════════════════════════════════════════════
# 3. PARSE — extrai dados estruturados de cada HTML cacheado
# ═══════════════════════════════════════════════════════════════════

def clean_html(raw: str) -> str:
    """Remove o pageModel de 28MB que polui o documento."""
    pm_start = raw.find("window.pageModel = {")
    if pm_start < 0:
        return raw
    pm_end = raw.find("//-->", pm_start)
    if pm_end < 0:
        pm_end = raw.find("</script>", pm_start)
    if pm_end < 0:
        return raw
    return raw[:pm_start - 50] + raw[pm_end:]


# ─── parsers de campos individuais ──────────────────────────────────

def _to_int_money(s: str) -> Optional[int]:
    """'64.900' -> 64900, '290.000' -> 290000, '290.000 a 525.000' -> 290000 (min)"""
    if not s: return None
    s = s.split("a")[0].strip()  # pegar só o min se for range
    s = re.sub(r"[^\d]", "", s)  # remover (Fixo), pontos, espaços
    try:
        return int(s) if s else None
    except ValueError:
        return None


def _money_range(s: str) -> tuple[Optional[int], Optional[int]]:
    """'290.000 a 525.000' -> (290000, 525000); '64.900' -> (64900, 64900)"""
    if not s: return (None, None)
    s = s.replace("(Fixo)", "").strip()
    parts = re.split(r"\s*a\s+", s)
    if len(parts) == 1:
        v = _to_int_money(parts[0])
        return (v, v)
    return (_to_int_money(parts[0]), _to_int_money(parts[1]))


def _area_range(s: str) -> tuple[Optional[float], Optional[float]]:
    """'de 12 a 15 m²' -> (12, 15); 'de 90 a 150 m²' -> (90, 150)"""
    if not s: return (None, None)
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums: return (None, None)
    if len(nums) == 1: return (float(nums[0]), float(nums[0]))
    return (float(nums[0]), float(nums[1]))


def _payback_months(s: str) -> tuple[Optional[int], Optional[int]]:
    """'de 18 a 24 meses' -> (18, 24)"""
    if not s: return (None, None)
    nums = re.findall(r"\d+", s)
    if not nums: return (None, None)
    if len(nums) == 1: return (int(nums[0]), int(nums[0]))
    return (int(nums[0]), int(nums[1]))


def _extract_section_text(html_block: str) -> Optional[str]:
    """Converte um bloco HTML em texto limpo preservando paragrafos.

    Used pra detailed_description e ideal_franchisee_profile.
    - <br /> -> \n
    - </p> -> \n\n
    - <img> e outras tags -> removidas
    - HTML entities -> decoded
    - whitespace -> normalizado
    """
    if not html_block:
        return None
    body = re.sub(r"<br\s*/?>", "\n", html_block, flags=re.IGNORECASE)
    body = re.sub(r"</p>", "\n\n", body, flags=re.IGNORECASE)
    body = re.sub(r"<[^>]+>", "", body)
    body = html.unescape(body)
    # normaliza whitespace mas preserva quebras de paragrafo
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n[ \t]+", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = body.strip()
    return body if body else None


def _kv_following(text: str, label: str) -> Optional[str]:
    """encontra `label\\nvalor` no texto."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == label and i + 1 < len(lines):
            return lines[i + 1].strip()
    return None


# ─── parser principal de uma ficha ──────────────────────────────────

def parse_franchise(slug: str, raw_html: str, segment_info: dict) -> dict:
    cleaned = clean_html(raw_html)
    soup = BeautifulSoup(cleaned, "lxml")

    # remover scripts, styles e o menu lateral pra não poluir
    for tag in soup.find_all(["script", "style", "nav", "footer"]):
        tag.decompose()

    result: dict = {
        "slug": slug,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "source_url": segment_info["source_url"],
        "segment_abf_id": segment_info["segment"],
        "segment_abf_name": segment_info["segment_name"],
    }

    # 1. nome (title h1)
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(" ", strip=True)
        # "FRANQUIA CACAU SHOW" -> "Cacau Show"
        name = re.sub(r"^FRANQUIA\s+", "", name, flags=re.IGNORECASE)
        result["name"] = name.strip().title() if name.isupper() else name

    # 2. meta description (vai pro campo description provisório)
    meta = soup.find("meta", {"name": "description"})
    if meta and meta.get("content"):
        result["meta_description"] = meta["content"].strip()

    # 3. tagline (title da página tem padrão "Franquia X - tagline")
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        m = re.match(r"Franquia\s+[^-]+-\s*(.+)", title, re.IGNORECASE)
        if m:
            result["tagline"] = m.group(1).strip()

    # 4. data atualização ABF
    text_full = soup.get_text("\n", strip=True)
    m_date = re.search(r"Dados atualizados pela franquia em (\d{2}/\d{2}/\d{4})", text_full)
    if m_date:
        result["abf_updated_at"] = m_date.group(1)

    # 5. site oficial (link com utm)
    link = soup.find("a", href=re.compile(r"utm_source=portaldofranchising"))
    if link:
        href = link["href"]
        # limpar UTMs
        result["scraped_website"] = href.split("?")[0]
        result["scraped_website_with_utm"] = href

    # 6. logo: variações de path observadas:
    #    /abf/logomarca/X.svg | /logomarca/X.png | /logo.jpg | /logotipo/X.png
    logo_pattern = re.compile(
        r'https://static\.portaldofranchising\.com\.br/'
        r'central/material-de-clientes/[^/]+/'
        r'(?:abf/logomarca|logomarca|logotipo|logo)/?'
        r'[^"\'>\s)]+\.(?:svg|png|jpg|jpeg|webp)',
        re.IGNORECASE
    )
    logo_match = logo_pattern.search(cleaned)
    if logo_match:
        result["logo_url"] = logo_match.group(0)
    else:
        # fallback: qualquer URL com "logo" no path da pasta cliente
        fallback = re.search(
            r'https://static\.portaldofranchising\.com\.br/'
            r'central/material-de-clientes/[^/]+/[^"\'>\s)]*logo[^"\'>\s)]*\.(?:svg|png|jpg|jpeg|webp)',
            cleaned, re.IGNORECASE
        )
        if fallback:
            result["logo_url"] = fallback.group(0)

    # 7. og:image (= logo na maioria das fichas, não é banner real)
    og = soup.find("meta", {"property": "og:image"})
    if og and og.get("content"):
        result["og_image"] = og["content"]

    # 7b. banner real — <img class="main-img lazyload" data-src="...">
    # Naming variavel: capa-{date}.jpg, testeira-new.jpg, header-...jpg, etc.
    # Cobertura ~92% das fichas; anchor robusto e a classe CSS, nao filename.
    # data-src e usado por causa de lazy loading (src fica vazio ou placeholder).
    banner_img = soup.select_one("img.main-img.lazyload")
    if banner_img:
        banner_src = banner_img.get("data-src", "")
        if banner_src.startswith("https://"):
            result["banner_url"] = banner_src

    # 8. galeria — imgs em /mini-site/ com sufixo numérico
    gallery = []
    seen = set()
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "static.portaldofranchising" in src and "/mini-site/" in src and src not in seen:
            gallery.append(src)
            seen.add(src)
    result["gallery_urls"] = gallery

    # 8b. video_url — primeiro YouTube/Vimeo embedado no carousel-main-video
    # Naming variavel: as URLs aparecem como text content em script JS que monta
    # iframes dinamicos. Pegamos a primeira (schema do Franchise.videoUrl e text
    # unico, frontend renderiza 1 video no hero).
    m_video = re.search(
        r'(?:https?://)?(?:www\.)?'
        r'(youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+|vimeo\.com/\d+)',
        cleaned,
    )
    if m_video:
        url = m_video.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        result["video_url"] = url

    # 8c. detailed_description — bloco "Sobre a franquia X"
    # Texto editorial rico (1-2K chars), separado do meta_description (155 chars).
    # Vai pra Franchise.detailedDescription. Limite 5000 chars.
    m_desc = re.search(
        r'<h2[^>]*>Sobre a franquia[^<]*</h2>(.*?)'
        r'(?:<h2[^>]*>|<hr\s+class="border-separator)',
        cleaned,
        re.DOTALL | re.IGNORECASE,
    )
    if m_desc:
        body = _extract_section_text(m_desc.group(1))
        # Threshold 200 chars: descarta placeholder tipo "Conheca abaixo..." +
        # imagem. Aceita so texto editorial real.
        if body and len(body) >= 200:
            result["detailed_description"] = body[:5000] + (
                "..." if len(body) > 5000 else ""
            )

    # 8d. ideal_franchisee_profile — bloco "Perfil do franqueado X"
    # Mesma tecnica do 8c, marker diferente. Vai pra Franchise.idealFranchiseeProfile.
    m_profile = re.search(
        r'<h2[^>]*>Perfil do franqueado[^<]*</h2>(.*?)'
        r'(?:<h2[^>]*>|<hr\s+class="border-separator)',
        cleaned,
        re.DOTALL | re.IGNORECASE,
    )
    if m_profile:
        body = _extract_section_text(m_profile.group(1))
        # Threshold 150 chars: descarta intro curta ("Conheca o perfil...") +
        # imagem. Frontend renderiza skip-if-null pra evitar bloco confuso.
        if body and len(body) >= 150:
            result["ideal_franchisee_profile"] = body[:5000] + (
                "..." if len(body) > 5000 else ""
            )

    # 9. modelos de negócio — bloco "Investimento para um/uma X"
    # cada bloco tem tabela financeira + retorno + sede + unidades + área + propaganda + royalties
    models = []

    # achar âncoras "Investimento para um/uma X"
    for h_text in re.finditer(r"Investimento para (?:um|uma)\s+([A-Za-zÀ-ÿ ]+?)(?:\n|$)", text_full):
        model_name = h_text.group(1).strip()
        # bloco entre essa âncora e a próxima (ou fim)
        block_start = h_text.end()
        next_match = re.search(r"Investimento para (?:um|uma)\s+", text_full[block_start:])
        block_end = block_start + next_match.start() if next_match else len(text_full)
        block = text_full[block_start:block_end]

        capital_inst = _kv_following(block, "Capital para instalação")
        taxa_franquia = _kv_following(block, "Taxa de franquia")
        capital_giro = _kv_following(block, "Capital de giro")
        invest_total = _kv_following(block, "Investimento total")
        retorno = _kv_following(block, "Retorno do investimento")
        sede = _kv_following(block, "Sede")
        unidades = _kv_following(block, "Número total de unidades")
        # área tem label dinâmico ("Área da Quiosque", "Área da loja", "Área de quiosque")
        area = None
        m_area = re.search(r"Área (?:da|de|do)\s+\S+\s*\n([^\n]+)", block)
        if m_area:
            area = m_area.group(1).strip()

        # propaganda (taxa + base de cálculo) — primeiro bloco de Taxa/Base após "Taxa de propaganda"
        prop_taxa, prop_base, prop_obs = None, None, None
        royal_taxa, royal_base, royal_obs = None, None, None
        # split entre "Taxa de propaganda" e "ROYALTIES"
        m_prop = re.search(r"Taxa de propaganda(.*?)(?:ROYALTIES|$)", block, re.DOTALL)
        if m_prop:
            prop_block = m_prop.group(1)
            prop_taxa = _kv_following(prop_block, "Taxa")
            prop_base = _kv_following(prop_block, "Base de cálculo")
            prop_obs  = _kv_following(prop_block, "Observação")
        m_royal = re.search(r"ROYALTIES(.*?)(?:Clique aqui|Comunicado Importante|Investimento para|$)", block, re.DOTALL)
        if m_royal:
            royal_block = m_royal.group(1)
            royal_taxa = _kv_following(royal_block, "Taxa")
            royal_base = _kv_following(royal_block, "Base de cálculo")
            royal_obs  = _kv_following(royal_block, "Observação")

        invest_min, invest_max = _money_range(invest_total) if invest_total else (None, None)
        capital_inst_min, capital_inst_max = _money_range(capital_inst) if capital_inst else (None, None)
        taxa_min, taxa_max = _money_range(taxa_franquia) if taxa_franquia else (None, None)
        giro_min, giro_max = _money_range(capital_giro) if capital_giro else (None, None)
        payback_min, payback_max = _payback_months(retorno) if retorno else (None, None)
        area_min, area_max = _area_range(area) if area else (None, None)

        unidades_int = None
        if unidades:
            try:
                unidades_int = int(re.sub(r"[^\d]", "", unidades.split("Todas")[0]))
            except ValueError:
                pass

        models.append({
            "name": model_name,
            "headquarter": sede,
            "total_units": unidades_int,
            "capital_installation_min": capital_inst_min,
            "capital_installation_max": capital_inst_max,
            "franchise_fee_min": taxa_min,
            "franchise_fee_max": taxa_max,
            "working_capital_min": giro_min,
            "working_capital_max": giro_max,
            "investment_total_min": invest_min,
            "investment_total_max": invest_max,
            "payback_months_min": payback_min,
            "payback_months_max": payback_max,
            "area_m2_min": area_min,
            "area_m2_max": area_max,
            "advertising_fee_rate": prop_taxa,
            "advertising_fee_base": prop_base,
            "advertising_fee_observation": prop_obs,
            "royalties_rate": royal_taxa,
            "royalties_base": royal_base,
            "royalties_observation": royal_obs,
        })

    result["business_models"] = models

    # 10. agregados (mín/máx considerando todos os modelos)
    if models:
        all_mins = [m["investment_total_min"] for m in models if m["investment_total_min"]]
        all_maxs = [m["investment_total_max"] for m in models if m["investment_total_max"]]
        all_units = [m["total_units"] for m in models if m["total_units"]]
        result["minimum_investment"] = min(all_mins) if all_mins else None
        result["maximum_investment"] = max(all_maxs) if all_maxs else None
        result["total_units"] = sum(all_units) if all_units else None
        result["headquarter"] = models[0].get("headquarter")

    return result


def parse_all(slugs_filter: Optional[set] = None):
    index_path = OUTPUT / "franchises_index.json"
    franchises = json.loads(index_path.read_text())

    if slugs_filter:
        franchises = [f for f in franchises if f["slug"] in slugs_filter]
        print(f"[parse] filtro: {len(franchises)} fichas em {sorted(slugs_filter)}")

    parsed_dir = OUTPUT / "parsed"
    successes, failures = 0, []

    for f in franchises:
        cache = HTML_CACHE / f"{f['slug']}.html"
        if not cache.exists() or cache.stat().st_size < 1000:
            failures.append((f["slug"], "no_cache"))
            continue

        try:
            raw = cache.read_text()
            data = parse_franchise(f["slug"], raw, f)
            (parsed_dir / f"{f['slug']}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            successes += 1
        except Exception as e:
            print(f"  ! parse error {f['slug']}: {e}")
            failures.append((f["slug"], str(e)))

    print(f"\n[parse] {successes} ok / {len(failures)} falhas")
    if failures:
        (OUTPUT / "parse_failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2)
        )

    # gerar report consolidado
    aggregate = []
    for slug_file in parsed_dir.glob("*.json"):
        d = json.loads(slug_file.read_text())
        aggregate.append({
            "slug": d["slug"],
            "name": d.get("name"),
            "segment": d.get("segment_abf_name"),
            "models_count": len(d.get("business_models", [])),
            "min_investment": d.get("minimum_investment"),
            "max_investment": d.get("maximum_investment"),
            "total_units": d.get("total_units"),
            "gallery_count": len(d.get("gallery_urls", [])),
            "has_logo": bool(d.get("logo_url")),
            "has_banner": bool(d.get("banner_url")),
            "abf_updated_at": d.get("abf_updated_at"),
        })
    aggregate.sort(key=lambda x: x["slug"])
    (OUTPUT / "report.json").write_text(
        json.dumps({"total": len(aggregate), "franchises": aggregate}, ensure_ascii=False, indent=2)
    )

    print(f"[parse] report consolidado em {OUTPUT/'report.json'}")


# ═══════════════════════════════════════════════════════════════════
# 4. DOWNLOAD ASSETS — baixa imagens de cada franquia
# ═══════════════════════════════════════════════════════════════════

def download_assets():
    parsed_dir = OUTPUT / "parsed"
    total_dl, total_skip, total_err = 0, 0, 0

    for json_file in sorted(parsed_dir.glob("*.json")):
        d = json.loads(json_file.read_text())
        slug = d["slug"]
        urls = []
        if d.get("logo_url"): urls.append(("logo", d["logo_url"]))
        if d.get("banner_url") and d["banner_url"] not in [u[1] for u in urls]:
            urls.append(("banner", d["banner_url"]))
        if d.get("og_image") and d["og_image"] not in [u[1] for u in urls]:
            urls.append(("og", d["og_image"]))
        for i, u in enumerate(d.get("gallery_urls", [])):
            urls.append((f"gallery_{i:02d}", u))

        if not urls:
            continue

        slug_dir = ASSETS / slug
        slug_dir.mkdir(exist_ok=True)

        for kind, url in urls:
            ext = url.split(".")[-1].split("?")[0]
            dest = slug_dir / f"{kind}.{ext}"
            if dest.exists() and dest.stat().st_size > 0:
                total_skip += 1
                continue
            data = http_get_binary(url)
            if data is None:
                total_err += 1
                continue
            dest.write_bytes(data)
            total_dl += 1
            time.sleep(0.5)

    print(f"\n[download-assets] baixadas: {total_dl}, já existiam: {total_skip}, erros: {total_err}")


# ═══════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["discover", "fetch", "parse", "download-assets", "all"])
    parser.add_argument(
        "--slugs",
        help="Comma-separated slug filter (parse only). Ex: --slugs franquia-cacau-show-valor,franquia-altenburg",
    )
    args = parser.parse_args()

    slugs_filter = None
    if args.slugs:
        slugs_filter = {s.strip() for s in args.slugs.split(",") if s.strip()}

    if args.command in ("discover", "all"):
        discover()
    if args.command in ("fetch", "all"):
        fetch_all()
    if args.command in ("parse", "all"):
        parse_all(slugs_filter=slugs_filter)
    if args.command in ("download-assets", "all"):
        download_assets()
