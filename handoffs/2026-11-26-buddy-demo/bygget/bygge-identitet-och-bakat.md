# paket identitet-och-bakat

## Bygge
Både fel 1 och fel 2 är rättade och de statiska testerna är gröna. En sak är kvar som jag inte fick göra: utloggningen returnerar nu en adress, och då kompilerar inte components/AppShell.tsx och components/auth/OnboardingWizard.tsx. Båda ligger utanför mitt paket och måste ändras i samma commit (se ej_gjort).

FEL 2, felsidan vid bakåtknappen: /admin ligger nu i protectedRoutePrefixes. Proxyn skickar en besökare utan session till /login, och next bär nu både sökväg och söksträng (två ställen, och klonens egen söksträng nollställs). Kommentaren om /admin i proxy.ts är rättad och matcher-exporten heter fortfarande config.

Admin-layouten frågar först auth(). Utan session går besökaren till /login?next=/admin. En admin som stoppas av tvåfaktorn går till /settings/tvafaktor och en inloggad icke-admin till /dashboard; notFound() är borta. Kommentaren i layouten beskriver det ändrade säkerhetsvalet. /api/admin är orörd och svarar fortfarande 404.

startsidaFor känner igen ett next under /admin. En kund skickas då till /dashboard, en admin som stoppas av tvåfaktorn till /settings/tvafaktor, och en admin behåller sitt next.

FEL 1, fel arbetsytas data under rätt skal:
- **En funktion räknar identiteten.** Den nya exporten snajpIdentitet() i lib/snajp/tenant.ts räknar en opak sha256-hash av användar-id, vy och slug. Den läser sessionen och aktivVy(), inget annat. Utan session blir det en fast hash för utloggad.
- **Proxyn märker varje svar.** proxyAsTenant sätter X-Snajp-Identitet på varje svar från en enda utgång, även vid tenantfel och läsrollens 403. Den gamla kroppen ligger kvar som den privata funktionen vidarebefordra.
- **Svaren cachas inte.** proxyWithApiKey sätter Cache-Control: private, no-store och Vary: Cookie på alla utgångar, via ett tunt omslag runt den privata vidarebefordraMedNyckel.
- **Ny route.** GET /api/snajp-support/identitet kör requireSnajpTenant och svarar med hashen i huvud och kropp, no-store. Utan session svarar den 401; andra tenantfel ger 200, eftersom de gäller panelerna och inte vem som är inloggad.
- **Layouten bär samma värde.** DashboardState har fått det valfria fältet identitet, satt av resolveDashboardState med samma funktion.
- **Jämförelsen sker på ett ställe.** DashboardProvider har en osynlig kontroll i en Suspense-gräns som jämför vid ändring av pathname eller searchParams, vid focus, vid visibilitychange och vid meddelanden på BroadcastChannel("snajp-identitet"). Vid skillnad laddar den om. Loopskyddet i sessionStorage tillåter högst en omladdning per byte, och nyckeln rensas när identiteten stämmer igen.
- **Inga server-redirects.** signInWithPassword returnerar { success, url } och rensar snajp.vy. signOut returnerar { url: "/login" }, rensar snajp.vy och loggar ut utan redirect. bytVy returnerar { url } eller { url: null }.
- **Anroparna öppnar adressen hårt.** De nya hjälparna oppnaEfterIdentitetsbyte, bytVyOchOppna och loggaUtOchOppna i DashboardContext.tsx postar på kanalen och öppnar med window.location.replace. LoginForm (inloggning, tvåfaktorsteg och registrering), SignOutButton, AdminShell, VyVaxel, BytKund, OppnaArbetsyta och ImpersonationBanner använder dem. OAuth-vägen var redan en hård navigering och kunden hamnar rätt via layoutens nya gren.
- **Körnings-id:t följer inte med.** localStorage-nyckeln i LeadsRunForm är nu snipra:korning:<identitet>, med den gamla nyckeln som reserv där identitet saknas.

Alla nya tester fällde dagens kod innan rättningen och är gröna nu. Den scopade typkontrollen är ren utom de två väntade felen i AppShell.tsx.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\lib\routes.ts
- C:\Users\Anton L\snipe-leads\proxy.ts
- C:\Users\Anton L\snipe-leads\lib\actions\auth.ts
- C:\Users\Anton L\snipe-leads\lib\actions\vy.ts
- C:\Users\Anton L\snipe-leads\lib\snajp\tenant.ts
- C:\Users\Anton L\snipe-leads\lib\data\dashboard.ts
- C:\Users\Anton L\snipe-leads\components\dashboard\DashboardContext.tsx
- C:\Users\Anton L\snipe-leads\app\admin\layout.tsx
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\_auth.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\_lib.ts
- C:\Users\Anton L\snipe-leads\components\auth\LoginForm.tsx
- C:\Users\Anton L\snipe-leads\components\auth\SignOutButton.tsx
- C:\Users\Anton L\snipe-leads\components\VyVaxel.tsx
- C:\Users\Anton L\snipe-leads\components\admin\BytKund.tsx
- C:\Users\Anton L\snipe-leads\components\admin\OppnaArbetsyta.tsx
- C:\Users\Anton L\snipe-leads\components\ImpersonationBanner.tsx
- C:\Users\Anton L\snipe-leads\components\admin\AdminShell.tsx
- C:\Users\Anton L\snipe-leads\components\leads\LeadsRunForm.tsx
- C:\Users\Anton L\snipe-leads\tests\e2e\kundresa.spec.ts
- C:\Users\Anton L\snipe-leads\tests\invariants\test_inv_sec_011.py

### Nya filer
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\identitet\route.ts
- C:\Users\Anton L\snipe-leads\lib\routes.test.ts
- C:\Users\Anton L\snipe-leads\lib\identitet-proxy.test.ts
- C:\Users\Anton L\snipe-leads\tests\fixtures\identitet-proxy\hooks.mjs
- C:\Users\Anton L\snipe-leads\tests\fixtures\identitet-proxy\tenant-stub.ts
- C:\Users\Anton L\snipe-leads\tests\fixtures\identitet-proxy\lib-stub.ts
- C:\Users\Anton L\snipe-leads\tests\invariants\test_inv_auth_002.py
- C:\Users\Anton L\snipe-leads\tests\invariants\test_inv_sec_014.py

### Tester
- `node --test lib/routes.test.ts (före rättningen)` → FÄLLDE som avsett: isProtectedRoute('/admin') gav false (actual: false, expected: true)
- `node --test lib/routes.test.ts` → ℹ pass 4 / ℹ fail 0
- `node --test lib/identitet-proxy.test.ts (före rättningen)` → FÄLLDE som avsett: X-Snajp-Identitet saknades (actual: null) i alla tre testerna
- `node --test lib/identitet-proxy.test.ts` → ℹ pass 3 / ℹ fail 0
- `python -m pytest -q tests/invariants/test_inv_auth_002.py (före rättningen)` → 6 failed in 3.02s
- `python -m pytest -q tests/invariants/test_inv_auth_002.py` → 6 passed in 0.26s
- `python -m pytest -q tests/invariants/test_inv_sec_014.py (före rättningen)` → 17 failed in 3.98s
- `python -m pytest -q tests/invariants/test_inv_sec_014.py` → 17 passed in 0.47s
- `python -m pytest -q tests/invariants/test_inv_sec_011.py` → 9 passed in 0.99s (det nya testet är en vakt och var grönt redan före ändringen, eftersom tenant.ts aldrig läst header, query eller cookie)
- `python -m pytest -q tests/invariants/test_inv_copy_001.py` → 4 passed in 1.89s
- `python -m pytest -q tests/invariants/test_inv_auth_001.py` → 10 passed in 0.19s
- `python -m pytest -q tests/invariants/test_inv_sec_010.py` → 27 passed, 6 skipped in 0.28s
- `python -m pytest -q tests/invariants/test_inv_ui_001.py` → 4 passed in 0.99s
- `python -m pytest -q tests/test_bokforing_atkomst.py` → 14 passed in 0.44s
- `python -m pytest -q tests/test_leads_ui_endpoints.py` → 7 passed in 19.21s
- `python -m pytest -q tests/test_vilande_agenter.py` → 6 passed in 0.21s
- `python -m pytest -q snajp-support/tests/invariants/test_inv_job_003.py` → 11 passed in 16.06s
- `node --max-old-space-size=2048 node_modules/typescript/bin/tsc -p <scratchpad>/tsconfig.identitet.json (bara de rörda filerna och det de importerar)` → 2 fel, båda väntade och utanför paketet: components/AppShell.tsx(443,25) och (509,23) error TS2322: Type '() => Promise<{ url: string; }>' is not assignable to type 'string | ((formData: FormData) => void | Promise<void>) | undefined'. Inga fel i paketets filer.
- `tests/e2e/kundresa.spec.ts` → EJ KÖRD (kräver lokal stack). Inte typkontrollerad heller, eftersom tests/e2e är undantagen i tsconfig och @playwright/test inte är installerat.

### Ej gjort
- MÅSTE GÖRAS I SAMMA COMMIT, annars kompilerar inte appen: components/AppShell.tsx (rad 25, 443, 509) och components/auth/OnboardingWizard.tsx (rad 9, 630, 709) använder fortfarande <form action={signOut}>. Filerna ligger utanför mitt paket, så jag har inte rört dem. Rättningen är två rader per fil: byt importen av signOut mot `import { loggaUtOchOppna } from "@/components/dashboard/DashboardContext"` (i AppShell finns redan useDashboard-importen) och skriv action={loggaUtOchOppna}. Utan rättningen fäller tsc med TS2322. Därefter kan AppShell.tsx och OnboardingWizard.tsx läggas till i parametriseringen av test_anroparna_oppnar_adressen_hart i tests/invariants/test_inv_sec_014.py.
- ARCHITECTURE_INVARIANTS.md har jag inte rört (utanför paketet), fast regeln kräver att invariantens text ändras i samma arbete. Tre saker behövs: en ny post INV-SEC-014 (identitetsbyte; test tests/invariants/test_inv_sec_014.py), en ny post INV-AUTH-002 (matcher och protectedRoutePrefixes får inte glida isär, admin-layouten frågar auth() först och skickar en inloggad icke-admin till /dashboard; test tests/invariants/test_inv_auth_002.py), och ett tillägg i INV-SEC-011 om att requireSnajpTenant aldrig läser tenant ur header, query eller cookie.
- docs/BESLUT.md har jag inte rört (orkestreraren skriver den). Tre beslut ska in där: att 404 för en inloggad icke-admin på /admin ersattes av en omdirigering till /dashboard (Antons krav 2026-11-24), att en anonym besökare på /admin/** nu skickas till /login, och att in- och utloggning samt vybyte navigerar hårt. Det sista betyder att formulären inte längre fungerar utan JavaScript.
- app/cookies/CookiesSida.tsx (utanför paketet) nämner fortfarande localStorage-nycklarna snipra:korning:kund och snipra:korning:admin. De heter nu snipra:korning:<identitet>, så texten bör uppdateras.
- Punkt 10 i lib/http/json.ts (401 leder till /login?next=, egen tvåspråkig 403-text) är inte gjord. Den var valfri, och 401-vägen täcks nu av identitetskontrollen för alla inloggade träd: en utgången session ger identiteten för utloggad, fliken laddar om och proxyn skickar till /login. Ändringen i json.ts påverkar alla anropare och hela filen är i dag bara på svenska, så den bör göras för sig.
- Ingen visuell granskning. Inget nytt syns i gränssnittet (se syns_i_granssnittet), men omdirigeringarna och omladdningarna behöver prövas i en körande app.
- Ingen eslint-körning, för att spara minne. Den extra beroendet på pathname och sokning i useEffect i Identitetskontroll är avsiktlig.
- E2e-testerna är skrivna men inte körda, som uppdraget sa. Tvåfliksfallet hoppas över utan QA_ADMIN_LOSEN och förutsätter ett adminkonto utan tvåfaktor i lokal_stack.
- Ingen git add eller commit.
- Den vidarebefordrade begäran om att ta bort tempmapparna ingick inte i det här byggsteget, och jag har inte rört dem. Tänk på att utredningsfilerna och tsconfig för typkontrollen ligger i scratchpaden under Temp.

### Antaganden
- Identiteten för vyn admin bygger på arbetsytans slug, och på dess id när slug saknas. För vyerna kund och demo bygger den på sluggen från aktivVy(). Kopplas en slug först i requireSnajpTenant ändras identiteten, och fliken laddar om en gång.
- DashboardState.identitet är valfri, så att app/demo och app/duo-demo (utanför paketet, utan session) fortsätter kompilera. Där görs ingen kontroll.
- Ett tomt eller saknat X-Snajp-Identitet läses som okänt och ger ingen omladdning. Det gäller när snajpIdentitet kastar i proxyn eller layouten.
- Identitetsrouten svarar 200 för andra tenantfel än 401 (till exempel en arbetsyta som inte är aktiverad), så att e2e-felvakten inte fälls på varje sida. 401 utan session ingår i TILLATNA i kundresa.spec.ts.
- En admin vars session saknar tvåfaktormarkeringen skickas också till /settings/tvafaktor. Beslutet sa att en admin som stoppas av tvåfaktorn ska dit, och jag lät det gälla båda fallen.
- BroadcastChannel-meddelandet startar en ny identitetskontroll i stället för en blind omladdning, så att bara flikar vars identitet faktiskt bytts laddar om. Fliken som gör bytet får inte sitt eget meddelande, eftersom kanalen är en enda instans per flik.
- Enhetstestet för proxyAsTenant laddar _auth.ts med en egen resolve-hook i tests/fixtures/identitet-proxy, eftersom node --test inte kan lösa upp @/-aliaset. Tenantmodulen och backendproxyn är stubbar.
- OAuth-vägen lämnades oförändrad: den navigerade redan hårt med window.location.assign. Det är layoutens nya gren som skyddar en kund vars callbackUrl pekar på /admin.

### Syns i gränssnittet
- Inga nya element, rutor eller texter. Allt nedan gäller navigering och måste ses i en körande app.
- En inloggad kund på /admin eller /admin/** hamnar på /dashboard i stället för felsidan Sidan finns inte.
- Utan session leder /admin/** (även själva /admin) till /login med next. Bakåt efter utloggning visar inloggningen, aldrig en felsida.
- Inloggning, registrering, utloggning och vybyten (Admin | Demo, Byt kund, Öppna på Kunder-raden, Tillbaka till adminytan) gör nu en hel sidladdning i stället för en mjuk navigering. Det tar någon sekund längre och knapparna fungerar inte utan JavaScript.
- Andra öppna flikar laddar om när identiteten byts i en flik (via BroadcastChannel), och en gammal flik laddar om vid nästa navigering, fokus eller när den blir synlig. Ska prövas med två flikar: kund i flik A, admin i flik B.
- Ett pågående körnings-id i Leads-formuläret följer inte längre med mellan konton eller kundbesök. Ett id som sparats under den gamla nyckeln återupptas inte efter uppdateringen.

## Granskning: godkänd=False
- [blockerande] components/AppShell.tsx, components/auth/OnboardingWizard.tsx (utanför paketet, följd av lib/actions/auth.ts):AppShell 25/443/509, OnboardingWizard 9/630/709 signOut returnerar nu Promise<{ url: string }> och loggar ut med redirect:false. De två filerna använder fortfarande <form action={signOut}>. Det ger TS2322 (byggfel), och i drift blir användaren kvar på sidan, utloggad och utan omdirigering. Det gäller kundskalets utloggning och onboardingens. Paketet kan alltså inte committas ensamt. Byggaren har redovisat det korrekt och lämnat filerna orörda, så felet ligger inte i byggarens arbete. Det är ändå blockerande för en commit. FÖRSLAG: Orkestreraren ändrar i samma commit: byt importen mot loggaUtOchOppna från @/components/dashboard/DashboardContext och skriv action={loggaUtOchOppna} (två ställen per fil). Lägg sedan till båda filerna i parametriseringen av test_anroparna_oppnar_adressen_hart i tests/invariants/test_inv_sec_014.py. Kör den scopade tsc igen. Annars är paketet godkänt.
- [bor_rattas] ARCHITECTURE_INVARIANTS.md (utanför paketet): INV-SEC-014 och INV-AUTH-002 har nya tester men ingen post i ARCHITECTURE_INVARIANTS.md, och INV-SEC-011 har fått en ny vakt utan att invariantens text ändrats. Uppgiften kräver att text och test ändras i samma arbete. FÖRSLAG: Orkestreraren lägger till posterna INV-SEC-014 och INV-AUTH-002 och tillägget i INV-SEC-011 i samma commit, tillsammans med BESLUT.md-raderna: 404 för en icke-admin ersatt av omdirigering till /dashboard, anonym besökare på /admin till /login, hård navigering vid identitetsbyte som inte fungerar utan JS.
- [bor_rattas] tests/e2e/kundresa.spec.ts:483-528 Tvåfliksfallet byter cookies direkt i kontexten och loggar inte in admin i flik B, som uppgiften beskrev. Det prövar jämförelsen vid mjuk navigering men inte BroadcastChannel-vägen. Testet har dessutom en verklig adminadress (snajpsupport@gmail.com) som standardvärde för QA_ADMIN_EPOST, trots att det ska köras med syntetiska konton i lokal_stack. FÖRSLAG: Ta bort standardadressen och hoppa över testet när QA_ADMIN_EPOST saknas. Lägg gärna till en variant där admin loggar in i en andra page i SAMMA kontext, så att flik A laddar om via kanalen utan egen navigering. E2e är inte körda.
- [notering] app/admin/layout.tsx:61-64 En admin vars konto har aktiv tvåfaktor men vars session saknar tvåfaktormarkeringen skickas till /settings/tvafaktor. Det är en inrullningssida, och utredaren föreslog /login för just det fallet. Ingen loop uppstår, men admin kan bli stående på en sida som inte hjälper. Byggaren redovisade valet som antagande. FÖRSLAG: Låt Anton avgöra. Alternativet är /login?next=/admin när getPlatformAdminUtanTvafaktorkrav().tvafaktorISessionen är false och kontot har aktiv tvåfaktor.
- [notering] app/api/snajp-support/_auth.ts, lib/snajp/tenant.ts:_auth.ts 15-19, tenant.ts 20-29 proxyAsTenant räknar nu snajpIdentitet() på varje proxat anrop. Det betyder getWorkspaceContext plus aktivVy/getPlatformAdmin, utöver det requireSnajpTenant redan gjort. Om React cache inte deduplicerar i route handlers blir det extra DB-frågor per API-anrop. Identitetsrouten kör dessutom requireSnajpTenant vid varje navigering, fokus och synlighetsbyte. Ingen korrekthetsbrist, men en driftkostnad som inte är mätt. FÖRSLAG: Mät i den körande appen. Låt annars snajpIdentitet ta emot det redan upplösta tenant-objektet i proxyn, med samma funktion som källa.
- [notering] components/dashboard/DashboardContext.tsx:47-59 Utloggning och vybyte är nu server actions som sätter eller rensar cookies utan redirect, och klienten anropar window.location.replace först efter svaret. Next renderar om den aktuella sidan i action-svaret när cookies ändras. Om layouten då själv kastar redirect (en sida utan session) är det oprövat att löftet hinner lösas och replace körs. Slutläget blir troligen ändå /login, men det är inte verifierat. FÖRSLAG: Pröva i den körande appen eller med e2e-testet sessionen innan commit: utloggning från /dashboard, /admin och /onboarding ska landa på /login med en hel sidladdning.
- [notering] components/auth/LoginForm.tsx:292 (OAuth) OAuth-inloggningen postar inte på kanalen snajp-identitet. Andra flikar märker bytet först vid fokus eller nästa navigering. Det är acceptabelt eftersom kontrollen täcker fallet. FÖRSLAG: Ingen åtgärd krävs. Lägg eventuellt identitetskanal-posten före window.location.assign.
- [notering] lib/actions/auth.ts:181-201 Logiken i startsidaFor stämmer: regexet ^/admin(?:[/?#]|$) fångar /admin och undervägar men inte /adminx, en kund går till /dashboard, en admin med krävd men saknad tvåfaktor går till /settings/tvafaktor och en admin behåller sitt next. Den statiska testen för det är svag (söker bara strängar). Det finns inget beteendetest för startsidaFor; e2e-steget login?next=/admin/arbetsyta täcker det men är inte kört. FÖRSLAG: Ingen ändring krävs nu.

### Utanför paketet
- components/AppShell.tsx: <form action={signOut}> på rad 443 och 509 måste bli loggaUtOchOppna i samma commit (byggfel och utloggning utan omdirigering).
- components/auth/OnboardingWizard.tsx: <form action={signOut}> på rad 630 och 709, samma ändring.
- ARCHITECTURE_INVARIANTS.md: nya poster INV-SEC-014 och INV-AUTH-002 och tillägg i INV-SEC-011.
- docs/BESLUT.md: 404 → /dashboard för en icke-admin på /admin, anonym besökare på /admin till /login, hård navigering vid identitetsbyte (formulären kräver nu JS).
- app/cookies/CookiesSida.tsx rad 241 nämner fortfarande snipra:korning:kund och snipra:korning:admin. Nycklarna heter nu snipra:korning:<identitet> (tvåspråkig text).
- lib/auth/admin.ts rad ~50 (dokumentkommentar) säger fortfarande att /admin/layout.tsx svarar 404. Inaktuellt efter ändringen.
- lib/http/json.ts (punkt 10, valfri) är inte gjord: 401 till /login?next= och en egen tvåspråkig 403-text.
- Den vidarebefordrade användarbegäran 'Ta bort tempmapparna helt' har inte utförts. Granskaren ändrar inga filer, och scratchpaden under Temp innehåller utredningsfilerna och byggarens tsconfig. Orkestreraren får avgöra när och vilka mappar som tas bort.

### Granskarens tester
- `node --test lib/routes.test.ts` → ℹ pass 4 / ℹ fail 0 (sista raden: ℹ duration_ms 1301.8638)
- `node --test lib/identitet-proxy.test.ts` → ℹ pass 3 / ℹ fail 0 (sista raden: ℹ duration_ms 3053.1459)
- `python -m pytest -q tests/invariants/test_inv_auth_002.py` → 6 passed in 0.41s
- `python -m pytest -q tests/invariants/test_inv_sec_014.py` → 17 passed in 0.57s
- `python -m pytest -q tests/invariants/test_inv_sec_011.py` → 9 passed in 0.50s
- `python -m pytest -q tests/invariants/test_inv_copy_001.py` → 4 passed in 3.16s
- `python -m pytest -q tests/invariants/test_inv_sec_010.py` → 27 passed, 6 skipped in 0.44s
- `tests/e2e/kundresa.spec.ts` → EJ KÖRD (kräver lokal stack, enligt uppdraget)
- `scoped tsc` → Inte omkörd av granskaren (minnesskäl). Byggarens resultat: två TS2322 i components/AppShell.tsx, inga fel i paketets filer. OnboardingWizard.tsx ingick troligen inte i byggarens scope men har samma fel.

## Rättning
Jag har rättat det enda fyndet som låg inom paketet, i tests/e2e/kundresa.spec.ts. Tvåfliksfallet har inte längre någon riktig adminadress som standardvärde. Både adressen och lösenordet läses nu ur QA_ADMIN_EPOST och QA_ADMIN_LOSEN, och testet hoppas över om någon av dem saknas. Jag lade också till ett nytt e2e-test som prövar kanalvägen. I det loggar admin in i flik B i SAMMA kontext, och flik A ska ladda om utan att själv navigera, via BroadcastChannel("snajp-identitet").

De två andra fynden gäller filer utanför paketet: AppShell.tsx och OnboardingWizard.tsx (blockerande), samt ARCHITECTURE_INVARIANTS.md. Enligt granskarens förslag ska orkestreraren ändra dem, så jag har inte rört dem. Det blockerande fyndet stämmer mot koden: signOut returnerar nu { url }, och de två filerna använder fortfarande action={signOut}. Paketet kan alltså inte committas utan den ändringen.

E2e-testerna är inte körda. Jag har inte heller rört tempmapparna (se ej_gjort).

### Ändrade filer
- C:\Users\Anton L\snipe-leads\tests\e2e\kundresa.spec.ts

### Tester
- `python -m pytest -q tests/invariants/test_inv_sec_014.py` → 17 passed in 0.30s
- `python -m pytest -q tests/invariants/test_inv_copy_001.py` → 4 passed in 2.48s
- `tests/e2e/kundresa.spec.ts` → EJ KÖRD (kräver lokal stack; @playwright/test är inte installerat och tests/e2e ingår inte i tsconfig, så filen är inte heller typkontrollerad)

### Ej gjort
- Fynd 1 (blockerande) gäller components/AppShell.tsx (rad 25, 443, 509) och components/auth/OnboardingWizard.tsx (rad 9, 630, 709). Båda ligger utanför paketet, och enligt granskarens förslag ändrar orkestreraren dem i samma commit. Ändringen: importera loggaUtOchOppna från @/components/dashboard/DashboardContext och skriv action={loggaUtOchOppna}. Lägg sedan till båda filerna i parametriseringen av test_anroparna_oppnar_adressen_hart i tests/invariants/test_inv_sec_014.py och kör den scopade tsc igen. Jag har inte lagt till dem i parametriseringen själv, eftersom testet då skulle fällas tills filerna är ändrade.
- Fynd 2: ARCHITECTURE_INVARIANTS.md ligger utanför paketet, och docs/BESLUT.md skriver orkestreraren. Där behövs nya poster för INV-SEC-014 och INV-AUTH-002 och ett tillägg i INV-SEC-011. I BESLUT.md behövs tre rader: en inloggad icke-admin på /admin skickas till /dashboard i stället för 404, en anonym besökare på /admin skickas till /login, och in- och utloggning samt vybyte navigerar hårt och fungerar därför inte utan JavaScript.
- Inga e2e-tester körda (kräver lokal stack).
- Den vidarebefordrade begäran att ta bort tempmapparna har jag inte utfört. Det framgår inte vilka mappar som avses. En permanent radering kräver ett bekräftat mål, och den kan inte göras från det här byggsteget eftersom andra byggare arbetar samtidigt. Scratchpaden under Temp innehåller dessutom utredningsfilerna (fynd-adminlacka.md, fynd-bakat-felsida.md) och den tillfälliga tsconfig som orkestreraren behöver för den scopade typkontrollen. Huvudsessionen bör fråga Anton vilka mappar som avses.
- Ingen git add eller commit.

### Antaganden
- I kanaltestet tas kundens cookie bort med context.clearCookies() innan admin loggar in i flik B. Annars kan /login skicka flik B vidare som redan inloggad. Flik A får ingen händelse av att cookien tas bort, så omladdningen kan bara komma från meddelandet på kanalen.
- Kanaltestet börjar med att logga in kunden igen i flik A, eftersom det föregående testet lämnade adminens session i kontextet. Inloggningen postar på kanalen, men bara flik A är öppen då.
- Liksom det första tvåfliksfallet utgår det nya testet från att ett adminkonto utan tvåfaktor hamnar under /admin efter omladdningen.

### Syns i gränssnittet
- Inget nytt i den här rättningen: bara e2e-testet har ändrats.
- Det som fortfarande ska ses i en körande app är oförändrat från paketet: omdirigeringarna på /admin, inloggningen när man går bakåt efter utloggning, de hårda omladdningarna vid in- och utloggning och vybyte, och tvåfliksfallet med kund i flik A och admin i flik B.
