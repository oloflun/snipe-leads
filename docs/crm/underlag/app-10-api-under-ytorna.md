# App-10: API:t under ytorna (registret de andra läsarna mäts mot)

Kartläggning 2026-11-26, för flytten av hela appen till Snajp CRM
(`docs/crm/PLAN-MIGRERING.md`). Bara läst: ingen kod körd, ingen server startad.
Bygger vidare på `snajp-04-tenants-auth-api-jobb.md` (auth, nycklar, jobbkö) och
`snajp-01`–`snajp-05` (tabeller); de upprepas inte här.

## Översikt

**Vad området är.** Allt som ligger under de synliga ytorna: FastAPI-backenden
`snajp-support` (Railway-tjänsten `api`) med 39 routrar och 3 egna rutter i
`app/main.py`, Next-appens egna rutter under `app/api/**` (proxyer, inloggning,
Email Studio, hälsa), de fyra route-filerna utanför `app/api`
(`/chat/[tenant]`, `/prova/[token]`, `/llms.txt`, `proxy.ts`), serveråtgärderna i
`lib/actions/*` som talar direkt med backenden med master- eller kundnyckel, och
bakgrundsjobben som startas i backendens `lifespan`.

**Vilka som använder det.** Inloggade kunder (via proxyn med kundens nyckel),
plattformsadmin (via adminproxyn och serveråtgärder med master-nyckeln), anonyma
besökare (publika chatten, demon, triage-demon, demolänken), externa system
(CRM-API:t `/api/crm/v1` med omfångsnyckel, kanalwebhooks, Resend-webhooks,
flyttmottagaren), GitHub Actions (`/api/drift/schema`) och skript under
`scripts/`.

**Hur delarna hänger ihop.**

1. Webbläsaren anropar aldrig backenden direkt. Inloggad trafik går till
   `/api/snajp-support/<väg>` (catch-all, `app/api/snajp-support/[...path]/route.ts`),
   som via `proxyAsTenant` (`_auth.ts`) slår upp tenanten ur SESSIONEN
   (`requireSnajpTenant`), lägger på kundens `X-API-Key`, `X-Snajp-User` och vid
   demo `X-Snajp-Demo`, och skickar till `/api/<väg>` i backenden. Klientkod
   skriver ofta vägen utan prefix (`leadsAnrop("/leads/queue")`,
   `hamta("/usage?days=30")`, `snajpAnrop(...)`); prefixet `/api/snajp-support`
   läggs på i hjälparen.
2. Proxyn har tre grindar som alla nya ytor måste ärva: **läsrollen** (en
   `viewer` får 403 `{kod:"lasroll"}` på allt utom GET/HEAD), **impersonering**
   (admin som "tittar som kund": varje skrivning märks `is_test=true` i både
   frågesträng och JSON-kropp, läsning visar skarpa data) och **tenantfel**
   (`SnajpTenantError` → status och `kod` som UI:t kan skilja på, t.ex. "inte
   aktiverad ännu").
3. Proxyn (`_lib.ts:proxyWithApiKey`) gör om GET upp till 5 gånger (9 s per
   försök, exponentiell paus med jitter) vid nätfel och tomma 502/503/504, men
   ALDRIG POST/PUT/PATCH/DELETE (en omtagen batch startade fem körningar).
   En skrivning får alltså ETT försök på 9 s; bara `POST /api/inbox/sync` och
   `POST /api/inbox/mailboxes` får 45 s. Det är skälet till att långa skrivningar
   i backenden svarar 202 och kör vidare som jobb (avsnitt 7 och 10). FastAPI:s
   `{"detail": ...}` skrivs om till `{"error": ...}`; pydantics engelska
   valideringslista blir "Uppgifterna gick inte att läsa. Kontrollera det du
   fyllt i och försök igen." `Server-Timing` och `X-Request-Id` följer med.
   Svarar backenden inte: 503 `{offline:true, error:"Assistenten har svårt att
   nå sin motor just nu …"}`. Interna Railway-nätet används först
   (`SNAJP_SUPPORT_INTERNAL_URL`) och faller tillbaka på den publika adressen i
   fem minuter.
4. Backenden grindar med dependencies i `app/api/deps.py`:
   `require_api_key` (giltig nyckel, demo, master eller kundnyckel),
   `require_tenant` (kundnyckel med omfång `*`; master → 403 "Master-nyckeln är
   administrativ …"; omfångsnyckel → 403 "Nyckeln gäller bara CRM-API:t under
   /api/crm/v1."), `require_crm_nyckel` (kundnyckel med eller utan omfång; varje
   CRM-v1-ändpunkt kräver sitt omfång `crm:las`, `crm:skriv`, `crm:synk` eller
   `crm:admin`), `require_master_key` (bara master; varje godkänt anrop loggas i
   `audit_logs` via `adminlogg.logga_masteranrop`, INV-SEC-013) och
   `require_bookkeeping_tenant` (kundnyckel vars arbetsyta har produkten
   `bookkeeping`, annars 404 "Sidan finns inte."; okänd arbetsyta släpps igenom).
   UUID-parametrar valideras med `kraev_uuid` (fel form ger 404, inte 422).
5. Admin går två vägar: GET via `/api/admin/[...path]` (Next kräver
   `getPlatformAdmin()`, annars 404; master-nyckeln läggs på serversidan; bara
   GET finns) och skrivningar via serveråtgärder i `lib/actions/*` som anropar
   backenden med master-nyckeln och `X-Snajp-Admin: <användar-id>` (så att
   åtkomstloggen säger vem). Admins serverrenderade sidor läser via
   `lib/data/admin.ts:adminFetch`.
6. CRM-appen (`/crm`) använder samma proxy: `lib/crm/api.ts:crmAnrop` →
   `/api/snajp-support/crm/...` → `/api/crm/...` respektive `/api/crm/v1/...`.
   Felkroppen `detail.{code,message,meddelande,fields}` översätts till `CrmFel`
   med text på båda språken.

**Kolumnen "Tvåspråkig"** gäller texter som når användaren (felmeddelanden i
svaret). Backendens `detail` är nästan alltid bara svenska; CRM-v1 svarar med
`message` (engelska) och `meddelande` (svenska). Vyerna översätter oftast själva;
det står i respektive vyfil (app-01–app-09).

**Sekretess, webbplatsbedömningen.** Backendens grind är
`app/leads/webbpool.py:far_se(storage, tenant_id)` (sann bara för plattformsadmin
och webbyråkunderna). Den används i `GET /api/leads/prospects` (rad 638),
`GET /api/leads/prospects/{id}` (751), i hjälparen `_utan_dold_bedomning` (rad
756–772) som tvättar SKRIVSVAREN från skapa prospekt (471), befordra (887, 950),
degradera (986, 989), PATCH (2545) och listrad → prospekt (4790),
`GET /api/leads/listor/{id}` (4679),
`POST /api/leads/listor/{id}/omprova` (5086) och i researchen
(`leads_research_v2.py:437`). `admin_listor.LISTRADSFALT` saknar fälten med flit,
och flyttpaketet (`admin_flytt`) bär dem bara mellan miljöer. Varje ny yta i CRM:et
som visar prospekt eller listrader måste läsa via dessa ändpunkter eller grinda på
samma funktion.

## Avprickningslista

| Fil eller katalog | Status |
|---|---|
| `snajp-support/app/main.py` (lifespan, routrar, /health*) | läst |
| `snajp-support/app/api/deps.py` | läst |
| `snajp-support/app/api/chat.py` | delvis läst (rutter och grind; jobbflödet beskrivs i snajp-04) |
| `snajp-support/app/api/chattar.py` | delvis läst (rutter) |
| `snajp-support/app/api/support_config.py`, `support_oversikt.py` | delvis läst (rutter) |
| `snajp-support/app/api/integrationer.py`, `kanaler.py` | delvis läst (rutter, grind) |
| `snajp-support/app/api/triage.py`, `tickets.py`, `keys.py`, `rules.py`, `drafts.py` | delvis läst (rutter) |
| `snajp-support/app/api/kb.py` | delvis läst (rutter) |
| `snajp-support/app/api/inbox.py` | delvis läst (rutter, BackgroundTasks) |
| `snajp-support/app/api/leads.py` (69 rutter) | delvis läst (rutter, styrning av körning, webbgrinden; kroppar ej lästa) |
| `snajp-support/app/api/leads_suite.py`, `leads_konversationer.py`, `leads_uppfoljningar.py`, `leads_massatgard.py`, `leads_kampanjer.py` | delvis läst (rutter och docstrings) |
| `snajp-support/app/api/demo.py`, `analytics.py`, `usage.py`, `sending_domains_api.py`, `drift.py` | delvis läst (rutter) |
| `snajp-support/app/api/admin*.py` (11 filer) | delvis läst (rutter, prefix, grind) |
| `snajp-support/app/api/bookkeeping.py`, `kvitton.py` | delvis läst (rutter, grind) |
| `snajp-support/app/api/crm.py`, `crm_v1.py` | delvis läst (rutter, omfång) |
| `snajp-support/app/api/adminlogg.py`, `dubbelstart.py`, `stegtexter.py`, `rate_limit_db.py` | läst (kontrolläsaren, avsnitt 10) |
| `snajp-support/app/api/events.py` | delvis läst (felhanteraren `install_exception_handler`, beroendefel, kvotfel; rad 1–100 skummade) |
| `snajp-support/app/api/rate_limit.py`, `schemas.py` | delvis läst (`rate_limit.py`: processlokal glidande fönster-räknare, används av demon och CRM-v1; `schemas.py`: bara de modeller som nämns i raderna) |
| Ruttlistan i alla 39 routrar (grep på `@router.*`) | läst och jämförd: varje rutt har en rad (kontrolläsaren) |
| `snajp-support/app/main.py` rad 100–565 (lifespan, middleware, CORS, felhanterare) | läst (kontrolläsaren) |
| `snajp-support/app/config.py` (standardvärden för loopar och arbetare) | delvis läst (de variabler loopraderna nämner) |
| `snajp-support/app/leads/scheduler.py` (loopar) | delvis läst (run_godkand_sandare, run_send_scheduler, sweep_follow_ups) |
| `snajp-support/app/jobs/stadare.py` (loopen) | läst (kontrolläsaren) |
| `snajp-support/app/jobs/trial_paminnare.py`, `gallring.py`, `bakgrund.py` | läst (kontrolläsaren) |
| `snajp-support/app/jobs/store.py` | delvis läst (tidsgräns och TTL) |
| `snajp-support/app/jobs/stream.py` | ej läst utöver anropen i main.py |
| `snajp-support/app/leads/autopilot.py` | läst (kontrolläsaren) |
| `snajp-support/app/loopvakt.py` | delvis läst (docstringar, dödsvakten) |
| `snajp-support/app/email_pipeline/poller.py` | delvis läst (struktur, stämpling per synkförsök) |
| `app/api/snajp-support/_lib.ts`, `_auth.ts`, `[...path]` | läst |
| `app/api/snajp-support/chat`, `chat/samtal`, `jobs/[jobId]`, `triage`, `testchatt`, `testchatt/samtal`, `testchatt/jobb/[jobId]`, `leads/jobb/[jobId]` | läst |
| `app/api/snajp-support/kvitton/[[...path]]`, `bookkeeping/[...path]` | läst (hela, kontrolläsaren) |
| `app/api/admin/[...path]`, `app/api/admin/kunder` | läst |
| `app/api/agentsajt/[agent]/sso`, `app/api/auth/[...nextauth]`, `app/api/email-studio`, `app/api/health` | läst |
| `app/chat/[tenant]/route.ts`, `app/prova/[token]/route.ts`, `proxy.ts` | läst |
| `app/llms.txt/route.ts` | läst (kontrolläsaren) |
| `app/robots.ts`, `app/sitemap.ts`, `app/manifest.ts` | listade, ej lästa (metadatarutter, ingen funktion för CRM:et) |
| `lib/actions/*` | delvis läst (vilka backendvägar de anropar) |
| `lib/data/admin.ts`, `lib/crm/api.ts` | läst (anropsdelen) |
| Anropare i `components/`, `app/`, `lib/` | sökta med grep per väg |
| `support-webb/` (agentsajtens portal) | delvis läst (`lib/api.ts`, sidlistan) |
| `.github/workflows/*.yml` | delvis läst (utlösare) |
| Sidor (`app/**/page.tsx`) | listade |

## 1. Next-rutter (webbtjänsten `web`)

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP1 | Inloggad kunds väg till hela backenden (inkorg, utkast, regler, kunskapsbas, leads, agent, CRM, usage, analys) | GET/POST/PUT/PATCH/DELETE på `/api/snajp-support/<väg>` → `/api/<väg>` med kundens nyckel. Läsroll: skrivning ger 403 `{error, kod:"lasroll"}`. Impersonering: skrivning får `is_test=true` i frågesträng och JSON. Tenantfel → status + `kod`. GET görs om upp till 5 ggr, skrivningar aldrig. Svaret gzip-komprimeras (`lib/http/komprimera`). `maxDuration` 60 s | Alla kundvyer (components/leads, snajp, settings, dashboard, crm) | `app/api/snajp-support/[...path]/route.ts`, `_auth.ts:proxyAsTenant`, `_lib.ts:proxyWithApiKey` | Inloggad kund och admin som tittar som kund; tenanten ur sessionen, aldrig ur klienten | delvis (proxyns egna feltexter bara svenska) |
| AP2 | Publik supportchatt startar ett chattjobb | POST, anonym (INV-SEC-010). Tenant-slug ur kroppen avgör nyckeln (`lib/tenants`), okänd slug → demonyckeln, registrerad kund utan nyckel → 503 "Supporten är inte färdigaktiverad …". `customer_email` måste sluta på `@session.snajp.se` (annars 422 med sv+en-text). Fältet `arbetsyta` strippas | `components/snajp/SupportChat.tsx` (publik läge), `/chat/[tenant]/[session]`, `/embed/[nyckel]` | `app/api/snajp-support/chat/route.ts` → `POST /api/chat` | Anonym besökare; rate limit per IP i backenden | ja (422-texten) |
| AP3 | Publik chatt hämtar sitt eget samtal (medarbetarens svar efter överlämning) | POST (identiteten ska inte i URL). Anonym; backenden läser bara sessionsidentiteter | `SupportChat.tsx` | `chat/samtal/route.ts` → `POST /api/chat/samtal` | Anonym | nej |
| AP4 | Publik chatt pollar sitt jobb | GET med `?tenant=` (måste följa med, annars hittas jobbet inte under demonyckeln och chatten fastnar på "Agenten arbetar") | `SupportChat.tsx` | `jobs/[jobId]/route.ts` → `GET /api/jobs/{id}` | Anonym; jobb-id är UUID | nej |
| AP5 | Testchatten för den inloggade kunden | POST; tenant ur sessionen; `arbetsyta:true` sätts på serversidan så agenten får arbetsytans nyckeltal | `SupportChat.tsx` (testläge), Inställningar/Support | `testchatt/route.ts` → `POST /api/chat` | Inloggad kund | nej |
| AP6 | Testchatten hämtar samtal och pollar jobb | Som AP3/AP4 men tenant ur sessionen; ingen `?tenant=` accepteras | `SupportChat.tsx` | `testchatt/samtal/route.ts`, `testchatt/jobb/[jobId]/route.ts` → `/api/chat/samtal`, `/api/jobs/{id}` | Inloggad kund | nej |
| AP7 | Inloggad pollning av leadsjobb (körning, utkast, utskick) | GET; får inte gå via AP4 (anonym, demonyckel) | `LeadsRunForm.tsx`, `LeadsSnabbsok.tsx`, `IrisBolag.tsx`, `Bolagssida.tsx`, `Bolagsregister.tsx`, `lib/leads/utskicksjobb.ts` | `leads/jobb/[jobId]/route.ts` → `GET /api/jobs/{id}` | Inloggad kund | nej |
| AP8 | Sortera-inkorgen-demon på den publika supportsidan | POST, anonym; backendens triage är läsande; kostnadsspärr = rate limit | `components/snajp/InboxTriage.tsx` på `/support` | `triage/route.ts` → `POST /api/triage` | Anonym | nej |
| AP9 | Kvittohanterarens proxy (binärsäker) | GET/POST/DELETE; grind FÖRST: inloggad och `products` innehåller `bookkeeping`, annars 404 "Hittades inte."; kropp och svar som bytes, `Content-Type` och `Content-Disposition` bevaras (CSV med BOM); 3 försök inom 52 s; annars 503 `{offline:true}` "Kvittohanteraren har svårt att nå sin motor …" | `components/kvitton/KvittoYta.tsx`, `KvittoOversikt.tsx`, `KvittoChatt.tsx` | `kvitton/[[...path]]/route.ts` → `/api/kvitton/...` | Kund med bokföringspaketet. OBS (kontroll 2026-11-26): proxyn anropar `requireSnajpTenant` direkt och har INTE catch-allens läsrollsspärr eller impersoneringens `is_test`-märkning, och den gör om även POST/DELETE (upp till 3 försök) | nej |
| AP10 | Bokföringens proxy (SIE4, underlag, chatt, avstämning) | Samma grind och binärhantering som AP9; SIE-filen är CP437 | Ingen nuvarande vy hittad i huvudappen (kvittohanteraren ersatte den 2026-09-16; motorn står kvar) | `bookkeeping/[...path]/route.ts` → `/api/bookkeeping/...` | Kund med bokföringspaketet | nej |
| AP11 | Admins läsväg till `/api/admin/*` | Bara GET. `getPlatformAdmin()` saknas → 404 "Hittades inte." (inte 403). Master-nyckel saknas i miljön → 503 med variabelns namn. Ingen POST/PUT/PATCH/DELETE med flit | `components/admin/BytKund.tsx` (fallback); serverrenderade adminsidor använder i stället `lib/data/admin.ts` | `app/api/admin/[...path]/route.ts` | Plattformsadmin | nej |
| AP12 | Lista kunder som "Byt kund" kan öppna | GET; SQL `tenants_for_admin()` (migration 042) i Next-databasen + demokontot som extra rad; fel → 503 "Kundlistan gick inte att hämta." | `components/admin/BytKund.tsx`, `components/leads/LeadslistorView.tsx` (välj målkund vid kopiera/flytta lista) | `app/api/admin/kunder/route.ts`, Postgres-funktion | Plattformsadmin, annars 404 | nej |
| AP13 | "Kör agent"-knappen till agentsajten (supportportalen) med engångsbiljett | GET `/api/agentsajt/{agent}/sso`; okänd agent, ej inloggad eller saknad produkt → 404; viewer → 404 (portalen har ingen läsroll); biljett lever 60 s, skapas vid klicket; utan hemlighet/nyckel: rak länk till sajtens inloggning; svar 303 | Knappar i dashboardens agentkort (`lib/agentsajt.ts`-registret) | `app/api/agentsajt/[agent]/sso/route.ts`, `lib/bokforing/sso.ts` | Inloggad kund med agentens produkt, ej viewer | nej |
| AP14 | Inloggning (Auth.js) | `/api/auth/signin`, `/callback/<provider>`, `/session`, `/csrf`; anonym med flit; CSRF på POST, OAuth `state`+PKCE | `/login`, `LoginForm.tsx` | `app/api/auth/[...nextauth]/route.ts`, `lib/auth` | Alla | – (se app-01) |
| AP15 | Email Studio: skriv om ett mejl med AI (kortare, skriv om, förbättra, personalisera, översätt, A/B, uppföljning, analysera, längre) | POST `{action, draft/body, subject, context, locale}`; okänd åtgärd → `improve`. Anonym: alltid handskrivet exempelsvar (sex exempelbolag eller startsidans exempel), aldrig modellen, `simulated:true`. Inloggad: modell enligt `lib/llm/modellval` (OpenAI → Vertex → Gemini → DeepSeek med dataskyddsspärr), 3 försök à 25 s, ärliga fel: 503 ingen modell/kreditslut, 429 kvot, 502 tillfälligt; svaret putsas (`putsaText`), `simulated:false`. Struktur B bevaras. Hårda regler: ingen prislista, högst ~120 ord, ett möte som mål, inget påhittat namn | `components/email/EmailStudioEditor.tsx`, inbäddad i `IrisGranskning.tsx`, `IrisBolag.tsx`, `Bolagssida.tsx`, `LeadsRunForm.tsx`, `ProductPage.tsx`, `CrmDemo.tsx`; även serveråtgärden `lib/actions/emails.ts:refineEmail` | `app/api/email-studio/route.ts`, modell direkt från Next | Anonym (bara exempel) och inloggad | delvis (felen svenska; `locale` styr modellens språk) |
| AP16 | Hälsokontroll för webbtjänsten | GET anonym; 503 om databasen saknas/inte svarar | Railway healthcheck, `overvakning.yml` | `app/api/health/route.ts` | Anonym | – |
| AP17 | Publik supportlänk skapar en ny chattsession | GET `/chat/{tenant}` → 307 till `/chat/{tenant}/{uuid}`; okänd tenant → 404 | Kundens hemsida, mejl | `app/chat/[tenant]/route.ts` | Anonym | – |
| AP18 | Spårad demolänk i utskick: klick och besök | GET loggar klick (`demolank_klick`) och skickar 302 till målet (med `besok=<token>` bara om egen domän); fel/okänd token → `/demo`. HEAD loggar inget. POST (beacon från `DemoBesok.tsx`) loggar riktigt besök, alltid 204 | `components/demo/DemoBesok.tsx`; listan "Vilka har besökt demon" i `IrisErbjudanden.tsx` (via AP81). Token måste matcha `^[A-Za-z0-9_-]{6,64}$`; målet räknas mot sajtens publika origin (`appBasUrl`), icke-http(s)-mål blir `/demo` | `app/prova/[token]/route.ts`, security definer-funktioner (migration 116) | Anonym mottagare | – |
| AP19 | Inloggningsgrind och CSP för inbäddning | Matcher: `/dashboard`, `/settings`, `/onboarding`, `/crm`, `/admin`, `/login`, `/embed`. Utan session på skyddad rutt → `/login?next=`; med session på `/login` → `/dashboard`; `/embed/{nyckel}` får `frame-ancestors` per tenant och `noindex`. `/api` täcks inte (rutterna grindar själva) | – | `proxy.ts` | – | – |
| AP20 | `llms.txt` för AI-sökmotorer | GET; text ur `lib/llms.ts` med kontaktadressen; 404 "Not found" när anropet kommer på en kunds egen domän (`getCurrentTenant()`); `Cache-Control: public, max-age=3600`; inte grindad på miljö (robots.txt säger nej utanför produktion) | – | `app/llms.txt/route.ts` | Anonym | – |

## 2. Backenden: hälsa, chatt, support och inkorg

Grind anges som dependency. "Anropare" är det grep hittade i `components/`,
`app/`, `lib/`; "ingen i appen" betyder att bara skript, tester, externa system
eller supportportalen (`support-webb/`, nås via AP13) använder vägen.

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP21 | Hälsa, liveness och readiness | `GET /health` (läge simulation/live, modell, lagring, jobbkö, commit), `/health/live` (alltid ok), `/health/ready` (200 även degraderad med `warnings`; 503 bara när lagringen är nere) | Railway, `overvakning.yml` (var tredje timme) | `main.py` | Öppen | – |
| AP22 | Starta ett chattsvar från agenten (publik, testchatt, egen integration) | `POST /api/chat` → 202 med `job_id`; jobbet körs i Redis-strömmen `chatt` om Redis finns, annars `create_task`; pollas via AP24 | AP2, AP5 | `chat.py` | `require_tenant` | nej |
| AP23 | Läs tillbaka ett samtal | `POST /api/chat/samtal`; bara sessionsidentiteter | AP3, AP6 | `chat.py`, överlämningstabellerna (snajp-03) | `require_tenant` | nej |
| AP24 | Läs ett jobbs läge | `GET /api/jobs/{id}`; jobbet slås upp inom tenanten (annars 404 "Jobbet finns inte eller har städats bort."); auto-fail efter 600 s utan förlopp (`JOB_TIMEOUT_SECONDS` i `jobs/store.py`; `Forlopp.satt` flyttar klockan), posten lever 3 600 s (TTL). Svaret: `status`, `result` utan stegloggarnas texter (`stegtexter.utan_stegtexter`), `error` översatt från leverantörens kvotfel, `fas` (laser/soker/skriver/kontrollerar/arbetar) medan chattjobbet går och `forlopp` för jobb med förlopp | AP4, AP6, AP7 | `chat.py`, `app/jobs/store.py` (Redis eller minne) | `require_tenant` | nej |
| AP25 | Lista överlämnade chattar med orsakstext | `GET /api/chattar`, högst 100 | `JournalVy.tsx`, `dashboard/Aktivitet.tsx` (supporttal, överlämningslistan); portalens `ChattarVy` | `chattar.py`, `list_chat_handovers` | `require_tenant` | nej |
| AP26 | Öppna en överlämnad chatt | `GET /api/chattar/{customer_id}` | Ingen i appen (portalen) | `chattar.py` | `require_tenant` | nej |
| AP27 | Medarbetaren svarar i en överlämnad chatt | `POST /api/chattar/{customer_id}/svar` → 201; svaret syns i besökarens fönster via AP3 | Ingen i appen (portalen) | `chattar.py` | `require_tenant` | nej |
| AP28 | Lämna tillbaka chatten till agenten | `POST /api/chattar/{customer_id}/aterlamna` | Ingen i appen (portalen) | `chattar.py` | `require_tenant` | nej |
| AP29 | Läs och spara supportagentens eskaleringsregler | `GET`/`PUT /api/support/config` (agentinställningar för support) | `components/settings/SupportEskalering.tsx` | `support_config.py`, `get_agent_settings` | `require_tenant` | nej |
| AP30 | Supportöversiktens tal och veckograf | `GET /api/support/oversikt` | `components/snajp/SupportOversikt.tsx` | `support_oversikt.py` | `require_tenant` | nej |
| AP31 | Kundens egna system (HTTP-verktyg, MCP): lista, skapa, ändra, ta bort | `GET`, `POST` (201), `PATCH /{id}`, `DELETE /{id}` under `/api/integrationer`; hemligheter returneras maskerade | Läsning i `IrisAutomation.tsx`; skrivning bara i portalens `IntegrationerVy` | `integrationer.py`, `app/integrationer/lagring` | `require_tenant` | nej |
| AP32 | Lista en integrations verktyg och prova den | `GET /api/integrationer/{id}/verktyg`, `POST /{id}/prova` | Ingen i appen (portalen) | `integrationer.py` | `require_tenant` | nej |
| AP33 | Kanalanslutningar (WhatsApp, Messenger, Slack, Teams): lista, skapa, ändra, ta bort, prova | `GET`, `POST` (201, okänd kanal avvisas), `PATCH /{id}`, `DELETE /{id}`, `POST /{id}/prova` under `/api/kanaler` | Ingen i appen (portalen) | `kanaler.py`, `app/kanaler/lagring` | `require_tenant` | nej |
| AP34 | Ta emot kanalwebhooks | `GET /api/kanaler/{kanal}/{tenant}/{anslutning}/webhook` (verifiering), `POST …/webhook` (meddelande in → agentsvar i bakgrunden, `kanaler/mottagning.py` create_task) | Externa plattformar | `kanaler.py` | Öppen; kanalens signatur verifieras; avtalsgrinden kan stoppa | – |
| AP35 | Klassa mejl (demo och API) | `POST /api/triage`; läsande | AP8 | `triage.py` | `require_tenant` (demonyckel via AP8) | nej |
| AP36 | Hämta ärende med historik / kundens historik | `GET /api/tickets/{id}`, `GET /api/customers/{id}/history` | Ingen i appen (dokumenterad i `IntegrationSection.tsx` för kundens egen integration) | `tickets.py` | `require_tenant` | nej |
| AP37 | Skapa tenant och API-nyckel | `POST /api/keys` → 201; skapar (eller återanvänder) tenant med slug (härledd ur namnet om den saknas, å/ä/ö → a/o), nyckeln `snajp_live_…` i klartext EN gång (bara hashen sparas, "Spara nyckeln nu — den visas aldrig igen."). `kraver_avtal` utelämnad = avtalsgrinden PÅ; bara test-, demo- och interna tenants skickar false. Slug som börjar på `testkund-` får exempelkunskapsbasen seedad | `lib/snajp/testtenant.ts`, `lib/actions/onboarding.ts` (provisionering), skript | `keys.py` | `require_master_key` | nej |
| AP38 | Kunskapsbasen: lista, lägg till, ta bort artikel | `GET /api/kb`, `POST /api/kb` (201), `DELETE /api/kb/{id}` | `settings/Kunskapsbas.tsx`, `SupportChat.tsx` (spara svar som artikel) | `kb.py` | `require_tenant` | nej |
| AP39 | Skanna kundens webbplats till artikelförslag | `POST /api/kb/skanna` → 202, körs i bakgrunden (create_task); `GET /api/kb/forslag` visar senaste skanning och väntande utkast; `POST /api/kb/forslag/beslut` godkänner/avvisar | `settings/WebbplatsForslag.tsx`, `lib/snajp/webbplatsskanning.ts` (onboarding) | `kb.py` | `require_tenant` | nej |
| AP40 | Läs text ur en PDF till kunskapsbasen | `POST /api/kb/extrahera` | `SupportChat.tsx` | `kb.py` | `require_tenant` | nej |
| AP41 | Inkorgar: lista, upptäck inställningar, koppla, koppla ur | `GET /api/inbox/mailboxes`, `GET …/upptack?adress=` (3–254 tecken), `POST /api/inbox/mailboxes` (provar inloggning, 45 s budget), `DELETE …/{id}` (hämtade mejl blir kvar som ärenden) | `settings/Inkorgar.tsx`, `snajp/Dashboard.tsx` | `inbox.py` | `require_tenant` | nej |
| AP42 | Synka inkorgen nu | `POST /api/inbox/sync`; hämtar via IMAP och processar varje mejl i FastAPI `BackgroundTasks` | `Inkorgar.tsx`, `Dashboard.tsx` | `inbox.py` | `require_tenant` | nej |
| AP43 | Lägg in exempelmejl / externt mejl | `POST /api/inbox/mock` (201, processas i bakgrunden), `POST /api/inbox/ingest` (201) | `Dashboard.tsx` (mock); ingest: ingen i appen | `inbox.py` | `require_tenant` | nej |
| AP44 | Lista inkorgen med räknare | `GET /api/inbox` (filter, kategori- och statusräknare) | `Dashboard.tsx`, portalens `InkorgVy` | `inbox.py` | `require_tenant` | nej |
| AP45 | Provsortera mejl i realtid | `POST /api/inbox/sortera` | `Dashboard.tsx` | `inbox.py` | `require_tenant` | nej |
| AP46 | Åtgärder på ett mejl: läs, klassa om, ta över, markera hanterat, processa om, befordra testmejl | `GET /api/inbox/{id}`, `POST …/klassa`, `…/takeover`, `…/hanterad`, `…/processa-om`, `…/befordra` | `Dashboard.tsx` (alla utom processa-om; processa-om: ingen anropare hittad) | `inbox.py` | `require_tenant` | nej |
| AP47 | Supportutkast: godkänn och skicka, omformulera, avvisa | `POST /api/drafts/{id}/approve`, `/omformulera`, `/reject` | `Dashboard.tsx` | `drafts.py` | `require_tenant` | nej |
| AP48 | Kategoriregler (automatiskt / granska) | `GET`/`PUT /api/rules` | `settings/SupportRegler.tsx` | `rules.py`, `get_category_rules` | `require_tenant` | nej |
| AP49 | Avsändardomän: skapa, läs, verifiera | `POST`/`GET /api/sending-domain`, `POST /api/sending-domain/verify` | Ingen i appen | `sending_domains_api.py` | `require_tenant` | nej |
| AP50 | Resend-webhooks: domänstatus, studs och klagomål | `POST /api/webhooks/resend/domains`, `POST /api/webhooks/resend/emails` (studs/klagomål stoppar vidare utskick, send_guard regel 5e) | Resend | `sending_domains_api.py` | Öppen; signatur kontrolleras | – |
| AP51 | Publik demochatt med kaksession | `POST /api/demo/chat`; sätter httponly-kaka för sessionen | Ingen anropare hittad i appen | `demo.py` | Öppen | nej |
| AP52 | Veckoanalys | `GET /api/analytics/weekly?weeks=1–52` (standard 8) | `dashboard/Analys.tsx`, `leads/LeadsDiagram.tsx` (24 veckor) | `analytics.py` | `require_tenant` | nej |
| AP53 | Kundens förbrukning per dag och budget | `GET /api/usage?days=` | `JournalVy.tsx` (30), `dashboard/Aktivitet.tsx` (60) | `usage.py` | `require_tenant` | nej |

## 3. Backenden: Leads (Iris), `leads.py`

Alla rader: `require_tenant`, kundens egna data. Vyernas beteende står i app-03,
app-04 och app-05; här står vägen, vad den gör och vem som anropar den.

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP60 | Affärskontext (produktmarknadsföring) som dokument | `POST /api/leads/context-docs` (201), `GET …?kind=` | `lib/actions/affarskontext.ts`, `lib/snajp/standard.ts` (standardvärden vid provisionering), direkt mot backenden med kundnyckel | `leads.py` | Kund | nej |
| AP61 | Onboardingläge, kontextpaket och onboardingchatt för Iris | `GET /api/leads/onboarding/status`, `GET /api/leads/context-pack`, `POST /api/leads/onboarding/chat` | Ingen i appen (status bara i demons stubbe `lib/demo/oversikt.ts`) | `leads.py`, `leads_agent.run_onboarding_turn` | Kund | nej |
| AP62 | Skapa ett prospekt för hand / exempelprospekt | `POST /api/leads/prospects` (201), `POST /api/leads/prospects/exempel` (201) | Skapa: `IrisBolag.tsx`, `Bolagssida.tsx`, `Bolagsregister.tsx`; exempel: ingen anropare hittad | `leads.py` | Kund | nej |
| AP63 | Lista prospekt (leads) | `GET /api/leads/prospects` (`limit` standard 500, högst 1000; `lista=1` ger Iris-listans smala rader med egen sidstorlek `LISTLAGE_SIDA`; `offset`; svaret bär `fler` och `nasta` och klienten hämtar tills `fler` är falskt; `?arkiverade=1` visar bara arkiverade, `?bortvalda=1` bara bortvalda, annars döljs båda samt ringlistans och listornas bakgrundsprospekt; ny-bolag med köad research visas som `researching`); webbplatsbedömningen ingår bara om `webbpool.far_se` | `LeadsTabell.tsx`, `Kontakter.tsx`, `Bolagsregister.tsx`, `LeadsDiagram.tsx`, `IrisBolag.tsx`, `Bolagssida.tsx` | `leads.py` | Kund; webbfälten bara admin/webbyråer | nej |
| AP64 | Fördelningen av prospekt (Iris, ringlista, ej kvalificerade, utan webbplats) | `GET /api/leads/prospects/fordelning` | `LeadsDiagram.tsx` | `leads.py` | Kund | nej |
| AP65 | Läs ett prospekt | `GET /api/leads/prospects/{id}`; webbrevision grindad med `far_se` | `IrisBolag.tsx`, `Bolagssida.tsx`, `LeadsTabell.tsx` | `leads.py` | Kund; webbfälten bara admin/webbyråer | nej |
| AP66 | Lägg till en källa på ett prospekt | `POST /api/leads/prospects/{id}/sources` (201) | Ingen anropare hittad | `leads.py` | Kund | nej |
| AP67 | Senaste utkastet för ett prospekt | `GET /api/leads/prospects/{id}/utkast` | `IrisBolag.tsx`, `Bolagssida.tsx` | `leads.py` | Kund | nej |
| AP68 | Befordra ett lead (listspår → Iris) / degradera | `POST …/{id}/befordra`, `POST …/{id}/degradera` | Befordra: `LeadsTabell.tsx`, `Bolagsregister.tsx`; degradera: `Bolagsregister.tsx` | `leads.py` | Kund | nej |
| AP69 | Ändra prospektets bedömning/status (PATCH) | `PATCH /api/leads/prospects/{id}`; kan starta bakgrundsarbete (create_task, rad 2536/2842) | `LeadsTabell.tsx`, `Bolagsregister.tsx` | `leads.py` | Kund | nej |
| AP70 | Iris röstdokument (soul) | `GET`/`PUT /api/leads/soul` | `components/SoulEditor.tsx`, `lib/snajp/standard.ts` | `leads.py` | Kund | nej |
| AP71 | Önskemål till agenten (fritext som bakas in i instruktionen) med förhandsgranskning och versioner | `GET /api/agent/onskemal/{agent}`, `POST …/forhandsgranska` (bakar in utan att spara, visar ändringar med skäl), `PUT …` (spara), `POST …/aterstall/{doc_id}` | `settings/AgentOnskemal.tsx` | `leads.py`, `app/leads/onskemal.py` | Kund | nej |
| AP72 | Kör ett researchsteg / skriv ett utkast för ett prospekt | `POST /api/leads/research/step` (ingen anropare hittad); `POST /api/leads/outreach/draft` → 202 + `job_id`, utkastet skrivs i bakgrunden (create_task) och pollas via AP7 | Utkast: `IrisBolag.tsx`, `Bolagssida.tsx`, `Bolagsregister.tsx` | `leads.py` | Kund | nej |
| AP73 | Lista körningar (äldre format) | `GET /api/leads/runs` | Ingen i appen (bara demons stubbe) | `leads.py` | Kund | nej |
| AP74 | Svar från prospekt: registrera och lista | `POST /api/leads/svar` (ingen anropare i appen), `GET /api/leads/svar` | `Svar.tsx`, `AttGora.tsx` | `leads.py` | Kund | nej |
| AP75 | Kör uppföljningssvepet nu | `POST /api/leads/uppfoljning/svep`; samma svep som bakgrundsloopen (AP162) | Ingen anropare i appen | `leads.py`, `follow_up_generator` | Kund | nej |
| AP76 | Agentens förbättringsförslag: lista, godkänn, öppna som ärende, avfärda | `GET /api/agent/forslag?status=ny`, `POST …/{id}/godkann`, `POST …/{id}/arende` (201), `POST …/{id}/avfard` | `SupportChat.tsx`, `leads/AgentLarande.tsx` (Lärande) | `leads.py` | Kund | nej |
| AP77 | Feedback till agenten | `POST /api/agent/feedback` (201), `GET /api/agent/feedback` | `SupportChat.tsx` (POST), `AgentLarande.tsx` (GET) | `leads.py` | Kund | nej |
| AP78 | Skickade utskick och antal | `GET /api/leads/skickat?limit=500` (standard 200; schemalagda godkända utkast står överst med `skickas_tidigast`; `svarat` när tråden fått svar efter utskicket, och då bär raden hela `konversation`), `GET /api/leads/skickat/antal?dagar=28` (1–366) | `IrisInkorg.tsx` och `LeadsTabell.tsx` hämtar; `SkickatLista.tsx` visar det de hämtat (anropar inte själv) | `leads.py` | Kund | nej |
| AP79 | Leadsinställningar (autonomi, sändning, automation, autopilot, produkter, eskalering) | `GET`/`PUT /api/leads/config` | `LeadsControls.tsx`, `IrisAutomation.tsx`, `IrisProdukter.tsx`, `IrisEskalering.tsx`, `Bolagssida.tsx`, `lib/snajp/standard.ts` | `leads.py` | Kund | nej |
| AP80 | Erbjudanden (offerter till utkasten) | `GET`/`PUT /api/leads/erbjudanden` | `IrisErbjudanden.tsx`, `lib/snajp/standard.ts` | `leads.py` | Kund | nej |
| AP81 | Vilka har besökt demon (spårade länkar) | `GET /api/leads/demobesok` | `IrisErbjudanden.tsx` | `leads.py`, tabellerna från migration 116 | Kund | nej |
| AP82 | Iris-profilen (målgrupp) och omtolkning | `GET /api/leads/profil`, `POST /api/leads/profil/tolka-om` | `IrisProfil.tsx`, `lib/snajp/standard.ts` | `leads.py` | Kund | nej |
| AP83 | Jevs statistik (första filtret) | `GET /api/leads/jev/statistik` | `IrisProfil.tsx` | `leads.py` | Kund | nej |
| AP84 | Körningar: lista och läsa en | `GET /api/leads/korningar?limit=`, `GET /api/leads/korningar/{job_id}` | `IrisKorningar.tsx`, `LeadsOversikt.tsx`, `dashboard/Aktivitet.tsx`, `LeadsRunForm.tsx` | `leads.py`, `leads_korningar` (snajp-01) | Kund | nej |
| AP85 | Styr en körning: pausa, återuppta, avbryt, fortsätt | `POST /api/leads/korningar/{job_id}/{pausa|aterupta|avbryt|fortsatt}`. 404 "Körningen finns inte."; 409 "Körningen pågår inte och kan inte styras." (fortsätt har egen 409-text: "Körningen kan inte fortsätta: den pågår, nådde målet eller avbröts.") Paus: inga nya prospekt köas. Avbryt: köade hoppar över research, slutorsak `avbruten`. Fortsätt: öppnar en avslutad körning under målet och fyller på (409 om målet nåtts, avbruten eller pågår). Återuppta/avbryt väcker motorn via leadsströmmen | `IrisKorningar.tsx` | `leads.py`, `set_korning_styrning` | Kund | nej |
| AP86 | Körningens utkast: lista, skriv, skicka (synkront eller som jobb med förlopp) | `GET …/korningar/{id}/utkast`, `POST …/utkast/skriv` (202), `POST …/utkast/skicka`, `POST …/utkast/skicka-jobb` (202, `jobs.bakgrund` med förlopp) | `KorningensUtkast.tsx` | `leads.py` | Kund | nej |
| AP87 | Granskningskön: lista, ändra text, godkänn, avvisa | `GET /api/leads/queue`, `PUT /api/leads/queue/{id}`, `POST …/{id}/approve`, `POST …/{id}/reject` | `IrisGranskning.tsx`, `LeadsControls.tsx`, `AttGora.tsx`, `IrisBolag.tsx`, `Bolagssida.tsx`, `KorningensUtkast.tsx`, `Uppfoljningar.tsx` | `leads.py`, `send_queue` | Kund | nej |
| AP88 | Schemalägg, skicka nu, tillbaka till Iris | `POST /api/leads/queue/schemalagg` (ny tid, inom 60 dagar), `POST …/{id}/skicka-nu` (direkt även utanför sändfönstret vardagar 08–16), `POST …/tillbaka-till-iris` (202) | `SkickatLista.tsx` | `leads.py` | Kund | nej |
| AP89 | Provmejl till sig själv | `GET /api/leads/provmejl/mottagare`, `POST /api/leads/provmejl` | `ProvmejlKnapp.tsx` | `leads.py` | Kund | nej |
| AP90 | Starta en Iris-körning | `POST /api/leads/runs/batch` → 202; köas på leadsströmmen (`crm:jobb:leads`, överlever deploy) eller create_task; aldrig omtagen av proxyn | `LeadsRunForm.tsx`, `LeadsSnabbsok.tsx` | `leads.py` | Kund | nej |
| AP91 | Processa om valda prospekt (skriv utkast ur befintlig research) | `POST /api/leads/prospects/processa-om` → 202 | `LeadsTabell.tsx`, `IrisBolag.tsx`, `Bolagssida.tsx`, `Bolagsregister.tsx` | `leads.py` | Kund | nej |
| AP92 | Beställ en leadslista (listspåret) / kombinera listor | `POST /api/leads/listor` (202, bakgrund), `POST /api/leads/listor/kombinera` (201) | `LeadslistorView.tsx`, `Saljlista.tsx` | `leads.py` | Kund | nej |
| AP93 | Lista och läsa leadslistor | `GET /api/leads/listor`, `GET /api/leads/listor/{id}` (webbfälten bara med `far_se`) | `LeadslistorView.tsx`, `LeadsOversikt.tsx`, `Saljlista.tsx` | `leads.py` | Kund; webbfälten bara admin/webbyråer | nej |
| AP94 | Listrad → lead, utkast för listan, köa en rads utkast, pröva om listan | `POST …/listor/{id}/items/{item}/prospekt`, `POST …/listor/{id}/utkast` (202), `POST …/items/{item}/koa`, `POST …/listor/{id}/omprova` (202, bakgrund; webbyråer får ny webbrevision) | `LeadslistorView.tsx` (koa: ingen anropare hittad) | `leads.py` | Kund | nej |
| AP95 | Ta bort en lista | `DELETE /api/leads/listor/{id}` | `LeadslistorView.tsx` | `leads_massatgard.py` | Kund | nej |
| AP96 | Arkivera eller radera prospekt i mängd | `POST /api/leads/prospects/arkivera`, `POST /api/leads/prospects/radera` | `LeadsTabell.tsx` | `leads_massatgard.py` | Kund | nej |

## 4. Backenden: Leads-sviten, konversationer, uppföljningar, kampanjer

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP100 | Bolagets tidslinje | `GET /api/leads/prospects/{id}/tidslinje`, nyast först | `leads/Tidslinje.tsx` | `leads_suite.py` | Kund | nej |
| AP101 | Logga ett samtal (utfall Ej svar, Återkom, Ej intresserad, Kontakta inte, Möte bokat) | `POST …/{id}/samtal` (201) | `Samtalslista.tsx` | `leads_suite.py`, `app/leads/samtal.py` | Kund | nej |
| AP102 | Ringlistan och återkopplingslistan, med antal för i dag | `GET /api/leads/samtal?lista=aterkoppling|ring`, `GET /api/leads/samtal/antal` | `Samtalslista.tsx`, `AttGora.tsx` | `leads_suite.py` | Kund | nej |
| AP103 | Anteckningar och uppgifter på ett bolag | `POST …/{id}/anteckningar` (201), `POST …/{id}/uppgifter` (201), `PATCH /api/leads/uppgifter/{id}`, `GET /api/leads/uppgifter?oppna=` | `Tidslinje.tsx`, `LeadsTabell.tsx` | `leads_suite.py` | Kund | nej |
| AP104 | Sparade vyer i leadstabellen | `GET`/`POST /api/leads/vyer` (201), `DELETE …/{id}` (204) | `LeadsTabell.tsx`, `lib/leads/suite.ts` | `leads_suite.py` | Kund | nej |
| AP105 | Importera kundens egen fil (annat CRM, kalkylblad) med förhandsgranskning | `POST /api/leads/import/granska` (vilka rader är befintliga/nya), `POST /api/leads/import` (201) | `ImportLista.tsx` | `leads_suite.py` | Kund | nej |
| AP106 | Konversationer: lista med räknare, läsa tråd, markera läst | `GET /api/leads/konversationer`, `GET …/{tråd}`, `POST …/{tråd}/last` | `Konversationer.tsx`, `KonversationsTrad.tsx` | `leads_konversationer.py` (migration 149) | Kund | nej |
| AP107 | Svarsutkast i en tråd: spara, skicka, kassera, återställ, skriv om med Iris | `PUT …/{tråd}/utkast`, `POST …/utkast/skicka`, `…/utkast/kassera`, `…/utkast/{msg}/aterstall`, `…/utkast/generera` (202, `jobs.bakgrund`, nyckel `konversation:{tråd}`; kräver riktig modell och leadsbudget; förloppet läses INTE via jobbet utan ur trådens händelselogg: `generering_startad`, sedan `utkast` eller `generering_fel` med skäl, så det syns efter omladdning; pågår en omskrivning svarar den `{pagar:true}` utan nytt jobb; vyn pollar inte `job_id` utan laddar om tråden) | `KonversationsTrad.tsx` | `leads_konversationer.py` | Kund | nej |
| AP108 | Byt steg i tråden / lägg in en extern händelse | `POST …/{tråd}/steg`, `POST …/{tråd}/extern` (201) | `KonversationsTrad.tsx` | `leads_konversationer.py` | Kund | nej |
| AP109 | Notiser: lista, antal i navigationen, markera lästa | `GET /api/leads/notiser?limit=30`, `GET …/antal` (0 före migration 149), `POST …/last` | `Konversationer.tsx`, `lib/leads/konversationer.ts` | `leads_konversationer.py` | Kund | nej |
| AP110 | Uppföljningar: lista och skriv nu för markerade | `GET /api/leads/uppfoljningar`, `POST …/skapa` (202) | `Uppfoljningar.tsx` | `leads_uppfoljningar.py` | Kund | nej |
| AP111 | Bolagssökning över alla leads | `GET /api/leads/sok?q=` (namn, kontakt, e-post …) | `BolagsSok.tsx` | `leads_uppfoljningar.py` | Kund | nej |
| AP112 | Kampanjer: lista med utfall, läsa, skapa, skicka | `GET /api/leads/kampanjer`, `GET …/{id}`, `POST /api/leads/kampanjer` (202, utkast köas i bakgrunden), `POST …/{id}/skicka` (synkront; ingen anropare), `POST …/{id}/skicka-jobb` (202, `jobs.bakgrund` med förlopp) | `Kampanjer.tsx` | `leads_kampanjer.py` | Kund | nej |

## 5. Backenden: adminytan (`/api/admin/*`, master-nyckel)

Alla rader utom AP140 (HMAC-signatur) och AP141 (egen schemanyckel): `require_master_key` på routern (rättat vid kontroll: AP138 och AP139 ÄR master-grindade); varje anrop
loggas i `audit_logs` med plattformsadminens id (`X-Snajp-Admin`). Läsning når
backenden via `lib/data/admin.ts` eller AP11; skrivning via serveråtgärderna i
avsnitt 8.

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP120 | Alla kunder med nyckeltal (aktiv, produkter, körningar, ärenden, senaste aktivitet) | `GET /api/admin/tenants` | `lib/data/admin.ts:listTenants` → `/admin`, `/admin/kunder` (`Portfoljvy.tsx`, `Kundtabell.tsx`); `lib/snajp/kundregister.ts` | `admin.py` | Plattformsadmin | nej |
| AP121 | Agentkörningar: per kund, alla (filter, `sammandrag=true`), en körning med steg | `GET /tenants/{id}/runs`, `GET /runs`, `GET /runs/{id}` | `lib/data/admin.ts` → `/admin/korningar`, `/admin/korningar/[id]` (`KorningsOversikt.tsx`) | `admin.py` | Plattformsadmin | nej |
| AP122 | Insyn: vad agenten ser för en kund (instruktioner, skills, kunskapsbas), skillfil, kb-prov | `GET /tenants/{id}/insyn?agent=&kanal=`, `GET /skills/fil?skill=&fil=` (bara registrerade filer, orörd mot manifestet), `POST /tenants/{id}/insyn/kb-prov` (vilka artiklar en fråga hade hämtat) | `/admin/kunder/[id]/insyn` (`components/admin/insyn/Insynsvy.tsx`), `lib/actions/insyn.ts` | `admin.py`, `app/agentcore/insyn.py` | Plattformsadmin | nej |
| AP123 | En körnings kedja för ett bolag (utfall per nod, grindar, var den stannade) | `GET /prospects/{id}/kedja?tenant_id=` (tenant krävs) | `lib/actions/insyn.ts:hamtaKedja` → Insynsvy | `admin.py` | Plattformsadmin | nej |
| AP124 | Plattformshändelser (fel, varningar) | `GET /api/admin/events?level=` | `lib/data/admin.ts:listEvents` → `/admin/handelser` (`Handelselista.tsx`, `FelOchEskaleringar.tsx`) | `admin.py`, `platform_events` | Plattformsadmin | nej |
| AP125 | Kundens inkorg, utkast och leadsunderlag sett av admin | `GET /tenants/{id}/inbox`, `GET /tenants/{id}/drafts` (samma granskningskö som kunden ser), `GET /tenants/{id}/leads-underlag?limit=200` (källor, material, bedömning per lead) | Ingen i appen; leads-underlag används av `scripts/granska_leads_underlag.py`, `scripts/ombedom_leads.py` | `admin.py` | Plattformsadmin | nej |
| AP126 | Förbrukning per kund (fakturering och kostnad) | `GET /api/admin/usage` | Ingen anropare hittad i appen (agentanvändningssidorna kan läsa annan väg, se Oklarheter) | `admin.py` | Plattformsadmin | nej |
| AP127 | Diagnos av mejlvägen och provmejl | `GET /sandvag?vard=&port=`, `POST /sandvag/prov?till=` (ett provmejl) | Ingen i appen (körs för hand, STATUS.md) | `admin.py` | Plattformsadmin | nej |
| AP128 | Ombedöm sparade Iris-leads efter regelskärpning | `POST /tenants/{id}/leads-ombedom`; torrkör som standard, `apply=true` köar research utan utkast | `scripts/ombedom_leads.py` | `admin_ombedom.py` | Plattformsadmin | nej |
| AP129 | Kundregistret: läsa, spara, kontaktpersoner | `GET`/`PUT /tenants/{id}/kunddata`, `POST /tenants/{id}/kontakter`, `PUT`/`DELETE …/kontakter/{id}` | `/admin/kunder/[id]/data` (`components/admin/Kunddata.tsx`) via `lib/actions/kunddata.ts`; `lib/snajp/kundregister.ts` | `admin_kunddata.py` | Plattformsadmin | nej |
| AP130 | Gallringens insyn: översikt och logg per kund | `GET /api/admin/gallring?limit=`, `GET /tenants/{id}/gallring` | Ingen anropare hittad i appen | `admin_gallring.py`, `ss_gallringslogg` | Plattformsadmin | nej |
| AP131 | Agentinstruktionerna (gemensamt lager, support, leads): läsa, förhandsgranska feedback, spara, återställ version | `GET /instruktioner?agent=`, `POST /instruktioner/forhandsgranska`, `PUT /instruktioner`, `POST /instruktioner/{id}/aterstall` (ny rad, `kalla='aterstalld'`) | `components/admin/Agentinstruktioner.tsx` via `lib/actions/agentinstruktioner.ts` | `admin_profil.py` | Plattformsadmin | nej |
| AP132 | Kundens agentprofil: läsa alla fält och var de hamnar i prompten, spara skickade fält | `GET /tenants/{id}/profil?agent_type=`, `PUT /tenants/{id}/profil` (None = rör inte) | Kundsidan i admin via `lib/actions/agentinstruktioner.ts:hamtaKundprofil/sparaKundprofil` | `admin_profil.py` | Plattformsadmin | nej |
| AP133 | Stäng av / slå på en kund, sätt kundstatus | `PUT /tenants/{id}/aktiv`, `PUT /tenants/{id}/status` | `lib/actions/avstangning.ts`, `lib/actions/kundstatus.ts` (revaliderar `/admin/paket`) | `admin_profil.py` | Plattformsadmin | nej |
| AP134 | Bädda in kunskapsartiklar som saknar vektor | `POST /kb/badda-in?apply=&tenant_id=` | `scripts/badda_in_kb.py` | `admin_profil.py` | Plattformsadmin | nej |
| AP135 | Konvertera en testkund till en riktig kund | `POST /api/admin/konvertera`; torrkör som standard, `apply` skriver över målets konfiguration, valfria prospekt | `components/admin/KonverteraTestkund.tsx` via `lib/actions/konvertera.ts`; `scripts/konvertera_testkund.py` | `admin_konvertera.py` | Plattformsadmin | nej |
| AP136 | Webbpoolens bakåtfyllnad: läge och kör | `GET`/`POST /webbpool/bakatfyll` (`apply`, `max_bedom`); krediter kvar hos ScrapeGraph | `scripts/webbpool_bakatfyll.py` | `admin_webbpool.py` | Plattformsadmin; rör webbplatsbedömningen | nej |
| AP137 | Normalisera utkast hos alla kunder (svep) | `POST /api/admin/leads/normalisera-utkast` | Ingen anropare hittad | `admin_utkastsvep.py` | Plattformsadmin | nej |
| AP138 | Kopiera eller flytta en leadslista till en annan kund | `POST /listor/{id}/till-kund`; bara `LISTRADSFALT` följer med (ingen webbrevision, inga kontakter som inte hör dit) | `LeadslistorView.tsx` via `lib/actions/listor.ts` | `admin_listor.py` | Plattformsadmin | nej |
| AP139 | Flytt från spegeln (development) till main: status, kandidater, paket, skicka | `GET /flytt/status`, `GET /flytt/kandidater?slug=`, `POST /flytt/paket` (signerat, skickas inte), `POST /flytt/skicka` (kvitto per rad i `dev_flytt_ko`) | "Byt kund"-panelen (bara i en spegel) via `lib/actions/flytt.ts` | `admin_flytt.py` | Plattformsadmin | nej |
| AP140 | Ta emot ett flyttpaket i main | `POST /api/admin/flytt/importera`; HMAC-signatur i huvudet; vägrar i en spegel (409); idempotent på id | Development-miljöns AP139 | `admin_flytt.py` (`mottag`-routern) | Ingen master-nyckel; signaturen är grinden | nej |
| AP141 | Migrationsliggarens versioner för PR-kontrollen | `GET /api/drift/schema`; egen smal nyckel i huvudet; 404 när nyckeln inte är satt | `.github/workflows/migrera.yml` | `drift.py` | Egen nyckel | – |

## 6. Backenden: kvitton, bokföring och CRM

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP142 | Kvitton: kopplat mejlkonto, skanna inkorgen (synkront och som jobb med förlopp) | `GET /api/kvitton/mejlkonto`, `POST /api/kvitton/skanna`, `POST /api/kvitton/skanning` (202, `jobs.bakgrund` "kvittoskanning"), `GET /api/kvitton/skanning/{job_id}` (status, `lasta`, `totalt`) | `kvitton/KvittoYta.tsx`, `KvittoOversikt.tsx` | `kvitton.py` | `require_bookkeeping_tenant` (+ AP9) | nej |
| AP143 | Kvitton: lista, sammanfattning, rensa period, ladda upp underlag | `GET /api/kvitton`, `GET …/sammanfattning`, `DELETE …/period`, `POST …/underlag` (multipart) | `KvittoYta.tsx`, `KvittoOversikt.tsx` | `kvitton.py` | Som AP142 | nej |
| AP144 | Kvitton: godkänn, byt riktning (in/ut), exportera CSV, kvittochatt | `POST …/{id}/godkann`, `POST …/{id}/riktning`, `GET …/export.csv` (BOM, Content-Disposition), `POST …/chat` | `KvittoYta.tsx`, `KvittoChatt.tsx` | `kvitton.py`, `kvitto_agent` | Som AP142 | nej |
| AP145 | Bokföringsmotorn: underlag, periodrapport, rensa period, SIE4-export, chatt, avstämning | `POST`/`GET /api/bookkeeping/underlag`, `GET`/`DELETE …/period`, `GET …/period.sie`, `POST …/chat`, `POST …/avstamning` | Ingen nuvarande vy hittad (se AP10) | `bookkeeping.py` | `require_bookkeeping_tenant` | nej |
| AP146 | CRM-appens API-nycklar: lista, skapa (klartext en gång), återkalla | `GET /api/crm/nycklar`, `POST` (201), `DELETE …/{id}` (204; 404 om okänd) | `crm/app/UtvecklareVy.tsx` | `crm.py`, `app/crm/nycklar.py` | `require_tenant` (en omfångsnyckel kan inte skapa nycklar) | nej |
| AP147 | CRM-översikten (antal bolag per relation, personer, anslutningar, senaste synkkörningar) | `GET /api/crm/oversikt` | `OversiktVy.tsx`, `BolagVy.tsx`, `PersonerVy.tsx`, `synklage.tsx` | `crm.py` | `require_tenant` | nej |
| AP148 | CRM-API v1, bolag: lista (sök, sortera, markör), skapa eller uppdatera på org.nr, läsa, ändra, ta bort (mjukt), återställa | `GET`/`POST /api/crm/v1/companies`, `GET`/`PATCH`/`DELETE …/{id}`, `POST …/{id}/restore`; 422 `invalid_fields` med `fields[]` | `BolagVy.tsx`, `BolagFormular.tsx`, `OversiktVy.tsx`, `PersonerVy.tsx`, `Kommandopalett.tsx`; externa integrationer | `crm_v1.py` | `require_crm_nyckel` + omfång `crm:las`/`crm:skriv` | delvis (`message` en, `meddelande` sv) |
| AP149 | CRM-API v1, personer: samma operationer, upsert på e-post | `GET`/`POST /api/crm/v1/people`, `GET`/`PATCH`/`DELETE …/{id}`, `POST …/{id}/restore` | `PersonerVy.tsx`, `PersonFormular.tsx`, `BolagPanel.tsx` | `crm_v1.py` | Omfång `crm:las`/`crm:skriv` | delvis |
| AP150a | CRM-API v1, anslutningar och mappning | `GET /connections/systems`, `GET`/`POST /connections` (`crm:admin`), `GET`/`PATCH`/`DELETE /connections/{id}` (`crm:admin` för skrivning), `POST /connections/{id}/preview` (provar mappning utan att skriva) | `SynkVy.tsx`, `OversiktVy.tsx`, `synklage.tsx` (systems och preview: ingen anropare i appen) | `crm_v1.py` | Omfång `crm:las`/`crm:admin` | delvis |
| AP150b | CRM-API v1, synkkörningar: starta, lista, läsa med räknare och fel, skicka satser, slutföra; satssynk i ett anrop | `POST`/`GET /sync/runs`, `GET /sync/runs/{id}`, `POST /sync/runs/{id}/companies`, `…/people`, `…/complete`, `POST /sync/companies`, `POST /sync/people` | Läsning: `SynkVy.tsx`; skrivning: bara externa system | `crm_v1.py`, `app/crm/synk.py` | Omfång `crm:synk`/`crm:las` | delvis |
| AP150c | CRM-API v1, nyckeln som används och specifikationen | `GET /api/crm/v1/me`, `GET /api/crm/v1/openapi.json` | `UtvecklareVy.tsx` (länk till openapi) | `crm_v1.py` | Omfång `crm:las` | – |

## 7. Bakgrundsjobb, köer, webhooks in och schemalagda flöden

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP160 | Chattjobben överlever en deploy | Startas i `lifespan` när jobbkön är Redis: ström med `CHAT_WORKERS` (4) platser, engångssvep av okvitterade poster vid uppstart; utan Redis `create_task` i processen. Förlopp: AP24 (pollning); jobb som hänger failas efter 600 s (`JOB_TIMEOUT_SECONDS`; kommentaren i main.py säger 300, koden i `jobs/store.py` 600) | Chattfönstret visar "Agenten arbetar" tills svaret kommer | `main.py`, `app/jobs/stream.py`, `api/chat.py:hantera_strom_jobb` | – | – |
| AP161 | Leadskörningarnas per-prospektjobb överlever en deploy | Ström `crm:jobb:leads` med `LEADS_WORKERS` (10) platser; ett uppgivet jobb failar liggaren och listan (`ge_upp_leadsjobb`); utan Redis `create_task`. Förlopp: körningens rad (AP84) och AP7 | `IrisKorningar.tsx`, `LeadsRunForm.tsx` | `main.py`, `api/leads.py:hantera_leads_jobb` | – | – |
| AP162 | Sändaren för godkända utkast och bevakningen | `run_godkand_sandare` var `GODKANDA_UTSKICK_SEKUNDER` (60, minst 30): skickar godkända utkast när sändfönstret öppnar (miljön där de godkändes); var tionde minut uppföljningssvepet (skriver bara utkast till granskning, aldrig autonomt; i en spegel bara trådar vars första utskick gick efter speglingen; hoppas över i simulering och utan affärskontext). Utfall: `send_queue`-status, syns i Skickat/Granskning | `SkickatLista.tsx`, `IrisGranskning.tsx`, `Uppfoljningar.tsx` | `leads/scheduler.py` | Startas bara om `SEND_QUEUE_POLL_SECONDS` = 0 | – |
| AP163 | Den gamla schemaläggaren för autonoma utskick | `run_send_scheduler` när `SEND_QUEUE_POLL_SECONDS` > 0 (standard 0 = av): skickar allt förfallet, autonoma utskick bara i main; uppföljningssvep högst en gång i timmen | – | `leads/scheduler.py` | – | – |
| AP164 | Leads-städaren, väckaren och autopiloten | `run_leads_stadare` var `LEADS_STADNING_SEKUNDER` (300): hängande leadsjobb och listor får ett ärligt slut (första varvet = uppstartsstädning); var 60:e sekund väcks stillastående körningar och autopiloten startar en Iris-körning per vardag för kunder med `automation.autopilot.pa` (från kl. 06 svensk tid, `KORTIMME`; `leads_per_dag` standard 10, tak 50; två lås: miljövariabeln `LEADS_AUTOPILOT=1`, av som standard, OCH kundens val; aldrig i en spegel; högst en autopilotkörning per dag och aldrig medan en pågår; blockerade dagar hoppas över). Hängtiden för städningen är `leads_hangtid_minuter` (60) räknat på tystnad (`updated_at`), pausade körningar städas aldrig, städade listor förlorar sina rader och får texten "Listbygget avbröts innan det blev klart … Beställ listan igen.", städade jobb "Körningen avbröts innan den blev klar … Kör om den."; städningen körs också lat vid `GET /api/leads/listor[/{id}]` och loggas i `platform_events`; synkvakten larmar i development om synken main → development stått still mer än en timme | Körningen syns i `IrisKorningar.tsx` som vilken körning som helst | `jobs/stadare.py`, `leads/autopilot.py`, `jobs/synkvakt` | – | – |
| AP165 | Trial-påminnaren | Var sjätte timme (`TRIAL_PAMINNELSE_SEKUNDER`, minst 300 s; första svepet direkt): mejlar arbetsytans adress 7 dagar och 1 dag före `workspaces.trial_slut` (provperiod 2 kalendermånader, migration 074). Ämnen "Er provperiod hos Snajp går ut om en vecka" / "… imorgon"; texten lovar att inget stängs av utan samtal. Skickar först, loggar sedan i `trial_paminnelser` (unik per arbetsyta och typ); utan levererande sändväg skickas och loggas ingenting (varning i loggen). Stänger ingenting när perioden gått ut | Mejl till kunden; ingen vy | `jobs/trial_paminnare.py`, `trial_paminnelser`, `workspaces.trial_slut` | Kundens kontoadress | nej (bara svenska mejl) |
| AP166 | Gallringen | Av som standard (`GALLRING_AKTIV`); tittar en gång i timmen, kör tidigast `GALLRING_TIMME` svensk tid och högst en gång per dygn (dygnsspärr i `ss_gallringskorning`, samma transaktion som raderingen). Kunder utan beslutad policy (`ss_gallringspolicy`) gallras aldrig; integritetspolicyn lovar 24 månader från senaste behandling. Tak per kund (`GALLRING_TAK`): större urval ändrar ingenting hos kunden och larmar plattformsadmin (`platform_events` + prioriterat mejl); en kund som faller rullas tillbaka utan att stoppa de andra. I en spegel bara det synken inte för över. Mekanismen är databasfunktionen `gallra_alla` (migration 119). Utfall: `ss_gallringslogg`, läsbar via AP130 | Ingen vy | `jobs/gallring.py`, migration 119, 133 | – | – |
| AP167 | Inkorgspollern | Av som standard (`INBOX_POLL_SECONDS` = 0); när på hämtas alla aktiva inkorgar (inte `mock`) en tenant i taget via IMAP och processas. Varje synkförsök, även det manuella (AP42), stämplar `ss_mailboxes.last_sync_at` och `last_error` (t.ex. "Inget app-lösenord för … — koppla om inkorgen under Inställningar → Inkorgar."), och UID-märket flyttas så att inget mejl hämtas två gånger | Inkorgen | `email_pipeline/poller.py` | – | – |
| AP168 | Vertex-token hålls färsk | Hämtas utanför händelseloopen så att första kundanropet efter deploy inte blockerar | – | `agent/llm.py:varm_vertex_token` | – | – |
| AP169 | Jobb med förlopp (`jobs.bakgrund`) | `bakgrund.starta(state, tenant, slag, arbete)` ger `job_id` och `pagar`: samma slag hos samma kund medan det första går ger SAMMA jobb, inget nytt. Uppgiften lever i api-processen (ingen kö); dör processen fälls jobbet av jobblagrets tidsgräns och arbetet ska tåla omstart. Fel med egen text (HTTPException) visas som den, annars "Det gick inte att slutföra. Försök igen om en stund."; förloppet läses via AP24 eller egen läsväg. Används av kvittoskanningen (AP142), körningens utskick (AP86), kampanjutskick (AP112) och omskrivning i en tråd (AP107) | Förloppsrader i respektive vy | `jobs/bakgrund.py` | – | – |
| AP170 | Lösa bakgrundsuppgifter utan förloppsväg | `create_task` i: utkast för ett prospekt (AP72), batchkörning utan Redis (AP90), listbeställning (AP92), omprövning av lista (AP94), kampanjutkast (AP112), webbplatsskanning (AP39), anteckning/uppgift (`leads_suite.py:281`), webbpoolens efterbedömning efter körning och listbygge (`webbpool.efter_korning`, fördelar akuta/dåliga sajter till Alunix och Umeå Webbdesign), webbpoolens bakåtfyllnad (AP136), PATCH av prospekt (AP69); FastAPI `BackgroundTasks` i inkorgssynken och mock (AP42, AP43). Dör med processen | Varierar; status på raden (körning, lista, prospekt) | Se respektive ändpunkt | Webbpoolens utfall bara för admin/webbyråer | – |
| AP171 | Webhooks in | Kanaler (AP34), Resend domäner och studs/klagomål (AP50), flyttmottagaren (AP140) | – | Se respektive | Signaturgrindade | – |
| AP172 | GitHub Actions mot drift | `migrera.yml` (push som rör `db/migrations/`, release-PR, för hand) läser AP141; `overvakning.yml` (cron var tredje timme) kontrollerar hälsa; `sakerhetsbevakning.yml` (dagligen 05:37); `synk.yml` (för hand) | PR-kontrollen "releasens migrationer" | `.github/workflows/` | – | – |

## 8. Serveråtgärder och serverläsningar som går förbi proxyn

Dessa anropar backenden direkt från Next-servern (inte via `/api/snajp-support`).

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP180 | Adminläsning för serverrenderade sidor | `adminFetch` kräver `getPlatformAdmin()`; fel ger `AdminUnavailableError` som sidan visar | `/admin/*` | `lib/data/admin.ts` → AP120, AP121, AP122, AP124 | Plattformsadmin | – |
| AP181 | Agentinstruktioner och kundprofil | `hamtaInstruktioner`, `forhandsgranskaInstruktioner`, `sparaInstruktioner`, `aterstallInstruktioner`, `hamtaKundprofil`, `sparaKundprofil` | `components/admin/Agentinstruktioner.tsx`, kundsidan i admin | `lib/actions/agentinstruktioner.ts` → AP131, AP132 | Plattformsadmin | – |
| AP182 | Kundregister och kontakter | `hamtaKunddata`, `sparaKunddata`, `skapaKontakt`, `uppdateraKontakt`, `taBortKontakt` | `components/admin/Kunddata.tsx` | `lib/actions/kunddata.ts` → AP129 | Plattformsadmin | – |
| AP183 | Avstängning, kundstatus, konvertering, listflytt, flytt till main, insyn | `sattKundAktiv`, `sattKundStatus`, `konverteraTestkund`, `listaTillKund`, `hamtaFlyttbart`, `flyttaTillMain`, `flyttaProspektTillMain`, `hamtaKedja`, `hamtaKorning`, `hamtaSkillfil`, `provaKb` | Admin och `LeadslistorView.tsx` | `lib/actions/avstangning.ts`, `kundstatus.ts`, `konvertera.ts`, `listor.ts`, `flytt.ts`, `insyn.ts` | Plattformsadmin | – |
| AP184 | Provisionering och standardvärden för ny kund | Skapar tenant (AP37), sparar nyckeln, sätter standarder för affärskontext, soul, leadsinställningar, erbjudanden och läser profilen (AP60, AP70, AP79, AP80, AP82); skannar webbplatsen (AP39) | Onboarding, testkund | `lib/actions/onboarding.ts`, `lib/snajp/testtenant.ts`, `lib/snajp/standard.ts`, `lib/snajp/webbplatsskanning.ts`, `lib/snajp/provisionering.ts` | Inloggad användare vid onboarding | – |
| AP185 | Affärskontexten | `hamtaAffarskontext`, `sparaAffarskontext`, `lasOffertForUtkast` | Inställningar → Affärskontext | `lib/actions/affarskontext.ts` → AP60 | Kund | – |
| AP186 | Serveråtgärder som bara rör Next-databasen | `auth.ts` (inloggning, registrering, demo, lösenord, OAuth, utloggning), `tvafaktor.ts`, `team.ts`, `notiser.ts`, `paket.ts`, `tillagg.ts`, `vy.ts`, `saljlista.ts`, `demo.ts` (boka demo), `emails.ts` (`refineEmail`, `persistEmailDraft`) | Se app-01, app-08 | `lib/actions/*` | Varierar | – |

## 9. Sidor (`page.tsx`) och deras rutter

För luckgranskaren. "Inloggad" = bakom `proxy.ts`-matchern; adminsidorna grindas
dessutom av `getPlatformAdmin()` i `app/admin/layout.tsx` (404).

| ID | Rutt | Fil | Del |
|---|---|---|---|
| AP200 | `/dashboard` och undervyer `/dashboard/att-gora`, `/leads` (med `?vy=` korningar, listor m.fl.), `/support`, `/companies`, `/contacts`, `/inbox`, `/larande`, `/analytics`, `/assistant`, `/kvitton` | `app/dashboard/[[...slug]]/page.tsx` (vyerna styrs av `lib/routes.ts`) | Arbetsytan, inloggad (app-02–app-07) |
| AP201 | `/settings` och `/settings/affarskontext`, `/kunskapsbas`, `/soul`, `/leads`, `/regler`, `/mailboxes`, `/team`, `/billing`, `/addons`, `/notiser`, `/tema` | `app/settings/[[...slug]]/page.tsx` | Inställningar, inloggad (app-08) |
| AP202 | `/onboarding`, `/login`, `/auth/reset` | `app/onboarding/page.tsx`, `app/login/page.tsx`, `app/auth/reset/page.tsx` | Inloggning och onboarding (app-01) |
| AP203 | `/admin`, `/admin/kunder`, `/admin/kunder/[id]`, `/admin/kunder/[id]/data`, `/admin/kunder/[id]/insyn`, `/admin/korningar`, `/admin/korningar/[id]`, `/admin/testkorningar`, `/admin/handelser`, `/admin/paket`, `/admin/arbetsyta`, `/admin/agentanvandning`, `/admin/bokforingsanvandning`, `/admin/installningar/[[...slug]]`, `/admin/[...slug]` (övriga) | `app/admin/**/page.tsx` | Adminytan (app-09) |
| AP204 | `/crm` (omdirigerar till `/crm/oversikt`), `/crm/oversikt`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` | `app/crm/**/page.tsx` | Det nya gränssnittet |
| AP205 | `/chat/[tenant]/[session]`, `/embed/[nyckel]` | `app/chat/[tenant]/[session]/page.tsx`, `app/embed/[nyckel]/page.tsx` | Publik chatt och widget |
| AP206 | `/avregistrera/[token]` | `app/avregistrera/[token]/page.tsx` | Avregistrering från utskick (anonym) |
| AP207 | `/demo/[[...slug]]`, `/duo-demo`, `/boka-demo` | `app/demo/…`, `app/duo-demo/…`, `app/boka-demo/…` | Demo och bokning (anonym) |
| AP208 | `/kvitton`, `/bokforing`, `/leads`, `/support` | `app/kvitton/page.tsx`, `app/bokforing/page.tsx`, `app/leads/page.tsx`, `app/support/page.tsx` | Produktsidor (marknad) |
| AP209 | `/`, `/ai-agenter`, `/ai-supportagent`, `/b2b-leads`, `/b2b-prospektering`, `/faq`, `/jamfor-ai-sdr`, `/jamfor-supportagenter`, `/leads-i-inkorgen`, `/support-pa-svenska`, `/supportchatt`, `/svensk-ai-sdr`, `/vart-team` | `app/**/page.tsx` | Marknadssidor |
| AP210 | `/angerratt`, `/cookies`, `/integritetspolicy`, `/villkor` | `app/**/page.tsx` | Juridik |
| AP211 | `/forhandsvisning/*` (crm, exempelbolag, iris-granskning, konversationer, korningens-utkast, kundinstallningar, leads-skickat, leads-snabbsok, listutkast, meny, samtal, webbpool) | `app/forhandsvisning/**/page.tsx` | Förhandsvisningar för granskning utan backend (anropen besvaras i webbläsaren) |
| AP212 | `/design-drafts/[variant]`, `/design-drafts/[variant]/portal/[[...slug]]` | `app/design-drafts/**` | Designutkast |
| AP213 | Supportportalen (egen Next-app, nås via AP13): `/`, `/chattar`, `/inkorg`, `/installningar`, `/integrationer`, `/kontakt`, `/kunskapsbas`, `/testchatt`, `/logga-in`; egna rutter `/api/ag/[...path]` (spegel av backendens tenantyta), `/api/logga-in`, `/api/logga-ut`, `/sso` | `support-webb/app/**` | Agentsajten för support |

## 10. Kompletteringar (kontrolläsaren 2026-11-26)

Regler, spärrar och tvärgående lager som raderna ovan inte bar. Ruttlistan
jämfördes mot `@router.*` i alla 39 routrar och de tre rutterna i `main.py`:
varje backendrutt har en rad i avsnitt 2–6. Sidlistan jämfördes mot
`app/**/page.tsx` (67 filer): alla finns i avsnitt 9.

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| AP220 | Startvägran när miljön är fel konfigurerad | Först i `lifespan`, före databasen: `LLM_PROVIDER=deepseek` i en miljö med riktig kunddata (main, development) fäller uppstarten (`Settings.llm_provider_fault`); master-nyckeln med den incheckade standardvärdet i en databasmiljö fäller uppstarten (`master_key_fault`); `DATABASE_URL` satt men Postgres onåbar efter flera försök fäller uppstarten i stället för att starta i minnesläge. Railway behåller då föregående version | – | `main.py:lifespan`, `config.py` | – | – |
| AP221 | Uppstartens självläkning | Tom kunskapsbas seedas (standard- och G8-demons artiklar) och får aldrig fälla uppstarten; Redis för jobbkön och en egen Redis-klient för embedding- och svarscache, versioner och arbetsminne; utan Redis allt i minnet (jobb dör då med processen) | – | `main.py`, `scripts/seed_kb.py`, `cache/*`, `minne/arbetsminne` | – | – |
| AP222 | Loopvakt och dödsvakt | Loopvakten loggar stacken när händelseloopen står still längre än `LOOPVAKT_MS` (250 ms), högst en logg per 5 s. Dödsvakten avslutar processen om loopen står still `LOOPVAKT_DOD_S` (120 s), så att Railway startar om en hängd api. Vid nedstängning avbryts loopar och arbetare och får 10 s att avsluta | Användaren märker en omstart som AP160/AP161 | `loopvakt.py`, `main.py` | – | – |
| AP223 | Ohanterade fel blir händelser, kvotfel blir 429 | `install_exception_handler`: varje ohanterat fel loggas i `platform_events` (syns i `/admin/handelser`) med anropets `x-request-id`; leverantörens kvotfel blir 429 med kundtext (och larm vid kreditslut) i stället för 500; tappad Redis/databas/nät räknas som beroendefel. En inaktuell cachad databasfråga efter en migration ger 503 utan kropp (proxyn gör om GET) och poolen byts | Alla vyer (felmeddelanden) | `api/events.py`, `main.py:_inaktuell_cachad_fraga`, `kvotfel.py` | Felets detaljer bara för plattformsadmin | nej |
| AP224 | Mätning och spårning per anrop | Middleware `Sparning` sätter `x-request-id` på varje svar, `Matning` lägger frågor och databastid i `Server-Timing`; proxyn för båda vidare till webbläsaren | – | `sparning.py`, `matning.py` | – | – |
| AP225 | CORS för kundens egen webbapp | Av som standard (`ALLOWED_ORIGINS` tom); när satt: bara GET/POST/PUT/PATCH/OPTIONS, rubrikerna `Content-Type` och `X-API-Key`, aldrig credentials. OBS: DELETE saknas i listan | Kundens egen integration | `main.py` | – | – |
| AP226 | Tak på LLM-anrop per timme (överlever omstart) | Kontrollera först, bokför efter: tenant 400 LLM-anrop/h, användare 120/h (demoarbetsyta 20/h), demons IP 30 svar/h. Taket kan passeras med som mest en körning. Fail-open om räknaren inte går att läsa. 429-texter: "Agenten har nått sitt tak för den här timmen. Försök igen om en stund." (tenant), "Det har kommit många frågor på kort tid. Vänta en stund och försök igen." (användare, IP). `X-Snajp-User` kan bara snäva in taket | Chattfönstren (AP2, AP5), demon (AP51) | `api/rate_limit_db.py`, räknartabell (migration 019) | Per tenant, användare och IP | nej |
| AP227 | Chattens grindar före jobbet | `POST /api/chat` prövar i ordning: bilagor, avtalsgrinden (pilottenant utan registrerat avtal → 403 med `KUNDTEXT_AVTAL`, migration 070), timtaken (429), supportbudgeten per dygn i tokens med larm vid 80 % (429). Först därefter skapas jobbet | AP2, AP5 | `api/chat.py`, `app/budget.py`, avtalsgrinden | Kund | nej |
| AP228 | Dubbelklicksspärren för starter | `dubbelstart.en_gang`: en likadan begäran (samma kund, handling och kropp) medan den första pågår eller inom 30 s efteråt får SAMMA svar märkt `dubblett:true`; faller den första får den andra samma fel, och ett misslyckat försök kan göras om direkt. Används av: starta körning (`korning`, AP90), körningens utkast (`korningens-utkast`), körningens utskick (`korningens-utskick`), kampanj (`kampanj`, `kampanjens-utskick`), kvittoskanning. Per process | `LeadsRunForm.tsx`, `KorningensUtkast.tsx`, `Kampanjer.tsx`, `KvittoYta.tsx` | `api/dubbelstart.py` | Kund | – |
| AP229 | Stegloggarnas texter lämnar aldrig backenden | `utan_stegtexter` tar bort `user_message`, `raw_output`, `reasoning_content`, `system_prompt`, `output`, `detalj` ur `step_log`/`step_outputs` (ned till djup 4) i jobbsvaret (AP24) och research-/prospektsvaren; mätvärden (steg, tid, tokens) står kvar. Texterna (som kan bära webbplatsbedömningen och kundens instruktioner) läses bara av plattformsadmin i `agent_runs` | AP4, AP7 och varje pollande vy | `api/stegtexter.py` | Texterna bara plattformsadmin | – |
| AP230 | Åtkomstloggen för master-nyckeln | Varje godkänt master-anrop ger en rad i `audit_logs`: admin-id ur `X-Snajp-Admin` (godtas bara om det står i `platform_admins`, annars "master-nyckel" utan person), metod, ruttmall, `tenant_id` ur väg eller frågesträng, ett id ur vägen och anropets id; aldrig frågesträng, kropp eller svar. Faller skrivningen går anropet ändå igenom (varning i loggen). INV-SEC-013 fäller en adminrutt utan loggen | Admin (avsnitt 5 och 8) | `api/adminlogg.py`, `deps.require_master_key`, migration 123 | Plattformsadmin | – |
| AP231 | CRM-API v1: tak, idempotens och sidindelning | 600 anrop per minut och kund (429 `rate_limited` med `Retry-After: 60`; `X-RateLimit-Limit/Remaining` på varje svar; räknaren är processlokal). `Idempotency-Key` (högst 200 tecken) på POST ger samma svar i 24 h med `Idempotent-Replayed: true`; samma nyckel med annan kropp avvisas. Listor: `limit` 1–500 (standard 50), `cursor`/`next_cursor`, `sort` updated eller name, `updated_since` (ISO 8601), `include_deleted`, `q` högst 200 tecken; oläslig markör → 422 `invalid_parameter`. Saknat omfång → 403 `scope_missing` | `crm/app/*Vy.tsx`, externa integrationer | `api/crm_v1.py`, idempotenstabellen i `app/crm/lagring` | Omfångsnyckel eller kundnyckel | ja (`message` en, `meddelande` sv) |
| AP232 | CRM-API v1: avtalsgrind och felkoder vid skrivning | Varje skrivning (skapa, ändra, radera, återställ, synk) kräver registrerat biträdesavtal: annars 403 `agreement_missing` ("Personuppgiftsbiträdesavtalet är inte registrerat än. Kontakta Snajp."). 409 `conflict` när org.nr eller e-post redan finns på en annan post; 404 `not_found`; 422 `company_not_found` när `company_id` inte pekar på ett bolag. Radering är mjuk i 30 dagar (sedan töms posten, kvar blir id och `deleted_at`); `permanent=true` tömmer direkt (GDPR art. 17); 409 `processing_restricted` om behandlingen är begränsad (art. 18); återställning av tömd post → 410 `permanently_deleted`. POST på befintligt org.nr/e-post uppdaterar och svarar 200 i stället för 201 | `BolagFormular.tsx`, `PersonFormular.tsx`, `BolagVy.tsx`, `PersonerVy.tsx` | `api/crm_v1.py`, `app/crm/synk.py` | Omfång `crm:skriv` | ja |
| AP233 | CRM-API v1: anslutningar och synksatser, gränser | Anslutning: namn 1–80 tecken och unikt (409), mappningen valideras (422 `invalid_mapping`); radering behåller bolag och personer men glömmer källsystemets id. Förhandsgranskning högst 50 poster, skriver inget. Sats: högst 500 poster och 8 MB (413 `body_too_large`), JSON (`{"items":[…]}` eller lista) eller UTF-8-CSV med rubrikrad (semikolon, komma, tabb); tom sats 422 `empty_batch`. Sats till avslutad körning 409 `run_closed`; anslutning borttagen 409. `POST /sync/companies|people` = en hel deltakörning i ett anrop (kräver `connection`, 422 `connection_required`). Fullkörning utan en enda post misslyckas i stället för att tömma registret; `missing_records` tillämpas bara vid fullkörning | `SynkVy.tsx` (läsning); skrivning bara externa system | `api/crm_v1.py`, `app/crm/synk.py`, `app/crm/adaptrar` | Omfång `crm:synk`, `crm:admin` | ja |
| AP234 | CRM-nycklar: validering | `POST /api/crm/nycklar`: `namn` 1–80 tecken, minst ett omfång av `crm:las`, `crm:skriv`, `crm:synk`, `crm:admin`; klartexten bara i svaret | `UtvecklareVy.tsx` | `api/crm.py`, `app/crm/nycklar.py` | Kundnyckel med fullt omfång | nej |
| AP235 | Bolagssökningen: gränser | `GET /api/leads/sok?q=`: under 2 tecken → tom lista; över 100 tecken → 422 "Sökningen får vara högst 100 tecken."; högst 20 träffar (namn som börjar med frågan först, sedan namn som innehåller den, sedan kontakt, e-post, webbplats, ort, eller minst fyra siffror ur org.nr); exempelbolag tas aldrig med; svaret bär inga webbfält | `BolagsSok.tsx` | `leads_uppfoljningar.py` | Kund | nej |
| AP236 | Uppföljningar: skriv nu, med skäl för det som hoppas över | `POST /api/leads/uppfoljningar/skapa` kräver riktig modell och leadsbudget; hoppar över med skäl `inget_skickat`, `avslutad` (svar, avslutande status eller arkiverad), `sekvensen_klar`, `skrivs_redan`, `har_utkast`. `GET` bär `automatiskt` (sant bara när den gamla schemaläggaren är på) och de 50 senaste skickade uppföljningarna | `Uppfoljningar.tsx` | `leads_uppfoljningar.py` | Kund | nej |
| AP237 | Sändlistans schemaläggning och "tillbaka till Iris" | Schemalägg: tiden måste ligga efter nu och högst 60 dagar fram (422 "Välj en tid från nu och högst 60 dagar fram."); bara köade utkast ändras; en tid utanför vardagar 08–16 går ut när fönstret öppnar (`skickas_tidigast`). Tillbaka till Iris: avbryter markerade utkast i granskning eller kö som vid Avvisa och lämnar leadet som nytt, UTAN automatisk omskrivning, inget tak på antalet. Skicka nu: alla spärrar (språk, suppression, karens, volymtak, avsändaruppgifter) gäller, 404 "Utkastet finns inte." | `SkickatLista.tsx` | `leads.py` | Kund | nej |
| AP238 | Koppla inkorg: felmeddelanden | Okänd leverantör utan `imap_host` → 400 "Vi känner inte igen mejlleverantören. Ange IMAP-värden …"; inloggningen provas före sparning, med och utan mellanslag; Gmail-lösenord som inte är 16 tecken ger "Ett app-lösenord från Google är exakt 16 tecken — det ni klistrade in är N tecken …" (422); miljö utan krypteringsnyckel → 503 "Hemligheter kan inte sparas i den här miljön ännu."; lösenordet sparas Fernet-krypterat; urkoppling av okänd inkorg → 404 "Inkorgen finns inte." | `settings/Inkorgar.tsx` | `inbox.py`, `ss_mailboxes` | Kund | nej |
| AP239 | Förbrukningens fönster | `GET /api/usage?days=` standard 30, 1–90 | `JournalVy.tsx`, `Aktivitet.tsx` | `usage.py` | Kund | – |
| AP240 | Flytten till main: grindar på båda sidor | Avsändaren: 503 "FLYTT_MAL_URL är inte satt …" utan mottagare; nätfel eller fel från main → 502 och kvitto `fel` per rad i `dev_flytt_ko`; kandidater: 30 mejl, 200 körningar, 30 listor och de 50 senaste kvittona. Mottagaren: 403 "Ogiltig signatur." eller när paketets tid saknas/är för gammal ("Flytta en gång till från development."), 409 i en spegel, 422 för okänt format (bara typerna mejl, korning, prospekt, lista, version 1), 404 "Kunden finns inte i den här miljön."; en rad som faller stoppar inte resten | "Byt kund"-panelen | `admin_flytt.py` | Plattformsadmin (avsändare), signatur (mottagare) | nej |
| AP241 | Schemaläsningen för PR-kontrollen | `GET /api/drift/schema` med `X-Schema-Nyckel`: 404 när `SCHEMA_LASNYCKEL` saknas i miljön, 401 "Ogiltig nyckel." vid fel nyckel; svarar bara miljönamn och sorterade migrationsversioner | `.github/workflows/migrera.yml` | `drift.py` | Egen smal nyckel | – |
| AP242 | Publika metadatarutter | `robots.ts`, `sitemap.ts`, `manifest.ts` (ej lästa i detalj) | – | `app/robots.ts`, `app/sitemap.ts`, `app/manifest.ts` | Anonym | – |

## Rättat vid kontroll

Stickprov mot koden 2026-11-26 (24 rader). Rader som stämde: AP1 (läsroll,
impersonering, omtag), AP2 (sessionsdomän, strippat `arbetsyta`, 503-texten),
AP11, AP12, AP13, AP19, AP41, AP52, AP85, AP88, AP141, AP146, AP148, AP140, AP37
(grind), AP107 (nyckeln), AP169 (användarna), översiktens punkt 4 (deps-texterna).

- **Översikten, punkt 3**: kompletterad. En skrivning genom proxyn har ett enda försök på 9 s, inte bara "inga omtag".
- **Webbgrinden i översikten**: rad 770 är inte en läsväg utan hjälparen `_utan_dold_bedomning`, som tvättar skrivsvaren från skapa, befordra, degradera, PATCH och listrad → prospekt. Listan är kompletterad.
- **AP9**: kvittoproxyn saknar catch-allens läsrollsspärr och impersoneringens `is_test`-märkning, och gör om även POST/DELETE. Tidigare stod "samma grind" utan förbehåll.
- **AP18**: listan "Vilka har besökt demon" läses via AP81 (`/api/leads/demobesok`), inte AP64 (fördelningen).
- **AP20**: var "ej läst"; nu beskriven.
- **AP24, AP160**: jobbens tidsgräns är 600 s (`jobs/store.py:JOB_TIMEOUT_SECONDS`), inte 300 s. Kommentaren i `main.py` är inaktuell.
- **AP37**: nyckeln skapar ELLER återanvänder tenanten; avtalsgrinden är på när `kraver_avtal` utelämnas; testkunder får seedad kunskapsbas.
- **AP63**: `limit` har standard 500; sidindelning med `fler`/`nasta` och filtren för arkiverade och bortvalda saknades.
- **AP78**: `SkickatLista.tsx` anropar inte vägen själv; standardgränsen är 200, inte 500.
- **AP85**: fortsätt har en egen 409-text.
- **AP107**: omskrivningens förlopp läses ur trådens händelselogg, inte via jobbet; vyn pollar inte `job_id`.
- **AP164**: autopiloten kräver också miljöns `LEADS_AUTOPILOT=1` och körs aldrig i en spegel; städningens regler saknades.
- **AP165**: var märkt "ej läst"; nu beskriven (provperiod 2 månader, ingen avstängning).
- **Avsnitt 5, inledningen**: undantagen från master-nyckeln är AP140 och AP141, inte AP138 och AP139 (de är master-grindade via `admin_listor.py` och `admin_flytt.py`).

## Följda anrop (kontroll av ändpunkt och lagring)

Följt från vyn genom Next-rutten till backendens ändpunkt; alla stämmer med raderna:

1. `UtvecklareVy.tsx` → `crmAnrop("/nycklar")` → `/api/snajp-support/crm/nycklar` → `GET/POST/DELETE /api/crm/nycklar` (`crm.py` → `app/crm/nycklar`) (AP146).
2. `BolagVy.tsx`, `OversiktVy.tsx` → `crmAnrop("/v1/companies?…")`, `crmAnrop("/oversikt")` → `/api/crm/v1/companies`, `/api/crm/oversikt` (AP147, AP148).
3. `PersonFormular.tsx` → `POST`/`PATCH /v1/people` → `crm_v1.py:_skapa/_andra` → `synk.skapa/andra` (AP149).
4. `IrisInkorg.tsx` → `leadsAnrop("/leads/skickat?limit=500")` (`lib/leads/suite.ts`, prefix `/api/snajp-support`) → `leads.py:list_skickat` → `storage.list_skickade` (AP78).
5. `IrisKorningar.tsx` → `/leads/korningar/${id}/{atgard}` → `leads.py:styr_korning` → `set_korning_styrning` på `leads_job_ledger` (AP85).
6. `KonversationsTrad.tsx` → `/leads/konversationer/{tråd}/utkast/generera` → `leads_konversationer.py:generera` → `bakgrund.starta` + händelseloggen (AP107).
7. `KvittoYta.tsx` → `/api/snajp-support/kvitton/skanning` (egen proxy AP9) → `kvitton.py` → `dubbelstart` + `bakgrund.starta("kvittoskanning")` (AP142).
8. `BolagsSok.tsx` → `/leads/sok` → `leads_uppfoljningar.py:sok` → `storage.list_prospects` med fasta kolumner (AP111, AP235).
9. `ProvmejlKnapp.tsx` → `/leads/provmejl` och `/leads/provmejl/mottagare` → `leads.py` → `app/leads/provmejl.py` (AP89).
10. `settings/Inkorgar.tsx` → `/inbox/mailboxes` → `inbox.py:koppla_inkorg` → `storage.upsert_mailbox` (`ss_mailboxes`) (AP41, AP238).
11. `settings/SupportEskalering.tsx` → `/support/config` → `support_config.py` (AP29).
12. `settings/AgentOnskemal.tsx` → `/agent/onskemal/{agent}` → `leads.py` (AP71).
13. `Samtalslista.tsx`, `AttGora.tsx` → `/leads/samtal` → `leads_suite.py` (AP102).
14. `LeadsTabell.tsx` → `/leads/vyer` → `leads_suite.py` (AP104).
15. `app/api/admin/kunder/route.ts` → `select … from public.tenants_for_admin()` (migration `042_admin_impersonation.sql`) (AP12).

## Sådant som bara finns här

Funktion som det nya gränssnittet (`/crm`) i dag saknar motsvarighet till. Allt i
avsnitt 2–6 utom AP146–AP150c saknar CRM-vy; de viktigaste att inte tappa:

- **Proxyns skyddslager** (AP1): läsrollen, impersoneringens `is_test`-märkning och
  tenantfelens `kod`. CRM-appen ärver dem bara så länge den går via
  `/api/snajp-support`. En egen väg förbi proxyn tappar alla tre.
- **Överlämnade chattar** (AP26–AP28): att svara i och lämna tillbaka en chatt
  finns bara i supportportalen (`support-webb`), inte i huvudappen.
- **Integrationer och kanaler** (AP31–AP33): skrivning finns bara i portalen.
- **Jobb med förlopp** (AP169) och leadsströmmen (AP161): mönstret för att visa
  förlopp och utfall efter omladdning (projektregeln 2026-10-10). CRM-synken har
  egna körningar (AP150b) men inget gemensamt förloppsmönster med resten.
- **Webbplatsbedömningens grind** (`webbpool.far_se`) finns bara i
  leadsändpunkterna; CRM-API:t bär inga webbfält i dag och får inte börja göra det
  ogrindat.
- **Spårade demolänkar** (AP18, AP81), **avregistrering** (AP206) och
  **Resend-studs** (AP50) påverkar vilka bolag som får utskick.
- **Email Studio** (AP15) körs i Next, inte i backenden, och har egen
  modellväljare och dataskyddsspärr.
- **Admins skrivvägar** (avsnitt 5 och 8) går via serveråtgärder med
  master-nyckeln; adminproxyn (AP11) är bara läsande.
- **Tvärgående skydd i backenden** (AP220–AP230): startvägran, timtak på
  LLM-anrop, chattens avtals- och budgetgrind, dubbelklicksspärren, rensningen av
  stegloggarnas texter och master-nyckelns åtkomstlogg. CRM-ytan ärver dem bara
  om den anropar samma ändpunkter; nya ändpunkter för CRM:et måste själva gå
  genom `dubbelstart`, `bakgrund` och (för admin) `require_master_key`.
- **Bakgrundsloopar** (AP162–AP167): utskick i sändfönstret, uppföljningssvep,
  autopiloten, trial-påminnelser, gallring. De har ingen vy alls i dag utöver
  utfallen på respektive rad.

## Det jag inte hann läsa

- Kropparna i `leads.py` (5 500 rader) utöver styrningen av körningar, listan och
  läsningen av prospekt, Skickat, schemaläggning, skicka nu, tillbaka till Iris,
  provmejl och webbgrinden: exakta valideringar per ändpunkt för research, utkast,
  befordra/degradera, PATCH, batch, listor och processa om är fortfarande olästa.
- Kropparna i `kb.py`, `kvitton.py`, `bookkeeping.py`, `integrationer.py`,
  `kanaler.py`, `leads_suite.py`, `leads_kampanjer.py`, `admin*.py` (utom
  `admin_flytt.py`) och `crm_v1.py` rad 1–340 (fältmodeller och utformat).
- `jobs/stream.py` (strömmens återtag och `MAX_LEVERANSER`), `leads/scheduler.py`
  i sin helhet, `leads/webbpool.py` utöver `far_se`, `jobs/synkvakt.py`,
  `events.py` rad 1–100, `schemas.py`.
- `app/robots.ts`, `app/sitemap.ts`, `app/manifest.ts`.
- Supportportalens vyer (`support-webb/components/vyer/*`) och dess proxy.
- Vilka adminsidor som läser `/api/admin/usage` och gallringen (se Oklarheter).

## Oklarheter

- **Ändpunkter utan anropare i appen**: `GET /api/leads/runs`,
  `GET /api/leads/onboarding/status`, `GET /api/leads/context-pack`,
  `POST /api/leads/onboarding/chat`, `POST /api/leads/prospects/exempel`,
  `POST …/prospects/{id}/sources`, `POST /api/leads/research/step`,
  `POST /api/leads/svar`, `POST /api/leads/uppfoljning/svep`,
  `POST …/listor/{id}/items/{item}/koa`, `POST /api/leads/kampanjer/{id}/skicka`,
  `POST /api/inbox/{id}/processa-om`, `POST /api/inbox/ingest`,
  `/api/sending-domain*`, `POST /api/demo/chat`, `/api/tickets/{id}`,
  `/api/customers/{id}/history`, `/api/bookkeeping/*`, `GET /api/admin/usage`,
  `GET /api/admin/gallring*`, `POST /api/admin/leads/normalisera-utkast`,
  `/api/admin/sandvag*`, `GET /api/admin/tenants/{id}/inbox|drafts`. Grep kan ha
  missat vägar som byggs ihop av variabler. Anton avgör om de ska följa med till
  CRM:et, pensioneras eller bara finnas för skript och externa kunder.
- **Agent- och bokföringsanvändning i admin** (`/admin/agentanvandning`,
  `/admin/bokforingsanvandning`) läser troligen Next-databasen direkt eller via en
  väg grep inte hittade; går att avgöra i den körande appen.
- **PATCH `/api/leads/prospects/{id}`**: vilka vyer som skickar PATCH och vilka som
  bara läser samma väg med GET (`IrisBolag.tsx:517`, `LeadsTabell.tsx:761`) är
  inte kontrollerat rad för rad.
- **Bokföringsmotorn** (AP10, AP145) har proxy och grind men ingen vy hittad. Ska
  den finnas kvar i CRM:et eller bara som maskineri bakom kvittohanteraren?
- **Supportportalen** (`support-webb`): ska dess funktioner (svara i chatt,
  integrationer, kanaler) byggas in i CRM:et, eller förblir portalen en egen
  agentsajt?
- **Läsrollen i kvitto- och bokföringsproxyn** (AP9, AP10): en `viewer` med
  bokföringspaketet tycks kunna skriva (godkänna kvitton, rensa en period) eftersom
  de två proxyerna saknar catch-allens spärr, och admin som tittar som kund skriver
  skarpt där. Backenden vet inte om rollen. Avgörs i den körande appen; i CRM:et
  ska kvittoytan gå genom samma spärr som resten.
- **Kvittoproxyn gör om POST** (upp till tre försök inom 52 s) medan catch-allen
  aldrig gör det. Kvittoskanningen skyddas av `dubbelstart`, men uppladdning och
  godkännande gör det inte (obelagt om de är idempotenta).
- **Omskrivningen i en tråd svarar alltid `pagar: true`** (`leads_konversationer.py`
  rad 491), även när ett nytt jobb startades. Vyn läser inte fältet i dag; ett nytt
  gränssnitt som gör det får fel besked.
- **CORS-listan saknar DELETE** (AP225). Spelar roll först den dag en kund anropar
  API:t direkt från en webbläsare.
- **Jobbens tidsgräns**: kommentaren i `main.py` säger 300 s, koden 600 s. Vilken som
  är avsedd avgör Anton eller den som skrev den.
- **CRM-v1:s tak på 600 anrop per minut är processlokalt** (`SlidingWindowRateLimiter`)
  och nollställs vid varje omstart; dubbelstartsspärren likaså. Räcker med en
  api-process, inte med flera.
- **CRM-synkens fel till kunden** (Antons svar 13: förlopp för kunden, fel i enkla
  ord, hela rapporten som supportärende): `GET /api/crm/v1/sync/runs/{id}` bär i
  dag `errors[]` med fältkoder direkt till kunden. Hur uppdelningen ska se ut
  avgörs av sessionen som bygger supportärendena.
