# Strategier — snipe-leads

(Kanonisk slug är `snipe-leads`. Äldre poster från 2026-08-26 ligger i den omdirigerade
hubben `wiki/projects/snipe/strategies.md`.)

## 2026-08-27

### En juridisk paus som hävs av en deploy är inte en paus
- **När:** arbete stoppas av ett icke-tekniskt skäl (juridik, avtal, kunddata) och stoppet
  bara lever som ett konfigvärde eller en README-rad.
- **Gör:** förankra pausen i något en deploy inte kan återställa — en migration, ett saknat
  hemligt värde, en spärr i koden — och skriv i arbetsposten exakt vilka steg som måste vara
  gjorda innan den får hävas.
- **Undvik:** att lita på att "vi kom överens om att pausa". Arbetspost `snipe-a1c` är öppen
  just därför: produktionen kör Gemini igen utan att de dokumenterade åtgärderna gjorts.
- **Evidens:** Dröm 2026-08-27, bundle §4/§8.

### Kvotgränser mäts, gissas inte
- **När:** en extern gratisnivå misstänks strypa produktionen.
- **Gör:** mät den faktiska gränsen innan arbetet planeras om — mätningen gav 6 anrop per
  minut, inte den dygnsspärr som först antogs, vilket gör att en kö löser problemet i
  stället för ett leverantörsbyte.
- **Undvik:** att bygga en migreringsplan på en antagen kvot.
- **Evidens:** Dröm 2026-08-27, arbetspost `snipe-zfn`.

## 2026-09-29
### Exempeldata i produktionsvägen döljer att motorn är död
- **När:** en funktion har en demo-/exempelgren i samma kodväg som den riktiga körningen.
- **Gör:** låt exempelutdata bära en synlig markör och låt en misslyckad riktig körning
  bli ett fel, inte ett exempel. En körning som inte kan nå motorn ska returnera fel.
- **Undvik:** att bedöma funktionen på utdatans utseende. Varje riktig leads-körning dog
  på ett `NameError` innan källhämtningen (`680c778`), men gränssnittet fortsatte visa
  färdiga exempel — felet upptäcktes först när Anton skrev "det fungerar inte att anropa
  agenter överhuvudtaget ... leadskörningar genererar fortfarande färdiga exempel direkt
  utan riktig agentkörning".
- **Evidens:** Dröm 2026-08-30, bundle §2b (08-29 23:53) och §6.
- **Åtgärd registreras som:** ny arbetspost i snipe-leads (finns ännu inte).
### Två miljöer som delar nyckelrymd är en miljö
- **När:** produktion och spegel/dev pekar på samma Redis, samma databas eller samma
  externa nyckel.
- **Gör:** namnrymda per driftsättning innan miljön tas i bruk, och skriv i STATUS vad
  som var exponerat under tiden delningen pågick.
- **Undvik:** att kalla det "samma data, olika appar". Delningen omfattade job-ström,
  svarscache och arbetsminne — dev kunde konsumera produktionens jobb.
- **Evidens:** Dröm 2026-08-30, bundle §6 (`810a511`, `c424ca7`); jfr öppen post
  `snipe-3to` om egen `GEMINI_API_KEY` per miljö, som är samma problem i ett annat lager.

## 2026-09-30
### En global reserv för en per-kund-integration är en läcka mellan kunder
- **Bygger på:** "Två miljöer som delar nyckelrymd är en miljö" (08-30).
- **När:** en tenant-integration (IMAP, API-nyckel, webhook) har globala env-variabler som fallback när kunden saknar egen.
- **Gör:** saknad per-kund-konfig = "ej kopplad", aldrig global reserv. Mät skadan per konto (antal, inte innehåll).
- **Undvik:** att tro att borttagna env-variabler når körande containrar — det kräver ny deploy/omstart.
- **Evidens:** `f9eaac6c` 09-29/30: adminbrevlådan läckte till `kund-ea08b974` (main, 8 mail) och demokontot (dev, 6); fix `eb3ea9d`; main väntar på PR #28/Redeploy.

## 2026-10-01
### Ett lead utan verifierad kontaktperson med roll och telefon är inget lead
- **När:** leads-/Iris-körningar sammanställer en lista mot en beställning.
- **Gör:** hårt filter före rangordning (kontakt + roll + telefon + lägesbeskrivning med poäng/signaler); räkna levererat mot beställt och rapportera underskottet.
- **Undvik:** att fylla listan till beställt antal med okvalificerade bolag — "leadslistorna är katastrof och stämmer inte mot kraven".
- **Evidens:** `842a0b06` 23:58 (Antons krav ordagrant i bundle 1c).

### En körning som inte kan följas dör tyst
- **När:** ett långt bakgrundsjobb (leads-batch, Iris) startas från UI:t.
- **Gör:** ledger-rad per körning med status/levererat/bortvalt, synlig och återvändbar (INV-JOB-003); slutstatus även vid noll resultat.
- **Undvik:** att noll nya leads ser ut som "fortfarande igång".
- **Evidens:** `842a0b06`: körningen slutade utan leads och utan spår → `1e96688` (migration 080).

### Kod som skriver en ny kolumn: migrationen före pushen
- **När:** en commit skriver till en kolumn som en ny migration skapar och Railway deployar på push.
- **Gör:** `railway_migrate.py --env <env> --apply` först, sedan `git push`.
- **Undvik:** push först — varje batchkörning faller tills migrationen körts.
- **Evidens:** `HANDOFF-2026-10-01-KORNINGAR.md` (080, `leads_job_ledger.korning`).

## 2026-10-03
### Fler sidor är inte mer produkt — bygg ihop innan du bygger ut
- **När:** en ny funktion ska in i appen (Iris, listor, körningar).
- **Gör:** placera den som vy/flik under ett befintligt objekt (Twenty-modellen: ett objekt per sida, vyerna inuti); döp efter användarens ord ("leads", inte "bolag").
- **Undvik:** en ny toppnivåsida per funktion, och flikar för funktioner som inte finns ("kanban" utan kanban).
- **Evidens:** `312b3ed3` 10-02 22:35 "rörigt och utspritt … Iris-sidor fler och mer spridda än någonsin"; 23:32 "Leads ska heta leads … vad står kanban för?".
### Prospekt utan telefon är en annan lista, inte skräp
- **Bygger på:** "Ett lead utan verifierad kontaktperson med roll och telefon är inget lead" (10-01).
- **När:** kvalificeringen sorterar bort kandidater som saknar telefon men har mail.
- **Gör:** spara dem i en separat underflik av samma lista (sortera på telefon/mail); låt listor kombineras.
- **Undvik:** att kasta dem, eller blanda dem i en separat mailista.
- **Evidens:** `842a0b06` 10-01 22:40.

## 2026-10-25
### SL1. Mallfraser i utkast: tillåtna ibland i varierad form, aldrig i varje mejl
- **När:** en fras som "kräver att ni kan fokusera på varje projekt" återkommer i en utkastbatch.
- **Gör:** låt den förekomma i ungefär vart fjärde mejl och variera formuleringen (S11).
- **Undvik:** att förbjuda den helt, och att låta den stå i alla mejl.
- **Evidens:** Antons rättelse 10-25 00:49 i `54579688`.

### SL2. Iterera utkast i mätta varv mot en fast feltabell
- **När:** utkastkvaliteten ska förbättras över flera provkörningar.
- **Gör:** gör en tabell per varv med antal utkast, ordspann, frekvensen för mallgreppet och antal påhittade förmågor, och visa alla utkast.
- **Undvik:** att säga "bättre" utan siffror per varv.
- **Evidens:** `54579688` varv 1→3: 12/17, 11/14, 14/14. Ord 105–150 → 83–123. Greppet 5/12 → 1/14. Påhittade förmågor försvann.
