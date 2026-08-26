# Handoff: agentbackenden — tre döda kedjor, självlärande, eval-harness, kundminne

Skriven 2026-08-27 till Sebbe. Läs § "Det du behöver göra" först om du har bråttom.
Pushat till `development` (71fb992), **inte** till `railway-development` — den
pushen och migrationskörningen gör du (eller jag, på Antons ord).

Bakgrund: Anton bad om en full genomgång av agentbackenden — hitta brister,
optimera retrieval och responser, verifiera instruktionslager och skillkedja,
och sen fortsätta hämta arkitektur utifrån tills han sa stopp. Tre varv,
committat som en enda commit. Full mätrapport med bevis (skärmdumpar,
före/efter-citat): https://claude.ai/code/artifact/862c4b3b-e058-4959-86b8-caa84591b127

**Skillsen i `agent-core/skills/` är helt orörda.** INV-SKILL-005 vakar, och
skill-auditen (`python scripts/run_live_tests.py --skill-audit`) verifierar
att alla 22 steg i de fyra playbooksen renderar komplett. Allt nedan ligger i
orkestrering, kodgrindar och overlay-ytan — exakt den sanktionerade ytan du
och jag redan använder för tuning.

---

## Det du behöver göra

### 1. Migration 051 och 052 är inte körda i development

```bash
python scripts/railway_migrate.py --env development --apply
```

Två nya tabeller: `agent_suggestions` (självlärandet, se §3 nedan) och
`customer_memory` (kundminnet, §6). Ny kolumnkonstant i
`app/storage/base.py`: `AGENT_RUN_TYPES` fick `leads_svar` och
`leads_followup` — check-villkoret i migration 051 måste matcha, annars
kastar Postgres på första riktiga svarskörningen (samma felklass som
`agent_type`-buggen från i somras, se `tests/invariants/test_inv_store_001.py`).

### 2. Push till railway-development när du vill se det live

```bash
git push origin development:railway-development
```

Gör INTE detta blint — läs §7 (öppna trådar) först. Prospektsvar-vägen och
uppföljningsgeneratorn är nya kodvägar som aldrig körts mot en riktig
Postgres, bara mot MemoryStorage och `--skarp`-verifiering.

### 3. Adminytan `/dashboard/larande` är byggd men inte pixelverifierad inloggad

`components/leads/AgentLarande.tsx`, routad i `lib/routes.ts` +
`lib/i18n.tsx` + `WorkspaceViews.tsx`. tsc är rent och rotvaktposterna är
gröna (den nya routen beter sig som syskonflikarna oautentiserat), men jag
hade inget testkonto att logga in med — så själva klicket "godkänn ett
förslag och se artikeln skapas" är overifierat i webbläsaren. Kör det själv
en gång innan du litar på den.

---

## Tre döda kedjor, lagade

### A. Ingen kodväg skapade någonsin en `outreach_threads`-rad

`_queue_outreach_draft_impl` (i `app/agent/leads_tools.py`) skrev mot ett
`thread_id` som **ingen kodväg någonsin skapade**. `MemoryStorage` saknar
FK-kontroll, så hela testsviten var grön — men mot riktig Postgres hade
första riktiga utkastköningen fallit på foreign key-villkoret. Det här är
samma felklass som `agent_runs`-buggen i somras: minnet ljuger om vad
produktionen faktiskt gör.

Lagat: `ensure_outreach_thread(tenant_id, prospect_id=...)` i alla tre
lagringarna (`base.py`/`memory.py`/`postgres.py`) — get-or-create per
prospekt. `/api/leads/outreach/draft` tar nu `prospect_id` som alternativ
till `thread_id`.

### B. Prospektsvar hade ingen hanteringsväg

Svar-fliken läste `list_replies`, en tabell ingen kodväg fyllde.
`route_handoff()` i `app/leads/handoff.py` var byggd men saknade
produktionsanropare — precis det modulens egen docstring pekade ut.

Byggt: `app/leads/svar.py`, `POST /api/leads/svar`. Klassificerar svaret
(positivt/invändning/fråga/negativt/avregistrering/autosvar — okänt faller
försiktigt till fråga) och AGERAR I KOD, inte i modellen:

- **positivt** → köade utskick ställs in, `route_handoff` + `sa:call-prep`
  bygger underlag åt människan, prioriterat mejl, prospekt → `meeting`.
  Agenten bokar aldrig själv (strukturell begränsning, inget
  boknings-/prisverktyg i toolslistan).
- **invändning/fråga** → svarsutkast (skopad `mk:sales-enablement` →
  humanizer → grundningsgrind), **alltid** köat `awaiting_review` — oavsett
  kundens autonominivå. Autonomin styr den utgående sekvensen, inte ett svar
  i ett levande samtal.
- **avregistrering** → suppression, samma spärr som avregistreringslänken.
- **autosvar** → köade utskick skjuts en vecka, inte in.
- Påhoppsgrinden körs i kod FÖRE klassificeringen (samma princip som
  supporten): ett hot avbryter samtalet utan ett enda LLM-anrop.

Elva tester i `tests/leads/test_svar.py`.

### C. Uppföljningssekvensen anropades bara från tester

`follow_up.py` hade hela spaklogiken (Del H: svagaste spak i
värdeekvationen anfalls först, breakup sist) men ingen produktionsanropare
— öppen i beads sedan augusti (`snipe-3dx`, nu uppdaterad).

Byggt: `app/leads/follow_up_generator.py`. Ren policy-funktion
`trad_som_ar_forfallna()` — testbar utan databas — pekar ut vilka trådar
som är förfallna: stigande tystnadskrav (4/6/8/10 dagar), självbegränsande
(ett ogodkänt utkast eller ett inkommet svar tar tråden ur svepet, så
generatorn kan inte spamma). Köningen går genom **samma väg** som första
mejlet — lagstadgad fot, språkgrind, autonomi.

`app/leads/scheduler.py` fick `sweep_follow_ups()`, körs en gång i timmen
från send-loopen. Manuell trigger: `POST /api/leads/uppfoljning/svep`.

**Vad som INTE byggdes, med flit**: `weakest_lever`-ordningen (Del H:s
egentliga poäng) kräver att `offers`-rader faktiskt skrivs, vilket ingen
kodväg gör. v1 kör fast spakordning (`ponytail:`-markerad i koden med
uppgraderingsväg). Samma rot blockerar A/B-varianttracking
(`ab_variants` kräver `offer_id`).

---

## Självlärande persisterat (migration 051, ny invariant INV-LEARN-001)

`cs:kb-article` och leads kunskapsfångst (`_fanga_kunskap`) räknade ut en
lärdom på varje körning och **kastade den** — fanns bara i `step_log`.
Samma lucka återupptäcktes från noll i varje ärende.

Nu: `agent_suggestions`-tabellen. Support sparar `kb_article`-förslag,
leads sparar `marknadsinsikt`-förslag. Dedupe på `(tenant_id, dedupe_key)`
där `status='ny'` — tio ärenden om samma lucka ger EN granskningsrad.

**Hård regel, mekaniskt vaktad**: agenten skriver ALDRIG själv i
kunskapsbasen eller kontextpaketet. `POST /api/agent/forslag/{id}/godkann`
är enda kodvägen som skapar en KB-artikel — och det är endpointen som gör
det, inte agenten. Testat med en instruktionsattack: se
`test_kb_article_runs_on_kb_gap_and_suggestion_is_persisted`.

`cs:kb-article` är dessutom **villkorat** nu — körs bara vid kunskapslucka
eller säkerhetskritiskt ärende. Sparar ett LLM-anrop av sex på varje ärende
där KB redan bar svaret (den vanliga vägen).

---

## Retrieval och klassificering — fyra separata fixar

1. **`storage.search_kb` kör hybrid, inte antingen/eller.** Vektor OCH
   fulltext hämtas parallellt, slås ihop med Reciprocal Rank Fusion (k=60,
   samma konstant som Elasticsearch/OpenSearch/Qdrant). Förut: en enda svag
   vektorträff över tröskeln stängde fulltexten helt, även när svaret stod
   där. Ren funktion i `postgres.py::_rrf_fusion`, testad utan databas
   (`tests/storage/test_rrf_fusion.py`) — men **overifierad mot en riktig
   Postgres**, `snajp_app`-lösenordet saknas fortfarande (`snipe-lt9`). Kör
   den mot dev innan du litar på den skarpt.

2. **Flerturssökningen i chatten.** Ett kort andra meddelande ("Ja, en
   Android.") söker nu tillsammans med kundens FÖRRA replik — den bär
   ämnet, det nya meddelandet gör det oftast inte.

3. **`retention_classifier.is_cancellation_risk` läckte.** Villkoret var
   `intent >= 0.6 OR missnöje >= 0.6` — ren irritation utan
   uppsägningssignal räckte. Uppmätt skarpt: en försenad-paket-fråga
   stämplades `retention_risk` och injicerade retention-skillen i onödan.
   Nu: missnöje kan bara FÖRSTÄRKA en redan existerande signal
   (`intent >= 0.4 AND missnöje >= 0.7`), aldrig bära beslutet ensamt.

4. **Ny gissningsordsgrind** (`app/leads/gissnings_gate.py`). Overlay-regeln
   mot gissningar om mottagaren ("troligen", "brukar", "lär") visade sig
   vara en riktning — EFTER-körningen släppte igenom "lär ni få många
   frågor" trots regeln. Nu kodgrind, samma reparationscykel som
   grundningsgrinden, i alla tre utkastvägar (outreach, svar, uppföljning).

---

## Instruktionslagret — overlays, inte skills

- **Overlay-komposition**, ny mekanik i `agentcore/packs.py` +
  `step_runner.py`: `PlaybookStep.overlay` kan nu vara en `tuple`, renderas
  i deklarationsordning. Ett steg kan bära hårdreglerna OCH en
  syftesoverlay utan att duplicera text (`overlay=("leads-hard-rules",
  "leads-reply")`).
- Två nya overlays: `leads-reply.md` (erkänn invändningen först, max en
  fråga tillbaka, aldrig rabatt/priseftergift, eskalera inte uppmaningen),
  `leads-followup.md` (kort, ingen förebråelse, tillför alltid det nya,
  breakup-regler).
- `leads-hard-rules.md` fick evidensregler — inte teoretiska, ur faktiska
  utkastsvagheter i 9-augusti-körningen: gissningsord förbjudna, ämnesraden
  ska bära mottagarens EGET faktum, EN uppmaning per mejl, en referens ska
  bära sitt "varför" i samma mening.
- Temperaturparitet: leads-kedjans formuleringssteg (utkast, humanizer)
  fick 0.5/0.7, samma som supportens 25-augusti-beslut. Analys- och
  granskningssteg är fortfarande kalla. Thinking förblir AV enligt
  Antons §8.5-beslut i `docs/THINKING_MODE_COMPARISON.md` — rört ingenstans.
- `mk:customer-research` (research steg 1) fick `existing_support_channels`
  och `has_chatbot` som kontraktsfält — det var forskningens bästa
  SPONTANA fynd i Antons genomläsning (kollade om bolagen redan hade en
  chattlösning), nu obligatoriskt i stället för ett gott infall som kan
  utebli.

---

## Arkitektur hämtad utifrån (Antons uppmaning efter varv 1–2)

### Eval-harness — `app/agent/evals.py` + `scripts/kor_evals.py`

Langfuse/promptfoo/Ragas-mönstret: ett golden-set körs mot agenten,
egenskaper mäts mekaniskt (inte exakt textmatchning). Vårt golden-set är
inte påhittat — det är **de sju verkliga incidenterna** från 7–26 augusti
(betalfrågan mot seedad KB, S2-felklassningen, GDPR, hotet, tom hälsning,
osv), varje case med dokumenterat upphov i koden.

Faithfulness (svarar mejlet med vad underlaget faktiskt säger?) mäts UTAN
LLM-domare — återanvänder grundningsextraktorn från
`app/leads/grounding_gate.py` som redan finns för INV-GROUND-001.
Falsifierbart och gratis, där fältet normalt kalibrerar en domarmodell mot
mänsklig bedömning.

Skarpkört en gång: **7/7 godkända**, `docs/live-tests/evals-20260826-222210.json`.
Faller sviten (exit 1) faller CI om du vill koppla in den där — inte gjort än.

`POST /api/agent/feedback` (nedtummad körning + `corrected_output`) skapar
nu **automatiskt** ett nytt eval-case — feedback matas mekaniskt in i
golden-setet. `agent_evals`-tabellen fick sin första kodväg (stått död
sedan migration 010).

### Kundminne — migration 052, ny invariant INV-MEM-001

mem0:s ADD-only-mönster, inte Zeps temporala kunskapsgraf (fel skala för en
supportkunds handfull fakta). Supportagenten minns nu vad kunden själv
uppgett mellan ärenden — "Har en Android-telefon" i ärende 1 finns i
kontexten i ärende 2.

Extraktionen är inbakad i triagesteget (steg 1), inte ett eget LLM-anrop —
triagen läser ändå hela meddelandet. **Kontamineringsspärr**, hård regel:
minnet bär ENBART vad kunden själv sagt, aldrig agentens egna slutsatser
(sentiment, kategori, tolkningar). En agent som lagrar sina egna
tolkningar och matar tillbaka dem blir självförstärkande — en felläsning
i ärende 1 blir "fakta" i ärende 2. Injiceras alltid genom
`wrap_untrusted_content(source="customer:memory")` i user-position,
aldrig systemprompten — kundhärledd text är kundskriven text
(INV-SEC-009-gränsen).

Testat med en instruktionsattack sparad som "fakta"
(`test_minnesblocket_ar_opalitligt_wrappat`): bevisar att den bara når
prompten inkapslad i sin wrap.

### Avvisat, med motivering (så du inte återuppfinner samma utvärdering)

- **Zep-graf** — fel skala, en supportkunds fakta är en handfull rader.
- **LLM-domare i evalen** — kalibreringsbörda, kostar per körning; husets
  grundningsextraktor gör samma jobb gratis och deterministiskt.
- **A/B-varianttracking** — blockerad av samma rot som weakest_lever:
  `offers`-rader skrivs aldrig av någon kodväg.

---

## Mätt, inte påstått

Fyra skarpa livekörningar mot riktig DeepSeek (MemoryStorage, samma
sanktionerade väg som `run_live_tests.py` alltid använt) plus
eval-körningen. Allt i `docs/live-tests/`. Jämförelseskript:
`scripts/jamfor_livekorningar.py support FORE.json EFTER.json`.

En riktig förbättring, mätt: S2 (irriterad leveransfråga) eskalerade den
7:e med "vi har ingen information" trots seedad KB. Efter allt ovan svarar
den själv med en KB-grundad handlingsplan, ingen felaktig retention-etikett.
Leads-utkastens ämnesrader gick från "supportagenten"/"returfrågor" (vår
egen kategori) till "Fri retur — och frågorna den skapar" (mottagarens
eget faktum). Fullständiga citat och skärmdumpar i artifakten länkad högst
upp.

**1445 backendtester gröna** (1338 innan), **333 rotvaktposter**, 22
skill-steg verifierat kompletta.

---

## Öppna trådar

1. **RRF-fusionen är overifierad mot riktig Postgres** — `snajp_app`-
   lösenordet saknas (`snipe-lt9`). Testad ren utan databas, men den
   skarpa SQL-vägen (`_sok_vektor`/`_sok_fulltext`) har inte körts på
   riktigt sedan ändringen.
2. **Svarshanteringen och uppföljningsgeneratorn är nya kodvägar mot en
   databas som aldrig sett dem.** MemoryStorage-testad, `--skarp`-
   verifierad för instruktionslagren, men INTE körd end-to-end mot
   Postgres. Kör en riktig svarskörning i dev innan du litar på den i
   `main`.
3. **Adminytan är inte pixelverifierad inloggad** (§3 ovan).
4. **`snipe-xl9`** (mejlpipeline-routing av prospektsvar till
   `hantera_prospektsvar`): blockerad av att själva utskicksvägen
   fortfarande är en stub (`snipe-ork`, LoggingSendProvider). Ingen
   riktig SMTP → inga riktiga svar att routa än.
5. **`snipe-a6i`**: pg_trgm-kandidat för sammansatta ord och stavfel i
   svensk fulltext — inte påbörjad, bara scoped.

## Snabbkontroll när du har tid

```bash
cd snajp-support && python -m pytest tests/ -q          # 1445 gröna, 4 skippade
cd .. && python -m pytest tests/ -q                     # 333 gröna (rotvaktposter)
python scripts/run_live_tests.py --skill-audit           # 22 steg, inga trasiga referenser
python scripts/verifiera_instruktioner.py --skarp        # instruktionslagret, riktig modell
python scripts/kor_evals.py                              # golden-setet, riktig modell
```
