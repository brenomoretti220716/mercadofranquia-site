#!/usr/bin/env python3
"""apply_post_enrichment.py — rename dirs + rewrite URLs + populate bannerUrl.

Roda no EC2. 3 fases separadas pra evitar dessincronizacao DB/filesystem:

  Fase 1 — Preflight (sempre dry-run):
    - Lista renames de dirs (franquia-{abf_slug} -> {db_slug})
    - Lista URL updates pendentes (logoUrl, galleryUrls hot-linked)
    - Lista bannerUrl sets (DB.bannerUrl IS NULL e file existe)

  Fase 2 — Filesystem (apenas com --apply):
    - mv dirs no /uploads/abf/. Skip se dst ja existe.
    - Se algum mv falhar, ABORT antes de tocar DB.

  Fase 3 — DB (apenas se Fase 2 completou):
    - Valida file existe via os.path antes de cada UPDATE
    - UPDATE em transacao unica BEGIN/COMMIT
    - Pula items individuais se file ausente (nao rompe batch)

Source-of-truth do mapping abf_slug -> db_slug: enrichment_diff.json
gerado pelo apply_enrichment.py.

Uso (no EC2):
    cd /tmp/abf_apply_workspace/scripts
    DATABASE_URL=$(sudo grep -oE 'Environment=DATABASE_URL=[^[:space:]]+' \\
        /etc/systemd/system/mf-api.service | sed 's|Environment=DATABASE_URL=||') \\
    /home/ubuntu/mf-api/bin/python apply_post_enrichment.py            # dry-run
    DATABASE_URL=... apply_post_enrichment.py --apply                  # mutate
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text


# ============================================================================
# Paths (EC2 layout)
# ============================================================================
ASSETS_ROOT = Path("/home/ubuntu/mercadofranquia-api/uploads/abf")
WORKSPACE = Path(__file__).resolve().parent / "abf_scraper"
ENRICHMENT_DIFF = WORKSPACE / "output" / "enrichment_diff.json"
PARSED_DIR = WORKSPACE / "output" / "parsed"

URL_REL_PREFIX = "/uploads/abf"
HOT_LINK_HOST = "static.portaldofranchising"


# ============================================================================
# Helpers
# ============================================================================
def find_file_by_stem(dir_: Path, stem: str) -> Optional[Path]:
    """Retorna primeiro file `{stem}.{ext}` em dir_, ou None."""
    if not dir_.is_dir():
        return None
    for p in dir_.iterdir():
        if p.is_file() and p.stem == stem:
            return p
    return None


def list_gallery_files(dir_: Path) -> dict[int, Path]:
    """Retorna {idx: Path} pros gallery_NN.{ext}."""
    out: dict[int, Path] = {}
    if not dir_.is_dir():
        return out
    for p in dir_.iterdir():
        if p.is_file() and p.stem.startswith("gallery_"):
            try:
                idx = int(p.stem.replace("gallery_", ""))
                out[idx] = p
            except ValueError:
                continue
    return out


# ============================================================================
# Fase 1: Preflight (dry-run safe — nao toca filesystem nem DB)
# ============================================================================
def preflight(
    items: list[dict], db_state: dict[str, dict]
) -> tuple[list, list, list, list]:
    """Computa todas as acoes sem aplicar."""
    renames: list[tuple[Path, Path]] = []
    logo_updates: list[tuple[str, str, str]] = []  # (db_slug, old, new)
    gallery_updates: list[tuple[str, str]] = []  # (db_slug, new_json)
    banner_sets: list[tuple[str, str]] = []  # (db_slug, new_url)

    for it in items:
        if it["match_status"] == "skipped_claimed":
            continue

        abf_slug = it["abf_slug"]
        db_slug = it.get("match_db_slug") or (
            it.get("insert_payload") or {}
        ).get("slug")
        if not db_slug:
            continue

        src_dir = ASSETS_ROOT / abf_slug
        dst_dir = ASSETS_ROOT / db_slug

        # Source dir pra ler files (pre-rename)
        if abf_slug == db_slug:
            scan_dir = src_dir  # nada a renomear
        else:
            if src_dir.is_dir() and not dst_dir.exists():
                renames.append((src_dir, dst_dir))
            scan_dir = src_dir if src_dir.is_dir() else dst_dir

        # ---- Logo: reescrever se DB tem URL hot-linked e file existe ----
        cur_logo = (db_state.get(db_slug) or {}).get("logoUrl") or ""
        if HOT_LINK_HOST in cur_logo:
            logo_file = find_file_by_stem(scan_dir, "logo")
            if logo_file:
                ext = logo_file.suffix.lstrip(".")
                new_url = f"{URL_REL_PREFIX}/{db_slug}/logo.{ext}"
                logo_updates.append((db_slug, cur_logo, new_url))

        # ---- Gallery: reescrever JSON list se DB tem URLs hot-linked ----
        cur_gallery = (db_state.get(db_slug) or {}).get("galleryUrls") or ""
        if HOT_LINK_HOST in cur_gallery:
            parsed_path = PARSED_DIR / f"{abf_slug}.json"
            if parsed_path.exists():
                parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
                abf_gallery = parsed.get("gallery_urls") or []
                files_by_idx = list_gallery_files(scan_dir)
                new_urls = []
                for i, _abf_url in enumerate(abf_gallery):
                    if i in files_by_idx:
                        ext = files_by_idx[i].suffix.lstrip(".")
                        new_urls.append(
                            f"{URL_REL_PREFIX}/{db_slug}/gallery_{i:02d}.{ext}"
                        )
                if new_urls:
                    gallery_updates.append(
                        (db_slug, json.dumps(new_urls, ensure_ascii=False))
                    )

        # ---- Banner: SET se DB.bannerUrl IS NULL OU rewrite se hot-linked ----
        # Patch A (refresh): inicialmente era so "set if null". Refresh popula
        # bannerUrl com URL portaldofranchising via override, entao precisa
        # rewrite tambem (mesma logica de logo/gallery).
        cur_banner = (db_state.get(db_slug) or {}).get("bannerUrl") or ""
        if cur_banner == "" or HOT_LINK_HOST in cur_banner:
            banner_file = find_file_by_stem(scan_dir, "banner")
            if banner_file:
                ext = banner_file.suffix.lstrip(".")
                banner_sets.append(
                    (db_slug, f"{URL_REL_PREFIX}/{db_slug}/banner.{ext}")
                )

    return renames, logo_updates, gallery_updates, banner_sets


# ============================================================================
# Fase 2: Filesystem (mv dirs)
# ============================================================================
def apply_filesystem(renames: list[tuple[Path, Path]]) -> int:
    """Renomeia dirs. ABORT se qualquer falha. Retorna count completados."""
    completed = 0
    for src, dst in renames:
        if not src.is_dir():
            print(f"  SKIP {src.name}: source nao existe (provavelmente ja renomeado)")
            continue
        if dst.exists():
            print(f"  SKIP {src.name}: destino {dst.name} ja existe")
            continue
        try:
            src.rename(dst)
            completed += 1
            print(f"  OK   {src.name} -> {dst.name}")
        except Exception as e:
            print(f"  FAIL {src.name} -> {dst.name}: {e}", file=sys.stderr)
            print(f"  ABORTED. {completed} ja renomeados.", file=sys.stderr)
            sys.exit(2)
    return completed


# ============================================================================
# Fase 3: DB updates (transacao)
# ============================================================================
def apply_db(
    engine,
    logo_updates: list[tuple[str, str, str]],
    gallery_updates: list[tuple[str, str]],
    banner_sets: list[tuple[str, str]],
) -> dict[str, int]:
    """UPDATE em transacao. Valida file antes de cada SET."""
    stats = {"logo_ok": 0, "logo_skip": 0, "gallery_ok": 0, "banner_ok": 0, "banner_skip": 0}
    with engine.begin() as conn:
        # Logo
        for db_slug, _old, new_url in logo_updates:
            file_path = ASSETS_ROOT / db_slug / Path(new_url).name
            if not file_path.exists():
                print(f"  WARN logo {db_slug}: file {file_path.name} missing — skip")
                stats["logo_skip"] += 1
                continue
            conn.execute(
                text('UPDATE "Franchise" SET "logoUrl" = :url WHERE slug = :slug'),
                {"url": new_url, "slug": db_slug},
            )
            stats["logo_ok"] += 1

        # Gallery
        for db_slug, new_json in gallery_updates:
            conn.execute(
                text('UPDATE "Franchise" SET "galleryUrls" = :g WHERE slug = :slug'),
                {"g": new_json, "slug": db_slug},
            )
            stats["gallery_ok"] += 1

        # Banner
        # Patch A (refresh): preflight ja gate "NULL ou hot-linked", entao
        # UPDATE nao precisa filtro adicional. WHERE slug + clause anterior
        # "AND bannerUrl IS NULL" era do deploy original (set-only).
        for db_slug, new_url in banner_sets:
            file_path = ASSETS_ROOT / db_slug / Path(new_url).name
            if not file_path.exists():
                print(f"  WARN banner {db_slug}: file {file_path.name} missing — skip")
                stats["banner_skip"] += 1
                continue
            res = conn.execute(
                text('UPDATE "Franchise" SET "bannerUrl" = :url WHERE slug = :slug'),
                {"url": new_url, "slug": db_slug},
            )
            if res.rowcount == 0:
                stats["banner_skip"] += 1
            else:
                stats["banner_ok"] += 1
    return stats


# ============================================================================
# Main
# ============================================================================
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Mutate filesystem + DB. Default: dry-run.",
    )
    p.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="Connection string (default: DATABASE_URL env).",
    )
    args = p.parse_args()

    if not args.database_url:
        print("ERROR: DATABASE_URL nao definida", file=sys.stderr)
        sys.exit(1)

    is_dry_run = not args.apply
    mode = "DRY-RUN" if is_dry_run else "APPLY"
    print(f"=== apply_post_enrichment.py — Mode: {mode} ===\n")

    # Load enrichment_diff
    if not ENRICHMENT_DIFF.exists():
        print(f"ERROR: {ENRICHMENT_DIFF} nao encontrado", file=sys.stderr)
        sys.exit(1)
    diff = json.loads(ENRICHMENT_DIFF.read_text(encoding="utf-8"))
    items = diff["items"]
    print(f"[init] Loaded {len(items)} items from enrichment_diff.json")

    # Load DB state (read-only — dry-run nao muta nada)
    engine = create_engine(args.database_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text('SELECT slug, "logoUrl", "galleryUrls", "bannerUrl" FROM "Franchise"')
        ).all()
    db_state = {r._mapping["slug"]: dict(r._mapping) for r in rows}
    print(f"[init] Loaded {len(db_state)} franchises do DB")

    # ---- Fase 1: Preflight ----
    print("\n[1/3] Preflight (sem mutacao)...")
    renames, logo_updates, gallery_updates, banner_sets = preflight(items, db_state)

    print(f"  Renames de dirs:        {len(renames)}")
    print(f"  Logo URLs a reescrever: {len(logo_updates)}")
    print(f"  Gallery rows a reescrever: {len(gallery_updates)}")
    print(f"  Banner URLs a popular:  {len(banner_sets)}")

    print("\n--- Sample preview ---")
    if renames:
        print(f"\nRenames (mostrando ate 8 de {len(renames)}):")
        for src, dst in renames[:8]:
            print(f"  {src.name} -> {dst.name}")
        if len(renames) > 8:
            print(f"  ... +{len(renames) - 8} more")

    if logo_updates:
        print(f"\nLogo updates (todas {len(logo_updates)}):")
        for slug, _old, new in logo_updates:
            print(f"  {slug}: -> {new}")

    if gallery_updates:
        print(f"\nGallery updates (showing 1 of {len(gallery_updates)}):")
        slug, g_json = gallery_updates[0]
        urls = json.loads(g_json)
        print(f"  {slug}: {len(urls)} URLs")
        for u in urls[:3]:
            print(f"    {u}")
        if len(urls) > 3:
            print(f"    ... +{len(urls) - 3} more URLs")

    if banner_sets:
        print(f"\nBanner sets (mostrando 8 de {len(banner_sets)}):")
        for slug, url in banner_sets[:8]:
            print(f"  {slug}: -> {url}")
        if len(banner_sets) > 8:
            print(f"  ... +{len(banner_sets) - 8} more")

    if is_dry_run:
        print("\n--- Dry-run only. Re-run with --apply to mutate. ---")
        return

    # ---- Fase 2: Filesystem ----
    print("\n[2/3] Filesystem rename...")
    completed = apply_filesystem(renames)
    print(f"  {completed}/{len(renames)} renames completos")

    # ---- Fase 3: DB ----
    print("\n[3/3] DB updates (transacao)...")
    stats = apply_db(engine, logo_updates, gallery_updates, banner_sets)
    print(f"  Logo:    {stats['logo_ok']} OK, {stats['logo_skip']} skipped")
    print(f"  Gallery: {stats['gallery_ok']} OK")
    print(f"  Banner:  {stats['banner_ok']} OK, {stats['banner_skip']} skipped")
    print("\nDone.")


if __name__ == "__main__":
    main()
