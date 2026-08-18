#!/usr/bin/env python3
"""Spegla Supabase produktion → development-grenen. ENVÄGS, med fyra spärrar.

    python scripts/supabase_seed_dev.py            # visa vad som skulle kopieras
    python scripts/supabase_seed_dev.py --apply    # kör speglingen

## Varför den här filen finns

Supabase-grenar skapas med `--with-data`, vilket är en ENGÅNGSKOPIA som fryses
i det ögonblick grenen skapas. Den är alltså ingen spegel: allt som händer i
produktionen efteråt saknas.

Det kostade en hel felsökningskväll. Preview-grenen klonades 2026-08-15 21:25;
kontot `snajpsupport@gmail.com` skapades i produktionen 2026-08-17 10:44. Grenen
kunde därför varken logga in kontot eller visa `/admin`, eftersom
`platform_admins` slås upp på ett användar-id som inte fanns där. Symptomen såg
ut som två skilda buggar — trasig inloggning och en 404 — men var samma sak:
databasen var två dagar gammal.

Railway löste det med `railway_seed_dev.py`. Det här är samma metod mot Supabase.
Ändras den ena bör den andra läsas om.

## Riktningen är det farliga, och den är låst i fyra lager

Kunddata som testkörningar skapar i development får ALDRIG nå produktionen.
Spärrarna är inte en konvention utan kod:

1. **Målet är hårdkodat** till `TARGET_REF`. Ingen `--target`-flagga finns, och
   käll- och mål-DSN läses ur skilda, namngivna miljövariabler.
2. **Projekt-ref kontrolleras mot DSN:en.** Käll-DSN måste innehålla
   produktionens ref och mål-DSN grenens. En omkastad `.env.deploy` fångas här,
   före första skrivningen.
3. **Markörtabellen `public.mirror_meta`.** Skriptet vägrar skriva till en
   databas vars markör inte säger `development`, och vägrar LÄSA från en som har
   en markörrad alls — att spegla en spegel är alltid ett misstag.
4. **INV-DATA-002** (statisk invariant): ingen kodväg i den här filen pekar
   målet mot produktionen.

Det finns ingen väg tillbaka. Strukturella ändringar går till produktionen via
`supabase/migrations/` och en merge till `main` — aldrig via data.

## Vad som ÖVERLEVER speglingen

Speglingen truncar målet. Rader som listas i `public.dev_persistent` sparas
undan före truncate och spelas tillbaka efteråt med `on conflict do nothing`, så
att en produktionsrad med samma id alltid vinner. Det är där admin-körningar
gjorda i development hör hemma: de ska finnas kvar mellan speglingar, men de
ska aldrig kunna vandra åt andra hållet.

## Metod

Inga postgres-klientbinärer krävs: kopieringen sker med
`COPY ... (format binary)` via psycopg2:s `copy_expert` — strömmat, inga
temporära filer, fungerar på Windows.

`session_replication_role = replica` på målet stänger av både främmande nycklar
och triggern `on_auth_user_created` under kopieringen. Utan det skapar varje
kopierad `auth.users`-rad ett extra workspace, och FK-ordningen skulle tvinga
fram en topologisk sortering av hela schemat.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

import psycopg2

# Spärr 1: målet är hårdkodat. Ingen flagga, ingen härledning ur argument.
SOURCE_REF = "spsmblyvasagpekjmgmf"  # produktion
TARGET_REF = "eppgmjswfnrfwnqvtrge"  # development-grenen
TARGET_ENV = "development"

SOURCE_ENV_VAR = "PRODUCTION_POSTGRES_URL"
TARGET_ENV_VAR = "PREVIEW_POSTGRES_URL"

#: Auth-tabeller som måste följa med för att en inloggning ska fungera.
#: `users` bär identiteten och lösenordshashen; `identities` bär OAuth-kopplingen.
#: Övriga (sessions, refresh_tokens) kopieras medvetet INTE — en session från
#: produktionen ska inte vara giltig i development.
AUTH_TABLES = ("users", "identities")

MIRROR_META = """
create table if not exists public.mirror_meta (
  id boolean primary key default true,
  environment text not null,
  seeded_at timestamptz not null default now(),
  source_fingerprint text,
  constraint mirror_meta_singleton check (id)
);
"""

DEV_PERSISTENT = """
create table if not exists public.dev_persistent (
  table_name text not null,
  row_id uuid not null,
  note text,
  created_at timestamptz not null default now(),
  primary key (table_name, row_id)
);
comment on table public.dev_persistent is
  'Rader som ska överleva speglingen. Finns BARA i development.';
"""


def env_read(path: Path) -> dict[str, str]:
    """Läser .env.deploy. Ingen dotenv-dependens; filen är enkel med flit."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def dsn_for(values: dict[str, str], var: str) -> str:
    dsn = os.environ.get(var) or values.get(var, "")
    if not dsn:
        sys.exit(
            f"AVBRYT: {var} saknas. Lägg den i .env.deploy eller i miljön.\n"
            f"Den ska vara postgres-anslutningen (pooler), inte projekt-URL:en."
        )
    return dsn


def assert_refs(source_dsn: str, target_dsn: str) -> None:
    """Spärr 2: DSN:erna måste peka på de projekt vi tror.

    En omkastad .env.deploy är det enda realistiska sättet att av misstag få
    produktionen som MÅL, och det fångas här — före första skrivningen.
    """
    if SOURCE_REF not in source_dsn:
        sys.exit(f"AVBRYT: {SOURCE_ENV_VAR} pekar inte på produktionen ({SOURCE_REF}).")
    if TARGET_REF not in target_dsn:
        sys.exit(f"AVBRYT: {TARGET_ENV_VAR} pekar inte på development-grenen ({TARGET_REF}).")
    if SOURCE_REF in target_dsn:
        sys.exit(
            f"AVBRYT: målet innehåller produktionens ref ({SOURCE_REF}). "
            f"Detta hade skrivit över produktionen."
        )


def assert_target_is_dev(cur) -> None:
    """Spärr 3, skrivsidan: målet måste bära dev-markören (eller sakna en helt)."""
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='public' and table_name='mirror_meta')""")
    if cur.fetchone()[0]:
        cur.execute("select environment from public.mirror_meta")
        row = cur.fetchone()
        if row and row[0] != TARGET_ENV:
            sys.exit(
                f"AVBRYT: målets mirror_meta säger {row[0]!r}, inte {TARGET_ENV!r}. "
                f"Detta är inte development-databasen."
            )


def assert_source_is_production(cur) -> None:
    """Spärr 3, lässidan: källan får INTE ha en markör.

    En databas som någon gång speglats hit har en mirror_meta-rad. Att läsa från
    den betyder att spegla en spegel — och om någon pekat om DSN:erna är detta
    det som fångar det.
    """
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='public' and table_name='mirror_meta')""")
    if cur.fetchone()[0]:
        cur.execute("select count(*) from public.mirror_meta")
        if cur.fetchone()[0] > 0:
            sys.exit(
                "AVBRYT: källan har en mirror_meta-rad — det är en spegel, inte "
                "produktionen. Att spegla från en spegel är alltid ett misstag."
            )


def public_tables(cur) -> list[str]:
    cur.execute("""select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
                   where n.nspname='public' and c.relkind='r'
                     and c.relname not in ('mirror_meta','dev_persistent')
                   order by c.relname""")
    return [r[0] for r in cur.fetchall()]


def auth_tables_present(cur) -> list[str]:
    cur.execute("""select table_name from information_schema.tables
                   where table_schema='auth' and table_name = any(%s)""", (list(AUTH_TABLES),))
    return [r[0] for r in cur.fetchall()]


def migration_version(cur) -> str | None:
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='supabase_migrations' and table_name='schema_migrations')""")
    if not cur.fetchone()[0]:
        return None
    cur.execute("select max(version) from supabase_migrations.schema_migrations")
    return cur.fetchone()[0]


def save_persistent(cur) -> dict[str, list[tuple]]:
    """Plocka ut de rader som ska överleva truncate.

    Returnerar {tabell: [rader]} som råa tupler. Kolumnordningen bevaras genom
    att läsa `select *`, och återinsättningen använder samma ordning.
    """
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='public' and table_name='dev_persistent')""")
    if not cur.fetchone()[0]:
        return {}

    cur.execute("select table_name, row_id from public.dev_persistent")
    wanted: dict[str, list[str]] = {}
    for table, row_id in cur.fetchall():
        wanted.setdefault(table, []).append(row_id)

    saved: dict[str, list[tuple]] = {}
    for table, ids in wanted.items():
        try:
            cur.execute(f'select * from public."{table}" where id = any(%s)', (ids,))
            rows = cur.fetchall()
            if rows:
                saved[table] = rows
        except psycopg2.Error:
            # En tabell som inte längre finns, eller saknar id-kolumn, ska inte
            # fälla hela speglingen — men den ska synas.
            print(f"  VARNING: kunde inte spara undan {table}, hoppar över.")
            cur.connection.rollback()
    return saved


def restore_persistent(cur, saved: dict[str, list[tuple]]) -> int:
    """Lägg tillbaka de bevarade raderna. Produktionen vinner vid krock."""
    total = 0
    for table, rows in saved.items():
        if not rows:
            continue
        placeholders = ",".join(["%s"] * len(rows[0]))
        for row in rows:
            try:
                cur.execute(
                    f'insert into public."{table}" values ({placeholders}) '
                    f"on conflict do nothing",
                    row,
                )
                total += cur.rowcount
            except psycopg2.Error as exc:
                print(f"  VARNING: {table}-rad kunde inte återställas: {exc}")
                cur.connection.rollback()
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="Speglar Supabase produktion → development.")
    ap.add_argument("--apply", action="store_true", help="Utför speglingen.")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    values = env_read(root / ".env.deploy")

    source_dsn = dsn_for(values, SOURCE_ENV_VAR)
    target_dsn = dsn_for(values, TARGET_ENV_VAR)
    assert_refs(source_dsn, target_dsn)  # spärr 2

    src = psycopg2.connect(source_dsn, connect_timeout=20)
    dst = psycopg2.connect(target_dsn, connect_timeout=20)
    src.autocommit = False
    dst.autocommit = False
    sc, dc = src.cursor(), dst.cursor()

    # --- Spärr 3, före något rörs
    assert_source_is_production(sc)
    dc.execute(MIRROR_META)
    dc.execute(DEV_PERSISTENT)
    dst.commit()
    assert_target_is_dev(dc)

    # --- Schemat måste stämma. En datakopia in i ett annat schema är värre än
    #     ingen kopia: den ser ut att lyckas och felar först vid läsning.
    sv, dv = migration_version(sc), migration_version(dc)
    if sv != dv:
        sys.exit(
            f"AVBRYT: schemaversionerna skiljer sig (produktion={sv}, development={dv}). "
            f"Kör migrationerna mot grenen först."
        )
    print(f"schemaversion: {sv} (matchar)")

    tbls = public_tables(sc)
    auth_tbls = auth_tables_present(sc)
    print(f"tabeller att spegla: {len(tbls)} publika + {len(auth_tbls)} auth ({', '.join(auth_tbls)})")

    if not args.apply:
        for t in tbls:
            sc.execute(f'select count(*) from public."{t}"')
            n = sc.fetchone()[0]
            if n:
                print(f"  public.{t}: {n}")
        for t in auth_tbls:
            sc.execute(f'select count(*) from auth."{t}"')
            print(f"  auth.{t}: {sc.fetchone()[0]}")
        saved = save_persistent(dc)
        if saved:
            print("\nBevaras över speglingen (dev_persistent):")
            for table, rows in saved.items():
                print(f"  {table}: {len(rows)} rad(er)")
        print("\nInget kopierat. Kör med --apply.")
        src.close()
        dst.close()
        return 0

    # --- Spara undan det som ska överleva
    saved = save_persistent(dc)
    if saved:
        print(f"sparar undan {sum(len(r) for r in saved.values())} rad(er) ur dev_persistent")

    # --- Replica-läge: FK och triggrar av under kopieringen
    dc.execute("set session_replication_role = replica")

    for t in auth_tbls:
        dc.execute(f'truncate table auth."{t}" cascade')
    for t in tbls:
        dc.execute(f'truncate table public."{t}" cascade')

    def copy(qualified: str) -> int:
        buf = io.BytesIO()
        sc.copy_expert(f"copy {qualified} to stdout (format binary)", buf)
        buf.seek(0)
        dc.copy_expert(f"copy {qualified} from stdin (format binary)", buf)
        sc.execute(f"select count(*) from {qualified}")
        return sc.fetchone()[0]

    counts: dict[str, int] = {}
    for t in auth_tbls:
        counts[f'auth."{t}"'] = copy(f'auth."{t}"')
    for t in tbls:
        counts[f'public."{t}"'] = copy(f'public."{t}"')

    # --- Sekvenser: målets värde sätts till källans, annars kolliderar nästa insert.
    sc.execute("select sequencename from pg_sequences where schemaname='public'")
    for (seq,) in sc.fetchall():
        sc.execute(f'select last_value, is_called from public."{seq}"')
        last, called = sc.fetchone()
        dc.execute("select setval(%s, %s, %s)", (f"public.{seq}", last, called))

    # --- Lägg tillbaka det bevarade
    if saved:
        restored = restore_persistent(dc, saved)
        print(f"återställde {restored} rad(er) ur dev_persistent")

    # Markören SIST, så en avbruten körning inte lämnar en falsk "klar"-stämpel.
    dc.execute("delete from public.mirror_meta")
    dc.execute(
        "insert into public.mirror_meta (environment, source_fingerprint) values (%s, %s)",
        (TARGET_ENV, sv),
    )

    dc.execute("set session_replication_role = origin")
    dst.commit()

    # --- Verifiera radantal mot källan.
    print("\nVerifierar radantal:")
    mismatches = 0
    for qualified, expected in counts.items():
        dc.execute(f"select count(*) from {qualified}")
        got = dc.fetchone()[0]
        if got != expected:
            mismatches += 1
            print(f"  FEL {qualified}: {got}/{expected}")
        elif expected:
            print(f"  OK  {qualified}: {got}")

    src.close()
    dst.close()
    if mismatches:
        print(f"\n{mismatches} tabell(er) har fel radantal.")
        return 1
    print(f"\nSpegling klar. mirror_meta.environment = {TARGET_ENV}, fingerprint = {sv}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
