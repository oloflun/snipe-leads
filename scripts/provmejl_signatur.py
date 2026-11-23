#!/usr/bin/env python
"""Ett provmejl genom sändkedjan med DEN HÄR arbetskopians kod.

    python scripts/provmejl_signatur.py --till snajpsupport@gmail.com           # torrkörning: visar texten
    python scripts/provmejl_signatur.py --till snajpsupport@gmail.com --apply   # skickar

## Varför skriptet finns

Anton 2026-11-23: "se till att den håller hela vägen i utskicken (skicka
provmejl till snajpsupport)". Signaturen, foten och HTML-delen ändrades i en
gren som ännu inte kör någonstans, och produktens egen Skicka provmejl-knapp
kör den kod som är deployad. Det här skriptet kör grenens kod på ett utkast i
samma form som de som står i kön i main: den GAMLA signaturen och den GAMLA
foten med Railway-adressen. Sedan samma steg som ett riktigt utskick:

  scheduler._fot_vid_godkannande   signaturen byts mot den aktuella, foten byggs om
  provmejl.skicka_provmejl         samma bygg_html och samma avsändare som utskicket

Lagringen är i minnet (MemoryStorage): ingen databas läses eller skrivs,
ingenting i kön eller hos något lead rörs. Mottagaren i tråden är påhittad;
provet går bara till `--till`, som måste vara en av Snajps egna adresser.

## Hemligheter

Mejltjänstens nyckel och avsändare läses ur Railway (tjänsten api i main) in i
processens miljö och skrivs aldrig ut. Utan `--apply` läses de inte alls.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROT / "snajp-support"))

#: Snajps signatur efter 2026-11-23 (samma som scripts/satt_mejlsignatur.py).
SIGNATUR = {
    "aktiv": True,
    "namn": "Sebastian Bergman",
    "titel": "Grundare & VD",
    "verksamhet": "Snajp | AI för leads och kundtjänst",
    "telefon": "+46 70 360 05 64",
    "epost": "sebastian@snajp.se",
    "ort": "Umeå & Göteborg",
    "webb": "www.snajp.se",
    "logotyp_url": "https://www.snajp.se/epost/snajp-logga.png",
}

#: Ett utkast så som det står i kön i main i dag: den gamla signaturen och
#: den gamla foten med Railway-adressen.
GAMMALT_UTKAST = """Hej,

Om vår agent Iris kunde ta fram 40 nya företag i veckan som passar er, med ett färdigt första mejl till varje, skulle det vara till nytta för er?

Vänliga hälsningar,
Sebastian Bergman
Snajp Support | AI för leads och kundtjänst
+46 70 360 05 64
snajpsupport@gmail.com

Umeå & Göteborg
www.snajp.se

Snajp Sverige

--
Snajp

Du får det här mejlet därför att din adress är hämtad ur offentliga företagsuppgifter och vi bedömer att erbjudandet är relevant för din verksamhet. Ändamålet är att ta en första affärskontakt.
Snajp är personuppgiftsansvarig för dina uppgifter. Du har rätt att invända mot behandlingen och att få dina uppgifter raderade.
Hur Snajp behandlar personuppgifter: https://www.snajp.se/integritetspolicy

Vill du inte få fler mejl från oss: https://web-production-1fe2c.up.railway.app/avregistrera/00000000000000000000000000000000"""

#: Det som läses ur Railway när provet ska skickas. Bara namn, aldrig värden, skrivs ut.
SANDVARIABLER = ("RESEND_API_KEY", "EMAIL_PROVIDER", "SMTP_FROM", "SMTP_FROM_NAME")


def _las_sandvag() -> list[str]:
    from railway_env_bootstrap import service_vars
    from railway_provision import envs_by_name, services_by_name, state

    projekt = state()
    variabler = service_vars(services_by_name(projekt)["api"]["id"], envs_by_name(projekt)["main"])
    satta = []
    for namn in SANDVARIABLER:
        if variabler.get(namn):
            os.environ[namn] = variabler[namn]
            satta.append(namn)
    return satta


async def kor(till: str, skicka: bool) -> int:
    from app.leads.provmejl import ProvmejlFel, skicka_provmejl
    from app.leads.scheduler import _fot_vid_godkannande
    from app.leads.send_provider import get_send_provider
    from app.leads.signatur import bygg_html, normalisera
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="snajp-prov", name="Snajp")
    tid = tenant["id"]
    storage.tenants[tid].update(company_name="Snajp", policy_url="https://www.snajp.se/integritetspolicy")
    await storage.set_agent_settings(tid, agent_type="leads", settings={"signatur": SIGNATUR})
    storage.mailboxes["prov"] = {
        "id": "prov", "tenant_id": tid, "provider": "imap", "address": till, "status": "active", "syfte": "leads",
    }
    # Påhittad mottagare med en personlig adress, så att foten blir den
    # fullständiga (art. 14). Provet skickas aldrig dit.
    prospekt = await storage.create_prospect(
        tid, company_name="Exempelbolaget AB", contact_name="Per Provsson", contact_email="per.provsson@exempelbolaget.test",
    )
    trad = await storage.ensure_outreach_thread(tid, prospect_id=prospekt["id"])
    koat = await storage.queue_outreach_message(
        tid, thread_id=trad["id"], subject="Prov: signaturen i första mejlet", body=GAMMALT_UTKAST,
        humanizer_variant="snajp:humanizer-svenska", scheduled_at=datetime.now(timezone.utc), status="awaiting_review",
    )
    item = koat["queue_item"]

    # Steg 1, som vid Godkänn och skicka: signaturen byts mot den aktuella och
    # foten byggs om med adressen i PUBLIC_BASE_URL.
    await _fot_vid_godkannande(storage, tid, item)
    text = (await storage.get_pending_outreach_message(tid, trad["id"]))["body"]
    print("--- TEXTDELEN EFTER GODKÄNNANDET " + "-" * 30)
    print(text)
    print("-" * 63)
    kontroller = {
        "en signatur, den nya": text.count("Sebastian Bergman") == 1 and "Grundare & VD" in text,
        "gamla titeln och adressen borta": "Snajp Support |" not in text and "snajpsupport@gmail.com" not in text,
        "ingen Railway-adress": "railway.app" not in text,
        "ren avregistreringsadress": "https://www.snajp.se/avregistrera/" in text,
        "kort GDPR-fot": "Ändamålet är att" not in text and "personuppgiftsansvarig" in text,
    }
    html = bygg_html(text, normalisera(SIGNATUR))
    kontroller["HTML-delen bär loggan och fet titel"] = "snajp-logga.png" in html and "font-weight:bold;\">Grundare &amp; VD" in html
    for namn, ok in kontroller.items():
        print(f"  {'OK ' if ok else 'FEL'} {namn}")
    if not all(kontroller.values()):
        print("AVBRYTER: kedjan gav inte det väntade mejlet. Inget skickat.")
        return 1
    if not skicka:
        print("TORRKÖRNING: inget skickat. Lägg till --apply.")
        return 0

    # Steg 2: produktens provmejlsväg, med samma bygg_html och avsändare som utskicket.
    try:
        svar = await skicka_provmejl(storage, tid, get_send_provider(), till=till, queue_item_id=item["id"])
    except ProvmejlFel as fel:
        print(f"AVBRYTER: {fel.text}")
        return 1
    print(f"Provmejl skickat till {svar['till']}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--till", required=True, help="en av Snajps egna adresser")
    parser.add_argument("--apply", action="store_true", help="skicka på riktigt (annars torrkörning)")
    args = parser.parse_args()

    # Aldrig en databas, aldrig en torrkörningsmapp som stoppar sändningen.
    for namn in ("DATABASE_URL", "SNAJP_OUTBOX_DIR"):
        os.environ.pop(namn, None)
    os.environ["PUBLIC_BASE_URL"] = "https://www.snajp.se"
    if args.apply:
        satta = _las_sandvag()
        print("Sändvägen läst ur Railway (main, api):", ", ".join(satta) or "inget")
    return asyncio.run(kor(args.till.strip().lower(), args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
