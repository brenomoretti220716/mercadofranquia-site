"""Database engine & session factory.

`DATABASE_URL` should use the `postgresql+psycopg://` scheme (psycopg 3).
"""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://mf_user:mf_senha_forte_2026@localhost:5432/mercadofranquia",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
