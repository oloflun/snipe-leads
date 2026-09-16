"""Fånga OAuth-samtycket för Kvittohanterarens mejlkoppling.

Vi kopplar åt kunden (samma mönster som Inkorgar/IMAP): det här skriptet
skrivs ut en konsent-URL, kunden (eller vi, i kundens närvaro) godkänner
read-only-åtkomst, och refresh-token landar i terminalen — FÖR ATT LÄGGAS I
MILJÖN (KVITTO_OAUTH_REFRESH_TOKEN på Railway), aldrig i git och aldrig i
databasen.

    python scripts/kvitto_oauth.py gmail
    python scripts/kvitto_oauth.py microsoft

Klientuppgifter läses ur .env.deploy (KVITTO_OAUTH_CLIENT_ID/SECRET) och
skrivs ALDRIG ut — läckagespärren i CLAUDE.md gäller här.

Scopes är read-only med flit: gmail.readonly respektive Mail.Read. Begär
aldrig mer — agenten läser kvitton, den rör ingenting.
"""

from __future__ import annotations

import http.server
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
PORT = 8765
REDIRECT = f"http://localhost:{PORT}/callback"

LEVERANTORER = {
    "gmail": {
        "auth": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/gmail.readonly",
        "extra": {"access_type": "offline", "prompt": "consent"},
    },
    "microsoft": {
        "auth": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scope": "https://graph.microsoft.com/Mail.Read offline_access",
        "extra": {},
    },
}


def las_env_deploy() -> dict[str, str]:
    varden: dict[str, str] = {}
    fil = REPO / ".env.deploy"
    if not fil.exists():
        sys.exit(".env.deploy saknas — lägg KVITTO_OAUTH_CLIENT_ID/SECRET där först.")
    for rad in fil.read_text(encoding="utf-8").splitlines():
        rad = rad.strip()
        if rad and not rad.startswith("#") and "=" in rad:
            nyckel, _, varde = rad.partition("=")
            varden[nyckel.strip()] = varde.strip().strip('"')
    return varden


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in LEVERANTORER:
        sys.exit("Användning: python scripts/kvitto_oauth.py gmail|microsoft")
    leverantor = sys.argv[1]
    spec = LEVERANTORER[leverantor]
    env = las_env_deploy()
    client_id = env.get("KVITTO_OAUTH_CLIENT_ID", "")
    client_secret = env.get("KVITTO_OAUTH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        sys.exit("KVITTO_OAUTH_CLIENT_ID/SECRET saknas i .env.deploy.")

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": spec["scope"],
        **spec["extra"],
    }
    url = f"{spec['auth']}?{urllib.parse.urlencode(params)}"

    kod: dict[str, str] = {}
    klart = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 — http.server:s namn
            fraga = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            kod["code"] = (fraga.get("code") or [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Klart — gå tillbaka till terminalen.</p>".encode())
            klart.set()

        def log_message(self, *args: object) -> None:  # tystnad
            pass

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print("Öppnar konsent-sidan i webbläsaren (read-only-åtkomst begärs).")
    print(f"Om inget öppnas: klistra in URL:en själv:\n\n{url}\n")
    webbrowser.open(url)
    klart.wait(timeout=300)
    server.shutdown()
    if not kod.get("code"):
        sys.exit("Inget samtycke fångades inom 5 minuter.")

    svar = httpx.post(
        spec["token"],
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": kod["code"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT,
            **({"scope": spec["scope"]} if leverantor == "microsoft" else {}),
        },
        timeout=30,
    )
    refresh = svar.json().get("refresh_token")
    if not refresh:
        sys.exit(f"Token-svaret saknade refresh_token (status {svar.status_code}).")

    print("\nKlart. Sätt i miljön (Railway → backend):")
    print(f"  KVITTO_MEJL_LEVERANTOR={leverantor}")
    print(f"  KVITTO_OAUTH_REFRESH_TOKEN={refresh}")
    print("  (KVITTO_OAUTH_CLIENT_ID/SECRET från .env.deploy, KVITTO_MEJL_ADRESS=kundens adress)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
