-- Demobokningar från den publika sidan.
--
-- ## Varför tabellen är SKRIVBAR men inte LÄSBAR för webbrollen
--
-- Det här är den enda ytan i produkten där en ANONYM besökare skriver till
-- databasen. Alla andra skrivvägar har en session bakom sig och skopas på
-- `app.user_id` eller `app.tenant_id`; här finns ingen sådan identitet att
-- skopa på, och policyn måste därför släppa igenom `with check (true)`.
--
-- Följden vore obehaglig om läsning också var öppen: vem som helst som hittade
-- en väg att köra en select genom webbrollen hade fått ut varje bokning med
-- namn, bolag och e-postadress. Det finns ingen SELECT-policy för snajp_web.
-- Tabellen är en brevlåda: man postar i den, man tömmer den inte.
--
-- Det är också skälet till att koden INTE använder `insert ... returning`.
-- RETURNING kräver att raden passerar en SELECT-policy, och den saknas med
-- flit. Server-actionen räknar påverkade rader i stället.
--
-- ## Varför ingen tenant_id
--
-- En demobokning kommer från någon som ännu inte är kund. Det finns ingen
-- tenant att koppla den till, och att peka den på en godtycklig hade varit att
-- lägga en främmande persons uppgifter hos ett befintligt bolag.
--
-- ## Personuppgifter
--
-- Raderna ÄR personuppgifter: namn och e-post till en fysisk person i
-- yrkesroll. Rättslig grund är berättigat intresse för B2B-kontakt, samma
-- grund som prospekteringen. `gallring`-rutinen (migration 048) är rätt ställe
-- att lägga en bortre gräns när någon bestämt hur länge en obesvarad
-- förfrågan ska sparas.
-- TODO: bekräfta med Sebbe — gallringsfrist för demo_requests.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

create table if not exists public.demo_requests (
  id          uuid primary key default gen_random_uuid(),
  namn        text not null,
  foretag     text,
  epost       text not null,
  -- Fritext och inte timestamptz. Besökaren skriver "helst tisdag förmiddag",
  -- inte en tidpunkt — och ett datumfält hade tvingat fram en precision som
  -- ändå ska bekräftas i ett svarsmejl. Riktig kalenderbokning är Cal.coms
  -- jobb; se app/boka-demo/page.tsx.
  onskad_tid  text,
  meddelande  text,
  -- Var bokningen kom ifrån, för att kunna se vilken sida som faktiskt säljer.
  kalla       text,
  status      text not null default 'ny'
              check (status in ('ny', 'kontaktad', 'bokad', 'avfard')),
  created_at  timestamptz not null default now()
);

create index if not exists demo_requests_created_idx
  on public.demo_requests (created_at desc);

alter table public.demo_requests enable row level security;

-- INSERT, och bara insert. Se resonemanget överst.
drop policy if exists demo_requests_publik_insert on public.demo_requests;
create policy demo_requests_publik_insert on public.demo_requests
  for insert to snajp_web
  with check (true);

grant insert on public.demo_requests to snajp_web;

-- Backenden läser dem när någon bygger en adminvy för förfrågningarna.
-- Rollen har ingen policy här ännu; grant utan policy ger noll rader, vilket
-- är rätt förval: den som bygger vyn får lägga policyn medvetet.
grant select on public.demo_requests to snajp_app;

comment on table public.demo_requests is
  'Demobokningar från den publika sidan. Enda anonyma skrivvägen i produkten: '
  'insert-policy utan skopning, INGEN select-policy för snajp_web. Raderna är '
  'personuppgifter — se 048 för gallring.';
