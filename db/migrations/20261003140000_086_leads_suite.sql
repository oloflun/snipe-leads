-- 086: Leads Suite (plan del F, Fas 10): anteckningar, uppgifter, statuslogg
-- och sparade vyer per prospekt, plus två nya härkomster.
--
-- Tidslinjen är INGEN tabell: den komponeras i kod (app/api/leads_suite.py)
-- ur prospektet, statusloggen, mejltråden, anteckningarna och uppgifterna.
-- En egen händelsetabell hade blivit en andra sanning som glider isär.
--
-- Statusloggen skrivs av storage.update_prospect när statusen faktiskt
-- ändras, så varje anropare (svarshanteringen, sändningen, PATCH) loggas på
-- ett ställe. kalla: kod | manuell | import.
--
-- Härkomst: 'lista' = rad ur en sökbyggd leadslista, 'iris' = bolag Iris
-- själv hittade i en körning. Före 086 bar båda 'import', och då gick det
-- inte att skilja en CSV-import från Iris egna fynd när automationsreglerna
-- per typ (app/leads/automation.py) ska tillämpas. Gamla rader står kvar som
-- 'import'.

alter table public.prospects drop constraint if exists prospects_origin_check;
alter table public.prospects add constraint prospects_origin_check
  check (origin in ('manual', 'example', 'import', 'test', 'inkorg', 'lista', 'iris')) not valid;

create table if not exists public.lead_anteckningar (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  prospect_id uuid not null references public.prospects(id) on delete cascade,
  text        text not null,
  created_at  timestamptz not null default now()
);
create index if not exists lead_anteckningar_prospekt_idx
  on public.lead_anteckningar (tenant_id, prospect_id);

create table if not exists public.lead_uppgifter (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  prospect_id uuid not null references public.prospects(id) on delete cascade,
  titel       text not null,
  forfaller   date,
  klar        boolean not null default false,
  klar_at     timestamptz,
  created_at  timestamptz not null default now()
);
create index if not exists lead_uppgifter_prospekt_idx
  on public.lead_uppgifter (tenant_id, prospect_id);

create table if not exists public.prospect_status_logg (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  prospect_id uuid not null references public.prospects(id) on delete cascade,
  fran        text,
  till        text not null,
  kalla       text not null default 'kod' check (kalla in ('kod', 'manuell', 'import')),
  created_at  timestamptz not null default now()
);
create index if not exists prospect_status_logg_prospekt_idx
  on public.prospect_status_logg (tenant_id, prospect_id);

create table if not exists public.lead_vyer (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  namn        text not null,
  filter      jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists lead_vyer_tenant_idx on public.lead_vyer (tenant_id);

do $$
declare
  t text;
begin
  foreach t in array array['lead_anteckningar', 'lead_uppgifter', 'prospect_status_logg', 'lead_vyer']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    execute format('drop policy if exists tenant_isolation on public.%I', t);
    execute format(
      'create policy tenant_isolation on public.%I
         using (tenant_id = current_setting(''app.tenant_id'', true)::uuid)
         with check (tenant_id = current_setting(''app.tenant_id'', true)::uuid)',
      t
    );
  end loop;
end $$;
