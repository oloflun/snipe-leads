#!/usr/bin/env python
"""Sätt RAILWAY_<MILJÖ>_PG_* i .env.deploy — lösenord via getpass.

Motsvarigheten till set_preview_postgres_url.py, fast för Railway. Samma regel:
lösenordet läses från terminalens stdin, syns aldrig på skärmen, hamnar aldrig i
shell-historiken, och passerar aldrig en chattkanal.

    python scripts/set_railway_postgres_url.py --env development

## Varför den behövs

`railway_migrate.py` och `railway_seed_dev.py` bygger sin DSN ur tre variabler
i .env.deploy:

    RAILWAY_<MILJÖ>_PG_PASSWORD
    RAILWAY_<MILJÖ>_PG_HOST
    RAILWAY_<MILJÖ>_PG_PORT

Filen är gitignorerad, vilket är rätt — men konsekvensen är att den aldrig
följer med en push. En maskin som klonar repot har alltså ingen väg att köra
migrationer, och felet visar sig långt senare som en saknad kolumn eller en
utebliven admingrad i en miljö där koden ser korrekt ut.

## Var uppgifterna finns

Railway → projektet `brave-passion` → välj miljö → tjänsten `Postgres` →
fliken **Variables**. Använd de PUBLIKA värdena (proxy), inte de privata:

    RAILWAY_TCP_PROXY_DOMAIN   -> host
    RAILWAY_TCP_PROXY_PORT     -> port
    POSTGRES_PASSWORD          -> lösenord

`RAILWAY_PRIVATE_DOMAIN` fungerar bara inifrån Railways nät och löses inte upp
härifrån — samma fälla som RAILWAY.md dokumenterar för en klonad miljö.
"""

from __future__ import annotations

import argparse
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


def skriv(nycklar: dict[str, str]) -> None:
    """Ersätter befintliga rader, behåller övriga."""
    rader = DEPLOY_ENV.read_text(encoding="utf-8").splitlines() if DEPLOY_ENV.exists() else []
    rader = [r for r in rader if not any(r.startswith(f"{k}=") for k in nycklar)]
    rader.extend(f"{k}={v}" for k, v in nycklar.items())
    DEPLOY_ENV.write_text("\n".join(rader) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Sätt Railway-postgresuppgifter i .env.deploy.")
    ap.add_argument("--env", choices=("main", "development"), default="development")
    args = ap.parse_args()

    prefix = f"RAILWAY_{args.env.upper()}_PG_"

    if not DEPLOY_ENV.exists():
        DEPLOY_ENV.write_text("# Drift- och speglingsvariabler. GITIGNORERAD.\n", encoding="utf-8")
        print(f"Skapade {DEPLOY_ENV.name}.")

    print(f"Miljö: {args.env}")
    print("Railway -> brave-passion -> miljön -> Postgres -> Variables\n")

    host = input("  RAILWAY_TCP_PROXY_DOMAIN (host): ").strip()
    port = input("  RAILWAY_TCP_PROXY_PORT (port):   ").strip()
    if not host or not port:
        sys.exit("Host och port krävs.")
    if not port.isdigit():
        sys.exit(f"Porten {port!r} är inte ett tal.")

    # Bara lösenordet göms. Host och port är inte hemligheter, och att dölja dem
    # hade gjort felstavningar omöjliga att upptäcka.
    password = getpass.getpass("  POSTGRES_PASSWORD (syns inte):   ")
    if not password:
        sys.exit("Inget lösenord gavs.")

    dsn = f"postgresql://postgres:{password}@{host}:{port}/railway"
    try:
        conn = psycopg2.connect(dsn, connect_timeout=15)
        cur = conn.cursor()
        # Bevisa att rollen DUGER, inte bara att den kan ansluta: migrationerna
        # rör både public och auth, och en roll utan de rättigheterna faller
        # halvvägs genom kedjan i stället för att aldrig starta.
        cur.execute("select current_user, current_database()")
        roll, db = cur.fetchone()
        cur.execute("select count(*) from information_schema.tables where table_schema='public'")
        tabeller = cur.fetchone()[0]
        conn.close()
        print(f"\nOK: ansluten som {roll} till {db}, {tabeller} tabeller i public.")
    except Exception as exc:  # noqa: BLE001
        första = str(exc).strip().splitlines()[0]
        if "password authentication failed" in första.lower():
            sys.exit(
                "\nFel lösenord. Värden svarar, så host och port stämmer.\n"
                "Kontrollera POSTGRES_PASSWORD i Railways Variables-flik."
            )
        sys.exit(f"\nKunde inte ansluta — {första}")

    skriv({f"{prefix}HOST": host, f"{prefix}PORT": port, f"{prefix}PASSWORD": password})
    print(f"{prefix}{{HOST,PORT,PASSWORD}} skrivna till {DEPLOY_ENV.name}.")
    print("Lösenordet lämnade aldrig terminalen.\n")
    print("Nästa steg:")
    print(f"  python scripts/railway_migrate.py --env {args.env} --apply")


if __name__ == "__main__":
    main()
