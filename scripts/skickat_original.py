#!/usr/bin/env python3
"""Byt textkopiorna i kundens Skickat mot utskicken som de faktiskt gick ut.

    python scripts/skickat_original.py --slug snajp --env main --jag-menar-produktion
    python scripts/skickat_original.py --slug snajp --env main --jag-menar-produktion --apply

## Varför skriptet finns

Fram till 2026-11-23 la sändvägen en kopia i kundens Skickat som var ren text
från adressen utan namn, också när mottagaren fick HTML-delen med signaturen
och logotypen. Kopian visade alltså något annat än det som gick ut (Anton
2026-11-23: "Byt ut mailen i skickat"). Nya utskick får rätt kopia direkt
(`app/email_pipeline/skickatkopia.py`); det här skriptet rättar de gamla.

Mejltjänsten sparar varje utskick som det gick ut. För varje utskick som
tillhör kunden (mottagare och ämne matchar ett skickat meddelande i kundens
kö) och som gick med HTML-del:

  1. originalet läggs i Skickat med sändtiden och avsändarnamnet,
  2. först när det ligger där flyttas den gamla textkopian till papperskorgen.

Ingenting raderas: papperskorgen behåller kopian i 30 dagar hos Gmail. Hittas
inte exakt en gammal kopia läggs originalet dit ändå och den gamla rörs inte.
En omkörning gör ingenting: originalen bär ett eget Message-ID som söks först.

Originalet är det som gick ut. Ett utskick som gick med en äldre signatur
visas med den; skriptet skriver aldrig om ett mejl.

## Hemligheter

Mejltjänstens nyckel, krypteringsnyckeln för brevlådans lösenord och
databasadressen läses i processen ur Railway och `.env.deploy`. Inget av dem
skrivs ut, och inga mottagaradresser eller mejltexter skrivs ut heller.
"""
from __future__ import annotations

import argparse
import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROT / "snajp-support"))

from railway_provision import env_read  # noqa: E402

#: Så långt får en gammal kopias tid ligga från utskickets för att räknas som
#: samma mejl. Kopian lades direkt efter sändningen.
TIDSGLAPP = timedelta(minutes=20)
RESEND = "https://api.resend.com/emails"


def resend_hamta(url: str, nyckel: str) -> dict:
    for forsok in range(6):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {nyckel}", "User-Agent": "snajp-skickat/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as svar:
                return json.load(svar)
        except urllib.error.HTTPError as fel:
            if fel.code != 429 or forsok == 5:
                raise
            time.sleep(1.5 * (forsok + 1))
    raise RuntimeError("oåtkomligt")


def resend_lista(nyckel: str, sedan: str) -> list[dict]:
    alla: list[dict] = []
    efter = None
    while True:
        svar = resend_hamta(f"{RESEND}?limit=100" + (f"&after={efter}" if efter else ""), nyckel)
        data = svar.get("data") or []
        alla += [r for r in data if str(r.get("created_at"))[:10] >= sedan]
        if not data or not svar.get("has_more") or str(data[-1].get("created_at"))[:10] < sedan:
            return alla
        efter = data[-1]["id"]
        time.sleep(0.5)


def tid(varde: str) -> datetime:
    """Mejltjänstens tid ("2026-11-23 08:37:25.123456+00") som datetime i UTC."""
    text = str(varde).strip().replace(" ", "T", 1)
    text = re.sub(r"([+-]\d\d)$", r"\1:00", text)
    t = datetime.fromisoformat(text)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def avkoda(rubrik: str | None) -> str:
    return str(email.header.make_header(email.header.decode_header(rubrik or ""))).strip()


def norm(amne: str) -> str:
    return " ".join((amne or "").split()).lower()


def eget_id(resend_id: str) -> str:
    return f"<utskick-{resend_id}@kopia.snajp.se>"


def gamla_kopior(klient, till: str, amne: str, nar: datetime) -> list[bytes]:
    """UID för textkopior i den valda mappen som är samma utskick: samma
    mottagare och ämne, ren text, tiden inom TIDSGLAPP, och inte ett original
    som skriptet själv lagt dit."""
    fran = (nar - timedelta(days=1)).strftime("%d-%b-%Y")
    till_dag = (nar + timedelta(days=2)).strftime("%d-%b-%Y")
    typ, data = klient.uid("search", None, "TO", f'"{till}"', "SINCE", fran, "BEFORE", till_dag)
    if typ != "OK":
        return []
    traffar: list[bytes] = []
    for uid in (data[0] or b"").split():
        typ, svar = klient.uid(
            "fetch", uid, "(INTERNALDATE BODY.PEEK[HEADER.FIELDS (SUBJECT CONTENT-TYPE MESSAGE-ID)])"
        )
        if typ != "OK" or not svar or not isinstance(svar[0], tuple):
            continue
        huvud = email.message_from_bytes(svar[0][1])
        if "@kopia.snajp.se>" in (huvud.get("Message-ID") or ""):
            continue
        if (huvud.get_content_type() or "") != "text/plain":
            continue
        if norm(avkoda(huvud.get("Subject"))) != norm(amne):
            continue
        intern = imaplib.Internaldate2tuple(svar[0][0])
        if intern is None:
            continue
        lagd = datetime.fromtimestamp(time.mktime(intern), tz=timezone.utc)
        if abs(lagd - nar) <= TIDSGLAPP:
            traffar.append(uid)
    return traffar


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--jag-menar-produktion", action="store_true")
    ap.add_argument("--sedan", default="2026-10-24", help="äldsta dag att gå igenom (ÅÅÅÅ-MM-DD)")
    ap.add_argument("--apply", action="store_true", help="lägg dit originalen och flytta textkopiorna")
    args = ap.parse_args()
    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    import psycopg2

    from railway_env_bootstrap import service_vars
    from railway_migrate import dsn
    from railway_provision import envs_by_name, services_by_name, state

    projekt = state()
    api_vars = service_vars(services_by_name(projekt)["api"]["id"], envs_by_name(projekt)[args.env])
    nyckel = api_vars.get("RESEND_API_KEY")
    if not nyckel:
        sys.exit("AVBRYTER: RESEND_API_KEY saknas på api.")
    # Brevlådans lösenord låses upp med samma nyckel som appen använder.
    os.environ["INTEGRATION_NYCKEL"] = api_vars.get("INTEGRATION_NYCKEL", "")

    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("select id::text from public.ss_tenants where slug = %s", (args.slug,))
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYTER: ingen tenant med sluggen {args.slug!r} i {args.env}.")
    tenant_id = rad[0]
    cur.execute(
        """select lower(p.contact_email), m.subject
             from public.outreach_messages m
             join public.outreach_threads t on t.id = m.thread_id
             join public.prospects p on p.id = t.prospect_id
            where m.tenant_id = %s and m.direction = 'outbound' and m.sent_at is not null
              and p.contact_email is not null""",
        (tenant_id,),
    )
    kundens = {(adress, norm(amne)) for adress, amne in cur.fetchall()}
    cur.execute(
        """select provider, address, imap_host, status, syfte, secret_enc
             from public.ss_mailboxes where tenant_id = %s order by created_at""",
        (tenant_id,),
    )
    brevlador = [
        dict(zip(("provider", "address", "imap_host", "status", "syfte", "secret_enc"), r)) for r in cur.fetchall()
    ]
    conn.close()

    from app.email_pipeline.connectors.imap import _skickat_meddelande, mapp_med_attribut
    from app.email_pipeline.poller import host_for_mailbox, losenord_for

    # Samma val som skickatkopia.kopiera_till_skickat gör för leadsutskick.
    rang = {"leads": 0, "bada": 1}
    brevlada = losen = host = None
    for b in sorted(brevlador, key=lambda m: rang.get(m.get("syfte") or "support", 2)):
        if b.get("status") != "active" or b.get("provider") == "mock":
            continue
        host, losen = host_for_mailbox(b), losenord_for(b, args.slug)
        if host and losen:
            brevlada = b
            break
    if not brevlada:
        sys.exit("AVBRYTER: ingen aktiv brevlåda med läsbart lösenord för kunden.")

    listade = resend_lista(nyckel, args.sedan)
    print(f"miljö: {args.env}  tenant: {args.slug}  brevlåda: {brevlada['address']}")
    print(f"mejltjänsten: {len(listade)} utskick sedan {args.sedan} (alla kunder)")

    klient = imaplib.IMAP4_SSL(host, timeout=60)
    utfall: Counter[str] = Counter()
    try:
        klient.login(brevlada["address"], losen)
        skickat = mapp_med_attribut(klient, b"\\sent")
        papperskorg = mapp_med_attribut(klient, b"\\trash")
        if not skickat or not papperskorg:
            sys.exit("AVBRYTER: hittar inte Skickat eller papperskorgen i brevlådan.")
        typ, _ = klient.select(f'"{skickat}"', readonly=not args.apply)
        if typ != "OK":
            sys.exit("AVBRYTER: Skickat gick inte att öppna.")
        kan_flytta = "MOVE" in {str(c).upper() for c in klient.capabilities}

        for post in listade:
            mottagare = [str(a).strip().lower() for a in (post.get("to") or [])]
            amne = post.get("subject") or ""
            if len(mottagare) != 1 or (mottagare[0], norm(amne)) not in kundens:
                utfall["hör inte till kundens utskick"] += 1
                continue
            till = mottagare[0]
            mejl = resend_hamta(f"{RESEND}/{post['id']}", nyckel)
            time.sleep(0.5)
            if not mejl.get("html"):
                utfall["gick som ren text, kopian stämmer redan"] += 1
                continue
            nar = tid(post["created_at"])
            mid = eget_id(post["id"])
            typ, data = klient.uid("search", None, "HEADER", "Message-ID", f'"{mid}"')
            redan = typ == "OK" and bool((data[0] or b"").split())
            gamla = gamla_kopior(klient, till, amne, nar)
            if not args.apply:
                utfall[
                    "redan utbytt" if redan and not gamla
                    else f"skulle bytas (gamla kopior: {len(gamla)})"
                ] += 1
                continue
            if not redan:
                namn, adress = email.utils.parseaddr(mejl.get("from") or "")
                original = _skickat_meddelande(
                    fran=adress or brevlada["address"], till=till, amne=amne,
                    brodtext=mejl.get("text") or "", html=mejl["html"], fran_namn=namn,
                    datum=nar, message_id=mid,
                )
                typ, _ = klient.append(
                    f'"{skickat}"', "\\Seen", imaplib.Time2Internaldate(nar.timestamp()), original.as_bytes()
                )
                if typ != "OK":
                    utfall["originalet gick inte att lägga dit, gamla kopian orörd"] += 1
                    continue
            if len(gamla) != 1:
                utfall[f"original på plats, gamla kopian orörd ({len(gamla)} träffar)"] += 1
                continue
            if kan_flytta:
                typ, _ = klient.uid("MOVE", gamla[0], f'"{papperskorg}"')
            else:
                typ, _ = klient.uid("COPY", gamla[0], f'"{papperskorg}"')
                if typ == "OK":
                    klient.uid("STORE", gamla[0], "+FLAGS", "(\\Deleted)")
                    klient.expunge()
            utfall["utbytt" if typ == "OK" else "original på plats, flytten av gamla kopian nekades"] += 1
    finally:
        try:
            klient.logout()
        except Exception:  # noqa: BLE001
            pass

    print("TORRKÖRNING: inget ändrat i brevlådan." if not args.apply else "KLART.")
    for vad, antal in utfall.most_common():
        print(f"  {antal:5d}  {vad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
