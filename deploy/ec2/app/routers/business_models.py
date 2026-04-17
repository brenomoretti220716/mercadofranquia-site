"""
Business models — public read + admin/franchisor CRUD.

Public:
    GET /business-models/franchise/{slug}  list business models of a franchise
    GET /business-models/{id}              single business model

Admin/Franchisor (require_any_role("ADMIN","FRANCHISOR") + ownership):
    POST   /business-models       multipart create (photo required)
    PUT    /business-models/{id}  multipart update (photo optional)
    DELETE /business-models/{id}  delete (also drops the photo from disk)

Authorization model: ADMIN bypasses ownership; FRANCHISOR must be the
`ownerId` of the franchise the business model belongs to.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
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
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import BusinessModel, Franchise
from app.security import (
    JwtPayload,
    assert_franchise_owner,
    require_any_role,
)
from app.storage import delete_uploaded_file, save_image_upload

router = APIRouter(prefix="/business-models", tags=["business-models"])
logger = logging.getLogger("mf-api.business-models")

_BM_UPLOAD_SUBDIR = "franchises/business-models"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _serialize(bm: BusinessModel) -> dict[str, Any]:
    return {
        "id": bm.id,
        "name": bm.name,
        "description": bm.description,
        "photoUrl": bm.photoUrl,
        "franchiseId": bm.franchiseId,
        "createdAt": _iso(bm.createdAt),
        "updatedAt": _iso(bm.updatedAt),
    }


def _resolve_franchise(db: Session, slug_or_id: str) -> Franchise:
    f = db.scalar(select(Franchise).where(Franchise.slug == slug_or_id))
    if f is None:
        f = db.scalar(select(Franchise).where(Franchise.id == slug_or_id))
    if f is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franchise not found"
        )
    return f


@router.get("/franchise/{slug}", summary="Modelos de negócio de uma franquia")
def list_by_franchise(slug: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    franchise = _resolve_franchise(db, slug)
    rows = db.scalars(
        select(BusinessModel)
        .where(BusinessModel.franchiseId == franchise.id)
        .order_by(BusinessModel.createdAt.desc())
    ).all()
    return [_serialize(bm) for bm in rows]


@router.get("/{bm_id}", summary="Modelo de negócio por id")
def get_one(bm_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    bm = db.scalar(select(BusinessModel).where(BusinessModel.id == bm_id))
    if bm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Business model not found"
        )
    return _serialize(bm)


# ===========================================================================
# Admin/Franchisor CRUD endpoints
# ===========================================================================


def _load_bm_with_franchise(db: Session, bm_id: str) -> BusinessModel:
    bm = db.scalar(
        select(BusinessModel)
        .where(BusinessModel.id == bm_id)
        .options(selectinload(BusinessModel.franchise))
    )
    if bm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo de negócio não encontrado",
        )
    return bm


# ---------------------------------------------------------------------------
# POST /business-models  — multipart create, photo required
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="Cria business model (admin/franchisor) — multipart com foto",
    status_code=status.HTTP_201_CREATED,
)
def create_business_model(
    franchiseId: str = Form(..., min_length=1),
    name: str = Form(..., min_length=1, max_length=100),
    description: str = Form(..., min_length=10, max_length=2000),
    photo: UploadFile = File(..., description="Imagem (JPEG/PNG/GIF/WebP, ≤5MB)"),
    user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = db.scalar(
        select(Franchise).where(Franchise.id == franchiseId)
    )
    if franchise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franquia não encontrada"
        )
    assert_franchise_owner(user, franchise.ownerId)

    photo_url = save_image_upload(photo, _BM_UPLOAD_SUBDIR)

    bm = BusinessModel(
        id=uuid.uuid4().hex,
        name=name,
        description=description,
        photoUrl=photo_url,
        franchiseId=franchiseId,
    )
    try:
        db.add(bm)
        db.commit()
        db.refresh(bm)
    except Exception:
        delete_uploaded_file(photo_url)
        raise

    return _serialize(bm)


# ---------------------------------------------------------------------------
# PUT /business-models/{id}  — multipart update, photo optional
# ---------------------------------------------------------------------------

@router.put(
    "/{bm_id}",
    summary="Atualiza business model (admin/franchisor) — multipart, foto opcional",
)
def update_business_model(
    bm_id: str,
    name: Optional[str] = Form(None, min_length=1, max_length=100),
    description: Optional[str] = Form(None, min_length=10, max_length=2000),
    photo: Optional[UploadFile] = File(None),
    user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    bm = _load_bm_with_franchise(db, bm_id)
    franchise = bm.franchise
    owner_id = franchise.ownerId if franchise is not None else None
    assert_franchise_owner(user, owner_id)

    # FastAPI hands an empty UploadFile (filename="") when the multipart field
    # is present without a file body — treat that as "no photo".
    photo_provided = photo is not None and bool(photo.filename)

    new_photo_url: Optional[str] = None
    if photo_provided:
        new_photo_url = save_image_upload(photo, _BM_UPLOAD_SUBDIR)

    old_photo_url = bm.photoUrl

    if name is not None:
        bm.name = name
    if description is not None:
        bm.description = description
    if new_photo_url is not None:
        bm.photoUrl = new_photo_url

    try:
        db.commit()
        db.refresh(bm)
    except Exception:
        if new_photo_url:
            delete_uploaded_file(new_photo_url)
        raise

    # Drop the previous photo only after a successful DB write — safer than
    # NestJS which deletes before the update (potential dangling state if
    # the DB write fails after).
    if new_photo_url and old_photo_url and old_photo_url != new_photo_url:
        delete_uploaded_file(old_photo_url)

    return _serialize(bm)


# ---------------------------------------------------------------------------
# DELETE /business-models/{id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{bm_id}",
    summary="Apaga business model (admin/franchisor)",
)
def delete_business_model(
    bm_id: str,
    user: JwtPayload = Depends(require_any_role("ADMIN", "FRANCHISOR")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    bm = _load_bm_with_franchise(db, bm_id)
    franchise = bm.franchise
    owner_id = franchise.ownerId if franchise is not None else None
    assert_franchise_owner(user, owner_id)

    photo_url = bm.photoUrl
    db.delete(bm)
    db.commit()

    # Best-effort photo cleanup after the row is gone.
    delete_uploaded_file(photo_url)

    return {"message": "Modelo de negócio excluído com sucesso"}
