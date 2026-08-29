#!/usr/bin/env python3
"""Slå på TLS för Redis Cloud-databasen och byt REDIS_URL till rediss:// — i ett svep.

    python scripts/redis_tls_pa.py                # visa läget, ändra ingenting
    python scripts/redis_tls_pa.py --apply        # gör båda stegen

Varför ett skript: TLS-påslaget och URL-bytet är ETT sammanhängande byte, inte
två. Slås TLS på utan att REDIS_URL byts till rediss:// tappar api-tjänsten
anslutningen och faller tillbaka till in-memory-jobb tills någon minns steg
två. Skriptet gör därför båda, i rätt ordning, och verifierar däremellan.

Bakgrund (2026-08-29): databasen Snajp-Chat-Data ligger i EU (europe-west1,
verifierat med scripts/redis_kontroll.py) men hade TLS AV — jobbposterna, som
bär riktiga kundsvar, gick i klartext över nätet. Se docs/JURIDIK_ATGARDER.md
P1.2. Auto-läge-klassificeraren stoppade agentens direkta försök att göra
det här (rätt: en skrivning mot delad moln-infrastruktur ska gå via en
människas hand), därför finns kommandot som ett skript åt Anton i stället.

Stegen vid --apply:
1. PUT enableTls=true på databasen via kontonivå-API:t (nycklarna ur
   .env.deploy, samma som scripts/redis_kontroll.py), polla klart.
2. Läs REDIS_URL ur Railway development/api, byt schema redis:// -> rediss://
   (värdet skrivs ALDRIG ut), PING-testa den nya URL:en härifrån, och skriv
   tillbaka den. Railway deployar om api-tjänsten automatiskt.
3. Skriv ut verifieringskommandot (health-endpointen ska säga "jobs":"redis").

Certifikatnot: rediss:// verifierar serverns certifikat mot systemets
CA-lager. Faller PING-testet på certifikatverifiering skriver skriptet ut
felet i klartext — då är nästa steg ett medvetet beslut (CA-bundle eller
konsolsamtal med Redis), inte en tyst ssl_cert_reqs=none.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read, envs_by_name, read_vars, services_by_name, set_vars, state  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_BAS = "https://api.redislabs.com/v1"
SUB_ID = 3396987        # Snajp-Chat-Data (fixed/Essentials), verifierad 2026-08-29
DB_ID = 14581306

def _kalla(metod: str, sökväg: str, kropp: dict | None = None) -> tuple[int, dict | str]:
    env = env_read()
    req = urllib.request.Request(
        f"{API_BAS}{sökväg}",
        data=json.dumps(kropp).encode() if kropp else None,
        method=metod,
        headers={
            "x-api-key": env.get("REDIS_CLOUD_API_KEY", ""),
            "x-api-secret-key": env.get("REDIS_CLOUD_API_SECRET", ""),
            "Accept": "application/json",
            "Content-Type": "application/json",
            # Cloudflare framför API:t blockerar Pythons standard-User-Agent.
            "User-Agent": "Mozilla/5.0 snajp-redis-tls/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as fel:
        return fel.code, fel.read().decode(errors="replace")[:600]
    except Exception as fel:  # noqa: BLE001
        return -1, f"{type(fel).__name__}: {str(fel)[:300]}"


def _tls_läge() -> bool | None:
    st, data = _kalla("GET", f"/fixed/subscriptions/{SUB_ID}/databases/{DB_ID}")
    if st != 200 or not isinstance(data, dict):
        print(f"  Kunde inte läsa databasen: HTTP {st}: {data}")
        return None
    return bool((data.get("security") or {}).get("enableTls"))


def _vänta_på_task(task_id: str) -> bool:
    for _ in range(36):
        time.sleep(5)
        st, t = _kalla("GET", f"/tasks/{task_id}")
        status = t.get("status") if isinstance(t, dict) else "?"
        print(f"  task: {status}")
        if status == "processing-completed":
            return True
        if status == "processing-error":
            print(f"  Felkropp: {json.dumps(t)[:600]}")
            return False
    print("  Gav upp efter 3 minuter — kontrollera tasken i Redis Cloud-konsolen.")
    return False


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="Slå på TLS och byt REDIS_URL. Utan flaggan: visa bara läget.")
    args = p.parse_args()

    tls = _tls_läge()
    if tls is None:
        return 1
    print(f"  TLS på databasen just nu: {'PÅ' if tls else 'AV'}")

    projekt = state()
    env_id = envs_by_name(projekt).get("development")
    api = services_by_name(projekt).get("api")
    if not env_id or not api:
        print("  Hittade inte development/api i Railway.")
        return 1
    variabler = read_vars(api["id"], env_id)
    url = variabler.get("REDIS_URL", "")
    schema = url.split("://", 1)[0] if "://" in url else "(saknas)"
    print(f"  REDIS_URL i development/api: schema={schema}, längd={len(url)}")

    if not args.apply:
        print("\n  (Kör med --apply för att slå på TLS och byta till rediss://.)")
        return 0

    if not tls:
        print("\n  Slår på TLS via kontonivå-API:t …")
        st, resp = _kalla("PUT", f"/fixed/subscriptions/{SUB_ID}/databases/{DB_ID}", {"enableTls": True})
        if st not in (200, 202) or not isinstance(resp, dict):
            print(f"  MISSLYCKADES: HTTP {st}: {resp}")
            return 1
        task = resp.get("taskId")
        if task and not _vänta_på_task(task):
            return 1
        print("  TLS är PÅ.")

    if not url.startswith("redis"):
        print("  REDIS_URL saknas i Railway — kör scripts/redis_konfig.py i stället.")
        return 1
    ny_url = re.sub(r"^redis://", "rediss://", url)
    if ny_url == url and url.startswith("rediss://"):
        print("  REDIS_URL är redan rediss:// — inget att byta.")
    else:
        print("  PING-testar rediss://-varianten …")
        try:
            import redis

            klient = redis.from_url(ny_url, socket_connect_timeout=10, socket_timeout=10)
            if not klient.ping():
                print("  PING svarade utan PONG — avbryter utan att skriva.")
                return 1
        except ImportError:
            print("  Paketet 'redis' saknas här — hoppar över PING, verifiera med /health efteråt.")
        except Exception as fel:  # noqa: BLE001
            print(f"  PING MISSLYCKADES: {type(fel).__name__}: {str(fel)[:300]}")
            print("  Ingenting skrivet till Railway. Är felet certifikatverifiering: se docstringen.")
            return 1
        set_vars(api["id"], env_id, {"REDIS_URL": ny_url})
        print("  REDIS_URL uppdaterad till rediss:// i development/api. Railway deployar om.")

    print("\n  Verifiera när deployen är uppe:")
    print("    curl -s https://api-development-5cc3.up.railway.app/health | grep -o '\"jobs\":\"[a-z]*\"'")
    print('  Ska säga "jobs":"redis".')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
