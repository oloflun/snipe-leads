# Plan 2026-10-02 — knyta ihop förra körningen: adminfelet, development, listorna, tvåspråkigheten

> Allt arbete på `development`. Main rörs bara med Antons ord (CLAUDE.md §8.1a).
> `bd` är nere (dolt saknas i PATH) — rutorna här är spårningen. Ponytail full.
> Subagenter: Opus (Fable delegerar till Opus). Visuell granskning gör jag själv.

## Kontext

Förra sessionen (2026-10-01→02) byggde Iris › Körningar, menyn i railen och merinfo som
registerkälla, men avslutades på Antons order innan hans sista beställning påbörjades.
Kvar är fyra saker i Antons ordning: (1) adminytan i produktion visar felsida, (2) hans
avbrutna order "migrera, pusha, aktivera scrapegraph och Jev i development", (3) listornas
nya krav (mejl-rader, underflik, kombinera, flytta till Iris), (4) engelska översättningen
av varje sida plus en mekanisk tvåspråkighetsregel. Dessutom: testerna efter rebasen är
inte körda och sex lokala commits är opushade.

## Läget, verifierat i dag (inte antaget)

| Vad | Fakta |
|---|---|
| Adminfelet i main | **Bekräftat i Railway-loggen** (api/main): `asyncpg UndefinedColumnError: column t.status does not exist` i `app/api/admin.py:35` (`GET /api/admin/tenants`, 500). Alla tre sidorna (`/admin`, `/admin/kunder`, `/admin/paket`) anropar `listTenants()` → samma 500. Felet är backendens 500-text, inte Next's error.tsx. |
| Adminytan i development | **Inget sådant fel i loggen.** 079 + 080_paket_admin är körda där. (Antons antagande "ligger även på development" stämmer inte.) |
| Torrkörning main | `+ 079_iris_bedomning, + 080_paket_admin, + 080_korningar, + 081_kontakt_telefon` väntar. |
| Torrkörning development | `+ 080_korningar, + 081_kontakt_telefon` väntar. |
| `railway_migrate.py` | Har INGEN per-fil-filter: `--apply` kör alla väntande i filordning. Mot main betyder det alla fyra. 080_korningar/081 är rent additiva (kolumner med default) och ingen kod i main läser dem. |
| Git | `development` lokalt **6 commits före** origin (inkl. conclude-committen), 30 filer, ej pushade. Testsvit + tsc **ej körda** efter rebasen. |
| Variabler api/development (bara namn) | `IRIS_JEV=skugga`, `TYPESAFE_API_KEY` finns, `SCRAPEGRAPHAI_API_KEY` finns, `LEADS_PIPELINE=v2`. **`LEADS_MERINFO` saknas.** Jev är alltså redan pushad i skuggläge. |
| Variabler api/main | `SCRAPEGRAPHAI_API_KEY`, `LEADS_PIPELINE=v2`. Ingen Jev, ingen merinfo (rätt — avtal saknas). |
| Lokal `.env` | `TYPESAFE_API_KEY` och `SCRAPEGRAPHAI_API_KEY` finns (namn kontrollerade, inte värden). |
| Minne | 12,5 GB ledigt commit, 1,6 GB fysiskt. pytest och tsc går, men inte parallellt med dev-server. |
| Sidofynd dev-loggen | `processor.py:273 → storage.search_kb` kraschar vid mejlprocessering (Vertex-embeddings 500 → full-text-fallback faller). Inte i scope; noteras i handoff. |
| i18n-mekanism | `lib/i18n.tsx`: `useLocale()` → `text({sv,en})`, `t(CopyKey)` för 29 delade nycklar. Admin: `lib/admin/sprak.ts` `a(nyckel, locale)`. Bara 29 tsx-filer anropar `useLocale`. |
| Oöversatt yta | 131 filer / ~2 300 rader oparad svenska (kommentarer och `sv:`-rader bortsorterade). Topp: email-studio/route.ts (API), DesignDrafts (utkast), integritetspolicy, LeadsRunForm 83, OnboardingWizard 83, LandingPhoto 79, Dashboard 72, Oversikt 72, IrisBolag 60, LeadslistorView 59. |
| Meta-testet | `tests/invariants/test_meta_invariants.py:22` regex `INV-[A-Z]+-\d+` — ett id med siffror (I18N) parsas aldrig. **Namnge invarianten `INV-COPY-001`.** |
| "CRM-lista" | `lib/demo/sektioner.ts:45`, Sebbes `c1c3c0c` (2026-09-12). Hela demonavet är råa svenska strängar; `AppShell.tsx:287,291` renderar `child.label` direkt. |
| Kicker-etiketterna på /demo | `components/dashboard/Oversikt.tsx:646–663` + `:840,849`, klass `.kicker` (globals.css:258). INV-UI-001-brott men på skuldlistan `_SKULD_2026_09_28`. |

## Ordning och ett medvetet avsteg

Antons ordning: H1 admin → H2 development → H3–H5 listor → H6–H7 översättning.
**Avsteg:** tvåspråkighetsregeln + det mekaniska testet (H7) läggs FÖRE listarbetet, för
att listornas nya UI ska födas tvåspråkigt och fällas av testet annars. Själva
översättningspasset (H6) ligger kvar sist. Allt annat i Antons ordning.

---

## Fas 0 — Grund (ingen kod)

- [ ] 0.1 `.agent-chorus/CHECKPOINT.md` uppdaterad (agent, tid, gren, uppgift, filer).
- [ ] 0.2 Kör sviten efter rebasen: `cd snajp-support && python -m pytest tests -q -x` (förväntat ~2 320 gröna) och `npx tsc --noEmit` i roten. **Sekventiellt**, inte parallellt (minne). Rött här stoppar allt tills det är lagat.
- [ ] 0.3 `python -m pytest tests/invariants -q` i roten (rotvakterna, ~397).
- [ ] 0.4 **Granskning av förra sessionens sex commits** (`git diff origin/development..development`, 30 filer, ≈5 200 rader) innan något pushas. Antons krav: "säkerställ att allt som byggdes följer med, gå igenom det och kontrollera så allt är bra."
  - Jag läser hela diffen själv, fil för fil, mot handoffens § 6 (Del A, Del G, merinfo) och planens rutor A1–A7, G1–G3, B-tillfällig: varje påstådd leverans ska finnas i koden, inte bara i texten.
  - Två Opus-granskare parallellt med avgränsat mål och namngiven kontroll: (a) backend — `leads.py` (`_spara_korning`, `_fyll_pa`, routes `/leads/korningar`), `storage/{base,memory,postgres}.py` (tre lager i synk, INV-STORE-001), `merinfo.py` + taxonomin, migration 080_korningar/081; kontroll: `pytest tests/invariants/test_inv_job_003.py tests/api/test_korningar.py tests/leads/test_merinfo.py -q` grönt och inga personuppgifter i fixturerna. (b) frontend — `IrisKorningar.tsx`, `LeadsRunForm.tsx` (pollning, localStorage-återupptagning, "Följ körningen"), `AppShell.tsx` (railfot/mobilrad, fokusordning), `LeadslistorView.tsx`/`IrisBolag.tsx` (telefon), `routes.ts`/`i18n.tsx`/`WorkspaceSection.tsx`; kontroll: `npx tsc --noEmit` rent, `pytest tests/invariants -q` grönt, catch-all-proxyn täcker de nya GET-vägarna.
  - Fynd rättas i samma commit-serie (`fix(...)`) före push. Kända luckor från handoffen som ska bekräftas i koden: Körningar-vyn är enspråkig (rättas i Fas 5.1), `is_test` på liggarraden sätts, batchraden lämnar `processing` vid fel.

Kontroll: tre gröna körningar loggade i handoffen med antal, plus granskningsrapporten (fynd → rättning → test) i handoffen.

---

## Fas 1 — Adminytan i main (H1, Antons prioritet 1) — kräver Antons ord

Rotorsak bekräftad (tabellen ovan). Ingen kodändring behövs; det är en migration.

- [ ] 1.1 **Antons go givet 2026-10-02 ("1. Ja"):** `python scripts/railway_migrate.py --env main --apply` kör alla fyra väntande (079, 080_paket_admin, 080_korningar, 081). De två nya är additiva kolumner med default, ingen kod i main läser dem, och lika schemaversion öppnar nattspegeln. Torrkör en gång till omedelbart före, och avbryt om listan skiljer sig från tabellen ovan.
- [ ] 1.2 Kör. Verifiera: torrkörning igen ger bara `=`; `railway logs --service api --environment main` visar inga nya `UndefinedColumnError`; `/admin`, `/admin/kunder`, `/admin/paket` renderar — Anton loggar in i webbläsarpanelen (jag matar aldrig in lösenord), jag tar skärmbilderna.
- [ ] 1.3 STATUS.md: en rad om att adminfelet var saknad migration, och att Sebbes commit-regel ("torrkör och kör INNAN mergen") ska in i release-rutinen i `DEPLOY.md` (en mening under main-avsnittet).

Kontroll: skärmbild av de tre sidorna utan felruta + ren torrkörning.

---

## Fas 2 — Development: migrera, pusha, aktivera merinfo (H2, Antons avbrutna order)

Förutsätter Fas 0 grönt (inklusive granskningen 0.4). Jev är redan på i skuggläge; **Anton svarade "På"**, så läget byts till `pa` i 2.4.

- [ ] 2.1 `python scripts/railway_migrate.py --env development --apply` (torrkört: bara 080_korningar + 081). Måste ske FÖRE push — koden på development skriver `leads_job_ledger.korning` vid varje Iris-körning.
- [ ] 2.2 `git branch --show-current` = development → `git push origin development`. Railway deployar själv.
- [ ] 2.3 `railway variables --set LEADS_MERINFO=scrapegraph --service api --environment development` (SCRAPEGRAPHAI_API_KEY finns redan, kontrollerat per namn). Aldrig i main (merinfos villkor).
- [ ] 2.4 Jev i skarpt läge: `python scripts/keys.py --push-jev development --jev-lage pa` (läser nyckeln ur `snajp-support/.env`, provar den skarpt mot TypeSafe, sätter `IRIS_JEV=pa` på api/development och deployar; värdet hanteras aldrig av mig). I `pa` fäller triagen kandidater bara vid hög säkerhet (≤0,08 på ett måste-kriterium eller ≥0,92 på en uteslutning, `jev.py:58–59`) och faller öppet vid fel. Efter 2.5: läs Jev-statistiken och tratten i Körningar och rapportera hur många kandidater som föll, så Anton ser effekten av `pa` direkt.
- [ ] 2.5 Verifiera deployen: `/health/ready` på web-development; starta en lista ("bygg, Mölndal, 5") och en Iris-körning (3 leads) på development; följ dem i Iris › Körningar; raderna har namn, roll, telefon. Jev-statistiken (`/api/leads` jev-stats) visar anrop.

Kontroll: körnings-id:n, radantal och skärmbild av Körningar-vyn i handoffen.

---

## Fas 3 — Tvåspråkighetsregeln + mekanisk grind (H7)

**Filer:** `CLAUDE.md` (under "Projektregler — drift"), `AGENTS.md` (speglas, sync-agent-configs: CLAUDE.md är kanonisk), `DESIGN.md` § Copy (L249), `ARCHITECTURE_INVARIANTS.md` (ny post under `## Active`, formatet L16–24), ny `tests/invariants/test_inv_copy_001.py`.

- [ ] 3.1 Regeltexten (samma lydelse i alla tre): *Varje komponent med användarvänd text är tvåspråkig (sv + en) via `lib/i18n.tsx` — `text({sv, en})` eller en modulkonstant av `Localized` — utan undantag. Grinden: INV-COPY-001.*
- [ ] 3.2 `test_inv_copy_001.py`, kopia av mönstret i `test_inv_ui_001.py` (kommentarsstrippning, `_fynd`, skuldlista, `test_grinden_fäller_det_den_ska`, `test_appytorna_finns`):
  - Scope: INV-UI-001:s `APPYTOR` **plus** `app/demo`, `app/kvitton`, `app/support`, `app/leads`, `app/avregistrera`, `components/marketing`, `components/crm`, `components/auth`, `lib/demo/sektioner.ts`.
  - Fynd: rad med `[åäöÅÄÖ]` i JSX-text (`>\s*[^<{]*[åäö]`) eller i strängliteral, som INTE står på en rad med `sv:` eller inom ett `{ sv: …, en: … }`-objekt. Rader med bara identifierare (`värde`, `kör(`) hanteras av att kräva mellanslag eller skiljetecken i träffen; justeras mot de två kontrollsnuttarna.
  - Scope även: `app/integritetspolicy`, `app/villkor`, `app/angerratt`, `app/cookies` (Anton: översätt dem).
  - Uteslut: `lib/i18n.tsx`, `lib/admin/sprak.ts`, `components/marketing/copy.ts`, `lib/admin/exempeldata.ts`, `lib/demo/*` (utom sektioner.ts), `components/DesignDrafts.tsx`, `app/forhandsvisning/**`, `app/api/**`.
  - `_SKULD_2026_10_02` = exakt de filer som faller i dag (≈120), så testet är grönt från dag ett och `test_skulden_ar_fortfarande_skuld` tvingar bort varje fil när den översatts.
- [ ] 3.3 Rätta meta-testets lucka minimalt? **Nej** (ponytail): byt bara namn till INV-COPY-001; att vidga regexen drar in tre INV-LEADS-poster som aldrig kontrollerats och kan fälla CI oväntat. Notera luckan i ARCHITECTURE_INVARIANTS-posten.

Kontroll: `pytest tests/invariants/test_inv_copy_001.py` grönt; en medvetet enspråkig testsnutt faller; `test_meta_invariants` ser posten.

---

## Fas 4 — Listorna (H3, H4, H5)

Allt nytt UI här skrivs tvåspråkigt (Fas 3 fäller annars).

### 4A Spara rader med bara mejl (H3)

**Filer:** `snajp-support/app/leads/sources/merinfo.py`, `snajp-support/tests/leads/test_merinfo.py`, `components/leads/LeadslistorView.tsx`.

- [ ] 4A.1 `sok` L536–539: behåll alla listrader som kandidater, men **sortera rader med telefon först** så bolagssidetaket (`min(90, antal·3)`) träffar de billiga först. (Mejl syns aldrig på listsidan, så rader utan telefon måste få sin bolagssida hämtad.)
- [ ] 4A.2 `granska` (L548–555): om varken `telefon` eller `epost` men `website` → `discovery.hamta_kontaktvag(website)` (httpx, ingen ScrapeGraph-kostnad, ≤3 sidor) fyller `epost`. Räkna anropen i loggen (mät).
- [ ] 4A.3 `kontrollera` L428: `personer` krävs fortfarande; `telefon or epost` räcker. Felmeningen: "Ingen verifierad kontakt: namn, roll och telefon eller mejl krävs."
- [ ] 4A.4 `_kodpoang`: telefon +1 (före mejl), så rangordningen föredrar telefon vid lika.
- [ ] 4A.5 Tester: `test_kontaktkravet_och_kanda_fakta_faller` uppdateras; nytt fall "bara mejl → godkänd", "varken telefon eller mejl → faller", "hamta_kontaktvag fyller mejl (stubbad)".
- [ ] 4A.6 UI i `Listtabell`: segmentkontroll **Alla · Telefon · Mejl · Båda** (klientstate, filtrerar på `contact_phone`/`contact_email`) + sortering (kontaktväg, bolag A–Ö). Ny kolumn "Kontaktväg" med chip (tel/mejl/båda); CSV får rubrikerna tvåspråkigt via `text()`. Mobilkorten visar samma chip.

Kontroll: skarp lista "bygg, Mölndal, 10" på development innehåller rader i alla tre kontaktvägarna; fliken Mejl visar bara mejl-rader.

### 4B Kombinera flera listor (H4)

**Filer:** ny `supabase/migrations/20261003100000_082_listor_kombinerade.sql`, `snajp-support/app/storage/{base,memory,postgres}.py`, `snajp-support/app/api/leads.py`, `snajp-support/app/api/schemas.py`, `snajp-support/tests/leads/test_leadslistor.py`, `components/leads/LeadslistorView.tsx`.

- [ ] 4B.1 Migration 082: `lead_lists.kalla text not null default 'sok' check (kalla in ('sok','kombinerad','import'))`, `lead_lists.kallistor uuid[]`, `lead_lists.kontaktfilter text` (`alla|telefon|mejl|bada`). Index `lead_list_items (list_id, orgnr)` (icke-unik; dedup sker i kod eftersom orgnr kan saknas).
- [ ] 4B.2 `POST /api/leads/listor/kombinera` `{titel, list_ids[2..10], kontaktfilter}` → verifierar att alla listor tillhör tenanten och är `klar`; skapar ny `lead_lists`-rad (`kalla='kombinerad'`, `status='klar'`, `icp` = sammanfattning av källistornas icp, `antal` = radantal); kopierar rader med `add_lead_list_item` (loop, ponytail: ingen bulk-insert), **dedup på `orgnr`, fallback casefold `company_name`** när orgnr saknas; filtret tillämpas före kopiering. Svar: `{list, items, dubbletter_bort: n}`.
- [ ] 4B.3 Storage: `create_lead_list` får `kalla`, `kallistor`, `kontaktfilter` (alla tre lager, INV-STORE-001); `list_lead_lists`/`get_lead_list` returnerar dem.
- [ ] 4B.4 UI: kryssrutor på listraderna, panel "Kombinera valda" (titel, filter-radio, knapp); den nya listan visar "Byggd av: A · B" och filtret. Källistorna rörs inte.
- [ ] 4B.5 Tester: dedup på orgnr, fallback på namn, filter `mejl` ger bara mejlrader, främmande tenant → 404, lista i `byggs` → 409.

Kontroll: två listor (bygg Mölndal + bygg Göteborg) → kombinerad, dubblettantalet stämmer med handräkning.

### 4C Flytta till Iris / utkast för alla, med research per bolag (H5)

**Varför inte dagens knapp:** "Skriv utkast till alla med mejladress" (`skrivUtkastForRad`, LeadslistorView L534–668) går direkt till `POST /leads/outreach/draft` utan `run_research_step` — mall ur radens metadata, i strid med regeln "Aldrig mall som utkast". Och `start_batch_run` med `company_names` skapar nya prospekt utan kontakt/telefon/orgnr, `batch_id=None`, så Körningar visar inget. Båda vägarna ersätts.

**Filer:** `snajp-support/app/api/leads.py`, `schemas.py`, `storage/{base,memory,postgres}.py` (`create_prospect` får `contact_phone`), `snajp-support/tests/leads/test_leadslistor.py`, `components/leads/LeadslistorView.tsx`, `lib/i18n.tsx`.

- [ ] 4C.1 `create_prospect` (base.py:847 + memory + postgres) tar `contact_phone`; `listrad_till_prospekt` (L2283) skickar `contact_phone` och `orgnr` (orgnr i `profil`).
- [ ] 4C.2 `POST /api/leads/listor/{list_id}/till-iris` `{item_ids?: [], scope: 'research'|'research_and_draft', is_test}`:
  1. per rad: samma logik som `listrad_till_prospekt` (dedup på namn mot befintliga prospekt) → `prospect_id`;
  2. skapa batchrad i liggaren med `scope='batch'`, `korning={mal: n, undersokta: 0, levererade: 0, tratt: {}, kalla: 'lista', list_id}` via `_spara_korning`;
  3. `_lagg_prospektjobb(prospect_id, scope, batch_id=batch)` per prospekt — `_run_batch_prospect` kör då research (v2 → `bedomning.bedom` → lägesbeskrivning/poäng/nivå) och utkast när scope säger det;
  4. vid varje barnjobbs slut: uppdatera batchens `korning` (undersökta/levererade/tratt) och sätt batchen `completed` när sista barnet är klart (`registrera_utfall` i `korning.py:113` räknar redan när `batch_id` finns — koppla `_spara_korning` dit).
  Svar: `{batch_id, prospekt: n}`; frontend länkar "Följ körningen →" till `/dashboard/iris/korningar/<batch_id>`.
- [ ] 4C.3 **Känd gräns, sägs rakt ut i UI:t:** `leverbar` (leads.py ≈1975–1990) kräver arbetsmejl, så en rad med bara telefon får research och bedömning men inget utkast (`draft_note` "hoppade över"). Att ändra det är planens del C (`plans/2026-10-01-leads-suite-och-korningar.md`), inte den här fasen. Körningar-vyn visar skälet per rad (tratten).
- [ ] 4C.4 UI: i listdetaljen ersätts "Skriv utkast till alla med mejladress" och per-rad-utkastet med **"Flytta till Iris"** (valda eller alla) + val research / research + utkast; kvitto med länk till körningen. "Lägg alla i registret" blir "Flytta till Iris (bara research)". `skrivUtkastForRad` tas bort.
- [ ] 4C.5 Tester: till-iris skapar prospekt med telefon+orgnr, batchrad med `korning.kalla='lista'`, barnjobb köade med batch_id; dubbelklick skapar inte dubbla prospekt; främmande tenant 404.

Kontroll: "Flytta till Iris" på en 5-radslista på development → Körningar visar raden, undersökta räknas upp, varje bolag har bedömning; utkast finns för raderna med mejl.

---

## Fas 5 — Översätt varje sida (H6)

**Mönster:** ≤10 strängar → inline `text({sv, en})`; fler → modulkonstant `const T = { nyckel: { sv, en } } satisfies Record<string, Localized>` (StartView-mönstret). Admin fortsätter med `lib/admin/sprak.ts`. Inga nya mekanismer. Formatering av datum/antal via `sprak.ts`:s `datum`/`antal` där de redan används.

Ordning (varje steg: filen bort ur `_SKULD_2026_10_02`, INV-COPY-001 grönt, tsc rent):

- [ ] 5.1 **Förra sessionens egna filer** (Antons uttryckliga första steg): `IrisKorningar.tsx`, `LeadsRunForm.tsx` (statusraden, knappar, "Följ körningen", "Beslutsfattare"), `AppShell.tsx` (railfot L426–441, mobilrad L498–508, demonav L287/291 via `text(child.label)`), `LeadslistorView.tsx` (CSV-rubriker, "Org.nr", telefon), `IrisBolag.tsx`.
- [ ] 5.2 **Demon** (Antons skärmdumpar): `lib/demo/sektioner.ts` → `label: Localized` ("CRM-lista" → `{sv:"CRM-lista", en:"CRM list"}`), `app/demo/[[...slug]]/page.tsx` titlar (L117, 124, 148, 172, 185, 196), `components/dashboard/Oversikt.tsx` (72 rader) **inklusive kicker-etiketterna → vanlig etikettstil**, filen bort ur `_SKULD_2026_09_28` i INV-UI-001. `WorkspaceViews.tsx:282` samma.
- [ ] 5.3 **Produktsidorna** `/kvitton`, `/support`, `/leads`: `components/marketing/ProductPage.tsx` (+ `useLocale`), `KvittoDemo.tsx` (chrome, inte fixturdata), `SupportShowcase`, `LandingPhoto.tsx` (79), `EmailStudioEditor`, `ProduktBilder.tsx` (chrome).
- [ ] 5.4 **Leads/Iris:** `Bolagssida.tsx` 54, `Bolagsregister.tsx` 36, `LeadsSnabbsok.tsx` 28, `IrisProfil.tsx` 19, `IrisGranskning.tsx` 19, `LeadsControls.tsx` 15, `AgentLarande.tsx`.
- [ ] 5.5 **Support/kvitton/inställningar:** `snajp/Dashboard.tsx` 72, `SupportChat.tsx` 45, `settings/Inkorgar.tsx` 42, `Kunskapsbas.tsx` 40, `SupportEskalering.tsx` 27, `kvitton/KvittoYta.tsx` 27, `dashboard/Analys.tsx` 34, `WorkspaceViews.tsx` 43, `SoulEditor.tsx` 20.
- [ ] 5.6 **Auth/admin/marknad:** `OnboardingWizard.tsx` 83, `LoginForm.tsx` 30, `avregistrera/[token]` 16, `admin/Kundprofil.tsx` 38, `Agentinstruktioner.tsx` 28, `PaketHantering.tsx` 24, `Kundtabell.tsx`, `admin/kunder/[id]/page.tsx`, `PricingSection.tsx` 22, `LaddaNerAppen.tsx` 20, `vart-team/page.tsx` 34, `crm/CrmDemo.tsx` (chrome).
- [ ] 5.7 **Juridiska sidorna** (Anton: översätt): `app/integritetspolicy/page.tsx` 88, `app/villkor/page.tsx` 48, `app/angerratt/page.tsx` 35, `app/cookies/page.tsx`. Texterna är förstautkast med en synlig "ej juristgranskad"-ruta (GOALS delmål 15); den rutan översätts också, så engelska läsaren får samma förbehåll. Juridiska termer översätts konservativt (ångerrätt → "right of withdrawal", personuppgiftsbiträde → "data processor"); ingen innebörd ändras.
- [ ] 5.8 **Utanför:** `app/api/**` (serverfeltexter, inte JSX — lämnas), `DesignDrafts`/`forhandsvisning` (utkast).

**Delegering:** 5.3–5.6 går till Opus-subagenter per punkt (en fil-batch var, invariantstestet + tsc som namngiven kontroll, inga andra filer). 5.1–5.2 gör jag själv. Jag läser varje diff; engelskan granskas för ton (DESIGN.md § Copy: ingen tankstreck, inga kicker).

Kontroll: `_SKULD_2026_10_02` tom för alla appytor utom 5.8; språkväxling på development visar inga svenska strängar på `/demo`, `/kvitton`, `/support`, `/leads`, Iris-vyerna, inställningarna.

---

## Fas 6 — Pixelgranskning (H8) och avslut

- [ ] 6.1 På development efter push (Anton loggar in i webbläsarpanelen): Körningar-vyn, railen (320/768/1440, inget horisontellt spill, fokusordning rail → innehåll), listflikarna, "Kombinera", "Flytta till Iris", engelska läget på de sex sidorna. Jag bedömer bilderna själv.
- [ ] 6.2 `/simplify` på diffen; skippade fynd till `.agent-chorus/SIMPLIFY-SKIPPED.md`.
- [ ] 6.3 Uppdatera `plans/2026-10-01-leads-suite-och-korningar.md` (H-rutorna), STATUS.md, handoff, `/conclude`.

---

---

## Fas 7–10 — resten av beställningen 2026-10-01: Iris-kvalitet, inkorgen, spegeln, Leads Suite

Detaljerade rutor finns i `plans/2026-10-01-leads-suite-och-korningar.md` (del C, D, E, F).
Här står ordningen, vad dagens läge ändrar, och vad som byggs. Migrationsnumren
flyttas ett steg eftersom 082 tas av kombinerade listor (Fas 4B).

**Beroenden:** C bygger på merinfo-källan (klar) och Jev `pa` (Fas 2). D är fristående.
E behöver lika schemaversion i main och dev (löst av Fas 1). F visar det A–D producerar
och kommer sist. D och E kan byggas parallellt med C av separata Opus-agenter.

### Fas 7 — Del C: Iris-körningar med register ∩ signaler, obligatorisk lägesbeskrivning och kontakt

Antons ord: lägesbeskrivning med poäng och signaler MÅSTE finnas för alla leads Iris presenterar, kontaktperson med roll och telefon likaså, och mejlet ska utgå från just det bolagets läge.

**Filer:** `snajp-support/app/leads/korning.py` (`sokrunda`), `app/leads/jev.py` (`matcha_signaler`), `app/agent/leads_research_v2.py` + `agent-core/overlays/leads-research-v2.md` (nytt obligatoriskt fält `lagesbeskrivning`, `kontaktperson` förifylld ur registret), `app/leads/bedomning.py` (`leverbar`), `snajp-support/app/api/leads.py` (≈1975–1990, leverbar-villkoret), migration `083_iris_lagesbeskrivning` (`prospects.lagesbeskrivning text`, `signaler jsonb`; `contact_phone` finns redan via 081), `components/leads/IrisBolag.tsx`/`Bolagssida.tsx` (Lägesbeskrivning överst, Signaler med källa+datum, Kontaktperson med roll+telefon), utkastagenten (`run_outreach_draft` får lägesbeskrivning + signaler som tillåtna fakta; grundningsgrinden orörd).

- [ ] C1 Kandidatunion i `sokrunda`: merinfo-ringen för profilens bransch/ort ∪ signalkällor (JobTech, nyhets-RSS, merinfos bolagshändelser). Signalträff utanför registret slås upp på orgnr/namn och fälls om bransch/ort inte matchar. Jev `matcha_signaler` prioriterar kandidater vars signal matchar profilens `signaler[]`.
- [ ] C2 Research-schemat: `lagesbeskrivning` (4–6 meningar: vad bolaget gör, vad som hänt senast med källa, vad som matchar profilen, varför nu) och `kontaktperson {namn, roll, telefon, kalla}` förifylld från merinfo — modellen bekräftar/kompletterar med belägg, hittar aldrig på. Migration 083.
- [ ] C3 **`leverbar` ändras:** kräver kvalificerad + över tröskel + `kontaktperson.namn` + `roll` + (`telefon` ELLER arbetsmejl) + icke-tom `lagesbeskrivning`. Det tar bort dagens mejlkrav som gör att merinfo-leads med bara telefon inte räknas mot N (Fas 4C.3:s kända gräns försvinner här). Utkast skrivs fortfarande bara när arbetsmejl finns; utan mejl levereras leadet med telefon som kontaktväg och utkastet markeras "ring".
- [ ] C4 UI-detaljvyn + utkastets fakta. INV-LEADS-SCORE-001 utvidgas (test i `test_inv_leads_score_001.py`): *ett levererat lead har alltid lägesbeskrivning och kontaktperson med roll och telefon eller mejl.*
- [ ] C5 Skarp körning på development: Alunix-profilen 3 leads med utkast, Nordform-regressionen 5/5; alla har lägesbeskrivning + kontakt. Jev-tratten rapporteras.

### Fas 8 — Del D: Jev-sorterad inkorg och leads-inkorg under Iris

Antons ord: Jev sorterar kundtjänstinkorgen i supportrelaterat (klassificerat), ej relaterat, och lead; leads-kunder får en egen inkorg under Iris, samma system som kundtjänstinkorgen, dit de kopplar sin brevlåda.

**Arkitekturen** står utritad i den gamla planens del D (poller → ingest → klassning i tre steg: kodregler → Jev `choice` τ≥0,9 → LLM-triage; tre vägar support/lead/ej_relaterat; varje beslut i `ss_decision_log` med källa).

**Filer:** ny `snajp-support/app/email_pipeline/klassning.py`, migration `084_inkorg_klass` (`ss_emails.klass`, `klass_kalla`, `ss_mailboxes.syfte` support|leads|bada, status `ej_relaterat`), `processor.py` (klassning först; `lead` → `leads/svar.py`), `app/api/inbox.py` (`?klass=lead`, `POST /{id}/klassa` manuell rättning = lärdata), `app/leads/svar.py` (`nytt_inkommande_lead`: prospekt med `origin='inkorg'`, kontakt ur mejlet, status `replied`), `components/snajp/InboxTriage.tsx` (`yta: support|leads`), ny `components/leads/IrisInkorg.tsx` (flikar Inkommande · Svar · Att hantera · Dolda), rutt `/dashboard/iris/inkorg` i `lib/routes.ts` (grind: produkten leads räcker), `components/settings/Inkorgar.tsx` (steg 1: "Vad ska brevlådan användas till?"), `/admin/support` klass-chip + Jev-stödrad.

- [ ] D1 Klassningsmodulen + migration 084 + processorns väg (test: regler, Jev stubbad, LLM stubbad; prospektdomän → lead; nyhetsbrev → ej_relaterat)
- [ ] D2 Lead-vägen: svar till befintlig tråd (även annan adress på samma domän), nytt lead utan tråd
- [ ] D3 Inkorgs-API med `klass` + manuell omklassning
- [ ] D4 Leads-inkorgen under Iris + brevlådans syfte i guiden; tvåspråkig från start (INV-COPY-001)
- [ ] D5 Admin-support: klass-chip per rad och stödraden
- **Sidofynd att laga här:** dev-loggen visar `processor.py:273 → storage.search_kb` som kraschar när embeddings ger 500 (Vertex) — full-text-fallbacken faller. Rättas i D1 eftersom klassningen sitter i samma kedja.

### Fas 9 — Del E: nattlig spegling main → development och "Flytta till main" (bara admin)

Antons ord: alla konton och all data speglas till development, envägs; den ENDA vägen tillbaka är en adminfunktion i Byt kund där man markerar supportmejl eller leadskörningar och flyttar dem till main.

**Dagens läge ändrar:** E0 (migration 079 mot main) löses av Fas 1 — efter den har main och development samma schemaversion och `railway_seed_dev.py` slutar vägra. Första speglingen kan alltså köras för hand direkt efter Fas 1, på Antons ord (den skriver över development-data; testdata som ska sparas flyttas först).

**Filer:** `.github/workflows/spegla-dev.yml` (cron `0 2 * * *` + `workflow_dispatch`, `RAILWAY_TOKEN` ur repo-secrets, fönsterlöst per definition), `scripts/railway_seed_dev.py` (`--behall-flyttko` vägrar spegla om `dev_flytt_ko` har oflyttade rader; skriver `mirror_meta.seeded_at`), migration `085_flyttko` i BÅDA miljöerna (`dev_flytt_ko`, `ss_emails.importerad_fran`, `prospects.importerad_fran`), ny `snajp-support/app/api/admin_flytt.py` (`POST /api/admin/flytt/paket` i dev → signerat JSON-paket; `POST /api/admin/flytt/importera` i main → HMAC med `FLYTT_NYCKEL`, plattformsadmin, idempotent på id, vägrar om `mirror_meta` finns), ny `components/admin/FlyttTillMain.tsx` i Byt kund-menyn (bara `isPlatformAdmin` och bara när `mirror_meta.environment='development'`; kryssrutor, kvitto per rad, "Nästa spegling: <tid>. Allt oflyttat försvinner då."), `DEPLOY.md` spegelregeln.

- [ ] E1 Första spegling för hand (Antons ord) och verifierad: radantal per tabell matchar main
- [ ] E2 Workflow + flyttkö-spärren
- [ ] E3 Migration 085 + paket/importera + HMAC + tester (dubbelkörning = no-op "redan flyttad"; utan HMAC/admin/i spegel → 403)
- [ ] E4 Admin-panelen i Byt kund + kvitto; INV-DATA-003: *enda skrivvägen dev → main är `admin_flytt.importera`* (statisk grep + API-test)
- [ ] E5 `DEPLOY.md`
- **Antons handgrepp:** `FLYTT_NYCKEL` sätts i main och development med `scripts/keys.py` (värdet hanteras aldrig av mig).

### Fas 10 — Del F: Leads Suite — CRM-överblick, import, utkast per rad, uppföljning, automation, extern synk

Antons ord: inspiration från Salesforce/Upsales, teknisk förebild Twenty; verklig CRM-överblick över listor och Iris-leads, status/svar per lead, import av befintlig kundbas, utkast per prospekt, synk mot leads-inkorgen, uppföljning och automation med filter per leadtyp i inställningarna, integration med befintligt CRM.

**Ur Twenty bärs över:** bolaget är navet; varje händelse (körning, mejl ut, svar, statusbyte, anteckning, uppgift) är en tidslinjerad på bolaget; pipeline-status är ett valfält (kanban); sparade vyer per användare. Inte: egen metadata-motor, GraphQL, egen auth.

**Datamodell (minsta som bär överblicken):** `prospects` = bolaget (status-enumen `new…won/lost/suppressed` är pipelinen). `lead_lists.kalla` (från Fas 4B: `sok|kombinerad|import`) används som leadtyp tillsammans med `prospects.origin` (`iris|manual|import|inkorg`). Migration `086_leads_suite`: `lead_anteckningar`, `lead_uppgifter`, `lead_vyer` (filter+sort per användare), `prospect_status_logg`; tidslinjen är en VY `v_lead_handelser` över `agent_runs`, `outreach_messages`, `ss_emails` (klass lead), statusloggen, anteckningar, uppgifter — ingen dubbellagring.

**Vyer (under Iris i railen):** Bolag (tabell, kolumner status · nivå · poäng · kontaktväg · senaste händelse · nästa uppgift; inline-statusbyte; sparade vyer), **Pipeline** (kanban per status, drag = statusbyte, tangentbord, 44 px mål), Bolagssida (lägesbeskrivning, kontakt, tidslinje, anteckning, uppgift, "Skriv utkast", "Svara" via leads-inkorgen), Listor (Fas 4 + import), Inkorg (Fas 8), Körningar, Granskning, Inställningar.

**Import:** `POST /api/leads/import` tar CSV + kolumnkarta (namn, orgnr, kontakt, roll, e-post, telefon, status) → `lead_lists(kalla='import')`; färdiga kolumnkartor för HubSpot/Pipedrive/Salesforce/Upsales-export i `lib/leads/importmallar.ts`; parsning i webbläsaren (som `CrmDemo.tsx` redan gör), förhandsvisning av fem rader före skrivning. "Flytta till Iris" (Fas 4C) ger utkast per importerad rad med research.

**Automation (Inställningar → Iris):** regler per leadtyp (`iris|lista|import|inkorg`): utkast automatiskt vid nytt lead ja/nej; uppföljning efter N dagar utan svar (kopplar in färdiga `follow_up_generator.py`, GOALS delmål 12); Jev-tröskel för automatiskt bortval; positiva svar eskaleras till e-post/Slack (kanalerna finns). Allt genom granskningskön tills autonominivån säger annat (INV-SEC-004 orörd).

**Externt CRM (sist):** HubSpot/Pipedrive via REST med kundens egen nyckel (krypterad som integrationsnycklarna, GOALS öppen fråga 10): envägs ut (status + anteckning) först; tvåvägs när någon ber om det.

- [ ] F1 Migration 086 + tidslinjevyn + statuslogg
- [ ] F2 Bolagstabellen med inline-status och sparade vyer (`components/leads/LeadsTabell.tsx`)
- [ ] F3 Pipeline-kanban (`components/leads/Pipeline.tsx`)
- [ ] F4 Bolagssidan med tidslinje, anteckning, uppgift, utkast, svar
- [ ] F5 Import med kolumnkartor + förhandsvisning
- [ ] F6 Automationsregler + uppföljningskedjan inkopplad
- [ ] F7 Envägs synk ut till HubSpot/Pipedrive (bakom nyckel)
- Allt UI tvåspråkigt från start; `/design`-skillen + DESIGN.md för varje ny vy; pixelgranskning per vy (320/768/1440) gör jag själv.

### Granskningsfokus för Fas 7–10 (det ingen ruta testar av sig själv)

1. Körning startad, api:t deployas om mitt i → liggaren `processing` → `completed`, aldrig evig `processing`.
2. "Mölndal och Luleå" i samma profil → två separata sökningar, inget län-breddat av misstag.
3. Bolag med telefon men utan namngiven person → faller på kontaktkravet, syns i tratten, aldrig rad med `contact_name=null`.
4. Prospektsvar från annan adress på samma domän → `lead`, kopplat till tråden.
5. "Flytta till main" två gånger på samma mejl → no-op med kvitto, inga dubbletter.

### Sessionsindelning (realistisk)

Fas 0–2 och 3 ryms i en session. Fas 4 en session. Fas 5 (översättningen, 131 filer) en till två sessioner med subagenter. Fas 7–10 är var sin session eller mer; D och E kan gå parallellt med C. Varje session avslutas med `/conclude`, uppdaterade rutor i båda planfilerna och STATUS.md, så ordningen överlever ett avbrott.

---

## Verifiering (hela kedjan)

1. `python -m pytest snajp-support/tests -q` grönt, `npx tsc --noEmit` rent, `pytest tests/invariants -q` grönt (inkl. INV-COPY-001 och meta-testet).
2. Torrkörning main och development: bara `=`.
3. Railway-loggen api/main utan `UndefinedColumnError`; skärmbild av `/admin`, `/admin/kunder`, `/admin/paket`.
4. Development: en lista (alla tre kontaktvägar), en kombinerad lista (dubblettantal), en "Flytta till Iris" som syns i Körningar med bedömning per bolag.
5. Språkväxling: inga svenska strängar på de sex sidorna i Antons skärmdumpar.
6. `.agent-chorus/CHECKPOINT.md`, STATUS.md, handoff uppdaterade.

## Antons svar 2026-10-02 (inarbetade ovan)

1. Migrationerna mot main: **ja**, alla fyra väntande (Fas 1.1).
2. Jev: **på** (Fas 2.4).
3. Juridiska sidorna: **översätt** (Fas 3.2 scope, Fas 5.7).
4. Tillägg: **granska allt som byggdes förra sessionen** och säkerställ att det följer med (Fas 0.4).

Antagande utan fråga: Fas 3 (regeln + grinden) före listorna, så det nya UI:t föds tvåspråkigt.

---

## Status 2026-10-02 (session 3) — alla tio faser kodade, fyra moment kvar i Antons hand

### Klart i kod (25 commits lokalt på `development`, opushade)
- [x] Fas 4B kombinera (b0fc6a8, migration 082), Fas 4C Flytta till Iris (6112c9c).
- [x] Fas 5 hela översättningen: skuldlistan `_SKULD_2026_10_02` är TOM (3a06b06, 6bc46fb).
- [x] Fas 7 del C: register ∩ signaler, obligatorisk lägesbeskrivning, `_leverbarhet` utan mejlkrav (b027478, migration 083).
- [x] Fas 8 del D: klassning support/lead/ej relaterat, leads-inkorgen under Iris, brevlådans syfte (1759872, 9cc0a8e, migration 084).
- [x] Fas 9 del E: nattlig spegling + Flytta till main med HMAC, INV-DATA-003 (cbe2ae5, migration 085).
- [x] Fas 10 del F: F1–F7 (1b0ba87 backend, ef028d0 frontend, migration 086): tidslinje, anteckningar, uppgifter, sparade vyer, Tabell-segment, Pipeline-kanban, CSV-import med kolumnkartor, automation per leadtyp, envägs CRM-synk HubSpot/Pipedrive.
- [x] Fas 6.1 delvis: pixelgranskning av Pipeline, Tabell och importpanelen lokalt (demon, 1280 + 375, sv + en); ett fynd rättat (051f131). Flikarna i Iris › Bolag har pilnavigering (planens a11y-notering).
- [x] Grindar vid avslut: backend 2463 passed/4 skipped, rotinvarianter 425, tsc rent, node 162.

### Kvar — kräver Anton (behörighetsgrinden nekar auto-läget)
- [ ] Fas 2.2/2.3: `git push origin development` + `railway variables --set LEADS_MERINFO=scrapegraph --service api --environment development`.
- [ ] Fas 1: `python scripts/railway_migrate.py --env main` (torr) → `--apply` (079, 080_paket_admin, 080_korningar, 081 **plus nu 082–086**, alla additiva).
- [ ] Development: `python scripts/railway_migrate.py --env development --apply` (082–086) FÖRE eller direkt efter pushen.
- [ ] `FLYTT_NYCKEL` (main + development) och `FLYTT_MAL_URL` (development) via `scripts/keys.py`; repo-secret `ENV_DEPLOY` för `spegla-dev.yml`.
- [ ] Fas 2.5 + 6.1 skarpt: lista, Iris-körning, Flytta till Iris, Pipeline/Tabell med riktiga rader, engelska läget på development; `a11y-audit` på Körningar och listvyn.

### Känt och medvetet
- `/simplify`-skillen finns inte installerad; förenklingspasset gjordes för hand i granskningen av Fas 10 (inget utöver rättningarna ovan).
- Demon: Listor-segmentet anropar API:t och visar "Du måste vara inloggad" (fanns före Fas 10; importpanelen ärver det).
- Pipeline på telefon är sidledsscroll med 256 px-kolumner; första kolumnen (Ny) är ofta tom.
- Gamla prospekt med `origin='import'` går inte att skilja från CSV-importer; nya Iris-fynd får `'iris'`, listrader `'lista'`.

## Status 2026-10-02 (session 2) — /conclude

### Completed
- [x] Fas 0: checkpoint, 2375→2379 backendtester gröna, tsc rent, rotvakter gröna; granskning av 5f05678..0db86ac med ett blockerande fynd (uppgivet barnjobb låste körningen) och tio should-fix rättade — commit 5d16619.
- [x] Fas 2.1 development migrerad (080_korningar, 081). Fas 2.4 Jev `pa` deployad (ea40aad9).
- [x] Fas 3: regeln i CLAUDE.md/AGENTS.md/DESIGN.md, INV-COPY-001 med skuldlista — commit a1ef11e.
- [x] Fas 4A: mejl-rader + underflik Telefon/Mejl/Båda + sortering — commit 6204c00.
- [x] Fas 5.1, 5.2 (demon, Oversikt utan kickers), delar av 5.3/5.5/5.6: 37 filer, skuldlistan 89 → 52 — commits ee3ec59, 1b7de0c.

### In Progress
- [ ] Fas 5: 52 filer kvar. Agent A hann inte ProductPage/LandingPhoto/UspSection/SupportShowcase; agent B hann inte Inkorgar/Kunskapsbas/SupportEskalering/KvittoYta/Analys.

### Remaining
- [ ] Fas 2.2/2.3 push + LEADS_MERINFO (Antons hand, behörighetsgrinden), Fas 2.5 skarp verifiering.
- [ ] Fas 1 migrationen mot main (Antons hand, behörighetsgrinden "Production Deploy").
- [ ] Fas 4B, 4C, Fas 5.4–5.7, Fas 6, Fas 7–10.

### Blockers
- Auto-läget nekar `railway_migrate.py --env main --apply` och `git push` + `railway variables --set`; Anton kör dem i terminalen.
- `bd` nere (dolt saknas i PATH).

### Next Steps
1. Anton: `git push origin development`, `railway variables --set LEADS_MERINFO=scrapegraph --service api --environment development`, `python scripts/railway_migrate.py --env main` (torr) → `--apply`.
2. Fas 2.5 på development: lista "bygg, Mölndal, 10", Iris-körning 3 leads, Jev-tratt, Körningar-vyn, engelska läget.
3. Fas 4B (migration 082, kombinera) och 4C (Flytta till Iris med batch_id).
4. Fas 5 nästa batch i den ordning som står ovan.
5. Tillgänglighet (stop-hookens route-gap 2026-10-02, a11y-audit aldrig laddad): kontaktvägsfliken i LeadslistorView och flikarna i DemoSupportYta bär `role="tablist"`/`role="tab"` utan pilnavigering och roving tabindex. Antingen fullt tabs-mönster (←/→, Home/End, en tabbstopp) eller byt till en `radiogroup`/segmentkontroll utan tab-roller. Kör `a11y-audit` på Körningar, listvyn och demon när development är deployad (Fas 6).
