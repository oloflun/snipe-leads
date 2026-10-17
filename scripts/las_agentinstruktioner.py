#!/usr/bin/env python
"""Visar vilka globala agentinstruktioner en miljö FAKTISKT kör på. Läser bara.

    python scripts/las_agentinstruktioner.py --env development
    python scripts/las_agentinstruktioner.py --env development --text   # även texterna

Skälet (2026-10-06): en mall som klistrades in under Globala agentinstruktioner
ersatte hela instruktionsblocket, och ingenting i adminytan visade vad som stod
där före. Det här svarar på tre frågor utan att öppna databasen: läser agenten
filen eller en sparad rad, när sparades raden, och vad stod i råtexten.

Samma HTTPS-mönster som scripts/livrustning_produktkontext.py. Nyckeln läses ur
.env.deploy och skrivs aldrig ut.
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
    parser.add_argument("--text", action="store_true", help="skriv även ut den aktiva texten och råtexten")
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas = store.get(f"{prefix}_API_URL")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    rad = Api(bas, master, skarpt=True).get("/api/admin/instruktioner").get("instruktioner") or {}
    aktiv = rad.get("aktiv_text") or ""
    print(f"Miljö: {args.env}")
    print(f"Läser agenten filen (agent-core/AGENTS.md)? {'ja' if rad.get('fran_fil') else 'NEJ, en sparad rad'}")
    print(f"Aktiv text: {len(aktiv)} tecken, hash {rad.get('hash')}")
    print(f"Sparad rad: källa={rad.get('kalla') or '-'}  uppdaterad={rad.get('uppdaterad') or '-'}")
    print(f"Råtext: {len(rad.get('ravtext') or '')} tecken")
    print("Historik (nyast först):")
    for h in rad.get("historik") or []:
        print(
            f"  {h.get('created_at')}  aktiv={h.get('aktiv')}  källa={h.get('kalla')}  "
            f"dokument={h.get('tecken') or h.get('strukturerad_tecken')}  råtext={h.get('rav_tecken')}"
        )
    if args.text:
        print("\n===== AKTIV TEXT =====\n" + aktiv)
        print("\n===== RÅTEXT =====\n" + (rad.get("ravtext") or ""))


if __name__ == "__main__":
    main()
