-- 146: gallringens tak räknar även raderna kaskaden tar (Codex-granskningen
-- 2026-11-20, runda 14).
--
-- Taket (GALLRING_TAK, p_tak) är skyddet mot ett felaktigt policyvärde: en
-- kund vars gallring skulle röra fler rader än taket lämnas orörd och larmar.
-- v_totalt räknade bara de valda raderna i varje kategori, men ett prospekt
-- tar sina trådar, meddelanden, köposter, demolänkar, samtal, anteckningar,
-- uppgifter, statuslogg och källor med sig genom ON DELETE CASCADE, ett ärende
-- sina konversationer och meddelanden, ett mejl sina utkast, bilagor,
-- klassningar och beslutslogg, en kund sina identifierare, chattläge och
-- kanalkontakter. Ett prospekt med hundra meddelanden räknades som en rad.
-- Torrkörningen och gallringsloggen underskattade ingreppet på samma sätt.
--
-- gallring_kaskad räknar varje barn som försvinner med sin förälder, utan att
-- räkna en rad två gånger: ett barn som också är en egen kategori (ärenden och
-- kundminne hos en raderad kund) räknas bara utöver kategorins eget urval.
-- gallra_tenant lägger summan till totalen före takprövningen i första varvet
-- och räknar om den efter andra varvet, på det som faktiskt raderas och med
-- kandidaterna låsta, och lägger varje barntabell i antal med åtgärden
-- "kaskad". Spärrlistan räknas inte: kopplingen nollas före kontakterna.
-- tests/db/test_gallring.py prövar katalogen: varje kaskad från en tabell
-- gallringen raderar ur ska stå i funktionen eller vara en egen kategori.
-- gallra_tenant är 145 med kaskaden. Additiv och idempotent.

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
    -- Under kampanjutkasten.
    'email_events',            (select count(*) from public.email_events e where e.generated_email_id = any(p_genererade))
  )
$$;

revoke all on function public.gallring_kaskad(uuid[], uuid[], uuid[], uuid[], uuid[], uuid[]) from public;

create or replace function public.gallra_tenant(
  p_tenant uuid,
  p_torrkorning boolean default true,
  p_tak integer default null,
  p_kord_av text default 'skript'
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_dagar      integer;
  v_grans      timestamptz;
  v_tomt_uuid  uuid[] := '{}';
  v_tomt_text  text[] := '{}';
  v_begr       text[];
  v_kaskad     jsonb;
  v_ws         uuid[];
  v_mejl       uuid[];
  v_arenden    uuid[];
  v_minne      uuid[];
  v_kunder     uuid[];
  v_prospekt   uuid[];
  v_listrader  uuid[];
  v_listor     uuid[];
  v_liggare    text[];
  v_lankar     text[];
  v_genererade uuid[];
  v_kontakter  uuid[];
  v_saljlista  uuid[];
  v_korningar  uuid[];
  v_feedback   uuid[];
  v_evals      uuid[];
  v_forslag    uuid[];
  v_handelser  uuid[];
  v_sidcache   text[];
  v_sedda      bigint;
  v_sparr      bigint;
  v_antal      jsonb;
  v_totalt     bigint;
  v_status     text;
  v_logg       bigint;
  v_spegel     boolean := to_regclass('public.mirror_meta') is not null;
  v_varv       integer;
  v_timeout    text;
  v_mejl_1       uuid[];
  v_arenden_1    uuid[];
  v_minne_1      uuid[];
  v_kunder_1     uuid[];
  v_prospekt_1   uuid[];
  v_listrader_1  uuid[];
  v_listor_1     uuid[];
  v_liggare_1    text[];
  v_lankar_1     text[];
  v_genererade_1 uuid[];
  v_kontakter_1  uuid[];
  v_saljlista_1  uuid[];
  v_korningar_1  uuid[];
  v_feedback_1   uuid[];
  v_evals_1      uuid[];
  v_forslag_1    uuid[];
  v_handelser_1  uuid[];
  v_sidcache_1   text[];
begin
  select dagar into v_dagar
    from public.ss_gallringspolicy
   where tenant_id = p_tenant;

  if v_dagar is null then
    -- Ingen beslutad policy: ingenting gallras. Den ofarliga defaulten (048).
    return jsonb_build_object('status', 'ingen_policy', 'tenant_id', p_tenant);
  end if;

  v_grans := now() - make_interval(days => v_dagar);

  select coalesce(array_agg(id), v_tomt_uuid) into v_ws
    from public.workspaces where ss_tenant_id = p_tenant;

  -- 138: urvalet görs två gånger. Efter första varvet låses kandidaterna och
  -- raderna deras aktivitet räknas ur (for update), och andra varvet väljer
  -- igen med en ny ögonblicksbild. Bara det båda varven valde raderas. En rad
  -- som fick aktivitet före låset syns i andra varvet och står kvar; efter
  -- låset kan ingen ny rad knytas till en kandidat (främmande nycklarna tar
  -- ett nyckellås på föräldern) och ingen låst rad ändras. Låsen gäller bara
  -- rader utan aktivitet sedan gränsen, så skrivningar hos andra kunder, och
  -- i kundens levande data, väntar aldrig på gallringen (Codex runda 6 och 7).
  -- Utan lås står: meddelanden, identifierare och demolänkarnas händelser (nya
  -- rader blockeras via föräldern, tiderna ändras aldrig), agent_evals,
  -- agent_suggestions och platform_events (bara created_at), de sedda
  -- inkommande (raderas i en sats som prövar seen_at själv) och spärrlistan
  -- (en ny rad mot en låst kontakt blockeras). Avregistreringslänken skapas
  -- med en upsert som väntar på radlåset och gör en ny token om den gamla
  -- raderats, så ett mejl får aldrig en död länk.
  -- Torrkörningen och en körning över taket väljer en gång och låser inget.
  if not p_torrkorning and current_setting('transaction_isolation') <> 'read committed' then
    raise exception 'gallra_tenant raderar bara i read committed: andra varvet ska se allt som skrivits före låset'
      using errcode = 'invalid_transaction_state';
  end if;

  for v_varv in 1..2 loop
    -- 144: adresser med aktiv begränsning av behandlingen (art. 18, 124).
    select coalesce(array_agg(distinct lower(email)), v_tomt_text) into v_begr
      from public.behandlingsbegransningar where havd_at is null;

    -- -- Urvalen. Ingenting ändras förrän alla är räknade. ----------------------
    -- 139: i en spegel väljer varje synkad tabell bara sina egna provrader,
    -- med synkens villkor (scripts/railway_synk.py:SYNK, där "false" betyder
    -- att allt synkas). De speglade raderna får main:s raderingar genom synken,
    -- och en egen radering där hade kopierats tillbaka vid nästa varv; de
    -- lokala provraderna når synken aldrig och gallras här. Villkoret står i
    -- urvalet, inte efteråt, så att beroendena mellan urvalen räknas på samma
    -- rader. tests/test_gallring_spegel.py håller villkoren lika med SYNK.

    -- Supportmejl: mejlets egen aktivitet och dess utkast.
    select coalesce(array_agg(e.id), v_tomt_uuid) into v_mejl
      from public.ss_emails e
     where e.tenant_id = p_tenant
       and (not v_spegel or (e.is_test))
       and greatest(e.created_at, e.received_at, e.updated_at, e.hanterad_at, e.behandlad_at,
             (select max(greatest(d.created_at, d.updated_at, d.behandlad_at))
                from public.ss_drafts d where d.email_id = e.id)) < v_grans
       and coalesce(lower(e.from_email), '') <> all(v_begr);

    -- Ärenden (chatt och mejl): ärendets, meddelandenas, mejlens och utkastens
    -- senaste tid. Ett ärende som ett kvarvarande mejl eller utkast pekar på,
    -- eller som är förfader till ett kvarvarande ärende, i hur många led som
    -- helst, står kvar (främmande nycklar utan kaskad; 135).
    with recursive kandidat as (
      select t.id
        from public.ss_tickets t
       where t.tenant_id = p_tenant
         and (not v_spegel or (t.is_test))
         and not exists (select 1 from public.ss_customer_identifiers i
                          where i.customer_id = t.customer_id and i.type = 'email'
                            and lower(i.value) = any(v_begr))
         and greatest(t.created_at, t.updated_at, t.behandlad_at,
               (select max(greatest(c.created_at, c.behandlad_at, m.created_at))
                  from public.ss_conversations c
                  left join public.ss_messages m on m.conversation_id = c.id
                 where c.ticket_id = t.id),
               (select max(greatest(e.created_at, e.received_at, e.updated_at, e.hanterad_at, e.behandlad_at))
                  from public.ss_emails e where e.ticket_id = t.id),
               (select max(greatest(d.created_at, d.updated_at, d.behandlad_at))
                  from public.ss_drafts d where d.ticket_id = t.id)) < v_grans
         and not exists (select 1 from public.ss_emails e
                          where e.ticket_id = t.id and e.id <> all(v_mejl))
         and not exists (select 1 from public.ss_drafts d
                          where d.ticket_id = t.id and d.email_id <> all(v_mejl))
    ),
    -- Förfäderna till varje ärende som står kvar. Startar i föräldern till ett
    -- ärende utanför urvalet och går uppåt; union stoppar en eventuell cykel.
    behall(id) as (
      select b.parent_ticket_id
        from public.ss_tickets b
       where b.parent_ticket_id is not null
         and b.id not in (select id from kandidat)
      union
      select t.parent_ticket_id
        from public.ss_tickets t
        join behall on t.id = behall.id
       where t.parent_ticket_id is not null
    )
    select coalesce(array_agg(k.id), v_tomt_uuid) into v_arenden
      from kandidat k
     where k.id not in (select id from behall);

    -- Kundminnet: varje faktum är en egen behandling.
    select coalesce(array_agg(id), v_tomt_uuid) into v_minne
      from public.customer_memory
     where tenant_id = p_tenant and greatest(created_at, behandlad_at) < v_grans
       and (not v_spegel or (false))
       and not exists (select 1 from public.ss_customer_identifiers i
                          where i.customer_id = customer_memory.customer_id and i.type = 'email'
                            and lower(i.value) = any(v_begr));

    -- Chatt- och supportkunden: när varken kunden själv, chattläget,
    -- kanalkontakten eller kundminnet rörts, och inget ärende står kvar.
    select coalesce(array_agg(c.id), v_tomt_uuid) into v_kunder
      from public.ss_customers c
     where c.tenant_id = p_tenant
       and (not v_spegel or (false))
       and not exists (select 1 from public.ss_customer_identifiers i
                          where i.customer_id = c.id and i.type = 'email'
                            and lower(i.value) = any(v_begr))
       and greatest(c.created_at, c.behandlad_at,
             (select max(i.created_at) from public.ss_customer_identifiers i
               where i.customer_id = c.id),
             (select max(greatest(s.updated_at, s.overlamnad_at, s.behandlad_at)) from public.ss_chat_state s
               where s.customer_id = c.id),
             (select max(greatest(k.created_at, k.updated_at, k.behandlad_at)) from public.ss_channel_contacts k
               where k.customer_id = c.id),
             (select max(greatest(m.created_at, m.behandlad_at)) from public.customer_memory m
               where m.customer_id = c.id)) < v_grans
       and not exists (select 1 from public.ss_tickets t
                        where t.customer_id = c.id and t.id <> all(v_arenden));

    -- Prospekten: den senaste tiden över allt som hänger på prospektet.
    select coalesce(array_agg(p.id), v_tomt_uuid) into v_prospekt
      from public.prospects p
     where p.tenant_id = p_tenant
       and (not v_spegel or (p.origin in ('test', 'example')))
       and coalesce(lower(p.contact_email), '') <> all(v_begr)
       and greatest(p.created_at, p.arkiverad_at, p.behandlad_at,
             (select max(greatest(t.created_at, t.last_inbound_at, t.svarsklass_at, t.behandlad_at))
                from public.outreach_threads t where t.prospect_id = p.id),
             (select max(greatest(coalesce(m.sent_at, m.created_at), m.leverans_at, m.kasserad_at,
                                 m.behandlad_at))
                from public.outreach_messages m
                join public.outreach_threads t on t.id = m.thread_id
               where t.prospect_id = p.id),
             (select max(greatest(q.created_at, q.scheduled_at, q.behandlad_at))
                from public.send_queue q
                join public.outreach_threads t on t.id = q.thread_id
               where t.prospect_id = p.id),
             (select max(greatest(d.created_at, d.behandlad_at, h.created_at))
                from public.ss_demolankar d
                join public.outreach_threads t on t.id = d.thread_id
                left join public.ss_demolank_handelser h on h.token = d.token
               where t.prospect_id = p.id),
             (select max(greatest(s.created_at, s.aterkom_datum::timestamptz, s.behandlad_at))
                from public.lead_samtal s where s.prospect_id = p.id),
             (select max(greatest(a.created_at, a.behandlad_at)) from public.lead_anteckningar a where a.prospect_id = p.id),
             (select max(greatest(u.created_at, u.klar_at, u.forfaller::timestamptz, u.behandlad_at))
                from public.lead_uppgifter u where u.prospect_id = p.id),
             (select max(l.created_at) from public.prospect_status_logg l where l.prospect_id = p.id),
             (select max(greatest(k.retrieved_at, k.behandlad_at)) from public.prospect_sources k where k.prospect_id = p.id),
             -- 143: listraden som pekar på prospektet ("Processa om" rör bara
             -- listraden när kontakten är oförändrad).
             (select max(greatest(i.created_at, i.processad_at, i.behandlad_at))
                from public.lead_list_items i where i.prospect_id = p.id)
           ) < v_grans;

    -- Listorna: varje rad för sig, sedan de listor som blir tomma.
    select coalesce(array_agg(id), v_tomt_uuid) into v_listrader
      from public.lead_list_items
     where tenant_id = p_tenant
       and (not v_spegel or (list_id in (select id from public.lead_lists where is_test)))
       and greatest(created_at, processad_at, behandlad_at) < v_grans
       and coalesce(lower(contact_email), '') <> all(v_begr)
       -- 142: en listrad vars prospekt står kvar (nytt utkast, svar, samtal)
       -- står också kvar; prospektets urval räknas före listradernas.
       and (prospect_id is null or prospect_id = any(v_prospekt));

    select coalesce(array_agg(l.id), v_tomt_uuid) into v_listor
      from public.lead_lists l
     where l.tenant_id = p_tenant
       and (not v_spegel or (l.is_test))
       and greatest(l.created_at, l.completed_at, l.behandlad_at) < v_grans
       and not exists (select 1 from public.lead_list_items i
                        where i.list_id = l.id and i.id <> all(v_listrader));

    -- Jobbliggaren: bara avslutade jobb (INV-JOB-002 läser pågående).
    select coalesce(array_agg(job_id), v_tomt_text) into v_liggare
      from public.leads_job_ledger
     where tenant_id = p_tenant
       and (not v_spegel or (is_test))
       and status in ('completed', 'failed')
       and greatest(created_at, updated_at, completed_at, behandlad_at) < v_grans
       and (prospect_id is null or prospect_id not in (select bp.id from public.prospects bp where lower(bp.contact_email) = any(v_begr)))
       and not public.gallring_namner_begransad(concat_ws(' ', korning::text, error), v_begr);

    -- Avregistreringslänken återanvänds för varje mejl till samma adress, så
    -- dess egen tid säger inget om när den senast skickades. Den står kvar så
    -- länge adressen finns i ett kvarvarande prospekt eller en kvarvarande
    -- listrad hos kunden.
    select coalesce(array_agg(a.token), v_tomt_text) into v_lankar
      from public.ss_avregistreringslankar a
     where a.tenant_id = p_tenant
       and greatest(a.created_at, a.anvand_at, a.behandlad_at) < v_grans
       and coalesce(lower(a.email), '') <> all(v_begr)
       and not exists (select 1 from public.prospects p
                        where p.tenant_id = p_tenant
                          and lower(p.contact_email) = lower(a.email)
                          and p.id <> all(v_prospekt))
       and not exists (select 1 from public.lead_list_items i
                        where i.tenant_id = p_tenant
                          and lower(i.contact_email) = lower(a.email)
                          and i.id <> all(v_listrader));

    -- Den gamla kampanjmodellen hänger på arbetsytan, inte på tenanten.
    select coalesce(array_agg(id), v_tomt_uuid) into v_genererade
      from public.generated_emails
     where workspace_id = any(v_ws)
       and greatest(created_at, sent_at, behandlad_at) < v_grans
       and (contact_id is null or contact_id not in
             (select bk.id from public.contacts bk where lower(bk.email) = any(v_begr)))
       and not public.gallring_namner_begransad(concat_ws(' ', subject, body), v_begr);

    select coalesce(array_agg(k.id), v_tomt_uuid) into v_kontakter
      from public.contacts k
     where k.workspace_id = any(v_ws)
       and coalesce(lower(k.email), '') <> all(v_begr)
       and greatest(k.created_at, k.behandlad_at,
             (select max(greatest(g.created_at, g.sent_at, g.behandlad_at)) from public.generated_emails g
               where g.contact_id = k.id),
             (select max(greatest(m.booked_for, m.behandlad_at)) from public.meetings m where m.contact_id = k.id)) < v_grans;

    select coalesce(array_agg(id), v_tomt_uuid) into v_saljlista
      from public.saljlista
     where workspace_id = any(v_ws)
       and greatest(created_at, updated_at, senast_kontaktad::timestamptz, behandlad_at) < v_grans
       and coalesce(lower(kontaktmail), '') <> all(v_begr)
       and not public.gallring_namner_begransad(anteckningar, v_begr);

    -- Agentloggarna: bara rader som fortfarande bär något att nolla, så att en
    -- andra körning räknar noll.
    select coalesce(array_agg(id), v_tomt_uuid) into v_korningar
      from public.agent_runs
     where tenant_id = p_tenant
       and (not v_spegel or (is_test))
       and created_at < v_grans
       and (input is not null or output is not null or grounding is not null
            or step_log <> '[]'::jsonb or prospect_id is not null or thread_id is not null)
       and (prospect_id is null or prospect_id not in (select bp.id from public.prospects bp where lower(bp.contact_email) = any(v_begr)))
       and (thread_id is null or thread_id not in
             (select bt.id from public.outreach_threads bt where bt.prospect_id in (select bp.id from public.prospects bp where lower(bp.contact_email) = any(v_begr))))
       and not public.gallring_namner_begransad(
             concat_ws(' ', input, output, step_log::text, grounding::text), v_begr);

    select coalesce(array_agg(id), v_tomt_uuid) into v_feedback
      from public.agent_feedback
     where tenant_id = p_tenant
       and created_at < v_grans
       and (comment is not null or corrected_output is not null)
       and not public.gallring_namner_begransad(concat_ws(' ', comment, corrected_output), v_begr)
       -- 145: feedbacken hör till sin körning. En körning som begränsningen
       -- skyddar (via prospektet, tråden eller löptexten) behåller sin feedback.
       and not exists (
             select 1 from public.agent_runs r
              where r.id = agent_feedback.run_id
                and (r.prospect_id in (select bp.id from public.prospects bp
                                         where lower(bp.contact_email) = any(v_begr))
                     or r.thread_id in (select bt.id from public.outreach_threads bt
                                         where bt.prospect_id in (select bp.id from public.prospects bp
                                                                   where lower(bp.contact_email) = any(v_begr)))
                     or public.gallring_namner_begransad(
                          concat_ws(' ', r.input, r.output, r.step_log::text, r.grounding::text), v_begr)));

    select coalesce(array_agg(id), v_tomt_uuid) into v_evals
      from public.agent_evals
     where tenant_id = p_tenant and created_at < v_grans
       and not public.gallring_namner_begransad(concat_ws(' ', input, approved_output), v_begr);

    select coalesce(array_agg(id), v_tomt_uuid) into v_forslag
      from public.agent_suggestions
     where tenant_id = p_tenant and created_at < v_grans
       and (not v_spegel or (false))
       and not public.gallring_namner_begransad(content::text, v_begr);

    select coalesce(array_agg(id), v_tomt_uuid) into v_handelser
      from public.platform_events
     where tenant_id = p_tenant and created_at < v_grans
       and not public.gallring_namner_begransad(concat_ws(' ', message, detail::text), v_begr);

    select coalesce(array_agg(url), v_tomt_text) into v_sidcache
      from public.leads_sidcache
     where tenant_id = p_tenant and hamtad_at < v_grans
       and not public.gallring_namner_begransad(innehall, v_begr);

    select count(*) into v_sedda
      from public.ss_channel_inbound_seen
     where tenant_id = p_tenant and seen_at < v_grans;

    if v_varv = 1 then
      v_totalt := cardinality(v_mejl) + cardinality(v_arenden) + cardinality(v_minne)
                + cardinality(v_kunder) + cardinality(v_prospekt) + cardinality(v_listrader)
                + cardinality(v_listor) + cardinality(v_liggare) + cardinality(v_lankar)
                + cardinality(v_genererade) + cardinality(v_kontakter) + cardinality(v_saljlista)
                + cardinality(v_korningar) + cardinality(v_feedback) + cardinality(v_evals)
                + cardinality(v_forslag) + cardinality(v_handelser) + cardinality(v_sidcache)
                + v_sedda;
      -- 146: barnen som kaskaden tar räknas mot taket.
      v_kaskad := public.gallring_kaskad(v_mejl, v_arenden, v_minne, v_kunder, v_prospekt, v_genererade);
      v_totalt := v_totalt + (select coalesce(sum(value::bigint), 0) from jsonb_each_text(v_kaskad));
      exit when p_torrkorning or (p_tak is not null and v_totalt > p_tak);
      v_mejl_1 := v_mejl;
      v_arenden_1 := v_arenden;
      v_minne_1 := v_minne;
      v_kunder_1 := v_kunder;
      v_prospekt_1 := v_prospekt;
      v_listrader_1 := v_listrader;
      v_listor_1 := v_listor;
      v_liggare_1 := v_liggare;
      v_lankar_1 := v_lankar;
      v_genererade_1 := v_genererade;
      v_kontakter_1 := v_kontakter;
      v_saljlista_1 := v_saljlista;
      v_korningar_1 := v_korningar;
      v_feedback_1 := v_feedback;
      v_evals_1 := v_evals;
      v_forslag_1 := v_forslag;
      v_handelser_1 := v_handelser;
      v_sidcache_1 := v_sidcache;
      -- En skrivning som håller en kandidatrad väntas ut högst tio sekunder;
      -- sedan faller kunden för i dag och nästa körning tar den.
      v_timeout := current_setting('lock_timeout');
      perform set_config('lock_timeout', '10s', true);
      perform pg_advisory_xact_lock_shared(hashtext('snajp.behandlingsbegransning'));
      perform 1 from public.ss_emails where id = any(v_mejl) or ticket_id = any(v_arenden) for update;
      perform 1 from public.ss_drafts where email_id = any(v_mejl) or ticket_id = any(v_arenden) for update;
      perform 1 from public.ss_tickets where id = any(v_arenden) for update;
      perform 1 from public.ss_conversations where ticket_id = any(v_arenden) for update;
      perform 1 from public.ss_customers where id = any(v_kunder) for update;
      perform 1 from public.ss_chat_state where customer_id = any(v_kunder) for update;
      perform 1 from public.ss_channel_contacts where customer_id = any(v_kunder) for update;
      perform 1 from public.customer_memory where id = any(v_minne) or customer_id = any(v_kunder) for update;
      perform 1 from public.prospects where id = any(v_prospekt) for update;
      perform 1 from public.outreach_threads where prospect_id = any(v_prospekt) for update;
      perform 1 from public.outreach_messages where thread_id in (select t.id from public.outreach_threads t where t.prospect_id = any(v_prospekt)) for update;
      perform 1 from public.send_queue where thread_id in (select t.id from public.outreach_threads t where t.prospect_id = any(v_prospekt)) for update;
      perform 1 from public.ss_demolankar where thread_id in (select t.id from public.outreach_threads t where t.prospect_id = any(v_prospekt)) for update;
      perform 1 from public.lead_samtal where prospect_id = any(v_prospekt) for update;
      perform 1 from public.lead_anteckningar where prospect_id = any(v_prospekt) for update;
      perform 1 from public.lead_uppgifter where prospect_id = any(v_prospekt) for update;
      perform 1 from public.prospect_status_logg where prospect_id = any(v_prospekt) for update;
      perform 1 from public.prospect_sources where prospect_id = any(v_prospekt) for update;
      perform 1 from public.lead_list_items where id = any(v_listrader) or prospect_id = any(v_prospekt) for update;
      perform 1 from public.lead_lists where id = any(v_listor) for update;
      perform 1 from public.leads_job_ledger where job_id = any(v_liggare) for update;
      perform 1 from public.ss_avregistreringslankar where token = any(v_lankar) for update;
      perform 1 from public.generated_emails where id = any(v_genererade) or contact_id = any(v_kontakter) for update;
      perform 1 from public.contacts where id = any(v_kontakter) for update;
      perform 1 from public.meetings where contact_id = any(v_kontakter) for update;
      perform 1 from public.saljlista where id = any(v_saljlista) for update;
      perform 1 from public.agent_runs where id = any(v_korningar) for update;
      perform 1 from public.agent_feedback where id = any(v_feedback) for update;
      perform 1 from public.leads_sidcache where tenant_id = p_tenant and url = any(v_sidcache) for update;
      perform set_config('lock_timeout', v_timeout, true);
    else
      v_mejl := array(select unnest(v_mejl) intersect select unnest(v_mejl_1));
      v_arenden := array(select unnest(v_arenden) intersect select unnest(v_arenden_1));
      v_minne := array(select unnest(v_minne) intersect select unnest(v_minne_1));
      v_kunder := array(select unnest(v_kunder) intersect select unnest(v_kunder_1));
      v_prospekt := array(select unnest(v_prospekt) intersect select unnest(v_prospekt_1));
      v_listrader := array(select unnest(v_listrader) intersect select unnest(v_listrader_1));
      v_listor := array(select unnest(v_listor) intersect select unnest(v_listor_1));
      v_liggare := array(select unnest(v_liggare) intersect select unnest(v_liggare_1));
      v_lankar := array(select unnest(v_lankar) intersect select unnest(v_lankar_1));
      v_genererade := array(select unnest(v_genererade) intersect select unnest(v_genererade_1));
      v_kontakter := array(select unnest(v_kontakter) intersect select unnest(v_kontakter_1));
      v_saljlista := array(select unnest(v_saljlista) intersect select unnest(v_saljlista_1));
      v_korningar := array(select unnest(v_korningar) intersect select unnest(v_korningar_1));
      v_feedback := array(select unnest(v_feedback) intersect select unnest(v_feedback_1));
      v_evals := array(select unnest(v_evals) intersect select unnest(v_evals_1));
      v_forslag := array(select unnest(v_forslag) intersect select unnest(v_forslag_1));
      v_handelser := array(select unnest(v_handelser) intersect select unnest(v_handelser_1));
      v_sidcache := array(select unnest(v_sidcache) intersect select unnest(v_sidcache_1));
    end if;
  end loop;

  -- Spärrlistans koppling till kontakter som raderas. Räknas för loggen men
  -- inte i taket: raden står kvar, bara pekaren nollas.
  select count(*) into v_sparr
    from public.suppressions
   where contact_id = any(v_kontakter);

  v_antal := jsonb_build_object(
    'ss_emails',                jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_mejl)),
    'ss_tickets',               jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_arenden)),
    'customer_memory',          jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_minne)),
    'ss_customers',             jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_kunder)),
    'prospects',                jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_prospekt)),
    'lead_list_items',          jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_listrader)),
    'lead_lists',               jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_listor)),
    'leads_job_ledger',         jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_liggare)),
    'ss_avregistreringslankar', jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_lankar)),
    'generated_emails',         jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_genererade)),
    'contacts',                 jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_kontakter)),
    'saljlista',                jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_saljlista)),
    'agent_runs',               jsonb_build_object('atgard', 'anonymisera', 'antal', cardinality(v_korningar)),
    'agent_feedback',           jsonb_build_object('atgard', 'anonymisera', 'antal', cardinality(v_feedback)),
    'agent_evals',              jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_evals)),
    'agent_suggestions',        jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_forslag)),
    'platform_events',          jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_handelser)),
    'leads_sidcache',           jsonb_build_object('atgard', 'radera', 'antal', cardinality(v_sidcache)),
    'ss_channel_inbound_seen',  jsonb_build_object('atgard', 'radera', 'antal', v_sedda),
    'suppressions',             jsonb_build_object('atgard', 'frikoppla', 'antal', v_sparr)
  );

  v_totalt := cardinality(v_mejl) + cardinality(v_arenden) + cardinality(v_minne)
            + cardinality(v_kunder) + cardinality(v_prospekt) + cardinality(v_listrader)
            + cardinality(v_listor) + cardinality(v_liggare) + cardinality(v_lankar)
            + cardinality(v_genererade) + cardinality(v_kontakter) + cardinality(v_saljlista)
            + cardinality(v_korningar) + cardinality(v_feedback) + cardinality(v_evals)
            + cardinality(v_forslag) + cardinality(v_handelser) + cardinality(v_sidcache)
            + v_sedda;

  -- 146: kaskaden räknas om på det som faktiskt raderas, efter låsen, och
  -- läggs både i totalen (taket) och i antal per tabell (loggen). Ett barn
  -- som också är en egen kategori (ärenden, kundminne) läggs till där.
  v_kaskad := public.gallring_kaskad(v_mejl, v_arenden, v_minne, v_kunder, v_prospekt, v_genererade);
  v_totalt := v_totalt + (select coalesce(sum(value::bigint), 0) from jsonb_each_text(v_kaskad));
  select v_antal || coalesce(jsonb_object_agg(k.key, jsonb_build_object(
           'atgard', coalesce(v_antal -> k.key ->> 'atgard', 'kaskad'),
           'antal', coalesce((v_antal -> k.key ->> 'antal')::bigint, 0) + k.value::bigint)), '{}'::jsonb)
    into v_antal
    from jsonb_each_text(v_kaskad) k;

  if p_torrkorning then
    v_status := 'torrkorning';
  elsif p_tak is not null and v_totalt > p_tak then
    v_status := 'tak_nadd';
  else
    v_status := 'klar';
  end if;

  if v_status = 'klar' then
    -- -- Raderingen, i främmande nycklars ordning. -------------------------

    -- Mejlen först: ss_emails.ticket_id och ss_drafts.ticket_id saknar kaskad.
    delete from public.ss_emails where id = any(v_mejl);
    -- Föräldrar och barn i samma sats: NO ACTION prövas vid satsens slut.
    delete from public.ss_tickets where id = any(v_arenden);
    delete from public.customer_memory where id = any(v_minne);
    delete from public.ss_customers where id = any(v_kunder);

    delete from public.prospects where id = any(v_prospekt);
    delete from public.lead_list_items where id = any(v_listrader);
    delete from public.lead_lists where id = any(v_listor);
    delete from public.leads_job_ledger where job_id = any(v_liggare);
    delete from public.ss_avregistreringslankar where token = any(v_lankar);

    -- SPÄRRLISTAN FÖRE KONTAKTERNA. suppressions.contact_id kaskaderar från
    -- contacts; utan det här steget hade gallringen tagit med sig
    -- avregistreringen och nästa utskick nått den som bett att slippa.
    update public.suppressions set contact_id = null where contact_id = any(v_kontakter);
    delete from public.generated_emails where id = any(v_genererade);
    delete from public.contacts where id = any(v_kontakter);
    delete from public.saljlista where id = any(v_saljlista);

    update public.agent_runs
       set input = null, output = null, grounding = null, step_log = '[]'::jsonb,
           prospect_id = null, thread_id = null
     where id = any(v_korningar);
    update public.agent_feedback
       set comment = null, corrected_output = null
     where id = any(v_feedback);
    delete from public.agent_evals where id = any(v_evals);
    delete from public.agent_suggestions where id = any(v_forslag);
    delete from public.platform_events where id = any(v_handelser);
    delete from public.leads_sidcache where tenant_id = p_tenant and url = any(v_sidcache);
    delete from public.ss_channel_inbound_seen where tenant_id = p_tenant and seen_at < v_grans;
  end if;

  -- Spårbarheten. En gallring ingen kan visa att den skett är, vid en
  -- granskning, en gallring som inte skett (048).
  insert into public.ss_gallringslogg
    (tenant_id, kord_av, torrkorning, status, dagar, grans, tak, totalt, antal)
  values
    (p_tenant, coalesce(p_kord_av, 'skript'), p_torrkorning, v_status, v_dagar, v_grans,
     p_tak, v_totalt, v_antal)
  returning id into v_logg;

  return jsonb_build_object(
    'status', v_status, 'tenant_id', p_tenant, 'dagar', v_dagar, 'grans', v_grans,
    'spegel', v_spegel, 'tak', p_tak, 'totalt', v_totalt, 'antal', v_antal, 'logg_id', v_logg
  );
end;
$$;
