# Systemblad: Iris (leadsagenten)

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning: `README.md` i samma mapp. "AI-inv." =
`ARCHITECTURE_INVARIANTS.md`. "Bevis" = `docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`.
"IA" = `docs/intresseavvagning_kallmejl.md`. Sökvägar under `app/` avser
`snajp-support/app/` om inget annat anges.

## 1. Syfte och avsedd användning

**Vad den gör.** Iris söker bolag som passar kundens målgrupp, bedömer dem mot
kundens kriterier (Iris-profilen) till nivå A, B eller C med motivering,
researchar bolagets egen webbplats och skriver ett första kallmejl. Mejlet
köas; om och när det skickas avgörs av kundens autonominivå och av
sändspärren i kod (`app/villkor/VillkorSida.tsx:18, 43`;
`app/leads/autonomy.py:8-24`; `app/leads/send_guard.py`).

**För vem.** Snajps kunder som säljer till andra bolag. Mottagarna är bolag,
via adresser som bolaget självt publicerat (IA rad 145-150; `CLAUDE.md`
leadsregel 10, 12-13).

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad policy):

- Bedömning av fysiska personer. Iris bedömer bolag; enskilda firmor fälls
  före research när org.nr är känt (`app/leads/forfilter.py:30-44`;
  `docs/compliance/ramverk/iso42001/ai-forordningen.md:56`).
- Val av kandidater till anställning. Platsannonser läses bara som köpsignal
  (`ai-forordningen.md:57`).
- Kreditbedömning. Omsättning och storlek är filter för vilka bolag som
  kontaktas (`ai-forordningen.md:58`).
- Kontakt med privatpersoner eller via registrets personsidor (`CLAUDE.md`
  leadsregel 6), och registrets personer som kontakt (leadsregel 1 och 3).
- Utskick utan avregistrering, avsändare eller art. 14-information vid
  personlig adress: spärren blockerar dem (`send_guard.py:198-282, 345-374`).

## 2. Design

### 2.1 Kedjan per körning (`app/leads/korning.py:sokrunda`, rad 135-208)

| # | Steg | AI? | Kod | Fail-closed |
|---|---|---|---|---|
| 1 | Kandidater ur registret (filter) och, om det inte räcker, grundad Google-sökning | Gemini med Google Search | `app/leads/discovery.py:hitta_bolag` rad 1693, `_gemini_med_sokning` rad 495 | Sökfel kastar `DiscoveryError` (`korning.py:139-140`) |
| 2 | Förfilter: uteslutna domäner, enskild firma | Nej | `forfilter.py:41`; `korning.py:166-170` | Fäller |
| 3 | Existensgrind: bolaget styrks av sin egen webbplats | Nej | `app/leads/existens.py:56`; `korning.py:171-179`; INV-LEADS-EXIST-001 (AI-inv. 869-897) | Osäkert fäller |
| 4 | Webbpoolen får bolagsnivån | Bild (se `webbrevision.md`) | `korning.py:182-184` | – |
| 5 | Jev-triage | Jev | `korning.py:186-203`; `jev.md` | Av i `main`; fel släpper kandidaten vidare |
| 6 | Research på bolagets sajt; bara ordagrant verifierade citat räknas | Gemini | `app/agent/leads_research_v2.py:_research_v2` rad 338; `app/leads/bedomning.py:56` | Utan källmaterial inget modellanrop, nivå C (AI-inv. 876-880) |
| 7 | Bedömning: nivå och kvalificering räknas i kod ur utslagen per kriterium | Kod på modellens utslag | `bedomning.py:284`; INV-LEADS-SCORE-001, INV-LEADS-PROFIL-001 (AI-inv. 845-867) | Utslag utan citat räknas som okänt |
| 8 | Jev-klassning efter research (bara för jämförelse) | Jev | `leads_research_v2.py:609` | Påverkar inte nivån (`app/leads/jev.py:226-227`) |
| 9 | Kontakt: adress på bolagets sajt | Nej | `discovery.py:hamta_person_kontakt` rad 1289, `mottagare` rad 992 | Ingen adress: inget Iris-lead |
| 10 | Utkast: skriv, personalisera ingången, stilgrind, humanizer sist, stilgrind igen | Gemini | `leads_research_v2.py:run_outreach_draft_v2` rad 1083; `docs/UTKASTKEDJAN-REFERENS-2026-10-16.md:170-187`; `app/leads/outreach_playbook.py:123-213` | Högst två omskrivningsvarv |
| 11 | Faktagrind och gissningsgrind på exakt ämnesrad och brödtext | Nej | `leads_research_v2.py:1590-1594`; INV-GROUND-001, -004 (AI-inv. 319-335, 377-392) | Ostött påstående: en reparation, annars överlämning |
| 12 | Köning, med stilflaggor synliga för granskaren | Nej | `leads_research_v2.py:1613-1619` | – |
| 13 | Autonomi: köa, skicka eller hålla | Nej | `autonomy.py:59-95` | Okänt värde blir `draft` (rad 47-56) |
| 14 | Sändspärren vid sändtillfället: avsändare, avregistrering, spärrlista, art. 14, volym, kontorstid, karens, leveransstopp, de tre första granskas | Nej | `send_guard.py:172` och regel 1-6 (rad 198-523); IA rad 202-232 | Blockerar, köar om eller skickar till granskning |
| 15 | Bara schemaläggaren skickar; modellen har inget sändverktyg | Nej | `app/leads/scheduler.py:process_due_item` rad 368; INV-SEC-004 (AI-inv. 137-148) | – |

Iris-profilen kompileras ur kundens affärskontext med ett eget modellanrop
(`app/leads/profil.py:kompilera` rad 602, modellval rad 577).

### 2.2 Instruktionslager och opålitlig text

- Playbookstegen (`sa:draft-outreach`, `mk:cold-email`,
  `snajp:humanizer-svenska`) i `app/leads/outreach_playbook.py:43-70, 123-213`
  och researchstegen i `app/leads/research_playbook.py:33-46`. Tre lager per
  körning (INV-AUDIT-001).
- Text från prospektens sajter ramas in som opålitlig och står i
  användarposition (INV-SEC-003, AI-inv. 219-228).
- Facit för utkasten är låst (INV-LEADS-UTKAST-001 och -002, AI-inv.
  933-963). Facit ändras bara med Antons ja (`CLAUDE.md`).

## 3. Modeller och resurser per livscykelsteg

| Steg | Konfigfält | Standard i kod | I drift (main) | Plats |
|---|---|---|---|---|
| Research, bedömning, kontaktsökning | `model` | `gpt-4o-mini` (`config.py:288`) | `gemini-2.5-flash` (bevis rad 254) | Vertex AI `europe-west1` |
| Grundad sökning | `model` om den är Gemini, annars `gemini-2.5-flash` | `discovery.py:478` | `gemini-2.5-flash` | Vertex AI `europe-west1`, verktyget Google Search |
| Utkast | `leads_draft_model` | tom = `MODEL` (`config.py:420-429`) | Osatt, alltså `gemini-2.5-flash` | `vertex_utkast_region`, tom = huvudregionen (`config.py:274-281`) |
| Humanizer | `leads_humanizer_model` | tom = `MODEL` (`config.py:430-434`) | Osatt | Som utkastet |
| Iris-profilen | `iris_profil_model` | tom = `MODEL` (`config.py:435-438`) | Osatt | `europe-west1` |
| Webbplatsens bildbedömning | `vision_model` | `gemini-2.5-flash` | Osatt | Se `webbrevision.md` |
| Förfilter och klassning | `iris_jev` | `off` (`config.py:447-450`) | Osatt i `main`, alltså av; satt i `development` med okänt värde (bevis rad 97) | TypeSafe, USA. Se `jev.md` |
| Kedjans version | `leads_pipeline` | `v1` (`config.py:412-419`) | Satt i båda miljöerna, värdet syns inte (bevis rad 100, 251). Vilken kedja som kör är **inte belagt** | – |
| Tokenbudget per kund och dygn | `leads_daily_token_budget` | 2 000 000 (`config.py:456-462`) | Satt, värdet syns inte (bevis rad 98, 250) | – |

`gemini-2.5-pro` för utkasten togs bort 2026-10-21 på Antons beslut; stegen
ärver `MODEL` (`docs/BESLUT.md:2258-2275`).

**Var den körs.** Railway-tjänsten `api` (bevis rad 237), Amsterdam.
Bakgrundsjobb byter till reservregionerna `europe-west4,europe-north1` vid 429
(`config.py:253-258`).

**Livslängd.** Gemini 2.5 är pensionerad enligt Google (`README.md`). För
utkasten finns ingen godkänd ersättare: `gemini-3.8-flash` i `eu` föll på
kapacitet och `gemini-3.5-flash-lite` på stilgrinden
(`docs/compliance/modellbyte-underlag.md:599-605, 674-689`;
`docs/BESLUT.md:30-31`).

## 4. Data in och ut

| Anrop | Vad skickas | Maskering | Belägg |
|---|---|---|---|
| Research, bedömning, utkast | Prospektets publika sidor, bolagsfakta utan personer och nummer, kontaktnamn, kundens erbjudande och affärskontext | Ingen (publika B2B-uppgifter) | `gemini-bedomning.md:69`; `CLAUDE.md` leadsregel 9 |
| Grundad sökning | Målgrupp (bransch, ort, storlek), kundens kriterier i fritext, eller ett bolagsnamn. Ingen kundmejltext | Ingen | `gemini-bedomning.md:70`; INV-DATA-007 (bara `development`) |
| Jev | Se `jev.md` | E-post, telefon, personnummer | `app/leads/jev.py:77-80` |

**Hos Google:** sökgrundningens frågor sparas upp till tre dygn och det går
inte att stänga av (`gemini-bedomning.md:100`).

**Ut:** bedömning med poäng, nivå och motivering (INV-LEADS-SCORE-001), källa,
datum och laglig grund per prospektfaktum (INV-DATA-001, AI-inv. 117-125),
utkast i `send_queue`.

**Loggat:** fulla promptar i `agent_runs`, också sökningens
(`gemini-bedomning.md:73`); körningens tillstånd i `leads_job_ledger`
(INV-JOB-003, AI-inv. 916-931); sändspärrens beslut per utskick.

**Lagringstid för prospekt, kontakter och utskickshistorik: inte beslutad**
(IA rad 286-296). Avregistrerade adresser sparas i spärrlistan och överlever
radering (IA rad 291-292).

## 5. Mänsklig översyn

| Kontroll | Vad | Kod och test |
|---|---|---|
| Autonominivå per kund | `draft` (standard): inget skickas utan människa. `first_contact`: första mejlet går själv. `meeting`: beter sig som `first_contact` eftersom överlämningen saknar anropare. `auto_send`: kräver ICP, produktbeskrivning och avsändardomän | `autonomy.py:8-24, 34-40, 59-95, 107-147`; `snajp-support/tests/leads/test_autonomy.py` |
| Okänd nivå | Blir `draft` | `autonomy.py:47-56` |
| De tre första utskicken per kund | Granskas alltid av människa | `send_guard.py:503-523`; `tests/leads/test_send_guard.py` |
| Schemaläggaren för automatiska utskick | Av när `SEND_QUEUE_POLL_SECONDS` är 0; då går varje utkast till granskningskön | `config.py:514-518`; `app/agent/leads_tools.py:298` |
| Modellen kan inte skicka | Bara schemaläggaren | INV-SEC-004, `tests/leads/test_scheduler.py` |

**I drift 2026-11-18:** `SEND_QUEUE_POLL_SECONDS` och `LEADS_AUTOPILOT` står
inte i beviset för någon miljö. Alltså skickas inget Iris-mejl utan att en
människa godkänt det, oavsett kundens autonominivå. Anton har beslutat att
Iris ska sköta leads automatiskt inom kontots spärr (`docs/BESLUT.md:3007-3011`),
men att slå på variablerna i `main` väntar på hans ja (rad 3027-3030). IA:n
ska göras om när de slås på (IA rad 307-308).

## 6. Utvärdering

| Svit | Fall | Datum, miljö, modell | Utfall | Fil |
|---|---|---|---|---|
| `snajp-support/evals/iris_utkast.json` + `iris_rubrik.json` | 33 | 2026-11-10 före, development, 2.5-flash | 25/33; inga påhitt 93,9 %, skrivregler 87,9 % | `docs/stabilitet-2026-11/eval/fore-iris.json` |
| samma | 33 | 2026-11-10 efter | 24/33; inga påhitt 87,9 %, skrivregler 87,9 % | `…/eval/efter-iris.json` |
| samma, urval | 11 | 2026-11-18 kväll, development, 2.5-flash `europe-west1` | 7 godkända, 6 utan stilfynd, 2 tekniska fel (503) | `…/eval/modellbyte-dev-2026-11-18-iris-25flash.json` |
| samma, urval | 11 | 2026-11-18 kväll, development, 3.5-flash-lite `eu` | 4 godkända, 5 utan stilfynd, 0 tekniska fel | `…/eval/modellbyte-dev-2026-11-18-iris-35lite.json` |
| Utkastfacit | 12 + 7 utkast | låsta 2026-10-12 och 2026-10-16 | Testas i CI | INV-LEADS-UTKAST-001, -002 |

**Inte mätt:**

- Researchen, Jev och den grundade sökningen har ingen låst svit
  (`modellbyte-underlag.md:758-760`).
- Bedömningens träffsäkerhet (nivå A/B/C) mot ett facit: ingen svit hittad,
  inte belagt att en finns.
- Tonen och om ingången är den bästa möjliga (`snajp-support/evals/README.md:47-49`).
- Hur mottagarna uppfattar mejlen; svaren i oktober tydde på att de flesta
  hamnade i skräpposten (IA rad 164-168).

## 7. Kända begränsningar

- "dygnet runt" stod i 16 av 33 utkast fast erbjudandet aldrig sa det
  (`SLUTRAPPORT.md:160`).
- Utkasten konvergerar mot samma ingång (`UTKASTKEDJAN-REFERENS-2026-10-16.md:232-235`).
- Koncernbolag med få anställda passerar storleksfiltret (samma, rad 236-237).
- Enskilda firmor fälls bara när org.nr är känt (IA rad 195-198).
- I drift räknas en adress som personlig bara om lokaldelen har punkt eller
  bindestreck; rättningen är inte driftsatt (IA rad 181-194).
- Demolänkens spårning per mottagare är inte informerad (IA rad 172-180).
- 503 och 429 från Vertex tappar utkast (`modellbyte-underlag.md:698-700`).

## 8. Risker per AI-steg (bedömningsutkast)

Utkast av agenten. Påverkan på mottagarna bedöms i IA:n (steg 3, rad 141-200).

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| Grundad sökning | Påhittat bolag eller fel webbplats | Mejl till fel mottagare | Existensgrinden (INV-LEADS-EXIST-001) | Låg | nej (ägarens beslut) |
| Grundad sökning | Kunddata i sökfrågan, sparad hos Google i tre dygn | Överföring som inte går att återkalla | INV-DATA-007 (bara `development`); sökningen får bara målgrupp och kriterier | Låg | nej (ägarens beslut) |
| Research | Promptinjektion på prospektets sajt | Styrt utkast | Inramning (INV-SEC-003); modellen kan inte skicka (INV-SEC-004) | Låg | nej (ägarens beslut) |
| Bedömning | Fel nivå: bra bolag fälls eller dåligt kvalificeras | Förlorat lead, eller onödigt mejl | Nivån räknas i kod ur verifierade citat (INV-LEADS-PROFIL-001) | Inte mätt | nej (ägarens beslut) |
| Utkast | Påhittad siffra, kund eller fakta | Osant påstående i kundens namn | Faktagrind och gissningsgrind på exakt text (INV-GROUND-001, -004) | Låg; 9-10 av 10 utan påhitt i mätningen (`modellbyte-underlag.md:191`) | nej (ägarens beslut) |
| Utkast | Mallton, lika mejl | Läses som massutskick | Stilgrind och facit (INV-LEADS-UTKAST-002) | Medel | nej (ägarens beslut) |
| Utskick | Mejl utan mänsklig granskning | Fel mejl till ett bolag | Autonomi `draft` som standard; schemaläggaren av i drift; tre första granskas | Låg i dag; medel om autonoma utskick slås på | nej (ägarens beslut) |
| Utskick | Mottagaren vet inte att en AI skrivit mejlet | Möjlig brist mot art. 50.1 | Ingen upplysning i kallmejl; juristfråga (`ai-forordningen.md:66`) | Inte fastställd | nej (ägarens beslut) |
| Modellen | Google stänger Gemini 2.5 | Inga utkast | Ingen godkänd ersättare | Hög sannolikhet över tid | nej (ägarens beslut) |
