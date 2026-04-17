"""
Scraping admin endpoints — STUBS.

The NestJS scraping module relies on a Puppeteer browser pool, two HTML
scrapers (new + old layout), a sitemap parser, an image processor, and a
CSV-driven persistence pipeline (~1500 LOC across 10+ files). Porting it
to Python would require Playwright + a browser pool and is out of scope
for the current admin-port effort.

For now both endpoints respond 200 with the NestJS response shape and a
single error explaining that scraping is not available in this deployment.
The frontend treats `success == 0` as a failed run and surfaces the message.

When scraping is actually ported, replace the stub bodies with the real
Puppeteer/Playwright pipeline.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Franchise
from app.security import JwtPayload, require_role

router = APIRouter(prefix="/scraping", tags=["scraping"])
logger = logging.getLogger("mf-api.scraping")

_STUB_REASON = (
    "Scraping não está disponível neste deployment do FastAPI. "
    "Infraestrutura de browser headless (Puppeteer/Playwright) ainda não foi portada. "
    "Acionar o backend NestJS legado ou portar o módulo de scraping."
)


class SyncFranchiseImagesBody(BaseModel):
    franchiseIds: Optional[list[str]] = None
    force: Optional[bool] = None
    concurrency: Optional[int] = None


@router.patch(
    "/{franchise_id}",
    summary="Update franchise via scraping (STUB — não implementado)",
)
def update_franchise_by_scraping(
    franchise_id: str,
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Mirrors NestJS ImportResultType: { total, success, failed, errors[] }.
    # Frontend reads `success` to decide if the run was OK; we report 0/0/1
    # so the admin UI shows the explanation instead of a misleading success.
    franchise_exists = (
        db.scalar(select(Franchise.id).where(Franchise.id == franchise_id)) is not None
    )

    logger.warning(
        "[update_franchise_by_scraping] STUB call — franchise=%s exists=%s",
        franchise_id, franchise_exists,
    )

    error_payload = {
        "row": 1,
        "data": {"franchiseId": franchise_id},
        "error": _STUB_REASON,
    }
    return {
        "total": 1,
        "success": 0,
        "failed": 1,
        "errors": [error_payload],
    }


@router.post(
    "/franchises/images/sync",
    summary="Sync franchise images via scraping (STUB — não implementado)",
    status_code=status.HTTP_200_OK,
)
def sync_franchise_images(
    body: SyncFranchiseImagesBody = Body(default_factory=SyncFranchiseImagesBody),
    _admin: JwtPayload = Depends(require_role("ADMIN")),
) -> dict[str, Any]:
    # Mirrors NestJS FranchiseImagesSyncResult:
    #   { processed, updated, skipped, errors: [{franchiseId, scrapedWebsite, error}] }
    target_count = len(body.franchiseIds) if body.franchiseIds else 0

    logger.warning(
        "[sync_franchise_images] STUB call — franchiseIds=%s force=%s concurrency=%s",
        body.franchiseIds, body.force, body.concurrency,
    )

    return {
        "processed": 0,
        "updated": 0,
        "skipped": target_count,
        "errors": [
            {
                "franchiseId": "*",
                "scrapedWebsite": "",
                "error": _STUB_REASON,
            }
        ],
    }
