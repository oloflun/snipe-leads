-- Var ett prospekt kommer ifrån.
--
-- BAKGRUND: `POST /api/leads/runs/batch` svarar 422 "Inga prospekt att köra
-- på" när tenanten är tom. En ny kund har alltid noll prospekt, så knappen
-- "Starta körning" kunde inte tryckas förrän någon lagt in bolag för hand —
-- alltså innan de sett agenten göra någonting alls.
--
-- Lösningen är exempelbolag: påhittade företag som ligger inom kundens ICP och
-- visar hur agenten arbetar. Och i samma stund som påhittade bolag ligger i
-- samma tabell som riktiga behövs en kolumn som skiljer dem åt — annars är den
-- enda skillnaden att namnet ser påhittat ut, vilket ingen kod kan läsa.
--
-- VARFÖR DET INTE RÄCKER MED ETT NAMNPREFIX: ett prefix är text i ett fält
-- kunden kan redigera. `origin` är ett check-villkor i databasen, och
-- send-guarden slår upp den innan provider.send(). Ett exempelbolag som mejlas
-- är i bästa fall ett mejl till en adress som inte finns, i värsta fall till
-- ett riktigt bolag som råkar heta samma sak.
--
-- 'import' finns med redan nu fastän ingenting skriver den: kolumnen ska inte
-- behöva ett nytt check-villkor den dag en CSV-import byggs, och en ALTER på
-- ett check-villkor i drift är en låsning av tabellen.

alter table public.prospects
  add column if not exists origin text not null default 'manual'
    check (origin in ('manual', 'example', 'import'));

comment on column public.prospects.origin is
  'manual = kunden eller agenten lade in bolaget. example = påhittat '
  'exempelbolag ur ICP:t, får ALDRIG mejlas (blockeras i send_guard). '
  'import = kom in via en filimport.';

-- Körkontrollen och granskningskön frågar "vilka riktiga prospekt finns", och
-- det är ett filter på origin. Utan index blir det en seq scan per körning när
-- en demo-tenant fyllts på med exempelbolag.
create index if not exists prospects_origin_idx
  on public.prospects (tenant_id, origin);
