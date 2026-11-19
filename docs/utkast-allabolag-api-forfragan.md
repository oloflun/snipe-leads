# Utkast — förfrågan till Allabolag (UC) om företagsdata via API

> Ej skickat. Mottagare: kontakt@allabolag.se (UC Affärsinformation AB, försäljning;
> adressen hittad via sökning, kontrollera på allabolag.se/kontakt/api innan du skickar).
> Underlag: plans/2026-10-01-leads-suite-och-korningar.md, `AllabolagSource` i
> snajp-support/app/leads/sources/registry.py (kräver abonnemangsnyckel, skrapar aldrig).
> Allabolags villkor kräver skriftligt medgivande för regelbunden insamling och lagring,
> därför frågar mejlet uttryckligen om lagring och cache.

**Ämne:** Förfrågan om företagsdata via API – Snajp (B2B-prospektering)

Hej,

Jag heter Anton och driver Snajp (snajp.se), ett verktyg där svenska småföretag
får fram och kvalificerar B2B-leads. Vi vill använda Allabolags API som grund
för de listorna och undrar vad det skulle kosta och vilka villkor som gäller.

**Det vi behöver per bolag**
- Namn, organisationsnummer, bolagsform och status (aktivt/avregistrerat)
- Bransch (SNI) och säte på län- och kommunnivå
- Antal anställda och omsättning
- Befattningshavare: VD, ordförande och styrelseledamöter med roll
- Telefonnummer, adress och, där det finns, hemsida
- Gärna händelser: nyregistreringar, styrelseändringar och adressändringar

**Så skulle vi använda dem**
Våra kunder beställer urval som "byggbolag i Norrland" eller "VVS-firmor i
Mölndal". Vi söker bolagen på bransch, län och kommun, filtrerar dem på storlek
och status och visar dem i tjänsten tillsammans med en kontaktperson och dess
roll. Vi skulle cacha uppgifterna i högst sju dagar. Vi börjar med 1–5 kunder
och räknar med 1 000–7 500 bolagsuppslag i månaden, upp mot 15 000 när kunderna
kör dagligen. Ett uppslag är ett anrop som hämtar ett bolags uppgifter;
urvalssökningar på bransch och ort tillkommer och står för högst en tiondel av
volymen.

**Frågor**
1. Kan vi söka bolag på bransch, region och storlek via API:t, eller bara slå
   upp ett bolag i taget på organisationsnummer? Det avgör hur många anrop vi
   behöver.
2. Hur ser prismodellen ut (per uppslag, per månad eller per urval)? Ett fast
   månadspris eller en volymtrappa passar oss bäst, eftersom volymen växer med
   antalet kunder.
3. Er sida om API:t anger att lagring och sammanställning av data kräver
   skriftligt medgivande. Får vi cacha svaren i sju dagar och spara
   organisationsnumren på bolag vi redan har visat, så att samma bolag inte
   hämtas och levereras två gånger?
4. Får vi visa uppgifterna för våra kunder i tjänsten och låta dem exportera
   sina egna listor?
5. Hur ser ni på personuppgifterna om befattningshavare – vem är
   personuppgiftsansvarig för källan, och finns ett avtal vi bör teckna?

Jag ser hellre en licensierad lösning än att hämta från webben, så ett
prisförslag eller ett kort samtal skulle hjälpa mycket.

Vänliga hälsningar
Anton Lundin
Snajp
kontakt@snajp.se
