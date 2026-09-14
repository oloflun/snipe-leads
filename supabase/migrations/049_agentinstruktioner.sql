-- Instruktionslagret blir REDIGERBART — och därmed mätbart.
--
-- ## Felet den här migrationen finns för att rätta
--
-- `agent_configs` har burit `instructions_md` och `tone` sedan 010. Ingenting
-- har någonsin LÄST dem. Inte agenten, inte API:t, inte dashboarden. Följden
-- var det som rapporterades 2026-08-24: en kund ändrar sina instruktioner och
-- svaren blir exakt likadana, för texten fanns aldrig i prompten.
--
-- Det enda kundskrivna som faktiskt nådde modellen var SOUL (017) och
-- kanalens `tone` i `ss_channel_configs`. Affärskontexten
-- (`agent_context_docs.kind='product_marketing'`) lästes bara av leads-agenten
-- och aldrig av supportagenten.
--
-- ## Två skikt, två positioner i prompten
--
-- GLOBALT (den här filens nya tabell) är VÅR text, skriven av en
-- plattformsadmin. Den motsvarar `agent-core/AGENTS.md` och går i
-- SYSTEMposition, först i kedjan, precis som filen gör i dag.
--
-- PER KUND (`agent_configs.instructions_md`) är också VÅR text — fältet är
-- avsiktligt admin-only, redigerbart från /admin/kunder/<slug> och INTE från
-- kundens egna inställningar. Därför går även den i SYSTEMposition.
--
-- Kundskriven text har inte flyttat: SOUL, affärskontext och kunskapsbas
-- ligger kvar i USERposition, wrappade som opålitligt innehåll. Den gränsen
-- ÄR säkerhetsmekanismen (INV-SEC-009, app/leads/soul.py) och den här
-- migrationen rör den inte. Att skilja på "vem skrev texten" i stället för
-- "vad handlar texten om" är hela poängen: ton går att be om, regler inte.
--
-- ## Varför råtext OCH strukturerad text sparas
--
-- Admin skriver löpande text och feedback. En modell strukturerar den till
-- AGENTS.md-form. Bara den strukturerade texten når prompten.
--
-- Råtexten sparas ändå, av två skäl. Struktureringen ska gå att köra om när
-- promptmallen förbättras, utan att någon behöver skriva om sina anteckningar.
-- Och när en agent betett sig oväntat är frågan alltid "vad bad vi om?" — den
-- frågan besvaras av råtexten, inte av modellens omskrivning av den.
--
-- ## Varför en INSERT-versionerad tabell och inte en rad som uppdateras
--
-- `agent_runs.pack_version` ska kunna peka ut exakt vilken instruktionstext en
-- körning läste (INV-AUDIT-001). En rad som skrivs över gör den frågan
-- obesvarbar dagen efter en ändring. En ny rad per sparning ger historiken
-- gratis, och `aktiv` pekar ut vilken som gäller nu.

create table if not exists public.agent_global_instructions (
  id uuid primary key default gen_random_uuid(),
  -- Vad admin faktiskt skrev, ordagrant. Aldrig i prompten.
  ravtext text not null default '',
  -- Modellens strukturerade version. DET HÄR är vad agenten läser.
  strukturerad_md text not null default '',
  -- Hur den strukturerade texten kom till. 'ai' = modellen strukturerade,
  -- 'manuell' = en människa skrev eller redigerade den direkt. Skillnaden
  -- betyder något vid felsökning: en manuellt redigerad text har inte
  -- passerat valideringen i app/agentcore/strukturera.py.
  kalla text not null default 'ai' check (kalla in ('ai', 'manuell')),
  aktiv boolean not null default true,
  uppdaterad_av uuid references auth.users(id),
  created_at timestamptz not null default now()
);

-- Exakt EN aktiv global instruktion. Villkoret ligger i databasen därför att
-- läsvägen (app/agentcore/instruktioner.py) plockar `where aktiv` utan
-- ordning — två aktiva rader hade gett ett godtyckligt val som varierar mellan
-- körningar och inte går att felsöka från loggen.
create unique index if not exists agent_global_instructions_en_aktiv
  on public.agent_global_instructions ((true)) where aktiv;

create index if not exists agent_global_instructions_historik
  on public.agent_global_instructions (created_at desc);

comment on table public.agent_global_instructions is
  'Plattformsövergripande agentinstruktioner, redigerade av admin. Ersätter '
  'agent-core/AGENTS.md i drift; filen är fallback när ingen aktiv rad finns. '
  'SYSTEMposition — det här är VÅR text, inte kundens.';

alter table public.agent_global_instructions enable row level security;

-- Ingen kundroll får läsa eller skriva. Tabellen är plattformens, inte
-- arbetsytans, och den är därför INTE grantad till snajp_web. Vägen in går via
-- backendens /api/admin (master-nyckel), som kör som snajp_app.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on public.agent_global_instructions to snajp_app;

    drop policy if exists "snajp_app agentinstruktioner"
      on public.agent_global_instructions;
    create policy "snajp_app agentinstruktioner"
    on public.agent_global_instructions for all
    to snajp_app
    using (true) with check (true);
  end if;
end $$;

-- Per kund: råtexten saknade kolumn. `instructions_md` finns sedan 010 och
-- får nu sin avsedda betydelse (den strukturerade texten som injiceras).
alter table public.agent_configs
  add column if not exists instructions_rav text not null default '';

comment on column public.agent_configs.instructions_md is
  'Strukturerad kundspecifik instruktion. ADMIN-ONLY (redigeras från '
  '/admin/kunder/<slug>), går i SYSTEMposition efter den globala. Kundskriven '
  'text hör hemma i SOUL, som går i USERposition — se app/leads/soul.py.';

comment on column public.agent_configs.instructions_rav is
  'Råtexten admin skrev, före strukturering. Aldrig i prompten.';

comment on column public.agent_configs.tone is
  'Fritt tonläge per kund och agenttyp. Läggs på ärendekontexten av '
  'app/agent/support_agent.py. Tom = kanalens tone i ss_channel_configs gäller.';
