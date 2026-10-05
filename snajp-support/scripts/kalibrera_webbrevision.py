"""Kör webbrevisionen skarpt mot Antons facit och jämför (plan 2026-10-05, fas 3).

    python scripts/kalibrera_webbrevision.py

Hämtar varje sajt (httpx), kör PageSpeed och bildbedömningen och skriver ut
betyg, utslag för "Företag med gamla hemsidor" och facit. Inga kunddata: bara
publika bolagssajter. Kostar ett bildanrop per sajt mot vision-sidovagnen.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("LEADS_WEBBREVISION", None)
os.environ.pop("LEADS_WEBBSIGNAL", None)

from app.leads.bedomning import webbutslag  # noqa: E402
from app.leads.platshallare import platshallare_for_webbplats  # noqa: E402
from app.leads.webbrevision import citerbara_rader, revidera, visuell  # noqa: E402
from app.leads.webbsignal import mat_webbplats  # noqa: E402

FACIT = [
    ("Byggarna Berggren", "https://byggarnaberggren.se", "träff"),
    ("Vicht Engineering", "https://vicht.se", "träff"),
    ("Torbens Byggservice", "https://torbensbygg.se", "listspår (parkerad)"),
    ("Ställningskompaniet", "https://stallningskompaniet.se", "okänt (gränsfall)"),
    ("Björkekärrs Bygg", "https://bjorkekarrsbygg.se", "miss"),
    ("Eustaff", "https://eustaff.se", "miss"),
    ("Ostia", "https://ostia.io", "miss på storlek (internationellt)"),
]


async def lokal_skarmbild(url: str) -> str | None:
    import base64

    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            webblasare = await p.chromium.launch()
            sida = await webblasare.new_page(viewport={"width": 1440, "height": 900})
            await sida.goto(url, wait_until="networkidle", timeout=30000)
            bild = await sida.screenshot(type="jpeg", quality=70)
            await webblasare.close()
    except Exception as fel:  # noqa: BLE001
        print(f"  (ingen lokal skärmbild för {url}: {type(fel).__name__})")
        return None
    return "data:image/jpeg;base64," + base64.b64encode(bild).decode()


async def en(namn: str, url: str, facit: str) -> str:
    parkerad = await platshallare_for_webbplats(url)
    if parkerad:
        return f"{namn:22} parkerad ({parkerad})  facit: {facit}"
    fakta = await mat_webbplats(url)
    rev = await revidera(url, fakta)
    if rev.get("modernitet") is None:
        # PageSpeeds kvot utan nyckel är delad och ofta slut: ta skärmbilden
        # lokalt (bara i kalibreringen, aldrig i drift) och kör samma bedömning.
        bild = await lokal_skarmbild(url)
        vis = await visuell(url, bild, fakta) if bild else None
        if vis:
            rev.update(modernitet=vis["modernitet"], layout_era=vis.get("layout_era"),
                       brister=vis["top_3_brister"],
                       internationell=vis.get("intern_eller_internationell") == "internationell")
            rev["rader"] = citerbara_rader(rev)
    utslag = webbutslag("Företag med gamla hemsidor", rev)
    mobil = (rev.get("pagespeed") or {}).get("mobil") or {}
    return (
        f"{namn:22} modernitet {rev.get('modernitet')!s:4} internationell {rev.get('internationell')!s:5} "
        f"PSI mobil {mobil.get('prestanda')!s:4} → {utslag[0] if utslag else '—':6} facit: {facit}\n"
        f"{'':22} brister: {'; '.join(rev.get('brister') or []) or '—'}"
    )


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for rad in await asyncio.gather(*(en(*f) for f in FACIT)):
        print(rad)


if __name__ == "__main__":
    asyncio.run(main())
