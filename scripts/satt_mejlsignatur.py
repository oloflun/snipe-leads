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
#: Sedan 2026-11-23 samma rader som Sebastians egen Gmail-signatur (Anton:
#: "ändra texten så att den överensstämmer med signaturen", med titeln
#: Grundare & VD): namn, titel, verksamhet, telefon, e-post, logga, ort, webb.
#: Ingen bolagsrad sist; den stod inte i hans signatur.
#:
#: KÖR INTE mot en miljö som saknar koden från 2026-11-23: äldre kod känner
#: igen det gamla blocket i köade utkast på titelraden, och ett titelbyte ger
#: då två signaturer i samma mejl (signatur._foraldrat_start rättar det).
STANDARD = {
    "namn": "Sebastian Bergman",
    "titel": "Grundare & VD",
    "verksamhet": "Snajp | AI för leads och kundtjänst",
    "telefon": "+46 70 360 05 64",
    "epost": "sebastian@snajp.se",
    "ort": "Umeå & Göteborg",
    "webb": "www.snajp.se",
}

FALT = (*STANDARD, "bolag", "logotyp_url")


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


def direkt(store: dict, env: str, slug: str, signatur: dict, *, apply: bool) -> int:
    """Samma byte rakt i databasen, för en miljö där tenantens nyckel inte
    finns i .env.deploy (main 2026-11-23: bytet blev liggande ett halvt dygn
    och 75 mejl gick ut med den gamla signaturen).

    Valideringen är API:ts egen (SignaturRequest) och bara nyckeln `signatur`
    i settings rörs, så resten av leads-inställningarna står orörda. Beviset
    är en ny läsning genom samma normalisering som sändvägen använder.
    """
    import psycopg2

    from railway_migrate import dsn

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "snajp-support"))
    from app.api.schemas import SignaturRequest
    from app.leads.signatur import bygg_signaturtext, normalisera

    varde = SignaturRequest(**signatur).model_dump(exclude_none=True)
    if normalisera(varde) is None and varde.get("aktiv") is not False:
        sys.exit("AVBRYTER: signaturen normaliseras till ingenting (namn saknas).")

    conn = psycopg2.connect(dsn(store, env), connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("select id from public.ss_tenants where slug = %s", (slug,))
        rad = cur.fetchone()
        if not rad:
            sys.exit(f"AVBRYTER: ingen tenant med sluggen {slug!r} i {env}.")
        tenant_id = rad[0]
        cur.execute(
            "select settings->'signatur' from public.agent_configs where tenant_id = %s and agent_type = 'leads'",
            (tenant_id,),
        )
        nuvarande = (cur.fetchone() or (None,))[0]
        print(f"miljö: {env}  tenant: {slug}  (direkt i databasen)")
        print("nuvarande:" if nuvarande else "nuvarande: (ingen signatur)")
        if nuvarande:
            print(json.dumps(nuvarande, ensure_ascii=False, indent=2))
        print("blir:")
        print(json.dumps(varde, ensure_ascii=False, indent=2))
        if not apply:
            conn.rollback()
            print("\nInget skrivet. Kör med --apply.")
            return 0
        ny = json.dumps(varde, ensure_ascii=False)
        cur.execute(
            """insert into public.agent_configs (tenant_id, agent_type, settings)
               values (%s, 'leads', jsonb_build_object('signatur', %s::jsonb))
               on conflict (tenant_id, agent_type)
               do update set settings = jsonb_set(coalesce(public.agent_configs.settings, '{}'::jsonb),
                                                  '{signatur}', %s::jsonb),
                             updated_at = now()""",
            (tenant_id, ny, ny),
        )
        conn.commit()
        cur.execute(
            "select settings->'signatur' from public.agent_configs where tenant_id = %s and agent_type = 'leads'",
            (tenant_id,),
        )
        kontroll = normalisera((cur.fetchone() or (None,))[0])
    finally:
        conn.close()
    if varde.get("aktiv") is False:
        print("\nVerifierat: signaturen är avstängd." if kontroll is None else "VARNING: signaturen läste tillbaka trots --av.")
        return 0 if kontroll is None else 1
    if not kontroll or kontroll.get("namn") != varde["namn"]:
        print("VARNING: signaturen läste inte tillbaka som väntat.")
        return 1
    print("\nVerifierat mot en ny läsning (normaliserat värde):")
    print(json.dumps(kontroll, ensure_ascii=False, indent=2))
    print("\nTextblocket i mejlen:")
    print(bygg_signaturtext(kontroll))
    if not kontroll.get("logotyp_url"):
        print("OBS: ingen logotyp_url i det sparade värdet — mejlen går utan logga.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="tenantens slug, t.ex. kund-7cea8ee9")
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--apply", action="store_true", help="skriv (annars visas bara planen)")
    ap.add_argument("--jag-menar-produktion", action="store_true")
    ap.add_argument("--av", action="store_true", help="stäng av signaturen (aktiv=false)")
    ap.add_argument(
        "--direkt", action="store_true",
        help="skriv i databasen i stället för via API:t (när tenantens nyckel saknas i .env.deploy)",
    )
    for falt in FALT:
        ap.add_argument("--" + falt.replace("_", "-"), default=None)
    args = ap.parse_args()

    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    web_url = store.get(f"{prefix}_WEB_URL", "").rstrip("/")
    signatur = {
        **STANDARD,
        **({"logotyp_url": f"{web_url}/epost/snajp-logga.png"} if web_url else {}),
        **{f: getattr(args, f) for f in FALT if getattr(args, f) is not None},
        "aktiv": not args.av,
    }
    if args.direkt:
        return direkt(store, args.env, args.slug, signatur, apply=args.apply)

    api_url = store.get(f"{prefix}_API_URL", "").rstrip("/")
    # Tenantens egen nyckel — /api/leads/config är tenant-scopad, inte admin.
    nyckelnamn = f"{prefix}_KEY_{args.slug.upper().replace('-', '_')}"
    nyckel = store.get(nyckelnamn)
    if not api_url or not nyckel:
        sys.exit(
            f"AVBRYTER: {prefix}_API_URL / {nyckelnamn} saknas i .env.deploy. "
            "Lägg till --direkt för att skriva i databasen i stället."
        )

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
