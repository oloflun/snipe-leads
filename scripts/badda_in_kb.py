#!/usr/bin/env python
"""Bäddar in kunskapsartiklar som saknar vektor (fas 9, 2026-10-06).

    python scripts/badda_in_kb.py --env development            # räknar bara
    python scripts/badda_in_kb.py --env development --apply    # bäddar in

Artiklarna som sparades medan Vertex OpenAI-kompatibla inbäddningsväg svarade
500 (2026-09-12 till 2026-10-06) saknar vektor, så hybridsökningen i
kunskapsbasen hittar dem bara med fulltext. Endpointen tar högst 50 artiklar
per kund och anrop; skriptet kör om tills inget är kvar eller inget händer.
Nyckeln läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from seed_demo import Api, deploy_env  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas, master = store.get(f"{prefix}_API_URL"), store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")
    api = Api(bas, master, skarpt=True)

    forra = None
    while True:
        status, svar = api.anrop("POST", f"/api/admin/kb/badda-in?apply={'true' if args.apply else 'false'}", None)
        if status != 200:
            sys.exit(f"AVBRYTER: svarade {status} — {svar.get('fel', '')}")
        for k in svar["kunder"]:
            print(f"  {k['tenant_id']}: {k['utan_vektor']} utan vektor, {k['inbaddade']} inbäddade")
        print(f"Kvar: {svar['kvar']}")
        if not args.apply or svar["kvar"] == 0:
            break
        if svar["kvar"] == forra:
            sys.exit("AVBRYTER: inget blev inbäddat i förra varvet — inbäddningarna svarar inte.")
        forra = svar["kvar"]


if __name__ == "__main__":
    main()
