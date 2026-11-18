-- Kategorier anpassade för hjärtstartarbranschen (pilot).
--
-- ÅTERSTÄLLD UR LIGGAREN 2026-08-16. Den här migrationen kördes via
-- Management-API:t och dess repo-fil finns inte längre — kommentaren i den
-- registrerade SQL:en pekar på `005_snajp_pilot_categories.sql`, men den
-- platsen upptas numera av `005_workspace_products.sql`. DDL:en fanns alltså
-- BARA i databasen, i ingen gren och i ingen diff.
--
-- SQL:en nedan är ordagrant hämtad ur
-- `supabase_migrations.schema_migrations.statements` och är den som faktiskt
-- kördes. Den återges här för att en ny databas ska bli likadan som den vi har.

update ss_tickets set category = 'teknisk_support' where category = 'konto';
update ss_knowledge_base set category = 'teknisk_support' where category = 'konto';
update ss_classifications set category = 'teknisk_support' where category = 'konto';
delete from ss_category_rules where category = 'konto';

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

alter table ss_knowledge_base add column if not exists is_placeholder boolean not null default false;
