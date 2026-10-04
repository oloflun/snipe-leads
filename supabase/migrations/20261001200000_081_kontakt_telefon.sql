-- 081: Kontaktpersonens telefon på prospekt och listrader.
--
-- Antons minsta krav för ett kvalificerat lead (2026-10-01): en verifierad
-- kontaktperson med roll OCH telefonnummer. Registerkällan (merinfo,
-- app/leads/sources/merinfo.py) levererar alla tre, men tabellerna hade bara
-- namn, roll och e-post: telefonen föll bort mellan källan och kunden.
-- orgnr på listraden gör att en lista kan granskas och dedupliceras mot
-- registret utan att gå via bolagsnamnet.
alter table public.prospects
  add column if not exists contact_phone text;

alter table public.lead_list_items
  add column if not exists contact_phone text,
  add column if not exists orgnr text;
