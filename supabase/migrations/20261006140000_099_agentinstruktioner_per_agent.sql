-- 099: Globala agentinstruktioner per agent (2026-10-06).
--
-- Tabellen bar EN aktiv rad, gemensam för alla agenter. När en utkastmall
-- klistrades in under Globala agentinstruktioner 2026-10-05 ersatte den hela
-- det gemensamma lagret (sanningsreglerna i agent-core/AGENTS.md) för både
-- support och leads, eftersom det inte fanns någon annan plats att lägga den.
--
-- Nu har varje agent sin egen rad:
--   'alla'    det gemensamma lagret (fallback: agent-core/AGENTS.md)
--   'support' supportagentens grundprompt (fallback: agent-core/prompts/support-systemprompt.md)
--   'leads'   Iris grundprompt          (fallback: agent-core/prompts/leads-systemprompt.md)
-- Befintliga rader blir 'alla'. En aktiv rad per agent.
--
-- `feedback` sparar vad admin skrev, ordagrant, när texten kom till genom att
-- feedbacken bakades in (app/agentcore/baka_in.py). `ravtext` står kvar för de
-- äldre raderna.
--
-- Idempotent.

alter table public.agent_global_instructions
  add column if not exists agent_type text not null default 'alla';

alter table public.agent_global_instructions
  drop constraint if exists agent_global_instructions_agent_type_check;
alter table public.agent_global_instructions
  add constraint agent_global_instructions_agent_type_check
    check (agent_type in ('alla', 'support', 'leads'));

alter table public.agent_global_instructions
  add column if not exists feedback text not null default '';

-- Källan 'bakad' = admins feedback bakad in i det befintliga dokumentet.
-- 'aterstalld' = en tidigare version återställd.
alter table public.agent_global_instructions
  drop constraint if exists agent_global_instructions_kalla_check;
alter table public.agent_global_instructions
  add constraint agent_global_instructions_kalla_check
    check (kalla in ('ai', 'manuell', 'bakad', 'aterstalld'));

drop index if exists public.agent_global_instructions_en_aktiv;
create unique index if not exists agent_global_instructions_en_aktiv_per_agent
  on public.agent_global_instructions (agent_type) where aktiv;
