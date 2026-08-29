# Handoff: Redis-arkitekturen + Fas 1–7-planen implementerad

Skriven 2026-08-29 (natt→morgon) av Claude på Antons uppdrag, till Sebbe.
Motpart till dina två handoffs (`HANDOFF-2026-08-27-GRANSKNING.md`,
`HANDOFF-2026-08-29-KUNDER-DATA.md`) — båda lästa i sin helhet innan något
byggdes, liksom hela sjufasplanen och koden den pekar på.

**Status: byggt, testat och pushat till `development`.**
Backendsviten **1586 passed** (från 1505 vid sessionsstart — 101 nya tester),
rotvakterna **362 passed** (från 342), `tsc` rent. Migration **054+055
applicerade i development FÖRE pushen** (din 053-regel följd). **`main` är
INTE rörd** — §8.1a-spärren gäller oförändrat, och den här sessionen har
dessutom gjort den dokumenterade main-kedjan omöjlig att köra av misstag
(se Fas 7 nedan).

Arkitekturreferens: [plans/2026-08-29-redis-agentarkitektur.md](plans/2026-08-29-redis-agentarkitektur.md)
— läs den för HELA resonemanget (Redis Iris-produktdomarna, avvisade
alternativ, gates). Det här dokumentet är vad du behöver för att röra koden.

---

## 1. Kartan: vad som byggdes, i vilka filer

### Fas R1 — chattkörningar överlever en deploy (kärnan)

Problemet du själv dokumenterade i requirements-kommentaren ("tappar varje
pågående chattjobb vid nästa deploy") är stängt på riktigt:

* `app/jobs/stream.py` (NY) — `ChattStrom`: XADD till `crm:jobb:chatt`,
  consumer group `agenter`, XREADGROUP-workers, XAUTOCLAIM-återtag (min-idle
  60 s) både vid uppstart och löpande per varv. OBS kommentaren om
  fakeredis cursor-beteendet i `atertag` — den är lastbärande, ta inte bort
  loopvillkorets andra ben.
* `app/api/chat.py` — endpointen XADD:ar när `app.state.chattstrom` finns;
  annars EXAKT gamla `create_task`-vägen (paritetsvägen som befintliga
  sviten bevisar). `hantera_strom_jobb` är workerns hanterare: läser
  jobbposten först, **completed ⇒ bara kvittera** (fönstret mellan
  `jobs.complete()` och XACK), annars kör — med `aterta` när posten redan
  bär ticket_id.
* `app/agent/support_agent.py` — `run_support_agent` fick `aterta` +
  `vid_arende` (callback när ärendet skapats). Idempotensinvarianten
  **INV-JOB-001**: *en avbruten körning fullföljs och lämnar exakt ETT
  ärende och EN inbound-rad* — testad genom den riktiga hanteraren med en
  krasch injicerad EFTER create_ticket (`tests/invariants/test_inv_job_001.py`).
* `app/jobs/store.py` — `annotate()` på båda storarna; `get()` släpper
  igenom extra fält (ticket_id/conversation_id) men ALDRIG `created`
  (timeout-klockan). Klockan flyttas bara vid återtag.
* `app/config.py` — `chat_workers=2` (= max samtidiga LLM-kedjor per
  process; taket är KVOTDISCIPLIN, inte prestanda).

### Fas R2 — semantisk svarscache + embeddingcache

* `app/cache/svarscache.py` (NY) — grinden, lookup/store, Memory+Redis-par.
  **INV-CACHE-001**: en cachad replik är en ren funktion av (tenant, fråga,
  KB-version, konfigversion). Grinden kräver SAMTIDIGT: tom historik, inga
  bilagor, tomt kundminne, ingen personnummerträff — och `abuse.ska_eskalera`
  stänger grinden helt. STORE dessutom bara icke-eskalerat +
  `CACHEBARA_KATEGORIER` (aldrig betalning/retur_reklamation/ovrigt —
  motiveringen står i moduldocstringen, läs den innan du ändrar mängden).
* `app/cache/embeddingcache.py` (NY) — sha256(text)→float32-packad vektor,
  TTL 30 d, krokad i `embed_text`. Sparar både Gemini-kvot och latens på
  varje upprepad KB-sökfråga.
* `app/cache/versioner.py` (NY) — kb/config-versionsräknare; bumpas i
  `POST /api/kb` och profil-/instruktionsskrivvägarna. En KB-ändring gör
  alla gamla cacheposter omatchbara utan någon delete.
* Lägen: `SEMANTIC_CACHE=off|shadow|on`, **default off i kod**. `shadow`
  loggar skulle-ha-träffat till `platform_events` (hash-prefix + likhet,
  aldrig frågetexten) utan att servera — mätperioden före `on`.
  `scripts/kor_evals.py` tvingar alltid off (evals mäter modellen).
* En cacheträff i `on` bokförs som en `agent_runs`-rad med
  `step_log=[{"step":"svarscache",...}]` och `model="svarscache"` — och
  `rate_limit_db.record` räknar numera bara steg med `"skill"`-nyckeln, så
  träffen inte debiteras som LLM-anrop.

**Liveverifierad mot dev-databasens riktiga Query Engine** — och den
verifieringen fångade en äkta bugg som sviten ALDRIG kunnat se: RediSearch
kräver escapade specialtecken i TAG-frågor, och varje riktigt tenant-id är
ett UUID med bindestreck. Oescapat gav `Syntax error at offset 18` på varje
produktionsanrop — tyst, bakom graceful-fallbacken, för evigt. Fixad
(`RedisSvarscache._tag`), enhetstestad, och den efterföljande livekörningen
gav träff med likhet 0,9992 på UUID-tenant + korrekt MISS för annan
tenant/ortogonal vektor/bumpad version. fakeredis kan inte köra `FT.*` —
**paritetsimplementationen bär logiken i sviten, liveverifiering krävs för
varje ändring i RedisSvarscache.**

### Fas R3 — arbetsminne (rullande samtalssummering)

* `app/minne/arbetsminne.py` (NY) — per (tenant, kund): summering +
  täckta_turer, TTL 72 h förnyad vid läs OCH skriv, Memory+Redis-par.
* `_render_conversation` visar `summering + de 8 senaste turerna` när
  samtalet passerat 12 turer och en summering finns — annars EXAKT dagens
  3-ärenden/8-turer-beteende. Summeringen är ALLTID
  `wrap_untrusted_content(source="customer:samtalssummering")` i
  user-position (INV-SEC-009 orörd).
* Uppdateringen är fire-and-forget (`asyncio.create_task` efter svaret) —
  en förlorad summering är rekonstruerbar ur Postgres, kunden väntar aldrig
  på den. Summeringsprompten bär **kontamineringsspärren** ordagrant nära
  migration 052: bara vad kunden uppgett och vad som utlovats — aldrig
  sentiment/bedömningar. **INV-MEM-002** registrerad + regressionstestad.

### Fas R4 — leads-batchen på strömmen

`ChattStrom` parametriserades (`stream_key`/`group`, chattens värden som
default — inga befintliga anropare ändrade). `POST /api/leads/runs/batch`
XADD:ar per-prospekt-jobb till `crm:jobb:leads`; `hantera_leads_jobb` har
samma completed-vakt. `leads_workers=1` (åtta LLM-anrop per jobb —
kvotdisciplin). En halvkörd 50-batch fortsätter nu efter en deploy i stället
för att tyst försvinna.

### Fas R0 — hygien/GDPR (och det som är Antons hand)

* `scripts/redis_kontroll.py` (NY) — region+TLS per databas via konto-API:t,
  **fäller vid icke-EU**. Körd live: `Snajp-Chat-Data` ligger i **GCP
  europe-west1 (EU ✅)** men **TLS är AV** — jobbposterna (som bär riktiga
  kundsvar) går i klartext.
* `scripts/redis_tls_pa.py` (NY) — slår på TLS via API:t OCH byter
  `REDIS_URL` till `rediss://` i ett svep (stegen är ETT byte). Agentens
  eget försök stoppades korrekt av auto-läge-klassificeraren → **Anton kör**
  `python scripts/redis_tls_pa.py --apply`.
* `scripts/redis_provisionera.py` (NY, SPÄRRAD §8.1a) — mains EGNA databas
  den dagen cutovern kommer: `--planer` listar priser (rätt val 2026-08-29:
  Single-Zone_Persistence_250MB, id 21437, 10 USD/mån — enda 250-nivån med
  BÅDE persistens och replikering), `--skapa` kräver en explicit spärrflagga.
* Redis Cloud + Resend är nu **underbiträden i juridikkedjan**:
  `docs/JURIDIK_ATGARDER.md` P1.2 (åtgärdslistan), `docs/registerforteckning.md`,
  `lib/bolag.ts` (platshållarregioner håller varningsrutan uppe tills
  verifierat/DPA-tecknat).

### Fas 1 — ytorna skarpa

Gemini-gren i `valjModell()` (`app/api/email-studio/route.ts`, ordning
OpenAI→Gemini→DeepSeek-lokalt, `MODEL`-variabeln delad med backenden),
explicit `simulated: false` i skarpa svar, den diskreta
"Exempeltext, ingen modell kördes."-raden (mineral, ingen ruta — ersätter
ochre-boxen), Exempel-märken i Bolagsregister/Bolagssida (samma
kicker/mineral som statusorden). **1.2 är Antons kommando:**
`python scripts/gemini_web_konfig.py --apply` (klassificeraren stoppade
agentens variabelskrivning — och OBS: Railway kör fortfarande GAMLA
Gemini-nyckeln, se §4).

### Fas 2 — testisolering

Migration **054**: `prospects.origin` +`'test'` (NOT VALID+VALIDATE, per
039:s egen varning). **Premissen i planen var fel** — batchflödet skapar
inga prospekt alls; den verkliga läckan var `POST /leads/prospects` från
LeadsRunForms "Egna bolag", som nu tar `?is_test=true` (query-param — ett
body-fält hade tyst brutit alla anropare) och frontendens `kör()` skickar
den. Send-guardens spärr noll blockerar nu `origin in ('example','test')`.
**2.5**: `ChatRequest.is_test` finns äntligen — trådad genom strömmen till
`agent_runs`, och adminytans Testkörningar-flik skickar den (dess egen
beskrivning lovade det i veckor utan att fältet existerade).

### Fas 3 — befordra prospekt

`POST /api/leads/prospects/{id}/befordra` — validering FÖRST för
test/example (Luhn-orgnr via befintliga `orgnr.py`, ingen
.example/.invalid/.test-domän, riktig e-post; 422 med fältlista), idempotent
200 för redan-manuella. Delad validering i `app/leads/befordran.py` — EN
plats, används även av `konvertera_testkund.py --prospekt <ids>` (kopiering
demo→riktigt konto med torrkörning, foretagsnyckel-krockkontroll mot
90-dagarskarensen, och uttalat val att agent_runs-historiken INTE följer
med). UI: kryssrutor + "Flytta över valda" + per-bolag-utfall i
Bolagsregister, plus 2.4-filtret ("Visa testkörningar (N)" — test döljs
default, exempel döljs ALDRIG).

### Fas 4 — Email-studion in i leaden

Menyposten borta (`preview: true` i routes.ts — routen nås fortfarande
direkt), Bolagssidan äger flödet: "Skapa utkast" → riktiga
`POST /api/leads/outreach/draft` → `<EmailStudioEditor compact />` inline
med leadens verkliga kontext → "Godkänn och skicka" →
`POST /api/leads/queue/{id}/approve` → autonomiuppföljningen (PUT
/api/leads/config; auto_send provas reaktivt och visar backendens
hindertext vid 422). `LeadsControls` auto_send-buggen (snipe-b2g) lagad.
Läsvägen efter omladdning: NY `GET /api/leads/prospects/{id}/utkast`
(returnerar senaste utkastet + `queue_item_id` — **kö-id ≠ meddelande-id**,
de är send_queue resp. outreach_messages länkade via thread_id, jag gick
själv i den fällan innan testet avslöjade det).

### Fas 5 — Testchatt

Flik bredvid Kundtjänst (`SupportWorkspaceTabs`), SupportChat i `testMode`
mot INLOGGAD tenant via nya `app/api/snajp-support/testchatt/*`-proxyroutes
— de gamla chat/jobs-routerna är ANONYMA med flit (INV-SEC-010) och löser
tenant ur en klient-slug; testchatten går via `proxyAsTenant` (sessionen).
Feedback (tummar + rättningsruta → `POST /api/agent/feedback` — endpointen
hade legat anropslös), `run_id` returneras nu ur körningen (6.2, även för
cacheträffar). Textfiler → förhandsvisning → "Lägg till i kunskapsbasen"
(människans klick = godkännandet, INV-LEARN-001). PDF via NY
`POST /api/kb/extrahera` (pypdf, ren beräkning, skriver inget, varnar för
tomt/glest textlager) + synlig förhandsvisning — Kunskapsbas-filens egen
invändning besvarad, inte kringgången. Agentförslag renderas i chatten med
godkänn/avfärda mot befintliga förslagsvägar. **INV-SEC-012** (ny):
KB-artikeltext når aldrig systemposition — injektionstestad genom riktiga
kedjan. R1.5: widgetens polling tål 5xx med backoff (deploy-fönstret).

### Fas 6 — jämförelseluckan + rundorna

Migration **055**: `agent_runs.model` — alla sju loggpunkter skickar
`provider:modell` (cacheträffen "svarscache"). Rundorna: se §3.

### Fas 7 — förberedelsen (deploydelen förblir SPÄRRAD)

`railway_provision.py` skriver LLM_PROVIDER/MODEL **bara på osatta fält**
(snipe-u70 stängd — samma predikat som keys.py-fixen), `DEPLOY.md`s
main-avsnitt omskrivet med varningsruta + den verifierade merge-ordningen,
de döda workflows (`deploy-production.yml`, `deploy-development.yml`)
**borttagna** (falska gröna signaler mot död stack), `verify.yml` triggar
inte längre på döda `railway-development`, `CLAUDE.md`s farliga
tvåstegskedja ersatt med varningen, klartextlösenordet i `EMAIL_STUDIO.md`
borttaget (**värdet är komprometterat i git-historiken — rotera kontot**,
snipe-8wy). **CNAME-fällan hittad:** `loopia_dns.py --apply` hade pekat
www.snajp.se på en Railway-host som svarar **404** (domänen är inte
registrerad på tjänsten, och DEN registreringen är ett main-skrivande =
spärrat). CNAME:n är alltså en del av cutover-paketet, INTE en fristående
förberedelse — applicera den inte ensam.

---

## 2. Nya invarianter (alla registrerade + testade)

| Id | Påstående | Test |
|---|---|---|
| INV-JOB-001 | En avbruten chattkörning fullföljs idempotent — exakt ett ärende, en inbound-rad, aldrig dubbelkörd efter complete | `snajp-support/tests/invariants/test_inv_job_001.py` |
| INV-CACHE-001 | En cachad replik är en ren funktion av (tenant, fråga, kb-version, konfigversion) — aldrig PII/minne/samtal/eskalering | `snajp-support/tests/invariants/test_inv_cache_001.py` |
| INV-MEM-002 | Samtalssummeringen bär bara kundens uppgifter + löften till kunden, alltid wrappad, aldrig instruktionsposition | `snajp-support/tests/test_arbetsminne.py` |
| INV-SEC-012 | KB-artikeltext når aldrig systemposition | `tests/invariants/test_inv_sec_012.py` |

## 3. Verifierat, och hur

* **Sviterna:** backend 1586/0, rotvakter 362/0, tsc 0 fel — på slutträdet.
* **Migrationer:** 054+055 applicerade mot development och verifierade `=`
  i liggaren FÖRE pushen.
* **Redis live:** svarscachens FT-kedja mot dev-databasens riktiga Query
  Engine (träff 0,9992 / korrekta missar — och TAG-escape-buggen hittad+fixad
  där, se §1/R2). Embeddingcachens binära roundtrip live. Regionen
  EU-verifierad via konto-API:t.
* **Fas 6, DeepSeek (lokalt, MemoryStorage, syntetisk data):**
  `run_live_tests.py --support` **10/10 scenarier** korrekt beteende (5
  disabled-läge + 5 enabled-läge; eskaleringarna träffar rätt, skillarna
  injiceras kompletta 11/11). `kor_evals.py`: **alla 7 golden-fall godkända**
  (körda i flera varv; se ärlighetsnoten nedan). Rapporter i
  `docs/live-tests/`.
* **Ärlighetsnot om flaken, med rotorsak:** enstaka `APITimeoutError` föll
  slumpmässigt olika fall i olika varv (fyra körningar, fyra olika offer —
  varje fall grönt i övriga varv). Diagnos: dev-MASKINENS DNS mätte 15 s för
  en färsk uppslagning samma natt, och klientens connect-timeout är 5 s —
  anropen dog på anslutning, inte på svar. Miljöflake på Windows-maskinen,
  inte kod och inte leverantörskvalitet; Railway-containern delar inte
  problemet. Bifynd i samma spår: lokala globala Python kör openai 2.53
  medan requirements pinnar >=3.3,<4 — exakt den versionsdrift
  requirements-kommentaren varnar för; sviterna kör grönt på båda, men
  skarp lokal felsökning bör ske i en venv på den pinnade versionen. Plus EN äkta
  nondeterministisk faithfulness-fällning (superlativ i retention-svaret, 1
  av 3 varv) — det är precis vad grindarna finns för att fånga, och värt
  att titta på i overlay:n om den återkommer. Ingen av fällningarna är en
  regression från den här sessionens kod (cache är AV i evals).
* **Fas 6, Gemini: BLOCKERAD av B1 — mätt, inte antagen.** Se §4.
* **Visuellt (lokalt, demo-ytorna):** Bolagsregistrets Exempel-märken och
  simulerad-raden i Email-studion granskade i renderade pixlar + computed
  style (mineral-token, ingen ruta). Inloggade ytor granskade mot live-dev
  efter deployen — se §5.

## 4. B1/Gemini — statusen är VÄRRE än "okopplat projekt", nu med mätdata

1. **Railway (BÅDA miljöerna) kör fortfarande den GAMLA nyckeln** (svans
   `…A2Mw`, verifierat via variabelläsning) — Antons nya nyckel (`…Idfg`)
   finns bara i lokala `.env`. Gratisnivåns 20/dygn gäller alltså driften
   precis som förut.
2. **Den nya nyckeln är produktionsoduglig som den är:** uppmätt
   ~**170 sekunder per anrop**, konsekvent över 9 anrop (200 OK, inga 429,
   `completion_tokens: 0` vid små token-tak). Det är en strypt kö hos
   Google — projektet är sannolikt fortfarande inte fakturerings-kopplat,
   eller Express-läget köar. **12 Gemini-rundor ≈ 4 timmar och hade ändå
   slagit i dygnstak** — därför kördes Fas 6:s Gemini-halva inte alls, med
   detta som dokumenterat skäl i stället för en gissning.
3. Vägen ur: Anton verifierar i Google-konsolen att nyckelns projekt är
   kopplat till faktureringskontot (plan §1.1), mäter om
   (`gemini_burst`-mönstret: åtta snabba anrop, quotaId i felsvaret är
   facit), och rullar först DÄREFTER ut nyckeln (`scripts/keys.py` +
   variabelbytet — klassificeraren kräver Antons hand för själva
   Railway-skrivningen).

## 5. Live-läget i development efter deployen (verifierat, inte antaget)

Uppstartsloggen för deployen (05:52 UTC, `0512ab3`):

```
Lagring: Postgres (Supabase)
Jobbkö: Redis
Semantisk svarscache: Redis (embeddingcache + svarscache + versioner + arbetsminne).
Chattström: Redis-baserad jobbkö aktiv (0 poster återtagna vid uppstart, 2 workers).
Leadsström: Redis-baserad jobbkö aktiv (0 poster återtagna vid uppstart, 1 workers).
```

* **`qa_vyer.mjs` mot live dev: GRÖNT, inga avvikelser** — anonym får 404 på
  adminytan, kund ser inte admin, admin når alla 17 vyer. Skärmbilderna
  granskade för hand: Testchatt-fliken ligger bredvid Kundtjänst med korrekt
  ochre-markering, Email-studioposten är borta ur kundmenyn (nås direkt via
  URL), Bolagsregistret bär Exempel-märken + kryssrutor, dina två "E2E
  Verifiering AB"-rader är korrekt omärkta (origin='manual' — och numera
  städbara via befordra/filter).
* **Migrationsliggaren:** 054+055 står som `=` i development.
* **Chatt-E2E genom strömmen:** ett riktigt meddelande via publika demon
  gick 202 → ström → worker → körning. Körningen FÖLL — på
  `openai.RateLimitError: 429 exceeded your current quota` i triagesteget,
  dvs. GEMINIS DYGNSKVOT på den gamla nyckeln (snipe-a1c/B1), inte på någon
  ny kodväg. Kunden fick det avsedda, vänliga felmeddelandet. Kedjans
  mekanik är alltså bevisad hela vägen; själva SVARET är kvotgrindat tills
  B1 är löst — samma vägg som stoppade Fas 6:s Gemini-rundor.
* `SEMANTIC_CACHE=shadow` är satt på development/api (icke-hemlig variabel —
  klassificeraren släppte den) — mörkstartens mätning börjar rulla med
  nästa deploy; träffkvoten läses i Händelser (source `cache:svarscache`).

## 6. Antons kommandolista (allt förberett, klassificeraren kräver din hand)

```bash
python scripts/redis_tls_pa.py --apply        # TLS på + rediss:// i ett svep
python scripts/gemini_web_konfig.py --apply   # GEMINI_API_KEY till web/dev (Fas 1.2)
python scripts/redis_kontroll.py              # verifiera EU+TLS efteråt
```

Plus: Redis DPA i Redis Cloud-kontot (Account → Legal), B1-konsolsteget
(§4.3), rotera EMAIL_STUDIO-testkontots lösenord (snipe-8wy), och — när du
vill börja mäta cachen — sätt `SEMANTIC_CACHE=shadow` på `development/api`.

## 7. Medvetna val och öppna seams (inte glömda — valda)

* **Redigerat innehåll persisteras inte från studion till
  outreach_messages** (queue-approve tar inga edits): fria redigeringar
  EFTER grundningsgrinden hade försvagat grinden — beslutet är att
  godkännandet skickar det grindade utkastet, och UI:t säger det ärligt.
  Vill ni ha redigering: bygg den FÖRE grinden (re-gate på edit), inte förbi.
* **KB-artikeltext wrappas inte som untrusted** i `_kb_block` (SOUL och
  affärskontext wrappas). Positionsgarantin håller (INV-SEC-012 bevisar),
  men wrappen vore konsekvent — ligger som förberedd bakgrundsuppgift hos
  Anton (chip "Wrap KB article text as untrusted content").
* **`GET /api/leads/config` exponerar inte auto_send-verdiktet** — UI:t
  provar PUT:en och visar backendens hindertext reaktivt. Räcker; ett
  `auto_send: {tillaten, hinder}`-fält på GET:en är en trevlig framtida rad.
* **Managed Iris (Agent Memory/LangCache) är INTE inkopplade** — åtta gates
  i `docs/REDIS_IRIS_EVAL.md` (preview-status, DPA, EU-region, BYOK,
  INV-MEM-001-kompatibel extraktion m.m.); sandbox-protokollet är skrivet
  och väntar bara på kontostegen. Development bär riktig kunddata — ingen
  "testkoppling" dit, någonsin.
* **Fas 7:s deploydel + R5 (mains Redis) förblir spärrade** tills Anton
  säger cutover. Allt är förberett: merge-ordningen i DEPLOY.md,
  provisioneringsskriptet, TLS-mönstret.

## 8. Det som inte flyttade sig

Din SMTP/Resend-kedja är orörd (och `/health/ready` visar sändvägen frisk —
varningen borta). Kunder & Data orörd. `main` orörd. Gemini-kvotfrågan
(snipe-a1c, P0) är fortfarande Antons beslut — nu med skarpare mätdata (§4).
