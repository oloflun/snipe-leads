-- 156: plattformsärendena, kundernas felrapporter till Snajp ur Hjälprutan.
--
-- ## Varför
--
-- Antons beställning 2026-11-25 (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 5):
-- en felrapport ur Hjälprutan blir ett ärende med ett nummer och ett förlopp
-- som finns kvar efter en omladdning och på andra enheter. Förloppet låg
-- tidigare ingenstans: agentens eskalering tystar chatten och jobbminnet lever
-- en timme.
--
-- ## Vad tabellerna bär
--
-- `plattformsarenden`: en rad per rapport. Rapportör, arbetsyta, kund, vy,
-- roll och om det var en besökande plattformsadmin sätts av Next-servern ur
-- sessionen, aldrig ur klientens kropp. `sida` är bara sökvägen.
--
-- `plattformsarende_handelser`: varje statusbyte, kundens svar och utslag.
-- `synlig_for_kund` skiljer det kunden ser från Snajps interna anteckningar.
--
-- ## Radskydd
--
-- Tabellerna har ingen tenant_id: ärendena är Snajps egna, om plattformen, och
-- inte en kunds data i en kunds tenant. Därför samma villkor som adminytans
-- läsningar (029) och tenant-skapningen: snajp_app når raderna BARA utan
-- tenant-kontext. Varje kundskopad anslutning (_scoped i postgres.py) ser
-- alltså ingenting, och webbens roll har ingen rätt alls: Next når ärendena
-- bara genom backendens vägar, under hjälpens nyckel eller master-nyckeln.
-- Ingen radering: ärendena gallras inte av appen.
--
-- Additiv och idempotent: kan köras om.

create table if not exists public.plattformsarenden (
  id                 uuid primary key default gen_random_uuid(),
  -- "F-" och fyra tecken ur ett alfabet utan förväxlingsbara tecken
  -- (app/storage/base.ARENDENUMMER_ALFABET).
  nummer             text not null,
  status             text not null default 'mottagen',
  rapportor_user_id  uuid not null,
  rapportor_namn     text,
  kund_workspace_id  uuid not null,
  kund_tenant_slug   text not null,
  vy                 text not null,
  roll               text not null,
  besok_av_admin     boolean not null default false,
  sida               text not null check (length(sida) <= 300),
  gjorde             text not null,
  hande              text not null,
  vantade            text not null default '',
  -- Data-URL, samma tak som chattens bilagor (~6 MB tecken).
  bild               text,
  testversion_url    text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'plattformsarenden_status_check') then
    alter table public.plattformsarenden
      add constraint plattformsarenden_status_check
      check (status in ('mottagen', 'undersoks', 'rattning_pagar', 'redo_att_testa',
                        'kund_godkand', 'i_development', 'i_main', 'behover_mer', 'stangd'));
  end if;
end;
$$;

create unique index if not exists plattformsarenden_nummer_idx
  on public.plattformsarenden (nummer);
create index if not exists plattformsarenden_rapportor_idx
  on public.plattformsarenden (rapportor_user_id, created_at desc);
create index if not exists plattformsarenden_status_idx
  on public.plattformsarenden (status);

create table if not exists public.plattformsarende_handelser (
  id               uuid primary key default gen_random_uuid(),
  arende_id        uuid not null references public.plattformsarenden(id) on delete cascade,
  tid              timestamptz not null default now(),
  -- skapad, status, kundsvar, utslag
  typ              text not null,
  status           text,
  meddelande       text,
  synlig_for_kund  boolean not null default false,
  -- kund, plattformsadmin eller admin:<uuid>
  aktor            text not null
);

create index if not exists plattformsarende_handelser_arende_idx
  on public.plattformsarende_handelser (arende_id, tid);

comment on table public.plattformsarenden is
  'Kundernas felrapporter ur Hjälprutan, med nummer och läge. Ingen tenant_id: Snajps egna ärenden. Migration 156.';
comment on table public.plattformsarende_handelser is
  'Förloppet för ett plattformsärende. synlig_for_kund styr vad kunden ser. Migration 156.';

alter table public.plattformsarenden enable row level security;
alter table public.plattformsarende_handelser enable row level security;

drop policy if exists plattformsarenden_backend on public.plattformsarenden;
create policy plattformsarenden_backend on public.plattformsarenden
  for all to snajp_app
  using (nullif(current_setting('app.tenant_id', true), '') is null)
  with check (nullif(current_setting('app.tenant_id', true), '') is null);

drop policy if exists plattformsarende_handelser_backend on public.plattformsarende_handelser;
create policy plattformsarende_handelser_backend on public.plattformsarende_handelser
  for all to snajp_app
  using (nullif(current_setting('app.tenant_id', true), '') is null)
  with check (nullif(current_setting('app.tenant_id', true), '') is null);

revoke all on table public.plattformsarenden from public;
revoke all on table public.plattformsarende_handelser from public;

do $$
begin
  -- Standardrättigheterna i schemat (030) hade annars gett webbens roll full
  -- rätt på de nya tabellerna.
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    revoke all on table public.plattformsarenden from snajp_web;
    revoke all on table public.plattformsarende_handelser from snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    revoke delete, truncate on table public.plattformsarenden from snajp_app;
    revoke delete, truncate on table public.plattformsarende_handelser from snajp_app;
    grant select, insert, update on table public.plattformsarenden to snajp_app;
    grant select, insert on table public.plattformsarende_handelser to snajp_app;
  end if;
end;
$$;
