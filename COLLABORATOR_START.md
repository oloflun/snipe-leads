# Snipra — Collaborator Onboarding

Copy this entire message and paste it into Claude Code when you're ready to start.

---

## Your Setup (one-time)

```bash
# 1. Clone the repo
git clone https://github.com/oloflun/snipe-leads.git
cd snipe-leads

# 2. Pull the development branch
git checkout development
git pull origin development

# 3. Create your first feature branch
# Name it feature/<what-youre-building>, e.g.:
git checkout -b feature/supabase-auth-setup
```

Then connect Claude Code to the Snipra database — see **`SUPABASE_MCP_SETUP.md`**.
Takes ~5 minutes, one time per machine. It lets Claude apply migrations and
inspect tables directly, without anyone sharing the database password.

## Before You Write a Single Line of Code

Read these files in order:

1. **`AGENT.md`** — Your guardrails. This is non-negotiable. Read every section.
2. **`SNIPRA_IMPLEMENTATION_PLAN.md`** — Your scope contract. The 6-phase roadmap you will follow.
3. **`PROJECT_KNOWLEDGE.md`** — Architecture reference and design principles.

Then read:
```
.agent-context/current/00_START_HERE.md
.agent-context/current/30_BEHAVIORAL_INVARIANTS.md
.agent-context/current/20_CODE_MAP.md
```

## Your Mission

Develop backend functionality for the Snipra dashboard according to the implementation plan. The landing page and design system are complete — your focus is the dashboard's data layer, AI integration, email infrastructure, workflow engine, and analytics.

## The Rules (Quick Reference)

1. **Start at Phase 1**. Do not skip ahead. Complete each phase before moving on.
2. **Never touch** the landing page, design system, or component structure outside of dashboard workflow views.
3. **Before building any backend function**, invoke the appropriate marketing skill(s) from the Skills Integration Map in the plan.
4. **Work on feature branches**, never on main or development.
5. **Send PRs to `development`** — I will review before merging.
6. **Write `STATUS.md`** updates as you complete each phase.
7. **Collaborate with me** to evaluate and optimize each workflow before marking it complete.
8. **Design changes only in dashboard**, and only with `/polish` skill audit first.
9. **Never modify** `snipra prompt.txt`, `PROJECT_KNOWLEDGE.md`, or `SNIPRA_IMPLEMENTATION_PLAN.md`.

## When You Complete a Feature

```bash
# Push your feature branch
git push -u origin feature/<your-branch-name>

# Create a pull request to development
gh pr create --base development --head feature/<your-branch-name> \
  --title "Phase X: <what you built>" \
  --body "## Summary
  ...
  ## Tested
  - [ ] Golden path
  - [ ] Edge cases
  - [ ] /polish audit"
```

I'll review, audit with `/polish`, and merge if it passes.

## Start Here

Begin with **Phase 1: Foundation — Supabase & Auth**.
Your first task: Set up the Supabase client, build the auth flow, and protect the dashboard routes.

Ask me if anything is unclear before you start.
