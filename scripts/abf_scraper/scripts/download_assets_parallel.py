#!/usr/bin/env python3
"""Download paralelo de imagens das franquias.

Faz 10 downloads simultâneos. Salva em assets/{slug}/{kind}.{ext}.
"""
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
PARSED = ROOT / "output" / "parsed"
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


import ssl
import certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def download_one(url: str, dest: Path) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return (True, "skip")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
            data = r.read()
        if len(data) < 200:
            return (False, "too_small")
        dest.write_bytes(data)
        return (True, "downloaded")
    except Exception as e:
        return (False, str(e)[:60])


def main():
    # construir lista de tarefas
    tasks = []
    for json_file in sorted(PARSED.glob("*.json")):
        d = json.loads(json_file.read_text())
        slug = d["slug"]
        slug_dir = ASSETS / slug
        slug_dir.mkdir(exist_ok=True)

        if d.get("logo_url"):
            ext = d["logo_url"].split(".")[-1].split("?")[0].lower()
            if ext not in ("svg", "png", "jpg", "jpeg", "webp"):
                ext = "jpg"
            tasks.append((d["logo_url"], slug_dir / f"logo.{ext}"))

        if d.get("banner_url"):
            ext = d["banner_url"].split(".")[-1].split("?")[0].lower()
            if ext not in ("svg", "png", "jpg", "jpeg", "webp"):
                ext = "jpg"
            tasks.append((d["banner_url"], slug_dir / f"banner.{ext}"))

        for i, url in enumerate(d.get("gallery_urls", [])):
            ext = url.split(".")[-1].split("?")[0].lower()
            if ext not in ("svg", "png", "jpg", "jpeg", "webp"):
                ext = "jpg"
            tasks.append((url, slug_dir / f"gallery_{i:02d}.{ext}"))

    print(f"Total tasks: {len(tasks)}")

    # paralelizar
    ok, skip, err = 0, 0, 0
    err_samples = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(download_one, url, dest): (url, dest) for url, dest in tasks}
        done = 0
        for fut in as_completed(futures):
            success, msg = fut.result()
            done += 1
            if success and msg == "downloaded":
                ok += 1
            elif success and msg == "skip":
                skip += 1
            else:
                err += 1
                if len(err_samples) < 5:
                    err_samples.append((futures[fut][0][:80], msg))
            if done % 100 == 0:
                print(f"  {done}/{len(tasks)} | ok={ok} skip={skip} err={err}")

    print(f"\nFinal: downloaded={ok}, already_existed={skip}, errors={err}")
    if err_samples:
        print("Sample errors:")
        for url, msg in err_samples:
            print(f"  {msg}: {url}")


if __name__ == "__main__":
    main()
