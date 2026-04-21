"""
Serializers for User / UserProfile / FranchisorRequest — shape the Next.js
frontend expects when talking to `/users/me`, `/users/register/*`, etc.

Shape derived from the NestJS service responses + `web/src/schemas/auth/auth.ts`
payload shape + `useGetMe`/`useUpdateProfile` consumers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.models import (
    FranchisorRequest,
    FranchisorUser,
    User,
    UserProfile,
)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def serialize_user_profile(p: Optional[UserProfile]) -> Optional[dict[str, Any]]:
    if p is None:
        return None
    return {
        "id": p.id,
        "userId": p.userId,
        "city": p.city,
        "interestSectors": p.interestSectors,
        "interestRegion": p.interestRegion,
        "investmentRange": p.investmentRange,
    }


def serialize_franchisor_profile(f: Optional[FranchisorUser]) -> Optional[dict[str, Any]]:
    if f is None:
        return None
    return {
        "id": f.id,
        "streamName": f.streamName,
        "userId": f.userId,
        "cnpj": f.cnpj,
        "responsable": f.responsable,
        "responsableRole": f.responsableRole,
        "commercialEmail": f.commercialEmail,
        "commercialPhone": f.commercialPhone,
        "cnpjCardPath": f.cnpjCardPath,
        "socialContractPath": f.socialContractPath,
        "createdAt": _iso(f.createdAt),
        "updatedAt": _iso(f.updatedAt),
    }


def serialize_franchisee_summary(franchise: Any) -> dict[str, Any]:
    """Subset of Franchise fields returned alongside a user's franchiseeOf list."""
    return {
        "id": franchise.id,
        "name": franchise.name,
        "slug": franchise.slug,
        "segment": franchise.segment,
        "subsegment": franchise.subsegment,
        "logoUrl": franchise.logoUrl,
    }


def serialize_franchise_admin_summary(franchise: Any) -> dict[str, Any]:
    """Wider Franchise summary used in admin listings (members + franchisors).

    Mirrors the Prisma `select` blocks in NestJS MembersService and
    FranchisorsService — includes investment range and headquarter state.
    """
    def _decimal(v: Any) -> Optional[float]:
        return float(v) if v is not None else None

    return {
        "id": franchise.id,
        "name": franchise.name,
        "segment": franchise.segment,
        "subsegment": franchise.subsegment,
        "minimumInvestment": _decimal(franchise.minimumInvestment),
        "maximumInvestment": _decimal(franchise.maximumInvestment),
        "totalUnits": franchise.totalUnits,
        "headquarterState": franchise.headquarterState,
    }


def serialize_franchisor_request_for_franchisor_listing(
    r: Optional["FranchisorRequest"],
) -> Optional[dict[str, Any]]:
    """Subset shape of FranchisorRequest as included alongside a Franchisor user
    in the admin listing — matches the NestJS Prisma `select` in
    FranchisorsService.findFranchisorsPaginated."""
    if r is None:
        return None
    reviewer = None
    # The reviewer relationship isn't preloaded in this snapshot; routers can
    # populate `reviewer` separately if eager-loaded. Fall back to bare id.
    return {
        "id": r.id,
        "status": r.status,
        "rejectionReason": r.rejectionReason,
        "reviewedBy": r.reviewedBy,
        "reviewedAt": _iso(r.reviewedAt),
        "createdAt": _iso(r.createdAt),
        "updatedAt": _iso(r.updatedAt),
        "streamName": r.streamName,
        "mode": r.mode,
        "franchiseId": r.franchiseId,
        "hubspotCompanyId": r.hubspotCompanyId,
        "reviewer": reviewer,
    }


def serialize_user_admin_member(u: User) -> dict[str, Any]:
    """User shape returned in `GET /admin/members` listings."""
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "isActive": bool(u.isActive),
        "cpf": u.cpf,
        "phone": u.phone,
        "createdAt": _iso(u.createdAt),
        "updatedAt": _iso(u.updatedAt),
        "profile": serialize_user_profile(getattr(u, "profile", None)),
        "franchiseeOf": [
            serialize_franchise_admin_summary(f)
            for f in (getattr(u, "franchises_as_franchisee", []) or [])
        ],
    }


def serialize_user_admin_franchisor(u: User) -> dict[str, Any]:
    """User shape returned in `GET /admin/franchisors` listings."""
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "isActive": bool(u.isActive),
        "cpf": u.cpf,
        "phone": u.phone,
        "createdAt": _iso(u.createdAt),
        "updatedAt": _iso(u.updatedAt),
        "franchisorRequest": serialize_franchisor_request_for_franchisor_listing(
            getattr(u, "franchisor_request", None)
        ),
        "ownedFranchises": [
            serialize_franchise_admin_summary(f)
            for f in (getattr(u, "franchises_owned", []) or [])
        ],
    }


def serialize_user_admin_admin(u: User) -> dict[str, Any]:
    """User shape returned in `GET /admin` (admins listing) and findById."""
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "isActive": bool(u.isActive),
        "cpf": u.cpf,
        "phone": u.phone,
        "createdAt": _iso(u.createdAt),
        "updatedAt": _iso(u.updatedAt),
    }


def serialize_user(
    u: User,
    *,
    include_profile: bool = True,
    include_franchisor_profile: bool = True,
    include_franchisees: bool = True,
) -> dict[str, Any]:
    """Same shape as NestJS `Omit<User, 'password'>` with its usual includes."""
    payload: dict[str, Any] = {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "isActive": bool(u.isActive),
        "cpf": u.cpf,
        "phone": u.phone,
        "createdAt": _iso(u.createdAt),
        "updatedAt": _iso(u.updatedAt),
    }
    if include_profile:
        payload["profile"] = serialize_user_profile(getattr(u, "profile", None))
    if include_franchisor_profile:
        payload["franchisorProfile"] = serialize_franchisor_profile(
            getattr(u, "franchisor_profile", None)
        )
    if include_franchisees:
        franchisees = getattr(u, "franchises_as_franchisee", []) or []
        payload["franchiseeOf"] = [serialize_franchisee_summary(f) for f in franchisees]
    return payload


def serialize_franchisor_request(
    r: FranchisorRequest,
    *,
    include_reviewer: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": r.id,
        "userId": r.userId,
        "streamName": r.streamName,
        "mode": r.mode,
        "franchiseId": r.franchiseId,
        "claimReason": r.claimReason,
        "hubspotCompanyId": r.hubspotCompanyId,
        "status": r.status,
        "rejectionReason": r.rejectionReason,
        "reviewedBy": r.reviewedBy,
        "reviewedAt": _iso(r.reviewedAt),
        "createdAt": _iso(r.createdAt),
        "updatedAt": _iso(r.updatedAt),
    }
    if include_reviewer and getattr(r, "user", None) is not None:
        data["user"] = {
            "id": r.user.id,
            "name": r.user.name,
            "email": r.user.email,
        }
    if getattr(r, "franchise", None) is not None:
        data["franchise"] = {
            "id": r.franchise.id,
            "name": r.franchise.name,
            "logoUrl": getattr(r.franchise, "logoUrl", None),
            "status": r.franchise.status,
        }
    return data
