-- Migration 010 skapade outreach_messages utan en subject-kolumn.
-- sa:draft-outreach producerar alltid ett ämne tillsammans med brödtexten
-- (Del F Fas C) — utan kolumnen skulle varje utskick gå ut med tomt ämne.
-- Upptäckt när app/agent/leads_tools.py kopplade ihop utkastflödet på riktigt.

alter table outreach_messages add column if not exists subject text not null default '';
