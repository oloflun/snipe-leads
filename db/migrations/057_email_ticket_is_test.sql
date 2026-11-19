-- Testmail och testärenden ska kunna skiljas från skarpa.
--
-- Utan kolumnen landar "Hämta testmail" i samma lista som kundens riktiga
-- inkorg. Då ser en testkörning ut som ett ärende att följa upp — precis
-- den förväxlingen exempelbolagen redan gjorde på leads-sidan.
--
-- Backfill: mock-provider är definitionen av testmail hittills.

alter table public.ss_emails
  add column if not exists is_test boolean not null default false;

alter table public.ss_tickets
  add column if not exists is_test boolean not null default false;

comment on column public.ss_emails.is_test is
  'Testmail (Hämta testmail / admin-impersonation). Syns inte i skarpa Kundtjänst.';

comment on column public.ss_tickets.is_test is
  'Testärende från testchatt eller testmail. Flyttas till skarpt med befordra.';

update public.ss_emails
   set is_test = true
 where provider = 'mock'
   and is_test = false;

create index if not exists ss_emails_is_test_idx
  on public.ss_emails (tenant_id)
  where is_test;

create index if not exists ss_tickets_is_test_idx
  on public.ss_tickets (tenant_id)
  where is_test;
