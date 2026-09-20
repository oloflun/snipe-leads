# Lanseringsuppdraget 2026-09-20 — status per punkt + GO/NO-GO

Beställningen: tenant-isolering granskad med formell dom, Snajp som egen
intern Iris-kund, GDPR-säker utskicksinfrastruktur, 2 månaders gratis trial,
och org.nummer-fältet förberett. Allt nedan ligger på `development` i den här
pushen. `main` är inte rörd.

---

## 1. Tenant-isolering — **GO, med två villkor före externa kunder**

### Vad som granskades och hur

Statisk genomgång av hela identitetskedjan (API-nycklar → `app.tenant_id` →
RLS i 60+ tabeller, Next-sidans session → `current_workspace_id()`, bryggan
`workspace_tenant_keys`) plus **skarp live-testning mot Railway development**:
två färska granskningstenants skapades, data lades som A på alla tre
agenternas ytor, och åtkomst försöktes som B, som demonyckel, som masternyckel
och anonymt. Allt städat efteråt.

**21 av 21 skarpa kontroller höll:**

- IDOR: B fick 404 på A:s prospekt (läs + skriv), KB-artikel (radera), kvitto
  (godkänn), annan tenants ticket och jobb-id. A:s data syntes aldrig i B:s
  listor eller CSV-export.
- Nyckelklasserna: demonyckel → 404 mot kunddata, masternyckel → 403, ingen/
  ogiltig nyckel → 401. Anonyma webbjobbroutens `?tenant=`-slug ger 404 över
  tenantgränsen.
- RLS direkt i databasen som `snajp_app`: B-skopad session får noll rader av
  A:s prospekt/KB/kvitton. Båda approllerna är `nosuperuser, nobypassrls`.
  Alla publika tabeller har RLS; deny-all-listan är exakt de fyra avsiktliga
  (`workspace_tenant_keys`, `ss_gallringspolicy`, `mirror_meta`,
  `platform_admin_bootstrap`).
- Demodata: inga exempelbolag utanför demotenanterna, ingen Nordlys-KB i
  riktiga kunders baser.
- **Redis-svarscachens tenant-taggfilter är nu liveverifierat** mot dev-Redis
  (Query Engine): fel tenant = miss, rätt tenant = träff. Det var kodbasens
  enda oskattade isoleringsyta (klassens egen docstring sa "aldrig körd mot
  riktig Redis"). Bifynd: redis-py 8 ger FT.SEARCH-svaret i dict-form som
  gamla tolkningen missade — cachen gav ALDRIG träff live (tyst, fail-safe).
  Lagat i `svarscache._tolka_traff` + regressionstest.

### Fixat under granskningen

- **Fakturasekvens-säkerheten (snipe-a4y): LÖST.** Verifikatnumret räknades
  som `len(lista)+1` i tre API-vägar utan unik spärr — två samtidiga
  uppladdningar kunde få samma nummer. Nu: `nummer=None` → lagringen räknar
  nästa lediga i själva insert-satsen, unikt index per (tenant, serie, nummer)
  i **migration 072** (körd mot development), omtag vid kollision. Inga
  befintliga dubbletter fanns i dev.
- **Produktgrinden i backenden (snipe-h12): LÖST.** `/api/kvitton/*` och
  `/api/bookkeeping/*` krävde bara en giltig tenantnyckel — grinden satt
  enbart i proxyerna. Ny router-dependency `require_bookkeeping_tenant`
  (404 för tenant utan bookkeeping-paketet; tenant utan arbetsyta släpps
  igenom som förut). Läser `workspaces.products` via ny storage-metod, samma
  mönster som migration 064.

### Villkoren (måste hållas/verifieras innan externa kunder släpps på)

1. **`support-webb`-portalen**: delat lösenord (`AGENTSAJT_LOSEN`), ingen
   rollmodell, 12-timmars nyckelkaka och en catch-all-proxy som faller
   tillbaka på demonyckeln. Verifiera att `AGENTSAJT_LOSEN` är satt i varje
   miljö där portalen svarar (utan den är väggen AV), eller vik in portalen i
   huvudappen innan externa kunder får portalinloggning.
2. **Demonyckeln** `snajp_demo_2f8c1a9e4b7d` är incheckad och ger full åtkomst
   till demotenanten Nordlys. Den når ingen riktig kunddata (verifierat), men
   den bör roteras till en miljösatt hemlighet med en `demo_key_fault` i
   uppstarten, samma mönster som masternyckelvakten. Ej blockerande — spårat
   nedan.

### Kvarstående rekommendationer (ej blockerande, skapa/behåll beads)

- `029_snajp_app_admin_reads`: åtta tabeller är cross-tenant-läsbara för varje
  OSKOPAD anslutning (avsiktligt, bakom masternyckeln) — varje ny oskopad
  kodväg i `postgres.py` ärver den ytan. Hålls i schack av granskningsvanan;
  värd en invariant.
- `snajp-support/backend/` (gitignorerad dubblettkopia med egen Dockerfile,
  utan send_guard) bör raderas från disk.
- Delade Redis-strömmar tar `tenant_id` ur payloaden — skrivåtkomst till
  Redis är tenantbyte. Egen Redis-instans per miljö står redan i planen.

**Dom: GO för tenant-isoleringen.** Ingen väg hittades där en tenant kan läsa,
skriva eller logga en annan tenants data — via API, databas-roll, cache eller
demoytor. Villkor 1–2 gäller portalen och demonyckeln, inte kärnisoleringen.

---

## 2. Snajp som egen intern kund — **KLART, körd skarpt**

- Nytt skript [`scripts/skapa_snajp_intern_kund.py`](scripts/skapa_snajp_intern_kund.py)
  (idempotent, torrkörning som default) skapade kontot `intern@snajp.se`,
  arbetsytan **Snajp AB** och backend-tenanten **`kund-7cea8ee9`** i
  development — via exakt samma vägar som en riktig kund (`POST /api/keys`,
  `link_workspace_tenant`, ICP via `PUT /api/leads/config`). Inga specialfall
  i koden. Lösenord + tenantnyckel ligger i `.env.deploy`
  (`RAILWAY_DEVELOPMENT_SNAJP_INTERN_LOSEN`, `RAILWAY_DEVELOPMENT_KEY_KUND_7CEA8EE9`),
  aldrig ekade.
- OBS: sluggen `snajp` återanvändes INTE — den är adminarbetsytans och gav
  korskontaminering i produktion 2026-09-02.
- ICP-profilen enligt beställningen (HLR/första hjälpen/brandskydd/heta
  arbeten/arbetsmiljö, Sverige, roller, signaler, Zendesk-uteslutning).
  Nyansen "10–250 anställda, eller mindre bolag med hög kursvolym" ryms inte i
  det strukturerade storleksfältet — spannet sattes 1–250 och undantaget
  kodades som signal, så småbolagen inte hårdfiltreras bort.
- **Skarp körning genomförd** (scope research, limit 10, `is_test=false`):
  **10 bolag, 6 kvalificerade (fit 0,90–1,00), alla i rätt nisch**, på 2,5
  minuter och ≈ 0,13–0,15 kr/lead. Diskvalificeringarna var korrekta (ideell
  organisation, två bemanningsbolag, en oåtkomlig sajt). Fullständig logg med
  prospektlistan för säljarbetet:
  [`docs/iris-snajp-intern-2026-09-20.md`](docs/iris-snajp-intern-2026-09-20.md).

---

## 3. GDPR-infrastruktur för utskick — **KLART (mycket fanns redan)**

Tre av fem krav var redan byggda och blockerande i kod: avregistreringslänken
(send_guard regel 2 fäller varje mejl utan den; foten byggs i kod), spärrlistan
(regel 3, först av sex, i sändningsögonblicket; "nej tack"-svar skriver dit
automatiskt), och kontaktloggen (`prospects` + `prospect_sources` med källa,
tidpunkt OCH laglig grund per källa — mer än beställt; datamiminering hålls av
schemat). Det som byggdes idag:

- **Integritetspolicylänk i foten**: nytt fält `ss_customer_details.policy_url`
  (**migration 073**, redigerbart i admin → Kunder → Data), rad i
  `utskicksfot.bygg_fot()`, och **blockerande krav i send_guard regel 2** —
  en tenant utan policy_url får sina utskick stoppade med besked.
- **Rotorsak till att inga kallmejl kunnat skickas hittad och lagad**: Railway
  och DEPLOY.md säger `PUBLIC_BASE_URL`, men koden läste bara `PUBLIK_BAS_URL`
  — den satta variabeln gjorde ingenting, foten kunde aldrig byggas och
  regel 1 blockerade allt med fel felmeddelande. Nu läses båda namnen
  (alias + regressionstest), och DEPLOY.md förklarar.
- **Rollflaggning**: nytt härlett fält `rollkoppling_oklar` på varje prospekt
  i API:t (namngiven person/personlig adress utan belagd yrkesroll) — se
  `app/leads/rollkoppling.py`. Underlag för intresseavvägningen; själva
  bedömningen byggdes medvetet inte.
- **`egna_kunder`-spärren fick data**: regel 3 kontrollerade kundens egen
  kundlista mot en ALLTID TOM mängd. Nu matas den ur supportens kundregister
  (`ss_customer_identifiers`) — den som har ett ärende hos tenantens support
  kallmejlas inte.
- Supportsvarens medvetna undantag från spärrlistan är nu dokumenterat i
  `email_pipeline/sender.py` (ett svar på kundens egen fråga är inte
  marknadsföring).

**Kvar för människa:** Snajps eget orgnr och postadress är fortfarande
platshållare (P0.3b i `docs/JURIDIK_ATGARDER.md`) — send_guard blockerar
därför Snajps EGNA utskick tills Anton fyllt i dem plus `policy_url` för
Snajp-tenanten. För kundtenants: fyll kundregistret vid onboarding.

---

## 4. Gratis 2-månaders trial — **BYGGT; konverteringen väntar på ER**

- **Migration 074** (körd mot development): `workspaces.trial_slut date`,
  default = kontoskapandet + 2 månader för varje nytt konto, backfyllt från
  `created_at` för befintliga. Ett datum ÄR statusen (samma mönster som
  `avtal_signerat`); betalande kund känns igen på avtalet.
- **Påminnelser 7 dagar + 1 dag före slut**: ny daglig svepare
  `app/jobs/trial_paminnare.py` i backendens lifespan (mönstret från
  leads-städaren). Skickar via den riktiga sändvägen (Resend i development),
  vägrar en sändväg som inte levererar (ingen loggad påminnelse kunden aldrig
  fick), loggar i nya tabellen `trial_paminnelser` (unik per arbetsyta+typ =
  omkörningsbar utan dubbletter), hoppar över demo-ytor och kunder med
  signerat avtal. Fem tester.
- **Synligt i admin**: ny kolumn "Trial" i Kundtabellen — dagar/veckor kvar,
  "Sista dagen", eller slutdatum när den passerat; streck för betalande.
  Datat flödar via `list_tenants_with_stats`.
- **Konverteringen beslutad och byggd senare samma dag: manuell avstängning
  med bekräftelse i admin.** Ny sektion "Avstängning" sist på kundprofilen:
  trialkontexten i klartext, tvåstegsbekräftelse med obligatorisk orsak (blir
  en warning-rad i `platform_events`), och återaktivering med ett klick.
  Skrivningen är `PUT /api/admin/tenants/{id}/aktiv` (`admin_profil.py`,
  masternyckel). Avstängningen ÄR `ss_tenants.active` — nycklarna avvisas med
  401 i samma ögonblick, alla tre agenterna/webben/portalen/publika chatten
  låses, inget raderas. Liveverifierad mot development: avstängd
  granskningstenant fick 401 direkt, återaktivering öppnade igen. Ingen
  automatik: ingenting händer vid trial-slut förrän en människa trycker.

---

## 5. Org.nummer-fältet — **FANNS REDAN, verifierat**

`ss_customer_details.orgnr` (migration 053) är exakt det beställda nullbara
fältet på kundmodellen: per tenant, manuellt lager med härledd fallback ur
onboardingens affärskontext, validering i `lib/orgnr.ts`, redigerbart i
admin → Kunder → Data. Ingen ny migration behövdes, ingen
Bolagsverket-koppling byggdes (enligt beställningen).

---

## Verifierat

- Backend: `pytest` 2253 gröna (2235 → +18 nya). Rotens invariantsvit 532
  gröna. `npx tsc --noEmit` rent. `npm test` grönt. `npm run build` går
  igenom.
- Migrationer 072–074 körda mot Railway development och verifierade i
  katalogen (unikt index, trial_slut backfylld, policy_url-kolumn,
  profiles-läsning för snajp_app).
- Skarpa liveverifieringar mot development: IDOR-sviten (21/21),
  svarscachens taggfilter, Iris-körningen. Alla granskningsartefakter städade
  (tenants, KB-rad, kvittorad, Redis-nycklar).

## Kräver människa (sammanfattning)

1. **Trial-konverteringen** (punkt 4) — affärsbeslut, inget byggt.
2. **Snajps bolagsuppgifter** (orgnr, postadress, policy_url) innan Iris får
   skicka något för Snajp-tenanten — send_guard blockerar tills dess.
3. **Portalens `AGENTSAJT_LOSEN`** verifieras satt per miljö (villkor 1).
4. **Demonyckel-rotationen** (villkor 2) — kan byggas på beställning.
5. Release till `main` är som alltid Antons handgrepp (§8.1a); migrationerna
   072–074 ska köras mot main (torrkörning först) FÖRE mergen.
