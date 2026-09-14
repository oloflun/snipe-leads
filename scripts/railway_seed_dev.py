#!/usr/bin/env python3
"""Spegla main → development. ENVÄGS, med tre spärrar mot att vändas.

    python scripts/railway_seed_dev.py            # visa vad som skulle kopieras
    python scripts/railway_seed_dev.py --apply    # kör speglingen

Motsvarar Supabase-grenens `--with-data`: development ska vara en 1:1-kopia av
main, så att en ändring kan utvärderas med allt annat lika. Skillnaden är att
Railways miljökloning ger tom infrastruktur — data måste kopieras separat, och
riktningen måste vara omöjlig att vända av misstag.

## Varför riktningen är farlig och hur den låses

Kunddata som testkörningar skapar i dev får ALDRIG nå main. Tre spärrar, inte
en konvention:

1. **Målet är hårdkodat** till `development`. Ingen `--target`-flagga finns;
   käll- och mål-DSN kommer ur miljönamn, inte ur argument.
2. **Markörtabellen `public.mirror_meta`.** Skriptet vägrar skriva till en
   databas vars markör inte säger `development`, och vägrar LÄSA från en som
   har en markörrad alls. Main saknar tabellen och blir därmed aldrig ett
   giltigt mål.
3. **INV-DATA-001** (statisk invariant): ingen kodväg i den här filen pekar
   målet mot main.

## Metod

Inga postgres-klientbinärer finns lokalt, så kopieringen sker med
`COPY ... (format binary)` via psycopg2:s `copy_expert` — strömmat, inga
temporära filer, fungerar på Windows.

`session_replication_role = replica` på målet stänger av både främmande nycklar
och triggern `on_auth_user_created` under kopieringen. Utan det skapar varje
kopierad `auth.users`-rad ett extra workspace, och FK-ordningen skulle tvinga
fram en topologisk sortering av 90 relationer.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway_provision import env_read  # noqa: E402
from railway_migrate import dsn  # noqa: E402

SOURCE_ENV = "main"
TARGET_ENV = "development"  # hårdkodat — spärr 1

MIRROR_META = """
create table if not exists public.mirror_meta (
  id boolean primary key default true,
  environment text not null,
  seeded_at timestamptz not null default now(),
  source_fingerprint text,
  constraint mirror_meta_singleton check (id)
);
"""


def tables(cur) -> list[str]:
    cur.execute("""select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
                   where n.nspname='public' and c.relkind='r' and c.relname <> 'mirror_meta'
                   order by c.relname""")
    return [r[0] for r in cur.fetchall()]


def migration_version(cur) -> str | None:
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='supabase_migrations' and table_name='schema_migrations')""")
    if not cur.fetchone()[0]:
        return None
    cur.execute("select max(version) from supabase_migrations.schema_migrations")
    return cur.fetchone()[0]


def assert_target_is_dev(cur) -> None:
    """Spärr 2, skrivsidan: målet måste bära dev-markören (eller sakna en helt)."""
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='public' and table_name='mirror_meta')""")
    if cur.fetchone()[0]:
        cur.execute("select environment from public.mirror_meta")
        row = cur.fetchone()
        if row and row[0] != TARGET_ENV:
            sys.exit(f"AVBRYT: målets mirror_meta säger {row[0]!r}, inte {TARGET_ENV!r}. "
                     f"Detta är inte development-databasen.")


def assert_source_is_main(cur) -> None:
    """Spärr 2, lässidan: källan får INTE ha en markör.

    En databas som någon gång speglats hit har en mirror_meta-rad. Att läsa från
    den betyder att spegla en spegel — och om någon av misstag pekat om DSN:erna
    är detta det som fångar det.
    """
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='public' and table_name='mirror_meta')""")
    if cur.fetchone()[0]:
        cur.execute("select count(*) from public.mirror_meta")
        if cur.fetchone()[0] > 0:
            sys.exit("AVBRYT: källan har en mirror_meta-rad — det är en spegel, inte main. "
                     "Att spegla från en spegel är alltid ett misstag.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    env = env_read()
    src = psycopg2.connect(dsn(env, SOURCE_ENV), connect_timeout=20)
    dst = psycopg2.connect(dsn(env, TARGET_ENV), connect_timeout=20)
    src.autocommit = False
    dst.autocommit = False
    sc, dc = src.cursor(), dst.cursor()

    # --- Spärrar innan något rörs
    assert_source_is_main(sc)
    dc.execute(MIRROR_META)
    dst.commit()
    assert_target_is_dev(dc)

    # --- Schemat måste stämma. En datakopia in i ett annat schema är värre än
    #     ingen kopia: den ser ut att lyckas och felar först vid läsning.
    sv, dv = migration_version(sc), migration_version(dc)
    if sv != dv:
        sys.exit(f"AVBRYT: schemaversionerna skiljer sig (main={sv}, development={dv}). "
                 f"Kör `python scripts/railway_migrate.py --env development --apply` först.")
    print(f"schemaversion: {sv} (matchar)")

    tbls = tables(sc)
    print(f"tabeller att spegla: {len(tbls)} + auth.users")

    if not args.apply:
        for t in tbls:
            sc.execute(f'select count(*) from public."{t}"')
            n = sc.fetchone()[0]
            if n:
                print(f"  {t}: {n}")
        sc.execute("select count(*) from auth.users")
        print(f"  auth.users: {sc.fetchone()[0]}")
        print("\nInget kopierat. Kör med --apply.")
        return 0

    # --- Replica-läge: FK och triggrar av under kopieringen
    dc.execute("set session_replication_role = replica")

    # Töm i omvänd ordning spelar ingen roll i replica-läge. auth.users först,
    # sedan publika.
    dc.execute("truncate table auth.users cascade")
    for t in tbls:
        dc.execute(f'truncate table public."{t}" cascade')

    def copy(cur_src, cur_dst, qualified: str) -> int:
        buf = io.BytesIO()
        cur_src.copy_expert(f"copy {qualified} to stdout (format binary)", buf)
        buf.seek(0)
        cur_dst.copy_expert(f"copy {qualified} from stdin (format binary)", buf)
        cur_src.execute(f"select count(*) from {qualified}")
        return cur_src.fetchone()[0]

    counts: dict[str, int] = {}
    counts["auth.users"] = copy(sc, dc, "auth.users")
    for t in tbls:
        counts[t] = copy(sc, dc, f'public."{t}"')

    # Sekvenser: sätt målets värde till källans, annars kolliderar nästa insert.
    sc.execute("""select sequencename from pg_sequences where schemaname='public'""")
    for (seq,) in sc.fetchall():
        sc.execute(f"select last_value, is_called from public.\"{seq}\"")
        last, called = sc.fetchone()
        dc.execute("select setval(%s, %s, %s)", (f"public.{seq}", last, called))

    # Markören SIST, så en avbruten körning inte lämnar en falsk "klar"-stämpel.
    sc.execute("select max(version) from supabase_migrations.schema_migrations")
    fingerprint = sc.fetchone()[0]
    dc.execute("delete from public.mirror_meta")
    dc.execute("insert into public.mirror_meta (environment, source_fingerprint) values (%s, %s)",
               (TARGET_ENV, fingerprint))

    dc.execute("set session_replication_role = origin")
    dst.commit()

    # --- Verifiera radantal mot källan. Skiljer något, rulla tillbaka intrycket.
    print("\nVerifierar radantal:")
    mismatches = 0
    for name, expected in counts.items():
        schema, tbl = name.split(".") if "." in name else ("public", name.strip('"'))
        dc.execute(f'select count(*) from {schema}."{tbl.strip(chr(34))}"' if schema == "auth"
                   else f'select count(*) from public."{tbl}"')
        got = dc.fetchone()[0]
        flag = "OK " if got == expected else "FEL"
        if got != expected:
            mismatches += 1
        if expected or got != expected:
            print(f"  {flag} {name}: {got}/{expected}")

    src.close(); dst.close()
    if mismatches:
        print(f"\n{mismatches} tabell(er) har fel radantal.")
        return 1
    print(f"\nSpegling klar. mirror_meta.environment = {TARGET_ENV}, fingerprint = {fingerprint}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
