"""
Auth endpoints — mirror of the NestJS `AuthController` in the old backend.

Routes (prefix `/auth`, externally `/api/auth` after nginx):
    POST /login              credentials  -> { user, access_token }
    POST /validate           Authorization header -> { valid, payload, message }
    POST /forgot-password    email  -> { message, expiresAt }
    POST /verify-reset-code  email+code -> { message }
    POST /reset-password     email+code+password -> { message, user, access_token }
    POST /resend-reset-code  email -> { message, expiresAt }

Password reset codes live in the `UserVerification` table with
`userData = '{"type":"password_reset"}'`. Email delivery is stubbed to a
logger call until SMTP is plugged in — see `_dispatch_reset_email`.
"""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserVerification
from app.security import (
    JwtPayload,
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("mf-api.auth")

RESET_CODE_TTL_MINUTES = 15
RESET_PAYLOAD_TYPE = "password_reset"


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class VerifyResetCodeBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=6)


class ResetPasswordBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=6)
    password: str = Field(min_length=6)
    confirmPassword: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_code() -> str:
    """6-digit numeric code, matching NestJS.generateVerificationCode()."""
    return f"{random.randint(100000, 999999)}"


def _expires_at(minutes: int = RESET_CODE_TTL_MINUTES) -> datetime:
    # Stored as naive UTC in MySQL/Prisma — keep naive here too so comparisons
    # with DB datetime columns don't hit tz-aware mismatch.
    return datetime.utcnow() + timedelta(minutes=minutes)


def _minutes_until(when: datetime) -> int:
    delta = (when - datetime.utcnow()).total_seconds()
    mins = int(delta // 60)
    return mins if mins > 0 else 1


def _user_public_dict(u: User) -> dict[str, Any]:
    """What the frontend expects in the `user` field of login/reset responses."""
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
    }


def _user_full_dict(u: User) -> dict[str, Any]:
    """Used internally for JWT generation — includes `isActive`."""
    return {**_user_public_dict(u), "isActive": bool(u.isActive)}


def _dispatch_reset_email(*, to: str, code: str, expires_at: datetime, user_name: str) -> None:
    """
    Stub: log the code instead of sending an email. Replace with SMTP/SES
    delivery when the mail provider is wired up.
    """
    logger.warning(
        "[RESET CODE] to=%s name=%s code=%s expires_at=%s (email not actually sent — stub)",
        to, user_name, code, expires_at.isoformat(),
    )


def _find_active_reset_verification(db: Session, email: str) -> Optional[UserVerification]:
    """
    Returns the most recent *unused and not expired* password-reset verification
    record for the given email.
    """
    now = datetime.utcnow()
    stmt = (
        select(UserVerification)
        .where(
            UserVerification.email == email,
            UserVerification.isUsed.is_(False),
            UserVerification.expiresAt > now,
        )
        .order_by(UserVerification.createdAt.desc())
    )
    for rec in db.scalars(stmt).all():
        if _is_reset_record(rec):
            return rec
    return None


def _is_reset_record(v: UserVerification) -> bool:
    """Checks `userData` JSON has type == password_reset."""
    if not v.userData:
        return False
    try:
        parsed = json.loads(v.userData)
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(parsed, dict) and parsed.get("type") == RESET_PAYLOAD_TYPE


def _find_latest_reset_verification(db: Session, email: str) -> Optional[UserVerification]:
    """Most recent unused reset record regardless of expiry (for resend logic)."""
    stmt = (
        select(UserVerification)
        .where(
            UserVerification.email == email,
            UserVerification.isUsed.is_(False),
        )
        .order_by(UserVerification.createdAt.desc())
    )
    for rec in db.scalars(stmt).all():
        if _is_reset_record(rec):
            return rec
    return None


def _find_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", summary="Autenticação de usuário")
def login(body: LoginBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Returns 404 for any credential failure (matches NestJS privacy policy:
    frontend interprets 404 as "invalid credentials").
    """
    user = _find_user_by_email(db, body.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid credentials")
    if not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid credentials")

    token = issue_token(_user_full_dict(user))
    return {
        "user": _user_public_dict(user),
        "access_token": token,
    }


@router.post("/validate", summary="Validação de token JWT")
def validate_token(
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    """
    Reads `Authorization: Bearer <token>`, returns the decoded payload.
    404 / 401 semantics match the NestJS handler.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {
        "valid": True,
        "payload": payload.to_public_dict(),
        "message": "Token is valid",
    }


@router.post("/forgot-password", summary="Solicitar código de reset de senha")
def forgot_password(body: ForgotPasswordBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = _find_user_by_email(db, body.email)

    if user is None:
        # Privacy policy: NestJS throws 404 here; frontend treats as success.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Se este e-mail estiver cadastrado, você receberá um código de verificação.",
        )

    existing = _find_active_reset_verification(db, body.email)
    if existing is not None:
        mins = _minutes_until(existing.expiresAt)
        # NestJS returns 400 with a structured body; FastAPI does the same via
        # HTTPException detail as a dict — frontend already parses errorData.expiresIn.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "expiresIn": mins,
                "message": f"Um código já foi enviado. Aguarde {mins} minuto(s) antes de solicitar um novo código.",
            },
        )

    code = _generate_code()
    expires_at = _expires_at()

    db.add(UserVerification(
        email=body.email,
        code=code,
        expiresAt=expires_at,
        isUsed=False,
        userData=json.dumps({"type": RESET_PAYLOAD_TYPE}),
    ))
    db.commit()

    _dispatch_reset_email(to=body.email, code=code, expires_at=expires_at, user_name=user.name)

    return {
        "message": "Código de verificação enviado para seu email",
        "expiresAt": expires_at.isoformat(),
    }


@router.post("/verify-reset-code", summary="Verificar código de reset")
def verify_reset_code(body: VerifyResetCodeBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    rec = db.scalar(
        select(UserVerification).where(
            UserVerification.email == body.email,
            UserVerification.code == body.code,
            UserVerification.isUsed.is_(False),
        )
    )
    if rec is None or not _is_reset_record(rec):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou já utilizado",
        )
    if rec.expiresAt < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código expirado. Solicite um novo código.",
        )
    return {"message": "Código verificado com sucesso"}


@router.post("/reset-password", summary="Redefinir senha com código")
def reset_password(body: ResetPasswordBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    if body.password != body.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas não coincidem.",
        )

    rec = db.scalar(
        select(UserVerification).where(
            UserVerification.email == body.email,
            UserVerification.code == body.code,
            UserVerification.isUsed.is_(False),
        )
    )
    if rec is None or not _is_reset_record(rec):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou já utilizado",
        )
    if rec.expiresAt < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código expirado. Solicite um novo código.",
        )

    user = _find_user_by_email(db, body.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    user.password = hash_password(body.password)
    rec.isUsed = True
    rec.usedAt = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = issue_token(_user_full_dict(user))
    return {
        "message": "Senha redefinida com sucesso",
        "user": _user_public_dict(user),
        "access_token": token,
    }


@router.post("/resend-reset-code", summary="Reenviar código de reset")
def resend_reset_code(body: ForgotPasswordBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    rec = _find_latest_reset_verification(db, body.email)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma solicitação de reset encontrada",
        )

    # If the existing code is still valid, refuse the resend (rate-limit window).
    if rec.expiresAt > datetime.utcnow():
        mins = _minutes_until(rec.expiresAt)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "expiresIn": mins,
                "message": f"Aguarde {mins} minuto(s) antes de solicitar um novo código.",
            },
        )

    user = _find_user_by_email(db, body.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    new_code = _generate_code()
    new_expires = _expires_at()
    rec.code = new_code
    rec.expiresAt = new_expires
    db.commit()

    _dispatch_reset_email(to=body.email, code=new_code, expires_at=new_expires, user_name=user.name)

    return {
        "message": "Código reenviado com sucesso",
        "expiresAt": new_expires.isoformat(),
    }
