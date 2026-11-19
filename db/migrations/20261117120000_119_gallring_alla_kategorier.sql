-- 119: gallringen omfattar alla kategorier integritetspolicyn räknar upp.
--
-- ## Varför
--
-- Integritetspolicyn säger att uppgifter sparas i 24 månader räknat från den
-- senaste behandlingen, att samma tid gäller samtliga kategorier och att
-- gallringen är automatiserad och loggas. 048 byggde mekanismen men bara för
-- supportmejl (ss_emails med kaskad). Leads, chattar, agentloggar och den
-- gamla kampanjmodellen låg kvar för alltid. Den här migrationen bygger
-- resten av mekanismen. BESLUTET är fortfarande ägarens: ingen policy skrivs
-- här, och en kund utan rad i ss_gallringspolicy gallras aldrig (se 048).
--
-- ## Vad "senaste behandlingen" betyder
--
-- Gränsen går vid den senaste AKTIVITETEN på den sak raden hör till, inte vid
-- radens skapelsetid: ett ärende som fortfarande besvaras, ett prospekt som
-- fick ett svar förra veckan och en kund som chattade i går är inte gamla.
-- Varje urval nedan räknar därför den senaste tidsstämpeln över raden och de
-- rader som hänger på den (meddelanden, utkast, samtal, uppgifter).
--
-- Tre kolumner används MEDVETET INTE, för att de lades till i efterhand med
-- `default now()` och därför bär migrationsdagen på varje äldre rad, inte
-- någon behandling:
--   * synk_andrad_at (111) — dessutom bumpas den av varje teknisk skrivning,
--   * outreach_messages.created_at (107) — sent_at används i första hand,
--   * leads_job_ledger.updated_at (080) — tas med, men gör bara gallringen
--     senare för gamla rader, aldrig tidigare.
--
-- ## Vad som raderas, vad som anonymiseras och vad som lämnas
--
-- Raderas (urvalet räknas först, sedan raderas i främmande nycklars ordning):
--   ss_emails (kaskad: bilagor, klassningar, utkast, granskningar, beslutslogg)
--   ss_tickets (kaskad: konversationer, meddelanden), customer_memory,
--   ss_customers (kaskad: identifierare, chattläge, kanalkontakter),
--   prospects (kaskad: källor, trådar, meddelanden, kö, demolänkar och deras
--   händelser, anteckningar, uppgifter, statuslogg, samtal),
--   lead_list_items, lead_lists (tomma), leads_job_ledger (avslutade),
--   ss_avregistreringslankar (när adressen inte längre finns i något kvarvarande
--   prospekt eller någon listrad), generated_emails (kaskad: email_events),
--   contacts, saljlista, agent_evals, agent_suggestions, platform_events,
--   leads_sidcache, ss_channel_inbound_seen.
--
-- Anonymiseras: agent_runs och agent_feedback, se nedan.
--
-- Rörs ALDRIG:
--   * suppressions — spärrlistan finns för att en avregistrerad adress aldrig
--     ska kontaktas igen. suppressions.contact_id kaskaderar från contacts, så
--     kopplingen NOLLAS innan en kontakt raderas (samma aktiva steg som
--     scripts/gdpr_radera.py). Raden med adressen står kvar.
--   * bk_underlag, bk_verifikat, kvitto_mejl_lasta — kundens räkenskapsmaterial
--     med sju års lagkrav (BFL 7 kap. 2 §). Inte den här mekanismens sak.
--   * ss_customer_details, ss_customer_contacts, ss_mailboxes,
--     ss_sending_domains, workspace_invites, trial_paminnelser, auth.users,
--     profiles — Snajps eget avtals- och kontoregister över kunden, inte
--     kunddata i produkten. Gallras när kundrelationen avslutas.
--   * demo_requests, webbpool — saknar tenant (plattformens egna).
--   * ss_decision_log utan email_id — där står bland annat gallringens egna
--     bevis från 048. Rader MED email_id följer mejlet i kaskaden.
--   * companies, campaigns, offers, sequences — bolags- och kampanjnivå,
--     inga personuppgifter.
--   * audit_logs — kontots säkerhetslogg, kontoflödets beslut.
--
-- ## Agentloggarna: anonymisera, inte radera
--
-- agent_runs bär hela promptar och svar (input, output, step_log, grounding)
-- med namn och mejltext. Det ÄR personuppgifterna, och de nollas. Raden står
-- kvar med typ, modell, tokens, kostnad, svarstid och tid: siffror som inte
-- säger något om en person men som kostnads- och användningsrapporterna
-- summerar. Att radera raden hade skrivit om historiska kostnader och tagit
-- med sig agent_feedback i kaskaden; att nolla textfälten och kopplingarna
-- till prospekt och tråd tar bort allt som pekar ut en människa. Det är det
-- minst ingripande som ändå uppfyller lagringsminimeringen (art. 5.1 e): det
-- som blir kvar är inte längre en personuppgift. agent_feedback behandlas
-- likadant (kommentaren och den rättade texten nollas, omdömet står kvar).
-- agent_evals raderas: ett eval-fall ÄR texten och går inte att anonymisera.
--
-- ## Taket
--
-- p_tak är det största antal rader en körning får ändra hos EN kund. Räknas
-- urvalet till fler görs INGENTING hos den kunden, och loggen får status
-- tak_nadd. Ett felaktigt policyvärde (30 i stället för 730) ska ge ett larm,
-- inte en tom kund. En första gallring av en kund med lång historik går
-- därför genom skriptet (scripts/gallra.py), som en människa kör efter en
-- torrkörning.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

-- ---------------------------------------------------------------------------
-- Loggen: en rad per körning och kund.
-- ---------------------------------------------------------------------------

create table if not exists public.ss_gallringslogg (
  id          bigint generated always as identity primary key,
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  kord_at     timestamptz not null default now(),
  -- 'schemalagd' (api-tjänstens dagliga körning) eller 'skript' (gallra.py).
  kord_av     text not null,
  torrkorning boolean not null,
  status      text not null
              check (status in ('klar', 'torrkorning', 'tak_nadd', 'fel')),
  dagar       integer,
  grans       timestamptz,
  tak         integer,
  totalt      bigint not null default 0,
  -- {tabell: {"atgard": "radera"|"anonymisera"|"frikoppla", "antal": n}}
  antal       jsonb not null default '{}'::jsonb,
  fel         text
);

create index if not exists ss_gallringslogg_tenant_idx
  on public.ss_gallringslogg (tenant_id, kord_at desc);

comment on table public.ss_gallringslogg is
  'En rad per gallringskörning och kund: vad som raderades eller '
  'anonymiserades, per tabell. Skrivs bara av gallra_tenant/gallra_alla.';

-- ---------------------------------------------------------------------------
-- Dygnsspärren: den schemalagda körningen görs högst en gång per svenskt dygn,
-- hur många api-processer som än startar den. Den som först får in raden kör;
-- de andra ser konflikten och gör ingenting. Raden skrivs i SAMMA transaktion
-- som gallringen, så en körning som faller i sin helhet lämnar ingen spärr
-- efter sig och görs om vid nästa varv.
-- ---------------------------------------------------------------------------

create table if not exists public.ss_gallringskorning (
  dag        date primary key,
  startad_at timestamptz not null default now(),
  klar_at    timestamptz,
  kunder     integer,
  totalt     bigint,
  tak_nadda  integer,
  fel        integer
);

comment on table public.ss_gallringskorning is
  'Dygnsspärren för den schemalagda gallringen: en rad per svenskt dygn.';

-- RLS slås på av event-triggern (0000). Appens roll får LÄSA, så att
-- plattformsadmin ser loggen; den får aldrig skriva. Skrivningen sker bara i
-- de säkerhetsdefinierade funktionerna nedan. Samma läsrätt på policytabellen
-- (048), som annars bara ägarrollen ser.
alter table public.ss_gallringslogg enable row level security;
alter table public.ss_gallringskorning enable row level security;
alter table public.ss_gallringspolicy enable row level security;

drop policy if exists ss_gallringslogg_las on public.ss_gallringslogg;
create policy ss_gallringslogg_las on public.ss_gallringslogg
  for select to snajp_app using (true);
drop policy if exists ss_gallringskorning_las on public.ss_gallringskorning;
create policy ss_gallringskorning_las on public.ss_gallringskorning
  for select to snajp_app using (true);
drop policy if exists ss_gallringspolicy_las on public.ss_gallringspolicy;
create policy ss_gallringspolicy_las on public.ss_gallringspolicy
  for select to snajp_app using (true);

grant select on table public.ss_gallringslogg, public.ss_gallringskorning,
  public.ss_gallringspolicy to snajp_app;
revoke insert, update, delete on table public.ss_gallringslogg,
  public.ss_gallringskorning, public.ss_gallringspolicy from snajp_app;

-- ---------------------------------------------------------------------------
-- Gallringen för en kund.
-- ---------------------------------------------------------------------------
--
-- Torrkörning som default, som 048: räknar urvalet, loggar det och ändrar
-- ingenting. Returnerar
--   {status, tenant_id, dagar, grans, tak, totalt, antal, logg_id}
-- där status är 'ingen_policy' (ingenting gjort, ingen logg), 'torrkorning',
-- 'tak_nadd' (ingenting gjort) eller 'klar'.

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

  -- -- Urvalen. Ingenting ändras förrän alla är räknade. ----------------------

  -- Supportmejl: mejlets egen aktivitet och dess utkast.
  select coalesce(array_agg(e.id), v_tomt_uuid) into v_mejl
    from public.ss_emails e
   where e.tenant_id = p_tenant
     and greatest(e.created_at, e.received_at, e.updated_at, e.hanterad_at,
           (select max(greatest(d.created_at, d.updated_at))
              from public.ss_drafts d where d.email_id = e.id)) < v_grans;

  -- Ärenden (chatt och mejl): ärendets, meddelandenas, mejlens och utkastens
  -- senaste tid. Ett ärende som ett kvarvarande mejl eller utkast pekar på,
  -- eller som är förälder till ett kvarvarande ärende, står kvar (främmande
  -- nycklar utan kaskad).
  with kandidat as (
    select t.id
      from public.ss_tickets t
     where t.tenant_id = p_tenant
       and greatest(t.created_at, t.updated_at,
             (select max(greatest(c.created_at, m.created_at))
                from public.ss_conversations c
                left join public.ss_messages m on m.conversation_id = c.id
               where c.ticket_id = t.id),
             (select max(greatest(e.created_at, e.received_at, e.updated_at, e.hanterad_at))
                from public.ss_emails e where e.ticket_id = t.id),
             (select max(greatest(d.created_at, d.updated_at))
                from public.ss_drafts d where d.ticket_id = t.id)) < v_grans
       and not exists (select 1 from public.ss_emails e
                        where e.ticket_id = t.id and e.id <> all(v_mejl))
       and not exists (select 1 from public.ss_drafts d
                        where d.ticket_id = t.id and d.email_id <> all(v_mejl))
  )
  select coalesce(array_agg(k.id), v_tomt_uuid) into v_arenden
    from kandidat k
   where not exists (select 1 from public.ss_tickets b
                      where b.parent_ticket_id = k.id
                        and b.id not in (select id from kandidat));

  -- Kundminnet: varje faktum är en egen behandling.
  select coalesce(array_agg(id), v_tomt_uuid) into v_minne
    from public.customer_memory
   where tenant_id = p_tenant and created_at < v_grans;

  -- Chatt- och supportkunden: när varken kunden själv, chattläget,
  -- kanalkontakten eller kundminnet rörts, och inget ärende står kvar.
  select coalesce(array_agg(c.id), v_tomt_uuid) into v_kunder
    from public.ss_customers c
   where c.tenant_id = p_tenant
     and greatest(c.created_at,
           (select max(i.created_at) from public.ss_customer_identifiers i
             where i.customer_id = c.id),
           (select max(greatest(s.updated_at, s.overlamnad_at)) from public.ss_chat_state s
             where s.customer_id = c.id),
           (select max(greatest(k.created_at, k.updated_at)) from public.ss_channel_contacts k
             where k.customer_id = c.id),
           (select max(m.created_at) from public.customer_memory m
             where m.customer_id = c.id)) < v_grans
     and not exists (select 1 from public.ss_tickets t
                      where t.customer_id = c.id and t.id <> all(v_arenden));

  -- Prospekten: den senaste tiden över allt som hänger på prospektet.
  select coalesce(array_agg(p.id), v_tomt_uuid) into v_prospekt
    from public.prospects p
   where p.tenant_id = p_tenant
     and greatest(p.created_at, p.arkiverad_at,
           (select max(greatest(t.created_at, t.last_inbound_at, t.svarsklass_at))
              from public.outreach_threads t where t.prospect_id = p.id),
           (select max(greatest(coalesce(m.sent_at, m.created_at), m.leverans_at, m.kasserad_at))
              from public.outreach_messages m
              join public.outreach_threads t on t.id = m.thread_id
             where t.prospect_id = p.id),
           (select max(greatest(q.created_at, q.scheduled_at))
              from public.send_queue q
              join public.outreach_threads t on t.id = q.thread_id
             where t.prospect_id = p.id),
           (select max(greatest(d.created_at, h.created_at))
              from public.ss_demolankar d
              join public.outreach_threads t on t.id = d.thread_id
              left join public.ss_demolank_handelser h on h.token = d.token
             where t.prospect_id = p.id),
           (select max(greatest(s.created_at, s.aterkom_datum::timestamptz))
              from public.lead_samtal s where s.prospect_id = p.id),
           (select max(a.created_at) from public.lead_anteckningar a where a.prospect_id = p.id),
           (select max(greatest(u.created_at, u.klar_at, u.forfaller::timestamptz))
              from public.lead_uppgifter u where u.prospect_id = p.id),
           (select max(l.created_at) from public.prospect_status_logg l where l.prospect_id = p.id),
           (select max(k.retrieved_at) from public.prospect_sources k where k.prospect_id = p.id)
         ) < v_grans;

  -- Listorna: varje rad för sig, sedan de listor som blir tomma.
  select coalesce(array_agg(id), v_tomt_uuid) into v_listrader
    from public.lead_list_items
   where tenant_id = p_tenant
     and greatest(created_at, processad_at) < v_grans;

  select coalesce(array_agg(l.id), v_tomt_uuid) into v_listor
    from public.lead_lists l
   where l.tenant_id = p_tenant
     and greatest(l.created_at, l.completed_at) < v_grans
     and not exists (select 1 from public.lead_list_items i
                      where i.list_id = l.id and i.id <> all(v_listrader));

  -- Jobbliggaren: bara avslutade jobb (INV-JOB-002 läser pågående).
  select coalesce(array_agg(job_id), v_tomt_text) into v_liggare
    from public.leads_job_ledger
   where tenant_id = p_tenant
     and status in ('completed', 'failed')
     and greatest(created_at, updated_at, completed_at) < v_grans;

  -- Avregistreringslänken återanvänds för varje mejl till samma adress, så
  -- dess egen tid säger inget om när den senast skickades. Den står kvar så
  -- länge adressen finns i ett kvarvarande prospekt eller en kvarvarande
  -- listrad hos kunden.
  select coalesce(array_agg(a.token), v_tomt_text) into v_lankar
    from public.ss_avregistreringslankar a
   where a.tenant_id = p_tenant
     and greatest(a.created_at, a.anvand_at) < v_grans
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
     and greatest(created_at, sent_at) < v_grans;

  select coalesce(array_agg(k.id), v_tomt_uuid) into v_kontakter
    from public.contacts k
   where k.workspace_id = any(v_ws)
     and greatest(k.created_at,
           (select max(greatest(g.created_at, g.sent_at)) from public.generated_emails g
             where g.contact_id = k.id),
           (select max(m.booked_for) from public.meetings m where m.contact_id = k.id)) < v_grans;

  select coalesce(array_agg(id), v_tomt_uuid) into v_saljlista
    from public.saljlista
   where workspace_id = any(v_ws)
     and greatest(created_at, updated_at, senast_kontaktad::timestamptz) < v_grans;

  -- Agentloggarna: bara rader som fortfarande bär något att nolla, så att en
  -- andra körning räknar noll.
  select coalesce(array_agg(id), v_tomt_uuid) into v_korningar
    from public.agent_runs
   where tenant_id = p_tenant
     and created_at < v_grans
     and (input is not null or output is not null or grounding is not null
          or step_log <> '[]'::jsonb or prospect_id is not null or thread_id is not null);

  select coalesce(array_agg(id), v_tomt_uuid) into v_feedback
    from public.agent_feedback
   where tenant_id = p_tenant
     and created_at < v_grans
     and (comment is not null or corrected_output is not null);

  select coalesce(array_agg(id), v_tomt_uuid) into v_evals
    from public.agent_evals
   where tenant_id = p_tenant and created_at < v_grans;

  select coalesce(array_agg(id), v_tomt_uuid) into v_forslag
    from public.agent_suggestions
   where tenant_id = p_tenant and created_at < v_grans;

  select coalesce(array_agg(id), v_tomt_uuid) into v_handelser
    from public.platform_events
   where tenant_id = p_tenant and created_at < v_grans;

  select coalesce(array_agg(url), v_tomt_text) into v_sidcache
    from public.leads_sidcache
   where tenant_id = p_tenant and hamtad_at < v_grans;

  select count(*) into v_sedda
    from public.ss_channel_inbound_seen
   where tenant_id = p_tenant and seen_at < v_grans;

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
    'tak', p_tak, 'totalt', v_totalt, 'antal', v_antal, 'logg_id', v_logg
  );
end;
$$;

revoke all on function public.gallra_tenant(uuid, boolean, integer, text) from public;

comment on function public.gallra_tenant(uuid, boolean, integer, text) is
  'Gallrar en kunds uppgifter äldre än kundens beslutade period i alla '
  'kategorier (migration 119). Torrkörning som default. Ingen policy = '
  'ingenting görs. Anropas av scripts/gallra.py och av gallra_alla.';

-- ---------------------------------------------------------------------------
-- Den schemalagda körningen: alla kunder med beslutad policy, en gång per dygn.
-- ---------------------------------------------------------------------------
--
-- Returnerar {status, dag, kunder: [...]} där status är
--   'spegel'      — databasen är en spegel (mirror_meta finns). Ingenting görs:
--                   spegeln får main:s raderingar genom synken
--                   (synk_raderingar, 111), och en egen gallring där hade
--                   skrivit i en databas som skrivs över.
--   'redan_kord'  — dygnets körning är redan gjord (eller pågår).
--   'kord'        — körd; kunder bär varje kunds svar från gallra_tenant,
--                   eller {status: 'fel', fel} för en kund som föll.

create or replace function public.gallra_alla(
  p_tak integer,
  p_kord_av text default 'schemalagd'
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_dag    date := (now() at time zone 'Europe/Stockholm')::date;
  v_rad    record;
  v_svar   jsonb;
  v_kunder jsonb := '[]'::jsonb;
  v_ny     integer;
  v_totalt bigint := 0;
  v_tak    integer := 0;
  v_fel    integer := 0;
begin
  if to_regclass('public.mirror_meta') is not null then
    return jsonb_build_object('status', 'spegel', 'dag', v_dag);
  end if;

  insert into public.ss_gallringskorning (dag) values (v_dag)
  on conflict (dag) do nothing;
  get diagnostics v_ny = row_count;
  if v_ny = 0 then
    return jsonb_build_object('status', 'redan_kord', 'dag', v_dag);
  end if;

  for v_rad in
    select tenant_id from public.ss_gallringspolicy order by tenant_id
  loop
    begin
      v_svar := public.gallra_tenant(v_rad.tenant_id, false, p_tak, p_kord_av);
    exception when others then
      -- En kund som faller stoppar inte de andra. Delblocket rullar tillbaka
      -- just den kundens ändringar; felet loggas och syns i adminvägen.
      insert into public.ss_gallringslogg
        (tenant_id, kord_av, torrkorning, status, tak, fel)
      values (v_rad.tenant_id, p_kord_av, false, 'fel', p_tak, left(sqlerrm, 500));
      v_svar := jsonb_build_object('status', 'fel', 'tenant_id', v_rad.tenant_id,
                                   'fel', left(sqlerrm, 500));
    end;
    v_kunder := v_kunder || jsonb_build_array(v_svar);
    if v_svar->>'status' = 'klar' then
      v_totalt := v_totalt + coalesce((v_svar->>'totalt')::bigint, 0);
    elsif v_svar->>'status' = 'tak_nadd' then
      v_tak := v_tak + 1;
    elsif v_svar->>'status' = 'fel' then
      v_fel := v_fel + 1;
    end if;
  end loop;

  update public.ss_gallringskorning
     set klar_at = now(), kunder = jsonb_array_length(v_kunder),
         totalt = v_totalt, tak_nadda = v_tak, fel = v_fel
   where dag = v_dag;

  return jsonb_build_object('status', 'kord', 'dag', v_dag, 'kunder', v_kunder);
end;
$$;

revoke all on function public.gallra_alla(integer, text) from public;
grant execute on function public.gallra_alla(integer, text) to snajp_app;

comment on function public.gallra_alla(integer, text) is
  'Den dagliga gallringen (migration 119): alla kunder med beslutad policy, '
  'högst en gång per svenskt dygn, aldrig i en spegel, med tak per kund. '
  'Anropas av api-tjänstens bakgrundsjobb (app/jobs/gallring.py).';
