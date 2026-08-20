#!/usr/bin/env python3
"""Ett kommando som gör Railway-development färdig — i rätt ordning, idempotent.

    python scripts/railway_gor_klart.py            # visa planen och vad som går
    python scripts/railway_gor_klart.py --apply    # gör det

## Varför den finns

Sju kommandon i rätt ordning, med två olika förutsättningar, är en punktlista i
ett dokument — och en punktlista går inte att köra om, verifiera eller
falsifiera. Det här är samma steg som ett kommando som säger vad det gjorde.

Ordningen är inte godtycklig:

 1. `.env.deploy` ur Railway först. Utan den saknar varje senare steg sina
    uppgifter, och `railway_provision.py` hade GENERERAT nya i stället —
    alltså roterat lösenordet under en levande stack.
 2. LLM-nyckeln före migrationerna, för att den går över HTTPS och därför
    fungerar även från en maskin som inte når databasen. Det som kan bli klart
    ska bli klart.
 3. Migrationerna före adminraden: `admin_cleanup` skriver i tabeller som
    migrationskedjan äger.
 4. `railway-main` FÖRE `railway-development` när adminraden skapas.
    `railway_seed_dev.py` kopierar `platform_admins` main → development, så en
    rad som bara finns i dev försvinner vid nästa spegling.
 5. Verifiering sist, och ett riktigt prov av exempelbolagsvägen allra sist:
    ett grönt API säger att tjänsten lever, inte att knappen fungerar.

## Två förutsättningar, inte en

Steg som bara talar HTTPS går överallt. Steg som talar med Postgres kräver en
maskin med öppen utgående TCP — Railways databas nås via en TCP-proxy på en hög
port, och en molnsession släpper bara ut 443. Skriptet MÄTER det i förväg i
stället för att låta tre kommandon i rad tajma ut på 20 sekunder var.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_provision import env_read  # noqa: E402

HAR = Path(__file__).resolve().parent
PY = sys.executable

#: (namn, argv, kräver_databas)
STEG: list[tuple[str, list[str], bool]] = [
    (".env.deploy ur Railway", ["railway_env_bootstrap.py", "--apply"], False),
    ("LLM-nyckeln", ["railway_repair_llm_key.py", "--env", "development", "--apply"], False),
    ("migrationskedjan", ["railway_migrate.py", "--env", "development", "--apply"], True),
    ("adminraden i main", ["admin_cleanup.py", "--env", "railway-main"], True),
    ("adminraden i development", ["admin_cleanup.py", "--env", "railway-development"], True),
    ("adminraden, kontroll", ["admin_cleanup.py", "--env", "railway-development", "--diagnos"], True),
    ("driftkontroll", ["verify_railway.py"], True),
]


def kor(argv: list[str]) -> int:
    print(f"\n$ python scripts/{' '.join(argv)}", flush=True)
    return subprocess.run([PY, str(HAR / argv[0]), *argv[1:]]).returncode


def databasen_nas(store: dict) -> tuple[bool, str]:
    """Går det att öppna en TCP-anslutning till dev-databasens proxy?

    Mäts med en ren socket och inte med psycopg2: det som ska avgöras är om
    PORTEN är öppen, inte om lösenordet stämmer. En blandning av de två frågorna
    ger ett svar som inte pekar på någonting.
    """
    host = store.get("RAILWAY_DEVELOPMENT_PG_HOST")
    port = store.get("RAILWAY_DEVELOPMENT_PG_PORT")
    if not (host and port):
        return False, "RAILWAY_DEVELOPMENT_PG_{HOST,PORT} saknas i .env.deploy"
    try:
        socket.create_connection((host, int(port)), timeout=10).close()
        return True, f"{host}:{port} svarar"
    except Exception as exc:
        return False, f"{host}:{port} — {type(exc).__name__}"


def prova_exempelbolag(store: dict) -> bool:
    """Sista provet: går det att ladda in exempelbolag i den riktiga deployen?

    Först ett LÄSANDE prov av att migration 039 är körd (fältet `origin` ska
    finnas på en prospektrad), sedan ett riktigt anrop som skapar ETT bolag.
    Ordningen sparar en skräprad den dagen migrationen inte är körd, och skiljer
    "inte körd" från "körd men trasig".
    """
    url = store.get("RAILWAY_DEVELOPMENT_API_URL")
    key = store.get("RAILWAY_DEVELOPMENT_DEMO_API_KEY")
    if not (url and key):
        print("  ! API-URL eller demo-nyckel saknas i .env.deploy")
        return False

    def anrop(path: str, kropp: dict | None = None):
        data = json.dumps(kropp).encode() if kropp is not None else None
        req = urllib.request.Request(
            f"{url}{path}", data=data,
            headers={"X-API-Key": key, "Content-Type": "application/json",
                     "User-Agent": "snajp-gorklart/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()[:300]

    status, body = anrop("/api/leads/prospects")
    if status != 200:
        print(f"  FEL  kunde inte lista prospekt: HTTP {status}")
        return False
    rader = body.get("prospects") or []
    if rader and "origin" not in rader[0]:
        print("  FEL  kolumnen prospects.origin saknas — migration 039 är inte körd.")
        print("       Exempelbolag kan inte skapas förrän den är det.")
        return False

    status, body = anrop("/api/leads/prospects/exempel", {"limit": 1})
    if status != 201:
        print(f"  FEL  exempelbolag: HTTP {status} — {body}")
        return False
    skapat = (body.get("created") or [{}])[0]
    if skapat.get("origin") != "example":
        print(f"  FEL  bolaget skapades utan origin='example' ({skapat.get('origin')!r}).")
        print("       Utan markeringen kan utskicksspärren inte skilja det från ett riktigt.")
        return False
    print(f"  OK   exempelbolag skapat: {skapat.get('company_name')} (origin=example)")
    print(f"       {skapat.get('motivering', '')}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="kör stegen (annars visas bara planen)")
    ap.add_argument("--hoppa-db", action="store_true",
                    help="kör bara stegen som talar HTTPS, även om databasen nås")
    args = ap.parse_args()

    store = env_read()
    if not store.get("RAILWAY_TOKEN"):
        sys.exit("RAILWAY_TOKEN saknas i .env.deploy — utan den går inget av det här.\n"
                 "Sätt den med: python scripts/set_railway_token.py")

    db_ok, db_detalj = (False, "hoppas över (--hoppa-db)") if args.hoppa_db else databasen_nas(store)
    print(f"databasvägen: {'ÖPPEN' if db_ok else 'STÄNGD'} — {db_detalj}")
    if not db_ok and not args.hoppa_db:
        print("  Railways Postgres nås via en TCP-proxy på en hög port. Går bara 443 ut\n"
              "  (molnsession, restriktivt nät) körs migrationerna och adminraden inte här.")

    print("\nplan:")
    for namn, argv, kraver_db in STEG:
        markering = "–" if kraver_db and not db_ok else "×"
        print(f"  {markering} {namn:26} python scripts/{' '.join(argv)}")
    print(f"  × {'exempelbolag i drift':26} (inbyggt prov över HTTPS)")
    print("\n  × körs, – hoppas över.")

    if not args.apply:
        print("\nKör om med --apply.")
        return 0

    hoppade: list[str] = []
    for namn, argv, kraver_db in STEG:
        if kraver_db and not db_ok:
            hoppade.append(namn)
            continue
        kod = kor(argv)
        if kod != 0:
            # verify_railway faller med flit när databasen inte nås; det är
            # ingen anledning att låta bli det sista provet.
            print(f"\n  ! steget {namn!r} slutade med kod {kod}")

    print("\n--- exempelbolag i drift ---")
    exempel_ok = prova_exempelbolag(store)

    print("\n=== sammanfattning ===")
    print(f"  exempelbolagsvägen: {'GRÖN' if exempel_ok else 'RÖD'}")
    if hoppade:
        print("  hoppades över (databasen nås inte härifrån):")
        for namn in hoppade:
            print(f"    - {namn}")
        if not exempel_ok:
            # Skilj "vägen är trasig" från "steget som skulle laga den kördes
            # inte". Samma röda rad med två helt olika åtgärder är precis den
            # sortens rapport som får någon att felsöka fel sak.
            print("\n  Rött ovan är VÄNTAT så länge migrationskedjan är överhoppad —")
            print("  exempelbolag kräver kolumnen som 039 lägger till.")
        print("  Kör om det här kommandot från en maskin med öppen utgående TCP.")
    return 0 if exempel_ok and not hoppade else 1


if __name__ == "__main__":
    raise SystemExit(main())
