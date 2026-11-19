-- snajp_app får radera i de två tabeller en kodväg faktiskt raderar i.
--
-- Migration 009 räknade upp arton tabeller och gav `select, insert, update` på
-- alla. Inte `delete`. Raden `alter default privileges ... grant select, insert,
-- update on tables to snajp_app` upprepar samma tre för allt som skapats sedan
-- dess, så luckan har följt med varje ny tabell.
--
-- Det syntes inte förrän 2026-08-21, av två skäl som förstärker varandra:
--
--  * Bara TVÅ kodvägar i hela backenden gör DELETE. Allt annat är
--    append-only eller status-uppdateringar, alltså täckt av update.
--  * Sviten kör mot MemoryStorage, som inte har några rättigheter att sakna.
--    Och den som körde mot en riktig databas gjorde det som `postgres`, där
--    frågan aldrig ställs.
--
-- Följden var att `POST /api/inbox/mock` svarade 500 med "permission denied
-- for table ss_emails" — det gick alltså inte att generera ett enda testmejl i
-- någon miljö som kör med snajp_app-rollen, vilket är den roll INV-SEC-001
-- kräver. Felet såg ut som ett programfel och var ett rättighetsfel.
--
-- Barnraderna (ss_email_attachments, ss_classifications, ss_drafts,
-- beslutsloggens mailrader) behöver INGET eget grant: `on delete cascade` i
-- migration 004 körs med den refererade tabellens ägarrättigheter, inte med
-- anroparens. Att lista dem här hade vidgat ytan utan att lösa något.
--
-- ss_tickets står med flit inte här. Ärendet refereras av mailet och inte
-- tvärtom, och spåret av att ett ärende funnits ska inte försvinna för att en
-- demoinkorg städas — se docstringen i postgres.delete_emails_by_provider.

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    -- Demoinkorgens omladdning: byter UT tidigare mock-mail, provider-scopat,
    -- så att den aldrig kan röra IMAP- eller API-inkorgen (storage/base.py).
    grant delete on table ss_emails to snajp_app;

    -- Rate limit-städningen. Plattformsnivå, ingen tenant_id, raderar rader
    -- äldre än ett dygn. Samma lucka, bara ännu tystare: den körs i bakgrunden
    -- och en misslyckad städning syns som att tabellen växer.
    if to_regclass('public.platform_rate_events') is not null then
      grant delete on table platform_rate_events to snajp_app;
    end if;
  end if;
end $$;
