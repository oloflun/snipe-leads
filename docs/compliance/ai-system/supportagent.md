# Systemblad: supportagenten

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning och förkortningar: `README.md` i samma mapp. "AI-inv." =
`ARCHITECTURE_INVARIANTS.md`. "Bevis" = `docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`.

## 1. Syfte och avsedd användning

**Vad den gör.** Supportagenten läser kundens inkommande kundmejl och
chattmeddelanden, klassar ärendet, skriver ett svar grundat i kundens
kunskapsbas och lämnar över till en människa när underlag saknas
(`docs/dpia_supportagenten.md:67`). Svaret blir ett utkast som en människa
godkänner, utom i de ärendekategorier där kunden själv ställt om till
automatiskt svar (`app/villkor/VillkorSida.tsx:38-40`). I chatten svarar
agenten direkt.

**För vem.** Snajps kunder (företag) och deras kunder, som skriver till
kundtjänsten (`VillkorSida.tsx:18`; DPIA rad 71). Kunden är
personuppgiftsansvarig och Snajp biträde (DPIA rad 68-69).

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad
policy; villkoren saknar en sådan lista, `docs/compliance/ramverk/iso42001/ai-forordningen.md:38`):

- Beslut om kreditvärdighet, liv- eller sjukförsäkring, anställning eller
  offentliga förmåner för fysiska personer. Agenten bedömer inte personer; den
  kan svara på en fråga om ett villkor (`ai-forordningen.md:35, 38`).
- Utvärdering eller prioritering av nödsamtal (`ai-forordningen.md:36`).
  Agenten prioriterar kundtjänstärenden, inte nödärenden.
- Känsloigenkänning på biometrisk grund. Triagen läser ett sentimentvärde ur
  text (`snajp-support/app/email_pipeline/processor.py:756`), inget annat
  (`ai-forordningen.md:37`).
- Svar utan stöd i kundens kunskapsbas. Utan träff lämnas ärendet över
  (`processor.py:660-662`).

Om en kund inom bank, försäkring, bemanning, vård eller offentlig sektor
använder agenten är inte belagt (`matris.md:213`, fråga 6).

## 2. Design

### 2.1 Mejlvägen (`snajp-support/app/email_pipeline/processor.py:process_email`, rad 521)

| # | Steg | Kod | Vad som händer vid fel eller osäkerhet |
|---|---|---|---|
| 1 | Snajps egna larm sorteras bort | rad 531-537 | Till "Att hantera", ingen modell |
| 2 | Klassning: support, lead eller ej relaterat | rad 542, 396-421; `email_pipeline/klassning.py:119-191` | Bara kodregler i drift (Jev av, se `jev.md`). Fel i klassningen ger supportvägen (rad 413-415) |
| 3 | Avtalsgrind: ingen kundtext till modellen utan registrerat avtal | rad 551-556 | Mejlet väntar obehandlat |
| 4 | Dygnsbudget | rad 560-567 | Mejlet väntar obehandlat |
| 5 | Inbäddning och sökning i kunskapsbasen, bredare sökning per fråga | rad 332-342 | – |
| 6 | Triage och utkast i ett modellanrop (`agent/triage.py:triage_email_llm`) | rad 350-363 | Obesvarade frågor ger en ny sökning och ett omskrivet utkast, en gång (rad 368-389) |
| 7 | Tvingad överlämning: triagen säger eskalera, ingen träff, kunden ber om en människa, eller kategorins regel är `escalate` | rad 657-673 | Utkast med status `pending`, ärendet `escalated` (rad 706-720). Ett delsvar går genom faktagrinden; håller det inte används en fast text (rad 690-705) |
| 8 | Textkvalitet (språkputs och flaggor) | rad 728-731 | En flagga stoppar autosvar (rad 757) |
| 9 | Faktagrind mot kunskapsbas, kundens text och profil | rad 738-750; `agent/support_faktagrind.py` | Ostött påstående stoppar autosvar och loggas |
| 10 | Autosvar bara om regeln är `auto`, konfidens minst `AUTO_SEND_MIN_CONFIDENCE`, sentiment minst 0,4, ingen textflagga och faktagrinden ok | rad 753-759 | Annars utkast (rad 807-826) |
| 11 | AI-upplysning sist i autosvaret, i kod | rad 44-64, 768 | Bara i `development` (INV-AI-001) |
| 12 | Sändning före statusskrivning | rad 773-782 | Sändfel blir ett utkast till granskning |
| 13 | Oväntat fel | rad 828-849 | Status `failed`, skälet i beslutsloggen |

Bilder i mejl: med `LLM_PROVIDER=gemini` skickas bilderna inte till
triagemodellen; prompten får en rad om att bildanalys inte stöds
(`snajp-support/app/agent/triage.py:141-146`).

### 2.2 Chattvägen (`snajp-support/app/agent/support_agent.py:run_support_agent`, rad 923)

| # | Steg | Kod |
|---|---|---|
| 1 | Bilagor beskrivs av bildmodellen och kastas | rad 1010-1014; `agent/vision.py:23-33` |
| 2 | Uppsägningsklassaren startas parallellt; fel ger 0,0 | rad 1195-1205; `agent/retention_classifier.py:37-47` |
| 3 | Personnummer maskeras, kundtexten ramas in | rad 1215-1220 |
| 4 | Triage (`cs:ticket-triage`) | rad 1296 |
| 5 | Research i kunskapsbasen (`cs:customer-research`) | rad 1493 |
| 6 | Överlämning avgörs i kod: kunden ber om en människa | rad 1557-1588; INV-ESC-001 (AI-inv. 752-783) |
| 7 | Utkast (`cs:draft-response`) på kundens nivå för faktakontroll | rad 1799, 1822 |
| 8 | Eskaleringsbedömning (`cs:customer-escalation`) | rad 1894 |
| 9 | Faktagrind, med en reparationsrunda | rad 2199-2226; INV-GROUND-002 och -003 (AI-inv. 336-375) |
| 10 | Läckspärr: ett svar som bär agentens instruktioner når aldrig kunden | rad 2320-2335 |

### 2.3 Instruktionslager

- Tre lager per körning: vendorad baslinje, overlay och global
  instruktionsfil; hasharna sparas i `agent_runs.pack_version`
  (INV-AUDIT-001, AI-inv. 394-405).
- Agentens grundprompt och kundens önskemål läses per kund
  (`processor.py:343-348`).
- Kundskriven SOUL-text och kunskapsbasens artiklar står i användarposition,
  inramade som opålitlig text (INV-SEC-009, AI-inv. 259; INV-SEC-012,
  AI-inv. 293-318).

## 3. Modeller och resurser per livscykelsteg

| Steg | Konfigfält | Standard i kod | I drift (main och development) | Leverantör och plats |
|---|---|---|---|---|
| Triage, research, utkast, eskalering, språkputs, uppsägningsklassare, mejltriage | `model` (`MODEL`) | `gpt-4o-mini` (`snajp-support/app/config.py:288`) | `gemini-2.5-flash` (bevis rad 103, 254), `LLM_PROVIDER=gemini` (rad 102, 253) | Google Vertex AI |
| Bildbeskrivning i chatten | `vision_model` | `gemini-2.5-flash` (`config.py:307`) | Osatt, alltså standard | Google Vertex AI |
| Inbäddningar | `embedding_model` | `gemini-embedding-001`, 1536 dimensioner (`config.py:289, 303`) | Osatt, alltså standard | Google Vertex AI |
| Region | `google_cloud_region` | `europe-west1` (`config.py:252`) | Osatt, alltså `europe-west1` | Belgien |
| Reservregioner vid 429 i bakgrundsjobb | `vertex_reservregioner` | `europe-west4,europe-north1` (`config.py:258`) | Osatt, alltså standard | `europe-north1` saknas i Googles tabell för Gemini 2.5 (`gemini-bedomning.md:87`, A9) |
| Region för inbäddning och bild | `vertex_inbaddning_region`, `vertex_bild_region` | tom = huvudregionen (`config.py:265, 273`) | Osatta | – |
| Tänkande | `gemini_reasoning_effort` | `none` (`config.py:348`); eskaleringssteget tänker ändå (`config.py:344-346`) | Osatt | – |
| Tidsgräns per steg i chatten | `llm_timeout_chatt_s` | 20 s (`config.py:407`) | Osatt | – |

**Var den körs.** Railway-tjänsten `api` i miljöerna `main` och
`development` (bevis rad 83, 237), region Amsterdam (DPIA rad 109). Chatten
nås via tjänsterna `web` och `support`.

**Livslängd.** Gemini 2.5 har passerat Googles pensionsdatum 2026-10-20 och
saknar vald ersättare. Se `README.md`, sista avsnittet. Supportsviten gav
48/50 på `gemini-3.5-flash-lite` i `eu` mot 47/50 på 2.5-flash
(`docs/stabilitet-2026-11/eval/modellbyte-dev-2026-11-18-support.json`;
`efter-support.json`), men bytet är återställt (`docs/BESLUT.md:12-33`).

## 4. Data in och ut

| Anrop | Vad skickas | Maskering | Kod |
|---|---|---|---|
| Mejltriage och utkast | Avsändare, ämne, mejltext, kunskapsbasens träffar, kundens profil | Personnummer maskeras i ämne och text | `agent/triage.py:127-128` |
| Chattens steg | Kundens meddelande, kunskapsbas, kundminne, profil | Personnummer maskeras | `support_agent.py:1215-1220` |
| Uppsägningsklassaren | Hela kundmeddelandet | Maskeras i `development`; **inte i `main`** (INV-DATA-007 saknas där) | `retention_classifier.py:41-47`; `gemini-bedomning.md:79` (A1) |
| Inbäddningar | Ämne och mejltext, kunskapsbasens artiklar | Maskeras i `development`; **inte i `main`** | `agent/embeddings.py:61`; `gemini-bedomning.md:80` (A2) |
| Bildbeskrivning | Bilden som base64 | Går inte att maskera; bilden lagras inte | `agent/vision.py:23-33`; DPIA rad 145-146 |
| Omformulering av utkast | Ämne, mejltext, utkast | Personnummer maskeras | `email_pipeline/omformulering.py:166-172` |

Hälsouppgifter, namn och adresser i löptext maskeras inte (DPIA rad 159, 220).

**Vad som loggas.**

- `ss_decision_log`: varje beslut i mejlvägen med motivering: `klassning`,
  `classified`, `escalated`, `faktagrind`, `auto_sent`, `auto_send_failed`,
  `draft_created`, `failed`, `vantar_avtal`, `budget`
  (`processor.py:409-412, 552-555, 614-626, 698-705, 716-719, 743-750,
  778-781, 795-803, 812-825, 846-848`; tabellen i
  `snajp-support/app/storage/postgres.py:4212-4225`).
- `agent_runs`: varje körning med hela prompten och svaret (DPIA rad 478-480;
  `snajp-support/app/agentcore/insyn.py:56`), och `pack_version` med alla tre
  instruktionslagren (INV-AUDIT-001).
- Plattformshändelser vid läckspärren (`support_agent.py:2326-2332`).

**Lagringstid: inte beslutad.** Gallringen finns som databasfunktion men är
av som standard, och ingen kund har en policy (INV-DATA-005, AI-inv.
1014-1034). DPIA:n står med öppna fält för både supportdata och stegloggar
(DPIA rad 331, 488).

## 5. Mänsklig översyn

| Var | Vad | Kod och test |
|---|---|---|
| Kategoriregel per kund: `draft`, `auto` eller `escalate` | Standard `draft` för varje kategori; kunden kan ställa om | `processor.py:652-653`; `VillkorSida.tsx:38-40` |
| Tvingad överlämning | Triagen, ingen träff, kunden ber om människa | `processor.py:657-673`; INV-ESC-001, `snajp-support/tests/agent/test_support_eskalering.py` |
| Människan äger ett överlämnat chattsamtal | Agenten tar aldrig tillbaka det | INV-ESC-001 (AI-inv. 752-783) |
| Autosvar spärras vid låg konfidens, negativt sentiment, textflagga eller ostött påstående | Utkast till granskning i stället | `processor.py:753-759`; INV-GROUND-002, `tests/agent/test_kallbunden_faktagrind.py` |
| AI-upplysning i autosvar och "AI-assistent" i chatten | Bara `development` | INV-AI-001, `snajp-support/tests/invariants/test_inv_ai_001.py` |
| Avtalsgrind som standard för nya kunder | Bara `development` | INV-AVTAL-001, `tests/invariants/test_inv_avtal_001.py` |

**Automatiskt utan människa:** chattens svar, klassningen i inkorgen, och
mejlsvar i kategorier som kunden satt på `auto`. Vilka kunder som har satt en
kategori på `auto` är inte belagt (`matris.md:212`, fråga 5).
`AUTO_SEND_MIN_CONFIDENCE` är satt i båda miljöerna, värdet syns inte i
beviset (bevis rad 84, 238); standard är 0,75 (`config.py:525`).

Artikel 22 bedöms inte tillämplig så länge utkast granskas; bedömningen ska
göras om för kategorier på `auto` (DPIA rad 559-577).

## 6. Utvärdering

| Svit | Fall | Datum, miljö, modell | Godkända | Fil |
|---|---|---|---|---|
| `snajp-support/evals/support_livrustning.json` (chatten) | 50 | 2026-11-10 före, development, 2.5-flash | 47/50; injektion 4/5; p50 10,2 s, p95 21,2 s | `docs/stabilitet-2026-11/eval/fore-support.json` |
| samma | 50 | 2026-11-10 efter | 47/50; injektion 5/5; p50 8,0 s, p95 14,7 s | `…/eval/efter-support.json` |
| samma | 50 | 2026-11-18, development, 3.5-flash-lite i `eu` | 48/50; p50 5,9 s, p95 8,1 s | `…/eval/modellbyte-dev-2026-11-18-support.json` |
| Golden (syntetisk) | 7 | 2026-11-18 lokalt, 2.5-flash | 6/7 (7/7 i en tidigare körning) | `docs/compliance/modellbyte-underlag.md:185` |
| Mejltriage (samma 50 fall) | 50 | 2026-11-18 lokalt, 2.5-flash | 45/50 | `modellbyte-underlag.md:186-187` |

Bedömningen är mekanisk: utfall, fakta, inga fel, format
(`snajp-support/evals/README.md:9, 42-45`).

**Inte mätt:**

- Tonen (`evals/README.md:47-49`).
- Nivån Ordagrant mot riktig modell (`docs/BESLUT.md:722, 745-746`).
- Mejlvägen genom hela `process_email` mot driftsatt miljö; bara triagen är
  mätt lokalt.
- Produktionen (`docs/stabilitet-2026-11/SLUTRAPPORT.md:242-243`).
- Kvaliteten på svar i drift löpande (`matris.md:76`, 9.1).
- Spridning: en körning per mätning; ett eller två fall är brus
  (`SLUTRAPPORT.md:244-247`).

Sviten bygger på en riktig kunds kunskapsbas; att kunden godkänt det är inte
belagt (`matris.md:215`, fråga 8).

## 7. Kända begränsningar

- Målet under 8 s i p95 är inte nått (`SLUTRAPPORT.md:16-20, 83`).
- Onödiga överlämningar vid irriterad men saklig kund och vid orden
  "ångerrätt" och "reklamation" (`SLUTRAPPORT.md:174-177`).
- Att rätt mening valts går inte att bevisa i kod (INV-GROUND-003, AI-inv.
  373-374).
- Kunskapsbasens vektorer är inte ifyllda; sökningen bygger på fulltext
  (`config.py:295-297`; `docs/BESLUT.md:767`).
- Mejlvägen skriver alltid svenska (`docs/BESLUT.md:678-679`).
- Bilder i mejl analyseras inte med Gemini (`agent/triage.py:145-146`).
- I `main` saknas AI-upplysningen, maskeringen före klassaren och
  inbäddningarna, och regiongrinden (README, läsanvisningen).
- Gemini 2.5 är pensionerad enligt Google och kan stängas.

## 8. Risker per AI-steg (bedömningsutkast)

Utkast av agenten. Inga riskkriterier finns, så ingen restrisk är accepterad.
Påverkan på individer bedöms i DPIA:n (R1-R13, DPIA rad 167-557) och
upprepas inte här.

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| Klassning i inkorgen | Ett supportmejl styrs bort som lead eller ej relaterat | Kunden får inget svar | Kodregler; fel ger supportvägen (`processor.py:413-415`); loggat i `ss_decision_log` | Låg (DPIA R3) | nej (ägarens beslut) |
| Triage | Fel kategori eller missad eskalering | Brådskande ärende ligger kvar, eller autosvar i fel kategori | Eskalering vid ord och sentiment; regel per kategori | Låg till medel | nej (ägarens beslut) |
| Utkast och autosvar | Påhittad uppgift om pris, frist eller villkor | Fel besked i kundens namn | Faktagrind (INV-GROUND-002/-003), grundningsregel, autosvar bara vid `auto` | Låg vid `draft`, medel vid `auto` (DPIA R2, R4) | nej (ägarens beslut) |
| Utkast | Promptinjektion i kundens mejl | Löfte om rabatt, läckt instruktion | Inramning, läckspärr (`support_agent.py:2320-2335`); 5/5 injektionsfall | Låg | nej (ägarens beslut) |
| Uppsägningsklassare och inbäddningar | Personnummer till Google omaskerat | Onödig överföring av personuppgift | INV-DATA-007, bara i `development` | Hög i `main` tills release (`gemini-bedomning.md:79-80`) | nej (ägarens beslut) |
| Alla modellanrop | Hälsouppgift i löptext till leverantören | Känslig uppgift utanför kundens kontroll | EU-region; ingen mönstermaskering möjlig | Inte fastställd (DPIA R1) | nej (ägarens beslut) |
| Autosvar | Mottagaren vet inte att en AI svarat | Brott mot AI-förordningen art. 50.1 | INV-AI-001, bara i `development` | Hög i `main` tills release (DPIA R13) | nej (ägarens beslut) |
| Loggning | Fulla promptar sparas utan slutdatum | Andra kopia av kundmejlen | RLS per kund; gallring byggd men av | Medel (DPIA R10) | nej (ägarens beslut) |
| Modellen | Google stänger Gemini 2.5 | Agenten står still | Ingen; koden förberedd för byte | Hög sannolikhet över tid | nej (ägarens beslut) |
