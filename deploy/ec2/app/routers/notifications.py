"""
Notifications endpoints — all auth required.

    GET    /notifications                paginated list (unreadOnly flag)
    GET    /notifications/stats          {unread, total, hasUnread}
    PATCH  /notifications/mark-read      body: {notificationIds:[...]} — bulk
    POST   /notifications/mark-all-read  mark every unread
    PUT    /notifications/{id}/read      mark a single one read (convenience; matches user-requested shape)
    DELETE /notifications/{id}           delete
"""
from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Notification
from app.security import JwtPayload, get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _serialize(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "userId": n.userId,
        "title": n.title,
        "message": n.message,
        "type": n.type,
        "link": n.link,
        "isRead": bool(n.isRead),
        "createdAt": _iso(n.createdAt),
        "readAt": _iso(n.readAt),
    }


class MarkAsReadBody(BaseModel):
    notificationIds: list[str] = Field(min_length=1)


# ---------------------------------------------------------------------------
# GET /notifications
# ---------------------------------------------------------------------------

@router.get("", summary="Listar notificações do usuário")
def list_notifications(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    unreadOnly: bool = Query(False),
) -> dict[str, Any]:
    base = select(Notification).where(Notification.userId == current.id)
    if unreadOnly:
        base = base.where(Notification.isRead.is_(False))
    base = base.order_by(Notification.createdAt.desc())

    total = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.userId == current.id,
            *([Notification.isRead.is_(False)] if unreadOnly else []),
        )
    ) or 0
    offset = (page - 1) * limit
    rows = db.scalars(base.offset(offset).limit(limit)).all()

    return {
        "data": [_serialize(n) for n in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }


# ---------------------------------------------------------------------------
# GET /notifications/stats
# ---------------------------------------------------------------------------

@router.get("/stats", summary="Contador de notificações")
def stats(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    total = db.scalar(
        select(func.count(Notification.id)).where(Notification.userId == current.id)
    ) or 0
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.userId == current.id,
            Notification.isRead.is_(False),
        )
    ) or 0
    return {"total": total, "unread": unread, "hasUnread": unread > 0}


# ---------------------------------------------------------------------------
# PATCH /notifications/mark-read  — bulk mark
# ---------------------------------------------------------------------------

@router.patch("/mark-read", summary="Marcar notificações como lidas (em massa)")
def mark_as_read(
    body: MarkAsReadBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.utcnow()
    result = db.execute(
        update(Notification)
        .where(
            Notification.id.in_(body.notificationIds),
            Notification.userId == current.id,
            Notification.isRead.is_(False),
        )
        .values(isRead=True, readAt=now)
    )
    db.commit()
    return {"updated": result.rowcount or 0}


# ---------------------------------------------------------------------------
# POST /notifications/mark-all-read
# ---------------------------------------------------------------------------

@router.post("/mark-all-read", summary="Marcar todas como lidas")
def mark_all_as_read(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.utcnow()
    result = db.execute(
        update(Notification)
        .where(
            Notification.userId == current.id,
            Notification.isRead.is_(False),
        )
        .values(isRead=True, readAt=now)
    )
    db.commit()
    return {"updated": result.rowcount or 0}


# ---------------------------------------------------------------------------
# PUT /notifications/{id}/read  — single mark (user-requested shape)
# ---------------------------------------------------------------------------

@router.put("/{notif_id}/read", summary="Marcar uma notificação como lida")
def mark_single_read(
    notif_id: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    n = db.scalar(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.userId == current.id,
        )
    )
    if n is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificação não encontrada",
        )
    if not n.isRead:
        n.isRead = True
        n.readAt = datetime.utcnow()
        db.commit()
        db.refresh(n)
    return _serialize(n)


# ---------------------------------------------------------------------------
# DELETE /notifications/{id}
# ---------------------------------------------------------------------------

@router.delete("/{notif_id}", summary="Excluir notificação")
def delete_notification(
    notif_id: str,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    n = db.scalar(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.userId == current.id,
        )
    )
    if n is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificação não encontrada",
        )
    db.delete(n)
    db.commit()
    return {"success": True}
