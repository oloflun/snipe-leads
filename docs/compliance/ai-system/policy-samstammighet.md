# AI-policyn mot Snajps övriga policyer (ISO 42001 A.2.3)

| | |
|---|---|
| Status | **UTKAST 2026-11-18. Gäller först när Anton har godkänt P27.** Förslagen nedan är inte beslutade |
| Skrivet av | Claude (agent), på Antons uppdrag |
| Granskas och godkänns av | Anton |
| Krav | ISO 42001 A.2.3 *Alignment with other organizational policies*; ramverkets uppgift 20 *AI Policy Alignment Review* (`../ramverk/iso42001/uppgifter.md` rad 45), årligen |
| Lästa versioner | P27 och P28: `../ramverk/iso42001/policyer/`. G01–G06: `../ramverk/gdpr/policyer/`. P07–P26: `../ramverk/iso27001/policyer/`. Alla utkast 2026-11-17, ingen godkänd. Kod och CI lästa på `development` e1ebbbdc |
| Nästa genomgång | När P27 godkänns (då med de beslutade ändringarna), sedan årligen och när någon av policyerna ändras i ett avsnitt som listas här |

## Varför genomgången finns och vad den inte är

A.2.3 kräver att AI-policyn inte säger emot de andra styrdokumenten och att det som
hör ihop hänvisar till varandra. P27 avsnitt 10 pekar ut genomgången och lägger den
på agenten med Antons granskning.

Genomgången är ett underlag. Den ändrar ingen policy. Alla 28 policyer är osignerade
utkast, så det finns ännu inget beslutat dokument att stämma av mot. Därför gäller den
här texten först när P27 är godkänd, och den ska göras om mot de versioner som då
godkänns. Förslagen står som *förslag* och blir regler först genom Antons beslut.

## Metod

P27 lästes avsnitt för avsnitt mot var och en av de 27 andra policyerna. För varje
policy anges:

- **Möts:** var de reglerar samma sak och säger samma sak, med avsnitt.
- **Krock:** två regler som inte båda kan följas, eller som säger olika om samma sak.
- **Glapp:** något som faller mellan policyerna, så att ingen av dem täcker det.
- **Inaktuellt:** ett faktapåstående som inte längre stämmer med repot eller driften.
  Det är ingen krock i sak, men en policy med fel fakta går inte att stämma av.
- **Förslag:** ändringen, och i vilken policy den görs.

Påståenden om läget i dag är kontrollerade mot koden, CI och `../railway-baslinje.json`
den 2026-11-18. En hänvisning till en annan fil betyder att den lästs.

## Sammanfattning

27 policyer genomgångna. **6 krockar, 19 glapp** och 13 policyer med inaktuella
påståenden. Fyra policyer har ingen beröring med AI-policyn i sak (P14, P17, P22, P23);
två av dem har ändå inaktuella fakta.

De sex krockarna, i den ordning de bör lösas:

1. **Omfånget.** P27 avsnitt 1 gäller supportagenten, Iris och Jev. Snajp har sju
   AI-system (`README.md` här): också kvittohanteraren, webbrevisionens bildbedömning,
   Email Studio och kvitto-assistenten med den äldre bokföringsytan. G01 och P07 räknar
   kvittohanteraren till omfånget. Godkänns P27 som den står gäller AI-policyn inte för
   fyra system som behandlar kunddata med Gemini.
2. **AI-kodverktygen.** P27 avsnitt 1 tar med AI-kodverktygen i omfånget, och avsnitt 6.1
   säger att ingen ny modelleverantör får kunddata förrän Anton godkänt den. P13, P20,
   P26 och G02 konstaterar att kodverktygen i dag läser testmiljön, som är en spegel med
   riktig kunddata. Godkänns P27 utan ändring blir dagens arbetssätt ett avsteg från den
   dag policyn börjar gälla.
3. **Två godkännandeordningar för leverantörer.** G06 har sju steg, P27 avsnitt 6 fem.
   De skiljer sig: P27 saknar förhandsbeskedet till kunderna (G06 steg 6, art. 28.2) och
   överföringsbedömningen (G06 steg 3), och listar tre förteckningar där G06 listar fyra.
4. **Avsteg.** P27 avsnitt 9 lägger avsteg i `docs/BESLUT.md` "som enligt P08". P08 lägger
   dem i ett undantagsregister (`loggar/undantag.md`) och kräver att Sebbe läst ett avsteg
   som Anton själv begär. P27 saknar den kompenserande kontrollen.
5. **Konsekvensbedömningens utlösare.** G06 kräver en DPIA vid sex utlösare, P27 avsnitt 8
   en AI-konsekvensbedömning vid fyra andra. Samma ändring (till exempel ett nytt
   automatiskt svar) kan alltså kräva den ena men inte den andra.
6. **Radhänvisningar som glider.** P27 hänvisar till `docs/BESLUT.md` med radnummer
   (101-158, 1647-1664, 2095-2098). BESLUT skrivs med nyaste överst, så raderna flyttar
   sig vid varje nytt beslut. Rad 101 handlar i dag om inloggningsspärren, inte om
   "belägg eller överlämning". Samma sak gäller `config.py:609-700` för DeepSeek-spärren,
   som i dag står i `llm_provider_fault` (`snajp-support/app/config.py:776`).

Det största glappet: **AI-fel utan personuppgifter har ingen incidentrutin.** P27 avsnitt
10 säger att de ska loggas enligt G03, men G03 gäller personuppgiftsincidenter och
nämner inte AI-fel (ISO 42001 A.8.4, 10.2).

## Tvärgående fynd

Det här gäller flera policyer och står därför en gång.

**T1. Repot är privat sedan 2026-11-18.** G02, G05, P08 och P28 säger att repot är
publikt och att `docs/compliance/` hålls utanför git. Båda delarna är fel sedan PR 67 och
2026-11-18 (`../bevis/github-2026-11-18.txt`). Regler som bygger på det ("inte i det
publika repot", P15, P16, P18, P28) behöver en ny formulering: *inte i git* om det inte
ska ha historik, annars i `docs/compliance/`.

**T2. Tre vägar att säga till, med samma tomma kontakt.** P16 ("Att säga till"), P27
avsnitt 8 och P28 ("Den som anmäler") beskriver var för sig vart oro tas upp, alla med
"[FYLL: extern kontakt]". Den enda väg som finns, ärendemallen
`.github/ISSUE_TEMPLATE/ai-oro.yml`, nämns i ingen av dem. Förslag: P28 blir den enda
platsen; P16 och P27 hänvisar dit; mallen nämns där.

**T3. Driftvariabler som byter AI-beteende.** P19 och P21 säger att variabler som styr
dataflöden ändras bara efter beslut i BESLUT.md, och P27 avsnitt 6.5 säger samma sak för
AI-variablerna. Det stämmer. Det de inte säger är hur en ändring upptäcks. Sedan
2026-11-18 finns ett sätt: `scripts/railway_baslinje.py --jamfor` jämför driften mot
`../railway-baslinje.json`, som visar värdena för `INKORG_JEV`, `IRIS_JEV`,
`LLM_PROVIDER`, `MODEL` och alla `*_MODEL` per miljö. Jämförelsen kördes 2026-11-18
19:10 UTC med noll avvikelser. Förslag: P19, P21 och P27 avsnitt 6.5 hänvisar till samma
rutin (`--jamfor` före och `--skriv` efter varje ändring).

**T4. Systemägare.** P27 avsnitt 5 har två roller "[FYLL]". G06 sätter Anton som ägare
av alla leverantörer, P09 som ägare av alla risker. Inget krockar så länge Anton äger
allt, men när systemägarna i P27 utses behöver G06 och P09 säga att systemägaren äger
AI-leverantörens och AI-riskernas uppföljning.

## Policy för policy

### G01 Compliance & Regulatory Monitoring

- **Möts:** G01:s förteckning över skyldigheter tar upp AI-förordningen art. 50
  (upplysningen), som P27 regel 6 genomför.
- **Glapp:** förteckningen saknar AI-förordningen art. 4 (AI-kunnighet, gäller sedan
  2025-02-02), som P27 avsnitt 8 bygger på, och hänvisar inte till
  `../ramverk/iso42001/ai-forordningen.md` där skyldigheterna är kartlagda.
- **Förslag (G01):** lägg till art. 4 och en rad "AI-förordningen i övrigt: se
  `ai-forordningen.md`". Låt årsgenomgången av bevis också omfatta ISO 42001-matrisen.

### G02 Data Classification & Handling

- **Möts:** klassningen gör `agent_runs` (fulla promptar) till Begränsad, och G02 kräver
  att Begränsad data bara går till leverantörer godkända enligt G06; P27 avsnitt 6 säger
  samma sak för modelleverantörer. Maskeringen av personnummer före Vertex står i båda
  (G02 "Överföring", P27 regel 7). DeepSeek-spärren och att modellen inte kan skicka
  står i båda (G02 "Inbyggt dataskydd", P27 regel 2 och 8).
- **Krock:** se krock 2. G02 säger att AI-kodverktygens läsning av spegeln "ska
  regleras"; P27 förbjuder den i praktiken från godkännandet.
- **Glapp:** G02 säger att hälsouppgifter i löptext inte maskeras. P27 regel 7 säger bara
  att personnummer maskeras och tiger om resten, så restrisken (DPIA R1) står i ingen
  policy som accepterad.
- **Inaktuellt:** `docs/compliance/` "undantagen från git, eftersom repot är publikt"
  (T1).
- **Förslag (P27):** regel 7 får tillägget "Hälsouppgifter i löptext maskeras inte;
  restrisken är [accepterad/behandlas] enligt DPIA R1". **(G02):** rätta T1.

### G03 Incident Response & Breach Notification

- **Möts:** G03 gäller också AI-kodagenter som stöter på exponerad persondata (de stoppar
  och rapporterar). P28 steg 1 och G03 löper parallellt, som båda säger.
- **Glapp (det största):** P27 avsnitt 10 säger att AI-fel utan persondata ska loggas
  enligt G03. G03:s syfte och omfång är personuppgiftsincidenter; den har ingen kategori
  för ett felaktigt automatiskt svar, ett påhittat utkast som gått ut eller en modell som
  slagits på utan beslut. Matrisens A.8.4 och 10.2 har samma gap.
- **Förslag (G03):** ett avsnitt "AI-incidenter": vad som räknas (svar eller utkast med
  ostödd uppgift som nått en mottagare, autonomi som gått utöver kundens val, modell eller
  leverantör påslagen utan beslut), att de loggas i samma incidentlogg, att kunden
  underrättas när dennes kunder fått ett felaktigt svar, och att åtgärden blir en
  invariant med test (P27 regel 1). Ärendemallen `ai-oro.yml` blir en ingång.

### G04 Privacy & Data-Subject Rights

- **Möts:** PR-7 (automatiserade beslut): supportagenten levereras med Utkast, kunden väljer
  Auto och bär bedömningen (G04 "Automatiserade beslut", P27 avsnitt 3). AI-upplysningen
  (G04, P27 regel 6).
- **Krock (mild):** G04 kräver att kunden bekräftar autonominivån skriftligt vid
  onboarding (`docs/pilot_onboarding.md` steg 6). P27 avsnitt 3 säger att kunden väljer och
  ansvarar, men inte att valet ska bekräftas. Den som läser P27 ensam missar kravet.
- **Glapp:** för Iris är Snajp ansvarig för egna kallmejl (G04 "Omfattning"), men ingen av
  policyerna säger om prospektet får veta att mejlet skrevs med AI (matrisen A.8.2).
- **Inaktuellt:** båda säger att AI-upplysningen "ska införas" (G04) eller är
  "ocommittad" (P27 regel 6). Den är mergad till `development` (INV-AI-001,
  `ARCHITECTURE_INVARIANTS.md` rad 965) och väntar på release till `main`.
- **Förslag (P27):** avsnitt 3 hänvisar till G04:s krav på skriftlig bekräftelse. Ett
  beslut om upplysning i kallmejl skrivs i P27 avsnitt 4 (Antons val, inte agentens).

### G05 Security & Privacy Awareness Training

- **Möts:** båda kräver kvittens före åtkomst.
- **Glapp:** G05:s utbildning tar inte upp AI-förordningen art. 4, P27 eller systembladen;
  P27 avsnitt 8 kräver en separat AI-genomgång med egen kvittens. Två genomgångar med två
  loggar för två personer.
- **Inaktuellt:** "Repot är publikt" (regel 1, T1).
- **Förslag (G05):** lägg AI-delen i G05:s innehåll (art. 4, P27, systembladen,
  `ai-forordningen.md`) och en kvittens i `loggar/utbildning.md`. **(P27):** avsnitt 8
  hänvisar dit i stället för att ha en egen genomgång.

### G06 Vendor & Third-Party Risk

- **Möts:** båda kräver godkännande innan en leverantör får kunddata och en kodspärr efter
  DeepSeek-mönstret. Båda tar TypeSafe som skälet.
- **Krock:** krock 3 (sju steg mot fem) och krock 5 (utlösarna för DPIA mot AI-bedömning).
- **Inaktuellt:** TypeSafe står som Hög "så länge inkorgsklassningen är på". Den är av
  (`INKORG_JEV=off` i båda miljöerna, `../railway-baslinje.json`), men TypeSafe får
  fortfarande leadsdata (`IRIS_JEV=pa` i `development`; `jev.md` avsnitt 8). Nivån behöver
  en ny motivering, inte strykas.
- **Förslag:** G06 är grunden för alla leverantörer. P27 avsnitt 6 skrivs om till "G06
  steg 1–7 gäller, och för en modelleverantör dessutom": evalsviten före och efter, raden i
  leverantörsgranskningen om träning på data, och beslutet med mätningen. Utlösarna för
  konsekvensbedömning samlas i en lista som både G06 och P27 hänvisar till (unionen av
  dagens tio).

### P07 Information Security & Privacy Governance

- **Möts:** ansvaret ligger hos Anton i båda. Omfånget i P07 tar med AI-kodverktygen, som
  P27.
- **Glapp:** P07 säger att "de andra 25 policyerna bygger på den"; P27 och P28 räknas inte.
  P07:s kommunikationsplan (krav 7.4) har ingen rad om vad som sägs om AI, till vem.
  P07:s ledningens genomgång (två gånger per år) och P27:s kvartalsrad i BESLUT.md om
  AI-ledningssystemet är två rytmer utan koppling.
- **Förslag (P07):** "de andra 27"; en rad i kommunikationsplanen: AI-upplysning och
  AI-incidenter till kunden. **(P10):** AI-underlag i ledningens genomgång (se P10). Då kan
  P27:s kvartalsrad bli underlaget dit, inte en egen process.

### P08 Policy Management & Exception Handling

- **Möts:** P27 avsnitt 9 hänvisar uttryckligen till P08.
- **Krock:** krock 4. P08 kräver undantagsregister och Sebbes läsning när Anton begär ett
  avsteg från sig själv; P27 avsnitt 9 nämner bara BESLUT.md.
- **Glapp:** P08:s förteckning är `policies` i ISO 27001-importen (26 policyer). P27 och
  P28 står i `../ramverk/iso42001/import.json`. Förteckningen behöver omfatta båda.
- **Inaktuellt:** "`docs/compliance/` är undantagen från git ... ingen versionshistorik" (T1;
  ISO 27001 och ISO 42001 7.5.3 är uppfyllda sedan 2026-11-18).
- **Förslag (P27):** avsnitt 9 lyder "Avsteg enligt P08 (undantagsregistret), med
  beslutet i BESLUT.md". **(P08):** förteckningen omfattar P27 och P28; rätta T1.

### P09 Risk Management

- **Möts:** P09 uppdaterar registret "när en driftvariabel ändrar dataflöden", vilket är
  P27 avsnitt 6.5 i riskens språk.
- **Glapp:** P27 har ingen riskmetod. Riskutkasten per AI-steg (`*.md` avsnitt 8 här)
  använder låg/medel/hög, P09 påverkan × sannolikhet 1–5 med acceptansnivå 12. AI-riskerna
  kan alltså inte jämföras med säkerhetsriskerna eller accepteras enligt P09 (ISO 42001
  6.1.1–6.1.3).
- **Förslag (P27):** ett avsnitt "Risker": AI-risker bedöms med P09:s skala och står i
  samma register (`risks` i importen), med systemägaren som riskägare. Agenten kan räkna
  om utkasten till P09:s skala när skalan är beslutad.

### P10 Internal Audit Procedure

- **Möts:** P10 säger att en AI-agent kan göra underlaget men att en människa drar
  slutsatsen; P27 avsnitt 10 lägger den här genomgången på agenten med Antons granskning.
- **Glapp:** underlaget till ledningens genomgång tar inte upp AI: evalresultat,
  AI-incidenter, ärenden från `ai-oro.yml`, modellbyten och avsteg från P27 (ISO 42001
  9.3.2). Revisionsprogrammet omfattar inte ISO 42001-matrisen.
- **Förslag (P10):** lägg till de fem AI-punkterna i underlaget och ISO 42001-matrisen i
  revisionens kriterier.

### P11 Access Control & Least Privilege

- **Möts:** inget i sak.
- **Glapp:** vem som får ändra en AI-variabel i Railway (P27 avsnitt 6.5) är en
  åtkomstfråga. P11 listar Railway-rollerna som "[FYLL]". `../privilegierade-verktyg.md`
  har ett förslag.
- **Förslag:** inget i P27. P11 tar in förslaget i `privilegierade-verktyg.md` när det är
  beslutat.

### P12 Authentication & Password

- **Möts:** tvåfaktor på TypeSafe och Google Cloud (AI-leverantörerna) ingår i P12:s lista.
- **Glapp:** ett servicekonto `snajp-vertex` i alla miljöer (JA #14) gör att testmiljön och
  produktionen delar AI-behörighet. Det rör P27 regel 9 (EU-regionen) indirekt men inte
  i sak.
- **Förslag:** inget i P27.

### P13 Acceptable Use & Workstation Security

- **Möts:** P13 förbjuder att kunddata klistras in i AI-tjänster utanför Snajps avtalade
  leverantörer. Det är den enda regeln om Snajps egen AI-användning (ISO 42001 A.9.2).
- **Krock:** krock 2. Regeln och P27 avsnitt 6.1 tillsammans gör AI-kodverktygens läsning
  av spegeln till ett avsteg om inte kodverktygens leverantörer räknas som avtalade.
- **Förslag (P27):** ett nytt avsnitt "Egen användning av AI" som tar in P13:s regel och
  säger hur kodverktygen behandlas: antingen godkända enligt avsnitt 6 med sina villkor,
  eller utan åtkomst till spegeln. Valet är Antons (matrisens fråga 7).

### P14 Remote Access & BYOD

Ingen beröring. Ingen ändring.

### P15 Background Screening, On- & Off-boarding

- **Möts:** avslutet roterar alla hemligheter, också `GEMINI_API_KEY` och `TYPESAFE_API_KEY`.
- **Glapp:** ISO 42001 A.4.6 kräver att det framgår vem som utvecklar, driftsätter och
  övervakar varje AI-system och med vilken kompetens. P15 tar inte upp AI-kompetens vid
  start.
- **Förslag:** löses med G05-förslaget ovan. Ingen ändring i P15.

### P16 Code of Business Conduct

- **Möts:** P16 gäller också AI-agenterna som agerar för Snajp, och "Ärlighet" (inga löften
  om funktioner som inte finns) är samma tanke som P27 regel 3 (belägg eller överlämning).
- **Glapp:** T2 (tre vägar att säga till). P16 säger att anonym rapportering inte är
  meningsfull; matrisen A.3.3 räknar avsaknaden som gap. Det är ett beslut, inte en krock,
  men det ska stå på ett ställe.
- **Förslag:** se T2.

### P17 Physical & Environmental Security

Ingen beröring. Ingen ändring.

### P18 Backup, Business Continuity & DR

- **Möts:** "Vertex AI nere" står i kontinuitetsplanen, med regeln att reservvägen till AI
  Studio inte får bära kunddata. Det är P27 regel 9 och INV-DATA-004.
- **Glapp:** planen saknar två AI-händelser: att en modell pensioneras (Gemini 2.5 har
  passerat pensionsdatumet, `../gemini-bedomning.md`) och att TypeSafe inte svarar (Jev
  faller öppet, `jev.md` avsnitt 8). Ingen av dem står heller i P27.
- **Förslag (P18):** två rader i kontinuitetsplanen: "Modell pensioneras: byte enligt P27
  avsnitt 6.4, evalsviten före och efter" och "TypeSafe nere: kandidaten går vidare utan
  Jev; ingen åtgärd".

### P19 Change & Release Management

- **Möts:** driftvariabler som styr dataflöden ändras bara efter beslut i BESLUT.md (P19,
  P27 avsnitt 6.5). Akuta ändringar dokumenteras i efterhand (P19), vilket är förenligt
  med P27.
- **Glapp:** P19:s test före ändring är CI. P27 avsnitt 7 kräver dessutom evalsviten före
  och efter en ändring av prompt, modell eller kedja; P19 nämner det inte, så en ändring
  kan följa P19 och bryta P27. INV-PROC-001 (frågan om AI-påverkan i varje PR) nämns i
  ingen av dem.
- **Inaktuellt:** "Grenskyddet kräver granskning av code owner" gäller inte sedan repot blev
  privat på gratisplanen (`../bevis/github-2026-11-18.txt`). Exemplet `INKORG_JEV=auto` är
  rättat i drift.
- **Förslag (P19):** under "Test och konsekvens": "En ändring av prompt, modell eller
  AI-kedja kräver evalsviten före och efter (P27 avsnitt 7). Varje PR besvarar frågan om
  AI-påverkan (INV-PROC-001)." Rätta grenskyddet.

### P20 Secure Software Development Lifecycle

- **Möts:** invarianterna med test (P20 "Säkerhetskrav", P27 regel 1); kodverktygen följer
  `CLAUDE.md` och granskas som andra (P20, P27 avsnitt 1).
- **Krock:** krock 2 (P20 "AI-kodverktyg": de läser testmiljöns kunddata).
- **Inaktuellt:** "Ingen skanning av beroenden i dag (`.github/dependabot.yml` finns inte)"
  och "gitleaks köras i CI" som framtid. Båda finns (`.github/dependabot.yml`;
  `.github/workflows/verify.yml` rad 50).
- **Förslag:** löses med P13-förslaget. Rätta de inaktuella raderna.

### P21 Secure Configuration & Hardening

- **Möts:** DeepSeek-spärren står i baslinjen (P21 "Uppstartsspärrar", P27 regel 8).
- **Glapp:** P27 avsnitt 6.5 planerar en kodspärr för ej godkända AI-leverantörer. Den hör
  hemma i P21:s baslinje när den finns, men står inte där. Avvikelsekontrollen ("ska
  införas", månadsvis) finns nu som `railway_baslinje.py` (T3).
- **Inaktuellt:** "Avsteg: `INKORG_JEV=auto`" (av sedan 2026-11-17); "Grenskydd finns" (T1,
  P19).
- **Förslag (P21):** baslinjen får raden "AI-leverantörer: bara godkända enligt P27
  avsnitt 6; läge per miljö i `railway-baslinje.json`". Avvikelsekontrollen hänvisar till
  skriptet.

### P22 Vulnerability & Patch Management

Ingen beröring i sak. Inaktuellt: "`.github/dependabot.yml` finns inte" (se P20).

### P23 Encryption & Crypto Controls

Ingen beröring i sak. Inaktuellt sedan mätningen 2026-11-18
(`../bevis/tls-2026-11-18.txt`): TLS 1.0 och 1.1 vägras, 1.2 och 1.3 accepteras; HSTS
saknades och läggs till i appen.

### P24 Information Sharing & Transfer

- **Möts:** maskeringen före Vertex och Jev (P24 "Minimering och maskering", P27 regel 7);
  överföring bara till godkända leverantörer.
- **Glapp:** P24 beskriver Jev-rensningen som adresser och telefonnummer
  (`jev.py:63-77`), P27 som personnummer (`jev.py:47`). Båda stämmer: funktionen
  `_utan_personuppgifter` (`snajp-support/app/leads/jev.py:77-80`) tar bort e-post,
  telefon och personnummer. Ingen av policyerna säger att personnamn går till TypeSafe
  (`jev.md` avsnitt 8, restrisk medel).
- **Inaktuellt:** "Avsteg i dag: kundmejl till TypeSafe utan avtal" (stoppat 2026-11-17).
- **Förslag (P27):** regel 7 hänvisar till `_utan_personuppgifter` och säger att namn inte
  rensas. **(P24):** rätta avsteget till leadsdata.

### P25 Logging, Monitoring & Audit

- **Möts:** `agent_runs` och `ss_decision_log` (P25 "Loggar som finns"); lagringstiden för
  `agent_runs` hänskjuts till G02 i båda.
- **Glapp:** P27 har ingen regel om loggning, fast ISO 42001 A.6.2.8 är uppfyllt genom den
  (alla tre instruktionslagren loggas per körning, `ARCHITECTURE_INVARIANTS.md`). P25:s larm
  tar inte upp AI-kvalitet i drift (ISO 42001 9.1, A.6.2.6).
- **Inaktuellt:** "Saknas: en logg över vad plattformsadmin läser och ändrar" (finns sedan
  migration 123, PR 85, i `development`); Railways loggtid "[FYLL]" (belagd i
  `../drift-och-tillgangar.md` §5).
- **Förslag (P27):** en grundregel "Varje AI-körning loggas med instruktionslagren; lagring
  enligt G02". **(P25):** under "Larm" en punkt om AI-mått när de är beslutade (P27 avsnitt 7).

### P26 Third-Party Processors & Vendors

- **Möts:** P26 räknar AI-kodverktygen (Claude Code, Codex) som leverantörer som ska stå i
  leverantörslistan.
- **Krock:** krock 2, och P26 löser den halvt: om kodverktygen står i listan och godkänns
  enligt G06/P27 försvinner krocken. Det beslutet är inte fattat.
- **Förslag:** samma som P13. P27 avsnitt 6 säger uttryckligen att kodverktygens
  leverantörer är modelleverantörer i policyns mening.

### P28 Sanctions & Disciplinary

- **Möts:** P28 gäller brott mot P27, med P27 avsnitt 6 som exempel på måttligt brott, och
  skyddet för den som anmäler (P27 avsnitt 8). Hänvisningarna går åt båda håll.
- **Glapp:** T2.
- **Inaktuellt:** "en rad som inte ligger i det publika repot" (T1).
- **Förslag:** se T2 och T1.

## Föreslagna ändringar i P27 (samlat)

| Nr | Avsnitt | Ändring | Löser |
|---|---|---|---|
| 1 | 1 | Omfånget är alla AI-system i `ai-system/README.md` (i dag sju), inte tre | Krock 1 |
| 2 | 1, 6, nytt | Nytt avsnitt "Egen användning av AI": P13:s regel, och hur kodverktygen behandlas (godkända enligt 6 eller utan åtkomst till spegeln). Antons val | Krock 2 |
| 3 | 6 | "G06 steg 1–7 gäller; för modelleverantörer dessutom ..." | Krock 3 |
| 4 | 9 | "Avsteg enligt P08 (undantagsregistret, Sebbes läsning), beslutet i BESLUT.md" | Krock 4 |
| 5 | 8 | Utlösarna hänvisar till en gemensam lista med G06 | Krock 5 |
| 6 | alla | Hänvisningar till BESLUT.md med datum och rubrik i stället för radnummer; till koden med funktionsnamn | Krock 6 |
| 7 | 2 regel 6 | "Gäller i `development`; i `main` från release" | Inaktuellt |
| 8 | 2 regel 7 | Vad som maskeras före Vertex och Jev, och vad som inte gör det (hälsouppgifter, namn) | G02, P24 |
| 9 | 2, ny regel | Loggning av varje körning, lagring enligt G02 | P25 |
| 10 | nytt | "Risker": P09:s skala och register | P09 |
| 11 | 3 | Kundens val bekräftas skriftligt enligt G04 | G04 |
| 12 | 8 | AI-kunnighet genom G05 | G05 |
| 13 | 8, 10 | Oro anmäls enligt P28; incidenter enligt G03:s nya AI-avsnitt | T2, G03 |
| 14 | 6.5 | Ändringar upptäcks med `railway_baslinje.py --jamfor` | T3 |

## Föreslagna ändringar i de andra policyerna (samlat)

| Policy | Ändring |
|---|---|
| G01 | AI-förordningen art. 4 och hänvisning till `ai-forordningen.md` |
| G02, G05, P08, P28 (och P15, P16, P18) | Repot är privat (T1) |
| G03 | Avsnitt om AI-incidenter |
| G05 | AI-delen i utbildningen, en kvittens |
| G06 | Grunden för leverantörsgodkännande; gemensam lista över utlösare; TypeSafes nivå motiverad på nytt |
| P07 | "De andra 27"; AI i kommunikationsplanen |
| P08 | Förteckningen omfattar P27 och P28 |
| P10 | AI-underlag i ledningens genomgång; ISO 42001-matrisen i revisionen |
| P18 | Modell pensioneras; TypeSafe nere |
| P19 | Evalsviten och INV-PROC-001 under test; grenskyddet rättat |
| P20, P22 | Dependabot och gitleaks finns |
| P21 | AI-leverantörer i baslinjen; avvikelsekontrollen är skriptet; `INKORG_JEV` rättat |
| P24 | Avsteget gäller leadsdata, inte kundmejl |
| P25 | Adminloggen finns i `development`; Railways loggtid; AI-mått under larm |

## Vad som återstår för att A.2.3 ska vara uppfyllt

1. Anton godkänner P27, och tar ställning till förslagen ovan: vilka som förs in, i P27
   eller i den andra policyn. Krock 1 och 2 kräver ett beslut i sak (omfånget och
   kodverktygen), de andra är redaktionella.
2. De policyer som ändras godkänns i samma omgång, så att genomgången kan göras om mot
   godkända versioner. Det är den versionen av den här filen som är belägget.
3. Genomgången upprepas årligen (uppgift 20) och när en policy ändras i ett avsnitt som
   står här. Agenten kan göra den; Anton granskar.
