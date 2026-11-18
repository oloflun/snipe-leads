# AI-systemen i Snajp: systemblad

Datum: 2026-11-18. Skrivet av: Claude (agent), på Antons uppdrag.
Status: **underlag, inte godkänt av ägaren.** Inget i den här mappen är ett
beslut. Där ett beslut finns hänvisas till `docs/BESLUT.md` med radnummer.

Syfte: ett systemblad per AI-system, så som koden och mätningarna visar det i
dag. Bladen ska stänga gapen i `docs/compliance/ramverk/iso42001/matris.md`
(åtgärd 5, rad 199, och delar av åtgärd 3, rad 197). De beskriver inget som
inte finns.

## Läsanvisning

- Varje påstående har en hänvisning: fil och rad, eller fil.
- "inte belagt" betyder att agenten inte kunnat kontrollera saken.
- "I drift" betyder Railway-konfigurationen hämtad 2026-11-18 08:59 UTC
  (`docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`). Beviset
  visar variabelnamn och några värden, inte hemligheter. En variabel som inte
  står i beviset är osatt, och då gäller kodens standardvärde.
- Testmiljön (`development`) prövade ett modellbyte 2026-11-18 och återställdes
  samma kväll till samma modellinställningar som `main` (`docs/BESLUT.md:12-33`,
  ett beslut fattat av agenten på Antons uppdrag, inte av Anton). Bladen
  beskriver därför båda miljöerna som `MODEL=gemini-2.5-flash`.
- Koden lästes på grenen `compliance/score-2026-11-18`, utgrenad från
  `development` 1c078ebb. Flera spärrar finns i `development` men inte i
  `main` enligt de lokala referenserna (`origin/main` fe43310a, 2026-11-17;
  `origin/development` 1c078ebb, 2026-11-18): INV-AI-001, INV-AVTAL-001,
  INV-DATA-004, INV-DATA-006, INV-DATA-007 och maskeringen av personnummer före
  Jev. Bladen säger var det gäller. Release-PR 72 (som ersatte PR 60) väntar på
  ägarens merge.
- `KVITTO_MODEL` och `VERTEX_KVITTO_REGION` (`snajp-support/app/config.py:282-287,
  439-446`) är nya 2026-11-18, finns i `development`, inte i `main`, och är satta i
  ingen miljö.

## AI-systemen i omfånget

| System | Vad AI:n gör | Modell i drift | Blad |
|---|---|---|---|
| Supportagenten | Läser kundens kundmejl och chattar, klassar, skriver svar ur kundens kunskapsbas, skickar själv bara i kategorier kunden satt på automatiskt svar | Gemini 2.5 Flash, Vertex AI `europe-west1` | `supportagent.md` |
| Iris (leadsagenten) | Söker och bedömer bolag mot kundens kriterier, researchar bolagets webbplats, skriver kallmejl som köas | Gemini 2.5 Flash, Vertex AI `europe-west1`, med Google Search i sökningen | `iris.md` |
| Jev | TypeSafes beslutsmodell `jev-1.13.0`: förfiltrering och klassning av leads, tidigare också klassning av inkorgen | Extern, TypeSafe, USA. Av i `main` (se bladet) | `jev.md` |
| Kvittohanteraren | Läser kvitton och fakturor ur kopplad brevlåda och uppladdade filer, föreslår bokföring | Gemini 2.5 Flash (text och bild), Vertex AI `europe-west1` | `kvittohanteraren.md` |
| Webbrevisionens bildbedömning och webbpoolen | Betygsätter skärmbilden av ett bolags startsida; betyget fördelar bolag till webbyråkunder | Gemini 2.5 Flash (bild), Vertex AI `europe-west1` | `webbrevision.md` |
| Email Studio | Skriver om ett mejlutkast på användarens begäran (kortare, omskrivning, översättning med mera) | Gemini 2.5 Flash, Vertex AI `europe-west1`, i tjänsten `web` | `email-studio.md` |
| Kvitto-assistenten och den äldre bokföringsytan | Chatt över kundens kvitton med beloppsgrind; äldre uppladdning med dubbel avläsning och bokföringschatt | Gemini 2.5 Flash, Vertex AI `europe-west1` | `bokforingschatt.md` |

Samhällspåverkan över alla system (A.5.5), som utkast: `samhallspaverkan.md`.

Avgränsning:

- Supportagentens bildbeskrivning, uppsägningsklassare och inbäddningar är
  delsteg i supportagenten och står i det bladet.
- Iris-profilens kompilering och den grundade sökningen är delsteg i Iris.
- Kvitto-assistenten och den äldre bokföringsytan har ett eget blad,
  `bokforingschatt.md`. Kvitto-assistenten nås från arbetsytan; att något i
  gränssnittet anropar den äldre bokföringsytan är inte belagt.
- DeepSeek, OpenAI och Google AI Studio är inte AI-system i drift. Uppstarten
  vägrar dem där data är riktig (`snajp-support/app/config.py:776`,
  `llm_provider_fault`; DeepSeek-spärren i `CLAUDE.md`; INV-DATA-004 och
  INV-DATA-006 bara i `development`). `DEEPSEEK_API_KEY` och `GEMINI_API_KEY`
  är ändå satta i båda miljöerna (bevis rad 86, 90, 240, 243).

## Vilket blad ger belägg för vilket krav

| Krav (ISO/IEC 42001:2023) | README | supportagent | iris | jev | kvittohanteraren | webbrevision | email-studio | bokforingschatt | samhallspaverkan |
|---|---|---|---|---|---|---|---|---|---|
| **A.4.2** Resursdokumentation | förteckning | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | – |
| **A.4.5** System- och beräkningsresurser | – | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 | avsnitt 3 och "Nås de i produktion?" | avsnitt 4 |
| **A.6.2.2** Krav och specifikation | – | avsnitt 1, 2, 5 | avsnitt 1, 2, 5 | avsnitt 1, 2 | avsnitt 1, 2, 5 | avsnitt 1, 2 | avsnitt 1, 2 | avsnitt 1, 2 | – |
| **A.6.2.3** Design- och utvecklingsdokumentation | – | avsnitt 2 | avsnitt 2 | avsnitt 2 | avsnitt 2 | avsnitt 2 | avsnitt 2 | avsnitt 2 | – |
| **A.6.2.7** Teknisk dokumentation | – | hela bladet | hela bladet | hela bladet | hela bladet | hela bladet | hela bladet | hela bladet | – |
| **A.9.2** Ansvarsfull användning | – | avsnitt 5 | avsnitt 5 | avsnitt 5 | avsnitt 5 | avsnitt 5 | avsnitt 5 | avsnitt 5 | – |
| **A.9.4** Avsedd användning | – | avsnitt 1 | avsnitt 1 | avsnitt 1 | avsnitt 1 | avsnitt 1 | avsnitt 1 | avsnitt 1 | – |
| **6.1.2 / 8.2** AI-riskbedömning | – | avsnitt 8 | avsnitt 8 | avsnitt 8 | avsnitt 8 | avsnitt 8 | avsnitt 8 | avsnitt 8 | – |
| **A.5.4** Påverkan på individer och grupper | – | avsnitt 8 (hänvisar till DPIA) | avsnitt 8 (hänvisar till IA) | **avsnitt 9** | avsnitt 8 | avsnitt 8 | avsnitt 8 | avsnitt 8 | – |
| **A.5.5** Samhällspåverkan | – | – | – | – | – | – | – | – | hela (utkast) |

Avsnitten är desamma i alla systemblad (inte i `samhallspaverkan.md`): 1 Syfte och avsedd användning, 2 Design,
3 Modeller och resurser, 4 Data in och ut, 5 Mänsklig översyn, 6 Utvärdering,
7 Kända begränsningar, 8 Risker per AI-steg. Jev har dessutom 9 Påverkan på
individer och grupper.

## Vad bladen inte gör

- De **beslutar ingenting**. Listan "Användning som inte är avsedd" i varje
  blad är Snajps beskrivning av vad systemet inte är byggt eller konfigurerat
  för, inte en beslutad policy. Villkoren saknar i dag förbjudna användningar
  (`docs/compliance/ramverk/iso42001/ai-forordningen.md:38`).
- Riskbedömningarna i avsnitt 8 är **utkast**. Ingen risknivå är accepterad
  och ingen behandling beslutad; det kräver riskkriterier som inte finns
  (`matris.md:44-45`, 6.1.1 och 6.1.2).
- Lagringstider är inte beslutade för `agent_runs`, `ss_decision_log` eller
  leadstabellerna (`docs/dpia_supportagenten.md:331, 488`;
  `docs/intresseavvagning_kallmejl.md:286-296`). Bladen säger det, de föreslår
  inget.
- Ingen systemägare är utsedd (`matris.md:115`, A.4.6). Bladen namnger ingen.

## Gemensamt för alla Google-system: modellens livslängd

Google listar pensionsdatum 2026-10-20 för `gemini-2.5-flash` och
`gemini-2.5-pro` (`docs/compliance/modellbyte-underlag.md:50-58`;
`docs/compliance/gemini-bedomning.md:175`). Modellen svarade ändå i
`europe-west1`, `-west3`, `-west4` och `europe-north1` den 2026-11-18
(`modellbyte-underlag.md:65-68, 89-97`). "Google kan stänga när som helst"
(samma, rad 68). Ingen ersättare finns i dagens region; ersättarna finns i
EU-multiregionen `eu` (rad 101-103). Ersättare för utkast och bilder är inte
vald; frågan står öppen för Anton (`docs/BESLUT.md:30-31`). Stänger Google 2.5
står chatten, triagen, Iris, kvittohanteraren, webbrevisionen och Email Studio
still i båda miljöerna (`modellbyte-underlag.md:747`).
