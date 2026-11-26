# paket kunskapsbas-saljfakta

## Bygge
Säljfakta i kunskapsbasen är byggt och de riktade testerna går igenom. Webbplatsskanningen ber nu i samma LLM-anrop om både supportartiklar och säljfakta i kategorin "salj": tjänster och nytta, målgrupp, bevis och pris. Kategorin finns bara i kunskapsbasen (config.KB_CATEGORIES och en ny migration 153). Triagen och ärendena läser fortfarande config.CATEGORIES och kan inte välja "salj". Två regler gäller nu i kod och inte bara i prompten. En säljartikel med en siffra som inte står på webbplatsen kasseras helt, eftersom den annars blir en tillåten siffra i grundningsgrinden. En prisartikel kasseras när sajten saknar pris. Kontextpaketet (build_context_pack) får avsnittet "Kundens egna fakta ur kunskapsbasen" med kundens tillagda salj-artiklar. Utgångna artiklar, supportartiklar och förslag som inte lagts till tas inte med. Avsnittet hamnar därmed i grundningsgrindens underlag. I artikellistan i Kunskapsbas.tsx står nu kategorin som etikett på båda språken. Förslagslistan ligger i en annan fil (WebbplatsForslag.tsx), och något befintligt filter finns inte. De två delarna är därför inte gjorda, se ej_gjort. Begäran "ta bort tempmapparna helt" har jag inte utfört här (se ej_gjort).

### Ändrade filer
- C:\Users\Anton L\snipe-leads\snajp-support\app\config.py (nya KB_SALJ = "salj" och KB_CATEGORIES = (*CATEGORIES, KB_SALJ); CATEGORIES, CATEGORY_LABELS och DEFAULT_CATEGORY_RULES är oförändrade med flit)
- C:\Users\Anton L\snipe-leads\snajp-support\app\kb_skanning.py (importerar KB_CATEGORIES och KB_SALJ; SYSTEMPROMPT beställer två slags artiklar, med regel 4 för säljfakta och 'Står inget pris på sajten, skriv ingen prisartikel'; format(..., salj=KB_SALJ); _sanera_artikel tar emot KB_CATEGORIES och kasserar salj-artiklar med obelagda siffror och prisartiklar när webbplatsen saknar pris (_PRIS_RE); nytt _PRISORD)
- C:\Users\Anton L\snipe-leads\snajp-support\app\leads\context_pack.py (render_context_pack får parametern kb_salj; ny KB_SALJ_RUBRIK = 'Kundens egna fakta ur kunskapsbasen' och _kb_salj(storage, tenant_id) som läser list_kb, alltså bara tillagda artiklar, filtrerar på category == 'salj' och hoppar över passerad giltig_till; build_context_pack skickar in den)
- C:\Users\Anton L\snipe-leads\components\settings\Kunskapsbas.tsx (modulkonstanten KATEGORI: Record<string, Localized> med sv och en för alla KB-kategorier, bland dem salj 'Erbjudande och säljfakta' / 'Offer and sales facts'; i artikellistan visas etiketten i ett span efter rubriken)

### Nya filer
- C:\Users\Anton L\snipe-leads\db\migrations\20261125100000_153_kb_kategori_salj.sql (drop if exists och add av ss_knowledge_base_category_check med 'salj' tillagd; ss_tickets och ss_classifications rörs inte; ss_kb_forslag.category har inget CHECK-villkor och behöver ingen ändring)
- C:\Users\Anton L\snipe-leads\snajp-support\tests\test_kb_skanning_saljfakta.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\leads\test_context_pack_kb.py
- C:\Users\Anton L\snipe-leads\snajp-support\tests\test_kb_kategori_salj.py
- C:\Users\ANTONL~1\AppData\Local\Temp\claude\20bc186535c3c092\fd9b0b93-e92d-4cea-a78c-7ea782ace803\scratchpad\tsconfig.kb.json (tillfällig, för den avgränsade tsc-körningen, ligger inte i repot)

### Tester
- `python -m pytest -q tests/test_kb_skanning_saljfakta.py (före rättningen)` → 1 error in 2.83s (KB_CATEGORIES fanns inte)
- `python -m pytest -q tests/leads/test_context_pack_kb.py (före rättningen)` → 2 failed, 2 passed in 6.73s
- `python -m pytest -q tests/test_kb_kategori_salj.py (före rättningen)` → 1 error in 37.12s
- `python -m pytest -q tests/test_kb_skanning_saljfakta.py` → 4 passed in 1.41s
- `python -m pytest -q tests/leads/test_context_pack_kb.py` → 4 passed in 1.86s
- `python -m pytest -q tests/test_kb_kategori_salj.py` → 4 passed in 13.21s
- `python -m pytest -q tests/api/test_kb_forslag.py` → 8 passed in 17.07s (föll först med 1 failed när jag hade lagt en kategorivalidering i KbArticle; valideringen är borttagen igen)
- `python -m pytest -q tests/api/test_kb_skanning.py` → 16 passed in 27.71s
- `python -m pytest -q tests/leads/test_context_pack.py` → 5 passed in 1.94s
- `python -m pytest -q tests/leads/test_onboarding_state.py` → 9 passed in 1.64s
- `python -m pytest -q tests/test_sim_triage.py` → 20 passed in 1.31s
- `python -m pytest -q tests/invariants/test_delete_grants.py (snajp-support)` → 1 passed in 1.40s
- `python -m pytest -q tests/test_pilot_kb_utkast.py (repots rot)` → 67 passed in 2.12s
- `python -m pytest -q tests/test_rls_nullif_vakt.py (repots rot)` → 5 passed in 0.22s
- `python -m pytest -q tests/invariants/test_inv_copy_001.py (repots rot)` → 4 passed in 2.14s
- `node node_modules/typescript/bin/tsc -p scratchpad/tsconfig.kb.json (bara Kunskapsbas.tsx och dess importer, max-old-space 1536 MB; ledigt virtuellt minne var 3,7 GB)` → exit 1: inga fel i Kunskapsbas.tsx. De enda felen var components/AppShell.tsx(443,25) och (509,23) TS2322 'Promise<{ url: string; }>' is not assignable to 'Promise<void>'. De kommer av en annan byggares pågående ändring av lib/actions/auth.ts, inte av mitt paket.

### Ej gjort
- Begäran 'Ta bort tempmapparna helt, gör det nu' är inte utförd. Den anger inte vilka mappar som avses. Den delade scratchpaden innehåller utredningen (fynd-kunskapsbas.md) som tre andra byggare arbetar mot just nu, och radering kan inte ångras. Orkestreraren eller Anton behöver säga exakt vilka mappar som ska bort, till exempel gamla .claude/worktrees/agent-* för att frigöra disk åt CRM-sessionen.
- Förslagslistan: säljfakta visas med kategorietikett bara i artikellistan i Kunskapsbas.tsx. Förslagslistan renderas av components/settings/WebbplatsForslag.tsx, som ligger utanför mitt paket. Den visar ingen kategori i dag. Där behövs samma KATEGORI-etikett, och den bör flyttas till en delad modul eller exporteras från Kunskapsbas.tsx.
- Filtret: Kunskapsbas.tsx och WebbplatsForslag.tsx har inget befintligt kategorifilter. Att lägga till ett hade varit en ny kontroll ovanpå ytan, vilket strider mot regeln 2026-11-24, så jag har inte byggt något. Om Anton vill ha ett filter är det ett eget beslut.
- Ingen förhandsvisning under app/forhandsvisning/ finns för Kunskapsbas, och mitt paket fick inte lägga till en. Orkestreraren behöver en, till exempel app/forhandsvisning/kunskapsbas/page.tsx som renderar KunskapsbasPanel och besvarar /api/snajp-support/kb (artiklar med category 'salj' och 'leverans') och /api/snajp-support/kb/forslag i webbläsaren.
- Ingen kategorivalidering i KbArticle (schemas.py). Jag provade en validator mot KB_CATEGORIES, men den fällde tests/api/test_kb_forslag.py::test_sparad_skanning_kompletterar_och_skriver_aldrig_over, som postar category 'allmant' mot MemoryStorage. Därför tog jag bort den. Schemat har ingen kategorilista och tar redan emot 'salj'. Min diff i schemas.py är tom; de +4 raderna där (exempel_kb) kommer från ett annat paket.
- Supportagentens search_kb filtrerar inte bort salj-artiklar, så supportagenten kan citera dem, till exempel vid prisfrågor. Det är oförändrat och avsiktligt enligt utredarens förslag 3, men inget beslut i beställningen tar ställning till det.
- kb.py behövde ingen ändring: förslag och tillägg går redan igenom oförändrad category. Varken ARCHITECTURE_INVARIANTS.md eller docs/BESLUT.md är ändrade. Ingen invariant beskriver kategorilistan i kunskapsbasen eller vad kontextpaketet läser, och BESLUT.md skriver orkestreraren.
- Varken commit eller git add är gjorda, och migrationen är inte körd mot någon databas.

### Antaganden
- Migrationsnummer 153 var ledigt när filen skrevs (senaste var 152). Om en annan byggare också tar 153 måste ett av numren bytas.
- Om en salj-artikel innehåller en siffra som inte står på webbplatsen kasseras den helt i stället för att få en varning som supportartiklarna. Skälet är att context_pack går in i build_permitted_facts, så en påhittad siffra skulle bli tillåten i Iris utkast.
- En prisartikel känns igen på rubriken (' pris', ' kostnad', ' kostar', ' price' efter _for_matchning). Sajten räknas ha pris om _PRIS_RE träffar i källsidan eller i webbplatsens text.
- Salj-avsnittet i kontextpaketet ramas inte in med wrap_untrusted_content. Ramens UUID innehåller siffror som annars hade hamnat i grundningsgrindens tillåtna mängd. Texten har kunden själv granskat och lagt till, precis som product_marketing, som inte heller ramas in.
- Artiklar med passerad giltig_till räknas inte med, enligt samma regel och svenska datum som kunskapsbasens sökning.
- 'salj' ligger med flit inte i CATEGORY_LABELS: api/leads.py:1449 väljer ärendefack med 'kategori in CATEGORY_LABELS'.
- Kategorietiketterna i Kunskapsbas.tsx följer SupportOversikt.tsx (till exempel 'Reklamation & retur').

### Syns i gränssnittet
- Inställningar › Kunskapsbas (KunskapsbasPanel), avsnittet 'I kunskapsbasen (n)': på varje rad står kategorin som en liten grå etikett (13px, text-ink-subtle) efter rubriken i samma p-element, till exempel 'Pris  Erbjudande och säljfakta' eller på engelska 'Offer and sales facts'. Supportartiklarna får sina fack, till exempel 'Leverans' / 'Delivery'. Raden kan radbrytas på mobil och behöver ses på både desktop och mobil.
- Ingen förhandsvisning finns. För att se ändringen utan databas behövs app/forhandsvisning/kunskapsbas/, som saknas i dag (se ej_gjort).
- Indirekt: skanningens förslagslista (WebbplatsForslag.tsx) kommer nu att innehålla säljfakta-förslag, men utan kategorietikett, eftersom den filen inte ingick i paketet.

## Granskning: godkänd=True
- [bor_rattas] components/settings/WebbplatsForslag.tsx: Beslut 3 är bara delvis uppfyllt. Säljfakta ska synas med kategorietikett i den befintliga förslagslistan, men förslagslistan renderas av WebbplatsForslag.tsx (importeras i Kunskapsbas.tsx rad 12, används rad 347). Den filen ingick inte i paketet. Kunden ser därför salj-förslagen blandade med supportförslagen utan etikett just när hen ska välja vilka som läggs till, och det är bara tillagda artiklar som når Iris. Något befintligt kategorifilter finns inte i någon av filerna (kontrollerat), så delen om filtret går inte att uppfylla utan att bygga en ny kontroll. FÖRSLAG: Orkestreraren ger ett paket som får röra WebbplatsForslag.tsx. Där visas samma etikett på varje förslag. Exportera KATEGORI från Kunskapsbas.tsx, eller flytta den till en delad modul, i stället för att skapa en fjärde kopia. Om ett filter ska finnas är det Antons beslut, enligt regeln 2026-11-24.
- [bor_rattas] app/forhandsvisning/: Ändringen syns i gränssnittet (etiketten i artikellistan), men det finns ingen förhandsvisning av Kunskapsbas under app/forhandsvisning/. Enligt CLAUDE.md får ändringen inte committas innan den har setts i bild på desktop och mobil. FÖRSLAG: Lägg till app/forhandsvisning/kunskapsbas/. Den ska rendera KunskapsbasPanel och besvara /api/snajp-support/kb (med artiklar i kategorierna salj och leverans) och /api/snajp-support/kb/forslag i webbläsaren. Ta bilder på desktop och mobil före commit.
- [notering] snajp-support/app/kb_skanning.py:717-727 Prisspärren känns bara igen på rubriken (_PRISORD: ' pris', ' kostnad', ' kostar', ' price'). En engelsk rubrik som 'Pricing' eller 'Cost' träffas inte. Spärren kontrollerar dessutom pris var som helst på sajten, inte på artikelns källsida. En prisartikel utan siffror ('kontakta oss för offert') släpps därför igenom om någon annan sida har ett kr-belopp, till exempel en fraktkostnad. Siffror i prisartiklar fångas ändå av obelagda_siffror, så ingen påhittad siffra når grundningsgrinden. FÖRSLAG: Godtagbart som det är. Lägg eventuellt till 'pricing' och 'cost' i _PRISORD.
- [notering] snajp-support/app/leads/context_pack.py:79-101 Salj-avsnittet ramas med flit inte in med wrap_untrusted_content (skälet: ramens UUID-siffror skulle hamna i grindens tillåtna mängd). Texten kommer från kundens webbplats och har passerat kundens klick på Lägg till, men den går orammad in i research- och utkastprompten. Det är en avvägning som ingen invariant tar ställning till. Avsnittet har heller inget längdtak. FÖRSLAG: Ingen ändring krävs nu. Orkestreraren bör skriva avvägningen i docs/BESLUT.md och lägga till en rad i docs/FALTKARTA.md: ss_knowledge_base med category salj, läses av leads/context_pack.py.
- [notering] snajp-support/tests/test_kb_kategori_salj.py:27-29 test_triagen_kan_inte_valja_salj fäller inte den gamla koden, eftersom tolka_svar redan validerade mot CATEGORIES. Testet är ett regressionsskydd och inget test som fäller dagens kod. Filen som helhet föll före rättningen, men bara på importen av KB_CATEGORIES. FÖRSLAG: Godtagbart som regressionsvakt. Inget att åtgärda.
- [notering] components/settings/Kunskapsbas.tsx:49-59 KATEGORI-tabellen är en tredje kopia av samma etiketter som finns i components/snajp/Dashboard.tsx:120 och SupportOversikt.tsx:155. Dubbleringen fanns redan och följer filens stil, men nästa ändring av en etikett måste göras på tre ställen. FÖRSLAG: Låt den stå i det här paketet, och samla tabellen när WebbplatsForslag.tsx också behöver den.

### Utanför paketet
- snajp-support/app/api/schemas.py: diffen (fältet exempel_kb i CreateKeyRequest) hör till ett annat paket (Nordlys-seedningen), inte till kunskapsbas-saljfakta. Byggarens egen diff i filen är tom.
- components/settings/WebbplatsForslag.tsx: behöver kategorietiketten för att beslut 3 ska uppfyllas, men låg utanför paketet och är inte rörd.
- app/forhandsvisning/kunskapsbas/: saknas och behövs för att ändringen ska kunna ses i bild före commit.
- docs/FALTKARTA.md och docs/BESLUT.md: den nya läsvägen från kunskapsbasen till leadskedjan och valet att inte rama in salj-texten bör dokumenteras där. Det gör orkestreraren.
- Den vidarebefordrade begäran 'Ta bort tempmapparna helt, gör det nu' ligger utanför granskningssteget. Jag har inte utfört den och inte raderat något, eftersom den inte säger vilka mappar som avses.

### Granskarens tester
- `cd snajp-support && python -m pytest -q tests/test_kb_skanning_saljfakta.py` → 4 passed in 1.86s
- `cd snajp-support && python -m pytest -q tests/leads/test_context_pack_kb.py` → 4 passed in 3.24s
- `cd snajp-support && python -m pytest -q tests/test_kb_kategori_salj.py` → 4 passed in 50.09s
- `cd snajp-support && python -m pytest -q tests/api/test_kb_skanning.py` → 16 passed in 78.16s (0:01:18)
- `cd snajp-support && python -m pytest -q tests/leads/test_context_pack.py` → 5 passed in 3.63s
- `python -m pytest -q tests/invariants/test_inv_copy_001.py (repots rot)` → 4 passed in 2.46s

## Rättning
Jag har prövat båda fynden mot koden och båda stämmer. components/settings/WebbplatsForslag.tsx visar ingen kategori, och under app/forhandsvisning/ finns ingen förhandsvisning (katalogen är tom för Kunskapsbas, kontrollerat med Glob). Båda filerna ligger utanför mitt paket, och granskaren säger själv att orkestreraren behöver ge ett paket som får röra dem. Därför har jag inte rättat dem. I paketet har jag gjort en sak: KATEGORI i Kunskapsbas.tsx exporteras nu, så att nästa paket kan visa samma etikett i förslagslistan utan att skapa en fjärde kopia. INV-COPY-001 går fortfarande igenom. Jag har inte raderat några tempmappar (se ej_gjort).

### Ändrade filer
- C:\Users\Anton L\snipe-leads\components\settings\Kunskapsbas.tsx (rad 49: `const KATEGORI` har blivit `export const KATEGORI`. Inget annat är ändrat.)

### Tester
- `python -m pytest -q tests/invariants/test_inv_copy_001.py (repots rot)` → 4 passed in 2.81s

### Ej gjort
- Fynd 1, etiketten i WebbplatsForslag.tsx: fyndet stämmer, för filen har varken KATEGORI eller någon kategorietikett. Filen ligger utanför paketet och är därför inte ändrad. Nästa paket gör så här: i varje förslagsrad visas `loc.text(KATEGORI[forslag.category])` när nyckeln finns, i samma lilla grå span som i artikellistan. Observera att Kunskapsbas.tsx redan importerar WebbplatsForslag. Om WebbplatsForslag importerar KATEGORI tillbaka blir importen cirkulär. Det fungerar, eftersom värdet bara läses vid rendering, men det är renare att flytta KATEGORI till en liten delad modul, till exempel components/settings/kbKategori.ts, och importera den i båda filerna.
- Fynd 1, filtret: inget befintligt kategorifilter finns i någon av filerna. Att bygga ett vore en ny kontroll ovanpå ytan och strider mot regeln 2026-11-24. Om det ska finnas ett filter är det Antons beslut.
- Fynd 2, förhandsvisningen: fyndet stämmer, för app/forhandsvisning/ har ingen Kunskapsbas-vy. Katalogen ligger utanför paketet och är inte skapad. Det som behövs är app/forhandsvisning/kunskapsbas/page.tsx. Den ska rendera KunskapsbasPanel och besvara /api/snajp-support/kb (artiklar i kategorierna salj och leverans) och /api/snajp-support/kb/forslag i webbläsaren. Efter det ska den ses i bild på desktop och mobil före commit.
- Begäran 'Ta bort tempmapparna helt, gör det nu' är inte utförd. Den säger inte vilka mappar som avses, och radering går inte att ångra. Den delade scratchpaden innehåller dessutom utredningen som andra byggare arbetar mot just nu, och i arbetskatalogen pågår tre andra byggare. Sammanhanget tyder på att målet är att frigöra disk åt CRM-sessionens worktree: 4,2 GB ledigt, 5,4 GB behövs. Orkestreraren eller Anton behöver peka ut exakt vilka mappar som ska bort, till exempel gamla .claude/worktrees/agent-*.
- Jag har inte kört om den avgränsade tsc-kontrollen. Ändringen lägger bara till ett export-nyckelord på en befintlig konstant och påverkar inga typer.
- Varken commit eller git add är gjord.

### Antaganden
- Uppdraget att rätta fynden gäller bara paketets filer. Båda fynden pekar på filer utanför paketet, så det jag kunde göra inom paketet var att förbereda återanvändningen genom att exportera KATEGORI.
- Begäran om tempmapparna gäller diskutrymmet för CRM-sessionens worktree och inte det här paketet. Den är för otydlig för att radera något på.

### Syns i gränssnittet
- Inget nytt syns i den här rundan, eftersom exporten inte ändrar hur något renderas. Det som redan syns sedan förra rundan gäller fortfarande: i Inställningar › Kunskapsbas, listan 'I kunskapsbasen (n)', står kategorin som en grå etikett efter rubriken på varje rad. För att den ska kunna ses utan databas behövs förhandsvisningen app/forhandsvisning/kunskapsbas/, och den finns inte ännu.
