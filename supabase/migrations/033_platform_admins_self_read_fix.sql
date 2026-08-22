-- `platform_admins_self_read` var självrefererande och kunde aldrig bli sann.
--
-- Policyn från 020 löd:
--   using (exists (select 1 from platform_admins pa where pa.user_id = auth.uid()))
--
-- Alltså: för att få läsa platform_admins måste du finnas i platform_admins —
-- vilket kräver att du får läsa platform_admins. Postgres svarar
-- `infinite recursion detected in policy for relation "platform_admins"`.
-- Verifierat mot PRODUKTIONEN, inte bara mot en testinstans.
--
-- Följden är att hela Fas 6 aldrig gått att nå. `isPlatformAdmin()` är
-- fail-closed med flit — ett uppslag som inte gick att göra betyder INTE admin —
-- så felet blev en 404 i stället för en krasch. Det är rätt beteende, och det
-- är precis därför ingen upptäckte det: adminytan såg ut att fungera som den
-- ska för den som inte var admin, och den som VAR admin fick samma svar.
--
-- Det är också förklaringen till den öppna tråden "sex UI-ytor är obesiktigade
-- i pixlar". /admin gick inte att besiktiga. Den renderade aldrig för någon.
--
-- Rättelsen är den policy som faktiskt behövdes: var och en ser SIN EGEN rad.
-- Det är exakt vad `isPlatformAdmin(userId)` frågar efter — den läser
-- `where user_id = $1` med anroparens eget id, aldrig hela listan. Ingen
-- funktion i kodbasen listar alla plattformsadmins.
--
-- Skrivpolicyer saknas fortfarande, med flit (se 020): rader läggs till med en
-- priviligierad anslutning, aldrig från appen.

drop policy if exists platform_admins_self_read on public.platform_admins;
create policy platform_admins_self_read on public.platform_admins
  for select
  using (user_id = auth.uid());
