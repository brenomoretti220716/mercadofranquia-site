"""
User self-service endpoints (authenticated).

    GET  /users/me                      current user hydrated with profile + franchiseeOf
    PUT  /users/me                      update name/phone/cpf (own only unless admin)
    PUT  /users/me/password             change password
    GET  /users/me/profile-completion   {isComplete, completionPercentage, missingFields}
    POST /users/me/request-email-change generate verification code for a new e-mail
    POST /users/me/verify-email-change  confirm code and swap the e-mail
    PUT  /users/profile                 update role / city / sectors / region / investment range
                                        (returns new access_token if role changed)
"""
from __future__ import annotations

import json
import logging
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import AdminActionLog, Franchise, ProfileType, User, UserProfile, UserVerification
from app.profile_completion import compute_completion
from app.security import (
    JwtPayload,
    get_current_user,
    hash_password,
    issue_token,
    require_role,
)
from app.user_serializers import (
    serialize_user,
    serialize_user_admin_admin,
    serialize_user_admin_franchisor,
    serialize_user_admin_member,
)
from app.validators import strip_non_digits, validate_cpf, validate_phone_digits

router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin", tags=["admin-users"])
logger = logging.getLogger("mf-api.users")

# Roles considered "members" in admin listings (mirrors MembersService.findMembersPaginated).
MEMBER_ROLES = ("FRANCHISEE", "CANDIDATE", "ENTHUSIAST", "MEMBER")
# Subset used for active/inactive counters (MEMBER excluded — matches NestJS).
MEMBER_ROLES_FOR_COUNTERS = ("FRANCHISEE", "CANDIDATE", "ENTHUSIAST")

ROLE_LITERAL = Literal["FRANCHISEE", "CANDIDATE", "ENTHUSIAST", "FRANCHISOR"]

EMAIL_CHANGE_TTL_MINUTES = 15
EMAIL_CHANGE_TYPE = "email-change"


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class UpdateBasicInfoBody(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    phone: Optional[str] = None
    cpf: Optional[str] = None
    isActive: Optional[bool] = None  # only Admin can actually toggle

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not validate_phone_digits(v):
            raise ValueError("Phone must have 10 or 11 digits")
        return strip_non_digits(v)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        digits = strip_non_digits(v)
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not validate_cpf(v):
            raise ValueError("Invalid CPF")
        return digits


class UpdatePasswordBody(BaseModel):
    password: str = Field(min_length=6)
    confirmPassword: str

    @field_validator("confirmPassword")
    @classmethod
    def _match(cls, v: str, info) -> str:
        pwd = info.data.get("password")
        if pwd is not None and pwd != v:
            raise ValueError("Passwords do not match")
        return v


class RequestEmailChangeBody(BaseModel):
    newEmail: EmailStr


class VerifyEmailChangeBody(BaseModel):
    newEmail: EmailStr
    code: str = Field(min_length=6, max_length=6)


class UpdateProfileBody(BaseModel):
    city: Optional[str] = Field(default=None, min_length=1)
    interestSectors: Optional[str] = Field(default=None, min_length=1)
    interestRegion: Optional[str] = Field(default=None, min_length=1)
    investmentRange: Optional[str] = Field(default=None, min_length=1)
    role: Optional[ROLE_LITERAL] = None
    franchiseeOf: Optional[list[str]] = None

    @field_validator("franchiseeOf")
    @classmethod
    def _role_needs_franchises(
        cls, v: Optional[list[str]], info
    ) -> Optional[list[str]]:
        if info.data.get("role") == "FRANCHISEE":
            if not v or len(v) == 0:
                raise ValueError(
                    "FRANCHISEE role requires at least one franchise to be linked"
                )
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_code() -> str:
    return f"{random.randint(100000, 999999)}"


def _utcnow() -> datetime:
    return datetime.utcnow()


def _expires_at(minutes: int) -> datetime:
    return _utcnow() + timedelta(minutes=minutes)


def _dispatch_email_change_email(
    *, to: str, code: str, expires_at: datetime, user_name: str, old_email: str
) -> None:
    """Stub — log instead of sending. Replace with SMTP when available."""
    logger.warning(
        "[EMAIL CHANGE CODE] user_name=%s from=%s to=%s code=%s expires_at=%s"
        " (email not actually sent — stub)",
        user_name,
        old_email,
        to,
        code,
        expires_at.isoformat(),
    )


def _load_full_user(db: Session, user_id: str) -> Optional[User]:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.profile),
            selectinload(User.franchisor_profile),
            selectinload(User.franchises_as_franchisee),
        )
    )


def _validate_franchises_exist(db: Session, ids: list[str]) -> None:
    if not ids:
        return
    existing = set(
        db.scalars(select(Franchise.id).where(Franchise.id.in_(ids))).all()
    )
    missing = [fid for fid in ids if fid not in existing]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Franchises with IDs {', '.join(missing)} do not exist",
        )


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

@router.get("/me", summary="Usuário autenticado (hidratado)")
def get_me(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, current.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return serialize_user(user)


# ---------------------------------------------------------------------------
# PUT /users/me  — update basic info (name/phone/cpf)
# ---------------------------------------------------------------------------

@router.put("/me", summary="Atualizar dados básicos")
def update_me(
    body: UpdateBasicInfoBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, current.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if body.phone is not None and body.phone != user.phone:
        clashing = db.scalar(
            select(User).where(User.phone == body.phone, User.id != user.id)
        )
        if clashing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Phone already in use"
            )
    if body.cpf is not None and body.cpf != user.cpf:
        clashing = db.scalar(
            select(User).where(User.cpf == body.cpf, User.id != user.id)
        )
        if clashing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="CPF already in use"
            )
    if body.isActive is not None and current.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change account status",
        )

    if body.name is not None:
        user.name = body.name
    if body.phone is not None:
        user.phone = body.phone
    if body.cpf is not None:
        user.cpf = body.cpf
    if body.isActive is not None and current.role == "ADMIN":
        user.isActive = body.isActive

    db.commit()
    db.refresh(user)
    return {"user": serialize_user(user)}


# ---------------------------------------------------------------------------
# PUT /users/me/password
# ---------------------------------------------------------------------------

@router.put("/me/password", summary="Atualizar senha")
def update_password(
    body: UpdatePasswordBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, current.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return {"message": "Senha atualizada com sucesso", "user": serialize_user(user)}


# ---------------------------------------------------------------------------
# GET /users/me/profile-completion
# ---------------------------------------------------------------------------

@router.get("/me/profile-completion", summary="Status de completude do perfil")
def profile_completion(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, current.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return compute_completion(user)


# ---------------------------------------------------------------------------
# POST /users/me/request-email-change
# ---------------------------------------------------------------------------

@router.post("/me/request-email-change", summary="Solicitar código para trocar e-mail")
def request_email_change(
    body: RequestEmailChangeBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.scalar(select(User).where(User.id == current.id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if body.newEmail == user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O novo email deve ser diferente do email atual",
        )
    clashing = db.scalar(select(User).where(User.email == body.newEmail))
    if clashing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este email já está em uso"
        )

    # Refuse if there is already an active (unused, not expired) email-change
    # code for this userId — rate-limit behavior identical to NestJS.
    now = _utcnow()
    stmt = (
        select(UserVerification)
        .where(
            UserVerification.isUsed.is_(False),
            UserVerification.expiresAt > now,
        )
        .order_by(UserVerification.createdAt.desc())
    )
    for rec in db.scalars(stmt).all():
        if not rec.userData:
            continue
        try:
            parsed = json.loads(rec.userData)
        except (json.JSONDecodeError, TypeError):
            continue
        if (
            isinstance(parsed, dict)
            and parsed.get("type") == EMAIL_CHANGE_TYPE
            and parsed.get("userId") == current.id
        ):
            mins = max(1, int((rec.expiresAt - now).total_seconds() // 60))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "expiresIn": mins,
                    "message": f"Um código já foi enviado. Aguarde {mins} minuto(s) antes de solicitar um novo código.",
                },
            )

    code = _generate_code()
    expires_at = _expires_at(EMAIL_CHANGE_TTL_MINUTES)

    db.add(UserVerification(
        # For email changes we key by the NEW email — that's where the user
        # will receive the code, and verify-email-change looks it up by newEmail.
        email=body.newEmail,
        code=code,
        expiresAt=expires_at,
        isUsed=False,
        userData=json.dumps({
            "type": EMAIL_CHANGE_TYPE,
            "userId": current.id,
            "oldEmail": user.email,
            "newEmail": body.newEmail,
        }),
    ))
    db.commit()

    _dispatch_email_change_email(
        to=body.newEmail,
        code=code,
        expires_at=expires_at,
        user_name=user.name,
        old_email=user.email,
    )

    return {
        "message": "Código de verificação enviado para seu novo email",
        "expiresAt": expires_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /users/me/verify-email-change
# ---------------------------------------------------------------------------

@router.post("/me/verify-email-change", summary="Confirmar código e trocar e-mail")
def verify_email_change(
    body: VerifyEmailChangeBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rec = db.scalar(
        select(UserVerification).where(
            UserVerification.email == body.newEmail,
            UserVerification.code == body.code,
            UserVerification.isUsed.is_(False),
        )
    )

    def _reject_invalid() -> None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou já utilizado",
        )

    if rec is None or not rec.userData:
        _reject_invalid()

    assert rec is not None  # silences type checker
    try:
        parsed = json.loads(rec.userData)  # type: ignore[arg-type]
    except (json.JSONDecodeError, TypeError):
        _reject_invalid()
        parsed = {}  # unreachable but keeps typing happy

    if parsed.get("type") != EMAIL_CHANGE_TYPE:
        _reject_invalid()
    if parsed.get("userId") != current.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verification code",
        )
    if parsed.get("newEmail") != body.newEmail:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match verification code",
        )
    if rec.expiresAt < _utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código expirado. Solicite um novo código.",
        )

    # Double check that the new email isn't in use by someone else now.
    clash = db.scalar(
        select(User).where(User.email == body.newEmail, User.id != current.id)
    )
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este email já está em uso"
        )

    user = _load_full_user(db, current.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.email = body.newEmail
    rec.isUsed = True
    rec.usedAt = _utcnow()
    db.commit()
    db.refresh(user)
    return {"message": "Email atualizado com sucesso", "user": serialize_user(user)}


# ---------------------------------------------------------------------------
# PUT /users/profile
# ---------------------------------------------------------------------------

@router.put("/profile", summary="Atualizar perfil completo (role, city, etc.)")
def update_profile(
    body: UpdateProfileBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, current.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
    if body.franchiseeOf:
        _validate_franchises_exist(db, body.franchiseeOf)

    role_changed = body.role is not None and body.role != user.role
    final_role = body.role or user.role

    if body.city is not None:
        user.profile.city = body.city
    if body.interestSectors is not None:
        user.profile.interestSectors = body.interestSectors
    if body.interestRegion is not None:
        user.profile.interestRegion = body.interestRegion
    if body.investmentRange is not None:
        user.profile.investmentRange = body.investmentRange

    if body.role is not None:
        user.role = body.role

    if final_role == "FRANCHISEE" and body.franchiseeOf is not None:
        franchises = db.scalars(
            select(Franchise).where(Franchise.id.in_(body.franchiseeOf))
        ).all()
        user.franchises_as_franchisee = list(franchises)
    elif final_role != "FRANCHISEE":
        user.franchises_as_franchisee = []

    db.commit()
    db.refresh(user)

    if role_changed:
        token = issue_token({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "isActive": user.isActive,
        })
        return {
            "message": "Profile updated successfully",
            "user": serialize_user(user),
            "access_token": token,
            "roleChanged": True,
        }
    return {"message": "Profile updated successfully", "roleChanged": False}


# ===========================================================================
# Admin endpoints — mounted under /admin (separate router)
#
#   POST /admin                         createAdmin
#   GET  /admin                         findAllUsers (admins listing)
#   GET  /admin/members                 paginated members
#   GET  /admin/franchisors             paginated franchisors
#   PUT  /admin/franchisors/:id         update a franchisor
#   GET  /admin/users/:id               get user by id
#   PUT  /admin/users/:id               update user basic info (admin)
#   PUT  /admin/users/:id/profile       update user profile (admin)
#
# All endpoints require role == ADMIN — enforced via `require_role("ADMIN")`.
# Paths mirror the NestJS controllers exactly so the frontend works unchanged.
# ===========================================================================


def _strong_password(v: str) -> str:
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one number")
    return v


class CreateAdminBody(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    phone: str
    cpf: str

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _strong_password(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not validate_phone_digits(v):
            raise ValueError("Phone must have 10 or 11 digits")
        return strip_non_digits(v)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str) -> str:
        digits = strip_non_digits(v)
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not validate_cpf(v):
            raise ValueError("Invalid CPF")
        return digits


class UpdateFranchisorBody(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    isActive: Optional[bool] = None
    ownedFranchises: Optional[list[str]] = None

    @field_validator("password")
    @classmethod
    def _password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _strong_password(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not validate_phone_digits(v):
            raise ValueError("Phone must have 10 or 11 digits")
        return strip_non_digits(v)

    @field_validator("ownedFranchises")
    @classmethod
    def _of_min(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None and len(v) < 1:
            raise ValueError("At least one franchise is required")
        return v


def _search_clause(search: Optional[str]) -> Optional[Any]:
    """Returns an ilike OR(name, email) clause, or None if search is empty."""
    if not search or not search.strip():
        return None
    pat = f"%{search.strip()}%"
    return or_(User.name.ilike(pat), User.email.ilike(pat))


# ---------------------------------------------------------------------------
# POST /admin  — create a new ADMIN user
# ---------------------------------------------------------------------------

@admin_router.post("", summary="Cria novo usuário ADMIN")
def create_admin(
    body: CreateAdminBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    if db.scalar(select(User).where(User.phone == body.phone)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Phone already exists")
    if db.scalar(select(User).where(User.cpf == body.cpf)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "CPF already exists")

    user = User(
        id=uuid.uuid4().hex,
        name=body.name,
        email=body.email,
        password=hash_password(body.password),
        phone=body.phone,
        cpf=body.cpf,
        role="ADMIN",
        isActive=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": serialize_user_admin_admin(user)}


# ---------------------------------------------------------------------------
# GET /admin  — paginated admins listing
# ---------------------------------------------------------------------------

@admin_router.get("", summary="Lista admins paginada")
def find_all_admins(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    page = max(page, 1)
    limit = max(limit, 1)
    skip = (page - 1) * limit

    where_role = User.role == "ADMIN"
    search_clause = _search_clause(search)
    where = and_(where_role, search_clause) if search_clause is not None else where_role

    items = db.scalars(
        select(User).where(where).offset(skip).limit(limit)
    ).all()
    total = db.scalar(select(func.count()).select_from(User).where(where)) or 0
    total_active = (
        db.scalar(
            select(func.count()).select_from(User).where(
                and_(User.role == "ADMIN", User.isActive.is_(True))
            )
        )
        or 0
    )
    total_inactive = (
        db.scalar(
            select(func.count()).select_from(User).where(
                and_(User.role == "ADMIN", User.isActive.is_(False))
            )
        )
        or 0
    )

    return {
        "data": [serialize_user_admin_admin(u) for u in items],
        "total": total,
        "totalActive": total_active,
        "totalInactive": total_inactive,
        "page": page,
        "lastPage": max(1, (total + limit - 1) // limit),
    }


# ---------------------------------------------------------------------------
# GET /admin/members
# ---------------------------------------------------------------------------

@admin_router.get("/members", summary="Lista membros paginada")
def get_members(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    page = max(page, 1)
    limit = max(limit, 1)
    skip = (page - 1) * limit

    where_role = User.role.in_(MEMBER_ROLES)
    search_clause = _search_clause(search)
    where = and_(where_role, search_clause) if search_clause is not None else where_role

    items = db.scalars(
        select(User)
        .where(where)
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(User.profile),
            selectinload(User.franchises_as_franchisee),
        )
    ).all()
    total = db.scalar(select(func.count()).select_from(User).where(where)) or 0
    total_active = (
        db.scalar(
            select(func.count()).select_from(User).where(
                and_(
                    User.role.in_(MEMBER_ROLES_FOR_COUNTERS),
                    User.isActive.is_(True),
                )
            )
        )
        or 0
    )
    total_inactive = (
        db.scalar(
            select(func.count()).select_from(User).where(
                and_(
                    User.role.in_(MEMBER_ROLES_FOR_COUNTERS),
                    User.isActive.is_(False),
                )
            )
        )
        or 0
    )

    return {
        "data": [serialize_user_admin_member(u) for u in items],
        "total": total,
        "totalActive": total_active,
        "totalInactive": total_inactive,
        "page": page,
        "lastPage": max(1, (total + limit - 1) // limit),
    }


# ---------------------------------------------------------------------------
# GET /admin/franchisors
# ---------------------------------------------------------------------------

@admin_router.get("/franchisors", summary="Lista franqueadores paginada")
def get_all_franchisors(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    page = max(page, 1)
    limit = max(limit, 1)
    skip = (page - 1) * limit

    where_role = User.role == "FRANCHISOR"
    search_clause = _search_clause(search)
    where = and_(where_role, search_clause) if search_clause is not None else where_role

    items = db.scalars(
        select(User)
        .where(where)
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(User.franchisor_request),
            selectinload(User.franchises_owned),
        )
    ).all()
    total = db.scalar(select(func.count()).select_from(User).where(where)) or 0
    total_active = (
        db.scalar(
            select(func.count()).select_from(User).where(
                and_(User.role == "FRANCHISOR", User.isActive.is_(True))
            )
        )
        or 0
    )
    total_inactive = (
        db.scalar(
            select(func.count()).select_from(User).where(
                and_(User.role == "FRANCHISOR", User.isActive.is_(False))
            )
        )
        or 0
    )

    return {
        "data": [serialize_user_admin_franchisor(u) for u in items],
        "total": total,
        "totalActive": total_active,
        "totalInactive": total_inactive,
        "page": page,
        "lastPage": max(1, (total + limit - 1) // limit),
    }


# ---------------------------------------------------------------------------
# PUT /admin/franchisors/:id  — update a FRANCHISOR user
# ---------------------------------------------------------------------------

@admin_router.put("/franchisors/{user_id}", summary="Atualiza franqueador")
def update_franchisor(
    user_id: str,
    body: UpdateFranchisorBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchisor = db.scalar(
        select(User).where(User.id == user_id, User.role == "FRANCHISOR")
    )
    if franchisor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Franchisor not found")

    if body.email is not None and body.email != franchisor.email:
        if db.scalar(
            select(User).where(User.email == body.email, User.id != user_id)
        ) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use by another user")
    if body.phone is not None and body.phone != franchisor.phone:
        if db.scalar(
            select(User).where(User.phone == body.phone, User.id != user_id)
        ) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone already in use by another user")

    if body.ownedFranchises is not None:
        franchises = db.scalars(
            select(Franchise)
            .where(Franchise.id.in_(body.ownedFranchises))
            .options(selectinload(Franchise.owner))
        ).all()
        found_ids = {f.id for f in franchises}
        missing = [fid for fid in body.ownedFranchises if fid not in found_ids]
        if missing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Franchises with IDs {', '.join(missing)} do not exist",
            )
        conflicts = [
            f for f in franchises if f.owner is not None and f.owner.id != user_id
        ]
        if conflicts:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {
                    "message": "One or more franchises are already owned by other franchisors",
                    "conflicts": [
                        f"Franchise \"{f.name}\" (ID: {f.id}) is already owned by "
                        f"{f.owner.name} ({f.owner.email})"
                        for f in conflicts
                    ],
                    "takenFranchises": [f.id for f in conflicts],
                },
            )

    if body.name is not None:
        franchisor.name = body.name
    if body.email is not None:
        franchisor.email = body.email
    if body.phone is not None:
        franchisor.phone = body.phone
    if body.password is not None:
        # NestJS's updateFranchisor stores the raw password string (bug). FastAPI hashes it.
        franchisor.password = hash_password(body.password)
    if body.isActive is not None:
        franchisor.isActive = body.isActive

    if body.ownedFranchises is not None:
        # NOTE: matches NestJS behavior — only sets ownerId on the new list,
        # does NOT unlink previously owned franchises that aren't in the new list.
        for f in franchises:
            f.ownerId = user_id

    db.commit()
    return {"message": "Franchisor updated successfully"}


# ---------------------------------------------------------------------------
# GET /admin/users/:id  — fetch any user by id (returns null if not found,
# matching NestJS behavior)
# ---------------------------------------------------------------------------

@admin_router.get("/users/{user_id}", summary="Get user by id (admin)")
def find_user_by_id(
    user_id: str,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> Optional[dict[str, Any]]:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        return None
    return serialize_user_admin_admin(user)


# ---------------------------------------------------------------------------
# PUT /admin/users/:id  — update basic info as admin
# ---------------------------------------------------------------------------

@admin_router.put("/users/{user_id}", summary="Atualiza dados básicos (admin)")
def admin_update_user_basic_info(
    user_id: str,
    body: UpdateBasicInfoBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if body.phone is not None and body.phone != user.phone:
        if db.scalar(
            select(User).where(User.phone == body.phone, User.id != user.id)
        ) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone already in use")
    if body.cpf is not None and body.cpf != user.cpf:
        if db.scalar(
            select(User).where(User.cpf == body.cpf, User.id != user.id)
        ) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "CPF already in use")

    if body.name is not None:
        user.name = body.name
    if body.phone is not None:
        user.phone = body.phone
    if body.cpf is not None:
        user.cpf = body.cpf
    if body.isActive is not None:
        user.isActive = body.isActive

    db.commit()
    db.refresh(user)
    return {"user": serialize_user(user)}


# ---------------------------------------------------------------------------
# PUT /admin/users/:id/profile  — update profile (city, role, franchiseeOf)
# ---------------------------------------------------------------------------

@admin_router.put("/users/{user_id}/profile", summary="Atualiza perfil (admin)")
def admin_update_user_profile(
    user_id: str,
    body: UpdateProfileBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _load_full_user(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User profile not found")
    if body.franchiseeOf:
        _validate_franchises_exist(db, body.franchiseeOf)

    role_changed = body.role is not None and body.role != user.role
    final_role = body.role or user.role

    if body.city is not None:
        user.profile.city = body.city
    if body.interestSectors is not None:
        user.profile.interestSectors = body.interestSectors
    if body.interestRegion is not None:
        user.profile.interestRegion = body.interestRegion
    if body.investmentRange is not None:
        user.profile.investmentRange = body.investmentRange

    if body.role is not None:
        user.role = body.role

    if final_role == "FRANCHISEE" and body.franchiseeOf is not None:
        franchises = db.scalars(
            select(Franchise).where(Franchise.id.in_(body.franchiseeOf))
        ).all()
        user.franchises_as_franchisee = list(franchises)
    elif final_role != "FRANCHISEE":
        user.franchises_as_franchisee = []

    db.commit()
    db.refresh(user)

    if role_changed:
        # Mirrors NestJS — emits a token reflecting the target user's new role.
        # The admin's own token is unchanged; the frontend's useAdminUpdateProfile
        # ignores access_token, so this is informational only.
        token = issue_token({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "isActive": user.isActive,
        })
        return {
            "roleChanged": True,
            "updatedUser": serialize_user(user),
            "access_token": token,
        }
    return {"roleChanged": False}


# ---------------------------------------------------------------------------
# PATCH /admin/users/{user_id}/profile-type  (Sprint 3 Fase 2)
# Muda profileType do user + grava AdminActionLog pra audit trail.
# ---------------------------------------------------------------------------


class UpdateProfileTypeBody(BaseModel):
    profileType: ProfileType
    reason: Optional[str] = Field(default=None, max_length=500)


@admin_router.patch(
    "/users/{user_id}/profile-type",
    summary="Atualiza profileType do user (admin only, audit-logged)",
)
def update_user_profile_type(
    user_id: str,
    body: UpdateProfileTypeBody,
    db: Session = Depends(get_db),
    admin: JwtPayload = Depends(require_role("ADMIN")),
) -> dict[str, Any]:
    target = db.scalar(select(User).where(User.id == user_id))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    previous = target.profileType
    if previous == body.profileType:
        return {
            "user": serialize_user(target),
            "changed": False,
            "previous": previous.value if previous else None,
        }

    target.profileType = body.profileType

    log = AdminActionLog(
        id=uuid.uuid4().hex,
        adminId=admin.id,
        action="UPDATE_PROFILE_TYPE",
        targetUserId=user_id,
        metadata_={
            "from": previous.value if previous else None,
            "to": body.profileType.value,
            "reason": body.reason,
        },
    )
    db.add(log)
    db.commit()
    db.refresh(target)

    return {
        "user": serialize_user(target),
        "changed": True,
        "previous": previous.value if previous else None,
    }
