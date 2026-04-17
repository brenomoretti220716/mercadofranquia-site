"""
Ranking endpoint — top franchises ordered by number of units.

  GET /ranking  ->  { data: Franchise[], total, page, lastPage }

Each item carries a `rankingPosition` derived from the global ordering,
so the client can render it without a second query. Filters are a subset
of the `/franchises` endpoint's: segment, investment range, search.
"""
from __future__ import annotations

from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Franchise
from app.serializers import serialize_franchise

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("", summary="Top franchises ranked by totalUnits")
def ranking(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    segment: Optional[str] = None,
    subsegment: Optional[str] = None,
    minInvestment: Optional[float] = None,
    maxInvestment: Optional[float] = None,
    search: Optional[str] = None,
):
    stmt = select(Franchise).where(Franchise.isActive.is_(True))

    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))
    if subsegment:
        stmt = stmt.where(Franchise.subsegment.ilike(f"%{subsegment}%"))
    if minInvestment is not None:
        stmt = stmt.where(Franchise.minimumInvestment >= minInvestment)
    if maxInvestment is not None:
        stmt = stmt.where(Franchise.maximumInvestment <= maxInvestment)
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))

    # Stable order: totalUnits desc, then rating desc, then name asc for tie-break.
    stmt = stmt.order_by(
        Franchise.totalUnits.desc().nulls_last(),
        Franchise.averageRating.desc().nulls_last(),
        Franchise.name.asc(),
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * limit
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()

    data = [
        serialize_franchise(f, ranking_position=offset + idx + 1)
        for idx, f in enumerate(rows)
    ]

    return {
        "data": data,
        "total": total,
        "page": page,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }
