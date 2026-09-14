# Session Log — 2026-09-04

## Session Summary
Kostnadsjakten på leads-kedjan avslutad och två datakvalitetsgrindar
tillagda, allt pushat till `development` och liveverifierat. Slutläget är
**0,187 kr/lead** mot utgångsläget ~1 kr (5,3×), uppmätt mot riktiga
gemini-3.6-flash på committat HEAD med samma fixtures och facit som alla
tidigare mätningar — precision oförändrad (kontakt 3/5, qualified 4/4).

0,10 kr nåddes INTE, och det är ett mätresultat snarare än ett misslyckande:
alla skopningar är gjorda, och den enda återstående vägen — billigare modell
på utkaststegen — är uppmätt och avvisad på kvalitetsgrund. Mekaniken ligger
kvar inert så nästa lite-generation prövas med en env-flagga i stället för
en kodändring.

Pixelbesiktningen efter deployen (`qa_vyer.mjs` mot dev, GRÖNT på 50+ vyer)
ledde vidare till en skarp verifieringskörning som avslöjade att
ATS-subdomäner (`fibio.teamtailor.com`) passerade namn↔domän-grinden — fixat
och pushat samma session.

## What Changed

### Files Modified
- `snajp-support/app/leads/discovery.py` — `webbplats_matchar_namn` (namn↔domän-grind på källdata, tre vägar, golv 5 tecken) och `_ANNONSPLATTFORMAR` (ATS/jobbannonsvärdar fälls i `webbplats_ar_bolagets`, subdomänmatchning)
- `snajp-support/app/leads/outreach_playbook.py` — humanizerns `model_setting` rättad till `leads_humanizer_model` (hade blivit `leads_draft_model` i en patchflytt)
- `snajp-support/tests/leads/test_sources_federation.py` — tester för båda grindarna, inklusive de två verkliga driftfallen
- `snajp-support/tests/agent/test_leads_v2_wiring.py` — `test_stegen_har_skilda_modellfalt` låser att humanizern inte ärver utkastets modell

### Commits (development)
- `e3936d0` fix: humanizerns model_setting pekade på utkastets fält efter patchflytt
- `678cab6` fix: källdomäner verifieras mot bolagsnamnet i federationen
- `bd3deee` fix: rekryteringsplattformar räknas inte som bolagets egen sajt

## Mätningar

| Konfiguration | kr/lead | Domare mot V1 | Utfall |
|---|---|---|---|
| V1 (utgångsläge) | ~1,00 | referens | — |
| V2 all-flash + alla skopor | **0,187** | 2 V / 0 F | **i drift** |
| V2 + lite på båda utkaststegen | 0,121* | 1 V / 3 F | avvisad — tappade å/ä/ö |
| V2 + lite bara på utkastet | 0,161* | 1 V / 3 F | avvisad — svagare krokar |

\* lite-prisantagande (⅓ in, 1/6,25 ut av flash), markerat i skriptet.

Per steg (in-tokens/anrop): research 5 963 · utkast 6 169 · humanizer 8 276.

## Fynd värda att minnas
- **Allt som ger modellen en MALL homogeniserar utdatan.** Ett arbetat exempel
  i måltexttypen gav 3/4 mejl med samma öppningsfras; lite-modellen gav samma
  klass av utslätning. Samma mekanism, två olika orsaker.
- **Snåla aldrig på beläggen.** En hård cap på `evidence` fällde 2/5 utkast i
  grundningsgrinden, och reparationscykeln (+15,7k tokens/fällt lead) kostade
  mer än bantningen sparade. Resonemangsfälten tål telegramform; beläggen inte.
- **Annonsörens domän är inte alltid arbetsgivarens**, och ATS-subdomäner bär
  bolagets namn utan att vara bolagets sajt. Båda hittades i skarp data, ingen
  av dem i testsviten.
- **`git commit` committar hela det delade indexet.** En commit av åtta egna
  filer publicerade en annan sessions stagade arbete under fel rubrik. Fyra
  sessioner arbetade i samma katalog i kväll — committa med explicita
  sökvägar, alltid.

## Verifiering
- Testsviten: **1778 passed, 4 skipped** (`snajp-support/.venv/Scripts/python.exe -m pytest`)
- `qa_vyer.mjs` mot dev efter deployen: GRÖNT, inga avvikelser, inga JS-fel
- Skarp listkörning mot dev: alla fem rader fick namnmatchande domäner
- Migrationer 059/060/061 verifierade som `=` mot development

## Kvarstående
- V1-kedjan raderas efter ~en veckas V2-drift utan klagomål
- Privatpersoner i Leadslistor: juridiskt beslut hos Anton (datamodellen
  förberedd via `item_typ`)
- Nästa lite-generation: `LEADS_DRAFT_MODEL` + en domarkörning
