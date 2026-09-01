# Snipra Status

## 2026-09-02 — Claude/Sebbe — agenterna drar färre anrop: grindar, snabbsök, GDPR-lager

Beställningen var att sänka credits/anrop utan kvalitetstapp, och svaret är
GRINDAR för utfall som ändå kasserades — inte tunnare prompts:

* **Leads:** okvalificerat eller kontaktlöst prospekt stoppar efter
  ICP-steget: 3 anrop i stället för 9, och utkastfasen (4–7 anrop till)
  hoppas över. `icp_fit`/`qualified`/`disqualifiers` persisteras ÄNTLIGEN på
  prospektraden (migration 024:s syfte — ingen kodväg skrev dem).
  Sökprompten bär nu SNI-koder, regioner och exclude_domains — en kund med
  enbart SNI-koder sökte tidigare "hela internet" med tom målgruppstext.
  Kontaktkravet är kodgrind, inte bara prompttext.
* **Leads-snabbsöket byggt** (`scope="sok"` + `LeadsSnabbsok.tsx` till höger
  om formuläret på /admin/testkorningar): en rad, "Sök Leads", 12 leads med
  kontaktväg för EN Gemini-sökning. Träffar utan kontakt räknas separat.
* **Support:** eskaleringssteget (kedjans enda thinking-anrop) villkorat —
  körs bara vid kb-lucka, säkerhetssignal eller när kunden ber om en
  människa (ny kodregex tar över exakt den signalen). 6→5 anrop på lyckliga
  flödet. Följdfrågegränsen höjd till TVÅ motfrågor innan kb-lucka
  eskalerar. Påhoppsgrinden orörd och verifierad: svordomar eskalerar inte,
  riktade allvarliga hot gör det.
* **Bokföring:** chattagenten läser nu det globala instruktionslagret (var
  enda LLM-ytan där adminredigerade regler inte nådde fram), dataskyddsblock
  i systemprompten och nytt kunskapsämne `gdpr_och_bokforing`.
* **Dataskydd:** ScrapeGraphAI stod INTE i underleverantörslistan trots att
  den hämtat prospektsidor sedan skrapningen byggdes — tillagd i
  `lib/bolag.ts`, DPA/region flaggade till Anton. Full kunddatalista i
  handoffen. INV-API-001 föll på HEAD (`lib/skatteverket/oauth.ts`) — lagad.

Parallellsessionen (snipe-leads-28) levererade i samma push: INV-JOB-002-
liggaren (migration 059, körd mot dev före pushen), tokenbudget och
V2-playbooks bakom env-flagga; körvägen `leads_research_v2.py` kommer i
deras egen push.

**1717 backendtester + 386 rotvakter gröna, tsc rent.** Deployad `ef9a1af`
(auto-deployen fungerar igen). Handoff:
`HANDOFF-2026-09-02-RESURSER-OCH-GRINDAR.md`.

## 2026-09-01 — Claude/Sebbe — UTSKICKEN FUNGERAR. Sista sändblockeraren avförd.

Ett riktigt mejl gick från Railway-containern hela vägen till inkorgen:
`Snajp <kontakt@snajp.se>` -> snajpsupport@gmail.com, status **delivered**
i Resend. Egen domän, DKIM-signerat, via HTTPS.

Vägen dit, för den som möter samma vägg igen:
* Railway blockerar utgående SMTP på Free/Trial/Hobby (mätt inifrån
  containern med `GET /api/admin/sandvag`: 587/465/2525 ger alla timeout).
  Gmail-app-lösenord kan alltså aldrig fungera här. Samma vägg som Render
  gav 2026-07-30.
* Lösningen är HTTPS via Resend (`ResendMailer`, väljs av RESEND_API_KEY och
  går före SMTP). snajp.se är verifierad i **eu-west-1** — EU-regionen valdes
  medvetet, samma dataskyddsresonemang som fällde DeepSeek.
* DNS hos Loopia: DKIM-TXT på `resend._domainkey`, CNAME `send` och `rsend`,
  TXT `_dmarc`. Apex orörd — MX:en dit `kontakt@snajp.se` pekar.
* Två falska spår kostade tid: negativ DNS-cache hos Google (jag slog upp
  posterna innan de fanns), och en API-nyckel som var sändnings-begränsad
  och därför inte kunde se att domänen var verifierad.

**Verifiera själv:** `POST /api/admin/sandvag/prov?till=<adress>` (master-nyckel).

**Kvar på sändsidan:** godkänt supportsvar genom hela flödet är ännu inte
kört mot ett RIKTIGT inkommande mejl — testmejl (provider='mock') skickas
aldrig med flit, och IMAP är inte kopplat, så det finns inga riktiga att
godkänna än. Koden är enhetstestad; kedjan är bevisad till och med Resend.
Produktionen (`main`) har INGA mejlvariabler satta — den är orörd.

## 2026-08-31 (eftermiddag) — Grok — Starta körning dog på timeout

Anton tryckte Starta körning (tomma Egna bolag) och fick "Kunde inte nå
servern". Inte 422: Gemini+Google-sökningen låg i POST-svaret, Next-proxyn
avbryter efter 9 s, Safari ser TypeError. Sökningen är nu ett jobb
(`fase=soker`); knappen får 202 direkt. POST görs inte om (fem omförsök
startade fem sökningar). Manuell Railway-deploy krävs.

## 2026-08-31 (sen kväll) — Grok — leads-kedjan hittar bolag

Körningen krävde ifyllda namn i Egna bolag (422), behandlade "Inget, hitta
själv" som bolagsnamn, plockade gamla rader ur registret och skrev inget
utkast trots "Research och utkast". Nu: ICP → sök (Gemini + Google) →
registrera bolagets egen sajt → research → utkast. Egna bolag är valfritt.
Placeholder säger det.

## 2026-08-31 (kväll) — Grok — testmail isolerade, flytta-formulär, byt kund, pushat

Kvarvarande punkter från morgonens plan: is_test på inkorg/ärenden (migration
057 körd mot development), Testmail-flik för riktiga kunder, ifyllnad vid
Flytta över, sökbar kundväxel i headern, knapp för testkund → riktigt konto.
21 exempelbolag raderade från Snajp-tenanten. Redis: EU, SEMANTIC_CACHE=shadow,
TLS fortfarande av (kräver `python scripts/redis_tls_pa.py --apply` av Anton).

Pushat till `origin/development`. Auto-deploytriggern är död sedan 29/8 —
manuell Railway-deploy krävs. Handoff:
`HANDOFF-2026-08-31-TESTISOLERING.md`.

## 2026-08-31 — Grok — exempelkörningar borta, testmail mot profilen, testchatt kalibrerar

Anton visade fjorton skärmbilder: leads som spottade färdiga VVS-pitchar,
flytta röd på `.example`, inkorg som först såg statisk ut, nästan allt
eskalerat, testchattens kunskapsartikel som lät som uppladdad affärskontext.

Byggt lokalt på `development` (inte pushat):

- Exempelbolag skapas bara för Nordlys/demo. Formuläret pollar den riktiga
  batchen. 403 utanför demon.
- Testmail byggs ur tenantens kunskapsbas. Inkorgen visar Bearbetas medan
  agenten läser.
- Testchatten öppnar undersökningsärende i stället för att default-spara KB.
  Feedback 403 på skarpa körningar; rättningar läses i nästa testchatt.
- Admin som tittar som kund tvingar `is_test` i proxyn.
- Inställningsmenyn: Underlag först, vanlig svenska.

Live mot Railway och Redis-TLS är inte kört. Handoff:
`HANDOFF-2026-08-31-TESTLAGER-OCH-UI.md`.

## 2026-08-30 — Claude — leads-batchens NameError lagad; UI:t visar ändå bara exempelbolag

Anton rapporterade att leadskörningar "fortfarande genererar färdiga exempel
direkt" trots gårdagens Redis-fasleverans. Grävning visade två separata fel:

- **Backend, lagad:** `_gather_registered_sources` i `leads_agent.py` kraschade
  med `NameError: name 'skatteverket' is not defined` på VARJE riktig
  batchkörning, före första LLM-anropet. Sviten var grön eftersom alla
  batchtester monkeypatchar `run_research_step`. Fixad, omockat test
  verifierat rött→grönt, deployad och verifierad med en riktig körning mot
  live dev (`status: completed`).
- **Frontend, INTE lagad — dokumenterad handoff:** `LeadsRunForm.tsx` visar
  aldrig den riktiga körningens resultat. Exempelbolagens pitch-text är
  hundraprocentigt färdigskriven i kod och renderas direkt (default-checkbox
  påslagen); den riktiga batchens `job_id` pollas aldrig. Se
  `HANDOFF-2026-08-30-LEADS-KORNING.md`.

Samtidigt: KB-artikeltext wrappas nu som opålitlig text (INV-SEC-012 skärkt
till två lager), och Railways deploytrigger för `development` visade sig ha
slutat fira sedan 2026-08-29 22:42Z — omgången med manuell deploy, orsaken
inte undersökt. Se `HANDOFF-2026-08-30-KB-WRAP.md` och
`session-logs/2026-08-30-session-log.md`.

## 2026-08-29 (sen kväll) — Claude/Sebbe — adminytan fylld, tvåspråkig och läsbar; tokenkostnaden satt till leverantörens riktiga pris

**Utgångspunkt: tre skärmbilder.** Kolumner fulla av nollor i Översikt och
Kunder & Data, engelska flikar över svenska tabellrubriker, och ett notiscenter
som visade leverantörernas råa JSON-fel som brödtext.

**Byggt och deployat (sex commits, alla `SUCCESS` på development):**
- **Exempeldata** (`lib/admin/exempeldata.ts`) på arbetsytor HELT utan
  aktivitet. Deterministiskt härlett ur tenantens id, sex profiler, varje rad
  märkt `Exempel` och räknad i en fotnot. Rader med riktig aktivitet — Nordlys
  Handel, Snajp — rörs aldrig. Av med `NEXT_PUBLIC_ADMIN_EXEMPELDATA=av`.
- **Tvåspråkig adminyta** (`lib/admin/sprak.ts`). Kolumnrubriker, hälsotexter,
  statistik, rådgivarens frågor och svar, fotnoter, plattformsflikar. Språkvalet
  sparas i `localStorage` — det snäppte förut tillbaka vid varje omladdning.
- **Läsbara händelsetexter** (`lib/admin/handelsetext.ts`). Tio tolkare gör om
  undantagstext till rubrik och förklaring; råtexten ligger kvar bakom
  "Tekniska detaljer". `RateLimitError: Error code: 429 - [{'error'...` blev
  "Kvoten hos Google Gemini (gemini-3.6-flash) är slut".
- **Statistikgrafen** fylls av exempelraderna, utspridda över hela
  tolvveckorsfönstret. Demoytorna (`nordlys-handel`, `public-demo`) räknas
  aldrig som kunder, oavsett märke.

**Hydreringsbugg hittad och rättad i samma andetag.** Konverteringen till
klientkomponenter tog med `Date.now()` och tidszonsberoende datumformatering
över server/klient-gränsen: servern kör UTC, webbläsaren Europe/Stockholm, och
en tidsstämpel strax före midnatt UTC blev olika datum i de två renderingarna.
Klockan läses nu en gång på servern och skickas ned som `nu: number`; tidszonen
är spikad i `sprak.ts`. Verifierat med Playwright mot tre webbläsartidszoner,
med och utan fixen — ett hydreringstest som inte kan falla bevisar ingenting.

**Tokenkostnaden var fel om fel leverantör.** `TOKENKOSTNAD_PER_MILJON_SEK = 12`
beskrev "DeepSeek-klassen". Railway säger `LLM_PROVIDER=gemini`,
`MODEL=gemini-3.6-flash` i BÅDA miljöerna, och DeepSeek är dessutom spärrad där
kunddata finns. Konstanten är nu två, eftersom utgående tokens kostar fem gånger
mer än ingående: **7,14 kr in / 35,71 kr ut per miljon**, Googles listpris
omräknat till 9,5237 SEK/USD.

**MÄTT: faktureringen hos Google är fortfarande inte påslagen.** Felloggen visar
`generate_content_free_tier_requests, limit: 20`, samma sak som
`docs/JURIDIK_ATGARDER.md` mätte. Det verkliga utfallet i kronor är alltså noll
— betalat i genomströmning i stället för i pengar — och talen ovan visar vad det
kostar den dag faktureringen slås på. **Listpriset dubblas 2027-01-01**
(14,29 / 71,43); står i docstringen så att marginalfallet inte läses som en bugg.

**Kvarstår:** marginalkolumnen är i praktiken konstant 100 % vid realistiska
volymer — ett paket på 6 990 kr tål ~39 miljoner utgående tokens innan
marginalen ens blir gul. Det är en egenskap hos affären, inte hos koden, och
kräver ett beslut när en riktig faktura finns.

Session: `session-logs/2026-08-29-session-log-4.md` ·
Plan: `plans/2026-08-29-adminytan-exempeldata-och-sprak.md`

## 2026-08-29 (kväll) — Claude/Sebbe — main och development delade Redis-nyckelrymd: jobbströmmen korsade miljögränsen

**Hittat genom att svara på varför `redis-cli` inte fanns på Windows.** Mätt
mot Railways API och den körande instansen: `main` och `development` har
IDENTISK `REDIS_URL`, båda svarade `jobs: redis`, och ingen nyckel bar miljö.
Redis Cloud-gratisnivån ger EN logisk databas (`SELECT 1` → "DB index is out
of range"), så miljöerna låg i samma nyckelrymd.

**Aktivt exponerat, inte teoretiskt:**
- **Jobbströmmen.** En enda consumer group `agenter` på `crm:jobb:chatt`, med
  konsumenter från NIO containrar. En grupp delar ut varje post till exakt EN
  konsument — ett chattjobb från en riktig kund kunde alltså köras av en
  development-container mot spegeldatabasen, och tvärtom. Att en specifik
  körning korsade går inte att bevisa i efterhand (pending var 0, ingen
  per-post-logg); exponeringen var det.
- **Arbetsminnet** (`minne:{tenant}:{kund}`). Kopplas in så fort `REDIS_URL`
  finns, alltså i båda miljöerna, och development speglar produktionen med
  IDENTISKA tenant- och kund-id:n.

**Latent, inte aktivt:** svarscachen delade `svarscache_idx` (filtrerar på
`tenant`), men `SEMANTIC_CACHE` är osatt i main och defaulten är `off` — den
hade blivit aktiv i samma sekund någon slog på den. Embeddingcachen delas
också, vilket är ofarligt (ren funktion av texten).

**Åtgärdat i kod:** nio ytor går nu genom `app/redisnycklar.nyckel()` —
jobbposter, chatt- och leadsströmmarna, embeddingcachen, KB- och
konfigversionerna, arbetsminnet, samt svarscachens nycklar OCH dess FT-index.
Fröet är HELA DSN:en plus miljönamnet, och det är ett mätresultat: första
utkastet hashade värd + databasnamn och hade varit VERKNINGSLÖST, eftersom
båda miljöerna kör mot `postgres.railway.internal:5432/railway` som
`snajp_app` — bara lösenordet skiljer. `INV-REDIS-001` prövar exakt det
fallet, och är verifierad genom att brytas med flit.

**Verifierat mot körande Redis efter deploy:** `nsb340e34a:crm:jobb:chatt`
och `...:leads` finns nu med egna konsumenter. Development har lämnat den
delade rymden, alltså är korskopplingen stängd framåt. 1998 tester gröna.

**KVAR — Antons hand:** `main` kör fortfarande på de onamnrymdade nycklarna
tills den deployas (tvåstegspushen + NO-GO-listan). Den är ensam där nu, så
exponeringen är borta, men produktionen får sin namnrymd först vid deploy.
Egen Redis-instans åt `main` (plan R5) kräver betald nivå och är fortfarande
rätt slutläge. Redis-lösenordet klistrades in i klartext i en chatt — rotera
det i Redis Cloud när tillfälle ges.

## 2026-08-29 (morgon) — Claude — sjufasplanen + Redis-arkitekturen byggd, verifierad och PUSHAD till development

**Hela beställningen från 2026-08-28 är implementerad** (Fas 1–6 + Fas 7:s
förberedelse) plus den nya Redis-arkitekturen (Fas R0–R4), tre commits
(`cb05da0`, `f25e91b`, `0512ab3`). Arbetet dirigerades till nio
Sonnet-delagenter med egen granskning av varje leverans — viktigaste
egenfyndet var RediSearch TAG-escapningsbuggen (UUID-bindestreck), som
BARA liveverifieringen mot dev-databasens riktiga Query Engine kunde se.

**Chattkörningar överlever nu en deploy** (Redis Streams + XAUTOCLAIM +
idempotent återupptagning, INV-JOB-001), **semantisk svarscache** i
mörkstartsläge (`SEMANTIC_CACHE=shadow` satt i dev — träffkvot läses i
Händelser; INV-CACHE-001 med PII-/minnes-/påhopps-/kategorigrindar),
**rullande samtalsminne** (INV-MEM-002), Testchatt-flik mot inloggad tenant,
befordran test→riktigt konto med Luhn-validering, `agent_runs.model`,
`origin='test'` hela vägen. Migration 054+055 applicerade FÖRE pushen.
**1586+362 tester gröna** (101 nya), tsc rent, `qa_vyer` GRÖNT mot live dev,
uppstartsloggen visar ström-workers + cachelager aktiva.

**B1 skärpt med mätdata:** nya Gemini-nyckeln svarar ~170 s/anrop (strypt
kö) och Railway kör fortfarande GAMLA nyckeln i båda miljöerna —
chatt-E2E:t på dev gick hela strömkedjan och föll exakt på 429-dygnskvoten.
**Antons kommandolista** (allt förberett, klassificeraren krävde
människohand): `redis_tls_pa.py --apply` (TLS är AV — trafiken okrypterad,
regionen EU-verifierad), `gemini_web_konfig.py --apply`, Redis DPA,
B1-konsolsteget. Redis Cloud + Resend står nu som underbiträden i
juridikkedjan; Resend-sändvägen bekräftad live (varningen borta).

Fullständig karta: [HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md](HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md)
· [plans/2026-08-29-redis-agentarkitektur.md](plans/2026-08-29-redis-agentarkitektur.md)
· [session-logs/2026-08-29-session-log-3.md](session-logs/2026-08-29-session-log-3.md)

## 2026-08-29 — Claude — Sebbes 24 commits genomgångna, Resend + Redis konfigurerade i development

**Läste in och redogjorde för allt Sebbe (med Claude) byggt sedan Antons
senaste commit (`090a0ba` → `9d15d73`, 24 commits, tre nätter):**
lanseringsgranskningen (triage-timtak, dev-masternyckelvakt,
`agent_feedback`-sortering, fyra frontend-fixar), mejlsändningen i tre steg
(SMTP byggd → uppmätt att Railway blockerar utgående SMTP på trial-planen →
byggd om till Resend/HTTPS), och adminfliken "Kunder & Data" (kundregister
med käll-märkning per fält, statistik, felöversikt — intäkter/utgifter
medvetet INTE byggt som siffror, väntar på Antons beslut om datakälla). Full
detalj i `HANDOFF-2026-08-27-GRANSKNING.md` och
`HANDOFF-2026-08-29-KUNDER-DATA.md`.

**Resend satt i `development`:** `RESEND_API_KEY`, `EMAIL_PROVIDER=resend`,
`SMTP_FROM=kontakt@snajp.se` — bekräftat i Railways variabellager, men
deployen stod kvar som `BUILDING` vid sessionens slut och `/health/ready`
visade fortfarande varningen om saknad sändväg i sista kontrollen. Inget
fel, bara inte utrullad än — nästa session kollar `curl .../health/ready`
igen innan den litar på att den är live.

**Redis Cloud kopplad som jobbkö.** Ny databas ("Snajp-Chat-Data") satt som
`REDIS_URL` på `development/api` (`scripts/redis_konfig.py`, nytt).
**Bekräftat live:** `/health` svarar `"jobs":"redis"` — en omstart av
`api`-tjänsten tappar inte längre pågående chatt-/leads-jobb. Redis Clouds
konto-nivå-API sparat i `.env.deploy` (`scripts/redis_cloud_nycklar.py`,
nytt) efter en felsökning som visade att Cloudflare (framför Redis Clouds
API) blockerade Pythons standard-`User-Agent` — inget fel i nyckelparet, som
det först såg ut som. Förkravet för att provisionera fler Redis-databaser är
nu på plats; vad de ska användas till är en öppen fråga till Anton.

Redis-databasen delas INTE med `main` — samma tysta-korskoppling-resonemang
som redan gäller `GEMINI_API_KEY`. `main` har fortfarande varken Resend,
Redis eller Kunder & Data; produktionsspärren från
`plans/2026-08-28-skarpa-korningar-och-produktion.md` §8.1a gäller
oförändrat, allt arbete gick mot `development`.

Fullständig sessionslogg: [session-logs/2026-08-29-session-log.md](session-logs/2026-08-29-session-log.md)

## 2026-08-29 (natt) — Claude/Sebbe — adminfliken Kunder & Data: kundregister, statistik, felöversikt

**Live i development, migration 053 körd.** Handoff till Anton:
[HANDOFF-2026-08-29-KUNDER-DATA.md](HANDOFF-2026-08-29-KUNDER-DATA.md).

Befintliga fliken Kunder utbyggd (inte kopierad) till "Kunder & Data",
sidtitel `Snajp - Kunder&Data`. **Migration 053**: `ss_customer_details`
(orgnr, fakturerings- och adressfält, kund_sedan, avtal_signerat) +
`ss_customer_contacts`, båda admin-only via 029-mönstret (åtkomliga bara på
OSKOPAD anslutning). Backend: `api/admin_kunddata.py` bakom
`require_master_key`, fältlistan delad i `storage/base.py`. Skrivningen går via
server actions, eftersom adminproxyn är GET-only med flit och den regeln inte
luckrades upp.

**Bärande beslut: varje fält bär sin källa** (`manuell`/`onboarding`/`system`/
saknas). Bara orgnr och kund-sedan går att härleda i dag; resten finns inte i
någon datakälla. Ett härlett värde som ser handbekräftat ut i ett
faktureringsunderlag är felet som kostar pengar hos någon annan. Följdregel:
klienten skickar bara ÄNDRADE fält, annars blir varje härlett värde manuellt
vid första sparning.

Statistik: avtal per dag/vecka/månad/år + veckograf (nya kunder, signerade
avtal) + försäljningstakt. Demo- och testytor räknas aldrig som kunder, men
göms inte. Fel & eskaleringar sammanfattar `platform_events` +
`ss_tickets.status='escalated'` — inget nytt felsystem, länk till Händelser.

**Intäkter/utgifter byggdes MEDVETET inte.** Det finns ingen riktig
betalkälla: migration 044:s betalsätt är Stripes testkort mot simulerad
provider, fakturor/nummerserie/moms saknas i kod. Sidan säger det rakt ut i
stället för att visa påhittade siffror. Datakälla är Antons beslut.

**1505 tester gröna** (13 nya), tsc rent, `qa_vyer.mjs` GRÖNT mot körande dev,
nya detaljvyn besiktigad inloggad (noll JS-fel, noll 4xx). Lokal fullstack gick
inte att resa — pgvector saknas i lokala PostgreSQL 17 — så UI:t granskades via
en okommittad preview-route + Playwright på 1440/375 i båda lägena.

## 2026-08-28 — Claude — sjufasplan för skarpa körningar, produktionsspärren hittad, Loopia satt

Anton bad om sju saker på en gång: gör alla körningar skarpa, skilj
testkörningar från kundens riktiga konto, prospektbefordran, Email-studion
in i leaden, en Testchatt-flik, minst 10 riktiga rundor DeepSeek/Gemini, och
förberedd produktion på `main`. Fem parallella delagenter kartlade ytan;
varje bärande fynd verifierades själv innan det gick in i planen —
[plans/2026-08-28-skarpa-korningar-och-produktion.md](plans/2026-08-28-skarpa-korningar-och-produktion.md),
17 `bd`-ärenden med beroenden, publicerat sammanfattningsdokument.

**Varför körningarna ser autogenererade ut — fyra oberoende orsaker.**
Email-studions modellväljare kände aldrig till Gemini (bara OpenAI/DeepSeek),
föll alltid till mallgenererad text; exempelbolagen är deterministiska med
flit men oskiljbara från en AI-körning i UI:t; Gemini kör gratisnivå (20
anrop/dygn) trots betalt faktureringskonto — nyckelns PROJEKT var inte
kopplat till kontot; ingen sändväg finns (varken IMAP in eller SMTP ut).
Simuleringsläget i backenden var **inte** aktivt — båda miljöer `mode: live`.

**Produktionsdeployen är farligare än dokumenterat.** `git rev-list` mot
`origin` visade `main` som strikt förfader till `railway-main` (152 commits
efter, noll före) — den dokumenterade `git push origin main:railway-main`
skulle i dag avvisas eller, tvingad igenom, rulla tillbaka 22 aug-omläggningen
och 25 aug-hotfixen. Verifierat att `development` redan innehåller hotfixens
fulla innehåll, så säkra vägen är merge, inte force. **Produktionen rörs inte
förrän Anton säger till** — skrivet in i planen på tre ställen.

**Loopia satt och verifierat live.** `scripts/loopia_nycklar.py` (nytt,
säker inklistring via getpass) → `python scripts/loopia_dns.py` returnerade
riktiga MX/NS/TXT-poster från Loopias servrar, alltså bekräftat fungerande.
`www.snajp.se`-CNAME väntar bara på `--apply`; apex-vidarebefordran förblir
manuell (finns inte i LoopiaAPI).

**Gemini — pågående, inte stängt.** Nyckeln var en Vertex AI Express
Mode-nyckel vars PROJEKT (`snajp-506221`) inte var kopplat till
faktureringskontot — därför gratisnivå trots betalt konto. Anton har sedan
kopplat ett nytt projekt och bytt nyckel via `scripts/keys.py`, men det är
INTE verifierat live än (nästa session: `python scripts/kor_evals.py`, ingen
429 = bekräftat).

`scripts/keys.py` säkrad: ett `FIXED`-block skrev tidigare ovillkorligt över
`LLM_PROVIDER`/`MODEL` vid varje inklistring — samma felklass som
`snipe-u70`. Skriver nu bara på ett tomt fält.

Fullständig sessionslogg: [session-logs/2026-08-28-session-log.md](session-logs/2026-08-28-session-log.md)

## 2026-08-28 — Claude/Sebbe — MÄTT: Railway blockerar SMTP. HTTPS-vägen byggd.

`/api/admin/sandvag` kördes mot den körande dev-containern: portarna 587, 465
och 2525 ger alla TimeoutError ut mot smtp.gmail.com. Railway släpper igenom
utgående SMTP först på Pro; projektet ligger på `trial`. **Gmail-kontot med
app-lösenord kan alltså aldrig fungera här** — det är inte ett fel i
uppgifterna, och ingen ska felsöka lösenordet igen.

Samma vägg som Render gav 2026-07-30 (commit 0d3ac1d). Byggt i stället:
`ResendMailer` (HTTPS, väljs av RESEND_API_KEY och går före SMTP),
`BlockeradSmtpPort` som översätter errno 101/110/111 till "byt kanal", och
`/api/admin/sandvag` så frågan går att ställa på en sekund nästa gång.

**Kvar — och bara en människa kan göra det:** konto på resend.com, verifiera
snajp.se med tre DNS-poster hos Loopia (ger DKIM), sedan
`python scripts/smtp_konfig.py --env development --apply --resend
--avsandare-resend hej@snajp.se`. Gratisnivån (3 000/mån) rymmer paketens 300.

## 2026-08-28 (efter midnatt) — Claude/Sebbe — SMTP-sändvägen byggd (snipe-ork stängd i kod)

`SmtpMailer` + `email_pipeline/sender.py` + kopplingen i approve/autosvar,
commit `cec72ad`, live i development. Kontraktet: 'sent' kan aldrig ljuga —
sändning sker före status, fel ger 502/granskningskö, testmejl skickas aldrig,
torrkörning vinner över SMTP. 17 nya tester, 1467 gröna. **Aktivering är ett
människosteg:** sätt SMTP_HOST/USER/PASSWORD (+ ev. FROM) i Railway, se
DEPLOY.md § "Kundvänd utgående SMTP". Tills dess loggas utskick som förut.
Kvar: per-tenant-avsändare (Del F), Next-appens egna mejlvägar (glömt
lösenord/demo-länk), snipe-xl9 väntar på riktiga inkommande svar.

## 2026-08-27 (senare samma natt) — Claude/Sebbe — go/no-go-granskning, tre av Antons trådar stängda, fem fixar live i development

Full lanseringsgranskning av hela ytan + live-verifiering; rapport i
`HANDOFF-2026-08-27-GRANSKNING.md`, sessionslogg i
`session-logs/2026-08-27-session-log.md`. **Isolering GODKÄND mot körande DB**
(snajp_web/snajp_app utan BYPASSRLS, RLS 64/64 tabeller). Antons agentbackend-
handoff genomgången: RRF-fusionen skarpverifierad mot Postgres, chat-E2E grön
hela HTTP-vägen (KB-grundat svar), larande-vyerna verifierade inloggat.
Svar-E2E blockerad av Gemini-429 (chatten gick igenom — troligen annan
kvotpott per modell). Antons enda röda test lagat (agent_feedback-sortering)
→ 1450 gröna. Nytt i koden: timtak på /api/triage (var enda LLM-vägen utan
enforce), startvakt mot dev-masternyckeln, error.tsx/global-error.tsx,
429-texter, EjAktiverad i supportinkorgen, fyra catch-lösa hämtvägar.
Pushat till `development` (nya deploy-kedjan), deployad commit f081e11
verifierad med verify_railway.py — allt grönt. `main` orörd; kvarstående
main-blockerare i handoffens §4 (SMTP-attrappen, fakturering, orgnr-
platshållaren, kvoterna 150/300, Redis, Gemini-kvoten).


## 2026-08-27 (natt) — Claude — varv 2–3: mätningen bevisad, grindarna skärpta, och två arkitekturmönster hämtade utifrån

Fortsättning på kvällens audit, på Antons uttryckliga "fortsätt tills jag säger
stopp". Milstolperapport med all mätdata:
https://claude.ai/code/artifact/862c4b3b-e058-4959-86b8-caa84591b127

**Mätningen gjord på riktigt (4 skarpa körningar + jämförelseskript).**
Support: S1-vändningen (7 aug eskalerade mot seedad KB → svarar nu),
S2-vändningen (falsk retention_risk → svarar själv med KB-grundad plan;
klassarvillkoret lagat: missnöje ensamt bär aldrig retention-etiketten).
Leads: evidensreglerna bet direkt (ämnesrader bär mottagarens fakta, EN
uppmaning, "troligen" borta); referensregeln träffade 3/3 i EFTER-körningen;
grundningscykeln fällde+reparerade+köade skarpt. `--skarp`-verifiering:
modellen följde injicerad kundinstruktion ordagrant.

**Gissningsordsgrinden i kod** (`app/leads/gissnings_gate.py`): overlay-regeln
visade sig vara en riktning ("lär"/"brukar" slank igenom) — nu kodgrind,
testad mot exakt de meningarna, inkopplad i alla tre utkastvägarna med samma
reparationscykel som grundningen.

**Adminytan Lärande** (`/dashboard/larande`, `components/leads/AgentLarande.tsx`):
förslagen godkänns/avfärdas (godkänd KB-artikel skapas av backend-endpointen,
aldrig av klienten), teamets domar listas read-only därunder. Wirad i
routes/i18n/WorkspaceViews; rotvaktpost tillagd (333 gröna). *(En
processomstart tappade kontexten om att ytan byggts — en mellanversion av den
här posten kallade den felaktigt obyggd; verifierad på disk och i tsc/vaktposter
2026-08-27.)*

**Varv 3 — arkitektur utifrån, husanpassad:**
- **Eval-harness** (Langfuse/promptfoo/Ragas-mönstret): `app/agent/evals.py`,
  7 golden cases ur VERKLIGA incidenter, faithfulness mätt med
  grundningsextraktorn i stället för LLM-domare, `scripts/kor_evals.py`
  (exit 1 vid fall). Döda `agent_evals` fick sin första kodväg, och nedtummad
  feedback med rättad text blir AUTOMATISKT ett eval-case — fältets
  "live trafik in i golden-setet", mekaniskt.
- **Kundminne** (mem0 ADD-only): migration 052 `customer_memory`, extraktion
  inbakad i triagesteget (noll extra anrop), ny invariant **INV-MEM-001**
  (bara kundens egna utsagor, aldrig agentens slutsatser, alltid
  untrusted-wrappat — injektionsattack-testat). `agent_feedback` fick också
  sin första kodväg (verdict + corrected_output, POST /api/agent/feedback).
- Avvisade med motivering: Zep-graf, LLM-domare, A/B-bandit (blockerad av att
  offers-rader aldrig skrivs — samma rot som weakest_lever, snipe-3dx).

**1445 backendtester gröna** (1338 vid sessionens start), 333 rotvaktposter.
**Eval-harnessen skarpkörd: 7/7 golden cases godkända mot riktig modell**
(docs/live-tests/evals-20260826-222210.json) — inklusive faithfulness-mätningen.
Migration 051+052 parsas som pending. Allt okommittat — commit/push/migration
väntar på Antons ord.

## 2026-08-26 (kväll) — Claude — djupaudit av agentbackenden: tre döda kedjor hittade, självlärningen persisterad, svar och uppföljningar byggda

**Tre saker som såg färdiga ut var aldrig inkopplade, och en av dem kunde inte
ens köras i produktion.** (1) Ingen kodväg skapade någonsin en
`outreach_threads`-rad — `queue_outreach_message` skrev mot ett thread_id som
bara hand-SQL kunde ha skapat. MemoryStorage saknar FK-kontrollen, så sviten
var grön medan Postgres hade fällt första riktiga köningen. Nu:
`ensure_outreach_thread` (get-or-create per prospekt) i alla tre lagringarna,
och API:t tar `prospect_id` som alternativ till `thread_id`. (2) Prospektsvar
hade ingen hanteringsväg alls — `list_replies` läste en tabell inget fyllde,
`route_handoff` saknade anropare. (3) `follow_up.py`:s hela sekvenslogik
anropades bara från tester (snipe-3dx).

**Svarshanteringen byggd** (`app/leads/svar.py`, `POST /api/leads/svar`):
klassificering (positivt/invandning/fraga/negativt/avregistrering/autosvar,
okänt faller till fraga), påhoppsgrind i kod före allt. Positivt → kön ställs
in, `route_handoff` + `sa:call-prep`-underlag + prioriterat mejl, prospekt →
`meeting`. Invändning/fråga → svarsutkast (skopad mk:sales-enablement →
humanizer → grundningsgrind) som ALLTID köas `awaiting_review`, oavsett
autonominivå — autonomin styr utgående sekvens, inte svar i levande samtal.
Avregistrering → suppression (samma spärr som länken). Autosvar → kön skjuts
en vecka. Grundlöst påstående → människa, ingen reparationsrunda.

**Uppföljningsgeneratorn byggd** (`app/leads/follow_up_generator.py`):
ren due-policy (`trad_som_ar_forfallna`) skild från I/O; stigande delays
(4/6/8/10 dagar), spakvinklar + breakup, grundningsgrind, köning genom SAMMA
väg som första mejlet (fot, språkgrind, autonomi — `draft` ⇒ granskning).
Självbegränsande: ogodkänt utkast gör tråden icke-förfallen; inkommet svar
tar den ur svepet. Schemaläggaren sveper varje timme; manuell trigger
`POST /api/leads/uppfoljning/svep`.

**Självlärningen persisteras** (migration 051, `agent_suggestions`, ny
invariant INV-LEARN-001): supportens `cs:kb-article` och leads
`_fanga_kunskap` räknade ut lärdomar på varje körning och KASTADE dem —
utdatan fanns bara i step_log. Nu sparas de som förslag med dedupe (tio
ärenden om samma lucka = EN rad), och agenten skriver ALDRIG själv i
underlaget: `POST /api/agent/forslag/{id}/godkann` (människans klick) skapar
KB-artikeln. `cs:kb-article` är dessutom VILLKORAT — körs bara vid
kunskapslucka eller säkerhetskritiskt ärende (~1 anrop av 6 sparat på
lyckliga flödet, som per definition saknar lucka att skriva om).

**Retrieval förbättrad på två punkter.** Postgres `search_kb` kör nu UNION av
vektor + fulltext i stället för antingen/eller — en enda svag vektorträff
över tröskeln stängde förut fulltexten helt, även när svaret stod där.
Flerturssökningen: ett kort svar i en fortsättning ("Ja, en Android.") söker
nu med kundens FÖRRA replik inlagd i frågan — den bär ämnet.

**Paritetsluckor som systemet självt fångade under bygget:** `agent_type`-
värdena `leads_svar`/`leads_followup` fälldes av AGENT_RUN_TYPES-spegeln i
test (exakt den mekanism som byggdes efter halvårsbuggen), och memorys
`get_outreach_thread` speglade inte SQL-joinens `prospect_email` — lagat.

**Verifierat:** 1338 → **1390 tester gröna** (52 nya, 0 regressioner).
`verifiera_instruktioner.py`: 6/6 fält i rätt position, global regel i alla
steg. Skill-audit: 22 steg i 4 playbooks renderar komplett, inga trasiga
referenser. Migration 051 parsas och listas som pending av railway_migrate
(appliceras efter deploy, samma ordning som handoffen).

**Kvar:** live före/efter-körningen (`run_live_tests.py --support/--leads`)
blockerades av auto-mode-klassificeraren efter harness-fixen (den blankar nu
DATABASE_URL i egen process — spärren själv är orörd och gjorde rätt) —
snipe-kea. Adminyta för förslagen: snipe-lu4. Mejlpipeline-routing av
prospektsvar: snipe-xl9 (blockeras reellt av snipe-ork). pg_trgm-kandidaten:
snipe-a6i.

## 2026-08-26 — Claude — instruktionslagren byggda och deployade, och pausen från 24:e har hävts utan att åtgärdslistan gjordes

**Migration 049: `agent_configs.instructions_md`/`.tone` fick sin läsväg.** Fälten hade
funnits sedan migration 010 utan att någon kodväg läste dem — en kund kunde spara nya
instruktioner och få identiskt oförändrade svar. Byggt: en global instruktionstabell
(admin-redigerad, fallback till `agent-core/AGENTS.md`), per-kund-instruktioner i
systemposition, en struktureringsgrind (fri text → imperativa regler under fasta
rubriker, kodstädad efteråt), och en adminkundprofil (`/admin/kunder/<id>`) som visar
varje fälts promptposition explicit. Affärskontexten nådde tidigare bara leads-agenten,
aldrig supporten — samma klass av fel, nu åtgärdad. Verifierat med
`scripts/verifiera_instruktioner.py`: sex av sex fält i rätt position, global regel i
alla sex steg, och med `--skarp` följde en riktig modell den injicerade instruktionen
ordagrant. Se `HANDOFF-2026-08-25-INSTRUKTIONER.md` och `docs/FALTKARTA.md`.

**KB-sökningen kedjar nu vektor → fulltext.** Vektorvägen gav tom träfflista så fort
den kom tom, utan fallback; tom träfflista är ett hårt eskaleringsvillkor, så en
retrievalmiss blev ett onödigt människoärende i stället för ett sämre svar.

**Rebasen mot en parallell session (Sebbe/PR #10) hittade en bugg innan den nådde
production.** Ett nytt kunskapssteg (`sa:call-summary`, `_fanga_kunskap`) anropade
`run_step` utan instruktionslagren — det hade läst filens `AGENTS.md` medan de åtta
stegen omkring läste kundens, tyst, utan att något felade. Lagat: varje `run_step`-
anrop i `leads_agent.py` bär nu `instruktioner=`.

**En Supabase-import sänkte tyst Nordlys Handels affärskontext (2026-08-24, upptäckt och
rättat 2026-08-25/26).** Ett tidigt skript skrev importerade kontextdokument som
`max(version)+1`, alltså senaste — ett 726-teckens dokument ersattes av en 43-teckens
Supabase-stubbe utan att något felade. Återställt (ingen historik raderad).
`far_importeras()` vägrar nu skriva in i ett fack som redan har innehåll; regeln testad
mot exakt den import som orsakade skadan.

**Windows/git-fälla värd att komma ihåg:** Python-skript utan explicit `newline='\n'`
skrev CRLF i tio filer i det här LF-repot, vilket fick en 3200-radersdiff att se ut
som 7000+ rader omskrivna och hade gett konflikt på varenda rad i en rebase. Normaliserat
före commit; se global `MEMORY.md`.

### Det som INTE är löst, och som blev tydligare i kväll

**Pausen från 2026-08-24 kväll är hävd, utan att åtgärdslistan i `docs/JURIDIK_ATGARDER.md`
P0.1c genomfördes.** Den kvällen pausades `main` uttryckligen till simuleringsläge:
gratisnivåns Gemini-avtal tillåter Google att använda kunddata för produktförbättring,
och riktiga kundmejl gick dit. Fyra åtgärder listades innan pausen skulle hävas:
bekräfta nivån, aktivera fakturering eller byt provider, skaffa en EGEN nyckel per miljö,
teckna DPA.

Mätt i kväll: **både `main` och `development` svarar `mode: live`.** Samma
`GEMINI_API_KEY` delas fortfarande mellan miljöerna. Kvoten är fortfarande FreeTier
(`GenerateRequestsPerMinutePerProjectPerModel-FreeTier` triggas efter 6 anrop/minut —
en betald nivå har inte den kvotklassen). Ingen av de fyra åtgärderna är genomförd.
Ingen av `JURIDIK_ATGARDER.md`, det här dokumentet, eller integritetspolicyn uppdaterades
när pausen hävdes. Riktiga kundmejl går just nu till gratisnivån igen — precis det
pausen fanns för att förhindra. Spårat som `snipe-a1c` (P0). Flaggat till Anton direkt,
inte bara här.

**`main` ligger ~80 commits efter `development`** och saknar migration 043–049.
`snipe-zfc`.

## 2026-08-24 — Claude — produktionen pausad, Render tystad, Gemini-frågan avgjord

**Gemini-nyckeln ÄR gratisnivån.** Inga indicier kvar — Googles eget kvotfel namnger den:
`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, 20 anrop per dygn per projekt och modell.
Dagens demo-anrop åt upp hela ransonen för båda miljöerna, som delar nyckel.

**Produktionen är pausad till simuleringsläge.** Efter hotfixen svarade den 429 på VARJE anrop
och skickade kunddata till en nivå vars villkor tillåter träning — sämre på båda axlarna än
läget innan. Nu: `mode: simulation`, regelmotorn svarar, ingenting går till någon leverantör.
Verifierat med ett riktigt anrop. Ångras med `llm_provider.py --env main --satt gemini --apply`.

`--pausa` är byggt som en flagga och inte ett engångskommando, eftersom det är något man vill
kunna göra om och backa.

**Render-tjänsterna är tystade men inte avstängda.** DEEPSEEK_API_KEY blankad på båda; båda
rapporterar SIMULERINGSLÄGE i uppstartsloggen. Render-verktyget saknar suspend och Chrome-
tillägget är inte anslutet, så själva avstängningen är ett handgrepp i dashboarden.

**Kvotfel ser inte längre ut som en krasch** — 429 med begriplig text i stället för
"Något gick fel på vår sida", som är samma svar som ett nullpointerfel gav.

## 2026-08-24 — Claude — Gemini-nyckeln är på gratisnivån, och båda miljöerna delar den

Sista verifieringen av maskeringen föll — men på något annat än maskeringen:

    openai.RateLimitError: 429 "You exceeded your current quota, please check
    your plan and billing details."

Det är gratisnivåns signatur. Ett fakturerat Gemini-projekt slår inte i kvoten på en handfull
anrop en kväll, och det stämmer med vad kodbasen själv säger om nyckeln ("vald för
gratisnivån"). Indicier, inte ett kontoutdrag — men planera inte som om det vore något annat.

**Juridiskt** tillåter gratisnivån Google att använda innehållet för produktförbättring, och
riktiga kundmejl går dit sedan produktionen lagades i kväll. Till skillnad från DeepSeek-läget,
där grunden saknades för en överföring, har vi här aktivt lämnat bort innehållet.

**Operativt** kommer produktionen att svara 429 under all verklig belastning.

**Och nyckeln är SAMMA i main och development**, alltså samma kvot: en provkörning i dev kan ta
ner produktionen. Repot varnar redan för mönstret — `PER_ENV_SECRETS` i railway_provision.py
kallar en delad hemlighet "tyst korskoppling". GEMINI_API_KEY står inte i den listan och borde.

Övervägande värt att ta: pausa den skarpa trafiken tills nivån är bytt. Produktionen körde
simuleringsläge fram till i kväll och har klarat sig utan agenten hittills.

## 2026-08-24 — Claude — Render-stacken var inte död, och min spärr missade den

**Två Render-tjänster låg kvar levande och startade med `provider=deepseek` mot en riktig
Postgres.** `snajp-support` (gren `main`) och `snajp-support-dev` (gren `development`), båda med
autoDeploy — varje push till våra grenar deployade dit, inklusive dagens. DeepSeek-överföringen
som stoppades på Railway i dag var alltså aldrig stoppad överallt.

Ytan fanns inte i någon dokumentation, inte i registerförteckningen, och inte i min egen
bedömning. Den hittades genom att incidentposten om den läckta Render-nyckeln skulle bedömas —
frågan "vad nådde nyckeln?" ledde rakt till den.

**Min spärr fångade den inte, och det var ett designfel.** `har_riktig_kunddata()` grindade på
miljönamnet med motiveringen att "Railway sätter alltid RAILWAY_ENVIRONMENT_NAME". Sant, och
ändå fel: det antog att Railway är den enda värden. På Render var namnet tomt, så spärren läste
det som utveckling och släppte igenom. Grenen som skulle skydda en lokal körning skyddade i
stället en bortglömd produktionsyta från att bli upptäckt.

Regeln keyar nu på DATABASEN: en fjärrdatabas betyder riktig data oavsett värd. Loopback är
undantaget, eftersom `lokal_stack.py` kör där och den stacken är tom. Undantaget gäller
adressen, inte en flagga någon kan sätta — en flagga hade blivit satt.

Tjänsterna är INTE avstängda av mig; det är utåtriktat och Antons beslut. Se
`docs/JURIDIK_ATGARDER.md`, P0.2b, och två nya poster i incidentloggen.

## 2026-08-24 — Claude — produktionen lagad med en hotfix, dev-spegeln av-indexerad

**Produktionen svarade riktiga kunder med regelmotorn.** `LLM_PROVIDER=gemini` mot kod som
inte kände till värdet gav en tom nyckel, och en tom nyckel är simuleringsläge. Hälsokontrollen
sa `status: ok` hela tiden — ordet som avslöjade det var "simulation" i ett fält ingen larmar på.

Rättat med en KIRURGISK hotfix på `railway-main` (78c900e, 39 rader), inte en full merge.
Produktionen deployar från `railway-main`, inte från `main` — den senare är den döda
Vercel-grenen och ligger 151 commits efter. Skillnaden till development var 37 commits, och att
skicka alla för att laga en tom nyckel hade varit fel växling. Produktionen bär nu rättningen
men INTE spärrarna, de juridiska sidorna eller avregistreringen.

**Dev-spegeln låg fritt indexerbar.** Ingen robots.txt, ingen X-Robots-Tag — en fullständig
kopia av säljsajten med en inloggning till riktig kunddata. Vercels SSO täckte det förut.
Stängt med `app/robots.ts` och en noindex-tagg, båda styrda av `lib/miljo.ts`, som läser
RAILWAY_ENVIRONMENT_NAME och inte NODE_ENV — den senare är "production" i BÅDA miljöerna.
Appens egen grind mättes samtidigt och håller.

**Två buggar hittades genom att köra skarpt**, inga tester fångade dem: avregistreringen reste
ett undantag för en tenant utan arbetsyta, och `add_suppression` skrev tyst noll rader i samma
läge. Migration 049. Kedjan är nu klickad hela vägen på development.

DPIA och intresseavvägning skrivna som utkast. DPIA:ns R1 — okontrollerat kundinnehåll till
modelleverantören — är blockerad av att Geminis avtalsnivå inte är fastställd, och kan inte
stängas i kod.

## 2026-08-24 — Claude — modellnamnet följde inte med providerbytet

Fortsättning på posten nedan, och en påminnelse om att `mode: live` inte är ett bevis.

`MODEL` stod kvar på `deepseek-v4-flash` när LLM_PROVIDER byttes till `gemini`. Omskrivningen
i `_default_model_for_provider` utlöses bara när MODEL lämnats på gpt-defaulten, så ett namn
satt för hand gick rakt igenom. Development startade, hälsokontrollen sa `mode: live`, och
varje anrop svarade `404 models/deepseek-v4-flash is not found`. Hälsokontrollen mäter att en
NYCKEL finns — aldrig att modellen existerar hos den provider nyckeln pekar på.

Nu fäller ett modellnamn från fel familj uppstarten, med 404-orsaken utskriven i
felmeddelandet. Okända namn släpps fortfarande igenom: leverantörerna döper nya modeller utan
att fråga oss, och en för snäv lista blir bortkommenterad.

**Produktionen kör simuleringsläge.** `main` ligger på kod från 23 augusti som inte känner
till `gemini`, faller till den tomma OpenAI-nyckeln, och svarar riktiga kunder med regelmotorn
i stället för med agenten. Det kräver både rättade variabler och en deploy av main — se
`docs/JURIDIK_ATGARDER.md`, P0.1d. Development är åtgärdad och verifierad med ett riktigt
anrop, inte bara med hälsokontrollen.

## 2026-08-24 — Claude — Gemini kopplad som chattprovider, och tystnaden stängd

`LLM_PROVIDER=gemini` sattes för hand i båda Railway-miljöerna. DeepSeek är därmed borta —
men `gemini` var inget värde koden kände till. `active_llm_key` slutade med
`return self.openai_api_key`, så VARJE okänt providernamn gav en tom nyckel, och en tom
nyckel är simuleringsläge. Development svarade `mode: simulation` med regelmotorn i stället
för agenten. Deployen gick igenom. Ingenting larmade.

Tre ändringar: Gemini är nu en riktig chattprovider (nyckel, endpoint, modellnamn — samma
som vision-sidovagnen redan använder mot samma endpoint). Okända providernamn fäller
uppstarten i stället för att degradera tyst. Och `scripts/llm_provider.py` frågar numera
"har den här tjänsten rätt nyckel för det den påstår sig köra?" i stället för att leta efter
just OpenAI — det var den frågan som inte ställdes.

**Kvar och brådskande (P0.1c):** nyckeln är den kodbasen själv beskriver som vald för
GRATISNIVÅN. Gratisnivåer tillåter typiskt leverantören att använda innehållet för
produktförbättring, och går det på kunddata är det värre än DeepSeek var. Påståendet i
integritetspolicyn om att leverantören "inte tränar på texten" är borttaget tills någon
läst avtalet — ett löfte i en integritetspolicy är bindande.

## 2026-08-24 — Claude — GDPR: DeepSeek utspärrad, juridiska sidor, gallring och rättighetsflöde

**DeepSeek får inte längre se kunddata.** `LLM_PROVIDER=deepseek` fäller uppstarten i `main`
och `development` (spegelmiljön räknas — den bär riktiga kunders ärenden). Spärren ligger i
`Settings.llm_provider_fault()`, körs från `app/main.py` före databasen och från
`agent/llm.py` vid klientbygget. Motivet står i CLAUDE.md så att nästa session inte vänder
tillbaka det av kostnadsskäl. **Läst ur Railway efteråt: BÅDE main och development kör `LLM_PROVIDER=deepseek`, och
ingen miljö har en `OPENAI_API_KEY`.** Produktionen skickar alltså riktiga kundmejl till
DeepSeek i skrivande stund, och providern går inte att vända förrän en nyckel finns —
utan nyckel startar tjänsten i simuleringsläge, vilket är ett fel som inte larmar.
Deployen av den här commiten till development föll som avsett på spärren; Railway lät
den gamla versionen ligga kvar. `python scripts/llm_provider.py` visar läget, `--apply`
byter provider men vägrar göra det utan nyckel. Se `docs/JURIDIK_ATGARDER.md`, P0.1b.

**Tre juridiska sidor finns**: `/integritetspolicy`, `/villkor`, `/cookies`, med en delad
sidfot som bär bolagsidentifikation. Alla texter är förstautkast och bär en synlig
"Förstautkast"-ruta tills en jurist läst dem. Bolagsuppgifterna i `lib/bolag.ts` är
platshållare med flit — ett gissat organisationsnummer kan tillhöra ett annat bolag.

**Marknadstexten sa inte hela sanningen.** Dataskyddsstycket lovade att ingenting delas mellan
kunder men nämnde inte att mejltexten skickas till en AI-leverantör. Den säger det nu, och är
mer specifik i stället för mer försiktig.

**Art. 14-sidfoten byggs numera i KOD, inte av modellen.** `send_guard` har blockerat utskick
utan avsändaridentifikation och avregistreringslänk sedan Del 2.3 — men ingenting LADE DIT
dem. Det gör `app/leads/utskicksfot.py` nu, vid köning, så att texten en människa granskar är
texten som skickas. Avregistreringslänken fungerar hela vägen: ogenomskinlig token i
`ss_avregistreringslankar`, inlöst via en security definer-funktion på
`/avregistrera/[token]`.

**Gallring och rättighetsflöde finns som skript, inte som instruktioner**: `scripts/gallra.py`
(torrkörning som default) och `scripts/gdpr_radera.py` (sök, registerutdrag, radering).
Retentionsperioden är MEDVETET inte satt — det är ett affärsbeslut, och ingen policy betyder
ingen gallring.

**Migration 046 och 048 är skrivna men inte körda.** Avregistreringssidan och gallringen gör
ingenting förrän de är applicerade.

Öppen post i incidentloggen: den läckta Render-nyckeln. Se `INCIDENT_RESPONSE.md`.


## 2026-08-16 — Claude — Plattformen färdig, preview-miljö byggd, riktningsbyte mot enad stack

**Alla sju faser i plattformsplanen är byggda och committade.** Fas 1.3–1.5 (RPC-härdning,
DB-baserad rate limiting, INV-SEC-010), Fas 2 (plattformsadmin, glömt lösenord, OAuth,
inbjudningar), Fas 3 (fail-closed entitlements, tillägg, navrensning), Fas 4 (autonominivå,
ICP, körkontroller), Fas 6 (admin master control, notiscenter, spårvy). 454 backend-tester och
47 invarianter gröna.

**Migration 018–029 körda och verifierade i produktion.** Blockeraren är löst: `agent_runs`
avvisade varje leads-körning i ett halvår, och `MemoryStorage` saknade villkoret så testerna
var gröna. Två RLS-buggar hittades först vid skarp körning som `snajp_app`:

- **028** — `current_setting('app.tenant_id', true)` blir `''`, aldrig NULL, efter första
  skopade transaktionen på en poolad anslutning. Varje senare oskopad fråga kastade `''::uuid`.
- **029** — 028 stoppade kraschen men inte TYSTNADEN: adminvyn gav 0 körningar av 10, och
  kundöversikten fyra kunder med nollställda tal. Trovärdiga men felaktiga siffror.

**Preview-miljön fungerar.** Push till `development` ger Vercel Preview, Render
`snajp-support-dev` och en Supabase-gren som är en full spegel av produktionen (`--with-data`,
Antons beslut — konsekvensen är kunddata i preview, dokumenterat i `CLAUDE.md`).

**Nio buggar som bara verklig körning avslöjade**, bland dem tre kolumnbuggar i SQL som aldrig
exekverats, `scheduler.py` som hade adresserat mejl till strängen "okänd", migrationskedjan som
inte var självbärande, och `INV-DEPLOY-001` som blev blind när en andra tjänst lades till.

**Två misstag jag gjorde:** raderade två produktionsvariabler i Vercel (`env rm` tar hela
posten när den delas mellan scope — återställda, spärr inbyggd), och läckte Render-API-nyckeln
i transkriptet under felsökning. **Rotera den.**

**Riktningsbyte:** upplägget kostade åtta separata infrastrukturfällor att få på plats. Anton
vill utvärdera en enad Railway-stack. Plan skriven; kartläggningen visar att beroendet till
Supabase går genom två strupar — `current_workspace_id()` (15 av 17 policyer) och
`getWorkspaceContext()` (9 av 11 filer). Neon kvar som fallback.

**Grenar:** `feature/plattform-fas1-7` är FRYST säkerhetskopia av allt detta.
`feature/railway-stack` är arbetsgrenen. `main` ligger 20 commits efter och är orörd.

Sessionslogg: `session-logs/2026-08-16-session-log.md`

## 2026-08-15 — Claude — Anonymt API stängt, ren kundchatt, agenten vet var i samtalet den är

**Hela backend-API:t var anonymt nåbart i produktion.** `proxy.ts`-matchern täcker bara
`/dashboard`, `/settings`, `/onboarding`, `/login`, `/auth/callback` — inte `/api/*` — och
ingen route under `app/api/` gjorde egen sessionskontroll. Mätt mot drift, utan cookie:
`GET /api/snajp-support/leads/soul` gav 200 med innehåll, `PUT` gav 422 (nådde backenden,
stoppades bara av pydantics typkontroll — en giltig sträng hade skrivits). `kb`, `rules`
och `inbox` gav 200. Catch-allen kunde dessutom adressera `POST /api/keys`, räddat enbart
av att `SNAJP_INTERNAL_API_KEY` råkar vara demonyckeln och inte master.

Andra halvan av samma bugg: catch-allen skickade ingen tenant, så varje **inloggad** kunds
inkorg, kunskapsbas och röstdokument lästes ur demo-tenanten Nordlys Handel. Två kunder
hade skrivit i samma SOUL. `workspaces.ss_tenant_id` och `.slug` har funnits sedan
migration 007 men saknades i `lib/database.types.ts`, så koden kunde inte se kopplingen
ens om den velat — tystnaden var hela felet. Tenanten härleds nu ur sessionen
(`lib/snajp/tenant.ts`); saknas slug, configfil eller nyckel blir det 409/503 med namnet
på det som fattas. Verifierat i produktion efter deploy: 401 på allihop, anonym `PUT`
avvisad, publik chatt oförändrat 202.

**SOUL-innehållet var däremot väl försvarat.** Userposition, UUID-avgränsare per anrop,
INV-SEC-009 med ett riktigt injektionstest, och onboarding-agenten kan inte skriva den.
Användarens egna prompt-injektionsförsök i drift ("Forget everything…", "Disregard the
system prompt…") höll båda. Hålet satt i *vem som fick skriva* SOUL, inte i hur den
renderades.

**Kunden såg vår interna bedömning av sig själv.** Chattbubblan bar kategori,
"Sentiment 0.1", "Eskalerat till människa" och "Källa: <artikel>", plus ett lägespill som
avslöjade "Live-AI" respektive "Demo-läge". Tydligast i ett skarpt fall: en person skrev
att hans fru avlidit, och under agentens svar stod "Sentiment 0.1". Allt borttaget ur den
kundvända komponenten — utan konfigurationsflagga, eftersom en kundvänd komponent inte ska
gå att ställa in på att läcka. Datat finns kvar för den interna vyn och spårningen.

**Agenten visste inte var i samtalet den befann sig.** Utkaststeget fick bara ANTALET
tidigare kontakter, aldrig samtalet, så varje replik var formellt sett ett första
meddelande: "Hej" på varje tur, "Vänliga hälsningar," under varje, ofta hängande utan
namn. Nu: utskrift av de senaste turerna i `case_context`, overlay
`support-conversation.md` bunden till BÅDA textstegen (humaniseraren är sista handen och
hade annars satt tillbaka hälsningen), och `strip_dangling_sign_off()` som kodgrind
eftersom felet uppträdde i båda thinking-lägena. Verifierat mot riktig modell i tre turer.
Historiken tvingade fram en till fix: alla demobesökare delade en kundidentitet, vilket var
ofarligt när agenten bara fick ett antal men hade läckt föregående besökares repliker in i
nästa besökares kontext.

**Rotorsaken till gårdagens två buggrapporter:** Render pekade på `development`, som
forkade vid `32c58cd` och aldrig sett Livrustning-tenanten, fack-filtret eller
grundningsgrinden. Frontenden deployade från `main`. Docker-bygget failade sedan på
`"/agent-core": not found` — Root Directory stod kvar på `snajp-support`, så `agent-core/`
låg utanför byggkontexten. Båda åtgärdade av användaren. Den överflödiga Render-tjänsten
`snipe-leads` raderad; leads-agenten kör i samma FastAPI-app som supporten.

**Öppet:** Fas 1 till hälften — RPC-härdning (018), rate limiting (019), INV-SEC-010 ·
Fas 2/3/4/6 opåbörjade · **`agent_runs.agent_type` avvisar det koden skriver, så ingen
leads-körning har någonsin sparats i produktion** (blockerar admin-spårvyn) ·
`SNAJP_KEY_LIVRUSTNING` osatt på Vercel · `snajp_app`-rollens lösenord fortfarande osatt.
Plan: [plans/2026-08-15-plattformsplan.md](plans/2026-08-15-plattformsplan.md).

## 2026-08-14 — Claude — Grundningsgrind, skill-lås, tre-lagers instruktionssystem, DB-spegel

**Den öppna tråden från 2026-08-10 är stängd.** Sportamore-incidenten (AV-utkastet påstod
"minskat återkommande frågor med 30 procent" mot ett kontextpaket utan en enda procentsiffra)
har nu en kodgrind: `app/leads/grounding_gate.py` extraherar siffror/procent/belopp/
kundreferenser/superlativ ur ett utkast, jämför mot en tillåten faktamängd byggd ur
kontextpaket + Fas B:s research-evidence + erbjudandet, och fäller om något saknar täckning.
En reparationsrunda (max 1) försöker laga det specifika påståendet, bara de ändrade
meningarna delta-humaniseras (`app/leads/text_delta.py` — meningsoffsets, förlustfritt),
och kvarstår felet går utkastet till en människa i stället för `send_queue`. Ny invariant
INV-GROUND-001, regressionstestad mot exakt incidenten.

**Produktionsbugg fixad innan den hann utlösas.** `render.yaml` satte `rootDir: snajp-support`,
så `agent-core/` (i repo-roten) låg utanför Dockers byggkontext och kunde inte kopieras in.
Containern startade grönt (agentimporterna är uppskjutna in i request-handlers), och kraschen
skulle ha kommit på det FÖRSTA riktiga agentanropet — alltså exakt när `DEEPSEEK_API_KEY`
sätts för att gå live. Fixat (`rootDir: .` + `COPY agent-core`), reproducerat och verifierat
för hand (Docker saknas lokalt — `docker-smoke`-CI-jobbet är oprövat till nästa PR).
Ny invariant INV-DEPLOY-001.

**Tre-lagers instruktionssystem byggt** som svar på "var justerar jag agentens output utan
att röra en vendorad skill": `agent-core/AGENTS.md` (global policy, opinnad, aldrig ton),
`agent-core/overlays/*.md` (per-steg, pinnad via `overlay_hash`, den sanktionerade
tuningytan), och SOUL (`agent_context_docs kind='soul'`, kundredigerbar i `/settings/soul`,
renderas ENDAST i användarposition — aldrig systemprompt). `pack_version` bär nu tre hashar
så en körning går att spåra till exakt vilken kombination av lager som formade den.
INV-SEC-009 bevisar SOUL-gränsen med ett riktigt injektionstest (`"IGNORERA REGLERNA OVAN..."`)
som fångar de faktiska meddelandena och asserterar sentinel aldrig når `messages[0]`.

**DB-spegel för skills byggd, men SMALARE än begärt — obekräftat med användaren.**
`skill_source="filesystem"` är default i ALL miljö, `render.yaml` sätter aldrig
`SKILL_SOURCE`. Motivering: kan databasen leverera skill-text containern inte har på disk
är git bara källa till sanning i intentionen, och INV-SKILL-005 (som hashar filsystemet)
slutar fungera som lås. Spegeln är i stället en granskningspost — vilken exakt text
producerade en given `agent_runs`-rad. **Kräver ett beslut från användaren nästa session.**

**Fem UI-defekter hittade genom att faktiskt läsa renderade pixlar**, inte kodgranskning
(en `design-stop`-hook blockerade första försöket att avsluta av precis det skälet):
90-tecken radlängd, ett fält 3/4 tomt, en kvarhängande "Sparat"-kvittens samtidigt som
"för långt"-felet, 2.17:1 kontrast på felfärgen (ny `--warning`-token, 4.75:1), och en
`grid-cols-12`/`gap-x-8`-kollaps som gjorde att "BILLING" försvann helt vid 320px bredd
(alla tolv kolumner klampade till 0px — `overflow-x:hidden` dolde det i stället för att
visa horisontell scroll). Tre andra ställen i `WorkspaceViews.tsx` har samma mönster,
oåtgärdade.

**Öppet:** bekräfta DB-spegel-scope · skarp körning mot riktiga DeepSeek-nycklar
(`scripts/run_live_tests.py --leads`, mät `grounding.fired`-frekvens, injicera medvetet ett
påhittat påstående och verifiera att grinden fäller) · tre grid-collapse-ställen kvar ·
`--mineral`/`--danger` under AA (4.4:1) repo-brett.

### 2026-08-14 (forts.) — `main` fast-forwardad till produktion, på användarens explicita instruktion

**`main` låg fryst på `a10d919` sedan 2026-05-24** (avsiktligt beslut 2026-07-28: `snipra.vercel.app`
skulle INTE röras medan redesignen pågick på `snajp-redesign`). Användaren instruerade explicit,
två gånger i den här sessionen, att pusha allt till `main`. Verifierat innan push: `main` hade **0
commits `snajp-redesign` saknade** — en ren fast-forward, inga konflikter att lösa på den fronten.

`git push origin snajp-redesign:main` — `a10d919..858b533`, 45 commits på en gång. Blockerades
först av auto-mode-klassificeraren (produktionspush är en egen skyddsgrind); användaren godkände
explicit, pushen kördes om och lyckades.

**Detta utlöste en RIKTIG produktionsdeploy** (`.github/workflows/deploy-production.yml` triggar
på push till `main`, `vercel.json` har `git.deploymentEnabled: true`). Verifierat via `gh run list`
och pollning till slutfört: **`Deploy — Production` lyckades**, och **`snipra.vercel.app` är nu
aliaserat till den nya deployen** (`https://snipra-76rq0l4x3-olofluns-projects.vercel.app`) —
2026-07-28-frysningen är alltså medvetet upphävd. `Verify`-workflowet kördes samtidigt och blev
grönt, inklusive **`docker-smoke`-jobbet på riktigt** (INV-DEPLOY-001 var tidigare bara verifierad
genom en handbyggd containersimulering lokalt — nu bekräftad i skarp CI).

**Render (backend) påverkas INTE av den här pushen** — `render.yaml` har ingen branch-inställning,
Render styrs av sin egen dashboard-konfiguration (historiskt `development`, inte `main`). Skills
och grundningsgrinden finns alltså på produktionsFRONTENDEN nu, men backend-agenten som faktiskt
kör dem är oförändrad tills en separat Render-deploy görs.

**En utförlig handoff till Sebbe skriven:** [HANDOFF-2026-08-14-SEBBE.md](HANDOFF-2026-08-14-SEBBE.md)
— täcker sammanslagningskonflikten i `_lib.ts` (hans kallstart-retry-logik + den nyare per-tenant-
nyckelhämtningen, komponerade för hand, inte en av-sidorna-vinner-lösning), samt alla öppna punkter.

## 2026-08-10 — Claude — Leads migrerad till per-steg, thinking BESLUTAT AV, skill-grind mekaniserad

**Leads-agenten kör per-steg.** `leads_agent.py`s tre `Runner.run`-anrop ersattes
med `step_runner.run_step` — Fas B (8 steg) och Fas C (4 steg), ett LLM-anrop per
skill. Det var förkravet för att `THINKING_MODE` överhuvudtaget skulle nå
API-anropet; utan det mätte 2026-08-08 års jämförelse ingenting. Skrapningen och
köningen av utkast flyttades till kod: G4 och INV-SEC-004 blir kodvägar i stället
för hopp om att modellen anropar rätt verktyg. **Fas A (onboarding) kör medvetet
kvar på `Runner.run`** — flerturssamtal passar inte per-steg-kontrakt, och den
saknar därför fortfarande thinking-kontroll och `step_log`. Det är en kvarvarande
lucka, inte klart.

**BESLUT: thinking HELT AV i leadsflödet.** Användarens beslut efter genomläsning
av rådatan från 72 skarpa anrop (3 bolag × 2 lägen × 12 steg). **Beslutet
underkände min rekommendation, som var PÅ** — jag drog slutsatser ur mätvärden
(PÅ bröt utdatakontraktet noll gånger mot AV:s sex, differentierade sina
konfidenssiffror), användaren läste vad modellen faktiskt producerade. Där var AV
bättre: personligare utkast med rätt ton, medan PÅ blev hackigt och robotaktigt
trots övertänkandet. AV hade dessutom **rätt** om att B2C passar supportprodukten;
PÅ:s underkännande av alla tre bolagen var pessimism, inte skärpa. Beslutet är
pinnat explicit per steg (`research_playbook.THINKING`), inte ärvt från
`settings.thinking_mode`, och låst av två tester. Se
`docs/THINKING_MODE_COMPARISON.md` §8.5 för hela resonemanget inklusive varför
min slutsats var fel.

**HÅRD REGEL, nu mekaniskt tvingad: skillsen ändras aldrig.** INV-SKILL-005
(`tests/invariants/test_inv_skill_005.py`) jämför varje fil under
`agent-core/skills/` mot sitt sha256 i manifestet och fäller builden på tyst
redigering, tillagd eller borttagen fil. Verifierad genom att faktiskt ändra
`mk:offers`, se testet fälla, och återställa. Justering av output sker i stället
med **tilläggsinstruktioner** i playbookens `task`/`case_context` — det spåret
utvärderas i kommande tester (§8.6).

**Tre buggar som körningen avslöjade, två åtgärdade:**
1. ScrapeGraphAI returnerar `markdown.data` som **lista**, inte sträng → längden
   rapporterades som 1 i stället för ~4 000, och sidan injicerades som listrepr
   med literala `\n`. Fixad (`_as_markdown`). Testmocken antog sträng — samma
   felklass som `MemoryStorage.search_kb` förra sessionen.
2. Hängande signatur i 5/6 utkast: modellen skrev `[Signatur]`,
   platshållargrinden tog bort den (rätt) och lämnade "Med vänliga hälsningar,"
   naket. Fixad (`sign_off`).
3. **EJ ÅTGÄRDAD — påhittad statistik i ett kundvänt utkast.** AV-utkastet till
   Sportamore påstod "minskat sina återkommande frågor med 30 procent inom 30
   dagar"; kontextpaketet innehåller noll procentsiffror. Ingen kodgrind fångar
   ogrundade påståenden i dag. **Detta är den högsta prioriteten nästa session.**

**Avslöjandebuggen inverterad (efter sessionens slut).** Sektioner på `/leads`
renderade som rubrik med tomt under — andra gången samma felklass. Orsaken var
inte en trasig vakt: alla tre vakterna (`threshold: 0`, guard-2, 1200 ms-
failsafe) var deployade och verifierade. Problemet var **riktningen**: CSS gav
`.rise` `opacity: 0` som grundtillstånd, så synlighet krävde att JS lyckades,
och varje element hooken missade blev osynligt för alltid.

Nu döljer CSS bara `.rise` medan `<html>` bär `reveal-armed` — en klass
`useReveal` sätter före första paint och äger. Kör hooken inte alls (ingen JS,
blockerad JS, route utan hooken, undantag vid mount) är sidan fullt läsbar utan
animation. Dessutom fångar en `MutationObserver` noder som tillkommer efter
mount, och deadlinen är per nod i stället för en engångstimer över en snapshot.
`<noscript>`-overriden i `layout.tsx` togs bort — den är död kod nu, och död kod
som ser bärande ut är vad nästa person snubblar på.

`scripts/check_reveal.py` mäter nu **computed opacity** i stället för klassen
`is-visible` (klassen är inte längre det som avgör synlighet), och har ett
fjärde läge som tar bort `reveal-armed` och kräver att allt ändå syns.
Verifierat att checken FÄLLER mot den gamla CSS:en och passerar mot den nya —
en check som inte kan fela är ingen check. Sveptes över 320/375/414/768/1440 ×
3 sidor: inga dolda element, ingen horisontell scroll. Skärmdumpar lästa.

**Öppet:** grundningsgrind mot påhittade påståenden · Fas A-migrering ·
utvärdering av tilläggsinstruktioner · `DATABASE_URL` fortfarande osatt
(pgvector-vägen overifierad, `snajp_app`-lösenordet aldrig satt) · död kod från
första passet · edge-function-stubbar · `BLOCKS.md` 7 060 tecken mot 3 000 i tak.

## 2026-08-08 — Claude — Agent-backend implementerad, live-testad, kritiska luckor hittade och täppta

**Hela DeepSeek v4 Flash-planen implementerad** efter godkännande (`/goal`-invokering
räknades som godkännande, tre `ExitPlanMode`-avslag var för ren kontext, inte
invändning). Full teknisk status: [HANDOFF.md](HANDOFF.md) — läs den, inte denna
rad, för detaljer. Plan: `plans/2026-08-07-agent-backend-deepseek.md`.

**Användarens skepsis efter en första "15/15 klart"-rapport var befogad.** Allt var
enhetstestat, nästan inget var kopplat till en riktig kodväg — `agent_runs`
skrevs aldrig, leads-pipelinen saknade ett sätt att skapa ett prospekt,
läsgarantin (`check_output_contract`) anropades aldrig live. Rättat: supportagenten
byggdes om från EN hopklistrad agentloop-prompt till ETT LLM-anrop per skill-steg
(`app/agent/step_runner.py`) — den mekanism som gör läsgarantin faktiskt verifierbar.

**Live-testat mot riktiga DeepSeek/ScrapeGraphAI-nycklar.** 66 skarpa anrop i
supportflödet (`docs/THINKING_MODE_COMPARISON.md`), hittade och fixade en
kundvänd bugg (`[Your name]`-mallrester i 3/10 svar). **Beslut:** thinking AV
i support (identiska beslut i båda lägen, 11x fler tokens/6x latens PÅ),
UTOM `cs:customer-escalation` (thinking PÅ, medvetet).

**Leads-jämförelsen kördes — och är OGILTIG.** 12 körningar lyckades tekniskt,
men `THINKING_MODE` hade noll effekt: `leads_agent.py` kör `Runner.run`
(Agents SDK-loopen) och rör aldrig `step_runner.run_step`. Alltså inga
`reasoning_tokens`, inget `step_log`, ingen `agent_runs`-loggning, inget
utdatakontrakt per steg. **Leads har samma arkitekturfel som support hade före
omskrivningen.** Upptäckt genom att latenserna var identiska mellan lägena där
support visade 6× skillnad. Leads måste migreras till per-steg-körning innan
någon jämförelse betyder något — se `docs/THINKING_MODE_COMPARISON.md` §6.

**Vision + embeddings bytt OpenAI → Gemini** (gratisnivå, användarens uttryckliga
önskan). Ny generaliserad skill `~/.agents/skills/api-key-setup/` byggd från
sessionens nyckel-friktion.

**Öppet:** `DATABASE_URL` inte satt lokalt → KB-sökning bara testad mot
`MemoryStorage` (ignorerar embeddings helt, ren tokenmatchning) — den riktiga
pgvector-vägen overifierad. `snajp_app`-rollens lösenord är inte satt
(`execute_sql` blockerad av miljöns klassificerare, se `BLOCKS.md`).
`discover-leads`/`generate-outreach` edge functions fortfarande orörda stubbar.

## 2026-08-07 — Claude — Auth fixat, Livrustning live (chat-only), agent-backend-plan under granskning

**Registrering med privat mailadress fungerar.** Grundorsaken var en trigger som
kunde misslyckas tyst och lämna en `auth.users`-rad utan profil — inte
mailleverantören. Migration 006 gör triggern självläkande
(`ensure_workspace_for_user()`, sväljer sina egna fel) och lägger till
`workspace_invites` för invite-only-flöden. `proxy.ts` hade dessutom en tyst bugg:
`proxyConfig` (fel exportnamn) gjorde att matchern aldrig applicerades, så varje
anonym sidladdning körde ett Supabase-anrop. Verifierat i dev-loggen, fixat till
`config`. Se `AUTH.md`.

**Livrustning AB är live som tenant på `livrustning.snajp.se`.** Byggdes först som
fem statiska sidor (Om oss, Villkor, Garanti, Integritetspolicy, Kontakt) —
**rivet igen efter uttrycklig rättning**: Snajp bygger inte om kundens hemsida,
bara supportchatten. `/chat/livrustning` är den enda ytan, med kundens logga
("Powered by Snajp") och en riktig kunskapsbas (22 artiklar, sourcead från alla
sex sidor på livrustning.se, inte bara startsidan). En tenant-isoleringsgenomgång
hittade att Snajps egna marknadsföringssidor (`/`, `/leads`, `/support`,
`/design-drafts`) läckte igenom på kundens domän — täppt med en enda
`notFoundOnTenant()`-vakt. Se `TENANTS.md` för onboarding-rutinen till nästa kund.

**Öppen fråga hos kunden, inte hos oss:** vilken garanti gäller för en lös
hjärtstartare — 1 år (deras villkor) eller 8 år (Hjärtsäker zon-bundlens copy på
livrustning.se)? Agenten eskalerar tills Livrustning bekräftat. Inget annat
blockerar deploy förutom att sätta `SNAJP_KEY_LIVRUSTNING` och
`IMAP_PASSWORD_LIVRUSTNING` i Vercel.

**Ny arkitekturplan (DeepSeek v4 Flash agent-backend) är INTE godkänd.** Läst
varenda skill i den begärda kedjan ordagrant, inte bara beskrivningarna — hittade
och rättade två felval (`competitors` istället för `competitor-profiling`,
`revops` som lät rätt men innehöll fel sak) samt att repot helt saknar test-CI.
Planen ligger kvar i `.claude/plans/hej-f-rfina-denna-plan-dreamy-yao.md` och en
statussammanfattning i `plans/2026-08-07-agent-backend-deepseek.md`. **Ingen kod
skriven än — invänta explicit godkännande innan implementation påbörjas.**

## 2026-08-02 — Claude — Merget till main, alla trådar utom Alunix stängda, två tysta länkfel

**`super-intelligence` 0.4.5 merget till `main` och pushat.** Fast-forward, gjord utan
utcheckning eftersom 22 ospårade impeccable v3-filer blockerade den — `git push
origin design-system-v2:main` gav samma resultat utan att röra arbetsträdet.
Installer-wiringen klar: registreringstabellen 6 → 8 poster plus **matcheravstämning**,
för den gamla mergen frågade bara "finns skriptet?" och hade lämnat den breddade
`design-verify-gate`-matchern på sitt gamla värde hos alla befintliga installationer.
Testad mot en simulerad 0.4.4: 6 ändringar första passet, 0 andra, orelaterat
`carl-hook.py` orört.

**Trådar stängda:** `gbrain` (felet var scope, inte trasig installation — `sync` utan
argument riktar sig mot en federerad källa utan sökväg), `.next` i Klova och
`.impeccable` i snipe-leads avspårade, `alunix` canon och `alunix-site` raderad efter
verifiering (bygget rent, 104 `.shots`-filer kopierade som klonen missat).

**`/conclude` byggdes om** — mekaniska halvan kör parallellt i
`.agents/scripts/conclude-finalize.py`, startad i bakgrunden. Mätt: 3 min 54 s mot
uppskattade 12–14 innan. Inget steg togs bort.

### Två tysta länkfel, samma orsak
En arbetsgranskning avslöjade att **`~/vault-local` är död** (WSL-arv) men fem skills
skrev fortfarande dit — separat katalog på disk, nådd bara av ett fördröjt jobb.
Åtgärdat, CARL GLOBAL-regel 10.

Och **`~/STATUS.md` är ingen hårdlänk längre** trots att `CLAUDE.md` påstår det.
Valvkopian är fryst sedan 11 juni. Det är tredje bekräftade instansen av samma fel,
och orsaken finns i varmt minne sedan maj: **Edit-verktyget skriver via temp-fil och
byter namn, vilket kapar hårdlänkar.** Båda sökvägarna fortsätter fungera, den ena
slutar bara vara samma fil. **Öppen tråd — kräver ett beslut om vilken sida som vinner,
och ett svep över alla dokumenterade junctions.**

## 2026-08-01 (forts.) — Claude — Distribuerat, och conclude-protokollet parallelliserat

**Designsystemet är helt i `super-intelligence` 0.4.5** och pushat till grenen
`design-system-v2` (inte `main` — PR-länk finns om du vill merga). Verifierat identiskt:
126 filer i `skills/design`, alla nio hooks, båda syskonskillen, hash för hash.

**Installer-wiringen är gjord** — den öppna tråden från förra passet. Registreringstabellen
i `install.mjs` och `upgrade.mjs` gick från 6 till 8 poster, och båda mergarna stämmer nu av
en **ändrad** matcher: `design-verify-gate` breddades till att täcka Chrome-tillägget, och
den gamla närvarokontrollen hade lämnat befintliga installationer på det gamla värdet för
alltid. Testat mot en simulerad 0.4.4-`settings.json`: 6 ändringar första passet, 0 andra,
och ett orelaterat `carl-hook.py`-block i samma eventarray orört.

**`alunix` är canon.** `alunix-site` ligger kvar med `SUPERSEDED.md` i stället för att
raderas — två levande kopior är precis hur fel katalog blir redigerad, men radering är
ditt beslut, inte ett automatiskt städsteg.

**`/conclude` byggdes om.** Dess mekaniska halva (sessions.db, globala STATUS.md,
minnesspegling, vault-backup, qmd, gbrain, chorus) kör nu parallellt i
`~/.agents/scripts/conclude-finalize.py`, startad i bakgrunden så snart sessionsloggen
finns. Inget steg togs bort. Två buggar som bara körning kunde hitta: npm-shims på Windows
löses inte av `subprocess` utan `shutil.which`, och `gbrain` är faktiskt okonfigurerat
(`Source "default" has no local_path`) — tidigare tyst, nu synligt.

## 2026-08-01 — Claude — Designsystemet ombyggt till register, tre projekt härdade

Arkeologi över tre tidigare sessioner visade att v2-omarbetningen fixade mekaniska fel
(hooks som inte utlöstes, varumärkeskontaminering) men aldrig frågade varför v1:s output
faktiskt var bra. Den enda husstilen (editorial print) ersattes med en registertabell vald
ur verksamheten; utgångsribban gjordes mekanisk (`design-stop.py` blockerar avslut om UI-ändringar
finns utan att en rendering lästs efteråt, i stället för att bero på att användaren skriver
ett explicit mål varje session).

Verifierat med tre blinda one-shot-byggen från fräscha subagenter (Tidvatten, Vintergatan,
Vinterspelen — inklusive ett register utan arbetat exempel på disk), alla godkända vid
första försöket. `verify-design-system.py` 80/80.

Tillämpat på:
- **`anti-slop-design`** — sex demo-register, showcase-sidan omskriven och tre gates den
  själv bröt mot rättade (handritad webbläsarkrom, `1fr`-rutnät som drog 1200px horisontell
  scroll vid 320px, 21 tankstreck). Committad och pushad.
- **`alunix-site`** → klonad till **`alunix`** (nytt fristående repo, historik bevarad,
  ingen fjärrkoppling). Grafanimationen ombyggd till en "dolly" (princip lånad från
  21st.dev, körd baklänges), plus en regression hittad och rättad: reducerad rörelse
  klippte hela stegprogressionen i stället för bara rörelsen.
- **`klova-hamnkrog`** — audit + 8 fynd åtgärdade (saknad accent-token, IA-dubblett,
  kontrastfel, riktad hero-scrim).
- **`super-intelligence`** 0.4.4 → 0.4.5, committad lokalt, **ej pushad**.

**Öppet:** `alunix-site` och `alunix` existerar båda på disk — bestäm vilken som är
kanonisk. Alunix-sidan i övrigt behöver mer arbete enligt användaren själv.
Full session-logg: `session-logs/2026-08-01-session-log.md`.

## 2026-07-30 — Claude — Snajp deployad, designsystemet härdat

### Live
- **https://snajp.vercel.app** — landningssidan, eget Vercel-projekt `snajp`, publik.
- **https://snajp-showcase.vercel.app** — processidan, eget projekt `snajp-showcase`, publik.
- `snipra.vercel.app` **orörd**, pekar fortfarande på main-deployen från 2026-05-24.
  Verifierat efter varje deploy: gammal titel, `/snajp-support` ger 404.

### Gjort
- Allt committat och pushat. `snajp-redesign` (huvudträdet) och `nordic-photo` (E2) ligger på
  GitHub. `.shots/` gitignorerat, 73 MB sessionsbevis som inte hör hemma i historiken.
- E2 sammanslagen in i huvudträdet. Tre CSS-verktyg som handoffen påstod fanns saknades i båda
  träden: `.parallax` (bakgrundsbilder renderade i naturlig storlek och klipptes), `.rise`
  (avslöjandet gjorde ingenting) och `.hrule` (stegraden saknade linjer). Hittade genom att titta
  på den körande servern, inte genom att läsa dokumentationen.
- `<p>` låg inuti `<p>` under demon. Ogiltig HTML, hydreringen bröts, hela sidan ritades om
  på klienten.
- **Malmö → Göteborg och Umeå.** Två nya fotografier: `goteborg-golden.webp` (@addekalk) och
  `haga.webp` (@federi), valda ur ~40 kandidater som lästes som bilder. Statement-bandets scrim
  fick en ockra-komponent, annars läste Haga-gatan kallblått mot den varma paletten.
- **Avslöjandet vid scroll lämnade tolv element permanent osynliga** på varje route i den första
  deployen — sektionsrubriker med tomt under. Infört av mig när `.rise` fick tillbaka
  `opacity: 0`. Fyra spärrar nu, och `scripts/check_reveal.py` som föll mot den trasiga versionen
  innan den litades på.
- Showcasen fångad och läst för första gången. Slutversionen visade Stockholm-E2:an med
  dev-overlay; omfångad från produktionsdeployen. Skärmdumparna gick från 3656 KB till 396 KB.
- **CARL DESIGN har regel 5–10** och beslutet `design-003`: fallback-kedja för visuell
  verifiering, referenser fångas före första raden kod, iterera tills en hel genomgång är ren
  *och* resultatet slår referenserna, misstro mätningen före ögonen, inga förbudsbara designsystem,
  avslöjandesystem ska fela mot synligt.
- `~/.agents/skills/design/` fick steg 1b (referensfångst), fallback-kedjan i steg 5, och
  `scripts/` med shoot, shoot_slices, measure och check_reveal.

### Kvar
- **Alunix-sidan är inte byggd.** Nytt Next.js-projekt i `C:\Users\Anton L\alunix-site`, svenska
  och engelska. Underlag i `HANDOFF-2026-07-29.md` §10, referenslista i planen.
- **Demodatan säger fortfarande Malmö.** Icke-kritiskt, hela Sverige täcks. Fem filer:
  `lib/mock-data.ts`, `components/WorkspaceViews.tsx`, `app/api/email-studio/route.ts`,
  `lib/agent/email-studio-prompt.ts`, `components/DesignDrafts.tsx`.
- **Vercel-token ligger i sessionstranskriptet och bör roteras.**
- Migration `005_workspace_products.sql` är skriven men inte applicerad.
- Env-vars är inte satta på `snajp`-projektet: `SNAJP_SUPPORT_URL` och Supabase-nycklarna.
  Support-demon visar offline-text tills de finns.
- Worktrees `snajp-copyedit`, `snajp-humanized`, `snajp-original` och dev-servrarna på
  3008–3023 lever kvar. Allt är committat, så de kan rivas.
- `MEMORY.md` över taket (2358/2200), `USER.md` på 98 %.
- `.agent-context/current/*` är fortfarande en ofylld mall trots att CLAUDE.md kräver att den läses.

## 2026-07-07 — Grok — Email Studio full automation per Snipra Prompt (1).md

**Fokus:** Automatisera Email-Studio så företag kan skapa konto (endast email/magic link), logga in och omedelbart testa alla funktioner "Kortare", "Skriv om", "Förbättra", "Personalisera", "Översätt", "A/B-varianter", "Uppföljning", "Analysera" på https://snipra.vercel.app/emails (och /dashboard).

**Kritisk regel implementerad:** VARJE åtgärd utgår från https://github.com/coreyhaines31/marketingskills (cold-email, copywriting, copy-editing, ab-testing, emails, marketing-psychology etc). 

### Completed (per spec i "Snipra - Prompt (1).md")
- Utökade till exakt 8 funktioner med svenska etiketter + interna instruktioner bundna till skills.
- Uppdaterade system-prompt i både lib/agent/email-studio-prompt.ts och supabase/functions/_shared/prompts/email-studio.ts:
  - Full "Du är Email Studio..." + KRITISK REGEL + sub-agent arkitektur + kvalitetskontroller + exakt output-format.
  - Inkluderar few-shot + explicit referenser till SKILL.md:er.
  - Använder loadAllMarketingSkills() / bundled corpus.
- Ändrade output till rikt strukturerad JSON (original_version, new_version, explanation (med skills-ref), subject_suggestions (2-3), confidence_tips).
- Uppdaterade UI (EmailStudioEditor.tsx):
  - 8 knappar.
  - Resultatpanel som visar exakt formatet: Ursprunglig, Ny version, Förklaring, Ämnesradsförslag, Konfidens/Tips.
  - "Använd ny version" + direkt apply för vanliga åtgärder.
  - Notis om marketingskills.
- Uppdaterade parsers i actions + edge function + types för rich result.
- Auth: Magic link default till /emails för omedelbar Email Studio access. Endast email + magic recommended för snabb registrering utan extra verifikation. Notiser + hjälptext i LoginForm.
- Legacy mock i WorkspaceViews uppdaterad till nya 8 knappar.
- Följt AGENT.md: Läste marketingskills SKILL.md innan kod (cold-email, copywriting, emails, ab-testing, marketing-psychology). Skyddade filer orörda. Uppdaterade STATUS.md.

### Verification steps (rekommenderas lokalt)
- npm run type-check
- Starta dev: C:\Program Files\nodejs\npm.cmd run dev
- Gå till /login → välj "Magic link" → ange testmail → efter login → /emails → prova alla 8 knappar.
- Kontrollera att förklaringar refererar skills och output matchar spec.

### Notes
- Kräver giltig LLM-nyckel (DeepSeek/OpenAI) i env för att knapparna ska producera riktiga resultat.
- För prod: edge function (refine-email) och Supabase secrets.
- Automator (snipra_automator.py) bör nu kunna klicka de nya knapparna (text "Kortare" etc matchar).
- Nästa: spara user preferences (ton etc) explicit i profile/business_context + feedback loop för smakprofil (enligt tidigare email-studio plan).
- Git: Inget .git synligt i workspace — använd temp overlay + feature branch + gh pr per AGENT.md när push ska göras.

## 2026-06-30 — Grok — snipra_automator + Persistent Login State
Completed reliable login automation + artifact persistence for testing the Email Studio.

### Completed
- Diagnosed and fixed `python snipra_automator.py login <email> <pass>` (was timing out waiting for email input).
  - Root cause: `get_playwright_context` always loaded existing `.snipra-auth-state.json` → middleware instantly redirected `/login` → form never rendered.
  - Fix: `login` command now forces a completely fresh context (`browser.new_context()`, never passes `storage_state`). Other commands (`run`, `demo`, `interactive`) still load the state file to appear "already logged in".
  - Improved robustness: `domcontentloaded` + explicit waits, `type=` locators (primary) + placeholder fallbacks, detailed debug dumps, better navigation waits (lambda + networkidle), onboarding auto-fill path.
- Executed successful login with test account `snipra.dev.1782852323729@example.com`.
- User request "spara ner allt till snipe-leads mappen":
  - Re-saved `.snipra-auth-state.json` after navigating to actual pages (captures latest session).
  - Captured full-page screenshots: `screenshots/logged-in-dashboard.png` and `screenshots/logged-in-emails.png`.
  - Exported `screenshots/cookies-dump.json`.
- Verified end-to-end: loading state + going to `/emails` lands on the real editor (textarea[aria-label="Mejltext"], refine buttons present). No login redirect.
- Background dev server restarts performed cleanly when needed (npm.cmd via hidden processes because of PowerShell policy).

### Verification
- `python snipra_automator.py login ...` → exit 0 + "✓ Logged in successfully! State saved".
- Direct Playwright load with the state file → `/emails` + editor visible.
- Screenshots and state file present in project root after conclude.

### Notes
- Auth token lifetime ~1h (Supabase). Re-login will be needed for long-lived sessions.
- Dev server processes frequently disappear in the agent shell; start locally with `C:\Program Files\nodejs\npm.cmd run dev` for interactive work.
- The four refine buttons (Kortare etc.) are now testable via `python snipra_automator.py run` or `demo` once a valid LLM key is configured.
- Session log: `session-logs/2026-06-30-session-log.md`

## 2026-05-22
Codex rebuilt the project from the prompt into a Next.js App Router SaaS mock/product scaffold.

## Completed
- Created Next.js source structure with TypeScript, Tailwind and App Router.
- Added all requested routes: `/`, `/login`, `/onboarding`, `/dashboard`, `/assistant`, `/leads`, `/companies`, `/companies/[id]`, `/contacts`, `/contacts/[id]`, `/campaigns`, `/campaigns/[id]`, `/emails`, `/analytics`, `/inbox`, `/settings`, `/settings/mailboxes`, `/settings/team`, `/settings/billing`.
- Built Swedish-first landing page, app shell, command palette, mobile nav, dashboard, lead discovery, company intelligence, contact views, campaign views, email studio, analytics, inbox and settings views.
- Added realistic Swedish mockdata for companies, signals, contacts, campaigns, emails and analytics.
- Added localization foundation via `lib/i18n.tsx` and localized mockdata fields.
- Added Supabase schema with RLS draft and Edge Function stubs.
- Added `PROJECT_KNOWLEDGE.md`, `SNIPRA_IMPLEMENTATION_PLAN.md` and `.agents/product-marketing.md`.

## Verification
- `npm.cmd run type-check` passed.
- `npm.cmd run build` passed.
- Local devserver smoke-tested all primary routes with HTTP 200 while the server was running.

## Notes
- Persistent background devserver processes are terminated by the tool environment after command completion. Run `npm.cmd run dev -- --port 3000` locally to keep it open.
- `chorus` was not available in PATH, so cross-agent messages could not be sent.

## 2026-05-22 Shell Fix
- Root cause from npm log: npm was launched from `C:\Users\Anton L`, so it searched for `C:\Users\Anton L\package.json` instead of the project package.
- Added `C:\Users\Anton L\package.json` proxy scripts that forward `npm.cmd run dev`, `build`, `type-check` and `start` to `C:\Users\Anton L\snipe-leads`.
- Added project-local `snipra.cmd` launcher and `scripts/windows-shell.md`.
- Did not change PowerShell execution policy. Use `npm.cmd` instead of `npm` in PowerShell unless the user explicitly approves a broader user-level policy change.

## 2026-05-22 Visual Rebuild Recovery
- Restored Tailwind output by adding Tailwind layer directives to `app/globals.css`.
- Rebuilt the visual direction from `snipra.html`: Fraunces display typography, JetBrains Mono kickers, ruled editorial grids, ochre/mineral/paper tokens, ledger rows, marquee, dark proof section and publication-style product surfaces.
- Replaced the generic SaaS dashboard shell with editorial app navigation, PageShell layouts, ledgers, timelines and compact manuscript/workspace views.
- Rebuilt onboarding as a styled editorial wizard instead of browser-default inline controls.
- Added mobile containment/polish rules for 12-column editorial grids, app nav scrolling and narrow text columns.
- Verification passed: `npm.cmd run build`, sequential `npm.cmd run type-check`, generated CSS utility search, production HTTP 200 route smoke for `/`, `/onboarding`, `/dashboard`, `/leads`, `/companies/byggkompaniet-syd`, `/campaigns/lokal-expansion-syd`, `/emails`, `/analytics`, `/settings`.
- Final screenshots captured in `C:\tmp\snipra-final-*.png`.

## 2026-05-22 Chorus Fork Install
- Installed `agent-chorus@0.9.1` globally from `C:\Users\Anton L\agent-chorus-fork`.
- Removed generated `chorus.ps1` / `chorus-node.ps1` shims so PowerShell resolves `chorus` to the working npm `.cmd` shim without changing execution policy.
- Ran `chorus setup --context-pack`; provider wiring and context-pack templates were created, but Git hook install failed because `C:\Users\Anton L\snipe-leads` is not currently a Git repository.
- Ran plain `chorus setup --json`; project provider snippets and managed blocks are installed in `.agent-chorus/`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `.gitignore`.
- Verified `chorus --version`, `chorus doctor --json`, `chorus send`, `chorus messages --clear`, and `chorus read --agent codex --cwd ... --json`.
- Remaining doctor warnings are environmental: no Gemini/Claude/Cursor sessions discovered for this project, registry update check blocked, Claude CLI not found, Git hooks not configured because this folder has no `.git`.

## 2026-05-22 Conclude
- Session log updated at `session-logs/2026-05-22-codex-snipra-rebuild.md`.
- Next focus: connect mockdata to Supabase, generate database types after schema application, implement real AI/mail adapters, add browser/UI regression coverage, and split `components/WorkspaceViews.tsx` before the next large feature pass.

## 2026-05-24 Global MCP Fix — Claude
- Fixed `agentmemory` MCP (-32000 error): changed `~/.claude.json` command from `npx -y @agentmemory/mcp` → `node dist/cli.mjs mcp` (avoids unreliable npx spawn on Windows).
- Fixed `carl-mcp` (not showing up): added to `~/.claude.json` top-level `mcpServers` and `~/.claude/settings.json` `enabledMcpjsonServers`. Now global across all projects.
- Session log: `session-logs/2026-05-24-session-log-4.md`
- **Next action: restart session to verify both MCP servers appear.**

## 2026-05-24 Design Draft Polish — Claude
- Landing page (`/` → `editorial-clean` variant) **APPROVED** by user.
- Fixed gradient (ochre tint): replaced blurred blob (clipped by `body { overflow-x: hidden }`) with pure CSS radial-gradient div on `<main>` at `top-0`. No filter = no clipping.
- Header frosted glass: `bg-paper/30 backdrop-blur-xl` (was `/60` — now 50% more see-through).
- Gradient: `circle at 18% 0%`, opacity 0.3, transparent 65%, h-860px, mask fades 78%→100%.
- Dashboard portal needs further work — open thread for next session.
- Session log: `session-logs/2026-05-24-session-log.md`
- Active plan: `plans/2026-05-24-snipra-design-drafts.md`
- **Next focus: dashboard portal improvements** (`/design-drafts/editorial-clean/portal`).

## 2026-05-24 Vercel CI/CD — Claude
- Vercel project `snipra` created under `olofluns-projects` and linked to `https://github.com/oloflun/snipe-leads`.
- GitHub Actions workflows added: `main` → production, `development` → preview.
- `vercel.json` with `"git": {"deploymentEnabled": false}` prevents duplicate deploys from Vercel's own Git integration.
- `package-lock.json` committed (required by `actions/setup-node@v4 cache: npm`).
- Both pipelines verified working end-to-end.
- Session log: `session-logs/2026-05-24-session-log-2.md`
- **Next focus: dashboard portal improvements** — ask user what specifically needs fixing.

## 2026-06-10 Phase 1: Supabase & Auth — Grok (in progress)

### Completed
- Added Supabase client layer: `lib/supabase/client.ts`, `server.ts`, `admin.ts`
- Added `lib/database.types.ts` (hand-written from schema; regenerate with `npx supabase gen types typescript --linked` after linking project)
- Added `lib/auth.ts`, `lib/workspace.ts`, `middleware.ts`, `app/auth/callback/route.ts`
- Added server actions: `lib/actions/auth.ts`, `lib/actions/onboarding.ts`
- Wired `LoginView` and `OnboardingView` to Supabase Auth (password, magic link, signup) and `business_contexts` save flow
- Added `components/auth/LoginForm.tsx`, `OnboardingForm.tsx`, `useUser.ts`
- Added signup trigger migration: `supabase/migrations/001_handle_new_user.sql`
- Added `.env.local.example`; added `@supabase/ssr` dependency for cookie-based App Router auth

### 2026-06-10 Schema applied — Grok
- Project: `https://spsmblyvasagpekjmgmf.supabase.co`
- `.env` configured (gitignored): URL, API keys, `SUPABASE_DB_PASSWORD`
- `npm run apply:schema` succeeded — all 15 public tables + signup trigger live
- Verified: admin user creation → workspace + profile auto-created via `handle_new_user` trigger
- Server/middleware use `SUPABASE_SERVICE_ROLE_KEY` (publishable key still rejected by API)

### Remaining before Phase 1 sign-off
- **Dashboard**: Authentication → Providers → Email → disable **Confirm email** (`mailer_autoconfirm` still false; public signup hits rate limit)
- ~~**Dashboard**: copy valid Publishable key~~ — `sb_publishable_...` verified working in `.env`
- **Git**: not available in collaborator environment; feature branch `feature/supabase-auth-setup` must be created locally before PR
- **Marketing skills**: `/customer-research` and `/marketing-psychology` skills not found locally; onboarding defaults applied from `.agents/product-marketing.md` — review workflow with user before marking Phase 1 complete

### Verification (pending credentials)
- [ ] Sign up → workspace + profile created via trigger
- [ ] Login → protected routes accessible
- [ ] Incomplete onboarding → redirect to `/onboarding`
- [ ] Save business context → redirect to `/dashboard`
- [ ] Auth persists across refresh
- [ ] `npm run type-check` and `npm run build`

## 2026-06-10 Email Studio + Conclude — Grok

### Completed
- Installed 44 marketing skills to `references/marketingskills-main/` (coreyhaines31/marketingskills)
- Email Studio agent: skill loader (all skills/call), DeepSeek LLM, `refineEmail` action, `EmailStudioEditor` UI
- Edge Function `refine-email` + shared prompts/LLM layer
- `/emails` wired to data loader (Supabase with mock fallback)
- User decisions: DeepSeek yes, GDPR yes, no feedback UI, skills in repo references/
- Restored `~/.agents/skills/conclude/SKILL.md` on collaborator machine (partial — Step 1 only)
- `npm run type-check` passes; `npm run bundle:skills` bundles corpus

### Remaining
- Add `DEEPSEEK_API_KEY` to `.env` and test studio buttons
- Phase 1 sign-off items (confirm email off, auth E2E, git PR)
- Seed `generated_emails` for real Supabase data on `/emails`
- Paste full `/conclude` SKILL.md (Steps 2–5) from KB

- Session log: `session-logs/2026-06-10-session-log.md`
- **Next focus:** DeepSeek key + Email Studio live test + Phase 1 verification

## 2026-05-24 Skill Registry Fix — Claude
- `/skill` SKILL.md: fixed iCloud→`~/.agents/skills/` path, documented flat structure (no category subdir), fixed evolve script path.
- `/conclude` SKILL.md: Step 5b added skills path/commit note; Step 2e replaced broken `py - <<'PYEOF'` with PowerShell `$script | & "C:\Python314\python.exe" -`.
- `~/CLAUDE.md`: `/skill` table entry corrected to `~/.agents/skills/`.
- `~/.claude/skills/` converted from unlinked copy to junction → `~/.agents/skills/` (backup at `skills-backup-20260524`).
- Session log: `session-logs/2026-05-24-session-log-3.md`

## 2026-07-25 Snajp-Support: Render + DeepSeek portability — Claude

**Bakgrund:** Snajp-Support (headless AI-kundtjänstbackend, `snajp-support/`) körde bara lokalt via en `.venv` + `uvicorn --port 8000`, bunden till en enskild dators filsystem. Två samarbetande utvecklare + krav på publik demo-miljö → allt måste fungera reproducerbart över GitHub + Vercel, ingen maskinbunden state.

### Completed
- **DeepSeek-kompatibilitet i backenden** (var OpenAI-only):
  - Ny `snajp-support/app/agent/llm.py` — central klientfabrik. Provider styrs av `LLM_PROVIDER` (`openai`|`deepseek`); DeepSeek går mot `https://api.deepseek.com` (OpenAI-kompatibel chat-completions).
  - `support_agent.py`: Agents SDK tvingas till `OpenAIChatCompletionsModel` (DeepSeek saknar stöd för Responses API) + `set_tracing_disabled(True)` i live-läge. Vision (bildbilagor) degraderar till textnotis när provider=deepseek (DeepSeek `deepseek-chat` är inte multimodal).
  - `embeddings.py`: embeddings går **alltid** mot OpenAI (`EMBEDDING_API_KEY`, separat från chat-nyckeln) — DeepSeek har ingen embeddings-endpoint. Utan nyckel → `None` → KB faller tillbaka på Postgres full-text-sökning (befintligt mönster, oförändrat).
  - `config.py`: nya fält `llm_provider`, `llm_base_url`, `deepseek_api_key`, `embedding_api_key`, `active_llm_key()`; auto-korrigerar `gpt-*`-default → `deepseek-chat` när provider=deepseek; `is_simulation()` kollar nu aktiv providers nyckel.
  - Verifierat: 15/15 pytest passerar (simuleringsläge), samt manuell konstruktionskontroll av båda provider-vägarna (base_url, modelltyp, embedding-klient None/set) i en engångs-venv i scratchpad — ingen `.venv` skapad i repot.
- **Render-deploy** (backend-host, beslutat av användaren över "allt på Vercel" pga serverless-inkompatibilitet — bakgrundsjobb via `asyncio.create_task` + in-memory job-store överlever inte serverless-invocations):
  - Ny `snajp-support/render.yaml` (Blueprint, IaC) — pekar på befintlig `Dockerfile` oförändrad.
  - `Dockerfile`: CMD respekterar nu `$PORT` (Render injicerar den; lokalt defaultar 8000).
- **Vercel-koppling** (ingen frontend-kodändring — proxyn var redan ren):
  - `vercel.json`: `git.deploymentEnabled` false → **true** (auto-deploy från GitHub aktiverat).
  - `app/api/snajp-support/_lib.ts`: offline-hint uppdaterad (pekade tidigare på lokal venv-uvicorn-kommando, nu på Render/`SNAJP_SUPPORT_URL`).
- Env-dokumentation: `snajp-support/.env.example` + rotens `.env.local.example` (lade till `SNAJP_SUPPORT_URL`/`SNAJP_INTERNAL_API_KEY` som saknades där helt).
- `snajp-support/README.md`: Docker-quickstart ersätter venv-instruktioner, DeepSeek-konfig, Render-deploy-steg.
- Branch: `feature/email-studio-sync-2026-07-20`.

### Open threads / next agent
- **Render dashboard-setup (ej gjort, kräver användarens konto):** skapa Blueprint mot repot (`snajp-support/render.yaml`), sätt secrets `DEEPSEEK_API_KEY`, `SNAJP_MASTER_API_KEY`, `SNAJP_DEMO_API_KEY`. Notera den publika Render-URL:en.
- **Vercel env-vars (ej gjort):** sätt `SNAJP_SUPPORT_URL` = Render-URL:en, `SNAJP_INTERNAL_API_KEY` = samma värde som Renders `SNAJP_DEMO_API_KEY`.
- **Valfritt men rekommenderat för stabil demo:** kör migrationerna `supabase/migrations/002_snajp_support.sql` + `003_snajp_multitenant.sql` mot Supabase-projektet, sätt `DATABASE_URL` på Render — annars nollställs tickets/KB vid Renders free-tier spin-down (in-memory).
- **Ej verifierat mot riktigt DeepSeek-API** — bara konstruktions-/wiring-verifiering lokalt (ingen faktisk API-nyckel användes). Första riktiga end-to-end-test bör göras efter Render-deploy: `POST /api/chat` → polla `/api/jobs/{id}` → riktigt svenskt svar.
- Free-tier Render spinner ner vid inaktivitet → cold start ~30–60s på första anropet; `SupportChat`-komponenten pollar upp till 90 ggr så det tolereras, men vet om det.
- `.claude/launch.json`: dev-servern kör nu på **port 3005** (inte 3000) — porten var upptagen av ett annat lokalt projekt på användarens maskin. `autoPort: true` är satt som fallback.
- Ospårade filer i arbetskatalogen som INTE ingår i denna commit (fanns redan innan detta arbete, orörda): `References/` (First/Original/Second/Third iteration), `session-logs/2026-05-27-session-log.md`. Okänt syfte — fråga användaren om de ska committas eller är skräp.
- `package-lock.json` hade oskarpt npm-versions-brus (borttagna `libc`-fält) från en lokal `npm install` — **inte committat**, lämnat orört i arbetskatalogen för att undvika onödigt diff-brus. Kör `npm install` igen och committa separat om det stör CI.

## 2026-07-25 (forts.) Vercel-bygget lagat + deploy-förberedelser — Claude

**Bakgrund:** Efter att Sebbes email-pipeline (`38457f2` + merge `3471758`) hämtats hem gjordes en genomgång av integrationen mot DeepSeek/Render-arbetet. Merge-konflikterna i `triage.py`/`config.py` var korrekt lösta — DeepSeek-lagret överlevde, och Sebbes vision-hantering återanvände vår `llm_provider`-guard. Genomgången avslöjade däremot tre fel som blockerade deploy.

### Completed
- **Vercel-bygget var trasigt sedan minst 2026-07-22** — de fem senaste deployerna hade `readyState: ERROR` och projektet stod `live: false`. Ingen hade märkt det. Byggloggen (via Vercel-MCP) pekade på `app/api/email-studio/route.ts:277`: AI SDK 7 döpte om `maxTokens` → `maxOutputTokens` och tog bort det gamla namnet (verifierat mot `node_modules/ai@7.0.19` — `maxTokens` finns inte i typerna). Fixat.
- **Följdfel:** efter den fixen stoppades bygget av samma fel i `email-studio/kopior/` — en kopiemapp (37 spårade filer) med dubbletter som redan type-checkas på riktig plats, inkl. Deno-funktioner. `supabase/functions` var redan exkluderad i `tsconfig.json` av just det skälet; `email-studio/kopior` tillagd enligt samma mönster. `npm run build` + `npm run type-check` går nu igenom rent (exit 0).
- **Sex odokumenterade env-vars** från email-pipelinen (`INBOX_POLL_SECONDS`, `AUTO_SEND_MIN_CONFIDENCE`, `IMAP_HOST/USER/PASSWORD/FOLDER`) fanns i `config.py` men varken i `.env.example` eller `render.yaml` — IMAP hade inte gått att aktivera på Render. Alla 17 `Settings`-fält är nu dokumenterade (verifierat programmatiskt mot `Settings.model_fields`).
- **Migration 003 och 004 saknade väg in i databasen.** `scripts/apply-snajp-migration.mjs` stannade vid 002. Kör nu alla tre. Valt framför `npx supabase db push` eftersom 001/002 applicerades utanför Supabases migrationsspårning — `db push` hade försökt köra om dem. Verifierat att alla tre migrationerna är idempotenta (samtliga `CREATE` har `IF NOT EXISTS`, samtliga `DROP` har `IF EXISTS`), så omkörning är ofarlig.
- **End-to-end-verifierat lokalt** (backend i simuleringsläge på :8000, frontend på :3005): 6 mockmail → klassificering → utkast → godkännande → `sent`. Både eskaleringsvägarna bekräftade: grundningsregeln (ingen KB-träff → "Fråga om öppettider", conf 0.4) och den hårda spärren (återbetalning → "Trasig vara", conf 0.55). Sebbes nya `orderstatus`-fack träffar rätt med conf 0.9. Dashboarden visar korrekt via catch-all-proxyn, inga konsolfel. 21/21 pytest.
- Commits: `677ff48` (env-docs), `a5cf234` (migrationsskript), `6149580` (byggfix).

### Open threads / next agent
- **Deploy `dpl_5AnMtgAh2Ezx1Fy5EpfYRJ7LXdx4` byggde när sessionen avslutades** — kontrollera att den blev `READY`. Blir den det är Vercel-pipelinen frisk igen för första gången sedan 2026-07-22.
- **Env-vars är INTE satta någonstans än.** De bor på tre ställen, inte två: Vercel (frontend), Render (Python-backenden), och Supabase är bara databasen man pekar på — ingen env-butik. Ordning: migrationer → Render → Vercel (Vercel behöver Render-URL:en).
- **Vercel CLI är inte inloggad** (`vercel login` krävs, interaktivt). Vercel-**MCP:n** är däremot autentiserad mot rätt team (`team_xLbo3OZ554hw3HEJBC7F5Dui`) och kan läsa projekt/deployer/byggloggar — men har inga verktyg för att sätta env-vars.
- **Supabase-MCP:n är auktoriserad mot fel organisation** — rätt konto, men OAuth-kopplingen ger bara org `ycracxrmcbapcvaxigej` ("AL") som enbart innehåller projektet "WMS". Snipras org är `fgaquwmqajjaboyqliij`; `get_project` mot den ger `permission denied`. Åtgärd: koppla om Supabase-connectorn i appen och godkänn rätt org — då kan migrationerna köras via MCP:ns `apply_migration` helt utan DB-lösenord.
- **Projekt-ref:en i koden är korrekt och ska INTE ändras.** `fgaquwmqajjaboyqliij` är ett organisations-ID, inte en projekt-ref (verifierat: `fgaquwmqajjaboyqliij.supabase.co` är NXDOMAIN, medan `spsmblyvasagpekjmgmf.supabase.co` löser upp och svarar 401). De fyra skripten i `scripts/` som hårdkodar `spsmblyvasagpekjmgmf` pekar alltså rätt.
- **Varning inför demon:** DeepSeek utan `EMBEDDING_API_KEY` ger full-text-sökning istället för vektorsökning i KB. Grundningsregeln eskalerar allt utan KB-träff — demon riskerar att eskalera nästan varje mail. Sätt en OpenAI-nyckel som `EMBEDDING_API_KEY` på Render om demon ska svara i stället för att eskalera.
- `next-env.d.ts` växlar mellan `.next/dev/types` och `.next/types` beroende på om `dev` eller `build` kördes sist. Generad fil — committa den inte, det skapar bara konflikter mellan er två.

## 2026-07-27 Demo redo i deploy + två åtkomstspärrar kvar — Claude

### Completed
- **KB-landmina åtgärdad** (`870f8bc`): med `DATABASE_URL` mot färsk Supabase var `ss_knowledge_base` tom → grundningsregeln i `processor.py` hade eskalerat *varje* ärende. `ensure_default_kb()` bruten ur `seed_kb.py`, anropas nu vid uppstart i Postgres-läget. Seedar text utan embeddings (blockerar inte Renders health check), idempotent, fäller aldrig uppstarten.
- **`render.yaml` kräver inga hemligheter**: utan `DEEPSEEK_API_KEY` kör tjänsten simuleringsläge. `SNAJP_MASTER_API_KEY` genereras av Render (föll annars tillbaka på publik platshållare — verklig svaghet). `SNAJP_DEMO_API_KEY` satt explicit = frontendens fallback, så Vercel/Render matchar utan konfiguration.
- Migrationerna 002/003/004 **applicerade** mot `spsmblyvasagpekjmgmf` via `supabase-snipra`-MCP:n. Alla 14 `ss_`-tabeller + 4 extra från 004 finns, RLS aktivt, default-tenant seedad.
- **Multi-org Supabase-MCP löst**: `.mcp.json` (HTTP-typ, PAT via `${SUPABASE_PAT_SNIPRA}`) vid sidan av OAuth-connectorn. Gitignorad. Kräver att env-varen finns i processen *vid start* — `setx` + helt nytt terminalfönster, inte bara ny `claude`-process i samma fönster.
- `development` och feature-branchen står på `870f8bc`, identiska. Alla Vercel-deployer sedan byggfixen är READY.
- Deployad sida verifierad via Vercel-MCP:ns `web_fetch_vercel_url`: HTTP 200, korrekt titel, alla fyra flikar, alla sju fack.

### Open threads / next agent
- **Preview-URL:erna ligger bakom Vercel Deployment Protection** — `snipra-git-development-…vercel.app` ger 302 → `vercel.com/sso-api`. Fungerar för inloggade, men är INTE en publik demo. Åtgärd: stäng av Deployment Protection i Vercel-projektets inställningar (Settings → Deployment Protection).
- **Produktionsdomänen är inaktuell**: `snipra.vercel.app/snajp-support` ger 404. Produktion är låst till en gammal deploy från `main` (commit `a10d919`, från innan Snajp-Support fanns). `main` har medvetet inte rörts. Ska demon ligga på produktionsdomänen krävs en merge till `main`.
- **Render är fortfarande inte uppsatt** — utan `SNAJP_SUPPORT_URL` visar demon tomt läge/offline-text. Blueprint + `SNAJP_SUPPORT_URL` på Vercel är allt som återstår för fungerande demo.
- **Säkerhetsskuld inför publik demo** (användaren: "vi fixar det i nästa runda"): demo-nyckeln är publik i repot, så vem som helst med backend-URL:en kan anropa API:t. Harmlöst i simuleringsläge; med riktig `DEEPSEEK_API_KEY` blir det tokenbränning. Byt `SNAJP_DEMO_API_KEY` till ett hemligt värde och sätt samma som `SNAJP_INTERNAL_API_KEY` på Vercel innan riktig AI slås på publikt.

## 2026-07-28 Publik demo live + Gmail-inkorg verifierad — Claude

### Completed
- **Demon fungerar publikt**: https://snipra-oloflun-olofluns-projects.vercel.app/snajp-support
  Hela kedjan verifierad mot deployen: 6 mockmail seedade → klassificerade i sex fack
  (konf 0.4–0.9) → 2 eskalerade, 4 utkast → godkännande i UI:t → status `sent`.
- **Render-backenden deployad**: `snajp-support` (`srv-d9k99ktg1s2s73fl0v6g`,
  https://snajp-support.onrender.com), Docker, rootDir `snajp-support`, branch
  `development`, healthCheck `/health/live`. Kör simuleringsläge (ingen DeepSeek-nyckel).
- **Tre fel som blockerade demon, alla åtgärdade:**
  1. Render-tjänsten `snipe-leads` (`srv-d9k8u6jm8hqs73bukveg`) var felkonfigurerad — en
     Node-tjänst som byggde Next.js-frontenden från repo-roten, alltså en dubblett av
     Vercel, inte Python-backenden. Ligger kvar orörd; **kan pausas/raderas, den fyller
     ingen funktion** (kräver användarens beslut).
  2. `SNAJP_SUPPORT_URL` fanns på Vercel men med **tomt värde** och bara target
     `production` — medan deployerna som servar demon är previews. Satt till
     Render-URL:en för production+preview. OBS: teamet tvingar `type: sensitive` på
     alla env-vars, så värdet går inte att läsa tillbaka via API:t.
  3. `snipra-oloflun-olofluns-projects.vercel.app` var aliasad till en **gammal deploy**
     utan env-varen. Ompekad till den nya produktionsdeployen.
- **Gmail-IMAP verifierad live lokalt**: 3 riktiga mail hämtade från `snajpsupport@gmail.com`,
  parsade (multipart→text, svenska tecken korrekt), klassificerade, utkast skapade,
  beslutslogg komplett. Omkörd synk gav 0 nya → dedupe på Message-ID håller.
- **Dashboard: "Synka inkorg"-knapp** + proxyn skiljer nu på "env-var saknas" och
  "backend svarar inte" och skriver ut vilken adress den försökte nå (`df597a6`).
  Den diagnostiken var det som gjorde fel 2 och 3 ovan synliga.
- `.gitignore`: `.env.*` (utom `.env.example`). En `.env.txt`-kopia med riktiga
  IMAP-credentials låg untracked och hade följt med nästa `git add`.
- MCP: `.mcp.json` med `supabase-snipra` **och** `render` (https://mcp.render.com/mcp),
  båda med env-var-referenser. Vercel CLI v58 installerad.

### Open threads / next agent
- **IMAP är medvetet INTE satt på Render.** Demo-nyckeln är publik i repot, så vem som
  helst med backend-URL:en kunde annars anropa `/api/inbox/sync` och läsa användarens
  riktiga Gmail via `/api/inbox`. Säkra `SNAJP_DEMO_API_KEY` först (se skulden ovan),
  sätt sedan `IMAP_HOST/USER/PASSWORD` i Render-dashboarden.
- **Nyskapad Render-tjänst routar inte direkt.** Första ~10 min gav
  `x-render-routing: no-server` intermittent (mätt 7/12), därefter 12/12. Bygget och
  health-checkarna var gröna hela tiden — vänta ut propageringen, felsök inte bygget.
  (Renders gräns är 750 instanstimmar/månad delat på alla gratistjänster, **inte** ett
  tak på antal tjänster — den hypotesen testades och avfärdades.)
- **Free-tier spinner ner efter 15 min** utan trafik, spin-up tar ~1 min. Första
  anropet efter viloläge kan visa offline-text; ladda om.
- **`DATABASE_URL` är inte satt på Render** → in-memory-lagring, allt nollställs vid
  spin-down. Migrationerna är applicerade, så det räcker att sätta pooler-strängen.
- **`snipra.vercel.app` ska INTE röras** (användarens beslut 2026-07-28). Den pekar på
  den gamla main-deployen från 2026-05-24 (`dpl_FyddcYVEApuJEUUFNyYHga1tYVZa`,
  commit `a10d919`) och `/snajp-support` ger 404 där — det är avsiktligt.
  Varning: att deploya med `target: production` flyttar aliaset dit automatiskt.
  Det hände under denna session och fick återställas manuellt. Vill du deploya om
  demon, aliasa `snipra-oloflun-olofluns-projects.vercel.app` mot den nya deployen
  i stället för att göra den till produktion.
- **Prioriterad demo-URL:** https://snipra-oloflun-olofluns-projects.vercel.app/snajp-support
  (alias mot `dpl_BpCmCG495MbPdd5rXeAMqHXkZxLb`, branch `development`).
