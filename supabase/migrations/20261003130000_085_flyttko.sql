-- 085: Flyttloggen development → main (plan del E, Antons beställning 2026-10-01).
--
-- Development speglas från main varje natt (scripts/railway_seed_dev.py, envägs,
-- truncate + copy). Det som skapats i development och ska sparas måste flyttas
-- till main INNAN nästa spegling, via den ENDA vägen: admin-panelen Flytta till
-- main (app/api/admin_flytt.py, HMAC-signerat paket). Den här tabellen är
-- kvittot per rad, och spegelskriptet vägrar spegla när en flytt nyligen
-- misslyckats (--behall-flyttko), så inget försvinner tyst.
--
-- Tabellen finns i BÅDA miljöerna (samma schema), men bara development skriver
-- i den. importerad_fran på mejl och prospekt lagras i beslutsloggen respektive
-- prospektets profil (ingen ny kolumn).
create table if not exists public.dev_flytt_ko (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  typ         text not null check (typ in ('mejl', 'korning')),
  ref_id      text not null,
  skapad_at   timestamptz not null default now(),
  flyttad_at  timestamptz,
  resultat    text not null default 'ok'
);

create index if not exists dev_flytt_ko_tenant_idx on public.dev_flytt_ko (tenant_id, skapad_at desc);

alter table public.dev_flytt_ko enable row level security;
alter table public.dev_flytt_ko force row level security;
drop policy if exists tenant_isolation on public.dev_flytt_ko;
create policy tenant_isolation on public.dev_flytt_ko
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);
