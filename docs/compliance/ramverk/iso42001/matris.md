# ISO 42001-matris för Snajp

Ramverk: Comp AI, ISO 42001 version 1.0.0, id `frk_68cc0e2a21184ed168ab2eea`, seed-data i `trycompai/comp` commit `712ee1b3`. 70 krav, 76 kontroller, 21 policyer, 61 uppgifter.
Gjord 2026-11-17, endast läsning. Senaste genomgång: 2026-11-18 (andra). Nästa: [FYLL: datum].
Syfte: en sann bild av hur Snajp styr sin AI-användning inför första betalande kund. Snajp ska inte certifieras nu. EU:s AI-förordning täcks inte av ramverket; den står i `ai-forordningen.md`.

**AI-systemen i omfånget.** (1) Supportagenten: läser kundens kundmejl och chattar, klassar, skriver svar, skickar själv i de kategorier kunden ställt på automatiskt svar. (2) Iris, leadsagenten: söker och bedömer bolag mot kundens kriterier, skriver kallmejl, skickar enligt sändspärrarna och kundens autonominivå. (3) Jev: TypeSafes beslutsmodell `jev-1.13.0` för förfiltrering av leads och, när `INKORG_JEV` inte är `off`, klassning av inkorgen. Sedan 2026-11-17 är `INKORG_JEV = off` i `main` och `development` (bevis/konf-efter rad 95, 248), så Jev ser inte längre kundmejl. Modellerna är Gemini 2.5 via Vertex AI i `europe-west1` (Google) och Jev (TypeSafe, USA).

**Statusregler (samma som `../gdpr/matris.md` och `../iso27001/matris.md`).** *Uppfyllt* kräver belägg som finns i dag. Ett ogranskat utkast, ett skript som aldrig körts, en ocommittad ändring eller ett löfte utan mekanism är *delvis*. Där kravet gäller ett beslutat dokument eller en tilldelad roll räcker inte kod: finns bara koden blir det *saknas* eller *delvis*, och raden säger vilket. *Ej tillämpligt* kräver ett konkret skäl. *Okänt* betyder att underlaget inte räcker.

**Gruppering.** Som ramverket: identifierarna heter `ISO/IEC 42001:2023 Clause 4.1` och `ISO/IEC 42001:2023 A.2.2`. Tabellerna skriver bara `4.1` och `A.2.2`. Klausul 4–10, sedan bilaga A.2–A.10.

**Kontroller.** Ramverket kopplar paraplykontrollen *ISO 42001* (`frk_ct_68cc25ac90e3fe79c1beb98d`) till 36 av kraven. Den står som **U**; dess policy är P27 och dess 17 uppgifter upprepas inte per rad. ISO 27001-kontroller som ramverket återanvänder står förkortade: SOP (Standard Operating Procedures), CM (Change management), SMD (Security Monitoring & Detection), SIM (Security Incident Management), MSA (Management Security Accountability), SGR (Security Governance Roles), NS (Network Security), AR (Access Rights), EP (Endpoint Protection), RM (Risk Management), DRP (Disaster Recovery Planning), RCM (Resource Capacity Management), DP (Data Privacy), RL (Regulatory Liaison), DIS (Disciplinary process), PS (Personnel Security). Övriga kontroller har AI-namn och står utskrivna.

**Policyer.** G01–G06 = `../gdpr/policyer/01–06`. P07–P26 = `../iso27001/policyer/07–26`. P27 = `policyer/27-ai-policy-control-framework.md` och P28 = `policyer/28-sanctions-disciplinary.md` här. Uppgifterna står i `uppgifter.md`.

**Hänvisningar.** "AI-inv." = `ARCHITECTURE_INVARIANTS.md` med radnummer; varje invariant har ett test som körs i CI. "BESLUT" = `docs/BESLUT.md` med radnummer. "Inv." = `../../nulage-inventering.md`. "BU A2" = `../../BESLUTSUNDERLAG-2026-11-17.md`. "Lev." = `../../leverantorsgranskning.md`. "DPIA" = `docs/dpia_supportagenten.md`. "IA" = `docs/intresseavvagning_kallmejl.md`. "Evals" = `snajp-support/evals/README.md`. "Slutrapport" = `docs/stabilitet-2026-11/SLUTRAPPORT.md`. **Ocommittat** = finns i arbetskatalogen 2026-11-17 men är inte committat eller driftsatt. Vem: **Ä** = Anton, **S** = Sebbe, **A** = agent.

**Tillägg 2026-11-18.** Det som var ocommittat (INV-AI-001, INV-AVTAL-001, INV-DATA-004) är mergat till `development` (PR 45) och kör i testmiljön, men är inte släppt till `main`; release-PR 60 väntar på ägarens merge. Det räknas som delvis. "PR n" = pull request n i repot. "Underlag" = `../../underlag/` (osignerade utkast). "bevis/konf-efter" = `../../bevis/railway-konfiguration-2026-11-17-efter.txt`. **Markering:** Status-cellen säger "ändr. 11-18" där bevis eller gap ändrats 2026-11-18, och "var X" där statusen ändrats.

---

## Klausul 4: Context of the organization

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **4.1** Understanding the organization and its context | AI Organizational Context, MSA, NS, SGR | P07, P20 · AI Context Register, Separation of Environments, Production Firewall | **delvis** | Bolaget och AI-flödena beskrivna (Inv. §2, DPIA §1, IA "Behandlingen"); rollerna leverantör och användare bedömda i `ai-forordningen.md` (utkast) | Ingen beslutad kontextbeskrivning för AI: syfte per system, Snajps roll, interna och externa förhållanden | A, Ä |
| **4.2** Needs and expectations of interested parties | AI Interested Parties, U | P27 · Stakeholder Register | **delvis** | Kunderna (villkor, pilotavtal), kundernas kunder (DPIA), prospekten (IA), IMY och leverantörerna (Lev.) finns beskrivna var för sig | Inget intressentregister med krav och hur AI-ledningssystemet svarar på dem | A, Ä |
| **4.3** Determining the scope of the AI management system | AIMS Scope Definition | P27 · AIMS Scope Statement | **saknas** · ändr. 11-18 | inget beslutat. Beslutsutkast Underlag `beslut/e-omfattning-ledningssystem.md` | Omfånget är inte beslutat; utkastet osignerat. Förslag i P27 | Ä |
| **4.4** AI management system | AI Management System Establishment, SOP | P19, P21 · AIMS Manual, Separation of Environments | **saknas** | Den här mappen är första steget | Inget beslutat ledningssystem för AI: ingen godkänd policy, ingen riskmetod, ingen uppföljning | Ä |

## Klausul 5: Leadership

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **5.1** Leadership and commitment | AI Leadership Commitment, SOP | P27, P19, P21 · AI Leadership Commitment Record | **delvis** | Anton fattar AI-beslut med skäl: DeepSeek-spärren (`CLAUDE.md`), belägg eller överlämning (BESLUT 101-158), ingen behandling utanför EU-regionen (BESLUT 2095-2098) | Inget skrivet åtagande, ingen godkänd AI-policy, inga AI-mål, inga avsatta resurser | Ä |
| **5.2** Policy | AI Policy, SOP | P27 · Public Policies | **saknas** | Bara utkastet P27 | Ingen AI-policy med ramverk för mål och åtaganden om efterlevnad och förbättring | Ä |
| **5.3** Organizational roles, responsibilities and authorities | AI Org. Roles, AR, U | P27, P11, P12, P15 · AI MS Roles & Responsibilities, Access Review Log, Employee Access | **saknas** · ändr. 11-18 | inget belägg för AI-ledningssystemet. Anton är ensam code owner (`.github/CODEOWNERS`). Beslutsutkast om ansvar och systemägare: Underlag `beslut/a-ansvarig-dataskydd-informationssakerhet.md` | Ingen har fått ansvaret; utkastet osignerat, systemägarna [FYLL]. Förslag i P27 | Ä |

## Klausul 6: Planning

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **6.1.1** Actions to address risks and opportunities | AI Risk and Opportunity Actions, DRP, SMD | P18, P25 · AI Risk and Opportunity Register | **delvis** | AI-risker identifierade: DPIA R1–R13, gaplistan (Inv. §7), risker i `import.json` här | Inga AI-riskkriterier (vad som är acceptabelt). Inget register över risker och möjligheter för själva ledningssystemet | Ä |
| **6.1.2** AI risk assessment | AI Risk Assessment, EP, RM, SIM | P09, G06, G03, P13, P14, P21 · AI Risk Assessment Execution (Log) | **delvis** | DPIA bedömer supportagentens risker för individer (R1–R13, uppdaterad 2026-11-17); IA för kallmejlen | Ingen metod som ger jämförbara resultat. Iris och Jev saknar en AI-riskbedömning utöver dataskyddet. Riskerna inte godkända | Ä, A |
| **6.1.3** AI risk treatment | AI Risk Treatment | P27 · AI Risk Treatment Implementation Record | **delvis** | Behandling finns i kod per risk: faktagrinden mot felaktiga svar (AI-inv. 336-375), maskering (`app/moderation/maskering.py`), autonomi fail-closed (`app/leads/autonomy.py:47-56`) | Ingen behandlingsplan, ingen jämförelse mot bilaga A, ingen Statement of Applicability för ISO 42001, restrisker inte accepterade | Ä |
| **6.1.4** AI system impact assessment | AI System Impact Assessment Process, U, NS | P27, P20 · AI System Impact Assessment Procedure | **delvis** | DPIA (supportagenten) och IA (kallmejl) bedömer följder för registrerade | Ingen beslutad process för konsekvensbedömning av AI-system. Jev saknar bedömning. Samhällsperspektivet saknas (A.5.5) | Ä, A |
| **6.2** AI objectives and planning to achieve them | AI Objectives and Planning, U, SOP | P27 · AI Objectives Register | **delvis** | Mätbara mål för agenterna: minst 30 evalfall per agent, svarstid p95 under 8 s (Slutrapport rad 82-87); facit för Iris (AI-inv. 943) | Målen är produktmål, inte AI-mål kopplade till en policy. Inget register med ansvarig, datum och uppföljning | Ä |
| **6.3** Planning of changes | AI Change Planning, CM, U | P27, P19, P21 · AI System Change Log, Code Changes | **delvis** · ändr. 11-18 | Modellbyten beslutas och mäts: pro→flash efter mätning (BESLUT 1647-1664); facit ändras bara med Antons ja (`CLAUDE.md`). `INKORG_JEV` återställd till `off` efter Antons beslut 2026-11-17 (bevis/konf-efter rad 95, 248). Beslutsutkast om godkännande av ny modell eller leverantör (Underlag `beslut/f-…`) | Ingen ändringslogg för AI-system. Vem som satte `INKORG_JEV=auto` mot Antons beslut 2026-09-30 är okänt (BU A2). Godkännandebeslutet osignerat. Gemini 2.5 har passerat Googles pensionsdatum 2026-10-20 utan planerat byte (`../../gemini-bedomning.md`) | Ä, A |

## Klausul 7: Support

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **7.1** Resources | AI Resources, EP, U | P27, P13, P14, P21 · AI MS Resource Allocation Record | **delvis** | Två personer; betald Vertex AI (Inv. §2.1) | Ingen tid eller budget avsatt för AI-styrningen: [FYLL: timmar per månad] | Ä |
| **7.2** Competence | AI Competence, DIS, PS | P28, P15, G05 · AI Competence Record, Employee Descriptions, Employee Verification | **saknas** · ändr. 11-18 | inget belägg. Utbildningsmaterial med AI-förordningen art. 4 som utkast (Underlag `utbildning/genomgang.md`) | Inga kompetenskrav för AI-arbetet och ingen förteckning. AI-förordningen art. 4 kräver AI-kunnighet sedan 2025-02-02 (`ai-forordningen.md`). Materialet är inte använt | Ä |
| **7.3** Awareness | AI Awareness, SOP | P27 · AI Awareness Program | **saknas** · ändr. 11-18 | inget belägg. Genomgång och kvittens som utkast (Underlag `utbildning/`) | Ingen AI-policy att känna till. Ingen genomgång med Sebbe hållen | Ä, S |
| **7.4** Communication | AI Communication, DP, U, RL | P27, G01, G02, G04, P24 · AI MS Communication Plan, Contact Information, Public Policies | **delvis** · ändr. 11-18 | Kundförklaringen av faktakontrollen (`docs/SA-FUNGERAR-FAKTAKONTROLLEN.md`); autonomins ansvar i villkoren (`app/villkor/VillkorSida.tsx:34-41`). I testmiljön: AI-upplysningen (INV-AI-001, PR 45) och integritetspolicyns avsnitt om AI-assistenten och vägen till en människa (PR 51) | Ingen plan för vad som sägs om AI, till vem och när. Upplysningen och texten inte i drift förrän PR 60 | A, Ä |
| **7.5.1** Documented information (General) | AIMS Documented Information, SOP | P08 · AIMS Documented Information Index | **delvis** | AI-inv. (alla med test), BESLUT, Evals, DPIA, `docs/UTKASTKEDJAN-REFERENS-2026-10-16.md` | Det standarden kräver (omfång, policy, riskbedömning, SoA, konsekvensbedömning, revision) finns inte eller bara som utkast | A, Ä |
| **7.5.2** Creating and updating | AIMS Documented Information | P08 · AIMS Documented Information Index | **delvis** | Git ger historik; BESLUT och invarianterna är daterade | `docs/compliance/` saknar versionshistorik. Inget godkännande av något AI-styrdokument | A, Ä |
| **7.5.3** Control of documented information | AIMS Documented Information | P08, G02 · AIMS Documented Information Index | **delvis** | Känsliga utkast utanför git | Repot är publikt (BU A1): prompter, grindar och kända svagheter i AI-kedjan är läsbara för alla | Ä |

## Klausul 8: Operation

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **8.1** Operational planning and control | AI Operational Planning and Control, CM, U, SMD | P27, P19, P25 · AI MS Operational Control Procedure, AI Context Register | **delvis** · ändr. 11-18 | Kriterier i kod: autosvar bara vid regel `auto`, säkerhet, sentiment, textkvalitet och faktagrind (`email_pipeline/processor.py:752-759`); modellen kan inte skicka (AI-inv. 137); sändspärrarna (`app/leads/send_guard.py`) | Externa AI-tjänster styrs fortfarande inte av en beslutad procedur: Jev fick kundmejl utan beslut (BU A2), nu stoppat i drift (bevis/konf-efter rad 95, 248). Spärren mot AI Studio (INV-DATA-004, PR 45) kör bara i testmiljön tills PR 60 mergas. Godkännandebeslutet `beslut/f-…` osignerat. EU-grindar för modellanrop byggs i en PR som inte är mergad | Ä, A |
| **8.2** AI risk assessment | AI Risk Assessment, U, SIM, SMD | P27, G03, P25 · AI Risk Assessment Execution (Log) | **delvis** | DPIA och IA omgjorda 2026-11-17 efter ändringar | Inget intervall och ingen utlösare beslutad. Volymhöjningen till 100 per dag (BESLUT 161-224) gjordes utan ny bedömning | Ä |
| **8.3** AI risk treatment | AI Risk Treatment, U | P27 · AI Risk Treatment Implementation Record | **delvis** | Åtgärderna provas: injektionsfallen 1 av 5 → 0 av 5 (Slutrapport rad 33); invarianttester i CI | Ingen godkänd plan att genomföra eller följa upp mot | Ä, A |
| **8.4** AI system impact assessment | AI System Impact Assessment Process, U, NS | P27, P20 · AI System Impact Assessment Procedure | **delvis** | DPIA uppdaterad 2026-11-17 | Inget intervall. Jev och webbpoolens bedömning av bolags webbplatser saknar bedömning | Ä, A |

## Klausul 9: Performance evaluation

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **9.1** Monitoring, measurement, analysis and evaluation | AI Performance Monitoring…, RCM, SMD | P18, P25 · Monitoring & Alerting, App Availability | **delvis** · ändr. 11-18 | Evalsviter före och efter ändring (Evals; resultat i `docs/stabilitet-2026-11/eval/`); stilgrindens mätning av utkast (BESLUT 1654-1659); webbfacit med grind 85 % (`CLAUDE.md` regel 18). Driftövervakning av produktionens hälsokontroller med provad larmkedja (`overvakning.yml`, PR 50; `../iso27001/matris.md` A.8.16) | Övervakningen mäter tillgänglighet, inte AI-kvalitet. Ingen löpande mätning av svaren i drift. Internlarmen saknar variabler i båda miljöerna. Ingen utvärdering av ledningssystemet | Ä, A |
| **9.2.1** Internal audit (General) | AI Internal Audit, U, MSA, SGR, SOP | P10, P07 · AI Internal Audit Reports, AI MS Internal Audit Program | **saknas** | inget belägg | Ingen internrevision | Ä |
| **9.2.2** Internal audit (programme) | AI Internal Audit, U, MSA, SGR, SOP | P10 · AI Internal Audit Reports, AI MS Internal Audit Program | **saknas** | inget belägg | Inget revisionsprogram. Oberoende kräver en tredje person (P10) | Ä |
| **9.3.1** Management review (General) | AI Management Review, MSA, SGR | P07, P10 · AI Management Review Minutes | **saknas** | inget belägg | Ingen ledningens genomgång | Ä |
| **9.3.2** Management review inputs | AI Management Review, MSA, SGR | P07, P10 · AI Management Review Minutes | **saknas** | inget belägg | Som 9.3.1 | Ä |
| **9.3.3** Management review results | AI Management Review, MSA, SGR | P07, P10 · AI Management Review Minutes | **saknas** | inget belägg | Som 9.3.1 | Ä |

## Klausul 10: Improvement

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **10.1** Continual improvement | AI Continual Improvement, U, MSA, SGR, SOP | P27, P07 · AI MS Continual Improvement Log | **delvis** | Förbättringar mäts före och efter (Slutrapport rad 30-41); beslut med skäl i BESLUT | Förbättrar agenterna, inte ledningssystemet. Ingen förbättringslogg | Ä |
| **10.2** Nonconformity and corrective action | AI Nonconformity and Corrective Action, SIM | G03 · Incident Response | **delvis** | Starkt mönster: varje AI-fel blir en invariant med orsak och test som bevisligen fäller, t.ex. påhittade 30 % (AI-inv. 328-331), påhittade bolag (AI-inv. 885-889), injektion som lovade rabatt (Slutrapport rad 144) | AI-fel förs inte in i incidentloggen (promptläckan saknas där, Inv. §3). Ingen uppföljning av att åtgärden räckte, utöver testet | Ä, A |

---

## A.2 Policies related to AI

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.2.2** AI Policy | AI Policy, U | P27 · Public Policies | **delvis** | Beslutade regler finns, men spridda: DeepSeek får inte se kunddata (`CLAUDE.md`, spärr i `snajp-support/app/config.py:609-700`), leadsreglerna 1–22 (`CLAUDE.md`), belägg eller överlämning (BESLUT 101-158) | Ingen samlad AI-policy. P27 samlar dem som utkast | Ä |
| **A.2.3** Alignment with other organizational policies | AI Policy Alignment…, U | P27 · AI Policy Alignment Review | **saknas** | inget belägg | Ingen genomgång mot G01–G06 och P07–P26 | A, Ä |
| **A.2.4** Review of the AI policy | AI Policy Review, U | P27 · AI Policy Review | **saknas** | inget belägg | Ingen policy att se över; intervall förslås i P27 | Ä |

## A.3 Internal organization

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.3.2** AI roles and responsibilities | AI Org. Roles, U | P27 · AI MS Roles & Responsibilities | **delvis** · ändr. 11-18 | Ansvar syns i praktiken: Anton beslutar modellval och facit (BESLUT 2068-2098), Sebbe beslutar leadsreglerna 10, 11 och 22 (`CLAUDE.md`). Beslutsutkast a och f (Underlag `beslut/`) | Inga AI-roller tilldelade; utkasten osignerade. Vem som får slå på en modelleverantör är oklart tills beslut f är signerat (BU A2) | Ä |
| **A.3.3** Reporting of concerns | AI Concern Reporting | P27, P28 · Contact Information | **saknas** | inget belägg | Ingen väg för Sebbe eller en framtida anställd att anmäla oro om AI-användningen | Ä |

## A.4 Resources for AI systems

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.4.2** Resource documentation | AI Resource Documentation | P27 · AI MS Resource Allocation Record | **delvis** | Modeller, regioner och leverantörer i Inv. §2 och `../../leverantorer.json` | Utkast från en agent, inte granskat. Ingen förteckning per AI-system och livscykelsteg | A |
| **A.4.3** Data resources | AI Data Resources, U | P27, G02 · AI Data Resource Register | **delvis** | Dataflöden per system: DPIA §1 (support), IA (leads), `docs/registerforteckning.md`, `snajp-support/app/leads/jev.py:22-28` | Inget dataregister per AI-system med känslighet, lagringstid och åtkomst | A |
| **A.4.4** Tooling resources | AI Tooling Resources, U | P27 · AI Tooling Inventory | **delvis** · ändr. 11-18 | Vendorade skills med sha256 och baseline (`agent-core/manifest.json`, AI-inv. 97-115); modellnamn i `snajp-support/app/config.py`; modellversioner och pensionsdatum utredda (`../../gemini-bedomning.md`) | Ingen förteckning med version, licens och godkännande per verktyg och modell. Gemini 2.5 har passerat Googles pensionsdatum 2026-10-20 men svarar ännu; ersättaren inte vald | A, Ä |
| **A.4.5** System and computing resources | AI System and Computing Resources, U | P27, P18 · App Availability | **delvis** · ändr. 11-18 | Vertex `europe-west1` (Inv. §2.1); Railway i Amsterdam (bevis/region) | Ogranskat; en replik per tjänst; Jev körs hos TypeSafe i USA (Lev. §7), sedan 2026-11-17 bara för leads | A, Ä |
| **A.4.6** Human resources | AI Human Resources | P15 · Employee Verification | **saknas** · ändr. 11-18 | inget belägg. Systemägare som [FYLL] i beslutsutkast a (Underlag `beslut/a-…`) | Ingen beskrivning av vem som utvecklar, driftsätter och övervakar respektive system och med vilken kompetens | Ä |

## A.5 Assessing impacts of AI systems

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.5.2** AI system impact assessment process | AI System Impact Assessment Process, U | P27 · AI System Impact Assessment Procedure | **delvis** | Som 6.1.4 | Som 6.1.4 | Ä, A |
| **A.5.3** Documentation of AI system impact assessments | AI SIA Documentation | P27 · AI Impact Assessment Log | **delvis** | DPIA och IA, daterade med ändringslogg | Utkast, ogranskade av jurist. Lagringstid för bedömningarna inte bestämd | Ä |
| **A.5.4** Assessing AI system impact on individuals and groups | Assessing AI System Impact on Individuals…, U | P27, G04 · AI Impact Assessment Log | **delvis** | Kundernas kunder (DPIA R1–R13), prospekt och VD (IA steg 3) | Jev saknas. Grupper (t.ex. små bolag som alltid hamnar i nivå C, språk annat än svenska som lämnas över) inte bedömda | Ä, A |
| **A.5.5** Assessing societal impacts of AI systems | Assessing Societal Impacts… , U | P27 · AI Societal Impact Assessment | **saknas** | inget belägg | Ingen bedömning av t.ex. mängden automatiska kallmejl eller jobb inom kundtjänst | Ä |

## A.6 AI system life cycle

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.6.1.2** Objectives for responsible development of AI system | Responsible AI Development Objectives | P27 · Responsible AI Development Objectives | **delvis** | Antons krav 2026-11-16: "det måste gå att lita på den till hundra procent, är den inte hundra procent säker måste den eskalera" (BESLUT 107-108); modellen kan inte skicka (AI-inv. 137) | Inga nedskrivna mål med mått, ansvarig och godkännande | Ä |
| **A.6.1.3** Processes for trustworthy AI system design and development | Trustworthy AI D&D Processes | P20, P19 · Code Changes | **delvis** | Starkt: "an invariant without a test is not an invariant", CI fäller bygget (AI-inv. 7-10); beslut med skäl (BESLUT 3-8); facit ändras bara med Antons ja (`CLAUDE.md`) | Ingen AI-specifik granskning av risk, etik och efterlevnad vid ändring av modell eller prompt. `development` deployas utan granskning | Ä, A |
| **A.6.2.2** AI system requirements and specification | AI System Requirements and Specification, U | P27 · AI System Requirements and Specification | **delvis** | Krav som invarianter och leadsregler (`CLAUDE.md` regel 1–22) | Inget kravdokument per system som täcker syfte, mänsklig tillsyn och regelkrav. Inget godkänt | A, Ä |
| **A.6.2.3** Documentation of AI system design and development | AI System D&D Documentation | P20 · AI Design and Development Documentation | **delvis** | Iris kedja steg för steg (`docs/UTKASTKEDJAN-REFERENS-2026-10-16.md` §5); insynsvyn byggd ur samma objekt som prompten (`snajp-support/app/agentcore/insyn.py:11-20`) | Supportagenten och Jev saknar designdokument. Kända begränsningar inte samlade | A |
| **A.6.2.4** AI system verification and validation | AI System V&V, U | P27, P20 · AI Verification & Validation Report | **delvis** | Evalsviter med mekanisk bedömning och 33–50 fall (Evals; Slutrapport rad 30-41); facit för Iris (AI-inv. 927-957); webbfacit 85 % | Ingen godkänd gräns för när en ändring får gå till main. Jev i inkorgen saknar svit. Ordagrant inte mätt (BESLUT 134-135) | A, Ä |
| **A.6.2.5** AI system deployment | AI System Deployment, U | P27, P19 · Code Changes | **delvis** | Release till `main` via PR med code owner (`CLAUDE.md`); modellbyten via miljövariabel med beslut (BESLUT 1661-1664) | Ingen driftsättningsplan med AI-krav (t.ex. evalsvit grön före release). Miljövariabler som byter AI-beteende ändras utan logg | Ä |
| **A.6.2.6** AI system operation and monitoring | AI System Operation and Monitoring, U | P27, P25 · AI System Operation & Monitoring Plan, Monitoring & Alerting | **delvis** · ändr. 11-18 | Kreditslut larmas (AI-inv. 508-550); leveransstopp vid studs och klagomål (`send_guard.py:68-79`); jobbens tillstånd i liggaren (AI-inv. 910). Driftövervakning av hälsokontrollerna, som också kontrollerar att jobbkön svarar (`overvakning.yml`, PR 50) | Internlarmets variabler saknas i drift. Ingen mätning av svarens kvalitet eller avvikelser i produktion | Ä, A |
| **A.6.2.7** AI system technical documentation | AI System Technical Documentation, U | P27 · AI System Technical Documentation (Model Card) | **delvis** | Kundförklaringen (`docs/SA-FUNGERAR-FAKTAKONTROLLEN.md`, avsnittet om vad som inte lovas) | Ingen teknisk dokumentation per system för kund och tillsyn: syfte, modeller, begränsningar, mätresultat | A |
| **A.6.2.8** AI system recording of event logs | AI System Event Logging, U | P27, P25 · AI System Event Logging Configuration | **uppfyllt** · ändr. 11-18 | Varje körning loggas med alla tre instruktionslagren (AI-inv. 394-404, test `tests/agentcore/test_overlays.py`); anrop utanför stegmotorn, också Jev, loggas (`insyn.py:56-86`); beslut i `ss_decision_log` (`email_pipeline/processor.py:716-719, 743-750`) | Kravet är uppfyllt för loggningen. Lagringstid och åtkomst saknas: `agent_runs` sparar fulla prompter utan gallring (DPIA R10). Gallringen som anonymiserar dem är byggd (PR 48) men avslagen och inte i `main`. Det hör till G02 och P25 | A, Ä |

## A.7 Data for AI systems

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.7.2** Data for development and enhancement of AI system | Data for AI Development and Enhancement | G02 · AI Data Resource Register | **delvis** | Snajp tränar inga modeller. Utvecklingsdata är facit och evalfall (`snajp-support/evals/`, `tests/leads/fixtures/`); agenten ändrar aldrig själv sitt underlag (AI-inv. 571-587) | Ingen beslutad process. Evalsviten för support bygger på en riktig kunds kunskapsbas (`evals/kb/livrustning.json`). AI-kodverktyg läser development-spegeln (Inv. §7 #29) | Ä, A |
| **A.7.3** Acquisition of data | AI Data Acquisition, U | P27, G04 · AI Data Acquisition Record | **delvis** | Varje prospektfaktum har källa, datum och laglig grund, `NOT NULL` i databasen (AI-inv. 117-125); LinkedIn aldrig första källa (AI-inv. 127-135); registrets personsidor används inte (`CLAUDE.md` regel 6) | allabolag och hitta hämtas utan avtal (Inv. §6.3 #10). Ingen samlad förteckning över källor | Ä |
| **A.7.4** Quality of data for AI systems | AI Data Quality | G02 · AI Data Quality Assessment | **delvis** | Bolag som inte går att styrka blir aldrig lead (AI-inv. 863-891); bara ordagrant verifierade citat räknas (AI-inv. 377-392); kunskapsbasens artiklar får källa och giltighetstid (BESLUT 143-146) | Inga nedskrivna kvalitetskrav per system. Vektorerna i kunskapsbasen inte ifyllda (BESLUT 156-157) | A |
| **A.7.5** Data provenance | AI Data Provenance | G02 · AI Data Provenance Record | **delvis** · ändr. 11-18 | Leadsdelen uppfyller kravet: AI-inv. 117-125. Supportsvarens belägg sparas per uppgift (AI-inv. 336-352); svarscachen är en funktion av KB-version (AI-inv. 679). Kunskapsbasens källfält (migration 117) körd i testmiljön | Migration 117 inte i `main` förrän PR 60 | A |
| **A.7.6** Data preparation | AI Data Preparation | G02 · AI Data Preparation Record | **delvis** · ändr. 11-18 | Personnummer maskeras före Vertex (`moderation/maskering.py`) och, i testmiljön, före Jev (`jev.py:47`, PR 45); personer och nummer bort ur registerfakta (`CLAUDE.md` regel 9); opålitlig text ramas in (AI-inv. 219-228, 293-317) | Maskeringen före Jev inte i drift förrän PR 60. Hälsouppgifter i löptext maskeras inte (DPIA R1). Maskering före inbäddningar byggs i en PR som inte är mergad. Ingen dokumenterad förberedelse per system | A |

## A.8 Information for interested parties of AI systems

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.8.2** System documentation and information for users | AI System Documentation and Information for Users, U | P27, G04 · Public Policies | **delvis** · ändr. 11-18 | Villkoren beskriver agenterna och autonomin (`VillkorSida.tsx:17-41`); textmall för kundens art. 13-information (`docs/kundmall_informationstext.md`). I testmiljön: AI-upplysning i chattens huvud och i ogranskade mejlsvar (INV-AI-001, PR 45), och policyns avsnitt om AI-assistenten (PR 51) | Upplysningen inte i drift förrän PR 60. Ingen information till prospekten om att Iris skrev mejlet | Ä (merge), A |
| **A.8.3** External reporting | AI External Reporting | G01, G04 · Public Policies | **delvis** · ändr. 11-18 | `kontakt@snajp.se` publik (Inv. §3 P0.3d); den som ber om en människa får en (AI-inv. 746-776), i mejl eskalerat av koden i testmiljön (PR 60); avregistrering i varje kallmejl (`send_guard.py:246-271`); `SECURITY.md` och `security.txt` för säkerhetsrapporter (PR 50, testmiljön) | Ingen uttalad väg för att anmäla skada eller fel från AI:n, och inga anmälningar loggas. `SECURITY.md` gäller säkerhetsbrister, inte AI-fel | Ä, A |
| **A.8.4** Communication of incidents | AI Incident Communication, U | G03 · Incident Response | **delvis** | Underrättelse till kund vid personuppgiftsincident (`INCIDENT_RESPONSE.md:60-71`) | AI-incidenter utan persondata (fel autosvar, påhittat utkast som gått ut) täcks inte | Ä |
| **A.8.5** Information for interested parties | Information for Interested Parties | G01 · Public Policies | **delvis** | Skyldigheterna enligt AI-förordningen kartlagda (`ai-forordningen.md`, utkast) | Ingen beslutad lista över vad Snajp måste rapportera, till vem | Ä |

## A.9 Use of AI systems

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.9.2** Processes for responsible use of AI systems | Responsible AI Use Processes | P27, P13 · Responsible AI Use Procedure | **delvis** | Iris standard är utkast, okänd nivå blir utkast (`autonomy.py:18-20, 47-56`); de tre första utskicken granskas av människa (Inv. §6.2); supportagenten levereras med granskning på för alla kategorier (`VillkorSida.tsx:38-40`) | Ingen procedur för Snajps egen användning av AI, t.ex. AI-kodverktyg som läser kunddata (Inv. §7 #29) | Ä |
| **A.9.3** Objectives for responsible use of AI system | Responsible AI Use Objectives | P27 · Responsible AI Use Objectives | **delvis** | Belägg eller överlämning (BESLUT 101-110); "inget hamnar i skräpposten" som styrde utskickstakten (BESLUT 168-169, 190-191) | Inga nedskrivna mål med mått | Ä |
| **A.9.4** Intended use of the AI system | Intended Use of AI System | P27 · Intended Use Statement | **delvis** | Villkoren beskriver vad agenterna gör (`VillkorSida.tsx:17-19`) | Ingen avsedd användning med förbjudna användningar, t.ex. beslut om kredit, anställning eller försäkring (`ai-forordningen.md` §3) | Ä |

## A.10 Third-party and customer relationships

| Krav | Kontroll(er) | Policy · uppgifter | Status | Bevis | Gap | Vem |
|---|---|---|---|---|---|---|
| **A.10.2** Allocating responsibilities | AI Third-Party Responsibility Allocation, U | P27, G06 · AI Third-Party Responsibility Matrix | **delvis** | Kunden ansvarar för autonominivån och art. 13-informationen (`VillkorSida.tsx:30-41`); pilotavtalets §5 (`docs/pilotavtal.md:83-113`, utkast) | Ingen fördelning över livscykeln mellan Snajp, Google, TypeSafe och kunden. Villkoren ogranskade | Ä |
| **A.10.3** Suppliers | AI Suppliers, U | P27, G06, P26 · AI Supplier Register | **delvis** · ändr. 11-18 | Vertex och TypeSafe granskade med källor (Lev. §1, 2, 7); Gemini-bedömningen (`../../gemini-bedomning.md`). TypeSafe får inte längre kundmejl (bevis/konf-efter rad 95, 248). Beslutsutkast om godkännande av ny modell eller leverantör (Underlag `beslut/f-…`) | Godkännandeprocessen osignerad. TypeSafe är röd och får fortfarande leadsdata; raderingsbegäran för kundmejlen inte skickad. Gemini 2.5 har passerat pensionsdatumet | Ä |
| **A.10.4** Customers | AI Customers, U | P27 · Contact Information | **delvis** | Kundens krav styr: autonomi per kategori, facit efter kundens granskning (AI-inv. 927-957), produktmatchning efter Sebbes krav (AI-inv. 876-881) | Ingen dokumenterad process för att fånga kundernas förväntningar på AI:n | Ä |

---

## Summering

| Status | 2026-11-17 | 2026-11-18 | Krav 2026-11-18 |
|---|---|---|---|
| Uppfyllt | 1 | 1 | A.6.2.8 |
| Delvis | 53 | 53 | 4.1, 4.2, 5.1, 6.1.1, 6.1.2, 6.1.3, 6.1.4, 6.2, 6.3, 7.1, 7.4, 7.5.1, 7.5.2, 7.5.3, 8.1, 8.2, 8.3, 8.4, 9.1, 10.1, 10.2, A.2.2, A.3.2, A.4.2–A.4.5, A.5.2–A.5.4, A.6.1.2, A.6.1.3, A.6.2.2–A.6.2.7, A.7.2–A.7.6, A.8.2–A.8.5, A.9.2–A.9.4, A.10.2–A.10.4 |
| Saknas | 16 | 16 | 4.3, 4.4, 5.2, 5.3, 7.2, 7.3, 9.2.1, 9.2.2, 9.3.1, 9.3.2, 9.3.3, A.2.3, A.2.4, A.3.3, A.4.6, A.5.5 |
| Ej tillämpligt | 0 | 0 | – |
| Okänt | 0 | 0 | – (frågorna till ägaren nedan påverkar statusen på 7.1, 7.2, A.3.2 och A.4.6) |

**Förändring 2026-11-18:** ingen statusändring; uppfyllt 1 → 1, delvis 53 → 53, saknas 16 → 16. Bevis eller gap ändrades i 19 krav: 4.3, 5.3, 6.3, 7.2, 7.3, 7.4, 8.1, 9.1, A.3.2, A.4.4, A.4.5, A.4.6, A.6.2.6, A.6.2.8, A.7.5, A.7.6, A.8.2, A.8.3, A.10.3. Det viktigaste i drift är att Jev inte längre läser kundmejl. Det mesta övriga (AI-upplysningen, AI Studio-spärren, maskeringen före Jev) kör i testmiljön och väntar på PR 60. De saknade kraven är formella (policy, roller, omfång, utbildning, revision) och flyttas bara av Antons signaturer, inte av kod.

Inget krav är ej tillämpligt. Snajp tränar inga modeller, men bilaga A.7 gäller ändå data som AI-systemen använder i drift och i utveckling (facit, evalfall, kunskapsbaser).

Bilden är tydlig åt båda håll. Den tekniska styrningen är ovanligt stark för ett bolag med två personer: AI-felen har blivit invarianter med tester som körs i CI, modellen kan inte skicka eller välja kund, osäkra svar lämnas över, och modellbyten mäts innan de beslutas. Det räcker för ett krav (loggningen), och de flesta delvis-raderna i bilaga A.6 och A.7 har belägg i kod som en revisor kan läsa. Det som saknas är det formella runt omkring: ingen AI-policy, inga roller, inget omfång, ingen konsekvensbedömning som process, ingen revision. Det farligaste gapet är ändå ett styrningsfel i drift, inte ett dokument: Jev började läsa kundmejl utan att någon beslutat det, mot ett uttryckligt beslut (BU A2). Det är precis den sortens händelse en godkännandeprocess för modeller ska stoppa.

### Tio åtgärder som flyttar flest krav till uppfyllt

1. **Anton godkänner P27 (AI-policyn) med omfång och roller.** Flyttar 4.3, 4.4, 5.1, 5.2, 5.3, A.2.2, A.3.2 och, efter genomgång med Sebbe, 7.3. Ä.
2. **Godkännande av modeller och modelleverantörer (P27 avsnitt 6) och stopp för Jev i inkorgen** (`INKORG_JEV=off`, BU A2). Flyttar A.10.3, 6.3, 8.1 och ger belägg till A.6.2.5. Ä, A på ja. *Läge 2026-11-18: Jev stoppad i drift. Kvar: signera `beslut/f-…`, välja ersättare för Gemini 2.5.*
3. **En konsekvensbedömning per AI-system** med en sida per system: individer, grupper och samhälle, med intervall och utlösare (DPIA och IA återanvänds för support och Iris, Jev får en ny). Flyttar 6.1.4, 8.4, A.5.2–A.5.5, och 6.1.2 och 8.2 med riskkriterierna i åtgärd 4. A skriver, Ä godkänner.
4. **AI-riskkriterier och en SoA för bilaga A** i samma riskregister som ISO 27001 (P09). Flyttar 6.1.1, 6.1.2, 6.1.3, 8.2, 8.3. Ä.
5. **Ett systemblad per AI-system:** syfte och avsedd användning, förbjudna användningar, krav, modeller, begränsningar, mätresultat, ansvarig. Flyttar A.6.2.2, A.6.2.3, A.6.2.7, A.9.4, A.4.2–A.4.5 och delar av A.8.2. A skriver, Ä godkänner.
6. **Evalsviten blir en releasegrind** med en beslutad lägsta nivå per agent, och Jev i leads får en egen svit. Flyttar A.6.2.4, A.6.2.5, A.6.1.3 och 9.1 (med åtgärd 7). A bygger, Ä beslutar gränsen.
7. **Larm och mätning i drift:** sätt internlarmets variabler, logga autosvar som fälls av faktagrinden och utkast som stoppas, och läs av dem varje månad. Flyttar A.6.2.6, 9.1 och uppgiften Monitoring & Alerting. Ä sätter variablerna, A bygger.
8. **AI-kunnighet och kompetens:** en kort genomgång för Anton och Sebbe av P27, AI-förordningen art. 4 och 50, och systembladen, med kvittens. Flyttar 7.2, 7.3, A.4.6 och uppfyller art. 4. Ä och S.
9. **Driftsätt AI-upplysningen och avtalsgrinden** (INV-AI-001, INV-AVTAL-001) och lägg en rad om AI-fel i incidentrutinen och en anmälningsväg på sajten. Flyttar A.8.2, A.8.3, A.8.4, 10.2 och A.3.3 (tillsammans med P28). Ä godkänner, A gör. *Läge 2026-11-18: mergat till development och kör i testmiljön. Driftsättningen är Antons merge av PR 60.*
10. **Första ledningens genomgång och en extern granskning** efter tre månader. Flyttar 9.3.1–9.3.3, 10.1, A.2.3, A.2.4 och, med en extern granskare, 9.2.1 och 9.2.2. Ä.

### Uppgifter jag behöver från ägaren

1. **Vem satte `INKORG_JEV=auto` i main, och när?** (Jev är avstängd för kundmejl sedan 2026-11-17; frågan om vem står kvar.)
2. **Roller:** vem äger respektive AI-system (support, Iris, Jev)? Får Sebbe besluta om modellbyten och leadsregler utan dig, som han gjort (regel 10, 11, 22)?
3. **Kompetens:** vilken utbildning eller erfarenhet av AI och dataskydd har du och Sebbe? Finns intyg?
4. **Resurser:** hur många timmar i månaden läggs på AI-styrningen, och finns budget för jurist och extern granskning?
5. **Autonomi i drift:** vilka kunder har satt supportkategorier på automatiskt svar, och vilka har Iris på `first_contact` eller `meeting`? Är `SEND_QUEUE_POLL_SECONDS` och `LEADS_AUTOPILOT` påslagna i main (BESLUT 2415-2418)?
6. **Kundernas branscher:** använder eller planerar någon kund supportagenten inom bank, försäkring, bemanning, vård eller offentlig sektor? Det avgör om riskklassen kan ändras (`ai-forordningen.md` §3).
7. **AI-kodverktyg:** vilka används (Claude Code, Codex, andra), med vilka avtal, och ska de få läsa development-spegeln med riktig kunddata?
8. **Evalsvitens kunskapsbas:** har Livrustning godkänt att deras kunskapsbas används som testdata (`evals/kb/livrustning.json`)?
9. **TypeSafe:** vilka villkor accepterades när kontot skapades (Lev. §7)?
