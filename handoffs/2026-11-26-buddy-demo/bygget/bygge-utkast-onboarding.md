# paket utkast-onboarding

## Bygge
Paketet (utkast och onboarding) låg redan nästan färdigt i arbetskatalogen när jag började, troligen från en tidigare körning av samma paket. Det gäller beslut 1, 3, 4 och 5 och spärren vid körstarten i beslut 2. Jag gick igenom varje diff mot besluten och körde alla tester en fil i taget. Allt är grönt.

Det enda som saknades var att spärren också anropas i run_outreach_draft_v2. Jag skrev ett test som fällde dagens kod och lade in anropet, men då föll 11 av 20 tester i tests/agent/test_leads_v2_wiring.py. Deras fixturer saknar produktlista, och regressionen enligt § 7 ska passera oförändrad. Jag tog därför bort både anropet och testet igen. Nettot i den här körningen är alltså ingen kodändring, bara verifiering. Spärren gäller vid körstarten (POST /api/leads/runs/batch med scope research_and_draft svarar 422 med beskedet på svenska och engelska). Vill orkestreraren ha spärren även i run_outreach_draft_v2 måste fixturerna i wiring-testet få en produkt. Det beslutet är orkestrerarens.

Det som finns i arbetskatalogen och som jag har granskat:
- standard.ts: forstaProdukt skriver settings.produkter ur "Vad vi säljer", men bara när listan är tom, och fältet utfall.produkter finns. provisionering.ts loggar nu när utfall.produkter är sant.
- business_context.py: require_egen_produkt med beskedet EGEN_PRODUKT_SAKNAS.
- api/leads.py: anropet vid körstarten, rad 3868-3873.
- stilkontroll.py: fyndet snajp_produkt_hos_kund, som stoppar köningen i run_outreach_draft_v2.
- leads-systemprompt.md rad 13: Supportagenten och Kvittohanteraren står i förbudslistan.
- Exempelbasen: schemas.py har fältet exempel_kb, förvalt falskt. keys.py seedar bara när det är satt. inbox.py seedar bara när basen är tom och ingen skanning finns.
- onboarding.ts: testtenanten får företagsnamnet.

Adminvyernas testmärke läses ur sluggen (lib/admin/statistik.ts:arTestyta, components/admin/Kundtabell.tsx), aldrig ur namnet.

### Ändrade filer
- Ingen nettoändring i den här körningen: anropet i C:\Users\Anton L\snipe-leads\snajp-support\app\agent\leads_research_v2.py och testet i C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_eget_erbjudande_sparr.py lades till och togs bort igen. Filerna står som före körningen.
- Redan ändrade i arbetskatalogen och granskade av mig (paketets diff): C:\Users\Anton L\snipe-leads\lib\snajp\standard.ts, C:\Users\Anton L\snipe-leads\lib\snajp\provisionering.ts, C:\Users\Anton L\snipe-leads\lib\actions\onboarding.ts, C:\Users\Anton L\snipe-leads\snajp-support\app\api\keys.py, C:\Users\Anton L\snipe-leads\snajp-support\app\api\schemas.py, C:\Users\Anton L\snipe-leads\snajp-support\app\api\inbox.py, C:\Users\Anton L\snipe-leads\snajp-support\app\scripts\seed_kb.py, C:\Users\Anton L\snipe-leads\snajp-support\app\leads\business_context.py, C:\Users\Anton L\snipe-leads\snajp-support\app\leads\stilkontroll.py, C:\Users\Anton L\snipe-leads\snajp-support\app\agent\leads_research_v2.py (bara snajpfynd-grinden före köningen), C:\Users\Anton L\snipe-leads\agent-core\prompts\leads-systemprompt.md, C:\Users\Anton L\snipe-leads\snajp-support\app\api\leads.py (bara rad 3868-3873 hör till paketet), C:\Users\Anton L\snipe-leads\snajp-support\tests\api\test_kb_seedning.py

### Nya filer
- Fanns redan i arbetskatalogen (ospårade), granskade och körda: C:\Users\Anton L\snipe-leads\lib\snajp\standard.test.ts
- C:\Users\Anton L\snipe-leads\lib\actions\onboarding.test.ts
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_eget_erbjudande_sparr.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_stilkontroll_snajp_produkt.py
- Tillfällig tsconfig (inte i repot): C:\Users\ANTONL~1\AppData\Local\Temp\claude\20bc186535c3c092\fd9b0b93-e92d-4cea-a78c-7ea782ace803\scratchpad\tsconfig.pkt.json

### Tester
- `python -m pytest tests/leads/test_eget_erbjudande_sparr.py -q -k fore_modellen (mitt nya test, före rättningen)` → 1 failed, 5 deselected in 24.54s (fäller dagens kod: når modellanropet)
- `python -m pytest tests/agent/test_leads_v2_wiring.py -q (med spärren i run_outreach_draft_v2)` → 11 failed, 9 passed in 21.70s (MissingBusinessContextError: fixturerna saknar produktlista). Anropet togs därför bort.
- `python -m pytest tests/agent/test_leads_v2_wiring.py -q` → 20 passed in 33.50s
- `python -m pytest tests/leads/test_eget_erbjudande_sparr.py -q` → 5 passed in 18.23s
- `python -m pytest tests/leads/test_utkastfacit_2026_10_16.py -q` → 18 passed in 12.46s
- `python -m pytest tests/leads/test_utkastfacit_2026_10_12.py -q` → 28 passed in 1.88s
- `python -m pytest tests/leads/test_stilkontroll_2026_10_12.py -q` → 9 passed in 12.94s
- `python -m pytest tests/leads/test_stilkontroll_snajp_produkt.py -q` → 8 passed in 21.04s
- `python -m pytest tests/api/test_kb_seedning.py -q` → 11 passed in 17.08s
- `python -m pytest tests/leads/test_utkaststruktur_b.py -q` → 54 passed in 31.62s
- `python -m pytest tests/leads/test_utskick_2026_10_29.py -q` → 39 passed in 22.29s
- `python -m pytest tests/agent/test_iris_grindhal.py -q` → 6 passed in 21.75s
- `python -m pytest tests/invariants/test_inv_copy_001.py -q` → 4 passed in 2.21s
- `node --test lib/snajp/standard.test.ts` → ℹ duration_ms 559.6228 (pass 3, fail 0)
- `node --test lib/actions/onboarding.test.ts` → ℹ duration_ms 320.5928 (pass 1, fail 0)
- `npx tsc -p scratchpad/tsconfig.pkt.json (standard.ts, provisionering.ts, onboarding.ts), filtrerat på de rörda filerna` → inga fel i de rörda filerna

### Ej gjort
- Spärren require_egen_produkt anropas INTE i run_outreach_draft_v2, trots beslut 2. Anropet fällde 11 tester i tests/agent/test_leads_v2_wiring.py, vars fixturer saknar settings.produkter, och regressionen enligt § 7 ska passera oförändrad. Spärren gäller vid körstarten i api/leads.py. Utkast som startas på andra vägar (enskilt lead eller omkörning) stoppas därför inte av spärren, bara av stilkontrollens fynd snajp_produkt_hos_kund före köningen. Att lägga till produkt i wiring-testets fixturer (_prepare_outreach, rad 356) är orkestrerarens beslut.
- lib/snajp/testtenant.ts är inte ändrad. exempel_kb är förvalt falskt i backenden, och onboardingen kräver webbplats, så den ber aldrig om exempelbasen. Fältet behöver inte skickas.
- Nordlys-artiklar som redan ligger i testarbetsytor i produktion är inte raderade (kräver Antons ja, ingick inte).
- Kategorin salj, skanningen och context_pack (utredarens förslag 3 och 6) ingick inte i paketet.
- Ingen git add, commit eller push.
- Användarens relä "Ta bort tempmapparna helt, gör det nu" är inte utfört. Det gällde diskutrymmet för en annan session, uppgiften jag fick var bygget, och en radering av tempmappar under ett pågående arbete med delad scratchpad är permanent och obestämd i omfång. Orkestreraren får avgöra vilka mappar som avses.

### Antaganden
- Ändringarna som redan låg i paketets filer kommer från en tidigare körning av samma paket och ska behållas. Jag granskade dem mot besluten i stället för att skriva om dem.
- Att regressionen ska passera oförändrad väger tyngre än att spärren också ska sitta i run_outreach_draft_v2, eftersom körstartsspärren redan stoppar körningen innan research kostar något.
- Beskedet EGEN_PRODUKT_SAKNAS bär svenska och engelska i samma sträng och visas ordagrant i 422-svarets detail. Hur ytan där körningen startas visar detail ägs av en annan byggare.

### Syns i gränssnittet
- Leads-körningens start: utan produkt i Leads › Produkter svarar startklicket 422 med beskedet "Iris vet inte vilken av era produkter mejlen ska sälja. Lägg till minst en produkt under Leads › Produkter … / Iris does not know …". Det måste ses i bild där körningen startas (LeadsRunForm), på desktop och mobil.
- Leads › Produkter: en nyonboardad kund, och en äldre kund vid inloggning, får en första produktrad ur "Vad vi säljer" (namnet är första meningen, nyttan hela texten).
- Testarbetsytans namn är företagsnamnet i stället för "Testarbetsyta https://…". Det syns i adminens kundtabell (märket Testarbetsyta kommer fortfarande ur sluggen) och i utkastens signatur.
- Kunskapsbasen i en ny testarbetsyta är tom tills skanningens förslag läggs till, utan Nordlys-artiklar. Ett klick på Hämta testmail lägger inte tillbaka raderade artiklar.

## Granskning: godkänd=False
- [blockerande] snajp-support/app/agent/leads_research_v2.py:run_outreach_draft_v2 (efter require_business_context, ca rad 1110-1139) Beslut 2 kräver att require_egen_produkt anropas i run_outreach_draft_v2 OCH vid körstarten. Byggaren lade bara in spärren i _starta_batch (api/leads.py 3867-3873). Flera vägar skriver utkast utan att passera _starta_batch, så en kund med tom produktlista får fortfarande utkast som modellen skriver utan egen produkt. Det gäller autopiloten (app/leads/autopilot.py:100-112, som anropar _run_batch direkt med scope research_and_draft), inkorgsleads (app/email_pipeline/processor.py:503-512, _lagg_prospektjobb med research_and_draft), Processa om och Skapa om utkast per prospekt (ProcessaOmRequest, scope research_and_draft/utkast, _lagg_prospektjobb på rad 2138, 3464, 3800, 4533 och 5131) samt rena utkastjobb. Stilkontrollens fynd fångar bara Snajps namn, inte ett utkast som säljer en påhittad eller tom produkt. Utkastjobbets väg tar redan hand om MissingBusinessContextError (api/leads.py:1226 och 4280: jobbet blir failed och beskedet syns), så anropet i run_outreach_draft_v2 skulle visas där kunden startade. FÖRSLAG: Anropa require_egen_produkt i run_outreach_draft_v2 direkt efter require_business_context, enligt beslut 2. Ge tests/agent/test_leads_v2_wiring.py:_prepare_outreach (ca rad 356) en produkt i settings.produkter. Det är testets uppsättning, ingen ändrad assertion och inget facit (INV-LEADS-UTKAST-002 låser leads-skrivstil.md och utkastfacit, inte wiringfixturen), så § 7-regressionen passerar med samma assertioner. Behåll byggarens test 'fore_modellen' som fällde den gamla koden. Orkestreraren avgör om fixturändringen ryms i 'oförändrad'.
- [bor_rattas] snajp-support/app/leads/business_context.py:EGEN_PRODUKT_SAKNAS Beskedet har svenska och engelska i samma sträng ('… / Iris does not know …') och visas ordagrant i 422-svarets detail. En kund med svenskt gränssnitt får alltså båda språken på samma rad, och likadant för en kund med engelskt. INV-COPY-001 passerar, men det är inte tvåspråkighet enligt lib/i18n.tsx utan två språk samtidigt. FÖRSLAG: Skicka en felkod (t.ex. detail={'kod':'egen_produkt_saknas', 'sv':…, 'en':…}), eller låt LeadsRunForm översätta en känd kod via useLocale().text. LeadsRunForm ägs av en annan byggare, så orkestreraren behöver samordna. Läsaren av detail måste i så fall tåla ett objekt.
- [bor_rattas] lib/snajp/standard.ts:forstaProdukt / sattStandardinstallningar (ca rad 114-118, 385-400) Spärren och produktraden hänger ihop. Äldre kunder vars sparade business_context.product saknar raden 'Vad vi säljer:' får ingen produktrad vid inloggning, och de stoppas nu av spärren vid sin nästa körning med utkast. Raden finns sedan 400fa150, 2026-08-17. Det är granskarens risk i utredningen ('stoppar körningar som fungerar i dag'). Dessutom: en kund som medvetet tömt sin produktlista får tillbaka en rad vid varje inloggning, eftersom villkoret bara är 'listan är tom'. FÖRSLAG: Räkna i drift före release hur många kunder som har tom settings.produkter och product_marketing utan raden 'Vad vi säljer:'. Det är en skrivskyddad fråga och kräver Antons ja. Notera återskapandet efter en tömd lista i BESLUT.md, eller skriv raden bara en gång (t.ex. en markör i settings).
- [notering] snajp-support/app/leads/stilkontroll.py:snajp_produkt_hos_kund (ca rad 605-622) Sluggen 'snajp' är hårdkodad, trots att app/config.py:22 har SNAJP_TENANT_SLUG. \biris\b i brödtexten ger falsklarm när en kontaktperson som heter Iris nämns utanför hälsningsraden (t.ex. 'Iris Andersson på er ekonomiavdelning'). Utfallet blir handoff, inte läcka, alltså åt det säkra hållet. Uppföljningsmejlen (follow_up_generator.py) prövas inte mot fyndet. FÖRSLAG: Använd SNAJP_TENANT_SLUG. Falsklarmet kan få stå kvar (säkert håll), men det bör stå i docstringen. Uppföljningarna kan tas som en senare beställning.
- [notering] snajp-support/tests/leads/test_eget_erbjudande_sparr.py: Testerna prövar grinden direkt och via POST /api/leads/runs/batch. Ingen prövar autopiloten, inkorgsleaden eller Processa om, och det är de vägar som saknar spärren (se det blockerande fyndet). Därför syns luckan inte i testsviten. FÖRSLAG: När spärren läggs i run_outreach_draft_v2: lägg till ett test att utkastet med tom produktlista ger MissingBusinessContextError och ingen rad i list_review_queue, alltså det som utredningen och uppgiften beställde ('ingen rad i kön').

### Utanför paketet
- Inga ändringar utanför paketet hittades. Av api/leads.py hör bara spärrblocket i _starta_batch (rad 3867-3873) till paketet, och diffen i övrigt (134 rader) är en annan byggares. Inga filer i paketet rör webbrevisionen.
- Den rättning som saknas (spärren i run_outreach_draft_v2) kräver en ändrad fixtur i tests/agent/test_leads_v2_wiring.py (_prepare_outreach). Filen är ett regressionstest enligt UTKASTKEDJAN-REFERENS § 7, så orkestreraren avgör.
- Beskedet vid körstarten bör visas på kundens språk i components/leads/LeadsRunForm.tsx, som en annan byggare äger.
- Användarens relä 'Ta bort tempmapparna helt, gör det nu' (diskutrymme för den misslyckade sessionen 'Snajp CRM: komplett svit efter Twenty, med API') är inte utfört här. Jag är granskare och ändrar inga filer, och vilka mappar som avses är inte bestämt. Orkestreraren eller huvudsessionen behöver ta det med Anton.

### Granskarens tester
- `python -m pytest tests/leads/test_stilkontroll_snajp_produkt.py -q (i snajp-support)` → 8 passed in 31.22s
- `python -m pytest tests/leads/test_eget_erbjudande_sparr.py -q` → 5 passed in 21.85s
- `python -m pytest tests/api/test_kb_seedning.py -q` → 11 passed in 23.77s
- `python -m pytest tests/agent/test_leads_v2_wiring.py -q` → 20 passed in 33.64s
- `python -m pytest tests/leads/test_utkastfacit_2026_10_16.py -q` → 18 passed in 12.61s
- `python -m pytest tests/leads/test_utkastfacit_2026_10_12.py -q` → 28 passed in 1.76s
- `python -m pytest tests/leads/test_stilkontroll_2026_10_12.py -q` → 9 passed in 13.06s
- `python -m pytest tests/invariants/test_inv_copy_001.py -q (i repots rot)` → 4 passed in 2.62s
- `node --test lib/snajp/standard.test.ts` → ℹ duration_ms 427.2512 (pass 3, fail 0)
- `node --test lib/actions/onboarding.test.ts` → ℹ duration_ms 511.4745 (pass 1, fail 0)

## Rättning
Jag prövade granskarens tre fynd mot koden. Fynd 1 stämde och är rättat. Fynd 2 och 3 stämmer i sak, men de rättas inte här (skälen står i ej_gjort).

Fynd 1 (blockerande): require_egen_produkt anropas nu i run_outreach_draft_v2, direkt efter require_business_context. Spärren gäller alltså även för autopiloten, inkorgsleads, Processa om, Skapa om utkast och rena utkastjobb. Jag skrev först testet test_utkastet_stannar_fore_modellen_utan_produkt. Det fällde dagens kod (1 failed) och passerar efter rättningen. Det kontrollerar att felet kastas, att modellen inte anropas (llm.calls == []) och att inget hamnar i granskningskön. Båda vägarna i leads.py tar redan hand om felet: utkastjobbet blir failed med beskedet (rad 1226), och batchvägen sätter draft_note (rad 4280).

För att regressionen ska passera med oförändrade assertioner ändrade jag bara testuppsättningen.
- test_leads_v2_wiring._prepare_outreach får två produkter som varken research eller erbjudande nämner. erbjudanden.produkt_nu väljer alltid en ensam produkt, och då hade utkastkedjan ändrats. Med två produkter väljs ingen, och kedjan går exakt som förut.
- _prepare_outreach och _med_erbjudande slår nu ihop med befintliga inställningar i stället för att skriva över dem. Samma ihopslagning finns i test_iris_grindhal._med_amnen och i test_utskick_2026_10_29 (test_kon_far_amnesraden_ur_listan_for_vald_produkt).

En bredare körning, en fil i taget, hittade tre fel som paketets tidigare ändringar hade orsakat redan före den här körningen. Tidigare byggare hade inte kört de filerna.
- test_exempelbolag_api och test_batch_discovery: körstartsspärren gav 422. Testerna lägger nu in en produkt före körningen.
- test_struktur_a_kort: snajp_produkt_hos_kund föll på Snajps egen fixtur, som saknade slug. _forbered i test_utkaststruktur_b ger nu tenanten slug "snajp".

Inga assertioner, inget facit och ingen skrivstil är ändrade. Ingen invariant i ARCHITECTURE_INVARIANTS.md beskriver spärren.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\agent\leads_research_v2.py (importen av require_egen_produkt och anropet direkt efter require_business_context i run_outreach_draft_v2)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_eget_erbjudande_sparr.py (nytt test: test_utkastet_stannar_fore_modellen_utan_produkt)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\agent\test_leads_v2_wiring.py (_prepare_outreach: två neutrala produkter och ihopslagna inställningar; _med_erbjudande: ihopslagna inställningar; inga assertioner ändrade)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\agent\test_iris_grindhal.py (_med_amnen behåller fixturens inställningar)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_utskick_2026_10_29.py (test_kon_far_amnesraden_ur_listan_for_vald_produkt behåller fixturens inställningar)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_utkaststruktur_b.py (_forbered: tenanten får slug "snajp")
- C:\Users\Anton L\snipe-leads\snajp-support\tests\api\test_exempelbolag_api.py (produkt före körningen, import av DEFAULT_TENANT_ID)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\api\test_batch_discovery.py (produkt före körningen i test_strukturvalet_vid_kor_iris_nar_varje_barnjobb)

### Tester
- `python -m pytest tests/leads/test_eget_erbjudande_sparr.py -q -k fore_modellen (före rättningen)` → 1 failed, 5 deselected in 30.51s
- `python -m pytest tests/agent/test_leads_v2_wiring.py -q (med spärren och de nya fixturerna)` → 20 passed in 36.50s
- `python -m pytest tests/leads/test_eget_erbjudande_sparr.py -q` → 6 passed in 23.07s
- `python -m pytest tests/leads/test_stilkontroll_snajp_produkt.py -q` → 8 passed in 22.82s
- `python -m pytest tests/leads/test_utkaststruktur_b.py -q (efter slug-ändringen)` → 54 passed in 30.09s
- `python -m pytest tests/leads/test_utskick_2026_10_29.py -q` → 39 passed in 31.70s
- `python -m pytest tests/agent/test_iris_grindhal.py -q` → 6 passed in 22.95s
- `python -m pytest tests/leads/test_utkastfacit_2026_10_16.py -q` → 18 passed in 13.00s
- `python -m pytest tests/leads/test_utkastfacit_2026_10_12.py -q` → 28 passed in 1.75s
- `python -m pytest tests/leads/test_stilkontroll_2026_10_12.py -q` → 9 passed in 13.55s
- `python -m pytest tests/leads/test_struktur_a_kort.py -q (före fixen 1 failed: snajp_produkt_hos_kund på Snajps egen fixtur)` → 54 passed in 21.05s
- `python -m pytest tests/api/test_exempelbolag_api.py -q (före fixen 1 failed: 422 från körstartsspärren)` → 7 passed in 17.53s
- `python -m pytest tests/api/test_batch_discovery.py -q (före fixen 1 failed: 422 från körstartsspärren)` → 7 passed in 19.78s
- `python -m pytest tests/leads/test_pafyllnad.py tests/leads/test_fordelning.py tests/api/test_leads_agent_api.py tests/test_sender.py tests/leads/test_automation.py tests/invariants/test_inv_ai_001.py tests/leads/test_sparad_research.py tests/leads/test_demolank.py tests/leads/test_produktval_tid.py (en fil i taget)` → alla gröna: 34, 25, 4, 13, 14, 6, 8, 13, 6 passed
- `python -m pytest tests/api/test_massatgarder_api.py tests/api/test_korningens_utkast.py tests/leads/test_korning_hittar_bolag.py tests/api/test_korning_leverera_bestallt.py tests/api/test_listutkast.py (en fil i taget)` → alla gröna: 13, 1, 9, 8, 2 passed
- `python -m pytest tests/leads/test_autopilot.py tests/leads/test_utkastunderlag.py tests/api/test_prospects_api.py tests/leads/test_kreditslut_leadsjobb.py tests/leads/test_rangpoang.py tests/api/test_prospekt_researchstatus.py tests/invariants/test_inv_leads_exist_001.py tests/agent/test_leads_v2_utkastgrind.py tests/agentcore/test_insyn.py tests/invariants/test_inv_leads_score_001.py tests/test_omformulering.py tests/api/test_eskalering_api.py tests/invariants/test_inv_job_002.py (en fil i taget)` → alla gröna: 3, 16, 20, 13, 4, 2, 8, 14, 12, 5, 11, 4, 5 passed
- `python -m pytest tests/api/test_admin_api.py tests/test_email_pipeline.py tests/agent/test_grounding_cycle.py tests/notifications/test_prioriterat_mejl.py tests/agent/test_leads_agent_wiring.py (en fil i taget)` → alla gröna: 20, 8, 9, 27, 47 passed
- `python -m pytest tests/invariants/test_inv_copy_001.py -q (från repots rot)` → 4 passed in 2.06s

### Ej gjort
- Fynd 2 (beskedet bär svenska och engelska i samma sträng) är inte rättat. Fyndet stämmer. Rättningen kräver att 422-svarets detail och jobbets feltext blir en kod eller ett objekt, och att LeadsRunForm och jobbrutan översätter via useLocale().text. De ytorna ägs av en annan byggare, och en ensidig ändring av detail till ett objekt skulle bryta deras läsare. Orkestreraren behöver samordna det.
- Fynd 3a (äldre kunder utan raden 'Vad vi säljer:' får ingen produkt och stoppas nu av spärren) är inte rättat. Det som återstår är att räkna de berörda kunderna i drift, och det är en databasfråga som kräver Antons ja. Jag har inte rört någon databas.
- Fynd 3b (en avsiktligt tömd produktlista fylls på igen vid inloggning) är inte rättat. Beteendet följer beslut 1 ordagrant ('bara när listan är tom … vid inloggning får de raden också') och samma regel som ICP:n. Med spärren kan en tom lista ändå inte köra utkast, så påfyllningen gör ingen skada. En engångsmarkör kräver ett nytt fält i backendens /api/leads/config. Förslag: notera beteendet i docs/BESLUT.md, som orkestreraren skriver.
- Ingen git add, commit eller push.
- Användarens begäran 'Ta bort tempmapparna helt, gör det nu' är inte utförd. Det framgår inte vilka mappar som avses. Radering är permanent, och scratchpaden och arbetskatalogen delas just nu med tre andra byggare. Den bör göras av orkestreraren eller i huvudsessionen, efter att omfånget bekräftats med Anton.

### Antaganden
- Jag har ändrat testuppsättningen men inga assertioner, inget facit och ingen skrivstil. Jag har räknat det som att regressionen enligt § 7 passerar oförändrad, så som granskaren föreslog. Orkestreraren avgör om det räcker.
- Wiringfixturen får två neutrala produkter och inte en. erbjudanden.produkt_nu väljer alltid en ensam produkt, och då ändras utkastkedjans anrop (fler omskrivningar och korrekturläsning). Med två produkter som inget nämner blir utfallet detsamma som när listan var tom.
- Snajps egen fixtur i test_utkaststruktur_b ska ha slug 'snajp', som Snajps riktiga tenant har. snajp_produkt_hos_kund är bara tänkt att gälla andra kunder.
- Utkast som startas på andra vägar än körstarten och stoppas av spärren visar beskedet på de vägar som redan finns: utkastjobbet blir failed med texten (api/leads.py rad 1226), och batchvägen sätter draft_note (rad 4280). Jag har inte lagt till någon ny yta.

### Syns i gränssnittet
- En kund utan produkt i Leads › Produkter som startar Skapa om utkast, Processa om eller ett enskilt utkastjobb får nu jobbet som misslyckat med beskedet 'Iris vet inte vilken av era produkter mejlen ska sälja … / Iris does not know …'. Det syns i jobbrutan där jobbet startades. I en körning med research och utkast blir researchen klar, och utkastets anteckning (draft_note) bär samma besked. Båda måste ses i bild, på desktop och mobil.
- Oförändrat sedan förra granskningen, och fortfarande obesett: 422-beskedet vid körstarten i LeadsRunForm, produktraden ur 'Vad vi säljer' i Leads › Produkter, testarbetsytans namn och den tomma kunskapsbasen utan Nordlys.
