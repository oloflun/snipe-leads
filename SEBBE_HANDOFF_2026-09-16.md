# Sebbes commits 3–16 september 2026 — underlag + handoff

> Tillfälligt dokument. Sammanställt 2026-09-16/17 av Claude (Opus) på uppdrag av Anton,
> baserat på fyra parallella Sonnet-subagenters genomgång av `git show --stat`/`git show`
> för samtliga ~85 commits av Sebbe sedan 3 september 2026. Radera eller flytta till
> `session-logs`/vault när innehållet är konsumerat — det är inte kanoniskt minne.

## Läsordning
1. **Handoff till nästa agent** (nederst i dokumentet) — börja där om du bara ska agera.
2. **Executive summary** (nedan) — det Anton fick presenterat i chatten.
3. **Rådata från subagenterna** — fyra sektioner, en per tidsblock, orörda rapporter för
   den som vill verifiera en detalj eller hitta en commit-hash.

---

## Executive summary (levererad till Anton 2026-09-16)

### 1. Produktytorna växte från en till fyra sajter
- **Bokföringssajt** (`bokforing-webb`, 14/9): fristående Next.js-app, eget UI, Snajps
  designsystem, proxy mot befintligt bokförings-API, lösenordsskyddad tills riktiga
  konton finns.
- **CRM-demo** (`components/crm/CrmDemo.tsx`, ~886 rader, 12/9): säljdemo på `/demo/crm`
  — CSV-import av kundens egen kundlista (stannar i `localStorage`, aldrig servern),
  klick på kund → signaler + en **egen isolerad Email studio per kund** som hålls
  monterad i bakgrunden så utkast för olika kunder aldrig blandas.
- **Leads- och Supportagenten fick egna sajter** (15–16/9), samma SSO-mönster som
  bokföring. På vägen: en conclude-commit svepte oavsiktligt bort SSO-routen
  (återställd), och en klientkomponent läste `process.env` i webbläsaren så
  "Kör Agent"-bannern försvann tyst (flyttad till serverrendering).
- **16/9 — senaste läget:** gemensamt vänsterrail-skal delas av alla tre sajter, demo
  fick förladdade exempel. **Leadsagenten heter nu Iris** (persona, gränser, eskalering,
  källhänvisning per prospekt synliga för kund). **Bokföringsagenten heter nu
  Kvittohanteraren** — funktionell ombyggnad: läser kundens inkorg read-only, tolkar
  belopp/moms/datum, stoppar dubbletter (kräver migration 063). Bekräftat: Leads- och
  Supportsajterna är i drift i **main**.

### 2. Vertex AI-migreringen — en kedja av dolda följdbuggar
Bytet från Gemini API-nyckel till Vertex AI (service account) gick sönder i lager:
1. **Modellnamn saknade prefix** — Vertex kräver `google/<modell>`, koden skickade bart
   namn → *alla* agentanrop (chatt, leads, bokföring, Email studio) föll med 400 sedan
   flytten, trots att hälsokontrollen visade "live" (mätte bara credentials). Senaste
   lyckade körning i main innan fixet: 22 augusti.
2. **Email studio kapades av tankbudget** — Vertex gemini-2.5-flash drar "thinking" ur
   samma tokenpott som svaret → klippte JSON-svar. Fixat i tre steg, till sist
   `thinkingBudget 0` / `reasoning_effort='minimal'` (`'none'` avvisades av Vertex och
   slog sönder *varje* anrop tills upptäckt).
3. **Leadssökningens latens** — samma tankbudget-problem gav 300s med en rad;
   `thinkingBudget 0` → 9–16s med åtta rader (PR #15).
4. **Discovery-sökningen** föll med 400 "Please use a valid role" (Vertex kräver
   `role:"user"`) — dolt länge av en annan bugg (JobTech-källan, se nedan).
5. **Timeout kopierad fel** — Email studios 15s-timeout var Vercels gräns; appen körs på
   Railway utan den taket. Höjd till 25s.

**Praktiskt:** Email studio och leadssökning var trasiga/fel i flera lager samtidigt
under övergången. Allt fixat och verifierat **i development** — väntar på release till
main.

### 3. Leads-kvaliteten — flera oberoende spärrar tillkom
QA mot en riktig testkund (Nordform) avslöjade att kunder fick felaktiga leads och
mejlutkast till bolag som borde underkänts:
- Formulärets storleksval nådde aldrig prompten (fältmiss); bemanningsföretag godkändes
  felaktigt → ny kodgrind `kvalificeringsgrind.py` som bara kan **fälla**, aldrig
  godkänna.
- `stopped_early` hårdkodad `None` → underkända bolag fick ändå mejlutkast.
- JobTech-källan sökte på Snajps *egna* nyckelord i stället för kundens målgrupp → helt
  fel leads, maskerade Vertex-role-buggen ovan.
- Rekryteringsplattformar (Teamtailor, Varbi, Indeed) räknades som bolagets egen sajt →
  kontaktskörden hämtade ett ansökningsformulär i stället för kontaktuppgifter.
- `geography`-listan strängades rakt in i sökfrågan (blev `"Inköpschef ['Umeå']"`
  bokstavligt).
- Dubblettspärren i batchsökning kollade bara samma körning, inte hela registret.
- Skrapningen (ScrapeGraphAI) blockerade hela API:t synkront upp till 60s och missade
  parkerade/"under konstruktion"-sidor.

**Praktiskt:** leadskedjan hårdare validerad på flera oberoende nivåer — men detta
ligger i development, inte main.

### 4. Kvotfel och kreditslut — ärlighet mot kunden
- Minutkvot (429) fällde leadsjobb i onödan → tålmodiga omförsök med Retry-After.
- **Kreditslut** (permanent) särskiljdes från transient kvotfel → egen felklass
  `app/kvotfel.py`, ärlig svensk kundtext, larm via Resend (Railway blockerar SMTP).
  Gäller chatt, leads *och* bokföring.
- Failade inkorgsmejl gick tidigare förlorade permanent → ny återprocessa-endpoint.
- `last_sync_at`/`last_error` på mailboxar hade aldrig skrivits på fyra månader.

### 5. Bokföring, tillägg och admin
- Verifikat krediterades alltid mot 1930, även obetalda leverantörsfakturor → ny
  obligatorisk betalstatus styr rätt motkonto (1930 vs 2440/1510).
- `workspaces.addons`-kolumnen kunde inte skrivas av kod → ny säker admin-UI
  (`Tillaggsvaljare`).
- Ny adminvy visar token-förbrukning och uppskattad AI-kostnad per kund.
- Riktig inloggningssida ersätter Basic Auth på bokföringssajten (två buggrundor:
  ingen felfeedback, sedan redirect mot `localhost` bakom Railways proxy).
- Migration 064 gav RLS-policy men glömde `GRANT SELECT` → fixat i development.

### 6. Deploy-infrastruktur och release-läge (viktigast)
- **main deployar nu direkt från main-grenen** (Railway-triggern omlagd), `railway-main`
  pensionerad — releaseflödet är PR development→main, inte den gamla tvåstegspushen som
  kunde rulla tillbaka produktionen.
- Handoff-fil `HANDOFF-2026-09-15-RELEASE-TILL-MAIN.md` sammanställer allt ovan inför
  flytt development→main, inklusive krav på att köra migrationerna 062–065 före merge.
- **Nuläge 16/9:** Leads- och Supportsajterna bekräftat i drift i main. Resten
  (Vertex-migreringen, leadskvalitet, bokföringskontering, RLS-grant) är verifierat bara
  i development — release till main kräver Antons uttryckliga instruktion (projektregel).

### 7. Övrigt
- Ångerrätt-svaret i supportens kunskapsbas: en cherry-pick var trasig (SyntaxError, 28
  testmoduler föll) — reverterad och omskriven från grunden med rätt synonymer.
  Grundproblemet (Livrustning saknar embeddings, ren fulltextsökning) kvarstår som känd
  brist.
- Prestanda: -8,9% utdata-tokens per lead → leadskostnad ned till 0,184 kr.
- Pilotavtalsutkast (PUB, ansvarstak) + automatiserat onboardingskript (orgnr+webbplats
  → kunskapsbasutkast), 13/9.
- `bd init`: projektet gick över till beads-issuetracker 14/9.

---

## Rådata: block 1 — 4–11 september (18 commits)

**Leadsjobb och kvotfel (tyngsta klustret)**
- `2204e2a` (6/9): Minut-429 fällde leadsjobb i onödan — `run_step` fick opt-in
  `talamod_429` (två tålmodiga omtag, 20s/40s, respekterar Retry-After) för
  bakgrundsjobb; chatten orörd.
- `98fa223` (6/9): Failade inkorgsmejl var permanent förlorade (IMAP läst-markerat) — ny
  endpoint `POST /api/inbox/{id}/processa-om`. Beslutsloggen visar nu svensk text i
  stället för leverantörens råa engelska kvottext.
- `2617a5d` (11/9, störst): Kreditslut (permanent) särskiljs från transient minutkvot —
  ny `app/kvotfel.py`, egen kundtext, larm till oss (platform_event + Resend-mejl).
  Ny invariant INV-QUOTA-001. `9c58f85` liten följdfix på samma invariant.
- `c898b62` (4/9): `trigger_events` (starkaste kroken i kalla mejl) nådde aldrig
  skrivsteget — fanns bara i grundningsgrindens tillåtna-lista. Lades in i
  `final_output`. Domarskriptet körs nu i båda ordningarna mot positionsbias.

**Discovery-buggar**
- `bd3deee` (4/9): Rekryteringsplattformar (teamtailor.com, varbi.com, indeed.com)
  räknades som bolagets egen sajt → kontaktskörden hämtade ett ansökningsformulär. Ny
  lista `_ANNONSPLATTFORMAR`.
- `c0ed60e` (6/9): (1) `geography` (lista) strängades rakt in i sökfrågan
  (`"Inköpschef ['Umeå']"` bokstavligt); (2) batchsökningens dubblettspärr kollade bara
  samma körning, inte hela registret.
- `99c4690`+`9d4fbfb` (4/9): Kunskapsbasen hade tagits bort ur kunddataspärren globalt
  (fällde testarbetsytor vid seedning) men öppnade för att en riktig kunds KB kunde
  raderas som "beroende". Villkorat på `testkund-`-prefix.

**Drift/synk**
- `a01c78a` (7/9): `last_sync_at`/`last_error` på mailboxar hade aldrig skrivits på fyra
  månader. Ny `touch_mailbox_sync` stämplar varje synkförsök i alla utfallsvägar.

**Bokföring**
- `f27ea01` (11/9): Alla inköpsverifikat krediterades alltid mot 1930, även obetalda
  leverantörsfakturor. Ny obligatorisk `betalstatus` styr motkonto (1930 vs 2440/1510).
  Ny invariant INV-BOOK-004, migration 062.

**Tillägg/entitlements**
- `48117a8` (11/9): `workspaces.addons` fanns sedan migration 022 men ingen kodväg kunde
  skriva kolumnen. Ny security-definer skrivväg, migration 063, admin-UI
  (`Tillaggsvaljare`).

**Email studio**
- `ddd67ac` (11/9): Klick på ett lead i en leadslista öppnar Email studio direkt under
  raden — ny brygga som lyfter raden in i prospektregistret (dedupe på bolagsnamn).

**Prestanda**
- `75cbd6f` (4/9): Beskar utdatalängder i resonemangsfält som ingen kod läser — mätt
  -8,9% utdata-tokens/lead, leadskostnad 0,1897 → 0,1844 kr. Belägg-fält (evidence,
  likely_pains, trigger_events) uttryckligen undantagna.

**QA/dokumentation**
- `ab91bba` (8/9): Nytt E2E QA-skript (`qa_kundresa.mjs`) — hittade att Gemini-krediterna
  var slut sedan 6/9 (grunden för `2617a5d`).
- `c83b43d` (conclude 4/9): milstolpe — leadskostnad 0,187 kr/lead.
- `fd81488`, `75e6dd3`: sessionsloggar utan ny substans (grensynk, ROUTE GAP hanterad
  annan session).

---

## Rådata: block 2 — 11–14 september (18 commits)

**Tilläggspanelen i adminytan (7366d0a, 34d60ed, 8a7752b)** — kundnamnet interpolerades
felaktigt in i ingresstexten trots att namnet redan stod som H1 (bortplockat med en död
prop). Ett scratch-testskript som följde med i en `git add -A` städades bort. Sista
fixet: en `disabled`-satt växel stal tangentbordsfokus vid varje toggling (guard i
handlern), sparstatus skrevs men syntes aldrig i UI ("– sparar…" i etiketten). Två
oberoende datahämtningar parallelliserades med `Promise.all`.

**CRM-demon (c1c3c0c)** — stor ny demofunktion på `/demo/crm`. Kunden CSV-importerar sin
egen CRM-kundlista (parsas i webbläsaren, `localStorage` bara — ingen server, följer
demorutens anonymitetsregel). Master-detalj: klick på kund → signaler (CRM-notering +
nyhets-/annonsrad) + **egen isolerad Email studio per kund** kvar monterad i bakgrunden
vid kundbyte. Affärsprofil matas levande in i studions knappar.
`components/crm/CrmDemo.tsx` ~886 rader — enskilt största produktändringen i perioden.

**Kreditslut och felhantering (fadc95e, de6cecc)** — svar på testarfynd 13/9: när
Google-krediterna på Vertex AI tar slut gav systemet vaga besked. Chatt, leads och
bokföring fäller nu snabbt med korrekt kundtext + larm. Städjobb för jobb/listor som
hänger i "processing". Samtidigt bytte Email studio till Vertex AI (service account JSON
→ RS256-JWT → OAuth2-token, `lib/llm/vertex.ts`) eftersom Google tog bort
AI Studio-krediterna — modellvalskedja: OpenAI → Vertex → GEMINI_API_KEY → DeepSeek
(DeepSeek fortsatt spärrat i development, spegling av produktion).

**Leadslistor och Email studio-koppling (8e30461)** — leadslistor kan generera mejl
direkt (enskilt eller batchat, max 25/klick, allt till granskningskön). Rätt paketnamn
visas nu i översikt/admin (hämtat ur `workspaces.products`).

**Pilotavtal och onboarding (f24cab8, 1bb3d11)** — juridiskt pilotavtalsutkast (PUB,
ansvarstak, export/radering) + automatiserat onboardingskript som skannar en ny kunds
hemsida och genererar ett kunskapsbasutkast för granskning. Handoff-dokument listar vad
som *inte* är i drift (Railway var nere) och manuella steg.

**Deploy-infrastruktur för main (0306119, dfce76e)** — `main`-miljön deployar nu direkt
från main-grenen (Railways trigger omlagd via `deploymentTriggerUpdate`), `railway-main`
pensionerad. Releaseflödet: PR development → main med code owner-granskning, inte den
gamla tvåstegspushen. Invariant-assert `test_inv_deploy_002` uppdaterad så en återinförd
`railway-main`-koppling räknas som regression.

**Vertex-modellnamn-bugg (6147af8)** — allvarlig: Vertex kräver `google/<modell>`,
koden skickade bart namn → *alla* agentanrop föll med 400 sedan Vertex-flytten, trots
"live" hälsokontroll (mätte bara credentials). Senaste lyckade körning i main: 22
augusti. Fixat med prefix på klientnivå.

**Fristående bokföringssajt (520b66e)** — ny kundyta `bokforing-webb/`, separat
Next.js-app, eget UI (Översikt, Resultat, Bokföringsagenten, PDF-filer), Snajps
designsystem, proxy mot bokförings-API, lösenordsskydd (`BOKFORING_LOSEN`) tills riktiga
konton finns. Egen Railway-tjänst, bara development. Backend fick "dubbel avläsning" —
fält där två oberoende genomgångar läser olika döljs för gissning, går till manuell
granskning.

**Övrigt** — admin-workspace-flytt fick skyddad `--flytta-fran`-flagga (09912ae);
superlativspärren fällde svenska idiom som "på bästa sätt" felaktigt, nu vitlistad
(5ad2f51); beads-verktygsstädning utan produktpåverkan (262afa9, bbbb30a).

---

## Rådata: block 3 — 15–16 september, del A (18 commits)

**Ångerrätt-fixen i Livrustnings kunskapsbas (8b9687b, ea76e24, 56d9dc7, b756198,
901e3b1)** — en tidigare cherry-pick (PR #8, 8fc8d34) skulle laga att kunder som skrev
"kan jag ångra mitt köp?" inte fick träff (svensk fulltextsökning delar inte sammansatta
ord, Livrustning saknar embeddings). Cherry-picken var trasig (felkodad byte,
oavslutad strängliteral → SyntaxError, 28 testmoduler föll). Reverterad (56d9dc7) och
omskriven (b756198): titel/inledning får synonymerna kunder faktiskt skriver, kursbokningar
eskaleras till människa, regressionstest låser innehåll och importerbarhet. 901e3b1
rättar sakfel: produktionen hade redan rätt artikel, bara dev låg efter. **Grundproblemet
(inga embeddings) kvarstår som känd brist.**

**Leadssökningens latensbugg (2319aa8, 928fb5f, 8a34086 delvis)** — QA-kunden Nordform:
"0 av 5 bolag" — Gemini-sökningen fick lästimeout efter 90s, tre gånger i rad, formuläret
gav upp efter ~3 min. Lästaket höjt till 180s, läs-timeout → direkt fel i stället för
omförsök, frontendens väntetid förlängd till ~5 min. Grundorsak (928fb5f): standardtänk i
Gemini/Vertex-anropet gav 300s och en rad; `thinkingBudget 0` → 9–16s, åtta rader.
Innehållet i PR #15.

**Bokföringssajtens kundknapp och admin-kostnader (e6a8a93)** — (a) knapp i den
inbyggda bokföringsvyn ger kunden SSO-genväg till den fristående bokföringssajten
(60s-biljett växlas mot httpOnly-session, allowlist på backend-URL); (b) ny adminvy
`/admin/bokforingsanvandning` visar token-förbrukning och uppskattad AI-kostnad
(Vertex/Gemini 2.5 Flash-listpris, märkt uppskattning) per kund.

**Leads- och Supportagenten får egna sajter (6e4544b, d649640, 656d309, fb9ef94,
5e28536)** — `leads-webb`/`support-webb` efter samma mönster som bokföring (SSO,
generisk tenant-proxy, admin-vy `agentanvandning`). Felcykel: conclude-commiten 8a34086
svepte bort SSO-routen av misstag (d649640 återställde), en klientkomponent läste
`process.env` i webbläsaren → "Kör Agent"-bannern på Leads-fliken försvann tyst (656d309
flyttade till serverrendering, tog bort en återuppstånden dubblettfil). fb9ef94: 422-fel
doldes bakom generiskt "Oväntat svar".

**Senaste läget 16 september (1cca394, d91d741, 729402c, caeb766)**
- 1cca394: Gemensamt vänsterrail-skal delas av alla tre sajter, demoläget förladdade
  exempelkörningar.
- d91d741: Leadsagenten döps om till **Iris** — persona, gränser, eskaleringsregler,
  källhänvisning per prospekt.
- 729402c: Bokföringsagenten döps om till **Kvittohanteraren** — funktionell ombyggnad:
  läser kundens e-postinkorg (read-only), identifierar kvitton/utlägg, tolkar
  belopp/moms/datum, stoppar dubbletter. Kräver ny databasmigration (063) före deploy.
- caeb766: Bekräftar Leads- och Supportsajterna provisionerade och i drift i **main**.

---

## Rådata: block 4 — 15 september, del B (19 commits)

**Vertex AI-migreringen — kedja av följdbuggar (5b7640f, ae02a96, 95b3524, 4a112ef,
ed60d10, a65ab1e)**
1. `5b7640f` — Email-studions JSON-svar klipptes av: prompten bad onödigt om att
   modellen upprepade hela originaltexten (→ `null` i stället), `maxOutputTokens`
   1800→3000, parsern fick räddningsregex för trunkerade svar
   (`app/api/email-studio/route.ts`).
2. `95b3524` — Modellen drog fortfarande för mycket till tankbudget. `reasoningEffort=
   'none'` (= `thinking_budget=0`), fallback vägrar servera rå JSON-brate.
3. `4a112ef` — `reasoning_effort='none'` avvisas av Vertex (400) — *varje* Email
   studio-anrop trasigt tills `'minimal'` (lägsta accepterade) sattes.
4. `ae02a96` — Timeouten 15s kopierad från Vercels budget, appen körs på Railway utan
   det taket. Höjd till 25s.
5. `ed60d10` — Gemini-sökningen i discovery föll med 400 ("Please use a valid role")
   eftersom Vertex kräver `role:"user"` — trasigt sedan Vertex-flytten, dolt av att
   JobTech-källan (nedan) fyllde körningarna. Samtidigt fixades felaktiga redirects i
   webbplatsgissning.
6. `a65ab1e` — JobTech-källan sökte på Snajps egna nyckelord ("kundtjänst") i stället för
   kundens ICP-branscher → helt fel leads, maskerade Vertex-buggen ovan.

**Leads-kvalificeringens träffsäkerhet (c158455, 2b5b8db, 36bf8fa, aa68ccf)**
- `c158455`: "okänd storlek" fällde bolag trots att overlayen sa okänt inte är fel —
  fixbart bara i prompttext.
- `2b5b8db`: Formulärets storleksval nådde aldrig prompten (fältmiss i
  `_med_overrides`), bemanningsföretag godkändes felaktigt. Ny kodgrind
  `kvalificeringsgrind.py` som bara kan fälla.
- `36bf8fa`: `stopped_early` hårdkodad `None` i V2 → underkända bolag fick mejlutkast.
- `aa68ccf`: Skrapningen (ScrapeGraphAI) blockerade API:t synkront upp till 60s, missade
  parkerade sidor. Ny `platshallare.py` sorterar bort sådana träffar.

**Bokföringssajten: ny inloggning ersätter Basic Auth (817ba04, 2e467be, c074df9)**
- `817ba04`: Basic Auth gav ingen feedback vid fel lösenord. Egen `/logga-in`-sida,
  sessionskaka, 401-JSON för API-anrop. Osatt lösenordsvariabel = ingen vägg lokalt.
- `2e467be`: Redirecten byggde på `request.url` = `localhost:8080` bakom Railways proxy
  → fel lösenord skickade webbläsaren till localhost. Fixat via
  `x-forwarded-proto/-host`.
- `c074df9`: Inloggade kunder skickas till extern bokföringstjänst när
  `BOKFORING_EXTERN_URL` är satt (bara development tills vidare).

**Databas (6b9c069)**: Migration 064 gav RLS-policy men glömde `GRANT SELECT` →
`InsufficientPrivilegeError` i loggarna. Fixat i development, väntar på main.

**Dokumentation/release (d977efc, 9ea2213, 35d4f70, c7b242b, 3801d54)**: sessionsloggar +
handoff-fil `HANDOFF-2026-09-15-RELEASE-TILL-MAIN.md` som sammanställer allt inför
development→main, inklusive krav på att köra migration 065 före merge.

---

## Handoff till nästa agent

**Kontext:** Anton bad om en fullständig genomgång av allt Sebbe gjort sedan 3/9. Det är
gjort (ovan). Ingen kod har ändrats av mig i denna session — rent research-/
sammanställningsuppdrag.

**Vad som ännu inte är gjort och sannolikt är nästa steg:**
1. **Release till main är inte kört.** Enligt `HANDOFF-2026-09-15-RELEASE-TILL-MAIN.md`
   och projektdigestet (`main ligger ~80 commits efter development och kör gammal kod`)
   väntar en stor batch fixar (Vertex-migreringen, leadskvalitet, bokföringskontering,
   RLS-grant, migrationer 062–065) på att flyttas till main. **Kör inte detta utan
   Antons uttryckliga go-ahead** — projektregel (`CLAUDE.md`, §"main-kedjan").
2. **Dataskyddsfrågan om språkmodell-leverantören** är enligt GOALS.md/projektdigestet
   fortfarande öppen och är nästa uttalade delmål.
3. **`IMAP_PASSWORD_LIVRUSTNING` saknas på Railway api** (både main och development)
   enligt projektdigestet — blockerar leads-mejl för den tenanten.
4. **Livrustning-tenantens garantiperiod** väntar på kundens bekräftelse.
5. Detta dokument (`SEBBE_HANDOFF_2026-09-16.md`) är en tillfällig arbetsfil i
   projektroten — flytta relevant substans till en session-logg eller `bd remember` och
   radera filen när den är konsumerad, i linje med "skriv aldrig kanoniskt minne mitt i
   sessionen" och "använd bd, inte MEMORY.md/markdown-TODO".

**Öppna trådar från BLOCKS.md (nämnt i projektdigestet, ej verifierat i denna session):**
Ett mönster där två dokument från samma auktoritet (sajtcopy vs villkorsdokument) gav
olika värden för samma påstående — en smalare auktoritativ källa som behövdes för att
skilja dem åt svarade inte. Se `bd show` för hela ärendet innan du agerar på det.

**Rekommendation:** be Anton om explicit besked innan du rör main-releasen eller
dataskyddsfrågan — båda är beslut som enligt projektreglerna kräver hans ord, inte bara
att koden är klar i development.
