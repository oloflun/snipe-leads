-- Fas B:s bedömning ska landa någonstans.
--
-- `icp_fit` räknas ut av modellen i Fas B steg 2 och **sparas aldrig**. Den
-- finns alltså i en logg och i ingenting annat: det går inte att sortera
-- prospekt på den, inte att mäta om urvalet blir bättre, och inte att svara
-- på "varför kontaktade agenten det här bolaget".
--
-- `disqualifiers` är den viktigare av de tre. Ett prospekt som VALDES BORT är
-- den enda datapunkt som visar att ICP-konfigurationen gör något — utan den
-- ser en för snäv ICP ut precis som en tom pipeline.

alter table public.prospects
  add column if not exists icp_fit numeric(3, 2)
    check (icp_fit is null or (icp_fit >= 0 and icp_fit <= 1));

alter table public.prospects
  add column if not exists qualified boolean;

alter table public.prospects
  add column if not exists disqualifiers text[] not null default '{}';

-- Granskningskön och körkontrollen frågar båda "vilka prospekt är kvar att
-- göra något med", vilket är ett filter på qualified.
create index if not exists prospects_qualified_idx
  on public.prospects (tenant_id, qualified, icp_fit desc);
