# Plattformsplan: säkerhet, kundvyer, admin master control

Källa: `~/.claude/plans/perfekt-k-r-ven-standup-swift-garden.md` (godkänd 2026-08-15).
Den här filen är projektlokal statusspegel — planens resonemang står i originalet.

## Scope

Sju faser: stänga den anonyma API-ytan, ge varje kund en vy som bara innehåller det de
betalar för, bygga en admin-vy som spårar allt ner till varje LLM-steg, och ge kunden
kontroll över hur långt leads-agenten får gå.

## Completed

- [x] **Fas 0 — synk.** `snajp-redesign` fast-forwardad till `origin/main` (`c2ca092`),
      `.claude/launch.json` committad, 376 tester + `tsc` som utgångsläge.
- [x] **Fas 1.1 — sessionshärledd tenant.** `lib/snajp/tenant.ts`,
      `app/api/snajp-support/_auth.ts`, `proxyWithApiKey()` bruten ur `proxyToBackend()`.
      Catch-allen kräver inloggning; tenant ur `workspaces.slug`/`ss_tenant_id`.
- [x] **Fas 1.2 — anonyma ytor avgränsade.** Chat, jobs och triage förblir öppna med
      skriven motivering. Ingen separat `/api/snajp-demo`-route behövdes: de specifika
      routerna ÄR den anonyma ytan, och det var catch-allen som var hålet.
- [x] **Fas 5 — ren kundchatt.** Badge-raden och lägespillret borta. Plus en 320px-defekt
      som syntes först då: composern bryter till två rader under 360px.
- [x] **Fas 7 — samtalsform.** Historik i `case_context`, overlay på båda textstegen,
      `strip_dangling_sign_off()`, eget demo-session-id per flik. 12 nya tester.

## In Progress

- [ ] **Fas 1.3 — RPC-härdning** (migration `018_rpc_hardening.sql`).
      `handle_new_user()` och `rls_auto_enable()` är `security definer` och anropbara av
      `anon` via `/rest/v1/rpc/…`. Bekräftat av Supabase security advisor.
      Slå även på leaked-password-skyddet i Supabase Auth (konsolmoment).
- [ ] **Fas 1.4 — rate limiting** (migration `019_rate_limit.sql` +
      `snajp-support/app/api/rate_limit_db.py`). Dagens `rate_limit.py` är en
      process-lokal deque som bara skyddar demon och nollställs vid varje spin-down.
      Tre tak, räknade i LLM-anrop: 400/h per tenant, 120/h per användare, 30/h per demo-IP.
      Fail-open vid trasigt uppslag.
- [ ] **Fas 1.5 — INV-SEC-010.** Anonymt anrop mot varje route-fil under `app/api/`,
      kräver 401 utom för den allowlistade demon. Verifiera mot en medvetet trasig
      version innan testet litas på.

## Remaining

- [ ] **Fas 2 — roller och inlogg.** `platform_admins`-tabell (egen dimension, inte
      `profiles.role` som är workspace-scopad), `snajpsupport@gmail.com` som admin,
      glömt-lösenord, Google/Microsoft-SSO, skrivväg för `workspace_invites`.
      Buggfix på vägen: `nextPath` defaultar till `/emails` som inte finns.
- [ ] **Fas 3 — kundens vy.** Fail-closed entitlements (i dag faller `lib/data/dashboard.ts`
      tillbaka på BÅDA produkterna), `workspaces.addons`, sex låsta tilläggstjänster,
      `app/settings/layout.tsx` (saknas, så inställningarna kör på FALLBACK-kontexten).
- [ ] **Fas 4 — leads-kontroller.** Autonominivå (`draft` default), ICP-konfiguration,
      körkontroller, granskningskö.
- [ ] **Fas 6 — admin master control.** `app/api/admin.py`, cross-tenant-metoder på
      `Storage`, tre migrationer, `/admin`-route-gruppen.

## Blockers

- **`agent_runs.agent_type` avvisar det koden skriver.** Check-villkoret tillåter
  `('support','leads')`; `leads_agent.py` skriver `"leads_research"`/`"leads_outreach"`.
  Mot Postgres kastar båda check-violation, `MemoryStorage` har inget villkor.
  **Ingen leads-körning har någonsin sparats i produktion.** Blockerar hela Fas 6 —
  spårvyn har noll historik att visa. Fixas i `025_agent_runs_fix.sql`.
- **`snajp_app`-rollens lösenord osatt** (sedan 2026-08-07). Backenden kör som `postgres`
  med BYPASSRLS; varje `tenant_isolation`-policy är dekorativ för den anslutningen.
- **`SNAJP_KEY_LIVRUSTNING` osatt på Vercel.** Ger nu 503 i stället för fel kunds svar.

## Deferred

- **Kvotgrenen mergas inte.** `feature/snajp-multitenant-saas` divergerade vid `32c58cd`
  (21 fram, 34 bakom, 39 filer i konflikt, dubbla migrationssläktled 005–010).
  Plocka i stället ut `app/billing/plans.py`, `quota.py`, `agent/usage.py`,
  `lib/billing/stripe.ts` och omnumrera migrationen till `018+` när Fas 3 behöver dem.
- Fas A (onboarding) skriver fortfarande ingen `agent_runs`-rad — den kör `Runner.run`.
  Känd lucka, dokumenteras i admin-vyn som "ingen spårning" snarare än tom data.

## Next Steps

1. Migration 018 + 019, `rate_limit_db.py`, INV-SEC-010 — avsluta Fas 1.
2. Migration 025 (`agent_runs.agent_type`) tidigt, även om admin-UI:t dröjer: utan den
   samlas ingen spårdata och historiken går inte att rekonstruera i efterhand.
3. Fas 2, som Fas 3 och 4 bygger på.
