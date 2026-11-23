-- 149: Iris-konversationer (Antons beställning 2026-11-22).
--
-- Kunderna köper i första hand de nya konversationerna, men svaren låg som
-- filtret "Svarat" under Inkorg › Skickat, svarsutkasten syntes ingenstans och
-- kasserades tyst när nästa svar kom (Telecom Buddy, main 2026-11-22). Leads
-- får en egen flik för konversationerna (components/leads/Konversationer.tsx,
-- app/api/leads_konversationer.py). Två saker saknades i schemat:
--
-- 1. lead_handelser: händelseloggen per tråd. Ett nytt svar, ett nytt
--    svarsutkast, ett kasserat eller återställt utkast, ett stegbyte (Möte
--    bokat, Återkom, Ej intresserad, Kontakta inte), ett mejl skickat utanför
--    Snajp och ett samtal. `notis` märker händelserna som också är notiser i
--    Snajp (nytt svar, nytt utkast, möte bokat, Iris lämnar över); `last_at`
--    är när någon i arbetsytan läst notisen. Läsmarkeringen gäller arbetsytan,
--    inte den enskilda användaren: konversationerna är en delad inkorg, och
--    den som öppnat svaret har tagit det (docs/BESLUT.md 2026-11-22).
--    `detalj` bär id:n, klass och steg, aldrig svarstexten, utom för ett mejl
--    som skickats utanför Snajp och lagts in för hand (`extern`): då finns
--    texten ingen annanstans. Samtalen står kvar i lead_samtal och
--    visas i tråden därifrån. Raderna kaskaderar från prospektet
--    (scripts/gdpr_radera.py: KASKAD).
-- 2. outreach_threads.aterkom_datum och .steg: steget Återkom med datum, och
--    det steg en människa senast valt. Möte, Ej intresserad och Kontakta inte
--    bor kvar i prospects.status (meeting, lost, suppressed), så att Skickat,
--    samtalslistorna och mätningen läser samma sanning som konversationerna.
--    `steg` behövs för det statusen inte skiljer: Svarat mot Återkom (båda
--    'replied'). Ett nytt svar nollar det, så att Iris klassning gäller igen
--    (app/leads/konversation.py: steg).
--
-- Spegeln: tabellen synkas main → development som de andra leadstabellerna
-- (scripts/railway_synk.py: SYNK), med synk_andrad_at och raderingsloggen
-- (111) och läsrätt för synkens roll (122).
--
-- Additiv och idempotent.

alter table public.outreach_threads add column if not exists aterkom_datum date;
alter table public.outreach_threads add column if not exists steg text;
alter table public.outreach_threads drop constraint if exists outreach_threads_steg_check;
alter table public.outreach_threads add constraint outreach_threads_steg_check
  check (steg is null or steg in ('svarat', 'aterkom', 'mote', 'ej_intresserad', 'kontakta_inte'));

create table if not exists public.lead_handelser (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  prospect_id uuid not null references public.prospects(id) on delete cascade,
  thread_id   uuid references public.outreach_threads(id) on delete cascade,
  typ         text not null check (typ in (
                'svar', 'klassad', 'utkast', 'utkast_ersatt', 'utkast_kasserat',
                'utkast_aterstallt', 'utkast_redigerat', 'generering_startad',
                'generering_fel', 'skickat', 'steg', 'mote', 'overlamnat',
                'extern')),
  kalla       text not null default 'kod' check (kalla in ('kod', 'manuell')),
  detalj      jsonb not null default '{}'::jsonb,
  notis       boolean not null default false,
  last_at     timestamptz,
  created_at  timestamptz not null default now()
);

create index if not exists lead_handelser_trad_idx
  on public.lead_handelser (tenant_id, thread_id, created_at);
create index if not exists lead_handelser_notis_idx
  on public.lead_handelser (tenant_id, created_at desc) where notis;
create index if not exists lead_handelser_olast_idx
  on public.lead_handelser (tenant_id) where notis and last_at is null;

alter table public.lead_handelser enable row level security;
alter table public.lead_handelser force row level security;
drop policy if exists tenant_isolation on public.lead_handelser;
create policy tenant_isolation on public.lead_handelser
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on table public.lead_handelser to snajp_app;
  end if;
  if exists (select 1 from pg_roles where rolname = 'synk_las') then
    grant select on table public.lead_handelser to synk_las;
  end if;
end $$;

-- Synken (111): ändringstid och raderingslogg, som de andra synkade tabellerna.
alter table public.lead_handelser
  add column if not exists synk_andrad_at timestamptz not null default now();
drop trigger if exists synk_markera on public.lead_handelser;
create trigger synk_markera before insert or update on public.lead_handelser
  for each row execute function public.synk_markera();
drop trigger if exists synk_radera on public.lead_handelser;
create trigger synk_radera after delete on public.lead_handelser
  for each row execute function public.synk_radera('id');

comment on table public.lead_handelser is
  'Händelseloggen per konversation och notiserna i Leads (migration 149). '
  'Skrivs av app/leads/konversation.py, läses av app/api/leads_konversationer.py.';
