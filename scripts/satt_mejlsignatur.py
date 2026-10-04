#!/usr/bin/env python3
"""Sätt Iris mejlsignatur för EN tenant — blocket som läggs sist i varje
utgående leads-mejl (app/leads/signatur.py).

    python scripts/satt_mejlsignatur.py --slug kund-7cea8ee9
    python scripts/satt_mejlsignatur.py --slug kund-7cea8ee9 --apply
    python scripts/satt_mejlsignatur.py --slug x --env main --jag-menar-produktion --apply

## Varför skriptet finns

Signaturen bor i `agent_configs.settings["signatur"]` och sätts via
PUT /api/leads/config — en endpoint som kräver TENANTENS nyckel, inte
masterns. Utan skript hade rutinen varit "curl:a med nyckeln ur .env.deploy",
och det är exakt den sortens punktlista som ekar en hemlighet i ett skal.
Nyckeln läses här ur .env.deploy och skrivs aldrig ut.

Standardvärdena är Snajps egen signatur (beställd 2026-10-04, samma som
Gmail-signaturen för snajpsupport@gmail.com) — flaggorna finns för att sätta
en annan tenants. Logotypens URL byggs av miljöns WEB_URL om den inte anges:
PNG:n ligger i `public/epost/snajp-logga.png` och måste alltså vara DEPLOYAD
i miljön innan mottagare kan se den.

Vägen går via API:t, inte SQL: samma pydantic-validering (SignaturRequest)
och samma fältvisa sammanslagning som när UI:t sparar. En direktskrivning
hade kunnat lämna ett värde normaliseringen sedan tyst förkastar.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read  # noqa: E402

#: Snajps egen signatur — defaultvärdena. Ingen hemlighet någonstans här.
STANDARD = {
    "namn": "Sebastian Bergman",
    "titel": "Snajp Support | AI för leads och kundtjänst",
    "telefon": "+46 70 360 05 64",
    "epost": "snajpsupport@gmail.com",
    "ort": "Umeå & Göteborg",
    "webb": "www.snajp.se",
    "bolag": "Snajp AB",
}

FALT = (*STANDARD, "logotyp_url")


def api_anrop(url: str, nyckel: str, metod: str, kropp: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(kropp).encode() if kropp is not None else None,
        headers={"Content-Type": "application/json", "X-API-Key": nyckel},
        method=metod,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as svar:
            return json.load(svar)
    except urllib.error.HTTPError as fel:
        # Läs detaljen men eka aldrig kroppen — den speglar förfrågan.
        try:
            detalj = json.load(fel).get("detail", "")
        except Exception:  # noqa: BLE001
            detalj = ""
        sys.exit(f"AVBRYTER: {metod} /api/leads/config svarade {fel.code}: {detalj}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="tenantens slug, t.ex. kund-7cea8ee9")
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--apply", action="store_true", help="skriv (annars visas bara planen)")
    ap.add_argument("--jag-menar-produktion", action="store_true")
    ap.add_argument("--av", action="store_true", help="stäng av signaturen (aktiv=false)")
    for falt in FALT:
        ap.add_argument("--" + falt.replace("_", "-"), default=None)
    args = ap.parse_args()

    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    api_url = store.get(f"{prefix}_API_URL", "").rstrip("/")
    # Tenantens egen nyckel — /api/leads/config är tenant-scopad, inte admin.
    nyckelnamn = f"{prefix}_KEY_{args.slug.upper().replace('-', '_')}"
    nyckel = store.get(nyckelnamn)
    if not api_url or not nyckel:
        sys.exit(f"AVBRYTER: {prefix}_API_URL / {nyckelnamn} saknas i .env.deploy.")

    web_url = store.get(f"{prefix}_WEB_URL", "").rstrip("/")
    signatur = {
        **STANDARD,
        **({"logotyp_url": f"{web_url}/epost/snajp-logga.png"} if web_url else {}),
        **{f: getattr(args, f) for f in FALT if getattr(args, f) is not None},
        "aktiv": not args.av,
    }

    nuvarande = api_anrop(f"{api_url}/api/leads/config", nyckel, "GET").get("signatur")

    print(f"miljö: {args.env}  tenant: {args.slug}")
    print(f"nuvarande: {'(ingen signatur)' if not nuvarande else ''}")
    if nuvarande:
        print(json.dumps(nuvarande, ensure_ascii=False, indent=2))
    print("blir:")
    print(json.dumps(signatur, ensure_ascii=False, indent=2))

    if not args.apply:
        print("\nInget skrivet. Kör med --apply.")
        return 0

    api_anrop(f"{api_url}/api/leads/config", nyckel, "PUT", {"signatur": signatur})

    # Beviset är en ny LÄSNING av det normaliserade värdet — det köningen
    # faktiskt använder. En logotyp utan https hade t.ex. försvunnit här.
    kontroll = api_anrop(f"{api_url}/api/leads/config", nyckel, "GET").get("signatur")
    if args.av:
        if kontroll is not None:
            print("VARNING: signaturen läste tillbaka trots --av.")
            return 1
        print("\nVerifierat: signaturen är avstängd.")
        return 0
    if not kontroll or kontroll.get("namn") != signatur["namn"]:
        print("VARNING: signaturen läste inte tillbaka som väntat.")
        return 1
    print("\nVerifierat mot en ny läsning (normaliserat värde):")
    print(json.dumps(kontroll, ensure_ascii=False, indent=2))
    if not kontroll.get("logotyp_url"):
        print("OBS: ingen logotyp_url i det sparade värdet — mejlen går utan logga.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
