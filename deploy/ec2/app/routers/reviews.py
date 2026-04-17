"""
Review endpoints — `franchiseId` in the URL is a SLUG for public-facing routes.

    GET  /reviews/franchise/{slug}                     public; paginated reviews
    GET  /reviews/franchise/franchisee/{slug}          auth; has-reviewed check for the caller
    POST /reviews/{slug}                               auth; create review
"""
from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Franchise, Review, User
from app.profile_completion import compute_completion
from app.security import JwtPayload, get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _resolve_franchise(db: Session, slug: str) -> Franchise:
    f = db.scalar(select(Franchise).where(Franchise.slug == slug))
    if f is None:
        f = db.scalar(select(Franchise).where(Franchise.id == slug))
    if f is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franchise not found"
        )
    return f


def _serialize_review(r: Review) -> dict[str, Any]:
    author = getattr(r, "author", None)
    payload: dict[str, Any] = {
        "id": r.id,
        "rating": r.rating,
        "comment": r.comment,
        "anonymous": bool(r.anonymous),
        "isActive": bool(r.isActive),
        "isFranchisee": bool(r.isFranchisee),
        "franchiseId": r.franchiseId,
        "authorId": r.authorId,
        "createdAt": _iso(r.createdAt),
    }
    if author is not None:
        payload["author"] = (
            None
            if r.anonymous
            else {"id": author.id, "name": author.name}
        )
    return payload


class CreateReviewBody(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=4000)
    anonymous: bool = False


# ---------------------------------------------------------------------------
# GET /reviews/franchise/{slug}
# ---------------------------------------------------------------------------

@router.get(
    "/franchise/{slug}",
    summary="Reviews de uma franquia (público, paginado)",
)
def list_reviews(
    slug: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(4, ge=1, le=50),
) -> dict[str, Any]:
    franchise = _resolve_franchise(db, slug)

    stmt = (
        select(Review)
        .where(Review.franchiseId == franchise.id, Review.isActive.is_(True))
        .options(selectinload(Review.author))
        .order_by(Review.createdAt.desc())
    )
    total = db.scalar(
        select(func.count())
        .where(Review.franchiseId == franchise.id, Review.isActive.is_(True))
        .select_from(Review)
    ) or 0
    offset = (page - 1) * limit
    reviews = db.scalars(stmt.offset(offset).limit(limit)).all()

    return {
        "data": [_serialize_review(r) for r in reviews],
        "total": total,
        "page": page,
        "limit": limit,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }


# ---------------------------------------------------------------------------
# GET /reviews/franchise/franchisee/{slug}
# ---------------------------------------------------------------------------

@router.get(
    "/franchise/franchisee/{slug}",
    summary="O usuário logado já avaliou essa franquia?",
)
def has_reviewed(
    slug: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _resolve_franchise(db, slug)
    row = db.scalar(
        select(Review.id, Review.rating).where(
            Review.franchiseId == franchise.id,
            Review.authorId == current.id,
        )
    )
    if row is None:
        return {"hasReviewed": False, "reviewId": None}
    # scalar() returns the first column — re-query for both.
    rec = db.execute(
        select(Review.id, Review.rating).where(
            Review.franchiseId == franchise.id,
            Review.authorId == current.id,
        )
    ).first()
    return {
        "hasReviewed": True,
        "reviewId": rec[0] if rec else None,
        "rating": rec[1] if rec else None,
    }


# ---------------------------------------------------------------------------
# POST /reviews/{slug}
# ---------------------------------------------------------------------------

@router.post("/{slug}", status_code=status.HTTP_201_CREATED, summary="Criar review")
def create_review(
    slug: str,
    body: CreateReviewBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # User must exist + be active.
    user = db.scalar(
        select(User)
        .where(User.id == current.id, User.isActive.is_(True))
        .options(selectinload(User.profile))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive",
        )

    franchise = db.scalar(
        select(Franchise)
        .where(Franchise.slug == slug, Franchise.isActive.is_(True))
        .options(selectinload(Franchise.franchisees))
    )
    if franchise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Franchise not found or inactive",
        )
    if franchise.isReview is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Franchise is not accepting reviews",
        )

    # Already reviewed?
    existing = db.scalar(
        select(Review.id).where(
            Review.franchiseId == franchise.id,
            Review.authorId == current.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this franchise",
        )

    if not compute_completion(user)["isComplete"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete seu perfil para usar esta funcionalidade",
        )

    # isFranchisee if user is linked via `franchises_as_franchisee`.
    is_franchisee = any(u.id == current.id for u in (franchise.franchisees or []))

    review = Review(
        franchiseId=franchise.id,
        authorId=current.id,
        anonymous=body.anonymous,
        rating=body.rating,
        comment=body.comment,
        isFranchisee=is_franchisee,
        isActive=True,
    )
    db.add(review)

    # Update franchise aggregates transactionally (SQLAlchemy flushes on commit).
    franchise.reviewCount = (franchise.reviewCount or 0) + 1
    franchise.ratingSum = (franchise.ratingSum or 0) + body.rating
    new_count = franchise.reviewCount
    franchise.averageRating = (
        float(franchise.ratingSum) / new_count if new_count > 0 else None
    )

    db.commit()
    db.refresh(review)
    db.refresh(review, attribute_names=["author"])
    return _serialize_review(review)
