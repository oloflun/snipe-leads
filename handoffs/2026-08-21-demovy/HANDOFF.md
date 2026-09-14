# Handoff 2026-08-21 — Adminytan delad i skarp sida och demovy

Allt nedan är **uppmätt mot Railway development**, inte antaget. Där något är
obekräftat står det utskrivet med ordet OBEKRÄFTAT.

Sju commits, `3ab8666..cd6d83b`, pushade till `development` och
`railway-development`. `main` och `railway-main` är orörda utom migration 041,
som kördes i båda Railway-miljöerna.

---

## 1. Det som kräver DIG, i prioritetsordning

### 1.1 Aktivera Gemini-API:t (5 minuter, blockerar semantisk sökning)

<https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview?project=595248550632>

`GEMINI_API_KEY` är satt i alla fyra miljöerna och nyckeln är giltig. Men API:t
har aldrig aktiverats på Google-projektet, så varje embedding-anrop svarar:

```
403 Gemini API has not been used in project 595248550632 before or it is disabled.
```

Följden var att `POST /api/kb` och `POST /api/inbox/mock` svarade **500** — det
gick inte att lägga till en enda artikel i någon kunskapsbas, i någon miljö.
`/health/ready` sa `mode: live` utan invändning, eftersom den mäter LLM-nyckeln
och inte embeddings.

Jag har gjort `embed_text` degraderande i stället för kastande (commit
`3ab8666`), så allt fungerar nu — men **utan vektorer**. Kunskapsbasen söks med
svensk full-text i stället för pgvector. Det är sämre, inte trasigt.

Verifiera efteråt:

```powershell
python scripts\seed_demo.py --env development --apply
# "lägger till N artiklar: OK" och svarsfältet embeddings > 0
```

Detta är ett OAuth/konsol-moment hos tredjepart och kan inte automatiseras
härifrån.

### 1.2 Besluta om skärmdumparna i historiken

Jag committade nio skärmdumpar innan jag tänkte efter. Två av dem —
`01-admin-oversikt.png` och `09-tillbaka-till-admin.png` — var portföljvyn och
innehöll **en riktig kunds namn (Livrustning AB), månadsintäkten 12 980 kr, hela
arbetsytelistan och adminens mejladress**. CLAUDE.md är uttrycklig: inga
skärmdumpar med kunddata.

De är borttagna ur arbetsträdet och `.gitignore` täcker mönstret
(`screenshots/**/*admin*.png`) så skriptet inte kan göra om det. **Men de ligger
kvar i historiken i commit `0acb104`, som är pushad till GitHub.**

Att skriva om historiken är ditt beslut. Alternativen:

| Val | Konsekvens |
|---|---|
| Låt ligga | Bilderna finns i git-historiken för alla med läsrättighet på repot |
| `git filter-repo` + force-push | Rensar dem, men skriver om sju commits och kräver att alla klonar om |
| Gör repot privat om det inte redan är det | Enklast, löser exponeringen utan historikomskrivning |

Jag rör inte historiken utan att du säger till.

### 1.3 Öppna Vercel-previewen och prova vyväxeln där

**Bygget är grönt** — uppmätt, inte antaget. `npx vercel ls` visar fem
Preview-deployer, alla `● Ready`, och den senaste är jämngammal med commit
`cd6d83b`. Vercel har alltså byggt hela serien.

Vad jag **inte** har gjort: öppnat previewen och klickat i den. Previewen är
SSO-skyddad och automatisering kräver en `x-vercel-protection-bypass`-token
(DEPLOY.md rad 230-250). Alla beteendekontroller nedan — skärmdumpar,
`qa_vyer.mjs`, cookie-kontrollen — är körda mot **Railway development**.

Det som gör att det inte är en formalitet: `NEXT_PUBLIC_SITE_URL` bakas in vid
bygget och sätts per scope. Är den osatt i Preview-scopet skickar magiska
länkar från previewen användaren till **produktionen** (DEPLOY.md rad 122-137).
Vyväxeln rör inte den variabeln, men den är värd att kontrollera i samma svep.

```
https://snajp-git-development-olofluns-projects.vercel.app
```

Logga in som admin, tryck Demo, och bekräfta att huvudet säger *Nordlys Handel*
och att adminflikarna är borta.

---

## 2. Vad som är klart och uppmätt

### 2.1 Vyväxeln Admin / Demo

Knappen sitter i huvudmenyn på båda ytorna, bara för plattformsadmin.

```
lib/vy.ts                  cookie snajp.vy + grinden getPlatformAdmin
lib/actions/vy.ts          server action, egen grind före skrivningen
components/VyVaxel.tsx     två segment, formulär (fungerar utan JS)
lib/snajp/tenant.ts        demogren FÖRE arbetsytans slug
lib/data/dashboard.ts      workspaceName, products, vy
app/dashboard/layout.tsx   omdirigerar till /admin BARA i skarpt läge
app/admin/layout.tsx       omdirigerar till /dashboard i demoläge
```

Uppmätt via skärmdump och DOM-avläsning, inloggad som plattformsadmin:

| Vy | Arbetsyta i huvudet | Flikar |
|---|---|---|
| Admin | Snajp Admin workspace | Översikt · Kunder · Körningar · Testkörningar · Händelser + arbetsytans rad |
| Demo | **Nordlys Handel** | Översikt · Leads · Kundtjänst · Email studio · Inställningar |
| Demo → Leads | Nordlys Handel | Översikt · **Leads** · Email studio · Inställningar |
| Demo → Support | Nordlys Handel | Översikt · **Kundtjänst** · Inställningar |

Sidokolumnen i inställningarna följer med: i Leads-läget listas *Leads: målgrupp
och autonomi*, i Support-läget *Kundtjänst: fack och autosvar* och *Inkorgar*.
`Team` är dold i demovyn och `/settings/team` svarar 404 — sidan listar våra
egna mejladresser.

Bevisbilder: `screenshots/demovy/02..08`. Adminbilderna är borttagna, se 1.2.

### 2.2 Läget bär till alla undersidor

`scope` flyttades från localStorage till cookien `snajp.scope`, som servern
läser i `resolveDashboardState`. Det var det enda som fick läget att gälla
`/settings/*` och `/admin/*` — de renderas på servern och hade aldrig sett
`scope`.

Flikarna **är** växeln nu (`FLIKENS_LAGE` i `components/AppShell.tsx`). Leads
och Support smalnar av hela vyn, Översikt tar tillbaka Duo. `ScopeSwitch`, som
låg bredvid flikarna och bara gjorde halva jobbet, är borttagen.

### 2.3 Sex buggar, alla tysta var för sig

| # | Vad | Varför det inte syntes | Fix |
|---|---|---|---|
| 1 | `NameError` i `/leads/research/step` — `overrides` bands aldrig | Simuleringsläget svarar 503 några rader tidigare, alltså grön svit | `app/api/leads.py` |
| 2 | Batchens `overrides` skickades ingenstans | Svaret ekade tillbaka dem som om de gällt | `_run_batch_prospect` |
| 3 | `is_test` nådde aldrig `agent_runs` | Kolumnen fanns sedan 036, ingen anropsplats satte den | `leads_agent.py` |
| 4 | Översikten frågade `agent_type=leads` | Pipelinen skriver `leads_research` — noll rader, alltid | `Oversikt.tsx` |
| 5 | `step_log` nådde vyerna som **sträng** | Fel 4 gjorde fel 5 osynligt; båda kom fram samtidigt | `postgres.list_agent_runs` |
| 6 | `snajp_app` hade aldrig `delete` på `ss_emails` | Bara två kodvägar raderar, och sviten kör i minne | migration **041** |

Fel 5 och 6 hittades först när fel 4 var lagat och de skarpa körningarna
faktiskt gick igenom. Det är värt att notera för nästa gång: ett filter som
alltid ger noll rader gömmer varje bugg bakom sig.

**Bevis, uppmätt i databasen efter tre skarpa körningar:**

```
leads_research   is_test=True   steg=8
leads_research   is_test=True   steg=8
leads_research   is_test=True   steg=8
```

och i portföljens siffror:

```
nordlys-handel   runs=0  test_runs=3  tickets=21
snajp            runs=3  test_runs=0  tickets=6
```

`runs` är kundvolym, `test_runs` redovisas separat — de göms inte, de räknas
bara inte som något kunden gjort. Tokens räknar **båda**: en provkörning kostar
lika mycket som en riktig.

### 2.4 Demokontot är fyllt

Tenant `nordlys-handel`, UUID `00000000-0000-4000-a000-000000000001`.

| Vad | Status |
|---|---|
| Kunskapsbas | 22 artiklar (16 befintliga + 6 nya) |
| Affärskontext | `agent_context_docs` kind `product_marketing`, version 1 |
| Röstdokument | skrivet, under 4 000 tecken |
| Målgrupp | ICP med fem branscher, autonominivå `draft` |
| Regler | 8 fack: 2 auto · 4 utkast · 2 eskalera |
| Exempelbolag | 6, `origin='example'` |
| Inkorg | 6 testmejl: 1 eskalerad · 2 autosvarade · 3 utkast |
| Körningar | 3, märkta `is_test` |

De sex nya artiklarna är **valda ur demons egna mejl**, inte ur en
föreställning om vad en kunskapsbas brukar innehålla. Sex av de tolv besvarbara
mejlen i `mock.py` saknade underlag — öppettider, garanti, utbildning,
ombud/hemleverans och kvitto — och utan träff tvingar grundningsregeln fram en
eskalering. Halva demoinkorgen blev röd av en lucka i texten, inte av något
agenten gjorde.

Snajps egen tenant har **10 egna artiklar** och delar ingenting med Nordlys.
Isoleringen är bevisad i `tests/api/test_demo_isolation.py`: kunskapsbas,
röstdokument, målgrupp, affärskontext och regler skrivs med demonyckeln och
läses med en annan tenants — ingen rad syns.

### 2.5 Nycklar och drift

DeepSeek-nyckeln är utbytt **överallt**, alla fyra rapporterar `mode: live`:

| Miljö | Status |
|---|---|
| Lokalt (`snajp-support/.env`) | satt, len=35 |
| Railway `main` | satt, live |
| Railway `development` | satt, live |
| Render `snajp-support` (prod) | satt, live |
| Render `snajp-support-dev` | satt, live |

Render-pushen visade varför den behövdes: **produktionens `MODEL` stod på ett
OpenAI-modellnamn** medan providern var DeepSeek. Nu `deepseek-v4-flash`.

Nya kommandon i `scripts/keys.py`:

```powershell
python scripts\keys.py --key DEEPSEEK_API_KEY   # sätt EN nyckel
python scripts\keys.py --push-render            # båda Render-tjänsterna
```

`--push-render` läser nuvarande värden först och **hoppar över deployen om
inget ändrats** — produktionen ligger bakom slingan och en kallstart är ett
verkligt avbrott för den som råkar skriva just då.

### 2.6 Invarianten

**INV-SEC-011 — Vybytet till demokontot kräver plattformsadmin.**
`tests/invariants/test_inv_sec_011.py`, registrerad i
`ARCHITECTURE_INVARIANTS.md`.

En cookie är något klienten skickar, och tenanten härleds annars ur sessionen
med flit (INV-SEC-002). Skillnaden mellan den här funktionen och buggen där
varje inloggad kunds inkorg pekade på Nordlys Handel är **en rad**:
`getPlatformAdmin()`. Tas den bort fungerar demovyn precis som förut — den
fungerar bara för fler än den ska.

Testet är statiskt eftersom det som blir fel är vad som **inte** står där.
Bevisat även i drift: `qa_vyer.mjs` sätter `snajp.vy=demo` på en riktig kund
och mäter att arbetsytan är oförändrad.

---

## 3. Öppna punkter som INTE blockerar

### 3.1 Demokontots onboarding är inte "complete"

```json
{"complete": false, "present": ["product_marketing"],
 "missing": ["customer_research", "retention_playbook"]}
```

Två kontextdokument saknas. Följden är en gap-notis i agentens kontextpaket och
en "Kom igång"-ruta i översikten. Medvetet inte påhittat: `customer_research`
ska vara riktig research och `retention_playbook` riktiga erbjudanden, och
uppfunnet innehåll i de fälten är precis vad INV-GROUND-001 finns för att
stoppa. Skriv dem i produkten från demovyn när du vet vad de ska säga, eller
lägg dem i `scripts/seed_demo.py` bredvid `AFFARSKONTEXT`.

### 3.2 Migration 041 är INTE körd i Supabase-produktionen

`snajp_app` saknar `delete` på `ss_emails` även där. Ofarligt **just nu**,
eftersom `DATABASE_URL` fortfarande pekar på en roll med BYPASSRLS — men det
blir akut i samma sekund som `snajp_app`-övergången görs, och den övergången är
redan blockerad av **028**. Kör 041 tillsammans med 028. Noterat i
`MIGRATIONS-PENDING.md`.

### 3.3 Tre inställningssidor är fortfarande attrapper

`Mailboxes`, `Plan och fakturering` och `Tillägg` visar hårdkodad text. Enligt
ditt beslut lämnade jag dem. `Team` är dold i demovyn men fungerar skarpt.

Mailboxes kan inte byggas utan att IMAP-inloggning per kund byggs i backenden
först — den saknas helt, se 3.4.

### 3.4 Ingen inkommande mail, ingen utgående sändning

`/health/ready` säger det själv i båda Railway-miljöerna:

```
IMAP saknas — inga inkommande mail hämtas.
Ingen riktig sändväg — godkända svar loggas men skickas aldrig till kund.
```

Demoinkorgen fylls av `POST /api/inbox/mock`, alltså fixtures. Det räcker för
en demo och det är gratis — men produkten kan inte tas i skarp drift för en
kund förrän båda finns.

### 3.5 Avsändaridentiteten kan aldrig uppfyllas

`leads/scheduler.py:110-113` läser `company_name`, `orgnr` och
`postal_address` från tenantraden. **Ingen av de kolumnerna finns på
`ss_tenants`**, och ingen endpoint skriver dem. `send_guard` regel 1 —
lagstadgad avsändarinformation — kan därför aldrig passera i produktion.

Upptäckt under kartläggningen, inte åtgärdad: det är en egen uppgift med en
migration och ett formulär, och den hör ihop med 3.4. Så länge ingenting
skickas spelar det ingen roll.

### 3.6 En främmande stash ligger kvar

```
stash@{0}: WIP on codex/snipra-next: e6a493f Merge pull request #1 ...
```

Den är **inte min**. Jag råkade poppa den under felsökning och återställde med
`git reset --hard` — inget gick förlorat, stashen finns kvar orörd. Men den låg
där redan innan sessionen och någon bör avgöra om den ska tillämpas eller
slängas.

### 3.7 `SNAJP_DEMO_API_KEY` finns inte på web-tjänsten

Demogrenen faller tillbaka på `SNAJP_INTERNAL_API_KEY`, som är **samma sträng**
(verifierat mot api-tjänstens `SNAJP_DEMO_API_KEY`). Det fungerar och är
dokumenterat i koden. Att sätta en dubblett hade gett ett andra ställe att hålla
i synk. Lämnat som det är, med flit.

---

## 4. Nästa steg, i den ordning jag skulle ta dem

1. **Aktivera Gemini-API:t** (1.1). Fem minuter, och kunskapsbasen får sin
   semantiska sökning tillbaka.
2. **Besluta om skärmdumparna** (1.2).
3. **Öppna Vercel-previewen** (1.3) och bekräfta att vyväxeln beter sig likadant
   där som på Railway. Bygget är grönt; beteendet är oprövat.
4. **Prova demovyn på en riktig person.** Det är det den finns för. Logga in som
   admin, tryck Demo, gå igenom Leads och Support med någon som inte sett
   produkten, och skriv ner var de tappar tråden.
5. **Fyll `customer_research` och `retention_playbook`** (3.1) — helst genom att
   göra det i demovyn, eftersom det då också provar att formulären skriver rätt.
6. **Kör 028 + 041 mot Supabase-produktionen** när `snajp_app`-övergången ska
   göras (3.2).
7. **IMAP och sändväg** (3.4) — den enda kvarvarande saken mellan demon och en
   riktig kund i drift.

---

## 5. Kommandon du kommer behöva

```powershell
# Fyll på demokontot (idempotent, torrkörning som default)
python scripts\seed_demo.py --env development
python scripts\seed_demo.py --env development --apply
python scripts\seed_demo.py --env development --apply --korningar   # KOSTAR PENGAR
python scripts\seed_demo.py --env development --apply --tenant snajp  # bara KB

# Nycklar
python scripts\keys.py --key DEEPSEEK_API_KEY
python scripts\keys.py --check
python scripts\keys.py --push-railway
python scripts\keys.py --push-render

# Sviterna
cd snajp-support; python -m pytest tests\ -q      # 655 gröna
cd ..; python -m pytest tests\ -q                 # 245 gröna
npx tsc --noEmit; npm run build

# Driftkontroll mot Railway development
npm i --no-save playwright; npx playwright install chromium
$env:BASE="https://web-development-6c85.up.railway.app"
node scripts\qa_vyer.mjs      # GRÖNT vid senaste körningen
node scripts\qa_klick.mjs
```

### Testkonton i Railway development

| Roll | Konto |
|---|---|
| Plattformsadmin | `snajpsupport@gmail.com` / `Snajpen123!` |
| Kund | `testkund+qa031732@snajp.se` / `Testkund123!` |

Kundkontot skapades av `qa_testkund.mjs` under den här sessionen. `qa_vyer.mjs`
använder `kund@example.com` som förval, och **det kontot finns bara lokalt** —
sätt `QA_KUND_EPOST` och `QA_KUND_LOSEN` när du kör mot Railway, annars
misslyckas inloggningen och tre kontroller hoppas över med en missvisande
felrad.

---

## 6. Commits

| Commit | Vad |
|---|---|
| `3ab8666` | Vyväxeln, läget i cookie, fyra buggfixar, kunskapsbasen, `seed_demo.py`, `keys.py` |
| `2eb290e` | INV-SEC-011 + isoleringstester + cookie-kontroll i `qa_vyer.mjs` |
| `8bbdcc3` | Migration 041 — `snajp_app` fick aldrig radera |
| `9e74318` | `--push-render` deployar inte i onödan; snajp får inte Nordlys innehåll |
| `e63ae97` | `step_log` som sträng — två fel som gömde varandra |
| `0acb104` | Portföljvyn skiljer kundvolym från provkörningar |
| `cd6d83b` | Adminskärmdumparna borttagna — de innehöll kunddata |
