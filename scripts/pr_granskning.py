#!/usr/bin/env python
"""Säkerhets- och AI-frågan i varje PR mot development (INV-PROC-001).

Körs i CI-jobbet `invariants` på varje pull request
(.github/workflows/verify.yml). Läser PR:ens beskrivning ur händelsefilen
(GITHUB_EVENT_PATH) och fäller jobbet om avsnitten "Säkerhet och dataskydd"
eller "AI-påverkan" ur `.github/pull_request_template.md` saknas eller saknar
ett ikryssat svar.

Varför: ISO 27001 A.5.8 kräver att informationssäkerhet ingår i planeringen av
varje arbete, och ISO 42001 A.6.1.3 att ändringar av modeller och prompter
prövas. Före 2026-11-18 fanns ingen fast fråga; säkerhetsinvarianterna skrevs
när någon kom ihåg det.

Undantag, med skäl:
  * Botar (Dependabot): beskrivningen skrivs av GitHub, och beroendets risk
    prövas av larmen och CI.
  * PR:er mot en annan gren än development (release-PR:er mot main): de samlar
    PR:er som redan besvarat frågan.

Lokalt: `python scripts/pr_granskning.py --fil beskrivning.md` prövar en text.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

AVSNITT = ("Säkerhet och dataskydd", "AI-påverkan")
BASGREN = "development"

_RUBRIK = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
_IKRYSSAD = re.compile(r"^\s*[-*]\s+\[[xX]\]\s+\S", re.MULTILINE)


def avsnitt_text(beskrivning: str, rubrik: str) -> str | None:
    """Texten under rubriken fram till nästa rubrik, eller None om rubriken saknas."""
    traffar = list(_RUBRIK.finditer(beskrivning or ""))
    for i, m in enumerate(traffar):
        if m.group(1).strip().lower() == rubrik.lower():
            slut = traffar[i + 1].start() if i + 1 < len(traffar) else len(beskrivning)
            return beskrivning[m.end() : slut]
    return None


def brister(beskrivning: str) -> list[str]:
    """Tom lista = frågan besvarad."""
    ut: list[str] = []
    for rubrik in AVSNITT:
        text = avsnitt_text(beskrivning, rubrik)
        if text is None:
            ut.append(f"Avsnittet '## {rubrik}' saknas. Använd mallen i .github/pull_request_template.md.")
        elif not _IKRYSSAD.search(text):
            ut.append(f"Avsnittet '## {rubrik}' har inget ikryssat svar (- [x] ...).")
    return ut


def undantag(handelse: dict) -> str | None:
    pr = handelse.get("pull_request") or {}
    login = ((pr.get("user") or {}).get("login") or "").lower()
    if login.endswith("[bot]"):
        return f"PR:en är skapad av {login}."
    bas = ((pr.get("base") or {}).get("ref")) or ""
    if bas != BASGREN:
        return f"PR:en går mot {bas or 'okänd gren'}, inte {BASGREN}."
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fil", type=Path, help="Pröva en beskrivning i en fil i stället för händelsen.")
    args = parser.parse_args(argv)

    if args.fil:
        beskrivning = args.fil.read_text(encoding="utf-8")
    else:
        sokvag = os.environ.get("GITHUB_EVENT_PATH", "")
        if not sokvag:
            print("Ingen GITHUB_EVENT_PATH; inget att pröva.")
            return 0
        handelse = json.loads(Path(sokvag).read_text(encoding="utf-8"))
        if "pull_request" not in handelse:
            print("Inte en pull request; inget att pröva.")
            return 0
        skal = undantag(handelse)
        if skal:
            print(f"Undantagen: {skal}")
            return 0
        beskrivning = handelse["pull_request"].get("body") or ""

    fel = brister(beskrivning)
    for rad in fel:
        print(f"::error::{rad}")
    if fel:
        return 1
    print("Säkerhets- och AI-frågan är besvarad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
