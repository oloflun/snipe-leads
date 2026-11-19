-- 140: tvåfaktorn aktiveras bara för ett konto med lösenord.
--
-- Codex-granskningen 2026-11-19 (runda 8): konton som skapats genom Google
-- eller Microsoft (lib/auth.ts: upsertOAuthUser) saknar encrypted_password.
-- De kunde ändå rulla in tvåfaktor. Efter aktiveringen nekar OAuth-vägen
-- kontot (ett konto med tvåfaktor loggar in med lösenord och kod), och
-- lösenordsvägen kräver ett lösenord innan koden prövas. Administratören var
-- utelåst trots giltiga återställningskoder. Nu vägrar aktiveringen högt för
-- ett konto utan lösenord, och webben säger åt användaren att sätta ett först
-- (lib/actions/tvafaktor.ts, felkoden kraver_losenord).
--
-- Versionen med två argument från 128 tas bort. Den prövade inte vilken
-- hemlighet koden verifierats mot (132 lade till det), ingen kod anropar den
-- sedan 132, och den har aldrig nått main. Kvar hade den varit en väg runt
-- både hemlighetsprövningen och lösenordskravet.
--
-- Idempotent (create or replace, drop if exists).

drop function if exists public.tvafaktor_aktivera(bigint, text[]);

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
end $$;
