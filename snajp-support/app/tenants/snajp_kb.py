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

#: Rubriker som funnits i den här filen men döpts om — seedningen raderar
#: dem så att en omdöpt artikel inte lämnar en föråldrad dubblett i basen.
FORLEGADE_RUBRIKER: tuple[str, ...] = (
    "Hur man kommer igång, och hur lång tid det tar",
)

KB_ARTICLES: list[dict] = [
    # -- Företaget och produkten -------------------------------------------
    {
        "title": "Om Snajp",
        "category": "ovrigt",
        "content": (
            "Snajp bygger AI-agenter för svenska B2B-bolag. Vi levererar tre agenter: en "
            "kundservice-agent som svarar på inkommande ärenden utifrån kundens egen "
            "kunskapsbas, Iris — leads-agenten som hittar företag med konkreta signaler "
            "och skriver utkast till mejl — och Kvittohanteraren, som läser kvitton ur "
            "mejlen och sammanställer dem. Kvittohanteraren bokför ingenting själv; den "
            "läser av, sammanställer och exporterar som SIE4 till kundens eget "
            "bokföringsprogram. Verksamheten drivs från Göteborg och Umeå och arbetar "
            "med bolag i hela landet. Vi bygger inte om kundens hemsida — kunden "
            "behåller sin egen sajt, och det vi levererar är agenterna."
        ),
    },
    {
        "title": "Vilka står bakom Snajp",
        "category": "ovrigt",
        # Speglar lib/team.ts och /vart-team (2026-10-05). Namnen är
        # bekräftade uppgifter, inte härledda — se team.ts egen docstring.
        "content": (
            "Snajp har två grundare: Sebastian Bergman och Anton Lundin. Båda har "
            "titeln Grundare — det finns ingen uppdelning i vd eller teknikchef, och "
            "det är medvetet: två grundare i ett litet bolag som gör allting "
            "tillsammans. Sebastian har byggt det mesta av plattformen: agenternas "
            "backend, databasen och gränssnittet kunderna arbetar i. Anton har byggt "
            "agenternas färdighetsregister — spelböckerna som avgör vad de kan och hur "
            "de resonerar. Snajp byggs i Göteborg och Umeå. Mer om teamet finns på "
            "sidan /vart-team på snajp.se."
        ),
    },
    {
        "title": "Kontakt med Snajp",
        "category": "ovrigt",
        "content": (
            "Mejladressen till Snajp är kontakt@snajp.se — den gäller både frågor om "
            "tjänsten och övriga ärenden. En demo bokas på /boka-demo (15–20 minuter). "
            "Telefonnummer och supporttider är inte fastställda i vårt underlag; "
            "frågar kunden efter dem, hänvisa till mejladressen eller koppla in en "
            "kollega."
        ),
    },
    {
        "title": "Hitta rätt på arbetsytan",
        "category": "teknisk_support",
        # Speglar arbetsytans faktiska navigering (components/AppShell.tsx,
        # vyerna under components/). Uppdatera när menyn ändras.
        "content": (
            "Arbetsytan nås efter inloggning på snajp.se och har en meny till "
            "vänster:\n"
            "• Översikt — nyckeltalen överst (väntande utkast, nya leads, ärenden) "
            "och Att göra för alla agenter.\n"
            "• Iris — leads-agenten: Bolag (prospekten med bedömning och utkast), "
            "Granskning (utkast som väntar på godkännande), Inställningar (målgrupp "
            "och automation) och CRM-lista. Knappen \"Kör Iris\" startar en körning.\n"
            "• Kundtjänst — Inkorgen (mejl med svarsutkast att godkänna, knapparna "
            "Förbättra, Kortare och Mer personlig skriver om utkastet) och "
            "Kundchatten.\n"
            "• Kvitton — Kvittohanteraren: koppla inkorgen och tryck \"Skanna "
            "inkorgen\", ställ frågor till kvittoassistenten i chatten.\n"
            "• Inställningar — här kopplas mejlinkorgen (med app-lösenord från "
            "mejlleverantören), kunskapsbasen fylls på, affärskontexten \"Vad ni "
            "säljer\" skrivs in, och eskaleringsregler ställs in.\n\n"
            "Ingenting skickas till riktiga mottagare utan godkännande enligt den "
            "autonominivå kunden valt. Går något inte att hitta: be kunden beskriva "
            "vad den försöker göra, eller koppla in en kollega."
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
            "kunskapsbasen säger den det rakt ut i stället för att gissa, svarar på det "
            "den har stöd för och erbjuder att en kollega tittar på resten. Ärenden som "
            "rör pengar tillbaka, fakturafel, juridik, GDPR, säkerhet eller en kund i "
            "kris lämnar den alltid över till en människa direkt."
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
            "• Snajp Kvitton — 2 690 kr/mån. Kvittohanteraren som läser kvitton ur "
            "mejlen (endast läsbehörighet) och exporterar som SIE4. Den bokför "
            "ingenting själv.\n"
            "• Snajp Duo — 6 990 kr/mån. Leads- och kundservice-agenten i samma dashboard, "
            "med delad kunddata.\n"
            "• Snajp Trio — 9 990 kr/mån. Alla tre agenterna: leads, kundtjänst och "
            "kvitton.\n"
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
            "Snajp Kvitton säljs med en kampanj: en extra kvittoagent kostar 999 kr. "
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
            "Då säger den att den inte har uppgiften, svarar på det den har stöd för, och "
            "erbjuder att en kollega tittar på frågan — tackar kunden ja lämnas ärendet "
            "över i samma samtal. Det är ett medvetet val: ett trovärdigt men felaktigt "
            "svar i kundens namn är värre än ett ärligt \"det vet jag inte\", och kunden "
            "slipper vänta på en människa för en fråga hen kanske inte behöver svar på.\n\n"
            "Vissa ärenden lämnar agenten alltid över direkt: pengar tillbaka, fakturafel, "
            "juridik, GDPR-begäranden, säkerhet, en kund i kris, en arg kund eller en "
            "kund som ber om en människa. Samma sak gäller motstridiga uppgifter — står "
            "två olika saker i underlaget jämkar agenten inte ihop dem, den eskalerar."
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
    # -- Speglar sajtens FAQ (lib/faq.ts, 2026-08-25). Samma regel som för
    # priserna: sakuppgifterna ägs av FAQ-filen och Next-sidorna; den här
    # filen speglar dem så att chatten och sajten säger samma sak. FAQ-poster
    # med "TODO: bekräfta med Sebbe" (provperiodens längd, uppsägningstid)
    # speglas INTE — de är kodade som eskalering i artikeln nedan. ----------
    {
        "title": "Komma igång: testa, demo och hur lång tid det tar",
        "category": "ovrigt",
        # "testa/test" måste stå i texten: fulltextsökningen hittade inte
        # artikeln på "Hur kommer vi igång om vi vill testa?" när den bara
        # sa "prova" (batteritestet 2026-10-05).
        "content": (
            "Vill ni testa Snajp finns två vägar. Alla tre agenterna går att testa "
            "direkt i webbläsaren utan konto, med exempeldata — på produktsidorna "
            "för leads, support och kvitton. Nästa steg är en demo på 15–20 "
            "minuter, bokas på /boka-demo: vi går igenom kundens egna ärenden "
            "eller kunder live, kunden ser vad agenten föreslår, och vi säger "
            "rakt ut om vi tror att det passar. Inga förpliktelser.\n\n"
            "Att koppla en inkorg och fylla kunskapsbasen är dagens arbete, inte "
            "månadens. Det som tar tid är att komma överens om tonen i svaren, och det "
            "görs bäst genom att köra agenten i utkastläge ett par dagar och rätta det "
            "som blir fel.\n\n"
            "Frågar kunden om en längre kostnadsfri testperiod eller provperiod på "
            "ett eget konto: villkoren är inte fastställda i vårt underlag — lämna "
            "över till en människa i stället för att gissa."
        ),
    },
    {
        "title": "Fungerar agenterna på svenska?",
        "category": "teknisk_support",
        "content": (
            "Ja. Agenterna hämtar sina formuleringar ur kundens egen kunskapsbas, så "
            "tonen blir kundens egen och inte en översättning. Produkten är byggd för "
            "svensk B2B från början, inte lokaliserad i efterhand."
        ),
    },
    {
        "title": "Sparas kvittona som laddas upp till bokföringsagenten?",
        "category": "teknisk_support",
        "content": (
            "Nej. Filen finns i minnet under själva avläsningen och kastas sedan. Kvar "
            "blir de avlästa fälten och ett kontrollsummevärde som gör att samma "
            "kvitto känns igen om det laddas upp två gånger. Originalet ska arkiveras "
            "i kundens eget system — bokföringslagen lägger det ansvaret på den som "
            "för bokföringen."
        ),
    },
    {
        "title": "Vad händer med kundens egen kunddata",
        "category": "ovrigt",
        "content": (
            "Kundens data är kundens. Varje arbetsyta är avskild i databasen med "
            "radsäkerhet — en spärr i databasen själv, inte bara i koden ovanpå. "
            "Kunddata blir aldrig publik och delas aldrig med andra kunder.\n\n"
            "Innehållet i ett kundmejl skickas till den AI-leverantör som driver "
            "modellen, för att svaret ska kunna skrivas. Vilken leverantör det är och "
            "var behandlingen sker står i integritetspolicyn på /integritetspolicy — "
            "underleverantörerna räknas upp med namn. För kontouppgifter är Snajp "
            "personuppgiftsansvarig; för kunddatan i produkten är kunden ansvarig och "
            "Snajp biträde under ett personuppgiftsbiträdesavtal. Den rättsliga "
            "grunden för B2B-prospektering är berättigat intresse, och varje utskick "
            "bär en avregistreringslänk som fungerar med ett klick."
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
