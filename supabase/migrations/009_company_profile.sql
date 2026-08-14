-- Företagsprofil: fakta som BÅDA agenterna behöver om kunden.
-- Körs efter 008. Idempotent.
--
-- business_contexts har hittills bara beskrivit säljsidan (produkt, målgrupp,
-- ton, erbjudande) och används av email studio. Kundservice-agenten fick
-- ingenting alls vid registrering — den startade med default-prompten och en tom
-- kunskapsbas, vilket betyder att grundningsregeln eskalerade varenda fråga.
--
-- Kolumnerna nedan är supportsidans motsvarighet: garantier, villkor, leverans
-- och returer. De matas in i onboarding och synkas till kundens Snajp-tenant
-- (systemprompt + seedade KB-artiklar) av lib/snajp/profile.ts.
--
-- Alla kolumner är nullable och saknar default, så befintliga rader är
-- oförändrade och email studio påverkas inte.

alter table business_contexts add column if not exists company_name text;
alter table business_contexts add column if not exists guarantee text;
alter table business_contexts add column if not exists terms text;
alter table business_contexts add column if not exists delivery text;
alter table business_contexts add column if not exists returns_policy text;
alter table business_contexts add column if not exists support_email text;

-- Spårbarhet: när synkades profilen senast till supportagenten? Används av
-- onboarding-checklistan för att visa om agenten är uppdaterad med senaste
-- ändringen, i stället för att gissa.
alter table business_contexts add column if not exists support_synced_at timestamptz;

comment on column business_contexts.guarantee is
  'Garantivillkor i klartext. Blir en KB-artikel hos kundens supportagent.';
comment on column business_contexts.terms is
  'Köp- och betalningsvillkor. Blir en KB-artikel.';
comment on column business_contexts.delivery is
  'Leveranstider och frakt. Blir en KB-artikel.';
comment on column business_contexts.returns_policy is
  'Retur- och reklamationsvillkor. Blir en KB-artikel.';
comment on column business_contexts.support_synced_at is
  'Senaste lyckade synk till Snajp-tenanten (systemprompt + KB).';
