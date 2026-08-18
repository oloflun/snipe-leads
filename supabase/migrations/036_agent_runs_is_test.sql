-- En testkörning ska gå att skilja från kundtrafik.
--
-- PROBLEMET: adminytans provkörningar skriver rader i agent_runs precis som
-- riktiga kundkörningar. Portföljvyn räknar dem, hälsobedömningen i
-- lib/admin/halsa.ts väger in dem, och en kund som knappt använt tjänsten kan
-- se aktiv ut för att VI provkört mot deras tenant. Siffror som inte går att
-- lita på är värre än inga siffror — de fattar beslut åt en.
--
-- Kolumnen är NOT NULL med default false, inte nullable: "vet inte" ska inte
-- vara ett möjligt tillstånd. Varje befintlig rad är per definition en riktig
-- körning, eftersom testflaggan inte fanns när den skrevs.
--
-- Additiv och bakåtkompatibel: befintliga INSERT:ar utan kolumnen fortsätter
-- fungera och får false.

alter table public.agent_runs
  add column if not exists is_test boolean not null default false;

comment on column public.agent_runs.is_test is
  'true = körning startad från adminytans testyta. Räknas aldrig som kundvolym.';

-- Partiellt index: adminvyn filtrerar nästan alltid BORT testkörningar, och
-- ett fullt index på en kolumn där 99 % är false är mest död vikt.
create index if not exists agent_runs_is_test_idx
  on public.agent_runs (tenant_id, created_at desc)
  where is_test;
