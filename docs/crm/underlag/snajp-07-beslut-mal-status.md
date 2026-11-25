# Snajp CRM, underlag 07: beslut, mål och status som berör ett CRM med tvåvägs-API

Skrivet 2026-11-25 av en läsande agent, på arbetsgrenen `claude/snajp-crm-dd0d83`. Inget i
repot är ändrat utom att den här filen är ny.

**Vad som är läst, i sin helhet:** `docs/BESLUT.md` (rad 1–4346), `GOALS.md` (1–372),
`HANDOFF-2026-10-08-CRM-FLODE.md`, `HANDOFF-2026-11-23-LISTIMPORTEN.md`, `TENANTS.md`,
`PROJECT_KNOWLEDGE.md`, `plans/2026-10-06-listor-crm-separation.md`, projektets `CLAUDE.md`
(reglerna). **Läst i delar:** `STATUS.md` (rad 1–330 och sökträffar på CRM, Buddy, HubSpot,
webhook, tillägg), `plans/2026-10-01-leads-suite-och-korningar.md` (rad 1–60, 290–379),
`plans/2026-10-02-knyta-ihop-korningen.md` (sökträffar), `plans/2026-10-08-crm-flode.md`
(sökträffar), `DESIGN.md` § App surfaces, och kod där ett beslut pekar på den.

**Märkning.** [LÄST] betyder att påståendet står i den angivna filen och raden. [ANTAGANDE] och
[BEDÖMNING] är mina egna slutsatser och ska prövas. Citat är ordagranna ur källan.

---

## 0. Det en byggare behöver veta först

1. **Licensen är avgjord: egen kod, alternativ A** [LÄST `docs/BESLUT.md:12-49`]. Inget ur
   Twentys AGPL-paket kopieras eller citeras; bara MIT-paketen (`twenty-ui`, `twenty-shared`,
   SDK:erna) får återanvändas, och aldrig en fil märkt `/* @license Enterprise */`. Backend under
   `snajp-support/app/crm/`, API under `snajp-support/app/api/`, gränssnittet som egen app under
   `app/crm/`. Twentys namn används inte i produkten.
2. **Datamodellens val har inget beslut i BESLUT.md.** Migration 153 hänvisar till "docs/BESLUT.md
   2026-11-25" för skälen till sina val (`db/migrations/20261125090000_153_crm_grund.sql:8`), men
   posten 2026-11-25 handlar bara om licensen. Konfliktregeln (`kallan_vinner`), vad som händer med
   saknade poster (`behall`/`tidigare_kund`/`ta_bort`), orgnr som unik nyckel och API-nycklarnas
   omfång är alltså obeslutade av Anton och odokumenterade. Projektregeln kräver en post med
   beslutsfattarens resonemang (`CLAUDE.md:63`).
3. **Befintliga kunder blir aldrig leads, i något spår** [LÄST `GOALS.md:169-173`]. Det finns redan
   två vägar för det: CRM-kundlistan (`lead_lists.kalla='crm'`, migration 098) och den gemensamma
   uteslutningsmängden (`snajp-support/app/leads/upptagna.py:87`). Migration 153 lägger `crm_bolag`
   i samma mängd (`snajp-support/app/storage/postgres.py:3653-3658`).
4. **Ett bolag finns på ett ställe** [LÄST `HANDOFF-2026-10-08-CRM-FLODE.md:30,67`]: Antons ord
   "varje bolag ska bara finnas på ett ställe i systemet". Ett fristående CRM med egna
   `crm_bolag` bredvid `prospects` och `lead_list_items` är den största risken för att bryta det.
5. **Webbplatsbedömningen är hemlig** [LÄST `CLAUDE.md:26-34`]: `webbrevision`, `webbniva` och allt
   som härleds ur dem syns bara för plattformsadmin, Umeå Webdesign och Alunix. Gäller varje
   API-svar, export och synk ut. Grindas i samma commit, annars är det en läcka.
6. **Development är en spegel av produktionen med riktiga kunders data** [LÄST `CLAUDE.md:129`],
   main är sanningen och development skickar inget [LÄST `docs/BESLUT.md:3844-3876`]. Nya tabeller
   måste tas ställning till i synken och i gallringen.
7. **Förlopp och utfall ska synas där användaren startade och finnas kvar efter omladdning**
   [LÄST `CLAUDE.md:36-42`, `docs/BESLUT.md:4262-4274`]. En synk är precis ett sådant flöde.
8. **En ny funktion byggs in i den befintliga ytan, aldrig ovanpå** [LÄST `CLAUDE.md:44-53`,
   `docs/BESLUT.md:123-158`]. Krockar med "egen app" om CRM:et dubblerar det Leads redan visar.
9. **Inget beslut finns om ett publikt API, om webhooks ut, om tvåvägs CRM-synk eller om
   Fortnox.** Det som finns: en envägs synk UT till HubSpot och Pipedrive (`snajp-support/app/leads/
   crm_synk.py:1-10`, "Ingenting läses tillbaka"), planens ord att tvåvägs byggs "först när någon
   ber om det" (`plans/2026-10-01-leads-suite-och-korningar.md:319`), och Resends inkommande webhook.
10. **Inget prisbeslut finns för CRM:et.** Listimporten ligger bakom tillägget `leadlists`, och om
    Buddy ska ha den utan tillägget är det "ett prisbeslut" [LÄST
    `HANDOFF-2026-11-23-LISTIMPORTEN.md:51-52`].

---

## 1. CRM-beslutet och dess föregångare

| Datum | Vem | Kärnan, ordagrant | Betydelse för CRM:et |
|---|---|---|---|
| 2026-11-25 | Anton | Svar på valet A (egen kod) eller B (fork som egen AGPL-tjänst): "A" [`docs/BESLUT.md:25-26`] | Egen kod efter en beteendespecifikation. Inventeringen i `docs/crm/` beskriver funktion, inte källkod. Svenska namn där repot är svenskt. Kopplingen till en kunds Twenty-installation går över Twentys publicerade API (Twenty Application Exception) [`:46-49`]. |
| 2026-11-25 | Agentens skäl, följt av Anton | "(1) CRM:et ska kunna byggas in i eller ersätta dashboarden senare, och det stänger B" [`docs/BESLUT.md:28-30`] | Anton har alltså öppnat för att CRM:et **ersätter dashboarden**. Bygg så att det går: samma auth, samma tenantmodell, samma designprimitiver. |
| 2026-11-25 | Öppet | "Var gränsen går mellan 'arkitektur och struktur från originalet' och ett härlett verk är en juridisk bedömning. Den är inte prövad av jurist." [`docs/BESLUT.md:36-37`] | Juristfråga, inte agentens. |
| 2026-11-25 | Agentens skäl | "gränssnittet ska ändå byggas i Astryx" [`docs/BESLUT.md:31`] | [ANTAGANDE] Astryx nämns ingen annanstans i repots markdown (sökt 2026-11-25). Vad det är (designsystem, komponentbibliotek) behöver bekräftas innan gränssnittet byggs. |
| 2026-11-24 | Anton (beställning) | Beställningen återges i migration 153: "Buddy vill inte ladda upp sin kundlista för hand: kunddatan ska synkas in över ett API och hållas aktuell, och kunderna ska gå att hantera i Snajp." [`db/migrations/20261125090000_153_crm_grund.sql:3-5`] | Första körbara del: kundsynk IN. Beställningens egen text 2026-11-24 står inte i BESLUT.md (bara licensvalet 11-25). |
| 2026-11-23 | Anton | "Ta gärna inspiration från hur Twenty byggt upp sin suite och se till att listorna inte bara blir en halvt undangömd flik, utan en integrerad del i sviten …" [`docs/BESLUT.md:62-65`] | Förebilden Twenty gällde redan listorna. "Integrerad del i sviten" är samma linje som regeln 11-24. |
| 2026-11-22 | Anton | Kunderna ska ha "en egen flik och en större plats i Leads-översikten … med notiser även från Snajp för nya svar och händelser och allt annat som förväntas i en faktisk CRM-suite" [`docs/BESLUT.md:589-591`] | Leads är redan en CRM-svit i Antons ögon: Konversationer, Uppföljningar, Sök bolag, notiser. Ett fristående CRM måste förhålla sig till de flikarna. |
| 2026-10-02 | Plan (Anton beställde 10-01) | "Antons ord: inspiration från Salesforce/Upsales, teknisk förebild Twenty; verklig CRM-överblick över listor och Iris-leads … integration med befintligt CRM." [`plans/2026-10-02-knyta-ihop-korningen.md:239`] | Leads Suite (migration 086) byggdes: tidslinje, anteckningar, uppgifter, sparade vyer, pipeline-kanban, CSV-import, automation, envägs synk [`plans/2026-10-02-knyta-ihop-korningen.md:304`, `STATUS.md:258-261`]. |
| 2026-10-01 | Plan | "ett bolag är navet … Det som INTE bärs över: egen metadata-motor, GraphQL, egen auth — vi har tenant/RLS och Next redan." [`plans/2026-10-01-leads-suite-och-korningar.md:301-306`] | Samma gräns bör gälla nu: ingen metadata-motor, ingen GraphQL, ingen egen auth. |
| 2026-10-03 | Anton (design) | "Det ser inte särskilt bra ut" → referenslåset är Twenty (täta tabeller, vyrad) med Mailchimps konsol [`DESIGN.md:188-196`] | CRM-ytorna ska använda `components/ui.tsx`-skalan, understrukna flikar, täta tabeller. |

---

## 2. Listor och listimport

| Datum | Vem | Kärnan, ordagrant | Betydelse för CRM:et |
|---|---|---|---|
| 2026-10-06 | Sebbe | "Iris-leads och leadslistor är skilda spår som aldrig delar bolag … Kundens befintliga kunder, uppladdade som CRM-kundlista, blir aldrig leads i något av spåren." [`GOALS.md:169-173`] | CRM:ets kunder ska in i uteslutningsmängden (görs i 153). Öppet sedan dess: "om listorna bara ska innehålla bolag som underkänts för Iris" [`GOALS.md:172-173`, `plans/2026-10-06-listor-crm-separation.md:25`]. |
| 2026-10-06 | Byggt | CRM-kundlistan sparas som `kalla='crm'` (migration 098), "prospekteras aldrig", 409 på till-iris, prospektbefordran och kombinera; `CrmKundlista.tsx` "även utan listtillägg" [`plans/2026-10-06-listor-crm-separation.md:10-12`, `STATUS.md:196-208`] | Det finns redan en kundlista. CRM:et måste antingen ersätta den eller mata den; två kundregister bredvid varandra bryter "ett ställe". |
| 2026-10-10 | Anton | "Alla leads från listor stannar i sina listor. Varje rad går att klicka på och öppnar samma information och utkast som ett Iris-lead, med exakt samma upplevelse. Knappen Flytta till Iris tas bort helt" [`docs/BESLUT.md:4225-4229`] | En listrad bär ett bakgrundsprospekt (`lead_list_items.prospect_id`, migration 110) [`:4236-4238`]. Ett bolag i CRM:et som också är listrad har alltså redan ett prospekt. |
| 2026-10-10 | Anton | Processa om "gör om informationshämtningen i en noggrannare sökning och sveper bara källor som förra agenten inte använde" [`docs/BESLUT.md:4246-4250`] | Raderna "uppdateras på plats, inget flyttas" [`:4260`]. Samma princip passar CRM-berikning. |
| 2026-10-08 | Anton | "ta inte bort några befintliga listor, och lägg till en funktion för att kunna flytta/lägga till listor till andra kunder" och "Men gör det även möjligt för användaren att ta bort listor." [`HANDOFF-2026-10-08-CRM-FLODE.md:66`] | Plattformsadmin kan kopiera listor mellan kunder (`app/api/admin_listor.py`). Kopian bär bara `LISTRADSFALT` [`snajp-support/app/api/admin_listor.py:38-42`]. |
| 2026-11-23 | Anton | "Vi behöver hårdtesta listimporten och miljön för denna för att motsvara riktig CRM-funktionalitet, som stöder alla tänkbara listformat från olika CRM-leverantörer och gör det användarvänligt och intuitivt." [`docs/BESLUT.md:60-63`] | Läsaren (`lib/leads/importfil.ts`, `importmallar.ts`, `importvarden.ts`, `importrader.ts`) och fältmatchningen finns. CRM:ets filimport och fältmappning bör återanvända dem, inte skriva en andra. |
| 2026-11-23 | Agentens val (inte Antons ord) | Listor är egen flik med vyerna Listor, Säljlista, Befintliga kunder; import i fyra steg (fil, kolumner, granska, klart) med kvitto på listan; dataminimering ("Fritextanteckningar föreslås inte"); "Personnummer sparas inte"; "Ett bolag, en rad"; befintliga kunder, avböjda och begränsade adresser hoppas alltid över; avtalsslut som eget fält; högst 5 000 rader i satser om 500 [`docs/BESLUT.md:75-102`] | Varje punkt är ett mönster CRM-synken bör följa. Särskilt: **personnummer sparas inte** (se avsnitt 6 om migration 153), och **avtalsslut används inte i utkasten** utan Antons ja (facit låst, INV-LEADS-UTKAST-002) [`:99-101`]. |
| 2026-11-23 | Lucka, inte beslut | "`avtalsslut` och `extra` följer aldrig med när plattformsadmin kopierar en lista … Flytten från development till main (`admin_flytt.py`) bär dem inte heller: det är en lucka, inte ett beslut." [`docs/BESLUT.md:117-119`] | Samma lucka uppstår för varje ny CRM-tabell om flyttvägen inte byggs ut. |
| 2026-11-23 | Ej belagt | "Fixturerna i `lib/leads/fixtures/crm-export` är syntetiska. Bara Vismas rubriker är tagna ordagrant ur leverantörens dokumentation." [`docs/BESLUT.md:104-107`] | Henriks riktiga export är provet [`HANDOFF-2026-11-23-LISTIMPORTEN.md:38-40`]. |

---

## 3. Befintliga kunder och "ett bolag på ett ställe"

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-10-06 | Sebbe/byggt | Gemensam uteslutningsmängd "orgnr eller namn utan bolagsform" [`plans/2026-10-06-listor-crm-separation.md:8`] | Nyckeln är `upptagna.orgnr_nyckel` (`snajp-support/app/leads/upptagna.py:41`) och namnnyckeln `nyckel` (`:30`). Migration 153 säger att `crm_bolag.orgnr_nyckel` är "samma nyckel som app/leads/upptagna.py räknar fram" (`153_crm_grund.sql:16-18`). |
| 2026-10-08 | Anton | "Säkerställ att omprocessningar av gamla listor eller Iris-leads aldrig genererar dubletter, varje bolag ska bara finnas på ett ställe i systemet." [`HANDOFF-2026-10-08-CRM-FLODE.md:67`] | Byggt som dubblettgrind och lås i `create_prospect`, `upptagna.samma_bolag` (`upptagna.py:77`) och `signal='flyttad'` [`HANDOFF-2026-10-08-CRM-FLODE.md:30`]. |
| 2026-11-23 | Agentens val | "Befintliga kunder (kundlistan) och adresser som avböjt kontakt hoppas alltid över … Bolag som redan är leads hoppas över om kunden inte kryssar för att ta med dem." [`docs/BESLUT.md:96-98`] | Samma regel bör gälla när CRM-synken skapar personer och bolag. |
| 2026-10-15 | Anton | "var noga med att inte generera dubletter eller att alla agenter söker igenom samma företag … de ska sorteras bort som bortvalda och periodiskt blandas in" [`docs/BESLUT.md:4033-4036`] | Bortval står sig 30 dagar (`api/leads.py:_nyligen_bortvalda`) [`:4040-4042`]. Ett bolag som blir kund i CRM:et ska aldrig blandas in igen. |
| 2026-11-25 | Byggt (ocommittat) | `lista_upptagna_bolag` lägger till `crm_lagring.upptagna_rader` (`snajp-support/app/storage/postgres.py:3653-3658`) | [LÄST] Iris och listbygget utesluter alltså redan CRM:ets bolag när koden når drift. [BEDÖMNING] Det är så kravet "befintliga kunder uteslutas ur Iris-körningar" uppfylls. Prövas inte här. |
| 2026-10-21 | Anton | "Uteslutna bolag ALDRIG i sökprompten" [`docs/BESLUT.md:3464`]: listan "-24seven vending sweden …" gav 13 080 tecken och noll källor [`:3474-3480`] | Ett stort kundregister från Buddy får aldrig skrivas in i en prompt. Uteslutningen sker i kod efter svaret (`discovery._rena_traffar`) [`:3483-3484`]. |

---

## 4. Registerdata och kontaktregler (CLAUDE.md regel 1–22)

Reglerna gäller "tills Anton säger annat. Bygg varje ny leadsfunktion utifrån dem." Källa:
`CLAUDE.md:142-283`. Reglerna gäller leads; ett CRM som delar bolag med leads ärver dem där
bolagen möts.

| Regel | Datum, vem | Kärnan (kort citat) | Betydelse för CRM:et |
|---|---|---|---|
| 1 | 2026-10-04 Anton | "Registret … är ett filter, inte en kontaktkälla." (`CLAUDE.md:144`) | Registrets personer och nummer får aldrig bli en `crm_personer`-rad. Berikning ur allabolag/merinfo får fylla bolagsfakta, aldrig kontakter. [BEDÖMNING] Kunddata från kundens eget CRM är en annan källa (kunden är ansvarig) och omfattas inte av regel 1, men källan per fält bör sparas så att de två aldrig blandas. |
| 2 | 2026-10-04 Anton | "Jev är första filtret." (`:148`) | Gäller nya bolag i leads. Jev får bara publika bolagsdata, aldrig kundmejl (`docs/BESLUT.md:1873-1900`). CRM-data får inte gå till TypeSafe. |
| 3 | 2026-10-04 Anton | "Kontakta bara VD." (`:150`) | Ersatt för Iris av regel 10; står kvar för listor (regel 5, 7). Förbudet mot styrelseledamöter, suppleanter och revisorer UR REGISTRET står kvar (`:184-187`). |
| 4 | 2026-10-04 Anton | Iris-leads hämtar kontakt och händelser från bolagets webbplats (`:153`) | Delvis ersatt av 10 och 22. |
| 5 | 2026-10-04 Anton | Listor: mejl eller telefon "bara om uppgiften kan styrkas tillhöra VD" (`:157`) | Gäller listspåret. En CRM-person från kunden är inte en listrad. |
| 6 | 2026-10-04 Anton | "Inga privatpersonsidor." (`:161`) | Ingen berikning av CRM-personer ur registrets personsidor. |
| 7 | 2026-10-05 Anton | Ensam VD: registrets telefon får användas, "Bara i listor, aldrig som Iris-kontakt." (`:166`) | Inte i CRM:et. |
| 8 | 2026-10-05 Anton | "Bolag som inte blir Iris-leads kastas inte." (`:170`) | — |
| 9 | 2026-10-05 Anton | "Webbkriterier avgörs i kod." Merinfos råsida når aldrig researchprompten (`:174`) | — |
| 10 | 2026-10-07 Sebbe | "Det enda kontaktkravet för ett Iris-lead är en kontaktmejl till bolaget" … "Aldrig en privat adress, en främmande domän eller en HR-, ekonomi- eller robotadress" (`:194`) | Mottagarregeln (`discovery.mottagare`, `_EJ_SALJADRESS`) bör gälla när CRM:et startar ett utskick. |
| 11 | 2026-10-07 Sebbe | Registret fylls på av den gamla sökkedjan; "Anton ska informeras" (`:202`) | — |
| 12 | 2026-10-07 Anton | "Ett bolag med webbplats har alltid ett kontaktsätt." (`:210`) | — |
| 13 | 2026-10-07 Anton | Mejladress som bolaget självt publicerar → Iris; registrets bolags-e-post räcker (`:216`) | — |
| 14 | 2026-10-07 Anton | Tilltal: personlig adress → personens namn, annars utan namn (`:220`) | En CRM-person med styrkt namn ger tilltalet. |
| 15 | 2026-10-07 Anton | "Bara telefon → ringlistan." "Enskilda firmor går inte till ringlistan (NIX-spärren gäller dem)." (`:223-229`) | Koden: `merinfo.py:1140` ("Enskild firma (NIX-kontroll krävs)"), `katalog.py:96`. Ett CRM som ringer eller mejlar enskilda firmor ur sitt register behöver NIX-kontroll. |
| 16 | 2026-10-07 Anton | Ej kvalificerade: utan webbplats och kontakt, utan namngiven VD, "eller enskilda firmor" (`:230`) | — |
| 17 | 2026-10-07 Anton | Återkoppling med utfallen "Ej svar, Återkom (datum), Ej intresserad, Kontakta inte och Möte bokat" … "Uppföljningsmejl är alltid utkast som en människa godkänner." (`:232-245`) | CRM:ets aktivitets- och utfallsmodell ska använda samma utfall (`app/leads/samtal.py`). |
| 18 | 2026-10-08 Anton | Fyra webbnivåer avgjorda i kod (`:247`) | Hemligt, se avsnitt 5. |
| 19 | 2026-10-08 Anton | "Avvecklade bolag kastas i alla spår" (`:256`) | [BEDÖMNING] En CRM-kund som avvecklas ska inte kastas (det är kundens data), men får inte få utskick. Obeslutat. |
| 20 | 2026-10-08 Anton | Webbpoolen: "Bara bolagsnivå lämnar källkunden (INV-SEC-008)" … "aldrig vilken kund som hittade bolaget" (`:258-266`) | CRM-kundernas bolag får aldrig flyta in i webbpoolen med kundkoppling. [BEDÖMNING] Kundens egna kunder bör inte matas in i poolen alls; det är inte prövat om `webbpool.mata_in` läser något som 153 påverkar. |
| 21 | 2026-10-08 Anton | ScrapeGraph och PageSpeed (`:267`) | — |
| 22 | 2026-10-30 Sebbe | `webbplats_kravs` och `behov` är kundval, i dag bara Snajp (`:273`, `docs/BESLUT.md:3130-3184`) | Kundval ligger i `agent_configs.settings` via `PUT /api/leads/config`. CRM-inställningar bör följa samma mönster om de är per kund. |

---

## 5. Webbplatsbedömningens sekretess och INV-SEC-008

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-10-08 | Anton | "En viktig sak: Webbplatsbedömningen är ett hemligt värde som bara är synligt för Admin, Umeå Webdesign och Alunix i det här läget." [`HANDOFF-2026-10-08-CRM-FLODE.md:70`] | Regeln i `CLAUDE.md:26-34`: "Varje API-svar, UI, CSV-export, listkopiering, utkast och prompt som bär den ska grindas … Lägger du till ett ställe som visar eller skickar vidare bedömningen: grinda det i samma commit, annars är det en läcka." |
| Koden | — | `DOLDA_FALT = ("webbrevision", "webbniva")` (`snajp-support/app/leads/webbpool.py:98`), `far_se` "Nej vid fel" (`:108-116`), `dolj` (`:119-120`), synliga kunder ur `WEBBBEDOMNING_SYNLIG`, mottagarna och `WEBBPOOL_INSPIRATION` (`:101-105`) | CRM-API:ts bolagssvar (`/api/crm/v1/companies`) och varje synk UT måste gå genom `far_se`/`dolj`. Webbpoolens `signal_detalj` "ÄR bedömningen" och nollas vid listkopiering (`admin_listor.py:108-110`). |
| 2026-10-08 | Anton (INV-SEC-008) | "Tabellen `webbpool` … är den andra avsiktliga tenantgränsöverskridningen … Aldrig kontaktperson, mejl, telefon, kundens utkast eller status, och aldrig vilken kund som hittade bolaget" [`ARCHITECTURE_INVARIANTS.md:176-186`] | CRM-data får aldrig korsa tenantgränsen. Ingen ny gränsöverskridning utan Antons beslut. |
| Fynd | — | ID:t INV-SEC-008 används två gånger: demotenantens verktyg (`ARCHITECTURE_INVARIANTS.md:150`) och webbpoolen (`:176`). | [BEDÖMNING] En ny CRM-invariant bör få ett ledigt ID; dubbletten bör rättas av den som äger invarianterna. |
| 2026-11-06 | Sebbe | Marknadsvideon: "Webbplatsbedömningen visas inte (Antons beslut 2026-10-08)." [`docs/BESLUT.md:2784-2785`] | Gäller också demodata och skärmbilder av CRM:et. |

---

## 6. GDPR-besluten

### 6.1 Gallring

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| — | Anton (beslut att inte besluta) | "Gallringsperioden är medvetet inte satt — det är ett affärsbeslut, inte ett tekniskt." [`GOALS.md:167-168`]; öppen fråga 3 "Hur länge ska kunddata sparas?" [`:239-240`] | Ett CRM med kundens kundregister ökar mängden personuppgifter kraftigt. Lagringstid för CRM-poster är obeslutad. |
| 2026-11-19 | Agent, efter Codex-granskning | Gallringen är "fortfarande AV i båda miljöerna (`GALLRING_AKTIV`)" [`docs/BESLUT.md:811-813`]; koden `snajp-support/app/jobs/gallring.py:12` | Inget gallras i dag. |
| 2026-11-19 | Agent (runda 3) | Spegeln gallrar själv det synken inte för över; "`tests/test_gallring_spegel.py` håller SQL-listan ihop med `railway_synk.SYNK`" [`docs/BESLUT.md:802-810`] | Varje ny CRM-tabell kräver ett beslut: synkas den (`railway_synk.SYNK`) eller gallras den av spegeln? Testet fäller annars. |
| 2026-11-19 | Agent (runda 9–11) | Triggern `gallring_behandlad` sätter `behandlad_at` "vid varje faktisk ändring … i alla 25 tabeller urvalet läser aktivitet ur" [`docs/BESLUT.md:913-920`] | Om CRM-aktivitet ska skjuta upp gallringen av ett prospekt måste CRM-tabellerna in i urvalet. [BEDÖMNING] "En återkommande teknisk skrivning över gamla rader skulle däremot hålla dem vid liv för alltid … INV-DATA-005 säger att ingen får tillkomma" [`:918-920`]: en synk som skriver om varje rad varje natt är exakt en sådan skrivning. Synken bör bara skriva vid faktisk ändring. |
| 2026-11-19 | Agent (runda 14) | "Ett databastest läser katalogens kaskader och fäller en ny tabell som taket inte räknar." [`docs/BESLUT.md:952-955`] | Nya tabeller med `on delete cascade` från en gallrad tabell fäller testet tills de räknas. |
| 2026-11-18 | Agent | Åtkomstloggen sparas 365 dagar; öppet för Anton om det är rätt [`docs/BESLUT.md:1221-1256`] | Plattformsadmins läsning av CRM-data loggas via `require_master_key`. |

### 6.2 Begränsning (art. 18), spärrlista och invändning

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-11-18 | Agent på Antons uppdrag | "Begränsning av behandling (GDPR art. 18) är en markering per e-postadress i tabellen `behandlingsbegransningar` (migration 124), **global över alla kunder** … Markeringen **behålls vid radering**" [`docs/BESLUT.md:1191-1197`]; satt bara med `scripts/gdpr_radera.py --begransa` | En CRM-person med begränsad adress får varken utskick eller AI-behandling, och får inte raderas av en synk (`saknade='ta_bort'`). Läsning: `Storage.list_begransade` (`postgres.py:1460`). Fail closed: "Kan listan inte läsas stoppar spärren" [`:1195-1196`]. |
| 2026-11-19 | Agent (runda 12) | Gallringen raderade begränsade uppgifter, "ett lagbrott åt det håll gallringen aldrig får fela" [`docs/BESLUT.md:930-938`] | Gäller också CRM:ets egen radering och mjukradering. |
| 2026-11-19 | Agent (runda 15) | "en begränsning är en rättighet som ska gälla överallt där uppgifterna finns" [`docs/BESLUT.md:971-973`] | Varje ny lagringsplats för en adress (crm_personer) ska prövas mot begränsningen. |
| 2026-11-23 | Anton | "Ja bygg den, 6 mån"; Kontakta inte bara efter uttrycklig begäran; "en invändning mot direktmarknadsföring ska följas utan prövning (GDPR art. 21)" [`docs/BESLUT.md:430-453`] | Stegen Återkom, Ej intresserad, Kontakta inte är CRM-status. Kontakta inte är prospektets `suppressed` [`:571-574`]. |
| Spärrlistan | Koden | `list_suppressions` och `add_suppression` per tenant (`snajp-support/app/storage/postgres.py:1453,1469`); Resend-studs och klagomål läggs i suppressions [`docs/BESLUT.md:3419-3421`] | CRM:et ska läsa spärrlistan innan ett utskick och visa den på personen. Om en spärr ska synkas UT till kundens system är obeslutat. |
| 2026-10-25 | Anton (öppet) | "Kampanjer till befintliga kunder är marknadsföring och inte kallkontakt. Det är lagligt B2B med avregistrering i varje mejl, men en lista med privatpersoners adresser kräver samtycke." [`docs/BESLUT.md:3352-3355`] | Kampanjer kan redan gå till CRM-kundlistan [`:3331-3337`]. Ett synkat kundregister kan innehålla privatpersoner (en telefonioperatör har det). Obeslutat hur de skiljs ut. |

### 6.3 Personnummer och enskilda firmor (NIX)

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-11-23 | Agentens val | "**Personnummer sparas inte.** Ett org.nr vars tredje siffra är 0 eller 1 är en enskild firmas personnummer." [`docs/BESLUT.md:90-92`]; koden `lib/leads/importvarden.ts:17,68` | **Krock:** migration 153 sparar en enskild firmas organisationsnummer och märker det (`153_crm_grund.sql:18-19`, `enskild_firma boolean` rad 76, kommentaren rad 278). Två motsatta val i samma kodbas utan beslut av Anton. |
| 2026-10-07 | Anton | Enskilda firmor går inte till ringlistan, "NIX-spärren gäller dem" (`CLAUDE.md:228-229`) | Se regel 15. |
| 2026-11-17 | Agent | Personnummer maskeras före Jev och före varje inbäddning och klassare [`docs/BESLUT.md:1984-2009`, `:1686-1700`] | CRM-text som går till en modell (sammanfattning, sökning) ska maskeras på samma ställe. |

### 6.4 Avtal, AI-leverantörer och informationsplikt

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-11-17 | Agent inom Antons uppdrag | Avtalsgrinden: "ingen trafik på chatt, inkommande mejl och kanaler förrän ett avtalsdatum är registrerat" (GDPR art. 28) [`docs/BESLUT.md:1926-1934`] | [BEDÖMNING] En kundsynk in är personuppgiftsbehandling i biträdesrollen och bör stå bakom samma grind (`ss_tenants.kraver_avtal`). Obeslutat; öppen fråga om självregistrerade kunder [`:1938-1944`]. |
| 2026-08-24 | Anton | "Ingen kunddata till DeepSeek." [`GOALS.md:156-159`, `CLAUDE.md:285`] | Gäller CRM-data. |
| 2026-11-17 | Anton | "Kundmejl går inte till TypeSafe" [`docs/BESLUT.md:1873-1900`] | Gäller CRM-data. |
| 2026-11-17 | Agent | "Google AI Studio får inte bära kunddata" [`docs/BESLUT.md:1904-1921`]; Vertex i `eu` (`:706-746`) | All AI över CRM-data via Vertex i EU. |
| 2026-11-17/11-23 | Agent/Anton | Personlig adress får art. 14-foten; "Med bild, utan gdpr-block" med två meningar kvar [`docs/BESLUT.md:1840-1869`, `:477-489`] | Utskick från CRM:et går genom samma sändare och `send_guard`. |
| 2026-11-15 | Anton (öppet) | Demolänkens klick "knyts till en namngiven mottagare, så integritetspolicyn och utskicksfotens ändamålsrad bör nämna att länkar i utskicken mäts" [`docs/BESLUT.md:2330-2332`] | Om klick och besök visas på CRM-personens tidslinje är det samma öppna fråga. |
| — | Öppet | Q10: "Får kundernas integrationsnycklar ligga krypterade i databasen?" [`GOALS.md:255-262`] | Om CRM:et hämtar från kundens HubSpot/Pipedrive (pull) behövs kundens nyckel. Den lagras i dag krypterad i integrationerna (`crm_synk.py:7-9`), vilket är undantaget Anton inte godkänt. |
| — | Öppet | Q11: dataskyddet när kunden kopplar in en kanal (Meta, Microsoft, USA) [`GOALS.md:263-267`] | Samma fråga för en CRM-källa i USA (HubSpot, Salesforce). |

---

## 7. Prissättning och tillägg

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-11-07 | Anton | "Ändra även priserna till 9990 ex moms för Support och 12990 för Leads 19990 för Duo, skriv även att detta är tillfälliga priser under pilotperioden och kan komma att höjas." [`docs/BESLUT.md:2711-2713`]; `lib/pricing.ts:56-118` | GOALS säger fortfarande 3 990/4 490/6 990 och Trio [`GOALS.md:141-145`]: inaktuellt. |
| 2026-10-17 | Sebbe | "Main fokus är att det ska finnas Snajp duo, inte trio." Kvittohanteraren blir tillägg till Support, pris inte satt [`docs/BESLUT.md:3878-3899`, `lib/pricing.ts:134-154`] | Paketen är Support, Leads, Duo. |
| 2026-08-22/25 | Anton | Leads-paketet: "ICP-konfiguration …, 150 prospekt och 300 mejl per månad, och en granskningskö" [`GOALS.md:146-149`, `lib/pricing.ts:82-88`] | **Vad kunden får utan tillägg** (Leads): Iris, ICP, 150 prospekt, 300 mejl, granskningskö. Extra prospekt 9 kr, extra mejl 3 kr (`lib/pricing.ts:169-170`). Startavgift 1 590 kr (`:166`). |
| — | Pris | Duo lovar "Båda agenterna i samma dashboard, med delad kunddata" och "Delad kunddata" (`lib/pricing.ts:97,103`) | [BEDÖMNING] "Delad kunddata" är redan utlovat i Duo. Ett CRM kan läsas som infriandet av det löftet, eller som en ny produkt. Obeslutat. |
| 2026-09-02 | Byggt | Tillägget `leadlists`: "Agenten bygger färdiga, granskningsbara leadslistor … I tillägget ingår också en säljlista" (`lib/addons.ts:80-84`); övriga tillägg `inbox`, `vision`, `kb_autoingest`, `multilang`, `own_domain`, `reports` (`:15-26`) | Grinden sitter bara i Next (`components/leads/LeadsSida.tsx:213`, `lib/actions/saljlista.ts:46`); backenden grindar inte (`snajp-support/app/api/leads.py:4476-4479`). CRM-kundlistan är tillgänglig "även utan listtillägg" (`plans/2026-10-06-listor-crm-separation.md:12`). |
| 2026-11-23 | Öppet | "Importen ligger bakom tillägget `leadlists`. Om Buddy ska ha den utan tillägget är det ett prisbeslut." [`HANDOFF-2026-11-23-LISTIMPORTEN.md:51-52`] | Inget beslut om CRM:et ingår i Leads, i Duo eller blir ett tillägg. Inget tilläggs-ID finns för CRM i `addonKeys` eller i databasens check-villkor (migration 022/060). |
| 2026-11-15 | Sebbe | "Antalet leads och körningar får inte märkas i sidan" [`docs/BESLUT.md:2140-2191`] | Ett kundregister på tiotusentals rader kräver samma sidindelning och serverräkning (100 rader per sida, `GET …/fordelning`). |

---

## 8. Integrationer och API

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-09-18/19 | Sebbe | Supportagenten kopplas till kundens system: "Kunden lägger själv in HTTP-anrop i Ebbots format eller en MCP-server … Kundens nycklar lagras krypterade (se öppen fråga 10)" [`GOALS.md:132-140`, `STATUS.md:298-312`] | Integrationsramverket (`app/integrationer/`, `INTEGRATION_NYCKEL`, Fernet) finns och bär redan HubSpot/Pipedrive-nyckeln för envägssynken. |
| 2026-10-01/02 | Plan (Antons beställning) | "**Externt CRM-synk (sist, efter import):** HubSpot/Pipedrive via deras REST-API med kundens egen nyckel … envägs ut (status + anteckning) som första steg; tvåvägs först när någon ber om det." [`plans/2026-10-01-leads-suite-och-korningar.md:319`] | Byggt som `snajp-support/app/leads/crm_synk.py`: "Snipra är sanningen … Ingenting läses tillbaka" (`:1-10`), valet `settings.crm_synk` (`api/leads.py:1934-1940`). Buddys beställning är "någon ber om det", och då gäller **kundens system** som källa för kunderna. Det vänder sanningsregeln i `crm_synk.py:3`. |
| 2026-10-24 | Sebbe | Resends webhook `POST /api/webhooks/resend/emails` skriver leverans och lägger adressen i suppressions [`docs/BESLUT.md:3418-3421`] | Det enda inkommande webhook-mönstret för data. Kräver `RESEND_WEBHOOK_SECRET` (`:3428-3429`). |
| — | Anton | "Hemligheter lagras aldrig i databasen, bara som miljövariabler. Frågan restes och avböjdes uttryckligen." [`GOALS.md:160-161`] | API-nycklar till Snajps eget API (`ss_api_keys`) är hashade nycklar, inte hemligheter i den meningen [ANTAGANDE]. Kundens nycklar till externa system är undantaget i Q10. |
| — | Rutin | API-nyckel per kund `SNAJP_KEY_<SLUG>` via `POST /api/keys` med master-nyckeln [`TENANTS.md:120-124`] | Migration 153 ger `ss_api_keys` `omfang`, `namn`, `revoked_at`; befintliga nycklar får `'{*}'` (`153_crm_grund.sql:30-32,268-270`). Byggt men obeslutat av Anton. Underlag 04 § 4.2 rekommenderar omfångsnycklar till Buddy. |
| 2026-11-18 | Agent | Adminloggen sitter i `require_master_key`, "så att nästa admin-endpoint inte kan glömmas" [`docs/BESLUT.md:1232-1236`] | CRM:ets admin-endpoints ärver loggen om de använder samma beroende. |
| 2026-11-18 | Agent | Webbens databasroll har bara det webben gör; "en migration som lägger till en tabell webben ska nå måste ge rättigheten uttryckligen" [`docs/BESLUT.md:1129-1146`] | Om `app/crm/` (Next) läser CRM-tabeller direkt krävs grants och en rad i `TILLATET` (`tests/db/test_snajp_web_rattigheter.py`). Går allt via api:t behövs inget. |
| 2026-11-25 | Anton | Koppling till kunders Twenty "över Twentys publicerade API" [`docs/BESLUT.md:48-49`] | Twenty är en möjlig källa. Migration 153 listar HubSpot, Pipedrive, Lime, Upsales, Salesforce, Twenty och eget format (`153_crm_grund.sql:10-11`). |
| Fortnox | — | Inget beslut. Fortnox nämns bara som mottagare av SIE-exporten (`snajp-support/app/api/kvitton.py:661`) och som en idé i `HANDOFF-2026-08-29-KUNDER-DATA.md:168`. | Kvittohanteraren står på is [`docs/BESLUT.md:3901-3935`]. |
| Publikt API, webhooks ut | — | Inget beslut hittat. | Ett tvåvägs-API mot Buddy (utgående händelser till deras system) är nytt mark. Underlag 04 behandlar säkerheten. |
| 2026-11-18 | Anton | "Repot ska vara privat" [`docs/BESLUT.md:1651-1653`] | OpenAPI-specen (`/api/crm/v1/openapi.json`, `crm_v1.py:840`) är nåbar för den som har nyckel; ingen publik dokumentationssajt är beslutad. |

---

## 9. Designbeslut om appytor

| Datum | Vem | Kärnan, ordagrant | Betydelse |
|---|---|---|---|
| 2026-11-24 | Anton | "lägg till en regel om att ALDRIG enbart lägga till funktioner på det sättet, INTEGRERA alltid i den befintliga designen på ett sätt som samspelar och är logiskt och intuitivt för användaren, verifiera ALLTID med dina egna ögon innan du committar." [`docs/BESLUT.md:133-138`] | `CLAUDE.md:44-61`, `DESIGN.md:198-208`: en rad nyckeltal i trattens ordning (leads, utkast att godkänna, skickade mejl, svar, bokade möten); nya listor blir paneler med samma huvud. "Två rader tal i två stilar, eller två tal som säger nästan samma sak på samma sida, är tecknet på att funktionen lagts ovanpå." |
| 2026-11-24 | Anton | "Går ytan inte att se committas den inte." [`docs/BESLUT.md:146-147`] | Rendera på desktop och mobil, i en förhandsvisning under `app/forhandsvisning/` om ytan kräver inloggning (`CLAUDE.md:55-61`). Development-data får inte synas i skärmbilder (`CLAUDE.md:129-138`). |
| 2026-09-27/10-03 | Anton | En fast skala ur `components/ui.tsx`; "The reference lock is Twenty … with Mailchimp's console" [`DESIGN.md:165-196`] | CRM-appen använder `Sidhuvud`, `Sektion`, `Nyckeltal`, `Tabell`, `fliklista`, `radLank`, `Tomt`. INV-UI-001 fäller `kicker`, versaler, spärrad text, kursiva rubriker och tankstreck i appytornas källkod (`DESIGN.md:214-215`). |
| 2026-10-02 | Anton | "Varje komponent med användarvänd text är tvåspråkig, utan undantag." [`CLAUDE.md:67-77`] | INV-COPY-001 fäller svenska utan par. Gäller `app/crm/` om testets scope täcker katalogen [ANTAGANDE: scope bör kontrolleras, `components/crm` står i planens scope `plans/2026-10-02-knyta-ihop-korningen.md:93`]. |
| 2026-11-23 | Agentens val | "en sida har en primär knapp (DESIGN.md § App surfaces)" [`docs/BESLUT.md:81-82`] | — |
| 2026-11-09 | Anton | Den orangea "Demokonto"-rutan är "FÖRBJUDNA" [`docs/BESLUT.md:2531-2548`] | Gäller en CRM-demo. |
| 2026-11-22 | Anton | Notiserna "**läses av arbetsytan, inte av varje användare**" [`docs/BESLUT.md:576-578`]; "Per användare är en senare utbyggnad om flera säljare delar en arbetsyta." [`:596-597`] | CRM:ets ägare per bolag, uppgifter per användare och notiser är en modell som Leads ännu inte har. |

---

## 10. Förlopp och utfall

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-10-10 | Anton | "Bygg alltid ett sätt att följa flödet för varje funktion. Fråga alltid om det ska vara synligt för kund när det är tveksamt." … "det fanns inget sätt att följa aktiviteten eller veta om det lyckades. Det ska lösas enkelt och tydligt i den befintliga miljön, inte i ytterligare en flik om det inte är absolut nödvändigt." [`docs/BESLUT.md:4262-4274`] | `CLAUDE.md:36-42`: "Ett meddelande om att något 'pågår i bakgrunden' räcker inte." Migration 153 har `crm_synkkorningar` som liggare, uttryckligen för den här regeln (`153_crm_grund.sql:26-28`). **Fråga Anton:** ska synkens förlopp och fel synas för kunden (Buddy) eller bara för plattformsadmin? Regeln säger att det ska frågas. |
| 2026-10-05 | Byggt | Körningar som överlever deploy (INV-JOB-003) [`STATUS.md:193-195`] | Synkkörningar bör återupptas eller avslutas tydligt efter en deploy. |
| 2026-11-10 | Sebbe | "Ett fel gäller sin egen rad, inte hela arbetet" [`docs/BESLUT.md:2395-2420`] | En dålig rad i Buddys sats ska bokföras på raden; resten går vidare. |
| 2026-11-09 | Sebbe | "Samma start två gånger är en start." [`docs/BESLUT.md:2481-2483`] | Migration 153 har `crm_idempotens` (`:29`). |
| 2026-11-23 | Anton | "du måste larma tydligare om sådant": ett steg som påverkar vad som går ut "är ett stopp och inte en rad i en lista" [`docs/BESLUT.md:359-362`] | En synk som tyst slutar uppdatera uteslutningsmängden gör att Iris kontaktar befintliga kunder. Det är ett stopp, inte en logg. |

---

## 11. Drift, miljöer och data som ett CRM ärver

| Datum | Vem | Kärnan | Betydelse |
|---|---|---|---|
| 2026-10-17 | Anton | "När vi fått över alla körningar från development blir main sanningen och synkar till development, och körningar gjorda i development behöver flyttas aktivt" [`docs/BESLUT.md:3846-3850`] | En CRM-synk mot Buddy körs i main. I development skrivs varje CRM-rad över av synken eller står kvar tills den flyttas (`admin_flytt`). [BEDÖMNING] Buddys API bör bara peka mot main; development får sin data via spegeln. |
| 2026-10-21 | Anton | "gör så att inget skrivs från development längre, fyll bara på från main" [`docs/BESLUT.md:3562-3563`] | — |
| 2026-11-16 | Anton | Synken tål att development ligger före main i schemat [`docs/BESLUT.md:2195-2229`]; migrationer ska vara "additiva och idempotenta" [`:2257-2258`] | 153 säger "Additiv och idempotent" (`:33`). |
| 2026-11-23 | Anton | Driftjobben körs hos Railway: `synk` och `migrera-main` i main, `overvakning` i development [`docs/BESLUT.md:283-331`] | Nya tabeller måste in i `railway_synk.SYNK` eller uteslutas med skäl (INV-DATA-008 gäller synken hos Railway). |
| 2026-10-10 | Anton | Utskick, uppföljningssvep, inkorgsläsning och autopilot bara i main [`docs/BESLUT.md:4186-4188`] | Händelser från CRM:et som startar utskick ska följa `scheduler.skickas_har`. |
| 2026-11-18 | Anton | "Ta bort supabase-spåret som ligger kvar helt." [`docs/BESLUT.md:1359`] | `PROJECT_KNOWLEDGE.md:40-41,57-58` pekar fortfarande på `supabase/schema.sql` och tabellerna `companies`, `contacts`: inaktuellt. 153 säger att `companies` och `contacts` är upptagna av äldre tabeller och inte används (`:14-15`). |

---

## 12. Buddy och Henrik

| Datum | Källa | Vad som står | Betydelse |
|---|---|---|---|
| 2026-11-17/18 | Testfixtur | Henrik på Buddy svarade på Snajps utskick; svaret ligger som fixtur `HENRIKS_SVAR` (`snajp-support/tests/leads/test_konversation.py:74-86`) | Buddy kom in som ett lead i Snajps eget Iris-flöde. |
| 2026-11-22 | Anton | "Telecom Buddy (main 2026-11-22) visade varför: svarsutkasten syntes ingenstans, två kasserades tyst, och mötet som bokats från Sebastians Gmail gav 'Möte 0'." [`docs/BESLUT.md:592-594`] | Konversationerna, notiserna och statusen `meeting` byggdes ur Buddy-fallet. **Följd:** Telecom Buddy AB finns som prospekt i tenanten `snajp` [`tests/api/test_konversationer_api.py:3`]. När Buddy blir kund är de en egen tenant; Snajps prospekt på dem är en annan rad. [BEDÖMNING] Snajp bör själv ha Buddy som kund i sitt eget CRM så att Iris aldrig kontaktar dem igen. |
| 2026-11-23 | Anton | "efter att Henrik (Buddy) frågat om leads ur deras egna data (gamla prospekt, förlorade affärer, kunder vars avtal går ut)" [`docs/BESLUT.md:59-60`] | Tre användningsfall: gamla prospekt, förlorade affärer, avtal som går ut. Kundsynken in är grunden; avtalsslut som fält finns (`lead_list_items.avtalsslut`, migration 152). |
| 2026-11-23 | Sebastian | Grenen `buddy-demo-prep` för startsidans prestanda före ett möte [`docs/BESLUT.md:204-245`] | "Inte bekräftat av Anton". |
| 2026-11-24 | Migration 153 | "Buddy vill inte ladda upp sin kundlista för hand" (`153_crm_grund.sql:3`) | Första körbara del. |
| — | Underlag 04 | § 4.2 "Konsekvens för Buddys tvåvägs-API": en vanlig `snajp_live_`-nyckel ger full åtkomst (`docs/crm/underlag/snajp-04-tenants-auth-api-jobb.md:365-367`) | Läs där. |
| Saknas | — | Ingen post om Buddys avtal, pris, avtalsdatum (`kraver_avtal`), vilket källsystem de har, volym, eller vem som är kontakt. Inget i BESLUT eller STATUS om att Buddy är tecknad kund. | Måste frågas. |

---

## 13. Vad GOALS.md anger som nästa delmål

GOALS.md är senast uppdaterad 2026-10-17 (`GOALS.md:4`) och är inaktuell på flera punkter.

| Delmål | Text i GOALS | Läget enligt senare källor |
|---|---|---|
| 9 | "Avgör dataskyddsfrågan om språkmodell-leverantören" (`:74-87`) | I praktiken flyttat till Vertex i EU med servicekonto (`docs/BESLUT.md:610-647`, `:670-702`). De juridiska punkterna (DPA, PUB-villkor) står kvar. |
| 10 | Produktionen i fas med development (`:88-96`) | Gjort 2026-10-17 (`GOALS.md:372`). Releaser sker löpande via PR. |
| 11 | Riktig mejlsändning (`:97-105`) | Utskick går i main (100/dag, `docs/BESLUT.md:2073-2136`). Kvar: avsändare per kund. |
| 12 | Uppföljningskedjan (`:106-109`) | Inkopplad 2026-10-08 (`GOALS.md:276`). |
| 13 | "Riktig betalväxel" (`:110`) | Öppen. |
| 14 | Onboarding körbar igen (`:111-113`) | Onboardingen kopplar arbetsytan själv (`docs/BESLUT.md:160-200`, `TENANTS.md:79-85`). |
| 15 | Jurist, riktiga bolagsuppgifter, gallringsperiod (`:114-117`) | Öppen. |

**Inget delmål nämner ett CRM.** Senaste "nästa att bygga" i STATUS är Antons beställning 2026-11-23
om efterkontroll av svar från brevlådan (`STATUS.md:11-22`), inte CRM:et. [BEDÖMNING] GOALS och
STATUS bör få CRM:et som delmål, så att det inte bara finns i en migration och en licenspost.

---

## 14. Beslut som ett fristående CRM riskerar att krocka med

1. **"Ett bolag på ett ställe"** (`HANDOFF-2026-10-08-CRM-FLODE.md:67`). `crm_bolag` blir en fjärde
   plats för ett bolag bredvid `prospects`, `lead_list_items` och CRM-kundlistan (`lead_lists.kalla='crm'`).
   Uteslutningen fungerar (153 lägger till sig i mängden), men visningen gör det inte: samma bolag
   kan stå som kund i CRM:et, som rad i CRM-kundlistan och som prospekt med tidslinje i Leads.
2. **"Integrera, aldrig ovanpå"** (`docs/BESLUT.md:123-158`). Leads har redan Konversationer,
   Uppföljningar, Samtal, Sök bolag, tidslinje, anteckningar, uppgifter, pipeline och vyn
   Befintliga kunder. En egen CRM-app med egna tal och egen tidslinje är "två tal som säger nästan
   samma sak" i större skala.
3. **"Personnummer sparas inte"** (`docs/BESLUT.md:90-92`) mot `crm_bolag.enskild_firma` som sparar
   numret (`153_crm_grund.sql:18-19`).
4. **Sanningsregeln i envägssynken**: "Snipra är sanningen … Ingenting läses tillbaka"
   (`crm_synk.py:3-4`) mot `konfliktregel default 'kallan_vinner'` (`153_crm_grund.sql:44`).
   Två synkar mot samma HubSpot-konto, åt var sitt håll med var sin sanning, kan pingpong:a.
5. **Hemligheter aldrig i databasen** (`GOALS.md:160-161`) och öppen fråga 10, om CRM:et hämtar
   från kundens system med kundens nyckel.
6. **Webbplatsbedömningens sekretess** (`CLAUDE.md:26-34`): varje CRM-svar, export och synk ut.
7. **Development är spegel, main är sanning** (`docs/BESLUT.md:3844-3876`): ett API som Buddy
   anropar måste peka på main; gallring och synk måste känna de nya tabellerna
   (`tests/test_gallring_spegel.py`, kaskadtestet, `railway_synk.SYNK`).
8. **Avtalsgrinden** (`docs/BESLUT.md:1924-1952`): en synk in är behandling som biträde.
9. **Begränsning är global och överlever radering** (`docs/BESLUT.md:1189-1215`): `saknade='ta_bort'`
   får inte radera en begränsad adress.
10. **Leadsregel 1 och 6** (`CLAUDE.md:144,161`): registerberikning får aldrig bli en CRM-kontakt.
11. **Tillägget `leadlists`** (`lib/addons.ts:80-84`): importen ligger bakom det; CRM-kundlistan
    inte. Om CRM:et ingår i paketet eller kostar extra är obeslutat.
12. **Notiser per arbetsyta** (`docs/BESLUT.md:576-578`): ett CRM med ägare per bolag förutsätter
    per användare.
13. **BESLUT.md-regeln** (`CLAUDE.md:63-65`): datamodellens och API:ts val saknar post.
14. **INV-SEC-008 används två gånger** (`ARCHITECTURE_INVARIANTS.md:150,176`): en ny CRM-invariant
    ska inte förvärra det.
15. **Utkastfacit är låst** (INV-LEADS-UTKAST-002, `CLAUDE.md:79-81`): avtalsslut eller CRM-data i
    utkasten kräver Antons ja (`docs/BESLUT.md:99-101`).

---

## 15. Frågor till Anton

Ordnade efter hur mycket de blockerar kundsynken in åt Buddy.

1. **Sanning och konflikter.** När Buddys system och Snajp säger olika om samma kund: vinner
   källan (som migration 153 gör nu), Snajp, eller den senaste ändringen? Och när en kund saknas
   i en full synk: behåll, märk som tidigare kund, eller ta bort?
2. **Ett ställe.** Ska CRM:ets bolag ersätta CRM-kundlistan (`lead_lists.kalla='crm'`) och bli
   den enda platsen för "befintliga kunder", eller ska båda leva?
3. **Egen app eller del av Leads.** Hur förhåller sig CRM-appen till Leads-flikarna Konversationer,
   Uppföljningar, Samtal och Befintliga kunder? Flyttar de, länkas de, eller finns båda? (Regeln
   2026-11-24 och beslutet 2026-11-25 om att CRM:et kan ersätta dashboarden.)
4. **Enskilda firmor.** Får CRM:et spara en enskild firmas organisationsnummer (personnummer), när
   listimporten valt att inte göra det?
5. **Pris.** Ingår CRM:et och kundsynken i Leads, i Duo ("Delad kunddata"), eller blir det ett
   tillägg? Får Buddy listimporten utan `leadlists`?
6. **Buddys avtal.** Är Buddy tecknad kund, med biträdesavtal registrerat (`kraver_avtal`)? Vilket
   system kommer kunddatan ur, och ungefär hur många kunder och personer?
7. **Synlighet för förloppet.** Ska synkens förlopp, fel och konflikter synas för Buddy eller bara
   för plattformsadmin? (Regeln 2026-10-10 säger att det ska frågas.)
8. **Privatpersoner i kundregistret.** En telefonioperatörs register kan innehålla konsumenter.
   Ska de filtreras bort vid synken, sparas men aldrig kontaktas, eller kräva samtycke (öppet
   sedan 2026-10-25)?
9. **Hämtning med kundens nyckel.** Om Snajp ska hämta ur kundens HubSpot/Pipedrive i stället för
   att kunden skickar: godkänner du att kundens nyckel ligger krypterad i databasen (GOALS fråga 10)?
10. **Tvåvägs ut.** Vad ska gå tillbaka till kundens system: status, möten, utfall, spärrar? Ska en
    avregistrering hos Snajp skrivas till kundens system?
11. **Lagringstid.** Hur länge sparas synkade kunder och personer, och följer de kunddatans
    (obeslutade) gallringsperiod?
12. **Astryx.** Vad är det, och var finns det? (Nämns i licensbeslutet men ingen annanstans.)
13. **Avtalsslut i utkasten.** Ska Iris använda avtalsslut när den skriver till Buddys egna
    kunder? Kräver ändring i låst facit.

---

## 16. Inaktuellt i de lästa dokumenten (att känna till, inte att följa)

- `GOALS.md:141-145` priser och Trio; gällande: `lib/pricing.ts:56-118`, `docs/BESLUT.md:2704-2722`, `:3878-3899`.
- `GOALS.md:61-63` deploy från `railway-main`/`railway-development`; `railway-main` är pensionerad (`CLAUDE.md`).
- `PROJECT_KNOWLEDGE.md:40-41,52-58` Supabase-schema och edge functions; Supabase är borttaget (`docs/BESLUT.md:1357-1384`).
- `TENANTS.md:125,145` Vercel för DNS och "ett Supabase-anrop"; Vercel är avvecklat (`CLAUDE.md`).
- `HANDOFF-2026-10-08-CRM-FLODE.md:42` "Flytta till Iris"; borttagen 2026-10-10 (`docs/BESLUT.md:4223-4242`).
- `GOALS.md:271-277` ändringslogg slutar 2026-10-17; inget om konversationer, listimport eller CRM.
