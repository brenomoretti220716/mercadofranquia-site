#!/usr/bin/env python3
"""Comprime os HTMLs cacheados removendo o pageModel de 28MB."""
from pathlib import Path

CACHE = Path(__file__).parent.parent / "html_cache"

def clean(content: str) -> str:
    pm_start = content.find("window.pageModel = {")
    if pm_start < 0:
        return content
    pm_end = content.find("//-->", pm_start)
    if pm_end < 0:
        pm_end = content.find("</script>", pm_start)
    if pm_end < 0:
        return content
    return content[:pm_start - 50] + content[pm_end:]

if __name__ == "__main__":
    total_before, total_after, count = 0, 0, 0
    for f in sorted(CACHE.glob("*.html")):
        raw = f.read_text()
        if len(raw) < 1_000_000:
            continue  # já comprimido
        cleaned = clean(raw)
        f.write_text(cleaned)
        total_before += len(raw)
        total_after += len(cleaned)
        count += 1
    print(f"Comprimidos {count} arquivos: {total_before/1e6:.0f} MB -> {total_after/1e6:.1f} MB")
