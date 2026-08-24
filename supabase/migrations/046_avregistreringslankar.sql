-- Avregistreringslänken: den enda vägen ut ur ett utskick.
--
-- VARFÖR EN TABELL OCH INTE EN SIGNERAD TOKEN I URL:EN
--
-- Alternativet var en HMAC-signerad token som bär tenant och adress. Den hade
-- inte krävt någon tabell — men base64 är inte kryptering, så adressen hade
-- legat läsbar i varje länk: i mottagarens webbhistorik, i vår access-logg,
-- i referer-huvudet till varje resurs sidan laddar, och i det e-postskydd som
-- klickar länken innan mottagaren gör det. En personuppgift i en URL är en
-- personuppgift på fyra ställen till.
--
-- Ett ogenomskinligt slumptal säger ingenting alls om det läcker, och kostar
-- en tabell.
--
-- VARFÖR TOKEN ÄR text OCH INTE uuid: den ska gå att generera var som helst
-- i kedjan (Python idag, kanske Next imorgon) utan att formatet blir ett
-- kontrakt mellan två språk. 32 hexdecimaler ur `secrets.token_hex` är vad
-- app/leads/utskicksfot.py skriver.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

create table if not exists public.ss_avregistreringslankar (
  token       text primary key,
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  email       text not null,
  created_at  timestamptz not null default now(),
  -- Sätts när mottagaren faktiskt avregistrerat sig. Länken slutar INTE
  -- fungera efter det: en mottagare som klickar igen ska få se att hen redan
  -- är avregistrerad, inte ett 404 som ser ut som att klicket inte togs emot.
  anvand_at   timestamptz
);

-- En adress ska ha EN länk per kund, inte en per utskick. Annars slutar den
-- gamla länken i ett tidigare mejl att kännas rätt när mottagaren letar upp
-- den, och två giltiga tokens för samma person gör spårningen dubbeltydig.
create unique index if not exists ss_avregistreringslankar_tenant_email_idx
  on public.ss_avregistreringslankar (tenant_id, lower(email));

-- Samma tenant-isolering som resten av backendens tabeller, med 028:s
-- nullif-skydd inbyggt — utan `nullif` kastar policyn
-- `invalid input syntax for type uuid: ""` så fort en skopad fråga körts
-- tidigare på samma poolade anslutning.
alter table public.ss_avregistreringslankar enable row level security;

drop policy if exists ss_avregistreringslankar_tenant_isolation
  on public.ss_avregistreringslankar;
create policy ss_avregistreringslankar_tenant_isolation
  on public.ss_avregistreringslankar
  for all to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

comment on table public.ss_avregistreringslankar is
  'Ogenomskinlig token per (tenant, adress) som gör avregistreringslänken i '
  'utskicken klickbar utan att adressen ligger i URL:en. Skrivs av '
  'app/leads/utskicksfot.py, löses in av app/avregistrera/[token] i Next.';


-- ---------------------------------------------------------------------------
-- Inlösen. EN funktion, security definer.
-- ---------------------------------------------------------------------------
--
-- VARFÖR INTE VANLIGA POLICYER: den som klickar är inte inloggad. Hen har
-- ingen session, ingen arbetsyta och ingen tenant — bara en sträng ur ett
-- mejl. Varje RLS-policy i den här databasen skopar på `current_workspace_id()`
-- eller `app.tenant_id`, och båda är tomma här. Att öppna `suppressions` för
-- en oautentiserad roll hade varit att riva spärren för att komma åt en dörr.
--
-- Funktionen är i stället den enda dörren: den tar EN ogenomskinlig token,
-- och kan inte förmås att skriva något annat än exakt den avregistrering
-- token pekar ut. Kan man inte token kan man ingenting.
--
-- `set search_path = public, pg_temp` av samma skäl som 018_rpc_hardening:
-- utan den kan en anropare med rätt att skapa ett schema kapa varje
-- okvalificerat namn i kroppen.
--
-- Returvärde: 'avregistrerad' | 'redan_avregistrerad' | 'okand_token'. Alltså
-- aldrig ett undantag för en token som inte finns — en trasig länk ska ge
-- mottagaren ett begripligt besked, inte en 500-sida.

create or replace function public.avregistrera_via_token(p_token text)
returns text
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  l record;
  v_workspace uuid;
  v_fanns boolean;
begin
  select * into l
    from public.ss_avregistreringslankar
   where token = p_token;

  if not found then
    return 'okand_token';
  end if;

  select exists (
    select 1 from public.suppressions s
     where s.tenant_id = l.tenant_id
       and lower(s.email) = lower(l.email)
  ) into v_fanns;

  -- workspace_id är not null sedan 000. Saknas kopplingen är det ett riktigt
  -- fel: en avregistrering som tyst inte sparas är det värsta utfallet i hela
  -- den här filen.
  select w.id into v_workspace
    from public.workspaces w
   where w.ss_tenant_id = l.tenant_id
   limit 1;

  if v_workspace is null then
    raise exception 'Tenant % saknar arbetsyta — avregistreringen kan inte sparas.', l.tenant_id;
  end if;

  if not v_fanns then
    insert into public.suppressions (workspace_id, tenant_id, email, reason)
    values (v_workspace, l.tenant_id, lower(l.email), 'avregistrering via länk i utskick');
  end if;

  -- Stämplas även när adressen redan fanns: det säger att LÄNKEN användes,
  -- vilket är den fråga man ställer när någon hävdar att den inte fungerade.
  update public.ss_avregistreringslankar
     set anvand_at = coalesce(anvand_at, now())
   where token = p_token;

  return case when v_fanns then 'redan_avregistrerad' else 'avregistrerad' end;
end;
$$;

revoke all on function public.avregistrera_via_token(text) from public;
grant execute on function public.avregistrera_via_token(text) to snajp_web;
grant execute on function public.avregistrera_via_token(text) to snajp_app;

comment on function public.avregistrera_via_token(text) is
  'Löser in en avregistreringslänk. Enda vägen för en oinloggad mottagare att '
  'skriva till suppressions. Se 046_avregistreringslankar.sql för varför den '
  'är security definer.';
