#!/usr/bin/env python
"""Snajps egna produkter, målsegment och Iris-formulering. Idempotent.

    python scripts/snajp_malgrupp.py --env development                  # visar planen
    python scripts/snajp_malgrupp.py --env development --apply
    python scripts/snajp_malgrupp.py --env development --kund kund-1a2b3c4d --apply

Skälet (2026-10-06): provkörningen 2026-10-05 sökte utan målgrupp, drog mot bygg
och skolor, och utkasten räknade upp alla tre agenterna. Snajp säljer två
produkter till olika segment. Här står vilka, i den form Iris läser dem:

Kvittohanteraren är borttagen ur listan sedan 2026-10-17 (Sebbe): den står på
is, säljs inte och ska inte förekomma i Iris utkast. Admin använder den som
vanligt. Ta tillbaka den här, i SEGMENT och i ERBJUDANDEN när den ska säljas
igen (lib/routes.ts: VILANDE_PRODUKTER styr arbetsytan).

  * settings.produkter  — researchen väljer EN produkt per bolag
  * settings.segment    — rangordnade målsegment; en körning utan filter söker i dem
  * settings.offentlig_sektor = false — bara privata bolag
  * kundinstruktionen för Iris — hur Snajp presenterar sig i utkastets mall
  * erbjudandena         — piloten i form A och B, lika viktade (Anton 2026-10-25)

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
        # Sebbe 2026-10-29: effektiviseringen först, så att mottagaren förstår
        # tidigt att prospekteringen går fortare, och en inblick i hur enkelt.
        "nytta": "effektiviserar prospekteringen: hittar och kvalificerar nya företagskunder efter er idealkund och skriver färdiga första mejl som ni själva godkänner innan något skickas, så att tiden går till samtal i stället för research",
    },
    {
        "namn": "Supportagenten",
        "nytta": "effektiviserar kundhanteringen: svarar direkt på återkommande kundfrågor i chatt och mejl dygnet runt, ur företagets egen kunskapsbas, och lämnar över till en människa när den inte säkert kan svara, så att teamet slipper svara på samma frågor om och om igen",
    },
]

#: Bäst först. `varfor` är en mening om varför segmentet passar och vilken
#: produkt som bär det. (förslag) = inte i Antons tabell, Claudes förslag.
SEGMENT = [
    {"bransch": "utbildningsföretag", "varfor": "Kurs- och utbildningsföretag inom säkerhet, certifiering och arbetsmiljö säljer till företag och får många frågor om datum, intyg och bokning: Iris och Supportagenten."},
    {"bransch": "konsultbolag", "varfor": "Konsult- och byråbolag lever på nya företagskunder: Iris."},
    {"bransch": "fastighetsservice", "varfor": "(förslag) B2B-tjänster med serviceavtal, som fastighetsservice, städ och larm, säljer till företag och får återkommande ärenden: Iris och Supportagenten."},
    {"bransch": "IT-konsulter", "varfor": "(förslag) Små IT- och SaaS-bolag med företagskunder behöver nya kunder och har supportfrågor: Iris och Supportagenten."},
    {"bransch": "grossister", "varfor": "(förslag) Grossister och B2B-handel har företagskunder och orderfrågor: Iris och Supportagenten."},
]

MARKOR = "## Så presenterar sig Snajp i Iris utkast"
IRIS_INSTRUKTION = f"""{MARKOR}

- Erbjud den produkt researchen valt, och bara den. Nämn aldrig de andra agenterna.
- Nämn aldrig kvitton, bokföring eller Kvittohanteraren: den säljs inte just nu.
- Avsluta med erbjudandets handling enligt villkoren under "Erbjudandet i det här mejlet", som en vardaglig inbjudan. Aldrig "Svara X så gör vi Y" och aldrig med en fråga.
- Kalla Iris "vår agent Iris" första gången och sedan "Iris". Aldrig "Iris, leadsagenten", "leadsagenten Iris", "Vår Iris" eller "hon".
- Iris hittar och kvalificerar nya företagskunder och skriver första mejlet till dem. Iris hittar aldrig tomter, investerare, leverantörer eller personal.
- Frågan i form B: för Iris om det tar mest tid att hantera de förfrågningar som redan kommer in eller att hitta nya kunder; för Supportagenten om det tar mest tid att gå igenom kundmejlen eller att sitta i supportchattarna. Inga andra moment.
- Mejlet är varmt och informerande, aldrig säljigt eller pushande. Senast i meningen efter ingången ska mottagaren förstå att agenten effektiviserar deras arbete: för Iris att hitta nya kunder (prospekteringen), för Supportagenten kundhanteringen. Säg det med vad de slipper eller får tid till, och ge en kort inblick i hur enkelt det är (Iris: ni säger vilka kunder ni söker, och Iris tar fram bolagen och skriver första mejlet som ni godkänner; Supportagenten: den svarar utifrån er egen information). "Effektiviserar prospekteringen" eller "effektiviserar kundhanteringen" får stå en gång.
- Ingången beskriver vad deras arbete går ut på, utan problem och utan krav på dem: aldrig vad deras kunder förväntar sig eller kräver, aldrig att frågorna växer eller tar tid från något, och aldrig en fråga om hur de ska hinna eller kunna klara något.
- Rabatten är "upp till 50 %" för den som stannar efter piloten, aldrig "50 %" rakt av.
"""

#: Erbjudandena (A/B, app/leads/erbjudanden.py), Antons beslut 2026-10-10: alla
#: tre aktiva och lika viktade, villkor per produkt. Siffrorna är preliminära
#: uppskattningar tills vi har egna mätdata; det står med finstil i
#: användarvillkoren (app/villkor), aldrig i mejlen. Ändras i Iris
#: inställningar › Erbjudanden, eller här och kör om.
#: Gratisprovet för Supportagenten går via svar på mejlet (frågorna bifogade)
#: och hanteras för hand tills demolänken finns: ingen kunskapsbas behöver kopplas.
IRIS, SUPPORT = (p["namn"] for p in PRODUKTER)
#: Antons villkor 2026-10-25: piloten i varje mejl, inga fler detaljer, och
#: avslutet en vardaglig inbjudan till demon eller en kostnadsfri genomgång.
#: Kort (2026-10-25): piloten och avslutet tog 60 av 105–150 ord i provet.
#: Sebbe 2026-10-29: "upp till 50 % rabatt om du stannar efteråt", och demon
#: kräver ingen inloggning (app/demo): mottagaren testar direkt.
_PILOT = (
    "Just nu tar vi in 20 företag i en kostnadsfri pilot av {agent} i tre månader, med alla funktioner. "
    "Du får upp till 50 % rabatt om du stannar efteråt. Handling: testa {agent} direkt i demon på "
    "snajp.se/demo, eller svara på mejlet så bokar vi en kostnadsfri genomgång."
)
#: Kortnamnet i texten ("Iris", inte "Iris, leadsagenten"): Anton 2026-10-25 om
#: mejlen som "berättar om 'leadsagenten' helt utan kontext".
_PILOTER = {agent: _PILOT.format(agent=agent.split(",")[0]) for agent in (IRIS, SUPPORT)}
#: Ämnesraderna per produkt (Sebbe 2026-10-29), i du-form: koden väljer en
#: per mejl och skriver om den till ni-form när mottagaren inte är namngiven
#: (app/leads/erbjudanden.py:valj_amne). Den första i varje lista är den
#: starkaste och står i ungefär vart tredje mejl.
AMNEN = {
    IRIS: [
        "Effektivisering av prospektering",
        # Tidsvinst i sökandet
        "Sluta leta efter kunder, låt dem hittas åt dig",
        "Från timmar av research till minuter",
        "Din säljare ska sälja, inte googla bolag",
        "Researchen är klar innan kaffet är slut",
        "Mer tid till samtal, mindre tid i Excel",
        "Den tråkiga delen av prospekteringen, automatiserad",
        # Träffsäkerhet och idealkund
        "Rätt företag, rätt tidpunkt, varje morgon",
        "Bara bolag som matchar din idealkund",
        "Slipp leadlistor som inte leder någonvart",
        "Vilka bolag i din bransch växer just nu?",
        "Nya företagskunder som redan passar din profil",
        "Träffsäker prospektering, utan gissningar",
        # Signaler och timing
        "Vi märker när ett bolag är redo att köpa",
        "Nyanställd säljchef hos din målgrupp? Du vet det först",
        "Kontakta bolaget medan nyheten fortfarande är färsk",
        "Prospektering som styrs av vad som händer, inte av magkänsla",
        "Ett bolag rekryterar eller expanderar. Du får veta samma dag",
        # Skalbarhet och pipeline
        "En full säljpipeline utan extra researchtjänster",
        "Fyll pipen utan att öka bemanningen",
        "Hur hittar du dina nästa 50 kunder?",
        "Så får ditt team jämnare flöde av nya leads",
        "Samma säljteam, fler kvalificerade samtal",
        # Frågor som väcker nyfikenhet
        "Hur lång tid tar det dig att hitta en ny kund?",
        "Vad kostar en timme av ditt säljteams researchtid?",
        "Hur vet du vilka bolag du borde ringa i dag?",
        "Skulle du vilja ha dina nästa leads färdiga i morgon bitti?",
    ],
    SUPPORT: [
        "Support 24/7 för dina kunder",
        "Svar till dina kunder, även klockan 03:00",
        "Halvera din supportkö utan att anställa",
        "Kunder som får svar direkt blir kvar längre",
        "Slipp upprepa samma svar 50 gånger om dagen",
        "Vad händer med frågorna som kommer efter kl. 17?",
        "En supportagent som kan din FAQ utantill",
        "Kortare svarstider, nöjdare kunder",
        "Så avlastar du supporten under säsongstopparna",
        "Din support, alltid på. Utan extra bemanning",
        "Färre tickets till teamet, snabbare svar till kunden",
    ],
}
#: A/B (Anton 2026-10-25): samma pilot, två former, hälften var. Katalogens
#: gratisprov och garanti står kvar avslagna och kan slås på i Leads › Erbjudanden.
ERBJUDANDEN = {
    "aktiva": [{"nyckel": "pilot_a", "vikt": 1}, {"nyckel": "pilot_b", "vikt": 1}],
    "egna": {
        "pilot_a": {"namn": "Piloten, form A", "form": "rak"},
        "pilot_b": {"namn": "Piloten, form B (frågan)", "form": "fraga"},
    },
    "amnen": AMNEN,
    "villkor": {
        "pilot_a": _PILOTER,
        "pilot_b": _PILOTER,
        "pilot": _PILOTER,
        "gratis_prov": {
            IRIS: "Fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till vart och ett, helt utan kostnad och utan att det binder er till något. Handling: vill ni ha dem svarar ni på mejlet, så skickar vi de fem inom två arbetsdagar.",
            SUPPORT: "Agentens svar på era fem vanligaste kundfrågor, utifrån era egna villkor, helt utan kostnad och utan att något behöver kopplas in. Handling: skicka de fem frågorna och era villkor som svar på mejlet, så får ni tillbaka agentens svar inom en arbetsdag.",
        },
        "garanti": {
            IRIS: "Vi lovar minst 10 nya kunddialoger, alltså svar från intresserade företag, inom 90 dagar. Blir det färre förlänger vi provperioden utan kostnad tills ni har fått dem, så länge ni har godkänt utkasten i granskningen. Handling: vill ni se hur det fungerar bokar vi gärna 20 minuter, det räcker med ett svar på mejlet.",
            SUPPORT: "Vi lovar att ni lägger minst 50 % mindre tid på kundmejlen inom 60 dagar. Annars förlänger vi provperioden utan kostnad tills ni gör det. Handling: vill ni se hur det fungerar bokar vi gärna 20 minuter, det räcker med ett svar på mejlet.",
        },
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
    # Servern sparar texten utan avslutande radbrytning: jämför utan den, annars
    # säger torrkörningen "skrivs" även direkt efter en --apply.
    oforandrad = ny_instruktion.rstrip() == instruktion.rstrip()
    print("Iris-instruktion:", "oförändrad" if oforandrad else "skrivs (ersätter Snajps tidigare block)")
    print("Erbjudanden:", ", ".join(a["nyckel"] for a in ERBJUDANDEN["aktiva"]), "(lika vikt, villkor per produkt)")
    print("Ämnesrader:", ", ".join(f"{p} {len(r)}" for p, r in AMNEN.items()))
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
    if not oforandrad:
        status, svar = admin.anrop(
            "PUT", f"/api/admin/tenants/{kund['id']}/profil",
            {"agent_type": "leads", "instruktioner_md": ny_instruktion},
        )
        if not 200 <= status < 300:
            sys.exit(f"AVBRYTER: Iris-instruktionen skrevs inte ({status}) — {svar.get('detail', '')}")
    print("\nKlart. Profilen kompileras om vid nästa körning.")


if __name__ == "__main__":
    main()
