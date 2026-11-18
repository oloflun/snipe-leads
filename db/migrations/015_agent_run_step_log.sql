-- G10-revisionsloggen behöver kunna svara på "vilket skill-steg gjorde vad?",
-- inte bara "vilka skills var inblandade". step_log är en rad per faktiskt
-- LLM-anrop: skill, antal försök, om steget eskalerade, latens, och de
-- sources_used/context_refs steget själv rapporterade (Del C p.4).
--
-- Behövs eftersom supportagenten gick från EN hopklistrad prompt till ETT
-- anrop per skill-steg — nu finns det faktiska steg att logga.

alter table agent_runs add column if not exists step_log jsonb not null default '[]'::jsonb;
