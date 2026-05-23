# Snipra Implementation Plan

## Build Order
1. App shell, navigation, layout and design system.
2. Onboarding and dashboard with realistic mockdata.
3. Leads, companies, contacts, campaigns, analytics and inbox pages.
4. Embedded AI assistant panel and email studio.
5. Supabase schema and Auth integration.
6. RLS policies.
7. Edge Functions for AI generation, scheduler, inbox sync and sending.
8. Replace mock flows with Supabase-backed data access.
9. Polish responsive states, loading, empty, success and error states.
10. Production-ready structure, tests and deployment checks.

## Current Scope Completed In This Pass
- Next.js App Router scaffold.
- Full route surface requested in the prompt.
- Reusable app shell with command palette and mobile nav.
- Swedish-first mockdata for companies, contacts, campaigns, signals, emails and analytics.
- Landing page and product app surfaces using the same visual identity.
- Supabase schema, RLS draft and Edge Function placeholders.
- Project knowledge and product marketing context.

## Next Integration Steps
1. Add Supabase environment variables and generated database types.
2. Replace `lib/mock-data.ts` reads with server data loaders.
3. Implement Auth session handling and workspace membership resolution.
4. Connect Edge Functions to an AI provider and a mail provider.
5. Add queue, retry and audit logging around sending.
6. Add tests for data access, RLS assumptions and email guardrails.
