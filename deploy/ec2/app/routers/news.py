"""
News endpoints — public listing + detail; comments accept POST when authed,
GET is public.

    GET  /news                   paginated + filters (page, limit, search, category)
    GET  /news/{news_id}         single article (active only)
    GET  /news/{news_id}/comments list comments on an article (public)
    POST /news/{news_id}/comments create a comment (auth required; profile must be complete)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from math import ceil
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import News, NewsComment, User
from app.profile_completion import compute_completion
from app.security import JwtPayload, get_current_user, require_role
from app.storage import delete_uploaded_file, save_image_upload

router = APIRouter(prefix="/news", tags=["news"])
logger = logging.getLogger("mf-api.news")


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


# ===========================================================================
# Admin endpoints — multipart/form-data
#
#   POST /news        — create news, photo REQUIRED
#   PUT  /news/{id}   — update news, photo OPTIONAL
#
# Both require role == ADMIN. Photo is uploaded via app.storage; the public
# URL `/uploads/news/<uuid><ext>` is stored in News.photoUrl.
# ===========================================================================


@router.post("", summary="Cria notícia (admin) — multipart com foto", status_code=status.HTTP_201_CREATED)
def create_news(
    title: str = Form(..., min_length=1, max_length=200),
    category: str = Form(..., min_length=1, max_length=100),
    summary: str = Form(..., min_length=1, max_length=500),
    content: str = Form(..., min_length=10, max_length=2000),
    photo: UploadFile = File(..., description="Imagem (JPEG/PNG/GIF/WebP, ≤5MB)"),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    photo_url = save_image_upload(photo, "news")

    news = News(
        id=uuid.uuid4().hex,
        title=title,
        category=category,
        summary=summary,
        content=content,
        photoUrl=photo_url,
        isActive=True,
    )
    try:
        db.add(news)
        db.commit()
        db.refresh(news)
    except Exception:
        # If DB write fails, drop the orphaned upload so we don't leave dead bytes.
        delete_uploaded_file(photo_url)
        raise

    return _serialize_news(news)


@router.put("/{news_id}", summary="Atualiza notícia (admin) — multipart, foto opcional")
def update_news(
    news_id: str,
    title: Optional[str] = Form(None, min_length=1, max_length=200),
    category: Optional[str] = Form(None, min_length=1, max_length=100),
    summary: Optional[str] = Form(None, min_length=1, max_length=500),
    content: Optional[str] = Form(None, min_length=10, max_length=2000),
    isActive: Optional[bool] = Form(None),
    photo: Optional[UploadFile] = File(None),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    n = db.scalar(select(News).where(News.id == news_id))
    if n is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notícia não encontrada"
        )

    # FastAPI sends an empty UploadFile (filename="") when the field is omitted
    # in some clients. Treat empty filename as "no photo provided".
    photo_provided = photo is not None and bool(photo.filename)

    new_photo_url: Optional[str] = None
    if photo_provided:
        # Upload first; if upload raises, DB is untouched and old photo stays.
        new_photo_url = save_image_upload(photo, "news")

    old_photo_url = n.photoUrl

    if title is not None:
        n.title = title
    if category is not None:
        n.category = category
    if summary is not None:
        n.summary = summary
    if content is not None:
        n.content = content
    if isActive is not None:
        n.isActive = isActive
    if new_photo_url is not None:
        n.photoUrl = new_photo_url

    try:
        db.commit()
        db.refresh(n)
    except Exception:
        # Roll back the orphan upload if DB write fails.
        if new_photo_url:
            delete_uploaded_file(new_photo_url)
        raise

    # DB write succeeded — now safe to drop the previous file. Best-effort,
    # never fails the request if the file is already gone.
    if new_photo_url and old_photo_url and old_photo_url != new_photo_url:
        delete_uploaded_file(old_photo_url)

    return _serialize_news(n)
