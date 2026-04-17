"""
Local-disk image upload helper.

Files are saved under `${UPLOAD_PATH}/<subdir>/<uuid><ext>` (UPLOAD_PATH env,
default `./uploads`). The function returns the **public URL path**
`/uploads/<subdir>/<filename>` — Nginx is configured to serve `/uploads/*`
directly from this directory (see `deploy/ec2/mercadofranquia.nginx`).

This mirrors the NestJS `UploadService.uploadFile()` semantics so the URLs
written into existing tables (`News.photoUrl`, `Franchise.thumbnailUrl`, etc.)
keep the same shape across both backends.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Iterable, Optional

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger("mf-api.storage")

UPLOAD_ROOT = Path(os.environ.get("UPLOAD_PATH", "./uploads")).resolve()

# Mirrors the NestJS allowed list in upload.service.ts + file-news.schema.ts.
DEFAULT_IMAGE_MIMES = (
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
)
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB

# Map mimetype -> canonical extension when the uploaded filename has none or
# carries an inconsistent extension. Falls back to the original suffix.
_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _resolve_extension(filename: Optional[str], mimetype: Optional[str]) -> str:
    """Pick a sane lowercase extension for the saved file."""
    if filename:
        ext = Path(filename).suffix.lower()
        if ext:
            return ext
    if mimetype and mimetype in _MIME_TO_EXT:
        return _MIME_TO_EXT[mimetype]
    return ""


def save_image_upload(
    upload: UploadFile,
    subdir: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    allowed_mimes: Iterable[str] = DEFAULT_IMAGE_MIMES,
) -> str:
    """Validate, persist, and return the public URL path for an image upload.

    Raises HTTPException(400) on validation failures (bad mime, too large,
    empty file). Caller is responsible for deleting the previous photo (if any)
    after a successful save.
    """
    allowed = tuple(allowed_mimes)
    if not upload.content_type or upload.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos JPEG, PNG, GIF e WebP são permitidos",
        )

    content = upload.file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O arquivo deve ter no máximo {max_bytes // (1024 * 1024)}MB",
        )

    ext = _resolve_extension(upload.filename, upload.content_type)
    name = f"{uuid.uuid4().hex}{ext}"

    # Subdir is hard-coded by the caller (e.g. "news"), so this is safe — but
    # defensively strip path traversal characters anyway.
    safe_subdir = subdir.strip("/").replace("..", "")
    dest_dir = UPLOAD_ROOT / safe_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / name
    with open(dest, "wb") as f:
        f.write(content)

    return f"/uploads/{safe_subdir}/{name}"


def delete_uploaded_file(public_url_path: Optional[str]) -> None:
    """Delete a file previously persisted by `save_image_upload`. Tolerates
    missing files / non-`/uploads/` paths — only logs warnings."""
    if not public_url_path:
        return
    if not public_url_path.startswith("/uploads/"):
        # Could be a legacy absolute URL like https://.../uploads/news/x.jpg —
        # try to extract the path portion if it ends with /uploads/<subdir>/<file>.
        idx = public_url_path.find("/uploads/")
        if idx == -1:
            logger.warning("delete_uploaded_file: not a /uploads path: %s", public_url_path)
            return
        public_url_path = public_url_path[idx:]

    rel = public_url_path[len("/uploads/"):]
    target = UPLOAD_ROOT / rel
    try:
        # Defense-in-depth: ensure resolved target stays within UPLOAD_ROOT.
        resolved = target.resolve()
        if not str(resolved).startswith(str(UPLOAD_ROOT)):
            logger.warning(
                "delete_uploaded_file: refusing path outside UPLOAD_ROOT: %s",
                public_url_path,
            )
            return
        if resolved.exists():
            resolved.unlink()
    except OSError as e:
        logger.warning("delete_uploaded_file: failed for %s: %s", public_url_path, e)
