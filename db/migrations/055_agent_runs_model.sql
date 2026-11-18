-- agent_runs saknar både `model` och `provider` (verifierat mot 010/025/027/036,
-- se plans/2026-08-28-skarpa-korningar-och-produktion.md §7). Två körningar
-- går i dag bara att skilja åt på filnamn, och jämföraren
-- scripts/jamfor_livekorningar.py (Fas 6: DeepSeek mot Gemini, minst 10
-- riktiga rundor per provider) behöver ett fält i DATA för att gruppera på
-- provider — inte en gissning ur vilket skript som kördes när.
--
-- `model` bär BÅDA delarna som en sträng, "<provider>:<modell>"
-- (t.ex. "gemini:gemini-3.6-flash"), i stället för två kolumner: anroparna
-- har redan settings.llm_provider och settings.model i scope tillsammans, och
-- en sammansatt sträng räcker för att gruppera jämförelsen. En cacheträff
-- (app/cache/svarscache.py) körde ingen modell alls och skriver "svarscache"
-- — det VAR ingen modellkörning och ska inte se ut som en i jämförelsen.
--
-- IDEMPOTENT: `if not exists` — samma stil som husets övriga ALTER-migrationer.
alter table public.agent_runs
  add column if not exists model text;

comment on column public.agent_runs.model is
  'Providern och modellen körningen faktiskt gjordes mot, som '
  '"<provider>:<modell>" (t.ex. "deepseek:deepseek-v4-flash"). '
  '"svarscache" när raden är en cacheträff och ingen modell kördes. '
  'null för körningar loggade innan denna kolumn fanns.';
