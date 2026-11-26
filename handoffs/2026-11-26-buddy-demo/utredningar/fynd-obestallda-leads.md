# obestallda-leads
belagt=True konfidens=hog | granskning: haller=True konfidens=hog

## Sammanfattning
De 36 raderna är körningens ringlistebolag. De skapas som prospekt i `_spara_listspar` (`snajp-support/app/api/leads.py:3506-3510`). En vanlig körning ger dem origin 'ring', och de filtreras då bort ur leadslistan. Demons körning var en provkörning (is_test: demokontot, demovyn eller admin som tittar som kund). Raden `"test" if k.get("is_test") else "ring"` ger dem då origin 'test'. Origin 'test' är samma markering som provkörningens Iris-leads har, så filtret `listvy.synliga` (som bara släpper bort 'ring') visar dem. Det förklarar etiketten "Provkörning" och 44 i "Leads i listan". Ingen research köas på dem. Därför saknar de poäng och nivå, och frontendens `researchPagar()` visar "Researchar". Samtal hoppar över origin 'test', så de syns inte där heller. Jag har återskapat felet med MemoryStorage: is_test=True ger origin 'test' och raden syns i leadslistan, is_test=False ger 'ring' och raden syns inte. Också i skarpa körningar skapas ringprospekt utöver beställt antal. De syns i Samtal och i Att göra, räknas som "nya leads" i veckoanalysen, och "Skapa utkast"/Processa kan starta betald research på dem. Jag rekommenderar alternativ B: ringbolagen skrivs som en lista under Listor (följer körningens is_test), på samma sätt som "Ej kvalificerade". Ändringen sitter i en enda funktion. Inget prospekt skapas utöver beställt antal, och inget visas i leadslistan utan bedömning.

## Grundorsak
1) Var de skapas. `merinfo._komplettera_iris` (`snajp-support/app/leads/sources/merinfo.py:1302-1319`) lägger varje bolag med spår "ring" från `fordela` (rad 1153-1158) i `listspar` via `ringrad()`. Det gäller alla sådana bolag och är inte begränsat av `antal`: bara Iris-spåret kapas vid `len(ut) < antal`. När körningen är klar anropar `_fyll_pa` funktionen `_spara_listspar` (`api/leads.py:3459`). Den skapar ett prospekt per ringrad med `_skapa_prospekt_ur_kandidat(storage, tenant_id, rad, "test" if k.get("is_test") else "ring")` (rad 3507-3509). Inget `_lagg_prospektjobb` körs på dem.
2) Varför de syns. Leadslistan, nyckeltalet "Leads i listan" och munkdiagrammet räknar alla genom `listvy.synliga` (`app/leads/listvy.py:106`). Filtret tar bara bort `origin == "ring"`. En provkörning ger origin 'test', och då går raden igenom. Provkörningen sätts av `LeadsSida.tsx:259` (`isTest={demo || isDemo || vy === "demo"}`) eller av proxyn vid impersonering (`app/api/snajp-support/_auth.ts:39-56`). `LeadsTabell.tsx:1204` ritar etiketten "Provkörning" för origin 'test'.
3) Varför "Researchar". Inget researchjobb köas, och `score_total`, `niva` och `icp_fit` är tomma. `IrisBolag.tsx:186-188` och `LeadsTabell.tsx:235-238` härleder "Researchar" ur just att de fälten saknas. Statusen 'researching' sätts inte.
4) Samtal. `samtal.py:39,99` hoppar över origin 'test'. Provkörningens ringbolag hamnar alltså i leadslistan i stället för i Samtal.
Main och development är identiska på alla berörda rader (kontrollerat med git show origin/main).

## Bevis
- snajp-support/app/api/leads.py:3506-3510 _spara_listspar skapar ett prospekt per ringrad med origin "test" om körningen är en provkörning, annars "ring". Ingen research köas.
- snajp-support/app/api/leads.py:3459 _fyll_pa anropar _spara_listspar när körningen är klar, efter att Iris-leveransen (mal) är räknad. Ringraderna kommer alltså utöver beställt antal.
- snajp-support/app/leads/sources/merinfo.py:1302-1319 _komplettera_iris lägger varje spar=='ring' i listspar utan tak. Bara Iris-spåret begränsas av antal.
- snajp-support/app/leads/listvy.py:106 synliga() tar bara bort origin=='ring'. Origin 'test' går igenom till leadslistan, nyckeltalet och /prospects/fordelning (api/leads.py:654, 721).
- components/leads/LeadsSida.tsx:259 Demokontot och demovyn kör alltid med isTest=true.
- app/api/snajp-support/_auth.ts:39-56 Admin som tittar som kund får is_test=true på varje skrivning, också på körningar.
- components/leads/IrisBolag.tsx:186-188, 711-712 researchPagar() blir sann när niva, score_total och icp_fit saknas. Därför visas 'Bedömning: Researchar' på ett lead som aldrig köats för research.
- components/leads/LeadsTabell.tsx:235-238, 1204 Samma härledning ger poäng '–'. Origin 'test' ritar etiketten Provkörning.
- components/leads/LeadsOversikt.tsx:340-346 'Leads i listan' och 'nya' är LeadsTabells rader, alltså samma filtrerade mängd: 8 Iris + 36 ring = 44.
- snajp-support/app/leads/samtal.py:39, 99-103 Samtal hoppar över origin 'test'. Ringlistan tar bara origin 'ring'. Provkörningens ringbolag syns alltså inte i Samtal.
- snajp-support/app/storage/postgres.py:3942-3945 weekly_analytics räknar nya_leads som origin not in ('example','test'). Skarpa ringprospekt (origin 'ring') räknas alltså som nya leads i Analys och i arbetsytans sifferblock (agent/arbetsyta_siffror.py:52).
- components/leads/AttGora.tsx:342 Att göra räknar samtal.ring. Skarpa ringprospekt blåser upp kundens att göra-tal.
- snajp-support/app/storage/postgres.py:3641-3651 lista_upptagna_bolag läser alla prospekt utan att filtrera på origin. Provkörningens 36 rader stänger därför ute bolagen från tenantens framtida körningar.
- snajp-support/app/api/admin_flytt.py:47-51 Flytt till main gör origin 'test' till 'import'. Ett flyttat testringprospekt blir ett skarpt lead utan bedömning.
- snajp-support/app/leads/budget.py:74-86 Leadsbudgeten räknar tokens i agent_runs. Ringprospekten kostar inga tokens när de skapas, men 'Skapa utkast'/Processa på dem startar betald research. Någon räknare för antal leads mot kunden finns inte i koden.
- snajp-support/tests/leads/test_fordelning.py:152-159 Testet prövar bara is_test=False. Fallet is_test=True saknar test.
- (egen återskapning, MemoryStorage): _spara_listspar med is_test=True gav origin ['test'] och 1 rad i listvy.synliga. Med is_test=False gav den origin ['ring'] och 0 rader.

## Förslag
- REKOMMENDATION B (minsta ändring som tar bort hela felklassen). I _spara_listspar (api/leads.py:3498-3526) skapas inget prospekt för spar=='ring'. Ringraderna skrivs i stället till en lista med create_lead_list/add_lead_list_item, på samma sätt som 'Ej kvalificerade'. Listan får titeln 'Ringlista, Iris <datum>', is_test följer körningen och raden behåller VD, telefon, antal anställda och signal_detalj. k['fordelning']['ring'] räknas som förut, och k['listspar_ringlista'] sparar list-id:t. Följden: körningen skapar exakt de Iris-prospekt som räknas mot mal. Leadslistan, 'Leads i listan', munkdiagrammet, Att göra och veckoanalysen innehåller bara bedömda leads. Bolagen finns kvar för kunden under Listor, med telefon, CSV-export och Processa om/Skapa utkast som kunden själv startar. Ingen ny ruta behövs: Listor är den befintliga ytan för bolag som inte är Iris-leads. Dedup gäller fortfarande, eftersom lista_upptagna_bolag läser lead_list_items.
- Den kundvända texten i korning.sammanfatta (korning.py:320) ändras från 'till ringlistan' till 'i ringlistan under Listor'. Om sammanfattningen visas med lokal behöver den ett engelskt par.
- Konsekvens för reglerna 15–17 och Samtal. Regel 15 ('bara telefon → ringlistan') uppfylls av listan, men Samtal › Ringlista (samtal.py, origin='ring') får inga nya rader från körningar. Regel 17 (återkoppling på kontaktade Iris-leads) påverkas inte. Anton behöver bestämma vad Samtal-fliken Ringlista ska göra: (a) visa bara äldre origin='ring'-prospekt och sedan tas bort, eller (b) få rader först när kunden själv flyttar en listrad dit. Flyttmekanismen finns redan (omprova MARKERING 'ringlistan', signal='flyttad'). Beslutet skrivs i docs/BESLUT.md, och CLAUDE.md regel 15/17 uppdateras.
- Avvisade alternativ. (A) Skapa dem inte alls: bryter regel 8 och 15 ('bolag kastas inte', 'bara telefon → ringlistan') och kastar kontaktdata som kunden redan betalat sidhämtningar för. (C) Räkna in dem i beställt antal: då kan 10 beställda ge 2 bedömda och 8 obedömda leads. Det bryter Antons nya regel om att inget obearbetat lead får ligga i listan, och kunden får sämre leverans för samma pris.
- Om Anton vill ha ett snävare första steg: bara i provkörningar skrivs ringraderna till listan i stället för som 'test'-prospekt (en rad i samma funktion). Felet i demon försvinner då, men skarpa körningar blåser fortfarande upp Samtal, Att göra och veckoanalysen. Jag rekommenderar hela B.
- Skydd i fler lager (valfritt, liten ändring): i postgres.py:3944 och memory.py weekly_analytics läggs 'ring' till bland de origin som inte räknas som nya leads, så att äldre ringprospekt inte räknas där.
- De 36 raderna: radera dem inte. Hitta dem read-only med följande villkor: tenant = demokontots (eller den impersonerade kundens) tenant_id, origin='test', created_at mellan körningens start och slut (leads_jobs-raden för batch_id), contact_email is null, contact_phone not null, score_total, niva och icp_fit är null, och inget leads_jobs-barn har prospect_id på raden. Kontrollera också att company_name inte finns i körningens k['jobs']. Antalet ska bli 36 och stämma mot k['fordelning']['ring']. Åtgärd, med Antons ja: arkivera dem (arkiverad_at, syns under ?arkiverade=1), eller flytta dem till en is_test-lista 'Ringlista, Iris 2026-11-24' med samma skript som för B och arkivera sedan. Arkiveringen tar inte bort dem ur dedup-mängden (upptagna). Om tenanten är en riktig kund som visades genom impersonering stänger raderna ute 36 bolag från kundens skarpa körningar. Då bör de raderas, med Antons uttryckliga ja. Kom ihåg att development är en spegel och har samma rader.

## Filer att ändra
- snajp-support/app/api/leads.py (_spara_listspar, rad 3476-3529: ringrader till en lista i stället för prospekt; docstringen)
- snajp-support/app/leads/korning.py (sammanfatta, rad 320: 'i ringlistan under Listor')
- snajp-support/app/leads/samtal.py (docstringen och, efter Antons beslut, ringlistans källa)
- snajp-support/app/storage/postgres.py (weekly_analytics rad 3944: utesluta 'ring', valfritt)
- snajp-support/app/storage/memory.py (weekly_analytics: samma uteslutning, valfritt)
- docs/BESLUT.md (beslutet med Antons resonemang)
- CLAUDE.md (§ Leads, regel 15/17: var ringlistan ligger)
- snajp-support/tests/leads/test_fordelning.py
- snajp-support/tests/leads/test_upptagna_bolag.py

## Tester
- test_fordelning: _spara_listspar med is_test=True skapar 0 prospekt. En lista 'Ringlista, Iris <datum>' med is_test=True innehåller ringraden med telefon, VD och antal anställda. k['fordelning']['ring']==1.
- test_fordelning: samma fall med is_test=False skapar 0 prospekt och en lista med is_test=False. Det befintliga testet på rad 152-181 skrivs om: assert ring['origin']=='ring' ersätts av listans rad.
- Nytt invarianttest (t.ex. tests/leads/test_korning_skapar_bara_beställt.py): en hel Iris-körning mot MemoryStorage med mal=2 och listspar med fem ringrader och ett överskott av Iris. Efteråt finns högst mal prospekt med körningens origin, och vart och ett har ett köat researchjobb.
- test_listvy: ett prospekt med origin 'test' utan nivå eller poäng och utan researchjobb visas inte efter körningen. Det följer av att _spara_listspar inte längre skapar det; testet låser att körningsvägen aldrig ger ett sådant prospekt.
- test_upptagna_bolag: ett bolag i ringlistan (lead_list_items) räknas som upptaget nästa körning.
- Om weekly_analytics ändras: test i tests/db eller tests/storage att origin 'ring' inte räknas i new_leads.
- Kör bara riktat: pytest snajp-support/tests/leads/test_fordelning.py.

## Risker
- Samtal › Ringlista slutar få nya rader. Utan Antons beslut om källan (se förslagen) kan säljare som ringer därifrån tro att flödet har stannat.
- Prospekten skapas idag efter dedup mot upptagna. Listraden måste också läggas till i sedda innan nästa rad skrivs (sedda |= bolagsnycklar), annars blir det dubbletter i samma körning.
- Ringraden har fält som add_lead_list_item kanske inte tar emot (spar, jev_triage, anstallda, postnr, sni, omsattning). Kontrollera kolumnerna i lead_list_items och filtrera fälten innan skrivningen. Ingen migration ska behövas, eftersom 'Ej kvalificerade' redan skrivs på samma sätt.
- Gamla körningar har kvar sina 'ring'-prospekt. Samtal och veckoanalysen läser dem som förut om ingen engångsflytt görs.
- Antal leads som räknas mot kunden finns inte som mätare i koden (budgeten räknas i tokens). Påståendet att ringbolagen 'äter budget' gäller bara när kunden startar Skapa utkast/Processa på dem. Det är belagt i koden men inte mätt i produktion.
- Om demon gjordes som impersonering av en riktig kund ligger de 36 test-raderna i kundens tenant och stänger ute bolagen från kundens körningar tills de tas bort.

## Öppna beslut
- B, A eller C? Jag rekommenderar B, men den flyttar ringlistan (regel 15) från Samtal till Listor, och det kräver Antons ja.
- Samtal › Ringlista efter B: ska fliken fasas ut, eller ska kunden flytta en listrad dit själv (befintlig flytt, signal='flyttad')?
- De 36 raderna: arkivera, flytta till en is_test-lista eller radera? Radering kräver Antons uttryckliga ja och påverkar både main och development-spegeln.
- Ska veckoanalysen sluta räkna äldre origin 'ring' som nya leads redan nu?

## Prodfråga
Read-only mot main: vilken tenant körde demon (demokontot med workspaces.is_demo, eller en riktig kund via impersonering)? Hur många prospekt med origin='test', contact_email null, contact_phone not null och score_total/niva/icp_fit null skapades under körningens batch_id-intervall? Antalet ska vara 36 och stämma mot korningens fordelning.ring.

## GRANSKARE: invändningar
- Kedjan går att följa i koden och jag hittar inget som motsäger den. merinfo.py:1302-1319: bara Iris-spåret kapas vid len(ut) < antal. Varje spar=='ring' läggs i listspar utan tak, och listspar fylls på över alla rundor. leads.py:3459: _spara_listspar körs när körningen är klar. Rad 3506-3509 skapar sedan ett prospekt med origin 'test' när k['is_test'] är satt, annars 'ring'. Inget _lagg_prospektjobb körs på dem, till skillnad från Iris-vägen på rad 3413-3433. listvy.py:106 släpper bara bort origin=='ring', så 'test' går igenom.
- Main och development skiljer sig inte i leads.py, listvy.py, merinfo.py, samtal.py, components/leads/ och _auth.ts (git diff --stat origin/main origin/development gav inget). Felet finns alltså lika på båda grenarna.
- Ingen annan väg skapar ring-prospekt. Den enda andra 'ring'-träffen i leads.py (rad 5119, _omprova_utfall) ger bara utfallstexten för Processa om. Den skriver på listraden och dess bakgrundsprospekt och skapar inget nytt prospekt. Utredarens påstående att 'flyttmekanismen finns redan (omprova MARKERING ringlistan, signal=flyttad)' håller jag därför inte för belagt. MARKERING i omprova.py:32 är en etikett. Jag har inte sett någon kod som gör en listrad till ett origin='ring'-prospekt.

## GRANSKARE: missat
- Förslag B tappar antal anställda. add_lead_list_item (postgres.py:3537-3558, memory.py:2558-) skriver bara de fasta kolumnerna och 'extra'. anstallda, omsattning, sni, jev_triage och spar kastas tyst om ringrad skickas in med **rad. Regel 15 kräver att 'Antal anställda visas alltid'. Utredaren skriver att listraden 'behåller ... antal anställda', men det stämmer inte utan att anstallda läggs i extra (jsonb, migration 152) eller i signal_detalj. Listvyn måste då också visa värdet.
- Utredarens 'Flyttmekanismen finns redan' för alternativ (b) i Samtal är inte belagt, se invändningarna. Om Anton väljer (b) är det ny kod, inte befintlig.
- Provkörningens ringlista hamnar också under Listor och räknas i upptagna (lista_upptagna_bolag, postgres.py:3641-3653, läser lead_list_items oavsett is_test). B flyttar alltså problemet med att provkörningar stänger ute bolag från skarpa körningar. Det tar inte bort det. Ej kvalificerade-listan beter sig redan så i dag, men det bör nämnas.
- Antons regel ('inte fler än beställt') kan också läsas som att den gäller listan 'Ej kvalificerade', som skapas utöver beställt antal. Den hamnar inte i leadslistan och räknas inte, så den följer rimligen regeln. Ingen av dem prövade det, och det bör bekräftas med Anton i samma beslut.
- Ringraderna samlas inte bara upp utan tak. Varje ring-bolag kostar också sidhämtningar i kontaktsökningen, och prov är rankade[:antal*PROV_PER_LEAD]. Kostnaden för ringbolagen tas alltså redan när de söks, inte bara vid Skapa utkast. Utredarens risk 'äter budget bara vid Skapa utkast' underskattar det något, men det ingår i körningstaket.
- Inga ytterligare frontendfiler behöver ändras. LeadsOversikt läser listorna via /leads/listor (rad 232-245), så en ny ringlista syns i översiktens Listor-panel utan ny yta. Det stämmer med regeln om befintlig yta, men listan räknas då in i 'egna' listor.

## GRANSKARE: justerat förslag
- Behåll rekommendation B: ringraderna skrivs i _spara_listspar (snajp-support/app/api/leads.py:3498-3526) till en lista under Listor i stället för som prospekt, med samma kodväg som för Ej kvalificerade. Använd en gemensam hjälpfunktion som skapar en lista per spår och körning: 'Ringlista, Iris <datum>' och 'Ej kvalificerade, Iris <datum>', med is_test från körningen och k['listspar_ringlista'] = id. Behåll listspar_sparad-vakten så att funktionen fortfarande bara körs en gång.
- Skriv ringraden genom ett uttryckligt fältfilter, inte med **rad: company_name, website, ort, postnr, orgnr, contact_name, contact_role, contact_phone, contact_level, signal='ring', signal_detalj, source_name, source_url och extra={'anstallda':…, 'omsattning':…}. Kontrollera att listvyn (LeadslistorView/listrad) visar antal anställda ur extra, så att regel 15 fortfarande gäller. Saknas det i vyn är det en tvåspråkig kolumnrubrik i den befintliga tabellen, ingen ny panel.
- korning.sammanfatta (snajp-support/app/leads/korning.py:320): ändra 'till ringlistan' till 'i ringlistan under Listor', med engelskt par om texten visas lokaliserad.
- listvy.synliga (listvy.py:106) får ett extra skydd för äldre rader: ett prospekt utan nivå, poäng och icp_fit som inte är kopplat till ett researchjobb visas inte. Det enklaste kriteriet är signal/kontaktväg 'ring' eller contact_email null och origin in ('ring','test') utan niva. Då försvinner de 36 befintliga demoraderna ur leadslistan och nyckeltalet utan att någon rad raderas. Spärren ska ligga i synliga, eftersom både /prospects, fordelning och nyckeltalet räknar därifrån.
- Samtal › Ringlista: Anton beslutar. Utredarens påstående om att en flyttmekanism redan finns ska strykas, så att beslutsunderlaget inte vilar på något obelagt. Beslutet förs in i docs/BESLUT.md, och CLAUDE.md regel 15 uppdateras: ringlistan är en lista under Listor.
- Tester: test_fordelning.py ska täcka is_test True och False, 0 prospekt, en lista per spår och att anstallda finns i extra. Lägg till ett invarianttest med en hel körning mot MemoryStorage där antalet prospekt med körningens origin är högst mal och vart och ett har ett researchjobb. test_listvy ska visa att ett obedömt prospekt med origin test/ring inte syns. test_upptagna_bolag ska visa att en ringlisterad räknas som upptagen. Kör bara riktat: pytest snajp-support/tests/leads/test_fordelning.py.
- De 36 raderna: hitta dem read-only med samma villkor som utredaren angav, och kontrollera dessutom att signal='ring' eller contact_level i ('named_role_match','role_address') och att contact_email är null. Om demotenanten är demokontot räcker skyddet i synliga plus arkivering med Antons ja. Om det var en riktig kund som impersonerades krävs radering med Antons uttryckliga ja, eftersom raderna annars stänger ute bolagen från kundens skarpa körningar. Development-spegeln har samma rader.
