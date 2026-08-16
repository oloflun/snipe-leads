-- Event-triggern som slår på RLS för varje ny tabell i `public`.
--
-- VARFÖR FILEN FINNS: den här funktionen har körts i produktion sedan länge,
-- men skapades för hand och stod i INGEN migration. Migration 018 revokar
-- EXECUTE på den, så en kedja som reses från noll föll på
-- `function public.rls_auto_enable() does not exist` — upptäckt först när
-- schemat restes mot Railway-Postgres.
--
-- Det är samma klass av lucka som 000_base_schema.sql skrevs för att täppa,
-- och den är värre än den ser ut: utan triggern får en ny gren tabeller UTAN
-- radsäkerhet, och alla 60 publika tabeller i produktionen har den påslagen
-- just på grund av triggern — inte på grund av något `alter table` i
-- migrationerna. Ett schema som ser identiskt ut men är oskyddat.
--
-- Filnamnet sorterar FÖRE 000_base_schema med flit ('0' < '_'), eftersom
-- triggern måste finnas innan den första tabellen skapas för att den ska
-- omfatta dem alla.
--
-- Idempotent: `create or replace` på funktionen, och triggern skapas bara om
-- den saknas — i produktion finns den redan under namnet `ensure_rls`.

create or replace function public.rls_auto_enable()
returns event_trigger
language plpgsql
security definer
set search_path to 'pg_catalog'
as $function$
declare
  cmd record;
begin
  for cmd in
    select *
    from pg_event_trigger_ddl_commands()
    where command_tag in ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      and object_type in ('table', 'partitioned table')
  loop
    if cmd.schema_name is not null
       and cmd.schema_name in ('public')
       and cmd.schema_name not in ('pg_catalog', 'information_schema')
       and cmd.schema_name not like 'pg_toast%'
       and cmd.schema_name not like 'pg_temp%' then
      begin
        execute format('alter table if exists %s enable row level security', cmd.object_identity);
        raise log 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      exception
        when others then
          raise log 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      end;
    else
      raise log 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)',
        cmd.object_identity, cmd.schema_name;
    end if;
  end loop;
end;
$function$;

-- Event triggers har ingen `if not exists`-form. Namnet `ensure_rls` är det
-- produktionen redan använder — byt det inte, då får instansen två triggrar
-- som gör samma sak.
do $$
begin
  if not exists (select 1 from pg_event_trigger where evtname = 'ensure_rls') then
    create event trigger ensure_rls
      on ddl_command_end
      execute function public.rls_auto_enable();
  end if;
end
$$;
