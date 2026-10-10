# Plan 2026-10-05 — Iris billigare och skarpare, inkorgen rätt, Leads/Att göra/Översikt omgjorda

## Context

Anton testade development 2026-10-04 efter merinfo-bygget och hittade sju problem:
1. ScrapeGraph-krediten rann iväg (109 krediter på en dag, gratispotten på 500 slut).
2. Översikten är tråkig. Den ska bli en dashboard man vill titta på, i stil med Upsales.
3. Att göra är en oändlig scroll. Leadsinkorgen och utkasten hör hemma under Leads.
4. Leads har dåliga flikar. Tabell och Pipeline ska bakas in i en enda vy med statusmarkering och full bredd. En flik Körningar saknas.
5. Alunix inkorg: alla mejl eskalerades, även nyhetsbrev och driftlarm.
6. Iris bedömer webbplatser och bolag inkonsekvent. Ostia är fel målgrupp. Björkekärr och Eustaff har bra sajter. Bolag utan sajt får ibland 100 poäng och fälls ibland.
7. Bolag utan webbplats ska inte kastas. De ska hamna i listorna i stället.

Målet: ett Iris-lead kostar en bråkdel av i dag, webbplatsbedömningen går att lita på, och de ytor kunden ser först ser genomtänkta ut. Delmål i GOALS.md: 2 (leads-agenten) och 10 (release till main). Fas 1 är dessutom villkoret för mergen av PR #30.

## Vad kartläggningen visade (orsakerna)

**ScrapeGraph** (allt går genom `research_tools.py:118` `_hamta_via_scrapegraph`):
- En Iris-körning med N=5 gör cirka 60–70 anrop.
  - 4–10 listsidor. Loopen i `merinfo.py:558-578` slutar inte när målet är nått.
  - Upp till 30 bolagssidor per runda (`mal = antal*3`), och upp till 3 rundor.
  - 2–5 anrop per researchat prospekt.
- Varje filter körs **efter** att bolagssidan är betald: `kontrollera`, Jev, webbplatskravet och leverbarheten. I provet fälldes 5 av 8 först efter full research.
- Cachen är en processdict (`merinfo.py:73`) som försvinner vid varje deploy. Research-vägen (`leads_agent.py:550`) har ingen cache alls och hämtar om merinfo-sidan som redan hämtats.
- Startsidan hämtas tre gånger per prospekt: `webbsignal`, research och ScrapeGraph.
- **Bugg:** utan egen sajt blir merinfo-URL:en "hemsida" (`_gissa_hemsida`, `leads_agent.py:490`). Då skrapas tre merinfo-undersidor som "kontaktsidor".

**Bedömningen** (`bedomning.py:47-57`, `profil.py:376-405`, `merinfo.py:606-665`):
- Citatkontrollen kollar bara att citatet finns, inte vilket håll det pekar. "Ingen webbplats hittades" kan därför styrka både "ja" (100 p) och "nej" (C).
- Regeln `utan_webbplats` (d65de7f) ligger inuti den opålitliga omslaget. Modellen är instruerad att ignorera den.
- merinfo-läget kastar alltid bolag utan sajt. Det motsäger d65de7f.
- Jev får inga webbsignaler på merinfo-vägen (`signaler=[]`).
- Webbsignalerna är grova: copyright-år, generator, jQuery, tabeller och svarstid. Ingen bedömer hur sajten faktiskt ser ut.
- **Regelbrott:** merinfos bolagssida ingår i researchens källmaterial (72db2cf). Då blir "Beslutsfattare: Reino Börjesson, Styrelseledamot · 070-…" leadets kontakt, och det bryter mot reglerna 1 och 3 från 2026-10-04.

**Inkorgen** (`klassning.py`, `processor.py:460-485`):
- Main kör kod utan klassning, och development fick Alunix rader via nattspegeln från main.
- På development faller allt Jev är osäker på (under 0,9, timeout, ingen nyckel) tillbaka till `support`. Med tom kunskapsbas eskaleras då allt (grundningsregeln).
- Headers som `List-Unsubscribe`, `Auto-Submitted` och `Precedence` slängs i `connectors/imap.py:162-181`.
- No-reply-kontrollen matchar bara ett prefix, så `CloudPlatform-noreply@`, `notifications@` och `team@` slinker igenom.
- Det finns ingen Ej relaterat-vy (`Dashboard.tsx:294`), och `/klassa`-endpointen används inte.
- `sortera` stänger inte ärendet och avvisar inte utkastet.
- `mailbox_id` sparas aldrig (`postgres.py:2540`).

**Gränssnittet:**
- Översikten räknar på klientsidan ur listor som kapas vid 200 rader (`Oversikt.tsx:639-774`).
- `GET /api/analytics/weekly` finns men används bara i den dolda `Analys.tsx`. `recharts` är installerat men importeras ingenstans.
- `IrisKorningar.tsx` finns färdig men ligger gömd under Aktivitet.
- Mejlutkast-felet: `lasOffertForUtkast` (`lib/actions/affarskontext.ts:251-272`) kastar ett fel som Next.js döljer i produktion. Felet uppstår när affärskontexten ("Vad ni säljer") saknas för vyn.

## Bedömning: Firecrawl eller ScrapeGraph

Kostnadsskillnaden är liten. Det som kostar är antalet anrop.

| | ScrapeGraph | Firecrawl |
|---|---|---|
| Gratis | 500 krediter, en gång | 1 000 krediter per månad |
| Instegsplan | $20 för 10 000 krediter ($2 per 1 000) | $16 för 5 000 ($3,2 per 1 000, årsbetalning) |
| Sida som markdown | 1 kredit | 1 kredit |
| Strukturerad JSON | 5 krediter | 1 + 4 krediter |
| Skärmbild | 2 krediter | ingår i scrape |

- **Firecrawls styrka är crawl av hela domäner.** Den behöver vi inte: vi vet vilka 1–4 sidor vi vill ha.
- **ScrapeGraphs extract bedömer inte "DOM-struktur" visuellt.** Den kör en språkmodell över sidans text eller html. Om en sajt *ser* modern ut avgörs bara av en skärmbild plus en bildmodell, och det går att göra med vilken leverantör som helst.
- **Påståendet att Firecrawl hämtar mer pålitligt** (anti-bot, JS-rendering) är rimligt men obevisat för just våra sajter.
- Rekommendation:
  - Byt inte nu. Gör anropen färre (fas 2).
  - Låt allt gå genom en enda hämtfunktion.
  - Mät sedan Firecrawls gratisnivå mot ScrapeGraph på 20 riktiga URL:er där vi misslyckas i dag: merinfo, Vicht (svarade inte på 10 s) och JS-sajter. Det tar en timme och ger ett beslut på fakta (fas 7).
- När allabolag-API:t kommer (utkast i `docs/utkast-allabolag-api-forfragan.md`) försvinner merinfo-skrapningen helt. Det är det största anropsposten.

## Fas 1 — Inkorgen sorterar rätt (villkor för mergen av PR #30)

1. **`connectors/imap.py:162-181`:** räkna ut `automatutskick: bool`. Den sätts av `List-Unsubscribe`, `List-Id`, `Auto-Submitted≠no`, `Precedence: bulk|list|junk` eller `X-Auto-Response-Suppress`. Bär den på `InboundEmail` (`models.py`) och spara den i `ss_emails.automatutskick`.
   - Ny migration 092 för kolumnen.
   - Fixa samtidigt att `mailbox_id` sparas: `ingest.py` och `save_email`.
2. **`klassning.py`:** ny regel 1, före Jev, som sätter `ej_relaterat` (källa `kod`) om något av följande gäller:
   - `automatutskick` är sant
   - avsändarens lokaldel innehåller `noreply|no-reply|donotreply|notifications?|mailer-daemon` var som helst
   - `_NYHETSBREV` träffar brödtextens sista 1 500 tecken
3. **Osäkerhetsregeln:** om Jev är osäker *och* avsändaren är automatisk blir mejlet `ej_relaterat`, inte support. Ett mänskligt mejl utan träff i kunskapsbasen eskaleras fortfarande. Det är grundningsregeln, och den rör vi inte.
4. **`api/inbox.py:490` `sortera`:** när förslaget tillämpas och klassen blir icke-support:
   - stäng ärendet (`resolved`, orsak "omklassat")
   - avvisa det väntande utkastet
   - nytt läge `status=escalated|awaiting_approval` så att gamla rader går att sortera om i bulk, inte bara 25 synliga
5. **Ej relaterat-vy:** lägret `ej_relaterat` i `Dashboard.tsx` (`params.set("klass","ej_relaterat")`), som fliken "Dolda" i `SupportWorkspaceTabs.tsx`. Varje rad får knappen "Flytta till kundtjänst", som anropar befintliga `POST /api/inbox/{id}/klassa`.
6. **Omsortera Alunix och admin på development:** först torrkörning, sedan tillämpa. Samma körning mot main efter mergen.

Test:
- `test_klassning.py`: headerfall, noreply mitt i lokaldelen, osäker Jev plus automatisk avsändare.
- `test_inbox_sortera.py`: ärendet stängs och utkastet avvisas.

## Fas 2 — Iris billigare utan sämre underlag

Mål: Iris N=5 ska kosta ≤ 20 krediter (i dag cirka 65), och en lista med 15 rader ≤ 25 (i dag cirka 50).

1. **Beständig cache:**
   - Tabellen `leads_sidcache(url pk, innehall text, format, hamtad_at, status)`, ny migration 093.
   - Cachen sitter i den enda hämtfunktionen `hamta_sida(url)`. Den ersätter både `merinfo.hamta` och `_scrape_registered_source_impl`.
   - Livslängd: listsidor 7 dagar, bolagssidor 30 dagar, webbplatser 14 dagar.
   - Misslyckade hämtningar cachas 1 dygn, så att vi inte betalar för samma fel två gånger.
2. **Rätt ordning, billigast först** (`merinfo.sok`):
   - a. Listsida → rader med namn, orgnr och URL.
   - b. Kodfilter på raden, utan att något hämtas:
     - orgnr som redan finns hos kunden, i vilken status som helst
     - orgnr avvisat för samma profil de senaste 30 dagarna (ny tabell `leads_avvisade(tenant, orgnr, profilhash, orsak, at)`, samma migration)
     - icke-AB-orgnr när profilen utesluter enskild firma (`ar_enskild_firma` på orgnr)
   - c. Bolagssidor hämtas **i takt med behovet**: `behov*2` åt gången. Fler bara om det inte räckte. Listloopen bryts när målet är nått.
3. **Webbplatsen hämtas en gång** med httpx (gratis) till ett `HamtadSida`-objekt. Samma objekt matar `webbsignal`, `platshallare`, kontaktjakten och researchen. ScrapeGraph används bara som reserv, när httpx misslyckas eller sidan är tom/JS-renderad (under 500 tecken text). I dag är det tvärtom.
4. **Researchen återanvänder** den merinfo-sida som `sok` redan hämtat. Den ges via kandidaten, så den hämtas inte en gång till.
5. **Bugg:** kontaktlänkar letas bara på bolagets egen domän, aldrig på merinfo (`_gissa_hemsida` och `extrahera_kontaktlankar`).
6. **Kredittak per körning:**
   - `LEADS_SKRAP_TAK` (default 40) räknas i hämtfunktionen.
   - Är taket nått avslutas körningen med `slut_orsak="kredittak"`, och den ärligt redovisade summan visas.
   - Antal anrop per fas (lista, bolag, webb, research) sparas i `korning.skrap` i ledgern och visas i Körningar (fas 4).
7. **Leverbarheten flyttas före researchen.** Saknas en VD-kontakt på webbplatsen (`hamta_vd_kontakt`, httpx) körs ingen dyr research. Bolaget går till listspåret (fas 3.5).

Test:
- cacheträff över omstart (MemoryStorage-motsvarighet)
- förfilter hoppar över kända orgnr
- listloopen bryts
- taket avslutar körningen
- merinfo-domänen ger inga kontaktlänkar

Ett anropsräkningstest med fejkad hämtfunktion låser budgeten: N=5 ger högst 20 anrop.

## Fas 3 — Webbplatsbedömning och poäng som håller

1. **Kodsignaler ur html:en** vi redan har (gratis), i `webbsignal.py`:
   - layout: flex/grid i inline-CSS och den första länkade stilmallen, tabellayout
   - animation: gsap, framer, lottie, aos, swiper, `@keyframes`, `scroll-behavior`, `IntersectionObserver`
   - plattform och version: WordPress, Wix, Squarespace, Webflow, Next, React
   - mobil: viewport och bildformat (webp/avif)
   - övrigt: antal menyval, copyright-år, https, sidvikt
   - Signalerna är fakta, inte omdömen.
2. **Skärmbild plus mätvärden från Google PageSpeed Insights:**
   - Det är gratis: mobil- och desktopkörning, Lighthouse-poäng för prestanda/tillgänglighet/SEO, LCP och slutlig skärmbild.
   - Det ger också säljargument till mejlet: "er sida tar 7,8 s att ladda på mobil".
   - Reserv: ScrapeGraphs `screenshot`-format (2 krediter).
   - Körs bara för bolag som klarat steg 2b–c och 3, alltså cirka 5–10 per körning.
3. **Visuell bedömning med befintlig vision-sidovagn** (`llm.py`, `gemini-2.5-flash`):
   - Publika bolagssajter, ingen kunddata, så dataskyddsbeslutet berörs inte.
   - Strikt JSON-schema byggt på Antons prompt plus tillägg:
     - `navigering_tydlig`
     - `hero_modern`
     - `layout_era` (tabeller/tidig responsiv/modern flex-grid)
     - `animationer` (kodsignalen avgör; skärmbilden kan inte se rörelse)
     - `mobilanpassad`
     - `typografi_och_luft`
     - `bildkvalitet`
     - `fortroende` (kontaktuppgifter, referenser, cookie/GDPR)
     - `uppskattat_byggar`
     - `modernitet_1_10`
     - `top_3_brister` med konkreta, synliga fel
     - `intern_eller_internationell` (koncern, flera länder, bara engelska)
   - Kodsignalerna skickas med som fakta, så att modellen inte gissar mot dem.
4. **Webbkriterier avgörs i kod, inte av fri modell** (`bedomning.py`):
   - `modernitet ≤ 4` eller parkerad domän: TRAFF
   - `modernitet ≥ 7`: MISS (Björkekärr, Eustaff)
   - däremellan: OKÄNT/gränsfall (Ställningskompaniet)
   - Citatvägen för webbkriterier tas bort, så att samma citat inte kan styrka båda hållen.
   - `intern_eller_internationell=internationell` sätter målgruppskriteriet till MISS (Ostia).
5. **Utan webbplats → listspåret, alltid:**
   - Iris kräver sajt och VD-kontakt, enligt regel 4.
   - Bolag utan sajt, med parkerad domän eller utan VD-kontakt på sajten sparas inte som Iris-lead. De läggs i kundens lista "Utan webbplats" med bolagsfakta, så att utkast med ett generellt erbjudande kan skapas senare.
   - Regeln `utan_webbplats` flyttas ut ur det opålitliga omslaget och blir kod (routing), inte prompttext. Då försvinner självmotsägelsen.
6. **Kontaktläckan:**
   - Telefon- och personrader tvättas bort ur merinfo-materialet innan det når researchprompten. Merinfo får bara ge bolagsfakta.
   - Researchens `contact_*` godtas bara från källor på bolagets egen domän.
   - Befintliga leads med kontakt från merinfo på development flaggas och körs om.
7. **Jev får webbinfo:** webbkriterier lämnas till steg 4. Jev frågas bara om bransch, målgrupp och koncerntillhörighet.
8. **Kalibreringsset** med Antons facit som fixtur (html plus förväntat utslag) i `tests/leads/test_webbedomning_facit.py`:

   | Bolag | Förväntat |
   |---|---|
   | Byggarna Berggren | TRAFF |
   | Vicht | TRAFF |
   | Torbens (parkerad) | listspår |
   | Ställningskompaniet | gränsfall |
   | Björkekärr | MISS |
   | Eustaff | MISS |
   | Ostia | MISS på målgrupp |

   Kodsignalerna testas deterministiskt. Visionsteget testas med inspelat svar. Ett skarpt prov körs en gång manuellt och jämförs med facit.

## Fas 4 — Leads-sektionen

1. **Underflikar** i `IrisBolag.tsx` `SEGMENT`: **Leads · Inkorg · Utkast · Listor · Körningar**.
   - Synkas med `?vy=` via `router.replace`.
   - Visas också som `children` under Leads i rälsen (`lib/routes.ts`; `Rail.tsx:190` stödjer det redan).
   - Tabell och Pipeline försvinner som flikar. Gamla `?vy=tabell|pipeline` leds om till `leads`.
2. **Leads-vyn i full bredd**, en tabell som ersätter alla tre gamla vyerna:
   - Överst en **statusremsa**: Ny 14 · Research · Redo · Kontaktad · Svarat · Möte · Vunnen · Förlorad. Varje steg är en klickbar räknare som filtrerar. Det är pipelinen i kompakt form.
   - Därunder filterraden och sparade vyer (flyttade från `LeadsTabell`).
   - Varje rad visar:
     - bolag, ort och domän
     - statuschip med inline-byte (PATCH som i dag)
     - poäng och nivå
     - modernitetsbetyg och topp-brist (från fas 3)
     - kontaktväg
     - senaste händelse
     - nästa uppgift
     - typ (Iris/Import/Lista)
     - motiveringens första rad
   - Klick på en rad öppnar **detaljen som en låda från höger** (cirka 640 px, `?lead=id`, Esc stänger, fokusfälla). Där ligger Bedömning, Mejlutkast och Tidslinje som i dag. "Välj ett lead i listan" försvinner.
   - Mobil: lådan blir helskärm.
   - Kanban-dragningen tas bort. `Pipeline.tsx` och `LeadsTabell.tsx` slås ihop till den nya tabellen, och döda filer raderas.
3. **Inkorg:** `IrisInkorg` flyttas hit från Att göra. **Utkast:** `IrisGranskning` flyttas hit.
4. **Körningar:**
   - `IrisKorningar` monteras som den är.
   - Regexarna `bas` (`IrisKorningar.tsx:147`, `LeadsRunForm.tsx:295`) och omdirigeringen i `WorkspaceSection.tsx:168` rättas.
   - "Följ körningen" leder hit.
   - Visar krediter per fas och slut-orsak (från fas 2.6).
5. **Mejlutkast-felet:** `lasOffertForUtkast` och de tre syskonen (`Bolagsregister.tsx:185`, `Bolagssida.tsx:280`, `LeadslistorView.tsx:908`) returnerar `{ok:false, error}` i stället för att kasta. Meddelandet är tvåspråkigt och länkar till "Vad ni säljer" i inställningarna.

## Fas 5 — Att göra blir en kö, inte en scroll

- **Överst en sammanfattningsrad** med räknare som länkar: "3 eskalerade ärenden · 2 svar från leads → Leads › Inkorg · 5 utkast → Leads › Utkast".
- **En prioriterad lista** ersätter de fem sektionerna, ordnad efter vikt: eskalerat kundärende, svar från lead, svar att godkänna, utkast och larm. Fem rader per grupp visas, plus "Visa alla (N)" som expanderar på plats.
- **Larm grupperas på ämne** med räknare. I stället för 12 likadana "[PRIORITERAT] Supportärende eskalerat — Övrigt" står det en rad med "×12".
- Leadsinkorgen och utkasten finns bara under Leads. Inget dubbelt.

## Fas 6 — Översikten som dashboard (Upsales-inspirerad)

**Backend:** nytt `GET /api/oversikt?period=7|30|90`. Räknar på servern så att 200-taket försvinner och återanvänder `analytics/weekly`. Det returnerar:
- KPI:er med föregående period, för att visa utvecklingen
- veckoserier
- pipelinetratten med konvertering
- pågående körning
- topp-leads
- topp 5 i att göra-kön
- kundtjänstens självlösningsgrad och kategorier

**Layout** (recharts, husets tokens, tvåspråkigt):
- **Huvud:** "God morgon, {namn}" och dagens datum, samt en mening om vad Snajp gjorde sedan sist ("Iris hittade 6 bolag, kundtjänsten löste 14 av 23 ärenden själv"). Periodväljare 7/30/90 dagar.
- **Fyra KPI-kort** med stor siffra, förändring mot föregående period (pil och procent) och sparkline: leveranser från Iris, svar från leads, möten bokade och ärenden lösta av Snajp.
- **Tratt-kort:** Ny → Kontaktad → Svarat → Möte → Vunnen som horisontell tratt med konvertering mellan stegen. Klick leder till Leads filtrerad på steget.
- **Aktivitetsgraf** över 8–12 veckor (ytdiagram): skickat, svar och nya leads.
- **Live-kort för Iris:** pågående körning med förloppsstapel, levererade av mål och krediter. Annars senaste körningen och knappen "Kör Iris".
- **"Att göra nu":** topp 5 från kön. **"Hetaste leads":** topp 5 på poäng och senaste händelse, med modernitetsbetyg.
- **Kundtjänstens hälsa:** ring för självlösningsgrad och kategoristaplar.
- **Tomlägen** som säger vad nästa steg är, inte en nolla. Demoläget får motsvarande fixtur i `lib/demo/oversikt.ts`.

## Fas 7 — Mät Firecrawl (beslutsunderlag, ingen ombyggnad)

Skriptet `scripts/jamfor_skrapare.py` hämtar samma 20 URL:er med båda tjänsterna: 5 merinfo, Vicht, JS-tunga sajter och några i facit. Det mäter lyckade hämtningar, textmängd, tid och krediter. Firecrawl körs på gratisnivån. Anton skapar kontot och lägger nyckeln via `api-key-setup`. Byte sker bara om Firecrawl lyckas klart oftare på det vi misslyckas med.

## Ordning och leverans

- Fas 1 → 2 → 3 → 4 → 5 → 6. Fas 7 när Firecrawl-nyckeln finns.
- Allt går till `development`. En commit per delsteg.
- Migrationerna 092 och 093 körs mot development med `scripts/railway_migrate.py` (torrkörning först) och mot main före release.
- PR #30 växer med detta. Mergen och mainmigrationerna är fortfarande Antons ord.
- **Antons handgrepp:**
  - fylla på ScrapeGraph-krediten. Rekommendation: engångspåfyllnad på $5 för 1 000 krediter räcker länge efter fas 2; Starter $20/mån behövs inte än.
  - Firecrawl-konto (fas 7)
  - eventuellt en Google API-nyckel för PageSpeed (fungerar utan nyckel med lägre gräns)

## Verifiering

- **Backend:** `pytest snajp-support/tests` (hela sviten grön, nya tester enligt varje fas), plus anropsbudgettestet och facittestet.
- **Frontend:** `npx tsc --noEmit`, `pytest tests/invariants` (INV-COPY-001 och INV-UI-001), och a11y-audit på Leads-lådan och dashboarden.
- **Visuellt:** granskas själv mot `python scripts/lokal_stack.py --apply` med syntetisk data. Development speglar kunddata, så inga skärmdumpar därifrån. Skrivbord och mobil, ljust och mörkt.
- **Skarpt prov på development:**
  - Iris N=5 på Alunix: krediterna läses ur ledgern (`korning.skrap`) och ScrapeGraphs dashboard. Mål ≤ 20.
  - Facitbolagen jämförs med utslagen.
  - Omsorteringen av Alunix inkorg: inga nyhetsbrev eller driftlarm kvar som eskalerade.

## Antons beslut 2026-10-05 (fas 3.5)

Listspåret för bolag utan webbplats: registrets telefonnummer **får** användas när VD är den enda personen i bolaget. Villkor i kod: en anställd (eller färre) och VD är ende person med roll på bolagssidan, inga övriga ledamöter. Då räknas numret som VD:s (regel 5). Annars sparas raden med bolagsfakta och VD:ns namn utan nummer. Undantaget skrivs in i CLAUDE.md/AGENTS.md under "Leads: källor, filter och kontakter" som ett preciserat undantag från regel 1, och testas i `test_merinfo.py`.


## Läge 2026-10-05 (conclude)

### Completed
- [x] Fas 1–6 byggda, testade (backend 2557, invarianter 433, tsc, axe) och driftsatta på development.
- [x] Flytta till main lagad (095, bedömningen följer med); 092–095 körda mot main.
- [x] Release-PR #31 öppen.

### Remaining
- [ ] Antons merge av #31.
- [ ] Skarpt Iris-prov N=5 på Alunix efter ScrapeGraph-påfyllning.
- [ ] PAGESPEED_API_KEY (Anton).
- [ ] Fas 7 Firecrawl-mätning (väntar på konto).

### Next Steps
- Se `HANDOFF-2026-10-05-IRIS-KOSTNAD-YTOR.md` § 3.
