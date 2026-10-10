-- 108: webbpoolen (plan 2026-10-08, Antons godkännande samma dag). Idempotent.
--
-- Varje körning hos varje kund passerar bolag med webbplats. Sidbedömningen
-- av dem (webbrevision) samlas i en plattformstabell och fördelas till
-- webbyråkunderna efter län: Alunix (Västra Götaland, Halland) och Umeå
-- Webbdesign (Norrland). Bara BOLAGSNIVÅ får finnas här: offentliga
-- bolagsuppgifter och en mätning av en publik sajt. Inga personuppgifter,
-- inget kundinnehåll och aldrig vilken kund som hittade bolaget
-- (INV-SEC-008, tests/invariants/test_inv_sec_008.py granskar kolumnerna).
--
-- 1. prospects.lan och lead_list_items.lan/postnr/webbniva/webbrevision.
-- 2. lead_lists.kalla får 'webbpool'.
-- 3. webbpool: en rad per domän, utan tenant_id.
-- 4. webbpool_fordelad: vilken mottagare som fått vilken domän, så att en
--    domän aldrig fördelas två gånger till samma kund.

alter table public.prospects add column if not exists lan text;

alter table public.lead_list_items add column if not exists lan text;
alter table public.lead_list_items add column if not exists postnr text;
alter table public.lead_list_items add column if not exists webbniva text;
alter table public.lead_list_items add column if not exists webbrevision jsonb;

alter table public.lead_lists drop constraint if exists lead_lists_kalla_check;
alter table public.lead_lists
  add constraint lead_lists_kalla_check
    check (kalla in ('sok', 'kombinerad', 'import', 'crm', 'saljlista', 'webbpool'));

create table if not exists public.webbpool (
  doman            text primary key,
  website          text not null,
  company_name     text,
  orgnr            text,
  ort              text,
  postnr           text,
  lan              text,
  sni              text,
  webbniva         text check (webbniva in ('akut', 'dalig', 'bra', 'mycket_bra', 'okand', 'avvecklad')),
  webbrevision     jsonb,
  forsta_kalla_typ text check (forsta_kalla_typ in ('korning', 'lista')),
  bedomd_at        timestamptz,
  sedd_at          timestamptz not null default now(),
  created_at       timestamptz not null default now()
);
create index if not exists webbpool_lan_niva_idx on public.webbpool (lan, webbniva);

create table if not exists public.webbpool_fordelad (
  doman        text not null references public.webbpool(doman) on delete cascade,
  mottagare    uuid not null references public.ss_tenants(id) on delete cascade,
  list_id      uuid,
  fordelad_at  timestamptz not null default now(),
  primary key (doman, mottagare)
);

comment on table public.webbpool is
  'Sidbedömda bolag ur alla körningar, bara bolagsnivå (INV-SEC-008). Ingen tenant_id, '
  'inga personuppgifter. Fördelas till webbyråkunderna efter län (app/leads/webbpool.py).';

alter table public.webbpool enable row level security;
alter table public.webbpool_fordelad enable row level security;

-- Plattformens tabeller, inte arbetsytans: INTE grantade till snajp_web.
-- Vägen in går via backenden (snajp_app), samma mönster som prompt_lager (101).
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on public.webbpool to snajp_app;
    grant select, insert on public.webbpool_fordelad to snajp_app;

    drop policy if exists "snajp_app webbpool" on public.webbpool;
    create policy "snajp_app webbpool" on public.webbpool
      for all to snajp_app using (true) with check (true);
    drop policy if exists "snajp_app webbpool_fordelad" on public.webbpool_fordelad;
    create policy "snajp_app webbpool_fordelad" on public.webbpool_fordelad
      for all to snajp_app using (true) with check (true);
  end if;
end $$;
