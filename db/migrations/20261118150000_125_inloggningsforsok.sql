-- 125: spärr mot upprepade inloggningsförsök och återställningsbegäranden
-- (ISO 27001 A.8.5, 2026-11-18).
--
-- Webben räknar misslyckade lösenordsinloggningar och begäranden om
-- lösenordsåterställning per e-postadress och per IP. Når en nyckel sin tröskel
-- inom fönstret spärras den en stund, och spärren blir längre för varje ny
-- spärr samma dygn: 1, 5, 15 och sedan 60 minuter. Reglerna (trösklar och
-- fönster) står i lib/auth/inloggningsregler.ts; den här filen räknar och spärrar.
--
-- Nyckeln är en HMAC av adressen eller IP:t (lib/auth/inloggningsforsok.ts),
-- aldrig klartext. Den räknas likadant för en adress med och utan konto, så att
-- spärren inte avslöjar vilka adresser som finns.
--
-- Tabellen nås BARA genom funktionerna nedan (security definer). Approllerna
-- har ingen rättighet på själva tabellen: varken webben eller api:t ska kunna
-- läsa vilka nycklar som är spärrade eller nollställa någon annans räknare
-- förbi reglerna.
--
-- Additiv och idempotent: kan köras om.

create table if not exists public.inloggningsforsok (
  nyckel          text primary key,
  forsok          integer     not null default 0,
  fonster_borjan  timestamptz not null default now(),
  sparrad_till    timestamptz,
  sparrniva       integer     not null default 0,
  senast          timestamptz not null default now()
);

comment on table public.inloggningsforsok is
  'Spärren mot upprepade inloggningsförsök (125). Nyckeln är handling:omfång:HMAC, '
  'aldrig en adress eller ett IP i klartext. Rader utan aktiv spärr gallras efter ett dygn.';

create index if not exists inloggningsforsok_senast_idx on public.inloggningsforsok (senast);

alter table public.inloggningsforsok enable row level security;

-- Inga policyer: tabellen nås bara genom funktionerna. Standardrättigheterna i
-- schemat (030) hade annars gett snajp_web full rätt på den nya tabellen.
revoke all on table public.inloggningsforsok from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    revoke all on table public.inloggningsforsok from snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    revoke all on table public.inloggningsforsok from snajp_app;
  end if;
end;
$$;

-- Spärrnivå → väntetid. Nivån räknas från noll varje dygn utan försök.
create or replace function public.inloggningsforsok_vantetid(p_niva integer)
returns interval
language sql
immutable
as $$
  select case
    when p_niva <= 0 then interval '1 minute'
    when p_niva = 1 then interval '5 minutes'
    when p_niva = 2 then interval '15 minutes'
    else interval '60 minutes'
  end
$$;

-- Är någon av nycklarna spärrad just nu? Svarar med den senaste spärrtiden,
-- eller null.
create or replace function public.inloggningsforsok_sparrad(p_nycklar text[])
returns timestamptz
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select max(sparrad_till)
    from public.inloggningsforsok
   where nyckel = any(p_nycklar)
     and sparrad_till > now()
$$;

-- Registrera ett försök på en nyckel. Svarar med spärrtiden om försöket fick
-- nyckeln att spärras, annars null. Raden låses av upserten, så två samtidiga
-- försök räknas båda.
create or replace function public.inloggningsforsok_registrera(
  p_nyckel    text,
  p_troskel   integer,
  p_fonster_s integer
)
returns timestamptz
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_fonster interval := make_interval(secs => greatest(p_fonster_s, 1));
  v_rad     public.inloggningsforsok;
begin
  if p_nyckel is null or length(p_nyckel) = 0 or length(p_nyckel) > 200 then
    raise exception 'ogiltig nyckel';
  end if;
  if p_troskel is null or p_troskel < 1 then
    raise exception 'ogiltig tröskel';
  end if;

  insert into public.inloggningsforsok as a (nyckel, forsok, fonster_borjan, senast)
  values (p_nyckel, 1, now(), now())
  on conflict (nyckel) do update set
    -- Ett dygn utan försök: börja om från nivå noll.
    sparrniva = case when a.senast < now() - interval '24 hours' then 0 else a.sparrniva end,
    forsok = case when a.fonster_borjan < now() - v_fonster then 1 else a.forsok + 1 end,
    fonster_borjan = case when a.fonster_borjan < now() - v_fonster then now() else a.fonster_borjan end,
    senast = now()
  returning * into v_rad;

  if v_rad.forsok >= p_troskel then
    update public.inloggningsforsok
       set sparrad_till   = now() + public.inloggningsforsok_vantetid(sparrniva),
           sparrniva      = sparrniva + 1,
           forsok         = 0,
           fonster_borjan = now()
     where nyckel = p_nyckel
    returning * into v_rad;
    return v_rad.sparrad_till;
  end if;

  -- Gallring i förbigående: rader utan aktiv spärr och utan försök på ett dygn.
  delete from public.inloggningsforsok
   where senast < now() - interval '24 hours'
     and (sparrad_till is null or sparrad_till < now());

  return null;
end;
$$;

-- En lyckad inloggning nollställer adressens räknare (inte IP:ts).
create or replace function public.inloggningsforsok_nollstall(p_nyckel text)
returns void
language sql
security definer
set search_path = public, pg_temp
as $$
  delete from public.inloggningsforsok where nyckel = p_nyckel
$$;

revoke all on function public.inloggningsforsok_sparrad(text[]) from public;
revoke all on function public.inloggningsforsok_registrera(text, integer, integer) from public;
revoke all on function public.inloggningsforsok_nollstall(text) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.inloggningsforsok_sparrad(text[]) to snajp_web;
    grant execute on function public.inloggningsforsok_registrera(text, integer, integer) to snajp_web;
    grant execute on function public.inloggningsforsok_nollstall(text) to snajp_web;
  end if;
end;
$$;
