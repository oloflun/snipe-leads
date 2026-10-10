#!/usr/bin/env python3
"""Tvåvägssynk av körningar och supportärenden mellan development och main.

    python scripts/railway_synk.py                    # torrkörning: vad som skulle ändras
    python scripts/railway_synk.py --apply            # synka (kräver att första synken gjorts)
    python scripts/railway_synk.py --apply --forsta   # första synken: development vinner

Antons beslut 2026-10-10 (docs/BESLUT.md): alla körningar och supportärenden
speglas åt båda hållen med det senast ändrade som sanning, utom provkörningar
(is_test, prospekt med origin 'test'/'example' och allt under dem), som stannar
i development och flyttas till main med Flytta till main (admin_flytt). Det
ersätter den nattliga envägsspegeln main → development (railway_seed_dev.py),
som tömde development varje natt.

## Regler per rad (tabellerna i SYNK, nyckeln är primärnyckeln)

* Finns i båda och är lika: inget.
* Finns i båda och skiljer sig: den med senast `synk_andrad_at` vinner
  (migration 111). Vid första synken (`--forsta`) vinner development.
* Finns bara på ena sidan: raderingsloggen (`synk_raderingar`, migration 111)
  på den andra sidan avgör. Raderades raden där efter att den senast ändrades
  här, raderas den här också; annars kopieras den dit.
* Provkörningar och rader hos en kund som bara finns i en av miljöerna rörs
  aldrig.
* Ett inkommande mejl som bara finns i main men vars provider_message_id redan
  finns i development (båda miljöerna läste samma brevlåda före synken)
  kopieras inte: development har redan mejlet.

Första synken raderar ingenting: det som bara finns i main (kundmejl som kom in
efter den senaste speglingen) kopieras till development. Före första synken
sparas en kopia av varje synkad tabell i schemat `synk_kopia_<tid>` i båda
databaserna.

## Skrivningen

Replica-läge på målet: främmande nycklar och triggrar är av, så den kopierade
`synk_andrad_at` står kvar och raderingstriggern loggar inte synkens egna
raderingar. Varje rad skrivs som radera + infoga ur radens JSON
(jsonb_populate_record), med en savepoint per rad: en rad som krockar med ett
unikt villkor rapporteras och hoppas över, resten går igenom.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

DEV, MAIN = "development", "main"

_TEST_PROSPEKT = "select id from public.prospects where origin in ('test', 'example')"
_TEST_TRADAR = (
    "select t.id from public.outreach_threads t join public.prospects p on p.id = t.prospect_id "
    "where p.origin in ('test', 'example')"
)
_TEST_ARENDEN = "select id from public.ss_tickets where is_test"
_TEST_MEJL = "select id from public.ss_emails where is_test"

#: Tabell → villkoret som gör en rad till en provkörning (aldrig synkad).
#: Ordningen spelar ingen roll i replica-läge men följer föräldrar → barn.
SYNK: dict[str, str] = {
    "ss_customers": "false",
    "ss_customer_identifiers": "false",
    "ss_tickets": "x.is_test",
    "ss_conversations": f"x.ticket_id in ({_TEST_ARENDEN})",
    "ss_messages": f"x.conversation_id in (select c.id from public.ss_conversations c where c.ticket_id in ({_TEST_ARENDEN}))",
    "ss_emails": "x.is_test",
    "ss_email_attachments": f"x.email_id in ({_TEST_MEJL})",
    "ss_classifications": f"x.email_id in ({_TEST_MEJL})",
    "ss_decision_log": f"x.email_id in ({_TEST_MEJL})",
    "ss_drafts": f"(x.email_id in ({_TEST_MEJL}) or x.ticket_id in ({_TEST_ARENDEN}))",
    "ss_human_reviews": "false",
    "ss_agent_metrics": f"x.ticket_id in ({_TEST_ARENDEN})",
    "customer_memory": "false",
    "agent_suggestions": "false",
    "prospects": "x.origin in ('test', 'example')",
    "prospect_sources": f"x.prospect_id in ({_TEST_PROSPEKT})",
    "prospect_status_logg": f"x.prospect_id in ({_TEST_PROSPEKT})",
    "outreach_threads": f"x.prospect_id in ({_TEST_PROSPEKT})",
    "outreach_messages": f"x.thread_id in ({_TEST_TRADAR})",
    "send_queue": f"x.thread_id in ({_TEST_TRADAR})",
    "lead_lists": "x.is_test",
    "lead_list_items": "x.list_id in (select id from public.lead_lists where is_test)",
    "lead_samtal": f"x.prospect_id in ({_TEST_PROSPEKT})",
    "lead_anteckningar": f"x.prospect_id in ({_TEST_PROSPEKT})",
    "lead_uppgifter": f"x.prospect_id in ({_TEST_PROSPEKT})",
    "suppressions": "false",
    "leads_job_ledger": "x.is_test",
    "agent_runs": "x.is_test",
}


def pk(cur, tabell: str) -> list[str]:
    cur.execute(
        """select a.attname from pg_index i
           join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
           where i.indrelid = ('public.' || %s)::regclass and i.indisprimary order by a.attnum""",
        (tabell,),
    )
    return [r[0] for r in cur.fetchall()]


def nyckeluttryck(kolumner: list[str]) -> str:
    return "concat_ws('|', " + ", ".join(f"x.{k}::text" for k in kolumner) + ")"


def rader(cur, tabell: str, kolumner: list[str], tenants: list[str]) -> dict[str, dict]:
    """Nyckel → {andrad, hash, rad} för de rader som får synkas. Saknas
    synk_andrad_at (migration 111 inte körd, bara i torrkörning) blir tiden null."""
    cur.execute("select to_regclass('public.' || %s) is not null", (tabell,))
    if not cur.fetchone()[0]:
        return {}  # bara i torrkörning: skrivning kräver samma schema (kontrollera)
    cur.execute(
        "select exists (select 1 from information_schema.columns where table_schema = 'public' "
        "and table_name = %s and column_name = 'synk_andrad_at')", (tabell,),
    )
    andrad = "x.synk_andrad_at" if cur.fetchone()[0] else "null::timestamptz"
    cur.execute(
        f"""select {nyckeluttryck(kolumner)}, {andrad},
                   md5((to_jsonb(x) - 'synk_andrad_at')::text), to_jsonb(x)
              from public.{tabell} x
             where x.tenant_id = any(%s::uuid[]) and not coalesce(({SYNK[tabell]}), false)""",
        (tenants,),
    )
    return {k: {"andrad": a, "hash": h, "rad": r} for k, a, h, r in cur.fetchall()}


def raderingar(cur, tabell: str) -> dict[str, datetime]:
    cur.execute("select to_regclass('public.synk_raderingar') is not null")
    if not cur.fetchone()[0]:
        return {}
    cur.execute("select nyckel, raderad_at from public.synk_raderingar where tabell = %s", (tabell,))
    return dict(cur.fetchall())


def planera(
    dev: dict[str, dict], main: dict[str, dict], rad_dev: dict[str, datetime], rad_main: dict[str, datetime],
    *, forsta: bool,
) -> dict[str, list]:
    """Ren funktion: vad som ska skrivas och raderas i varje miljö."""
    plan: dict[str, list] = {"till_main": [], "till_dev": [], "radera_main": [], "radera_dev": []}
    for k in dev.keys() | main.keys():
        d, m = dev.get(k), main.get(k)
        if d and m:
            if d["hash"] == m["hash"]:
                continue
            if forsta or (d["andrad"] or datetime.min.replace(tzinfo=timezone.utc)) >= (
                m["andrad"] or datetime.min.replace(tzinfo=timezone.utc)
            ):
                plan["till_main"].append(d["rad"])
            else:
                plan["till_dev"].append(m["rad"])
        elif d:
            raderad = rad_main.get(k)
            if raderad and not forsta and (d["andrad"] is None or raderad > d["andrad"]):
                plan["radera_dev"].append(k)
            else:
                plan["till_main"].append(d["rad"])
        else:
            raderad = rad_dev.get(k)
            if raderad and not forsta and (m["andrad"] is None or raderad > m["andrad"]):
                plan["radera_main"].append(k)
            else:
                plan["till_dev"].append(m["rad"])
    return plan


def skriv(cur, tabell: str, kolumner: list[str], nya: list[dict], radera: list[str]) -> list[str]:
    """Raderar och skriver i replica-läge, en savepoint per rad. Returnerar felen."""
    fel: list[str] = []
    villkor = f"{nyckeluttryck(kolumner)} = %s"
    for k in radera:
        cur.execute(f"delete from public.{tabell} x where {villkor}", (k,))
    for rad in nya:
        k = "|".join(str(rad.get(c)) for c in kolumner)
        cur.execute("savepoint rad")
        try:
            cur.execute(f"delete from public.{tabell} x where {villkor}", (k,))
            cur.execute(
                f"insert into public.{tabell} select * from jsonb_populate_record(null::public.{tabell}, %s::jsonb)",
                (json.dumps(rad, default=str),),
            )
            cur.execute("release savepoint rad")
        except psycopg2.Error as e:
            cur.execute("rollback to savepoint rad")
            fel.append(f"{tabell} {k}: {str(e).splitlines()[0]}")
    return fel


def kopiera_tabeller(cur, schema: str) -> None:
    cur.execute(f"create schema if not exists {schema}")
    for t in SYNK:
        cur.execute(f"create table {schema}.{t} as table public.{t}")


def kontrollera(dc, mc, *, skriver: bool) -> None:
    """Spärrarna: rätt databaser, samma schema, synkens infrastruktur på plats.
    En torrkörning varnar för schema och infrastruktur i stället för att avbryta."""
    dc.execute("select to_regclass('public.mirror_meta') is not null")
    if not dc.fetchone()[0]:
        sys.exit("AVBRYT: development saknar mirror_meta. Fel databas?")
    dc.execute("select environment from public.mirror_meta")
    if (dc.fetchone() or [None])[0] != DEV:
        sys.exit("AVBRYT: development-databasens markör säger inte 'development'.")
    mc.execute("select to_regclass('public.mirror_meta') is not null")
    if mc.fetchone()[0]:
        mc.execute("select count(*) from public.mirror_meta")
        if mc.fetchone()[0]:
            sys.exit("AVBRYT: main-databasen har en spegelmarkör. Det är inte main.")
    versioner = []
    for c in (dc, mc):
        c.execute("select max(version) from supabase_migrations.schema_migrations")
        versioner.append(c.fetchone()[0])
    stopp = sys.exit if skriver else (lambda text: print("VARNING:", text.removeprefix("AVBRYT: ")))
    if versioner[0] != versioner[1]:
        stopp(f"AVBRYT: schemaversionerna skiljer sig (development={versioner[0]}, main={versioner[1]}). "
                 "Kör railway_migrate.py mot den som ligger efter.")
    for c, namn in ((dc, DEV), (mc, MAIN)):
        c.execute("select to_regclass('public.synk_raderingar') is not null")
        if not c.fetchone()[0]:
            stopp(f"AVBRYT: {namn} saknar synk_raderingar (migration 111).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--forsta", action="store_true", help="första synken: development vinner varje konflikt")
    args = ap.parse_args()

    env = env_read()
    dev = psycopg2.connect(dsn(env, DEV), connect_timeout=20)
    mn = psycopg2.connect(dsn(env, MAIN), connect_timeout=20)
    dc, mc = dev.cursor(), mn.cursor()
    kontrollera(dc, mc, skriver=args.apply)

    if args.apply:
        dc.execute("alter table public.mirror_meta add column if not exists lage text")
        dc.execute("alter table public.mirror_meta add column if not exists synkad_at timestamptz")
        dev.commit()
    dc.execute("select to_jsonb(m) from public.mirror_meta m")
    meta = dc.fetchone()[0]
    lage, synkad = meta.get("lage"), meta.get("synkad_at")
    if args.apply and lage != "tvavags" and not args.forsta:
        sys.exit("AVBRYT: första synken är inte gjord. Kör den för hand med --apply --forsta.")
    forsta = args.forsta or lage != "tvavags"
    print(f"läge: {'första synken (development vinner)' if forsta else 'tvåvägs'}; senast synkad: {synkad or 'aldrig'}")

    dc.execute("select id::text from public.ss_tenants")
    mc.execute("select id::text from public.ss_tenants")
    gemensamma = sorted({r[0] for r in dc.fetchall()} & {r[0] for r in mc.fetchall()})

    mc.execute("select provider_message_id from public.ss_emails where provider_message_id is not null")
    dc.execute("select provider_message_id from public.ss_emails where provider_message_id is not null")
    mejl_dev = {r[0] for r in dc.fetchall()}

    planer: dict[str, tuple[list[str], dict]] = {}
    print(f"{'tabell':26} {'→ main':>7} {'→ dev':>7} {'rad main':>9} {'rad dev':>8}")
    for t in SYNK:
        kol = pk(dc, t)
        d, m = rader(dc, t, kol, gemensamma), rader(mc, t, kol, gemensamma)
        plan = planera(d, m, raderingar(dc, t), raderingar(mc, t), forsta=forsta)
        if t == "ss_emails":
            plan["till_dev"] = [r for r in plan["till_dev"]
                                if not (r.get("provider_message_id") in mejl_dev and r["id"] not in d)]
        planer[t] = (kol, plan)
        if any(plan.values()):
            print(f"{t:26} {len(plan['till_main']):>7} {len(plan['till_dev']):>7} "
                  f"{len(plan['radera_main']):>9} {len(plan['radera_dev']):>8}")

    if not args.apply:
        print("\nTorrkörning: inget skrivet. Kör med --apply (första gången --apply --forsta).")
        return 0

    stampel = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    if forsta:
        for c in (dc, mc):
            kopiera_tabeller(c, f"synk_kopia_{stampel}")
        print(f"kopia sparad i schemat synk_kopia_{stampel} i båda databaserna")

    fel: list[str] = []
    for c in (dc, mc):
        c.execute("set session_replication_role = replica")
    for t, (kol, plan) in planer.items():
        fel += skriv(mc, t, kol, plan["till_main"], plan["radera_main"])
        fel += skriv(dc, t, kol, plan["till_dev"], plan["radera_dev"])
    for c in (dc, mc):
        c.execute("set session_replication_role = origin")
    dc.execute("update public.mirror_meta set lage = 'tvavags', synkad_at = now()")
    mn.commit()
    dev.commit()
    for f in fel:
        print("HOPPAD:", f)
    print(f"\nSynk klar. {len(fel)} rader hoppades över.")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
