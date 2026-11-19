#!/usr/bin/env python3
"""PR-kontrollen "releasens migrationer" utan databasanslutning.

    python scripts/releasens_migrationer.py

docs/compliance/synkflytt-plan.md steg 9 (runbookens steg 10). Frågar api:t i
development och main (GET /api/drift/schema, nyckeln SCHEMA_LASNYCKEL) vilka
migrationer som är körda, och jämför med migrationerna i den utcheckade koden:

* development ska ha kört alla. Saknas någon fälls kontrollen: en migration ska
  ha gått i development innan releasen når main.
* main visar vad releasen bär, alltså det som körs när PR:en mergas.

Ingen databas, inget lösenord: svaret bär bara filnamn. Miljövariabler:

    SCHEMA_LASNYCKEL   den smala nyckeln (samma värde i båda miljöerna)
    DEV_API_URL        t.ex. https://api-development-5cc3.up.railway.app
    MAIN_API_URL       t.ex. https://api-production-d7695.up.railway.app

Rapporten skrivs ut och, i Actions, till GITHUB_STEP_SUMMARY. Slutkod 1 när
development har okörda migrationer eller när ett api inte svarar, 2 när
variablerna saknas.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPO_ROOT / "db" / "migrations"
COMPAT = "000_auth_compat"
NYCKELHUVUD = "X-Schema-Nyckel"


def repots_versioner(katalog: Path = MIGRATIONS) -> set[str]:
    """Versionerna som railway_migrate.planned() kör, samma namn som liggaren."""
    return {COMPAT} | {p.stem for p in katalog.glob("*.sql")}


def hamta(bas: str, nyckel: str, timeout: float = 30) -> set[str]:
    """Liggarens versioner ur ett api. Kastar RuntimeError med statusen vid fel,
    utan att nyckeln eller svaret i övrigt syns."""
    url = bas.rstrip("/") + "/api/drift/schema"
    req = urllib.request.Request(url, headers={NYCKELHUVUD: nyckel, "User-Agent": "snajp-releasens-migrationer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as svar:
            data = json.load(svar)
    except urllib.error.HTTPError as fel:
        raise RuntimeError(f"{url} svarade {fel.code}") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as fel:
        raise RuntimeError(f"{url} gick inte att läsa ({type(fel).__name__})") from None
    versioner = data.get("versioner") if isinstance(data, dict) else None
    if not isinstance(versioner, list) or not all(isinstance(v, str) for v in versioner):
        raise RuntimeError(f"{url} gav ett okänt svar")
    return set(versioner)


def bedom(repo: set[str], dev: set[str], main: set[str]) -> tuple[list[str], list[str]]:
    """Ren funktion: (okörda i development, det som körs mot main vid mergen)."""
    return sorted(repo - dev), sorted(repo - main)


def rapport(okorda_dev: list[str], releasen: list[str]) -> str:
    rader = ["### Releasens migrationer", "Körs mot main när PR:en mergas:"]
    rader += [f"- {v}" for v in releasen] or ["- inga, schemat är redan aktuellt"]
    if okorda_dev:
        rader += ["", "**Development har okörda migrationer:**"] + [f"- {v}" for v in okorda_dev]
    return "\n".join(rader)


def main() -> int:
    nyckel = os.environ.get("SCHEMA_LASNYCKEL", "").strip()
    dev_url = os.environ.get("DEV_API_URL", "").strip()
    main_url = os.environ.get("MAIN_API_URL", "").strip()
    if not (nyckel and dev_url and main_url):
        print("Saknar SCHEMA_LASNYCKEL, DEV_API_URL eller MAIN_API_URL.", file=sys.stderr)
        return 2
    try:
        dev = hamta(dev_url, nyckel)
        prod = hamta(main_url, nyckel)
    except RuntimeError as fel:
        print(f"::error::{fel}")
        return 1
    okorda_dev, releasen = bedom(repots_versioner(), dev, prod)
    text = rapport(okorda_dev, releasen)
    print(text)
    sammanfattning = os.environ.get("GITHUB_STEP_SUMMARY")
    if sammanfattning:
        with open(sammanfattning, "a", encoding="utf-8") as fil:
            fil.write(text + "\n")
    if okorda_dev:
        print("::error::Development har okörda migrationer. De ska ha gått där innan releasen når main.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
