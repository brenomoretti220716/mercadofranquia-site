"""
Franchisor request endpoints — the user applies to become a FRANCHISOR
role by submitting CNPJ, responsible person info, and two document files.

    POST /users/franchisor-request            multipart/form-data; creates a PENDING request
    GET  /users/franchisor-request/my-request returns the caller's own request (or null)

Admin approval/rejection endpoints are a separate router (step 4).

Files are saved under  {UPLOAD_DIR}/franchisor-requests/<userId>/  and the
relative path is stored in the DB.
"""
from __future__ import annotations

import os
import re
import uuid
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
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import FranchisorRequest, User
from app.security import JwtPayload, get_current_user
from app.user_serializers import serialize_franchisor_request
from app.validators import strip_non_digits, validate_cnpj, validate_phone_digits

router = APIRouter(prefix="/users/franchisor-request", tags=["franchisor-requests"])

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
