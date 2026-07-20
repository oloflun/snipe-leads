# Snipra Status

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
