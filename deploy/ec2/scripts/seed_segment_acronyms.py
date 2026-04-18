#!/usr/bin/env python3
"""
Seed initial segment acronyms used by the ABF charts on /mercado.

These are best-effort guesses inferred from the 13 distinct segment names
present in the local pipeline (api/abf.db faturamento table, excluding the
"Total" aggregate). Values below may need manual correction to match the
acronyms used publicly by the ABF Franchising Report.

Idempotent: re-running overwrites "acronimo" for existing "segmento" keys.

Usage (on EC2 inside the venv):
    python scripts/seed_segment_acronyms.py

Env:
    DATABASE_URL   postgresql://mf_user:...@localhost:5432/mercadofranquia
"""
from __future__ import annotations

import os
import sys

try:
    import psycopg
except ImportError:
    sys.exit("Missing dependency: pip install 'psycopg[binary]>=3.1'")


DEFAULT_DB_URL = "postgresql://mf_user:mf_senha_forte_2026@localhost:5432/mercadofranquia"


SEED: list[tuple[str, str]] = [
    ("Alimentação",                   "ALI"),    # inferido (não existe em produção, canônico do pipeline)
    ("Alimentação - CD",              "ACD"),    # "ACD" em produção, bate com "Comercialização e Distribuição"
    ("Alimentação - FS",              "AFS"),    # "AFS" em produção, bate com "Food Service"
    ("Casa e Construção",             "CC"),
    ("Comunicação/TI",                "CIE"),    # produção grafa "Comunicação, Informática e Eletrônicos"
    ("Educação",                      "EDU"),
    ("Entretenimento e Lazer",        "EL"),
    ("Hotelaria e Turismo",           "HT"),
    ("Limpeza e Conservação",         "LC"),
    ("Moda",                          "MOD"),
    ("Saúde, Beleza e Bem-Estar",     "SBBE"),   # pipeline: "Bem-Estar" com hífen; produção: "Bem Estar" sem — mantém canônico do pipeline
    ("Serviços Automotivos",          "SA"),
    ("Serviços e Outros Negócios",    "SON"),
]


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
    with psycopg.connect(db_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            for segmento, acronimo in SEED:
                cur.execute(
                    """
                    INSERT INTO "SegmentAcronym" (segmento, acronimo)
                    VALUES (%s, %s)
                    ON CONFLICT (segmento) DO UPDATE
                        SET acronimo = EXCLUDED.acronimo
                    """,
                    (segmento, acronimo),
                )
        conn.commit()
    print(f"Seeded {len(SEED)} segment acronyms.")


if __name__ == "__main__":
    main()
