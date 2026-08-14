-- SOUL: kundens eget röst- och tondokument.
--
-- Nytt `kind` på agent_context_docs i stället för en ny tabell. Versionering
-- (version int), RLS-policyn från 010 och storage.get_latest_context_doc
-- finns redan och gäller då automatiskt — en egen tabell hade krävt att allt
-- det byggdes om, och att RLS-policyn skrevs en gång till (vilket är precis
-- hur en tenant-läcka uppstår).
--
-- SOUL skiljer sig från de tre befintliga sorterna på ett sätt som INTE syns
-- i schemat och därför måste stå här: de andra är skrivna av oss eller av
-- onboarding-agenten. SOUL är skriven av KUNDEN. Den läses därför alltid
-- genom app/leads/soul.render_soul, som wrappar den som opålitligt innehåll
-- och placerar den i användarposition — aldrig i systemprompten (INV-SEC-009).

alter table agent_context_docs
  drop constraint if exists agent_context_docs_kind_check;

alter table agent_context_docs
  add constraint agent_context_docs_kind_check
  check (kind in ('product_marketing', 'customer_research', 'retention_playbook', 'upload', 'soul'));
