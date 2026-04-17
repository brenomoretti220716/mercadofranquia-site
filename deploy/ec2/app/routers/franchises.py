"""
Franchises endpoints. URL prefix is `/franchises` — nginx adds the `/api/`
prefix externally (see `deploy/ec2/mercadofranquia.nginx`).

Response shapes are kept compatible with what the Next.js client consumes in
`web/src/services/franchises.ts`:

  GET /franchises           -> { data: Franchise[], total, page, lastPage }
  GET /franchises/count     -> { total: number }
  GET /franchises/{slug}    -> { data: Franchise }
"""
from __future__ import annotations

from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Franchise, Review
from app.serializers import serialize_franchise

router = APIRouter(prefix="/franchises", tags=["franchises"])


SORT_COLUMNS = {
    "name":          Franchise.name,
    "rating":        Franchise.averageRating,
    "units":         Franchise.totalUnits,
    "investment":    Franchise.minimumInvestment,
    "roi":           Franchise.minimumReturnOnInvestment,
    "franchiseFee":  Franchise.franchiseFee,
    "revenue":       Franchise.averageMonthlyRevenue,
}


def _apply_filters(stmt, *, only_active: bool, filters: dict):
    if only_active:
        stmt = stmt.where(Franchise.isActive.is_(True))

    search = filters.get("search")
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))

    segment = filters.get("segment")
    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))

    subsegment = filters.get("subsegment")
    if subsegment:
        stmt = stmt.where(Franchise.subsegment.ilike(f"%{subsegment}%"))

    exclude_subsegment = filters.get("excludeSubsegment")
    if exclude_subsegment:
        stmt = stmt.where(
            or_(
                Franchise.subsegment.is_(None),
                ~Franchise.subsegment.ilike(f"%{exclude_subsegment}%"),
            )
        )

    if (v := filters.get("minInvestment")) is not None:
        stmt = stmt.where(Franchise.minimumInvestment >= v)
    if (v := filters.get("maxInvestment")) is not None:
        stmt = stmt.where(Franchise.maximumInvestment <= v)
    if (v := filters.get("minUnits")) is not None:
        stmt = stmt.where(Franchise.totalUnits >= v)
    if (v := filters.get("maxUnits")) is not None:
        stmt = stmt.where(Franchise.totalUnits <= v)
    if (v := filters.get("minROI")) is not None:
        stmt = stmt.where(Franchise.minimumReturnOnInvestment >= v)
    if (v := filters.get("maxROI")) is not None:
        stmt = stmt.where(Franchise.maximumReturnOnInvestment <= v)
    if (v := filters.get("minFranchiseFee")) is not None:
        stmt = stmt.where(Franchise.franchiseFee >= v)
    if (v := filters.get("maxFranchiseFee")) is not None:
        stmt = stmt.where(Franchise.franchiseFee <= v)
    if (v := filters.get("minRevenue")) is not None:
        stmt = stmt.where(Franchise.averageMonthlyRevenue >= v)
    if (v := filters.get("maxRevenue")) is not None:
        stmt = stmt.where(Franchise.averageMonthlyRevenue <= v)
    if (v := filters.get("minRating")) is not None:
        stmt = stmt.where(Franchise.averageRating >= v)
    if (v := filters.get("maxRating")) is not None:
        stmt = stmt.where(Franchise.averageRating <= v)
    if (v := filters.get("isSponsored")) is not None:
        stmt = stmt.where(Franchise.isSponsored == v)
    return stmt


def _apply_sorts(stmt, sort_params: dict[str, Optional[str]]):
    """Apply user-requested sorts, falling back to units DESC, name ASC."""
    orders = []
    for key, direction in sort_params.items():
        if direction not in ("asc", "desc"):
            continue
        col = SORT_COLUMNS.get(key)
        if col is None:
            continue
        ordering = col.desc() if direction == "desc" else col.asc()
        # Nulls go last regardless of direction so they don't dominate rankings.
        orders.append(ordering.nulls_last())
    if not orders:
        orders = [Franchise.totalUnits.desc().nulls_last(), Franchise.name.asc()]
    return stmt.order_by(*orders)


@router.get("", summary="List franchises with filters & sorting (paginated)")
def list_franchises(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    segment: Optional[str] = None,
    subsegment: Optional[str] = None,
    excludeSubsegment: Optional[str] = None,
    minInvestment: Optional[float] = None,
    maxInvestment: Optional[float] = None,
    minUnits: Optional[int] = None,
    maxUnits: Optional[int] = None,
    minROI: Optional[int] = None,
    maxROI: Optional[int] = None,
    minFranchiseFee: Optional[float] = None,
    maxFranchiseFee: Optional[float] = None,
    minRevenue: Optional[float] = None,
    maxRevenue: Optional[float] = None,
    minRating: Optional[float] = None,
    maxRating: Optional[float] = None,
    isSponsored: Optional[bool] = None,
    nameSort: Optional[str] = None,
    ratingSort: Optional[str] = None,
    unitsSort: Optional[str] = None,
    investmentSort: Optional[str] = None,
    roiSort: Optional[str] = None,
    franchiseFeeSort: Optional[str] = None,
    revenueSort: Optional[str] = None,
):
    filters = {
        "search": search,
        "segment": segment,
        "subsegment": subsegment,
        "excludeSubsegment": excludeSubsegment,
        "minInvestment": minInvestment,
        "maxInvestment": maxInvestment,
        "minUnits": minUnits,
        "maxUnits": maxUnits,
        "minROI": minROI,
        "maxROI": maxROI,
        "minFranchiseFee": minFranchiseFee,
        "maxFranchiseFee": maxFranchiseFee,
        "minRevenue": minRevenue,
        "maxRevenue": maxRevenue,
        "minRating": minRating,
        "maxRating": maxRating,
        "isSponsored": isSponsored,
    }
    sort_params = {
        "name":         nameSort,
        "rating":       ratingSort,
        "units":        unitsSort,
        "investment":   investmentSort,
        "roi":          roiSort,
        "franchiseFee": franchiseFeeSort,
        "revenue":      revenueSort,
    }

    stmt = select(Franchise)
    stmt = _apply_filters(stmt, only_active=True, filters=filters)
    stmt = _apply_sorts(stmt, sort_params)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * limit
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()

    return {
        # rankingPosition reflete a ordem da query atual (filtros + sort
        # aplicados), páginado. Para "posição global fixa por totalUnits"
        # independente do sort, usar GET /ranking.
        "data": [
            serialize_franchise(f, ranking_position=offset + idx + 1)
            for idx, f in enumerate(rows)
        ],
        "total": total,
        "page": page,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }


@router.get("/count", summary="Total active franchises matching filters")
def count_franchises(
    db: Session = Depends(get_db),
    segment: Optional[str] = None,
    minInvestment: Optional[float] = None,
    maxInvestment: Optional[float] = None,
    search: Optional[str] = None,
    isActive: Optional[bool] = True,
):
    stmt = select(func.count(Franchise.id))
    if isActive is not None:
        stmt = stmt.where(Franchise.isActive == isActive)
    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))
    if minInvestment is not None:
        stmt = stmt.where(Franchise.minimumInvestment >= minInvestment)
    if maxInvestment is not None:
        stmt = stmt.where(Franchise.maximumInvestment <= maxInvestment)
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))
    total = db.scalar(stmt) or 0
    return {"total": total}


@router.get(
    "/{slug}/ranking",
    summary="Franquia + vizinhos no ranking (next/prev nav)",
)
def get_franchise_ranking(
    slug: str,
    db: Session = Depends(get_db),
    segment: Optional[str] = None,
    search: Optional[str] = None,
):
    # Build the same ordering as the default /franchises list so neighbor
    # navigation is stable: totalUnits DESC → name ASC, plus any subset
    # of the public list filters that the detail page forwards.
    stmt = select(Franchise).where(Franchise.isActive.is_(True))
    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(
        Franchise.totalUnits.desc().nulls_last(), Franchise.name.asc()
    )

    # Load only what we need for navigation (id, slug, name, position).
    ordered = db.execute(
        stmt.with_only_columns(Franchise.id, Franchise.slug, Franchise.name)
    ).all()

    idx = next(
        (i for i, row in enumerate(ordered) if row[1] == slug or row[0] == slug),
        None,
    )
    if idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franchise not found"
        )

    # Load the full franchise for the current one.
    current = db.scalar(
        select(Franchise).where(Franchise.id == ordered[idx][0])
    )
    assert current is not None

    def _neighbor(offset: int) -> Optional[str]:
        j = idx + offset
        if 0 <= j < len(ordered):
            return ordered[j][1] or ordered[j][0]
        return None

    return {
        "data": {
            "franchiseWithRanking": {
                **serialize_franchise(current),
                "rankingPosition": idx + 1,
            },
            "nextFranchiseWithRanking": _neighbor(1),
            "previousFranchiseWithRanking": _neighbor(-1),
        }
    }


@router.get("/{slug}", summary="Get a single franchise by slug (or id)")
def get_franchise(slug: str, db: Session = Depends(get_db)):
    stmt = (
        select(Franchise)
        .where(or_(Franchise.slug == slug, Franchise.id == slug))
        .options(
            selectinload(Franchise.contact),
            selectinload(Franchise.owner),
            selectinload(Franchise.business_models),
            selectinload(Franchise.reviews).selectinload(Review.author),
        )
    )
    franchise = db.scalars(stmt).first()
    if franchise is None:
        raise HTTPException(status_code=404, detail="Franchise not found")
    return {"data": serialize_franchise(franchise, include_relations=True)}
