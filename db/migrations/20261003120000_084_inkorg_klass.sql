-- 084: Inkorgens klass och brevlådans syfte (plan del D, Antons beställning 2026-10-01).
--
-- Jev (eller kodregler, eller standard) sorterar varje inkommande mejl i
-- support, lead eller ej relaterat INNAN triagen. Leads-kunder får en egen
-- inkorg under Iris som läser klass='lead'; kundtjänstinkorgen visar
-- support. Ett prospektsvar som landade i supportinkorgen fick tidigare ett
-- supportutkast.
--
-- klass:        support | lead | ej_relaterat (null = inte klassat än, äldre rader).
-- klass_kalla:  regel | jev | syfte | standard | manuell — vem som avgjorde,
--               så en manuell omklassning blir lärdata och Jev går att mäta.
-- syfte:        vad kundens brevlåda används till: support (default), leads, bada.
alter table public.ss_emails
  add column if not exists klass text
    check (klass is null or klass in ('support', 'lead', 'ej_relaterat')),
  add column if not exists klass_kalla text;

alter table public.ss_mailboxes
  add column if not exists syfte text not null default 'support'
    check (syfte in ('support', 'leads', 'bada'));

-- Två nya statusar: 'lead' (bor i leads-inkorgen, inget supportutkast) och
-- 'ej_relaterat' (dolt, syns under Dolda).
alter table public.ss_emails drop constraint if exists ss_emails_status_check;
alter table public.ss_emails add constraint ss_emails_status_check check (status in (
  'new', 'processing', 'awaiting_approval', 'auto_sent', 'sent',
  'escalated', 'rejected', 'taken_over', 'failed', 'att_hantera',
  'lead', 'ej_relaterat'
));

create index if not exists ss_emails_klass_idx on public.ss_emails (tenant_id, klass);

-- Ett nytt inkommande lead (avsändare utan prospekt) blir ett prospekt med
-- origin 'inkorg' — samma tabell, en ny härkomst (jfr migration 039/054).
alter table public.prospects drop constraint if exists prospects_origin_check;
alter table public.prospects add constraint prospects_origin_check
  check (origin in ('manual', 'example', 'import', 'test', 'inkorg')) not valid;
