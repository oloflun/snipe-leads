#!/usr/bin/env python3
"""Koppla tjänsten synk (Railway-miljön main) till databaserna. Ägarens handgrepp.

    python scripts/railway_synk_anslut.py            # visa läget, ändra inget
    python scripts/railway_synk_anslut.py --apply    # nytt lösenord för synk_las + tjänstens variabler
    python scripts/railway_synk_anslut.py --stang    # synk_las kan inte längre logga in (backning)

docs/compliance/synkflytt-runbook.md, steg 6. Förutsätter att migration 122
(rollen synk_las) har körts i main, att tjänsten `synk` finns i miljön main,
och att .env.deploy har RAILWAY_MAIN_PG_* och RAILWAY_DEVELOPMENT_PG_* (mains
port är fortfarande öppen när det här körs).

--apply gör, i en transaktion mot main:
  1. ett nytt slumpat lösenord för synk_las, och inloggning på (bara i main;
     i development förblir rollen utan inloggning),
  2. tjänstens två variabler: SYNK_MAIN_PG_URL (synk_las över mains privata
     nät) och SYNK_DEVELOPMENT_PG_URL (postgres över developments publika port,
     sslmode=require),
  3. commit först när variablerna är skrivna, så att rollens lösenord och
     variabeln aldrig skiljer sig.

Lösenordet skapas här, går direkt till databasen och till Railway, och skrivs
aldrig ut, aldrig till .env.deploy och aldrig som argument. Ägaren förseglar
variablerna i Railways gränssnitt efteråt (Seal), vilket API:t inte kan.
Satsen körs med log_statement = 'none', så att lösenordet inte hamnar i
databasens logg.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import (  # noqa: E402
    env_read, envs_by_name, instance, read_vars, services_by_name, set_vars, state,
)
from railway_synk import MAIN, URL_DEV, URL_MAIN, kontrollera_anslutningar  # noqa: E402

TJANST = "synk"
ROLL = "synk_las"
#: Mains Postgres på mains privata nät (samma värdnamn som api:s DATABASE_URL).
MAIN_PRIVAT = "postgres.railway.internal:5432"


def urls(store: dict[str, str], losen: str) -> dict[str, str]:
    """Ren funktion: tjänstens två variabler. Prövas mot synkens egna spärrar
    innan något skrivs."""
    pw, host, port = (store.get(f"RAILWAY_DEVELOPMENT_PG_{n}") for n in ("PASSWORD", "HOST", "PORT"))
    if not (pw and host and port):
        sys.exit("Saknar RAILWAY_DEVELOPMENT_PG_{PASSWORD,HOST,PORT} i .env.deploy.")
    varden = {
        URL_MAIN: f"postgresql://{ROLL}:{quote(losen, safe='')}@{MAIN_PRIVAT}/railway",
        URL_DEV: f"postgresql://postgres:{quote(pw, safe='')}@{host}:{port}/railway?sslmode=require",
    }
    kontrollera_anslutningar(varden[URL_MAIN], varden[URL_DEV], railway=True, forsta=False, miljo=MAIN)
    return varden


def main() -> int:
    ap = argparse.ArgumentParser()
    grupp = ap.add_mutually_exclusive_group()
    grupp.add_argument("--apply", action="store_true")
    grupp.add_argument("--stang", action="store_true")
    args = ap.parse_args()

    store = env_read()
    conn = psycopg2.connect(dsn(store, MAIN), connect_timeout=20)
    cur = conn.cursor()
    cur.execute("select to_regclass('public.mirror_meta') is not null")
    if cur.fetchone()[0]:
        cur.execute("select count(*) from public.mirror_meta")
        if cur.fetchone()[0]:
            sys.exit("AVBRYT: databasen har en spegelmarkör. Det är inte main.")
    cur.execute("select rolcanlogin from pg_roles where rolname = %s", (ROLL,))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYT: rollen {ROLL} saknas i main. Migration 122 har inte körts där (release).")
    print(f"{ROLL} i main: {'kan logga in' if rad[0] else 'utan inloggning'}")

    project = state()
    env_id = envs_by_name(project).get(MAIN)
    tjanst = services_by_name(project).get(TJANST)
    if not env_id or not tjanst or not instance(tjanst, env_id):
        sys.exit(f"AVBRYT: tjänsten {TJANST} finns inte i miljön {MAIN}. Skapa den först (runbooken, steg 6).")
    satta = read_vars(tjanst["id"], env_id)
    print(f"{TJANST} i {MAIN}: " + ", ".join(f"{n} {'satt' if satta.get(n) else 'saknas'}" for n in (URL_MAIN, URL_DEV)))

    if args.stang:
        cur.execute(f"alter role {ROLL} with nologin")
        conn.commit()
        print(f"{ROLL} i main: utan inloggning. Synken hos Railway avbryter vid nästa körning.")
        return 0
    if not args.apply:
        print("\nInget ändrat. Kör med --apply.")
        return 0

    losen = secrets.token_urlsafe(32)
    varden = urls(store, losen)
    cur.execute("set local log_statement = 'none'")
    cur.execute(f"alter role {ROLL} with login password %s", (losen,))
    set_vars(tjanst["id"], env_id, varden)  # skriver bara namnen
    conn.commit()
    print(f"{ROLL} i main: inloggning på, nytt lösenord ({len(losen)} tecken). "
          "Försegla de två variablerna i Railways gränssnitt (Seal).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
