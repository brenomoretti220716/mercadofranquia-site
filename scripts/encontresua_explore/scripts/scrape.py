#!/usr/bin/env python3
"""Fetch HTML pages from EncontreSuaFranquia.

Usage:
  python scrape.py --sample 50      # uniform sample across the index
  python scrape.py --all            # all 800 fichas
  python scrape.py --slugs a,b,c    # specific slugs

Cache: /tmp/encontresua_html/{slug}.html (skipped if already present, non-empty)
Crawl delay: 10s between requests (skips don't count).
"""
import argparse
import ssl
import sys
import time
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "output" / "franchises_index.txt"
CACHE = Path("/tmp/encontresua_html")
CACHE.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DELAY = 10
SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def fetch_one(url: str, dest: Path) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 1000:
        return (True, "cached")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept-Language": "pt-BR,pt;q=0.9",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
            data = r.read()
        if len(data) < 5000:
            return (False, f"too_small ({len(data)})")
        dest.write_bytes(data)
        return (True, "downloaded")
    except Exception as e:
        return (False, str(e)[:80])


def pick_targets(args, all_urls: list[str]) -> list[str]:
    if args.slugs:
        wanted = set(s.strip() for s in args.slugs.split(","))
        return [u for u in all_urls if slug_from_url(u) in wanted]
    if args.sample:
        n = args.sample
        if n >= len(all_urls):
            return all_urls
        step = len(all_urls) / n
        return [all_urls[int(i * step)] for i in range(n)]
    if args.all:
        return all_urls
    raise SystemExit("Must pass --sample N, --all, or --slugs a,b,c")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, help="uniform sample N from index")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--slugs", help="comma-separated slugs")
    args = ap.parse_args()

    urls = [line.strip() for line in INDEX.read_text().splitlines() if line.strip()]
    print(f"Index: {len(urls)} URLs")

    targets = pick_targets(args, urls)
    print(f"Targets: {len(targets)}")

    ok_dl, ok_cache, err = 0, 0, 0
    err_samples = []
    network_attempts = 0

    for i, url in enumerate(targets, 1):
        slug = slug_from_url(url)
        dest = CACHE / f"{slug}.html"
        was_cached = dest.exists() and dest.stat().st_size > 1000

        if not was_cached and network_attempts > 0:
            time.sleep(DELAY)
        if not was_cached:
            network_attempts += 1

        success, msg = fetch_one(url, dest)
        if success:
            if msg == "cached":
                ok_cache += 1
            else:
                ok_dl += 1
        else:
            err += 1
            if len(err_samples) < 5:
                err_samples.append((slug, msg))

        if i % 10 == 0 or i == len(targets):
            print(f"  [{i}/{len(targets)}] dl={ok_dl} cache={ok_cache} err={err}")

    print(f"\nFinal: downloaded={ok_dl} | cached={ok_cache} | errors={err}")
    if err_samples:
        print("Sample errors:")
        for s, m in err_samples:
            print(f"  {s}: {m}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
