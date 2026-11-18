-- Betalstatus på underlaget — skillnaden mellan ett kvitto och en obetald faktura.
--
-- ## Varför kolumnen behövs
--
-- Avläsningen läste sex fält (datum, motpart, brutto, momssats, riktning,
-- kategori) och INGET av dem sa om underlaget var betalt. Följden var att
-- `bygg_inkopsverifikat` alltid krediterade 1930 Företagskonto och
-- `bygg_forsaljningsverifikat` alltid debiterade 1930: en leverantörsfaktura
-- med 30 dagars betalningsvillkor bokfördes som om pengarna redan lämnat
-- kontot. Skulden på 2440 uppstod aldrig, och kundfordran på 1510 likaså.
--
-- Båda kontona fanns i kontoplanen sedan 045 utan att någon kodväg nådde dem,
-- och app/bookkeeping/kunskap.py talade samtidigt om för kunden att
-- leverantörsskulder hör hemma på 2440 — alltså sa chatten en sak och motorn
-- gjorde en annan.
--
-- ## Varför befintliga rader backfyllas till 'betald'
--
-- Kolumnen blir ett KRÄVT fält i verifieringsgrinden (KRAVDA_FALT). Utan
-- backfill hade varje historiskt underlag saknat fältet, alltså hade varje
-- redan avslutad periodrapport hoppat från `klar` till `granska_manuellt` i
-- samma sekund som den här migrationen kördes.
--
-- 'betald' är inte en gissning här utan en AVSKRIFT av vad som faktiskt
-- hände: raderna konterades av den gamla koden mot 1930, och 1930 ÄR
-- betald-grenen. Backfillen skriver alltså ned det verifikaten redan säger.
-- Nya rader får ingen default — de måste bära en riktig avläsning, annars
-- fäller grinden dem till granskning.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

alter table public.bk_underlag
  add column if not exists betalstatus text;

-- Backfill FÖRE check-villkoret: annars fäller villkoret på de nullrader som
-- redan ligger där.
update public.bk_underlag
   set betalstatus = 'betald'
 where betalstatus is null;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'bk_underlag_betalstatus_check'
  ) then
    alter table public.bk_underlag
      add constraint bk_underlag_betalstatus_check
      check (betalstatus is null or betalstatus in ('betald', 'obetald'));
  end if;
end $$;

-- Nullbar med flit, precis som syskonfälten: ett underlag grinden fällt ska gå
-- att spara med hål i, annars finns ingen granskningskö att fylla. Se
-- kommentaren över tabellen i 045.
comment on column public.bk_underlag.betalstatus is
  'betald = pengarna har lämnat/nått kontot (1930). obetald = leverantörsskuld '
  '(2440) respektive kundfordran (1510). null = avläsningen kunde inte avgöra, '
  'och grinden skickar underlaget till manuell granskning.';
