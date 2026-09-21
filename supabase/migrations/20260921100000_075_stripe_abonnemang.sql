-- 075: Stripe-abonnemanget per arbetsyta — spegeln webhooken håller synkad.
--
-- ## Varifrån det här kommer
--
-- Porterat från grenen feature/snajp-multitenant-saas (migration 010 där,
-- 2026-08-14). Den grenen knöt abonnemanget till en BACKEND-tenant och till
-- kvotnivåer (Prova/Bas/Plus/Pro) som aldrig blev prismodellen. Prismodellen
-- blev paket per agent (lib/pricing.ts), och entitlementen är
-- workspaces.products (044). Tabellen hör därför till ARBETSYTAN här, och
-- paket_id är samma id som i lib/pricing.ts.
--
-- ## Stripe äger betalningen, den här raden är en spegel
--
-- Sanningen om vad kunden betalar för finns hos Stripe. Raden finns så att
-- faktureringssidan kan visa läget, och portalknappen hitta kundens
-- Stripe-kund, utan ett API-anrop till Stripe vid varje sidvisning.
--
-- ## Vad webhooken FÅR och INTE FÅR ändra
--
-- Ett aktivt köp sätter workspaces.products till paketets produkter — samma
-- skrivning som paketväljaren gör (set_workspace_products), bara utlöst av en
-- betalning i stället för ett klick.
--
-- En uppsägning eller ett misslyckat kortdrag ändrar INTE products. Det är
-- beslutet från trial-konverteringen (PR #23): avstängning är ett manuellt
-- handgrepp med bekräftelse i admin, aldrig något en händelse gör tyst. Här
-- speglas bara statusen, så att en människa ser den.

create table if not exists public.billing_subscriptions (
  workspace_id uuid primary key references public.workspaces(id) on delete cascade,
  -- Samma id som Paket.id i lib/pricing.ts. Null = okänt pris (webhooken
  -- gissar hellre inte).
  paket_id text,
  -- Speglar Stripes prenumerationsstatus. 'none' = aldrig haft en.
  status text not null default 'none' check (status in
    ('none', 'trialing', 'active', 'past_due', 'canceled', 'unpaid',
     'incomplete', 'incomplete_expired', 'paused')),
  stripe_customer_id text,
  stripe_subscription_id text unique,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  -- Sant när nyckeln var en testnyckel (sk_test_…). Samma skäl som
  -- billing_payment_methods.is_test: raderna från testperioden ska gå att
  -- skilja ut den dag skarpa nycklar sätts.
  is_test boolean not null default true,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists billing_subscriptions_customer_idx
  on public.billing_subscriptions (stripe_customer_id);

comment on table public.billing_subscriptions is
  'Spegel av Stripe-prenumerationen per arbetsyta. Skrivs BARA av '
  'stripe_synka_abonnemang (webhooken); kunden läser sin egen rad.';

alter table public.billing_subscriptions enable row level security;

-- Kunden läser sin egen rad. Ingen skrivpolicy: skrivvägen är funktionen
-- nedan och ingenting annat.
drop policy if exists "workspace reads own subscription" on public.billing_subscriptions;
create policy "workspace reads own subscription"
on public.billing_subscriptions for select
using (workspace_id = public.current_workspace_id());

-- ## Skrivvägen
--
-- security definer, eftersom webhooken saknar användare och RLS då skulle
-- stänga varje skrivning. Den får bara anropas av webbrollen EFTER att
-- Stripe-signaturen verifierats (app/api/billing/webhook/route.ts) —
-- signaturen är autentiseringen, samma roll som master-nyckeln spelade i
-- grenens backendvariant.
--
-- p_workspace får vara null: senare händelser (misslyckat kortdrag) bär bara
-- kund-id:t, och arbetsytan slås då upp via den rad köpet skapade.
--
-- p_products är null utom vid ett aktivt köp av ett känt paket. Kartan
-- paket → produkter bor i lib/pricing.ts (PRODUKTER_FOR_PAKET) och skickas
-- in därifrån — en andra kopia här hade glidit isär från den första.
create or replace function public.stripe_synka_abonnemang(
  p_workspace uuid,
  p_customer text,
  p_subscription text,
  p_paket text,
  p_status text,
  p_period_end timestamptz,
  p_cancel boolean,
  p_is_test boolean,
  p_products text[]
)
returns uuid
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $$
declare
  arbetsyta uuid := p_workspace;
begin
  if arbetsyta is null and p_customer is not null then
    select workspace_id into arbetsyta
      from public.billing_subscriptions
     where stripe_customer_id = p_customer
     limit 1;
  end if;
  if arbetsyta is null then
    return null;
  end if;

  insert into public.billing_subscriptions as s (
    workspace_id, paket_id, status, stripe_customer_id, stripe_subscription_id,
    current_period_end, cancel_at_period_end, is_test, updated_at
  ) values (
    arbetsyta, p_paket, coalesce(p_status, 'none'), p_customer, p_subscription,
    p_period_end, coalesce(p_cancel, false), coalesce(p_is_test, true), now()
  )
  on conflict (workspace_id) do update set
    -- coalesce: en händelse som inte bär ett fält ska inte nolla det. Ett
    -- misslyckat kortdrag vet inte vilket paket det gällde.
    paket_id = coalesce(excluded.paket_id, s.paket_id),
    status = excluded.status,
    stripe_customer_id = coalesce(excluded.stripe_customer_id, s.stripe_customer_id),
    stripe_subscription_id = coalesce(excluded.stripe_subscription_id, s.stripe_subscription_id),
    current_period_end = coalesce(excluded.current_period_end, s.current_period_end),
    cancel_at_period_end = excluded.cancel_at_period_end,
    is_test = excluded.is_test,
    updated_at = now();

  -- Bara ett AKTIVT köp ändrar entitlementen, och bara uppåt i den meningen
  -- att den sätts till det paket kunden betalat för. Villkoret på kolumnen
  -- (005) validerar listan.
  if p_products is not null
     and array_length(p_products, 1) is not null
     and coalesce(p_status, '') in ('active', 'trialing') then
    update public.workspaces set products = p_products where id = arbetsyta;
  end if;

  return arbetsyta;
end;
$$;

revoke all on function public.stripe_synka_abonnemang(
  uuid, text, text, text, text, timestamptz, boolean, boolean, text[]
) from public;

-- BARA webbrollen. Ingen fallback till `authenticated`, till skillnad från
-- 044: en funktion som kan sätta VILKEN arbetsytas produkter som helst får
-- inte bli anropbar för en inloggad klient via ett REST-lager.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.stripe_synka_abonnemang(
      uuid, text, text, text, text, timestamptz, boolean, boolean, text[]
    ) to snajp_web;
    grant select on table public.billing_subscriptions to snajp_web;
  end if;
end $$;
