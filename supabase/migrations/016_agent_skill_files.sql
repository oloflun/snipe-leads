-- Verifierad spegel av agent-core/skills/.
--
-- VAD DEN ÄR: en frågbar post över exakt vilken text en agent_runs-rad
-- producerades ur. Kombinerad med agent_runs.pack_version går det att svara
-- på "vad läste modellen den 14 augusti?" utan att checka ut en gammal commit.
--
-- VAD DEN INTE ÄR: en uppdateringskanal. Git är källa till sanning. Kan
-- databasen leverera skill-text som containern inte har på disk är git bara
-- källa till sanning i intentionen — och INV-SKILL-005 (som hashar
-- FILSYSTEMET) skulle sluta vara ett lås. Därför:
--   * app.config.skill_source defaultar till "filesystem" i ALL miljö
--   * render.yaml sätter aldrig SKILL_SOURCE (INV-DEPLOY-001 verifierar det)
--   * registry verifierar varje rads sha256 mot det PINNADE manifestet och
--     felar stängt vid avvikelse (INV-SKILL-007)
--
-- NYCKLAD PÅ manifest_hash, inte på "senaste". Det löser versionsskev
-- STRUKTURELLT: en container frågar alltid på SIN egen utcheckade
-- manifest_hash, så en nyare publicering hamnar under ett annat hash och är
-- osynlig för den. Skev kan alltså inte uppstå — bara "mina rader saknas",
-- vilket är ett tydligt fel med en tydlig åtgärd i stället för ett tyst
-- beteendeskifte.
--
-- Ingen tenant_id: delad baselinekatalog, precis som agent_skill_packs.

create table if not exists agent_skill_files (
  id uuid primary key default gen_random_uuid(),
  manifest_hash text not null,
  namespace text not null check (namespace in ('mk', 'cs', 'sa', 'snajp')),
  relative_path text not null,          -- t.ex. 'cold-email/SKILL.md'
  content text not null,
  sha256 text not null,
  byte_size int not null,
  published_at timestamptz not null default now(),
  published_by text not null default '',
  unique (manifest_hash, namespace, relative_path)
);

create index if not exists agent_skill_files_lookup_idx
  on agent_skill_files(manifest_hash, namespace, relative_path);

alter table agent_skill_files enable row level security;
alter table agent_skill_files force row level security;
drop policy if exists skill_files_read_all on agent_skill_files;
create policy skill_files_read_all on agent_skill_files for select using (true);

-- Samma princip som agent_skill_packs: tjänsten får LÄSA sina skills, aldrig
-- skriva dem. "Tjänsten kan inte skriva om sina egna skills" blir en
-- DB-garanti i stället för en konvention. Migration 009:s
-- "alter default privileges" ger annars snajp_app insert/update automatiskt
-- på varje ny tabell — det motverkas explicit här.
grant select on table agent_skill_files to snajp_app;
revoke insert, update, delete on table agent_skill_files from snajp_app;
