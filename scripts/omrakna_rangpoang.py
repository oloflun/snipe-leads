#!/usr/bin/env python3
"""Räknar om score_total till rangpoängen för godkända leads (Sebbe 2026-10-07).

    python scripts/omrakna_rangpoang.py --env development            # torrkörning
    python scripts/omrakna_rangpoang.py --env development --apply

Rangpoängen (snajp-support/app/leads/rangpoang.py) ersätter grindens poäng,
som var 100 för varje synligt lead. Allt den behöver står redan på
prospektraden, så omräkningen gör inga sökningar och inga modellanrop.

Bara godkända leads (nivå A/B, qualified inte false) räknas om: ett bortvalt
bolags poäng är grindens och står kvar. Nivå, qualified och icp_fit (kundens
tröskel) rörs inte. Idempotent.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import psycopg2

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "scripts"))
sys.path.insert(0, str(ROT / "snajp-support"))

from app.leads.rangpoang import rangpoang  # noqa: E402
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

URVAL = """
    select p.id, t.name, p.score_total, p.jev, p.score_breakdown, p.contact_name, p.contact_email, p.signaler
      from prospects p
      join ss_tenants t on t.id = p.tenant_id
     where p.niva in ('A', 'B') and p.qualified is not false and p.score_breakdown is not null
       and (%(tenant)s::uuid is null or p.tenant_id = %(tenant)s::uuid)
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
            andringar: list[tuple[int, str]] = []
            per_kund: dict[str, list[tuple[int | None, int]]] = {}
            for pid, kund, fore, jev, sb, cn, ce, sig in cur.fetchall():
                ny = rangpoang({"jev": jev, "score_breakdown": sb, "contact_name": cn,
                                "contact_email": ce, "signaler": sig})
                per_kund.setdefault(kund, []).append((fore, ny))
                if fore != ny:
                    andringar.append((ny, str(pid)))
            for kund, par in sorted(per_kund.items()):
                fore = [f for f, _ in par if f is not None]
                nya = [n for _, n in par]
                print(f"  {kund}: {len(par)} leads | före {min(fore, default=0)}–{max(fore, default=0)}"
                      f" (median {statistics.median(fore) if fore else '-'}) | efter {min(nya)}–{max(nya)}"
                      f" (median {statistics.median(nya)})")
            print(f"{len(andringar)} leads får ny poäng ({args.env}).")
            if not args.apply or not andringar:
                if andringar:
                    print("Torrkörning. Lägg till --apply för att skriva.")
                return 0
            cur.executemany("update prospects set score_total = %s where id = %s::uuid", andringar)
            print(f"Skrev {len(andringar)} poäng.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
