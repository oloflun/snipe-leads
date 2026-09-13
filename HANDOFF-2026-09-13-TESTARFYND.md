# Handoff — testarens pilotfynd åtgärdade (2026-09-13)

Från Sebbe (via Claude) till Anton. Allt ligger på `development`
(`fadc95e..f24cab8`). **Inget av det är i drift** — Railway är fortfarande
nere (se nedan), så pushen deployade ingenting.

## TL;DR

| Fynd från testaren | Läge |
|---|---|
| Kredit-429 behandlas som övergående (chatt, leadsjobb, bokföring) | Åtgärdat i kod, testat |
| Leadslistor ↔ Email studio saknas | Åtgärdat — bron fanns men syntes inte; nu på alla rader + snabbmail |
| Tillval går inte att aktivera | Toggeln fanns (migration 063) — troligen ej körd; tydligt fel nu |
| Email studio demoläge med fel förklaring | Åtgärdat — Vertex-stöd + ett sant besked per orsak |
| Översikten visar "Snajp Duo" efter Trio | Åtgärdat |
| Testarbetsytor inaktiva i admin | Åtgärdat |
| Listtiteln styr inte sökningen | Åtgärdat |
| Pilotavtal | Utkast i `docs/pilotavtal.md` — ska till jurist |
| Orgnr-automatiken | Skript: `scripts/pilot_kb_utkast.py` |

Tester: backend 1853 gröna / 0 fel, rot + invarianter 437 gröna, TS-enhetstester
36/36, `tsc` rent (utom två gamla genererade `.next`-stubbar).

---

## Det här behöver DU göra (i ordning)

1. **Starta Railway igen.** Uppmätt 2026-09-13: `api-development`,
   `api-production` och `web-development` svarar 404 på `/health/ready`, och
   development-Postgres stänger anslutningen. Samma mönster som 2026-09-11/12
   (alla deployer REMOVED). Troligen plan/betalning. Handoffen 2026-09-12 säger
   "verifierat mode=live" — det gäller inte längre.
2. **Lägg `GOOGLE_SERVICE_ACCOUNT_JSON` på `web`-tjänsten** i båda miljöerna
   (samma enradiga JSON som på `api`). Email studio kör nu Vertex, men utan
   nyckeln på `web` står den kvar i demoläge. `OPENAI_API_KEY` ska vara osatt
   på `web`, annars vinner den över Vertex. Valfritt: `GOOGLE_CLOUD_REGION`
   (default `europe-west1`).
3. **Kör migrationerna:**
   ```
   python scripts/railway_migrate.py --env development          # visar vad som saknas
   python scripts/railway_migrate.py --env development --apply
   ```
   `063_workspace_addons_admin` (tilläggsväljaren) och `064_workspaces_admin_read`
   (adminvyns paketkolumn). Se `MIGRATIONS-PENDING.md`. Main först efter ditt ord,
   som vanligt.
4. **Gör ett riktigt Vertex-anrop.** Modellnamnet `gemini-2.5-flash` utan prefix
   är inte bekräftat mot Vertex OpenAI-kompatibla endpoint — Googles docs visar
   `google/gemini-2.5-flash`. Vi kunde inte prova: service account-filen finns
   bara hos dig. Blir första anropet 404 är det orsaken, och då påverkas
   backendchatten likadant (`snajp-support/app/agent/llm.py`).
5. **Jurist på pilotavtalet** innan det skickas (`docs/pilotavtal.md`).

---

## 1. Kreditslut fäller snabbt — `fadc95e`

**Varför testaren fick "försök igen":** två orsaker.
- `kvotfel.py` kände bara igen AI Studios förskottskredit. Vertex svarar 403
  `BILLING_DISABLED` / "billing account … is disabled" / `CONSUMER_SUSPENDED` —
  inget 429, ingen markör, alltså generisk text och inget larm. Markörerna
  (inkl. "spending cap") finns nu i `kvotfel.py` OCH `lib/admin/handelsetext.ts`
  och i `lib/llm/kvotfel.ts` (INV-QUOTA-001 utvidgad).
- `SupportChat.tsx` kastade bort backendens text och visade en slumpad
  "försök igen". Visar nu `job.error`.

**Leads:**
- Alla jobbtyper (utkast, batch, per-prospekt, lista) fäller direkt med
  kundtext + larm; ingen råtext från leverantören i jobbfel, `draft_note`
  eller `lead_lists.felorsak`.
- Listbygget skriver rader först när bygget lyckats — inga skräprader.
- `discovery.py` kastade bort svarskroppen vid 4xx; den ligger nu i
  undantagets orsak så att kreditslut i sökningen klassas.
- **Ny städare** `app/jobs/stadare.py`: leadsjobb i queued/processing och
  listor i bestalld/byggs äldre än `LEADS_HANGTID_MINUTER` (60) failas med
  ärligt besked — vid uppstart, var 300:e sekund (`LEADS_STADNING_SEKUNDER`)
  och vid listläsning. Strömmens `MAX_LEVERANSER`-tak ger nu upp jobbet i
  stället för att tyst kvittera. **Testarens hängande jobb städas vid första
  uppstarten efter deploy** — databasen är inte rörd för hand.
- `POST /leads/listor` svarar 422 om varken sparad målgrupp eller titeln ger
  något sökbart, före budgetkontrollen.

**Bokföring:** uppladdning och chattbilaga svarar 503 (kreditslut, larm) /
429 (kvot) med `klass` och en mening som säger att dokumentet INTE sparades
(bytes kastas per design). `BokforingPanel` stoppar batchen vid kreditslut,
namnger oskickade filer och har "Försök igen med N filer" vid kvot.

**Kvar:** chattströmmen har inte give-up-kopplingen (bara leads); chattjobb
failar fortfarande lat efter 300 s vid läsning. `hitta_bolag` sväljer
DiscoveryError när källträffar finns (levererar dem) — utan larm.

## 2. Email studio — `de6cecc`

- **Vertex:** `lib/llm/vertex.ts` signerar JWT med `node:crypto` → OAuth2-token
  med cache. Samma endpoint som `llm.py`. Inga nya npm-beroenden.
- **Det gamla Gemini-flödet kunde aldrig lyckas:** `createOpenAI(...)(modell)`
  i @ai-sdk/openai v4 går mot Responses API, som Gemini/DeepSeek saknar. Icke-
  OpenAI går nu via `.chat()`.
- **Modellval** (`lib/llm/modellval.ts`): OpenAI → Vertex → GEMINI_API_KEY →
  DeepSeek. **DeepSeek spärrad även i development** (spegel av produktionen),
  speglar `har_riktig_kunddata()`.
- **Besked per orsak** i `EmailStudioEditor`: anonym (logga in) / ingen
  modellnyckel / kreditslut / kvot / tillfälligt fel. Bara "anonym" säger
  logga in. Loggen bär inte längre kundens prompt (den gjorde det förut).
- **Kvar:** Next-sidan har ingen väg att larma (skriver inte `platform_events`,
  skickar inget prioriterat mejl). Kreditslut i Email studio syns bara som
  loggraden `[email-studio:kreditslut]`.

## 3. Leadslistor, tillval, översikt, admin — `8e30461`

- **Leadslistor → Email studio:** bron ("Skriv mejl", commit ddd67ac) fanns
  men renderades bara på rader med adress — testarens lista hade inga. Nu på
  alla rader; saknas adress frågar rutan efter den först och sparar den på
  prospektet (utkast utan adress går inte att köa lagligt, avregistreringsfoten
  byggs på adressen). **Snabbmail:** "Skriv utkast till alla med mejladress",
  högst 25 per klick, bekräftelse, stopp, allt till granskningskön — inget
  skickas. Saknad affärskontext ger nu ett läsbart fel (skickade tidigare tom
  `offer_summary` → 422).
- **Listtiteln** skickas som `overrides.must_have`, samma mekanism som
  snabbsöket.
- **Tillval:** toggeln finns i adminens kundprofil sedan 063. Saknas RPC:n
  (42883) visar väljaren nu ett fel som namnger migrationen. Kundbesök visar
  kundens riktiga tillval (var hårdkodat tomt). Profilen länkad från listan.
- **Översikten:** paketnamnet ur `workspaces.products` — Trio visas som Trio.
- **Admin:** testarbetsytor räknar testaktivitet och märks "Testarbetsyta";
  paketet ur products med härledning som reserv. **Kräver 064** — utan den
  blockerar RLS läsningen tyst och fotnoten visar "härlett".
- **Kvar:** kundbesökets `select … from workspaces where slug` returnerar
  troligen inget för en annan kunds arbetsyta av samma RLS-skäl (beteendet
  var så redan innan).

## 4. Pilotavtal och onboarding — `f24cab8`

- `docs/pilotavtal.md`: 2–3 sidor. Pris + ordinarie prislista ur
  `lib/pricing.ts`, PUB med underbiträdesbilaga, mänsklig granskning som
  villkor, ansvarstak = pilotavgiften, export/radering, veckosamtal +
  referensrätt, styrning vecka 1–2 / 3–6 / 7–8 via produktens regler.
  **Hakparenteser = ej ifyllt/ej verifierat.** Underbiträdenas regioner är
  overifierade: `scripts/railway_region.py` gav "okänd" för alla tjänster.
  `lib/bolag.ts` listar fortfarande Supabase och OpenAI — stryk eller behåll
  medvetet.
- `scripts/pilot_kb_utkast.py`: orgnr + webbplats → KB-utkast (JSON + md) +
  luckor att fråga kunden om. Kör med backendens venv. `--apply` skickar bara
  artiklar med `"godkand": true` och kontrollerar tenantnamnet först.
  Genomsökningen provkörd mot en riktig sajt; LLM-steget bara mot attrapp
  (ingen Vertex-nyckel lokalt). Bransch/SNI slås inte upp — kräver
  Bolagsverkets licensierade API. Se `docs/pilot_onboarding.md`.

---

## Småsaker värda att veta

- **Lokal `.env` fällde tester:** `snajp-support/.env` har
  `MODEL=gemini-3.6-flash`, och tester som sätter `LLM_PROVIDER=deepseek`
  föll på modell/provider-kontrollen. Tre testfiler pinnar nu `MODEL`. CI
  påverkades inte. Samma lokala nyckel (AI Studio) svarar dessutom att
  `gemini-2.5-flash` inte längre finns för nya användare.
- **Beads är trasigt lokalt:** `.beads/embeddeddolt/snipe` är tom och remoten
  har inga `refs/dolt` — inget registrerat där den här sessionen.
- **Inte visuellt verifierat:** adminvyerna, Skriv mejl-flödet och Email
  studios inloggade besked — kräver inloggning och databas. Demoytorna
  (Email studio desktop/mobil, översikt, bokföring, kundtjänst) renderar utan
  konsolfel.
