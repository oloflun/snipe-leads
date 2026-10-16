# Utkastkedjan: referens för Iris första mejl (låst 2026-10-12)

> Antons ord 2026-10-12: "Alla utkast är perfekta nu, lås in detta." Det här
> dokumentet är den exakta beskrivningen av kedjan, strukturen och vad som
> ändrades för att komma hit. Facitet i kod är
> `snajp-support/tests/leads/fixtures/utkastfacit_2026-10-12.json`, låst av
> INV-LEADS-UTKAST-001 (`tests/leads/test_utkastfacit_2026_10_12.py`).
> Förbättra utkasten vidare enligt avsnitt 7, aldrig genom att ändra facitet
> först.

## 1. Vad ett perfekt utkast är

Tre korta stycken efter hälsningen, 50–110 ord, i den här ordningen.

| Stycke | Vad det gör | Exempel (Tingstad Måleri, gratisprov Iris) |
|---|---|---|
| **Ingången** (1 mening, högst 2) | Skriven **till** mottagaren i andra person ("ni/er/era", eller "du/din" till en namngiven person), byggd på **en konkret detalj ur bolagets egna sajt** (vem de arbetar för, vad de lägger vikt vid, hur de arbetar), och avslutad i **det moment den valda produkten löser**, sagt som något som får vänta eller tar tid hos dem. | "Era uppdrag, som sträcker sig från villor till stora fastighets- och nybyggnadsprojekt, ofta åt kommuner och byggentreprenörer, gör att det är en utmaning att hinna hitta nya som matchar er verksamhet." |
| **Erbjudandet** (2–3 meningar) | "Vår [agent] [gör X] åt er." följt av **villkorens innehåll och siffror ordagrant i sak**: vad de får, utan kostnad / garantin / pilotpriset. Inget utöver villkoren. | "Vår agent Iris hittar dem åt er. Ni får fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till var och en, helt utan kostnad och utan att det binder er till något." |
| **Handlingen** (1 mening) | **Villkorens handling**, så enkel att det kostar mindre att svara ja än att låta bli. Aldrig en fråga. | "Svara "ja" på mejlet, så skickar vi de fem inom två arbetsdagar." |

Ämnesraden är två till fem ord om deras löfte eller momentet, **utan bolagets
namn och utan vår produkt** (Anton 2026-10-15; före dess bar den namnet).
**Nivån sedan 2026-10-15 är Båtladan** ("Hur hinner du med att ge personlig
rådgivning och service genom hela processen, från köp till underhåll, när
kundfrågorna om båtar, motorer och trailers blir många?"): ingången tar det
bolaget lovar sina kunder och ställer det mot momentet, aldrig en uppräkning av
sortimentet och aldrig "Med er/ert/era …", "När ni …" eller "Ni som …". Hälsningen, signaturen och
den lagstadgade foten läggs på i kod (`app/leads/halsning.py`,
`app/leads/signatur.py`, `app/leads/utskicksfot.py`); modellen skriver dem
aldrig.

### Fel och rätt i ingången (verkliga utkast)

| Fel: allmän mening om branschen med en etikett på | Rätt: skriven till dem ur deras egna ord |
|---|---|
| "För företag som ert, som säljer till andra företag, är det ofta en utmaning att hitta nya kunder." | "Att hitta nya företagsuppdrag i Göteborg, parallellt med villor och fastighetsprojekt, är ofta en tidstjuv." |
| "När man arbetar med markarbeten och grundläggningar, som ni gör, kommer många förfrågningar …" | "Era projekt inom markarbeten, grundläggningar och enskilda avlopp för både företag och privatpersoner i Sundsvall genererar många förfrågningar som kan vara svåra att hinna med när ni är ute på jobb." |
| "Med 20–25 anställda och fem platschefer vet jag att fokus ligger på kvalitet." | "Med ert fokus på nära relationer med beställare och fastighetsägare, och ert arbete med totalentreprenad för fastighetsägare, brf:er och allmännyttan, hur hinner ni då hitta nya företagsuppdrag som matchar er verksamhet?" |

Det som skiljer: rätt-kolumnen kunde inte stå i ett mejl till något annat
bolag, den innehåller inga siffror ur registret, inget "man"/"den som", ingen
etikett ("som ni gör", "som ert", "liksom ni") och inget antagande ("vet jag
att", "kan jag tänka mig", "är jag säker på").

## 2. Kedjan, steg för steg

Allt i `app/agent/leads_research_v2.py:run_outreach_draft_v2`. Varje LLM-steg
bär Iris grundprompt (`agent-core/prompts/leads-systemprompt.md`), skrivstilen
(`agent-core/prompts/leads-skrivstil.md`), de hårda reglerna
(`agent-core/overlays/leads-hard-rules.md`) och kundens instruktioner.

| # | Steg | Vad som skickas in | Vad som händer |
|---|---|---|---|
| 0 | **Ärendet byggs** | Uppdrag, skrivregler, skrivstil, brief, erbjudandet som styr vinkeln, **erbjudandeblocket** (katalogavsnitt + kundens villkor för den valda produkten, `app/leads/erbjudanden.py`), **ingångens form för just det här mejlet** (`_ingangsform`, fem former roterade på prospekt-id), **ingångar som redan används i körningen** (ur granskningskön), språkläge, kontextpaket, SOUL, researchvyn (`_utkastens_researchvy`: mottagare, vald produkt, citat, lägesbeskrivning, trigger, bolagsbild, varför bolaget valdes). | — |
| 1 | **Utkastet** (`sa:draft-outreach` + skopad `mk:cold-email`, temperatur 0,5) | Ärendet + `_UTKAST_V2_UPPGIFT`: skriv, skärp personaliseringen, granska mot checklistan, allt i ett svar. | JSON med subject, body m.m. Tom body ger ett omförsök. |
| 1a | **Personalisera ingången** (samma steg, `_INGANGSUPPGIFT`), **alltid** | Ärendet + utkastet. Skriv om **enbart** första stycket: andra person, en detalj ur citaten, slutar i momentet, inga etiketter, högst 30 ord; resten ordagrant kvar. | Nytt subject/body. Det är den extra Personalisera-rundan som hjälpte i granskningen, inbyggd. |
| 1b | **Stilgrinden** (`app/leads/stilkontroll.py`, kod) | Råutkastet, villkoren, produkten, körningens andra utkast. | Fynd: mallingång, generell ingång, registerfakta, antaganden, "jag ser att", "vi har skapat", effektivisera, utropstecken, tankstreck, superlativ, slutar med fråga, över 90 ord, kolonlista, tappat erbjudande (villkorens siffror, produktens stam), samma ingång eller konstruktion som ett annat mejl. Fälls något: **en** omskrivning av hela utkastet med fynden utpekade (`lang_mening` och `samma_uppmaning` undantagna, villkoren dikterar dem). |
| 2 | **Humanizern** (`snajp:humanizer-svenska`, temperatur 0,7), **alltid sist** (INV-LANG-002) | Minimal bas: uppdrag, språkläge, skrivstil, erbjudandeblock, och en rad om att ingången är i andra person och inte får bli allmän. | final_subject, final_body. |
| 2b | **Grinden igen efter humanizern** (sedan 2026-10-15) | Det humaniserade utkastet. | Samma fynd som 1b plus ämnesraden. Kvarstår något: omskrivning och ny humanisering, högst två varv. Humanizern är fortfarande sist. |
| 3 | **Kodens efterarbete** | `sign_off`, `ratta_tilltal` (hälsningen avgörs i kod), `ett_bolagsnamn` (namnet en gång, kortnamn). | — |
| 4 | **Faktagrinden** (`_run_grounding_cycle`, INV-GROUND-001) | Tillåtna fakta: kontextpaket, researchcitat, erbjudandet + villkoren, brief. | Ostött påstående eller gissningsord → reparation + deltahumanisering, en runda; annars stoppas utkastet före kön. |
| 5 | **Köningen** (`leads_tools._queue_outreach_draft_impl`) | Platshållare, textkvalitet, hälsningsnormalisering, stilkontrollen igen (flaggar bara, skälet på köposten), signatur, fot, språkgrind. | `awaiting_review`. Inget skickas utan en människas godkännande. |

Researchen före kedjan (`_research_v2`) ger citaten, mottagaren, lägesbeskrivningen och den valda produkten. Produkten väljs av modellen ur kundens produktlista; lämnar den fältet tomt härleds produkten ur ett uppfyllt produktbundet kriterium (`bedomning.produkt_ur_kriterierna`), och ett kriterium bundet till en annan produkt än den valda gäller inte leadet.

**Modellen (sedan 2026-10-15/16):** utkast- och humanizerstegen kör
`gemini-2.5-pro` i Vertex `europe-west1` (`LEADS_DRAFT_MODEL`,
`LEADS_HUMANIZER_MODEL` på api i development), med lite tänkande
(`reasoning_effort="low"`; pro tål inte tankebudget 0). Flash föll tillbaka i
mallorden även efter två grindvarv; pro skrev ingångar på den nivå Anton bad
om. Ett utkast tar 5–8 minuter med pro.

## 3. Prompterna, exakt var reglerna står

| Fil | Bär |
|---|---|
| `agent-core/prompts/leads-skrivstil.md` | HUR mejlet formuleras: kärnan, kritiska regler 1–8, strukturen (ingång/erbjudande/handling), tabellen fel/rätt, ordval, meningsbyggnad, ton, ämnesraden, gränserna, före/efter, feedbackrundor 1–5. |
| `agent-core/prompts/leads-systemprompt.md` § 10 | VAD mejlet får säga: skrivregler, grundmallen (ordningen, inte orden), observationen. |
| `agent-core/prompts/leads-erbjudanden.md` + kundens villkor | Erbjudandet: tre kärnerbjudanden (gratisprov, garanti, pilot), villkoren per produkt är det enda mejlet lovar. |
| `agent-core/overlays/leads-hard-rules.md` | Ren text, språkläge, felfri svenska, hälsningsraden, de fyra tonförbuden, evidens före antagande. |
| `app/agent/leads_research_v2.py` | `_UTKAST_V2_UPPGIFT`, `_INGANGSUPPGIFT`, `_INGANGSFORMER`, uppdragets skrivregler i `base`. |

## 4. Vad som ändrades för att komma hit (2026-10-12)

Utgångsläget (natten): första utkastet rabblade registerfakta ("Med fem
platschefer … är jag säker på att") eller öppnade som en mall ("För företag
som ert, som …"). Personalisera i granskningen gjorde det personligare men
tappade erbjudandet; Förbättra blev opersonligt; en andra Personalisera
landade. Beställningen: det första utkastet ska landa där.

| Commit | Ändring | Varför |
|---|---|---|
| `931258a` | Mallfraserna bort ur skrivstilen och grundmallen; stilgrind med mallingång, registerfakta, antaganden, tappat erbjudande, samma konstruktion; omskrivning före humanizern; körningens använda ingångar i ärendet; Tillbaka till Iris utan omskrivning; listtaken borta. | Prompterna föreslog själva "För företag som ert inom …" som ingång, och modellen tog orden. |
| `33282df`, `7455fa4` | Produktbundna profilkriterier gäller bara den valda produkten; produkten härleds ur ett uppfyllt kriterium. | Profilen kompilerades om till tre måste-kriterier, ett per produkt; 80 av 100 föll. |
| `897e3d7` | Ingångsform tilldelad per mejl. | 45 av 62 började "När man …": parallella jobb ser inte varandras utkast. |
| `dda1531` | **Ingången skrivs till mottagaren.** Grinden fäller etiketter var de än står ("som ni gör", "som ert", "liksom ni") och allmänna ingångar ("man", "den som", "ett företag som"); obligatoriskt personaliseringssteg för ingången; formerna i andra person; tabellen fel/rätt. | Anton: "som ni gör"/"som ert" stod kvar i nästan alla; modellen skrev en allmän mening och hängde på etiketten. |
| `c5946e4` | Utkastsvepet byter en föråldrad signatur ("Snajp AB" → "Snajp Sverige"). | Signaturen ska vara "Snajp Sverige". |
| denna | Facit i fixtur, INV-LEADS-UTKAST-001, kolon i "brf:er" är ingen uppräkning. | Låsa in. |
| 2026-10-15 | Ingången bygger på deras löfte; stilgrinden fäller slentrianöppning, uppräkning, lånade exempelord, du och ni, agenten efter löftet, och namn, produkt eller samma början i ämnesraden; namnet lyfts ur ämnet i kod; förnamnet väljs mot adressen; facit reviderat (Båtladan in, sex ut). | Anton: "med er/ert/era, när ni, … en generisk upprabbling", "pinsamma ämnesrader", "Hej Delsbo". |

Uppmätt efter sista omgången: 76 av 80 omkörbara leads med nya utkast, noll
ingångar med etikett eller "man", ingångarnas form fördelad över "Med er …",
"Att hitta …", "Hur hinner ni …", "Era projekt/kunder …", "Ni …".

## 5. Facitet

Tolv utkast ur granskningskön, med erbjudande, produkt och villkor, i
`snajp-support/tests/leads/fixtures/utkastfacit_2026-10-12.json`:
BizBitz Technologies, Eketräs Trafikskola, Fiskebäck Byggservice, Härlanda
Fog & Byggservice, Preparatus, Sorelle, Stenstaden Mark och Entreprenad,
Stöcke Svets, Svensk Rivtjänst, Tingstad Måleri, Witekk Sverige, ÅW
Hemprodukter. De täcker alla tre erbjudandena och alla tre produkterna.
Hälsningsraden är normaliserad till "Hej," (förnamn sätts i kod), signatur
och fot är borttagna.

Testet kräver att varje facitutkast passerar stilgrinden utan andra fynd än
`lang_mening`, `samma_uppmaning` och `for_langt` (villkoren själva orsakar
dem), har erbjudandets siffror och produkt kvar, ingången i andra person utan
"man", slutar med en handling, att facitutkasten börjar olika, och att de fyra
utpekade felen fortfarande fälls.

## 6. Så verifierar du att kedjan håller

```bash
cd snajp-support && python -m pytest -q tests/leads/test_utkastfacit_2026_10_12.py tests/leads/test_stilkontroll_2026_10_12.py tests/agent/test_leads_v2_wiring.py
```

```bash
python scripts/granska_utkast.py --slug snajp --visa 5
```

`granska_utkast.py` kör samma stilgrind på kundens väntande utkast i
development och visar fynd per utkast, ingången och ordantalet. Noll
`mall_ingang`, `generell_ingang`, `registerfakta_i_ingangen`,
`antagande_om_dem`, `erbjudande_*` är målet; `samma_uppmaning` och
`lang_mening` är förväntade på villkorsstyrda mejl.

## 7. Så förbättrar du utkasten vidare utan att tappa det här

1. Skriv ned vad som är fel som en **ny feedbackrunda** i
   `leads-skrivstil.md`, med verkliga exempel (fel/rätt).
2. Ändra regeln i prompten **och** lägg till ett fynd i stilgrinden när felet
   går att känna igen i kod. En regel som bara står i en prompt är en
   riktning, inte en garanti (bevisat fyra gånger den här dagen).
3. Kör testerna i avsnitt 6. Fäller facitet den nya regeln: regeln är fel,
   eller så ska Anton godkänna ett nytt facit. Facitet ändras aldrig tyst.
4. Prova på fem leads (`scripts/omskriv_utkast.py --slug snajp --prospekt …
   --apply`), läs dem själv, kör `granska_utkast.py`.
5. Först därefter hela körningen. Skapa om researchar om och kan tappa ett
   lead som passerade förut; kör bara om det som behöver skrivas om.
6. Dokumentera i `docs/BESLUT.md` med resonemanget.
