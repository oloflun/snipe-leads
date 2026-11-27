-- 166: Snajp CRM, en gemensam spärr för alla kanaler.
--
-- Antons beslut 2026-11-27 (docs/crm/SVENSK-STANDARD.md § 4, enligt
-- förslaget). Rätten att invända mot direktmarknadsföring (GDPR art. 21.2-3)
-- gäller i varje system, och IMY:s beslut mot H&M 2023 visar att en invändning
-- som inte når alla system är ett fel (docs/crm/underlag/svensk-02 § 3.2 och
-- § 6.3). I dag finns tre spärrar som inte känner till varandra:
-- suppressions (avregistrerade e-postadresser), leadets status suppressed
-- (ringlistans kontakta inte) och kontakta_inte på CRM:ets bolag och personer.
--
-- crm_sparrar är den fjärde källan och den enda som bär kanal, orsak och
-- datum. Grinden app/crm/sparr.py: ar_sparrad läser alla fyra tillsammans;
-- ingenting kopieras mellan dem.
--
-- kanal   mejl, telefon eller alla.
-- slag    epost, telefon, doman eller orgnr. Värdet är normaliserat: e-post
--         och domän i gemener, telefon i E.164 (app/crm/falt.py: telefon) och
--         organisationsnummer som tio siffror. En enskild firmas nummer är
--         ett personnummer och tas inte emot (beslut 2026-11-23).
-- orsak   invandning (art. 21), avregistrering, nix, kunden_bad, studs, annat.
-- kalla   vilken väg spärren kom in: app, api, utfall, import, synk.
-- havd_at En hävd spärr står kvar som bevis på att den funnits, men gäller
--         inte. Det unika indexet gäller därför bara de ohävda.
--
-- anteckning är fritext (högst 500 tecken) och skrivs aldrig i en logg, en
-- händelse eller en webhook. Händelserna sparr.skapad och sparr.havd bär id,
-- kanal, slag och orsak, aldrig värdet (app/crm/handelser.py).
--
-- Radskydd som de övriga CRM-tabellerna (160, 162, 164). Additiv och idempotent.

create table if not exists public.crm_sparrar (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  kanal       text not null,
  slag        text not null,
  varde       text not null,
  orsak       text not null default 'annat',
  anteckning  text,
  kalla       text not null default 'app',
  bolag_id    uuid references public.crm_bolag(id) on delete set null,
  person_id   uuid references public.crm_personer(id) on delete set null,
  created_at  timestamptz not null default now(),
  havd_at     timestamptz,
  havd_av     text
);

alter table public.crm_sparrar drop constraint if exists crm_sparrar_kanal_check;
alter table public.crm_sparrar add constraint crm_sparrar_kanal_check
  check (kanal in ('mejl', 'telefon', 'alla'));
alter table public.crm_sparrar drop constraint if exists crm_sparrar_slag_check;
alter table public.crm_sparrar add constraint crm_sparrar_slag_check
  check (slag in ('epost', 'telefon', 'doman', 'orgnr'));
alter table public.crm_sparrar drop constraint if exists crm_sparrar_orsak_check;
alter table public.crm_sparrar add constraint crm_sparrar_orsak_check
  check (orsak in ('invandning', 'avregistrering', 'nix', 'kunden_bad', 'studs', 'annat'));
alter table public.crm_sparrar drop constraint if exists crm_sparrar_kalla_check;
alter table public.crm_sparrar add constraint crm_sparrar_kalla_check
  check (kalla in ('app', 'api', 'utfall', 'import', 'synk'));
alter table public.crm_sparrar drop constraint if exists crm_sparrar_anteckning_check;
alter table public.crm_sparrar add constraint crm_sparrar_anteckning_check
  check (anteckning is null or length(anteckning) <= 500);
-- Organisationsnumret som tio siffror, aldrig med bindestreck eller sekel.
alter table public.crm_sparrar drop constraint if exists crm_sparrar_orgnr_check;
alter table public.crm_sparrar add constraint crm_sparrar_orgnr_check
  check (slag <> 'orgnr' or varde ~ '^[0-9]{10}$');

-- En spärr per kanal, slag och värde bland de som gäller.
create unique index if not exists crm_sparrar_uq
  on public.crm_sparrar (tenant_id, kanal, slag, varde)
  where havd_at is null;
-- Grinden slår upp på värdet, listan går senast lagd först.
create index if not exists crm_sparrar_varde_idx on public.crm_sparrar (tenant_id, varde)
  where havd_at is null;
create index if not exists crm_sparrar_lista_idx on public.crm_sparrar (tenant_id, created_at desc, id desc);

-- Händelseloggen (162) får typen havd: en spärr hävs, den raderas inte.
alter table public.crm_handelser drop constraint if exists crm_handelser_typ_check;
alter table public.crm_handelser add constraint crm_handelser_typ_check
  check (typ in ('skapad', 'andrad', 'raderad', 'aterstalld', 'tomd', 'havd'));

do $$
begin
  execute 'alter table public.crm_sparrar enable row level security';
  execute 'alter table public.crm_sparrar force row level security';
  execute 'drop policy if exists tenant_isolation on public.crm_sparrar';
  execute 'create policy tenant_isolation on public.crm_sparrar
             using (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)
             with check (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)';
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    execute 'grant select, insert, update, delete on table public.crm_sparrar to snajp_app';
  end if;
end $$;

comment on table public.crm_sparrar is
  'Snajp CRM: den gemensamma spärren för mejl, telefon och alla kanaler (migration 166). '
  'Läses tillsammans med suppressions, leadets status suppressed och kontakta_inte av '
  'app/crm/sparr.py: ar_sparrad. En hävd spärr (havd_at) står kvar men gäller inte.';
comment on column public.crm_sparrar.anteckning is
  'Fritext, högst 500 tecken. Skrivs aldrig i en logg, en händelse eller en webhook.';
