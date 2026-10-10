-- 096: Kvittohanterarens granskning — grundpromptens fulla avläsning per underlag.
--
-- Kvittohanteraren utgår sedan 2026-10-06 från en fast grundprompt
-- (agent-core/prompts/kvittohanterare-systemprompt.md). Den läser ut fler fält
-- än bk_underlags platta kolumner rymmer — säkerhet och källa per fält,
-- dokumenttyp, betalningsuppgifter, flaggor, kontrollräkningar — och sätter en
-- status ur avsnitt 9.2. Allt det sparas här:
--
--   granskning         jsonb: promptens underlagsobjekt (belopp som strängar)
--                      plus meddelandeklassen och den interna noteringen.
--                      Bankgiro/plusgiro/IBAN härifrån är vad nästa faktura
--                      från samma leverantör jämförs mot (avsnitt 8.3).
--   granskningsstatus  KLAR_FÖR_GRANSKNING | BEHÖVER_GRANSKNING |
--                      PRIORITERAD_GRANSKNING | KRÄVER_MANUELL_HÄMTNING
--
-- `status` (klar/granska_manuellt) är oförändrad och avgör fortfarande om
-- underlaget räknas i summor och får ett verifikatförslag.
--
-- kvitto_mejl_lasta: fingeravtrycken för mejl som lästs men INTE gav något
-- underlag (nyhetsbrev, offerter). Utan den lästes samma mejl av modellen vid
-- varje skanning. Fingeravtrycket är samma sha256("mejl:adress:id") som
-- bk_underlag.sha256 — mejlets innehåll sparas inte, bara klassen.
--
-- OBS: körs via scripts/railway_migrate.py mot Railway — katalognamnet är
-- historiskt, filen ska aldrig köras mot Supabase (se CLAUDE.md).
-- Idempotent enligt husets regel: kan köras om utan verkan.

alter table public.bk_underlag
  add column if not exists granskning jsonb,
  add column if not exists granskningsstatus text;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'bk_underlag_granskningsstatus_check'
  ) then
    alter table public.bk_underlag
      add constraint bk_underlag_granskningsstatus_check
      check (
        granskningsstatus is null
        or granskningsstatus in (
          'KLAR_FÖR_GRANSKNING',
          'BEHÖVER_GRANSKNING',
          'PRIORITERAD_GRANSKNING',
          'KRÄVER_MANUELL_HÄMTNING'
        )
      );
  end if;
end $$;

comment on column public.bk_underlag.granskning is
  'Kvittohanterarens avläsning enligt grundprompten (096): fält med säkerhet/källa, flaggor, kontrollräkningar.';
comment on column public.bk_underlag.granskningsstatus is
  'Status ur grundpromptens avsnitt 9.2 (096). Ingen status betyder godkänt — det gör alltid en människa.';

create table if not exists public.kvitto_mejl_lasta (
  tenant_id     uuid not null references public.ss_tenants(id) on delete cascade,
  fingeravtryck text not null,
  klass         text not null,
  last_at       timestamptz not null default now(),
  primary key (tenant_id, fingeravtryck)
);

alter table public.kvitto_mejl_lasta enable row level security;

drop policy if exists kvitto_mejl_lasta_tenant_isolation on public.kvitto_mejl_lasta;
create policy kvitto_mejl_lasta_tenant_isolation on public.kvitto_mejl_lasta
  for all to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

grant select, insert, update, delete on public.kvitto_mejl_lasta to snajp_app;
