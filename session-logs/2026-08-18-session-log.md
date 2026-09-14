# Session Log — 2026-08-18

## Session Summary
Rekonstruerade hela auth/admin/demo-arkitekturen över två deploystackar (Vercel/Render + Railway). Rebase railway-development på main, gjorde Auth.js kanoniskt, pivotade till Supabase-adapter (option B) för credentials, satte upp Supabase-preview (snajp_web-roll + RLS-fix + platform_admins-seed), byggde demo-läge som mejl-åtkomst, och återställde /admin som egen route med flikar. Supabase-syncen (produktion → preview) är parkerad som öppen punkt.

## What Changed

### Files Created
- `lib/supabase-auth.ts` — Supabase-klient (GoTrue) + `hasSupabaseAuthEnv()`, adapter för credentials
- `scripts/admin_cleanup.py` — idempotent rensning av platform_admins (snajpsupport = enda admin)
- `scripts/set_preview_postgres_url.py` — getpass för preview-grenens postgres-lösenord
- `scripts/create_preview_snajp_web.py` — skapar snajp_web-rollen (public-grants, ingen auth)
- `supabase/migrations/035_app_user_id_rls.sql` — RLS läser app.user_id (GUC) i stället för auth.uid()

### Files Modified
- `lib/auth.ts` — authorize: GoTrue (Supabase) vs direkt SQL (Railway, scrypt)
- `lib/actions/auth.ts` — signUp/startDemo→requestDemoAccess, fail-closed fel
- `lib/data/dashboard.ts` — isDemo-flagga trådad
- `components/dashboard/DashboardContext.tsx` — isDemo i FALLBACK
- `components/auth/LoginForm.tsx` — demo som mejl-fält, magic link borttagen
- `components/WorkspaceViews.tsx` — logga ut-knapp på onboarding, campaign-sektion bort
- `components/AppShell.tsx` — admin-länk → /admin, demo-banner
- `proxy.ts` — fail-closed, /admin tillbaka i matcher
- `lib/database.types.ts` — is_demo-fält

### Files Moved/Deleted
- `app/admin/*` → `app/dashboard/admin/*` → **tillbaka till `app/admin/*`** (återställd)
- `lib/supabase/*` (Supabase-klient) borttagen i rebasen, återinförd som supabase-auth.ts

## Decisions Made
- **Auth-pivot (option B):** Auth.js credentials använder GoTrue (`supabase.auth.signInWithPassword`) på Supabase, direkt SQL (scrypt) på Railway. Rotorsak: Supabase har bcrypt (GoTrue), Railway har scrypt (replikerad auth) — två format, två kodvägar.
- **Supabase RLS-fix:** Supabase låser auth-schemat så auth.uid() (läser JWT) kan inte bytas. Lösning: current_workspace_id() + 4 policyer läser app.user_id (GUC) direkt. Migration 035.
- **Admin:** först enad (/admin → /dashboard/admin), sedan **återställd /admin** som egen route efter att enad inte visades i drift.
- **Demo:** auto-inloggning (startDemo) ersatt av mejl-fält + "skicka åtkomstlänk" (requestDemoAccess, ärlig stub).

## Context & Discussion
- Supabase-branching är `--with-data` = **engångskopia** (fryses). Railway har `railway_seed_dev.py` = **sync**. Det är därför login "bara fungerar" på Railway men inte Supabase.
- Preview-grenens snajpsupport (bcrypt) är en gammal hash — stämmer inte med produktionslösenordet.
- Användaren är frustrerad över att behöva veta/ändra lösenord — vill ha sync, inte kopia.
- Lösenordet för preview är satt via Admin-API (krävde `apikey`-header) och sparat i `.env.deploy` som `PREVIEW_SNAJP_ADMIN_PASSWORD`.

## Open Threads
- **Supabase-sync (produktion → preview):** parkerad. Behöver `PRODUCTION_POSTGRES_URL` i `.env.deploy` (produktions-poolerns postgres-anslutning), sedan bygga sync-skript (adapta railway_seed_dev.py: kopiera auth.users + public-tabeller).
- **Riktigt inloggningstest:** lösenordet satt, men inte verifierat av användaren.
- **Railway main:** 36/77 migrerad (produktion, rörs sist).
- **Produktions-Supabase:** samma setup (snajp_web + 035 + seed) behövs innan main deployas.
- **OAuth via Supabase:** `upsertOAuthUser` använder fortfarande direkt SQL (inte Supabase OAuth).

## Cross-Project Handoffs
None this session.

## Current State After This Session
Auth är adaptiv (Supabase=GoTrue, Railway=scrypt) och pushat till både development och railway-development. Supabase-preview är uppsatt (snajp_web, RLS-fix, seed, env). /admin är återställt med flikar. Demo är mejl-åtkomst. Nästa session bör bygga Supabase-syncen (behöver PRODUCTION_POSTGRES_URL) och verifiera inloggning + admin-funktioner.

<!-- session-state
date: 2026-08-18
type: auth-admin-demo-rebuild
files_created:
  - lib/supabase-auth.ts
  - scripts/admin_cleanup.py
  - scripts/set_preview_postgres_url.py
  - scripts/create_preview_snajp_web.py
  - supabase/migrations/035_app_user_id_rls.sql
files_modified:
  - lib/auth.ts
  - lib/actions/auth.ts
  - lib/data/dashboard.ts
  - components/auth/LoginForm.tsx
  - components/WorkspaceViews.tsx
  - components/AppShell.tsx
  - proxy.ts
  - lib/database.types.ts
decisions_made: 4
open_threads: 5
handoffs_pending: []
priority_changes: true
status_updated: true
next_session_focus: "Bygg Supabase-syncen (produktion → preview) med PRODUCTION_POSTGRES_URL och verifiera inloggning"
session-state -->
