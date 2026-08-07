-- G8: den publika, oautentiserade demons egen tenant. Samma mönster som
-- 003_snajp_multitenant.sql:s Nordlys Handel-backfill — en fast UUID så
-- app/config.py:PUBLIC_DEMO_TENANT_ID alltid pekar på samma rad, oavsett
-- vilken ordning create_tenant (upsert på slug) råkar köras i.
--
-- Ingen KB seedas här — det gör app/scripts/seed_kb.py:ensure_public_demo_kb
-- (samma mönster som ensure_default_kb, körs automatiskt vid uppstart).

insert into ss_tenants (id, slug, name)
values ('00000000-0000-4000-a000-000000000099', 'public-demo', 'Snajp — offentlig demo')
on conflict (slug) do nothing;
