# karta chatt

Allt nedan är bara läst. Det finns redan en chatt med supportagenten på fyra ställen, och alla kör samma komponent, components/snajp/SupportChat.tsx:
1. Den publika demon på marknadssidan (tenanten snajp när SNAJP_KEY_SNAJP finns).
2. Kundens egen länk /chat/[tenant]/[session].
3. Widgeten under /embed/[nyckel].
4. Testchatt-fliken i dashboardens Kundtjänst (testMode, mot den INLOGGADE kundens egen tenant).

Backendvägen är POST /api/chat. Den svarar 202 med ett job_id och kör agenten i bakgrunden, via Redis-strömmen eller en asyncio-task. Klienten pollar sedan GET /api/jobs/{id} och får en grov fas: läser, söker, skriver eller kontrollerar. Det finns ingen tokenströmning (SSE eller ReadableStream) någonstans.

Tenanten väljs alltid av API-nyckeln (deps.require_tenant). Next har två proxyfamiljer:
- Den anonyma (proxyToBackend) väljer nyckel efter en slug som klienten skickar.
- Den inloggade (proxyAsTenant) väljer nyckel efter sessionen via requireSnajpTenant.

X-Snajp-User och X-Snajp-Demo sätts bara av servern ur sessionen. Backenden använder dem enbart till timtaket per användare (rate_limit_db.scopes_for).

Varje chattmeddelande skapar ett ss_tickets-ärende med konversation och meddelanden i tenanten. Undantaget är ett överlämnat samtal: då svarar en människa via /api/chattar, vars svarsgränssnitt bara finns i den separata appen support-webb.

Snajps egen tenant finns redan: lib/tenants/snajp.ts med SNAJP_KEY_SNAJP och en egen kunskapsbas i snajp-support/app/tenants/snajp_kb.py. Den används i dag bara anonymt, av marknadssidan.

I dashboardens skal finns redan en hjälp- och felanmälningsingång: AgentMenu ("Meny") i railens fot vid lg och uppåt, och i mobilraden. Där finns "Anmäl felaktigt svar", men den är bara en mailto till snajpsupport@gmail.com. Det finns ingen felrapport som blir ett ärende, ingen koppling till en kodande agent och ingen spegelmiljö.

Den säkra vägen till Snajps egen agent ur en annan kunds arbetsyta är en NY autentiserad Next-route. Den kräver session (getWorkspaceContext eller requireSnajpTenant) men skickar med SNAJP_KEY_SNAJP och aldrig kundens nyckel. Identiteten, arbetsytan, vyn och sidan härleds på servern. Kundens kunskapsbas får bara skrivas genom kundens egen proxy (proxyAsTenant mot /api/kb) efter ett människoklick, som testchattens KB-kort redan gör.

Chattrutan hör hemma i AgentMenu-ingången, alltså railens fot och mobilraden. Där står "Anmäl felaktigt svar" i dag och ska ersättas. Den ska inte vara en ny flytande bubbla eller en ny panel ovanpå sidorna.

## Saknas
- En inloggad väg från en kunds arbetsyta till Snajps EGEN agent (tenanten snajp) finns inte. SNAJP_KEY_SNAJP används bara av den anonyma marknadsdemon (ProductPage.tsx:26). Det finns ingen route som kräver session och samtidigt använder Snajps nyckel.
- Det finns ingen chattruta i dashboardens skal. Den enda chatten i dashboarden är Testchatt-fliken i Kundtjänst, och den talar med kundens EGEN agent, inte med Snajp.
- En felrapport som blir ett ärende finns inte. 'Anmäl felaktigt svar' är en mailto (AgentMenu.tsx:122-134), och ingen mejltransport finns enligt komponentens docstring. Det finns ingen tabell eller endpoint för plattformsfelrapporter, och grep efter felrapport, bug_report och plattformsarende ger bara kommentarer.
- Det finns inget fält för sida, arbetsyta, vy eller rapporterande användare i ChatRequest (schemas.py:15-31) eller i ss_tickets (postgres.py:612-645). Kategorierna saknar något för felrapport (config.py:54-63).
- Vidarebefordran till en kodande agent finns inte: ingen kö, ingen webhook, inget GitHub-ärende och ingen anropspunkt från backenden.
- En spegelmiljö per kund eller per rättning finns inte. Proxyn har en enda backendadress (SNAJP_SUPPORT_URL eller SNAJP_SUPPORT_INTERNAL_URL, _lib.ts:9-34). Det finns ingen routning per användare eller per gren.
- Det finns ingen tokenströmning (inget EventSource, text/event-stream eller StreamingResponse i app, components, lib eller snajp-support/app). Chatten är 202 plus pollning med fyra faser.
- Uppföljning av ett ärendes status i samma ruta finns inte. Samtalet återställs bara via sessionStorage-identiteten i samma flik (SupportChat.tsx:281-295, 459-485, lib/sessionslagring.ts). En ny flik eller en ny enhet ger en ny identitet och tom historik. Ingen ärendestatus (mottaget, rättning pågår, spegel klar, publicerad) visas någonstans.
- Medarbetarsvar på en överlämnad chatt kan inte ges i Next-appen. POST /api/chattar/{id}/svar anropas bara från support-webb/ChattarVy.tsx:133.
- INV-SEC-010 och INV-SEC-014 saknar avsnitt i ARCHITECTURE_INVARIANTS.md (där finns bara INV-SEC-001–009, 011–013). INV-SEC-010 finns som test (tests/invariants/test_inv_sec_010.py). INV-SEC-014 hittade jag bara i kommentarer.
- Snajps egen kunskapsbas har nästan ingen produkthjälp för den inloggade ytan (en artikel, 'Hitta rätt på arbetsytan', snajp_kb.py:64). Resten är sälj- och villkorsfrågor. För ärendeslag 1 krävs alltså mer KB-innehåll.

## Fällor
- Samtalen läcker om identiteten slutar på @session.snajp.se. Tenanten snajp nås ANONYMT via /api/snajp-support/chat och /chat/samtal med tenant=snajp (ProductPage.tsx:26, chat/route.ts:27-71, chat.py:320-352). Får en inloggad kunds hjälpchatt identiteten '<userId>@session.snajp.se' kan vem som helst som känner värdet läsa samtalet och skriva i det anonymt. Identiteten måste sättas på servern, ligga på en domän som den anonyma routen avvisar (till exempel @kund.snajp.se, avvisas redan av arSessionsidentitet, chat/route.ts:22-25), och läsas tillbaka via en NY autentiserad backendväg, eftersom samtal-endpointen bara godtar @session.snajp.se (chat.py:335).
- Kunden får inte proxyAsTenant. Den väljer nyckel efter KUNDENS tenant (_auth.ts:37,74), så chatten hade gått till kundens egen agent och kunskapsbas. Under impersonering stämplar den dessutom is_test på kroppen. Hjälpchatten behöver egen nyckelhantering med proxyWithApiKey(SNAJP_KEY_SNAJP, userId, isDemo) men sessionsgrind via getWorkspaceContext eller requireSnajpTenant, annars fäller INV-SEC-010-testet routen (test_inv_sec_010.py:79-84).
- arbetsyta=true får aldrig sättas på hjälpchatten. Med Snajps nyckel bygger arbetsyta_siffror.bygg_sifferblock Snajps EGNA nyckeltal (support_agent.py:1240-1241) och visar dem för en kund. Testchattens route sätter flaggan ovillkorligen (testchatt/route.ts:36), så den kan inte återanvändas rakt av.
- Kunskapsbasens tenantgräns: Snajps agent (tenanten snajp) kan inte och får inte skriva i kundens kunskapsbas. Kontext för ärendeslag 2 måste gå genom kundens egen proxy (POST /api/snajp-support/kb via proxyAsTenant) efter ett människoklick, som KB-kortet gör (SupportChat.tsx:738-782, INV-LEARN-001). Läsrollen (viewer) får då 403 (_auth.ts:50-52), och en impersonerande admin skriver is_test.
- Delade tak: alla kunders hjälpchattar plus den publika marknadsdemon delar tenanten snajps tak på 400 LLM-anrop i timmen (rate_limit_db.py:49) och dess dygnsbudget (chat.py:265). Ett skov på marknadssidan kan stänga kundernas hjälpchatt och tvärtom. Ett supportsvar kostar ungefär sex steg, så taket räcker till ungefär 60–70 svar i timmen totalt.
- Avtalsgrinden körs på tenanten snajp (chat.py:245). Har snajp kraver_avtal=true utan registrerat avtal svarar hjälpchatten 403. Värdet ligger i databasen och är inte kontrollerat här (endast läsning).
- Varje chattmeddelande blir ett eget ss_tickets-ärende (support_agent.py:1384-1401). En felrapport via vanliga /api/chat blir därför ett generiskt supportärende i Snajps inkorg, utan sida, arbetsyta eller koppling till rapportören, och utsatt för agentens eskaleringsregler. En felrapport behöver ett eget, strukturerat flöde och inte agentens fria klassning.
- Kundminnet: med en stabil identitet per användare sparar triagesteget kundfakta (support_agent.py:1366-1375) och historik i Snajps tenant. Det är bra för kontinuiteten, men identiteten ska vara per användare och inte per arbetsyta, så att två användare i samma kundföretag inte delar samtal.
- Impersonering: en plattformsadmin som besöker en kund (vy 'kund') ska inte skapa felrapporter som ser ut att komma från kunden. Rapportören måste vara user.id, med vy och besökt slug som separata fält (lib/snajp/tenant.ts:228-299).
- Ett nytt ChatRequest-fält, till exempel sida eller arbetsyta som kontext, måste med på tre ställen: schemat, enqueue-nyttolasten (chat.py:282-302) och rekonstruktionen (chat.py:207-215). Annars försvinner det tyst i drift (Redis-vägen) men inte lokalt. Det har hänt med arbetsyta.
- Webbplatsbedömningen är hemlig. En felrapports automatiska kontext (sidans data, skärmbild, API-svar) får inte bära webbrevision eller webbnivå från Leads till Snajps ärende eller till den kodande agenten om rapportören inte är admin, Umeå Webdesign eller Alunix. Utan grind blir det en läcka.
- Dataskydd: development är en spegel av produktionen med riktig kunddata. En 'spegel med fixen' som kör mot riktig data får aldrig nå DeepSeek (Settings.llm_provider_fault). Den kodande agenten får inte få kunddata i sin prompt utan avtalsstöd.
- Projektregler: allt användarvänt måste vara sv/en (INV-COPY-001, tests/invariants/test_inv_copy_001.py), och förlopp och utfall ska synas där ärendet startades och finnas kvar efter omladdning. Dagens sessionStorage-modell (en per flik) uppfyller inte det sistnämnda för inloggade användare.
- Den publika chatten är 'kort' som standard med fast höjd (SupportChat.tsx:221-227). I en panel ur AgentMenu behövs layout='fyll' eller en ny variant. AgentMenu-panelen är 22rem bred och viewportankrad på mobil (AgentMenu.tsx:164-171), mätt mot överlopp vid 375 px.

## Kräver Anton
- Ska tenanten snajp dela timtak och dygnsbudget med den publika marknadsdemon, eller ska hjälpchatten få en egen tenant (till exempel snajp-hjalp) med egen kunskapsbas och egna tak? Det påverkar också om kundernas hjälpsamtal blandas med anonyma besökares i samma inkorg.
- Ska felrapporter skickas till den kodande agenten automatiskt, eller först efter att någon hos Snajp (Anton eller Sebbe) har godkänt ärendet? Och vilken kunddata får följa med till agenten (skärmbild, sidans innehåll, API-svar)? Development speglar produktionen, och webbplatsbedömningen är hemlig.
- Vad betyder 'spegel bara för deras inlogg' i drift? En egen Railway-deploy per rättning mot development-databasen (en spegel med riktig data), eller en flagga per användare i befintlig development? Och vem trycker 'gå vidare till development'? Main kräver alltid Antons uttryckliga ja (CLAUDE.md, §8.1a).
- Ska förloppet i rutan (mottaget, rättning pågår, spegel klar, publicerad) synas fullt för kunden, eller bara delvis med resten för plattformsadmin? Projektregeln 2026-10-10 säger att Anton ska tillfrågas när det är tveksamt.
- Är kraver_avtal satt för tenanten snajp, och ska avtalsgrinden gälla Snajps egen hjälpchatt? Om ja och avtal saknas svarar den 403. Det går inte att kontrollera med bara läsning.
- Ska medarbetarsvar på överlämnade hjälpchattar kunna ges inifrån huvudappen? Svarsgränssnittet finns i dag bara i support-webb, och dess framtid är ett öppet beslut enligt DEPLOY.md.

# karta arenden

Supportagenten (snajp-support/app/agent/support_agent.py) är en kedja av JSON-steg i fast ordning: triage, research, utkast, eskaleringsbedömning, KB-förslag, retention och humanizer. Varje steg är ett eget modellanrop i JSON-läge (step_runner.run_step, response_format json_object). Allt som har en sidoeffekt görs i kod efter stegen, och agenten anropar alltså inga verktyg. Det den kan göra utöver att svara med text är fyra fasta saker i kod. Den skapar ett ärende per chattmeddelande, eskalerar (status escalated plus ett prioriterat mejl till snajpsupport@gmail.com och ett överlämnat samtalsläge), sparar ett KB-förslag i agent_suggestions och skickar händelsen arende_eskalerat till kundens integrationer. Verktygsanrop via Agents SDK finns bara i demoagenten, bokförings-, kvitto- och leadsagenterna (Runner.run), aldrig i supportkedjan.

Lagringen består av ss_tickets (status open/in_progress/escalated/resolved/closed, 8 kategorier, kanalerna web/email/whatsapp/messenger/slack/teams), ss_conversations, ss_messages (author customer/agent/human), ss_chat_state (lage agent/overlamnad, orsakskod) och agent_suggestions. Det finns två KB-förslagsvägar: agent_suggestions (kind kb_article/marknadsinsikt) och ss_kb_forslag, som webbplatsskanningen fyller.

Ärendena visas på tre ställen:
- **Dashboarden:** fliken Kundtjänst med flikarna Översikt, Ärenden, Testmail, Dolda och Testchatt.
- **Den separata portalen support-webb:** vyn ChattarVy, där en medarbetare tar över chatten.
- **Adminytan:** FelOchEskaleringar, och ärendelänken /admin/kunder?arende=.

Notiscentret i appen gäller bara Leads (lead_handelser, migration 149).

Testchatten i dashboarden kör kundens EGEN agent mot kundens egen kunskapsbas (is_test, arbetsyta=true). Det är inte Snajps agent. Snajp finns redan som tenant (slug snajp, lib/tenants/snajp.ts, nyckeln SNAJP_KEY_SNAJP).

Det som saknas helt:
- en avsiktsklass för felrapport och kunskapsbidrag
- ett sätt att bära sidkontext in i chatten
- en skrivväg till en ANNAN tenants kunskapsbas från en körning
- en tabell eller statusmodell för felärende, gren, spegel och godkännande
- ett ärendestatus som kunden kan läsa
- koppling till en kodande agent
- en spegel per inloggning

Modellen är MODEL=gemini-3.5-flash-lite på Vertex i EU (BESLUT 2026-11-20, i development, main först med release). Dataskyddet tvingas fram av Settings.llm_provider_fault(): DeepSeek och OpenAI fälls i miljöer med riktig data, och alla regioner måste ligga i EU. INKORG_JEV är av i båda miljöerna sedan 2026-11-17. Anthropic står inte i underbiträdesförteckningen, vilket rör överlämningen till en kodande agent.

## Saknas
- Supportagenten kan inte anropa verktyg. Det finns ingen avsiktsklassning för hjälp, kunskapsbidrag eller felrapport: triagen ger bara kategori, prioritet, sentiment och flaggorna escalate, ber_om_manniska, inom_amnesomradet och missforstadd (support_agent.py:1303-1341). Ett felärende kan alltså inte skapas av agenten i dag.
- Det finns ingen ärendetyp för felrapport. ss_tickets.category har 8 supportfack via check-villkor och ss_tickets.status bara open/in_progress/escalated/resolved/closed. Ingen kolumn eller tabell finns för gren, PR, spegel-URL, vem som får testa, kundens test eller godkännande, och inget tillstånd mellan escalated och resolved.
- ChatRequest saknar fält för kontext: aktuell sida eller URL, vilken arbetsyta (tenant_id) användaren sitter i, användar-id eller roll, webbläsare och tidpunkt. Inget sådant når agenten eller ärendet i dag (schemas.py:15-31).
- Ingen route i huvudappen låter en inloggad kund chatta med SNAJPS agent (tenant snajp). testchatt/route.ts går alltid med kundens egen nyckel, och den anonyma chat-routen kräver en sessionsidentitet och bär ingen inloggad identitet.
- Ingen kodväg skriver ett KB-förslag i en ANNAN tenant än den körningen gäller. save_agent_suggestion och ss_kb_forslag skrivs alltid med körningens tenant_id, RLS kräver app.tenant_id och master-nyckeln vägras mot kunddata (deps.py:67-71).
- agent_suggestions.kind tillåter bara kb_article och marknadsinsikt (migration 051), och ss_kb_forslag har ingen kolumn för källa eller ärende. Att ett utkast kom från kundens chatt går inte att märka utan migration (skanning_id är nullable, så raden kan skapas, men källan syns inte).
- Kunden kan inte läsa ett ärendes status. GET /api/tickets/{id} kräver tenantens nyckel, och ärendet ligger i Snajps tenant, inte i kundens. Inget svar från /api/chat/samtal bär ärendestatus.
- Det finns inga supportnotiser i appens notiscenter (bara Leads). Inget säger till kunden att spegeln är klar eller rättningen ute.
- Huvudappen har inget gränssnitt för att ta över chatten. Svar och återlämning finns bara i support-webb (ChattarVy), som är en egen tjänst.
- Ingen koppling finns till en kodande agent: ingen kö, inget webhook och ingen GitHub-issue eller gren skapas ur ett ärende. Det prioriterade mejlet är den enda signalen ut, och det får inte bära kundens text.
- Ingen spegel per inloggning finns. Det finns ingen routning från en viss användare till en viss build eller miljö, och ingen tabell för vem som når vilken förhandsversion. Development är en delad spegel av produktionen, inte en miljö per ärende.
- Inga tester eller invarianter finns för felärenden, för skrivning till en annan tenant eller för vem som når en spegel.

## Fällor
- Testchatten är fel bas. Den kör KUNDENS egen agent mot kundens kunskapsbas, märks is_test och ger arbetsyta=true, så kundens nyckeltal hamnar i kontexten. Snajps hjälpchatt måste gå med Snajps nyckel och tenant (SNAJP_KEY_SNAJP), och arbetsyta=true får inte sättas där. Annars hamnar Snajps nyckeltal, eller fel tenants, i svaret.
- Varje chattmeddelande blir ett eget ärende (support_agent.py:1384-1401, kommentaren vid MAX_HISTORY_TICKETS). En felrapport över flera repliker sprids därmed på flera ss_tickets-rader. Felärendet behöver ett eget id som binder ihop dem, eller ss_tickets.parent_ticket_id, som finns men inte används.
- En eskalering sätter lage=overlamnad. Agenten tiger då i upp till 24 h, eller kvitterar, men en ny fråga ger gästläge (support_agent.py:805-920, 2419-2449). Om en felrapport modelleras som en eskalering förlorar kunden hjälpchatten medan felet rättas. Felrapporten bör vara en egen sidoeffekt, inte en överlämning.
- Triagens instruktion säger att escalate aldrig ska sättas för en vanlig fråga (rad 1312-1316), och kategorin hamnar då på ovrigt. Utan ett nytt fält går en felrapport som ett vanligt svar utan något ärende alls.
- INV-LEARN-001 innebär att kontext kunden ger till sin kunskapsbas aldrig får skrivas in automatiskt av agenten. Den ska bli ett utkast (ss_kb_forslag status vantar, eller agent_suggestions) som kunden godkänner. Utkastet ska ligga i KUNDENS tenant, och skrivningen kräver kundens tenantkontext (RLS app.tenant_id), inte Snajps.
- INV-SEC-012: text som kunden skriver i chatten och som blir KB-utkast är opålitlig och ska kapslas när den senare läses som artikel. Ett utkast som skapats från en annan tenants körning får inte hoppa över det.
- Webbplatsbedömningen är hemlig (CLAUDE.md). Om felrapportens kontext tar med sidans innehåll eller API-svar från Leads (webbrevision, webbniva, lan) och kunden inte är Umeå Webdesign eller Alunix, är det en läcka till ärendet och till kodagenten. Kontextpaketet ska grindas.
- Dataskyddet: kundens felrapport innehåller personuppgifter (användarens mejl och ofta kunddata på skärmen). Att lämna den till en kodande agent (Claude Code, Anthropic, USA) är en ny överföring. Anthropic står inte i lib/bolag.ts, och JURIDIK_ATGARDER punkt 28 ('AI-kodverktyg läser testmiljöns kunddata') är obeslutad. INV-DATA-006 gäller bara appens egna modellanrop.
- Det prioriterade mejlet får aldrig bära kundens text (prioriterat_mejl.py:34-41). En felrapport till Snajp får alltså bara länka till ärendet, inte innehålla beskrivningen.
- Spegeln: development-databasen är en kopia av produktionen med riktiga kunders data (CLAUDE.md, DEPLOY.md:193). En spegel per kund som pekar dit visar andra kunders data för den som når miljön, om inte RLS och inloggningen håller. En lokal server får aldrig pekas dit.
- Jobbstatusen har TTL på 1 h (jobs/store.py:18). Felärendets förlopp och utfall måste ligga i databasen för att finnas kvar efter omladdning (projektregeln 2026-10-10), inte i jobbet.
- Nya ChatRequest-fält måste läggas in på två ställen, i enqueue och i hantera_strom_jobb (chat.py:280-301 och 165-230). Det har redan tappats en gång (arbetsyta, 2026-10-05).
- ss_tickets.channel och category har check-villkor. En ny kanal (t.ex. 'portal' eller 'app') eller kategori (t.ex. 'felrapport') kräver en additiv migration, och CATEGORIES i config.py måste matcha.
- Supportbudget, rate limit och avtalsgrind gäller per tenant. Alla kunders hjälpchattar mot Snajps tenant delar alltså Snajps dygnsbudget (app/budget.py). Om tenanten snajp har kraver_avtal=true utan avtalsdatum svarar /api/chat 403 (chat.py:245). Det är inte kontrollerat i databasen här.
- Varje kund som chattar blir en rad i Snajps ss_customers (find_or_create på e-post). Snajp blir då personuppgiftsansvarig för den raden, inte biträde. Gallring och registerförteckning måste täcka den.
- Ocommittat arbete i samma område pågår: _auth.ts (X-Snajp-Identitet), app/api/snajp-support/identitet/, config.py, api/inbox.py, kb_skanning.py och migration 153 (KB-kategorin salj). Bygg inte på de filerna innan de committats.
- Svarscachen (INV-CACHE-001) får inte cacha ett svar som skapat ett felärende eller ett KB-utkast. Villkoret vid rad 2464-2469 behöver ett tillägg.
- _KANSLIGT och _KRIS eskalerar i kod. En felrapport med ord som 'dragit pengar två gånger' eller 'fel faktura' blir en överlämning med orsaken sakerhet. Ordningen mellan de två vägarna måste bestämmas.

## Kräver Anton
- Får en kodande agent (Claude Code, Anthropic, USA) läsa kundens felrapport, och i så fall hur mycket? Antingen pseudonymiserad sammanfattning och länk, eller full text med skärmbild. Anthropic är inte underbiträde (lib/bolag.ts), och JURIDIK_ATGARDER punkt 28 är obeslutad. Om ja ska underbiträdet in på alla fyra listorna i samma ändring.
- Spegelns data: ska kundens spegel gå mot development (riktig data från alla kunder), en egen kopia av bara kundens tenant, eller syntetisk data? Vem utöver kunden når den, och hur länge lever den?
- Ska kundens kunskapsbidrag från chatten alltid bli ett utkast som kunden godkänner (INV-LEARN-001, som i dag), eller vill Anton ha ett undantag (waiver) för text som kunden uttryckligen ber om att få inlagd?
- Hur mycket av förloppet ska kunden se: alla steg (analys, gren, PR, spegel) eller bara mottagen, spegel klar, ute? Projektregeln 2026-10-10 säger att Anton ska tillfrågas när det är tveksamt.
- Det godkända flödet efter kundens test: automatisk merge till development, eller Antons eller Sebbes granskning först? Varje release till main kräver fortfarande Antons uttryckliga ja (§8.1a).
- Snajps tenant som mottagare: avtalsgrind (kraver_avtal), dygnsbudget för alla kunders hjälpchattar och modell (MODEL=gemini-3.5-flash-lite gäller bara development tills releasen).
- Ska takeover och ärendehantering för Snajps egna ärenden ske i support-webb (ChattarVy) eller flyttas in i huvudappens admin? DEPLOY.md säger att det beslutet väntar på Anton och Sebbe.
- Gallring och registerförteckning för felärenden och chattar där Snajp är personuppgiftsansvarig, inte biträde.

# karta kunskapsbas

Allt som lägger in nya artiklar i ss_knowledge_base går genom två ställen i lagringen: Storage.add_kb_article (postgres.py:1086-1116, memory.py:795-815) och PostgresStorage.lagg_till_kb_forslag, som har en egen rå INSERT (postgres.py:1278-1286, memory.py:899-915). Undantagen är konverteringen testkund→kund, som kopierar med rå SQL (tenants/konvertera.py:246-262), och scripts/fyll_embeddings.py, som uppdaterar embedding direkt med SQL. Bara tre vägar tar bort artiklar: DELETE /api/kb/{id} (kb.py:113-124), seed_tenant för just tenanten "snajp" (seed_kb.py:172-183) och konverteringens radering av hela basen. Kunskapsbasen har inget UI för att ta bort eller ändra en artikel, och inget PUT-endpoint finns.

ss_kb_forslag skrivs bara av webbplatsskanningen (kb.py:_spara_utfall 170-184 → add_kb_forslag), av POST /api/kb/forslag/beslut (kb.py:338-390) och av migration 130. Det finns ett andra förslagslager, agent_suggestions (migration 051). Supportagentens cs:kb-article skriver dit (support_agent.py:2060-2067), och POST /api/agent/forslag/{id}/godkann gör förslaget till en artikel (leads.py:1371-1406).

En seedad exempelartikel går i dag INTE att känna igen i data. Kolumnen is_placeholder finns (migration 20260730204754 rad 33, default false), men ingen kodrad skriver eller läser den. embedding är null även för kundens egna artiklar från perioden 2026-09-12 till 2026-10-06 och för allt som sparas i simuleringsläge. Den enda pålitliga signalen är rubriken (och innehållet) ur kb_articles.KB_ARTICLES i en tenant vars slug börjar på testkund-. Det är samma heuristik som scripts/qa_radera_konto.py:84-102 bygger på.

En annan agent ändrar just nu i det här området, och ändringarna är inte committade: exempelbasen läggs bara in med exempel_kb=True (keys.py:61), och inbox-mocken seedar bara en helt tom bas utan skanning (inbox.py:94-105). Ingen anropare i appen skickar exempel_kb=True. Inget tar bort de Nordlys-artiklar som redan finns i befintliga testarbetsytor, till exempel ytan från Buddy-demon.

Förslag: rensningen läggs i lagringslagret, i samma transaktion som varje insert av eget innehåll. add_kb_article och lagg_till_kb_forslag får is_placeholder (False som standard), och vid False raderas tenantens is_placeholder-rader i samma transaktion. Bara ensure_tenant_kb skickar True. Konverteringen kopierar aldrig is_placeholder-rader. En backfill markerar befintliga exempelrader.

Kontext som kunden ger i chatten blir ett förslag i ss_kb_forslag med källa chatt, inte en artikel direkt. Förslaget visas i chatten och i den befintliga förslagslistan, och artikeln skapas först när kunden klickar på Lägg till.

## Saknas
- Inget skriver eller läser is_placeholder. Seedade exempelartiklar är omärkta i data, och list_kb och search_kb kan inte skilja dem från kundens egna.
- Ingen rensning av exempelartiklar finns någonstans. När kundens eget innehåll kommer in står Nordlys-artiklarna kvar och fortsätter vara grundningskälla i search_kb (postgres.py:987-1059).
- Det finns ingen backfill för befintliga testkund-tenants som redan bär Nordlys-artiklar (seedade före 2026-11-25, till exempel från Buddy-demon 2026-11-24).
- ss_kb_forslag saknar fält för källa och spårbarhet (kalla, kalla_ref, skapad_av). Ett förslag ur en chatt går inte att skilja från ett skanningsförslag och inte att spåra till meddelandet.
- Det finns inget endpoint för att skapa ett enskilt förslag utanför skanningen. add_kb_forslag kräver skanning_id som argument, men kolumnen är nullable.
- Det finns inget update-endpoint och inget 'ersätter artikel X'. Rättelser ur en chatt kan bara bli en ny artikel bredvid den gamla.
- Kunskapsbas-UI:t saknar knapp för att ta bort en artikel. Kunden kan inte själv bli av med exempelartiklarna.
- Två förslagslager finns parallellt (ss_kb_forslag i kundens Kunskapsbas och agent_suggestions i lärande- och adminvyn), med olika dubblettregler. Det finns ingen gemensam väg.
- Det finns ingen kod för en chattruta med Snajps egen agent i den inloggade dashboarden som skriver till kundens bas. SupportChat:s testMode kör kundens EGEN agent mot kundens EGEN bas.
- Migration 121 ger ingen delete-grant på ss_kb_forslag, så förslag kan bara statusmärkas, inte raderas.

## Fällor
- Dubblettkontrollen äter skanningsförslag: _spara_utfall (kb.py:172) och beslutet (kb.py:354, 370-375) jämför mot ALLA rubriker i list_kb. Exempelrubriker som 'Öppettider och kontaktvägar' eller 'Leveranstider och fraktalternativ' gör att kundens egna förslag med samma titelnyckel räknas som 'redan_fanns' eller avvisas som 'fanns_redan'. Dubblettkontrollen måste bortse från is_placeholder-rader, annars hjälper rensningen inte.
- lagg_till_kb_forslag har en egen rå INSERT (postgres.py:1278-1286) som inte går genom add_kb_article. En rensning som bara läggs i add_kb_article missar därför den vanligaste vägen för eget innehåll, att kunden lägger till ett skanningsförslag.
- Konverteringen (konvertera.py:252-262) kopierar exempelartiklar till en riktig kund med rå SQL. Då kommer ett annat bolags villkor in i kundens grundningskälla, alltså precis den korsning keys.py:51-54 varnar för.
- Inbox-mockens grind (inbox.py:99-105) seedar på nytt om basen blir tom och ingen skanning har körts. Raderar en kund alla sina egna artiklar efter rensningen kommer Nordlys tillbaka.
- embedding IS NULL duger inte som igenkänning: egna artiklar från 2026-09-12 till 2026-10-06 och allt som sparas i simuleringsläge saknar också vektor (base.py:435-438).
- Rubrikmatchning för backfill: KB_ARTICLES har växt från 16 till 28 artiklar (qa_radera_konto.py:95-100), och en del rubriker och innehåll har ändrats. Backfillen måste matcha mot alla historiska rubriker, och bara inom testkund-*-tenants.
- DEFAULT_TENANT_ID (Nordlys Handel) och PUBLIC_DEMO-tenanten äger sina artiklar. De får aldrig markeras som exempel, och ensure_default_kb och ensure_public_demo_kb ska inte sätta is_placeholder.
- Tenanten 'snajp' seedas och ersätts per rubrik av seed_tenant (seed_kb.py:155-192). Snajps egna produktartiklar får aldrig behandlas som exempel.
- Tenantgränsen: chattrutan drivs av Snajps agent (tenanten snajp), men kontexten ska in i KUNDENS bas. Lagringen skopar med _scoped(tenant_id) och RLS på app.tenant_id. Snajps agent får aldrig skriva med en annan tenants skop. Förslaget ska skrivas av ett endpoint som autentiseras med kundens session via proxyAsTenant.
- Webbplatsbedömningen är hemlig (CLAUDE.md). En chattkontext eller felrapport som bär webbrevisionens fält får inte hamna i kundens förslag eller artiklar.
- INV-COPY-001: varje ny text i förslagskortet och i Kunskapsbas ('Exempel', 'Från chatten') måste finnas på både svenska och engelska.
- Migration 153 och de pågående ändringarna i keys.py, inbox.py, kb_skanning.py och Kunskapsbas.tsx är ocommittade från en annan agent. Rensningsändringen krockar i keys.py, inbox.py och seed_kb.py och måste byggas på deras commit.

## Kräver Anton
- När ska exemplen bort? Vid första egna artikeln i basen (mitt förslag: agenten blir aldrig stående med en tom bas) eller redan när webbplatsskanningen levererar förslag, även om kunden inte lagt till något?
- Ska alla exempelartiklar bort på en gång när första egna artikeln kommer in, eller bara de i samma kategori? Mitt förslag är alla, eftersom de är ett annat bolags villkor.
- Ska chattkontexten bli förslag som kunden godkänner (mitt förslag, i linje med INV-LEARN-001 och beslutet 2026-11-18) eller artikel direkt när kunden uttryckligen skriver att något ska läggas in?
- Får backfillen köras mot development och sedan produktion, och vilka testarbetsytor ska den omfatta? Riktiga kunder som konverterats från testkund kan bära Nordlys-artiklar via konvertera.py. Ska de också städas? Det kräver en granskning per kund, eftersom basen är deras.
- Ska chattförslagen ligga i ss_kb_forslag (kundens Kunskapsbas) och agent_suggestions fortsätta som ett separat lager för agentens egna luckor, eller ska lagren slås ihop?
- Behöver kunden en knapp för att ta bort en artikel i Kunskapsbas? Endpointet finns, men UI:t saknar knappen.

# karta miljoer

Railway-projektet (brave-passion, b4ec4f98-…) har två miljöer, main och development. Båda kör web, api, Postgres, Redis och support. Main har dessutom migrera-main och synk, och development har migrera och overvakning. Båda deployar av sig själva från sina egna grenar via miljöspecifika deploymentTriggers. Development är en spegel av main och har markören public.mirror_meta. Raderna i 28 tabeller (körningar och ärenden, se railway_synk.SYNK) synkas var tionde minut. Övriga tabeller (workspaces, auth.users, kunskapsbas, agent_configs) fylls bara när railway_seed_dev.py körs för hand, med truncate och copy av hela databasen. Workflowen spegla-dev.yml som DEPLOY.md beskriver finns inte längre.

Två saker finns redan och bär nästan hela alternativ A:
1. railway_provision.py kan skapa en ny miljö som klon (environmentCreate med sourceEnvironmentId, skipInitialDeploys), sätta gren per miljö (ensure_trigger), skapa domän och skriva variabler.
2. RAILWAY.md:202-217 har mätt en grenmiljö: klonen gav egen Postgres och egna domäner utan handgrepp, men databasen blev tom och en DATABASE_URL satt som referens löstes inte ut.

Spegelmarkören stänger redan det farligaste i en sådan miljö, om lage='envags' är satt. Då stoppas utskick, inkorgsläsning och autopilot (scheduler.py:698-700, 838-844, autopilot.py:73, poller.py:359).

Det som saknas:
- ett utdrag som fyller en databas med bara en kunds data (inget sådant verktyg finns)
- en grind som släpper in bara den kundens inloggning
- en vitlista för variabler, så att en klon inte ärver FLYTT_*, RESEND/SMTP, inkorgslösenord och liknande
- städning med environmentDelete (finns inte i koden)
- en körväg som når databasen inifrån Railway. En molnsession når bara port 443 (RAILWAY.md:58-77).

Bedömning:
- (A) En egen miljö per rättning är det enda alternativet som uppfyller beställningen. Kunden testar körande kod från fix-grenen innan något når development eller main. Det kräver mest bygge.
- (B) En delad förhandsmiljö som byter gren använder samma maskineri. Den är billigare men klarar bara en rättning och en kund åt gången, och miljön måste tömmas och fyllas om vid varje byte.
- (C) En funktionsflagga per arbetsyta kräver att koden redan ligger i main bakom flaggan, alltså en release med Antons ja före kundens test. Det vänder ordningen i beställningen och fungerar inte för vanliga buggrättningar. Det närmaste som finns i dag är kundval i agent_configs.settings (profil.kundval), inget generellt flaggsystem.

Rekommendation: A, byggd som ett nytt skript och ett nytt Railway-jobb. Jobbet ska skapa en tom miljö eller klona med vitlista, migrera från noll, läsa main skrivskyddat med en ny läsroll, skriva bara kundens rader, sätta markören med lage='envags', lägga på en grind för tillåtna användare och radera miljön efteråt. B är en reserv om kostnaden eller planens gränser stoppar A.

## Saknas
- Det finns inget kundutdrag som fyller en databas med EN kunds data. railway_seed_dev.py kopierar allt, och synk_las får bara läsa de 28 SYNK-tabellerna. workspaces, profiles, auth.users, workspace_members, kunskapsbasen, agent_configs, workspace_tenant_keys med flera kan rollen inte läsa (migration 122). Utdraget behöver en egen läsroll, en tabellista per kundnyckel (tenant_id, workspace_id, ss_tenant_id och barn via främmande nycklar) och svar på de delade tabellerna (auth.users, platform_admins, platform_events, suppressions, webbpoolen, behandlingsbegransningar).
- Det finns ingen spärr i koden som håller ett utdrag borta från main och development. INV-DATA-001 vaktar bara railway_seed_dev.py. Ett nytt skript behöver samma tre spärrar: hårdkodad målform (t.ex. miljönamn som börjar på forhand-), markörkontroll åt båda hållen, och en statisk invariant.
- Det finns inget skript för en miljö per rättning. railway_provision.py tar bara main och development (argparse choices, testet test_onboard_skript.py:62 och INV-DEPLOY-002). En ny fil behövs, i stället för att vidga ENVIRONMENTS.
- environmentDelete och städning finns inte någonstans i repot. Det finns heller ingen livslängd, inget tak för antal samtidiga miljöer och ingen inventering av öppna miljöer.
- Det finns ingen vitlista för variabler vid kloning. En klon av development eller main ärver allt, också FLYTT_NYCKEL, FLYTT_MAL_URL, RESEND_API_KEY, SMTP_*, INTERNLARM_*, SYNK_*_PG_URL, inkorgslösenord som miljövariabler (poller.password_env_name) och webhookhemligheter.
- Det finns ingen grind som släpper in bara vissa användare i en miljö, t.ex. en lista med användar-id i proxy.ts eller i auth. Inloggningen släpper i dag in alla konton som finns i databasen.
- Det finns ingen markör för en förhandsmiljö. mirror_meta känner bara environment och lage. Varje miljö som inte heter development räknas av synkvakten som en icke-spegel, och miljo() skriver godkand_i med miljönamnet.
- Det finns ingen körväg där en agent kan bygga miljön. Databasstegen (migrering från noll, utdrag) går inte från en molnsession, som bara når port 443. De måste köras som ett Railway-jobb, som migrera och synk, eller från Antons dator.
- Det finns ingen koppling mellan ett supportärende, en fix-gren och en miljö, och ingen status som kunden kan följa (projektregeln om förlopp och utfall efter omladdning).
- Det finns ingen testgrind för fix-grenen medan GitHub Actions står still (BESLUT.md:257-283).
- DEPLOY.md:716-735 beskriver en nattlig spegling via spegla-dev.yml. Workflowen finns inte (.github/workflows saknar den). Hur färska developments icke-SYNK-tabeller är syns inte i repot.

## Fällor
- En klon ärver flyttvägen. Om en förhandsmiljö klonas från development följer FLYTT_NYCKEL och FLYTT_MAL_URL med, och miljöns egen panel kan skicka signerade paket till main. Mottagaren vägrar bara när MÅLET är en spegel (admin_flytt.py:18-21), inte när avsändaren är det. Variablerna måste strykas.
- Lage måste vara 'envags'. Utan lage, eller med en markör som saknar lage, skickar scheduler.process_godkanda godkännanden som gjorts efter seeded_at (scheduler.py:883-887). Kunden kan då få ett riktigt mejl att gå ut från förhandsmiljön. Grinden finns bara i scheduler.py:698-700 (lage='envags'). Som andra lager ska api sakna RESEND_API_KEY och SMTP_*, så att LoggingSendProvider väljs (DEPLOY.md:390-393).
- En klon av main tar med synk och migrera-main. Synkens SYNK_MAIN_PG_URL pekar på postgres.railway.internal, som i den nya miljön är den nya databasen. Railway_synk stoppar då på markörkontrollerna, men tjänsten ska inte finnas där alls. RAILWAY.md:204 mätte kloning när bara tre tjänster fanns. Vad en klon gör med cron-tjänster som synk och overvakning (som mejlar larm till snajpsupport@gmail.com) är inte mätt.
- DATABASE_URL som referens löses inte ut i en klonad miljö (RAILWAY.md:210-213). Det måste vara literalt, som provision() gör (railway_provision.py:205-215, 336-338).
- railway_provision.py --apply genererar och roterar hemligheter som saknas i .env.deploy (RAILWAY.md:53-56). Kör den aldrig mot main eller development för att testa en förhandsmiljö.
- Migrationskedjan från noll skapar inte platform_admins-raden (RAILWAY.md:219-258), och auth.users-triggern on_auth_user_created skapar en arbetsyta per inkopierad användare om replica-läge inte används (railway_seed_dev.py:32-35).
- Rollernas lösenord (snajp_app, snajp_web) och synk_las inloggning sätts utanför migrationerna. En ny databas behöver samma steg, och värdena får aldrig synas i en logg.
- Utdraget från main kräver en ny läsroll med bredare rätt än synk_las. Den rollen kan läsa alla kunders arbetsytor. Den ska vara skrivskyddad som synk_las, och urvalet per kund måste avgöras i koden, inte av RLS, eftersom rollen kringgår RLS.
- Development som källa är fel underlag. Bara 28 tabeller hålls färska. Kunskapsbasen, inställningarna och kontona är från senaste fullspegling, vars datum inte syns i repot.
- Webbplatsbedömningen är hemlig (CLAUDE.md). Den följer med i prospects och liknande tabeller och syns för plattformsadmin. Ett kundutdrag får inte ta med fält från webbpoolen som kunden inte får se, och i A finns bara kundens egna rader. Granska vilka fält i prospects med flera som bär webbrevision.
- Railway-planen ligger under Pro (JURIDIK_ATGARDER.md rad 47, BESLUTSUNDERLAG A4). Exakt plan och gränsen för antal miljöer per projekt är inte belagda i repot. Volymer stannar på 500 MB om de skapats på provplanen (HANDOFF-2026-10-17, rad 26).
- Den publika *.up.railway.app-domänen når vem som helst, och inloggningssidan svarar. Skyddet är databasens innehåll, bara kundens konton plus en lista över tillåtna användare. Magic link och lösenordsåterställning har ingen mejlväg (RAILWAY.md:262-264), så kunden loggar in med samma lösenord som i main (hashen följer med auth.users).
- Modellkostnaden: förhandsmiljön behöver GOOGLE_SERVICE_ACCOUNT_JSON (Vertex i EU, annars stoppar uppstarten enligt config.py:937). Den är listad som hemlighet per miljö (railway_provision.py:54-57), och delar kreditprojektet med development om dess nyckel återanvänds.
- Alternativ B: ett grenbyte under pågående test byter koden under kunden. Databasen måste tömmas och fyllas om vid kundbyte, annars ser kund 2 kund 1:s data. Det får aldrig vara en tyst ombyggnad.
- Alternativ C: en rättning bakom flagga i main kräver en release (PR development → main med Antons code owner-review och ord enligt §8.1a) innan kunden kan testa. Kunden testar då i produktionen med sina riktiga utskick påslagna.

## Kräver Anton
- Ett beslut om kostnad och plan. Kontot ligger under Pro. Exakt plan och gränsen för antal miljöer är inte belagda i repot. Grov uppskattning från Railways listpriser, inte mätt här: web, api, Postgres och Redis på tomgång tar ungefär 1–1,5 GB RAM, alltså cirka 10–15 USD i månaden om en miljö står hela månaden, eller ungefär 1–2 USD för en rättning som lever 2–3 dygn, plus byggtid. Bygget tar uppskattningsvis 10–20 minuter per miljö (två byggen parallellt, migrering från noll, utdrag), också omätt. Pro behövs redan av andra skäl (säkerhetskopior, JURIDIK_ATGARDER 4b) och är en planuppgradering med betalning.
- Att slå på inloggningen för den nya läsrollen i main (samma handgrepp som synk_las, synkflytt-runbook steg 6) och försegla (Seal) dess anslutningsvariabel i Railways gränssnitt, eftersom Seal inte går via API:t (BESLUT.md:285-287).
- Det dataskyddsmässiga ja:et till att kopiera en kunds personuppgifter till en ny miljö hos samma leverantör (Railway, Amsterdam), med en notering i docs/compliance/datamangder.md och BESLUT.md. Antons beslut, enligt mönstret för development-spegeln.
- GitHub-betalningen, så att verify.yml och pr-granskning.yml körs på fix-grenarna igen. Annars måste testgrinden flyttas till Railway (BESLUT.md:257-283).
- En token: om skapandet och raderingen av miljöer ska köras automatiskt från api-tjänsten eller ett jobb behövs en Railway-token med projekträtt som hemlighet hos Railway. Det är Antons hand (skapa och försegla).
- Varje release till main: PR development → main kräver Antons code owner-review och uttryckliga ord, även för en rättning som kunden godkänt i sin förhandsmiljö.
- Valet mellan A och B (och att C inte duger för buggrättningar), och om förloppet i förhandsmiljön ska synas för kunden eller bara för plattformsadmin (projektregeln 2026-10-10 säger: fråga Anton).

# karta inlogg

Kartläggningen gäller inloggning och åtkomst per inlogg. Jag har bara läst kod och inte ändrat något. Auth.js v5 kör med JWT-session. Token bär bara identiteten: `sub` = auth.users.id och `tvafaktor` (lib/auth.ts:192-230, låst av INV-AUTH-001). Proxyn kör på Edge och svarar bara på en fråga: finns en token? Den gör ingen databasfråga (proxy.ts:51-65). Allt annat läses färskt per request. Arbetsytan läses via getWorkspaceContext (lib/workspace.ts:61-114: profiles.workspace_id → workspaces + business_contexts + exists(platform_admins)). Den funktionen är den gemensamma punkt som admin (lib/auth/admin.ts:81), tenant (lib/snajp/tenant.ts:176), onboardinggrinden och identiteten (INV-SEC-014) läser ifrån. En användare har exakt en arbetsyta. Det finns ingen medlemskapstabell, bara profiles.workspace_id, som är not null (db/migrations/000_base_schema.sql:26-32). Plattformsadmin kan "testa som kund" via cookien snajp.vy=kund:<slug> (lib/vy.ts:72-96, lib/actions/vy.ts:27-71). Cookien gäller bara om getPlatformAdmin() svarar ja, och den kräver att sessionen gått igenom tvåfaktor när kontot har tvåfaktor (lib/auth/admin.ts:54-72). Nyckeln hämtas via tenant_api_key_for_admin(), som gör om admin-kontrollen i databasen (042_admin_impersonation.sql). Besöket loggas med log_admin_impersonation (123_adminlogg.sql:176-210). Skrivningar under ett besök märks is_test (app/api/snajp-support/_auth.ts:54-72), men besöket är inte tekniskt läsläge (tenant.ts:225-226).

Följande finns INTE i dag:
- Någon grind som begränsar en körande miljö till vissa arbetsytor.
- Någon generell funktionsflagga per arbetsyta eller användare. Det som finns är products (005), addons (022, med CHECK-låst värdelista), is_demo (034) och backendens agent_configs.settings (023) per tenant.
- Inloggning mellan värdar (cross-host SSO).
- En gren- eller spegelmiljö per kund.

Grinden för en spegel bör sitta på tre ställen, plus en spärr av vägarna som skapar konton:
(1) I signIn-callbacken och Credentials authorize (lib/auth.ts:128-210). Anrop: tillåten om profiles.workspace_id ingår i en miljövariabel, till exempel SPEGEL_ARBETSYTOR, eller om användaren står i platform_admins. Kontrollen ska ligga före upsertOAuthUser, som annars SKAPAR användare och därmed arbetsytor (lib/auth.ts:83-95, 202).
(2) Samma kontroll i getWorkspaceContext, så att den fångar en giltig token som tagit sig förbi. Där fäller den layouter, API-proxyn och admin stängt på en gång.
(3) Proxyn kan bara kontrollera att en token finns, eftersom den kör på Edge utan databas. Den kan inte vara den bärande grinden.
Därtill ska signUpWithPassword, startDemo och requestDemoAccess (lib/actions/auth.ts:204, 257, 295) vara avstängda i spegeln.

Cookies följer inte med. Auth.js-cookien är host-only, eftersom ingen domain är satt i lib/auth.ts, så inloggningen på www.snajp.se gäller inte på spegelns värd. Kunden måste logga in på nytt eller få en signerad engångsöverlämning.

Den största fällan gäller datan. Synken mellan main och development kopierar INTE auth.users, profiles, workspaces, workspace_tenant_keys eller ss_tenants (scripts/railway_synk.py:118-149). En kund som onboardas i main nästa vecka (Buddy) finns alltså inte alls i development, och "samma lösenord om användarraden finns i kopian" fungerar inte utan en egen kopiering. Development-databasen innehåller dessutom alla kunders riktiga data (DEPLOY.md:193-215). Att släppa in en kund i en kopia av den krockar med projektregeln. Det beslutet är Antons.

## Saknas
- Ingen grind som begränsar inloggningen i en miljö till vissa arbetsytor. Credentials authorize och signIn-callbacken släpper varje giltigt konto (lib/auth.ts:128-210), och ingen miljövariabel bär tillåtna arbetsytor eller användare.
- Ingen generell funktionsflagga per arbetsyta eller användare. addons har en CHECK-låst värdelista (022), så ett nytt värde kräver en migration. products styr menyn. agent_configs.settings ligger per tenant i backenden, inte per användare.
- Ingen medlemskapsmodell. En användare har exakt en arbetsyta (profiles.workspace_id not null), så en kund kan inte vara medlem i en spegelarbetsyta parallellt med sin vanliga.
- Ingen inloggning mellan värdar och ingen överlämningstoken. Den enda engångstoken är lösenordsåterställningen (lib/reset-token.ts), och den lagras i den egna databasen. En spegel med egen databas kan alltså inte slå upp en token som utfärdats i main eller development.
- Ingen spegel eller grenmiljö per kund eller ärende. environmentCreate finns (scripts/railway_provision.py:261), men en klonad miljö får en tom databas och en DATABASE_URL-referens som inte löses ut (RAILWAY.md:204-217).
- Ingen kopiering av identitetstabeller mellan miljöer. Synken tar inte auth.users, profiles, workspaces, workspace_tenant_keys eller ss_tenants (scripts/railway_synk.py:118-149). En kund som skapas i main finns alltså inte i development och inte i en kopia av den.
- Kundbesöket är inte tekniskt läsläge, bara is_test-märkning av skrivningar (lib/snajp/tenant.ts:225-226; _auth.ts:54-72).
- Ingen spärr mot att skapa konton i en begränsad miljö: signUpWithPassword, startDemo, requestDemoAccess och OAuth-upsert skapar användare och arbetsytor fritt.
- platform_admins-raden skapas inte av migrationskedjan. En ny miljö har därför ingen admin förrän scripts/admin_cleanup.py körts (RAILWAY.md:219-231).

## Fällor
- En spegel som är en kopia av development innehåller alla kunders riktiga ärenden och adresser (DEPLOY.md:193-215: 'Inga länkar till web-development för utomstående', 'samma personkrets som produktionen'). RLS skyddar per arbetsyta, men att ge Buddy en inloggning i en sådan miljö bryter projektregeln. Spegeln behöver en databas med bara den kundens arbetsyta, eller syntetiska data.
- AUTH_SECRET gör mer än att signera sessionen. Den härleder också nyckeln för tvåfaktorhemligheterna, bunden till userId (lib/auth/tvafaktor-krypto.ts:10-48), och HMAC:en i inloggningsspärren (lib/auth/inloggningsforsok.ts:26, 116). Ger spegeln en egen AUTH_SECRET kan en admin med aktiv TOTP inte logga in där med de kopierade hemligheterna. Delar spegeln AUTH_SECRET med källmiljön är en sessions-JWT därifrån giltig i spegeln om cookien förs över. Värdbundna cookies skyddar i praktiken, men grinden i signIn och getWorkspaceContext måste ändå finnas.
- Auth.js-cookien är host-only, eftersom ingen cookies.domain är satt i lib/auth.ts:192-230. Inloggningen på www.snajp.se eller web-development följer inte med till spegelns värd, och kunden måste logga in där. Sätt inte domain=.snajp.se för att lösa det: då gäller sessionen på alla underdomäner, kundernas <slug>.snajp.se inräknade.
- OAuth i spegeln: upsertOAuthUser skapar användaren innan någon kontroll görs (lib/auth.ts:202), och triggern on_auth_user_created skapar då arbetsyta och profil. Allowlist-kontrollen måste ligga före upsert, eller så ska OAuth vara avstängt i spegeln (AUTH_GOOGLE_ID och AUTH_MICROSOFT_ENTRA_ID_ID osatta). Redirect-URI:erna hos Google och Microsoft gäller dessutom per värd.
- Proxyn kör på Edge utan databas (proxy.ts:6-13), så tillåtna arbetsytor kan inte kontrolleras där. Att lägga workspace_id i JWT:n för att proxyn ska kunna läsa den bryter mot INV-AUTH-001.
- tenantSlugFromHost tolkar första etiketten som kundslug (lib/tenants/index.ts:110-116). En spegel på buddy.snajp.se, eller en Railway-domän vars första etikett råkar vara en configfils-tenant, ger kundens branding i app/layout.tsx och 404 på publika sidor (lib/tenants/server.ts:26-30). Den första etiketten får inte vara en kundslug.
- Railways plan tillåter en egen domän per tjänst, och www har den (DEPLOY.md:523-525). En spegel får därför en *.up.railway.app-domän om planen inte uppgraderas.
- En klonad Railway-miljö ärver variablerna. DATABASE_URL-referensen löses inte ut (RAILWAY.md:210-213). SITE_URL, om den är satt, pekar på källan, så mejllänkar (appBasUrl, lib/mail.ts:40-50) går till fel värd. Nycklarna SNAJP_KEY_* och SNAJP_MASTER_API_KEY följer också med och kan peka på källans backend.
- Utskick och inkorg: en spegel med kundens riktiga inkorgsuppgifter kan läsa samma IMAP-brevlåda och skicka skarpt. Development stoppar det med mirror_meta och scheduler.skickas_har (scripts/railway_synk.py:36-45), och en ny spegel behöver samma markör. Gäller också DeepSeek-spärren (Settings.llm_provider_fault) för miljöer med riktiga kunddata.
- En kund som onboardas i main (Buddy nästa vecka) har ingen auth.users-, profil- eller arbetsyterad i development, eftersom synken inte för över identitetstabellerna. 'Samma lösenord om användarraden finns i kopian' fungerar bara om spegeln får användarraden och dess scrypt-hash kopierad i ett eget steg.
- Andra agenter ändrar just nu proxy.ts, lib/routes.ts, lib/actions/auth.ts, lib/actions/vy.ts, lib/snajp/tenant.ts, app/admin/layout.tsx och identitetsrouten (INV-SEC-014 och INV-AUTH-002). En grind i samma filer krockar med deras ocommittade arbete.
- Kundbesökets cookie snajp.vy lever i 30 dagar (lib/actions/vy.ts:51-56) och raderas först vid nästa inloggning (lib/actions/auth.ts:144). En admin som går från spegeln tillbaka till main behåller vyläget där.

## Kräver Anton
- Får en kund logga in i en miljö vars databas innehåller andra kunders data? Det gäller till exempel en kopia av development, som enligt DEPLOY.md:193-215 hanteras som produktionen. Annars måste spegeln byggas med bara kundens egen arbetsyta.
- Domän och kostnad: en Railway-miljö per ärende kostar pengar, och planen ger bara en egen domän per tjänst. Duger *.up.railway.app-adresser för kunden, eller ska planen uppgraderas (en betalning)?
- Hur kunden kommer in i spegeln: samma lösenord (kräver att kundens auth.users-rad med lösenordshash kopieras till spegeln), en signerad engångslänk (kräver en ny delad hemlighet mellan miljöerna) eller lösenordsåterställning i spegeln.
- Får spegeln köra kundens riktiga inkorg, skicka mejl och anropa språkmodeller med kundens data, eller ska den gå i ett spärrat läge med mirror_meta och utan utskick?
- Räcker kundens godkännande i spegeln för att rättningen ska gå vidare till development, eller granskar en människa först? Release till main kräver som alltid Antons uttryckliga ja och hans merge (code owner).
- Ska spegelns och ärendets förlopp synas för kunden eller bara för plattformsadmin? Projektregeln 2026-10-10 säger att Anton ska tillfrågas när det är tveksamt.
- Ska spegeln ha en egen AUTH_SECRET? Då kan inte admins kopierade tvåfaktorhemligheter användas där. Med samma AUTH_SECRET som källmiljön blir en sessionstoken därifrån portabel till spegeln.

# karta agentkoppling

Det finns ingen väg i dag som skickar ett kundärende vidare till en agent som skriver kod. Det saknas ett arbetsflöde, ett skript, en tabell och en kö för det. Det som finns att bygga på är tre saker. Två arbetsflöden skapar redan GitHub-ärenden med etikett (`overvakning.yml`, `sakerhetsbevakning.yml`, båda med `issues: write` och bara `GITHUB_TOKEN`). `platform_events` ger fel per kund med run_id och detaljer. `untrusted_content.py` kan märka kundtext som data.

Det viktigaste fyndet: repot oloflun/snipe-leads är PUBLIKT just nu. `gh api` ger visibility=public, updated_at 2026-11-23T23:08Z, och github.com/oloflun/snipe-leads svarar 200 utan inloggning. Ändå säger docs/BESLUT.md:1611 (2026-11-18) att repot är privat, och rad 1624 säger att docs/compliance ska flyttas ut först om repot görs publikt igen. Den mappen ligger på origin/development: 108 spårade filer med docs/compliance, JURIDIK_ATGARDER och DPIA:n. Inget nytt beslut om publikt finns i BESLUT.md.

Följden för det här bygget är att ärendetext, kundnamn, mejladresser eller arbetsytenamn aldrig får skrivas till GitHub (ärenden, PR-text, commits eller grennamn). Ärendet ska ligga i Snajps egen databas, och agenten ska få ett avpersonifierat arbetsunderlag.

Grenskyddet är svagare än DEPLOY.md påstår. På main finns bara regeluppsättningen main-3: en godkännande granskning, inget krav på kodägare, och admin-rollen får alltid gå förbi. development har i praktiken inget skydd, eftersom "Standard rules" har tomt include. Kör en agent med Antons token kan den alltså pusha direkt till development. Den grenen deployar sig själv mot en databas som speglar produktionen.

Rekommendationen är en kö i Snajps databas som en agent hämtar ur. Agenten ska ha en egen GitHub-identitet utan admin-roll och utan workflow-rätt, och får bara öppna en PR mot development från grenen fix/arende-<id>. En ny regeluppsättning på development ska kräva PR och Antons godkännande. Kundtexten kapslas som opålitlig data, går först genom ett steg utan verktyg som gör den strukturerad, och agenten har inga hemligheter, ingen databas och ingen produktionsåtkomst.

## Saknas
- Någon tabell eller kö för felrapporter från kunder till Snajp. Ingen migration innehåller till exempel felrapport, plattformsarende eller feedback till plattformen, och ss_tickets används bara för kundernas egna supportärenden.
- Något arbetsflöde, skript eller tjänst som startar en kodande agent. Det finns ingen claude-code-action, codex-action, workflow_dispatch för en agent eller claude -p i repot (bara scripts/benchmark_leads_kedja.py nämner en modellnyckel).
- Någon GitHub-identitet för en agent, alltså en GitHub App eller en finkornig token utan admin-roll. Allt går i dag via Antons gh-inloggning, som har admin och därmed går förbi regeluppsättningarna.
- Grenskydd på development: regeluppsättningen 'Standard rules' har include=[] och skyddar därför ingen gren.
- Kodägarkrav på main i praktiken (require_code_owner_review=false) trots att DEPLOY.md påstår det
- Någon etikett eller ärendemall för kundfel (bara driftlarm, sakerhetsbevakning och ai-oro finns)
- Någon avpersonifiering eller pseudonym för en kund mot GitHub eller en agent
- Något sätt att länka en PR eller gren till ett Snajp-ärende och visa status tillbaka i Snajp. Det finns ingen webhook, ingen polling av PR-status och inget fält för pr_url eller gren.
- Någon miljö per gren hos Railway. DEPLOY.md beskriver bara development och main, och Vercel-previewerna är avvecklade.
- Någon post i BESLUT.md om att repot gjorts publikt igen efter 2026-11-18

## Fällor
- REPOT ÄR PUBLIKT. All ärendetext, alla kund- och arbetsytenamn, mejladresser, skärmbilder och platform_events-detaljer som hamnar i ett GitHub-ärende, en PR-text, en commit, ett grennamn eller en testfixtur blir världsläsbara. Även privata repon ligger hos ett amerikanskt underbiträde, vilket avtalsfrågan i PUB punkt 8 redan rör. GitHub-ärenden ska alltså bära högst ett ärende-id, en avpersonifierad sammanfattning och vilken sida det gäller.
- Antons token är admin (RepositoryRole 5) och går alltid förbi main-3 och 'Standard rules'. En agent som kör med `gh` på Antons maskin kan merga till main och pusha direkt till development. development deployar sig själv inom några minuter mot en databas som speglar produktionen (CLAUDE.md, DEPLOY.md:27-58).
- Ändringar i migrationerna når databasen vid push till development: migrera.yml kör kedjan mot spegeln utan att en människa godkänt. En agent-PR som rör db/migrations får aldrig mergas utan Antons granskning.
- En PR från en gren i samma repo mot main kör migrera.yml-jobbet 'granska' med SCHEMA_LASNYCKEL, och i reserven ENV_DEPLOY och PG-hemligheterna. pull_request kör arbetsflödet från PR:ens egen version, så en agent som får ändra .github/workflows kan läcka hemligheterna. Agentens identitet får därför ALDRIG ha workflow-rätt (scope workflow eller workflows: write), och agentens PR:er ska bara gå mot development.
- verify.yml ger GITHUB_TOKEN actions: write och issues: write på varje PR. Ett ändrat arbetsflöde i en agentgren skulle få de rättigheterna. Samma spärr gäller: ingen workflow-rätt.
- Promptinjektion: kundens text är opålitlig och går in till en agent som har skrivrätt i repot. Kapslingen i untrusted_content.py hjälper men räcker inte ensam. Därför behövs ett steg utan verktyg som gör texten strukturerad (sida, steg, förväntat, faktiskt), att agenten saknar nätverk utöver paketregistren, att den saknar hemligheter i miljön, och att den inte kan merga.
- Grennamn och commitmeddelanden blir också publika. Använd fix/arende-<uuid-prefix> och aldrig kundens eller företagets namn (CLAUDE.md: webbbedömningen är hemlig, och kunddata får inte läcka).
- Actions-minuterna tog slut 2026-11-23 medan repot var privat (BESLUT.md:225). En agent som körs i GitHub Actions kostar minuter om repot görs privat igen. Ett publikt repo har obegränsade minuter, men då är exponeringen den som beskrivs ovan.
- GitHubs schemaläggare tappar de flesta schemalagda körningar (overvakning.yml:42-60). En agentkö som hämtar på schema i Actions blir opålitlig, så hämtningen bör ske hos Railway eller lokalt i en loop.
- DeepSeek är förbjudet i miljöer med kunddata (CLAUDE.md). Den kodande agentens modell och region måste stämma med Bilaga 3 i PUB, annars skickas felrapporten med kunddata till ett underbiträde som inte är godkänt.
- Den 'spegel' kunden ska testa i får inte peka på development-databasen utan att man tänkt efter, eftersom den är en spegel av produktionen med alla kunders data. Spegeln måste begränsas till den egna kundens tenant och inloggning, och agenten själv ska aldrig nå den databasen.
- Andra agenter ändrar just nu bland annat app/api/snajp-support/_auth.ts, _lib.ts, proxy.ts och lib/routes.ts (ocommittat). Bygg inte inloggningsgrindar för spegeln ovanpå de halvfärdiga filerna.

## Kräver Anton
- BRÅDSKANDE: repot är publikt sedan cirka 2026-11-23 23:08 UTC, trots beslutet att det är privat (BESLUT.md:1611). docs/compliance (DPIA, juridiska åtgärder, incidentloggen och PUB-utkastet) ligger därmed publikt. Är det avsiktligt (till exempel för Actions-minuterna eller grenskyddet), eller ska repot göras privat igen och mappen flyttas ut?
- Ska den kodande agenten ha en egen GitHub-identitet (GitHub App eller finkornig token)? Att skapa den kräver Antons hand: kontoåtgärd och OAuth i tredjepartskonsol.
- Godkänn en ny regeluppsättning på development som kräver PR och granskning, med undantag bara för Antons användare. Det ändrar arbetssättet för Sebbe och för alla agenter som i dag pushar direkt till development.
- Ändra main-3 till require_code_owner_review=true och ersätt rollundantaget med Antons användar-id, så att DEPLOY.md stämmer.
- Vilken modell och region får den kodande agenten använda för felrapporter? Står leverantören i PUB Bilaga 3, och får felrapportens innehåll gå dit?
- Var ska agenten köras: på Antons maskin (fönsterlöst), som en tjänst hos Railway, eller i GitHub Actions? Det sista kostar Actions-minuter om repot är privat och exponerar mer om det är publikt.
- Vilka personuppgifter får följa med till agenten: bara ärende-id, sida och avpersonifierade steg, eller också kundens fritext? Och ska ingenting alls från kunden skrivas till GitHub så länge repot är publikt?
- Ska kundens 'det fungerar' i spegeln vara ett krav före Antons granskning, eller bara information till honom? Ett ja från kunden får aldrig ersätta Antons ja inför development och main.

