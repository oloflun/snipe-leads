#!/usr/bin/env python
"""Bedömer och fördelar alla kunders gamla leads i webbpoolen. Torrkör som standard.

    python scripts/webbpool_bakatfyll.py --env main                      # läget och kostnaden
    python scripts/webbpool_bakatfyll.py --env main --apply --main-godkant
    python scripts/webbpool_bakatfyll.py --env main --apply --main-godkant --max 500
    python scripts/webbpool_bakatfyll.py --env main --folj               # följ en pågående körning

Antons beställning 2026-11-22: de gamla leadsen (4 000+ hos Snajp) ska gå
igenom webbbedömningen och fördelas till Alunix och Umeå Webbdesign, men bara
när Anton säger till efter att ScrapeGraph-krediten fyllts på. Ingen körning
startar den här bakåtfyllnaden. Api:t vägrar starta om saldot inte räcker
(cirka 2 krediter per sajt). Avbryts körningen startar --apply om där den
slutade.

Logiken finns i snajp-support/app/leads/webbpool.py (bakatfyll), endpointen
i app/api/admin_webbpool.py. Nyckeln läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from seed_demo import Api, deploy_env  # noqa: E402


def visa(svar: dict) -> None:
    nivaer = ", ".join(f"{k} {v}" for k, v in sorted((svar.get("nivaer") or {}).items()))
    print(f"Domäner hos källkunderna: {svar.get('domaner')} ({nivaer})")
    print(f"Kvar att bedöma: {svar.get('kvar_att_bedoma')}, kräver cirka {svar.get('krediter_behov')} krediter")
    print(f"ScrapeGraph-krediter kvar: {svar.get('krediter_kvar')}")
    k = svar.get("korning") or {}
    if k:
        print(f"Körning: {'pågår' if k.get('pagar') else 'klar'}, {k.get('bedomda', 0)} av {k.get('mal')} bedömda"
              + (f", fel: {k['fel']}" if k.get("fel") else "")
              + (f", fördelat: {k['fordelat']}" if k.get("fordelat") else ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--apply", action="store_true", help="starta bakåtfyllnaden (annars torrkörning)")
    parser.add_argument("--max", type=int, help="högst så många sajter i den här körningen")
    parser.add_argument("--folj", action="store_true", help="visa läget varje minut tills körningen är klar")
    parser.add_argument("--main-godkant", action="store_true", help="Anton har godkänt körningen mot main")
    args = parser.parse_args()
    if args.env == "main" and args.apply and not args.main_godkant:
        sys.exit("AVBRYTER: --apply mot main kräver --main-godkant (Antons uttryckliga ord).")

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas, master = store.get(f"{prefix}_API_URL"), store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")
    api = Api(bas, master, skarpt=True)

    if args.folj:
        while True:
            _, svar = api.anrop("GET", "/api/admin/webbpool/bakatfyll", None)
            visa(svar)
            if not (svar.get("korning") or {}).get("pagar"):
                return
            print("---")
            time.sleep(60)

    status, svar = api.anrop("POST", "/api/admin/webbpool/bakatfyll", {"apply": args.apply, "max_bedom": args.max})
    if status == 404:
        sys.exit("AVBRYTER: api:t saknar /api/admin/webbpool/bakatfyll. Vänta in deployen.")
    if status != 200:
        sys.exit(f"{status} {svar.get('detail') or svar}")
    visa(svar)
    if svar.get("fel"):
        sys.exit(f"STARTADE INTE: {svar['fel']}")
    print(f"\nStartad: {svar['ska_bedomas']} sajter. Följ med --folj." if svar.get("startad")
          else "\nTorrkörning: ingenting startat. Lägg till --apply.")


if __name__ == "__main__":
    main()
