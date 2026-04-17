"""
Ranking big-numbers — public read + admin CRUD.

Public:
    GET /ranking-big-numbers?year=      cards for the year (visible ones only)
    GET /ranking-big-numbers/years      distinct visible years

Admin (require_role("ADMIN")):
    GET    /ranking-big-numbers/admin                   list ALL cards (incl. hidden)
    POST   /ranking-big-numbers/admin                   create card
    POST   /ranking-big-numbers/admin/bulk              bulk create (exactly 4)
    PATCH  /ranking-big-numbers/admin/year/visibility   hide/unhide whole year
    PATCH  /ranking-big-numbers/admin/{id}              update card
    PUT    /ranking-big-numbers/admin/reorder           reorder 4 cards
    DELETE /ranking-big-numbers/admin/{id}              delete card
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import distinct, func, select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RankingBugnumber
from app.security import JwtPayload, require_role

router = APIRouter(prefix="/ranking-big-numbers", tags=["big-numbers"])
logger = logging.getLogger("mf-api.big-numbers")


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


# ===========================================================================
# Admin endpoints — require_role("ADMIN")
#
# Order of declaration matters less here (different methods avoid most route
# conflicts), but `/admin/year/visibility` is declared BEFORE `/admin/{id}`
# defensively for clarity.
# ===========================================================================


def _current_year() -> int:
    return datetime.utcnow().year


def _resolve_admin_year(year: Optional[int]) -> int:
    """Admin endpoints default to current year (matches NestJS resolveYear)."""
    return year if year is not None else _current_year()


def _list_for_year(db: Session, year: int, *, visible_only: bool) -> list[dict[str, Any]]:
    stmt = select(RankingBugnumber).where(RankingBugnumber.year == year)
    if visible_only:
        stmt = stmt.where(RankingBugnumber.isHidden.is_(False))
    stmt = stmt.order_by(RankingBugnumber.position.asc())
    return [_serialize(b) for b in db.scalars(stmt).all()]


class CreateBigNumberBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    position: int = Field(ge=1, le=4)
    growthPercentage: float = Field(ge=-999.99, le=999.99)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)


class BulkCardItem(BaseModel):
    position: int = Field(ge=1, le=4)
    name: str = Field(min_length=1, max_length=120)
    growthPercentage: float = Field(ge=-999.99, le=999.99)


class BulkCreateBigNumbersBody(BaseModel):
    year: int = Field(ge=2000, le=2100)
    cards: list[BulkCardItem] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def _positions_complete(self) -> "BulkCreateBigNumbersBody":
        positions = sorted(c.position for c in self.cards)
        if positions != [1, 2, 3, 4]:
            raise ValueError("Cards must have positions exactly 1, 2, 3 and 4.")
        return self


class UpdateBigNumberBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    position: Optional[int] = Field(default=None, ge=1, le=4)
    growthPercentage: Optional[float] = Field(default=None, ge=-999.99, le=999.99)

    @model_validator(mode="after")
    def _at_least_one(self) -> "UpdateBigNumberBody":
        if all(
            getattr(self, f) is None for f in ("name", "position", "growthPercentage")
        ):
            raise ValueError("At least one field must be provided.")
        return self


class ReorderCardItem(BaseModel):
    id: str = Field(min_length=1)
    position: int = Field(ge=1, le=4)


class ReorderBigNumbersBody(BaseModel):
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    cards: list[ReorderCardItem] = Field(min_length=4, max_length=4)


class SetYearVisibilityBody(BaseModel):
    year: int = Field(ge=2000, le=2100)
    isHidden: bool


# ---------------------------------------------------------------------------
# GET /admin
# ---------------------------------------------------------------------------

@router.get("/admin", summary="Lista admin (inclui hidden)")
def find_all_admin(
    year: Optional[int] = Query(None),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    selected = _resolve_admin_year(year)
    return _list_for_year(db, selected, visible_only=False)


# ---------------------------------------------------------------------------
# POST /admin
# ---------------------------------------------------------------------------

@router.post(
    "/admin",
    summary="Cria card (admin)",
    status_code=status.HTTP_201_CREATED,
)
def create_card(
    body: CreateBigNumberBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    year = _resolve_admin_year(body.year)

    count = db.scalar(
        select(func.count())
        .select_from(RankingBugnumber)
        .where(RankingBugnumber.year == year)
    ) or 0
    if count >= 4:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This year already has 4 ranking big number cards.",
        )

    position_taken = db.scalar(
        select(RankingBugnumber.id).where(
            RankingBugnumber.year == year,
            RankingBugnumber.position == body.position,
        )
    )
    if position_taken is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Position already used for this year.",
        )

    card = RankingBugnumber(
        id=uuid.uuid4().hex,
        name=body.name,
        position=body.position,
        growthPercentage=Decimal(str(body.growthPercentage)),
        year=year,
        isWorst=(body.position == 4),
        isHidden=False,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _serialize(card)


# ---------------------------------------------------------------------------
# POST /admin/bulk  — exactly 4 cards in a single transaction
# ---------------------------------------------------------------------------

@router.post(
    "/admin/bulk",
    summary="Bulk create (exatamente 4 cards, ano sem cards)",
    status_code=status.HTTP_201_CREATED,
)
def bulk_create_cards(
    body: BulkCreateBigNumbersBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    existing = db.scalar(
        select(func.count())
        .select_from(RankingBugnumber)
        .where(RankingBugnumber.year == body.year)
    ) or 0
    if existing > 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This year already has big numbers cards.",
        )

    for card in body.cards:
        db.add(
            RankingBugnumber(
                id=uuid.uuid4().hex,
                name=card.name,
                position=card.position,
                growthPercentage=Decimal(str(card.growthPercentage)),
                year=body.year,
                isWorst=(card.position == 4),
                isHidden=False,
            )
        )
    db.commit()

    # Match NestJS: returns the visible set (which == the just-created cards).
    return _list_for_year(db, body.year, visible_only=True)


# ---------------------------------------------------------------------------
# PATCH /admin/year/visibility  (declared BEFORE /admin/{id} for clarity)
# ---------------------------------------------------------------------------

@router.patch(
    "/admin/year/visibility",
    summary="Hide/unhide year (bulk update)",
)
def set_year_visibility(
    body: SetYearVisibilityBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    count = db.scalar(
        select(func.count())
        .select_from(RankingBugnumber)
        .where(RankingBugnumber.year == body.year)
    ) or 0
    if count == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot change visibility for this year because no big numbers cards exist.",
        )

    result = db.execute(
        update(RankingBugnumber)
        .where(RankingBugnumber.year == body.year)
        .values(isHidden=body.isHidden)
    )
    db.commit()
    return {
        "message": f"Year {body.year} visibility updated successfully.",
        "updatedCount": result.rowcount,
    }


# ---------------------------------------------------------------------------
# PUT /admin/reorder  — 2-step swap to sidestep unique(year, position)
# ---------------------------------------------------------------------------

@router.put("/admin/reorder", summary="Reordena Top1/Top2/Top3/Worst")
def reorder_cards(
    body: ReorderBigNumbersBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    year = _resolve_admin_year(body.year)

    cards_in_db = db.execute(
        select(RankingBugnumber.id).where(RankingBugnumber.year == year)
    ).all()
    if len(cards_in_db) != 4:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Reorder requires exactly 4 cards registered for the selected year.",
        )

    ids_in_db = {row[0] for row in cards_in_db}
    ids_in_payload = {c.id for c in body.cards}
    if (
        len(ids_in_payload) != 4
        or ids_in_payload != ids_in_db
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Payload must contain exactly the same 4 cards from the selected year.",
        )

    positions_sorted = sorted(c.position for c in body.cards)
    if positions_sorted != [1, 2, 3, 4]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Positions must be exactly 1, 2, 3 and 4.",
        )

    # Step 1: shift positions to a non-conflicting range (11..14). The unique
    # constraint (year, position) blocks any direct swap because intermediate
    # states would briefly share a position. Doing it in two passes — and
    # flushing after pass 1 — keeps each row update individually valid.
    for card in body.cards:
        db.execute(
            update(RankingBugnumber)
            .where(RankingBugnumber.id == card.id)
            .values(position=card.position + 10)
        )
    db.flush()

    # Step 2: apply final positions + isWorst.
    for card in body.cards:
        db.execute(
            update(RankingBugnumber)
            .where(RankingBugnumber.id == card.id)
            .values(position=card.position, isWorst=(card.position == 4))
        )
    db.commit()

    return _list_for_year(db, year, visible_only=True)


# ---------------------------------------------------------------------------
# PATCH /admin/{id}
# ---------------------------------------------------------------------------

@router.patch("/admin/{card_id}", summary="Atualiza card (admin)")
def update_card(
    card_id: str,
    body: UpdateBigNumberBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    card = db.scalar(
        select(RankingBugnumber).where(RankingBugnumber.id == card_id)
    )
    if card is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ranking big number card not found."
        )

    if body.position is not None and body.position != card.position:
        position_taken = db.scalar(
            select(RankingBugnumber.id).where(
                RankingBugnumber.year == card.year,
                RankingBugnumber.position == body.position,
                RankingBugnumber.id != card_id,
            )
        )
        if position_taken is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Position already used for this year.",
            )

    if body.name is not None:
        card.name = body.name
    if body.position is not None:
        card.position = body.position
        card.isWorst = (body.position == 4)
    if body.growthPercentage is not None:
        card.growthPercentage = Decimal(str(body.growthPercentage))

    db.commit()
    db.refresh(card)

    # NestJS validateYearConsistency runs a defensive count check (>4) which
    # is unreachable here since update never increases card count. Skip.
    return _serialize(card)


# ---------------------------------------------------------------------------
# DELETE /admin/{id}
# ---------------------------------------------------------------------------

@router.delete("/admin/{card_id}", summary="Apaga card (admin)")
def delete_card(
    card_id: str,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    card = db.scalar(
        select(RankingBugnumber).where(RankingBugnumber.id == card_id)
    )
    if card is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ranking big number card not found."
        )

    count = db.scalar(
        select(func.count())
        .select_from(RankingBugnumber)
        .where(RankingBugnumber.year == card.year)
    ) or 0
    # NestJS guard — effectively unreachable in practice (create blocks the
    # 5th card per year, so count is always 0..4 → this always throws).
    # Ported faithfully so the error matches.
    if count <= 4:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete card while year would have less than 4 items.",
        )

    db.delete(card)
    db.commit()
    return {"message": "Ranking big number card deleted successfully."}
