# Session Log — 2026-08-27

## Session Summary
Fortsättning på 2026-08-26: djupaudit av hela agentbackenden på Antons uttryckliga "fortsätt tills jag är nöjd" — tre döda kedjor lagade (outreach-trådar, prospektsvar, uppföljningssekvens), självlärande persisterat, eval-harness och kundminne byggda utifrån hämtad arkitektur (mem0/Langfuse-mönster). Allt pushat till `development` och skarpt verifierat (7/7 golden evals, hälsokontroller gröna). Sessionen avslutades med en infrastrukturändring: Railways deploy-trigger för development pekar nu på grenen `development` direkt i stället för spegelgrenen `railway-development` — Vercel är avvecklat, en enda push räcker nu.

## What Changed

### Files Created (urval — full lista i commit 71fb992)
- `snajp-support/app/leads/svar.py` — prospektsvarshantering (klassificering + kodagerande), `POST /api/leads/svar`
- `snajp-support/app/leads/follow_up_generator.py` — uppföljningssekvensens produktionsanropare (var bara testad)
- `snajp-support/app/leads/gissnings_gate.py` — kodgrind mot gissningsord om mottagaren
- `snajp-support/app/agent/evals.py` + `scripts/kor_evals.py` — eval-harness, 7 golden cases ur verkliga incidenter
- `supabase/migrations/051_agent_suggestions.sql`, `052_customer_memory.sql`
- `agent-core/overlays/leads-reply.md`, `leads-followup.md`
- `components/leads/AgentLarande.tsx` — adminyta för agentens förslag/feedback
- `HANDOFF-2026-08-27-AGENTBACKEND.md` — handoff till Sebbe
- `scripts/jamfor_livekorningar.py` — jämförelseskript för live-körningar
- ~15 nya testfiler i `snajp-support/tests/`

### Files Modified
- `snajp-support/app/agent/support_agent.py` — kundminne inbakat i triagesteget, flerturssökning
- `snajp-support/app/agent/retention_classifier.py` — missnöje kan bara förstärka en uppsägningssignal, aldrig bära den ensam
- `snajp-support/app/storage/{base,memory,postgres}.py` — `ensure_outreach_thread`, `agent_suggestions`, `customer_memory`, `agent_feedback`, RRF-hybridsökning
- `snajp-support/app/agentcore/packs.py`, `step_runner.py` — overlay-komposition (tuple av overlays per steg)
- `agent-core/overlays/leads-hard-rules.md`, `leads-grounding-repair.md` — evidensregler ur skarpa körningar
- `DEPLOY.md`, `CLAUDE.md` — deploy-topologi omskriven efter trigger-ändringen
- `scripts/railway_provision.py` — `ENVIRONMENTS["development"]` ändrad från `"railway-development"` till `"development"` (källan till sanning för framtida reprovisionering)
- `tests/invariants/test_inv_deploy_002.py` — uppdaterad i samma commit som ovan

### Files Moved/Deleted
Inga.

## Decisions Made
- **Skillsen i `agent-core/skills/` rörs aldrig** — alla förbättringar i overlay-lagret. Bekräftat av Anton uttryckligen ("det är därför att inte råka ändra saker i skillsen när vi kan tweaka instruktionerna").
- **Fortsätt tills stopp, rapportera vid milstolpar** — Anton avvisade det första svaret som avslutat för tidigt ("du har skyndat dig igenom arbetet... jag vill inte att du slutar tills jag godkänner det"). Tre varv kördes, med milstolperapport publicerad som artifakt vid varje varv.
- **Arkitektur hämtad utifrån** (varv 3): mem0:s ADD-only-minnesmönster valdes över Zeps kunskapsgraf (fel skala för en supportkunds fakta); egenbyggd faithfulness-mätning (grundningsextraktorn) valdes över en LLM-domare (kalibreringskostnad). A/B-varianttracking avvisat — blockerat av att `offers`-rader aldrig skrivs.
- **Railways deploy-trigger för development ändrad live via GraphQL, inte dashboard** — samma verktygsprincip som resten av `scripts/railway_*.py`. Scope uttryckligen avgränsat: bara development, main lämnas orörd tills Anton tar det som ett separat steg.
- **`railway_provision.py`s `ENVIRONMENTS`-dict identifierad som den verkliga källan till sanning** — utan att ändra den hade en framtida reprovisionering tyst återställt triggern. Detta upptäcktes genom att `verify_railway.py` föll EFTER att triggern redan var korrekt ändrad — skriptet mätte mot den gamla koden, inte mot Railway.

## Context & Discussion
- En Claude Code-processkrasch inträffade mitt i en bakgrundskörning (eval-harnessen). Vid återstart hade kontexten om en redan byggd adminyta (`AgentLarande.tsx`) tappats, vilket ledde till en felaktig "rättelse" i STATUS.md som påstod att ytan inte fanns. Verifierat mot disk (tsc rent, vaktposter gröna) och STATUS.md återställd till sanningen, med incidenten dokumenterad öppet i stället för dold.
- Design-stop-hooken (CARL DESIGN-domänen) triggade flera gånger på UI-ändringar (rapportartifakten, `AgentLarande.tsx`, `BokforingDemo.tsx`). Hanterat genom att faktiskt rendera och läsa skärmdumpar av rapporten (ljust/mörkt tema, tre bredder) innan publicering — inte kringgått.
- Sessionen körde till $0,56 av $3 USD-budget kvar vid /conclude-anropet, vilket tvingade en nedskalad avslutning: ingen `conclude-finalize.py`-bakgrundskörning (vault-backup, qmd-reindex, chorus-handoff), ingen skill-skapande-utvärdering. Dokumenterat explicit i stället för utelämnat tyst.

## Open Threads
- **`main` är fortfarande 80+ commits efter `development`** och saknar migration 043–052 (`snipe-zfc`). Deploy-triggern för `main` är medvetet oförändrad — Anton sa uttryckligen "vi tar main senare (main ska ersätta railway-main och trigga produktionsdeployment)". Nästa session bör fråga om det är dags.
- **`snipe-a1c` (P0, Gemini legal pause)** är fortfarande obesvarad sedan 2026-08-26 — production kör `mode: live` mot Gemini free tier utan de fyra åtgärderna (nivå, fakturering, egen nyckel, DPA). Inte rört denna session; bör tas upp direkt nästa gång.
- **RRF-hybridsökningen är overifierad mot en riktig Postgres** — `snajp_app`-lösenordet saknas fortfarande (`snipe-lt9`, blockerat sedan 2026-08-07).
- **Prospektsvar-vägen och uppföljningsgeneratorn är nya kodvägar** som bara körts mot MemoryStorage och `--skarp`-verifiering, inte end-to-end mot Postgres i drift.
- **Adminytan `/dashboard/larande` är inte pixelverifierad inloggad** — inget testkonto tillgängligt denna session.
- **`snipe-xl9`**: mejlpipeline-routing av prospektsvar, blockerad av att sändvägen fortfarande är en stub (`snipe-ork`).

## Cross-Project Handoffs
Inga identifierade denna session — allt arbete var internt i `snipe-leads`.

## Current State After This Session
`development` är live med den fullständiga agentbackend-auditen: 1445 backendtester och 333 rotvaktposter gröna, 7/7 golden evals mot riktig modell, verify_railway.py helt grönt. Railways deploy-trigger för development är fixad permanent (källan till sanning i kod, inte bara i Railway-dashboarden). Nästa session bör börja med `snipe-a1c` (P0, juridiskt) innan mer trafik routas genom `main`, och sedan avgöra om `main` ska läggas om till att deploya direkt liksom `development` gjorde denna session.

<!-- session-state
date: 2026-08-27
type: feature-development + infrastructure-fix
files_created:
  - snajp-support/app/leads/svar.py
  - snajp-support/app/leads/follow_up_generator.py
  - snajp-support/app/leads/gissnings_gate.py
  - snajp-support/app/agent/evals.py
  - scripts/kor_evals.py
  - scripts/jamfor_livekorningar.py
  - supabase/migrations/051_agent_suggestions.sql
  - supabase/migrations/052_customer_memory.sql
  - agent-core/overlays/leads-reply.md
  - agent-core/overlays/leads-followup.md
  - components/leads/AgentLarande.tsx
  - HANDOFF-2026-08-27-AGENTBACKEND.md
files_modified:
  - snajp-support/app/agent/support_agent.py
  - snajp-support/app/agent/retention_classifier.py
  - snajp-support/app/storage/base.py
  - snajp-support/app/storage/memory.py
  - snajp-support/app/storage/postgres.py
  - snajp-support/app/agentcore/packs.py
  - snajp-support/app/agentcore/step_runner.py
  - agent-core/overlays/leads-hard-rules.md
  - agent-core/overlays/leads-grounding-repair.md
  - DEPLOY.md
  - CLAUDE.md
  - scripts/railway_provision.py
  - tests/invariants/test_inv_deploy_002.py
decisions_made: 5
open_threads: 6
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: "skipped -- budget exhausted this session, se STATUS.md 2026-08-27-posten för sakinnehallet"
next_session_focus: "snipe-a1c (P0 juridik) forst, sedan avgor om main ska laggas om till direkt Railway-deploy som development"
session-state -->
