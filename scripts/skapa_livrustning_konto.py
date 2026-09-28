#!/usr/bin/env python3
"""Ger Livrustning-piloten ett inloggningsbart konto med alla tre agenterna gratis.

    python scripts/skapa_livrustning_konto.py --env development           # visa planen
    python scripts/skapa_livrustning_konto.py --env development --apply

## Varför skriptet finns

Livrustning provisionerades 2026-09-19 som PUBLIK tenant (widget, KB, mejl) men
fick aldrig någon inloggningsväg: arbetsytan "Livrustning AB" (slug
`livrustning`) stod utan konto, utan profil och utan `business_contexts`, så
det gick inte att logga in och se det kunden ser. Beställningen 2026-09-20 är
att piloten ska ha ALLA TRE agenterna gratis och gå att köra inloggad.

Vad skriptet gör, idempotent och i onboardingens egna banor:

  1. `workspaces.products = leads, support, bookkeeping` — pilotens gratispaket.
  2. `workspaces.trial_slut` flyttas till pilotens slutdatum, så att
     trial-påminnarna (migration 074) inte mejlar kunden mitt i piloten.
  3. En `workspace_invites`-rad (roll owner) för kontoadressen — invite-only är
     enda sanktionerade vägen in i en befintlig arbetsyta (se AUTH.md), och
     triggern `on_auth_user_created` läser den vid kontoskapandet.
  4. Kontot i `auth.users` (scrypt, bitidentiskt med lib/password.ts).
     Lösenordet genereras och sparas i `.env.deploy` som
     `RAILWAY_<ENV>_LIVRUSTNING_LOSEN` — ekas ALDRIG.
  5. `business_contexts` ur samma underlag som
     snajp-support/app/tenants/livrustning_business_context.py, så att
     inloggningen landar på /dashboard i stället för i onboardingwizarden.
     Wizarden hade skrivit om `products` till ett PAKET — pilotens tre agenter
     ska inte kunna nedgraderas av ett välmenande klick.

Vad skriptet INTE gör: ingen nyckelrad i `workspace_tenant_keys`. Livrustning
har configfil (lib/tenants/livrustning.ts) och `requireSnajpTenant()` löser då
nyckeln ur miljövariabeln `SNAJP_KEY_LIVRUSTNING` — samma nyckel som den
publika chatten redan kör med. Avtalsgrinden rörs inte heller: datumet
registrerades i Kunder & Data 2026-09-20 och grinden är öppen.

## Läckagespärr

Lösenordet skrivs till `.env.deploy` (gitignorerad) och ekas aldrig — bara
variabelnamnet och längden skrivs ut.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import os
import secrets
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read, env_set  # noqa: E402

EPOST = "kontakt@livrustning.se"
NAMN = "Livrustning"
SLUG = "livrustning"
PRODUKTER = ["leads", "support", "bookkeeping"]

#: Pilotens gratisperiod. Ett datum och inte "aldrig": trialmodellen (074) ÄR
#: ett datum, och en pilot utan slutdatum är en pilot ingen utvärderar.
TRIAL_SLUT = dt.date(2026, 12, 31)

# Samma underlag som livrustning_business_context.py, kokat till
# business_contexts fyra fält. Branschraden följer onboardingwizardens form
# (lib/bransch.ts): kundens EGEN bransch som text, aldrig i `industries`.
PRODUKT = (
    "Bransch: Utbildning\n"
    "Organisationsnummer: 556824-9022\n\n"
    "Livrustning AB utbildar i HLR, första hjälpen och brand. Instruktörerna "
    "kommer till kundens arbetsplats på ett datum kunden väljer. Fyra upplägg: "
    "Säkerhetsdag (4 timmar, brand, HLR och första hjälpen i fyra stationer), "
    "eHLR-Event (2 timmar, hela personalen i HLR med hjärtstartare, personligt "
    "intyg till alla), eHLR och eFörstaHjälpen (digitalt lärande plus praktisk "
    "träning, ett års access) och klassiska kurser i små grupper. Priset sätts "
    "per offert. De hjälper också arbetsplatser att bli en Hjärtsäker zon "
    "enligt SS 280000. Livrustning säljer inte hjärtstartare."
)
MALGRUPP = (
    "Arbetsplatser som vill att hela personalen ska kunna rädda liv — gärna "
    "som programpunkt på en kick-off eller planeringsdag. De digitala kurserna "
    "passar verksamheter där alla inte kan vara på samma plats samtidigt. Bas "
    "i Stockholm, Umeå och Nerja i Spanien; utbildning över hela Sverige."
)
ERBJUDANDE = (
    "Över 30 års erfarenhet och cirka 2 000 utbildade deltagare per år. "
    "Rekommenderade på Reco.se fem år i rad. 100 % nöjdhetsgaranti. Allt "
    "kursinnehåll följer Svenska HLR-rådets riktlinjer. Hela personalen "
    "utbildas på en gång, samma dag."
)
NASTA_STEG = "Be om en offert utifrån antal deltagare, utbildning och ort."

KEYLEN = 64


def hasha(losenord: str) -> str:
    """`scrypt$1$<salt>$<hash>` — bitidentiskt med lib/password.ts."""
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

    conn = psycopg2.connect(dsn(store, args.env), connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(
        "select id, products, trial_slut from public.workspaces where slug = %s", (SLUG,)
    )
    rad = cur.fetchone()
    if rad is None:
        sys.exit(
            f"AVBRYTER: ingen arbetsyta med slug '{SLUG}' i {args.env}. "
            "Skriptet kopplar ett konto till den BEFINTLIGA pilotarbetsytan — "
            "det provisionerar ingen tenant (se TENANTS.md för den rutinen)."
        )
    arbetsyta, produkter_nu, trial_nu = str(rad[0]), list(rad[1] or []), rad[2]

    cur.execute("select id from auth.users where lower(email) = lower(%s)", (EPOST,))
    urad = cur.fetchone()
    finns = urad is not None

    print(f"miljö: {args.env}")
    print(f"arbetsyta: {arbetsyta} (products i dag: {produkter_nu}, trial: {trial_nu})")
    print(f"konto: {EPOST} — {'FINNS redan' if finns else 'saknas'}")

    if not args.apply:
        print(f"\nSkulle sätta products={PRODUKTER}, trial_slut={TRIAL_SLUT}, skapa")
        print("owner-inbjudan + konto och fylla business_contexts. Kör med --apply.")
        return 0

    # 1. Alla tre agenterna, gratis pilot till slutdatumet.
    if produkter_nu != PRODUKTER:
        cur.execute(
            "update public.workspaces set products = %s where id = %s",
            (PRODUKTER, arbetsyta),
        )
        print(f"  + products = {', '.join(PRODUKTER)}")
    if trial_nu != TRIAL_SLUT:
        cur.execute(
            "update public.workspaces set trial_slut = %s where id = %s",
            (TRIAL_SLUT, arbetsyta),
        )
        print(f"  + trial_slut = {TRIAL_SLUT} (pilotens gratisperiod)")

    # 2+3. Inbjudan före kontot — triggern läser den och lägger profilen i
    # pilotens arbetsyta i stället för att skapa en ny.
    if not finns:
        cur.execute(
            """insert into public.workspace_invites (email, workspace_id, role)
               select %s, %s, 'owner'
               where not exists (
                 select 1 from public.workspace_invites
                 where lower(email) = lower(%s) and accepted_at is null
               )""",
            (EPOST, arbetsyta, EPOST),
        )
        if cur.rowcount:
            print("  + owner-inbjudan skapad")

        losen = secrets.token_urlsafe(18)
        cur.execute(
            """insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at)
               values (%s, %s, jsonb_build_object('full_name', %s::text), now())
               returning id""",
            (EPOST, hasha(losen), NAMN),
        )
        anvandare = cur.fetchone()[0]
        env_set(f"{prefix}_LIVRUSTNING_LOSEN", losen)
        print(
            f"  + konto skapat; lösenordet ({len(losen)} tecken) sparat som "
            f"{prefix}_LIVRUSTNING_LOSEN i .env.deploy"
        )
    else:
        anvandare = urad[0]

    # Kontrollera att profilen faktiskt hamnade i pilotens arbetsyta — en
    # profil i FEL arbetsyta är värre än ingen, därför hård kontroll.
    cur.execute("select workspace_id from public.profiles where id = %s", (anvandare,))
    prad = cur.fetchone()
    if prad is None:
        # Triggern sväljer fel med flit (006) — läk via samma funktion.
        cur.execute("select public.ensure_workspace_for_user(%s, %s)", (anvandare, NAMN))
        cur.execute("select workspace_id from public.profiles where id = %s", (anvandare,))
        prad = cur.fetchone()
        print("  + profil läkt via ensure_workspace_for_user")
    if prad is None or str(prad[0]) != arbetsyta:
        conn.rollback()
        sys.exit(
            f"AVBRYTER: profilen pekar på {prad[0] if prad else 'ingenting'}, "
            f"inte på pilotarbetsytan {arbetsyta}. Ingenting har sparats."
        )

    # 5. Affärskontexten = onboardingflaggan. Utan den skickas inloggningen
    # till wizarden, vars paketval hade skrivit om products.
    cur.execute("select 1 from public.business_contexts where workspace_id = %s", (arbetsyta,))
    if cur.fetchone() is None:
        cur.execute(
            """insert into public.business_contexts
                   (workspace_id, product, target_audience, industries, geography,
                    tone, offer, cta, contact_roles, updated_at)
               values (%s, %s, %s, '{}', '{}', %s, %s, %s, '{}', now())""",
            (arbetsyta, PRODUKT, MALGRUPP, "Lågmäld, specifik, inga superlativ.", ERBJUDANDE, NASTA_STEG),
        )
        print("  + affärskontext skapad (inloggningen landar på /dashboard)")
    else:
        print("  = affärskontext fanns redan")

    conn.commit()
    print("\nKlart. Logga in som " + EPOST + " med lösenordet ur .env.deploy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
