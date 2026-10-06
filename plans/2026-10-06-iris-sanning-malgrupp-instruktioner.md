# Iris: påhittade bolag, läckt webbpitch, platta utkast, fel målgrupp och agentinstruktioner som skrivs över

## Status 2026-10-06 (kväll)

- **Klart och pushat till development:** fas 1–6 (förra sessionen), fas 1b, fas 7, fas 8, fas 9 (omindexering, kalibrering; hybridsökningen fanns redan), skillmätningen (variant (c) kvar), dubblettspärren Iris ↔ listor.
- **Kvar (Anton):** radera de nio bolagen, återställ development-instruktionerna, migration 101/102 i development, ja till 096–102 mot main, gallringsperiod för spårets fulltext.
- **Kvar (agent):** visuell kontroll + a11y av Underlag och flöde, skarpt Iris-prov N=5 (kräver ScrapeGraph-kredit), husets kantkontrast.
- Detalj: `HANDOFF-2026-10-06-KVALITET-INSYN-KUNDYTA.md`.

## Kontext

Provkörningarna 2026-10-05 (Snajp, utan filter, development) gav tre bolag som inte finns, utkast utan innehåll, en webbdesignpitch i ett mejl från Snajp, skolor och kommuner som leads och en slagsida mot bygg. När utkastmallen klistrades in under Globala agentinstruktioner ersattes dessutom hela instruktionsblocket. Planen rättar varje orsak i kod (grindar, inte bara prompttext), delar instruktionerna per agent och gör att feedback bakas in i stället för att ersätta. Delmål i `GOALS.md`: 2 (leads-agenten hittar inte på) och 6 (instruktioner når agenten); grunden för kundernas egen tuning.

## Rotorsaker (lästa i koden, `snajp-support/` om inget annat anges)

| Problem | Orsak | Var |
|---|---|---|
| Påhittade bolag | I en körning utan bransch går registret (merinfo) inte att använda och annonskällorna hoppas över. Då är Gemini-sökningen enda källan, och ingenting kontrollerar att bolaget eller domänen finns. Sökningens källhänvisningar kastas. En död domän räknas som "inte parkerad" och behålls. Slut på sidhämtningskredit ger samma reservväg. | `app/leads/discovery.py:1117-1211`, `:520-526`; `platshallare.py:109-123`; `webbsignal.py:141-143`; `sources/merinfo.py:648-652` |
| Poäng 100 utan källmaterial | Ort och antal anställda tas ur sökmodellens egna påståenden och skrivs som "enligt källmaterialet". Nivå A kräver inga uppfyllda kriterier. | `app/leads/bedomning.py:132-133,165-176,252-257` |
| Utkast trots tomt underlag | Ingen grind på tomt material. Leverbarhetskontrollen räknar bara, den stoppar varken status Redo eller utkastet. Sökmodellens gissade mejladress godtas om domänen stämmer. | `app/agent/leads_research_v2.py:184,317`; `app/api/leads.py:2209-2227,2331-2345,1533` |
| Webbpitch från Snajp | Webbrevisionen (byggd för webbyråer) körs för alla kunder, och dess rader ("byggd med Next.js", "synlig brist på startsidan") skickas till utkastet som citerbara fakta. Inget läckte mellan kunder: cache och profil är per kund. | `leads_research_v2.py:196-209,405-408,528`; `app/api/leads.py:2393`; `app/leads/webbrevision.py:51-65` |
| Platta utkast, påhittat case | Utkaststeget får en mening om bolaget, inga citat, inget kontaktnamn och hela produkttexten utan val av produkt. Den vendorade skillens mall ber uttryckligen om "liknande företag"-bevis, och faktagrinden fäller bara namngivna kunder och siffror. | `app/api/leads.py:2373-2404`; `leads_research_v2.py:516-529,569-577`; `app/leads/outreach_playbook.py:140-147`; `app/leads/grounding_gate.py:120-125` |
| Fel mottagare (rekrytering@, Inköpschef) | Standardrollerna är VD, Inköpschef, Platschef. Kontaktuppgraderingen fäster vilken adress som helst på bolagets domän. | `lib/snajp/standard.ts:109`; `app/agent/leads_agent.py:380-403`; `discovery.py:225-235` |
| Bygg-slagsida, Göteborg/Umeå | Utan branscher bär sökprompten bara rollerna, och "Platschef" drar mot bygg. Profilkompilatorn har ingen regel mot att säljarens egna orter blir målgruppens geografi. | `discovery.py:1148-1153`; `app/leads/profil.py:406-438` |
| Skolor och kommuner | Ingen grind på organisationstyp utom i annonskällan. `orgnr.juridisk_form` finns men används inte. | `sources/jobtech.py:152`; `app/leads/orgnr.py:142`; `forfilter.py:40-71` |
| "bortvalda: ligger i göteborg" | Sammanfattningen visar kriteriets namn i stället för skälet. | `app/leads/korning.py:135,142`; `bedomning.py:206` |
| Instruktionerna skrevs över | Redigeraren skickar bara den nya texten, modellen ombeds formatera den till regler under sex fasta rubriker, och resultatet ersätter den enda aktiva raden. Därefter läser körningen aldrig `agent-core/AGENTS.md`. Ingen återställning finns. | `app/agentcore/strukturera.py:58-74`; `app/api/admin_profil.py:59-80,128-135`; `app/agentcore/instruktioner.py:146-150`; `components/admin/Agentinstruktioner.tsx:95-98` |

## Antaganden (säg till om något är fel)

1. **Sebbes uppdelning per agent finns inte i repot eller på origin.** Jag bygger den och utgår från supportprompten du klistrade in. Har Sebbe opushat arbete ska han pusha först, annars krockar vi.
2. **Grundmallen är en struktur, inte en färdig text.** Regeln "aldrig mall som utkast" står kvar: varje utkast genereras, mallen anger delarna och ordningen. Den generella strukturen gäller alla kunder. Snajps egen formulering ("Vi på Snajp bygger AI-agenter…") läggs som Snajps kundinstruktion för Iris.
3. **Bara VD med styrkt adress får ett Iris-utkast** (din regel 3). info@ och rekrytering@ ger inget utkast. Det sänker volymen ytterligare, och jag rapporterar hur mycket efter provet.
4. **Jag raderar inga leads.** De tre påhittade och övriga som faller på de nya grindarna listas, och du avgör vad som tas bort.
5. **Commit per fas på `development`, push på ditt ord.**
6. **Ordning:** fas 0–4 först (felen som skadar), sedan 5–6 (instruktionerna), sedan 7–8 (insynen och kundytan), sist 9 (kontextlagret). Inbäddningarna i fas 9 mäts dock redan i fas 0, eftersom svaret påverkar supportagenten i drift. Fas 7:s segmentlista byggs samtidigt som agentlagret i fas 5, eftersom båda rör `step_runner.py`.

## Fas 0 – Akut i development

- Läs `GET /api/admin/instruktioner` på development. Ligger mallraden kvar som aktiv kör alla agenter där utan sanningsreglerna. Jag visar dig läget och återställer till filen på ditt ord (skrivning mot spegeln).
- Jämför radens tidsstämpel med körningarna 21:25 och 21:41 för att veta om de kördes utan reglerna.
- Hämta mallens råtext ur radens `ravtext` så ingenting går förlorat.

## Fas 1 – Inga påhittade bolag (kodgrindar)

1. **Existensgrind för varje kandidat som inte kommer ur registret**, ny `app/leads/existens.py`, anropad i `korning.sokrunda` före Jev: startsidan måste gå att hämta (återanvänd `sidhamtning.hamta`, gratis först) och bolagsnamnet måste stå på den (`discovery.webbplats_matchar_namn`). Fel, timeout eller saknat namn ger bortval med skälet "Bolaget gick inte att styrka". Grinden fäller vid osäkerhet.
2. `webbsignal.mat_webbplats`: DNS-fel och timeout ger `har_webbplats: False` plus `svarar_inte`, inte `True`.
3. `merinfo.sok`: kredittak ger "stopp" i stället för `None`, så rundan avslutas med skälet "Sidhämtningskrediten är slut" och faller inte tillbaka på Gemini.
4. **Källan sparas**: `kalla` (merinfo, gemini, jobtech, namngivet) på prospektet via `_skapa_prospekt_ur_kandidat`. Sökmodellens `contact_email` sparas aldrig; adressen tas bara ur hämtat material.
5. **Bedömningen** (`bedomning.py`): ort och storlek ur kandidaten används bara när `kalla` är registret, och texten säger då "enligt registret". Nivå A kräver minst ett uppfyllt kriterium med belägg. Tomt material ger nivå C med skälet "Inget källmaterial".
6. **Research V2**: tomt material ger `stopped_early="inget_underlag"`, status blir inte Redo och inget utkast skrivs.
7. **Utkastgrinden** (`api/leads.py:2331`): kräver att `_leverbarhet` är godkänd.
8. **Sändspärren** (`app/leads/scheduler.py:86`): blockerar prospekt utan hämtat underlag.
9. `korning.sammanfatta` och `avsluta`: visa skälet ("Utanför målområdet"), inte kriteriets namn.
10. **Inventering**: `scripts/granska_leads_underlag.py` (läser bara) listar befintliga Iris-leads vars domän inte svarar eller som saknar hämtat material, per kund och miljö.

Tester (`tests/leads/test_existens.py`, tillägg i `test_discovery.py`, `tests/agent/test_leads_v2_wiring.py`): påhittad `.se`-domän som inte svarar faller, sajt utan bolagsnamnet faller, tomt material ger varken Redo eller utkast, kredittak ger ingen Gemini-sökning, sammanfattningens etikett. `tests/conftest.py` nollar även `GOOGLE_SERVICE_ACCOUNT_JSON`.

## Fas 1b – Bara leads som uppfyller kraven, nyaste överst (Antons krav 2026-10-06)

Anton såg leads vars motivering säger att de inte uppfyller kriterierna, och nya leads som hamnade mitt i listan. Kravet: visa bara leads som uppfyller kraven, och nyaste alltid överst.

| Orsak | Ändring |
|---|---|
| `bedomning.bedom` gav nivå B när ett måste-kriterium var okänt eller ett bör-kriterium hade ett uttryckligt nej | Varje nej fäller (även bör och webbkriterier); ett måste utan belägg fäller ("kravet kunde inte styrkas"); inget styrkt kriterium ger nivå C när profilen har kriterier |
| Modellens fria motivering ("uppfyller inte …") visades på godkända bolag | `_SAGER_NEJ`: en godkänd rad får kodens egen motivering |
| Ett bolag som föll på leverbarheten (tröskel, kontakt, kontaktväg) stod kvar som prospekt | `_run_batch_prospect` sparar nivå C med skälet |
| `GET /api/leads/prospects` skickade nivå C, tabellen gömde dem bakom "Visa bortvalda" | API:t filtrerar bort nivå C och `qualified=false`; knappen borttagen. Raden står kvar i databasen för dedupliceringen |
| Tabellen sorterade på nivå och poäng | `LeadsTabell.sortera`: `created_at` fallande, exemplen först |
| Jevs jämförelseklassning kördes även på bortvalda | Körs bara för kvalificerade (ett modellanrop mindre per bortvalt bolag) |

Följd: volymen sjunker, eftersom okända måste-krav tidigare blev B. Provkörningen mäter hur mycket.

Tester: `bedomning.demo()` (nej på bör fäller, okänt måste fäller, självmotsägande motivering ersätts), `tests/agent/test_leads_v2_utkastgrind.py` (modellens fria skäl och påhittade citat fäller fortfarande aldrig), `tests/invariants/test_inv_leads_exist_001.py` (listan returnerar aldrig nivå C).

## Fas 2 – Rätt målgrupp

1. **Bara privata bolag som standard.** `forfilter.forfiltrera` fäller organisationsnummer med prefix 2 (stat, region, kommun) via `orgnr.juridisk_form`, registrets bolagsform som inte är privat bolag, kommun- och myndighetsdomäner samt namnord (kommun, region, komvux, folkhögskola, gymnasium, grundskola, universitet, högskola, yrkeshögskola, myndighet). Profilen får flaggan `offentlig_sektor`, som kompilatorn bara sätter när kundens målgruppstext uttryckligen nämner offentlig sektor eller skolor.
2. Samma uteslutning läggs som standardrad i profilen, så researchmodellen bedömer gränsfallen med citat (Hermods Komvux är ett privat bolag men en skola).
3. **Profilkompilatorn** (`profil.py:406-438`): ny regel att säljarens egna orter inte är målgruppens geografi, och ett nytt fält `segment`: rangordnade målsegment med en mening om varför de passar kundens verksamhet.
4. **Körning utan filter**: sökningen tar segmenten i rangordning och växlar segment per runda. Saknar profilen segment startar ingen sökning; körningen svarar "Fyll i målgrupp".
5. `STANDARDROLLER` blir `["VD"]` (`lib/snajp/standard.ts:109`), och sökprompten ber bara om VD.

## Fas 3 – Rätt erbjudande, ingen webbpitch

1. Webbrevisionen körs bara när profilen har ett webbkriterium (`belagg == "webbsignal"`). Annars anropas den inte och inga webbrader når research, belägg eller utkast (`leads_research_v2.py:196-209,405-408,528`; `api/leads.py:2393`).
2. Stycket i `agent-core/overlays/leads-research-v2.md:68-69` om webbsignaler gäller bara när profilen har webbkriterier.
3. **Produktval**: `agent_configs.settings["produkter"]` (lista med namn, nytta och målsegment). Researchen väljer en produkt med motivering, och utkastet får den valda produktens stycke i stället för hela produkttexten (`api/leads.py:2404`). Kunder utan lista fungerar som i dag.
4. Förvillkoret `offer_selected` markeras i dag som uppfyllt för hand utan att något erbjudande valts (`leads_research_v2.py:588`). Det sätts bara när researchen faktiskt valt en produkt.
5. Test: kund utan webbkriterium ger en utkastprompt utan webbrader, och revisionen anropas inte.

## Fas 4 – Utkasten

1. **Utkastet får riktigt underlag**: citaten (`evidence`), lägesbeskrivningen, kontaktens namn och roll och den valda produkten (`api/leads.py:2373-2396`, `_utkastens_researchvy`).
2. **Underlagsgolv**: utan minst ett ordagrant citat från bolagets egen sajt skrivs inget utkast; leadet får noteringen "För tunt underlag för ett personligt mejl".
3. **Grundmallen** står i Iris-dokumentet (fas 5) som struktur: ämnesrad med konkret observation och företagsnamn, hälsning med VD:ns förnamn, observation ur källan, en mening om branschens vanliga utmaning (allmän, aldrig ett påstående om mottagaren), vilka vi är och vad vi gör, den valda produkten med en konkret nytta, en uppmaning. Snajps formulering läggs som Snajps kundinstruktion.
4. **Den amerikanska skillen `sa:draft-outreach` skopas snävare, bara i första-mejlets steg** (`outreach_playbook.py:140-147`, OUTREACH_V2 steg 1). Filen rörs inte (INV-SKILL-005); bara vilka sektioner steget läser ändras, med motivering (INV-SKILL-003).
   - **Ny mekanism: radändringar deklarerade i playbooken.** `PlaybookStep` får fältet `radandringar`: en lista med (exakt rad ur skillen, ersättning eller tom för struken, skäl). Motorn tillämpar dem på den lästa texten före anropet. Filen och manifestet är orörda, ändringen står i playbooken med motivering, bärs av versionshashen och visas i insynen ("playbooken har ändrat 3 rader i skillen"). Finns raden inte längre i skillen (efter en ny vendoring) faller importen, så en ändring kan aldrig tyst sluta gälla. INV-SKILL-003 utökas: varje radändring kräver motivering.
   - **Raderna som ändras i `sa:draft-outreach`:** AIDA-raden "[Desire: Brief proof point - similar company result]" ersätts med nyttan av den valda produkten, och bevis bara när ett namngivet case finns i underlaget. Mallraden "We helped [Similar Company] achieve [Result]" och motsvarande mening i Notion-exemplet stryks. "Step 2: Research First" (webbsökning modellen inte kan göra) ersätts med att researchen redan är gjord och är enda källan. LinkedIn-blocken stryks.
   - **Tre varianter mäts på fem riktiga bolag ur provkörningen** (femton modellanrop): (a) dagens skopa, (b) snäv skopa där hela sektionerna tas bort, (c) samma sektioner kvar med radändringarna. Den variant som ger noll påhittade case och bäst personalisering blir kvar. Min förväntan är (c), eftersom den behåller arbetsflödet och det arbetade exemplet.
   - *Mätt 2026-10-06* (`scripts/mat_skillvarianter.py`, 5 syntetiska fixtures × 3, gemini-2.5-flash via Vertex; de riktiga bolagen ur provkörningen ligger i development-spegeln och får inte läsas lokalt): noll påhittade case i alla tre; (a) och (b) gav varsitt påhittat förnamn ("Hej Mikael,"), (c) inget; personalisering (b) = (c) > (a). **(c) står kvar.** (b) var ~9 % billigare. Mätningen hittade två grindluckor som gällde alla varianter, rättade samma dag: hälsningen avgörs i kod mot VD:ns förnamn (`app/leads/tilltal.py`), och faktagrinden fäller oifyllda mallfält (`placeholder`). Benchmarkens modell `gemini-3.6-flash` finns inte på Vertex (404), så `benchmark_leads_kedja.py --modell gemini` är trasig.
   - Strukturen kommer i alla varianter ur grundmallen i Iris-dokumentet, som ligger efter skillen och vinner. Kallmejlsmallen i skillen tas ur skopan oavsett variant, eftersom två mallar i samma prompt konkurrerar.
   - **Senare alternativ, inte nu:** en egen svensk kallmejlsskill i namnrymden `snajp:`. Den ger full kontroll men kräver upplåsningsnyckeln och ett nytt manifest, alltså ny baslinje för alla kunder. Iris-dokumentet plus radändringarna ger samma effekt utan det steget.
   - Orört: humaniseringen, svarskedjan, uppföljningskedjan och V1. Uppföljningen läser hela skillen och får samma behandling först efter att första-mejlet mätts. Faktagrinden i punkt 5 är skyddsnätet för alla kedjor.
5. **Faktagrinden** (`grounding_gate.py`): ny typ för onamngivna case ("ett annat företag", "hjälpte nyligen", "liknande bolag", "vi har hjälpt") som fälls när kundens underlag saknar case. Test i `tests/agent/test_grounding_cycle.py`.
6. **Mottagaren**: utkast kräver roll VD och en adress som bär VD:ns namn eller står intill namnet på sajten (logiken i `discovery.hamta_vd_kontakt`). `_uppgradera_kontakt` fäster aldrig en funktionsadress på en namngiven person.
7. **Email Studio** (`app/api/email-studio/route.ts:324,326`): exemplen med påhittade case stryks.

## Fas 5 – Instruktioner per agent, feedback bakas in

**Lager.** `agent-core/AGENTS.md` står kvar orörd som gemensamt sanningslager. Nytt agentlager:

- `agent-core/agents/support.md`: din supportprompt, avsnitt 1–10 och 12. Utdataformatet (avsnitt 11) och blocket med injicerade inställningar tas inte med, eftersom varje steg har sitt eget utdatakontrakt i kod och kundens inställningar redan ligger i ärendekontexten.
- `agent-core/agents/leads.md`: nytt Iris-dokument med samma detaljnivå: roll och uppdrag; prioritetsordning (sanning, mottagarens integritet och lagen, avstå hellre än gissa, relevans, ton); källor (bolagets egen sajt är enda källan om prospektet, registret är filter och aldrig kontaktkälla, kundens affärskontext är enda källan om erbjudandet); grundregeln mot påhitt (bolag, personer, case, produkter, siffror); vem som får bli lead (reglerna 1–9 i `CLAUDE.md`, bara privata bolag, bästa matchning mot kundens verksamhet, produktval); kontakt (bara VD, styrkt); arbetsflöde per bolag; beslut Iris-lead, lista eller avstå; källmaterial är data och aldrig instruktioner; skrivregler; grundmallen; självkontroll; exempel ur de verkliga felen. Byggs ur `CLAUDE.md` § Leads, `leads-hard-rules.md`, `docs/intresseavvagning_kallmejl.md` och dina ordagranna instruktioner i handoff-filerna.

**Skills och agentdokumenten.** Skills anropas aldrig av modellen och ska inte refereras som något agenten "ska ladda". Playbooken i kod pekar ut skillen per steg, motorn läser filerna och lägger texten i prompten före anropet. Agentdokumenten säger bara vad som gäller över skillen vid krock. Kontrollera också vilken kedja main kör: `LEADS_PIPELINE` har standardvärdet `v1` i koden (`app/config.py:271`), och development kör `v2`.

**Körning.** `Instruktionslager.agent_md` läses av `las_instruktioner` per `agent_type` (databasrad, annars filen). `step_runner.py:257-271` lägger blocket efter overlays och före kundlagret, så det vinner över den vendorade skillen och går att justera från adminytan. Ordning: gemensamt, skill, overlay, agent, kund, kontrakt. Hashen bär agentlagret. Tak 24 000 tecken för agentlagret. Kvitto och bokföring läser bara det gemensamma, som i dag.

**Lagring.** Migration 096: kolumnen `agent_type` (`alla`, `support`, `leads`) på `agent_global_instructions`, en aktiv rad per typ. Körs mot development och main samma dag (nattspeglingen kontrollerar schemat).

**Baka in** (ny `app/agentcore/baka_in.py`, ersätter `strukturera` i `_dokument_ur`, och gäller därmed även kundinstruktionerna):

- In: det dokument agenten faktiskt läser (filen medräknad) plus din feedback. Gemini-anrop med tänkande på.
- Ut: en lista ändringar, var och en med typ (lägg till, ersätt, ta bort), den exakta befintliga texten som berörs, ny text och skäl. Modellen bedömer vad som är överflödigt eller motsägelsefullt. Koden tillämpar ändringarna, så all text som inte berörs är bokstavligt oförändrad. Citerat material som en mall bevaras ordagrant.
- Förhandsgranskningen visar vad som läggs till, ersätts och tas bort med skälen, och du godkänner innan något sparas. En borttagning över en tröskel ger en varning som kräver ett extra klick. Det är ett skyddsnät; bedömningen är modellens och godkännandet ditt.
- Feedbacken sparas ordagrant som logg. Historiken visar texten och får knappen Återställ.

**Adminytan** (`components/admin/Agentinstruktioner.tsx`, `lib/actions/agentinstruktioner.ts`): tre flikar (Gemensamt, Supportagenten, Iris), vänster ruta för feedback, höger ruta med hela resultatdokumentet och ändringarna markerade. Svenska och engelska i `lib/admin/sprak.ts` (INV-COPY-001). `Skill(design)` laddas före UI-ändringen.

Tester: `tests/agentcore/test_baka_in.py` (tillägg bevarar allt annat ordagrant, motsägelse ersätter, ankare som inte hittas rapporteras, mall bevaras ordagrant), tillägg i `test_overlays.py` och `test_instruktionslager.py` (ordning och hash), `test_admin_profil_api.py` (per agent, återställning). `scripts/verifiera_instruktioner.py` får en leads-markör.

## Fas 6 – Standardmålgrupper för Snajp

Läggs som `produkter` och `segment` på Snajps egna kunder (Snajp Admin workspace och Snajp Intern) med ett idempotent skript efter mönstret i `scripts/skapa_snajp_intern_kund.py`, torrkörning först.

| Segment | Support | Iris | Kvitto | Källa |
|---|---|---|---|---|
| Utbildnings- och kursföretag (säkerhet, certifiering, arbetsmiljö) | Stark | Stark | Medel | din tabell |
| Små e-handlare | Mycket stark | Svag | Stark | din tabell |
| Bygg, hantverk, installation | Svag | Medel | Mycket stark | din tabell |
| Konsult- och byråbolag | Svag | Stark | Stark | din tabell |
| B2B-tjänster med serviceavtal (fastighetsservice, städ, larm, företagshälsa) | Stark | Stark | Medel | förslag |
| Små IT- och SaaS-bolag med företagskunder | Stark | Stark | Medel | förslag |
| Grossister och B2B-handel | Stark | Stark | Medel | förslag |
| Uthyrning och bokningsbaserade tjänster (maskiner, konferens, event) | Stark | Medel | Stark | förslag |
| Redovisningsbyråer | Medel | Stark | Mycket stark, som partnerkanal | förslag |

Uteslutet som standard: kommuner, regioner, myndigheter, statliga bolag, skolor, ideella föreningar, enskilda firmor, vård och juridik (känsliga uppgifter), bolag över 250 anställda. Iris väljer segment efter kolumnen för den produkt som passar bolaget bäst; Leads-kolumnen väger tyngst när inget annat anges.

## Verifiering

1. `pytest` i `snajp-support/` (hela sviten, 2 567 gröna i dag), `pytest tests/invariants`, `npx tsc --noEmit`. En tung process åt gången.
2. `python scripts/verifiera_instruktioner.py`: markörerna för gemensamt lager, agentlager och kundlager landar rätt för både support och leads.
3. Adminytan lokalt (`python scripts/lokal_stack.py --apply`, aldrig mot spegeln): klistra in mallen som feedback under Iris. Förhandsgranskningen ska visa ett tillägg och noll borttagningar, mallen ska stå ordagrant, och Återställ ska ge tillbaka föregående version. Skärmbild.
4. Efter push och deploy till development, på ditt ord: Iris-körning N=5 som Snajp utan filter. Jag kontrollerar varje lead för hand: domänen svarar, bolagsnamnet står på sajten, minst ett citat, ingen webbpitch, VD som mottagare, inget offentligt bolag, flera segment. Kräver ScrapeGraph-kredit.
5. `scripts/granska_leads_underlag.py` mot development: listan över befintliga leads som faller på de nya grindarna går till dig.
6. Supportagenten: `python scripts/kor_evals.py` före och efter agentlagret, eftersom Livrustning kör skarpt.
7. Insynen: öppna Underlag och flöde för Snajp och Iris lokalt. Lagerstapeln för utkaststeget ska visa alla sex systemlager och hela användarmeddelandet, skillfilerna ska bära "orörd", och uppspelningen av en körning med ett bolag utan källmaterial ska peka ut researchnoden. Skärmbilder i 1440 och 375.
8. Kundytan: spara en produkt och ett segment som kund, skriv en feedback, godkänn förhandsgranskningen och se i källmatrisen att texten når utkaststeget i användarposition.

## Fas 7 – Insyn: allt agenten läser, visat som flöde

**Läget i dag (kontrollerat 2026-10-06).** Skillkedjan är hel: 414 filer, noll avvikelser mot manifestet (`1ec41e2d0551`), och varje steg i alla tio playbooks renderar. Men spårvyn (`app/admin/korningar/[id]/page.tsx`) kapar varje fält vid 8 000 tecken (`step_runner.py:138`). Utkaststegets systemprompt är runt 19 000 tecken, så overlay, kundlager och kontrakt syns aldrig, och inte heller slutet av användarmeddelandet. Anropen utanför stegmotorn (bolagssökningen, profilkompileringen, Jev, webbrevisionen, korrekturen) lämnar inget spår alls. De påhittade bolagen kom ur ett sådant anrop.

**Ny vy: Admin › Kund › Underlag och flöde** (väljare för agent), fyra delar på samma yta:

1. **Flödeskartan, byggd ur playbookerna.** Kartan genereras ur `Playbook`-objekten i koden, inte ur en handskriven beskrivning. Varje playbook (`support/v1`, `leads/research-v2`, `leads/outreach-v2`, grundningsreparation, svar, uppföljning) är en egen bana med sina steg i körordning, och kodgrindarna ligger som egna noder mellan dem. Iris: källa, förfilter, existensgrind, Jev, research, bedömning i kod, kontaktkontroll, utkast, humanisering, faktagrind, kö. Varje stegnod visar **hur skillen valdes**: vilken skill playbooken pekar ut, om hela skillen eller en skopa läses och playbookens egen motivering till skopan, extra skills i samma steg, overlays, vad steget kräver av föregående steg, villkoret för villkorade steg (till exempel "eskalering körs bara vid kunskapslucka, säkerhetssignal eller när kunden ber om en människa"), modell och temperatur. Kartan visar också vilken kedja miljön kör (v1 eller v2).
2. **Lagerstapeln.** Klick på ett steg visar prompten exakt som den byggs, lager för lager i verklig ordning: gemensamt, skill, overlay, agentlager, kundlager, kontrakt, och i användarmeddelandet uppdrag, erbjudande, kontextpaket (affärskontext, vad ni säljer, målgrupp), profil, röstdokument, källmaterial eller kunskapsbasträffar. Varje lager bär källa (fil eller tabell), vem som får ändra det, antal tecken, hash och länk till redigeringen. Skill-lagret går att fälla ut till de enskilda filerna och sektionerna, var och en med märket "orörd" efter kontroll mot manifestet, och går att läsa i sin helhet.
3. **Källmatrisen.** Rader: varje underlag (gemensamma regler, agentdokument, kundinstruktion, affärskontext, vad ni säljer, produkter, målgrupp och profil, röstdokument, kunskapsbas, kundens egna önskemål). Kolumner: stegen. Cellen säger om texten läses där, i vilken position och hur många tecken. Rött betyder att ett ifyllt underlag inte når något steg, eller att ett steg kräver ett underlag som är tomt. Klick öppnar prompten med stycket markerat.
4. **Välj en enskild körning och se hela flödet.** En väljare med de senaste körningarna, filtrerbar på kund, agent, bolag eller ärende. Den valda körningen ritas på samma karta, färgad efter utfall: vilka steg som kördes, vilka som hoppades över och varför (villkoret föll, kedjan stannade tidigt), in- och utdata per steg, kodgrindarnas utslag och skälet där kedjan stannade (till exempel "Källmaterial: 0 tecken" på researchnoden). Under kartan står **Skills i den här körningen**: steg, skill, exakt vilka filer och sektioner som lästes, antal tecken, hash och om filen var orörd mot manifestet vid körningen. Nås också från leadets låda, från ärendet och från körningens rad.

Dessutom **Prova en fråga** för kunskapsbasen: en fråga in, vilka artiklar som skulle hämtas ut, utan modellanrop.

**Så blir visningen sann och inte en parallell beskrivning:**

- Systempromptens hopsättning bryts ut ur `run_step` till `bygg_systemprompt(step, lager, roll)`, som ger en lista segment (etikett, källa, position, text). `run_step` fogar ihop samma lista; insynen visar den. Ett test kräver att de är teckenidentiska.
- Användarmeddelandet byggs på samma sätt som segment i `leads_research_v2.py` (research och utkast) och `support_agent.py`.
- **Spårvyns tak på 8 000 tecken ersätts av lagring per lager.** `StepResult` sparar segmentlistan i `step_log`. De stabila lagren (gemensamt, skill, overlay, agentlager, kundlager, kontrakt) sparas som namn, källa, tecken och hash, och själva texten läggs en gång per unik hash i en ny tabell `prompt_lager` (migration 097, `insert … on conflict do nothing`). En skilltext på 11 000 tecken lagras alltså en gång, inte en gång per körning, och går alltid att visa exakt som den såg ut, även efter att filen ändrats. Det som varierar per körning (källmaterial, ärendetext, research) sparas i sin helhet på steget.
- Spårvyn (`app/admin/korningar/[id]/page.tsx`) byter de fyra fällbara råfälten mot lagerstapeln och kartan. Äldre körningar, som bara har de kapade fälten, visas som i dag med en rad som säger att spåret är kapat.
- **Gallring av fulltexten:** förslag 30 dagar för den varierande texten (den bär kundmejl och bolagsmaterial), därefter står bara mätvärden och hashar kvar. Perioden är ditt beslut; tills du sagt ett tal gallras inget, som i dag.
- Anropen utanför stegmotorn loggas som egna poster: bolagssökningen (prompt, råsvar och sökningens källadresser), profilkompileringen, Jev, webbrevisionen. Kodgrindarnas utslag (existens, förfilter, bedömningens rader, faktagrinden) sparas per bolag i körningens tratt.

Ny kod: `app/agentcore/insyn.py`; endpoints `GET /api/admin/tenants/{id}/insyn`, `GET /api/admin/skills/fil`, `POST /api/admin/tenants/{id}/insyn/kb-prov`, `GET /api/admin/prospects/{id}/kedja`; komponenter under `components/admin/insyn/`. `Skill(design)` och `DESIGN.md` styr utformningen, svenska och engelska i `lib/admin/sprak.ts`.

Tester: segmentlistan är identisk med den skickade prompten; ett ifyllt underlag som inte når något steg ger rött i matrisen (prövat med ett avsiktligt dött fält); uppspelningen av en körning med tomt källmaterial pekar ut researchnoden; skillfilen som visas stämmer mot manifestet.

## Fas 8 – Kundens egen yta: produkter, segment och egen feedback

1. **Produkter och segment i kundens inställningar.** Under Vad ni säljer: lista med produkter (namn, nytta, vilka segment den passar och hur starkt). Under Målgrupp och automation: rangordnade segment och uteslutningar, med rutan "Vi säljer till offentlig sektor och skolor" som sätter `offentlig_sektor`. Sparas i `agent_configs.settings` och läses av profilkompilatorn och produktvalet i fas 2–3. Skriptet i fas 6 fyller i Snajps egna värden; sedan går de att ändra här.
2. **Kundens egen feedback till sin agent.** En ruta per agent där kunden skriver feedback med egna ord. Samma `baka_in` som i fas 5, med förhandsgranskning, historik och Återställ. Skillnaden: basdokumentet är kundens eget (`agent_context_docs`, typ `kundonskemal_<agent>`), och det läggs i **användarposition**, inslaget som opålitligt innehåll under rubriken "Kundens egna önskemål", precis som röstdokumentet (INV-SEC-009). Kunden kan styra ton, fokus och formuleringar men kan inte upphäva reglerna, och kodgrindarna körs efteråt som vanligt. Våra lager i systemposition rörs aldrig av kundens feedback. Tak på antal inbakningar per dygn och kund.
3. Båda syns i källmatrisen (fas 7), så det går att se att kundens text når rätt steg.

*Byggt 2026-10-06:* `components/leads/IrisProdukter.tsx`, `components/settings/AgentOnskemal.tsx` (Iris › Inställningar och Inställningar › Regler), `app/leads/onskemal.py`, migration 102, förhandsvisning `/forhandsvisning/kundinstallningar`. A11y-granskningens sex HIGH-fynd i de nya filerna är rättade och mätta (fokus stannar på knappen eller flyttas till Ändringar, ångra vid borttagning, inget sparbart formulär efter misslyckad hämtning, hela feedbacken nåbar).
**Skuld i husets mönster, inte nytt här:** fältkanten `border-ink/15` på `bg-paper` mäter 1,37:1 (ljust) och 1,47:1 (mörkt) mot kravet 3:1 (WCAG 1.4.11), i 17 filer; `btnLiten` är 36 px (klarar 2.5.8 AA, under 44 px-rekommendationen, beslutat i DESIGN.md). Rättas som ett eget pass över hela appen, inte i två filer.

Tester: kundens önskemål hamnar i användarmeddelandet och aldrig i systemprompten (tillägg i `tests/invariants/test_inv_sec_009.py`); en feedback som ber agenten strunta i reglerna ändrar inte systemlagren; produkter och segment sparade i ytan når profilen och utkastet.

## Fas 9 – Kontextlagret: vad Redis Iris ger oss och vad vi gör i stället

**Genomgången (dokumentationen läst 2026-10-06).** Redis Iris är fyra hanterade tjänster ovanpå Redis Cloud, alla i publik förhandsversion utom där annat anges. Ingen av dem löser felen i fas 1–5, som sitter i kedjan och grindarna. Genomgången pekar däremot ut vår verkliga svaghet i kontextlagret: inbäddningarna.

| Tjänst | Vad den gör | Vad vi redan har | Bedömning |
|---|---|---|---|
| LangCache | Semantisk cache av modellsvar, tröskel 0,85, högst fem attribut för avgränsning, egen inbäddningsmodell | `app/cache/svarscache.py`: per kund, tröskel 0,90, bara första kontakt utan personuppgifter, bara faktakategorier, ogiltig när kunskapsbasen eller inställningarna ändras | Avstå. Vår är strängare och bättre anpassad. En cache höjer aldrig skärpan, den kan bara sänka den. Leads har inget att cacha. |
| Agent Memory | Sessionsminne med automatisk summering, långtidsminne som en modell extraherar, egna minnestyper, sökning | `app/minne/arbetsminne.py` (rullande summering) och kundminnet (bara det kunden själv sagt, aldrig agentens slutsatser) | Avstå nu. Modell-extraherade minnen bryter mot vår kontamineringsspärr, sessionsinnehållet går till en modelleverantör som inte namnges när Redis egna nycklar används, och de inbyggda detektorerna saknar svenska personnummer och telefonnummer. Omprövas när tjänsten är allmänt släppt och om en kund får långa samtal över flera kanaler. |
| Context Retriever | Gör en datamodell till fasta MCP-verktyg med åtkomsttaggar | Supportagentens uppslag mot kundens egna system (`app/integrationer/uppslag.py`) | Avstå. Kräver att datan ligger i vår Redis, och våra agenter är fasta kedjor där modellen inte anropar verktyg. Principen (fasta verktyg i stället för fria frågor) följer vi redan. |
| Data Integration | Speglar en relationsdatabas till Redis i nära realtid | — | Avstå. Förhandsversion bara för Pro-databaser på AWS, och vi har ingen läslast som Postgres inte klarar. |
| Redis Search | Vektor-, fulltext- och hybridsökning | Används redan för svarscachens index. Kunskapsbasen söks i Postgres med pgvector och svensk fulltext, bakom radnivåsäkerhet per kund. | Behåll som i dag. Att flytta kunskapsbasen till Redis tappar radnivåsäkerheten och kräver synk. |

**Det som faktiskt höjer skärpan, och som genomgången ledde fram till:**

1. **Laga inbäddningarna.** Statusjournalen 2026-09-12 säger att inbäddningar via Vertex OpenAI-kompatibla väg är trasig (500 hos Google) och att kunskapsbasen därför söks med enbart fulltext. Koden går fortfarande den vägen (`app/agent/embeddings.py:56`). Först mäts läget i development. Är det fortfarande trasigt byts anropet till Vertex egna inbäddnings-API i EU-regionen. Utan inbäddningar missar supportagenten omformulerade frågor och eskalerar i onödan, svarscachen kan inte träffa, och punkt 3 nedan går inte att bygga.
   *Byggt 2026-10-06:* `POST /api/admin/kb/badda-in` + `scripts/badda_in_kb.py` (torrkörning som standard) fyller på vektorer för artiklar som saknar dem.
2. *Rättelse 2026-10-06: hybridsökningen finns redan sedan 2026-08-26* (`search_kb` kör vektor och fulltext och slår ihop med RRF, k=60). Påståendet nedan om antingen-eller var fel; det som saknades var vektorerna (punkt 1). Ursprunglig text: **Hybridsökning i kunskapsbasen** i Postgres: vektor och svensk fulltext körs båda och rangordningarna vägs ihop, i stället för dagens antingen-eller (`postgres.py:790`). Mäts mot evalsviten före och efter.
3. **Iris lär sig av kundens utslag.** I dag blir kundens feedback på leads bara evalfall och når aldrig en prompt. Varje godkänt, avvisat och skickat lead sparas med skäl och inbäddning. Vid bedömningen av ett nytt bolag hämtas kundens tre mest lika tidigare utslag som kalibrering till Jev och researchen, i användarposition och inslaget som opålitligt innehåll. Det är människans utslag, inte agentens egna slutsatser, så INV-LEARN-001 hålls. Byggs på pgvector, ingen ny tjänst. Avvisade bolag utesluts dessutom deterministiskt ur kommande sökningar.
   *Byggt 2026-10-06 (`app/leads/utslag.py`):* utslag = manuella statusbyten i statusloggen (086), kontaktad/svarat/möte/vunnen = ja, förlorad/spärrad = nej; ingen ny tabell. Kalibreringen går bara till researchen. **Avvikelse:** inte till Jev, eftersom Jev (TypeSafe, tredje part) enligt Antons beslut 2026-09-30 aldrig ser kundens egna data. Uteslutningen fanns redan: prospektraden står kvar i `leads/upptagna.py`.
4. **Promptbudget.** Utkaststeget får i dag produkttexten två gånger (erbjudandet och kontextpaketet). Efter fas 3 får det bara den valda produkten, en gång.

**Alternativ som vägts och varför de inte valdes nu:**

- *LangCache som bakände till vår egen grind*, i skuggläge. Lockande eftersom den har egen inbäddning och alltså fungerar även om vår är trasig. Avstår eftersom den inte höjer skärpan, eftersom den svenska träffkvaliteten är okänd, och eftersom det inte framgår var Redis inbäddningsmodell körs. Går att prova senare med syntetiska frågor lokalt, aldrig mot spegeln.
- *Agent Memory med egen nyckel* (Vertex, om leverantören går att välja i konsolen) för minne över kanaler. Rimligt först när identiteten över kanaler är löst hos oss; lagringen är inte det svåra.
- *Context Retriever över vår egen leadsdata* för en "fråga dina leads"-assistent. Kräver Pro och spegling; ett par fasta SQL-frågor ger samma svar.

**Två saker för dig:** Redis marknadsför nu "Iris" som namn på en produkt för AI-agenter, samma namn som vår leadsagent. Värt att känna till inför varumärkesarbetet. Och varje ny Redis-tjänst som tar emot kundtext måste in i underbiträdeslistan och PUB-avtalet innan den slås på.

Tester: inbäddningsanropet ger vektorer i development (mätt, inte antaget); hybridsökningen hittar en omformulerad fråga som fulltexten missar; kalibreringen hämtar bara den egna kundens utslag; ett avvisat bolag kommer inte tillbaka i nästa körning.

## Fas 1c – Produktmatchning för varje lead (Sebbes krav 2026-10-06)

### Completed
- [x] Kriteriet `kp` i `bedomning._produktmatch_rad`: bara ett belagt ja blir ett lead; ingen vald produkt (när kunden har en lista) fäller (`aa02fc2`).
- [x] Prompt, overlay och INV-LEADS-EXIST-001 uppdaterade; V1 fäller tomt källmaterial.
- [x] Ombedömning av sparade leads: `admin_ombedom.py` + `scripts/ombedom_leads.py` (`63b9cf1`, `038541d`).
- [x] Körd i development: 51 leads, alla 30 med material bär `kp`, kvar synliga Snajp 3, Alunix 0.

### Remaining
- [ ] 21 leads föll utan bedömning (ScrapeGraph-krediten slut): `ombedom_leads.py --env development --utan-underlag --apply` efter påfyllning.
- [ ] Ombedömning mot main efter mergen, på Antons ord (`--apply --main-godkant`).
- [ ] Mät leverans per Iris-körning under de skärpta reglerna.

### Blockers
- ScrapeGraph-kredit; Antons migrationer 096–099 mot main och merge av PR #31.

## Utanför den här planen

- Release till main: PR från development, din merge.
