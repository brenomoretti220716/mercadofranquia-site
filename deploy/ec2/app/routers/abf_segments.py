"""
ABF segment entries — public read.

    GET /abf-segments?year=&quarter=   list entries (ordered year desc, quarter desc, value desc)
    GET /abf-segments/years            distinct years available
    GET /abf-segments/{id}             single entry
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AbfSegmentEntry

router = APIRouter(prefix="/abf-segments", tags=["abf-segments"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _serialize(e: AbfSegmentEntry) -> dict[str, Any]:
    return {
        "id": e.id,
        "year": e.year,
        "quarter": e.quarter,
        "segment": e.segment,
        "acronym": e.acronym,
        "value": e.value,
        "createdAt": _iso(e.createdAt),
        "updatedAt": _iso(e.updatedAt),
    }


@router.get("", summary="Listar entradas ABF por segmento")
def list_entries(
    db: Session = Depends(get_db),
    year: Optional[int] = Query(None),
    quarter: Optional[str] = Query(None, min_length=1, max_length=2),
) -> list[dict[str, Any]]:
    stmt = select(AbfSegmentEntry)
    if year is not None:
        stmt = stmt.where(AbfSegmentEntry.year == year)
    if quarter is not None:
        stmt = stmt.where(AbfSegmentEntry.quarter == quarter)
    stmt = stmt.order_by(
        AbfSegmentEntry.year.desc(),
        AbfSegmentEntry.quarter.desc(),
        AbfSegmentEntry.value.desc(),
    )
    return [_serialize(e) for e in db.scalars(stmt).all()]


@router.get("/years", summary="Anos disponíveis")
def list_years(db: Session = Depends(get_db)) -> list[int]:
    rows = db.scalars(
        select(distinct(AbfSegmentEntry.year)).order_by(AbfSegmentEntry.year.desc())
    ).all()
    return list(rows)


@router.get("/{entry_id}", summary="Entrada ABF por id")
def get_one(entry_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    e = db.scalar(
        select(AbfSegmentEntry).where(AbfSegmentEntry.id == entry_id)
    )
    if e is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found"
        )
    return _serialize(e)
