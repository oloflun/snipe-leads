# Uppgifter i ISO 42001-ramverket

De 61 uppgiftsmallarna som ramverket `frk_68cc0e2a21184ed168ab2eea` (commit `712ee1b3`) kopplar till sina kontroller. Namn, id och frekvens är mallens. "Kräver" sammanfattar mallens text och acceptanskriterier. Status med plattformens värden (`todo`, `in_progress`, `in_review`, `done`, `not_relevant`). Vem: **Ä** = Anton, **S** = Sebbe, **A** = agent. Hänvisningar som i `matris.md`.

Uppgifterna är grupperade efter ämne men inte sammanslagna; varje mall har sin egen post.

Uppdaterad 2026-11-18. "Ändr. 11-18" efter statusen betyder att posten ändrats den dagen. **Summering 2026-11-18:** 0 `done`, 24 `in_progress`, 1 `in_review`, 36 `todo`. Förändring från 2026-11-17: `todo` 46 → 36, `in_progress` 14 → 24, `in_review` 1 → 1, `done` 0 → 0. Tio uppgifter gick till `in_progress` för att ett utkast eller en åtgärd i drift finns; ingen kan stängas.

## Kan stängas i dag

**Ingen uppgift kan stängas som `done` med befintligt bevis.** Närmast:

- **AI Verification & Validation Report:** rapporten finns (`docs/stabilitet-2026-11/eval/`, Slutrapport rad 30-41). Saknar godkännare och ett acceptansbeslut. Stängs om Anton skriver under resultatet från 2026-11-10 som godkänt eller med åtgärder.
- **AI System Event Logging Configuration:** loggningen finns (matris A.6.2.8). Saknar beslutad lagringstid och åtkomstregel för `agent_runs`.
- **Contact Information:** kontaktadressen är publik. Saknar logg över inkomna klagomål.

---

## Delade med ISO 27001 och GDPR (15)

Samma id som i `../iso27001/uppgifter.md` (och `../gdpr/uppgifter.md` för de fem delade där). Den filen gäller; här står bara det ISO 42001 lägger till.

1. **Access Review Log** · `frk_tt_68e805457c2dcc784e72e3cc` · kvartalsvis. Inget tillägg. Rutinen som utkast (`../../underlag/rutiner/d-atkomstgenomgang.md`). `in_progress` · ändr. 11-18.
2. **App Availability** · `frk_tt_68406d2e86acc048d1774ea6` · årligen. Tillägg: kopplad till A.4.5, beräkningsresurser för AI. Vertex-region belagd (Inv. §2.1), Jev hos TypeSafe i USA, sedan 2026-11-17 bara för leads. `todo` · ändr. 11-18.
3. **Backup Restoration Test** · `frk_tt_68e52b269db179c434734766` · årligen. Inget tillägg. Inga kopior finns; Railway kräver Pro-planen (BU A4). `todo`.
4. **Code Changes** · `frk_tt_68406d64f09f13271c14dd01` · årligen. Tillägg: ändringar av modell, prompt och data ska granskas för risk, etik och efterlevnad. Modellbyten beslutas med mätning (BESLUT 1647-1664), men ingen AI-granskning i PR. Vem: Ä, A. `in_progress`.
5. **Employee Access** · `frk_tt_68406ca292d9fffb264991b9` · årligen. Tillägg: rollbeskrivningar ska nämna ansvar i AI-ledningssystemet. Saknas (P27 avsnitt 5). Kontoförteckningen som mall i `../../underlag/rutiner/d-…`. `in_progress` · ändr. 11-18.
6. **Employee Verification** · `frk_tt_68406951bd282273ebe286cc` · årligen. Tillägg: kopplad till A.4.6, vem som arbetar med AI-systemen och med vilken kompetens. Saknas. `todo`.
7. **Encryption at Rest** · `frk_tt_68e52b26bf0e656af9e4e9c3` · årligen. Inget tillägg. `todo`.
8. **Incident Response** · `frk_tt_68406b4f40c87c12ae0479ce` · årligen. Tillägg: AI-avvikelser och kommunikation av AI-incidenter till användare (10.2, A.8.4). AI-fel blir invarianter men förs inte in i incidentloggen. Vem: Ä, A. `in_progress`.
9. **Monitoring & Alerting** · `frk_tt_68406af04a4acb93083413b9` · årligen. Tillägg: bevaka AI-specifika risker (försämrad kvalitet, avvikelser). Driftövervakning med provad larmkedja finns (ärende 53; `../gdpr/uppgifter.md` nr 11), men ingen AI-specifik bevakning; internlarmen saknar variabler. Vem: Ä, A. `in_progress` · ändr. 11-18.
10. **Planning** · `frk_tt_68406e7abae2a9b16c2cc197` · årligen. Tillägg: AI-systemen i kontinuitetsplanen, t.ex. vad som händer när Vertex inte svarar. Kreditslut hanteras (AI-inv. 508-550); ingen plan. `todo`.
11. **Production Firewall & No-Public-Access Controls** · `frk_tt_68fa2a852e70f757188f0c39` · årligen. Inget tillägg. Redis på Railways privata nät; Postgres publika proxy kvar (`../iso27001/uppgifter.md` nr 17). `in_progress` · ändr. 11-18.
12. **Public Policies** · `frk_tt_6840791cac0a7b780dbaf932` · årligen. Tillägg: policyerna ska säga hur kunders, myndigheters och samhällets rättigheter hanteras. Delvis i villkoren (`VillkorSida.tsx:30-41`). AI-upplysningen och policyns AI-avsnitt mergade till development (PR 45, 51), inte i main förrän PR 60. Vem: A, Ä. `in_progress` · ändr. 11-18.
13. **Sanitized Inputs** · `frk_tt_68406eedf0f0ddd220ea19c2` · årligen. Inget tillägg; opålitlig text i modellanrop ramas in (AI-inv. 219-317). `in_progress`.
14. **Secure Devices** · `frk_tt_6840796f77d8a0dff53f947a` · årligen. Inget tillägg. Mall som utkast (`../../underlag/rutiner/e-enheter.md`). `in_progress` · ändr. 11-18.
15. **Separation of Environments** · `frk_tt_68e52a484cad0014de7a628f` · årligen. Inget tillägg; egen Redis per miljö sedan 2026-11-17, men samma Vertex-servicekonto i båda miljöerna (JA #14). `in_progress` · ändr. 11-18.

## Ledningssystemet (13)

16. **AIMS Scope Statement** · `frk_tt_69ea915ebae9e6858fa4fa07` · årligen. Kräver godkänt omfång med system, roller och undantag. Finns: förslag i P27 avsnitt 1 och beslutsutkast `../../underlag/beslut/e-omfattning-ledningssystem.md`. Saknas: signatur. Ä. Kan stängas när beslutet signeras. `in_progress` · ändr. 11-18.
17. **AIMS Manual** · `frk_tt_69ea915f44950702d9f7733c` · årligen. Kräver ett huvuddokument med processer, ansvar och hänvisningar. Finns: inget. Förslag: P27 plus `matris.md` räcker för två personer. Ä. `todo`.
18. **AI Leadership Commitment Record** · `frk_tt_69ea9161097ef7eb142b70ff` · årligen. Kräver daterat godkännande av AI-policy och mål. Finns: inget. Ä. `todo`.
19. **AI Policy Review** · `frk_tt_69ea9163eb166db383bb2140` · årligen. Kräver dokumenterad översyn med versionsnummer. Finns: inget, policyn är utkast. Ä. `todo`.
20. **AI Policy Alignment Review** · `frk_tt_69ea916227fbbb6a722126b6` · årligen. Kräver genomgång av krockar mot övriga policyer. Finns: kopplingarna i P27 avsnitt 10 och genomgången som utkast (`../../ai-system/policy-samstammighet.md`, 2026-11-18). Saknas: Antons beslut om förslagen, och en ny genomgång mot de godkända versionerna. A förbereder, Ä godkänner. `in_progress` · ändr. 11-18i.
21. **AI MS Roles & Responsibilities Assignment** · `frk_tt_68cc2ce9cb0d2a4774975ace` · årligen. Kräver roller med ansvar och rapportering. Finns: rolltabellen i P27, två rader [FYLL]; beslutsutkast `../../underlag/beslut/a-…` med systemägare [FYLL]. Ä, S. `in_progress` · ändr. 11-18.
22. **AI MS Resource Allocation Record** · `frk_tt_68cc30fbbeabb8a4c2f56082` · årligen. Kräver belägg för avsatta resurser. Finns: inget. Ä. `todo`.
23. **AI Objectives Register** · `frk_tt_68cc2fa423533e602e4dee25` · årligen. Kräver mätbara mål med ansvarig och uppföljning. Finns: produktmål i Slutrapport rad 82-87; förslag i P27 avsnitt 7. Ä. `todo`.
24. **AI MS Communication Plan** · `frk_tt_68cc327ff5d3130a1b42420b` · årligen. Kräver plan för vad, när, till vem, hur. Finns: inget samlat. A skriver, Ä godkänner. `todo`.
25. **AIMS Documented Information Index** · `frk_tt_69ea916a881ab0d59e67c930` · årligen. Kräver register över styrdokument med version, plats och lagringstid. Finns: inget. A. `todo`.
26. **AI MS Operational Control Procedure** · `frk_tt_68cc395b90e179fe3209b795` · årligen. Kräver procedur för kriterier, ändringar och externt levererade AI-tjänster. Finns: kriterier i kod (`processor.py:752-759`); beslutsutkast om godkännande av ny modell eller leverantör (`../../underlag/beslut/f-…`); Jev stoppad för kundmejl i drift; AI Studio-spärren i development. Saknas: signerad procedur. Ä. `in_progress` · ändr. 11-18.
27. **AI MS Internal Audit Program** · `frk_tt_68cc4190caf0b458effcee6e` · årligen. Kräver program med frekvens och oberoende revisor. Finns: inget. Ä. `todo`.
28. **AI Internal Audit Reports** · `frk_tt_68cc41ad7cbd2839c0bc7104` · årligen. Kräver revisionsrapporter. Finns: `matris.md` är en genomgång, inte en revision. Ä. `todo`.

## Uppföljning och förbättring (3)

29. **AI Management Review Minutes** · `frk_tt_69ea917c23d26cfe23eb8fca` · årligen. Kräver protokoll som täcker 9.3.2. Finns: inget. Ä. `todo`.
30. **AI MS Continual Improvement Log** · `frk_tt_68cc459ed57b70a4cb631e72` · årligen. Kräver versionerad förbättringslogg. Finns: BESLUT.md fungerar för agenterna. Saknas: förbättringar av ledningssystemet. Ä. `todo`.
31. **AI Context Register** · `frk_tt_68cc25658bacb2ccff56adf9` · årligen. Kräver register över interna och externa frågor, roller och syften. Finns: `ai-forordningen.md` §1, Inv. §2. A skriver, Ä godkänner. `todo`.

## Risk och konsekvens (6)

32. **AI Risk and Opportunity Register** · `frk_tt_69ea9164c6574221a69e1107` · årligen. Kräver register för ledningssystemets risker och möjligheter. Finns: inget särskilt. Ä. `todo`.
33. **AI Risk Assessment Execution (Log)** · `frk_tt_68cc39efd7916e240451cae5` · årligen. Kräver AI-risker i riskregistret. Finns: `risks` i `import.json` här (8 poster), DPIA R1–R13. Saknas: godkännande och riskkriterier. Ä. `in_progress`.
34. **AI Risk Treatment Implementation Record** · `frk_tt_68cc3f427e309607f1ad5ba4` · årligen. Kräver belägg för genomförd behandling och uppföljning. Finns: åtgärder med tester (AI-inv.). Saknas: koppling till en plan. A, Ä. `todo`.
35. **AI System Impact Assessment Procedure** · `frk_tt_68cc2f30b51920e5515465e6` · årligen. Kräver en process för konsekvensbedömning. Finns: förslag i P27 avsnitt 8. Ä. `todo`.
36. **AI Impact Assessment Log** · `frk_tt_68cc3ffab3fb703917f51e19` · årligen. Kräver dokumenterade bedömningar. Finns: DPIA, IA (utkast 2026-11-17). Saknas: Jev; juristgranskning. A, Ä. `in_progress`.
37. **AI Societal Impact Assessment** · `frk_tt_69ea9165056eb451ccc79c0f` · årligen. Kräver samhällsbedömning per system. Finns: inget. A skriver, Ä godkänner. `todo`.

## AI-systemens livscykel (9)

38. **Responsible AI Development Objectives** · `frk_tt_69ea916b05b146a8a544c406` · årligen. Kräver godkända mål med mått. Finns: Antons krav 2026-11-16 (BESLUT 101-110). Saknas: mått och godkännande. Ä. `todo`.
39. **AI System Requirements and Specification** · `frk_tt_69ea916c7b0b9487da3dbe78` · årligen. Kräver kravdokument per system. Finns: invarianter och leadsregler. Saknas: dokumentet. A, Ä. `todo`.
40. **AI Design and Development Documentation** · `frk_tt_69ea916e273fdb8732d89fc6` · årligen. Kräver designdokument per system. Finns: Iris (`docs/UTKASTKEDJAN-REFERENS-2026-10-16.md`). Saknas: support, Jev. A. `in_progress`.
41. **AI Verification & Validation Report** · `frk_tt_69ea916f42193436fb7b55de` · kvartalsvis. Kräver rapport med mått mot mål och beslut. Finns: före- och efterkörning (Slutrapport). Saknas: godkännare, Jev. Ä. `in_progress`, kan stängas med Antons underskrift.
42. **AI System Technical Documentation (Model Card)** · `frk_tt_69ea917139f2541637597cc4` · årligen. Kräver modellkort per system. Finns: kundförklaringen av faktakontrollen. A. `todo`.
43. **AI System Event Logging Configuration** · `frk_tt_69ea91725a27f56747512056` · årligen. Kräver loggschema, lagring, åtkomst och utdrag. Finns: AI-inv. 394-404, `insyn.py`. Saknas: lagringstid (DPIA R10). A, Ä. `in_progress`.
44. **AI System Operation & Monitoring Plan** · `frk_tt_69ea917069457debb719152e` · kvartalsvis. Kräver mått, gränser, larm och senaste rapport. Finns: driftövervakning av tillgängligheten, ingen AI-mätning. A, Ä. `todo` · ändr. 11-18.
45. **AI System Change Log** · `frk_tt_68cc301a8fd914534ab95b11` · årligen. Kräver logg över modell-, prompt- och styrningsändringar. Finns: BESLUT.md, `pack_version` per körning (AI-inv. 394); ändringen av `INKORG_JEV` 2026-11-17 dokumenterad i beslutsunderlaget och i konfigurationsexporten före och efter. Saknas: löpande logg över miljövariabler. A, Ä. `in_progress` · ändr. 11-18.
46. **AI Tooling Inventory** · `frk_tt_69ea9167679a59212c7db16f` · årligen. Kräver förteckning med version, licens och godkännande. Finns: `agent-core/manifest.json`, modellnamn i config. A. `todo`.

## Data (5)

47. **AI Data Resource Register** · `frk_tt_69ea9166fd0793a689981939` · årligen. Kräver dataregister per system. Finns: `docs/registerforteckning.md`, DPIA §1. A. `todo`.
48. **AI Data Acquisition Record** · `frk_tt_69ea9173e73c9a96895468c8` · årligen. Kräver källa, grund och licens per datamängd. Finns: källa, datum och grund per prospektfaktum (AI-inv. 117). Saknas: avtal med allabolag och hitta. Ä. `in_progress`.
49. **AI Data Quality Assessment** · `frk_tt_69ea9174fe7e40c0405cd057` · kvartalsvis. Kräver mått, gränser och resultat. Finns: webbfacit 85 %, existensgrinden. A. `todo`.
50. **AI Data Provenance Record** · `frk_tt_69ea9175640d0bbbddde05a7` · årligen. Kräver ursprung och kedja per datamängd. Finns: leads fullt, KB-källa (migration 117). A. `in_progress`.
51. **AI Data Preparation Record** · `frk_tt_69ea91761c04c37d4f867908` · årligen. Kräver förberedelsesteg med verktyg och granskare. Finns: maskering (också före Jev i development, PR 45), inramning. Maskering före inbäddningar byggs, inte mergad. A. `todo` · ändr. 11-18.

## Information och användning (4)

52. **Intended Use Statement** · `frk_tt_69ea91773112b091b458de8d` · årligen. Kräver avsedd och förbjuden användning per system. Finns: P27 avsnitt 4 (förslag). Ä med jurist. `todo`.
53. **Responsible AI Use Procedure** · `frk_tt_69ea9178aaa6c6a7058c0fcf` · årligen. Kräver procedur med mänsklig tillsyn och eskalering. Finns: autonomiregler och INV-ESC-001. Saknas: Snajps egen användning av AI-kodverktyg. Ä. `todo`.
54. **Responsible AI Use Objectives** · `frk_tt_69ea91794c21fc8f347cdddd` · årligen. Kräver mål med mätresultat. Finns: inget nedskrivet. Ä. `todo`.
55. **Stakeholder Register / Interested Parties Log** · `frk_tt_68cc27431d1266e3c77d7c0f` · årligen. Kräver register över intressenter och deras krav. Finns: spritt (matris 4.2). A. `todo`.

## Leverantörer, kunder och personal (6)

56. **AI Supplier Register** · `frk_tt_69ea917b78c7fc9f3c659a90` · årligen. Kräver register med riskgrad och AI-klausuler. Finns: Lev. §1, 2, 7; Gemini-bedömningen (`../../gemini-bedomning.md`). TypeSafe får inte längre kundmejl. Saknas: AI-klausuler; TypeSafe röd och får leadsdata; Gemini 2.5 har passerat pensionsdatumet 2026-10-20. Ä. `in_progress` · ändr. 11-18.
57. **AI Third-Party Responsibility Matrix** · `frk_tt_69ea917abdbda1fa183386d2` · årligen. Kräver RACI över livscykeln. Finns: kundens ansvar i villkoren. A skriver, Ä godkänner. `todo`.
58. **Contact Information** · `frk_tt_68406a514e90bb6e32e0b107` · årligen. Kräver kontaktsida och logg över klagomål. Finns: `kontakt@snajp.se`; `SECURITY.md` och `security.txt` i development (PR 50). Saknas: loggen; säkerhetskontakten i drift (PR 60). Ä. `in_progress` · ändr. 11-18.
59. **AI Awareness Program** · `frk_tt_69ea91684c77e2310a928a7a` · årligen. Kräver genomgång med material och kvittens. Finns: material och kvittens som utkast (`../../underlag/utbildning/`). Saknas: hållen genomgång. Ä, S. `in_progress` · ändr. 11-18.
60. **AI Competence Record** · `frk_tt_69ea916984bd6ff9ec7fd09b` · årligen. Kräver matris roll mot kompetens. Finns: inget. Ä, S. `todo`.
61. **Employee Descriptions** · `frk_tt_684069a3a0dd8322b2ac3f03` · årligen. Kräver rollbeskrivning och årligt samtal per anställd. Snajp har inga anställda; förslag: rollbeskrivningar för Anton och Sebbe i P27 avsnitt 5, samtalet `not_relevant` tills någon anställs. Ä beslutar. `in_review`.

---

**Summering 2026-11-18:** 0 `done`, 24 `in_progress`, 1 `in_review`, 36 `todo` (2026-11-17: 0, 14, 1, 46). Tre ligger nära: AI Verification & Validation Report, AI System Event Logging Configuration, Contact Information. AIMS Scope Statement stängs med en signatur på beslut e.
