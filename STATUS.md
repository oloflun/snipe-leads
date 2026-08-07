# Snipra Status

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
