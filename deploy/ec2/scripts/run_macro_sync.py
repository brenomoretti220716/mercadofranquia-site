#!/usr/bin/env python3
"""
Standalone entrypoint for the daily macro data sync.

Wired via systemd timer in Sessão 5 (mf-macro-sync.timer @ 03:00 BRT).
Safe to run manually for debugging from the EC2 venv:

    python scripts/run_macro_sync.py

Exit codes:
    0   orchestration completed (individual source errors are logged to
        MacroSyncLog, not surfaced here — systemd expects 0 for "ran")
    1   unhandled crash (DB down, import failure, etc.)
"""
from __future__ import annotations

import logging
import sys

from app.db import SessionLocal
from app.services.macro_sync import sync_all


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        with SessionLocal() as session:
            sync_all(session)
    except Exception:
        logging.exception("macro sync crashed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
