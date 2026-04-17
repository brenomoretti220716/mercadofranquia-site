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

import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Franchise, FranchisorRequest, FranchisorUser, User
from app.security import JwtPayload, get_current_user, require_role
from app.user_serializers import serialize_franchisor_request
from app.validators import strip_non_digits, validate_cnpj, validate_phone_digits

router = APIRouter(prefix="/users/franchisor-request", tags=["franchisor-requests"])
admin_router = APIRouter(
    prefix="/admin/franchisor-requests", tags=["admin-franchisor-requests"]
)
logger = logging.getLogger("mf-api.franchisor-requests")

UPLOAD_ROOT = Path(os.environ.get("UPLOAD_PATH", "./uploads")).resolve()
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _safe_ext(filename: Optional[str]) -> str:
    if not filename:
        return ""
    ext = Path(filename).suffix.lower()
    return ext if ext in ALLOWED_EXTS else ""


def _save_upload(upload: UploadFile, *, user_id: str, slot: str) -> str:
    ext = _safe_ext(upload.filename)
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type for {slot}; allowed: {', '.join(sorted(ALLOWED_EXTS))}",
        )
    content = upload.file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({slot}); max {MAX_FILE_BYTES // (1024 * 1024)} MB",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Empty file for {slot}",
        )
    safe_user = re.sub(r"[^A-Za-z0-9_.-]", "", user_id)[:64] or "user"
    dest_dir = UPLOAD_ROOT / "franchisor-requests" / safe_user
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{slot}-{uuid.uuid4().hex}{ext}"
    dest = dest_dir / name
    with open(dest, "wb") as f:
        f.write(content)
    # Return path relative to the upload root so it's portable.
    return f"franchisor-requests/{safe_user}/{name}"


# ---------------------------------------------------------------------------
# POST /users/franchisor-request
# ---------------------------------------------------------------------------

@router.post("", summary="Criar solicitação para virar FRANCHISOR")
def create_request(
    streamName: str = Form(..., min_length=1),
    cnpj: str = Form(..., min_length=1),
    responsable: str = Form(..., min_length=1),
    responsableRole: str = Form(..., min_length=1),
    commercialEmail: str = Form(..., min_length=1),
    commercialPhone: str = Form(..., min_length=1),
    cnpjCard: UploadFile = File(...),
    socialContract: UploadFile = File(...),
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Validations mirror the Zod stepThreeSchema.
    if not validate_cnpj(cnpj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CNPJ"
        )
    if not validate_phone_digits(commercialPhone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Commercial phone must have 10 or 11 digits",
        )

    # Simple e-mail sanity (full RFC validation is overkill here;
    # Pydantic's EmailStr needs a BaseModel, which is awkward with Form fields).
    if "@" not in commercialEmail or "." not in commercialEmail.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format"
        )

    cnpj_digits = strip_non_digits(cnpj)
    phone_digits = strip_non_digits(commercialPhone)

    # Uniqueness checks (one request per user; one per CNPJ).
    existing_by_user = db.scalar(
        select(FranchisorRequest).where(FranchisorRequest.userId == current.id)
    )
    if existing_by_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending request",
        )
    existing_by_cnpj = db.scalar(
        select(FranchisorRequest).where(FranchisorRequest.cnpj == cnpj_digits)
    )
    if existing_by_cnpj is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="CNPJ already in use"
        )

    cnpj_path = _save_upload(cnpjCard, user_id=current.id, slot="cnpjCard")
    contract_path = _save_upload(socialContract, user_id=current.id, slot="socialContract")

    req = FranchisorRequest(
        id=uuid.uuid4().hex,
        userId=current.id,
        streamName=streamName,
        cnpj=cnpj_digits,
        cnpjCardPath=cnpj_path,
        socialContractPath=contract_path,
        responsable=responsable,
        responsableRole=responsableRole,
        commercialEmail=commercialEmail,
        commercialPhone=phone_digits,
        status="PENDING",
    )
    db.add(req)
    db.commit()

    # Re-load with user relation for the response.
    req = db.scalar(
        select(FranchisorRequest)
        .where(FranchisorRequest.id == req.id)
        .options(selectinload(FranchisorRequest.user))
    )
    return serialize_franchisor_request(req)  # type: ignore[arg-type]


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

    return {
        "id": r.id,
        "userId": r.userId,
        "streamName": r.streamName,
        "cnpj": r.cnpj,
        "cnpjCardPath": r.cnpjCardPath,
        "socialContractPath": r.socialContractPath,
        "responsable": r.responsable,
        "responsableRole": r.responsableRole,
        "commercialEmail": r.commercialEmail,
        "commercialPhone": r.commercialPhone,
        "status": r.status,
        "rejectionReason": r.rejectionReason,
        "reviewedBy": r.reviewedBy,
        "reviewedAt": r.reviewedAt.isoformat() if r.reviewedAt else None,
        "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        "updatedAt": r.updatedAt.isoformat() if r.updatedAt else None,
        "user": user_block,
        "reviewer": reviewer_map.get(r.reviewedBy) if r.reviewedBy else None,
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
    """OR(user.name ilike, user.email ilike, cnpj contains)."""
    if not search or not search.strip():
        return None
    pat = f"%{search.strip()}%"
    return or_(
        User.name.ilike(pat),
        User.email.ilike(pat),
        FranchisorRequest.cnpj.contains(search.strip()),
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
    body: ApproveRequestBody,
    admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    req = db.scalar(select(FranchisorRequest).where(FranchisorRequest.id == request_id))
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "PENDING":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Request has already been reviewed"
        )

    franchises = db.scalars(
        select(Franchise)
        .where(Franchise.id.in_(body.ownedFranchises))
        .options(selectinload(Franchise.owner))
    ).all()
    if len(franchises) != len(body.ownedFranchises):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "One or more franchises do not exist"
        )
    already_owned = [f for f in franchises if f.owner is not None]
    if already_owned:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Uma ou mais franquias selecionadas já estão vinculadas a outro franqueador. "
            "Atualize a lista e tente novamente.",
        )

    # Single SQLAlchemy unit-of-work — all writes commit together; any raise
    # before commit means nothing is persisted (FastAPI's get_db closes the
    # session without commit on exceptions).
    now = datetime.utcnow()
    req.status = "APPROVED"
    req.reviewedBy = admin.id
    req.reviewedAt = now

    db.add(
        FranchisorUser(
            id=uuid.uuid4().hex,
            userId=req.userId,
            streamName=req.streamName,
            cnpj=req.cnpj,
            cnpjCardPath=req.cnpjCardPath,
            socialContractPath=req.socialContractPath,
            responsable=req.responsable,
            responsableRole=req.responsableRole,
            commercialEmail=req.commercialEmail,
            commercialPhone=req.commercialPhone,
        )
    )

    target = db.scalar(select(User).where(User.id == req.userId))
    if target is None:
        # Should be impossible (FK), but guard against orphaned data.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target user not found")
    target.role = "FRANCHISOR"

    for f in franchises:
        f.ownerId = req.userId

    db.commit()

    # Side effects from NestJS that we don't have ports for yet:
    #   - emailService.sendUserUpdateNotification
    #   - notificationsService.notifyRequestApproved
    # Logged so it's traceable until those services are ported.
    logger.warning(
        "[approve_request] approved request=%s for user=%s by admin=%s — "
        "skipped email + in-app notification (services not ported yet)",
        req.id,
        req.userId,
        admin.id,
    )

    return {"message": "Request approved successfully"}


# ---------------------------------------------------------------------------
# POST /admin/franchisor-requests/:id/reject
# ---------------------------------------------------------------------------

@admin_router.post("/{request_id}/reject", summary="Rejeitar solicitação")
def reject_request(
    request_id: str,
    body: RejectRequestBody,
    admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    req = db.scalar(select(FranchisorRequest).where(FranchisorRequest.id == request_id))
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "PENDING":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Request has already been reviewed"
        )

    req.status = "REJECTED"
    req.rejectionReason = body.rejectionReason
    req.reviewedBy = admin.id
    req.reviewedAt = datetime.utcnow()
    db.commit()

    logger.warning(
        "[reject_request] rejected request=%s for user=%s by admin=%s — "
        "skipped email + in-app notification (services not ported yet)",
        req.id,
        req.userId,
        admin.id,
    )

    return {"message": "Request rejected successfully"}
