-- 114: kampanjutskick till befintliga listor (Anton 2026-10-25).
--
-- Ett kampanjmejl ("Hej Namn," och kampanjtexten) till en befintlig kund- eller
-- leadslista är inget kallmejl. Märkningen låter sändspärren släppa det till
-- kundens egna kunder (avregistreringar gäller som förut), och utfallet räknas
-- per kampanj (storage.kampanjens_poster). Kampanjens definition bor i
-- leads-inställningarna (settings.kampanjer); bara märkningen behöver en kolumn.
-- Additiv: köningen utan kampanj skriver aldrig kolumnen.

alter table public.outreach_messages add column if not exists kampanj_id text;

create index if not exists outreach_messages_kampanj_idx
  on public.outreach_messages (tenant_id, kampanj_id)
  where kampanj_id is not null;
