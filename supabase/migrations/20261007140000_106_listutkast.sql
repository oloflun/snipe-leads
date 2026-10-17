-- 106: Utkast på listraden (Sebbe 2026-10-07: "Bygg utkast till listan Utan
-- webbplats också").
--
-- Listspårets bolag (regel 8 i CLAUDE.md) får ett utkast med kundens
-- generella erbjudande (app/leads/listutkast.py). Utkastet sparas på raden
-- tills kunden lagt in en mejladress som tillhör VD; då köas det med
-- signatur och lagstadgad fot och syns i granskningskön som alla andra.
--
-- utkast: {"subject", "body", "skrivet_at", "anmarkning"?, "queue_item_id"?,
--          "prospect_id"?}. NULL = inget utkast skrivet.
--
-- Kolumnen omfattas av tabellens befintliga RLS-policy (tenant_isolation,
-- migration 060) och snajp_app:s update-grant. Idempotent.

alter table public.lead_list_items
  add column if not exists utkast jsonb;
