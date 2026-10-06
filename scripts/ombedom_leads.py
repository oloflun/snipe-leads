#!/usr/bin/env python
"""Bedömer om sparade Iris-leads med dagens regler. Torrkör som standard.

    python scripts/ombedom_leads.py --env development                # visa vad som rörs
    python scripts/ombedom_leads.py --env development --apply        # köa ombedömningen
    python scripts/ombedom_leads.py --env development --kund snajp --apply
    python scripts/ombedom_leads.py --env development --rapport      # utfallet efteråt

Skälet (2026-10-06): varje lead kräver nu ett belagt behov av det kunden
säljer, och ett obelagt måste-krav fäller. Leads som redan står i listan
bedömdes med de gamla reglerna. Ombedömningen kör om researchen för dem via
/api/admin/tenants/<id>/leads-ombedom (se app/api/admin_ombedom.py): bara
Iris- och testleads med nivå A/B och status Ny/Redo, bara research, aldrig
utkast. Ett bolag som inte klarar reglerna blir nivå C och försvinner ur
kundens lista; raden står kvar för dedupliceringen.

Kostar ett researchanrop per lead (cirka 0,2 kr) plus sidhämtning.
Mot main krävs --main-godkant: varje skrivning mot produktionen kräver
Antons uttryckliga ord (CLAUDE.md). Nyckeln läses ur .env.deploy och skrivs
aldrig ut.
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from seed_demo import Api, deploy_env  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--kund", help="bara den här kundens slug")
    parser.add_argument("--apply", action="store_true", help="köa ombedömningen (annars torrkörning)")
    parser.add_argument("--rapport", action="store_true", help="visa nivåerna för Iris-leads nu")
    parser.add_argument("--main-godkant", action="store_true", help="Anton har godkänt skrivningen mot main")
    args = parser.parse_args()
    if args.env == "main" and args.apply and not args.main_godkant:
        sys.exit("AVBRYTER: --apply mot main kräver --main-godkant (Antons uttryckliga ord).")

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas, master = store.get(f"{prefix}_API_URL"), store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")
    api = Api(bas, master, skarpt=True)

    totalt = 0
    for kund in api.get("/api/admin/tenants").get("tenants") or []:
        if args.kund and kund.get("slug") != args.kund:
            continue
        namn = f"{kund.get('name')} ({kund.get('slug')})"
        if args.rapport:
            _, svar = api.anrop("GET", f"/api/admin/tenants/{kund['id']}/leads-underlag", None)
            leads = [l for l in svar.get("leads") or [] if l.get("origin") in ("iris", "test")]
            if leads:
                per = collections.Counter(l.get("niva") or "-" for l in leads)
                print(f"{namn}: " + ", ".join(f"nivå {k}: {v}" for k, v in sorted(per.items())))
            continue
        status, svar = api.anrop(
            "POST", f"/api/admin/tenants/{kund['id']}/leads-ombedom", {"apply": args.apply}
        )
        if status == 404 and "Kunden" not in str(svar):
            sys.exit("AVBRYTER: api:t saknar /leads-ombedom. Vänta in deployen.")
        if status != 200:
            print(f"{namn}: {status} {svar.get('detail') or svar}")
            continue
        if not svar.get("antal"):
            continue
        totalt += svar["antal"]
        per = collections.Counter(f"{l['origin']}/{l['niva']}/{l['status']}" for l in svar["leads"])
        print(f"{namn}: {svar['antal']} leads ({', '.join(f'{k} {v}' for k, v in sorted(per.items()))})"
              + (f", {len(svar.get('jobb') or [])} jobb köade" if args.apply else ""))
    if not args.rapport:
        print(f"\n{totalt} leads i {args.env}. "
              + ("Ombedömningen är köad; kör --rapport när jobben gått klart." if args.apply
                 else "Torrkörning — ingenting köat. Lägg till --apply."))


if __name__ == "__main__":
    main()
