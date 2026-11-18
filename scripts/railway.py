#!/usr/bin/env python3
"""Railway-klient: GraphQL v2, token ur .env.deploy.

Ett kommando som går att köra om och falsifiera, i stället för en punktlista i
ett dokument (samma mönster som scripts/verify_railway.py).

Leakage-spärr: token läses ur .env.deploy (gitignorerad) och skrivs aldrig ut.

Användning:
    python scripts/railway.py projects
    python scripts/railway.py show <projectId>
    python scripts/railway.py q '<graphql>' '<json-vars>'
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows-konsolen kör cp1252. Svaren härifrån är RAILWAYS text, inte vår:
# byggloggar, commit-meddelanden, felkroppar. Next.js skriver "▲" i sin
# byggrubrik och "✓" per steg, och ingetdera finns i cp1252 — en `buildLogs`
# dog därför med UnicodeEncodeError efter att ha hämtat loggen, alltså precis
# när den skulle visa svaret. Felet ser ut som ett trasigt skript och skickar
# felsökningen till dashboarden, vilket är vad skriptet finns för att slippa.
# Samma rad som i set_railway_token.py, av samma skäl.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENDPOINT = "https://backboard.railway.com/graphql/v2"

#: Railway sitter bakom Cloudflare, som svarar 403 (error 1010) på Python-urllibs
#: default-UA. Det är INTE auth som faller — svaret är identiskt oavsett om
#: tokenen duger, och ett skript som tolkar det som "tokenen avvisades" pekar
#: felsökningen åt fel håll. Konstanten är delad med set_railway_token.py, som
#: hade en egen kopia av anropet UTAN headern och därför avvisade giltiga tokens.
#: Uppmätt: utan headern 403/1010, med headern 200 med ett riktigt auth-svar.
USER_AGENT = "snajp-railway-client/1.0"
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_token() -> str | None:
    tok = os.environ.get("RAILWAY_TOKEN")
    if tok:
        return tok
    env = REPO_ROOT / ".env.deploy"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("RAILWAY_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


#: Railways egen CLI. Är den inloggad bär den en giltig session även när
#: RAILWAY_TOKEN i .env.deploy har gått ut (2026-11-19: tokenen svarade "Not
#: Authorized" medan `railway whoami` var inloggad).
CLI = "railway"


def _gql_cli(query: str, variables: dict) -> dict:
    """Samma fråga genom `railway api`. Variablerna går via stdin, så att ett
    lösenord i en variabel aldrig syns i processlistan eller i en fil.
    Sessionen ligger hos CLI:t; skriptet läser den inte."""
    import shutil
    import subprocess

    # Hela sökvägen: på Windows hittar subprocess inte railway.cmd på namnet.
    cli = shutil.which(CLI)
    if not cli:
        sys.exit("RAILWAY_TOKEN saknas eller avvisades, och Railways CLI finns inte. "
                 "Sätt en ny token i .env.deploy (scripts/set_railway_token.py) eller kör `railway login`.")
    import tempfile

    # Frågan som fil: en flerradig fråga som argument bryts av cmd-skalet runt
    # railway.cmd på Windows. Filen bär bara frågan, aldrig ett värde.
    with tempfile.NamedTemporaryFile("w", suffix=".graphql", delete=False, encoding="utf-8") as fil:
        fil.write(query)
    try:
        resultat = subprocess.run(
            [cli, "api", "--file", fil.name, "--variables", "@-", "--compact", "--allow-errors"],
            input=json.dumps(variables), capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
    finally:
        os.unlink(fil.name)
    if resultat.returncode != 0:
        sys.exit(f"railway api föll ({resultat.returncode}): {(resultat.stderr or resultat.stdout).strip()[:800]}")
    return json.loads(resultat.stdout)


def gql(query: str, variables: dict | None = None) -> dict:
    """Kör en GraphQL-fråga. Kastar SystemExit med felmeddelandet vid fel.

    Med RAILWAY_TOKEN går frågan direkt mot API:t. Saknas tokenen, eller
    avvisas den, går samma fråga genom den inloggade CLI:n (`_gql_cli`)."""
    variables = variables or {}
    token = load_token()
    payload: dict
    if token:
        body = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                # Se USER_AGENT ovan — utan den svarar Cloudflare 403 före auth.
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:  # ponytail: felkroppen är det enda intressanta
            sys.exit(f"HTTP {exc.code}: {exc.read().decode()[:800]}")
        if _avvisad(payload):
            print("RAILWAY_TOKEN avvisades; frågan går genom Railways CLI.", file=sys.stderr)
            payload = _gql_cli(query, variables)
    else:
        payload = _gql_cli(query, variables)
    if payload.get("errors"):
        msgs = "; ".join(e.get("message", "?") for e in payload["errors"])
        raise RuntimeError(msgs)
    return payload["data"]


def _avvisad(payload: dict) -> bool:
    """Tokenen avvisades (utgången eller fel scope), till skillnad från ett
    fel i själva frågan."""
    return any("not authorized" in (e.get("message") or "").lower() for e in payload.get("errors") or [])


PROJECTS = """
query { projects { edges { node { id name } } } }
"""

SHOW = """
query($id: String!) {
  project(id: $id) {
    id name
    environments { edges { node { id name } } }
    services { edges { node { id name
      serviceInstances { edges { node {
        environmentId rootDirectory
        source { image repo }
        builder
        healthcheckPath
        startCommand
        region
      } } }
    } } }
  }
}
"""


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "projects":
        print(json.dumps(gql(PROJECTS), indent=2, ensure_ascii=False))
    elif cmd == "show":
        print(json.dumps(gql(SHOW, {"id": sys.argv[2]}), indent=2, ensure_ascii=False))
    elif cmd == "q":
        variables = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(gql(sys.argv[2], variables), indent=2, ensure_ascii=False))
    else:
        sys.exit(f"okänt kommando: {cmd}")


if __name__ == "__main__":
    main()
