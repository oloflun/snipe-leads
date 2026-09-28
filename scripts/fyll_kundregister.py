#!/usr/bin/env python3
"""Fyll kundregistret för EN tenant — uppgifterna Iris måste ha för att få skicka.

    python scripts/fyll_kundregister.py --slug livrustning
    python scripts/fyll_kundregister.py --slug livrustning --apply
    python scripts/fyll_kundregister.py --slug x --env main --jag-menar-produktion --apply

## Varför skriptet finns

Kallmejlgrinden (app/leads/send_guard.py) har två krav som INTE är kodfrågor:
regel 1 vill se företagsnamn, organisationsnummer och postadress i sidfoten,
regel 2 en länk till avsändarens integritetspolicy. Saknas något byggs utkastet
inte ens (app/agent/leads_tools.py), och kunden ser ett blockerat utskick utan
att förstå varför.

Uppgifterna bor i `ss_customer_details` (migration 053 + 073) och fylls annars
för hand i admin under Kunder & Data. Det är en punktlista i ett dokument, och
punktlistor körs fel den dag det brådskar. Mätt 2026-09-20: kundregistret i
produktion var TOMT på alla fem tenants, alltså kunde ingen kund skicka ett
enda kallmejl.

## Vad skriptet med FLIT inte kan

`avtal_signerat` går inte att sätta härifrån, trots att fältet finns i samma
tabell. Det datumet är påståendet att ett personuppgiftsbiträdesavtal ÄR
signerat, och det ska registreras av en människa som sett avtalet — inte av
ett skript som kör med masternyckeln. Avtalsgrinden (app/avtalsgrind.py)
hänger på det fältet. Registrera det i admin under Kunder & Data.

## Vägen

Anropet går via admin-API:t (`PUT /api/admin/tenants/{id}/kunddata`), inte med
SQL mot tabellen: samma validering, samma normalisering och samma rad i
`platform_events` som när en människa sparar i admin. En direktskrivning hade
hoppat över alltihop.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

#: Fälten skriptet får sätta. `avtal_signerat` saknas med flit — se docstringen.
FALT = (
    "orgnr",
    "foretagsadress",
    "policy_url",
    "telefon",
    "faktureringsmejl",
    "faktureringsadress",
    "kund_sedan",
)


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
        sys.exit(f"AVBRYTER: {metod} kunddata svarade {fel.code}: {detalj}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="tenantens slug, t.ex. livrustning")
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--apply", action="store_true", help="skriv (annars visas bara planen)")
    ap.add_argument("--jag-menar-produktion", action="store_true")
    for falt in FALT:
        ap.add_argument("--" + falt.replace("_", "-"), default=None)
    args = ap.parse_args()

    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    api_url = store.get(f"{prefix}_API_URL", "").rstrip("/")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not api_url or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL / {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    # Sluggen slås upp mot databasen och inte mot API:t: tenant-id är det
    # endpointen tar, och en felstavad slug ska falla här och inte som en 404
    # med masternyckeln i handen.
    conn = psycopg2.connect(dsn(store, args.env), connect_timeout=20)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("select id, name from public.ss_tenants where slug = %s", (args.slug,))
    rad = cur.fetchone()
    conn.close()
    if not rad:
        sys.exit(f"AVBRYTER: ingen tenant med sluggen {args.slug!r} i {args.env}.")
    tenant_id, namn = rad

    nytt = {f: getattr(args, f) for f in FALT if getattr(args, f) is not None}
    if not nytt:
        print("Inga fält angivna. Ange minst ett, t.ex. --orgnr.")

    nuvarande = api_anrop(f"{api_url}/api/admin/tenants/{tenant_id}/kunddata", master, "GET")
    falt_nu = (nuvarande.get("kunddata") or {}).get("falt") or {}

    print(f"miljö: {args.env}")
    print(f"tenant: {namn}  slug={args.slug}")
    print()
    for falt in FALT:
        fore = (falt_nu.get(falt) or {}).get("varde")
        efter = nytt.get(falt)
        if efter is None:
            print(f"  {falt:20} {fore if fore else '(tomt)'}  — rörs inte")
        elif fore == efter:
            print(f"  {falt:20} {efter}  — redan satt")
        else:
            print(f"  {falt:20} {fore if fore else '(tomt)'}  ->  {efter}")

    # Grindens krav, sagt rakt ut: det är DE tre fälten som avgör om ett
    # kallmejl över huvud taget byggs.
    efter_allt = {f: nytt.get(f) or (falt_nu.get(f) or {}).get("varde") for f in FALT}
    saknas = [f for f in ("orgnr", "foretagsadress", "policy_url") if not efter_allt.get(f)]
    print()
    if saknas:
        print("Iris kan INTE skicka efteråt — saknas: " + ", ".join(saknas))
    else:
        print("Kallmejlgrindens krav uppfyllda (orgnr, foretagsadress, policy_url).")

    if not args.apply:
        print("\nInget skrivet. Kör med --apply.")
        return 0
    if not nytt:
        return 0

    svar = api_anrop(
        f"{api_url}/api/admin/tenants/{tenant_id}/kunddata", master, "PUT", nytt
    )
    print("\nSparat: " + ", ".join(svar.get("sparat") or []))

    # Beviset är en ny LÄSNING, inte att PUT:en svarade 200.
    kontroll = api_anrop(f"{api_url}/api/admin/tenants/{tenant_id}/kunddata", master, "GET")
    kvar = (kontroll.get("kunddata") or {}).get("falt") or {}
    fel = [f for f, v in nytt.items() if (kvar.get(f) or {}).get("varde") != v]
    if fel:
        print("VARNING: dessa fält läste inte tillbaka som väntat: " + ", ".join(fel))
        return 1
    print("Verifierat mot en ny läsning.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
