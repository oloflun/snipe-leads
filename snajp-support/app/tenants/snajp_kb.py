"""Kunskapsbas för Snajp — vår egen arbetsyta.

Källor: `lib/pricing.ts` (enda stället prissiffror får bo, se filens egen regel),
`lib/tenants/snajp.ts`, `TENANTS.md`, `AUTH.md` och produktens faktiska beteende
i `app/leads/autonomy.py` och `snajp-support/app/`. Sammanställd 2026-08-17.

Agenten får enligt sin grundningsregel bara svara utifrån dessa artiklar.
Ändras en siffra här ändras alltså vad agenten påstår för vår räkning — och
prissiffror ska ALDRIG ändras här först. De bor i `lib/pricing.ts`; den här
filen speglar dem.

VAD SOM MEDVETET SAKNAS, och därför är kodat som eskalering nedan:
supporttider, svarslöften/SLA, faktureringsintervall, uppsägningstid (bindningstiden
är noll, vilket inte är samma sak), och vad som gäller vid fel i tjänsten. De uppgifterna finns
inte skrivna någonstans i repot. En agent som gissar dem åt kundens räkning är
värre än en som lämnar över till en människa — se TENANTS.md.
"""

KB_ARTICLES: list[dict] = [
    # -- Företaget och produkten -------------------------------------------
    {
        "title": "Om Snajp",
        "category": "ovrigt",
        "content": (
            "Snajp bygger AI-agenter för svenska B2B-bolag. Vi levererar tre agenter: en "
            "kundservice-agent som svarar på inkommande ärenden utifrån kundens egen "
            "kunskapsbas, en leads-agent som hittar företag med konkreta signaler och "
            "skriver utkast till mejl, och en bokföringsagent som läser kvitton och "
            "fakturor och föreslår kontering. Verksamheten drivs från Göteborg och Umeå och "
            "arbetar med bolag i hela landet. Vi bygger inte om kundens hemsida — kunden "
            "behåller sin egen sajt, och det vi levererar är agenterna."
        ),
    },
    {
        "title": "Vad Snajp Support gör",
        "category": "teknisk_support",
        "content": (
            "Snajp Support är kundservice-agenten. Den läser inkommande mejl och "
            "chattmeddelanden, sorterar dem i rätt kategori, bedömer ton och prioritet, "
            "och skriver färdiga svarsutkast grundade i kundens egen kunskapsbas. "
            "I paketet ingår kundservice-agent, egen kunskapsbas, obegränsade chattar och "
            "e-posttriage. Agenten svarar aldrig ur en allmän modell — saknas svaret i "
            "kunskapsbasen säger den det och lämnar över till en människa i stället för "
            "att gissa."
        ),
    },
    {
        "title": "Vad Snajp Leads gör",
        "category": "teknisk_support",
        "content": (
            "Snajp Leads är leads-agenten. Den letar efter företag som matchar kundens "
            "idealkundprofil (ICP), läser publika signaler som nyöppningar, rekryteringar "
            "och ändrade tjänstesidor, och skriver utkast till mejl där tajmingen "
            "motiveras. I paketet ingår leads-agent, ICP-konfiguration, 150 prospekt per "
            "månad, 300 mejl per månad och en granskningskö. Uppgifterna hämtas ur öppna "
            "källor: bolagets egen webbplats, platsannonser och pressmeddelanden. Ingen "
            "LinkedIn-skrapning och inga köpta listor."
        ),
    },
    # -- Priser. Speglar lib/pricing.ts, ändra aldrig här först. -----------
    {
        "title": "Priser och paket",
        "category": "betalning",
        "content": (
            "Vi har fem paket, priser per månad exklusive moms:\n"
            "• Snajp Support — 3 990 kr/mån. Kundservice-agenten som svarar utifrån er "
            "egen kunskapsbas.\n"
            "• Snajp Leads — 4 490 kr/mån. Leads-agenten som hittar och skriver till rätt "
            "företag.\n"
            "• Snajp Bokföring — 2 690 kr/mån. Bokföringsagenten som läser kvitton och "
            "föreslår kontering.\n"
            "• Snajp Duo — 6 990 kr/mån. Leads- och kundservice-agenten i samma dashboard, "
            "med delad kunddata.\n"
            "• Snajp Trio — 9 990 kr/mån. Alla tre agenterna: leads, kundtjänst och "
            "bokföring.\n"
            "Duo kostar 1 490 kr mindre per månad än att köpa Support och Leads var för "
            "sig (3 990 + 4 490 = 8 480 kr). Trio kostar 1 180 kr mindre än alla tre var "
            "för sig (3 990 + 4 490 + 2 690 = 11 170 kr)."
        ),
    },
    {
        "title": "Uppstartsavgift och bindningstid",
        "category": "betalning",
        "content": (
            "Vid start tillkommer en engångsavgift på 1 590 kr. Den täcker uppsättning av "
            "kunskapsbasen och konfigurationen av agenten för verksamheten — alltså det "
            "arbete som gör att agenten svarar om ert bolag och inte i allmänhet.\n\n"
            "Det finns ingen bindningstid: 0 månader.\n\n"
            "Frågar kunden om uppsägningstid, faktureringsintervall eller återbetalning: "
            "svara inte på egen hand. Att bindningstiden är noll säger INTE vilken "
            "uppsägningstid som gäller, och de två blandas lätt ihop. Lämna över till en "
            "människa."
        ),
    },
    {
        "title": "Volymer och vad som kostar extra",
        "category": "betalning",
        "content": (
            "Snajp Leads innehåller 150 prospekt och 300 mejl per månad. Utöver den "
            "volymen kostar varje ytterligare prospekt 9 kr och varje ytterligare mejl "
            "3 kr.\n\n"
            "Snajp Support har obegränsade chattar — där finns alltså inget volymtak att "
            "räkna på.\n\n"
            "Snajp Bokföring säljs med en kampanj: en extra bokföringsagent kostar 999 kr. "
            "Frågar kunden hur länge kampanjen gäller, eller vad en extra agent innebär i "
            "praktiken: det är inte fastställt i vårt underlag. Lämna över till en "
            "människa.\n\n"
            "Frågar kunden hur överskjutande volym faktureras eller när i månaden den "
            "räknas av: det är inte fastställt i vårt underlag. Lämna över till en "
            "människa."
        ),
    },
    # -- Kontrollen. Den vanligaste invändningen. --------------------------
    {
        "title": "Ingenting skickas utan att kunden godkänt det",
        "category": "ovrigt",
        "content": (
            "Det här är den vanligaste frågan, och svaret är entydigt: agenten skickar "
            "ingenting på egen hand som kunden inte har ställt in att den får skicka.\n\n"
            "Leads-agenten har tre nivåer som kunden själv väljer:\n"
            "• Bara utkast — agenten researchar och skriver, men ingenting lämnar systemet "
            "utan att kunden tryckt skicka.\n"
            "• Första kontakten — agenten får skicka det första mejlet själv. "
            "Uppföljningar kräver godkännande.\n"
            "• Till bokat möte — agenten får föra dialogen fram till ett möte, men bokar "
            "aldrig en tid utan bekräftelse.\n\n"
            "Oavsett nivå granskas de tre första utskicken alltid av en människa. "
            "Kundservice-agentens svar kan på samma sätt ställas in per kategori: "
            "automatiskt svar, utkast för godkännande, eller alltid till en människa."
        ),
    },
    {
        "title": "Hur agenten vet vad den ska svara",
        "category": "teknisk_support",
        "content": (
            "Agenten svarar utifrån kundens egen kunskapsbas — artiklar som skrivs vid "
            "uppstarten utifrån kundens webbplats, villkor och det kunden berättar. Den "
            "hämtar alltså inte svar ur en allmän språkmodell.\n\n"
            "Hittar agenten inget stöd för ett svar i kunskapsbasen svarar den inte ändå. "
            "Då säger den att den inte har uppgiften och kopplar in en människa. Det är ett "
            "medvetet val: ett trovärdigt men felaktigt svar i kundens namn är värre än ett "
            "ärligt överlämnande. Samma regel gäller motstridiga uppgifter — står två olika "
            "saker i underlaget jämkar agenten inte ihop dem, den eskalerar."
        ),
    },
    {
        "title": "Dataskydd och var uppgifterna finns",
        "category": "ovrigt",
        "content": (
            "Uppgifterna lagras inom EU. Varje kund har sin egen avgränsade data — "
            "kunskapsbas, ärenden och prospekt är separerade per kund på databasnivå, så "
            "en kunds agent kan inte läsa en annan kunds underlag.\n\n"
            "Leads-agenten använder enbart öppna källor: företagets egen webbplats, "
            "platsannonser och pressmeddelanden. Vi skrapar inte LinkedIn och köper inte "
            "adresslistor.\n\n"
            "Frågar kunden om personuppgiftsbiträdesavtal, radering enligt GDPR eller "
            "registerutdrag: hantera det inte automatiskt. Sådana begäranden har rättslig "
            "verkan och en lagstadgad svarsfrist — lämna alltid över till en människa."
        ),
    },
    # -- Den uttryckliga eskaleringsartikeln -------------------------------
    {
        "title": "Frågor som alltid går till en människa",
        "category": "ovrigt",
        "content": (
            "Följande är INTE fastställt i vårt underlag. Svara aldrig på dem på egen "
            "hand, ens ungefärligt, utan säg att du kopplar in en kollega:\n"
            "• Supporttider och när kunden kan förvänta sig svar\n"
            "• Svarslöften eller SLA\n"
            "• Uppsägningstid — bindningstiden är noll, men uppsägningstiden är inte "
            "fastställd\n"
            "• Faktureringsintervall, betalningsvillkor och återbetalning\n"
            "• Vad som gäller vid fel eller avbrott i tjänsten\n"
            "• Avtalstext, personuppgiftsbiträdesavtal och andra juridiska handlingar\n"
            "• Rabatter, offerter och avsteg från prislistan\n\n"
            "En gissning på någon av de här punkterna kan kosta pengar eller bli ett "
            "åtagande vi inte kan hålla."
        ),
    },
]
