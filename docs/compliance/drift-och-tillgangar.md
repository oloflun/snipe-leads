# Drift och tillgångar: det som finns, med belägg

Datum: 2026-11-18. Skrivet av Claude (agent) på Antons uppdrag. Status: beskrivning av
dagens drift, inte en policy. Allt här går att kontrollera i den fil som anges; det
som inte är belagt står som "inte belagt". Underlag för ISO 27001 A.5.9, A.5.37,
A.8.4, A.8.9, A.8.15, A.8.16, A.8.29, A.8.32 och ISO 42001 A.4.5
(`score-plan-2026-11-18.md`).

Källor: `bevis/railway-konfiguration-2026-11-18.txt` (variabelnamn, inga värden),
`bevis/railway-regioner-2026-11-17-efter.txt`, `bevis/github-2026-11-18.txt`,
`leverantorer.json`, och koden som anges per rad.

---

## 1. Tillgångsförteckning: driften

Railway-projektet `brave-passion`, två miljöer. Alla tjänster och volymer i
regionen `ams` (Amsterdam), en replik per tjänst (`bevis/railway-regioner-2026-11-17-efter.txt`).

| Miljö | Tjänst | Vad | Publik adress | Data |
|---|---|---|---|---|
| main | `web` | Next.js-appen (sajt, inloggning, adminytor) | `https://www.snajp.se` (`bevis/railway-konfiguration-2026-11-18.txt:174`) | Ingen egen lagring; når Postgres som `snajp_web` |
| main | `api` | FastAPI-backenden (`snajp-support/`): support, Iris, kvitton | `https://api-production-d7695.up.railway.app` (rad 198) | Når Postgres som `snajp_app` och Redis |
| main | `support` | Den publika chattytan | `support-main.up.railway.app` (rad 185) | – |
| main | `Postgres` | Produktionsdatabasen, volym `postgres-volume` | Publik TCP-proxy påslagen (rad 230-231) | Alla kunders data |
| main | `Redis-main` | Jobbkö och cache, volym `redis-main-volume` | Ingen | Jobbposter, kort livslängd |
| main | `Redis` | Bara variabler (rad 201); ingen driftsatt instans i miljön enligt regionsbeviset | Ingen | Ingen |
| development | `web`, `api`, `support` | Samma kod från grenen `development` | `web-development-6c85.up.railway.app`, `api-development-5cc3.up.railway.app`, `support-development.up.railway.app` (rad 10, 34, 21) | Spegel av produktionen (`DEPLOY.md`) |
| development | `Postgres` | Spegeln, volym `postgres-volume-BM7I` | Publik TCP-proxy påslagen (rad 76-77) | Kopia av produktionens persondata |
| development | `Redis` | Jobbkö och cache, volym `redis-volume` | Ingen | – |
| development | `Redis-main` | Bara variabler (rad 156); ingen driftsatt instans i miljön enligt regionsbeviset | Ingen | Ingen |

Säkerhetskopior: inga scheman och inga kopior på någon volym (`bevis/railway-backuper-2026-11-17.txt`).

## 2. Tillgångsförteckning: tjänster utanför Railway

| Tjänst | Används till | Belägg |
|---|---|---|
| GitHub (`oloflun/snipe-leads`, privat) | Källkod, CI, synk och migrationer i Actions, övervakning | `bevis/github-2026-11-18.txt` |
| Google Cloud, Vertex AI | Alla modellanrop (Gemini), regioner per steg i `snajp-support/app/config.py` | `ai-system/README.md`; INV-DATA-006 |
| TypeSafe (Jev) | Förfiltrering av leads; av för inkorgen | `ai-system/jev.md` |
| Resend | Utgående mejl | `leverantorer.json` |
| ScrapeGraphAI | Hämtning av bolagssajter | `leverantorer.json` |
| Loopia | DNS för snajp.se | `leverantorer.json` |
| Redis Cloud, Render, Supabase, Vercel | Avvecklade i drift, inte raderade | `bevis/render-suspenderad-2026-11-18.txt`, `bevis/vercel-snajp-stangt-2026-11-18.txt` |

Saknas i förteckningen: datorer, telefoner och vem som äger respektive konto. Det kräver
uppgifter från ägaren (`ramverk/iso27001/matris.md`, frågorna sist).

## 3. Åtkomst till källkoden

- Repot är privat. Två personer har åtkomst: `oloflun` (admin) och `bergmansebastian2002`
  (write) (`bevis/github-2026-11-18.txt`).
- **Grenskyddet på `main` gäller inte längre.** GitHub svarar 403 på frågan om grenskydd:
  gratisplanen har det bara för publika repon. Code owner-kravet i `.github/CODEOWNERS`
  tvingar därför inget sedan repot blev privat 2026-11-18. Release till `main` är
  fortfarande Antons handgrepp enligt `CLAUDE.md`, men det är en regel, inte en spärr.
- Installerade GitHub-appar går inte att lista med agentens token. Appen Supabase har
  enligt release-PR 72 fortfarande åtkomst till repot.

## 4. Ändringshantering som CI tvingar fram

Arbetsflödena körs från standardgrenen `development`.

| Kontroll | Var | Vad den fäller |
|---|---|---|
| Hemligheter (gitleaks) | `verify.yml`, jobbet `hemligheter` | Nyckelformat i nya commits i varje PR och push |
| Testsviten | `verify.yml`, `python-tests` | Backendens tester |
| Arkitekturinvarianter | `verify.yml`, `invariants` | Varje invariant i `ARCHITECTURE_INVARIANTS.md`; en utan test fäller (meta-testet) |
| Databastester | `verify.yml`, `databas` | Migrationskedjan från noll i Postgres 17, gallringen, **tenantisoleringen (RLS) och rättighetsskriptet** (från 2026-11-18, se avsnitt 6) |
| Imagebygge | `verify.yml`, `docker-smoke` | Att backendens och driftens images bygger och startar |
| Typkontroll | `verify.yml`, `type-check` | TypeScript |
| Säkerhets- och AI-frågan | `pr-granskning.yml` (INV-PROC-001, från 2026-11-18) | En PR mot development utan besvarad fråga i mallen |
| Releasens migrationer | `migrera.yml` | En release-PR mot main när development har okörda migrationer |
| Beroenden | `.github/dependabot.yml` | Veckovisa uppdaterings-PR:er; larm vid kända sårbarheter |

Belägg för att CI körs: 95 körningar av Verify på `development`, 93 lyckade
(`bevis/github-2026-11-18.txt`).

**Det CI inte tvingar:**
- Railway deployar på push utan att vänta på CI (`verify.yml`, kommentaren under `railway-main`).
- Ingen granskning krävs före merge, varken till `development` eller, sedan repot blev privat, till `main` (avsnitt 3).
- Ändringar i Railway-variabler loggas inte någonstans. Konfigurationen exporteras för hand
  (`bevis/railway-konfiguration-*.txt`). Sedan 2026-11-18 finns en baslinje att jämföra mot:
  `python scripts/railway_baslinje.py --jamfor` visar avvikelser mot `railway-baslinje.json`
  (namn och icke-hemliga inställningar, aldrig hemliga värden). Den körs inte automatiskt.
- Kodskanningen (CodeQL) och GitHubs hemlighetsskanning är avstängda sedan repot blev privat.

## 5. Loggning och övervakning

| Vad | Var | Lagringstid |
|---|---|---|
| Ett id per HTTP-anrop (`X-Request-Id`) på varje loggrad, i svaret och i felposten | `snajp-support/app/sparning.py:1-20` | Som Railways loggar |
| Fel och händelser | Tabellen `platform_events` (`sparning.py`) | Inte beslutad |
| Varje AI-körning med instruktionslager, indata och utdata | `agent_runs` (INV, se `ai-system/README.md`); den äldre bokföringsytan sparar sedan 2026-11-18 bara kvittotextens längd och hash (PR 83) | Inte beslutad; gallringen är byggd men avslagen |
| Plattformsadminens och master-nyckelns åtkomst | `audit_logs` (migration 123), se nedan | 365 dagar, gallras automatiskt |
| Supportens beslut per mejl | `ss_decision_log` | Inte beslutad |
| Tjänsternas loggar | Railway | Beror på planen: 3 dagar (Free), 7 dagar (Trial och Hobby), 30 dagar (Pro), enligt https://docs.railway.com/guides/logs, avsnittet "Log retention". Kontots plan är lägre än Pro (`BESLUTSUNDERLAG-2026-11-17.md` A4); exakt plan är inte belagd |

**Åtkomstloggen för admin** (från 2026-11-18 natt, i `development`, migration 123). Fram till
dess skrev ingen kod i `audit_logs`. Nu skrivs en rad per åtkomst:

| Väg | Var loggen skrivs | Vem | Åtgärd |
|---|---|---|---|
| Varje anrop med master-nyckeln (`/api/admin/*`, `/api/keys`): adminytan i Next och provisioneringen av nya kunder | `deps.require_master_key` → `snajp-support/app/api/adminlogg.py` → `logga_adminatkomst` | Plattformsadminens id ur `X-Snajp-Admin`, som Next sätter ur sessionen (`app/api/snajp-support/_lib.ts`) och databasen prövar mot `platform_admins`. Annars "master-nyckel" | `las` (GET) eller `andra` |
| Kundbesök: admin öppnar en kunds arbetsyta (`lib/actions/vy.ts`) | `log_admin_impersonation` (042, utökad i 123) | Plattformsadmin, prövad i databasen | `oppna` |

Raden bär kund (`tenant_id`), ruttens mall (`resurs`, t.ex. `/api/admin/tenants/{tenant_id}/kunddata`),
ett id ur sökvägen och anropets `X-Request-Id`. Den bär aldrig frågesträng, kropp, svar eller
nyckel. Approllerna `snajp_app` och `snajp_web` får inte skriva, ändra eller radera i tabellen;
bara de två säkerhetsdefinierade funktionerna skriver. Raderna gallras efter 365 dagar vid varje
skrivning, oberoende av `GALLRING_AKTIV`. Invariant: INV-SEC-013. Test:
`tests/invariants/test_inv_sec_013.py` och `snajp-support/tests/db/test_adminlogg.py` (jobbet
`databas`). Begränsningar: läsningar under ett kundbesök loggas som besöket, inte per anrop, och
om skrivningen faller går anropet igenom med en varning i api:ts logg.

**Övervakning.** `.github/workflows/overvakning.yml` hämtar produktionens startsida, `/health`
och `/health/ready` och skapar ett ärende med etiketten `driftlarm` vid avvikelse.
Larmkedjan är provad (ärende 53). Schemat gav en enda schemalagd körning
(2026-11-18 04:44 UTC) av omkring 60 förväntade (`bevis/github-2026-11-18.txt`). **Orsaken
(utredd 2026-11-18 natt):** GitHubs schemaläggare tappar de flesta schemalagda körningar i det
här repot: `synk.yml` (var tionde minut) fick 32 schemalagda körningar 2026-11-10–18, ungefär
fyra om dygnet, före och efter att repot blev privat. Syntax, standardgren, privat repo och
Actions-minuter är uteslutna (kommentaren i arbetsflödet). Från PR 84 körs övervakningen på två
scheman, efter varje körning av Verify och synk (`workflow_run`), och en dödmanskontroll i
`verify.yml` (`scripts/overvakning_dodman.sh`) öppnar ett ärende med etiketten
`overvakning-tyst` när övervakningen inte gått på tre timmar. Utan push, PR eller synk kan båda
utebli; en extern pingtjänst är det som löser det. Internlarmets variabler (`INTERNLARM_SMTP_*`)
är inte satta i någon miljö.

## 6. Tester som verifierar åtkomst och radering mot databasen

Från 2026-11-18 kör CI-jobbet `databas` (`verify.yml`) två tester till mot hela
migrationskedjan, och fäller jobbet om något av dem hoppas över:

- `snajp-support/tests/db/test_rls_isolation.py`: approllen `snajp_app`, scopad till en
  kund, får noll rader när den läser en annan kunds ärende direkt på id (INV-SEC-001).
  Testet skapar nu sina två kunder själv i en transaktion som rullas tillbaka; förut
  hoppades det över i varje miljö utan kunder, alltså i CI.
- `snajp-support/tests/db/test_gdpr_radera_db.py`: kör `scripts/gdpr_radera.py` som process
  mot en syntetisk person. Sökningen hittar varje tabell i skriptets karta i det riktiga
  schemat, `--export` lämnar ut personens rader, `--radera` avbryter vid fel bekräftelse,
  raderar vid rätt, behåller spärrlistans rad utan koppling och rör inte en annan person.

Det verifierar koden och schemat. Det verifierar inte att driftens databas har samma
policyer; det följer av att samma kedja körs där av `migrera.yml`.
