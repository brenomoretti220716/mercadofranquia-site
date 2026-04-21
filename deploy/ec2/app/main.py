"""
Mercado Franquia — FastAPI entry point.

Routes are mounted at bare paths (`/franchises`, `/ranking`, `/health`).
Nginx adds the external `/api/` prefix (see `deploy/ec2/mercadofranquia.nginx`),
so the public URLs are `/api/franchises`, `/api/ranking`, `/api/health`.

Env:
    DATABASE_URL    postgresql+psycopg://mf_user:...@localhost:5432/mercadofranquia
    CORS_ORIGINS    Comma-separated origins allowed to call the API
                    (default: "*"). Example:
                    "https://mercadofranquia.vercel.app,https://mercadofranquia.com.br"
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db import engine
from app.routers import (
    abf_segments,
    auth,
    big_numbers,
    business_models,
    favorites,
    fontes,
    franchises,
    franchisor_requests,
    news,
    notifications,
    quiz,
    ranking,
    register,
    reviews,
    scraping,
    statistics,
    users,
)


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="Mercado Franquia API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(register.router)
app.include_router(users.router)
app.include_router(users.admin_router)
app.include_router(franchisor_requests.router)
app.include_router(franchisor_requests.admin_router)
app.include_router(franchises.router)
app.include_router(franchises.franchisor_router)
app.include_router(ranking.router)
app.include_router(news.router)
app.include_router(favorites.router)
app.include_router(reviews.router)
app.include_router(quiz.router)
app.include_router(notifications.router)
app.include_router(business_models.router)
app.include_router(abf_segments.router)
app.include_router(big_numbers.router)
app.include_router(statistics.router)
app.include_router(scraping.router)
app.include_router(fontes.router)


@app.get("/health", summary="Liveness + DB connectivity check", tags=["meta"])
def health() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index() -> dict[str, str]:
    return {"service": "mercadofranquia-api", "docs": "/docs"}
