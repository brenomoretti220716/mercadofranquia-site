"""
Macro / ABF data sync service.

Ports ~/Developer/mercadofranquia/api/sync.py (416 LOC, SQLite) to
SQLAlchemy + PostgreSQL UPSERT (ON CONFLICT DO UPDATE). Fetches:

  - BCB SGS: 9 macro series + 6 CAGED (emprego formal) series
  - IBGE SIDRA: PIB estadual (5938), PMC varejo (8881)
  - IBGE SIDRA: PMC por segmento (8882) multi-variável

Called daily via scripts/run_macro_sync.py wired to a systemd timer
(Sessão 5 — mf-macro-sync.timer at 03:00 America/Sao_Paulo).

Resilience knobs:
  - 2 retries with (5s, 15s) backoff on URLError/TimeoutError/5xx
  - 4xx raised immediately (404 = series decommissioned, no point retrying)
  - per-URL timeout (CHUNK_TIMEOUT_SEC), not global
  - commit per BATCH_SIZE UPSERT rows
  - duracaoMs recorded in MacroSyncLog for every source
"""
from __future__ import annotations

import gzip
import json
import logging
import ssl
import time
from datetime import datetime
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    CagedBcb,
    MacroBcb,
    MacroIbge,
    MacroSyncLog,
    PmcIbge,
)

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config (mirrors api/sync.py in the pipeline repo)
# ---------------------------------------------------------------------------

SERIES_BCB: dict[int, str] = {
    11:    "Selic",
    433:   "IPCA",
    1:     "USD/BRL",
    4380:  "PIB trimestral",
    24369: "Desemprego",
    4393:  "ICC",
    4395:  "ICE",
    29039: "Endividamento famílias",
    17633: "Massa salarial real",
}

# Daily series are too large for one SGS call since 2014 — split into 3 chunks.
SERIES_DIARIAS: set[int] = {11, 1}
BCB_CHUNKS: list[tuple[str, str]] = [
    ("01/01/2014", "31/12/2017"),
    ("01/01/2018", "31/12/2021"),
    ("01/01/2022", ""),  # empty dataFinal = up to today
]
BCB_CHUNK_UNICO: list[tuple[str, str]] = [("01/01/2014", "")]

SERIES_CAGED: dict[int, str] = {
    28763: "Total",
    28771: "Comércio",
    28772: "Serviços",
    28774: "Alojamento e alimentação",
    28770: "Construção",
    28766: "Indústria de transformação",
}


def _periodos_mensais_ibge(ano_inicio: int = 2014, ano_fim: int | None = None) -> str:
    if ano_fim is None:
        ano_fim = datetime.now().year
    periodos = [
        f"{ano}{mes:02d}"
        for ano in range(ano_inicio, ano_fim + 1)
        for mes in range(1, 13)
    ]
    return "|".join(periodos)


PERIODOS_IBGE = "|".join(str(a) for a in range(2014, datetime.now().year + 1))
PERIODOS_MENSAIS_IBGE = _periodos_mensais_ibge()

ENDPOINTS_IBGE: list[dict[str, Any]] = [
    {
        "nome": "PIB por estado",
        "codigo_agregado": 5938,
        "url": (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/5938"
            f"/periodos/{PERIODOS_IBGE}/variaveis/37?localidades=N3[all]"
        ),
    },
    {
        "nome": "PMC - Varejo",
        "codigo_agregado": 8881,
        "url": (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/8881"
            f"/periodos/{PERIODOS_MENSAIS_IBGE}/variaveis/11709?localidades=N1[all]"
            f"&classificacao=11046[56736]"
        ),
    },
]

CHUNK_TIMEOUT_SEC = 45
RETRY_ATTEMPTS = 2                  # 1 initial + 2 retries = 3 total tries
RETRY_BACKOFF_SEC = (5.0, 15.0)
BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: float = CHUNK_TIMEOUT_SEC) -> Any:
    """Fetch URL; transparently decompress gzip (IBGE ignores Accept-Encoding)."""
    req = Request(url)
    req.add_header("User-Agent", "MercadoFranquia/1.0")
    with urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        raw = resp.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def _fetch_with_retry(url: str) -> Any:
    """Fetch with 2 retries (5s, 15s backoff) on URLError/TimeoutError/5xx.

    HTTPError with 4xx is re-raised immediately — 404 means the BCB/IBGE
    series was decommissioned and retrying can't fix it. The outer caller
    catches the exception, writes to MacroSyncLog, and moves to the next
    series ("loga-e-segue" — matches original sync.py behavior).
    """
    last_exc: BaseException | None = None
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            return _fetch_json(url)
        except HTTPError as e:
            if 400 <= e.code < 500:
                raise
            last_exc = e
        except (URLError, TimeoutError) as e:
            last_exc = e
        if attempt < RETRY_ATTEMPTS:
            delay = RETRY_BACKOFF_SEC[attempt]
            logger.warning(
                "fetch retry %d/%d after %.0fs: %s (%s)",
                attempt + 1, RETRY_ATTEMPTS, delay, url, last_exc,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _data_iso_from_bcb(data_raw: str) -> str:
    """BCB returns dd/mm/aaaa; normalize to aaaa-mm-dd for our VARCHAR(10)."""
    partes = data_raw.split("/")
    if len(partes) == 3:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return data_raw


# ---------------------------------------------------------------------------
# Sync log
# ---------------------------------------------------------------------------

def _log_sync(
    session: Session,
    fonte: str,
    status: str,
    registros: int = 0,
    erro: str | None = None,
    duracao_ms: int = 0,
) -> None:
    session.add(MacroSyncLog(
        fonte=fonte,
        status=status,
        registrosInseridos=registros,
        duracaoMs=duracao_ms,
        erro=erro,
    ))
    session.commit()


# ---------------------------------------------------------------------------
# UPSERT batch helper
# ---------------------------------------------------------------------------

def _upsert_batches(
    session: Session,
    model: Any,
    rows: list[dict[str, Any]],
    conflict_cols: Sequence[str],
    update_cols: Sequence[str],
) -> int:
    """Batch-UPSERT ``rows`` with Postgres ON CONFLICT DO UPDATE.

    Commits every BATCH_SIZE. Returns number of rows processed (before
    conflict resolution — so "N rows sent", not "N rows inserted").
    """
    if not rows:
        return 0
    processed = 0
    for start in range(0, len(rows), BATCH_SIZE):
        chunk = rows[start:start + BATCH_SIZE]
        stmt = pg_insert(model).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=list(conflict_cols),
            set_={c: stmt.excluded[c] for c in update_cols},
        )
        session.execute(stmt)
        session.commit()
        processed += len(chunk)
    return processed


# ---------------------------------------------------------------------------
# BCB macro series
# ---------------------------------------------------------------------------

def sync_bcb(session: Session) -> int:
    """Fetch 9 BCB SGS series and UPSERT into MacroBcb. Returns total rows."""
    total = 0
    for codigo, nome in SERIES_BCB.items():
        fonte = f"BCB/{nome} ({codigo})"
        t0 = time.monotonic()
        chunks = BCB_CHUNKS if codigo in SERIES_DIARIAS else BCB_CHUNK_UNICO
        try:
            dados: list[dict[str, Any]] = []
            for data_ini, data_fim in chunks:
                url = (
                    f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
                    f"/dados?formato=json&dataInicial={data_ini}"
                )
                if data_fim:
                    url += f"&dataFinal={data_fim}"
                dados.extend(_fetch_with_retry(url))

            rows: list[dict[str, Any]] = []
            for item in dados:
                data_raw = item.get("data", "")
                valor_raw = item.get("valor", "")
                if not valor_raw:
                    continue
                try:
                    valor = float(valor_raw)
                except (ValueError, TypeError):
                    continue
                rows.append({
                    "data": _data_iso_from_bcb(data_raw),
                    "codigoSerie": codigo,
                    "nomeSerie": nome,
                    "valor": valor,
                })

            inseridos = _upsert_batches(
                session, MacroBcb, rows,
                conflict_cols=["data", "codigoSerie"],
                update_cols=["valor", "nomeSerie"],
            )
            total += inseridos
            duracao_ms = int((time.monotonic() - t0) * 1000)
            _log_sync(session, fonte, "ok", inseridos, duracao_ms=duracao_ms)
            logger.info("%s: %d registros em %d ms", fonte, inseridos, duracao_ms)

        except Exception as e:
            duracao_ms = int((time.monotonic() - t0) * 1000)
            _log_sync(session, fonte, "erro", 0, erro=str(e), duracao_ms=duracao_ms)
            logger.error("%s falhou: %s", fonte, e)

    return total


# ---------------------------------------------------------------------------
# IBGE aggregates (PIB estadual, PMC varejo nacional)
# ---------------------------------------------------------------------------

def sync_ibge(session: Session) -> int:
    """Fetch IBGE aggregates 5938/8881 and UPSERT into MacroIbge."""
    total = 0
    for endpoint in ENDPOINTS_IBGE:
        fonte = f"IBGE/{endpoint['nome']} ({endpoint['codigo_agregado']})"
        t0 = time.monotonic()
        try:
            dados = _fetch_with_retry(endpoint["url"])
            rows: list[dict[str, Any]] = []
            for variavel_obj in dados:
                nome_variavel = variavel_obj.get("variavel", endpoint["nome"])
                for resultado in variavel_obj.get("resultados", []):
                    for serie in resultado.get("series", []):
                        localidade = serie.get("localidade", {}).get("nome", "Brasil")
                        for periodo, valor_raw in serie.get("serie", {}).items():
                            if not valor_raw or valor_raw in ("...", "..", "-", "X"):
                                continue
                            try:
                                valor = float(valor_raw)
                            except (ValueError, TypeError):
                                continue
                            rows.append({
                                "data": periodo,
                                "codigoAgregado": endpoint["codigo_agregado"],
                                "variavel": nome_variavel,
                                "localidade": localidade,
                                "valor": valor,
                            })

            inseridos = _upsert_batches(
                session, MacroIbge, rows,
                conflict_cols=["data", "codigoAgregado", "variavel", "localidade"],
                update_cols=["valor"],
            )
            total += inseridos
            duracao_ms = int((time.monotonic() - t0) * 1000)
            _log_sync(session, fonte, "ok", inseridos, duracao_ms=duracao_ms)
            logger.info("%s: %d registros em %d ms", fonte, inseridos, duracao_ms)

        except Exception as e:
            duracao_ms = int((time.monotonic() - t0) * 1000)
            _log_sync(session, fonte, "erro", 0, erro=str(e), duracao_ms=duracao_ms)
            logger.error("%s falhou: %s", fonte, e)

    return total


# ---------------------------------------------------------------------------
# PMC per-segment (IBGE tabela 8882, two variables)
# ---------------------------------------------------------------------------

# Two upsert passes (one per variable) intentionally: an UPDATE that only
# sets variacaoMensal preserves any previously-stored variacaoAnual, which
# a single combined pass with both fields would overwrite with NULL on months
# when IBGE only publishes one of them. This matches api/sync.py behavior.

def sync_pmc(session: Session) -> int:
    """Fetch IBGE PMC 8882 (multi-segmento) and UPSERT into PmcIbge."""
    fonte = "IBGE/PMC (8882)"
    t0 = time.monotonic()
    now = datetime.now()

    try:
        periodos = _periodos_mensais_ibge(2014)
        url = (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/8882"
            f"/periodos/{periodos}"
            f"/variaveis/11709|11710"
            f"?localidades=N1[all]"
            f"&classificacao=11046[56734]|85[all]"
        )
        dados = _fetch_with_retry(url)

        VAR_COL = {"11709": "variacaoMensal", "11710": "variacaoAnual"}
        rows_by_var: dict[str, list[dict[str, Any]]] = {
            "variacaoMensal": [],
            "variacaoAnual": [],
        }

        for variavel_obj in dados:
            var_id = str(variavel_obj.get("id", ""))
            coluna = VAR_COL.get(var_id)
            if not coluna:
                continue
            for resultado in variavel_obj.get("resultados", []):
                segmento_map: dict[str, str] = {}
                for clf in resultado.get("classificacoes", []):
                    if clf.get("id") == "85":
                        segmento_map = clf.get("categoria", {})
                        break
                if not segmento_map:
                    continue
                codigo_seg = next(iter(segmento_map))
                nome_seg = segmento_map[codigo_seg]
                for serie in resultado.get("series", []):
                    for periodo_raw, valor_raw in serie.get("serie", {}).items():
                        if not valor_raw or valor_raw in ("..", "...", "-", "X"):
                            continue
                        try:
                            valor = float(valor_raw)
                        except (ValueError, TypeError):
                            continue
                        rows_by_var[coluna].append({
                            "data": f"{periodo_raw[:4]}-{periodo_raw[4:6]}",
                            "codigoSegmento": codigo_seg,
                            "nomeSegmento": nome_seg,
                            coluna: valor,
                            "dataColeta": now,
                        })

        inseridos = 0
        inseridos += _upsert_batches(
            session, PmcIbge, rows_by_var["variacaoMensal"],
            conflict_cols=["data", "codigoSegmento"],
            update_cols=["nomeSegmento", "variacaoMensal", "dataColeta"],
        )
        inseridos += _upsert_batches(
            session, PmcIbge, rows_by_var["variacaoAnual"],
            conflict_cols=["data", "codigoSegmento"],
            update_cols=["nomeSegmento", "variacaoAnual", "dataColeta"],
        )

        duracao_ms = int((time.monotonic() - t0) * 1000)
        _log_sync(session, fonte, "ok", inseridos, duracao_ms=duracao_ms)
        logger.info("%s: %d registros em %d ms", fonte, inseridos, duracao_ms)
        return inseridos

    except Exception as e:
        duracao_ms = int((time.monotonic() - t0) * 1000)
        _log_sync(session, fonte, "erro", 0, erro=str(e), duracao_ms=duracao_ms)
        logger.error("%s falhou: %s", fonte, e)
        return 0


# ---------------------------------------------------------------------------
# CAGED (employment stock via BCB SGS)
# ---------------------------------------------------------------------------

def sync_caged(session: Session) -> int:
    """Fetch 6 CAGED series from BCB SGS and UPSERT into CagedBcb."""
    total = 0
    now = datetime.now()
    for codigo, setor in SERIES_CAGED.items():
        fonte = f"BCB/CAGED {setor} ({codigo})"
        t0 = time.monotonic()
        url_base = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
            f"/dados?formato=json&dataInicial=01/01/2014"
        )
        try:
            dados = _fetch_with_retry(url_base)
            rows: list[dict[str, Any]] = []
            prev_estoque: float | None = None
            for item in dados:
                data_raw = item.get("data", "")
                valor_raw = item.get("valor", "")
                if not valor_raw:
                    continue
                try:
                    estoque = float(valor_raw)
                except (ValueError, TypeError):
                    continue
                saldo = estoque - prev_estoque if prev_estoque is not None else None
                rows.append({
                    "data": _data_iso_from_bcb(data_raw),
                    "estoque": estoque,
                    "saldo": saldo,
                    "setor": setor,
                    "codigoBcb": codigo,
                    "urlFonte": url_base,
                    "dataColeta": now,
                })
                prev_estoque = estoque

            inseridos = _upsert_batches(
                session, CagedBcb, rows,
                conflict_cols=["data", "codigoBcb"],
                update_cols=["estoque", "saldo", "dataColeta"],
            )
            total += inseridos
            duracao_ms = int((time.monotonic() - t0) * 1000)
            _log_sync(session, fonte, "ok", inseridos, duracao_ms=duracao_ms)
            logger.info("%s: %d registros em %d ms", fonte, inseridos, duracao_ms)

        except Exception as e:
            duracao_ms = int((time.monotonic() - t0) * 1000)
            _log_sync(session, fonte, "erro", 0, erro=str(e), duracao_ms=duracao_ms)
            logger.error("%s falhou: %s", fonte, e)

    return total


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def sync_all(session: Session) -> dict[str, int]:
    """Run the 4 syncs sequentially. Returns row counts per source.

    Never raises — each sub-sync catches its own exceptions and logs them
    to MacroSyncLog so a single flaky endpoint doesn't abort the whole run.
    Unexpected exceptions during orchestration itself (e.g. DB
    disconnection) do bubble up and fail the script.
    """
    logger.info("macro sync start")
    t0 = time.monotonic()
    counts = {
        "bcb":   sync_bcb(session),
        "ibge":  sync_ibge(session),
        "pmc":   sync_pmc(session),
        "caged": sync_caged(session),
    }
    total = sum(counts.values())
    duracao_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "macro sync done in %d ms: bcb=%d ibge=%d pmc=%d caged=%d (total=%d)",
        duracao_ms,
        counts["bcb"], counts["ibge"], counts["pmc"], counts["caged"], total,
    )
    return counts
