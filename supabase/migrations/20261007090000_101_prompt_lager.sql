-- 101: promptlagren, en gång per unik text (plan 2026-10-06, fas 7).
--
-- Spårvyn kapade varje fält i agent_runs.step_log vid 8 000 tecken
-- (step_runner.TRACE_FIELD_MAX_CHARS). Utkaststegets systemprompt är runt
-- 19 000 tecken, så overlay, kundlager och kontrakt syntes aldrig, och inte
-- heller slutet av användarmeddelandet. Nu bär step_log en lista lager (namn,
-- källa, tecken, hash) och texten till de stabila lagren — gemensamt,
-- grundprompt, skill, overlay, kundlager, kontrakt — läggs EN gång per unik
-- hash här. En skilltext på 11 000 tecken lagras alltså en gång, inte en gång
-- per körning, och går att visa exakt som den såg ut även efter att filen
-- ändrats. Det som varierar per körning (användarmeddelandet, svaret) står i
-- sin helhet i step_log.
--
-- Skrivs av storage.log_agent_run med insert … on conflict do nothing. Ingen
-- tenant_id: samma text är samma lager oavsett kund, och tabellen läses bara
-- via /api/admin (master-nyckeln). Kundlagret (agent_configs.instructions_md)
-- är admin-skriven text och hör hemma här av samma skäl.
--
-- GALLRING: ingen. Förslaget är 30 dagar för den varierande texten i
-- step_log; perioden är Antons beslut och den här tabellen bär ingen
-- kundskriven text.
--
-- Vidgar också agent_runs.agent_type med 'leads_underlag': anropen utanför
-- stegmotorn (bolagssökningen, Jev-triagen, profilkompileringen), loggade som
-- egna poster av app/agentcore/insyn.samla_anrop. Konstanten AGENT_RUN_TYPES
-- i app/storage/base.py ändras i samma diff.
--
-- Idempotent.

create table if not exists public.prompt_lager (
  hash       text primary key,
  text       text not null,
  created_at timestamptz not null default now()
);

comment on table public.prompt_lager is
  'Promptlagrens text per sha256 (Fas 7, insynen). agent_runs.step_log[].lager[].hash '
  'pekar hit. Skrivs med on conflict do nothing; en rad ändras aldrig.';

alter table public.prompt_lager enable row level security;

-- Plattformens tabell, inte arbetsytans: INTE grantad till snajp_web. Vägen
-- in går via backenden (snajp_app). Ingen update eller delete: en hash pekar
-- alltid på samma text.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert on public.prompt_lager to snajp_app;
    revoke update, delete on public.prompt_lager from snajp_app;

    drop policy if exists "snajp_app prompt_lager" on public.prompt_lager;
    create policy "snajp_app prompt_lager"
    on public.prompt_lager for all
    to snajp_app
    using (true) with check (true);
  end if;
end $$;

alter table public.agent_runs drop constraint if exists agent_runs_agent_type_check;
alter table public.agent_runs add constraint agent_runs_agent_type_check
  check (agent_type in (
    'support', 'leads', 'leads_research', 'leads_outreach', 'demo', 'bookkeeping',
    'leads_svar', 'leads_followup', 'leads_underlag'
  ));

-- Kedjan per bolag (GET /api/admin/prospects/{id}/kedja) söker på kolumnen,
-- som funnits sedan 025 men aldrig skrivits.
create index if not exists agent_runs_prospect_idx
  on public.agent_runs (prospect_id, created_at desc) where prospect_id is not null;

-- OBS DEPLOYORDNING: kör migrationen innan koden når miljön. Utan tabellen
-- loggar log_agent_run ett fel och sparar körningen utan lagertexterna; utan
-- det vidgade villkoret faller loggningen av 'leads_underlag'-posterna, som
-- insyn.samla_anrop fångar och loggar i stället för att fälla anroparen.
