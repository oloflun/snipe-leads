# Agent Backend on DeepSeek v4 Flash — Support & Leads

**Status: NOT APPROVED.** This mirrors a plan still under active `/plan`-mode
review. Full detail, all decisions, and the complete reasoning trail live in
`C:\Users\Anton L\.claude\plans\hej-f-rfina-denna-plan-dreamy-yao.md` (~825 lines)
— read that file before implementing anything. This document is a status
summary, not a replacement.

## Scope
Replace the stubbed leads edge functions and the unstructured support-agent
prompt with a real, versioned agent backend on `deepseek-v4-flash`, built by
vendoring and correctly chaining skills from `anthropics/knowledge-work-plugins`
(customer-support, sales) and `coreyhaines31/marketingskills`, with per-tenant
configuration, hard-coded safety gates (language, timing, data provenance), and
a CI-enforced invariant system so the architecture can't be quietly weakened by
a future contributor.

## Completed (this planning round)
- [x] Read every skill in the requested chain verbatim, not just descriptions
- [x] Identified and got user sign-off on: `competitor-profiling` before
      `competitors` (not instead of); a new from-scratch
      `snajp:retention-conversation` skill instead of live-injecting
      `mk:churn-prevention`; kundkonfigurerbar ticket taxonomy over Anthropic's
      SaaS-shaped nine categories; offer-level A/B testing with an explicit
      "insufficient sample" state
- [x] Dropped `mk:revops` after reading the actual 345-line file — description
      matched, content didn't (CRM/pipeline configuration, not lead handoff)
- [x] Designed a scoping mechanism for `mk:sales-enablement` (inject only
      § Objection Handling + its reference, not all ~1,455 lines) that doesn't
      undermine the "the agent always reads what it's told to" guarantee —
      scope requires a written rationale in the playbook, is hashed into the
      pack version, and is enforced by the same pre-condition gate as a full skill
- [x] Found the repo has zero test CI (`.github/workflows/` = two deploy
      workflows only) — this became build-order step 1
- [x] Designed `ARCHITECTURE_INVARIANTS.md` + `waivers.yml`: every safety rule
      gets a stable id and a CI-enforced test; breaking one requires a dated,
      owned, expiring entry in committed YAML, not a chat approval

## In Progress
- [ ] Plan is still being reviewed interactively with the user — three
      `ExitPlanMode` rejections so far, each with substantive feedback that's
      been incorporated. Not yet approved.

## Remaining (once approved)
1. `verify.yml` (pytest, type-check, invariant tests) + `ARCHITECTURE_INVARIANTS.md`
   skeleton — before anything else
2. `snajp_app` Postgres role without BYPASSRLS (INV-SEC-001) — the biggest
   pre-existing gap, documented but never fixed since `003_snajp_multitenant.sql`
3. Vendor skills fresh: `offers` is missing from today's vendored copy
   (44/49 skills), plus `attribution`, `influencer-marketing`,
   `marketing-council`, `marketing-loops`, and the `tools/` directory
4. Namespace registry (`mk:`, `cs:`, `sa:`, `snajp:`) with manifest hashing
5. Skiktmodell (baseline/playbook/tenant/run), pack versioning, eval-gated
   promotion — a pinned tenant only moves to a new baseline after passing its
   own stored evals in shadow mode
6. Migration 009 (agent_skill_packs, agent_configs, agent_context_docs,
   agent_feedback, agent_evals, agent_runs, prospects, prospect_sources, offers,
   ab_variants/results, outreach_threads/messages, send_queue)
7. Write `snajp:retention-conversation` + its own Swedish objection library
   (distinct from sales' — support meets a customer who already bought and is
   upset, not a prospect who hasn't)
8. Rebuild the support playbook on `cs:` skills
9. Language gate (Swedish default, flips only on a confirmed English reply from
   the prospect — never from an English LinkedIn profile or English-speaking
   customer) and timing gate (outreach only, 08:00–16:00 Europe/Stockholm,
   60-min minimum reply delay, Swedish holidays excluded) — both as hard code
   gates with frozen-clock tests, before any send path exists
10. Leads onboarding → research → outreach → follow-up → handoff chain
11. Scheduler + background queue in the existing FastAPI service
12. Snajp as its own tenant + sandboxed public demo
13. Segment-level A/B learning across ≥3 tenants, aggregate-only, no
    per-tenant `tenant_id` in the exposed view (last, once ≥3 customers exist
    in one segment)

## Deferred
- `sa:competitive-intelligence` — would overlap with the profiling→comparison
  pair already in the chain; revisit only if that pair proves to lack a sales
  angle
- `mk:marketing-psychology` — explicitly not recommended (persuasion tactics
  cut against Snajp's low-pressure tone); add only if the user overrides that
  reservation
- Scoping any skill beyond `sales-enablement` — decide case-by-case with the
  user if dilution shows up during implementation, don't scope silently

## Blockers
- Plan approval itself
- Branch protection on `development`/`main` requiring `verify.yml` as a
  mandatory check is a GitHub setting outside agent reach — without it the
  entire invariant system is advisory, not enforced

## Next Steps
1. Resolve any remaining open questions with the user and get `ExitPlanMode`
   approved
2. Start at plan step 1 exactly as ordered — `verify.yml` before the database
   role fix before anything product-facing
