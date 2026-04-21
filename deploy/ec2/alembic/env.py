"""Alembic environment — Mercado Franquia backend.

Conecta-se ao Postgres via DATABASE_URL (mesma var que o app usa).
Usa Base.metadata de app.models como target para autogenerate.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Garante que `app` é importável (alembic roda a partir de deploy/ec2/)
BASE_DIR = Path(__file__).resolve().parent.parent  # deploy/ec2/
sys.path.insert(0, str(BASE_DIR))

from app.models import Base  # noqa: E402

# Alembic config object (lê alembic.ini)
config = context.config

# Injeta DATABASE_URL (env var > alembic.ini)
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError(
        "DATABASE_URL não definida. Exporte no shell antes de rodar alembic.\n"
        "Ex: export DATABASE_URL='postgresql+psycopg://mf_user:dev_password_local@localhost:5432/mercadofranquia'"
    )
config.set_main_option("sqlalchemy.url", db_url)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata pro autogenerate
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Ignora tabelas legadas do Prisma que não estão nos models.

    Isso evita que autogenerate tente dropar tabelas válidas que existem no
    banco mas não foram portadas pro SQLAlchemy (ex: _prisma_migrations).
    """
    # Ignora tabelas legadas do Prisma
    if type_ == "table" and name.startswith("_prisma"):
        return False
    return True


def run_migrations_offline() -> None:
    """Gera SQL sem conectar ao banco (útil pra revisar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Conecta ao banco e aplica migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
