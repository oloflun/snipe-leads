-- Per-kund-inkorgar.
--
-- Pollern läste tidigare EN global uppsättning IMAP_HOST/USER/PASSWORD ur
-- config.py, vilket betyder ett enda mailkonto för hela tjänsten. Med flera
-- kunder behöver varje tenant sin egen inkorg.
--
-- Lösenordet lagras medvetet INTE här. Det läses ur env med tenantens slug som
-- nyckel (IMAP_PASSWORD_<SLUG>), så databasen aldrig innehåller en hemlighet i
-- vila och en läsbehörighet på ss_mailboxes inte räcker för att läsa kundens
-- mail. Värden kan härledas för gmail/outlook men måste anges för egen server.

alter table public.ss_mailboxes
  add column if not exists imap_host text;

comment on column public.ss_mailboxes.imap_host is
  'IMAP-värd. NULL för provider gmail/outlook, där värden härleds. Lösenord ligger i env, aldrig här.';

-- Livrustnings inkorg. Pollern hoppar över den tills IMAP_PASSWORD_LIVRUSTNING
-- är satt, så raden kan ligga här innan kunden lämnat sitt app-lösenord.
insert into public.ss_mailboxes (tenant_id, provider, address, status)
select t.id, 'imap', 'kontakt@livrustning.se', 'active'
from public.ss_tenants t
where t.slug = 'livrustning'
on conflict (tenant_id, address) do nothing;
