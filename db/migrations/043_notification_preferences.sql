-- Mejlnotiser: vem som vill bli störd, och av vad.
--
-- ## Varför en egen tabell och inte kolumner på `profiles`
--
-- `profiles` har EN policy och den är `for select` (000_base_schema.sql rad
-- 220). Kolumner där hade alltså kunnat läsas men aldrig skrivas — en
-- UPDATE under RLS returnerar noll rader UTAN att fela, så inställningen hade
-- sett ut att sparas och tyst rullat tillbaka vid varje omladdning. Att öppna
-- `profiles` för UPDATE i stället vore att öppna `role` för skrivning, och den
-- kolumnen avgör vad en medlem får göra.
--
-- ## Varför per ANVÄNDARE och inte per arbetsyta
--
-- Ett mejl går till en person, inte till ett bolag. Med en rad per arbetsyta
-- hade den som stänger av notiser stängt av dem för hela teamet — och den
-- rutan som visas vid kontoskapandet (components/auth/OnboardingForm.tsx)
-- frågar en enskild människa om det är okej att mejla DEM.
--
-- Följden är avsiktlig: en ny kollega i samma arbetsyta får sina egna
-- standardvärden och sin egen fråga, i stället för att ärva ett svar någon
-- annan gav.
--
-- ## Varför `events` är en text[] med check och inte tre boolean-kolumner
--
-- Samma skäl som `workspaces.addons` (022): villkoret räknar upp de tillåtna
-- värdena i databasen, så att applikationen inte kan glida ifrån dem. Tre
-- kolumner hade dessutom betytt en migration per ny notistyp, och listan
-- kommer att växa.

create table if not exists public.notification_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  -- Huvudströmbrytaren. Är den av spelar `events` ingen roll — men listan
  -- sparas ändå, så att den som slår på notiser igen får tillbaka sitt urval
  -- i stället för standardvärdet.
  email_enabled boolean not null default true,
  events text[] not null default array['lead', 'escalation']::text[],
  updated_at timestamptz not null default now()
);

alter table public.notification_preferences
  drop constraint if exists notification_preferences_events_check;

alter table public.notification_preferences
  add constraint notification_preferences_events_check check (
    events <@ array[
      'lead',        -- ett nytt kvalificerat lead har landat
      'escalation'   -- kundtjänstagenten lämnade över ett ärende till en människa
    ]::text[]
  );

comment on table public.notification_preferences is
  'Per ANVÄNDARE, inte per arbetsyta: ett mejl går till en person. Raden '
  'skapas när kunden svarar på frågan i onboardingen; saknas den gäller '
  'defaultvärdena i lib/actions/notiser.ts, som speglar kolumndefaultarna här.';

comment on column public.notification_preferences.email_enabled is
  'Huvudströmbrytare. Av = inga notismejl alls, oavsett vad events innehåller.';

alter table public.notification_preferences enable row level security;

-- `app.user_id` och inte `auth.uid()`. Auth.js-sessionen är vår egen JWT och
-- Supabases auth.uid() vet ingenting om den — hela poängen med 035. Guarden
-- mot tom sträng är läxan från 028: `''::uuid` kastar, och ett kast i en
-- policy ser ut som ett databasfel långt från orsaken.
drop policy if exists "own notification preferences" on public.notification_preferences;
create policy "own notification preferences"
on public.notification_preferences for all
using (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
with check (user_id = nullif(current_setting('app.user_id', true), '')::uuid);

-- Backenden skickar mejlen och måste kunna LÄSA vem som vill ha dem. Den kör
-- som `snajp_app` och sätter aldrig app.user_id — en policy som kräver den
-- hade gjort tabellen osynlig för just den process som behöver den.
--
-- GRANTET är strikt taget redundant: `alter default privileges` i 009 ger
-- snajp_app select/insert/update på varje ny tabell i public. Det står ändå
-- utskrivet, eftersom den regeln är osynlig från den här filen och en läsare
-- annars måste veta att den finns för att förstå att raden fungerar.
-- POLICYN är däremot inte redundant — RLS ärvs inte av något default.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select on public.notification_preferences to snajp_app;

    drop policy if exists "snajp_app reads notification preferences"
      on public.notification_preferences;
    create policy "snajp_app reads notification preferences"
    on public.notification_preferences for select
    to snajp_app
    using (true);
  end if;
end $$;
