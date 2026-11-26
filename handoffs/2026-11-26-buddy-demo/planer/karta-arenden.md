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

## Befintligt
- snajp-support/app/agent/support_agent.py:923-967 Supportkedjans huvudfunktion. Signaturen har flaggorna is_test, arbetsyta (kundens nyckeltal i kontexten), forlopp (stegnamn till chatten), aterta och vid_arende för återupptagning.
- snajp-support/app/agent/support_agent.py:1-13 Modulens grundprincip: varje steg är ett eget JSON-anrop, och sidoeffekter görs i kod, aldrig av modellen via verktyg.
- snajp-support/app/agent/support_playbook.py:22-108 Stegordningen (playbooken): cs:ticket-triage → cs:customer-research → cs:draft-response → cs:customer-escalation → cs:kb-article → snajp:retention-conversation → snajp:humanizer-svenska, med requires-villkor.
- snajp-support/app/agent/support_agent.py:1303-1341 Triagesteget. JSON-kontraktet: category, priority, sentiment, escalate, kundfakta, ber_om_manniska, inom_amnesomradet, missforstadd, sprak och sokfraga_sv. Det här är den naturliga platsen för ett nytt avsiktsfält, eftersom triagen redan klassar.
- snajp-support/app/agent/support_agent.py:428-479 Triagesvaret normaliseras: ja/nej-fälten listas i _TRIAGE_JA_NEJ, och ett nytt fält måste in här.
- snajp-support/app/agent/support_agent.py:1377-1403 Varje chattmeddelande skapar ett EGET ss_tickets-ärende och sparar det inkommande meddelandet. Med aterta återanvänds ärendet.
- snajp-support/app/agent/support_agent.py:1636-1645, 1974 Eskaleringstriggers i kod: påhopp, kund_bad_om_manniska, sakerhet, utanfor_amnesomradet och fortydligandetak, och därefter modellbedomning.
- snajp-support/app/agent/support_agent.py:198-233 Regexen _KANSLIGT (juridik, pengar tillbaka, GDPR-rättigheter, fakturafel) och _KRIS, som eskalerar i kod.
- snajp-support/app/agent/support_agent.py:2033-2069 KB-förslagssteget: sparar save_agent_suggestion(kind='kb_article') i SAMMA tenant som körningen och skriver aldrig själv i kunskapsbasen (INV-LEARN-001).
- snajp-support/app/agent/support_agent.py:2352-2417 Sidoeffekterna vid eskalering: update_ticket(status='escalated', priority='high', escalation_reason), skicka_prioriterat (ett mejl per kund och eskalering) och integrationshändelsen arende_eskalerat.
- snajp-support/app/agent/support_agent.py:2419-2449 Samtalsläget sparas: lage overlamnad/agent, orsak och overlamnad_ticket_id. I gästläget häver agenten aldrig en överlämning (INV-ESC-001).
- snajp-support/app/agent/support_agent.py:805-920 Under en överlämning körs ingen modell: meddelandet läggs i det överlämnade ärendets tråd och får en kvittens, eller inget svar alls om en människa redan svarat. En ny fråga släpps vidare till gästläget.
- snajp-support/app/agent/support_agent.py:64, 674-687 Överlämningen gäller i 24 timmar efter senaste livstecken (OVERLAMNING_GILTIG_TIMMAR).
- snajp-support/app/agent/step_runner.py:1-17, 431, 555, 568, 648 run_step: ett modellanrop per steg i JSON-läge (response_format json_object), med kontraktskontroll och ett omtag. Steget har inga sidoeffekter.
- snajp-support/app/agent/tools.py:65-254 Gamla funktionsverktyg från Agents SDK (find_or_create_customer, create_ticket, escalate_to_human, send_response m.fl.). Bara DEMO_TOOLS (search_knowledge_base, send_response) används, av den publika demoagenten.
- snajp-support/app/agent/bookkeeping_agent.py:43, 873, 899 Mönstret för verktygsanrop som FINNS: Agents SDK Runner.run med @function_tool. Tenanten tas ur kontexten och verktygen är vitlistade.
- snajp-support/app/agent/bookkeeping_chat_tools.py:113-260 Verktygsmoduler med samma mönster: tenanten ur kontexten och resultatet sparas.
- snajp-support/app/agent/support_regler.py:217-260 Orsakskoderna för överlämning (ORSAKER) och ber_om_manniska som kodtrigger.
- snajp-support/app/agent/overlamning.py:1-60 Medarbetarens sida av överlämningen: samtalsutskrift över alla kundens ärenden, medarbetarsvar (author='human') och aterlamna.
- snajp-support/app/api/chattar.py:32-97 API för överlämnade chattar: GET /api/chattar, GET /api/chattar/{customer_id}, POST .../svar (med kanalleverans) och POST .../aterlamna. Tenant-skopat.
- support-webb/components/vyer/ChattarVy.tsx:1-30 Takeover-gränssnittet finns BARA i den fristående supportportalen support-webb, inte i huvudappen. DEPLOY.md säger att portalen står kvar tills Anton och Sebbe avgör om den ska in i huvudappen.
- snajp-support/app/api/chat.py:165-230, 236-310 POST /api/chat (202 plus jobb): avtalsgrinden, rate limit per X-Snajp-User, supportbudgeten och köning via chattstrom. Varje nytt ChatRequest-fält måste med både i enqueue och i rekonstruktionen i hantera_strom_jobb.
- snajp-support/app/api/chat.py:320-366, 368-390 POST /api/chat/samtal: chattfönstret läser tillbaka samtalet och läget overlamnad. GET /api/jobs/{id} visar stegförloppet.
- snajp-support/app/api/schemas.py:15-31 ChatRequest har bara message, subject, channel, customer_email, customer_name, attachments, is_test och arbetsyta. Det finns inget fält för sida, arbetsyta-id eller ärendetyp.
- snajp-support/app/jobs/store.py:17-18 Jobbstatusen lever i Redis eller minnet med TTL 1 h, så den räcker inte för ett utfall som ska finnas kvar efter omladdning.
- snajp-support/app/api/tickets.py:10-29 Ärendet kan bara läsas med ärende-id under tenantens egen nyckel: GET /api/tickets/{id} och GET /api/customers/{id}/history.
- db/migrations/002_snajp_support.sql:22-57 Tabellerna ss_tickets (status open/in_progress/escalated/resolved/closed, priority, escalation_reason, parent_ticket_id), ss_conversations (1:1 mot ärendet) och ss_messages.
- db/migrations/067_integrationer_och_kanaler.sql:41-43 Check-villkoret för kanal i ss_tickets: web, email, whatsapp, messenger, slack, teams.
- snajp-support/app/config.py:43-73 Kategorierna (måste matcha DB-checken): teknisk_support, garanti, leverans, utbildning, retur_reklamation, betalning, orderstatus, ovrigt. KB_SALJ ligger i en ocommittad ändring.
- db/migrations/066_support_samtalslage.sql:30-57 ss_chat_state (lage, misslyckade_i_rad, erbjod_manniska, overlamnad_orsak, overlamnad_ticket_id, sprak) och author-kolumnen på ss_messages, med RLS per app.tenant_id.
- db/migrations/051_agent_suggestions.sql:30-52 agent_suggestions: kind är begränsat till 'kb_article' och 'marknadsinsikt' via check-villkor, status ny/godkand/avfard, och ett dedupe-index.
- db/migrations/20261118100000_121_kb_forslag.sql:48-64 ss_kb_forslag: artikelutkast med status vantar/tillagd/avvisad som kunden själv beslutar om.
- snajp-support/app/api/kb.py:327-392 GET /api/kb/forslag och POST /api/kb/forslag/beslut: kundens godkännande blir en ny artikel, atomiskt, och svarscachen bumpas.
- snajp-support/app/api/leads.py:1353-1440, 1533 GET /api/agent/forslag och POST .../godkann (skapar KB-artikeln, en människas klick), .../arende och .../avfard.
- snajp-support/app/notifications/prioriterat_mejl.py:1-50, 234-317 Det prioriterade mejlet till snajpsupport@gmail.com: aldrig kundens text, bara tenant, vad, varför och en länk. Ärendelänken pekar på /admin/kunder?arende=<id>.
- snajp-support/app/email_pipeline/processor.py:519-533, 534-600, 695, 771-878 Inkorgskedjan för mejl: Snajps egna larm går till Att hantera, och begränsad behandling, klassning, triage, ärende, eskalering eller autosvar eller utkast följer.
- snajp-support/app/agent/triage.py:1-40 Mejltriagen i ett enda anrop med supportens grundprompt som systemmeddelande.
- snajp-support/app/email_pipeline/klassning.py:104-115 INKORG_JEV (off/prov/auto) styr Jev i inkorgen, skilt från IRIS_JEV.
- snajp-support/app/config.py:241-317, 457-471 Modellval: llm_provider (standard openai, bara lokalt), MODEL, vision_model, inkorg_jev och jev_motor/jev_modell.
- snajp-support/app/config.py:803-944 llm_provider_fault(): fäller DeepSeek och OpenAI där datan är riktig, fäller fel modellnamn per steg, regioner utanför EU, LLM_BASE_URL utanför EU och Gemini utan läsbart servicekonto.
- snajp-support/app/agent/llm.py:1-35, 551-605 Den centrala LLM-klienten (Vertex AI med OAuth, EU-regioner). Dokumenterar varför DeepSeek inte är primärmodell.
- snajp-support/app/agent/arbetsyta_siffror.py:1-22 arbetsyta-flaggan: tenantens egna nyckeltal läggs i kontexten. Den sätts bara av den autentiserade testchatt-routen och strippas i den publika.
- snajp-support/app/api/deps.py:62-72 require_tenant: nyckeln avgör tenanten, och master-nyckeln vägras mot kunddata.
- app/api/snajp-support/testchatt/route.ts:1-45 Den autentiserade testchatten: tenanten tas ur sessionen (proxyAsTenant), arbetsyta=true läggs till server-side och anropet går till /api/chat. Det är kundens EGEN agent.
- app/api/snajp-support/chat/route.ts:1-60 Den anonyma chatten (INV-SEC-010): tenanten kommer från en slug, och bara sessionsidentiteter (@session.snajp.se) godtas.
- app/api/snajp-support/_auth.ts:7, 15-74 proxyAsTenant härleder tenanten och API-nyckeln ur sessionen (requireSnajpTenant). Rubriken X-Snajp-Identitet ingår i en ocommittad ändring.
- lib/tenants/snajp.ts:1-35 Snajp finns som egen tenant: slug snajp, supportKeyEnv SNAJP_KEY_SNAJP. I databasen heter tenanten 'Hjärtstartare-piloten'.
- components/snajp/SupportWorkspaceTabs.tsx:30-59, 88-96 Flikarna i dashboardens Kundtjänst: Översikt, Ärenden, Testmail, Dolda och Testchatt. Testchatten är SupportChat med testMode.
- components/snajp/SupportChat.tsx:414-485, 523-660, 744-870, 918-988 SupportChat: pollning av samtalet (överlämning och medarbetarsvar), jobbpollning med steg, kort för KB-uppladdning (text och PDF) till kundens EGEN kunskapsbas, och förslagskort (godkänn, avfärda, öppna som ärende) i testläget.
- components/snajp/JournalVy.tsx:14-27, 119-140 Journalen för kundens läsroll: körningar, kostnad och överlämnade chattar via /api/chattar. Den kan inte svara.
- components/admin/FelOchEskaleringar.tsx:13-35 Adminytans Fel och eskaleringar: platform_events plus ss_tickets med status escalated.
- components/AppShell.tsx:184-186, 323-325 Notiscentret i appen gäller bara Leads (lead_handelser, migration 149, läses per arbetsyta). Det finns inga supportnotiser.
- lib/actions/notiser.ts:1-50 Mejlnotiser per användare (notification_preferences).
- lib/bolag.ts:237-247 Underbiträdena: GitHub finns med, Anthropic/Claude saknas.
- docs/JURIDIK_ATGARDER.md:61-76, 76-90 Punkt 28: 'AI-kodverktyg läser testmiljöns kunddata – Besluta policy' är obeslutad (Ä). Punkt 16: testmiljön är en full kopia av produktionen.
- ARCHITECTURE_INVARIANTS.md:577-592 INV-LEARN-001: agenten skriver aldrig själv i kunskapsbasen. Bara en människas klick skapar en artikel.
- ARCHITECTURE_INVARIANTS.md:293-318 INV-SEC-012: artikeltext är opålitlig text i användarposition och ska kapslas med wrap_untrusted_content.

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

## Fästpunkter
- Avsikten bestäms i triagen. Lägg ett fält 'avsikt' (hjalp|kb_kontext|felrapport) i triagens JSON-kontrakt (support_agent.py:1303-1341) och normalisera det i _normalisera_triage (428-479). Det kostar inget extra modellanrop. Uppgifterna (sammanfattning, steg att återskapa, förväntat mot faktiskt, KB-titel och KB-text) tas i ett nytt villkorat steg efter triagen, i samma form som cs:kb-article (2033-2069), alltså JSON-steg plus sidoeffekt i kod, enligt mönstret 'modellen resonerar, koden agerar'.
- Sidoeffekterna läggs i kodblocket efter rad 2352: skapa felärendet, skicka notis och sätt samtalsläge. Eskalering eller överlämning ska inte återanvändas.
- Vill man ha verktyg finns mönstret redan: Agents SDK med @function_tool, tenanten ur kontexten och vitlistade verktyg (bookkeeping_chat_tools.py, kvitto_chat_tools.py, Runner.run i bookkeeping_agent.py:873). Det bryter dock supportkedjans princip att stegen saknar sidoeffekter.
- En ny autentiserad Next-route i form av testchatt/route.ts, men proxad med Snajps nyckel (lib/tenants/snajp.ts supportKeyEnv) och med server-satt kontext ur sessionen: kundens tenant_id, user_id, roll och sidväg. Klienten får aldrig själv ange tenanten.
- ChatRequest får ett kontextfält, t.ex. 'kundkontext' {tenant_id, user_id, sida}, som bara den nya routen sätter och den publika strippar. Det läggs in i schemas.py, i enqueue och i rekonstruktionen i chat.py.
- En ny tabell (additiv, idempotent migration), t.ex. ss_felarenden: id, snajp_ticket_id (ss_tickets i Snajps tenant), kund_tenant_id, rapporterad_av (user_id), sida, beskrivning, status (mottagen, analyseras, rattning_pagar, spegel_klar, kund_testar, kund_godkand, i_development, i_main, avvisad), gren, pr_url, spegel_url, tillaten_user_id, tidsstämplar och en händelselogg. Lägg in RLS och grindning för båda tenanterna.
- KB-bidrag läggs som ss_kb_forslag (status vantar) i KUNDENS tenant med en kolumn för källan (chatt eller ärende). Kunden beslutar via befintliga /api/kb/forslag/beslut (kb.py:338-392), och chatten kan visa samma kort som kb-forhandsvisning och forslag-kort (SupportChat.tsx:744-988). Skrivningen görs i kod med kundens tenant_id satt i transaktionen (postgres.py:291-296), aldrig av modellen.
- Status visas i chatten genom att utöka /api/chat/samtal eller lägga till en egen tenant-skopad endpoint som läser ss_felarenden för den inloggade kunden. SupportChat pollar redan samtalet (414-485) och kan visa ett statuskort per ärende.
- Snajps sida: ärendet syns i adminytans FelOchEskaleringar och via arendelank (/admin/kunder?arende=). Det prioriterade mejlet kan återanvändas med ny rubrik, utan text.
- Notiser till kunden: mönstret finns i lead_handelser (migration 149) och räknaren i AppShell.tsx:184-186. Mejlnotiser går via notification_preferences (lib/actions/notiser.ts).
- Chattrutan placeras i den befintliga ytan (regeln 2026-11-24). En hjälpknapp i AppShell eller Rail bredvid de befintliga kontrollerna, eller en flik i Kundtjänst, inte en ny panel ovanpå. Den ska finnas på svenska och engelska via lib/i18n.tsx (INV-COPY-001).

## Kräver Anton
- Får en kodande agent (Claude Code, Anthropic, USA) läsa kundens felrapport, och i så fall hur mycket? Antingen pseudonymiserad sammanfattning och länk, eller full text med skärmbild. Anthropic är inte underbiträde (lib/bolag.ts), och JURIDIK_ATGARDER punkt 28 är obeslutad. Om ja ska underbiträdet in på alla fyra listorna i samma ändring.
- Spegelns data: ska kundens spegel gå mot development (riktig data från alla kunder), en egen kopia av bara kundens tenant, eller syntetisk data? Vem utöver kunden når den, och hur länge lever den?
- Ska kundens kunskapsbidrag från chatten alltid bli ett utkast som kunden godkänner (INV-LEARN-001, som i dag), eller vill Anton ha ett undantag (waiver) för text som kunden uttryckligen ber om att få inlagd?
- Hur mycket av förloppet ska kunden se: alla steg (analys, gren, PR, spegel) eller bara mottagen, spegel klar, ute? Projektregeln 2026-10-10 säger att Anton ska tillfrågas när det är tveksamt.
- Det godkända flödet efter kundens test: automatisk merge till development, eller Antons eller Sebbes granskning först? Varje release till main kräver fortfarande Antons uttryckliga ja (§8.1a).
- Snajps tenant som mottagare: avtalsgrind (kraver_avtal), dygnsbudget för alla kunders hjälpchattar och modell (MODEL=gemini-3.5-flash-lite gäller bara development tills releasen).
- Ska takeover och ärendehantering för Snajps egna ärenden ske i support-webb (ChattarVy) eller flyttas in i huvudappens admin? DEPLOY.md säger att det beslutet väntar på Anton och Sebbe.
- Gallring och registerförteckning för felärenden och chattar där Snajp är personuppgiftsansvarig, inte biträde.
