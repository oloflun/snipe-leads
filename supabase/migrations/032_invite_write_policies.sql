-- Skrivpolicyer för workspace_invites, så inbjudningar inte längre kräver en
-- roll som kringgår RLS.
--
-- 006 gav tabellen en SELECT-policy och inga skrivpolicyer, med motiveringen
-- att en klient aldrig ska kunna skriva en inbjudan direkt — då hade
-- `workspace_id` kommit från klienten. Följden blev att lib/actions/team.ts
-- gick via service-rollen, alltså en anslutning UTAN radsäkerhet, och att
-- `revokeInvite` fick lägga till `workspace_id` i sin where-sats för hand med
-- kommentaren att den inte är överflödig. Den var det inte — men den var ett
-- villkor som bara fanns i applikationskoden.
--
-- Policyerna nedan flyttar samma villkor till databasen och gör det starkare:
-- `workspace_id` KAN inte komma från klienten, eftersom raden måste matcha
-- anroparens egen arbetsyta, och bara ägaren släpps igenom. Ett glömt
-- where-villkor i en framtida refaktorering blir då ett avslag i stället för
-- en läcka.
--
-- Det tar också bort behovet av en andra databasanslutning med förhöjd
-- behörighet i Next-appen, vilket var en av delarna ombyggnaden skulle bli av
-- med.

create or replace function public.current_user_is_owner()
returns boolean
language sql
security definer
stable
set search_path = public, pg_temp
as $$
  select exists (
    select 1 from public.profiles
     where id = auth.uid() and role = 'owner'
  )
$$;

revoke execute on function public.current_user_is_owner() from public;
grant execute on function public.current_user_is_owner() to authenticated;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    execute 'grant execute on function public.current_user_is_owner() to snajp_web';
  end if;
end $$;

drop policy if exists workspace_owners_write_invites on public.workspace_invites;
create policy workspace_owners_write_invites on public.workspace_invites
  for insert
  with check (
    workspace_id = public.current_workspace_id()
    and public.current_user_is_owner()
  );

-- Bara obrukade inbjudningar går att ta bort. En accepterad inbjudan är en
-- historisk händelse, inte ett väntande tillstånd, och att kunna radera den
-- hade tagit bort spåret av vem som släppte in vem.
drop policy if exists workspace_owners_delete_invites on public.workspace_invites;
create policy workspace_owners_delete_invites on public.workspace_invites
  for delete
  using (
    workspace_id = public.current_workspace_id()
    and public.current_user_is_owner()
    and accepted_at is null
  );
