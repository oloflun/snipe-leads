"""Svensk kunskapsbas för den fiktiva e-handeln Nordlys Handel.

Används både av seed-skriptet (Postgres) och in-memory-lagringen, så att
demon alltid har samma innehåll oavsett lagringsläge.
"""

# G8: den PUBLIKA, oautentiserade demons kunskapsbas — om Snajp själv, inte
# om en fiktiv kund. Egen tenant (PUBLIC_DEMO_TENANT_ID), delar ingenting
# med Nordlys Handel eller en betalande kund.
DEMO_KB_ARTICLES: list[dict] = [
    {
        "title": "Vad är Snajp?",
        "category": "ovrigt",
        "content": (
            "Snajp bygger AI-agenter för svensk kundsupport och B2B-leads. "
            "Supportagenten svarar kunder grundat i företagets egen kunskapsbas "
            "och eskalerar till en människa när underlag saknas. Leads-agenten "
            "researchar prospekt och skriver signalbaserade, lågmälda utskick — "
            "aldrig massutskick."
        ),
    },
    {
        "title": "Hur fungerar supportagenten?",
        "category": "ovrigt",
        "content": (
            "Agenten läser en kunds kunskapsbas, klassificerar ärendet, och svarar "
            "ENBART grundat i den kunskapsbasen. Saknas svar eskalerar den till en "
            "människa i stället för att gissa. Den här demon visar samma "
            "resonemang, men utan att skapa ett riktigt ärende eller spara något."
        ),
    },
    {
        "title": "Är den här demon kopplad till en riktig kund?",
        "category": "ovrigt",
        "content": (
            "Nej. Demon körs i ett isolerat läge utan kunddata, utan ärende- eller "
            "kundregistrering, och utan möjlighet att skicka något. Den är till för "
            "att visa hur agenten resonerar, inte för att testa en riktig "
            "integration."
        ),
    },
]

KB_ARTICLES: list[dict] = [
    {
        "title": "Inloggningsproblem och återställning av lösenord",
        "category": "teknisk_support",
        "content": (
            "Om du inte kan logga in: kontrollera att du använder den e-postadress du "
            "registrerade kontot med. Klicka på 'Glömt lösenord?' på inloggningssidan så "
            "skickas en återställningslänk inom 5 minuter. Länken är giltig i 24 timmar. "
            "Hittar du inget mail — titta i skräpposten. Efter fem misslyckade försök låses "
            "kontot i 15 minuter av säkerhetsskäl."
        ),
    },
    {
        "title": "Felkoder i kassan (E-101, E-204, E-500)",
        "category": "teknisk_support",
        "content": (
            "E-101 betyder att sessionen har gått ut — ladda om sidan och försök igen. "
            "E-204 betyder att en vara i kundvagnen tagit slut i lagret; ta bort varan och "
            "fortsätt. E-500 är ett tillfälligt serverfel — vänta några minuter och försök "
            "igen. Kvarstår felet, skicka gärna en skärmdump till supporten så felsöker vi."
        ),
    },
    {
        "title": "Appen eller webbplatsen fungerar inte som den ska",
        "category": "teknisk_support",
        "content": (
            "Börja med att tömma webbläsarens cache eller uppdatera appen till senaste "
            "versionen. Vi stödjer de två senaste versionerna av Chrome, Safari, Edge och "
            "Firefox. Vid vita sidor eller knappar som inte reagerar hjälper det ofta att "
            "logga ut och in igen. Bifoga gärna en skärmdump med synligt felmeddelande när "
            "du kontaktar oss."
        ),
    },
    {
        "title": "Leveranstider och fraktalternativ",
        "category": "leverans",
        "content": (
            "Standardfrakt tar 2–4 vardagar inom Sverige och är gratis över 499 kr, annars "
            "49 kr. Expressfrakt (1 vardag, beställ före kl 14) kostar 99 kr. Vi skickar med "
            "PostNord och Instabox. Till Norge, Danmark och Finland tar leveransen 3–6 "
            "vardagar. Du får ett spårningsnummer via mail när paketet lämnar lagret."
        ),
    },
    {
        "title": "Försenat eller försvunnet paket",
        "category": "leverans",
        "content": (
            "Om spårningen inte uppdaterats på 3 vardagar kan paketet vara försenat hos "
            "transportören. Kontrollera först spårningslänken i ditt leveransmail. Har det "
            "gått mer än 7 vardagar sedan beställningen startar vi en efterlysning hos "
            "transportören, vilket tar 1–3 vardagar. Paket som inte hämtas ut returneras "
            "efter 14 dagar och beställningen återbetalas minus fraktkostnad."
        ),
    },
    {
        "title": "Ändra leveransadress på en lagd beställning",
        "category": "leverans",
        "content": (
            "Leveransadressen kan ändras fram tills paketet lämnat vårt lager — oftast inom "
            "2 timmar från beställning. Gå till Mina sidor → Beställningar → Ändra adress, "
            "eller kontakta supporten med ditt ordernummer. Har paketet redan skickats kan "
            "du i PostNords app styra om det till ett annat ombud."
        ),
    },
    {
        "title": "Betalningsmetoder vi accepterar",
        "category": "betalning",
        "content": (
            "Vi accepterar kortbetalning (Visa, Mastercard), Swish, Klarna faktura och "
            "Klarna delbetalning. Fakturan från Klarna har 30 dagars betalningstid. Vid "
            "delbetalning väljer du plan direkt i kassan. Alla priser visas inklusive moms."
        ),
    },
    {
        "title": "Dubbeldragning eller felaktig debitering",
        "category": "betalning",
        "content": (
            "Ser du två dragningar för samma köp är den ena oftast en reservation som "
            "släpps automatiskt inom 3–5 bankdagar — kontrollera om beloppet är bokfört "
            "eller reserverat. Om båda dragningarna bokförs korrigerar vi det omgående när "
            "du hör av dig med ordernummer och datum. Ärenden som gäller återbetalning av "
            "pengar hanteras alltid av en medarbetare."
        ),
    },
    {
        "title": "Faktura från Klarna — förfallodatum och påminnelser",
        "category": "betalning",
        "content": (
            "Klarna skickar fakturan via mail samma dag som paketet skickas. Betalningstid "
            "är 30 dagar. Behöver du flytta förfallodatumet görs det enklast i Klarna-appen. "
            "Påminnelseavgifter hanteras av Klarna, men hör av dig till oss om något blivit "
            "fel med ordern så pausar vi fakturan under utredningen."
        ),
    },
    {
        "title": "Så gör du en retur",
        "category": "retur_reklamation",
        "content": (
            "Du har 30 dagars öppet köp. Starta returen på Mina sidor → Beställningar → "
            "Returnera, skriv ut retursedeln och lämna paketet hos närmaste ombud. Returen "
            "är gratis. När returen nått vårt lager tar återbetalningen 5–10 bankdagar till "
            "samma betalsätt som vid köpet. Varan ska vara oanvänd och i originalförpackning."
        ),
    },
    {
        "title": "Reklamation av skadad eller defekt vara",
        "category": "retur_reklamation",
        "content": (
            "Har varan kommit fram skadad eller slutat fungera? Skicka en bild på skadan "
            "tillsammans med ordernumret så behandlar vi reklamationen inom 2 vardagar. Vid "
            "godkänd reklamation väljer du mellan ny vara eller återbetalning. Synliga "
            "transportskador ska anmälas inom 7 dagar från leverans. Reklamationsrätten "
            "gäller i 3 år enligt konsumentköplagen."
        ),
    },
    {
        "title": "Ångra eller ändra en beställning",
        "category": "retur_reklamation",
        "content": (
            "En beställning kan avbrytas kostnadsfritt fram tills den plockas i lagret, "
            "oftast inom 1–2 timmar. Därefter går det alltid bra att neka paketet vid "
            "leverans eller göra en vanlig retur inom 30 dagar. Kontakta supporten med "
            "ordernumret så hjälper vi dig."
        ),
    },
    {
        "title": "Orderstatus och orderbekräftelse",
        "category": "orderstatus",
        "content": (
            "Direkt efter köpet skickas en orderbekräftelse via mail — kommer den inte inom "
            "15 minuter, kontrollera skräpposten. Under Mina sidor → Beställningar ser du "
            "alltid aktuell status: Mottagen, Packas, Skickad eller Levererad. När ordern "
            "skickas får du ett spårningsnummer. En order kan ändras eller avbrytas fram "
            "tills den packas, oftast inom 1–2 timmar från beställning."
        ),
    },
    {
        "title": "Uppdatera kontouppgifter och adress",
        # Facket "konto" togs bort ur CATEGORIES när taxonomin lades om, men
        # artiklarna följde inte med. Databasens check-villkor avvisar därför
        # raden, och eftersom seedningen avbryts på första felet fick demo-
        # tenanten INGEN kunskapsbas alls i Postgres-läge.
        # Migrationen som tog bort facket flyttade befintliga rader till
        # teknisk_support (där inloggnings- och kontofrågor hamnar) — samma
        # mappning används här.
        "category": "teknisk_support",
        "content": (
            "Under Mina sidor → Inställningar ändrar du namn, e-postadress, telefonnummer "
            "och sparade adresser. Byter du e-postadress skickas en bekräftelselänk till den "
            "nya adressen. Sparade kort hanteras av vår betalpartner och kan tas bort under "
            "Betalning → Sparade kort."
        ),
    },
    {
        "title": "Radera konto och personuppgifter (GDPR)",
        # GDPR-ärenden tvingas ändå alltid till människa av eskaleringsreglerna,
        # så facket styr bara var artikeln går att hitta. "ovrigt" är rätt plats
        # för en allmän policytext.
        "category": "ovrigt",
        "content": (
            "Du kan begära ett registerutdrag eller radering av dina personuppgifter enligt "
            "GDPR. Begäran om radering hanteras alltid manuellt av vår personuppgifts-"
            "ansvariga och bekräftas inom 30 dagar. Orderhistorik som krävs enligt "
            "bokföringslagen sparas i 7 år även efter radering."
        ),
    },
    {
        "title": "Nyhetsbrev och kampanjkoder",
        "category": "ovrigt",
        "content": (
            "Kampanjkoder anges i kassan i fältet 'Rabattkod' och kan inte kombineras. "
            "Koden dras innan frakt beräknas. Nyhetsbrevet avregistrerar du via länken "
            "längst ner i varje utskick. Välkomstrabatten på 10 % gäller första köpet och "
            "i 30 dagar från registrering."
        ),
    },
]

# Sex artiklar tillagda 2026-08-21, valda ur DEMONS EGNA MEJL och inte ur en
# föreställning om vad en kunskapsbas brukar innehålla. Sex av de tolv
# besvarbara i email_pipeline/connectors/mock.py saknade underlag här —
# öppettider, garanti, utbildning, ombud/hemleverans och kvitto — och utan
# träff i basen tvingar grundningsregeln (processor.py steg 2) fram en
# eskalering. Alltså blev hälften av demons inkorg röd av en lucka i texten,
# inte av något agenten gjorde.
#
# Facken måste ligga i config.CATEGORIES, annars faller
# ss_knowledge_base_category_check vid insert. `garanti` och `utbildning`
# fanns i listan men hade noll artiklar.
KB_ARTICLES += [
    {
        "title": "Om Nordlys Handel",
        "category": "ovrigt",
        "content": (
            "Nordlys Handel är en svensk e-handel för hem och utemiljö: förvaring, "
            "belysning, textil, krukor och trädgårdsredskap. Vi har lager i Jönköping "
            "och en butik i Göteborg. Vi säljer både till privatpersoner och till "
            "företag — företagskunder kan handla mot faktura efter kreditprövning. "
            "Sortimentet är cirka 4 000 artiklar och vi lagerhåller allt själva, "
            "vilket är varför leveranstiden är densamma oavsett årstid."
        ),
    },
    {
        "title": "Öppettider och kontaktvägar",
        "category": "ovrigt",
        "content": (
            "Kundtjänst har öppet vardagar 09–16 och nås på hej@nordlyshandel.se eller "
            "031-123 45 67. Butiken i Göteborg har öppet vardagar 10–18 och lördagar "
            "11–15. Butiken är STÄNGD på söndagar och på röda dagar, samt på "
            "midsommarafton, julafton och nyårsafton. Dagen före röd dag stänger både "
            "butik och kundtjänst kl 13. Webbutiken tar emot beställningar dygnet runt, "
            "men order lagda efter kl 14 packas nästa vardag."
        ),
    },
    {
        "title": "Garanti: hur länge den gäller och vad den täcker",
        "category": "garanti",
        "content": (
            "Du har tre års reklamationsrätt enligt konsumentköplagen på allt vi säljer. "
            "Utöver det lämnar vi två års produktgaranti på belysning och elektriska "
            "produkter, räknat från leveransdatum. Garantin täcker fel som fanns vid "
            "leveransen eller uppstår vid normal användning: trasig elektronik, "
            "sprickor i material, ytbehandling som släpper. Den täcker INTE normalt "
            "slitage, frostskador på utomhuskrukor som stått ute över vintern, eller "
            "skada efter felaktig montering. Vid garantiärende behöver vi ordernummer "
            "och en bild på felet — då skickar vi ny vara eller återbetalar."
        ),
    },
    {
        "title": "Utbildning och introduktion för företagskunder",
        "category": "utbildning",
        "content": (
            "Företagskunder får en kostnadsfri genomgång av beställningsportalen: 45 "
            "minuter på plats eller digitalt, upp till tio deltagare per tillfälle. Den "
            "täcker inköpsflödet, kostnadsställen, återkommande order och hur man "
            "hämtar underlag till bokföringen. Boka via hej@nordlyshandel.se med "
            "önskat datum och antal deltagare — vi återkommer inom två vardagar. Har "
            "ni fler än tio deltagare delar vi upp det på flera tillfällen, eftersom "
            "genomgången bygger på att alla hinner logga in och prova själva."
        ),
    },
    {
        "title": "Ombud eller hemleverans",
        "category": "leverans",
        "content": (
            "Du väljer själv i kassan. Ombud är standard och ingår i fraktpriset: "
            "PostNord eller Instabox, och du får en avisering när paketet finns att "
            "hämta. Hemleverans till dörren kostar 79 kr extra och bokas med tidsfönster "
            "kvällstid 17–21 — transportören sms:ar dagen innan. Skrymmande varor över "
            "20 kg, till exempel större krukor och möbler, skickas ALLTID som "
            "hemleverans och då utan extra avgift. Paket hos ombud ligger kvar i 14 "
            "dagar innan de returneras."
        ),
    },
    {
        "title": "Kvitto och faktura för bokföringen",
        "category": "betalning",
        "content": (
            "Kvittot ligger som PDF under Mina sidor → Beställningar → Ladda ner kvitto, "
            "och går att hämta hur många gånger som helst. Det är ett fullständigt "
            "underlag: organisationsnummer, momssats och momsbelopp specificerat per "
            "rad. Handlade du utan konto skickar vi kvittot på nytt om du mejlar "
            "ordernummer till hej@nordlyshandel.se. Företagskunder som handlar mot "
            "faktura får underlaget som e-faktura eller PDF, och kan lägga till "
            "referens eller kostnadsställe i kassan så att det följer med på fakturan."
        ),
    },
    # --- Påfyllnad 2026-08-22: garanti, utbildning och orderstatus hade EN
    # artikel var. Följden var mätbar i dev: ett garantiärende hamnade i
    # teknisk_support och en utbildningsfråga i ovrigt, eftersom
    # grundningsregeln (processor.py steg 2) styr klassificeringen mot det fack
    # där det finns täckning. Facken fanns alltså i menyn men fylldes aldrig,
    # och en kund som klickade dit såg en tom inkorg.
    {
        "title": "Garanti efter reparation eller utbyte",
        "category": "garanti",
        "content": (
            "Vid en garantireparation löper den ursprungliga garantitiden vidare från "
            "köpdatumet — den börjar alltså inte om. Får du en helt ny vara i utbyte "
            "startar en ny garantitid från leveransdagen på den nya varan. Reparerade "
            "delar har alltid minst tre månaders garanti från reparationsdatumet, även "
            "om den ursprungliga garantin skulle löpa ut dessförinnan."
        ),
    },
    {
        "title": "Garanti vid köp hos återförsäljare",
        "category": "garanti",
        "content": (
            "Garantin följer varan och gäller även om du köpt hos en av våra "
            "återförsäljare. Reklamationen gör du i första hand hos butiken du köpte "
            "av, eftersom det är de som har ditt köpavtal. Får du inte hjälp där tar "
            "vi över ärendet — skicka kvitto eller ordernummer från butiken så löser "
            "vi det direkt med dem."
        ),
    },
    {
        "title": "Utbildningens upplägg: på plats eller digitalt",
        "category": "utbildning",
        "content": (
            "Introduktionen hålls antingen digitalt (90 minuter, upp till 15 deltagare) "
            "eller på plats hos er (en halvdag, upp till 8 deltagare för att alla ska "
            "hinna prova själva). Digitalt går att boka med två veckors varsel, på plats "
            "brukar kräva fyra. Vi spelar in den digitala varianten om ni vill kunna "
            "visa den för nyanställda senare."
        ),
    },
    {
        "title": "Förberedelser inför en utbildning",
        "category": "utbildning",
        "content": (
            "Vi skickar ett kort underlag en vecka innan: en översikt på två sidor och "
            "tre korta filmer. Deltagare som hunnit titta får ut mer av tiden, eftersom "
            "vi då kan ägna passet åt era egna fall i stället för åt grunderna. Har ni "
            "specifika frågor ni vill ha med, mejla dem i förväg så bygger vi in dem."
        ),
    },
    {
        "title": "Ändra eller komplettera en lagd order",
        "category": "orderstatus",
        "content": (
            "En order går att komplettera fram tills den plockas i lagret, oftast inom "
            "1–2 timmar på vardagar. Hör av dig med ordernumret och vad du vill lägga "
            "till, så slår vi ihop det till en leverans och du betalar bara en frakt. "
            "Har ordern redan packats lägger du en ny beställning — kontakta oss så "
            "krediterar vi frakten på den andra ordern."
        ),
    },
    {
        "title": "Vad orderstatusen betyder",
        "category": "orderstatus",
        "content": (
            "Mottagen: ordern ligger hos oss men är inte plockad. Behandlas: den plockas "
            "i lagret just nu. Skickad: paketet är hos transportören och spårningsnumret "
            "är på väg till din mejl. Delvis skickad: en vara var restnoterad och skickas "
            "separat utan extra fraktkostnad. Står ordern kvar som Behandlas mer än två "
            "vardagar hör av dig, då har något fastnat."
        ),
    },
]
