-- 092: automatutskick på ss_emails (plan 2026-10-05, fas 1).
--
-- IMAP-connectorn läste hela meddelandet men slängde List-Unsubscribe,
-- Auto-Submitted och Precedence. Utan dem blev nyhetsbrev och driftnotiser
-- kundärenden, och med tom kunskapsbas eskalerades de alla (Alunix
-- 2026-10-04). Flaggan sätts vid hämtningen och läses av klassningens första
-- regel, före Jev och före varje modellanrop.
--
-- Default false: gamla rader och API-ingest saknar headers och klassas som
-- förut, på avsändare och innehåll.

alter table public.ss_emails
  add column if not exists automatutskick boolean not null default false;
