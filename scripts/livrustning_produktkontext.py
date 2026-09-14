#!/usr/bin/env python
"""Materialiserar Livrustnings produktbeskrivning — filen fanns, ledningen saknades.

    python scripts/livrustning_produktkontext.py --env development            # visar planen
    python scripts/livrustning_produktkontext.py --env development --apply

`snajp-support/app/tenants/livrustning_business_context.py` innehåller en
noggrant skriven produktbeskrivning för Livrustning (källor, invändningar,
förbjudna påståenden om garantitid) men importerades ingenstans i backenden —
bekräftat genom att filen saknar en `.pyc` i `__pycache__` medan syskonfilerna
(`livrustning_kb.py`, `snajp_kb.py`) har en. `require_business_context`
(app/leads/business_context.py) kräver minst 120 tecken `product_marketing`
innan ett utkast får skrivas — utan den här körningen har Livrustning alltså
troligen INGEN produktbeskrivning i drift, och varje utkastförsök avbryts med
"Produktbeskrivningen saknas för den här kunden".

Samma HTTPS-mönster som scripts/seed_demo.py (ingen direkt-SQL, se den filens
docstring för varför) — nyckeln mintas färskt via POST /api/keys med
masternyckeln, exakt som seed_demo.py redan gör för tenanten "snajp".
Idempotent: skriver bara en ny version om innehållet faktiskt ändrats.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "snajp-support"))

from seed_demo import Api, deploy_env  # noqa: E402

from app.tenants.livrustning_business_context import PRODUCT_MARKETING  # noqa: E402

SLUG = "livrustning"
TENANT_NAME = "Livrustning AB"  # måste matcha ss_tenants.name — create_tenant är en upsert


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas = store.get(f"{prefix}_API_URL")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    if not args.apply:
        sys.exit(
            "TORRKÖRNING stöds inte för nyckelmintningen (POST /api/keys skriver alltid). "
            "Kör igen med --apply — själva kontextdokumentet skrivs ändå bara om det ändrats."
        )

    status, svar = Api(bas, master, skarpt=True).anrop(
        "POST", "/api/keys", {"tenant_name": TENANT_NAME, "slug": SLUG}
    )
    if not 200 <= status < 300:
        sys.exit(f"AVBRYTER: kunde inte hämta nyckel för {SLUG} ({status}) — {svar.get('fel', '')}")
    nyckel = svar.get("api_key") or svar.get("key")
    if not nyckel:
        sys.exit(f"AVBRYTER: /api/keys gav inget nyckelfält. Svarsnycklar: {sorted(svar)}")

    api = Api(bas, nyckel, skarpt=True)
    print(f"Miljö: {args.env}  Backend: {bas}  Tenant: {SLUG}")

    dokument = api.get("/api/leads/context-docs?kind=product_marketing").get("docs", [])
    senaste = max(dokument, key=lambda d: d.get("version", 0), default=None)
    nuvarande = (senaste or {}).get("content", "").strip()
    print(f"Nuvarande produktbeskrivning: {len(nuvarande)} tecken (version {(senaste or {}).get('version', 0)}).")

    if nuvarande == PRODUCT_MARKETING.strip():
        print("Oförändrad — ingen ny version.")
        return

    status, svar = api.anrop(
        "POST",
        "/api/leads/context-docs",
        {
            "kind": "product_marketing",
            "content": PRODUCT_MARKETING,
            "source": "scripts/livrustning_produktkontext.py",
        },
    )
    if not 200 <= status < 300:
        sys.exit(f"AVBRYTER: skrivningen misslyckades ({status}) — {svar.get('fel', '')}")
    version = svar.get("doc", {}).get("version", "?")
    print(f"Skrev version {version} ({len(PRODUCT_MARKETING.strip())} tecken).")


if __name__ == "__main__":
    main()
