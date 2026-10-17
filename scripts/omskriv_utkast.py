#!/usr/bin/env python3
"""Skriv om leads-utkast hos en kund i development genom den riktiga kedjan.

    python scripts/omskriv_utkast.py --slug snajp --sedan "2026-10-11"            # visa vilka
    python scripts/omskriv_utkast.py --slug snajp --sedan "2026-10-11" --apply    # kör

Varje prospekt som fått ett research_and_draft-jobb sedan --sedan (eller som
anges med --prospekt id …) skickas till `POST /api/leads/prospects/processa-om`
med `scope=utkast`: det väntande utkastet ställs in och kasseras, och ett nytt
skrivs ur leadets sparade research genom samma utkastkedja och grindar som en
vanlig körning (app/leads/sparad_research.py). Bedömningen ändras inte.
`--med-research` kör i stället research + utkast om (`research_and_draft`,
`ersatt=true`), vilket kan fälla leads till nivå C. Utkasten hamnar i
granskningskön; inget skickas.

Kundens API-nyckel läses ur Railways `web`-tjänst (variabeln `SNAJP_KEY_<SLUG>`)
med samma helpers som railway_tenant_keys.py. Nyckeln skrivs aldrig ut.
Bara development.
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

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read, envs_by_name, read_vars, services_by_name, state  # noqa: E402
from railway_tenant_keys import env_key  # noqa: E402

BATCH = 20


def tenant_nyckel(slug: str) -> str:
    project = state()
    env_id = envs_by_name(project)["development"]
    web = services_by_name(project)["web"]["id"]
    nyckel = read_vars(web, env_id).get(env_key(slug))
    if not nyckel:
        sys.exit(f"AVBRYTER: {env_key(slug)} saknas på web i development.")
    return nyckel


def anrop(api: str, nyckel: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{api}{path}", data=data, method="POST" if body is not None else "GET",
        headers={"X-API-Key": nyckel, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"HTTP {exc.code} på {path}: {exc.read().decode()[:600]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--sedan", help="prospekt med research_and_draft-jobb sedan denna tidpunkt")
    ap.add_argument("--prospekt", nargs="*", default=[], help="prospekt-id:n i stället för --sedan")
    ap.add_argument("--utan-utkast", action="store_true",
                    help="bara prospekt som saknar ett osänt utkast skapat sedan --sedan")
    ap.add_argument("--med-research", action="store_true",
                    help="kör om researchen också (ny bedömning) i stället för bara utkastet")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not a.sedan and not a.prospekt:
        sys.exit("Ange --sedan eller --prospekt.")

    store = env_read()
    api = store["RAILWAY_DEVELOPMENT_API_URL"].rstrip("/")
    conn = psycopg2.connect(dsn(store, "development"), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("select id from ss_tenants where slug = %s", (a.slug,))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"Kunden {a.slug} finns inte.")
    tenant_id = str(rad["id"])
    if a.prospekt:
        ids = list(dict.fromkeys(a.prospekt))
    else:
        filter_ = (
            """ and p.id not in (
                     select t.prospect_id from outreach_threads t join send_queue s on s.thread_id = t.id
                      where t.tenant_id = %s and s.created_at >= %s and s.status in ('awaiting_review', 'queued'))"""
            if a.utan_utkast else ""
        )
        cur.execute(
            f"""select distinct l.prospect_id, p.company_name from leads_job_ledger l
                 join prospects p on p.id = l.prospect_id
                where l.tenant_id = %s and l.created_at >= %s and l.scope = 'research_and_draft'{filter_}
                order by p.company_name""",
            (tenant_id, a.sedan, tenant_id, a.sedan) if a.utan_utkast else (tenant_id, a.sedan),
        )
        rader = cur.fetchall()
        ids = [str(r["prospect_id"]) for r in rader]
        for r in rader:
            print(f"  {r['company_name']}")
    print(f"{len(ids)} prospekt hos {a.slug}")
    if not a.apply:
        print("Inget gjort. Kör med --apply.")
        return 0

    nyckel = tenant_nyckel(a.slug)
    jobb = 0
    for i in range(0, len(ids), BATCH):
        del_ = ids[i : i + BATCH]
        svar = anrop(api, nyckel, "/api/leads/prospects/processa-om",
                     {"prospect_ids": del_, "scope": "research_and_draft", "ersatt": True}
                     if a.med_research else {"prospect_ids": del_, "scope": "utkast"})
        n = len(svar.get("jobs") or [])
        jobb += n
        print(f"  batch {i // BATCH + 1}: {n} jobb köade")
        time.sleep(1)
    print(f"{jobb} jobb köade. Följ dem i Leads › Körningar eller med scripts/granska_utkast.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
