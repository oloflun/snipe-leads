-- Blockeraren. Ingen leads-körning har någonsin sparats i produktion.
--
-- `leads_agent.py` skriver agent_type="leads_research" (rad ~420) och
-- "leads_outreach" (rad ~646). Check-villkoret tillåter bara 'support' och
-- 'leads'. Mot Postgres kastar båda check-violation; körningen loggas alltså
-- aldrig. `GET /api/leads/runs` filtrerar dessutom på samma omöjliga värden,
-- så felet syns inte ens som en tom lista med fel innehåll — det syns som en
-- tom lista, vilket ser normalt ut.
--
-- Varför testsviten missade det i ett halvår: MemoryStorage hade inget
-- check-villkor alls. Testerna körde mot minnet och var gröna. Den luckan
-- stängs i samma commit som den här filen (app/storage/memory.py validerar
-- nu samma värdemängd), för en migration ensam hade bara flyttat samma fälla
-- ett steg åt sidan.
--
-- Kör den här TIDIGT, även om admin-UI:t dröjer. Spårdata som inte samlades
-- går inte att rekonstruera i efterhand.

alter table agent_runs drop constraint if exists agent_runs_agent_type_check;
alter table agent_runs add constraint agent_runs_agent_type_check
  check (agent_type in ('support', 'leads', 'leads_research', 'leads_outreach', 'demo'));

-- Spårvyn (Fas 6) behöver veta VAD en körning gällde, inte bara att den
-- skedde. Utan de här två är en leads-körning en rad utan koppling till
-- prospektet eller tråden den handlade om.
alter table agent_runs add column if not exists prospect_id uuid
  references prospects(id) on delete set null;
alter table agent_runs add column if not exists thread_id uuid
  references outreach_threads(id) on delete set null;

-- Grundningsgrindens utfall. Ligger på körningen, inte i step_log, eftersom
-- det är en egenskap hos hela körningen och ska gå att filtrera på.
alter table agent_runs add column if not exists grounding jsonb;

-- Admin-vyn sorterar alltid på tid, oftast filtrerat på typ. Utan de här två
-- är varje sida i /admin/korningar en seq scan över hela tabellen.
create index if not exists agent_runs_created_idx on agent_runs (created_at desc);
create index if not exists agent_runs_type_idx on agent_runs (agent_type, created_at desc);
