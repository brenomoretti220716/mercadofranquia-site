"""URL validator for franchise video links.

Whitelist-only: apenas YouTube e Vimeo, sempre HTTPS. Rejeita qualquer outro
esquema (http, javascript, data, file) e qualquer host fora da lista pra
evitar XSS em player embed e SSRF futuro caso o backend decida fetchar.
"""
from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_VIDEO_HOSTS: frozenset[str] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "vimeo.com",
        "www.vimeo.com",
        "player.vimeo.com",
    }
)


def is_valid_video_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host in ALLOWED_VIDEO_HOSTS
