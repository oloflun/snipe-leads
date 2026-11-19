-- Leads-jobbens persistenta liggare (INV-JOB-002) + budgetindex.
--
-- ## Varför tabellen behövs
--
-- Vakten mot omkörning i hantera_leads_jobb (app/api/leads.py) läste bara
-- Redis-jobbposten, och den ljuger på två sätt för köade batchjobb:
--
--   1. RedisJobStore.get auto-failar "processing"-poster efter 300 s
--      (JOB_TIMEOUT_SECONDS) — men jobbraden skapas när prospektet KÖAS,
--      inte när arbetet börjar. Med leads_workers=1 står jobb nr 5+ i en
--      18-jobbsbatch i kö längre än så, och deras poster flippar till
--      "failed" innan första LLM-anropet ens gjorts.
--   2. Posten TTL:ar bort helt efter 3 600 s.
--
-- Vid ett XAUTOCLAIM-återtag (varje worker-varv + engångssvepet vid varje
-- deploy/omstart, se app/jobs/stream.py och app/main.py) ser vakten då
-- "failed" eller ingenting — aldrig "completed" — och kör om HELA
-- research+utkast-kedjan. Uppmätt följd 2026-09-01: en färdig batch om
-- 18 leads kördes om i sin helhet efter en omstart, ~18 kr i LLM-kostnad
-- utan någon användarhandling.
--
-- Liggaren är sanningen som överlever både 300-sekundersflippen och TTL:n:
-- en rad per leads-jobb, skriven vid köande (queued), start (processing)
-- och slut (completed/failed). Vakten läser den FÖRST; Redis-posten blir en
-- snabbväg, inte en sanning. Vid konflikt gäller Postgres.
--
-- ## Budgetindexet
--
-- kontrollera_leads_budget (app/leads/budget.py) summerar agent_runs-tokens
-- per tenant för leads-typerna över ett 24-timmarsfönster vid varje
-- körningsstart. Indexet gör den frågan till en indexläsning i stället för
-- en tabellsvepning.

create table if not exists public.leads_job_ledger (
  job_id       text primary key,
  tenant_id    uuid not null references public.ss_tenants(id) on delete cascade,
  -- Null för batchens föräldrajobb (sökfasen) — det har inget prospekt.
  prospect_id  uuid,
  -- 'research' | 'research_and_draft' | 'batch' | 'draft' — fritext med
  -- flit: värdemängden ägs av api/leads.py och en check hade tvingat en
  -- migration för varje ny jobbsort utan att skydda något (raden är en
  -- logg, inte ett kontrakt).
  scope        text not null,
  status       text not null default 'queued'
               check (status in ('queued', 'processing', 'completed', 'failed')),
  created_at   timestamptz not null default now(),
  completed_at timestamptz
);

comment on table public.leads_job_ledger is
  'En rad per leads-jobb (INV-JOB-002). Sanningen om huruvida ett jobb '
  'redan är färdigt — Redis-jobbposten auto-failar/TTL:ar och får ALDRIG '
  'ensam avgöra om ett återtaget jobb ska köras om.';

comment on column public.leads_job_ledger.status is
  'queued = köad, ej påbörjad. processing = arbete pågår. completed = '
  'FÄRDIG — ett återtag av det här jobbet ska kvitteras utan körning. '
  'failed = avslutad med fel (får tas om).';

create index if not exists leads_job_ledger_tenant_idx
  on public.leads_job_ledger (tenant_id, created_at desc);

-- RLS: samma tenant_isolation-mönster som migration 010/051.
alter table public.leads_job_ledger enable row level security;
alter table public.leads_job_ledger force row level security;
drop policy if exists tenant_isolation on public.leads_job_ledger;
create policy tenant_isolation on public.leads_job_ledger
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

grant select, insert, update, delete on table public.leads_job_ledger to snajp_app;

-- Budgetfrågans index (tenant + typ + tid). agent_runs har sedan tidigare
-- bara (tenant_id)-vägar via primärnyckeln/generella index — 24h-summan per
-- agent_type behöver den här sammansättningen.
create index if not exists agent_runs_tenant_type_created_idx
  on public.agent_runs (tenant_id, agent_type, created_at desc);

-- OBS DEPLOYORDNING (samma mönster som migration 058): koden som skriver
-- liggaren deployas från grenen, migrationen körs separat via
-- `python scripts/railway_migrate.py --env development --apply`. Kör den
-- INNAN koden når miljön — storage-lagret skriver till tabellen från första
-- körningen och fäller annars varje leads-jobb med "relation does not exist".
