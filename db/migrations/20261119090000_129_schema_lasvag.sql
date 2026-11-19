-- 129: api:t får läsa migrationsliggaren, för PR-kontrollen utan databas.
--
-- docs/compliance/synkflytt-plan.md steg 9. "releasens migrationer" i
-- .github/workflows/migrera.yml frågar api:t (GET /api/drift/schema, egen smal
-- nyckel SCHEMA_LASNYCKEL) vilka migrationer som är körda, i stället för att
-- ansluta till databasen över den publika porten med superanvändaren. Api:t
-- ansluter som snajp_app, som i dag inte når schemat supabase_migrations.
--
-- Additiv och idempotent: bara läsrätt på en tabell som bär filnamn, ingen
-- persondata. Rollen och liggaren finns inte i varje databas (en testdatabas
-- som inte byggts av railway_migrate), så rättigheten ges bara när båda finns.

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app')
     and to_regclass('supabase_migrations.schema_migrations') is not null then
    execute 'grant usage on schema supabase_migrations to snajp_app';
    execute 'grant select on table supabase_migrations.schema_migrations to snajp_app';
  end if;
end;
$$;
