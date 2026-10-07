#!/usr/bin/env python3
"""Flyttar leads som Iris själv satt i Redo till Ny (Sebbe 2026-10-07).

    python scripts/flytta_redo_till_ny.py --env development            # torrkörning
    python scripts/flytta_redo_till_ny.py --env development --apply

Fram till 5e89a41 satte V2-researchen status `ready` på varje kvalificerat
bolag, så körningarnas fynd hamnade i Redo i stället för i Ny. Koden är
ändrad; det här skriptet flyttar de gamla.

Bara leads som Iris satte i Redo flyttas: en rad där kunden själv valt Redo
(statusloggen, migration 086, `till='ready'` med `kalla='manuell'`) rörs
inte. Varje flytt skrivs i statusloggen med kalla `kod`, i samma transaktion.
Idempotent: en andra körning hittar inget.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

URVAL = """
    select p.id, p.tenant_id, t.name as kund
      from prospects p
      join ss_tenants t on t.id = p.tenant_id
     where p.status = 'ready'
       and (%(tenant)s::uuid is null or p.tenant_id = %(tenant)s::uuid)
       and not exists (
         select 1 from prospect_status_logg l
          where l.prospect_id = p.id and l.till = 'ready' and l.kalla = 'manuell'
       )
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=("main", "development"), required=True)
    ap.add_argument("--tenant", help="Bara den här kunden (uuid).")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = psycopg2.connect(dsn(env_read(), args.env))
    try:
        with conn, conn.cursor() as cur:
            cur.execute(URVAL, {"tenant": args.tenant})
            rader = cur.fetchall()
            per_kund: dict[str, int] = {}
            for _, _, kund in rader:
                per_kund[kund] = per_kund.get(kund, 0) + 1
            for kund, antal in sorted(per_kund.items(), key=lambda x: -x[1]):
                print(f"  {antal:4d}  {kund}")
            print(f"{len(rader)} leads i Redo satta av Iris ({args.env}).")
            if not args.apply or not rader:
                if rader:
                    print("Torrkörning. Lägg till --apply för att flytta dem till Ny.")
                return 0
            ids = [str(r[0]) for r in rader]
            cur.execute(
                """
                insert into prospect_status_logg (tenant_id, prospect_id, fran, till, kalla)
                select tenant_id, id, 'ready', 'new', 'kod'
                  from prospects where id = any(%s::uuid[]) and status = 'ready'
                """,
                (ids,),
            )
            cur.execute(
                "update prospects set status = 'new' where id = any(%s::uuid[]) and status = 'ready'",
                (ids,),
            )
            print(f"Flyttade {cur.rowcount} leads till Ny.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
