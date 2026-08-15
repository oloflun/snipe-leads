-- Notiscentret: fel över alla kunder, på ett ställe.
--
-- I dag finns inga FastAPI-exception-handlers alls och ingen middleware.
-- Ohanterade fel går till stdout på Render, där de rullar förbi och
-- försvinner vid nästa spin-down. Tre ställen i leads-koden sväljer dessutom
-- fel utan spår (leads_agent.py runt rad 269, scheduler.py 70-72 och 92-93).
-- Följden är att "det funkar inte för kunden" bara går att felsöka genom att
-- be kunden göra om det medan man tittar.
--
-- tenant_id är NULLABLE med flit: plattformsnivåfel (proxyn, schemaläggaren
-- innan den vet vilken kund den jobbar för) hör hemma här också, och en
-- not-null-kolumn hade tvingat fram en påhittad tenant för dem.

create table if not exists public.platform_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.ss_tenants(id) on delete cascade,
  level text not null check (level in ('error', 'warning', 'info')),
  source text not null,
  message text not null,
  -- traceback, run_id, steg, request-id. Jsonb och inte kolumner: vad som är
  -- värt att spara skiljer sig per källa, och en kolumn per fält hade blivit
  -- en tabell med trettio nullbara kolumner varav tre används åt gången.
  detail jsonb not null default '{}'::jsonb,
  run_id uuid references public.agent_runs(id) on delete set null,
  created_at timestamptz not null default now()
);

-- Notiscentret frågar alltid "senaste felen", ibland filtrerat på kund.
create index if not exists platform_events_level_idx
  on public.platform_events (level, created_at desc);
create index if not exists platform_events_tenant_idx
  on public.platform_events (tenant_id, created_at desc);

alter table public.platform_events enable row level security;

-- Samma resonemang som platform_rate_events i 019: enda skrivaren och läsaren
-- är backendens egen anslutning. Policyn måste ändå finnas, eftersom
-- snajp_app är nobypassrls (009) och "RLS på utan policy" hade låst ute
-- tjänsten vid cutover.
drop policy if exists platform_events_service on public.platform_events;
create policy platform_events_service on public.platform_events
  for all to snajp_app using (true) with check (true);

grant select, insert, delete on table public.platform_events to snajp_app;
