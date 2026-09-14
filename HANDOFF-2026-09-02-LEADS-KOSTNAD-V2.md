# Handoff 2026-09-02: Leads-kostnaden kapad — V2-kedjan, jobbliggaren, källfederationen och Leadslistor

**Till: Anton.** Bakgrund: en omprocessning av 18 leads kostade ~18 kr, och
saldot sjönk sedan ytterligare ~18 kr utan någon handling på sidan. Målet var
≤0,10 kr/lead. Den här handoffen täcker hela leveransen; systerhandoffen
`HANDOFF-2026-09-02-RESURSER-OCH-GRINDAR.md` (parallellsessionen) täcker
grindarna i V1-kedjan, snabbsök och supportens ändringar.

## De två rotorsakerna, båda bevisade

1. **13–16 LLM-anrop per lead**, där varje anrop bar HELA den vendorade
   skillen (mk:offers ~70 kB, mk:prospecting ~52 kB …) plus hela basen
   (brief + kontextpaket + SOUL + 14 000 tecken skrap) PÅ NYTT. ~100k
   input-tokens/lead bara i research. Input var kostnaden, inte output.
2. **De extra 18 kr utan handling**: Redis-strömmens XAUTOCLAIM-återtag körs
   varje worker-varv plus vid varje deploy/omstart. Vakten mot omkörning
   läste bara Redis-jobbposten — men den posten skapas vid KÖANDET,
   auto-failas efter 300 s i kö (leads har 1 sekventiell worker, så jobb
   nr 5+ i en 18-batch står alltid längre än så) och TTL:ar efter en timme.
   Vid återtaget såg vakten "failed"/ingenting → hela kedjan kördes om.
   Live-belägg: budgetgrinden (ny, se nedan) fångade Snajp-tenanten på
   **5,49M tokens på 24 h** — mot ett nysatt tak på 2M.

## Levererat (allt på `development`, migrationer körda)

### 1. Blödningen stoppad (INV-JOB-002 — ny invariant med CI-test)
- **Jobbliggare i Postgres** (migration 059, `leads_job_ledger`): en rad per
  leads-jobb, skriven vid köande/start/slut. Vakten läser liggaren FÖRST —
  en `completed`-rad stoppar omkörningen oavsett vad Redis säger.
- **Kötid är inte arbetstid**: leads-jobb skapas som `queued`;
  300-sekundersklockan räknar från faktisk start (`store.start()`).
  Chattjobbens beteende (INV-JOB-001) är oförändrat och regressionstestat.
- **Budgettak**: `LEADS_DAILY_TOKEN_BUDGET` (default 2M tokens/dygn/tenant
  ≈ 20 kr) grindar batch, processa-om och direktutkast med HTTP 429.
  Verifierad live. 0 stänger grinden.
- **XAUTOCLAIM-hängslen**: en post som levererats >3 gånger kvitteras
  oprövad i stället för att bli en evig omkörningsmaskin.

### 2. Research 9 anrop → 1, utkast 4 → 2 (V2-kedjan, PÅSLAGEN i development)
- `RESEARCH_V2`: ETT anrop med basskillen sa:account-research + overlayen
  `leads-research-v2` — destillatet av de nio skillsens kärnprinciper
  (kontaktschema, ICP-kvalificering, positionering, invändningar,
  erbjudande, osäkerhet, kunskapsfångst) i ett JSON-schema. **OBS
  avvikelse från planen:** destillatet ligger som OVERLAY, inte som ny
  skill `snajp:leads-research` — upplåsningsnyckeln för skills-manifestet
  finns med avsikt inte på utvecklingsmaskinerna, och overlays är den
  sanktionerade ytan (INV-SKILL-005/006). Samma text, rätt mekanism.
- `OUTREACH_V2`: steg 1 = sa:draft-outreach + mk:cold-email (skopad till
  personalisering + granskningssektionerna, via ny opt-in-mekanism
  `PlaybookStep.extra_skills`) i SAMMA anrop; steg 2 = humanizern,
  oförändrat HEL och fysiskt SIST — **INV-LANG-002 bevaras utan
  invariantändring**. Grundningscykeln och tomtext-omförsöket är exakt
  desamma. Mejlutkastens skillinnehåll är alltså BEHÅLLET — bara
  workflowen är komprimerad, precis som beställt.
- Artefaktkontraktet nedströms är identiskt (verifierat i
  `tests/agent/test_leads_v2_wiring.py`, 10 tester). Kedjevalet styrs av
  env `LEADS_PIPELINE` (kod-default v1); **v2 är satt på Railway
  development** efter benchmarken nedan.
- Två latenta buggar fixades på vägen: batch-vägens research_summary
  serialiserade `{null, null, null}` (fälten fanns aldrig på toppnivå),
  och `research_evidence` skickades aldrig till utkastet i batch-vägen —
  grundningsgrinden saknade researchbeläggen där.

### 3. Benchmark mot RIKTIGA gemini-3.6-flash (`scripts/benchmark_leads_kedja.py`)

| Kedja | Anrop/lead | Tokens in/lead | ~kr/lead |
|---|---|---|---|
| V1 (med parallellsessionens grind) | 7,7 | 66 882 | **0,56** |
| V2 | 2,3 | 18 322 | **0,19** |

- Kvalitet: kontaktfält ordagrant rätt 2/3 för BÅDA (samma fixture föll),
  qualified 3/3 för båda. Blind parvis utkastdom: **V2 vann båda**
  jämförelserna (tydligare värdeerbjudande, vassare CTA).
- Mot den ursprungliga ogrindarde kedjan (~1 kr/lead) är V2 **~5x
  billigare**; målet 0,10 kr nås med nästa steg: skopa humanizern (39 kB
  hel idag — mätbar uppföljning, harnessen finns).
- Skriptet stödjer `--modell haiku` (proxy, kräver ANTHROPIC_API_KEY) och
  `--modell gemini` (riktig mätning). Fixtures:
  `snajp-support/fixtures/leads_benchmark/` (5 syntetiska prospekt, varav
  ett medvetet gränsfall). OBS: den LOKALA Gemini-nyckeln i
  snajp-support/.env är gratisnivån (20 anrop/dygn) — benchmarken kördes
  med development-nyckeln ur .env.deploy.

### 4. Källfederationen (ersätter brett Gemini-sökande)
- `sources/jobtech.py`: Platsbanken/JobSearch (öppet, gratis, nyckellöst) —
  annonsen är köpsignalen ("rekryterar kundtjänst"), ger arbetsgivare, ort,
  ofta webbadress. Offentlig sektor filtreras.
- `sources/nyheter.py`: nyhets-RSS (MyNewsdesk-default, konfigurerbar via
  `LEADS_NYHETS_RSS`) — bara poster med växtsignal (expanderar, nytt
  kontor, rekryterar …).
- `hitta_bolag` kör källorna FÖRST; Gemini-sökningen är numera UTFYLLNAD
  (max 1 grounded anrop, bara om källorna gav färre än beställt).
  Webbplatser utan käll-URL gissas via HEAD-validering
  (`https://<slug>.se`) innan något grounded uppslag görs.
- `LEADS_KALLOR` styr aktiva källor (osatt = båda; tom sträng = inga —
  testsvitens läge, konftest håller sviten hermetisk).
- Kontaktperson hämtas som förr ALLTID från bolagets egen webbplats
  (kontakt-/om-oss-sidan) — aldrig privata adresser. Allabolag/orgnr rörs
  inte i leads-steget (var redan så).

### 5. Leadslistor — nytt tilläggspaket (`leadlists`, migration 060)
- Produkten delad i två: dagens snäva körningar med personliga utkast, och
  volymlistor — kunden beställer titel + antal (1–200), federationen bygger
  en granskningsbar tabell (bolag, ort, kontaktväg enligt trappan, signal,
  källänk) med CSV-export. Inga utkast, ingen sändning (INV-SEC-004).
- Backend: `POST/GET /api/leads/listor(/{id})`, listjobb i leads-strömmen
  (liggaren ger idempotens, budgeten grindar), tabeller `lead_lists` +
  `lead_list_items`. Frontend: addon-kort, route `/dashboard/leads/listor`,
  `LeadslistorView`, demo-exempellista i högerkolumnen vid testkörningarna.
- **Privatpersoner: MEDVETET INTE byggt.** Datamodellen är förberedd
  (`item_typ`), men prospektering av privatpersoner kräver en GDPR art.
  6-avvägning + art. 14-information, och källorna för persondata
  (ratsit/hitta) är TOS-blockerade. **Det är ditt beslut, inte ett
  kodbeslut** — säg till så bygger vi vidare på laglig grund
  (t.ex. enskilda firmor med egen sajt).

### 6. UI-texterna
- "Skräddarsydda leads efter din målgrupp och produkt." (rubrik),
  ny ingress, "Diskvalificerar" → "Egna kriterier" överallt,
  "Stad, län, region" → "Stad". De tre divergerande ICP-etikettlistorna är
  centraliserade till `lib/leads/icpLabels.ts` — nästa textändring är en rad.

## Kvarstående beslut/uppföljning

1. **Humanizer-skopning** (39 kB hel → kärnsektioner): sista steget mot
   0,10 kr/lead. Mät med benchmarkskriptet före/efter.
2. **V1-radering**: V1 ligger kvar bakom flaggan. Efter en veckas
   V2-drift i development utan kvalitetsklagomål: radera V1-grenarna.
3. **main**: ingenting här rör main. Flaggan+migrationerna för main tas
   den dag main-kedjan släpps (kräver ditt uttryckliga ord, §8.1a).
4. **Privatpersoner i leadslistor**: juridiskt beslut, se ovan.
5. **Gemini-fritier-nyckeln lokalt**: snajp-support/.env bär en
   gratisnyckel (20 anrop/dygn) — räcker inte ens till en testbatch.
   Överväg att lägga en betald nyckel lokalt eller peka utvecklingsflödet
   mot development-API:t.

## Verifiering
- Backend-sviten: **1758 passed, 4 skipped** (inkl. nya
  test_inv_job_002, test_budget, test_leads_v2_wiring,
  test_sources_federation, test_leadslistor).
- Migrationer 059+060 körda mot development via railway_migrate (`=`).
- Budgetgrinden verifierad live (429). Benchmark körd mot riktiga
  gemini-3.6-flash (tabellen ovan), resultat i
  `var/benchmark_leads/senaste.json`.
