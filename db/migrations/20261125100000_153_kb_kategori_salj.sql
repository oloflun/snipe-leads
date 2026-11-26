-- Kunskapsbasens kategori "salj" (Erbjudande och säljfakta / Offer and sales facts).
--
-- Kunddemon 2026-11-24: webbplatsskanningen skrev bara supportartiklar, och
-- leadsagenten Iris fick inget av det kunden säljer. Skanningen föreslår nu
-- också säljfakta (tjänster och nytta, målgrupp, bevis, pris) i kategorin
-- 'salj', och kontextpaketet läser de artiklar kunden har lagt till.
--
-- Bara ss_knowledge_base vidgas. Ärendenas fack (ss_tickets,
-- ss_classifications) rörs INTE: triagen får aldrig välja 'salj'
-- (config.CATEGORIES mot config.KB_CATEGORIES). ss_kb_forslag.category har
-- inget CHECK-villkor (migration 121).
--
-- Additiv och idempotent: villkoret blir bara vidare, varje befintlig rad
-- uppfyller det, och drop/add går att köra om.

alter table ss_knowledge_base drop constraint if exists ss_knowledge_base_category_check;
alter table ss_knowledge_base add constraint ss_knowledge_base_category_check check (category in
  ('teknisk_support', 'garanti', 'leverans', 'utbildning',
   'retur_reklamation', 'betalning', 'orderstatus', 'ovrigt', 'salj'));
