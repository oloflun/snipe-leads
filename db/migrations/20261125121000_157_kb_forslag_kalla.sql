-- 157: förslagen i kunskapsbasen får en källa.
--
-- Hjälprutan (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 3): kunden kan göra
-- text ur samtalet med Snajps agent till ett förslag i sin EGEN kunskapsbas
-- (POST /api/kb/forslag, under kundens nyckel). Förslaget beslutas på samma
-- väg som skanningens (INV-LEARN-001: en människa lägger till varje artikel),
-- och listan visar var det kom ifrån.
--
--   kalla      'skanning' (webbplatsskanningen, allt som fanns före den här
--              migrationen), 'chatt' (Hjälprutan) eller 'agent'.
--   kalla_ref  en valfri hänvisning, t.ex. samtalets id. Ingen främmande nyckel.
--   skapad_av  användaren som lade förslaget, när den är känd.
--
-- skanning_id var redan nullbar (121). Villkoret nedan gör den obligatorisk
-- bara för skanningens förslag; NOT VALID så att befintliga rader inte prövas.
--
-- Additiv och idempotent. Rättigheterna från 121 (select, insert, update till
-- snajp_app) och radskyddet per tenant gäller oförändrade.

alter table public.ss_kb_forslag
  add column if not exists kalla     text not null default 'skanning',
  add column if not exists kalla_ref text,
  add column if not exists skapad_av uuid;

alter table public.ss_kb_forslag alter column skanning_id drop not null;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ss_kb_forslag_kalla_check') then
    alter table public.ss_kb_forslag
      add constraint ss_kb_forslag_kalla_check
      check (kalla in ('skanning', 'chatt', 'agent'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ss_kb_forslag_skanning_kalla_check') then
    alter table public.ss_kb_forslag
      add constraint ss_kb_forslag_skanning_kalla_check
      check (kalla <> 'skanning' or skanning_id is not null) not valid;
  end if;
end;
$$;

comment on column public.ss_kb_forslag.kalla is
  'Var förslaget kom ifrån: skanning, chatt (Hjälprutan) eller agent. Migration 157.';
