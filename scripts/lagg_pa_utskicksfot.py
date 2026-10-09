#!/usr/bin/env python
"""Lägger på signaturen och den lagstadgade sidfoten på utkast som saknar dem,
och lägger regel 1-stoppade utkast tillbaka i granskningskön. Torrkörning som
standard.

    python scripts/lagg_pa_utskicksfot.py                      # visar vad som skulle göras
    python scripts/lagg_pa_utskicksfot.py --kund snajp         # en kund
    python scripts/lagg_pa_utskicksfot.py --apply              # gör det (development)
    python scripts/lagg_pa_utskicksfot.py --env main --apply --main-godkand

Två steg, i den här ordningen:

1. **Signaturen** (Sebbe 2026-10-09: "utkasten och alla mail måste ha
   signaturen"). Signaturen läggs på av kod vid köningen (app/leads/signatur.py),
   men bara om tenanten hade den satt då. Utkast köade innan saknar blocket. Varje
   osänt utkast i kön (väntar på granskning, godkänt eller stoppat) som saknar det
   får det, före en eventuell fot, med samma kod som köningen
   (`signatur.med_signatur_fore_fot`). Status och godkännande rörs inte: blocket
   är kodens text, inte en ändring av det granskaren sagt ja till, och
   Godkänn och skicka lägger på det på samma sätt (scheduler._fot_vid_godkannande).
   Det här steget kräver inget ur kundregistret.

2. **Foten** (2026-10-08): foten (org.nr, postadress, ändamål, avregistreringslänk)
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
- Foten: bara poster med status 'blocked' och send_guard_regel
  '1_avsandaridentifikation'. Spärrar som 'ej_styrkt' och 'testkorning' rörs aldrig.
- Kundens org.nr och företagsadress måste finnas i kundregistret (Kunder &
  Data); saknas de hoppas den kundens fotsteg över med besked om vad som
  saknas (signatursteget görs ändå). Saknad policy_url varnas för (regel 2
  hade stoppat utskicket igen).
- Ett utkast som redan bär signaturen eller en fot får ingen andra.
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


def _ladda(namn: str):
    """En modul i app/leads laddad direkt ur filen: utskicksfot.py och
    signatur.py beror bara på standardbiblioteket, medan paketet app drar in
    hela backendens beroenden."""
    fil = REPO / "snajp-support" / "app" / "leads" / f"{namn}.py"
    spec = importlib.util.spec_from_file_location(namn, fil)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


fot = _ladda("utskicksfot")
signatur = _ladda("signatur")


def saknade_uppgifter(kund: dict) -> list[str]:
    """Det som saknas för att foten ska klara regel 1."""
    return [
        etikett
        for etikett, nyckel in (("företagsnamn", "namn"), ("organisationsnummer", "orgnr"), ("företagsadress", "adress"))
        if not str(kund.get(nyckel) or "").strip()
    ]


def med_signatur(brodtext: str, *, sig: dict | None, sprak: str) -> str:
    """Brödtexten med signaturen före en eventuell fot; oförändrad om
    signaturen saknas i inställningarna eller redan finns i texten."""
    if not sig:
        return brodtext
    return signatur.med_signatur_fore_fot(brodtext, sig, halsning=signatur.HALSNING[sprak])


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


#: Osända utkast i kön, ett per köpost (trådens senaste osända text — den
#: sändaren tar).
UTKAST = """
    select distinct on (m.id) m.id, t.slug, th.language_state, m.body
      from send_queue q
      join ss_tenants t on t.id = q.tenant_id
      join outreach_threads th on th.id = q.thread_id
      join lateral (
        select id, body from outreach_messages
         where tenant_id = q.tenant_id and thread_id = q.thread_id and direction = 'outbound'
           and sent_at is null and kasserad_at is null
         order by created_at desc, id desc limit 1
      ) m on true
     where q.status in ('awaiting_review', 'queued', 'blocked')
       and (%(kund)s::text is null or t.slug = %(kund)s::text)
"""

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


def signatursteg(cur, *, kund: str | None, apply: bool) -> None:
    """Steg 1: signaturen på varje osänt utkast som saknar den."""
    cur.execute(
        "select t.slug, a.settings->'signatur' from agent_configs a join ss_tenants t on t.id = a.tenant_id"
        " where a.agent_type = 'leads' and (%(kund)s::text is null or t.slug = %(kund)s::text)",
        {"kund": kund},
    )
    signaturer = {slug: signatur.normalisera(varde) for slug, varde in cur.fetchall()}
    cur.execute(UTKAST, {"kund": kund})
    andras: list[tuple[str, str]] = []
    per_kund: dict[str, list[int]] = {}
    for msg_id, slug, language_state, body in cur.fetchall():
        rakning = per_kund.setdefault(slug, [0, 0])
        rakning[0] += 1
        sprak = "en" if language_state == "en_confirmed" else "sv"
        ny = med_signatur(body or "", sig=signaturer.get(slug), sprak=sprak)
        if ny != (body or ""):
            rakning[1] += 1
            andras.append((msg_id, ny))
    print("Steg 1, signaturen:")
    for slug, (alla, saknar) in sorted(per_kund.items()):
        if not signaturer.get(slug):
            print(f"  {slug}: {alla} utkast, ingen signatur inställd (Inställningar › Signatur).")
        else:
            print(f"  {slug}: {alla} utkast, {saknar} saknar signaturen och får den.")
    if not per_kund:
        print("  Inga osända utkast.")
    if apply:
        for msg_id, ny in andras:
            cur.execute("update outreach_messages set body = %s where id = %s and sent_at is null", (ny, msg_id))
        if andras:
            print(f"  {len(andras)} utkast har fått signaturen.")


def fotsteg(cur, *, kund: str | None, apply: bool, bas_url: str) -> int:
    """Steg 2: foten på regel 1-stoppade utkast, och tillbaka till granskning."""
    print("Steg 2, sidfoten:")
    cur.execute(URVAL, {"kund": kund})
    poster = cur.fetchall()
    if not poster:
        print("  Inga utkast stoppade av regel 1.")
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

    ofullstandiga: set[str] = set()
    for tenant_id, k in kunder.items():
        saknas = saknade_uppgifter(k)
        if saknas:
            ofullstandiga.add(tenant_id)
            print(f"  {k['slug']}: kundregistret saknar {', '.join(saknas)} (fyll i under Kunder & Data). Hoppas över.")
        elif not str(k.get("policy_url") or "").strip():
            print(f"  {k['slug']}: VARNING — policy_url saknas; send_guard regel 2 stoppar utskicket igen.")

    andras, hoppas = [], {"utan_utkast": 0, "utan_adress": 0, "har_fot": 0, "ofullstandig_kund": 0}
    for item_id, tenant_id, slug, msg_id, body, epost in poster:
        if tenant_id in ofullstandiga:
            hoppas["ofullstandig_kund"] += 1
        elif not msg_id:
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
    print(f"  Utkast stoppade av regel 1: {len(poster)}")
    for slug, n in sorted(per_kund.items()):
        print(f"  {slug}: {n} får sidfot och går till granskningskön")
    print(f"  Hoppas över: {hoppas['ofullstandig_kund']} hos kunder utan org.nr/adress, "
          f"{hoppas['utan_utkast']} utan väntande utkast, "
          f"{hoppas['utan_adress']} utan mottagaradress, {hoppas['har_fot']} har redan fot.")
    if not apply:
        return 1 if ofullstandiga else 0

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
    if andras:
        print(f"  {len(andras)} utkast har fått sidfot och ligger i granskningskön.")
    return 1 if ofullstandiga else 0


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
            print(f"Miljö: {args.env}{'' if args.apply else ' (torrkörning)'}")
            signatursteg(cur, kund=args.kund, apply=args.apply)
            kod = fotsteg(cur, kund=args.kund, apply=args.apply, bas_url=bas_url)
            if not args.apply:
                print("Inget ändrat; kör med --apply.")
    finally:
        conn.close()
    return kod


if __name__ == "__main__":
    raise SystemExit(main())
