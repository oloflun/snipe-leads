#!/usr/bin/env python3
"""Utfärda en tenants API-nyckel och sätt den på Railway-webbens miljö.

    python scripts/railway_tenantnyckel.py --slug snajp --name "Snajp" --env development --apply

Gör tre saker som annars är tre manuella steg i två olika verktyg:

  1. POST /api/keys mot miljöns backend (masternyckeln ur .env.deploy) —
     utfärdar en `snajp_live_`-nyckel kopplad till tenanten. Upsert: tenanten
     skapas om den saknas, och GAMLA nycklar fortsätter gälla (ss_api_keys är
     additiv), så en omkörning roterar ingenting.
  2. Sparar nyckeln som RAILWAY_<ENV>_KEY_<SLUG> i .env.deploy och sätter den
     som SNAJP_KEY_<SLUG> på web-tjänsten i samma Railway-miljö, följt av en
     redeploy så att variabeln faktiskt når processen.
  3. Verifierar med den nya nyckeln mot /api/kb — beviset är ett svar från
     backenden, inte att mutationen gick igenom.

`onboard_tenant.py` gör motsvarande mot VERCEL-scopes; det här är
Railway-stackens variant av samma steg. Se HANDOFF-2026-08-25: main saknar
just de här web-variablerna, så skriptet är skrivet för att kunna köras mot
båda miljöerna.

Läckagespärr som i railway_env_bootstrap.py: nyckelvärdet passerar aldrig
terminalen — bara namn och längd skrivs ut, även i fel-lägen.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway import gql  # noqa: E402
from railway_provision import (  # noqa: E402
    PROJECT_ID,
    deploy,
    env_read,
    env_set,
    envs_by_name,
    services_by_name,
    set_vars,
    state,
)


def utfarda(api_url: str, master: str, slug: str, name: str) -> str:
    req = urllib.request.Request(
        f"{api_url}/api/keys",
        data=json.dumps({"tenant_name": name, "slug": slug}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": master},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as svar:
            kropp = json.load(svar)
    except urllib.error.HTTPError as fel:
        # Läs kroppen för status/detalj men skriv aldrig ut den rå — den kan
        # i värsta fall eka tillbaka delar av förfrågan.
        sys.exit(f"AVBRYTER: /api/keys svarade {fel.code}.")
    nyckel = kropp.get("api_key")
    if not nyckel:
        sys.exit(f"AVBRYTER: /api/keys gav inget nyckelfält. Svarsnycklar: {sorted(kropp)}")
    print(f"  nyckel utfärdad för tenant {kropp.get('tenant_slug')} ({len(nyckel)} tecken)")
    return nyckel


def verifiera(api_url: str, nyckel: str) -> None:
    req = urllib.request.Request(f"{api_url}/api/kb", headers={"X-API-Key": nyckel})
    with urllib.request.urlopen(req, timeout=30) as svar:
        antal = len(json.load(svar).get("articles", []))
    print(f"  verifierad: /api/kb svarar med {antal} artiklar för nyckelns tenant")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--env", choices=["development", "main"], default="development")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    api_url = store.get(f"{prefix}_API_URL")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not api_url or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL / {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    env_var = f"SNAJP_KEY_{args.slug.upper().replace('-', '_')}"
    if not args.apply:
        print(f"TORRKÖRNING: skulle utfärda nyckel för {args.slug} mot {api_url},")
        print(f"spara som {prefix}_KEY_{args.slug.upper()} och sätta {env_var} på web ({args.env}).")
        return 0

    print(f"Miljö: {args.env}  Backend: {api_url}")
    nyckel = utfarda(api_url, master, args.slug, args.name)
    env_set(f"{prefix}_KEY_{args.slug.upper().replace('-', '_')}", nyckel)

    project = state()
    env_id = envs_by_name(project).get(args.env)
    if not env_id:
        sys.exit(f"AVBRYTER: miljön {args.env} finns inte i Railway-projektet {PROJECT_ID}.")
    web = services_by_name(project).get("web")
    if not web:
        sys.exit("AVBRYTER: tjänsten web finns inte i projektet.")

    set_vars(web["id"], env_id, {env_var: nyckel})
    # Variabeln når inte den körande processen utan en ny deploy.
    deploy(web["id"], env_id)
    print(f"  web ({args.env}) redeployar med {env_var}")

    verifiera(api_url, nyckel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
