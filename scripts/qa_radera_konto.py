#!/usr/bin/env python
"""Radera ETT QA-konto ur development — kontot, arbetsytan och dess tenant.

    python scripts/qa_radera_konto.py --epost nykund+80319488@snajp.se
    python scripts/qa_radera_konto.py --epost nykund+80319488@snajp.se --radera

## Varför skriptet behövde finnas

`qa_ny_kund.mjs` och `qa_testkund.mjs` skapar ett riktigt konto vid varje
körning — det är hela poängen, ett konto som skapas med en INSERT bevisar inte
att en människa kan bli kund. Priset är att development samlar på sig
arbetsytor och tenants som ingen städar, och en portfölj full av
`Testkund 68713860` är precis den sortens siffra som fattar beslut åt en.

Att städa för hand är fel svar: raderingen spänner över sju tabeller i två
delsystem, och tre av dem hänger på `ss_tenants` med NO ACTION — de måste bort
FÖRE tenanten, annars faller raderingen halvvägs och lämnar ett konto utan
arbetsyta. Ordningen syns inte på anropsstället, bara i främmande nycklar.

## Tre spärrar, och ingen av dem är kosmetisk

1. **Bara development.** `--env` finns inte. Skriptet läser
   `RAILWAY_DEVELOPMENT_PG_*` och kan inte peka på main.
2. **Vägrar kunddata.** Finns ett enda ärende, mejl eller prospekt på tenanten
   avbryts raderingen. Ett QA-konto har ingenting av det; en riktig kund har
   det, och den skillnaden ska maskinen kontrollera — inte den som skriver
   adressen. En riktig kunds radering går via `scripts/gdpr_radera.py`, som
   är byggd för artikel 17 och kan visa i efterhand vad som gjordes.
3. **Torrkörning som default.** Utan `--radera` skrivs bara vad som skulle
   försvinna.

Allt sker i EN transaktion. En halv radering är värre än ingen: kvar blir ett
konto som kan logga in i en arbetsyta som inte finns.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

#: Prefixet som avgör om en kunskapsbas är SEEDAD eller kundens egen.
#:
#: Samma villkor som backenden redan har på tre ställen: `POST /api/keys`
#: (app/api/keys.py), `POST /api/inbox/mock` (app/api/inbox.py) och docstringen
#: i app/scripts/seed_kb.py, som säger det rakt ut — artiklarna är Nordlys
#: Handels, och "i en riktig kunds bas är de fel svar presenterade som kundens
#: egna". Ändras villkoret där måste det ändras här.
TESTKUND_PREFIX = "testkund-"

#: Tabeller som pekar på ss_tenants med NO ACTION och som ett QA-konto faktiskt
#: får rader i. De måste bort före tenanten. Övriga NO ACTION-tabeller fångas av
#: kunddatakontrollen nedan — får de rader är kontot inte ett QA-konto.
TENANTBEROENDEN = ("agent_context_docs", "agent_configs", "ss_api_keys")

#: Spår av riktig verksamhet. En rad här betyder att kontot INTE är ett tomt
#: QA-konto, och då ska den här vägen inte användas.
KUNDDATA = (
    "ss_tickets",
    "ss_emails",
    "ss_customers",
    "ss_conversations",
    "ss_messages",
    "ss_drafts",
    "prospects",
    "outreach_messages",
    "send_queue",
    "agent_runs",
    # Villkorad — se `kb_ar_seedad()`. Står i listan för att en RIKTIG kunds
    # kunskapsbas är innehåll de själva lagt in.
    "ss_knowledge_base",
)


def kb_ar_seedad(tenant_slug: str | None) -> bool:
    """Är kunskapsbasen backendens seed, eller kundens eget innehåll?

    Skillnaden är hela spärren, och den var fel i b19efeb: `ss_knowledge_base`
    togs ur KUNDDATA GLOBALT därför att seedningen fällde varje testarbetsyta.
    Botemedlet var bredare än sjukdomen. En riktig kund som är onboardad men
    ännu inte igång — kunskapsbas uppladdad, noll ärenden, noll mejl, noll
    prospekt, noll körningar — passerade då spärren, och deras bas hade
    raderats som ett beroende. Det är exakt det tillstånd ett nytecknat konto
    står i veckan före driftsättning, alltså det tillstånd spärren finns för.

    Att i stället räkna rader (">16 artiklar = kundens egna") vore sämre: taket
    ändras när seed-ämnena ändras, och då tystnar spärren utan att någon rört
    den.
    """
    return bool(tenant_slug) and tenant_slug.startswith(TESTKUND_PREFIX)

#: Tenants som är REGISTRERADE i koden och därför aldrig får raderas.
#:
#: Läses ur `lib/tenants/index.ts` i stället för att skrivas av här: en hårdkodad
#: lista glider isär från registret vid första nya kunden, och den glidningen
#: syns inte förrän någon raderat en tenant som en configfil pekar på.
#:
#: Vad som går sönder om en av dem försvinner: `lib/tenants/<slug>.ts` pekar på
#: ett tomt id, `SNAJP_KEY_<SLUG>` blir en nyckel utan tenant, och för `testkund`
#: dessutom `link_testkund_workspace()` — fallbacken varje testarbetsyta faller
#: tillbaka på när den egna tenanten inte kunde skapas.
#:
#: ARBETSYTAN raderas ändå. Det är bara tenantraden som skyddas.
def registrerade_tenants() -> set[str]:
    index = Path(__file__).resolve().parents[1] / "lib" / "tenants" / "index.ts"
    kalla = index.read_text(encoding="utf-8")
    block = kalla.split("const tenants: Record<string, Tenant> = {")[1].split("};")[0]
    return {
        rad.strip().rstrip(",")
        for rad in block.splitlines()
        if rad.strip() and not rad.strip().startswith("//")
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epost", required=True, help="Kontots e-postadress.")
    ap.add_argument("--radera", action="store_true", help="Radera på riktigt.")
    args = ap.parse_args()

    conn = psycopg2.connect(dsn(env_read(), "development"))
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("select id from auth.users where email = %s", (args.epost,))
    rader = cur.fetchall()
    if not rader:
        print(f"Ingen användare med adressen {args.epost} i development.")
        return 1
    if len(rader) > 1:
        print(f"{len(rader)} användare delar adressen — avbryter, det är inte ett QA-konto.")
        return 1
    user_id = rader[0][0]

    cur.execute(
        """select w.id, w.name, w.slug, w.ss_tenant_id
             from public.workspaces w
             join public.profiles p on p.workspace_id = w.id
            where p.id = %s""",
        (user_id,),
    )
    ws = cur.fetchone()
    workspace_id, namn, slug, tenant_id = ws if ws else (None, None, None, None)

    # Tenantens EGEN slug, inte arbetsytans. De är samma sak för en tenant som
    # skapats i drift, men inte för en arbetsyta som pekar på en delad tenant —
    # och det är tenantens slug som avgör både seedningen och registerspärren.
    tenant_slug = None
    if tenant_id:
        cur.execute("select slug from public.ss_tenants where id = %s", (tenant_id,))
        tenant_slug = (cur.fetchone() or [None])[0]

    seedad_kb = kb_ar_seedad(tenant_slug)

    print(f"Konto:     {args.epost}  ({user_id})")
    print(f"Arbetsyta: {namn or '—'}  slug={slug or '—'}")
    print(f"Tenant:    {tenant_slug or '—'}  ({tenant_id or '—'})")
    print(f"Kunskapsbas: {'seedad av backenden' if seedad_kb else 'kundens egen — spärrad'}")

    # Spärr 2. Körs FÖRE allt annat: fyndet ska stoppa körningen, inte
    # rapporteras efter att raderingen redan börjat.
    if tenant_id:
        fynd = []
        for tabell in KUNDDATA:
            # Seedad kunskapsbas är inte kunddata — se kb_ar_seedad(). För en
            # riktig kund fälls den däremot, även när allt annat är tomt.
            if tabell == "ss_knowledge_base" and seedad_kb:
                continue
            try:
                cur.execute(f"select count(*) from public.{tabell} where tenant_id = %s", (tenant_id,))
                antal = cur.fetchone()[0]
            except psycopg2.Error:
                conn.rollback()
                continue
            if antal:
                fynd.append(f"{tabell}={antal}")
        if fynd:
            print("\nAVBRYTER — tenanten bär kunddata: " + ", ".join(fynd))
            print("Det här är inte ett tomt QA-konto. Använd scripts/gdpr_radera.py.")
            return 1

    plan: list[tuple[str, str, tuple]] = []
    if workspace_id:
        plan.append(
            (
                "workspaces (kaskad: profiles, business_contexts, workspace_tenant_keys)",
                "delete from public.workspaces where id = %s",
                (workspace_id,),
            )
        )
    plan.append(
        (
            "auth.users (kaskad: notification_preferences)",
            "delete from auth.users where id = %s",
            (user_id,),
        )
    )
    # Spärr 4: en tenant som står i lib/tenants/index.ts raderas ALDRIG.
    #
    # `testkund` är fallet som gör spärren nödvändig. Arbetsytan
    # "Testkund 68713860 workspace" pekar på den DELADE tenanten, inte på en egen
    # — den skapades innan migration 040, eller när den egna tenanten inte gick
    # att skapa. Att radera kontot hade då tagit `ss_tenants`-raden med sig, och
    # med den `SNAJP_KEY_TESTKUND`, configfilen och `link_testkund_workspace()`.
    # Nästa testarbetsyta som föll tillbaka hade mötts av ett 409 utan spår av
    # varför.
    skyddad = tenant_slug in registrerade_tenants() if tenant_slug else False

    if tenant_id and not skyddad:
        # Före tenanten: de här hänger på den med NO ACTION.
        beroenden = list(TENANTBEROENDEN)
        # Bara den SEEDADE basen raderas som ett beroende. Är den kundens egen
        # har spärren ovan redan avbrutit, så den här grenen nås aldrig med en
        # riktig kunds artiklar — raden står här för att ordningen ska vara
        # läsbar på ETT ställe, inte utspridd på två.
        if seedad_kb:
            beroenden.append("ss_knowledge_base")
        for tabell in beroenden:
            plan.append((tabell, f"delete from public.{tabell} where tenant_id = %s", (tenant_id,)))
        plan.append(("ss_tenants", "delete from public.ss_tenants where id = %s", (tenant_id,)))
    elif skyddad:
        print(
            f"\nTenanten {tenant_slug!r} står i lib/tenants/index.ts och SPARAS — "
            "bara arbetsytan och kontot raderas."
        )

    print()
    if not args.radera:
        for etikett, sats, params in plan:
            cur.execute(sats.replace("delete from", "select count(*) from"), params)
            print(f"  - {etikett}: {cur.fetchone()[0]} rad(er) skulle raderas")
        conn.rollback()
        print("\nInget raderat. Kör med --radera.")
        return 0

    try:
        for etikett, sats, params in plan:
            cur.execute(sats, params)
            print(f"  - {etikett}: {cur.rowcount} rad(er)")
        conn.commit()
    except psycopg2.Error as fel:
        conn.rollback()
        print(f"\nAVBRUTET, ingenting raderat: {fel}")
        return 1

    # Beviset är att raderna är borta, inte att satserna kördes.
    cur.execute("select count(*) from auth.users where email = %s", (args.epost,))
    kvar_konto = cur.fetchone()[0]
    cur.execute("select count(*) from public.workspaces where slug = %s", (slug,)) if slug else None
    kvar_ws = cur.fetchone()[0] if slug else 0
    # En skyddad tenant SKA finnas kvar — den räknas därför inte som rest.
    if tenant_id and not skyddad:
        cur.execute("select count(*) from public.ss_tenants where id = %s", (tenant_id,))
        kvar_tenant = cur.fetchone()[0]
    else:
        kvar_tenant = 0

    print(f"\nKvar efteråt — konto: {kvar_konto}, arbetsyta: {kvar_ws}, tenant: {kvar_tenant}")
    return 0 if (kvar_konto or kvar_ws or kvar_tenant) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
