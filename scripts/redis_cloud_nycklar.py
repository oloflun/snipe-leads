#!/usr/bin/env python3
"""Redis Clouds KONTO-API in i .env.deploy — inte samma sak som en databas-URL.

    python scripts/redis_cloud_nycklar.py            # frågar efter båda nycklarna
    python scripts/redis_cloud_nycklar.py --kontroll # visar vad som är satt, skriver inget

## Två helt olika "Redis-nycklar" i den här kodbasen

`scripts/redis_konfig.py` sätter `REDIS_URL` — anslutningen till EN databas
(host, port, lösenord), det är vad `snajp-support` läser för att prata med
jobbkön. Det här skriptet sätter något annat: Redis Clouds **kontonivå-API**
(under "Team & API" i deras dashboard), två nycklar som tillsammans styr HELA
kontot — skapa/radera databaser, subscriptions, användare. Har du bara en
databas att koppla in är det `redis_konfig.py` du vill ha, inte det här.

Det här skriptet är förkravet för att provisionera FLER Redis-tjänster utan
att klicka igenom dashboarden för varje ny databas.

## Varför nycklarna ALDRIG tas som argument

Ett kommandoradsargument hamnar i skalets historik och i processlistan, där
det ligger kvar långt efter att fönstret stängts. `getpass` läser utan att
eka och utan att spara. Samma läckagespärr som CLAUDE.md beskriver: en `cat`
under felsökning läcker lika mycket som ett `echo`.

Skriptet testar nycklarna mot Redis Clouds riktiga API (`GET /v1/subscriptions`)
INNAN något sparas — ett sparat värde är inte ett verifierat värde.
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read, env_set  # noqa: E402

API_BAS = "https://api.redislabs.com/v1"
KONTO_NYCKEL = "REDIS_CLOUD_API_KEY"       # x-api-key
HEMLIG_NYCKEL = "REDIS_CLOUD_API_SECRET"   # x-api-secret-key


def visa(env: dict[str, str]) -> None:
    """Status utan att avslöja värdena. Längd + fyra sista räcker för att
    känna igen rätt uppgift; resten är onödig exponering i en loggad terminal."""
    for nyckel in (KONTO_NYCKEL, HEMLIG_NYCKEL):
        varde = env.get(nyckel, "")
        if not varde:
            print(f"  {nyckel:24} SAKNAS")
        else:
            print(f"  {nyckel:24} satt ({len(varde)} tecken, slutar …{varde[-4:]})")


def testa_nycklarna(konto: str, hemlig: str) -> tuple[bool, str]:
    """Ett riktigt anrop mot Redis Clouds API. Returnerar (ok, meddelande)."""
    req = urllib.request.Request(
        f"{API_BAS}/subscriptions",
        headers={
            "x-api-key": konto,
            "x-api-secret-key": hemlig,
            "Accept": "application/json",
            # Utan ett vanligt User-Agent skickar urllib "Python-urllib/3.x" —
            # en känd bot-signatur som Cloudflare (framför Redis Clouds API)
            # blockerar med "Error 1010" innan anropet ens når Redis. Verifierat:
            # samma nyckelpar gick igenom i Swagger UI (en webbläsare), inte här.
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) snajp-redis-konfig/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            antal = len(data.get("subscriptions", data if isinstance(data, list) else []))
            return True, f"Nycklarna fungerar — kontot har {antal} subscription(er) synliga via API:t."
    except urllib.error.HTTPError as fel:
        # Redis Clouds egen felkropp är den enda pålitliga ledtråden här —
        # en generisk "fel nyckelpar"-gissning gjorde två felsökningsvarv
        # längre än nödvändigt. Visa den alltid, oavsett statuskod.
        kropp = fel.read().decode("utf-8", "replace")[:300]
        return False, f"HTTP {fel.code}: {kropp or '(tomt svar)'}"
    except Exception as fel:  # noqa: BLE001
        return False, f"{type(fel).__name__}: {str(fel)[:200]}"


def main() -> int:
    p = argparse.ArgumentParser(description="Skriv Redis Clouds konto-API-nycklar till .env.deploy.")
    p.add_argument("--kontroll", action="store_true", help="visa status, skriv ingenting")
    args = p.parse_args()

    if args.kontroll:
        print("\n.env.deploy:")
        visa(env_read())
        return 0

    print("\nRedis Cloud konto-API -> .env.deploy (gitignorerad)")
    print("Skapas i dashboarden under Team & API -> API Keys (Account key + Secret key).\n")

    konto = getpass.getpass("Account key / x-api-key (visas inte): ").strip()
    if not konto:
        print("Avbrutet — ingen account key angiven.")
        return 1
    hemlig = getpass.getpass("Secret key / x-api-secret-key (visas inte): ").strip()
    if not hemlig:
        print("Avbrutet — ingen secret key angiven.")
        return 1

    print("\nTestar mot Redis Clouds API …")
    ok, meddelande = testa_nycklarna(konto, hemlig)
    print(f"  {meddelande}")
    if not ok:
        print("\nInget sparat.")
        return 1

    print()
    env_set(KONTO_NYCKEL, konto)
    env_set(HEMLIG_NYCKEL, hemlig)

    print("\nSparat. Kontroll (läser tillbaka ur filen):")
    visa(env_read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
