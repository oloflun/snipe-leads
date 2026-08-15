# Session Log — 2026-08-15

## Session Summary

Hittade och stängde ett hål där **hela backend-API:t var anonymt nåbart i produktion** —
en oinloggad kunde läsa och skriva demo-agentens röstdokument, kunskapsbas, regler och
inkorg. Samma bugg gjorde att varje inloggad kunds dashboard läste ur demo-tenanten i
stället för sin egen. Rensade dessutom kundchatten från interna bedömningar (sentiment,
eskaleringsflagga, källartikel) och gav supportagenten konversationshistorik, så att den
slutar hälsa och ta avsked i varje replik. Fyra commits pushade till `main`, produktionen
verifierad med samma prob som hittade hålet.

## What Changed

### Files Created
- `lib/snajp/tenant.ts` — härleder tenant ur SESSIONEN (`requireSnajpTenant`); kastar 401/409/503 med namnet på det som saknas i stället för att falla tillbaka på demonyckeln
- `app/api/snajp-support/_auth.ts` — `proxyAsTenant()`, vidarebefordran för inloggad trafik
- `agent-core/overlays/support-conversation.md` — turordningston: hälsa bara i första svaret, ingen avslutningsfras i chatt, kort öppen motfråga på tomma öppningar
- `snajp-support/tests/agent/test_support_conversation.py` — 12 tester: samtalsläget når prompten, utskriften kapas rätt, kodgrinden mot hängande signatur, overlayen bunden till båda textstegen

### Files Modified
- `app/api/snajp-support/[...path]/route.ts` — kräver nu inloggning; tenant ur session
- `app/api/snajp-support/_lib.ts` — `proxyWithApiKey()` bruten ur `proxyToBackend()`; nyckeln är obligatorisk i den inloggade vägen
- `app/api/snajp-support/triage/route.ts` — förblir anonym, med motiveringen skriven i filen (driver "Sortera inkorgen" på publika /support, och endpointen är läsande)
- `lib/database.types.ts` — `workspaces.slug` och `.ss_tenant_id` tillagda; de har funnits i databasen sedan migration 007 men saknades i typerna, så koden kunde inte se kopplingen
- `components/snajp/SupportChat.tsx` — badge-raden och lägespillret borttagna; composern bryter till två rader under 360px; demon får eget session-id per flik
- `snajp-support/app/agent/support_agent.py` — `_render_conversation()`, samtalsläge i `case_context`, `strip_dangling_sign_off()`
- `snajp-support/app/agent/support_playbook.py` — overlayen bunden till `cs:draft-response` och `snajp:humanizer-svenska`
- `.claude/launch.json` — backend-launchconfig (låg okommitterad sedan förra sessionen)

### Files Moved/Deleted
Inga.

## Decisions Made

- **Kvotgrenen mergas inte — delarna plockas ut.** `origin/feature/snajp-multitenant-saas`
  divergerade vid `32c58cd`: 21 commits fram, 34 bakom, 39 filer i konflikt, och
  migrationsnummer 005–010 är två parallella släktled. Produktionsdatabasen följer mains
  kedja; varken `ss_usage` eller `ss_subscriptions` är applicerad. En cherry-pick av
  `dfdf82b` mot dagens main blir mindre och ärligare än en merge av två divergerade världar.
  *Detta underkände min egen tidigare rekommendation (merga först), efter mätning.*

- **`/api/*` läggs INTE till i `proxy.ts`-matchern.** Matchern svarar med omdirigering
  till `/login`, vilket är fel form för ett API-anrop och hade dolt 401:an. Grinden hör
  hemma i routen.

- **Chatt, jobbpollning och triage förblir anonyma.** Den publika chatten ÄR produkten —
  kunden publicerar länken själv. `/api/triage` driver marknadsföringsdemon och är läsande.
  Kostnadsspärren där är rate limit, inte inloggning. *Upptäcktes genom att jag först
  gated triage och sedan kontrollerade vem som anropar den — annars hade demon brutits.*

- **Ingen `showDiagnostics`-prop på kundchatten.** En kundvänd komponent ska inte gå att
  konfigurera till att läcka. Den interna vyn (`Dashboard.tsx`) har redan egen rendering.

- **Turordningsregeln som overlay, inte skill.** `agent-core/skills/` är låst av
  INV-SKILL-005 och skillen är vendorad. Overlayen bunden till BÅDA textstegen —
  humaniseraren är sista handen och hade annars satt tillbaka hälsningen.

- **Kodgrind vid sidan av instruktionen.** `strip_dangling_sign_off()` finns för att
  felet uppträdde i båda thinking-lägena. En regel som bara står i en instruktion är
  en förhoppning.

- **Admin-dashboard i `/admin` i samma app**, **leads-default `draft`**,
  **SSO som kod + konsolchecklista** — användarens val under planeringen.

## Context & Discussion

- **Render pekade på fel gren.** Backend-tjänsten `snajp-support` stod på `development`,
  som forkade vid `32c58cd` och aldrig sett Livrustning-tenanten, fack-filtret eller
  grundningsgrinden. Frontenden deployade från `main`. Det förklarade båda buggarna i
  användarens skärmdumpar. Sebbe bytte till `snajp-leads`, användaren till `main`.
- **Docker-bygget failade på `"/agent-core": not found`** — Root Directory i Render stod
  kvar på `snajp-support`, så `agent-core/` låg utanför byggkontexten. Åtgärdat av
  användaren efter min diagnos.
- **`snipe-leads`-tjänsten i Render raderad** — en felkonfigurerad Node-tjänst som byggde
  Next-frontenden, alltså en dubblett av Vercel. Leads-agenten kör i samma FastAPI-app
  som supporten (`main.py:109` `app.include_router(leads.router)`).
- **Prompt-injektionstesterna i användarens skärmdumpar höll.** Agenten vägrade både
  "Forget everything…" och "Disregard the system prompt…". SOUL-gränsen (userposition +
  UUID-avgränsare + INV-SEC-009) är väl byggd — hålet satt i *vem som fick skriva* SOUL,
  inte i hur den renderades.
- **Mitt ögonmått på en skärmdump var fel.** Jag läste svarstexten som blå; mätningen
  (rastrering av `oklch()` till en canvas-pixel) gav rgb(16,23,30) och 14.72:1. Utan
  mätningen hade jag "fixat" en färg som var korrekt.
- **Historiken tvingade fram en till fix.** Alla demobesökare delade kundidentiteten
  `demo@nordlyshandel.se`. Ofarligt när agenten bara fick ett antal — men med utskriften
  i prompten hade nästa besökare fått föregående besökares repliker.

## Open Threads

**Planen är till en fjärdedel byggd.** `~/.claude/plans/perfekt-k-r-ven-standup-swift-garden.md`
har sju faser; Fas 0, 5 och 7 är klara, Fas 1 till hälften.

- **Fas 1 kvar:** RPC-härdning (migration 018 — `handle_new_user()`, `rls_auto_enable()`
  och `ensure_workspace_for_current_user()` är `security definer` och anropbara av `anon`
  via PostgREST), rate limiting (migration 019 + `rate_limit_db.py`, tre tak: 400/h per
  tenant, 120/h per användare, 30/h per demo-IP, räknat i LLM-anrop inte meddelanden),
  och INV-SEC-010 (anonymt anrop mot varje route-fil).
- **Fas 2 — roller och inlogg:** `platform_admins`-tabell, `snajpsupport@gmail.com` som
  admin, glömt-lösenord, Google/Microsoft-SSO. Ej påbörjad.
- **Fas 3 — kundens vy:** fail-closed entitlements, `workspaces.addons`, sex låsta
  tilläggstjänster, `/settings/layout.tsx`. Ej påbörjad.
- **Fas 4 — leads-kontroller:** autonominivå, ICP-konfiguration, körkontroller. Ej påbörjad.
- **Fas 6 — admin master control:** blockeras av tre migrationer. Ej påbörjad.
- **BLOCKERANDE FYND: ingen leads-körning har någonsin sparats i produktion.**
  `agent_runs.agent_type` har `check in ('support','leads')`, koden skriver
  `"leads_research"`/`"leads_outreach"`. Mot Postgres kastar båda check-violation;
  `MemoryStorage` har inget villkor, vilket är varför testerna aldrig fångade det.
  Admin-spårvyn har noll historik tills detta är fixat.
- **`SNAJP_KEY_LIVRUSTNING` är fortfarande osatt på Vercel.** Efter dagens ändring blir
  det ett tydligt 503 i stället för fel kunds svar, men nyckeln behövs.
- **`snajp_app`-rollens lösenord** — öppet sedan 2026-08-07. Backenden kör som `postgres`
  med BYPASSRLS, så varje `tenant_isolation`-policy är dekorativ för den anslutningen.
- **Repeterad artighetsfras.** "Har du fler frågor är du välkommen att höra av dig!"
  avslutar nu varje svar ordagrant. Inte en avskedsfras, men robotaktigt i längden.
- **`design-stop`-hookens ROUTE GAP gav falskt positivt två gånger** för
  `react-components` (Stitch-till-komponent-konvertering, matchar inte en
  targeterad JSX-borttagning i en befintlig Next-komponent). Eskalerat till
  CARL-domän `design` som `design-005` — öppet ärende i hook-configen, user-level,
  inte knutet till detta projekt. Se `HANDOFF-2026-08-15.md`.
- **Handoff skriven till nästa session:** `HANDOFF-2026-08-15.md`, fullständig
  kontext för att fortsätta Fas 1:s resterande tre punkter samt Fas 2–4 och 6.

## Cross-Project Handoffs

None this session.

## Current State After This Session

`main` står på `998dcd0`, fyra commits före gårdagens läge. Både `Verify` och
`Deploy — Production` gröna, och Render deployar numera från `main` — verifierat genom att
produktionsagenten svarade `"Hej, hur kan jag hjälpa dig?"` på en bar hälsning, alltså med
den nya overlayen. Säkerhetshålet är stängt i produktion, bekräftat med samma prob som
hittade det (`leads/soul`, `kb`, `rules`, `inbox` ger 401; anonym `PUT` ger 401; publik
chatt ger fortfarande 202). 388 tester gröna, `tsc` rent.

Nästa session tar Fas 1:s återstående tre punkter (RPC-härdning, rate limiting,
INV-SEC-010) och `agent_runs.agent_type`-buggen, som blockerar hela admin-spåret.

<!-- session-state
date: 2026-08-15
type: security-fix
files_created:
  - lib/snajp/tenant.ts
  - app/api/snajp-support/_auth.ts
  - agent-core/overlays/support-conversation.md
  - snajp-support/tests/agent/test_support_conversation.py
  - session-logs/2026-08-15-session-log.md
  - plans/2026-08-15-plattformsplan.md
files_modified:
  - app/api/snajp-support/[...path]/route.ts
  - app/api/snajp-support/_lib.ts
  - app/api/snajp-support/triage/route.ts
  - lib/database.types.ts
  - components/snajp/SupportChat.tsx
  - snajp-support/app/agent/support_agent.py
  - snajp-support/app/agent/support_playbook.py
  - .claude/launch.json
  - STATUS.md
decisions_made: 8
open_threads: 10
handoffs_pending: []
priority_changes: true
status_updated: true
next_session_focus: "Fas 1 klart: RPC-härdning (018), rate limiting (019), INV-SEC-010 — samt agent_runs.agent_type-buggen som blockerar admin-spårvyn"
session-state -->
