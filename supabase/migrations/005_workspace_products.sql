-- Snajp ships two products. A workspace may own either or both, and the server
-- decides what the dashboard renders. Without this column every signed-in user
-- would see both products regardless of what they bought.
--
-- Default is both: existing workspaces and internal/demo accounts keep full
-- access, and narrowing a workspace is an explicit act.

alter table public.workspaces
  add column if not exists products text[] not null default array['leads', 'support'];

-- Guard against typos reaching the UI, where an unknown key would silently
-- render nothing rather than fail loudly.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'workspaces_products_valid'
  ) then
    alter table public.workspaces
      add constraint workspaces_products_valid
      check (products <@ array['leads', 'support']::text[] and array_length(products, 1) >= 1);
  end if;
end $$;

comment on column public.workspaces.products is
  'Entitlement: which Snajp products this workspace may use. Subset of {leads, support}, never empty.';
