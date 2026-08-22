#!/usr/bin/env python3
"""Railway-klient: GraphQL v2, token ur .env.deploy.

Samma mönster som scripts/verify_render.py — ett kommando som går att köra om
och falsifiera, i stället för en punktlista i ett dokument.

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

ENDPOINT = "https://backboard.railway.com/graphql/v2"

#: Railway sitter bakom Cloudflare, som svarar 403 (error 1010) på Python-urllibs
#: default-UA. Det är INTE auth som faller — svaret är identiskt oavsett om
#: tokenen duger, och ett skript som tolkar det som "tokenen avvisades" pekar
#: felsökningen åt fel håll. Konstanten är delad med set_railway_token.py, som
#: hade en egen kopia av anropet UTAN headern och därför avvisade giltiga tokens.
#: Uppmätt: utan headern 403/1010, med headern 200 med ett riktigt auth-svar.
USER_AGENT = "snajp-railway-client/1.0"
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_token() -> str:
    tok = os.environ.get("RAILWAY_TOKEN")
    if tok:
        return tok
    env = REPO_ROOT / ".env.deploy"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("RAILWAY_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("RAILWAY_TOKEN saknas — sätt den i .env.deploy eller miljön.")


def gql(query: str, variables: dict | None = None) -> dict:
    """Kör en GraphQL-fråga. Kastar SystemExit med felmeddelandet vid fel."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {load_token()}",
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
    if payload.get("errors"):
        msgs = "; ".join(e.get("message", "?") for e in payload["errors"])
        raise RuntimeError(msgs)
    return payload["data"]


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
