-- Kontaktinsamlingens fallback-trappa (INV-CONTACT-001) behöver en plats att
-- landa VILKEN nivå som träffades, inte bara adressen.
--
-- Bakgrund: leads-agenten hittade nästan aldrig en kontaktperson, eftersom
-- `hitta_bolag()`s prompt gjorde contact_email frivilligt och `contact_name`
-- (som fanns i schemat sedan migration 010) aldrig fylldes i från
-- sökträffarna. Kunden bad uttryckligen om en trappa: namngiven person i den
-- sökta rollen → annan namngiven beslutsfattare → rollbaserad adress på egen
-- domän → kontaktformulärets URL som sista utväg.
--
-- UI:t och utkastet kan bara vara ärliga om säkerheten i kontaktuppgiften om
-- NIVÅN som träffades går att läsa tillbaka — inte bara om ett namn eller en
-- adress råkar finnas. Utan den här kolumnen hade "en gissad adress" och
-- "en verifierad rollpost" sett identiska ut i databasen.
--
-- Fälten är alla nullbara: en körning som bara hittar en webbplats och inget
-- annat ska fortfarande skapa prospektet (se resonemanget i migration 031).

alter table public.prospects
  add column if not exists contact_role text,
  add column if not exists contact_level text
    check (contact_level is null or contact_level in
      ('named_role_match', 'named_other', 'role_address', 'contact_form')),
  add column if not exists contact_form_url text;

comment on column public.prospects.contact_role is
  'Rollen/titeln kontakten hittades i (t.ex. "VD", "Marknadschef"), eller '
  'lokaldelen av en rollbaserad adress (t.ex. "info"). Fritext, aldrig gissad '
  '— null när ingen roll kunde verifieras.';

comment on column public.prospects.contact_level is
  'Vilken nivå i fallback-trappan som träffades. named_role_match = namngiven '
  'person i den ICP-sökta rollen. named_other = annan namngiven '
  'beslutsfattare. role_address = info@/kontakt@/hej@/sales@ på bolagets egen '
  'domän. contact_form = ingen adress hittades, bara kontaktformulärets URL. '
  'Styr hur säkert UI:t och utkastet får framställa kontaktuppgiften.';

comment on column public.prospects.contact_form_url is
  'Bolagets kontaktformulär, satt BARA när contact_level=contact_form (ingen '
  'e-postadress kunde verifieras). Sista utvägen i trappan, inte ett '
  'förstahandsval.';

-- OBS DEPLOYORDNING (samma mönster som migration 031/039): koden som skriver
-- till de här kolumnerna deployas från grenen, migrationen körs separat av
-- en människa med databaslösenordet via
-- `python scripts/railway_migrate.py --env development --apply`. Kör den
-- INNAN koden som sätter contact_role/contact_level/contact_form_url når
-- produktion eller den speglade development-databasen — annars fäller
-- create_prospect/update_prospect för alla icke-manuella ursprung
-- (origin='import'/'test'), av samma skäl som INV-DATA-001-fallbacken i
-- app/storage/postgres.py redan förklarar för `origin`-kolumnen.
