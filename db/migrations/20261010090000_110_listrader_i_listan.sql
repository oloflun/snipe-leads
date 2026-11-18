-- 110: listornas leads stannar i listan (Anton 2026-10-10, docs/BESLUT.md).
--
-- * lead_list_items.prospect_id: raden öppnas i samma detaljvy som ett
--   Iris-lead och får research och utkast genom prospektet. Prospektet är
--   radens bakgrundspost: Iris-tabellen visar inte listkopplade prospekt, så
--   bolaget finns på ETT ställe (listan).
-- * lead_list_items.kallor: källorna Processa om redan prövat för raden. Nästa
--   omprövning söker i dem som inte prövats.
-- * lead_list_items.processad_at: när raden senast processades om.
-- * lead_lists.processering: förloppet för listans senaste Processa om eller
--   Skapa utkast, så att det syns i listan och överlever en omladdning.

alter table lead_list_items
  add column if not exists prospect_id uuid references prospects(id) on delete set null,
  add column if not exists kallor jsonb not null default '[]'::jsonb,
  add column if not exists processad_at timestamptz;

create index if not exists lead_list_items_prospect_idx
  on lead_list_items (tenant_id, prospect_id) where prospect_id is not null;

alter table lead_lists
  add column if not exists processering jsonb;
