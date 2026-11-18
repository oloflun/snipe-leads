-- 080: Körningens tillstånd i liggaren (INV-JOB-003).
--
-- ## Felet
--
-- Iris-motorns tillstånd (`korning`: mål, levererade, undersökta, tratt,
-- slutorsak) bodde BARA i jobbstoret (app/jobs/store.py, Redis, TTL 3 600 s)
-- och i LeadsRunForm.tsx:s React-state. Anton startade en körning 2026-09-30
-- som inte hann bli klar; när han kom tillbaka fanns inget spår av den: inga
-- nya leads, ingen felorsak, ingen lista över körningar. Liggaren (059) hade
-- batchraden, men den sattes till 'completed' i samma ögonblick som motorn
-- STARTADE (sökjobbet var "klart"), och bar varken tillstånd eller fel.
--
-- ## Lösningen
--
-- Samma princip som 059 utvidgad från statusen till tillståndet: liggaren
-- är sanningen, Redis är snabbvägen. Varje steg i motorn skriver `korning`
-- hit, varje fel skriver `error` i klartext, och batchraden står i
-- 'processing' tills motorn säger `klar`. GET /api/leads/korningar läser
-- härifrån, så en körning går att följa, lämna och återvända till, och en
-- körning som dog säger varför.
alter table public.leads_job_ledger
  add column if not exists korning    jsonb,
  add column if not exists error      text,
  add column if not exists is_test    boolean not null default false,
  add column if not exists updated_at timestamptz not null default now();

comment on column public.leads_job_ledger.korning is
  'Iris-motorns tillstånd (app/leads/korning.py) för batchraden, skrivet vid '
  'varje steg. Null för prospektjobb och för batchar med egna bolagsnamn.';
comment on column public.leads_job_ledger.error is
  'Felorsaken i klartext när status = failed. Kunden ser den i Körningar.';

-- Körningslistan: tenantens batch- och listrader, nyast först.
create index if not exists leads_job_ledger_korningar_idx
  on public.leads_job_ledger (tenant_id, created_at desc)
  where scope in ('batch', 'lista');
