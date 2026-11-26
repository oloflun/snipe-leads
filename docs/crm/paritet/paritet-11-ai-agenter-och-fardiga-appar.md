# Paritet 11: AI-agenter och färdiga appar

I Twenty finns en AI-assistent som användaren pratar med i en chatt och inkorg, sparade agenter med instruktion, modell, roll och utlösare, färdigheter och verktyg som agenterna använder, en egen MCP-server för externa AI-klienter, krediter och mätning av förbrukningen, samt färdiga appar (mötesinspelning, Slack, WhatsApp, LinkedIn, berikning, webbsökning med flera). Snajp CRM har ingen del av detta i dag: CRM-koden anropar ingen språkmodell (`docs/crm/SVENSK-STANDARD.md` § 2.7), och det AI-arbete Snajp gör (Iris, Jev, utkasten, supportagenten, testchatten) ligger i Leads och Support utanför CRM:et och flyttar in i fas 4 och 5.

Antal per läge (räknat i tabellen nedan, 271 rader): verifierad 0, byggd 0, delvis 2, inte gjord 259, avstår 10.

Underlag: `docs/crm/underlag/twenty-11-ai-agenter-och-fardiga-appar.md`. Läget gäller arbetskatalogen 2026-11-26. `docs/crm/PLAN-MIGRERING.md` har ingen fas för AI-assistent, agenter, MCP eller appar från tredje part; "ej planerad" i kolumnen Fas betyder att planen saknar fas för raden. Fas 4 står där funktionen finns i Leads (`snajp-support/app/leads/`), fas 5 där den finns i Support, Inställningar eller resten av appen (`docs/crm/MIGRERING-FUNKTIONSLISTA.md`). De två delvis-raderna bygger på CRM-API:ts hastighetsgräns och tidslinjen.

## De största luckorna

1. Det finns ingen AI-chatt i CRM:et. Användaren kan inte fråga om sina bolag, personer och affärer på vanlig svenska, och ingen assistent förstår "det här bolaget" utifrån sidan man står på.
2. Det går inte att skapa en egen agent med instruktion, modell och utlösare som reagerar på en posthändelse eller körs på schema.
3. Ingen MCP-server: Claude, Cursor eller ChatGPT kan inte ansluta till CRM:et och läsa eller skriva poster. API-nycklarna finns, men bara för REST-API:t.
4. Inga godkännandekort i CRM:et där en agent föreslår en ändring eller ett mejl som en människa godkänner. Snajps utkast som en människa godkänner finns i Leads och flyttar in först i fas 4.
5. Ingen inkorg för konversationer mellan kollegor och assistenten: inga trådar, direktmeddelanden, kanaler, tilldelning, snooze eller notiser.
6. Inga färdigheter och inga verktyg att ge assistenten, och inga externa MCP-servrar att ansluta.
7. Ingen mötesinspelning, transkribering eller sammanfattning (Call Recorder, Fathom, Fireflies, Granola, Meet, Teams).
8. Inga kanaler in från Slack, Teams, WhatsApp eller LinkedIn, varken för meddelanden på posterna eller för att prata med agenten.
9. Ingen synlig förbrukning: inga krediter, ingen användningssida och ingen kvot per medlem. Snajp har en dygnsbudget och en driftruta utanför CRM:et (fas 4 och 5).
10. Inga fält för senaste kontakt på personer, bolag och affärer. Tidslinjen visar kontakterna, men inget fält sammanfattar dem.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| AI-001 | Användaren ställer frågor om CRM-datan på vanligt språk i en AI-chatt. | inte gjord | Ingen chatt i CRM:et, och CRM-koden anropar ingen språkmodell (`docs/crm/SVENSK-STANDARD.md` § 2.7). Kvittoassistenten (funktionslistan KV-60) svarar bara om kvitton. | ej planerad |
| AI-002 | Chatten förstår "den här posten" utifrån sidan användaren står på. | inte gjord | Finns inte. | ej planerad |
| AI-003 | AI-steg i arbetsflöden som berikar, klassar, sammanfattar, skriver utkast och poängsätter. | inte gjord | Inte i CRM:et. I Leads klassar Jev bolag (`snajp-support/app/leads/jev.py`), poängsättningen motiverar sig (`scoring.py`) och utkast och uppföljningar skrivs av agenten (`follow_up_generator.py`), men inte som steg i ett arbetsflöde. | 4 |
| AI-004 | Administratören tilldelar en roll till en AI-agent. | inte gjord | Inga agenter och inga roller i CRM:et. | ej planerad |
| AI-005 | AI-förbrukning dras först från medlemmens personliga kvot, sedan från arbetsytans krediter. | inte gjord | Inga krediter i CRM:et. | ej planerad |
| AI-006 | Kunden väljer vilka AI-modeller arbetsytan får använda. | inte gjord | Kunden väljer ingen modell; Snajp väljer leverantör i driften (`snajp-support/app/config.py`, `llm_provider`). | ej planerad |
| AI-007 | Självhostad administratör lägger till egna AI-leverantörer och slutpunkter. | avstår | Gäller bara egen drift av Twenty. Snajp driver en enda tjänst och väljer leverantör i sin egen konfiguration (`snajp-support/app/config.py`). | |
| AI-008 | CRM:et är en MCP-server som externa AI-assistenter kan ansluta till. | inte gjord | Ingen MCP-slutpunkt. CRM:et har bara REST-API:t `/v1` (`snajp-support/app/api/crm_v1.py`). | ej planerad |
| AI-009 | Inloggning mot MCP-servern med OAuth och dynamisk klientregistrering. | inte gjord | Ingen MCP och ingen OAuth i CRM-API:t. | ej planerad |
| AI-010 | Inloggning mot MCP-servern med API-nyckel. | inte gjord | Ingen MCP. API-nycklar med omfång finns för REST-API:t (`snajp-support/app/crm/nycklar.py`), men de når ingen MCP-slutpunkt. | ej planerad |
| AI-011 | Inställningssidan visar färdig MCP-konfiguration att kopiera in i klienten. | inte gjord | Utvecklarvyn (`components/crm/app/UtvecklareVy.tsx`) visar nycklar och API-dokumentation, ingen MCP-konfiguration. | ej planerad |
| AI-012 | MCP standardläge med ett fast utbud av post-, metadata- och hjälpverktyg. | inte gjord | Finns inte. | ej planerad |
| AI-013 | MCP direktläge med ett verktyg per objekt och operation. | inte gjord | Finns inte. | ej planerad |
| AI-014 | MCP metaläge med verktyg för att lära sig och köra andra verktyg. | inte gjord | Finns inte. | ej planerad |
| AI-015 | Självhostad MCP kräver att instansens publika adress är rätt inställd. | avstår | Gäller bara egen drift av Twenty. | |
| AI-016 | Skrivbordsnotiser för nya meddelanden i chattinkorgen, med nivå och förhandsvisning. | inte gjord | Ingen chattinkorg och inga webbnotiser i CRM:et. | ej planerad |
| AI-020 | Skapa en agent med namn, instruktion och modell. | inte gjord | Inga sparade agenter i CRM:et. | ej planerad |
| AI-021 | Agentens utseende med avatarfärg och avatarform. | inte gjord | Finns inte. | ej planerad |
| AI-022 | Agentens svar som fri text eller som JSON enligt ett schema. | inte gjord | Finns inte. | ej planerad |
| AI-023 | Modellval per agent, med arbetsytans standard och fem nivåer från extra snabb till extra smart. | inte gjord | Finns inte; modellen väljs av Snajp i driften. | ej planerad |
| AI-024 | Per agent slå på leverantörens inbyggda webbsökning. | inte gjord | Inte i CRM:et. Leads söker med Geminis inbyggda Google-sökning (`snajp-support/app/leads/discovery.py`), men det är ingen inställning per agent. | 4 |
| AI-025 | Resonemangsnivå per modell. | inte gjord | Finns inte. | ej planerad |
| AI-026 | En agent kan märkas privat och knytas till den som skapade den. | inte gjord | Finns inte. | ej planerad |
| AI-027 | System- och appagenter går att justera lokalt utan att originalet försvinner. | inte gjord | Finns inte. | ej planerad |
| AI-028 | Behörighet krävs för att läsa och ändra agenter. | inte gjord | Inga agenter och inga behörighetsflaggor i CRM:et. | ej planerad |
| AI-029 | Högst 300 steg per agentkörning. | inte gjord | Finns inte. | ej planerad |
| AI-030 | En agent kan köras programmatiskt utanför arbetsflöden med egen grundinstruktion. | inte gjord | Finns inte. | ej planerad |
| AI-031 | Agentens utlösare är en posthändelse eller ett schema. | inte gjord | Finns inte. Posthändelser går bara ut som webhooks (`snajp-support/app/crm/webhooks.py`). | ej planerad |
| AI-032 | En agent kan deklareras i en apps manifest. | inte gjord | Inga appar. | ej planerad |
| AI-033 | Standardassistenten har ett namn och en profil som arbetsytan kan ändra. | inte gjord | Ingen assistent i CRM:et. | ej planerad |
| AI-034 | Datapolicy per arbetsyta som kräver dataplacering i EU och nolllagring hos leverantören. | inte gjord | Ingen policy per kund. Det som finns är en spärr för hela plattformen: DeepSeek fäller uppstarten i miljöer med kunddata (`snajp-support/app/config.py:llm_provider_fault`), och CRM-koden anropar ingen modell. | ej planerad |
| AI-035 | Modellkatalogen stöder tio leverantörstyper. | inte gjord | Ingen modellkatalog i CRM:et. Snajp väljer leverantör i driften (`config.py`, `llm_provider`). | ej planerad |
| AI-036 | Verktygen är indelade i tretton kategorier med elva postoperationer per objekt. | inte gjord | Inga AI-verktyg. | ej planerad |
| AI-037 | Agenten kan pausa och vänta på människan med fråga, formulär eller förslag. | inte gjord | Finns inte. | ej planerad |
| AI-038 | Föreslagen åtgärd visas som ett kort med mall och status, och upptäcker om posten ändrats. | inte gjord | Finns inte. | ej planerad |
| AI-039 | Särskilda chattverktyg: tiga, reagera, knyta konversationen till poster, avsluta uppstart. | inte gjord | Finns inte. | ej planerad |
| AI-040 | Referenser i chattext till poster, objekt, fält och vyer som blir klickbara. | inte gjord | Finns inte. | ej planerad |
| AI-041 | Inkorg för chattrådar per medlem med läst, oläst, arkivera, snooza och följa. | inte gjord | Finns inte. | ej planerad |
| AI-042 | Förvalda filter i chattinkorgen. | inte gjord | Finns inte. | ej planerad |
| AI-043 | Notisnivå för chattinkorgen. | inte gjord | Finns inte. | ej planerad |
| AI-044 | Trådtyperna vanlig chatt och direktmeddelande mellan medlemmar. | inte gjord | Finns inte. | ej planerad |
| AI-045 | Svaret strömmas till klienten med händelser för kö, fel och slut på krediter. | inte gjord | Finns inte. | ej planerad |
| AI-046 | Sammanfattning av en agentkörning med tokens, kostnad, verktygsanrop och tid. | inte gjord | Inte i CRM:et. Leads och Support sparar körningar med tokens och steglogg (`agent_runs`, se `snajp-support/app/leads/sparad_research.py`), och driftrutan med körningar, tokens och modell finns i Support (funktionslistan SU-063). | 5 |
| AI-047 | Verktyg från externa MCP-servrar räknas som destruktiva om inget annat sägs. | inte gjord | Inga externa MCP-servrar. | ej planerad |
| AI-048 | Kodtolkens indatafil får vara högst 50 MB. | inte gjord | Ingen kodtolk. | ej planerad |
| AI-049 | AI-utvärdering av svar med frågor av typen val, poäng och ja eller nej. | inte gjord | Finns inte. | ej planerad |
| AI-050 | Lista agenter och hämta en agent. | inte gjord | Finns inte. | ej planerad |
| AI-051 | Ändra en agent, med kontroll mot datapolicyn. | inte gjord | Finns inte. | ej planerad |
| AI-052 | Radera en eller flera agenter. | inte gjord | Finns inte. | ej planerad |
| AI-053 | Bara ägaren byter en agents synlighet mellan privat och delad. | inte gjord | Finns inte. | ej planerad |
| AI-054 | Privata agenter går över till en efterträdare när ägaren lämnar. | inte gjord | Finns inte. | ej planerad |
| AI-055 | Tilldela, byta och ta bort roll för en agent. | inte gjord | Finns inte. | ej planerad |
| AI-056 | Chatten skapar, listar, ändrar och raderar agenter åt användaren. | inte gjord | Finns inte. | ej planerad |
| AI-057 | En agent som startas av en utlösare behandlar postdata som information, aldrig som instruktioner. | inte gjord | Inte i CRM:et. Leads och Support lägger opålitlig text i ett avgränsat datablock och aldrig i instruktionsposition (`snajp-support/app/leads/untrusted_content.py:wrap_untrusted_content`). | 4 |
| AI-058 | Agenten startas av posthändelser, med bevakade fält, villkor och satsläge. | inte gjord | Finns inte. | ej planerad |
| AI-059 | Schemalagda agenter startas av ett jobb varje minut. | inte gjord | Finns inte. | ej planerad |
| AI-060 | Spärr mot skenande agentkörningar, högst 100 per agent och timme. | inte gjord | Inte i CRM:et. Leads har en dygnsbudget per kund som stoppar körningar (`snajp-support/app/leads/budget.py:kontrollera_leads_budget`, funktionslistan LK-009). | 4 |
| AI-061 | Körlogg per agent med status, modell, tokens, krediter, indata och svar. | inte gjord | Inte i CRM:et. Körningarna sparas i `agent_runs` och visas i driftrutan i Support (funktionslistan SU-063, bara för plattformsadmin). | 5 |
| AI-062 | Agentlistan visar de tio senaste körningarna per agent. | inte gjord | Ingen agentlista. | ej planerad |
| AI-064 | Köra en agent via API från en app, en API-nyckel eller en användare. | inte gjord | Finns inte. | ej planerad |
| AI-065 | Regler för agentkörning via API: arkiverad agent, fortsatt tråd, kör som medlem, väntetid. | inte gjord | Finns inte. | ej planerad |
| AI-066 | Fri AI-generering utan sparad agent, med behörighetsomfång och stopp. | inte gjord | Finns inte. | ej planerad |
| AI-067 | Bilagor till agentkörningar, högst tio per meddelande, med orsak när en fil inte kan levereras. | inte gjord | Finns inte. | ej planerad |
| AI-068 | Vilka verktyg en programmatisk agentkörning får och inte får använda. | inte gjord | Finns inte. | ej planerad |
| AI-069 | Körningen stoppas när krediterna tar slut. | inte gjord | Inga krediter i CRM:et. | ej planerad |
| AI-070 | Agenten kan vänta på att en post skapas, ändras eller raderas. | inte gjord | Finns inte. | ej planerad |
| AI-071 | Agenten kan vänta en angiven tid. | inte gjord | Finns inte. | ej planerad |
| AI-072 | Agenten ställer en fråga med svarsalternativ. | inte gjord | Finns inte. | ej planerad |
| AI-073 | Agenten ber användaren fylla i ett formulär. | inte gjord | Finns inte. | ej planerad |
| AI-074 | Agenten föreslår en åtgärd, till exempel ett mejl, som användaren godkänner, avböjer eller redigerar. | inte gjord | Inte i CRM:et. I Leads skriver agenten utkast som en människa godkänner innan något skickas (`snajp-support/app/leads/autonomy.py`, nivån `draft`; CLAUDE.md regel 17). | 4 |
| AI-063 | Statistik för en agent över 14 dagar: körningar, tokens, krediter och tid. | inte gjord | Ingen agentstatistik. | ej planerad |
| AI-080 | Konversationen är ett eget objekt med titel, ägare, tilldelad, kanal och senaste aktivitet. | inte gjord | Inga AI-konversationer i CRM:et. Tidslinjen visar leadens mejlsvar (`snajp-support/app/crm/tidslinje.py`), men det är kundens mejltrådar, inte chattrådar. | ej planerad |
| AI-081 | Deltagare per tråd med senast läst, följer och omnämnd. | inte gjord | Finns inte. | ej planerad |
| AI-082 | En konversation kan knytas till bolag, personer och affärer och listas på posten. | inte gjord | Finns inte. | ej planerad |
| AI-083 | Meddelanden, meddelandedelar och reaktioner sparas som poster. | inte gjord | Finns inte. | ej planerad |
| AI-084 | En tur är en körning av assistenten eller en agent, med status, tokens och krediter. | inte gjord | Finns inte i CRM:et. | ej planerad |
| AI-085 | Skapa en chattråd och skicka meddelanden till assistenten, med kö medan den svarar. | inte gjord | Inte i CRM:et. Testchatten mot supportagenten finns i Support och flyttar till `/crm/kundtjanst/testchatt` (funktionslistan SU-070 till SU-087). | 5 |
| AI-086 | Avbryta ett svar och försöka igen. | inte gjord | Finns inte. | ej planerad |
| AI-087 | Strömning med återanslutning och ikappläsning. | inte gjord | Finns inte. | ej planerad |
| AI-088 | Besked när konversationen blivit för lång eller ingen modell finns. | inte gjord | Finns inte. | ej planerad |
| AI-089 | Assistentens grundinstruktion: ladda färdighet, lär verktyg, utför. | inte gjord | Finns inte. | ej planerad |
| AI-090 | Assistentens regler för små datauttag, massverktyg och sammanslagning av dubbletter. | inte gjord | Finns inte. | ej planerad |
| AI-091 | Assistenten känner till CRM:ets egna begrepp som favoriter och menyposter. | inte gjord | Finns inte. | ej planerad |
| AI-092 | Assistenten knyter konversationen till de poster den arbetat med. | inte gjord | Finns inte. | ej planerad |
| AI-093 | Flera deltagare i samma tråd, där bara den som frågar ger behörighet. | inte gjord | Finns inte. | ej planerad |
| AI-094 | Svar i markdown med klickbara referenser till poster. | inte gjord | Finns inte. | ej planerad |
| AI-095 | Sidans kontext (post, listvy, inställningssida) skickas med till assistenten. | inte gjord | Finns inte. | ej planerad |
| AI-096 | Behörig användare kan se den sammansatta systeminstruktionen. | inte gjord | Finns inte. | ej planerad |
| AI-097 | Vilka verktyg som förladdas och vilka som utesluts i chatten. | inte gjord | Finns inte. | ej planerad |
| AI-098 | Bygga egna gränssnittskomponenter med hjälp av chatten. | inte gjord | Finns inte. | ej planerad |
| AI-099 | Emojireaktioner på meddelanden. | inte gjord | Finns inte. | ej planerad |
| AI-100 | Inkorgsåtgärder per tråd och medlem: läst, oläst, arkivera, snooza, följ. | inte gjord | Finns inte. | ej planerad |
| AI-101 | Tilldela en tråd till en medlem. | inte gjord | Finns inte. | ej planerad |
| AI-102 | Lägga till deltagare i en tråd. | inte gjord | Finns inte. | ej planerad |
| AI-103 | Direktmeddelanden mellan kollegor. | inte gjord | Finns inte. | ej planerad |
| AI-104 | Omnämnanden och regler för när assistenten svarar i en tråd med flera. | inte gjord | Finns inte. | ej planerad |
| AI-105 | Räknare över öppna trådar per filter för märken i menyn. | inte gjord | Finns inte. | ej planerad |
| AI-106 | Appar skickar meddelanden till medlemmarnas inkorg, med förslag att godkänna. | inte gjord | Finns inte. | ej planerad |
| AI-107 | Kanaler som delade inkorgsmappar styrda av roller. | inte gjord | Finns inte. | ej planerad |
| AI-108 | Radera en kanal och flytta dess trådar. | inte gjord | Finns inte. | ej planerad |
| AI-109 | Trådar i en kanal: flytta, markera klar, snooza och öppna igen. | inte gjord | Finns inte. | ej planerad |
| AI-110 | Webbpush-notiser för chattrådar. | inte gjord | Finns inte. | ej planerad |
| AI-111 | En ny arbetsyta kan sättas upp genom en chatt med assistenten. | inte gjord | Finns inte. Snajps onboarding (fas 5, funktionslistan SK-1xx) är en stegguide, ingen chatt. | ej planerad |
| AI-112 | Arbetsytans och medlemmens kreditförbrukning i chatten kan hämtas. | inte gjord | Finns inte. | ej planerad |
| AI-120 | Modellkatalog med språk-, transkriptions- och utvärderingsmodeller. | inte gjord | Ingen modellkatalog. | ej planerad |
| AI-121 | Leverantörskonfiguration på instansnivå med nycklar, bas-URL och region. | avstår | Gäller bara egen drift av Twenty. Snajp konfigurerar sina leverantörer i driften (`snajp-support/app/config.py`). | |
| AI-122 | Modellbeskrivning med pris, kontextfönster, modaliteter och dataplacering. | inte gjord | Finns inte. | ej planerad |
| AI-123 | Vilka filtyper en modell kan ta emot direkt. | inte gjord | Finns inte. | ej planerad |
| AI-124 | Administratören slår på och av modeller och väljer standardmodell per nivå. | avstår | Gäller adminpanelen i en egen drift av Twenty. Snajp väljer modell i sin konfiguration (`snajp-support/app/config.py`). | |
| AI-125 | Arbetsytans modellinställningar: datapolicy, automatiskt val, modell per nivå. | inte gjord | Finns inte. | ej planerad |
| AI-126 | Leverantörernas inbyggda webbsökning och dess kostnad per anrop. | inte gjord | Inte i CRM:et. Leads använder Geminis inbyggda Google-sökning (`snajp-support/app/leads/discovery.py`). | 4 |
| AI-127 | Kostnaden räknas om till krediter. | inte gjord | Inga krediter. | ej planerad |
| AI-128 | Telemetri och spårning av modellanrop. | inte gjord | Inga modellanrop i CRM:et. | ej planerad |
| AI-129 | Föråldrad REST-slutpunkt för textgenerering. | inte gjord | Finns inte. | ej planerad |
| AI-130 | Svara på ett väntande verktygsanrop (fråga, formulär, förslag). | inte gjord | Finns inte. | ej planerad |
| AI-131 | AI-statistik för arbetsytan: antal konversationer, färdigheter och verktyg. | inte gjord | Finns inte. | ej planerad |
| AI-132 | Automatisk utvärdering av svar med en bedömningsmodell. | inte gjord | Finns inte. | ej planerad |
| AI-133 | Verktyg för att låta AI bygga, förhandsvisa och publicera gränssnittskomponenter. | inte gjord | Finns inte. | ej planerad |
| AI-140 | Skapa en färdighet: en namngiven instruktionstext som assistenten laddar vid behov. | inte gjord | Finns inte. | ej planerad |
| AI-141 | Lista, ändra, aktivera, inaktivera och radera färdigheter. | inte gjord | Finns inte. | ej planerad |
| AI-142 | Agentens redigerbara egenskaper, och standardagenter som bara kan överskrivas. | inte gjord | Finns inte. | ej planerad |
| AI-143 | Ansluta en extern MCP-server så att agenterna kan använda dess verktyg. | inte gjord | Finns inte. | ej planerad |
| AI-144 | Lista, ändra och radera anslutna MCP-servrar. | inte gjord | Finns inte. | ej planerad |
| AI-145 | Synka en MCP-servers verktygslista, manuellt eller automatiskt. | inte gjord | Finns inte. | ej planerad |
| AI-146 | Anropa ett verktyg på en extern MCP-server med tidsgräns och skydd mot interna adresser. | inte gjord | Finns inte. | ej planerad |
| AI-147 | Logga in mot en MCP-server med OAuth. | inte gjord | Finns inte. | ej planerad |
| AI-150 | Verktygsregister med leverantörer per kategori. | inte gjord | Finns inte. | ej planerad |
| AI-151 | Metaverktyg för att hitta, lära sig och köra verktyg och ladda färdigheter. | inte gjord | Finns inte. | ej planerad |
| AI-152 | Postverktyg per objekt som följer rollens rättigheter. | inte gjord | Inga AI-verktyg. Posterna nås bara via REST-API:t (`snajp-support/app/api/crm_v1.py`). | ej planerad |
| AI-153 | Godkännandemallar för skrivande verktyg som styr hur förslagskortet ser ut. | inte gjord | Finns inte. | ej planerad |
| AI-154 | Åtgärdsverktyg (HTTP, mejl, kalender, filer, kodtolk) styrda av behörighetsflaggor. | inte gjord | Finns inte. | ej planerad |
| AI-155 | Agenten gör HTTP-anrop mot valfri adress. | inte gjord | Finns inte. | ej planerad |
| AI-156 | Agenten skickar mejl eller sparar utkast från ett anslutet konto. | inte gjord | Inte i CRM:et. I Leads skriver agenten utkast och skickar efter godkännande (`snajp-support/app/leads/autonomy.py`, `send_provider.py`, `send_guard.py`). | 4 |
| AI-157 | Agenten listar de brevlådor användaren får skicka från. | inte gjord | Finns inte. | ej planerad |
| AI-158 | Agenten skapar en kalenderhändelse på Google eller Microsoft. | inte gjord | Ingen kalender i CRM:et. | ej planerad |
| AI-159 | Kodtolk som kör Python i sandlåda för analys, filer och diagram. | inte gjord | Finns inte. | ej planerad |
| AI-160 | Agenten läser PDF och bilder som ligger på poster. | inte gjord | Bilagor finns på posterna (`snajp-support/app/crm/objekt.py`, migration 164), men ingen agent läser dem. | ej planerad |
| AI-161 | Assistenten söker i hjälpcentret innan den svarar på hur något görs. | inte gjord | Inte i CRM:et. Hjälprutan med Snajps supportagent finns i dagens dashboard (`components/snajp/HjalpRuta.tsx`, BESLUT 2026-11-25). | 5 |
| AI-162 | Agenten delar en post med en medlem eller en roll. | inte gjord | Ingen delning per post i CRM:et. | ej planerad |
| AI-163 | Ladda upp filer i chattens lagring. | inte gjord | Finns inte. | ej planerad |
| AI-164 | Stora verktygsresultat sparas som fil och navigeras med sökvägar och textsök. | inte gjord | Finns inte. | ej planerad |
| AI-165 | MCP-verktyg som kan ändra data kräver godkännande. | inte gjord | Finns inte. | ej planerad |
| AI-166 | Verktygsindex för inställningssidan. | inte gjord | Finns inte. | ej planerad |
| AI-170 | All förbrukning registreras som användningshändelser per typ, resurs och enhet. | avstår | Enterprise-fil i förlagan (`core-modules/usage`). Snajp räknar sina egna modellanrop i `agent_runs` utanför CRM:et. | |
| AI-171 | Användningsanalys för administratören per användare, typ, app och modell. | avstår | Enterprise-fil i förlagan. Snajps egen motsvarighet är driftrutan i Support (funktionslistan SU-063). | |
| AI-172 | Personlig AI-kvot per medlem och vecka, med arbetsytans krediter som reserv. | avstår | Kvotprövningen och användarkrediterna är Enterprise-filer i förlagan. Snajp har en dygnsbudget per kund av egna skäl (`snajp-support/app/leads/budget.py`). | |
| AI-173 | Gränstyper: hastighet, kvot per period och lager, med svar som säger när man får försöka igen. | delvis | Hastighetsgräns finns: 600 anrop per minut och kund med 429 och `Retry-After` (`snajp-support/app/api/crm_v1.py:_TAK`; test `test_taket_ger_429_med_retry_after` i `snajp-support/tests/crm/test_api.py`). Saknas: kvoter per period, lagergränser och olika betalare (medlem, nyckel, agent). | ej planerad |
| AI-174 | Administratören listar, skapar, ändrar och raderar gränser. | inte gjord | Taket är fast i koden. | ej planerad |
| AI-175 | Kontroll av tak och användarkrediter på prenumerationen. | avstår | Enterprise-fil i förlagan. | |
| AI-180 | Inställningssidan för AI med flikar för översikt, MCP, modeller, färdigheter, verktyg och användning. | inte gjord | CRM:et har inga inställningssidor än. | ej planerad |
| AI-181 | Ändra assistentens namn och avatar. | inte gjord | Finns inte. | ej planerad |
| AI-182 | Välja när assistenten deltar i konversationer: aldrig, bara när den nämns eller automatiskt. | inte gjord | Inte i CRM:et. Snajps motsvarighet är "När agenten får svara själv" för supportagenten (funktionslistan IN-050 till IN-076, STATUS-MIGRERING 5.3). | 5 |
| AI-183 | Arbetsytans instruktioner som läggs till varje systeminstruktion, till exempel bolagsbeskrivning och ton. | inte gjord | Inte i CRM:et. Snajp har Företaget, Vad ni säljer och Så ska agenten låta (`snajp-support/app/leads/soul.py`; STATUS-MIGRERING 5.2). | 5 |
| AI-184 | Läsa systeminstruktionerna och användarkontexten. | inte gjord | Finns inte. | ej planerad |
| AI-185 | Välja modell per läge, automatiskt eller manuellt, med tabell över modellerna. | inte gjord | Finns inte. | ej planerad |
| AI-186 | Sidan för färdigheter: lista, sök, skapa, redigera, inaktivera och radera. | inte gjord | Finns inte. | ej planerad |
| AI-187 | Sidan för verktyg: lista, sök, skapa eget verktyg och se parametrar. | inte gjord | Finns inte. | ej planerad |
| AI-188 | AI-förbrukning över tid, per typ, modell och användare. | inte gjord | Inte i CRM:et. Dygnsbudgeten och driftrutan med körningar, tokens och modell finns i Support och Översikt (funktionslistan OV-030, SU-063). | 5 |
| AI-189 | MCP-fliken visar hur externa klienter ansluts. | inte gjord | Ingen MCP. | ej planerad |
| AI-190 | Lägga till och hantera fjärranslutna MCP-servrar med inloggning och synk av verktyg. | inte gjord | Finns inte. | ej planerad |
| AI-191 | Agentens sida listar dess färdigheter och verktyg. | inte gjord | Finns inte. | ej planerad |
| AI-200 | Chatten öppnas i sidopanelen och som inkorg. | inte gjord | CRM-skalet (`components/crm/app/CrmRam.tsx`) har ingen chatt. | ej planerad |
| AI-201 | Tomt läge med förslag som "sammanfatta posten" och "researcha företaget". | inte gjord | Finns inte. | ej planerad |
| AI-202 | Skrivfältet kan bifoga filer, poster och färdigheter. | inte gjord | Finns inte. | ej planerad |
| AI-203 | Ny tråd med mottagare: personer, en kanal eller assistenten. | inte gjord | Finns inte. | ej planerad |
| AI-204 | Diktering med webbläsarens taligenkänning. | inte gjord | Finns inte. | ej planerad |
| AI-205 | Meddelanden som skickas medan assistenten svarar köas och kan tas bort. | inte gjord | Finns inte. | ej planerad |
| AI-206 | Välja modellnivå i chatten med reglage, och slå på webbsökning. | inte gjord | Finns inte. | ej planerad |
| AI-207 | Meddelandevisning med markdown, resonemang, verktygsdetaljer och åtgärder som kopiera och försök igen. | inte gjord | Inte i CRM:et. Testchatten i Support visar bubblor, skeden medan jobbet går och tumme upp och ned (funktionslistan SU-070 till SU-087). | 5 |
| AI-208 | Visa hur mycket av kontextfönstret och krediterna en tråd använt. | inte gjord | Finns inte. | ej planerad |
| AI-209 | Banderoller när krediter eller gränser tar slut. | inte gjord | Finns inte. | ej planerad |
| AI-210 | Godkännandekort för föreslagna åtgärder, till exempel ett mejl att redigera och skicka. | inte gjord | Inte i CRM:et. Utkastgranskningen i Leads låter en människa redigera och godkänna agentens mejl före utskick (`snajp-support/app/leads/autonomy.py`). | 4 |
| AI-211 | Frågekort och formulärkort när agenten väntar på svar. | inte gjord | Finns inte. | ej planerad |
| AI-212 | Kalenderinbjudan med kontroll av deltagarnas lediga tider. | inte gjord | Finns inte. | ej planerad |
| AI-213 | Trådlista och trådhuvud med olästmarkering, status och snooze-meny. | inte gjord | Finns inte. | ej planerad |
| AI-214 | Välkomnande i en ny arbetsyta som anpassar uppsättningen. | inte gjord | Finns inte. | ej planerad |
| AI-300 | Call Recorder: en bot spelar in, transkriberar och sammanfattar möten i kalendern. | inte gjord | Ingen mötesinspelning. | ej planerad |
| AI-301 | Call Recorder: val per möte och medlem om vilka möten som spelas in. | inte gjord | Finns inte. | ej planerad |
| AI-302 | Call Recorder: appinställningar för inspelarens namn, tidsgränser och sammanfattningar. | inte gjord | Finns inte. | ej planerad |
| AI-303 | Call Recorder: debitering per inspelningstimme. | inte gjord | Finns inte. | ej planerad |
| AI-304 | Call Recorder: widgetar för deltagare och inspelningar på posten, och städning av bottar. | inte gjord | Finns inte. | ej planerad |
| AI-305 | Serverdelen för skrivbordsappen som spelar in samtal. | inte gjord | Finns inte. | ej planerad |
| AI-306 | Discord: skicka, ändra och radera meddelanden, reagera och lista kanaler. | inte gjord | Finns inte. | ej planerad |
| AI-307 | Webbsökning för agenter med kategori och antal träffar. | inte gjord | Inte i CRM:et. Leads söker på webben med Geminis Google-sökning och läser bolagens webbplatser (`snajp-support/app/leads/discovery.py`). | 4 |
| AI-308 | Fathom: importera inspelningar, transkript, sammanfattningar och åtgärdspunkter. | inte gjord | Finns inte. | ej planerad |
| AI-309 | Granola: importera mötesanteckningar och transkript. | inte gjord | Finns inte. | ej planerad |
| AI-311 | Fireflies: transkript och sammanfattningar kopplade till kalenderhändelsen. | inte gjord | Finns inte. | ej planerad |
| AI-312 | AI:n kan söka i produktens dokumentation via en publik MCP-server. | inte gjord | Inte i CRM:et. Snajps supportagent svarar på hjälpfrågor i Hjälprutan (`components/snajp/HjalpRuta.tsx`). | 5 |
| AI-313 | Fält för senaste kontakt på personer, företag och affärer, med riktning och vem. | delvis | Tidslinjen samlar postens kontakter (skickade mejl, svar, samtal, supportärenden) nyast först (`snajp-support/app/crm/tidslinje.py`; test `test_bolagets_tidslinje_samlar_crm_leads_och_support` i `snajp-support/tests/crm/test_tidslinje.py`). Saknas: egna fält för senaste kontakt, utgående och inkommande, vem som kontaktade, och fältet på affärer. | ej planerad |
| AI-314 | LinkedIn: meddelanden på personer och företag, med svar från CRM:et. | inte gjord | Finns inte. | ej planerad |
| AI-315 | Berika personer och företag ur People Data Labs. | avstår | Strider mot CLAUDE.md, leadsreglerna 3 och 6: en kontaktuppgift används bara om den kan styrkas tillhöra personen, och personuppgifter som plats, utbildning och sociala profiler ur en datamäklare är inga B2B-källor. Berikning av bolag ur SCB är en öppen fråga (`docs/crm/SVENSK-STANDARD.md`, fråga 4). | |
| AI-316 | Slack: fråga CRM:et från Slack och posta tillbaka. | inte gjord | Finns inte. | ej planerad |
| AI-317 | Teams: transkript och AI-sammanfattningar från möten. | inte gjord | Finns inte. | ej planerad |
| AI-318 | WhatsApp: meddelanden på personer och företag, med svar från CRM:et. | inte gjord | Finns inte. | ej planerad |
| AI-310 | Google Meet: importera transkript, anteckningar och inspelningar. | inte gjord | Finns inte. | ej planerad |
| AI-330 | Dokument ur mallar med platshållare, sparade på posten som PDF. | inte gjord | Finns inte. | ej planerad |
| AI-331 | Minsta exempelapp som visar hur en app byggs. | inte gjord | Ingen appplattform. | ej planerad |
| AI-332 | Spela in röst- eller videoanteckningar och spara dem på en post. | inte gjord | Bilagor finns (`snajp-support/app/crm/objekt.py`), men ingen inspelning. | ej planerad |
| AI-333 | Referensapp som visar alla delar en app kan ha. | inte gjord | Ingen appplattform. | ej planerad |
| AI-334 | Branschmall för fastighetsmäklare med egna objekt och fält. | inte gjord | Inga egna objekt eller branschmallar. | ej planerad |
| AI-335 | Testfixturer för appsystemet. | inte gjord | Ingen appplattform; ingen användarfunktion. | ej planerad |
| AI-340 | Skrivbordsappen visar kommande möten och ansluter till dem. | inte gjord | Ingen skrivbordsapp. | ej planerad |
| AI-341 | Skrivbordsappen spelar in mikrofon och systemljud. | inte gjord | Finns inte. | ej planerad |
| AI-342 | Skrivbordsappens inloggning, behörigheter och säkerhet. | inte gjord | Finns inte. | ej planerad |
| AI-343 | Färdigheter för kodagenter som bygger appar till CRM:et. | inte gjord | Ingen appplattform. | ej planerad |
| AI-360 | AI-steg i arbetsflöden med en sparad agent eller egen instruktion och modell. | inte gjord | Inga arbetsflöden i CRM:et (se paritet 06, AF-222). | ej planerad |
| AI-361 | Validering av AI-steget. | inte gjord | Finns inte. | ej planerad |
| AI-362 | AI-steget kan stanna och fråga en människa innan arbetsflödet fortsätter. | inte gjord | Finns inte. | ej planerad |
| AI-363 | Grundinstruktion och körlogg för AI-steg. | inte gjord | Finns inte. | ej planerad |
| AI-350 | Sexton inbyggda färdigheter, till exempel mötesförberedelse, affärsgenomgång och CRM-hygien. | inte gjord | Finns inte. | ej planerad |
| AI-351 | Standardkanalen "General" för chattrådar. | inte gjord | Finns inte. | ej planerad |
| AI-400 | Nitton verktyg för att bygga, köra och läsa arbetsflöden. | inte gjord | Inga arbetsflöden och inga AI-verktyg. | ej planerad |
| AI-401 | Agenten bygger ett helt arbetsflöde i ett anrop eller steg för steg. | inte gjord | Finns inte. | ej planerad |
| AI-402 | Kontrollera, testköra och felsöka arbetsflöden från chatten. | inte gjord | Finns inte. | ej planerad |
| AI-403 | Tre verktyg för att skapa och läsa instrumentpaneler med diagram. | inte gjord | Inga egna instrumentpaneler; översikten har fasta nyckeltal (`components/crm/app/OversiktVy.tsx`). | ej planerad |
| AI-404 | Sex verktyg för postsidornas layout och widgetar. | inte gjord | Finns inte. | ej planerad |
| AI-405 | Sjutton verktyg för objekt, fält och valideringsregler. | inte gjord | Ingen datamodellredigerare. | ej planerad |
| AI-406 | Tjugotvå verktyg för vyer, vyfält, filter och sortering. | inte gjord | Inga sparade vyer. | ej planerad |
| AI-407 | Sju verktyg för roller och behörigheter. | inte gjord | Inga roller i CRM:et. | ej planerad |
| AI-408 | Verktyg för navigeringens menyposter och för webhooks. | inte gjord | Webhooks finns i API:t (`snajp-support/app/crm/webhooks.py`), men inga AI-verktyg når dem. | ej planerad |
| AI-409 | Fyra verktyg för att lista, skapa, ändra och radera agenter. | inte gjord | Finns inte. | ej planerad |
| AI-410 | Fem verktyg för AI-byggda gränssnittskomponenter. | inte gjord | Finns inte. | ej planerad |
| AI-411 | Verktyg för mejlkampanjer: utkast, förhandsvisning av mottagare, provutskick, utskick och spärrar. | inte gjord | Inte i CRM:et. Leads har utkast, provmejl, schemalagt utskick och sändspärr (`snajp-support/app/leads/provmejl.py`, `scheduler.py`, `send_guard.py`), men inte som verktyg för en agent i CRM:et. | 4 |
| AI-412 | Varje logikfunktion med verktygsutlösare blir ett verktyg för agenten. | inte gjord | Inga logikfunktioner. | ej planerad |
| AI-413 | Destruktiva verktyg kräver godkännande. | inte gjord | Finns inte. | ej planerad |
| AI-420 | Verktyg som aldrig exponeras via MCP. | inte gjord | Ingen MCP. | ej planerad |
| AI-421 | MCP:s standardläge listar tio av tretton verktygskategorier. | inte gjord | Ingen MCP. | ej planerad |
| AI-422 | MCP-protokollets detaljer: förmågor, cachetips och felkoder. | inte gjord | Ingen MCP. | ej planerad |
| AI-430 | Lista agenter i en tabell med filter och flerval. | inte gjord | Finns inte. | ej planerad |
| AI-431 | Agentens sida har flikarna Översikt, Inställningar och Turer. | inte gjord | Finns inte. | ej planerad |
| AI-432 | Agentens inställningar: namn, beskrivning, avatar, modell och instruktioner. | inte gjord | Finns inte. | ej planerad |
| AI-433 | Agentens dataåtkomst per objekt: se, ändra, radera och förstöra. | inte gjord | Finns inte. | ej planerad |
| AI-434 | Agentens verktygsflaggor, tolv stycken. | inte gjord | Finns inte. | ej planerad |
| AI-435 | Utlösare i agentens gränssnitt, högst tjugo per agent. | inte gjord | Finns inte. | ej planerad |
| AI-436 | Översiktsfliken med nyckeltal och diagram över 14 dagar. | inte gjord | Finns inte. | ej planerad |
| AI-437 | Turfliken med körlogg grupperad per konversation. | inte gjord | Finns inte. | ej planerad |
| AI-438 | Testa agenten i sidopanelen. | inte gjord | Inte i CRM:et. Testchatten mot supportagenten finns i Support och flyttar till `/crm/kundtjanst/testchatt` (funktionslistan SU-070 till SU-087). | 5 |
| AI-439 | Radera en agent efter bekräftelse. | inte gjord | Finns inte. | ej planerad |
| AI-440 | Inbyggd standardkatalog med 125 modeller och möjlighet till egen lagrad katalog. | avstår | Gäller bara egen drift av Twenty (katalogen och `AI_CATALOG_STORAGE_PATH` är instansens). Snajp väljer modell i sin konfiguration (`snajp-support/app/config.py`). | |
| AI-441 | Fyra möjliga datapolicyer av region och nolllagring. | inte gjord | Ingen datapolicy per kund (se AI-034). | ej planerad |
| AI-450 | Call Recorder: schemalagda jobb, posthändelser och webhookar. | inte gjord | Finns inte. | ej planerad |
| AI-451 | Desktop Recorder: utlösare för skrivbordsappen. | inte gjord | Finns inte. | ej planerad |
| AI-452 | Discord: utlösare och HTTP-vägar. | inte gjord | Finns inte. | ej planerad |
| AI-453 | Fathom och Fireflies: historikimport, webhook och daglig avstämning. | inte gjord | Finns inte. | ej planerad |
| AI-454 | Granola: avstämning, verktyg och HTTP-vägar. | inte gjord | Finns inte. | ej planerad |
| AI-455 | Last Contact: sex posthändelser som uppdaterar senaste kontakt. | inte gjord | Inga fält för senaste kontakt (se AI-313). | ej planerad |
| AI-456 | LinkedIn och WhatsApp: HTTP-vägar för historik och inställningar. | inte gjord | Finns inte. | ej planerad |
| AI-457 | People Data Labs: berika en eller flera personer och företag. | inte gjord | Finns inte; berikningen själv avstår vi från (se AI-315). | ej planerad |
| AI-458 | Slack: verktyg, användarkopplingar och händelser. | inte gjord | Finns inte. | ej planerad |
| AI-459 | Meet och Exa: utlösare och webbsökningsverktyget. | inte gjord | Finns inte. | ej planerad |
| AI-470 | En app deklarerar färdigheter och agenter. | inte gjord | Ingen appplattform. | ej planerad |
| AI-471 | En app deklarerar en extern MCP-server. | inte gjord | Ingen appplattform. | ej planerad |
| AI-472 | En app kör en agent med konversationer och som en viss medlem. | inte gjord | Finns inte. | ej planerad |
| AI-473 | En app följer en konversation i realtid. | inte gjord | Finns inte. | ej planerad |
| AI-474 | En app anropar fri AI-generering med omfång och strömning. | inte gjord | Finns inte. | ej planerad |
| AI-475 | Appar debiterar krediter för sina operationer. | inte gjord | Inga appar och inga krediter. | ej planerad |
| AI-476 | Appar med fast månadspris på arbetsytans prenumeration. | inte gjord | Inga appar från tredje part. CRM:et är själv ett tillägg med grind (`snajp-support/app/crm/tillgang.py`), men det är Snajps eget, inte en app. | ej planerad |
| AI-480 | Teams-assistent: prata med agenten i Microsoft Teams. | inte gjord | Finns inte. | ej planerad |
| AI-481 | Teams-assistent: förfrågningarna loggas som poster med status. | inte gjord | Finns inte. | ej planerad |
| AI-482 | Teams-assistent: koppla Teams-användare till medlemmar. | inte gjord | Finns inte. | ej planerad |
| AI-483 | Teams-assistent: tidsgränser och statusbubbla medan agenten arbetar. | inte gjord | Finns inte. | ej planerad |
| AI-484 | Teams-assistent: signerad mottagning och säker sändning. | inte gjord | Finns inte. | ej planerad |
| AI-485 | Teams: appvariabler och servervariabler. | inte gjord | Finns inte. | ej planerad |
| AI-486 | Teams: transkript, historikimport och sammanfattning. | inte gjord | Finns inte. | ej planerad |
| AI-487 | Skrivbordsappens standardinställningar. | inte gjord | Ingen skrivbordsapp. | ej planerad |
| AI-488 | Skrivbordsappen avgör när ett möte är aktuellt och öppnar det automatiskt. | inte gjord | Finns inte. | ej planerad |
| AI-489 | Skrivbordsappens anslutning till arbetsytan. | inte gjord | Finns inte. | ej planerad |
| AI-490 | Chatten öppnas från kommandomenyn med "Ask AI", och en sökning utan träff kan skickas som fråga. | inte gjord | Kommandopaletten finns (`components/crm/app/Kommandopalett.tsx`, Ctrl/Cmd+K) men har bara navigering och sökning, ingen AI. | ej planerad |
| AI-491 | Skrivfältets tangenter: Enter skickar, @ omnämner, / föreslår färdigheter. | inte gjord | Finns inte. | ej planerad |
| AI-492 | Assistenten avgör med en bedömningsmodell om den ska svara i en tråd med flera människor. | inte gjord | Finns inte. | ej planerad |
| AI-493 | Upprepning av kalenderhändelser som agenten skapar. | inte gjord | Ingen kalender i CRM:et. | ej planerad |
