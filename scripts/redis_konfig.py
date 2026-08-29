#!/usr/bin/env python3
"""Sätt REDIS_URL för api-tjänsten i Railway — med ett live-pingtest före, inte hopp.

    python scripts/redis_konfig.py --env development --endpoint industry-pan-coppery-23072.db.redis.io:19335
    python scripts/redis_konfig.py --env development --endpoint <host>:<port> --apply

Samma princip som scripts/smtp_konfig.py: sätt ingenting i Railway förrän
uppgifterna är bevisade att fungera, inte bara inklistrade.

Lösenordet (Redis Clouds "Default user password") läses med getpass — det
syns aldrig på skärmen, hamnar aldrig i shell-historiken och skrivs aldrig ut.
Skriptet bygger REDIS_URL = redis://<användare>:<lösenord>@<host>:<port> och
testar ett riktigt PING mot databasen innan något sätts.

Paketet `redis` är valfritt HÄR (i den venv som kör scripts/) — testet hoppas
över med en varning om det saknas, det är inte samma venv som
snajp-support/requirements.txt gäller för, och backenden har paketet sedan
commit 09cfbc8 oavsett.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from railway_provision import envs_by_name, services_by_name, set_vars, state  # noqa: E402

# Windows-konsolen kör cp1252 och kan inte koda alla tecken vi skriver ut.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def testa_anslutning(url: str) -> str | None:
    """PING mot Redis. Returnerar felsträng, "___SAKNAS___" om paketet
    saknas i den här venv:n, eller None när det gick."""
    try:
        import redis  # valfritt beroende i scripts/-venv:n
    except ImportError:
        return "___SAKNAS___"
    try:
        klient = redis.from_url(url, socket_connect_timeout=10, socket_timeout=10)
        if not klient.ping():
            return "PING svarade utan PONG"
        return None
    except Exception as fel:  # noqa: BLE001
        return f"{type(fel).__name__}: {str(fel)[:200]}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default="development", choices=["development", "main"])
    p.add_argument(
        "--endpoint",
        required=True,
        help="host:port från Redis Cloud, t.ex. industry-pan-coppery-23072.db.redis.io:19335",
    )
    p.add_argument("--anvandare", default="default", help="Redis Cloud-användaren. Standard: default.")
    p.add_argument("--apply", action="store_true", help="Testa anslutningen och sätt REDIS_URL i Railway.")
    args = p.parse_args()

    if ":" not in args.endpoint:
        print("  --endpoint måste vara host:port.")
        return 1
    host, _, port = args.endpoint.rpartition(":")
    if not port.isdigit():
        print("  Porten i --endpoint måste vara ett tal (efter sista ':').")
        return 1

    rått = getpass.getpass("Redis-lösenord (Default user password, syns inte): ")
    losenord = "".join(rått.split())
    if not losenord:
        print("  Tomt lösenord — inget gjort.")
        return 1
    if losenord != rått.strip():
        print("  (Tog bort mellanslag ur lösenordet.)")

    url = f"redis://{args.anvandare}:{losenord}@{host}:{port}"

    print(f"\n  Testar PING mot {host}:{port} …")
    fel = testa_anslutning(url)
    if fel == "___SAKNAS___":
        print("  Paketet 'redis' finns inte i den här venv:n — hoppar över live-testet.")
        print("  Verifiera i stället EFTERÅT med /health/ready (se nedan).")
    elif fel:
        print(f"  MISSLYCKADES: {fel}")
        print("  Ingenting har satts i Railway. Kontrollera lösenord/endpoint i Redis Cloud-")
        print("  dashboarden (Databases -> din databas -> Configuration -> Connect), och om")
        print("  databasen har en IP-allowlist under Security — Railway saknar en fast utgående")
        print("  IP som standard, så en allowlist där stänger ute Railway även med rätt lösenord.")
        return 1
    else:
        print("  PING -> PONG. Anslutningen fungerar från den här maskinen.")
        print("  (Bevisar inte att Railway når samma databas — se IP-allowlist-varningen ovan")
        print("  om steget efter fortfarande visar \"jobs\": \"memory\".)")

    if not args.apply:
        print("\n  (Kör med --apply för att också sätta REDIS_URL i Railway.)")
        return 0

    projekt = state()
    miljoer = envs_by_name(projekt)
    tjanster = services_by_name(projekt)
    env_id = miljoer.get(args.env)
    api = tjanster.get("api")
    if not env_id or not api:
        print(f"  Hittade inte miljön {args.env!r} eller tjänsten 'api' i Railway.")
        return 1

    set_vars(api["id"], env_id, {"REDIS_URL": url})
    print(f"\n  REDIS_URL satt i {args.env}/api. Railway deployar om tjänsten automatiskt.")
    print("  Verifiera när den är uppe:")
    print("    curl -s https://<api-url för miljön>/health/ready")
    print('  Fältet "jobs" ska då säga "redis", inte "memory".')
    print()
    print("  OBS: dela inte samma Redis-databas mellan development och main längre fram —")
    print("  samma tysta korskoppling som GEMINI_API_KEY hade när båda miljöer läste samma")
    print("  nyckel. En andra (gratis) databas hos Redis Cloud åt main när den dagen kommer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
