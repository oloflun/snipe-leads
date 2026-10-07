#!/usr/bin/env python
"""Flyttar äldre köade utkast UTAN mänskligt godkännande till granskningskön.
Torrkörning som standard, bara development.

    python scripts/koade_utkast_till_granskning.py                 # visar antal per kund
    python scripts/koade_utkast_till_granskning.py --kund snajp    # en kund
    python scripts/koade_utkast_till_granskning.py --apply         # flyttar

Skälet (2026-10-08): utkast köades förr som 'queued' utan att någon
schemaläggare körde dem (SEND_QUEUE_POLL_SECONDS osatt i båda miljöerna).
De syns ingenstans: inte i "Utkast att godkänna" (bara awaiting_review), inte
som skickade, och run_godkand_sandare rör dem inte (bara approved_by='human').
Här blir de 'awaiting_review', så att en människa ser och avgör dem.

Skydd:
- Rader med `gate_checks.approved_by = 'human'` rörs ALDRIG: en människa har
  sagt ja, och run_godkand_sandare skickar dem när sändfönstret öppnar.
- Bara poster vars tråd har ett väntande utkast (osänt, icke-kasserat): en
  post utan text att granska hade blivit en tom rad i kön. De räknas separat.
- Bara development; main vägras. Allt i EN transaktion som rullas tillbaka om
  antalet inte stämmer med torrkörningen. Inga adresser eller texter skrivs ut.
Lösenordet läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

#: Köposterna som flyttas: köade, utan mänskligt godkännande, med text.
URVAL = """
    from send_queue q
    join ss_tenants t on t.id = q.tenant_id
    where q.status = 'queued'
      and coalesce(q.gate_checks->>'approved_by', '') <> 'human'
      and (%(kund)s::text is null or t.slug = %(kund)s::text)
      and {med_text} exists (
        select 1 from outreach_messages m
         where m.thread_id = q.thread_id and m.direction = 'outbound'
           and m.sent_at is null and m.kasserad_at is null
      )
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="development")
    parser.add_argument("--kund", default=None, help="bara den här kundens slug")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.env != "development":
        sys.exit("AVBRYTER: skriptet körs bara mot development. Main rörs inte härifrån.")

    conn = psycopg2.connect(dsn(env_read(), "development"), connect_timeout=20)
    try:
        with conn, conn.cursor() as cur:
            parametrar = {"kund": args.kund}
            cur.execute(
                "select t.slug, count(*) " + URVAL.format(med_text="") + " group by 1 order by 1",
                parametrar,
            )
            per_kund = cur.fetchall()
            cur.execute("select count(*) " + URVAL.format(med_text="not"), parametrar)
            utan_text = cur.fetchone()[0]
            antal = sum(int(n) for _, n in per_kund)
            print("Köade utkast utan mänskligt godkännande, med text att granska:")
            for slug, n in per_kund:
                print(f"  {slug}: {n}")
            print(f"Totalt {antal}. Utan väntande text (rörs inte): {utan_text}.")
            if not args.apply:
                print("Inget ändrat; kör med --apply för att flytta dem till granskningskön.")
                return 0
            cur.execute(
                "update send_queue set status = 'awaiting_review',"
                " gate_checks = gate_checks || jsonb_build_object("
                "   'till_granskning', 'koade_utkast_till_granskning', 'flyttad_at', now()::text)"
                " where id in (select q.id " + URVAL.format(med_text="") + ")",
                parametrar,
            )
            if cur.rowcount != antal:
                raise RuntimeError(f"flyttade {cur.rowcount}, väntade {antal}; rullar tillbaka")
            print(f"{cur.rowcount} utkast flyttade till granskningskön i development.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
