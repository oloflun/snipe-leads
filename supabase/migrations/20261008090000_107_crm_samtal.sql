-- 107: CRM-flödet för leads (Antons beställning 2026-10-07). Idempotent.
--
-- 1. outreach_messages.created_at: tabellen hade ingen tidsstämpel, så varje
--    "senaste meddelandet" ordnades på slumpmässigt uuid. Lådan kunde visa ett
--    annat utkast än det som skickas. Befintliga rader får now(); nya rader
--    ordnas rätt, och en kasserad rad (nedan) väljs aldrig.
-- 2. outreach_messages.kasserad_at: ett avvisat eller ersatt utkast som aldrig
--    skickats. Det blev förut kvar som osänt och spärrade uppföljningar
--    (has_pending_item) och kunde väljas som "väntande" text.
-- 3. prospects.arkiverad_at: Arkivera i Iris-listan. Ett arkiverat lead är
--    dolt, behåller sin historik och står kvar i uteslutningsmängden.
-- 4. origin 'ring': bolag med bara telefon och namngiven VD (leadsregel 15)
--    blir prospekt på ringlistan, skilda från Iris-leads.
-- 5. lead_samtal: utfallet av varje samtal i ring- och återkopplingslistan
--    (leadsregel 17). Statusen på prospektet ändras av koden i samma anrop.
-- 6. snajp_app får radera prospekt (Ta bort, bara aldrig kontaktade leads, se
--    app/api/leads.py). Trådar, meddelanden, köposter och Suite-tabellerna
--    följer med via on delete cascade (010, 086).

alter table public.outreach_messages
  add column if not exists created_at timestamptz not null default now();
alter table public.outreach_messages
  add column if not exists kasserad_at timestamptz;
create index if not exists outreach_messages_trad_skapad_idx
  on public.outreach_messages (thread_id, created_at);

alter table public.prospects add column if not exists arkiverad_at timestamptz;

alter table public.prospects drop constraint if exists prospects_origin_check;
alter table public.prospects add constraint prospects_origin_check
  check (origin in ('manual', 'example', 'import', 'test', 'inkorg', 'lista', 'iris', 'ring')) not valid;

create table if not exists public.lead_samtal (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references public.ss_tenants(id) on delete cascade,
  prospect_id   uuid not null references public.prospects(id) on delete cascade,
  utfall        text not null check (utfall in ('ej_svar', 'aterkom', 'ej_intresserad', 'kontakta_inte', 'mote')),
  aterkom_datum date,
  anteckning    text,
  created_at    timestamptz not null default now()
);
create index if not exists lead_samtal_prospekt_idx
  on public.lead_samtal (tenant_id, prospect_id, created_at);

alter table public.lead_samtal enable row level security;
alter table public.lead_samtal force row level security;
drop policy if exists tenant_isolation on public.lead_samtal;
create policy tenant_isolation on public.lead_samtal
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert on table public.lead_samtal to snajp_app;
    grant delete on table public.prospects to snajp_app;
  end if;
end $$;
