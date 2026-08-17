# Handoff 2026-08-17 — leads: nischtargeting, spärrar, priser

Gren `feature/plattform-fas1-7`, speglad till `development`. Sista commit
`16126a2`. Alla checkar gröna: pytest (587), invarianter (47), type-check,
docker-smoke, **Supabase Preview**, Vercel.

`main` är ORÖRD. Ingenting av det här är i produktion.

---

## Det som tog längst tid var inte det som stod i uppdraget

### Supabase-checken var två fel, inte ett

Den föregående sessionen registrerade repots versionsnummer (000–029) som
applicerade och stoppade `MIGRATIONS: FAILED`. Den fixen var riktig men halv:
liggaren behöll sina 31 tidsstämplade versioner, som saknade filer i
`supabase/migrations/`, och checken svarade i stället `Remote migration
versions not found in local migrations directory`.

**Fällan som nästan blev ett tredje fel:** grenen och produktionen har OLIKA
tidsstämplar för samma migration. 028 är `20260815224044` i produktionen men
`20260815213200` i grenen, och samma för 029 och avstämningen. Grenen har
dessutom en migration produktionen aldrig haft (`preview_snajp_app_password`).
Hade jag skrivit filer efter bara produktionens liggare hade checken förblivit
röd, och orsaken hade varit svår att se — filerna FANNS ju.

Samma katalog betjänar båda databaserna. Den måste alltså täcka unionen: 35
tidsstämplade filer, kontrollerat i båda riktningarna (ingen version utan fil,
ingen fil utan version).

### Tre ändringar fanns bara i produktionsdatabasen

De kördes via Management-API:t och existerade i ingen gren och ingen diff. En
återställning från noll hade tappat dem tyst. Två är säkerhetsrelevanta:

- `segment_ab_aggregate_lock_down` — `revoke execute ... from anon` på
  `segment_ab_aggregate()`. Utan den kan vem som helst med den publika nyckeln
  läsa segmentstatistiken via PostgREST.
- `018b_current_workspace_id_search_path` — låst `search_path` på funktionen
  varje workspace-scopad RLS-policy anropar.
- `snajp_pilot_categories` — kategoriomläggningen för hjärtstartarbranschen.

SQL:en är nu ordagrant återställd ur `schema_migrations.statements`.

**`20260815213243_preview_snajp_app_password.sql` är tom och ska förbli det.**
Originalet satte lösenordet på rollen `snajp_app`. Att återställa den SQL:en
hade committat ett databaslösenord i klartext.

### En produktionsbugg i support-agenten

`get_customer_history` sorterade bara på `created_at`, utan tiebreaker. Ärenden
som skapas i samma ögonblick ordnades godtyckligt, och `history[:3]` plockade
då FEL tre ärenden. Agenten läste samtalet i skakad ordning och trodde att
kunden frågat något innan de gjort det.

Mitt första försök bröt likheter på `id`. Det var fel: `uuid4` är slumpat, så
testet blev flakigt i stället för trasigt — sämre, eftersom det såg fixat ut.
MemoryStorage bryter nu på insättningsordning. Sviten kördes sex gånger i rad
för att bevisa determinism.

---

## Vad som byggdes

### DEL 1 — nischtargeting

`geo.py` (regioner som data), `sni.py`, utökad `icp.py`, `sources/`
(protokoll + CSV + två ärliga stubbar), `scoring.py`.

Två beslut värda att känna till:

**Postnumret avgör ensamt när det finns.** Ortnamn är fritext — "Västra
Frölunda" ligger i Göteborg men heter inte så. Okänd plats släpps aldrig
igenom: "vet inte" får inte betyda "släpp igenom" i ett urvalsfilter.

**Okänd uppgift behandlas OLIKA per kriterium.** Geografi och bransch
diskvalificerar vid okänt (finns i varje register — saknas de är posten
trasig). Anställda och omsättning gör det inte (saknas rutinmässigt även i bra
källor; Bolagsverket har dem inte alls). Ett KÄNT värde utanför spannet
diskvalificerar däremot.

### DEL 2 — sex spärrar

`send_guard.py`, ren logik utan I/O, 32 tester. **Den sitter i sändvägen** —
`scheduler.process_due_item` kör den direkt före `provider.send()`, den enda
punkt där mottagare, färdig text, klocka och tenanthistorik är kända samtidigt.
Fyra integrationstester bevisar att schemaläggaren faktiskt anropar den.

`DryRunMailer` skriver headers + body till fil. `auto_send` går inte att
aktivera utan ICP, produktbeskrivning och avsändardomän. Tom
produktbeskrivning avbryter körningen före första LLM-anropet.

### DEL 5 — priser

`lib/pricing.ts` håller allt; komponenten innehåller ingen prissiffra.
Duo-besparingen räknas fram ur paketpriserna. Verifierat i webbläsaren.

### Utöver uppdraget

`abuse_gate.py` — gränsen går vid vad uttrycket RIKTAS mot, inte hur hårt det
är. En arg kund får hjälp, inte en tillrättavisning.

---

## Vad som ÅTERSTÅR

### Blockerat på dig

**Adminkontot.** `snajpsupport@gmail.com` finns inte i `auth.users`. Registrera
det på `/login`. Migration `032` ger graden automatiskt vid bekräftad adress —
ingen andra körning behövs. Jag skapar inte konton och sätter inte lösenord.

**032 ligger bara på preview.** Ska `/admin` fungera i produktion måste
`development` mergas till `main`. Det är en produktionsdeploy.

### Inte påbörjat

- **DEL 3.4–3.5** — leads-körningen mot Göteborgsfixturen med `DryRunMailer`,
  de tre utkasten i sin helhet, och verifieringen att `agent_runs` skapas med
  `agent_type='leads_research'`. ICP-förslaget och produktdatan finns
  (`app/leads/profiles/livrustning.py`,
  `app/tenants/livrustning_business_context.py`), men körningen kräver riktiga
  LLM-anrop och är inte gjord. **`agent_runs`-raden är alltså inte bevisad mot
  vare sig Postgres eller MemoryStorage i den här sessionen.**
- **DEL 4** — `duo-demo`-tenanten, dashboarden med båda ytorna,
  404-verifieringen via `scripts/verify_inv_sec_010.sh`.
- **Menyerna** — kontaktuppgifter, manuell eskaleringsknapp som rapporterar
  till snajpsupport@gmail.com, språkval sv/en, GDPR-flik. `abuse_gate` är
  byggd men INTE inkopplad i support-agentens svarsväg.
- **`SEND_QUEUE_POLL_SECONDS`** är fortfarande osatt. Schemaläggaren startar
  alltså inte, och `get_send_provider()` returnerar `LoggingSendProvider` om
  inte `SNAJP_OUTBOX_DIR` sätts. Ingen kodväg når en riktig SMTP-server — den
  klassen finns inte.

### Öppna fynd

- `border-ink/12` genereras inte av Tailwind (opacitetsvärdet 12 ligger utanför
  skalan) och renderas som grå standardram på HELA marknadssajten, footern
  inkluderad. Verifierat med `getComputedStyle` och genomsökning av
  stylesheets.
- `fixtures/prospects-*.csv` är SYNTETISKA. Org.nummer gick inte att få
  lagligt, och `.example`-domäner gör ett oavsiktligt utskick omöjligt. Se
  `snajp-support/fixtures/README.md`.

---

## Kör så här

```bash
cd snajp-support && .venv/Scripts/python.exe -m pytest -q
```

```bash
snajp-support/.venv/Scripts/python.exe -m pytest tests/invariants -q
```

Båda krävs. Invariantsviten ligger i repots ROT och körs av ett eget
CI-jobb — den fångas inte av backendsvitens `pytest`, vilket jag lärde mig
genom att pusha rött.

---

# TILLÄGG — sessionens andra halva

Gren `feature/plattform-fas1-7`, speglad till `development`. Produktionen
deployad manuellt via `npx.cmd vercel deploy --prod --yes`.

## Tre fel som alla gömde sig bakom gröna checkar

Det här var sessionens egentliga innehåll, och de hänger ihop i karaktär:
**något såg friskt ut på den yta man tittade på, medan sanningen fanns
någon annanstans.**

### 1. Produktionsdeployen hade fallerat sedan maj

`VERCEL_PROJECT_ID` och `VERCEL_ORG_ID` pekade på det gamla `snipra`-projektet.
Varje körning dog på `Error: Project not found`. Verify-jobbet gick grönt hela
tiden, så commiten såg deployad ut — och `main` kunde vara i perfekt fas med
`development` utan att en rad av koden fanns live.

Jag felsökte en hel dag i kod som aldrig deployats. **Kontrollera
`gh run list --workflow "Deploy — Production"` INNAN du felsöker något som
"redan är ute".**

Hemligheterna är lagade. `workflow_dispatch` tillagd så deployen går att köra
om utan låtsas-commit.

### 2. Inloggningsloopen — proxyn tappade sessionscookies

`NextResponse.redirect()` bar inte med sig de roterade auth-cookies som
`getUser()` skrivit till `supabaseResponse`. Symptomen var TRE olika:
"Internal Server Error", "Sidan finns inte" på `/admin`, och inloggningar som
verkade lyckas utan att leda någonstans. En orsak.

Loggen avslöjade det: `/login → /dashboard → /onboarding → /login`.

**Varje ny redirect i `proxy.ts` måste gå via `redirectMedSession()`.** Annars
är loopen tillbaka, och den syns inte i något test.

### 3. RLS-policyn läste sin egen tabell

`platform_admins_self_read` gav `infinite recursion`. `isPlatformAdmin()` är
fail-closed och svalde felet, så `/admin` svarade bara 404 — adminraden fanns,
allt såg rätt ut, sidan fanns ändå inte.

**Läxan för alla tre: verifiera som `authenticated`, aldrig som `postgres`.**
MCP:n kör med BYPASSRLS och ser rätt även när appen inte gör det.

## Byggt i den här halvan

- **Menyn** på kundservice- och leadsytorna: kontakt, språkval sv/en, GDPR-flik,
  eskalering via mailto (ingen mejltransport finns — ett API-anrop hade sett ut
  att fungera och tyst inte nått fram)
- **`/demo`** — hela arbetsytan utan konto, elva sektioner, mot mockdata.
  Grinden på `/dashboard` är ORÖRD; att öppna den hade varit ett dataläckage
- **`/duo-demo`** och `DuoSummary` — duo-ytan, dold för enproduktskunder
- **Adminöversikten** med intäkt, kostnad, marginal och åtgärdslista, plus en
  rådgivare som RÄKNAR i stället för att fråga en modell
- **Affärskontext på fyra fält** (org.nr, webbplats, produkt, fokus) med
  Luhn-validering — det gamla formuläret hade åtta fält förifyllda med
  påhittade värden som gick att skicka in rakt av
- **USP:n** på förstasidan
- **`lib/tenants/snajp.ts`**, migrationerna 030–033 applicerade mot produktionen

## Kvar

- **`SNAJP_KEY_SNAJP`** — `python scripts/onboard_tenant.py --slug snajp --name "Snajp" --env production`
- **DEL 3.4** — leads-körningen med tre utkast och `agent_runs`-beviset. Kräver
  LLM-nyckel; `LLM_PROVIDER`, `DEEPSEEK_API_KEY` och `OPENAI_API_KEY` är alla
  tomma. **Fortfarande obevisad mot både Postgres och MemoryStorage.**
- **Inget JS-testramverk finns.** Ekonomimatematiken i `lib/admin/halsa.ts` är
  verifierad en gång med ett engångsskript, men inte bevakad. Införs vitest bör
  de fjorton kontrollerna bli permanenta.
- Admin saknar inställningsvy, per-kund-detalj och prognos
- `border-ink/12` genereras inte av Tailwind och renderas grå över hela
  marknadssajten
