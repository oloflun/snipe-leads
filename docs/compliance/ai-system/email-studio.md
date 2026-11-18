# Systemblad: Email Studio

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning: `README.md` i samma mapp. "Bevis" =
`docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`.

## 1. Syfte och avsedd användning

**Vad den gör.** En inloggad användare väljer en åtgärd på ett mejlutkast i
editorn, och modellen skriver ett förslag: kortare, omskrivning, förbättring,
personalisering, översättning, A/B-varianter, uppföljning, analys med betyg,
eller längre (`app/api/email-studio/route.ts:372-395`). Okänd åtgärd blir
"förbättra" (rad 510). Förslaget visas för användaren; routen skickar inget
mejl.

**För vem.** Snajps kunder som skriver utgående mejl, oftast Iris utkast.

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad policy):

- Skicka mejl. Routen returnerar text; utskick går genom Iris kö och
  sändspärr (`iris.md` avsnitt 5).
- Anonyma besökare: de får simulerade svar utan modellanrop
  (`route.ts:525-573`, `simulated_reason: "anonym"`).
- Behandling av kundens kundmejl. Indata är användarens eget utkast.

## 2. Design

| # | Steg | Kod |
|---|---|---|
| 1 | Kräver inloggad session; publik demo simuleras | `route.ts:491-492, 525` |
| 2 | Åtgärden slås upp i en fast lista | `route.ts:372-395, 510` |
| 3 | Modellval: där data är riktig aldrig OpenAI, AI Studio eller DeepSeek, och Vertex bara i en EU-region; annars `null` och simulering | `lib/llm/modellval.ts:235-278`; INV-DATA-004, INV-DATA-006 (bara `development`) |
| 4 | Prompten: hårda utdataregler och språkkrav, sedan åtgärdens instruktion | `route.ts:269-343, 589` |
| 5 | Modellanrop med upp till tre försök | `route.ts:397-400` |
| 6 | Modellfel loggas med klass, leverantör, modell och åtgärd | `route.ts:663, 675` |

## 3. Modeller och resurser

| | Konfig | Standard | I drift | Plats |
|---|---|---|---|---|
| Modell | `MODEL` om den börjar på `gemini`, annars `gemini-2.5-flash` | `lib/llm/modellval.ts:182-185, 255` | `MODEL` står inte på tjänsten `web` i beviset (rad 4-35, 168-199), alltså `gemini-2.5-flash` | Vertex AI |
| Region | `GOOGLE_CLOUD_REGION` | `europe-west1` (`modellval.ts:52, 204`) | Osatt | Belgien |
| Servicekonto | `GOOGLE_SERVICE_ACCOUNT_JSON` | – | Satt på `web` i båda miljöerna (bevis rad 9, 173) | – |
| Tänkande | `reasoningEffort` | lägsta nivå per modell (`route.ts:442-449`) | – | – |

**Var den körs.** Railway-tjänsten `web` (Next), inte `api`.

**Livslängd.** Gemini 2.5 är pensionerad enligt Google (`README.md`).
`gemini-3.5-flash-lite` i `eu` gav 200 på två provanrop i development
2026-11-18 (`docs/compliance/modellbyte-underlag.md:603`).

## 4. Data in och ut

- **In:** användarens utkast, som kan innehålla mottagarens namn och bolagets
  uppgifter (`docs/compliance/gemini-bedomning.md:71`). Ingen maskering.
- **Ut:** förslag och, för analys, ett betyg med förbättringar.
- **Loggat:** modellfel i webbtjänstens logg (`route.ts:675`). Om
  anropen sparas i `agent_runs` är inte belagt; ingen sådan skrivning hittad i
  routen.
- **Lagringstid:** inte beslutad.

## 5. Mänsklig översyn

Varje anrop startas av en människa, och resultatet är ett förslag som samma
människa väljer att använda eller inte. Inget går ut automatiskt.

## 6. Utvärdering

Ingen svit finns. Två anrop i development 2026-11-18 är det enda belägget
(`modellbyte-underlag.md:603, 770`).

**Inte mätt:** kvaliteten per åtgärd, att översättningen är trogen, och att
förslagen inte lägger till påståenden som saknar grund. Iris faktagrind körs
inte på Email Studios utdata i routen; om utdata som klistras in i ett utkast
granskas igen före utskick är inte belagt.

## 7. Kända begränsningar

- Ingen faktagrind i routen; modellen kan föreslå en siffra eller ett påstående
  som inte stod i utkastet. Användaren är kontrollen.
- `EMAIL_STUDIO_MODEL` gäller bara OpenAI- och DeepSeek-vägarna, som är
  spärrade där data är riktig (`modellval.ts:242, 271-272`).

## 8. Risker per AI-steg (bedömningsutkast)

Utkast av agenten. Inga riskkriterier finns, så ingen restrisk är accepterad.

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| Omskrivning | Påhittat påstående i förslaget | Osant i ett mejl om användaren tar det | Människan väljer; hårda utdataregler i prompten | Låg till medel | nej (ägarens beslut) |
| Modellval | Utkast med namn går till en leverantör utanför EU | Överföring utan avtal | `valjModell` (INV-DATA-004/-006, bara `development`); i `main` saknas OpenAI-nyckel i beviset | Låg | nej (ägarens beslut) |
| Modellen | Google stänger Gemini 2.5 | Funktionen svarar med fel | Ärligt fel till användaren (`route.ts:663`) | Hög sannolikhet över tid | nej (ägarens beslut) |

Påverkan på individer: mottagaren av det slutliga mejlet berörs indirekt; se
`iris.md` och IA:n (`docs/intresseavvagning_kallmejl.md`).
