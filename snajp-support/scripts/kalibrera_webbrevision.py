"""Kör webbrevisionen skarpt mot Antons facit och mäter träffsäkerheten.

    python scripts/kalibrera_webbrevision.py [--facit FIL] [--bilder KATALOG] [--bara N]

Facit (standard `tests/leads/fixtures/webbfacit_2026-10-08.json`) har fyra
nivåer: akut, dalig, bra, mycket_bra, plus avvecklad (ska kastas). Skriptet
kör samma kedja som drift (webbsignal → platshållare → webbrevision.revidera)
och skriver ut nivå mot facit, träffsäkerheten och ScrapeGraph-krediterna
före och efter. Grinden (plan 2026-10-08): minst 85 % rätt sammanslaget
(akut+dalig mot bra+mycket_bra) och ingen akut sajt på bra.

Inga kunddata: bara publika bolagssajter. Kostar en skärmbild och ett
bildanrop per sajt.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT))
os.environ.pop("LEADS_WEBBREVISION", None)
os.environ.pop("LEADS_WEBBSIGNAL", None)
os.environ.pop("LEADS_PLATSHALLARKONTROLL", None)

from app.leads import webbrevision  # noqa: E402
from app.leads.platshallare import AVVECKLAT, platshallare_for_webbplats  # noqa: E402
from app.leads.webbsignal import mat_webbplats  # noqa: E402

DALIGA = {"akut", "dalig"}


def _krediter() -> int | None:
    from app.config import get_settings

    try:
        from scrapegraph_py import ScrapeGraphAI

        svar = ScrapeGraphAI(api_key=get_settings().scrapegraphai_api_key).credits()
        data = svar.data if hasattr(svar, "data") else svar
        data = data.model_dump() if hasattr(data, "model_dump") else data
        return next((int(v) for k, v in (data or {}).items() if "remaining" in k.lower()), None)
    except Exception:  # noqa: BLE001
        return None


async def en(rad: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        url = webbrevision.startsida(rad["url"])
        fakta = await mat_webbplats(url)
        skal = await platshallare_for_webbplats(url)
        if skal == AVVECKLAT:
            return {**rad, "fick": "avvecklad", "modernitet": None}
        if skal:
            fakta = {**fakta, "platshallare": skal}
        rev = await webbrevision.revidera(url, fakta)
        return {**rad, "fick": rev.get("webbniva") or "okand", "modernitet": rev.get("modernitet"),
                "brister": rev.get("brister") or [], "platshallare": rev.get("platshallare")}


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--facit", default=str(ROT / "tests/leads/fixtures/webbfacit_2026-10-08.json"))
    p.add_argument("--bilder", help="spara skärmbilderna här för egen granskning")
    p.add_argument("--bara", type=int, help="bara de N första sajterna")
    a = p.parse_args()
    sajter = json.loads(Path(a.facit).read_bytes().decode("utf-8"))["sajter"][: a.bara]
    bilder = Path(a.bilder) if a.bilder else None
    if bilder:
        bilder.mkdir(parents=True, exist_ok=True)
        verklig = webbrevision.visuell

        async def sparande(url, skarmbild, fakta):
            (bilder / f"{webbrevision.doman(url)}.png").write_bytes(base64.b64decode(skarmbild.split(",", 1)[1]))
            return await verklig(url, skarmbild, fakta)

        webbrevision.visuell = sparande
    fore = _krediter()
    sem = asyncio.Semaphore(4)
    utfall = await asyncio.gather(*(en(r, sem) for r in sajter))
    efter = _krediter()

    ratt = akut_pa_bra = 0
    for r in sorted(utfall, key=lambda r: (r["niva"], r["url"])):
        ok = r["fick"] == r["niva"] or (r["fick"] in DALIGA and r["niva"] in DALIGA) or (
            r["fick"] in ("bra", "mycket_bra") and r["niva"] in ("bra", "mycket_bra"))
        ratt += ok
        akut_pa_bra += r["niva"] == "akut" and r["fick"] in ("bra", "mycket_bra")
        print(f"{'OK ' if ok else 'FEL'} {r['niva']:10} fick {r['fick']:10} m={r['modernitet']!s:4} {r['url']}"
              + (f"  ({r['platshallare']})" if r.get("platshallare") else ""))
    print(f"\nRätt sammanslaget: {ratt}/{len(utfall)} = {ratt / max(1, len(utfall)):.0%}. Akut på bra: {akut_pa_bra}.")
    if fore is not None and efter is not None:
        print(f"ScrapeGraph-krediter: {fore} → {efter} ({fore - efter} för {len(utfall)} sajter).")
    print("GRIND:", "GODKÄND" if ratt / max(1, len(utfall)) >= 0.85 and not akut_pa_bra else "UNDERKÄND")


if __name__ == "__main__":
    asyncio.run(main())
