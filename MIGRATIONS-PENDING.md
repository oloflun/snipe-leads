# Migrationer som väntar på att köras i produktion

Skrivna och committade i `supabase/migrations/`, men **inte applicerade**.
DDL mot produktionsdatabasen blockerades av behörighetsklassificeraren i den
session som skrev dem — det är en spärr i verktyget, inte ett fel i SQL:en.

Kör dem i **nummerordning** i Supabase SQL-editorn eller via
`mcp__supabase-snipra__apply_migration`. Verifieringen efter varje är den som
räknas; en applicerad migration som ingen mätt är en oapplicerad migration.

---

## 018_rpc_hardening.sql — P0, säkerhet

Fyra `security definer`-funktioner hade EXECUTE till PUBLIC och var anropbara
som `anon` via `/rest/v1/rpc/…`.

**Verifiera efteråt:**
```sql
select p.proname, array_to_string(p.proacl, ' | ') as acl
from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in ('handle_new_user', 'rls_auto_enable', 'ensure_workspace_for_current_user');
```
Förväntat: ingen `=X/postgres` (PUBLIC) och inget `anon=X` kvar.
`ensure_workspace_for_current_user` ska ha `authenticated=X` — den anropas av
`app/auth/callback/route.ts` efter inloggning, och utan den graden går ingen
att logga in.

**Konsolmoment i samma svep:** slå på leaked-password-skyddet i
Supabase Auth → Providers → Email.

---

## 019_rate_limit.sql — P0, kostnadsspärr

Tabellen `platform_rate_events` + policy för `snajp_app` + grants.

**Verifiera efteråt:**
```sql
select count(*) from platform_rate_events;                  -- ska ge 0, inte fel
select polname, polroles::regrole[] from pg_policy
where polrelid = 'public.platform_rate_events'::regclass;   -- ska ge snajp_app
```

Koden är redan fail-open: utan tabellen släpps alla anrop igenom och en
varning loggas. Det är alltså inte trasigt före migrationen — bara oskyddat.

---

## 025_agent_runs_fix.sql — P0, blockerar Fas 6

`agent_runs.agent_type` avvisar `leads_research` och `leads_outreach`, som är
exakt vad koden skriver. **Ingen leads-körning har någonsin sparats.**

**Verifiera efteråt:**
```sql
select pg_get_constraintdef(oid) from pg_constraint
where conname = 'agent_runs_agent_type_check';
-- ska innehålla leads_research, leads_outreach, demo

insert into agent_runs (tenant_id, agent_type, pack_version)
select id, 'leads_research', 'test' from ss_tenants limit 1;
-- ska lyckas. Radera raden efteråt.
```

Kör den här **tidigt även om admin-UI:t dröjer**. Spårdata som inte samlades
går inte att rekonstruera i efterhand.

---

## Fortfarande öppet, kräver dig — inte en migration

1. **`snajp_app`-rollens lösenord** är osatt sedan 2026-08-07. Tills dess kör
   backenden som `postgres` med BYPASSRLS, och varje `tenant_isolation`-policy
   är dekorativ för den anslutningen (INV-SEC-001).
2. **`SNAJP_KEY_LIVRUSTNING`** är osatt på Vercel-projektet `snajp`.
3. **Lösenordet till `snajpsupport@gmail.com`** — regel, inte förmåga.
4. **OAuth-konsolerna** (Google Cloud, Microsoft Entra, Supabase Auth Providers).
   Checklista i `AUTH.md`.
