"""
Favorites endpoints. All routes require auth. The `franchiseId` path param
is actually a SLUG (same as NestJS — the service resolves slug → id).

    GET    /favorites                         paginated list (sortBy, order, search)
    GET    /favorites/ids                     all favorited franchise IDs for the user
    GET    /favorites/check/{slug}            { isFavorited: bool }
    POST   /favorites/{slug}                  add (idempotent)
    POST   /favorites/{slug}/toggle           toggle (used by the heart icon)
    DELETE /favorites/{slug}                  remove (idempotent)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from math import ceil
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Favorite, Franchise, User
from app.profile_completion import compute_completion
from app.security import JwtPayload, get_current_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _resolve_franchise(db: Session, slug: str) -> Franchise:
    f = db.scalar(select(Franchise).where(Franchise.slug == slug))
    if f is None:
        f = db.scalar(select(Franchise).where(Franchise.id == slug))
    if f is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Franchise with ID {slug} not found",
        )
    return f


def _check_profile_complete(db: Session, user_id: str) -> None:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not compute_completion(user)["isComplete"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete seu perfil para usar esta funcionalidade",
        )


def _serialize_favorite_row(fav: Favorite, f: Franchise) -> dict[str, Any]:
    """Shape matches the NestJS `getUserFavorites` entry — `FavoriteWithFranchiseType`."""
    return {
        "id": fav.id,
        "userId": fav.userId,
        "franchiseId": fav.franchiseId,
        "createdAt": _iso(fav.createdAt),
        "franchise": {
            "id": f.id,
            "slug": f.slug,
            "name": f.name,
            "description": f.description,
            "logoUrl": f.logoUrl,
            "thumbnailUrl": f.thumbnailUrl,
            "segment": f.segment,
            "subsegment": f.subsegment,
            "minimumInvestment": float(f.minimumInvestment) if f.minimumInvestment is not None else None,
            "maximumInvestment": float(f.maximumInvestment) if f.maximumInvestment is not None else None,
            "averageMonthlyRevenue": float(f.averageMonthlyRevenue) if f.averageMonthlyRevenue is not None else None,
            "minimumReturnOnInvestment": f.minimumReturnOnInvestment,
            "maximumReturnOnInvestment": f.maximumReturnOnInvestment,
            "franchiseFee": float(f.franchiseFee) if f.franchiseFee is not None else None,
            "averageRating": f.averageRating,
            "reviewCount": f.reviewCount,
            "totalUnits": f.totalUnits,
            "isActive": bool(f.isActive),
        },
    }


# ---------------------------------------------------------------------------
# GET /favorites — paginated
# ---------------------------------------------------------------------------

@router.get("", summary="Listar favoritos do usuário (paginado)")
def list_favorites(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    sortBy: Literal["createdAt", "name"] = "createdAt",
    order: Literal["asc", "desc"] = "desc",
) -> dict[str, Any]:
    stmt = (
        select(Favorite, Franchise)
        .join(Franchise, Favorite.franchiseId == Franchise.id)
        .where(Favorite.userId == current.id, Franchise.isActive.is_(True))
    )
    if search and search.strip():
        stmt = stmt.where(Franchise.name.ilike(f"%{search.strip()}%"))

    if sortBy == "name":
        col = Franchise.name
    else:
        col = Favorite.createdAt
    stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())

    total = db.scalar(
        select(func.count())
        .select_from(Favorite)
        .join(Franchise, Favorite.franchiseId == Franchise.id)
        .where(
            Favorite.userId == current.id,
            Franchise.isActive.is_(True),
            *(
                [Franchise.name.ilike(f"%{search.strip()}%")]
                if search and search.strip()
                else []
            ),
        )
    ) or 0

    offset = (page - 1) * limit
    rows = db.execute(stmt.offset(offset).limit(limit)).all()

    return {
        "data": [_serialize_favorite_row(fav, f) for (fav, f) in rows],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": max(1, ceil(total / limit)) if total else 1,
        },
    }


# ---------------------------------------------------------------------------
# GET /favorites/ids
# ---------------------------------------------------------------------------

@router.get("/ids", summary="IDs das franquias favoritas do usuário")
def list_favorite_ids(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[str]]:
    ids = db.scalars(
        select(Favorite.franchiseId).where(Favorite.userId == current.id)
    ).all()
    return {"franchiseIds": list(ids)}


# ---------------------------------------------------------------------------
# GET /favorites/check/{slug}
# ---------------------------------------------------------------------------

@router.get("/check/{slug}", summary="Checar se franquia está favoritada")
def check_favorite(
    slug: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    franchise = _resolve_franchise(db, slug)
    exists = db.scalar(
        select(Favorite.id).where(
            Favorite.userId == current.id,
            Favorite.franchiseId == franchise.id,
        )
    )
    return {"isFavorited": exists is not None}


# ---------------------------------------------------------------------------
# POST /favorites/{slug}
# ---------------------------------------------------------------------------

def _add_favorite(db: Session, user_id: str, franchise: Franchise) -> Favorite:
    if not franchise.isActive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot favorite an inactive franchise",
        )
    existing = db.scalar(
        select(Favorite).where(
            Favorite.userId == user_id,
            Favorite.franchiseId == franchise.id,
        )
    )
    if existing is not None:
        return existing
    fav = Favorite(
        id=uuid.uuid4().hex,
        userId=user_id,
        franchiseId=franchise.id,
    )
    db.add(fav)
    franchise.favoritesCount = (franchise.favoritesCount or 0) + 1
    db.commit()
    db.refresh(fav)
    return fav


def _remove_favorite(db: Session, user_id: str, franchise: Franchise) -> bool:
    fav = db.scalar(
        select(Favorite).where(
            Favorite.userId == user_id,
            Favorite.franchiseId == franchise.id,
        )
    )
    if fav is None:
        return False
    db.delete(fav)
    franchise.favoritesCount = max(0, (franchise.favoritesCount or 0) - 1)
    db.commit()
    return True


@router.post(
    "/{slug}",
    summary="Adicionar aos favoritos",
    status_code=status.HTTP_201_CREATED,
)
def add_favorite(
    slug: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _check_profile_complete(db, current.id)
    franchise = _resolve_franchise(db, slug)
    fav = _add_favorite(db, current.id, franchise)
    return {
        "success": True,
        "message": "Franchise added to favorites",
        "data": {
            "id": fav.id,
            "userId": fav.userId,
            "franchiseId": fav.franchiseId,
            "createdAt": _iso(fav.createdAt),
        },
    }


@router.delete("/{slug}", summary="Remover dos favoritos")
def remove_favorite(
    slug: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _resolve_franchise(db, slug)
    _remove_favorite(db, current.id, franchise)
    return {"success": True, "message": "Franchise removed from favorites"}


@router.post("/{slug}/toggle", summary="Alternar favorito (heart icon)")
def toggle_favorite(
    slug: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _resolve_franchise(db, slug)
    exists = db.scalar(
        select(Favorite).where(
            Favorite.userId == current.id,
            Favorite.franchiseId == franchise.id,
        )
    )
    if exists is not None:
        _remove_favorite(db, current.id, franchise)
        return {
            "success": True,
            "data": {
                "isFavorited": False,
                "message": "Franchise removed from favorites",
            },
        }
    _check_profile_complete(db, current.id)
    _add_favorite(db, current.id, franchise)
    return {
        "success": True,
        "data": {
            "isFavorited": True,
            "message": "Franchise added to favorites",
        },
    }
