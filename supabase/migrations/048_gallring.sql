-- Gallring av supportdata: mekanismen, inte beslutet.
--
-- ## Varför det inte står något tal i den här filen
--
-- Retentionsperioden är ett AFFÄRSBESLUT lika mycket som ett tekniskt. Den
-- måste stämma med vad som står i integritetspolicyn, med
-- personuppgiftsbiträdesavtalet och med vad kunden lovat sina egna kunder —
-- och en siffra som en utvecklare valde för att något behövde stå där hade
-- blivit den siffra som gäller, utan att någon fattat beslutet.
--
-- Därför: ingen policy = ingen gallring. Tabellen nedan är tom när
-- migrationen körts, och `gallra_supportdata` raderar då ingenting. Det är
-- den ofarliga defaulten. Motsatsen — ett antaget tal på 24 månader — hade
-- raderat en kunds ärendehistorik utan att kunden vetat om det.
--
-- ## Varför bara ss_emails i delete-satsen
--
-- ss_email_attachments, ss_classifications, ss_drafts och ss_human_reviews
-- hänger alla i `on delete cascade` från ss_emails (se 004). En delete per
-- tabell hade varit fyra chanser att glömma en, och den man glömmer är
-- bilagan — alltså den rad som faktiskt bär bilden på någons kvitto.
--
-- ## Varför ingen soft delete
--
-- Ett `deleted_at` som döljer raden i UI:t men lämnar den i databasen är inte
-- radering. Den registrerade som begärt att bli glömd är inte glömd, och
-- backupen bär den lika länge som förut. Gallring ska ta bort.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

create table if not exists public.ss_gallringspolicy (
  tenant_id  uuid primary key references public.ss_tenants(id) on delete cascade,
  -- Antal dagar efter senaste aktivitet på ärendet som raden får ligga kvar.
  -- Ingen default: den som skriver raden ska ha tagit ställning.
  dagar      integer not null check (dagar >= 30),
  -- Vem som beslutade och när. Frågan "vem bestämde 24 månader?" ställs alltid
  -- vid fel tillfälle, och ett svar i databasen är billigare än ett i minnet.
  beslutad_av text not null,
  beslutad_at timestamptz not null default now()
);

comment on table public.ss_gallringspolicy is
  'Retentionsperiod per kund. Ingen rad = ingen automatisk gallring. Talet är '
  'ett affärsbeslut och sätts av en människa, inte av en migration.';

-- ---------------------------------------------------------------------------
-- Gallringen.
-- ---------------------------------------------------------------------------
--
-- `p_torrkorning` finns för att första körningen mot en riktig databas ska gå
-- att göra utan att radera något. En rutin som bara har ett läge — skarpt —
-- provkörs inte, och en ogranskad första körning mot produktion är exakt det
-- som gör gallring till en incident i stället för en rutin.
--
-- Returnerar antalet ärenden som raderades (eller skulle ha raderats).

create or replace function public.gallra_supportdata(
  p_tenant uuid,
  p_torrkorning boolean default true
)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_dagar   integer;
  v_grans   timestamptz;
  v_antal   integer;
begin
  select dagar into v_dagar
    from public.ss_gallringspolicy
   where tenant_id = p_tenant;

  if v_dagar is null then
    return 0;  -- Ingen policy beslutad. Ofarlig default, se filhuvudet.
  end if;

  v_grans := now() - make_interval(days => v_dagar);

  -- `updated_at` och inte `received_at`: gränsen går vid senaste AKTIVITET på
  -- ärendet. Ett ärende som fortfarande besvaras är inte gammalt bara för att
  -- det första mejlet kom in för två år sedan.
  select count(*) into v_antal
    from public.ss_emails
   where tenant_id = p_tenant
     and updated_at < v_grans;

  if p_torrkorning then
    return v_antal;
  end if;

  delete from public.ss_emails
   where tenant_id = p_tenant
     and updated_at < v_grans;

  -- Spårbarheten. En gallring ingen kan visa att den skett är, vid en
  -- granskning, en gallring som inte skett.
  -- email_id lämnas NULL med flit: kolumnen kaskaderar från ss_emails, så en
  -- logg som pekade på ett raderat ärende hade raderats i samma andetag som
  -- det den skulle bevisa.
  insert into public.ss_decision_log (tenant_id, email_id, event, detail)
  values (
    p_tenant,
    null,
    'gallring',
    jsonb_build_object('raderade', v_antal, 'dagar', v_dagar, 'grans', v_grans)
  );

  return v_antal;
exception
  when undefined_table then
    -- ss_decision_log finns inte i alla miljöer (den kom med 002). Att en
    -- saknad logg-tabell skulle rulla tillbaka en genomförd radering vore
    -- fel prioritering — raderingen är det viktiga, loggen är beviset.
    return v_antal;
end;
$$;

revoke all on function public.gallra_supportdata(uuid, boolean) from public;
grant execute on function public.gallra_supportdata(uuid, boolean) to snajp_app;

comment on function public.gallra_supportdata(uuid, boolean) is
  'Raderar ärenden äldre än kundens beslutade retentionsperiod. Torrkörning '
  'som default. Anropas av scripts/gallra.py, schemalagd i Railway.';
