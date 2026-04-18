#!/usr/bin/env python3
"""
One-shot ETL: SQLite (pipeline abf.db) → PostgreSQL (mf_user @ EC2 local).

Ports ~10k rows across 9 tables. Idempotent — every INSERT uses the table's
UniqueConstraint as the ON CONFLICT key, so reruns update-in-place instead
of duplicating.

Skipped on purpose:
  - SegmentAcronym  (already seeded via scripts/seed_segment_acronyms.py)
  - MacroSyncLog    (operational log from the local pipeline, not useful)

Also dropped at column level:
  - SQLite `id`                 (PG autoincrements its own)
  - SQLite `relatorio_id`       (FK fantasma — killed in Sessão 2)
  - SQLite `created_at`/
    `updated_at`                (PG server_default fills these at insert time)

Usage (on EC2 inside the venv):
    python scripts/migrate_sqlite_to_pg.py
    python scripts/migrate_sqlite_to_pg.py --dry-run
    python scripts/migrate_sqlite_to_pg.py --sqlite-path /tmp/abf.db

Env:
    DATABASE_URL   postgresql://mf_user:...@localhost:5432/mercadofranquia
                   (auto-strips the SQLAlchemy `+psycopg` driver suffix so
                   the same URL used by systemd mf-api works here too)
"""
from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
import time
from typing import Any, Sequence

try:
    import psycopg
except ImportError:
    sys.exit("Missing dependency: pip install 'psycopg[binary]>=3.1'")


DEFAULT_SQLITE_PATH = "/home/ubuntu/abf.db"
DEFAULT_DB_URL = "postgresql://mf_user:mf_senha_forte_2026@localhost:5432/mercadofranquia"
BATCH_SIZE = 500

logger = logging.getLogger("migrate")


# ---------------------------------------------------------------------------
# Migration map
#
# Tuple layout:
#   (sqlite_table, pg_table, conflict_pg_cols, [(sqlite_col, pg_col), ...])
#
# Column lists are ordered and mirror the PG UniqueConstraint in models.py
# (lines 942-1254). Columns omitted here (id, relatorio_id, created_at,
# updated_at) either auto-generate on the PG side or were dropped from the
# schema entirely.
# ---------------------------------------------------------------------------

TABLES: list[tuple[str, str, list[str], list[tuple[str, str]]]] = [
    (
        "relatorios", "AbfReport", ["periodo"],
        [
            ("periodo",    "periodo"),
            ("ano",        "ano"),
            ("trimestre",  "trimestre"),
            ("tipo",       "tipo"),
            ("arquivo",    "arquivo"),
            ("status",     "status"),
            ("notas",      "notas"),
        ],
    ),
    (
        "faturamento", "AbfRevenue", ["periodo", "segmento", "tipoDado"],
        [
            ("periodo",    "periodo"),
            ("segmento",   "segmento"),
            ("valor_mm",   "valorMm"),
            ("tipo_dado",  "tipoDado"),
        ],
    ),
    (
        "indicadores", "AbfIndicator", ["periodo"],
        [
            ("periodo",              "periodo"),
            ("empregos_diretos",     "empregosDiretos"),
            ("num_redes",            "numRedes"),
            ("num_unidades",         "numUnidades"),
            ("ticket_medio",         "ticketMedio"),
            ("var_empregos_pct",     "varEmpregosPct"),
            ("var_redes_pct",        "varRedesPct"),
            ("var_unidades_pct",     "varUnidadesPct"),
            ("empregos_por_unidade", "empregosPorUnidade"),
        ],
    ),
    (
        "ranking", "AbfUnitsRanking", ["ano", "posicao"],
        [
            ("ano",          "ano"),
            ("posicao",      "posicao"),
            ("posicao_ant",  "posicaoAnt"),
            ("marca",        "marca"),
            ("segmento",     "segmento"),
            ("unidades",     "unidades"),
            ("unidades_ant", "unidadesAnt"),
            ("var_pct",      "varPct"),
        ],
    ),
    (
        "projecoes", "AbfProjection", ["anoReferencia"],
        [
            ("ano_referencia",    "anoReferencia"),
            ("fat_var_min_pct",   "fatVarMinPct"),
            ("fat_var_max_pct",   "fatVarMaxPct"),
            ("fat_realizado_pct", "fatRealizadoPct"),
            ("redes_var_pct",     "redesVarPct"),
            ("unidades_var_pct",  "unidadesVarPct"),
            ("empregos_var_pct",  "empregosVarPct"),
        ],
    ),
    (
        "macro_bcb", "MacroBcb", ["data", "codigoSerie"],
        [
            ("data",         "data"),
            ("codigo_serie", "codigoSerie"),
            ("nome_serie",   "nomeSerie"),
            ("valor",        "valor"),
            ("fonte",        "fonte"),
        ],
    ),
    (
        "macro_ibge", "MacroIbge", ["data", "codigoAgregado", "variavel", "localidade"],
        [
            ("data",            "data"),
            ("codigo_agregado", "codigoAgregado"),
            ("variavel",        "variavel"),
            ("localidade",      "localidade"),
            ("valor",           "valor"),
            ("fonte",           "fonte"),
        ],
    ),
    (
        "pmc_ibge", "PmcIbge", ["data", "codigoSegmento"],
        [
            ("data",            "data"),
            ("codigo_segmento", "codigoSegmento"),
            ("nome_segmento",   "nomeSegmento"),
            ("variacao_mensal", "variacaoMensal"),
            ("variacao_anual",  "variacaoAnual"),
            ("indice",          "indice"),
            ("fonte",           "fonte"),
            ("url_fonte",       "urlFonte"),
            ("data_coleta",     "dataColeta"),
        ],
    ),
    (
        "caged_bcb", "CagedBcb", ["data", "codigoBcb"],
        [
            ("data",        "data"),
            ("estoque",     "estoque"),
            ("saldo",       "saldo"),
            ("setor",       "setor"),
            ("codigo_bcb",  "codigoBcb"),
            ("fonte",       "fonte"),
            ("url_fonte",   "urlFonte"),
            ("data_coleta", "dataColeta"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_db_url(url: str) -> str:
    """Strip SQLAlchemy driver suffix so psycopg3 accepts the URL.

    systemd's mf-api.service hands DATABASE_URL as
    `postgresql+psycopg://...` (SQLAlchemy flavor). psycopg3 parses bare
    `postgresql://...` only, so peel the prefix if present.
    """
    prefix = "postgresql+psycopg://"
    if url.startswith(prefix):
        return "postgresql://" + url[len(prefix):]
    return url


def _build_upsert_sql(pg_table: str, pg_cols: Sequence[str],
                      conflict_cols: Sequence[str]) -> str:
    """Compose an INSERT ... ON CONFLICT DO UPDATE for one target table.

    All identifiers are double-quoted to survive camelCase columns
    (codigoSerie, valorMm, tipoDado, …). If every column is in the
    conflict key (no non-key cols to update), fall back to DO NOTHING.
    """
    col_list    = ", ".join(f'"{c}"' for c in pg_cols)
    placeholder = ", ".join(["%s"] * len(pg_cols))
    conflict    = ", ".join(f'"{c}"' for c in conflict_cols)
    update_cols = [c for c in pg_cols if c not in conflict_cols]

    if update_cols:
        update_sql = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
        action = f"DO UPDATE SET {update_sql}"
    else:
        action = "DO NOTHING"

    return (
        f'INSERT INTO "{pg_table}" ({col_list}) VALUES ({placeholder}) '
        f'ON CONFLICT ({conflict}) {action}'
    )


def _preflight(sqlite_path: str, pg_conn: "psycopg.Connection") -> None:
    """Fail loudly before any writes if inputs are missing."""
    if not os.path.isfile(sqlite_path):
        sys.exit(f"SQLite file not found: {sqlite_path}")

    expected = [pg for _, pg, *_ in TABLES]
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename = ANY(%s)
            """,
            (expected,),
        )
        found = {row[0] for row in cur.fetchall()}
    missing = [t for t in expected if t not in found]
    if missing:
        sys.exit(f"Missing Postgres tables (run alembic upgrade head first): {missing}")


def _migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: "psycopg.Connection",
    sqlite_table: str,
    pg_table: str,
    conflict_cols: Sequence[str],
    col_map: Sequence[tuple[str, str]],
    dry_run: bool,
) -> tuple[int, int]:
    """UPSERT one table end-to-end. Returns (rows_read, rows_upserted)."""
    t0 = time.monotonic()
    sqlite_cols = [s for s, _ in col_map]
    pg_cols     = [p for _, p in col_map]

    select_sql = f'SELECT {", ".join(sqlite_cols)} FROM {sqlite_table}'
    upsert_sql = _build_upsert_sql(pg_table, pg_cols, conflict_cols)

    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute(select_sql)

    read = upserted = 0
    batch: list[tuple[Any, ...]] = []

    with pg_conn.cursor() as pg_cur:
        for row in sqlite_cur:
            read += 1
            batch.append(tuple(row))
            if len(batch) >= BATCH_SIZE:
                upserted += _flush(pg_cur, pg_conn, upsert_sql, batch, dry_run)
                batch = []
        if batch:
            upserted += _flush(pg_cur, pg_conn, upsert_sql, batch, dry_run)

    elapsed = time.monotonic() - t0
    logger.info(
        "%s: %d linhas lidas, %d upserted, 0 erros, %.1fs",
        pg_table, read, upserted, elapsed,
    )
    return read, upserted


def _flush(
    pg_cur: "psycopg.Cursor",
    pg_conn: "psycopg.Connection",
    upsert_sql: str,
    batch: list[tuple[Any, ...]],
    dry_run: bool,
) -> int:
    """Send one batch. Commit only on real runs — dry-run accumulates in the
    enclosing transaction and relies on the caller to ROLLBACK at the end."""
    pg_cur.executemany(upsert_sql, batch)
    if not dry_run:
        pg_conn.commit()
    return len(batch)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-shot SQLite→Postgres migration for the mercadofranquia pipeline."
    )
    parser.add_argument(
        "--sqlite-path", default=DEFAULT_SQLITE_PATH,
        help=f"SQLite file to read (default: {DEFAULT_SQLITE_PATH})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run all UPSERTs in a transaction and ROLLBACK at the end.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    db_url = _normalize_db_url(os.environ.get("DATABASE_URL", DEFAULT_DB_URL))
    logger.info("SQLite: %s", args.sqlite_path)
    logger.info("Postgres host: %s", db_url.rsplit("@", 1)[-1])
    if args.dry_run:
        logger.info("DRY RUN — no changes will be committed")

    sqlite_conn = sqlite3.connect(args.sqlite_path)

    total_read = total_upserted = 0
    try:
        with psycopg.connect(db_url, autocommit=False) as pg_conn:
            _preflight(args.sqlite_path, pg_conn)

            for sqlite_t, pg_t, conflict, col_map in TABLES:
                r, u = _migrate_table(
                    sqlite_conn, pg_conn,
                    sqlite_t, pg_t, conflict, col_map,
                    args.dry_run,
                )
                total_read     += r
                total_upserted += u

            logger.info("Contagem final por tabela:")
            with pg_conn.cursor() as cur:
                for _, pg_t, *_ in TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{pg_t}"')
                    n = cur.fetchone()[0]
                    logger.info("  %s: %d", pg_t, n)

            if args.dry_run:
                pg_conn.rollback()
                logger.info("Rolled back (dry-run).")
    finally:
        sqlite_conn.close()

    logger.info(
        "Done. Total: %d linhas lidas, %d upserted.",
        total_read, total_upserted,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
