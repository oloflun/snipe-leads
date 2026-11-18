-- 103: Säljlistan per arbetsyta (Sebbes beställning 2026-10-06, kväll).
--
-- 100 byggde säljlistan som Snajps egen, plattformsövergripande lista med
-- plattformsadmin som enda behörighet. Beslutet ändrades samma kväll:
-- säljlistan INGÅR i tillägget Leadslistor, så varje kund med tillägget får en
-- egen. Tillägget slås på av oss efter att kunden hört av sig (ingen
-- självbetjäning) — Snajps egen arbetsyta (slug `snajp`) har det.
--
-- Därför:
--   * tabellen byter namn till `saljlista` (den är inte längre Snajps),
--   * varje rad bär `workspace_id`; befintliga rader är Snajps,
--   * RLS släpper igenom den egna arbetsytans rader via current_workspace_id()
--     (app.user_id → profiles.workspace_id, se 035) i stället för
--     platform_admins.
--
-- Tilläggsgrinden ('leadlists' på workspace-raden) ligger i Next-appen, som
-- för resten av Leadslistor (lib/actions/saljlista.ts). RLS är isoleringen
-- mellan kunder; den avgör inte vad kunden betalat för.
--
-- 100 ligger bara i development när det här skrivs; i en kedja som reses från
-- noll körs båda i ordning. Idempotent.

alter table if exists public.snajp_saljlista rename to saljlista;
alter index if exists public.snajp_saljlista_skapad rename to saljlista_skapad;

alter table public.saljlista
  add column if not exists workspace_id uuid references public.workspaces(id) on delete cascade;

-- Rader från 100 var Snajps egna.
update public.saljlista
   set workspace_id = (select id from public.workspaces where slug = 'snajp' limit 1)
 where workspace_id is null;

-- En rad utan arbetsyta kan ingen läsa längre; den ska inte ligga kvar osynlig.
delete from public.saljlista where workspace_id is null;

alter table public.saljlista alter column workspace_id set not null;

drop index if exists public.saljlista_skapad;
create index if not exists saljlista_arbetsyta
  on public.saljlista (workspace_id, created_at desc);

comment on table public.saljlista is
  'Säljlista (CRM över bolag man ringt), ingår i tillägget Leadslistor. En '
  'per arbetsyta; RLS på current_workspace_id(), tilläggsgrinden i Next.';

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant select, insert, update, delete on public.saljlista to snajp_web;

    drop policy if exists saljlista_plattformsadmin on public.saljlista;
    drop policy if exists saljlista_arbetsyta on public.saljlista;
    create policy saljlista_arbetsyta on public.saljlista
      for all to snajp_web
      using (workspace_id = public.current_workspace_id())
      with check (workspace_id = public.current_workspace_id());
  end if;
end $$;
