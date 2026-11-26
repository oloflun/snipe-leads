-- 165: Snajp CRM, relationen "ej aktuell", förlustorsak ur en lista och
-- källa och insamlingsdag på personen.
--
-- Antons beslut 2026-11-27 (docs/crm/SVENSK-STANDARD.md § 4, alla enligt
-- förslaget):
--
-- 1. crm_bolag.relation får ett sjunde värde, 'ej_aktuell'. Det skiljer ett
--    bolag som sagt nej, eller som inte passar, från ett prospekt. Ett sådant
--    bolag är INTE fritt för Iris: bara 'tidigare_kund' är fri
--    (app/crm/lagring.py: FRIA_RELATIONER). Check-villkoret från 160 byts.
-- 2. crm_affarer.forlustorsak_kod: förlustorsaken ur en fast lista, så att den
--    går att räkna på. Fritexten forlustorsak (164) står kvar som reserv och
--    får sättas tillsammans med vilken kod som helst. Status "Uppskjuten"
--    byggs inte (väntar enligt beslutet).
-- 3. crm_personer.kalla_typ, kalla_namn och insamlad_at: varifrån uppgiften
--    om personen först kom, och när. GDPR art. 14.2 f kräver att källan går
--    att ange (docs/crm/underlag/svensk-02-gdpr-nix-marknadsforing.md § 2.1).
--    Kolumnen kalla som redan finns (manuell, api, synk) rörs inte och betyder
--    något annat: vilken väg posten kom in i Snajp. kalla_typ är var
--    uppgiften kommer ifrån i världen (bolagets webbplats, ett register,
--    kunden själv). Fälten är frivilliga: befintliga rader har dem tomma, och
--    det ska gå att se vilka personer som saknar källa. En senare synk skriver
--    aldrig över en källa som redan står (app/crm/synk.py).
--
-- Inga nya tabeller: radskyddet, grants och force row level security från
-- 160 och 164 gäller de nya kolumnerna som de står. Additiv och idempotent.

-- 1. Relationen ej aktuell ------------------------------------------------

alter table public.crm_bolag drop constraint if exists crm_bolag_relation_check;
alter table public.crm_bolag add constraint crm_bolag_relation_check
  check (relation in ('kund', 'tidigare_kund', 'prospekt', 'partner', 'leverantor', 'ovrigt', 'ej_aktuell'));

-- 2. Förlustorsak ur en lista ---------------------------------------------

alter table public.crm_affarer add column if not exists forlustorsak_kod text;

alter table public.crm_affarer drop constraint if exists crm_affarer_forlustorsak_kod_check;
alter table public.crm_affarer add constraint crm_affarer_forlustorsak_kod_check
  check (forlustorsak_kod is null or forlustorsak_kod in
         ('pris', 'konkurrent', 'tidpunkt', 'inget_behov', 'ingen_budget', 'inget_svar', 'annat'));

-- Listan över förlorade affärer per orsak.
create index if not exists crm_affarer_forlustorsak_idx on public.crm_affarer (tenant_id, forlustorsak_kod)
  where forlustorsak_kod is not null;

-- 3. Källa och insamlingsdag på personen ----------------------------------

alter table public.crm_personer add column if not exists kalla_typ text;
alter table public.crm_personer add column if not exists kalla_namn text;
alter table public.crm_personer add column if not exists insamlad_at timestamptz;

alter table public.crm_personer drop constraint if exists crm_personer_kalla_typ_check;
alter table public.crm_personer add constraint crm_personer_kalla_typ_check
  check (kalla_typ is null or kalla_typ in
         ('bolagets_webbplats', 'register', 'kunden', 'synk', 'manuell', 'annan'));
alter table public.crm_personer drop constraint if exists crm_personer_kalla_namn_check;
alter table public.crm_personer add constraint crm_personer_kalla_namn_check
  check (kalla_namn is null or length(kalla_namn) <= 300);

-- Filtret på källans typ, och listan över personer som saknar källa.
create index if not exists crm_personer_kalla_typ_idx on public.crm_personer (tenant_id, kalla_typ);
