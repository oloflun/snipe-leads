#!/usr/bin/env python
"""Adressen i mejlens länkar: avregistrering, demolänk och länkar in i Snajp.

    python scripts/publik_bas_url.py                                   # visa läget
    python scripts/publik_bas_url.py --env main --satt https://www.snajp.se          # torrkörning
    python scripts/publik_bas_url.py --env main --satt https://www.snajp.se --apply  # byt

## Varför skriptet finns

Avregistreringslänken i varje utskick byggs ur `PUBLIC_BASE_URL` på tjänsten
`api` (snajp-support/app/config.py: publik_bas_url, app/leads/utskicksfot.py).
I main stod den på Railways egen adress, så mottagaren såg
`web-production-1fe2c.up.railway.app/avregistrera/…` under ett mejl från
Snajp (Anton 2026-11-23: "skapa även en clean adress för avregistrering").
En okänd värddomän i ett kallt mejl är dessutom en skräppostsignal.

Samma webbapp svarar på kundens egen domän, så bytet är en variabel och ingen
ny kod. Foten byggs om med den aktuella adressen när ett utkast godkänns och
igen när det skickas (leads_tools.lagstadgad_fot, byt_fot), så även utkast
som redan står i kön får den nya adressen. Länkar i mejl som redan gått ut
pekar kvar på Railway-adressen och fortsätter fungera: token är densamma och
appen svarar på båda domänerna.

## Kontrollen före bytet

`--satt` prövar först att `<adress>/avregistrera/<nollor>` svarar 200 med
avregistreringssidan. En adress som inte bär appen hade gett varje mottagare
en död avregistreringslänk, vilket är värre än en ful.

Bytet startar om tjänsten `api` i miljön. Det kräver `--apply`, och mot main
Antons ord (projektregeln om produktionen).
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_env_bootstrap import service_vars  # noqa: E402
from railway_provision import ENVIRONMENTS, envs_by_name, services_by_name, set_vars, state  # noqa: E402

VARIABEL = "PUBLIC_BASE_URL"
TJANST = "api"
#: En token som aldrig finns: sidan ska ändå svara, med avregistreringsvyn.
PROVVAG = "/avregistrera/" + "0" * 32


def svarar(bas_url: str) -> tuple[bool, str]:
    """(ok, besked): bär adressen webbappens avregistreringssida?"""
    url = bas_url.rstrip("/") + PROVVAG
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "snajp-kontroll"}), timeout=20) as svar:
            kropp = svar.read(200_000).decode("utf-8", "replace")
            if svar.status == 200 and "vregistrera" in kropp:
                return True, f"{url} svarar 200 med avregistreringssidan"
            return False, f"{url} svarar {svar.status} utan avregistreringssidan"
    except Exception as fel:  # noqa: BLE001 — varje fel är ett nej
        return False, f"{url} gick inte att nå: {fel}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--env", choices=ENVIRONMENTS, help="en miljö; utan: alla")
    parser.add_argument("--satt", metavar="URL", help="ny adress, t.ex. https://www.snajp.se")
    parser.add_argument("--apply", action="store_true", help="skriv ändringen (annars torrkörning)")
    args = parser.parse_args()

    projekt = state()
    miljoer = envs_by_name(projekt)
    tjanst = services_by_name(projekt)[TJANST]
    for namn in ([args.env] if args.env else list(ENVIRONMENTS)):
        nu = service_vars(tjanst["id"], miljoer[namn]).get(VARIABEL, "")
        print(f"{namn}: {VARIABEL}={nu!r}")

    if not args.satt:
        return 0
    if not args.env:
        print("AVBRYTER: --satt kräver --env.")
        return 2
    ny = args.satt.rstrip("/")
    if not ny.startswith("https://"):
        print("AVBRYTER: adressen ska börja med https://.")
        return 2
    ok, besked = svarar(ny)
    print(besked)
    if not ok:
        print("AVBRYTER: adressen bär inte avregistreringssidan. Ingenting ändrat.")
        return 1
    if not args.apply:
        print(f"TORRKÖRNING: {args.env} skulle få {VARIABEL}={ny!r} och api startas om. Lägg till --apply.")
        return 0
    set_vars(tjanst["id"], miljoer[args.env], {VARIABEL: ny})
    print(f"{args.env}: {VARIABEL}={ny!r}. Tjänsten api startar om; kör skriptet igen för att se läget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
