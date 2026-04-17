"""
ABF segment entries — public read + admin CRUD.

Public:
    GET /abf-segments?year=&quarter=   list entries (ordered year desc, quarter desc, value desc)
    GET /abf-segments/years            distinct years available
    GET /abf-segments/{id}             single entry

Admin (require_role("ADMIN")):
    POST   /abf-segments               create entry
    PATCH  /abf-segments/{id}          update entry (partial)
    DELETE /abf-segments/{id}          delete entry
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import distinct, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AbfSegmentEntry
from app.security import JwtPayload, require_role

router = APIRouter(prefix="/abf-segments", tags=["abf-segments"])
logger = logging.getLogger("mf-api.abf-segments")

_QUARTER_RE = re.compile(r"^Q[1-4]$")


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


# ===========================================================================
# Admin endpoints — require_role("ADMIN")
# ===========================================================================


def _validate_quarter(v: str) -> str:
    if not _QUARTER_RE.match(v):
        raise ValueError("Trimestre inválido (use Q1, Q2, Q3 ou Q4)")
    return v


class CreateAbfSegmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int = Field(ge=1900, le=2100)
    quarter: str
    segment: str = Field(min_length=1, max_length=200)
    acronym: str = Field(min_length=1, max_length=10)
    value: int = Field(ge=0)

    @field_validator("quarter")
    @classmethod
    def _q(cls, v: str) -> str:
        return _validate_quarter(v)


class UpdateAbfSegmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    quarter: Optional[str] = None
    segment: Optional[str] = Field(default=None, min_length=1, max_length=200)
    acronym: Optional[str] = Field(default=None, min_length=1, max_length=10)
    value: Optional[int] = Field(default=None, ge=0)

    @field_validator("quarter")
    @classmethod
    def _q(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_quarter(v)


@router.post(
    "",
    summary="Cria entrada ABF (admin)",
    status_code=status.HTTP_201_CREATED,
)
def create_entry(
    body: CreateAbfSegmentBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    entry = AbfSegmentEntry(
        id=uuid.uuid4().hex,
        year=body.year,
        quarter=body.quarter,
        segment=body.segment,
        acronym=body.acronym,
        value=body.value,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # AbfSegmentEntry_year_quarter_acronym_key
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um segmento com este (year, quarter, acronym)",
        )
    db.refresh(entry)
    return _serialize(entry)


@router.patch("/{entry_id}", summary="Atualiza entrada ABF (admin)")
def update_entry(
    entry_id: str,
    body: UpdateAbfSegmentBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    entry = db.scalar(
        select(AbfSegmentEntry).where(AbfSegmentEntry.id == entry_id)
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento ABF não encontrado",
        )

    if body.year is not None:
        entry.year = body.year
    if body.quarter is not None:
        entry.quarter = body.quarter
    if body.segment is not None:
        entry.segment = body.segment
    if body.acronym is not None:
        entry.acronym = body.acronym
    if body.value is not None:
        entry.value = body.value

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um segmento com este (year, quarter, acronym)",
        )
    db.refresh(entry)
    return _serialize(entry)


@router.delete("/{entry_id}", summary="Apaga entrada ABF (admin)")
def delete_entry(
    entry_id: str,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    entry = db.scalar(
        select(AbfSegmentEntry).where(AbfSegmentEntry.id == entry_id)
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento ABF não encontrado",
        )
    db.delete(entry)
    db.commit()
    return {"message": "Segmento ABF deletado com sucesso"}
