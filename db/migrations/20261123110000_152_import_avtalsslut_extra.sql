-- 152: listimporten tar med kundens egna kolumner och lämnar ett kvitto.
--
-- Importen (POST /api/leads/import) sparade åtta fält och tappade resten av
-- kundens CRM-export tyst. Nu följer det med:
--
--   lead_list_items.avtalsslut  avtalets slutdatum ur kundens egen data
--   lead_list_items.extra       filens omappade kolumner, rubrik -> värde
--   lead_lists.importinfo       ett bestående kvitto på importen (filnamn,
--                               mappning, vad som hoppades över)
--
-- `extra` och `avtalsslut` är källkundens egna uppgifter. De följer aldrig
-- med när plattformsadmin kopierar en lista till en annan kund
-- (app/api/admin_listor.py:LISTRADSFALT saknar dem med flit).
--
-- Additiv och idempotent. Null på gamla rader: listorna ser ut som förut.

alter table public.lead_list_items
  add column if not exists avtalsslut date,
  add column if not exists extra jsonb;

alter table public.lead_lists
  add column if not exists importinfo jsonb;
