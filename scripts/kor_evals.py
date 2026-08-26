"""Kör golden eval-setet mot supportagenten, live mot lokal DeepSeek.

    python scripts/kor_evals.py

Samma sanktionerade väg som run_live_tests: MemoryStorage, syntetiska
fixtures, DATABASE_URL blankad i egen process. Skriver rapporten till
docs/live-tests/evals-<stamp>.json och skriver ut en rad per case.

Golden-setet: app/agent/evals.SUPPORT_GOLDEN — varje case är ett verkligt
produktionsfel eller en verklig gränsdragning. Mätningen är mekanisk
(eskaleringsbeslut, kategori, faithfulness via grundningsextraktorn) —
ingen LLM-domare.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "snajp-support"))

# Samma skäl som run_live_tests: harnessen kör enbart MemoryStorage, och en
# fjärr-DATABASE_URL ur .env fäller annars DeepSeek-spärren i onödan.
os.environ["DATABASE_URL"] = ""

OUT_DIR = ROOT / "docs" / "live-tests"


async def main() -> None:
    from app.agent.evals import SUPPORT_GOLDEN, kor_support_evals

    print(f"Kör {len(SUPPORT_GOLDEN)} golden cases mot supportagenten ...", flush=True)
    rapport = await kor_support_evals()

    for rad in rapport["resultat"]:
        status = "OK " if rad["godkand"] else "FEL"
        print(f"  [{status}] {rad['case']} ({rad['latency_ms']} ms)")
        for fel in rad["fel"]:
            print(f"        - {fel}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ut = OUT_DIR / f"evals-{stamp}.json"
    ut.parent.mkdir(parents=True, exist_ok=True)
    ut.write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{rapport['godkanda']}/{rapport['totalt']} godkända. Skrev {ut.relative_to(ROOT)}")
    if rapport["godkanda"] < rapport["totalt"]:
        raise SystemExit(1)


asyncio.run(main())
