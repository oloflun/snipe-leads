-- 090: Lösenordsåterställning via mail — token-tabellen.
--
-- Flödet (lib/actions/auth.ts): requestPasswordReset skapar en rad med en
-- SHA-256-hash av en engångstoken och mejlar länken; updatePassword förbrukar
-- raden atomiskt (used_at sätts i samma UPDATE som validerar den). Själva
-- token lagras ALDRIG — läcker tabellen läcker inga användbara länkar.
--
-- En rad kan bara peka på en BEFINTLIG användare (FK mot auth.users). Det är
-- databasens halva av kravet att återställningen aldrig kan bli en väg att
-- skapa konton: länken byter lösenord på en rad som redan finns, ingenting mer.
--
-- RLS utan policies, samma mönster som workspace_tenant_keys: appens
-- RLS-skopade vägar (sqlAsUser) ser noll rader; bara den privilegierade
-- server-action-vägen når tabellen.

create table if not exists public.password_reset_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  token_hash text not null unique,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz
);

create index if not exists password_reset_tokens_user_idx
  on public.password_reset_tokens (user_id);

alter table public.password_reset_tokens enable row level security;
