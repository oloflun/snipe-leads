# Handoff 2026-09-16 — Iris (leadsagenten omdöpt och vidareutvecklad)

**Läge: ENDAST LOKALT.** Ingenting är committat, pushat eller deployat. Trädet
delas med kvittohanterar-sessionen (se HANDOFF-2026-09-16-KVITTOHANTERAREN.md) —
en commit ska plocka Iris-filerna selektivt, aldrig `git add .`.

## Vad som byggdes

Uppdraget: döp om Leads-agenten till Iris och vidareutveckla på konceptnivå
(gränser, eskalering, källtransparens, animerat demo) — utan att kopiera
Artisans produkt, texter, prisramning eller databaslöften.

### Namnet

- `lib/agentsajt.ts` — leads-posten bär Iris-rubrik/persona och ett nytt
  `knapp`-fält per agent: bannern säger **"Kör Iris"** för leads, "Kör Agent"
  för de andra. `components/AgentSajtKnapp.tsx` läser fältet.
- Marknadsytan: `components/marketing/copy.ts` ("Möt *Iris*, din säljare som
  aldrig sover" + persona-lede), `UspSection.tsx`, `lib/pricing.ts`,
  `lib/faq.ts`, `app/leads/page.tsx` (metadata).
- Arbetsytan: `components/WorkspaceViews.tsx` (leads/companies/contacts),
  `components/settings/NotisSettings.tsx`, admin (`Kundprofil`,
  `Testkorningar`), förhandsvisningen, demo-kickern.
- **Medvetet INTE omdöpt:** `app/villkor/page.tsx` (avtalstext),
  URL-sluggar/produktnycklar (`leads`), interna variabelnamn.
- leads-webb: metadata "Iris — Snajp Leads", railen "Iris · Leads", alla vyer.

### Iris-registret (leads-webb/lib/iris.ts)

Persona, gränslistan `GRANSER`, eskaleringsregler (typ + localStorage-
läs/skriv), `kallEtikett()` (URL → LinkedIn/Platsbanken/värdnamn) och
`statusEtikett()` (backendens `new` → "Ny"). Namn och regler bor HÄR;
huvudappens motsvarighet är `lib/agentsajt.ts`.

### Gränser och eskalering

- "Det här gör Iris aldrig utan din granskning" på /agenten
  (`components/IrisGranser.tsx`) — fem punkter, var och en backad av en
  faktisk spärr (granskningskön, avregistreringen, källkravet, svarsstoppet).
  Skriv aldrig in en gräns som koden inte upprätthåller.
- Konfigurerbara eskaleringsregler under /installningar
  (`components/vyer/Eskalering.tsx`): osäker kvalificering med tröskel,
  pris/avtal, negativt svar, juridik. **Sparas i localStorage** tills
  backenden bär ett fält — vyn säger det rakt ut. Uppföljning: snipe-e45.

### Källtransparens

- Prospektraden i leads-webb fäller ut "Hittad via" och hämtar
  `GET /leads/prospects/{id}` → `sources` (backendens `prospect_sources`,
  riktiga URL:er). Huvudappens Bolagssida visade redan källorna.
- Verifierad end-to-end mot minnesbackenden med seedat prospekt (se nedan).

### Demoflödet

`leads-webb/components/vyer/DemoVy.tsx` på /demo ("Se Iris arbeta"):
hitta (Fjällvind Energi AB, fiktivt) → berika med fyra synliga källor →
maskinskrivet utkast → inkommande svar där **prisfrågan eskaleras enligt
reglerna** → möte bokat efter användarens bekräftelse. Märkt "Fiktivt
exempel" (hederlighetsregeln), respekterar `prefers-reduced-motion`
(allt visas direkt), replay-knapp. Stegtakt `STEG_MS`, sista steget
`SISTA_STEGET`.

## Lokal stack

| Del | Kommando/URL |
|---|---|
| Backend, minnesläge 8010 | launch.json `iris-backend` → `snajp-support/lokal_iris.py` (blankar DATABASE_URL/REDIS_URL — pekar ALDRIG mot spegel-DB:n) |
| Iris-ytan | launch.json `iris-leads-dev` → http://localhost:3101 (lösenväggen av lokalt) |
| Huvudappen | launch.json `web` → http://localhost:3005 (`/leads`, dashboard) |

`LEADS_EXTERN_URL=http://localhost:3101` är tillagd i rotens `.env.local`
(gitignorerad) så dashboardbannern pekar på lokala ytan.

Seeda källdata i minnesbackenden (UTF-8-bytes krävs i PS 5.1, annars 400):

```powershell
# POST /api/ag/leads/prospects  {company_name, contact_name, contact_email}
# POST /api/ag/leads/prospects/<id>/sources  {source_url, source_type, lawful_basis}
# source_type: company_website|public_news|business_register|job_signal|linkedin|...
# OBS INV-DATA-002: LinkedIn får inte vara första källan.
```

## Verifiering

- Typkontroll grön i roten och leads-webb.
- Playwright-fullpage-PNG:er (1440 + 375) av demo, agenten, installningar,
  prospekt och /leads — alla lästa. Fynd som rättades: `[object Object]` i
  Målgrupp (nästlade ICP-värden plattas + tomfiltreras i `InstallningarVy`),
  rå status `new` i badgar (statusEtikett). Omskott rena.
- Eskaleringsväxeln: av → omladdning → läget kvarstår (localStorage).
- **Ej visuellt verifierad:** dashboardbannern "Kör Iris" (kräver inloggning;
  lokal server ska inte logga in mot fjärr-Supabase). Kodvägen är rak:
  `WorkspaceSection` → `<AgentSajtKnapp agent="leads"/>` → `text.knapp`.

## Öppna trådar

1. **snipe-e45**: eskaleringsreglerna till backendfält (agent_configs) +
   koppling till svarshanteringen; localStorage är en lokal placeholder.
2. Dashboardbannern verifieras visuellt vid nästa inloggade QA-pass
   (qa_vyer.mjs-mönstret).
3. Commit väntar på Antons/Sebbes klartecken; plocka Iris-filerna separat
   från kvittohanterar-sessionens.
