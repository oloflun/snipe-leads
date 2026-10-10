#!/usr/bin/env python
"""Snajps egna produkter, målsegment och Iris-formulering. Idempotent.

    python scripts/snajp_malgrupp.py --env development                  # visar planen
    python scripts/snajp_malgrupp.py --env development --apply
    python scripts/snajp_malgrupp.py --env development --kund kund-1a2b3c4d --apply

Skälet (2026-10-06): provkörningen 2026-10-05 sökte utan målgrupp, drog mot bygg
och skolor, och utkasten räknade upp alla tre agenterna. Snajp säljer tre
produkter till olika segment. Här står vilka, i den form Iris läser dem:

  * settings.produkter  — researchen väljer EN produkt per bolag
  * settings.segment    — rangordnade målsegment; en körning utan filter söker i dem
  * settings.offentlig_sektor = false — bara privata bolag
  * kundinstruktionen för Iris — hur Snajp presenterar sig i utkastets mall
  * erbjudandena         — tre aktiva, lika viktade, villkor per produkt (2026-10-10)

Segmenten kommer ur Antons tabell 2026-10-06 (utbildning, e-handel, bygg,
konsult och byrå) plus fyra förslag (markerade nedan). Max sex segment ryms i
profilen; de med starkast passform för Iris går först, eftersom det är Iris
som söker dem. Ändra listan här och kör om.

Torrkörningen läser och visar, och skriver ingenting. --apply mintar en
kundnyckel via /api/keys (samma mönster som livrustning_produktkontext.py) och
skriver. Nycklar läses ur .env.deploy och skrivs aldrig ut.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from seed_demo import Api, deploy_env  # noqa: E402

PRODUKTER = [
    {
        "namn": "Iris, leadsagenten",
        "nytta": "hittar och kvalificerar nya företagskunder och skriver färdiga utkast som ni själva godkänner innan något skickas",
    },
    {
        "namn": "Supportagenten",
        "nytta": "svarar på återkommande kundfrågor i chatt och mejl dygnet runt, ur företagets egen kunskapsbas, och lämnar över till en människa när den inte säkert kan svara",
    },
    {
        "namn": "Kvittohanteraren",
        "nytta": "läser kvitton och fakturor, föreslår kontering enligt BAS-kontoplanen och exporterar till bokföringen",
    },
]

#: Bäst först. `varfor` är en mening om varför segmentet passar och vilken
#: produkt som bär det. (förslag) = inte i Antons tabell, Claudes förslag.
SEGMENT = [
    {"bransch": "utbildningsföretag", "varfor": "Kurs- och utbildningsföretag inom säkerhet, certifiering och arbetsmiljö säljer till företag och får många frågor om datum, intyg och bokning: Iris och Supportagenten."},
    {"bransch": "konsultbolag", "varfor": "Konsult- och byråbolag lever på nya företagskunder och har mycket underlag att hantera: Iris och Kvittohanteraren."},
    {"bransch": "fastighetsservice", "varfor": "(förslag) B2B-tjänster med serviceavtal, som fastighetsservice, städ och larm, säljer till företag och får återkommande ärenden: Iris och Supportagenten."},
    {"bransch": "IT-konsulter", "varfor": "(förslag) Små IT- och SaaS-bolag med företagskunder behöver nya kunder och har supportfrågor: Iris och Supportagenten."},
    {"bransch": "grossister", "varfor": "(förslag) Grossister och B2B-handel har företagskunder, orderfrågor och många fakturor: Iris, Supportagenten och Kvittohanteraren."},
    {"bransch": "redovisningsbyråer", "varfor": "(förslag) Redovisningsbyråer söker nya kunder och kan använda Kvittohanteraren åt sina egna kunder."},
]

MARKOR = "## Så presenterar sig Snajp i Iris utkast"
IRIS_INSTRUKTION = f"""{MARKOR}

- Erbjud den produkt researchen valt, och bara den. Nämn aldrig de andra agenterna.
- Avsluta med erbjudandets handling enligt villkoren under "Erbjudandet i det här mejlet" (svara "ja", svara med något bifogat, svara så bokar vi), aldrig med en fråga.
"""

#: Erbjudandena (A/B, app/leads/erbjudanden.py), Antons beslut 2026-10-10: alla
#: tre aktiva och lika viktade, villkor per produkt. Siffrorna är preliminära
#: uppskattningar tills vi har egna mätdata; det står med finstil i
#: användarvillkoren (app/villkor), aldrig i mejlen. Ändras i Iris
#: inställningar › Erbjudanden, eller här och kör om.
#: Gratisprovet för Supportagenten och Kvittohanteraren går via svar på mejlet
#: (frågor respektive kvitton bifogade) och hanteras för hand tills demolänken
#: och en kvittoadress finns: ingen kunskapsbas eller inkorg behöver kopplas.
IRIS, SUPPORT, KVITTO = (p["namn"] for p in PRODUKTER)
_PILOT = (
    "Vi tar in 20 företag i en pilot för {agent}. Vi tar bara 20 eftersom vi sätter upp varje företag "
    "personligen. Pilotföretagen får 50 % rabatt första året om de vill fortsätta, och 25 % så länge de "
    "stannar. Handling: svara \"pilot\" på mejlet, så håller vi en plats åt er."
)
ERBJUDANDEN = {
    "aktiva": [{"nyckel": n, "vikt": 1} for n in ("gratis_prov", "garanti", "pilot")],
    "villkor": {
        "gratis_prov": {
            IRIS: "Fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till vart och ett, helt utan kostnad och utan att det binder er till något. Handling: svara \"ja\" på mejlet, så skickar vi de fem inom två arbetsdagar.",
            SUPPORT: "Agentens svar på era fem vanligaste kundfrågor, utifrån era egna villkor, helt utan kostnad och utan att något behöver kopplas in. Handling: svara på mejlet med de fem frågorna och era villkor, så får ni tillbaka agentens svar inom en arbetsdag.",
            KVITTO: "Fem av era kvitton färdiga att ladda ned till bokföringen, med belopp, moms och konto, helt utan kostnad. Handling: svara på mejlet med fem kvitton bifogade, så får ni tillbaka dem färdiga inom en arbetsdag.",
        },
        "garanti": {
            IRIS: "Vi lovar minst 10 nya kunddialoger, alltså svar från intresserade företag, inom 90 dagar. Blir det färre förlänger vi provperioden utan kostnad tills ni har fått dem, så länge ni har godkänt utkasten i granskningen. Handling: svara på mejlet, så bokar vi 20 minuter där vi visar vilka företag Iris redan hittar åt er.",
            SUPPORT: "Vi lovar att ni lägger minst 50 % mindre tid på kundmejlen inom 60 dagar. Annars förlänger vi provperioden utan kostnad tills ni gör det. Handling: svara på mejlet, så bokar vi 20 minuter och sätter upp agenten på era vanligaste frågor.",
            KVITTO: "Vi lovar att ni lägger minst 70 % mindre tid på kvittona inom 60 dagar. Annars förlänger vi provperioden utan kostnad tills ni gör det. Handling: svara på mejlet, så bokar vi 20 minuter och kopplar in er inkorg.",
        },
        "pilot": {agent: _PILOT.format(agent=agent) for agent in (IRIS, SUPPORT, KVITTO)},
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=["development", "main"])
    parser.add_argument("--kund", default="snajp", help="kundens slug (standard: snajp)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store = deploy_env()
    prefix = f"RAILWAY_{args.env.upper()}"
    bas, master = store.get(f"{prefix}_API_URL"), store.get(f"{prefix}_MASTER_API_KEY")
    if not bas or not master:
        sys.exit(f"AVBRYTER: {prefix}_API_URL eller {prefix}_MASTER_API_KEY saknas i .env.deploy.")
    admin = Api(bas, master, skarpt=True)

    kund = next((t for t in admin.get("/api/admin/tenants").get("tenants") or [] if t.get("slug") == args.kund), None)
    if not kund:
        sys.exit(f"AVBRYTER: ingen kund med slug {args.kund!r} i {args.env}.")
    profil = admin.get(f"/api/admin/tenants/{kund['id']}/profil?agent_type=leads").get("profil") or {}
    instruktion = profil.get("instruktioner_md") or ""
    fore = instruktion.split(MARKOR)[0].rstrip()
    ny_instruktion = f"{fore}\n\n{IRIS_INSTRUKTION}".strip() + "\n"

    print(f"Miljö: {args.env}  Kund: {kund.get('name')} ({args.kund})")
    print("Produkter:", json.dumps([p["namn"] for p in PRODUKTER], ensure_ascii=False))
    print("Segment:  ", json.dumps([s["bransch"] for s in SEGMENT], ensure_ascii=False))
    print("Offentlig sektor: nej")
    print("Iris-instruktion:", "oförändrad" if ny_instruktion == instruktion else "skrivs (ersätter Snajps tidigare block)")
    print("Erbjudanden:", ", ".join(a["nyckel"] for a in ERBJUDANDEN["aktiva"]), "(lika vikt, villkor per produkt)")
    if not args.apply:
        print("\nTORRKÖRNING. Ingenting skrevs. Kör igen med --apply.")
        return

    status, svar = admin.anrop("POST", "/api/keys", {"tenant_name": kund["name"], "slug": args.kund})
    nyckel = (svar or {}).get("api_key") or (svar or {}).get("key")
    if not 200 <= status < 300 or not nyckel:
        sys.exit(f"AVBRYTER: kunde inte hämta nyckel för {args.kund} ({status}).")
    status, svar = Api(bas, nyckel, skarpt=True).anrop(
        "PUT", "/api/leads/config", {"produkter": PRODUKTER, "segment": SEGMENT, "offentlig_sektor": False}
    )
    if not 200 <= status < 300:
        sys.exit(f"AVBRYTER: inställningarna skrevs inte ({status}) — {svar.get('detail', '')}")
    status, svar = Api(bas, nyckel, skarpt=True).anrop("PUT", "/api/leads/erbjudanden", ERBJUDANDEN)
    if not 200 <= status < 300:
        sys.exit(f"AVBRYTER: erbjudandena skrevs inte ({status}) — {svar.get('detail', '')}")
    if ny_instruktion != instruktion:
        status, svar = admin.anrop(
            "PUT", f"/api/admin/tenants/{kund['id']}/profil",
            {"agent_type": "leads", "instruktioner_md": ny_instruktion},
        )
        if not 200 <= status < 300:
            sys.exit(f"AVBRYTER: Iris-instruktionen skrevs inte ({status}) — {svar.get('detail', '')}")
    print("\nKlart. Profilen kompileras om vid nästa körning.")


if __name__ == "__main__":
    main()
