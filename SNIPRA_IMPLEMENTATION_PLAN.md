# Snipra — Implementation Plan

> Authoritative roadmap. Derived from `snipra prompt.txt` and `PROJECT_KNOWLEDGE.md`.
> Collaborator agents: read `AGENT.md` BEFORE any work. This plan is your scope contract.

## Current State (What's Done)

| Layer | Status | Files |
|-------|--------|-------|
| Landing page | Complete — editorial design, hero, method, proof, pricing, CTA, marquee | `app/page.tsx` → `components/DesignDrafts.tsx` (DraftLanding), `components/LandingPage.tsx` |
| App shell | Complete — sticky nav, command palette, locale toggle (sv/en), breadcrumb bar | `components/AppShell.tsx` |
| All routes | Complete — 17 route pages with full mock-data views | `app/*/page.tsx`, `components/WorkspaceViews.tsx` |
| Design system | Complete — OKLCH color tokens, Fraunces/Geist/JetBrains Mono fonts, editorial CSS utilities, responsive breakpoints | `app/globals.css` |
| UI components | Complete — Badge, MetricCard, ButtonLink, EmptyState, SkeletonRows, LoadingToast | `components/ui.tsx` |
| i18n | Complete — LocaleProvider, sv/en interchangeable, all UI strings localized | `lib/i18n.tsx` |
| Mock data | Complete — 5 realistic Swedish companies, contacts, signals, campaigns, email variants, analytics series | `lib/mock-data.ts` |
| Supabase schema | Complete — 15 tables with full RLS policies, workspace-scoped | `supabase/schema.sql` |
| Edge Function stubs | 4 stubs exist, need AI/mail wiring | `supabase/functions/*/index.ts` |
| Design drafts | 2 variants (editorial-clean, modern-blend), portal previews | `components/DesignDrafts.tsx`, `lib/design-drafts.ts` |

## What Remains (Backend Functionality)

The dashboard is entirely mock-data driven. Every view needs real data plumbing:

1. **Auth & Workspaces** — Login/register flows, session management, workspace membership
2. **Data Layer** — Replace `lib/mock-data.ts` reads with Supabase queries via server components/actions
3. **AI Pipeline** — Connect Edge Functions to OpenAI for lead discovery, company analysis, email generation, reply classification
4. **Email Infrastructure** — Mailbox connections, email sending, reply detection, follow-up scheduling
5. **Workflow Engine** — Stateful 11-step workflow from lead discovery to CRM update
6. **Analytics** — Real aggregated metrics from email events and campaign data
7. **Polish** — Loading skeletons, error states, empty states connected to real data states

---

## Phase 1: Foundation — Supabase & Auth

### 1.1 Environment & Client Setup
- **Files**: `.env.local`, `lib/supabase/client.ts`, `lib/supabase/server.ts`, `lib/supabase/admin.ts`
- Create Supabase project, add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to `.env.local`
- Add `SUPABASE_SERVICE_ROLE_KEY` for server-side/admin operations
- Build browser client (for client components), server client (for server components/actions), and admin client (for Edge Functions)
- Generate TypeScript types from Supabase: `npx supabase gen types typescript --linked > lib/database.types.ts`

### 1.2 Auth Flow — Dashboard Access Control
- **Files**: `app/login/page.tsx`, `app/auth/callback/route.ts`, `lib/auth.ts`, `middleware.ts`
- Dashboard and all sub-routes are **protected** — unauthenticated users are redirected to `/login`
- Replace demo login form with Supabase Auth (magic link + password)
- Create auth callback route for email confirmation
- Add middleware for protected route redirects (all `/dashboard/*`, `/leads`, `/companies`, `/contacts`, `/campaigns`, `/emails`, `/analytics`, `/inbox`, `/assistant`, `/settings/*`)
- Wire `useUser()` hook and profile/workspace resolution

### 1.2b Per-Customer Profiles & Business Context
- Each authenticated user gets their own **profile** row linked to their workspace
- Profile stores: full_name, role, workspace_id
- Each workspace has one **business_context** row containing:
  - product/tjänst, target audience/ICP, focus industries, geography
  - tonalitet (tone preferences), offer, CTA
  - contact roles, taste preferences for AI-generated content
- The **first user profile** (the collaborator/admin) configures the general preferences and model tuning parameters during initial setup
- These taste preferences and business context parameters are used by ALL AI agents across the dashboard
- Business context is editable via `/settings` but must be populated during onboarding
- Onboarding wizard (`app/onboarding/page.tsx`) writes to the `business_contexts` table
- **Skill check BEFORE building**: `/customer-research` (ICP definition), `/marketing-psychology` (taste/tone preferences)

### 1.3 Workspace Resolution
- **Files**: `lib/workspace.ts`, middleware update
- On signup: create workspace + profile row
- On login: resolve workspace_id from profiles table
- Store workspace context for RLS-scoped queries
- Create workspace switcher placeholder (single workspace for MVP)

**Acceptance criteria**: User can sign up, log in, access protected routes with workspace context. Auth state persists across refreshes.

---

## Phase 2: Data Layer — Mock → Supabase

### 2.1 Server Data Loaders
- **Files**: `lib/data/companies.ts`, `lib/data/contacts.ts`, `lib/data/campaigns.ts`, `lib/data/analytics.ts`, `lib/data/emails.ts`
- Create typed server functions that replace `findCompany()`, `findContact()`, `findCampaign()` etc.
- Each loader: accepts workspace_id (from auth), returns typed data, handles empty/null states
- Use React Server Components where possible (App Router data fetching pattern)
- Seed the database with the existing mock data as development seed (`supabase/seed.sql`)

### 2.2 Server Actions for Mutations
- **Files**: `lib/actions/companies.ts`, `lib/actions/campaigns.ts`, `lib/actions/emails.ts`, `lib/actions/settings.ts`
- Create server actions for: create/update campaign, save business context, update lead status, save email draft, add notes
- Each action validates workspace ownership (RLS double-check)
- Return typed results with error handling (`{ success: boolean; error?: string; data?: T }`)

### 2.3 Mock Data Seed
- **Files**: `supabase/seed.sql`
- Convert `lib/mock-data.ts` companies, contacts, signals, campaigns, email variants, analytics into SQL INSERTs
- Use fixed UUIDs for reproducibility
- Include business_context row

**Acceptance criteria**: Dashboard, leads, companies, contacts, campaigns, analytics, and inbox pages load real data from Supabase instead of mock-data.ts. Empty states appear when no data exists.

---

## Phase 3: AI Integration — Edge Functions

### 3.1 OpenAI Client & Shared Utilities
- **Files**: `supabase/functions/_shared/openai.ts`, `supabase/functions/_shared/cors.ts`
- Create typed OpenAI client wrapper with error handling and retry
- Add CORS headers utility
- Define shared types for AI request/response shapes

### 3.2 Discover Leads (Discovery Agent)
- **Files**: `supabase/functions/discover-leads/index.ts`
- Input: business context (product, ICP, industries, geography, tone)
- Output: company suggestions with signal annotations and lead scores
- **Skill check BEFORE building**: `/lead-magnets` (understand lead qualification), `/customer-research` (understand ICP targeting), `/competitor-profiling` (understand market analysis)
- **Workflow evaluation with user**: Validate output quality, signal relevance, scoring rubric

### 3.3 Generate Outreach (Email Generation Agent)
- **Files**: `supabase/functions/generate-outreach/index.ts`
- Input: company data, contact, signals, business context, tone, variant preferences
- Output: subject line, body (kort/medium/lång), follow-up variants, CTA
- **Skill check BEFORE building**: `/cold-email` (primary), `/copywriting` (tone/style), `/emails` (email strategy), `/marketing-psychology` (persuasion principles)
- Must follow Swedish B2B tonalitetsregler (lågmäld, professionell, specifik, mänsklig)
- **Workflow evaluation with user**: Review generated emails against tonalitetsregler, iterate on prompt engineering

### 3.4 Company Research & Signal Detection
- **Files**: `supabase/functions/enrich-company/index.ts`, `supabase/functions/detect-signals/index.ts`
- Enrich company: scrape/gather website data, business registry info, news mentions
- Detect signals: parse enrichment data for expansion, hiring, new offerings, location changes, press
- **Skill check BEFORE building**: `/customer-research`, `/competitor-profiling`, `/ai-seo` (for web signal detection patterns)
- **Workflow evaluation with user**: Validate signal detection accuracy, false positive rate

### 3.5 Reply Classifier
- **Files**: `supabase/functions/classify-reply/index.ts`
- Classify incoming replies: positive, objection, not-interested, wrong-person, auto-reply, unsubscribe-request
- Update contact status and trigger appropriate workflow step
- **Skill check BEFORE building**: `/emails`, `/customer-research` (understanding reply intent)
- **Workflow evaluation with user**: Test classification accuracy on sample replies

**Acceptance criteria**: Edge Functions return typed, validated responses. AI-generated emails follow Swedish B2B tone. Signal detection produces verifiable results. Reply classification is accurate on test set.

---

## Phase 4: Email Infrastructure

### 4.1 Mailbox Connection Center
- **Files**: `app/settings/mailboxes/page.tsx`, `lib/mailboxes.ts`
- Connect Gmail (OAuth), Outlook (OAuth), SMTP (manual config)
- Store connection status, daily limits, warmup status
- **Skill check BEFORE building**: `/cold-email` (sending infrastructure), `/emails` (deliverability)

### 4.2 Email Sending Pipeline
- **Files**: `supabase/functions/send-email/index.ts`, `lib/queue.ts`
- Queue emails for sending within business hours (Tue-Thu 08:30-15:20 Europe/Stockholm)
- Respect daily limits per mailbox
- Handle bounces, track sent status
- Check suppression list before every send
- **Skill check BEFORE building**: `/cold-email` (send strategy), `/emails` (deliverability)
- **Workflow evaluation with user**: Test send flow end-to-end, verify suppression checks

### 4.3 Reply Detection & Sync
- **Files**: `supabase/functions/sync-inbox/index.ts`
- Poll connected mailboxes for replies
- Match replies to sent emails via thread/In-Reply-To headers
- Create email_events rows for reply events
- Trigger reply classifier
- **Workflow evaluation with user**: Test reply detection accuracy

### 4.4 Follow-Up Scheduler
- **Files**: `supabase/functions/schedule-followups/index.ts`
- Check for leads with no reply after X days (per sequence config)
- Generate follow-up email via AI
- Queue for sending within send window
- Stop if contact replied, unsubscribed, or suppressed
- **Skill check BEFORE building**: `/cold-email` (follow-up strategy), `/marketing-psychology` (timing/persistence)
- **Workflow evaluation with user**: Validate follow-up timing, stop conditions, tone adaptation

**Acceptance criteria**: Emails send within configured windows. Replies are detected and classified. Follow-ups trigger correctly. Suppression is always respected.

---

## Phase 5: Workflow Engine & Analytics

### 5.1 Stateful Workflow Implementation
- **Files**: `lib/workflow.ts`, `lib/workflow-steps.ts`
- Implement the 11-step stateful pipeline: Fetch leads → Enrich company → Detect signals → Analyze company → Score relevance → Generate outreach angle → Generate email variants → Queue sending → Watch replies/events → Plan follow-up → Update CRM/analytics
- Each step is a typed function with clear input/output contracts
- Steps are composable and independently testable
- Track workflow state per lead/campaign

### 5.2 Sequence Builder Logic
- **Files**: `lib/sequences.ts`
- Build sequence from campaign config: step order, wait days, variant type, goal
- Sequence steps: cold email → follow-up 1 → follow-up 2 → final follow-up
- Stop conditions: on reply, on bounce, on unsubscribe, manual pause
- Send window enforcement per sequence

### 5.3 Analytics Aggregation
- **Files**: `lib/analytics.ts`, `supabase/functions/aggregate-analytics/index.ts`
- Replace mock analyticsSeries with real queries against email_events + campaigns
- Compute: open rate, reply rate, click rate, booked meetings, conversion rate, delivered, opt-outs, bounce rate
- Aggregate by week, campaign, segment, geography
- **Skill check BEFORE building**: `/analytics` (metric design), `/cro` (conversion tracking)
- **Workflow evaluation with user**: Validate metric definitions, aggregation logic

**Acceptance criteria**: All analytics metrics computed from real data. Sequence builder creates correct step schedules. Workflow pipeline produces correct state transitions.

---

## Phase 6: Polish & Production Readiness

### 6.1 Loading States
- Wire existing `SkeletonRows` component to real loading states in all data views
- Add Suspense boundaries at page and section level
- Use streaming where beneficial (dashboard, leads table)

### 6.2 Error States
- Wire existing `EmptyState` for empty data scenarios
- Add error boundaries with recovery actions
- Toast notifications for mutations (success/error) using `LoadingToast`

### 6.3 Responsive Verification
- Test all views at mobile (375px), tablet (768px), desktop (1440px)
- Verify sticky nav, sidebar behavior, table overflow
- Test command palette on mobile

### 6.4 Testing
- **Files**: `__tests__/workflow.test.ts`, `__tests__/edge-functions.test.ts`
- Unit tests for workflow steps, data loaders, server actions
- Integration tests for Edge Functions (local Supabase)
- RLS policy verification tests
- Email tone compliance checks (Swedish B2B rules)

### 6.5 Scheduled Jobs
- Configure pg_cron or Supabase scheduled functions for:
  - Auto follow-ups (every 30 min during business hours)
  - Refresh lead signals (daily)
  - Inbox sync (every 5 min)
  - Reply detection (every 2 min)
  - Analytics aggregation (hourly)
  - Campaign health checks (daily)

**Acceptance criteria**: No blank screens during loading. Errors show recovery paths. All breakpoints work. Tests pass. Scheduled jobs execute reliably.

---

## File Structure (Target)

```
snipe-leads/
├── app/                          # Route pages (exist, minimal changes)
│   ├── page.tsx                  # Landing (DON'T TOUCH)
│   ├── layout.tsx                # Root layout (DON'T TOUCH without /polish)
│   ├── globals.css               # Design tokens (DON'T TOUCH without /polish)
│   ├── login/page.tsx            # → Connect to Supabase Auth
│   ├── onboarding/page.tsx       # → Save to business_contexts table
│   ├── dashboard/[[...slug]]/page.tsx
│   ├── assistant/page.tsx
│   ├── leads/page.tsx
│   ├── companies/page.tsx
│   ├── companies/[id]/page.tsx
│   ├── contacts/page.tsx
│   ├── contacts/[id]/page.tsx
│   ├── campaigns/page.tsx
│   ├── campaigns/[id]/page.tsx
│   ├── emails/page.tsx
│   ├── analytics/page.tsx
│   ├── inbox/page.tsx
│   ├── settings/page.tsx
│   ├── settings/mailboxes/page.tsx
│   ├── settings/team/page.tsx
│   ├── settings/billing/page.tsx
│   ├── auth/callback/route.ts    # NEW
│   └── not-found.tsx
├── components/
│   ├── AppShell.tsx              # DON'T TOUCH without /polish
│   ├── WorkspaceViews.tsx        # DON'T TOUCH without /polish
│   ├── LandingPage.tsx           # DON'T TOUCH
│   ├── DesignDrafts.tsx          # DON'T TOUCH
│   ├── Logo.tsx                  # DON'T TOUCH
│   └── ui.tsx                    # DON'T TOUCH without /polish
├── lib/
│   ├── i18n.tsx                  # DON'T TOUCH without /polish
│   ├── routes.ts                 # DON'T TOUCH
│   ├── utils.ts                  # Extend with new utilities only
│   ├── mock-data.ts              # KEEP as reference, DON'T DELETE
│   ├── design-drafts.ts          # DON'T TOUCH
│   ├── auth.ts                   # NEW
│   ├── workspace.ts              # NEW
│   ├── workflow.ts               # NEW
│   ├── sequences.ts              # NEW
│   ├── analytics.ts              # NEW
│   ├── mailboxes.ts              # NEW
│   ├── database.types.ts         # NEW (generated)
│   ├── supabase/
│   │   ├── client.ts             # NEW
│   │   ├── server.ts             # NEW
│   │   └── admin.ts              # NEW
│   ├── data/
│   │   ├── companies.ts          # NEW
│   │   ├── contacts.ts           # NEW
│   │   ├── campaigns.ts          # NEW
│   │   ├── emails.ts             # NEW
│   │   └── analytics.ts          # NEW
│   └── actions/
│       ├── companies.ts          # NEW
│       ├── campaigns.ts          # NEW
│       ├── emails.ts             # NEW
│       └── settings.ts           # NEW
├── supabase/
│   ├── schema.sql                # EXISTS, may need migration scripts
│   ├── seed.sql                  # NEW
│   ├── migrations/               # NEW
│   └── functions/
│       ├── _shared/
│       │   ├── types.ts          # EXISTS, extend
│       │   ├── openai.ts         # NEW
│       │   └── cors.ts           # NEW
│       ├── discover-leads/index.ts
│       ├── generate-outreach/index.ts
│       ├── enrich-company/index.ts    # NEW
│       ├── detect-signals/index.ts    # NEW
│       ├── classify-reply/index.ts    # NEW
│       ├── send-email/index.ts        # NEW
│       ├── sync-inbox/index.ts
│       ├── schedule-followups/index.ts
│       └── aggregate-analytics/index.ts # NEW
└── middleware.ts                 # NEW (auth protection)
```

---

## Marketing Skills Integration Map

Each backend function MUST evaluate and apply the appropriate marketing skill(s) before implementation:

| Backend Function | Required Skills |
|-----------------|-----------------|
| Lead Discovery Engine | `/lead-magnets`, `/customer-research`, `/competitor-profiling` |
| AI Company Analysis | `/customer-research`, `/competitor-profiling`, `/seo-audit` (website signals) |
| AI Personalization/Email Generation | `/cold-email`, `/copywriting`, `/emails`, `/marketing-psychology` |
| Email Studio (tone variants) | `/copywriting`, `/marketing-psychology` |
| Follow-Up System | `/cold-email`, `/marketing-psychology` |
| Reply Classification | `/emails`, `/customer-research` |
| Campaign/Sequence Builder | `/cold-email`, `/marketing-psychology`, `/cro` |
| Analytics Dashboard | `/analytics`, `/cro`, `/ab-testing` |
| Mailbox Health/Warmup | `/cold-email`, `/emails` |
| Onboarding Business Context | `/customer-research`, `/lead-magnets` |

---

## Verification Strategy

### Per-Phase Verification
1. **Phase 1**: `npm run dev` → sign up, log in, access protected routes
2. **Phase 2**: `npm run dev` → verify dashboard/leads/companies show Supabase data, not mock
3. **Phase 3**: Invoke Edge Functions locally → verify AI responses follow Swedish tone rules
4. **Phase 4**: End-to-end: create campaign → generate email → queue → send (to test mailbox) → detect reply → classify
5. **Phase 5**: Verify analytics numbers match raw email_events data, workflow states transition correctly
6. **Phase 6**: `npm run build` passes, `npm run test` passes, mobile/tablet/desktop verified

### Key Quality Gates
- Swedish B2B tone compliance for all AI-generated content
- RLS: user A cannot see user B's data (test manually)
- Suppression: suppressed contacts never receive emails
- Audit logs: all sensitive actions logged
- No secrets in frontend code
