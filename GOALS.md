---
type: goals
project_slug: snipe-leads
updated: 2026-09-02
updated_by: claude
---

# Mål — Snajp (Snipra / Snajp-Support)

## Vad projektet är och för vem

Snajp säljer AI-medarbetare till svenska företag. Det finns tre av dem i dag:
en **kundtjänstagent** som svarar på kundmejl och chattar utifrån företagets egen
kunskapsbas och hellre lämnar över till en människa än gissar, en **leads-agent**
som letar upp rätt företag att kontakta och skriver ett personligt mejl till dem
(inte massutskick), och en **bokföringsagent** som läser kvitton och fakturor och
föreslår kontering.

Kunderna är svenska små och medelstora bolag. Varje kund kallas i koden för en
"tenant" — en egen avskild del av samma system, med egen kunskapsbas, egna
inställningar och egen avgränsning i databasen, så att ingen kund kan se någon
annans data. Livrustning AB är första riktiga kunden och kör bara chatten, på
sin egen adress. Nordlys Handel är ett påhittat demobolag som används för att
visa produkten.

Två namn förvirrar lätt: **Snipra** är webbappen (dashboarden, inloggningen,
Email Studio) och **Snajp-Support** är Python-backenden där agenterna faktiskt
körs. Båda ligger i samma repo och säljs under varumärket Snajp.

## Vad "klart" betyder

**Det som står registrerat i dag** (i projektets hubbfil `snipe-leads.md`, skriven
av en agent — inte bekräftad av Anton, se Öppna frågor): nästa milstolpe är att
produktionen kör samma kod som utvecklingsmiljön, och att Livrustning svarat på
garantifrågan som agenten fastnat på.

**Föreslaget mått på att hela produkten är klar** (mitt förslag, ej beslutat): en
ny kund kan teckna, betala, få sin agent igång och få den att svara kunder och
skicka mejl — utan att någon i teamet kör ett skript för hand. Det målet är
tydligt inte nått i dag, och de två sakerna som saknas är konkreta:

- **Inget mejl skickas på riktigt.** Leads-agenten skriver utkast, granskar dem,
  kör dem genom språk-, tids- och faktakontroll, och lägger dem i en kö — och
  där tar det slut. Koden som ska skicka (`send_provider.py`) skriver bara en
  rad i loggen. API:t säger det rakt ut: "Utskick simulerat".
- **Ingen riktig betalning kan tas emot.** Kortformuläret tar med flit bara emot
  Stripes officiella testkortsnummer, för att ingen ska lära sig att skriva sitt
  riktiga kort på en yta som inte är byggd för det. Prislistan är däremot skarp.

## Delmål i ordning

- [x] 1. Kundtjänstagent som svarar ur kundens egen kunskapsbas och eskalerar
  i stället för att hitta på — byggd, kör i sju steg där varje steg är ett eget
  anrop till språkmodellen med sitt eget kontrakt på vad det ska svara.
- [x] 2. Leads-agent som researchar ett företag, skriver ett utkast och kör det
  genom en faktakontroll — byggd. Faktakontrollen (`grounding_gate.py`) fäller
  varje siffra, procent, belopp eller namngiven kund som inte går att belägga i
  underlaget; en reparationsrunda, sedan går det till en människa.
- [x] 3. Plattform för flera kunder samtidigt: inloggning, roller, inbjudningar,
  per-kund-avgränsning i databasen, adminvy, spårning av varje körning.
- [x] 4. Flytta all drift till Railway och lämna den gamla kedjan (Vercel, Render,
  Supabase) — gjord i augusti; koden deployar från grenarna `railway-main` och
  `railway-development`.
- [x] 5. Stäng de akuta säkerhetshålen som hittades i skarp drift: hela backend-
  API:t var anonymt åtkomligt, varje inloggad kunds inkorg pekade på demokunden,
  chattbubblan visade vår interna bedömning av kunden för kunden själv, och
  utvecklingsspegeln låg fritt sökbar på Google. Alla fyra åtgärdade och mätta.
- [x] 6. Få kundens egna instruktioner att faktiskt nå agenten. Två databasfält
  hade funnits sedan i våras utan att någon kod läste dem — en kund kunde spara
  nya instruktioner och få exakt samma svar för alltid. Byggt och verifierat med
  ett skript som märker varje fält och kontrollerar var det landar i prompten.
- [x] 7. Bokföringsagent med SIE4-export, periodrapport och chattassistent.
- [x] 8. Sätt priser och paket (beslutat 2026-08-22 och 2026-08-25).
- [ ] 9. **Avgör dataskyddsfrågan om språkmodell-leverantören.** Produktionen
  pausades medvetet 24 augusti eftersom Googles gratisnivå för Gemini tillåter
  dem att använda kundernas innehåll för att förbättra sina produkter. Fyra
  åtgärder listades innan pausen fick hävas. Pausen är hävd — men ingen av de
  fyra är gjord. Riktiga kundmejl går just nu dit igen. Spårat som `snipe-a1c`,
  och det kräver ett beslut av Anton, inte kod.
  **Skärpt 2026-08-28:** den tekniska pusselbiten (varför gratisnivån
  fortfarande gäller trots ett betalt faktureringskonto) är löst — nyckelns
  Google-PROJEKT var inte kopplat till kontot, en ren konsolinställning, inte
  ett nytt köp. Det gör åtgärdslistans andra punkt ("aktivera
  fakturering/byt provider") billig att göra klar, men de tre juridiska
  punkterna (DPA, dataregion, PUB-villkor) kvarstår olösta och är fortfarande
  Antons beslut. Anton har kopplat ett nytt projekt och bytt nyckel samma
  kväll — inte verifierat live vid sessionens slut.
- [ ] 10. Uppdatera produktionen till samma kod som utvecklingsmiljön. `main`
  ligger ungefär 80 commits efter och saknar sju databasmigreringar. Spårat som
  `snipe-zfc`. Bör inte göras före punkt 9 — annars flyttas problemet bara.
  **Skärpt 2026-08-28:** den dokumenterade deploy-vägen (`git push origin
  main:railway-main`) är dessutom farlig som den står — `main` ligger 152
  commits EFTER `railway-main`, så den kommandot skulle rulla tillbaka
  produktionen, inte flytta den framåt. Se `plans/2026-08-28-skarpa-korningar-och-produktion.md`
  §8.1 för den verifierade ordningen (merge, inte push). Spårat som
  `snipe-jvj`.
- [ ] 11. Koppla in riktig mejlsändning (`snipe-ork`). **Byggd och konfigurerad
  i `development` 2026-08-27–29:** en HTTPS-sändväg (Resend, väljs eftersom
  Railway blockerar utgående SMTP på nuvarande plan) med `kontakt@snajp.se`
  som avsändare, satt och bekräftad i Railways variabellager. **Bekräftad
  live 2026-08-29:** varningen "Ingen riktig sändväg" är borta ur
  `/health/ready` — bara IMAP-varningen kvarstår. Inget riktigt mejl är
  ännu skickat och verifierat i Resends dashboard. Kvar: varje kunds egna avsändaruppgifter (i dag ett globalt
  konto) och kopplingen till autonomigrinden. `main` saknar fortfarande
  sändväg helt.
- [ ] 12. Koppla ihop uppföljningskedjan (`snipe-3dx`). Funktionen som bygger
  uppföljningsmejl 2–N finns färdig men anropas bara från testerna — inget
  produktionsflöde använder den. Löftet "planerar uppföljningar" i
  marknadsmaterialet infrias alltså inte än.
- [ ] 13. Riktig betalväxel, så att en kund kan betala med sitt eget kort.
- [ ] 14. Gör onboarding av en ny kund körbar igen. Skriptet
  `scripts/onboard_tenant.py` pekar fortfarande på den gamla, döda Vercel-kedjan.
  En riktig onboarding kräver i dag handpåläggning mot Railway.
- [ ] 15. Låt en jurist läsa de juridiska texterna, fyll i riktiga
  bolagsuppgifter (de i `lib/bolag.ts` är platshållare med flit) och bestäm hur
  länge kunddata ska sparas — gallringsskriptet finns men har ingen period satt,
  och ingen period betyder ingen gallring.

## Planerade funktioner

### Beslutat

- **Tre agenter, sålda var för sig eller i paket.** Support 3 990 kr/mån, Leads
  4 490 kr/mån, Bokföring 2 690 kr/mån, Duo (support + leads) 6 990 kr/mån, Trio
  (alla tre) 9 990 kr/mån, plus 1 590 kr i startavgift. Beslutat 2026-08-22 och
  2026-08-25, och förbehållet om att priserna är preliminära är medvetet
  bortplockat — de läses alltså som utlovade.
- **Det som ingår i Leads-paketet är utlovat i prislistan:** ICP-konfiguration
  (beskrivningen av vilken sorts företag kunden vill nå), 150 prospekt och 300
  mejl per månad, och en granskningskö där en människa kan godkänna innan
  utskick.
- **Det som ingår i Bokförings-paketet är utlovat i prislistan:** avläsning av
  kvitton och fakturor, konteringsförslag ur BAS-kontoplanen, periodrapport med
  momssummor, SIE4-export och en bokföringsassistent i chatten.
- **Snajp bygger aldrig om kundens hemsida.** Det enda vi levererar på kundens
  egen adress är chatten. Uttrycklig rättning från Anton efter att fem statiska
  sidor byggts åt Livrustning och sedan revs igen.
- **Ingen kunddata till DeepSeek.** Beslut 2026-08-24, motiverat i `CLAUDE.md`:
  DeepSeek behandlar texten i Kina och det avtalsunderlag som krävs finns inte.
  Systemet vägrar starta om någon försöker sätta tillbaka det i en miljö med
  riktig kunddata.
- **Hemligheter lagras aldrig i databasen**, bara som miljövariabler. Frågan
  restes och avböjdes uttryckligen.
- **Agenternas färdighetsfiler ("skills") får aldrig redigeras.** Behöver
  utdatan justeras skriver man ett tillägg i ett eget lager i stället. Regeln är
  mekaniskt kontrollerad — bygget faller om en fil ändrats.
- **Utvecklingsmiljön är en spegel av produktionen med riktig kunddata**, inte en
  sandlåda. Antons beslut. Följden är att den ska behandlas med samma sekretess.
- **Gallringsperioden är medvetet inte satt** — det är ett affärsbeslut, inte ett
  tekniskt.

### Föreslaget — ej beslutat

- **Agentplattformens minnes- och hastighetslager (Redis).** Beställt av Anton
  2026-08-29 och BYGGT samma dag (pushat till development, se
  `HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md`): chattkörningar som överlever deployments
  (hållbar kö med återtag), tenant-skopad semantisk svarscache (svar på
  återkommande frågor på under en sekund utan modellanrop — direkt lindring av
  Gemini-kvoten), och rullande samtalssummering så långa samtal inte tappar
  kontext. Postgres förblir systemets minne; Redis bär bara det som tål att
  försvinna. Plan: `plans/2026-08-29-redis-agentarkitektur.md`.
- **Riktig mejlsändning från kundens egen domän.** Finns som en tydlig lucka i
  koden med en namngiven plats där det ska in. Förslaget finns för att produkten
  annars inte gör det den säljs som att göra.
- **Uppföljningskedjan kopplas in.** Koden finns färdig och testad, men inget
  anropar den. Kom in via idé-lådan 2026-08-25.
- **Fyra förbättringar av uppföljningarna** som koden själv listar som obyggda:
  tajming styrd av signaler, avbryt på negativ signal och inte bara på svar, en
  bredare svensk "dödperiod"-kalender kring juli och storhelger, och inlärning
  per kund. Dessa kräver ett uttryckligt ja innan de byggs.
- **Riktig betalväxel (Stripe).** Kortformuläret är redan byggt i den form en
  riktig växel lämnar tillbaka data, så bara källan till värdena behöver bytas.
- **Städa bort resterna av den döda stacken.** En Render-tjänst svarar
  fortfarande på nätet och hålls vaken av ett schemalagt jobb; Supabase har kvar
  5 användare, 4 kunder och 48 kunskapsartiklar. Att stänga av dem är utåtriktat
  och därför Antons beslut, inte agentens.
- **Egen Gemini-nyckel per miljö.** I dag delar produktion och utveckling samma
  nyckel, alltså samma kvot — en provkörning i utvecklingsmiljön kan ta ner
  produktionen. Repot har redan ett begrepp för det: "tyst korskoppling".
- **Skriv om onboarding-skriptet mot Railway** så en ny kund går att lägga upp
  med ett kommando i stället för handpåläggning.
- **Databasspegeln av färdighetsfilerna är byggd smalare än vad som ursprungligen
  begärdes** (bara som spårbarhet, inte som live-uppdateringskanal) och det har
  inte bekräftats med Anton.

## Beroenden till andra projekt

Det här projektet väntar inte på kod i något annat repo. Det väntar däremot på
fyra saker utanför sin egen kontroll:

- **Google/Gemini** — vilken avtalsnivå språkmodellen körs på avgör både om
  produktionen får ta emot riktig trafik alls (dataskyddsfrågan) och hur mycket
  den tål. Gratisnivån tål sex anrop per minut, och ett enda supportärende gör
  sex till sju anrop. Ett ärende kan alltså ensamt slå i taket.
- **Livrustning AB** — kunden måste svara på om garantin är 1 år eller 8 år för
  en lös hjärtstartare. Deras egen sajt och deras eget villkorsdokument säger
  olika. Agenten lämnar över till en människa varje gång frågan ställs tills
  kunden svarat.
- **Railway** — hela driften ligger där sedan augusti.
- **En jurist** — de tre juridiska sidorna, dataskyddsbeskrivningen och
  intresseavvägningen är alla förstautkast och bär en synlig ruta som säger det.

Inuti repot finns ett beroende som är värt att känna till: Sebastian Bergman
arbetar parallellt i samma kodbas, och två sessioner har redan krockat i en
rebase. Ändringar behöver samordnas, inte bara pushas.

## Öppna frågor till Anton

1. **Gemini-nivån — vad ska hända nu?** Produktionen skickar riktiga kundmejl
   till Googles gratisnivå igen, trots att den uttryckligen pausades 24 augusti
   av precis det skälet. Tre vägar: pausa om, betala för en nivå med avtal, eller
   byta leverantör. Ingen kod löser det. (`snipe-a1c`, P0)
2. **Är milstolpen i hubbfilen din?** Den säger "main uppdaterad till samma kod
   som development, och Livrustning-tenantens garantiperiod bekräftad av kund".
   Den är skriven av en agent. Stämmer den, eller är målet något annat?
3. **Hur länge ska kunddata sparas?** Gallringsskriptet är byggt men saknar
   period, och utan period gallras ingenting.
4. **Vilka bolagsuppgifter ska stå på de juridiska sidorna?** Organisationsnummer
   och adress är platshållare i dag, med flit — ett gissat organisationsnummer
   kan tillhöra ett annat bolag.
5. **Ska Render-tjänsten och Supabase-projektet stängas av?** Båda är rester av
   den gamla stacken. Avstängning är utåtriktad och därför ditt beslut.
6. **Hur tar ni betalt tills en betalväxel finns?** Prislistan är skarp och
   förbehållet om preliminära priser är borttaget, men systemet kan bara ta emot
   testkort.
7. **Ska uppföljningsmejlen (2, 3, 4 …) byggas klart nu?** Koden finns men är
   inte inkopplad, och marknadsmaterialet lovar redan funktionen.
8. **Ska de fyra obyggda förbättringarna av uppföljningarna byggas?** De kräver
   ett uttryckligt ja enligt planen.
9. **Livrustnings garantifråga — vem jagar kunden?** Den har stått öppen sedan
   7 augusti och blockerar en av de två delarna i den registrerade milstolpen.

## Ändringslogg

- 2026-09-02 — claude — kostnadsgrindar i alla tre agenter (leads: stopp efter
  ICP-steget för okvalificerade/kontaktlösa prospekt, 3 anrop i st.f. 9;
  support: eskaleringssteget villkorat, 6→5 anrop; bokföring: globala
  instruktionslagret + GDPR-riktlinjer) plus nya snabbsöket "Sök Leads"
  (scope=sok, ett anrop) — levererat, deployat och liveverifierat. Målbilden
  (delmålslistan) orörd; ScrapeGraphAI tillagd som underbiträde i lib/bolag.ts
  och flaggad till Anton (DPA/region saknas). Se
  HANDOFF-2026-09-02-RESURSER-OCH-GRINDAR.md.
- 2026-08-29 — claude — sjufasplanen + Redis-arkitekturen byggd och pushad
  till development (Fas 1–6 + R0–R4; Fas 7-deploydelen och R5 spärrade per
  §8.1a). Fyra nya invarianter. B1 skärpt med mätdata: nya Gemini-nyckeln
  ~170 s/anrop och Railway kör fortfarande den gamla — Antons konsolsteg
  kvarstår. Redis Cloud + Resend införda som underbiträden i juridikkedjan.
- 2026-08-29 — claude — punkt 11 (mejlsändning) uppdaterad: Sebbe byggde
  Resend-sändvägen 27–28 aug efter att ha mätt att Railway blockerar SMTP;
  den här sessionen konfigurerade den i `development` (`kontakt@snajp.se`),
  inte ännu bekräftad live. Se `session-logs/2026-08-29-session-log.md`.
- 2026-08-28 — claude — punkt 9 skärpt: Gemini-gratisnivån berodde på ett
  okopplat Google-projekt, inte utebliven betalning; punkt 10 skärpt: den
  dokumenterade `main`-deployen skulle ha rullat tillbaka produktionen
  (`snipe-jvj`) — se `plans/2026-08-28-skarpa-korningar-och-produktion.md`
- 2026-08-26 — claude — skapad, ur kod, statusjournal, sessionsloggar, öppna
  arbetsposter och hubbfilen
- 2026-08-29 (kväll) — claude — punkt 9 (Gemini-nivån) mätt igen och kvantifierad:
  både `main` och `development` ligger kvar på gratisnivån, och adminytan visar nu
  vad drift på betald nivå kostar (7,14 kr in / 35,71 kr ut per miljon tokens för
  `gemini-3.6-flash`, dubblas 2027-01-01). Målbilden i övrigt orörd — sessionen
  var gränssnittsarbete i adminytan, se
  `plans/2026-08-29-adminytan-exempeldata-och-sprak.md`.
