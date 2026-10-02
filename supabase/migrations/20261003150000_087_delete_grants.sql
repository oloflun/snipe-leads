-- 087: snajp_app får radera sparade vyer (Leads Suite, migration 086) och
-- koppla ur en inkorg (ss_mailboxes, migration 077).
--
-- Samma lucka som 041 beskriver: default privileges ger snajp_app bara
-- select/insert/update på nya tabeller, aldrig delete. DELETE /api/leads/vyer/{id}
-- svarade därför 500 "permission denied for table lead_vyer" på development
-- (röktest 2026-10-02). Sviten kör mot MemoryStorage och ser aldrig felet.
--
-- ss_mailboxes: "Koppla ur inkorgen" i Inställningar › Inkorgar
-- (DELETE /api/inbox/mailboxes/{id} → storage.delete_mailbox) har haft samma
-- lucka sedan 077 och svarat 500 i varje miljö. Hittad av den nya vakten
-- snajp-support/tests/invariants/test_delete_grants.py.
--
-- Bara lead_vyer av 086:s tabeller: den enda en kodväg raderar i.
-- Anteckningar, uppgifter och statusloggen är append-only/uppdateras; deras
-- rader försvinner bara via on delete cascade från prospects.

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant delete on table public.lead_vyer to snajp_app;
    grant delete on table public.ss_mailboxes to snajp_app;
  end if;
end $$;
