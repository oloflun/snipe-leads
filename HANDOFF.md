# Handoff — agent-backend på DeepSeek v4 Flash

**Datum:** 2026-08-07 · **Gren:** `snajp-redesign` · **Inget är committat** —
allt ligger i arbetskopian för granskning.

Detta dokument är skrivet för att en annan agent ska kunna ta över utan att
läsa hela chatthistoriken. Läs det uppifrån och ned innan du rör något.

---

## 1. Vad som byggs och varför

Ursprungsplanen ligger i två filer och **måste läsas först**:

| Fil | Vad |
| --- | --- |
| `plans/2026-08-07-agent-backend-deepseek.md` | Statussammanfattning (96 rader) |
| `C:\Users\Anton L\.claude\plans\hej-f-rfina-denna-plan-dreamy-yao.md` | **Den fullständiga planen (825 rader)** — Del A–L, all motivering, alla beslut |

Kort: ersätt supportagentens handskrivna prompt och leads-stubbarna med en
riktig, versionerad agentbackend på `deepseek-v4-flash`, byggd genom att
vendora och kedja skills från `coreyhaines31/marketingskills` (`mk:`) och
`anthropics/knowledge-work-plugins` (`cs:`, `sa:`), med per-kund-konfiguration,
hårdkodade säkerhetsgrindar och CI-tvingade invarianter.

**Styrande princip från planen:** kvalitet före kvantitet. Inga massutskick.
Agenten är första intrycket i en kundrelation och arbetar i andra företags namn.

---

## 2. Nuvarande läge — ärligt

### Det som är byggt OCH verifierat

| Område | Bevis |
| --- | --- |
| CI-grind (`verify.yml`) + `ARCHITECTURE_INVARIANTS.md` + `waivers.yml` | `tests/invariants/` — metatest faller om en aktiv invariant saknar test |
| `snajp_app`-roll utan BYPASSRLS (INV-SEC-001) | Verifierat live mot produktion: som `snajp_app` scopad till fel tenant gav direkt id-läsning **0 rader** (transaktion rullades tillbaka) |
| Vendorat skill-register, 414 filer, 4 namnrymder, sha256-manifest | `agent-core/manifest.json`, `tests/agentcore/test_registry.py` |
| **Skill-integritet: varje oskopad skill laddas KOMPLETT (SKILL.md + alla references)** | `python scripts/run_live_tests.py --skill-audit` — `mk:offers` 69 574 tecken/7 refs, `mk:prospecting` 51 779/5 refs, alla `renders_complete: true` |
| Per-steg-orkestrering: **ett LLM-anrop per skill** | `app/agent/step_runner.py`, `tests/agent/test_support_agent_wiring.py` |
| Migrationer 009–015 (roll, 14 tabeller, demo-tenant, Snajp-tenant, segmentaggregat, subject-kolumn, step_log) | Alla applicerade live mot Supabase |
| Språk-/tidsgrindar med fryst klocka | `tests/leads/test_{language,timing}_gate.py` |
| Proveniensgrind INV-DATA-002 | `tests/leads/test_provenance_gate.py` + API-spärr i `app/api/leads.py` |
| Segmentaggregat ≥3 kunder (G11) | `tests/leads/test_segment_aggregate.py`, SQL-funktion med `HAVING` |
| Efterhandstrigger av onboarding | `app/leads/onboarding_state.py`, `tests/leads/test_onboarding_state.py` |
| G10 revisionslogg med `step_log` per skill-anrop | `agent_runs`, exponerad via `GET /api/leads/runs` |

**240 tester gröna, 1 skippad (kräver DATABASE_URL), `npm run type-check` ren.**

### Det som är byggt men ALDRIG ANROPAS (dött)

Detta är den viktigaste ärligheten i dokumentet. Följande finns, är
enhetstestat, men ingen live-kodväg rör det:

| Modul | Status |
| --- | --- |
| `agentcore/evals.decide_promotion` | Evalgrinden (INV-AGENT-002) anropas inte av något |
| `agentcore/layers.ComposedRun` / `pinned_pack_version` | Hela skiktmodellen (Del B) används inte i drift; `agent_configs.pinned_pack_version` läses aldrig |
| `leads/follow_up.build_follow_up_sequence` | Del H:s värdespaks-rotation anropas inte |
| `leads/handoff.route_handoff` / `render_call_prep_instructions` | Fas E anropas inte |
| `offers` / `ab_variants` / `ab_results` | Tabellerna skrivs aldrig till |
| `supabase/functions/discover-leads` + `generate-outreach` | **Fortfarande orörda stubbar, 29+25 rader** — planen sa att de skulle ersättas |

### Det som INTE är byggt

- Email-Studio-integration (utkast hamnar i `outreach_messages`, inte i Email Studios `ss_drafts`)
- Dashboard-UI för research (API:t `GET /api/leads/runs` finns, ingen vy)
- SMTP-utskick (`LoggingSendProvider` loggar i stället för att skicka — medvetet)

---

## 3. Miljö och nycklar

```bash
python "C:\Users\Anton L\snipe-leads\scripts\keys.py"          # sätt
python "C:\Users\Anton L\snipe-leads\scripts\keys.py" --check  # verifiera
```

Fungerar från vilken katalog som helst. Se `DEPLOY_KEYS.md`.

| Nyckel | Krävs | Status 2026-08-07 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | **Ja** | SATT |
| `SCRAPEGRAPHAI_API_KEY` | Fas B | SATT |
| `GEMINI_API_KEY` | Vision + embeddings | **SATT** (senare i sessionen) |
| `DATABASE_URL` | Riktig pgvector-sökning (se Steg 0) | **Saknas.** `snajp_app`-rollen finns live (INV-SEC-001), men dess lösenord är ALDRIG satt — `execute_sql` blockerades av miljöns auto-mode-klassificerare när jag försökte. Antingen kör `alter role snajp_app with password '...';` själv i Supabase SQL-editorn och bygg `DATABASE_URL` från det, eller bevilja `execute_sql`-behörighet så nästa agent kan göra det. |

**Nycklar hör ALDRIG hemma i databasen** (INV-SEC-006 / plan G5). Frågan har
ställts och besvarats — det är cirkulärt (tjänsten behöver ändå en
Supabase-nyckel i env) och bryter mot vår egen invariant.

**Fallgrop som redan kostat en körning:** `Settings.model_config` använde
`env_file=".env"` (relativ sökväg → löses mot `cwd`). Alla live-anrop föll på
"Missing credentials" så fort något kördes från repo-roten. Nu absolut sökväg
i `app/config.py`. Ändra inte tillbaka.

---

## 4. Thinking mode — BESLUTAT för support, TESTAS för leads

DeepSeek v4 kör thinking som default. Toggeln är verifierad empiriskt mot
API:t:

```python
extra_body={"thinking": {"type": "disabled"}}   # av — inga reasoning_tokens
reasoning_effort="none"                          # OpenAI-kompatibelt alias, samma effekt
```

Mekanismen är nu **per steg**, inte bara global: `PlaybookStep.thinking:
str | None` (`app/agentcore/packs.py`) override:ar `settings.thinking_mode`
när den är satt. `app/agent/step_runner.py` läser `step.thinking if step.thinking
is not None else settings.thinking_mode`. Loggas per steg i `agent_runs.step_log`
(`thinking_mode`-fältet).

### Support — BESLUTAT 2026-08-07

**Global default: `disabled`** (`app/config.py`). **Undantag:**
`cs:customer-escalation` kör med `thinking="enabled"`
(`app/agent/support_playbook.py`) — det enda steget som avgör "ska det här
till en människa?". Motivering från användaren: livechatt har tidspress, så
snabb respons prioriteras överallt UTOM i just den bedömningen, där en
felaktig eskalering (åt endera hållet) är dyrare än den extra latensen.

Grunddata: `docs/THINKING_MODE_COMPARISON.md` §1 (kostnad, giltig) och §2
(kvalitet, **kör om mot PostgresStorage** — se Steg 0 nedan för varför).

**ÖPPEN FRÅGA, inte avgjord:** ska `snajp:retention-conversation`
(triggas vid uppsägningsrisk, som alltid leder till eskalering) också ha
`thinking="enabled"`? Användaren sa uttryckligen "vid eskalering" om
bedömningssteget — fråga innan du ändrar detta.

### Leads (research + outreach) — BESLUTAT 2026-08-10: thinking AV, helt

**Beslutet är fattat och verkställt i kod. Ändra det inte utan att prata
med användaren.**

Varje steg i `app/leads/{onboarding,research,outreach}_playbook.py` sätter
explicit `thinking="disabled"` via `research_playbook.THINKING`. Det ärvs
medvetet INTE från `settings.thinking_mode` — supportbeslutet ger samma
värde i dag, och ett leadsbeslut som tyst hänger på ett supportbeslut
flyttar med när supportbeslutet ändras. Låst av två tester i
`tests/agent/test_leads_agent_wiring.py`.

**Grunden:** 72 skarpa anrop (3 bolag × 2 lägen × 12 steg). Rådata
`docs/LEADS_THINKING_COMPARISON.md`, analys `THINKING_MODE_COMPARISON.md` §8.

Användaren läste igenom materialet och underkände min rekommendation, som
var PÅ. **Läs §8.5 innan du rör det här** — den beskriver varför jag hade
fel, och felet är lärorikt: jag drog slutsatser ur mätvärden (brutna
utdatakontrakt, differentierade konfidenssiffror, skeptiskare ICP-bedömning)
och läste dem som kvalitet. Användaren läste vad modellen faktiskt
producerade. Kort:

- Utkasten är **bättre** med AV — personligare, rätt ton, tillräcklig
  kontext. PÅ blev hackigt och robotaktigt trots övertänkandet.
- AV hade **rätt** om att B2C passar supportprodukten. PÅ:s underkännande
  av alla tre var inte skärpa utan pessimism — precis vad §8.3 varnade för.
- AV:s research var genuint bra: kollade om bolagen redan hade chatbot,
  hittade en öppning via Instagram, förberedde rimliga invändningar.

### Finjustering via TILLÄGGSINSTRUKTIONER — BYGGT 2026-08-14

**HÅRD REGEL: vi går inte in och ändrar i skillsen.** Regeln är oförändrad,
men den har numera en anvisad plats i stället för att bara vara ett förbud:

| Vill du ändra | Ändra då | Kräver |
| --- | --- | --- |
| en säkerhets-/sanningsregel för ALLA kunder | `agent-core/AGENTS.md` | PR |
| hur ett visst steg formulerar sig | `agent-core/overlays/<namn>.md` + `PlaybookStep(overlay=...)` | PR |
| en enskild kunds röst och ton | kundens SOUL-dokument (`/settings/soul`) | inget, kunden äger den |
| en vendorad metodik | `scripts/unlock_skills.py --rebuild-manifest` | `SNAJP_SKILL_UNLOCK_KEY` + `VENDOR-BUMP:`-trailer |

`agent-core/AGENTS.md` är **opinnad** — den slår igenom hos alla direkt. Därför
bara policy där, aldrig ton. Kryper tuning in dit finns en väg att ändra varje
kunds agent utan pin och utan godkännande.

`pack_version` bär nu tre hashar (`manifest+overlay+global`), så en körning går
att reproducera trots att två av lagren är fritt redigerbara (INV-AUDIT-001).

**`python agent-core/build_manifest.py` kräver numera nyckeln** och hänvisar
till `scripts/unlock_skills.py`, som visar diffen och kräver bekräftelse.

Regeln är mekanisk sedan 2026-08-10: **INV-SKILL-005**
(`tests/invariants/test_inv_skill_005.py`) jämför varje fil under
`agent-core/skills/` mot sitt sha256 i manifestet och fäller på tyst
redigering, tillagd eller borttagen fil. Verifierat att den faktiskt fäller.

Vad som ska utvärderas härnäst — se §8.6 för resonemanget:
1. `sa:draft-outreach` + `snajp:humanizer-svenska` — tonen avgörs där.
   Justeras i `agent-core/overlays/leads-hard-rules.md`.
2. ~~Grundningskrav på siffror och kundreferenser i utkast~~ — **BYGGT
   2026-08-14.** `app/leads/grounding_gate.py` fäller ostödda påståenden,
   `GROUNDING_V1` reparerar en gång, delta-humaniserar bara de ändrade
   meningarna, och grindar om. Kvarstår ett ostött påstående går utkastet
   till en människa (INV-GROUND-001). Den påhittade "30 procent"-siffran är
   regressionstestad i `tests/leads/test_grounding_gate.py`.
3. `mk:prospecting` — behåll AV:s bedömning, be den motivera tydligare.
   Ny overlay, inte en skill-ändring.

### (historik) Uppdraget innan datan fanns

Uttrycklig instruktion 2026-08-07: *"Eftersom det är mailbaserat har vi inte
samma tidspress och kvalitet på output är största prioritet, men det är
förstås ändå intressant ur kostnadssynpunkt, därför behöver vi noggranna
tester för att kunna utvärdera ordentligt."*

Konsekvens: **inget playbook-steg i `app/leads/*_playbook.py` ska få en
`thinking`-override förrän den fulla jämförelsen är klar och användaren har
sett resultatet.** Sätt inte defaulten till "disabled" för leads bara för att
den är det för support — det är en separat, ännu ofattad beslut.

Körning startad 2026-08-07 (se Steg 1 för status — troligen fortfarande
igång när du läser detta):

```bash
python scripts/run_live_tests.py --leads --modes disabled,enabled
```

Kör:

```bash
python scripts/run_live_tests.py --support --modes enabled,disabled
python scripts/run_live_tests.py --leads   --modes enabled,disabled
```

Resultat skrivs till `docs/live-tests/` (JSON + markdown, fulla outputs).

---

## 5. Vad som återstår — i ordning

### Steg 0: FÖRST — skaffa `DATABASE_URL` och testa mot RIKTIG pgvector-sökning

**Support-jämförelsen ÄR körd** (66 skarpa anrop, båda lägena). Resultat och
full analys: [`docs/THINKING_MODE_COMPARISON.md`](docs/THINKING_MODE_COMPARISON.md),
rådata i `docs/live-tests/support-20260807-200723.{json,md}`.

Den avslöjade två buggar:

1. **Mallrester nådde kundsvaret** (`[Your name]`, `[Kundtjänst]` i 3 av 10
   svar) — **ÅTGÄRDAD** via `strip_placeholders` i `app/agent/tools.py`,
   regressionstest i `tests/agent/test_placeholder_gate.py`.
2. **KB-återvinningen missar uppenbara träffar** — **EJ ÅTGÄRDAD, diagnos
   KORRIGERAD två gånger, läs noga.**

**Första diagnosen (fel):** trodde `GEMINI_API_KEY` saknades → inga
embeddings → dålig fulltextsökning. Nyckeln sattes, samma sanity-check
kördes om, felet fanns kvar oförändrat (till och med värre — en ny
irrelevant träff dök upp).

**Andra diagnosen (rätt, verifierad i kod):** testharnesset använder
`MemoryStorage`, vars `search_kb` (`app/storage/memory.py`) tar emot
`embedding`-parametern men **använder den aldrig** — ren tokenöverlappning,
alltid, oavsett nyckel. "Vilka betalsätt" och "Betalningsmetoder vi
accepterar" delar noll tokens (olika ordformer). Dokumenterat med en
varningskommentar i koden så nästa person inte upprepar misstaget.

**`PostgresStorage` (den faktiska produktionsvägen, pgvector-cosine, tröskel
0.25) är ALDRIG TESTAD** — `DATABASE_URL` är inte satt lokalt. Det är den
enda plats embeddings-nyckeln faktiskt kan bevisa något.

**Gör detta:**
1. Skaffa en Postgres-anslutningssträng för `snajp_app`-rollen (skapad i
   avsnitt om G1 nedan; lösenord är INTE satt än — se §3 där).
2. Sätt `DATABASE_URL` i `snajp-support/.env`.
3. Kör om sanity-checken med `PostgresStorage` i stället för `MemoryStorage`:
   ```python
   storage = await PostgresStorage.connect(get_settings().database_url)
   ```
4. Jämför `kb_sources` mot samma frågor. Först då säger resultatet något om
   embeddings-kvalitet.

**Tills detta är gjort är kvalitetsdelen av support-jämförelsen (§2 i
`THINKING_MODE_COMPARISON.md`) overifierad mot produktion** — kostnads-/
latensdelen (§1) är fortfarande giltig eftersom samma trasiga retrieval
drabbade båda thinking-lägena lika.

### Steg 1: KLART 2026-08-09 — leads är migrerad, jämförelsen omkörd

> **Status:** migreringen nedan är **gjord**. `app/agent/leads_agent.py` kör
> Fas B (8 steg) och Fas C (4 steg) via `step_runner.run_step`.
> `THINKING_MODE` når nu varje anrop, `agent_runs` skrivs, utdatakontraktet
> gäller per steg, och skrapningen sker i kod före steg 1.
>
> - Ny jämförelse (giltig): [`docs/LEADS_THINKING_COMPARISON.md`](docs/LEADS_THINKING_COMPARISON.md)
> - Vad som ändrades: `docs/THINKING_MODE_COMPARISON.md` §7
> - Regressionstest för själva grundfelet:
>   `tests/agent/test_leads_agent_wiring.py::test_thinking_mode_reaches_the_api_call`
>   — det inspekterar de kwargs LLM-klienten FICK, inte vad koden påstår.
> - **Kvarstår:** Fas A (`run_onboarding_turn`) kör medvetet kvar på
>   `Runner.run` (flerturssamtal) och saknar därför fortfarande
>   thinking-kontroll och `step_log`.
>
> Texten nedan står kvar som beskrivning av felet som åtgärdades.

#### (historik) Jämförelsen 2026-08-08 var OGILTIG

**Kört 2026-08-08, resultatet går inte att använda.** 12 körningar (3 prospekt
× 2 tenants × 2 lägen), alla tekniskt lyckade, men `THINKING_MODE` hade noll
effekt: `app/agent/leads_agent.py` kör `Runner.run(...)` (Agents SDK-loopen)
på tre ställen och rör aldrig `app/agent/step_runner.run_step`. Alltså:

- `thinking_kwargs()` anropas aldrig → båda "lägena" körde identisk config
  (avslöjades av att latenserna var identiska, ibland lägre med thinking PÅ —
  i support var PÅ 6× långsammare)
- inget `step_log`, inga `reasoning_tokens`, ingen `agent_runs`-loggning (G10)
- inget utdatakontrakt per steg (Del C p.4)
- `skills_used` listar deklarerade skills, inte lästa — **samma
  overifierbarhet som supportagenten hade före omskrivningen**

Användarens krav ("bevaka hur skillsen anropas", jämför "VARJE delmoment")
är alltså **inte uppfyllbart** med leads-agentens nuvarande arkitektur.

**Gör i denna ordning:**
1. Migrera `leads_agent.py`:s tre `Runner.run`-anrop till `step_runner.run_step`,
   precis som `support_agent.py` gjordes. Playbookarna finns redan
   (`app/leads/{onboarding,research,outreach}_playbook.py`) och deklarerar
   stegen — det som saknas är själva körvägen.
2. Verifiera med `--skill-audit` + `step_log.injected_chars` per körning.
3. Kör OM jämförelsen (kommandot nedan). Först då säger den något.
4. Sätt `PlaybookStep.thinking` per leads-steg utifrån den datan — **inte**
   genom analogi till supportbeslutet (mailbaserat, ingen tidspress,
   kvalitet väger tyngre än latens).

Full analys: `docs/THINKING_MODE_COMPARISON.md` §6. Rådata behålls som bevis
på att körningen skedde: `docs/live-tests/leads-20260807-225625.json` — får
**inte** citeras som en thinking-jämförelse.

### Steg 1b: kommandot (efter migreringen ovan)

```bash
python scripts/run_live_tests.py --leads --modes disabled,enabled
```

Output till `docs/live-tests/leads-run.log` under körning, slutresultat till
`docs/live-tests/leads-<stamp>.json`. Tidskrävande: 12 körningar tog ~50 min
i 2026-08-08-passet. **Kör den inte förrän migreringen i Steg 1 är klar** —
utan den mäter den ingenting (det var precis felet 2026-08-08).

`scripts/run_live_leads.py`: tre riktiga svenska bolag (Gina Tricot,
Blomsterlandet, Sportamore), research via ScrapeGraphAI mot deras publika
webbplatser (INV-DATA-002 uppfylld — company_website registreras som första
källa), sedan ett outreach-utkast per bolag. Körs för **Nordlys Handel**
(UTAN onboarding — testar luckhanteringen från `onboarding_state.py`) och
**Snajps egen tenant** (MED fullständig profil, redan ifylld i filen).
Skickar ALDRIG något — köas bara.

Använder `MemoryStorage`, INTE `PostgresStorage` — samma Steg 0-begränsning
gäller här också för eventuell KB-baserad kontext, men leads-flödets
research bygger huvudsakligen på ScrapeGraphAI-skrapning + skill-resonemang,
inte KB-sökning, så det är mindre kritiskt här än för support.

Utöka `docs/THINKING_MODE_COMPARISON.md` med ett nytt avsnitt "§4 Leads"
när körningen är klar:

- Fullständig output per prospekt, per steg, per läge, sida vid sida —
  användarens uttryckliga krav: **VARJE delmoment** i hela flödet
- Per steg: `tokens_out`, `reasoning_tokens`, latens, `sources_used`, `context_refs`
- Skilj på kundflödet (utan onboarding) och Snajp-flödet (med onboarding) —
  onboarding-luckorna kan påverka kvaliteten oberoende av thinking
- **Ingen rekommendation ännu** — bara data. Beslutet är användarens, inte
  automatiskt "samma som support". Motivering: mailbaserat (ingen
  tidspress) + kvalitet är prioritet, kostnad är "intressant men inte
  avgörande". Presentera avvägningen, låt användaren välja.

**Krav från användaren, gäller båda flödena:** varje skill ska verifieras
anropad i sitt **kompletta** skick (inkl. references) och jämföras mellan
lägena. `--skill-audit` ger integritetsdelen; `step_log.injected_chars` ger
per-körning-beviset. `thinking_mode`-fältet i `step_log` visar exakt vilket
läge varje enskilt anrop kördes med — inklusive per-steg-override (se §4).

### Steg 2: Väck de döda modulerna eller ta bort dem

Ta ställning per modul — bygg in i live-vägen eller radera. Låt dem inte ligga
kvar som falsk trygghet:

1. `decide_promotion` → anropa vid baseline-bump, blockera pin-flytt vid regression
2. `ComposedRun` / `pinned_pack_version` → läs `agent_configs.pinned_pack_version`, kör pinnad pack
3. `build_follow_up_sequence` → koppla till `offers.weakest_lever` + `send_queue`
4. `route_handoff` → anropa när outreach-agenten flaggar positivt svar

### Steg 3: Ersätt edge-function-stubbarna

`supabase/functions/discover-leads/index.ts` och `generate-outreach/index.ts`
returnerar hårdkodad text. Antingen proxya till FastAPI-endpointsen
(`/api/leads/research/step`, `/api/leads/outreach/draft`) eller ta bort dem.
Planens Context-avsnitt pekar ut dem explicit.

### Steg 4: Email Studio + dashboard

- Utkast från `outreach_messages` ska synas som drafts i Email Studio
  (`app/api/email-studio/route.ts`, tabellen `ss_drafts`)
- Vy för `GET /api/leads/runs` så hela research-processen går att granska
  från dashboarden — `step_log` innehåller allt som behövs

### Steg 5: Utvärdera ScrapeGraphAI vs agent-reach

Användarens fråga: räcker ScrapeGraph för all nödvändig information? I så fall
är agent-reach överflödig (den kan ändå inte användas enbart via API).
Avgörs på riktig research-output från Steg 1 — inte på arkitekturresonemang.

### Steg 6: Kvarstår hos användaren (kan inte automatiseras)

- Branch protection med `verify.yml` som obligatorisk check på `development` och `main`
- Utan det är hela invariantsystemet rådgivande, inte tvingande (plan Del L6)

---

## 6. Fällor att undvika

1. **Markera inget som klart för att enhetstesterna är gröna.** Det var exakt
   felet i den första rundan: 15/15 "klart", men läsgarantin anropades aldrig,
   `agent_runs` skrevs aldrig, och leads-pipelinen saknade ingång (inget sätt
   att skapa ett prospekt). Kör flödet live innan du säger att det fungerar.
2. **Rör aldrig innehållet i `agent-core/skills/` — HÅRD REGEL, numera
   mekaniskt tvingad (INV-SKILL-005).** Om ett skill-anrop fallerar eller
   verkar oläst: hårdna routingen. Om outputen behöver justeras: skriv
   TILLÄGGSINSTRUKTIONER i playbookens `task`/`case_context`. Ändra aldrig
   skillen. `tests/invariants/test_inv_skill_005.py` fäller builden på varje
   tyst redigering — den förbjuder inte ändringen, den gör den omöjlig att
   göra omärkt.
3. **Simuleringsläget döljer allt.** `is_simulation()` gör att support faller
   till `app/simulation/sim_agent.py` och leads-ytorna svarar 503. Ett grönt
   testresultat i simuleringsläge bevisar ingenting om agenten.
4. **Sidoeffekter hör hemma i kod, inte i modellen.** Eskalering avgörs av tre
   oberoende villkor i `support_agent.py`, inte av att modellen kom ihåg att
   anropa ett verktyg. Behåll den ordningen.
5. **`send_queue` är den enda vägen ut.** Bara
   `app/leads/scheduler.process_due_item` får sätta `status='sent'`
   (INV-SEC-004). Lägg aldrig ett sändverktyg i agentens verktygslista.
6. **Testsviten är hermetisk — håll den så.** `tests/conftest.py` tvingar
   simuleringsläge för alla tester. Utan den började 17 tester göra skarpa
   API-anrop i samma sekund som en riktig `DEEPSEEK_API_KEY` fanns på
   maskinen, dvs. testresultatet berodde på utvecklarens miljö. Ett test som
   ska köra live måste sätta sin nyckel explicit och mocka nätverksgränsen.
7. **`monkeypatch.delenv` fungerar INTE för att simulera saknad nyckel.**
   Nyckeln kan komma från `.env`-FILEN, inte processens env — `delenv` blir
   ett no-op och pydantic-settings läser den ändå. Använd
   `monkeypatch.setenv(NAME, "")`, som faktiskt override:ar. Kostade ett
   oavsiktligt skarpt skrapningsanrop innan det upptäcktes.
8. **`MemoryStorage.search_kb` ignorerar `embedding`-parametern helt.** Ren
   tokenöverlappning, alltid — bevisar ingenting om semantisk sökkvalitet
   oavsett vilken embeddingnyckel som finns. Kostade en felaktig diagnos
   (trodde `GEMINI_API_KEY` var boven; satte den, felet kvarstod, letade
   vidare, hittade rätt orsak i storage-lagret i stället). Kvalitetstester
   av KB-sökning MÅSTE köras mot `PostgresStorage` — se Steg 0.
9. **En första hypotes som "verkar rimlig" måste ändå verifieras i koden
   innan den skrivs ner som slutsats.** "GEMINI_API_KEY saknas" lät som en
   fullt rimlig förklaring och hamnade i en tidigare version av det här
   dokumentet som facit — tills nyckeln sattes och felet inte försvann. Läs
   den faktiska implementationen (`search_kb` i just det storage-lager som
   användes) innan en rotorsak skrivs ner permanent.

---

## 7. Snabbstart för nästa agent

```bash
cd "C:\Users\Anton L\snipe-leads"
python scripts/keys.py --check                    # miljö OK?
cd snajp-support && python -m pytest -q           # 240 gröna?
cd .. && python -m pytest tests/invariants -q     # invarianter gröna?
python scripts/run_live_tests.py --skill-audit    # skills kompletta?
```

Läs sedan, i ordning: den fullständiga planen (Del A–L),
`ARCHITECTURE_INVARIANTS.md`, och avsnitt 2 ovan (dött vs byggt).
