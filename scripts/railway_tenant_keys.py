#!/usr/bin/env python
"""Utfärda kundernas API-nycklar och sätt dem på Railways `web`-tjänst.

    python scripts/railway_tenant_keys.py --env development
    python scripts/railway_tenant_keys.py --env development --apply

## Varför skriptet behövde finnas

`keys.py --push-railway` skickar LLM-nycklar till `api`. `onboard_tenant.py`
skriver `SNAJP_KEY_*` till Vercel — och kände bara till Supabase-miljöerna
(`production`, `preview`). Railway-stacken hade alltså ingen ingång alls, exakt
samma lucka som `admin_cleanup.py` hade för adminraden.

Följden är uppmätt, inte antagen: `web` i miljön `development` hade NOLL
`SNAJP_KEY_*`-variabler, och varje inloggad yta som talar med backenden
(`/admin/leads/kontroll`, `/admin/support`, hela kundens `/dashboard/*`) föll på
`requireSnajpTenant()` med 409 eller 503.

## Varför nya nycklar och inte de befintliga

`POST /api/keys` returnerar rånyckeln EN gång; backenden lagrar bara hashen.
Det finns alltså inget att kopiera från main. Nycklarna är dessutom
miljöspecifika med flit — samma resonemang som `SNAJP_MASTER_API_KEY` i
`RAILWAY.md`: en delad nyckel gör dev-frontenden till en giltig klient mot
main-backenden.

Anropet upsertar tenanten, så det är idempotent i backenden. Varje körning ger
en NY nyckel för samma tenant; det är ofarligt (den gamla slutar användas när
variabeln skrivs över) men skriptet är därför inte en no-op — kör det när det
behövs, inte i en loop.

Utan `--apply` skrivs ingenting: skriptet listar vad som skulle utfärdas.

## Läckagespärr

Rånyckeln går från HTTP-svaret rakt in i Railway-mutationen. Den skrivs aldrig
ut, aldrig till en fil, och aldrig till ett skalkommando.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from onboard_tenant import create_tenant_and_key  # noqa: E402
from railway_provision import (envs_by_name, services_by_name,  # noqa: E402
                               set_vars, deploy, env_read)

#: Kunderna som ska ha en nyckel i web-tjänsten. Speglar `lib/tenants/index.ts`
#: — en tenant som saknas där har ingen configfil och kan aldrig nås ändå.
TENANTS = {
    "livrustning": "Livrustning AB",
    "snajp": "Snajp",
}


def env_key(slug: str) -> str:
    """Samma härledning som onboard_tenant.py och lib/tenants/*.ts."""
    return f"SNAJP_KEY_{slug.upper().replace('-', '_')}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=("main", "development"), default="development")
    parser.add_argument("--apply", action="store_true", help="Utfärda och skriv på riktigt.")
    args = parser.parse_args()

    prefix = f"RAILWAY_{args.env.upper()}_"
    store = env_read()
    api_url = store.get(f"{prefix}API_URL")
    master = store.get(f"{prefix}MASTER_API_KEY")
    if not api_url or not master:
        sys.exit(
            f"AVBRYTER: {prefix}API_URL eller {prefix}MASTER_API_KEY saknas i .env.deploy."
        )

    print(f"miljö: {args.env}   api: {api_url}")
    for slug, name in TENANTS.items():
        print(f"  {env_key(slug)}  ({slug} — {name})")
    if not args.apply:
        print("\nInget gjort. Kör med --apply.")
        return

    project = None
    from railway_provision import state
    project = state()
    environments = envs_by_name(project)
    services = services_by_name(project)
    if args.env not in environments:
        sys.exit(f"AVBRYTER: miljön {args.env} finns inte i projektet.")
    env_id = environments[args.env]

    payload: dict[str, str] = {}
    for slug, name in TENANTS.items():
        result = create_tenant_and_key(api_url, master, slug, name)
        raw = result.get("api_key") or result.get("key") or result.get("raw_key")
        if not raw:
            sys.exit(
                f"AVBRYTER: /api/keys svarade utan nyckelfält för {slug}. "
                f"Fälten var: {sorted(result)}"
            )
        payload[env_key(slug)] = raw
        print(f"  {env_key(slug)}: utfärdad")   # namn, aldrig värdet

    set_vars(services["web"]["id"], env_id, payload)
    print(f"  deploy: {deploy(services['web']['id'], env_id)}")
    print("\nKlart. Vänta på deployen och kör sedan:")
    print(f"  BASE={store.get(prefix + 'WEB_URL')} node scripts/qa_vyer.mjs")


if __name__ == "__main__":
    main()
