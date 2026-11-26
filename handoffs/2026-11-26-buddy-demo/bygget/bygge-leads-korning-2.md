# paket leads-korning-2

## Bygge
Del 2 är byggd: påfyllnadsstegen och vilande körning. Testerna skrevs först och fällde dagens kod (test_pafyllnad: AttributeError; test_inv_leads_n_002: 5 failed). Efter rättningen går alla rörda testfiler gröna.

1. Stegen. korning.py har fått rena funktioner: nasta_pafyllnad, BORTVALSGRUPPER, bortvalsgrupp, rangordna_bortval, pafyllnadsskal, tolka_storleksskal, vidgad_grans, inom_vidgning, utanfor_ursprung, far_fyllas_pa, vila, vilans_skal, ska_vackas och vakna. Dit kom också konstanterna PAFYLL_BELAGT_NEJ = True, PAFYLLNADSSTEG, VIDGNING, VILA_TIMMAR och TJANSTEFEL. Tillståndet ligger i k["pafyllnad"].

2. Motorn. Där _fyll_pa_last förr avslutade under målet körs nu _starta_pafyllnad (ny funktion i api/leads.py):
- Steg 1 köar om de egna prospekten som föll på tjänstefel och kör om fallna sökrundor en gång.
- Steg 2 returnerar ett uppdrag som _kor_sokrunda kör utanför låset via _omprova_listspar (omprova.hamta_bolag, sok_alla, planera). Det räknas inte som en sökrunda.
- Steg 3 och 5 tar körningens egna bortval i rangordning, sparar pafylld och pafylld_skal och köar jobbet med körningens scope. Ett påfyllt lead skrivs ur sparad research.
- Steg 4 vidgar anställda och omsättning (+25, +50, +100 %). Den vidgade gränsen läggs i k["overrides"] (så att researchens storleksrad ser den) och i sökprofilen. Bortvalen inom gränsen släpps ur uteslutningen. Ett lead som levereras tack vare vidgningen märks som påfyllt i _rapportera_till_korning.
- Ett steg står som klart först när det inte har något kvar att pröva. Geografin vidgas aldrig.

3. Grindarna. Bara flaggan pafylld släpper ett nivå C-lead förbi leverbarheten (_leverbarhet), tröskelstoppet för utkast, listvy.synliga och sändspärren i scheduler.py. Mottagaren och lägesbeskrivningen krävs fortfarande. Misslyckas påfyllningen tas märkningen bort.

4. Vilande. När alla steg är tömda blir körningen vilande med skälet registret, kredittak, sokningen_foll, ingen_malgrupp eller inga_traffar.
- Den står kvar i processing och städaren fäller den aldrig (postgres och memory).
- Väckaren hoppar över den tills ett dygn har gått. Då nollar vakna stegen och körningen får ett nytt sidtak.
- Kundens Avbryt fungerar även på en vilande körning.
- Sammanfattningen läser vilans skäl, och webbpoolen startar även när körningen lägger sig att vila.

5. Lagring och dokument. Migrationen 20261125130000_158_pafyllt_lead.sql lägger till prospects.pafylld (boolean, default false) och pafylld_skal (text); den är additiv och idempotent. merinfo skriver nu gränsen i omsättningsskälet. ARCHITECTURE_INVARIANTS.md har omskrivna INV-LEADS-N-001 och INV-LEADS-EXIST-001, med datum 2026-11-24 och Antons regel ordagrant.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\korning.py (importer; orgnr i registrets bortval i tratten; hela § Påfyllnaden med konstanter och rena funktioner; sammanfatta läser vilans skäl)
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\leads.py (_kor_sokrunda och ny _omprova_listspar; _sla_in_sokrunda hanterar omprövningsrundan; _fyll_pa_last har vilande och väckning, vidgad profil, fria namn ur uteslutningen, sidtak_extra, märkningen 'vantande' och påfyllnadsstegen i stället för 'klar under målet'; nya _starta_webbpool och _starta_pafyllnad; _rapportera_till_korning märker de vidgade; vack_stillastaende_korningar hoppar över vilande; _leverbarhet och _run_batch_prospect släpper pafylld)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\listvy.py (LISTKOLUMNER och FORDELNINGSKOLUMNER fick pafylld/pafylld_skal; synliga visar ett påfyllt C-lead)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\scheduler.py (sändspärren ej_styrkt släpper pafylld)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\sources\merinfo.py (omsättningsskälet bär gränsen: '(högst X kr)' och '(minst X kr)')
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\postgres.py (spara_bedomning skriver pafylld/pafylld_skal; _PROSPEKT_LASKOLUMNER har fälten; stada_hangande_leadsjobb undantar vilande körningar)
- C:\Users\Anton L\snipe-leads\snajp-support\app\storage\memory.py (samma två ändringar som postgres)
- C:\Users\Anton L\snipe-leads\ARCHITECTURE_INVARIANTS.md (INV-LEADS-N-001 omskriven: levererar N eller vilar; INV-LEADS-EXIST-001 har fått undantaget för påfyllda leads)
- C:\Users\Anton L\snipe-leads\components\leads\IrisKorningar.tsx (typen Korning.vilande; VILA_SKAL och vilaText i utfallscellen; vilande körningar pollas inte)
- C:\Users\Anton L\snipe-leads\components\leads\LeadsTabell.tsx (T.pafyllt; motiveringsraden visar 'Påfyllt: <skäl>' / 'Filled in: <reason>')
- C:\Users\Anton L\snipe-leads\components\leads\IrisBolag.tsx (typen fick pafylld/pafylld_skal; bedömningscellen visar märkningen under nivån)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_leads_n_001.py (_kor väntar på klar eller vilande; test_slut_pa_kandidater_namnger_flaskhalsen blev test_slut_pa_kandidater_ger_en_vilande_korning; test_taket_ar_ett_larm_inte_ett_slut förväntar sig vilande)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_job_003.py (ny _vanta_slut; uppgivet barnjobb, återtag och sokningen_foll förväntar sig vilande)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_leads_exist_001.py (nytt test_ett_pafyllt_lead_ar_ett_markt_undantag)

### Nya filer
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_pafyllnad.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_leads_n_002.py
- C:\Users\Anton L\snipe-leads\db\migrations\20261125130000_158_pafyllt_lead.sql

### Tester
- `python -m pytest tests/leads/test_pafyllnad.py -q (före rättningen)` → 1 failed in 4.50s (AttributeError, med -x)
- `python -m pytest tests/invariants/test_inv_leads_n_002.py -q (före rättningen)` → 5 failed in 20.67s
- `python -m pytest tests/leads/test_pafyllnad.py -q` → 34 passed in 2.00s
- `python -m pytest tests/invariants/test_inv_leads_n_002.py -q` → 5 passed in 14.15s
- `python -m pytest tests/invariants/test_inv_leads_n_001.py -q` → 8 passed in 14.86s
- `python -m pytest tests/invariants/test_inv_job_003.py -q` → 13 passed in 16.26s
- `python -m pytest tests/invariants/test_korning_fortsatter_till_malet.py -q` → 9 passed in 15.85s
- `python -m pytest tests/invariants/test_inv_leads_exist_001.py -q` → 8 passed in 18.09s
- `python -m pytest tests/invariants/test_inv_store_001.py -q` → 720 passed in 6.35s
- `python -m pytest tests/leads/test_fordelning.py -q` → 25 passed in 14.29s
- `python -m pytest tests/leads/test_listvy.py -q` → 9 passed in 35.86s
- `python -m pytest tests/leads/test_scheduler.py -q` → 19 passed in 2.25s
- `python -m pytest tests/leads/test_merinfo.py -q` → 34 passed in 14.90s
- `python -m pytest tests/leads/test_korning_hittar_bolag.py -q` → 9 passed in 1.73s
- `python -m pytest tests/leads/test_sidhamtning.py -q` → 11 passed in 13.20s
- `python -m pytest tests/leads/test_upptagna_bolag.py -q` → 13 passed in 16.71s
- `python -m pytest tests/leads/test_webbpool.py -q` → 13 passed in 16.68s
- `python -m pytest tests/api/test_analytics_weekly.py -q` → 6 passed in 2.04s
- `python -m pytest tests/api/test_korning_leverera_bestallt.py -q` → 8 passed in 14.33s
- `python -m pytest tests/api/test_korningar.py -q / tests/api/test_korning_lasning_latt.py -q` → 2 passed in 15.87s / 5 passed in 13.55s
- `python -m pytest tests/api/test_dubbelstart_vagar.py, tests/leads/test_discovery.py, test_kreditslut_leadsjobb.py, test_saljlista_bestallning.py, tests/test_korning_samtidighet.py, tests/test_korning_styrning.py, tests/test_leads_strom.py (var för sig, före webbpoolsändringen)` → 4 passed / 26 passed / 13 passed / 3 passed / 5 passed, 60 warnings / 15 passed / 6 passed
- `python -m pytest tests/invariants/test_inv_copy_001.py -q (repots rot)` → 4 passed in 2.42s
- `python -m app.leads.korning` → korning: ok
- `node node_modules/typescript/bin/tsc -p <scratchpad>/tsconfig.pafyll.json (bara IrisKorningar.tsx, LeadsTabell.tsx, IrisBolag.tsx och next-env.d.ts)` → ingen utskrift, inga typfel

### Ej gjort
- Tempmapparna är inte borttagna. Användarens rad 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses. Permanent radering kräver ett besked om exakt vad som ska bort. Scratchpaden under %TEMP%\claude innehåller dessutom utredningsfilerna, och tre andra byggare arbetar mot samma maskin. Uppmätt: %TEMP% är 2,8 GB, varav %TEMP%\claude 1,1 GB, och C: har 3,7 GB ledigt. Orkestreraren eller Anton får peka ut mapparna.
- Ingen bild av gränssnittet är tagen, och inget är committat. Ingen git add eller commit har körts, enligt uppdraget.
- base.py rördes inte (utanför paketet), så BEDOMNINGSFALT saknar pafylld och pafylld_skal. postgres.py och memory.py lägger till fälten lokalt i spara_bedomning. Hör de hemma i protokollet ska de flyttas till BEDOMNINGSFALT.
- lib/leads/suite.ts rördes inte (utanför paketet). LeadsTabell utökar SuiteProspekt lokalt med typen MedPafyllnad.
- Inget integrationstest kör steg 2 (omprövningen anropar nätverket via omprova) eller steg 4 (storleksvidgningen med en vidgad sökrunda). Stegens ordning, tolkningen, vidgningen och märkningen 'storleken vidgad' är bara testade som rena funktioner. Kedjan från bortval till leverans, vilan och städarens undantag är testade i motorn.
- Postgres-SQL:en (städarens undantag, de nya kolumnerna i projektion och UPDATE) är inte körd mot en riktig databas, bara speglad i MemoryStorage. Migration 158 är inte körd.
- docs/BESLUT.md och CLAUDE.md (regel 23 under § Leads) är inte uppdaterade. Orkestreraren skriver dem.
- Statuscellen i IrisKorningar visar fortfarande 'Pågår' för en vilande körning; utfallscellen bär '8 av 10, letar vidare: <skäl>'. SLUT_ETIKETT['tak'] ('fyra gånger så många') står kvar för gamla rader. 'Klar, under målet' står kvar som etikett för äldre körningar men kan inte längre uppstå.
- pafylld_skal skrivs på svenska i backend, som motivering och disqualifiers. Bara prefixet 'Påfyllt'/'Filled in' och vilans skäl är tvåspråkiga i frontend.
- Omsättningen vidgas bara i sökningens profil. context_pack._med_overrides (utanför paketet) tar inga omsättnings-overrides, men researchens bedömning fäller inte heller på omsättning.
- Fortsätt (_kan_fortsatta) är oförändrad. Den gäller bara gamla körningar som redan står klara eller fallna under målet.

### Antaganden
- Storleksvidgningen räknas mot kundens gräns: en övre gräns blir ceil(gräns × (1 + andel)), minst +1, och en undre floor(gräns × (1 − andel)). 49 blir 62 vid 25 %, och 5 blir 2 vid 50 %. Gränsen tas ur ursprungsprofilen (pafyllnad['ursprung']), inte ur skälets tal.
- Rangordningen i steg 3 är a till d och sedan en egen grupp 'ovrigt' (bortval utan belagt nej som inte passar a till d, eller som saknar score_breakdown). Utan den hade körningen kunnat vila medan sådana bolag fanns kvar.
- En storleksrad med MISS i researchen räknas som belagt nej på ett måste-kriterium, alltså steg 5. Ett produktmatchningsnej räknas som belagt när raden har belägg eller lyder 'Ingen av kundens produkter passar'. Ett MISS utan belägg räknas som okänt.
- Spärren fäller också bolag med ortraden MISS ('Området breddas aldrig'), arkiverade bolag och statusen lost, utöver punkt 2. Redan kontaktat betyder status contacted, replied, meeting, won eller lost, eller en träff i mängden kontaktade.
- Steg 1, 3 och 5 tar högst behovet (mål − levererade − pågående) åt gången, så att körningen aldrig överskrider beställningen. Ett steg står som klart först när inget är kvar att pröva.
- Steg 2 kör alla oprövade prova_om-rader på en gång med betald=False (cachade, gratis sidor). Bara de som ger en Iris-mottagare och passerar far_fyllas_pa blir kandidater.
- Leads från steg 2 och de som researchas om i steg 1 är vanliga leads och märks inte. Märkta blir de från steg 3 och 5, och de från steg 4 som ligger utanför kundens ursprungliga gräns, när de levereras.
- Kredittak, sokningen_foll och ingen_malgrupp hoppar över storlekssteget men kör övriga steg innan körningen vilar.
- Vid varje dygnsväckning nollas stegen och körningen får ett nytt sidtak, ett korningstak till via sidtak_extra. Utan det vilar en körning som stannat på kredittaket för alltid. Det är ett kostnadsantagande som Anton bör bekräfta.
- Listspåret sparas och webbpoolen startas även när en körning lägger sig att vila. Listspårets flaggor nollas vid väckning, och dubblettkontrollen i _spara_listspar hindrar att rader skrivs två gånger.
- Migrationen fick nummer 158 eftersom 156 och 157 redan låg i katalogen. 154 och 155 användes inte, de kan vara reserverade av andra byggare.
- En vilande körning har slut_orsak None. Utfallscellen läser korning.vilande.skal.

### Syns i gränssnittet
- Leads › Körningar och Översiktens Aktivitet (IrisKorningar.tsx): en vilande körning visar '8 av 10, letar vidare: <skäl>' (en: '8 of 10, still searching: <reason>') i utfallscellen, statusen 'Pågår' i ochre, och den pollas inte. Ska ses på desktop och mobil.
- Leadslistan (LeadsTabell.tsx): ett påfyllt lead står i listan med sin riktiga nivå (C i rött i poängcellen). Motiveringsraden under bolagsnamnet visar 'Påfyllt: <skäl>' (en: 'Filled in: <reason>') i stället för motiveringens första mening. Ingen ny kolumn. Ett vanligt nivå C-lead är fortfarande dolt.
- Bolagslådan (IrisBolag.tsx): under nivån i bedömningscellen står en rad 'Påfyllt: <skäl>' i ink-muted.
- Leadslistans nyckeltal och fördelning räknar nu ett påfyllt lead som synligt (listvy.synliga).

## Granskning: godkänd=False
- [blockerande] snajp-support/app/leads/autopilot.py (orsakas av api/leads.py:_fyll_pa_last + korning.vila):autopilot.py:61 En vilande körning står kvar i status 'processing' tills den når målet. autopilot.ska_kora returnerar False så länge någon autopilotkörning har status queued/processing. Det betyder att en enda autopilotkörning som lägger sig att vila (smal målgrupp, 'registret') stoppar kundens alla kommande autopilotkörningar utan att någon ser det, eftersom den kan vila i all oändlighet. Ingen test täcker fallet. FÖRSLAG: Låt ska_kora räkna en körning med korning.vilande som icke pågående (eller låt dagens autopilotkörning ta över den vilandes behov). autopilot.py ligger utanför paketet, så orkestreraren får avgöra vem som rättar det. Lägg till ett test där en vilande autopilotkörning inte blockerar nästa dags körning.
- [bor_rattas] snajp-support/app/api/leads.py:2938-2944 (_andra_korningars_bolag) En vilande körning har status processing och klar=false, så _andra_korningars_bolag fortsätter att räkna hela dess tratt (även tusentals registerbortval, som annars inte står sig mellan körningar), dess kandidater och dess listspår som upptagna för kundens alla andra körningar. Det pågår så länge körningen vilar, alltså möjligen för alltid. Dessutom läses den vilandes fulla arbetsminne vid varje sökrunda i varje annan körning, vilket är den kostnad som togs bort 2026-11-07. FÖRSLAG: Hoppa över rader med korning.vilande i _andra_korningars_bolag. En vilande körning har inga kandidater i rörelse. Behåll bara dess eventuella kandidater om det behövs. Lägg till ett test där två körningar kör samtidigt och den ena vilar.
- [bor_rattas] snajp-support/app/leads/korning.py:far_fyllas_pa (Kontakta inte / redan kontaktat) Spärren fäller 'Kontakta inte' bara på fälten utfall och kontakta_inte, som en prospektrad inte har, samt på status suppressed. Suppressionslistan och samtalens eller konversationernas utfall kontakta_inte slås aldrig upp. 'Redan kontaktat' via mängden kontaktade körs aldrig i drift, eftersom anroparna (egna_prospekt i _starta_pafyllnad och _omprova_listspar) inte skickar kontaktade. test_sparren_faller_vart_och_ett_av_fallen matar in syntetiska fält och prövar alltså bara funktionen mot sig själv. FÖRSLAG: Låt anroparna hämta mängden en gång per steg och skicka in den som kontaktade: upptagna.hamta plus skickade utskick och suppressionslistan, plus samtal och konversationer med kontakta_inte. Alternativt kan far_fyllas_pa ta dem som parametrar. Testa med MemoryStorage, där ett bolag har ett samtalsutfall kontakta_inte respektive en adress på suppressionslistan.
- [bor_rattas] snajp-support/app/leads/korning.py:_GRUPPSKAL, pafyllnadsskal, utanfor_ursprung pafylld_skal är fasta svenska strängar som kunden ser i LeadsTabell och IrisBolag efter 'Filled in:'. En engelsk användare läser alltså 'Filled in: kopplingen till det kunden säljer kunde inte beläggas…'. Uppgiften kräver att varje användarvänd text är tvåspråkig, och skälen är en sluten uppsättning som går att översätta. FÖRSLAG: Spara gruppnyckeln, eller ett {sv, en}-par, i pafylld_skal och översätt i frontend (LeadsTabell T / IrisBolag T). Alternativt kan skälet byggas på kundens språk i backend. Tröskelfallet bär ett tal och kan formateras på båda språken.
- [bor_rattas] snajp-support/tests/invariants/test_inv_leads_n_002.py: Bara steg 3 körs genom motorn. Steg 1 (att researcha om tjänstefelen och köra om fallna sökrundor), steg 2 (omprövningen via _omprova_listspar och _sla_in_sokrunda) och steg 4 (den vidgade sökrundan, fria namn ur uteslutningen, overrides till researchen och märkningen 'storleken vidgad' i _rapportera_till_korning) har inget motortest. Det gäller även steg 5 genom motorn. Ordningen prövas bara som listan klara i två fall. FÖRSLAG: Lägg till motortester med fejkad sökning och research. (1) Ett prospekt med 'Inget källmaterial' researchas om och levereras. (2) En prova_om-rad, med omprova.sok_alla monkeypatchad att ge en mejladress, blir en Iris-kandidat och lämnar listspåret. (3) Ett registerbortval 'För stort: 55 anställda (högst 49)' släpps vid +25 %, levereras och bär pafylld och skälet 'storleken vidgad'.
- [notering] snajp-support/app/leads/korning.py:nasta_pafyllnad / _SOKSTOPP Vid kredittak eller en fallen sökning körs först stegen 1, 2, 3 och 5 (belagt nej) innan körningen vilar. Uppgiften kan läsas som att körningen i de fallen ska bli vilande direkt. Nu kan alltså bolag med belagt nej levereras dagen innan en ny sökning med nytt sidtak hade kunnat hitta fullt kvalificerade. FÖRSLAG: Låt orkestreraren eller Anton bekräfta tolkningen. Ett alternativ är att hoppa över belagt_nej när orsaken är kredittak eller sokningen_foll och vänta på dygnsväckningen.
- [notering] snajp-support/app/api/leads.py:_fyll_pa_last (vakna, sidtak_extra) Varje dygnsväckning ger körningen ett helt nytt korningstak av betalda sidor, utan någon övre gräns, och en körning med 'registret' eller 'inga_traffar' väcks varje dygn för alltid. Byggaren flaggar själv detta som ett kostnadsantagande. FÖRSLAG: Låt Anton bekräfta, eller sätt ett tak på antalet väckningar och kredit per körning och skriv det i BESLUT.md.
- [notering] snajp-support/app/api/leads.py:_starta_pafyllnad steg 4 Den vidgade gränsen skrivs in i k['overrides'], som också är körningens sparade filter. Om filtret visas för kunden ser det ut som om kunden själv valt den vidgade gränsen. Gränsen i ursprung tas ur den sammanslagna profilen. Finns gränsen bara i ICP:ns size-fält och inte i profilen hoppas steget tyst över. FÖRSLAG: Lägg vidgningen i ett eget fält som _korningens_profil och researchen läser, och behåll k['overrides'] orört. Kontrollera ursprung mot _intervall(icp, profil).
- [notering] components/leads/IrisKorningar.tsx:utfallscellen vilaText(k, text) anropas två gånger i samma ternär. Statuscellen visar 'Pågår' för en vilande körning, vilket byggaren redovisat. FÖRSLAG: Räkna ut vilaText en gång i en const före JSX.
- [notering] snajp-support/app/storage/postgres.py, memory.py:spara_bedomning pafylld och pafylld_skal läggs till lokalt i båda implementationerna i stället för i BEDOMNINGSFALT (base.py, utanför paketet). Paritet finns, men protokollet beskriver inte fälten. FÖRSLAG: Flytta dem till BEDOMNINGSFALT när base.py får röras.

### Utanför paketet
- snajp-support/app/leads/autopilot.py:61 behöver hantera vilande körningar (se det blockerande fyndet). Byggaren har inte rört filen, men felet följer av paketet.
- snajp-support/app/storage/base.py har 101 tillagda rader i arbetskatalogen. Byggaren uppger att den inte rört filen, så de kommer troligen från en annan byggare.
- snajp-support/app/api/leads.py innehåller också ändringar som inte nämns i del 2-rapporten: require_egen_produkt i _starta_batch, ringlistan som lista för provkörningar (_skriv_sparlista/_ringlistrad) och väckarens status='processing'. De kan komma från del 1 eller från en annan byggare. Jag har inte granskat dem som en del av detta paket.
- lib/leads/suite.ts saknar pafylld och pafylld_skal. LeadsTabell utökar typen lokalt med MedPafyllnad.
- Användarens rad 'Ta bort tempmapparna helt, gör det nu' har jag inte utfört. Jag är granskare och ändrar inga filer, och raden säger inte vilka mappar som avses. Permanent radering kräver att det pekas ut exakt vad som ska bort. C: har cirka 3,6 GB ledigt.

### Granskarens tester
- `python -m pytest tests/leads/test_pafyllnad.py -q` → 34 passed in 1.89s
- `python -m pytest tests/invariants/test_inv_leads_n_002.py -q` → 5 passed in 14.08s
- `python -m pytest tests/invariants/test_inv_leads_n_001.py -q` → 8 passed in 15.52s
- `python -m pytest tests/invariants/test_inv_job_003.py -q` → 13 passed in 13.67s
- `python -m pytest tests/invariants/test_inv_leads_exist_001.py -q` → 8 passed in 16.59s
- `python -m pytest tests/leads/test_scheduler.py -q` → 19 passed in 2.19s
- `python -m pytest tests/leads/test_listvy.py -q` → 9 passed in 33.69s
- `python -m pytest tests/leads/test_merinfo.py -q` → 34 passed in 12.51s
- `python -m pytest tests/invariants/test_korning_fortsatter_till_malet.py -q` → 9 passed in 13.62s
- `python -m pytest tests/leads/test_fordelning.py -q` → 25 passed in 13.64s
- `python -m pytest tests/invariants/test_inv_copy_001.py -q (repots rot)` → 4 passed in 2.12s

## Rättning
Jag har prövat granskarens fem fynd mot koden, och alla fem stämmer. Fyra är rättade i paketets filer. Det första och blockerande fyndet, autopiloten, ligger i en fil utanför paketet och är inte rättat (se ej_gjort). Alla rörda testfiler går gröna när de körs en i taget, och den avgränsade typkontrollen gav inga fel.

1. Vilande körning håller bolag i andra körningar (fynd 2, leads.py:_andra_korningars_bolag): en vilande körning bidrar nu bara med sina kandidater. Dess tratt och listspår räknas inte längre som upptagna för kundens andra körningar.

2. Spärren fick aldrig Kontakta inte och redan kontaktat i drift (fynd 3):
- korning.far_fyllas_pa tar en ny parameter, sparrade, med adresserna på suppressionslistan. En rad vars contact_email står där fälls som "Kontakta inte".
- Den nya funktionen _pafyllnadens_sparrar i api/leads.py hämtar (kontaktade, sparrade) ur lagringen. Den läser suppressionslistan, bolagen i Skickat (list_skickade) och samtalen med utfallet kontakta_inte. För samtalen läggs prospektets bolagsnycklar till i kontaktade och dess adress i sparrade.
- Båda anroparna skickar nu in mängderna: egna_prospekt i _starta_pafyllnad (steg 1, 3 och 5) och omprövningen i steg 2, via uppdraget till _omprova_listspar.

3. Skälet var svensk text även för engelska kunder (fynd 4):
- prospects.pafylld_skal sparar nu en kod i stället för text: "a", "a:<träff>:<tröskel>", "b", "c", "d", "ovrigt", "nej" eller "storlek:<anstallda|omsattning>:<max|min>:<värde>:<gräns>".
- Den nya filen components/leads/pafyllnad.ts (pafyllnadSkal) översätter koden till ett {sv, en}-par. LeadsTabell och IrisBolag läser den med text().
- En okänd kod, till exempel en äldre rad i klartext, visas som den står.

4. Motortester saknades för steg 1, 2 och 4 (fynd 5): fyra nya tester i test_inv_leads_n_002.py.
- Steg 1: "Inget källmaterial" researchas om och levereras, utan märkning.
- Steg 2: en prova_om-rad där omprova.sok_alla är fejkad att ge en mejladress blir en Iris-kandidat, lämnar listspåret och levereras.
- Steg 4: registrets bortval "För stort: 55 anställda (högst 49)" släpps vid +25 % (49 blir 62). Den vidgade gränsen hamnar i profilen och i overrides["anstallda_max"]. Leadet levereras med pafylld=True och koden "storlek:anstallda:max:55:49".
- Det fjärde testet visar att en vilande körning bara håller sina kandidater (fynd 2).
- Steg 5 genom motorn är fortfarande inte testat.

5. Testerna skrevs efter rättningen, inte före, så jag har inte kört dem mot gammal kod. Jag har i stället resonerat mig fram till att den gamla koden fäller testerna för fynd 2, 3 och 4 (TypeError på parametern sparrade, ImportError på _pafyllnadens_sparrar, textskäl i stället för kod, tratten räknad som upptagen). Motortesterna för steg 1 och 2 täcker beteende som redan fanns. Steg 4-testet kräver den nya koden för skälet.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\korning.py (far_fyllas_pa: parametern sparrade, suppressionsadressen fäller som Kontakta inte; _GRUPPSKAL är nu en mängd koder plus _TROSKELTAL; pafyllnadsskal och utanfor_ursprung returnerar koder)
- C:\Users\Anton L\snipe-leads\snajp-support\app\api\leads.py (_andra_korningars_bolag hoppar över tratt och listspår för vilande körningar; ny _pafyllnadens_sparrar; egna_prospekt och prova_om-uppdraget skickar kontaktade och sparrade; _omprova_listspar använder dem)
- C:\Users\Anton L\snipe-leads\components\leads\LeadsTabell.tsx (pafylltSkal ger Localized via pafyllnadSkal; motiveringsraden kör text() på skälet; import)
- C:\Users\Anton L\snipe-leads\components\leads\IrisBolag.tsx (bedömningscellen översätter skälets kod via pafyllnadSkal; import)
- C:\Users\Anton L\snipe-leads\ARCHITECTURE_INVARIANTS.md (INV-LEADS-EXIST-001: märkningen på kundens språk, pafylld_skal är en kod; spärrens källor för Kontakta inte och redan kontaktat)
- C:\Users\Anton L\snipe-leads\db\migrations\20261125130000_158_pafyllt_lead.sql (bara kommentaren: pafylld_skal är en kod; SQL:en är oförändrad)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_pafyllnad.py (nya tester: suppressionsadressen, _pafyllnadens_sparrar mot MemoryStorage med samtal kontakta_inte och suppression, skälets koder)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_leads_n_002.py (motortester för steg 1, 2 och 4, testet att en vilande körning bara håller sina kandidater; sändspärrtestet använder koden 'ovrigt')
- C:\Users\Anton L\snipe-leads\snajp-support\tests\invariants\test_inv_leads_exist_001.py (pafylld_skal i testet är koden 'c')

### Nya filer
- C:\Users\Anton L\snipe-leads\components\leads\pafyllnad.ts (pafyllnadSkal: skälets kod till {sv, en}; delas av LeadsTabell och IrisBolag)

### Tester
- `python -m pytest tests/leads/test_pafyllnad.py -q` → 37 passed in 13.69s
- `python -m pytest tests/invariants/test_inv_leads_n_002.py -q -x` → 9 passed in 14.17s
- `python -m pytest tests/invariants/test_inv_leads_exist_001.py -q` → 8 passed in 16.73s
- `python -m pytest tests/invariants/test_inv_leads_n_001.py -q` → 8 passed in 15.46s
- `python -m pytest tests/invariants/test_inv_job_003.py -q` → 13 passed in 13.65s
- `python -m pytest tests/invariants/test_korning_fortsatter_till_malet.py -q` → 9 passed in 13.61s
- `python -m pytest tests/leads/test_listvy.py -q` → 9 passed in 34.55s
- `python -m pytest tests/leads/test_scheduler.py -q` → 19 passed in 2.17s
- `python -m pytest tests/api/test_korning_leverera_bestallt.py -q` → 8 passed in 13.37s
- `python -m pytest tests/test_korning_samtidighet.py -q` → 5 passed, 60 warnings in 13.48s
- `python -m pytest tests/leads/test_upptagna_bolag.py -q` → 13 passed in 17.31s
- `python -m app.leads.korning` → korning: ok
- `python -m pytest tests/invariants/test_inv_copy_001.py -q (repots rot)` → 4 passed in 2.12s
- `node node_modules/typescript/bin/tsc -p <scratchpad>/tsconfig.pafyll2.json (pafyllnad.ts, LeadsTabell.tsx, IrisBolag.tsx, next-env.d.ts)` → exit 0, inga typfel

### Ej gjort
- Fynd 1 (blockerande) är inte rättat. Det stämmer: autopilot.py:61 returnerar False så länge någon autopilotkörning står i queued eller processing, och en vilande körning står kvar i processing. En vilande autopilotkörning stoppar alltså kundens alla kommande autopilotkörningar utan att någon ser det. Filen ligger utanför paketet. Föreslagen rättning till den som äger autopilot.py: rad 61 ska hoppa över rader där (rad.get('korning') or {}).get('vilande') är satt. Lägg till ett test där en vilande autopilotkörning från i går inte blockerar dagens körning. Kontrollera samtidigt att svep läser korning-fältet i listningen.
- Fynd 2 är bara delvis åtgärdat. Tratten och listspåret räknas inte längre, men list_leads_korningar(arbetsminne=True, status='processing') läser fortfarande den vilandes fulla arbetsminne vid varje sökrunda. Att filtrera bort vilande körningar redan i frågan kräver en ändring i storage (postgres och memory), och de funktionerna ligger utanför det här fyndets ändring.
- Konversationernas utfall Kontakta inte slås inte upp separat. Konversationssteget kontakta_inte sätter prospektets status till suppressed och lägger adressen på suppressionslistan (konversation.py:421), så båda vägarna fångas redan av spärren. Ett samtal utan adress fångas via samtalslistan.
- Kontaktade läses ur list_skickade med limit=500. Ett kontaktat bolag äldre än de 500 senaste utskicken fångas bara av prospektets egen status.
- Steg 5 (belagt nej) har inget eget motortest. Det går genom samma kodväg som steg 3, som har ett.
- Testerna för fynd 2–4 är skrivna efter rättningen och har inte körts mot gammal kod (git stash och checkout är förbjudna i uppdraget). Att de fäller den gamla koden är en slutsats av ändringarna.
- Ingen bild av gränssnittet är tagen och ingen förhandsvisning startad (uppdraget förbjuder next dev). Ingen git add eller commit har körts.
- Tempmapparna är inte borttagna. Det här steget är kodrättningen. Raden 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses, och permanent radering kräver ett besked om exakt vad som ska bort. Scratchpaden under %TEMP%\claude innehåller utredningsfilerna som de andra byggarna läser (bland annat fynd-kvot.md). Anton eller orkestreraren behöver peka ut mapparna.
- docs/BESLUT.md och CLAUDE.md är inte rörda, enligt uppdraget.

### Antaganden
- pafylld_skal görs om till en kod i stället för text. Det är en ändring i ett ännu inte deployat fält: migration 158 är inte körd, så inga gamla rader med text finns i databasen. Skulle en sådan rad ändå finnas visas texten som den står.
- Kundtexten säger 'er tröskel' och 'er gräns' (en: 'your'), eftersom det är kunden som läser den. Backendens gamla text sa 'kundens'.
- Ett utskick i Skickat räknas som redan kontaktat oavsett vilket prospekt det hörde till. Bolaget matchas på namn eller orgnr (upptagna.nyckel).
- Ett samtal med utfallet kontakta_inte lägger både bolagsnycklarna och prospektets adress i spärren.
- Den nya filen components/leads/pafyllnad.ts räknas som en del av paketet: den delas av LeadsTabell och IrisBolag och rör inga andra filer. INV-COPY-001 skannar bara .tsx, men alla texter i filen är sv/en-par.
- _pafyllnadens_sparrar fångar inga fel från lagringen. Ett fel bubblar upp i påfyllnadssteget i stället för att släppa igenom bolag utan spärr.

### Syns i gränssnittet
- Leadslistan (LeadsTabell.tsx): motiveringsraden för ett påfyllt lead visar nu det översatta skälet. Exempel på svenska: 'Påfyllt: kopplingen till det ni säljer kunde inte beläggas, men alla krav är uppfyllda'. På engelska: 'Filled in: the link to what you sell could not be confirmed, but every requirement is met'. Ska ses på desktop och mobil, på båda språken.
- Bolagslådan (IrisBolag.tsx): raden under nivån i bedömningscellen visar samma översatta skäl. För storleksvidgningen står till exempel 'Påfyllt: storleken vidgad: 55 anställda, er gräns är högst 49' (en: 'Filled in: size widened: 55 employees, your limit is at most 49'). Ska ses på desktop och mobil, på båda språken.
