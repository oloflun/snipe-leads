# Session Log — 2026-08-07

## Session Summary
Two-part session. **Part 1 (shipped):** fixed the root cause blocking signup with a private email address (missing profile row on trigger failure, plus Supabase's mailer never reaching private addresses), then built Livrustning AB as a multi-tenant customer of the same codebase — pivoted mid-build from "static marketing pages" to "chat-only, powered-by-Snajp" per explicit correction, with a real knowledge base sourced from livrustning.se and a tenant-isolation sweep that caught Snajp's own marketing site leaking onto the customer's domain. **Part 2 (planned, not approved):** a from-scratch architecture for a DeepSeek v4 Flash agent backend for Support and Leads, built by reading every skill in the requested chain verbatim (not just descriptions) — surfaced a wrong skill choice (`competitors` vs `competitor-profiling`), a category mismatch (`revops` didn't fit despite a matching description), and the fact that the repo has zero test CI today. Plan is still under active user review inside `/plan` mode; nothing in Part 2 has been implemented.

## What Changed

### Files Created
- `AUTH.md` — auth flow diagram, config checklist, manual + automated test procedure
- `TENANTS.md` — the onboarding runbook for adding a new tenant, written after Livrustning exposed three real gotchas
- `supabase/migrations/006_auth_selfheal.sql` — `workspace_invites`, `ensure_workspace_for_user()`, trigger that swallows its own errors, backfill for the orphaned Gmail account
- `supabase/migrations/007_workspace_tenants.sql` — `workspaces.slug` / `ss_tenant_id`, links dashboard workspace to support-agent tenant
- `supabase/migrations/008_mailbox_imap_host.sql` — per-tenant IMAP host column, seeds Livrustning's mailbox row
- `scripts/test-auth-flow.mjs` — rewritten from a script with zero assertions into one that actually fails (signup→profile, invite→correct workspace, self-heal)
- `lib/tenants/{types,index,server,livrustning}.ts` — the tenant registry: host→slug resolution, palette-to-CSS, Livrustning's config (petrol accent, chosen because red/green were already claimed by `--danger`/`--moss`)
- `app/chat/[tenant]/route.ts`, `app/chat/[tenant]/[session]/page.tsx` — the public support link; each hit mints a fresh session UUID
- `public/tenants/livrustning/logo.png` — pulled from livrustning.se; it's white-on-transparent, which is why the chat header is dark
- `snajp-support/app/tenants/{__init__,livrustning_kb}.py` — 22 KB articles sourced from all six pages of livrustning.se, not just the homepage; includes a deliberately unresolved garanti article (see Open Threads)
- `.claude/plans/hej-f-rfina-denna-plan-dreamy-yao.md` — now holds the DeepSeek agent-backend plan (~825 lines); the earlier auth/tenant plan that used to live at this path was approved and implemented earlier in the session, then this same path got reused for the new plan per Claude Code's plan-mode convention

### Files Modified
- `lib/actions/auth.ts`, `app/auth/callback/route.ts`, `lib/actions/onboarding.ts` — Swedish error messages, honest signup copy, self-heal-on-login instead of a dead-end "log in again"
- `proxy.ts` — `proxyConfig` → `config`; the old name silently disabled the matcher, so the proxy was running a Supabase call on every anonymous marketing-page hit. Verified in the dev log, not assumed.
- `components/auth/LoginForm.tsx`, `OnboardingForm.tsx` — error text was `--ochre` (the same token as the primary CTA and focus ring — read as a hint, not a warning), fixed to `--danger`; `grid-cols-12 gap-x-8` was clipping form fields on mobile because 11×32px of gutter exceeds a 375px viewport's content width, `body{overflow-x:clip}` hid it from the naive check
- `app/globals.css` — global `:focus-visible` baseline; the auth forms had `outline-none` with only a border-color change, invisible to keyboard users
- `app/page.tsx`, `app/not-found.tsx`, `app/leads/page.tsx`, `app/support/page.tsx`, `app/design-drafts/**` — every one of Snajp's own routes now 404s or redirects on a tenant domain; `notFoundOnTenant()` is the single guard
- `components/snajp/SupportChat.tsx` — accepts `tenant`/`session` props; demo copy ("Nordlys Handel", felkod-i-kassan prompts) no longer leaks onto a real tenant's chat; fixed an autoscroll-on-empty-chat bug and an input field that shrank to 114px on mobile
- `snajp-support/app/config.py`, `agent/prompt.py`, `simulation/sim_triage.py`, `email_pipeline/poller.py`, `scripts/seed_kb.py`, `storage/{base,memory,postgres}.py` — category taxonomy resynced to what the live database's check constraint actually allows (`garanti`/`utbildning` exist, `konto` doesn't — the repo's migrations had drifted from live); poller now iterates all tenants' mailboxes instead of one hardcoded inbox, password read from `IMAP_PASSWORD_<SLUG>` env, never the database

### Files Removed
- `app/(tenant)/` route group and `components/tenant/TenantNav.tsx` — built as five static marketing pages (Om oss, Villkor, Garanti, Integritetspolicy, Kontakt), then torn out mid-session per explicit correction: **Snajp ships the support chat, not a rebuilt version of the customer's website.** Livrustning keeps livrustning.se; the only thing on `livrustning.snajp.se` is `/chat/livrustning`.

## Decisions Made

- **Chat-only tenant surface, not a mirrored marketing site:** the user's correction, not my initial design. I had built five branded pages assuming a full site handoff; the actual product is narrower — a support chat their existing site links to, with "Powered by Snajp" next to their logo. Deleted the pages rather than leaving dead routes.
- **Garanti taxonomy split into three distinct facts, not one merged answer:** livrustning.se states 8-year warranty for the Hjärtsäker zon bundle; the customer's own terms document says 1 year for loose webshop purchases. These are not the same claim and I could not verify which applies to an arbitrary single-item purchase (hjartstartarbutiken.com didn't respond to fetch). Rather than guess, the KB article hard-codes an escalation instruction: the agent must ask what was purchased and hand off rather than state a warranty length. This is the single most consequential open item in the KB — see Open Threads.
- **`competitor-profiling` before `competitors` in the leads research chain, not `competitors` alone:** the user's own stated reason — comparison material is useful both for answering a prospect's direct question and for strengthening the offer's presentation — meant both skills earn a place, in that order (profile first, comparison-page skill second), rather than either replacing the other.
- **`revops` dropped from the plan after reading the actual file:** its description matched the "hand off a warm lead" need, but the 345-line body is MQL scoring models, deal-desk approval tiers, and CRM automation — it assumes the customer runs a CRM with pipeline stages. The two paragraphs that were relevant (routing, speed-to-lead) will be hand-written instead of injecting the whole skill.
- **`sales-enablement` scoped to its Objection Handling section only, not injected whole:** ~1,455 lines across the skill plus its four reference files cover pitch decks, ROI calculators, demo scripts, proposal templates — none relevant to writing a cold email. The concern voiced was that irrelevant instruction *dilutes*, not that it costs context (1M tokens is not the constraint). Scoping required inventing a mechanism (see below) so that scoping itself doesn't become the loophole that quietly erodes the "the agent always reads what it's supposed to" guarantee.
- **A separate `snajp:retention-conversation` skill instead of injecting `mk:churn-prevention` live:** that skill asks for MRR, churn rate, and billing provider — designed for SaaS subscription cancel flows. Triggered mid-conversation on an upset customer, it would ask a private individual about their monthly recurring revenue. No existing skill in either source repo covers live de-escalation (confirmed by reading `knowledge-work-plugins`' full plugin list — nothing does). `churn-prevention` still runs once, at onboarding, to produce a **retention playbook** the live skill is only allowed to read from — it can never invent an offer.
- **A/B testing reframed to offer-level, multi-month, explicit-uncertainty:** `ab-testing` requires pre-committed sample size and forbids early stopping; `prospecting` recommends ~25 verified leads per list. At an ~8% reply rate that's two replies — statistical significance is arithmetically impossible at that volume. Decided to test offers over months, not emails over weeks, and to report "insufficient sample" as a real, displayed state rather than force a winner.
- **Zero test CI is the actual root of the "how do we stop this from eroding" problem:** `.github/workflows/` only contains two deploy workflows. Before any of the new invariants (tenant isolation, language gate, timing gate) can be *enforced* rather than merely documented, a `verify.yml` that can fail a PR has to exist. This became step 1 of the plan's build order, ahead of the database role fix that used to be step 1.
- **Waiver-as-committed-YAML instead of asking-in-chat:** direct response to the stated risk (a fast-approving collaborator). An invariant can only be broken by adding a dated, owned entry to `waivers.yml`, which CI reads and fails on if expired. This makes an exception visible in `git log` forever instead of disappearing into a conversation.

## Context & Discussion

- **The user corrected the tenant-surface scope explicitly** ("kunderna ska komma direkt till /chat/livrustning") after I had already built and screenshotted five static pages. Cost: a full page-removal pass, a rewrite of `app/page.tsx`/`app/not-found.tsx` to redirect straight to chat, and re-verification of the logo/header on the new chat-only layout. Lesson for future tenant work: confirm "does this tenant get pages, or just the chat?" before building either.
- **The design-stop hook (`~/.claude/hooks/design-stop.py`) counts `Skill` tool invocations for its `ROUTE GAP` warning, not whether the referenced guidance was actually read.** Reading a skill's reference file directly with `Read` (which is what happened for `impeccable operate`, and is what caught the Snajp-leaking-onto-tenant-domain bug) leaves the counter unchanged and the warning keeps firing. Confirmed by direct A/B: same file content, loaded via `Skill()` vs `Read()`, only one moves the counter. This is a hook-behavior fact worth knowing before the next design-heavy session, not a bug to route around by force-calling irrelevant skills.
- **`next-best-practices`' own documentation is wrong about Next 16.** It states the proxy matcher config exports as `proxyConfig`; empirically (same dev server, only the export name changed, timing shown in the request log) it must be `config`. This was flagged for the user rather than silently trusted, and was already the actual bug in `proxy.ts`.
- **The database's `ss_knowledge_base_category_check` constraint has drifted from the repo's own migrations** — live has `garanti`/`utbildning`, not `konto`. This is the second time in this project a live-vs-repo drift has cost implementation time (first was the workspace `products` column in an earlier session). `TENANTS.md` now tells the next session to check the constraint *before* writing KB categories, not after hitting the insert error.
- **Deep skill-reading surfaced two skill-selection mistakes I made from descriptions alone**, both caught only because the user pushed for verbatim reading rather than summary: `competitors` (SEO comparison-page builder) vs `competitor-profiling` (research/dossier — what the research step actually needed), and `revops` (assumed CRM-configuration skill, actually is one). Both are now documented as explicit corrections in the plan file itself, not just fixed silently, so a future reader of the plan sees the reasoning.
- **The user's underlying concern across both plan-mode rounds was the same shape**: don't let an agent's judgment call (or a fast-approving human's rubber stamp) be the only thing standing between "this is fine" and a real data leak or a diluted skill. That's why the plan's newest section (Del L) makes every invariant a CI-checked test with an id, rather than a paragraph of instructions.

## Open Threads

- **Livrustning's garanti question is unresolved and requires the customer, not code.** Which warranty period applies to a single hjärtstartare bought loose in the webshop — 1 year (stated in their terms) or 8 years (stated as part of the Hjärtsäker zon bundle on livrustning.se)? The KB article currently forces escalation on every warranty question until this is answered. Ask Livrustning directly; update `snajp-support/app/tenants/livrustning_kb.py` once confirmed.
- **`.env.local`'s `SUPABASE_SERVICE_ROLE_KEY` is empty** (confirmed this session) — `scripts/test-auth-flow.mjs` cannot run until it's filled in from the Supabase dashboard.
- **The DeepSeek agent-backend plan is NOT approved.** It is still open in `/plan` mode as of session end — the user rejected `ExitPlanMode` three times, each with substantive scope-changing feedback that was incorporated (see Decisions Made). **Nothing in Part 2 has been implemented — no vendored skills, no migration 009, no agentcore package.** The next session should NOT start building from this plan without first getting explicit approval; the plan file itself (`.claude/plans/hej-f-rfina-denna-plan-dreamy-yao.md`) is the source of truth for exactly what's decided vs. still open, and this session's local mirror (`plans/2026-08-07-agent-backend-deepseek.md`) summarizes it — see Cross-Project Handoffs section header below, this stays intra-project.
- Specifically un-confirmed inside that plan: whether any *other* skill besides `sales-enablement` needs scoping (flagged in the plan as "decide with the user if it comes up, don't scope silently"), and whether `mk:marketing-psychology` should be added despite the stated reservation against it (persuasion tactics vs. Snajp's low-pressure tone).
- Branch protection on `development`/`main` requiring the new `verify.yml` as a mandatory check is a GitHub setting an agent cannot flip — needs to happen by hand once the workflow exists, or the entire invariant system in the plan is advisory rather than enforced.
- Deploy env vars for the tenant work were never confirmed as set in Vercel: `SNAJP_KEY_LIVRUSTNING`, `IMAP_PASSWORD_LIVRUSTNING`. Without them the tenant falls back to the demo API key (logged as a warning, not a hard failure) and the mailbox poller skips Livrustning's inbox silently (also logged, not failed).
- The project hub doc at `wiki/projects/snipe/snipe.md` was a near-empty stub ("No meaningful markdown project docs found yet") before this session — updated below, but it had clearly never been maintained; worth checking whether other active projects have the same gap.

## Cross-Project Handoffs
None this session — both parts of the work are scoped entirely to `snipe-leads`.

## Current State After This Session
Auth is fixed and verified against the live database (registration → profile → workspace, invite → correct workspace, orphaned-account self-heal — all tested with real inserts and cleaned up). Livrustning AB is live as a chat-only tenant at `livrustning.snajp.se/chat/livrustning`, isolated from Snajp's own marketing routes in both directions, with a 22-article KB sourced from their actual site (minus the one open garanti question). None of that is deployed yet — Vercel env vars for Livrustning's API key and IMAP password are unset. The DeepSeek agent-backend architecture is fully designed on paper (four-layer skill/pack/tenant/run model, tenant-configurable playbooks, hard-coded language/timing/provenance gates, a CI-enforced invariant system) but exists only in the plan file — zero implementation. Next session's job is either (a) get the plan approved and start at its step 1 (`verify.yml` + `ARCHITECTURE_INVARIANTS.md`), or (b) resolve the garanti question and flip the Vercel env vars to actually ship Livrustning.

<!-- session-state
date: 2026-08-07
type: feature-build-and-architecture-planning
files_created:
  - AUTH.md
  - TENANTS.md
  - supabase/migrations/006_auth_selfheal.sql
  - supabase/migrations/007_workspace_tenants.sql
  - supabase/migrations/008_mailbox_imap_host.sql
  - scripts/test-auth-flow.mjs
  - lib/tenants/types.ts
  - lib/tenants/index.ts
  - lib/tenants/server.ts
  - lib/tenants/livrustning.ts
  - app/chat/[tenant]/route.ts
  - app/chat/[tenant]/[session]/page.tsx
  - public/tenants/livrustning/logo.png
  - snajp-support/app/tenants/__init__.py
  - snajp-support/app/tenants/livrustning_kb.py
files_modified:
  - lib/actions/auth.ts
  - app/auth/callback/route.ts
  - lib/actions/onboarding.ts
  - proxy.ts
  - components/auth/LoginForm.tsx
  - components/auth/OnboardingForm.tsx
  - app/globals.css
  - app/page.tsx
  - app/not-found.tsx
  - app/leads/page.tsx
  - app/support/page.tsx
  - components/snajp/SupportChat.tsx
  - snajp-support/app/config.py
  - snajp-support/app/agent/prompt.py
  - snajp-support/app/simulation/sim_triage.py
  - snajp-support/app/email_pipeline/poller.py
  - snajp-support/app/scripts/seed_kb.py
  - snajp-support/app/storage/base.py
  - snajp-support/app/storage/memory.py
  - snajp-support/app/storage/postgres.py
decisions_made: 8
open_threads: 7
handoffs_pending: []
priority_changes: true
status_updated: true
next_session_focus: "Get the DeepSeek agent-backend plan approved before writing any code, OR resolve Livrustning's garanti question and set Vercel env vars to actually ship the tenant that's already built."
session-state -->
