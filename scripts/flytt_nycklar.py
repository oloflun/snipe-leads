#!/usr/bin/env python3
"""Nycklarna för Flytta till main och nattspegeln (plan del E), i ett kommando.

    python scripts/flytt_nycklar.py --check     # vad finns, inga värden visas
    python scripts/flytt_nycklar.py --apply     # sätt allt som saknas och verifiera

Ingen av nycklarna kommer från en leverantör, så det finns ingen dashboard att
hämta dem ur:

  FLYTT_NYCKEL   Delad HMAC-hemlighet mellan development (avsändare) och main
                 (mottagare). Skapas här med `secrets`, sparas i .env.deploy så
                 att en omkörning återanvänder samma värde, och sätts på api i
                 BÅDA miljöerna. Samma värde måste finnas på båda sidor.
  FLYTT_MAL_URL  Mains api-adress, sätts bara på api i development. Läses ur
                 RAILWAY_MAIN_API_URL i .env.deploy.
  ENV_DEPLOY     GitHub-repohemligheten som .github/workflows/spegla-dev.yml
                 skriver till .env.deploy på runnern. Bara de sex rader
                 speglingen läser (RAILWAY_{MAIN,DEVELOPMENT}_PG_{PASSWORD,HOST,PORT}),
                 aldrig hela filen: Render-, Loopia- och Redis-nycklarna har
                 inget på GitHub att göra.

Värdena skrivs aldrig ut och läggs aldrig i ett kommandoargument: Railway får
dem via GraphQL (railway_provision.set_vars), GitHub via stdin till `gh secret set`.

OBS: när ENV_DEPLOY finns kör nattspegeln 02:00 UTC varje natt och skriver
över development med main. Det är Antons beställning 2026-10-01; flytta det
som ska sparas med Byt kund → Flytta till main innan dess.
"""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_provision import (deploy, env_read, env_set, envs_by_name,  # noqa: E402
                               services_by_name, set_vars, state)

REPO = "oloflun/snipe-leads"
SPEGELNYCKLAR = [f"RAILWAY_{m}_PG_{f}" for m in ("MAIN", "DEVELOPMENT") for f in ("PASSWORD", "HOST", "PORT")]


def _gh_hemligheter() -> set[str]:
    r = subprocess.run(["gh", "secret", "list", "--repo", REPO, "--json", "name"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gh secret list misslyckades: {r.stderr.strip()}  (kör `gh auth login`)")
    return {s["name"] for s in json.loads(r.stdout or "[]")}


def _flytt_status(env: dict[str, str], miljo: str) -> dict | None:
    """Appens egen kontroll (GET /api/admin/flytt/status): bevisar att api:t
    LÄSER variablerna, inte bara att Railway tog emot dem."""
    url = env.get(f"RAILWAY_{miljo.upper()}_API_URL")
    nyckel = env.get(f"RAILWAY_{miljo.upper()}_MASTER_API_KEY")
    if not (url and nyckel):
        return None
    req = urllib.request.Request(f"{url.rstrip('/')}/api/admin/flytt/status", headers={"X-API-Key": nyckel})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except Exception as fel:  # noqa: BLE001
        return {"fel": type(fel).__name__ + (f" {fel.code}" if hasattr(fel, "code") else "")}


def check() -> None:
    env = env_read()
    print("Lokalt (.env.deploy):")
    print(f"  FLYTT_NYCKEL           {'finns' if env.get('FLYTT_NYCKEL') else 'saknas (skapas av --apply)'}")
    print(f"  RAILWAY_MAIN_API_URL   {env.get('RAILWAY_MAIN_API_URL') or 'SAKNAS'}")
    saknas = [k for k in SPEGELNYCKLAR if not env.get(k)]
    print(f"  spegelns sex PG-rader  {'alla finns' if not saknas else 'SAKNAS: ' + ', '.join(saknas)}")
    print("GitHub:")
    print(f"  ENV_DEPLOY             {'finns' if 'ENV_DEPLOY' in _gh_hemligheter() else 'saknas'}")
    print("Railway, appens egen status (/api/admin/flytt/status):")
    for miljo in ("development", "main"):
        s = _flytt_status(env, miljo)
        if s is None:
            print(f"  {miljo}: ingen API-URL eller masternyckel i .env.deploy")
        elif "fel" in s:
            hint = " (koden är inte släppt till main än)" if miljo == "main" and "404" in s["fel"] else ""
            print(f"  {miljo}: {s['fel']}{hint}")
        else:
            print(f"  {miljo}: nyckel={s.get('nyckel_konfigurerad')} mål={s.get('mal_konfigurerat')} spegel={bool(s.get('spegel'))}")


def apply() -> None:
    env = env_read()
    saknas = [k for k in SPEGELNYCKLAR + ["RAILWAY_MAIN_API_URL"] if not env.get(k)]
    if saknas:
        sys.exit(f"AVBRYTER: .env.deploy saknar {', '.join(saknas)}.")

    if not env.get("FLYTT_NYCKEL"):
        env_set("FLYTT_NYCKEL", secrets.token_urlsafe(48))
        env = env_read()
    nyckel = env["FLYTT_NYCKEL"]

    projekt = state()
    miljoer, tjanster = envs_by_name(projekt), services_by_name(projekt)
    api = tjanster["api"]["id"]
    for miljo, varden in (
        ("main", {"FLYTT_NYCKEL": nyckel}),
        ("development", {"FLYTT_NYCKEL": nyckel, "FLYTT_MAL_URL": env["RAILWAY_MAIN_API_URL"].rstrip("/")}),
    ):
        set_vars(api, miljoer[miljo], varden)
        print(f"  {miljo}: satt {', '.join(sorted(varden))}, deploy {deploy(api, miljoer[miljo])}")

    kropp = "\n".join(f"{k}={env[k]}" for k in SPEGELNYCKLAR) + "\n"
    r = subprocess.run(["gh", "secret", "set", "ENV_DEPLOY", "--repo", REPO], input=kropp, text=True,
                       capture_output=True)
    if r.returncode != 0:
        sys.exit(f"gh secret set misslyckades: {r.stderr.strip()}")
    print(f"  GitHub: ENV_DEPLOY satt ({len(SPEGELNYCKLAR)} rader, {len(kropp)} tecken)")

    print("\nVerifierar development mot appens egen status (deployen tar 1-3 minuter):")
    for _ in range(24):
        s = _flytt_status(env, "development")
        if s and s.get("nyckel_konfigurerad") and s.get("mal_konfigurerat"):
            print(f"  development: nyckel=True mål=True spegel={bool(s.get('spegel'))}. Klart.")
            break
        time.sleep(10)
    else:
        sys.exit(f"  development svarade inte med båda flaggorna: {s}")
    print("  main: verifieras när koden släppts dit (PR development → main); --check visar läget.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    apply() if a.apply else check()


if __name__ == "__main__":
    main()
