#!/usr/bin/env python3
"""Godkänn om utkast som en sändspärr stoppade av ett skäl som nu är åtgärdat.

    python scripts/los_sandsparr.py --slug snajp --env main                       # torrkörning
    python scripts/los_sandsparr.py --slug snajp --env main --jag-menar-produktion --apply

Skriptet skriver ALDRIG själv i databasen. Det läser kandidatlistan read-only
och kör sedan exakt samma väg som granskarens "Godkänn och skicka"-knapp:
`POST /api/leads/queue/{id}/approve`, en post i taget, med kundens API-nyckel
ur .env.deploy. Den vägen byter den föråldrade foten (utskicksfot.byt_fot,
2026-10-20), kör tidsgrinden, språkgrinden och alla sex sändspärrarna om, och
skriver utfallet på köposten — ett utkast som fortfarande bryter mot en regel
blockeras igen med samma besked, så inget kan gå ut som inte passerar.

## Vad som räknas som åtgärdbart

Bara spärrskäl vars orsak ligger i kundregistret eller i en regel som sedan
dess mjukats upp:

* "Mejlet saknar en länk till avsändarens integritetspolicy …" — regel 2.
  Åtgärden är policy_url i kundregistret (scripts/fyll_kundregister.py).
* "Sidfoten saknar organisationsnummer, postadress …" — regel 1:s GAMLA
  lydelse; sedan Antons beslut 2026-10-10 kräver regeln bara företagsnamn.

Allt annat (provkörning, ej styrkt, karens, arkiverad, avregistrerad) rörs
inte: de skälen är riktiga och löser sig inte av en omgodkänning.

OBS: fotbytet kräver att miljön kör koden från 2026-10-20. Mot en äldre main
blockeras policyposterna om igen (ofarligt); kör skriptet en gång till när
releasen är ute.
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

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

#: Prefix i gate_checks->>'send_guard_skal' som är åtgärdbara. Prefix och inte
#: likhet: skälen bär mottagarspecifika uppräkningar efter kolon.
ATGARDBARA = (
    "Mejlet saknar en länk till avsändarens integritetspolicy",
    "Sidfoten saknar organisationsnummer",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="tenantens slug, t.ex. snajp")
    ap.add_argument("--env", choices=("main", "development"), default="main")
    ap.add_argument("--apply", action="store_true", help="godkänn om (annars visas bara planen)")
    ap.add_argument("--jag-menar-produktion", action="store_true")
    args = ap.parse_args()

    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    api_url = store.get(f"{prefix}_API_URL", "").rstrip("/")
    nyckel = store.get(f"{prefix}_KEY_{args.slug.upper().replace('-', '_')}")
    if not api_url or not nyckel:
        sys.exit(f"AVBRYTER: {prefix}_API_URL / {prefix}_KEY_{args.slug.upper()} saknas i .env.deploy.")

    conn = psycopg2.connect(dsn(store, args.env), connect_timeout=20)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("select id from public.ss_tenants where slug = %s", (args.slug,))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYTER: ingen tenant med sluggen {args.slug!r} i {args.env}.")
    tenant_id = rad[0]

    # Grindens underlag, sagt rakt ut: utan policy_url blockeras posterna igen.
    cur.execute(
        "select orgnr, foretagsadress, policy_url from public.ss_customer_details where tenant_id = %s",
        (tenant_id,),
    )
    detaljer = cur.fetchone() or (None, None, None)
    for namn, varde in zip(("orgnr", "foretagsadress", "policy_url"), detaljer):
        print(f"kundregistret.{namn}: {'satt' if varde else 'SAKNAS'}")
    if not detaljer[2]:
        print("VARNING: policy_url saknas — regel 2 blockerar om. Fyll i med scripts/fyll_kundregister.py först.")

    villkor = " or ".join("gate_checks->>'send_guard_skal' like %s" for _ in ATGARDBARA)
    monster = [p + "%" for p in ATGARDBARA]
    cur.execute(
        f"""select id::text, left(gate_checks->>'send_guard_skal', 60)
              from public.send_queue
             where tenant_id = %s and status = 'blocked' and ({villkor})
             order by created_at""",
        (tenant_id, *monster),
    )
    poster = cur.fetchall()
    conn.close()
    if not poster:
        print("Inget att göra: inga spärrade poster med åtgärdbara skäl.")
        return 0
    per_skal: dict[str, int] = {}
    for _, skal in poster:
        per_skal[skal] = per_skal.get(skal, 0) + 1
    for skal, antal in sorted(per_skal.items(), key=lambda x: -x[1]):
        print(f"  {antal:>4}  {skal}…")

    if not args.apply:
        print(f"\nTorrkörning: {len(poster)} poster skulle godkännas om. Kör med --apply.")
        return 0

    utfall: dict[str, int] = {}
    fel: list[str] = []
    for i, (item_id, _) in enumerate(poster, 1):
        req = urllib.request.Request(
            f"{api_url}/api/leads/queue/{item_id}/approve",
            data=b"{}",
            headers={"Content-Type": "application/json", "X-API-Key": nyckel},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as svar:
                ut = json.load(svar)
            utfall[str(ut.get("utfall"))] = utfall.get(str(ut.get("utfall")), 0) + 1
        except urllib.error.HTTPError as e:
            fel.append(f"{item_id}: HTTP {e.code}")
        except Exception as e:  # noqa: BLE001 — ett nätfel ska inte stoppa resten
            fel.append(f"{item_id}: {e}")
        if i % 10 == 0 or i == len(poster):
            print(f"{i}/{len(poster)}", flush=True)
        time.sleep(0.2)  # inte snabbare än en människa som klickar — API:t skickar på riktigt

    print("\nUtfall:", ", ".join(f"{k}: {v}" for k, v in sorted(utfall.items())) or "inga")
    for f in fel:
        print("FEL:", f)
    print("requeued = godkänt, skickas när sändfönstret öppnar; blocked = en spärr sa nej igen (se skälet i vyn).")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
