"""
Platform statistics — single summary record used by the home hero.

    GET /statistics   { franchisesReviewed, totalReviews, totalSegments, medianRating }

Falls back to live-computed values when the singleton row is absent, mirroring
the NestJS `StatisticsService.getStatistics` behavior (minus the Redis cache).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Franchise, PlatformStatistics, Review

router = APIRouter(prefix="/statistics", tags=["statistics"])


def _compute_live(db: Session) -> dict[str, Any]:
    franchises_reviewed = db.scalar(
        select(func.count(distinct(Review.franchiseId))).where(Review.isActive.is_(True))
    ) or 0
    total_reviews = db.scalar(
        select(func.count(Review.id)).where(Review.isActive.is_(True))
    ) or 0
    total_segments = db.scalar(
        select(func.count(distinct(Franchise.segment))).where(
            Franchise.isActive.is_(True), Franchise.segment.isnot(None)
        )
    ) or 0
    # Median rating of franchises that have at least one review.
    ratings = db.scalars(
        select(Franchise.averageRating).where(
            Franchise.isActive.is_(True),
            Franchise.averageRating.isnot(None),
            Franchise.reviewCount > 0,
        )
    ).all()
    median = None
    ratings = [r for r in ratings if r is not None]
    if ratings:
        ratings.sort()
        n = len(ratings)
        mid = n // 2
        median = ratings[mid] if n % 2 == 1 else (ratings[mid - 1] + ratings[mid]) / 2
    return {
        "franchisesReviewed": franchises_reviewed,
        "totalReviews": total_reviews,
        "totalSegments": total_segments,
        "medianRating": median,
    }


@router.get("", summary="Platform statistics")
def get_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    record = db.scalar(
        select(PlatformStatistics).where(PlatformStatistics.id == 1)
    )
    if record is not None:
        return {
            "franchisesReviewed": record.franchisesReviewed,
            "totalReviews": record.totalReviews,
            "totalSegments": record.totalSegments,
            "medianRating": record.medianRating,
        }
    return _compute_live(db)
