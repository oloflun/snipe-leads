-- Kundminne — supportagenten minns vad kunden själv berättat.
--
-- ## Mönstret, och varifrån det är hämtat
--
-- mem0:s tvåstegsarkitektur (extraction -> update) i sin token-effektiva
-- ADD-only-variant: fakta extraheras en gång, läggs till, och skrivs aldrig
-- om eller raderas av pipelinen — historiken bevaras och uppdateringslogiken
-- (mem0:s ADD/UPDATE/DELETE-beslut) skjuts tills behovet bevisats. Zep-stilens
-- temporala kunskapsgraf är medvetet INTE med: en supportkunds fakta är en
-- handfull rader, inte en graf.
--
-- ## Kontamineringsspärren (MemGuard-klassens risk)
--
-- Minnet bär ENBART vad KUNDEN SJÄLV uppgett — aldrig agentens slutsatser,
-- aldrig sentiment, aldrig kategoriseringar. Ett minne som lagrar modellens
-- egna tolkningar och matar tillbaka dem blir självförstärkande: en
-- felläsning i ärende 1 blir "fakta" i ärende 2 och omöjlig att skilja från
-- kunskap. Samma beslut som INV-LEARN-001, tillämpat på kundnivån.
-- Extraktionen sker i triagesteget (noll extra LLM-anrop) och injektionen
-- är ALLTID wrappad som opålitligt innehåll i user-position — kundhärledd
-- text är kundskriven text (INV-SEC-009).
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

create table if not exists customer_memory (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references ss_tenants(id) on delete cascade,
  customer_id uuid not null references ss_customers(id) on delete cascade,
  -- En kort, stabil faktarad i klartext ("Har en Android-telefon",
  -- "Beställde 14 augusti, ordernummer uppgivet"). Klartext och inte jsonb:
  -- raden ÄR injektionsformatet, och en struktur hade krävt en rendering
  -- som kan glida ifrån det som faktiskt sparades.
  fakta       text not null,
  created_at  timestamptz not null default now()
);

create index if not exists customer_memory_kund_idx
  on customer_memory (tenant_id, customer_id, created_at desc);

alter table customer_memory enable row level security;
alter table customer_memory force row level security;
drop policy if exists tenant_isolation on customer_memory;
create policy tenant_isolation on customer_memory
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);
