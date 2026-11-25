# Svenskt underlag 02: dataskydd, NIX och marknadsföringsrätt för Snajp CRM

Underlag till Snajp CRM (Antons beställning 2026-11-24). Skrivet 2026-11-25 av en
researchagent. **Det här är inte juridisk rådgivning.** Det som kräver jurist står
som öppen fråga i § 11.

## Hur texten ska läsas

Varje påstående bär en av fyra märkningar:

| Märkning | Betyder |
|---|---|
| **[LAG]** | Står i lagtext eller förordningstext. Källa anges. |
| **[MYND]** | Vägledning, beslut eller praxis från IMY, EDPB, Konsumentverket, eller branschens självreglering (NIX-Telefon, SWEDMA/Kontakta). Inte bindande lag, men det tillsynen mäter mot. |
| **[BED]** | Min bedömning. Inte prövad av någon jurist. |
| **[REPO]** | Läst i repot. Anges med `fil:rad`. |

Källförteckningen med alla URL:er står i § 12. Allt under [LAG] och [MYND] är hämtat
eller sökt fram 2026-11-25. Där jag inte kunnat läsa källtexten själv står det.

---

## 0. Det viktigaste för den som bygger (sammanfattning)

1. **Två roller i samma app.** När Buddy synkar in sitt kundregister är Buddy
   personuppgiftsansvarig och Snajp biträde [BED, stöd i EDPB 07/2020]. När Snajp
   använder samma data för egna syften (till exempel webbpoolen eller korsning mellan
   kunder) blir Snajp ansvarig för den behandlingen, och den saknar grund. CRM-datan
   får därför aldrig lämna kundens tenant, utom till mottagare kunden själv anger.
2. **Rätten att invända mot direktmarknadsföring är ovillkorlig och ska gälla alla
   kanaler och alla system.** IMY ansåg i H&M-beslutet (DI-2020-10545, 2023-10-17)
   att två dagar var rimlig tid. Sanktionsavgiften blev 350 000 kr, och IMY lade vikt
   vid att invändningar inte nått alla system [MYND]. Spärren måste därför vara
   gemensam för mejl, ringlista och export, och ut-API:t måste fortplanta den
   (`person.sparrad`).
3. **Mjuk radering är inte radering.** `crm_personer.raderad_at` (153:139) behåller
   namn, e-post och telefon, och `GET /api/crm/v1/people?include_deleted=true` lämnar
   ut dem igen (`crm_v1.py:132-139`, `:445`) [REPO]. Art. 17 kräver att uppgifterna
   försvinner [LAG]. Det behövs två lägen: *borttagen i källsystemet* (mjuk, får
   gallras) och *raderad enligt art. 17* (gravsten utan personuppgifter).
4. **E-post till AB kräver inte samtycke enligt MFL. E-post till en enskild firma
   gör det.** MFL 19 § gäller "fysisk person", och en enskild näringsidkare är en
   fysisk person. 20 § (giltig adress att begära stopp till) gäller alltid, också
   till juridiska personer [LAG]. Repot fäller redan enskilda firmor före research
   (`forfilter.py:24-44`) [REPO].
5. **NIX gäller fysiska personers telefonabonnemang, också enskilda näringsidkares.**
   NIX-reglerna (punkt 6.3) tillåter ändå samtal till en enskild näringsidkare om
   produkter för yrkesrollen, om personen är momsregistrerad, arbetsgivare eller har
   F-skatt [MYND]. Ett nummer som kontrollerats får ringas i **två månader**.
   Webbtvätt kostar **17 öre per nummer exkl. moms**, med påfyllning om minst
   1 000 kr [MYND]. Repot spärrar alla enskilda firmor från ringlistan, vilket är
   strängare än branschreglerna (`CLAUDE.md` regel 15) [REPO].
6. **Fälten varje person behöver:** `rattslig_grund` (finns redan, 153:132),
   `kalla_typ` och `kalla_detalj`, `insamlad_at`, `art14_informerad_at`,
   `senaste_kontakt_at`, `gallras_efter`, `sparr_orsak` och `sparr_at` (för alla
   kanaler), `nix_kontrollerad_at` och `nix_utfall`, samt en begränsningsmarkering
   som läses från `behandlingsbegransningar` (124).
7. **API-händelser ut:** `person.skapad`, `person.andrad`, `person.borttagen`
   (mjuk), `person.raderad` (art. 17, gravsten), `person.sparrad`,
   `person.sparr_havd`, `person.begransad`, `person.begransning_havd`, samma för
   bolag när bolaget är en enskild firma. Gör händelserna tunna (id och typ) och
   låt mottagaren hämta resten med sin nyckel [BED].
8. **CRM-tabellerna gallras inte i dag** (snajp-05 § 3.4) [REPO]. Integritetspolicyn
   lovar 24 månader (`JURIDIK_ATGARDER.md:56`, punkt 8) [REPO]. Antingen ansluts
   `crm_bolag`/`crm_personer` till `gallra_tenant`, eller så beslutar Anton att
   kundens eget register gallras på kundens instruktion. Det beslutet saknas.
9. **PUB-avtalet saknar CRM** (`JURIDIK_ATGARDER.md:80`, punkt 22). Med Buddys synk
   blir punkten blockerande [REPO, slutsats som snajp-05:471-473].

---

## 1. Rättslig grund per behandling

### 1.1 Grunderna

- **[LAG]** GDPR art. 6.1 räknar upp sex grunder. För ett B2B-CRM är tre aktuella:
  avtal (b), berättigat intresse (f) och samtycke (a). Art. 6.1 b gäller bara avtal
  *med den registrerade själv* eller åtgärder på dennes begäran före avtal. Ett avtal
  med ett aktiebolag är inte ett avtal med bolagets kontaktperson.
- **[MYND]** IMY: direktmarknadsföring *kan* vara ett berättigat intresse, men den
  ansvarige måste visa att behandlingen är nödvändig, väga intresset mot vad den
  registrerade "rimligen kan förvänta sig", och dokumentera hur bedömningen gjorts.
  Kan samma resultat nås på ett mindre integritetskänsligt sätt går det inte att stödja
  sig på intresseavvägning (IMY, *Intresseavvägning som rättslig grund*).
- **[MYND]** EDPB Guidelines 1/2024 om art. 6.1 f (version 2 publicerad 2026-11):
  skäl 47 betyder *inte* att all direktmarknadsföring automatiskt är ett berättigat
  intresse. Grunden faller om marknadsföringen är olaglig (till exempel bryter mot
  e-privacyreglerna) eller om den registrerade inte rimligen kunde vänta sig den.
  Brev och annan icke-elektronisk marknadsföring omfattas inte av e-privacys
  samtyckeskrav. Jag har inte kunnat läsa version 2 i fulltext (PDF:en gick inte att
  tolka). Paragrafnumren ska kontrolleras innan de citeras i ett avtal.

### 1.2 Grund per behandling i CRM:et

| Behandling | Vem är ansvarig | Rimlig grund | Märkning |
|---|---|---|---|
| Kundens kunder, synkade in från kundens CRM (Buddy) | Kunden | Kundens sak att avgöra. Vanligen 6.1 b för enskilda firmor som själva är avtalspart, annars 6.1 f för kontaktpersoner hos kundbolag | [BED] |
| Prospekt som Iris hittar för kunden | Kunden (Snajp biträde, B2 i `registerforteckning.md`) | 6.1 f, med kundens egen intresseavvägning | [REPO] `intresseavvagning_kallmejl.md:11-13`; [BED] |
| Snajps egna prospekt och kallmejl | Snajp | 6.1 f. Avvägningen är ett utkast som "inte håller i alla delar" | [REPO] `intresseavvagning_kallmejl.md:236-238` |
| Uteslutning av befintliga kunder ur Iris-körningar | Kunden | Samma grund som kundregistret. Uteslutningen minskar intrånget och stärker avvägningen | [BED] |
| Spärrlistan efter invändning eller radering | Den som spärrar | 6.1 c eller f: att kunna respektera invändningen kräver att adressen finns kvar | [BED]; repot behåller `suppressions` vid radering (`gdpr_radera.py:126-132`, via snajp-05:315) |
| Begränsning (art. 18), global över alla kunder | Snajp och varje kund | Rättslig förpliktelse | [REPO] 124:24-29 |
| Samtalsanteckningar, utfall och påminnelser | Kunden | 6.1 f | [BED] |
| Supportärenden på personens tidslinje | Kunden (B1) | Det kunden redan anger för supporten | [REPO] `registerforteckning.md:91` |

**Samtycke** behövs i praktiken bara för e-post och sms till fysiska personer enligt
MFL 19 § (§ 5 nedan). Där är samtycket ett krav enligt marknadsföringsrätten och
blir då i regel också den rättsliga grunden enligt GDPR [MYND, EDPB 1/2024]. CRM:et
måste kunna lagra ett samtycke med tidpunkt, kanal, text och återkallelse (§ 9).

### 1.3 B2B-kontaktuppgifter och enskilda firmor

- **[MYND]** IMY: en adress som `förnamn.efternamn@företag.se` är en personuppgift.
  `info@företag.se` är det inte (IMY, *Personuppgifter*).
- **[MYND]** IMY: ett organisationsnummer för en juridisk person är inte en
  personuppgift. För en **enskild firma** är organisationsnumret ägarens personnummer
  och "anses det vara en personuppgift". GDPR omfattar inte uppgifter om juridiska
  personer (skäl 14).
- **[LAG]** GDPR skäl 14: förordningen gäller inte uppgifter om juridiska personer,
  till exempel firma, juridisk form och kontaktuppgifter till den juridiska personen.
- **[BED]** Följden för datamodellen: allt i `crm_bolag` blir personuppgifter när
  `enskild_firma = true`. Det gäller namn (firman bär ofta ägarens namn), orgnr,
  adress, telefon och e-post. Ett bolag som är en enskild firma ska därför behandlas
  som en person i gallring, radering, export, spärr och webhooks. Migration 153 har
  redan flaggan (153:76) och kommentaren säger det (153:19-20) [REPO], men inget i
  `gdpr_radera.py` söker på orgnr, och testets regex fångar inte `orgnr` (snajp-05:353)
  [REPO].
- **[BED]** En persons tjänsteadress hos ett AB omfattas av GDPR fullt ut. Att
  uppgiften är "i yrkesrollen" påverkar intresseavvägningen (rimliga förväntningar)
  men tar inte bort skyddet. Jag har inte hittat någon IMY-vägledning som säger något
  annat.

---

## 2. Informationsplikt, roller och avtal

### 2.1 Art. 13 och 14

- **[LAG]** Art. 13 gäller när uppgifterna samlas in från personen själv. Art. 14
  gäller när de kommer från annat håll, till exempel ett register, en webbplats eller
  kundens CRM.
- **[LAG]** Art. 14.3: informationen ska lämnas inom skälig tid, **senast inom en
  månad**. Används uppgifterna för att kommunicera med personen ska den lämnas
  **senast vid första kontakten**. Lämnas uppgifterna ut till en annan mottagare ska
  den lämnas senast då.
- **[LAG]** Art. 14.2 f: personen ska få veta **från vilken källa** uppgifterna kommer,
  och i förekommande fall om den är allmänt tillgänglig.
- **[LAG]** Art. 14.5 b: undantag om det är omöjligt eller skulle kräva
  oproportionerlig ansträngning. Då ska informationen göras allmänt tillgänglig och
  andra lämpliga åtgärder vidtas.
- **[REPO]** Art. 14-foten byggs i kod (`utskicksfot.py:67-121`) och regel 4 i
  `send_guard.py` kräver fyra delar: vem, varför, varifrån och rätten att invända
  (`send_guard.py:336-341`). Texten säger "hämtad ur {kalla}" med standardvärdet
  "offentliga företagsuppgifter" (`utskicksfot.py:75, 120`).

**Vad det betyder för CRM:et [BED]:**

| Situation | Vem informerar | När | Vad CRM:et måste spara |
|---|---|---|---|
| Buddy synkar in sina egna kunder | Buddy (har redan informerat enligt art. 13 när kunden tecknade avtal) | Inget nytt, så länge ändamålet är detsamma | `kalla_typ = 'kundsynk'`, anslutningens id, `insamlad_at` |
| Iris hittar ett prospekt i ett register och mejlar | Kunden, genom foten Snajp lägger på | Vid första mejlet (14.3 b) | `kalla_typ = 'register'` eller `'webbplats'`, källans namn (merinfo, allabolag, bolagets egen sajt), `art14_informerad_at` |
| Prospekt som sparas men inte kontaktas | Kunden | Inom en månad (14.3 a), om inte 14.5 b gäller | Samma, och `gallras_efter` |
| Personen läggs in för hand av en säljare | Kunden | Inom en månad eller vid första kontakten | `kalla_typ = 'manuell'`, vem som lade in |

Prospekt som lagras längre än en månad utan att kontaktas är det svagaste läget. Antingen
gallras okontaktade prospekt inom 30 dagar, eller så måste jurist bedöma om 14.5 b
räcker (öppen fråga J3). Repot blandar in bortvalda bolag igen efter 30 dagar
(`intresseavvagning_kallmejl.md:292-293`) [REPO], men det finns ingen gallring av
okontaktade prospekt.

Källuppgiften måste vara konkret. "Offentliga företagsuppgifter" täcker inte en
adress som hämtats från bolagets egen webbplats eller en synk [BED]. Kolumnen `kalla`
i 153 har bara värdena `manuell` och `synk` (153:98, 136; `synk.py:237`) [REPO], vilket
inte räcker för art. 14.2 f.

### 2.2 Personuppgiftsansvarig eller biträde

- **[MYND]** EDPB Guidelines 07/2020 (version 2.1, 2021-07-07): den som bestämmer
  ändamål och väsentliga medel är ansvarig. En leverantör som behandlar på kundens
  instruktion är biträde. Ett biträde som själv bestämmer ändamål för uppgifterna blir
  ansvarig för den behandlingen (art. 28.10 [LAG]).
- **[BED]** När Buddy synkar in sitt kundregister är Buddy ansvarig och Snajp biträde.
  Det stämmer med hur repot redan beskriver supportagenten och leadsagenten
  (`registerforteckning.md:86-112`, avsnitt B) [REPO].
- **[BED]** Snajp blir ansvarig om CRM-datan används för något kunden inte bett om:
  - att träna eller utvärdera modeller på kundens CRM-data,
  - att låta en kunds kundregister påverka en annan kunds körningar (till exempel
    utesluta Buddys kunder ur en annan kunds Iris-körning),
  - att föra in CRM-bolag i webbpoolen (`CLAUDE.md` regel 20; INV-SEC-008 säger att
    bara bolagsnivå lämnar källkunden [REPO]). För en enskild firma är bolagsnivån en
    personuppgift.
  Alla tre ska vara spärrade i kod.
- **[REPO]** Begränsningen av behandling är medvetet global, utan `tenant_id`
  (124:24-29). Det är en annan sak: den skyddar personen och avslöjar inget om vilken
  kund som har personen. Det bör stå i PUB-avtalet (öppen fråga J5).

### 2.3 PUB-avtal, underbiträden och tredjeland

- **[LAG]** Art. 28.3 kräver ett skriftligt avtal med bland annat instruktioner,
  sekretess, säkerhet, villkor för underbiträden, bistånd med de registrerades
  rättigheter (e), bistånd med säkerhet och incidenter (f), radering eller återlämning
  när avtalet upphör (g) och granskning (h).
- **[REPO]** `docs/pub-avtal.md` täcker detta som utkast: rättigheter i punkt 7
  (`pub-avtal.md:187-207`), incidenter i punkt 9 med en tom timgräns
  (`pub-avtal.md:225-229`), radering inom 30 dagar efter avtalsslut (`:258`).
  CRM saknas (`JURIDIK_ATGARDER.md:80`, punkt 22).
- **[REPO]** Underbiträden står på fyra ställen och ska ändras samtidigt
  (`JURIDIK_ATGARDER.md:94-96`). Railways DPA är inte signerad (`:54`, punkt 6).
  Resend lagrar innehåll i USA i 30 dagar, och TIA är inte gjord (`:58`,
  `registerforteckning.md` tabellen överst).
- **[BED]** Det PUB-avtalet behöver för CRM:et:
  1. att kundens CRM-data är en egen kategori med eget ändamål (kundhantering och
     uteslutning ur Iris), och att den aldrig används för andra kunder eller för
     Snajps egna syften;
  2. vilka underbiträden som rör CRM-datan. Railway (databas) gör det alltid. Vertex
     AI gör det bara om CRM-data når en modell, till exempel en sammanfattning på
     tidslinjen. Det bör vara ett aktivt kundval, inte standard;
  3. att webhooks och API-exporter går till mottagare som **kunden** anger, på
     kundens instruktion. Snajp är inte ansvarig för vad mottagaren gör;
  4. hur raderingar och spärrar fortplantas, i båda riktningar (§ 8);
  5. en frist för bistånd med registerutdrag och radering. Utkastet föreslår 10 dagar
     (`pub-avtal.md:201-203`). Det ryms i månadsfristen [BED].
- **[LAG]** Tredjelandsöverföring kräver ett skäl i kapitel V (adekvansbeslut, till
  exempel EU-US Data Privacy Framework för certifierade bolag, eller SCC).
  Om en webhook-mottagare ligger utanför EU är det kundens överföring på kundens
  instruktion, men PUB-avtalet bör säga det [BED].

---

## 3. De registrerades rättigheter

### 3.1 Fristerna

- **[LAG]** Art. 12.3: utan onödigt dröjsmål och senast inom **en månad**. Fristen
  kan förlängas med **två månader** om begäran är komplicerad eller om det kommer
  många, men personen ska få veta om förlängningen och skälet inom den första
  månaden.
- **[MYND]** IMY: fristen börjar dagen begäran tas emot och slutar samma datum
  månaden efter. Faller dagen på en helg skjuts den till nästa vardag (IMY,
  *Tidsfrister*).
- **[MYND]** Invändning mot direktmarknadsföring: IMY bedömde i H&M-beslutet att
  **två dagar** var rimlig tid. Hanteringen bör vara "en rutinåtgärd" och ske
  skyndsamt (IMY DI-2020-10545, s. 9-11). Det gäller där avregistreringen kan ske
  automatiskt. Beslutet säger uttryckligen att tiden beror på omständigheterna.
- **[LAG]** Art. 19: den ansvarige ska meddela **varje mottagare** som fått
  uppgifterna om rättelse, radering och begränsning, om det inte är omöjligt eller
  kräver oproportionerlig ansträngning. Personen har rätt att få veta vilka
  mottagarna är. Det är den rättsliga grunden för webhooks i § 8.
- **[LAG]** Art. 28.3 e: biträdet ska hjälpa den ansvarige att besvara begäranden.

### 3.2 Vad CRM:et måste kunna, rätt för rätt

| Rätt | Lagkrav | Vad CRM:et ska göra tekniskt [BED] | Vad som finns [REPO] |
|---|---|---|---|
| Tillgång, art. 15 | Kopia av uppgifterna, ändamål, mottagare, lagringstid, **källa** (15.1 g), rätten att klaga | Sök på e-post, telefon, mobil, namn och orgnr (enskild firma). Utdrag som JSON och läsbar sammanställning per person, inklusive tidslinjen (konversationer, utkast, samtal, uppföljningar, ärenden) och synkens externa id | `gdpr_radera.py --epost X --export` söker bara på e-post (snajp-05:325-327). Inget API, inget UI (snajp-05:317-321) |
| Rättelse, art. 16 | Rätta felaktiga uppgifter utan onödigt dröjsmål | Ändring i UI och API. Ändringen ska överleva nästa synk: markera fältet i `manuellt_andrade` och skicka `person.andrad` så att källsystemet rättas | `manuellt_andrade` finns (153:97, 135). Konfliktregeln `kallan_vinner` är standard (153:44) och skriver över en rättelse om inte fältet skyddas |
| Radering, art. 17 | Radera utan onödigt dröjsmål när grunden fallit, vid invändning, eller när behandlingen är olaglig | Hård radering av personens fält och tidslinje. Kvar blir en gravsten utan personuppgifter, och en spärrpost med det minimum som krävs för att inte kontakta igen | Skriptet raderar (`gdpr_radera.py:494-547`, snajp-05:309). CRM-tabellerna finns inte i skriptets listor. API:ts `DELETE /api/crm/v1/people/{id}` sätter bara `raderad_at` (`crm_v1.py:431-435`; `synk.py:216-221`) |
| Begränsning, art. 18 | Bara lagring medan något prövas | Läs `behandlingsbegransningar`. Ingen automatisk behandling, ingen export, inget utskick, inga AI-sammanfattningar. Personen ska informeras innan begränsningen hävs (18.3) | Tabellen finns (124:40-47), global, nyckel bara e-post. Tre kodvägar frågar den (snajp-05:393-398). CRM-koden frågar den inte |
| Portabilitet, art. 20 | Bara när grunden är samtycke eller avtal och behandlingen är automatiserad | Export i maskinläsbart format (JSON) av det personen själv lämnat. Samma utdrag som art. 15 räcker | Saknas |
| Invändning, art. 21.1 | Avvägning: den ansvarige får fortsätta bara med tvingande berättigade skäl | Manuell bedömning, sätt begränsning under prövningen (18.1 d) | Begränsningen finns |
| Invändning mot direktmarknadsföring, art. 21.2-3 | Ovillkorlig. Uppgifterna "får inte längre behandlas för sådana ändamål" | Spärr i alla kanaler i sändögonblicket: mejl, ringlista, export till säljverktyg, webhooks. Spärren ska föras till källsystemet | `suppressions` gäller bara e-post (000:170-177, 030). Ringlistans utfall `kontakta_inte` sätter status `suppressed` på leadet (`samtal.py:30-33`). `crm_personer.kontakta_inte` och `crm_bolag.kontakta_inte` finns (153:95, 133). Tre separata spärrar som inte känner till varandra |

### 3.3 Loggning av rättighetsärenden

- **[LAG]** Art. 5.2: den ansvarige ska kunna **visa** att principerna följs.
- **[MYND]** H&M kunde inte visa när klagandena invänt, eftersom
  kundtjänstkorrespondensen redan gallrats. IMY utgick då från det senaste belagda
  datumet (DI-2020-10545, s. 3 och 9-11). Lärdomen: ett rättighetsärende ska sparas
  längre än den vanliga korrespondensen.
- **[BED]** En tabell `crm_rattighetsarenden` per tenant (eller global, för Snajps
  egna ärenden): `id`, `tenant_id`, `typ` (`tillgang`, `rattelse`, `radering`,
  `begransning`, `portabilitet`, `invandning`, `invandning_dm`), `mottagen_at`,
  `kanal` (`mejl`, `avregistreringslank`, `telefon`, `api`, `kund`), `frist_at`
  (mottagen + 1 månad), `forlangd_till`, `forlangning_skal`, `status`
  (`mottagen`, `identitet_kontrolleras`, `pagar`, `besvarad`, `avslagen`),
  `besvarad_at`, `atgard`, `utford_av`. Den får **inte** bära själva personens
  uppgifter efter en radering, bara ett ärendenummer och en hash av nyckeln.
  Lagringstid: förslagsvis tre år, motsvarande preskriptionstiden för skadestånd
  enligt GDPR art. 82 som jurist bör bekräfta (öppen fråga J7).

---

## 4. Lagringsminimering och gallringstider

### 4.1 Lag och myndighetsvägledning

- **[LAG]** Art. 5.1 e: uppgifterna får inte förvaras längre än nödvändigt för
  ändamålet. Art. 13.2 a och 14.2 a: lagringstiden, eller kriterierna för den, ska
  anges i informationen.
- **[LAG]** Bokföringslagen 7 kap. 2 §: räkenskapsinformation ska bevaras till och
  med det **sjunde året** efter utgången av det kalenderår då räkenskapsåret
  avslutades. 5 kap. 7 §: en verifikation ska ange bland annat motparten.
  Räkenskapsinformation (1 kap. 2 § 9) omfattar verifikationer och avtal av särskild
  betydelse för verksamhetens ekonomiska förhållanden.
- **[BED]** Bokföringslagen ger skäl att spara **fakturaunderlag**, inte
  marknadsföringsdata. Att en kund finns i bokföringen i sju år betyder inte att
  kontaktpersonen får ligga kvar i CRM:et för säljändamål i sju år. Snajp CRM är inte
  bokföringssystemet. Fakturor och verifikationer hör hemma i kundens
  bokföringssystem (eller Snajps bokföringsagent, B3 i registerförteckningen), och
  CRM:et ska bara peka dit.
- **[MYND]** NIX-reglerna punkt 6.2: ett **befintligt kundförhållande** anses bestå en
  tid efter avtalets fullgörande, "men inte mer än ett (1) år". Gäller telefon till
  konsumenter, men det är branschens egen gräns för hur länge en kundrelation motiverar
  oombedd kontakt.
- **[MYND]** NIX-reglerna punkt 6.1: ett samtycke till telefonkontakt får användas
  högst **tre månader** efter att det lämnats.
- **[MYND]** SWEDMA/Kontakta, etiska regler 2021-07-01, punkt 4.3: inspelade samtal
  sparas **sex månader** efter samtalet.

Jag har inte hittat någon svensk myndighetsvägledning med fasta gallringstider för
B2B-prospekt. Tabellen nedan är därför min bedömning av vad svenska bolag brukar
tillämpa och vad som går att försvara i en intresseavvägning.

### 4.2 Föreslagna gallringstider [BED]

| Kategori | Föreslagen tid | Räknas från | Motivering |
|---|---|---|---|
| Prospekt som aldrig kontaktats | 30 dagar | `insamlad_at` | Art. 14.3 a ger en månad att informera. Längre lagring utan information är svår att försvara |
| Prospekt kontaktat, inget svar | 12 månader | `senaste_kontakt_at` | Ett år motsvarar NIX:s gräns för kundförhållanden. Repot karensar redan tidigare kontaktade (`send_guard.py` regel 3) |
| Förlorad affär, "ej intresserad" | 12 månader, sedan bara spärrposten | `senaste_kontakt_at` | Behövs för att inte kontakta igen för tidigt |
| Kund med pågående avtal | Avtalstiden | | Kundens eget register, kundens instruktion |
| Före detta kund | 24 månader efter avtalsslut | `avtalsslut` (153:93) | Integritetspolicyns 24 månader (`JURIDIK_ATGARDER.md:56`). Bokföringsunderlaget ligger kvar i bokföringen i sju år, inte i CRM:et |
| Spärrpost efter invändning | Tills vidare, minsta möjliga | `sparr_at` | Krävs för att respektera invändningen. Repot behåller `suppressions` (snajp-05:315) |
| Gravsten efter art. 17-radering | Tills vidare, utan personuppgifter | `raderad_at` | Behövs för att synkande system ska se raderingen (§ 8) |
| Rättighetsärende | Tre år | `besvarad_at` | Bevisning, se H&M ovan (öppen fråga J7) |
| Synkens externa id (`crm_externa_id`) | Som posten den pekar på | | Ett externt id kan vara en personuppgift tillsammans med källsystemet |
| Webhook- och API-loggar | 90 dagar | | Felsökning och incidentutredning (§ 7) |

**Två villkor gäller oavsett siffra:**

1. **Kundens register gallras på kundens instruktion.** Är Snajp biträde bestämmer
   Buddy lagringstiden. Standardvärdet ovan gäller tills kunden valt något annat, och
   valet ska sparas per tenant (som `ss_gallringspolicy`, 048:31-39) [BED].
2. **En synk får inte hålla gamla rader vid liv.** Triggern `gallring_behandlad`
   räknar varje faktisk ändring som en behandling (142). En synk som skriver
   `senast_sedd_at = now()` på själva personraden skulle göra att den aldrig gallras.
   153 lägger `senast_sedd_at` i `crm_externa_id` (153:164), vilket är rätt
   [REPO; varningen står i snajp-05:441-448].

---

## 5. Marknadsföringslagen 19-21 §§ och e-handelslagen

### 5.1 Lagtexten (MFL 2008:486)

- **[LAG] 19 § första stycket:** en näringsidkare får vid marknadsföring till en
  **fysisk person** använda e-post, telefax, uppringningsautomater eller liknande
  automatiska system bara om den fysiska personen **samtyckt på förhand**.
- **[LAG] 19 § andra stycket (befintlig kund):** samtycke krävs inte om adressen
  fåtts i samband med en försäljning till personen, personen inte motsatt sig,
  marknadsföringen gäller **näringsidkarens egna likartade produkter**, och personen
  klart och tydligt får möjlighet att kostnadsfritt och enkelt motsätta sig, både när
  adressen samlas in och i varje följande meddelande.
- **[LAG] 20 §:** varje marknadsföringsmejl ska innehålla en **giltig adress** dit
  mottagaren kan skicka en begäran om att marknadsföringen ska upphöra. "Detta gäller
  även vid marknadsföring till en juridisk person."
- **[LAG] 21 §:** andra metoder för individuell kommunikation på distans (telefonsamtal
  med en människa, brev) får användas om inte **den fysiska personen** tydligt
  motsatt sig det.
- **[LAG] 29 och 31 §§:** marknadsstörningsavgift, lägst 10 000 kr och högst fyra
  procent av omsättningen.
- **[MYND]** Konsumentverket: MFL gäller oavsett om företag vänder sig till företag
  eller konsumenter. Patent- och marknadsdomstolen har bedömt samtal till nummer i
  NIX-registret som brott mot 21 § och god marknadsföringssed (Konsumentverket,
  *Telefonförsäljning - regler för företag*).

### 5.2 Vad det betyder per mottagare

| Mottagare | E-post/sms | Telefon (människa) | Märkning |
|---|---|---|---|
| Aktiebolag, funktionsadress (info@) | Tillåtet utan samtycke. Opt-out-adress krävs (20 §) | Tillåtet. NIX gäller inte juridiska personers nummer vid samtal om verksamheten (NIX-regler punkt 7) | [LAG]/[MYND] |
| Anställd hos AB, personlig adress | MFL 19 § gäller fysiska personer. Den vanliga tolkningen är att marknadsföring riktad till bolaget via en anställds tjänsteadress inte kräver samtycke, men jag har inte hittat någon myndighetstext som säger det. GDPR gäller fullt ut, med art. 14-information | Tillåtet om personen inte motsatt sig (21 §) | [BED], öppen fråga J1 |
| Enskild näringsidkare | **Samtycke krävs** (19 §), om inte undantaget för befintlig kund gäller | Tillåtet om personen inte motsatt sig (21 §). NIX gäller, men undantaget i NIX-regel 6.3 (yrkesrollen, momsregistrerad, arbetsgivare eller F-skatt) kan tillåta samtalet | [LAG]/[MYND] |
| Befintlig kund (fysisk person) | Undantaget i 19 § andra stycket: bara egna likartade produkter, opt-out i varje mejl | Tillåtet; NIX-regel 6.2 tillåter samtal i högst ett år efter avtalet | [LAG]/[MYND] |

**[REPO]** Repot följer detta för e-post: enskilda firmor fälls före research
(`forfilter.py:24-44`), men bara när orgnr är känt
(`intresseavvagning_kallmejl.md:195-198`). En enskild firma utan känt orgnr kan alltså
få ett kallmejl.

**[BED] Kundsynken ändrar läget för undantaget i 19 § andra stycket.** När Buddy synkar
in sina egna kunder kan CRM:et veta att en enskild firma *är* kund. Då kan undantaget
för befintlig kund gälla, men bara för Buddys egna likartade produkter, och bara om
Buddy erbjudit opt-out när adressen samlades in. CRM:et kan inte veta det sista. Det
ska därför vara ett uttryckligt val per anslutning ("kunderna har fått möjlighet att
tacka nej till marknadsföring vid köpet"), inte en slutsats ur relationen.

### 5.3 Avsändaruppgifter

- **[LAG]** E-handelslagen (2002:562) 8 §: tjänsteleverantören ska ge information om
  namn, adress i etableringsstaten, e-postadress och, i förekommande fall,
  organisationsnummer och momsregistreringsnummer, lätt, direkt och stadigvarande
  tillgängligt.
- **[LAG, inte kontrollerad ordagrant]** E-handelslagen 10 §: kommersiella meddelanden
  ska vara tydligt identifierbara, och det ska framgå på vems uppdrag de skickas. Jag
  har inte läst paragrafens lydelse i den här genomgången.
- **[REPO]** Regel 1 i `send_guard.py` kräver företagsnamnet och tar org.nr och adress
  "när de finns" (`send_guard.py:198-209`). Org.nr saknas i foten
  (`JURIDIK_ATGARDER.md:70`, punkt 17).
- **[MYND]** SWEDMA/Kontakta punkt 4.1 (telefon till konsument): säljaren ska ange sitt
  namn, uppdragsgivaren, relationen mellan dem och syftet, och kunna berätta
  **adresskällan**, det vill säga varifrån numret kommer.

---

## 6. NIX-Telefon och spärrlistor

### 6.1 Vad NIX är

- **[MYND]** NIX-Telefon är branschens spärregister. Registreringen gäller tills
  vidare och kan hävas när som helst. Den är gratis för den som spärrar
  (nixtelefon.org).
- **[MYND]** Vem kan registrera: fysiska personer med telefonabonnemang, vilket enligt
  NIX-reglerna omfattar **konsumenter och enskilda näringsidkare**. Nummer som ägs av
  juridiska personer behandlas i punkt 7: samtal till personen som konsument är inte
  tillåtna, men samtal om den juridiska personens verksamhet är det, normalt under
  kontorstid (nixtelefon.org/regler).
- **[MYND]** Undantag (NIX-regler punkt 6):
  - 6.1 uttryckligt samtycke, inom samtyckets syfte, högst tre månader eller tills det
    återkallas;
  - 6.2 befintligt kundförhållande, samma typ av varor eller tjänster, högst ett år
    efter fullgjort avtal;
  - 6.3 **enskild näringsidkare**: samtal om produkter för yrkesrollen är tillåtna om
    personen är momsregistrerad, arbetsgivare eller F-skattskyldig;
  - en person som uttryckligen avböjt kontakt från ett visst företag får aldrig
    kontaktas av det företaget.
- **[MYND]** Kontroll: ett nummer som inte var registrerat vid kontrollen får ringas
  inom **två månader** från uppdateringsdatumet för registerversionen. Befintliga
  kunder behöver inte kontrolleras, men NIX rekommenderar att de som spärrat tas bort
  (nixtelefon.org/for-foretag).
- **[MYND]** SWEDMA/Kontakta, etiska regler för telefon till konsument (version
  2021-07-01), punkt 2: samtal i försäljnings- eller marknadsföringssyfte är inte
  tillåtna till nummer i NIX-Telefon **eller i det spärregister marknadens aktörer är
  skyldiga att tillhandahålla**, det vill säga en spärrlista i egen regi. Reglerna
  sätter också samtalstider (vardagar 08-21, helger 10-18), högst två påringningar per
  dygn och nummer med minst fyra timmar emellan, och högst 20 påringningar per uppdrag
  och 30 dagar (punkt 3.2). Reglerna gäller samtal till konsumenter och anmäls till
  NIX-nämnden eller Konsumentverket.
- **[MYND]** Det finns **inget betalt NIX-register för företag**. Säljare som erbjuder
  företag en "NIX-spärr" mot avgift är enligt SWEDMA oftast callcenterbolag själva
  (Realtid).

### 6.2 Hur tvätten görs och vad den kostar

**[MYND]**, nixtelefon.org/for-foretag, priser exkl. moms, hämtade 2026-11-25:

| Väg | Hur | Pris |
|---|---|---|
| Webbtvätt | Ladda upp en lista. Verktyget ger en fil där registrerade nummer är borttagna eller markerade. Listan lämnas inte till någon annan | 17 öre per kontrollerat nummer. Kontot fylls på med minst 1 000 kr åt gången |
| Återförsäljare | Eget avtal med föreningen, hämtar registret varje vecka och tvättar åt andra | 5 000 kr i registreringsavgift plus 13 öre per kontrollerat nummer eller 17 öre per levererat NIX-fritt nummer |
| Storanvändare | Minst 800 000 kontroller per år, bara för koncernens egna produkter | 110 500 kr per år, inga rörliga avgifter |

Sidan nämner också en rabatt på 15 procent med två olika datum. De aktuella villkoren
ska bekräftas med NIX (kampanjkontroll@nixtelefon.org) innan avtal tecknas.

**[BED]** Det finns inget publikt API för tvätt som jag hittat. Snajp kan inte själv bli
storanvändare för kundernas räkning, eftersom den licensen bara gäller egna produkter.
Rimliga vägar:

1. Kunden tvättar själv via webbtvätten och laddar upp utfallet. CRM:et sparar
   `nix_kontrollerad_at` och `nix_utfall` och vägrar ringlistan när kontrollen är
   äldre än två månader.
2. Snajp tecknar avtal som återförsäljare och tvättar åt kunderna. Då blir Snajp
   biträde för kunden även i tvätten, och det ska stå i PUB-avtalet. Kostnaden är
   ungefär 5 000 kr en gång plus 13-17 öre per nummer.

### 6.3 Spärrlista i egen regi

- **[BED]** En spärr i egen regi ska gälla **tills vidare**. NIX-reglerna säger att en
  person som avböjt kontakt från ett visst företag aldrig får kontaktas av det
  företaget. Den spärren är per tenant, eftersom personen avböjt just den kundens
  kontakt.
- **[BED]** Spärren ska gälla alla kanaler: e-post, telefon och sms. I dag finns tre
  separata mekanismer (§ 3.2). En gemensam tabell, till exempel `crm_sparrar`
  (`tenant_id`, `kanal`: `alla`, `epost`, `telefon`, `sms`; `nyckel_typ`: `epost`,
  `telefon`, `orgnr`; `nyckel_hash`; `orsak`; `kalla`; `sparrad_at`; `havd_at`), med
  `suppressions` som en vy eller en kopia, gör att samma kontroll kan ske i
  sändögonblicket för mejl och när ringlistan byggs.
- **[BED]** Nyckeln kan sparas som en hash (normaliserad e-post eller telefonnummer i
  E.164) i stället för i klartext. En hash är fortfarande en personuppgift
  (pseudonymiserad) men minskar vad som läcker vid en incident.

### 6.4 Pågående lagstiftning

- **[MYND]** Regeringen gav 2026-07-09 en utredare i uppdrag att se över skyddet för
  konsumenter vid telefonförsäljning, bland annat **opt-in** och ett möjligt
  **förbud**, och hur självregleringen med spärregister kan stärkas. Redovisas
  **senast 2027-01-15** (regeringen.se). Pressmeddelandet nämner bara konsumenter.
- **[MYND]** Konsumentverket har föreslagit ett generellt förbud mot telefonförsäljning
  (sökresultat, regeringens uppdrag 2025-05). Jag har inte läst rapporten själv.
- **[BED]** Bygg telefonkanalen så att en opt-in-regel för fysiska personer går att slå
  på per tenant utan ombyggnad: samma samtyckesfält som för e-post (§ 9).

---

## 7. Loggning och säkerhet

- **[LAG]** Art. 30.1: den ansvarige för ett register över behandlingar. Art. 30.2:
  biträdet för ett eget register över behandlingar det utför för varje ansvarig.
  Undantaget i 30.5 för färre än 250 anställda gäller inte när behandlingen sker
  regelbundet, och ett CRM behandlar regelbundet.
- **[LAG]** Art. 32: lämpliga tekniska och organisatoriska åtgärder, bland annat
  förmåga att säkerställa konfidentialitet och att regelbundet testa åtgärderna.
- **[LAG]** Art. 33.1: anmälan till IMY inom **72 timmar** från att den ansvarige
  blivit medveten om incidenten, om det inte är osannolikt att den medför risk. Art.
  33.2: biträdet underrättar den ansvarige **utan onödigt dröjsmål**. Art. 34: de
  registrerade underrättas vid hög risk.
- **[MYND]** IMY tar emot anmälan via e-tjänsten (e-tjanster.imy.se/report).
- **[REPO]** Incidentrutinen finns (`INCIDENT_RESPONSE.md:1-79`) och säger rätt sak om
  biträdesrollen: Snajp underrättar kunden snabbare än 72 timmar (`:64-71`). Fem
  incidenter står öppna och obedömda (`:85-91`). PUB-avtalets timgräns är tom
  (`pub-avtal.md:229`, pilotavtalet föreslår 24 timmar).
- **[REPO]** Registerförteckningen finns (`docs/registerforteckning.md`) men har ingen
  post för CRM:et, och lagringstiderna är "[fylls i]" (`:44, 59, 82, 101`).
- **[REPO]** Åtkomstlogg för admin finns i `audit_logs` via `logga_adminatkomst`
  (migration 123, snajp-05:313).

**Vad CRM:et behöver [BED]:**

1. **Post i registerförteckningen:** en B-post "B4. Snajp CRM, kundens kundregister"
   (biträde) och en ändring i A2 om Snajps egen användning.
2. **Åtkomstlogg per API-nyckel:** vilken nyckel (`ss_api_keys.id`), metod, sökväg,
   antal poster, tid och IP, i en egen tabell utan själva personuppgifterna. Krävs
   för att kunna svara "vilka uppgifter nådde den läckta nyckeln" efter en incident.
   Rutinen säger att en läckt nyckel roteras först (`INCIDENT_RESPONSE.md:34-41`).
3. **Logg över export och webhook-leveranser:** mottagare (URL eller nyckel),
   händelsetyp, post-id, tid, utfall. Uppfyller art. 19 andra meningen (rätten att få
   veta mottagarna).
4. **Omfång per nyckel:** 153 ger `ss_api_keys` omfång (153:30-32). En nyckel för
   kundsynk in bör inte kunna läsa ut hela registret; en läsnyckel för webhooks bör
   inte kunna skriva.
5. **Ingen personuppgift i loggrader** utöver id. Felmeddelanden i
   `crm_synkkorningar` får inte innehålla e-post eller namn ur den post som fallerade
   [BED; jfr incidenten 2026-11-10 om steglogg i jobbsvaret,
   `INCIDENT_RESPONSE.md:90`].

---

## 8. Publikt API och webhooks ut

### 8.1 Vilka uppgifter får lämna systemet, och till vem

- **[BED]** Mottagaren är alltid kunden själv eller någon kunden utsett. Snajp väljer
  aldrig mottagare. En webhook-URL och en API-nyckel är kundens instruktion och ska
  sparas med vem som lade in dem och när.
- **[BED]** Följande ska **aldrig** gå ut via CRM-API:t eller webhooks:
  - webbplatsbedömningen och allt som härleds ur den, för andra kunder än
    plattformsadmin, Umeå Webdesign och Alunix (`CLAUDE.md`, "Webbplatsbedömningen är
    hemlig") [REPO];
  - registrets personuppgifter som inte får vara kontakter (`CLAUDE.md` leadsregel 1
    och 6) [REPO];
  - uppgifter om andra kunder, inklusive att en person är begränsad *hos en annan
    kund* utöver att begränsningen finns;
  - personuppgifter om en person med aktiv begränsning, utöver id och markeringen.
- **[BED]** Raderade poster: `include_deleted=true` får bara ge gravstenen (id, externa
  id, `deleted_at`, orsak), aldrig namn, e-post eller telefon. I dag ger den hela
  posten (`crm_v1.py:132-139` och `:445`) [REPO].

### 8.2 Hur raderingar och spärrar fortplantas

- **[LAG]** Art. 19 kräver att mottagare meddelas om rättelse, radering och
  begränsning. Art. 21.3 kräver att direktmarknadsföringen upphör, och H&M-beslutet
  visar att det gäller i alla system [MYND].
- **[BED]** Två sorters "borta":

| Läge | Orsak | Vad som sparas | Händelse |
|---|---|---|---|
| Borttagen | Posten saknas i källsystemet vid en full synk (`saknade = 'ta_bort'`, 153:62), eller kunden tog bort den | Hela posten tills gallringen tar den | `person.borttagen` |
| Raderad (art. 17) | Den registrerades begäran, gallring eller kundens instruktion att radera | Gravsten: `id`, `tenant_id`, externa id, `raderad_at`, `orsak`. Inga personuppgifter | `person.raderad` |

- **[BED]** Gravstenen behövs för att den som synkar ut ska kunna radera hos sig.
  Den ska behållas tills vidare, eller åtminstone så länge någon anslutning kan synka.
- **[BED]** Ett återinsläpp efter radering måste hanteras. Synkar Buddy in samma person
  igen efter en art. 17-radering finns två fall:
  1. raderingen kom från Buddy (kundens beslut): ny post är tillåten;
  2. raderingen kom från den registrerade via Snajp (till exempel
     avregistreringslänken): Snajp lägger posten på spärren och rapporterar den i
     synkkörningen med en kod som `person_raderad_pa_begaran`, så att Buddy kan radera
     i sitt eget system.
  Vem som avgör, Buddy eller Snajp, är en avtalsfråga (öppen fråga J6).
- **[BED]** Ordning och leverans: webhooks ska vara signerade (HMAC över kroppen med en
  hemlighet per mottagare), gå bara över HTTPS, försökas om med backoff, och ha en
  logg kunden kan läsa (regeln 2026-10-10 om att följa flödet) [REPO för regeln].
  Varje händelse bär `event_id` (för idempotens), `occurred_at`, `type` och
  `data.id`.
- **[BED]** Tunna händelser: skicka id och typ, inte posten. Mottagaren hämtar posten
  med sin nyckel via `GET /api/crm/v1/people/{id}`. Det gör att en begränsning eller
  radering som skett mellan händelse och hämtning respekteras, och att en
  feladresserad webhook läcker mindre.

### 8.3 Händelsekatalog [BED]

| Händelse | När | `data` utöver `id` |
|---|---|---|
| `person.skapad` | Ny person | `bolag_id` |
| `person.andrad` | Fält ändrat (också rättelse enligt art. 16) | `falt` (namnen, inte värdena) |
| `person.borttagen` | Mjuk borttagning | `orsak` |
| `person.raderad` | Art. 17 eller gallring, gravsten skapad | `orsak`: `registrerads_begaran`, `gallring`, `kundens_instruktion` |
| `person.sparrad` | Invändning mot direktmarknadsföring eller "kontakta inte" | `kanal`: `alla`, `epost`, `telefon`, `sms`; `orsak` |
| `person.sparr_havd` | Spärren hävd (bara på personens egen begäran) | `kanal` |
| `person.begransad` | Aktiv rad i `behandlingsbegransningar` för personens adress | inget mer |
| `person.begransning_havd` | Begränsningen hävd (personen ska ha informerats, art. 18.3) | inget mer |
| `bolag.*` | Samma uppsättning. För `enskild_firma = true` gäller samma regler som för person | |
| `synk.korning_klar` | Synkkörningen klar | räknare, felkoder utan personuppgifter |

---

## 9. Kravlista för CRM:et

### 9.1 Fält

På `crm_personer`, och på `crm_bolag` när `enskild_firma = true` [BED]:

| Fält | Typ | Värden | Varför | Finns |
|---|---|---|---|---|
| `rattslig_grund` | text | `avtal`, `berattigat_intresse`, `samtycke` | Art. 6, art. 13.1 c och 14.1 c | Ja, 153:132, 144 |
| `kalla_typ` | text | `kundsynk`, `register`, `webbplats`, `manuell`, `formular`, `import` | Art. 14.2 f, 15.1 g | Delvis: `kalla` har `manuell`/`synk` (153:98, 136) |
| `kalla_detalj` | text | anslutningens namn, registrets namn, sidans URL | Art. 14.2 f kräver källan, inte bara typen | Nej |
| `insamlad_at` | timestamptz | | Startar fristen i art. 14.3 a och gallringen | Nej (`created_at` är inte samma sak vid omsynk) |
| `art14_informerad_at` | timestamptz | | Visar att informationen lämnats | Nej |
| `senaste_kontakt_at` | timestamptz | | Gallring och karens | Nej, räknas ur tidslinjen |
| `gallras_efter` | date | | Beräknad ur kategori och kundens policy, syns i UI | Nej |
| `sparr_orsak` | text | `invandning_dm`, `avregistrering`, `kontakta_inte_samtal`, `kundens_beslut`, `nix` | Art. 21.3, MFL 20-21 §§ | Bara `kontakta_inte boolean` (153:95, 133) |
| `sparr_kanal` | text | `alla`, `epost`, `telefon`, `sms` | Spärren ska kunna gälla alla kanaler | Nej |
| `sparr_at` | timestamptz | | Bevis för när invändningen verkställdes (H&M) | Nej |
| `samtycke_kanal`, `samtycke_at`, `samtycke_text`, `samtycke_aterkallat_at` | | | MFL 19 § för enskilda firmor och fysiska personer | Nej |
| `nix_kontrollerad_at`, `nix_utfall` | timestamptz, text (`fri`, `registrerad`, `undantag_6_2`, `undantag_6_3`) | | NIX två månader, ringlistan | Nej |
| `marknadsforing_optout_vid_kop` | boolean, per anslutning | | 19 § andra stycket | Nej |

Begränsningen ska **inte** kopieras in som fält. Den läses från
`behandlingsbegransningar` varje gång (124 är global och skrivs bara av skriptet).
Nyckeln där är bara e-post (124:40-47) [REPO]; en person med bara telefon kan inte
begränsas i dag.

### 9.2 Funktioner

1. **Rättighetssök** över e-post, telefon, mobil, namn och orgnr för enskild firma.
   Utöka `gdpr_radera.py` med CRM-tabellerna, med orgnr och telefon som nycklar, och
   lägg `crm_bolag`, `crm_personer`, `crm_externa_id` i dess listor. Testet
   `tests/test_gdpr_radera.py` fäller tabellerna annars bara om kolumnnamnet matchar
   regexen, och `mobil` och `orgnr` gör det inte (snajp-05:347-353) [REPO].
2. **Registerutdrag** per person, JSON och läsbart, inklusive tidslinje och källor.
3. **Radering enligt art. 17** som skapar gravsten, raderar tidslinjen, lägger
   spärrposten och skickar `person.raderad`. Skild från mjuk borttagning.
4. **Rättelse** som skyddar fältet mot nästa synk och skickar `person.andrad`.
5. **Gemensam spärr** för alla kanaler, kontrollerad i sändögonblicket (som
   `send_guard` regel 3, `send_guard.py:288-298`) och när ringlistan byggs.
6. **Begränsning** som stoppar export, webhooks med innehåll, AI-sammanfattningar och
   utskick. Kundsynken in får lagra men inte trigga automatisk behandling
   (snajp-05:404-408).
7. **Gallring** av `crm_bolag` och `crm_personer` per kategori enligt § 4.2, med
   kundens policy per tenant. Följer reglerna i snajp-05 § 3.4 (två varv, radlås,
   begränsningsundantag, takräkning).
8. **NIX-status** per telefonnummer, uppladdning av tvättfil, spärr av ringlistan när
   kontrollen är äldre än två månader.
9. **Rättighetsärenden** med frist, förlängning och status (§ 3.3).
10. **Åtkomst- och leveranslogg** per API-nyckel och webhook (§ 7).
11. **Inget flöde mellan tenants:** test som fäller om CRM-data från en tenant påverkar
    en annan tenants Iris-körning, webbpool eller export.

### 9.3 API-ytan

Finns i dag (`crm_v1.py`, prefix `/api/crm/v1`, 45) [REPO]: `GET/POST /companies`,
`GET/PATCH/DELETE /companies/{company_id}`, `GET/POST /people`,
`GET/PATCH/DELETE /people/{person_id}`, anslutningar och synkkörningar
(`crm_v1.py:448-800`). Inga webhooks finns (sökning på "webhook" i `app/crm/` och
`crm_v1.py` gav ingen träff).

Förslag [BED]:

| Metod och sökväg | Vad |
|---|---|
| `DELETE /api/crm/v1/people/{id}` | Behåll som mjuk borttagning |
| `POST /api/crm/v1/people/{id}/erase` | Art. 17-radering, gravsten, `person.raderad` |
| `POST /api/crm/v1/people/{id}/suppress` | Spärr, `kanal` och `orsak` i kroppen, `person.sparrad` |
| `DELETE /api/crm/v1/people/{id}/suppress` | Häv spärr (kräver orsak) |
| `GET /api/crm/v1/people/{id}/export` | Registerutdrag/portabilitet som JSON |
| `GET /api/crm/v1/suppressions?updated_since=` | Spärrar att föra in i källsystemet |
| `GET /api/crm/v1/erasures?updated_since=` | Gravstenar att radera i källsystemet |
| `POST /api/crm/v1/webhooks`, `GET`, `DELETE /api/crm/v1/webhooks/{id}` | Kundens mottagare, med hemlighet för signering |
| `GET /api/crm/v1/webhooks/{id}/deliveries` | Leveranslogg |

---

## 10. Jämförelse med det repot redan har

| Område | Finns [REPO] | Saknas för CRM:et |
|---|---|---|
| Rättslig grund | `crm_personer.rattslig_grund` (153:132, 144); intresseavvägning för kallmejl, utkast (`intresseavvagning_kallmejl.md`) | Grund per bolag när enskild firma; samtycke med tid och text |
| Art. 14 | Fot i kod, regel 4 (`utskicksfot.py`, `send_guard.py:336-356`) | Källa per person; `art14_informerad_at`; gallring av okontaktade prospekt |
| Art. 15/17 | `gdpr_radera.py`, bara e-post, bara skript | CRM-tabeller, telefon och orgnr som nycklar; API och UI |
| Art. 18 | `behandlingsbegransningar` (124), gallringen respekterar den (144), spegeln väntar på den (147) | CRM-vägarna frågar den inte; nyckel bara e-post |
| Art. 21.2-3 | `suppressions` (e-post, per tenant, 030); `samtal.py` `kontakta_inte`; `crm_*.kontakta_inte` | En gemensam spärr för alla kanaler; fortplantning ut |
| Gallring | `gallra_tenant` med två varv, radlås, kaskad, tak (138-147); `ss_gallringspolicy` (048) | CRM-tabellerna är inte anslutna (snajp-05:438); beslut om lagringstid saknas (`intresseavvagning_kallmejl.md:288`) |
| MFL 19 § | Enskilda firmor fälls före research (`forfilter.py:24-44`) | Fälls inte när orgnr saknas; undantaget för befintlig kund går inte att uttrycka |
| NIX | Enskilda firmor går aldrig till ringlistan (`CLAUDE.md` regel 15, 16) | NIX-tvätt; undantaget 6.3 för momsregistrerade näringsidkare; två månaders giltighet |
| Säkerhet och incident | `INCIDENT_RESPONSE.md`; `audit_logs` för admin (123) | Logg per API-nyckel; PUB-avtalets timgräns; registerförteckningens CRM-post |
| Avtal | PUB-utkast (`pub-avtal.md`), underbiträden på fyra ställen | CRM i PUB-avtalet (punkt 22); webhooks som kundens instruktion |

---

## 11. Öppna frågor

### Till jurist

- **J1.** Kräver MFL 19 § samtycke för e-post till en anställds personliga tjänsteadress
  hos ett aktiebolag, när marknadsföringen gäller bolagets verksamhet? Jag har inte
  hittat myndighetstext som avgör det.
- **J2.** Räcker art. 14.5 b (oproportionerlig ansträngning) för prospekt som lagras
  utan att kontaktas, eller måste de gallras inom en månad?
- **J3.** Är "offentliga företagsuppgifter" en tillräcklig källuppgift enligt
  art. 14.2 f, eller måste källan namnges (merinfo, allabolag, bolagets sajt)?
- **J4.** Är Snajp biträde även när Snajp tillhandahåller Iris-research och därmed väljer
  källorna? (EDPB 07/2020 om "väsentliga medel".)
- **J5.** Får den globala begränsningen (124) synas för andra kunder än den där
  begäran kom in, och vad ska PUB-avtalet säga om det?
- **J6.** Vem avgör om en person som raderats på egen begäran får synkas in igen:
  kunden som ansvarig eller Snajp?
- **J7.** Hur länge får rättighetsärenden och spärrposter sparas? Är tre år rätt för
  ärenden?
- **J8.** Gäller 19 § andra stycket (befintlig kund) när Snajp skickar för kundens räkning
  och kunden inte kan visa att opt-out erbjöds vid köpet?
- **J9.** Hur ska ett återförsäljaravtal med NIX formuleras i förhållande till PUB-avtalet?

### Till Anton

- **A1.** Ska CRM-tabellerna gallras av `gallra_tenant` med Snajps standardtider, eller
  bara på kundens instruktion? (Samma fråga som snajp-05:438.)
- **A2.** Ska Snajp tvätta mot NIX åt kunderna (återförsäljaravtal, cirka 5 000 kr plus
  13-17 öre per nummer), eller ska kunderna göra det själva?
- **A3.** Ska ringlistan ta enskilda firmor som uppfyller NIX-regel 6.3, eller behålla
  dagens totalspärr?
- **A4.** Får CRM-data någonsin nå Vertex AI (sammanfattningar på tidslinjen)? I så fall
  som kundval, och med registerförteckningen uppdaterad.
- **A5.** Ska spärrnyckeln sparas som hash?

---

## 12. Källor

Lag och förordning:

- Marknadsföringslag (2008:486), riksdagen.se:
  https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/marknadsforingslag-2008486_sfs-2008-486/
- Samma, lagen.nu (19-21, 31 §§): https://lagen.nu/2008:486
- Bokföringslag (1999:1078), lagen.nu (1 kap. 2 §, 5 kap. 7 §, 7 kap. 2 §):
  https://lagen.nu/1999:1078
- Lag (2002:562) om elektronisk handel, lagen.nu (8 §): https://lagen.nu/2002:562
- Dataskyddsförordningen i fulltext, IMY:
  https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/introduktion-till-gdpr/dataskyddsforordningen-i-fulltext/
- Dataskyddsförordningens skäl, IMY:
  https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/introduktion-till-gdpr/dataskyddsforordningen-i-fulltext/beaktandesatser/

IMY:

- Intresseavvägning som rättslig grund:
  https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/rattslig-grund/intresseavvagning/
- Personuppgifter (enskild firma, förnamn.efternamn@):
  https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/introduktion-till-gdpr/personuppgifter/
- De registrerades rättigheter:
  https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/de-registrerades-rattigheter/
- Tidsfrister: https://www.imy.se/privatperson/dataskydd/dina-rattigheter/galler-for-alla-rattigheterna/tidsfrister/
- Rätt att göra invändningar: https://www.imy.se/privatperson/dataskydd/dina-rattigheter/att-gora-invandningar
- Beslut H&M, DI-2020-10545, 2023-10-17:
  https://www.imy.se/globalassets/dokument/beslut/2023/beslut-tillsyn-hm-klagomal.pdf
- Anmäl personuppgiftsincident: https://e-tjanster.imy.se/report

EDPB:

- Guidelines 1/2024 om art. 6.1 f, version 2:
  https://www.edpb.europa.eu/system/files/2026-11/edpb_guidelines_202401_legitimateinterest_v2_en.pdf
  (inte läst i fulltext; innehållet ur sökresultat och konsultationsrapporten
  https://www.edpb.europa.eu/system/files/2026-11/report_public_consultation_edpb_guidelines_202401_legitimateinterest_v2_en.pdf)
- Guidelines 07/2020 om ansvarig och biträde:
  https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-072020-concepts-controller-and-processor-gdpr_en
- Guidelines 01/2022 om rätten till tillgång:
  https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-012022-data-subject-rights-right-access_en

Konsumentverket:

- Telefonförsäljning, regler för företag:
  https://www.konsumentverket.se/marknadsratt-foretag/telefonforsaljning-regler-for-foretag/
- Marknadsföringslagen för företag:
  https://www.konsumentverket.se/marknadsratt-foretag/marknadsforingslagen-for-foretag/

NIX och bransch:

- NIX-Telefon: https://www.nixtelefon.org/
- För företag (priser, två månader): https://www.nixtelefon.org/for-foretag
- Regler för spärregistret (undantag 6.1-6.3, punkt 7): https://www.nixtelefon.org/regler
- Lagar och bestämmelser: https://www.nixtelefon.org/lagar-bestammelser
- Kontakta och SWEDMA, Etiska regler för försäljning och marknadsföring över telefon
  till konsument, 2021-07-01: https://kontakta.se/upl/files/193291
- Realtid om falska NIX-tjänster för företag:
  https://www.realtid.se/bors-finans/teleskojare-lurar-smaforetag/

Regeringen:

- Förbud mot telefonförsäljning ska utredas, 2026-07-09:
  https://regeringen.se/pressmeddelanden/2026/07/forbud-mot-telefonforsaljning-ska-utredas/
- Uppdrag att granska brister vid telefonförsäljning, 2025-05:
  https://www.regeringen.se/pressmeddelanden/2025/05/uppdrag-att-granska-brister-vid-telefonforsaljning/

Repot (läst 2026-11-25 i worktree `snajp-crm-dd0d83`): `docs/JURIDIK_ATGARDER.md`,
`INCIDENT_RESPONSE.md`, `docs/intresseavvagning_kallmejl.md`,
`docs/registerforteckning.md`, `docs/pub-avtal.md`, `CLAUDE.md`,
`db/migrations/000_base_schema.sql`, `030_suppressions_tenant_scope.sql`,
`048_gallring.sql`, migration 124 och 138-147,
`20261125090000_153_crm_grund.sql`, `snajp-support/app/leads/forfilter.py`,
`utskicksfot.py`, `send_guard.py`, `samtal.py`, `snajp-support/app/api/crm_v1.py`,
`snajp-support/app/crm/synk.py`, `docs/crm/underlag/snajp-05-migrationer-invarianter-gdpr-test.md`.
