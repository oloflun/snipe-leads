-- 133: gallringen körs också i development-spegeln, för tabellerna synken
-- inte för över.
--
-- Codex-granskningen 2026-11-19 (runda 3): gallra_alla avbröt helt när
-- mirror_meta fanns, med antagandet att synken för över main:s gallring. Men
-- synken (scripts/railway_synk.py:SYNK) omfattar inte bland annat
-- agent_feedback, generated_emails, contacts, saljlista, platform_events och
-- leads_sidcache, som gallringen raderar eller anonymiserar. Rader där, från
-- den gamla fulla speglingen eller från developments egna körningar, låg kvar
-- i spegeln för alltid, också när samma uppgifter gallrats i main.
--
-- Nu gallrar spegeln själv de tabeller synken inte rör, med samma policy och
-- samma urval som main. De synkade tabellerna lämnas åt synken som förut: main
-- är sanningen där, och en egen radering hade kopierats tillbaka.
--
-- Policyn (ss_gallringspolicy) synkas inte; scripts/gallra.py skriver den nu
-- i båda miljöerna när den sätts i main.
--
-- Funktionerna är i övrigt oförändrade från 119. Additiv och idempotent
-- (create or replace, samma signaturer, samma rättigheter).

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
  v_spegel     boolean := to_regclass('public.mirror_meta') is not null;
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

  -- 133: i en spegel gallras bara tabellerna synken inte för över. De synkade
  -- får main:s raderingar genom synk_raderingar, och en egen radering där hade
  -- kopierats tillbaka från main vid nästa varv. Listan ska vara exakt
  -- tabellerna i scripts/railway_synk.py:SYNK som gallringen rör; testet
  -- tests/test_gallring_spegel.py håller ihop dem.
  if v_spegel then
    v_mejl := v_tomt_uuid;
    v_arenden := v_tomt_uuid;
    v_minne := v_tomt_uuid;
    v_kunder := v_tomt_uuid;
    v_prospekt := v_tomt_uuid;
    v_listrader := v_tomt_uuid;
    v_listor := v_tomt_uuid;
  end if;

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

  if v_spegel then
    v_liggare := v_tomt_text;
    v_korningar := v_tomt_uuid;
    v_forslag := v_tomt_uuid;
  end if;

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
    'spegel', v_spegel, 'tak', p_tak, 'totalt', v_totalt, 'antal', v_antal, 'logg_id', v_logg
  );
end;
$$;

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

  return jsonb_build_object('status', 'kord', 'dag', v_dag, 'kunder', v_kunder,
                            'spegel', to_regclass('public.mirror_meta') is not null);
end;
$$;

comment on function public.gallra_alla(integer, text) is
  'Den dagliga gallringen (migration 119, 133): alla kunder med beslutad '
  'policy, högst en gång per svenskt dygn, med tak per kund. I en spegel '
  'bara tabellerna synken inte för över. Anropas av api-tjänstens '
  'bakgrundsjobb (app/jobs/gallring.py).';
