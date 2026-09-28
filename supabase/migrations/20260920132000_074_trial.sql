-- Gratis provperiod: 2 kalendermånader från kontoskapande, för alla nya konton.
--
-- Beställd 2026-09-20. Trialen är ett DATUM, inte en boolean — samma mönster
-- som avtal_signerat (053): "trial till och med <datum>" är hela statusen,
-- och dagens datum avgör om den löper. Ingen automatisk konvertering till
-- betalning byggs här; det är ett affärsbeslut som väntar på Anton/Sebbe.
--
-- Kolumnen ligger på workspaces eftersom kontot ÄR arbetsytan
-- (workspaces.created_at sätts av signupflödets trigger) — tenanten skapas
-- först vid onboardingen och kan dröja. Befintliga arbetsytor backfylls från
-- sitt riktiga skapelsedatum: för dem som är äldre än två månader blir
-- trialen ett passerat datum, vilket är sant. Betalande kunder känns igen på
-- avtal_signerat i kundregistret, inte på trialdatumet.

alter table public.workspaces
  add column if not exists trial_slut date;

update public.workspaces
   set trial_slut = (created_at + interval '2 months')::date
 where trial_slut is null;

-- Volatil default utvärderas per INSERT (created_at ~ now() i samma rad).
-- Att den sätts EFTER backfyllnaden är avsiktligt: en volatil default i
-- själva ADD COLUMN hade skrivit "migrationsdagen + 2 månader" på varje
-- befintlig rad.
alter table public.workspaces
  alter column trial_slut set default (now() + interval '2 months')::date;

comment on column public.workspaces.trial_slut is
  'Sista dagen i den fria provperioden (2 mån från kontoskapande). '
  'Datum passerat = trial över. Betalstatus avgörs av ss_customer_details.avtal_signerat.';

-- Påminnelseloggen: en rad per skickad påminnelse, unik per arbetsyta och
-- typ. Unikheten är spärren som gör sveparen omkörningsbar — skickning sker
-- FÖRE loggning (hellre en dubblettpåminnelse efter en krasch än en tyst
-- utebliven), och conflict-hanteringen tar dubbletterna.
create table if not exists public.trial_paminnelser (
  id            uuid primary key default gen_random_uuid(),
  workspace_id  uuid not null references public.workspaces(id) on delete cascade,
  typ           text not null check (typ in ('7_dagar', '1_dag')),
  skickad_till  text not null,
  created_at    timestamptz not null default now(),
  unique (workspace_id, typ)
);

-- Plattformstabell utan tenant-kolumn, läst/skriven av backendens svepare.
-- Samma villkor som 029/064: bara när INGEN tenant-kontext är satt.
alter table public.trial_paminnelser enable row level security;
drop policy if exists trial_paminnelser_platform on public.trial_paminnelser;
create policy trial_paminnelser_platform on public.trial_paminnelser
  for all to snajp_app
  using (nullif(current_setting('app.tenant_id', true), '') is null)
  with check (nullif(current_setting('app.tenant_id', true), '') is null);
grant select, insert on table public.trial_paminnelser to snajp_app;

-- Sveparen behöver ägarens mejladress: workspaces -> profiles(owner) ->
-- auth.users. snajp_app läser redan auth.users och workspaces (064) men
-- saknade profiles. Enbart select, och bara utan tenant-kontext — profiles
-- bär inga hemligheter (user-id, workspace-id, roll), mejlen bor i auth.users.
grant select on public.profiles to snajp_app;
drop policy if exists profiles_platform_read on public.profiles;
create policy profiles_platform_read on public.profiles
  for select to snajp_app
  using (nullif(current_setting('app.tenant_id', true), '') is null);

-- Verifiering efter körning:
--   select count(*) from workspaces where trial_slut is null;      -- 0
--   som snajp_app utan tenant-kontext:
--   select count(*) from profiles;                                  -- > 0
--   insert into trial_paminnelser (workspace_id, typ, skickad_till)
--     values ('<ws>', '7_dagar', 'test@example.com');               -- ok + unik
