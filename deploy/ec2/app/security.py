"""
Security helpers — JWT (HS256) + bcrypt password hashing.

Mirrors the NestJS backend:
  - JWT algorithm:     HS256
  - JWT secret:        env JWT_SECRET
  - JWT expiration:    env JWT_EXPIRES_IN (default "1h"); accepts "1h"/"7d"/"15m"/"60s"/int seconds
  - Payload:           {id, email, name, role, isActive}
  - Bcrypt cost:       10 (both for new hashes and verifying existing ones;
                         verifying works for any cost — cost is embedded in the hash string).
"""
from __future__ import annotations

import logging
import os
import re
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

# pyjwt raises InsecureKeyLengthWarning for HMAC keys < 32 bytes. The current
# secret is 32 bytes (hex-encoded as 64 chars), so this is a defensive filter
# in case a shorter secret is configured via env in the future.
try:
    from jwt.warnings import InsecureKeyLengthWarning  # type: ignore
    warnings.simplefilter("ignore", InsecureKeyLengthWarning)
except Exception:
    pass

from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger("mf-api.security")

JWT_SECRET = os.environ.get("JWT_SECRET", "your-fallback-secret")
JWT_EXPIRES_IN_RAW = os.environ.get("JWT_EXPIRES_IN", "1h")
JWT_ALGORITHM = "HS256"
BCRYPT_ROUNDS = 10


# ---------------------------------------------------------------------------
# JWT duration parsing — matches the `ms` package semantics used by NestJS.
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^\s*(\d+)\s*(ms|s|m|h|d|w|y)?\s*$", re.IGNORECASE)

_UNIT_SECONDS = {
    None: 1,
    "ms": 1 / 1000,
    "s":  1,
    "m":  60,
    "h":  60 * 60,
    "d":  60 * 60 * 24,
    "w":  60 * 60 * 24 * 7,
    "y":  60 * 60 * 24 * 365,
}


def parse_duration_seconds(raw: str | int) -> int:
    """'1h' -> 3600; '24h' -> 86400; '7d' -> 604800; 900 -> 900."""
    if isinstance(raw, int):
        return raw
    m = _DURATION_RE.match(str(raw))
    if not m:
        raise ValueError(f"Unparseable duration: {raw!r}")
    value = int(m.group(1))
    unit = (m.group(2) or "").lower() or None
    seconds = value * _UNIT_SECONDS[unit]
    return int(seconds)


JWT_EXPIRES_SECONDS = parse_duration_seconds(JWT_EXPIRES_IN_RAW)


# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verification; works with any cost embedded in hash."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in DB — treat as mismatch.
        return False


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


# ---------------------------------------------------------------------------
# JWT issue / verify
# ---------------------------------------------------------------------------

@dataclass
class JwtPayload:
    id: str
    email: str
    name: str
    role: str
    isActive: bool
    iat: Optional[int] = None
    exp: Optional[int] = None

    def to_public_dict(self) -> dict[str, Any]:
        """Shape returned to the client — excludes iat/exp for the `/auth/validate`
        response `payload` field so it mirrors the NestJS JwtPayload interface."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "isActive": self.isActive,
        }


def issue_token(user: dict[str, Any], *, expires_seconds: Optional[int] = None) -> str:
    """
    Sign a JWT for the given user dict. `user` must contain the NestJS-compatible
    fields; any extras are ignored. `exp` is set to now + expires_seconds.
    """
    ttl = expires_seconds if expires_seconds is not None else JWT_EXPIRES_SECONDS
    now = datetime.now(timezone.utc)
    payload = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "isActive": bool(user.get("isActive", True)),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[JwtPayload]:
    """Decode and verify the token signature + expiration. Returns None on failure."""
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    try:
        return JwtPayload(
            id=decoded["id"],
            email=decoded["email"],
            name=decoded["name"],
            role=decoded["role"],
            isActive=bool(decoded.get("isActive", True)),
            iat=decoded.get("iat"),
            exp=decoded.get("exp"),
        )
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# FastAPI dependency — use as `user: JwtPayload = Depends(get_current_user)`
# for any route that requires authentication.
# ---------------------------------------------------------------------------

def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_current_user(authorization: Optional[str] = Header(None)) -> JwtPayload:
    """Extract + verify a Bearer token from the Authorization header.

    Raises 401 on missing, malformed, or expired tokens.
    """
    token = _extract_bearer(authorization)
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
    if payload.isActive is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    return payload


# Optional variant used by endpoints that want to peek at auth without failing
# when it's missing — useful for public endpoints with logged-in enrichment.
def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[JwtPayload]:
    token = _extract_bearer(authorization)
    if not token:
        return None
    payload = verify_token(token)
    if payload is None or payload.isActive is False:
        return None
    return payload


# ---------------------------------------------------------------------------
# Role-based access — dependency factories. Use as:
#
#   @router.get("/admin/things")
#   def list_things(user: JwtPayload = Depends(require_role("ADMIN"))): ...
#
#   @router.post("/business-models")
#   def create_bm(user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR"))):
#       ...
# ---------------------------------------------------------------------------

def require_role(required_role: str):
    """401 if no/expired token, 403 if role does not match."""
    def _check(user: JwtPayload = Depends(get_current_user)) -> JwtPayload:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires {required_role}",
            )
        return user
    return _check


def require_any_role(*allowed_roles: str):
    """401 if no/expired token, 403 if role not in allowed_roles."""
    allowed = tuple(allowed_roles)
    def _check(user: JwtPayload = Depends(get_current_user)) -> JwtPayload:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires one of {', '.join(allowed)}",
            )
        return user
    return _check


def require_franchisor_profile(
    user: JwtPayload = Depends(get_current_user),
) -> JwtPayload:
    """Gate pra rotas /franqueador/* — permite ADMIN (bypass) ou user com profileType=FRANCHISOR.

    Checagem real é via DB (source of truth) porque o JWT atual não carrega
    profileType. Custo: 1 query extra por request protegido.

    Aceita qualquer role desde que profileType=FRANCHISOR (MEMBER aguardando
    aprovação e FRANCHISOR já aprovado ambos passam).
    """
    if user.role == "ADMIN":
        return user

    # Lazy imports pra evitar ciclo de import no startup
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import ProfileType, User

    db = SessionLocal()
    try:
        target = db.scalar(select(User.profileType).where(User.id == user.id))
    finally:
        db.close()

    if target != ProfileType.FRANCHISOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a usuários com perfil de franqueador.",
        )
    return user


# ---------------------------------------------------------------------------
# Ownership checks — for resources scoped to a Franchise.
# ---------------------------------------------------------------------------

def assert_franchise_owner(user: JwtPayload, owner_id: Optional[str]) -> None:
    """Raises 403 unless the user is ADMIN, or is FRANCHISOR matching `owner_id`.

    Designed to be called AFTER a `require_any_role("ADMIN", "FRANCHISOR")`
    dependency has already gated the endpoint — assumes the caller has one of
    those two roles. Use:

        franchise = db.scalar(...)
        assert_franchise_owner(user, franchise.ownerId)
    """
    if user.role == "ADMIN":
        return
    if user.role == "FRANCHISOR" and owner_id is not None and owner_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Você não tem permissão para esta operação",
    )
