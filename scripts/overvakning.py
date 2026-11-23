#!/usr/bin/env python3
"""Övervakningen av produktionen som ett jobb hos Railway.

    python scripts/overvakning.py                 # kontrollera, larma vid avvikelse
    python scripts/overvakning.py --simulera-fel  # prova larmkedjan utan att något är nere

## Varför skriptet finns

Övervakningen låg bara i `.github/workflows/overvakning.yml`. 2026-11-23
slutade GitHub starta jobb för repot (misslyckad betalning eller slut på
minuter), och då larmade ingenting om produktionen hade gått ner. Samma
kontroll körs därför också hos Railway, som ett schemalagt jobb i miljön
development: en annan miljö än den som övervakas, och utan GitHubs minuter.
GitHub-flödet står kvar som en andra, oberoende kontroll när det går.

## Kontrollen

Samma som i GitHub-flödet, och bara publika adresser:

  * webbens startsida svarar HTTP 200,
  * /health svarar 200 med status=ok, mode=live, storage=postgres, jobs=redis,
  * /health/ready svarar 200 med status=ok och degraded=false.

Tre försök med en halv minut emellan, så att en omstart under en deploy inte
larmar. Ett enda friskt försök räcker.

## Larmet

Ett mejl genom mejltjänsten (RESEND_API_KEY) från LARM_FRAN till LARM_TILL.
Mejlet bär bara statuskoder och de kända fälten, sanerade, aldrig svarskroppar.
Jobbet har inget minne mellan körningarna. Larmfloden hålls ändå nere: varje
larm bär en idempotensnyckel av avvikelserna och sextimmarsblocket, så att
mejltjänsten skickar samma larm högst en gång per block. En ny avvikelse ger
ett nytt mejl direkt.

Körningen slutar med kod 1 vid avvikelse, så att Railway visar den som
misslyckad, och 0 när produktionen är frisk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone

WEBB_URL = "https://www.snajp.se/"
API_HALSA_URL = "https://api-production-d7695.up.railway.app/health"
API_REDO_URL = "https://api-production-d7695.up.railway.app/health/ready"

HALSA_VANTAT = {"status": "ok", "mode": "live", "storage": "postgres", "jobs": "redis"}
REDO_VANTAT = {"status": "ok", "degraded": "false"}

FORSOK = 3
PAUS_SEKUNDER = 30
#: Samma larm skickas högst en gång per så här många timmar.
BLOCK_TIMMAR = 6
RESEND = "https://api.resend.com/emails"
SIMULERAT = "SIMULERAT FEL: manuell provkörning. Inget är nere."

Svar = tuple[int, object]


def sanera(varde: object) -> str:
    """Fältvärden hamnar i ett mejl: bara korta, enkla värden skrivs ut."""
    text = "" if varde is None else (str(varde).lower() if isinstance(varde, bool) else str(varde))
    if not text:
        return "(saknas)"
    return text if re.fullmatch(r"[A-Za-z0-9._-]{1,32}", text) else "(oväntat värde)"


def hamta(url: str) -> Svar:
    """(statuskod, tolkad JSON eller None). Statuskod 0 = adressen svarade inte."""
    for forsok in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "snajp-overvakning/1.0"})
            with urllib.request.urlopen(req, timeout=20) as svar:
                kod, ra = svar.status, svar.read(200_000)
        except urllib.error.HTTPError as fel:
            kod, ra = fel.code, b""
        except Exception:  # noqa: BLE001 — nätverksfel räknas som inget svar
            kod, ra = 0, b""
        if kod not in (0, 429) and kod < 500:
            break
        if forsok < 2:
            time.sleep(10)
    try:
        return kod, json.loads(ra) if ra else None
    except ValueError:
        return kod, None


def _falt(url: str, namn: str, svar: Svar, vantat: dict[str, str], vid_fel: str) -> list[str]:
    kod, kropp = svar
    if kod != 200:
        return [f"{namn} {url} svarade HTTP {kod} (väntat 200{vid_fel})."]
    if not isinstance(kropp, dict):
        return [f"{namn} {url} svarade inte med JSON."]
    ut = []
    for falt, ratt in vantat.items():
        varde = kropp.get(falt)
        text = str(varde).lower() if isinstance(varde, bool) else ("" if varde is None else str(varde))
        if text != ratt:
            ut.append(f"{namn} {url}: fältet {falt} är {sanera(varde)} (väntat {ratt}).")
    return ut


def avvikelser(hamtare: Callable[[str], Svar] = hamta) -> list[str]:
    """Ren mot `hamtare`: det som skiljer produktionen från det friska läget."""
    ut: list[str] = []
    kod, _ = hamtare(WEBB_URL)
    if kod != 200:
        ut.append(f"Webbens startsida {WEBB_URL} svarade HTTP {kod} (väntat 200).")
    ut += _falt(API_HALSA_URL, "Hälsokontrollen", hamtare(API_HALSA_URL), HALSA_VANTAT, "")
    ut += _falt(
        API_REDO_URL, "Beredskapskontrollen", hamtare(API_REDO_URL), REDO_VANTAT,
        "; 503 betyder att lagringen inte svarar",
    )
    return ut


def larmnyckel(rader: list[str], nu: datetime) -> str:
    """Samma avvikelser i samma sextimmarsblock ger samma nyckel, och
    mejltjänsten skickar då inte en gång till."""
    block = f"{nu:%Y-%m-%d}-{nu.hour // BLOCK_TIMMAR}"
    avtryck = hashlib.sha256("\n".join(sorted(rader)).encode("utf-8")).hexdigest()[:16]
    return f"driftlarm-{block}-{avtryck}"


def larmmejl(rader: list[str], nu: datetime) -> tuple[str, str]:
    amne = "Driftlarm: produktionen avviker" if SIMULERAT not in rader else "Driftlarm (prov): larmkedjan fungerar"
    text = "\n".join(
        [
            f"Övervakningen hos Railway såg en avvikelse {nu:%Y-%m-%d %H:%M} UTC.",
            "",
            *[f"- {r}" for r in rader],
            "",
            "Kontrollen gjorde tre försök med en halv minut emellan.",
            f"Samma larm skickas högst en gång per {BLOCK_TIMMAR} timmar. En ny avvikelse ger ett nytt mejl.",
            "Loggen: Railway, tjänsten overvakning, miljön development.",
        ]
    )
    return amne, text


def skicka_larm(rader: list[str], nu: datetime, environ: dict[str, str] | None = None) -> str:
    """Skickar larmet och svarar med en rad för loggen. Kastar aldrig."""
    environ = os.environ if environ is None else environ
    nyckel = (environ.get("RESEND_API_KEY") or "").strip()
    fran, till = (environ.get("LARM_FRAN") or "").strip(), (environ.get("LARM_TILL") or "").strip()
    if not (nyckel and fran and till):
        return "LARMET SKICKADES INTE: RESEND_API_KEY, LARM_FRAN eller LARM_TILL saknas på tjänsten."
    amne, text = larmmejl(rader, nu)
    kropp = json.dumps({"from": f"Snajp drift <{fran}>", "to": [till], "subject": amne, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        RESEND, data=kropp, method="POST",
        headers={
            "Authorization": f"Bearer {nyckel}", "Content-Type": "application/json",
            "Idempotency-Key": larmnyckel(rader, nu), "User-Agent": "snajp-overvakning/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as svar:
            return f"Larmet är lämnat till mejltjänsten (HTTP {svar.status})."
    except urllib.error.HTTPError as fel:
        return f"LARMET SKICKADES INTE: mejltjänsten svarade HTTP {fel.code}."
    except Exception as fel:  # noqa: BLE001
        return f"LARMET SKICKADES INTE: {type(fel).__name__}."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulera-fel", action="store_true")
    args = ap.parse_args(argv)
    simulera = args.simulera_fel or os.environ.get("SIMULERA_FEL", "").strip() == "1"

    rader: list[str] = []
    for forsok in range(1, FORSOK + 1):
        rader = avvikelser()
        if not rader:
            break
        print(f"Försök {forsok} avvek:", *rader, sep="\n  ", flush=True)
        if forsok < FORSOK:
            time.sleep(PAUS_SEKUNDER)
    if simulera:
        rader = [*rader, SIMULERAT]
    if not rader:
        print("Produktionen är i det friska läget.", flush=True)
        return 0
    print(skicka_larm(rader, datetime.now(timezone.utc)), flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
