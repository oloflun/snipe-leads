#!/usr/bin/env python3
"""Synk av körningar och supportärenden mellan development och main.

    python scripts/railway_synk.py                    # torrkörning: vad som skulle ändras
    python scripts/railway_synk.py --apply            # synka main → development (kräver första synken)
    python scripts/railway_synk.py --apply --forsta   # första synken: allt åt båda hållen, development vinner

Antons beslut 2026-10-17 (docs/BESLUT.md), som ersätter tvåvägssynken från
2026-10-10: första synken för över alla körningar från development till main.
Därefter är main sanningen och speglas till development; körningar gjorda i
development flyttas aktivt till main med Flytta till main (admin_flytt).
Provkörningar (is_test, prospekt med origin 'test'/'example' och allt under
dem) synkas aldrig.

## Regler per rad (tabellerna i SYNK, nyckeln är primärnyckeln)

* Finns i båda och är lika: inget.
* Finns i båda och skiljer sig: main vinner (första synken: development).
* Finns bara i main: kopieras till development.
* Finns bara i development: står kvar tills den flyttas, utom när main har
  raderat den (main:s `synk_raderingar`, migration 111), då raderas den.
  Första synken kopierar den till main.
* Provkörningar och rader hos en kund som bara finns i en av miljöerna rörs
  aldrig.

## Utskicken

Development skickar inget i det här läget (`mirror_meta.lage = 'envags'`,
`scheduler.skickas_har`): en spegelrad som development skickade hade fått
tillbaka main:s status vid nästa synk och kunnat gå ut igen. Första synken
skriver därför om `godkand_i` från development till main på de köade
utkasten, så att main skickar dem.
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


def nyckelvillkor(cur, tabell: str, kolumner: list[str]) -> tuple[str, str]:
    """(villkor för en nyckel, villkor för en lista nycklar) i skriv.

    Med en nyckelkolumn jämförs kolumnen mot sin egen typ, så att
    primärnyckelns index används. concat_ws('|', x.id::text) = … kan inte
    använda något index, och varje rad blev en läsning av hela tabellen:
    synken efter en veckas uppehåll (2026-10-30, ~5 000 rader) hann inte klart
    på 15 minuter och avbröts mitt i outreach_threads. Sammansatta nycklar
    behåller uttrycket; nycklarnas textform är densamma i båda fallen."""
    if len(kolumner) != 1:
        uttryck = nyckeluttryck(kolumner)
        return f"{uttryck} = %s", f"{uttryck} = any(%s)"
    cur.execute(
        "select format_type(atttypid, atttypmod) from pg_attribute "
        "where attrelid = ('public.' || %s)::regclass and attname = %s",
        (tabell, kolumner[0]),
    )
    typ = cur.fetchone()[0]
    kolumn = f"x.{kolumner[0]}"
    return f"{kolumn} = %s::{typ}", f"{kolumn} = any(%s::{typ}[])"


def rader(cur, tabell: str, kolumner: list[str], tenants: list[str]) -> dict[str, dict]:
    """Nyckel → {andrad, hash, pmid} för de rader som får synkas. Själva raden
    hämtas först när den skrivs (skriv): alla körningar med spår på en gång
    tog slut på minnet 2026-10-17. Saknas synk_andrad_at (migration 111 inte
    körd, bara i torrkörning) blir tiden null."""
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
                   md5((to_jsonb(x) - 'synk_andrad_at')::text), to_jsonb(x)->>'provider_message_id'
              from public.{tabell} x
             where x.tenant_id = any(%s::uuid[]) and not coalesce(({SYNK[tabell]}), false)""",
        (tenants,),
    )
    return {k: {"andrad": a, "hash": h, "pmid": pm} for k, a, h, pm in cur.fetchall()}


def raderingar(cur, tabell: str) -> dict[str, datetime]:
    cur.execute("select to_regclass('public.synk_raderingar') is not null")
    if not cur.fetchone()[0]:
        return {}
    cur.execute("select nyckel, raderad_at from public.synk_raderingar where tabell = %s", (tabell,))
    return dict(cur.fetchall())


def planera(
    dev: dict[str, dict], main: dict[str, dict], rad_main: dict[str, datetime], *, forsta: bool,
) -> dict[str, list]:
    """Ren funktion: nycklarna som ska skrivas och raderas i varje miljö.
    Main skrivs bara av första synken; därefter är main sanningen."""
    plan: dict[str, list] = {"till_main": [], "till_dev": [], "radera_main": [], "radera_dev": []}
    for k in dev.keys() | main.keys():
        d, m = dev.get(k), main.get(k)
        if d and m:
            if d["hash"] != m["hash"]:
                plan["till_main" if forsta else "till_dev"].append(k)
        elif d:
            if forsta:
                plan["till_main"].append(k)
            elif k in rad_main:
                plan["radera_dev"].append(k)
            # annars: en körning gjord i development, flyttas med Flytta till main
        else:
            plan["till_dev"].append(k)
    return plan


#: Rader per parti i skriv: en hämtning, en borttagning och en insert.
PARTI = 100


def skriv(
    kalla, cur, tabell: str, kolumner: list[str], nycklar: list[str], radera: list[str], *, ersatt_krockar: bool = False,
) -> list[str]:
    """Raderar och skriver i replica-läge, ett parti om PARTI rader åt gången
    (en savepoint per parti, per rad bara när partiet faller). Returnerar
    felen."""
    fel: list[str] = []
    nyckel = nyckeluttryck(kolumner)
    en, flera = nyckelvillkor(cur, tabell, kolumner)
    # Genererade kolumner (prospects.foretagsnyckel) räknas fram av målet och
    # får inte skrivas; 855 prospekt föll på det 2026-10-17.
    cur.execute(
        "select string_agg(quote_ident(attname), ', ' order by attnum) from pg_attribute "
        "where attrelid = ('public.' || %s)::regclass and attnum > 0 and not attisdropped and attgenerated = ''",
        (tabell,),
    )
    kol = cur.fetchone()[0]
    for i in range(0, len(radera), PARTI):
        cur.execute(f"delete from public.{tabell} x where {flera}", (radera[i:i + PARTI],))
    for i in range(0, len(nycklar), PARTI):
        kalla.execute(
            f"select {nyckel}, to_jsonb(x)::text from public.{tabell} x where {flera}",
            (nycklar[i:i + PARTI],),
        )
        parti = kalla.fetchall()
        if not parti:
            continue
        # Hela partiet i två anrop (2026-10-30): synken körs från GitHub mot
        # Railway, och fyra rundresor per rad var det mesta av tiden. Faller
        # partiet (en trasig rad) görs det om rad för rad nedan, så att felet
        # pekar ut raden och resten skrivs som förut.
        cur.execute("savepoint parti")
        try:
            cur.execute(f"delete from public.{tabell} x where {flera}", ([k for k, _ in parti],))
            cur.execute(
                f"insert into public.{tabell} ({kol}) select {kol} "
                f"from jsonb_populate_recordset(null::public.{tabell}, %s::jsonb)",
                ("[" + ",".join(rad for _, rad in parti) + "]",),
            )
            cur.execute("release savepoint parti")
            continue
        except psycopg2.Error:
            cur.execute("rollback to savepoint parti")
        for k, rad in parti:
            cur.execute("savepoint rad")
            try:
                cur.execute(f"delete from public.{tabell} x where {en}", (k,))
                cur.execute(
                    f"insert into public.{tabell} ({kol}) select {kol} from jsonb_populate_record(null::public.{tabell}, %s::jsonb)",
                    (rad,),
                )
                cur.execute("release savepoint rad")
            except psycopg2.Error as e:
                cur.execute("rollback to savepoint rad")
                # 23505 = unique_violation. Felkoden och inte psycopg2.errors:
                # INV-DATA-003 laddar skriptet med en psycopg2-stubbe utan
                # undermoduler.
                krock = getattr(e, "pgcode", None) == "23505"
                if not (krock and ersatt_krockar and _ersatt_krock(cur, tabell, kolumner, kol, en, k, rad, e)):
                    fel.append(f"{tabell} {k}: {str(e).splitlines()[0]}")
    return fel


def _ersatt_krock(cur, tabell: str, kolumner: list[str], kol: str, en: str, k: str, rad: str, e) -> bool:
    """Main-raden krockar med en ANNAN rad i development på ett unikt index
    (2026-10-30: agent_suggestions_dedupe_ny_idx, samma förslag skapat i båda
    miljöerna med olika id). Main är sanningen: development-raden som krockar
    tas bort och main-raden skrivs. Bara index på vanliga kolumner; ett
    uttrycksindex rapporteras som förut. True = ersatt."""
    index = getattr(getattr(e, "diag", None), "constraint_name", None)
    if not index:
        return False
    cur.execute(
        """select array(select a.attname from unnest(i.indkey) with ordinality k(attnum, ord)
                        join pg_attribute a on a.attrelid = i.indrelid and a.attnum = k.attnum
                        order by k.ord),
                  0 = any(i.indkey), pg_get_expr(i.indpred, i.indrelid)
             from pg_index i join pg_class c on c.oid = i.indexrelid
            where c.relname = %s and i.indisunique""",
        (index,),
    )
    rad_index = cur.fetchone()
    if not rad_index or rad_index[1] or not rad_index[0]:
        return False
    indexkolumner, _, predikat = rad_index
    lika = " and ".join(f"x.{c} is not distinct from n.{c}" for c in indexkolumner)
    annan = " or ".join(f"x.{c} is distinct from n.{c}" for c in kolumner)
    cur.execute("savepoint krock")
    try:
        cur.execute(
            f"""delete from public.{tabell} where ctid in (
                  select x.ctid from public.{tabell} x, jsonb_populate_record(null::public.{tabell}, %s::jsonb) n
                   where {lika} and ({annan}))"""
            + (f" and ({predikat})" if predikat else ""),
            (rad,),
        )
        cur.execute(f"delete from public.{tabell} x where {en}", (k,))
        cur.execute(
            f"insert into public.{tabell} ({kol}) select {kol} from jsonb_populate_record(null::public.{tabell}, %s::jsonb)",
            (rad,),
        )
        cur.execute("release savepoint krock")
        print(f"ERSATT: {tabell} {k}: development-raden som krockade på {index} togs bort", flush=True)
        return True
    except psycopg2.Error:
        cur.execute("rollback to savepoint krock")
        return False


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
    if args.apply and lage != "envags" and not args.forsta:
        sys.exit("AVBRYT: första synken är inte gjord. Kör den för hand med --apply --forsta.")
    if args.apply and args.forsta and lage == "envags":
        sys.exit("AVBRYT: första synken är redan gjord; main är sanningen. Kör utan --forsta.")
    forsta = args.forsta or lage != "envags"
    if not forsta:
        # Main är sanningen (Anton 2026-10-21): utanför första synken öppnas
        # main skrivskyddat, så att synken mekaniskt inte kan skriva dit.
        # Körningar från development når main bara via Flytta till main.
        mn.rollback()
        mn.set_session(readonly=True)
    print(f"läge: {'första synken (development vinner)' if forsta else 'main → development'}; "
          f"senast synkad: {synkad or 'aldrig'}")

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
        plan = planera(d, m, raderingar(mc, t), forsta=forsta)
        if t == "ss_emails":
            plan["till_dev"] = [k for k in plan["till_dev"] if not (m[k]["pmid"] in mejl_dev and k not in d)]
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
        fel += skriv(dc, mc, t, kol, plan["till_main"], plan["radera_main"])
        # Main är sanningen: en krock i development på ett unikt index ger vika.
        fel += skriv(mc, dc, t, kol, plan["till_dev"], plan["radera_dev"], ersatt_krockar=True)
        print(f"skrivet: {t}", flush=True)
    if forsta:
        # Köade utkast godkända i development skickas av main från och med nu
        # (lika i båda miljöerna, så raderna förblir synkade).
        for c in (dc, mc):
            c.execute(
                f"""update public.send_queue x
                       set gate_checks = jsonb_set(x.gate_checks, '{{godkand_i}}', '"main"')
                     where x.gate_checks->>'godkand_i' = 'development'
                       and x.tenant_id = any(%s::uuid[]) and not coalesce(({SYNK['send_queue']}), false)""",
                (gemensamma,),
            )
            print(f"godkand_i → main på {c.rowcount} köade utkast i {'development' if c is dc else 'main'}")
    for c in (dc, mc):
        c.execute("set session_replication_role = origin")
    dc.execute("update public.mirror_meta set lage = 'envags', synkad_at = now()")
    mn.commit()
    dev.commit()
    for f in fel:
        print("HOPPAD:", f)
    print(f"\nSynk klar. {len(fel)} rader hoppades över.")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
