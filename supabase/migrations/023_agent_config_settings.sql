-- Kundens kontroller över leads-agenten: autonominivå och målgrupp (ICP).
--
-- I dag finns INGEN sådan knapp. Pipelinen är hårdkodad att stanna vid ett
-- köat utkast, och `SEND_QUEUE_POLL_SECONDS` är osatt i render.yaml så
-- schemaläggaren är avstängd — inget skickas någonsin. Det är säkert av
-- olyckshändelse, inte av design, och den sortens säkerhet försvinner tyst
-- den dag någon sätter env-varen.
--
-- Landar i `agent_configs`, som redan finns med unique(tenant_id, agent_type)
-- sedan 010. En egen tabell hade betytt en andra RLS-policy för samma data,
-- och det är precis så en tenant-läcka uppstår.
--
-- Jsonb och inte kolumner: ICP är ett dussin fält som kommer att ändras medan
-- vi lär oss vad kunderna faktiskt vill styra på. Autonomi är EN sträng med
-- tre värden och hade gärna fått vara en kolumn — men två lagringsformer för
-- "kundens inställningar" är ett ställe till att glömma.

alter table public.agent_configs
  add column if not exists settings jsonb not null default '{}'::jsonb;

-- Autonominivån måste vara ett av tre värden om den finns. Villkoret ligger i
-- databasen med flit: det här är fältet som avgör om ett mejl går till en
-- riktig mottagare utan att en människa sett det.
alter table public.agent_configs
  drop constraint if exists agent_configs_autonomy_check;

alter table public.agent_configs
  add constraint agent_configs_autonomy_check check (
    settings->>'autonomy' is null
    or settings->>'autonomy' in ('draft', 'first_contact', 'meeting')
  );

comment on column public.agent_configs.settings is
  'autonomy: draft (default) | first_contact | meeting. icp: {industries, '
  'exclude_industries, company_size, geography, roles, must_have, '
  'deal_breakers}. trace_verbose: bool. SOUL styr ton, ICP styr urval — '
  'två fält, två syften.';

-- Granskningskön behöver ett eget tillstånd i send_queue. Utan det finns bara
-- 'queued', som schemaläggaren plockar upp — ett utkast i draft-läge hade
-- alltså legat i exakt samma kö som ett godkänt och skickats så fort
-- SEND_QUEUE_POLL_SECONDS sätts. Autonominivån hade varit dekorativ.
alter table public.send_queue drop constraint if exists send_queue_status_check;
alter table public.send_queue add constraint send_queue_status_check
  check (status in ('queued', 'awaiting_review', 'sent', 'cancelled', 'blocked'));

-- Default är 'draft' för varje kund, inklusive de som redan finns. Ett fel
-- blir då ett dåligt utkast, inte ett skickat mejl till en riktig mottagare.
update public.agent_configs
set settings = jsonb_set(settings, '{autonomy}', '"draft"'::jsonb)
where settings->>'autonomy' is null;
