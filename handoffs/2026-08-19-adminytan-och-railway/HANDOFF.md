# Handoff 2026-08-19 — adminytan lagad, Railway-deployen står still

Till nästa agent (och till människan som läser över axeln). Allt nedan är
**uppmätt**, inte antaget. Där något är obekräftat står det utskrivet.

---

## 1. Läget på 30 sekunder

| | Status |
|---|---|
| Koden | Lagad, verifierad i webbläsare mot en riktig databas. Pushad till `claude/admin-dashboard-routing-layout-9l7kei`, `railway-development` och `development`. |
| Adminytan lokalt | **Fungerar.** Inloggning → `/admin`, alla 15 vägar renderar, alla knappar svarar. |
| Adminytan på Railway | **Fungerar fortfarande inte.** Två skäl, båda utanför koden — se §3 och §4. |
| Pengafri testväg | **Finns nu.** `python scripts/lokal_stack.py --apply` + `node scripts/qa_vyer.mjs`. Se §2. |

Två saker kräver dig. Ingen av dem går att göra härifrån:

1. **Adminraden i Railways databaser saknas.** Kräver `.env.deploy`. → §3
2. **Railway deployar inte grenen.** Kräver Railway-token eller dashboarden. → §4

---

## 2. Kör och testa allt utan att betala någon

Det här är vägen som gäller så länge Railway står still. Den använder samma
migrationskedja, samma roller, samma auth och samma backend som drift.

```bash
# 1. Engångsinstallation (Ubuntu/Debian; macOS-kommandon står i skriptet)
sudo apt-get install -y postgresql-16 postgresql-16-pgvector
sudo service postgresql start
sudo -u postgres psql -c "alter role postgres password 'localdev'"
npm ci
python -m pip install -r scripts/requirements-scripts.txt
python -m pip install -r snajp-support/requirements.txt   # kräver Python 3.12

# 2. Res databasen, skapa konton, seeda demodata
python scripts/lokal_stack.py --kontrollera     # säger vad som fattas
python scripts/lokal_stack.py --apply

# 3. Två terminaler
cd snajp-support && DATABASE_URL=postgresql://snajp_app:localapp@127.0.0.1:5432/railway \
  SNAJP_MASTER_API_KEY=snajp_master_local_test_key python -m uvicorn app.main:app --port 8000
npm run build && npm start

# 4. Utfärda tenant-nycklarna nu när backenden lever, och besiktiga
python scripts/lokal_stack.py --apply
npm i --no-save playwright && npx playwright install chromium
node scripts/qa_vyer.mjs
```

Två konton skapas, och båda behövs — grinden går inte att bevisa med bara ett:

| Konto | Lösenord | Förväntat |
|---|---|---|
| `snajpsupport@gmail.com` | `Snajpen123!` | Plattformsadmin. Landar på `/admin`. |
| `kund@example.com` | `Kundtest123!` | Vanlig kund, kopplad till `livrustning`. Landar på `/dashboard`, får **404** på hela `/admin`. |

`scripts/qa_vyer.mjs` besiktigar 20 publika, 11 inloggade och 15 admin-vägar i
tre roller och skriver `GRÖNT — inga avvikelser` eller listar raderna märkta
`!`. Den ska stå på grönt när du är klar. Den stod på grönt 2026-08-19.

**`--nollstall` river databasen** och stryker samtidigt `SNAJP_KEY_*` ur
`.env.local` — en nyckel som pekar på en raderad rad ger 401, och det felet
läses som "adminytan är trasig" i stället för "nyckeln är gammal".

---

## 3. Varför `/admin` svarar 404 på Railway

**Koden är rätt och redan deployad.** Det är bevisat: `/login` byggd från
grenens HEAD var byte-identisk med den deployade sidan.

Det som saknas är **raden i `public.platform_admins`**. Den skapas av
`scripts/admin_cleanup.py`, som fram till nu bara hade Supabase-miljöer
(`production`, `preview`). Railway-stacken hade ingen ingång alls.

Uppmätt mot **båda** Railway-miljöerna: inloggningen lyckas,
`/api/auth/session` ger rätt konto, varje `/admin*` ger 404. Reproducerat
lokalt genom att ta bort raden — då gick inloggningen till `/dashboard` och
`/admin` sa "Sidan finns inte", identiskt. Satte tillbaka raden → `/admin`, 200.

```bash
python scripts/admin_cleanup.py --env railway-main --diagnos   # läser bara
python scripts/admin_cleanup.py --env railway-main             # skapar raden
python scripts/admin_cleanup.py --env railway-development
```

DSN:en byggs av `RAILWAY_{MAIN,DEVELOPMENT}_PG_{PASSWORD,HOST,PORT}` i
`.env.deploy` — samma variabler som `railway_migrate.py`, och samma miljöprefix,
så `--env railway-development` inte kan träffa main.

`--diagnos` skriver sex rader. Den sista är den enda som räknas:

```
    isPlatformAdmin() som appen . True
```

Den frågan ställs som `snajp_web` med `app.user_id` satt, alltså med RLS
påslagen. Som `postgres` (BYPASSRLS) ser den rätt ut även när den inte är det —
exakt den blindheten lät den självrefererande policyn i `020` ligga oupptäckt
tills `033` städade upp.

**Ordningen spelar roll:** `railway_seed_dev.py` kopierar `platform_admins`
från main till development. Kör mot `railway-main` FÖRST, annars raderas raden
i dev vid nästa spegling.

---

## 4. Railway deployar inte grenen

Merge-commiten ligger på `railway-development` sedan 16:04. En timme senare
serverade `web-development-6c85` fortfarande gammal kod.

Så här mättes det, utan Railways API. Chunk-namnen på publika `/demo` är
innehållshärledda, så de ändras för att `WorkspaceViews.tsx` och
`DuoSummary.tsx` ändrades — inte för att något byggdes om:

| | deployad | bygge av `8a78ea6` |
|---|---|---|
| chunk A | `0v99uga1h9k3n.js` | `0998gngv8jac0.js` |
| chunk B | `122scefeokikr.js` | `0~ch5lwztm83v.js` |

Övriga tio är identiska — precis vad diffen förutsäger. Build-id:t är också
oförändrat.

Det här är alltså **inte** en misslyckad deploy som syns i loggen som röd. Det
är en deploy som aldrig startade.

Två hypoteser, i sannolikhetsordning. Ingen av dem går att avgöra härifrån:

1. **Planen/kvoten.** Railways gratisnivå slutar deploya när krediten är slut;
   redan körande tjänster lever vidare på sin gamla image. Det matchar exakt
   det som observeras — gammal kod uppe, ny commit ignorerad, inget fel någonstans.
2. **Deployment-triggern.** `RAILWAY.md` dokumenterar fällan: triggern är
   miljöspecifik, medan `serviceConnect` sätter tjänstens default-gren för
   ALLA miljöer. Fel verktyg där lät `web` bygga fel gren i tre deployer i rad.
   `INV-DEPLOY-002` spärrar den vägen numera, men bara för nyprovisionering.

**Nästa steg:** kör `python scripts/keys.py --set-railway-token`, sedan
`python scripts/verify_railway.py`. Den frågar Railway och Postgres i stället
för att läsa en fil, och svarar på både gren, byggkontext, roll och radsäkerhet.
Utan token: kolla i dashboarden om `development`-miljöns `web`-tjänst har en
deployment-trigger på `railway-development`, och om det finns en deploy i kö
eller ett kvotmeddelande.

Om det ÄR kvoten: hela §2 är vägen framåt tills någon vill betala. Produkten
går att köra och besiktiga i sin helhet lokalt.

### Uppdatering 2026-08-20 08:40 — deployen HAR gått

Hypoteserna ovan föll. Båda tjänsterna serverar dagens kod. Mätt utifrån, utan
Railway-token, med fyra prov som bara kan svara så här på ny kod:

| Prov | Svar | Fanns först i |
|---|---|---|
| `GET /settings/general` | `308 → /settings/affarskontext` | `225f327` (redirect i `next.config.ts`) |
| `GET /dashboard/leads/kontroll` | `308 → /settings/leads` | `225f327` |
| `api/openapi.json` → `/api/leads/prospects/exempel` | finns | `225f327` |
| `api/openapi.json` → `LeadsRunOverrides` | alla åtta fälten, inkl. `roles`, `must_have`, `deal_breakers` | `e4a418e` |

`development` och `railway-development` står båda på `d26ba0a`, och proven
sätter web och api på `225f327` eller senare. `d26ba0a` går inte att prova
utifrån — den rör bara fallbacken i `postgres.py`, som kräver ett autentiserat
anrop för att synas. Det som återstår är alltså **inte** en deploy: `/admin` är 404 för att raden i `platform_admins`
saknas (§3), och 039/040 är inte körda mot dev-databasen
(`MIGRATIONS-PENDING.md`). Båda kräver `.env.deploy`, som numera går att
återskapa ur Railway med en enda token — se `RAILWAY.md`,
"`.env.deploy` följer inte med en klon".

---

## 5. Vad som faktiskt lagades

Fem separata fel. Alla hittade genom att köra ytan, inte genom att läsa den.

**1. Två staplade headers under `/admin`.** Varje arbetsytesvy renderar sitt
eget `AppShell` via `PageShell`, och dess länkar pekar på `/dashboard/*` — som
för en plattformsadmin studsar tillbaka till `/admin`. Alltså tog varje flik i
den inre raden användaren UR fliken de stod i. `AppShell` renderar nu bara
innehåll under `/admin`; skalet bor i `components/admin/AdminShell.tsx`.

**2. "Min arbetsyta" var oåtkomlig.** `workspaceTabs()` mappade `/dashboard`
till `/admin`, som är portföljvyn. `WorkspaceSection` kan inte heller rendera
översikten, eftersom `app/admin/[...slug]` är en icke-optional catch-all och
aldrig får ett tomt slug. Ny route: `app/admin/arbetsyta/page.tsx`.

**3. Ingen utloggning i adminskalet.** `signOut()` fanns och fungerade; ingen
komponent anropade den. Skalet har nu samma delar som kundens: logotyp,
arbetsytans namn, scope-växel, språkval, agentmeny, utloggning, aktiv flik
(längsta match, så `/admin/leads/kontroll` markerar bara Kontroll) och
Inställningar.

**4. Spårvyn kraschade** på `steps.map is not a function`. asyncpg avkodar inte
jsonb utan typkodare, så `step_log` nådde sidan som en sträng.
`postgres.py::_avkoda_jsonb` avkodar där kolumnen läses; `lib/data/admin.ts`
normaliserar dessutom, eftersom web och api deployar var för sig och ett web
som är nyare än sitt api är ett normaltillstånd.

**5. `ensureWorkspace()` var dubbelt trasig.** Den anropade
`ensure_workspace_for_user($1)` — REVOKED från alla roller i `006` med flit —
via `sql()` utan identitet, så den föll på `permission denied` vid varje
inloggning, tyst. Dessutom lästes användar-id ur `auth()`, som läser den
INKOMMANDE requesten och därför alltid gav `null` direkt efter `signIn()`. Hela
self-healing-blocket var död kod. Går nu via
`ensure_workspace_for_current_user()` och `sqlAsUser`, med id:t hämtat ur
`auth.users` på adressen.

Utöver det: inloggningen landar på arbetsytans rot i stället för Email studio
(en produkt av två), och plattformsadmin skickas direkt till `/admin` i stället
för via en studs genom `/dashboard`.

---

## 6. Vad som är verifierat, och hur

| Påstående | Hur det mättes |
|---|---|
| Migrationskedjan reser sig från noll | Hela kedjan mot ren Postgres 16 + pgvector. 46 filer körda, 0 fel. |
| Inga oskyddade RLS-policyer | `select count(*) from pg_policies where qual like '%app.tenant_id%' and qual not like '%NULLIF%'` → 0 |
| Adminytan renderar för rätt roll, och bara för den | `scripts/qa_vyer.mjs`: GRÖNT |
| Varje knapp svarar | Klickvandring: 11 flikar, 5 körningsfilter (18/6/6/3/3 rader), 4 händelsefilter, Spår, rådgivarens 6 frågor, scope-växel, EN/SV, agentmeny, utloggning, "Starta testkörning", "Ställ frågan" (körde en riktig agentkörning) |
| Adminytan överlever att backenden är nere | Backend stoppad: alla sidor 200 med fullt skal och ärligt felmeddelande, ingen kraschsida |
| Bygget är rent | `rm -rf .next && npx next build` grönt, `npx tsc --noEmit` grönt, `npm ci` mot låsfilen rent |
| Invarianterna håller | `pytest tests/invariants` → 210 passed, 29 skipped |
| Backenden håller | `pytest` i snajp-support → 608 passed. 5 röda är `ModuleNotFoundError: scrapegraph_py`, som kräver Python 3.12; CI kör 3.12 och de passerar där. |
| agent-core laddas | docker-smoke-jobbets exakta påstående kört utan container (ingen docker-daemon i sessionen) |

**Inte verifierat:** ingenting av ovanstående är kört mot Railway, eftersom
deployen inte gått. Docker-imagen är inte byggd — ingen daemon fanns.

---

## 7. Att göra härnäst, i ordning

1. `python scripts/admin_cleanup.py --env railway-main --diagnos` — läser bara,
   svarar på varför `/admin` är 404.
2. Samma utan `--diagnos`, mot `railway-main` först och sedan
   `railway-development`.
3. Ta reda på varför Railway inte deployar (§4). Token via
   `scripts/keys.py --set-railway-token`, sedan `scripts/verify_railway.py`.
4. När deployen gått: `BASE=https://web-development-6c85.up.railway.app node
   scripts/qa_vyer.mjs`. Den ska ge samma GRÖNT som lokalt.
5. Först därefter `railway-main`.

**Rör inte** `main` — projektreglerna i `CLAUDE.md` säger att allt går via
`development`, och `main` rörs först när något är verifierat i previewen.

---

## 8. Skärmdumpar

`skarmdumpar/` innehåller det som besiktigades, tagna mot den lokala stacken
i §2 (1440×900 där inget annat sägs):

| Fil | Vad den visar |
|---|---|
| `klar-01-oversikt.png` | `/admin` med hela skalet: logotyp, arbetsytans namn, scope-växel, EN/SV, agentmeny, utloggning, båda flikraderna med aktiv flik |
| `klar-03-korningar.png` | `/admin/korningar` med filterraden och Spår-länkarna |
| `klar-06-arbetsyta.png` | `/admin/arbetsyta` — routen som saknades |
| `klar-12-spar.png` | Spårvyn, den som kraschade på `steps.map` |
| `klar-13-mobil.png` | `/admin` vid 375px |
| `degraderad-oversikt.png` | `/admin` med backenden NERE: fullt skal, ärligt felmeddelande, ingen kraschsida |

---

## 9. Öppna trådar som INTE hör till det här arbetet

- **Preview-routerna** (`/dashboard/companies`, `/contacts`, `/inbox`,
  `/analytics`, `/assistant`) går inte att nå som kund: `AppShell`s
  stranded-effekt skickar tillbaka till `/dashboard`, samtidigt som
  `lib/routes.ts` påstår att "de nås fortfarande direkt". Motsägelsen är äldre
  än det här arbetet. Under `/admin` renderar de, eftersom effekten är villkorad
  på `/dashboard/`-prefixet.
- **Utgående mail saknas i hela kodlinjen.** Magic link och
  lösenordsåterställning svarar ärligt att de inte är kopplade.
- **`DEEPSEEK_API_KEY`** — backenden går i simuleringsläge utan den. "Starta
  testkörning" på leads-ytan säger det rakt ut i UI:t.
