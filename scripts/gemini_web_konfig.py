#!/usr/bin/env python3
"""Sätt GEMINI_API_KEY på WEB-tjänsten i Railway (Fas 1.2) — ur den lokala .env-filen.

    python scripts/gemini_web_konfig.py --env development --apply

Varför: Email-studion (app/api/email-studio/route.ts) fick en Gemini-gren i
Fas 1, men nyckeln finns bara på api-tjänsten — web-tjänsten har den inte,
så studion faller till simulateAction() även för en inloggad kund. Skriptet
läser värdet ur snajp-support/.env (dit scripts/keys.py redan skriver det)
och sätter det på web-tjänsten. Värdet skrivs ALDRIG ut — bara namn + längd.

--env main är MEDVETET avstängd: §8.1a i
plans/2026-08-28-skarpa-korningar-och-produktion.md spärrar varje skrivande
Railway-anrop mot main tills Anton uttryckligen säger till. Den dagen: ta
bort spärren här i samma commit som resten av cutovern.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import envs_by_name, read_vars, services_by_name, set_vars, state  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default="development", choices=["development", "main"])
    p.add_argument("--apply", action="store_true", help="Skriv värdet. Utan flaggan: visa bara läget.")
    args = p.parse_args()

    if args.env == "main":
        print("  ⛔ SPÄRRAD (§8.1a): main rörs inte utan Antons uttryckliga ord.")
        return 1

    nyckel = ""
    for rad in Path(__file__).resolve().parent.parent.joinpath("snajp-support", ".env").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.+)\s*$", rad)
        if m:
            nyckel = m.group(1).strip().strip('"').strip("'")
    if not nyckel:
        print("  GEMINI_API_KEY saknas i snajp-support/.env — kör scripts/keys.py först.")
        return 1

    projekt = state()
    env_id = envs_by_name(projekt).get(args.env)
    web = services_by_name(projekt).get("web")
    if not env_id or not web:
        print(f"  Hittade inte miljön {args.env!r} eller tjänsten 'web'.")
        return 1

    befintlig = (read_vars(web["id"], env_id).get("GEMINI_API_KEY") or "").strip()
    print(f"  web/{args.env} GEMINI_API_KEY före: {'satt (len=%d)' % len(befintlig) if befintlig else 'OSATT'}")
    print(f"  Lokala värdet: len={len(nyckel)}, svans=...{nyckel[-4:]}")

    if not args.apply:
        print("\n  (Kör med --apply för att skriva.)")
        return 0
    if befintlig == nyckel:
        print("  Samma värde redan satt — inget skrivet.")
        return 0
    set_vars(web["id"], env_id, {"GEMINI_API_KEY": nyckel})
    print(f"  GEMINI_API_KEY satt på web/{args.env}. Railway deployar om web-tjänsten.")
    print("  Verifiera: anrop mot /api/email-studio inloggat ska ge simulated: false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
