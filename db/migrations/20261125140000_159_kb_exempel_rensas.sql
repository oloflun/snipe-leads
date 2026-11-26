-- 159: exempelartiklarna i testarbetsytorna märks och rensas.
--
-- Anton 2026-11-25: "se till att gamla exempelartiklar tas bort automatiskt
-- när kunskapsbasen fylls på" (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 4).
--
-- Kolumnen is_placeholder finns sedan 20260730204754 men lästes och skrevs
-- aldrig. Från och med nu sätter BARA seedningen av exempelbasen
-- (seed_kb.ensure_tenant_kb) den, och lagringslagret raderar tenantens
-- exempelrader i samma transaktion som kundens eget innehåll kommer in
-- (add_kb_article, lagg_till_kb_forslag).
--
-- Den här migrationen tar hand om raderna som redan finns:
--   1. En rad märks när tenantens slug börjar på 'testkund-', rubriken finns
--      i exempellistan (app/kb_articles.py: KB_ARTICLES, inskriven här
--      eftersom en migration inte läser Python) och embedding är null, som
--      ensure_tenant_kb alltid lämnar den.
--   2. Märkta rader raderas i de tenants som redan har eget innehåll: en
--      omärkt artikel, eller ett förslag som lagts till.
--
-- Tenanter som inte är testarbetsytor rörs aldrig: Snajps egen bas, hjälpens
-- bas och Nordlys Handels egen bas (demo-tenanten) märks inte.
--
-- Additiv och idempotent: kolumnen läggs bara till om den saknas, märkningen
-- hoppar över märkta rader och raderingen hittar inget andra gången.

alter table public.ss_knowledge_base
  add column if not exists is_placeholder boolean not null default false;

update public.ss_knowledge_base k
   set is_placeholder = true
  from public.ss_tenants t
 where t.id = k.tenant_id
   and t.slug like 'testkund-%'
   and not k.is_placeholder
   and k.embedding is null
   -- Den exakta rubriken först: ensure_tenant_kb skriver KB_ARTICLES-rubriken
   -- oförändrad. lower() viker inte Å/Ä/Ö under C-kollation, så gemenlistan
   -- nedan ensam missar tre rubriker där.
   and (btrim(k.title) in (
    'Inloggningsproblem och återställning av lösenord',
    'Felkoder i kassan (E-101, E-204, E-500)',
    'Appen eller webbplatsen fungerar inte som den ska',
    'Leveranstider och fraktalternativ',
    'Försenat eller försvunnet paket',
    'Ändra leveransadress på en lagd beställning',
    'Betalningsmetoder vi accepterar',
    'Dubbeldragning eller felaktig debitering',
    'Faktura från Klarna — förfallodatum och påminnelser',
    'Så gör du en retur',
    'Reklamation av skadad eller defekt vara',
    'Ångra eller ändra en beställning',
    'Orderstatus och orderbekräftelse',
    'Uppdatera kontouppgifter och adress',
    'Radera konto och personuppgifter (GDPR)',
    'Nyhetsbrev och kampanjkoder',
    'Om Nordlys Handel',
    'Öppettider och kontaktvägar',
    'Garanti: hur länge den gäller och vad den täcker',
    'Utbildning och introduktion för företagskunder',
    'Ombud eller hemleverans',
    'Kvitto och faktura för bokföringen',
    'Garanti efter reparation eller utbyte',
    'Garanti vid köp hos återförsäljare',
    'Utbildningens upplägg: på plats eller digitalt',
    'Förberedelser inför en utbildning',
    'Ändra eller komplettera en lagd order',
    'Vad orderstatusen betyder'
   ) or lower(btrim(k.title)) in (
    'inloggningsproblem och återställning av lösenord',
    'felkoder i kassan (e-101, e-204, e-500)',
    'appen eller webbplatsen fungerar inte som den ska',
    'leveranstider och fraktalternativ',
    'försenat eller försvunnet paket',
    'ändra leveransadress på en lagd beställning',
    'betalningsmetoder vi accepterar',
    'dubbeldragning eller felaktig debitering',
    'faktura från klarna — förfallodatum och påminnelser',
    'så gör du en retur',
    'reklamation av skadad eller defekt vara',
    'ångra eller ändra en beställning',
    'orderstatus och orderbekräftelse',
    'uppdatera kontouppgifter och adress',
    'radera konto och personuppgifter (gdpr)',
    'nyhetsbrev och kampanjkoder',
    'om nordlys handel',
    'öppettider och kontaktvägar',
    'garanti: hur länge den gäller och vad den täcker',
    'utbildning och introduktion för företagskunder',
    'ombud eller hemleverans',
    'kvitto och faktura för bokföringen',
    'garanti efter reparation eller utbyte',
    'garanti vid köp hos återförsäljare',
    'utbildningens upplägg: på plats eller digitalt',
    'förberedelser inför en utbildning',
    'ändra eller komplettera en lagd order',
    'vad orderstatusen betyder'
   ));

delete from public.ss_knowledge_base k
 using public.ss_tenants t
 where t.id = k.tenant_id
   and t.slug like 'testkund-%'
   and k.is_placeholder
   and (
     exists (
       select 1 from public.ss_knowledge_base e
        where e.tenant_id = k.tenant_id and not e.is_placeholder
     )
     or exists (
       select 1 from public.ss_kb_forslag f
        where f.tenant_id = k.tenant_id and f.status = 'tillagd'
     )
   );
