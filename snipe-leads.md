---
title: Snipra / Snajp
type: project
status: active
project_slug: snipe-leads
repo: C:\Users\Anton L\snipe-leads
updated: 2026-08-08
---

# Snipra / Snajp

Two products, one repo. **Snipra** is the Next.js frontend (leads dashboard,
Email Studio, onboarding, settings) on Vercel. **Snajp-Support**
(`snajp-support/`) is a separate Python/FastAPI backend on Render, providing
AI customer support and — as of 2026-08 — a real agent backend for both
support and B2B leads generation, on `deepseek-v4-flash`.

## What it does, in one paragraph

Snajp sells AI agents to Swedish companies: one that answers customer
support tickets grounded only in the company's own knowledge base (escalates
rather than invents facts), and one that researches B2B prospects and drafts
low-pressure, source-grounded outreach — never mass email. Each customer
("tenant") gets an isolated slice of the same codebase: own KB, own agent
config, own Postgres RLS scope. Livrustning AB is the first live customer
(chat-only, `/chat/livrustning`, no marketing pages — the customer's site
stays theirs).

## Core mechanics

| Layer | What | Where |
| --- | --- | --- |
| Frontend | Next.js App Router, Vercel, multi-tenant via workspace/proxy routing | `app/` |
| Support backend | FastAPI, tenant-scoped Postgres RLS, agent runtime | `snajp-support/` |
| Agent core | Skill registry + read-guarantee mechanism (Del C) | `snajp-support/app/agentcore/` |
| Agent execution | One LLM call per skill step, not a concatenated prompt | `snajp-support/app/agent/step_runner.py` |
| Skill content | Vendored `mk:`/`cs:`/`sa:`/`snajp:` skills, sha256-manifested | `agent-core/skills/` |
| Playbooks | Which skills run, in what order, for which agent type | `snajp-support/app/agent/support_playbook.py`, `snajp-support/app/leads/*_playbook.py` |
| DB | Multi-tenant Postgres via Supabase, migrations 001–015 | `supabase/migrations/` |

**Decision flow for a support ticket:** triage → customer-research →
draft-response → escalation-check → kb-article → (retention-conversation, if
cancellation risk) → humanizer-svenska. Every arrow is a real LLM call with
its own output contract (`sources_used`/`context_refs`), not a step inside
one big prompt — that separation is what makes the "did it actually read the
skill" guarantee checkable instead of assumed.

## Document map

| File | Carries |
| --- | --- |
| [HANDOFF.md](HANDOFF.md) | **Current, authoritative technical status** — built vs. live-verified vs. dead code vs. missing, for the 2026-08 agent-backend work. Read this first for "what state is the code actually in." |
| [STATUS.md](STATUS.md) | Chronological session-by-session status, newest first. Narrative history. |
| [ARCHITECTURE_INVARIANTS.md](ARCHITECTURE_INVARIANTS.md) | Machine-enforced rules (CI-checked). `INV-SKILL-*`, `INV-SEC-*`, etc. |
| [plans/2026-08-07-agent-backend-deepseek.md](plans/2026-08-07-agent-backend-deepseek.md) | Plan-level scope/progress tracker for the agent-backend work; points to the full design doc. |
| [DEPLOY_KEYS.md](DEPLOY_KEYS.md) | How to set API keys locally and at deploy; `scripts/keys.py`. |
| [docs/THINKING_MODE_COMPARISON.md](docs/THINKING_MODE_COMPARISON.md) | DeepSeek thinking-mode on/off comparison, real API calls, per flow. |
| [TENANTS.md](TENANTS.md) | Runbook for onboarding a new customer tenant. |
| [AUTH.md](AUTH.md) | Auth flow, config checklist, test procedure. |
| `agent-core/README.md` | Skill registry: namespaces, sources, how to vendor/update. |
| `snajp-support/app/storage/base.py` | The `Storage` interface — read this to see every operation the agent layer can perform; both `memory.py` (tests, dev) and `postgres.py` (production) implement it. |
| `scripts/run_live_tests.py`, `scripts/run_live_leads.py` | Live comparison harness against real API keys; writes to `docs/live-tests/`. |

## Invariants and gotchas

- **Skills are never edited to fix a routing problem.** If a skill call fails
  or seems unread, harden the precondition gate / output contract
  (`app/agentcore/packs.py`) — never the vendored skill content
  (`agent-core/skills/`).
- **Secrets never go in the database** (`INV-SEC-006`) — env only, see
  `DEPLOY_KEYS.md`. This was raised and explicitly declined as an option.
- **`pydantic-settings` `env_file` must be an absolute path.** A relative one
  resolves against `cwd`, not the settings file's location — silently reads
  zero keys depending on where something is run from.
- **`monkeypatch.delenv` doesn't override a value sourced from a `.env`
  FILE** — only real process env. Use `monkeypatch.setenv(key, "")`.
- **`tests/conftest.py` forces simulation mode for the whole suite.** Without
  it, the suite is only hermetic by accident (works until a real API key
  happens to exist on the dev machine).
- **`MemoryStorage.search_kb` ignores the `embedding` argument entirely** —
  pure token overlap. Never use it to judge KB-search/embeddings quality;
  that requires `PostgresStorage` (real pgvector) and a working
  `DATABASE_URL`.
- **Sidoeffekter (escalate, persist, send) happen in code, never via a tool
  the model calls.** The model reasons; the code decides and acts. See
  `run_support_agent` for the pattern.
- **`send_queue` is the only path to sending anything** (`INV-SEC-004`) — no
  tool in the agent's toolset can send directly.

## How to verify the system

```bash
python scripts/keys.py --check                       # keys present?
cd snajp-support && python -m pytest -q               # unit suite
cd .. && python -m pytest tests/invariants -q         # CI invariant meta-test
npm run type-check
python scripts/run_live_tests.py --skill-audit        # every skill loads complete, incl. references
```

Live end-to-end verification (needs real keys, hits real APIs):

```bash
python scripts/run_live_tests.py --support --modes disabled,enabled
python scripts/run_live_tests.py --leads   --modes disabled,enabled
```

## Current status (2026-08-08)

Agent backend implemented and partially live-verified (support flow, both
DeepSeek thinking modes, real KB + real replies). Leads pipeline has real
entry points (prospect creation, research, outreach draft) but its
thinking-mode comparison was still running in the background at last
session close. `DATABASE_URL` is not set locally, so the real pgvector
KB-search path is unverified — everything tested so far used the in-memory
storage backend, which doesn't do semantic search at all. See
[HANDOFF.md](HANDOFF.md) for the full built/dead/missing breakdown and next
steps.
