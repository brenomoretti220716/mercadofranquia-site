"""
Gerador de slug único pra Franchises.

Uso:
    from app.utils.slug import generate_unique_slug
    slug = generate_unique_slug("Pizza do Jorge", db)
    # => "pizza-do-jorge" (ou "pizza-do-jorge-2" se já existe)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Franchise


def _normalize(name: str) -> str:
    """
    Normaliza uma string pra formato slug:
    - Remove acentos (á → a, ç → c, ã → a)
    - Lowercase
    - Substitui qualquer caractere não-alfanumérico por hífen
    - Colapsa múltiplos hífens em um só
    - Remove hífens do início/fim
    """
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_str.lower()
    slugged = re.sub(r"[^a-z0-9]+", "-", lowered)
    slugged = re.sub(r"-+", "-", slugged).strip("-")
    return slugged


def generate_unique_slug(
    name: str,
    db: Session,
    *,
    exclude_id: Optional[str] = None,
    max_attempts: int = 100,
) -> str:
    """
    Gera um slug único pra uma Franchise a partir do nome.

    Args:
        name: Nome a ser convertido em slug.
        db: Sessão SQLAlchemy ativa.
        exclude_id: Se fornecido, ignora Franchise com esse id (útil em updates).
        max_attempts: Limite de tentativas com sufixo numérico antes de erro.

    Returns:
        Slug único (ex: "pizza-do-jorge" ou "pizza-do-jorge-2").

    Raises:
        ValueError: Se o nome resulta em slug vazio (só símbolos/acentos).
        RuntimeError: Se não conseguir gerar slug único em max_attempts tentativas.
    """
    base = _normalize(name)
    if not base:
        raise ValueError(f"Nome '{name}' não resulta em slug válido")

    candidate = base
    for attempt in range(1, max_attempts + 1):
        query = select(Franchise).where(Franchise.slug == candidate)
        if exclude_id is not None:
            query = query.where(Franchise.id != exclude_id)

        existing = db.scalar(query)
        if existing is None:
            return candidate

        candidate = f"{base}-{attempt + 1}"

    raise RuntimeError(
        f"Não foi possível gerar slug único pra '{name}' em {max_attempts} tentativas"
    )
