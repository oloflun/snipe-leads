
# leads-korning-1
granskning godkänd=True
  [bor_rattas] ARCHITECTURE_INVARIANTS.md: INV-LEADS-N-001 säger fortfarande att körningen slutar när 'poolen, taket (4×N undersökta) eller dygnsbudgeten tar slut'. Beteendet är nu ändrat: taken förlängs och TOMMA_RUNDOR är det enda målgruppsslutet. INV-JOB-003 nämner inte heller at
  [bor_rattas] snajp-support/app/storage/postgres.py: Undantaget i stada_hangande_leadsjobb saknar en yttersta gräns. En batchrad med klar≠true, kalla≠lista och pagaende=0 fälls aldrig, oavsett hur länge den varit tyst. Om väckaren inte kan driva den, ligger den kvar som 'Pågår' för alltid. De
  [utanför] snajp-support/app/api/leads.py, hunken i _starta_batch (require_egen_produkt, 422 för research_and_draft): den hör till paketet utkast-onboarding och inte till byggaren av leads-korning-1.
  [utanför] snajp-support/tests/api/test_kb_seedning.py är ändrad i arbetskatalogen. Den hör till ett annat paket.
  [utanför] ARCHITECTURE_INVARIANTS.md (INV-LEADS-N-001, INV-JOB-003) behöver ny text. Orkestreraren skriver den.
  [utanför] components/leads/IrisKorningar.tsx (SLUT_ETIKETT 'tak') och listtabellens visning av extra.anstallda (regel 15) behöver kontrolleras i bild.
  [utanför] docs/BESLUT.md och CLAUDE.md regel 15/17 (provkörningens ringlista ligger under Listor, taken är larm). Orkestreraren skriver dem.
  [utanför] Den vidarebefordrade raden 'Ta bort tempmapparna helt, gör det nu' har jag inte utfört. Jag är granskare och ändrar inga filer, och raden säger inte vilka mappar som avses. Permanent radering kräver att Anton bekräftar exakt vad som ska bor
rättning: Granskarens fynd 2 (städarens undantag saknade en yttersta gräns) stämde mot koden och är rättat. Fynd 1 (ARCHITECTURE_INVARIANTS.md) ligger utanför paketet och lämnas till orkestreraren. Två nya tester skrevs först och fällde dagens kod (2 failed, 11 passed). Därefter rättades stada_hangande_leadsjobb i postgres.py och memory.py. Undantaget för väckbara körningar gäller nu bara status 'processing', alltså det väckaren läser, och bara om updated_at ligger inom den nya konstanten stadare.VACKNING_RESERV_MINUTER (24 h). En köad rad med korning-objekt och en väckbar rad som varit tyst längre än ett dygn fälls nu med error=HANGFEL_JOBB. De rörda testfilerna går gröna.
  ej gjort (bygge): Tempmapparna är inte borttagna. Användarens rad 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses, och permanent radering kräver ett uttryckligt besked om vad som ska bort. Scratchpaden innehöll dessutom utredningsfi
  ej gjort (bygge): ARCHITECTURE_INVARIANTS.md är inte ändrad (filen ligger utanför paketet). INV-LEADS-N-001 (rad 904-910) säger fortfarande att körningen slutar när 'poolen, taket (4×N undersökta) eller dygnsbudgeten tar slut'. Föreslagen text: körningen fyl
  ej gjort (bygge): base.py (protokollet) har inte rörts. Därför fick list_leads_korningar ingen scope-parameter (INV-STORE-001 kräver identisk signatur). Väckaren läser status='processing' med limit=500 och filtrerar scope='batch' i Python.
  ej gjort (bygge): Frontend är inte ändrad (utanför paketet). IrisKorningar.tsx SLUT_ETIKETT['tak'] säger fortfarande 'fyra gånger så många', fast slutet 'tak' inte längre uppstår. Listvyn för leadslistor visar troligen inte extra.anstallda, och regel 15 ('an
  ej gjort (bygge): docs/BESLUT.md och CLAUDE.md (regel 15/17: provkörningens ringlista ligger under Listor; taken är larm) är inte uppdaterade. Orkestreraren skriver dem.
  ej gjort (bygge): Skarpa körningar skapar fortfarande ringprospekt med origin 'ring'. Det väntar på Antons beslut om Samtal › Ringlista, enligt uppdraget.
  ej gjort (bygge): Kredittak och sokningen_foll avslutar som förut. Att göra dem vilande hör till del 2.
  ej gjort (bygge): De 36 befintliga demoraderna är inte rörda i databasen (ingen databas får röras). Skyddet i listvy.synliga döljer dem i leadslistan och nyckeltalet.
  ej gjort (bygge): Postgres-SQL:en i stada_hangande_leadsjobb och weekly_analytics är inte körd mot en riktig databas, bara speglad och testad i MemoryStorage.
  ej gjort (bygge): Ingen TypeScript rördes, så ingen tsc-kontroll kördes.
  ej gjort (rättning): Fynd 1 är inte rättat, eftersom ARCHITECTURE_INVARIANTS.md ligger utanför paketet. Orkestreraren behöver skriva om INV-LEADS-N-001 enligt byggarens tidigare förslag. INV-JOB-003 behöver en mening om tre saker: städaren skriver HANGFEL_JOBB 
  ej gjort (rättning): Tempmapparna är inte borttagna. Raden 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses. Den sitter i samma meddelande som beskedet att en worktree inte kunde skapas på grund av diskbrist (4,2 GB ledigt, 5,4 GB krävs
  ej gjort (rättning): SQL:en i postgres.py är inte körd mot en riktig databas (ingen databas får röras). Den är speglad i MemoryStorage och testad där.
  ej gjort (rättning): Ingen TypeScript rördes, så ingen tsc kördes.
  syns: En Iris-körning som väckaren inte fått i gång på ett dygn, eller som fastnat i status 'queued', visas nu som Misslyckades med städarens felmening (HANGFEL_JOBB) i stället för att stå kvar som Pågår för alltid. Det ser ut som en vanlig fälld
  TEST: python -m pytest tests/invariants/test_inv_job_003.py -q (i snajp-support, före rättningen) → 2 failed, 11 passed in 18.78s

# leads-korning-2
granskning godkänd=False
  [blockerande] snajp-support/app/leads/autopilot.py (orsakas av api/leads.py:_fyll_pa_last + korning.vila): En vilande körning står kvar i status 'processing' tills den når målet. autopilot.ska_kora returnerar False så länge någon autopilotkörning har status queued/processing. Det betyder att en enda autopilotkörning som lägger sig att vila (smal
  [bor_rattas] snajp-support/app/api/leads.py: En vilande körning har status processing och klar=false, så _andra_korningars_bolag fortsätter att räkna hela dess tratt (även tusentals registerbortval, som annars inte står sig mellan körningar), dess kandidater och dess listspår som uppt
  [bor_rattas] snajp-support/app/leads/korning.py: Spärren fäller 'Kontakta inte' bara på fälten utfall och kontakta_inte, som en prospektrad inte har, samt på status suppressed. Suppressionslistan och samtalens eller konversationernas utfall kontakta_inte slås aldrig upp. 'Redan kontaktat'
  [bor_rattas] snajp-support/app/leads/korning.py: pafylld_skal är fasta svenska strängar som kunden ser i LeadsTabell och IrisBolag efter 'Filled in:'. En engelsk användare läser alltså 'Filled in: kopplingen till det kunden säljer kunde inte beläggas…'. Uppgiften kräver att varje användar
  [bor_rattas] snajp-support/tests/invariants/test_inv_leads_n_002.py: Bara steg 3 körs genom motorn. Steg 1 (att researcha om tjänstefelen och köra om fallna sökrundor), steg 2 (omprövningen via _omprova_listspar och _sla_in_sokrunda) och steg 4 (den vidgade sökrundan, fria namn ur uteslutningen, overrides ti
  [utanför] snajp-support/app/leads/autopilot.py:61 behöver hantera vilande körningar (se det blockerande fyndet). Byggaren har inte rört filen, men felet följer av paketet.
  [utanför] snajp-support/app/storage/base.py har 101 tillagda rader i arbetskatalogen. Byggaren uppger att den inte rört filen, så de kommer troligen från en annan byggare.
  [utanför] snajp-support/app/api/leads.py innehåller också ändringar som inte nämns i del 2-rapporten: require_egen_produkt i _starta_batch, ringlistan som lista för provkörningar (_skriv_sparlista/_ringlistrad) och väckarens status='processing'. De k
  [utanför] lib/leads/suite.ts saknar pafylld och pafylld_skal. LeadsTabell utökar typen lokalt med MedPafyllnad.
  [utanför] Användarens rad 'Ta bort tempmapparna helt, gör det nu' har jag inte utfört. Jag är granskare och ändrar inga filer, och raden säger inte vilka mappar som avses. Permanent radering kräver att det pekas ut exakt vad som ska bort. C: har cirk
rättning: Jag har prövat granskarens fem fynd mot koden, och alla fem stämmer. Fyra är rättade i paketets filer. Det första och blockerande fyndet, autopiloten, ligger i en fil utanför paketet och är inte rättat (se ej_gjort). Alla rörda testfiler går gröna när de körs en i taget, och den avgränsade typkontrollen gav inga fel.

1. Vilande körning håller bolag i andra körningar (fynd 2, leads.py:_andra_korningars_bolag): en vilande körning bidrar nu bara med sina kandidater. Dess tratt och listspår räknas inte längre som upptagna för kundens andra körningar.

2. Spärren fick aldrig Kontakta inte och redan kontaktat i drift (fynd 3):
- korning.far_fyllas_pa tar en ny parameter, sparrade, med adresserna på suppressionslista
  ej gjort (bygge): Tempmapparna är inte borttagna. Användarens rad 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses. Permanent radering kräver ett besked om exakt vad som ska bort. Scratchpaden under %TEMP%\claude innehåller dessutom 
  ej gjort (bygge): Ingen bild av gränssnittet är tagen, och inget är committat. Ingen git add eller commit har körts, enligt uppdraget.
  ej gjort (bygge): base.py rördes inte (utanför paketet), så BEDOMNINGSFALT saknar pafylld och pafylld_skal. postgres.py och memory.py lägger till fälten lokalt i spara_bedomning. Hör de hemma i protokollet ska de flyttas till BEDOMNINGSFALT.
  ej gjort (bygge): lib/leads/suite.ts rördes inte (utanför paketet). LeadsTabell utökar SuiteProspekt lokalt med typen MedPafyllnad.
  ej gjort (bygge): Inget integrationstest kör steg 2 (omprövningen anropar nätverket via omprova) eller steg 4 (storleksvidgningen med en vidgad sökrunda). Stegens ordning, tolkningen, vidgningen och märkningen 'storleken vidgad' är bara testade som rena funk
  ej gjort (bygge): Postgres-SQL:en (städarens undantag, de nya kolumnerna i projektion och UPDATE) är inte körd mot en riktig databas, bara speglad i MemoryStorage. Migration 158 är inte körd.
  ej gjort (bygge): docs/BESLUT.md och CLAUDE.md (regel 23 under § Leads) är inte uppdaterade. Orkestreraren skriver dem.
  ej gjort (bygge): Statuscellen i IrisKorningar visar fortfarande 'Pågår' för en vilande körning; utfallscellen bär '8 av 10, letar vidare: <skäl>'. SLUT_ETIKETT['tak'] ('fyra gånger så många') står kvar för gamla rader. 'Klar, under målet' står kvar som etik
  ej gjort (bygge): pafylld_skal skrivs på svenska i backend, som motivering och disqualifiers. Bara prefixet 'Påfyllt'/'Filled in' och vilans skäl är tvåspråkiga i frontend.
  ej gjort (bygge): Omsättningen vidgas bara i sökningens profil. context_pack._med_overrides (utanför paketet) tar inga omsättnings-overrides, men researchens bedömning fäller inte heller på omsättning.
  ej gjort (bygge): Fortsätt (_kan_fortsatta) är oförändrad. Den gäller bara gamla körningar som redan står klara eller fallna under målet.
  ej gjort (rättning): Fynd 1 (blockerande) är inte rättat. Det stämmer: autopilot.py:61 returnerar False så länge någon autopilotkörning står i queued eller processing, och en vilande körning står kvar i processing. En vilande autopilotkörning stoppar alltså kun
  ej gjort (rättning): Fynd 2 är bara delvis åtgärdat. Tratten och listspåret räknas inte längre, men list_leads_korningar(arbetsminne=True, status='processing') läser fortfarande den vilandes fulla arbetsminne vid varje sökrunda. Att filtrera bort vilande körnin
  ej gjort (rättning): Konversationernas utfall Kontakta inte slås inte upp separat. Konversationssteget kontakta_inte sätter prospektets status till suppressed och lägger adressen på suppressionslistan (konversation.py:421), så båda vägarna fångas redan av spärr
  ej gjort (rättning): Kontaktade läses ur list_skickade med limit=500. Ett kontaktat bolag äldre än de 500 senaste utskicken fångas bara av prospektets egen status.
  ej gjort (rättning): Steg 5 (belagt nej) har inget eget motortest. Det går genom samma kodväg som steg 3, som har ett.
  ej gjort (rättning): Testerna för fynd 2–4 är skrivna efter rättningen och har inte körts mot gammal kod (git stash och checkout är förbjudna i uppdraget). Att de fäller den gamla koden är en slutsats av ändringarna.
  ej gjort (rättning): Ingen bild av gränssnittet är tagen och ingen förhandsvisning startad (uppdraget förbjuder next dev). Ingen git add eller commit har körts.
  ej gjort (rättning): Tempmapparna är inte borttagna. Det här steget är kodrättningen. Raden 'Ta bort tempmapparna helt, gör det nu' säger inte vilka mappar som avses, och permanent radering kräver ett besked om exakt vad som ska bort. Scratchpaden under %TEMP%\
  ej gjort (rättning): docs/BESLUT.md och CLAUDE.md är inte rörda, enligt uppdraget.
  syns: Leadslistan (LeadsTabell.tsx): motiveringsraden för ett påfyllt lead visar nu det översatta skälet. Exempel på svenska: 'Påfyllt: kopplingen till det ni säljer kunde inte beläggas, men alla krav är uppfyllda'. På engelska: 'Filled in: the l
  syns: Bolagslådan (IrisBolag.tsx): raden under nivån i bedömningscellen visar samma översatta skäl. För storleksvidgningen står till exempel 'Påfyllt: storleken vidgad: 55 anställda, er gräns är högst 49' (en: 'Filled in: size widened: 55 employe

# utkast-onboarding
granskning godkänd=False
  [blockerande] snajp-support/app/agent/leads_research_v2.py: Beslut 2 kräver att require_egen_produkt anropas i run_outreach_draft_v2 OCH vid körstarten. Byggaren lade bara in spärren i _starta_batch (api/leads.py 3867-3873). Flera vägar skriver utkast utan att passera _starta_batch, så en kund med t
  [bor_rattas] snajp-support/app/leads/business_context.py: Beskedet har svenska och engelska i samma sträng ('… / Iris does not know …') och visas ordagrant i 422-svarets detail. En kund med svenskt gränssnitt får alltså båda språken på samma rad, och likadant för en kund med engelskt. INV-COPY-001
  [bor_rattas] lib/snajp/standard.ts: Spärren och produktraden hänger ihop. Äldre kunder vars sparade business_context.product saknar raden 'Vad vi säljer:' får ingen produktrad vid inloggning, och de stoppas nu av spärren vid sin nästa körning med utkast. Raden finns sedan 400
  [utanför] Inga ändringar utanför paketet hittades. Av api/leads.py hör bara spärrblocket i _starta_batch (rad 3867-3873) till paketet, och diffen i övrigt (134 rader) är en annan byggares. Inga filer i paketet rör webbrevisionen.
  [utanför] Den rättning som saknas (spärren i run_outreach_draft_v2) kräver en ändrad fixtur i tests/agent/test_leads_v2_wiring.py (_prepare_outreach). Filen är ett regressionstest enligt UTKASTKEDJAN-REFERENS § 7, så orkestreraren avgör.
  [utanför] Beskedet vid körstarten bör visas på kundens språk i components/leads/LeadsRunForm.tsx, som en annan byggare äger.
  [utanför] Användarens relä 'Ta bort tempmapparna helt, gör det nu' (diskutrymme för den misslyckade sessionen 'Snajp CRM: komplett svit efter Twenty, med API') är inte utfört här. Jag är granskare och ändrar inga filer, och vilka mappar som avses är 
rättning: Jag prövade granskarens tre fynd mot koden. Fynd 1 stämde och är rättat. Fynd 2 och 3 stämmer i sak, men de rättas inte här (skälen står i ej_gjort).

Fynd 1 (blockerande): require_egen_produkt anropas nu i run_outreach_draft_v2, direkt efter require_business_context. Spärren gäller alltså även för autopiloten, inkorgsleads, Processa om, Skapa om utkast och rena utkastjobb. Jag skrev först testet test_utkastet_stannar_fore_modellen_utan_produkt. Det fällde dagens kod (1 failed) och passerar efter rättningen. Det kontrollerar att felet kastas, att modellen inte anropas (llm.calls == []) och att inget hamnar i granskningskön. Båda vägarna i leads.py tar redan hand om felet: utkastjobbet blir failed med beskedet (
  ej gjort (bygge): Spärren require_egen_produkt anropas INTE i run_outreach_draft_v2, trots beslut 2. Anropet fällde 11 tester i tests/agent/test_leads_v2_wiring.py, vars fixturer saknar settings.produkter, och regressionen enligt § 7 ska passera oförändrad. 
  ej gjort (bygge): lib/snajp/testtenant.ts är inte ändrad. exempel_kb är förvalt falskt i backenden, och onboardingen kräver webbplats, så den ber aldrig om exempelbasen. Fältet behöver inte skickas.
  ej gjort (bygge): Nordlys-artiklar som redan ligger i testarbetsytor i produktion är inte raderade (kräver Antons ja, ingick inte).
  ej gjort (bygge): Kategorin salj, skanningen och context_pack (utredarens förslag 3 och 6) ingick inte i paketet.
  ej gjort (bygge): Ingen git add, commit eller push.
  ej gjort (bygge): Användarens relä "Ta bort tempmapparna helt, gör det nu" är inte utfört. Det gällde diskutrymmet för en annan session, uppgiften jag fick var bygget, och en radering av tempmappar under ett pågående arbete med delad scratchpad är permanent 
  ej gjort (rättning): Fynd 2 (beskedet bär svenska och engelska i samma sträng) är inte rättat. Fyndet stämmer. Rättningen kräver att 422-svarets detail och jobbets feltext blir en kod eller ett objekt, och att LeadsRunForm och jobbrutan översätter via useLocale
  ej gjort (rättning): Fynd 3a (äldre kunder utan raden 'Vad vi säljer:' får ingen produkt och stoppas nu av spärren) är inte rättat. Det som återstår är att räkna de berörda kunderna i drift, och det är en databasfråga som kräver Antons ja. Jag har inte rört någ
  ej gjort (rättning): Fynd 3b (en avsiktligt tömd produktlista fylls på igen vid inloggning) är inte rättat. Beteendet följer beslut 1 ordagrant ('bara när listan är tom … vid inloggning får de raden också') och samma regel som ICP:n. Med spärren kan en tom list
  ej gjort (rättning): Ingen git add, commit eller push.
  ej gjort (rättning): Användarens begäran 'Ta bort tempmapparna helt, gör det nu' är inte utförd. Det framgår inte vilka mappar som avses. Radering är permanent, och scratchpaden och arbetskatalogen delas just nu med tre andra byggare. Den bör göras av orkestrer
  syns: En kund utan produkt i Leads › Produkter som startar Skapa om utkast, Processa om eller ett enskilt utkastjobb får nu jobbet som misslyckat med beskedet 'Iris vet inte vilken av era produkter mejlen ska sälja … / Iris does not know …'. Det 
  syns: Oförändrat sedan förra granskningen, och fortfarande obesett: 422-beskedet vid körstarten i LeadsRunForm, produktraden ur 'Vad vi säljer' i Leads › Produkter, testarbetsytans namn och den tomma kunskapsbasen utan Nordlys.
  TEST: python -m pytest tests/leads/test_eget_erbjudande_sparr.py -q -k fore_modellen (före rättningen) → 1 failed, 5 deselected in 30.51s

# kunskapsbas-saljfakta
granskning godkänd=True
  [bor_rattas] components/settings/WebbplatsForslag.tsx: Beslut 3 är bara delvis uppfyllt. Säljfakta ska synas med kategorietikett i den befintliga förslagslistan, men förslagslistan renderas av WebbplatsForslag.tsx (importeras i Kunskapsbas.tsx rad 12, används rad 347). Den filen ingick inte i p
  [bor_rattas] app/forhandsvisning/: Ändringen syns i gränssnittet (etiketten i artikellistan), men det finns ingen förhandsvisning av Kunskapsbas under app/forhandsvisning/. Enligt CLAUDE.md får ändringen inte committas innan den har setts i bild på desktop och mobil.
  [utanför] snajp-support/app/api/schemas.py: diffen (fältet exempel_kb i CreateKeyRequest) hör till ett annat paket (Nordlys-seedningen), inte till kunskapsbas-saljfakta. Byggarens egen diff i filen är tom.
  [utanför] components/settings/WebbplatsForslag.tsx: behöver kategorietiketten för att beslut 3 ska uppfyllas, men låg utanför paketet och är inte rörd.
  [utanför] app/forhandsvisning/kunskapsbas/: saknas och behövs för att ändringen ska kunna ses i bild före commit.
  [utanför] docs/FALTKARTA.md och docs/BESLUT.md: den nya läsvägen från kunskapsbasen till leadskedjan och valet att inte rama in salj-texten bör dokumenteras där. Det gör orkestreraren.
  [utanför] Den vidarebefordrade begäran 'Ta bort tempmapparna helt, gör det nu' ligger utanför granskningssteget. Jag har inte utfört den och inte raderat något, eftersom den inte säger vilka mappar som avses.
rättning: Jag har prövat båda fynden mot koden och båda stämmer. components/settings/WebbplatsForslag.tsx visar ingen kategori, och under app/forhandsvisning/ finns ingen förhandsvisning (katalogen är tom för Kunskapsbas, kontrollerat med Glob). Båda filerna ligger utanför mitt paket, och granskaren säger själv att orkestreraren behöver ge ett paket som får röra dem. Därför har jag inte rättat dem. I paketet har jag gjort en sak: KATEGORI i Kunskapsbas.tsx exporteras nu, så att nästa paket kan visa samma etikett i förslagslistan utan att skapa en fjärde kopia. INV-COPY-001 går fortfarande igenom. Jag har inte raderat några tempmappar (se ej_gjort).
  ej gjort (bygge): Begäran 'Ta bort tempmapparna helt, gör det nu' är inte utförd. Den anger inte vilka mappar som avses. Den delade scratchpaden innehåller utredningen (fynd-kunskapsbas.md) som tre andra byggare arbetar mot just nu, och radering kan inte ång
  ej gjort (bygge): Förslagslistan: säljfakta visas med kategorietikett bara i artikellistan i Kunskapsbas.tsx. Förslagslistan renderas av components/settings/WebbplatsForslag.tsx, som ligger utanför mitt paket. Den visar ingen kategori i dag. Där behövs samma
  ej gjort (bygge): Filtret: Kunskapsbas.tsx och WebbplatsForslag.tsx har inget befintligt kategorifilter. Att lägga till ett hade varit en ny kontroll ovanpå ytan, vilket strider mot regeln 2026-11-24, så jag har inte byggt något. Om Anton vill ha ett filter 
  ej gjort (bygge): Ingen förhandsvisning under app/forhandsvisning/ finns för Kunskapsbas, och mitt paket fick inte lägga till en. Orkestreraren behöver en, till exempel app/forhandsvisning/kunskapsbas/page.tsx som renderar KunskapsbasPanel och besvarar /api/
  ej gjort (bygge): Ingen kategorivalidering i KbArticle (schemas.py). Jag provade en validator mot KB_CATEGORIES, men den fällde tests/api/test_kb_forslag.py::test_sparad_skanning_kompletterar_och_skriver_aldrig_over, som postar category 'allmant' mot MemoryS
  ej gjort (bygge): Supportagentens search_kb filtrerar inte bort salj-artiklar, så supportagenten kan citera dem, till exempel vid prisfrågor. Det är oförändrat och avsiktligt enligt utredarens förslag 3, men inget beslut i beställningen tar ställning till de
  ej gjort (bygge): kb.py behövde ingen ändring: förslag och tillägg går redan igenom oförändrad category. Varken ARCHITECTURE_INVARIANTS.md eller docs/BESLUT.md är ändrade. Ingen invariant beskriver kategorilistan i kunskapsbasen eller vad kontextpaketet läse
  ej gjort (bygge): Varken commit eller git add är gjorda, och migrationen är inte körd mot någon databas.
  ej gjort (rättning): Fynd 1, etiketten i WebbplatsForslag.tsx: fyndet stämmer, för filen har varken KATEGORI eller någon kategorietikett. Filen ligger utanför paketet och är därför inte ändrad. Nästa paket gör så här: i varje förslagsrad visas `loc.text(KATEGOR
  ej gjort (rättning): Fynd 1, filtret: inget befintligt kategorifilter finns i någon av filerna. Att bygga ett vore en ny kontroll ovanpå ytan och strider mot regeln 2026-11-24. Om det ska finnas ett filter är det Antons beslut.
  ej gjort (rättning): Fynd 2, förhandsvisningen: fyndet stämmer, för app/forhandsvisning/ har ingen Kunskapsbas-vy. Katalogen ligger utanför paketet och är inte skapad. Det som behövs är app/forhandsvisning/kunskapsbas/page.tsx. Den ska rendera KunskapsbasPanel 
  ej gjort (rättning): Begäran 'Ta bort tempmapparna helt, gör det nu' är inte utförd. Den säger inte vilka mappar som avses, och radering går inte att ångra. Den delade scratchpaden innehåller dessutom utredningen som andra byggare arbetar mot just nu, och i arb
  ej gjort (rättning): Jag har inte kört om den avgränsade tsc-kontrollen. Ändringen lägger bara till ett export-nyckelord på en befintlig konstant och påverkar inga typer.
  ej gjort (rättning): Varken commit eller git add är gjord.
  syns: Inget nytt syns i den här rundan, eftersom exporten inte ändrar hur något renderas. Det som redan syns sedan förra rundan gäller fortfarande: i Inställningar › Kunskapsbas, listan 'I kunskapsbasen (n)', står kategorin som en grå etikett eft

# identitet-och-bakat
granskning godkänd=False
  [blockerande] components/AppShell.tsx, components/auth/OnboardingWizard.tsx (utanför paketet, följd av lib/actions/auth.ts): signOut returnerar nu Promise<{ url: string }> och loggar ut med redirect:false. De två filerna använder fortfarande <form action={signOut}>. Det ger TS2322 (byggfel), och i drift blir användaren kvar på sidan, utloggad och utan omdirigerin
  [bor_rattas] ARCHITECTURE_INVARIANTS.md (utanför paketet): INV-SEC-014 och INV-AUTH-002 har nya tester men ingen post i ARCHITECTURE_INVARIANTS.md, och INV-SEC-011 har fått en ny vakt utan att invariantens text ändrats. Uppgiften kräver att text och test ändras i samma arbete.
  [bor_rattas] tests/e2e/kundresa.spec.ts: Tvåfliksfallet byter cookies direkt i kontexten och loggar inte in admin i flik B, som uppgiften beskrev. Det prövar jämförelsen vid mjuk navigering men inte BroadcastChannel-vägen. Testet har dessutom en verklig adminadress (snajpsupport@g
  [utanför] components/AppShell.tsx: <form action={signOut}> på rad 443 och 509 måste bli loggaUtOchOppna i samma commit (byggfel och utloggning utan omdirigering).
  [utanför] components/auth/OnboardingWizard.tsx: <form action={signOut}> på rad 630 och 709, samma ändring.
  [utanför] ARCHITECTURE_INVARIANTS.md: nya poster INV-SEC-014 och INV-AUTH-002 och tillägg i INV-SEC-011.
  [utanför] docs/BESLUT.md: 404 → /dashboard för en icke-admin på /admin, anonym besökare på /admin till /login, hård navigering vid identitetsbyte (formulären kräver nu JS).
  [utanför] app/cookies/CookiesSida.tsx rad 241 nämner fortfarande snipra:korning:kund och snipra:korning:admin. Nycklarna heter nu snipra:korning:<identitet> (tvåspråkig text).
  [utanför] lib/auth/admin.ts rad ~50 (dokumentkommentar) säger fortfarande att /admin/layout.tsx svarar 404. Inaktuellt efter ändringen.
  [utanför] lib/http/json.ts (punkt 10, valfri) är inte gjord: 401 till /login?next= och en egen tvåspråkig 403-text.
  [utanför] Den vidarebefordrade användarbegäran 'Ta bort tempmapparna helt' har inte utförts. Granskaren ändrar inga filer, och scratchpaden under Temp innehåller utredningsfilerna och byggarens tsconfig. Orkestreraren får avgöra när och vilka mappar 
rättning: Jag har rättat det enda fyndet som låg inom paketet, i tests/e2e/kundresa.spec.ts. Tvåfliksfallet har inte längre någon riktig adminadress som standardvärde. Både adressen och lösenordet läses nu ur QA_ADMIN_EPOST och QA_ADMIN_LOSEN, och testet hoppas över om någon av dem saknas. Jag lade också till ett nytt e2e-test som prövar kanalvägen. I det loggar admin in i flik B i SAMMA kontext, och flik A ska ladda om utan att själv navigera, via BroadcastChannel("snajp-identitet").

De två andra fynden gäller filer utanför paketet: AppShell.tsx och OnboardingWizard.tsx (blockerande), samt ARCHITECTURE_INVARIANTS.md. Enligt granskarens förslag ska orkestreraren ändra dem, så jag har inte rört dem. Det blockerande fynde
  ej gjort (bygge): MÅSTE GÖRAS I SAMMA COMMIT, annars kompilerar inte appen: components/AppShell.tsx (rad 25, 443, 509) och components/auth/OnboardingWizard.tsx (rad 9, 630, 709) använder fortfarande <form action={signOut}>. Filerna ligger utanför mitt paket,
  ej gjort (bygge): ARCHITECTURE_INVARIANTS.md har jag inte rört (utanför paketet), fast regeln kräver att invariantens text ändras i samma arbete. Tre saker behövs: en ny post INV-SEC-014 (identitetsbyte; test tests/invariants/test_inv_sec_014.py), en ny post
  ej gjort (bygge): docs/BESLUT.md har jag inte rört (orkestreraren skriver den). Tre beslut ska in där: att 404 för en inloggad icke-admin på /admin ersattes av en omdirigering till /dashboard (Antons krav 2026-11-24), att en anonym besökare på /admin/** nu s
  ej gjort (bygge): app/cookies/CookiesSida.tsx (utanför paketet) nämner fortfarande localStorage-nycklarna snipra:korning:kund och snipra:korning:admin. De heter nu snipra:korning:<identitet>, så texten bör uppdateras.
  ej gjort (bygge): Punkt 10 i lib/http/json.ts (401 leder till /login?next=, egen tvåspråkig 403-text) är inte gjord. Den var valfri, och 401-vägen täcks nu av identitetskontrollen för alla inloggade träd: en utgången session ger identiteten för utloggad, fli
  ej gjort (bygge): Ingen visuell granskning. Inget nytt syns i gränssnittet (se syns_i_granssnittet), men omdirigeringarna och omladdningarna behöver prövas i en körande app.
  ej gjort (bygge): Ingen eslint-körning, för att spara minne. Den extra beroendet på pathname och sokning i useEffect i Identitetskontroll är avsiktlig.
  ej gjort (bygge): E2e-testerna är skrivna men inte körda, som uppdraget sa. Tvåfliksfallet hoppas över utan QA_ADMIN_LOSEN och förutsätter ett adminkonto utan tvåfaktor i lokal_stack.
  ej gjort (bygge): Ingen git add eller commit.
  ej gjort (bygge): Den vidarebefordrade begäran om att ta bort tempmapparna ingick inte i det här byggsteget, och jag har inte rört dem. Tänk på att utredningsfilerna och tsconfig för typkontrollen ligger i scratchpaden under Temp.
  ej gjort (rättning): Fynd 1 (blockerande) gäller components/AppShell.tsx (rad 25, 443, 509) och components/auth/OnboardingWizard.tsx (rad 9, 630, 709). Båda ligger utanför paketet, och enligt granskarens förslag ändrar orkestreraren dem i samma commit. Ändringe
  ej gjort (rättning): Fynd 2: ARCHITECTURE_INVARIANTS.md ligger utanför paketet, och docs/BESLUT.md skriver orkestreraren. Där behövs nya poster för INV-SEC-014 och INV-AUTH-002 och ett tillägg i INV-SEC-011. I BESLUT.md behövs tre rader: en inloggad icke-admin 
  ej gjort (rättning): Inga e2e-tester körda (kräver lokal stack).
  ej gjort (rättning): Den vidarebefordrade begäran att ta bort tempmapparna har jag inte utfört. Det framgår inte vilka mappar som avses. En permanent radering kräver ett bekräftat mål, och den kan inte göras från det här byggsteget eftersom andra byggare arbeta
  ej gjort (rättning): Ingen git add eller commit.
  syns: Inget nytt i den här rättningen: bara e2e-testet har ändrats.
  syns: Det som fortfarande ska ses i en körande app är oförändrat från paketet: omdirigeringarna på /admin, inloggningen när man går bakåt efter utloggning, de hårda omladdningarna vid in- och utloggning och vybyte, och tvåfliksfallet med kund i f