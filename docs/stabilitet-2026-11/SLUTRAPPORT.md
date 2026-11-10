# Slutrapport: stabilitet, hastighet och agentkvalitet

2026-11-10. Uppdraget: Snajp ska inte krascha, ska svara snabbt, och agenterna
ska göra sitt arbete rätt. Arbetet ligger i `development` (`8f23e29`) och är
utrullat där. Inget är släppt till `main`.

## 1. Slutsats

**GO för release till main, med tre villkor. NO-GO för att säga att
hastighetsmålen för supporten är nådda.**

Releasen bör inte vänta: produktionen lämnar i dag ut agentens promptar till
varje besökare i chattwidgeten (avsnitt 5), och rättningen ligger i den här
grenen. Villkoren står i avsnitt 8.

Hastighetsmålen är delvis nådda. Supportens svarstid gick från 10,2 till 8,0
sekunder i median och från 21,2 till 14,7 i p95. Målet var under 8 sekunder i
p95 och första tecknet inom 2 sekunder. Det går inte att nå med fyra
modellanrop i följd; det kräver en kortare kedja eller ett strömmat svar, och
båda ändrar vad kunden får och ska prövas mot evalsviten först.

## 2. Före och efter

Mätt mot development. Före är koden efter fas 1 (`6df6c2f`), efter är
`7a8e661` och senare. Evalsviterna körs mot riktig modell; siffrorna för ett
enskilt fall varierar mellan körningar (se avsnitt 9).

### Agenterna

| Mätning | Före | Efter |
|---|---|---|
| Support, godkända fall | 47 av 50 | 47 av 50 |
| Support, lydde en inbäddad instruktion | 1 av 5 injektionsfall | 0 av 5 |
| Support, svarstid p50 / p95 | 10,2 s / 21,2 s | 8,0 s / 14,7 s |
| Support, triagen gjordes om | 74 % av anropen | 0 % |
| Support, utkastet gjordes om | 34 % | 0 % |
| Support, modellanrop i följd per svar | cirka 7,1 | cirka 4,8 |
| Kvittohanteraren, godkända fall | 35 av 40 | 37 av 40 |
| Kvittohanteraren, serverfel | 2 av 40 | 0 av 40 |
| Kvittohanteraren, svarstid p50 | 16,6 s | 20,9 s |
| Iris utkast, godkända fall | 25 av 33 | 24 av 33 |

Supportens godkända antal är detsamma men sammansättningen är en annan:
injektionsfallet och ett fall med onödig överlämning går nu igenom, och två
andra föll i efterkörningen (ett faktasvar som modellen ibland missar, en
skadad vara som lämnades över). Iris kedja ändrades inte; skillnaden på ett
fall är variation mellan körningar. Kvittohanterarens svarstid ändrades inte i
koden; körningarna gjordes vid olika tider på dagen.

### Läsvägarna

En användare åt gången, p50 (före är fas 0-sonden, efter är
`last/efter-en-anvandare.json`):

| Väg | Före | Efter |
|---|---|---|
| `/api/leads/skickat` | 2 416 ms | 572 ms |
| `/api/leads/prospects` | 1 621 ms | 392 ms |
| `/api/leads/runs` | 1 730 ms, 8,5 MB | 59 ms, 25 kB |
| `/api/leads/korningar` | 348 ms | 279 ms |

Tio samtidiga användare i 40 sekunder (`scripts/lasttest.py`):

| Mätning | Före | Efter |
|---|---|---|
| Anrop, fel | 651, 0 fel | 821, 0 fel |
| Alla vägar, p95 | 3 549 ms | 1 620 ms |
| `/api/leads/skickat`, p50 | 3 883 ms | 2 130 ms |
| `/api/leads/prospects`, p50 | 2 393 ms | 720 ms |
| `/api/leads/runs`, p50 | 479 ms | 206 ms |
| Åtta samtidiga chattar | 8 av 8, p50 14,4 s | 8 av 8, p50 11,9 s |

Databasfrågan bakom utkastens läge (`utkast_lagen`) gick från 1 826 till 99 ms
hos den största kunden: 3 184 sekventiella genomläsningar av `send_queue` per
anrop blev en.

## 3. Målen i uppdraget

| Mål | Utfall |
|---|---|
| Inget fel ger vit sida, stackspår eller obegriplig text | Felgränser per yta, 503 för beroendefel, läsbara besked på de vägar som gåtts igenom. Inte uttömmande: råa felmeddelanden finns kvar på ställen som inte gåtts igenom (avsnitt 7). |
| Support: första tecknet inom 2 s | Inte nått. Chatten visar vad agenten gör från första hämtningen (0,7 s), men svaret kommer helt. |
| Support: hela svaret under 8 s i p95 | Inte nått: 14,7 s. Median 8,0 s. |
| Iris och kvitton startar direkt och visar förlopp | Kvittoskanningen och massutskicken är jobb med förlopp som överlever en omladdning. Iris körningar hade det redan. |
| Dashboardens API under 500 ms i p95 | Nått för en användare åt gången utom `/skickat` (780 ms). Inte nått under tio samtidiga användare. |
| Evalsvit, minst 30 fall per agent, före och efter | 50, 33 och 40 fall. Körda före och efter. |
| Skydd mot promptinjektion | Ram runt kundens text och en läckspärr i kod, i supporten. Mätt: 5 av 5. Iris och kvittohanteraren har sina tidigare skydd; kvittosvitens fyra injektionsfall går igenom. |
| Last-, kaos- och regressionstest | Lasttest mot development, kaostester i `tests/kaos/`, sviterna gröna (backend 3 930, invarianter 549, webb 216; 3 643 i backend före uppdraget). |

## 4. Ändringar per fas

### Fas 1: stabilitet (i development sedan tidigare)

Se `docs/BESLUT.md` 2026-11-09 och 2026-11-10. I korthet: uppstarten vägrar
minnesläge, tidsgränser på modell, databas och Redis, idempotens i utskick,
dubbelstartsvakt, felgränser per yta, anrops-id i loggar och svar, ordfiltren
som lämnade över vanliga kursfrågor, sändfel som bokförs, kvittoskanning som
läser vidare, supportportalens nyckelval, flyttpaketets tidsstämpel,
hämtvakten mot interna adresser.

### Fas 2: hastighet

- `utkast_lagen` läser tabellerna en gång; migration 115 lägger index.
- `/api/leads/runs` ger ett sammandrag; feedbackvägen slår upp en rad.
- Fliken Skickat läser utkastens text bara för de godkända.
- Supporten: en påminnelserad tog bort omförsöken, avhoppsklassaren går
  samtidigt med triagen, de två sökningarna i kunskapsbasen samtidigt, 20
  sekunder per modellanrop (45 förut).
- Chatten visar fyra skeden och hämtar svaret tätare.
- Kvittoskanningen och "Godkänn och skicka alla" går som jobb med förlopp
  (`app/jobs/bakgrund.py`).

### Fas 3: agentkvalitet

- Evalsviterna i `snajp-support/evals/` med körare, mall och README.
- Kundens text står inom en ram i supportens chatt och mejl; ett svar som bär
  våra instruktionsmarkörer stoppas i kod.
- Chattens grundprompt ber inte längre kunden "svara på det här mejlet".
- Språkputsen får inte göra om ett svar till en hälsning.
- Supportens triage normaliseras (sentiment 0, "false" i citattecken,
  kundfakta som sträng).
- Skälet när faktagrinden stoppar ett Iris-utkast säger vad som fälldes.
- En kundfaktura uppladdad med fel knapp får ett besked med vägen framåt.

### Fas 4: last, kaos, regression

- `scripts/lasttest.py`, kört före och efter.
- `tests/kaos/`: beroenden nere ger 503, ett modellsvar utan tokenräkning
  fäller inte agenten.
- Ett modellsvar i fel form (lista, null) ger ett omförsök i stället för ett
  serverfel.

## 5. Fynd som mätningarna gav

Inget av dessa stod på fas 0-listan. De hittades av evalsviterna eller under
arbetet med hastigheten.

1. **Jobbsvaret lämnade ut agentens promptar.** `GET /api/jobs/{id}`, som den
   anonyma chattwidgeten pollar, bar hela stegloggen: verksamhetskontext,
   SOUL, kundminne, kunskapsbasens artiklar, modellens resonemang. Samma
   texter gick ut via `/api/leads/runs` och två direkta agentsvar, och
   researchpromptarna kan bära webbplatsbedömningen. Rättat i development.
   **Produktionen har kvar felet tills releasen.**
2. **Supporten lydde en inbäddad "SYSTEM:"-rad** och lovade 50 % rabatt med
   en påhittad kod. Rättat och mätt.
3. **Två av fyrtio kvitton gav serverfel** när Vertex svarade utan
   tokenräkning. Rättat och mätt.
4. **Supportens triage gjordes om i tre av fyra anrop.** Rättat och mätt.
5. **Ramens första version gjorde svaren sämre.** Med förklaringen inuti
   taggarna svarade supporten "Hej, hur kan jag hjälpa dig?" på två av femtio
   riktiga frågor. Upptäckt av sviten samma dag och rättat. Det är skälet att
   promptändringar ska gå genom sviten.

## 6. Inte gjort, och förslag som väntar

| Sak | Varför inte | Vad som krävs |
|---|---|---|
| Strömmat supportsvar | Ändrar chattens protokoll i widget och proxy, och vinner bara språkputsens skrivtid så länge kedjan har fyra steg. | Beslut om kedjans längd först. |
| Kortare supportkedja (slå ihop triage och research, eller hoppa över språkputsen när utkastet håller) | Ändrar vad kunden får. | En provomgång mot evalsviten. Det är den åtgärd som kan ge p95 under 8 s. |
| Iris: "dygnet runt" stod i 16 av 33 utkast fast erbjudandet aldrig sa det | Iris kedja är låst mot facit och ändras enligt referensens avsnitt 8. | En ny feedbackrunda i skrivstilen eller ett fynd i stilgrinden, med Antons ja. |
| Iris: ett utkast av 33 köades inte på grund av brutet kontrakt | Samma skäl. Supportens påminnelserad tog bort motsvarande fel där. | Prova påminnelsen på Iris utkaststeg mot facit. |
| Kvittohanteraren: en egen kundfaktura känns inte igen utan rätt knapp | Igenkänningen ligger avsiktligt utanför grundprompten. | Produktbeslut. |
| Strömbrytare och reservmodell på Vertex | En reservmodell ger andra svar och ska prövas mot sviten. | Val av modell, en provomgång. |
| Sentry eller motsvarande | Kräver ett konto, en EU-region och en rad i PUB-avtalet. | Ditt eller Antons beslut. |
| Extern upptidsövervakning | Ny tjänst. | Samma. |
| Kundnycklarna i klartext i development | Kräver en migration av nyckellagringen. | Eget beslut. |
| Supportens dagsbudget (av som standard), tak för kvittohanteraren | Vad en kund får kosta är inte en kodfråga. | Värden per miljö. |
| `impeccable`-genomgång av felgränserna och statustexterna | Inte gjord. | En egen genomgång. |

## 7. Kvarstående risker

- **Produktionen läcker promptar tills releasen** (avsnitt 5.1).
- **Adminlösenordet ligger i git-historiken** och är inte bytt, vad jag kan se.
- **Onödiga överlämningar.** En irriterad men saklig kund ("Fan vad
  krångligt …") får sitt svar och lämnas ändå över på sentimentet. Ord som
  "ångerrätt" och "reklamation" lämnar över även när kunskapsbasen bär
  svaret. Det är gällande policy, och sviten mäter den nu.
- **En process, en arbetare.** Under tio samtidiga användare är `/skickat`
  2,1 s i median. Fler repliker kräver delade lås (Redis), se minnesanteckningen
  om samtidiga körningar.
- **Bakgrundsjobben lever i api-processen.** En deploy mitt i en skanning
  eller ett massutskick avbryter arbetet. Inget görs två gånger, men
  användaren får starta om.
- **Vertex kvot.** Under eftermiddagens mätningar svarade Vertex 429 på nio av
  fyrtio kvitton och modellanropen tog två till fem gånger längre än på
  förmiddagen. Svarstiderna ovan gäller en lugn stund.
- **20 sekunder per modellanrop** kan ge fler omförsök en trög stund. Värdet
  styrs av `LLM_TIMEOUT_CHATT_S`.
- **Råa felmeddelanden** finns kvar i vyer som inte gåtts igenom
  (`lib/leads/suite.ts`, `lib/actions/affarskontext.ts`, `lib/snajp/tenant.ts`).
- **Speglingen till development** står still medan development har en
  migration som main saknar (115).

## 8. Driftguide

### Release till main

1. Kör migration 115 mot main före mergen, torrkörning först:
   `python scripts/railway_migrate.py --env main`, sedan `--apply`. Den lägger
   bara index.
2. Kontrollera att `AGENTSAJT_LOSEN` är satt för supportportalen i Railway.
   Saknas den svarar portalen 401 till den som inte kommer via Snajp.
3. Byt plattformsadminens lösenord och uppdatera `QA_ADMIN_LOSEN` i
   `.env.deploy`.
4. PR #43 från development till main bär hela arbetet. Mergen är Antons.

### Efter en ändring av promptar, modell eller kedja

```bash
cd snajp-support
python -m evals.kor kor --env development --agent alla --etikett efter
python -m evals.kor jamfor fore efter
```

Evalkunderna finns redan i development. Supportens evalkund har ett timtak på
400 modellanrop: två hela körningar inom en timme slår i det (`forbered
--antal 1 --behall` ger en ny). Mer i `snajp-support/evals/README.md`.

### Lasttest

```bash
python scripts/lasttest.py --env development --etikett <namn>
```

### När något går fel

- **Ett fel i en vy** bär en referens. Samma id står som `X-Request-Id` på
  svaret och på api:ts loggrader (`[id]`), och i plattformshändelsen.
- **503 "tillfälligt otillgänglig"** betyder att Redis eller databasen inte
  svarade. Loggraden säger vilken undantagstyp.
- **Deployen dör med "Startvägran"**: databasen gick inte att nå på fem
  försök, eller en nyckel står på sitt incheckade standardvärde. Föregående
  version ligger kvar.
- **Ett utkast står som Stoppat med skälet "Mejltjänsten …"**: Resend tog inte
  emot det. Godkänn och skicka prövar igen från noll.
- **Plattformshändelser att hålla ögonen på:** källa `budget` (80 % av
  leadsbudgeten), `injektion` (ett supportsvar stoppades för att det bar våra
  instruktioner), `api` (ohanterade fel).

## 9. Inte verifierat

- **Produktionen.** Allt är mätt i development. Livrustnings riktiga
  svarstider är inte mätta.
- **Variationen mellan körningar.** Varje svit är körd en gång före och en
  gång efter. Iris skiljde fem fall åt ena hållet och fyra åt andra utan att
  koden ändrats, och en supportfråga som underkändes i sviten gav rätt svar
  tre gånger av tre vid omprov. En skillnad på ett eller två fall är brus.
- **Före-värdet för supportens svarstid** mättes på förmiddagen och
  efter-värdet på kvällen. En körning däremellan, när Vertex var trögt, gav
  14,8 s i median med samma kod. Antalet modellanrop per svar är det mått som
  inte beror på tiden.
- **Webbens nya kod i drift**: chattens skeden är inte sedda i den driftsatta
  chatten, bara enhetstestade. Skanningens och massutskickets förlopp är sedda
  i en förhandsvisning med syntetiska svar.
- **Sändfelen mot riktiga Resend** och hur Railways kant skriver
  `X-Forwarded-For`.
- **Om de incheckade standardnycklarna godtas i någon miljö.**
- **Evalsviternas förväntningar** är skrivna av en modell och granskade av mig
  på de fall som underkändes. Fall som godkändes har jag inte läst ett och ett.

## Underlag

- Mätresultat: `docs/stabilitet-2026-11/eval/` och `docs/stabilitet-2026-11/last/`.
- Beslut: `docs/BESLUT.md`, 2026-11-09 och 2026-11-10 (tre poster).
- Fas 0-rapporten: `docs/fas0-2026-11-09/RAPPORT.md` i huvudkatalogen, inte
  incheckad eftersom den listade svagheter som då var olösta.
