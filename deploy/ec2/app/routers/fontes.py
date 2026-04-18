"""
Central de Fontes — admin read-only status panel.

Aggregates the live state of every macro data source the EC2 pipeline
feeds (9 BCB series + 2 IBGE aggregates + 1 PMC aggregate + 6 CAGED),
plus the list of ABF reports already ingested. Backs the /admin/fontes
screen (Fase 1A da fusão Intelligence → Site).

Source-of-truth for series codes and names: app.services.macro_sync
(the same dicts the systemd timer uses). Don't duplicate.

Endpoint:
    GET /fontes/admin/status   require_role("ADMIN")
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AbfReport,
    CagedBcb,
    MacroBcb,
    MacroIbge,
    MacroSyncLog,
    PmcIbge,
)
from app.security import JwtPayload, require_role
from app.services.macro_sync import (
    ENDPOINTS_IBGE,
    SERIES_BCB,
    SERIES_CAGED,
)

router = APIRouter(prefix="/fontes", tags=["fontes"])
logger = logging.getLogger("mf-api.fontes")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _latest_logs_by_fonte(db: Session) -> dict[str, MacroSyncLog]:
    """Return the single most recent MacroSyncLog row per `fonte` string.

    Classic "latest per group": MAX(createdAt) subquery joined back to the
    full row so status/duracaoMs aren't collapsed to aggregates. Runs on
    the existing (fonte, createdAt) index — no table scan.

    Rationale (see spec): status/daysSince MUST come from the latest log
    row, NEVER from MAX(data) on the data tables. ultimo_registro is only
    informational — it doesn't feed the status pill.
    """
    latest_ts = (
        select(
            MacroSyncLog.fonte.label("fonte"),
            func.max(MacroSyncLog.createdAt).label("max_ts"),
        )
        .group_by(MacroSyncLog.fonte)
        .subquery()
    )
    rows = db.execute(
        select(MacroSyncLog).join(
            latest_ts,
            (MacroSyncLog.fonte == latest_ts.c.fonte)
            & (MacroSyncLog.createdAt == latest_ts.c.max_ts),
        )
    ).scalars().all()
    return {row.fonte: row for row in rows}


def _build_row(
    *,
    codigo: str,
    nome: str,
    fonte: str,
    tabela: str,
    total: int,
    ultimo_registro: Optional[str],
    log: Optional[MacroSyncLog],
) -> dict[str, Any]:
    """Assemble one macro source row.

    sync_status = 'nunca' when there's no log entry at all for this fonte
    (macro_sync has never run or never logged it). Frontend paints NUNCA
    the same red as ERRO but with a distinct label.
    """
    if log is None:
        sync_status = "nunca"
        ultima_sync: Optional[str] = None
        duracao_ms: Optional[int] = None
        registros_inseridos: Optional[int] = None
    else:
        sync_status = log.status
        ultima_sync = _iso(log.createdAt)
        duracao_ms = log.duracaoMs
        registros_inseridos = log.registrosInseridos

    return {
        "codigo": codigo,
        "nome": nome,
        "fonte": fonte,
        "tabela": tabela,
        "total": total or 0,
        "ultimo_registro": ultimo_registro,
        "ultima_sync": ultima_sync,
        "sync_status": sync_status,
        "duracao_ms": duracao_ms,
        "registros_inseridos": registros_inseridos,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/admin/status", summary="Consolidated source status (admin)")
def get_status(
    _admin: JwtPayload = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    """18 macro sources (9 BCB + 2 IBGE + 1 PMC + 6 CAGED) + AbfReport list."""

    # --- Aggregated stats, one GROUP BY query per data table ----------------
    bcb_stats: dict[int, tuple[int, Optional[str]]] = {
        row.codigo: (row.total, row.ultimo)
        for row in db.execute(
            select(
                MacroBcb.codigoSerie.label("codigo"),
                func.count().label("total"),
                func.max(MacroBcb.data).label("ultimo"),
            ).group_by(MacroBcb.codigoSerie)
        )
    }

    ibge_stats: dict[int, tuple[int, Optional[str]]] = {
        row.codigo: (row.total, row.ultimo)
        for row in db.execute(
            select(
                MacroIbge.codigoAgregado.label("codigo"),
                func.count().label("total"),
                func.max(MacroIbge.data).label("ultimo"),
            ).group_by(MacroIbge.codigoAgregado)
        )
    }

    # PmcIbge is reported as a single aggregated row ("8882 — todos segmentos")
    pmc_total, pmc_ultimo = db.execute(
        select(func.count(), func.max(PmcIbge.data))
    ).one()

    caged_stats: dict[int, tuple[int, Optional[str]]] = {
        row.codigo: (row.total, row.ultimo)
        for row in db.execute(
            select(
                CagedBcb.codigoBcb.label("codigo"),
                func.count().label("total"),
                func.max(CagedBcb.data).label("ultimo"),
            ).group_by(CagedBcb.codigoBcb)
        )
    }

    log_by_fonte = _latest_logs_by_fonte(db)

    # --- 18 macro sources, in the same order macro_sync.py runs them --------
    macro: list[dict[str, Any]] = []

    # 9 BCB macro series
    for codigo, nome in SERIES_BCB.items():
        fonte_key = f"BCB/{nome} ({codigo})"
        total, ultimo = bcb_stats.get(codigo, (0, None))
        macro.append(_build_row(
            codigo=str(codigo),
            nome=f"{nome} (série {codigo})",
            fonte="BCB",
            tabela="MacroBcb",
            total=total,
            ultimo_registro=ultimo,
            log=log_by_fonte.get(fonte_key),
        ))

    # 2 IBGE aggregates (5938 PIB estadual, 8881 PMC varejo nacional)
    for endpoint in ENDPOINTS_IBGE:
        codigo = endpoint["codigo_agregado"]
        nome = endpoint["nome"]
        fonte_key = f"IBGE/{nome} ({codigo})"
        total, ultimo = ibge_stats.get(codigo, (0, None))
        macro.append(_build_row(
            codigo=str(codigo),
            nome=f"{nome} (agregado {codigo})",
            fonte="IBGE",
            tabela="MacroIbge",
            total=total,
            ultimo_registro=ultimo,
            log=log_by_fonte.get(fonte_key),
        ))

    # 1 PMC aggregated (multi-segmento, single row in the UI)
    macro.append(_build_row(
        codigo="8882",
        nome="PMC por segmento (todos)",
        fonte="IBGE",
        tabela="PmcIbge",
        total=pmc_total or 0,
        ultimo_registro=pmc_ultimo,
        log=log_by_fonte.get("IBGE/PMC (8882)"),
    ))

    # 6 CAGED series
    for codigo, setor in SERIES_CAGED.items():
        fonte_key = f"BCB/CAGED {setor} ({codigo})"
        total, ultimo = caged_stats.get(codigo, (0, None))
        macro.append(_build_row(
            codigo=str(codigo),
            nome=f"CAGED {setor} (série {codigo})",
            fonte="BCB",
            tabela="CagedBcb",
            total=total,
            ultimo_registro=ultimo,
            log=log_by_fonte.get(fonte_key),
        ))

    # --- AbfReport list -----------------------------------------------------
    abf_rows = db.execute(
        select(AbfReport).order_by(
            AbfReport.ano.desc(),
            AbfReport.trimestre.desc().nullslast(),
        )
    ).scalars().all()
    abf = [
        {
            "periodo": r.periodo,
            "ano": r.ano,
            "trimestre": r.trimestre,
            "status": r.status,
            "created_at": _iso(r.createdAt),
        }
        for r in abf_rows
    ]

    return {"macro": macro, "abf": abf}
