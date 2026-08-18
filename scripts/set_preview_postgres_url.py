#!/usr/bin/env python
"""Sätt PREVIEW_POSTGRES_URL i .env.deploy — lösenord via getpass.

Lösenordet läses från terminalens stdin med getpass (syns aldrig på skärmen,
hamnar aldrig i shell-historik eller i en sessionslogg) och verifieras mot
databasen innan det skrivs till .env.deploy. Körs av DIG i en egen terminal —
inte via Claude Code — så att hemligheten aldrig passerar chattkanalen.

    python scripts/set_preview_postgres_url.py

Var lösenordet finns: Supabase → projektet → Branches → development →
Database → Reset password. Det visas EN gång, direkt efter återställningen.

## Sessionsläge, inte transaktionsläge

Poolern har två portar och de beter sig olika:

  6543  transaktionsläge — sessionstillstånd överlever inte mellan satser
  5432  sessionsläge     — beter sig som en vanlig anslutning

`supabase_seed_dev.py` sätter `session_replication_role = replica` för att
stänga av främmande nycklar och triggern `on_auth_user_created` under
kopieringen. Det är en SESSIONSinställning: på 6543 kan den tappas mellan
satser, och speglingen skulle då fela mitt i med ett obegripligt FK-fel.

Därför provas 5432 FÖRST. 6543 finns kvar som reserv, med en varning, eftersom
en anslutning som fungerar halvvägs är bättre än ingen — men speglingen bör
köras mot 5432.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

import psycopg2

# Windows-konsolen kor cp1252 och kan INTE koda U+2192 (pilen). En print med
# ett sadant tecken kastar UnicodeEncodeError och dodar skriptet INNAN det
# hinner fraga efter nagot - exakt vad som hande 2026-08-18: kommandot kordes,
# gav en traceback, och .env.deploy forblev tom. Felet sag ut som om anvandaren
# aldrig kort kommandot.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"

#: Poolern, INTE direktvärden. Direktvärden (db.<ref>.supabase.co) är IPv6-only
#: och nås inte — samma fälla som DEPLOY.md fälla 3.
#:
#: Grenen ligger på aws-1, produktionen på aws-0. De går INTE att gissa till
#: varandra; uppmätt 2026-08-18, och ett fel här ser ut som fel lösenord.
HOST = "aws-1-eu-west-1.pooler.supabase.com"
DB = "postgres"
KEY = "PREVIEW_POSTGRES_URL"
REF = "eppgmjswfnrfwnqvtrge"

#: Sessionsläge först. Se modulens docstring.
PORTAR = (5432, 6543)

#: Poolern kräver `<roll>.<projektref>` som användarnamn. Speglingen behöver
#: postgres-rollen: snajp_app och snajp_web har medvetet inga rättigheter på
#: auth-schemat, och auth.users är just det som måste kopieras för att en
#: inloggning ska fungera i grenen.
ANVANDARE = (f"postgres.{REF}", "postgres")


def main() -> None:
    if not DEPLOY_ENV.exists():
        DEPLOY_ENV.write_text(
            "# Drift- och speglingsvariabler. GITIGNORERAD.\n", encoding="utf-8"
        )
        print(f"Skapade {DEPLOY_ENV.name}.")

    password = getpass.getpass("Databaslösenord för development-grenen (syns inte): ")
    if not password:
        sys.exit("Inget lösenord gavs.")

    dsn = None
    valdt_port = None
    senaste_fel = None
    fel_losenord = False

    for port in PORTAR:
        for user in ANVANDARE:
            kandidat = f"postgresql://{user}:{password}@{HOST}:{port}/{DB}"
            try:
                conn = psycopg2.connect(kandidat, connect_timeout=10)
                cur = conn.cursor()
                # Bevisa att rollen DUGER, inte bara att den kan ansluta.
                # snajp_app kan ansluta men får inte läsa auth — och en spegling
                # som faller på rättigheter efter halva kopieringen är värre än
                # en som aldrig startar.
                cur.execute("select current_user, (select count(*) from auth.users)")
                roll, antal = cur.fetchone()
                conn.close()
                dsn, valdt_port = kandidat, port
                print(f"OK: ansluten som {roll} på port {port}, auth.users = {antal}.")
                break
            except Exception as exc:  # noqa: BLE001
                text = str(exc).strip().split("\n")[0]
                if "password authentication failed" in text.lower():
                    fel_losenord = True
                senaste_fel = text
        if dsn:
            break

    if not dsn:
        if fel_losenord:
            sys.exit(
                "Fel lösenord. Värden svarar och känner igen projektet, så det är\n"
                "inte ett nätverks- eller konfigurationsfel.\n\n"
                "Hämta ett nytt: Supabase → Branches → development → Database →\n"
                "Reset password. Det visas bara en gång, direkt efter."
            )
        # Visa FÖRSTA raden av felet — den säger vad som gick fel, aldrig lösenordet.
        sys.exit(f"Kunde inte ansluta — {senaste_fel}.")

    if valdt_port != 5432:
        print(
            "VARNING: bara transaktionsläget (6543) svarade. Speglingen sätter\n"
            "         session_replication_role, som kan tappas där. Går den fel,\n"
            "         prova sessionsläget (5432) i Supabase-panelen."
        )

    rader = DEPLOY_ENV.read_text(encoding="utf-8").splitlines()
    rader = [r for r in rader if not r.startswith(f"{KEY}=")]
    rader.append(f"{KEY}={dsn}")
    DEPLOY_ENV.write_text("\n".join(rader) + "\n", encoding="utf-8")

    print(f"{KEY} skriven till {DEPLOY_ENV.name}. Lösenordet lämnade aldrig terminalen.")
    print("\nNästa steg — torrkörning först, den rör ingenting:")
    print("  snajp-support/.venv/Scripts/python.exe scripts/supabase_seed_dev.py")


if __name__ == "__main__":
    main()
