"""Lasttest mot en driftsatt miljö: läsvägar under samtidig last, och en chattskur.

    python scripts/lasttest.py --env development --etikett fore
    python scripts/lasttest.py --env development --etikett efter --anvandare 20 --sekunder 60

Två delar:

1. **Läsvägarna.** Ett antal samtidiga användare hämtar dashboardens vägar om
   och om igen i ett bestämt antal sekunder, som en arbetsyta med flera flikar
   öppna gör. Per väg: antal, fel, p50, p95, max, databastid och svarsstorlek
   (Server-Timing från api:t).
2. **Chattskuren.** Ett antal chattar startas samtidigt mot en evalkund
   (`python -m evals.kor forbered`), fler än chattens arbetare, så att kön
   syns. Per chatt: tid till svar och om den lyckades.

Bara läsningar och testchattar (is_test). Körs aldrig mot produktionen.
Nycklar läses ur .env.deploy och skrivs aldrig ut; svarskroppar skrivs aldrig
ut. Resultatet sparas i docs/stabilitet-2026-11/last/<etikett>.json.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROT = Path(__file__).resolve().parents[1]
UT = ROT / "docs" / "stabilitet-2026-11" / "last"

LASVAGAR = [
    "/api/leads/prospects?limit=1000",
    "/api/leads/skickat?limit=500",
    "/api/leads/korningar?limit=30",
    "/api/leads/queue",
    "/api/leads/runs",
    "/api/leads/config",
    "/api/leads/listor",
    "/api/inbox",
    "/api/kb",
    "/api/usage",
    "/api/kvitton",
    "/api/chattar",
    "/api/support/oversikt",
    "/health/ready",
]

CHATTFRAGOR = [
    "Vad kostar frakten och hur lång är leveranstiden?",
    "Kan vi betala med faktura?",
    "Hur länge har jag öppet köp?",
    "Håller ni HLR-kurser hos oss på kontoret?",
    "Vad krävs för att bli en Hjärtsäker zon?",
    "Går det att delbetala en hjärtstartare?",
    "Varan kom skadad, vad gör jag?",
    "Vad är eHLR?",
]


def _envfil() -> Path:
    for katalog in [ROT, *ROT.parents]:
        if (katalog / ".env.deploy").exists():
            return katalog / ".env.deploy"
    sys.exit("Hittar ingen .env.deploy.")


def _env() -> dict[str, str]:
    ut: dict[str, str] = {}
    for rad in _envfil().read_text(encoding="utf-8").splitlines():
        rad = rad.strip()
        if rad and not rad.startswith("#") and "=" in rad:
            namn, varde = rad.split("=", 1)
            ut[namn.strip()] = varde.strip().strip('"').strip("'")
    return ut


def _pct(varden: list[float], p: float) -> float | None:
    if not varden:
        return None
    v = sorted(varden)
    return round(v[min(len(v) - 1, max(0, round(p / 100 * (len(v) - 1))))], 1)


def las_under_last(api: str, nyckel: str, anvandare: int, sekunder: int) -> dict:
    slut = time.perf_counter() + sekunder
    lage: dict[str, dict] = {v: {"ms": [], "db": [], "fel": 0, "koder": {}, "byte": 0} for v in LASVAGAR}
    las = threading.Lock()

    def en_anvandare(nr: int) -> None:
        with httpx.Client(timeout=60, headers={"X-API-Key": nyckel}) as klient:
            i = nr  # olika användare börjar på olika vägar
            while time.perf_counter() < slut:
                vag = LASVAGAR[i % len(LASVAGAR)]
                i += 1
                start = time.perf_counter()
                try:
                    svar = klient.get(api + vag)
                    ms = (time.perf_counter() - start) * 1000
                    db = re.search(r"db;dur=([\d.]+)", svar.headers.get("server-timing", ""))
                    with las:
                        post = lage[vag]
                        post["ms"].append(ms)
                        post["koder"][svar.status_code] = post["koder"].get(svar.status_code, 0) + 1
                        post["byte"] = max(post["byte"], len(svar.content))
                        if db:
                            post["db"].append(float(db.group(1)))
                        if svar.status_code >= 500:
                            post["fel"] += 1
                except httpx.HTTPError:
                    with las:
                        lage[vag]["fel"] += 1

    with ThreadPoolExecutor(max_workers=anvandare) as pool:
        list(pool.map(en_anvandare, range(anvandare)))

    rader = {}
    for vag, post in lage.items():
        antal = len(post["ms"]) + post["fel"]
        rader[vag] = {
            "antal": antal,
            "fel": post["fel"],
            "koder": post["koder"],
            "p50_ms": _pct(post["ms"], 50),
            "p95_ms": _pct(post["ms"], 95),
            "max_ms": round(max(post["ms"]), 1) if post["ms"] else None,
            "db_p50_ms": _pct(post["db"], 50),
            "kb": round(post["byte"] / 1024, 1),
        }
    alla = [ms for post in lage.values() for ms in post["ms"]]
    fel = sum(post["fel"] for post in lage.values())
    return {
        "anvandare": anvandare,
        "sekunder": sekunder,
        "anrop": len(alla) + fel,
        "anrop_per_sekund": round((len(alla) + fel) / sekunder, 1),
        "fel": fel,
        "p50_ms": _pct(alla, 50),
        "p95_ms": _pct(alla, 95),
        "vagar": rader,
    }


def chattskur(api: str, nyckel: str, antal: int) -> dict:
    def en_chatt(nr: int) -> dict:
        huvud = {"X-API-Key": nyckel}
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=60) as klient:
                svar = klient.post(
                    api + "/api/chat",
                    headers=huvud,
                    json={
                        "message": CHATTFRAGOR[nr % len(CHATTFRAGOR)],
                        "customer_email": f"{uuid.uuid4()}@session.snajp.se",
                        "is_test": True,
                    },
                )
                if svar.status_code != 202:
                    return {"ok": False, "s": 0.0, "skal": f"start {svar.status_code}"}
                job_id = svar.json()["job_id"]
                while time.perf_counter() - start < 300:
                    time.sleep(0.5)
                    jobb = klient.get(f"{api}/api/jobs/{job_id}", headers=huvud).json()
                    if jobb.get("status") in ("completed", "failed"):
                        return {
                            "ok": jobb["status"] == "completed" and bool((jobb.get("result") or {}).get("reply")),
                            "s": round(time.perf_counter() - start, 1),
                            "skal": None if jobb["status"] == "completed" else str(jobb.get("error"))[:120],
                        }
        except (httpx.HTTPError, ValueError) as fel:
            return {"ok": False, "s": round(time.perf_counter() - start, 1), "skal": type(fel).__name__}
        return {"ok": False, "s": 300.0, "skal": "inget svar på fem minuter"}

    with ThreadPoolExecutor(max_workers=antal) as pool:
        utfall = list(pool.map(en_chatt, range(antal)))
    tider = [u["s"] for u in utfall if u["ok"]]
    return {
        "samtidiga": antal,
        "lyckade": len(tider),
        "misslyckade": [u["skal"] for u in utfall if not u["ok"]],
        "p50_s": round(statistics.median(tider), 1) if tider else None,
        "langsta_s": max(tider) if tider else None,
        "tider_s": sorted(tider),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default="development")
    p.add_argument("--etikett", required=True)
    p.add_argument("--anvandare", type=int, default=10)
    p.add_argument("--sekunder", type=int, default=30)
    p.add_argument("--chattar", type=int, default=8)
    a = p.parse_args()
    if a.env == "main":
        sys.exit("Lasttestet körs inte mot produktionen.")
    env = _env()
    prefix = f"RAILWAY_{a.env.upper()}_"
    api = env[prefix + "API_URL"].rstrip("/")
    lasnyckel = env.get(prefix + "KEY_SNAJP")
    evalnycklar = [n for n in env.get(f"EVAL_{a.env.upper()}_NYCKLAR", "").split(",") if n]
    if not lasnyckel:
        sys.exit(f"{prefix}KEY_SNAJP saknas i .env.deploy.")

    rapport: dict = {
        "etikett": a.etikett, "miljo": a.env,
        "tid": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": httpx.get(api + "/health", timeout=15).json().get("commit"),
    }
    print(f"läsvägar: {a.anvandare} samtidiga användare i {a.sekunder} s …", flush=True)
    rapport["lasning"] = las_under_last(api, lasnyckel, a.anvandare, a.sekunder)
    l = rapport["lasning"]
    print(f"  {l['anrop']} anrop ({l['anrop_per_sekund']}/s), {l['fel']} fel, p50 {l['p50_ms']} ms, p95 {l['p95_ms']} ms")
    for vag, r in sorted(l["vagar"].items(), key=lambda kv: -(kv[1]["p95_ms"] or 0)):
        print(f"  {vag:<36} n={r['antal']:<4} p50 {r['p50_ms']} p95 {r['p95_ms']} max {r['max_ms']} ms, "
              f"db {r['db_p50_ms']} ms, {r['kb']} kB, fel {r['fel']}")
    if a.chattar and evalnycklar:
        print(f"chattskur: {a.chattar} samtidiga chattar …", flush=True)
        rapport["chattskur"] = chattskur(api, evalnycklar[0], a.chattar)
        c = rapport["chattskur"]
        print(f"  {c['lyckade']}/{c['samtidiga']} lyckade, p50 {c['p50_s']} s, längsta {c['langsta_s']} s, "
              f"misslyckade: {c['misslyckade'] or 'inga'}")
    elif a.chattar:
        print("chattskuren hoppas över: inga evalnycklar (kör `python -m evals.kor forbered`).")
    UT.mkdir(parents=True, exist_ok=True)
    (UT / f"{a.etikett}.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
    print("sparat i", (UT / f"{a.etikett}.json").relative_to(ROT))


if __name__ == "__main__":
    main()
