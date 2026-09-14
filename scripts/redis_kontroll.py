#!/usr/bin/env python3
"""Kontrollera Redis Clouds konto — region och TLS per databas, i klartext.

    python scripts/redis_kontroll.py

Läser samma två kontonivå-nycklar som scripts/redis_cloud_nycklar.py sätter
(REDIS_CLOUD_API_KEY / REDIS_CLOUD_API_SECRET, ur .env.deploy) och listar
VARJE databas kontot har — både under vanliga prenumerationer
(`/v1/subscriptions`) och under Essentials-prenumerationer, som Redis Cloud
kallar "fixed" i själva API:et (`/v1/fixed/subscriptions`). De flesta konton
har bara den ena sorten; skriptet frågar båda och hanterar en tom eller
404:ad lista utan att larma om det — det är inte ett fel att sakna
Essentials-prenumerationer.

## Varför det här skriptet finns

Redis Cloud är ett underbiträde — support-agentens jobbkö (`REDIS_URL`, satt
av scripts/redis_konfig.py) kan bära kunddata i transit genom en extern
tjänst. Två fält avgör om det är juridiskt försvarbart, inte bara tekniskt
bekvämt:

- **Region.** Data som lämnar EU/EES är en tredjelandsöverföring — samma
  resonemang som stängde av DeepSeek för kunddata i CLAUDE.md, fast för
  infrastruktur i stället för en LLM-leverantör. En databas i `us-east-1`
  är inte en teknisk detalj, det är ett avtalsbrott som väntar på att hittas.
- **TLS.** Ett Redis-lösenord (`REDIS_URL`) går i klartext över nätet om
  anslutningen inte är krypterad — TLS av är samma sak som att skicka
  kunddata okrypterat mellan Railway och Redis Cloud.

Skriptet gissar aldrig. Saknar API-svaret ett TLS-fält skrivs "okänt" ut, inte
"av" eller "på" — en gissning i fel riktning är värre än ett hål i rapporten.
Ligger en databas i en region som inte börjar på "eu"/"europe" (eller saknar
regionfältet helt, vilket räknas som overifierat) avslutar skriptet med
exit 1: det ska synas som ett FEL i terminalen, inte som en rad bland andra
som är lätt att missa i en logg.

## Två svarsformer, samma kod

Redis Clouds egna exempel-payloads för `/databases` skiljer sig mellan
prenumerationstyperna: nyckeln `subscription` är en LISTA för vanliga
prenumerationer men ETT ENDA objekt för fixed/Essentials (verifierat mot
Redis Clouds egen OpenAPI-specifikation, inte gissat). Skriptet hanterar båda
formerna i stället för att anta den ena och krascha på den andra kontotypen.

Enbart läsande mot Redis Clouds API — skriptet varken skapar, ändrar eller
raderar något. TLS-toggle i konsolen (databasen -> Security -> TLS) och en
eventuell flytt eller nedstängning av en icke-EU-databas är Antons hand, inte
det här skriptets.
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

# Windows-konsolen kör cp1252 och kan inte koda alla tecken vi skriver ut.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_BAS = "https://api.redislabs.com/v1"
KONTO_NYCKEL = "REDIS_CLOUD_API_KEY"       # x-api-key
HEMLIG_NYCKEL = "REDIS_CLOUD_API_SECRET"   # x-api-secret-key

#: (etikett, bas-sökväg för prenumerationslistan). Essentials-planer heter
#: "fixed" i API:et, inte "essentials" — samma ord dashboarden döljer bakom
#: ett vänligare namn.
PRENUMERATIONSTYPER = (
    ("standard", "/subscriptions"),
    ("fixed (Essentials)", "/fixed/subscriptions"),
)


def _hämta(sökväg: str, konto: str, hemlig: str) -> tuple[int, dict | None, str]:
    """Ett GET mot Redis Clouds konto-API. Returnerar (statuskod, json-eller-None, rå text).

    Den råa texten skickas alltid med tillbaka, även vid fel — Redis Clouds
    egen felkropp är den enda pålitliga ledtråden när något går fel, en
    generisk gissning ("fel nyckelpar"?) kostar bara ett felsökningsvarv till.
    """
    req = urllib.request.Request(
        f"{API_BAS}{sökväg}",
        headers={
            "x-api-key": konto,
            "x-api-secret-key": hemlig,
            "Accept": "application/json",
            # Utan ett vanligt User-Agent skickar urllib "Python-urllib/3.x" —
            # en känd bot-signatur som Cloudflare (framför Redis Clouds API)
            # blockerar med "Error 1010" innan anropet ens når Redis.
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) snajp-redis-kontroll/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            råtext = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(råtext), råtext
            except json.JSONDecodeError:
                return resp.status, None, råtext
    except urllib.error.HTTPError as fel:
        råtext = fel.read().decode("utf-8", "replace")
        return fel.code, None, råtext
    except Exception as fel:  # noqa: BLE001
        return -1, None, f"{type(fel).__name__}: {str(fel)[:300]}"


def _databaser_ur_svar(data: dict) -> list[dict]:
    """Bänder ut databaslistan ur /databases-svaret.

    `subscription` är en LISTA i standard-svaret men ETT ENDA objekt i
    fixed-svaret (Redis Clouds egna exempel-payloads skiljer sig här) —
    hantera båda formerna i stället för att anta en och krascha på den andra.
    """
    if not isinstance(data, dict):
        return []
    sub = data.get("subscription")
    poster = sub if isinstance(sub, list) else [sub] if isinstance(sub, dict) else []
    databaser: list[dict] = []
    for post in poster:
        if isinstance(post, dict):
            for db in post.get("databases") or []:
                if isinstance(db, dict):
                    databaser.append(db)
    return databaser


def _tls_status(db: dict) -> str:
    """"på"/"av" om fältet finns, annars ärligt "okänt" — aldrig en gissning.

    Fältet heter `enableTls`, antingen direkt på databasobjektet eller under
    `security`. Essentials-planer (fixed) saknar det ofta helt i svaret —
    verifierat mot Redis Clouds eget exempel för en fixed-databas, som har
    ett `security`-objekt utan någon TLS-nyckel alls.
    """
    if "enableTls" in db:
        return "på" if db["enableTls"] else "av"
    security = db.get("security")
    if isinstance(security, dict) and "enableTls" in security:
        return "på" if security["enableTls"] else "av"
    return "okänt"


def _plan_sträng(db: dict) -> str:
    """Plan/minnesstorlek skrivs olika för Essentials (fixed) och Pro —
    visa fältet som faktiskt finns i stället för att tvinga fram ett format
    som passar ingen av dem."""
    if "planMemoryLimit" in db:
        enhet = db.get("memoryLimitMeasurementUnit", "")
        return f"{db['planMemoryLimit']} {enhet}".strip()
    if "memoryLimitInGb" in db:
        return f"{db['memoryLimitInGb']} GB"
    if "datasetSizeInGb" in db:
        return f"{db['datasetSizeInGb']} GB"
    return "okänt"


def _minnesanvändning(db: dict) -> str:
    if "memoryUsedInMb" in db:
        return f"{db['memoryUsedInMb']} MB"
    return "okänt"


def _är_eu_region(region: str) -> bool:
    return region.lower().startswith(("eu", "europe"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.parse_args()

    env = env_read()
    konto = env.get(KONTO_NYCKEL, "")
    hemlig = env.get(HEMLIG_NYCKEL, "")
    if not konto or not hemlig:
        print(f"  {KONTO_NYCKEL} / {HEMLIG_NYCKEL} saknas i .env.deploy.")
        print("  Kör scripts/redis_cloud_nycklar.py först.")
        return 1

    print("Redis Cloud — region och TLS per databas\n")

    icke_eu: list[str] = []
    http_fel = False
    någon_databas = False

    for etikett, bas_sökväg in PRENUMERATIONSTYPER:
        status, data, råtext = _hämta(bas_sökväg, konto, hemlig)
        if status == 404:
            print(f"[{etikett}] inga prenumerationer av den här typen (404 på {bas_sökväg}).")
            continue
        if status != 200 or data is None:
            print(f"[{etikett}] HTTP {status}: {(råtext or '(tomt svar)')[:500]}")
            http_fel = True
            continue

        subs = data.get("subscriptions") or []
        if not subs:
            print(f"[{etikett}] 0 prenumerationer.")
            continue

        for sub in subs:
            sub_id = sub.get("id")
            sub_namn = sub.get("name") or f"(id {sub_id})"
            print(f"\n[{etikett}] Prenumeration: {sub_namn} (id {sub_id})")
            if sub_id is None:
                print("    saknar id i svaret — kan inte hämta databaser, hoppar över.")
                continue

            db_status, db_data, db_råtext = _hämta(f"{bas_sökväg}/{sub_id}/databases", konto, hemlig)
            if db_status == 404:
                print("    inga databaser (404).")
                continue
            if db_status != 200 or db_data is None:
                print(f"    HTTP {db_status}: {(db_råtext or '(tomt svar)')[:500]}")
                http_fel = True
                continue

            databaser = _databaser_ur_svar(db_data)
            if not databaser:
                print("    0 databaser.")
                continue

            for db in databaser:
                någon_databas = True
                db_namn = db.get("name") or f"(databas {db.get('databaseId', '?')})"
                region = db.get("region") or "okänt"
                provider = db.get("provider") or "okänt"
                print(f"    - {db_namn}")
                print(f"        provider/region  : {provider} / {region}")
                print(f"        plan/minne       : {_plan_sträng(db)}")
                print(f"        TLS              : {_tls_status(db)}")
                print(f"        minnesanvändning : {_minnesanvändning(db)}")

                if not _är_eu_region(region):
                    icke_eu.append(
                        f"[{etikett}] {sub_namn} / {db_namn}: region={region!r}"
                    )

    print()
    if not någon_databas and not http_fel:
        print("Inga databaser hittades alls (varken standard eller fixed) — kontrollera")
        print("att nycklarna hör till rätt konto.")

    if icke_eu:
        print("FEL: följande databaser ligger UTANFÖR EU (eller har en overifierad region):")
        for rad in icke_eu:
            print(f"  - {rad}")
        print()
        print("Redis Cloud är underbiträde med kunddata i jobbkön (REDIS_URL) — en")
        print("icke-EU-region kräver samma SCC-bedömning som DeepSeek-spärren i CLAUDE.md.")
        print("Flytta databasen till en eu-region, eller stäng av kön mot den här databasen,")
        print("innan den används mot development eller main.")
        return 1

    if http_fel:
        print("Klart, men med minst ett HTTP-fel ovan — lita inte på listan förrän det felet")
        print("är förstått. Statuskod och felkropp står ovan (aldrig nycklarna).")
        return 1

    print("Klart. Inga databaser utanför EU hittades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
