"""
Business models — public read endpoints.

    GET /business-models/franchise/{slug}  list business models of a franchise
    GET /business-models/{id}              single business model

The CREATE/UPDATE/DELETE flows are franchisor-panel features and are still
unported (admin/franchisor auth + ownership checks). Flag when those pages
are wired up.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BusinessModel, Franchise

router = APIRouter(prefix="/business-models", tags=["business-models"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _serialize(bm: BusinessModel) -> dict[str, Any]:
    return {
        "id": bm.id,
        "name": bm.name,
        "description": bm.description,
        "photoUrl": bm.photoUrl,
        "franchiseId": bm.franchiseId,
        "createdAt": _iso(bm.createdAt),
        "updatedAt": _iso(bm.updatedAt),
    }


def _resolve_franchise(db: Session, slug_or_id: str) -> Franchise:
    f = db.scalar(select(Franchise).where(Franchise.slug == slug_or_id))
    if f is None:
        f = db.scalar(select(Franchise).where(Franchise.id == slug_or_id))
    if f is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franchise not found"
        )
    return f


@router.get("/franchise/{slug}", summary="Modelos de negócio de uma franquia")
def list_by_franchise(slug: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    franchise = _resolve_franchise(db, slug)
    rows = db.scalars(
        select(BusinessModel)
        .where(BusinessModel.franchiseId == franchise.id)
        .order_by(BusinessModel.createdAt.desc())
    ).all()
    return [_serialize(bm) for bm in rows]


@router.get("/{bm_id}", summary="Modelo de negócio por id")
def get_one(bm_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    bm = db.scalar(select(BusinessModel).where(BusinessModel.id == bm_id))
    if bm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Business model not found"
        )
    return _serialize(bm)
