"""Ta bort origin='example'-prospekt från alla tenants utom demon.

Exempelbolag hör bara hemma på /demo (Nordlys Handel). En default-checkbox
i LeadsRunForm skapade dem på varje arbetsyta, inklusive Snajp Admin.

  python scripts/rensa_exempelbolag.py              # torrkörning
  python scripts/rensa_exempelbolag.py --apply      # development
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snajp-support"))

from app.config import DEFAULT_TENANT_ID  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    sql = """
        select tenant_id, count(*) as n
        from prospects
        where origin = 'example'
          and tenant_id <> %s
        group by tenant_id
        order by n desc
    """
    delete_sql = """
        delete from prospects
        where origin = 'example'
          and tenant_id <> %s
    """

    # Lokal/CI: skriv bara vad som skulle göras om DATABASE_URL saknas.
    import os

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL saknas — ingen databas att städa.")
        print(f"Skulle radera origin=example där tenant_id <> {DEFAULT_TENANT_ID}")
        return 0

    import psycopg

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (DEFAULT_TENANT_ID,))
            rader = cur.fetchall()
            totalt = sum(n for _, n in rader)
            print(f"{totalt} exempelbolag utanför demon, fördelat på {len(rader)} tenants.")
            for tenant_id, n in rader:
                print(f"  {tenant_id}: {n}")
            if not args.apply:
                print("Torrkörning. Kör med --apply för att radera.")
                return 0
            cur.execute(delete_sql, (DEFAULT_TENANT_ID,))
            print(f"Raderade {cur.rowcount} rader.")
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
