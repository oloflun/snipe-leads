-- 113: Leveransutfall per utskick (Sebbe 2026-10-24).
--
-- Resends webhook (email.bounced, email.complained) skriver utfallet på det
-- skickade meddelandet, och send_guard regel 5e pausar tenantens utskick när
-- studsandelen eller klagomålen de senaste 14 dagarna går över gränserna.
-- Före det fanns ingen återkoppling alls: ~600 kallmejl gick ut utan att något
-- i systemet visste hur många som studsat eller markerats som skräppost.
alter table public.outreach_messages
  add column if not exists leverans text check (leverans in ('studs', 'klagomal')),
  add column if not exists leverans_at timestamptz;

create index if not exists outreach_messages_leverans_idx
  on public.outreach_messages (tenant_id, sent_at)
  where leverans is not null;
