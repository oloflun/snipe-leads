#!/usr/bin/env python3
"""Koppla webbens utgående mailväg (lösenordsåterställningen) i Railway.

    python scripts/web_mailvag.py                      # torrkörning, visar läget
    python scripts/web_mailvag.py --apply --env development
    python scripts/web_mailvag.py --apply --env main

Sätter på tjänsten `web`, per miljö:

  * RESEND_API_KEY   — ur .env.deploy-raden RESEND_FULL_API_KEY. Samma nyckel
    som api-tjänsten skickar med; webben skickar bara återställningsmail, så
    delad nyckel är delad AVSÄNDARDOMÄN här, inte en delad LLM-kvot
    (jämför api_key_setup.py, där delning är själva felet).
  * SMTP_FROM / SMTP_FROM_NAME — läses från API-TJÄNSTEN i samma miljö, så
    webbens avsändare alltid är identisk med den Resend-verifierade identitet
    resten av plattformen använder. Divergens här ger tysta avvisningar.
  * SITE_URL — ur RAILWAY_<MILJÖ>_WEB_URL i .env.deploy. Läses av
    lib/mail.ts (appBasUrl) för länken i mailet; aldrig ur Host-headern,
    se kommentaren där om password reset poisoning.

Innan något skrivs provas nyckeln mot Resends /domains — en nyckel som inte
kan lista domäner kan inte skicka. Nyckelvärden skrivs aldrig ut; bara längd
och kort sha256 (samma leakage-spärr som api_key_setup.py).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request

from railway import REPO_ROOT, gql

PROJECT_ID = "b4ec4f98-2d00-4410-bfae-12fb69652d0b"
WEB_SERVICE_ID = "0261f633-1247-4d92-b5ab-40c2a1828b90"
API_SERVICE_ID = "5828c279-ad8f-429b-b5e1-969372db8a0a"
ENV_DEPLOY = REPO_ROOT / ".env.deploy"

MILJOER = {
    "development": "02c39616-1b8e-47b7-beea-d8c6cfba1acd",
    "main": "47bc7047-a458-404b-a1de-ccec612cb96e",
}


def fingeravtryck(varde: str) -> str:
    return f"len={len(varde)} sha={hashlib.sha256(varde.encode()).hexdigest()[:10]}"


def las_env_deploy() -> dict[str, str]:
    if not ENV_DEPLOY.exists():
        sys.exit(f"AVBRYTER: {ENV_DEPLOY} finns inte.")
    ut: dict[str, str] = {}
    for rad in ENV_DEPLOY.read_text(encoding="utf-8").splitlines():
        if "=" in rad and not rad.lstrip().startswith("#"):
            nyckel, _, varde = rad.partition("=")
            ut[nyckel.strip()] = varde.strip()
    return ut


def variabler(env_id: str, service_id: str) -> dict[str, str]:
    return gql(
        "query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }",
        {"p": PROJECT_ID, "e": env_id, "s": service_id},
    )["variables"]


def satt(env_id: str, namn_varden: dict[str, str]) -> None:
    gql(
        "mutation($in: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $in) }",
        {
            "in": {
                "projectId": PROJECT_ID,
                "environmentId": env_id,
                "serviceId": WEB_SERVICE_ID,
                "variables": namn_varden,
                # replace:false — vi rör bara mailvariablerna, inte uppsättningen.
                "replace": False,
            }
        },
    )


def prova_resend_nyckel(nyckel: str) -> str | None:
    """Felsträng eller None. /domains kräver en giltig nyckel men skickar inget."""
    # User-Agent av samma skäl som railway.py: Cloudflare svarar 403 (1010) på
    # Python-urllibs default-UA INNAN auth prövas — det ser ut som en avvisad
    # nyckel och är det inte.
    req = urllib.request.Request(
        "https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {nyckel}", "User-Agent": "snajp-railway-client/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as svar:
            data = json.load(svar)
        domaner = [d.get("name") for d in data.get("data", [])]
        verifierade = [
            d.get("name") for d in data.get("data", []) if d.get("status") == "verified"
        ]
        if not verifierade:
            return f"nyckeln duger men INGEN domän är verifierad hos Resend (fanns: {domaner})"
        return None
    except urllib.error.HTTPError as fel:
        return f"Resend avvisade nyckeln ({fel.code})"
    except urllib.error.URLError as fel:
        return f"kunde inte nå Resend ({fel.reason})"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", choices=sorted(MILJOER) + ["alla"], default="alla")
    p.add_argument("--apply", action="store_true", help="skriv till Railway (annars torrkörning)")
    args = p.parse_args()

    env = las_env_deploy()
    nyckel = env.get("RESEND_FULL_API_KEY", "")
    if not nyckel:
        sys.exit("AVBRYTER: RESEND_FULL_API_KEY är tom i .env.deploy.")

    miljoer = sorted(MILJOER) if args.env == "alla" else [args.env]

    problem = prova_resend_nyckel(nyckel)
    print(f"Resend-nyckel: {fingeravtryck(nyckel)}")
    if problem:
        print(f"AVBRYTER — {problem}")
        return 1
    print("Resend-prov: nyckeln duger och en verifierad domän finns.\n")

    plan: dict[str, dict[str, str]] = {}
    fel: list[str] = []
    for miljo in miljoer:
        env_id = MILJOER[miljo]
        api_vars = variabler(env_id, API_SERVICE_ID)
        site_url = env.get(f"RAILWAY_{miljo.upper()}_WEB_URL", "").rstrip("/")
        smtp_from = api_vars.get("SMTP_FROM", "")
        smtp_namn = api_vars.get("SMTP_FROM_NAME", "")
        if not site_url:
            fel.append(f"{miljo}: RAILWAY_{miljo.upper()}_WEB_URL saknas i .env.deploy")
        if not smtp_from:
            fel.append(
                f"{miljo}: api-tjänsten saknar SMTP_FROM — ingen avsändaridentitet att ärva"
            )
        nuvarande = variabler(env_id, WEB_SERVICE_ID)
        plan[miljo] = {
            "RESEND_API_KEY": nyckel,
            "SMTP_FROM": smtp_from,
            "SMTP_FROM_NAME": smtp_namn,
            "SITE_URL": site_url,
        }
        print(miljo)
        print(f"  SITE_URL       : {site_url or 'SAKNAS'}")
        print(f"  SMTP_FROM      : {smtp_from or 'SAKNAS'} (från api-tjänsten)")
        print(f"  SMTP_FROM_NAME : {smtp_namn or '(tomt)'}")
        oforandrad = nuvarande.get("RESEND_API_KEY", "") == nyckel
        print(f"  RESEND_API_KEY : {fingeravtryck(nyckel)}{' (oförändrad)' if oforandrad else ''}")

    if fel:
        print("\nAVBRYTER — ingenting skrivet:")
        for rad in fel:
            print(f"  * {rad}")
        return 1

    if not args.apply:
        print("\nTorrkörning. Kör om med --apply för att skriva till Railway.")
        return 0

    print()
    for miljo in miljoer:
        satt(MILJOER[miljo], plan[miljo])
        tillbaka = variabler(MILJOER[miljo], WEB_SERVICE_ID)
        if tillbaka.get("RESEND_API_KEY", "") != nyckel:
            print(f"{miljo:12} SKREV MEN VERIFIERINGEN FALLERADE — värdet stämmer inte.")
            return 1
        print(f"{miljo:12} mailvariablerna satta och tillbakalästa.")

    print(
        "\nRailway startar om web-tjänsten när variabler ändras.\n"
        "Verifiera i drift: begär en återställningslänk på /login och följ den."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
