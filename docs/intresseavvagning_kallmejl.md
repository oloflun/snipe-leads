# Intresseavvägning — utgående kallmejl

> **UTKAST. Inte juridiskt granskat.** Avvägningen ska läsas av jurist och
> beslutas av Anton som personuppgiftsansvarig för Snajps egna utskick. Den är
> inte en färdig rättslig grund förrän det är gjort.

Artikel 6.1 f kräver att den som stödjer sig på berättigat intresse **har gjort
avvägningen och kan visa den**. Ett påstående om berättigat intresse utan en
dokumenterad avvägning är inte en rättslig grund, det är en förhoppning.

Gäller: Snajps egna kallmejl (A2 i [registerförteckningen](registerforteckning.md))
och, i tillämpliga delar, kundens utskick via leadsagenten (B2), där kunden är
ansvarig och gör sin egen avvägning.

**Status: utkast, internt.** Uppdaterad 2026-11-17.

## Ändringslogg

- **2026-11-17, kväll:** ny regel för personlig adress införd i steg 3, steg 4
  och förutsättning 3 i steg 5. Byggd men inte committad eller driftsatt.
- **2026-11-17:** avvägningen omgjord mot dagens kod, enligt avsnittet "Att
  ompröva" i förra versionen: spärrarna har ändrats (regel 1 kräver bara
  företagsnamn sedan 2026-10-10, kort fot till funktionsadresser sedan
  2026-10-24) och volymen har ökat (tak 100 per dag och tenant sedan
  2026-11-16). Underlag: `snajp-support/app/leads/send_guard.py`,
  `utskicksfot.py`, `scheduler.py`, `forfilter.py`, `docs/BESLUT.md`,
  leadsreglerna i `CLAUDE.md`, Railways driftkonfiguration 2026-11-17 och
  nulägesinventeringen 2026-11-17 (internt underlag, inte i repot;
  avsnitt 6).
- 2026-08-24: förstautkast, byggt på 20 utskick per dag och full
  avsändaridentifiering.

---

## Behandlingen som den ser ut i dag

**Vem som kontaktas.** Iris väljer bolag ur registret (allabolag, merinfo) på
bransch, ort och storlek, och Jev sorterar bort uppenbara missar på
bolagsnivå. Kontaktadressen hämtas sedan från bolagets egen webbplats, från
hitta.se eller från registrets bolags-e-post (`CLAUDE.md`, leadsregel 10,
12–13 och 22; BESLUT 2026-10-10, rad 2284-2288). Reglerna i korthet:

- En namngiven persons styrkta adress föredras. Annars duger bolagets egen
  adress (info@, kontakt@), också på gmail eller telia om bolaget självt
  publicerar den (regel 13).
- HR-, ekonomi-, jobb- och robotadresser utesluts (regel 10 och 13).
- Registrets personer och privatpersonsidor blir aldrig kontakter (regel 1
  och 6).
- För Snajps egna Iris-körningar krävs ingen webbplats: registrets
  bolags-e-post räcker, och målgruppen är bolag med 1–200 anställda (regel 22,
  BESLUT 2026-10-30).
- Tilltalet: personligt namn vid personlig adress, eller ägarens eller VD:s
  namn från Om oss-sidan när den visar högst två personer (regel 14).
- Bolag med bara telefon går till ringlistan, inte till mejl (regel 15). Den
  behandlingen omfattas inte av den här avvägningen.

**Vem som skriver.** Utkasten skrivs automatiskt av Iris (Gemini 2.5 flash på
Vertex AI, `europe-west1`) ur research om bolaget. Den lagstadgade foten och
demolänkens rad läggs på av kod, inte av modellen (`utskicksfot.py:1-31`;
BESLUT 2026-11-15, rad 284-287).

**Vem som skickar.** I main är `SEND_QUEUE_POLL_SECONDS` inte satt (Railway,
2026-11-17). Varje utkast hamnar då i granskningskön
(`agent/leads_tools.py:298-299`), och bara utkast som en människa godkänt
skickas, av godkändsändaren (`config.py:393-398`). Autopiloten
(`LEADS_AUTOPILOT`) är inte satt i main. Development skickar inga utskick i
spegelläget (`scheduler.py:655-672`).

**Kön.** 2026-11-16 stod 3 868 godkända utkast i kö hos den största kunden,
det äldsta köat 2026-10-26 (BESLUT rad 83-89). Kön skickas äldst först och tar
ungefär åtta veckor att beta av (rad 131-133). Ett utkast kan alltså vara
flera veckor gammalt när det går ut. Godkännande kan göras i mängd: filtren,
Markera alla och massåtgärderna gäller hela urvalet (BESLUT 2026-11-15, rad
166-169).

**Uppföljning av mottagaren.** Varje utkast bär en demolänk
`{sajten}/prova/<token>`, en token per tråd. Klick loggas vid
vidarebefordringen, och ett besök loggas när mottagaren scrollar eller klickar
på demosidan. Båda knyts till tråden och därmed till en namngiven mottagare,
och kunden ser en lista "Vilka har besökt demon" (BESLUT 2026-11-15, rad
288-299 och 313-325; migration 116; `components/demo/DemoBesok.tsx`).

---

## Steg 1 — Finns ett berättigat intresse?

**Intresset:** att marknadsföra en programvara till företag som sannolikt har
nytta av den, genom direktkontakt med bolaget.

Direktmarknadsföring pekas uttryckligen ut som ett möjligt berättigat intresse
i skäl 47 till dataskyddsförordningen. Det avgör inte saken, men frågan är
öppen snarare än stängd.

Intresset är kommersiellt, och det är i sig inget problem. Det ska vara
verkligt, lagligt och konkret nog att väga. Det är det: Snajp är ett nystartat
bolag som säljer en supportagent och en leadsagent till småbolag, och
direktkontakt är den enda vägen att nå dem i den här fasen.

**Ett andra intresse har tillkommit:** att mäta vilka mottagare som besöker
demon, för att följa upp dem och jämföra utkastens varianter (A/B). Det är ett
eget ändamål. Det är också legitimt, men det ingår inte självklart i "att ta
en första affärskontakt" och måste vägas för sig (steg 3).

**Laglighet.** Intresset är bara berättigat om behandlingen är laglig i övrigt.
Där finns en brist: e-handelslagen (8 §) kräver att en näringsidkare anger
organisationsnummer. Regel 1 kräver bara företagsnamn sedan 2026-10-10
(`send_guard.py:210-222`), och BESLUT noterar själv att "Ett utskick utan
org.nr går nu ut" (rad 2189-2191). Snajps eget org.nr är en platshållare i
`lib/bolag.ts:39`. Om kundregistret i databasen har det är inte kontrollerat.
Snajp är en enskild firma, så organisationsnumret är ägarens personnummer;
att publicera det är ett beslut bara ägaren kan fatta.

## Steg 2 — Är behandlingen nödvändig för intresset?

Nödvändig betyder "det finns inget mindre ingripande sätt att nå samma mål",
inte "det är det bekvämaste sättet".

Alternativ som övervägts:

- **Enbart annonsering och inbound.** Når inte de specifika bolag där
  produkten gör mest nytta. Otillräckligt, inte likvärdigt.
- **Enbart funktionsadresser** (`info@`, `kontakt@`). Används i dag så fort
  ingen styrkt personlig adress finns (regel 10 och 13). För de minsta bolagen
  är funktionsadressen ofta ägarens egen inkorg, så skillnaden i intrång är
  liten där.
- **Uppsökande via telefon.** Mer ingripande. Används bara för bolag utan
  mejladress (ringlistan).

**Nödvändigheten håller för själva kontakten.** Den håller sämre för tre delar:

1. **Volymen.** 100 mejl per dag och tenant är satt för att beta av en kö på
   3 868 utkast, inte utifrån vad intresset kräver (BESLUT 2026-11-16, rad
   74-81). Det är ett affärsval. Det är inte i sig olagligt, men det tynger
   steg 3.
2. **Spårningen per person.** A/B-mätningen går att göra på aggregerad nivå
   (klick per variant) utan att knyta besöket till en namngiven mottagare.
   Listan över vilka personer som besökt demon är mer än mätningen kräver.
3. **Att utkast ligger i veckor.** Kontaktuppgifterna lagras längre än
   kontakten kräver, och ingen lagringstid är beslutad.

## Steg 3 — Vad väger på den registrerades sida?

**Det som talar för att intrånget är litet:**

- Uppgifterna är tjänsteuppgifter: bolagets adress eller en persons
  arbetsadress, namn och roll. Inga privatadresser från register, inga
  känsliga uppgifter.
- Adressen kommer från bolagets egen webbplats, en företagskatalog eller
  registrets bolagsnivå, där den publicerats för att bolaget ska bli kontaktat.
- Ett mejl om verksamhetens behov till någon som ansvarar för verksamheten
  ligger inom vad en yrkesperson rimligen kan förvänta sig (skäl 47).
- Bedömningen görs på bolaget (bransch, storlek, webbplats), inte på
  individen.
- Enskilda firmor fälls före researchen, eftersom en enskild näringsidkare är
  en fysisk person (`forfilter.py:25-44`).
- Varje mejl kan avregistreras med ett klick, och avregistreringen gäller hela
  tenanten permanent.

**Det som talar emot, och inte ska bortförklaras:**

- Personen har inte bett om kontakten och har inte lämnat uppgiften till oss.
- `fornamn.efternamn@bolaget.se` är en personuppgift. För ett bolag med en
  person är `info@` det också i praktiken.
- **Volymen har femfaldigats** sedan förra avvägningen (20 till 100 per dag
  och tenant). I oktober gick ~600 kallmejl ut på några dagar, och svaren
  tydde på att de flesta hamnade i skräpposten (BESLUT 2026-10-24, rad
  1399-1406). Det är ett tecken på att mottagarna och deras filter läste
  utskicken som massutskick.
- **Mejlen skrivs av en språkmodell** och godkänns ofta i mängd. Den mänskliga
  granskningen är verklig för de tre första, men för resten kan den bli en
  formalitet.
- **Spårningen är inte informerad.** Demolänken knyter klick och besök till en
  namngiven mottagare. Det står inte i utskicksfoten
  (`utskicksfot.py:106-124`) eller i integritetspolicyn, och cookiesidan säger
  att Snajp inte mäter besökarens beteende på sidan
  (`app/cookies/CookiesSida.tsx:26`). Besöksmätningen använder
  `sessionStorage` (`components/demo/DemoBesok.tsx`), vilket kan omfattas av
  LEK 9 kap. 28 §. BESLUT lämnar frågan till Anton (rad 327-330). En
  mottagare förväntar sig inte att ett besök på en länk i ett kallmejl
  registreras under hens namn.
- **Funktionsadresser får ingen art. 14-information.** Till info@ och kontakt@
  går en kort fot med avsändare och avregistrering, utan art. 14-stycken och
  utan policylänk (`utskicksfot.py:98-104`; `send_guard.py:272-276`). Det är
  försvarbart när adressen verkligen är en funktion. Men gränsen dras av en
  heuristik: i drift räknas en adress som personlig bara om lokaldelen
  innehåller punkt eller bindestreck (`leads/sources/base.py`).
  `anna@bolaget.se` räknas därför som funktionsadress och får den korta foten,
  fast den bär en persons namn. **Rättat i kod 2026-11-17, inte committat
  eller driftsatt:** en adress räknas nu som personlig när lokaldelen inte är
  en känd funktionsadress (listan `FUNKTIONSADRESSER` i
  `leads/sources/base.py` och avdelningsorden i `discovery.AVDELNINGSORD`).
  `anna@` och `andersson@` får då den fullständiga foten, och `vd@` och `ceo@`
  räknas som personliga eftersom de når en utpekbar person. Test:
  `tests/leads/test_personlig_adress.py`.
- **Enskilda firmor fälls bara när org.nr är känt.** `ar_enskild_firma`
  returnerar falskt när numret saknas (`forfilter.py:30-34`), och "okänt fäller
  aldrig" (rad 9-10). En kandidat från den öppna sökningen utan org.nr kan
  alltså vara en enskild firma.
- **Avsändaren går inte att identifiera fullt ut** när org.nr och postadress
  saknas i foten (steg 1).

## Steg 4 — Skyddsåtgärderna, och var de sitter i koden

Åtgärderna nedan är spärrar i kod, kontrollerade mot `send_guard.py` på grenen
`development` (HEAD `545dca1b`) och mot `origin/main` efter mergen av PR #44
2026-11-17. Spärrarna körs i sändögonblicket på varje mejl.

| Åtgärd | Var | Vad som händer om den brister |
|---|---|---|
| Avregistrering gäller omedelbart, för hela tenanten och permanent. Befintliga kunder och redan kontaktade adresser stoppas | Regel 3, `send_guard.py:288-329` | **Blockeras** |
| Företagsnamnet står i foten. Org.nr och postadress tas med bara när kundregistret har dem | Regel 1, `send_guard.py:198-222`; `utskicksfot.py:91-97` | **Blockeras** om namnet saknas. **Inget stopp** om org.nr eller adress saknas |
| Klickbar avregistreringslänk i varje mejl | Regel 2, `send_guard.py:246-271` | **Blockeras** |
| Länk till avsändarens integritetspolicy, bara vid personlig adress | Regel 2, `send_guard.py:272-282` | **Blockeras** |
| Art. 14-information (vem, varför, varifrån, rätten att invända), bara vid personlig adress | Regel 4, `send_guard.py:345-374`; `utskicksfot.py:106-124` | **Blockeras** |
| Kort fot till funktionsadresser: avsändare och avregistrering, inga art. 14-stycken | `utskicksfot.py:98-104` | – |
| Vad som räknas som personlig adress. I drift: punkt eller bindestreck i lokaldelen. Byggt 2026-11-17, inte driftsatt: allt som inte är en känd funktionsadress | `leads/sources/base.py` (`FUNKTIONSADRESSER`); `discovery.AVDELNINGSORD` | Foten byggs i sändögonblicket, så redan köade utkast till namnadresser får den fullständiga foten när ändringen driftsätts. Saknar kunden `policy_url` **blockeras** de enligt regel 2 |
| Kontorstid, vardagar 08–17 svensk tid. Kallmejl går bara 08–16; efter 16 bara svar i trådar där leadet svarat | Regel 5a, `send_guard.py:87-90, 396-412`; `scheduler.py:790-795` | **Köas om**. "Skicka nu" släpper bara tidsgrinden |
| Karens: högst en kontakt per bolag per 90 dagar, räknat på org.nr, annars domän | Regel 5b, `send_guard.py:81-85, 414-425, 544-564` | **Blockeras** |
| Uppvärmning: 20 per dag de första 14 dagarna | Regel 5c, `send_guard.py:44-49, 432-434` | **Köas om** |
| Upptrappning: högst 5 fler än den största dagsvolymen senaste sju dagarna, aldrig över 100 per dag och tenant | Regel 5d, `send_guard.py:51-66, 435-438` | **Köas om** |
| Ett mejl i taget, minst 45 sekunder mellan två utskick per kund, från 08:00 | `scheduler.py:776` (`TAKT_SEKUNDER = 45`); BESLUT rad 106-113 | Väntar |
| Leveransstopp: över 0,1 % klagomål eller över 3 % studs (minst 20 skickade) de senaste 14 dagarna stoppar alla tenantens utskick | Regel 5e, `send_guard.py:68-79, 479-497` | **Köas om**, även "Skicka nu" |
| De tre första utskicken för en ny tenant granskas av en människa | Regel 6, `send_guard.py:92-93, 503-523` | Går till **granskningskö** |
| I main: inget utkast skickas utan mänskligt godkännande | `leads_tools.py:298-299`; `SEND_QUEUE_POLL_SECONDS` osatt i main 2026-11-17 | Går till **granskningskö**. En miljöinställning, inte en spärr i koden |
| Enskilda firmor fälls före research (MFL 19 §) | `forfilter.py:25-44` | Fälls, **om org.nr är känt** |
| Modellen kan inte skicka; bara kod skickar | INV-SEC-004 | Modellen har inget sändverktyg |

**Två spärrar är svagare än i förra versionen:** regel 1 (org.nr och adress
krävs inte) och foten till funktionsadresser (inga art. 14-stycken). Volymen
är fem gånger högre. **Tre spärrar har tillkommit:** upptrappningen,
leveransstoppet och takten. De skyddar främst domänens leverans, men de
begränsar också hur snabbt volymen kan öka.

## Steg 5 — Slutsats

**Avvägningen håller inte i alla delar som utskicken ser ut i dag.** Den
bärande delen håller: en enstaka relevant kontakt med ett bolag, via en adress
bolaget själv publicerat, med fungerande avregistrering och karens. Men fyra
punkter försvagar den så mycket att den inte går att visa upp som den är:

- avsändaren identifieras inte med org.nr (e-handelslagen),
- demolänkens spårning per namngiven mottagare är inte informerad,
- volymen har ökat femfaldigt och kön skickar veckogamla utkast,
- adresser som bär en persons namn kan få den korta foten utan art.
  14-information.

**Berättigat intresse håller som grund för Snajps egna kallmejl under
förutsättning att:**

1. Org.nr och postadress står i varje utskick. Antingen återinförs kravet i
   regel 1, eller så kontrolleras att kundregistret har uppgifterna för varje
   tenant som skickar. För Snajp själv kräver det ett beslut om att publicera
   den enskilda firmans organisationsnummer, eller att bolagisera. (Anton)
2. Demolänkens spårning blir informerad eller avgränsad: en rad i
   utskicksfoten och i integritetspolicyn om att länken mäts, cookiesidan
   rättad, och ett beslut om `sessionStorage` och LEK 9 kap. 28 §. Alternativt
   mäts klicken bara per variant och inte per person. (Anton beslutar, agent
   genomför)
3. Heuristiken för personlig adress fångar också förnamnsadresser
   (`anna@bolaget.se`), eller så får alla mejl den fulla foten med
   art. 14-information. (agent) **Läge 2026-11-17:** byggd men inte
   committad eller driftsatt. Allt som inte är en känd funktionsadress räknas
   som personligt (steg 3). Kvar: Antons godkännande, driftsättning, och
   `policy_url` ifylld för varje kund som skickar till namnadresser.
4. Godkända utkast som legat längre än [FYLL: maxålder för ett köat utkast]
   researchas om eller stryks innan de skickas, så att uppgifterna är aktuella
   (art. 5.1 d). (Anton beslutar, agent bygger)
5. Lagringstiden för prospekt och kontakter beslutas och gallras (se nedan).
   (Anton)
6. Volymtaket på 100 per dag och tenant bekräftas av Anton som ett medvetet
   val, med leveransstoppet och upptrappningen kvar. (Anton)
7. Enskilda firmor fälls också när org.nr saknas, eller så kräver mejlspåret
   ett känt org.nr. (agent)
8. En jurist bekräftar att den korta foten utan art. 14-information är
   tillräcklig för funktionsadresser hos småbolag där adressen i praktiken är
   en persons. (jurist)

Tas regel 2 (avregistreringen) eller regel 4 (art. 14 vid personlig adress)
bort är bedömningen inte giltig alls.

**Rätten att invända** (artikel 21.2) är ovillkorlig vid direktmarknadsföring.
Den registrerade behöver inte ange skäl, och vi måste sluta omedelbart.
Avregistreringslänken gör det, och kontrollen sker i sändögonblicket, så
också köade utkast stoppas.

## Lagringstid för prospekt och kontakter

**Obeslutad.** [FYLL: lagringstid för prospekt, kontaktuppgifter och
utskickshistorik, och vad som sparas av en avregistrerad adress]

Det som finns i dag: avregistrerade adresser sparas i spärrlistan, och
spärrlistan överlever radering (`scripts/gdpr_radera.py:67, 185-200`). Bolag
som valts bort i en körning blandas in igen efter 30 dagar (BESLUT 2026-10-15,
rad 2038-2040). Gallringen i migration 048 omfattar inte leadstabellerna.
Registerförteckningen lämnar frågan öppen (`registerforteckning.md:42`).

## Att ompröva

Bedömningen ska göras om vid något av följande:

- Volymen ökar utöver 100 per dag och tenant, eller upptrappningen tas bort.
- Personlig profilering införs, alltså bedömning av individen och inte bolaget.
  Spårningen av besök per mottagare ligger nära den gränsen redan.
- Källorna vidgas bortom bolagets egen webbplats, företagskataloger och
  registrets bolagsnivå.
- Någon spärr i steg 4 tas bort eller mjukas upp.
- Utskicken börjar gå utan mänskligt godkännande i main
  (`SEND_QUEUE_POLL_SECONDS` eller `LEADS_AUTOPILOT` sätts).

## Öppna punkter

- [ ] Läst av jurist
- [ ] Förutsättning 1–8 i steg 5 genomförda eller avvisade med skäl
- [ ] Beslutad lagringstid för prospekt och kontaktuppgifter (kopplas till
      gallringen). [FYLL: lagringstid]
- [ ] Källangivelsen i utskicksfoten granskad. Den säger i dag "offentliga
      företagsuppgifter" (`utskicksfot.py:71`). Källorna är bolagets egen
      webbplats, allabolag, merinfo och hitta.se
- [ ] Beslut om Snajps organisationsnummer i utskicken (enskild firma eller AB)
