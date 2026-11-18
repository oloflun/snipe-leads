# Systemblad: kvitto-assistenten och den äldre bokföringsytan

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning: `README.md` i samma mapp. "Bevis" =
`docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`. Sökvägar under
`app/` avser `snajp-support/app/`.

Bladet täcker två ytor som delar grind och modell:

- **A. Kvitto-assistenten**, chatten över kundens inlästa kvitton
  (`app/agent/kvitto_agent.py`, `app/agent/kvitto_chat_tools.py`).
- **B. Den äldre bokföringsytan**: uppladdning med dubbel avläsning
  (`app/bookkeeping/underlag.py`, `app/agent/bookkeeping_agent.py:164-423`)
  och bokföringschatten (`bookkeeping_agent.py:426-948`).

## Nås de i produktion?

| Yta | Backend | Webb | Belägg |
|---|---|---|---|
| A. Kvitto-assistenten | `POST /api/kvitton/chat` (`app/api/kvitton.py:715`), routern registrerad (`app/main.py:484`) | `components/kvitton/KvittoChatt.tsx:8-21` anropar `/api/snajp-support/kvitton/chat`; vyn monteras i arbetsytan (`components/kvitton/KvittoVy.tsx:6`; `components/dashboard/WorkspaceSection.tsx:147`) | **Nås**, för arbetsytor med bokföringspaketet (`app/api/deps.py:84-99`) |
| B. Uppladdning, period, SIE, chatt | `POST /api/bookkeeping/underlag`, `/chat`, `/avstamning`, `GET /period`, `/period.sie` (`app/api/bookkeeping.py:258-566`), routern registrerad (`app/main.py:481`), grindad på bokföringspaketet (`bookkeeping.py:64`) | Proxyn `app/api/snajp-support/bookkeeping/[...path]/route.ts` finns. Ingen komponent i `app/`, `components/` eller `lib/` anropar den (sökt 2026-11-18) | Backend och proxy **nås** med giltig session eller nyckel. Att någon yta i gränssnittet använder dem är **inte belagt**. CSV-exporten i kvittovyn hänvisar till SIE-vägen (`app/api/kvitton.py:661-662`) |

`KvittoChatt.tsx:10` kallar bokföringsassistenten "den gamla". Om B används i
drift är inte belagt.

## 1. Syfte och avsedd användning

**A.** Svarar på frågor om vad företaget lagt pengar på: summor per period
och kategori, enskilda kvitton och varför de flaggats, och förklaringar av
momsbegrepp ur en fast kunskapstext (`kvitto_agent.py:50-75`;
`kvitto_chat_tools.py:1-10`).

**B.** Läser av ett uppladdat kvitto två gånger, sammanför, och bygger ett
verifikat när grinden säger ja (`bookkeeping_agent.py:349-405`). Chatten
svarar på bokföringsfrågor med samma grind, polering och kunskapsfångst
(`bookkeeping_agent.py:700-948`).

**För vem.** Kunder med bokföringspaketet.

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad policy):

- Skatteråd: avdragsrätt, deklaration, frågor från Skatteverket. Prompten
  hänvisar till redovisningskonsult (`kvitto_agent.py:114-118`).
- Belopp som modellen räknar själv (`kvitto_agent.py:53-59`; INV-BOOK-001).
- Godkännande av kvitton: "det gör alltid en människa" (`kvitto_agent.py:99-100`).
- Arkivering av original (`app/bookkeeping/underlag.py:3-14`).

## 2. Design

**A. En tur i kvitto-assistenten** (`kvitto_agent.py:158-218`)

| # | Steg | Kod |
|---|---|---|
| 1 | Global instruktion plus systemprompt | rad 134-144, 166-167 |
| 2 | Tonläge vid otrevligt språk | rad 172-175 |
| 3 | Agent med fem läsande verktyg, tenant ur kontexten, högst 50 rader per lista, högst 8 varv | rad 178; `kvitto_chat_tools.py:33-42, 58-266` |
| 4 | Beloppsgrind: varje krontal i svaret måste finnas i turens verktygssvar | rad 181; `app/bookkeeping/beloppsgrind.py:174` |
| 5 | Fälls: ett omförsök med instruktion att hämta siffran | rad 147-155, 182-198 |
| 6 | Fälls igen: fast svar i stället för modellens | rad 200-201 |
| 7 | Godkänt: deterministisk putsning | rad 202-208 |
| 8 | Svaret märks `grundad` och visas med förbehåll | rad 210-218; `KvittoChatt.tsx:13-15` |

**B. Uppladdning** (`app/api/bookkeeping.py:120-190`)

| # | Steg | Kod |
|---|---|---|
| 1 | Filkontroll; PDF-textlager eller bildavskrift | `underlag.py:61-135`; `bookkeeping.py:175-185` |
| 2 | Två oberoende avläsningar, JSON, temperatur 0 | `bookkeeping_agent.py:164-218, 364-366` |
| 3 | Sammanför; fält där de skiljer sig utelämnas och ger granskning | `bookkeeping_agent.py:311-347, 368` |
| 4 | Verifieringsgrind; verifikat byggs av kod | `bookkeeping_agent.py:382-405`; `app/bookkeeping/verifieringsgrind.py` |

**B. Bokföringschatten** (`bookkeeping_agent.py:820-948`): som A, plus
polering med humanizer efter grinden och ny grind på det polerade (rad
775-818, 903-908), kunskapsfångst och ett prioriterat larm när svaret fälls
även efter omförsök (rad 730-773, 913-934).

## 3. Modeller och resurser

| Steg | Konfigfält | I drift | Plats |
|---|---|---|---|
| A: agenten | `model` via `get_agent_model` (`kvitto_agent.py:26, 141`), temperatur 0,5 | `gemini-2.5-flash` (bevis rad 254) | Vertex AI `europe-west1`. **Inte** `KVITTO_MODEL`, som bara gäller kvittohanteraren |
| B: avläsning | `model` (`bookkeeping_agent.py:216`), temperatur 0 | `gemini-2.5-flash` | Samma |
| B: bildavskrift | `vision_model` (`underlag.py:127`) | Osatt, alltså `gemini-2.5-flash` | `vertex_bild_region` eller huvudregionen |
| B: chatten, polering, kunskapsfångst | `model` | `gemini-2.5-flash` | Samma |

Railway-tjänsten `api`. Gemini 2.5 är pensionerad enligt Google (`README.md`).

## 4. Data in och ut

- **A in:** kundens fråga och historik, och verktygssvar ur `bk_underlag`
  (leverantör, belopp, kategori, flaggor, notering). Ingen maskering; prompten
  förbjuder att skriva ut personnummer och fullständiga kortnummer
  (`kvitto_agent.py:120-123`).
- **B in:** kvittots text eller bild (`underlag.py:107-135`). Ingen maskering.
  Filen sparas inte, bara fält och sha256 (`underlag.py:3-9`).
- **Loggat i `agent_runs`:** A: frågan och svaret, högst 4 000 tecken vardera,
  plus grindens utfall (`app/api/kvitton.py:766-785`). B: sedan 2026-11-18
  inte kvittots text, bara dess längd, en kort sha256 och underlagets id
  (`kvittotext_for_logg` i `app/api/bookkeeping.py`), fälten och stegloggen
  utan text (`as_log(verbose=False)`: mätvärden och lagrens hashar). Chatten
  loggar kundens fråga och svaret, högst 4 000 tecken vardera; texten ur ett
  bifogat underlag går till modellen men står i loggen bara som längd, hash
  och id. Test: `tests/bookkeeping/test_kvittotext_logg.py`. Före 2026-11-18
  sparades upp till 4 000 tecken kvittotext i `input_text` och hela texten i
  stegloggen; de raderna nollas av gallringen när den slås på (migration 119).
- **Lagringstid:** inte beslutad.
- Integritetsnotisen säger att mejlens text inte sparas (`kvitto_agent.py:36-42`,
  visad i `components/kvitton/Integritetsnotis.tsx`). Det gäller mejl; i B
  sparas sedan 2026-11-18 inte heller kvittots text, se ovan.

## 5. Mänsklig översyn

- A ändrar inget; den läser och svarar. Ett fällt svar märks i gränssnittet
  (`KvittoChatt.tsx:13-15`).
- B bygger verifikat utan godkännande när grinden säger ja
  (`bookkeeping_agent.py:382-405`). Oeniga avläsningar ger granskning.
- B larmar Snajp när chatten inte kan svara med hämtade siffror
  (`bookkeeping_agent.py:921-934`).

Test: INV-BOOK-003 i `snajp-support/tests/bookkeeping/test_chatt.py` och
`test_chatt_flertur.py`. INV-BOOK-003 saknar egen rubrik i
`ARCHITECTURE_INVARIANTS.md` (sökt 2026-11-18); den definieras i
`beloppsgrind.py:1`.

## 6. Utvärdering

Ingen evalsvit för A eller B (`snajp-support/evals/README.md:7-11`).
Grinden är enhetstestad (ovan). Mätt kvalitet på svaren: **inte belagt.**

## 7. Kända begränsningar

Grinden fångar inte belopp utan valutamarkör och decimaler, och inte ett tal
som av en slump finns i ett verktygssvar, till exempel ett årtal
(`beloppsgrind.py:22-37`). Den prövar att talen är hämtade, inte att svaret
är rimligt (rad 15-16).

## 8. Risker per AI-steg (bedömningsutkast)

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| A, B chatt | Påhittat belopp | Fel tal i en momsfråga | Beloppsgrind, omförsök, fast svar | Låg; luckorna i avsnitt 7 kvarstår | nej (ägarens beslut) |
| A, B chatt | Råd om avdrag eller deklaration | Felaktigt skatteråd | Bara instruktion i prompten | Medel; ingen kodspärr | nej (ägarens beslut) |
| A, B chatt | Personnummer i svaret | Onödig exponering | Bara instruktion i prompten | Låg | nej (ägarens beslut) |
| B avläsning | Verifikat utan människa | Fel i bokföringen | Dubbel avläsning, grind, Decimal | Medel | nej (ägarens beslut) |
| B | Oanvänd yta som hålls öppen | Otestad väg in till modellen | Paketgrind | Inte bedömd; användning okänd | nej (ägarens beslut) |
| Alla | Google stänger Gemini 2.5 | Ytan står still | Ingen | Hög sannolikhet över tid | nej (ägarens beslut) |

Påverkan på individer: underlagen rör företagets ekonomi; personer berörs som
motparter. Ingen konsekvensbedömning finns (`matris.md:123`).
