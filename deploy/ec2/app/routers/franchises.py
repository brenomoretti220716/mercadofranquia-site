"""
Franchises endpoints. URL prefix is `/franchises` — nginx adds the `/api/`
prefix externally (see `deploy/ec2/mercadofranquia.nginx`).

Response shapes are kept compatible with what the Next.js client consumes in
`web/src/services/franchises.ts`:

  GET /franchises           -> { data: Franchise[], total, page, lastPage }
  GET /franchises/count     -> { total: number }
  GET /franchises/{slug}    -> { data: Franchise }
"""
from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import Any, Literal, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionLocal, get_db
from app.models import ContactInfo, Franchise, Review, User
from app.security import JwtPayload, get_optional_user, require_role
from app.serializers import serialize_franchise
from app.services import hubspot_client
from app.services.ses_mailer import (
    send_additional_franchise_approved,
    send_additional_franchise_received,
    send_additional_franchise_rejected,
)
from app.utils.slug import generate_unique_slug

router = APIRouter(prefix="/franchises", tags=["franchises"])
franchisor_router = APIRouter(
    prefix="/franchisor/franchises",
    tags=["franchisor-franchises"],
)
logger = logging.getLogger("mf-api.franchises")

# Mirrors the Prisma SponsorPlacement enum.
SponsorPlacementValue = Literal["HOME_DESTAQUES", "RANKING_CATEGORIA", "QUIZ"]
MAX_SPONSORED_FRANCHISES = 5


SORT_COLUMNS = {
    "name":          Franchise.name,
    "rating":        Franchise.averageRating,
    "units":         Franchise.totalUnits,
    "investment":    Franchise.minimumInvestment,
    "roi":           Franchise.minimumReturnOnInvestment,
    "franchiseFee":  Franchise.franchiseFee,
    "revenue":       Franchise.averageMonthlyRevenue,
}


def _apply_filters(stmt, *, only_active: bool, filters: dict):
    if only_active:
        stmt = stmt.where(Franchise.isActive.is_(True))
        # Defesa em profundidade: além de isActive, filtra explicitamente por status.
        # Previne que franquias PENDING/REJECTED vazem pro público mesmo se alguém
        # setar isActive=true manualmente sem passar pelo fluxo de aprovação.
        stmt = stmt.where(Franchise.status == "APPROVED")

    search = filters.get("search")
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))

    segment = filters.get("segment")
    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))

    subsegment = filters.get("subsegment")
    if subsegment:
        stmt = stmt.where(Franchise.subsegment.ilike(f"%{subsegment}%"))

    exclude_subsegment = filters.get("excludeSubsegment")
    if exclude_subsegment:
        stmt = stmt.where(
            or_(
                Franchise.subsegment.is_(None),
                ~Franchise.subsegment.ilike(f"%{exclude_subsegment}%"),
            )
        )

    if (v := filters.get("minInvestment")) is not None:
        stmt = stmt.where(Franchise.minimumInvestment >= v)
    if (v := filters.get("maxInvestment")) is not None:
        stmt = stmt.where(Franchise.maximumInvestment <= v)
    if (v := filters.get("minUnits")) is not None:
        stmt = stmt.where(Franchise.totalUnits >= v)
    if (v := filters.get("maxUnits")) is not None:
        stmt = stmt.where(Franchise.totalUnits <= v)
    if (v := filters.get("minROI")) is not None:
        stmt = stmt.where(Franchise.minimumReturnOnInvestment >= v)
    if (v := filters.get("maxROI")) is not None:
        stmt = stmt.where(Franchise.maximumReturnOnInvestment <= v)
    if (v := filters.get("minFranchiseFee")) is not None:
        stmt = stmt.where(Franchise.franchiseFee >= v)
    if (v := filters.get("maxFranchiseFee")) is not None:
        stmt = stmt.where(Franchise.franchiseFee <= v)
    if (v := filters.get("minRevenue")) is not None:
        stmt = stmt.where(Franchise.averageMonthlyRevenue >= v)
    if (v := filters.get("maxRevenue")) is not None:
        stmt = stmt.where(Franchise.averageMonthlyRevenue <= v)
    if (v := filters.get("minRating")) is not None:
        stmt = stmt.where(Franchise.averageRating >= v)
    if (v := filters.get("maxRating")) is not None:
        stmt = stmt.where(Franchise.averageRating <= v)
    if (v := filters.get("isSponsored")) is not None:
        stmt = stmt.where(Franchise.isSponsored == v)
    return stmt


def _apply_sorts(stmt, sort_params: dict[str, Optional[str]]):
    """Apply user-requested sorts, falling back to units DESC, name ASC."""
    orders = []
    for key, direction in sort_params.items():
        if direction not in ("asc", "desc"):
            continue
        col = SORT_COLUMNS.get(key)
        if col is None:
            continue
        ordering = col.desc() if direction == "desc" else col.asc()
        # Nulls go last regardless of direction so they don't dominate rankings.
        orders.append(ordering.nulls_last())
    if not orders:
        orders = [Franchise.totalUnits.desc().nulls_last(), Franchise.name.asc()]
    return stmt.order_by(*orders)


@router.get("", summary="List franchises with filters & sorting (paginated)")
def list_franchises(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=500),
    search: Optional[str] = None,
    segment: Optional[str] = None,
    subsegment: Optional[str] = None,
    excludeSubsegment: Optional[str] = None,
    minInvestment: Optional[float] = None,
    maxInvestment: Optional[float] = None,
    minUnits: Optional[int] = None,
    maxUnits: Optional[int] = None,
    minROI: Optional[int] = None,
    maxROI: Optional[int] = None,
    minFranchiseFee: Optional[float] = None,
    maxFranchiseFee: Optional[float] = None,
    minRevenue: Optional[float] = None,
    maxRevenue: Optional[float] = None,
    minRating: Optional[float] = None,
    maxRating: Optional[float] = None,
    isSponsored: Optional[bool] = None,
    nameSort: Optional[str] = None,
    ratingSort: Optional[str] = None,
    unitsSort: Optional[str] = None,
    investmentSort: Optional[str] = None,
    roiSort: Optional[str] = None,
    franchiseFeeSort: Optional[str] = None,
    revenueSort: Optional[str] = None,
):
    filters = {
        "search": search,
        "segment": segment,
        "subsegment": subsegment,
        "excludeSubsegment": excludeSubsegment,
        "minInvestment": minInvestment,
        "maxInvestment": maxInvestment,
        "minUnits": minUnits,
        "maxUnits": maxUnits,
        "minROI": minROI,
        "maxROI": maxROI,
        "minFranchiseFee": minFranchiseFee,
        "maxFranchiseFee": maxFranchiseFee,
        "minRevenue": minRevenue,
        "maxRevenue": maxRevenue,
        "minRating": minRating,
        "maxRating": maxRating,
        "isSponsored": isSponsored,
    }
    sort_params = {
        "name":         nameSort,
        "rating":       ratingSort,
        "units":        unitsSort,
        "investment":   investmentSort,
        "roi":          roiSort,
        "franchiseFee": franchiseFeeSort,
        "revenue":      revenueSort,
    }

    stmt = select(Franchise)
    stmt = _apply_filters(stmt, only_active=True, filters=filters)
    stmt = _apply_sorts(stmt, sort_params)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * limit
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()

    return {
        # rankingPosition reflete a ordem da query atual (filtros + sort
        # aplicados), páginado. Para "posição global fixa por totalUnits"
        # independente do sort, usar GET /ranking.
        "data": [
            serialize_franchise(f, ranking_position=offset + idx + 1)
            for idx, f in enumerate(rows)
        ],
        "total": total,
        "page": page,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }


@router.get("/count", summary="Total active franchises matching filters")
def count_franchises(
    db: Session = Depends(get_db),
    segment: Optional[str] = None,
    minInvestment: Optional[float] = None,
    maxInvestment: Optional[float] = None,
    search: Optional[str] = None,
    isActive: Optional[bool] = True,
):
    stmt = select(func.count(Franchise.id))
    if isActive is not None:
        stmt = stmt.where(Franchise.isActive == isActive)
    # Só conta franquias aprovadas (consistente com /franchises list)
    stmt = stmt.where(Franchise.status == "APPROVED")
    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))
    if minInvestment is not None:
        stmt = stmt.where(Franchise.minimumInvestment >= minInvestment)
    if maxInvestment is not None:
        stmt = stmt.where(Franchise.maximumInvestment <= maxInvestment)
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))
    total = db.scalar(stmt) or 0
    return {"total": total}


# ===========================================================================
# Franchise options + admin endpoints
#
# These MUST be declared before the `/{slug}*` catch-all routes below so that
# literal paths (`/options`, `/admin/all`) win over the slug matcher.
#
#   GET   /franchises/options                  public — [{id, name}, ...]
#   GET   /franchises/admin/all                admin — paginated, inc. inactive
#   PATCH /franchises/{id}/toggle-status       admin — isActive
#   PATCH /franchises/{id}/toggle-review       admin — isReview
#   PATCH /franchises/{id}/toggle-sponsored    admin — isSponsored (max 5)
#   PATCH /franchises/{id}/sponsor-placements  admin — JSON placements array
# ===========================================================================


class ToggleStatusBody(BaseModel):
    isActive: bool


class ToggleReviewBody(BaseModel):
    isReview: bool


class ToggleSponsoredBody(BaseModel):
    isSponsored: bool


class UpdateSponsorPlacementsBody(BaseModel):
    placements: list[SponsorPlacementValue]


@router.get("/options", summary="Opções de franquia (id+name) — público")
def get_franchise_options(
    db: Session = Depends(get_db),
    availableOnly: bool = False,
    userId: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Public endpoint — returns [{id, name}].

    - default:                  all active franchises
    - availableOnly=true:       active AND ownerId IS NULL
    - availableOnly=true+userId: active AND (ownerId IS NULL OR ownerId=userId)
    """
    stmt = (
        select(Franchise.id, Franchise.name)
        .where(Franchise.isActive.is_(True))
        .order_by(Franchise.name.asc())
    )
    if availableOnly and userId:
        stmt = stmt.where(
            or_(Franchise.ownerId.is_(None), Franchise.ownerId == userId)
        )
    elif availableOnly:
        stmt = stmt.where(Franchise.ownerId.is_(None))

    rows = db.execute(stmt).all()
    return [{"id": row[0], "name": row[1]} for row in rows]


@router.get("/admin/all", summary="Lista admin paginada (inclui inativas)")
def get_all_franchises_for_admin(
    db: Session = Depends(get_db),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=500),
    search: Optional[str] = None,
    segment: Optional[str] = None,
    subsegment: Optional[str] = None,
    excludeSubsegment: Optional[str] = None,
    minInvestment: Optional[float] = None,
    maxInvestment: Optional[float] = None,
    minUnits: Optional[int] = None,
    maxUnits: Optional[int] = None,
    minROI: Optional[int] = None,
    maxROI: Optional[int] = None,
    minFranchiseFee: Optional[float] = None,
    maxFranchiseFee: Optional[float] = None,
    minRevenue: Optional[float] = None,
    maxRevenue: Optional[float] = None,
    minRating: Optional[float] = None,
    maxRating: Optional[float] = None,
    isSponsored: Optional[bool] = None,
    nameSort: Optional[str] = None,
    ratingSort: Optional[str] = None,
    unitsSort: Optional[str] = None,
    investmentSort: Optional[str] = None,
    roiSort: Optional[str] = None,
    franchiseFeeSort: Optional[str] = None,
    revenueSort: Optional[str] = None,
) -> dict[str, Any]:
    """Admin listing. Matches /franchises filters but:
      - does NOT restrict to isActive=true (admin sees everything)
      - includes totalActive / totalInactive / totalSponsored counters
      - omits the NestJS sponsored-first reordering with random selection
        (admin panel needs deterministic order, not the public UX bump).
    """
    filters = {
        "search": search,
        "segment": segment,
        "subsegment": subsegment,
        "excludeSubsegment": excludeSubsegment,
        "minInvestment": minInvestment,
        "maxInvestment": maxInvestment,
        "minUnits": minUnits,
        "maxUnits": maxUnits,
        "minROI": minROI,
        "maxROI": maxROI,
        "minFranchiseFee": minFranchiseFee,
        "maxFranchiseFee": maxFranchiseFee,
        "minRevenue": minRevenue,
        "maxRevenue": maxRevenue,
        "minRating": minRating,
        "maxRating": maxRating,
        "isSponsored": isSponsored,
    }
    sort_params = {
        "name":         nameSort,
        "rating":       ratingSort,
        "units":        unitsSort,
        "investment":   investmentSort,
        "roi":          roiSort,
        "franchiseFee": franchiseFeeSort,
        "revenue":      revenueSort,
    }

    stmt = select(Franchise)
    stmt = _apply_filters(stmt, only_active=False, filters=filters)
    stmt = _apply_sorts(stmt, sort_params)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * limit
    rows = db.scalars(
        stmt.options(selectinload(Franchise.contact)).offset(offset).limit(limit)
    ).all()

    total_active = (
        db.scalar(select(func.count()).select_from(Franchise).where(Franchise.isActive.is_(True))) or 0
    )
    total_inactive = (
        db.scalar(select(func.count()).select_from(Franchise).where(Franchise.isActive.is_(False))) or 0
    )
    total_sponsored = (
        db.scalar(select(func.count()).select_from(Franchise).where(Franchise.isSponsored.is_(True))) or 0
    )

    return {
        "data": [
            serialize_franchise(f, ranking_position=offset + idx + 1)
            for idx, f in enumerate(rows)
        ],
        "total": total,
        "totalActive": total_active,
        "totalInactive": total_inactive,
        "totalSponsored": total_sponsored,
        "page": page,
        "lastPage": max(1, ceil(total / limit)) if total else 1,
    }


def _load_franchise_or_404(db: Session, franchise_id: str) -> Franchise:
    f = db.scalar(select(Franchise).where(Franchise.id == franchise_id))
    if f is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Franchise not found")
    return f


@router.patch("/{franchise_id}/toggle-status", summary="Toggle isActive (admin)")
def toggle_franchise_status(
    franchise_id: str,
    body: ToggleStatusBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _load_franchise_or_404(db, franchise_id)
    franchise.isActive = body.isActive
    db.commit()
    db.refresh(franchise)

    # Side effects from NestJS skipped (no email service / cache in FastAPI):
    #   - emailService.sendUserUpdateNotification to owner
    #   - invalidateFranchiseCache (redis)
    logger.warning(
        "[toggle_franchise_status] franchise=%s isActive=%s — "
        "skipped owner email + cache invalidation (services not ported)",
        franchise_id, body.isActive,
    )

    return {
        "data": serialize_franchise(franchise),
        "message": f"Franchise {'activated' if body.isActive else 'deactivated'} successfully",
    }


@router.patch("/{franchise_id}/toggle-review", summary="Toggle isReview (admin)")
def toggle_franchise_review(
    franchise_id: str,
    body: ToggleReviewBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _load_franchise_or_404(db, franchise_id)
    franchise.isReview = body.isReview
    db.commit()
    db.refresh(franchise)
    return {
        "data": serialize_franchise(franchise),
        "message": "Franchise review toggled successfully",
    }


@router.patch("/{franchise_id}/toggle-sponsored", summary="Toggle isSponsored (admin, máx 5)")
def toggle_franchise_sponsored(
    franchise_id: str,
    body: ToggleSponsoredBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _load_franchise_or_404(db, franchise_id)

    if body.isSponsored:
        # Only enforce the cap when adding a new sponsored franchise. If the
        # franchise is already sponsored, toggling it to True is a no-op and
        # shouldn't count against the cap.
        if not franchise.isSponsored:
            sponsored_count = (
                db.scalar(
                    select(func.count())
                    .select_from(Franchise)
                    .where(Franchise.isSponsored.is_(True))
                )
                or 0
            )
            if sponsored_count >= MAX_SPONSORED_FRANCHISES:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Só podem existir no máximo 5 franquias patrocinadas ao mesmo tempo.",
                )

    franchise.isSponsored = body.isSponsored
    if not body.isSponsored:
        # Matches NestJS — clear placements when unsponsoring so the panel
        # doesn't keep stale placements for non-sponsored franchises.
        franchise.sponsorPlacements = []

    db.commit()
    db.refresh(franchise)
    return {
        "data": serialize_franchise(franchise),
        "message": f"Franchise {'sponsored' if body.isSponsored else 'unsponsored'} successfully",
    }


@router.patch("/{franchise_id}/sponsor-placements", summary="Update sponsor placements (admin)")
def update_sponsor_placements(
    franchise_id: str,
    body: UpdateSponsorPlacementsBody,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    franchise = _load_franchise_or_404(db, franchise_id)
    if not franchise.isSponsored:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot set sponsor placements for a non-sponsored franchise.",
        )

    # De-dupe while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for p in body.placements:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    franchise.sponsorPlacements = deduped
    db.commit()
    db.refresh(franchise)
    return {
        "data": serialize_franchise(franchise),
        "message": "Sponsor placements updated successfully",
    }


@router.get(
    "/{slug}/ranking",
    summary="Franquia + vizinhos no ranking (next/prev nav)",
)
def get_franchise_ranking(
    slug: str,
    db: Session = Depends(get_db),
    segment: Optional[str] = None,
    search: Optional[str] = None,
):
    # Build the same ordering as the default /franchises list so neighbor
    # navigation is stable: totalUnits DESC → name ASC, plus any subset
    # of the public list filters that the detail page forwards.
    stmt = select(Franchise).where(Franchise.isActive.is_(True))
    if segment:
        stmt = stmt.where(Franchise.segment.ilike(f"%{segment}%"))
    if search:
        stmt = stmt.where(Franchise.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(
        Franchise.totalUnits.desc().nulls_last(), Franchise.name.asc()
    )

    # Load only what we need for navigation (id, slug, name, position).
    ordered = db.execute(
        stmt.with_only_columns(Franchise.id, Franchise.slug, Franchise.name)
    ).all()

    idx = next(
        (i for i, row in enumerate(ordered) if row[1] == slug or row[0] == slug),
        None,
    )
    if idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Franchise not found"
        )

    # Load the full franchise for the current one.
    current = db.scalar(
        select(Franchise).where(Franchise.id == ordered[idx][0])
    )
    assert current is not None

    def _neighbor(offset: int) -> Optional[str]:
        j = idx + offset
        if 0 <= j < len(ordered):
            return ordered[j][1] or ordered[j][0]
        return None

    return {
        "data": {
            "franchiseWithRanking": {
                **serialize_franchise(current),
                "rankingPosition": idx + 1,
            },
            "nextFranchiseWithRanking": _neighbor(1),
            "previousFranchiseWithRanking": _neighbor(-1),
        }
    }


@router.get("/{slug}", summary="Get a single franchise by slug (or id)")
def get_franchise(
    slug: str,
    db: Session = Depends(get_db),
    current: Optional[JwtPayload] = Depends(get_optional_user),
):
    """
    Regras de visibilidade:
    - Franchise APPROVED: qualquer um pode ver (público).
    - Franchise PENDING/REJECTED: só owner ou admin pode ver.
    - Se não se enquadra, retorna 404 (não 403, pra não vazar existência).
    """
    stmt = (
        select(Franchise)
        .where(or_(Franchise.slug == slug, Franchise.id == slug))
        .options(
            selectinload(Franchise.contact),
            selectinload(Franchise.owner),
            selectinload(Franchise.business_models),
            selectinload(Franchise.reviews).selectinload(Review.author),
        )
    )
    franchise = db.scalars(stmt).first()
    if franchise is None:
        raise HTTPException(status_code=404, detail="Franchise not found")

    if franchise.status != "APPROVED":
        is_admin = current is not None and current.role == "ADMIN"
        is_owner = current is not None and current.id == franchise.ownerId
        if not (is_admin or is_owner):
            raise HTTPException(status_code=404, detail="Franchise not found")

    return {"data": serialize_franchise(franchise, include_relations=True)}


# ===========================================================================
# CSV import — admin endpoints
#
#   POST /franchises/import/csv               bulk create
#   POST /franchises/import/csv/update/{id}   single update
#
# Both accept multipart/form-data with a `file` field. Headers are translated
# PT→EN per the same map used by the NestJS importer. Numeric fields accept
# Brazilian formatting ("R$ 1.500,00"), booleans accept true/false/sim/não.
#
# Out of scope for this port (caveats):
#   - External image URL download (logoUrl/thumbnailUrl saved as-is)
#   - Per-row image-processing errors that NestJS captured separately
#   - Slug auto-generation (rows without `slug` are stored with slug=NULL;
#     admin must fill it in via a follow-up update if they want pretty URLs)
# ===========================================================================


CSV_HEADER_PT_TO_EN: dict[str, str] = {
    "nome": "name",
    "descrição": "description",
    "descricao": "description",
    "segmento": "segment",
    "investimento_mínimo": "minimumInvestment",
    "investimento_minimo": "minimumInvestment",
    "investimento_máximo": "maximumInvestment",
    "investimento_maximo": "maximumInvestment",
    "cidade": "headquarter",
    "estado": "headquarterState",
    "site": "website",
    "e-mail": "email",
    "email": "email",
    "telefone": "phone",
    "total_unidades": "totalUnits",
}

# Field groups used for type coercion and ContactInfo split.
_FRANCHISE_INT_FIELDS = (
    "totalUnits", "totalUnitsInBrazil", "minimumReturnOnInvestment",
    "maximumReturnOnInvestment", "storeArea", "brandFoundationYear",
    "franchiseStartYear", "abfSince",
)
_FRANCHISE_DECIMAL_FIELDS = (
    "minimumInvestment", "maximumInvestment", "franchiseFee",
    "averageMonthlyRevenue", "royalties", "advertisingFee",
    "setupCapital", "workingCapital",
)
_FRANCHISE_BOOL_FIELDS = ("isActive", "isSponsored", "isReview", "isAbfAssociated")
_FRANCHISE_STR_FIELDS = (
    "name", "sku", "slug", "segment", "subsegment", "businessType",
    "headquarter", "headquarterState", "description", "detailedDescription",
    "logoUrl", "thumbnailUrl", "videoUrl", "scrapedWebsite",
    "calculationBaseAdFee", "calculationBaseRoyaltie", "unitsEvolution",
)
_CONTACT_FIELDS = ("phone", "email", "website")
_KNOWN_FIELDS = frozenset(
    _FRANCHISE_INT_FIELDS
    + _FRANCHISE_DECIMAL_FIELDS
    + _FRANCHISE_BOOL_FIELDS
    + _FRANCHISE_STR_FIELDS
    + _CONTACT_FIELDS
)


def _translate_row(raw: dict[str, Any]) -> dict[str, Any]:
    """PT→EN headers, with whitespace stripped from keys."""
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k is None:
            continue
        key = CSV_HEADER_PT_TO_EN.get(k.strip(), k.strip())
        out[key] = v
    return out


def _coerce_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


_NUMBER_CLEAN_RE = re.compile(r"[R$\s]")


def _coerce_number_str(v: Any) -> Optional[str]:
    """Strip R$/spaces, normalize BR notation `1.500,00` → `1500.00`."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = _NUMBER_CLEAN_RE.sub("", s)
    # If both `.` and `,` present, BR style — `.` is thousands sep, `,` is decimal.
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # Only comma → treat as decimal separator.
        s = s.replace(",", ".")
    return s or None


def _coerce_int(v: Any) -> Optional[int]:
    s = _coerce_number_str(v)
    if s is None:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        raise ValueError(f"Valor inteiro inválido: {v!r}")


def _coerce_decimal(v: Any) -> Optional[Decimal]:
    s = _coerce_number_str(v)
    if s is None:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Valor decimal inválido: {v!r}")


def _coerce_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    if s in ("true", "1", "sim", "yes", "y", "t"):
        return True
    if s in ("false", "0", "não", "nao", "no", "n", "f"):
        return False
    raise ValueError(f"Valor booleano inválido: {v!r}")


def _parse_csv(text: str) -> list[dict[str, Any]]:
    """Returns a list of header→value dicts. Empty rows skipped."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows: list[dict[str, Any]] = []
        for row in reader:
            # Drop entirely-empty rows
            if not any((str(v).strip() if v is not None else "") for v in row.values()):
                continue
            rows.append(row)
        return rows
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {e}",
        )


def _validate_row(translated: dict[str, Any], *, require_name: bool) -> dict[str, Any]:
    """Coerce + validate a translated row. Returns a clean dict of typed values
    ready to apply to ORM objects. Raises ValueError on bad cells."""
    cleaned: dict[str, Any] = {}

    # Strings
    for f in _FRANCHISE_STR_FIELDS:
        if f in translated:
            v = _coerce_str(translated[f])
            if v is not None:
                cleaned[f] = v

    # Integers
    for f in _FRANCHISE_INT_FIELDS:
        if f in translated:
            v = _coerce_int(translated[f])
            if v is not None:
                cleaned[f] = v

    # Decimals
    for f in _FRANCHISE_DECIMAL_FIELDS:
        if f in translated:
            v = _coerce_decimal(translated[f])
            if v is not None:
                cleaned[f] = v

    # Booleans
    for f in _FRANCHISE_BOOL_FIELDS:
        if f in translated:
            v = _coerce_bool(translated[f])
            if v is not None:
                cleaned[f] = v

    # Contact (kept separate — applied to ContactInfo, not Franchise)
    contact: dict[str, Any] = {}
    for f in _CONTACT_FIELDS:
        if f in translated:
            v = _coerce_str(translated[f])
            if v is not None:
                contact[f] = v
    if contact:
        cleaned["__contact"] = contact

    if require_name and not cleaned.get("name"):
        raise ValueError("Coluna `name` (ou `nome`) é obrigatória")

    return cleaned


def _apply_to_franchise(franchise: Franchise, cleaned: dict[str, Any]) -> None:
    """Apply cleaned CSV values to a Franchise ORM object (excluding contact)."""
    for k, v in cleaned.items():
        if k == "__contact":
            continue
        setattr(franchise, k, v)


def _apply_contact(
    db: Session, franchise: Franchise, contact: dict[str, Any]
) -> None:
    """Create or update the franchise's ContactInfo row using cleaned contact
    fields. Mirrors NestJS franchisorUpdateFranchise contact handling: missing
    required fields default to empty string."""
    if not contact:
        return
    if franchise.contact is not None:
        if "phone" in contact:
            franchise.contact.phone = contact["phone"]
        if "email" in contact:
            franchise.contact.email = contact["email"]
        if "website" in contact:
            franchise.contact.website = contact["website"]
        return
    new_contact = ContactInfo(
        phone=contact.get("phone", ""),
        email=contact.get("email", ""),
        website=contact.get("website", ""),
    )
    db.add(new_contact)
    db.flush()  # need contact.id before linking
    franchise.contactId = new_contact.id


async def _read_csv_file(file: UploadFile) -> str:
    """Read multipart upload as UTF-8 text; reject empty / non-CSV content."""
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded"
        )
    if file.filename and not file.filename.lower().endswith(".csv"):
        # Be lenient on mimetype (varies wildly by client), strict on extension.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed",
        )
    try:
        return raw.decode("utf-8-sig")  # tolerate BOM
    except UnicodeDecodeError:
        try:
            return raw.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV must be UTF-8 or Latin-1 encoded",
            )


# ---------------------------------------------------------------------------
# POST /franchises/import/csv  — bulk create
# ---------------------------------------------------------------------------

@router.post("/import/csv", summary="Import franchises from CSV (admin)")
async def import_franchises_csv(
    file: UploadFile = File(...),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    text = await _read_csv_file(file)
    raw_rows = _parse_csv(text)

    errors: list[dict[str, Any]] = []
    success = 0

    for idx, raw in enumerate(raw_rows):
        row_num = idx + 1
        try:
            translated = _translate_row(raw)
            cleaned = _validate_row(translated, require_name=True)
        except ValueError as e:
            errors.append({"row": row_num, "data": raw, "error": str(e)})
            continue

        contact = cleaned.pop("__contact", None) or {}
        # SAVEPOINT per row so a single failing row (unique constraint, bad
        # CheckConstraint, etc.) doesn't abort the rows that already succeeded.
        try:
            with db.begin_nested():
                franchise = Franchise(
                    id=uuid.uuid4().hex,
                    sponsorPlacements=[],
                    **cleaned,
                )
                if contact:
                    new_contact = ContactInfo(
                        phone=contact.get("phone", ""),
                        email=contact.get("email", ""),
                        website=contact.get("website", ""),
                    )
                    db.add(new_contact)
                    db.flush()
                    franchise.contactId = new_contact.id
                db.add(franchise)
                db.flush()
        except Exception as e:
            errors.append(
                {
                    "row": row_num,
                    "data": raw,
                    "error": f"Database error: {e}",
                }
            )
            continue
        success += 1

    if success > 0:
        db.commit()

    logger.warning(
        "[import_franchises_csv] total=%s success=%s failed=%s",
        len(raw_rows), success, len(errors),
    )

    return {
        "total": len(raw_rows),
        "success": success,
        "failed": len(errors),
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# POST /franchises/import/csv/update/{franchise_id}  — single-row update
# ---------------------------------------------------------------------------

@router.post(
    "/import/csv/update/{franchise_id}",
    summary="Update one franchise from CSV (admin)",
)
async def update_franchise_from_csv(
    franchise_id: str,
    file: UploadFile = File(...),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not franchise_id or not franchise_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Franchise ID is required",
        )

    text = await _read_csv_file(file)
    raw_rows = _parse_csv(text)
    total = len(raw_rows)

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or has no data rows",
        )
    if total > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"CSV update only supports single row updates. Found {total} rows. "
                "Please provide only one row with update data."
            ),
        )

    raw = raw_rows[0]
    try:
        translated = _translate_row(raw)
        cleaned = _validate_row(translated, require_name=False)
    except ValueError as e:
        return {
            "total": 1,
            "success": 0,
            "failed": 1,
            "errors": [{"row": 1, "data": raw, "error": str(e)}],
        }

    if not any(k for k in cleaned if k != "__contact") and "__contact" not in cleaned:
        return {
            "total": 1,
            "success": 0,
            "failed": 1,
            "errors": [
                {
                    "row": 1,
                    "data": raw,
                    "error": "At least one field must be provided for update",
                }
            ],
        }

    franchise = db.scalar(
        select(Franchise)
        .where(Franchise.id == franchise_id)
        .options(selectinload(Franchise.contact))
    )
    if franchise is None:
        return {
            "total": 1,
            "success": 0,
            "failed": 1,
            "errors": [
                {"row": 1, "data": raw, "error": f"Franchise {franchise_id} not found"}
            ],
        }

    contact = cleaned.pop("__contact", None) or {}
    _apply_to_franchise(franchise, cleaned)
    _apply_contact(db, franchise, contact)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "total": 1,
            "success": 0,
            "failed": 1,
            "errors": [{"row": 1, "data": raw, "error": f"Database error: {e}"}],
        }

    logger.warning(
        "[update_franchise_from_csv] franchise=%s success",
        franchise_id,
    )

    return {"total": 1, "success": 1, "failed": 0, "errors": []}


# ===========================================================================
# Franchisor-facing endpoints — under /franchisor/franchises (franchisor_router)
#
#   GET  /franchisor/franchises/me       list franchises owned by caller
#   POST /franchisor/franchises          create an additional brand (PENDING)
# ===========================================================================


class CreateAdditionalFranchiseBody(BaseModel):
    """Payload pra franqueador aprovado criar uma marca adicional."""
    streamName: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    detailedDescription: Optional[str] = Field(None, max_length=10000)
    logoUrl: Optional[str] = Field(None, max_length=500)
    segment: Optional[str] = Field(None, max_length=100)
    subsegment: Optional[str] = Field(None, max_length=100)
    headquarter: Optional[str] = Field(None, max_length=100)
    headquarterState: Optional[str] = Field(None, max_length=2)


def _sync_hubspot_for_additional_franchise(
    *,
    franchise_id: str,
    franchise_name: str,
    user_id: str,
    hubspot_contact_id: Optional[str],
) -> None:
    """Background task: cria Company no HubSpot pra franquia adicional,
    associa ao Contact do franqueador. Falhas só logam."""
    import asyncio

    async def _run() -> None:
        company_id = await hubspot_client.create_franchisor_company(
            stream_name=franchise_name,
            mode="NEW",
            franchise_id=franchise_id,
        )
        if not company_id:
            logger.warning(
                "HubSpot create_franchisor_company retornou None pra franquia adicional %s",
                franchise_id,
            )
            return

        db2 = SessionLocal()
        try:
            franchise = db2.get(Franchise, franchise_id)
            if franchise is None:
                logger.warning(
                    "Franchise %s sumiu antes do sync HubSpot", franchise_id
                )
                return
            if hubspot_contact_id:
                await hubspot_client.associate_contact_with_company(
                    hubspot_contact_id=hubspot_contact_id,
                    hubspot_company_id=company_id,
                )
        finally:
            db2.close()

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Falha sync HubSpot franquia adicional %s: %s", franchise_id, exc
        )


@franchisor_router.get("/me", summary="Lista franquias do franqueador autenticado")
def my_franchises(
    db: Session = Depends(get_db),
    current: JwtPayload = Depends(require_role("FRANCHISOR")),
) -> dict[str, Any]:
    """
    Retorna todas as Franchises do user autenticado (ownerId=current.id),
    incluindo PENDING/REJECTED. Usado no painel do franqueador pra mostrar
    banner de status ("aprovada", "em análise", "rejeitada").
    """
    stmt = (
        select(Franchise)
        .where(Franchise.ownerId == current.id)
        .options(selectinload(Franchise.contact))
        .order_by(Franchise.createdAt.desc())
    )
    rows = db.scalars(stmt).all()

    return {
        "data": [serialize_franchise(f) for f in rows],
        "total": len(rows),
    }


@franchisor_router.post("", summary="Franqueador cria marca adicional")
def create_additional_franchise(
    body: CreateAdditionalFranchiseBody,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current: JwtPayload = Depends(require_role("FRANCHISOR")),
) -> dict[str, Any]:
    """
    Franqueador aprovado cria uma marca adicional.
    - Cria Franchise com status=PENDING, isActive=False, ownerId=current.id
    - Gera slug automático único
    - Dispara sync HubSpot (Company + Association com Contact)
    - Dispara email pra admins notificando

    Bloqueia se:
    - Já existe Franchise com esse nome (sugere usar painel existente)
    - User já tem marca adicional PENDING com mesmo nome (evita spam)
    """
    name_clean = body.streamName.strip()
    if len(name_clean) < 2:
        raise HTTPException(status_code=400, detail="streamName muito curto")

    existing_by_name = db.scalar(
        select(Franchise).where(Franchise.name == name_clean)
    )
    if existing_by_name is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Já existe uma franquia cadastrada com o nome '{name_clean}'. "
                f"Se for sua, acesse pelo painel. Se não for, escolha outro nome."
            ),
        )

    own_pending = db.scalar(
        select(Franchise).where(
            Franchise.ownerId == current.id,
            Franchise.name == name_clean,
            Franchise.status == "PENDING",
        )
    )
    if own_pending is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Você já tem uma marca '{name_clean}' pendente de aprovação.",
        )

    franchise_slug = generate_unique_slug(name_clean, db)

    user = db.get(User, current.id)
    if user is None:
        raise HTTPException(
            status_code=500, detail="User autenticado não encontrado no banco"
        )

    new_franchise = Franchise(
        id=uuid.uuid4().hex,
        name=name_clean,
        slug=franchise_slug,
        status="PENDING",
        isActive=False,
        ownerId=current.id,
        description=body.description,
        detailedDescription=body.detailedDescription,
        logoUrl=body.logoUrl,
        segment=body.segment,
        subsegment=body.subsegment,
        headquarter=body.headquarter,
        headquarterState=body.headquarterState,
        sponsorPlacements={},
    )
    db.add(new_franchise)
    db.commit()
    db.refresh(new_franchise)

    background_tasks.add_task(
        _sync_hubspot_for_additional_franchise,
        franchise_id=new_franchise.id,
        franchise_name=new_franchise.name,
        user_id=current.id,
        hubspot_contact_id=user.hubspotContactId,
    )

    admin_emails = db.scalars(
        select(User.email).where(User.role == "ADMIN", User.isActive.is_(True))
    ).all()
    for admin_email in admin_emails:
        background_tasks.add_task(
            send_additional_franchise_received,
            to=admin_email,
            franchisor_name=user.name,
            franchisor_email=user.email,
            stream_name=name_clean,
            franchise_id=new_franchise.id,
        )

    return {
        "data": serialize_franchise(new_franchise),
        "message": "Franquia criada com sucesso. Aguardando aprovação do admin.",
    }


# ===========================================================================
# Admin decision endpoints — approve/reject any Franchise (additional brands
# created by franchisors via POST /franchisor/franchises, or any PENDING row).
#
#   POST /franchises/admin/{id}/approve
#   POST /franchises/admin/{id}/reject
# ===========================================================================


class RejectFranchiseBody(BaseModel):
    rejectionReason: str = Field(..., min_length=5, max_length=1000)


def _sync_hubspot_on_franchise_decision(
    *,
    franchise_id: str,
    decision: str,
) -> None:
    """Background task: atualiza status da Company no HubSpot.
    decision: 'APPROVED' ou 'REJECTED'."""
    import asyncio

    async def _run() -> None:
        company_id = await hubspot_client.get_company_by_franchise_id(franchise_id)
        if not company_id:
            logger.warning(
                "HubSpot: sem Company pra franchise_id=%s, skip sync %s",
                franchise_id,
                decision,
            )
            return
        if decision == "APPROVED":
            await hubspot_client.mark_company_approved(company_id)
        elif decision == "REJECTED":
            await hubspot_client.mark_company_rejected(company_id)

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Falha sync HubSpot decisão franquia %s %s: %s",
            decision,
            franchise_id,
            exc,
        )


@router.post(
    "/admin/{franchise_id}/approve",
    summary="Admin aprova franquia (adicional ou qualquer PENDING)",
)
def admin_approve_franchise(
    franchise_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
) -> dict[str, Any]:
    """
    Aprova uma Franchise:
    - status → APPROVED
    - isActive → true (passa a aparecer no site público)
    - Sync HubSpot Company
    - Email pro owner (franqueador)

    Funciona pra qualquer Franchise em PENDING, independente de ter FranchisorRequest associada.
    Usado principalmente pras marcas adicionais criadas via POST /franchisor/franchises.
    """
    franchise = db.scalar(
        select(Franchise)
        .where(Franchise.id == franchise_id)
        .options(selectinload(Franchise.owner))
    )
    if franchise is None:
        raise HTTPException(status_code=404, detail="Franchise not found")

    if franchise.status == "APPROVED":
        raise HTTPException(status_code=409, detail="Franchise já está aprovada")

    franchise.status = "APPROVED"
    franchise.isActive = True
    db.commit()
    db.refresh(franchise)

    if franchise.owner is not None:
        background_tasks.add_task(
            send_additional_franchise_approved,
            to=franchise.owner.email,
            user_name=franchise.owner.name,
            stream_name=franchise.name,
            franchise_slug=franchise.slug or franchise.id,
        )

    background_tasks.add_task(
        _sync_hubspot_on_franchise_decision,
        franchise_id=franchise.id,
        decision="APPROVED",
    )

    return {
        "message": "Franchise approved successfully",
        "franchiseId": franchise.id,
        "slug": franchise.slug,
    }


@router.post(
    "/admin/{franchise_id}/reject",
    summary="Admin rejeita franquia",
)
def admin_reject_franchise(
    franchise_id: str,
    body: RejectFranchiseBody,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
) -> dict[str, Any]:
    """
    Rejeita uma Franchise:
    - status → REJECTED
    - isActive → false (se estava true, deixa de aparecer no site)
    - Sync HubSpot Company
    - Email pro owner com motivo
    """
    franchise = db.scalar(
        select(Franchise)
        .where(Franchise.id == franchise_id)
        .options(selectinload(Franchise.owner))
    )
    if franchise is None:
        raise HTTPException(status_code=404, detail="Franchise not found")

    if franchise.status == "REJECTED":
        raise HTTPException(status_code=409, detail="Franchise já está rejeitada")

    reason = body.rejectionReason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="rejectionReason vazio")

    franchise.status = "REJECTED"
    franchise.isActive = False
    db.commit()
    db.refresh(franchise)

    if franchise.owner is not None:
        background_tasks.add_task(
            send_additional_franchise_rejected,
            to=franchise.owner.email,
            user_name=franchise.owner.name,
            stream_name=franchise.name,
            rejection_reason=reason,
        )

    background_tasks.add_task(
        _sync_hubspot_on_franchise_decision,
        franchise_id=franchise.id,
        decision="REJECTED",
    )

    return {
        "message": "Franchise rejected successfully",
        "franchiseId": franchise.id,
        "rejectionReason": reason,
    }
