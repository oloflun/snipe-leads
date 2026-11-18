-- 119: arbetsytan får företagets namn i onboardingen.
--
-- ## Felet
--
-- Signup-triggern (006) döper arbetsytan till "<kontots namn> workspace", och
-- onboardingen frågade aldrig efter företagets namn. Backendens kundnamn tas
-- ur arbetsytans namn (lib/snajp/provisionering.ts), så en ny kund hette
-- "Anna Andersson workspace" i kundregistret och i sidfoten på varje utskick.
-- Uppmätt 2026-11-18 i den lokala stacken: ss_tenants.name = 'Anna Testsson
-- workspace' för en nyss onboardad kund.
--
-- ## Varför en RPC och inte en UPDATE-policy på `workspaces`
--
-- Samma skäl som 038, 040 och 044: en policy gäller hela raden, och raden bär
-- `slug`, som pekar ut backend-tenanten. Funktionen skriver EN kolumn, på den
-- arbetsyta som `app.user_id` tillhör. Det finns ingen parameter som pekar ut
-- en annan arbetsyta.
--
-- En UPDATE utan användaridentitet fungerar inte heller: `workspaces` har
-- radskydd utan uppdateringsregel, så satsen träffar noll rader utan fel. Det
-- provades först, och namnet stod kvar.
--
-- Additiv och idempotent: `create or replace`, inga kolumner rörs.

create or replace function public.set_workspace_name(nytt text)
returns text
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $$
declare
  anvandare uuid := nullif(current_setting('app.user_id', true), '')::uuid;
  arbetsyta uuid;
  rent text := btrim(regexp_replace(coalesce(nytt, ''), '\s+', ' ', 'g'));
  resultat text;
begin
  if anvandare is null then
    raise exception 'ingen inloggad användare';
  end if;

  select workspace_id into arbetsyta from public.profiles where id = anvandare;
  if arbetsyta is null then
    raise exception 'användaren saknar arbetsyta';
  end if;

  if char_length(rent) < 2 or char_length(rent) > 80 then
    raise exception 'namnet ska vara mellan 2 och 80 tecken';
  end if;

  update public.workspaces
     set name = rent
   where id = arbetsyta
  returning name into resultat;

  return resultat;
end;
$$;

-- Migration 018 återkallade execute på public för alla funktioner.
revoke all on function public.set_workspace_name(text) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.set_workspace_name(text) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.set_workspace_name(text) to authenticated;
  end if;
end $$;

comment on function public.set_workspace_name(text) is
  'Sätter arbetsytans namn till företagets. Skriver EN kolumn på den inloggades '
  'arbetsyta, se filens docstring om varför det inte är en UPDATE-policy.';
