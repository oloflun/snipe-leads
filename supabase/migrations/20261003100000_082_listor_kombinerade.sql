-- 082: Kombinerade leadslistor (Antons beställning 2026-10-02).
--
-- Kunden väljer flera färdiga listor och bygger en skräddarsydd: flera
-- branscher i samma region, samma bransch i flera regioner, och ett filter på
-- kontaktväg (telefon, mejl eller båda). Den nya listan är en egen rad i
-- lead_lists med raderna kopierade (dedup på orgnr, annars bolagsnamn), så
-- källistorna står orörda och resultatet går att granska i efterhand.
--
-- kalla:  'sok' = byggd av en sökning (default, alla befintliga rader),
--         'kombinerad' = byggd ur andra listor, 'import' = uppladdad kundbas
--         (Leads Suite, senare).
-- kallistor:    källistornas id, för "Byggd av: A · B" i vyn.
-- kontaktfilter: filtret som användes vid bygget.
alter table public.lead_lists
  add column if not exists kalla text not null default 'sok'
    check (kalla in ('sok', 'kombinerad', 'import')),
  add column if not exists kallistor uuid[],
  add column if not exists kontaktfilter text
    check (kontaktfilter is null or kontaktfilter in ('alla', 'telefon', 'mejl', 'bada'));

-- Dedup vid kombinering går på orgnr; icke-unikt eftersom orgnr kan saknas.
create index if not exists lead_list_items_orgnr_idx
  on public.lead_list_items (list_id, orgnr);
