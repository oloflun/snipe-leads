"""Anmäl sajtens adresser till IndexNow (Bing, Yandex, Seznam, Naver).

Varför: ChatGPT:s webbsökning och Copilot står på Bings index. En ny sida
som Bing inte har sett finns inte för dem, och Bing hittar en ny sida på egen
hand först när den råkar crawla oss. IndexNow säger till direkt.

Nyckeln är inte hemlig. Den ligger publikt i public/<nyckel>.txt, och det är
så IndexNow kontrollerar att anmälan kommer från sajtens ägare: tjänsten
hämtar filen och jämför. Byts nyckeln ska filen bytas i samma commit.

Kör efter en release till main, när de nya sidorna är ute:

    python scripts/indexnow.py            # torrkörning: visar vad som skickas
    python scripts/indexnow.py --apply    # skickar

Adresserna läses ur den LIVE sitemapen, inte ur koden: det som anmäls ska
vara det som faktiskt svarar på sajten.

`--vanta-pa-deploy` (används av .github/workflows/indexnow.yml efter varje
push till main): väntar tills /llms.txt på sajten visar både priserna i
lib/pricing.ts och varje sökordssida i lib/landningar.ts innan något anmäls.
Annars hinner Bing hämta sidorna medan den gamla versionen fortfarande svarar,
och sökträffen visar det gamla priset (Anton 2026-11-05: priserna i länkarna
ska följa hemsidan av sig själva). Ändrar en release varken pris eller
sökordssidor säger llms.txt ingenting om deployen, därför väntar workflowet
först några minuter; webbens /api/health redovisar med flit ingen version.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

NYCKELFIL = re.compile(r"^[0-9a-f]{32}\.txt$")
ENDPOINT = "https://api.indexnow.org/indexnow"
ROT = Path(__file__).resolve().parents[1]
# Intl skriver tusentalet med hårt (U+00A0) eller smalt (U+202F) mellanslag.
MELLANSLAG = str.maketrans({chr(0xA0): " ", chr(0x202F): " "})


def _ur_kallan(rel: str, monster: str) -> list[str]:
    traffar = re.findall(monster, (ROT / rel).read_text(encoding="utf-8"), re.MULTILINE)
    if not traffar:
        sys.exit(f"Hittade inget som matchar {monster!r} i {rel}.")
    return traffar


# Den kanoniska adressen har ETT ställe (lib/kanonisk.ts); skriptet läser den därifrån.
VARD = _ur_kallan("lib/kanonisk.ts", r'KANONISK_ORIGIN = "https://([^"]+)"')[0]


def nyckel() -> str:
    filer = [p for p in (ROT / "public").iterdir() if NYCKELFIL.match(p.name)]
    if len(filer) != 1:
        sys.exit(f"Väntade exakt en IndexNow-nyckelfil i public/, hittade {len(filer)}.")
    return filer[0].stem


def adresser() -> list[str]:
    with urllib.request.urlopen(f"https://{VARD}/sitemap.xml", timeout=20) as svar:
        xml = svar.read().decode("utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    if not locs:
        sys.exit("Sitemapen var tom. Körs skriptet mot produktion?")
    return locs


def vantat_innehall() -> list[str]:
    """Det den nya versionens llms.txt måste innehålla: priserna och sökordssidorna."""
    priser = [f"{int(b):,}".replace(",", " ") + " kr" for b in _ur_kallan("lib/pricing.ts", r"prisPerManad:\s*(\d+)")]
    sidor = [f"https://{VARD}{vag}" for vag in _ur_kallan("lib/landningar.ts", r'^\s*vag: "(/[^"]+)"')]
    return priser + sidor


def vanta_pa_deploy(maxtid: int = 1800) -> None:
    vantat = vantat_innehall()
    slut = time.monotonic() + maxtid
    while True:
        try:
            with urllib.request.urlopen(f"https://{VARD}/llms.txt", timeout=20) as svar:
                text = svar.read().decode("utf-8").translate(MELLANSLAG)
            saknas = [v for v in vantat if v not in text]
        except OSError as fel:
            saknas = [f"(llms.txt svarade inte: {fel})"]
        if not saknas:
            print(f"Sajten visar den nya versionen ({len(vantat)} kontrollerade uppgifter).")
            return
        if time.monotonic() > slut:
            sys.exit(f"Sajten visar fortfarande inte {', '.join(saknas)} efter {maxtid // 60} min. Ingenting anmält.")
        print(f"Väntar på deployen, saknar {', '.join(saknas)}.")
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="skicka på riktigt")
    parser.add_argument(
        "--vanta-pa-deploy",
        action="store_true",
        help="vänta tills sajten visar priserna och sökordssidorna i koden",
    )
    args = parser.parse_args()

    if args.vanta_pa_deploy:
        vanta_pa_deploy()
    k = nyckel()
    urls = adresser()
    kropp = {"host": VARD, "key": k, "keyLocation": f"https://{VARD}/{k}.txt", "urlList": urls}

    # Nyckelfilen måste svara innan anmälan har någon verkan.
    try:
        with urllib.request.urlopen(kropp["keyLocation"], timeout=20) as svar:
            svarad = svar.read().decode("utf-8").strip()
    except OSError as fel:
        svarad = f"fel: {fel}"
    if svarad != k:
        sys.exit(f"{kropp['keyLocation']} svarar inte med nyckeln ({svarad[:60]}). Är filen deployad?")

    print(f"{len(urls)} adresser till {ENDPOINT}:")
    for url in urls:
        print(f"  {url}")
    if not args.apply:
        print("Torrkörning. Kör med --apply för att skicka.")
        return

    forfragan = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(kropp).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(forfragan, timeout=30) as svar:
        # 200 = mottaget, 202 = mottaget men nyckeln kontrolleras ännu.
        print(f"IndexNow svarade {svar.status}.")


if __name__ == "__main__":
    main()
