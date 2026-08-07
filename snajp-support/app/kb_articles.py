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
        "category": "konto",
        "content": (
            "Under Mina sidor → Inställningar ändrar du namn, e-postadress, telefonnummer "
            "och sparade adresser. Byter du e-postadress skickas en bekräftelselänk till den "
            "nya adressen. Sparade kort hanteras av vår betalpartner och kan tas bort under "
            "Betalning → Sparade kort."
        ),
    },
    {
        "title": "Radera konto och personuppgifter (GDPR)",
        "category": "konto",
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
