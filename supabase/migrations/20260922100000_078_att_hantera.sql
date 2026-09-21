-- 078: Status 'att_hantera' — eskaleringslarm och notiser från Snajp.
--
-- ## Felet
--
-- Snajps prioriterade mejl ("[PRIORITERAT] Supportärende eskalerat — …",
-- app/notifications/prioriterat_mejl.py) skickas till snajpsupport@gmail.com.
-- Samma adress är snajp-arbetsytans kopplade inkorg, så "Synka inkorg"
-- hämtade in larmen som KUNDMEJL: de triagerades, eskalerades och fick ett
-- AI-utkast med ett svar till Snajp på vårt eget larm (kundtest 2026-09-22;
-- 14 sådana rader i produktion vid mätningen). Ett larm är en uppgift för en
-- människa, inte ett ärende att besvara.
--
-- ## Lösningen
--
-- En egen status. Processorn känner igen notisen (ämnesprefixet OCH
-- avsändarraden i brödtexten, se processor.ar_snajp_notis) och sätter
-- 'att_hantera' utan att köra triage eller skriva utkast. Inkorgens
-- huvudlista utesluter statusen; fliken "Att hantera" visar bara den.
--
-- Status och inte en flagga: listningen filtrerar redan på status, och en
-- rad som är ett larm ska aldrig samtidigt kunna vara 'awaiting_approval'.

alter table public.ss_emails drop constraint if exists ss_emails_status_check;
alter table public.ss_emails add constraint ss_emails_status_check check (status in (
  'new', 'processing', 'awaiting_approval', 'auto_sent', 'sent',
  'escalated', 'rejected', 'taken_over', 'failed', 'att_hantera'
));

-- Befintliga larm som redan hämtats in som kundärenden. Samma igenkänning
-- som koden: båda villkoren måste träffa, så ett kundmejl som råkar börja
-- med [PRIORITERAT] påverkas inte.
with larm as (
  select id from public.ss_emails
   where subject like '[PRIORITERAT]%'
     and body_text like '%Det här mejlet kommer från Snajp%'
)
update public.ss_drafts d
   set status = 'rejected'
  from larm
 where d.email_id = larm.id
   and d.status = 'pending';

update public.ss_emails
   set status = 'att_hantera'
 where subject like '[PRIORITERAT]%'
   and body_text like '%Det här mejlet kommer från Snajp%';
