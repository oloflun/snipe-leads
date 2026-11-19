-- 134: spegeln raderar barnrader som synken lämnat föräldralösa.
--
-- Codex-granskningen 2026-11-19 (runda 4): synken skriver i replica-läge
-- (session_replication_role = replica, scripts/railway_synk.py), där främmande
-- nycklars kaskader inte körs. När main raderar en kund, en agentkörning eller
-- en tråd (gallring, radering på begäran) raderas föräldern i spegeln men inte
-- barnen i tabeller synken inte för över. Kanalkontakterna (telefonnummer,
-- externa användar-id, namn, adress), chattläget, feedbacktexten och
-- demolänkarna blev därför kvar i development, och migration 133 nådde dem
-- inte: dess urval utgår från föräldrarna.
--
-- gallra_spegelns_foraldralosa() raderar varje sådan rad vars förälder saknas,
-- oberoende av policy (föräldern är redan borta i main), och gallra_alla anropar
-- den i en spegel före kunderna. Listan ska vara exakt de icke synkade tabeller
-- som kaskaderar från en synkad; tests/test_gallring_spegel.py läser
-- migrationerna och håller den ihop med railway_synk.SYNK.
--
-- Bara i en spegel: i main kör kaskaderna, och funktionen gör där ingenting.
-- Additiv och idempotent (create or replace, samma signatur för gallra_alla).

create or replace function public.gallra_spegelns_foraldralosa()
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_chatt    bigint;
  v_kanal    bigint;
  v_feedback bigint;
  v_demo     bigint;
begin
  if to_regclass('public.mirror_meta') is null then
    return jsonb_build_object('spegel', false);
  end if;

  delete from public.ss_chat_state s
   where not exists (select 1 from public.ss_customers c where c.id = s.customer_id);
  get diagnostics v_chatt = row_count;

  delete from public.ss_channel_contacts k
   where not exists (select 1 from public.ss_customers c where c.id = k.customer_id);
  get diagnostics v_kanal = row_count;

  delete from public.agent_feedback f
   where not exists (select 1 from public.agent_runs r where r.id = f.run_id);
  get diagnostics v_feedback = row_count;

  -- ss_demolank_handelser kaskaderar från ss_demolankar som vanligt här.
  delete from public.ss_demolankar d
   where not exists (select 1 from public.outreach_threads t where t.id = d.thread_id);
  get diagnostics v_demo = row_count;

  return jsonb_build_object(
    'spegel', true,
    'ss_chat_state', v_chatt,
    'ss_channel_contacts', v_kanal,
    'agent_feedback', v_feedback,
    'ss_demolankar', v_demo
  );
end;
$$;

revoke all on function public.gallra_spegelns_foraldralosa() from public;

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
  v_foraldralosa jsonb;
begin
  insert into public.ss_gallringskorning (dag) values (v_dag)
  on conflict (dag) do nothing;
  get diagnostics v_ny = row_count;
  if v_ny = 0 then
    return jsonb_build_object('status', 'redan_kord', 'dag', v_dag);
  end if;

  -- 134: i en spegel först raderna synken lämnat föräldralösa (se ovan).
  -- Oberoende av policy: föräldern är redan raderad i main.
  if to_regclass('public.mirror_meta') is not null then
    v_foraldralosa := public.gallra_spegelns_foraldralosa();
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
                            'spegel', to_regclass('public.mirror_meta') is not null,
                            'foraldralosa', v_foraldralosa);
end;
$$;
