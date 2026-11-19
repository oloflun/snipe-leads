#!/usr/bin/env python3
"""Fyll kundregistret för EN tenant — uppgifterna Iris måste ha för att få skicka.

    python scripts/fyll_kundregister.py --slug livrustning
    python scripts/fyll_kundregister.py --slug livrustning --apply
    python scripts/fyll_kundregister.py --slug x --env main --jag-menar-produktion --apply

## Varför skriptet finns

Utskicksspärren (app/leads/send_guard.py) har två krav som hänger på
kundregistret och INTE är kodfrågor:

  * Regel 1 kräver företagsnamnet i sidfoten. Det är tenantens namn
    (`ss_tenants.name`); utan det byggs ingen fot (app/agent/leads_tools.py,
    `lagstadgad_fot`) och varje utskick blockeras.
  * Regel 2 kräver, vid utskick till en PERSONLIG adress, en länk till
    avsändarens integritetspolicy (`policy_url`). Utan den blockeras utskick
    till personliga adresser; info@ och kontakt@ går igenom.

Organisationsnummer och postadress stoppar ALDRIG ett utskick (Antons beslut
2026-10-10, docs/BESLUT.md). Foten tar med dem när de finns. De bör ändå fyllas
i: e-handelslagen ställer kravet på avsändaren, alltså kunden, och det är bara
här Snajp kan hjälpa kunden att uppfylla det.

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

#: Fält som inte spärrar men bör finnas: e-handelslagen kräver dem av
#: avsändaren, och utskicksfoten visar dem när de finns.
BOR_FYLLAS = ("orgnr", "foretagsadress")


def grindlage(foretagsnamn: str | None, falt: dict[str, str | None]) -> tuple[list[str], list[str]]:
    """(det som blockerar utskick, det som bör fyllas i) för ett ifyllt register.

    Speglar send_guard.py: regel 1 kräver bara företagsnamnet, regel 2
    policy_url vid personliga adresser. Org.nr och adress är aldrig en spärr.
    """
    blockerar: list[str] = []
    if not str(foretagsnamn or "").strip():
        blockerar.append("företagsnamn (tenantens namn) — regel 1 blockerar varje utskick")
    if not str(falt.get("policy_url") or "").strip():
        blockerar.append("policy_url — regel 2 blockerar utskick till personliga adresser")
    bor = [f for f in BOR_FYLLAS if not str(falt.get(f) or "").strip()]
    return blockerar, bor


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

    # Spärrens krav, sagt rakt ut och skilt från det som bara bör finnas.
    efter_allt = {f: nytt.get(f) or (falt_nu.get(f) or {}).get("varde") for f in FALT}
    blockerar, bor = grindlage(namn, efter_allt)
    print()
    if blockerar:
        print("Blockerar utskick efteråt:")
        for rad in blockerar:
            print(f"  - {rad}")
    else:
        print("Utskicksspärrens krav uppfyllda (företagsnamn, policy_url).")
    if bor:
        print(
            "Bör fyllas i: " + ", ".join(bor)
            + " — krävs av e-handelslagen och visas i sidfoten (ingen spärr)."
        )

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
