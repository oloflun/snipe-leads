#!/usr/bin/env python3
"""DNS hos Loopia som ett kommando — inte som ett handgrepp i en kontrollpanel.

    python scripts/loopia_dns.py                 # visa nuvarande poster
    python scripts/loopia_dns.py --apply         # sätt www-CNAME mot Railway
    python scripts/loopia_dns.py --doman x.se --apply

## Varför skriptet finns

`www.snajp.se` är tillagd i Railway och väntar bara på en CNAME. Den posten
sattes annars för hand i Loopias kundzon, vilket gör den omöjlig att verifiera,
omöjlig att köra om och omöjlig att peka på i en handoff. Samma resonemang som
scripts/railway_doman.py: ett kommando som går att falsifiera slår en
punktlista varje gång.

## Det enda som inte går att automatisera

En LoopiaAPI-användare. Den skapas i kundzonen under
**Kontoinställningar -> LoopiaAPI** och är en egen inloggning, skild från
kontolösenordet. Lägg den i `.env.deploy` (gitignorerad):

    LOOPIA_API_USER=nagot@loopiaapi
    LOOPIA_API_PASSWORD=...

Det är ett kontolösenord och därför den enda delen som kräver dig. Allt efter
det sköter skriptet.

## Apex (snajp.se utan www)

Går INTE att peka på Railway, och det är inte en begränsning i skriptet:

  * En CNAME får enligt DNS-standarden inte samexistera med andra poster på
    samma namn, och apex MÅSTE ha NS och SOA. Därför krävs ALIAS/ANAME, som är
    en leverantörsspecifik utökning — Loopia har den inte.
  * Railways plan tillåter dessutom bara EN egen domän per tjänst, och den är
    använd av www.

Lösningen är Loopias egen webbvidarebefordran, `snajp.se` -> `https://www.snajp.se`.
Den ligger i kundzonen och exponeras inte i LoopiaAPI, så den punkten står kvar
som ett manuellt steg. Skriptet säger till om apex ser ut att peka fel.

Leakage-spärr: lösenordet läses ur .env.deploy och skrivs aldrig ut.
"""
from __future__ import annotations

import argparse
import sys
import xmlrpc.client
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read  # noqa: E402

ENDPOINT = "https://api.loopia.se/RPCSERV"

#: Railway-målet för www. Kommer ur `python scripts/railway_doman.py --env main`.
STANDARD_MAL = "2yamxcbe.up.railway.app"

#: Loopias parkeringsservrar. Pekar apex hit är domänen inte kopplad till oss.
PARKERING = {"194.9.94.85", "194.9.94.86"}


def klient() -> tuple[xmlrpc.client.ServerProxy, str, str] | None:
    """API-klienten, eller None när nycklar saknas.

    Returnerar None i stället för att avsluta. Skriptets första version dog här
    med en uppmaning att skapa en API-användare, och det var fel prioritering:
    målet är en DNS-post, inte ett API. Posten sätts på två minuter i kundzonen
    utan någon nyckel alls. API-användaren är värd besväret om man ska ändra DNS
    ofta — den är inte en förutsättning för att bli klar.

    Utan nycklar kör skriptet i KONTROLLÄGE: det säger exakt vilken post som ska
    sättas, och svarar på om den slagit igenom.
    """
    env = env_read()
    anv = env.get("LOOPIA_API_USER", "")
    los = env.get("LOOPIA_API_PASSWORD", "")
    if not anv or not los:
        return None
    # allow_none: Loopia svarar med nil i vissa fält.
    return xmlrpc.client.ServerProxy(uri=ENDPOINT, encoding="utf-8", allow_none=True), anv, los


def slar_upp(namn: str) -> list[str]:
    """A-posterna ett namn löser till. Tom lista om det inte löser alls."""
    import socket

    try:
        return sorted({t[4][0] for t in socket.getaddrinfo(namn, None, socket.AF_INET)})
    except OSError:
        return []


def kontrollera(doman: str, mal: str) -> int:
    """Utan API-nycklar: säg vad som ska göras, och om det redan är gjort."""
    www = f"www.{doman}"
    adresser = slar_upp(www)
    print(f"  {www:24} -> {', '.join(adresser) if adresser else '(löser inte)'}")

    klar = bool(adresser) and not (set(adresser) & PARKERING)
    if adresser and not klar:
        print(f"  {'':24}    Loopias parkering — posten är inte satt än")

    if klar:
        print()
        print("  Ser gjort ut. Bekräfta från Railways sida med:")
        print("    python scripts/railway_doman.py --env main")
        print("  Den skriver OK i stället för VÄNTAR när posten slagit igenom.")
        return 0

    print(f"""
  GÖR SÅ HÄR — två minuter, ingen API-nyckel behövs:

    1. Logga in på Loopias kundzon.
    2. Domännamn → {doman} → DNS-inställningar (Redigera zonfil).
    3. Vid underdomänen "www": TA BORT A-posterna som pekar på
       {', '.join(sorted(PARKERING))}, och lägg in en CNAME:

           Typ    CNAME
           Namn   www
           Värde  {mal}

       Alla poster på www måste bort först. En CNAME får enligt DNS-standarden
       inte samexistera med andra poster på samma namn, och en zon som bryter
       mot det löser olika beroende på vilken post resolvern råkar välja — ett
       fel som syns sporadiskt, inte direkt.

    4. Apex ({doman}) lämnas som den är. Lägg i stället en webbvidarebefordran
       {doman} → https://www.{doman}. Apex går inte att peka på Railway; se
       filens docstring om varför.

  Kör det här kommandot igen efteråt, så säger det till när posten slagit
  igenom. Vill du kunna göra det härifrån i framtiden: skapa en API-användare
  under Kontoinställningar → LoopiaAPI och lägg LOOPIA_API_USER och
  LOOPIA_API_PASSWORD i .env.deploy.""")
    return 0


def poster(api, anv, los, doman: str, under: str) -> list[dict]:
    """Zonposter för ett underdomännamn. `@` betyder apex."""
    try:
        return api.getZoneRecords(anv, los, doman, under)
    except xmlrpc.client.Fault as fel:
        sys.exit(f"LoopiaAPI avvisade anropet: {fel.faultString}")


def visa(api, anv, los, doman: str) -> None:
    for under in ("@", "www"):
        rader = poster(api, anv, los, doman, under)
        namn = doman if under == "@" else f"{under}.{doman}"
        if not rader:
            print(f"  {namn:24} (inga poster)")
            continue
        for r in rader:
            varde = str(r.get("rdata", "")).rstrip(".")
            flagga = ""
            if under == "@" and varde in PARKERING:
                flagga = "  <-- Loopias parkering, inte appen"
            if under == "www" and r.get("type") == "CNAME" and varde == STANDARD_MAL:
                flagga = "  <-- pekar rätt"
            print(f"  {namn:24} {r.get('type','?'):6} ttl={r.get('ttl','?'):<6} {varde}{flagga}")


def satt_www(api, anv, los, doman: str, mal: str, apply: bool) -> None:
    befintliga = poster(api, anv, los, doman, "www")

    ratt = [
        r for r in befintliga
        if r.get("type") == "CNAME" and str(r.get("rdata", "")).rstrip(".") == mal
    ]
    if ratt:
        print(f"  www.{doman} pekar redan på {mal} — inget att göra")
        return

    # Underdomänen måste finnas innan en post kan läggas där.
    try:
        if "www" not in api.getSubdomains(anv, los, doman):
            if apply:
                api.addSubdomain(anv, los, doman, "www")
                print(f"  skapade underdomänen www.{doman}")
            else:
                print(f"  SKULLE skapa underdomänen www.{doman}")
    except xmlrpc.client.Fault as fel:
        sys.exit(f"kunde inte läsa/skapa underdomän: {fel.faultString}")

    # Allt annat på www måste bort: en CNAME får inte samexistera med andra
    # poster på samma namn. Att lägga till utan att städa ger en zon som löser
    # olika beroende på vilken post resolvern råkar välja.
    for r in befintliga:
        if apply:
            api.removeZoneRecord(anv, los, doman, "www", r["record_id"])
            print(f"  tog bort {r.get('type')} {str(r.get('rdata','')).rstrip('.')}")
        else:
            print(f"  SKULLE ta bort {r.get('type')} {str(r.get('rdata','')).rstrip('.')}")

    ny = {"type": "CNAME", "ttl": 3600, "priority": 0, "rdata": mal}
    if apply:
        svar = api.addZoneRecord(anv, los, doman, "www", ny)
        print(f"  satte CNAME www.{doman} -> {mal}  ({svar})")
    else:
        print(f"  SKULLE sätta CNAME www.{doman} -> {mal}")


def apexrad(api, anv, los, doman: str) -> None:
    rader = poster(api, anv, los, doman, "@")
    varden = {str(r.get("rdata", "")).rstrip(".") for r in rader}
    if varden & PARKERING:
        print(
            f"\n  APEX: {doman} pekar på Loopias parkering.\n"
            "  Den går inte att peka på Railway — en CNAME får inte ligga på apex,\n"
            "  och Loopia har ingen ALIAS/ANAME. Lägg en webbvidarebefordran\n"
            f"  {doman} -> https://www.{doman} i kundzonen. Den finns inte i API:t."
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doman", default="snajp.se")
    ap.add_argument("--mal", default=STANDARD_MAL, help="Railway-målet för CNAME")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    uppkoppling = klient()

    # Utan nycklar: kontrolläge i stället för ett avbrott. Målet är en
    # DNS-post, och den går att sätta för hand på två minuter — se klient().
    if uppkoppling is None:
        print(f"domän: {args.doman}")
        print("läge: kontroll (inga LoopiaAPI-nycklar i .env.deploy)")
        print()
        return kontrollera(args.doman, args.mal)

    api, anv, los = uppkoppling

    print(f"domän: {args.doman}\nnuvarande poster:")
    visa(api, anv, los, args.doman)

    print("\nåtgärd:")
    satt_www(api, anv, los, args.doman, args.mal, args.apply)
    apexrad(api, anv, los, args.doman)

    if args.apply:
        print("\nefter ändringen:")
        visa(api, anv, los, args.doman)
        print("\nDNS sprider sig enligt TTL. Verifiera kopplingen med:")
        print("  python scripts/railway_doman.py --env main")
    else:
        print("\nInget ändrat. Kör med --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
