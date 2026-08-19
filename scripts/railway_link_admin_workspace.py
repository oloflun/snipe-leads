#!/usr/bin/env python
"""Koppla plattformsadminens egen workspace till en tenant.

    python scripts/railway_link_admin_workspace.py --env railway-development --diagnos
    python scripts/railway_link_admin_workspace.py --env railway-development

## Varför

Adminytan är en SUPERSET av kundens arbetsyta — "Min arbetsyta", Leads, Email
studio, Kontroll och Kundtjänst renderas av samma komponenter som kundens
`/dashboard`. De talar alla med backenden genom `requireSnajpTenant()`, som
härleder kunden ur `workspaces.slug`.

Adminens workspace hade ingen slug. Uppmätt på railway-development: av åtta
workspaces var exakt en (`Livrustning AB`) kopplad. Följden var 409 —
"Arbetsytan är inte kopplad till någon kund ännu" — på varje flik i den nedre
raden. Ytan renderade, grinden höll, och innehållet var ändå tomt.

`snajp` och inte en egen tenant: vi använder produkten själva, tenanten finns
redan i `ss_tenants` och i `lib/tenants/index.ts`, och `/chat/snajp` pekar
redan på den. En ny tenant hade krävt en ny configfil för ingen vinst.

Idempotent. Skriver bara om värdet skiljer sig, och vägrar skriva över en
workspace som redan pekar på någon ANNAN kund — den kopplingen är alltid
avsiktlig, och att tyst flytta den byter kund under en inloggad användare.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402
from admin_cleanup import ADMIN_EMAIL, ENVIRONMENTS, dsn_for  # noqa: E402

SLUG = "snajp"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env", choices=sorted(ENVIRONMENTS), default="railway-development")
    p.add_argument("--slug", default=SLUG)
    p.add_argument("--diagnos", action="store_true", help="Läs bara.")
    args = p.parse_args()

    conn = psycopg2.connect(dsn_for(ENVIRONMENTS[args.env]))
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        "select w.id, w.name, w.slug, w.ss_tenant_id from public.workspaces w "
        "join public.profiles pr on pr.workspace_id = w.id "
        "join auth.users u on u.id = pr.id where lower(u.email) = lower(%s)",
        (ADMIN_EMAIL,),
    )
    row = cur.fetchone()
    if not row:
        sys.exit(f"AVBRYTER: {ADMIN_EMAIL} har ingen workspace i {args.env}.")
    ws_id, ws_name, ws_slug, ws_tenant = row

    cur.execute("select id, name from public.ss_tenants where slug = %s", (args.slug,))
    tenant = cur.fetchone()
    if not tenant:
        sys.exit(
            f"AVBRYTER: ingen tenant med slug '{args.slug}' i ss_tenants. "
            "Kör scripts/railway_tenant_keys.py först — POST /api/keys upsertar den."
        )
    tenant_id, tenant_name = tenant

    print(f"miljö: {args.env}")
    print(f"  workspace ... {ws_name} ({ws_id})")
    print(f"  slug nu ..... {ws_slug!r}  ss_tenant_id {ws_tenant}")
    print(f"  tenant ...... {args.slug} = {tenant_name} ({tenant_id})")

    if ws_slug == args.slug and str(ws_tenant) == str(tenant_id):
        print("  → redan kopplad, ingenting att göra.")
        return
    if ws_slug and ws_slug != args.slug:
        sys.exit(
            f"AVBRYTER: workspacet pekar redan på '{ws_slug}'. Att flytta en "
            "befintlig koppling byter kund under en inloggad användare — gör det "
            "för hand om det är avsiktligt."
        )
    if args.diagnos:
        print("  → skulle kopplas. Kör utan --diagnos.")
        return

    cur.execute(
        "update public.workspaces set slug = %s, ss_tenant_id = %s where id = %s",
        (args.slug, tenant_id, ws_id),
    )
    print(f"  → kopplad till {args.slug}.")


if __name__ == "__main__":
    main()
