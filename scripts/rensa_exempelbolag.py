"""Ta bort origin='example'-prospekt från alla tenants utom demon.

Exempelbolag hör bara hemma på /demo (Nordlys Handel). En default-checkbox
i LeadsRunForm skapade dem på varje arbetsyta, inklusive Snajp Admin.

  python scripts/rensa_exempelbolag.py --env development
  python scripts/rensa_exempelbolag.py --env development --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snajp-support"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.config import DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID  # noqa: E402
from railway_migrate import dsn as railway_dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--env", choices=("main", "development"), default="development")
    args = parser.parse_args()

    sql = """
        select tenant_id, count(*) as n
        from prospects
        where origin = 'example'
          and tenant_id not in (%s, %s)
        group by tenant_id
        order by n desc
    """
    delete_sql = """
        delete from prospects
        where origin = 'example'
          and tenant_id not in (%s, %s)
    """

    import psycopg2

    conn = psycopg2.connect(railway_dsn(env_read(), args.env), connect_timeout=20)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID))
            rader = cur.fetchall()
            totalt = sum(n for _, n in rader)
            print(
                f"miljö={args.env}: {totalt} exempelbolag utanför demon, "
                f"fördelat på {len(rader)} tenants."
            )
            for tenant_id, n in rader:
                print(f"  {tenant_id}: {n}")
            if not args.apply:
                print("Torrkörning. Kör med --apply för att radera.")
                conn.rollback()
                return 0
            cur.execute(delete_sql, (DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID))
            print(f"Raderade {cur.rowcount} rader.")
        conn.commit()
        return 0
    except Exception as fel:  # noqa: BLE001
        conn.rollback()
        sys.exit(f"AVBRYT: {fel}")
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
