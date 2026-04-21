"""
Registration endpoints — mirror of the NestJS `/users/register/*` routes.

    POST /users/register/step-one   public    create account (name, email, password, phone)
    POST /users/register/step-two   JWT auth  complete profile (role + 4 profile fields + franchiseeOf)
"""
from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Franchise, User, UserProfile
from app.security import (
    JwtPayload,
    get_current_user,
    hash_password,
    issue_token,
)
from app.user_serializers import serialize_user
from app.validators import strip_non_digits, validate_phone_digits

from fastapi import BackgroundTasks
from app.db import SessionLocal
from app.services import hubspot_client
from app.services.ses_mailer import send_welcome_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/register", tags=["register"])

ROLE_LITERAL = Literal["FRANCHISEE", "CANDIDATE", "ENTHUSIAST", "FRANCHISOR"]


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class StepOneBody(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    phone: str

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("phone")
    @classmethod
    def _phone_digits(cls, v: str) -> str:
        if not validate_phone_digits(v):
            raise ValueError("Phone must have 10 or 11 digits")
        return strip_non_digits(v)


class StepTwoBody(BaseModel):
    role: ROLE_LITERAL
    city: str = Field(min_length=1)
    interestSectors: str = Field(min_length=1)
    interestRegion: str = Field(min_length=1)
    investmentRange: str = Field(min_length=1)
    franchiseeOf: Optional[list[str]] = None

    @field_validator("franchiseeOf")
    @classmethod
    def _validate_franchisees(
        cls, v: Optional[list[str]], info
    ) -> Optional[list[str]]:
        role = info.data.get("role")
        if role == "FRANCHISEE":
            if not v or len(v) == 0:
                raise ValueError(
                    "FRANCHISEE role requires at least one franchise to be linked"
                )
        return v


# ---------------------------------------------------------------------------
# POST /users/register/step-one
# ---------------------------------------------------------------------------

def _sync_hubspot_for_new_investor(
    *, user_id: str, email: str, name: str, phone: str
) -> None:
    """
    Background task: cria Contact no HubSpot e persiste hubspotContactId no User.

    Falhas aqui nunca propagam pro usuário — o cadastro já foi feito.
    Se HubSpot estiver fora, user continua sem hubspotContactId (pode ser
    sincronizado depois).
    """
    import asyncio

    try:
        contact_id = asyncio.run(
            hubspot_client.create_investor_contact(
                email=email,
                name=name,
                phone=phone,
                user_id=user_id,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Falha ao criar contact HubSpot pro user %s: %s", user_id, exc
        )
        return

    if not contact_id:
        logger.warning(
            "HubSpot retornou contact_id vazio pro user %s — não persistindo",
            user_id,
        )
        return

    # Persistir hubspotContactId no banco. Abre nova sessão porque a original
    # já fechou (endpoint retornou antes dessa task rodar).
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            logger.error(
                "User %s sumiu do banco entre o cadastro e a sync HubSpot", user_id
            )
            return
        user.hubspotContactId = contact_id
        db.commit()
        logger.info(
            "hubspotContactId %s salvo pro user %s", contact_id, user_id
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Erro persistindo hubspotContactId pro user %s: %s", user_id, exc
        )
        db.rollback()
    finally:
        db.close()


@router.post("/step-one", summary="Registro passo 1 (cria conta)")
def step_one(
    body: StepOneBody,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Conflict checks match NestJS usersService.stepOneRegister.
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    if db.scalar(select(User).where(User.phone == body.phone)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone already exists",
        )

    # Prisma generates cuid ids; Postgres + our models expect VARCHAR(191). A
    # UUID4 hex string is acceptable — it's unique and < 191 chars.
    user_id = uuid.uuid4().hex
    new_user = User(
        id=user_id,
        name=body.name,
        email=body.email,
        password=hash_password(body.password),
        phone=body.phone,
        role="MEMBER",
        isActive=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Background tasks (não bloqueiam a resposta): enviar welcome email + sync HubSpot
    background_tasks.add_task(
        send_welcome_email,
        to=new_user.email,
        user_name=new_user.name,
    )
    background_tasks.add_task(
        _sync_hubspot_for_new_investor,
        user_id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        phone=new_user.phone,
    )

    token = issue_token({
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "role": new_user.role,
        "isActive": new_user.isActive,
    })

    return {
        "user": serialize_user(
            new_user,
            include_profile=False,
            include_franchisor_profile=False,
            include_franchisees=False,
        ),
        "access_token": token,
    }


# ---------------------------------------------------------------------------
# POST /users/register/step-two
# ---------------------------------------------------------------------------

def _validate_franchises_exist(db: Session, ids: list[str]) -> None:
    if not ids:
        return
    existing = db.scalars(select(Franchise.id).where(Franchise.id.in_(ids))).all()
    found = set(existing)
    missing = [fid for fid in ids if fid not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Franchises with IDs {', '.join(missing)} do not exist",
        )


@router.post("/step-two", summary="Registro passo 2 (completa perfil)")
def step_two(
    body: StepTwoBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.scalar(
        select(User)
        .where(User.id == current.id)
        .options(
            selectinload(User.profile),
            selectinload(User.franchisor_profile),
            selectinload(User.franchises_as_franchisee),
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.profile is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User profile already exists",
        )

    if body.franchiseeOf:
        _validate_franchises_exist(db, body.franchiseeOf)

    # Create profile + update role + link franchises in one transaction.
    profile = UserProfile(
        id=uuid.uuid4().hex,
        userId=user.id,
        city=body.city,
        interestSectors=body.interestSectors,
        interestRegion=body.interestRegion,
        investmentRange=body.investmentRange,
    )
    db.add(profile)
    user.role = body.role

    if body.role == "FRANCHISEE" and body.franchiseeOf:
        franchises = db.scalars(
            select(Franchise).where(Franchise.id.in_(body.franchiseeOf))
        ).all()
        user.franchises_as_franchisee = list(franchises)

    db.commit()
    db.refresh(user)

    token = issue_token({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "isActive": user.isActive,
    })

    return {
        "message": "Profile completed successfully",
        "user": serialize_user(user),
        "access_token": token,
    }
