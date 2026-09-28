"""Kunskapsbas för Livrustning AB.

Källa: Livrustnings nya webbplats (livrustning.vercel.app, som ersätter
livrustning.se vid lansering), läst 2026-09-19. Sajtens egna fakta bor i
Umea-Webbdesign-repot, kunder/livrustning/src/lib/site.ts, och bygger på den
gamla sajten, kundens PDF:er om Säkerhetsdag och eHLR-Event samt besked från
Sebbe.

Utbytt mot versionen från 2026-08-05 (gamla Wix-sajten), som hade fel på tre
punkter som agenten annars hade upprepat för kundens räkning: telefonnumret
08-972247, adressen i Nacka, och webbutiken hjartstartarbutiken.com med dess
köpvillkor, frakt och garantier — Livrustning säljer inte hjärtstartare längre.
Krisstöd och distanskurser i brand står inte på nya sajten och är därför borta.
Kundlistan på sajten är ett FÖRSLAG som Livrustning inte godkänt, så den står
inte här.

Agenten får enligt sin grundningsregel bara svara utifrån dessa artiklar.
Formuleras något om här ändras alltså vad agenten påstår för kundens räkning —
ändra inte siffror, tider eller gruppstorlekar utan att stämma av med kunden.
När sajten ändras: skanna den från Kunskapsbas-vyn (POST /api/kb/skanna) i
stället för att skriva av den här.
"""

KB_ARTICLES: list[dict] = [
    # -- Företaget ----------------------------------------------------------
    {
        "title": "Om Livrustning",
        "category": "ovrigt",
        "content": (
            "Livrustning AB (org.nr 556824-9022) är ett utbildningsföretag inom HLR, första "
            "hjälpen och brand, med bas i Stockholm, Umeå och Nerja i Spanien. Vi har över 30 "
            "års erfarenhet, utbildar cirka 2 000 deltagare per år och är en av Sveriges "
            "ledande leverantörer av kurser i HLR och första hjälpen. Vi kommer till er och "
            "utbildar över hela Sverige, oavsett om det gäller ett event för hela personalen "
            "eller en klassisk kurs i en mindre grupp. Allt kursinnehåll följer gällande "
            "lagstiftning och Svenska HLR-rådets riktlinjer. Vårt mål är trygghet där ni "
            "lever och arbetar."
        ),
    },
    {
        "title": "Kontaktuppgifter",
        "category": "ovrigt",
        "content": (
            "E-post: kontakt@livrustning.se. Telefon: 070-733 32 54. Adress: Livrustning AB, "
            "Hökaren 49, 907 88 Täfteå. Org.nr 556824-9022. Vi finns i Stockholm, Umeå och "
            "Nerja och utbildar över hela Sverige. Vid en förfrågan: skriv gärna hur många ni "
            "är, var ni finns och vilket datum ni önskar, så kan vi skicka en offert direkt. "
            "Livrustning finns också på Facebook och Instagram."
        ),
    },
    {
        "title": "Säljer ni hjärtstartare?",
        "category": "ovrigt",
        "content": (
            "Nej, Livrustning säljer inte hjärtstartare. Vi utbildar i HLR med hjärtstartare, "
            "och på en Säkerhetsdag lär ni er exakt hur er egen hjärtstartare fungerar. Vi "
            "hjälper också arbetsplatser att bli en Hjärtsäker zon: utbildning, rutiner, "
            "rekommendationer om placering och skyltning, och registrering av hjärtstartaren "
            "i Sveriges Hjärtstartarregister."
        ),
    },
    # -- Utbildningar -------------------------------------------------------
    {
        "title": "Utbildningarna — vilken passar er?",
        "category": "utbildning",
        "content": (
            "Vi har fyra upplägg, från två timmar till en halvdag. Säkerhetsdag: 4 timmar hos "
            "er med brand, HLR och första hjälpen i fyra stationer — för arbetsplatser som vill "
            "täcka allt på en och samma dag. eHLR-Event: 2 timmar hos er, obegränsat antal "
            "deltagare, hela personalen utbildad i HLR med hjärtstartare — passar på kick-off, "
            "planeringsdag eller personalmöte. eHLR och eFörstaHjälpen: digitalt lärande och "
            "praktisk träning med ett års access — för verksamheter där alla inte kan vara på "
            "samma plats samtidigt. Kurser på plats: klassiska kurser i HLR, första hjälpen och "
            "brand i små grupper med instruktör, max 12 deltagare (20 för brand). Allt följer "
            "Svenska HLR-rådets riktlinjer."
        ),
    },
    {
        "title": "Säkerhetsdag — brand, HLR och första hjälpen på 4 timmar",
        "category": "utbildning",
        "content": (
            "Säkerhetsdagen är en halvdag, 4 timmar, hos er på ett datum ni väljer. Deltagarna "
            "delas in i fyra grupper som roterar mellan fyra stationer, med en instruktör per "
            "station. Station 1, brand teori: arbetsplatsens vanligaste brandrisker och hur ni "
            "förebygger dem, hur en brand utvecklas, riskerna med rök och brandgaser och hur ni "
            "agerar vid brandlarm. Station 2, brand praktik: släckövning inomhus med modern "
            "övningsutrustning. Station 3, HLR med hjärtstartare: kontrollera medvetande och "
            "andning, hjärt-lungräddning och att larma rätt, med övning på dockor och genomgång "
            "av er egen hjärtstartare. Station 4, första hjälpen: säkerhet på olycksplats, "
            "medvetandekontroll, stabilt sidoläge, luftvägsstopp, sår och brännskador, "
            "cirkulationssvikt och akuta sjukdomstillstånd. Schema: gemensam start 15 minuter i "
            "storsal med storbildsskärm, fyra pass om 45 minuter, 20 minuters kaffepaus efter "
            "andra passet, och avslutning med sammanfattning och tips på appar för första "
            "hjälpen. Är ni många anpassar vi antalet instruktörer så att alla får öva."
        ),
    },
    {
        "title": "eHLR-Event — hela personalen i HLR på 2 timmar",
        "category": "utbildning",
        "content": (
            "eHLR-Event utbildar hela personalen i HLR med hjärtstartare på 2 timmar, hos er "
            "när ni vill, med obegränsat antal deltagare. Upplägg: 50 minuters gemensam start "
            "där två instruktörer leder en interaktiv genomgång på storskärm med eHLR-metoden "
            "och alla svarar på kunskapsfrågor; 25 minuters praktisk träning där ena halvan "
            "övar HLR och hjärtstartare på övningsdockor med LED-feedback; 25 minuter där "
            "grupperna byter och andra halvan övar luftvägsstopp samt kontroll av medvetande "
            "och andning; 10 minuters avslutning och frågestund. Antalet instruktörer anpassas "
            "efter hur många ni är. Passar bra på kick-off eller planeringsdag."
        ),
    },
    {
        "title": "Intyg efter utbildningen",
        "category": "utbildning",
        "content": (
            "Efter eHLR-Event får deltagarna en länk till ett digitalt slutprov via e-post. När "
            "provet är godkänt laddar var och en ner sitt personliga utbildningsintyg. "
            "Företaget får ett samlingsintyg över alla som gått utbildningen."
        ),
    },
    {
        "title": "eHLR och eFörstaHjälpen — digitalt och praktiskt",
        "category": "utbildning",
        "content": (
            "eHLR® och eFörstaHjälpen kombinerar digitalt lärande med praktisk träning på "
            "LED-docka och träningshjärtstartare, så ni behöver inte samla alla på samma plats "
            "samtidigt. Ni får ett års full arbetsplatsaccess, så alla kan gå tillbaka och "
            "repetera när som helst. Fördelar: låg kostnad och ett prisvärt sätt att utbilda "
            "många; var och en i sin takt eller tillsammans i grupp; LED-dockan visar direkt "
            "hur det går; utbildningen finns på flera språk; mindre resor för både deltagare "
            "och instruktörer. eHLR är utvecklat av Livrustning tillsammans med "
            "utbildningsföretaget Nice To Be Alive AB. Berätta hur många ni är och hur er "
            "verksamhet ser ut, så föreslår vi ett upplägg och skickar en offert."
        ),
    },
    {
        "title": "Kurser på plats — HLR, första hjälpen och brand",
        "category": "utbildning",
        "content": (
            "Vill ni hellre ha en traditionell kurs kommer våra instruktörer ut till er när det "
            "passar er verksamhet. För bästa pedagogik har varje kurstillfälle ett tak: HLR med "
            "hjärtstartare högst 12 deltagare, Första hjälpen högst 12 deltagare, Brand högst 20 "
            "deltagare. Då får alla tid att öva med instruktören. Allt kursinnehåll följer "
            "gällande lagstiftning och Svenska HLR-rådets riktlinjer."
        ),
    },
    # -- Bokning, pris och praktiskt -----------------------------------------
    {
        "title": "Så bokar ni en utbildning",
        "category": "utbildning",
        "content": (
            "1. Ni hör av er via kontakt@livrustning.se eller 070-733 32 54 och berättar ungefär "
            "hur många ni är, var ni finns och när det skulle passa. 2. Ni får en offert med ett "
            "tydligt förslag på upplägg. 3. Instruktörerna kommer till er arbetsplats på det "
            "datum ni valt. Ni ordnar en lokal, och en storskärm om ni valt Säkerhetsdag eller "
            "eHLR-Event. 4. Alla övar på riktigt: kort teori och mycket praktik på dockor och "
            "träningshjärtstartare."
        ),
    },
    {
        "title": "Vad kostar det? Pris och offert",
        "category": "betalning",
        "content": (
            "Vi har inga fasta priser på webbplatsen. Priset beror på antal deltagare, vilken "
            "utbildning ni väljer och var i Sverige ni finns. Hör av er med de uppgifterna till "
            "kontakt@livrustning.se eller 070-733 32 54, så skickar vi en offert."
        ),
    },
    {
        "title": "Hur många kan vara med, och var sker utbildningen?",
        "category": "utbildning",
        "content": (
            "På eHLR-Event obegränsat många. På Säkerhetsdag anpassar vi antalet instruktörer "
            "efter gruppen. Klassiska kurser har max 12 deltagare för HLR och första hjälpen och "
            "20 för brand. Utbildningen sker hos er, på er arbetsplats, på ett datum ni väljer. "
            "Vi utbildar över hela Sverige och har bas i Stockholm, Umeå och Nerja i Spanien."
        ),
    },
    {
        "title": "Avboka eller boka om en utbildning",
        "category": "utbildning",
        "content": (
            "Avbokning och ombokning av en bokad utbildning hanterar vi personligen. Skriv till "
            "kontakt@livrustning.se eller ring 070-733 32 54 och ange vilken utbildning och vilket "
            "datum det gäller, så hjälper en av oss dig."
        ),
    },
    {
        "title": "Nöjdhetsgaranti",
        "category": "garanti",
        "content": (
            "Skulle ni inte bli nöjda gäller vår 100 % nöjdhetsgaranti på utbildningarna."
        ),
    },
    {
        "title": "Omdömen på Reco.se",
        "category": "ovrigt",
        "content": (
            "Våra kursdeltagare betygsätter oss på Reco.se, Sveriges största oberoende "
            "omdömessajt. Där har vi varit rekommenderade fem år i rad, och under flera år har "
            "vi haft Sveriges nöjdaste kursdeltagare i HLR och första hjälpen enligt Reco.se. "
            "Omdömena finns på reco.se/livrustning-ab."
        ),
    },
    # -- Hjärtsäker zon ------------------------------------------------------
    {
        "title": "Hjärtsäker zon enligt SS 280000",
        "category": "ovrigt",
        "content": (
            "Svensk standard SS 280000 beskriver vad som krävs för att en arbetsplats ska vara "
            "så hjärtsäker som möjligt. I en Hjärtsäker zon ska en person med hjärtstopp kunna "
            "få behandling med hjärtstartare inom 3 minuter. Standarden kräver också att det "
            "finns rutiner och beredskap för att hantera ett hjärtstopp och larma 112, att det "
            "finns kompetens i hjärt-lungräddning, att personalen vet var hjärtstartaren finns "
            "och kan använda den, och att hjärtstartaren är registrerad i Sveriges "
            "Hjärtstartarregister. Så hjälper vi er dit: utbildning i HLR med hjärtstartare "
            "enligt de nationella riktlinjerna, hjälp att ta fram rutiner för beredskap, larm "
            "och underhåll, rekommendationer om placering och skyltning, hjälp att registrera "
            "hjärtstartaren, planering av repetitionsutbildningar, och när standarden är "
            "uppfylld diplom, mallar och symboler att visa upp internt och externt. Berätta om "
            "er arbetsplats, så berättar vi hur ni kommer dit."
        ),
    },
    # -- Policyer -----------------------------------------------------------
    {
        "title": "Kvalitetspolicy",
        "category": "ovrigt",
        "content": (
            "Kvalitetspolicyn ingår i Livrustning AB:s systematiska arbetsmiljöarbete. "
            "Livrustning ska leverera kundanpassade utbildningar inom HLR och första hjälpen; "
            "arbeta målinriktat och systematiskt med ständiga förbättringar för kundnöjdhet och "
            "kundsäkerhet; följa aktuella lagar och krav; arbeta mot mätbara kvalitetsmål som "
            "följs upp löpande; följa Livrustnings riktlinjer för etik och kvalitet och de "
            "yrkesetiska riktlinjerna; behålla Sveriges nöjdaste kursdeltagare i HLR och första "
            "hjälpen enligt Reco.se; visa respekt, engagemang, omtanke och intresse i mötet med "
            "kunden; och sträva efter att överträffa kundens förväntan."
        ),
    },
    {
        "title": "Miljöpolicy",
        "category": "ovrigt",
        "content": (
            "Målet med miljöarbetet är att främja god hälsa och verka för en hälsosam miljö, "
            "med Miljöbalkens allmänna hänsynsregler som grund. Instruktören åker vanligtvis "
            "till kunden i stället för att alla deltagare reser till oss. I Stockholmsområdet "
            "används elbil, och i övriga landet samarbetar vi med lokala instruktörer med kort "
            "avstånd till utbildningsplatsen. Det digitala formatet eHLR är utvecklat för att "
            "minska miljöpåverkan. Vi har skriftliga rutiner för inköp och produktval, hantering "
            "av smittförande avfall och gods, och användning av kemiska produkter. Livrustning "
            "är medlem i Miljö- och klimatpakten, Stockholms stads klimatnätverk. VD är ytterst "
            "miljöansvarig."
        ),
    },
    {
        "title": "Integritetspolicy och personuppgifter",
        "category": "ovrigt",
        "content": (
            "Personuppgiftsansvarig är Livrustning AB, org.nr 556824-9022, Hökaren 49, 907 88 "
            "Täfteå, kontakt@livrustning.se. Webbplatsen använder inga kakor för spårning eller "
            "marknadsföring och har inga formulär. Vi behandlar namn, e-post, telefon och det du "
            "skriver när du kontaktar oss; uppgifter om företaget, till exempel antal deltagare "
            "och ort, vid offertförfrågan; namn och e-post för kursdeltagare när det behövs för "
            "slutprov och intyg; och faktureringsuppgifter vid köp. Uppgifterna används för att "
            "svara på frågor, lämna offerter, genomföra utbildningar, utfärda intyg och "
            "fakturera, och sparas inte längre än ändamålet kräver (bokföringsuppgifter så "
            "länge bokföringslagen kräver). Du har rätt att få veta vilka uppgifter vi har om "
            "dig, få felaktiga uppgifter rättade och i vissa fall raderade eller begränsade — "
            "kontakta kontakt@livrustning.se. Klagomål kan lämnas till "
            "Integritetsskyddsmyndigheten (IMY)."
        ),
    },
]
