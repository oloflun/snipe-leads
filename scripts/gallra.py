#!/usr/bin/env python
"""Kör gallringen av supportdata. Torrkörning som default.

    python scripts/gallra.py --env railway-main                 # visar bara
    python scripts/gallra.py --env railway-main --apply         # raderar
    python scripts/gallra.py --env railway-main --satt-policy 730 --beslutad-av "Anton"

## Varför ett skript och inte bara ett cron-anrop mot SQL-funktionen

Därför att den som kör det ska se VAD som försvinner innan det försvinner.
`gallra_supportdata` har torrkörning som default av samma skäl, och det här
skriptet gör den defaulten synlig: utan `--apply` raderas ingenting, och
utskriften säger hur många ärenden som skulle ha raderats per kund.

## Att sätta policyn är ett eget kommando

`--satt-policy` skriver retentionsperioden för en kund. Den är MEDVETET skild
från gallringen: att bestämma hur länge en kunds data får ligga kvar och att
radera den är två olika beslut, och ett kommando som gjorde båda hade gjort
det första av misstag.

Perioden är ett affärsbeslut. Skriv inte ett tal här utan att det är förankrat
med kunden och står i integritetspolicyn — se docs/JURIDIK_ATGARDER.md, P1.1.

## Schemaläggning

Tänkt som ett Railway-cronjobb, dagligen. Kör det med `--apply` först när en
torrkörning granskats mot produktionen minst en gång.
"""

from __future__ import annotations

import argparse
import sys

import psycopg2

from gdpr_verktyg import dsn_for


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Radera på riktigt. Utan flaggan är körningen en torrkörning.",
    )
    parser.add_argument("--tenant", help="Bara den här tenanten (UUID eller slug).")
    parser.add_argument(
        "--satt-policy",
        type=int,
        metavar="DAGAR",
        help="Sätt retentionsperiod för --tenant och avsluta. Raderar ingenting.",
    )
    parser.add_argument("--beslutad-av", default="", help="Vem som fattade beslutet.")
    args = parser.parse_args()

    with psycopg2.connect(dsn_for(args.env)) as conn, conn.cursor() as cur:
        if args.satt_policy is not None:
            if not args.tenant or not args.beslutad_av:
                sys.exit("AVBRYTER: --satt-policy kräver både --tenant och --beslutad-av.")
            tenant_id = _slå_upp_tenant(cur, args.tenant)
            cur.execute(
                """
                insert into ss_gallringspolicy (tenant_id, dagar, beslutad_av)
                values (%s, %s, %s)
                on conflict (tenant_id)
                do update set dagar = excluded.dagar,
                              beslutad_av = excluded.beslutad_av,
                              beslutad_at = now()
                """,
                (tenant_id, args.satt_policy, args.beslutad_av),
            )
            print(f"Policy satt: {args.satt_policy} dagar för {args.tenant} ({args.beslutad_av}).")
            return 0

        if args.tenant:
            tenants = [(_slå_upp_tenant(cur, args.tenant), args.tenant)]
        else:
            cur.execute("select id, slug from ss_tenants order by slug")
            tenants = cur.fetchall()

        utan_policy = 0
        totalt = 0
        for tenant_id, slug in tenants:
            cur.execute("select dagar from ss_gallringspolicy where tenant_id = %s", (tenant_id,))
            rad = cur.fetchone()
            if not rad:
                utan_policy += 1
                continue

            cur.execute(
                "select gallra_supportdata(%s, %s)", (tenant_id, not args.apply)
            )
            antal = cur.fetchone()[0]
            totalt += antal
            verb = "raderade" if args.apply else "skulle radera"
            print(f"  {slug}: {verb} {antal} ärenden (policy: {rad[0]} dagar)")

        if not args.apply:
            print("\nTORRKÖRNING — ingenting raderades. Lägg till --apply när siffrorna stämmer.")
        print(f"Summa: {totalt} ärenden. {utan_policy} kunder saknar beslutad policy.")

        if utan_policy:
            print(
                "\nEn kund utan policy gallras INTE. Det är den ofarliga defaulten, "
                "men det är också en kund vars data ligger kvar för alltid — "
                "sätt en policy med --satt-policy."
            )
    return 0


def _slå_upp_tenant(cur, nyckel: str) -> str:
    cur.execute("select id from ss_tenants where id::text = %s or slug = %s", (nyckel, nyckel))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYTER: hittar ingen tenant med id/slug '{nyckel}'.")
    return rad[0]


if __name__ == "__main__":
    raise SystemExit(main())
