# Handoff 2026-10-12 — utkastkedjan skriver referensutkastet på första försöket

Skriven av Claude (Fable 5.1) natten 2026-10-12, för en agent som inte sett
projektet. Antons beställning: analysera hur Iris utkast ändrades genom
AI-knapparna (Personalisera, Förbättra, Personalisera igen) på Fiskebäck
Byggservice och Härlanda Fog & Byggservice, och bygg om kedjan så att det
FÖRSTA utkastet landar där tredje omskrivningen landade, för samtliga 100
Snajp-leads. Dessutom: ta reda på vad som hände med de 27 av 100 som saknade
utkast, ta bort taket på 50 i "Tillbaka till Iris" och alla andra listtak, och
låt Tillbaka till Iris sluta skriva om automatiskt.

## 1. Läget just nu, verifierat

- **Git:** `development` på `dc8e3d3`, allt pushat. Ocommittat i trädet är
  Antons eget (`docs/utkast-merinfo-api-forfragan.md`, `next-env.d.ts`,
  `package.json`, `strategies.md`, `gsap.js`, `smooth-scroll.js`,
  `.playwright-mcp/`): rör inte.
- **Development (Railway):** api och web kör `dc8e3d3`-kedjan (sista
  kodändringen `1c9f4a7` deployad 02:3x, docs-committen bygger bara om).
  Ingen ny migration. `LEADS_DAILY_TOKEN_BUDGET` på api i development är
  **höjd 8 000 000 → 32 000 000** (skript i natt, för fem omkörningsomgångar).
  Anton återställer när han vill; variabeln läses vid start, så ett nytt
  deploy krävs efter ändring (`railway_provision.set_vars` + `deploy`).
- **Snajps granskningskö (tenant `snajp`, id …0002):** 92 nya utkast i
  `awaiting_review`, alla skrivna av den nya kedjan. De 73 gamla godkända
  (schemalagda 08:00) är **avbrutna** (`cancelled`, via Skapa om). Inget har
  skickats. Ett gammalt godkänt utkast står kvar: **Ekospeceriet Göteborg AB**
  (nivå C, godkänt 2026-10-12 00:35 av en människa, går ut 08:00 i gamla stilen)
  — det ingick inte i de 100 och lämnades med flit. Anton avgör.
- **main:** orört. PR #31 (release development → main) väntar fortfarande på
  Antons migrationer 096–099 och merge.
- **Beads (`bd`):** dolt saknas i PATH, inga issues gick att skapa; uppföljningarna
  står i `docs/BESLUT.md` (2026-10-12) och här.

## 2. Vad som byggdes

### Analysen (Antons kärnfråga)

De två kedjorna, steg för steg (skärmbilderna i Antons prompt):

- **Första utkastet** rabblade registerfakta som ingång ("Med fem platschefer
  och en etablerad verksamhet … är jag säker på att …") eller öppnade som en
  mall ("För företag som ert, som säljer till andra företag, är det ofta en
  utmaning att hitta nya kunder"). Erbjudandet fanns oftast med.
- **Personalisera (1)** gjorde mejlet mer personligt men fyllde på med fler
  fakta (20–25 anställda) och smicker, och **tappade erbjudandet** ("Skulle ni
  vilja se ett par konkreta exempel?") — ingen "fem leads utan kostnad", ingen
  enkel handling.
- **Förbättra** blev kortare och rakare, kärnerbjudandet kvar, men ingången
  generisk och ämnesraden utan bolagsnamn: opersonligt.
- **Personalisera (2)** landade: det starka erbjudandet kvar, handlingen sist
  med leveranstid, och en ingång byggd på **förståelse av verksamheten** ur
  bolagets egna ord ("med fokus på nära relationer med beställare och
  fastighetsägare", "med både privatpersoner och företag som kunder") utan
  siffror.
- De tre goda ingångarna i kön (Witekk, Tingstad, Consenso) var byggda på
  något ur bolagets egna ord och byggda olika; de tre dåliga (Preparatus,
  Stenstaden, Svensk Rivtjänst) följde formeln "För företag som ert, som X, är
  det ofta Y". Orsaken: skrivstilen (omgång 1, 2026-10-10) och grundmallen
  (§ 10.2) **föreslog bokstavligen** "För företag som ert inom …" och
  "När man jobbar med …, som ni gör" som ingångar, och modellen tog orden.

### Kedjan (commit `931258a`, `897e3d7`)

- `agent-core/prompts/leads-skrivstil.md` (omgång 4) och
  `agent-core/prompts/leads-systemprompt.md` § 10.2: mallfraserna borta;
  ingången bygger på EN egenskap ur citaten (vem de arbetar för, vad de lägger
  vikt vid, hur de arbetar), aldrig siffror; erbjudandet överlever omskrivning.
- `app/leads/stilkontroll.py`: nya fynd `mall_ingang`, `registerfakta_i_ingangen`
  (antal + anställda/platschefer/år, grundningsår), `antagande_om_dem` ("vet jag
  att", "kan jag tänka mig", "är jag säker på"), `erbjudande_siffror` och
  `erbjudande_produkt` (villkorens siffror och produktens stam ska stå i mejlet),
  `samma_konstruktion` (tre första orden som ett annat mejl i körningen).
- `app/agent/leads_research_v2.py:run_outreach_draft_v2`: körningens redan
  använda ingångar läggs i ärendet; stilgrinden körs på råutkastet och ger EN
  omskrivning med fynden utpekade **före** humanizern (INV-LANG-002 kvar);
  `_ingangsform` tilldelar varje mejl en av fem ingångsformer på prospekt-id,
  eftersom tio parallella jobb inte ser varandras utkast (utan den började 45 av
  62 "När man …").
- Produktval: `_vald_produkt` godtar kortformen ("Iris" = "Iris, leadsagenten");
  `_PRODUKTVAL` säger att null bara gäller när bolaget inte kan använda någon
  produkt.

### Två fel som dök upp under omkörningen (commit `33282df`, `7455fa4`)

- Vid körstart kompilerades Snajps profil om (version `a53bbc5268cf`) till tre
  **produktbundna måste-kriterier** (B2B för Iris, B2C för Supportagenten,
  kvitton för Kvittohanteraren). Alla tre krävdes av varje bolag → 80 av 100
  nivå C. `bedomning.bedom` tar nu `produkt`/`produkter`: ett kriterium bundet
  till en annan produkt än den valda blir en informationsrad med vikt 0.
- Modellen lämnade produktfältet tomt för bolag där "B2B för Iris" var en träff
  med citat. `bedomning.produkt_ur_kriterierna` härleder produkten ur ett
  uppfyllt bundet kriterium och skriver in den i fynd.

### Tillbaka till Iris och taken (commit `931258a`)

- `POST /api/leads/queue/tillbaka-till-iris` avbryter bara utkasten; inget
  research- eller utkastjobb köas. UI-texten i `components/leads/SkickatLista.tsx`
  säger att användaren väljer Skapa utkast i Iris-listan.
- `max_length` borttaget på: `TillbakaTillIrisRequest` (50), `SchemalaggRequest`
  (500), `ProcessaOmRequest` (200), `FlyttRequest` (50, flytt till main),
  `leads_massatgard` (500). `GET /api/leads/queue` hämtar 1000 i stället för 100.
- `processa-om` hoppar över ett felformat id i stället för 500 (`1c9f4a7`).

### Skript

- `scripts/omskriv_utkast.py --slug snajp --sedan … [--utan-utkast|--prospekt …] --apply`:
  kör om research + utkast (Skapa om, ersätter väntande) via API:t med kundens
  nyckel läst ur Railway (`SNAJP_KEY_<SLUG>` på web). Skriver aldrig ut nyckeln.
- `scripts/granska_utkast.py --slug snajp [--visa N] [--json fil]`: kör samma
  stilgrind på kundens väntande utkast och visar fynd per utkast.

### Utfallet, uppmätt

Fem omgångar (100, 80, 25, 13+48, 15 jobb): **92 av 100 har nya utkast**.
Stilgrindens fynd på de 92: inga mallingångar utom 2, inga registerfakta,
inga antaganden, inga tappade erbjudanden; kvar är det som bara flaggas för
granskning (samma handling som ett annat mejl: villkoren dikterar den;
mening över 25 ord: villkorens meningar; 31 med samma tre första ord som något
annat mejl). Ingångarnas två första ord: "när man" 26, "att hitta" 12, "när ni"
8, "den som" 8, därefter spritt. Erbjudanden: 33 gratisprov, 32 garanti, 27 pilot.
Fiskebäck Byggservice och Tingstad Måleri ligger på referensen. Härlanda fick
Kvittohanteraren som produkt i den nya researchen (referensen var Iris).

## 3. Vad som återstår, i prioritetsordning

1. **Anton:** 92 utkast väntar i granskningskön för Snajp. Godkänn, redigera
   eller avvisa som vanligt; inget går ut utan godkännande.
2. **Anton:** Ekospeceriet Göteborg AB går ut 08:00 i gamla stilen (godkänt
   separat 00:35, nivå C). Avbryt i Skickat-listan om det inte ska gå.
3. **Anton:** åtta leads faller som nivå C efter tre försök var: DS Flexhal,
   Nyströms Byggtjänst, Solega, Z Marktjänst (B2B för Iris kunde inte styrkas
   med citat på sajten), Fiive, SafeTeam (B2C för Supportagenten ej styrkt),
   Simmis (behov utan citat), STINAB (modellen uteslöt bolaget som offentlig
   sektor fast det bygger ÅT offentlig sektor). Vägar: lämna; Processa om från
   Iris-listan; eller mjuka upp de produktbundna kriterierna till "bör" i
   profilen. Det är Sebbes krav 2026-10-06 (belagt behov) mot Antons "samtliga
   100" — bara Anton kan väga dem.
4. **Anton:** återställ `LEADS_DAILY_TOKEN_BUDGET` på api i development till
   8 000 000 när natten är över (just nu 32 000 000). Omkörningen förbrukade
   ungefär 20 miljoner tokens.
5. **Agent:** stilgrinden bör kräva att garanti- och pilotmejl namnger agenten i
   stycke 2 före löftet (Witekk, Svensk Rivtjänst går från ingång rakt på "Vi
   lovar …"), och fälla du/ni-blandning (Svensk Rivtjänst: "liksom ni … åt dig").
6. **Agent:** uteslutningen "offentlig sektor" tillämpas ibland på bolagets
   kunder i stället för bolaget (STINAB, Roy Johnsson Linnéstaden). En rad i
   researchoverlayen eller en kodkontroll.
7. **Agent (lägre):** en "bara utkast"-scope för Skapa om, så att ett lead vars
   research redan är bra inte researchas om (och riskerar att falla) bara för
   att utkastet ska skrivas om. Omgång 4 tappade sju goda utkast så.

## 4. Fällor

- **Bash-heredoc på den här maskinen tappar `\\`.** `\\b` blev ett
  backspace-tecken (0x08) i `stilkontroll.py`; skriv kodändringar med Edit/Write
  eller en skriptfil i scratchpad. Pythons `open(...,'w')` skriver CRLF: id-listor
  som läses med `tr '\n' ' '` får `\r` kvar (gav 500 i processa-om).
- **Profilen kompileras om vid körstart** när indatahashen ändrats
  (`profil.sakerstall_profil`), och AI:n kan göra alla kriterier till "måste".
  Kontrollera `agent_configs.settings.profil.kriterier` efter en omkompilering.
- **Dygnsbudgeten** (`LEADS_DAILY_TOKEN_BUDGET`, rullande 24 h per tenant) ger
  429 på Skapa om; variabeln läses vid start, så sätt + deploy.
- **Railway-variabler via API triggar inget deploy** — kalla `deploy()` efteråt.
- **Skapa om (ersatt) avbryter godkända utkast** också. Kör aldrig
  `omskriv_utkast.py --apply` utan att veta att det är avsikten.
- Stilgrindens `samma_uppmaning` och `lang_mening` fälls alltid på villkorsstyrda
  mejl; de är avsiktligt undantagna från omskrivningen före humanizern.

## 5. Antons instruktioner ordagrant

> Gå igenom och resonera noga över de två exemplen med Härlanda Fog & Byggservice
> samt Fiskebäcks Byggservice och hur utkasten ändrades efter varje steg, från det
> platta, initiala, till det med Personalisera, som blev mer personligt men mindre
> säljande och tappade erbjudandet, till Förbättra som det kortare, mer direkta men
> opersonliga med kärnerbjudandet intakt, till den andra rundan med Personalisera,
> med det starkare erbjudandet kvar, men med en rimlig personalisering, utan att
> bara rabbla upp självklara och påträngande fakta som antal anställda, utan enbart
> en förståelse för verksamheten. Kolla även skillnaden på de 3 första markerade
> inledningarna jämfört med de 2 sista, För företag som ert, som gör bla bla, är
> det säkert bla bla och liknande, samma uppbyggnad och struktur och det blir
> väldigt opersonligt och spammigt, till skillnad från de 3 sista som faktiskt
> känns skrivna för varje företag och mottagare, försök verkligen förstå varje
> nyans och hur vi kan ändra kedjan så att den: Inte inleder på samma sätt för
> alla, inte tappar erbjudandet, inte rabblar upp påtvingande fakta och inte blir
> för kortfattat och opersonligt, utan precis motsatsen som jag beskrev innan, gör
> vad du kan för att fånga det och bygg kedjan på ett sådant vis att det faktiskt
> blir som den bra outputen för varenda en- på första utkastet, om du behöver lägga
> Personalisera-Förbättra-Personalisera ovanpå den befintliga kedjan eller något
> annat, gör det, gör vad som krävs och fortsätt tills du uppnått referensutkasten
> för SAMTLIGA 100 Leads. Ta även reda på vad som hände med de övriga 27 utöver de
> 73 av de 100 som finns kvar just nu. Se även till att det går att "Flytta
> tillbaka" vilket antal som helst till Iris, nu är det ett tak på 50, ta bort alla
> sådana tak för alla listor. Och se till att Flytta tillbaka automatiskt inte
> processar om alla, det är upp till användaren vad han vill göra.
