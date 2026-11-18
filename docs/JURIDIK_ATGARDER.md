# Juridik — vad som är gjort och vad som är kvar

Statusen här är sanningen. Planer och beslut beskriver avsikten; den här
filen säger vad som faktiskt gäller.

Uppdaterad 2026-11-17, efter en nulägesinventering och en granskning av 15
leverantörers villkor ur officiella källor samma dag. Texten från 2026-08-24
finns i git-historiken.

Allvar: **B** blockerar första kund, **F** bör vara gjort före första kund,
**V** kan vänta. Vem: **Ä** ägaren (Anton), **A** agent (kod eller dokument).

---

## Klart och verifierat

| Punkt | Belägg |
|---|---|
| DeepSeek får inte köras där data är riktig. Uppstarten fälls | `Settings.llm_provider_fault()`, `app/main.py`, `lib/llm/modellval.ts`; prövat skarpt 2026-08-24 |
| Gemini på gratisnivå i chatten är borta. Chatten går via Vertex AI på ett betalt Google Cloud-projekt | `HANDOFF-2026-09-12-VERTEX-AI.md`; `snajp-support/app/agent/llm.py`; BESLUT 2026-10-21 |
| Googles och Railways regioner är belagda: Vertex behandlar inom EU, Railway kör alla tjänster och volymer i Amsterdam | Leverantörsgranskning och Railways regionlista 2026-11-17 |
| Underbiträdesförteckningen stämmer med driften på tre spårade ställen | `lib/bolag.ts`, `docs/pilotavtal.md` Bilaga 1, `docs/registerforteckning.md` (2026-11-17). Utkastet `docs/pub-avtal.md` Bilaga 3 är ifyllt men inte committat |
| De juridiska sidorna finns på svenska och engelska, och platshållare renderas aldrig | `app/integritetspolicy/`, `app/villkor/`, `app/cookies/`; INV-COPY-001; `lib/bolag.ts:utanPlatshallare` |
| Publik kontaktadress på egen domän (kontakt@snajp.se) | `components/marketing/copy.ts` |
| Art. 14-foten byggs i kod, och avregistreringen fungerar hela vägen | `snajp-support/app/leads/utskicksfot.py`; migration 049; klickad skarpt 2026-08-24 |
| Testmiljön indexeras inte | `app/robots.ts`, `lib/miljo.ts` |
| Personnummer maskeras innan text går till språkmodellen | `snajp-support/app/moderation/maskering.py`. Samma maskering före Jev är byggd 2026-11-17 men inte committad |
| Villkoren lägger ansvaret för autonominivån på kunden och beskriver utskicksspärren som den är | `app/villkor/VillkorSida.tsx` (spärrtexten rättad 2026-11-17, inte committad) |
| Textmall till kunden för art. 13-information | `docs/kundmall_informationstext.md` |
| Avtalsgrind: en kund med krav på avtal får ingen trafik utan registrerat avtalsdatum | `snajp-support/app/avtalsgrind.py`; migration 070. Av som standard, se B3 |
| Testmiljön skickar inga utskick | Spegelläget, BESLUT 2026-11-16 |
| Synken går bara från produktion till testmiljö | BESLUT 2026-10-17 |
| Hemlighetsskanning och push-skydd är påslagna i GitHub. Inga larm vid första kontrollen | Påslaget 2026-11-17. Skanningen känner igen leverantörers nyckelformat, inte vanliga lösenord (se akut punkt 1) |
| Kundmejl går inte längre till TypeSafe (Jev). Inkorgen sorteras bara av kodreglerna | BESLUT 2026-11-17; `INKORG_JEV` av i båda miljöerna sedan 2026-11-17, nya deployer uppe och hälsokontrollerna ok. Kvar: begära radering av det som redan skickats; Jev används fortfarande i leadsdelen |
| Jobbkön (Redis) går inte längre över publikt nät. Den ligger på Railways egen Redis, nådd över det privata nätverket, med var sin databas för produktion och testmiljö | BESLUT 2026-11-17; flyttad samma kväll, uppstartsloggen i båda miljöerna visar jobbkö, svarscache, chattström och leadsström mot Redis, hälsokontrollen ok. Kvar: akut punkt 4 |

---

## Kvar som kräver ägaren

### Akut

| # | Punkt | Belägg | Nästa handgrepp | Vem |
|---|---|---|---|---|
| 1 | Plattformsadminens lösenord ska bytas, liksom andra lösenord som kan ha exponerats. Hemlighetsskanningen hittar inte vanliga lösenord i historiken | BESLUT ("ska bytas") | Byt lösenorden | Ä |
| 4 | Den gamla Redis Cloud-databasen finns kvar med cache och arbetsminne, och reservvariabeln med den gamla adressen ligger kvar på api-tjänsten | Flytten 2026-11-17 (Klart ovan) | Radera databasen och säg upp kontot (ditt beslut); ta bort reservvariabeln när flytten gått några dagar | Ä, sedan A |
| 4b | Produktionsdatabasen har ingen säkerhetskopia. Gick inte att slå på 2026-11-17: Railway kräver Pro-planen för säkerhetskopior av volymer, och kontot ligger på en lägre plan | Försök 2026-11-17 | Välj väg: (a) Railway Pro med dagliga, veckovisa och månatliga kopior, eller (b) ett eget schemalagt jobb som dumpar databasen till en lagringsplats i EU. Valet är ditt | Ä, sedan A |

### Blockerar första kund

| # | Punkt | Belägg | Nästa handgrepp | Vem |
|---|---|---|---|---|
| 5 | Bolagsform och bolagsuppgifter saknas. En enskild firmas org.nr är ditt personnummer | `lib/bolag.ts` | Besluta enskild firma eller AB; fyll i org.nr, postadress och integritet@ | Ä, sedan A |
| 6 | Railways DPA gäller inte förrän den är signerad. Backupernas plats är ej belagd | Leverantörsgranskning 2026-11-17 | Signera via DocuSign-länken i Railways compliance-dokumentation; begär besked om backupplats | Ä |
| 7 | Inget juristgranskat avtal. PUB-avtalet är ett utkast, `/villkor` saknar pris, ansvarsbegränsning och uppsägning, och DPIA och intresseavvägning är ogranskade. Sidorna ser färdiga ut | `docs/pub-avtal.md` (frågorna överst), `app/villkor/VillkorSida.tsx` | Boka jurist | Ä |
| 8 | Integritetspolicyn lovar 24 månaders automatisk gallring. Inget gallringsjobb körs, och mekanismen täcker bara supportmejl | `app/integritetspolicy/IntegritetspolicySida.tsx`; `scripts/gallra.py`; migration 048 | Bekräfta 24 månader; agenten bygger jobbet och utökar det till leads och agentloggar | Ä, sedan A |
| 9 | Avtalsgrinden är av som standard, så en ny kund får trafik utan signerat avtal | Migration 070. Grinden som standard för manuellt upplagda kunder (INV-AVTAL-001) är byggd 2026-11-17, inte committad | Granska och godkänn ändringen | Ä, sedan A |
| 10 | Leverantörernas avtal är inte på plats fullt ut: ScrapeGraphAI saknar DPA, Resend lagrar mejlinnehåll i USA | Leverantörsgranskning 2026-11-17 | ScrapeGraphAI: betald plan och begärd DPA. Resend: godkänn USA-lagringen, ladda ned signerad DPA, gör TIA. Redis Cloud: används inte sedan flytten 2026-11-17; försvinner ur kedjan när databasen är raderad (akut punkt 4) | Ä |
| 11 | Synken via GitHub Actions bär produktionens persondata. Kontot har Free-planen och omfattas inte av GitHubs DPA, och körmaskinernas region anges inte | Leverantörsgranskning 2026-11-17 | Besluta flytt till en schemalagd tjänst hos Railway i Amsterdam | Ä, sedan A |

### Före första kund

| # | Punkt | Belägg | Nästa handgrepp | Vem |
|---|---|---|---|---|
| 12 | Ingen kodstyrd AI-upplysning i drift i chatten och i automatiska mejlsvar (AI-förordningen art. 50) | `snajp-support/app/agent/support_systemprompt.py`. AI-upplysningen (INV-AI-001) är byggd 2026-11-17, inte committad | Granska och godkänn ändringen | Ä, sedan A |
| 13 | Reservvägen till Google AI Studio finns kvar i drift och får inte användas för kunddata | `snajp-support/app/agent/llm.py`. Spärren (INV-DATA-004) är byggd 2026-11-17, inte committad; servicekontot i båda miljöerna klarar den. BESLUT 2026-11-17 | Granska och godkänn ändringen | Ä, sedan A |
| 14 | Samma Vertex-servicekonto i alla miljöer | `HANDOFF-2026-09-12-VERTEX-AI.md` | Skapa ett servicekonto per miljö | Ä |
| 15 | Gamla stacken: Render-tjänsterna lever, Render-nyckeln är inte roterad, det gamla Supabase-projektet bär historiska uppgifter, två incidentposter från 2026-08-24 är obedömda | `INCIDENT_RESPONSE.md` | Stäng Render och rotera nyckeln; radera Supabase-projektet och begär raderingsbekräftelse; bedöm posterna | Ä |
| 16 | Testmiljön är en fullständig kopia av produktionens persondata, och dess skydd motsvarar inte produktionens fullt ut | `CLAUDE.md` (spegeln); BESLUT | Besluta minimering eller pseudonymisering | Ä, sedan A |
| 17 | Kallmejl: org.nr saknas i foten (e-handelslagen), förnamnsadresser räknas som funktionsadresser, och demolänkens spårning per mottagare nämns inte i policyn | `snajp-support/app/leads/send_guard.py`; `app/cookies/CookiesSida.tsx`. Förnamnsadresserna: byggd 2026-11-17, inte committad. Allt som inte är en känd funktionsadress räknas som personligt och får art. 14-foten (`leads/sources/base.py`, `tests/leads/test_personlig_adress.py`). En kund utan `policy_url` får då utskick till namnadresser stoppade tills den är ifylld | Besluta de tre punkterna | Ä, sedan A |
| 18 | Raderingsverktyget täcker inte tabeller tillkomna efter augusti och har aldrig provkörts | `scripts/gdpr_radera.py` | Utöka och torrkör mot den lokala stacken | A |
| 19 | Ingen dokumenterad backup- och återställningsrutin | Inget belägg | Välj väg enligt akut punkt 4b; agenten dokumenterar och provar | Ä, sedan A |
| 20 | Senare säkerhetshändelser saknas i incidentloggen | `INCIDENT_RESPONSE.md` (uppdaterad 2026-11-17, inte committad) | Bedöm posterna | Ä |
| 21 | Ingen hemlighetsskanning i CI, och Actions-hemligheterna är bredare än de behöver | `.github/workflows/verify.yml` | Lägg till skanning; smalna av hemligheterna | A, Ä roterar |

### Kan vänta

| # | Punkt | Nästa handgrepp | Vem |
|---|---|---|---|
| 22 | Kanaler och CRM som kunden slår på saknas i PUB-avtalet (blir B när en kund aktiverar en kanal) | Text i avtalet | A, sedan jurist |
| 23 | Radnivåsäkerheten är bara verifierad mot den gamla databasen | Kör testet mot den lokala stacken | A |
| 24 | Klausulen om Snajps egen användning av bolagsdata är preliminär | Juristfråga | Ä |
| 25 | Allabolag och hitta hämtas utan avtal | API-förfrågan | Ä |
| 26 | Död kod med DeepSeek som standard i `lib/agent/llm.ts` | Ta bort | A |
| 27 | NextAuth och Supabase Auth parallellt | Städa till en väg | A |
| 28 | AI-kodverktyg läser testmiljöns kunddata | Besluta policy | Ä |
| 29 | Widgetens supportadress och interna larm går via Gmail | Byt till egen domän när integritet@ finns | Ä, sedan A |
| 30 | Vägval för Comp AI | Välj väg | Ä |

---

## Löpande

- Underbiträdena står på fyra ställen: `lib/bolag.ts`, `docs/pub-avtal.md`
  Bilaga 3, `docs/pilotavtal.md` Bilaga 1 och `docs/registerforteckning.md`.
  En ny leverantör läggs in på alla fyra i samma ändring.
- Leverantörerna meddelar nya underbiträden i förväg: Google 30 dagar, Resend
  14, TypeSafe 15, Redis 5. Läs aviseringarna och uppdatera listorna.
- Varje nytt beslut skrivs i `docs/BESLUT.md`, varje säkerhetshändelse i
  `INCIDENT_RESPONSE.md`.

---

## Inte gjort, och varför

- **`gdpr_radera.py` körd skarpt.** Skriptet raderar data, och det finns
  ingen begäran att uppfylla. Sökläget kan köras när som helst.
- **Repots synlighet.** Den påverkar grenskyddet och Actions-minuterna och
  är ditt beslut.
- **Inga andra ändringar i driftmiljöerna** i compliance-arbetet 2026-11-17
  än de du sa ja till samma kväll: inkorgsklassningen via Jev avstängd i båda
  miljöerna, hemlighetsskanningen påslagen och jobbkön flyttad till
  Railways egen Redis (ny Redis-tjänst i produktionen, jobbköns adress bytt
  i båda miljöerna). Säkerhetskopior gick inte att slå på (akut punkt 4b).
- **Ingen Comp AI-installation.** Den väntar på vägvalet (punkt 30).
