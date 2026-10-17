# Handoff 2026-10-06 — Iris: inga påhittade bolag, rätt målgrupp, utkast till VD, instruktioner per agent

Plan: `plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md` (fas 0–9). Logg: `session-logs/2026-10-06-session-log.md`.

## 1. Läget just nu, verifierat (2026-10-06)

- **Git:** `development` lokalt = `649ca27`, **7 commits före origin och 3 efter** (Sebbe pushade `3f630b5`, `520d7f9`, `9873894`, alla support, efter min sammanslagning). Inget pushat. Nästa agent: `git merge origin/development` (konflikter möjliga i `snajp-support/app/agent/support_agent.py`, `support_systemprompt.py`), kör sviten, pusha på Antons ord.
- **Antons ocommittade filer, orörda:** `docs/utkast-merinfo-api-forfragan.md`, `next-env.d.ts`, `package.json` (gsap/lenis), `strategies.md`, `docs/utkast-allabolag-api-forfragan.md`, `gsap.js`, `smooth-scroll.js`, `session-logs/2026-09-30-session-log.md`.
- **development (Railway):** kör äldre kod (före mina commits). **Den globala instruktionsraden är fortfarande mallens fem rader (279 tecken, sparad 2026-10-05 20:05 UTC)**, så alla agenter där saknar sanningsreglerna i `agent-core/AGENTS.md`. Uppmätt med `scripts/las_agentinstruktioner.py --env development`. Leads-körningarna 20:34–20:46 UTC läste 279 tecken; de 19:26–19:44 UTC läste 3 610.
- **main:** läser filen (3 610 tecken). Opåverkad.
- **Migration 099** (`supabase/migrations/20261006140000_099_agentinstruktioner_per_agent.sql`) **är inte körd i någon miljö.** Koden behöver den (kolumnerna `agent_type`, `feedback`). Sebbes 096–098 finns redan.
- **Inbäddningar:** den OpenAI-kompatibla Vertex-vägen svarar 500 (uppmätt lokalt idag). Fixen går via Vertex `:predict` (commit `649ca27`), uppmätt lokalt: 1536 dim, omformulerad fråga 0,865, orelaterad 0,479. Befintliga KB-artiklar saknar vektorer tills de bäddas in på nytt.
- **Sviten:** 2 714 gröna, 4 skippade; rotinvarianter 434 gröna. `tsc` rent utom den kända `.next/dev/types/validator.ts`-resten.
- **Maskinen:** 1,4 GB ledigt virtuellt minne, lokal Postgres nere. `next dev` startades därför inte; UI-ändringarna är **inte visuellt kontrollerade**.
- **bd** fungerar inte (dolt saknas i PATH).

## 2. Vad som byggdes

| Commit | Vad | Varför (Antons fynd 2026-10-05) | Verifiering |
|---|---|---|---|
| `f613ac3` | Existensgrind (`app/leads/existens.py`), sökprompten frågar bara efter bolag (ingen kontakt/ort/storlek), sökträffens påståenden följer inte med till prospektet, inget underlag ⇒ inget modellanrop/nivå C/inte Redo/inget utkast, nivå A kräver ett uppfyllt kriterium, utkast bara för leverbara leads, sändspärr för Iris-leads utan godkänd bedömning, merinfo faller inte till Gemini vid kredittak/tjänstefel, bara privata bolag (`app/leads/offentlig.py`) i förfilter/register/sökprompt/profilens standarduteslutning, profilen får `segment` + `offentlig_sektor` (schema 2), säljarens orter är inte målgruppens, körning utan målgrupp stannar med `ingen_malgrupp`, `STANDARDROLLER = ["VD"]`, webbrevisionen bara vid webbkriterium, sammanfattningen namnger skälet. Ny invariant INV-LEADS-EXIST-001. Läsväg `GET /api/admin/tenants/{id}/leads-underlag` + `scripts/granska_leads_underlag.py`, `scripts/las_agentinstruktioner.py`. | Tre påhittade bolag med poäng 100; skolor/kommuner; bygg-slagsida; "bortvalda: ligger i göteborg" | `tests/leads/test_existens.py`, `tests/invariants/test_inv_leads_exist_001.py`, `test_scheduler.py`, `test_discovery.py` |
| `45c1098` | Utkast bara till VD med adress som bär namnet (`discovery.vd_mottagare`), funktionsadress fästs aldrig på namngiven person, utkastet får verifierade citat/lägesbeskrivning/mottagare/vald produkt, underlagsgolv (inga citat ⇒ inget utkast), produktval ur `settings.produkter`, faktagrinden fäller `unnamed_case`, `PlaybookStep.radandringar` (textändring i läst skill, skäl krävs, faller vid import om texten saknas), fyra ändringar i `sa:draft-outreach` + kallmejlsmallen ur skopan, researchoverlayn, Email Studio-exemplen | Påhittat case, platta utkast, rekrytering@/inköpschef, webbpitch från Snajp | `tests/leads/test_utkastunderlag.py`, `tests/agentcore/test_radandringar.py` |
| `fee78f3` | Iris grundprompt `agent-core/prompts/leads-systemprompt.md` + `app/agent/leads_systemprompt.py` (avsnitt per steg) som `agent_md` i Sebbes lager, migration 099, `app/agentcore/baka_in.py` (modellen föreslår ändringar, koden tillämpar), admin-API per agent + återställning, sparad grundprompt gäller chatt/mejlinkorg/omformulering/Iris | Mallen skrev över hela instruktionsblocket | `tests/api/test_admin_instruktioner_per_agent.py`, `baka_in` demo |
| `e90c303` | Adminvyn: flik per lager, feedback, förhandsgranskade ändringar med skäl, bekräftelse vid stora borttagningar, historik med Återställ | Samma | tsc, INV-COPY-001. **Ej renderad.** |
| `649ca27` | `produkter`/`segment`/`offentlig_sektor` i `PUT /api/leads/config`, `scripts/snajp_malgrupp.py` (torrkört mot development), inbäddningar via Vertex `:predict` | Standardmålgrupper för Snajps agenter; Redis Iris-genomgången pekade ut inbäddningarna | test, lokal mätning |

Sebbe hade redan lagt in Antons supportprompt ordagrant (`agent-core/prompts/support-systemprompt.md`, commit `8b27947`) med eget `agent_md`-lager. Jag byggde vidare på det; hans driftregel ("sällan eskalera") står kvar.

Redis Iris (LangCache, Agent Memory, Context Retriever, Data Integration) granskades mot dokumentationen: inget tas in nu (motivering i planens fas 9).

## 3. Vad som återstår, i prioritetsordning

1. **Anton:** godkänn push av `development` efter att agenten slagit ihop Sebbes tre nya commits och kört sviten.
2. **Anton:** kör migration 099 mot development och main samma dag (`python scripts/railway_migrate.py --env development --apply`, sedan `--env main`), annars pausar nattspeglingen och adminvyn faller på saknade kolumner.
3. **Agent, på Antons ord:** återställ development-instruktionerna efter deploy (spara en tom version under Gemensamt, eller `POST /api/admin/instruktioner` via vyn). Mallens text ligger kvar i historiken; den hör hemma som Iris-feedback, och Snajps formulering finns redan i `snajp_malgrupp.py`.
4. **Agent, på Antons ord:** `python scripts/snajp_malgrupp.py --env development --apply`.
5. **Agent:** visuell kontroll av `components/admin/Agentinstruktioner.tsx` och `IrisKorningar.tsx` (1440/375/320) + a11y-audit, när minne finns eller på development utan kunddata i bild.
6. **Agent:** bädda in befintliga KB-artiklar på nytt i båda miljöerna (skript saknas; `app/scripts/seed_kb.py` är förlaga).
7. **Anton + agent:** skarpt Iris-prov N=5 som Snajp utan filter (kräver ScrapeGraph-kredit) och manuell kontroll av varje lead. Sedan `scripts/granska_leads_underlag.py --env development` för att lista gamla påhittade leads; Anton avgör vad som raderas.
8. **Agent:** fas 7 (insynsvyn: flödeskarta ur playbookerna, lagerstapel, källmatris, enskild körning, prompt per lager i `prompt_lager`, migration 100), fas 8 (kundens produkter/segment i inställningarna, kundens egen feedback i användarposition), fas 9 rest (hybridsökning, Iris lär av kundens utslag), mätningen av de tre skillvarianterna.
9. **Öppna frågor till Anton:** gallringsperiod för spårets fulltext (förslag 30 dagar); de fyra föreslagna målsegmenten i `snajp_malgrupp.py` (märkta "förslag").

## 4. Fällor

- **Python via bash-heredoc förstör `\n` i strängar** som skrivs till kodfiler och bryts ibland av citattecken. Skriv ändringsskript till scratchpad-fil eller använd Edit; importera modulen efteråt.
- **Två `Test:`-sökvägar på en rad** fäller metatestet för invarianter (regexen tar en sökväg).
- **`.next/dev/types/validator.ts`** ger ett ofarligt tsc-fel om `app/forhandsvisning/korningar`.
- **Minnet:** kontrollera `FreeVirtualMemory` innan `next dev`; under ~4 GB, starta inte.
- **`Settings` är pydantic:** monkeypatcha inte metoder på instansen; patcha `get_settings` i modulen.
- **merinfo** returnerar nu `[]` vid kredittak och kastar `DiscoveryError` vid tjänstefel (ScrapeGraph kredit/kvot); `None` betyder bara "målgruppen gick inte att översätta".

## 5. Antons instruktioner ordagrant

> Kör /standup och gå igenom föregående arbete samt bilderna för att skapa dig en egen uppfattning av problemen: [inklistrad lång beställning: påhittade bolag, platta utkast, webbpitch från Snajp, skolor som leads, bygg-slagsida, målgrupp per tjänst med tabellen, undvik statliga företag och kommuner, mallen skrev över instruktionerna, supportprompten som förlaga för en lika detaljerad leadsprompt, grundmallen för utkast, instruktioner uppdelade per agent och feedback som Gemini bakar in utan att ta bort innehåll.]

> Det låter bra. Se till att inkludera: Utanför den här planen / Redigering av produkter och segment i kundens egen inställningsyta (skriptet räcker tills en andra kund behöver det). / Kundens egen feedback till sin agent. Mekanismen är densamma, men kundskriven text måste ligga i användarposition (INV-SEC-009) och kräver ett eget beslut. Gå även igenom och se till att skill-kedjan läses och är intakt, behöver de refereras i agentinstruktionerna eller hur kallas dem? Gå igenom det steg för steg för mig i chatten. Gör det även möjligt för Admin att kunna se ALLT underlag som agenterna läser, hur allt från affärskontext, vad ni säljer och kunskapsbas faktiskt läses av agenten samt skills ned till de enskilda skill-filerna och alla övriga instruktioner som ej syns idag, med en tydlig demonstration av flödet, inte bara en vanlig sida med olika rubriker, så att det går att identifiera vart i kedjan något brister.

> Vad kan vi göra åt spårvyn? Se till att playbooksen är med i kartan och visar hur skillsen väljs. Gör så att man kan välja en enskild körning och se hela flödet och vilka skills som kallades för just den körningen. Vad kan vi göra åt den amerikanska skillen som felar utan att påverka resten för mycket? Kan du även utveckla mer kring hur det fungerar att modellen inte anropar någon av skillsen, men att agenten läser dem? Var finns skill-filerna och de övriga instruktionsfilerna lagrade så att agenten kan läsa dem?

> Perfekt. Jag vill även att du går igenom Redis alla Iris-funktioner: https://redis.io/iris/ , läs igenom dokumentationen för varje och undersök ifall vi kan använda oss av någon av dem för att förbättra detta eller något annat i vårt system, var nyanserad och väg in flera alternativ, defaulta inte till minsta antsträngning, det ska fortfarande vara kostnadseffektivt, men skärpan hos agenterna är A och O.

> En sak till, går det att istället modifiera de bortvalda skillsen istället för att slopa dem helt på grund av en rad?

> Kör /conclude
