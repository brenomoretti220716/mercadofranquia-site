"""
Review endpoints — `franchiseId` in the URL is a SLUG for public-facing routes.

    GET  /reviews/franchise/{slug}                     public; paginated reviews
    GET  /reviews/franchise/franchisee/{slug}          auth; has-reviewed check for the caller
    POST /reviews/{slug}                               auth; create review
"""
from __future__ import annotations

import logging
from datetime import datetime
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Franchise, Review, ReviewResponse, User
from app.profile_completion import compute_completion
from app.services.review_service import recalculate_franchise_aggregates
from app.security import (
    JwtPayload,
    assert_franchise_owner,
    get_current_user,
    require_any_role,
    require_role,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])
logger = logging.getLogger("mf-api.reviews")


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
        "updatedAt": _iso(r.updatedAt),
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
    comment: str = Field(min_length=30, max_length=1000)
    anonymous: bool = False


class UpdateReviewBody(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, min_length=30, max_length=1000)


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
    db.flush()  # garante que o INSERT da review e visivel pra COUNT no helper

    # Recalcular agregados via SELECT COUNT/SUM/AVG WHERE isActive=true.
    # Mais robusto que incremental — evita drift se houver inconsistencia.
    recalculate_franchise_aggregates(db, franchise.id)

    db.commit()
    db.refresh(review)
    db.refresh(review, attribute_names=["author"])
    return _serialize_review(review)


# ---------------------------------------------------------------------------
# PATCH /reviews/{review_id} (autor edita propria avaliacao)
# ---------------------------------------------------------------------------

@router.patch("/{review_id}", summary="Editar propria avaliacao")
def update_review(
    review_id: int,
    body: UpdateReviewBody,
    db: Session = Depends(get_db),
    current: JwtPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """Permite ao autor editar a propria avaliacao.

    - Auth: precisa ser o autor da review.
    - Pode mudar rating, comment ou ambos.
    - updatedAt vira NOW() em qualquer mudanca.
    - Se rating mudou, recalcula agregados da Franchise.
    """
    review = db.scalar(select(Review).where(Review.id == review_id))
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avaliacao nao encontrada",
        )

    if review.authorId != current.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce so pode editar suas proprias avaliacoes",
        )

    rating_changed = False
    if body.rating is not None and body.rating != review.rating:
        review.rating = body.rating
        rating_changed = True

    if body.comment is not None:
        review.comment = body.comment

    review.updatedAt = datetime.utcnow()

    db.flush()

    if rating_changed:
        recalculate_franchise_aggregates(db, review.franchiseId)

    db.commit()
    db.refresh(review)
    db.refresh(review, attribute_names=["author"])

    return _serialize_review(review)


# ---------------------------------------------------------------------------
# DELETE /reviews/{review_id} (autor deleta propria avaliacao)
# ---------------------------------------------------------------------------

@router.delete("/{review_id}", summary="Deletar propria avaliacao")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current: JwtPayload = Depends(get_current_user),
) -> dict[str, str]:
    """Permite ao autor deletar a propria avaliacao (hard delete).

    - Auth: precisa ser o autor da review.
    - Side: ReviewResponse vinculada e deletada via CASCADE.
    - Recalcula agregados da Franchise.
    """
    review = db.scalar(select(Review).where(Review.id == review_id))
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avaliacao nao encontrada",
        )

    if review.authorId != current.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce so pode deletar suas proprias avaliacoes",
        )

    # Salvar franchiseId ANTES do delete (objeto vira detached depois)
    franchise_id = review.franchiseId

    db.delete(review)
    db.flush()

    recalculate_franchise_aggregates(db, franchise_id)

    db.commit()

    return {"message": "Avaliacao removida com sucesso"}


# ===========================================================================
# Admin endpoints — require_role("ADMIN")
# ===========================================================================


def _serialize_review_admin(
    r: Review,
    *,
    franchise_block: Optional[dict[str, Any]] = None,
    response_authors: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Admin shape — exposes author always (even when anonymous) and embeds
    full responses with author info."""
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
        "author": (
            {
                "id": author.id,
                "name": author.name,
                "email": author.email,
                "cpf": author.cpf,
            }
            if author is not None
            else None
        ),
    }
    if franchise_block is not None:
        payload["franchise"] = franchise_block
    responses: list[dict[str, Any]] = []
    for rr in sorted(
        getattr(r, "responses", []) or [],
        key=lambda x: x.createdAt or datetime.min,
        reverse=True,
    ):
        a_user = (response_authors or {}).get(rr.authorId)
        responses.append(
            {
                "id": rr.id,
                "content": rr.content,
                "reviewId": rr.reviewId,
                "authorId": rr.authorId,
                "createdAt": _iso(rr.createdAt),
                "updatedAt": _iso(rr.updatedAt),
                "author": (
                    {"id": a_user.id, "name": a_user.name, "role": a_user.role}
                    if a_user is not None
                    else None
                ),
            }
        )
    payload["responses"] = responses
    return payload


def _load_response_authors(db: Session, reviews: list[Review]) -> dict[str, User]:
    """Batch-load User rows for every ReviewResponse author across the list."""
    author_ids: set[str] = set()
    for r in reviews:
        for rr in getattr(r, "responses", []) or []:
            if rr.authorId:
                author_ids.add(rr.authorId)
    if not author_ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(author_ids))).all()
    return {u.id: u for u in users}


# ---------------------------------------------------------------------------
# GET /reviews/admin/franchise/{franchise_id}
# ---------------------------------------------------------------------------

@router.get(
    "/admin/franchise/{franchise_id}",
    summary="Reviews por franquia para admin (id, todas inclui inativas)",
)
def list_reviews_admin(
    franchise_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = db.scalar(select(Franchise).where(Franchise.id == franchise_id))
    if franchise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franchise not found"
        )

    base = select(Review).where(Review.franchiseId == franchise_id)
    total = db.scalar(
        select(func.count())
        .select_from(Review)
        .where(Review.franchiseId == franchise_id)
    ) or 0

    offset = (page - 1) * limit
    reviews = db.scalars(
        base.options(
            selectinload(Review.author),
            selectinload(Review.responses),
        )
        .order_by(Review.createdAt.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    response_authors = _load_response_authors(db, list(reviews))
    franchise_block = {
        "id": franchise.id,
        "name": franchise.name,
        "isActive": bool(franchise.isActive),
    }
    data = [
        _serialize_review_admin(
            r,
            franchise_block=franchise_block,
            response_authors=response_authors,
        )
        for r in reviews
    ]

    return {
        "data": data,
        "franchise": franchise_block,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": ceil(total / limit) if total else 0,
        },
    }


# ---------------------------------------------------------------------------
# PATCH /reviews/{review_id}/toggle-status
# ---------------------------------------------------------------------------

class ToggleReviewStatusBody(BaseModel):
    isActive: bool


@router.patch(
    "/{review_id}/toggle-status",
    summary="Toggle isActive da review (admin) + ajusta agregados da franchise",
)
def toggle_review_status(
    review_id: int,
    body: ToggleReviewStatusBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    review = db.scalar(
        select(Review)
        .where(Review.id == review_id)
        .options(
            selectinload(Review.author),
            selectinload(Review.responses),
            selectinload(Review.franchise),
        )
    )
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    response_authors = _load_response_authors(db, [review])
    franchise = review.franchise
    franchise_block = (
        {"id": franchise.id, "name": franchise.name, "isActive": bool(franchise.isActive)}
        if franchise is not None
        else None
    )

    if review.isActive == body.isActive:
        # Idempotent: NestJS returns the existing record with a "Review already X" message.
        return {
            "data": _serialize_review_admin(
                review,
                franchise_block=franchise_block,
                response_authors=response_authors,
            ),
            "message": f"Review already {'active' if body.isActive else 'inactive'}",
        }

    review.isActive = body.isActive

    if franchise is not None:
        db.flush()  # garante que o toggle de isActive afete o COUNT no helper
        recalculate_franchise_aggregates(db, franchise.id)

    db.commit()
    db.refresh(review)
    db.refresh(review, attribute_names=["author", "responses"])
    if franchise is not None:
        db.refresh(franchise)
        franchise_block = {
            "id": franchise.id,
            "name": franchise.name,
            "isActive": bool(franchise.isActive),
        }

    # Side effect from NestJS not ported: statisticsService.updateStatisticsAsync()
    logger.warning(
        "[toggle_review_status] review=%s isActive=%s franchise=%s — "
        "skipped statistics async update (service not ported yet)",
        review_id, body.isActive, franchise.id if franchise else None,
    )

    return {
        "data": _serialize_review_admin(
            review,
            franchise_block=franchise_block,
            response_authors=response_authors,
        ),
        "message": f"Review {'activated' if body.isActive else 'deactivated'} successfully",
    }


# ===========================================================================
# Review-responses — admin/franchisor reply to a review
#
#   POST   /reviews/{review_id}/responses    create response (1-per-review)
#   PUT    /reviews/responses/{response_id}  update (admin OR original author)
#   DELETE /reviews/responses/{response_id}  delete (admin OR original author)
# ===========================================================================


class CreateReviewResponseBody(BaseModel):
    content: str = Field(min_length=10, max_length=1000)


class UpdateReviewResponseBody(BaseModel):
    content: Optional[str] = Field(default=None, min_length=10, max_length=1000)


def _serialize_response(rr: ReviewResponse, author: Optional[User]) -> dict[str, Any]:
    return {
        "id": rr.id,
        "content": rr.content,
        "reviewId": rr.reviewId,
        "authorId": rr.authorId,
        "createdAt": _iso(rr.createdAt),
        "updatedAt": _iso(rr.updatedAt),
        "author": (
            {"id": author.id, "name": author.name, "role": author.role}
            if author is not None
            else None
        ),
    }


# ---------------------------------------------------------------------------
# POST /reviews/{review_id}/responses
# ---------------------------------------------------------------------------

@router.post(
    "/{review_id}/responses",
    summary="Cria resposta a uma review (admin/franchisor)",
    status_code=status.HTTP_201_CREATED,
)
def create_review_response(
    review_id: int,
    body: CreateReviewResponseBody,
    user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    review = db.scalar(
        select(Review)
        .where(Review.id == review_id)
        .options(selectinload(Review.franchise))
    )
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review não encontrada"
        )

    franchise = review.franchise
    owner_id = franchise.ownerId if franchise is not None else None
    # FRANCHISOR: must own the franchise of this review. ADMIN: bypass.
    assert_franchise_owner(user, owner_id)

    # NestJS allows only ONE response per review.
    existing = db.scalar(
        select(ReviewResponse.id).where(ReviewResponse.reviewId == review_id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta avaliação já possui uma resposta",
        )

    rr = ReviewResponse(
        content=body.content,
        reviewId=review_id,
        authorId=user.id,
    )
    db.add(rr)
    db.commit()
    db.refresh(rr)

    author = db.scalar(select(User).where(User.id == rr.authorId))
    return _serialize_response(rr, author)


# ---------------------------------------------------------------------------
# PUT /reviews/responses/{response_id}
# ---------------------------------------------------------------------------

@router.put(
    "/responses/{response_id}",
    summary="Atualiza resposta (admin OU autor da resposta)",
)
def update_review_response(
    response_id: int,
    body: UpdateReviewResponseBody,
    user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rr = db.scalar(
        select(ReviewResponse).where(ReviewResponse.id == response_id)
    )
    if rr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada"
        )

    # Per NestJS: ADMIN bypasses; otherwise must be the original author.
    # NOTE: even a FRANCHISOR who currently owns the franchise CANNOT edit a
    # response written by another (e.g. the previous owner) — only the author.
    if user.role != "ADMIN" and rr.authorId != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode editar suas próprias respostas",
        )

    if body.content is not None:
        rr.content = body.content

    db.commit()
    db.refresh(rr)

    author = db.scalar(select(User).where(User.id == rr.authorId))
    return _serialize_response(rr, author)


# ---------------------------------------------------------------------------
# DELETE /reviews/responses/{response_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/responses/{response_id}",
    summary="Apaga resposta (admin OU autor da resposta)",
)
def delete_review_response(
    response_id: int,
    user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    rr = db.scalar(
        select(ReviewResponse).where(ReviewResponse.id == response_id)
    )
    if rr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada"
        )

    if user.role != "ADMIN" and rr.authorId != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode deletar suas próprias respostas",
        )

    db.delete(rr)
    db.commit()
    return {"message": "Resposta deletada com sucesso"}
