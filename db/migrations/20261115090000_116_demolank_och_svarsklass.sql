-- 116: demolänken i utkasten, och A/B-mätningen av svar och klick (Anton 2026-11-15).
--
-- Antons beställning: varje utkast och varje erbjudande, A eller B, bär en
-- länk till demon "ett snäpp ned från resten av texten", vi ska se vilka som
-- faktiskt besökt den, och A/B-mätningen ska visa totala svar, andel Ja, Nej,
-- Kanske/Återkom och andel som klickat, per utkastvariant.
--
-- Tre delar:
--
-- 1. outreach_threads.svarsklass: prospektsvarets klass (app/leads/svar.py).
--    Förut sparades den inte alls; erbjudande_utfall härledde "svar" och
--    "positiva" ur statusloggen, och "återkom" gick inte att skilja från en
--    fråga. Senaste meningsfulla svaret vinner (ett autosvar skriver inget).
-- 2. outreach_threads.struktur: utkastets struktur A/B (app/leads/utkaststruktur.py),
--    förut bara i agent_runs.step_log. Fylls i bakåt därifrån; trådar från
--    före strukturvalet (2026-11-05) lämnas tomma och räknas inte i A/B.
-- 3. ss_demolankar + ss_demolank_handelser: en ogenomskinlig token per tråd
--    (samma mönster som ss_avregistreringslankar, 046). Länken pekar på
--    Next-routen /prova/<token>, som loggar ett KLICK och skickar vidare till
--    demon. Demosidan loggar ett BESÖK först vid mottagarens första
--    interaktion: e-postskydd (Safe Links, Proofpoint, Mimecast …) klickar
--    rutinmässigt på länkar men scrollar och klickar inte på sidan. Klick
--    som ser ut som en skanner (känd user agent, eller inom två minuter från
--    utskicket) märks `skanner` och räknas inte som klick i mätningen.
--
-- Additiv och idempotent.

alter table public.outreach_threads add column if not exists svarsklass text;
alter table public.outreach_threads add column if not exists svarsklass_at timestamptz;
alter table public.outreach_threads add column if not exists struktur text;

alter table public.outreach_threads drop constraint if exists outreach_threads_svarsklass_check;
alter table public.outreach_threads add constraint outreach_threads_svarsklass_check
  check (svarsklass is null or svarsklass in
    ('positivt', 'aterkom', 'invandning', 'fraga', 'negativt', 'avregistrering'));

alter table public.outreach_threads drop constraint if exists outreach_threads_struktur_check;
alter table public.outreach_threads add constraint outreach_threads_struktur_check
  check (struktur is null or struktur in ('a', 'b'));

-- Strukturen bakåt: trådens första utkastkörning med ett strukturssteg.
update public.outreach_threads t
   set struktur = s.struktur
  from (
    select distinct on (r.thread_id) r.thread_id, lower(e->>'struktur') as struktur
      from public.agent_runs r
     cross join lateral jsonb_array_elements(
       case when jsonb_typeof(r.step_log) = 'array' then r.step_log else '[]'::jsonb end
     ) e
     where r.thread_id is not null and e->>'step' = 'struktur'
     order by r.thread_id, r.created_at
  ) s
 where s.thread_id = t.id and t.struktur is null and s.struktur in ('a', 'b');

-- Körningar som inte satte thread_id: prospektets första utkastkörning.
update public.outreach_threads t
   set struktur = s.struktur
  from (
    select distinct on (r.tenant_id, r.prospect_id) r.tenant_id, r.prospect_id,
           lower(e->>'struktur') as struktur
      from public.agent_runs r
     cross join lateral jsonb_array_elements(
       case when jsonb_typeof(r.step_log) = 'array' then r.step_log else '[]'::jsonb end
     ) e
     where r.prospect_id is not null and e->>'step' = 'struktur'
     order by r.tenant_id, r.prospect_id, r.created_at
  ) s
 where s.tenant_id = t.tenant_id and s.prospect_id = t.prospect_id
   and t.struktur is null and s.struktur in ('a', 'b');

create table if not exists public.ss_demolankar (
  token       text primary key,
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  thread_id   uuid not null references public.outreach_threads(id) on delete cascade,
  -- Dit länken leder. Kundens demolänk när token skapades; byts när kunden
  -- byter demolänk och utkastet skrivs om (demolanktoken uppdaterar).
  mal_url     text not null,
  created_at  timestamptz not null default now()
);

create unique index if not exists ss_demolankar_trad_idx
  on public.ss_demolankar (tenant_id, thread_id);

create table if not exists public.ss_demolank_handelser (
  id          bigserial primary key,
  token       text not null references public.ss_demolankar(token) on delete cascade,
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  typ         text not null check (typ in ('klick', 'besok')),
  skanner     boolean not null default false,
  user_agent  text,
  created_at  timestamptz not null default now()
);

create index if not exists ss_demolank_handelser_token_idx
  on public.ss_demolank_handelser (tenant_id, token, created_at);

alter table public.ss_demolankar enable row level security;
alter table public.ss_demolank_handelser enable row level security;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on public.ss_demolankar to snajp_app;
    grant select on public.ss_demolank_handelser to snajp_app;

    drop policy if exists ss_demolankar_tenant_isolation on public.ss_demolankar;
    create policy ss_demolankar_tenant_isolation on public.ss_demolankar
      for all to snajp_app
      using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
      with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

    drop policy if exists ss_demolank_handelser_tenant_isolation on public.ss_demolank_handelser;
    create policy ss_demolank_handelser_tenant_isolation on public.ss_demolank_handelser
      for select to snajp_app
      using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
  end if;
end $$;

comment on table public.ss_demolankar is
  'Ogenomskinlig token per utskickstråd för demolänken i utkasten. Skrivs av '
  'app/leads/demolank.py, löses in av app/prova/[token] i Next.';

-- Klicket: loggas och ger mål-URL:en (null = okänd token). Security definer
-- av samma skäl som avregistrera_via_token: den enda dörren en oinloggad
-- mottagare har in, utan att tabellerna öppnas för webbens roll.
create or replace function public.demolank_klick(p_token text, p_ua text)
returns text
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  l record;
  v_ua text := left(coalesce(p_ua, ''), 300);
  v_skanner boolean;
begin
  select * into l from public.ss_demolankar where token = p_token;
  if not found then
    return null;
  end if;

  v_skanner := v_ua = ''
    or v_ua ~* '(bot|crawl|spider|preview|scan|safelinks|proofpoint|mimecast|barracuda|'
                'forcepoint|symantec|trend ?micro|sophos|fortinet|cisco|ironport|'
                'python|curl|wget|go-http|java/|okhttp|headless|phantom|httpclient|'
                'microsoft office|outlook-ios|googleimageproxy|yahoo! slurp)'
    or exists (
      select 1 from public.outreach_messages m
       where m.thread_id = l.thread_id and m.direction = 'outbound'
         and m.sent_at is not null and m.sent_at > now() - interval '2 minutes'
    );

  insert into public.ss_demolank_handelser (token, tenant_id, typ, skanner, user_agent)
  values (l.token, l.tenant_id, 'klick', v_skanner, nullif(v_ua, ''));

  return l.mal_url;
end;
$$;

-- Besöket: demosidan anropar det vid mottagarens första interaktion.
create or replace function public.demolank_besok(p_token text)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  l record;
begin
  select * into l from public.ss_demolankar where token = p_token;
  if not found then
    return false;
  end if;
  -- Ett besök per token och halvtimme räcker: mätningen frågar om de
  -- besökt, och en loop i en webbläsare ska inte kunna fylla tabellen.
  if exists (
    select 1 from public.ss_demolank_handelser h
     where h.token = l.token and h.typ = 'besok' and h.created_at > now() - interval '30 minutes'
  ) then
    return true;
  end if;
  insert into public.ss_demolank_handelser (token, tenant_id, typ)
  values (l.token, l.tenant_id, 'besok');
  return true;
end;
$$;

revoke all on function public.demolank_klick(text, text) from public;
revoke all on function public.demolank_besok(text) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.demolank_klick(text, text) to snajp_web;
    grant execute on function public.demolank_besok(text) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant execute on function public.demolank_klick(text, text) to snajp_app;
    grant execute on function public.demolank_besok(text) to snajp_app;
  end if;
end $$;
