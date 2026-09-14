-- Agentens föreslagna lärdomar — självlärningen får en persistensyta.
--
-- ## Vad som var fel innan
--
-- Supportens steg 5 (cs:kb-article) och leads steg 9 (_fanga_kunskap,
-- sa:call-summary) RÄKNADE UT en lärdom på varje körning — "det här ärendet
-- avslöjar en kunskapslucka", "det här varvet säger något om ICP:n" — och
-- kastade den. Utdatan fanns i agent_runs.step_log och ingenstans annars:
-- ingen yta läste den, ingen ackumulering skedde, och samma lucka
-- återupptäcktes från noll i varje ärende.
--
-- ## Vad agenten INTE får göra (INV-LEARN-001)
--
-- Agenten skriver FÖRSLAG hit. Den skriver ALDRIG själv in något i
-- kunskapsbasen, kontextpaketet eller ICP:n — godkännandet är en människas
-- klick i admin, och först då skapas KB-artikeln (i kod, av endpointen).
-- Det är samma beslut som _fanga_kunskaps docstring pekar ut som "inte
-- taget": en agent som uppdaterar sitt eget facit har en annan riskprofil,
-- och den risken tas inte tyst i en migration.
--
-- ## Dedupe
--
-- Ett partiellt unikt index på (tenant_id, dedupe_key) där status = 'ny':
-- agenten som ser samma lucka i tio ärenden ger EN rad att granska. Ett
-- godkänt/avfärdat förslag blockerar inte ett nytt med samma nyckel — en
-- lucka kan återuppstå efter att artikeln som stängde den tagits bort.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

create table if not exists agent_suggestions (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references ss_tenants(id) on delete cascade,
  -- Vilken agent som såg luckan: 'support' | 'leads'.
  agent_type  text not null check (agent_type in ('support', 'leads')),
  -- Vad förslaget ÄR: en KB-artikel att skapa, eller en marknadsinsikt att
  -- väga in i ICP/kontextpaket. Nya sorter kräver en migration — hellre ett
  -- medvetet tillägg än en fritextkolumn som blir en tyst taxonomi.
  kind        text not null check (kind in ('kb_article', 'marknadsinsikt')),
  title       text not null,
  -- Förslagets innehåll som JSON: kb_article bär {title, content, category},
  -- marknadsinsikt bär {gap, icp_adjustment, evidence}. JSONB och inte
  -- kolumner: de två sorterna delar ingen struktur, och nästa sort ska inte
  -- kräva en alter table.
  content     jsonb not null default '{}'::jsonb,
  dedupe_key  text not null,
  status      text not null default 'ny'
              check (status in ('ny', 'godkand', 'avfard')),
  created_at  timestamptz not null default now()
);

create unique index if not exists agent_suggestions_dedupe_ny_idx
  on agent_suggestions (tenant_id, dedupe_key)
  where status = 'ny';

create index if not exists agent_suggestions_tenant_status_idx
  on agent_suggestions (tenant_id, status, created_at desc);

-- RLS: samma tenant_isolation-mönster som migration 010.
alter table agent_suggestions enable row level security;
alter table agent_suggestions force row level security;
drop policy if exists tenant_isolation on agent_suggestions;
create policy tenant_isolation on agent_suggestions
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Två nya agent_runs-typer: svarshanteringen (app/leads/svar.py) och
-- uppföljningsgeneratorn (app/leads/follow_up_generator.py). Samma regel som
-- migration 045: check-villkoret och AGENT_RUN_TYPES i storage/base.py ändras
-- i SAMMA ändring — det var luckan som gömde "ingen leads-körning har
-- någonsin sparats" i ett halvår.
alter table public.agent_runs drop constraint if exists agent_runs_agent_type_check;
alter table public.agent_runs add constraint agent_runs_agent_type_check
  check (agent_type in (
    'support', 'leads', 'leads_research', 'leads_outreach', 'demo', 'bookkeeping',
    'leads_svar', 'leads_followup'
  ));
