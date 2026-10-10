-- 111: tvåvägssynk mellan development och main (Anton 2026-10-10, docs/BESLUT.md).
--
-- Körningar och supportärenden speglas åt BÅDA hållen med det senast ändrade
-- som sanning (scripts/railway_synk.py). Det kräver två saker som tabellerna
-- inte hade:
--
-- * synk_andrad_at: när raden senast skrevs. De flesta tabeller saknar
--   updated_at, och utan en ändringstid går "senast ändrad vinner" inte att
--   avgöra. Sätts av en trigger vid varje insert och update. Synken skriver i
--   replica-läge, där triggern inte körs, så den kopierade tiden står kvar.
-- * synk_raderingar: en rad per raderad rad (tabell, nyckel, tid). Utan den
--   återuppstår det som raderats i den ena miljön vid nästa synk från den
--   andra.
--
-- Körs i båda miljöerna. Idempotent.

create table if not exists public.synk_raderingar (
  tabell     text not null,
  nyckel     text not null,
  raderad_at timestamptz not null default now(),
  primary key (tabell, nyckel)
);

create or replace function public.synk_markera() returns trigger
language plpgsql as $$
begin
  new.synk_andrad_at := now();
  return new;
end $$;

-- SECURITY DEFINER: appens roll ska inte behöva skrivrätt på loggen.
create or replace function public.synk_radera() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  delar text[] := '{}';
  kol text;
begin
  foreach kol in array tg_argv loop
    delar := delar || (to_jsonb(old) ->> kol);
  end loop;
  insert into public.synk_raderingar (tabell, nyckel)
  values (tg_table_name, array_to_string(delar, '|'))
  on conflict (tabell, nyckel) do update set raderad_at = now();
  return old;
end $$;

do $$
declare
  t record;
begin
  for t in
    select * from (values
      ('leads_job_ledger', 'job_id'), ('prospects', 'id'), ('prospect_sources', 'id'),
      ('prospect_status_logg', 'id'), ('outreach_threads', 'id'), ('outreach_messages', 'id'),
      ('send_queue', 'id'), ('lead_lists', 'id'), ('lead_list_items', 'id'), ('lead_samtal', 'id'),
      ('lead_anteckningar', 'id'), ('lead_uppgifter', 'id'), ('suppressions', 'id'), ('agent_runs', 'id'),
      ('ss_customers', 'id'), ('ss_customer_identifiers', 'id'), ('ss_tickets', 'id'),
      ('ss_conversations', 'id'), ('ss_messages', 'id'), ('ss_emails', 'id'), ('ss_email_attachments', 'id'),
      ('ss_classifications', 'id'), ('ss_decision_log', 'id'), ('ss_drafts', 'id'),
      ('ss_human_reviews', 'id'), ('customer_memory', 'id'), ('ss_agent_metrics', 'id'),
      ('agent_suggestions', 'id')
    ) as v(tabell, nyckel)
  loop
    if to_regclass('public.' || t.tabell) is null then
      continue;
    end if;
    execute format('alter table public.%I add column if not exists synk_andrad_at timestamptz not null default now()', t.tabell);
    execute format('drop trigger if exists synk_markera on public.%I', t.tabell);
    execute format('create trigger synk_markera before insert or update on public.%I
                    for each row execute function public.synk_markera()', t.tabell);
    execute format('drop trigger if exists synk_radera on public.%I', t.tabell);
    execute format('create trigger synk_radera after delete on public.%I
                    for each row execute function public.synk_radera(%L)', t.tabell, t.nyckel);
  end loop;
end $$;
