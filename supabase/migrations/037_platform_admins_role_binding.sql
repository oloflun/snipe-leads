-- `/admin` svarar 404 på Railway trots att raden i platform_admins FINNS.
--
-- UPPMÄTT 2026-08-19 mot railway-development:
--     rad i platform_admins ....... True
--     isPlatformAdmin() som appen . False
--
-- Raden finns. Läsningen går ändå inte. Orsaken är inte villkoret utan
-- ROLLBINDNINGEN: migration 033 skrev policyn som
--
--     create policy platform_admins_self_read on public.platform_admins
--       for select to authenticated using (user_id = auth.uid());
--
-- `authenticated` är Supabases roll. På Railway talar Next-appen som
-- `snajp_web`, som varken ÄR `authenticated` eller medlem i den. En policy som
-- inte gäller anroparens roll utvärderas aldrig — och när ingen policy gäller
-- ger RLS noll rader. Inget fel kastas.
--
-- Mätningen som pekar ut den: av 66 policyer i databasen är 53 bundna till
-- PUBLIC och 12 till `snajp_app`. Exakt EN är bunden till `authenticated`, och
-- det är den här. Avvikelsen är felet.
--
-- Symptomen är precis de som `RAILWAY.md` beskriver för en SAKNAD rad, vilket
-- är varför de två förväxlades: `isPlatformAdmin()` är fail-closed med flit, så
-- "gick inte att läsa" och "är inte admin" ser identiska ut utifrån.
--   * `/admin` och `/admin/*` svarar 404 för rätt person.
--   * inloggningen landar på `/dashboard`, eftersom dirigeringen till adminytan
--     är villkorad på samma uppslag.
--
-- FIXEN: bind policyn till PUBLIC, som de 53 andra. Ingen ny rättighet ges —
-- vem som får SELECT styrs av GRANT (postgres, snajp_app, snajp_web), och
-- villkoret `user_id = app.user_id` gäller oförändrat för alla roller. En
-- anropare utan `app.user_id` satt jämför mot NULL och får noll rader.
--
-- ALTER och inte DROP/CREATE: villkoret sattes senast av migration 035
-- (auth.uid() → app.user_id). Att återskapa policyn här hade tyst rullat
-- tillbaka 035 på varje databas som kör kedjan i ordning.

do $$
begin
  if to_regclass('public.platform_admins') is not null
     and exists (
       select 1 from pg_policy
       where polrelid = 'public.platform_admins'::regclass
         and polname = 'platform_admins_self_read'
     )
  then
    alter policy platform_admins_self_read on public.platform_admins to public;
  end if;
end $$;

comment on policy platform_admins_self_read on public.platform_admins is
  'TO PUBLIC med flit. Bunden till `authenticated` gäller policyn inte snajp_web, '
  'och då ger RLS noll rader utan att kasta — vilket syns som att /admin är 404.';
