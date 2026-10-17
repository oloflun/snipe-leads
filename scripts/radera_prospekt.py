#!/usr/bin/env python
"""Raderar namngivna prospekt hos EN kund i development. Torrkörning som standard.

    python scripts/radera_prospekt.py --kund snajp --id <uuid> --id <uuid>          # visar bara
    python scripts/radera_prospekt.py --kund snajp --id <uuid> ... --apply          # raderar

Skälet (2026-10-06): inventeringen (scripts/granska_leads_underlag.py) pekade
ut nio Iris-leads hos Snajp i development som inte går att styrka: tre bolag
som inte finns, skolor och leads utan hämtat underlag. Anton beslutade att de
ska bort. Appens roll har ingen delete på prospects (by design), så raderingen
går som ägaren, på samma anslutning som scripts/railway_migrate.py.

Skydd: bara development (main vägras), bara id:n som tillhör den namngivna
kunden, allt i EN transaktion som rullas tillbaka om antalet inte stämmer.
Barnrader (källor, statuslogg, anteckningar, uppgifter, trådar) följer med via
on delete cascade; agent_runs.prospect_id sätts till null (025).
Lösenordet läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kund", required=True, help="kundens slug, t.ex. snajp")
    parser.add_argument("--id", action="append", required=True, dest="ids")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ids = [str(uuid.UUID(i)) for i in args.ids]

    conn = psycopg2.connect(dsn(env_read(), "development"), connect_timeout=20)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("select id from ss_tenants where slug = %s", (args.kund,))
            rad = cur.fetchone()
            if not rad:
                sys.exit(f"AVBRYTER: kunden {args.kund!r} finns inte.")
            tenant_id = rad[0]
            cur.execute(
                "select id, company_name, status, niva from prospects where tenant_id = %s and id = any(%s::uuid[])",
                (tenant_id, ids),
            )
            hittade = cur.fetchall()
            for pid, namn, status, niva in hittade:
                print(f"  {namn}  status={status} nivå={niva}  id={pid}")
            if len(hittade) != len(ids):
                sys.exit(f"AVBRYTER: {len(hittade)} av {len(ids)} id:n hör till {args.kund}. Inget raderat.")
            if not args.apply:
                print(f"{len(hittade)} prospekt skulle raderas. Inget ändrat; kör med --apply.")
                return 0
            cur.execute("delete from prospects where tenant_id = %s and id = any(%s::uuid[])", (tenant_id, ids))
            if cur.rowcount != len(ids):
                raise RuntimeError(f"raderade {cur.rowcount}, väntade {len(ids)}; rullar tillbaka")
            print(f"{cur.rowcount} prospekt raderade i development.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
