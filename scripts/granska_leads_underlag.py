#!/usr/bin/env python
"""Listar sparade leads som inte går att styrka. Läser bara, raderar ingenting.

    python scripts/granska_leads_underlag.py --env development
    python scripts/granska_leads_underlag.py --env development --kund snajp

Skälet (2026-10-06): provkörningen 2026-10-05 sparade tre bolag som inte finns
("Exempel E-handel AB", "Detaljhandel Design AB", "Byggmästarna i Göteborg AB").
Kodgrindarna stoppar nya (app/leads/existens.py), men de som redan står i
tabellen står kvar. Det här skriptet pekar ut dem; vad som ska bort avgör Anton.

Ett lead flaggas när minst ett av följande gäller:
  * domänen går inte att slå upp (DNS),
  * det är inte ett registerbolag och ingen sida har hämtats för det,
  * det står som Redo men saknar godkänd bedömning (nivå A eller B).

Kräver att api:t har endpointen /api/admin/tenants/<id>/leads-underlag
(deployad med samma ändring). Nyckeln läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import pathlib
import socket
import sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from seed_demo import Api, deploy_env  # noqa: E402


def doman_finns(webb: str | None) -> bool | None:
    """None = ingen webbplats angiven."""
    host = urlparse(webb if "://" in (webb or "") else f"https://{webb}").hostname if webb else None
    if not host:
        return None
    try:
        socket.getaddrinfo(host, 443)
        return True
    except OSError:
        return False


def flaggor(lead: dict) -> list[str]:
    ut: list[str] = []
    if doman_finns(lead.get("website")) is False:
        ut.append("domänen finns inte")
    if not lead.get("register") and not lead.get("hamtat_tecken"):
        ut.append("ingen sida hämtad och inget registerutdrag")
    if lead.get("status") == "ready" and lead.get("niva") not in ("A", "B"):
        ut.append("Redo utan godkänd bedömning")
    return ut


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--kund", help="bara den här kundens slug")
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas, master = store.get(f"{prefix}_API_URL"), store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")
    api = Api(bas, master, skarpt=True)

    totalt = flaggade = 0
    for kund in api.get("/api/admin/tenants").get("tenants") or []:
        if args.kund and kund.get("slug") != args.kund:
            continue
        status, svar = api.anrop("GET", f"/api/admin/tenants/{kund['id']}/leads-underlag", None)
        if status == 404:
            sys.exit("AVBRYTER: api:t saknar /leads-underlag. Deploya ändringen först.")
        leads = [l for l in svar.get("leads") or [] if l.get("origin") == "iris"]
        traffar = [(l, f) for l in leads if (f := flaggor(l))]
        totalt += len(leads)
        flaggade += len(traffar)
        if not traffar:
            continue
        print(f"\n{kund.get('name')} ({kund.get('slug')}): {len(traffar)} av {len(leads)} Iris-leads")
        for lead, skal in traffar:
            print(
                f"  {lead.get('company_name')}  {lead.get('website') or '-'}  "
                f"status={lead.get('status') or '-'} nivå={lead.get('niva') or '-'} "
                f"poäng={lead.get('score_total')}\n      {'; '.join(skal)}  id={lead['id']}"
            )
    print(f"\n{flaggade} av {totalt} Iris-leads flaggade i {args.env}. Ingenting har ändrats.")


if __name__ == "__main__":
    main()
