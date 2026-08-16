-- Plattformsadmin utan ordningsfälla.
--
-- PROBLEMET 021 HADE: den infogar `snajpsupport@gmail.com` i platform_admins
-- med en `select ... from auth.users where email = ...`. Finns inte kontot när
-- migrationen körs matchar select:en ingenting, och migrationen blir en TYST
-- no-op. Den är idempotent och kan köras om — men någon måste komma ihåg att
-- göra det, vid rätt tillfälle, efter en manuell registrering. Ett steg som
-- kräver att en människa minns en ordning är ett steg som förr eller senare
-- glöms bort, och symptomet är att /admin svarar 404 för rätt person utan att
-- något är trasigt.
--
-- LÖSNINGEN: gör kopplingen till ett TILLSTÅND i stället för ett ögonblick.
-- Adressen står i en lista; den som registrerar sig med en adress i listan blir
-- plattformsadmin, oavsett om kontot skapades före eller efter den här
-- migrationen. Ordningen slutar spela roll.

-- 1. Listan --------------------------------------------------------------
--
-- En tabell och inte en hårdkodad sträng i funktionen: en ny plattformsadmin
-- ska vara en rad man kan lägga till och se, inte en migration man måste
-- skriva. RLS är på och det finns INGA policyer — exakt som platform_admins
-- själv (020). Bara service_role och SQL-editorn når hit, och en
-- självbetjäningsväg in i admin är precis det de här tabellerna finns för att
-- förhindra.

create table if not exists public.platform_admin_bootstrap (
  email text primary key,
  note text,
  created_at timestamptz not null default now()
);

alter table public.platform_admin_bootstrap enable row level security;

insert into public.platform_admin_bootstrap (email, note)
values ('snajpsupport@gmail.com', 'Första plattformsadmin. Se MIGRATIONS-PENDING.md.')
on conflict (email) do nothing;

-- 2. Funktionen ----------------------------------------------------------
--
-- KRAVET PÅ BEKRÄFTAD ADRESS: graden ges först när `email_confirmed_at` är
-- satt. Plattformsadmin läser över ALLA kunders data, och den behörigheten ska
-- kräva bevisad kontroll över brevlådan — inte bara att någon skrivit
-- adressen i ett registreringsformulär.

create or replace function public.grant_bootstrap_platform_admin()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- HELA KROPPEN LIGGER I EN EXCEPTION-HANTERARE, och det är inte
  -- försiktighet utan en läxa: 006_auth_selfheal dokumenterar att en trigger
  -- på auth.users som KASTAR ger registreringen 500. Användaren blir kvar i
  -- auth.users utan profil och permanent utelåst, eftersom ingenting i appen
  -- kan skapa raden i efterhand. Det har redan hänt en riktig användare.
  --
  -- Att missa en admingrad är en olägenhet man rättar med en rad SQL. Att
  -- fälla registreringen är oreparabelt för det kontot. Fail-open är rätt val
  -- HÄR, och bara här, därför att den uteblivna effekten inte ger någon
  -- behörighet den inte skulle haft.
  begin
    if new.email_confirmed_at is not null and exists (
      select 1 from public.platform_admin_bootstrap b
       where lower(b.email) = lower(new.email)
    ) then
      insert into public.platform_admins (user_id)
      values (new.id)
      on conflict (user_id) do nothing;
    end if;
  exception when others then
    raise warning 'grant_bootstrap_platform_admin misslyckades för %: %', new.id, sqlerrm;
  end;

  return new;
end;
$$;

revoke all on function public.grant_bootstrap_platform_admin() from public, anon, authenticated;

-- 3. Triggern ------------------------------------------------------------
--
-- INSERT **och** UPDATE. Med e-postbekräftelse påslagen skapas raden med
-- `email_confirmed_at = null` och fylls i först när användaren klickat i
-- mejlet — en trigger enbart på INSERT hade därför aldrig gett graden. Med
-- bekräftelse avstängd sätts fältet direkt, och då räcker INSERT. Båda
-- vägarna täcks, så beteendet inte beror på en inställning i en konsol.

drop trigger if exists on_auth_user_bootstrap_admin on auth.users;

create trigger on_auth_user_bootstrap_admin
  after insert or update of email_confirmed_at on auth.users
  for each row execute function public.grant_bootstrap_platform_admin();

-- 4. Backfill ------------------------------------------------------------
--
-- För konton som redan finns. Idempotent; en no-op när kontot inte skapats än,
-- och då tar triggern över. Det är hela poängen: ingen ordning att minnas.

insert into public.platform_admins (user_id)
select u.id
  from auth.users u
  join public.platform_admin_bootstrap b on lower(b.email) = lower(u.email)
 where u.email_confirmed_at is not null
on conflict (user_id) do nothing;

comment on table public.platform_admin_bootstrap is
  'Adresser som blir plattformsadmin vid registrering. Ersätter 021:s '
  'ordningsberoende seed — graden ges när adressen bekräftats, oavsett om '
  'kontot skapades före eller efter migrationen.';
