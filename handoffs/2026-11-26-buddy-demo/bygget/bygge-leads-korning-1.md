# paket leads-korning-1

## Bygge
Del 1 av paketet leads-körning är klar. Alla nya tester skrevs först och fällde dagens kod, och efter rättningen går alla rörda testfiler gröna. A. Provkörningar skapar inga ringprospekt längre. Ringbolagen skrivs till listan "Ringlista, Iris <datum>" under Listor genom samma hjälpfunktion som "Ej kvalificerade". Listan får körningens is_test, varje rad går genom ett uttryckligt fältfilter och antal anställda och omsättning ligger i extra. Skarpa körningar skapar origin 'ring'-prospekt som förut, i en enda gren. listvy.synliga döljer obedömda prospekt med origin test/ring som saknar niva, score_total, icp_fit och mejl. weekly_analytics räknar inte origin 'ring' som nya leads. sammanfatta säger "i ringlistan under Listor" i provkörningar. B. Taket och rundtaket förlängs under målet i stället för att avsluta. Formeln är återstående behov × TAK_FAKTOR, rundtaket förlängs med max_rundor(behov), och varje förlängning loggas som platform_event "Körningens tak/rundtak förlängdes under målet". Det enda målgruppsslutet är nu TOMMA_RUNDOR. Kredittaket och fallen sökning är oförändrade. Varje sökrunda hämtar alltid MAX_PER_RUNDA. Fortsätt nollar rundor, rundor_tak, sokfel och dubblettrundor. Flaskhalsen räknar inte steg register/jev, och kredittak namnges "Sidtaket". C. Städaren fäller inte en batchrad med klar=false, kalla≠lista och pagaende=0. En rad som ändå fälls får error=HANGFEL_JOBB i liggaren. Väckaren läser status=processing (limit 500) i stället för de tio senaste, och run_leads_stadare väcker före städningen.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\leads.py (_SLUTFALT, _fortsatt_korning rundor=0, _sla_in_sokrunda använder _rundtak, nya _rundtak/_forlang_tak, _fyll_pa_last takförlängning, _RINGLISTFALT/_ringlistrad/_skriv_sparlista, _spara_listspar, vack_stillastaende_korningar)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\korning.py (docstrings, sokrunda antal=MAX_PER_RUNDA, TAKSLUT, avsluta flaskhals, sammanfatta ringtext)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\listvy.py (FORDELNINGSKOLUMNER + score_total/icp_fit, _obedomt_ringbolag i synliga)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\samtal.py (bara docstring)
- C:\Users\Anton L\snipe-leads\snajp-support\app\jobs\stadare.py (docstring, väck före städning)
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\postgres.py (stada_hangande_leadsjobb: undantag + error; weekly_analytics utan 'ring')
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\memory.py (samma två ändringar)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_fordelning.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_listvy.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_upptagna_bolag.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_leads_n_001.py (test_slut_pa_kandidater_namnger_flaskhalsen omskriven, test_taket_hindrar_en_skenande_korning ersatt av test_taket_ar_ett_larm_inte_ett_slut, nya test_en_snal_pool_fortsatter_forbi_rundtaket och test_flaskhalsen_raknar_inte_registrets_gratisbortval)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_korning_fortsatter_till_malet.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_job_003.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\api\test_analytics_weekly.py

### Tester
- `python -m pytest tests/leads/test_fordelning.py -q (i snajp-support; före rättningen fällde test_provkorningens_ringlista_blir_en_lista_inte_prospekt)` → 25 passed in 15.70s
- `python -m pytest tests/invariants/test_inv_leads_n_001.py -q (före: 4 failed)` → 8 passed in 16.02s
- `python -m pytest tests/invariants/test_inv_job_003.py -q (före: 3 failed)` → 11 passed in 12.06s
- `python -m pytest tests/invariants/test_korning_fortsatter_till_malet.py -q (före: 1 failed)` → 9 passed in 15.06s
- `python -m pytest tests/leads/test_listvy.py -q (före: 1 failed)` → 9 passed in 34.56s
- `python -m pytest tests/leads/test_upptagna_bolag.py -q` → 13 passed in 19.11s
- `python -m pytest tests/api/test_analytics_weekly.py -q (före: 1 failed)` → 6 passed in 1.95s
- `python -m pytest tests/leads/test_stadare.py -q` → 10 passed in 17.76s
- `python -m pytest tests/test_korning_styrning.py -q` → 15 passed in 16.61s
- `python -m pytest tests/leads/test_korning_hittar_bolag.py -q` → 9 passed in 1.67s
- `python -m pytest tests/leads/test_sidhamtning.py -q` → 11 passed in 14.35s
- `python -m pytest tests/api/test_korning_leverera_bestallt.py -q` → 8 passed in 18.04s
- `python -m pytest tests/api/test_korningar.py -q` → 2 passed in 17.67s
- `python -m pytest tests/invariants/test_inv_store_001.py -q` → 705 passed in 15.31s
- `python -m pytest tests/test_synkvakt.py -q` → 14 passed in 42.26s
- `python -m pytest tests/agent/test_arbetsyta_siffror.py -q` → 4 passed in 58.65s
- `python -m pytest tests/leads/test_existens.py -q` → 13 passed in 47.43s
- `python -m pytest tests/test_evalsviter.py -q` → 30 passed in 12.83s
- `python -m app.leads.korning (demo)` → korning: ok

### Ej gjort
- Tempmapparna är inte borttagna. Användarens rad 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses, och permanent radering kräver ett uttryckligt besked om vad som ska bort. Scratchpaden innehöll dessutom utredningsfilerna som uppgiften krävde. Orkestreraren eller Anton får avgöra vilka mappar och radera dem.
- ARCHITECTURE_INVARIANTS.md är inte ändrad (filen ligger utanför paketet). INV-LEADS-N-001 (rad 904-910) säger fortfarande att körningen slutar när 'poolen, taket (4×N undersökta) eller dygnsbudgeten tar slut'. Föreslagen text: körningen fyller på tills målet är nått, målgruppen är tom (TOMMA_RUNDOR efter breddningen), kredittaket är nått eller sökningen föll; taket (TAK_FAKTOR×N) och rundtaket förlängs under målet och loggas som platform_event. INV-JOB-003 bör få en mening om att städaren skriver HANGFEL_JOBB som error i liggaren och aldrig fäller en väckbar körning (klar=false, inget listjobb, pagaende=0). Testerna är redan ändrade.
- base.py (protokollet) har inte rörts. Därför fick list_leads_korningar ingen scope-parameter (INV-STORE-001 kräver identisk signatur). Väckaren läser status='processing' med limit=500 och filtrerar scope='batch' i Python.
- Frontend är inte ändrad (utanför paketet). IrisKorningar.tsx SLUT_ETIKETT['tak'] säger fortfarande 'fyra gånger så många', fast slutet 'tak' inte längre uppstår. Listvyn för leadslistor visar troligen inte extra.anstallda, och regel 15 ('antal anställda visas alltid') kräver en tvåspråkig kolumn i den befintliga listtabellen. Jag har inte kontrollerat det i vyn.
- docs/BESLUT.md och CLAUDE.md (regel 15/17: provkörningens ringlista ligger under Listor; taken är larm) är inte uppdaterade. Orkestreraren skriver dem.
- Skarpa körningar skapar fortfarande ringprospekt med origin 'ring'. Det väntar på Antons beslut om Samtal › Ringlista, enligt uppdraget.
- Kredittak och sokningen_foll avslutar som förut. Att göra dem vilande hör till del 2.
- De 36 befintliga demoraderna är inte rörda i databasen (ingen databas får röras). Skyddet i listvy.synliga döljer dem i leadslistan och nyckeltalet.
- Postgres-SQL:en i stada_hangande_leadsjobb och weekly_analytics är inte körd mot en riktig databas, bara speglad och testad i MemoryStorage.
- Ingen TypeScript rördes, så ingen tsc-kontroll kördes.

### Antaganden
- Rundstorlek: 'räkna behov som mal − levererade − pagaende och krymp inte under MAX_PER_RUNDA' ger matematiskt alltid MAX_PER_RUNDA, eftersom formeln min(8, …) aldrig överstiger 8. Därför blev antal=MAX_PER_RUNDA. Att registret är slut syns först som tomma rundor. Följden är att små beställningar (mal 1) hämtar 8 kandidater per runda i stället för 3, vilket ger något högre sidkostnad per runda.
- Städarens undantag gäller bara körningar som väckaren faktiskt väcker: scope batch, korning är ett objekt, klar≠true, kalla≠'lista' och pagaende=0. En körning med pagaende>0 vars barn dött städas som förut, annars hade den hängt för evigt eftersom väckaren hoppar över den.
- Förlängningen av taket: tak = undersokta + pagaende + (mal − levererade) × TAK_FAKTOR. Rundtaket: rundor_tak = rundor + max_rundor(mal − levererade). Det nya fältet korning['rundor_tak'] lagras i liggarens jsonb, så ingen migration behövs. Platform_event loggas med level 'info' och source 'leads'.
- Fortsätt sätter rundor=0. Geo-ringen börjar då om från första ringen, men tratten utesluter redan prövade bolag.
- Flaskhals vid kredittak blir 'Sidtaket' (sammanfattningen: 'Det som strypte mest: sidtaket.'). 'tak' mappas till 'Taket' men uppstår inte längre som slut.
- Körningens sammanfattning är en svensk backendsträng som IrisKorningar visar som den är, utan lokalisering. Den nya texten är därför bara svensk, som resten av meningen.
- Fel som redan står på en rad skrivs inte över av städaren (coalesce/nullif).
- Skyddet i synliga gäller origin 'test' och 'ring', men 'ring' filtrerades redan bort helt, så i praktiken verkar det på 'test'. Iris-prospekt under research har alltid contact_email och syns därför.

### Syns i gränssnittet
- Leadslistan och nyckeltalet 'Leads i listan' (och munkdiagrammet/fördelningen) tappar obedömda provkörningsbolag med origin 'test' utan mejl. Demokontots 44 bör bli 8.
- Under Listor (och i Leads-översiktens Listor-panel) dyker en ny lista 'Ringlista, Iris <datum>' upp efter varje provkörning med ringbolag. Raderna har VD, telefon, signal 'ring' och antal anställda i extra. Kontrollera om listtabellen visar antal anställda.
- Iris › Körningar: provkörningens sammanfattning säger 'N i ringlistan under Listor' i stället för 'N till ringlistan'. Vid kredittak står 'Det som strypte mest: sidtaket.', och registrets 'för stort' namnges inte längre som strypare.
- Körningar som tidigare slutade 'Klar, under målet' på tak eller max_rundor fortsätter nu (status Pågår längre). Fortsätt på en körning som stannat vid rundtaket når målet.
- En tyst körning visas inte längre som 'Misslyckades' + 'Letar fler bolag'. Den väcks i stället, och en körning som ändå fälls visar städarens felmening (HANGFEL_JOBB) i statuscellen.
- Analys/arbetsytans 'nya leads' räknar inte längre ringprospekt (origin 'ring').

## Granskning: godkänd=True
- [bor_rattas] ARCHITECTURE_INVARIANTS.md:904-910 INV-LEADS-N-001 säger fortfarande att körningen slutar när 'poolen, taket (4×N undersökta) eller dygnsbudgeten tar slut'. Beteendet är nu ändrat: taken förlängs och TOMMA_RUNDOR är det enda målgruppsslutet. INV-JOB-003 nämner inte heller att städaren nu skriver HANGFEL_JOBB i liggaren och undantar väckbara körningar. Uppgiften kräver att invariantens text ändras i samma arbete som testerna. Testerna är ändrade, texten är det inte. Filen ligger utanför paketet, och byggaren har redovisat det. FÖRSLAG: Orkestreraren skriver om INV-LEADS-N-001 enligt byggarens förslag i ej_gjort och lägger till en mening i INV-JOB-003 i samma commit som paketet.
- [bor_rattas] snajp-support/app/storage/postgres.py:3698-3709 (memory.py 2685-2703) Undantaget i stada_hangande_leadsjobb saknar en yttersta gräns. En batchrad med klar≠true, kalla≠lista och pagaende=0 fälls aldrig, oavsett hur länge den varit tyst. Om väckaren inte kan driva den, ligger den kvar som 'Pågår' för alltid. Det kan hända om _las_korning läser en inaktuell Redis-post med klar=True eller pagaende>0, så att _fyll_pa_last returnerar utan att spara. Förut fälldes en sådan rad efter 60 minuter, låt vara utan felorsak. Samma gäller en rad i status 'queued' som bär ett korning-objekt: väckaren läser bara 'processing', och städaren undantar den ändå. FÖRSLAG: Begränsa undantaget till status 'processing' och lägg till en reservgräns, till exempel updated_at äldre än 24 h. Då fälls också en väckbar rad, med error=HANGFEL_JOBB. Testa båda fallen i test_inv_job_003.py.
- [notering] snajp-support/app/storage/postgres.py:3679-3718, 3958-3962 Postgres-SQL:en (städarens nya villkor och error-kolumnen med $4, weekly_analytics) är inte körd mot en databas, bara speglad i MemoryStorage. Logiken stämmer vid läsning: coalesce för null-scope och korning, pagaende som '0' i jsonb och nullif(error,''). FÖRSLAG: Kör en torrkörning mot lokal_stack innan push, om stacken finns.
- [notering] snajp-support/app/leads/korning.py:145-149 antal = MAX_PER_RUNDA i varje runda. Byggarens skäl håller: formeln i uppdraget ger alltid 8. Men små beställningar (mal 1-2) köper nu kontaktsökning för 8 kandidater per runda i stället för 3-4. Kostnaden begränsas fortfarande av kredittaket, och nu när taken förlängs är kredittaket det enda kostnadsskyddet utöver TOMMA_RUNDOR. FÖRSLAG: Inget krav i del 1. Nämn kostnadsökningen för Anton, tillsammans med del 2 (vilande körningar och kredittak).
- [notering] components/leads/IrisKorningar.tsx:99 SLUT_ETIKETT 'tak' ('fyra gånger så många' enligt byggaren) uppstår inte längre som slut. Det är oklart om listvyn för en leadslista visar extra.anstallda, vilket regel 15 kräver ('antal anställda visas alltid') nu när provkörningens ringbolag är listrader. Filen ligger utanför paketet. FÖRSLAG: Orkestreraren kontrollerar listtabellen i bild, desktop och mobil, och lägger vid behov till en tvåspråkig kolumn i den befintliga tabellen.
- [notering] snajp-support/app/leads/korning.py:339-345 Sammanfattningens nya text 'i ringlistan under Listor' är bara svensk. Det följer det befintliga mönstret, eftersom hela meningen är en svensk backendsträng som IrisKorningar visar som den är, och INV-COPY-001 skannar bara .tsx. Engelska användare ser dock svensk text. FÖRSLAG: Ingen ändring i det här paketet. Lokaliseringen av sammanfattningen är en egen uppgift.
- [notering] snajp-support/tests/: Utredningens invarianttest för en hel körning (högst mal prospekt med körningens origin, och vart och ett med ett researchjobb) saknas. Byggarens uppdrag listade det inte, och test_fordelning och test_upptagna_bolag täcker _spara_listspar direkt. FÖRSLAG: Valfritt: lägg till det tillsammans med del 2.

### Utanför paketet
- snajp-support/app/api/leads.py, hunken i _starta_batch (require_egen_produkt, 422 för research_and_draft): den hör till paketet utkast-onboarding och inte till byggaren av leads-korning-1.
- snajp-support/tests/api/test_kb_seedning.py är ändrad i arbetskatalogen. Den hör till ett annat paket.
- ARCHITECTURE_INVARIANTS.md (INV-LEADS-N-001, INV-JOB-003) behöver ny text. Orkestreraren skriver den.
- components/leads/IrisKorningar.tsx (SLUT_ETIKETT 'tak') och listtabellens visning av extra.anstallda (regel 15) behöver kontrolleras i bild.
- docs/BESLUT.md och CLAUDE.md regel 15/17 (provkörningens ringlista ligger under Listor, taken är larm). Orkestreraren skriver dem.
- Den vidarebefordrade raden 'Ta bort tempmapparna helt, gör det nu' har jag inte utfört. Jag är granskare och ändrar inga filer, och raden säger inte vilka mappar som avses. Permanent radering kräver att Anton bekräftar exakt vad som ska bort. Scratchpaden innehåller dessutom utredningsfilerna som de andra byggarna läser.

### Granskarens tester
- `cd snajp-support && python -m pytest tests/leads/test_fordelning.py -q -p no:cacheprovider` → 25 passed in 14.12s
- `cd snajp-support && python -m pytest tests/leads/test_listvy.py -q -p no:cacheprovider` → 9 passed in 35.58s
- `cd snajp-support && python -m pytest tests/leads/test_upptagna_bolag.py -q -p no:cacheprovider` → 13 passed in 17.39s
- `cd snajp-support && python -m pytest tests/invariants/test_inv_leads_n_001.py -q -p no:cacheprovider` → 8 passed in 14.60s
- `cd snajp-support && python -m pytest tests/invariants/test_korning_fortsatter_till_malet.py -q -p no:cacheprovider` → 9 passed in 14.62s
- `cd snajp-support && python -m pytest tests/invariants/test_inv_job_003.py -q -p no:cacheprovider` → 11 passed in 13.96s
- `cd snajp-support && python -m pytest tests/api/test_analytics_weekly.py -q -p no:cacheprovider` → 6 passed in 2.04s
- `cd snajp-support && python -m pytest tests/leads/test_stadare.py -q -p no:cacheprovider` → 10 passed in 17.72s

## Rättning
Granskarens fynd 2 (städarens undantag saknade en yttersta gräns) stämde mot koden och är rättat. Fynd 1 (ARCHITECTURE_INVARIANTS.md) ligger utanför paketet och lämnas till orkestreraren. Två nya tester skrevs först och fällde dagens kod (2 failed, 11 passed). Därefter rättades stada_hangande_leadsjobb i postgres.py och memory.py. Undantaget för väckbara körningar gäller nu bara status 'processing', alltså det väckaren läser, och bara om updated_at ligger inom den nya konstanten stadare.VACKNING_RESERV_MINUTER (24 h). En köad rad med korning-objekt och en väckbar rad som varit tyst längre än ett dygn fälls nu med error=HANGFEL_JOBB. De rörda testfilerna går gröna.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\jobs\stadare.py (ny konstant VACKNING_RESERV_MINUTER = 24 * 60; modulens docstring nämner gränsen och att undantaget bara gäller 'processing')
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\postgres.py (stada_hangande_leadsjobb: undantaget kräver status = 'processing' och updated_at >= now() - make_interval(mins => $5), där $5 = VACKNING_RESERV_MINUTER)
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\memory.py (stada_hangande_leadsjobb: samma villkor speglat, tidsstämpeln läses en gång som 'senast')
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_job_003.py (nya test_en_vackbar_korning_falls_efter_reservgransen och test_en_koad_korning_undantas_inte)

### Tester
- `python -m pytest tests/invariants/test_inv_job_003.py -q (i snajp-support, före rättningen)` → 2 failed, 11 passed in 18.78s
- `python -m pytest tests/invariants/test_inv_job_003.py -q (efter rättningen)` → 13 passed in 13.84s
- `python -m pytest tests/leads/test_stadare.py -q` → 10 passed in 15.29s
- `python -m pytest tests/invariants/test_inv_store_001.py -q` → 705 passed in 6.12s

### Ej gjort
- Fynd 1 är inte rättat, eftersom ARCHITECTURE_INVARIANTS.md ligger utanför paketet. Orkestreraren behöver skriva om INV-LEADS-N-001 enligt byggarens tidigare förslag. INV-JOB-003 behöver en mening om tre saker: städaren skriver HANGFEL_JOBB som error i liggaren, den fäller inte en väckbar körning (status processing, batch, klar=false, inget listjobb, pagaende=0), och undantaget upphör efter VACKNING_RESERV_MINUTER (24 h).
- Tempmapparna är inte borttagna. Raden 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses. Den sitter i samma meddelande som beskedet att en worktree inte kunde skapas på grund av diskbrist (4,2 GB ledigt, 5,4 GB krävs). Permanent radering kräver ett uttryckligt besked om vad som ska bort, och den här uppgiften gällde granskarens fynd. Orkestreraren eller Anton får peka ut mapparna. Scratchpaden innehåller dessutom utredningsfilerna som paketet bygger på.
- SQL:en i postgres.py är inte körd mot en riktig databas (ingen databas får röras). Den är speglad i MemoryStorage och testad där.
- Ingen TypeScript rördes, så ingen tsc kördes.

### Antaganden
- Reservgränsen är satt till 24 h (granskarens exempel) och mäts på updated_at, samma klocka som den vanliga städningen.
- En köad rad (status 'queued') med korning-objekt städas efter den vanliga tröskeln (60 min), eftersom väckaren aldrig läser den.
- Konstanten ligger i stadare.py bredvid HANGFEL_JOBB och importeras lokalt i storage-metoderna, som HANGFEL_JOBB redan gjordes. Protokollet i base.py är oförändrat (INV-STORE-001 grön).

### Syns i gränssnittet
- En Iris-körning som väckaren inte fått i gång på ett dygn, eller som fastnat i status 'queued', visas nu som Misslyckades med städarens felmening (HANGFEL_JOBB) i stället för att stå kvar som Pågår för alltid. Det ser ut som en vanlig fälld rad i Iris › Körningar, och ingen ny yta har tillkommit.
