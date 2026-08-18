-- RLS läser app.user_id (GUC) i stället för auth.uid() (JWT).
--
-- VARFÖR: Auth.js-sessionen är en egen JWT, INTE Supabases. Frontenden scopes
-- sina frågor genom `set_config('app.user_id', …)` i lib/db.ts (sqlAsUser) och
-- förväntar sig att RLS följer den. På Railway fungerar det för att
-- railway/000_auth_compat.sql byter ut auth.uid() till att läsa app.user_id.
--
-- På Supabase går det INTE — auth.uid() är GoTrues egen funktion som läser
-- JWT:n, och auth-schemat är låst så den kan inte bytas. Därför flyttas
-- beroendet ner ett steg: current_workspace_id() och de fyra policyer som läser
-- auth.uid() direkt får läsa app.user_id i stället.
--
-- Idempotent och identisk i utfall på Railway (där auth.uid() redan är
-- app.user_id), så migrationen är säker att köra i båda stackarna.

-- 1. current_workspace_id() — används av ~15 "workspace scoped"-policyer.
create or replace function public.current_workspace_id()
returns uuid
language sql stable security definer
set search_path to 'public', 'pg_temp'
as $$
  select workspace_id from public.profiles
  where id = nullif(current_setting('app.user_id', true), '')::uuid
$$;

-- 2. De fyra policyer som läser auth.uid() direkt.
alter policy "own prefs" on public.user_preferences
  using (nullif(current_setting('app.user_id', true), '')::uuid = user_id);

alter policy "own history" on public.email_history
  using (nullif(current_setting('app.user_id', true), '')::uuid = user_id);

alter policy "platform_admins_self_read" on public.platform_admins
  using (user_id = nullif(current_setting('app.user_id', true), '')::uuid);

alter policy "workspace_members_read_invites" on public.workspace_invites
  using (
    workspace_id in (
      select profiles.workspace_id from profiles
      where profiles.id = nullif(current_setting('app.user_id', true), '')::uuid
    )
  );
