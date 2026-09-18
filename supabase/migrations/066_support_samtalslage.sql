-- Samtalsläge för supportchatten — sömlös överlämning till människa.
--
-- ## Varför en tabell, och varför nu
--
-- Varje chattmeddelande öppnar ett eget ärende (se support_agent.py), så
-- "samtalet" är en KUND, inte ett ärende. Tre saker måste överleva mellan
-- två meddelanden i samma samtal, och ingen av dem gick att läsa ut ur
-- ärendena:
--
--   * att samtalet är ÖVERLÄMNAT — en människa äger det, och agenten ska
--     inte svara med AI förrän människan lämnar tillbaka det;
--   * hur många MISSLYCKADE rundor i följd agenten haft (motfrågor, kund som
--     säger att svaret missade) — taket per tenant läses mot den räknaren;
--   * att agenten ERBJUDIT en människa, så att kundens "ja" blir en
--     begäran och inte en ny fråga att söka på.
--
-- En rad per (tenant, kund). Saknas raden gäller standardläget: agenten
-- svarar, noll misslyckade rundor, inget erbjudande ute.
--
-- ## ss_messages.author
--
-- En utgående rad kan numera komma från en MÄNNISKA (medarbetaren som svarar
-- i portalens Chattar-vy). Chattfönstret visar den som medarbetarens replik,
-- och agenten läser den som "Kollegan:" i samtalsutskriften i stället för
-- "Du:" — agenten ska veta vad en människa lovat, inte tro att den sagt det
-- själv. NULL = äldre rad: inbound är kunden, outbound är agenten.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

alter table ss_messages add column if not exists author text;
alter table ss_messages drop constraint if exists ss_messages_author_check;
alter table ss_messages add constraint ss_messages_author_check
  check (author is null or author in ('customer', 'agent', 'human'));

create table if not exists ss_chat_state (
  tenant_id            uuid not null references ss_tenants(id) on delete cascade,
  customer_id          uuid not null references ss_customers(id) on delete cascade,
  -- 'agent' = AI:n svarar. 'overlamnad' = en människa äger samtalet.
  lage                 text not null default 'agent'
                         check (lage in ('agent', 'overlamnad')),
  misslyckade_i_rad    integer not null default 0 check (misslyckade_i_rad >= 0),
  erbjod_manniska      boolean not null default false,
  -- Orsakskoden (support_regler.ORSAKER), inte fritext: portalen och
  -- analysen grupperar på den. Fritextmotiveringen står på ärendet
  -- (ss_tickets.escalation_reason) som förut.
  overlamnad_orsak     text,
  overlamnad_ticket_id uuid references ss_tickets(id) on delete set null,
  overlamnad_at        timestamptz,
  -- Samtalets språk (ISO 639-1, t.ex. 'sv', 'en'), satt av agentens senaste
  -- tur. Läses av kvittensen under en överlämning, som inte kör någon modell
  -- och därför inte kan avgöra språket själv. NULL = svenska.
  sprak                text,
  updated_at           timestamptz not null default now(),
  primary key (tenant_id, customer_id)
);

create index if not exists ss_chat_state_overlamnad_idx
  on ss_chat_state (tenant_id, updated_at desc) where lage = 'overlamnad';

alter table ss_chat_state enable row level security;
alter table ss_chat_state force row level security;
drop policy if exists tenant_isolation on ss_chat_state;
create policy tenant_isolation on ss_chat_state
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);
