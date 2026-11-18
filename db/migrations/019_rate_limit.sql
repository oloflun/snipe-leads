-- Rate limiting som överlever en omstart.
--
-- Dagens `app/api/rate_limit.py` är en process-lokal deque. Den skyddar bara
-- POST /api/demo/chat, och Render free-tier spinner ner efter 15 minuters
-- inaktivitet — varje uppvakning nollställer räknaren. I praktiken alltså
-- ingen spärr alls, bara en som ser ut som en.
--
-- Räknas i LLM-ANROP, inte i meddelanden. Ett supportsvar är sex skill-steg
-- och ett research-steg åtta; ett tak i meddelanden mäter alltså fel storhet
-- med en faktor sex till åtta.
--
-- Tabellen är avsiktligt platt (ingen tenant-kolumn, ingen FK): scope_kind
-- avgör vad scope_id betyder ('tenant' → ss_tenants.id, 'user' → auth.users.id,
-- 'ip' → en IP-sträng). En FK hade omöjliggjort IP-scopet och tvingat fram
-- tre tabeller för samma fråga.
--
-- RLS: på, med EN policy — och den gäller bara `snajp_app`. Tabellen rörs
-- enbart av backendens egen anslutning, aldrig via PostgREST, så anon och
-- authenticated saknar policy och är därmed nekade.
--
-- Policyn måste finnas: `snajp_app` skapades `nobypassrls` i 009, så "RLS på
-- utan policy" hade låst ute tjänsten själv den dagen DATABASE_URL byter från
-- postgres till snajp_app (INV-SEC-001, fortfarande öppen). Att upptäcka det
-- vid cutover i stället för här hade sett ut som ett anslutningsfel.

create table if not exists public.platform_rate_events (
  id bigserial primary key,
  scope_kind text not null check (scope_kind in ('tenant', 'user', 'ip')),
  scope_id text not null,
  kind text not null,
  created_at timestamptz not null default now()
);

-- Uppslaget är alltid "hur många events för den här nyckeln sedan T".
-- created_at desc gör fönsterfrågan till en indexskanning bakifrån.
create index if not exists platform_rate_events_lookup_idx
  on public.platform_rate_events (scope_kind, scope_id, kind, created_at desc);

-- Städning. Fönstret är en timme; allt äldre än ett dygn är rent avfall.
-- ponytail: ingen pg_cron-schemaläggning här — backenden städar opportunistiskt
-- i rate_limit_db.purge_old(). Flytta till pg_cron om raden blir het.
create index if not exists platform_rate_events_created_idx
  on public.platform_rate_events (created_at);

alter table public.platform_rate_events enable row level security;

drop policy if exists platform_rate_events_service on public.platform_rate_events;
create policy platform_rate_events_service on public.platform_rate_events
  for all to snajp_app using (true) with check (true);

-- Default-privilegierna i 009 ger select/insert/update men inte delete, och
-- ingenting på sekvensen. Städningen behöver båda.
grant select, insert, delete on table public.platform_rate_events to snajp_app;
grant usage, select on sequence public.platform_rate_events_id_seq to snajp_app;
