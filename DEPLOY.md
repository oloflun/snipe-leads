# Miljöer och driftsättning

Inget deployas genom att någon klickar i en dashboard.

> **LÄS DET HÄR FÖRST.** Repot har **två deploy-kedjor, och bara den ena är
> levande.** Den döda kedjan går fortfarande grön i GitHub Actions. Det är
> därför den kostar tid: ingenting säger ifrån, den bygger bara en miljö ingen
> använder. Uppmätt 2026-08-23, efter att en push till `development` inte syntes
> någonstans.

## Den levande kedjan: Railway

| | Produktion | Development |
|---|---|---|
| **Gren som deployar** | `railway-main` (tills vidare, se nedan) | **`development`** |
| Tjänster | Railway `web` + `api` | samma, i miljön `development` |
| Databas | Railway Postgres (`main`) | Railway Postgres (`development`) |
| Webb-URL | `web-production-1fe2c.up.railway.app` | `web-development-6c85.up.railway.app` |
| API-URL | `api-production-d7695.up.railway.app` | `api-development-5cc3.up.railway.app` |

URL:erna står i `.env.deploy` som `RAILWAY_{MAIN,DEVELOPMENT}_{WEB,API}_URL`.
Railway-projektet är `b4ec4f98-2d00-4410-bfae-12fb69652d0b`.

### `development` deployar sig själv sedan 2026-08-27

Vi har släppt Vercel helt (se legacy-avsnittet nedan). Railways `deploymentTrigger`
för `web` och `api` i miljön `development` pekade tidigare på grenen
`railway-development` — en spegelgren som fanns bara för att trigga Railway,
och som krävde en andra push varje gång:

```bash
git push origin development
git push origin development:railway-development   # den här raden fanns förut
```

**Det behövs inte längre.** Triggerns `branch`-fält ändrades via Railways
GraphQL-API (`deploymentTriggerUpdate`) från `railway-development` till
`development` direkt. En push till `development` startar nu byggen av `web`
och `api` i Railway-miljön `development` utan mellansteg. `railway-development`
som gren är därmed överflödig för development — den kan lämnas orörd eller
tas bort, inget läser den längre.

**Produktionen (`main`) är INTE omlagd än.** `railway-main` är fortfarande
den gren som triggar produktionsdeployen — det är ett separat, medvetet beslut
som väntar på att göras (main ska ersätta railway-main på samma sätt). Fram
tills dess gäller fortfarande, för produktion:

```bash
git push origin main
git push origin main:railway-main
```

Kontrollera grenen innan du felsöker "min ändring syns inte" — särskilt för
`main`, som fortfarande har den gamla tvåstegs-fällan. Det är andra gången
samma fälla slog till för development innan den lagades — `verify_railway.py`
bär en kommentar om att `web` byggde fel gren i tre deployer i rad medan
felsökningen letade i byggkontexten. Byggmeddelandet var sant hela tiden; det
beskrev en annan commit.

```bash
python scripts/verify_railway.py     # kontrollerar bland annat trigger-grenen
```

Trigger-configen läses och ändras med `scripts/railway.py` (rå GraphQL-klient,
token ur `.env.deploy`). Exempel — lista aktuell branch för en trigger:

```bash
python scripts/railway.py q \
  'query($p:String!,$e:String!,$s:String!){ deploymentTriggers(projectId:$p,environmentId:$e,serviceId:$s){ edges{ node{ id branch } } } }' \
  '{"p":"b4ec4f98-2d00-4410-bfae-12fb69652d0b","e":"<environmentId>","s":"<serviceId>"}'
```

`environmentId`/`serviceId` för respektive miljö och tjänst står i "Faktiska
identiteter" längst ned i den här filen.

### Migrationer körs mot Railway

```bash
python scripts/railway_migrate.py --env development --apply
python scripts/railway_migrate.py --env main --apply
```

**Inte** genom Supabase Management-API:t. Det registrerar sin egen 14-siffriga
version utan motsvarande fil i katalogen, vilket är den dubbla bokföring som
fällt liggaren två gånger. Se `MIGRATIONS-PENDING.md`.

Verifiera alltid som `snajp_web` med `app.user_id` satt — aldrig som `postgres`.
Tabellägaren kringgår RLS utan att något syns i en diff.

---

## Den döda kedjan: Vercel + Render + Supabase

Beskrivs längre ner i den här filen och i avsnitten om Render, Vercel och
Supabase-grenar. **Den driver ingenting längre.** Avsnitten står kvar för att de
förklarar varför saker ser ut som de gör, inte för att de beskriver hur något
deployas i dag.

Två konkreta konsekvenser som annars ser ut som buggar:

* `.github/workflows/deploy-development.yml` deployar till **Vercel** vid push
  till `development`. Den går grönt. Den når inte produkten.
* Vercel-previewen läser Supabase-grenen `development`, som står i
  `MIGRATIONS_FAILED` sedan 2026-08-15. Inloggning där ger
  `CallbackRouteError` — `authorize` i `lib/auth.ts` kastar mot en databas som
  saknar halva schemat. Det är inte ett kodfel och ska inte felsökas som ett.

Städa inte bort kedjan utan att först flytta det som fortfarande används:
Vercel-scopet håller variabler som `scripts/onboard_tenant.py` skriver till.

---

## PROJEKTREGEL: development-databasen är en spegel av produktionen

Gäller **Railway-miljön `development`**, som bär en spegelmarkör (`mirror_meta`)
och kontrolleras av `verify_railway.py`. Regeln följde med från Supabase-grenen
och gäller oförändrad — bara databasen under den har bytts.

**Varför:** en ändring ska gå att utvärdera med allt annat lika. En tom databas
testar bara att koden startar — inte att den fungerar mot verklig datamängd,
riktiga tenants och de kanttillfällen som bara finns i verklig data. Skiljer sig
underlaget går skillnaden i utfall inte att tillskriva ändringen.

**Konsekvensen, som måste stå skriven:** miljön innehåller därmed **riktiga
kunders ärenden, mejladresser och kunskapsbaser**. Den ska behandlas med samma
sekretess som produktionen:

- Inga länkar till `web-development-6c85.up.railway.app` för utomstående.
- Inga skärmdumpar med kunddata i chattar, ärenden eller dokument.
- Samma personkrets som har åtkomst till produktionen, ingen bredare.
- Peka inte en lokal utvecklingsserver mot den. Kör `scripts/lokal_stack.py`
  i stället — den reser hela kedjan från noll mot en tom lokal databas.

`main` får ALDRIG en spegelmarkör. Den är målets kännetecken; dyker den upp där
har riktningen vänts.

---

## Migrationskedjan är självbärande sedan `000_base_schema.sql`

`supabase/migrations/000_base_schema.sql` innehåller dashboardens grundtabeller
(`workspaces`, `profiles`, `business_contexts` …). Den finns för att kedjan inte
var självbärande: `001` och framåt förutsätter att `workspaces` finns, men den
skapades bara av `supabase/schema.sql` — som ingen migrationsmekanism kör.

Det märktes först när den första preview-grenen skapades: Supabase replayar
`migrations/`, och grenen fick `ss_tenants` (från `002`) men **inte**
`workspaces`. Ett halvt schema som såg ut att vara helt. Samma lucka gällde
varje framtida gren och varje återställning från noll.

`000` är idempotent — `create table if not exists` och `drop policy if exists`
före varje `create policy` — så den är en no-op mot en databas som redan har
tabellerna.

---

## Render

> **LEGACY — driver ingenting i dag.** Produkten deployas från Railway; se
> "Den levande kedjan" högst upp. Avsnittet står kvar för att det förklarar
> varför saker ser ut som de gör, inte för att beskriva hur något deployas nu.

Blueprinten är `snajp-support/render.yaml` och innehåller **båda** tjänsterna.

`branch:` står i git på båda. Det är inte kosmetik: grenvalet var ett osynligt
dashboardfält, och två produktionsincidenter kom ur att det pekade fel utan att
synas i någon diff. `INV-DEPLOY-001` kräver numera att varje tjänst anger sin
gren, och kontrollerar `rootDir`/`dockerfilePath` **per tjänst** — den var
tidigare blind för allt utom den första.

**Root Directory-fältet i dashboarden ska vara TOMT.** Det har återgått till
`snajp-support` av sig självt och fällt ett Docker-bygge med
`"/agent-core": not found`. `agent-core/` ligger utanför `snajp-support/` och
kan inte kopieras in om byggkontexten är undermappen.

### Kvoten — läs innan du slår på keep-alive för previewen

Renders gratisnivå ger **750 instanstimmar per månad delat på ALLA
gratistjänster** i workspacet. `keep-backend-awake.yml` pingar därför bara
**produktionen** (~250 h/mån). Två varma tjänster hade landat på ~500 h, och när
taket spricker stänger Render av allt till nästa månad.

Previewen får alltså en minuts kallstart vid första anropet efter inaktivitet.
Det är rätt avvägning för en testmiljö. Behövs dygnet-runt-drift: uppgradera en
tjänst till Starter (~7 USD/mån), vilket också tar bort SMTP-blockeringen.

---

## Vercel

> **LEGACY — driver ingenting i dag.** Produkten deployas från Railway; se
> "Den levande kedjan" högst upp. Avsnittet står kvar för att det förklarar
> varför saker ser ut som de gör, inte för att beskriva hur något deployas nu.

Variabler sätts **per scope**. `vercel env add <namn> preview`.

Efter Auth.js-bytet (`3c2cb2b`) är de kritiska Preview-variablerna:

`AUTH_SECRET` — signerar sessions-JWT:n. Utan den är ALLA oinloggade: proxyn
redirectar `/dashboard` → `/login` (fail-closed) och inloggningen svarar med en
konfig-felsträng i stället för en generisk 500. Generera: `openssl rand -base64 32`.

`DATABASE_URL` — pooler-värdet för Postgres (se fälla 3 nedan). PER MILJÖ:
preview pekar på preview-grenens databas, production på produktionsdatabasen.
Utan den kastar `lib/db.ts` och inloggningen 500:ar.

Sedan de som redan fanns: `SNAJP_SUPPORT_URL`, `SNAJP_INTERNAL_API_KEY`,
`SNAJP_MASTER_API_KEY` (backend-proxy + admin), `OPENAI_API_KEY` (email-studio,
simulerar utan), `AUTH_GOOGLE_ID` / `AUTH_MICROSOFT_ENTRA_ID_ID` (SSO, valfria).

De gamla Supabase-auth-variablerna (`NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`NEXT_PUBLIC_SITE_URL`) konsumeras INTE längre av frontenden — Supabase-klienten
är borttagen i Auth.js-bytet.

### `NEXT_PUBLIC_SITE_URL` är fällan

Den läses i `lib/actions/auth.ts` med defaulten `http://localhost:3000` och
**bakas in vid build**, inte vid runtime. Tre konsekvenser:

1. Sätts den inte i Preview-scopet ärvs produktionsvärdet, och varje magic link
   och lösenordsåterställning från previewen skickar användaren till
   **produktionssajten**.
2. Sätts den inte alls hamnar de på `localhost:3000`.
3. Den går inte att ändra efter deploy utan ombyggnad.

Använd den **stabila grenaliasen**
(`https://snajp-git-development-olofluns-projects.vercel.app`), inte
deployment-URL:en som byts vid varje push.

Supabase Auth → URL Configuration i **preview-grenens** projekt måste lista
`<grenalias>/auth/callback`, annars avvisas varje inloggningsredirect.

### Saknas Supabase-env står auth-grinden helt öppen

`hasServerSupabaseEnv()` gör att `proxy.ts` **står åt sidan** i stället för att
kasta — det var medvetet, eftersom ett kast tog ner de publika sidorna. Men
följden är att `/dashboard/*` och `/settings/*` inte grindas alls när
variablerna saknas. Alla tre Supabase-variablerna måste sättas i preview.

---

## Känd begränsning: kundytor går inte att testa på `.vercel.app`

> **LEGACY — driver ingenting i dag.** Produkten deployas från Railway; se
> "Den levande kedjan" högst upp. Avsnittet står kvar för att det förklarar
> varför saker ser ut som de gör, inte för att beskriva hur något deployas nu.

`tenantSlugFromHost()` (`lib/tenants/index.ts`) returnerar medvetet `null` för
allt som slutar på `.vercel.app`, eftersom preview-URL:er har formen
`snajp-git-branch-team.vercel.app` där första etiketten inte är en kund.

Kundspecifika ytor kräver alltså en egen wildcard-domän för att kunna testas i
preview. Dokumenterat i stället för kringgått.

---

## Email Studio behöver en modellnyckel på WEBB-tjänsten

Åtgärderna i Email Studio (Kortare, Skriv om, Förbättra, Personalisera,
Översätt, Uppföljning, Analysera, A/B) körs av `app/api/email-studio/route.ts`,
alltså i Next-appen — **inte** av agent-backenden. Nyckeln måste därför ligga på
`web`, inte bara på `api`.

Så var det inte. Uppmätt 2026-08-23 saknades `OPENAI_API_KEY` på `web` i båda
miljöerna, och routen föll då till sitt simuleringsläge. Följden var att varje
**inloggad, betalande** kund fick mallgenererad text med `success: true` och
ingenting som sa att den inte kom från en modell. Åtgärderna tog noll sekunder,
vilket var det enda som avslöjade det.

| Variabel | Tjänst | Betydelse |
|---|---|---|
| `OPENAI_API_KEY` | `web` | Används först när den finns |
| `DEEPSEEK_API_KEY` | `web` | Används annars, mot `https://api.deepseek.com` |
| `EMAIL_STUDIO_MODEL` | `web` | Valfri. Default `gpt-4o-mini` / `deepseek-chat` |

DeepSeek talar OpenAI-protokollet och är vad agenterna redan kör mot, så
projektet betalar inte för en ny leverantör. Nyckeln är kopierad från `api` till
`web` i båda miljöerna.

**Saknas båda simulerar routen fortfarande** — men svaret bär nu `simulated:
true` och editorn skriver "Exempelsvar" ovanför resultatet. Ta inte bort den
markeringen: utan den går ett simulerat svar inte att skilja från agentens
arbete.

**Anonyma anrop simuleras ALLTID**, oavsett vilka nycklar som finns. Det är den
raden som gör att marknadssidans knappar fungerar utan att en oinloggad kan
bränna nyckeln (INV-SEC-010). Den kontrollen får inte tas bort.

## Prioriterat mejl vid eskalering — kräver ett app-lösenord ▸ Anton

När support, bokföring eller leads lämnar över ett ärende till en människa går
ett mejl till `snajpsupport@gmail.com` med `[PRIORITERAT]` i ämnesraden och en
direktlänk in i adminvyn. Sändvägen är `app/notifications/prioriterat_mejl.py` — ETT
konto för hela plattformen, inte per kund, och ingenting med kundutskick att
göra. Det är ett mejl, inte ett larmsystem: ingen sida övervakas och ingen jour
väcks.

| Variabel | Tjänst | Betydelse |
|---|---|---|
| `INTERNLARM_SMTP_ANVANDARE` | `api` | `snajpsupport@gmail.com` |
| `INTERNLARM_SMTP_LOSENORD` | `api` | **App-lösenord**, 16 tecken — inte kontolösenordet |
| `PUBLIC_BASE_URL` | `api` | Utan den bygger mejlet ingen länk in i adminvyn |

**Lösenordet är inte kontolösenordet.** Ett Gmail med tvåstegsverifiering kan
inte logga in på SMTP med det. Ett app-specifikt lösenord skapas under
Google-kontots säkerhetsinställningar → *Appspecifika lösenord*, och kräver att
tvåstegsverifiering redan är påslagen. Nycklar och lösenord är undantaget i
`CLAUDE.md` — det här är din hand, inte agentens.

Variabelnamnen bär fortfarande `INTERNLARM_`. De behålls med flit: de står i
Railway och här, och att döpa om dem är en driftändring — inte en omdöpning i
koden.

`PUBLIC_BASE_URL` står redan som en post i
[`docs/JURIDIK_ATGARDER.md`](docs/JURIDIK_ATGARDER.md) (avregistreringslänken
behöver den). Mejlet är alltså ett andra skäl att sätta samma variabel, inte ett
nytt.

## Kundvänd utgående SMTP (leads-utskick + godkända supportsvar)

Sändvägen är opt-in: utan alla tre variablerna nedan väljer backenden
`LoggingSendProvider`, ingenting skickas, och `/health/ready` visar
"Ingen riktig sändväg". Halvsatt räknas som osatt (loggas som varning).
ETT konto för hela plattformen i v1 — per-tenant-avsändare är Del F.

| Variabel | Tjänst | Betydelse |
|---|---|---|
| `SMTP_HOST` | `api` | t.ex. `smtp.gmail.com` |
| `SMTP_PORT` | `api` | 587 (STARTTLS, default) eller 465 (implicit TLS) |
| `SMTP_USER` | `api` | Kontot som loggar in |
| `SMTP_PASSWORD` | `api` | **App-lösenord** — samma regel som internlarmet |
| `SMTP_FROM` | `api` | Avsändaradress i From:. Tom => `SMTP_USER` |
| `SMTP_FROM_NAME` | `api` | Visningsnamn, valfritt |

### Railway blockerar SMTP — MÄTT 2026-08-28, läs det här först

Verifierat inifrån den körande containern med `GET /api/admin/sandvag`
(master-nyckel): portarna 587, 465 och 2525 ger alla timeout ut mot
smtp.gmail.com. Kör den endpointen innan någon felsöker ett SMTP-lösenord.

Railway släpper igenom utgående SMTP (portarna 25/465/587/2525) **bara på Pro
och uppåt**. Projektet `brave-passion` ligger på `trial`, så SMTP-vägen kan
inte fungera i drift oavsett hur rätt uppgifterna är — containern får
`Network is unreachable`. Samma blockering fanns på Render och löstes
2026-07-30 (commit `0d3ac1d`).

**Vägen som fungerar på nuvarande plan är Resend över HTTPS:**

| Variabel | Tjänst | Betydelse |
|---|---|---|
| `RESEND_API_KEY` | `api` | Nyckeln från resend.com. Ensam räcker den — kanalen väljs automatiskt |
| `SMTP_FROM` | `api` | Avsändaradress, t.ex. `hej@snajp.se`. Måste ligga på en domän som är **verifierad hos Resend** |
| `SMTP_FROM_NAME` | `api` | Visningsnamn, t.ex. `Snajp` |
| `EMAIL_PROVIDER` | `api` | Valfri. Tom = auto. `smtp` tvingar SMTP-vägen för mätning |

Tre steg: skapa konto på resend.com, lägg till `snajp.se` och för in de tre
DNS-posterna Resend visar hos Loopia (DKIM + SPF + return-path), och sätt
`RESEND_API_KEY` i Railway. Domänverifieringen ger DKIM-signering, alltså
bättre leveransbarhet än både Gmail och en delad SMTP-brevlåda — och den löser
samtidigt att `hej@snajp.se` måste vara en riktig avsändare.

Gratisnivån är 3 000 mejl/månad och 100/dag, vilket rymmer paketens 300
mejl/månad med marginal.

**Sätt dem med skriptet, inte för hand:**

```bash
python scripts/smtp_konfig.py --env development            # visa läget
python scripts/smtp_konfig.py --env development --apply    # testa inloggning + sätt
```

Skriptet loggar in på SMTP-servern INNAN det rör Railway. Ett fel lösenord
ger annars inget felmeddelande vid deploy — bara mejl som tyst inte går fram.
Lösenordet läses med `getpass` och skrivs aldrig ut.

**Kontot måste ligga hos Loopia.** `snajp.se` har SPF-posten
`v=spf1 include:spf.loopia.se -all`, och `-all` är ett HÅRT avslag: bara
Loopias servrar får skicka som @snajp.se. Ett Gmail-konto med
`From: hej@snajp.se` skulle inte hamna i skräpposten — det skulle avvisas.
Brevlådan skapas i Loopias kundzon under E-post (LoopiaAPI-uppgifterna i
`.env.deploy` är tomma, och ett kontolösenord kräver en människa ändå).
Utgående server: `mailcluster.loopia.se` port **587** — 465 svarar inte där.

Skild från `INTERNLARM_SMTP_*` med flit — de två vägarna får aldrig dela
konto eller egenskaper (`app/notifications/prioriterat_mejl.py` skriver ut
varför). Tre saker som INTE ändras av att variablerna sätts: send_guard-
spärrarna gäller varje leads-utskick som förut, testmejl (`provider='mock'`)
skickas aldrig oavsett konfiguration, och `SNAJP_OUTBOX_DIR` (torrkörning)
vinner över SMTP om båda är satta — den kollisionen ska kosta en .eml-fil,
aldrig ett riktigt mejl.

**Saknas variablerna skickas ingenting, tyst.** Det är rätt utfall lokalt och i
testsviten — men det betyder också att ett bortglömt steg inte märks förrän
någon undrar var mejlen tog vägen. `prioriterat_mejl.har_konfiguration()` svarar på
om steget är gjort, utan att skicka ett provmejl och utan att något värde kan
hamna i en logg.

**Mejlet kan aldrig fälla det det handlar om.** Varje undantag fångas, SMTP körs
i en tråd med tio sekunders tak, och `skicka_prioriterat()` returnerar `False` i
stället för att kasta. Ett ärende som eskalerar har redan gått fel för kunden; att svaret
också uteblev för att Gmail hade en dålig dag vore att göra ett problem till
två.

**Ett mejl per eskaleringshändelse.** För support går dedupen på om KUNDEN redan
har ett eskalerat ärende — varje meddelande i chatten öppnar ett eget ärende, så
utan det hade en pågående, redan överlämnad tråd mejlat en gång per replik. För
bokföringsperioden bär nyckeln periodens brister, eftersom rapporten hämtas varje
gång någon öppnar vyn.

Dubblettminnet är PROCESSLOKALT. Två repliker har var sitt, och en omstart
glömmer. Följden är i värsta fall ett extra mejl, aldrig ett uteblivet — och de
två ställen där dubbletter annars skulle bli många dedupliceras dessutom mot
databasen.

## DNS hos Loopia — automatiserat, utom API-användaren

`www.snajp.se` är tillagd i Railway och väntar på en CNAME. Posten sätts med

```bash
python scripts/loopia_dns.py            # visa nuvarande poster
python scripts/loopia_dns.py --apply    # sätt CNAME mot Railway
```

Skriptet talar XML-RPC mot `https://api.loopia.se/RPCSERV`, städar bort poster
som krockar med en CNAME på samma namn, och skriver ut zonen före och efter.

**API-användaren är VALFRI.** Utan `LOOPIA_API_USER` och
`LOOPIA_API_PASSWORD` i `.env.deploy` kör skriptet i kontrolläge: det slår upp
`www` live, säger om posten är satt, och skriver ut exakt vad som ska fyllas i
om den inte är det. Posten går att sätta för hand i kundzonen på två minuter —
målet är en DNS-post, inte ett API.

Skapa API-användaren om du vill kunna ändra DNS **härifrån** i framtiden.

API-användaren Den skapas i
kundzonen under **Kontoinställningar → LoopiaAPI** och är en egen inloggning,
skild från kontolösenordet. Lägg den i `.env.deploy`:

```
LOOPIA_API_USER=nagot@loopiaapi
LOOPIA_API_PASSWORD=...
```

Det är ett kontolösenord, alltså ett av undantagen i CLAUDE.md som alltid
kräver dig. Allt efter den punkten är ett kommando.

### Apex går inte att peka på Railway

Och det är inte en begränsning i skriptet:

* En CNAME får enligt DNS-standarden inte samexistera med andra poster på
  samma namn, och apex MÅSTE ha NS och SOA. Det kräver ALIAS/ANAME, som är en
  leverantörsspecifik utökning — Loopia har den inte.
* Railways plan tillåter dessutom bara **en** egen domän per tjänst, och den är
  använd av `www`. Apex avvisades med *"You have reached the limit for custom
  domains per service on your plan."*

Lös det med Loopias egen **webbvidarebefordran**, `snajp.se` →
`https://www.snajp.se`. Den funktionen finns inte i LoopiaAPI, så den punkten
förblir manuell. Skriptet upptäcker att apex pekar på Loopias parkering
(194.9.94.85/86) och påminner om det.

Verifiera kopplingen från Railways sida när DNS spridit sig:

```bash
python scripts/railway_doman.py --env main
```

Den skriver `OK` i stället för `VÄNTAR` när posten pekar rätt.

## Skatteverket: Beskattningsengagemang (orgnr-verifiering vid onboarding)

Verifierar tenantens EGET organisationsnummer — F-skatt, momsregistrering och
arbetsgivarregistrering. I dag kontrollerar onboardingen bara Luhn-siffran
(`app/leads/orgnr.py`), alltså att numret är rätt SKRIVET, inte att bolaget
finns. Klienten ligger i `app/leads/skatteverket.py`.

**Ingenting av detta är påkopplat, och det är inte en glömska.** Utan båda
nycklarna returnerar `get_skatteverket_klient()` `None`, onboardingen fortsätter
på Luhn-kontrollen precis som idag och deployen påverkas inte. Halvsatt räknas
som osatt och loggas som varning — samma regel som SMTP.

| Variabel | Tjänst | Betydelse |
|---|---|---|
| `SKATTEVERKET_CLIENT_ID` | `api` | Delas ut av Skatteverket efter ansökan |
| `SKATTEVERKET_CLIENT_SECRET` | `api` | Samma utdelning. Sätts av en människa, aldrig i en fil som deployas |
| `SKATTEVERKET_API_BAS_URL` | `api` | Valfri. Default `https://api.test.skatteverket.se`. Produktion är `https://api.skatteverket.se` |

Bas-URL:en pekar på TESTMILJÖN som default med flit: en testnyckel mot
produktion hade slagit mot riktiga beskattningsuppgifter, och det är fel håll
att falla åt.

### Två spärrar som INTE går att koda bort

**1. Nycklarna kräver ett avtal.** Skatteverket delar ut dem via formulär på
skatteverket.se — testnycklar mot sandboxen, produktionsnycklar först efter
tecknat avtal enligt API:ets allmänna villkor. Det är ett avtalsbeslut av
samma slag som DeepSeek-frågan i `CLAUDE.md`, inte något ett skript ordnar.
▸ Anton

**2. API:t kräver BankID — det finns ingen server-till-server-väg.**
Auktorisation sker med OAuth2 Authorization Code Grant där den externa
användaren legitimerar sig med e-legitimation (tjänstebeskrivning
`beskattningsengagemang-v1`, avsnitt 2.6 och 5.4). Backenden kan alltså inte
slå upp ett godtyckligt orgnr på egen hand: uppslaget görs för en inloggad
firmatecknare, eller för ett registrerat ombud med organisationscertifikat
(en egen ansökan, inte en kodändring).

Följden: `access_token` är ett argument in i klienten, aldrig något den
skaffar själv. Redirect-flödet hör hemma i Next-appens onboarding och **finns
inte** — `skatteverket.paborja_inloggning()` är en stub som kastar med hela
skälet utskrivet. Authorize- och token-URI:erna publiceras under "Säkerhet och
API:er" och kommer med nycklarna; att gissa dem hade gett en implementation
som ser färdig ut och faller vid första riktiga inloggningen.

### Fällan i svaret: 200 betyder inte "godkänd"

Tjänsten returnerar personens SENASTE registrering, och den kan vara avslutad
eller ha ett startdatum i framtiden (tjänstebeskrivningen 4.2.2). Ett bolag
vars F-skatt drogs in för konkurs 2019 svarar alltså `200` med hela posten
kvar. Använd `Engagemang.ar_aktiv()` — ett `is not None`-test läser
"avregistrerad för konkurs" som ett godkänt bolag. `404` betyder att bolaget
aldrig haft engagemanget och är ett giltigt svar, inte ett fel.

Svaren är beskattningsuppgifter för en identifierad näringsidkare, och för en
enskild firma ÄR identiteten ett personnummer. Modulen loggar därför aldrig
svarskroppen — bara korrelations-id:t, som Skatteverket auditloggar i fem år.

## Ny kund

```bash
python scripts/onboard_tenant.py --slug bolaget --name "Bolaget AB" --env preview
```

Skriptet gör de fem maskinella stegen: tenant + API-nyckel, workspace-kopplingen,
configfilen, KB-stubben och nyckeln till rätt Vercel-scope. Research, KB-innehåll,
logotyp och besiktning kräver ögon och skrivs ut som checklista. Se `TENANTS.md`.


---

## Faktiska identiteter

### Railway — det som gäller

| | Värde |
|---|---|
| Projekt | `b4ec4f98-2d00-4410-bfae-12fb69652d0b` |
| Miljöer | `main` (`47bc7047-a458-404b-a1de-ccec612cb96e`), `development` (`02c39616-1b8e-47b7-beea-d8c6cfba1acd`) |
| Tjänster | `web` (`0261f633-1247-4d92-b5ab-40c2a1828b90`), `api` (`5828c279-ad8f-429b-b5e1-969372db8a0a`), `Postgres` (en uppsättning per miljö) |
| Deploy-gren, main | `railway-main` (oförändrat — main ska läggas om senare) |
| Deploy-gren, development | **`development`** (omlagd 2026-08-27, var `railway-development`) |

Verifierat mot Railways API — grenarna är lästa ur `deploymentTriggers`, inte
antagna. Senast omkontrollerat 2026-08-27 efter omläggningen av development.

### Vercel, Render och Supabase (2026-08-15) — LEGACY

| | Värde |
|---|---|
| Vercel-projekt | `snajp` — `prj_ZXXMG8Jlz0zHeLdg5NTMhN0tHpw9` |
| Preview-alias | `https://snajp-git-development-olofluns-projects.vercel.app` |
| Render produktion | `srv-d9k99ktg1s2s73fl0v6g` — https://snajp-support.onrender.com |
| Render preview | `srv-da0dopojo6nc73ea3b6g` — https://snajp-support-dev.onrender.com |
| Supabase produktion | `spsmblyvasagpekjmgmf` (org Snipe, eu-west-1) |
| Supabase preview-gren | `eppgmjswfnrfwnqvtrge`, persistent, `with_data: true` |

Hemligheter och anslutningssträngar ligger i `.env.deploy` (gitignorerad).

### Det finns ingen Render Blueprint

`GET /v1/blueprints` returnerar en **tom lista**. Båda tjänsterna är
fristående — produktionen skapad i dashboarden, previewen via API:t.
`render.yaml` läses alltså inte av någonting.

Det betyder att `INV-DEPLOY-001` vaktar en fil som inte styr driften, och att
sanningen ligger i Renders databas där ingen diff visar den. Det är precis den
luckan som orsakade två incidenter: Root Directory som svängde tillbaka till
`snajp-support`, och grenvalet som pekade mot `development` medan frontenden
deployade från `main`.

**Fixen är en driftkontroll, inte en blueprint:**

```bash
python scripts/verify_render.py
```

Den jämför Renders faktiska tjänster mot `render.yaml` — gren, rootDir,
dockerfilePath, healthCheckPath och plan — och returnerar 1 vid avvikelse.
Kör den efter varje ändring i dashboarden och som del av driftsättningsrutinen.
Filen beskriver avsikten; skriptet bevisar att verkligheten stämmer.

Att i stället registrera en riktig Blueprint hade krävt att `render.yaml` fanns
på den gren blueprinten läser (`main`), alltså en push till produktion innan
något verifierats i preview. Fel ordning.

## Migrationer 028 och 029 — kör BÅDA före rollbytet

Bevisade mot preview-spegeln, med produktionens verkliga datamängd:

- **028** stoppar kraschen `invalid input syntax for type uuid: ""`. Efter en
  skopad fråga blir `app.tenant_id` tom sträng, inte NULL, för resten av
  anslutningen — och varje senare oskopad fråga föll på `''::uuid`.
- **029** stoppar TYSTNADEN. 028 räckte inte: `list_agent_runs_all` gav 0 rader
  trots 10 i databasen, och kundöversikten fyra kunder med nollställda tal.
  Trovärdiga men felaktiga siffror är värre än en tom vy.

Efter båda, mätt som `snajp_app` utan BYPASSRLS: rätt antal överallt, och
skopade frågor ger fortfarande en delmängd — isoleringen håller.


---

## Två fällor som slog till på riktigt vid uppsättningen

**1. `vercel env rm NAME preview` raderar HELA posten.**
Vercel lagrar en variabel som gäller flera miljöer som EN post. `SNAJP_SUPPORT_URL`
och `SNAJP_INTERNAL_API_KEY` gällde "Production, Preview" — att sätta ett
preview-värde tog bort dem ur **produktionen**. Upptäckt genom att lista
scopet efteråt, inte av något felmeddelande.

`scripts/keys.py:vercel_env_set()` vägrar numera skriva till en delad post och
säger vad man ska göra i stället. Varje variabel bör vara en post per miljö.

**2. Preview-deployen är SSO-skyddad, och ska förbli det.**
`ssoProtection` är på för allt utom egna domäner, så `*.vercel.app` kräver
Vercel-inloggning. Med spegelregeln innehåller previewen riktig kunddata —
att stänga av skyddet vore ett dataläckage.

Följden: automatiserad verifiering (`scripts/verify_inv_sec_010.sh`) når inte
preview-frontenden. Skapa en **Protection Bypass for Automation**-token i
Vercel → Settings → Deployment Protection, och skicka den som
`x-vercel-protection-bypass`. Då kommer skript in medan människor fortfarande
måste logga in.

**3. Supabases direktvärd (`db.<ref>.supabase.co`) nås inte från Render.**
Den är IPv6-only. `DATABASE_URL` måste använda pooler-värden
(`aws-1-eu-west-1.pooler.supabase.com:6543`) med användarnamnet
`<roll>.<projektref>`. Symptomet är inte ett anslutningsfel utan att tjänsten
tyst faller tillbaka på `MemoryStorage` — vilket `/health/ready` numera säger
rakt ut med `storage: "memory"`.


---

## Neon som fallback

Beslut 2026-08-16: vi utvärderar Supabase-branching, och behåller Neon som
alternativ om speglingen visar sig otillräcklig. Neon har mer trogen
grenspegling och gratis branching (100 projekt, 10 grenar per projekt).

**Priset för ett byte är inte databasen — det är inloggningen.** Mätt i den här
kodbasen:

- **21 referenser** till `auth.users` / `auth.uid()` i 6 migrationsfiler
- **14 auth-anrop** över **13 filer** (`signInWithOAuth`,
  `exchangeCodeForSession`, `resetPasswordForEmail` …)
- Främmande nycklar från `platform_admins`, `workspace_invites` och `profiles`
  rakt in i `auth.users`
- Triggern `on_auth_user_created`, som skapar workspacet vid registrering

Ett byte kräver alltså att autentiseringen skrivs om — mot Neon Auth, Clerk
eller Auth.js — inte bara att anslutningssträngen ändras.

**Vad som skulle göra bytet billigare:** RLS-policyerna delar redan databasen i
två halvor. Backendens tabeller (`ss_*`, `agent_*`) grindas enbart på
`app.tenant_id` och rör aldrig `auth.uid()`. Bara dashboardens tabeller behöver
Supabase. Backenden skulle alltså kunna flytta först, med
`workspaces.ss_tenant_id` nedgraderad från främmande nyckel till mjuk referens.

Utvärderingskriterium: om Supabase-grenens spegling driver isär från
produktionen på ett sätt som gör utvärderingar otillförlitliga, är det signalen
att ta Neon-spåret.


---

## Varför Supabase-workflowen visade MIGRATIONS: FAILED

> **LEGACY.** Supabase-grenen används inte längre. Felet är dokumenterat
> i `MIGRATIONS-PENDING.md`, där beslutet att lämna grenen som den är
> också står. Migrationer körs mot Railway.

Två numreringssystem som aldrig möttes.

Repots filer heter `000_base_schema.sql`, `019_rate_limit.sql` och så vidare —
Supabase läser versionen som `000`, `019`. Men allt som faktiskt applicerats
gjordes via Management-API:t, som registrerar sina egna **14-siffriga
tidsstämplar** (`20260815150826`).

Uppmätt i produktionen före fixen:

    totalt: 30    tidsstämplade: 30    repo-numrerade: 0

Branching-workflowen läser `supabase/migrations/` från git-grenen, ser
versionerna `000`–`029`, hittar ingen av dem i `schema_migrations` och försöker
applicera **alla trettio**. De faller direkt, eftersom tabellerna och policyerna
redan finns.

Det var alltså aldrig ett fel i migrationerna. Databasen var korrekt hela
tiden — bokföringen sa bara emot.

**Fixen:** repots versionsnummer är nu registrerade som applicerade i BÅDE
produktionen och grenen. Ingen SQL kördes om; bara liggaren stämmer nu med
verkligheten.

**Regel framåt:** applicera migrationer så att versionen matchar filnamnet, och
kontrollera efteråt:

```sql
select count(*) from supabase_migrations.schema_migrations where version ~ '^[0-9]{1,3}$';
-- ska vara lika många som antalet filer i supabase/migrations/
```
