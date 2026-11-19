-- 130: utkast som blev "tillagda" utan att någon artikel skrevs läggs tillbaka.
--
-- Codex-granskningen 2026-11-19: POST /api/kb/forslag/beslut märkte utkastet
-- `tillagd` och committade det innan inbäddningen och artikeln skrevs. Ett
-- avbrott däremellan lämnade utkastet tillagt utan artikel: borta ur listan,
-- och en ny skanning föreslog inte rubriken igen. Koden skriver nu artikeln och
-- beslutet i en transaktion (PostgresStorage.lagg_till_kb_forslag). Den här
-- migrationen rättar rader som redan hamnat i mellanläget.
--
-- Idempotent och smal: bara `tillagd` utan artikel_id; inget annat rörs.

update public.ss_kb_forslag
   set status = 'vantar', beslutad_at = null
 where status = 'tillagd' and artikel_id is null;
