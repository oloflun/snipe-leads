-- 098: CRM-kundlistor (Sebbes beställning 2026-10-06).
--
-- Kunden (eller Snajp-admin åt kunden) laddar upp sin befintliga kundlista
-- ur sitt CRM. Den blir en egen leadslista med kalla='crm': kunden ser den
-- under Leads › Listor, men den prospekteras aldrig. Varje bolag i den, och i
-- alla andra listor, utesluts av både Iris och listbygget
-- (snajp-support/app/leads/upptagna.py), så Iris och listorna aldrig hämtar
-- samma bolag och kundens egna kunder aldrig blir leads.
--
-- Idempotent: villkoret droppas och skapas om med den nya mängden.

alter table public.lead_lists drop constraint if exists lead_lists_kalla_check;
alter table public.lead_lists
  add constraint lead_lists_kalla_check
    check (kalla in ('sok', 'kombinerad', 'import', 'crm'));

-- Uteslutningen läser alla listrader per kund vid varje sökning.
create index if not exists lead_list_items_tenant_idx
  on public.lead_list_items (tenant_id);
