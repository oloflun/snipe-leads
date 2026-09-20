-- Unik spärr på verifikatnummer per tenant och serie (snipe-a4y).
--
-- Verifikatnumret räknades som len(list_bk_verifikat())+1 i tre API-vägar,
-- utan unikt index. Två samtidiga uppladdningar inom samma tenant kunde läsa
-- samma längd och skriva SAMMA nummer — ett dubblerat verifikatnummer är en
-- värre revisionsanmärkning än ett hoppat, och SIE-exporten blir tvetydig.
--
-- Koden är samtidigt omlagd: create_bk_verifikat(nummer=None) räknar nästa
-- lediga i själva insert-satsen och försöker om vid kollision. Indexet är
-- spärren som gör omtaget möjligt.
--
-- Kontrollen först: finns redan dubbletter ska migrationen falla med besked,
-- inte tyst döpa om bokföringsposter. Omnumrering av ett verifikat är en
-- åtgärd en människa ska besluta om, med SIE-exporten framför sig.
do $$
declare
  dubblett record;
begin
  select tenant_id, serie, nummer, count(*) as antal
    into dubblett
    from public.bk_verifikat
   group by tenant_id, serie, nummer
  having count(*) > 1
   limit 1;
  if found then
    raise exception
      'bk_verifikat har redan dubbla nummer (tenant %, serie %, nummer %, % rader). '
      'Red ut dem för hand innan indexet läggs — omnumrering är ett bokföringsbeslut.',
      dubblett.tenant_id, dubblett.serie, dubblett.nummer, dubblett.antal;
  end if;
end $$;

create unique index if not exists bk_verifikat_tenant_serie_nummer_key
  on public.bk_verifikat (tenant_id, serie, nummer);

-- Verifiering efter körning:
--   select indexdef from pg_indexes
--   where tablename = 'bk_verifikat' and indexname = 'bk_verifikat_tenant_serie_nummer_key';
