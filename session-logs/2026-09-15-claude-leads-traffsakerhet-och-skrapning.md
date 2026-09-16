# Session Log — 2026-09-15 (Claude, testkörning)

## Session Summary
Leadsagenternas träffsäkerhet mot QA-kunden Nordforms målgrupp mättes som kund i webbläsaren och gick från 0 av 5 (leadskörning) och 0 av 10 (leadslista) till 5 av 5 respektive 10 av 10. Längs vägen hittades och rättades sex fel som dolde varandra: jobbannonskällan sökte på Snajps egna ord, Gemini-sökningen föll på Vertex, underkända bolag fick mejlutkast, formulärets storlek nådde aldrig agenten, researchen fällde bolag för okänd storlek, och skrapningen blockerade hela api-processen och gav upp på parkerade sajter. Allt är pushat till development och liveverifierat; fyra av rättningarna släpptes till produktion med PR #13, de två sista väntar i PR #14 på Antons granskning.

## What Changed

### Files Created
- `snajp-support/app/leads/kvalificeringsgrind.py` — kodregel efter ICP-bedömningen: känd storlek utanför intervallet eller bemanningsföretag fäller bolaget; kan bara fälla, aldrig godkänna.
- `snajp-support/app/leads/platshallare.py` — känner igen parkerade domäner, "under konstruktion", till salu och standardsidor; `utan_platshallare` används av discovery.
- `snajp-support/tests/leads/test_jobtech_malgrupp.py` — JobTech söker på kundens branscher, inte kundtjänst; bemanningsbolag filtreras.
- `snajp-support/tests/leads/test_discovery_vertex_roll.py` — Gemini-sökningens anropskropp bär `role: user`.
- `snajp-support/tests/leads/test_webbplatsgissning_redirect.py` — redirect godtas bara till bolagets egen värd.
- `snajp-support/tests/agent/test_leads_v2_utkastgrind.py` — V2 sätter stopped_early; kodgrinden och "okänt är inte fel" når modellen.
- `snajp-support/tests/leads/test_kvalificeringsgrind.py`, `tests/leads/test_run_overrides_storlek.py`, `tests/agent/test_research_tools_reserv.py`, `tests/leads/test_platshallare.py` — regressionstester för respektive rättning.
- `session-logs/2026-09-15-claude-leads-traffsakerhet-och-skrapning.md` — den här loggen.

### Files Modified
- `snajp-support/app/leads/sources/jobtech.py` — sökord ur ICP:ns branscher (annars korta nischord), bemanningsbolag bort (a65ab1e).
- `snajp-support/app/leads/discovery.py` — `role: user` i Vertex-anropet, redirect-värdkontroll (ed60d10); platshållarfilter i `hitta_bolag` (aa68ccf).
- `snajp-support/app/agent/leads_research_v2.py` — stopped_early som V1 (36bf8fa); fälten antal_anstallda/ar_bemanningsforetag, `icp`-parameter och kodgrinden (2b5b8db); regeln "OKÄNT ÄR INTE FEL" i uppgiften (c158455).
- `snajp-support/app/agent/leads_agent.py` — samma `icp`-parameter, fält, grind och regel för V1 (2b5b8db, c158455).
- `snajp-support/app/leads/context_pack.py` — formulärets anställda-intervall skrivs även till `size` (2b5b8db).
- `snajp-support/app/api/leads.py` — batchen skickar körningens sammanslagna ICP till researchen (2b5b8db).
- `agent-core/overlays/leads-research-v2.md` — skarpa regler för storlek, okänt och bemanning (2b5b8db).
- `snajp-support/app/agent/research_tools.py` — ScrapeGraphAI i tråd med tak 60 s, reservhämtning av samma registrerade URL, kodnotering för platshållare (aa68ccf).
- `snajp-support/tests/conftest.py` — `LEADS_PLATSHALLARKONTROLL` av i testläge (aa68ccf).
- `snajp-support/tests/agent/test_research_tools.py` — feltestet mockar reservhämtningen (aa68ccf).
- `STATUS.md` — nytt avsnitt för dagen.
- Rapport-artefakten "Snajp pilotläge" (https://claude.ai/artifact/FoofXP46WE7Xp4fKzPfNds) — version 9–12: leads-ommätningen, storlek och bemanning, skrapningen, releaseläget.
- Projektminne `~/.claude/projects/.../memory/leads-traffsakerhet-2026-09-15.md` + MEMORY.md-indexrad.

### Files Moved/Deleted
- Inga.

## Decisions Made
- **Kodgrinden får bara fälla, aldrig godkänna:** modellens bedömning står kvar och kan bara skärpas — ett fel i grinden ska aldrig kunna släppa igenom ett bolag som ska mejlas.
- **Okänd storlek fäller inte:** de flesta småbolag skriver aldrig ut antal anställda; att fälla dem tömmer målgruppen. Regeln ligger både i overlay och uppgiftstext eftersom overlayen ensam inte räckte (Spoon).
- **Reservhämtning av samma registrerade URL är tillåten:** allowlist-garantin (bara registrerade URL:er) består; discovery gjorde redan direkta anrop mot bolagssajter.
- **Inget pushat till development medan PR #13 var öppen:** PR:en följer grenen, så overifierad kod hade glidit in i releasen. Rättningarna hölls okommittade tills Vertex koppling meddelat merge.
- **"Pusha till main" = release-PR:** main får aldrig pushas direkt; PR #14 öppnad, mergen är Antons.

## Context & Discussion
- Mätningen gjordes som QA-testkunden (tenant ce659621-…) med Nordforms formulär: IT-konsulter, redovisningsbyråer, arkitektkontor, reklambyråer, Stockholm/Göteborg, 10–49 anställda.
- Testsviten fångade inte fel 1–2 eftersom all HTTP mockas — bara mätning som kund mot riktiga källor och riktig Vertex visade dem.
- Release-mekaniken ägdes under dagen av sessionen "Vertex koppling"; snipe-leads-e6 skrev handoffen till Anton. Mitt "klart för main" för 2b5b8db gavs efter live-bevis (FOJAB 168 anställda fälld av grinden, Ekord 13 godkänd).
- Produktionen kör ed46200 (PR #13) sedan 10:07.

## Open Threads
- PR #14 (c158455 + aa68ccf, plus 2dd393e och docs från andra sessioner) väntar på Antons granskning och merge; 2dd393e:s `railway_bokforing.py --env main` bör torrköras innan någon kör det mot main.
- En bortsorterad platshållare fylls inte på: körningen gav 4 bolag i stället för 5. Nästa steg är att överbeställa från Gemini med marginal och trimma efter filtret.
- Discovery kopplade "Arkitektgruppen i Stockholm AB" till Gävle-firmans sajt; namn↔sajt-kontrollen gäller inte Gemini-träffar. Nästa steg är att mäta hur ofta det händer innan grinden utvidgas.
- Devies AB underkändes som bemanningsföretag men ser ut som en digitalbyrå. Nästa steg är att kontrollera sajten och vid behov skärpa definitionen i overlayen.
- "Hej ," när kontaktnamn saknas i utkast, och dubblettrisk vid listbeställning när servern startas om mitt i — båda kvar.
- De två otrackade `docs/live-tests/evals-20260914-*.json` ska inte committas.

## Tillägg eftermiddag 2026-09-15

- PR #14 mergad 13:12 (main 871aa7d): skrapningen och okänt-regeln i produktion.
- `567b43f` påfyllning av bortsorterade platshållarplatser (källslingan kollar före räkning; Gemini ombeds om reserver i samma anrop, kapas efter filtret). 1938 tester.
- Liveverifieringen föll två gånger: Gemini grounded-sökningen tog >180 s i dev. Lokalt mätt: 55 s med reserver, 156 s utan — reserverna är inte orsaken, Vertex-latensen varierar.
- `2319aa8` lästak 180 s, ReadTimeout görs inte om, formulären (LeadsRunForm sökfas, LeadsSnabbsok) väntar ~5 min. Verifierat live: kunden får nu "Kunde inte söka efter bolag just nu" i stället för att formuläret ger upp — men sökningen gav fortfarande 0 av 5.
- PR #15 (öppnad av Vertex koppling, spets 2319aa8) väntar på Antons merge; mitt besked i PR:en: "inte klart, men säkert att släppa" (main har samma sega sökning med sämre hantering).
- ÖPPET: mätning av `thinkingBudget: 0` mot standardtänkande för grounded-sökningen körs i bakgrunden; resultatet skrivs till `%TEMP%/claude/C--Users-sebbe-Desktop-snipe-leads/c498f2b8-.../tasks/b7fxz5b47.output`. Nästa steg: om thinkingBudget 0 är klart snabbare med likvärdiga träffar → lägg `"thinkingConfig": {"thinkingBudget": 0}` i `generationConfig` i `discovery._gemini_med_sokning`, test, push, liveverifiera Nordform-körningen, kvittera i PR #15.

## Cross-Project Handoffs
- None this session.

## Current State After This Session
Leadsagenterna träffar Nordforms målgrupp i development (lista 10/10 med mejl, körning 5/5 i rätt bransch och stad) och produktionen har alla rättningar utom skrapningen och okänt-regeln. PR #14 är öppen med gröna tester lokalt och CI på väg. Nästa session bör ta Antons granskning av PR #14, fyllnaden av bortsorterade platser och en mätning på en andra kunds målgrupp.

Mekaniska conclude-steg: `~/.agents/scripts/conclude-finalize.py` finns inte på disken, så sessions.db-raden, globala STATUS.md, minnesspegeln, valvbackupen och omindexeringen kördes INTE. Upstream: inga globala infra-ändringar.

<!-- session-state
date: 2026-09-15
type: bugfix-and-verification
files_created:
  - snajp-support/app/leads/kvalificeringsgrind.py
  - snajp-support/app/leads/platshallare.py
  - snajp-support/tests/leads/test_jobtech_malgrupp.py
  - snajp-support/tests/leads/test_discovery_vertex_roll.py
  - snajp-support/tests/leads/test_webbplatsgissning_redirect.py
  - snajp-support/tests/agent/test_leads_v2_utkastgrind.py
  - snajp-support/tests/leads/test_kvalificeringsgrind.py
  - snajp-support/tests/leads/test_run_overrides_storlek.py
  - snajp-support/tests/agent/test_research_tools_reserv.py
  - snajp-support/tests/leads/test_platshallare.py
  - session-logs/2026-09-15-claude-leads-traffsakerhet-och-skrapning.md
files_modified:
  - snajp-support/app/leads/sources/jobtech.py
  - snajp-support/app/leads/discovery.py
  - snajp-support/app/agent/leads_research_v2.py
  - snajp-support/app/agent/leads_agent.py
  - snajp-support/app/leads/context_pack.py
  - snajp-support/app/api/leads.py
  - agent-core/overlays/leads-research-v2.md
  - snajp-support/app/agent/research_tools.py
  - snajp-support/tests/conftest.py
  - snajp-support/tests/agent/test_research_tools.py
  - STATUS.md
decisions_made: 5
open_threads: 6
handoffs_pending: []
priority_changes: false
status_updated: true
goals_updated: yes
next_session_focus: "Antons granskning av PR #14, fyllnad av bortsorterade platser, mätning på en andra kunds målgrupp"
session-state -->
