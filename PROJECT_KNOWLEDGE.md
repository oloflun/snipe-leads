# Snipra Project Knowledge

## Product
Snipra is an AI-first outbound sales automation product for Swedish B2B companies. The product acts as an embedded Swedish SDR that helps users find relevant companies, analyze public signals, identify pain points, generate low-pressure personalized outreach, run follow-ups, classify replies and book more meetings.

## Audience
- Swedish B2B companies, consultancies, agencies, SaaS companies and service businesses.
- Primary users: founders, CEOs, sales managers, marketing managers and operators who need better outbound without a large SDR team.
- Default locale: `sv-SE`.
- Default timezone: `Europe/Stockholm`.
- Currency: SEK.

## Voice
Customer-facing copy must feel Swedish, professional, specific and calm. Avoid aggressive US sales language, clickbait, exaggerated claims, generic AI phrasing and "I hope this email finds you well".

## Core Workflow
1. Fetch leads.
2. Enrich company.
3. Detect signals.
4. Analyze company.
5. Score relevance.
6. Generate outreach angle.
7. Generate email variants.
8. Queue sending.
9. Watch replies and events.
10. Generate follow-up if needed.
11. Update CRM and analytics.

## AI Modules
- Discovery Agent
- Company Research Agent
- Signal Detection Agent
- Contact Prioritization Agent
- Personalization Agent
- Email Generation Agent
- Follow-Up Planner
- Reply Classifier
- Analytics Insight Agent

## Data Model
The UI mock layer mirrors the Supabase schema in `supabase/schema.sql`: workspaces, profiles, business_contexts, companies, contacts, lead_signals, company_insights, campaigns, sequences, sequence_steps, generated_emails, email_events, meetings, suppressions and audit_logs.

## LinkedIn Guardrail
LinkedIn is a pluggable provider abstraction. Do not assume free scraping of personal profiles. Supported modes are company page references, user-authorized LinkedIn inputs, external enrichment providers via adapter pattern and manual enrichment fallback.

## UI System
Snipra uses a restrained, editorial SaaS product language: warm paper surfaces, ink text, copper action color, moss success, steel data accents, tight 8px-or-less radii and dense operational layouts. App UI should feel calm, scannable and work-focused rather than like a marketing template.

## Localization
All durable product strings should be represented as `{ sv, en }` where practical. Default language is Swedish. The current implementation uses `lib/i18n.tsx` for locale state and `Localized` values in mock/product data.

## Current Implementation
- Landing page: `app/page.tsx`
- App shell and command palette: `components/AppShell.tsx`
- Main product views: `components/WorkspaceViews.tsx`
- Mock data and workflow model: `lib/mock-data.ts`
- Supabase schema and RLS draft: `supabase/schema.sql`
- Edge Function stubs: `supabase/functions/*/index.ts`
