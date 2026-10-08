#!/usr/bin/env python
"""Lägger på den lagstadgade sidfoten på utkast som send_guard regel 1 stoppat,
och lägger tillbaka dem i granskningskön. Torrkörning som standard.

    python scripts/lagg_pa_utskicksfot.py                      # visar vad som skulle göras
    python scripts/lagg_pa_utskicksfot.py --kund snajp         # en kund
    python scripts/lagg_pa_utskicksfot.py --apply              # gör det (development)
    python scripts/lagg_pa_utskicksfot.py --env main --apply --main-godkand

Skälet (2026-10-08): foten (org.nr, postadress, ändamål, avregistreringslänk)
läggs på av KOD vid köningen (app/agent/leads_tools._med_lagstadgad_fot) och
bara om kundregistret har org.nr och företagsadress. Utkast skrivna innan
uppgifterna fanns saknar den, och send_guard regel 1 satte dem i 'blocked' —
en slutstatus som varken sändaren eller Godkänn och skicka rör. Att skapa om
utkasten kostar en ny research och skriver en annan text än den som godkänts.
Här byggs samma fot med samma kod (app/leads/utskicksfot.py) och samma
avregistreringstoken (ss_avregistreringslankar), och posten blir
'awaiting_review'. Godkännandet tas bort med flit: texten har ändrats, så en
människa ska se och godkänna den nya innan den skickas.

Skydd:
- Bara poster med status 'blocked' och send_guard_regel '1_avsandaridentifikation'.
  Spärrar som 'ej_styrkt' och 'testkorning' rörs aldrig.
- Kundens org.nr och företagsadress måste finnas i kundregistret (Kunder &
  Data); saknas de avbryts allt med besked om vad som saknas. Saknad
  policy_url varnas för (regel 2 hade stoppat utskicket igen).
- Ett utkast som redan bär en fot (avregistreringslänk) får ingen andra.
- Main kräver --main-godkand (produktionsdata, Antons ord gäller).
- Allt i EN transaktion. Inga adresser eller mejltexter skrivs ut.
Lösenord och Railway-token läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

#: Railway-ID:n för api-tjänsten och miljöerna (se railway_provision.state()).
API_SERVICE_ID = "5828c279-ad8f-429b-b5e1-969372db8a0a"
MILJO_ID = {
    "development": "02c39616-1b8e-47b7-beea-d8c6cfba1acd",
    "main": "47bc7047-a458-404b-a1de-ccec612cb96e",
}


def _utskicksfot():
    """app/leads/utskicksfot.py laddad direkt ur filen: modulen beror bara på
    re och secrets, medan paketet app drar in hela backendens beroenden."""
    fil = REPO / "snajp-support" / "app" / "leads" / "utskicksfot.py"
    spec = importlib.util.spec_from_file_location("utskicksfot", fil)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


fot = _utskicksfot()


def saknade_uppgifter(kund: dict) -> list[str]:
    """Det som saknas för att foten ska klara regel 1."""
    return [
        etikett
        for etikett, nyckel in (("företagsnamn", "namn"), ("organisationsnummer", "orgnr"), ("företagsadress", "adress"))
        if not str(kund.get(nyckel) or "").strip()
    ]


def med_fot(brodtext: str, *, kund: dict, lank: str) -> str | None:
    """Brödtexten med foten, eller None om den redan bär en.

    Samma anrop som leads_tools._med_lagstadgad_fot, med kundregistrets värden
    ordagrant (regel 1 jämför dem mot texten)."""
    if fot.har_fot(brodtext):
        return None
    return fot.med_fot(
        brodtext,
        fot=fot.bygg_fot(
            foretagsnamn=str(kund["namn"]).strip(),
            orgnr=str(kund["orgnr"]).strip(),
            postadress=str(kund["adress"]).strip(),
            lank=lank,
            policy_url=str(kund.get("policy_url") or "").strip(),
        ),
    )


URVAL = """
    select q.id, q.tenant_id, t.slug, m.id, m.body, p.contact_email
      from send_queue q
      join ss_tenants t on t.id = q.tenant_id
      join outreach_threads th on th.id = q.thread_id
      left join prospects p on p.id = th.prospect_id
      left join lateral (
        select id, body from outreach_messages
         where tenant_id = q.tenant_id and thread_id = q.thread_id and direction = 'outbound'
           and sent_at is null and kasserad_at is null
         order by created_at desc, id desc limit 1
      ) m on true
     where q.status = 'blocked'
       and q.gate_checks->>'send_guard_regel' = '1_avsandaridentifikation'
       and (%(kund)s::text is null or t.slug = %(kund)s::text)
     order by t.slug, q.created_at
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", choices=tuple(MILJO_ID), default="development")
    parser.add_argument("--kund", default=None, help="bara den här kundens slug")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--main-godkand", action="store_true", help="krävs för --apply mot main")
    args = parser.parse_args()
    if args.env == "main" and args.apply and not args.main_godkand:
        sys.exit("AVBRYTER: --apply mot main kräver --main-godkand (Antons uttryckliga ord).")

    import psycopg2
    from railway_migrate import dsn
    from railway_provision import env_read, read_vars

    # Samma två namn som Settings.publik_bas_url läser; Railway har PUBLIC_BASE_URL.
    variabler = read_vars(API_SERVICE_ID, MILJO_ID[args.env])
    bas_url = (variabler.get("PUBLIK_BAS_URL") or variabler.get("PUBLIC_BASE_URL") or "").strip()
    if not bas_url:
        sys.exit(f"AVBRYTER: PUBLIC_BASE_URL saknas för api i {args.env}; avregistreringslänken går inte att bygga.")

    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(URVAL, {"kund": args.kund})
            poster = cur.fetchall()
            if not poster:
                print("Inga utkast stoppade av regel 1. Inget att göra.")
                return 0

            kunder: dict[str, dict] = {}
            for tenant_id, slug in {(p[1], p[2]) for p in poster}:
                cur.execute(
                    "select t.name, d.orgnr, d.foretagsadress, d.policy_url from ss_tenants t"
                    " left join ss_customer_details d on d.tenant_id = t.id where t.id = %s",
                    (tenant_id,),
                )
                namn, orgnr, adress, policy = cur.fetchone()
                kunder[tenant_id] = {"slug": slug, "namn": namn, "orgnr": orgnr, "adress": adress, "policy_url": policy}

            fel = False
            for k in kunder.values():
                saknas = saknade_uppgifter(k)
                if saknas:
                    fel = True
                    print(f"  {k['slug']}: kundregistret saknar {', '.join(saknas)} (fyll i under Kunder & Data).")
                elif not str(k.get("policy_url") or "").strip():
                    print(f"  {k['slug']}: VARNING — policy_url saknas; send_guard regel 2 stoppar utskicket igen.")
            if fel:
                print("Inget ändrat.")
                return 1

            andras, hoppas = [], {"utan_utkast": 0, "utan_adress": 0, "har_fot": 0}
            for item_id, tenant_id, slug, msg_id, body, epost in poster:
                if not msg_id:
                    hoppas["utan_utkast"] += 1
                elif not str(epost or "").strip():
                    hoppas["utan_adress"] += 1
                elif fot.har_fot(body or ""):
                    hoppas["har_fot"] += 1
                else:
                    andras.append((item_id, tenant_id, slug, msg_id, body, epost))

            per_kund: dict[str, int] = {}
            for rad in andras:
                per_kund[rad[2]] = per_kund.get(rad[2], 0) + 1
            print(f"Utkast stoppade av regel 1 ({args.env}): {len(poster)}")
            for slug, n in sorted(per_kund.items()):
                print(f"  {slug}: {n} får sidfot och går till granskningskön")
            print(f"Hoppas över: {hoppas['utan_utkast']} utan väntande utkast, "
                  f"{hoppas['utan_adress']} utan mottagaradress, {hoppas['har_fot']} har redan fot.")
            if not args.apply:
                print("Inget ändrat; kör med --apply.")
                return 0

            for item_id, tenant_id, _slug, msg_id, body, epost in andras:
                cur.execute(
                    "insert into ss_avregistreringslankar (token, tenant_id, email) values (%s, %s, %s)"
                    " on conflict (tenant_id, lower(email)) do update set email = excluded.email returning token",
                    (fot.ny_token(), tenant_id, str(epost).strip().casefold()),
                )
                token = cur.fetchone()[0]
                ny = med_fot(body, kund=kunder[tenant_id], lank=fot.avregistreringslank(bas_url, token))
                cur.execute("update outreach_messages set body = %s where id = %s", (ny, msg_id))
                cur.execute(
                    "update send_queue set status = 'awaiting_review', gate_checks = %s::jsonb"
                    " where id = %s and status = 'blocked'",
                    (json.dumps({"till_granskning": "lagg_pa_utskicksfot",
                                 "tidigare_sparr": "1_avsandaridentifikation"}), item_id),
                )
                if cur.rowcount != 1:
                    raise RuntimeError(f"köposten {item_id} ändrades under körningen; rullar tillbaka")
            print(f"{len(andras)} utkast har fått sidfot och ligger i granskningskön i {args.env}.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
