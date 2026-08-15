-- Plattformsadmin som en EGEN dimension.
--
-- `profiles.role` ('owner'/'member') finns redan, men den är workspace-scopad:
-- den säger vad någon får göra inuti sin egen arbetsyta. En plattformsroll är
-- något annat — den ger läsning ÖVER alla kunder. Att belasta samma kolumn med
-- båda betydelserna hade gjort "owner" tvetydigt, och den dagen någon gör en
-- kund till owner av sitt eget workspace hade de blivit plattformsadmin.
--
-- Två dimensioner, två tabeller.

create table if not exists public.platform_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  granted_by uuid references auth.users(id) on delete set null,
  granted_at timestamptz not null default now()
);

alter table public.platform_admins enable row level security;

-- Läsbar bara av den som själv står i tabellen. En admin ser alltså listan;
-- alla andra ser en tom tabell, inte ett fel — vem som är admin är i sig
-- information vi inte behöver läcka.
drop policy if exists platform_admins_self_read on public.platform_admins;
create policy platform_admins_self_read on public.platform_admins
  for select to authenticated
  using (exists (select 1 from public.platform_admins pa where pa.user_id = auth.uid()));

-- INGA skrivpolicyer. Med RLS på och ingen insert/update/delete-policy kan
-- varken anon eller authenticated skriva hit — admin ges enbart via
-- service_role eller SQL-editorn. En självbetjäningsväg in i admin är exakt
-- det den här tabellen finns för att förhindra.
