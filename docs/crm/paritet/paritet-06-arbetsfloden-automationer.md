# Paritet 06: Arbetsflöden och automationer

I Twenty bygger användaren egna automationer: ett arbetsflöde har en utlösare (posthändelse, manuell start, schema eller webhook) och en graf av steg (poster, mejl, villkor, loopar, fördröjning, kod, HTTP, AI), körs i en kö och visas steg för steg i en diagramredigerare. Till området hör också logikfunktioner (serverlös kod med egna utlösare och HTTP-rutter) och kodtolken för AI.

Antal per läge (räknat i tabellen nedan, 291 rader): verifierad 0, byggd 0, delvis 10, inte gjord 270, avstår 11.

Underlag: `docs/crm/underlag/twenty-06-arbetsfloden-automationer.md`. Läget gäller arbetskatalogen 2026-11-26. Snajp CRM har ingen arbetsflödesmotor, ingen diagramredigerare och inga logikfunktioner, och `docs/crm/PLAN-MIGRERING.md` nämner inte området i någon fas. Det som finns och liknar området är webhooks ut (`snajp-support/app/crm/webhooks.py`), som skickar CRM:ets posthändelser till en extern adress, och automationerna i Leads (`snajp-support/app/leads/automation.py`, `autopilot.py`, `jev.py`), som ligger utanför CRM:et och flyttar in i fas 4. "Ej planerad" i kolumnen Fas betyder att planen inte har någon fas för raden.

## De största luckorna

1. Det går inte att bygga en automation alls: inget arbetsflöde, ingen utlösare, inga steg och ingen version att aktivera eller inaktivera.
2. En posthändelse (bolag skapat, affär ändrad, uppgift raderad) kan inte starta något inne i CRM:et. Den kan bara skickas vidare som webhook till ett externt system som gör arbetet där.
3. Inga schemalagda körningar (var N:e minut, timme eller dag, eller eget cron-uttryck) i CRM:et. Leads har en fast autopilot per vardag, men den går inte att styra från CRM:et.
4. Ingen manuell knapp för att köra ett flöde på en eller flera valda poster, och kommandopaletten (Ctrl/Cmd+K) kan inte starta något.
5. Inga steg som skapar, uppdaterar, söker eller raderar poster automatiskt, och inget villkor, filter eller loop som styr vad som händer.
6. Inga automatiska mejl, mejlutkast eller kalenderhändelser från CRM:et. Leads skapar utkast och uppföljningar av sig själv, men bara i Leads.
7. Ingen körningslogg för automationer: ingen lista över körningar, ingen status per steg, inget stopp och ingen omkörning av en misslyckad körning.
8. Ingen diagramredigerare där flödet ritas, testas steg för steg och visas live under körning.
9. Inga AI-steg i automationer (agent, klassificering). Jev klassar bolag i Leads, men inte som steg som CRM-användaren väljer.
10. Ingen egen kod eller HTTP-anrop som steg, och inga logikfunktioner med egna HTTP-rutter eller inkommande webhook som startar ett flöde.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| AF-001 | Skapa ett namngivet arbetsflöde från en lista, med ett första utkast. | inte gjord | Finns inte: CRM:et har inget arbetsflödesobjekt (inget i `snajp-support/app/crm/`, ingen migration). | ej planerad |
| AF-002 | Ge steg och utlösare egna namn, med standardnamn efter utlösartyp. | inte gjord | Finns inte: inga steg eller utlösare. | ej planerad |
| AF-003 | Versioner av ett arbetsflöde med status utkast, aktiv, inaktiverad och arkiverad. | inte gjord | Finns inte: inga arbetsflödesversioner. | ej planerad |
| AF-004 | Ändra ett aktivt arbetsflöde i ett nytt utkast medan det aktiva fortsätter köra. | inte gjord | Finns inte. | ej planerad |
| AF-005 | Aktivera ett utkast så att det blir aktivt och det förra arkiveras. | inte gjord | Finns inte. | ej planerad |
| AF-006 | Kasta ett utkast och behålla den aktiva versionen. | inte gjord | Finns inte. | ej planerad |
| AF-007 | Inaktivera ett aktivt arbetsflöde så att inga nya körningar startar. | inte gjord | Finns inte. Närmast är att stänga av en webhook ut (`webhooks.py:andra`, fältet `aktiv`), men det stoppar bara leveransen till en extern adress. | ej planerad |
| AF-008 | Se versionshistoriken med tid och status för varje version. | inte gjord | Finns inte. Postens historik (`components/crm/app/Historik.tsx`) gäller bolag och personer, inte arbetsflöden. | ej planerad |
| AF-009 | Göra en äldre version till nytt utkast ("Use as draft"). | inte gjord | Finns inte. | ej planerad |
| AF-010 | Lagra arbetsflöden och versioner som metadata, högst en aktiv version per flöde, status härledd ur versionerna. | inte gjord | Finns inte: ingen tabell för arbetsflöden i `db/migrations/*_16*_crm_*.sql`. | ej planerad |
| AF-011 | Regler för aktivering: utlösare och steg krävs, schemat kontrolleras, lås mot samtidiga ändringar. | inte gjord | Finns inte. | ej planerad |
| AF-012 | Regler för inaktivering: bara en aktiv version, utlösaren kopplas bort. | inte gjord | Finns inte. | ej planerad |
| AF-013 | Bara utkast kan kastas, och ett flödes enda version kan inte raderas. | inte gjord | Finns inte. | ej planerad |
| AF-014 | Duplicera ett arbetsflöde med en kopia av vald version. | inte gjord | Finns inte. | ej planerad |
| AF-015 | Radera ett eller flera arbetsflöden med deras versioner. | inte gjord | Finns inte. | ej planerad |
| AF-016 | Privata arbetsflöden som bara skaparen ser, och överlåtelse när en medlem tas bort. | inte gjord | Finns inte. | ej planerad |
| AF-017 | Systemarbetsflöden och arbetsflöden som ägs av en app och är skrivskyddade. | inte gjord | Finns inte: CRM:et har varken arbetsflöden eller appar från tredje part. | ej planerad |
| AF-018 | Lista och filtrera arbetsflöden på namn, status och datum, med sidindelning och sortering. | inte gjord | Finns inte. | ej planerad |
| AF-019 | Körningsinsikter för 14 dagar: antal, misslyckade, medeltid och senaste fel. | inte gjord | Finns inte. | ej planerad |
| AF-020 | Versionerna numreras v1, v2, v3 efter ålder, äldst först. | inte gjord | Finns inte. | ej planerad |
| AF-021 | Samtidig redigering av ett utkast skyddas med lås och vägrar sparanden som gör flödet trasigt. | inte gjord | Finns inte. | ej planerad |
| AF-022 | Ett arbetsflöde kan ha flera statusar samtidigt (utkast och aktiv). | inte gjord | Finns inte. | ej planerad |
| AF-023 | När ett arbetsflöde raderas raderas dess körningar permanent. | inte gjord | Finns inte. | ej planerad |
| AF-024 | Arbetsflöden som levereras av installerade appar, och export och publicering av egna flöden som kod. | inte gjord | Finns inte: inga appar från tredje part i CRM:et. | ej planerad |
| AF-025 | Hämta upp till 500 arbetsflöden med aktuell version i ett anrop. | inte gjord | Finns inte. | ej planerad |
| AF-026 | Redigeraren sparar ändringar per nod i kö och skapar utkast när man redigerar en aktiv version. | inte gjord | Finns inte. | ej planerad |
| AF-101 | Varje version har exakt en utlösare av fyra typer (posthändelse, manuell, schema, webhook). | inte gjord | Finns inte. | ej planerad |
| AF-102 | Utlösare när en post skapas. | delvis | Händelsen finns: varje skrivning loggas (`app/crm/handelser.py:logga`) och går ut som `company.created`, `person.created`, `deal.created` med flera till kundens webhooks (`app/crm/webhooks.py:HANDELSETYPER`, `koa`; test `test_webhooken_far_handelsen_signerad` i `snajp-support/tests/crm/test_handelser_webhooks.py`). Saknas: att händelsen startar ett arbetsflöde inne i CRM:et. | ej planerad |
| AF-103 | Utlösare när en post uppdateras, valfritt bara för vissa fält. | delvis | `*.updated` går ut som webhook och händelsen bär vilka fält som ändrades (`handelser.Handelse.falt`). Saknas: arbetsflöde som startar, och val av bevakade fält. | ej planerad |
| AF-104 | Utlösare när en post skapas eller uppdateras (upsert). | delvis | En webhook kan prenumerera på både `*.created` och `*.updated` (`webhooks.py:_vill_ha`). Saknas: en sammanslagen händelse och ett flöde som startar. | ej planerad |
| AF-105 | Utlösare när en post raderas, med postens data före raderingen. | delvis | `*.deleted` och `*.purged` går ut som webhook (`webhooks.py:HANDELSETYPER`). Saknas: arbetsflöde som startar, och postens värden före raderingen (loggen bär aldrig värden). | ej planerad |
| AF-106 | Villkorsfilter på posthändelseutlösaren så att ingen körning skapas när posten inte matchar. | inte gjord | Finns inte. Webhooks filtrerar bara på händelsetyp. | ej planerad |
| AF-107 | Den utlösande postens fält före och efter som variabler. | inte gjord | Finns inte: inga variabler. Webhookens kropp bär posten efter skrivningen (`handelser.Handelse.post`), men den når bara en extern mottagare. | ej planerad |
| AF-108 | Posthändelser även för systemobjekt som uppgifter, anteckningar och mejl. | delvis | Webhookhändelser finns för `deal`, `task`, `note`, `activity` och `attachment` utöver bolag och person (`webhooks.py:HANDELSETYPER`, test `test_varje_objekts_skrivning_syns_i_flodet_och_webhooken_bar_ingen_fil` i `test_objekt_ovriga.py`). Saknas: flöde som startar, och händelser för mejl och kalender. | ej planerad |
| AF-109 | Manuell utlösare som startas var som helst från kommandomenyn (Ctrl/Cmd+K). | inte gjord | Kommandopaletten finns (`components/crm/app/Kommandopalett.tsx`) men kan bara navigera och söka; den startar inga flöden. | ej planerad |
| AF-110 | Manuell utlösare på en eller flera valda poster, en körning per post. | inte gjord | Finns inte. Radmarkeringens åtgärdsrad i `BolagVy.tsx` och `PersonerVy.tsx` har inga flöden att köra. | ej planerad |
| AF-111 | Manuell utlösare på ett urval, en körning med hela listan. | inte gjord | Finns inte. | ej planerad |
| AF-112 | Ikon och fäst knapp i toppfältet för ett manuellt flöde. | inte gjord | Finns inte. | ej planerad |
| AF-113 | Uppgift om vilken medlem som startade ett manuellt flöde. | inte gjord | Finns inte. | ej planerad |
| AF-114 | Schemalagd utlösare var N:e minut. | inte gjord | Finns inte i CRM:et. | ej planerad |
| AF-115 | Schemalagd utlösare var N:e timme på en viss minut. | inte gjord | Finns inte i CRM:et. | ej planerad |
| AF-116 | Schemalagd utlösare var N:e dag på en viss tid. | inte gjord | Finns inte i CRM:et. Leads har en fast autopilot som startar en Iris-körning per vardag (`snajp-support/app/leads/autopilot.py`), men den är inte ett valfritt schema och nås inte från CRM:et. | 4 |
| AF-117 | Schemalagd utlösare med eget cron-uttryck, i UTC. | inte gjord | Finns inte. | ej planerad |
| AF-118 | Webhook-utlösare: en unik adress som ett externt system anropar med GET för att starta flödet. | inte gjord | Finns inte. CRM:et tar emot data genom synk-API:t med API-nyckel (`app/api/crm_v1.py`), men inget anrop startar ett flöde. | ej planerad |
| AF-120 | Kontroll av schemat vid aktivering med begripliga fel. | inte gjord | Finns inte. | ej planerad |
| AF-121 | Aktiva scheman i en cache som ett bakgrundsjobb läser för att starta körningar. | inte gjord | Finns inte. | ej planerad |
| AF-122 | Posthändelser i batch filtreras på behörighet, bevakade fält och villkor innan körning köas. | inte gjord | Finns inte. Webhookkön (`webhooks.py:koa`) filtrerar bara på händelsetyp. | ej planerad |
| AF-123 | Relaterade poster följer med i posthändelsen. | inte gjord | Finns inte: inga flöden, och händelsen berikas inte med relaterade poster. | ej planerad |
| AF-124 | Jokertecken i händelsenamn (`objekt.*`, `*.åtgärd`, `*.*`). | delvis | Webhooks tar `*` för alla händelser (`webhooks.py:_vill_ha`). Saknas: jokertecken per objekt eller per åtgärd, och lyssnare som inte är webhooks. | ej planerad |
| AF-125 | Webhookadressen tar GET och POST, kroppen blir utlösarens data och svaret ger körningens id. | inte gjord | Finns inte. | ej planerad |
| AF-126 | Kommandomenyn får en post för varje aktivt manuellt arbetsflöde. | inte gjord | Finns inte: kommandopaletten har inga flöden. | ej planerad |
| AF-119 | Webhook-utlösare med POST och ett exempel på förväntad kropp som ger variabler. | inte gjord | Finns inte. | ej planerad |
| AF-127 | Webhookadressen tar både GET och POST oavsett vald metod, och frågesträngen förs inte vidare. | inte gjord | Finns inte. | ej planerad |
| AF-128 | Schemat kollas varje minut och varje tidpunkt låses så att den bara startas en gång. | inte gjord | Finns inte i CRM:et. | ej planerad |
| AF-129 | En schemalagd körning startar utan data. | inte gjord | Finns inte. | ej planerad |
| AF-201 | Ett steg kan försöka igen 0 till 3 gånger efter 1, 5 och 15 sekunder. | inte gjord | Finns inte: inga steg. Webhooks ut har egna omförsök (`webhooks.py:VANTETIDER`, sju försök), men det gäller bara leveransen. | ej planerad |
| AF-202 | Ett steg kan låta körningen fortsätta trots att steget misslyckas. | inte gjord | Finns inte. | ej planerad |
| AF-203 | Steg som skapar en post med fasta värden eller variabler. | inte gjord | Finns inte. | ej planerad |
| AF-204 | Steg som uppdaterar valda fält på en vald post. | inte gjord | Finns inte. | ej planerad |
| AF-205 | Steg som raderar en post. | inte gjord | Finns inte. | ej planerad |
| AF-206 | Steg som söker poster med filter, sortering, gräns och förskjutning (högst 200). | inte gjord | Finns inte som steg. Sökning finns i API:t (`app/api/crm_v1.py`), men inget flöde använder den. | ej planerad |
| AF-207 | Steg som skapar eller uppdaterar en post efter ett unikt fält (e-post, domän). | inte gjord | Finns inte som steg. Synken matchar på organisationsnummer och e-post (`app/crm/synk.py`), men det är import, inte ett flödessteg. | ej planerad |
| AF-208 | Steg som väljer en post ur en lista: slump, turordning eller jämn fördelning. | inte gjord | Finns inte. | ej planerad |
| AF-209 | Loop som kör ett antal steg för varje element i en lista. | inte gjord | Finns inte. | ej planerad |
| AF-210 | Filtersteg som stoppar grenen när villkoret inte är uppfyllt. | inte gjord | Finns inte. | ej planerad |
| AF-211 | Villkorssteg med grenarna Om, Annars om och Annars. | inte gjord | Finns inte. | ej planerad |
| AF-212 | Fördröjning under en viss tid, högst ett år. | inte gjord | Finns inte i CRM:et. Leads väntar ett inställt antal dagar före första uppföljningen (`snajp-support/app/leads/automation.py`, `uppfoljning_dagar`), men det är en fast regel i Leads, inte ett steg. | 4 |
| AF-213 | Fördröjning till en viss tidpunkt, fast eller från ett datumfält. | inte gjord | Finns inte. | ej planerad |
| AF-214 | Vänta tills en viss posthändelse inträffar, med valfri tidsgräns. | inte gjord | Finns inte. | ej planerad |
| AF-215 | Steg som skickar mejl från ett anslutet konto, med kopia, bilagor och svar i tråd. | inte gjord | Finns inte i CRM:et. Ett sådant steg måste byggas inom CLAUDE.md regel 17 (uppföljningsmejl är alltid utkast som en människa godkänner) och utskickets enda sändväg (`snajp-support/app/leads/scheduler.py`, INV-SEC-004). | ej planerad |
| AF-216 | Steg som skapar ett mejlutkast för granskning. | inte gjord | Finns inte i CRM:et. Leads skapar utkast automatiskt (`snajp-support/app/leads/automation.py`, `utkast_auto`), men bara i Leads. | 4 |
| AF-217 | Steg som skapar en kalenderhändelse med deltagare och möteslänk. | inte gjord | Finns inte: ingen kalendersynk i CRM:et. | ej planerad |
| AF-218 | Formulärsteg som pausar körningen tills en människa svarar. | inte gjord | Finns inte. | ej planerad |
| AF-219 | Kodsteg med egen TypeScript eller JavaScript som körs isolerat. | inte gjord | Finns inte. | ej planerad |
| AF-220 | En återanvändbar logikfunktion från en app som eget steg. | inte gjord | Finns inte. | ej planerad |
| AF-221 | HTTP-anrop som steg, med metod, rubriker och kropp, högst 30 sekunder och 10 MB. | inte gjord | Finns inte som steg. Webhooks ut gör ett fast POST-anrop per händelse (`webhooks.py:_skicka`), men användaren kan inte forma anropet. | ej planerad |
| AF-222 | AI-agent som steg, med instruktioner, modell, svarsformat och mänsklig inmatning. | inte gjord | Finns inte i CRM:et. | ej planerad |
| AF-223 | Konversationens omfång för AI-steg: per körning, per steg eller delad med nyckel. | inte gjord | Finns inte. | ej planerad |
| AF-224 | Klassificeringssteg som ställer frågor (ja/nej, val, skala) om indata. | inte gjord | Finns inte i CRM:et. Jev klassar bolag mot kundens kriterier i Leads (`snajp-support/app/leads/jev.py`), men inte som steg. | 4 |
| AF-225 | Steg som skickar ett meddelande till en medlems AI-inkorg, valfritt med godkännande. | inte gjord | Finns inte. | ej planerad |
| AF-226 | Steg som anropar ett verktyg på en ansluten MCP-server. | inte gjord | Finns inte: CRM:et har ingen MCP. | ej planerad |
| AF-227 | Tomt steg som platshållare. | inte gjord | Finns inte. | ej planerad |
| AF-228 | Parallella grenar när ett steg har flera efterföljare. | inte gjord | Finns inte. | ej planerad |
| AF-229 | Sammanslagning av grenar som väntar tills alla inkommande grenar är klara. | inte gjord | Finns inte. | ej planerad |
| AF-231 | Standardvärden och standardnamn när ett nytt steg läggs till. | inte gjord | Finns inte. | ej planerad |
| AF-232 | Söksteget ger första träffen, alla träffar och totalt antal, med tydliga fel. | inte gjord | Finns inte. | ej planerad |
| AF-233 | Felmeddelanden och fältstädning för poststegen. | inte gjord | Finns inte. | ej planerad |
| AF-234 | Postvalet sorterar kandidaterna och minns turordningen mellan körningar. | inte gjord | Finns inte. | ej planerad |
| AF-235 | Filtersteget ger sant eller falskt och avslutar grenen vid falskt. | inte gjord | Finns inte. | ej planerad |
| AF-236 | Villkorssteget anger vilken gren som valdes. | inte gjord | Finns inte. | ej planerad |
| AF-237 | Loopen tolkar text som JSON, ger index och element och stannar vid 10 000 varv. | inte gjord | Finns inte. | ej planerad |
| AF-238 | Fördröjningens fel (saknad tid, tid i det förflutna, över ett år). | inte gjord | Finns inte. | ej planerad |
| AF-239 | Väntan på händelse ger postens fält och om tidsgränsen löpte ut. | inte gjord | Finns inte. | ej planerad |
| AF-240 | Mejlstegets avsändare, fel och utdata (meddelande-id och tråd). | inte gjord | Finns inte. | ej planerad |
| AF-241 | HTTP-steget skyddas mot interna adresser, delar takt med kod och kan testas. | inte gjord | Finns inte som steg. | ej planerad |
| AF-242 | Kodsteget ger kodens resultat eller fel och sparar en logg på högst 500 rader. | inte gjord | Finns inte. | ej planerad |
| AF-243 | Logikfunktionssteget fäller när funktionen saknas eller inte är exponerad. | inte gjord | Finns inte. | ej planerad |
| AF-244 | AI-agentens steg körs asynkront och väntar på agentens svar. | inte gjord | Finns inte. | ej planerad |
| AF-245 | Inkorgssteget väntar på mottagarens godkännande, ändring eller avvisning. | inte gjord | Finns inte. | ej planerad |
| AF-246 | MCP-steget ger verktygets resultat eller ett stegfel. | inte gjord | Finns inte. | ej planerad |
| AF-247 | Mejl- och kalendersteg kräver verktygsbehörighet när en app kör flödet. | inte gjord | Finns inte: inga appar och inga sådana steg. | ej planerad |
| AF-230 | Vissa objekt (arbetsflöden, medlemmar, synkade mejl) får inte ändras av automationer. | inte gjord | Finns inte: det finns inga automationer att spärra. | ej planerad |
| AF-248 | Syskonsteg körs samtidigt och långa flöden delas upp i nya köjobb efter 20 steg. | inte gjord | Finns inte. | ej planerad |
| AF-249 | Fel i ett loopvarv kan hoppas över så att loopen fortsätter. | inte gjord | Finns inte. | ej planerad |
| AF-250 | Kontroller före varje steg (flagga, behörighet, kvot) och regler för stegets status. | inte gjord | Finns inte. | ej planerad |
| AF-251 | HTTP-steget under AWS Lambda-drivrutinen (4 MB, 35 sekunder). | avstår | Gäller bara egen drift av Twenty: val av körmiljö för logikfunktioner. | |
| AF-252 | Filter och villkor tar Twentys filteroperander och äldre stavningar, med OCH och ELLER. | inte gjord | Finns inte. | ej planerad |
| AF-253 | Mejl som svar i en befintlig tråd via Message-ID. | inte gjord | Finns inte i CRM:et. | ej planerad |
| AF-301 | Variabler som hämtar utdata från utlösaren eller ett tidigare steg (`{{steg.fält}}`). | inte gjord | Finns inte. | ej planerad |
| AF-302 | Variabelväljare i varje fält som visar tidigare stegs utdata. | inte gjord | Finns inte. | ej planerad |
| AF-303 | Loopens aktuella element och index som variabler. | inte gjord | Finns inte. | ej planerad |
| AF-304 | Sökningens lista, antal och första post som variabler. | inte gjord | Finns inte. | ej planerad |
| AF-305 | Servern räknar fram vad varje steg ger för utdata, med exempelvärden. | inte gjord | Finns inte. | ej planerad |
| AF-306 | Loopens element får sina fält ur källans schema. | inte gjord | Finns inte. | ej planerad |
| AF-307 | En variabel som inte går att lösa blir tom, och i sökfilter ett tydligt fel. | inte gjord | Finns inte. | ej planerad |
| AF-401 | Strukturkontroll av en version: utlösare, steg, nåbarhet, cykler, variabler. | inte gjord | Finns inte. | ej planerad |
| AF-402 | Felkoder som alltid gör flödet trasigt och stoppar även sparande av utkast. | inte gjord | Finns inte. | ej planerad |
| AF-403 | Felkoder som tillåts i utkast men stoppar aktivering. | inte gjord | Finns inte. | ej planerad |
| AF-404 | Övriga valideringsfynd som bara visas, med förslag på närliggande sökvägar. | inte gjord | Finns inte. | ej planerad |
| AF-408 | Serverns egna kontroller: okända objekt, rich text, filtervärden, lastbalansering, AI. | inte gjord | Finns inte. | ej planerad |
| AF-409 | Två kontrollpunkter: varje sparande och varje aktivering. | inte gjord | Finns inte. | ej planerad |
| AF-405 | En variabel får bara peka på ett steg som garanterat körs före. | inte gjord | Finns inte. | ej planerad |
| AF-406 | Varje gren i en loop måste peka tillbaka till loopen. | inte gjord | Finns inte. | ej planerad |
| AF-407 | Mejlstegets kropp måste vara ett mejldokument, inte rå HTML eller text. | inte gjord | Finns inte. | ej planerad |
| AF-501 | Varje utlösning skapar en körning med tider, status, skapare, tillstånd och loggar. | inte gjord | Finns inte. Synkkörningar har förlopp och fel (`app/crm/synk.py`, `components/crm/app/SynkVy.tsx`), men de är import, inte arbetsflöden. | ej planerad |
| AF-502 | Körningens status: i kö, kör, klar, misslyckad, stoppas, stoppad. | inte gjord | Finns inte. | ej planerad |
| AF-503 | Status per steg, med resultat, fel och försöksnummer. | inte gjord | Finns inte. | ej planerad |
| AF-504 | Ett steg körs när alla dess föräldrar är klara, och icke valda grenar hoppas över. | inte gjord | Finns inte. | ej planerad |
| AF-505 | Körningen misslyckas när ett steg misslyckas, annars blir den klar. | inte gjord | Finns inte. | ej planerad |
| AF-506 | Automatiska omförsök per steg, men aldrig för användarfel. | inte gjord | Finns inte. | ej planerad |
| AF-507 | Stoppa en körning som står i kö eller kör. | inte gjord | Finns inte. | ej planerad |
| AF-508 | Köra om en misslyckad körning från de steg som föll. | inte gjord | Finns inte. Närmast är omskick av en misslyckad webhookleverans (`webhooks.py:skicka_om`), som inte är en körning. | ej planerad |
| AF-509 | Svara på ett formulär i en körning som väntar. | inte gjord | Finns inte. | ej planerad |
| AF-510 | Ändra förifyllda värden i ett väntande formulär. | inte gjord | Finns inte. | ej planerad |
| AF-511 | Körningar kan inte skapas eller raderas via post-API:t, bara byta namn. | inte gjord | Finns inte. | ej planerad |
| AF-512 | Visa körningar per arbetsflöde och i en egen vy, filtrerbara, med detalj per steg. | inte gjord | Finns inte. | ej planerad |
| AF-513 | Logg per steg med nivåer och typberoende detaljer (HTTP, mejl, kod, AI). | inte gjord | Finns inte. | ej planerad |
| AF-514 | Städjobb som köar om tappade körningar och stänger fastnade stopp. | inte gjord | Finns inte. | ej planerad |
| AF-515 | Rensning av körningar äldre än 14 dagar och fler än 1 000 per arbetsflöde. | inte gjord | Finns inte. Webhookernas leveranslogg gallras efter 30 dagar (`webhooks.py:_gallra`), men det är inte körningar. | ej planerad |
| AF-516 | En körning som kön vägrar blir en misslyckad körning med begripligt fel. | inte gjord | Finns inte. | ej planerad |
| AF-517 | Körningen skapas även när prenumerationen är inaktiv, och kvoten avgör per steg. | inte gjord | Finns inte. | ej planerad |
| AF-518 | Regler för körjobbet: bara köade körningar startas, avslutade kan inte ändras. | inte gjord | Finns inte. | ej planerad |
| AF-519 | En väntan registreras innan steget visas som väntande, så att ingen händelse tappas. | inte gjord | Finns inte. | ej planerad |
| AF-520 | Meddelanden från en körning anger arbetsflödet som avsändare. | inte gjord | Finns inte. | ej planerad |
| AF-521 | Körningar numreras "#n - namn" och läggs först i listan. | inte gjord | Finns inte. | ej planerad |
| AF-601 | Mjuk takt på 100 körningar per minut, överskott väntar i kön. | inte gjord | Finns inte. API:ts synk har en egen takt på 600 per minut, men det gäller anrop, inte körningar. | ej planerad |
| AF-602 | Hård gräns på 5 000 körningar per timme och arbetsyta. | inte gjord | Finns inte. | ej planerad |
| AF-603 | Krediter per körd nod och kontroll av kvoten före varje steg. | avstår | Ersätts av något Snajp redan har: kunden betalar för CRM:et genom tillägget, som är grinden (`snajp-support/app/crm/tillgang.py`, migration 161), inte per körd nod. | |
| AF-604 | Krediter per plan och månad i Twentys moln, och köp av extra paket. | avstår | Ersätts av något Snajp redan har: Snajps egen prissättning med tillägget som grind (`snajp-support/app/crm/tillgang.py`). Twentys planer gäller bara Twentys moln. | |
| AF-605 | Söksteget ger högst 200 poster. | inte gjord | Finns inte: inget söksteg. | ej planerad |
| AF-606 | Fördröjning högst ett år, negativa eller oläsbara delar fäller steget. | inte gjord | Finns inte. | ej planerad |
| AF-607 | HTTP-steget högst 30 sekunder och 10 MB. | inte gjord | Finns inte. | ej planerad |
| AF-608 | Kodsteget högst 15 minuter och 256 000 tecken. | inte gjord | Finns inte. | ej planerad |
| AF-609 | Logikfunktioner högst 1 000 anrop per minut. | inte gjord | Finns inte. | ej planerad |
| AF-611 | Loopen högst 10 000 varv. | inte gjord | Finns inte. | ej planerad |
| AF-612 | Manuell utlösare på urval tar högst 200 poster. | inte gjord | Finns inte. | ej planerad |
| AF-613 | Mejlbilagor högst 25 MB totalt. | inte gjord | Finns inte. | ej planerad |
| AF-614 | Tak för loggstorlek per steg, med markering av det som kortats. | inte gjord | Finns inte. | ej planerad |
| AF-610 | Massimport utlöser posthändelser för varje post. | inte gjord | Finns inte som flödesutlösare. Synken loggar varje skriven post som händelse som går ut till webhooks (test `test_synken_loggar_per_post_och_en_tomd_post_lamnar_bara_sitt_id` i `test_handelser_webhooks.py`), men inga flöden startar. | ej planerad |
| AF-615 | Resursgränser för logikfunktioner (tidsgräns, minne och lagring under Lambda). | avstår | Gäller bara egen drift av Twenty: körmiljöns resurser under Lambda-drivrutinen. | |
| AF-616 | Gränser för bakgrundsjobb som logikfunktioner köar. | inte gjord | Finns inte. | ej planerad |
| AF-617 | Gränser för kodtolkens sessioner (tid, vilotid, utdata, filer). | inte gjord | Finns inte. | ej planerad |
| AF-618 | AI-verktygens listgränser för arbetsflöden och körningar. | inte gjord | Finns inte. | ej planerad |
| AF-619 | Arbetsflödeslistans gränser (50 regler, 2 000 tecken, 200 per sida). | inte gjord | Finns inte. | ej planerad |
| AF-701 | Flödet ritas som ett diagram, redigerbart för utkast och skrivskyddat för aktiva versioner och körningar. | inte gjord | Finns inte: ingen diagramredigerare i `components/crm/app/`. | ej planerad |
| AF-702 | Välja utlösartyp i sidopanelen. | inte gjord | Finns inte. | ej planerad |
| AF-703 | Formulär för posthändelse: objekt och fält att lyssna på. | inte gjord | Finns inte. Webhookformuläret (`components/crm/app/Webhooks.tsx`) väljer händelser för en extern adress, inte för ett flöde. | ej planerad |
| AF-704 | Formulär för schema med intervall eller cron-uttryck och de kommande körtiderna. | inte gjord | Finns inte. | ej planerad |
| AF-705 | Formulär för webhook-utlösare med adress att kopiera, metod och förväntad kropp. | inte gjord | Finns inte. | ej planerad |
| AF-706 | Formulär för manuell utlösare: tillgänglighet, objekt, ikon och fästning. | inte gjord | Finns inte. | ej planerad |
| AF-707 | Lägga till ett steg med plusknapp, ur en väljare grupperad efter typ. | inte gjord | Finns inte. | ej planerad |
| AF-708 | Högerklick på duken: lägg till nod och städa layouten. | inte gjord | Finns inte. | ej planerad |
| AF-709 | Koppla, koppla bort och dra om pilar mellan steg. | inte gjord | Finns inte. | ej planerad |
| AF-710 | Flytta noder fritt och spara positionerna. | inte gjord | Finns inte. | ej planerad |
| AF-711 | Nodmeny: duplicera, byt typ och ta bort steg. | inte gjord | Finns inte. | ej planerad |
| AF-712 | Redigera ett steg i sidopanelen med löpande sparande. | inte gjord | Finns inte. | ej planerad |
| AF-713 | Nodinställningar för omförsök och fortsätt vid fel. | inte gjord | Finns inte. | ej planerad |
| AF-714 | Testa ett enskilt kod-, HTTP- eller MCP-steg och spara svaret som förväntad utdata. | inte gjord | Finns inte. Webhooks har ett testanrop (`webhooks.py:prova`, `ping`), men det testar en adress, inte ett steg. | ej planerad |
| AF-715 | Testa hela flödet med testindata, även ett utkast. | inte gjord | Finns inte. | ej planerad |
| AF-716 | Knappar för att aktivera, inaktivera, kasta, använda som utkast, duplicera och se körningar och versioner. | inte gjord | Finns inte. | ej planerad |
| AF-717 | Visa en körning i diagrammet med status per nod, live, och knappar Stoppa och Kör om. | inte gjord | Finns inte. | ej planerad |
| AF-718 | Fylla i ett formulär under körning i sidopanelen. | inte gjord | Finns inte. | ej planerad |
| AF-719 | Variabelväljaren i redigeraren med sökning och chips. | inte gjord | Finns inte. | ej planerad |
| AF-720 | Egna redigerare per stegtyp (sök, upsert, mejl, kalender, fördröjning, kod, AI, klassificering). | inte gjord | Finns inte. | ej planerad |
| AF-721 | Uppmaning att godkänna åtkomst när ett anslutet konto saknar rätt. | inte gjord | Finns inte: inga anslutna mejl- eller kalenderkonton i CRM:et. | ej planerad |
| AF-723 | Stegloggens etikett i körningar, med senaste loopvarvet och tappade data. | inte gjord | Finns inte. | ej planerad |
| AF-722 | AI-chatten har 19 verktyg för att bygga, köra och läsa arbetsflöden. | inte gjord | Finns inte: inga AI-agenter i CRM:et. | ej planerad |
| AF-724 | Automatisk layout av alla noder ("städa flödet"). | inte gjord | Finns inte. | ej planerad |
| AF-725 | Schemats tider i UTC med kommande körtider i användarens tidszon. | inte gjord | Finns inte. | ej planerad |
| AF-726 | Stegväljaren med fem grupper och 20 inbyggda steg. | inte gjord | Finns inte. | ej planerad |
| AF-727 | Utfallsrutan vid test, med "bearbetar" och storleksändring. | inte gjord | Finns inte. | ej planerad |
| AF-728 | En testkörning syns direkt i listan och följs live. | inte gjord | Finns inte. | ej planerad |
| AF-729 | Körningsvyns flikar Indata och Utdata spärras efter stegets status. | inte gjord | Finns inte. | ej planerad |
| AF-730 | En vägrad ändring rullas tillbaka i diagrammet med en notis. | inte gjord | Finns inte. | ej planerad |
| AF-731 | AI-verktygens regler för att bygga hela flöden och köra dem. | inte gjord | Finns inte. | ej planerad |
| AF-732 | Kortkommandon: Ctrl/Cmd+Enter testar steget, Escape lämnar helskärm, Ctrl/Cmd+K startar manuella flöden. | delvis | Ctrl/Cmd+K öppnar kommandopaletten (`components/crm/app/Kommandopalett.tsx`) för navigering och sökning. Saknas: flöden i paletten, och kortkommandona i redigeraren. | ej planerad |
| AF-801 | Skapa och redigera en logikfunktion med TypeScript-källa, tidsgräns och körmiljö. | inte gjord | Finns inte. | ej planerad |
| AF-802 | Logikfunktionens inställningssida med flikarna kod, inställningar, utlösare och test. | inte gjord | Finns inte. | ej planerad |
| AF-803 | Utlösare för logikfunktioner: cron, posthändelse, HTTP, AI-verktyg, arbetsflödessteg. | inte gjord | Finns inte. | ej planerad |
| AF-804 | Databasutlösare för logikfunktion med bevakade fält, villkor och batchläge. | inte gjord | Finns inte. | ej planerad |
| AF-805 | HTTP-rutt som exponerar en funktion på en egen sökväg och metod, valfritt med inloggning. | inte gjord | Finns inte. | ej planerad |
| AF-806 | Serverrutt för signerade webhooks från tjänster som Stripe och GitHub. | inte gjord | Finns inte: inga appar och inga inkommande webhooks till CRM:et. | ej planerad |
| AF-807 | Cronutlösare som startar logikfunktioner. | inte gjord | Finns inte. | ej planerad |
| AF-808 | Omförsök i bakgrunden per utlösartyp och en felhanterare efter slutligt fel. | inte gjord | Finns inte. | ej planerad |
| AF-809 | Miljövariabler för logikfunktioner, med reserverade namn. | inte gjord | Finns inte. | ej planerad |
| AF-810 | Beroendelager med npm-paket per arbetsyta. | inte gjord | Finns inte. | ej planerad |
| AF-811 | Köra en logikfunktion isolerat med kontroller och debitering per anrop och tid. | inte gjord | Finns inte. | ej planerad |
| AF-812 | Felkoderna för logikfunktioner (19 stycken). | inte gjord | Finns inte. | ej planerad |
| AF-813 | Liveloggar från logikfunktioner. | inte gjord | Finns inte. | ej planerad |
| AF-814 | API för att läsa, skapa, ändra, radera och köra logikfunktioner. | inte gjord | Finns inte. | ej planerad |
| AF-815 | En logikfunktion som verktyg för AI-chatten och MCP. | inte gjord | Finns inte. | ej planerad |
| AF-816 | En logikfunktion som steg i stegväljaren, med in- och utdataschema. | inte gjord | Finns inte. | ej planerad |
| AF-818 | Kodsteget bär sin egen dolda funktion som kopieras vid duplicering. | inte gjord | Finns inte. | ej planerad |
| AF-817 | Kodtolk där AI kör Python för att analysera filer och data. | inte gjord | Finns inte. | ej planerad |
| AF-819 | Körlägena LIVE (bygger från källkod) och PREBUILT (förbyggt paket). | avstår | Gäller bara egen drift av Twenty: hur installationen bygger och förvärmer funktionspaket. | |
| AF-820 | En funktion kan ha sex slags utlösare samtidigt. | inte gjord | Finns inte. | ej planerad |
| AF-821 | En ny funktion får ett startprojekt med exempelkod. | inte gjord | Finns inte. | ej planerad |
| AF-822 | Drivrutiner för logikfunktioner: avstängd, lokal eller AWS Lambda. | avstår | Gäller bara egen drift av Twenty: installationens val av körmiljö. | |
| AF-823 | En köad funktion kan själv begära omförsök, högst tre. | inte gjord | Finns inte. | ej planerad |
| AF-824 | Felhanterare som körs en gång efter att ett jobb slutgiltigt misslyckats. | inte gjord | Finns inte. | ej planerad |
| AF-825 | En funktion kan köa egna bakgrundsjobb och läsa deras status. | inte gjord | Finns inte. | ej planerad |
| AF-826 | Nyckel/värde-lager för logikfunktioner per arbetsyta eller server. | inte gjord | Finns inte. | ej planerad |
| AF-827 | Appar debiterar krediter för egna operationer. | avstår | Ersätts av något Snajp redan har: tillägget som grind (`snajp-support/app/crm/tillgang.py`). Twentys kreditdebitering från appar gäller Twentys molnfakturering. | |
| AF-828 | Kodtolkens sessioner behåller variabler och filer mellan anrop. | inte gjord | Finns inte. | ej planerad |
| AF-829 | Serverruttens äldre adressform med avvecklingsrubrik, och utskickens prioritet. | inte gjord | Finns inte. | ej planerad |
| AF-830 | Logikfunktionens redigerare sparar själv och härleder indataschemat ur koden. | inte gjord | Finns inte. | ej planerad |
| AF-831 | Testa en logikfunktion från inställningarna med JSON-indata. | inte gjord | Finns inte. | ej planerad |
| AF-832 | HTTP-ruttens adress under funktionsdomänen eller serverns adress. | inte gjord | Finns inte. | ej planerad |
| AF-833 | HTTP-ruttens svar, tillåtna rubriker och plattformens felkoder. | inte gjord | Finns inte. | ej planerad |
| AF-834 | Serverruttens resolver som svarar direkt eller skickar vidare till en målfunktion. | inte gjord | Finns inte. | ej planerad |
| AF-835 | Regler för Authorization-rubriken i serverrutter. | inte gjord | Finns inte. | ej planerad |
| AF-836 | Övervakning av serverrutter som inte kan nås. | inte gjord | Finns inte. | ej planerad |
| AF-837 | Databasutlösare i appformen med universella identifierare och regeluttryck. | inte gjord | Finns inte. | ej planerad |
| AF-838 | Körningskontext för logikfunktioner: arbetsyta, startande medlem, försöksnummer. | inte gjord | Finns inte. | ej planerad |
| AF-839 | Vems åtkomst en logikfunktion använder (personens roll snittad med appens). | inte gjord | Finns inte. | ej planerad |
| AF-840 | Ett AI-verktygsanrop ritat med appens egen komponent i chatten. | inte gjord | Finns inte. | ej planerad |
| AF-841 | Hälsokontroll för appar med statusbanderoll. | inte gjord | Finns inte: inga appar. | ej planerad |
| AF-842 | En logikfunktion kan publicera en händelse i en posts tidslinje. | inte gjord | Finns inte. Tidslinjen (`snajp-support/app/crm/tidslinje.py`) komponeras vid läsning ur CRM, leads och support; inget kan skriva egna händelser dit. | ej planerad |
| AF-843 | Köra funktioner och följa loggar från kommandoraden. | inte gjord | Finns inte. | ej planerad |
| AF-901 | Rollbehörigheten Workflows styr vem som ser och ändrar arbetsflöden. | inte gjord | Finns inte: inga arbetsflöden och inga roller per användare i CRM:et. | ej planerad |
| AF-902 | Bara inloggade användare och OAuth-klienter får skriva arbetsflöden via API:t. | inte gjord | Finns inte. | ej planerad |
| AF-903 | Vem som får läsa, köra och ändra logikfunktioner via API:t. | inte gjord | Finns inte. | ej planerad |
| AF-904 | En körning agerar som medlemmen som startade den, annars som arbetsflödets app. | inte gjord | Finns inte. | ej planerad |
| AF-905 | En posthändelse startar bara flöden som får läsa posten. | inte gjord | Finns inte. Webhooks ut läser bara den egna kundens händelser (radskydd, `webhooks.py`, test `test_webhooken_far_handelsen_signerad`), men det är kundisolering, inte behörighet per flöde. | ej planerad |
| AF-906 | Formulärets postval kontrolleras mot den svarandes läsrätt. | inte gjord | Finns inte. | ej planerad |
| AF-907 | AI-steg följer agentens roll eller stegets angivna behörigheter. | inte gjord | Finns inte. | ej planerad |
| AF-908 | Privata arbetsflöden och apparnas arbetsflöden (se AF-016 och AF-017). | inte gjord | Finns inte. | ej planerad |
| AF-909 | Webhook- och ruttutlösare är publika om inte inloggning slagits på. | inte gjord | Finns inte: CRM:et har inga inkommande utlösare. | ej planerad |
| AF-910 | Utgående anrop skyddas mot interna nät och inloggningsrubriker maskeras i loggar. | delvis | Webhooks ut går genom nätvakten (`snajp-support/app/integrationer/natvakt.py`, anropad i `webhooks.py:_kontrollera` och `_skicka`; tester `test_bara_publika_https_adresser_och_kanda_handelser` och `test_adressen_provas_igen_nar_leveransen_gar` i `test_handelser_webhooks.py`). Saknas: HTTP-steg och logikfunktioner som skyddet gäller, och maskering av rubriker i en steglogg. | ej planerad |
| AF-911 | Funktionsflaggor för inkorgs- och MCP-steg. | inte gjord | Finns inte. | ej planerad |
| AF-912 | Skillnad mellan användarfel (ingen felrapport, inget omförsök) och systemfel. | inte gjord | Finns inte för körningar. | ej planerad |
| AF-913 | Kod körs inte alls utan uttrycklig konfiguration av drivrutin. | avstår | Gäller bara egen drift av Twenty: installationens standardläge för kodkörning. | |
| AF-1001 | Uppräkning av de fyra utlösartyperna. | inte gjord | Finns inte. | ej planerad |
| AF-1002 | Uppräkning av posthändelserna (4 för arbetsflöden, 7 för logikfunktioner). | delvis | Webhookhändelserna `created`, `updated`, `deleted`, `restored`, `purged` och `*` (`snajp-support/app/crm/handelser.py:TYP_UT`, `webhooks.py:HANDELSETYPER`) motsvarar created, updated, deleted, restored, destroyed och jokertecknet. Saknas: `upserted`, och att händelserna kan utlösa något inne i CRM:et. | ej planerad |
| AF-1003 | Uppräkning av schematyperna (dagar, timmar, minuter, eget). | inte gjord | Finns inte. | ej planerad |
| AF-1004 | Uppräkning av manuell tillgänglighet (global, en post, urval) och fästning. | inte gjord | Finns inte. | ej planerad |
| AF-1005 | Uppräkning av webhookmetoder (GET, POST) och autentisering. | inte gjord | Finns inte. | ej planerad |
| AF-1006 | Uppräkning av de 23 stegtyperna. | inte gjord | Finns inte. | ej planerad |
| AF-1007 | Uppräkning av versionsstatus (4) och arbetsflödesstatus (3). | inte gjord | Finns inte. | ej planerad |
| AF-1008 | Uppräkning av körningsstatus (6). | inte gjord | Finns inte. | ej planerad |
| AF-1009 | Uppräkning av stegstatus (8). | inte gjord | Finns inte. | ej planerad |
| AF-1010 | Uppräkning av filteroperanderna (16 plus äldre alias) och OCH/ELLER. | inte gjord | Finns inte för steg. | ej planerad |
| AF-1011 | Uppräkning av HTTP-metoder (5) och kroppstyper (5). | inte gjord | Finns inte. | ej planerad |
| AF-1012 | Uppräkning av strategierna för postval (slump, turordning, jämn fördelning). | inte gjord | Finns inte. | ej planerad |
| AF-1013 | Uppräkning av konversationsomfång (per körning, per steg, med nyckel). | inte gjord | Finns inte. | ej planerad |
| AF-1014 | Uppräkning av klassificeringsfrågornas typer (val, skala, ja/nej). | inte gjord | Finns inte. | ej planerad |
| AF-1015 | Uppräkning av formulärets fälttyper (6). | inte gjord | Finns inte. | ej planerad |
| AF-1016 | Uppräkning av fördröjningstyper (till tidpunkt, under en tid). | inte gjord | Finns inte. | ej planerad |
| AF-1017 | Uppräkning av omförsöksval (0 till 3) och väntetider (1, 5, 15 sekunder). | inte gjord | Finns inte för steg. | ej planerad |
| AF-1018 | Uppräkning av AI-svarsformat (text, JSON) och JSON-fälttyper. | inte gjord | Finns inte. | ej planerad |
| AF-1019 | Uppräkning av arbetsflödeslistans filterfält, operander och sortering. | inte gjord | Finns inte. | ej planerad |
| AF-1020 | Uppräkning av logikfunktionernas sex utlösarinställningar. | inte gjord | Finns inte. | ej planerad |
| AF-1021 | Uppräkning av logikfunktionernas 19 felkoder. | inte gjord | Finns inte. | ej planerad |
| AF-1022 | Uppräkning av körmiljöer, körlägen och drivrutiner för funktioner och kodtolk. | avstår | Gäller bara egen drift av Twenty: installationens körmiljö och drivrutiner. | |
| AF-1023 | Uppräkning av de åtta miljövariabler plattformen injicerar. | inte gjord | Finns inte. | ej planerad |
| AF-1024 | Uppräkning av AI-chattens 19 verktyg för arbetsflöden. | inte gjord | Finns inte. | ej planerad |
| AF-1025 | Uppräkning av de 14 objekt som är spärrade för automation. | inte gjord | Finns inte. | ej planerad |
| AF-1026 | Uppräkning av funktionsflaggade steg och appbehörigheter för steg. | inte gjord | Finns inte. | ej planerad |
| AF-1027 | Uppräkning av stegväljarens fem grupper med 20 steg. | inte gjord | Finns inte. | ej planerad |
| AF-1028 | Uppräkning av stegexekveringens sex felkoder. | inte gjord | Finns inte. | ej planerad |
| AF-1029 | Uppräkning av bakgrundsjobbens sju tillstånd. | inte gjord | Finns inte. | ej planerad |
| AF-1030 | Uppräkning av förbrukningskategorierna för krediter (8). | avstår | Ersätts av något Snajp redan har: tillägget som grind (`snajp-support/app/crm/tillgang.py`) i stället för Twentys krediter. | |
| AF-1031 | Uppräkning av de 30 valideringskoderna. | inte gjord | Finns inte. | ej planerad |
| AF-1032 | Uppräkning av de fem svarsrubriker en HTTP-rutt får sätta. | inte gjord | Finns inte. | ej planerad |
| AF-1033 | Uppräkning av kodtolkens hjälpskript för Word, PDF, PowerPoint och Excel. | inte gjord | Finns inte. | ej planerad |
| AF-1034 | Uppräkning av kodtolkens drivrutiner och standardläge. | avstår | Gäller bara egen drift av Twenty: installationens val av sandlåda. | |
| AF-1035 | Uppräkning av serverruttens nio felkoder med HTTP-status. | inte gjord | Finns inte. | ej planerad |
| AF-1036 | Uppräkning av hälsokontrollens sex statusar. | inte gjord | Finns inte. | ej planerad |
| AF-1037 | Uppräkning av testkörningens tre statusar för logikfunktioner. | inte gjord | Finns inte. | ej planerad |
| AF-1038 | Uppräkning av redigerarens tre kortkommandon. | delvis | Ctrl/Cmd+K finns för kommandopaletten (`components/crm/app/Kommandopalett.tsx`). Saknas: Ctrl/Cmd+Enter för att testa ett steg och Escape ur kodens helskärm, eftersom redigeraren inte finns. | ej planerad |
| AF-1039 | Uppräkning av serverruttens metoder (GET, POST, standard POST). | inte gjord | Finns inte. | ej planerad |
