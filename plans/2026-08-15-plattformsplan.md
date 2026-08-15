# Plattformsplan: säkerhet, kundvyer, admin master control

Källa: `~/.claude/plans/perfekt-k-r-ven-standup-swift-garden.md` (godkänd 2026-08-15).
Den här filen är projektlokal statusspegel — planens resonemang står i originalet.

## Scope

Sju faser: stänga den anonyma API-ytan, ge varje kund en vy som bara innehåller det de
betalar för, bygga en admin-vy som spårar allt ner till varje LLM-steg, och ge kunden
kontroll över hur långt leads-agenten får gå.

**Alla sju faser är kodklara** (2026-08-15). **Nio av tio migrationer är körda och
verifierade mot produktionsdatabasen**; `021_seed_platform_admin` väntar på att kontot
`snajpsupport@gmail.com` skapas. Se `MIGRATIONS-PENDING.md`.

## Completed

- [x] **Fas 0 — synk.** `snajp-redesign` fast-forwardad till `origin/main` (`c2ca092`),
      `.claude/launch.json` committad.
- [x] **Fas 1.1 — sessionshärledd tenant.** `lib/snajp/tenant.ts`,
      `app/api/snajp-support/_auth.ts`, `proxyWithApiKey()` bruten ur `proxyToBackend()`.
- [x] **Fas 1.2 — anonyma ytor avgränsade.** Chat, jobs och triage förblir öppna med
      skriven motivering i respektive fil.
- [x] **Fas 1.3 — RPC-härdning** (`018_rpc_hardening.sql`). Fyra `security definer`-
      funktioner hade EXECUTE till PUBLIC. Att bara revoka från `anon` räcker inte —
      PUBLIC-graden ärvs, så den revokas först i varje block.
- [x] **Fas 1.4 — rate limiting** (`019_rate_limit.sql` + `app/api/rate_limit_db.py`).
      Tre tak räknade i LLM-anrop: 400/h tenant, 120/h användare, 30/h demo-IP.
      Fail-open. Kontrollera-först, bokför-efter — taket kan överskridas med som mest
      en körning, dokumenterat som ponytail-ceiling i filen.
- [x] **Fas 1.5 — INV-SEC-010.** Statisk invariant över varje `route.ts` under
      `app/api/`, plus `scripts/verify_inv_sec_010.sh` för levande verifiering.
      Falsifierad mot en ohejdad route innan den litades på.
- [x] **Fas 2 — roller och inlogg.** `020_platform_admins.sql`,
      `021_seed_platform_admin.sql`, `lib/auth/admin.ts` (fail-closed, `server-only`),
      glömt-lösenord via callbacken, Google/Microsoft-OAuth, `lib/actions/team.ts`.
      `nextPath`-buggen (`/emails` → `/dashboard/emails`) fixad.
- [x] **Fas 3 — kundens vy.** Fail-closed entitlements, `app/settings/layout.tsx`
      (saknades helt — hela trädet körde på FALLBACK-kontexten),
      `022_workspace_addons.sql`, sex tillägg i `lib/addons.ts`, fem mock-drivna
      rutter bakom `preview`.
- [x] **Fas 4 — leads-kontroller.** `023`/`024`, `app/leads/autonomy.py` (en regel,
      två anropsplatser), `app/leads/icp.py`, körkontroll-endpoints,
      `/dashboard/leads/kontroll`.
- [x] **Fas 5 — ren kundchatt.** Badge-raden och lägespillret borta.
- [x] **Fas 6 — admin master control.** `026`/`027`, `app/api/admin.py`,
      cross-tenant-metoder i BÅDA lagringarna, `app/admin/**` grindad på tre nivåer,
      `app/api/events.py` med FastAPI-exception-handler.
- [x] **Fas 7 — samtalsform.** Historik i `case_context`, overlay på båda textstegen.
- [x] **Blockeraren** `025_agent_runs_fix.sql`, plus `AGENT_RUN_TYPES` i `base.py` så
      att MemoryStorage validerar samma värdemängd som Postgres.

## Verifierat

- 447 backend-tester + 1 överhoppad, 38 invarianter + 3 överhoppade.
- `npx tsc --noEmit` och `npx next build` rena.
- Levande mot lokal stack: alla åtta grindade routes ger 401 anonymt, demon svarar 202,
  `/admin` och `/api/admin/*` ger 404 utan adminrad, `/auth/reset` utan session visar
  "Länken gäller inte längre", inloggningen renderar OAuth-knappar och
  återställningslänk.
- `PUT /api/leads/config` med en insmugglad `system_prompt`-nyckel: nyckeln ströks,
  autonomin och ICP:n kom tillbaka oförändrade i övrigt.
- En riktig supportkörning: `/api/admin/tenants` visar rätt nyckeltal, och spårvyns
  `system_prompt` mäter exakt 8 000 tecken (kapningen verkställs).

- Mot produktionsdatabasen: alla nio körda migrationer verifierade med SQL. Rådgivaren
  flaggar inte längre `handle_new_user` eller `rls_auto_enable`. **Blockeraren är löst** —
  en `leads_research`-rad gick att spara i `agent_runs`, vilket den aldrig gjort.
  Testraden raderad.
- Två av tre nya tabeller har RLS på med exakt en policy vardera, scopad till `snajp_app`;
  `platform_admins` har läspolicy för `authenticated` och inga skrivpolicyer.

- Varje SQL-fråga `PostgresStorage` skickar kördes mot produktionsschemat. Tre
  kolumnbuggar hittades och rättades — de hade kraschat vid första riktiga anropet och
  syntes inte i sviten, eftersom den kör mot `MemoryStorage` där testernas seed hade
  hittat på fälten.

**Inte verifierat:** backenden saknar `DATABASE_URL` här (lösenordet bor bara på Render),
så Python-koden runt frågorna — anslutningshantering, `_scoped()`-transaktionen,
typkodningen — har aldrig kört mot Postgres.

## Blockers

- **`021_seed_platform_admin` kan inte köras** förrän `snajpsupport@gmail.com` finns i
  `auth.users`. Kontrollerat: kontot finns inte. Migrationen hade blivit en tyst no-op.
- **`snajp_app`-rollens lösenord osatt** (sedan 2026-08-07). Backenden kör som
  `postgres` med BYPASSRLS; varje `tenant_isolation`-policy är dekorativ för den
  anslutningen (INV-SEC-001).
- **`SNAJP_KEY_LIVRUSTNING` osatt på Vercel.**
- **`SNAJP_MASTER_API_KEY` måste sättas på Vercel** — annars svarar `/api/admin/*` 503.
- **Konsolmoment:** OAuth-appar hos Google Cloud och Microsoft Entra, leaked-password-
  skyddet i Supabase Auth, lösenordet till `snajpsupport@gmail.com`. Checklistor i
  `AUTH.md`.

## Deferred

- **Kvotgrenen mergas inte.** `feature/snajp-multitenant-saas` divergerade vid `32c58cd`.
  Plocka ut `app/billing/plans.py`, `quota.py`, `agent/usage.py`, `lib/billing/stripe.ts`
  och omnumrera migrationen till `028+` när kvotlogiken behövs.
- Fas A (onboarding) skriver ingen `agent_runs`-rad — den kör `Runner.run`. Känd lucka,
  visas i spårvyn som "ingen spårning" i stället för som tom data.
- `meeting`-nivån beter sig som `first_contact` för uppföljningar tills `handoff.py`
  får en produktionsanropare (`MEETING_REQUIRES_HANDOFF` i `autonomy.py`).

## Next Steps

1. Skapa `snajpsupport@gmail.com` på `/login` och kör `021`.
2. Sätt `SNAJP_MASTER_API_KEY` på Vercel — annars svarar `/api/admin/*` 503.
3. Kör en riktig leads-körning mot en testtenant och bekräfta att `agent_runs`-raden
   skapas av KODEN. Schemat tar emot den nu; att kodvägen gör det är oprövat, eftersom
   den aldrig kunnat köras mot Postgres härifrån.
4. `bash scripts/verify_inv_sec_010.sh https://<deploy>` efter deploy.
