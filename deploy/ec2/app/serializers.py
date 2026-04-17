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

from app.models import (
    BusinessModel,
    ContactInfo,
    Franchise,
    Review,
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


def serialize_review(r: Review) -> dict[str, Any]:
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
    }


def serialize_franchise(
    f: Franchise,
    *,
    include_relations: bool = False,
    ranking_position: Optional[int] = None,
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
        "videoUrl": f.videoUrl,
        "thumbnailUrl": f.thumbnailUrl,
        "galleryUrls": parse_gallery_urls(f.galleryUrls),
        "logoUrl": f.logoUrl,
        "description": f.description,
        "detailedDescription": f.detailedDescription,
        "isActive": f.isActive,
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
    }

    if include_relations:
        payload["contact"] = serialize_contact(f.contact)
        payload["owner"] = serialize_owner(f.owner)
        payload["businessModels"] = [
            serialize_business_model(bm) for bm in (f.business_models or [])
        ]
        payload["reviews"] = [
            serialize_review(r) for r in (f.reviews or []) if r.isActive
        ]
    return payload
