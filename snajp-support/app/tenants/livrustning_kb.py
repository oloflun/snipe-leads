"""Kunskapsbas för Livrustning AB.

Källor: livrustning.se (startsida, /kurser, /hjartsakerzon, /kvalitetspolicy,
/miljopolicy, /intigritetspolicy) hämtade 2026-08-05, samt kundens köpvillkor
för webbutiken hjartstartarbutiken.com.

Agenten får enligt sin grundningsregel bara svara utifrån dessa artiklar.
Formuleras något om här ändras alltså vad agenten påstår för kundens räkning —
ändra inte siffror, garantitider eller tidsramar utan att stämma av med kunden.

OBS motstridiga garantiuppgifter: produktgarantin i webbutiken är 1 år mot
tillverkningsfel, men Hjärtsäker zon-paketet anges med 8 års garanti på
livrustning.se. Båda står nedan med sin kontext, så agenten inte blandar ihop
dem. Detta bör kunden bekräfta.
"""

KB_ARTICLES: list[dict] = [
    # -- Företaget ----------------------------------------------------------
    {
        "title": "Om Livrustning AB",
        "category": "ovrigt",
        "content": (
            "Livrustning AB (org.nr 556824-9022) har mer än 30 års erfarenhet av "
            "säkerhetsutbildningar och har utbildat cirka 60 000 personer. Vi utbildar ungefär "
            "2 000 personer per år i hjärt-lungräddning och första hjälpen sedan 90-talet, "
            "vilket gör oss till en av de största leverantörerna i Sverige inom livräddning. "
            "Vi har verksamhet i Stockholm, Umeå och Nerja i Spanien och utbildar över hela "
            "landet. Vi har under många år haft Sveriges nöjdaste kursdeltagare i HLR och "
            "första hjälpen enligt rekommendationssajten Reco.se, baserat på över 780 "
            "omdömen. Vi är en oberoende leverantör av olika märken av hjärtstartare och "
            "aktiv medlem i Branschrådet för Hjärtstartare i Sverige. Vårt mål är att kunden "
            "ska känna trygghet på arbetsplatsen, i föreningslokalen och i hemmet."
        ),
    },
    {
        "title": "Kontaktuppgifter och adresser",
        "category": "ovrigt",
        "content": (
            "E-post: kontakt@livrustning.se. Telefon: 070-733 32 54 eller 08-972247. "
            "Postadress enligt integritetspolicyn: Rudsjövägen 112, 131 47 Nacka. "
            "Kurskontor: Hökaren 49, 907 88 Täfteå. Org.nr: 556824-9022. "
            "Hjärtstartare säljs via webbutiken hjartstartarbutiken.com. "
            "För offert på utbildning, ange gärna antal deltagare och plats."
        ),
    },
    # -- Utbildningar -------------------------------------------------------
    {
        "title": "Utbildningar — översikt och upplägg",
        "category": "utbildning",
        "content": (
            "Våra utbildningar ger kunskap att hjälpa familj eller arbetskollegor vid "
            "livshotande situationer som brand, hjärtstopp, stroke eller luftvägsstopp. "
            "Utbildningarna kan ske hos er eller i våra kurslokaler i centrala Stockholm. "
            "Vi erbjuder även digitala kurser som kan genomföras var som helst och när som "
            "helst, vilket gör att ni slipper samla alla deltagare på en viss plats vid en "
            "viss tid. De digitala kurserna passar företag, bostadsrättsföreningar, skolor "
            "och föreningar. Kontakta kontakt@livrustning.se för utbildningsförslag och offert."
        ),
    },
    {
        "title": "Första hjälpen och HLR med hjärtstartare",
        "category": "utbildning",
        "content": (
            "Hjärt-lungräddning (HLR) med hjärtstartare är grunden i våra utbildningar i "
            "första hjälpen. Kursen kan därefter få en inriktning som anpassas efter de "
            "vanligaste tillbuden hos er, till exempel luftvägsstopp, drunkningstillbud och "
            "fallskador. Vi har kurser för kontoret, byggarbetsplatsen, förskolan och "
            "bostadsföreningen. Utbildningen i HLR med hjärtstartare kan även genomföras "
            "digitalt som eHLR."
        ),
    },
    {
        "title": "eHLR och eFörstaHjälpen — digitala utbildningar",
        "category": "utbildning",
        "content": (
            "eHLR® och eFörstaHjälpen (L-ABCDE) är digitala utbildningar med praktisk "
            "träning, framtagna av Livrustning tillsammans med Nice To Be Alive AB som också "
            "säljer dem (nicetobealive.se). Kurserna är designade för att den anställde ska "
            "kunna genomföra dem på egen hand vid datorn, när arbetstiden tillåter — "
            "tillgängligt året om, dygnet runt. Fördelarna är låg kostnad, individuellt "
            "lärande, praktisk träning, flera språk och att formatet är klimatsmart. Eftersom "
            "kostnaden per deltagare är låg kan hela arbetsplatsen utbildas i stället för "
            "ett urval."
        ),
    },
    {
        "title": "Brandutbildning",
        "category": "utbildning",
        "content": (
            "Utbildningarna inom brand ger kunskap om hur man arbetar förebyggande mot brand "
            "och ökar förståelsen för vilka skador brand orsakar på liv, egendom och miljö. "
            "Vi går igenom hur brandrisker och skador kan reduceras. En praktisk del ingår "
            "där vi tränar med handbrandsläckare, och rutiner vid utrymningssituationer "
            "tränas också. Många av kurserna kan genomföras på distans."
        ),
    },
    {
        "title": "Krisstöd och krishantering",
        "category": "utbildning",
        "content": (
            "Det är viktigt att i förväg veta vad man bör göra vid en kris. Det kan handla om "
            "en tragisk händelse, en olycka, allvarlig sjukdom hos en medarbetare, eller "
            "omorganisation och nedskärningar. Med rätt förberedelse hanterar ni kriser så "
            "att verksamheten snabbt kan återgå till det normala. Kurserna kan genomföras på "
            "distans."
        ),
    },
    # -- Hjärtstartare ------------------------------------------------------
    {
        "title": "Hjärtstartare för hem, företag och förening",
        "category": "ovrigt",
        "content": (
            "Vi är återförsäljare av marknadens mest lättanvända hjärtstartare, som med tydlig "
            "rösthjälp på svenska leder användaren genom hela räddningsförloppet. Vi är en "
            "oberoende leverantör av flera märken och utrustar företag, föreningar och "
            "privatpersoner med lämplig CE-märkt hjärtstartare anpassad efter deras miljö. "
            "Används en hjärtstartare snabbt tillsammans med hjärt-lungräddning överlever de "
            "flesta som drabbas av hjärtstopp. Priser finns i webbutiken hjartstartarbutiken.com."
        ),
    },
    {
        "title": "Hjärtsäker zon enligt svensk standard SS280000",
        "category": "ovrigt",
        "content": (
            "Svensk standard SS280000 beskriver hur en hjärtstartare används och vad som krävs "
            "för att en plats ska vara en Hjärtsäker zon. Kraven är: det ska finnas rutiner och "
            "beredskap för att hantera ett hjärtstopp och larma 112; det ska finnas kompetens i "
            "hjärt-lungräddning så att hjälp omgående kan sättas in; personalen ska veta var "
            "hjärtstartaren finns och kunna hantera den; behandling med hjärtstartare ska kunna "
            "ske inom 3 minuter; och hjärtstartaren ska vara registrerad i Sveriges "
            "Hjärtstartarregister. Standarden kan laddas ner gratis."
        ),
    },
    {
        "title": "Vad ingår när Livrustning hjälper er bli Hjärtsäker zon",
        "category": "ovrigt",
        "content": (
            "Vi hjälper er att bli en Hjärtsäker zon genom: val av lämplig kvalitetssäkrad "
            "hjärtstartare utifrån er miljö; skyddsväska, vägghållare, nödskylt, andningsmask "
            "och rescue-kit som alltid ingår; 8 års garanti; gratis supportavtal; utbildning av "
            "medarbetare i HLR med hjärtstartare enligt de nationella riktlinjerna; "
            "rekommendation av skyltning och placering; hjälp att upprätta beredskaps-, larm- "
            "och underhållsrutiner; hjälp att registrera hjärtstartaren i Hjärtstartarregistret; "
            "kontakt från oss när det är dags att byta elektroder och batteri; planering av "
            "repetitionsutbildningar; diplom när standarden uppfyllts; mallar och symboler för "
            "att informera internt och externt om att ni är en hjärtsäker zon; återställning av "
            "hjärtstartaren om den använts vid en verklig händelse; samt gratis elektroder och "
            "eventuellt batteri efter användning i skarpt läge. De 8 årens garanti avser "
            "hjärtstartaren i detta paket — se artikeln om vilken garanti som gäller i vilken "
            "situation innan du svarar på en garantifråga."
        ),
    },
    # -- Köpvillkor (webbutiken) --------------------------------------------
    {
        "title": "Nöjdhetsgaranti",
        "category": "garanti",
        "content": "Vi lämnar 100 % nöjdhetsgaranti på våra utbildningar.",
    },
    {
        "title": "Ångerrätt och öppet köp",
        "category": "retur_reklamation",
        "content": (
            "Du har öppet köp och ångerrätt i 45 dagar vid köp i webbutiken. Varan ska vara "
            "oskadad och i originalförpackning. Kunden betalar returfrakten. Återbetalning sker "
            "inom 30 dagar."
        ),
    },
    {
        "title": "Reklamation av skadad vara",
        "category": "retur_reklamation",
        "content": (
            "Har varan kommit fram skadad ska reklamationen göras inom 7 dagar efter mottagen "
            "leverans. Kontakta kontakt@livrustning.se med ordernummer och gärna en bild på "
            "skadan."
        ),
    },
    {
        "title": "Garanti — vilken gäller i vilken situation",
        "category": "garanti",
        "content": (
            "Det finns tre olika saker som kunder ofta blandar ihop. Skilj på dem.\n\n"
            "1. GARANTI VID KÖP I WEBBUTIKEN: 1 år mot tillverkningsfel räknat från leverans. "
            "Detta är grundgarantin och gäller sortimentet generellt, till exempel tillbehör "
            "som elektroder, batterier, väskor och vägghållare. Villkoren anger att vissa "
            "produkter har längre garantitid.\n\n"
            "2. GARANTI I HJÄRTSÄKER ZON-PAKETET: 8 år. Detta anges på livrustning.se som en "
            "del av vad som ingår när Livrustning hjälper en kund att uppfylla standarden "
            "SS280000. Den avser hjärtstartaren i det paketet.\n\n"
            "3. REKLAMATIONSRÄTT: en lagstadgad rätt som gäller oberoende av garantin och som "
            "inte kan avtalas bort för konsumenter. Garanti är ett frivilligt åtagande "
            "utöver den. En kund vars produkt gått sönder kan alltså ha rätt till åtgärd även "
            "efter att garantitiden löpt ut.\n\n"
            "VIKTIGT: uppgifterna 1 år och 8 år kommer från olika källor och det är inte "
            "bekräftat exakt vilken garantitid som gäller för en enskild hjärtstartare köpt "
            "lös i webbutiken. Ange därför ALDRIG en garantitid för en specifik produkt på "
            "eget bevåg. Fråga kunden vad som köpts och när, och eskalera till en medarbetare "
            "så fort svaret beror på vilken produkt eller vilket paket det gäller."
        ),
    },
    {
        "title": "Undantag från garantin",
        "category": "garanti",
        "content": (
            "Garantin omfattar inte skador orsakade av blixtnedslag eller strömfel, ingrepp i "
            "apparaten, felaktig inkoppling, slitage eller ovarsam hantering. Tillverkaren har "
            "rätt till upp till tre reparationsförsök innan byte av produkt krävs. Undantagen "
            "gäller garantin — de påverkar inte kundens lagstadgade reklamationsrätt, och ett "
            "ärende där kunden ifrågasätter ett avslag ska alltid gå till en medarbetare."
        ),
    },
    {
        "title": "Frakt och leverans",
        "category": "leverans",
        "content": (
            "Fraktkostnaden är 95 kr exklusive moms inom Sverige. Leveranstiden är 1–3 "
            "arbetsdagar och vi skickar med DHL eller UPS. Paket som inte hämtas ut debiteras "
            "295 kr. Hjärtstartare levereras direkt från generalagenten för att minska "
            "fraktens miljöpåverkan."
        ),
    },
    {
        "title": "Betalning, faktura och delbetalning",
        "category": "betalning",
        "content": (
            "Faktura med 30 dagars netto gäller för företag, kommun och skola. För "
            "privatpersoner, föreningar och stiftelser är betalningstiden 10 dagar. Vi tar "
            "ingen fakturaavgift. Delbetalning erbjuds räntefritt på 3, 6 eller 12 månader, "
            "eller på 24 månader med 9,95 % ränta."
        ),
    },
    {
        "title": "Priser och offert",
        "category": "ovrigt",
        "content": (
            "Utbildningar prissätts via offert eftersom priset beror på antal deltagare och "
            "plats. Priser på hjärtstartare finns i webbutiken hjartstartarbutiken.com. Begär "
            "offert via kontakt@livrustning.se eller ring 08-972247 / 070-733 32 54."
        ),
    },
    {
        "title": "Tvist och reklamationsnämnd",
        "category": "ovrigt",
        "content": (
            "Tvister avgörs enligt svensk lag. Vi följer Allmänna reklamationsnämndens (ARN) "
            "rekommendationer."
        ),
    },
    # -- Policyer -----------------------------------------------------------
    {
        "title": "Kvalitetspolicy",
        "category": "ovrigt",
        "content": (
            "Kvalitetspolicyn ingår i Livrustning AB:s systematiska arbetsmiljöarbete. "
            "Livrustning ska leverera kundanpassade utbildningar inom HLR och första hjälpen "
            "samt utrusta företag, föreningar och privatpersoner med lämplig CE-märkt "
            "hjärtstartare anpassad efter deras miljö. Vi arbetar målinriktat och systematiskt "
            "med ständiga förbättringar för ökad kundtillfredsställelse och kundsäkerhet, "
            "följer aktuella lagar och krav, arbetar mot mätbara kvalitetsmål som följs upp "
            "löpande, och följer Livrustnings riktlinjer för etik och kvalitet samt de "
            "yrkesetiska riktlinjerna. Vi arbetar för att bibehålla Sveriges nöjdaste "
            "kursdeltagare i HLR och första hjälpen enligt Reco.se, och strävar efter att "
            "överträffa kundens förväntan."
        ),
    },
    {
        "title": "Miljöpolicy",
        "category": "ovrigt",
        "content": (
            "Det övergripande målet med miljöarbetet är att främja god hälsa och verka för en "
            "hälsosam miljö. Miljöbalkens allmänna hänsynsregler utgör grunden. Instruktören "
            "åker vanligtvis till kunden i stället för att alla deltagare reser till våra "
            "lokaler, och väljer det miljömässigt bästa transportalternativet. I "
            "Stockholmsområdet används elbil, och i övriga landet samarbetar vi med lokala "
            "instruktörer med kort avstånd till utbildningsplatsen. Det digitala formatet eHLR "
            "utvecklades tillsammans med Nice To Be Alive AB för att minska miljöpåverkan. "
            "Hjärtstartare levereras direkt från generalagenten. Livrustning har skriftliga "
            "rutiner för inköp och produktval, hantering av smittförande avfall och användning "
            "av kemiska produkter, och är medlem i Miljö- och Klimatpakten, ett klimatnätverk "
            "från Stockholms stad. VD är ytterst miljöansvarig."
        ),
    },
    {
        "title": "Integritetspolicy och personuppgifter",
        "category": "ovrigt",
        "content": (
            "Livrustning AB, org.nr 556824-9022, Rudsjövägen 112, 131 47 Nacka, är "
            "personuppgiftsansvarig. Vi samlar in personuppgifter när du genomför ett köp, "
            "använder vår support, besöker webbplatsen eller deltar i en utbildning. De "
            "uppgifter som behandlas är namn och identifikationsnummer, adress, telefonnummer "
            "och e-post, betalningsuppgifter, kundnummer samt IP-adress och information om hur "
            "du använder webbplatsen. Uppgifterna används för att fullgöra våra förpliktelser "
            "som köp, fakturering och support, för kundvård, för marknadsföring, för att "
            "bedöma betalningsmetoder, för att förbättra vårt erbjudande, för att förhindra "
            "bedrägerier och för att följa lagstiftning som bokföringslagen. Grunderna är "
            "avtal, intresseavvägning och rättslig förpliktelse. Känsliga personuppgifter "
            "behandlas inte med stöd av intresseavvägning och ingen profilering sker på den "
            "grunden. Du kan när som helst kontakta oss för att uppdatera eller radera dina "
            "uppgifter. Begäran om radering hanteras av personuppgiftsansvarig."
        ),
    },
]
