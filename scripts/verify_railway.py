#!/usr/bin/env python3
"""Driftkontroll av Railway-stacken — mot verkligheten, inte mot en fil.

    python scripts/verify_railway.py

Samma roll som scripts/verify_render.py fyller för Render, och av samma skäl:
de fält som styr driften (gren, byggkontext, roll, radsäkerhet) syns inte i
någon diff. Sanningen ligger i Railways databas och i Postgres, så den måste
frågas ut.

Kontrollerna är valda för att kunna FALLA. En kontroll som bara läser tillbaka
det man nyss skrev bevisar ingenting; varje punkt nedan har en känd
felmöjlighet från den här kodbasens historia.

Kräver RAILWAY_TOKEN och Postgres-uppgifter i .env.deploy.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway import gql  # noqa: E402
from railway_migrate import dsn  # noqa: E402
from railway_provision import BRANCH, ENV_ID, PROJECT_ID, env_read  # noqa: E402

API_URL = "https://api-production-d7695.up.railway.app"
WEB_URL = "https://web-production-1fe2c.up.railway.app"

failures: list[str] = []
notes: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"  {'OK  ' if ok else 'FEL '} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(f"{label}: {detail}")


def http(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "snajp-verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


STATE = """
query($id: String!) {
  project(id: $id) {
    services { edges { node { id name
      serviceInstances { edges { node {
        environmentId rootDirectory dockerfilePath source { image repo }
        latestDeployment { status meta }
      } } }
    } } }
  }
}
"""


def verify_services() -> None:
    print("\nRailway-tjänster")
    data = gql(STATE, {"id": PROJECT_ID})
    services = {e["node"]["name"]: e["node"] for e in data["project"]["services"]["edges"]}

    for name in ("api", "web", "Postgres"):
        check(name in services, f"tjänsten {name} finns")

    for name in ("api", "web"):
        node = services.get(name)
        if not node:
            continue
        inst = next(
            (i["node"] for i in node["serviceInstances"]["edges"] if i["node"]["environmentId"] == ENV_ID),
            None,
        )
        if not inst:
            check(False, f"{name}: instans i miljön")
            continue

        # Grenen. web byggde `development` i tre deployer i rad medan
        # felsökningen letade i byggkontexten — felmeddelandet var sant men
        # beskrev en annan commit.
        meta = (inst.get("latestDeployment") or {}).get("meta") or {}
        check(meta.get("branch") == BRANCH, f"{name}: gren", f"{meta.get('branch')!r} (ska vara {BRANCH!r})")
        check(
            (inst.get("latestDeployment") or {}).get("status") == "SUCCESS",
            f"{name}: senaste deploy",
            str((inst.get("latestDeployment") or {}).get("status")),
        )

    api = services.get("api")
    if api:
        inst = next(i["node"] for i in api["serviceInstances"]["edges"] if i["node"]["environmentId"] == ENV_ID)
        # Byggkontexten. Root Directory har återgått till undermappen av sig
        # självt på Render och fällt Docker-bygget två gånger med
        # `"/agent-core": not found`.
        check(inst.get("rootDirectory") in ("/", None, ""), "api: byggkontext är repo-roten",
              repr(inst.get("rootDirectory")))
        check(inst.get("dockerfilePath") == "snajp-support/Dockerfile", "api: dockerfilePath",
              repr(inst.get("dockerfilePath")))


def verify_http() -> None:
    print("\nHTTP")
    status, body = http(f"{API_URL}/health/ready")
    check(status == 200, "api /health/ready svarar", str(status))
    if status == 200:
        payload = json.loads(body)
        check(payload.get("storage") == "postgres", "api använder Postgres, inte minnet",
              str(payload.get("storage")))
        for w in payload.get("warnings", []):
            notes.append(f"api: {w}")

    status, body = http(f"{WEB_URL}/api/health")
    check(status == 200, "web /api/health svarar", str(status))
    if status == 200:
        check(json.loads(body).get("database") == "ok", "web når databasen")

    # Sessionsgrinden. Utan cookie ska /dashboard vara en omdirigering till
    # /login, inte en sida. Före 2026-08-15 var hela API-ytan anonymt nåbar.
    req = urllib.request.Request(f"{WEB_URL}/dashboard", headers={"User-Agent": "snajp-verify/1.0"})
    opener = urllib.request.build_opener(type("NoRedirect", (urllib.request.HTTPRedirectHandler,), {
        "redirect_request": lambda *a, **k: None})())
    try:
        with opener.open(req, timeout=30) as resp:
            check(False, "web /dashboard kräver session", f"gav {resp.status} utan cookie")
    except urllib.error.HTTPError as exc:
        check(exc.code in (302, 307), "web /dashboard kräver session", f"HTTP {exc.code}")


def verify_database() -> None:
    print("\nDatabas")
    conn = psycopg2.connect(dsn(env_read()), connect_timeout=20)
    cur = conn.cursor()

    cur.execute("select count(*) from supabase_migrations.schema_migrations")
    applied = cur.fetchone()[0]
    on_disk = len(list((Path(__file__).resolve().parents[1] / "supabase" / "migrations").glob("*.sql"))) + 1
    check(applied == on_disk, "alla migrationer körda", f"{applied} av {on_disk}")

    # RLS på ALLA tabeller. I produktionen kommer den från event-triggern
    # `ensure_rls`, inte från något `alter table` i migrationerna — en gren utan
    # triggern får ett schema som ser identiskt ut men är oskyddat.
    cur.execute("""select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
                   where n.nspname='public' and c.relkind='r' and not c.relrowsecurity""")
    unprotected = cur.fetchone()[0]
    check(unprotected == 0, "radsäkerhet på varje publik tabell", f"{unprotected} utan")

    cur.execute("select 1 from pg_event_trigger where evtname='ensure_rls'")
    check(cur.fetchone() is not None, "event-triggern ensure_rls finns")

    # Rollerna får INTE kringgå radsäkerheten. Tabellägaren gör det utan att
    # något syns i en diff, och resultatet blir trovärdiga men felaktiga siffror.
    for role in ("snajp_app", "snajp_web"):
        cur.execute("select rolcanlogin, rolbypassrls from pg_roles where rolname=%s", (role,))
        row = cur.fetchone()
        check(row is not None, f"rollen {role} finns")
        if row:
            check(row[0] and not row[1], f"{role}: login utan BYPASSRLS", f"login={row[0]} bypassrls={row[1]}")

    # auth.uid() ska läsa GUC:en med NULLIF-skydd. Utan det kastar varje oskopad
    # fråga på en poolad anslutning ''::uuid (migration 028).
    cur.execute("""select pg_get_functiondef(p.oid) from pg_proc p
                   join pg_namespace n on n.oid=p.pronamespace
                   where n.nspname='auth' and p.proname='uid'""")
    row = cur.fetchone()
    check(row is not None, "auth.uid() finns")
    if row:
        check("nullif" in row[0].lower(), "auth.uid() har NULLIF-skydd")

    # Blockeraren från 2026-08-16: check-villkoret avvisade varje leads-körning.
    cur.execute("""select pg_get_constraintdef(oid) from pg_constraint
                   where conrelid='public.agent_runs'::regclass and contype='c'""")
    defs = " ".join(r[0] for r in cur.fetchall())
    for kind in ("leads", "leads_research", "leads_outreach"):
        check(f"'{kind}'" in defs, f"agent_runs tillåter {kind}")

    conn.close()


def main() -> int:
    verify_services()
    verify_http()
    verify_database()

    if notes:
        print("\nNoteringar (inte fel):")
        for n in notes:
            print(f"  · {n}")

    print()
    if failures:
        print(f"{len(failures)} kontroll(er) föll:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Alla kontroller gröna.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
