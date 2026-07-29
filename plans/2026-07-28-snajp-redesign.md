# Plan — Snajp redesign: unified Leads/Support surface + dual-product dashboard

**Branch:** `snajp-redesign` (from `origin/development` @ `32c58cd`)
**Date:** 2026-07-28
**Author:** Claude
**Status:** proposed — three gates need the user's sign-off before Phase 1 (see § 4)

---

## 1. What was asked

1. A unified Snajp Leads/Support surface with a stunning visual presentation of each demo.
2. Landing hero reads **Snajp**, with **Leads / Support** clickable, highlighting on select and
   interactively swapping the page contents. Leads shows the Email Studio demo; Support shows the
   Support demo. Both in one clean format consistent with the existing aesthetic.
3. Product surfaces live at `/leads` and `/support`.
4. A reworked `/dashboard` serving both Leads and Support users, able to render either product's
   data or both.
5. Full rename Snipra → Snajp, URLs included.
6. Leads stays on mock data. Do not wire it further.

## 1b. Decisions locked 2026-07-28

| # | Decision |
|---|---|
| D1 | Full rename Snipra → Snajp, URLs included. New Vercel project; old one keeps its frozen alias. |
| D2 | `/leads` and `/support` are public product surfaces. Legacy workspace moves to `/dashboard/*`, 308s from the old paths. Nothing deleted. |
| D3 | Leads stays on mock data. No further Supabase wiring this pass. |
| D4 | **Overhaul, not preserve.** Drop every editorial cue; rebuild as modern Nordic SaaS. |
| D5 | Keep the OKLCH palette exactly. Keep Fraunces italic display — **hero only**, section headings roman. |
| D6 | No fabricated proof in copy. Mock data is required *inside* the demos and the dashboard; it may not appear in copy as evidence. Illustrative examples carry fine print. |
| D7 | Copy reworked with `/copywriting` then `/humanizer`, both languages, Swedish canonical. |
| D8 | Dashboard split: **empty workspace → fresh, seeded workspace → demo.** No schema change. |
| D9 | Product access is a **server-side entitlement** on the workspace. Needs one new column. |

## 2. Mode and tier — declared before any token is picked

**Verb: redesign. Mode: `redesign · overhaul`** (revised from preserve on D4). New visual language
over preserved content and information architecture. Treat as greenfield for visuals only.

**Tier 1 · derive still holds — the brand evidence survives the overhaul.** The palette and the
display face are explicitly retained, so nothing is invented; the *genre* changes, not the identity.
Genre escape hatch per `verbs/redesign.md`: editorial → modern Nordic SaaS, stamped so later runs
don't revert.

**Tier 1 · derive.** No `DESIGN.md` exists, but brand evidence does, so nothing is invented:

| Evidence | Location |
|---|---|
| OKLCH palette (`--ink`, `--paper`, `--ochre`, `--mineral`, `--moss`, `--danger`) | [globals.css:5](app/globals.css:5) |
| Token → Tailwind mapping | [tailwind.config.ts:8](tailwind.config.ts:8) |
| Type stack — Fraunces display, JetBrains Mono kicker, Geist modern | [globals.css:16](app/globals.css:16) |
| Wordmark + logo mark | [Logo.tsx](components/Logo.tsx), `public/snipe_logo.svg` |
| Approved landing composition | `editorial-clean` variant, [DesignDrafts.tsx](components/DesignDrafts.tsx) |

**Two modes, one token set.** `/`, `/leads`, `/support` run **Persuade**. `/dashboard` runs
**Operate** — same colours and type, product density and cadence, no marketing choreography.
The dashboard is not a second identity.

**Consciously waived detector finding:** Fraunces is on the overused-font list. It is the
established brand face under Tier 1 preserve, so it stays. Recorded here rather than silently ignored.

## 3. Audit — current state

### Marketing / demo surfaces
| Route | Renders | Note |
|---|---|---|
| `/` | `DraftLanding variant="editorial-clean"` | user-approved composition, Leads-only story |
| `/snajp-support` | `PageShell` + `SnajpSupportDemo` | live public demo, 4 tabs, already on brand tokens |
| `/design-drafts/[variant]` | draft gallery | internal, keep |

### Product surfaces
| Route | Renders | Note |
|---|---|---|
| `/dashboard/[[...slug]]` | `DraftPortal` | already serves `/dashboard/leads`, `/dashboard/emails`, etc. |
| `/leads`, `/companies`, `/contacts`, `/campaigns`, `/emails`, `/analytics`, `/inbox`, `/assistant` | `WorkspaceViews` / `PageShell` | duplicate what `/dashboard/<slug>` already renders |

### Data
- **Support — live.** `/api/snajp-support/*` proxies to Render (`snajp-support.onrender.com`),
  running simulation mode. Inbox sync, triage, drafts, approve all verified end to end.
- **Leads — mock.** `lib/mock-data.ts`. Stays mock per decision 6.
- **Email Studio — live.** `/api/email-studio` → LLM, 8 actions, rich JSON result.

### Patterns to preserve
Ruled editorial grid, kicker + display heading rhythm, ledger rows, ochre accent under 5% per
viewport, dark proof section, Swedish-first copy with `useLocale` fallback.

### Patterns to retire
- `body { overflow-x: hidden }` ([globals.css:39](app/globals.css:39)) and the two mobile repeats at
  `:230` / `:239` — must be `overflow-x: clip`. `hidden` already cost a session once by clipping a
  blurred hero blob.
- The mobile width clamp at [globals.css:250](app/globals.css:250): `width: min(342px, 100%)
  !important` on every `h1/h2/h3/p/li/dt/dd/input/textarea`. It caps text at 342px even on a 414px
  viewport and will fight every new component with `!important`. Replace with `overflow-wrap:
  anywhere; min-width: 0` on display headers and `minmax(0, 1fr)` on grid tracks.

### Already correct — do not "fix"
`prefers-reduced-motion` is handled globally at [globals.css:210](app/globals.css:210): a blanket
animation/transition kill plus an explicit `.marquee` stop. The new View Transition swap inherits it
and degrades to an instant cut, which is the wanted behaviour. No new fallback needed.

## 4. Three gates before Phase 1

These are conflicts between the brief and the repo's existing state. Each needs an explicit yes.

### Gate A — RESOLVED 2026-07-28
`/leads`, `/support` and `/dashboard` are to be free and clean. The legacy authenticated workspace
moves rather than being deleted.

**Resolution:** the real workspace views move under `/dashboard/*`, which is where they belong once
`/dashboard` becomes the real dual-product app shell (Phase 4). The top-level routes become 308
redirects. Nothing is deleted; `WorkspaceViews` and the data loaders move intact.

| Was | Becomes | Old path |
|---|---|---|
| `/leads` (auth workspace) | `/dashboard/leads` | 308 → `/dashboard/leads` |
| `/emails`, `/companies`, `/contacts`, `/campaigns`, `/analytics`, `/inbox`, `/assistant` | `/dashboard/<slug>` | 308 each |
| `/snajp-support` | `/support` (public demo) | 308 → `/support` |
| — | `/leads`, `/support` | new public product surfaces |

Note: `/dashboard/<slug>` currently renders `DraftPortal`, which is the **mock showcase**, not the
real workspace. Phase 4 replaces that mock portal with the real views. The two are not equivalent
today, so the redirects and Phase 4 must ship together or `/dashboard/leads` regresses to mock data.

`protectedRoutePrefixes` ([routes.ts:30](lib/routes.ts:30)) collapses to `/dashboard`, `/settings`,
`/onboarding` — `/leads` and `/support` must leave it or the public demos bounce to `/login`.

### Gate B — the URL rename touches a domain you froze
STATUS 2026-07-28 records your decision that `snipra.vercel.app` must **not** be touched, and warns
that deploying with `target: production` moves the alias automatically. You've since asked for a new
Vercel deployment under the Snajp name, which resolves the conflict by sidestepping it: the old
project keeps its frozen alias, the new one carries the redesign.

**In this branch** — route slugs, redirects, wordmark, metadata, `metadataBase`. **Separate step** —
creating the new Vercel project and pointing the Snajp domain at it. Until that exists, deploy
previews only from this branch; never `target: production` against the old project.

### Gate C — `DESIGN.md` gets written and locked first
A two-product surface plus a dual-mode dashboard needs one locked system, not per-page picks. Phase 1
writes `DESIGN.md` at the project root from the Tier 1 evidence above. Every later phase reads it.
I state the picks in plain text and wait for your go before writing it.

## 5. Phases

### Phase 1 · Lock the system
Write `DESIGN.md` from existing evidence: genre editorial; three macrostructure families (marketing,
app, content); the OKLCH tokens verbatim from `globals.css`; Fraunces/Geist/JetBrains Mono; motion
`--ease-editorial` with an opacity-only reduced-motion fallback; CTA voice from the approved landing;
per-page allowances — enrichment on marketing only, never on `/dashboard`.

Also fixes `overflow-x: clip` and adds explicit `a` / `a:hover` colours (currently `color: inherit`
with no hover state).

**Files:** `DESIGN.md` (new), `app/globals.css`.

### Phase 2 · Rebrand Snipra → Snajp
Copy, wordmark and metadata only. No layout changes, so the diff stays reviewable.

- `components/Logo.tsx` — wordmark "Snipra" → "Snajp"; kicker "sales os" → product-neutral.
- `app/layout.tsx`, `app/not-found.tsx` — titles and metadata.
- `components/{LandingPage,AppShell,DesignDrafts,WorkspaceViews}.tsx` — visible strings.
- `lib/mock-data.ts`, `supabase/functions/generate-outreach/index.ts` — product-name strings.
- Route slugs + 308 redirects in `next.config.ts`: `/snajp-support` → `/support` (permanent, the old
  link is public), plus the Gate A redirects if approved.
- `lib/routes.ts` — nav hrefs, `protectedRoutePrefixes`, `authRoutes`.
- `public/snipe_logo.svg` — kept as-is unless you want a new mark. The wordmark is text, not the file.

Out of scope: `SNIPRA_IMPLEMENTATION_PLAN.md` and historical session logs. Renaming a historical
record makes it wrong.

### Phase 3 · The unified surface — hero product switch
The signature interaction. One composition, two product bodies.

- **Hero.** "Snajp" in Fraunces display, roman, never italic. "Leads / Support" as a two-option
  switch beneath it: selected gets the ochre underline and full-strength ink, unselected gets
  `ink/50`. No pill, no gradient, no card — the existing rule-and-underline vocabulary carries it.
- **Semantics.** `role="tablist"` with roving `tabindex`, arrow-key navigation, `aria-selected`.
  All 8 states on the switch. Scroll position pinned across swaps (gate 53 — no scroll-jump).
- **Content swap.** `<ViewTransition>` on the product body, ~200ms, cross-fade only.
  `prefers-reduced-motion` → instant swap.
- **Routing.** `/leads` and `/support` are real routes rendering the same shell with a different
  default selection, so both are linkable, crawlable and share OG cards. Switching updates the URL
  via `history.replaceState` without a navigation.
- **Leads body.** Email Studio demo — `EmailStudioEditor` in `compact` mode (the prop already
  exists), pre-loaded with one mock email, three of the eight actions surfaced. The full eight stay
  in the app.
- **Support body.** The existing four-tab demo, re-composed as one scroll rather than tabs-inside-a-
  page: triage → draft → approve, presented as a sequence.
- **Shared framing.** Both bodies inherit one section rhythm: kicker, display heading, one-line
  claim, live surface, then a ruled proof row.

**Honest copy:** the proof rows use only numbers the demo actually produces — cases classified,
confidence range, escalated vs drafted. No invented conversion rates or customer counts. Where a
number doesn't exist yet, an em-rule placeholder and a labelled grey block.

**Files:** `app/page.tsx`, `app/leads/page.tsx` (new), `app/support/page.tsx` (new),
`components/product/ProductSwitch.tsx` (new), `components/product/LeadsShowcase.tsx` (new),
`components/product/SupportShowcase.tsx` (new), `components/snajp/SnajpSupportDemo.tsx` (re-composed),
`components/email/EmailStudioEditor.tsx` (compact-mode polish only).

**Craft skills:** `emil-design-eng` for the switch feel and easing; `vercel-react-view-transitions`
for the body swap; `copywriting` + `humanizer` on every Swedish and English string.

### Phase 4 · Dashboard, Operate mode
`/dashboard/[[...slug]]` gains a product scope: **Leads · Support · Both**, persisted per user,
default Both.

- **Scope control** in the dashboard header, not the hero switch's marketing voice — a segmented
  control in product register, one accent for the current selection only.
- **Both** renders one merged worklist ordered by urgency, each row tagged with its product. Not two
  dashboards stacked — that is the whole point of the mode.
- **Leads** panels read `lib/mock-data.ts`. **Support** panels read the live Render proxy.
- **One data seam:** `lib/data/dashboard.ts` returns a discriminated union per product so Leads can
  be swapped to Supabase later without touching a component.
- **Nav** filters to the active scope so a Support-only user never sees Leads-only sections.
- **States:** skeletons not spinners; empty states that teach; a first-class offline state for
  Support (Render free tier sleeps after 15 min, ~1 min spin-up) — "waking the backend", not an error.

**Files:** `app/dashboard/[[...slug]]/page.tsx`, `components/dashboard/ScopeSwitch.tsx` (new),
`components/dashboard/UnifiedWorklist.tsx` (new), `lib/data/dashboard.ts` (new),
`components/DesignDrafts.tsx` (`DraftPortal` extracted — it is 1611 lines and was already flagged
for splitting), `lib/routes.ts`.

**Craft skills:** `dataviz` for metric tiles, accent-derived categorical colours only;
`ui-ux-pro-max` for table and empty-state UX, palettes ignored; `shadcn-ui` themed to locked tokens
if a primitive is needed.

### Phase 5 · Verify
`Skill(design-verify)`: console and network read before judging any render; 320 / 375 / 414 / 768
swept; no horizontal scroll. Then `detect.mjs --json` over every changed file, with the Fraunces
finding waived by name. Product-specific: every state rendered, keyboard path through the hero switch
and the scope switch, tables at real row counts, empty and offline states actually reachable.
Copy gate last, both languages. `npm run type-check` and `npm run build` green.

## 6. Explicitly out of scope

- Wiring Leads to Supabase (decision 6).
- Vercel domain/alias moves (Gate B, separate confirmation).
- Touching `main` or `snipra.vercel.app`.
- The public `SNAJP_DEMO_API_KEY` security debt — real and logged in STATUS, but it is a deploy
  concern, not a design one. It gates turning on a real `DEEPSEEK_API_KEY` publicly, not this branch.
- Renaming historical docs and session logs.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Deleting workspace routes breaks a link or an analytics event | Gate A approval + 308 redirects; no route file removed without a file-level list |
| The public `/snajp-support` link dies | Permanent redirect to `/support`, shipped in the same commit as the rename |
| `target: production` moves the frozen alias | Preview deploys only from this branch |
| `DraftPortal` split regresses the approved landing | Split is mechanical extraction, no visual change in the same commit; landing verified before and after |
| Support demo shows offline during review | Warm the Render service before any review pass |
