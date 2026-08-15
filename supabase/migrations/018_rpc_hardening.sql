-- INV-SEC-010, del 1: stäng den anonymt anropbara RPC-ytan.
--
-- PostgREST exponerar VARJE funktion i `public` som `POST /rest/v1/rpc/<namn>`
-- för den roll som har EXECUTE. Fyra `security definer`-funktioner hade
-- `=X/postgres` i sin ACL, vilket är EXECUTE till PUBLIC — bekräftat av
-- Supabase säkerhetsrådgivare och av `pg_proc.proacl` mot produktionen.
--
-- Det viktiga att inte missa: att bara `revoke ... from anon` räcker INTE
-- så länge PUBLIC-graden står kvar, eftersom anon ärver den. Därför revokas
-- PUBLIC först i varje block, och den enda grade som ska finnas skrivs
-- tillbaka explicit efteråt.
--
-- `current_workspace_id()` lämnas medvetet öppen: den anropas inifrån varje
-- `workspace scoped`-policy, som gäller rollen `public`. Utan EXECUTE får
-- anon ett behörighetsfel i stället för noll rader — samma resultat, sämre
-- form. Funktionen läser dessutom bara anroparens EGEN workspace via
-- auth.uid() och läcker därför ingenting.

-- 1. handle_new_user() — triggerfunktion på auth.users. Ingen klient ska
--    någonsin anropa den direkt; att den gick att anropa som anon lät vem
--    som helst köra dess sidoeffekter (profilrad + workspace-koppling).
revoke execute on function public.handle_new_user() from public;
revoke execute on function public.handle_new_user() from anon;
revoke execute on function public.handle_new_user() from authenticated;

-- 2. rls_auto_enable() — event-triggerfunktion som slår på RLS på nya
--    tabeller. Anropbar av anon var ett rent misstag i ACL:en.
revoke execute on function public.rls_auto_enable() from public;
revoke execute on function public.rls_auto_enable() from anon;
revoke execute on function public.rls_auto_enable() from authenticated;

-- 3. ensure_workspace_for_current_user() — den enda av de tre som HAR en
--    legitim anropare: app/auth/callback/route.ts efter exchangeCodeForSession.
--    Den behåller alltså `authenticated`, men inte PUBLIC och inte anon.
revoke execute on function public.ensure_workspace_for_current_user() from public;
revoke execute on function public.ensure_workspace_for_current_user() from anon;
grant execute on function public.ensure_workspace_for_current_user() to authenticated;

-- 4. Framtida funktioner ska inte återfå PUBLIC-graden automatiskt.
--    Postgres default-privilegier ger EXECUTE till PUBLIC på nya funktioner;
--    det är den regeln som gjorde att detta uppstod utan att någon skrev det.
alter default privileges in schema public revoke execute on functions from public;
