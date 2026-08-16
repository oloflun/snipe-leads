-- Ett workspace har EN affärskontext. Villkoret har funnits i koden sedan
-- början men aldrig i databasen.
--
-- `getBusinessContextForWorkspace()` använde `.maybeSingle()`, som KASTAR på
-- fler än en rad. Onboardingen läste först och skrev sedan, så två sparningar
-- som råkade överlappa kunde skapa två rader — och därefter var arbetsytan
-- permanent trasig: varje sidladdning som hämtade affärskontexten föll, utan
-- att något i koden såg fel ut.
--
-- Med villkoret i databasen blir samma sak en upsert i stället för en kapplöpning.
-- Verifierat mot produktionen innan det lades till: noll dubbletter finns, så
-- indexet går att skapa utan städning.

create unique index if not exists business_contexts_workspace_id_key
  on public.business_contexts (workspace_id);
