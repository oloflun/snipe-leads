-- 063: Kvittohanteraren — kvittofälten på bk_underlag.
--
-- Bokföringsagenten byggs om till Kvittohanteraren (2026-09-16). Kvitton kan
-- nu komma in via kundens MEJL (Gmail/Outlook, read-only) utöver uppladdning,
-- och ett utländskt belopp sparas som original utan att räknas om.
--
-- OBS: körs via scripts/railway_migrate.py mot Railway — katalognamnet är
-- historiskt, filen ska aldrig köras mot Supabase (se CLAUDE.md).

alter table bk_underlag
  add column if not exists kalla text not null default 'uppladdning'
    check (kalla in ('uppladdning', 'mejl')),
  add column if not exists mejl_id text,
  add column if not exists mejl_amne text,
  add column if not exists mejl_avsandare text,
  add column if not exists valuta text not null default 'SEK',
  add column if not exists belopp_original text;

comment on column bk_underlag.kalla is
  'Var kvittot kom ifrån: uppladdning eller mejl (Kvittohanteraren, 063).';
comment on column bk_underlag.mejl_id is
  'Mejlleverantörens meddelande-id när kalla=mejl. Fingeravtrycket i sha256-kolumnen räknas ur det.';
comment on column bk_underlag.valuta is
  'SEK när brutto bär beloppet. Annars valutakoden, och då är brutto tomt och belopp_original satt.';
