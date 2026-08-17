-- `/admin` svarar 404 även för en korrekt tillsatt plattformsadmin.
--
-- ORSAKEN: policyn `platform_admins_self_read` (migration 020) läser sin EGEN
-- tabell i sitt eget villkor:
--
--     using (exists (select 1 from platform_admins pa where pa.user_id = auth.uid()))
--
-- För att avgöra om en rad i platform_admins får läsas måste Postgres läsa
-- platform_admins, vilket kräver att policyn utvärderas, vilket kräver att
-- platform_admins läses. Resultatet är `infinite recursion detected in policy
-- for relation "platform_admins"`.
--
-- VARFÖR DET SÅG UT SOM ATT INGET VAR FEL: `isPlatformAdmin()` i
-- lib/auth/admin.ts är fail-closed med flit — ett uppslag som inte gick att
-- göra betyder INTE admin, eftersom motsatsen hade gjort ett databasavbrott
-- till en behörighetshöjning. Den fångar alltså rekursionsfelet, loggar det
-- och returnerar false. `/admin/layout.tsx` svarar då `notFound()`.
--
-- Följden är den värsta sortens fel: allt beter sig precis som om personen
-- inte vore admin. Ingen röd skärm, ingen felkod för användaren — bara en
-- sida som inte finns. Man letar efter en saknad rad i platform_admins,
-- hittar den, och förstår ändå ingenting.
--
-- Migration 032 löser TILLSÄTTNINGEN (rätt person hamnar i tabellen). Den här
-- löser LÄSNINGEN. Utan båda renderas ytan fortfarande inte.
--
-- FIXEN: `user_id = auth.uid()`. En rad är läsbar av den den handlar om.
-- Villkoret rör inte tabellen på nytt och kan därför inte rekursera.
--
-- VAD SOM GÅR FÖRLORAT: 020:s avsikt var att en admin skulle se HELA listan
-- över admins. Det har aldrig fungerat — policyn kastade från första dagen —
-- så ingenting som fungerade tas bort här. Funktionaliteten som faktiskt
-- används är `isPlatformAdmin(userId)`, som slår upp exakt en rad: sin egen.
-- Behöver adminytan senare räkna upp alla admins görs det via service_role i
-- en route som redan ligger bakom require_master_key, inte genom att öppna
-- tabellen för klienten.
--
-- SÄKERHETEN ÄR OFÖRÄNDRAD ELLER BÄTTRE: den som inte står i tabellen får noll
-- rader, precis som förut. Den som står i den får se sin egen rad och inte
-- någon annans — alltså läcker vi inte längre vilka andra som är admins.

drop policy if exists platform_admins_self_read on public.platform_admins;

create policy platform_admins_self_read on public.platform_admins
  for select to authenticated
  using (user_id = auth.uid());

comment on policy platform_admins_self_read on public.platform_admins is
  'Rör INTE tabellen i sitt eget villkor. Ett exists-uttryck mot platform_admins '
  'här ger infinite recursion, och felet syns som att /admin bara ger 404.';
