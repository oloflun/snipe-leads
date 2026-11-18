#!/usr/bin/env python3
"""Startkommandot för driftjobben hos Railway (avbilden railway/Dockerfile.drift).

    python scripts/railway_drift.py synk      # tjänsten synk i miljön main (cron)
    python scripts/railway_drift.py migrera   # tjänsten migrera, en per miljö

docs/compliance/synkflytt-plan.md och synkflytt-runbook.md. Samma kommando i
båda miljöerna; vad som körs avgörs av RAILWAY_ENVIRONMENT_NAME, som Railway
sätter själv, och av två variabler som ägaren slår på:

* synk: torrkörning tills SYNK_APPLY=1. Körs bara i miljön main. Aldrig
  --forsta (första synken skriver till main och är gjord 2026-10-17).
  Anslutningarna: SYNK_MAIN_PG_URL och SYNK_DEVELOPMENT_PG_URL (railway_synk).
* migrera: visar vad som väntar tills MIGRERA_APPLY=1; då körs kedjan mot den
  egna miljön och kontrolleras efteråt att inget väntar, som i migrera.yml.
  Anslutningen: MIGRERA_PG_URL (railway_migrate.anslutning).

Utan jobb, utanför Railway eller i fel miljö vägrar kommandot.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

SKRIPT = Path(__file__).resolve().parent
MILJOER = ("main", "development")


def kommandon(jobb: str, environ: Mapping[str, str]) -> list[list[str]]:
    """Ren funktion: kommandona i tur och ordning."""
    miljo = environ.get("RAILWAY_ENVIRONMENT_NAME", "").strip()
    if jobb == "synk":
        if miljo != "main":
            sys.exit(f"AVBRYT: synken körs bara i Railway-miljön main, inte i {miljo or '(ingen)'}.")
        kommando = [sys.executable, str(SKRIPT / "railway_synk.py")]
        if environ.get("SYNK_APPLY", "").strip() == "1":
            kommando.append("--apply")
        return [kommando]
    if jobb == "migrera":
        if miljo not in MILJOER:
            sys.exit(f"AVBRYT: migrationerna körs bara i Railway-miljöerna {', '.join(MILJOER)}, inte i {miljo or '(ingen)'}.")
        bas = [sys.executable, str(SKRIPT / "railway_migrate.py"), "--env", miljo]
        if environ.get("MIGRERA_APPLY", "").strip() == "1":
            return [[*bas, "--apply"], bas]
        return [bas]
    sys.exit("Användning: railway_drift.py synk|migrera")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    jobb = argv[0] if argv else ""
    steg = kommandon(jobb, os.environ)
    for i, kommando in enumerate(steg):
        resultat = subprocess.run(kommando, capture_output=True, text=True, encoding="utf-8", errors="replace")
        sys.stdout.write(resultat.stdout)
        sys.stderr.write(resultat.stderr)
        sys.stdout.flush()
        if resultat.returncode != 0:
            return resultat.returncode
        # Kontrollen efter migrationerna, samma som migrera.yml.
        if jobb == "migrera" and len(steg) > 1 and i == len(steg) - 1 and "skulle köras" in resultat.stdout:
            print("FEL: migrationer väntar fortfarande efter körningen.", flush=True)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
