# Synkflytten: databassynken och migrationerna från GitHub Actions till Railway

Utredning och plan. Skriven 2026-11-18. Bara läsning: inget i repot, hos Railway eller i databaserna är ändrat.

Märkning:
- **[V]** verifierat i fil (sökväg:rad). Repo = `C:\Users\Anton L\snipe-leads`.
- **[W]** verifierat i Railways officiella dokumentation (URL, hämtad 2026-11-17/18).
- **[G]** uppmätt i GitHubs körhistorik (`gh run list --workflow synk.yml --limit 200`, bara läsning, 2026-11-18).
- **[A]** antagande. Står det [A] ska det prövas innan steget byggs på det.

Railway-källor (alla hämtade 2026-11-17/18):
- W1 https://docs.railway.com/networking/private-networking/how-it-works
- W2 https://docs.railway.com/reference/private-networking
- W3 https://docs.railway.com/reference/cron-jobs
- W4 https://docs.railway.com/reference/tcp-proxy
- W5 https://docs.railway.com/databases/postgresql
- W6 https://docs.railway.com/reference/variables
- W7 https://docs.railway.com/guides/variables
- W8 https://docs.railway.com/guides/pre-deploy-command
- W9 https://docs.railway.com/reference/config-as-code
- W10 https://docs.railway.com/reference/pricing/plans
- W11 https://docs.railway.com/reference/static-outbound-ips
- W12 https://docs.railway.com/reference/pricing/faqs

---

## Kort svar

- **Privat nät gäller bara inom en miljö.** Railway: "Services in different environments (e.g., production vs staging) cannot communicate over the private network" [W1]. Även projekt är åtskilda: "Services in different projects cannot communicate over the private network" [W1]. "Each environment has its own isolated network" [W2].
- Följden: en synk mellan main och development kräver att **en** av databaserna nås över en publik port. Vilken avgörs av var synken körs.
- **Rekommendation: upplägg A.** Synken körs som cron-tjänst i miljön main. Den läser produktionen över det privata nätet med en ny läsroll och skriver till development över developments TCP-proxy. Migrationerna körs av en liten tjänst per miljö hos Railway. Därefter stängs produktionens port, `ENV_DEPLOY` tas bort och GitHub stryks som underbiträde för personuppgifter.
- **Fynd på vägen:** GitHub kör inte synken var tionde minut. Under 2026-11-10–17 blev det 3–4 körningar per dygn, och 2026-11-11–15 föll alla schemalagda körningar [G]. Synken hos Railway blir alltså både mer privat och betydligt tätare.

---

## 1. Vad synken gör

### Riktning och regler
- Efter första synken går den bara main → development. Main öppnas skrivskyddat (`mn.set_session(readonly=True)`) [V scripts/railway_synk.py:501-506].
- Läget läses ur `mirror_meta.lage`. Värdet `'envags'` betyder att första synken är gjord. Utan det vägrar `--apply` [V railway_synk.py:493-500].
- Per rad (nyckel = primärnyckeln) [V railway_synk.py:15-24, 246-265]:
  - finns i båda med olika innehåll: main vinner, raden skrivs till development;
  - finns bara i main: kopieras till development;
  - finns bara i development: står kvar. Undantag: main har loggat raderingen i `synk_raderingar` (migration 111). Då raderas raden i development.
- Inkommande mejl som bara finns i main men vars `provider_message_id` redan finns i development kopieras inte [V railway_synk.py:547-548].
- Bara kunder som finns i båda miljöerna synkas (`ss_tenants`-snittet) [V railway_synk.py:510-512].

### Tabeller (28 st.) och undantag
- `SYNK` i [V railway_synk.py:87-116]: `ss_customers`, `ss_customer_identifiers`, `ss_tickets`, `ss_conversations`, `ss_messages`, `ss_emails`, `ss_email_attachments`, `ss_classifications`, `ss_decision_log`, `ss_drafts`, `ss_human_reviews`, `ss_agent_metrics`, `customer_memory`, `agent_suggestions`, `prospects`, `prospect_sources`, `prospect_status_logg`, `outreach_threads`, `outreach_messages`, `send_queue`, `lead_lists`, `lead_list_items`, `lead_samtal`, `lead_anteckningar`, `lead_uppgifter`, `suppressions`, `leads_job_ledger`, `agent_runs`.
- Varje tabell har ett testvillkor. Provkörningar (`is_test`, prospekt med origin `test`/`example` och allt under dem) synkas aldrig [V railway_synk.py:77-116].
- Alla andra tabeller i databasen (t.ex. `ss_tenants`, kunskapsbaser, användare) synkas **inte** av det här skriptet [V railway_synk.py:87-116].

### Schemaskillnader
- Development får ligga före main. Egna kolumner i development hålls utanför jämförelsen och behåller sina värden [V railway_synk.py:26-34, 518-539; docs/BESLUT.md:403-437].
- Main före development, en kolumn bara i main eller en gemensam kolumn med olika typ stoppar synken [V railway_synk.py:459-466, 529-533].

### Skrivningen
- Development skrivs i replica-läge (`session_replication_role = replica`), så främmande nycklar och triggrar är av [V railway_synk.py:565-566, 584-585]. Det kräver superanvändare eller `GRANT SET ON PARAMETER` (Postgres 15+) [A, Postgres-kunskap; avbilden är `postgres-ssl:17` V scripts/railway_provision.py:27].
- **OBS:** raden körs mot *båda* anslutningarna, även main [V railway_synk.py:565-566]. Det spelar roll för en läsroll i main (se plan steg 2).
- Partier om 100 rader: radera + infoga ur JSON (`jsonb_populate_recordset`), savepoint per parti, rad för rad om partiet faller [V railway_synk.py:268-328, 347-384].
- Krock på unikt index i development: development-raden tas bort, main-raden skrivs [V railway_synk.py:387-430].
- Genererade kolumner skrivs inte [V railway_synk.py:287-294].
- Development: `alter table mirror_meta add column if not exists lage/synkad_at` vid varje `--apply`, och sist `update mirror_meta set lage='envags', synkad_at=now()` [V railway_synk.py:489-492, 586]. Kräver ägare eller superanvändare.
- Commit sker först efter alla tabeller. Fel i en rad ger `HOPPAD:` och slutkod 1 [V railway_synk.py:587-592].
- Första synken (`--forsta`) sparar en kopia i schemat `synk_kopia_<tid>` i båda databaserna och skriver till main [V railway_synk.py:47-50, 558-562]. Den är gjord 2026-10-17 och ska inte köras igen [V HANDOFF-2026-10-17-RELEASE-OCH-SYNK.md:7].

### Spärrar som markerar spegeln
- Development måste ha `mirror_meta` med `environment = 'development'` [V railway_synk.py:444-449].
- Main får inte ha någon rad i `mirror_meta` [V railway_synk.py:450-454; DEPLOY.md:176-177].
- Båda måste ha `synk_raderingar` [V railway_synk.py:470-473].
- `mirror_meta.lage = 'envags'` gör också att development inte skickar utskick (`scheduler.utskick_bara_i_main`) [V snajp-support/app/leads/scheduler.py:670-672; docs/BESLUT.md:2071-2079].

### Anslutningar och rättigheter
- Båda anslutningarna byggs av `railway_migrate.dsn()`: `postgresql://postgres:<lösen>@<host>:<port>/railway`, alltså superanvändaren `postgres` [V scripts/railway_migrate.py:54-67].
- Värdena läses ur `.env.deploy` via `env_read()`, som bara läser filen och inte miljövariabler [V scripts/railway_provision.py:72-80].
- Variabler: `RAILWAY_MAIN_PG_PASSWORD`, `RAILWAY_MAIN_PG_HOST`, `RAILWAY_MAIN_PG_PORT`, `RAILWAY_DEVELOPMENT_PG_PASSWORD`, `RAILWAY_DEVELOPMENT_PG_HOST`, `RAILWAY_DEVELOPMENT_PG_PORT`. För main finns reserv `RAILWAY_PG_*` [V railway_migrate.py:61-66].
- Värdarna är TCP-proxyerna, skapade av provisioneringen just för att kedjan körs utifrån [V railway_provision.py:303-320].
- Behov i **main** (envägsläget): bara läsning av de 28 tabellerna, `ss_tenants`, `ss_emails.provider_message_id`, `synk_raderingar`, `mirror_meta` (om den finns), `supabase_migrations.schema_migrations` och systemkatalogen. Tabellerna har RLS [A: att RLS gäller alla 28; DEPLOY.md:116-117 säger att RLS används], så en läsroll behöver `BYPASSRLS`.
- Behov i **development**: skriva i de 28 tabellerna, ändra `mirror_meta`, replica-läge. I praktiken superanvändare.

### Frekvens och körtid
- Avsett: var tionde minut, en körning åt gången, 15 minuters tak [V .github/workflows/synk.yml:17, 20-22, 27].
- Uppmätt [G]: 197 körningar 2026-10-10–11-17. Per dygn 3–10 körningar, inte 144. Lyckade körningar: median 117 s, 90:e percentilen 243 s, max 656 s, inräknat GitHubs uppstart (checkout, Python, pip). 2026-11-11–15 föll alla schemalagda körningar på 12–31 s, alltså direkt i spärren (schemaskillnaden som beskrivs i BESLUT 2026-11-16 [V docs/BESLUT.md:446-452]).
- Före indexfixen 2026-10-30 hann en synk efter en veckas uppehåll inte klart på 15 minuter [V railway_synk.py:136-141].

### Vid fel
- Spärrarna avslutar med `sys.exit("AVBRYT: …")` före första skrivningen [V railway_synk.py:444-473, 496-499, 529-536].
- En rad som inte går att skriva hoppas över och rapporteras. Slutkoden blir 1, jobbet rött [V railway_synk.py:589-592; synk.yml:42-44 med `pipefail`].
- Loggen laddas upp som artefakt i GitHub i 14 dagar [V synk.yml:45-50]. Den innehåller antal per tabell och `HOPPAD: <tabell> <nyckel>: <första raden av felet>` [V railway_synk.py:384, 590]. Nycklarna är id:n (pseudonyma uppgifter) [A: att felens första rad aldrig bär värden].

### Vad workflowerna mer kräver ur `.env.deploy`
- `synk.yml`: hela filen skrivs ur hemligheten `ENV_DEPLOY` [V synk.yml:34-39]. Skriptet läser bara de sex `RAILWAY_*_PG_*` ovan. `railway.py` importeras via `railway_provision` men `RAILWAY_TOKEN` läses bara vid ett API-anrop, som synken aldrig gör [V scripts/railway.py:45-55, 58-79].
- `migrera.yml`: samma hemlighet i båda jobben [V .github/workflows/migrera.yml:78-81, 132-135]. Jobbet `kör migrationerna` läser de tre variablerna för sin miljö; `releasens migrationer` läser alla sex [V migrera.yml:86-98, 140-141].
- `verify.yml` och `indexnow.yml` använder inga databashemligheter [V grep efter `secrets.` gav inga träffar].

---

## 2. Nätet

### Fakta
- Privat nät per miljö, aldrig mellan miljöer eller projekt [W1, W2]. WireGuard-nätet omfattar "all services within an environment" [W1].
- Privat nät finns bara vid körning, inte under bygget [W1]. Förkommandot (pre-deploy) körs "within your private network" [W8].
- Databaser är privata som standard. Publik åtkomst skapar en TCP-proxy, och trafiken genom den debiteras som utgående trafik [W5].
- TCP-proxyns dokumentation nämner ingen åtkomstlista för käll-IP [W4]. Det betyder inte att det säkert saknas, men inget går att bygga på [A].
- Fasta utgående IP-adresser finns bara på Pro [W11]. Projektet ligger på Hobby: säkerhetskopior vägrades med "only available for Pro workspaces" [V D:\comp-compliance\evidence\railway-backup-paslagen-2026-11-17.txt]; volymtaket 5 000 MB anges som Hobbys tak [V docs/BESLUT.md:2082-2084].
- Referensvariabler: `${{Tjänst.VAR}}` och `${{shared.VAR}}` [W6]. Delade variabler sätts per miljö [W7]. Dokumentationen säger inget om referenser till en annan miljö [W6, W7], så en referens från main till developments Postgres går inte att räkna med [A]. Värdet för den andra miljön blir en vanlig (förseglad) variabel.
- Samma privata värdnamn `postgres.railway.internal` används i båda miljöerna och pekar på olika databaser [V evidence/railway-konfiguration-2026-11-17-efter.txt, DATABASE_URL i development/api och main/api]. Det bekräftar att namnet löses inom miljön.
- Båda Postgres-tjänsterna har TCP-proxy påslagen i dag (`RAILWAY_TCP_PROXY_DOMAIN/PORT` satta) [V evidence/railway-konfiguration-2026-11-17-efter.txt, avsnitten development/Postgres och main/Postgres].

### Upplägg A: synken i main, skriver till development över developments port
- Läser produktionen privat. Produktionens port kan stängas.
- Developments port står kvar öppen, skyddad av lösenord (och TLS om den krävs i anslutningen).
- Data lämnar aldrig Railway som leverantör. Sträckan mellan tjänsten i main och developments proxy går dock via Railways publika kant, inte det privata nätet [A: att trafiken inte går ut på öppet internet längre än till Railways kant; inget i [W4] beskriver vägen]. TLS ska därför krävas.
- Tjänsten i main bär developments superlösenord. En intrång i den tjänsten når development. Development bär samma data som main, så det är ingen ny exponering av persondata, men det är en ny väg in i development.
- **Går sönder:** allt som når produktionen utifrån (se avsnitt 7). Developments utvecklarskript fortsätter fungera.
- **Bedömning:** bästa upplägget som går att bygga nu. Produktionen blir onåbar utifrån, GitHub försvinner ur persondatakedjan, och synken blir tätare.

### Upplägg B: synken i development, läser produktionen över produktionens port
- Skriver privat till development. Produktionens port måste stå kvar.
- Ingen vinst för produktionen. Enda vinsten mot i dag är att GitHub försvinner ur kedjan.
- **Bedömning:** sämre än A på alla punkter som rör produktionen. Avråds.

### Upplägg C: ingen databas med publik port
Varianterna, ärligt bedömda:

1. **Development som tjänster i miljön main** (web-dev, api-dev, Postgres-dev i samma miljö). Allt blir privat. Men: development och produktion delar då nät, så en sårbarhet i dev-tjänsterna når produktionens databas privat. `RAILWAY_ENVIRONMENT_NAME` blir `main` för dev-tjänsterna, och koden avgör miljö ur den (`aktiv_miljo`) [V snajp-support/app/config.py:155-160, 608]. Grenstyrning, variabler och värdnamn måste göras om. Stor risk för att dev-tjänster beter sig som produktion. **Avråds.**
2. **Eget projekt för synken.** Projekt är också åtskilda [W1]. **Löser inget.**
3. **Logisk replikering i Postgres.** Prenumeranten ansluter till utgivaren, så produktionen måste nås utifrån [A, Postgres-kunskap]. Den följer dessutom inte synkens regler (provkörningar, development före main). **Löser inget.**
4. **Proxytjänst med åtkomstlista.** Kräver kända käll-IP. Railways utgående IP är bara fasta på Pro [W11], och TCP-proxyn anger ingen åtkomstlista [W4]. Går på Pro med en egen TCP-proxy-tjänst (t.ex. HAProxy) som filtrerar på mains fasta IP [A]. Ger en port som bara mains tjänst kommer igenom. Kostar Pro-planen (20 USD/mån inkl. 20 USD förbrukning, mot Hobby 5/5 [W10]).
5. **HTTPS-relä i appen.** Synken delas i två: en läsände i main (en skyddad, skrivskyddad endpoint på main-api eller en egen tjänst) och en skrivände i development som hämtar. Mönstret finns redan i Flytta till main (HMAC-signerade paket över HTTPS) [V DEPLOY.md:733-738]. Ingen databas har publik port. Men produktionen exponerar då en endpoint som lämnar ut alla synkade rader mot en nyckel: risken flyttas från databasporten till appen. Den blir smalare (bara läsning, bara de 28 tabellerna, ingen superanvändare). Kräver omskrivning av `planera`/`rader`/`skriv` till ett protokoll med hashlistor och radhämtning per parti. Uppskattat 2–4 dagars arbete [A].
6. **WireGuard/Tailscale-sidovagn** i båda miljöerna. Tekniskt möjligt [A], men ny leverantör (koordineringstjänst) i kedjan. **Avråds** i ett compliancearbete som ska minska leverantörer.

**Slutsats C:** variant 5 är den enda som både stänger alla portar och håller miljöerna åtskilda. Den är en bra fas 2 efter A, om Anton vill stänga även developments port. Variant 4 är ett alternativ om projektet ändå går till Pro.

---

## 3. Körform hos Railway

| | Cron-tjänst | Loop i api (main) | Egen alltid-på-tjänst |
|---|---|---|---|
| Överlapp | Railway hoppar över nästa start om förra körningen är aktiv [W3] | Egen låsning krävs | Egen låsning krävs |
| Hemligheter | Bara i synktjänsten | Developments superlösenord hamnar i produktionens api | Bara i tjänsten |
| Avbild | Egen, liten | psycopg2 + skript in i api:s avbild; api-avbilden har i dag varken `scripts/` eller psycopg2 [V snajp-support/Dockerfile.dockerignore:12-15; snajp-support/requirements.txt] | Egen |
| Kostnad | Bara när den kör [A: dokumenterat bara som "save resources between executions" W3] | Ingen ny tjänst | Minne dygnet runt (~0,1 GB ≈ 1 USD/mån [W10, A om minnet]) |
| Fel | Nollskild slutkod syns som misslyckad körning [A: W3 beskriver inte status] | Loggrad i api | Loggrad |
| Kortaste intervall | 5 minuter [W3] | Fritt | Fritt |

- Schemat är i UTC [W3]. Tjänsten ska avsluta sig och stänga sina anslutningar [W3]. Skriptet gör det redan genom att returnera från `main()` [V railway_synk.py:595-596]; anslutningarna stängs vid processens slut.
- **Val: cron-tjänst.** Den håller produktionens api fri från developments lösenord, ärver Railways spärr mot överlapp och kostar nästan inget.

### Insyn (projektregeln om att följa flödet)
- I dag syns `synkad_at` och `lage` via `GET /api/admin/flytt/status` i development [V snajp-support/app/api/admin_flytt.py:266-276; storage/postgres.py:4529-4542]. Bara lyckade körningar sätter tiden [V railway_synk.py:586].
- Förslag: synken skriver i development även `senaste_forsok_at`, `senaste_utfall` (`ok`, `hoppade:<n>`, `avbruten:<skäl>`) och antal per tabell (en `jsonb`) i `mirror_meta`. Ingen persondata, bara antal och spärrtext. Panelen Byt kund / Flytta till main visar senaste körning, utfall och "senast lyckad för X min sedan", röd efter 60 minuter.
- Panelen är bara för plattformsadmin i development [V DEPLOY.md:731-733]. Synken startas inte av någon kund, så förloppet hör hemma där. Är Anton osäker på kundsynlighet ska han tillfrågas (projektregeln).
- Larm: Railway visar misslyckade körningar [A]. Om Railway mejlar vid misslyckad cron är inte verifierat [A; W3 säger inget]. Därför en egen kontroll: api i development loggar ett fel en gång i timmen när `synkad_at` är äldre än 60 minuter. Det stänger luckan från 2026-11-10–16, då synken stod röd i sex dagar utan att någon såg det [V docs/BESLUT.md:446-452].

### Hemligheter utan `.env.deploy`
- Tjänsten `synk` i main får:
  - `SYNK_MAIN_PG_URL = postgresql://synk_las:${{Postgres.SYNK_LAS_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/railway` (referens inom miljön [W6]; lösenordet som variabel på Postgres-tjänsten eller som förseglad variabel direkt på `synk`).
  - `SYNK_DEVELOPMENT_PG_URL = postgresql://postgres:<lösen>@<developments proxydomän>:<port>/railway?sslmode=require` som **förseglad** variabel [W7: förseglade värden syns aldrig i UI eller API]. Ingen referens över miljögränsen [A, W6/W7 tiger].
- Variabelnamn med `RAILWAY_`-prefix undviks: Railway sätter egna variabler med det prefixet [W6]. Om egna namn med prefixet är tillåtna är inte verifierat [A].

---

## 4. Migrationerna

### I dag
- Push till `development`/`main` som rör `supabase/migrations/**` eller `railway/000_auth_compat.sql` kör kedjan mot samma miljö [V migrera.yml:32-38, 58-100].
- PR mot `main` får kontrollen `releasens migrationer`: läser båda liggarna, listar vad main skulle få och fäller PR:en om development har okörda [V migrera.yml:119-153].
- Migrationerna kör SQL inne i databasen. Persondata passerar inte GitHub, utom möjligen i felmeddelanden [V railway_migrate.py:136-140, felet kapas till 400 tecken]. Men workflowen bär superlösenorden och kräver båda portarna.

### Kan produktionens port stängas om bara synken flyttas?
**Nej.** Jobbet `kör migrationerna` mot main och kontrollen `releasens migrationer` når mains databas utifrån [V migrera.yml:86-98, 141]. Båda måste göras om först.

### Alternativ hos Railway
1. **Förkommando i api** (`preDeployCommand`) [W8, W9]. Körs i det privata nätet, med api:s variabler, och stoppar deployen om det faller [W8]. Det ger en riktig grind (schemat före koden). Nackdel: api måste bära superlösenordet och avbilden migrationerna. Anton valde bort just det 2026-11-16 [V docs/BESLUT.md:453-456]. Kräver Antons nya beslut.
2. **Egen tjänst `migrera` per miljö (rekommenderas).** Samma avbild som synken. Startkommando `python scripts/railway_migrate.py --env <miljö> --apply`, omstart `NEVER` [W9], deploy från samma gren som miljön. Bygger om bara när migrationskatalogen ändras (`watchPatterns` [W9]). Ger samma ordning som i dag: "en ordning och ingen grind" [V DEPLOY.md:94-97]. Superlösenordet finns bara i den tjänsten.
   - [A] Att en tjänst som avslutar sig med kod 0 och omstart `NEVER` står som avslutad och inte startas om. Prövas i development först.
   - [A] Att pre-deploy-containern och vanlig körning har samma nätåtkomst; spelar ingen roll för alternativ 2.
3. **Förkommando på tjänsten `migrera`** i stället för startkommando: ger samma sak men med Railways "deployen fortsätter inte"-semantik [W8]. Ett val i bygget.

### PR-kontrollen "releasens migrationer"
- **Vad releasen bär** kan räknas ur git utan databas: filer i `supabase/migrations/` som finns i PR:ens gren men inte i `main`. Det ersätter main-liggarens lista [A: att main aldrig fått en migration utanför git; liggarregeln i DEPLOY.md:713-724 talar för det].
- **"Development har okörda"** kräver developments liggare. Förslag: en ny endpoint `GET /api/drift/schema` i api som returnerar de körda versionerna (bara filnamn, ingen persondata), skyddad av en egen smal nyckel `SCHEMA_LASNYCKEL`. GitHub anropar developments och mains api över HTTPS. Api-rollen `snajp_app` behöver `select` på `supabase_migrations.schema_migrations` (en additiv migration).
- Förlust: ingen funktionell. Kontrollen blir en HTTPS-fråga i stället för en databasanslutning. Torrkörningen "vad väntar" för hand (workflow_dispatch) ersätts av samma endpoint eller av tjänstens logg.

---

## 5. Den stora hemligheten `ENV_DEPLOY`

| Workflow / jobb | Variabler som faktiskt läses |
|---|---|
| `synk.yml` | `RAILWAY_MAIN_PG_PASSWORD/HOST/PORT`, `RAILWAY_DEVELOPMENT_PG_PASSWORD/HOST/PORT` (reserv `RAILWAY_PG_*` för main) |
| `migrera.yml` / `kör migrationerna` | De tre `RAILWAY_<MILJÖ>_PG_*` för vald miljö |
| `migrera.yml` / `releasens migrationer` | Alla sex |
| `verify.yml`, `indexnow.yml` | Inga |

[V railway_migrate.py:54-67; railway_provision.py:72-80; workflows enligt avsnitt 1.]

- **Snabb vinst (före flytten):** ersätt `ENV_DEPLOY` med sex smala hemligheter. Kodändring: `env_read()` faller tillbaka på `os.environ` för nycklar som saknas i filen (eller `dsn()` läser miljön först). Workflowerna sätter `env:` per steg i stället för att skriva filen. Mains tre hemligheter läggs i en GitHub-miljö `main` med Antons godkännande som skydd [A: att kontot tillåter skyddade miljöer på privat repo med nuvarande plan].
- **Efter flytten:** inga databashemligheter i GitHub. Kvar blir bara `SCHEMA_LASNYCKEL`. `ENV_DEPLOY` raderas.
- **Rotation:** allt som legat i `ENV_DEPLOY` har funnits hos GitHub. Minst databaslösenorden (`postgres` i båda miljöerna) och `RAILWAY_TOKEN` bör roteras efter borttagningen. Vilka fler nycklar filen bär går inte att se utan att läsa den (förbjudet här). Anton avgör omfattningen.

---

## 6. Rekommendation och plan

### Rekommenderat upplägg
Upplägg A med cron. Synken körs var tionde minut i miljön main, läser produktionen privat som en skrivskyddad roll och skriver till development över developments port med TLS. Migrationerna körs av en tjänst per miljö hos Railway, och PR-kontrollen läser liggarna över HTTPS, så att ingen databas nås från GitHub. Developments port står kvar tills vidare; variant C5 (HTTPS-relä) kan stänga även den i en senare fas.

### Plan

Varje steg: **vad**, **typ** (Kod / Railway / Ägare), **verifiering**, **backning**.

**Steg 0. Beslut och förberedelse** — Ägare (Anton)
- Godkänn upplägg A, cron, och att developments port står kvar. Skriv beslutet i `docs/BESLUT.md` med resonemanget (projektregel).
- Verifiering: beslutet står i BESLUT.md.
- Backning: inget att backa.

**Steg 1. Smala hemligheter i GitHub (snabb vinst, oberoende av resten)** — Kod + Ägare
- Kod: `scripts/railway_provision.py:env_read()` läser `os.environ` för nycklar som saknas i filen. `synk.yml` och `migrera.yml` sätter de sex `RAILWAY_*_PG_*` som `env:` ur sex hemligheter och skriver ingen `.env.deploy`. Test: `tests/test_railway_synk.py` eller nytt test som visar att `dsn()` hittar värden ur miljön och att `--env development` aldrig får mains värden.
- Ägare: lägg in de sex hemligheterna (via `api-key-setup`-mönstret, värdet aldrig i chatten).
- Verifiering: en manuell körning av `synk` (workflow_dispatch) och en torrkörning av `migrera` går grönt.
- Backning: återställ workflowerna; `ENV_DEPLOY` finns kvar tills steg 12.

**Steg 2. Synkskriptet klarar en läsroll och miljövariabler** — Kod
- `railway_synk.py`:
  - `dsn` läser `SYNK_MAIN_PG_URL` / `SYNK_DEVELOPMENT_PG_URL` om de finns, annars som förut.
  - `set session_replication_role` körs mot main bara när `forsta` är sant (i dag mot båda, rad 565-566 och 584-585).
  - Ny spärr: när `RAILWAY_ENVIRONMENT_NAME` finns ska den vara `main`; developments värd får inte sluta på `.railway.internal` (inom main pekar det namnet på produktionen). Den befintliga `mirror_meta`-spärren fångar redan felkopplingen [V rad 444-454], men det här stoppar före första frågan.
  - Rådgivande lås: `pg_try_advisory_lock(<konstant>)` på development-anslutningen. Upptaget → skriv "en annan synk pågår" och avsluta med 0. Behövs under parallellkörningen (steg 6) när GitHub och Railway körs samtidigt.
  - Insyn: skriv `senaste_forsok_at`, `senaste_utfall` och antal per tabell i `mirror_meta` i development, även när körningen avbryts efter att anslutningen öppnats (`try/finally` med egen transaktion).
- Tester: utöka `tests/test_railway_synk.py` (ren logik: spärren mot `.railway.internal`, att replica-läget inte sätts på main utanför första synken) och `snajp-support/tests/invariants/test_inv_data_003.py` om den laddar skriptet [V test_inv_data_003.py:68]. Kör hela backendsviten.
- Verifiering: torrkörning för hand från utvecklardatorn mot båda databaserna ger samma tabell som förut.
- Backning: git revert.

**Steg 3. Läsrollen i main** — Kod (migration)
- Ny additiv, idempotent migration: `create role synk_las login bypassrls` om den saknas, `grant usage` på `public` och `supabase_migrations`, `grant select` på de 28 tabellerna, `ss_tenants`, `synk_raderingar`, `mirror_meta` (villkorat), `schema_migrations`. `alter role synk_las set default_transaction_read_only = on`. Lösenordet sätts inte i migrationen (det hamnar annars i git): ägaren sätter det med `alter role … password` via `migrera`-tjänsten eller ett engångsskript som läser värdet ur stdin.
- Samma migration ger `snajp_app` `select` på `supabase_migrations.schema_migrations` (för steg 9).
- Verifiering: som `synk_las` går `select count(*)` på varje tabell, och `insert` faller med "read-only transaction".
- Backning: `drop role synk_las` (additivt, inget annat beror på rollen).

**Steg 4. Avbild för driftjobben** — Kod
- Ny `railway/Dockerfile.drift` med `python:3.12-slim` (samma ECR-spegel som api [V snajp-support/Dockerfile:4]), `pip install psycopg2-binary`, och `COPY scripts/railway_synk.py scripts/railway_migrate.py scripts/railway_provision.py scripts/railway.py`, `supabase/migrations/`, `railway/000_auth_compat.sql`. Egen allowlist `railway/Dockerfile.drift.dockerignore` (BuildKit läser `<Dockerfile>.dockerignore` först [V .dockerignore:3-5]). `docs/` utesluts redan av rotens ignorefil [V .dockerignore], så `supabase/` och `scripts/` måste släppas in uttryckligen.
- Inga hemligheter i avbilden.
- Test: `verify.yml` får ett byggsteg för avbilden (som docker-smoke för api).
- Verifiering: avbilden bygger i CI; `python scripts/railway_synk.py --help` går i containern.
- Backning: ta bort filerna.

**Steg 5. Tjänsten `synk` i main, torrkörning** — Railway (Ägare eller agent via `railway_provision.py`-mönstret)
- Ny tjänst `synk` i miljön **main**, region Amsterdam (`ams`, samma som övriga [V evidence/railway-regioner-2026-11-17-efter.txt]). Källa: repot, gren `main`. Bygg: `railway/Dockerfile.drift`. Ingen publik domän.
- Variabler: `SYNK_MAIN_PG_URL` (referens, se avsnitt 3), `SYNK_DEVELOPMENT_PG_URL` (förseglad, `sslmode=require`).
- Startkommando: `python scripts/railway_synk.py` (utan `--apply`). Schema `*/10 * * * *` [W3, W9]. Omstart: `NEVER`.
- Obs: tjänsten måste nå `main`-grenen innan den kan byggas därifrån, alltså kräver steg 2–4 en release. Alternativt byggs den tillfälligt från `development` [A: att en tjänst i main kan ha annan gren; triggern sätts per tjänst och miljö V railway_provision.py:323].
- Verifiering: loggen visar `läge: main → development` och tabellen per körning, utan `VARNING`. Körtid noteras.
- Backning: ta bort tjänsten. GitHub-synken går oförändrad.

**Steg 6. Parallellkörning med skrivning, minst 24 timmar** — Railway
- Startkommandot blir `python scripts/railway_synk.py --apply`. GitHub-synken går kvar. Det rådgivande låset (steg 2) gör att bara en skriver åt gången.
- Verifiering under minst 24 h: varje Railway-körning slutar `Synk klar. 0 rader hoppades över.`; `mirror_meta.synkad_at` är aldrig äldre än 20 minuter; räkning per tabell (ej test) är lika i main och development vid ett stickprov (som 2026-10-17 [V HANDOFF-2026-10-17-RELEASE-OCH-SYNK.md:7]); inga utskick från development.
- Backning: tillbaka till torrkörning eller ta bort tjänsten. GitHub-synken bär hela tiden.

**Steg 7. Stäng av GitHub-synken** — Kod
- Ta bort `schedule` i `synk.yml` (behåll `workflow_dispatch` en vecka som reserv), därefter hela filen.
- Verifiering: inga nya schemalagda körningar i Actions; Railway-synken fortsätter.
- Backning: återställ `schedule`.

**Steg 8. Tjänsten `migrera` per miljö** — Railway + Kod
- En tjänst `migrera` i development (gren `development`) och en i main (gren `main`), avbild `railway/Dockerfile.drift`, Amsterdam, ingen domän, omstart `NEVER`, `watchPatterns: ["supabase/migrations/**", "railway/000_auth_compat.sql"]` [W9].
- Variabel: `SYNK_<MILJÖ>_PG_URL`-motsvarighet med superanvändaren över privat nät, `postgres:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/railway` [W6]. Kod: `railway_migrate.dsn` läser den (samma ändring som steg 2).
- Startkommando: `python scripts/railway_migrate.py --env <miljö> --apply && python scripts/railway_migrate.py --env <miljö>` (kontrollen efteråt som i workflowen [V migrera.yml:93-100]).
- Ordning: development först. Låt `migrera.yml` gå kvar parallellt; kedjan är idempotent [V railway_migrate.py:106-113], så två körningar efter varandra är ofarliga. Samtidiga körningar kan krocka [A]; lägg samma rådgivande lås i `railway_migrate.py`.
- Verifiering: en additiv provmigration (t.ex. en kommentar eller `create … if not exists`) går i development via tjänsten; loggen visar `+ <version>`; liggaren har raden; sedan samma vid nästa release i main.
- Backning: ta bort tjänsterna; `migrera.yml` finns kvar.

**Steg 9. PR-kontrollen utan databas** — Kod
- `GET /api/drift/schema` i api (nyckeln `SCHEMA_LASNYCKEL`, satt i båda miljöerna, inte masternyckeln). Returnerar versionslistan.
- `migrera.yml`: jobbet `kör migrationerna` tas bort. `releasens migrationer` räknar releasens filer ur git och frågar developments endpoint om okörda. Inga databashemligheter.
- Tester: endpointens behörighet (401 utan nyckel), att svaret bara bär versioner.
- Verifiering: en PR mot `main` får kontrollen grön/röd som förut.
- Backning: återställ workflowen.

**Steg 10. Insyn och larm** — Kod
- Panelen (Byt kund › Flytta till main, `components/admin/FlyttTillMain.tsx` / `BytKund.tsx`) visar senaste körning, utfall och ålder. Tvåspråkigt via `lib/i18n.tsx` (projektregel, INV-COPY-001).
- Api i development loggar fel när `synkad_at` är äldre än 60 minuter (en gång i timmen).
- Verifiering: stoppa `synk`-tjänsten en timme i development-läget av provet; panelen blir röd och loggen visar felet.
- Backning: git revert.

**Steg 11. Stäng produktionsdatabasens publika port** — Ägare
- Först: gå igenom avsnitt 7 och bekräfta att inget som måste fungera når main utifrån. Uppdatera `railway_provision.py` så att den inte skapar en ny proxy när `RAILWAY_MAIN_PG_HOST` saknas [V railway_provision.py:306-320]; annars öppnar nästa `--apply` porten igen.
- Ta bort TCP-proxyn på Postgres i main (Settings › Networking). Hur den tas bort beskrivs inte i [W4, W5]; prövas i development på en kopia först eller via GraphQL `tcpProxyDelete` [A].
- Verifiering: `RAILWAY_TCP_PROXY_DOMAIN` saknas på main/Postgres i en ny bevisfil (`railway-konfiguration-<datum>.txt`); en anslutning till den gamla proxyadressen nekas; web, api och synk fungerar (hälsokontroller gröna, synken nästa varv grön).
- Backning: lägg till publik åtkomst igen [W5]. Ny proxyadress och port kan bli andra än förut [A]; `.env.deploy` uppdateras då.

**Steg 12. Ta bort `ENV_DEPLOY` och rotera** — Ägare
- Radera repo-hemligheten `ENV_DEPLOY` och de sex smala från steg 1. Rotera `postgres`-lösenorden i båda miljöerna och `RAILWAY_TOKEN` (och det mer som filen bar, Antons bedömning). Uppdatera de förseglade variablerna i `synk`/`migrera`.
- Verifiering: `gh secret list` visar bara `SCHEMA_LASNYCKEL`; synk och migrera går gröna efter rotationen.
- Backning: inte meningsfull för raderingen; rotationen kan inte ångras men är ofarlig.

**Steg 13. Dokumenten** — Kod (dokument)
- Stryk GitHub som underbiträde för personuppgifter: `docs/dpia_supportagenten.md` (raden "GitHub (Microsoft), Actions" och avsnittet kring rad 438-441 [V dpia_supportagenten.md:103, 114, 438-441]), `docs/JURIDIK_ATGARDER.md` (nämner GitHub [V grep]). `docs/registerforteckning.md`, `lib/bolag.ts`, integritetspolicyn och pilotavtalet gav ingen träff på "GitHub" [V grep 2026-11-18]; kontrollera ändå att underbiträdeslistan där inte behöver en rad om att GitHub inte behandlar persondata. GitHub står kvar som leverantör av kodförråd och CI utan persondata.
- Uppdatera `DEPLOY.md` (migrationer, synk, att mains port är stängd), `CLAUDE.md` (migrationsavsnittet), `ARCHITECTURE_INVARIANTS.md` INV-DATA-003 och `docs/BESLUT.md` med beslutet. Ta bort det inaktuella avsnittet om `spegla-dev.yml` i DEPLOY.md (workflowen finns inte [V .github/workflows]).
- Verifiering: `grep -i "ENV_DEPLOY\|synk.yml"` i docs visar bara historik.
- Backning: git revert.

### Kostnad hos Railway
Priser [W10]: RAM 10 USD/GB/mån, CPU 20 USD/vCPU/mån, utgående trafik 0,05 USD/GB. Antaganden [A] står inom parentes.

- `synk` (144 körningar/dygn, ~2 min per körning, 0,3 GB RAM, 0,5 vCPU medan den kör): ~144 h/mån aktiv → RAM ≈ 0,6 USD, CPU ≈ 2,0 USD.
- Trafik över developments proxy (hashlistor ur development varje körning; ~100 000 rader × ~100 byte ≈ 10 MB per körning): ≈ 43 GB/mån ≈ 2,2 USD. Mains del av samma trafik går i dag ut till GitHub och försvinner, så nettot blir ungefär hälften [A].
- `migrera` × 2: några sekunder per release, under 0,1 USD.
- **Totalt: ungefär 3–5 USD i månaden extra**, före avräkning av den trafik som i dag går till GitHub. Hobby-planens fasta 5 USD inkluderar 5 USD förbrukning [W10]; projektet ligger sannolikt redan över den [A], så tillägget betalas fullt.
- Priset är per minut [W10]. Om Railway debiterar en minsta tid per cronstart framgår inte [W12 tiger; A].

### Tidsåtgång
- Kod (steg 1–4, 9, 10, 13): 1,5–2 arbetsdagar.
- Railway och ägarens handgrepp (steg 5, 8, 11, 12): 2–3 timmar.
- Väntetid: 24 h torrkörning (steg 5) + minst 24 h parallellkörning (steg 6) + en release till main (för tjänsterna i main och `migrera` i main).
- **Kalendertid: ungefär 4–6 dagar**, styrd av releasen.

---

## 7. Risker

### Synken skriver åt fel håll
- Main öppnas skrivskyddat utanför första synken [V railway_synk.py:501-506]. Läsrollen `synk_las` gör det mekaniskt omöjligt även om koden ändras.
- Spärrarna på `mirror_meta` stoppar en förväxling av databaserna [V railway_synk.py:444-454]. Inom miljön main pekar `postgres.railway.internal` på produktionen: läggs det namnet av misstag i developments variabel möter synken produktionen som "development", hittar ingen markör och avbryter. Steg 2 lägger till en spärr före första frågan.
- Railways funktion för att kopiera tjänster mellan miljöer kan föra `synk` till development [A]. Där skulle "main" peka på developments databas, som har markören, och spärren på rad 450-454 slår till. Steg 2:s kontroll av `RAILWAY_ENVIRONMENT_NAME` stoppar det också.
- `--forsta` skriver till main. Med `synk_las` faller det på behörighet. Det är avsiktligt.

### Development skriver till produktionen
- Enda vägen är Flytta till main över HTTPS med HMAC [V DEPLOY.md:733-738; admin_flytt.py]. Den rörs inte av planen och fungerar med stängd port.
- Development skickar inga utskick i envägsläget [V scheduler.py:670-672]. Om synken står still länge blir developments bild av köer gammal, men utskick sker ändå bara i main.

### Parallella körningar
- Under steg 6 skriver två synkar till development. Utan låset kan de krocka och ge hoppade rader. Steg 2:s rådgivande lås krävs innan steg 6.

### Det som når databaserna utifrån
Allt nedan använder `RAILWAY_<MILJÖ>_PG_*` ur `.env.deploy` över TCP-proxyn [V grep efter `railway_migrate import dsn`/`_PG_HOST` i `scripts/`]. **Mot main slutar det fungera när porten stängs; mot development fungerar det som förut.**

- **CI:** `synk.yml`, `migrera.yml` (båda jobben). Ersätts i steg 6–9.
- **Skript som kan riktas mot main** (`--env main` eller fast main): `railway_migrate.py`, `railway_synk.py`, `railway_seed_dev.py` (läser main), `flytta_korningar_till_main.py` (skriver main), `fyll_kundregister.py`, `los_sandsparr.py`, `demolank_i_utkorgen.py`, `lagg_pa_utskicksfot.py`, `skapa_qa_kund.py`, `skapa_snajp_intern_kund.py`, `skapa_livrustning_konto.py`, `konvertera_testkund.py`, `flytta_fran_supabase.py`, `flytta_redo_till_ny.py`, `omrakna_rangpoang.py`, `rensa_exempelbolag.py`, `fyll_embeddings.py`, `koppla_testytor.py`, `set_railway_postgres_url.py`, `verify_railway.py` (ansluter till båda [V verify_railway.py:286]), `railway_provision.py` (skapar proxyn [V rad 303-320]).
- **GDPR-verktygen:** `gdpr_radera.py` / `gdpr_verktyg.py` med miljön `railway-main` [V gdpr_verktyg.py:22-27, 62-90]. **Det här är det viktigaste:** en registrerads begäran om radering i produktionen måste fortfarande gå att verkställa. Förslag: lägg `gdpr_radera.py` och `gdpr_verktyg.py` i driftavbilden och kör dem som ett engångsjobb i main (tillfälligt startkommando i en tjänst, eller Railways CLI-skal mot tjänsten om det finns [A]). Alternativt slås porten på tillfälligt och stängs igen; varje gång dokumenteras.
- **Skript som bara riktas mot development** (fortsätter fungera): `aterstall_bedomning.py`, `granska_utkast.py`, `koade_utkast_till_granskning.py`, `omklassa_listspar.py`, `omskriv_utkast.py`, `radera_prospekt.py`, `utkast_status.py`, `qa_radera_konto.py` m.fl.
- **Övrigt:** `admin_cleanup.py` och `gdpr_verktyg.py` har även lägena `production`/`preview` mot gamla Supabase-variabler (`DATABASE_URL`, `PREVIEW_DATABASE_URL`) [V admin_cleanup.py:64-68; gdpr_verktyg.py:20-21]. De rör den döda kedjan och påverkas inte.
- `lib/db.ts` slår på SSL för `proxy.rlwy.net` [V lib/db.ts:46]. Web i Railway använder det privata värdnamnet [V evidence, main/web DATABASE_URL], så stängningen påverkar inte webben. En lokal server pekad mot produktionen slutar fungera, vilket projektregeln redan förbjuder [V CLAUDE.md, "peka aldrig en lokal utvecklingsserver dit"].

### Övriga risker
- **Developments port står öppen.** Samma data som produktionen. Skydd: starkt lösenord, `sslmode=require`, rotation efter steg 12. Stängs helt först med variant C5.
- **Migrationer utan grind.** Som i dag kan api deploya före schemat. Additiva, idempotenta migrationer krävs redan [V migrera.yml:24-25].
- **Release-ordning.** Tjänsterna i main byggs från `main`. Steg 2–4 måste nå main innan steg 5 kan gå där, om inte grenen tillfälligt sätts till `development` [A].
- **Volymen i development.** Första synken fyllde en gång developments volym [V docs/BESLUT.md:2081-2084]. Envägsläget kopierar inga tabeller, men en tätare synk ger mer WAL. Bevaka volymen första veckan [A].
- **Okända Railway-beteenden:** status och larm för cron [W3 tiger], borttagning av TCP-proxy [W4/W5 tiger], referenser över miljögränsen [W6/W7 tiger], egna variabler med `RAILWAY_`-prefix [A]. Alla prövas i development innan de används i main.

### Säker prövning av öppna nätfrågor
- Att main inte når development privat: i en tillfällig tjänst i development, kör `getent hosts postgres.railway.internal` och jämför med mains svar. Olika adresser bekräftar isoleringen utan att någon databas rörs. Behövs egentligen inte: [W1] är entydig.
- Att TLS fungerar mot developments proxy: anslut med `sslmode=require` från tjänsten `synk` i torrkörningsläget (steg 5). Faller anslutningen är TLS inte på.
