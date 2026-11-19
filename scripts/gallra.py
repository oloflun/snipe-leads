#!/usr/bin/env python
"""Kör gallringen för hand. Torrkörning som default.

    python scripts/gallra.py --env railway-main                       # visar bara
    python scripts/gallra.py --env railway-main --tenant <slug>       # en kund
    python scripts/gallra.py --env railway-main --tenant <slug> --apply
    python scripts/gallra.py --env railway-main --tenant <slug> --policyns-period --beslutad-av "Anton"

## Vad den gör

Anropar `gallra_tenant` (migration 119) per kund med beslutad policy. Funktionen
räknar urvalet i varje kategori integritetspolicyn omfattar (supportmejl,
ärenden och chattar, kundminne, prospekt med trådar och samtal, listor,
kampanjmejl och kontakter, säljlistan, agentloggar, händelser, sidcache) och
skriver ut antal per tabell. Utan `--apply` ändras ingenting; körningen loggas
ändå i ss_gallringslogg med status `torrkorning`.

Spärrlistan (suppressions) och bokföringsunderlaget (bk_underlag) rörs aldrig.
Agentloggarnas promptar och svar nollas, raderna står kvar. Se filhuvudet i
db/migrations/20261117120000_119_gallring_alla_kategorier.sql.

## Varför ett skript bredvid den schemalagda körningen

Den schemalagda körningen (api-tjänsten, GALLRING_AKTIV) har ett tak per kund
och gör ingenting hos en kund vars urval är större. Första gallringen av en
kund med lång historik är därför ett handgrepp: torrkör, läs siffrorna, kör
med `--apply`. Skriptet har inget tak om du inte anger `--tak`.

## Att sätta policyn är ett eget kommando

`--satt-policy DAGAR` eller `--policyns-period` skriver retentionsperioden för
en kund och avslutar utan att radera något. Att bestämma hur länge en kunds
data får ligga kvar och att radera den är två olika beslut, och ett kommando
som gjorde båda hade gjort det första av misstag.

Satt mot `railway-main` skrivs policyn också i `railway-development`: spegeln
gallrar själv de tabeller synken inte för över (migration 133) och läser då
sin egen kopia av policyn, som inte synkas.

`--policyns-period` är de 24 månader integritetspolicyn utlovar, som 731 dagar:
24 månader är som mest 731 dagar, så ingenting gallras före 24 månader.

Perioden är ett affärsbeslut. Sätt den inte utan att den är förankrad med
kunden och stämmer med biträdesavtalet — se docs/JURIDIK_ATGARDER.md.
"""

from __future__ import annotations

import argparse
import json
import sys

import psycopg2

from gdpr_verktyg import dsn_for

#: 24 månader enligt integritetspolicyn (app/integritetspolicy), i hela dagar.
POLICYNS_PERIOD_DAGAR = 731


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Radera på riktigt. Utan flaggan är körningen en torrkörning.",
    )
    parser.add_argument("--tenant", help="Bara den här tenanten (UUID eller slug).")
    parser.add_argument(
        "--tak",
        type=int,
        default=None,
        help="Gör ingenting hos en kund vars urval är större än så här många rader.",
    )
    policy = parser.add_mutually_exclusive_group()
    policy.add_argument(
        "--satt-policy",
        type=int,
        metavar="DAGAR",
        help="Sätt retentionsperiod för --tenant och avsluta. Raderar ingenting.",
    )
    policy.add_argument(
        "--policyns-period",
        action="store_true",
        help=f"Sätt integritetspolicyns 24 månader ({POLICYNS_PERIOD_DAGAR} dagar) för --tenant.",
    )
    parser.add_argument("--beslutad-av", default="", help="Vem som fattade beslutet.")
    args = parser.parse_args()

    dagar = POLICYNS_PERIOD_DAGAR if args.policyns_period else args.satt_policy

    if dagar is not None:
        if not args.tenant or not args.beslutad_av:
            sys.exit("AVBRYTER: policyn kräver både --tenant och --beslutad-av.")
        _satt_policy(args.env, args.tenant, dagar, args.beslutad_av)
        print(f"Policy satt: {dagar} dagar för {args.tenant} ({args.beslutad_av}).")
        if args.env == "railway-main":
            # Spegeln gallrar det synken inte för över med sin egen kopia av
            # policyn (migration 133), och policytabellen synkas inte.
            try:
                _satt_policy("railway-development", args.tenant, dagar, args.beslutad_av)
                print("Samma policy satt i railway-development (spegeln).")
            except (SystemExit, psycopg2.Error) as fel:
                print(
                    "VARNING: policyn kunde inte sättas i railway-development "
                    f"({type(fel).__name__}). Kör samma kommando med --env railway-development."
                )
        print("Ingenting raderades. Torrkör gallringen innan den körs skarpt.")
        return 0

    with psycopg2.connect(dsn_for(args.env)) as conn, conn.cursor() as cur:
        cur.execute("select to_regclass('public.mirror_meta') is not null")
        if cur.fetchone()[0]:
            print(
                "Spegel (mirror_meta): bara tabellerna synken inte för över gallras här "
                "(migration 133). Resten får main:s raderingar genom synken."
            )

        if args.tenant:
            tenants = [(_slå_upp_tenant(cur, args.tenant), args.tenant)]
        else:
            cur.execute("select id, slug from ss_tenants order by slug")
            tenants = cur.fetchall()

        utan_policy = 0
        totalt = 0
        for tenant_id, slug in tenants:
            cur.execute(
                "select gallra_tenant(%s, %s, %s, 'skript')",
                (tenant_id, not args.apply, args.tak),
            )
            svar = cur.fetchone()[0]
            if isinstance(svar, str):
                svar = json.loads(svar)
            if svar["status"] == "ingen_policy":
                utan_policy += 1
                continue
            totalt += int(svar.get("totalt") or 0)
            print(f"\n  {slug}: {svar['status']}, {svar['totalt']} rader "
                  f"(policy {svar['dagar']} dagar, gräns {svar['grans']})")
            for tabell, post in svar["antal"].items():
                if post["antal"]:
                    print(f"    {tabell:<26} {post['atgard']:<12} {post['antal']}")
            if svar["status"] == "tak_nadd":
                print(f"    TAKET ({args.tak}) NÅTT — ingenting ändrades hos {slug}.")

        if not args.apply:
            print("\nTORRKÖRNING — ingenting raderades. Lägg till --apply när siffrorna stämmer.")
        print(f"Summa: {totalt} rader. {utan_policy} kunder saknar beslutad policy.")
        print("Spärrlistan och bokföringsunderlaget rörs aldrig.")

        if utan_policy:
            print(
                "\nEn kund utan policy gallras INTE. Det är den ofarliga defaulten, "
                "men det är också en kund vars data ligger kvar för alltid — "
                "sätt en policy med --policyns-period eller --satt-policy."
            )
    return 0


def _satt_policy(env: str, tenant: str, dagar: int, beslutad_av: str) -> None:
    with psycopg2.connect(dsn_for(env)) as conn, conn.cursor() as cur:
        tenant_id = _slå_upp_tenant(cur, tenant)
        cur.execute(
            """
            insert into ss_gallringspolicy (tenant_id, dagar, beslutad_av)
            values (%s, %s, %s)
            on conflict (tenant_id)
            do update set dagar = excluded.dagar,
                          beslutad_av = excluded.beslutad_av,
                          beslutad_at = now()
            """,
            (tenant_id, dagar, beslutad_av),
        )


def _slå_upp_tenant(cur, nyckel: str) -> str:
    cur.execute("select id from ss_tenants where id::text = %s or slug = %s", (nyckel, nyckel))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYTER: hittar ingen tenant med id/slug '{nyckel}'.")
    return rad[0]


if __name__ == "__main__":
    raise SystemExit(main())
