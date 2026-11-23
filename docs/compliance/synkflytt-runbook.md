# Synkflytten: runbook för Railway- och ägarstegen

Skriven 2026-11-18 till `docs/compliance/synkflytt-plan.md` (upplägg A). Den här
filen beskriver handgreppen. Kodstegen ligger i PR:en `compliance/synkflytt`.
Varje steg har kommandon, verifiering och backning. Ett steg som ändrar driften
körs bara med Antons ja för just det steget. En agent får köra det när Anton
sagt ja i chatten.

Märkning som i planen: **[A]** är ett antagande som ska prövas i steget innan
det byggs vidare på.

## Stegnumren

Uppdraget räknar ett steg längre än planen. Tabellen visar vilka steg som hör ihop.

| Här | Planen | Vad | Typ | Läge |
|---|---|---|---|---|
| 2 | 1 | Smala hemligheter i GitHub | Kod + ägare | Koden klar; ägarens del: steg 2b nedan (agenten fick inte skriva hemligheterna 2026-11-19) |
| 3 | 2 | Synkskriptet: miljövariabler, spärrar, lås, utfall | Kod | Klar |
| 4 | 3 | Läsrollen `synk_las` (migration 122) | Kod | Klar; i main först med releasen |
| 5 | 4 | Driftavbilden `railway/Dockerfile.drift` | Kod | Klar |
| 6 | 5 | Tjänsten `synk` i main, torrkörning | Railway + ägare | **Gjort 2026-11-23** med `scripts/railway_driftjobb.py --apply --bara synk` och `railway_synk_anslut.py --apply`. Kvar för ägaren: försegla de två variablerna |
| 7 | 6 | Parallellkörning med skrivning, minst 24 h | Railway | **Ersatt 2026-11-23:** GitHub-synken gick inte (GitHub startade inga jobb), så parallellkörningen gick inte att göra. Railway-synken torrkördes och slogs sedan på (`--skarp`) |
| 8 | 7 | Stäng av GitHub-synken | Kod | **Gjort 2026-11-23:** schemat borttaget ur `synk.yml`, manuell start kvar |
| 9 | 8 | Tjänsten `migrera` per miljö | Railway | **development: körs sedan 2026-11-19** (`MIGRERA_APPLY=1`); **main: körs sedan 2026-11-23** som tjänsten `migrera-main` (en tjänst finns bara i miljön den skapades i) |
| 10 | 9 | PR-kontrollen utan databas | Kod + ägare | Koden klar 2026-11-19 (`scripts/releasens_migrationer.py`, `GET /api/drift/schema`, migration 129); ägaren sätter `SCHEMA_LASNYCKEL`, se steg 10b |
| 11 | 10 | Insyn i panelen och larm | Kod | Klar 2026-11-19 |
| 12 | 11 | Stäng produktionens publika port | Ägare | Nedan; provisioneringens vakt är klar 2026-11-19 |
| 13 | 12 | Ta bort `ENV_DEPLOY` och rotera | Ägare | Nedan |
| 14 | 13 | Dokumenten | Kod (dokument) | Nedan |

## Gemensamt

- Projektet: `b4ec4f98-2d00-4410-bfae-12fb69652d0b`. Repot: `oloflun/snipe-leads`.
- GraphQL körs med `python scripts/railway.py q '<fråga>' '<json>'`. Tokenen läses
  ur `.env.deploy` eller `RAILWAY_TOKEN` och skrivs aldrig ut.
- Id:n för miljöer och tjänster:
  `python scripts/railway.py show b4ec4f98-2d00-4410-bfae-12fb69652d0b`. Nedan
  står `<MAIN>`, `<DEV>`, `<PG>` (tjänsten Postgres), `<SYNK>` och `<MIGRERA>`.
- Kontrollera först att fälten finns i API:t [A]. Namnen är hämtade ur
  repots egna skript och Railways config-as-code:
  ```
  python scripts/railway.py q '{ __type(name:"ServiceInstanceUpdateInput"){ inputFields { name } } }'
  ```
  Följande fält ska finnas: `rootDirectory`, `dockerfilePath`, `startCommand`,
  `cronSchedule`, `restartPolicyType` och `watchPatterns`. Saknas ett fält
  sätts det i tjänstens Settings i gränssnittet.
- Inget lösenord skrivs i en chatt, i en terminal eller som argument. Värden
  som rör databaserna går antingen direkt från fil till tjänst
  (`gh secret set` via stdin) eller skapas av ett skript och går direkt till
  databasen och Railway (`scripts/railway_synk_anslut.py`).

---

## Steg 2b. Ägarens del av de smala hemligheterna

Vid merge av PR:en läser `synk.yml` och `migrera.yml` sex nya hemligheter. När
de saknas används `ENV_DEPLOY` som förut. Steget kan göras när som helst.

**Kommandon** (Git Bash i repo-roten; värdena går från `.env.deploy` till `gh`
via stdin och syns aldrig):
```bash
for n in RAILWAY_MAIN_PG_PASSWORD RAILWAY_MAIN_PG_HOST RAILWAY_MAIN_PG_PORT \
         RAILWAY_DEVELOPMENT_PG_PASSWORD RAILWAY_DEVELOPMENT_PG_HOST RAILWAY_DEVELOPMENT_PG_PORT; do
  grep -E "^${n}=" .env.deploy | head -1 | cut -d= -f2- | tr -d '\r"'"'" | gh secret set "$n" -R oloflun/snipe-leads
done
```
Kontrollera först att alla sex finns i filen (bara namnen visas):
`grep -oE '^RAILWAY_(MAIN|DEVELOPMENT)_PG_(PASSWORD|HOST|PORT)=' .env.deploy`.
Om filen bara har de gamla namnen för main (`RAILWAY_PG_*`) läses de på samma
sätt men sparas under `RAILWAY_MAIN_PG_*`.

**Verifiering:**
- `gh secret list -R oloflun/snipe-leads` visar de sex namnen.
- `gh workflow run synk.yml -R oloflun/snipe-leads`. Loggen för steget Synka
  ska visa `Anslutningarna: de smala hemligheterna.` och sluta med
  `Synk klar. 0 rader hoppades över.`
- `gh workflow run migrera.yml -R oloflun/snipe-leads -f miljo=development -f apply=false`.
  Loggen ska visa `Anslutningen (development): de smala hemligheterna.` och
  sammanfattningen `Torrkörning. Väntar: - inga`.
- Båda körningarna kostar ungefär två Actions-minuter var.

**Backning:** `gh secret delete <namn> -R oloflun/snipe-leads`. Workflowerna
går då tillbaka till `ENV_DEPLOY`.

---

## Steg 6. Tjänsten `synk` i main, torrkörning

**Förutsättningar:**
- PR:en `compliance/synkflytt` har nått `main` i en release. Där körde
  `migrera.yml` migration 122. Kontrollera det:
  `python scripts/railway_migrate.py --env main` ska visa
  `= 20261118110000_122_synk_lasroll`.
- Tjänsten byggs från grenen `main`, eftersom avbilden och skriptet måste finnas där.

**Kommandon:**
1. Skapa tjänsten i miljön main (utan publik domän; `serviceCreate` skapar ingen):
   ```
   python scripts/railway.py q 'mutation($in: ServiceCreateInput!){ serviceCreate(input:$in){ id name } }' '{"in":{"projectId":"b4ec4f98-2d00-4410-bfae-12fb69652d0b","name":"synk","environmentId":"<MAIN>","source":{"repo":"oloflun/snipe-leads"},"branch":"main"}}'
   ```
2. Bygg, start, schema och omstart:
   ```
   python scripts/railway.py q 'mutation($sid:String!,$eid:String!,$in:ServiceInstanceUpdateInput!){ serviceInstanceUpdate(serviceId:$sid, environmentId:$eid, input:$in) }' '{"sid":"<SYNK>","eid":"<MAIN>","in":{"rootDirectory":"/","dockerfilePath":"railway/Dockerfile.drift","startCommand":"python scripts/railway_drift.py synk","cronSchedule":"*/10 * * * *","restartPolicyType":"NEVER"}}'
   ```
3. Kontrollera gren och region i `railway.py show`: tjänsten ska ha grenen
   `main` och samma region som `api` (Amsterdam). Är något annat, rätta det i
   Settings. Saknas deployment-triggern skapas den som i
   `railway_provision.ensure_trigger` (gren `main`).
4. Anslutningarna. Skriptet ger `synk_las` ett nytt slumpat lösenord och
   slår på inloggning, bara i main. Sedan skriver det tjänstens två variabler.
   Ingenting skrivs ut.
   ```
   python scripts/railway_synk_anslut.py           # visar läget
   python scripts/railway_synk_anslut.py --apply
   ```
   Försegla sedan `SYNK_MAIN_PG_URL` och `SYNK_DEVELOPMENT_PG_URL` i
   gränssnittet (tjänsten synk › Variables › ⋮ › Seal). Förseglingen går inte
   att göra via API:t.
5. `SYNK_APPLY` sätts inte än. Tjänsten torrkör.

**Verifiering** (Railway › synk › Deployments / Cron Runs, minst tre körningar,
sedan 24 h):
- `anslutningar: miljövariabler (Railway)`.
- `läge: main → development; senast synkad: <tid>` och tabellen per tabell.
- `Torrkörning: inget skrivet.` Ingen rad som börjar med `AVBRYT` eller `VARNING`.
- Att anslutningen till development lyckades bevisar att TLS fungerar mot
  developments port, eftersom `sslmode=require` krävs.
- Att körningen inte stannade på `main-anslutningen kan skriva` bevisar att
  `synk_las` saknar skrivrätt i main.
- Notera körtiden. Railway ska visa avslutade körningar, inte omstarter [A].

**Backning:**
- `python scripts/railway_synk_anslut.py --stang` gör att `synk_las` inte kan
  logga in.
- Ta bort tjänsten i gränssnittet (Settings › Delete service). GitHub-synken går hela tiden oförändrad.

---

## Steg 7. Parallellkörning med skrivning, minst 24 timmar

**Kommandon:**
```
python scripts/railway.py q 'mutation($in: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $in) }' '{"in":{"projectId":"b4ec4f98-2d00-4410-bfae-12fb69652d0b","environmentId":"<MAIN>","serviceId":"<SYNK>","variables":{"SYNK_APPLY":"1"},"replace":false}}'
```
GitHub-synken går kvar parallellt. Det rådgivande låset (`railway_synk.LAS`)
gör att bara en av dem skriver åt gången. Den andra skriver
`En annan synk pågår (låset är taget). Den här körningen gör ingenting.` och
avslutar med 0.

**Verifiering under minst 24 h:**
- Varje Railway-körning slutar med `Synk klar. 0 rader hoppades över.` eller
  med låsraden ovan.
- Utfallet i development går att läsa utan hemligheter i utskriften (bara läsning):
  ```
  python -c "import sys; sys.path.insert(0, 'scripts'); import psycopg2; from railway_migrate import dsn; from railway_provision import env_read; c = psycopg2.connect(dsn(env_read(), 'development')).cursor(); c.execute('select lage, synkad_at, senaste_forsok_at, senaste_utfall, senaste_antal from public.mirror_meta'); print(c.fetchone())"
  ```
  `synkad_at` ska aldrig vara äldre än 20 minuter, och `senaste_utfall` ska vara `ok`.
  `senaste_antal` bär bara antal per tabell.
- Gör ett stickprov på antalen i en tabell, som 2026-10-17: `select count(*) from
  public.ss_emails where not is_test` ska ge samma svar i main och development.
- Development skickar inga utskick (`mirror_meta.lage = 'envags'`).

**Backning:** ta bort `SYNK_APPLY` (variabeln, eller `"SYNK_APPLY": ""`).
Tjänsten torrkör då igen. Den kan också tas bort helt som i steg 6.

---

## Steg 8. Stäng av GitHub-synken

**Kommandon** (kod, en PR mot `development`):
1. Ta bort blocket `schedule:` i `.github/workflows/synk.yml` och behåll
   `workflow_dispatch` som reserv i en vecka.
2. Efter en vecka utan behov tas filen bort i en ny PR.

**Verifiering:** `gh run list -R oloflun/snipe-leads --workflow synk.yml --limit 5`
visar inga nya schemalagda körningar. Railway-synken går vidare (steg 7).

**Backning:** återställ `schedule:` (git revert).

---

## Steg 9. Tjänsten `migrera` per miljö

Börja i development. Main tas efter nästa release.

**Kommandon (development):**
1. Skapa tjänsten som i steg 6, med `"name":"migrera"`,
   `"environmentId":"<DEV>"` och `"branch":"development"`.
2. Konfigurera den:
   ```
   python scripts/railway.py q 'mutation($sid:String!,$eid:String!,$in:ServiceInstanceUpdateInput!){ serviceInstanceUpdate(serviceId:$sid, environmentId:$eid, input:$in) }' '{"sid":"<MIGRERA>","eid":"<DEV>","in":{"rootDirectory":"/","dockerfilePath":"railway/Dockerfile.drift","startCommand":"python scripts/railway_drift.py migrera","restartPolicyType":"NEVER","watchPatterns":["db/migrations/**","railway/000_auth_compat.sql"]}}'
   ```
3. Variabel på tjänsten, över miljöns privata nät, med referensen:
   `MIGRERA_PG_URL = postgresql://postgres:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/railway`.
   Sätt den i gränssnittet och försegla den. En referens löstes en gång inte ut
   i en klonad miljö (`railway_provision.private_domain`). Faller anslutningen
   med ett tomt värdnamn sätts värdet bokstavligt i stället
   (`postgres.railway.internal`). Lösenordet kopieras då inom gränssnittet från
   Postgres-tjänstens variabler.
4. Kör först utan `MIGRERA_APPLY`. Det är en torrkörning.

**Verifiering (development):**
- Loggen visar `miljö: development` och `= <version>` för varje migration,
  ingen rad med `skulle köras`.
- Sätt sedan `MIGRERA_APPLY=1` (variabel). Vid nästa push som rör
  `db/migrations/` visar loggen `+ <version>`, eller `=` om
  `migrera.yml` hann före. Båda körningarna håller samma rådgivande lås
  (`railway_migrate.LAS`) och väntar på varandra. Kontrollen efteråt ska inte
  hitta något som `skulle köras`.

**Main:** gör samma sak efter nästa release, med `<MAIN>` och `"branch":"main"`.

**Backning:** ta bort tjänsterna. `migrera.yml` finns kvar och bär kedjan.

---

## Steg 10b. Nyckeln för PR-kontrollen utan databas

Koden finns från 2026-11-19. Den slås på när samma värde ligger i tre ställen:
`api` i development, `api` i main och GitHub-hemligheten `SCHEMA_LASNYCKEL`.
Utan hemligheten i GitHub går kontrollen som förut, över databasportarna.

**Kommandon** (Git Bash i repo-roten; värdet skapas i skalet, går via stdin och
skrivs aldrig ut):
```bash
v="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
for e in development main; do
  printf '%s' "$v" | railway variable set SCHEMA_LASNYCKEL --stdin --service api --environment "$e" --json >/dev/null
done
printf '%s' "$v" | gh secret set SCHEMA_LASNYCKEL -R oloflun/snipe-leads
unset v
```
Main svarar på endpointen först efter releasen (koden och migration 129).

**Verifiering:** `curl -s -o /dev/null -w '%{http_code}' https://api-development-5cc3.up.railway.app/api/drift/schema`
ger 401 (nyckeln satt, ingen nyckel i anropet) i stället för 404. Nästa PR mot
`main` visar steget "Vad väntar i development och main (över HTTPS)" och inget
steg som installerar psycopg2.

**Backning:** `gh secret delete SCHEMA_LASNYCKEL -R oloflun/snipe-leads`.
Kontrollen går då tillbaka till databasvägen.

---

## Steg 12. Stäng produktionens publika port

**Förutsättningar** (alla ska vara uppfyllda; annars görs inte steget):
- Steg 7 har gått i minst 24 h och steg 8 är gjort.
- Steg 9 körs i båda miljöerna.
- Steg 10 är byggt. Annars når `migrera.yml` (`releasens migrationer` och
  `kör migrationerna` mot main) fortfarande main utifrån och faller.
- `scripts/railway_provision.py` skapar inte längre en proxy för main när
  `RAILWAY_MAIN_PG_HOST` saknas (rad ~306–320). Annars öppnar nästa `--apply`
  porten igen. Det är en liten kodändring som ännu inte är gjord.
- Det finns en väg för GDPR-raderingar i produktionen, som avsnitt 7 i planen
  kräver: `gdpr_radera.py` i driftavbilden som engångsjobb, eller porten öppnas
  tillfälligt och stängs igen. Båda dokumenteras varje gång.
- Kontrollera listan i planens avsnitt 7 över allt som når main utifrån.

**Kommandon:**
```
python scripts/railway.py q 'query($s:String!,$e:String!){ tcpProxies(serviceId:$s, environmentId:$e){ id domain proxyPort } }' '{"s":"<PG>","e":"<MAIN>"}'
python scripts/railway.py q 'mutation($id:String!){ tcpProxyDelete(id:$id) }' '{"id":"<PROXY_ID>"}'
```
`tcpProxyDelete` är ett antagande [A]. Finns mutationen inte, ta bort
proxyn i gränssnittet (Postgres › Settings › Networking › TCP Proxy).

**Verifiering:**
- En ny bevisfil `D:\comp-compliance\evidence\railway-konfiguration-<datum>.txt`
  visar att `RAILWAY_TCP_PROXY_DOMAIN` saknas på main/Postgres.
- `python scripts/railway_migrate.py --env main` faller på anslutningen. Det
  är det förväntade utfallet.
- Hälsokontrollerna för web och api är gröna. Synkens nästa körning är grön,
  eftersom den läser main privat.

**Backning:** skapa proxyn igen, som i `railway_provision.py`:
```
python scripts/railway.py q 'mutation($sid:String!,$eid:String!){ tcpProxyCreate(input:{serviceId:$sid, environmentId:$eid, applicationPort:5432}){ domain proxyPort } }' '{"sid":"<PG>","eid":"<MAIN>"}'
```
Domän och port kan bli nya [A]. Uppdatera i så fall `RAILWAY_MAIN_PG_HOST/PORT`
i `.env.deploy` (och i GitHub-hemligheterna om de finns kvar).

---

## Steg 13. Ta bort `ENV_DEPLOY` och rotera

**Förutsättning:** steg 8 till 12 är gjorda. Inget workflow läser längre en
databashemlighet.

**Kommandon:**
```bash
gh secret delete ENV_DEPLOY -R oloflun/snipe-leads
for n in RAILWAY_MAIN_PG_PASSWORD RAILWAY_MAIN_PG_HOST RAILWAY_MAIN_PG_PORT \
         RAILWAY_DEVELOPMENT_PG_PASSWORD RAILWAY_DEVELOPMENT_PG_HOST RAILWAY_DEVELOPMENT_PG_PORT; do
  gh secret delete "$n" -R oloflun/snipe-leads
done
```
Rotation. Allt som legat i `ENV_DEPLOY` har funnits hos GitHub.
- `postgres` i båda miljöerna: nytt lösenord med `alter role postgres password …`,
  som körs inne hos Railway (tjänsten `migrera`, eller Postgres › Data ›
  Query i gränssnittet [A]). Uppdatera därefter Postgres-tjänstens
  `POSTGRES_PASSWORD`, `MIGRERA_PG_URL` i båda miljöerna,
  `SYNK_DEVELOPMENT_PG_URL` (developments lösenord) och `.env.deploy`.
- `synk_las`: `python scripts/railway_synk_anslut.py --apply` ger nytt lösenord
  och ny variabel i ett steg. Det kräver mains port, så kör det före steg 12
  eller via en tillfälligt öppnad port.
- `RAILWAY_TOKEN`: ny token i Railways kontoinställningar, och den gamla tas bort.
- Vilka andra nycklar som ska roteras bestämmer Anton.

**Verifiering:** `gh secret list -R oloflun/snipe-leads` visar inga
databashemligheter (bara `SCHEMA_LASNYCKEL`, om steg 10 är byggt). Synken och
migrera blir gröna efter rotationen.

**Backning:** raderingen går inte att backa och behöver inte backas. Rotationen
går inte att ångra men skadar inget.

---

## Steg 14. Dokumenten

En PR mot `development`:
- `docs/dpia_supportagenten.md`: stryk GitHub (Actions) som underbiträde för
  persondata (raden kring 103, 114 och avsnittet 438–441).
  `docs/JURIDIK_ATGARDER.md`: samma sak.
- `DEPLOY.md`: migrationerna och synken körs hos Railway, och mains port är
  stängd. Det inaktuella avsnittet om `spegla-dev.yml` tas bort.
- `CLAUDE.md`: migrationsavsnittet.
- `ARCHITECTURE_INVARIANTS.md`: INV-DATA-003 säger fortfarande "åt båda hållen".
  Riktningen är main → development (INV-DATA-008).
- `docs/BESLUT.md`: Antons beslut (planens steg 0) med resonemanget.

**Verifiering:** `grep -rin "ENV_DEPLOY\|synk.yml" docs DEPLOY.md CLAUDE.md` visar bara historik.

**Backning:** git revert.
