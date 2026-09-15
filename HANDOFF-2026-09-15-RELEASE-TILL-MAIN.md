# Handoff till Anton — release development → main, 2026-09-15

Sebbe har beställt att allt på `development` går till produktion. Grenskyddet
kräver din review och merge (§8.1a) — den här filen är hela underlaget, med
nästa steg körbara direkt efter mergen.

## FÖRE mergen — inget kvar

Migration **065** (`workspaces_admin_grant`) är **redan körd mot main** och
verifierad verksam (2026-09-15; `has_table_privilege=true`). `verify_railway`
noterar "schemat ligger före koden" tills mergen — det är förväntat och
försvinner med den. Ingen migration återstår före merge.

## Mergen

Release-PR:en `development` → `main` (2026-09-15; Vertex koppling-sessionen
driver släppet på Sebbes order, med testkörnings klartecken som spärr).
Mergen deployar `web` + `api` i main automatiskt — triggarna lyssnar på
grenen `main` sedan §8.1-omläggningen.

## Vad släppet innehåller

**Bokföringsagenten som egen sajt** (`bokforing-webb/` + Railway-tjänsten
`bokforing`, BARA i development än så länge)
- Fristående Next-app: vänstermeny (Översikt, Resultat, Intäkter & utgifter,
  Bokföringsagenten, PDF-filer, Assistent, Inställningar, Kontakt), Snajps
  designsystem, proxy mot bokförings-API:t, Basic Auth-vägg tills riktig auth
  finns. Provisionerad av `scripts/railway_bokforing.py` (idempotent).
- Inloggade kunder på webben skickas dit: `/dashboard/bokforing` omdirigerar
  när `BOKFORING_EXTERN_URL` är satt (satt i development). **Osatt i main →
  exakt gamla inbyggda vyn.** Demon (`/demo`) är orörd.
- Backend: `las_underlag` gör nu TVÅ oberoende genomgångar per underlag
  (avläsning + kontrolläsning); fält där de läser olika går till granskning i
  stället för att gissas. Obs: dubblar LLM-kostnaden per underlag — medvetet.

**Email studio-serien** (Vertex): `5b7640f` + `ae02a96` + `95b3524` +
`4a112ef` — trunkerad JSON, timeout-budget, tänktokens, `reasoning_effort`.
Alla fyra krävs tillsammans; utan dem svarar produktionens email-studio 400
eller visar JSON-bråte. `GOOGLE_SERVICE_ACCOUNT_JSON` ligger redan på
web@main sedan 2026-09-14 — omdeployn i mergen aktiverar den.

**Leads-fixar** (liveverifierade i dev som QA-kund): `a65ab1e` (JobTech söker
på kundens målgrupp, inte Snajps egen köpsignal — 0/10 → 10/10 i målgrupp),
`ed60d10` (Vertex `role:user` + redirect-värdgissning), `36bf8fa` (V2:
underkända bolag får inte längre mejlutkast).

**Övrigt**: migration 065, DEPLOY.md-omläggningen (INV-DEPLOY-002),
bd-reparationen (serverläge; dolt-CLI via winget), diverse dokument.

## Verifierat före släpp

- snajp-support: fulla testsviten grön lokalt — 1911 passed, 4 skipped
  (2026-09-15 00:5x, spetsen före kvalificeringsgrinden), inkl. 6 nya tester
  för dubbelavläsningen.
- Prodsvep (session `snipe-leads-ee`): chattagent, support-E2E 18/18,
  adminytan i tre roller, leads-research hela vägen — grönt.
- Bokföringssajten kundtestad sida för sida i deployad dev (2026-09-15):
  uppladdning via UI → "Läst 2 gånger", korrekt avläsning (datum, motpart,
  1 250,00 kr, 25 %, kategori drivmedel), Resultat/moms rätt räknat,
  SIE-export med profilens företagsnamn+orgnr i filhuvudet, assistenten gav
  grundat svar ("250 kr ingående moms att dra av"), mobil 375px håller,
  inloggad-klick på Bokföring → Railway-sajten, demon orörd.

## EFTER mergen — nästa steg, i ordning

1. **Verifiera main** (5 min): web+api SUCCESS på merge-committen i Railway;
   logga in och tryck på Förbättra i email-studio (ska ge formaterad ny
   version, inte 400/JSON); `InsufficientPrivilegeError` borta ur api-loggen.
2. **När bokföringssajten ska ut i produktion** (ditt beslut, ~10 min):
   a. Railway dashboard → main-miljön → New service → GitHub
      `oloflun/snipe-leads`, root directory `/bokforing-webb`, trigger-gren
      `main`. (API:t saknar serviceInstanceCreate — dashboarden är vägen för
      en andra miljö; scripts/railway_bokforing.py klarar bara development.)
   b. Variabler på tjänsten: `SNAJP_SUPPORT_URL` = main-api-URL:en,
      `SNAJP_BOOKKEEPING_API_KEY` = main-nyckel (INTE dev-nyckeln —
      korskoppling), `BOKFORING_LOSEN` = eget värde (eller utelämna när
      riktig auth finns). Generera domän.
   c. Sätt `BOKFORING_EXTERN_URL` på web@main → inloggade skickas till sajten.
3. **Kända icke-blockerare** (från testkörnings svep, för backloggen):
   storleks-/bemanningsbedömningen i leads-research (Andara Group 0,70),
   "Hej ," utan kontaktnamn i utkast, dubblettrisk på listbeställning vid
   omstart. Bokföringssajten: Enter-för-skicka i assistenten kunde inte
   verifieras i testpanelen (knappen fungerar; troligen panelartefakt).
4. **Kvar i ee:s svep**: bokförings-PDF-testet i prod väntar på ett klick på
   Snajp Trio under /settings/billing (faktureringsyta = användarens klick,
   Sebbe har instruktionen).

Lösenordet till dev-sajten: `RAILWAY_DEVELOPMENT_BOKFORING_LOSEN` i
`.env.deploy` (roterat efter testpasset). Sajten:
https://bokforing-development.up.railway.app
