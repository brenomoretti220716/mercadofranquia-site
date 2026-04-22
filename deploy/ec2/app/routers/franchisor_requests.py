"""
Franchisor request endpoints — the user applies to become a FRANCHISOR
role by submitting CNPJ, responsible person info, and two document files.

    POST /users/franchisor-request            multipart/form-data; creates a PENDING request
    GET  /users/franchisor-request/my-request returns the caller's own request (or null)

Admin approval/rejection endpoints (separate router, /admin/franchisor-requests/*):

    GET  /admin/franchisor-requests/pending       paginated PENDING requests
    GET  /admin/franchisor-requests               paginated requests (any status)
    GET  /admin/franchisor-requests/:id           single request (with reviewer)
    POST /admin/franchisor-requests/:id/approve   approve + create FranchisorUser + bump role
    POST /admin/franchisor-requests/:id/reject    reject with reason

Files are saved under  {UPLOAD_DIR}/franchisor-requests/<userId>/  and the
relative path is stored in the DB.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.constantes import (
    FranchiseStatus,
    FranchisorRequestMode,
    FranchisorRequestStatus,
    UserRole,
)
from app.db import SessionLocal, get_db
from app.models import Franchise, FranchisorRequest, FranchisorUser, User
from app.security import JwtPayload, get_current_user, issue_token, require_role
from app.services import hubspot_client
from app.services.ses_mailer import (
    send_admin_new_franchisor_request,
    send_franchisor_approved,
    send_franchisor_rejected,
    send_franchisor_request_received,
)
from app.user_serializers import serialize_franchisor_request
from app.utils.slug import generate_unique_slug

router = APIRouter(prefix="/users/franchisor-request", tags=["franchisor-requests"])
admin_router = APIRouter(
    prefix="/admin/franchisor-requests", tags=["admin-franchisor-requests"]
)
logger = logging.getLogger("mf-api.franchisor-requests")

class CreateFranchisorRequestBody(BaseModel):
    mode: Literal["NEW", "EXISTING"]
    streamName: Optional[str] = Field(default=None, min_length=2, max_length=191)
    franchiseId: Optional[str] = None
    claimReason: Optional[str] = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _validate_mode_fields(self):
        if self.mode == "NEW":
            if not self.streamName:
                raise ValueError("streamName is required for mode=NEW")
            if self.franchiseId or self.claimReason:
                raise ValueError(
                    "franchiseId and claimReason are not allowed for mode=NEW"
                )
        elif self.mode == "EXISTING":
            if not self.franchiseId:
                raise ValueError("franchiseId is required for mode=EXISTING")
            if self.streamName:
                raise ValueError(
                    "streamName is not allowed for mode=EXISTING (derived from franchise)"
                )
        return self


def _sync_hubspot_for_franchisor_request(
    *,
    user_id: str,
    hubspot_contact_id: Optional[str],
    stream_name: str,
    mode: str,
    franchise_id: Optional[str],
) -> None:
    """Background task: cria Company no HubSpot, atualiza Contact, vincula os dois
    e persiste hubspotCompanyId na FranchisorRequest. Falhas só logam."""

    async def _run() -> Optional[str]:
        company_id = await hubspot_client.create_franchisor_company(
            stream_name=stream_name,
            mode=mode,
            franchise_id=franchise_id,
        )
        if hubspot_contact_id:
            await hubspot_client.update_contact_for_franchisor_request(
                hubspot_contact_id=hubspot_contact_id,
                mode=mode,
            )
        if company_id and hubspot_contact_id:
            await hubspot_client.associate_contact_with_company(
                hubspot_contact_id=hubspot_contact_id,
                hubspot_company_id=company_id,
            )
        return company_id

    try:
        company_id = asyncio.run(_run())
    except Exception as exc:
        logger.exception("Falha na sync HubSpot pro user %s: %s", user_id, exc)
        return

    if not company_id:
        return

    db = SessionLocal()
    try:
        req = db.scalar(
            select(FranchisorRequest)
            .where(FranchisorRequest.userId == user_id)
            .where(FranchisorRequest.status == FranchisorRequestStatus.PENDING)
            .order_by(FranchisorRequest.createdAt.desc())
        )
        if req:
            req.hubspotCompanyId = company_id
            db.commit()
            logger.info(
                "hubspotCompanyId %s salvo na request %s", company_id, req.id
            )
    except Exception as exc:
        logger.exception("Erro persistindo hubspotCompanyId: %s", exc)
        db.rollback()
    finally:
        db.close()


def _sync_hubspot_on_admin_decision(
    *,
    hubspot_contact_id: Optional[str],
    hubspot_company_id: Optional[str],
    decision: str,
) -> None:
    """Background task: aplica status APPROVED/REJECTED em contact+company no
    HubSpot quando admin decide uma request. Falhas só logam."""

    async def _run() -> None:
        if decision == FranchisorRequestStatus.APPROVED:
            if hubspot_contact_id:
                await hubspot_client.mark_contact_approved(hubspot_contact_id)
            if hubspot_company_id:
                await hubspot_client.mark_company_approved(hubspot_company_id)
        elif decision == FranchisorRequestStatus.REJECTED:
            if hubspot_contact_id:
                await hubspot_client.mark_contact_rejected(hubspot_contact_id)
            if hubspot_company_id:
                await hubspot_client.mark_company_rejected(hubspot_company_id)

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha sync HubSpot decisão %s: %s", decision, exc)


# ---------------------------------------------------------------------------
# POST /users/franchisor-request
# ---------------------------------------------------------------------------

@router.post("", summary="Criar solicitação para virar FRANCHISOR")
def create_request(
    body: CreateFranchisorRequestBody,
    background_tasks: BackgroundTasks,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.scalar(select(User).where(User.id == current.id))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    new_access_token: Optional[str] = None

    if body.mode == FranchisorRequestMode.NEW:
        name_clean = body.streamName.strip()
        existing_franchise = db.scalar(
            select(Franchise).where(func.lower(Franchise.name) == name_clean.lower())
        )
        if existing_franchise is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A franquia '{name_clean}' já existe no sistema. "
                    f"Use o modo EXISTING passando franchiseId='{existing_franchise.id}' "
                    f"para reivindicar a franquia existente."
                ),
            )

        same_name_pending = db.scalar(
            select(FranchisorRequest).where(
                FranchisorRequest.userId == current.id,
                FranchisorRequest.streamName == name_clean,
                FranchisorRequest.mode == FranchisorRequestMode.NEW,
                FranchisorRequest.status.in_(
                    [
                        FranchisorRequestStatus.PENDING,
                        FranchisorRequestStatus.UNDER_REVIEW,
                    ]
                ),
            )
        )
        if same_name_pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Você já tem um cadastro pendente para a marca '{name_clean}'. "
                    f"Aguarde a análise ou cancele o cadastro anterior."
                ),
            )

        franchise_slug = generate_unique_slug(name_clean, db)

        new_franchise = Franchise(
            id=uuid.uuid4().hex,
            name=name_clean,
            slug=franchise_slug,
            status=FranchiseStatus.PENDING,
            isActive=False,
            sponsorPlacements={},
            ownerId=user.id,
        )
        db.add(new_franchise)
        db.flush()

        new_request = FranchisorRequest(
            id=uuid.uuid4().hex,
            userId=user.id,
            streamName=name_clean,
            mode=FranchisorRequestMode.NEW,
            franchiseId=new_franchise.id,
            status=FranchisorRequestStatus.PENDING,
        )
        db.add(new_request)

        user.role = UserRole.FRANCHISOR

        db.commit()
        db.refresh(user)

        new_access_token = issue_token(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "isActive": user.isActive,
            }
        )
    else:
        target = db.scalar(select(Franchise).where(Franchise.id == body.franchiseId))
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Franchise not found")
        if target.status != FranchiseStatus.APPROVED:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Only APPROVED franchises can be claimed",
            )

        own_claim_pending = db.scalar(
            select(FranchisorRequest).where(
                FranchisorRequest.userId == current.id,
                FranchisorRequest.franchiseId == target.id,
                FranchisorRequest.mode == FranchisorRequestMode.EXISTING,
                FranchisorRequest.status.in_(
                    [
                        FranchisorRequestStatus.PENDING,
                        FranchisorRequestStatus.UNDER_REVIEW,
                    ]
                ),
            )
        )
        if own_claim_pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Você já tem uma reivindicação pendente para esta franquia.",
            )

        other_claim = db.scalar(
            select(FranchisorRequest).where(
                FranchisorRequest.franchiseId == target.id,
                FranchisorRequest.status.in_(
                    [
                        FranchisorRequestStatus.PENDING,
                        FranchisorRequestStatus.UNDER_REVIEW,
                    ]
                ),
            )
        )
        if other_claim is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Esta franquia já tem uma reivindicação em análise. "
                "Se é você, entre em contato com contato@mercadofranquia.com.br.",
            )

        new_request = FranchisorRequest(
            id=uuid.uuid4().hex,
            userId=user.id,
            streamName=target.name,
            mode=FranchisorRequestMode.EXISTING,
            franchiseId=target.id,
            claimReason=body.claimReason,
            status=FranchisorRequestStatus.PENDING,
        )
        db.add(new_request)

        db.commit()

    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.id == new_request.id)
        .options(
            selectinload(FranchisorRequest.user),
            selectinload(FranchisorRequest.franchise),
        )
    )

    background_tasks.add_task(
        send_franchisor_request_received,
        to=user.email,
        user_name=user.name,
        stream_name=req.streamName,
        mode=req.mode,
    )

    admins_env = os.environ.get("ADMIN_NOTIFICATION_EMAILS", "")
    admin_emails = [e.strip() for e in admins_env.split(",") if e.strip()]
    if admin_emails:
        background_tasks.add_task(
            send_admin_new_franchisor_request,
            to_admins_list=admin_emails,
            user_name=user.name,
            user_email=user.email,
            stream_name=req.streamName,
            mode=req.mode,
            request_id=req.id,
        )

    background_tasks.add_task(
        _sync_hubspot_for_franchisor_request,
        user_id=user.id,
        hubspot_contact_id=user.hubspotContactId,
        stream_name=req.streamName,
        mode=req.mode,
        franchise_id=req.franchiseId,
    )

    response: dict[str, Any] = {
        "request": serialize_franchisor_request(req),  # type: ignore[arg-type]
    }
    if new_access_token is not None:
        response["access_token"] = new_access_token
    return response


# ---------------------------------------------------------------------------
# GET /users/franchisor-request/my-request
# ---------------------------------------------------------------------------

@router.get("/my-request", summary="Solicitação do próprio usuário (ou null)")
def get_my_request(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[dict[str, Any]]:
    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.userId == current.id)
        .options(selectinload(FranchisorRequest.user))
    )
    if req is None:
        return None
    return serialize_franchisor_request(req)


# ===========================================================================
# Admin endpoints — under /admin/franchisor-requests
# All require role == ADMIN.
# ===========================================================================


class ApproveRequestBody(BaseModel):
    ownedFranchises: list[str] = Field(min_length=1)


class RejectRequestBody(BaseModel):
    rejectionReason: str = Field(min_length=10)


def _serialize_admin_request(
    r: FranchisorRequest,
    *,
    reviewer_map: dict[str, dict[str, Any]],
    user_extra_fields: bool = False,
) -> dict[str, Any]:
    """Admin-listing shape — like serialize_franchisor_request but the embedded
    `user` block carries phone+cpf (and optionally createdAt for getRequestById)
    and includes a `reviewer` block."""
    user_block: Optional[dict[str, Any]] = None
    if getattr(r, "user", None) is not None:
        user_block = {
            "id": r.user.id,
            "name": r.user.name,
            "email": r.user.email,
            "phone": r.user.phone,
            "cpf": r.user.cpf,
        }
        if user_extra_fields:
            user_block["createdAt"] = r.user.createdAt.isoformat() if r.user.createdAt else None

    franchise_block: Optional[dict[str, Any]] = None
    if getattr(r, "franchise", None) is not None:
        franchise_block = {
            "id": r.franchise.id,
            "name": r.franchise.name,
            "logoUrl": getattr(r.franchise, "logoUrl", None),
            "status": r.franchise.status,
        }

    return {
        "id": r.id,
        "userId": r.userId,
        "streamName": r.streamName,
        "mode": r.mode,
        "franchiseId": r.franchiseId,
        "claimReason": r.claimReason,
        "hubspotCompanyId": r.hubspotCompanyId,
        "status": r.status,
        "rejectionReason": r.rejectionReason,
        "reviewedBy": r.reviewedBy,
        "reviewedAt": r.reviewedAt.isoformat() if r.reviewedAt else None,
        "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        "updatedAt": r.updatedAt.isoformat() if r.updatedAt else None,
        "user": user_block,
        "reviewer": reviewer_map.get(r.reviewedBy) if r.reviewedBy else None,
        "franchise": franchise_block,
    }


def _load_reviewer_map(
    db: Session, requests: list[FranchisorRequest]
) -> dict[str, dict[str, Any]]:
    """Batch-load reviewer User rows for a list of requests. Returns
    {userId: {id,name,email}}."""
    ids = {r.reviewedBy for r in requests if r.reviewedBy}
    if not ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: {"id": u.id, "name": u.name, "email": u.email} for u in users}


def _admin_search_clause(search: Optional[str]) -> Optional[Any]:
    """OR(user.name ilike, user.email ilike, streamName ilike)."""
    if not search or not search.strip():
        return None
    pat = f"%{search.strip()}%"
    return or_(
        User.name.ilike(pat),
        User.email.ilike(pat),
        FranchisorRequest.streamName.ilike(pat),
    )


# ---------------------------------------------------------------------------
# GET /admin/franchisor-requests/pending
# ---------------------------------------------------------------------------

@admin_router.get("/pending", summary="Lista solicitações PENDING")
def get_pending_requests(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    page = max(page, 1)
    limit = max(limit, 1)
    skip = (page - 1) * limit

    base = (
        select(FranchisorRequest)
        .join(User, FranchisorRequest.userId == User.id)
        .where(FranchisorRequest.status == "PENDING")
    )
    search_clause = _admin_search_clause(search)
    if search_clause is not None:
        base = base.where(search_clause)

    items = db.scalars(
        base.options(selectinload(FranchisorRequest.user))
        .order_by(FranchisorRequest.createdAt.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    count_stmt = (
        select(func.count())
        .select_from(FranchisorRequest)
        .join(User, FranchisorRequest.userId == User.id)
        .where(FranchisorRequest.status == "PENDING")
    )
    if search_clause is not None:
        count_stmt = count_stmt.where(search_clause)
    total = db.scalar(count_stmt) or 0

    reviewer_map = _load_reviewer_map(db, items)

    return {
        "data": [_serialize_admin_request(r, reviewer_map=reviewer_map) for r in items],
        "total": total,
        "page": page,
        "lastPage": max(1, (total + limit - 1) // limit),
    }


# ---------------------------------------------------------------------------
# GET /admin/franchisor-requests
# ---------------------------------------------------------------------------

@admin_router.get("", summary="Lista todas as solicitações (filtro opcional por status)")
def get_all_requests(
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    search: Optional[str] = None,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    page = max(page, 1)
    limit = max(limit, 1)
    skip = (page - 1) * limit

    base = select(FranchisorRequest).join(User, FranchisorRequest.userId == User.id)
    count_base = (
        select(func.count())
        .select_from(FranchisorRequest)
        .join(User, FranchisorRequest.userId == User.id)
    )
    if status:
        base = base.where(FranchisorRequest.status == status)
        count_base = count_base.where(FranchisorRequest.status == status)
    search_clause = _admin_search_clause(search)
    if search_clause is not None:
        base = base.where(search_clause)
        count_base = count_base.where(search_clause)

    items = db.scalars(
        base.options(selectinload(FranchisorRequest.user))
        .order_by(FranchisorRequest.createdAt.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    total = db.scalar(count_base) or 0

    reviewer_map = _load_reviewer_map(db, items)

    return {
        "data": [_serialize_admin_request(r, reviewer_map=reviewer_map) for r in items],
        "total": total,
        "page": page,
        "lastPage": max(1, (total + limit - 1) // limit),
    }


# ---------------------------------------------------------------------------
# GET /admin/franchisor-requests/:id
# ---------------------------------------------------------------------------

@admin_router.get("/{request_id}", summary="Solicitação por id")
def get_request_by_id(
    request_id: str,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.id == request_id)
        .options(selectinload(FranchisorRequest.user))
    )
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    reviewer_map = _load_reviewer_map(db, [req])
    return _serialize_admin_request(
        req, reviewer_map=reviewer_map, user_extra_fields=True
    )


# ---------------------------------------------------------------------------
# POST /admin/franchisor-requests/:id/approve
# ---------------------------------------------------------------------------

@admin_router.post("/{request_id}/approve", summary="Aprovar solicitação")
def approve_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    current: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.id == request_id)
        .options(
            selectinload(FranchisorRequest.user),
            selectinload(FranchisorRequest.franchise),
        )
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status == FranchisorRequestStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Request already approved")

    user = req.user
    if user is None:
        raise HTTPException(status_code=500, detail="Request has no associated user")

    if req.mode == FranchisorRequestMode.NEW:
        franchise = req.franchise
        if franchise is None:
            raise HTTPException(
                status_code=500,
                detail="NEW request sem franchise associada — inconsistência de dados",
            )
        franchise.status = FranchiseStatus.APPROVED
        franchise.isActive = True
        # user.role já é FRANCHISOR desde o create_request
    elif req.mode == FranchisorRequestMode.EXISTING:
        user.role = UserRole.FRANCHISOR
        franchise = req.franchise
        if franchise is not None:
            franchise.ownerId = user.id
    else:
        raise HTTPException(
            status_code=500,
            detail=f"mode desconhecido: {req.mode}",
        )

    req.status = FranchisorRequestStatus.APPROVED
    req.rejectionReason = None
    req.reviewedBy = current.id
    req.reviewedAt = datetime.utcnow()

    existing_fu = db.scalar(
        select(FranchisorUser).where(FranchisorUser.userId == user.id)
    )
    if existing_fu is None:
        db.add(
            FranchisorUser(
                id=uuid.uuid4().hex,
                userId=user.id,
                streamName=req.streamName,
            )
        )

    db.commit()
    db.refresh(req)

    background_tasks.add_task(
        send_franchisor_approved,
        to=user.email,
        user_name=user.name,
        stream_name=req.streamName,
    )
    background_tasks.add_task(
        _sync_hubspot_on_admin_decision,
        hubspot_contact_id=user.hubspotContactId,
        hubspot_company_id=req.hubspotCompanyId,
        decision=FranchisorRequestStatus.APPROVED,
    )

    return {"message": "Request approved successfully", "requestId": req.id}


# ---------------------------------------------------------------------------
# POST /admin/franchisor-requests/:id/reject
# ---------------------------------------------------------------------------

@admin_router.post("/{request_id}/reject", summary="Rejeitar solicitação")
def reject_request(
    request_id: str,
    body: RejectRequestBody,
    background_tasks: BackgroundTasks,
    current: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not body.rejectionReason or len(body.rejectionReason.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="rejectionReason is required and cannot be empty",
        )

    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.id == request_id)
        .options(
            selectinload(FranchisorRequest.user),
            selectinload(FranchisorRequest.franchise),
        )
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status == FranchisorRequestStatus.REJECTED:
        raise HTTPException(status_code=409, detail="Request already rejected")

    user = req.user
    if user is None:
        raise HTTPException(status_code=500, detail="Request has no associated user")

    if req.mode == FranchisorRequestMode.NEW:
        franchise = req.franchise
        if franchise is not None:
            franchise.status = FranchiseStatus.REJECTED
            franchise.isActive = False
        user.role = UserRole.MEMBER
    elif req.mode == FranchisorRequestMode.EXISTING:
        pass

    req.status = FranchisorRequestStatus.REJECTED
    req.rejectionReason = body.rejectionReason.strip()
    req.reviewedBy = current.id
    req.reviewedAt = datetime.utcnow()

    db.commit()
    db.refresh(req)

    background_tasks.add_task(
        send_franchisor_rejected,
        to=user.email,
        user_name=user.name,
        stream_name=req.streamName,
        rejection_reason=req.rejectionReason,
    )
    background_tasks.add_task(
        _sync_hubspot_on_admin_decision,
        hubspot_contact_id=user.hubspotContactId,
        hubspot_company_id=req.hubspotCompanyId,
        decision=FranchisorRequestStatus.REJECTED,
    )

    return {"message": "Request rejected successfully", "requestId": req.id}


# ---------------------------------------------------------------------------
# POST /admin/franchisor-requests/:id/reopen
# ---------------------------------------------------------------------------

@admin_router.post(
    "/{request_id}/reopen",
    summary="Reabre uma request rejeitada (volta a PENDING)",
)
def reopen_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    current: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.id == request_id)
        .options(
            selectinload(FranchisorRequest.user),
            selectinload(FranchisorRequest.franchise),
        )
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != FranchisorRequestStatus.REJECTED:
        raise HTTPException(
            status_code=409,
            detail=f"Só é possível reabrir requests REJECTED. Status atual: {req.status}",
        )

    user = req.user
    if user is None:
        raise HTTPException(status_code=500, detail="Request has no associated user")

    if req.mode == FranchisorRequestMode.NEW:
        franchise = req.franchise
        if franchise is not None:
            franchise.status = FranchiseStatus.PENDING
            franchise.isActive = False
        user.role = UserRole.FRANCHISOR
    elif req.mode == FranchisorRequestMode.EXISTING:
        pass

    req.status = FranchisorRequestStatus.PENDING
    req.rejectionReason = None
    req.reviewedBy = None
    req.reviewedAt = None

    db.commit()
    db.refresh(req)

    hubspot_contact_id = user.hubspotContactId
    mode = req.mode

    def _reopen_hubspot() -> None:
        async def _run() -> None:
            if hubspot_contact_id:
                await hubspot_client.update_contact_for_franchisor_request(
                    hubspot_contact_id=hubspot_contact_id,
                    mode=mode,
                )

        try:
            asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha reopen HubSpot: %s", exc)

    background_tasks.add_task(_reopen_hubspot)

    return {"message": "Request reopened successfully", "requestId": req.id}
