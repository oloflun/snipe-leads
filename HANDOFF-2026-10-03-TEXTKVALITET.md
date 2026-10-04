# Textkvalitetsgranskningen 2026-10-03 — slutrapport

Uppdraget: kunder ska aldrig se stavfel, konstiga ord eller dålig struktur,
vare sig i agenternas texter eller i arbetsytan. Systematisk lösning, inte
punktlagning. Sju commits på `development` (39880b5..f314b80), inget pushat.

## 1. Rotorsaken till Iris stavfel

**Modellen själv producerar felen — ingen kod korrumperar texten.** Hela
kedjan från LLM-anrop till sparat utkast är genomlyst: ingen
teckenkodningsbugg (å/ä/ö), ingen trunkering mitt i ord (klippt JSON ger
omförsök/eskalering, aldrig halv text), ingen modellfallback i backendens
utkastflöde.

Det som däremot fanns:

1. **Ingen prompt krävde korrekt svenska.** Humanizern — sista handen på
   varje utkast — kör på temperatur 0,7 med Geminis tänkande AVSTÄNGT sedan
   2026-09-19 (ett kostnadsbeslut som aldrig mättes på stavning), uppmanas
   "tillföra röst" men aldrig stava rätt, och har engelska skills och ett
   engelskt exempelmejl bredvid sig i prompten.
2. **Ingen efterkontroll fanns.** Ingen kodväg granskade språket innan
   texten sparades eller visades.
3. **Platshållarstädningen skapade egna fel:** "[förnamn]" raderades tyst
   och lämnade "Hej ," eller meningar med saknade ord — ser ut som skrivfel.
4. **Sekundärt:** delta-humaniseringens meningssplice kan ge tilltals- och
   kongruensbrott; skrapningens reservväg kunde släppa in ersättningstecken
   ("F�retag") i ordagranna citat; UI-förhandsvisningen klippte vid 220
   tecken mitt i ord.

## 2. Kvalitetslagret (Steg 3)

**`snajp-support/app/textkvalitet.py`** — en central, beroendefri modul:

- `SPRAKREGLER` — promptblock med språkkraven, återanvänt i prompterna.
- `putsa()` — deterministiska, riskfria rättningar: blanksteg före
  skiljetecken, dubbla mellanslag, hängande hälsningar, kurerad lista av
  entydiga felstavningar (versalbevarat, med ordgräns). Länkar,
  e-postadresser och organisationsnummer maskeras undan och kan aldrig
  "rättas". Produktnamn (Snajp, Iris, Livrustning …) skyddas.
- `kontrollera()` — flaggar det som kräver människa: ersättningstecken,
  kvarlämnade platshållare, markdownrester, engelska inslag i svensk text,
  avhuggna meningar, tom text.
- `korrekturlas_llm()` — kort LLM-pass (temp 0,1) som BARA körs när något
  flaggats, och vars resultat verifieras: varje länk, siffra, adress och
  skyddat namn måste överleva ordagrant, längden får inte dra iväg — annars
  behålls originalet. Fail-closed.
- `sakra_utgaende_text()` — hela kedjan; `kraver_granskning` är kontraktet.

**`lib/textkvalitet.ts`** — TS-spegel av putsningen för Next-sidan.

### Var det anropas

| Väg | Vad som körs | Vid flagga |
|---|---|---|
| Leads-kön `_queue_outreach_draft_impl` (V1/V2 första mejl, svar, uppföljningar) | platshållare kontrolleras på RÅTEXTEN före strippen + `sakra_utgaende_text` | tvingas till `awaiting_review` oavsett autonominivå |
| Mejlpipelinen `processor.py` | `sakra_utgaende_text` på triageutkastet | autosvar degraderar till granskningskön, skälet i beslutsloggen |
| Omformulering (Förbättra/Kortare/Mer personlig) | `putsa` + språkregel i prompten | granskaren har alltid sista ordet |
| Supportchatt, kvittochatt, bokföringschatt | `putsa` på slutsvaret | (faktagrind/beloppsgrind finns redan) |
| Leads-bedömningens `motivering` | `putsa` före 1200-kapningen | — |
| Email Studio-routen | `putsaText` på new_version + ämnesförslag | resultatet landar alltid hos människa i editorn |

### Prompt-härdningen

- `leads-hard-rules`-overlayen (träffar V1/V2/svar/uppföljning): felfritt
  språk som hård regel + förbud mot platshållare.
- `humanizer-svenska`-skillen: nytt steg 8 "Korrekturläs till sist —
  mänskligt är aldrig slarvigt" + skillens egna språkfel rättade
  (Revidiera, Scanna, Sycofantiska, erkänsla m.fl.).
- Humanizer-stegens uppgiftstext (V2 + supportchatt): explicit korrekturkrav.
- Triageprompten: `SPRAKREGLER` + platshållarförbud.
- Kvitto-/bokföringschattens systemprompt: "korrekt, felfri svenska".
- `EMAIL_STUDIO_SYSTEM_PROMPT`: absolut språkkravsblock.

### Rotorsaksfixar utöver lagret

- Skrapningens reservväg avkodar latin-1 när UTF-8 fäller (inga fler "�" i citat).
- `IrisGranskning`: förhandsvisningen klipper vid ordgräns.
- `Dashboard`: beslutsloggen visar "Utkast omformulerat" i stället för slugen.

## 3. Hårdkodade texter (Steg 4)

~70 rättningar i två commits (`b0cbbc5` frontend, `d6de60e` backend +
agent-core): stavfel ("Skick per vecka", "dublett"), grammatik, svengelska
(workspace→arbetsyta, processa→bearbeta, trial→provperiod, read-only→endast
läsbehörighet), engelska statusvärden i kundtext ("redan approved"→"redan
godkänt", "Saturday är helg"→svensk veckodag), numerusböjning ("1 leads"→"1
lead"), "IT-tjänster" som inte längre gemenas, utskicksfotens
"höra av oss"-idiom, demotexternas syftningsfel, m.m. Full lista per fil:
`git show b0cbbc5 d6de60e`. Två punkter medvetet INTE ändrade:
KvittoYtans kategoriprompt (strängarna är API-värden) och KPI-etiketten
"Eskalerade" (korrekt plural).

## 4. Tester (Steg 5)

- `tests/test_textkvalitet.py` — 25 tester: å/ä/ö, långa/korta texter,
  blandspråk, egennamn, siffror/länkar, avsiktligt felstavad indata,
  korrekturverifieringens fail-closed-fall.
- `tests/agent/test_leads_tools.py` — två nya: putsningen i kön, och att en
  platshållare tvingar `awaiting_review` även med autonominivån
  `first_contact`.
- **`scripts/granska_ui_texter.py`** — skannar strängliteraler i
  components/, app/, lib/, support-webb/ och snajp-support/app efter kända
  felstavningar, ersättningstecken och blankstegsfel. Körs i ordinarie
  pytest via `tests/test_ui_texter.py` (⇒ CI via verify.yml). 0 fynd i dag.
  Nya fel läggs i `FELSTAVNINGAR` (håll py+ts i synk).
- **Resultat: hela backend-sviten 2371 passed, 4 skipped. `npx tsc
  --noEmit` 0 fel (rot + support-webb).**

### Skarpa provutkast (Steg 5.5) — BLOCKERAT av kredit

`snajp-support/scripts/generera_textkvalitetsprov.py` genererar 50 riktiga
utkast (10 Iris V2, 10×3 omformuleringslägen, 10 triage) mot syntetiska
fixtures och kör varje text genom kontrollen. Två hinder i dag, båda utanför
koden:

1. AI Studio serverar inte längre `gemini-2.5-flash` till kontot
   ("available to new users"-spärr) — produktionens modell nås bara via
   Vertex-servicekontot, som inte finns lokalt.
2. AI Studio-projektets förskottskredit är slut (402) — gäller även
   .env-nyckeln, så båda nycklarna pekar på samma projekt.

**Att köra när krediten är påfylld:**

```bash
cd snajp-support && PROV_MODELL=gemini-3.8-flash .venv/Scripts/python.exe scripts/generera_textkvalitetsprov.py
```

Rapporten hamnar i `var/textkvalitetsprov-<datum>.md` för genomläsning.

## 5. Kostnadspåverkan

- Deterministiska putsningen: **0 extra LLM-anrop**, mikrosekunder.
- LLM-korrekturen: **0 extra anrop för frisk text** — den körs bara när
  kontrollen flaggat, och då max 1 kort anrop (temp 0,1, ingen
  tänkbudget). På V2:s 0,19 kr/lead: oförändrat i normalfallet, ~+0,02 kr
  för den lilla andel utkast som flaggas (och de hade annars nått kunden
  trasiga eller eskalerats).
- Prompt-härdningen: ~80 extra in-tokens per anrop — försumbart.

## 6. Kvarvarande risker och öppna trådar

- **Skarpa provet är inte kört** (kredit) — lagrets grindar är testade
  deterministiskt, men modellens faktiska felfrekvens efter härdningen är
  inte uppmätt. Kör kommandot ovan efter påfyllning.
- **Felstavningslistan är kurerad, inte heltäckande** — svenskans fria
  sammansättningar gör en full ordlista mot LLM-text till brus. Nya fel
  läggs i listan när de upptäcks; LLM-korrekturen tar resten av de flaggade.
- **Tänk-av-beslutet på humanizern** (2026-09-19) mättes aldrig på
  stavning. Om felen fortsätter efter härdningen: slå på en liten tänkbudget
  för humanizersteget och A/B-mät.
- Flaggade som egna uppgifter (chips i appen): Email Studio-ändringar
  persisteras aldrig till kö-posten som skickas; engelska leadstrådar kan
  aldrig köas (humanizer-mismatch i språkgrinden); `LEADS_*_MODEL` passerar
  uppstartsvalideringen ovaliderat (lite-modellen tappar å/ä/ö — uppmätt);
  du/ni-policyn är obesluten (blandas i nästan varje vy) liksom mail/mejl i
  ett par filer.
- **Sakfel, inte språk:** FAQ:n nämner inte de två gratismånader som
  onboardingen lovar — två olika besked till kunden.
- Verifierat endast lokalt — inget pushat; `git push origin development`
  deployar när du vill.
