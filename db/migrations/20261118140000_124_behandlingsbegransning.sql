-- 124: begränsning av behandling (GDPR art. 18) som en teknisk spärrmarkering.
--
-- ## Varför
--
-- En registrerad person kan begära att behandlingen av hennes uppgifter
-- begränsas, till exempel medan riktigheten prövas (art. 18.1 a) eller i
-- väntan på att en invändning avgörs (art. 18.1 d). Uppgifterna får då bara
-- lagras. Fram till nu fanns ingen markering att sätta: rättighetsskriptet
-- (scripts/gdpr_radera.py) kunde söka, lämna ut och radera, men inte stoppa
-- fortsatt behandling utan att radera (GDPR PR-4, docs/compliance).
--
-- ## Vad markeringen gör
--
-- En aktiv rad (havd_at är null) för en adress gör att
--   * sändningsspärren stoppar varje utskick till adressen, hos varje kund
--     (snajp-support/app/leads/scheduler.py, före de sex reglerna i send_guard);
--   * ett inkommande mejl från adressen sparas men går till Att hantera, utan
--     klassning, triage, Jev eller AI-utkast (email_pipeline/processor.py).
-- Uppgifterna raderas inte och ändras inte. Markeringen hävs med
-- `gdpr_radera.py --hav-begransning`, som sätter havd_at; raden står kvar som
-- belägg för att begäran hanterats (art. 18.3: personen ska informeras innan
-- begränsningen hävs).
--
-- ## Varför global och inte per kund
--
-- Begäran gäller personen, inte en enskild kunds lista. Rättighetsskriptet
-- söker och raderar redan över alla kunder på adressen; markeringen gör
-- detsamma. Därför ingen tenant_id och ingen tenant-skopad policy, till
-- skillnad från suppressions (030).
--
-- ## Vem som får skriva
--
-- Ingen approll. snajp_app (api) och snajp_web (Next) får bara läsa; raderna
-- skrivs av ägarrollen genom scripts/gdpr_radera.py. Migration 009 och 030
-- ger approllerna rättigheter på nya tabeller automatiskt, därför återkallas
-- de uttryckligen nedan.
--
-- Additiv och idempotent: kan köras om utan verkan.

create table if not exists public.behandlingsbegransningar (
  id         uuid primary key default gen_random_uuid(),
  email      text not null,
  skal       text not null,
  begard_at  timestamptz not null default now(),
  havd_at    timestamptz,
  havd_skal  text,
  created_at timestamptz not null default now()
);

-- En aktiv begränsning per adress. En hävd rad hindrar inte en ny.
create unique index if not exists behandlingsbegransningar_aktiv_idx
  on public.behandlingsbegransningar (lower(email)) where havd_at is null;

comment on table public.behandlingsbegransningar is
  'GDPR art. 18 (124): en aktiv rad (havd_at null) stoppar utskick och '
  'automatisk behandling av inkommande mejl för adressen, hos alla kunder. '
  'Skrivs bara av scripts/gdpr_radera.py.';

alter table public.behandlingsbegransningar enable row level security;

drop policy if exists behandlingsbegransningar_las on public.behandlingsbegransningar;
create policy behandlingsbegransningar_las on public.behandlingsbegransningar
  for select using (true);

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    revoke insert, update, delete, truncate on table public.behandlingsbegransningar from snajp_app;
    grant select on table public.behandlingsbegransningar to snajp_app;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    revoke insert, update, delete, truncate on table public.behandlingsbegransningar from snajp_web;
    grant select on table public.behandlingsbegransningar to snajp_web;
  end if;
end;
$$;
