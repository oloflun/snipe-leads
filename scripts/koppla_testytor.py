#!/usr/bin/env python3
"""Ger befintliga testarbetsytor varsin EGEN backend-tenant.

    python scripts/koppla_testytor.py --env development
    python scripts/koppla_testytor.py --env development --apply

## Varför den behövs

Onboardingen skapar sedan migration 040 en egen tenant per testarbetsyta. Men
den körs bara för NYA konton. Arbetsytor som redan finns står kvar med
`slug = null`, och `requireSnajpTenant()` svarar då 409 på varenda av deras
egna ytor — Kontroll, Kundtjänst och Röst. En testkund som inte kan använda
produkten testar ingenting, vilket är exakt symptomet som en gång motiverade
den delade `testkund`-tenanten.

Uppmätt i development 2026-08-20: nio arbetsytor utan slug, varav tre skapade
genom testkundsflödet den 19 augusti.

## Vad skriptet INTE gör

* **Rör aldrig en arbetsyta som redan har en slug.** Villkoret sitter dessutom
  i `link_test_tenant` (migration 040), som är den enda som får skriva.
* **Kopplar aldrig till en annan kunds tenant.** Sluggen måste matcha
  `^testkund-[a-z0-9]{4,32}$`; databasfunktionen vägrar allt annat. Det är
  därför skriptet inte kan användas för att flytta en arbetsyta.
* **Skapar ingenting för en arbetsyta utan medlemmar.** Kopplingen sker i den
  INLOGGADES namn (`app.user_id`), och en arbetsyta utan profilrad har ingen
  sådan. De listas som överhoppade i stället för att gissas åt.

Kunskapsbasen seedas av backendens `POST /api/keys` när sluggen börjar på
`testkund-` — se snajp-support/app/api/keys.py. Ingen tenant lämnas alltså med
en tom bas, vilket hade fått agenten att eskalera varje ärende.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway import USER_AGENT  # noqa: E402
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

OKOPPLADE = """
select w.id, w.name,
       (select p.id from public.profiles p where p.workspace_id = w.id
         order by p.created_at limit 1) as medlem
  from public.workspaces w
 where w.slug is null
 order by w.created_at
"""


def skapa_tenant(api_url: str, master: str, slug: str, namn: str) -> tuple[str, str]:
    """Skapar (eller återanvänder) tenanten och returnerar (tenant_id, nyckel).

    `create_tenant` i backenden är en upsert på slug, så ett omtag efter ett
    avbrutet försök ger samma tenant och en ny nyckel — inte en andra tenant
    med halva arbetsytans data.
    """
    req = urllib.request.Request(
        f"{api_url}/api/keys",
        data=json.dumps({"tenant_name": namn, "slug": slug}).encode(),
        headers={
            "X-API-Key": master,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        kropp = json.load(resp)
    return kropp["tenant_id"], kropp["api_key"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    env = env_read()
    prefix = f"RAILWAY_{args.env.upper()}_"
    api_url = env.get(f"{prefix}API_URL")
    master = env.get(f"{prefix}MASTER_API_KEY")
    if not (api_url and master):
        sys.exit(f"Saknar {prefix}API_URL eller {prefix}MASTER_API_KEY i .env.deploy")

    conn = psycopg2.connect(dsn(env, args.env), connect_timeout=20)
    conn.autocommit = False
    kopplade, hoppade = 0, 0
    try:
        with conn.cursor() as cur:
            cur.execute(OKOPPLADE)
            rader = cur.fetchall()

            print(f"miljö: {args.env} · {len(rader)} arbetsytor utan slug\n")
            for ws_id, namn, medlem in rader:
                slug = f"testkund-{str(ws_id).replace('-', '')[:8]}"

                if medlem is None:
                    print(f"  –  {str(namn)[:34]:34} inga medlemmar — hoppas över")
                    hoppade += 1
                    continue

                if not args.apply:
                    print(f"  ×  {str(namn)[:34]:34} skulle få {slug}")
                    continue

                tenant_id, nyckel = skapa_tenant(api_url, master, slug, str(namn))

                # Kopplingen görs genom databasfunktionen och inte med en UPDATE.
                # Skälet står i migration 040: en UPDATE-policy på workspaces
                # hade öppnat `slug` för appen, alltså vilken kunds data
                # arbetsytan ser. Funktionen kan bara en sak, och den läser
                # arbetsytan ur anroparens profil.
                cur.execute("select set_config('app.user_id', %s, true)", (str(medlem),))
                cur.execute(
                    "select public.link_test_tenant(%s, %s, %s)", (slug, tenant_id, nyckel)
                )
                if cur.fetchone()[0]:
                    print(f"  OK {str(namn)[:34]:34} {slug}")
                    kopplade += 1
                else:
                    # Funktionen sa nej. Enda vägarna dit är att sluggen inte
                    # matchar mönstret eller att arbetsytan hann få en slug.
                    print(f"  !  {str(namn)[:34]:34} link_test_tenant nekade")
                    hoppade += 1

        if not args.apply:
            print("\nTorrkörning. Kör om med --apply.")
            conn.rollback()
            return 0

        conn.commit()
        print(f"\nKlart: {kopplade} kopplade, {hoppade} överhoppade.")
        print("Kunskapsbasen seedas av POST /api/keys för testkund-slugar.")
        return 0
    except Exception as fel:  # noqa: BLE001 — en halvkopplad arbetsyta är värre än ett fel
        conn.rollback()
        sys.exit(f"AVBRYT (inget skrivet): {fel}")
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
