-- 105: Beställ leads-lista rakt in i säljlistan (Sebbes beställning 2026-10-06).
--
-- "Beställ leads-lista" på Leads › Listor startar en färdig Iris-körning i
-- listspåret vars resultat INTE blir en synlig leadslista: raderna som bär
-- ALLT säljlistan kräver (namn, orgnr, kontaktperson, kontaktnummer,
-- kontaktmail) läggs direkt i arbetsytans säljlista. Körningens lead_list-rad
-- får kalla='saljlista' och visas aldrig under "Dina listor" — den finns kvar
-- för uteslutningen (upptagna.py läser alla listrader) och för felsökning.
--
-- Skrivningen görs av motorn (snajp-support, rollen snajp_app) via en
-- security definer-funktion: saljlista ägs av webben (RLS för snajp_web,
-- migration 103), och funktionen är den enda vägen in för motorn — den
-- mappar ss_tenant → workspace och dedupliklerar mot befintliga rader på
-- orgnr-siffror eller bolagsnamn, samma nycklar som webbens dubblettvarning.
--
-- Idempotent.

alter table public.lead_lists drop constraint if exists lead_lists_kalla_check;
alter table public.lead_lists
  add constraint lead_lists_kalla_check
    check (kalla in ('sok', 'kombinerad', 'import', 'crm', 'saljlista'));

create or replace function public.saljlista_fyll_pa(p_tenant uuid, p_rader jsonb)
returns integer
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $$
declare
  w uuid;
  n integer := 0;
  r jsonb;
begin
  select id into w from public.workspaces where ss_tenant_id = p_tenant limit 1;
  if w is null then
    return 0;
  end if;
  for r in select * from jsonb_array_elements(coalesce(p_rader, '[]'::jsonb)) loop
    if coalesce(r->>'foretagsnamn', '') = '' then
      continue;
    end if;
    if exists (
      select 1 from public.saljlista s
      where s.workspace_id = w
        and (
          (nullif(regexp_replace(s.orgnr, '\D', '', 'g'), '') is not null
            and regexp_replace(s.orgnr, '\D', '', 'g')
              = regexp_replace(coalesce(r->>'orgnr', ''), '\D', '', 'g'))
          or lower(s.foretagsnamn) = lower(r->>'foretagsnamn')
        )
    ) then
      continue;
    end if;
    insert into public.saljlista
      (workspace_id, foretagsnamn, orgnr, kontaktperson, kontaktnummer, kontaktmail, anteckningar)
    values
      (w,
       r->>'foretagsnamn',
       coalesce(r->>'orgnr', ''),
       coalesce(r->>'kontaktperson', ''),
       coalesce(r->>'kontaktnummer', ''),
       coalesce(r->>'kontaktmail', ''),
       coalesce(r->>'anteckningar', ''));
    n := n + 1;
  end loop;
  return n;
end;
$$;

revoke all on function public.saljlista_fyll_pa(uuid, jsonb) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant execute on function public.saljlista_fyll_pa(uuid, jsonb) to snajp_app;
  end if;
end $$;
