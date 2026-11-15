#!/usr/bin/env python
"""Sätter kundens demolänk och lägger demoraden på utkasten som redan ligger i
utkorgen. Torrkörning som standard.

    python scripts/demolank_i_utkorgen.py --kund snajp                       # visar läget
    python scripts/demolank_i_utkorgen.py --kund snajp --demo /demo          # en länk för alla produkter
    python scripts/demolank_i_utkorgen.py --kund snajp \\
        --demo-produkt "Iris, leadsagenten=/demo/leads" --demo-produkt "Supportagenten=/demo/support"
    python scripts/demolank_i_utkorgen.py --kund snajp --apply               # gör det (development)
    python scripts/demolank_i_utkorgen.py --env main --kund snajp --apply --main-godkand

Antons beställning 2026-11-15: varje mejl i utkorgen ska bära en länk till
demon, "ett snäpp ned från resten av texten", och vi ska se vilka som besökt
den (app/leads/demolank.py, migration 116, docs/BESLUT.md).

Två steg:

1. **Demolänken i kundens inställningar** (`settings.erbjudanden.demo`), om
   --demo eller --demo-produkt anges. En väg som börjar med "/" är en sida på
   plattformens egen webbplats, så samma värde gäller i development och main.
2. **Raden på osända utkast**: varje utkast i kön (väntar på granskning,
   godkänt eller stoppat) som saknar raden får den, med samma kod som
   köningen (`demolank.med_demolank`) och en token per tråd (`ss_demolankar`).
   En naken demoadress i texten ("på snajp.se/demo") blir "via länken nedan",
   så att mejlet inte bär två adresser till samma demo. Status och
   godkännande rörs inte: raden är kodens text, och Godkänn och skicka lägger
   på den på samma sätt (scheduler._fot_vid_godkannande).

Skydd:
- Svar i ett levande samtal (trådar med ett inkommande svar) får ingen rad.
- Kunder utan demolänk rörs inte.
- Ett utkast som redan bär en demolänk får ingen andra.
- Main kräver --main-godkand (produktionsdata, Antons ord gäller).
- Allt i EN transaktion. Inga adresser eller mejltexter skrivs ut.
Lösenord och Railway-token läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
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
    """En modul i app/leads laddad direkt ur filen (bara standardbiblioteket
    på modulnivå), samma mönster som lagg_pa_utskicksfot.py."""
    fil = REPO / "snajp-support" / "app" / "leads" / f"{namn}.py"
    spec = importlib.util.spec_from_file_location(namn, fil)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


demolank = _ladda("demolank")
signatur = _ladda("signatur")

_NAMNGIVEN = re.compile(r"^\s*(?:hej|hejsan|hallå|hi|hello|dear)\s+[A-ZÅÄÖÉ]", re.IGNORECASE)


def produkt_i_text(text: str, produkter: list[str]) -> str | None:
    """Produkten utkastet handlar om: den vars kortnamn står först i texten."""
    lag = text.casefold()
    traffar = sorted(
        (i, p) for p in produkter if (i := lag.find(p.split(",")[0].strip().casefold())) >= 0
    )
    return traffar[0][1] if traffar else None


def med_rad(body: str, *, demo, sig: dict | None, sprak: str, lank: str) -> str:
    """Utkastets text med demoraden; samma steg som demolank.lagg_till."""
    brodtext, _svans = signatur.dela_utkast(body, sig)
    alla = [demo] if isinstance(demo, str) else list(demo.values())
    renad = demolank.utan_bar_demo(brodtext, alla, sprak=sprak)
    text = renad + body[len(brodtext):]
    du = sprak != "en" and bool(_NAMNGIVEN.match(renad.split("\n", 1)[0]))
    return demolank.med_demolank(
        text,
        demolank.rad(lank, sprak=sprak, du=du),
        svans_start=len(renad) if len(renad) < len(text.rstrip()) else None,
    )


#: Osända utkast i kön, ett per tråd (trådens senaste osända text, den
#: sändaren tar), utom trådar där prospektet redan svarat.
UTKAST = """
    select distinct on (m.id) m.id, q.tenant_id, t.slug, th.id, th.language_state, m.body
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
       and th.last_inbound_at is null
       and (%(kund)s::text is null or t.slug = %(kund)s::text)
"""


def satt_demo(cur, *, kund: str, demo, apply: bool):
    """Visar och sätter kundens demolänk. Returnerar den som gäller efteråt."""
    cur.execute(
        "select a.tenant_id, a.settings from agent_configs a join ss_tenants t on t.id = a.tenant_id"
        " where a.agent_type = 'leads' and t.slug = %s",
        (kund,),
    )
    rad = cur.fetchone()
    if not rad:
        sys.exit(f"AVBRYTER: kunden {kund} har ingen leads-agent.")
    tenant_id, settings = rad
    produkter = [str(p.get("namn") or "").strip() for p in (settings or {}).get("produkter") or [] if isinstance(p, dict)]
    print(f"  {kund}: produkter: {', '.join(produkter) or '(inga)'}")
    nu = demolank.normalisera(((settings or {}).get("erbjudanden") or {}).get("demo"))
    print(f"  {kund}: demolänk i dag: {json.dumps(nu, ensure_ascii=False) if nu else '(ingen)'}")
    if demo is None:
        return nu
    nytt = demolank.validera(demo, produkter)
    print(f"  {kund}: demolänk blir: {json.dumps(nytt, ensure_ascii=False)}")
    if apply:
        cur.execute(
            "update agent_configs set settings = jsonb_set(coalesce(settings, '{}'::jsonb),"
            " '{erbjudanden}', coalesce(settings->'erbjudanden', '{}'::jsonb) || %s::jsonb)"
            " where tenant_id = %s and agent_type = 'leads'",
            (json.dumps({"demo": nytt}, ensure_ascii=False), tenant_id),
        )
        if cur.rowcount != 1:
            raise RuntimeError("inställningarna ändrades inte; rullar tillbaka")
    return nytt


def radsteg(cur, *, kund: str | None, apply: bool, bas_url: str, galler: dict | None = None) -> None:
    """`galler`: {slug: demolänk} som går före det sparade (torrkörningen
    med --demo visar utfallet innan något skrivits)."""
    cur.execute(
        "select t.slug, a.settings from agent_configs a join ss_tenants t on t.id = a.tenant_id"
        " where a.agent_type = 'leads' and (%(kund)s::text is null or t.slug = %(kund)s::text)",
        {"kund": kund},
    )
    per_slug = {}
    for slug, settings in cur.fetchall():
        settings = settings or {}
        per_slug[slug] = {
            "demo": demolank.normalisera((settings.get("erbjudanden") or {}).get("demo")),
            "sig": signatur.normalisera(settings.get("signatur")),
        }
        if slug in (galler or {}):
            per_slug[slug]["demo"] = galler[slug]
    cur.execute(UTKAST, {"kund": kund})
    andras: list[tuple[str, str]] = []
    rakning: dict[str, list[int]] = {}
    for msg_id, tenant_id, slug, thread_id, language_state, body in cur.fetchall():
        val = per_slug.get(slug) or {}
        r = rakning.setdefault(slug, [0, 0, 0])  # utkast, har redan, får raden
        r[0] += 1
        demo = val.get("demo")
        if not demo:
            continue
        body = body or ""
        if demolank.har_demolank(body):
            r[1] += 1
            continue
        r[2] += 1
        if not apply:
            continue
        sprak = "en" if language_state == "en_confirmed" else "sv"
        brodtext, _ = signatur.dela_utkast(body, val.get("sig"))
        produkt = produkt_i_text(brodtext, list(demo)) if isinstance(demo, dict) else None
        mal = demolank.demo_for(demo, produkt)
        cur.execute(
            "insert into ss_demolankar (token, tenant_id, thread_id, mal_url) values (%s, %s, %s, %s)"
            " on conflict (tenant_id, thread_id) do update set mal_url = excluded.mal_url returning token",
            (demolank.ny_token(), tenant_id, thread_id, mal),
        )
        token = cur.fetchone()[0]
        ny = med_rad(body, demo=demo, sig=val.get("sig"), sprak=sprak, lank=demolank.lank(bas_url, token))
        if not demolank.har_demolank(ny):
            raise RuntimeError(f"utkastet {msg_id} fick ingen demorad; rullar tillbaka")
        andras.append((msg_id, ny))
    print("Demoraden på osända utkast:")
    for slug, (alla, har, far) in sorted(rakning.items()):
        if not (per_slug.get(slug) or {}).get("demo"):
            print(f"  {slug}: {alla} utkast, ingen demolänk inställd. Rörs inte.")
        else:
            print(f"  {slug}: {alla} utkast, {har} bär redan raden, {far} får den.")
    if not rakning:
        print("  Inga osända utkast.")
    if apply:
        for msg_id, ny in andras:
            cur.execute("update outreach_messages set body = %s where id = %s and sent_at is null", (ny, msg_id))
            if cur.rowcount != 1:
                raise RuntimeError(f"utkastet {msg_id} ändrades under körningen; rullar tillbaka")
        print(f"  {len(andras)} utkast har fått demoraden.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", choices=tuple(MILJO_ID), default="development")
    parser.add_argument("--kund", default=None, help="bara den här kundens slug")
    parser.add_argument("--demo", default=None, help="demolänk för alla produkter (kräver --kund)")
    parser.add_argument("--demo-produkt", action="append", default=[], metavar="PRODUKT=URL",
                        help="demolänk per produkt, kan upprepas (kräver --kund)")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--main-godkand", action="store_true", help="krävs för --apply mot main")
    args = parser.parse_args()
    if args.env == "main" and args.apply and not args.main_godkand:
        sys.exit("AVBRYTER: --apply mot main kräver --main-godkand (Antons uttryckliga ord).")
    demo = None
    if args.demo and args.demo_produkt:
        sys.exit("AVBRYTER: ange --demo eller --demo-produkt, inte båda.")
    if args.demo:
        demo = args.demo
    elif args.demo_produkt:
        demo = dict(par.split("=", 1) for par in args.demo_produkt if "=" in par)
    if demo is not None and not args.kund:
        sys.exit("AVBRYTER: --demo och --demo-produkt kräver --kund.")

    import psycopg2
    from railway_migrate import dsn
    from railway_provision import env_read, read_vars

    variabler = read_vars(API_SERVICE_ID, MILJO_ID[args.env])
    bas_url = (variabler.get("PUBLIK_BAS_URL") or variabler.get("PUBLIC_BASE_URL") or "").strip()
    if not bas_url:
        sys.exit(f"AVBRYTER: PUBLIC_BASE_URL saknas för api i {args.env}; demolänken går inte att bygga.")

    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    try:
        with conn, conn.cursor() as cur:
            print(f"Miljö: {args.env}{'' if args.apply else ' (torrkörning)'}")
            cur.execute("select to_regclass('public.ss_demolankar')")
            if cur.fetchone()[0] is None:
                sys.exit("AVBRYTER: migration 116 är inte körd här (ss_demolankar saknas).")
            if args.kund:
                print("Demolänken i inställningarna:")
                galler = {args.kund: satt_demo(cur, kund=args.kund, demo=demo, apply=args.apply)}
            else:
                galler = None
            radsteg(cur, kund=args.kund, apply=args.apply, bas_url=bas_url, galler=galler)
            if not args.apply:
                print("Inget ändrat; kör med --apply.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
