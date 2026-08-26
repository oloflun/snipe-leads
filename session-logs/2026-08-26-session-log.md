# Session Log — 2026-08-26

## Session Summary

Built and shipped the instruction-layer system (migration 049): two database fields that
had existed since migration 010 with zero read path now reach the agent, in the correct
system/user prompt position, with an admin UI to write them. Rebased the work onto a
parallel session's 33 commits, found and fixed a bug the rebase introduced, and pushed to
`development` (deployed to Railway). On resuming today: closed a stale P0, re-measured the
Gemini quota (it's a 6/minute cap, not the daily one first assumed), and found that
production's 2026-08-24 legal pause (Gemini free tier trains on customer content) has been
silently reversed without the documented remediation steps being done.

## What Changed

### Files Created
- `snajp-support/app/agentcore/instruktioner.py` — reads the global + per-customer
  instruction layers once per run, renders them with the correct delimiters, hashes the
  combined text for `pack_version`.
- `snajp-support/app/agentcore/strukturera.py` — free text → LLM-structured
  AGENTS.md-shaped markdown, with a code gate that strips fences/pleasantries and rejects
  unknown headings; falls back to saving the raw text unstructured rather than losing it.
- `snajp-support/app/api/admin_profil.py` — the admin WRITE surface (deliberately split
  from `admin.py`, which is read-only by convention): global instructions CRUD, per-tenant
  profile CRUD, every field's prompt position stated in the response.
- `supabase/migrations/049_agentinstruktioner.sql` — `agent_global_instructions` table
  (versioned, one active row) + `agent_configs.instructions_rav` column.
- `components/admin/Agentinstruktioner.tsx`, `components/admin/Kundprofil.tsx` — admin
  UI. Extended by the parallel session after I built them (fach labels, skeleton state,
  per-field save state) — their additions are in the shipped commit.
- `app/admin/kunder/[id]/page.tsx`, `lib/actions/agentinstruktioner.ts` — the per-customer
  profile route and its server actions.
- `docs/FALTKARTA.md` — every fillable field in the product: where stored, who reads it,
  exact prompt position.
- `scripts/verifiera_instruktioner.py` — fills every field with a unique marker, runs a
  real agent turn, reports which position each marker landed in; `--skarp` adds one real
  model call to confirm the model obeyed.
- `scripts/flytta_fran_supabase.py` — moves remaining Supabase config (KB articles,
  context docs) into Railway Postgres. `far_importeras()` refuses to overwrite a non-empty
  slot (see the incident below for why).
- `snajp-support/tests/agent/test_instruktionslager.py`,
  `snajp-support/tests/api/test_admin_profil_api.py` — the falsification tests.
- `HANDOFF-2026-08-25-INSTRUKTIONER.md` — handoff to Sebbe.

### Files Modified
- `snajp-support/app/agent/support_agent.py`, `leads_agent.py`, `step_runner.py`,
  `agentcore/overlays.py` — every `run_step` call now threads the instruction layer;
  `pack_version()` takes the instruction hash instead of only the file hash.
- `snajp-support/app/storage/{base,memory,postgres}.py` — new storage methods for the
  instruction tables; `postgres.py:search_kb` now chains vector → fulltext instead of
  returning empty when the vector path misses.
- `lib/routes.ts`, `components/WorkspaceViews.tsx`,
  `components/settings/SettingsSection.tsx`, `app/admin/kunder/page.tsx` — wire the new
  admin-only settings section and the profile link into the existing nav.
- `.github/workflows/deploy-development.yml` — **not mine**, written by the parallel
  session; committed here with attribution during the rebase because it would otherwise
  have been lost. Changes the workflow from deploying a dead Vercel preview to mirroring
  `development` → `railway-development`, which is the branch Railway's deploy trigger
  actually watches.
- `snipe-leads.md` (project hub doc) — large rewrite: Live/Miljöer-och-drift/Current-status
  sections were describing the dead Vercel/Render/Supabase stack as current; replaced with
  the Railway-only topology, this session's architecture changes, and the open threads
  below. Flagged `scripts/onboard_tenant.py` as stale (still Vercel-scoped).
- `STATUS.md` — new dated entry for today, including the legal-pause finding below.
- Global `~/...\memory\MEMORY.md` — one entry added (CRLF/git trap, see Context below).

### Files Moved/Deleted
None.

## Decisions Made

- **Instruction fields are admin-only and stay in system position.** A customer can shape
  tone (SOUL, user position) but never write something the agent treats as a rule — the
  boundary is *who wrote the text*, not what it's about (INV-SEC-009). If either field ever
  moves to the customer's own settings page, it must move to user position in the same
  change; the two are one decision, not two.
- **A conflicting comment in the rebase (`support_agent.py`, over `escalated`) was resolved
  in the parallel session's favor**, not mine — their text described the current logic
  (they'd removed `not articles` and added `kb_saknar_svar`); mine described a condition
  that no longer existed. Added a paragraph about the storage-layer fix theirs didn't cover.
- **Declined to merge PR #10 on the peer session's behalf.** It stated its own `gh pr merge`
  was blocked by the permission classifier and asked me to do it instead — refused as
  permission laundering regardless of how reasonable the PR looked (it turned out to be
  already merged and mostly harmless, but that's not knowable in advance and isn't the
  test that matters).
- **Closed `snipe-h4w` rather than leave it open-but-stale.** It claimed both environments
  were provider-less; both were live by the time I checked. A wrong-but-open P0 is worse
  than a closed one with a note — it actively misleads whoever reads the tracker next.
- **Did not create a plan file for this work.** It reached shipped-and-deployed state within
  the session; the handoff doc and hub-doc update serve the purpose a plan file would have,
  and a plan retroactively written for finished work is process theater.

## Context & Discussion

- **The CRLF trap.** Several of my own Python scripts wrote CRLF into files in this
  LF-normalized repo (no `core.autocrlf`). The staged diff read as 7037 insertions /
  3922 deletions — entire files apparently rewritten — for what was actually a 3217/102
  change. Caught before committing by comparing `git diff --stat` against
  `git diff --ignore-cr-at-eol --stat`; had it gone to commit, the rebase would have
  conflicted on nearly every line it touched. Recorded in global `MEMORY.md` since it's an
  environment-level Windows/git/Python trap, not project-specific.
- **The Gemini key confusion, resolved.** Two sessions measured the same key differently
  on 2026-08-24/25 because there were, briefly, two different keys with the same length
  (53 chars) — one blocked (`API_KEY_SERVICE_BLOCKED`, a project-level Google Cloud block,
  fixed since), one working, sitting in different places (local `.env` files vs. Railway).
  Both measurements were individually correct; neither session initially realized the other
  was reading a different value. Fixed by overwriting the local files with the Railway value
  and comparing key *suffixes*, not lengths, going forward.
- **The quota re-measurement today corrected an earlier finding, not just re-confirmed it.**
  Yesterday's `429` was read as `GenerateRequestsPerDayPerProjectPerModel-FreeTier` (20/day)
  — accurate as far as it went, but today's immediate retry succeeded, which a genuine
  24-hour block wouldn't allow. A sequential burst test found the real, reproducible
  constraint: `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, 6 calls/minute,
  ~70s recovery. That's tighter in practice — one support ticket alone makes 6–7 sequential
  calls — and it's now the corrected basis for `snipe-zfn`.
- **The legal pause finding is the most important thing this session surfaced and almost
  didn't get flagged clearly.** `docs/JURIDIK_ATGARDER.md` P0.1c documents that `main` was
  *deliberately* set to simulation mode on 2026-08-24 because Gemini's free tier lets Google
  use customer content for product improvement — an active, unconsented processing, worse
  in the doc's own words than the earlier DeepSeek situation ("där grunden saknades... här
  har vi aktivt lämnat bort innehållet"). Four remediation steps were listed as prerequisites
  to un-pausing: confirm the tier, get a paid tier or switch provider, get a separate key
  per environment, sign a DPA. Today both `main` and `development` report `mode: live`,
  the key is still shared between environments, and the quota is still `FreeTier` — meaning
  the pause was reversed with **none** of the four steps done, and none of
  `JURIDIK_ATGARDER.md`, `STATUS.md`, or the privacy policy were updated when it happened.
  I did not do this reversal and don't know who did or when, only that it happened between
  2026-08-24 23:5x and 2026-08-26. Filed as `snipe-a1c` and flagged directly to Anton in the
  conclude summary, not left for a session log to surface on its own.

## Open Threads

- **`snipe-a1c` (P0, new)** — production live on Gemini free tier despite the documented
  legal pause; none of the four P0.1c remediation steps done. Needs Anton's decision:
  re-pause, or execute the remediation (paid tier/switch provider, separate keys, DPA).
- **`snipe-zfc` (P0)** — `main` ~80 commits behind `development`, missing migration
  043–049, still on older code (though now `mode: live`, not simulation).
- **`snipe-zfn` (P0, corrected today)** — Gemini free tier's real operational ceiling is
  6 requests/minute, not the 20/day figure. One ticket can trip it alone.
- **`IMAP_PASSWORD_LIVRUSTNING`** missing on Railway `api`, both environments.
- **Render orphan still answers `/health/ready` with 200**, kept warm by
  `.github/workflows/keep-backend-awake.yml`. Not touched this session.
- **Supabase still holds config for the retired stack** (5 users, 4 tenants, 48 KB
  articles) — partially migrated via `flytta_fran_supabase.py`; the rest is intentionally
  not moved (see that script's docstring for what and why).
- **`scripts/onboard_tenant.py` is stale** — still Vercel-scoped, never updated for Railway.
  Flagged in the hub doc; not fixed this session.
- Waiting on the customer to confirm Livrustning's warranty period (pre-existing thread,
  unrelated to this session's work).

## Cross-Project Handoffs

None this session. The one genuinely cross-project fact (the CRLF/git trap) went to the
global `MEMORY.md` directly rather than a project-to-project handoff doc, since it's an
environment lesson rather than a finding specific to another tracked project.

## Current State After This Session

The instruction-layer system is built, tested (1317 backend tests green), and deployed to
`development` — verified live via the admin API and a real model call that obeyed an
injected instruction. `main` is materially behind and doesn't have it yet. The most urgent
open item is not technical: production is currently sending real customer data to a Gemini
free-tier endpoint under a legal pause that was reversed without its remediation steps, and
that needs Anton's explicit decision before anything else here, including whether to route
more real traffic to `main` at all.

<!-- session-state
date: 2026-08-26
type: feature-build + incident-review
files_created:
  - snajp-support/app/agentcore/instruktioner.py
  - snajp-support/app/agentcore/strukturera.py
  - snajp-support/app/api/admin_profil.py
  - supabase/migrations/049_agentinstruktioner.sql
  - components/admin/Agentinstruktioner.tsx
  - components/admin/Kundprofil.tsx
  - app/admin/kunder/[id]/page.tsx
  - lib/actions/agentinstruktioner.ts
  - docs/FALTKARTA.md
  - scripts/verifiera_instruktioner.py
  - scripts/flytta_fran_supabase.py
  - snajp-support/tests/agent/test_instruktionslager.py
  - snajp-support/tests/api/test_admin_profil_api.py
  - HANDOFF-2026-08-25-INSTRUKTIONER.md
files_modified:
  - snajp-support/app/agent/support_agent.py
  - snajp-support/app/agent/leads_agent.py
  - snajp-support/app/agent/step_runner.py
  - snajp-support/app/agentcore/overlays.py
  - snajp-support/app/storage/base.py
  - snajp-support/app/storage/memory.py
  - snajp-support/app/storage/postgres.py
  - lib/routes.ts
  - components/WorkspaceViews.tsx
  - components/settings/SettingsSection.tsx
  - app/admin/kunder/page.tsx
  - .github/workflows/deploy-development.yml
  - snipe-leads.md
  - STATUS.md
decisions_made: 5
open_threads: 7
handoffs_pending: []
priority_changes: true
status_updated: true
next_session_focus: "Get Anton's decision on snipe-a1c (Gemini legal pause reversal) before routing more real traffic through main; then bring main current with development (snipe-zfc, migration 043-049)."
session-state -->
