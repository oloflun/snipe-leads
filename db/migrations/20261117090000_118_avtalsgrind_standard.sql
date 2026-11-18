-- Avtalsgrinden blir standard för NYA tenants (INV-AVTAL-001).
--
-- Snajp är personuppgiftsbiträde åt sina kunder och får enligt GDPR art. 28
-- inte behandla en kunds personuppgifter utan biträdesavtal. Migration 070
-- gjorde grinden opt-in, så en ny kund fick trafik om ingen kom ihåg att slå
-- på flaggan. Från och med nu är det skyddande valet standard: en tenant som
-- skapas utan att ange kolumnen kräver registrerat avtal.
--
-- BEFINTLIGA rader rörs inte. Att byta standardvärde ändrar ingen rad, och
-- här finns med flit ingen update: befintliga kunder, demotenants och interna
-- tenants behåller sitt värde, annars hade levande trafik stängts av i samma
-- sekund som migrationen kördes. Test-, demo- och interna ytor som skapas
-- framåt anger false uttryckligen (POST /api/keys, fältet kraver_avtal).
--
-- Idempotent: att sätta samma standardvärde igen är en no-op.

alter table ss_tenants
  alter column kraver_avtal set default true;

comment on column ss_tenants.kraver_avtal is
  'Avtalsgrind, på för nya tenants sedan migration 118: true = publika ytor (chatt, inkommande mejl, kanaler) vägrar trafik tills ss_customer_details.avtal_signerat bär ett datum. false bara för test-, demo- och interna tenants, eller när plattformsadmin stänger av den i Kunder & Data. Se app/avtalsgrind.py.';
