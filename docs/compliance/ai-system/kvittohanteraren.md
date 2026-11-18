# Systemblad: kvittohanteraren

Datum 2026-11-18. Claude (agent), på Antons uppdrag. Underlag, inte godkänt av
ägaren. Läsanvisning: `README.md` i samma mapp. "Bevis" =
`docs/compliance/bevis/railway-konfiguration-2026-11-18.txt`. Sökvägar under
`app/` avser `snajp-support/app/`.

## 1. Syfte och avsedd användning

**Vad den gör.** Läser kvitton och fakturor ur kundens kopplade brevlåda och
ur uppladdade filer, tolkar fälten (datum, motpart, belopp, moms,
betalstatus, riktning) och föreslår ett verifikat
(`app/villkor/VillkorSida.tsx:18`; `app/kvitton/hanterare.py:1-19`). Ett
underlag som klarar både modellens egen bedömning och kodens kontroll blir
`klar` och får ett verifikat; resten går till manuell granskning
(`hanterare.py:932-944`).

**För vem.** Snajps kunder (företag) och deras bokföring. Underlagen kan
innehålla namn på motparter och, för enskilda firmor, personer.

En separat kvitto-assistent i chatten svarar på frågor om vad företaget lagt
pengar på (`app/agent/kvitto_agent.py:1-11`; `app/api/kvitton.py:715`). Den
använder `MODEL` (`kvitto_agent.py:26, 141`) och är inte genomgången steg för
steg här.

**Användning som inte är avsedd** (Snajps beskrivning, inte en beslutad policy):

- Arkivering av räkenskapsinformation. Originalen lagras inte; kunden ansvarar
  enligt bokföringslagen (`VillkorSida.tsx:26-28`).
- Skatteråd (`kvitto_agent.py:6-7`).
- Att låta modellen räkna eller skriva belopp på en debetrad. Belopp räknas i
  kod (INV-BOOK-001, `ARCHITECTURE_INVARIANTS.md:463-479`).
- Bedömning av personer, kreditbeslut eller betalningar. Hanteraren läser och
  föreslår; den öppnar inga länkar och skriver inget i inkorgen
  (`hanterare.py:17-19`).

## 2. Design (`hanterare.py:hantera`, rad 733-833)

| # | Steg | AI? | Kod | Vid fel eller osäkerhet |
|---|---|---|---|---|
| 1 | Läs bilagor: PDF-textlager, annars bildavskrift ordagrant | Bildmodell | `hanterare.py:140-160, 163-190`; prompten `BILDPROMPT` i `app/bookkeeping/underlag.py` | Utan bildklient blir avskriften tom (rad 144-145) |
| 2 | Agenten läser meddelandet med grundprompten och läsande verktyg: sök i inkorgen, läs bilaga igen, sök tidigare underlag, kontrollera nummer, kontrollräkna, slå upp kunskap | Textmodell, temperatur 0, högst 12 varv | `hanterare.py:442-452, 478-498` | Oläsbart svar: ett omförsök (rad 500-512) |
| 3 | Modellen faller | – | `hanterare.py:513-525, 786-793` | Kvot- och kreditfel lyfts; annars läses underlaget maskinellt och flaggas `osäker_klassning` |
| 4 | Kontrolläsning: en andra, oberoende genomgång av kärnfälten | Textmodell, JSON, temperatur 0 | `hanterare.py:546-575, 778-784` | Körs bara om agenten gav underlag |
| 5 | Sammanför de två läsningarna | Kod | `hanterare.py:594-616` | – |
| 6 | Kodens kontroll: texten finns i källan, riktning, kredit, kontrollsiffror, kontrollräkning, moms och obligatoriska fält, valuta | Kod | `app/kvitton/granskning.py:852-877` | Brister sänker status |
| 7 | Samma fil redan inläst: möjlig dubblett | Kod | `hanterare.py:814-832` | Flagga och granskning |
| 8 | Spara: `klar` bara om promptens status är `KLAR_FÖR_GRANSKNING`, verifieringsgrinden säger ja, valutan är SEK och totalbeloppet finns | Kod | `hanterare.py:859-944`; `app/bookkeeping/verifieringsgrind.py:42-43` | Annars `granska_manuellt` |
| 9 | Verifikat byggs av kod; okänd kategori ger granskning | Kod | `hanterare.py:938-944`; INV-BOOK-004 | – |

Utan modellnyckel (simulering, testsvit) ersätts steg 2-4 av en
regexläsare med samma kontrakt (`hanterare.py:21-25, 651`).

Kontroller i kod som skyddar mot modellens fel: Decimal och balans
(INV-BOOK-001), periodrapport aldrig klar när den inte går ihop
(INV-BOOK-002), inget verifikat utan känd betalstatus (INV-BOOK-004)
(`ARCHITECTURE_INVARIANTS.md:463-512`).

## 3. Modeller och resurser per livscykelsteg

| Steg | Konfigfält | Standard i kod | I drift (main och development) | Plats |
|---|---|---|---|---|
| Bildavskrift | `vision_model` | `gemini-2.5-flash` (`config.py:307`) | Osatt, alltså standard | `vertex_bild_region`, tom = huvudregionen (`config.py:266-273`) |
| Agent och kontrolläsning | `kvitto_model`, annars `model` (`config.py:970-972`) | tom (`config.py:439-446`) | `KVITTO_MODEL` osatt; `MODEL=gemini-2.5-flash` (bevis rad 103, 254) | `vertex_kvitto_region`, annars huvudregionen (`config.py:282-287, 965-968`); `app/agent/llm.py:684-701` |
| Huvudregion | `google_cloud_region` | `europe-west1` | Osatt, alltså `europe-west1` | Vertex AI, Belgien |
| Kvitto-assistenten | `model` | – | `gemini-2.5-flash` | Vertex AI |

`KVITTO_MODEL` och `VERTEX_KVITTO_REGION` är tillagda 2026-11-18 (gren
`development`, inte i `main`) och inte satta i någon miljö. De finns för att
kvittostegen ska kunna stanna på en annan modell än `MODEL` vid ett byte
(`config.py:439-446`); test i `snajp-support/tests/kvitton/test_kvitto_modell.py`
(ny 2026-11-18). Regionen kontrolleras mot EU-listan (INV-DATA-006, bara i
`development`).

**Var den körs.** Railway-tjänsten `api`. Skanning av brevlådan går som
bakgrundsjobb med förlopp (`app/api/kvitton.py:188`; `SLUTRAPPORT.md:110-111`).

**Livslängd.** Gemini 2.5 är pensionerad enligt Google (`README.md`). När
kvittohanteraren gick på `gemini-3.5-flash-lite` föll sviten från 37/40 till
30/40, och en obetald kundfaktura bokfördes som klar med det egna bolaget som
motpart (`docs/compliance/modellbyte-underlag.md:716-733`). Provbytet
återställdes av det skälet (`docs/BESLUT.md:12-33`). Som bildmodell läste
`gemini-3.8-flash` fotografier bäst men rättade ett avsiktligt felsummerat
kvitto i stället för att skriva av det (`modellbyte-underlag.md:346-350`).

## 4. Data in och ut

| Anrop | Vad skickas | Maskering | Belägg |
|---|---|---|---|
| Bildavskrift | Kvittobilden som data-URL | Ingen; bilder går inte att maskera | `hanterare.py:147-158`; `gemini-bedomning.md:67` |
| Agent | Avsändare, mottagare, datum, ämne och text i mejlet; bilagornas text; upp till 40 tidigare underlag; kundens profil | Ingen | `hanterare.py:65, 767-776` |
| Kontrolläsning | Samma, plus det researchen läste in | Ingen | `hanterare.py:779-784` |

**Ut:** en `bk_underlag`-rad per underlag med fält, status, anmärkning och
eventuellt verifikat (`hanterare.py:955-995`).

**Lagras inte:** originalfiler, kvitton och mejl. Bara en sha256-summa
(`VillkorSida.tsx:27`; `docs/dpia_supportagenten.md:147-148`).

**Loggat:** stegloggen i minnet bär systemprompt och användarmeddelande
(`hanterare.py:527-541`). Det som skrivs till `agent_runs` vid skanning är en
sammanfattning: antal mejl, klass, antal underlag, verktyg och stegnamn, inte
prompterna (`app/api/kvitton.py:255-268`; `app/kvitton/skanning.py:150-157`).
Ingen skrivning till `agent_runs` hittad i uppladdningsvägen
(`app/api/kvitton.py:436-469`). Gallringen rör aldrig `bk_underlag` och
`bk_verifikat` (INV-DATA-005). Lagringstid är inte beslutad.

## 5. Mänsklig översyn

| Var | Vad | Kod |
|---|---|---|
| Status `granska_manuellt` | En människa godkänner, och kan rätta datum, belopp, moms, kategori, motpart och betalstatus. Grinden körs igen på det rättade | `app/api/kvitton.py:470-566` |
| Status `klar` | Verifikatet byggs **utan** mänskligt godkännande. Ett klart kvitto kan inte rättas i samma flöde; perioden måste rensas och läsas in igen | `hanterare.py:938-941`; `app/api/kvitton.py:495-501` |
| Riktning | Användarens besked "det här är en kundfaktura" vinner över igenkänningen | `hanterare.py:745-746, 808-812` |
| Periodrapport och SIE-export | Vägrar när något inte går ihop | INV-BOOK-002 |

Det enda fel i mätningarna som gick förbi granskningen var en obetald
kundfaktura bokförd som klar (`modellbyte-underlag.md:730-733`). Det visar att
statusen `klar` kan bära ett modellfel som koden inte fångar.

## 6. Utvärdering

| Svit | Fall | Datum, miljö, modell | Godkända | Fil |
|---|---|---|---|---|
| `snajp-support/evals/kvitto.json` (text-PDF:er) | 40 | 2026-11-10 före, development, 2.5-flash | 35/40; 2 tekniska fel; p50 16,6 s | `docs/stabilitet-2026-11/eval/fore-kvitto.json` |
| samma | 40 | 2026-11-10 efter, 2.5-flash | **37/40**; 0 tekniska fel; status 95 %, belopp 97,5 %, fält 97,5 %; injektion 4/4; p50 20,9 s, p95 37,9 s | `…/eval/efter-kvitto.json` |
| samma | 40 | 2026-11-18, development, `MODEL`=3.5-flash-lite i `eu` | **30/40**; status 82,5 %, belopp 92,5 %, fält 95 %; p50 7,2 s | `…/eval/modellbyte-dev-2026-11-18-kvitto.json` |
| Bildsteget: kvittotexterna renderade som skärmdump och foto | 40 + 40 | 2026-11-18 lokalt, 2.5-flash | Skärmdump 40/40, foto 36/40 | `modellbyte-underlag.md:325-342` |

**Inte mätt:**

- Bildmodellen genom hela kedjan: sviten består av text-PDF:er
  (`modellbyte-underlag.md:713-714, 761-766`).
- Fotograferade kvitton i development.
- Riktiga kunders underlag; sviten är syntetisk (`snajp-support/evals/README.md:32-33`).
- Kvitto-assistenten i chatten.

## 7. Kända begränsningar

- Fyra av 40 foton tappade totalbeloppet med 2.5-flash; de hade gått till
  granskning (`modellbyte-underlag.md:344-345`).
- En egen kundfaktura känns inte igen utan rätt knapp (`SLUTRAPPORT.md:162`).
- Utländsk valuta räknas inte om; beloppet hamnar i `belopp_original` och
  raden går till granskning (`hanterare.py:839-848, 905-913`).
- Vertex gav 429 på nio av 40 kvitton en eftermiddag (`SLUTRAPPORT.md:184-186`).

## 8. Risker per AI-steg (bedömningsutkast)

Utkast av agenten. Inga riskkriterier finns, så ingen restrisk är accepterad.

| Steg | Risk | Följd | Befintlig kontroll | Restrisk (utkast) | Behandling beslutad |
|---|---|---|---|---|---|
| Bildavskrift | Fel siffra eller tappat belopp | Fel belopp i bokföringen | Avskrift ordagrant med osäkra tecken markerade (`hanterare.py:70-75`); kontrolläsning; kontrollräkning i kod | Låg; fel går oftast till granskning | nej (ägarens beslut) |
| Bildavskrift | Modellen "rättar" kvittot | Felaktigt belopp som ser rätt ut | Kontrollräkning; uppmätt för 3.8-flash, inte för 2.5-flash | Låg med dagens modell, hög vid byte till 3.8-flash | nej (ägarens beslut) |
| Agent | Fel betalstatus eller motpart | Fel motkonto, skuld som aldrig uppstår | INV-BOOK-004; riktningskontroll | Medel: ett sådant fel gick förbi granskningen på 3.5-flash-lite | nej (ägarens beslut) |
| Agent | Promptinjektion i ett mejl | Felaktig klassning | Läsande verktyg, kodkontroll; injektion 4/4 | Låg | nej (ägarens beslut) |
| Status `klar` | Verifikat utan mänsklig granskning | Fel i bokföring och momsdeklaration | Dubbel läsning och kodgrind | Medel | nej (ägarens beslut) |
| Alla anrop | Kvittobilder och mejl med personuppgifter till Google | Överföring utan maskering | EU-region; inget lagras hos Snajp | Låg till medel | nej (ägarens beslut) |
| Modellen | Google stänger Gemini 2.5 | Hanteraren står still eller byter till en sämre modell | `KVITTO_MODEL` förberedd i `development`, inte satt | Hög sannolikhet över tid | nej (ägarens beslut) |

Påverkan på individer: underlagen rör företagets affärer; personer berörs
som motparter och, hos enskilda firmor, som företagare. Följden av ett fel är
ekonomisk för kunden, inte ett beslut om en person. Ingen separat
konsekvensbedömning finns (`matris.md:123`).
