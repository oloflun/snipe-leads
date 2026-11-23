-- 148: en påbörjad inrullning av tvåfaktorn gäller i femton minuter.
--
-- Codex-granskningen 2026-11-20 (runda 15): inrullningen krävde bara en
-- adminsession. En stulen session till ett konto utan aktiv tvåfaktor kunde
-- rulla in angriparens egen hemlighet och få återställningskoderna; ägarens
-- egen session nekades sedan adminåtkomst och ägaren saknade den nya faktorn.
-- Webben kräver nu lösenordet på nytt innan en inrullning påbörjas
-- (lib/actions/tvafaktor.ts: paborjaInrullning, med inloggningens spärr mot
-- gissning). Hemligheten skapas först efter den prövningen, så den påbörjade
-- raden är beviset för den. Här binds beviset i tid: aktiveringen godtar bara
-- en rad som påbörjats (uppdaterad_at) de senaste femton minuterna. En gammal
-- påbörjad rad kan inte aktiveras i efterhand av den som senare kommer åt
-- sessionen; användaren börjar om och anger lösenordet igen.
--
-- tvafaktor_aktivera är 140 med tidsgränsen. Idempotent (create or replace).

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
  -- 140: utan lösenord finns ingen väg in efter aktiveringen.
  if not exists (select 1 from auth.users u
                  where u.id = v_uid and u.encrypted_password is not null
                    and u.encrypted_password <> '') then
    raise exception 'kraver_losenord';
  end if;

  update public.tvafaktor
     set aktiverad_at = now(),
         senaste_steg = p_steg,
         senast_verifierad_at = now(),
         uppdaterad_at = now()
   where user_id = v_uid
     and aktiverad_at is null
     and hemlighet = p_hemlighet
     -- 148: en påbörjad inrullning gäller i femton minuter.
     and uppdaterad_at > now() - interval '15 minutes';
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
end $$;
