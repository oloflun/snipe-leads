-- 091: policy för password_reset_tokens (rättar 090).
--
-- 090 antog workspace_tenant_keys-mönstret "RLS utan policies = bara den
-- privilegierade vägen". Antagandet var fel för SKRIVNINGAR: webben ansluter
-- som `snajp_web`, som inte är RLS-befriad, så requestPasswordReset föll med
-- 42501 på första insert (uppmätt i development 2026-10-04, felkod 1460704702
-- i loggen). workspace_tenant_keys kommer undan för att dess enda läsväg är en
-- security definer-funktion — tokentabellen skrivs direkt av server actions.
--
-- Policyn är avsiktligt `to snajp_web using (true)`: tabellen nås bara av
-- auth-flödets server actions (lib/actions/auth.ts), varje rad är en
-- SHA-256-hash av en engångstoken med 256 bitar entropi — ett radläckage ger
-- inga användbara länkar — och RLS-skiktet finns kvar som spärr mot framtida
-- roller (authenticated, anon) som aldrig ska se tabellen.

-- Rollvakten är samma mönster som 063/080: i en kedja som reses från noll
-- (railway_migrate från tom databas) kan rollen saknas när filen körs.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    drop policy if exists app_reset_tokens on public.password_reset_tokens;
    create policy app_reset_tokens on public.password_reset_tokens
      for all to snajp_web using (true) with check (true);
  end if;
end $$;
