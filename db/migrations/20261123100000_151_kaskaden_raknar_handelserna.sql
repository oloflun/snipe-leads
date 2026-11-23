-- 151: gallringens tak räknar konversationernas händelser.
--
-- Migration 149 lade till lead_handelser, som försvinner med sitt prospekt
-- (och sin tråd) genom ON DELETE CASCADE. Taket i gallringen (146) räknar
-- varje rad kaskaden tar, och katalogtestet i tests/db/test_gallring.py
-- fällde den nya tabellen: ett prospekt med femtio händelser hade vägt lika
-- mycket som ett utan.
--
-- gallring_kaskad är 146 med en rad till. Händelserna räknas en gång, på
-- prospektet: varje händelse bär prospect_id, och tråden den kan peka på hör
-- till samma prospekt. Additiv och idempotent.
--
-- Känd gräns: händelsens egen tid ingår inte i prospektets senaste aktivitet
-- i gallringens urval. Det som skapar en händelse rör redan en rad som räknas
-- (ett svar, ett utkast, ett stegbyte på tråden, ett samtal), så ett prospekt
-- med färska händelser har också färsk aktivitet. Enda undantaget är att en
-- notis markeras som läst, vilket inte är en behandling av prospektet.

create or replace function public.gallring_kaskad(
  p_mejl uuid[], p_arenden uuid[], p_minne uuid[], p_kunder uuid[],
  p_prospekt uuid[], p_genererade uuid[]
)
returns jsonb
language sql
stable
set search_path = public, pg_temp
as $$
  with arenden as (
    select unnest(p_arenden) as id
    union
    select t.id from public.ss_tickets t where t.customer_id = any(p_kunder)
  ),
  utkast as (select d.id from public.ss_drafts d where d.email_id = any(p_mejl)),
  samtal as (select c.id from public.ss_conversations c where c.ticket_id in (select id from arenden)),
  tradar as (select t.id from public.outreach_threads t where t.prospect_id = any(p_prospekt)),
  demolankar as (select d.token from public.ss_demolankar d where d.thread_id in (select id from tradar))
  select jsonb_build_object(
    -- Under mejlen.
    'ss_drafts',               (select count(*) from utkast),
    'ss_human_reviews',        (select count(*) from public.ss_human_reviews r where r.draft_id in (select id from utkast)),
    'ss_email_attachments',    (select count(*) from public.ss_email_attachments a where a.email_id = any(p_mejl)),
    'ss_classifications',      (select count(*) from public.ss_classifications c where c.email_id = any(p_mejl)),
    'ss_decision_log',         (select count(*) from public.ss_decision_log l where l.email_id = any(p_mejl)),
    -- Under kunderna och ärendena.
    'ss_tickets',              (select count(*) from arenden a where a.id <> all(p_arenden)),
    'customer_memory',         (select count(*) from public.customer_memory m
                                 where m.customer_id = any(p_kunder) and m.id <> all(p_minne)),
    'ss_customer_identifiers', (select count(*) from public.ss_customer_identifiers i where i.customer_id = any(p_kunder)),
    'ss_chat_state',           (select count(*) from public.ss_chat_state s where s.customer_id = any(p_kunder)),
    'ss_channel_contacts',     (select count(*) from public.ss_channel_contacts k where k.customer_id = any(p_kunder)),
    'ss_conversations',        (select count(*) from samtal),
    'ss_messages',             (select count(*) from public.ss_messages m where m.conversation_id in (select id from samtal)),
    -- Under prospekten.
    'outreach_threads',        (select count(*) from tradar),
    'outreach_messages',       (select count(*) from public.outreach_messages m where m.thread_id in (select id from tradar)),
    'send_queue',              (select count(*) from public.send_queue q where q.thread_id in (select id from tradar)),
    'ss_demolankar',           (select count(*) from demolankar),
    'ss_demolank_handelser',   (select count(*) from public.ss_demolank_handelser h where h.token in (select token from demolankar)),
    'prospect_sources',        (select count(*) from public.prospect_sources s where s.prospect_id = any(p_prospekt)),
    'lead_samtal',             (select count(*) from public.lead_samtal s where s.prospect_id = any(p_prospekt)),
    'lead_anteckningar',       (select count(*) from public.lead_anteckningar a where a.prospect_id = any(p_prospekt)),
    'lead_uppgifter',          (select count(*) from public.lead_uppgifter u where u.prospect_id = any(p_prospekt)),
    'prospect_status_logg',    (select count(*) from public.prospect_status_logg l where l.prospect_id = any(p_prospekt)),
    -- 151: konversationernas händelser och notiser (149).
    'lead_handelser',          (select count(*) from public.lead_handelser h where h.prospect_id = any(p_prospekt)),
    -- Under kampanjutkasten.
    'email_events',            (select count(*) from public.email_events e where e.generated_email_id = any(p_genererade))
  )
$$;

revoke all on function public.gallring_kaskad(uuid[], uuid[], uuid[], uuid[], uuid[], uuid[]) from public;
