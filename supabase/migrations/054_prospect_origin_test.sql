-- Testkörningar ska kunna märka sina egna prospekt, precis som exempelbolag gör.
--
-- BAKGRUND: `prospects.origin` (migration 039) skiljer redan påhittade bolag
-- ('example') från riktiga ('manual'), och send-guarden läser kolumnen innan
-- provider.send(). En testkörning som skapar ett prospekt hade tidigare inget
-- eget värde att sätta — raden landade som 'manual' och gick inte att skilja
-- från en riktig kunds bolag, varken i portföljräkningen eller i utskicksspärren.
--
-- 'test' fyller samma roll för egna provkörningar som 'example' fyller för
-- exempelbolag: send_guard (app/leads/scheduler.py) blockerar den innan
-- provider.send() på samma sätt.
--
-- VARFÖR NOT VALID + VALIDATE I STÄLLET FÖR EN VANLIG ALTER: 039 varnar redan
-- om att en ALTER på ett check-villkor låser tabellen medan varje befintlig
-- rad valideras. `prospects` är den tabell send-guarden läser för VARJE
-- utskick, så en låsning där är precis den tabell man minst vill låsa i drift.
-- DROP + ADD ... NOT VALID lägger till villkoret utan att skanna tabellen,
-- och VALIDATE CONSTRAINT gör skanningen som ett eget steg.

alter table public.prospects
  drop constraint if exists prospects_origin_check;

alter table public.prospects
  add constraint prospects_origin_check
    check (origin in ('manual', 'example', 'import', 'test')) not valid;

alter table public.prospects
  validate constraint prospects_origin_check;

comment on column public.prospects.origin is
  'manual = kunden eller agenten lade in bolaget. example = påhittat '
  'exempelbolag ur ICP:t, får ALDRIG mejlas (blockeras i send_guard). '
  'import = kom in via en filimport. test = skapat av en egen provkörning, '
  'får ALDRIG mejlas (blockeras i send_guard, samma spärr som example).';
