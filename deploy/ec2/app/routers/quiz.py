"""
Quiz endpoints — all require auth.

    GET  /quiz            metadata of the user's submission (or null)
    POST /quiz            submit or update answers (upsert)
    GET  /quiz/profile    selected answer summary for display
    GET  /quiz/results    blocks of ranked franchises by fit

The scoring here is a **simplified** port of the NestJS `QuizScoringService`:
it filters by investment zones and preferred segments, then scores on 5
dimensions (segment, investment, payback, revenue, network) with equal
weights. Not feature-parity with the production algorithm — enough to give
plausible results while the upstream algorithm isn't ported. See
`README.md` → "Quiz scoring caveat".
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Franchise, QuizSubmission
from app.security import JwtPayload, get_current_user

router = APIRouter(prefix="/quiz", tags=["quiz"])


# ---------------------------------------------------------------------------
# Answer schema — mirrors QuizAnswersDto loosely. Extra keys are preserved.
# ---------------------------------------------------------------------------

class QuizAnswersBody(BaseModel):
    model_config = {"extra": "allow"}

    q20AvailableCapital: Optional[str] = None  # e.g. "100000-300000"
    q23DesiredMonthlyWithdrawal: Optional[str] = None
    q24ExpectedPayback: Optional[str] = None  # e.g. "24-36_months"
    q3PreferredSegments: Optional[list[str]] = None
    q4PreferredSubsegments: Optional[list[str]] = None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _submission_meta(s: QuizSubmission) -> dict[str, Any]:
    return {
        "id": s.id,
        "userId": s.userId,
        "createdAt": _iso(s.createdAt),
        "updatedAt": _iso(s.updatedAt),
    }


# ---------------------------------------------------------------------------
# GET /quiz  — user's current submission (metadata only)
# ---------------------------------------------------------------------------

@router.get("", summary="Obter quiz do usuário (ou null)")
def get_my_quiz(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[dict[str, Any]]:
    sub = db.scalar(select(QuizSubmission).where(QuizSubmission.userId == current.id))
    if sub is None:
        return None
    return _submission_meta(sub)


# ---------------------------------------------------------------------------
# POST /quiz  — upsert
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED, summary="Enviar / atualizar quiz")
def submit_quiz(
    body: QuizAnswersBody,
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = json.dumps(body.model_dump())
    existing = db.scalar(
        select(QuizSubmission).where(QuizSubmission.userId == current.id)
    )
    if existing is None:
        sub = QuizSubmission(
            id=uuid.uuid4().hex,
            userId=current.id,
            answers=payload,
        )
        db.add(sub)
    else:
        existing.answers = payload
        sub = existing
    db.commit()
    db.refresh(sub)
    return _submission_meta(sub)


# ---------------------------------------------------------------------------
# GET /quiz/profile
# ---------------------------------------------------------------------------

PROFILE_KEYS: list[tuple[str, str, str]] = [
    ("availableCapital", "Capital disponível", "q20AvailableCapital"),
    ("desiredMonthlyWithdrawal", "Retirada mensal desejada", "q23DesiredMonthlyWithdrawal"),
    ("expectedPayback", "Payback esperado", "q24ExpectedPayback"),
    ("preferredSegments", "Segmentos de interesse", "q3PreferredSegments"),
    ("preferredSubsegments", "Subsegmentos de interesse", "q4PreferredSubsegments"),
]


@router.get("/profile", summary="Resumo do perfil do quiz")
def get_profile(
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    sub = db.scalar(select(QuizSubmission).where(QuizSubmission.userId == current.id))
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum quiz encontrado para o usuário informado.",
        )
    try:
        answers = json.loads(sub.answers or "{}")
    except json.JSONDecodeError:
        answers = {}

    def _display(val: Any) -> Any:
        if isinstance(val, list):
            return ", ".join(str(x) for x in val)
        return val

    return {
        "answers": [
            {"key": k, "label": label, "value": _display(answers.get(source))}
            for (k, label, source) in PROFILE_KEYS
        ]
    }


# ---------------------------------------------------------------------------
# GET /quiz/results — simplified scoring
# ---------------------------------------------------------------------------

# "<min>-<max>" strings like "100000-300000" or "500000+" mapped to numeric ranges.
def _parse_money_range(s: Optional[str]) -> tuple[float, Optional[float]]:
    if not s:
        return (0.0, None)
    s = s.strip()
    if s.endswith("+"):
        try:
            return (float(s[:-1]), None)
        except ValueError:
            return (0.0, None)
    parts = s.split("-")
    try:
        lo = float(parts[0])
        hi = float(parts[1]) if len(parts) > 1 else None
    except ValueError:
        return (0.0, None)
    return (lo, hi)


def _score_franchise(answers: dict[str, Any], f: Franchise) -> dict[str, Any]:
    """Return a score dict matching the NestJS shape (zone + components + final)."""
    # Investment compatibility — which zone?
    avail_lo, avail_hi = _parse_money_range(answers.get("q20AvailableCapital"))
    franchise_min = float(f.minimumInvestment) if f.minimumInvestment is not None else 0.0

    if avail_hi is None:
        avail_hi = max(avail_lo * 3, franchise_min * 3, 999_999_999)

    if franchise_min <= avail_hi:
        zone = "ZONE_1"
        inv_score = 1.0
    elif franchise_min <= avail_hi * 1.5:
        zone = "ZONE_2"
        inv_score = 0.6
    else:
        zone = "ZONE_3"
        inv_score = 0.2

    # Segment match
    prefs = answers.get("q3PreferredSegments") or []
    segment_score = (
        1.0
        if f.segment and any(p and p.lower() in f.segment.lower() for p in prefs)
        else (0.3 if not prefs else 0.1)
    )

    # Payback / revenue / network — proxies with basic proportional scoring.
    revenue_score = min(
        1.0, float(f.averageMonthlyRevenue or 0) / 500_000.0
    )
    network_score = min(1.0, (f.totalUnits or 0) / 500.0)
    payback_score = min(
        1.0,
        1.0 / max(1, (f.minimumReturnOnInvestment or 36)) * 36,
    )

    final_score = (
        segment_score * 0.30
        + inv_score * 0.30
        + payback_score * 0.15
        + revenue_score * 0.15
        + network_score * 0.10
    )
    confidence = 0.6 if prefs else 0.4

    return {
        "segmentScore": round(segment_score, 4),
        "investmentScore": round(inv_score, 4),
        "paybackScore": round(payback_score, 4),
        "revenueScore": round(revenue_score, 4),
        "networkScore": round(network_score, 4),
        "zone": zone,
        "confidence": confidence,
        "finalScore": round(final_score, 4),
    }


def _franchise_for_results(f: Franchise, score: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f.id,
        "slug": f.slug,
        "name": f.name,
        "segment": f.segment,
        "subsegment": f.subsegment,
        "minimumInvestment": float(f.minimumInvestment) if f.minimumInvestment is not None else None,
        "maximumInvestment": float(f.maximumInvestment) if f.maximumInvestment is not None else None,
        "averageMonthlyRevenue": float(f.averageMonthlyRevenue) if f.averageMonthlyRevenue is not None else None,
        "totalUnits": f.totalUnits,
        "logoUrl": f.logoUrl,
        "score": score,
    }


MAX_PER_ZONE = 200


def _paginate(items: list, page: int, page_size: int) -> tuple[list, dict[str, Any]]:
    limited = items[:MAX_PER_ZONE]
    total = len(limited)
    size = page_size if page_size > 0 else 10
    total_pages = 1 if total == 0 else ceil(total / size)
    current = 1 if page < 1 else min(page, total_pages)
    start = (current - 1) * size
    return limited[start : start + size], {
        "total": total,
        "page": current,
        "pageSize": size,
        "totalPages": total_pages,
    }


@router.get("/results", summary="Resultados ranqueados do quiz")
def get_results(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    current: JwtPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    sub = db.scalar(select(QuizSubmission).where(QuizSubmission.userId == current.id))
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum quiz encontrado para o usuário informado.",
        )
    try:
        answers = json.loads(sub.answers or "{}")
    except json.JSONDecodeError:
        answers = {}

    franchises = db.scalars(
        select(Franchise).where(Franchise.isActive.is_(True), Franchise.slug.isnot(None))
    ).all()

    scored = [(_score_franchise(answers, f), f) for f in franchises]

    zone1 = [(s, f) for (s, f) in scored if s["zone"] == "ZONE_1"]
    zone2 = [(s, f) for (s, f) in scored if s["zone"] == "ZONE_2"]
    zone3 = [(s, f) for (s, f) in scored if s["zone"] == "ZONE_3"]
    for z in (zone1, zone2, zone3):
        z.sort(key=lambda sf: sf[0]["finalScore"], reverse=True)

    # Fallback: if Zone 1 & 2 both empty, promote Zone 3 into the second block.
    final_zone1 = zone1
    final_zone2 = zone2
    if len(final_zone1) == 0 and len(final_zone2) == 0 and len(zone3) > 0:
        final_zone2 = zone3

    z1_items, z1_pag = _paginate(final_zone1, page, pageSize)
    z2_items, z2_pag = _paginate(final_zone2, page, pageSize)

    return {
        "hasSubmission": True,
        "blocks": [
            {
                "label": "mais_compativeis",
                "zone": "ZONE_1",
                "pagination": z1_pag,
                "franchises": [_franchise_for_results(f, s) for (s, f) in z1_items],
            },
            {
                "label": "proximas_do_seu_perfil",
                "zone": "ZONE_2",
                "pagination": z2_pag,
                "franchises": [_franchise_for_results(f, s) for (s, f) in z2_items],
            },
        ],
    }
