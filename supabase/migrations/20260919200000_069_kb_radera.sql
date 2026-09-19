-- snajp_app får radera artiklar i kunskapsbasen (DELETE /api/kb/{id}).
--
-- 009 gav `select, insert, update` på ss_knowledge_base, aldrig `delete` —
-- samma lucka som 041 lagade för ss_emails. Så länge ingen kodväg raderade
-- syntes den inte. Nu gör en: webbplatsskanningen (app/kb_skanning.py) fyller
-- basen med utkast ur kundens sajt, och en artikel som inte längre stämmer
-- måste gå att ta bort — annars citerar agenten den för alltid.
--
-- Radnivån är redan rätt: 003:s tenant_isolation-policy saknar `for` och
-- gäller alltså ALLA kommandon, DELETE inräknat (med 028:s NULLIF-vakt).
-- Ingen annan tabell refererar ss_knowledge_base, så inget kaskaderar.

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant delete on table ss_knowledge_base to snajp_app;
  end if;
end $$;
