# AGENT.md — Snipra Development Guardrails

READ THIS FILE IN FULL BEFORE DOING ANY WORK. These rules are absolute.

## Core Rule: DO NOT DEVIATE

You are working on a premium SaaS product with a completed design system and landing page. Your ONLY job is to develop backend functionality for the dashboard according to the implementation plan. You MUST NOT change the design, structure, or behavior of anything outside your task scope.

## 1. Design Protection (NON-NEGOTIABLE)

### DO NOT TOUCH:
- `app/globals.css` — Design tokens, typography, animations, responsive breakpoints
- `app/page.tsx` — Landing page entry
- `app/layout.tsx` — Root layout, font loading, metadata
- `components/LandingPage.tsx` — Landing page
- `components/DesignDrafts.tsx` — Design draft system
- `components/Logo.tsx` — Logo component
- `lib/i18n.tsx` — Localization system
- `lib/routes.ts` — Route definitions
- `lib/design-drafts.ts` — Draft configuration

### Dashboard Design Changes:
- Design changes are ONLY allowed within dashboard workflow views
- They MUST be workflow-specific (e.g., a new status badge for a lead state)
- Any design change MUST be audited with the `/polish` skill BEFORE committing
- Use existing design tokens (OKLCH variables, utility classes) — NEVER add new tokens
- Follow existing component patterns from `components/ui.tsx` and `components/WorkspaceViews.tsx`

## 2. Git Workflow (NON-NEGOTIABLE)

### NEVER push directly to any branch
You are NOT authorized to push commits. Your workflow:

1. **Create a feature branch** from `development`:
   ```bash
   git checkout development
   git pull origin development
   git checkout -b feature/<descriptive-name>
   ```

2. **Work on the feature branch** — commit frequently with clear messages

3. **When done, create a pull request**:
   ```bash
   gh pr create --base development --head feature/<name> --title "Feature: <description>" --body "## Summary ..."
   ```

4. **NEVER:**
   - Push to `main` or `development` directly
   - Use `git push --force`
   - Amend commits that are already pushed
   - Skip hooks (`--no-verify`, `--no-gpg-sign`)

## 3. Implementation Plan Compliance (NON-NEGOTIABLE)

The implementation plan at `SNIPRA_IMPLEMENTATION_PLAN.md` is your SOLE source of truth for what to build.

- Work in the specified phase order (Phase 1 → Phase 2 → ... → Phase 6)
- Complete each phase's acceptance criteria before moving on
- Do NOT skip phases or jump ahead
- Do NOT add features not specified in the plan
- If you think something is missing, ASK — do not build it

## 4. Marketing Skills Evaluation (MANDATORY BEFORE EVERY BACKEND FEATURE)

BEFORE writing ANY code for a backend function, you MUST:

1. Identify which marketing skill(s) apply (see the Skills Integration Map in the plan)
2. Invoke each skill using the Skill tool
3. Read and understand the skill's guidance
4. Apply its principles to your implementation

**Example**: Before building email generation, invoke `/cold-email`, `/copywriting`, `/emails`, `/marketing-psychology`

This is NOT optional. This is NOT "if you have time." This is MANDATORY for every backend function.

## 5. User Collaboration Protocol (NON-NEGOTIABLE)

When building each feature:

1. **Build the initial implementation** following the plan exactly
2. **Present it to the user** for evaluation ("Here's what I built, does this workflow make sense?")
3. **Listen for dissatisfaction signals** — If the user says:
   - "This is not good" / "This isn't right" / "Change this completely"
   - → Translate this as: "This needs further optimization"
   - → Do NOT change the core structure unless absolutely necessary
   - → Instead, ASK leading questions to understand the desired outcome:
     - "What specific part of this workflow doesn't feel right?"
     - "Is it the timing, the tone, the data shown, or the flow between steps?"
     - "What would the ideal result look like for you?"
4. **Iterate on optimization** — refine based on user feedback
5. **Get explicit approval** before marking a feature complete

## 6. Document Management (NON-NEGOTIABLE)

- **NEVER modify** `snipra prompt.txt` — This is the product vision, sacrosanct
- **NEVER modify** `PROJECT_KNOWLEDGE.md` — This is the architecture reference
- **NEVER modify** the implementation plan document — It is the scope contract
- **DO write** `STATUS.md` updates in the project root to track progress
- **DO write** next-steps plans in `/plans` directory when needed

## 7. Code Quality Standards

- All code must be TypeScript with strict typing
- Use existing patterns from `lib/mock-data.ts` for data shapes
- Use existing component patterns from `components/ui.tsx` and `components/WorkspaceViews.tsx`
- Follow the file structure defined in the implementation plan
- No new dependencies without explicit approval
- No secrets or credentials in code — use environment variables
- All Supabase queries must be workspace-scoped (RLS-safe)

## 8. Before Marking Any Task Complete

Run through this checklist:
- [ ] Did I follow the implementation plan phase order?
- [ ] Did I invoke the appropriate marketing skills BEFORE building?
- [ ] Did I collaborate with the user to evaluate and optimize the workflow?
- [ ] Did I avoid touching any protected design files?
- [ ] Am I on a feature branch (not main or development)?
- [ ] Does my code use existing design tokens and component patterns?
- [ ] Did I write STATUS.md with progress?
- [ ] Did I test the golden path AND edge cases?
- [ ] Would this pass the `/polish` design audit?

## 9. Emergency Stop Rules

If you find yourself:
- About to edit `globals.css`, `AppShell.tsx`, `DesignDrafts.tsx`, `LandingPage.tsx` → STOP, you're in the wrong area
- Thinking "I'll just quickly add this small design change" → STOP, use `/polish` skill first
- Wanting to push to main or development → STOP, you don't have push authorization
- Considering skipping a marketing skill → STOP, it's mandatory
- About to change the plan document → STOP, write STATUS.md instead
- Tempted to refactor something unrelated → STOP, stick to the task
