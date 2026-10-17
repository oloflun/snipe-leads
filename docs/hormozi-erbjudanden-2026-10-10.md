# Hormozis erbjudandeverktyg, omsatta för Snajps kallmejl

Research 2026-10-10. Källor: Antons kunskapsvalv (`OneDrive/Dokument/Obsidian/Knowledge Base/`) och repot `snipe-leads` på grenen `development`.
Hormozi-materialet är läst i sin helhet där det spelar roll. Det gäller hela $100M Offers (råtranskripten, del 1–7, inklusive helavsnittens transkript för garanti-, brådske- och namngivningskapitlen), $100M Leads (wikisidan plus råtranskriptet för kall outreach) och $100M Money Models del 2–3. Till det kommer de erbjudanderelevanta avsnitten i 22 andra Hormozi-källsidor och säljdomänens §1.13–1.16 och §2.

Märkning:
- **[finns i dag]**: står redan i kod, prislista eller kundvända villkor (källan anges).
- **[nytt förslag – kräver Antons beslut]**: finns inte och får inte skrivas i ett mejl förrän det är beslutat.

---

## 0. Vad Snajp faktiskt erbjuder i dag (underlaget för allt nedan)

| Sak | Läge | Var det står |
|---|---|---|
| Tre agenter: **Iris** (leads), **Supportagenten** (kundtjänst), **Kvittohanteraren** (kvitton/bokföring) | finns | `lib/pricing.ts`, `scripts/snajp_malgrupp.py` |
| Priser (alla med "från"): Support 3 990, Leads 4 490, Kvitton 2 690, Duo 6 990, Trio 9 990 kr/mån + 1 590 kr startavgift; extra prospekt 9 kr, extra mejl 3 kr | finns, utlovade (förbehållet om preliminära priser är bortplockat) | `lib/pricing.ts`, GOALS.md |
| Leads-paketet: ICP-konfiguration, 150 prospekt + 300 mejl/mån, granskningskö | finns, utlovat | `lib/pricing.ts` |
| Kampanjrad: extra Kvittohanterare för 999 kr | finns i prislistans kort | `lib/pricing.ts` (`EXTRA_BOKFORINGSAGENT_PRIS`) |
| **Två månader gratis**, inga betalningsuppgifter vid registrering, faktura först efter gratisperioden, aldrig automatisk kortdragning, påminnelse 7 dagar och 1 dag före slut | finns i onboardingen ("Testa gratis i 2 månader"), på ångerrättssidan och i koden (`workspaces.trial_slut`, migration 074, `trial_paminnare.py`) | `components/auth/OnboardingWizard.tsx`, `app/angerratt/AngerrattSida.tsx` |
| **Motsägelse:** FAQ:n och supportchattens kunskapsbas säger att provperiodens villkor *inte* är fastställda och eskalerar frågan. Vad som händer när provperioden tar slut (konvertering) är inte beslutat | öppet | `lib/faq.ts` (`gratis-period`), `snajp_kb.py`, HANDOFF-2026-10-03-TEXTKVALITET |
| Ingen bindningstid (0 mån) | finns | `lib/pricing.ts`, ångerrättssidan |
| Testa alla tre agenterna i webbläsaren utan konto, med exempeldata | finns | `lib/faq.ts`, `snajp_kb.py` |
| Demo 15–20 min på kundens egna ärenden, "vi säger rakt ut om vi tror att det passar" | finns | `snajp_kb.py` |
| Utkastläge: agenten skriver förslag i några dagar och kunden rättar innan något går ut | finns (beskrivet i KB) | `snajp_kb.py` |
| Inget leadsmejl skickas utan att människa godkänt (granskningskö) | finns | prislistan, leadsflödet |
| Supportagenten lämnar över till människa i stället för att gissa | finns | GOALS.md delmål 1 |
| Faktakontroll: Iris kan inte skriva en siffra, ett belopp eller en kund som inte står i underlaget | finns | `grounding_gate.py` |
| Kvittohanteraren: läsbehörighet till Gmail/Outlook/Hotmail, belopp/moms/datum/kategori, dubblettkontroll, SIE4, BAS-förslag | finns | `lib/pricing.ts`, `snajp_malgrupp.py` |
| Export av data inom 14 dagar och radering 30 dagar efter avslut | finns (pilotavtalet) | `docs/pilotavtal.md` |
| **Garanti (pengarna tillbaka, resultatgaranti osv.)** | **finns inte** | – |
| **Bevis och kundcase** | **finns inte för leads.** Livrustning AB är första riktiga kund och kör bara chatten. Inget leadsmejl har ännu gått ut till något lead (HANDOFF-2026-10-09 §3.2) | – |
| Snajps nuvarande CTA i sina egna Iris-utkast: kort demo i veckan, "jag visar hur det skulle se ut för just [företag], så får du själv avgöra" | finns | `scripts/snajp_malgrupp.py` |
| Målsegment: utbildningsföretag, konsultbolag; förslag: fastighetsservice, IT-konsulter, grossister, redovisningsbyråer | finns (de fyra sista som förslag) | `scripts/snajp_malgrupp.py` |

**Följd för allt nedan:** Snajp har ingen bevisbank än. Hormozis starkaste hävstång just nu är därför inte bevis. Det är **riskomvändning och gratis-först-leverans**, och de två bitarna finns delvis redan.

---

## 1. Hormozis offer-verktyg, ett avsnitt per tips

Förkortningar för källor:
- **OFF-wiki** = `wiki/sources/2026-03-26-the-game-hormozi-100m-offers-audiobook.md`
- **OFF-n** = `Snipd/Data/The Game with Alex Hormozi/$100M Offers Audiobook Part n.md`
- **LEADS-wiki** = `wiki/sources/2026-10-08-the-game-hormozi-100m-leads-book.md`
- **LEADS-5** = `Snipd/Data/The Game with Alex Hormozi/Part 5_ Cold Outreach _ $100M Leads Book.md`
- **MM-wiki** = `wiki/sources/2025-08-19-the-game-hormozi-100m-money-models-audiobook.md`
- **MM-3** = `Snipd/Data/The Game with Alex Hormozi/Part 3_ Attraction Offers _ $100M Money Models Audiobook.md`

### A. Värde och pris

#### 1. Grand Slam-erbjudandet: så bra att ett nej känns dumt
**Kärna:** Erbjudandet är startpunkten för varje affär. Gör det så bra att mottagaren skulle känna sig dum om hen tackade nej. Erbjudandets *konstruktion* kan ge mångdubbelt resultat på samma annonsbudget, och Hormozis exempel på ett byte av erbjudande gav 22,4x mer intäkt i förskott.
**Källa:** OFF-1 › §The Sales Lesson That Changed Everything; OFF-2 › §Grand Slam Offer Money Math; OFF-wiki › §Grand Slam-erbjudanden.
**Så för Snajp:**
- Byt CTA:n "kort demo" mot något som *ger* värde innan det kostar något, se avsnitt 27–28. [nytt förslag – kräver Antons beslut]
- Paketera det som redan finns till ett sammanhållet riskfritt erbjudande: två månader gratis + inga kortuppgifter + ingen bindning + inget skickas utan ert ok. [finns i dag, men är spritt över fyra ställen och syns inte i mejlen]

#### 2. Kategori av ett: erbjudandet ska förklara sin egen skillnad
**Kärna:** Ett jämförbart erbjudande pressas mot lägsta pris. Bygg det så att valet står mellan ditt erbjudande och att göra ingenting, inte mellan dig och en billigare konkurrent.
**Källa:** OFF-2 › §Escape the Commodity Trap ("Grand Slam Offers Create A Category Of One", "Make The Offer Explain Its Own Difference").
**Så för Snajp:**
- Jämför aldrig med andra AI-verktyg i mejlet. Jämför med kundens nuläge: kvitton i inkorgen, samma kundfrågor varje vecka, nya kunder som ingen hinner leta upp. [finns i dag i skrivstilen, `agent-core/prompts/leads-skrivstil.md`]
- Lyft strukturen som gör Snajp annorlunda: en namngiven agent som gör *en* sak åt er och lämnar över till en människa när den är osäker. [finns i dag]

#### 3. Svältande publik: välj marknaden före erbjudandet
**Kärna:** En svältande publik slår ett perfekt erbjudande. Fyra filter: verklig smärta, köpkraft, lätt att nå och växande marknad. Satsa på en nisch tillräckligt länge för att testa flera erbjudanden innan du skyller på nischen.
**Källa:** OFF-2 › §Why Markets Matter More, §Four Traits of a Good Market, §Commit Harder to a Niche.
**Så för Snajp:**
- Ranka segmenten i `snajp_malgrupp.py` på de fyra filtren och testa varje segment mot samma erbjudande innan det byts. [nytt förslag – kräver Antons beslut, prioriteringen är hans]
- Redovisningsbyråer är "lätta att nå" och har kunder med samma kvittosmärta. Se avsnitt 33 (partner). [förslag finns redan som segment, ej beslutat]

#### 4. Nischa ner: specificitet höjer upplevt värde
**Kärna:** Samma produkt riktad till en smalare avatar upplevs som byggd för just dem, och priset kan stiga kraftigt utan att innehållet ändras. Hormozi smalnade av Gym Launch till mikrogym med ett visst antal medlemmar och sa nej till andra som han också kunde ha hjälpt.
**Källa:** OFF-2 › §Specificity Lets You Charge More; OFF-wiki › §Nischa ner för att höja priset; `wiki/sources/2026-09-03-the-game-hormozi-996-think-like-top-1-percent.md` › §Nischa ner för att höja upplevt värde.
**Så för Snajp:**
- En agent per segment i mejlet, aldrig tre. Iris väljer redan EN produkt per bolag. [finns i dag, `snajp_malgrupp.py`]
- Segmentnamn i erbjudandet: "Kvittohanteraren för byggföretag", "Supportagenten för kursföretag". [nytt förslag – kräver Antons beslut]

#### 5. Värdeglappet: höj värdet, sänk inte priset
**Kärna:** Folk köper när upplevt värde överstiger priset. Öka glappet genom mer värde, inte lägre pris. Att vara näst billigast ger ingen strategisk fördel. Höj priset först när värdet höjts.
**Källa:** OFF-2 › §Charge What the Value Justifies ("Price Matters Less Than Value Discrepancy", "Raise Prices By Increasing Value First"); `wiki/sources/2026-04-23-the-game-hormozi-fix-before-ads.md` › §Sänk inte priset för att bemöta en billigare kopia.
**Så för Snajp:**
- Nämn aldrig rabatt i kallmejl. Nämn det som ingår. [finns i dag i praktiken, men se avsnitt 22]
- Kampanjraden "extra Kvittohanterare för 999 kr" är en rabatt i Hormozis mening. Formulera om den som tillägg till befintlig kund, inte som lockpris i kallmejl. [finns i dag (raden), omformuleringen är nytt förslag]

#### 6. De som betalar mest är mest engagerade
**Kärna:** Ett pris som svider lite får kunden att använda produkten, och det ger bättre resultat och bättre kunder. Ett lågt pris ger kunder som inte gör sin del.
**Källa:** OFF-2 › §Premium Pricing Creates Better Clients.
**Så för Snajp:**
- Två månader gratis riskerar enligt Hormozis logik passiva provkunder. Motvikt: bind gratisperioden till aktivering (kopplad inkorg, godkänt första utkast), se avsnitt 24. [nytt förslag – kräver Antons beslut]

### B. Värdeekvationen

#### 7. Värdeekvationen: fyra hävstänger
**Kärna:** Värde = (drömresultat × upplevd sannolikhet) / (tidsfördröjning × ansträngning). Höj de två övre och pressa de två nedre. De bästa bolagen lägger kraften på nämnaren: omedelbart och utan ansträngning.
**Källa:** OFF-3 › §The Four Drivers of Offer Value; OFF-wiki › §Värdeekvationen.
**Så för Snajp:** varje kallmejl bör träffa minst två hävstänger:
- *Ansträngning:* "ni godkänner, agenten gör jobbet" (granskningskön, utkastläget). [finns i dag]
- *Tidsfördröjning:* första resultatet samma dag eller samma vecka (se avsnitt 10). [finns i dag i KB-texten "dagens arbete, inte månadens"; får bara sägas om det håller]
- *Sannolikhet:* "inget går ut utan att ni sett det" och "agenten hittar inte på" (faktakontrollen). [finns i dag]

#### 8. Drömresultatet är oftast status, sett med andras ögon
**Kärna:** Folk köper status mer än funktion. Beskriv nyttan som hur andra ser köparen efteråt, inte i tekniska termer.
**Källa:** OFF-3 › §Dream Outcomes Are Really Status Plays ("Write Benefits From The Viewpoint Of Others"); `wiki/sources/2025-07-21-the-game-hormozi-12-persuasion-hacks.md` › §Knyt fördelar till status.
**Så för Snajp:**
- Supportagenten: kunden som får svar på söndagskvällen minns företaget. [nytt förslag, formulering]
- Kvittohanteraren: redovisningskonsulten som får allt i ordning och slipper jaga. [nytt förslag, formulering]
- Iris: ägaren som kan ägna sig åt samtalen som blir affärer. [finns i dag i skrivstilens exempel]

#### 9. Upplevd sannolikhet: folk betalar för säkerhet
**Kärna:** Samma leverans är värd mer när köparen är säker på att den fungerar, till exempel genom track record och bevis. Bevis slår löften.
**Källa:** OFF-3 › §Certainty Makes Offers Worth More; `wiki/sources/2024-12-18-hormozi-789-how-to-make-money-so-fast.md` › §Bevis slår löften.
**Så för Snajp:**
- Bevis att använda i dag är det som går att *se själv*: demon i webbläsaren och provmejlet. Inga kundresultat finns att citera. [finns i dag]
- Bygg bevisbanken: de första provkunderna i utbyte mot rätten att beskriva resultatet (avsnitt 30). [nytt förslag – kräver Antons beslut]
- Påhittade eller lånade resultat får aldrig användas, och faktakontrollen fäller dem ändå. [finns i dag]

#### 10. Snabba känslomässiga vinster tidigt
**Kärna:** Kunden köper det långsiktiga resultatet men stannar för de tidiga vinsterna. Lägg en tydlig vinst så nära köpet som möjligt. Hormozi siktade på kundens första försäljning inom sju dagar.
**Källa:** OFF-3 › §Fast Wins Increase Retention.
**Så för Snajp:**
- Definiera "första vinsten" per agent: första godkända Iris-utkastet, första besvarade kundfrågan i utkastläge, första kvittoexporten. Nämn den i mejlet. [nytt förslag – kräver Antons beslut om vad som utlovas]
- Onboardingen mäter tiden till första vinst och ett mejl firar den. [nytt förslag]

#### 11. Det enda som slår gratis är snabbt; minsta möjliga ansträngning
**Kärna:** Köpare betalar för att slippa friktion. Klart-åt-dig slår gör-det-själv.
**Källa:** OFF-3 › §Ease Beats Effort in the Marketplace, §Meditation Loses to Xanax on Value.
**Så för Snajp:**
- Säg uttryckligen vem som gör jobbet: "vi sätter upp kunskapsbasen tillsammans med er" (uppstartsavgiften täcker det). [finns i dag]
- Kvittohanteraren läser inkorgen själv, så kunden behöver inte fota eller ladda upp något. [finns i dag]

#### 12. Upplevelse slår verklighet: psykologiska lösningar
**Kärna:** Det räcker inte att något är snabbare. Det måste *kännas* snabbare. Hormozi hämtar exempel från väntetidskartor och speglar i hissar.
**Källa:** OFF-3 › §Perception Creates Market Value.
**Så för Snajp:**
- Visa i stället för att beskriva: en skärmdump eller ett exempelutkast som bilaga eller länk till demon. [delvis finns (demon), bilaga är nytt förslag]

### C. Bygg erbjudandet

#### 13. Sälj utfallet, inte medlemskapet
**Kärna:** Hormozi slutade sälja gymmedlemskap och sålde i stället ett resultat inom en tidsram. Kunden vill inte ha tillgången, den vill ha utfallet.
**Källa:** OFF-4 › §Sell the Outcome, Not the Membership.
**Så för Snajp:**
- Sälj aldrig "en AI-agent". Sälj "kvittona klara för bokföringen", "svar till era kunder även när ni inte är på plats" och "ett personligt första mejl till rätt företag". [finns i dag i skrivstilsregel 2–3]

#### 14. Problemlistan: före, under, efter → "hur man"-lösningar
**Kärna:** Lista varje hinder kunden möter före, under och efter köpet, i detalj. Vänd sedan varje hinder till en "så här slipper du det"-lösning. Fler hinder ger fler saker att lösa.
**Källa:** OFF-4 › §Map Every Prospect Obstacle, §Turn Problems Into Solution Language.
**Så för Snajp:** typiska hinder hos en småföretagare och Snajps svar:
- "Jag har inte tid att sätta upp det" → vi gör uppsättningen tillsammans. [finns i dag]
- "Den svarar fel och skämmer ut oss" → utkastläge plus överlämning till människa. [finns i dag]
- "Det går iväg mejl jag inte sett" → granskningskön. [finns i dag]
- "Vad händer med vår data?" → läsbehörighet, export inom 14 dagar och radering. [finns i dag]
- "Bindning" → ingen bindningstid. [finns i dag]
- "Det kostar innan jag vet om det funkar" → två månader gratis och faktura i efterhand. [finns i dag]
- Gör listan till en mall som Iris kan välja *ett* hinder ur per mejl. [nytt förslag]

#### 15. Leveranskuben: varierar hur lösningen levereras
**Kärna:** Variera personlig tid (1:1 eller grupp), kundens insats (gör själv, gör tillsammans, gjort åt dig), medium och svarstid. Kontrollfråga: vad skulle jag leverera om kunden betalade tio gånger priset?
**Källa:** OFF-4 › §Brainstorm Delivery Vehicles Creatively.
**Så för Snajp:**
- En "gjort åt er"-start: en person från Snajp sätter upp agenten under ett möte. Det är i praktiken det som sker under demon och vid uppstarten. [finns i dag]
- En dyrare nivå med personlig kontakt (fast kontaktperson, veckogenomgång av Iris-utkasten) för den som vill ha mer. [nytt förslag – kräver Antons beslut]

#### 16. Trimma och stapla
**Kärna:** Stryk de lösningar som kostar mycket och ger lite. Behåll det kunden värderar högt och som är billigt att leverera, gärna verktyg som byggs en gång och delas ut många gånger. Buntat blir erbjudandet svårt att prisjämföra.
**Källa:** OFF-4 › §Trim High-Cost Low-Value Extras, §Stack the Final Grand Slam Bundle.
**Så för Snajp:**
- Stapeln finns redan i prislistans "ingår"-rader. I mejlet räcker de 2–3 rader som träffar mottagarens hinder. [finns i dag]
- **Gör inte** Hormozis dollarvärdering av varje del ("värde 4 351, ditt pris 599"). Det läses som tv-shop i svensk B2B, se avsnitt 3 i varningarna. [ton-råd]

#### 17. Överleverera först, systematisera sedan
**Kärna:** Ett nytt erbjudande ska överleverera, även om det kostar mer i början. Effektivisera leveransen när intäkterna kommer.
**Källa:** OFF-4 › §Overdeliver Before You Optimize.
**Så för Snajp:**
- De första tio kunderna får personlig uppsättning och uppföljning efter en vecka. [nytt förslag – kräver Antons beslut, det kostar tid]

#### 18. Lös varje invändning, och var inte romantisk om lösningen
**Kärna:** Hormozi förlorade affärer på sin egen princip tills han byggde en guide för den invändning som återkom, och den lösningen kunde sedan återanvändas.
**Källa:** OFF-4 › §Solve Every Reason They Hesitate.
**Så för Snajp:**
- Logga varje svar som säger nej eller "inte nu" efter orsak (Iris svarsklassning finns) och bygg ett svar eller en funktion för de tre vanligaste. [delvis finns (svarsklassning), loggning per orsak är nytt förslag]

### D. Förstärkare: knapphet, brådska, bonusar, garantier och namn

#### 19. Knapphet: ärlig kapacitet, aldrig påhittad
**Kärna:** Tre sorters knapphet: begränsat antal, begränsade platser per period och begränsad tillgång till dig. Den enklaste är ärlighet: säg hur många du faktiskt kan ta emot. Sälj hellre slut än överbeställ.
**Källa:** OFF-5 › §Three Practical Scarcity Types, §Ethical Scarcity for Service Businesses, §Honest Scarcity Beats Fake Scarcity; `wiki/sources/2025-11-18-the-game-hormozi-911-generate-1000s-of-leads.md` › §Scarcity ska komma från verklig kapacitet.
**Så för Snajp:**
- Kapaciteten är verkligt begränsad i dag eftersom onboardingen kräver handpåläggning (GOALS.md delmål 14). Ett ärligt tak, till exempel "vi tar in N nya kunder i månaden eftersom vi sätter upp kunskapsbasen tillsammans med var och en", är sant så länge det stämmer. [nytt förslag – kräver Antons beslut om N, och N måste hållas]
- Den som får nej efter att taket nåtts får nej. Annars är taket falskt. [regel]

#### 20. Brådska: tid, inte antal
**Kärna:** Fyra etiska former: rullande kohorter ("nästa start är måndag"), säsong, pris- eller bonusfönster, och möjligheter som blir sämre för varje dag. De flesta köp sker strax före deadline.
**Källa:** OFF-5 › §Urgency Turns Time Into Action, §Rolling Cohorts Close More Sales, §Seasonal and Promotional Deadlines, §Exploding Opportunities Decay Fast.
**Så för Snajp:**
- Säsong som *är* sann: bokslut och momsdeklaration för Kvittohanteraren, terminsstart och kurssäsong för utbildningsföretag, höstens offertsäsong för Iris. [nytt förslag, formulering]
- Kohortstart ("vi startar nya kunder på måndagar") om det blir en verklig rutin. [nytt förslag – kräver Antons beslut]
- **Inte** Hormozis variant "en kund hoppade av, så det finns en plats". Den får bara sägas när den är sann. [varning]

#### 21. Fördröj frågan, sälj färre
**Kärna:** Obesvarad efterfrågan växer, och den som säljer färre platser kan ta mer betalt nästa gång.
**Källa:** OFF-5 › §The Delicate Dance of Desire.
**Så för Snajp:** passar dåligt för kallmejl i dag. Det är ett läge för när efterfrågan finns. [ingen åtgärd nu]

#### 22. Bonusar i stället för rabatt
**Kärna:** En rabatt lär kunden att priset går att pruta på. En bonus vidgar glappet mellan pris och värde utan att röra prisankaret. Verktyg och checklistor är bättre bonusar än mer utbildning, eftersom de sparar tid. Varje bonus ska lösa en bestämd invändning, ha ett namn med nytta i och gärna lösa kundens *nästa* problem.
**Källa:** OFF-6 › §Why Bonuses Beat Discounts, §The Anatomy of Effective Bonuses, §Choosing Bonus Versus Core Offer.
**Så för Snajp:**
- Bonus till Kvittohanteraren: en färdig kategorimall för branschen eller en genomgång med kundens redovisningskonsult. [nytt förslag – kräver Antons beslut]
- Bonus till Supportagenten: Snajp skriver första versionen av kunskapsbasen ur kundens befintliga webbsidor och mejl (KB-skanning finns i koden, `kb_skanning.py`, men är inte utlovad som erbjudande). [nytt förslag – kräver Antons beslut]
- Bonus till Iris: en genomgång av kundens målgrupp (ICP) med en människa. [ICP-konfigurationen finns i dag; att lyfta fram den som bonus är nytt förslag]

#### 23. Bonusen kommer efter frågan, i samtalet
**Kärna:** I ett personligt säljsamtal ställer man frågan först. Säger kunden ja presenteras bonusarna efteråt som en överraskning. Säger kunden nej läggs en bonus till som löser den invändning som kom upp.
**Källa:** OFF-6 › §Using Bonuses in One-on-One Sales.
**Så för Snajp:**
- Håll bonusarna borta från första kallmejlet och använd dem i svaret på en invändning eller i demon. [nytt förslag]

#### 24. Garantier: vänd den exakta rädslan
**Kärna:** Den största invändningen är risk. Det finns fyra typer av garanti: ovillkorad, villkorad, anti-garanti och underförstådd (prestationsbaserad). En garanti ska ha formen "om ni inte får X inom Y gör vi Z". Börja med kundens värsta farhåga. En garanti förstärker en bra produkt men räddar inte en dålig.
**Källa:** OFF-6 › §Guarantees Reverse the Biggest Sales Risk, §Four Guarantee Types Explained, §Design Guarantees Around Buyer Fears.
**Så för Snajp:** de verkliga farhågorna hos en svensk småföretagare är 1) att agenten skickar eller svarar fel i deras namn, 2) bindning, 3) data och 4) att det inte ger något.
- 1–3 är redan omvända: granskningskön och överlämningen, ingen bindning, läsbehörighet och export. Säg det som en garanti, inte som en funktion. [finns i dag, formuleringen är ny]
- 4 är inte omvänd. Se avsnitt 25. [nytt förslag]

#### 25. Villkorad tjänstegaranti, uppskjuten betalning och garanti på första resultatet
**Kärna:** Hormozis favoritgaranti är att fortsätta arbeta utan kostnad tills kunden nått resultatet, villkorat av att kunden gör sin del. Varianter är att kunden inte faktureras igen förrän första resultatet kommit, eller att leverantören bär kostnaden fram till första resultatet. Villkoren ska vara de handlingar som faktiskt leder till resultat.
**Källa:** OFF-6 › §Creative Guarantee Structures That Sell (conditional service, modified service, delayed second payment, first outcome); "Guarantee The Outcome By Extending Service".
**Så för Snajp:**
- "Har Iris inte gett er [N] utkast ni vill skicka när provperioden är slut förlänger vi den med en månad, om ni har godkänt eller rättat utkasten i granskningskön." [nytt förslag – kräver Antons beslut om N och villkor]
- "Första fakturan kommer först när Kvittohanteraren har lämnat sin första SIE4-export till er." Med två månader gratis och faktura i efterhand ligger det redan nära. [nytt förslag – kräver Antons beslut]
- Låt alltid villkoret vara en *handling* (koppla inkorg, godkänna utkast) och aldrig ett affärsutfall som antal möten eller kronor. Snajp kan inte styra det och har inga data att stödja det på. [regel]

#### 26. Underförstådd garanti: prestationsbaserat pris; anti-garanti; stapla och namnge
**Kärna:** Betalt bara vid resultat är en inbyggd garanti, men kräver mätbarhet och förtroende. "Alla köp är slutgiltiga" kan höja värdet när produkten inte går att "ose". Garantier kan staplas och bör få ett eget namn.
**Källa:** OFF-6 › §Four Guarantee Types Explained (implied), §When No Refunds Increase Credibility, §Stacking Guarantees Strengthens Belief.
**Så för Snajp:**
- Prestationspris per *godkänt* utkast eller per bokat möte är tekniskt mätbart (granskningskön, svarsklassningen), men det är en ny prismodell. [nytt förslag – kräver Antons beslut, lågprioriterat]
- Anti-garanti passar inte: Snajp är en löpande tjänst och inte en hemlighet. [avråds]
- Stapla det som finns till en namngiven trygghet, till exempel "Inget-går-ut-utan-er-garantin": inget skickas utan ok, ingen bindning, avslut när som helst och data tillbaka inom 14 dagar. [delarna finns i dag, namnet är nytt förslag]

#### 27. Namnge erbjudandet med MAGIC
**Kärna:** Namnet avgör vem som klickar. MAGIC betyder anledning (Magnet), avatar, mål (Goal), tidsram (Interval) och behållarord (Container), och 3–5 delar räcker. Kort och slagkraftigt vinner. Testa 2–3 namn och gör vinnaren till kontroll. Lägg inte ett kvantifierat utfall inom en tidsram i namnet, eftersom det läses som garanti.
**Källa:** OFF-7 › §The MAGIC Naming Formula, §Rhymes and Alliteration That Stick; `wiki/domains/marketing/mp-sections/04-3-budskap-och-copy.md` › §3.13.
**Så för Snajp:** kandidater att testa i ämnesrad eller CTA:
- "Gratis kvittostart för byggföretag, 2 månader" (anledning: gratis; avatar; tidsram; behållare: start). [nytt förslag]
- "Bokslutsfri höst: Kvittohanteraren i två månader utan kostnad" (säsong som anledning). [nytt förslag]
- "Kundfrågestarten för kursföretag" (avatar plus behållare). [nytt förslag]
- "Tio-bolag-provet: Iris visar vilka som passar er" (för gratis-först-leveransen i avsnitt 28; antalet måste beslutas). [nytt förslag – kräver Antons beslut]
- Inga resultatlöften med siffror i namnet. [regel]

#### 28. Byt omslaget, inte erbjudandet
**Kärna:** När ett erbjudande tröttas ut byter man i ordning: bild, brödtext, rubrik, varaktighet och förstärkare. Intäktsmodellen byts sist. Lokala marknader tröttas ut snabbare.
**Källa:** OFF-7 › §How to Refresh Fatigued Offers; OFF-wiki › §Byt omslaget.
**Så för Snajp:**
- Håll erbjudandet stabilt (provperiod plus agent) och variera ingång, ämnesrad och säsongsanledning mellan körningar. Testa en sak i taget. [nytt förslag]
- Iris återkontaktar samma lista efter 3–6 månader med nytt omslag (avsnitt 31). [nytt förslag]

### E. Kallmejlets erbjudande ($100M Leads)

#### 29. Lead magnet och gratis-först: en komplett lösning på ett smalt problem
**Kärna:** Ge en komplett lösning på ett smalt problem, som i sin tur avslöjar nästa problem, som kärnerbjudandet löser. Det finns tre typer: diagnos som avslöjar ett dolt problem, prov och ett steg i en flerstegsprocess. Kall outreach: byt "boka ett samtal" mot konkret gratisleverans. Det tredubblade take rate hos Hormozi.
**Källa:** LEADS-wiki › §Engagerade leads och lead magnets, §Kall outreach; LEADS-5 › §Give Away Enough Value To Make No Feel Stupid; `wiki/sources/2025-11-18-the-game-hormozi-911-generate-1000s-of-leads.md` › §Mini-erbjudanden, §Fyra lead magnet-typer; `wiki/domains/sales/sp-sections/02-1-prospektering-och-pipeline.md` › §1.15, §1.16.
**Så för Snajp:**
- *Iris-provet:* Iris tar fram ett litet antal bolag som passar mottagaren, med ett färdigt första utkast till vart och ett, innan mottagaren bestämt något. Det är prov och första steg i ett. Kostnaden per prov (merinfo, ScrapeGraph och tokens) måste räknas. [nytt förslag – kräver Antons beslut]
- *Kvittoprovet:* kunden kopplar inkorgen med läsbehörighet och ser vilka kvitton som hittas från förra månaden. [prov på eget konto finns i dag via provperioden; att erbjuda det som ett avgränsat prov i mejlet är nytt förslag]
- *Supportprovet:* skicka in tio vanliga kundfrågor och få agentens svarsförslag tillbaka. [nytt förslag]
- *Inte* en webbplatsdiagnos: webbrevisionen är hemlig enligt projektregeln och får inte bära Snajps egna mejl, och Snajp bygger inte webbplatser. [regel]

#### 30. Gratis för de första, betalt när de börjar rekommendera
**Kärna:** Gratis är den enklaste förstärkaren. De första fem kunderna är förlåtande, lär dig vad som måste fixas och ger omdömen. Börja ta betalt när folk börjar rekommendera, med en pristrappa (stor rabatt för de första fem, mindre för nästa fem).
**Källa:** LEADS-wiki › §Varm outreach; `wiki/domains/sales/sp-sections/02-1-prospektering-och-pipeline.md` › §1.14.
**Så för Snajp:**
- Två månader gratis finns redan för alla. [finns i dag]
- Villkora en förlängd eller utökad gratisperiod för de första kunderna per segment mot att Snajp får beskriva resultatet (namngivet case efter kundens ok). [nytt förslag – kräver Antons beslut]

#### 31. Kall outreach: personalisering, lågstadienivå, flera kanaler, respektera nej, återkontakt
**Kärna:** Personalisera med 1–3 detaljer, skriv enkelt (enklare text gav 50 % fler svar i Hormozis test) och följ upp fler gånger på fler sätt. Sluta direkt när någon ber om det. Återkontakta listan var 3–6 månad, eftersom omständigheterna ändras.
**Källa:** LEADS-5 › §Personalization Gets Cold Outreach In The Door, §Follow Up Persistently But Respect Boundaries, §Revisit Old Leads When Their Timing Changes.
**Så för Snajp:**
- Personaliseringen ligger i *branschingången* och inte i en iakttagelse om dem. Det följer Antons skrivstilsregel 1 och gissningsgrinden. [finns i dag]
- Uppföljningskedjan (mejl 2–N) finns byggd men är inte inkopplad (GOALS.md delmål 12). [delvis finns]
- Återkontakt efter 3–6 månader med nytt omslag. [nytt förslag]
- Avregistrering stoppar allt direkt (suppressions-tabellen och återkopplingsutfallet "Kontakta inte"). [finns i dag]

#### 32. Referrals: lägre löften, fler snabba vinster, och be om dem
**Kärna:** Referrals växer exponentiellt så länge de överstiger churn. Lova lägre och överleverera. Gör de bästa kundernas framgångsbeteenden till villkor i garantin. Be om introduktioner med en belöning åt båda håll.
**Källa:** LEADS-wiki › §Kundreferrals; `wiki/domains/sales/sp-sections/02-1-prospektering-och-pipeline.md` › §1.5.
**Så för Snajp:**
- I kallmejlet: lova *mindre* än man tror (utkast att godkänna, inte "fler kunder"). [finns i dag i praktiken]
- Ett värvningserbjudande till befintliga kunder, till exempel en gratis månad åt båda. [nytt förslag – kräver Antons beslut]

#### 33. Vem har redan mina leads? Partner och affiliates
**Kärna:** Bolag som redan säljer till dina idealkunder kan integrera din lead magnet i sitt erbjudande. Partnerbonusar (andras tjänster i din stapel) höjer värdet och kan ge provision.
**Källa:** LEADS-wiki › §Affiliates och partners; OFF-6 › §Partner Bonuses Create Extra Profit Streams.
**Så för Snajp:**
- Redovisningsbyråer som kanal för Kvittohanteraren: byrån erbjuder sina kunder provet. [segmentet finns som förslag i `snajp_malgrupp.py`; partnerupplägget är nytt förslag – kräver Antons beslut]

### F. Sekvensen och etiken ($100M Money Models)

#### 34. Money model: attraktion → uppsälj → nedsälj → löpande
**Kärna:** Ett erbjudande är en sekvens. Varje steg löser nästa problem kunden upptäcker. Sikta på att kundens första 30 dagar täcker anskaffningskostnaden.
**Källa:** MM-wiki › §Vad är en "money model"?; `wiki/domains/sales/sp-sections/03-2-erbjudande-och-pris-i-affaren.md` › §2.14.
**Så för Snajp:**
- Attraktion: provperioden. Uppsälj: Duo, Trio och extra Kvittohanterare. Löpande: månadsavgiften. [finns i dag]
- **Krock med 30-dagarsregeln:** två gratismånader plus faktura i efterhand gör att CAC täcks tidigast månad 3–4. Anton bör veta det när provperioden används i mejl i stor skala. [observation]

#### 35. "Vinn tillbaka pengarna" och giveaways
**Kärna:** Kunden betalar och får pengarna tillbaka, eller kredit utspridd över tid, om hen gör bestämda handlingar eller når ett mål. Giveaway: en högt värderad huvudvinst, och sedan ett erbjudande till alla som inte vann.
**Källa:** MM-3 › §Maximizing Customer Engagement with Money-Back Offers, §Maximizing Lead Generation through Strategic Giveaways; `wiki/domains/sales/sp-sections/03-2-erbjudande-och-pris-i-affaren.md` › §2.15.
**Så för Snajp:**
- Passar dåligt så länge provperioden redan är gratis. [avråds nu]
- Giveaway med slumpinslag är lotteri enligt svensk lag. Se varningarna. [avråds]

#### 36. Designreglerna: transparens, pengarna tillbaka när kunden ber om det, aldrig hårt sälj
**Kärna:** Var transparent, följ lagen (särskilt kring "gratis"), ge tillbaka pengar när kunden ber om det och sälj aldrig hårt. Hårt sälj är ett tecken på en svag produkt.
**Källa:** MM-wiki › §Designregler.
**Så för Snajp:** stämmer med Snajps grundton och Antons skrivstil. Varje "gratis" i mejlet ska säga vad som händer efteråt. [finns i dag på ångerrättssidan; i mejlen är det nytt förslag]

### G. Copy-verktyg runt erbjudandet (Hormozis avsnitt)

#### 37. Ge varje erbjudande ett "därför"
**Kärna:** En begäran med ett skäl, vilket skäl som helst, får fler ja än en utan. Det är "M" i MAGIC.
**Källa:** `wiki/sources/2025-07-21-the-game-hormozi-12-persuasion-hacks.md` › §Ge varje erbjudande ett "därför"; OFF-7 › §The MAGIC Naming Formula.
**Så för Snajp:** säsong (bokslut, terminsstart) eller "vi startar nya kunder i [månad]", men bara när det är sant. [nytt förslag]

#### 38. Ärliga brister först, fördelen efter "men"
**Kärna:** Den som erkänner sina brister först blir mer trodd. Lägg bristen före "men" och fördelen efter.
**Källa:** `wiki/sources/2025-07-21-the-game-hormozi-12-persuasion-hacks.md` › §Äg dina brister, §Ärliga brister gör påståenden trovärdiga.
**Så för Snajp:** "Den svarar inte på allt, men de återkommande frågorna tar den." Ärligt, och stöds av eskaleringen. [finns i dag (sakläget), formuleringen är ny]

#### 39. Säg vem det inte är för, och avråd (unsell)
**Kärna:** Att välja bort fel kunder drar de rätta närmare. Den som först avråder från det kunden inte behöver blir trodd på resten.
**Källa:** `wiki/sources/2025-07-21-the-game-hormozi-12-persuasion-hacks.md` › §Annonsera till en specifik person; `wiki/sources/2026-10-01-the-game-hormozi-10m-service-business.md` › §Unsell → prescribe → fake choice.
**Så för Snajp:** PS-raden kan säga när det *inte* passar. KB:ns "vi säger rakt ut om vi tror att det passar" stöder det. [finns i dag i KB; PS-bruket är nytt förslag]

#### 40. PS-meningen
**Kärna:** Rubriken och PS:et är de mest lästa delarna. Använd PS:et till ett bortval, till beviset eller till erbjudandet i en mening.
**Källa:** `wiki/sources/2025-07-21-the-game-hormozi-12-persuasion-hacks.md` › §PS-meningen; `wiki/domains/marketing/mp-sections/04-3-budskap-och-copy.md` › §3.12 (där står redan "varje kallmejl i snipe-leads får ett PS").
**Så för Snajp:** lägg riskomvändningen i PS:et ("två månader utan kostnad, inga kortuppgifter"). [nytt förslag; PS-regeln är föreslagen i valvet men inte införd]

#### 41. Sälj vid största bristen
**Kärna:** Rätt erbjudande vid fel tidpunkt är fel erbjudande. Sälj när bristen känns starkast, inte direkt efter att den lugnats.
**Källa:** `wiki/sources/2025-11-18-the-game-hormozi-911-generate-1000s-of-leads.md` › §Sälj vid den djupaste bristen; `wiki/sources/2025-12-04-the-game-hormozi-14-years-in-70-minutes.md` › §Sälj vid största deprivation.
**Så för Snajp:** timing per segment. Kvittohanteraren inför moms- och bokslutsdatum. Supportagenten när ett utbildningsföretag öppnar anmälan. Iris när ett bolag nyss fått en signal (nyanställd säljare, ny filial). [Iris signaldetektion finns i dag; säsongsstyrda körningar är nytt förslag]

#### 42. Hinder före priset och spela ut värsta fallet
**Kärna:** Ta upp hindren (beslutsfattare, tid, "passar inte oss") innan priset kommer på tal, och fråga vad det värsta som kan hända är.
**Källa:** `wiki/sources/2024-09-02-the-game-hormozi-738-best-sales-advice.md` › §Döda hindren innan du ber om pengar, §Spela ut värsta fallet.
**Så för Snajp:** i demon och i svar på invändningar. Det värsta som kan hända under provperioden är att ingenting skickas och att det inte kostar något. [finns i dag (villkoren), manuset är nytt förslag]

---

## 2. Mejlmeningar för de tio starkaste alternativen

Ton enligt Antons beställning och `agent-core/prompts/leads-skrivstil.md`: börja i deras värld, mottagaren eller deras arbete som subjekt, "vår [agent] … så att ni får mer tid till …", en igenkänningsfråga och ingen gissning om dem ("ni brukar …" fälls). Inga siffror utöver de som finns i Snajps villkor. Skrivet i ni-form.

**Tekniskt villkor:** faktakontrollen (`grounding_gate.py`) fäller varje siffra som inte står i underlaget. "Två månader", "inga kortuppgifter" och "ingen bindning" måste alltså stå i Snajps affärskontext eller Iris-instruktion (`scripts/snajp_malgrupp.py`) innan Iris kan skriva dem.

**1. Riskomvändningen som redan finns** (två månader gratis, inga kortuppgifter, ingen bindning, inget går ut utan ok) [finns i dag]
> Ni kan låta Iris arbeta åt er i två månader utan kostnad. Inga kortuppgifter, ingen bindning, och inget mejl går iväg utan att ni själva har godkänt det.

> Vill ni prova Kvittohanteraren på era egna kvitton? De första två månaderna kostar ingenting, och ni kan avsluta när ni vill.

**2. Gratis-först-leverans för Iris** [nytt förslag – kräver Antons beslut]
> För företag som ert inom [bransch] är det sällan affärerna som är svåra. Det är att hinna hitta nästa kund medan man tar hand om de befintliga. Kan det vara så hos er också?

> Om ni vill tar vår Iris fram några företag som passar er, med ett färdigt första mejl till vart och ett. Då ser ni hur det blir innan ni har bestämt någonting.

**3. Gratis-först-leverans för Kvittohanteraren** [prov finns via provperioden; formen är nytt förslag]
> När man driver ett [byggföretag] med ett litet team är det ofta kvittona som blir liggande i inkorgen tills bokföringen ska göras. Kan det bli tidskrävande hos er?

> Vår Kvittohanterare läser er inkorg med läsbehörighet och plockar fram kvittona åt er, så att ni får mer tid till [bygget] i stället för pappersjakt.

**4. Sälj utfallet till en nisch** (supportagenten mot utbildningsföretag) [finns i dag]
> För kursföretag som ert kommer samma frågor om datum, intyg och bokning om och om igen. Känner ni igen er?

> Vår supportagent svarar på de frågorna utifrån det ni redan har skrivit, så att ni får mer tid till kurserna.

**5. Minsta ansträngning: vi gör uppsättningen** [finns i dag]
> Ni behöver inte lära er ett nytt system. Vi sätter upp kunskapsbasen tillsammans med er, och sedan svarar agenten utifrån era egna texter.

**6. Snabb första vinst i utkastläge** [finns i dag som arbetssätt; att lova en tidsram är nytt förslag]
> Ni kan börja med att låta agenten skriva förslag i några dagar och rätta det som blir fel, innan ett enda svar går ut till era kunder.

**7. Ärlig brist först, fördelen efter "men"** [finns i dag]
> Vår supportagent svarar inte på allt, och det är med flit. Den lämnar över till er när den inte säkert vet svaret, men de återkommande frågorna tar den hand om även när ni inte är på plats.

**8. Villkorad tjänstegaranti** [nytt förslag – kräver Antons beslut om antal och villkor]
> Har Iris inte gett er [antal] utkast som ni vill skicka innan provperioden är slut, förlänger vi den utan kostnad.

**9. Ärlig kapacitet eller kohortstart** [nytt förslag – kräver Antons beslut och att det är sant]
> Vi startar nya kunder i små grupper eftersom vi sätter upp kunskapsbasen tillsammans med var och en. Nästa start är [datum], och vill ni vara med då räcker det att svara på det här mejlet.

**10. PS med bortval (unsell plus riskomvändning)** [delvis finns; PS-bruket är nytt förslag]
> PS. Det här passar bäst för företag som får samma frågor om och om igen. Är varje ärende unikt hos er är det kanske inte rätt verktyg, och då säger vi det rakt ut.

> PS. Provperioden är två månader utan kostnad och utan kortuppgifter. Ni bestämmer först när ni har sett hur det fungerar hos er.

*(Statusvinkel, till avsnitt 8, för den som vill ha en elfte:)*
> När en kund mejlar en fråga en söndagskväll och får svar direkt är det ert företag de minns.

---

## 3. Varningar för svensk marknad

Det här är ingen juridisk rådgivning. Delmål 15 i GOALS.md (jurist läser villkoren) bör omfatta även kallmejlens erbjudandeformuleringar.

1. **E-post till enskilda firmor kräver samtycke.** Marknadsföringslagen (MFL 19 §) kräver förhandssamtycke för e-postreklam till fysiska personer, och en enskild näringsidkare är en fysisk person. Juridiska personer (AB, HB) får mejlas, men varje mejl ska ha en giltig adress där mottagaren kan be om att utskicken upphör (MFL 20 §). Leadsregel 15–16 utesluter redan enskilda firmor ur ringlistan och Iris. Håll det likadant för varje nytt erbjudande, även gratisproven.
2. **GDPR vid personlig adress.** `fornamn@bolaget.se` är en personuppgift. Det kräver berättigat intresse med dokumenterad intresseavvägning, information om behandlingen senast vid första kontakten (art. 14) och att ett nej eller en invändning stoppar allt direkt (art. 21). Hormozis "sluta direkt när någon ber om det" är här lag, inte artighet. Suppressionslistan och utfallet "Kontakta inte" finns. Hormozis "återkontakta hela listan var 3–6 månad" gäller bara den som inte sagt nej.
3. **Falsk knapphet och falsk brådska.** Vilseledande marknadsföring (MFL 8–10 §§) gäller även mellan näringsidkare. Påståenden om antal platser, deadline eller "en kund hoppade av" måste vara sanna. Bara verkliga tak (onboardingkapacitet) och verkliga datum (bokslut, kohortstart) går att använda. Säg nej efter deadline, annars var den falsk.
4. **"Gratis" måste vara gratis och säga vad som händer sedan.** Snajps provperiod är redan rätt byggd (inga kortuppgifter, ingen automatisk dragning, påminnelse före slut), men **FAQ:n och supportchatten säger fortfarande att villkoren inte är fastställda**. Rätta det innan provperioden står i ett kallmejl. Annars ger Snajp två olika besked i samma kundresa. Hormozi själv varnar för reglerna om "gratis"-påståenden (MM-wiki › §Designregler).
5. **Garantier är avtalslöften.** En utlovad garanti som inte hålls är både avtalsbrott och vilseledande. Garantera bara handlingar Snajp kontrollerar (förlängd provperiod, export, inget skickas utan ok) och aldrig affärsutfall (möten, kunder, kronor). Snajp har inga data som styrker sådana påståenden, och den som marknadsför ett påstående ska kunna belägga det.
6. **Inga lånade eller påhittade resultat.** Inget leadsmejl har ännu gått ut, så det finns inga Iris-resultat. Fejkade omdömen och case är förbjudna och dessutom Hormozis egen "varumärkesloop som alltid börjar om" (`wiki/sources/2025-12-04-the-game-hormozi-14-years-in-70-minutes.md` › §Fejkade testimonials). Faktakontrollen fäller dem, men stäng av dem i promptunderlaget också.
7. **Giveaways med slumpinslag är lotteri.** Enligt spellagen kräver de licens. Använd inte Hormozis giveaway-modell. En tävling som avgörs på skicklighet är något annat, men inte värd krånglet här.
8. **Jämförande reklam.** Jämför med kundens nuläge, inte med namngivna konkurrenter. Jämförande reklam är tillåten bara under särskilda villkor (MFL 18 §).
9. **Ton: värdestaplar och dollarankare läses som tv-shop.** "Värde 4 351 kr, ditt pris 599" och "så bra att du känner dig dum om du säger nej" fungerar dåligt i svensk B2B. Snajps röstregel säger lugnt, specifikt och utan aggressivt amerikanskt säljspråk (PROJECT_KNOWLEDGE.md › Voice). Tona ner så här:
   - visa *vad som ingår* i 2–3 rader i stället för påstått kronvärde
   - säg riskomvändningen sakligt ("inga kortuppgifter, ingen bindning") i stället för som en "galen garanti"
   - använd en enda förstärkare per mejl, inte bonus plus knapphet plus brådska plus garanti på en gång
   - använd inga utropstecken och inga versaler
10. **Personalisering, men inte som iakttagelse.** Hormozis "1–3 detaljer en vän skulle känna till" krockar med Antons regel mot "Jag ser att ni …" och med gissningsgrinden. Lägg detaljen i branschingången ("För kursföretag som ert …") och påstå aldrig något om deras vardag.
11. **Webbrevisionen är hemlig.** Hormozis diagnos-lead-magnet ("visa ett problem de inte visste om", t.ex. en långsam sajt) får inte byggas på webbrevisionen i Snajps egna mejl, enligt projektregeln 2026-10-08. Snajp bygger dessutom aldrig om hemsidor.
12. **30-dagarsregeln mot två gratismånader.** Används provperioden i stor skala i kallmejl skjuts Snajps återbetalningstid för CAC till minst månad 3. Det är ett affärsval och inget fel, men Anton bör ta det medvetet (business-principles §5.10).

---

## 4. Topp 5 för Snajps kallmejl just nu

**1. Sätt riskomvändningen som redan finns i varje mejl och i PS:et** (avsnitt 1, 24, 30, 40)
Två månader gratis, inga kortuppgifter, ingen bindning och inget går ut utan ert ok. Allt detta är redan byggt och lovat på ångerrättssidan och i onboardingen, men syns inte i mejlen. Utan bevis är risk den största invändningen, och det här tar bort den utan ny kostnad. Två saker måste göras först: rätta FAQ:n och supportchattens kunskapsbas så att de säger samma sak, och lägg villkoren i Snajps affärskontext så att faktakontrollen släpper igenom dem. *Antons beslut:* bara att bekräfta att provperioden är det officiella erbjudandet och vad som händer när den tar slut.

**2. Byt "kort demo" mot gratis-först-leverans per agent** (avsnitt 29, 1, 9)
Hormozis enskilt största hävstång i kall outreach var att byta ett samtal mot konkret leverans, vilket tredubblade take rate. Konkret för Snajp: Iris-provet (några matchande bolag med färdiga utkast), Kvittoprovet (vilka kvitton som hittas i inkorgen) och Supportprovet (svarsförslag på deras tio vanligaste frågor). Leveransen *är* beviset, och det är precis det Snajp saknar. *Antons beslut:* vilket prov per agent och kostnadstaket per prov (Iris-provet förbrukar merinfo- och ScrapeGraph-krediter).

**3. En agent, en nisch, en smärta och nyttan i deras eget arbete** (avsnitt 4, 7, 11, 13, 14)
Iris väljer redan en produkt per bolag, och skrivstilen är redan byggd för det. Det som återstår är att matcha *ett* hinder ur problemlistan (avsnitt 14) och *en* hävstång ur värdeekvationen (tid eller ansträngning) per segment. Det kostar inget nytt, höjer relevansen och är lätt att A/B-testa mellan segment.

**4. En villkorad tjänstegaranti på första resultatet** (avsnitt 25)
"Har ni inte fått [första resultatet] när provperioden är slut förlänger vi den, om ni har gjort [handling]." Det är Hormozis favoritgaranti, och Snajp riskerar bara mer gratistid, inga pengar. Villkoret driver dessutom aktivering, vilket motverkar risken med passiva provkunder (avsnitt 6). Den bygger på det som redan finns (provperiod, faktura i efterhand) och går att formulera utan affärslöften. *Antons beslut:* vad "första resultatet" är per agent och vilket villkor som gäller.

**5. Namnge erbjudandet med MAGIC och testa en sak i taget** (avsnitt 27, 28, 37)
Inget leadsmejl har gått ut ännu, så det första kontrollerbara experimentet är billigast i omslaget: två ämnesrader eller erbjudandenamn per segment mot samma erbjudande, en ändring per vecka, och vinnaren blir kontroll. En sann säsongsanledning (bokslut, terminsstart) är "M" i MAGIC och den enda ärliga brådska Snajp har i dag.

*Vänta med:* knapphet via kapacitetstak (avsnitt 19) tills taket är beslutat och hålls, bonusar i första mejlet (avsnitt 23, de hör hemma i svaret på en invändning), prestationspris (avsnitt 26) och allt som kräver kundresultat.
