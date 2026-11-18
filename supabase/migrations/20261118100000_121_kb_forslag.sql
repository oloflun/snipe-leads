-- 121: webbplatsskanningen sparar sitt utfall, så att den kan startas av
-- onboardingen och följas efteråt.
--
-- ## Varför
--
-- Skanningen av kundens egen webbplats (snajp-support/app/kb_skanning.py)
-- fanns, men sparade ingenting: utkasten låg i jobbsvaret i Redis, som går ut,
-- och inget i gränssnittet startade den. Kunskapsbasen var därför tom efter
-- onboardingen trots att guiden lovar att agenterna läser sajten (Antons
-- beställning 2026-11-18: skanningen startas automatiskt och kompletterar,
-- skriver inte över, kundens egna uppgifter).
--
-- ## Vad tabellerna bär
--
-- `ss_kb_skanningar`: en rad per skanning, med läge och utfall. Den är
-- förloppet kunden ser, och den finns kvar efter en omladdning (Antons regel
-- 2026-10-10 om att varje funktion ska gå att följa).
--
-- `ss_kb_forslag`: artikelutkasten. De blir artiklar först när kunden lägger
-- till dem, och då genom en INSERT i ss_knowledge_base, aldrig en UPDATE.
-- Kundens egna artiklar rörs alltså aldrig. Ett utkast som redan finns i
-- basen, eller som kunden redan har avvisat, sparas inte igen.
--
-- Additiv och idempotent. Radskyddet är samma som ss_sending_domains (061),
-- med 028:s vakt mot tom sträng.

create table if not exists public.ss_kb_skanningar (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references public.ss_tenants(id) on delete cascade,
  webbplats     text not null,
  status        text not null default 'pagar'
                check (status in ('pagar', 'klar', 'fel')),
  -- Vem som startade den: 'onboarding' eller 'kund' (knappen i Kunskapsbas).
  startad_av    text not null default 'kund',
  sidor         integer,
  lasbara_sidor integer,
  forslag       integer not null default 0,
  -- Utkast som inte sparades: de fanns redan i basen eller var avvisade.
  redan_fanns   integer not null default 0,
  fel           text,
  startad_at    timestamptz not null default now(),
  klar_at       timestamptz
);

create index if not exists ss_kb_skanningar_tenant_idx
  on public.ss_kb_skanningar (tenant_id, startad_at desc);

create table if not exists public.ss_kb_forslag (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references public.ss_tenants(id) on delete cascade,
  skanning_id  uuid references public.ss_kb_skanningar(id) on delete cascade,
  title        text not null,
  content      text not null,
  category     text not null,
  source_url   text,
  confidence   real,
  varningar    jsonb not null default '[]'::jsonb,
  status       text not null default 'vantar'
               check (status in ('vantar', 'tillagd', 'avvisad')),
  -- Artikeln utkastet blev, när kunden lade till det.
  artikel_id   uuid,
  created_at   timestamptz not null default now(),
  beslutad_at  timestamptz
);

create index if not exists ss_kb_forslag_tenant_idx
  on public.ss_kb_forslag (tenant_id, status, created_at);

comment on table public.ss_kb_skanningar is
  'En rad per skanning av kundens egen webbplats: läge, antal sidor och utfall. Migration 121.';
comment on table public.ss_kb_forslag is
  'Artikelutkast ur webbplatsskanningen. Blir artiklar bara när kunden lägger till dem. Migration 121.';

alter table public.ss_kb_skanningar enable row level security;
alter table public.ss_kb_forslag enable row level security;

drop policy if exists kb_skanningar_tenant on public.ss_kb_skanningar;
create policy kb_skanningar_tenant on public.ss_kb_skanningar
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

drop policy if exists kb_forslag_tenant on public.ss_kb_forslag;
create policy kb_forslag_tenant on public.ss_kb_forslag
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on table public.ss_kb_skanningar, public.ss_kb_forslag to snajp_app;
  end if;
end $$;
