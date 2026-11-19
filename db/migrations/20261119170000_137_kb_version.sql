-- 137: KB-versionen i databasen, i samma transaktion som artikeln.
--
-- Codex-granskningen 2026-11-19 (runda 6): svarscachens KB-version var en
-- räknare i Redis som api:t höjde EFTER att artikeln committats
-- (app/api/kb.py: lagg_till_kb_forslag, sedan versioner.bumpa_kb). Föll Redis
-- där fångade bumpa_kb felet och höjde bara processens egen räknare; nästa
-- lyckade läsning i Redis gav den gamla versionen, och gamla svar matchade i
-- upp till 21 dagar till. Ett processavbrott mellan commit och höjning gav
-- samma lucka, och ett nytt klick reparerade den inte eftersom utkastet redan
-- var tillagt.
--
-- Nu höjer en trigger på ss_knowledge_base en räknare per kund i samma
-- transaktion som varje insert, update och delete, oavsett skrivväg. Räknaren
-- ingår i cachenyckeln (storage.kb_cachestatus, versioner.kb_version_med_giltighet).
-- Rullas skrivningen tillbaka, rullas höjningen tillbaka med den.
--
-- Ingen främmande nyckel mot ss_tenants: när en kund raderas kaskaderar
-- artiklarna, triggern körs för varje rad, och en ny rad här hade då fällt
-- raderingen av kunden. Raden bär bara ett tal och raderas med kunden nedan.
-- Triggern är ENABLE ALWAYS, så att den körs också när synken skriver i
-- replica-läge, om tabellen en dag förs över. Additiv och idempotent.

create table if not exists public.ss_kb_version (
  tenant_id  uuid primary key,
  version    bigint not null default 0,
  andrad_at  timestamptz not null default now()
);

comment on table public.ss_kb_version is
  'Räknare per kund som höjs i samma transaktion som varje ändring i ss_knowledge_base. Svarscachens KB-version. Migration 137.';

alter table public.ss_kb_version enable row level security;

drop policy if exists kb_version_tenant on public.ss_kb_version;
create policy kb_version_tenant on public.ss_kb_version
  for select
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

create or replace function public.ss_kb_version_hoj()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_tenanter uuid[] := '{}';
  v_tenant   uuid;
begin
  if tg_op in ('INSERT', 'UPDATE') then
    v_tenanter := array_append(v_tenanter, new.tenant_id);
  end if;
  if tg_op = 'DELETE' then
    v_tenanter := array_append(v_tenanter, old.tenant_id);
  elsif tg_op = 'UPDATE' and old.tenant_id is distinct from new.tenant_id then
    v_tenanter := array_append(v_tenanter, old.tenant_id);
  end if;
  foreach v_tenant in array v_tenanter loop
    continue when v_tenant is null;
    -- Bara för en kund som finns: under raderingen av en kund kaskaderar
    -- artiklarna, och då ska ingen ny rad skrivas.
    insert into public.ss_kb_version as v (tenant_id, version, andrad_at)
    select v_tenant, 1, now()
     where exists (select 1 from public.ss_tenants where id = v_tenant)
    on conflict (tenant_id) do update
      set version = v.version + 1, andrad_at = now();
  end loop;
  return null;
end;
$$;

revoke all on function public.ss_kb_version_hoj() from public;

drop trigger if exists ss_kb_version_hoj on public.ss_knowledge_base;
create trigger ss_kb_version_hoj
  after insert or update or delete on public.ss_knowledge_base
  for each row execute function public.ss_kb_version_hoj();
alter table public.ss_knowledge_base enable always trigger ss_kb_version_hoj;

-- Raden följer kunden när kunden raderas.
create or replace function public.ss_kb_version_kund_raderad()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  delete from public.ss_kb_version where tenant_id = old.id;
  return null;
end;
$$;

revoke all on function public.ss_kb_version_kund_raderad() from public;

drop trigger if exists ss_kb_version_kund_raderad on public.ss_tenants;
create trigger ss_kb_version_kund_raderad
  after delete on public.ss_tenants
  for each row execute function public.ss_kb_version_kund_raderad();

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select on table public.ss_kb_version to snajp_app;
  end if;
end $$;
