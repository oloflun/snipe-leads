-- Creates workspace + profile when a new auth user signs up.
-- Run in Supabase SQL editor or via `supabase db push`.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  new_workspace_id uuid;
  display_name text;
begin
  display_name := coalesce(
    nullif(trim(new.raw_user_meta_data->>'full_name'), ''),
    split_part(new.email, '@', 1),
    'Mitt workspace'
  );

  insert into public.workspaces (name)
  values (display_name || ' workspace')
  returning id into new_workspace_id;

  insert into public.profiles (id, workspace_id, full_name, role)
  values (new.id, new_workspace_id, display_name, 'owner');

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();