-- Inkorgsflaggor (Livrustning-piloten): offert-/prisförfrågan och
-- utbildningsintresse som egna flaggor på klassificeringen, plus en manuell
-- hanterad-markering på mejlraden.
--
-- ## Varför flaggor OCH kategori
--
-- Facket `utbildning` finns redan, men ett mejl kan höra hemma i ett annat
-- fack och ÄNDÅ vara en offertförfrågan ("vad kostar en säkerhetsdag för 40
-- personer?" är betalning/utbildning/övrigt beroende på formulering). Hela
-- Livrustnings tratt är "kontakta oss för offert", så offertflaggan är
-- pilotens viktigaste signal och får inte bero på vilket fack triagen råkade
-- välja. Flaggorna sätts av vokabulär + modell i förening — se
-- app/email_pipeline/flaggor.py.
--
-- ## hanterad_at, inte en boolean
--
-- Samma resonemang som avtal_signerat i 053: en tidsstämpel ÄR statusen.
-- Null = ohanterad, ett datum = hanterad då. Skild från `status` med flit —
-- status bär pipelinens tillstånd (utkast/eskalerad/skickad) och en
-- medarbetare ska kunna bocka av ett mejl oavsett var pipelinen lämnade det.

alter table ss_classifications
  add column if not exists offertforfragan boolean not null default false;
alter table ss_classifications
  add column if not exists utbildningsintresse boolean not null default false;

comment on column ss_classifications.offertforfragan is
  'Mejlet ber om pris/offert. Vokabulär + modellbedömning, se app/email_pipeline/flaggor.py.';
comment on column ss_classifications.utbildningsintresse is
  'Mejlet uttrycker intresse för utbildning. Facket utbildning räknas alltid hit.';

alter table ss_emails
  add column if not exists hanterad_at timestamptz;

comment on column ss_emails.hanterad_at is
  'Manuell avbockning i inkorgen. Null = ohanterad. Oberoende av status.';
