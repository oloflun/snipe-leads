-- Gör spårningen faktiskt spårbar — ner till vad modellen fick och svarade.
--
-- Ingen schemaändring på agent_runs.step_log: den är redan jsonb och behåller
-- sin form. Det som ändras är vad koden LÄGGER i den. `RunTrace.as_log()`
-- (step_runner.py) kastar i dag bort `output` och `reasoning_content` — de
-- räknas fram, skickas till HTTP-anroparen via as_full(), och sparas aldrig.
--
-- Följden i praktiken: en spårvy som läser databasen kan visa skillnamn,
-- tokens och latens, men inte vad modellen faktiskt fick eller svarade. På
-- frågan "varför skrev den så här?" finns då bara ett skill-namn, och
-- skill-texten är fritt redigerbar (INV-AUDIT-001).
--
-- Den här filen finns alltså för dokumentationen och för indexet nedan.
-- Beteendeändringen ligger i app/agent/step_runner.py, styrd av
-- agent_configs.settings.trace_verbose (default PÅ — vi är i pilotfas och
-- behöver spåret mer än vi behöver diskutrymmet).
--
-- Kapning: 8 000 tecken per fält. ponytail: 8k räcker till felsökning;
-- flytta till objektlagring om vi behöver hela prompten.

comment on column public.agent_runs.step_log is
  'Ett objekt per LLM-anrop. Sedan 027 även system_prompt, user_message, '
  'raw_output och reasoning_content, kapade till 8000 tecken vardera och '
  'styrda av agent_configs.settings.trace_verbose (default true). '
  'Fas A (onboarding) skriver ingen agent_runs-rad alls — den kör Runner.run. '
  'Det är en känd lucka och visas i admin-vyn som "ingen spårning", inte som '
  'tom data.';

-- Spårvyn öppnar EN körning i taget via id, men listan bakom den filtrerar
-- på tenant och tid. Indexen finns sedan 025; det här är det som saknas för
-- notiscentrets väg tillbaka från ett event till dess körning.
create index if not exists agent_runs_tenant_created_idx
  on public.agent_runs (tenant_id, created_at desc);
