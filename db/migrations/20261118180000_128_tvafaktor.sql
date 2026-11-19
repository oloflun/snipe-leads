-- 128: valfri tvåstegsverifiering (TOTP) för plattformsadmin (ISO 27001 A.8.5,
-- A.5.17; 2026-11-18).
--
-- Två tabeller, nådda BARA genom funktionerna nedan (security definer), som i
-- 125. Approllerna har ingen rättighet på tabellerna.
--
--   tvafaktor                      en rad per konto: TOTP-hemligheten
--                                  KRYPTERAD (AES-256-GCM, nyckeln härledd ur
--                                  AUTH_SECRET i webben, lib/auth/tvafaktor-krypto.ts),
--                                  om den är aktiverad, och senast använda
--                                  tidssteg (skydd mot återspelning).
--   tvafaktor_aterstallningskoder  engångskoder som HMAC-hashar, aldrig klartext.
--
-- Databasen ser aldrig hemligheten i klartext och kan därför inte pröva en
-- kod; det gör webben. Funktionerna håller det databasen kan hålla:
--   * inrullning bara för plattformsadmin, och bara den inloggades egen rad
--     (identiteten ur app.user_id, som sqlAsUser sätter);
--   * en kod per tidssteg och en återställningskod en gång (atomiskt);
--   * avaktivering bara av den inloggade, och bara inom två minuter efter en
--     godkänd kod (`senast_verifierad_at`), så att en session utan kod inte
--     kan stänga av skyddet.
--
-- Additiv och idempotent: kan köras om.

create table if not exists public.tvafaktor (
  user_id               uuid primary key references auth.users(id) on delete cascade,
  hemlighet             text        not null,
  aktiverad_at          timestamptz,
  senaste_steg          bigint,
  senast_verifierad_at  timestamptz,
  skapad_at             timestamptz not null default now(),
  uppdaterad_at         timestamptz not null default now()
);

comment on table public.tvafaktor is
  'Tvåstegsverifiering per konto (128). hemlighet är AES-256-GCM-krypterad i webben; '
  'aktiverad_at null = inrullningen är påbörjad men inte bekräftad.';

create table if not exists public.tvafaktor_aterstallningskoder (
  user_id    uuid        not null references auth.users(id) on delete cascade,
  kod_hash   text        not null,
  anvand_at  timestamptz,
  skapad_at  timestamptz not null default now(),
  primary key (user_id, kod_hash)
);

comment on table public.tvafaktor_aterstallningskoder is
  'Engångskoder för tvåstegsverifieringen (128), som HMAC-SHA256-hashar. Klartexten visas en gång vid inrullningen.';

alter table public.tvafaktor enable row level security;
alter table public.tvafaktor_aterstallningskoder enable row level security;

revoke all on table public.tvafaktor from public;
revoke all on table public.tvafaktor_aterstallningskoder from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    revoke all on table public.tvafaktor from snajp_web;
    revoke all on table public.tvafaktor_aterstallningskoder from snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    revoke all on table public.tvafaktor from snajp_app;
    revoke all on table public.tvafaktor_aterstallningskoder from snajp_app;
  end if;
end;
$$;

-- Läget för ett konto. Inloggningen har ingen identitet än, därför tar
-- funktionen kontots id. Hemligheten är krypterad; nyckeln finns bara i webben.
create or replace function public.tvafaktor_las(p_user_id uuid)
returns table (aktiv boolean, hemlighet text, senaste_steg bigint, koder_kvar integer)
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select t.aktiverad_at is not null,
         t.hemlighet,
         t.senaste_steg,
         (select count(*)::integer
            from public.tvafaktor_aterstallningskoder k
           where k.user_id = t.user_id and k.anvand_at is null)
    from public.tvafaktor t
   where t.user_id = p_user_id
$$;

-- Påbörja inrullningen: spara en ny (krypterad) hemlighet, inte aktiverad.
-- Bara plattformsadmin, bara den egna raden, och aldrig över en aktiv rad.
create or replace function public.tvafaktor_paborja(p_hemlighet text)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := nullif(current_setting('app.user_id', true), '')::uuid;
begin
  if v_uid is null then
    return false;
  end if;
  if not exists (select 1 from public.platform_admins where user_id = v_uid) then
    return false;
  end if;
  if p_hemlighet is null or length(p_hemlighet) < 20 or length(p_hemlighet) > 500 then
    raise exception 'ogiltig hemlighet';
  end if;

  insert into public.tvafaktor as t (user_id, hemlighet)
  values (v_uid, p_hemlighet)
  on conflict (user_id) do update set
    hemlighet = excluded.hemlighet,
    senaste_steg = null,
    senast_verifierad_at = null,
    uppdaterad_at = now()
  where t.aktiverad_at is null;

  return found;
end;
$$;

-- Bekräfta inrullningen. Webben har prövat koden mot den påbörjade hemligheten;
-- här aktiveras raden, steget förbrukas och återställningskoderna byts.
create or replace function public.tvafaktor_aktivera(p_steg bigint, p_kodhashar text[])
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := nullif(current_setting('app.user_id', true), '')::uuid;
begin
  if v_uid is null then
    return false;
  end if;
  if p_steg is null
     or p_kodhashar is null
     or cardinality(p_kodhashar) < 1
     or cardinality(p_kodhashar) > 20
     or exists (select 1 from unnest(p_kodhashar) h where h is null or h !~ '^[0-9a-f]{64}$') then
    raise exception 'ogiltiga argument';
  end if;

  update public.tvafaktor
     set aktiverad_at = now(),
         senaste_steg = p_steg,
         senast_verifierad_at = now(),
         uppdaterad_at = now()
   where user_id = v_uid
     and aktiverad_at is null;
  if not found then
    return false;
  end if;

  delete from public.tvafaktor_aterstallningskoder where user_id = v_uid;
  insert into public.tvafaktor_aterstallningskoder (user_id, kod_hash)
  select v_uid, h from unnest(p_kodhashar) h
  on conflict do nothing;
  return true;
end;
$$;

-- Förbruka ett tidssteg. Svarar true bara om steget är nyare än det senast
-- använda: samma kod två gånger godtas inte (återspelning), också om två
-- inloggningar med samma kod kommer samtidigt (raden låses av uppdateringen).
create or replace function public.tvafaktor_anvand_steg(p_user_id uuid, p_steg bigint)
returns boolean
language sql
security definer
set search_path = public, pg_temp
as $$
  with u as (
    update public.tvafaktor
       set senaste_steg = p_steg,
           senast_verifierad_at = now(),
           uppdaterad_at = now()
     where user_id = p_user_id
       and aktiverad_at is not null
       and (senaste_steg is null or senaste_steg < p_steg)
    returning 1
  )
  select exists (select 1 from u)
$$;

-- Förbruka en återställningskod (en gång).
create or replace function public.tvafaktor_anvand_aterstallningskod(p_user_id uuid, p_kod_hash text)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  update public.tvafaktor_aterstallningskoder k
     set anvand_at = now()
   where k.user_id = p_user_id
     and k.kod_hash = p_kod_hash
     and k.anvand_at is null
     and exists (select 1 from public.tvafaktor t where t.user_id = p_user_id and t.aktiverad_at is not null);
  if not found then
    return false;
  end if;
  update public.tvafaktor
     set senast_verifierad_at = now(), uppdaterad_at = now()
   where user_id = p_user_id;
  return true;
end;
$$;

-- Avaktivera: bara den inloggades egen rad, och bara inom två minuter efter
-- en godkänd kod (webben förbrukar koden med funktionerna ovan först).
create or replace function public.tvafaktor_avaktivera()
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := nullif(current_setting('app.user_id', true), '')::uuid;
begin
  if v_uid is null then
    return false;
  end if;
  delete from public.tvafaktor
   where user_id = v_uid
     and (aktiverad_at is null
          or senast_verifierad_at > now() - interval '2 minutes');
  if not found then
    return false;
  end if;
  delete from public.tvafaktor_aterstallningskoder where user_id = v_uid;
  return true;
end;
$$;

revoke all on function public.tvafaktor_las(uuid) from public;
revoke all on function public.tvafaktor_paborja(text) from public;
revoke all on function public.tvafaktor_aktivera(bigint, text[]) from public;
revoke all on function public.tvafaktor_anvand_steg(uuid, bigint) from public;
revoke all on function public.tvafaktor_anvand_aterstallningskod(uuid, text) from public;
revoke all on function public.tvafaktor_avaktivera() from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.tvafaktor_las(uuid) to snajp_web;
    grant execute on function public.tvafaktor_paborja(text) to snajp_web;
    grant execute on function public.tvafaktor_aktivera(bigint, text[]) to snajp_web;
    grant execute on function public.tvafaktor_anvand_steg(uuid, bigint) to snajp_web;
    grant execute on function public.tvafaktor_anvand_aterstallningskod(uuid, text) to snajp_web;
    grant execute on function public.tvafaktor_avaktivera() to snajp_web;
  end if;
end;
$$;
