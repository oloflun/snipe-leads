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

import urllib.error
import urllib.request
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway import USER_AGENT  # noqa: E402

# Windows-konsolen kor cp1252. Se set_railway_postgres_url.py for varfor det
# har inte ar overdrivet: en print med fel tecken dodar skriptet innan det
# hinner fraga om nagot, och felet ser ut som om kommandot aldrig kordes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ENV = ROOT / ".env.deploy"
KEY = "RAILWAY_TOKEN"
API = "https://backboard.railway.com/graphql/v2"


def verifiera(token: str) -> tuple[str | None, str]:
    """Returnerar (kontonamn, forklaring). Kontonamn = None betyder inte OK.

    ## Varfor svaret ar tvadelat

    Funktionen returnerade forut bara None vid fel, och anroparen skrev
    "Tokenen avvisades av Railways API". Det var fel i det vanligaste fallet:
    UTAN en egen User-Agent svarar Cloudflare 403 (error 1010) INNAN Railway
    ser tokenen, och en fullt giltig account-token avvisades darfor med ett
    meddelande som skickade felsokningen till Railways dashboard.

    Uppmatt 2026-08-20 mot backboard.railway.com med en dummy-token:
      * utan User-Agent -> HTTP 403, kroppen "error code: 1010"
      * med User-Agent  -> HTTP 200, GraphQL-felet "Not Authorized"

    Det andra ar ett riktigt auth-svar. Det forsta ar ett natverkssvar, och de
    tva kraver helt olika atgarder - alltsa far de inte dela felmeddelande.
    """
    fraga = json.dumps({"query": "{ me { name email } }"}).encode()
    req = urllib.request.Request(
        API,
        data=fraga,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # Delad med scripts/railway.py. Se USER_AGENT dar.
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            svar = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        kropp = exc.read().decode("utf-8", "replace").strip()[:200]
        if exc.code == 403 and "1010" in kropp:
            return None, (
                "Cloudflare avvisade ANROPET (403, error 1010) - tokenen "
                "granskades aldrig. Det har ar en bugg i skriptet, inte i din "
                "token. Kontrollera att USER_AGENT skickas med."
            )
        return None, f"Railway svarade HTTP {exc.code}: {kropp}"
    except Exception as exc:  # natverk, DNS, TLS
        return None, f"Kunde inte na Railways API ({type(exc).__name__}: {exc})."

    if svar.get("errors"):
        meddelanden = "; ".join(e.get("message", "?") for e in svar["errors"])
        return None, (
            f"Railway granskade tokenen och sa nej: {meddelanden}. "
            "Vanligaste orsaken ar en PROJEKT-token - det maste vara en "
            "Account-token (Account Settings -> Tokens)."
        )

    me = (svar.get("data") or {}).get("me") or {}
    konto = me.get("email") or me.get("name")
    if not konto:
        return None, "Railway svarade utan konto. Tokenen nar inget konto."
    return konto, "ok"


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
