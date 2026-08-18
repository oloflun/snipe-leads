#!/usr/bin/env python
"""Sätt PREVIEW_POSTGRES_URL i .env.deploy — lösenord via getpass.

Lösenordet läses från terminalens stdin med getpass (syns aldrig på skärmen,
hamnar aldrig i shell-historik eller i en sessionslogg) och verifieras mot
databasen innan det skrivs till .env.deploy. Körs av DIG i en egen terminal —
inte via Claude Code — så att hemligheten aldrig passerar chattkanalen.

    python "C:\\Users\\Anton L\\snipe-leads\\scripts\\set_preview_postgres_url.py"
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"

#: Poolern, INTE direktvärden. Direktvärden (db.<ref>.supabase.co) är IPv6-only
#: och nås inte — samma fälla som DEPLOY.md fälla 3. Appen använder redan den
#: här poolern, så det är värdet som bevisligen fungerar.
HOST = "aws-1-eu-west-1.pooler.supabase.com"
PORT = 6543
DB = "postgres"
KEY = "PREVIEW_POSTGRES_URL"
REF = "eppgmjswfnrfwnqvtrge"


def main() -> None:
    if not DEPLOY_ENV.exists():
        sys.exit(".env.deploy finns inte — skapa den först.")

    password = getpass.getpass("Lösenord för preview-grenen (syns inte): ")
    if not password:
        sys.exit("Inget lösenord gavs.")

    # Poolern kräver `<roll>.<projektref>` som användarnamn. Testa både med och
    # utan ref — anslutningen verifieras, inte bara skriven.
    dsn = None
    last_error = None
    for user in (f"postgres.{REF}", "postgres"):
        candidate = f"postgresql://{user}:{password}@{HOST}:{PORT}/{DB}"
        try:
            conn = psycopg2.connect(candidate, connect_timeout=10)
            conn.close()
            dsn = candidate
            break
        except Exception as exc:
            last_error = exc

    if not dsn:
        # Visa FÖRSTA raden av felet — den säger "password authentication
        # failed" eller "connection refused", aldrig lösenordet.
        detail = ""
        if last_error:
            detail = " — " + str(last_error).strip().split("\n")[0]
        sys.exit(f"Kunde inte ansluta{detail}.")

    # Skriv in PREVIEW_POSTGRES_URL, behåll övriga rader.
    lines = DEPLOY_ENV.read_text(encoding="utf-8").splitlines()
    lines = [ln for ln in lines if not ln.startswith(f"{KEY}=")]
    lines.append(f"{KEY}={dsn}")
    DEPLOY_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("OK: anslutningen verifierad och PREVIEW_POSTGRES_URL skriven till .env.deploy.")


if __name__ == "__main__":
    main()
