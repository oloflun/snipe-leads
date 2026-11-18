# Systemblad: webbrevisionens bildbedömning och webbpoolen

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning: `README.md` i samma mapp. "Bevis" =
`docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`. Sökvägar under
`app/` avser `snajp-support/app/`.

Webbplatsbedömningen är hemlig utanför plattformsadmin och kunderna Umeå
Webdesign och Alunix (`CLAUDE.md`, Antons beslut 2026-10-08). Det här bladet
beskriver hur bedömningen görs, inte enskilda resultat.

## 1. Syfte och avsedd användning

**Vad den gör.** Bedömer hur ett bolags publika startsida ser ut och presterar
och ger den en av fyra nivåer: akut, dålig, bra eller mycket bra
(`app/leads/webbrevision.py:1-23, 130-148`). Två användningar:

1. **Som kriterium i Iris.** Betyget översätts i kod till träff, miss eller
   okänt för kundens webbkriterier (`app/leads/bedomning.py:79-100`;
   `CLAUDE.md` leadsregel 9).
2. **Webbpoolen.** Varje körnings bolag med webbplats bedöms och fördelas
   efter län till webbyråkunderna: akut och dålig som leads, mycket bra som
   inspirationslista, bra aldrig (`app/leads/webbpool.py:1-8`; INV-SEC-008,
   `ARCHITECTURE_INVARIANTS.md:176-192`, godkänd av Anton 2026-10-08).

**För vem.** Webbyråkunderna och Snajps plattformsadmin. Övriga kunder får
varken se eller få bedömningen beräknad (`webbpool.py:108-117`;
AI-inv. 186-187).

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad policy):

- Bedömning av personer. Det som bedöms är en publik sajt.
- Bedömning av en undersida; bara startsidan (`CLAUDE.md` leadsregel 18;
  `webbrevision.py:416`).
- Att modellens fria omdöme ensamt avgör något: nivån räknas i kod ur en
  siffra 1-10, och akut avgörs utan bild för parkerad domän, felsida och sajt
  som inte svarar (`webbrevision.py:130-148, 417-429`).
- Att visa bedömningen för andra kunder än webbyråerna, också via kopierade
  listor (`CLAUDE.md`).

## 2. Design (`webbrevision.py:revidera`, rad 411-460)

| # | Steg | AI? | Kod | Vid fel |
|---|---|---|---|---|
| 1 | Sajt som saknas, är parkerad, ger 404/410/5xx eller inte svarar blir akut | Nej | rad 417-429 | – |
| 2 | PageSpeed (mobil) och skärmbild via ScrapeGraph med nekade samtyckescookies | Nej | rad 431-432; samtycke rad 60-82 | PageSpeeds bild som reserv |
| 3 | Bildbedömning: skärmbild plus uppmätta fakta till bildmodellen; svaret är JSON med `modernitet` 1-10 och högst tre brister | Gemini (bild) | `visuell`, rad 344-383; prompten `VISIONPROMPT` rad 151 | Fel ger `None` (rad 364-366); tomt svar ger ett nytt försök (rad 434-436) |
| 4 | Ruta som skymmer: ett andra försök med stealth | Gemini (bild) | rad 437-443 | – |
| 5 | Nivå i kod: akut högst 2, dålig högst 5, bra högst 8, annars mycket bra; katalogsida aldrig bättre än dålig; skymd eller oläsbar blir okänd | Nej | rad 54-59, 130-148 | – |
| 6 | Iris: webbkriteriet avgörs i kod | Nej | `bedomning.py:79-100` | Okänt avgör inget |
| 7 | Poolen: bara bolagsfält, aldrig kontakt, kundinnehåll eller vilken kund som hittade bolaget | Nej | `webbpool.py:46`; INV-SEC-008 | – |

Kalibrering: mot Antons facit 2026-10-08 med 58 sajter och grind 85 %
(`snajp-support/tests/leads/fixtures/webbfacit_2026-10-08.json`;
`snajp-support/scripts/kalibrera_webbrevision.py`; `CLAUDE.md` leadsregel 18).

## 3. Modeller och resurser

| Del | Konfig | Standard | I drift | Plats |
|---|---|---|---|---|
| Bildbedömning | `vision_model` | `gemini-2.5-flash` (`config.py:307`) | Osatt, alltså standard | Vertex AI, `vertex_bild_region` eller `europe-west1` (`config.py:266-273`) |
| Skärmbild | ScrapeGraph (`scrapegraphai_api_key`) | – | Satt i båda miljöerna (bevis rad 122, 273) | Extern tjänst; plats inte genomgången här |
| Prestanda | Google PageSpeed (`pagespeed_api_key`, valfri) | – | Ingen nyckel i beviset | Google |
| På/av | `LEADS_WEBBREVISION` | osatt = på (`webbrevision.py:25-26, 195-196`) | Osatt, alltså på | – |
| Poolen | `WEBBPOOL`, `WEBBPOOL_FORDELNING`, `WEBBPOOL_MOTTAGARE`, `WEBBPOOL_INSPIRATION` | pool på, fördelning av (`webbpool.py:21-28`) | Fördelning, mottagare och inspiration satta bara i `development` (bevis rad 131-133); i `main` osatta, alltså ingen fördelning | – |
| Dygnstak | `WEBBPOOL_DAGSTAK` | 300 bedömningar per dygn och process (`webbpool.py:28`) | Osatt | – |

**Var den körs.** Railway-tjänsten `api`, som del av Iris körningar och
listbyggen.

**Livslängd.** Ingen kandidat efter Gemini 2.5 klarar grinden; `gemini-3.8-flash`
är jämnt för sträng, `gemini-3.5-flash-lite` satte en akut sajt på bra
(`docs/compliance/modellbyte-underlag.md:377-418`). Bildmodellen ligger kvar
på 2.5 tills ägaren väljer (samma, rad 416-418; `docs/BESLUT.md:30-31`).

## 4. Data in och ut

- **In till modellen:** skärmbilden av startsidan, sajtens adress och kodens
  uppmätta fakta (`webbrevision.py:331-352`). Publika bolagssajter; ingen
  kunddata (`webbrevision.py:15-19`). En skärmbild kan visa namn och
  kontaktuppgifter som står på sajten; de maskeras inte.
- **Ut:** nivå, modernitet, högst tre brister, PageSpeed-siffror och citerbara
  rader (`webbrevision.py:386-460`).
- **Loggat:** textdelen av prompten och svaret i `agent_runs`; skärmbilden
  loggas inte (`webbrevision.py:368-377`).
- **Poolen:** bara `POOLFALT` (`webbpool.py:46`).
- **Lagringstid:** inte beslutad.

## 5. Mänsklig översyn

- Ingen människa granskar varje bedömning. Nivån används automatiskt i Iris
  och i poolen.
- I Iris påverkar nivån bara kriterier som kunden själv skrivit om
  webbplatsen, och utkasten granskas av människa i drift (se `iris.md`
  avsnitt 5).
- Webbyrån som får poolen söker själv kontakt och bestämmer om den hör av sig
  (`webbpool.py:16-17`).
- Grinden på 85 % mot facit är den mänskligt satta kontrollen; den körs med
  skript, inte i CI.

## 6. Utvärdering

| Mätning | Modell | Resultat | Belägg |
|---|---|---|---|
| Full kalibrering, 58 facitsajter, 2026-11-18 | 2.5-flash, `europe-west1` (i drift) | 47/58 (81,0 %); **under grinden 85 %**; ingen akut på bra; 4 bra kallade dålig eller akut, 5 dåliga kallade bra | `modellbyte-underlag.md:377-399` |
| samma | 3.8-flash, `eu` | 47/58 (81,0 %); 9 bra kallade dåliga, ingen dålig kallad bra | samma, rad 379-385, 400-405 |
| samma | 3.5-flash-lite, `eu` | 46/58 (79,3 %); en akut sajt på bra | samma, rad 379-384, 406-407 |
| Urval 30 sajter | 2.5-flash | 25-26/30 (83-87 %) | samma, rad 301-307 |

En facitsajt (sagobetong.se) har åldrats; räknat utan den ändras inget utfall
(samma, rad 390-392).

**Inte mätt:** stabiliteten mellan körningar utöver två körningar på urvalet;
bedömningen av sajter utanför facit; hur ofta webbyråerna får en felaktig
lead i drift.

## 7. Kända begränsningar

- **Modellen i drift klarar inte sin egen kalibreringsgrind** på hela facit
  (81 % mot 85 %). Leadsregel 18 i `CLAUDE.md` säger att bedömningen är
  kalibrerad med grind 85 %; mätningen 2026-11-18 visar att den inte nås.
- Felen går åt båda håll med 2.5-flash: dåliga sajter blir bra (missade
  leads för webbyrån) och bra sajter blir dåliga (felaktiga leads).
- Skärmbilden kan skymmas av samtyckesrutor; då blir nivån okänd eller kräver
  ett dyrare andra försök (`webbrevision.py:437-443`).

## 8. Risker per AI-steg (bedömningsutkast)

Utkast av agenten. Inga riskkriterier finns, så ingen restrisk är accepterad.

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| Bildbedömning | Bra sajt bedöms som dålig | Bolaget får ett säljmejl från en webbyrå om en brist som inte finns | Facit och grind; akut avgörs i kod | Medel: 4 av 58 i mätningen | nej (ägarens beslut) |
| Bildbedömning | Dålig sajt bedöms som bra | Webbyrån missar ett lead | Samma | Medel: 5 av 58 | nej (ägarens beslut) |
| Bildbedömning | Promptinjektion i sajtens synliga text | Styrt betyg | Svaret tolkas bara som en siffra och tre brister; nivån räknas i kod | Låg | nej (ägarens beslut) |
| Poolen | Kunddata eller vilken kund som hittat bolaget läcker till en konkurrent | Brott mot kundens förtroende och avtal | INV-SEC-008, `tests/leads/test_webbpool.py` | Låg | nej (ägarens beslut) |
| Synlighet | Bedömningen syns för fel kund | Brott mot Antons beslut om sekretess | `webbpool.far_se`, nej vid fel (`webbpool.py:108-117`) | Låg | nej (ägarens beslut) |
| Modellen | Google stänger Gemini 2.5 | Ingen bedömning; kriterier faller på text | Ingen godkänd ersättare | Hög sannolikhet över tid | nej (ägarens beslut) |

Påverkan på individer och grupper: bedömningen gäller bolag. Små bolag med
egenbyggda eller äldre sajter hamnar oftare i akut eller dålig och får därmed
fler säljkontakter från webbyråer. Det är syftet, men det är inte bedömt som
påverkan på gruppen (`matris.md:70, 123`).
