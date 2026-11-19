-- Multi-tenant: en kund = ett workspace + en ss_tenant, i samma kodbas.
--
-- Alternativet var att kopiera repot per kund. Det hade inneburit att varje
-- buggfix måste göras på N ställen, och att en kund som glöms bort blir kvar på
-- en gammal, trasig version. Här kostar kund nummer tre en rad i databasen och
-- en configfil.
--
-- Körs efter 005 och 006. Idempotent.

alter table public.workspaces
  add column if not exists slug text,
  add column if not exists ss_tenant_id uuid references public.ss_tenants(id);

-- Delvis unikt index: bara workspaces med egen sajt har slug, resten är NULL
-- och NULL krockar inte med sig självt i ett vanligt unique-index ändå — men
-- predikatet gör avsikten explicit.
create unique index if not exists workspaces_slug_key
  on public.workspaces (slug) where slug is not null;

comment on column public.workspaces.slug is
  'Subdomänen som identifierar kunden, t.ex. livrustning → livrustning.<domän>. NULL = ingen egen sajt.';
comment on column public.workspaces.ss_tenant_id is
  'Kopplar dashboardens workspace till supportagentens tenant i ss_tenants.';

-- Livrustning AB: tenant för supportagenten + workspace för dashboarden.
insert into public.ss_tenants (slug, name)
values ('livrustning', 'Livrustning AB')
on conflict (slug) do update set name = excluded.name;

insert into public.workspaces (name, slug, ss_tenant_id, products)
select 'Livrustning AB', 'livrustning', t.id, array['leads', 'support']
from public.ss_tenants t
where t.slug = 'livrustning'
  and not exists (select 1 from public.workspaces w where w.slug = 'livrustning');
