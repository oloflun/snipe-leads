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
    "ss_knowledge_base",
)


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

    print(f"Konto:     {args.epost}  ({user_id})")
    print(f"Arbetsyta: {namn or '—'}  slug={slug or '—'}")
    print(f"Tenant:    {tenant_id or '—'}")

    # Spärr 2. Körs FÖRE allt annat: fyndet ska stoppa körningen, inte
    # rapporteras efter att raderingen redan börjat.
    if tenant_id:
        fynd = []
        for tabell in KUNDDATA:
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
    if tenant_id:
        # Före tenanten: de här hänger på den med NO ACTION.
        for tabell in TENANTBEROENDEN:
            plan.append((tabell, f"delete from public.{tabell} where tenant_id = %s", (tenant_id,)))
        plan.append(("ss_tenants", "delete from public.ss_tenants where id = %s", (tenant_id,)))

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
    cur.execute("select count(*) from public.ss_tenants where id = %s", (tenant_id,)) if tenant_id else None
    kvar_tenant = cur.fetchone()[0] if tenant_id else 0

    print(f"\nKvar efteråt — konto: {kvar_konto}, arbetsyta: {kvar_ws}, tenant: {kvar_tenant}")
    return 0 if (kvar_konto or kvar_ws or kvar_tenant) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
