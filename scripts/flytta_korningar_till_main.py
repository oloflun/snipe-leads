#!/usr/bin/env python3
"""Flytta ALLA development-körningar till main — genom flyttvägen, i bulk.

    python scripts/flytta_korningar_till_main.py                 # torrkörning: vad som skulle flyttas
    python scripts/flytta_korningar_till_main.py --apply         # flytta allt
    python scripts/flytta_korningar_till_main.py --slug snajp --apply

Sebbes beställning 2026-10-20: alla körningar gjorda i development ska till
main, utan dubbletter och utan att något mejl försvinner. Skriptet gör samma
sak som knappen Byt kund → Flytta till main, fast för varje dev-only körning
på en gång: det läser BÅDA databaserna (read-only) för att hitta körningar
vars job_id finns i development men inte i main, och skickar dem sedan genom
developments eget flytt-API (`POST /api/admin/flytt/skicka`) i omgångar.

## Varför API:t och inte SQL

INV-DATA-003: flyttvägen är den ENDA vägen från development till produktion.
Paketet signeras, mottagaren vägrar i en spegel, varje rad dedupliceras
(körningar på job_id, prospekt på bolagsnamn, utkast på väntande utkast i
tråden) och varje flytt loggas i dev_flytt_ko. En SQL-kopia hade hoppat över
alltihop. Databasläsningen här är bara kandidatlistan.

## Säkert att köra om

Mottagarens körningsimport är självläkande sedan 2026-10-20: en körning som
redan finns i main kompletteras med de prospekt och utkast en äldre flytt
inte bar ("kompletterad" i kvittot), i stället för att stanna vid "redan
flyttad". Provkörningar (is_test) flyttas aldrig — samma regel som synken.

OBS: flytten bär utkasten bara när BÅDA miljöerna kör koden från 2026-10-20
(utkast i paketet + självläkande import). Kör skriptet efter att releasen
nått main; körs det före följer bara körning+prospekt med, och en omkörning
efter releasen kompletterar utkasten.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

#: Körningar per anrop. Varje körning bär sina prospekt med utkast, så
#: paketen hålls små nog för mottagarens 60-sekundersfönster.
OMGANG = 10


def api_anrop(url: str, nyckel: str, kropp: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(kropp, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": nyckel},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as svar:
            return json.load(svar)
    except urllib.error.HTTPError as fel:
        try:
            detalj = json.load(fel).get("detail", "")
        except Exception:  # noqa: BLE001
            detalj = ""
        sys.exit(f"AVBRYTER: flytt/skicka svarade {fel.code}: {detalj}")


def kandidater(store: dict, slug_filter: str | None) -> dict[str, list[str]]:
    """slug → job_id-lista för körningar (ej test) som finns i development
    men inte i main. Läser båda databaserna utan att skriva."""
    dev = psycopg2.connect(dsn(store, "development"), connect_timeout=20)
    mn = psycopg2.connect(dsn(store, "main"), connect_timeout=20)
    for c in (dev, mn):
        c.set_session(readonly=True, autocommit=True)
    dc, mc = dev.cursor(), mn.cursor()

    dc.execute("select to_regclass('public.mirror_meta') is not null")
    if not dc.fetchone()[0]:
        sys.exit("AVBRYT: development saknar mirror_meta. Fel databas?")
    if _finns(mc, "mirror_meta"):
        mc.execute("select count(*) from public.mirror_meta")
        if mc.fetchone()[0]:
            sys.exit("AVBRYT: main-databasen har en spegelmarkör. Det är inte main.")

    mc.execute("select job_id::text from public.leads_job_ledger")
    i_main = {r[0] for r in mc.fetchall()}
    dc.execute(
        """select l.job_id::text, t.slug, l.created_at
             from public.leads_job_ledger l join public.ss_tenants t on t.id = l.tenant_id
            where not coalesce(l.is_test, false)
              -- Bara körningarna: delstegen (research_and_draft per lead)
              -- följer med sin körning, och deras prospekt finns redan i main.
              and l.scope in ('batch', 'lista')
            order by l.created_at"""
    )
    ut: dict[str, list[str]] = defaultdict(list)
    for job_id, slug, _ in dc.fetchall():
        if job_id in i_main:
            continue
        if slug_filter and slug != slug_filter:
            continue
        ut[slug].append(job_id)
    dev.close()
    mn.close()
    return dict(ut)


def _finns(cur, tabell: str) -> bool:
    cur.execute("select to_regclass('public.' || %s) is not null", (tabell,))
    return bool(cur.fetchone()[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="bara en kund (annars alla)")
    ap.add_argument("--apply", action="store_true", help="flytta (annars visas bara planen)")
    args = ap.parse_args()

    store = env_read()
    api_url = store.get("RAILWAY_DEVELOPMENT_API_URL", "").rstrip("/")
    master = store.get("RAILWAY_DEVELOPMENT_MASTER_API_KEY")
    if not api_url or not master:
        sys.exit("AVBRYTER: RAILWAY_DEVELOPMENT_API_URL / _MASTER_API_KEY saknas i .env.deploy.")

    plan = kandidater(store, args.slug)
    if not plan:
        print("Inget att flytta: varje icke-test-körning i development finns redan i main.")
        return 0
    for slug, jobs in plan.items():
        print(f"{slug}: {len(jobs)} körningar att flytta")
    if not args.apply:
        print("\nTorrkörning: inget skickat. Kör med --apply.")
        return 0

    summering: dict[str, int] = defaultdict(int)
    fel: list[str] = []
    for slug, jobs in plan.items():
        for i in range(0, len(jobs), OMGANG):
            omgang = jobs[i : i + OMGANG]
            svar = api_anrop(
                f"{api_url}/api/admin/flytt/skicka",
                master,
                {"slug": slug, "typ": "korning", "ids": omgang},
            )
            for rad in svar.get("rader") or []:
                summering[str(rad.get("resultat"))] += 1
                summering["prospekt"] += int(rad.get("prospekt") or 0)
                summering["utkast"] += int(rad.get("utkast") or 0)
                if rad.get("resultat") == "fel":
                    fel.append(f"{slug} {rad.get('ref_id')}: {rad.get('fel')}")
            print(f"{slug}: {min(i + OMGANG, len(jobs))}/{len(jobs)}", flush=True)

    print(
        f"\nKlart. Körningar: {summering.get('importerad', 0)} flyttade, "
        f"{summering.get('kompletterad', 0)} kompletterade, "
        f"{summering.get('redan_flyttad', 0)} fanns redan, {summering.get('fel', 0)} fel. "
        f"Prospekt: {summering.get('prospekt', 0)}. Utkast: {summering.get('utkast', 0)}."
    )
    for f in fel:
        print("FEL:", f)
    if not fel:
        print("Kontroll: kör skriptet igen — allt ska då vara 'redan flyttad'.")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
