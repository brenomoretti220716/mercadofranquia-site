"""
News endpoints — public listing + detail; comments accept POST when authed,
GET is public.

    GET  /news                   paginated + filters (page, limit, search, category)
    GET  /news/{news_id}         single article (active only)
    GET  /news/{news_id}/comments list comments on an article (public)
    POST /news/{news_id}/comments create a comment (auth required; profile must be complete)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import News, NewsComment, User
from app.profile_completion import compute_completion
from app.security import JwtPayload, get_current_user

router = APIRouter(prefix="/news", tags=["news"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _serialize_news(n: News) -> dict[str, Any]:
    return {
        "id": n.id,
        "title": n.title,
        "category": n.category,
        "summary": n.summary,
        "content": n.content,
        "photoUrl": n.photoUrl,
        "isActive": bool(n.isActive),
        "createdAt": _iso(n.createdAt),
        "updatedAt": _iso(n.updatedAt),
    }


def _serialize_comment(c: NewsComment) -> dict[str, Any]:
    author = getattr(c, "author", None)
    return {
        "id": c.id,
        "content": c.content,
        "newsId": c.newsId,
        "authorId": c.authorId,
        "createdAt": _iso(c.createdAt),
        "updatedAt": _iso(c.updatedAt),
        "author": (
            {"id": author.id, "name": author.name, "role": author.role}
            if author is not None
            else None
        ),
    }


class CreateCommentBody(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


@router.get("", summary="Listar notícias (ativas) paginadas")
def list_news(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    stmt = select(News).where(News.isActive.is_(True))
    if category and category.strip():
        stmt = stmt.where(News.category == category.strip())
    if search and search.strip():
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(News.title).like(like),
                func.lower(News.category).like(like),
                func.lower(News.summary).like(like),
                func.lower(News.content).like(like),
            )
        )
    stmt = stmt.order_by(News.createdAt.desc())

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * limit
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()

    return {
        "data": [_serialize_news(n) for n in rows],
        "total": total,
        "page": page,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }


@router.get("/{news_id}", summary="Obter notícia por ID")
def get_news(news_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    n = db.scalar(
        select(News).where(News.id == news_id, News.isActive.is_(True))
    )
    if n is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada"
        )
    return _serialize_news(n)


@router.get("/{news_id}/comments", summary="Listar comentários de uma notícia")
def list_comments(news_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    n = db.scalar(select(News.id).where(News.id == news_id))
    if n is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada"
        )
    stmt = (
        select(NewsComment)
        .where(NewsComment.newsId == news_id)
        .options(selectinload(NewsComment.author))
        .order_by(NewsComment.createdAt.desc())
    )
    return [_serialize_comment(c) for c in db.scalars(stmt).all()]


@router.post("/{news_id}/comments", summary="Comentar em uma notícia")
def create_comment(
    news_id: str,
    body: CreateCommentBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    n = db.scalar(select(News.id).where(News.id == news_id))
    if n is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada"
        )

    # Profile-complete gate, same as NestJS NewsCommentService.
    user = db.scalar(
        select(User)
        .where(User.id == current.id)
        .options(selectinload(User.profile))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not compute_completion(user)["isComplete"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete seu perfil para usar esta funcionalidade",
        )

    comment = NewsComment(
        id=uuid.uuid4().hex,
        content=body.content,
        newsId=news_id,
        authorId=current.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    # load author for response
    db.refresh(comment, attribute_names=["author"])
    return _serialize_comment(comment)
