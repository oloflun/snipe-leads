# karta agentkoppling

Det finns ingen väg i dag som skickar ett kundärende vidare till en agent som skriver kod. Det saknas ett arbetsflöde, ett skript, en tabell och en kö för det. Det som finns att bygga på är tre saker. Två arbetsflöden skapar redan GitHub-ärenden med etikett (`overvakning.yml`, `sakerhetsbevakning.yml`, båda med `issues: write` och bara `GITHUB_TOKEN`). `platform_events` ger fel per kund med run_id och detaljer. `untrusted_content.py` kan märka kundtext som data.

Det viktigaste fyndet: repot oloflun/snipe-leads är PUBLIKT just nu. `gh api` ger visibility=public, updated_at 2026-11-23T23:08Z, och github.com/oloflun/snipe-leads svarar 200 utan inloggning. Ändå säger docs/BESLUT.md:1611 (2026-11-18) att repot är privat, och rad 1624 säger att docs/compliance ska flyttas ut först om repot görs publikt igen. Den mappen ligger på origin/development: 108 spårade filer med docs/compliance, JURIDIK_ATGARDER och DPIA:n. Inget nytt beslut om publikt finns i BESLUT.md.

Följden för det här bygget är att ärendetext, kundnamn, mejladresser eller arbetsytenamn aldrig får skrivas till GitHub (ärenden, PR-text, commits eller grennamn). Ärendet ska ligga i Snajps egen databas, och agenten ska få ett avpersonifierat arbetsunderlag.

Grenskyddet är svagare än DEPLOY.md påstår. På main finns bara regeluppsättningen main-3: en godkännande granskning, inget krav på kodägare, och admin-rollen får alltid gå förbi. development har i praktiken inget skydd, eftersom "Standard rules" har tomt include. Kör en agent med Antons token kan den alltså pusha direkt till development. Den grenen deployar sig själv mot en databas som speglar produktionen.

Rekommendationen är en kö i Snajps databas som en agent hämtar ur. Agenten ska ha en egen GitHub-identitet utan admin-roll och utan workflow-rätt, och får bara öppna en PR mot development från grenen fix/arende-<id>. En ny regeluppsättning på development ska kräva PR och Antons godkännande. Kundtexten kapslas som opålitlig data, går först genom ett steg utan verktyg som gör den strukturerad, och agenten har inga hemligheter, ingen databas och ingen produktionsåtkomst.

## Befintligt
- gh api repos/oloflun/snipe-leads (läst 2026-11-25): Repot är publikt nu (visibility=public, private=false, updated_at 2026-11-23T23:08:42Z; github.com svarar 200 utan inloggning). Standardgrenen enligt API:t är main, inte development som overvakning.yml påstår.
- docs/BESLUT.md:1611-1628 Beslutet att repot är privat, och att docs/compliance ska flyttas ut innan det görs publikt igen. Det finns ingen senare post om att repot blivit publikt.
- docs/BESLUT.md:225-238 Repot blev privat 2026-11-18, Actions-minuterna tog slut 2026-11-23, och 'Grenskyddet på main kommer inte tillbaka … kräver GitHub Pro eller ett publikt repo'
- git ls-tree origin/development: Känsliga dokument som ligger publikt på origin/development: 108 filer under docs/compliance, docs/JURIDIK_ATGARDER.md och docs/dpia_supportagenten.md. Därtill pub-avtal.md och INCIDENT_RESPONSE.md, som också är spårade.
- .github/CODEOWNERS:2 CODEOWNERS: '* @oloflun' (Anton ensam kodägare)
- gh api repos/oloflun/snipe-leads/rulesets/{20942445,27592970-72}: Regeluppsättningen main-3 (pull_request): required_approving_review_count=1, require_code_owner_review=false, bypass för RepositoryRole 5 (admin) 'always'. main-1 förbjuder radering och main-2 förbjuder force-push, med undantag för användare 241491751. 'Standard rules' har include=[] och gäller därför ingen gren, så development saknar skydd.
- DEPLOY.md:51-58 DEPLOY.md påstår att grenskyddet kräver code owner-review från oloflun. Det stämmer inte med regeluppsättningarna ovan.
- .github/workflows/: Arbetsflödena: indexnow, migrera, overvakning, pr-granskning, sakerhetsbevakning, synk, verify. Inget använder pull_request_target, issues-händelser eller issue_comment, och inget startar en agent.
- .github/workflows/migrera.yml:34-45, 141-178 migrera.yml: kör migrationer vid push till development eller main när db/migrations ändras. På PR mot main körs jobbet 'granska' med SCHEMA_LASNYCKEL och, som reserv, ENV_DEPLOY och RAILWAY_*_PG_* för PR:er från repots egna grenar.
- .github/workflows/synk.yml:18-56 synk.yml använder ENV_DEPLOY och RAILWAY_MAIN/DEVELOPMENT_PG_{PASSWORD,HOST,PORT} och startas bara för hand
- .github/workflows/verify.yml:18-60 verify.yml körs på varje pull_request med permissions actions: write och issues: write. Postgres-tjänsten är syntetisk och inga hemligheter används.
- .github/workflows/overvakning.yml:96-130; sakerhetsbevakning.yml 98-190 Mönster för att skapa GitHub-ärenden med etikett från CI, med sanerad text: overvakning.yml skapar 'driftlarm' och sanera() släpper bara igenom [A-Za-z0-9._-]{1,32}, sakerhetsbevakning.yml skapar 'sakerhetsbevakning'. Båda använder bara GITHUB_TOKEN med issues: write.
- scripts/overvakning_dodman.sh:16, 69-142 Skript som pratar med GitHub: overvakning_dodman.sh (gh issue/label/api) och sakerhetsbevakning.py (läser advisories och skriver inget). Inget skript skapar grenar eller PR:er eller startar en agent.
- .github/ISSUE_TEMPLATE/ai-oro.yml:1-12 Ärendemallen ai-oro med etiketten ai-oro, som varnar 'Skriv inga personuppgifter, kundmejl eller hemligheter här' och hänvisar till ärende-id och körnings-id
- .github/pull_request_template.md:1-25 PR-mallen och INV-PROC-001: varje PR måste kryssa i säkerhets- och AI-frågan, kontrolleras av pr-granskning.yml och scripts/pr_granskning.py
- db/migrations/026_platform_events.sql:14-45 platform_events (notiscentret): tenant_id kan vara tomt, level, source, message, detail jsonb, run_id. Bara backendens snajp_app läser och skriver.
- snajp-support/app/api/events.py:27-60 log_event/log_exception skriver till platform_events och sväljer sina egna fel
- db/migrations/20261007100000_102_kundonskemal.sql:1-18 Migration 102: kundens önskemål sparas som agent_context_docs.kind 'kundonskemal_leads' och 'kundonskemal_support'. Det är återkoppling till kundens EGEN agent, inte till Snajps kod.
- snajp-support/app/leads/onskemal.py:1-40 onskemal.py: kundtexten bakas in i användarposition och kapslas som opålitlig enligt INV-SEC-009, med MAX_TECKEN 4000 och MAX_PER_DYGN 10
- db/migrations/20261120030000_145_feedback_foljer_korningen.sql:1-13, 334-351 Migration 145 handlar om gallringen av agent_feedback, alltså återkoppling på agentkörningar. Den rör inte felrapporter till plattformen.
- snajp-support/app/leads/untrusted_content.py:30, 56 Kapslingen av opålitlig text: kapsla_kundtext() och wrap_untrusted_content(content, source=)
- ARCHITECTURE_INVARIANTS.md:259 INV-SEC-009: kundskriven text når aldrig instruktionsposition
- docs/pub-avtal.md:45-48, 296-330 PUB-avtalets öppna fråga 8: development är en full kopia av produktionen och synkas via GitHub Actions på amerikanska servrar. Kapitel 12 och 13 begränsar modellerna till leverantörerna i Bilaga 3, och personnummer maskeras.
- scripts/lokal_stack.py:1-30; app/forhandsvisning/ Lokal stack och förhandsvisningar utan databas, som en agent kan använda för att verifiera utan riktig data

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

## Fästpunkter
- Förlagan för att skapa ärenden från CI är overvakning.yml: sanera(), etiketten skapas om den saknas, ett ärende per nyckel och dubbletter undviks med en nyckelmarkör i ärendekroppen (sakerhetsbevakning.py NYCKEL_RE). Den passar för ett GitHub-ärende som bara bär id och status.
- snajp-support/app/api/events.py:log_event och platform_events ger felkontexten (source, run_id, detail). Felrapporten kan peka på händelse-id i stället för att kopiera text.
- snajp-support/app/leads/untrusted_content.py:wrap_untrusted_content och kapsla_kundtext används för att märka kundtexten som data i agentens prompt, i samma mönster som onskemal.py och INV-SEC-009.
- Kunden ska kunna följa ärendet i Snajp, inte på GitHub. Det kräver en ny tabell med ärende, status, gren, PR-nummer, spegelns adress, kundens testutfall och Antons ja, och en endpoint i snajp-support/app/api/ som admin och agenten (med en egen nyckel) läser och skriver.
- Föreslagen kedja: (1) Felrapport i chattrutan blir en rad i Snajps databas plus ett ärende hos Snajp som tenant. (2) Ett steg utan verktyg gör ett avpersonifierat arbetsunderlag (sida, steg, förväntat, faktiskt, platform_events-id). (3) En agentarbetare hämtar underlaget via en egen nyckel och kör i en isolerad katalog eller container utan .env.deploy och utan Railway-token. (4) Den pushar fix/arende-<id> och öppnar en PR mot development med PR-mallen ifylld. (5) Spegeln byggs. (6) Kunden testar och svarar i rutan. (7) Anton godkänner och mergar till development, och release till main sker bara på hans uttryckliga ord.
- Ny regeluppsättning på development: kräv PR, en godkännande granskning och kodägare. Begränsa admin-undantaget till Antons användar-id (som main-2 gör med actor_id 241491751), inte rollen, så att agentens identitet aldrig kan gå förbi.
- Agentens identitet ska vara en GitHub App eller en finkornig token begränsad till repot, med contents: write och pull_requests: write, utan workflows, administration, secrets eller actions. Den ska inte vara Antons gh-inloggning.
- Grind i CI: ett nytt test eller en ny kontroll som fäller en PR från agentgrenen (fix/arende-*) som rör .github/, db/migrations/, CODEOWNERS eller hemlighetsläsande skript utan en etikett Anton satt. Förlagan är scripts/pr_granskning.py.
- Verifiering i agentens sandlåda: scripts/lokal_stack.py och app/forhandsvisning/ ger körbarhet utan riktig data, i linje med CLAUDE.md:s regel om att se med egna ögon.
- Nytt beslut i docs/BESLUT.md enligt projektregeln: vidarekopplingen, vilken identitet agenten har, vad som lämnar Snajp och Antons godkännandesteg.

## Kräver Anton
- BRÅDSKANDE: repot är publikt sedan cirka 2026-11-23 23:08 UTC, trots beslutet att det är privat (BESLUT.md:1611). docs/compliance (DPIA, juridiska åtgärder, incidentloggen och PUB-utkastet) ligger därmed publikt. Är det avsiktligt (till exempel för Actions-minuterna eller grenskyddet), eller ska repot göras privat igen och mappen flyttas ut?
- Ska den kodande agenten ha en egen GitHub-identitet (GitHub App eller finkornig token)? Att skapa den kräver Antons hand: kontoåtgärd och OAuth i tredjepartskonsol.
- Godkänn en ny regeluppsättning på development som kräver PR och granskning, med undantag bara för Antons användare. Det ändrar arbetssättet för Sebbe och för alla agenter som i dag pushar direkt till development.
- Ändra main-3 till require_code_owner_review=true och ersätt rollundantaget med Antons användar-id, så att DEPLOY.md stämmer.
- Vilken modell och region får den kodande agenten använda för felrapporter? Står leverantören i PUB Bilaga 3, och får felrapportens innehåll gå dit?
- Var ska agenten köras: på Antons maskin (fönsterlöst), som en tjänst hos Railway, eller i GitHub Actions? Det sista kostar Actions-minuter om repot är privat och exponerar mer om det är publikt.
- Vilka personuppgifter får följa med till agenten: bara ärende-id, sida och avpersonifierade steg, eller också kundens fritext? Och ska ingenting alls från kunden skrivas till GitHub så länge repot är publikt?
- Ska kundens 'det fungerar' i spegeln vara ett krav före Antons granskning, eller bara information till honom? Ett ja från kunden får aldrig ersätta Antons ja inför development och main.
