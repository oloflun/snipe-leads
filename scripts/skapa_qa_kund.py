#!/usr/bin/env python3
"""Skapar QA-besiktningens KUND-konto i en Railway-miljö.

    python scripts/skapa_qa_kund.py --env development           # visa planen
    python scripts/skapa_qa_kund.py --env development --apply

## Varför skriptet finns

`scripts/qa_vyer.mjs` besiktigar varje vy i TRE roller: anonym, kund och
plattformsadmin. Adminrollen har ett konto. Kundrollen har det inte — kontot
`kund@example.com` stod som defaultvärde i skriptet utan att någonsin ha
skapats, så kundraderna rapporterade

    ! inloggningen misslyckades
    200  /dashboard  →  /login  "Logga in"

i varje körning. Det såg ut som elva gröna rader och var elva rader som mätte
inloggningssidan. **Kundrollens vyer har alltså aldrig besiktigats** — och det
är den roll de flesta av produktens användare faktiskt har.

## Vad kontot behöver för att räknas som en kund

Tre saker, och de två sista är lätta att glömma:

 1. En rad i `auth.users` med ett scrypt-hashat lösenord. Formatet ägs av
    `lib/password.ts` och speglas nedan — se `hasha()` om varför Python kan
    räkna fram exakt samma sträng som Node.
 2. Workspace och profil. De skapas av triggern `on_auth_user_created`
    (migration 001/006), inte av det här skriptet. Faller triggern faller
    allt tyst, så vi kontrollerar efteråt att raderna finns.
 3. En rad i `business_contexts`. Det ÄR onboardingflaggan — se
    `hasCompletedOnboarding` i lib/workspace.ts. Utan den skickar
    `requireOnboarded()` kunden till /onboarding, och besiktningen hade
    fortsatt mäta fel sida, bara en annan.

## Bara mot Railway, aldrig mot produktion utan flagga

`--env main` går, men kräver `--jag-menar-produktion`. Ett testkonto i
produktionens `auth.users` är ett riktigt konto med ett publikt känt lösenord.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

#: Speglar defaultvärdena i scripts/qa_vyer.mjs. Ändras de där ska de ändras
#: här — två filer som måste hållas i takt är priset för att besiktningen ska
#: kunna köras utan att någon först läser ett dokument.
EPOST = os.environ.get("QA_KUND_EPOST", "kund@example.com")
LOSEN = os.environ.get("QA_KUND_LOSEN", "Kundtest123!")
NAMN = "QA Kundsson"

KEYLEN = 64


def hasha(losenord: str) -> str:
    """`scrypt$1$<salt>$<hash>`, bitidentiskt med lib/password.ts.

    Node anropar `crypto.scrypt(password, salt, 64)` utan optioner, alltså med
    standardparametrarna N=16384, r=8, p=1. Pythons `hashlib.scrypt` tar samma
    parametrar explicit och ger samma resultat — det är samma KDF, inte en
    approximation. Verifieras av `verifyPassword` vid första inloggningen, och
    det är den enda kontroll som räknas.
    """
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
        sys.exit(
            "Vägrar mot main utan --jag-menar-produktion. Ett QA-konto i "
            "produktionens auth.users är ett riktigt konto med ett lösenord "
            "som står i klartext i repot."
        )

    conn = psycopg2.connect(dsn(env_read(), args.env), connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("select id from auth.users where lower(email) = lower(%s)", (EPOST,))
    rad = cur.fetchone()
    finns = rad is not None

    print(f"miljö: {args.env}")
    print(f"konto: {EPOST} — {'FINNS redan' if finns else 'saknas'}")

    if not args.apply:
        print("\nSkulle " + ("kontrollera onboarding." if finns else "skapa kontot, workspace och affärskontext."))
        print("Kör med --apply.")
        return 0

    if not finns:
        cur.execute(
            """insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at)
               values (%s, %s, jsonb_build_object('full_name', %s::text), now())
               returning id""",
            (EPOST, hasha(LOSEN), NAMN),
        )
        anvandare = cur.fetchone()[0]
        print(f"  + auth.users skapad")
    else:
        anvandare = rad[0]

    # Triggern ska ha skapat workspace + profil. Faller den gör den det TYST
    # (migration 006 gjorde den exception-säker med flit), så vi läker här i
    # stället för att anta.
    cur.execute("select workspace_id from public.profiles where id = %s", (anvandare,))
    prad = cur.fetchone()
    if prad is None:
        cur.execute("select set_config('app.user_id', %s, true)", (str(anvandare),))
        cur.execute("select public.ensure_workspace_for_current_user()")
        cur.execute("select workspace_id from public.profiles where id = %s", (anvandare,))
        prad = cur.fetchone()
        print("  + profil/workspace läkt (triggern hade inte skapat dem)")
    if prad is None:
        conn.rollback()
        sys.exit("Kontot fick ingen profil. Migration 001/006 är inte körd i den här miljön.")
    arbetsyta = prad[0]

    cur.execute("update public.workspaces set name = %s where id = %s and name <> %s",
                ("QA Kund AB", arbetsyta, "QA Kund AB"))
    if cur.rowcount:
        print("  + arbetsytan döpt till 'QA Kund AB'")

    # Onboardingflaggan. Se modulens docstring: utan den här raden skickas
    # kunden till /onboarding och besiktningen mäter fortfarande fel sida.
    cur.execute("select 1 from public.business_contexts where workspace_id = %s", (arbetsyta,))
    if cur.fetchone() is None:
        cur.execute(
            """insert into public.business_contexts
                   (workspace_id, product, target_audience, industries, geography,
                    tone, offer, cta, contact_roles, updated_at)
               values (%s, %s, %s, '{}', '{}', %s, %s, %s, '{}', now())""",
            (
                arbetsyta,
                "QA-KONTO. Finns bara för scripts/qa_vyer.mjs och säljer ingenting.",
                "Ingen — kontot används för besiktning av vyer.",
                "Neutral.",
                "Inget erbjudande.",
                "Inget nästa steg.",
            ),
        )
        print("  + affärskontext skapad (kontot räknas nu som onboardat)")
    else:
        print("  = affärskontext fanns redan")

    conn.commit()
    print("\nKlart. Kör besiktningen:")
    print("  BASE=<url> node scripts/qa_vyer.mjs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
