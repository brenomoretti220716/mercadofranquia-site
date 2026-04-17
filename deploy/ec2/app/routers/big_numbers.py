"""
Ranking big-numbers — public read. Admin create/update/reorder routes
are still unported (future admin panel work).

    GET /ranking-big-numbers?year=      cards for the year (visible ones only)
    GET /ranking-big-numbers/years      distinct visible years
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RankingBugnumber

router = APIRouter(prefix="/ranking-big-numbers", tags=["big-numbers"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _num(v: Any) -> Any:
    return float(v) if isinstance(v, Decimal) else v


def _serialize(b: RankingBugnumber) -> dict[str, Any]:
    return {
        "id": b.id,
        "name": b.name,
        "position": b.position,
        "growthPercentage": _num(b.growthPercentage),
        "isWorst": bool(b.isWorst),
        "isHidden": bool(b.isHidden),
        "year": b.year,
        "createdAt": _iso(b.createdAt),
        "updatedAt": _iso(b.updatedAt),
    }


def _resolve_year(db: Session, year: Optional[int]) -> Optional[int]:
    if year is not None:
        return year
    latest = db.scalar(
        select(RankingBugnumber.year)
        .where(RankingBugnumber.isHidden.is_(False))
        .order_by(RankingBugnumber.year.desc())
        .limit(1)
    )
    return latest


@router.get("", summary="Big numbers visíveis do ano selecionado")
def list_visible(
    db: Session = Depends(get_db),
    year: Optional[int] = Query(None),
) -> list[dict[str, Any]]:
    resolved = _resolve_year(db, year)
    if resolved is None:
        return []
    rows = db.scalars(
        select(RankingBugnumber)
        .where(
            RankingBugnumber.year == resolved,
            RankingBugnumber.isHidden.is_(False),
        )
        .order_by(RankingBugnumber.position.asc())
    ).all()
    return [_serialize(b) for b in rows]


@router.get("/years", summary="Anos com big numbers publicados")
def list_years(db: Session = Depends(get_db)) -> list[int]:
    rows = db.scalars(
        select(distinct(RankingBugnumber.year))
        .where(RankingBugnumber.isHidden.is_(False))
        .order_by(RankingBugnumber.year.desc())
    ).all()
    return list(rows)
