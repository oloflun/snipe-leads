#!/usr/bin/env python3
"""Skapar Snajp AB:s EGET kundkonto i en Railway-miljö — som vilken kund som helst.

    python scripts/skapa_snajp_intern_kund.py --env development           # visa planen
    python scripts/skapa_snajp_intern_kund.py --env development --apply

## Varför skriptet finns

Snajp ska vara sin egen första leads-kund: Iris letar kunder åt oss själva.
Det ger både en riktig prospektlista och ett levande produktionstest av
exakt den väg en betalande kund går. Därför gör skriptet INGENTING som en
vanlig kund inte får:

  1. Konto i `auth.users` (scrypt-hash, samma format som lib/password.ts),
     workspace + profil via samma trigger/läkväg som signupflödet
     (`ensure_workspace_for_current_user`).
  2. `business_contexts` — onboardingflaggan, precis som onboardingformuläret.
  3. Backend-tenant via `POST /api/keys` med slugmönstret `kund-<8 ur
     workspace-id>` och koppling via `public.link_workspace_tenant`
     (migration 061) — ordagrant vad lib/snajp/provisionering.ts gör.
  4. Produktbeskrivning och ICP via samma API kunden själv använder
     (`POST /api/leads/context-docs`, `PUT /api/leads/config`).

OBS: sluggen `snajp` används INTE — den är adminarbetsytans och att dela den
gav identiskt Snajp-innehåll i två kundbesök i produktion 2026-09-02 (se
lib/actions/affarskontext.ts). Det här kontot är en HELT egen tenant.

## Läckagespärr

Lösenord och API-nyckel skrivs till `.env.deploy` (gitignorerad) som
`RAILWAY_<ENV>_SNAJP_INTERN_LOSEN` respektive `RAILWAY_<ENV>_KEY_<SLUG>`
och ekas ALDRIG i terminalen — bara namn och längd skrivs ut.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read, env_set  # noqa: E402

EPOST = "intern@snajp.se"
NAMN = "Snajp Intern"
ARBETSYTA = "Snajp AB"

# Affärskontexten — samma fyra fält som onboardingformuläret skriver.
# Organisationsnumret utelämnas med flit: Snajps riktiga orgnr är inte
# registrerat i repot (lib/bolag.ts bär platshållare, se P0.3b i
# docs/JURIDIK_ATGARDER.md) och ett gissat nummer kan tillhöra ett annat bolag.
PRODUKT = (
    "Snajp säljer AI-medarbetare till svenska företag: en kundtjänstagent som "
    "svarar kundmejl och chatt grundat enbart i företagets egen kunskapsbas och "
    "eskalerar till människa i stället för att gissa, en leads-agent (Iris) som "
    "hittar rätt företag och skriver personliga första mejl (aldrig massutskick), "
    "och en bokföringsagent (Kvittohanteraren) som läser kvitton och fakturor och "
    "föreslår kontering enligt BAS-kontoplanen med SIE4-export."
)
MALGRUPP = (
    "Svenska utbildningsföretag inom hälsa och säkerhet: HLR, första hjälpen, "
    "brandskydd, heta arbeten och arbetsmiljöutbildning, online och på plats. "
    "10–250 anställda, eller mindre bolag med hög kursvolym. Kännetecken: "
    "bokningskalender eller kursanmälan på webbplatsen, FAQ om intyg och "
    "certifikat, flera kursorter eller instruktörer, synlig kundtjänstkontakt."
)
ERBJUDANDE = (
    "Tre AI-agenter som avlastar kursadministrationen: supportagenten svarar på "
    "återkommande frågor om bokningar, intyg och ombokningar dygnet runt, Iris "
    "hittar nya företagskunder till kurserna, och Kvittohanteraren sköter "
    "kvittona. Svenska först, grundat i företagets eget material, människa i "
    "loopen före varje utskick."
)
NASTA_STEG = "Boka en kort demo på 20 minuter."

# Iris ICP — beställningen 2026-09-20, mappad på schemat i app/leads/icp.py.
# `industries[:2]` styr JobTech-sökorden (se app/leads/sources/jobtech.py),
# därför ligger de två bästa söktermerna först. `size` sätts 1–250 eftersom
# beställningen uttryckligen inkluderar "mindre bolag med hög kursvolym" —
# huvudspannet 10–250 och undantaget bär signallistan i stället, så att ett
# litet bolag med hög volym inte fälls av ett hårt storleksfilter.
ICP = {
    "industries": [
        "HLR-utbildning",
        "brandskyddsutbildning",
        "första hjälpen-utbildning",
        "heta arbeten-certifiering",
        "arbetsmiljöutbildning",
        "utbildningsföretag inom hälsa och säkerhet",
    ],
    "geography": ["Sverige"],
    "roles": ["VD", "Utbildningsansvarig", "Kursadministratör", "Kundtjänstansvarig"],
    "must_have": [
        "Bokningskalender eller kursanmälan på webbplatsen",
        "FAQ om intyg eller certifikat",
        "Flera kursorter eller instruktörer",
        "Synlig kundtjänstkontakt",
        "Under 10 anställda kvalificerar bara vid hög kursvolym",
    ],
    "deal_breakers": [
        "Använder redan Zendesk, Intercom, Freshdesk eller liknande synligt på webbplatsen",
    ],
    "exclude_domains": ["snajp.se"],
    "size": {"anstallda_min": 1, "anstallda_max": 250},
    "company_size": {"min": 1, "max": 250},
    "max_prospects_per_run": 25,
}

KEYLEN = 64


def hasha(losenord: str) -> str:
    """`scrypt$1$<salt>$<hash>` — bitidentiskt med lib/password.ts (se skapa_qa_kund.py)."""
    salt = os.urandom(16)
    nyckel = hashlib.scrypt(
        losenord.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=KEYLEN, maxmem=64 * 1024 * 1024
    )
    return (
        "scrypt$1$"
        + base64.b64encode(salt).decode("ascii")
        + "$"
        + base64.b64encode(nyckel).decode("ascii")
    )


def kund_slug(workspace_id: str) -> str:
    """`kund-<8>` — samma regel som kundtenantSlug() i lib/snajp/testtenant.ts."""
    rent = "".join(c for c in workspace_id if c.isalnum()).lower()
    return f"kund-{rent[:8]}"


def api_anrop(url: str, nyckel: str, metod: str = "GET", kropp: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(kropp).encode() if kropp is not None else None,
        headers={"Content-Type": "application/json", "X-API-Key": nyckel},
        method=metod,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as svar:
            return json.load(svar)
    except urllib.error.HTTPError as fel:
        # Läs detaljen men eka aldrig hela kroppen — den kan spegla förfrågan.
        try:
            detalj = json.load(fel).get("detail", "")
        except Exception:  # noqa: BLE001
            detalj = ""
        sys.exit(f"AVBRYTER: {metod} {url.split('/api/')[-1]} svarade {fel.code}: {detalj}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="kör (annars visas bara planen)")
    ap.add_argument("--env", choices=("main", "development"), default="development")
    ap.add_argument("--jag-menar-produktion", action="store_true")
    args = ap.parse_args()

    if args.env == "main" and not args.jag_menar_produktion:
        sys.exit("Vägrar mot main utan --jag-menar-produktion.")

    store = env_read()
    prefix = f"RAILWAY_{args.env.upper()}"
    api_url = store.get(f"{prefix}_API_URL", "").rstrip("/")
    master = store.get(f"{prefix}_MASTER_API_KEY")
    if not api_url or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL / {prefix}_MASTER_API_KEY saknas i .env.deploy.")

    conn = psycopg2.connect(dsn(store, args.env), connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("select id from auth.users where lower(email) = lower(%s)", (EPOST,))
    rad = cur.fetchone()
    finns = rad is not None

    print(f"miljö: {args.env}")
    print(f"konto: {EPOST} — {'FINNS redan' if finns else 'saknas'}")

    if not args.apply:
        print("\nSkulle skapa konto, workspace 'Snajp AB', affärskontext, backend-tenant")
        print("(kund-<8>), produktbeskrivning och ICP. Kör med --apply.")
        return 0

    # 1. Konto + workspace + profil — samma väg som signupflödet.
    if not finns:
        losen = secrets.token_urlsafe(18)
        cur.execute(
            """insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at)
               values (%s, %s, jsonb_build_object('full_name', %s::text), now())
               returning id""",
            (EPOST, hasha(losen), NAMN),
        )
        anvandare = cur.fetchone()[0]
        env_set(f"{prefix}_SNAJP_INTERN_LOSEN", losen)
        print(f"  + auth.users skapad; lösenordet sparat som {prefix}_SNAJP_INTERN_LOSEN i .env.deploy")
    else:
        anvandare = rad[0]

    cur.execute("select workspace_id from public.profiles where id = %s", (anvandare,))
    prad = cur.fetchone()
    if prad is None:
        cur.execute("select set_config('app.user_id', %s, true)", (str(anvandare),))
        cur.execute("select public.ensure_workspace_for_current_user()")
        cur.execute("select workspace_id from public.profiles where id = %s", (anvandare,))
        prad = cur.fetchone()
        print("  + profil/workspace läkt")
    if prad is None:
        conn.rollback()
        sys.exit("Kontot fick ingen profil. Migration 001/006 är inte körd i den här miljön.")
    arbetsyta = str(prad[0])

    cur.execute(
        "update public.workspaces set name = %s where id = %s and name <> %s",
        (ARBETSYTA, arbetsyta, ARBETSYTA),
    )
    if cur.rowcount:
        print(f"  + arbetsytan döpt till '{ARBETSYTA}'")

    # Alla tre agenterna — kontot är även ett levande produktionstest.
    cur.execute(
        """update public.workspaces set products = array['leads','support','bookkeeping']
           where id = %s and products <> array['leads','support','bookkeeping']""",
        (arbetsyta,),
    )
    if cur.rowcount:
        print("  + products = leads, support, bookkeeping")

    # 2. Affärskontexten = onboardingflaggan.
    cur.execute("select 1 from public.business_contexts where workspace_id = %s", (arbetsyta,))
    if cur.fetchone() is None:
        cur.execute(
            """insert into public.business_contexts
                   (workspace_id, product, target_audience, industries, geography,
                    tone, offer, cta, contact_roles, updated_at)
               values (%s, %s, %s, '{}', '{}', %s, %s, %s, '{}', now())""",
            (arbetsyta, PRODUKT, MALGRUPP, "Lågmäld, specifik, inga superlativ.", ERBJUDANDE, NASTA_STEG),
        )
        print("  + affärskontext skapad (kontot räknas nu som onboardat)")
    else:
        print("  = affärskontext fanns redan")

    conn.commit()

    # 3. Backend-tenant + nyckel — ordagrant provisioneringens väg.
    slug = kund_slug(arbetsyta)
    print(f"  tenant-slug: {slug}")
    kropp = api_anrop(f"{api_url}/api/keys", master, "POST", {"tenant_name": ARBETSYTA, "slug": slug})
    nyckel, tenant_id = kropp.get("api_key"), kropp.get("tenant_id")
    if not nyckel or not tenant_id:
        sys.exit(f"AVBRYTER: /api/keys gav inget nyckelfält. Svarsnycklar: {sorted(kropp)}")
    print(f"  + nyckel utfärdad ({len(nyckel)} tecken) för tenant {tenant_id}")

    cur.execute("select slug from public.workspaces where id = %s", (arbetsyta,))
    if cur.fetchone()[0] is None:
        cur.execute("select set_config('app.user_id', %s, true)", (str(anvandare),))
        cur.execute(
            "select public.link_workspace_tenant(%s, %s, %s)", (slug, tenant_id, nyckel)
        )
        kopplad = cur.fetchone()[0]
        conn.commit()
        if not kopplad:
            sys.exit("AVBRYTER: link_workspace_tenant nekade kopplingen.")
        print("  + arbetsytan kopplad till tenanten (link_workspace_tenant)")
    else:
        print("  = arbetsytan bar redan en slug — kopplingen rörs inte")

    env_set(f"{prefix}_KEY_{slug.upper().replace('-', '_')}", nyckel)
    print(f"  + nyckeln sparad som {prefix}_KEY_{slug.upper().replace('-', '_')} i .env.deploy")

    # 4. Produktbeskrivning + ICP via kundens eget API.
    api_anrop(
        f"{api_url}/api/leads/context-docs",
        nyckel,
        "POST",
        {"kind": "product_marketing", "content": PRODUKT + "\n\n" + ERBJUDANDE, "source": "snajp-intern-uppsattning"},
    )
    print("  + product_marketing skriven")

    api_anrop(f"{api_url}/api/leads/config", nyckel, "PUT", {"icp": ICP})
    tillbaka = api_anrop(f"{api_url}/api/leads/config", nyckel)
    sparat = tillbaka.get("icp", {})
    diff = [f for f in ("industries", "geography", "roles", "must_have", "deal_breakers") if sparat.get(f) != ICP[f]]
    if diff:
        sys.exit(f"AVBRYTER: ICP-rundturen skiljer sig i fälten: {diff}")
    print("  + ICP sparad och verifierad med GET-rundtur")

    print("\nKlart. Starta en körning med:")
    print(f"  POST {api_url}/api/leads/runs/batch  (X-API-Key ur {prefix}_KEY_{slug.upper().replace('-', '_')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
