-- 150: hämtningen bygger på UID, och mejl som redan var öppnade märks.
--
-- Antons beställning 2026-11-23: "Bygg om hämtningen, men se till att
-- supporten ser de vi öppnat och därmed inte skriver utkast på dem utan
-- sorterar till manuell hantering."
--
-- Hämtningen sökte olästa mejl (UNSEEN). Ett mejl som någon hann öppna i
-- brevlådan innan Snajp hämtade det var läst på servern och kom aldrig in:
-- inget ärende, inget svar i konversationen, ingen statusändring. Nu hämtas
-- allt som kommit efter det senast hämtade mejlets UID, läst eller inte.
--
--   ss_mailboxes.imap_last_uid      högsta UID som står i databasen
--   ss_mailboxes.imap_uidvalidity   mappens UIDVALIDITY när märket sattes;
--                                   byter servern den gäller märket inte
--   ss_emails.last_i_brevladan      mejlet var läst på servern när Snajp
--                                   hämtade det: en människa har öppnat det.
--                                   Det kvalificeras och får utkast som
--                                   vanligt, men skickas aldrig av sig självt.
--   ss_emails.besvarat_i_brevladan  mejlet var dessutom besvarat från
--                                   brevlådan. Inget AI-utkast: Att hantera,
--                                   avbockat (support), eller överlämnat i
--                                   konversationen (leads).
--
-- Antons förtydligande samma dag: en konversation som Iris sköter får inte
-- tappas för att någon råkar öppna mejlet. Bara ett redan besvarat mejl
-- lämnas utan utkast.
--
-- Additiv och idempotent. Default false och null: gamla rader och API-ingest
-- beter sig som förut, och en brevlåda utan märke börjar med olästa plus de
-- senaste dagarnas mejl (connectors/imap.py).

alter table public.ss_mailboxes
  add column if not exists imap_last_uid bigint,
  add column if not exists imap_uidvalidity bigint;

alter table public.ss_emails
  add column if not exists last_i_brevladan boolean not null default false,
  add column if not exists besvarat_i_brevladan boolean not null default false;
