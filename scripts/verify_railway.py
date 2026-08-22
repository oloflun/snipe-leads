#!/usr/bin/env python3
"""Driftkontroll av Railway-stacken — båda miljöerna, mot verkligheten.

    python scripts/verify_railway.py

Samma roll som scripts/verify_render.py fyller för Render, och av samma skäl:
de fält som styr driften (gren, byggkontext, roll, radsäkerhet, korskoppling)
syns inte i någon diff. Sanningen ligger i Railways databas och i Postgres, så
den måste frågas ut.

Kontrollerna är valda för att kunna FALLA. En kontroll som bara läser tillbaka
det man nyss skrev bevisar ingenting; varje punkt nedan har en känd
felmöjlighet ur den här kodbasens historia.

Kräver RAILWAY_TOKEN och per-miljö-uppgifterna i .env.deploy.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway import gql  # noqa: E402
from railway_migrate import dsn  # noqa: E402
from railway_provision import (ENVIRONMENTS, PROJECT_ID, env_read,  # noqa: E402
                               envs_by_name, instance, services_by_name, state)

failures: list[str] = []
notes: list[str] = []


#: Sätts av main() så att en fallen kontroll säger VILKEN miljö den gäller.
#: Utan det blev listan "api: senaste deploy" fyra gånger, vilket är exakt lika
#: användbart som ingen lista alls.
scope = ""


def check(ok: bool, label: str, detail: str = "") -> None:
    # Detaljen skrivs bara ut när kontrollen FALLER. På en grön rad läste den
    # som ett fel — "OK main saknar spegelmarkör — mirror_meta finns" är en
    # självmotsägelse och exakt den sortens text som gör en rapport otrovärdig.
    tag = f"[{scope}] " if scope else ""
    print(f"  {'OK  ' if ok else 'FEL '} {tag}{label}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(f"{tag}{label}: {detail}")


def http(url: str, headers: dict | None = None, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "snajp-verify/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def no_redirect_status(url: str) -> int:
    opener = urllib.request.build_opener(type("NoRedirect", (urllib.request.HTTPRedirectHandler,), {
        "redirect_request": lambda *a, **k: None})())
    req = urllib.request.Request(url, headers={"User-Agent": "snajp-verify/1.0"})
    try:
        with opener.open(req, timeout=25) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def verify_services(project: dict, env_name: str, env_id: str, branch: str) -> None:
    global scope
    scope = env_name
    print(f"\n[{env_name}] tjänster")
    services = services_by_name(project)
    triggers = {
        (t["node"]["serviceId"], t["node"]["environmentId"]): t["node"]["branch"]
        for t in project["deploymentTriggers"]["edges"]
    }

    for name in ("api", "web", "Postgres"):
        check(name in services and instance(services[name], env_id) is not None,
              f"{name} finns i miljön")

    for name in ("api", "web"):
        svc = services.get(name)
        if not svc:
            continue
        # Grenen. web byggde `development` i tre deployer i rad medan
        # felsökningen letade i byggkontexten — meddelandet var sant men
        # beskrev en annan commit.
        actual = triggers.get((svc["id"], env_id))
        check(actual == branch, f"{name}: gren", f"{actual!r} (ska vara {branch!r})")

        inst = instance(svc, env_id) or {}
        ld = inst.get("latestDeployment") or {}
        check(ld.get("status") == "SUCCESS", f"{name}: senaste deploy", str(ld.get("status")))

    api = services.get("api")
    if api:
        inst = instance(api, env_id) or {}
        # Byggkontexten. Root Directory har återgått till undermappen av sig
        # självt på Render och fällt Docker-bygget med "/agent-core": not found.
        check(inst.get("rootDirectory") in ("/", None, ""), "api: byggkontext är repo-roten",
              repr(inst.get("rootDirectory")))
        check(inst.get("dockerfilePath") == "snajp-support/Dockerfile", "api: dockerfilePath",
              repr(inst.get("dockerfilePath")))


def verify_http(env_name: str, store: dict) -> None:
    global scope
    scope = env_name
    print(f"\n[{env_name}] HTTP")
    api = store.get(f"RAILWAY_{env_name.upper()}_API_URL")
    web = store.get(f"RAILWAY_{env_name.upper()}_WEB_URL")
    if not (api and web):
        check(False, "URL:er i .env.deploy", "saknas")
        return

    status, body = http(f"{api}/health/ready")
    check(status == 200, "api /health/ready svarar", str(status))
    if status == 200:
        payload = json.loads(body)
        check(payload.get("storage") == "postgres", "api använder Postgres, inte minnet",
              str(payload.get("storage")))
        for w in payload.get("warnings", []):
            notes.append(f"{env_name}/api: {w}")

    status, body = http(f"{web}/api/health")
    check(status == 200, "web /api/health svarar", str(status))
    if status == 200:
        check(json.loads(body).get("database") == "ok", "web når databasen")

    # Sessionsgrinden. Före 2026-08-15 var hela API-ytan anonymt nåbar.
    check(no_redirect_status(f"{web}/dashboard") in (302, 307), "web /dashboard kräver session")


def verify_isolation(store: dict) -> None:
    """Det som gör två miljöer meningsfulla: att de INTE når varandra.

    En delad demo-nyckel hade betytt att en dev-frontend kunde tala med
    main-backenden utan att någon märkte det — precis den sortens tysta
    korskoppling som gör att "det funkade i dev" slutar betyda något.
    """
    global scope
    scope = "korskoppling"
    print("\n[korskoppling] miljöerna får inte nå varandra")
    main_api = store.get("RAILWAY_MAIN_API_URL")
    dev_api = store.get("RAILWAY_DEVELOPMENT_API_URL")
    main_key = store.get("RAILWAY_MAIN_DEMO_API_KEY")
    dev_key = store.get("RAILWAY_DEVELOPMENT_DEMO_API_KEY")
    if not all((main_api, dev_api, main_key, dev_key)):
        check(False, "uppgifter för korskopplingstestet", "saknas i .env.deploy")
        return

    check(main_key != dev_key, "demo-nycklarna skiljer sig")
    check(http(f"{main_api}/api/leads/config", {"X-API-Key": main_key})[0] == 200,
          "main-nyckel mot main-api")
    check(http(f"{dev_api}/api/leads/config", {"X-API-Key": dev_key})[0] == 200,
          "dev-nyckel mot dev-api")
    check(http(f"{dev_api}/api/leads/config", {"X-API-Key": main_key})[0] == 401,
          "main-nyckel AVVISAS av dev-api")
    check(http(f"{main_api}/api/leads/config", {"X-API-Key": dev_key})[0] == 401,
          "dev-nyckel AVVISAS av main-api")


def scrub(text: str, store: dict) -> str:
    """Ta bort hemligheter ur en text som ska skrivas ut.

    Felmeddelanden är den väg en hemlighet läcker när ingen echar den: en DSN
    med lösenord i klartext hamnar i undantagets str() och därifrån i loggen.

    Bara hemligheterna maskeras. Värdnamn och URL:er lämnas kvar — de är inte
    hemliga, och ett felmeddelande där adressen är bortmaskerad går inte att
    felsöka, vilket är en annan sorts skada.
    """
    hemlig = ("PASSWORD", "SECRET", "KEY", "TOKEN")
    for key, value in store.items():
        if value and len(value) > 7 and any(h in key.upper() for h in hemlig):
            text = text.replace(value, "***")
    return text


def verify_database(env_name: str, store: dict) -> None:
    global scope
    scope = env_name
    print(f"\n[{env_name}] databas")
    try:
        conn = psycopg2.connect(dsn(store, env_name), connect_timeout=20)
    except psycopg2.OperationalError as exc:
        # En stängd väg IN är inte samma sak som en trasig databas — men den får
        # aldrig räknas som grönt, för kontrollerna nedan kördes inte. Ett
        # undantag som bubblar upp hade dessutom tagit med sig hela körningen,
        # inklusive den andra miljöns tjänst- och HTTP-kontroller som inte rör
        # databasen alls. Det var precis vad som hände 2026-08-20.
        check(False, "databasen går att nå",
              scrub(str(exc).strip().splitlines()[0], store))
        notes.append(
            f"[{env_name}] databaskontrollerna kördes INTE. Postgres nås utifrån via "
            "en TCP-proxy på en hög port; en miljö som bara släpper ut 443 tajmar ut "
            "här. Kör om från en terminal med öppen utgående TCP."
        )
        return
    cur = conn.cursor()

    cur.execute("select count(*) from supabase_migrations.schema_migrations")
    applied = cur.fetchone()[0]
    on_disk = len(list((Path(__file__).resolve().parents[1] / "supabase" / "migrations").glob("*.sql"))) + 1
    check(applied == on_disk, "alla migrationer körda", f"{applied} av {on_disk}")

    # RLS på ALLA tabeller. I produktionen kommer den från event-triggern
    # `ensure_rls`, inte från något `alter table` — en miljö utan triggern får
    # ett schema som ser identiskt ut men är oskyddat.
    cur.execute("""select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
                   where n.nspname='public' and c.relkind='r' and not c.relrowsecurity""")
    check(cur.fetchone()[0] == 0, "radsäkerhet på varje publik tabell")
    cur.execute("select 1 from pg_event_trigger where evtname='ensure_rls'")
    check(cur.fetchone() is not None, "event-triggern ensure_rls finns")

    # Approllerna får INTE kringgå radsäkerheten. Tabellägaren gör det utan att
    # något syns i en diff, och resultatet blir trovärdiga men felaktiga siffror.
    for role in ("snajp_app", "snajp_web"):
        cur.execute("select rolcanlogin, rolbypassrls from pg_roles where rolname=%s", (role,))
        row = cur.fetchone()
        check(bool(row) and row[0] and not row[1], f"{role}: login utan BYPASSRLS", str(row))

    # NULLIF-skyddet: utan det kastar varje oskopad fråga på en poolad
    # anslutning ''::uuid (migration 028).
    cur.execute("""select pg_get_functiondef(p.oid) from pg_proc p
                   join pg_namespace n on n.oid=p.pronamespace
                   where n.nspname='auth' and p.proname='uid'""")
    row = cur.fetchone()
    check(bool(row) and "nullif" in row[0].lower(), "auth.uid() har NULLIF-skydd")

    # Blockeraren: check-villkoret avvisade varje leads-körning i ett halvår.
    cur.execute("""select pg_get_constraintdef(oid) from pg_constraint
                   where conrelid='public.agent_runs'::regclass and contype='c'""")
    defs = " ".join(r[0] for r in cur.fetchall())
    check(all(f"'{k}'" in defs for k in ("leads", "leads_research", "leads_outreach")),
          "agent_runs tillåter leads-typerna")

    # Spegelmarkören. main får ALDRIG ha en — den är målets kännetecken, och
    # skulle den dyka upp där betyder det att riktningen vänts.
    cur.execute("""select exists (select 1 from information_schema.tables
                   where table_schema='public' and table_name='mirror_meta')""")
    has_marker = cur.fetchone()[0]
    if env_name == "main":
        check(not has_marker, "main saknar spegelmarkör",
              "mirror_meta finns — riktningen kan ha vänts")
    else:
        check(has_marker, "development har spegelmarkör")
        if has_marker:
            cur.execute("select environment from public.mirror_meta")
            row = cur.fetchone()
            check(bool(row) and row[0] == "development", "markören säger development", str(row))
    conn.close()


def main() -> int:
    store = env_read()
    project = state()
    environments = envs_by_name(project)

    for env_name, branch in ENVIRONMENTS.items():
        if env_name not in environments:
            check(False, f"miljön {env_name} finns")
            continue
        verify_services(project, env_name, environments[env_name], branch)
        verify_http(env_name, store)
        verify_database(env_name, store)

    verify_isolation(store)

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
    print("Alla kontroller gröna, båda miljöerna.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
