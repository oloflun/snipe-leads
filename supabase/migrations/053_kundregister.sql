-- Kundregistret: strukturerade kunduppgifter för adminfliken Kunder & Data.
--
-- ## Varför tabellerna behövs
--
-- Kundens organisationsnummer har hittills bara funnits som en fritextrad i
-- affärskontexten ("Organisationsnummer: …", skriven av onboardingen), och
-- fakturaadress, telefon och avtalsdatum har inte funnits alls. En manuell
-- faktureringsrutin behöver dem på ett ställe där de går att läsa maskinellt
-- och rätta för hand — inte inbakade i en prompttext som agenten äger.
--
-- ## Vad som är automatiskt och vad som är manuellt
--
-- Raderna här är det MANUELLA lagret. Läsvägen (admin_kunddata.py) lägger
-- härledda värden ovanpå: kund-sedan-datumet faller tillbaka på
-- ss_tenants.created_at och organisationsnumret på affärskontextens
-- fritextrad, tills någon skrivit ett eget värde. Härledningen bor i koden
-- och inte i en trigger, så att svaret alltid kan tala om VAR ett värde kom
-- ifrån — ett värde som ser manuellt bekräftat ut men är en gissning är
-- precis vad ett faktureringsunderlag inte får innehålla.
--
-- ## Avtal
--
-- `avtal_signerat` är null tills någon registrerar ett datum, och det ÄR
-- statusflaggan: ett datum betyder att avtal finns, null att det inte gör
-- det. En separat boolean hade kunnat säga "avtal finns" utan datum — två
-- fält som kan säga emot varandra är ett fält för mycket.

create table if not exists public.ss_customer_details (
  tenant_id uuid primary key references public.ss_tenants(id) on delete cascade,
  orgnr text,
  faktureringsadress text,
  faktureringsmejl text,
  telefon text,
  foretagsadress text,
  -- Null => härleds ur ss_tenants.created_at i läsvägen.
  kund_sedan date,
  -- Null => inget avtal registrerat. Ett datum = avtal finns, signerat då.
  avtal_signerat date,
  updated_at timestamptz not null default now()
);

comment on table public.ss_customer_details is
  'Manuellt/automatiskt ifyllda kunduppgifter för adminfliken Kunder & Data. '
  'En rad per tenant; saknad rad betyder att bara härledda värden finns.';

create table if not exists public.ss_customer_contacts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.ss_tenants(id) on delete cascade,
  namn text not null,
  roll text,
  mejl text,
  telefon text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ss_customer_contacts_tenant_idx
  on public.ss_customer_contacts (tenant_id, created_at);

comment on table public.ss_customer_contacts is
  'Kontaktpersoner per kund, manuellt förvaltade i adminfliken Kunder & Data.';

-- ## Åtkomst
--
-- Samma mönster som adminläsningarna i 029: snajp_app får bara röra raderna
-- när INGEN tenant-kontext är satt. Varje kundvänd kodväg sätter kontexten
-- via _scoped(), så registret är oåtkomligt därifrån per konstruktion — den
-- enda vägen in är admin-routern, som i sin helhet ligger bakom
-- require_master_key. snajp_web får inga rättigheter alls: webben går via
-- backendens API, aldrig direkt mot registret.

alter table public.ss_customer_details enable row level security;
alter table public.ss_customer_contacts enable row level security;

do $$
declare
  t text;
begin
  foreach t in array array['ss_customer_details', 'ss_customer_contacts'] loop
    execute format('drop policy if exists %I on public.%I', t || '_admin_only', t);
    execute format(
      'create policy %I on public.%I for all to snajp_app '
      'using (nullif(current_setting(''app.tenant_id'', true), '''') is null) '
      'with check (nullif(current_setting(''app.tenant_id'', true), '''') is null)',
      t || '_admin_only', t
    );
  end loop;
end $$;

grant select, insert, update, delete on table public.ss_customer_details to snajp_app;
grant select, insert, update, delete on table public.ss_customer_contacts to snajp_app;
