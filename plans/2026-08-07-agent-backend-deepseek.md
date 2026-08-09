# Agent Backend on DeepSeek v4 Flash — Support & Leads

**Status: APPROVED and IMPLEMENTED (2026-08-07/08).** Full detail, all decisions,
and the complete reasoning trail live in
`C:\Users\Anton L\.claude\plans\hej-f-rfina-denna-plan-dreamy-yao.md` (~825 lines)
— read that file for the original design. **For current technical status, read
[HANDOFF.md](../HANDOFF.md) instead of this file** — it is now the authoritative
built-vs-dead-vs-missing breakdown. This document tracks planning-level scope
and history only.

## Scope
Replace the stubbed leads edge functions and the unstructured support-agent
prompt with a real, versioned agent backend on `deepseek-v4-flash`, built by
vendoring and correctly chaining skills from `anthropics/knowledge-work-plugins`
(customer-support, sales) and `coreyhaines31/marketingskills`, with per-tenant
configuration, hard-coded safety gates (language, timing, data provenance), and
a CI-enforced invariant system so the architecture can't be quietly weakened by
a future contributor.

## Completed (planning round, 2026-08-07)
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
      § Objection Handling + its reference, not all ~1,455 lines)
- [x] Found the repo has zero test CI — this became build-order step 1
- [x] Designed `ARCHITECTURE_INVARIANTS.md` + `waivers.yml`

## Completed (implementation round, 2026-08-07/08)
- [x] `verify.yml` + `ARCHITECTURE_INVARIANTS.md` + `waivers.yml`, INV-SKILL-001/002/003 Active
- [x] `snajp_app` DB role without BYPASSRLS (INV-SEC-001) — live, tenant-isolation verified
- [x] Full skill registry vendored (414 files, 4 namespaces), sha256 manifest
- [x] Read-guarantee mechanism (Del C): namespace registry, precondition gate,
      output contract — rebuilt mid-round from a concatenated-prompt agent loop
      to one LLM call per skill step, because the loop made the guarantee
      unverifiable in practice
- [x] Migrations 009–015: role, full agent-backend schema, demo tenant, Snajp
      tenant, segment aggregate, step-log column — all applied live
- [x] Language/timing/provenance gates with frozen-clock and live tests
- [x] `snajp:retention-conversation` skill + objection library
- [x] Support agent rebuilt on the `cs:` playbook, per-step orchestration
- [x] Leads: prospect creation, onboarding context pack (with retroactive-
      onboarding gap handling), research chain, outreach draft, follow-up
      sequencing, handoff routing, scheduler, demo tenant, segment aggregate
- [x] Live-verified against real DeepSeek + ScrapeGraphAI keys: support flow
      (66 calls, both thinking modes), skill-completeness audit
- [x] Found and fixed a customer-facing bug live testing surfaced: template
      placeholders (`[Your name]`) leaking into replies
- [x] Vision + embeddings switched from OpenAI to Gemini (free tier)
- [x] Support thinking-mode decision made from real data: disabled globally,
      enabled only for the escalation-determination step

## Completed (leads per-steg + thinking-beslut, 2026-08-09/10)
- [x] **`leads_agent.py` migrerad till per-steg-körning.** Fas B (8 steg) och
      Fas C (4 steg) kör via `step_runner.run_step`. `THINKING_MODE` når nu
      varje anrop, `agent_runs` skrivs, utdatakontrakt gäller per steg.
      Skrapning och köning flyttade till kod. Fas A medvetet kvar på
      `Runner.run` (flerturssamtal) — kvarvarande lucka, inte klart.
- [x] Regressionstest som inspekterar de kwargs LLM-klienten FAKTISKT fick
      (`test_thinking_mode_reaches_the_api_call`) — hade fällt 2026-08-08-
      körningen innan den kostade 50 minuter.
- [x] **Giltig leads-jämförelse körd:** 3 bolag × 2 lägen × 12 steg = 72 skarpa
      anrop, varje stegs kompletta utdata dokumenterad
      (`docs/LEADS_THINKING_COMPARISON.md`, 811 KB).
- [x] **Leads thinking-beslut fattat: HELT AV.** Användarens beslut efter
      genomläsning av rådatan, som underkände min rekommendation (PÅ). Pinnat
      explicit per steg via `research_playbook.THINKING`, låst av två tester.
      Motivering och min felslutsatsanalys: `THINKING_MODE_COMPARISON.md` §8.5.
- [x] Två buggar funna och åtgärdade: ScrapeGraphAI returnerar markdown som
      LISTA (gav längd 1 och listrepr i prompten), och hängande signatur i
      5/6 utkast efter att platshållargrinden gjort sitt jobb (`sign_off()`).
- [x] **INV-SKILL-005** — "ändra aldrig skillsen" är nu mekaniskt tvingad via
      sha256 mot manifestet, inte en instruktion i ett dokument. Verifierad
      genom att faktiskt fälla på en ändring.

## Remaining (see HANDOFF.md §2 and §5 for the authoritative, detailed list)
1. Get `DATABASE_URL` working; re-verify KB retrieval against real pgvector
   (the only KB-search testing so far used `MemoryStorage`, which ignores
   embeddings entirely — a real bug in the test harness, not yet fixed)
2. Wire in or delete the dead modules: eval-gated promotion, the layer/pack
   pinning model, follow-up sequencing, handoff routing
3. Replace or remove the still-untouched `discover-leads`/`generate-outreach`
   edge function stubs
4. Email Studio integration for outreach drafts; a dashboard view for
   `GET /api/leads/runs`
5. Evaluate whether ScrapeGraphAI alone covers Fas B research (making
   agent-reach redundant) — decide from the leads comparison's real output

## Deferred
- `sa:competitive-intelligence` — would overlap with the profiling→comparison
  pair already in the chain; revisit only if that pair proves to lack a sales
  angle
- `mk:marketing-psychology` — explicitly not recommended (persuasion tactics
  cut against Snajp's low-pressure tone); add only if the user overrides that
  reservation
- Whether `snajp:retention-conversation` should also run with thinking
  enabled (escalation-adjacent, but not the literal step the user named) —
  flagged in code as an open question, not decided

## Blockers
- `snajp_app` DB role has no password — `execute_sql` blocked by this
  environment's auto-mode classifier even though `apply_migration` succeeded
  on the same connection. Needs the user to set it directly or grant
  permission. See `BLOCKS.md` (vault).
- Branch protection on `development`/`main` requiring `verify.yml` as a
  mandatory check is a GitHub setting outside agent reach — without it the
  entire invariant system is advisory, not enforced

## Next Steps
1. **Grundningsgrind mot påhittade påståenden.** AV-utkastet till Sportamore
   innehöll en påhittad siffra ("30 procent inom 30 dagar") som inte finns i
   kontextpaketet. `strip_placeholders` tar mallrester, inte ogrundade
   påståenden. Allvarligaste kvarvarande kundvända felet.
2. **Utvärdera tilläggsinstruktioner** (`THINKING_MODE_COMPARISON.md` §8.6) —
   `sa:draft-outreach` + `snajp:humanizer-svenska` först, det är där tonen
   avgörs. HÅRD REGEL: aldrig genom att ändra i skillen (INV-SKILL-005).
3. Ta ställning till Fas A-migreringen (onboarding, `Runner.run`).
4. `DATABASE_URL`-blockeraren och den overifierade pgvector-vägen.
5. Beta av HANDOFF.md:s döda-kod-lista (väck in eller radera).
