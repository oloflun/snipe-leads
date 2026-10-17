-- 102: Kundens egna önskemål till sin agent (fas 8, 2026-10-06).
--
-- Kunden skriver feedback med egna ord, den bakas in i kundens eget dokument
-- (app/leads/onskemal.py) och sparas som en ny version per gång. Dokumentet
-- läses i ANVÄNDARposition, inslaget som opålitligt innehåll (INV-SEC-009),
-- precis som röstdokumentet (`soul`, migration 017) — därför ett nytt kind på
-- samma tabell och ingen ny tabell.
--
-- Idempotent.

alter table public.agent_context_docs
  drop constraint if exists agent_context_docs_kind_check;
alter table public.agent_context_docs
  add constraint agent_context_docs_kind_check
  check (kind in (
    'product_marketing', 'customer_research', 'retention_playbook', 'upload', 'soul',
    'kundonskemal_leads', 'kundonskemal_support'
  ));
