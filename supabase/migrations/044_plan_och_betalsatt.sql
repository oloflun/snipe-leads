-- Kunden byter paket själv, och kopplar ett betalsätt.
--
-- ## Varför en RPC och inte en UPDATE-policy på `workspaces`
--
-- `workspaces` har EN policy och den är `for select` (000_base_schema.sql).
-- Det uppenbara vore att lägga till `for update` scopad på arbetsytan — och
-- det vore fel, för en UPDATE-policy gäller RADEN, inte kolumnen. Med den på
-- plats kan vilken medlem som helst skriva `slug`, och slug är det som binder
-- arbetsytan till en backend-tenant (`requireSnajpTenant`). En kund hade
-- alltså kunnat peka sin arbetsyta på en ANNAN kunds inkorg och kunskapsbas
-- genom att ändra en sträng.
--
-- Funktionen nedan skriver en kolumn och bara en. Det är hela skälet till att
-- den finns.
--
-- ## Varför den inte tar ett workspace_id
--
-- Ett id i signaturen är ett id anroparen väljer, och då måste funktionen
-- själv bevisa att anroparen får röra just det. Genom att härleda arbetsytan ur
-- `app.user_id` finns det ingen parameter att förfalska.

create or replace function public.set_workspace_products(nya text[])
returns text[]
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $$
declare
  anvandare uuid := nullif(current_setting('app.user_id', true), '')::uuid;
  arbetsyta uuid;
  resultat text[];
begin
  if anvandare is null then
    raise exception 'ingen inloggad användare';
  end if;

  select workspace_id into arbetsyta from public.profiles where id = anvandare;
  if arbetsyta is null then
    raise exception 'användaren saknar arbetsyta';
  end if;

  -- Villkoret finns redan på kolumnen (005). Kontrollen upprepas här för att
  -- felet ska bli begripligt: ett check-brott från djupet av en UPDATE säger
  -- "workspaces_products_valid", vilket inte hjälper den som skickade fel lista.
  if nya is null or array_length(nya, 1) is null then
    raise exception 'en arbetsyta måste ha minst en produkt';
  end if;
  if not (nya <@ array['leads', 'support']::text[]) then
    raise exception 'okänd produkt i listan';
  end if;

  update public.workspaces
     set products = nya
   where id = arbetsyta
  returning products into resultat;

  return resultat;
end;
$$;

-- Migration 018 återkallade execute på public för alla funktioner. Utan det
-- här gruntet svarar RPC:n "permission denied" — och det felet ser ut som ett
-- RLS-problem, vilket är fel ställe att leta på.
revoke all on function public.set_workspace_products(text[]) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.set_workspace_products(text[]) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.set_workspace_products(text[]) to authenticated;
  end if;
end $$;

comment on function public.set_workspace_products(text[]) is
  'Byter arbetsytans paket. Skriver EN kolumn — se filens docstring om varför '
  'en UPDATE-policy på workspaces hade öppnat slug för skrivning.';

-- ---------------------------------------------------------------------------
-- Betalsätt
--
-- ## Vad som INTE får hamna här, och varför tabellen ser ut som den gör
--
-- Inget kortnummer. Ingen CVC. Inget som liknar ett kortnummer. Kolumnerna är
-- exakt det en riktig betalväxel lämnar TILLBAKA efter att den tagit hand om
-- kortet — märke, fyra sista, giltighetstid och en referens hos leverantören —
-- och det är också allt som behövs för att rita "Visa •••• 4242" i en
-- inställningsvy.
--
-- Formen är alltså inte en förenkling av det riktiga. Den ÄR det riktiga; det
-- som saknas är växeln, inte fälten.
--
-- ## `is_test`
--
-- Sant så länge inga skarpa nycklar är konfigurerade. Kolumnen finns för att
-- den dagen riktiga betalningar slås på ska raderna från testperioden gå att
-- skilja ut och rensa — utan den är den enda skillnaden mellan ett riktigt och
-- ett låtsat betalsätt vad någon minns.

create table if not exists public.billing_payment_methods (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  -- Leverantören som äger kortet. 'simulerad' = ingen växel inkopplad ännu.
  provider text not null default 'simulerad',
  -- Betalväxelns egen referens (pm_… hos Stripe). Det är DEN som debiteras,
  -- aldrig något vi lagrar om kortet.
  provider_ref text,
  brand text not null,
  last4 text not null check (last4 ~ '^[0-9]{4}$'),
  exp_month smallint not null check (exp_month between 1 and 12),
  exp_year smallint not null check (exp_year between 2020 and 2100),
  is_test boolean not null default true,
  created_at timestamptz not null default now()
);

-- Ett betalsätt per arbetsyta. Fler kort är en riktig funktion med ett
-- standardval, en borttagningsregel och en fråga om vad som händer med
-- prenumerationen när det valda kortet försvinner. Inget av det finns, och ett
-- index som TILLÅTER två rader hade betytt att vyn tyst visar den första.
create unique index if not exists billing_payment_methods_workspace_uniq
  on public.billing_payment_methods (workspace_id);

comment on table public.billing_payment_methods is
  'Kortets METADATA, aldrig kortet. Inget PAN och ingen CVC får lagras här — '
  'kolumnerna speglar vad en betalväxel returnerar efter tokenisering.';

alter table public.billing_payment_methods enable row level security;

drop policy if exists "workspace scoped payment methods" on public.billing_payment_methods;
create policy "workspace scoped payment methods"
on public.billing_payment_methods for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());
