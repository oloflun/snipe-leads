# AI Policy Control Framework (AI-policy)

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och vid ny modell, ny modelleverantör, ny autonominivå eller ny lag |
| Ramverkets mall | `frk_pt_68cc576eab0b1748940253fa` (avdelning `it`) |
| Täcker kontroll | ISO 42001 (`frk_ct_68cc25ac90e3fe79c1beb98d`) och, genom egen koppling, AI Policy, AI Policy Review, AI Org. Roles, AIMS Scope Definition |
| Täcker krav | 4.3, 5.1, 5.2, 5.3, 6.2, 7.3, A.2.2–A.2.4, A.3.2, A.6.1.2, A.9.2–A.9.4, A.10.3 (ramverket kopplar policyn till 36 krav) |

## 1. Syfte och omfång

Policyn samlar det som redan styr Snajps AI-användning och lägger till det som saknas. Den gäller supportagenten, Iris och Jev, de modeller de använder (Gemini via Vertex AI, Jev hos TypeSafe), och AI-kodverktyg som Anton och Sebbe använder i arbetet. Den gäller båda miljöerna (`main` och `development`) och alla som arbetar för Snajp.

## 2. Grundregler som gäller i dag

Varje regel har belägg. Att bryta en är ett avsteg enligt avsnitt 9.

1. **En invariant utan test är ingen invariant.** AI-krav skrivs i `ARCHITECTURE_INVARIANTS.md` med test som körs i CI och fäller bygget (rad 7-10). En invariant tas bara bort genom en tidsbegränsad waiver.
2. **Modellen skickar aldrig själv.** Bara kod skickar, efter sändspärrarna (INV-SEC-004). Modellen kan inte välja kund (INV-SEC-002).
3. **Belägg eller överlämning.** Ett svar eller utkast får bara bära uppgifter som står i en källa; annars går det till en människa (INV-GROUND-001–004; Antons beslut 2026-11-16, BESLUT 101-158).
4. **Den som ber om en människa får en**, och agenten tar aldrig tillbaka ett överlämnat ärende (INV-ESC-001).
5. **Opålitlig text är data.** Kundmejl, sajter, kunskapsbaser och kundens röstdokument når aldrig instruktionsposition (INV-SEC-003, -009, -012).
6. **AI-upplysning i kod.** Chatt och autosvar bär en upplysning som koden lägger på (INV-AI-001). Ocommittad 2026-11-17; gäller från driftsättning.
7. **Personnummer maskeras** före varje modellanrop med kunddata (`app/moderation/maskering.py`; Jev: `app/leads/jev.py:47`).
8. **DeepSeek får aldrig se kunddata.** Uppstarten fälls i varje miljö med riktig data (`snajp-support/app/config.py:609-700`, `CLAUDE.md`). Att ändra det är ett avtalsbeslut (SCC, TIA, PUB), inte ett kodbeslut.
9. **Behandlingen stannar i EU-regionen.** Vertex anropas i `europe-west1` med EU-reserv; den globala endpointen används inte (BESLUT 2095-2098).
10. **Agenten ändrar aldrig sitt eget underlag.** Lärdomar blir förslag som en människa godkänner (INV-LEARN-001).
11. **Beslut skrivs med skäl** i `docs/BESLUT.md` (Antons regel 2026-10-10).

## 3. Autonomi

- **Supportagenten** levereras med mänsklig granskning för alla kategorier. Kunden väljer automatiskt svar per kategori och ansvarar för valet (`app/villkor/VillkorSida.tsx:34-41`). Även då går ett svar bara ut om säkerhet, sentiment, textkvalitet och faktagrind håller (`email_pipeline/processor.py:752-759`).
- **Iris** har nivåerna `draft` (standard), `first_contact` och `meeting`. Ett okänt värde blir `draft` (`app/leads/autonomy.py:47-56`). De tre första utskicken för en ny kund granskas av en människa. Sändspärrarna gäller alltid (`app/leads/send_guard.py`).
- **Ska införas:** en ändring av standardnivån, eller av vad en nivå tillåter, kräver Antons beslut i BESLUT.md och en uppdaterad konsekvensbedömning. Införs [FYLL: datum], ansvarig Anton.

## 4. Avsedd och förbjuden användning

Avsedd: kundtjänst för kundens egna kunder; att hitta, bedöma och kontakta bolag i B2B-försäljning.

**Ska införas i villkoren**, [FYLL: datum], ansvarig Anton med jurist: Snajps agenter får inte användas för beslut om kredit, försäkring, anställning, utbildning, offentliga förmåner eller nödtjänster, eller för att bedöma fysiska personer (se `../ai-forordningen.md` §3.1).

## 5. Roller

| Roll | Vem | Ansvar |
|---|---|---|
| Ägare av AI-ledningssystemet | Anton | Godkänner policyn, modeller och leverantörer, autonominivåernas standard; ledningens genomgång |
| Systemägare support | [FYLL: Anton eller Sebbe] | Systembladet, evalsviten, konsekvensbedömningen |
| Systemägare Iris och Jev | [FYLL: Sebbe?] | Som ovan; leadsreglerna i `CLAUDE.md` |
| Rapportering om ledningssystemet | Anton | Kvartalsvis rad i BESLUT.md: incidenter, mätningar, avsteg |

Rollerna gäller från godkännandet. Sebbe bekräftar sina roller skriftligt.

## 6. Godkännande av ny modell eller modelleverantör

Det här steget fanns inte när kundmejl började gå till TypeSafe (`INKORG_JEV=auto` i main, mot Antons beslut 2026-09-30; BU A2). Från godkännandet gäller:

1. Ingen ny modelleverantör får kunddata förrän Anton godkänt den skriftligt i BESLUT.md.
2. Underlaget är en rad i `../../leverantorsgranskning.md`: avtal och DPA, region, träning på data, lagringstid, underbiträden, överföringsmekanism.
3. Leverantören läggs i underbiträdeslistorna (`lib/bolag.ts`, PUB-bilagan, registerförteckningen) innan trafiken slås på.
4. En ny modell hos en godkänd leverantör kräver en körning av evalsviten före och efter (`snajp-support/evals/README.md`) och ett beslut med mätningen, som bytet pro→flash (BESLUT 1647-1664).
5. Miljövariabler som slår på en modell eller leverantör (`INKORG_JEV`, `IRIS_JEV`, `LLM_PROVIDER`, `MODEL`, `LEADS_*_MODEL`) ändras bara med en rad i BESLUT.md. **Ska införas**, [FYLL: datum], ansvarig Anton: en spärr i koden som fäller uppstarten när en sådan väg är på i en miljö med riktig data utan att leverantören är godkänd, enligt mönstret för DeepSeek.

## 7. Mätning och mål

- Evalsviterna körs före och efter varje ändring av prompt, modell eller kedja, aldrig mot produktionen (Evals). **Ska införas**, [FYLL: datum], ansvarig [FYLL]: en lägsta nivå per agent som release till `main` kräver.
- Mål för 2027 (förslag, Anton beslutar): ingen ostödd uppgift i ett skickat svar; varje AI-fel i drift blir en invariant inom 14 dagar; evalsviten körd före varje release.

## 8. Konsekvensbedömning, kunnighet och anmälan

- Varje AI-system har en konsekvensbedömning för individer, grupper och samhälle. Supportens DPIA och kallmejlens intresseavvägning används som grund. Görs om vid ny modell, ny autonominivå, ny datakälla eller årligen. **Ska införas**, [FYLL: datum], ansvarig Anton; Jev saknar bedömning i dag.
- AI-kunnighet (AI-förordningen art. 4): Anton och Sebbe går igenom policyn, systembladen och `../ai-forordningen.md` och kvitterar. **Ska ske** [FYLL: datum], ansvarig Anton.
- Oro om AI-användningen tas upp med Anton, eller med [FYLL: extern kontakt] om den gäller Anton. Ingen får missgynnas för en anmälan i god tro (P28).

## 9. Avsteg

Avsteg beslutas av Anton med skäl och slutdatum i BESLUT.md, som enligt P08. Ett avsteg som släpper kunddata till en ny leverantör kan inte beviljas utan avsnitt 6.

## 10. Koppling till andra policyer

Dataskydd: G02, G04. Leverantörer: G06, P26. Incidenter: G03 (AI-fel utan persondata ska också loggas där). Ändringar: P19, P20. Loggning: P25. Disciplin: P28. **Ska ske:** en genomgång av att policyerna inte krockar (krav A.2.3), [FYLL: datum], ansvarig agent med Antons granskning.
