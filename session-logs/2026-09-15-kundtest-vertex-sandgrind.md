# Session 2026-09-15: kundtestet i mål — Vertex, email-studio, sändgrinden

Fortsättning på QA-uppdraget från 09-08/09-12 ("testa allt som kund, sida för
sida"), som stått blockerat på LLM-krediter. Uppdraget slutfört i natt.

## Upplösningen på nyckelfrågan

Fyra dagars nyckelfelsökning fick sitt svar: **"Service Role" = Google-
servicekontot.** Anton lade `GOOGLE_SERVICE_ACCOUNT_JSON` på api-tjänsten,
och appen har inbyggt Vertex-stöd (`app/agent/llm.py:_resolve_base_url`) som
tar över så fort variabeln finns — chat, embeddings och vision går då till
`{region}-aiplatform.googleapis.com` med OAuth-token, fakturerat via Google
Cloud. Den tömda Gemini-API-nyckeln (`...Idfg`, prepay-krediter slut) blev
irrelevant; alla mina prober mätte fel dörr. `MODEL=gemini-2.5-flash` är
KORREKT på Vertex (modellen finns kvar där; mot generativelanguage svarar
den 404 "no longer available to new users" — lita inte på det probet).

## Genomfört kundtest (testkund+qa0904fable@snajp.se, dev)

- Testchatt: riktigt KB-grundat svar. Bokföringsassistenten: exakta
  periodsiffror ("räknar aldrig själv" håller). Bokförings-KPI:er korrekta.
- Leads-testkörning (2 bolag, research och utkast): hela V2-kedjan i mål —
  discovery → research → kvalificering → utkast → humanizer → granskningskö.
  Dedupe-fixen (c0ed60e) håller live. Kvalificeringsgrinden avvisar ärligt.
  3 anrop/lead (V1: 13+); humanizer in 8 349 tok live mot benchmarkens 8 254.
- Bolagssidan: alla utkastknappar via email-studio.

## Fixat: email-studio (5b7640f)

Efter att `GOOGLE_SERVICE_ACCOUNT_JSON` kopierats till web-tjänsten (via
Railway-API:t på Sebbes order — dashboardförsöket landade aldrig) svarade
modellen, men kunden såg rå JSON: prompten bad modellen EKA ursprungstexten
och `maxOutputTokens: 1800` skulle även rymma 2.5-flashens tänktokens →
svaret klipptes mitt i JSON:en. Fix: eko bort (`original_version:null`),
tak 3000, trunkeringsräddning i parsern (`new_version` ligger först och
överlever). Slutverifierat i UI:t: formaterad ny version, förklaring,
ämnesradsförslag, "Använd ny version" ersätter texten.

## Sändgrinden skarptestad (Sebbes order), noll mejl ut

"Godkänn och skicka" på ett origin=test-prospekt med riktig mottagaradress:

1. **Autonomigrinden höll:** deployade `process_due_item` kördes mot
   dev-DB:ns riktiga rad med en tripwire-provider som fångar sändförsök i
   stället för att skicka. Arbetsytan står på "draft" → `awaiting_review`,
   "autonominivån tillåter inte utskick av det här steget". Noll försök.
2. **Spärr noll dömer rätt:** `_kor_send_guard` direkt →
   `blockera`/`testkorning`, "Prospektet kommer från en egen provkörning
   och kan aldrig kontaktas." Skyddet håller alltså även för kunder MED
   sändautonomi. Tripwire-mönstret är värt att återanvända: en provider som
   larmar i stället för att skicka gör grindtest ofarliga.

Tidsgrinden gör att spärr noll aldrig syns i nattliga tester — schemaläggaren
requeue:ar utanför sändfönstret, så en "queued" rad kl 01 bevisar ingenting.

## Kvarlämnat medvetet

- Main-släppet ägs av sessionen snipe-leads-e6 (Sebbes uppdrag där); jag gav
  grönt ljus 02:15 med noteringen att 5b7640f måste med och att main-webbens
  omdeploy aktiverar email-studio-AI:n i produktion (variabeln ligger redan).
- Ett tidigare "Enter skickar inte chatten"-fynd DROGS TILLBAKA: formuläret
  är korrekt; det var browserpanelens syntetiska tangenttryck som inte
  utlöser implicit submit. Verifiera formulär från koden innan de döms.

## Tillägg: produktionsreleasen (PR #13)

- e6 lämnade över släppet. Den här sessionen öppnade release-PR #13 och
  kvitterade varje spetsflytt med en grindkommentar (c7b242b → 817ba04 →
  35d4f70). Före varje grönt verifierades deltat: bara `bokforing-webb/` och
  dokument, noll web/api-filer.
- Migration 065 visade sig redan applicerad på main och är verifierad verksam
  (`has_table_privilege` och filens eget verifieringskommando som snajp_app).
- Anton mergade. main står på `ed46200`, api och web SUCCESS, health 200.
- email-studio är pixelverifierad i produktion som admin: Förbättra ger
  formaterad version, förklaring, ämnesradsförslag och konfidens.
- qa_vyer mot produktion: anonym och admin är gröna. Kundrollen ger alltid
  2 avvikelser, eftersom `kund@example.com` är en dev-fixtur och med avsikt
  saknas i prods `auth.users` (0 träffar). Samma sak gällde i slutsvepet före
  releasen, så det är ingen regression.
- Efter releasen pushade testkörning c158455 och aa68ccf till development.
  De ligger INTE i main och behöver ett nytt release-tåg (PR med
  oloflun-review) när deras QA är klar.

## Tillägg: PR #14, PR #8 och ångerrätt-rättningen

- **PR #14 mergad** av oloflun. main och prod står på `871aa7d`, api och web
  SUCCESS. Den tog allt från development, inklusive testkörnings rättningar.
- **PR #8 stängd.** Dess `8fc8d34` var trasig. Innehållet var rätt, men de avsedda
  `\n\n`-escapesekvenserna hade blivit riktiga radbrytningar inne i en
  strängliteral, så app.main gick inte att importera. Konsolens "kr�ver" var
  bara visningen av "kräver", inte ett kodningsfel.
- **Egen felpush:** en cherry-pick av 8fc8d34 pushades eftersom `pytest | tail`
  under `set -e` ger tails exitkod. Den revertades direkt (`56d9dc7`), och dev
  hann aldrig servera den. Lärdom: kör pytest utan pipe, eller med pipefail.
- **Omskriven rättning `b756198`** med regressionstestet
  `tests/test_livrustning_kb.py`. Samma escape-fel dök upp i min egen testfil
  (Bash-verktyget äter backslashar), och testet stoppade det före push.
  Sviten: 1943 passed.
- **RÄTTELSE av ett eget påstående:** jag skrev att prod hade 0
  Livrustning-artiklar, både i commitmeddelandet för b756198 och i chatten.
  Det stämmer inte. Frågan sökte på `Livrustning AB`, men prod-tenanten heter
  `Livrustning` (dev: `Livrustning AB`). Prod seedades 2026-08-21 med 22
  artiklar, och ångerrätt-artikeln där är **byte-identisk** med b756198:s
  modul, eftersom den kom med när PR #8-grenen seedades i augusti. Prod
  behövde alltså ingen ändring.
- **Dev-raden (`233950cf`) är fortfarande gammal.** Min UPDATE stoppades av
  auto-lägets klassificerare. Sebbe körde SQL:en själv, men den landade inte i
  dev och inte heller i prod (id:t saknas där, 0 nya rader senaste 3 h).
  Cacheversionen höjdes inte, eftersom det inte fanns något att invalidera.
  Återstår: kör UPDATE i Railway-projektets development-miljö och höj sedan
  `cachev:kb:<tenant>` (namnrymden kommer från DATABASE_URL och miljönamnet,
  se app/redisnycklar.py).

## Tillägg 2026-09-16: slutläge vid avslut

- PR #18 mergad av oloflun 16:37Z; prod verifierad på `7cb74a8` (api/web/bokforing
  SUCCESS, health 200, SSO "Kör Agent", /demo-railen).
- Därefter gick Iris och Kvittohanteraren till main via annan session (main `e9564a6`).
- development = `b91cc48`, lokalt rent, inget opushat; alla fem dev-tjänster SUCCESS.
- Main saknar endast `b91cc48` (kvitto-assistentens resor) → release-PR #20, alla
  checkar gröna, väntar på Antons review. Inga migrationer i deltat; torrkörning
  mot main och development: inget väntande (063 redan körd i main).
- Öppet: Antons merge av #20 + prodverifiering; IMAP-host för kontakt@livrustning.se.
