-- 162: Snajp CRM, händelseloggen och webhooks ut.
--
-- Fram till nu kunde den som ville hålla en kopia i fas bara fråga
-- "vad har ändrats sedan sist" per objekt (updated_since), och CRM:et kunde
-- inte säga till när något hänt. Tre saker byggs på en och samma logg:
--
-- 1. crm_handelser: en rad per skrivning (skapad, ändrad, raderad,
--    återställd, tömd). Den bär VILKA fält som ändrades, aldrig värdena: en
--    logg som överlever en radering får inte bli ett register över det som
--    raderades. Ändringsflödet (GET /api/crm/v1/changes) läser den i
--    löpnummerordning, och postens tidslinje läser den per post.
-- 2. crm_webhooks: adresser kunden vill ha händelserna skickade till, med en
--    hemlighet som signerar varje anrop. Hemligheten lagras Fernet-krypterad
--    (app/integrationer/hemligheter.py), aldrig i klartext.
-- 3. crm_webhook_leveranser: kön och leveransloggen. Varje försök står kvar
--    med statuskod och fel, så att kunden kan se varför något inte kom fram
--    och skicka om det. Omförsök med växande väntetid i app/crm/webhooks.py.
--
-- Radskydd som de övriga CRM-tabellerna (160). Leveransjobbet läser därför
-- alltid per kund, aldrig tvärs över kunder.
--
-- Additiv och idempotent.

create table if not exists public.crm_handelser (
  id          bigint generated always as identity primary key,
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  objekt      text not null,
  post_id     uuid not null,
  typ         text not null,
  falt        jsonb not null default '[]'::jsonb,
  kalla       text not null default 'api',
  aktor       text,
  created_at  timestamptz not null default now()
);

alter table public.crm_handelser drop constraint if exists crm_handelser_typ_check;
alter table public.crm_handelser add constraint crm_handelser_typ_check
  check (typ in ('skapad', 'andrad', 'raderad', 'aterstalld', 'tomd'));

-- Ändringsflödet läser i den här ordningen, tidslinjen i den andra.
create index if not exists crm_handelser_flode_idx on public.crm_handelser (tenant_id, id);
create index if not exists crm_handelser_post_idx on public.crm_handelser (tenant_id, objekt, post_id, id desc);

create table if not exists public.crm_webhooks (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references public.ss_tenants(id) on delete cascade,
  url           text not null,
  beskrivning   text,
  handelser     jsonb not null default '["*"]'::jsonb,
  hemlighet     text not null,
  aktiv         boolean not null default true,
  fel_i_rad     integer not null default 0,
  senast_ok_at  timestamptz,
  senast_fel_at timestamptz,
  senast_fel    text,
  avstangd_av   text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists crm_webhooks_tenant_idx on public.crm_webhooks (tenant_id, created_at);

create table if not exists public.crm_webhook_leveranser (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references public.ss_tenants(id) on delete cascade,
  webhook_id       uuid not null references public.crm_webhooks(id) on delete cascade,
  handelsetyp      text not null,
  kropp            jsonb not null,
  status           text not null default 'vantar',
  forsok           integer not null default 0,
  nasta_forsok_at  timestamptz not null default now(),
  statuskod        integer,
  fel              text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  levererad_at     timestamptz
);

alter table public.crm_webhook_leveranser drop constraint if exists crm_webhook_leveranser_status_check;
alter table public.crm_webhook_leveranser add constraint crm_webhook_leveranser_status_check
  check (status in ('vantar', 'levererad', 'misslyckad'));

create index if not exists crm_webhook_leveranser_ko_idx
  on public.crm_webhook_leveranser (tenant_id, nasta_forsok_at) where status = 'vantar';
create index if not exists crm_webhook_leveranser_logg_idx
  on public.crm_webhook_leveranser (tenant_id, webhook_id, created_at desc);

do $$
declare
  t text;
begin
  foreach t in array array['crm_handelser', 'crm_webhooks', 'crm_webhook_leveranser']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    execute format('drop policy if exists tenant_isolation on public.%I', t);
    execute format(
      'create policy tenant_isolation on public.%I
         using (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)
         with check (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)', t);
    if exists (select 1 from pg_roles where rolname = 'snajp_app') then
      execute format('grant select, insert, update, delete on table public.%I to snajp_app', t);
    end if;
  end loop;
end $$;

comment on table public.crm_handelser is
  'Snajp CRM: en rad per skrivning (migration 162). Bär vilka fält som ändrades, aldrig '
  'värdena. Läses av ändringsflödet och av postens tidslinje.';
comment on table public.crm_webhooks is
  'Snajp CRM: adresser som får händelserna skickade till sig (migration 162). hemlighet '
  'är Fernet-krypterad.';
comment on table public.crm_webhook_leveranser is
  'Snajp CRM: kön och loggen över webhook-leveranser (migration 162). kropp är det som '
  'skickas; raderna gallras efter 30 dagar av leveransjobbet.';
