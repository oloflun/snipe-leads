#!/usr/bin/env python
"""Satt RAILWAY_TOKEN i .env.deploy - token via getpass.

Samma monster som set_railway_postgres_url.py: vardet lases fran terminalens
stdin, syns aldrig pa skarmen, hamnar aldrig i shell-historiken, och passerar
aldrig en chattkanal.

    python scripts/set_railway_token.py

## Varfor den behovs

`scripts/railway.py` kan fraga Railways GraphQL-API om vad som helst -
deployloggar, tjanstkonfiguration, deployment-triggers, byggstatus. Utan token
gar ingen av de fragorna att stalla, och en deploy som fallerar i Railways egen
initialisering blir omojlig att diagnosticera utifran: symptomen syns bara i
deras dashboard, och gissningar kostar mer tid an de sparar.

## Var token finns

Railway -> Account Settings -> Tokens -> Create Token.

Valj en **Account**-token, inte en projekt-token: en projekt-token nar bara ett
projekt och kan inte lista deployments over miljoer, vilket ar precis vad som
behovs for att jamfora en fungerande deploy med en trasig.

Tokenen ger full atkomst till kontot. Den bor roteras nar felsokningen ar klar.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

import urllib.request
import json

# Windows-konsolen kor cp1252. Se set_railway_postgres_url.py for varfor det
# har inte ar overdrivet: en print med fel tecken dodar skriptet innan det
# hinner fraga om nagot, och felet ser ut som om kommandot aldrig kordes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"
KEY = "RAILWAY_TOKEN"
API = "https://backboard.railway.com/graphql/v2"


def verifiera(token: str) -> str | None:
    """Returnerar kontonamnet, eller None. Bevisar att tokenen DUGER."""
    fraga = json.dumps({"query": "{ me { name email } }"}).encode()
    req = urllib.request.Request(
        API,
        data=fraga,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            svar = json.loads(resp.read())
        me = (svar.get("data") or {}).get("me") or {}
        return me.get("email") or me.get("name")
    except Exception:
        return None


def main() -> None:
    if not DEPLOY_ENV.exists():
        DEPLOY_ENV.write_text("# Drift- och speglingsvariabler. GITIGNORERAD.\n", encoding="utf-8")
        print(f"Skapade {DEPLOY_ENV.name}.")

    print("Railway -> Account Settings -> Tokens -> Create Token")
    print("Valj en ACCOUNT-token, inte en projekt-token.\n")

    try:
        token = getpass.getpass("  RAILWAY_TOKEN (syns inte): ").strip()
    except EOFError:
        sys.exit(
            "\nIngen terminal att lasa fran. Skriptet MASTE koras i ett eget "
            "terminalfonster."
        )

    if not token:
        sys.exit("Ingen token gavs.")

    konto = verifiera(token)
    if not konto:
        sys.exit(
            "\nTokenen avvisades av Railways API. Kontrollera att den kopierats "
            "helt\noch att det ar en Account-token."
        )

    rader = DEPLOY_ENV.read_text(encoding="utf-8").splitlines()
    rader = [r for r in rader if not r.startswith(f"{KEY}=")]
    rader.append(f"{KEY}={token}")
    DEPLOY_ENV.write_text("\n".join(rader) + "\n", encoding="utf-8")

    print(f"\nOK: token verifierad for {konto}.")
    print(f"{KEY} skriven till {DEPLOY_ENV.name}. Den lamnade aldrig terminalen.")
    print("\nRotera tokenen nar felsokningen ar klar.")


if __name__ == "__main__":
    main()
