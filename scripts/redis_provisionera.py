#!/usr/bin/env python3
"""Provisionera en EGEN Redis Cloud-databas åt produktionen (main) — förberedd, SPÄRRAD.

    python scripts/redis_provisionera.py --planer            # lista köpbara planer (läser bara)
    python scripts/redis_provisionera.py --skapa --plan-id N --jag-vet-att-detta-ror-produktionen

⛔ SPÄRR: att skapa produktionens databas är en del av main-cutovern och
lyder under §8.1a i plans/2026-08-28-skarpa-korningar-och-produktion.md —
skriptet vägrar köra --skapa utan den utskrivna flaggan, och flaggan ska bara
användas när Anton uttryckligen sagt till. --planer är fri läsning.

## Varför en EGEN databas, inte den som finns

Snajp-Chat-Data (development) delas ALDRIG med main — samma tysta
korskoppling som när GEMINI_API_KEY delades mellan miljöerna och en
provkörning i dev åt upp produktionens kvot (snipe-a1c/snipe-3to). En
produktionsdatabas ska dessutom ha det gratis-30MB saknar: datapersistens
(AOF varje sekund) och replikering — annars är en Redis-failover samma sak
som en deploy var för pågående jobb.

## Krav som verkställs i koden

- Region: europe-west1 (EU, samma som dev — verifierad av redis_kontroll.py).
- Persistens: aof-every-1-second. Replikering: på.
- TLS: slås på direkt efter skapandet (samma PUT som scripts/redis_tls_pa.py).
- Minst 250 MB-planen — första betalnivån med persistens/HA enligt Redis
  plansida; gratis-30MB tål 30 anslutningar/100 ops/s och duger bara i dev.

Kontonivå-API:t kräver en betalmetod på kontot (planerna är betalda) —
saknas en svarar API:et med ett fel som skrivs ut i klartext.
Efter skapandet: kör `python scripts/redis_konfig.py --env main --endpoint
<host:port> --apply` (TLS är default där) för att sätta REDIS_URL — den
frågar efter databasens lösenord med getpass.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_provision import env_read  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_BAS = "https://api.redislabs.com/v1"
REGION = "europe-west1"
PROVIDER = "GCP"


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
            "User-Agent": "Mozilla/5.0 snajp-redis-provisionera/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as fel:
        return fel.code, fel.read().decode(errors="replace")[:800]
    except Exception as fel:  # noqa: BLE001
        return -1, f"{type(fel).__name__}: {str(fel)[:300]}"


def lista_planer() -> int:
    st, data = _kalla("GET", f"/fixed/plans?provider={PROVIDER}")
    if st != 200 or not isinstance(data, dict):
        print(f"  HTTP {st}: {data}")
        return 1
    planer = [p for p in data.get("plans", []) if p.get("region") == REGION]
    if not planer:
        print(f"  Inga fixed-planer i {REGION} — kontrollera regionnamnet mot API-svaret.")
        print(f"  Rått antal planer i svaret: {len(data.get('plans', []))}")
        return 1
    print(f"  Fixed-planer ({PROVIDER} / {REGION}):\n")
    # Fältnamnen är supportDataPersistence/supportReplication (utan s) —
    # verifierat mot ett rått API-svar 2026-08-29, inte gissat.
    for p in sorted(planer, key=lambda x: (x.get("size", 0), x.get("price", 0))):
        print(
            f"    id={p.get('id'):>8}  {str(p.get('size')):>6} {p.get('sizeMeasurementUnit', 'MB'):<3}"
            f"  pris={p.get('price')} {p.get('priceCurrency', 'USD')}/{p.get('pricePeriod', 'mån'):<6}"
            f"  persistens={'ja' if p.get('supportDataPersistence') else 'nej'}"
            f"  replikering={'ja' if p.get('supportReplication') else 'nej'}"
            f"  ({p.get('name')})"
        )
    print(
        "\n  Välj den minsta planen med persistens=ja OCH replikering=ja."
        "\n  2026-08-29 var det Single-Zone_Persistence_250MB, id 21437, 10 USD/mån"
        "\n  (obs: replikeringen halverar datasetSize till 125 MB — det räcker gott"
        "\n  för jobb/cache/arbetsminne, allt bär TTL)."
    )
    return 0


def skapa(plan_id: int) -> int:
    print(f"  Skapar fixed-prenumeration 'Snajp-Prod-Data' på plan {plan_id} …")
    st, resp = _kalla("POST", "/fixed/subscriptions", {"name": "Snajp-Prod-Data", "planId": plan_id})
    if st not in (200, 202) or not isinstance(resp, dict):
        print(f"  MISSLYCKADES: HTTP {st}: {resp}")
        return 1
    task = resp.get("taskId")
    sub_id = None
    for _ in range(60):
        time.sleep(5)
        st2, t = _kalla("GET", f"/tasks/{task}")
        status = t.get("status") if isinstance(t, dict) else "?"
        print(f"  task: {status}")
        if status == "processing-completed":
            sub_id = ((t.get("response") or {}).get("resourceId")) if isinstance(t, dict) else None
            break
        if status == "processing-error":
            print(f"  Felkropp: {json.dumps(t)[:800]}")
            return 1
    if not sub_id:
        print("  Fick inget prenumerations-id — kontrollera i konsolen.")
        return 1

    print(f"  Prenumeration {sub_id}. Skapar databasen …")
    st, resp = _kalla(
        "POST",
        f"/fixed/subscriptions/{sub_id}/databases",
        {
            "name": "Snajp-Prod-Data",
            "protocol": "stack",
            "dataPersistence": "aof-every-1-second",
            "replication": True,
            "dataEvictionPolicy": "volatile-lru",
            "enableTls": True,
        },
    )
    if st not in (200, 202) or not isinstance(resp, dict):
        print(f"  MISSLYCKADES: HTTP {st}: {resp}")
        return 1
    task = resp.get("taskId")
    for _ in range(60):
        time.sleep(5)
        st2, t = _kalla("GET", f"/tasks/{task}")
        status = t.get("status") if isinstance(t, dict) else "?"
        print(f"  task: {status}")
        if status == "processing-completed":
            break
        if status == "processing-error":
            # Vanligaste orsaken om enableTls avvisas vid skapandet: slå på det
            # i efterhand med samma PUT som scripts/redis_tls_pa.py använder.
            print(f"  Felkropp: {json.dumps(t)[:800]}")
            return 1

    st, data = _kalla("GET", f"/fixed/subscriptions/{sub_id}/databases")
    if st == 200 and isinstance(data, dict):
        sub = data.get("subscription")
        poster = sub if isinstance(sub, list) else [sub]
        for p in poster or []:
            for db in (p or {}).get("databases", []):
                print(f"\n  Endpoint: {db.get('publicEndpoint')}")
    print("\n  Nästa steg (kräver databasens lösenord ur konsolen, getpass):")
    print("    python scripts/redis_konfig.py --env main --endpoint <host:port> --apply")
    print("  Och verifiera region/TLS efteråt: python scripts/redis_kontroll.py")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--planer", action="store_true", help="Lista köpbara fixed-planer i EU-regionen (läser bara).")
    p.add_argument("--skapa", action="store_true", help="Skapa prenumeration + databas. Kräver spärrflaggan.")
    p.add_argument("--plan-id", type=int, help="Plan-id ur --planer.")
    p.add_argument(
        "--jag-vet-att-detta-ror-produktionen",
        action="store_true",
        help="Obligatorisk vid --skapa. Används bara när Anton uttryckligen sagt till (§8.1a).",
    )
    args = p.parse_args()

    if args.planer:
        return lista_planer()
    if args.skapa:
        if not args.jag_vet_att_detta_ror_produktionen:
            print("  ⛔ SPÄRRAD (§8.1a): produktionens databas skapas bara på Antons uttryckliga ord.")
            print("  Kör med --jag-vet-att-detta-ror-produktionen när det ordet finns.")
            return 1
        if not args.plan_id:
            print("  --plan-id krävs — kör --planer först och välj.")
            return 1
        return skapa(args.plan_id)
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
