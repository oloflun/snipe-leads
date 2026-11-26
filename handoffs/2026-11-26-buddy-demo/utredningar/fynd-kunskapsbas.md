# kunskapsbas
belagt=True konfidens=medel | granskning: haller=True konfidens=medel

## Sammanfattning
(a) är ingen läcka, ingen cache och ingen hallucination. Backenden seedar avsiktligt den fiktiva e-handeln Nordlys Handels supportartiklar (PostNord, Instabox, retur, paket) i varje testarbetsyta när tenanten skapas (POST /api/keys med slug testkund-*). Livrustnings data är inte inblandad.

(b) beror på att webbplatsskanningen bara har en uppgift: den skriver supportartiklar. Systemprompten nämner bara ångerrätt, returfrakt, leveranstider, garanti och betalsätt. Den har ingen väg för säljfakta till Iris.

(c) hänger inte ihop med (a) eller (b) i koden. Utkastkedjan läser aldrig kunskapsbasen (ingen list_kb eller search_kb i leads-modulerna). Den läser product_marketing, customer_research, retention_playbook, agent_configs.settings (produkter, erbjudanden, profil, icp), SOUL, instruktionslagren och Snajps egen grundprompt och skrivstil. För en ny testarbetsyta är produkter och erbjudanden tomma. Då väljs varken produkt eller erbjudande, och ingen spärr stoppar utkastet. Skrivstilen (agent-core/prompts/leads-skrivstil.md rad 28) har exemplet "Vår Supportagent svarar på de frågorna direkt på din webbplats …", och det första utkastet är nästan ordagrant det. Att utkasten blev rätt efter att kunskapsbasen uppdaterades är alltså en samtidighet: något annat ändrades samma gång (Vad ni säljer, produkter eller erbjudanden).

Namnet "Testarbetsyta https://buddy.se" kommer från lib/actions/onboarding.ts:529. Där får testtenanten webbadressen som namn i stället för företagsnamnet. Namnet går som tenant_name in i Iris-prompten ("åt …") och i signaturen. Koden för de berörda vägarna är densamma på origin/main och origin/development (git diff tom).

## Grundorsak
(a) Belagt i koden och låst av ett test. Kedjan:
1. lib/actions/onboarding.ts:525-529: en testarbetsyta tar vägen "testtenant" och anropar skapaTesttenant(workspace_id, `Testarbetsyta ${webbplats}`).
2. lib/snajp/testtenant.ts:100-108: det blir POST /api/keys med slug testkund-<8>.
3. snajp-support/app/api/keys.py:56-60: när sluggen börjar på "testkund-" körs ensure_tenant_kb(storage, new_tenant["id"]).
4. snajp-support/app/scripts/seed_kb.py:110-126: KB_ARTICLES läggs in som riktiga artiklar i ss_knowledge_base, med embedding NULL.
5. snajp-support/app/kb_articles.py:1, 44 och framåt: det är Nordlys Handels e-handelsbas, till exempel "Leveranstider och fraktalternativ" (PostNord och Instabox, rad 78-83), "Försenat eller försvunnet paket", "Ändra leveransadress", "Ombud eller hemleverans" och "Om Nordlys Handel".
6. tests/api/test_kb_seedning.py:51-60 (test_testarbetsyta_far_kunskapsbas_vid_skapandet) kräver det beteendet. Körd lokalt: 7 passed.
7. Webbplatsskanningen som onboardingen startar (onboarding.ts:596-598, api/kb.py:249-324, _spara_utfall rad 170-184) skriver bara FÖRSLAG i ss_kb_forslag, aldrig artiklar. Det enda som fyllde basen direkt efter onboardingen var alltså seedningen.

Övriga hypoteser avfärdade:
- Annan tenant eller läcka: tenanten är egen per arbetsyta. Reserven till den delade "testkund" tas bara om nyckeln saknas, och då hade namnet varit "Testarbetsyta" och ingen skanning hade körts.
- Cache: ingen KB-cache nycklad utan tenant finns i den vägen.
- Modellen hittar på: utkasten kräver hämtade sidor, och source_url saneras mot kallsidorna.
- URL-normalisering: tenanten fick rätt adress i namnet.

(b) Belagt. snajp-support/app/kb_skanning.py:772-789 (SYSTEMPROMPT) beställer utkast "för en svensk kundtjänstagent" med exemplen ångerrätt, returfrakt, leveranstider, garanti och betalsätt. Kategorierna är supportens (teknisk_support, leverans, betalning, retur_reklamation, konto, ovrigt; CHECK i db/migrations/002_snajp_support.sql). bedom_luckor (rad 961-1053) sätter "malgrupp" till "Kan bara kunden svara på". Ingenting i skanningen skriver produkter, nytta, målgrupp, bevis eller pris till Iris lager (agent_configs.settings.produkter, product_marketing).

(c) Delvis belagt.
- Belagt: leadskedjan läser aldrig KB (grep: list_kb, search_kb och ss_knowledge_base finns inte i app/leads/, agent/leads_research_v2.py, agent/leads_agent.py eller leads/context_pack.py; context_pack.py läser bara product_marketing, customer_research och retention_playbook).
- Belagt: run_outreach_draft_v2 (agent/leads_research_v2.py:1110-1139) kräver bara require_business_context, alltså minst 120 tecken product_marketing (business_context.py). Med tomma produkter (las_produkter, rad 249) ger erbjudanden.produkt_nu None (erbjudanden.py:250), for_trad ger None (rad 644-646) och prompten saknar både produktlista och erbjudandeblock. Ingen spärr stoppar utkastet.
- Belagt: modellen får alltid Snajps egna exempel. leads-skrivstil.md:28 har "Vår Supportagent svarar på de frågorna direkt på din webbplats, dygnet runt …", och rad 18, 24, 51, 150 och 154 talar om Iris, Supportagenten och "hos Snajp står piloten i varje mejl". Grundprompten leads-systemprompt.md:13 tillåter att agenten namnges "om {{FÖRETAGSNAMN}} är Snajp". Med tenant_name "Testarbetsyta https://buddy.se" kan modellen inte avgöra det.
- Belagt: stilkontroll.produktslag (rad 596-604) klassar varje produktnamn som innehåller "support" som Snajps Supportagent, för alla kunder. Det styr ingångsform, frågans moment (erbjudanden._MOMENT) och förebilderna (utkaststruktur.FOREBILDER med "Vår Supportagent finns just nu i en kostnadsfri pilot …").
- Förmodat: varifrån "3 månaders fri support" kom. Varken katalogen, promptfilerna eller koden innehåller frasen. Den kom troligen från researchens eget erbjudandeförslag eller från det Buddy skrev i onboardingens erbjudandefält. Det kräver att körningens agent_runs läses i drift.
- Förmodat: att Buddy fyllt i produkter, erbjudanden eller Vad ni säljer när kunskapsbasen uppdaterades. Det förklarar varför senare utkast blev rätt, men är inte visat ur data.

## Bevis
- snajp-support/app/api/keys.py:43-62 Varje tenant med slug testkund-* seedas med ensure_tenant_kb vid skapandet; kommentaren säger själv att KB_ARTICLES är Nordlys Handels e-handelsartiklar
- snajp-support/app/scripts/seed_kb.py:73-127 ensure_tenant_kb lägger in KB_ARTICLES som riktiga artiklar (embedding NULL), per rubrik och idempotent; anropas även från inbox-mocken
- snajp-support/app/kb_articles.py:1, 78-105, 235, 286-290 Nordlys Handel: PostNord, Instabox, paket, ombud, leveransadress, alltså innehållet som syntes hos Buddy
- snajp-support/tests/api/test_kb_seedning.py:51-60 Testet kräver att en testarbetsyta får kb_seeded > 0 vid skapandet; körd lokalt, 7 passed
- lib/actions/onboarding.ts:525-536 Testvägen skapar tenanten med namnet `Testarbetsyta ${webbplats}`, källan till "Testarbetsyta https://buddy.se"
- lib/actions/onboarding.ts:594-599 Webbplatsskanningen startas efter kopplingen och skriver förslag, inte artiklar
- snajp-support/app/api/kb.py:170-184, 249-324 _spara_utfall skriver bara ss_kb_forslag; artiklar skapas först när kunden lägger till dem
- snajp-support/app/kb_skanning.py:772-789 SYSTEMPROMPT beställer bara supportartiklar för en kundtjänstagent; ingen säljfakta för Iris
- snajp-support/app/agent/leads_research_v2.py:1110-1139 Utkastet kräver bara require_business_context; med tomma produkter blir vald_nu och erbjudande None och utkastet skrivs ändå
- snajp-support/app/leads/context_pack.py:150-162 Leadskedjan läser product_marketing, customer_research och retention_playbook, aldrig ss_knowledge_base
- agent-core/prompts/leads-skrivstil.md:28 Exemplet "Vår Supportagent svarar på de frågorna direkt på din webbplats …", nästan identiskt med Buddys första utkast
- agent-core/prompts/leads-systemprompt.md:13 Agentnamnen är tillåtna "om {{FÖRETAGSNAMN}} är Snajp"; med tenant_name "Testarbetsyta https://buddy.se" går det inte att avgöra
- snajp-support/app/leads/stilkontroll.py:596-604 produktslag klassar varje produktnamn med "support" som Snajps Supportagent oavsett kund, och styr därmed förebilder och moment
- snajp-support/app/leads/utkaststruktur.py:110-118 Förebilderna för support är Snajps Supportagent-mejl med pilot för 20 företag

## Förslag
- 1. Stoppa exempelbasen vid skapandet (löser a). POST /api/keys seedar Nordlys bara när anroparen uttryckligen ber om det: nytt fält exempel_kb, default false. Seedningen i inbox-mocken ('Hämta testmail', X-Snajp-Demo) står kvar, för där hör de fiktiva e-handelsmejlen och artiklarna ihop. En testarbetsyta får då en tom bas tills skanningens förslag läggs till. Skanningen startas redan i onboardingen, så kunskapsbasens befintliga förslagsyta fyller den med kundens egna sidor. Är den tomma basen ett problem för grundningsregeln i demon, kan onboardingen lägga till skanningens förslag med confidence ≥ 0.7 direkt för testarbetsytor, i stället för Nordlys.
- 2. Rätt namn. I onboarding.ts:529 får testtenanten `foretag` som namn i stället för `Testarbetsyta ${webbplats}`. Testmärkningen bärs redan av sluggen (lib/admin/statistik.ts:arTestyta läser slug, inte namn), så ingen adminvy tappar märket.
- 3. Låt kunskapsbasen bära Iris fakta i samma yta. Skanningens enda LLM-anrop ger två sorters artiklar. Supportartiklarna är som i dag. En ny kategori 'salj' (sv 'Erbjudande och säljfakta', en 'Offer and sales facts') får en artikel var för tjänster/produkter (namn + nytta), målgrupp, bevis (referenser, siffror som står på sajten) och pris, med samma regler som i dag: bara uppgifter ur sidtexten och en source_url per artikel. De hamnar i samma förslagslista och samma artikellista i Kunskapsbas.tsx, med kategorin som etikett och filter. Ingen ny panel. Leadskedjan läser dem: context_pack.build_context_pack lägger de tillagda salj-artiklarna som ett eget avsnitt ('Kundens egna fakta ur kunskapsbasen'), och de går in i grundningsgrindens underlag. Har kunden inga produkter ännu föreslår beslutsvägen (api/kb.py besluta_kb_forslag) samma tjänster som rader i Leads › Produkter (agent_configs.settings.produkter), men bara som förslag och bara när listan är tom. Supportagenten får också läsa salj-artiklarna (prisfrågor), så ingen fakta finns på två ställen.
- 4. Spärr mot utkast utan kundens eget erbjudande. Ny funktion business_context.require_eget_erbjudande(storage, tenant_id) körs i run_outreach_draft_v2 direkt efter require_business_context, och vid körstart i api/leads.py så att körningen stannar innan research kostar något. Den kastar MissingBusinessContextError ('Lägg till minst en produkt med vad den gör för kunden under Leads › Produkter, eller lägg till förslagen från webbplatsen i kunskapsbasen') när produkterna är tomma och kunskapsbasen saknar tillagda salj-artiklar. Spärren går före modellen, så inget utkast skrivs med Snajps exempel som enda produktkälla. Beskedet syns där körningen startades, i draft_note, enligt regeln om att följa flödet.
- 5. Kodgrind mot Snajps standardvärden hos andra kunder. stilkontroll får fyndet 'snajp_produkt_hos_kund': en tenant vars slug inte är 'snajp' och vars produkter inte innehåller namnet får aldrig köa ett utkast som nämner Supportagent(en), Iris, Kvittohanterare(n) eller Snajp. Fyndet är ett stopp i köningen (steg 5), inte en omskrivning. Samtidigt grindas produktslag och de Snajp-specifika förebilderna, momenten och ingångsformerna (utkaststruktur.forebilder, erbjudanden._MOMENT, leads_research_v2._ingangsform) på att tenanten är Snajp. En annan kunds produkt med ordet 'support' får då formreglerna, inte Snajps Supportagent-exempel. Skrivstilens exempel ändras inte, för facit är låst (INV-LEADS-UTKAST-002). Snajps egna utkast påverkas inte, eftersom grinden bara gäller andra tenants.
- 6. Ta bort Nordlys-artiklar i befintliga testarbetsytor (testkund-*). Det är radering av data i produktion och kräver Antons ja. Ett skript med torrkörning först kan ta bort exakt KB_ARTICLES-rubrikerna med embedding NULL i tenants med slug testkund-*, aldrig i andra tenants.

## Filer att ändra
- snajp-support/app/api/keys.py
- snajp-support/app/api/schemas.py
- lib/snajp/testtenant.ts
- lib/actions/onboarding.ts
- snajp-support/app/kb_skanning.py
- snajp-support/app/config.py
- db/migrations/<nästa nummer>_kb_kategori_salj.sql
- snajp-support/app/api/kb.py
- snajp-support/app/leads/context_pack.py
- snajp-support/app/leads/business_context.py
- snajp-support/app/agent/leads_research_v2.py
- snajp-support/app/api/leads.py
- snajp-support/app/leads/stilkontroll.py
- snajp-support/app/leads/utkaststruktur.py
- snajp-support/app/leads/erbjudanden.py
- components/settings/Kunskapsbas.tsx
- docs/BESLUT.md

## Tester
- snajp-support/tests/api/test_kb_seedning.py: ersätt test_testarbetsyta_far_kunskapsbas_vid_skapandet med ett test där POST /api/keys med en testkund-slug och utan exempel_kb ger kb_seeded == 0 och en tom /api/kb. Med exempel_kb true seedas fortfarande. test_testmail_seedar_en_testarbetsyta står kvar oförändrat.
- snajp-support/tests/test_kb_skanning_saljfakta.py (nytt): skanna() mot en fixture-sajt för ett tjänstebolag (telefoni och upphandling, ingen frakt) med en LLM-stubbe ger artiklar i kategorin 'salj' med source_url bland de hämtade sidorna. En sida utan pris ger ingen prisartikel. Inga påhittade siffror (obelagda_siffror).
- snajp-support/tests/leads/test_eget_erbjudande_sparr.py (nytt): en tenant utan produkter och utan tillagda salj-artiklar ger MissingBusinessContextError från run_outreach_draft_v2 och ingen rad i granskningskön. Med en produkt eller en salj-artikel passerar den.
- snajp-support/tests/leads/test_stilkontroll_snajp_produkt.py (nytt): ett utkast med 'Vår Supportagent …' hos en tenant med slug testkund-x och produkten 'Upphandling av företagstelefoni' ger fyndet snajp_produkt_hos_kund och köas inte. Samma text hos slug 'snajp' ger inget fynd. produktslag('Telefonisupport') hos en annan kund ger inga Snajp-förebilder.
- snajp-support/tests/leads/test_context_pack_kb.py (nytt): tillagda salj-artiklar står i kontextpaketet och i grundningsgrindens underlag; supportartiklar gör det inte.
- lib/snajp/testtenant.test.ts eller onboarding-test (node --test): testtenanten skapas med företagsnamnet, inte webbadressen.
- Regressionskontroll enligt UTKASTKEDJAN-REFERENS § 7: tests/leads/test_utkastfacit_2026_10_16.py, test_utkastfacit_2026_10_12.py, test_stilkontroll_2026_10_12.py och tests/agent/test_leads_v2_wiring.py ska passera oförändrade.
- tests/invariants/test_inv_copy_001.py: den nya kategorins etikett och spärrens besked finns på både svenska och engelska.

## Risker
- Om Nordlys-seedningen tas bort får en ny testarbetsyta en tom bas tills förslagen läggs till, och supportens grundningsregel (processor.py steg 2) eskalerar då allt i demon. Skälet till seedningen var just det. Antingen läggs högkonfidensförslag till automatiskt för testarbetsytor, eller så visar demon skanningens förslag först.
- Spärren i förslag 4 stoppar körningar för befintliga kunder som har product_marketing men inga produkter. Snajp själv har produkter. Andra kunders läge behöver räknas i drift före release, annars stannar körningar som fungerar i dag.
- Kategorin 'salj' kräver att CHECK-villkoret på ss_knowledge_base.category ändras (additiv, idempotent migration) och att CATEGORIES/KbArtikel-schemat utökas. Triage och support filtrerar på kategori och får inte börja skicka ärenden till 'salj'.
- Grinden mot Snajps agentnamn kan ge falsklarm för en kund som själv säljer något som heter 'Iris' eller 'Supportagent'. Grinden undantar därför namn som finns bland kundens egna produkter.
- Att radera Nordlys-artiklar i befintliga testkund-*-tenants är radering av data i produktion och kräver Antons uttryckliga ja; torrkörning först.
- Webbplatsbedömningen (regel 2026-10-08) berörs inte: salj-artiklarna är kundens egna fakta, inte webbrevisionen av prospekt.

## Öppna beslut
- Ska en testarbetsyta helt utan exempelartiklar, eller ska skanningens förslag med hög konfidens läggas till automatiskt så att demon svarar direkt? Det är Antons val, och det ändrar ett uttryckligt designbeslut i keys.py.
- Ska spärren i förslag 4 gälla alla kunder direkt, eller först efter att befintliga kunder utan produktlista fått sina produkter föreslagna? Det kräver en räkning i drift.
- Ska Nordlys-artiklarna tas bort ur befintliga testarbetsytor i produktion (radering, Antons ja)?
- Källan till '3 månaders fri support' och varför senare utkast blev rätt kan bara avgöras ur drift: agent_runs (leads_research och utkast) för testkontots tenant samt ändringstiderna för agent_configs (leads), produkter och erbjudanden och för context_docs product_marketing. Det är en separat skrivskyddad fråga, och om den ska köras är Antons beslut.

## Prodfråga
-- Skrivskyddad. Kör den inte utan Antons ja. Utgår från att appens tabeller (auth.users, profiles, workspaces) och backendens (ss_*) ligger i samma Railway-databas, som efter Supabase-avvecklingen. Annars delas den vid ss_tenant_id.
with konto as (
  select u.id as user_id, u.email, w.id as workspace_id, w.name as arbetsyta, w.slug, w.ss_tenant_id
  from auth.users u
  join public.profiles p on p.id = u.id
  join public.workspaces w on w.id = p.workspace_id
  where lower(u.email) = 'test@testsson.nu'
)
select k.slug,
       t.name              as tenant_namn,          -- väntat: 'Testarbetsyta https://buddy.se'
       t.created_at        as tenant_skapad,
       a.title,
       a.category,
       a.created_at        as artikel_skapad,
       a.created_at - t.created_at as efter_skapandet, -- väntat: några sekunder för seedade artiklar
       (a.embedding is null)       as utan_vektor,     -- seedningen sätter alltid NULL
       f.id is not null            as fran_skanning,   -- true bara för förslag kunden lade till
       f.source_url,
       a.title in ('Om Nordlys Handel','Leveranstider och fraktalternativ','Försenat eller försvunnet paket',
                   'Ändra leveransadress på en lagd beställning','Ombud eller hemleverans','Så gör du en retur') as nordlys_seed
from konto k
join public.ss_tenants t        on t.id = k.ss_tenant_id
join public.ss_knowledge_base a on a.tenant_id = t.id
left join public.ss_kb_forslag f on f.tenant_id = t.id and f.artikel_id = a.id
order by a.created_at;
-- Hypotesen för (a) bekräftas om k.slug är 'testkund-<8>' (inte den delade 'testkund'), om artiklarna med nordlys_seed = true har efter_skapandet på sekunder, utan_vektor = true och fran_skanning = false, och om Buddy-bitarna från omkörningen har fran_skanning = true och en source_url på buddy.se. Står slugen som 'testkund' utan suffix togs reserven (delad bas), och då gäller en annan förklaring.

## GRANSKARE: invändningar
- (a) håller i sak men är ofullständig. Det finns en andra väg som seedar Nordlys. snajp-support/app/api/inbox.py:94-95 kör ensure_tenant_kb när X-Snajp-Demo är true. Proxyn sätter den ur workspaces.is_demo, och link_test_tenant sätter is_demo = true (db/migrations/040_testkund_egen_tenant.sql:98). ensure_tenant_kb jämför per rubrik (seed_kb.py:110-126), så varje klick på 'Hämta testmail' lägger tillbaka de Nordlys-artiklar som kunden raderat. Att bara stänga av seedningen i keys.py (förslag 1) löser alltså inte hela klassen.
- Utredarens prodfraga antar att slugen är testkund-<8>. lib/snajp/kopplingsvag.ts:4-8 och onboarding.ts:480-484 beskriver ett fall i produktion 2026-11-23 (kund-ad046232): en redan kopplad testarbetsyta tog testvägen och hade kund-slug. Har Buddys arbetsyta en kund-slug men is_demo = true kom Nordlys via inbox-mocken och inte via keys.py. Hypotesen gäller med båda slugmönstren, men frågan måste skilja på dem.
- (c): påståendet att 'erbjudande blir None' stämmer inte om kunden fyllde i erbjudanden i onboardingen. onboarding.ts:552 anropar fyllStandardinstallningar(..., erbjudanden). Det blir standard.ts:345-354 och erbjudandenUrOnboarding (standard.ts:108-118), som skriver egna erbjudanden med villkor som ren sträng. villkor_for (erbjudanden.py:209-210) returnerar en strängvillkor för vilken produkt som helst, även None. valbara och for_trad (erbjudanden.py:512-523, 629-659) väljer därför erbjudandet även när produktlistan är tom. '3 månaders fri support' är med stor sannolikhet Buddys eget onboardingerbjudande, alltså villkorstexten ordagrant. Utredaren lämnade källan öppen, men kedjan går att följa i koden. Förmodat tills agent_configs har lästs.
- (c), den verkliga mekanismen: onboardingen skriver ALDRIG settings.produkter, för någon kund (grep: 'produkter' finns inte i lib/snajp/standard.ts eller lib/actions/onboarding.ts). Erbjudandeblocket säger att 'produkten är den researchen valde', och _PRODUKTMENING_A (erbjudanden.py:87-90) kräver att 'produkten namnges först'. Med tom produktlista, ett erbjudande som innehåller ordet 'support' och skrivstilens exempel 'Vår Supportagent svarar på de frågorna direkt på din webbplats' (leads-skrivstil.md:28) väljer modellen Snajps produktnamn. leads-systemprompt.md:13 förbjuder 'Snajp' och 'Iris' men inte 'Supportagent'. Därför är detta ingen samtidighet med KB-uppdateringen: det som rättade senare utkast måste vara att en produkt lades in i Leads › Produkter, eller att Vad ni säljer ändrades.
- Utredaren anger fel risk för förslag 4. Det är inte bara befintliga kunder utan produktlista som påverkas. Eftersom onboardingen aldrig skriver produkter skulle spärren stoppa varje nyonboardad kund, testkund eller riktig, vid deras första körning.

## GRANSKARE: missat
- Inbox-mockens seedning (api/inbox.py:94-95, grindad på is_demo) är en andra väg till Nordlys-artiklar och lägger tillbaka raderade artiklar per rubrik.
- Onboardingens erbjudanden skrivs som egna erbjudanden med strängvillkor som gäller alla produkter. Därför bär utkastet ett erbjudande ('3 månaders fri support') trots att produktlistan är tom.
- Onboardingen fyller aldrig settings.produkter, trots att 'Vad vi säljer' (input.produkt, obligatoriskt, onboarding.ts:246-247) redan finns. Grundorsaken till (c) sitter alltså i onboardingen och är densamma för alla nya kunder, inte bara testarbetsytor.
- leads-systemprompt.md:13 förbjuder bara 'Snajp, Iris, AI-leverantörer'. Produktnamnen 'Supportagent' och 'Kvittohanterare' saknas i förbudet, så modellen får använda dem för andra kunder.
- leads_research_v2.py:1183 klassar produkten ur researchens vald_produkt via produktslag när vald_nu är None. Om researchen hittar på ett produktnamn med 'support' (till exempel ur erbjudandets namn) väljs Snajps ingångsform och moment.
- Prodfragan saknar is_demo, workspaces.slug-mönstret (kund-/testkund-), testinkorgens skapandetid och leads-inställningarnas erbjudanden och produkter. Utan dem går det inte att skilja keys.py-vägen från inbox-vägen eller bekräfta källan till '3 månaders fri support'.
- Koden för alla berörda vägar (lib/snajp, lib/actions, snajp-support/app/leads, agent, agent-core) är identisk på origin/main och origin/development. Kontrollerat med git diff --stat, tom.

## GRANSKARE: justerat förslag
- 1. Grunden för (c), minsta ändring: onboardingen skriver kundens första produkt. I lib/snajp/standard.ts (sattStandardinstallningar) läggs en rad {namn: företagets kortnamn för det de säljer, nytta: input.produkt} till i settings.produkter, men bara när listan är tom, enligt samma regel som övriga fält. Samma funktion körs vid inloggning för äldre kunder (provisionering.ts), så befintliga kunder utan produkter får raden också. Tester: lib/snajp/standard.test.ts (node --test) prövar att en tom produktlista får en rad ur 'Vad vi säljer' och att en befintlig lista inte skrivs över.
- 2. Spärr före modellen, i den befintliga grinden. business_context.require_business_context, eller en granne som anropas på samma två ställen (run_outreach_draft_v2 och körstart i api/leads.py), kastar MissingBusinessContextError när las_produkter är tom. Det tidigare förslagets 'eller tillagda salj-artiklar' stryks: först punkt 1, sedan spärren, så att ingen ny kund stoppas. Beskedet visas i draft_note och körningsstatus, på svenska och engelska. Test: tests/leads/test_eget_erbjudande_sparr.py.
- 3. Kodgrind mot Snajps produktnamn hos andra kunder. stilkontroll får fyndet snajp_produkt_hos_kund som stoppar köning när en tenant med slug skild från 'snajp' får ett utkast som nämner Supportagent, Iris, Kvittohanterare eller Snajp, och namnet inte finns bland kundens produkter. leads-systemprompt.md:13 får 'Supportagent, Kvittohanteraren' i förbudslistan; det är inte den låsta facit-filen. produktslag-beroende förebilder och moment grindas på Snajp-tenanten, men det kan vänta. Test: tests/leads/test_stilkontroll_snajp_produkt.py och regressionen enligt UTKASTKEDJAN-REFERENS § 7 (utkastfacit 2026-10-16 och 2026-10-12, test_stilkontroll_2026_10_12, test_leads_v2_wiring).
- 4. Nordlys, hela klassen: båda vägarna stängs för testarbetsytor som har en webbplats. I keys.py seedas bara när anroparen ber om det (exempel_kb). I inbox.py:95 seedas bara när basen är helt tom OCH ingen skanning har körts eller väntar, så att raderade artiklar inte kommer tillbaka. Det är Antons beslut om testarbetsytan ska få skanningsförslag med hög konfidens tillagda automatiskt i stället. Tester: test_kb_seedning.py ändras för båda vägarna (keys och inbox-mock), och tests/api/test_inbox_mock_seedar_inte_om.py prövar att en raderad Nordlys-artikel inte läggs tillbaka.
- 5. Arbetsytans namn: onboarding.ts:529 får företagsnamnet i stället för `Testarbetsyta ${webbplats}`. Testmärket bärs av slug och is_demo.
- 6. Kunskapsbasen som bärare av Iris fakta (kategorin salj, skanningen, context_pack) är ett större designbeslut. Det löser inte (c) när punkt 1 och 2 är på plats, eftersom Iris läser produkter och product_marketing. Det bör tas som en separat beställning till Anton, med migrationen för CHECK-villkoret, och inte i samma rättning.
- 7. Prodfrågan, skrivskyddad och inte körd. Den läser workspaces.slug, is_demo och name för test@testsson.nu via auth.users → profiles → workspaces. Den läser ss_tenants.created_at, ss_knowledge_base (title, category, created_at, embedding is null) och den tidigaste testinkorgsraden för tenanten, för att se om Nordlys kom vid tenantens skapande eller vid första 'Hämta testmail'. Den läser också agent_configs.settings där agent_type = 'leads': settings->'erbjudanden'->'villkor' (väntat: '3 månaders fri support'), settings->'produkter' och updated_at. Jämförelsen sker mot created_at för den kö-rad som innehåller utkasten med 'Supportagent' och 'upphandling av företagstelefoni'.
