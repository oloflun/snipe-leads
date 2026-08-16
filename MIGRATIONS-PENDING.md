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

## Skrivna 2026-08-16 — INTE körda mot produktionen

Båda går via preview-grenen först, enligt DEPLOY.md:s ordning. De applicerades
alltså av Supabase-integrationen vid push till `development`, inte för hand.

### `030_suppressions_tenant_scope.sql`

Ger `public.suppressions` en `tenant_id`-kolumn.

**Varför:** tabellen var workspace-skopad och lästes bara av dashboarden. Koden
som avgör om ett mejl går iväg — `send_guard` regel 3 — kör i backenden, som
bara känner `tenant_id`. Utan kolumnen skrevs avregistreringen på ett ställe
och kontrollerades inte alls på det andra: den som klickat "avregistrera" hade
fått nästa utskick ändå.

En kolumn, inte en ny tabell. Två suppressionslistor som kan säga emot varandra
är värre än ingen — vilken som gällde hade avgjorts av vilken kodväg som råkade
fråga, och den frågan besvaras alltid efter att mejlet gått.

Backfillen är en no-op i dag: `suppressions` har noll rader i produktionen
(kontrollerat).

### `031_prospect_nischfalt.sql`

Ger `public.prospects` sju nischfält, `score_breakdown`, `score_total` och en
genererad `foretagsnyckel`.

**Varför:** tabellen hade company_name, contact_name, contact_email,
language_state, status, icp_fit, qualified och disqualifiers — alltså inget av
orgnr, ort, postnr, sni, hemsida, anställda eller omsättning. Det är exakt de
fält DEL 1:s källor producerar och scoringen dömer på. Utan dem kunde en
körning hitta rätt bolag men bara spara namnet, och `send_guard` regel 5:s
karens per företag hade saknat nyckel att räkna på.

`foretagsnyckel` är GENERERAD och får inte skrivas av koden: två uträkningar av
samma nyckel är två tillfällen att räkna olika, och den skillnaden syns först
när ett dubbelutskick redan gått. Uttrycket är verifierat mot produktionen — det
ger samma svar som `send_guard.foretagsnyckel()` i Python (`556824-9022` →
`5568249022`, tomt org.nr → e-postdomänen), och alla ingående funktioner är
`immutable`, vilket krävs för en `stored`-kolumn.

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
2. **`snajp_app`-rollens lösenord är nu satt** (2026-08-15, med ditt
   godkännande). Rollen är `nobypassrls` och verifierad: RLS-isoleringstestet
   kördes skarpt mot produktionen som den rollen och gav noll rader för fel
   tenant. Det är första gången INV-SEC-001 är BEVISAD och inte bara påstådd.

   **Men cutovern är blockerad av `028` — läs nästa avsnitt innan du byter
   DATABASE_URL på Render.**

   Lösenordet står i klartext i den här sessionens transkript, eftersom det
   fick skrivas in i ett SQL-anrop. Rotera med en rad om det stör:
   `alter role snajp_app with password '<nytt>';`
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

## 028 — MÅSTE köras innan DATABASE_URL byts till snajp_app

**Skriven men INTE applicerad.** Den skriver om 33 RLS-policyer i produktionen,
och det ska du se först.

Uppmätt mot produktionen: `set_config('app.tenant_id', <id>, true)` är
transaktionslokal, men efter COMMIT återgår GUC:en till `''` — inte NULL. En
custom-GUC som aldrig satts på sessionsnivå har tom sträng som utgångsvärde,
och varken `RESET` eller `set_config(..., NULL, false)` gör den NULL igen
(båda testade).

Följden på en POOLAD anslutning: så fort en skopad fråga har körts möter varje
senare **oskopad** fråga policyer som gör `''::uuid` och kastar
`invalid input syntax for type uuid: ""`.

Vad som går sönder vid cutovern:

- `ss_tenants.tenant_lookup` (`current_setting(...) IS NULL`) slutar gälla, och
  `tenant_self` kastar på castet. **`list_tenants()` är det schemaläggaren
  använder för att räkna upp kunder.**
- `list_agent_runs_all`, `get_agent_run`, `list_platform_events` — adminvyns
  oskopade läsningar — kastar likadant.
- Dessutom, redan verifierat: `list_agent_runs_all` ger **noll rader** under
  `snajp_app` även utan kraschen, eftersom `agent_runs.tenant_isolation` kräver
  ett satt `app.tenant_id`. Adminvyn hade visat en tom lista som ser ut som
  "inga körningar" i stället för som ett fel. `list_tenants_with_stats` ger då
  fyra kunder med nollställda siffror — **trovärdiga men fel tal**, vilket är
  värre än tomt.

Buggen har legat latent sedan multi-tenancy infördes. Ingen har märkt den
eftersom backenden kör som `postgres` med BYPASSRLS och policyerna aldrig
evalueras.

## SQL-vägarna — verifierade utan att kunna köra koden

Backenden har ingen `DATABASE_URL` i den här miljön (lösenordet bor bara på
Render), så `PostgresStorage` går inte att köra härifrån. I stället kördes
**exakt de frågor metoderna skickar** mot produktionsschemat. Det fångade tre
buggar som hade kraschat vid första riktiga anropet:

1. `list_review_queue` sorterade på `om.created_at` — `outreach_messages` har
   ingen sådan kolumn.
2. Samma query läste `t.prospect_email` — `outreach_threads` har `prospect_id`.
3. Följdfynd, äldre än det här arbetet: `get_outreach_thread` returnerade
   `select *`, och `scheduler.py` läser `prospect_email` ur resultatet. Mot
   Postgres hade varje utskick adresserats till strängen `"okänd"`.

Alla tre rättade och omkörda. Läsvägarna ger riktiga rader
(`list_tenants_with_stats` → fyra kunder); skrivvägarna kördes och städades:
`generate_series`-inserten, upserten på `agent_configs`, `platform_events` och
den dynamiska SET-listan i `update_prospect`.

**Uppdatering:** Python-koden HAR nu körts mot Postgres, som `snajp_app`.
`PostgresStorage` exercerades skarpt — `list_tenants_with_stats`,
`get_agent_settings`, `set_agent_settings`, `list_review_queue`,
`count_rate_events`, `record_rate_events`, `log_platform_event`,
`list_platform_events`. All testdata raderad och frånvaron kontrollerad.
Hela sviten kör nu 448 gröna med **noll överhoppade** — RLS-testet kördes för
första gången.

Det var den körningen som hittade `028` ovan.

Kvarstår att göra efter deploy:

```bash
bash scripts/verify_inv_sec_010.sh https://<deploy>
```

och en riktig leads-körning mot en testtenant, för att se en `agent_runs`-rad
skapas av koden och inte av en handskriven insert.
