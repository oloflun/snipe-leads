-- 132: aktiveringen av tvåfaktorn gäller bara den hemlighet som verifierades.
--
-- Codex-granskningen 2026-11-19 (runda 3): bekraftaInrullning läser hemlighet A,
-- prövar koden mot den och anropar sedan tvafaktor_aktivera(steg, hashar). En
-- parallell "Påbörja" kan byta A mot B däremellan (tvafaktor_paborja skriver över
-- en inaktiv rad), och aktiveringen slog då på tvåfaktorn med B, en hemlighet
-- användarens app aldrig fått. Nästa inloggning går inte att klara.
--
-- Den nya överlagringen tar med den krypterade hemligheten som koden prövades
-- mot och aktiverar bara om raden fortfarande bär exakt den. Byttes hemligheten
-- svarar den false, och webben ber användaren börja om.
--
-- Additiv: den gamla tvåargumentsvarianten finns kvar så att webben som körs
-- under utrullningen fungerar (schemat får ligga före koden). Webben anropar
-- den inte längre; en senare migration drar in den.

create or replace function public.tvafaktor_aktivera(p_steg bigint, p_kodhashar text[], p_hemlighet text)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := nullif(current_setting('app.user_id', true), '')::uuid;
begin
  if v_uid is null then
    return false;
  end if;
  if p_steg is null
     or p_hemlighet is null
     or p_kodhashar is null
     or cardinality(p_kodhashar) < 1
     or cardinality(p_kodhashar) > 20
     or exists (select 1 from unnest(p_kodhashar) h where h is null or h !~ '^[0-9a-f]{64}$') then
    raise exception 'ogiltiga argument';
  end if;

  update public.tvafaktor
     set aktiverad_at = now(),
         senaste_steg = p_steg,
         senast_verifierad_at = now(),
         uppdaterad_at = now()
   where user_id = v_uid
     and aktiverad_at is null
     and hemlighet = p_hemlighet;
  if not found then
    return false;
  end if;

  delete from public.tvafaktor_aterstallningskoder where user_id = v_uid;
  insert into public.tvafaktor_aterstallningskoder (user_id, kod_hash)
  select v_uid, h from unnest(p_kodhashar) h
  on conflict do nothing;
  return true;
end;
$$;

revoke all on function public.tvafaktor_aktivera(bigint, text[], text) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.tvafaktor_aktivera(bigint, text[], text) to snajp_web;
  end if;
end;
$$;
