-- 100: Snajps egen säljlista (Sebbes beställning 2026-10-06).
--
-- Snajp börjar ringa ut för att få in kunder. Listan är Snajps EGEN CRM över
-- bolagen vi ringt: företagsnamn, organisationsnummer, kontaktperson,
-- kontaktnummer, kontaktmail, senast kontaktad och anteckningar — samma
-- kolumner som kalkylarket den ersätter. Den redigeras i Leads › Listor i
-- adminvyn (components/leads/Saljlista.tsx, lib/actions/saljlista.ts).
--
-- ## Varför en egen tabell och inte lead_lists
--
-- lead_lists/lead_list_items är KUNDERNAS listor, scopade på arbetsyta och
-- lästa av upptagna.py som uteslutningsmängd för Iris. Snajps säljsamtal är
-- plattformens, inte en arbetsytas, och ska aldrig påverka vad kundernas Iris
-- hittar. Tabellen bär därför ingen workspace_id.
--
-- ## Behörighet
--
-- Webben ansluter som snajp_web, som inte är RLS-befriad (se 091). Policyn
-- släpper bara igenom den vars app.user_id står i platform_admins — samma
-- villkor som getPlatformAdmin() i lib/auth/admin.ts, fast i databasen, så
-- att en server action som glömt grinden ändå inte når raderna. Uppslaget i
-- platform_admins går genom dess egen policy platform_admins_self_read, som
-- släpper igenom den egna raden.
--
-- Idempotent.

create table if not exists public.snajp_saljlista (
  id uuid primary key default gen_random_uuid(),
  foretagsnamn text not null default '',
  orgnr text not null default '',
  kontaktperson text not null default '',
  kontaktnummer text not null default '',
  kontaktmail text not null default '',
  senast_kontaktad date,
  anteckningar text not null default '',
  skapad_av uuid,
  uppdaterad_av uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists snajp_saljlista_skapad
  on public.snajp_saljlista (created_at desc);

comment on table public.snajp_saljlista is
  'Snajps egen säljlista (CRM över bolag vi ringt). Plattformens, inte en '
  'arbetsytas — läses och skrivs bara av plattformsadmin via webben.';

alter table public.snajp_saljlista enable row level security;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant select, insert, update, delete on public.snajp_saljlista to snajp_web;

    drop policy if exists saljlista_plattformsadmin on public.snajp_saljlista;
    create policy saljlista_plattformsadmin on public.snajp_saljlista
      for all to snajp_web
      using (
        exists (
          select 1 from public.platform_admins pa
          where pa.user_id = nullif(current_setting('app.user_id', true), '')::uuid
        )
      )
      with check (
        exists (
          select 1 from public.platform_admins pa
          where pa.user_id = nullif(current_setting('app.user_id', true), '')::uuid
        )
      );
  end if;
end $$;
