#!/usr/bin/env python
"""Skapa snajp_web-rollen på preview-grenen (option B: public-grants, INTE auth).

Läser PREVIEW_POSTGRES_URL ur .env.deploy (postgres-rollen), skapar snajp_web
med ett slumpat lösenord och breda public-grants, och skriver den färdiga
snajp_web-DSN:n till .env.deploy. Lösenordet skrivs aldrig ut.
"""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"
REF = "eppgmjswfnrfwnqvtrge"
HOST = "aws-1-eu-west-1.pooler.supabase.com"
KEY = "PREVIEW_SNAJP_WEB_DATABASE_URL"


def read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def write_env(key: str, value: str) -> None:
    lines = DEPLOY_ENV.read_text(encoding="utf-8").splitlines()
    lines = [ln for ln in lines if not ln.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    DEPLOY_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    postgres_url = read_env(DEPLOY_ENV).get("PREVIEW_POSTGRES_URL", "")
    if not postgres_url:
        sys.exit("PREVIEW_POSTGRES_URL saknas i .env.deploy. Kör set_preview_postgres_url.py först.")

    password = secrets.token_urlsafe(24)
    conn = psycopg2.connect(postgres_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    # Rollen — nobypassrls, så den inte kringgår RLS.
    cur.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'snajp_web') THEN
            CREATE ROLE snajp_web WITH LOGIN NOBYPASSRLS;
          ELSE
            ALTER ROLE snajp_web WITH LOGIN NOBYPASSRLS;
          END IF;
        END $$;
        """
    )
    cur.execute("ALTER ROLE snajp_web WITH PASSWORD %s", (password,))

    # Public-grants (migration 030:s form, men UTAN auth.users — auth går via GoTrue).
    grants = [
        "GRANT USAGE ON SCHEMA public TO snajp_web",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO snajp_web",
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO snajp_web",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO snajp_web",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO snajp_web",
        "GRANT EXECUTE ON FUNCTION public.ensure_workspace_for_current_user() TO snajp_web",
        "GRANT EXECUTE ON FUNCTION public.current_workspace_id() TO snajp_web",
    ]
    for g in grants:
        cur.execute(g)
    conn.close()

    dsn = f"postgresql://snajp_web.{REF}:{password}@{HOST}:6543/postgres"
    write_env(KEY, dsn)

    print("OK: snajp_web skapad med public-grants; DSN skriven till .env.deploy.")


if __name__ == "__main__":
    main()
