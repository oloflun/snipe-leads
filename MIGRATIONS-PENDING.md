# Migrationer — status

Tio migrationer skrivna 2026-08-15. **Nio är körda och verifierade mot
produktionsdatabasen.** En återstår och kan inte köras än, av ett skäl som
inte är tekniskt.

## Körda och verifierade

| Migration | Verifierat med |
|---|---|
| `018_rpc_hardening` | `pg_proc.proacl` visar varken PUBLIC (`=X`) eller `anon` på `handle_new_user` och `rls_auto_enable`. `ensure_workspace_for_current_user` har kvar `authenticated=X` — utan den går ingen att logga in. Supabase säkerhetsrådgivare flaggar inte längre någon av de två. |
| `018b` (tillägg) | `current_workspace_id()` har nu låst `search_path`. Rådgivarens `function_search_path_mutable` för den är borta. |
| `019_rate_limit` | `platform_rate_events` finns, RLS på, en policy (`snajp_app`), sekvensgrant satt. |
| `020_platform_admins` | RLS på, `platform_admins_self_read` för `authenticated`, **inga skrivpolicyer**. |
| `022_workspace_addons` | Check-villkoret räknar upp de sex tilläggen. |
| `023_agent_config_settings` | `send_queue_status_check` innehåller `awaiting_review`. Autonomi-villkoret på plats. Inga befintliga `agent_configs`-rader att sätta default på — varje ny rad får `draft` från koden. |
| `024_prospect_icp_fit` | `icp_fit`, `qualified`, `disqualifiers` finns med index. |
| `025_agent_runs_fix` | **Blockeraren är löst.** En rad med `agent_type='leads_research'` gick att spara i produktionsdatabasen, vilket den aldrig gjort. Testraden raderad efteråt. |
| `026_platform_events` | RLS på, en policy (`snajp_app`), tabellen svarar på `select count(*)`. |
| `027_step_traces` | Kommentar och `agent_runs_tenant_created_idx` på plats. |

## Återstår

### `021_seed_platform_admin.sql`

Kan inte köras än: `snajpsupport@gmail.com` finns **inte** i `auth.users`
(kontrollerat). Migrationen hade blivit en tyst no-op.

1. Registrera kontot på `/login` → fliken "Skapa konto".
2. Kör migrationen — den är idempotent.
3. Verifiera:
   ```sql
   select u.email, pa.granted_at
   from public.platform_admins pa join auth.users u on u.id = pa.user_id;
   ```
4. Den riktiga verifieringen: `/admin` ska ge 404 för ett vanligt konto och
   200 för admin-kontot.

Lösenordet sätter du. Aldrig en agent, aldrig en migration.

## Fortfarande öppet — inte migrationer

1. **`SNAJP_MASTER_API_KEY` på Vercel.** Utan den svarar `/api/admin/*` med
   503 och ett meddelande som namnger variabeln.
2. **`snajp_app`-rollens lösenord** är osatt sedan 2026-08-07. Tills det är
   satt kör backenden som `postgres` med BYPASSRLS, och varje
   `tenant_isolation`-policy är dekorativ för den anslutningen (INV-SEC-001).
   **De två nya tabellernas policyer gäller `snajp_app`** — de är alltså
   skrivna för den dag rollen faktiskt används, och otestade tills dess.
3. **`SNAJP_KEY_LIVRUSTNING` på Vercel.**
4. **Leaked-password-skyddet** i Supabase Auth → Providers → Email. Rådgivaren
   flaggar det fortfarande.
5. **OAuth-konsolerna** (Google Cloud, Microsoft Entra). Checklista i `AUTH.md`.

## Kvarvarande rådgivarvarningar som är avsiktliga

- `current_workspace_id()` går att anropa som `anon` och `authenticated`.
  Avsiktligt: den anropas inifrån varje workspace-scopad RLS-policy, och de
  policyerna gäller rollen `public`. Utan graden får anon ett behörighetsfel
  i stället för noll rader — samma resultat, sämre form. Funktionen läser
  bara anroparens egen workspace via `auth.uid()` och läcker ingenting.
- `ensure_workspace_for_current_user()` går att anropa som `authenticated`.
  Krävs — `app/auth/callback/route.ts` anropar den efter inloggning.
- `vector` i public-schemat och `chorus_*`-funktionernas search_path är äldre
  än det här arbetet och rörs inte här.

## Vad som fortfarande INTE är verifierat

Backenden har ingen `DATABASE_URL` i den här miljön, så hela Python-stacken
har bara körts mot `MemoryStorage`. Schemat är verifierat med SQL direkt mot
produktionen (ovan), men **ingen kodväg har läst eller skrivit de nya
tabellerna via `PostgresStorage`.**

Kvarstår att göra efter deploy:

```bash
bash scripts/verify_inv_sec_010.sh https://<deploy>
```

och en riktig leads-körning mot en testtenant, för att se en `agent_runs`-rad
skapas av koden och inte av en handskriven insert.
