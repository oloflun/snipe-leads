# paket ruta-och-next

## Bygge
Jag har byggt paketet "ruta och Next-vägar" (planens del 1, 2, 3 och kundens del av 5). I Meny står nu "Hjälp och fel" i stället för mailto-raden "Anmäl felaktigt svar", men bara på den inloggade ytan i AppShell och inte i demoläget. Raden öppnar den nya HjalpRuta: ett ark intill sidomenyn på desktop (vänster 268px, 26rem brett) och i full höjd på mobil. Arket renderas genom en portal till document.body, eftersom mobilradens backdrop-blur annars hade stängt in det. Rutan har flikarna "Samtal" och "Mina ärenden (n)", där n bara syns när ett ärende väntar på kunden. Samtal är SupportChat i det nya läget hjalpMode, och historiken hämtas från servern. I samtalet finns kunskapskortet ("Lär agenten om oss", med "Lägg till i er kunskapsbas" eller "Spara som förslag" och därefter "Tillagd · Visa i Kunskapsbas") och felkortet ("Något är fel", med tre fält, valfri bild och en öppen rad om vad som skickas med; kvitteras med ärendenumret och läget Mottaget). Mina ärenden visar varje ärende med kundens ord för läget och händelserna med tid. Väntar ärendet på kunden finns ett svarsfält, eller knappen "Öppna testversionen" och frågan "Fungerade det?" med Ja och Nej plus kommentar. Ärenden som väntar fästs överst i Samtal och ger en prick på Meny. Listan pollas lugnt var 20:e sekund medan rutan är öppen och pausas när webbläsarfliken är dold. Sex sessionsgrindade Next-vägar under app/api/snajp-support/hjalp går under SNAJP_KEY_HJALP och bygger identiteten på servern i lib/snajp/hjalp.ts. Saknas nyckeln svarar de 503 med kod "hjalp_av" och en tvåspråkig text. Nya tester är ett node-test och INV-HJALP-001. Typkontrollen är ren för mina filer. Jag har inte sett något i bild, eftersom next dev inte fick startas. Förhandsvisningen ligger på /forhandsvisning/hjalpruta?lage=… och måste ses av orkestreraren.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\components\snajp\AgentMenu.tsx: ny prop hjalp. Med den ersätts mailto-blocket av "Hjälp och fel", som öppnar HjalpRuta. Meny-knappen får en ochre prick och sr-only-texten "Ett ärende väntar på dig", och knappen "Hjälp och fel" en siffra. Utan hjalp är beteendet som förut, så den publika chatten och AdminShell behåller mailto.
- C:\Users\Anton L\snipe-leads\components\snajp\SupportChat.tsx: nytt läge hjalpMode med props hjalpTomt, hjalpFast, hjalpKort, renderHjalpKort, hjalpStartFraga och hjalpVerktyg, samt en ny flödestyp "hjalp-kort". I hjalpMode går anropen mot /api/snajp-support/hjalp, hjalp/jobb/[id] och hjalp/samtal med kroppen {message, attachments}. Historiken hämtas alltid från servern, ingen sessionStorage. Chattens huvud och meny ritas inte, och 503 med kod hjalp_av ger en egen tvåspråkig bubbla. downscaleImage exporteras och HJALP_AV_TEXT är nytt. De fyra andra lägena är oförändrade: alla grenar är villkorade på hjalpMode.
- C:\Users\Anton L\snipe-leads\components\AppShell.tsx: bara monteringen. De två AgentMenu-instanserna (railen och mobilraden) får hjalp={signedIn && !demolage}.

### Nya filer
- C:\Users\Anton L\snipe-leads\components\snajp\HjalpRuta.tsx
- C:\Users\Anton L\snipe-leads\lib\snajp\hjalp.ts
- C:\Users\Anton L\snipe-leads\lib\snajp\hjalp.test.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\hjalp\route.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\hjalp\jobb\[jobId]\route.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\hjalp\samtal\route.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\hjalp\arenden\route.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\hjalp\arenden\[id]\svar\route.ts
- C:\Users\Anton L\snipe-leads\app\api\snajp-support\hjalp\arenden\[id]\utslag\route.ts
- C:\Users\Anton L\snipe-leads\app\forhandsvisning\hjalpruta\page.tsx
- C:\Users\Anton L\snipe-leads\tests\invariants\test_inv_hjalp_001.py

### Tester
- `node --test lib/snajp/hjalp.test.ts` → 11 av 11 gröna. Sista raden: "ℹ duration_ms 518.5442" (före den "ℹ pass 11" och "ℹ fail 0"). Efter de sista ändringarna kört igen: tests 11, pass 11, fail 0.
- `python -m pytest tests/invariants/test_inv_hjalp_001.py -q` → 22 passed in 0.45s
- `python -m pytest tests/invariants/test_inv_sec_010.py -q` → 33 passed, 6 skipped in 0.53s
- `python -m pytest tests/invariants/test_inv_copy_001.py tests/invariants/test_inv_ui_001.py -q` → 8 passed in 2.95s
- `python -m pytest tests/invariants/test_inv_sec_014.py -q` → 17 passed in 0.43s
- `python -m pytest tests/invariants/test_meta_invariants.py -q` → 3 passed in 0.38s
- `node node_modules/typescript/bin/tsc -p <scratchpad>/tsconfig.hjalp.json (tillfällig tsconfig utanför repot med bara de rörda och nya filerna)` → Mina filer är fria från fel. Två fel kvarstår, båda i components/AppShell.tsx rad 448 och 518 (TS2322 på <form action={signOut}>). De beror på en annan byggares ocommittade ändring i lib/actions/auth.ts, där signOut nu returnerar Promise<{ url: string }>, och inte på mina rader.

### Ej gjort
- Jag har inte sett något i bild. Uppdraget förbjöd next dev, och ingen server startades. Varje läge måste därför ses av orkestreraren, på desktop och mobil, innan något committas.
- Inget har committats eller lagts till i git (enligt uppdraget).
- INV-HJALP-001 är inte registrerad i ARCHITECTURE_INVARIANTS.md. Den filen ligger utanför mitt paket. Testet körs med pytest, men en post med 'Test:'-rad behövs om verify.yml bara kör registrerade invarianter.
- Inget nytt beslut är skrivet i docs/BESLUT.md, eftersom filen var förbjuden att röra. Beslut som bör in: mailto ligger kvar i den publika chatten och i adminytan, kund_workspace_id vid adminbesök (se antagandena) och läsrollens rätt att rapportera.
- AdminShell har inte fått Hjälprutan ("ändra inte adminytans beteende mer än nödvändigt"). Den behåller mailto.
- Sidans sökväg skickas inte med i chattfrågan. ChatRequest har inget fält för den, och att lägga den i subject hade ändrat hur agenten läser frågan. Sökvägen skickas bara med felrapporten.
- Agentens förslag om rätt kort ("Det låter som ett fel. Vill du anmäla det?") är inte byggt, eftersom det är backend och prompt. Rutan erbjuder korten själv: tre startval i tomt läge och två genvägar ovanför fältet när samtalet har innehåll.
- Den fasta AppShell-typfelen (signOut) har jag inte rättat, eftersom de ligger i en annan byggares fil.
- Ett avbrutet kort tar bort sitt innehåll men lämnar en tom plats i flödet (ett tomt div med space-y-luft). Tomt läge med startvalen kommer därför inte tillbaka efter en avbrytning. Felet är kosmetiskt.

### Antaganden
- Kontraktets vägar och former gäller som de är skrivna. GET /api/plattformsarenden?rapportor= returnerar {arenden}, POST returnerar 201 {id, nummer, status, created_at}, och svar och utslag returnerar ett helt Arende. Rutan hämtar om listan efter en ny rapport, eftersom POST-svaret inte är ett helt Arende.
- Identiteten vid adminbesök (vy "kund"): rapportören är adminen själv och kund_tenant_slug den besökta kundens slug. kund_workspace_id är adminens EGEN arbetsyta, eftersom den besökta kundens arbetsyte-id inte finns i sessionen utan en ny databasfråga. besok_av_admin=true bär besöket.
- Fältet vy får värdena "egen" (kundens egen yta), "admin" (plattformsadmin i adminvyn), "demo" eller "kund" (adminbesök). aktivVy() ger "admin" som standard för alla, och det hade varit missvisande för en vanlig kund.
- rapportor_namn tas ur profiles.full_name, och annars ur sessionens namn.
- Läsrollen får skapa felrapporter, svara och lämna utslag. Kunskapskortet visas för den med knapparna avstängda och en förklaring. Servern spärrar dessutom skrivningen i proxyAsTenant.
- "Lägg till i er kunskapsbas" går till POST /api/snajp-support/kb {articles:[{title, content}]} genom catch-all, alltså kundens egen nyckel. "Spara som förslag" går till POST /api/snajp-support/kb/forslag {title, content, category:null, kalla:"chatt"}. Den backendvägen byggs av ett annat paket.
- Rollen i "Det här skickas med" visas som "Läsbehörighet" eller "Ägare eller medlem". Klienten känner bara arLasare, och servern sätter den exakta rollen.
- Bilden i felrapporten och chatten skalas ned med samma downscaleImage som chattens bilagor (1024px). Servern godtar bara data:image/(png|jpeg|webp|gif);base64 upp till 2 000 000 tecken och annars null. Varje id i en sökväg prövas som uuid och ger annars 404.
- "Öppna testversionen" visas bara för en https-adress och öppnas med target=_blank och rel=noopener noreferrer.
- Kundens ord för stängd är "Stängd" enligt kontraktet, och förklaringen visas som händelsens meddelande.
- Hjälpen saknas i demoläget (/demo) och i den publika chatten: den kräver en riktig session.
- Status som väntar på kunden räknas som vantar_pa_kund, eller som status behover_mer eller redo_att_testa, så pricken visas även om fältet skulle saknas.

### Syns i gränssnittet
- Förhandsvisningen (ingen databas, ingen inloggning, anropen besvaras i webbläsaren) ligger på /forhandsvisning/hjalpruta. Lägena nås med ?lage=tomt, ?lage=fraga, ?lage=kunskap, ?lage=lasroll, ?lage=fel, ?lage=kvitto, ?lage=arenden och ?lage=av, till exempel http://localhost:3000/forhandsvisning/hjalpruta?lage=arenden. Varje läge ska ses på desktop (minst 1280 bred, arket intill en kuliss av sidomenyn) och på mobil (375 bred, arket i full höjd).
- ?lage=tomt visar tomt samtal med raden om vad rutan gör och de tre startvalen "Fråga om Snajp", "Lär agenten om oss" och "Något är fel".
- ?lage=fraga visar en pågående fråga med fasvisningen "Söker efter svaret" (jobbet blir aldrig klart i förhandsvisningen).
- ?lage=kunskap visar kunskapskortet med rubrik och text att ändra och knapparna "Lägg till i er kunskapsbas" och "Spara som förslag". Ett klick ger "Tillagd · Visa i Kunskapsbas".
- ?lage=lasroll visar samma kort med knapparna avstängda och förklaringen om läsbehörighet.
- ?lage=fel visar felkortet: tre fält, "Bifoga bild" och "Det här skickas med" (sidan, tiden, rollen). "Skicka" ger kvittot F-0047.
- ?lage=kvitto visar det kvitterade ärendet F-0047 med märket Mottaget och knappen "Visa i Mina ärenden".
- ?lage=arenden visar Mina ärenden med sex ärenden: redo_att_testa (med "Öppna testversionen" och "Fungerade det?"), behover_mer (med svarsfält), mottagen, undersoks, i_main och stangd med förklaring. Fliken visar siffran 2, och prickarna syns på Meny i kulissen.
- ?lage=av visar läget när hjälpen inte är påslagen (503): den tvåspråkiga texten i stället för samtal och lista.
- Två saker bör kontrolleras särskilt. Om samtalet har innehåll ska genvägschippen "Lär agenten om oss" och "Något är fel" stå ovanför fältet. I läget fraga och efter ett kort ska ärenden som väntar stå fästa överst i Samtal, och samtalet ska inte tappas när man byter flik och tillbaka.
- Utanför förhandsvisningen: i appens riktiga skal (inloggad) ska Meny-panelen i railens fot och i mobilraden visa sektionen "Behöver du hjälp?" med knappen "Hjälp och fel" i stället för "Svarade agenten fel?". Arket ska ligga över sidinnehållet intill railen, inte under mobilradens blur.

## Granskning: godkänd=True
- [bor_rattas] lib/snajp/hjalp.ts:207-219 När en admin besöker en kund (vy "kund") sätts kund_workspace_id till adminens egen arbetsyta, medan kund_tenant_slug är den besökta kundens. Paret pekar då på två olika kunder. Planen del 7 bygger testversionen med bara "den kundens arbetsyta". Om det paketet läser kund_workspace_id kopieras Snajps egen arbetsyta i stället för kundens. Byggaren har själv flaggat detta som ett antagande. FÖRSLAG: Slå upp den besökta kundens arbetsyte-id på servern ur sluggen (samma uppslag som proxyAsTenant gör för kundbesöket). Om det inte går: skicka null eller ett tydligt fält och låt backenden avgöra arbetsytan ur kund_tenant_slug. Beslutet skrivs i docs/BESLUT.md, och orkestreraren ser till att backend- och testversionspaketen läser rätt fält.
- [bor_rattas] components/snajp/HjalpRuta.tsx:902-910, 529 Ett avbrutet kort tas bort ur HjalpRutas kort-map, eller blir steg "avbruten", men dess id ligger kvar i kortIds och i SupportChats flöde. Kvar blir ett tomt <div> med space-y-luft. Tomt läge med de tre startvalen kommer inte tillbaka, eftersom messages.length > 0. Byggaren har noterat felet som kosmetiskt. FÖRSLAG: Ta bort id:t ur kortIds vid avbrytning. SupportChat bör också rensa ett hjalp-kort-id som inte längre finns i hjalpKort, alltså filtrera bort platser vars id saknas i propen.
- [bor_rattas] components/snajp/HjalpRuta.tsx:865-1071 Kortens tillstånd, till exempel ett halvifyllt felkort med bild, bor i HjalpRuta och försvinner när rutan stängs. AgentMenu avmonterar nämligen HjalpRuta när den stängs. Kunden som stänger rutan för att titta på sidan och sedan öppnar den igen har tappat sin rapport. FÖRSLAG: Lyft kort och kortIds till AgentMenu eller till den modulnivåbutik som redan används för ärendena. Ett alternativ är att dölja rutan i stället för att avmontera den medan ett kort är ofärdigt.
- [notering] app/api/snajp-support/hjalp/jobb/[jobId]/route.ts:13-20 Pollningen kontrollerar bara att jobbet tillhör hjälpens tenant, inte att det tillhör den inloggade. En inloggad användare som känner ett annat hjälpjobbs uuid kan läsa svaret på någon annans fråga. Risken är låg eftersom uuid inte går att gissa, men gränsen mellan rapportörer i hjälpens tenant vilar på det. FÖRSLAG: Spara jobbets ägare (customer_email) i jobbet och jämför i backenden. Ett alternativ är att Next-vägen skickar med hjalpAvsandare(userId) och att backenden avvisar ett jobb vars ägare inte matchar.
- [notering] components/snajp/HjalpRuta.tsx:99-152 Ärendelistan ligger i en butik på modulnivå som aldrig töms när användaren byts. Om utloggning och ny inloggning sker utan full omladdning kan nästa användare kort se den förras ärenden, tills nästa hämtning efter FARSK_MS (30 s). FÖRSLAG: Kontrollera att utloggningen gör en full omladdning (signOut returnerar nu {url}). Annars ska glomHjalpArenden() anropas vid utloggning, eller butiken nycklas på användar-id.
- [notering] components/snajp/HjalpRuta.tsx:347-504 Uppgiften säger att rutan ska visa "det befintliga kunskapsbaskortet". Byggaren har skrivit ett nytt redigerbart KunskapKort i samma visuella stil (samma klasser som KbForhandsvisningKortVy) i stället för att återanvända komponenten. Det befintliga kortet är inte redigerbart, så valet är rimligt, men det är en avvikelse. FÖRSLAG: Godta valet, eller bryt ut gemensam markup så att de två korten inte glider isär. Bedöms i bild.
- [notering] components/snajp/HjalpRuta.tsx:936-942 Rutan har aria-modal="false" men täcker hela skärmen på mobil (fixed inset-0). Fokus kan då tabba ut till sidan bakom. Flikarna saknar aria-controls, och det finns bara en tabpanel. FÖRSLAG: Låt aria-modal vara sant och lägg en fokusfälla under lg, eller använd inert på sidan bakom. Koppla tab och tabpanel med id och aria-controls.
- [notering] (utanför paketet): Saker som inte kunde göras inom paketet: INV-HJALP-001 är inte registrerad i ARCHITECTURE_INVARIANTS.md, besluten saknas i docs/BESLUT.md, och AppShell har typfel TS2322 på <form action={signOut}>. Typfelet beror på en annan byggares ändring i lib/actions/auth.ts, där signOut nu returnerar Promise<{url}>. Jag har bekräftat det i diffen. FÖRSLAG: Orkestreraren registrerar invarianten och skriver besluten. Den som äger lib/actions/auth.ts rättar formens action.
- [notering] app/forhandsvisning/hjalpruta/page.tsx: Inget är sett i bild. Rutans placering (lg:left-[268px], 26rem bred) mot den riktiga railen kan inte avgöras ur koden. Samma gäller arket ovanför mobilradens blur via portal, pricken på Meny och genvägarna. FÖRSLAG: Orkestreraren ser /forhandsvisning/hjalpruta?lage=tomt|fraga|kunskap|lasroll|fel|kvitto|arenden|av på desktop (minst 1280 px) och mobil (375 px), och dessutom det riktiga skalet inloggat via lokal_stack, innan något committas.

### Granskarens tester
- `node --test lib/snajp/hjalp.test.ts` → tests 11, pass 11, fail 0. Sista raden: ℹ duration_ms 496.3145
- `python -m pytest tests/invariants/test_inv_hjalp_001.py -q` → 22 passed in 0.37s
- `python -m pytest tests/invariants/test_inv_sec_010.py -q` → 33 passed, 6 skipped in 0.46s
- `python -m pytest tests/invariants/test_inv_copy_001.py -q` → 4 passed in 2.40s

## Rättning
Jag har prövat alla tre fynden mot koden. Alla stämde och alla är rättade i paketets filer. (1) lib/snajp/hjalp.ts: vid ett adminbesök och i demovyn slås den besökta kundens arbetsyte-id nu upp ur sluggen med `select id from public.workspaces where slug = $1` via sqlAsUser. kund_workspace_id och kund_tenant_slug pekar då på samma kund. Fyndet föreslog att återanvända uppslaget i proxyAsTenant, men något sådant finns inte: lib/snajp/tenant.ts sätter också workspaceId till adminens egen arbetsyta vid besök. Uppslaget är därför nytt. Om raden inte syns för adminens RLS-roll (lib/data/dashboard.ts säger att det ofta händer), eller om kunden saknar arbetsyta (nordlys-handel), ligger adminens egen arbetsyta kvar. Kontraktet och backendens schema (schemas.py:890, krävt, min_length 32) kräver ett uuid, så null går inte att skicka. (2) Ett avbrutet kort tas nu bort helt: både innehållet och platsen i kortlistan. SupportChat tar i hjalpMode bort de hjalp-kort-platser vars id inte längre finns i propen hjalpKort. Ingen tom plats blir kvar, och tomt läge med de tre startvalen kommer tillbaka när flödet är tomt. (3) Korten (ids och innehåll) ligger nu i en butik på modulnivå i HjalpRuta.tsx, i samma mönster som ärendebutiken. Ett halvifyllt felkort med bild finns kvar när rutan stängs och öppnas igen. Förhandsvisningen (med `start`) har kvar ett eget tillstånd per läge, så lägena inte läcker in i varandra. Alla rörda testfiler är gröna. Typkontrollen visar bara de två fel i AppShell som fanns sedan tidigare.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\lib\snajp\hjalp.ts: nytt import av hasDatabase och sqlAsUser från @/lib/db. Ny privat funktion besoktArbetsyta(userId, slug) slår upp workspaces.id ur sluggen och ger null vid fel, vid ett id som inte är ett uuid och när databasen saknas. hjalpIdentitet använder den när vyn inte är "admin" (alltså kund och demo) och faller annars tillbaka på context.workspace.id. Dokumentationen är uppdaterad.
- C:\Users\Anton L\snipe-leads\lib\snajp\hjalp.test.ts: en stubbe för @/lib/db. Identitetstestet prövar nu att besöket ger den besöktas arbetsyta och att frågan görs på sluggen. Det prövar också att adminens arbetsyta står kvar när raden inte syns.
- C:\Users\Anton L\snipe-leads\components\snajp\HjalpRuta.tsx: ny butik för korten på modulnivå (KortButik, prenumereraKort, sattKortButik, utanKort) och kroken useHjalpKort(start). Utan start används den delade butiken, med start ett eget tillstånd. HjalpRuta använder kroken i stället för två useState. andraKort tar bort kortet helt, alltså både id och innehåll, när det avbryts (null eller felkortets steg "avbruten").
- C:\Users\Anton L\snipe-leads\components\snajp\SupportChat.tsx: bara effekten för hjalp-kort, som också är villkorad på hjalpMode. Den filtrerar nu bort hjalp-kort-platser vars id saknas i hjalpKort och lägger till nya sist. Ingen annan rad och inget annat läge är ändrat.

### Tester
- `node --test lib/snajp/hjalp.test.ts` → tests 11, pass 11, fail 0. Sista raden: "ℹ duration_ms 491.4462"
- `python -m pytest tests/invariants/test_inv_hjalp_001.py -q` → 22 passed in 0.34s
- `python -m pytest tests/invariants/test_inv_copy_001.py -q` → 4 passed in 2.29s
- `python -m pytest tests/invariants/test_inv_sec_010.py -q` → 33 passed, 6 skipped in 0.39s
- `python -m pytest tests/invariants/test_inv_sec_014.py -q` → 17 passed in 0.36s
- `python -m pytest tests/invariants/test_inv_ui_001.py -q` → 4 passed in 1.03s
- `node node_modules/typescript/bin/tsc -p C:\Users\ANTONL~1\AppData\Local\Temp\claude\20bc186535c3c092\fd9b0b93-e92d-4cea-a78c-7ea782ace803\scratchpad\tsconfig.hjalp.json (tillfällig tsconfig utanför repot med HjalpRuta, SupportChat, AgentMenu, hjalp.ts, förhandsvisningen och arenden-vägen)` → Mina filer är fria från fel. Bara de två fel som fanns sedan tidigare återstår, i components/AppShell.tsx rad 448 och 518: TS2322 eftersom signOut returnerar Promise<{ url: string }>. Det kommer från en annan byggares ändring i lib/actions/auth.ts. Exit 1 enbart av dem.

### Ej gjort
- Fynd 1, delvis: fyndet föreslog att använda "samma uppslag som proxyAsTenant gör för kundbesöket", men det uppslaget finns inte. lib/snajp/tenant.ts rad 290 sätter också workspaceId: workspace.id, alltså adminens. Jag lade därför till ett eget uppslag ur sluggen. Det är inte helt pålitligt, eftersom workspaces-raden ofta är osynlig för adminens RLS-roll (enligt kommentaren i lib/data/dashboard.ts rad 227). Då står adminens arbetsyta kvar, eftersom kontraktet och backendens schema kräver ett uuid. En helt pålitlig väg kräver något utanför mitt paket. Det kan vara en security definer-funktion i en migration som ger den besöktas arbetsyte-id efter samma admingrind som tenant_api_key_for_admin. Det kan också vara att backenden (och testversionspaketet i planens del 7) avgör arbetsytan ur kund_tenant_slug när besok_av_admin är sant. Orkestreraren bör se till att testversionspaketet läser kund_tenant_slug vid besök. Beslutet ska skrivas i docs/BESLUT.md, som jag inte får röra.
- Butiken för korten töms inte vid utloggning. Ärendebutiken har samma egenskap sedan tidigare. Ett halvifyllt kort finns alltså kvar i minnet tills sidan laddas om. Utloggningen (lib/actions/auth.ts, components/auth/SignOutButton.tsx) ligger utanför mitt paket och ändras av en annan byggare. Rättningen vore att anropa en tömning (glomHjalpArenden plus korten) där.
- Svarsfältet i Mina ärenden (ArendeKort: svarText och kommentar) är fortfarande lokalt tillstånd och tappas när rutan stängs. Fyndet gällde korten i samtalet, så jag lät det vara.
- Inget i bild. Ingen server startades, enligt uppdraget. Ändringen av hur avbrytning och återöppning beter sig måste ses av orkestreraren.
- Ingen commit, ingen git add (enligt uppdraget).

### Antaganden
- Uppslaget av den besöktas arbetsyta körs bara när vyn inte är "admin". aktivVy() ger "kund" eller "demo" först efter getPlatformAdmin(), så en vanlig kund kan inte styra uppslaget med vy-cookien.
- Demovyn (nordlys-handel) har ingen arbetsyta. Den faller därför alltid tillbaka på adminens egen arbetsyta, och kund_tenant_slug bär kunden.
- Sidan i felkortet läses fortfarande när kortet monteras. Om kunden byter sida medan rutan är stängd och öppnar igen visar och skickar kortet den nya sidan. Det står öppet under "Det här skickas med", så kunden ser vad som skickas.
- Felkortets steg "avbruten" behandlas nu som borttagning. Typen står kvar oförändrad, och FelKort returnerar fortfarande null för den om steget skulle förekomma.

### Syns i gränssnittet
- Förhandsvisningen: http://localhost:3000/forhandsvisning/hjalpruta?lage=kunskap och ?lage=fel. Välj "Avbryt" på kortet. Kortet ska försvinna helt, utan tom luft, och tomt läge med de tre startvalen ("Fråga om Snajp", "Lär agenten om oss", "Något är fel") ska komma tillbaka. Se det på desktop (1280) och mobil (375).
- Butiken på modulnivå prövas genom Meny-knappen i kulissen, inte genom den fasta rutan i förhandsvisningen, som har eget tillstånd per läge. Gå till http://localhost:3000/forhandsvisning/hjalpruta?lage=tomt och öppna Meny, sedan "Hjälp och fel" (den riktiga AgentMenu-instansen utan start). Välj "Något är fel", fyll ett fält och bifoga en bild. Stäng rutan med krysset eller Escape och öppna den igen. Kortet ska stå kvar med text och bild. Avbryt det sedan och kontrollera att tomt läge kommer tillbaka.
- Inget nytt utseende i övrigt. Lägena tomt, fraga, kunskap, lasroll, fel, kvitto, arenden och av ska se ut som förut.
