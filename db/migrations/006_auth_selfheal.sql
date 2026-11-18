-- Registrering med privat mailadress gick inte att slutföra.
--
-- Två fel i 001_handle_new_user.sql:
--   1. Triggern är enda vägen till en profilrad, och `profiles` har bara en
--      SELECT-policy. Kastar triggern får signup 500 och användaren blir kvar i
--      auth.users utan profil — permanent låst ute, eftersom ingenting i appen
--      kan skapa raden i efterhand. Det har redan hänt en riktig användare.
--   2. Varje ny användare får ett eget workspace. Inbjudan till ett befintligt
--      workspace var därför omöjlig.
--
-- Denna migration är idempotent och kan köras om.

-- 1. Inbjudningar ----------------------------------------------------------
-- Finns en obrukad inbjudan för adressen hamnar användaren i det workspacet
-- istället för i ett nytt. Det är hela mekaniken bakom invite-only.

create table if not exists public.workspace_invites (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  role text not null default 'member',
  invited_by uuid references auth.users(id) on delete set null,
  accepted_at timestamptz,
  created_at timestamptz not null default now()
);

-- En obrukad inbjudan per adress och workspace. Delvis unikt index så att en
-- ny inbjudan kan skickas efter att en gammal förbrukats.
create unique index if not exists workspace_invites_open_key
  on public.workspace_invites (lower(email), workspace_id)
  where accepted_at is null;

alter table public.workspace_invites enable row level security;

-- Läsning för den som redan är medlem i workspacet. Skrivning sker med
-- service-rollen från servern, aldrig från klienten.
drop policy if exists workspace_members_read_invites on public.workspace_invites;
create policy workspace_members_read_invites on public.workspace_invites
  for select using (
    workspace_id in (select workspace_id from public.profiles where id = auth.uid())
  );

-- 2. En funktion, två anropare --------------------------------------------
-- Triggern använder den vid registrering; appen använder den via RPC för att
-- läka ett konto som saknar profil. Samma kod båda vägarna.

create or replace function public.ensure_workspace_for_user(
  target_user uuid,
  display_name text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  existing_workspace uuid;
  invite record;
  resolved_name text;
  user_email text;
begin
  select workspace_id into existing_workspace
  from public.profiles where id = target_user;

  if existing_workspace is not null then
    return existing_workspace;
  end if;

  select email into user_email from auth.users where id = target_user;

  if user_email is null then
    raise exception 'ensure_workspace_for_user: okänd användare %', target_user;
  end if;

  resolved_name := coalesce(
    nullif(trim(display_name), ''),
    nullif(split_part(user_email, '@', 1), ''),
    'Mitt workspace'
  );

  -- Inbjudan vinner över nytt workspace.
  select * into invite
  from public.workspace_invites
  where lower(email) = lower(user_email) and accepted_at is null
  order by created_at
  limit 1;

  if invite.id is not null then
    existing_workspace := invite.workspace_id;
    update public.workspace_invites
      set accepted_at = now() where id = invite.id;
  else
    insert into public.workspaces (name)
    values (resolved_name || ' workspace')
    returning id into existing_workspace;
  end if;

  insert into public.profiles (id, workspace_id, full_name, role)
  values (
    target_user,
    existing_workspace,
    resolved_name,
    coalesce(invite.role, 'owner')
  )
  on conflict (id) do nothing;

  return existing_workspace;
end;
$$;

-- Appen anropar den som inloggad användare, och bara för sig själv.
create or replace function public.ensure_workspace_for_current_user()
returns uuid
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then
    raise exception 'Inte inloggad.';
  end if;
  return public.ensure_workspace_for_user(auth.uid(), null);
end;
$$;

revoke all on function public.ensure_workspace_for_user(uuid, text) from public, anon, authenticated;
grant execute on function public.ensure_workspace_for_current_user() to authenticated;

-- 3. Triggern får aldrig blockera en registrering igen ----------------------
-- Misslyckas den loggas det som en varning och användaren skapas ändå;
-- profilen läks vid första inloggningen via RPC:n ovan. Ett trasigt workspace
-- går att reparera, ett konto som aldrig kunde skapas gör det inte.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  begin
    perform public.ensure_workspace_for_user(
      new.id,
      nullif(trim(new.raw_user_meta_data->>'full_name'), '')
    );
  exception when others then
    raise warning 'handle_new_user misslyckades för %: %', new.id, sqlerrm;
  end;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 4. Backfyll de konton som redan fastnat ----------------------------------

do $$
declare
  orphan record;
begin
  for orphan in
    select u.id from auth.users u
    left join public.profiles p on p.id = u.id
    where p.id is null
  loop
    perform public.ensure_workspace_for_user(orphan.id, null);
  end loop;
end $$;
