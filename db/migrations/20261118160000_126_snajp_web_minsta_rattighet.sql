-- 126: webbens roll får bara det webben gör (ISO 27001 A.8.2, A.8.3, A.5.15;
-- 2026-11-18). Ersätter de breda rättigheterna från 030.
--
-- FÖRE: `snajp_web` hade select, insert, update och delete på ALLA tabeller i
-- `public` (97 st), och fick det automatiskt på varje ny tabell (030:s
-- `alter default privileges`). RLS var enda grinden. `auth.users` (e-post och
-- lösenordshashar) var läsbar för PUBLIC, alltså för varje roll i databasen.
--
-- EFTER: rättigheterna nedan, och inget annat. Listan är kartlagd ur webbens
-- egen SQL (alla 22 filer som importerar lib/db.ts, 2026-11-18) och ur
-- katalogen i development (policyer, triggrar, funktioner):
--   * Varje funktion webben anropar är security definer och har redan egen
--     EXECUTE-rätt; de rörs inte här.
--   * Triggrarna på auth.users (on_auth_user_created,
--     on_auth_user_bootstrap_admin) är security definer.
--   * Policyn på workspace_invites läser profiles som anroparen; därför
--     select på profiles.
--   * `startDemo` (lib/actions/auth.ts) uppdaterar workspaces.is_demo. Utan
--     update-rätt hade frågan kastat och demon inte startat, så kolumnen får
--     update-rätt även om workspaces saknar en update-policy.
--
-- Webbens frågor körs som snajp_web med EXPLAIN mot hela kedjan i CI
-- (snajp-support/tests/db/test_snajp_web_rattigheter.py): en saknad rättighet
-- fäller där, och likaså en rättighet som inte står i listan.
--
-- FÖLJD FÖR NYA TABELLER: webben får INTE längre rättigheter automatiskt. En
-- migration som lägger till en tabell webben ska nå måste ge rättigheten
-- uttryckligen, och testet ovan måste få raden i sin lista.
--
-- `auth.users`: PUBLIC förlorar läsrätten. snajp_app (api:t) läser bara id och
-- e-post, i påminnelsen om provperioden (storage/postgres.py,
-- list_trial_paminnelse_kandidater), och får just de kolumnerna.
--
-- Sekvenserna (usage, select) lämnas som de är: de bär ingen data, och en
-- insert i en tabell med serienummer behöver dem.
--
-- Idempotent: revoke och grant kan köras om. Går något sönder i drift ska det
-- rättas med en ny migration som ger tillbaka just den rättighet som saknas.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'snajp_web') then
    raise notice '126: rollen snajp_web finns inte, inget att smalna av';
    return;
  end if;

  -- 1. Bort med allt i public, nu och framöver.
  execute 'revoke all on all tables in schema public from snajp_web';
  execute 'alter default privileges in schema public revoke all on tables from snajp_web';

  -- 2. Det webben gör.
  -- Arbetsyta och identitet (lib/workspace.ts, lib/data/dashboard.ts,
  -- lib/auth/admin.ts, lib/actions/team.ts).
  execute 'grant select on public.workspaces, public.profiles, public.platform_admins to snajp_web';
  -- startDemo: workspaces.is_demo (lib/actions/auth.ts).
  execute 'grant update (is_demo) on public.workspaces to snajp_web';

  -- Glömt lösenord (lib/actions/auth.ts, app/auth/reset/page.tsx).
  execute 'grant select, insert, delete on public.password_reset_tokens to snajp_web';
  execute 'grant update (used_at) on public.password_reset_tokens to snajp_web';

  -- Demoförfrågan från sajten (lib/actions/demo.ts).
  execute 'grant insert on public.demo_requests to snajp_web';

  -- Notisinställningar (lib/actions/notiser.ts).
  execute 'grant select, insert, update on public.notification_preferences to snajp_web';

  -- Säljlistan (lib/actions/saljlista.ts).
  execute 'grant select, insert, update, delete on public.saljlista to snajp_web';

  -- Inbjudningar (lib/actions/team.ts).
  execute 'grant select, insert, delete on public.workspace_invites to snajp_web';

  -- Affärskontexten (lib/data/business-context.ts, lib/workspace.ts).
  execute 'grant select, insert, update on public.business_contexts to snajp_web';

  -- Mejlutkastet i Email Studio (lib/data/emails.ts).
  execute 'grant select on public.contacts to snajp_web';
  execute 'grant select on public.generated_emails to snajp_web';
  execute 'grant update (subject, body, status) on public.generated_emails to snajp_web';

  -- Kundens namn ur slugen (lib/snajp/provisionering.ts). Bara de kolumnerna.
  execute 'grant select (id, slug, name) on public.ss_tenants to snajp_web';

  -- 3. auth.users: läsning (inloggningen), och skrivning bara av de kolumner
  -- registreringen och lösenordsbytet sätter.
  execute 'revoke insert, update on auth.users from snajp_web';
  execute 'grant select on auth.users to snajp_web';
  execute 'grant insert (email, encrypted_password, raw_user_meta_data, email_confirmed_at) on auth.users to snajp_web';
  execute 'grant update (encrypted_password, updated_at) on auth.users to snajp_web';
end;
$$;

-- 4. auth.users är inte längre läsbar för alla roller.
revoke select on auth.users from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    execute 'grant select (id, email) on auth.users to snajp_app';
  end if;
end;
$$;
