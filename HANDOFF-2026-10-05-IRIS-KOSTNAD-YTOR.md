# Handoff 2026-10-05 — Iris billigare och skarpare, inkorgen rätt, Leads/Att göra/Översikt, flytt till main

## 1. Läget just nu, verifierat (2026-10-05)

- **Git:** `development` = `origin/development` = `357f637`. Inget opushat utöver Antons egna ocommittade filer (`docs/utkast-merinfo-api-forfragan.md`, `next-env.d.ts`, `strategies.md`, `docs/utkast-allabolag-api-forfragan.md`, `gsap.js`, `smooth-scroll.js`, `session-logs/2026-09-30-session-log.md`) — rör dem inte.
- **main:** kod = PR #30 (mergad av Anton, `937ce5b`). Migrationer körda t.o.m. **095** (092–095 kördes mot main 2026-10-05).
- **development:** kod `357f637`, migrationer t.o.m. 095. Speglar sig som spegel igen (`flytt_nycklar.py --check`: `spegel=True`).
- **Öppen PR:** [oloflun/snipe-leads#31](https://github.com/oloflun/snipe-leads/pull/31) development → main, 23 commits. Inget att köra före merge. Mergen är Antons.
- **Flytta till main:** fungerar skarpt (signerat tomt paket mot main: 200; fel signatur: 403). Tills #31 är mergad landar flyttade leads **utan bedömning** i main (mains mottagare är äldre).
- **Externa blockerare:** ScrapeGraph-krediten slut (Anton fyller på); PageSpeed saknar API-nyckel (delad kvot slut, Gemini-nyckeln fungerar inte där) — utan den tas skärmbilden via ScrapeGraph (2 krediter). bd fungerar inte (dolt saknas).
- **Nattspeglingen** avbröt 2026-10-05 08:15 UTC på schemaskillnad (rätt beteende, inget rördes); schemat matchar nu, nästa natt ska gå igenom.

## 2. Vad som byggdes

Plan: `plans/2026-10-05-iris-kostnad-kvalitet-ytor.md`. Alla faser 1–6 klara; fas 7 (Firecrawl-mätning) ej påbörjad.

| Fas | Vad | Commit | Verifiering |
|---|---|---|---|
| 1 | Inkorgen: `automatutskick` ur headers (092), maskinadresser var som helst, sidfotsfraser; Kundtjänst › Dolda; sortera/klassa stänger ärende + avvisar utkast; bulkläge `status=escalated` | `d05e00e` | tester i `test_klassning.py`, `test_inbox_sortera.py` |
| 2 | `app/leads/sidhamtning.py`: cache per kund (093), httpx först, kredittak (40/körning, 6/research); merinfo i takt med behovet; registersidor aldrig "hemsida" | `98bde9c` | `test_sidhamtning.py`, budgettest N=5 ≤ 20 |
| 3 | `app/leads/webbrevision.py` (PageSpeed + bildbedömning), `bedomning.webbutslag`, listspår "Utan webbplats", ensam-VD-regeln, merinfo bolagsfakta utan personer (094); CLAUDE/AGENTS regel 7–9 | `6d0134c` | `test_webbedomning_facit.py`; skarp kalibrering mot Antons facit (`scripts/kalibrera_webbrevision.py`): Berggren 2, Ställningskompaniet 5, Björkekärr 7, Eustaff 8, Ostia internationell, Torbens parkerad |
| 4–5 | Leads underflikar (Leads/Inkorg/Utkast/Listor/Körningar), tabell i full bredd med statusremsa, låda (`LeadsSida.tsx`), Mejlutkast-felet (`lib/leads/offert.ts`), Att göra som kö | `205086c` | /demo 1440+375, låda Esc/fokus, axe rent |
| 6 | Översikten som dashboard (`OversiktPaneler.tsx`), `new_leads` i veckoanalysen, chart-tokens | `86dc1f8` | /demo, dataviz-validatorn, axe rent |
| — | Flytt: `mirror_meta` RLS utan policy dolde spegelmarkören (095); importen sparar bedömningen | `357f637` | `test_admin_flytt.py`, skarpt prov mot main |

Sebbes stödchatts-/utkastgrindsarbete mergades in två gånger utan konflikt; sviten 2557 gröna efteråt.

## 3. Vad som återstår, i prioritetsordning

1. **Anton mergar #31** — då får main inkorgssorteringen, Iris-förbättringarna, nya ytorna och flyttens bedömning. Inget behöver köras först.
2. **Anton fyller på ScrapeGraph** (1 000 krediter för $5 räcker). Därefter: agenten kör en Iris-körning N=5 på Alunix i development och läser kostnaden i Leads › Körningar (mål ≤ 20).
3. **Anton skapar en PageSpeed-API-nyckel** i Google Cloud och lägger `PAGESPEED_API_KEY` på Railway api (båda miljöerna).
4. **Kör "Sortera bort utskick"** på Alunix eskalerade kö i development (och i main efter #31) — agenten kan göra det via UI eller `POST /api/inbox/sortera {status:"escalated", tillampa:true}`.
5. **Fas 7:** Firecrawl-jämförelse på 20 URL:er — väntar på att Anton skapar ett gratiskonto och lägger nyckeln via `api-key-setup`.
6. **Visuell kontroll med riktig data:** Leads › Inkorg, Körningar, Kundtjänst › Dolda och Iris live-kortet under pågående körning har bara setts tomma/i demo.
7. **Full a11y-audit** (skillen) på development efter deploy — erbjuden, inte gjord.

## 4. Fällor

- **Auto-läget nekar `git merge -X ours` och diff-listningar som "destruktiva".** Gör vanlig `git merge origin/development` och lös konflikter per fil.
- **Migrationer mot development före main stoppar nattspeglingen** (schemakontroll). Kör samma migration mot main samma dag, eller räkna med att speglingen pausar.
- **Radnivåsäkerhet utan policy döljer rader för `snajp_app` utan fel** (så hittades `mirror_meta`). Kolla `pg_policy` när en tabell "är tom" för appen.
- **Python-heredocs i bash förstör `\b` och `\n`** i regex/strängar som skrivs till filer — använd Edit/Write för kod med escapes.
- **Designkroken nekar skalskrivning (sed, heredoc) i UI-filer** när sessionen är armad — använd Edit/Write.
- **gemini-2.5-flash räknar tänkandet mot `max_tokens`**: under ~4000 klipps JSON-svaret.
- **Testsviten är hermetisk via tomma env-flaggor** (`LEADS_DIREKTHAMTNING`, `LEADS_WEBBREVISION` m.fl. i `tests/conftest.py`); en ny nätverksväg behöver en ny flagga där.
- **Git Bash översätter `/demo` till en Windows-sökväg** i argument — `MSYS_NO_PATHCONV=1`.

## 5. Antons instruktioner ordagrant

> Kör /standup för kontext om föregående session.

> Detta är de nuvarande problemen: Scrape-graphen anropen stack iväg markant efter merinfo-implementationen, detta måste begränsas på ett smart sätt utan att tumma på retrieval-kvaliteten. Översikten ser väldigt tråkig och billig ut med intetsägande datapunkter. Jag vill att du tar inspiration från Upsales för att bygga en tilltalande dashboard för översikten som man faktiskt vill kolla på eftersom det är det första kunden ser. Sidorna i övrigt är bra designmässigt, men layouten och fördelningen är fortfarande skev. Att göra är en ända oändlig scroll förbi fullständiga listor som bör visa endast prioriterade eller kunna expanderas, innan Leads-inkorgen visas som faktiskt hade förtjänat en egen flik, samma med utkast. Egentligen bör det dyka upp som underflikar under leads när man klickar där, istället för de nuvarande flikarna Tabell och Pipeline som båda bör bakas in på ett smart sätt i den ordinarie Iris-leads-fliken och då menar jag inte att dela upp dem på den sidan, utan att visa alla datapunkter på ett smart sätt, en enkel statusmarkering skulle ersätta alla leads, samt att låta leadsen ta upp den fulla bredden av ytan istället för att låta "Välj ett lead i listan" ta upp halva. En flik som faktiskt behövs är Körningar, där man kan bevaka pågående Iris-körningar, som det fortfarande inte finns något sätt att se. En annan sak är att Alla mejl "eskalerats" till Alunix trots att inget gällde ett ärende som var relevant för någon av tjänsterna. De nya Jev/Merinfo- leadsen var väldigt relevanta och bra motiverade, med några undantag där Ostia är ett stort, internationellt företag med en relativt enkel men professionell sida, möjligtvis med kontor i Göteborg men utanför Alunix målgrupp. Påståendena om Vicht och Torbens stämde helt, samt Byggarna Berggren som är ett exempel på en verkligt dålig/gammal sida. Ställningskompaniet är ett gränsfall, sidan är inte katastrof men det kan vara värt att höra av sig. Björkeskärs bygg har däremot en bra sida för referens, även Eustaff (genererades innan ändringarna), som har en verkligt professionell sida med scrollanimationer och rörliga element på sidan. Sedan motsade sig även agenten i flera bedömningar där den i flera fall dömde bort kanditater utan sida som utanför Alunix målgrupp medan den satte en stark score på andra utan. Jag vet att jag i senaste sessionen sa att Iris-körningar endast är kvalificerade med en hemsida, men detta lämnar pengar på bordet för Alunix som borde nå ut till dessa själv, å andra sidan skulle det gå att göra via att de resultaten utan sidor hamnar i listorna istället utan lika kvalificeread information, där det går att skapa utkast till dessa senare med mer generella erbjudanden. Scrapegraphs LLM- drivna sökningar kan utvärdera semantik och DOM-struktur på sidor, testa ge den tydligare instruktioner för att bedöma sidorna korrekt, såsom: "Evaluate the website's structure. Is the navigation menu clear? Is the hero section visually modern? Does it use modern flexbox/grid layouts or outdated tables? Does it have animations? List the top 3 visual design flaws.", med dina förslag. Jag undersökte även möjligheten att använda sig av en alternativ tjänst för att spara på onödiga scrapegraph-anrop, men jag vet inte hur stor den faktiska kostnadsskillnaden blir, men detta antyder att den mer pålitligt skulle kunna hämta information från sidor som den idag misslyckas med, berätta gärna din bedömning. Var noga med att få med allt och skapa en detaljerad plan för att lösa varenda punkt.

> Kör alternativet, telefonnummer om VD:n är den enda.

> Pusha över allt till development, se till att det går ihop fint med Sebbes ändringar som pushas samtidigt och att våra ändringar prioriteras

> Nej, jag vill att du gör det och se till att det blir rätt gjort, så att alla våra ändringar överlever

> Se även till att det går att flytta över körningar från development till main nu

> Kör /conclude

---

## 6. Tillägg 2026-10-05 kväll — paus/avbryt, deploysäkra körningar, parallella körningar

Senare session samma dag. Avsnitt 1–5 ovan står orörda; det här gäller ovanpå dem.

### 6.1 Läget, verifierat

- **Git:** `development` = `origin/development` = `266aeca` (tre nya commits ovanpå `df81313`). Antons ocommittade filer orörda (samma lista som i 1).
- **Railway development:** `api` och `web` deployade `e318cad` med SUCCESS; `7224491` och `266aeca` pushade efter det (Railway deployar själv). Ingen migration behövdes: `updated_at` och `korning` finns sedan 080.
- **#31 innehåller detta:** PR:n pekar på grenen `development` och har nu 27 commits, sista `266aeca` (kontrollerat med `gh pr view 31`). En merge av #31 tar alltså med paus/avbryt och deployfixarna till main. Ingen migration behövs före.
- **Sviten:** 2 567 gröna, 4 skippade (full körning efter pushen).
- **Anton har testat skarpt i development:** avbryt fungerar på en pågående körning.

### 6.2 Vad som byggdes

| Vad | Commit | Verifiering |
|---|---|---|
| Paus/återuppta/avbryt Iris-körningar: `POST /api/leads/korningar/{id}/pausa\|aterupta\|avbryt`; `korning.styrning` skrivs atomiskt av `set_korning_styrning` (base/memory/postgres) och bevaras när motorn skriver om hela tillståndet. Paus köar inga nya prospekt; avbrott låter köade barn hoppa över researchen (`AVBRUTEN_KORNING`, räknas inte som undersökta) och avslutar med `slut_orsak="avbruten"` | `e318cad` | `tests/test_korning_styrning.py` (7 tester); Antons skarpa avbrott |
| **Deployfix 1, städaren:** `stada_hangande_leadsjobb` mäter `updated_at` (tystnad), inte `created_at` (ålder), och rör aldrig `styrning='paus'`. Tidigare fälldes varje Iris-körning äldre än 60 min, även friska | `e318cad` | `test_stadaren_mater_tystnad_inte_alder`; `tests/leads/test_stadare.py` uppdaterad |
| **Deployfix 2, hjärtslag:** `ChattStrom._hjartslag` gör `XCLAIM ... JUSTID` var 20:e s medan hanteraren kör. Utan det mättes `MIN_IDLE_MS` från leveransen, och en research över 60 s togs över av den nya containern under deployöverlappet och kördes två gånger | `e318cad` | `test_hjartslaget_hindrar_overtag`, falsifierat (failar med hjärtslaget avslaget) |
| **Deployfix 3, räkningen:** `_rapportera_till_korning` är idempotent per `job_id` (`korning.rapporterade`); inget rapporteras vid processdöd (CancelledError) | `e318cad` | `test_dubbel_rapport_raknas_en_gang` |
| **Deployfix 4, stillastående körning:** barnet rapporteras till körningen FÖRE sin egen completed-rad, sedan väcks motorn (`_vacka_korning`); ett återtaget barn som redan står completed väcker körningen i `hantera_leads_jobb` | `e318cad` | `test_atertaget_completed_barn_vacker_korningen` |
| UI: Pausa/Återuppta + Avbryt körningen (bekräftelse) i panelen för pågående körning i `IrisKorningar.tsx`; status "Pausad"/"Avbryts" i tabellen; slutorsak "Avbruten" | `e318cad` | renderat på stubbad förhandsvisning, 800 px och 375 px, inga konsolfel |
| Avbryt-knappen röd: `!text-danger` (husets `cn()` slår inte ihop klasser, så `btnSecondary`:s `text-ink` vann) | `7224491` | skärmbild |
| Körformuläret (`LeadsRunForm.tsx`) släpper knappen när körningen är överlämnad till servern; en ny körning tar över statusraden, den äldre följ-loopen tystnar (`foljer`-ref). Servern hindrade aldrig parallella körningar | `266aeca` | stubbad förhandsvisning: två körningar i rad, knappen aktiv igen efter ~3 s |

### 6.3 Vad som återstår (utöver 3 ovan)

1. **Två skarpa körningar parallellt i development** är inte provat; bara stubbat. Med `leads_workers=1` turas de om, så var och en tar längre tid.
2. **Knappen står fortfarande i "Startar…" under sökfasen** (1–3 min innan researchen börjar). Liten följdändring om Anton vill starta flera även då.
3. **"Researchar" bryts mitt i ordet** i Nyckeltal-panelen vid smal bredd (fanns före, ej åtgärdat).
4. **Inkorgspollern i development** kan inte dekryptera inkorgshemligheterna för `snajpsupport@gmail.com` och `o.anton.lundin@gmail.com` med nuvarande `INTEGRATION_NYCKEL` (syns i api-loggen vid uppstart). Orelaterat till detta, inte undersökt.
5. **Listjobb (`scope='lista'`) går inte att pausa/avbryta**: de saknar motortillstånd. Endpointen svarar 409.
6. **Paus stoppar inte köade barn**, bara nya. Med en körning ur en lista (`kalla='lista'`, alla barn köas direkt) gör paus därför lite; avbryt fungerar.

### 6.4 Fällor (nya)

- **`npx prettier` installerar en främmande prettier** (repot har ingen konfig) och formaterar om hela filen. Använd inte; formatera för hand.
- **`.next/dev/types/validator.ts` minns raderade sidor** och ger ett tsc-fel tills nästa `next dev`/build. Ofarligt.
- **Git Bash saknades tillfälligt** (`usr\bin\bash.exe` borta) mitt i sessionen; Anton uppdaterade. PowerShell-`git` gav då "fork bomb".
- **Förhandsvisning utan kunddata:** en okommitterad `app/forhandsvisning/<namn>/page.tsx` som stubbar `window.fetch` räcker för att se körningsytorna; ta bort den efteråt.

### 6.5 Antons instruktioner ordagrant

> Innan du gör något annat, lägg till en funktion för att pausa samt avbryta pågående leads-körningar.

> Innan du pushar, undersök om pågående körningar dör vid ny push och deploy på Railway

> Gör alla fixarna och fixa sedan UI:n för att manuellt kunna avbryta och pausa pågående körningar. Git bash är updaterat nu

> Pusha ändringarna så vi kan pausa den pågående körningen innan de drar mer

> Det går att avbryta pågående körningar, men jag kunde bara testa en åt gången eftersom det inte går att starta en ny körning under en pågående

> Okej, updatera senaste agentens handoff med dina ändringar, utan att ta bort något.
