# Snajp och EU:s AI-förordning (2024/1689)

> **Bedömning, inte rättsutlåtande.** Skriven 2026-11-17 av en agent på Antons uppdrag, ur repot och förordningens text som den var känd för agenten. En jurist ska granska den innan den används mot kund eller myndighet. Där rättsläget är oklart står det **osäkert**. Artikelhänvisningar som agenten inte är säker på är märkta.

Comp AI har inget ramverk för AI-förordningen. ISO 42001 (`matris.md`) täcker styrningen men inte förordningens skyldigheter. Den här filen kartlägger dem per AI-system.

## 1. Snajps roller

| Roll i förordningen | Gäller Snajp? | Skäl |
|---|---|---|
| **Leverantör** av AI-system (art. 3.3) | **Ja**, för supportagenten och Iris | Snajp utvecklar systemen och tillhandahåller dem under eget namn till kunder (`app/villkor/VillkorSida.tsx:17-19`). Att systemen bygger på inköpta modeller ändrar inte det |
| **Tillhandahållare** (den som använder, art. 3.4) | Ja, för Snajps egna utskick och egen support; kunden är tillhandahållare för sina | Snajp kör Iris för egen räkning (kontot Snajp, BESLUT 2026-10-30) och supportagenten på egen sajt |
| Leverantör av AI-modell för allmänna ändamål (GPAI, kap. V) | **Nej** | Snajp tränar och finjusterar inga modeller. Gemini (Google) och Jev (TypeSafe) är inköpta. GPAI-skyldigheterna (art. 53 och följande) ligger på Google och TypeSafe. Om Jev alls är en GPAI-modell är **osäkert**; den beskrivs som en liten beslutsmodell (`snajp-support/app/leads/jev.py:5-9`) |
| Användare av GPAI-modeller i nedströmsled | Ja | Snajp bygger system på Gemini via Vertex AI. Förordningen ger nedströmsleverantörer rätt till viss information från modelleverantören; exakt artikel: **osäkert, kontrollera** |

## 2. Datum som gäller

| Från | Vad | Läge för Snajp |
|---|---|---|
| 2025-02-02 | Art. 4 AI-kunnighet och art. 5 förbjudna användningar | Gäller nu |
| 2025-08-02 | GPAI-skyldigheter (kap. V), sanktioner | Gäller Google och TypeSafe, inte Snajp |
| 2026-08-02 | Art. 50 transparens; förordningen i övrigt, inklusive högrisksystem enligt bilaga III i den ursprungliga texten (art. 113) | Gäller nu |
| 2027-08-02 | Art. 6.1, högrisk via produktsäkerhetslagstiftning (bilaga I) | Inte relevant för Snajp |

**Osäkert:** kommissionen föreslog i november 2025 ett förenklingspaket (digital omnibus) som bland annat skjuter fram högriskkraven och ändrar art. 4. Om och i vilken form det antagits per 2026-11-17 är inte kontrollerat. Juristen ska kontrollera.

## 3. Riskklass per AI-system

### 3.1 Supportagenten

**Trolig klass: begränsad risk (art. 50), inte högrisk.**

- Den svarar på kundtjänstärenden, klassar och prioriterar dem, och skickar svar i de kategorier kunden ställt på automatiskt.
- Bilaga III pekar ut områden, inte tekniker. Kundtjänst finns inte där. Prövat särskilt:
  - **Väsentliga privata tjänster (bilaga III punkt 5).** Punkten gäller bland annat kreditvärdighet för fysiska personer och riskbedömning och prissättning i liv- och sjukförsäkring. Supportagenten fattar inga sådana beslut. Den kan svara en kund om ett villkor, men den bedömer inte personen.
  - **Nödsamtal (punkt 5).** Utvärdering och prioritering av nödsamtal är högrisk. Agentens prioritering av ärenden gäller kundtjänst, inte nödtjänster.
  - **Känsloigenkänning (art. 5.1 f och art. 50.3).** Triagen läser sentiment ur text (`email_pipeline/processor.py:756`). Förordningens känsloigenkänning bygger på biometriska uppgifter (definitionen i art. 3; exakt punkt: kontrollera). Text är inte biometri, så sentimentet bör falla utanför. Förbudet gäller dessutom bara arbetsplats och utbildning.
- **Risken för omklassning ligger hos kunden.** Använder en bank, ett försäkringsbolag, ett bemanningsbolag eller en myndighet agenten för beslut om kredit, försäkring, anställning eller förmåner, kan systemet bli högrisk i den användningen. Den som ändrar ett systems avsedda ändamål så att det blir högrisk blir själv leverantör (art. 25). Snajp bör därför skriva in förbjudna användningar i villkoren (P27 avsnitt 4). I dag saknas det.

**Skyldigheter och läge:**

| Skyldighet | Läge 2026-11-17 | Belägg |
|---|---|---|
| Art. 50.1: den som interagerar med systemet ska få veta att det är en AI, om det inte är uppenbart, senast vid första interaktionen | **Delvis.** Kodspärr byggd för chatt och automatiska supportmejl: "AI-assistent" i chattens huvud och en fast rad i varje autosvar, eskalering till människa i kod. **Ocommittad och inte driftsatt** | INV-AI-001 (`ARCHITECTURE_INVARIANTS.md:959-972`), test `snajp-support/tests/invariants/test_inv_ai_001.py`; `email_pipeline/processor.py:44-72, 768`; BESLUT 2026-11-17 |
| Art. 50.1 för utkast som en människa godkänner | Ingen rad läggs på. Agenten har bedömt att ett granskat svar är människans svar. **Osäkert**; juristen bedömer (DPIA R13) | `docs/BESLUT.md:57-59` |
| Art. 50.2: maskinläsbar märkning av AI-genererad text | **Saknas, osäkert om tillämpligt.** Gäller leverantörer av system som genererar syntetisk text. Hur märkningen ska se ut för e-post och om undantagen för redigeringsstöd gäller är oklart | – |
| Art. 4 AI-kunnighet | **Saknas.** Ingen dokumenterad åtgärd för Anton och Sebbe | `matris.md` 7.2 |
| Art. 5 förbjudna användningar | Inget tyder på förbjuden användning | – |

### 3.2 Iris (leadsagenten)

**Trolig klass: begränsad eller minimal risk, inte högrisk.**

- Iris söker bolag, bedömer dem mot kundens kriterier (nivå A/B/C), skriver kallmejl och kan skicka dem inom sändspärrarna och kundens autonominivå (`snajp-support/app/leads/autonomy.py:8-24`).
- Prövat särskilt:
  - **Bedömning av fysiska personer.** Iris bedömer bolag, inte personer. Enskilda firmor, där bolaget är en person, fälls innan research (`leads/forfilter.py:25-44`, `CLAUDE.md` leadsregel 15–16). Kontakten är en adress eller ett namn, inte en bedömd person. En bedömning av en fysisk person skulle dock inte i sig göra Iris till högrisk; det krävs att användningen står i bilaga III.
  - **Anställning (bilaga III punkt 4).** Iris läser platsannonser som köpsignal (`leads/sources/jobtech.py`) men väljer inte kandidater. Ej tillämpligt.
  - **Kreditvärdighet (punkt 5).** Omsättning och storlek används som filter (`CLAUDE.md` leadsregel 1), men för att välja kunder att kontakta, inte för att bevilja kredit, och inte för fysiska personer. Ej tillämpligt.
  - **Manipulation (art. 5.1 a).** Förbudet gäller tekniker som väsentligt snedvrider beteende och orsakar betydande skada. Säljmejl med belagda påståenden (INV-GROUND-001, -004) ligger klart utanför. Grindarna mot påhittade siffror stärker det.
- **Webbpoolen** (bedömning av bolags webbplatser, `CLAUDE.md` regel 18–20) gäller bolag och är inte högrisk.

**Skyldigheter och läge:**

| Skyldighet | Läge 2026-11-17 | Belägg |
|---|---|---|
| Art. 50.1 för kallmejl som skickas utan granskning (`first_contact`) | **Öppen fråga för juristen.** Ett första mejl är ett meddelande, inte nödvändigtvis en interaktion. Svar i en tråd som Iris själv skriver vid `meeting` ligger närmare interaktion. Ingen AI-upplysning i utskicken i dag | `docs/BESLUT.md:60-61`; `autonomy.py` |
| Art. 50.2 märkning av AI-genererad text | Som för supportagenten: **saknas, osäkert om tillämpligt** | – |
| Art. 4 AI-kunnighet | **Saknas** | – |
| Art. 5 | Inget tyder på förbjuden användning | – |

### 3.3 Jev (TypeSafe)

**Trolig klass: minimal risk.** Jev ger sannolikheter för förfiltrering av bolag (`jev.py:11-20`) och, när `INKORG_JEV` inte är `off`, en klassning av inkommande mejl. Den interagerar inte med någon människa och fattar inga beslut om personer. Inga särskilda skyldigheter enligt förordningen utöver art. 4.

Förordningen är inte problemet med Jev. Problemet är dataskyddet: kundmejl till en amerikansk leverantör utan EU-region, utan DPF och med en telemetrilicens (BU A2, Lev. §7). Det hanteras i `../gdpr/` och P27 avsnitt 6.

## 4. Sammanfattning

| System | Trolig riskklass | Snajps roll | Viktigaste skyldighet nu | Läge |
|---|---|---|---|---|
| Supportagenten | Begränsad risk (art. 50) | Leverantör; tillhandahållare för egen sajt | Art. 50.1 i chatt och autosvar | Byggt, ocommittat |
| Iris | Begränsad eller minimal | Leverantör; tillhandahållare för Snajps egna utskick | Art. 50.1 för autonoma utskick: öppen fråga | Ingen upplysning |
| Jev | Minimal | Användare av inköpt modell | Art. 4 | Saknas |
| Alla | – | – | Art. 4 AI-kunnighet sedan 2025-02-02 | Saknas |

## 5. Frågor till juristen

1. Är ett granskat utkast "människans svar" så att art. 50.1 inte kräver upplysning?
2. Gäller art. 50.1 ett kallmejl som Iris skriver och skickar utan granskning, och svar i tråden vid autonominivån `meeting`?
3. Gäller art. 50.2 (märkning) e-post som en AI skrivit, och hur märks e-post maskinläsbart?
4. Vilka förbjudna användningar ska stå i villkoren för att Snajp inte ska bli ansvarig om en kund använder supportagenten inom ett område i bilaga III?
5. Vad gäller efter förenklingspaketet för art. 4 och för datumen?
6. Räcker kundens ansvar för autonominivån i villkoren (`VillkorSida.tsx:34-41`), eller behöver Snajp som leverantör också ge kunden instruktioner för användningen?
