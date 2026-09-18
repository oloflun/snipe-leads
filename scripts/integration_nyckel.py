#!/usr/bin/env python3
"""INTEGRATION_NYCKEL på Railway: skapa, kontrollera, aldrig visa.

    python scripts/integration_nyckel.py                         # torrkörning: läget i båda miljöerna
    python scripts/integration_nyckel.py --env development --apply

Nyckeln krypterar kundernas API-nycklar, MCP-tokens och kanalhemligheter
(snajp-support/app/integrationer/hemligheter.py, bd snipe-36u). Utan den går
inga hemligheter att spara i en miljö med riktig kunddata. Portalen svarar
då 503 med ett begripligt besked.

## Vad skriptet gör

  * Finns variabeln redan på api-tjänsten: ingenting, utom att visa ett
    fingeravtryck. Skriptet ersätter ALDRIG en befintlig nyckel. Då hade
    varje redan sparad hemlighet blivit oläsbar. Rotation görs för hand:
    lägg den nya FÖRST i listan ("ny,gammal"), så dekrypteras gamla värden
    fortfarande.
  * Saknas den: skapar en Fernet-nyckel lokalt, skriver den först som
    säkerhetskopia i .env.deploy (RAILWAY_<MILJÖ>_INTEGRATION_NYCKEL) och
    sedan till Railway. En nyckel som bara finns i Railway är en nyckel som
    försvinner med ett felklick i dashboarden.

Nyckeln skrivs aldrig ut, bara längd och en kort sha256 (samma fingeravtryck
som api_key_setup.py visar).

main: kräver `--env main` uttryckligen. Kör det när en release som bär
integrationerna går till produktion. Se CLAUDE.md om vem som beslutar det.
"""
from __future__ import annotations

import argparse
import sys

from cryptography.fernet import Fernet

from api_key_setup import ENV_DEPLOY, MILJOER, fingeravtryck, las_env_deploy, railway_variabler, satt_variabel

NAMN = "INTEGRATION_NYCKEL"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=tuple(MILJOER), action="append")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    miljoer = args.env or list(MILJOER)
    if args.apply and not args.env:
        sys.exit("--apply kräver --env: välj miljö uttryckligen.")

    lokalt = las_env_deploy()
    for miljo in miljoer:
        befintlig = railway_variabler(MILJOER[miljo]).get(NAMN, "")
        radnamn = f"RAILWAY_{miljo.upper()}_{NAMN}"
        kopia = lokalt.get(radnamn, "")
        if befintlig:
            status = "samma som kopian" if kopia == befintlig else (
                "SAKNAR kopia i .env.deploy" if not kopia else "SKILJER sig från kopian i .env.deploy"
            )
            print(f"{miljo}: finns ({fingeravtryck(befintlig)}), {status}")
            continue
        if not args.apply:
            print(f"{miljo}: saknas (skulle skapas med --env {miljo} --apply)")
            continue
        ny = Fernet.generate_key().decode("ascii")
        text = ENV_DEPLOY.read_text(encoding="utf-8")
        if f"{radnamn}=" in text and kopia:
            sys.exit(f"AVBRYTER: {radnamn} finns redan i .env.deploy men inte på Railway. Utred innan något skrivs.")
        rader = [r for r in text.splitlines() if not r.startswith(f"{radnamn}=")]
        rader.append(f"{radnamn}={ny}")
        ENV_DEPLOY.write_text("\n".join(rader) + "\n", encoding="utf-8")
        satt_variabel(MILJOER[miljo], NAMN, ny)
        kontroll = railway_variabler(MILJOER[miljo]).get(NAMN, "")
        if kontroll != ny:
            sys.exit(f"{miljo}: Railway visar inte den nya nyckeln efter skrivningen.")
        print(f"{miljo}: skapad ({fingeravtryck(ny)}), kopia i .env.deploy ({radnamn})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
