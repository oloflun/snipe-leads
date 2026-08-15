-- snajpsupport@gmail.com som första plattformsadmin.
--
-- Idempotent och självdokumenterande i git, i stället för ett klick i en
-- konsol som ingen kan spåra i efterhand. Det är hela poängen med att en
-- engångsåtgärd ändå blir en migration.
--
-- Kontot måste finnas i auth.users först. Skapa det på /login (signup-fliken)
-- innan du kör den här — annars matchar select:en ingenting och migrationen
-- blir en tyst no-op. Kontrollen efteråt nedan är därför inte valfri.
--
-- Lösenordet sätts av dig, aldrig av en agent och aldrig i en migration.

insert into public.platform_admins (user_id)
select id from auth.users where email = 'snajpsupport@gmail.com'
on conflict (user_id) do nothing;

-- Verifiering (kör manuellt efter migrationen):
--   select u.email, pa.granted_at
--   from public.platform_admins pa join auth.users u on u.id = pa.user_id;
-- Tom rad = kontot fanns inte än. Skapa det och kör om filen; den är idempotent.
