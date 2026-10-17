#!/usr/bin/env python
"""Läser hur Iris-utkasten står per kund. Bara antal, inga adresser eller texter.

    python scripts/utkast_status.py --env development

Skälet (2026-10-07): Leads-översikten visade "Utkast att godkänna 0" och
"Skickade mejl 0" trots utkast i lådan och godkända utskick. Räknaren läser
bara awaiting_review; ett godkänt utkast utanför sändfönstret står som queued
och skickas av run_godkand_sandare när fönstret öppnar (vardagar 08-16).
Skriptet visar fördelningen så att ingen behöver gissa. Läsande transaktion.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

FRAGOR = {
    "Köposter per status": """
        select t.slug, q.status,
               case when q.status = 'queued' and q.gate_checks->>'approved_by' = 'human'
                    then 'godkänd av människa' when q.status = 'queued' then 'utan godkännande'
                    else '' end,
               count(*), min(q.scheduled_at), max(q.scheduled_at)
        from send_queue q join ss_tenants t on t.id = q.tenant_id
        group by 1, 2, 3 order by 1, 2, 3""",
    "Skickade meddelanden senaste 28 dygnen": """
        select t.slug, m.direction, count(*)
        from outreach_messages m join outreach_threads th on th.id = m.thread_id
        join ss_tenants t on t.id = th.tenant_id
        where m.sent_at > now() - interval '28 days'
        group by 1, 2 order by 1, 2""",
    "Prospekt per status (ej exempel/test)": """
        select t.slug, p.status, count(*)
        from prospects p join ss_tenants t on t.id = p.tenant_id
        where coalesce(p.origin, '') not in ('example', 'test')
        group by 1, 2 order by 1, 2""",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=("development", "main"), default="development")
    args = parser.parse_args()
    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            for rubrik, sql in FRAGOR.items():
                print(f"\n## {rubrik}")
                cur.execute(sql)
                for rad in cur.fetchall():
                    print("  " + " | ".join("" if v is None else str(v) for v in rad))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
