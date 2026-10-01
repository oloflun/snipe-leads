# Leads Suite, körningar, merinfo, leads-inkorg och spegling — plan

> **För agenter:** kör uppgift för uppgift med `superpowers:executing-plans`
> (eller subagent-driven när Anton säger det). Rutorna (`- [ ]`) bockas i.
> Allt arbete på `development`. Release till `main` kräver Antons ord.

**Mål:** kunden kan följa och återvända till varje Iris-körning; leadslistor
och Iris-leads byggs register-först ur merinfos bransch/län/kommun-träd och
kvalificeras av Jev; varje presenterat lead bär kontaktperson med roll och
telefon, poäng, signaler och en lägesbeskrivning; inkorgen sorteras av Jev i
support / lead / ej relaterat, och leads-kunder får en egen inkorg; dev speglar
main envägs varje natt med EN admin-väg tillbaka; en Leads Suite ger CRM-
överblick, import av befintlig kundbas och utkast per prospekt; menyn flyttar
ned i railen.

**Arkitektur i en mening:** samma mönster som Iris-profilen (plan 2026-09-30):
koden avgör, modellen formulerar, Jev är billig förgrind, allt tillstånd bor i
Postgres (aldrig bara i Redis eller i en React-komponent).

**Spec:** Antons beställning 2026-10-01 (chatten) + skärmdumparna av
`/admin/support`, `/admin/iris` och `www.snajp.se/dashboard/iris`.

**Spårning:** `bd` är nere (dolt saknas i PATH, samma fel som orkestratorn
rapporterade 2026-09-30). Rutorna här är spårningen tills `bd dolt start`
fungerar igen; skapa då ett epic per del (A–G) och klistra in rubrikerna.

---

## 0. Diagnos — varje symptom spårat till koden (verifierat 2026-10-01 på `0d25c2f`)

| Symptom (Antons ord) | Rotorsak i koden |
|---|---|
| "Inget sätt att bevaka eller återvända till en körning" | Körningens tillstånd (`korning`) bor i jobbstoret (`app/jobs/store.py`, Redis, TTL 3 600 s) och i `LeadsRunForm.tsx`:s React-state. `GET /api/leads/runs` listar `agent_runs` (LLM-anrop), inte körningar. `leads_job_ledger` (migration 059) har batchraden men inget tillstånd, ingen felorsak, ingen `updated_at`. Ladda om sidan = körningen är borta ur UI:t; efter en timme är den borta ur Redis också. |
| "Jobbet verkade sluta, inga leads genererades" | Tre kända vägar utan spår: (1) sökjobbet föll (`DiscoveryError`/timeout 180 s) → `jobs.fail` med text som bara LeadsRunForm läser i stunden; (2) `_fyll_pa` nådde `tak` eller `slut_pa_kandidater` → `klar=True` med `levererade=0`, bara i Redis; (3) deploy mitt i → XAUTOCLAIM-återtag, men liggarraden för batchen uppdateras aldrig till `completed`. Ingen av dem skriver något kunden kan se efteråt. |
| "Leadslistorna är katastrof" (Bygg i norrland → Adecco Malmö, Randstad Stockholm) | `_run_list_job` (`app/api/leads.py:2325`) bygger listan ur `hitta_bolag` = JobTech + nyhets-RSS + Gemini-utfyllnad. Jobbannonskällan söker på kundens *roller/signalord*, inte på bransch+ort som register; "kundtjänst" ger bemanningsbolag var som helst. Ingen rad kräver kontaktperson+roll+telefon (`lead_list_items.contact_*` är valfria). |
| "Lägesbeskrivning med poäng och signaler fungerar knappt" | Byggd 2026-09-30 (`bedomning.py`, migration 079) men bara för Iris-körningar via V2-kedjan; kräver `LEADS_PIPELINE=v2` och profil. Listorna går aldrig genom den. Kontaktperson kommer bara från bolagets egen sajt (`hamta_kontaktvag`) — ingen roll, aldrig telefon. |
| Inkorgen blandar support, leads och skräp | `processor.py` kör triage → `CATEGORY_LABELS` (8 supportfack). Det finns ingen klass "lead" och ingen "ej relaterat"; ett prospektsvar som landar i supportinkorgen får ett supportutkast. `POST /api/leads/svar` finns men anropas bara manuellt. |
| Konton i main syns inte i development | `scripts/railway_seed_dev.py` är envägs och säker, men manuell, och vägrar när schemaversionerna skiljer sig. Ingen har kört den sedan spegeln sattes. Ingen väg finns från dev till main alls (rätt — men Anton vill ha EN, admin-only). |
| Menyn ligger överst på kundytan | `AppShell.tsx:402–476` renderar BytKund/VyVaxel/språk/AgentMenu/Logga ut i en ljus `<header>`; `AdminShell.tsx:218–286` lägger samma kontroller i railens `footer` med `ton="rail"`. |

**Två beslut utanför koden som planen bygger på (säg till om något är fel):**

1. **merinfo.se:s villkor** (`/villkor`, läst 2026-10-01): *"Utan skriftligt
   samtycke är det förbjudet att kopiera innehåll på Merinfo, oavsett teknik."*
   Samma läge som allabolag/hitta/ratsit, som repots egen regel
   (`app/leads/sources/__init__.py`) förbjuder att skrapa. merinfo säljer
   däremot samma data via API/fil (`/data-via-api-eller-fil`, Informationsgruppen).
   Planen bygger därför **urvalsmodellen** (bransch → län → kommun, kontaktkrav,
   Jev-ranking) nu, bakom källprotokollet, med två hämtare: `api` (licensierad
   feed) och `webb` (HTML, som bara aktiveras av `MERINFO_SAMTYCKE=skriftligt`
   när Anton har deras skriftliga ja). Robots.txt tillåter sidorna, men robots
   är inte ett avtal. **Antons handgrepp:** be Informationsgruppen om pris på
   företagsdata med styrelse+telefon per bransch/kommun, eller om skriftligt
   samtycke för webbhämtning i vår volym (≈25 rader/sida, 1 anrop/s).
2. **Nattlig spegling raderar det som inte flyttats.** Spegeln är en
   fullständig kopia (truncate + copy). Testdata som ska sparas måste flyttas
   till main före nästa spegling. Admin-ytan säger det i klartext och visar
   tiden. Alternativet (selektiv spegling som bevarar dev-rader) är ett eget
   projekt och behövs inte förrän någon har förlorat något.

---

## 1. Arkitektur — hela kedjan efter planen

```
                     ┌──────────────── Iris-profil (per kund) ────────────────┐
                     │ branscher · orter/län · storlek · kriterier · signaler │
                     └───────────────┬────────────────────────────────────────┘
                                     │
   LISTA (volym)                     │                     KÖRNING (N leverbara)
   ─────────────                     │                     ────────────────────
   merinfo-trädet ───────────────────┼──────────────────── merinfo-trädet
   bransch/län/kommun                │                     + signalkällor (JobTech, nyheter,
        │                            │                       bolagshändelser)
        ▼                            │                          │
   kandidater (register-rader)       │                          ▼
        │  förfilter (kod)           │                     kandidater ∩ signaler
        ▼                            │                          │  förfilter (kod)
   Jev: rank mot kriterier ──────────┼───────────────────── Jev: triage + rank
        │  (score/choice, τ≥0,9)     │                          │
        ▼                            │                          ▼
   KONTAKTKRAV i kod:                │                     LLM-research per kriterium
   person + roll + telefon, annars   │                     → poäng, nivå, motivering,
   ut ur listan (tratt: "ingen       │                       LÄGESBESKRIVNING (obligatorisk),
   verifierad kontakt")              │                       kontaktperson + roll + telefon
        │                            │                          │
        ▼                            │                          ▼
   lead_list_items (N bästa)         │                     prospects (A/B) + utkast per lead
        └──────────────┬─────────────┴──────────────────────────┘
                       ▼
              LEADS SUITE (CRM-vyn): pipeline · tabell · bolagssida · tidslinje
              import av befintlig kundbas (CSV) · utkast per rad · uppföljning
                       ▲
                       │ svar, nya leads
              LEADS-INKORG ◄── Jev + triage: support | lead | ej relaterat ──► KUNDTJÄNST-INKORG
                       ▲
                       │ kundens kopplade brevlåda (syfte: support / leads / båda)
```

**Körningens tillstånd** lever i `leads_job_ledger.korning` (jsonb) och
uppdateras vid varje steg. Redis är fortfarande snabbvägen, aldrig sanningen
(INV-JOB-002 utvidgas till tillståndet, inte bara statusen).

---

## 2. Delar och ordning

| Del | Vad | Varför i den ordningen | Byggs |
|---|---|---|---|
| **A** | Körningar: bevaka, återvända, felorsak | Blockerar all verifiering av B–C (ingen kan se vad en körning gjorde) | **Den här sessionen** |
| **G** | Menyn ned i railen | Fristående, 1 fil, hög synlighet | **Den här sessionen** |
| **B** | merinfo-trädet som källa för listor | Listorna är "katastrof"; register-först är hela skillnaden | Nästa session (Antons TOS-besked avgör hämtaren) |
| **C** | Iris-körningar: merinfo ∩ signaler, Jev-urval, obligatorisk lägesbeskrivning + kontakt | Återanvänder B:s källa och bedömningen från 079 | Efter B |
| **D** | Jev-klassad inkorg + leads-inkorg under Iris | Fristående från B/C, men CRM:ens svarsflöde (F) hänger på den | Parallellt med B |
| **E** | Nattlig spegling main → dev + admin "Flytta till main" | Behövs för att testa C–D mot riktiga konton | Parallellt med B (liten) |
| **F** | Leads Suite (CRM) + import + automation | Sist: den visar det A–D producerar | Efter C och D |

---

## Del A — Körningar: bevaka, återvända, se varför det tog slut

**Filer**
- Skapa: `supabase/migrations/20261001100000_080_korningar.sql`
- Skapa: `components/leads/IrisKorningar.tsx`
- Ändra: `snajp-support/app/storage/base.py` (`set_leads_job_status` + nya `list_leads_korningar`, `get_leads_korning`), `memory.py`, `postgres.py`
- Ändra: `snajp-support/app/api/leads.py` (`_fyll_pa`, `_run_batch`, `start_batch_run`, nya routes)
- Ändra: `components/leads/LeadsRunForm.tsx` (återuppta via `localStorage`, visa länk till körningen)
- Ändra: `lib/routes.ts` (barnet `nav.iris.korningar`), `lib/i18n`-nycklar, `components/dashboard/WorkspaceSection.tsx`, `app/api/snajp-support/leads/korningar/...` proxy
- Test: `snajp-support/tests/invariants/test_inv_job_003.py`, `snajp-support/tests/api/test_korningar.py`

**Gränssnitt**
- Liggaren får `korning jsonb`, `error text`, `is_test boolean`, `updated_at timestamptz`.
- `GET /api/leads/korningar?limit=20` → `{korningar: [{job_id, status, scope, is_test, created_at, updated_at, completed_at, error, korning}]}` (bara `scope in ('batch','lista')`, nyast först).
- `GET /api/leads/korningar/{job_id}` → samma rad eller 404.
- `_fyll_pa` och alla `jobs.complete/fail` för batch skriver samma `korning` till liggaren (`set_leads_job_status(..., korning=k, error=...)`).
- INV-JOB-003: *En körnings tillstånd finns i liggaren efter varje steg; Redis-TTL får aldrig vara enda platsen.* Test: kör en batch mot MemoryStorage, töm jobbstoret, läs `get_leads_korning` → tillståndet finns med `levererade`, `tratt`, `slut_orsak`.

- [x] A1 Migration 080 + storage (tre lager, INV-STORE-001)
- [x] A2 `_fyll_pa`/`_run_batch` skriver tillståndet; felorsak sparas som `error`
- [x] A3 Routes (catch-all-proxyn täcker GET, inga nya Next-filer) (`/leads/korningar`, `/leads/korningar/[jobId]`)
- [x] A4 `IrisKorningar.tsx`: lista (datum · mål · levererade/undersökta · status · flaskhals), detalj (tratten rad för rad, levererade leads med länk till bolaget, felorsaken i klartext), pågående rad pollas var 3 s
- [x] A5 `LeadsRunForm`: `localStorage["snipra:korning:<tenant>"] = job_id` vid start; vid mount återupptas `följKörning` om raden inte är klar; "Följ körningen →" länkar till `/dashboard/iris/korningar/<id>`
- [x] A6 Rutt + meny: Iris får barnet **Körningar** (Bolag · Körningar · Granskning · Inställningar); admin speglar via `tillAdminvag`
- [x] A7 Tester gröna 2026-10-01 (2 320 backend, 397 rot, tsc ren). **Kvar:** `railway_migrate.py --env development --apply` (torrkörd: bara 080 väntar) FÖRE push, sedan pixelgranskning på development (maskinen hade 1,5 GB ledigt commit, ingen lokal dev-server startades)

---

## Del G — Menyn ned i railen (kundytan som adminytan)

**Filer:** `components/AppShell.tsx` (bara den), ev. `components/shell/Rail.tsx` om footern behöver `lg:`-varianten exponerad.

- [x] G1 Flytta `BytKund`, `VyVaxel`, språkknappen, `AgentMenu` och `Logga ut` till `Rail`:s `footer` i exakt samma komposition som `AdminShell.tsx:218–286` (`ton="rail"`, dold under `lg`, Logga ut + språk på en rad).
- [x] G2 Behåll den ljusa `<header>` BARA under `lg` (mobil): arbetsytans namn/Demo-märke till vänster, språk + Logga ut till höger, så mobilen inte tappar utloggningen när railen är ikonläge.
- [x] G3 Demons två utvägar (Till startsidan / Logga in) stannar i mobilraden och går in i railfootern på `lg+`.
- [ ] G4 Verifiera 320/768/1440 (INV-UI-001 grönt, tsc ren; pixelgranskning kvar, se A7) i webbläsaren: inget horisontellt spill, fokusordning rail → innehåll, INV-UI-001 grönt.

---

## Del B — merinfo-trädet som källa för leadslistor

**Varför register-först:** en lista på "bygg i Norrland" ska vara byggbolag i
Norrland. Ett register vet bransch och säte för varje bolag; en jobbannons
vet bara att någon rekryterar. Signalkällorna blir *filter och rankning* ovanpå
registret (del C), inte urvalet.

**Trädet (verifierat 2026-10-01):**
- `/sitemap/bransch` → 275 branscher på nivån `alla-lan/alla-kommuner/<bransch>`, grupperade i ~30 branschgrupper (t.ex. `byggbranschen` med tio underbranscher: anläggningsarbeten, fasadarbeten, VVS/el, takarbeten …).
- `/sitemap/bransch/<lan>/alla-kommuner/<bransch>` → kommunerna i länet (Västra Götaland: 49 kommuner + länsnivån).
- `/<bransch>/<kommun>/foretag/<sida>` eller `/<bransch>/<lan>/foretag/<sida>` → ~25 bolag per sida, JSON-LD `ItemList` med namn + bolags-URL (Mölndal bygg: 42 sidor ≈ 1 000 bolag).
- `/foretag/<Namn>-<orgnr>/<id>` → styrelse (`Styrelseledamot: <namn>`, VD, ordförande), telefon, adress + postnummer, antal anställda, omsättning, bolagsform, verksamhetsbeskrivning, status, hemsida/e-post när de finns, "Bolaget startades", kreditstatus.

**Geo-regeln (Antons):** nämns flera sammanhängande orter/regioner → ett bredare
filter (länsnivån, eller flera län för "Norrland" = Norrbotten, Västerbotten,
Jämtland, Västernorrland, Gävleborg, Dalarna); nämns två specifika kommuner →
två separata sökningar som slås ihop. Koden: `geo.merinfo_slugs(profil) ->
list[tuple[lan_slug, kommun_slug|None]]`.

**Filer**
- Skapa: `snajp-support/app/leads/sources/merinfo.py` (`MerinfoSource(ProspectSource)`, `MerinfoWebbHamtare`, `MerinfoApiHamtare`-stub, `tolka_bolagssida(html) -> Prospect`, `tolka_lista(html) -> list[url]`)
- Skapa: `snajp-support/app/leads/sources/merinfo_taxonomi.json` (branschgrupp → branscher → slug; län → kommuner → slug; genereras av `scripts/merinfo_taxonomi.py` från sitemapen, incheckad så körningen inte beror på nätet)
- Skapa: `scripts/merinfo_taxonomi.py`
- Skapa: `snajp-support/app/leads/branschval.py` (profilens branscher → branschgrupp/underbranscher; ett LLM-anrop med schema när ordlistan inte räcker, cachat per profilhash)
- Skapa: `supabase/migrations/..._081_kallcache.sql` (`lead_source_cache(url text pk, data jsonb, fetched_at timestamptz)` — 7 dagar; hövlig hämtning 1 anrop/s, `User-Agent: Snajp (kontakt@snajp.se)`)
- Ändra: `app/leads/geo.py` (kommun→län-karta, "Norrland"-expansion), `app/api/leads.py::_run_list_job` (ny kedja), `app/leads/forfilter.py` (bolagsform, status aktivt, anställda ur källan), `app/leads/jev.py` (`ranka(profil, kandidater) -> sorterad lista` med `score`-frågan per kriterium, `choice` för stödrad)
- Ändra: `lead_list_items` (migration 081): `contact_phone text`, `contact_verified_at timestamptz`, `orgnr text`, `bolagsform text`, `anstallda int`, `omsattning int`, `kvalificering jsonb` (Jev-utslag + stödrad)
- Test: `snajp-support/tests/leads/test_merinfo_tolkning.py` (fixturer: sparade HTML-sidor från 2026-10-01 — listsida + bolagssida), `test_branschval.py`, `test_geo_merinfo.py`

**Kedjan i `_run_list_job` efter B:**
1. `branschval` → branschslugs; `geo.merinfo_slugs` → (län, kommun)-par.
2. För varje par: listsidor tills `antal × 4` kandidater eller slut (tak 40 sidor).
3. Bolagssida per kandidat (cache) → `Prospect` med `extra={styrelse, telefon, bolagsform, status, omsattning}`.
4. `forfiltrera` (aktivt bolag, bolagsform ≠ enskild firma om profilen säger det, anställda inom spannet, undvik-ord).
5. **Kontaktkravet i kod:** `kontaktperson = VD or ordförande or första ledamot`; `telefon` måste finnas; annars tratten "ingen verifierad kontakt". Roll = merinfos beteckning. `contact_verified_at = now()`, `source_url` = bolagssidan (INV-DATA-001: källa, datum, laglig grund = berättigat intresse, B2B-rollperson).
6. `jev.ranka` mot profilens kriterier → topp `antal`. Utan Jev-nyckel: ordning = ring → anställda närmast profilens mitt → omsättning.
7. Skriv raderna först när hela bygget lyckats (samma regel som i dag).

- [x] **B-tillfällig (2026-10-01, Antons beslut i väntan på API-avtal med merinfo/allabolag):** registerkällan via ScrapeGraphAI i `snajp-support/app/leads/sources/merinfo.py`, bakom `LEADS_MERINFO=scrapegraph`. Trädet (275 branscher, 21 län, 290 kommuner) incheckat i `merinfo_taxonomi.json` (`python -m app.leads.sources.merinfo taxonomi`). Antons geografiregel, kontaktkravet (namn + roll + telefon), Jev-rangordning när Jev är på, migration 081 (`contact_phone`, `orgnr` på listrader). 22 tester i `tests/leads/test_merinfo.py`. Skarpt prov lokalt: bygg i Mölndal, 3 leads på 30 s, alla med namn, roll och telefon. Byts mot API-hämtaren när avtalet finns; urvalet står kvar.
- [ ] B1 Taxonomi-skriptet + JSON incheckad (kontroll: 275 branscher, 21 län, Västra Götaland 49 kommuner)
- [ ] B2 Tolkning av list- och bolagssida mot sparade fixturer
- [ ] B3 `MerinfoSource` bakom protokollet, hämtaren vald av `MERINFO_SAMTYCKE`/`MERINFO_API_NYCKEL`; utan någon av dem: `SourceError("merinfo: ingen tillåten hämtare")` och listan faller ärligt
- [ ] B4 Branschval + geo-slugs
- [ ] B5 Kontaktkravet + migration 081 + Jev-rankning
- [ ] B6 Ny `_run_list_job`-kedja; `LeadslistorView` visar roll + telefon + kvalificering; CSV får kolumnerna
- [ ] B7 Skarp lista "Bygg i Norrland, 25" på development: 25 rader, alla byggbolag med säte i de sex länen, alla med namn+roll+telefon

---

## Del C — Iris-körningar: register ∩ signaler, Jev-urval, obligatorisk lägesbeskrivning

**Filer**
- Ändra: `app/leads/korning.py::sokrunda` (kandidater = `MerinfoSource` för ringen ∪ signalkällor; signalträffar som inte finns i registret för bransch/ort slås upp via orgnr/namn och fälls om de inte matchar)
- Ändra: `app/leads/jev.py` (`matcha_signaler(profil, kandidat) -> {signal, stodrad, p}`; kandidater med signal som matchar profilens `signaler[]` prioriteras)
- Ändra: `app/agent/leads_research_v2.py` + `agent-core/overlays/leads-research-v2.md`: nytt obligatoriskt fält `lagesbeskrivning` (4–6 meningar: vad bolaget gör, vad som hänt senast med källa, vad som matchar profilen, varför nu) + `kontaktperson {namn, roll, telefon, kalla}` förifylld från registret, modellen får bara bekräfta/komplettera med belägg
- Ändra: `app/leads/bedomning.py`: `leverbar` kräver dessutom `kontaktperson.namn`, `roll` och (`telefon` eller `email`) samt icke-tom `lagesbeskrivning`; annars nivå B med skälet "kontakt saknas" i tratten och raden räknas INTE mot N
- Ändra: migration 082 på `prospects`: `lagesbeskrivning text`, `contact_phone text`, `signaler jsonb`
- Ändra: `IrisBolag.tsx` detaljvyn: Lägesbeskrivning överst, sedan Signaler (källa + datum), Kontaktperson (roll, telefon), Poäng/nivå, Kriterier, Utkast
- Ändra: utkastagenten (`run_outreach_draft`) får `lagesbeskrivning` + `signaler` som tillåtna fakta; grundningsgrinden fäller fortfarande allt som inte står där
- Invariant: INV-LEADS-SCORE-001 utvidgas: *ett levererat lead har alltid lägesbeskrivning, kontaktperson med roll och telefon/mejl.* Test i `test_inv_leads_score_001.py`.
- Källor för signaler (laglig ordning som i dag): JobTech, nyhets-RSS, merinfos bolagshändelser (nyregistrering, styrelseändring, adressändring) — LinkedIn-POSTER bara via bolagets egen sajt/presslänk, aldrig som första källa (INV-DATA-002 står kvar).

- [ ] C1 Kandidatunion i `sokrunda` + Jev-signalmatchning
- [ ] C2 Research-schemat + overlay + bedömningens kontaktkrav + migration 082
- [ ] C3 UI-detaljvyn + utkastets fakta
- [ ] C4 Skarp körning Alunix (3 leads, utkast på) och Nordform-regressionen; alla tre leads har lägesbeskrivning + kontakt

---

## Del D — Jev-sorterad inkorg och leads-inkorg under Iris

**Arkitekturen (det Anton bad om att få utritad):**

```
 kundens brevlåda (IMAP/OAuth, ss_mailboxes.syfte = support | leads | bada)
        │  poller.py (varje minut)
        ▼
 ingest.py ── spara ss_emails(status=new, klass=null)
        │
        ▼
 KLASSNING (ny: app/email_pipeline/klassning.py)
   1. kodregler, fäller säkert:  avsändare i suppressions → ej_relaterat
                                 ämnesprefix [PRIORITERAT] + Snajp-rad → att_hantera (som i dag)
                                 avsändardomän = ett prospekt/outreach_thread → lead
                                 nyhetsbrev-huvuden (List-Unsubscribe, Precedence: bulk) → ej_relaterat
   2. Jev (choice: support | lead | ej_relaterat), τ ≥ 0,9 → beslut + stödrad
   3. annars LLM-triage (befintlig classify) utvidgad med fältet klass
        │
        ├── support ──► processor.py som i dag (fack, eskalering, utkast)   → KUNDTJÄNST-INKORG
        ├── lead ─────► leads/svar.py: hantera_prospektsvar om tråd finns,   → LEADS-INKORG
        │               annars "nytt inkommande lead" (prospect skapas med
        │               origin='inkorg', kontakt ur mejlet, status=replied)
        └── ej_relaterat ─► status 'ej_relaterat', syns bara under "Övrigt/dolda"
 Varje beslut loggas i ss_decision_log med källa (regel | jev | llm) och stödrad.
```

**Filer**
- Skapa: `snajp-support/app/email_pipeline/klassning.py`
- Ändra: migration 083: `ss_emails.klass text check (klass in ('support','lead','ej_relaterat'))`, `ss_emails.klass_kalla text`, `ss_mailboxes.syfte text default 'support'`; status `ej_relaterat` i checken
- Ändra: `processor.py` (kör klassning först; `lead` → `svar.py`), `app/api/inbox.py` (`GET /api/inbox?klass=lead`, `POST /api/inbox/{id}/klassa` för manuell rättning som också blir lärdata), `app/leads/svar.py` (`nytt_inkommande_lead`)
- Ändra: `components/snajp/InboxTriage.tsx` får `yta: "support" | "leads"`; `components/leads/IrisInkorg.tsx` monterar den med `yta="leads"` (flikar: Inkommande · Svar · Att hantera · Dolda); rutt `/dashboard/iris/inkorg`, barn i `lib/routes.ts`, grind: produkten `leads` (leads-paketet räcker)
- Ändra: `components/settings/Inkorgar.tsx` steg 1 får valet "Vad ska brevlådan användas till? Kundtjänst / Leads / Båda" (`syfte`)
- Test: `snajp-support/tests/email_pipeline/test_klassning.py` (regler, Jev stubbad, LLM stubbad; tre klasser; prospektdomän → lead; nyhetsbrev → ej_relaterat)

- [ ] D1 Klassningsmodulen + migration 083 + processorns väg
- [ ] D2 Lead-vägen: svar till befintligt prospekt, nytt lead utan tråd
- [ ] D3 Inkorgs-API med `klass` + manuell omklassning
- [ ] D4 Leads-inkorgen under Iris + brevlådans syfte i guiden
- [ ] D5 Admin-support: `/admin/support` visar klass-chip per rad och Jev-stödraden

---

## Del E — Spegling main → development varje natt + "Flytta till main"

**Varför den inte redan går:** `railway_seed_dev.py` kräver samma
schemaversion. Efter PR #28 ligger `main` på samma kod som `development`
men **migration 079 är inte körd mot main** (handoffen 2026-09-30). Första
steget är därför Antons: `python scripts/railway_migrate.py --env main`
(torrkörning), sedan `--apply`.

**Filer**
- Skapa: `.github/workflows/spegla-dev.yml` — cron `0 2 * * *` (04:00 svensk sommartid) + `workflow_dispatch`; kör `railway_seed_dev.py --apply` med `RAILWAY_TOKEN` ur repo-secrets; artefakt: loggen. (Fönsterlöst per definition — inget lokalt jobb.)
- Ändra: `railway_seed_dev.py`: `--behall-flyttko` som vägrar spegla om `dev_flytt_ko` har oflyttade rader (så inget försvinner tyst), och skriver `mirror_meta.seeded_at` som admin-ytan visar
- Skapa: migration 084 (BÅDA miljöerna): `dev_flytt_ko(id, typ, ref_id, skapad_at, flyttad_at, resultat)`; `ss_emails.importerad_fran text`, `prospects.importerad_fran text`
- Skapa: `snajp-support/app/api/admin_flytt.py`:
  - `POST /api/admin/flytt/paket` (dev) → signerat JSON-paket av valda `ss_emails` (+drafts, tickets) eller en körning (`leads_job_ledger`-rad + prospects + prospect_sources + outreach_threads/messages)
  - `POST /api/admin/flytt/importera` (main) → tar emot paketet, verifierar HMAC (`FLYTT_NYCKEL`, bara i main och dev, aldrig i koden), kräver plattformsadmin, idempotent på id, sätter `importerad_fran='development'`, **vägrar om `mirror_meta` finns** (så dev aldrig kan importera till sig själv eller en annan spegel)
- Ändra: `components/admin/BytKund.tsx` → ny panel `components/admin/FlyttTillMain.tsx` i Byt kund-menyn, bara `isPlatformAdmin` och bara när `mirror_meta.environment='development'`: lista supportmejl och körningar med kryssrutor, "Flytta till main", kvitto per rad, raden "Nästa spegling: <tid>. Allt oflyttat försvinner då."
- Invariant INV-DATA-003: *Enda skrivvägen från development till main är `admin_flytt.importera`; mirror-skriptet pekar aldrig mot main.* Test: statisk grep i `tests/invariants/test_inv_data_003.py` + API-test att importera vägrar utan HMAC, utan admin, och i en databas med `mirror_meta`.

- [ ] E0 (Anton) migration 079 mot main, torrkörning först
- [ ] E1 Workflow + flyttkö-spärren i skriptet, första spegling körd för hand och verifierad (radantal matchar)
- [ ] E2 Migration 084 + paket/importera-routes + HMAC + tester
- [ ] E3 Admin-panelen i Byt kund + kvitto
- [ ] E4 Dokumentera i `DEPLOY.md` under spegelregeln (nattlig, flyttköns regel, nyckeln)

---

## Del F — Leads Suite: CRM-överblick, import, utkast per rad, uppföljning, automation

**Inspiration, hämtad ur Twenty (`packages/twenty-server/src/modules`):** objekten
`company`, `person`, `opportunity`, `note`, `task`, `timeline`, `messaging`
(mejltrådar kopplade till personer), `connected-account`, `workflow`. Det som
bärs över: **ett bolag är navet**, varje händelse (körning, mejl ut, svar,
statusbyte, anteckning, uppgift) är en tidslinjerad på bolaget, pipeline-
status är ett valfält man kan gruppera på (kanban), och vyer (filter + sort)
sparas per användare. Det som INTE bärs över: egen metadata-motor, GraphQL,
egen auth — vi har tenant/RLS och Next redan.

**Datamodell (minsta som bär överblicken):**
- `prospects` = Company (finns; status-enumen `new…won/lost/suppressed` är pipelinen)
- `lead_list_items` lyfts in i samma vy med `kalla='lista'|'import'|'iris'|'inkorg'`; "Lägg i registret" (finns) blir vägen från lista → prospekt
- Nya tabeller (migration 085): `lead_anteckningar(id, tenant_id, prospect_id, text, skriven_av, created_at)`, `lead_uppgifter(id, tenant_id, prospect_id, titel, forfaller_at, klar_at, skapad_av)`, `lead_vyer(id, tenant_id, user_id, namn, filter jsonb, sort jsonb)`
- Tidslinjen är en VY (`v_lead_handelser`) över `agent_runs` (research/utkast), `outreach_messages` (ut/in), `ss_emails` med `klass='lead'`, statusändringar (ny `prospect_status_logg`), anteckningar, uppgifter — ingen dubbellagring
- Import: `POST /api/leads/import` tar CSV + kolumnkarta (namn, orgnr, kontakt, roll, e-post, telefon, status) → `lead_lists(kalla='import')`; mallar för HubSpot/Pipedrive/Salesforce/Upsales-export som färdiga kolumnkartor i `lib/leads/importmallar.ts`; parsning i webbläsaren som `CrmDemo.tsx` redan gör, bekräftelse med förhandsvisning av fem rader före skrivning

**Vyer (under Iris, railen):** Bolag (tabell, Twenty-lik: kolumner status · nivå · poäng · kontakt · senaste händelse · nästa uppgift; inline-byte av status; sparade vyer), **Pipeline** (kanban per status, drag = statusbyte), Bolagssida (lägesbeskrivning, kontakt, tidslinje, anteckning, uppgift, "Skriv utkast", "Svara"), Listor (med import), Inkorg (del D), Körningar (del A), Granskning, Inställningar.

**Automation (Inställningar → Iris):** regler per leadtyp (`iris`/`lista`/`import`/`inkorg`): skriv utkast automatiskt vid nytt lead ja/nej; uppföljning efter N dagar utan svar (kopplar in den färdiga `follow_up_generator.py`, GOALS punkt 12); Jev-tröskel för automatiskt bortval; eskalera positiva svar till e-post/Slack (kanalerna finns). Allt genom granskningskön tills autonominivån säger annat (INV-SEC-004 orörd).

**Externt CRM-synk (sist, efter import):** HubSpot/Pipedrive via deras REST-API med kundens egen nyckel (krypterad som integrationsnycklarna, GOALS öppen fråga 10): envägs ut (status + anteckning) som första steg; tvåvägs först när någon ber om det.

- [ ] F1 Migration 085 + tidslinjevyn + statuslogg
- [ ] F2 Bolagstabellen med inline-status och sparade vyer (`components/leads/LeadsTabell.tsx`)
- [ ] F3 Pipeline-kanban (`components/leads/Pipeline.tsx`), tangentbordsnavigering, 44 px mål
- [ ] F4 Bolagssidan med tidslinje, anteckning, uppgift, utkast, svar
- [ ] F5 Import med kolumnkartor + förhandsvisning; "Skriv utkast" per importerad rad via befintlig bron
- [ ] F6 Automationsregler i IrisInstallningar + uppföljningskedjan inkopplad
- [ ] F7 Envägs synk ut till HubSpot/Pipedrive (bakom nyckel)

---

## Granskningsfokus (det ingen uppgift ovan testar av sig själv)

1. **En körning som startas, varefter api:t deployas om mitt i** — liggaren ska visa `processing` → `completed` med samma `korning`, aldrig en rad som står i `processing` för evigt (A: test med simulerad återtag).
2. **Två kommuner i olika län i samma profil** ("Mölndal och Luleå") — två separata sökningar, raderna märkta med sitt par, inget län-breddat av misstag (B4-test).
3. **Bolag med telefon men utan namngiven person** (styrelse saknas i källan) — faller på kontaktkravet och syns i tratten, hamnar aldrig som rad med `contact_name=null` (B5-test).
4. **Prospektsvar från en annan adress på samma domän** som utkastet gick till — klassas `lead` och kopplas till tråden, inte `support` (D2-test).
5. **"Flytta till main" körs två gånger på samma mejl** — andra gången är en no-op med kvitto "redan flyttad", inga dubbletter (E2-test).

---

## Antons handgrepp (ingen kod löser dem)

- [ ] merinfo: pris/avtal för API/fil, eller skriftligt samtycke för webbhämtning (del B, beslut 1 ovan) — utkast klart 2026-10-01 i `docs/utkast-merinfo-api-forfragan.md`, volym 1 000–7 500 uppslag/mån för 1–5 kunder; väntar på att Anton skickar
- [ ] migration 079 mot main (`railway_migrate.py --env main`, torrkörning först) — annars kan spegeln inte köras
- [ ] `FLYTT_NYCKEL` sätts i main och development med `scripts/keys.py` (värdet hanteras aldrig av agenten)
- [ ] Jev-nyckeln (`keys.py --key TYPESAFE_API_KEY`, `--push-jev development`) så Jev-rankningen kan skuggmätas
- [ ] `bd dolt start` (dolt saknas i PATH) så spårningen kan flyttas från den här filen till beads
