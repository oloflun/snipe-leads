# paket backend

## Bygge
Backendpaketet (planens del 2, 3 och 5) är byggt enligt kontraktet, och alla nya tester går igenom mot MemoryStorage. Två saker ligger utanför paketet och måste ordnas av någon annan, se ej_gjort. Den ena gör att tests/test_gdpr_radera.py nu fäller: kolumnen plattformsarenden.rapportor_namn saknas i scripts/gdpr_radera.py. Den andra är namnet på miljövariabeln: Next läser SNAJP_KEY_HJALP, men nyckelskriptet skriver SNAJP_KEY_SNAJP_HJALP.

Vägarna:
- **POST /api/hjalp/samtal** ligger i nya app/api/hjalp.py. Den godtar bara adresser på @kund.snajp.se och svarar som /api/chat/samtal. Grinden require_hjalp_tenant ger 404 för varje nyckel vars tenant inte har sluggen hjalp_tenant_slug.
- **Plattformsärendena** ligger i nya app/api/plattformsarenden.py: POST för att skapa, GET med ?rapportor=, samt /svar och /utslag. Listan filtreras alltid på rapportören. Bilden kontrolleras som chattens bilagor, och sida får bara vara en sökväg. Ärende som saknas eller tillhör någon annan ger 404, fel läge ger 409. Ändringen och händelsen skrivs i ett steg, så två samtidiga klick kan inte båda gå igenom.
- **Mejlet om en ny rapport** skickas i bakgrunden efter svaret. Det har ämnesraden "[PRIORITERAT] Ny felrapport" och bär bara ärendenumret och länken /admin?felrapport=<id>, aldrig kundens text. Om mejlet misslyckas sparas ärendet ändå.
- **Adminvägarna** ligger i nya app/api/admin_plattformsarenden.py: GET /api/admin/plattformsarenden?status= och POST .../{id}/status, under require_master_key och därmed åtkomstloggen. Lägena stangd och behover_mer kräver ett meddelande till kunden. Testversionens adress måste vara https och töms vid i_main och stangd.
- **POST /api/kb/forslag** i kb.py skapar ett väntande förslag i nyckelns egen tenant med kalla "chatt". Den kontrollerar längd, kategori mot KB_CATEGORIES och dubbletter mot både artiklar och väntande förslag (409). skapad_av tas ur X-Snajp-User när värdet är ett uuid. GET /api/kb/forslag lämnar nu fältet kalla.

Lagring och migrationer:
- Lagringen har fått metoderna skapa_plattformsarende, hamta_plattformsarende, list_plattformsarenden, andra_plattformsarende och skapa_kb_forslag, i en egen sektion sist i Storage-protokollet, MemoryStorage och PostgresStorage. Postgres når plattformstabellerna utan tenantkontext.
- Migration 156 skapar de två tabellerna med kontrollvillkor för status, unikt nummer och indexen. Radskyddet släpper bara in snajp_app när ingen tenantkontext är satt (samma villkor som 029). Webbens roll har ingen rätt alls, och ingen roll får radera.
- Migration 157 lägger till kalla, kalla_ref och skapad_av i ss_kb_forslag. skanning_id får vara null för andra källor än skanningen.

Hjälpens kund:
- Nya app/tenants/snajp_hjalp.py har seed_hjalp. Den skapar tenanten med avtalsgrinden avslagen och synkar artiklarna: Snajps befintliga artiklar plus 16 nya om den inloggade ytan. Varje påstående i artiklarna är belagt i gränssnittets texter, med källan i en kommentar.
- Kunden skapas inte automatiskt. I en miljö körs först `python -m app.tenants.snajp_hjalp` med miljöns DATABASE_URL. Därefter `python scripts/railway_tenantnyckel.py --slug snajp-hjalp --name "Snajp Hjälp" --env development --apply`, som utfärdar nyckeln. Körs de i omvänd ordning blir avtalsgrinden påslagen.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\config.py (fältet hjalp_tenant_slug = "snajp-hjalp" efter snajp_demo_api_key)
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\schemas.py (ny sektion sist: PlattformsarendeStatus, PlattformsarendeRequest, PlattformsarendeSvarRequest, PlattformsarendeUtslagRequest, PlattformsarendeStatusRequest, KbForslagChattRequest)
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\kb.py (import av KbForslagChattRequest; GET /api/kb/forslag sätter kalla='skanning' som förval; ny POST /api/kb/forslag)
- C:\Users\Anton L\snipe-leads\snajp-support\app\main.py (import och include_router för hjalp, plattformsarenden, admin_plattformsarenden)
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\base.py (protokollmetoder i ny sektion efter close; modulkonstanter PLATTFORMSARENDE_STATUSAR, PLATTFORMSARENDE_VANTAR_PA_KUND, ARENDENUMMER_ALFABET, KB_FORSLAG_KALLOR; funktionerna nytt_arendenummer och kontrollera_plattformsarende_status)
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\memory.py (ny sektion sist i klassen efter close)
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\postgres.py (ny sektion sist i klassen efter close)
- C:\Users\Anton L\snipe-leads\snajp-support\app\notifications\prioriterat_mejl.py (FELRAPPORT_RUBRIK, felrapportlank, felrapportmejl, skicka_felrapport; __all__ utökad)

### Nya filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\hjalp.py
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\plattformsarenden.py
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\admin_plattformsarenden.py
- C:\Users\Anton L\snipe-leads\snajp-support\app\tenants\snajp_hjalp.py
- C:\Users\Anton L\snipe-leads\db\migrations\20261125120000_156_plattformsarenden.sql
- C:\Users\Anton L\snipe-leads\db\migrations\20261125121000_157_kb_forslag_kalla.sql
- C:\Users\Anton L\snipe-leads\snajp-support\tests\api\test_plattformsarenden.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_hjalp_002.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\api\test_kb_forslag_chatt.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\notifications\test_felrapport_mejl.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\test_snajp_hjalp_kb.py

### Tester
- `cd snajp-support && python -m pytest tests/api/test_plattformsarenden.py -q -x -p no:cacheprovider` → 7 passed in 18.86s
- `cd snajp-support && python -m pytest tests/invariants/test_inv_hjalp_002.py -q -x -p no:cacheprovider` → 3 passed in 20.25s
- `cd snajp-support && python -m pytest tests/api/test_kb_forslag_chatt.py -q -x -p no:cacheprovider` → 2 passed in 19.15s (första körningen: 1 failed, för att testet antog att 'leveranstid' och 'leveranstider' blir samma rubriknyckel, vilket titelnyckel inte gör; testet rättat)
- `cd snajp-support && python -m pytest tests/notifications/test_felrapport_mejl.py -q -x -p no:cacheprovider` → 2 passed in 20.17s
- `cd snajp-support && python -m pytest tests/test_snajp_hjalp_kb.py -q -x -p no:cacheprovider` → 3 passed in 2.91s
- `cd snajp-support && python -m pytest tests/api/test_kb_forslag.py -q -p no:cacheprovider` → 8 passed in 20.01s
- `cd snajp-support && python -m pytest tests/test_kb_kategori_salj.py -q -p no:cacheprovider` → 4 passed in 14.71s
- `cd snajp-support && python -m pytest tests/api/test_chattar_api.py -q -p no:cacheprovider` → 3 passed in 19.94s
- `cd snajp-support && python -m pytest tests/notifications/test_prioriterat_mejl.py -q -p no:cacheprovider` → 27 passed in 20.06s
- `cd snajp-support && python -m pytest tests/invariants/test_delete_grants.py -q -p no:cacheprovider` → 1 passed in 1.37s
- `python -m pytest tests/invariants/test_inv_sec_013.py tests/test_rls_nullif_vakt.py -q -p no:cacheprovider (från repots rot)` → 1 failed, 8 passed in 36.20s. Det som föll är test_ett_masteranrop_ger_en_rad_utan_innehall, och felet är inte mitt: uppstarten fäller på LLM_PROVIDER=deepseek eftersom den lokala miljöns DATABASE_URL pekar på en fjärrdatabas. Rotens tester sätter inte om miljön som snajp-supports conftest gör, och spärren slår till innan någon databas öppnas. Strukturtestet för INV-SEC-013 (varje /api/admin-väg har require_master_key, de nya adminvägarna inräknade) och test_rls_nullif_vakt (migration 156) gick igenom.
- `python -m pytest tests/test_gdpr_radera.py -q -p no:cacheprovider (från repots rot)` → 1 failed, 12 passed in 2.67s. FÖRVÄNTAT FEL som jag inte kan rätta inom paketet: test_varje_personuppgiftskolumn_ar_hanterad fäller på kolumnen plattformsarenden.rapportor_namn, se ej_gjort.
- `python -m pytest tests/invariants/test_inv_copy_001.py -q -p no:cacheprovider` → 4 passed in 2.33s
- `python -m pytest tests/invariants/test_inv_hjalp_001.py -q -p no:cacheprovider` → 22 passed in 0.30s
- `python -m pytest tests/invariants/test_inv_tenant_001.py -q -p no:cacheprovider` → 13 passed in 0.26s
- `python -m py_compile app/storage/postgres.py app/storage/base.py app/tenants/snajp_hjalp.py && python -c "import app.storage.postgres as p; print(hasattr(p.PostgresStorage,'andra_plattformsarende'))"` → True (Postgres-vägen kompilerar men är inte körd mot en databas, se ej_gjort)

### Ej gjort
- scripts/gdpr_radera.py och tests/test_gdpr_radera.py ligger utanför paketet, och test_gdpr_radera fäller nu på plattformsarenden.rapportor_namn. Förslag: lägg plattformsarenden i TABELLER med villkoret på rapportor_user_id (händelserna följer med via on delete cascade, så plattformsarende_handelser hör hemma i KASKAD). Alternativet är en motiverad rad i UNDANTAG, men ärendet bär fritext från en namngiven användare, så radering är troligen rätt.
- Miljövariabelns namn: kontraktet säger SNAJP_KEY_HJALP, men scripts/railway_tenantnyckel.py och onboard_tenant.py härleder SNAJP_KEY_<SLUG>, alltså SNAJP_KEY_SNAJP_HJALP för sluggen snajp-hjalp. Antingen läser Next det härledda namnet, eller så sätts värdet för hand under SNAJP_KEY_HJALP. Ändras det måste kontraktet ändras.
- Hjälpens kund läggs inte i TENANTS i app/tenants/__init__.py, med flit. seed_kb.seed_tenant skapar tenanten utan kraver_avtal (alltså med grinden påslagen, och då svarar POST /api/chat 403 på varje fråga). Den fyller dessutom bara på artikel för artikel för sluggen 'snajp'. seed_hjalp i app/tenants/snajp_hjalp.py ersätter den vägen. Ska seed_kb.py kunna seeda hjälpen ska den anropa seed_hjalp, men filen ligger utanför paketet.
- Länken i mejlet går till /admin?felrapport=<id>, men adminytan läser inte parametern ännu (components/admin/Felrapporter.tsx och FelOchEskaleringar.tsx hör till ett annat paket). Utan det landar länken på översikten utan att markera ärendet.
- Det finns ingen väg för att visa felrapportens bild i adminytan. Kontraktet har bara har_bild, och lagringen lämnar aldrig ut bilden i listor eller uppslag. En sådan väg behöver ett kontraktstillägg (till exempel GET /api/admin/plattformsarenden/{id}/bild).
- Postgres-vägen (PostgresStorage-metoderna och migration 156/157) är inte körd mot en databas: det fick jag inte, och development speglar produktionen. Den bör prövas med scripts/lokal_stack.py, eller med ett test under tests/db i samma form som test_kb_forslag_atomisk.py, innan release.
- Ingen användarvänd UI-text är skriven i det här paketet, så INV-COPY-001 berörs inte. Backendens felmeddelanden (detail) är på svenska, som resten av API:t. Klienten översätter statusorden.
- Felrapporterna har ingen egen spärr mot många rapporter på kort tid. Kontraktet nämnde ingen, och vägen nås bara genom Next med en session.
- Ingen git add eller commit är gjord, och inga filer utanför paketet är rörda.

### Antaganden
- Ett ärende som inte finns eller tillhör en annan rapportör ger 404 på /svar och /utslag, inte 409. Uppgiften kan läsas som att även det ska ge 409, men 404 gör att ett främmande ärende inte går att skilja från ett som inte finns (samma resonemang som deps.kraev_uuid). Fel läge på ett eget ärende ger 409.
- Varje statusbyte från admin blir en kundsynlig händelse med den nya statusen, och meddelande_till_kund står i samma händelse. Alla statusvärden är kundens egna lägen, så det finns inget internt att dölja. Kundens svar och utslag är också kundsynliga händelser (typ 'kundsvar' och 'utslag'), och skapandet är händelsen 'skapad'.
- Admin får byta till vilken giltig status som helst, utan regler för vilka övergångar som är tillåtna, eftersom en människa sköter flödet fram till fas 3–4. Bara stangd och behover_mer kräver meddelande. redo_att_testa kräver ingen testversion_url, eftersom fas 4 inte finns ännu.
- testversion_url måste vara https. Den töms när ärendet går till i_main eller stangd (planens del 7: testversionen tas bort).
- Fälten gjorde och hande måste vara ifyllda (minst 1 tecken), medan vantade får vara tom. Alla tre har ett tak på 4000 tecken. vy och roll får vara högst 40 tecken, rapportor_namn högst 200 och kund_tenant_slug högst 100.
- Fältet sida måste börja med / och får inte börja med //. Det får inte innehålla ? eller #, inga blanktecken och högst 300 tecken; annars 422.
- aktor är 'kund' för kundens händelser. För admin blir den 'admin:<uuid>' när X-Snajp-Admin är ett giltigt uuid, annars 'plattformsadmin'.
- I mejlet står hjälpens egen tenant-id på raden Tenant, inte rapportörens kund eller arbetsyta. Dubblettnyckeln är felrapport:<id>.
- En dubblett vid POST /api/kb/forslag jämförs med kundens artiklar och väntande förslag via titelnyckel. Ett tidigare avvisat förslag hindrar inte ett nytt från chatten, eftersom kunden aktivt ber om det. Kategorin är ovrigt om den saknas. kalla_ref sätts inte (null).
- Hjälpens kunskapsbas tar inte med snajp_kb.py:s 'Hitta rätt på arbetsytan'. Den beskriver den gamla menyn (Iris › Bolag, Granskning) och ersätts av 'Arbetsytans meny'. Artikeln i snajp_kb.py lämnas orörd eftersom marknadssidans demo använder den.
- Artiklarna om Hjälprutan beskriver ingången (Meny › Hjälp och fel, Något är fel, Mina ärenden) och statusorden så som planen och kontraktet anger dem. Komponenterna byggs av ett annat paket, så artiklarna ska stämmas av mot dem när de är klara.
- Tenantens namn i ss_tenants är 'Snajp Hjälp'.

### Syns i gränssnittet
- Mitt paket har ingen egen UI-fil och ingen förhandsvisning. Ytorna som visar vägarna byggs av andra paket: rutan förhandsvisas på /forhandsvisning/hjalpruta (app/forhandsvisning/hjalpruta/) och adminlistan på /forhandsvisning/felrapporter (app/forhandsvisning/felrapporter/), med en lokal server på http://localhost:3000. De bör ses i bild med svarsformerna härifrån: Arende och AdminArende, vantar_pa_kund, händelser utan synlig_for_kund och aktor för kunden, och har_bild i stället för bilden.
- Förslagslistan i Kunskapsbas (components/settings/WebbplatsForslag.tsx) får nu fältet kalla ('skanning' eller 'chatt') på varje förslag. Om listan ska visa var förslaget kom ifrån är det UI-paketets sak, och det ska ses i bild där.
- Hjälpens svar i rutan bygger på kunskapsbasen i app/tenants/snajp_hjalp.py. Svarens innehåll syns först när hjälpens kund är seedad och nyckeln satt i en miljö. Det kan inte ses i en förhandsvisning utan databas.

## Granskning: godkänd=True
- [bor_rattas] scripts/gdpr_radera.py (utanför paketet) / db/migrations/20261125120000_156_plattformsarenden.sql: Den nya tabellen bär personuppgifter (rapportor_namn, fritext i gjorde/hande/vantade, bild), men GDPR-raderingen täcker den inte. tests/test_gdpr_radera.py::test_varje_personuppgiftskolumn_ar_hanterad fäller nu på 'plattformsarenden.rapportor_namn'. Jag har bekräftat det: 1 failed, 12 passed. Byggaren har redovisat det, och rättningen ligger utanför paketet. Committas paketet som det är blir testsviten röd, och en raderingsbegäran når inte felrapporterna. FÖRSLAG: Lägg in plattformsarenden i TABELLER i scripts/gdpr_radera.py med villkoret rapportor_user_id, och plattformsarende_handelser i KASKAD (de raderas via on delete cascade). Gör det i samma commit som paketet. Tänk på att migrationen tar bort delete-rätten för snajp_app: raderingsskriptet måste köra med en roll som har rätten kvar.
- [bor_rattas] snajp-support/app/storage/postgres.py:Hjälprutan-sektionen sist i PostgresStorage Postgres-vägen har aldrig körts. Det gäller skapa/hamta/list/andra_plattformsarende, skapa_kb_forslag, radskyddet i migration 156 (snajp_app utan tenantkontext) och villkoret i 157 (skanning_id not valid). Alla beteendetester går mot MemoryStorage. Koden ser riktig ut vid läsning: villkorad update med returning, retry på UniqueViolation, och _row strängar id/arende_id så att händelserna matchas. FÖRSLAG: Lägg till ett test under tests/db i samma form som test_kb_forslag_atomisk.py, eller pröva med scripts/lokal_stack.py före release. Pröva minst tre saker: att en _scoped-anslutning inte ser några ärenden, att den villkorade updaten ger None i fel läge, och att ett förslag med kalla 'chatt' och skanning_id null godtas medan ett med kalla 'skanning' och skanning_id null nekas.
- [bor_rattas] snajp-support/app/tenants/snajp_hjalp.py:docstring, steg 2 Miljövariabelns namn stämmer inte. Kontraktet säger SNAJP_KEY_HJALP, men railway_tenantnyckel.py skriver SNAJP_KEY_SNAJP_HJALP. Det är inget kontraktsbrott i backenden, som inte läser variabeln, men driftsättningen faller tyst om ingen sätter värdet för hand. FÖRSLAG: Orkestreraren bestämmer: antingen läser Next det härledda namnet (då ändras kontraktet), eller så står det i driftrutinen att värdet ska kopieras till SNAJP_KEY_HJALP.
- [notering] snajp-support/app/api/hjalp.py:34-39 Master-nyckeln får 403 på hjälpvägarna, inte 404, eftersom require_tenant fäller den innan require_hjalp_tenant körs. Kontraktet säger 404 för en nyckel vars tenant inte är hjälpens. Master-nyckeln saknar tenant, så det är en tolkningsfråga och ingen läcka. Testet kräver uttryckligen 403. FÖRSLAG: Godta det som det är, eller skriv in i kontraktet att master-nyckeln får 403.
- [notering] snajp-support/tests/api/test_plattformsarenden.py: Filtreringen på synlig_for_kund prövas aldrig med en händelse som är dold för kunden. Varje händelse som skapas i dag är synlig, eftersom adminvägen alltid sätter synlig_for_kund=True. Testet visar alltså inte att kundvy döljer interna händelser, bara att fälten synlig_for_kund och aktor tas bort. FÖRSLAG: Lägg in en händelse med synlig_for_kund=False direkt i MemoryStorage via andra_plattformsarende och kontrollera att GET ?rapportor= inte visar den.
- [notering] snajp-support/app/api/plattformsarenden.py:107-115 Bilden valideras som chattens bilagor, alltså med prefixet data:image/ och ett tak på 6 MB. Därmed godtas även data:image/svg+xml. Bilden sparas utan gallring, eftersom radering är bortdragen, och ingen väg visar den ännu. FÖRSLAG: När en bildväg för admin byggs (kontraktstillägg): servera bilden som en ren bild eller begränsa formaten till png, jpeg och webp, och bestäm hur länge felrapporter och bilder ska sparas.
- [notering] snajp-support/app/api/admin_plattformsarenden.py:35-40 Adminlistan har ett fast tak på 200 ärenden (förvalt limit i lagringen) och ingen sidindelning. Länken i mejlet (/admin?felrapport=<id>) läses inte av adminytan ännu. Byggaren har redovisat det. FÖRSLAG: Inget krävs nu. Följs upp i UI-paketet.

### Granskarens tester
- `cd snajp-support && python -m pytest tests/api/test_plattformsarenden.py -q -p no:cacheprovider` → 7 passed in 18.01s
- `cd snajp-support && python -m pytest tests/invariants/test_inv_hjalp_002.py -q -p no:cacheprovider` → 3 passed in 18.45s
- `cd snajp-support && python -m pytest tests/api/test_kb_forslag_chatt.py -q -p no:cacheprovider` → 2 passed in 15.66s
- `cd snajp-support && python -m pytest tests/notifications/test_felrapport_mejl.py -q -p no:cacheprovider` → 2 passed in 16.58s
- `cd snajp-support && python -m pytest tests/test_snajp_hjalp_kb.py -q -p no:cacheprovider` → 3 passed in 1.74s
- `python -m pytest tests/test_gdpr_radera.py -q -p no:cacheprovider (repots rot)` → 1 failed, 12 passed in 2.62s (test_varje_personuppgiftskolumn_ar_hanterad: ['plattformsarenden.rapportor_namn'])
- `python -m pytest tests/test_gallring_spegel.py -q -p no:cacheprovider (repots rot)` → 5 passed in 0.95s
- `python -m pytest tests/test_rls_nullif_vakt.py -q -p no:cacheprovider (repots rot)` → 5 passed in 0.29s
- `cd snajp-support && python -m pytest tests/invariants/test_delete_grants.py -q -p no:cacheprovider` → 1 passed in 1.19s

## Rättning
Jag prövade de tre fynden mot koden. Två kunde jag inte rätta inom paketet. Det tredje har jag rättat så långt jag får: Postgres-vägen har fått ett databastest. Själva körningen mot en databas återstår.

Fynd 2 (Postgres-vägen har aldrig körts): det nya testet är snajp-support/tests/db/test_plattformsarenden_db.py och har samma form som test_kb_forslag_atomisk.py. Det kör bara mot en lokal databas utan spegelmarkör och hoppar annars över. Det prövar tre saker:
- En kundskopad anslutning (_scoped) ser inga ärenden och inga händelser. Den kan inte heller skriva ett ärende, och approllen kan inte radera ett.
- Statusbytet i andra_plattformsarende ger None, och ingen händelse, i tre fall: fel läge, en annan rapportör och ett andra klick. Det rätta bytet ger exakt tre händelser, och listan visar bara rapportörens egna ärenden.
- Ett förslag med kalla 'chatt' och utan skanning godtas. Ett med kalla 'skanning' och utan skanning nekas med CheckViolation. kalla har förvalet 'skanning'.

Här hoppades alla tre testen över, eftersom jag inte får röra någon databas. CI kör dem inte heller förrän filen står i .github/workflows/verify.yml, som ligger utanför paketet.

Fynd 1 (GDPR): stämmer, men rättningen ligger i scripts/gdpr_radera.py, utanför paketet. Raderingsskriptet söker på mejladress, och plattformsarenden har ingen adress, bara rapportor_user_id. Villkoret måste därför gå via auth.users, se ej_gjort.

Fynd 3 (miljövariabelns namn): stämmer, och det är orkestrerarens beslut. Docstringen i snajp_hjalp.py säger redan att skriptet skriver SNAJP_KEY_SNAJP_HJALP och att värdet ska ligga under SNAJP_KEY_HJALP. Inget i backenden läser variabeln, så jag har inte ändrat något.

### Nya filer
- C:\Users\Anton L\snipe-leads\snajp-support\tests\db\test_plattformsarenden_db.py

### Tester
- `cd snajp-support && python -m pytest tests/db/test_plattformsarenden_db.py -q -p no:cacheprovider -rs` → 3 skipped in 0.35s (förväntat: GALLRING_TEST_DSN och GALLRING_TEST_APP_DSN saknas, och jag får inte röra någon databas)

### Ej gjort
- Fynd 1 (GDPR) är inte rättat: scripts/gdpr_radera.py och tests/test_gdpr_radera.py ligger utanför paketet. Skriptet söker per mejladress, men plattformsarenden har ingen adress. Förslaget att använda villkoret 'rapportor_user_id' rakt av fungerar därför inte. I TABELLER behövs i stället ett färdigt villkor: ("plattformsarenden", "rapportor_user_id in (select id from auth.users where lower(email) = lower(%s))", "Felrapporter ur Hjälprutan (namn, fritext, bild). Händelserna kaskaderar."). Därtill behövs ("plattformsarende_handelser", "arende_id in (select id from plattformsarenden where rapportor_user_id in (select id from auth.users where lower(email) = lower(%s)))", "plattformsarenden") i KASKAD. Det bör göras i samma commit som paketet, annars är test_gdpr_radera rött. Migration 156 tar bort delete-rätten för snajp_app. Skriptet ansluter med dsn_for (gdpr_verktyg) och inte som snajp_app, men den som lägger in raden bör bekräfta att rollen får radera i tabellen.
- Fynd 2 är bara delvis rättat. Testet finns men har inte körts mot en databas, eftersom ingen databas fick röras. CI-jobbet 'databas' i .github/workflows/verify.yml (rad 250) räknar upp sina testfiler. Där står varken test_plattformsarenden_db.py eller test_kb_forslag_atomisk.py, så CI kör inte heller det nya testet förrän filen läggs till i listan. Filen ligger utanför paketet. Alternativt kan testet köras lokalt mot scripts/lokal_stack.py med GALLRING_TEST_DSN och GALLRING_TEST_APP_DSN satta.
- Fynd 3 (SNAJP_KEY_HJALP mot SNAJP_KEY_SNAJP_HJALP) är inte ändrat. Det är inget fel i backenden, och docstringen i app/tenants/snajp_hjalp.py (rad 30–35) säger redan att värdet ska ligga under SNAJP_KEY_HJALP. Om Next ska läsa det härledda namnet i stället ändras kontraktet: det är orkestrerarens beslut.
- Ingen git add eller commit är gjord. Inga andra filer är rörda.

### Antaganden
- Testdatabasen i CI-jobbet 'databas' har alla migrationer körda, 156 och 157 inräknade, och rollen snajp_app finns. Samma förutsättning har de övriga testerna under tests/db.
- Ett avslag från radskyddets with check, och ett delete utan rätt, ger SQLSTATE 42501 (InsufficientPrivilegeError) i asyncpg.
- _row i postgres.py gör id till sträng, så att arende['id'] går att jämföra med listans id. tenant_id och skapad_av jämförs efter str().

### Syns i gränssnittet
- Inget nytt i den här rundan: bara ett databastest har tillkommit. Ytorna som visar vägarna förhandsvisas av de andra paketen på http://localhost:3000/forhandsvisning/hjalpruta och http://localhost:3000/forhandsvisning/felrapporter.
