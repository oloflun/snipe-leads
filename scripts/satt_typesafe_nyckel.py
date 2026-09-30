#!/usr/bin/env python3
"""Sätter Jev-nyckeln (TypeSafe) och Jev-läget på Railways api-tjänst.

    python scripts/satt_typesafe_nyckel.py --env development            # läge skugga
    python scripts/satt_typesafe_nyckel.py --env development --lage pa  # Jev fäller

Nyckeln finns redan i ~/.secrets/knowledge-graph.env (Antons Jev-experiment
2026-09-27, IMP-015). Skriptet läser den därifrån och skickar den direkt till
Railway — värdet skrivs aldrig ut, loggas aldrig och står aldrig i ett
skalkommando. Agenten kör inte skriptet: nyckelvärden hanteras av Anton.

Jev ser bara prospektens publika bolagsdata (app/leads/jev.py) — aldrig
kundens egna data. Beslut Anton 2026-09-30.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HEMLIGHETER = Path.home() / ".secrets" / "knowledge-graph.env"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", required=True, choices=("development", "main"))
    parser.add_argument("--lage", default="skugga", choices=("off", "skugga", "pa"))
    args = parser.parse_args()

    from dotenv import dotenv_values

    nyckel = (dotenv_values(HEMLIGHETER, interpolate=False) or {}).get("TYPESAFE_API_KEY") or ""
    if len(nyckel) < 20:
        print(f"TYPESAFE_API_KEY saknas i {HEMLIGHETER}.")
        return 1
    railway = shutil.which("railway")
    if not railway:
        print("Railway CLI saknas (npm i -g @railway/cli).")
        return 1
    svar = subprocess.run(
        [railway, "variables", "--service", "api", "--environment", args.env,
         "--set", f"TYPESAFE_API_KEY={nyckel}", "--set", f"IRIS_JEV={args.lage}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if svar.returncode != 0:
        # stderr kan i teorin eka argumenten — skriv bara ut att det föll.
        print(f"Railway vägrade (kod {svar.returncode}). Kör `railway login` och försök igen.")
        return svar.returncode
    print(f"Klart: Jev i läge '{args.lage}' på api/{args.env}. Tjänsten startar om med den nya variabeln.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
