#!/usr/bin/env python3
"""Kör migrationskedjan mot Railway-Postgres — från noll, i ordning, en gång var.

    python scripts/railway_migrate.py            # visa vad som skulle köras
    python scripts/railway_migrate.py --apply

Ordningen är: railway/000_auth_compat.sql först (bygger auth-schemat och
rollerna som Supabase annars tillhandahåller), sedan supabase/migrations/*.sql
i filnamnsordning — OFÖRÄNDRADE. Att kedjan går att resa från noll är hela
poängen med 000_base_schema.sql, och det här skriptet är testet av det.

Liggaren heter `supabase_migrations.schema_migrations` med flit: samma namn som
Supabase använder, så att det är ETT begrepp och inte två. Två numreringssystem
i liggaren var en av de åtta infrastrukturfällorna.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPAT = REPO_ROOT / "railway" / "000_auth_compat.sql"
MIGRATIONS = REPO_ROOT / "supabase" / "migrations"

LEDGER = """
create schema if not exists supabase_migrations;
create table if not exists supabase_migrations.schema_migrations (
  version text primary key,
  name text,
  applied_at timestamptz not null default now()
);
"""


def dsn(env: dict[str, str], environment: str = "main") -> str:
    """Superuser-DSN (postgres-rollen) för migrationer, per miljö.

    Miljöprefixet (RAILWAY_MAIN_*, RAILWAY_DEVELOPMENT_*) är det som gör att
    `--env development` inte kan råka köra mot main-databasen. Faller tillbaka
    på de gamla omiljöade namnen bara för main, som redan kör med dem.
    """
    p = f"RAILWAY_{environment.upper()}_"
    pw = env.get(f"{p}PG_PASSWORD") or (env.get("RAILWAY_PG_PASSWORD") if environment == "main" else None)
    host = env.get(f"{p}PG_HOST") or (env.get("RAILWAY_PG_HOST") if environment == "main" else None)
    port = env.get(f"{p}PG_PORT") or (env.get("RAILWAY_PG_PORT") if environment == "main" else None)
    if not (pw and host and port):
        sys.exit(f"Saknar RAILWAY_{environment.upper()}_PG_{{PASSWORD,HOST,PORT}} i .env.deploy")
    return f"postgresql://postgres:{pw}@{host}:{port}/railway"


def planned() -> list[tuple[str, Path]]:
    items = [("000_auth_compat", COMPAT)]
    items += [(p.stem, p) for p in sorted(MIGRATIONS.glob("*.sql"))]
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--env", choices=("main", "development"), default="main",
                    help="vilken Railway-miljös databas (default: main)")
    ap.add_argument("--reset", action="store_true",
                    help="RADERAR public/auth/liggaren först. Bara mot Railway, aldrig mot produktion.")
    args = ap.parse_args()

    print(f"miljö: {args.env}")
    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()

    if args.reset:
        if not args.apply:
            sys.exit("--reset kräver --apply.")
        # Event-triggern överlever `drop schema` (den är databasglobal) och
        # skulle annars peka på en borttagen funktion.
        cur.execute("drop event trigger if exists ensure_rls")
        cur.execute("drop schema if exists public cascade")
        cur.execute("drop schema if exists auth cascade")
        cur.execute("drop schema if exists supabase_migrations cascade")
        cur.execute("create schema public")
        conn.commit()
        print("  ~ nollställt: public, auth, liggaren")

    cur.execute(LEDGER)
    conn.commit()

    cur.execute("select version from supabase_migrations.schema_migrations")
    done = {r[0] for r in cur.fetchall()}

    failures = 0
    for version, path in planned():
        if version in done:
            print(f"  = {version}")
            continue
        if not args.apply:
            print(f"  + {version} (skulle köras)")
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            cur.execute(sql)
            cur.execute(
                "insert into supabase_migrations.schema_migrations (version, name) values (%s, %s)",
                (version, path.name),
            )
            conn.commit()
            print(f"  + {version}")
        except Exception as exc:  # ponytail: första felet är det enda som betyder något
            conn.rollback()
            print(f"  ! {version} FAILED: {str(exc).strip()[:400]}")
            failures += 1
            break

    conn.close()
    if not args.apply:
        print("\nInget kört. Kör med --apply.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
