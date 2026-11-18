# Uppgifter i ISO 27001-ramverket

De 24 uppgiftsmallarna som ramverket `frk_681ecc34e85064efdbb76993` (commit `712ee1b3`) kopplar till sina kontroller. Namn, id, frekvens och avdelning är mallens. "Kräver" sammanfattar mallens text; avsnitt för HIPAA, PCI och ISO 42001 är utelämnade, avsnitt för ISO 27001 är med.

Fem uppgifter delas med GDPR-ramverket (App Availability, Encryption at Rest, Incident Response, Monitoring & Alerting, Public Policies). De har samma id; GDPR-versionen i `../gdpr/uppgifter.md` gäller, med de tillägg som står här.

Status med plattformens värden (`todo`, `in_progress`, `in_review`, `done`, `not_relevant`). Vem: **Ä** = Anton, **A** = agent. Hänvisningar som i `matris.md`, med tilläggen 2026-11-18 (bevis/konf-efter, PR n, Underlag, GitHub-API).

Uppdaterad 2026-11-18. "Ändr. 11-18" vid status betyder att uppgiften ändrats den dagen.

**Summering:** 0 `done`, 13 `in_progress`, 1 `in_review`, 10 `todo`. Förändring från 2026-11-17: `todo` 18 → 10, `in_progress` 5 → 13, `in_review` 1 → 1, `done` 0 → 0.

## Kan stängas i dag

**Ingen uppgift kan stängas som `done` med befintligt bevis.** De som ligger närmast:

- **Legal Proof of Company Registration:** stängs när Anton laddar upp ett registreringsbevis från Bolagsverket med adress. Ett handgrepp, men det röjer personnumret som org.nr så länge Snajp är enskild firma (BU B1).
- **2FA:** stängs med skärmbilder från varje konto, om tvåfaktor redan är påslagen. Läget är okänt; rutinen `../../underlag/rutiner/d-atkomstgenomgang.md` samlar dem.
- **Secure Devices** och **Device List:** stängs med skärmbilder och den ifyllda listan `../../underlag/rutiner/e-enheter.md`, om datorerna redan uppfyller kraven. Okänt.
- **Monitoring & Alerting:** se `../gdpr/uppgifter.md` nr 11. Ärende 53 är ett verkligt larm från övervakningen, men schemat går glest och internlarmen är fortfarande tysta.

**Rättelse mot GDPR-filen 2026-11-17 (gäller fortfarande):** internlarmets variabler saknas i api i båda miljöerna (bevis/konf-efter), så `[PRIORITERAT]`-mejlen skickas troligen inte. Det nya beviset för Monitoring & Alerting är driftövervakningen, inte internlarmet.

---

### 1. 2FA
`frk_tt_68406cd9dde2d8cd4c463fe0` · årligen · `itsm` · AUTOMATED · kontroll: Credential Management

- **Kräver:** tvåfaktor påslagen överallt där det går; skärmbild av inställningen på organisationsnivå och av en användare som får tvåfaktorfrågan.
- **Finns:** tvåstegsverifiering på `snajpsupport@gmail.com` enligt `DEPLOY.md:347-350`. Mall för kontrollen i åtkomstgenomgången (Underlag `rutiner/d-…`).
- **Saknas:** kontroll och skärmbilder för GitHub, Railway, Google Cloud, Resend, Loopia för båda. Ingen tvåfaktor i appen (P12).
- **Vem:** Ä och Sebbe tar skärmbilderna.
- **Agent utan Ä:** nej.
- **Status:** `todo`. Kan stängas i dag om tvåfaktor redan är på.

### 2. Access Review Log
`frk_tt_68e805457c2dcc784e72e3cc` · kvartalsvis · `it` · MANUAL · kontroll: Access Rights

- **Kräver:** kvartalsvis genomgång av åtkomst med datum, granskare, användare och roller, åtgärder och ledningens underskrift.
- **Finns:** rutin och mall som utkast (Underlag `rutiner/d-atkomstgenomgang.md`), nästan allt [FYLL].
- **Saknas:** ifylld förteckning över konton och första granskningen med underskrift.
- **Vem:** Ä och Sebbe.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 3. App Availability (delad med GDPR)
`frk_tt_68406d2e86acc048d1774ea6` · årligen · `it` · AUTOMATED · kontroller: Disaster Recovery Planning, Resource Capacity Management

- **Kräver:** skärmbild på DDoS-skydd eller automatisk skalning; brandvägg runt produktionsdatabasen.
- **Finns:** som i `../gdpr/uppgifter.md` nr 1.
- **Tillägg:** Postgres i `main` har fortfarande en publik TCP-proxy (bevis/konf-efter rad 229-231). Brandväggsbelägget kan inte ges förrän den är stängd.
- **Vem:** Ä.
- **Agent utan Ä:** nej.
- **Status:** `todo` · ändr. 11-18 (bevis).

### 4. Backup Restoration Test
`frk_tt_68e52b269db179c434734766` · årligen · `it` · MANUAL · kontroll: Security Incident Management

- **Kräver:** ett nyligen gjort återställningsprov med kontroll av data, som inspelning eller rapport.
- **Finns:** inget. Inga kopior finns att återställa (bevis/backup). Beslutsutkast om mål och prov (Underlag `beslut/g-sakerhetskopiering-aterstallning.md`).
- **Saknas:** kopior och provet (P18). Railway kräver Pro-planen för kopior (BU A4).
- **Vem:** Ä uppgraderar och slår på kopiorna; A provar på Ä:s ja.
- **Agent utan Ä:** nej.
- **Status:** `todo` · ändr. 11-18 (blockerad av Pro-planen).

### 5. Code Changes
`frk_tt_68406d64f09f13271c14dd01` · årligen · `gov` · AUTOMATED · kontroll: Change management

- **Kräver:** grenskydd som stoppar direkta push och kräver PR; regressionstester. För ISO 27001: godkännande med granskning, testbelägg, plan för att backa och konsekvensbedömning.
- **Finns:** grenskydd med code owner på `main` (Inv. §4; PR #43, #44); CI med tester (`verify.yml`); kodskanning med CodeQL på PR. Release-PR 60 har en beskrivning med påverkan per ändring och vad som ska kontrolleras efter mergen.
- **Saknas:** skärmbild av grenskyddet; `development` är oskyddad och bär produktionsdata; Railway väntar inte på CI; ingen backningsplan i PR:erna (P19).
- **Vem:** Ä tar skärmbilden; A lägger mall för PR-beskrivning.
- **Agent utan Ä:** mallen ja.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 6. Data Masking
`frk_tt_686b51339d7e9f8ef2081a70` · årligen · `it` · MANUAL · kontroll: Data Masking

- **Kräver:** känsliga fält döljs.
- **Finns:** personnummer maskeras före Vertex (`snajp-support/app/moderation/maskering.py`) och, i testmiljön, före TypeSafe (PR 45); adresser och telefon bort före Jev; webbplatsbedömningen grindad.
- **Saknas:** maskering av hälsouppgifter (DPIA R1); maskering före inbäddningar (byggs, inte mergad); testmiljön omaskerad (JA #16).
- **Vem:** A.
- **Agent utan Ä:** beviset ja; minimeringen av testmiljön kräver Ä:s beslut.
- **Status:** `in_progress` · ändr. 11-18 (bevis). Maskeringskoden och dess tester kan laddas upp nu.

### 7. Device List
`frk_tt_68406903839203801ac8041a` · årligen · `admin` · AUTOMATED · kontroll: Asset Inventory

- **Kräver:** lista över datorer (och servrar). Kan ersättas av Comp AI:s enhetsagent.
- **Finns:** mall som utkast (Underlag `rutiner/e-enheter.md`), inte ifylld.
- **Saknas:** den ifyllda listan. Enhetsagenten används inte, eftersom plattformen inte är driftsatt.
- **Vem:** Ä och Sebbe.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 8. Employee Access
`frk_tt_68406ca292d9fffb264991b9` · årligen · `it` · AUTOMATED · kontroll: Access Rights

- **Kräver:** identitetsleverantör (t.ex. Google Workspace), skärmbild av användarlistan och årlig granskning. För ISO 27001: avslutslista och belägg för indragen åtkomst för en person som slutat; lista över privilegierade användare.
- **Finns:** kontoförteckningen som mall i åtkomstgenomgången (Underlag `rutiner/d-…`). Ingen central identitetsleverantör.
- **Saknas:** ifylld förteckning. Ingen har slutat, så avslutsbelägget kan inte ges; avslutsrutinen finns som utkast (P15).
- **Vem:** Ä.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 9. Employee Performance Evaluations
`frk_tt_68e52b27c4bdbf1b24051b8b` · årligen · `hr` · MANUAL · kontroll: Human Resources Security

- **Kräver:** minst fem anonymiserade medarbetarbedömningar.
- **Finns:** inget.
- **Bedömning:** med en ägare och en medutvecklare går det inte att visa fem bedömningar, och anonymisering är meningslös. Förslag: `not_relevant` med motiveringen att Snajp inte har anställda; kompetensen täcks av utbildningskvittenserna (G05, krav 7.2). Gäller tills någon anställs.
- **Vem:** Ä beslutar.
- **Agent utan Ä:** nej.
- **Status:** `in_review` → `not_relevant` när Anton beslutat.

### 10. Employee Verification
`frk_tt_68406951bd282273ebe286cc` · årligen · `hr` · AUTOMATED · kontroll: Human Resources Security

- **Kräver:** referenskontroll och identitetskontroll för varje nyanställd. För ISO 27001: sekretessavtal, bedömning av kandidaten och godkänd beställning av åtkomst.
- **Finns:** inget.
- **Saknas:** sekretessavtal med Sebbe (okänt om det finns); undantaget för befintliga två (P15).
- **Vem:** Ä.
- **Agent utan Ä:** nej.
- **Status:** `todo`.

### 11. Encryption at Rest (delad med GDPR)
`frk_tt_68e52b26bf0e656af9e4e9c3` · årligen · `it` · AUTOMATED · elva kontroller

- **Kräver:** skärmbilder på kryptering i vila för databaser, lagring och volymer.
- **Finns:** som i `../gdpr/uppgifter.md` nr 7.
- **Tillägg:** ISO-ramverket kopplar uppgiften till elva kontroller, bland dem Endpoint Protection. Diskkryptering på datorerna hör hit (P13).
- **Vem:** Ä.
- **Agent utan Ä:** nej.
- **Status:** `todo`.

### 12. Incident Response (delad med GDPR)
`frk_tt_68406b4f40c87c12ae0479ce` · årligen · `itsm` · MANUAL · kontroll: Security Incident Management

- **Kräver:** register över säkerhetsincidenter och hur de lösts.
- **Finns:** som i `../gdpr/uppgifter.md` nr 8.
- **Tillägg:** registret ska omfatta alla säkerhetshändelser, inte bara personuppgiftsincidenter (A.5.24). Driftlarmen blir ärenden i GitHub; de bör föras in i registret. Loggen ligger i det publika repot (P08).
- **Vem:** Ä bedömer; A uppdaterar.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (bevis).

### 13. Internal Security Audit
`frk_tt_68e52b2618cb9d9722c6edfd` · årligen · `itsm` · MANUAL · kontroll: Internal Audit & Management Review

- **Kräver:** plan och omfång, revisorns oberoende, checklistor, rapport med fynd och åtgärder.
- **Finns:** `matris.md` och `../gdpr/matris.md` är en genomgång (2026-11-17, uppdaterad 2026-11-18), men gjord av en agent på ägarens uppdrag, inte en revision.
- **Saknas:** plan, oberoende granskare, rapport (P10).
- **Vem:** Ä; extern granskare [FYLL].
- **Agent utan Ä:** underlaget ja, revisionen nej.
- **Status:** `todo`.

### 14. Legal Proof of Company Registration
`frk_tt_68d28f68f117d45c0adcba33` · årligen · `admin` · MANUAL · kontroll: Legal, Regulatory & IP Compliance

- **Kräver:** officiellt registreringsbevis med adress.
- **Finns:** inget i underlaget. Org.nr och adress är platshållare (`lib/bolag.ts:39-40`).
- **Saknas:** beviset; beslut om enskild firma eller AB (BU B1).
- **Vem:** Ä.
- **Agent utan Ä:** nej.
- **Status:** `todo`. Kan stängas i dag med ett utdrag från Bolagsverket.

### 15. Monitoring & Alerting (delad med GDPR)
`frk_tt_68406af04a4acb93083413b9` · årligen · `itsm` · AUTOMATED · kontroll: Security Monitoring & Detection

- **Kräver:** loggning i molnmiljöerna, regelbunden granskning, skärmbild av ett nyligen mottaget larm.
- **Finns:** som i `../gdpr/uppgifter.md` nr 11: driftövervakning med provad larmkedja (ärende 53).
- **Saknas:** tätt schema (en schemalagd körning under natten mot 18/11), internlarmets variabler, felspårning, beskrivning av Railways loggtid (P25).
- **Vem:** Ä sätter variablerna; A följer upp schemat.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 16. Planning
`frk_tt_68406e7abae2a9b16c2cc197` · årligen · `gov` · AUTOMATED · kontroll: Disaster Recovery Planning

- **Kräver:** återställning till tidpunkt eller säkerhetskopior påslagna, provade årligen, och en steg-för-steg-beskrivning av provet.
- **Finns:** inget i drift (bevis/backup). Beslutsutkast (Underlag `beslut/g-…`).
- **Saknas:** allt i drift (P18). Railway kräver Pro-planen.
- **Vem:** Ä; A provar.
- **Agent utan Ä:** nej.
- **Status:** `todo` · ändr. 11-18 (blockerad av Pro-planen).

### 17. Production Firewall & No-Public-Access Controls
`frk_tt_68fa2a852e70f757188f0c39` · årligen · `itsm` · AUTOMATED · kontroller: Access Rights, Network Security

- **Kräver:** neka allt som inte är tillåtet; databaser nås inte från internet, bara från appservrarna; inga öppna adminportar.
- **Finns:** appen når databasen och, sedan 2026-11-17, jobbkön via Railways privata nät (bevis/konf-efter). Inga egna servrar med SSH eller RDP. Plan för att flytta synken (`../../synkflytt-plan.md`).
- **Saknas:** Postgres har fortfarande en publik TCP-proxy i `main` och `development` (bevis/konf-efter rad 229-231, 75-77), och synken från GitHub ansluter genom den. Kravet är inte uppfyllt.
- **Vem:** Ä beslutar flytten av synken (JA #11); A bygger.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 18. Public Policies (delad med GDPR)
`frk_tt_6840791cac0a7b780dbaf932` · årligen · `it` · AUTOMATED · kontroll: Data Privacy

- **Kräver och finns:** som i `../gdpr/uppgifter.md` nr 12. Inga tillägg för ISO 27001.
- **Status:** `in_progress` · ändr. 11-18 (bevis, se GDPR-filen).

### 19. Sanitized Inputs
`frk_tt_68406eedf0f0ddd220ea19c2` · årligen · `it` · AUTOMATED · kontroller: Change management, Secure SDLC Integration

- **Kräver:** validering av indata med Zod, Pydantic eller liknande.
- **Finns:** FastAPI med Pydantic (`snajp-support/requirements.txt`). Demons sessionscookie godtar bara ett UUID (PR 49, testmiljön).
- **Saknas:** genomgång av Next-appens server actions och API-rutter; Zod används inte. Om alla endpoints validerar är inte kontrollerat.
- **Vem:** A.
- **Agent utan Ä:** ja.
- **Status:** `in_progress`.

### 20. Secure Devices
`frk_tt_6840796f77d8a0dff53f947a` · årligen · `itsm` · AUTOMATED · kontroll: Endpoint Protection

- **Kräver:** diskkryptering, skärmlås inom 15 minuter, lösenord minst 8 tecken, automatiska säkerhetsuppdateringar, antivirus. Skärmbilder per enhet.
- **Finns:** mall per dator som utkast (Underlag `rutiner/e-enheter.md`).
- **Saknas:** skärmbilder från varje dator (P13 kräver 10 minuter).
- **Vem:** Ä och Sebbe.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 21. Secure Secrets
`frk_tt_68407ae5274a64092c305104` · årligen · `itsm` · AUTOMATED · kontroller: Credential Management, Encryption Key Management

- **Kräver:** molnleverantörens hemlighetshantering; inga hemligheter i git eller kod; skärmbild av hanteringen.
- **Finns:** nycklar som Railway-variabler (bevis/konf, bara namn); `.env*` gitignorerat; `scripts/keys.py`. Hemlighetsskanning med push-skydd påslagen, 0 öppna larm 2026-11-18 (GitHub-API). `scripts/lokal_stack.py` skriver inte längre ut adminlösenordet (PR 49).
- **Saknas:** lösenordet i den publika historiken är inte bytt (BU A1, bevis/historik); skanningen känner inte igen vanliga lösenord; hela `.env.deploy` som en GitHub-hemlighet.
- **Vem:** Ä byter lösenord; A smalnar av hemligheterna.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 22. Separation of Environments
`frk_tt_68e52a484cad0014de7a628f` · årligen · `it` · AUTOMATED · arton kontroller

- **Kräver:** belägg för att utveckling, test och produktion är åtskilda, med begränsad åtkomst mellan dem.
- **Finns:** två Railway-miljöer med egna databaser och, sedan 2026-11-17, egen Redis per miljö (bevis/region-efter, bevis/konf-efter); lokal stack (`scripts/lokal_stack.py`).
- **Saknas:** testmiljön är en spegel av produktionsdata; miljöerna delar Vertex-servicekonto; synken förbinder dem (JA #14, #16).
- **Vem:** Ä beslutar; A bygger.
- **Agent utan Ä:** nej.
- **Status:** `in_progress` · ändr. 11-18 (var `todo`).

### 23. TLS / HTTPS
`frk_tt_68406f411fe27e47a0d6d5f3` · årligen · `itsm` · AUTOMATED · kontroll: Secure Data Transfer

- **Kräver:** TLS påslaget; skärmbild från SSL Labs.
- **Finns:** publika adresser på HTTPS (bevis/konf rad 161, 176). Redis går inte längre över internet.
- **Saknas:** SSL Labs-mätningen. Ingen HSTS.
- **Vem:** A kan köra mätningen mot de publika adresserna.
- **Agent utan Ä:** ja (en extern mätning av publika adresser; körs först på Antons ja, eftersom den riktas mot driften).
- **Status:** `todo` · ändr. 11-18 (bevis).

### 24. Utility Monitoring
`frk_tt_6849c1a1038c3f18cfff47bf` · årligen · `it` · AUTOMATED · kontroll: Utility Tool monitoring

- **Kräver:** lista över godkända privilegierade verktyg; belägg för tidssynk inom en sekund på en Linux-maskin och en Windows- eller Mac-dator.
- **Finns:** inget.
- **Saknas:** verktygslistan (P21, P25); tidssynk på datorerna. Snajp har ingen egen Linux-maskin; Railway sköter värdarna.
- **Vem:** Ä (datorerna); A (listan).
- **Agent utan Ä:** listan ja.
- **Status:** `todo`.
