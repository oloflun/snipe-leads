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
