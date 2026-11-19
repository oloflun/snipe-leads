-- 131: avbrutna inrullningar tas bort av en egen funktion som aldrig rör ett
-- aktiverat skydd.
--
-- Codex-granskningen 2026-11-19 (runda 2): "Avbryt" på en påbörjad inrullning
-- läste först att tvåfaktorn inte var aktiv och anropade sedan
-- tvafaktor_avaktivera(). Den raderar också ett AKTIVERAT skydd inom två
-- minuter från senaste verifieringen, och aktiveringen sätter
-- senast_verifierad_at. En parallell session kunde alltså, i fönstret mellan
-- läsningen och raderingen, ta bort ett nyss aktiverat skydd utan kod.
--
-- tvafaktor_avbryt_inrullning() raderar bara en rad med aktiverad_at null, i en
-- och samma sats: det finns ingen läsning före som kan bli inaktuell.
-- Additiv och idempotent (create or replace, grant).

create or replace function public.tvafaktor_avbryt_inrullning()
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
  delete from public.tvafaktor
   where user_id = v_uid
     and aktiverad_at is null;
  return found;
end;
$$;

revoke all on function public.tvafaktor_avbryt_inrullning() from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.tvafaktor_avbryt_inrullning() to snajp_web;
  end if;
end;
$$;
