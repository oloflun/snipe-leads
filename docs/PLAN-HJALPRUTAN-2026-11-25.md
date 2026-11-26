# Plan: Hjälprutan, felrapporter och testversion per kund

Skriven 2026-11-25 efter Antons beställning samma dag. Underlaget är sex
kartläggningar av det som redan finns och tre oberoende arkitekturförslag
(säkerhet först, minsta helhet först, kundens upplevelse först). Den här planen
är sammanvägningen. Varje val som är Antons står under "Kräver Anton", med det
förval bygget utgår från tills han säger annat.

## Beställningen

> Vår inbyggda supportagent ska finnas som en chattruta där kunderna kan ge
> kontext till kunskapsbasen och be om hjälp, men även direkt feedback på fel,
> vilket skapas som supporttickets och skickas vidare till vår agent och som
> bygger en spegel med fixen enbart för deras inlogg för att testa innan det
> pushas vidare.

Samma dag: gamla exempelartiklar ska tas bort automatiskt när kunskapsbasen
fylls på.

## Vad kunden får

En ingång, tre ärenden, ett förlopp.

- **Ingången** är knappen Meny i sidomenyns fot och i mobilraden. Där står i dag
  "Anmäl felaktigt svar", som bara öppnar ett mejl. Den raden blir "Hjälp och
  fel" och öppnar Hjälprutan: ett ark förankrat i sidomenyn på desktop, full
  höjd på mobil. Ingen flytande bubbla och ingen ny panel ovanpå sidorna.
- **Fråga om Snajp.** Snajps egen supportagent svarar ur Snajps kunskapsbas om
  produkten.
- **Lär agenten om oss.** Kunden skriver eller klistrar in text om sitt företag.
  Rutan visar exakt den rubrik och text som sparas, kunden kan ändra, och ett
  klick lägger artikeln i kundens egen kunskapsbas.
- **Något är fel.** Ett kort i samtalet med tre fält: vad gjorde du, vad hände,
  vad väntade du dig, plus valfri bild. Under fälten står öppet vad som skickas
  med (sidan, tiden, rollen). Rapporten kvitteras direkt med ett ärendenummer.
- **Mina ärenden.** En flik i samma ruta visar varje felrapport och var den står.
  Det finns kvar efter omladdning och på andra enheter. Samma händelser når
  appens befintliga notiscenter, så det blir ingen andra klocka.

Kunden ser sex lägen och två sidolägen. De interna stegen (gren, ändringsbegäran,
bygge) syns bara för plattformsadmin.

| Kunden ser | Betyder |
|---|---|
| Mottaget | Rapporten är sparad hos Snajp |
| Vi undersöker | En människa hos Snajp har läst den |
| Rättning på gång | Rättningen tas fram |
| Redo att testa | Testversionen är byggd; knappen "Öppna testversionen" och frågan "Fungerade det?" |
| Godkänd, granskas av oss | Kunden svarade ja; Snajp granskar innan något går ut |
| Ute i Snajp | Rättningen ligger i produktionen; testversionen är borttagen |
| Behöver mer från dig | Snajp har en fråga; svarsfält i kortet |
| Stängd med förklaring | Inte ett fel, eller går inte att rätta; en människa har skrivit varför |

Svarar kunden nej på "Fungerade det?" går ärendet tillbaka till Rättning på
gång med kundens kommentar och samma ärendenummer.

## Det som redan finns och återanvänds

- `components/snajp/SupportChat.tsx` är chattkomponenten på fyra ställen
  (marknadssidan, kundens länk, widgeten, testchatten). Den har fasvisning,
  pollning, felhantering och ett kort för kunskapsbasartiklar.
- `components/snajp/AgentMenu.tsx` är redan hjälp- och felingången, monterad i
  `components/AppShell.tsx`.
- Backendens chattväg `POST /api/chat` (`snajp-support/app/api/chat.py`) svarar
  med ett jobb som klienten pollar. Ingen tokenströmning finns och ingen byggs.
- Snajp finns som kund hos sig själv (`lib/tenants/snajp.ts`,
  `snajp-support/app/tenants/snajp_kb.py`), men nås i dag bara anonymt från
  marknadssidan.
- Kunskapsbasens förslagslista (`components/settings/WebbplatsForslag.tsx`,
  tabellen `ss_kb_forslag`) och regeln att en människa lägger till varje artikel
  (INV-LEARN-001).
- Adminytans `components/admin/FelOchEskaleringar.tsx` och det prioriterade
  mejlet utan kundtext (`snajp-support/app/notifications/prioriterat_mejl.py`).
- Spegelns spärrar: en databas märkt `mirror_meta` med läget `envags` stoppar
  utskick, inkorg och autopilot med kod som redan finns.
- Skripten mot Railway (`scripts/railway.py`, `scripts/railway_provision.py`)
  och inkapslingen av opålitlig text
  (`snajp-support/app/leads/untrusted_content.py`).
- Kolumnen `ss_knowledge_base.is_placeholder` finns sedan juli men ingen kod
  läser eller skriver den.

## Arkitekturen

### 1. Hjälprutan (Next)

- `AgentMenu` öppnar `components/snajp/HjalpRuta.tsx` (ny, tunn behållare med
  flikarna Samtal och Mina ärenden). Samtalet är `SupportChat` i ett nytt läge,
  `hjalpMode`, som hämtar historiken från servern i stället för webbläsarens
  minne.
- Tomt läge: en rad om vad rutan gör och tre startval. Kunden kan också skriva
  fritt. Agenten får föreslå rätt kort ("Det låter som ett fel. Vill du anmäla
  det?"), men ärendet skapas alltid av kundens klick, aldrig av modellens
  klassning.
- All text är tvåspråkig via `lib/i18n.tsx`. En förhandsvisning utan databas
  läggs under `app/forhandsvisning/hjalpruta/` så att varje läge går att se i
  bild på desktop och mobil.

### 2. Vägen till Snajps egen agent

- Nya inloggade vägar under `app/api/snajp-support/hjalp/`: chatt, jobb, samtal,
  ärenden. Alla kräver session (`getWorkspaceContext`), så INV-SEC-010 håller.
- De använder **hjälpens egen nyckel**, aldrig kundens och aldrig
  `proxyAsTenant`. Hjälpen får en egen kund i systemet, `snajp-hjalp`, skild
  från `snajp` som marknadssidans anonyma demo använder. Skäl: en anstormning
  på marknadssidan ska inte stänga kundernas hjälp, och den anonyma vägen ska
  inte kunna nå kundernas samtal ens med rätt adress.
- Servern skriver om anropet: avsändaren blir `<användar-id>@kund.snajp.se`
  (den domänen avvisas redan av den anonyma vägen), namnet tas ur profilen,
  `arbetsyta` tas alltid bort (annars hamnar Snajps egna nyckeltal i svaret)
  och `is_test` är falskt. Från klienten tas bara texten och sidans sökväg.
- Backend: `POST /api/hjalp/samtal` läser tillbaka samtalet och godtar bara
  `@kund.snajp.se`.
- Snajps kunskapsbas fylls på med produkthjälp för den inloggade ytan. I dag
  finns en enda sådan artikel, och utan fler svarar agenten svagt.

### 3. Kontext till kundens kunskapsbas

- Allt skrivs i **kundens** kund i systemet, genom kundens egen väg
  (`proxyAsTenant` mot `/api/kb`), efter kundens klick. Snajps agent skriver
  aldrig över gränsen mellan kunder.
- Nytt: `POST /api/kb/forslag` med källan `chatt`, så att text ur samtalet kan
  bli ett förslag som syns både i rutan och i den befintliga förslagslistan,
  med en etikett som säger var det kom ifrån.
- Läsrollen ser kortet med knappen avstängd och en förklaring. En
  plattformsadmin som besöker kunden skriver testmärkt, som i dag.

### 4. Exempelartiklarna rensas av sig själva

- `is_placeholder` börjar användas. Bara seedningen
  (`snajp-support/app/scripts/seed_kb.py`) sätter den.
- Rensningen ligger i lagringslagret: varje väg som lägger in kundens eget
  innehåll (`add_kb_article`, `lagg_till_kb_forslag`) raderar kundens
  exempelrader i samma transaktion. Då gäller den alla vägar, även framtida.
- Eget innehåll är en artikel kunden lagt till eller ett förslag kunden godkänt.
  Att skanningen lämnat förslag räcker inte: då står basen annars tom tills
  kunden godkänt något.
- En additiv migration märker de exempelrader som redan finns i testarbetsytor.
  Snajps egen bas och den riktiga demokunden Nordlys märks aldrig.

### 5. Felrapporten som ärende

- Felrapporten går ett eget, strukturerat flöde och inte genom agentens
  eskalering. En eskalering tystar chatten i upp till 24 timmar, och kunden
  ska kunna fortsätta fråga medan felet rättas.
- Ny tabell `plattformsarenden` och händelseloggen `plattformsarende_handelser`.
  Rapportör, arbetsyta, kund, vy, roll och om det är en besökande admin sätts
  på servern ur sessionen. Klienten skickar bara sökvägen, de tre fälten och
  eventuell bild.
- Förloppet ligger i databasen, inte i jobbminnet (som lever en timme). Därför
  finns det kvar efter omladdning.
- Kunden ser bara sina egna rapporter. En annan användare i samma arbetsyta ser
  dem inte utan Antons beslut.
- Snajps sida: listan i `FelOchEskaleringar` med rapportör, arbetsyta, sida och
  hela kedjan, plus ett prioriterat mejl med länk och utan kundtext.

### 6. Den kodande agenten, bakom en människa

- Ingen automatisk vidarekoppling från kundens text till en agent som skriver
  kod. Anton eller Sebbe läser rapporten och trycker "Skicka till agenten".
- Först görs ett **arbetsunderlag**: sida, steg, förväntat, faktiskt och
  eventuellt händelse-id. Ett modellsteg utan verktyg (Vertex i EU, den modell
  som redan är godkänd för kunddata) förifyller det, kundens text kapslas som
  opålitlig, och en människa godkänner. Underlaget bär inga namn, adresser,
  kunddata eller bilder.
- Agenten är `scripts/felrapport_agent.py`. Den hämtar godkända underlag,
  arbetar i en egen arbetskopia från `origin/development` utan `.env.deploy`,
  utan Railway-nyckel och utan databas, verifierar mot `scripts/lokal_stack.py`
  och förhandsvisningar, och öppnar en ändringsbegäran mot `development` från
  grenen `fix/arende-<8 tecken>`.
- Agenten har en **egen GitHub-identitet** som bara får skriva innehåll och
  öppna ändringsbegäran. Den kan inte slå ihop, inte ändra arbetsflöden och
  inte nå hemligheter. `scripts/pr_granskning.py` fäller en sådan gren som rör
  `.github/`, `CODEOWNERS`, `db/migrations/`, `lib/auth*`, `proxy.ts` eller
  `scripts/railway*` utan Antons märkning.
- Repot är publikt. Gren, commit och ändringsbegäran bär därför bara
  ärendenumret och en teknisk sammanfattning, aldrig kundens ord.
- Körs för hand per ärende tills flödet är bevisat, sedan som fönsterlös
  schemalagd uppgift.

### 7. Testversionen ("spegeln") bara för kundens inlogg

- En egen miljö hos Railway, `forhand`, med fyra tjänster (webb, api, databas,
  Redis), skapad tom av `scripts/railway_forhandsmiljo.py`. Den klonas aldrig
  från en befintlig miljö: en klon ärver mejltjänster, flyttvägar och synkjobb.
  Variablerna skrivs ur en vitlista, med egna hemligheter.
- Databasen byggs från noll per ärende och fylls av ett utdrag som bara
  innehåller **den kundens** arbetsyta. Development kopieras aldrig: den bär
  alla kunders data.
- Databasen märks `envags`, så utskick, inkorg och autopilot är avstängda av
  kod som redan finns.
- Inloggningen är stängd för alla utom kundens arbetsyta och plattformsadmin
  (variabeln `SPEGEL_ARBETSYTOR`, kontrollerad vid inloggning och i
  `getWorkspaceContext`). Saknas värdet släpps ingen in. Kontoskapande och
  inloggning via Google är avstängda där.
- Kunden kommer in med en **signerad engångslänk** ur rutan. Inga lösenord
  lämnar produktionen.
- Testversionen öppnas i en ny flik, eftersom den ligger på en annan adress.
  Det är det enda stället där regeln om ingen ny flik viker. Svaret på
  "Fungerade det?" lämnas alltid i den vanliga appens ruta.
- Första steget är en miljö och en kö: ett ärende i taget. En miljö per ärende
  är nästa steg med samma skript, när kön blir en flaskhals.
- Efter kundens svar, eller senast efter sju dagar, töms miljön.

### 8. Vidare till development och main

- Kundens ja är information. Det ersätter aldrig granskningen.
- Anton eller Sebbe granskar och slår ihop ändringsbegäran till `development`.
- Till `main` går rättningen som alltid: release med Antons uttryckliga ord och
  hans handgrepp.

## Hotbilden och vad som begränsar skadan

| Hot | Spärr |
|---|---|
| Kundens text styr en agent med skrivrätt i repot | Texten passerar ett steg utan verktyg och en människa innan agenten ser något; agenten kan bara öppna en ändringsbegäran |
| En felaktig eller elak rättning körs mot kunddata | Testversionens databas innehåller bara den rapporterande kundens rader och kan inte skicka mejl |
| Testversionen läcker | Den exponerar bara den kundens data, och bara för den kundens inlogg |
| Kunddata hamnar på GitHub | Felrapporten lagras bara i Snajps databas; GitHub får ärendenummer och teknisk text |
| Snajps agent skriver i fel kunds kunskapsbas | Kunskapsbasen skrivs bara genom kundens egen väg efter kundens klick |
| Snajps egna tal visas för kunden | `arbetsyta` sätts aldrig på hjälpchatten; statiskt test vaktar det |
| En besökande admin ser ut att vara kunden | Rapportören är alltid den inloggades eget id; besöket lagras för sig |
| Hjälpen stängs av trafik på marknadssidan | Egen kund i systemet med egna tak |

## Faserna

Varje fas går att bygga, testa och visa för sig.

| Fas | Innehåll | Klart när | Kräver Anton |
|---|---|---|---|
| 0 | Exempelartiklarna rensas när eget innehåll läggs in | Tester visar att varje väg för eget innehåll tar bort exemplen i samma transaktion, att Snajps och Nordlys baser aldrig märks, och Kunskapsbas är sedd i bild | Nej |
| 1 | Hjälprutan med Fråga och Lär agenten | En inloggad testkund får svar ur Snajps kunskapsbas, ser samtalet efter omladdning och i en ny flik, och lägger till en artikel i sin egen bas från rutan; bilder på desktop och mobil | En nyckel för `snajp-hjalp` i Railway |
| 2 | Felrapport som ärende, Mina ärenden, adminlistan | En rapport syns direkt som Mottaget, finns kvar efter omladdning, syns i adminytan med full kontext; admin byter läge och kunden ser det; en annan användare ser den inte | Nej |
| 3 | Arbetsunderlaget och den kodande agenten | Ett påhittat fel i en förhandsvisning går från godkänt underlag till öppen ändringsbegäran utan fler handgrepp än startkommandot, och begäran bär ingen kundtext | Ja: GitHub-identitet, dataskyddsbeslutet |
| 4 | Testversionen och kundens svar | Miljön byggs från rättningens gren med bara testkundens arbetsyta; testkunden kommer in via länken, en annan kund nekas; ett utkast går inte att skicka där; kundens ja syns i ärendet och miljön töms | Ja: kostnaden hos Railway, läsrollen i produktionen |
| 5 | Automatiken | Tio riktiga felrapporter har gått hela kedjan med människan som enbart godkännare, byggtid och kostnad är uppmätta, och Anton har skriftligt släppt det manuella steget | Ja |

Fas 0 till 2 byggs direkt. Fram till att fas 3 och 4 är klara sköts rättningen
och testversionen av en människa bakom samma lägen, så kundens vy behöver inte
byggas om.

## Kräver Anton

Bygget utgår från förvalet tills han säger annat.

1. **Repot är publikt.** `oloflun/snipe-leads` är publikt på GitHub, och
   `docs/compliance/` med 106 filer ligger incheckad. `docs/BESLUT.md` säger att
   repot är privat. Ska det bli privat igen? Planen håller i båda fallen, men
   det här bör avgöras oavsett.
2. **Den kodande agenten och dataskyddet.** Får agenten (Anthropic) läsa det
   avpersonifierade, människogodkända underlaget? Förval: ja, och inget annat.
   Då ska underbiträdet in i förteckningen i samma ändring. Det hänger ihop med
   delmålet om språkmodell-leverantören.
3. **Kundens data i testversionen.** Får en kunds arbetsyta kopieras till en
   egen miljö hos Railway? Förval: ja, bara den kundens rader, noterat i
   registerförteckningen.
4. **Kostnad.** Testmiljön kostar hos Railway. Uppskattat 10 till 15 dollar i
   månaden om den står hela tiden; inte uppmätt. Betalning och planbyte är
   Antons handgrepp.
5. **Konton och hemligheter.** En GitHub-identitet för agenten, en nyckel för
   `snajp-hjalp`, och inloggningen för läsrollen som gör kundutdraget.
6. **Hur mycket kunden ser.** Förval: de sex lägena ovan, inga interna steg.
7. **Vem som ser en rapport.** Förval: bara den som skrev den.
8. **Kundens ja.** Förval: information, aldrig ett godkännande som släpper något.

## Risker

- **Tiden.** Nästa kund onboardas inom en vecka. Fas 0 till 2 hinns; fas 3 och
  4 hänger på beslut och konton. Säg det rakt till kunden: de första veckorna
  sköts rättning och testversion med en människa i ledet.
- **Snajps kunskapsbas är tunn.** Utan produkthjälp svarar Fråga svagt.
- **Kundutdraget är ny kod mot produktionsdata** med en roll som går förbi
  radspärrarna. Urvalet testas mot en påhittad databas med två kunder, och
  första körningen är en torrkörning som bara räknar rader.
- **Vitlistan för testmiljöns variabler.** Brister den kan riktiga mejl gå ut.
  Det testas uttryckligen.
- **Maskinens minne.** Den kodande agenten får inte köra samtidigt som de
  nattliga jobben.

## Avvisat

- **En flytande chattbubbla.** Bryter mot regeln om att bygga in i befintlig
  yta, och Meny är redan hjälpingången.
- **Återanvända testchatten.** Den går till kundens agent och kunskapsbas och
  skickar med arbetsytans tal.
- **Felrapport som GitHub-ärende.** Repot är publikt.
- **Agenten i GitHub Actions.** Arbetsflödena står still och exponerar
  hemligheter för grenar.
- **Agenten med Antons egen GitHub-inloggning.** Den går förbi alla grenskydd.
- **Testversion som kopia av development.** Den bär alla kunders data.
- **Funktionsflagga per arbetsyta i produktionen.** Då måste rättningen släppas
  till main innan kunden testat, vilket vänder på ordningen.
- **Låta modellen ensam avgöra att något är en felrapport.** Ärendet skapas av
  kundens klick.
- **Samma lösenord i testversionen.** Då lämnar lösenordens kontrollsummor
  produktionen.
