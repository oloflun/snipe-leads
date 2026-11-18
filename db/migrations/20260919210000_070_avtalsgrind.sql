-- Avtalsgrinden (Livrustning-piloten): en tenant som kräver signerat avtal
-- får inte ta emot riktig kundtrafik förrän avtalet är registrerat.
--
-- ## Varför en egen kolumn och inte "gäller alla"
--
-- `ss_customer_details.avtal_signerat` (migration 053) finns redan och ÄR
-- statusen — men befintliga kunder i drift saknar ofta raden helt, och en
-- global grind hade stängt av deras trafik i samma sekund som migrationen
-- kördes. Grinden är därför opt-in per tenant: `kraver_avtal = true` betyder
-- att publika ytor (chatt, inkommande mejl, kanaler) vägrar tills ett datum
-- står i `avtal_signerat`. Läsvägen är app/avtalsgrind.py; admin registrerar
-- datumet i fliken Kunder & Data precis som förut.
--
-- Livrustning sätts direkt: piloten är hela anledningen till kolumnen, och
-- DPA:t är inte signerat när det här skrivs (2026-09-19).

alter table ss_tenants
  add column if not exists kraver_avtal boolean not null default false;

comment on column ss_tenants.kraver_avtal is
  'Opt-in-grind: true = publika ytor vägrar trafik tills ss_customer_details.avtal_signerat bär ett datum. Se app/avtalsgrind.py.';

update ss_tenants set kraver_avtal = true where slug = 'livrustning';
