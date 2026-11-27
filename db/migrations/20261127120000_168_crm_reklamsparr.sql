-- 168: Snajp CRM, registrets reklamspärr på bolaget.
--
-- Beställning 5 efter granskningen 2026-11-27: reklamspärren ur SCB:s
-- företagsregister stod bara i svaret från POST /api/crm/v1/companies/{id}/enrich
-- och var borta efter en omladdning. Projektets regel är att ett utfall ska
-- finnas kvar efter omladdning (CLAUDE.md, "Varje funktion har ett sätt att
-- följa flödet").
--
-- crm_bolag.reklamsparr: vad registret senast sa om reklam. true: bolaget har
--   frånsagt sig reklam. false: tar emot reklam. null: okänt eller aldrig
--   hämtat. Skrivs vid varje berikning, också till false och null, och aldrig
--   av synken eller för hand. API:t visar den som registry_advertising_block.
--
-- Den sätter ALDRIG kontakta_inte och lägger ingen spärr: det är kundens val
-- (spärrlistan, crm_sparrar, migration 166).
--
-- Inga nya tabeller: radskyddet, grants och force row level security från 160
-- gäller den nya kolumnen som de står. Additiv och idempotent. Längst ned ett
-- partiellt index för spärrkontrollens fråga mot prospekten.

alter table public.crm_bolag add column if not exists reklamsparr boolean;

-- Spärrkontrollen läser kundens leads med status suppressed på telefonnummer
-- (app/crm/sparr.py: leadens_sparrade_nummer), och ringlistan läser samma
-- mängd. Utan index läser frågan varje prospekt hos kunden (prospects_tenant_idx)
-- och filtrerar statusen rad för rad. Det partiella indexet ger bara de
-- spärrade raderna. Skapas bara där prospects har kolumnerna (inte i en
-- databas med bara CRM-kedjan).
do $$
begin
  if exists (select 1 from information_schema.columns
             where table_schema = 'public' and table_name = 'prospects' and column_name = 'status')
     and exists (select 1 from information_schema.columns
                 where table_schema = 'public' and table_name = 'prospects' and column_name = 'tenant_id') then
    create index if not exists prospects_kund_sparrad_idx
      on public.prospects (tenant_id) where status = 'suppressed';
  end if;
end $$;
