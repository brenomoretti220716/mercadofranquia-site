"""
Serializers that convert ORM objects to JSON-friendly dicts matching the
Franchise/ContactInfo/etc. TypeScript types the Next.js frontend consumes.

Key concerns:
- `Decimal` → `float` (JSON-compatible, frontend uses `number`).
- `datetime` → ISO-8601 string.
- `Franchise.galleryUrls` is stored as TEXT (JSON-encoded array historically);
  we parse it back into a list for the API response.
- `Franchise.sponsorPlacements` is JSONB; SQLAlchemy already returns a list/dict.
"""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BusinessModel,
    ContactInfo,
    Franchise,
    Review,
    ReviewResponse,
    User,
)


def _num(val: Any) -> Optional[float | int]:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return val


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def parse_gallery_urls(raw: Optional[str]) -> list[str]:
    """
    Franchise.galleryUrls is stored as TEXT. Historically it holds either:
      - a JSON-encoded array: '["url1","url2"]'
      - a comma-separated list
      - a single URL
    Parse defensively and always return a list[str].
    """
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x]
        except json.JSONDecodeError:
            pass
    if "," in raw:
        return [s.strip() for s in raw.split(",") if s.strip()]
    return [raw]


def parse_video_urls(raw: Optional[str]) -> list[str]:
    """
    Franchise.videoUrl column is stored as TEXT holding a JSON-encoded array
    (same shape as galleryUrls). The API exposes it as the plural `videoUrls`
    field to match the underlying list structure.
    """
    return parse_gallery_urls(raw)


def serialize_contact(c: Optional[ContactInfo]) -> Optional[dict[str, Any]]:
    if c is None:
        return None
    return {
        "id": c.id,
        "phone": c.phone,
        "email": c.email,
        "website": c.website,
    }


def serialize_owner(o: Optional[User]) -> Optional[dict[str, Any]]:
    if o is None:
        return None
    return {
        "id": o.id,
        "name": o.name,
        "email": o.email,
        "role": o.role,
        "isActive": o.isActive,
        "createdAt": _iso(o.createdAt),
        "updatedAt": _iso(o.updatedAt),
    }


def serialize_business_model(bm: BusinessModel) -> dict[str, Any]:
    return {
        "id": bm.id,
        "name": bm.name,
        "description": bm.description,
        "photoUrl": bm.photoUrl,
        "franchiseId": bm.franchiseId,
        "createdAt": _iso(bm.createdAt),
        "updatedAt": _iso(bm.updatedAt),
    }


def _serialize_response(
    rr: ReviewResponse, author: Optional[User]
) -> dict[str, Any]:
    """
    Espelha routers/reviews.py:_serialize_response.

    NOTA: ReviewResponse nao tem coluna `anonymous` no model, entao nao
    ha mascara analoga ao Review.anonymous. Respostas sao sempre publicas
    e atribuiveis. Se uma fatia futura adicionar anonimato a ReviewResponse,
    aplicar a mesma logica de mascarar `name` server-side aqui.
    """
    return {
        "id": rr.id,
        "content": rr.content,
        "reviewId": rr.reviewId,
        "authorId": rr.authorId,
        "createdAt": _iso(rr.createdAt),
        "updatedAt": _iso(rr.updatedAt),
        "author": (
            {"id": author.id, "name": author.name, "role": author.role}
            if author is not None
            else None
        ),
    }


def _load_response_authors(
    db: Session, reviews: list[Review]
) -> dict[str, User]:
    """
    Batch-load dos User rows de cada autor de ReviewResponse na lista de
    reviews. Necessario porque ReviewResponse nao tem `author` relationship
    declarada (so authorId FK), entao SQLAlchemy nao traz junto via
    selectinload(Review.responses) sozinho.

    Espelha routers/reviews.py:_load_response_authors.
    """
    author_ids: set[str] = set()
    for r in reviews:
        for rr in getattr(r, "responses", []) or []:
            if rr.authorId:
                author_ids.add(rr.authorId)
    if not author_ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(author_ids))).all()
    return {u.id: u for u in users}


def serialize_review(
    r: Review,
    *,
    response_authors: Optional[dict[str, User]] = None,
) -> dict[str, Any]:
    """
    Inclui `author: { id, name } | null` espelhando o shape de
    routers/reviews.py:_serialize_review. Mascara nome quando
    `r.anonymous=True` retornando author=null. Requer
    `selectinload(Review.author)` no query (ja feito em
    routers/franchises.py:get_franchise).

    Tambem inclui `responses: [...]` quando a relacao Review.responses
    foi pre-carregada (selectinload). Os autores das responses sao
    resolvidos via `response_authors` (dict authorId -> User), que o
    caller deve montar via _load_response_authors. Se o map for None,
    cada response sai com author=null.
    """
    author = getattr(r, "author", None)
    ra_map = response_authors or {}
    responses_payload = [
        _serialize_response(rr, ra_map.get(rr.authorId))
        for rr in (getattr(r, "responses", []) or [])
    ]
    return {
        "id": r.id,
        "rating": r.rating,
        "comment": r.comment,
        "anonymous": r.anonymous,
        "isActive": r.isActive,
        "isFranchisee": r.isFranchisee,
        "authorId": r.authorId,
        "franchiseId": r.franchiseId,
        "createdAt": _iso(r.createdAt),
        "author": (
            None
            if (author is None or r.anonymous)
            else {"id": author.id, "name": author.name}
        ),
        "responses": responses_payload,
    }


def serialize_franchise(
    f: Franchise,
    *,
    include_relations: bool = False,
    ranking_position: Optional[int] = None,
    response_authors: Optional[dict[str, User]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": f.id,
        "name": f.name,
        "slug": f.slug,
        "sku": f.sku,
        "minimumInvestment": _num(f.minimumInvestment),
        "maximumInvestment": _num(f.maximumInvestment),
        "headquarterState": f.headquarterState,
        "headquarter": f.headquarter,
        "totalUnits": f.totalUnits,
        "totalUnitsInBrazil": f.totalUnitsInBrazil,
        "unitsEvolution": f.unitsEvolution,
        "segment": f.segment,
        "subsegment": f.subsegment,
        "businessType": f.businessType,
        "brandFoundationYear": f.brandFoundationYear,
        "franchiseStartYear": f.franchiseStartYear,
        "abfSince": f.abfSince,
        "minimumReturnOnInvestment": f.minimumReturnOnInvestment,
        "maximumReturnOnInvestment": f.maximumReturnOnInvestment,
        "franchiseFee": _num(f.franchiseFee),
        "averageMonthlyRevenue": _num(f.averageMonthlyRevenue),
        "royalties": _num(f.royalties),
        "advertisingFee": _num(f.advertisingFee),
        "setupCapital": _num(f.setupCapital),
        "workingCapital": _num(f.workingCapital),
        "storeArea": f.storeArea,
        "calculationBaseRoyaltie": f.calculationBaseRoyaltie,
        "calculationBaseAdFee": f.calculationBaseAdFee,
        "videoUrls": parse_video_urls(f.videoUrl),
        "thumbnailUrl": f.thumbnailUrl,
        "galleryUrls": parse_gallery_urls(f.galleryUrls),
        "logoUrl": f.logoUrl,
        "description": f.description,
        "detailedDescription": f.detailedDescription,
        "isActive": f.isActive,
        "status": f.status,
        "isAbfAssociated": f.isAbfAssociated,
        "isSponsored": f.isSponsored,
        "sponsorPlacements": list(f.sponsorPlacements or []),
        "averageRating": f.averageRating,
        "ratingSum": f.ratingSum,
        "reviewCount": f.reviewCount,
        "favoritesCount": f.favoritesCount,
        "isReview": f.isReview,
        "contactId": f.contactId,
        "ownerId": f.ownerId,
        "rankingPosition": ranking_position,
        "createdAt": _iso(f.createdAt),
        "updatedAt": _iso(f.updatedAt),
        # Landing redesign — Fatia 0.5 (alembic 66a4e030b691).
        "tagline": f.tagline,
        "differentials": f.differentials,
        "idealFranchiseeProfile": f.idealFranchiseeProfile,
        "processSteps": f.processSteps,
        "testimonials": f.testimonials,
        "bannerUrl": f.bannerUrl,
        "phone": f.phone,
        "whatsapp": f.whatsapp,
        "publicEmail": f.publicEmail,
        "instagramUrl": f.instagramUrl,
        "facebookUrl": f.facebookUrl,
        "linkedinUrl": f.linkedinUrl,
        "totalUnitsUpdatedAt": _iso(f.totalUnitsUpdatedAt),
        "totalUnitsLastConfirmedAt": _iso(f.totalUnitsLastConfirmedAt),
    }

    if include_relations:
        payload["contact"] = serialize_contact(f.contact)
        payload["owner"] = serialize_owner(f.owner)
        payload["businessModels"] = [
            serialize_business_model(bm) for bm in (f.business_models or [])
        ]
        payload["reviews"] = [
            serialize_review(r, response_authors=response_authors)
            for r in (f.reviews or [])
            if r.isActive
        ]
    return payload
