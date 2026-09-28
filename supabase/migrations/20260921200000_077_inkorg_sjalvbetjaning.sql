-- 077: Självbetjänad inkorgskoppling — krypterat app-lösenord på inkorgsraden.
--
-- ## Vad som ändras och varför
--
-- Fram till nu kopplades en kunds inkorg av OSS: en rad i ss_mailboxes för
-- hand och app-lösenordet som miljövariabel (IMAP_PASSWORD_<SLUG>, se
-- migration 008). Det skalar inte till självbetjäning — en kund som skapar
-- konto själv kan inte sätta miljövariabler, och beslutet 2026-09-21 är att
-- "Synka inkorg" ska fungera utan att vi rör varje konto.
--
-- Kolumnen bär lösenordet KRYPTERAT med samma Fernet-lager som
-- integrationshemligheterna (app/integrationer/hemligheter.py, nyckeln
-- INTEGRATION_NYCKEL): AES-128-CBC + HMAC, aldrig klartext i vila. En
-- läsbehörighet på ss_mailboxes ger alltså fortfarande inte kundens mail —
-- det kräver även krypteringsnyckeln, som bara finns i backendens miljö.
-- Miljövariabelvägen finns kvar och vinner när den är satt, så Livrustnings
-- koppling påverkas inte.
--
-- ## Varför inte en egen tabell
--
-- Hemligheten hör 1:1 till inkorgsraden och dör med den (on delete cascade
-- hade varit en join för exakt en kolumn). Integrationerna gör likadant:
-- krypterad kolumn på raden, inte ett separat valv.

alter table public.ss_mailboxes
  add column if not exists secret_enc text;

comment on column public.ss_mailboxes.secret_enc is
  'App-lösenordet för IMAP, Fernet-krypterat med INTEGRATION_NYCKEL '
  '(app/integrationer/hemligheter.py). NULL när lösenordet i stället ligger i '
  'env (IMAP_PASSWORD_<SLUG>) eller när inkorgen inte är kopplad än. Aldrig '
  'klartext.';
