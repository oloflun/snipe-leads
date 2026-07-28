-- Snajp-Support: kategorier anpassade för hjärtstartarbranschen (pilot).
-- Körs efter 004. Idempotent.
--
-- Ändringar mot tidigare uppsättning:
--   + garanti      (garantitid, vad som täcks)
--   + utbildning   (HLR-kurser, handhavande, användarstöd)
--   - konto        (inloggning/konto är marginellt i B2B-försäljning av AED;
--                   befintliga rader flyttas till teknisk_support, som är där
--                   inloggningsfrågor hamnar i den nya klassificeringen)

-- 1. Flytta befintlig data INNAN villkoren stramas åt, annars faller ALTER.
update ss_tickets set category = 'teknisk_support' where category = 'konto';
update ss_knowledge_base set category = 'teknisk_support' where category = 'konto';
update ss_classifications set category = 'teknisk_support' where category = 'konto';
delete from ss_category_rules where category = 'konto';

-- 2. Nya villkor.
alter table ss_tickets drop constraint if exists ss_tickets_category_check;
alter table ss_tickets add constraint ss_tickets_category_check check (category in
  ('teknisk_support', 'garanti', 'leverans', 'utbildning',
   'retur_reklamation', 'betalning', 'orderstatus', 'ovrigt'));

alter table ss_knowledge_base drop constraint if exists ss_knowledge_base_category_check;
alter table ss_knowledge_base add constraint ss_knowledge_base_category_check check (category in
  ('teknisk_support', 'garanti', 'leverans', 'utbildning',
   'retur_reklamation', 'betalning', 'orderstatus', 'ovrigt'));

alter table ss_classifications drop constraint if exists ss_classifications_category_check;
alter table ss_classifications add constraint ss_classifications_category_check check (category in
  ('teknisk_support', 'garanti', 'leverans', 'utbildning',
   'retur_reklamation', 'betalning', 'orderstatus', 'ovrigt'));

-- 3. Kunskapsbasartiklar kan vara utkast/platshållare tills riktigt material finns.
--    Flaggan syns i dashboarden så ingen tror att en platshållare är godkänd text.
alter table ss_knowledge_base add column if not exists is_placeholder boolean not null default false;
