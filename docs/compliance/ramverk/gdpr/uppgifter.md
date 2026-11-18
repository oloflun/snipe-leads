# Uppgifter i GDPR-ramverket

De 15 uppgiftsmallarna som ramverket `frk_681ef1952907deb7cb85896d` (commit `712ee1b3`) kopplar till sina kontroller. Namn, id och frekvens är mallens. "Kräver" sammanfattar mallens text; där mallen har avsnitt för andra ramverk (HIPAA, PCI, ISO 42001, NEN 7510) tas bara den allmänna och GDPR-delen med.

Status anges med plattformens värden (`todo`, `in_progress`, `in_review`, `done`, `not_relevant`). Vem: **Ä** = Anton, **A** = agent. "Agent utan Ä" betyder att en agent kan göra hela uppgiften utan Antons hand.

Uppdaterad 2026-11-18. "Ändr. 11-18" vid status betyder att uppgiften ändrats den dagen. Nivåerna *i drift*, *i testmiljön* (mergat till `development`, väntar på release-PR 60) och *utkast* (`../../underlag/`) är desamma som i `matris.md`, liksom hänvisningarna (JA, BU, Inv., PR).

**Summering:** 0 `done`, 12 `in_progress`, 1 `in_review`, 2 `todo`. Förändring från 2026-11-17: `todo` 7 → 2, `in_progress` 7 → 12, `in_review` 1 → 1, `done` 0 → 0.

## Kan stängas i dag

**Ingen uppgift kan stängas som `done` med befintligt bevis.** Tre ligger nära:

- **Appoint or Review Data Protection Officer** kan sättas till `not_relevant` när Anton fyllt i och signerat `../../underlag/beslut/b-dataskyddsombud.md` och fört in det i `docs/BESLUT.md`. Mallen säger att uppgiften ska markeras "Not Relevant" om ombud inte krävs.
- **Monitoring & Alerting** kan stängas om Anton godtar ärende 53 som belägg för ett nyligen mottaget larm (simulerat fel 2026-11-17, skapat och stängt av övervakningen) och skriver en kommentar om vilka loggar Railway sparar. Det är tunnare än det ser ut: schemat har inte gått var 15:e minut under natten, och internlarmen saknar fortfarande sina variabler.
- **Secure Code** stängs när de öppna Dependabot-larmen med nivå kritisk och hög är åtgärdade och kodskanningens falska larm avfärdade med motivering. Verktygen är påslagna.

---

### 1. App Availability
`frk_tt_68406d2e86acc048d1774ea6` · årligen · `it` · AUTOMATED · kontroll: Privacy by Design and by Default

- **Kräver:** att tjänsten tål hög last och fel. Skärmbild på DDoS-skydd eller automatisk skalning, och belägg för brandvägg runt produktionsdatabasen.
- **Finns:** hastighetsbegränsning i api (`snajp-support/app/api/rate_limit.py`, `rate_limit_db.py`); tjänsterna i Amsterdam med en replik vardera (`../../bevis/railway-regioner-2026-11-17-efter.txt`). Övervakning av produktionen som upptäcker avbrott (`.github/workflows/overvakning.yml`).
- **Saknas:** belägg för DDoS-skydd eller skalning hos Railway. Postgres i `main` har fortfarande en publik TCP-proxy (`../../bevis/railway-konfiguration-2026-11-17-efter.txt`). Inga säkerhetskopior; Railway kräver Pro-planen (BU A4).
- **Vem:** Ä tar skärmbilder i Railway; A dokumenterar.
- **Agent utan Ä:** nej.
- **Status:** `todo` · ändr. 11-18 (bevis).

### 2. Appoint or Review Data Protection Officer
`frk_tt_68b5ce9b5393ae083c3beadf` · årligen · `admin` · MANUAL · kontroll: GDPR Accountability Roles and Representatives

- **Kräver:** bedöma om ombud krävs. Utse och dokumentera om det krävs; annars markera "Not Relevant". Ompröva när omfattningen ändras.
- **Finns:** bedömningen i `matris.md` (AG-4) och beslutsutkastet `../../underlag/beslut/b-dataskyddsombud.md`.
- **Saknas:** antal kunder som utlöser omprövning, Antons signatur, posten i `docs/BESLUT.md`.
- **Vem:** Ä.
- **Agent utan Ä:** nej (beslutet).
- **Status:** `in_review` · ändr. 11-18 → `not_relevant` när Anton beslutat.

### 3. Cookie Consent and Tracking Review
`frk_tt_69e92cc75996378b01b27ec9` · årligen · `admin` · AUTOMATED · kontroller: Lawful Basis Register, Privacy Notice, Data Subject Rights Request Workflow

- **Kräver:** förteckning över cookies, SDK:er, pixlar och spårning; samtyckesruta med icke-nödvändiga cookies av som standard; en cookiepolicy med namn, syfte, livslängd och mottagare; lagrade samtycken; avstämning mot vad som faktiskt sätts i produktionen.
- **Finns:** förteckning över sju kakor och elva lagringsnycklar med syfte, livslängd och plats i koden, och en omskriven cookiesida som beskriver demolänken (PR 51, i testmiljön).
- **Saknas:** sidan är inte i drift förrän PR 60. Samtyckesfrågan för demolänken, service workern och CRM-demon är obeslutad (LEK 9 kap. 28 §), och ingen samtyckesruta finns. Cal.com står inte i underbiträdeslistan. Ingen avstämning mot produktionen är gjord (JA #17).
- **Vem:** Ä beslutar om samtycke och demolänken; A gör avstämningen.
- **Agent utan Ä:** avstämningen ja, besluten nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 4. DPIA Trigger Review and Execution
`frk_tt_69e92829ac42d6ca48bc6cd9` · årligen · `admin` · AUTOMATED · kontroll: Data Protection Impact Assessment Process

- **Kräver:** pröva alla behandlingar mot utlösare för DPIA, göra DPIA där det utlöses, dokumentera restrisk, samråda med IMY vid hög restrisk, spara posterna.
- **Finns:** `docs/dpia_supportagenten.md` (uppdaterad 2026-11-17, ogranskad); `docs/intresseavvagning_kallmejl.md`; utlösarna i `policyer/06-vendor-third-party-risk.md`.
- **Saknas:** prövning av leadsagenten, webbpoolen och demolänkens spårning mot utlösarna; juristgranskning (JA #7).
- **Vem:** A skriver prövningen; Ä och jurist beslutar.
- **Agent utan Ä:** utkastet ja, beslutet nej.
- **Status:** `in_progress`.

### 5. Data Protection Awareness Training
`frk_tt_69e92829b6aa752b0dfba9a8` · årligen · `hr` · AUTOMATED · kontroll: Information Security Policy and Awareness Training

- **Kräver:** utbildning vid start och minst årligen om laglig behandling, rättigheter, incidentrapportering och den interna säkerhetspolicyn. Spara belägg (kvittens, quiz eller rapport).
- **Finns:** material och kvittens som utkast (`../../underlag/utbildning/genomgang.md`, `kvittens.md`); policyutkastet `policyer/05-security-privacy-awareness-training.md`.
- **Saknas:** genomförd genomgång och kvittenser från Anton och Sebbe.
- **Vem:** Ä och Sebbe.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 6. Data Subject Rights Request Handling
`frk_tt_69e92829e97f5a494f13d67b` · kvartalsvis · `admin` · AUTOMATED · kontroll: Data Subject Rights Request Workflow

- **Kräver:** granska loggen över begäranden (tillgång, rättelse, radering, begränsning, portabilitet, invändning): identitet kontrollerad, svar inom en månad, utfall dokumenterat.
- **Finns:** `scripts/gdpr_radera.py` (sök, export, radering) täcker dagens tabeller och har ett test, mergat till `development` (PR 45); avregistreringen med spärrlista; rutin och loggmall som utkast (`../../underlag/rutiner/a-begaran-fran-registrerad.md`, `b-begaranslogg.md`).
- **Saknas:** loggen är inte upplagd, så det går inte att visa att inga begäranden kommit eller att de besvarats i tid. Skriptet har aldrig körts. `integritet@` finns inte.
- **Vem:** Ä lägger upp loggen och fyller i rutinen; A provkör skriptet mot den lokala stacken.
- **Agent utan Ä:** skriptdelen ja.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 7. Encryption at Rest
`frk_tt_68e52b26bf0e656af9e4e9c3` · årligen · `it` · AUTOMATED · kontroll: Data Minimization, Encryption, and Pseudonymization

- **Kräver:** kryptering i vila på databaser, objektlagring och volymer, med skärmbilder från konsolen.
- **Finns:** Railways uppgift i DPA:n att databaser krypteras i vila (`../../leverantorsgranskning.md` §3); kundnycklar krypterade med Fernet i produktionen (Inv. §4). Jobbkön ligger sedan 2026-11-17 hos Railway, så Redis Cloud behöver inget eget besked när databasen där är raderad.
- **Saknas:** skärmbild eller skriftligt besked från Railway för Snajps volymer, också den nya Redis-tjänstens volym; kundnycklarna ligger i klartext i testmiljön (JA #16).
- **Vem:** Ä hämtar besked; A krypterar nycklarna i testmiljön.
- **Agent utan Ä:** nej.
- **Status:** `todo` · ändr. 11-18 (bevis).

### 8. Incident Response
`frk_tt_68406b4f40c87c12ae0479ce` · årligen · `itsm` · MANUAL · kontroller: Personal Data Breach Response Procedure

- **Kräver:** register över säkerhetsincidenter och hur de lösts. För GDPR: en dokumenterad plan med upptäckt, eskalering, anmälan inom 72 timmar och åtgärd, och regelbunden utbildning.
- **Finns:** `INCIDENT_RESPONSE.md` med plan och logg; `policyer/03-incident-response-breach-notification.md`; övningsprotokoll som utkast (`../../underlag/rutiner/c-incidentovning.md`). Övervakningens larmkedja provad (ärende 53).
- **Saknas:** bedömning och stängning av posterna (JA #1, #15, #20), också TypeSafe-överföringen; en hållen övning; utbildning.
- **Vem:** Ä bedömer och håller övningen med Sebbe; A uppdaterar loggen.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 9. Maintain Records of Processing Activities (RoPA)
`frk_tt_69e928283390c5483dccbcde` · årligen · `admin` · AUTOMATED · kontroll: Data Inventory and Mapping

- **Kräver:** förteckning enligt art. 30 med ändamål, kategorier, mottagare, överföringar, lagringstider, säkerhetsåtgärder och vem som har åtkomst per datamängd. Granskas årligen.
- **Finns:** `docs/registerforteckning.md` med A1–A3 och B1–B3, mottagare och överföringar 2026-11-17.
- **Saknas:** lagringstider (fem poster "[fylls i]"); åtkomst per datamängd; säkerhetsåtgärder för A-posterna; utvecklingsmiljön som egen mottagarkrets.
- **Vem:** Ä beslutar perioder; A fyller i åtkomst och åtgärder.
- **Agent utan Ä:** delvis.
- **Status:** `in_progress`. Förteckningen kan laddas upp nu.

### 10. Manage Third-party and EU Representative Relationships
`frk_tt_68b5ce9c6c1bdb171870f623` · årligen · `admin` · MANUAL · kontroller: GDPR Accountability Roles and Representatives, Data Processing Agreements with Third Parties

- **Kräver:** DPA med alla underbiträden; EU-representant om bolaget är utanför EU; regelbunden granskning.
- **Finns:** `../../leverantorer.json` och `../../leverantorsgranskning.md` med DPA-länk och hur den ingås för 19 poster; EU-representant behövs inte (`matris.md`, AG-3; beslutsutkast `../../underlag/beslut/c-eu-representant.md`). Kundmejl går inte längre till TypeSafe (`INKORG_JEV = off` i båda miljöerna). Render suspenderad, gamla Vercel-projektet pausat. Brev till TypeSafe, ScrapeGraphAI, Railway, Supabase och Render, och Redis som utkast (`../../underlag/brev/`).
- **Saknas:** Railways signerade DPA, Resends nedladdade kopia, skickade brev, ScrapeGraphAI-DPA, GitHub-plan (JA #3, #6, #10, #11); datum för ingående och nästa granskning per leverantör.
- **Vem:** Ä.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 11. Monitoring & Alerting
`frk_tt_68406af04a4acb93083413b9` · årligen · `itsm` · AUTOMATED · kontroller: Information Security Policy and Awareness Training, Personal Data Breach Response Procedure

- **Kräver:** loggning påslagen i molnmiljöerna och granskad regelbundet; skärmbild av ett nyligen mottaget larm, eller en kommentar om att inga larm kommit.
- **Finns:** övervakning av webben och api:ts hälsokontroller i produktionen (`.github/workflows/overvakning.yml`, PR 50) som skapar ett ärende med etiketten `driftlarm`; larmkedjan provad, ärende 53 skapat 2026-11-17 23:39 UTC och stängt 23:41 UTC. Spårbarhet med `X-Request-Id` och `platform_events` (Inv. §4); leveransstopp vid studs och klagomål.
- **Saknas:** schemat har gett en schemalagd körning under natten (04:44 UTC), inte en var 15:e minut. Internlarmets variabler (`INTERNLARM_SMTP_*`) saknas fortfarande, så `[PRIORITERAT]`-mejlen går troligen inte ut. Ingen beskrivning av vilka loggar Railway sparar och hur länge. Ingen felspårning.
- **Vem:** Ä godtar beviset och skriver kommentaren; A följer upp schemat.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 12. Public Policies
`frk_tt_6840791cac0a7b780dbaf932` · årligen · `it` · AUTOMATED · kontroller: Privacy Notice, Data Subject Rights Request Workflow

- **Kräver:** länkar till integritetspolicy och villkor; ett formulär för raderingsbegäran och loggning av begäranden. För GDPR: policyn ska ange grunder, rättigheter, kategorier, användning, delning och lagring, och uppdateras när praxis ändras.
- **Finns:** `/integritetspolicy`, `/villkor`, `/cookies` på svenska och engelska. I testmiljön (PR 45, 51): alla rättigheter, demolänken, AI-assistenten, rätt underbiträdeslista, kakorna, "senast uppdaterad".
- **Saknas:** rättningarna i drift (PR 60); formulär för radering (bara mejl); logg; gallringslöftet stämmer inte förrän gallringen körs; org.nr och adress; `/villkor` saknar pris, ansvar och uppsägning (JA #5, #7, #8).
- **Vem:** Ä beslutar och mergar; A skriver formulär.
- **Agent utan Ä:** formulär ja, publicering nej.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 13. Review Data Retention, Minimization, and Encryption
`frk_tt_69e92828297806545638eed7` · årligen · `it` · AUTOMATED · kontroll: Data Minimization, Encryption, and Pseudonymization

- **Kräver:** granska att insamlingen är minimal, att lagringstider tillämpas och att gammal data raderas, att data är krypterad i transit och vila och pseudonymiserad där det går. Dokumentera granskningen och åtgärderna.
- **Finns:** nulägesinventeringen §4 och DPIA:ns avsnitt 2 som första granskning (2026-11-17). Gallringen över alla kategorier byggd med databastester (PR 48), i testmiljön och avslagen. Jobbkön på Railways privata nät i båda miljöerna (`../../bevis/railway-konfiguration-2026-11-17-efter.txt`).
- **Saknas:** beslutade lagringstider (`../../underlag/beslut/d-gallringsperiod.md` osignerat), `GALLRING_AKTIV` på och gallringen i `main` (JA #8); minimering av testmiljön (JA #16).
- **Vem:** Ä beslutar; A torrkör och slår på efter beslut.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 14. Review International Data Transfers
`frk_tt_68b5ce9d508cacf8e4517b56` · årligen · `admin` · MANUAL · kontroller: Data Inventory and Mapping, Data Processing Agreements with Third Parties

- **Kräver:** gå igenom och dokumentera alla överföringar enligt kapitel V; bekräfta adekvansbeslut, SCC eller andra skydd.
- **Finns:** `../../leverantorsgranskning.md` med DPF-uppslag och SCC per leverantör 2026-11-17; tabellen överst i `docs/registerforteckning.md`. Kundmejl till TypeSafe stoppat 2026-11-17.
- **Saknas:** skydd för TypeSafe, som fortfarande får leadsdata (bara SCC, ingen TIA), ScrapeGraphAI (ingen mekanism), GitHub (synken; ingen avtalad), Resend (TIA saknas för USA-lagringen).
- **Vem:** Ä beslutar och avtalar; A skriver TIA-utkast.
- **Agent utan Ä:** TIA-utkast ja.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 15. Secure Code
`frk_tt_68406e353df3bc002994acef` · årligen · `itsm` · AUTOMATED · kontroll: Privacy by Design and by Default

- **Kräver:** Dependabot eller motsvarande som hittar sårbara beroenden; allvarliga sårbarheter åtgärdade; skärmbild av säkerhetsöversikten utan öppna kritiska eller höga.
- **Finns:** Dependabot-larm och säkerhetsuppdateringar, kodskanning (CodeQL) och hemlighetsskanning med push-skydd påslagna (GitHubs API 2026-11-18); `.github/dependabot.yml` i `development` (PR 50); kodskanningens verkliga larm rättade (PR 49); CI i `.github/workflows/verify.yml`; CODEOWNERS och grenskydd på `main`.
- **Saknas:** öppna larm 2026-11-18: Dependabot 10 kritiska, 28 höga, 27 medel, 3 låga; kodskanning 44 (39 höga, 5 medel), de flesta bedömda som falska i `../../kodskanning-triage.md` men inte avfärdade. Privat sårbarhetsrapportering är avslagen.
- **Vem:** A åtgärdar beroendena; Ä avfärdar falska larm och slår på rapporteringen.
- **Agent utan Ä:** beroendena ja (PR), avfärdandet nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).
