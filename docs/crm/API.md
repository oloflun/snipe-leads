# Snajp CRM API, version 1

Guide för den som kopplar ett eget system till Snajp CRM. Den fullständiga
specifikationen är [openapi.json](openapi.json) (OpenAPI 3.1), som också går att
hämta med en nyckel från `GET /api/crm/v1/openapi.json`.

Bas-URL: `https://<api-värden>/api/crm/v1`. Allt är JSON i UTF-8 om inget annat sägs.

## Kom igång: synka in era kunder

Tre steg. Efter dem finns era kunder i Snajp, och Iris hämtar dem aldrig som leads.

**1. Skapa en nyckel** i Snajp under CRM › Utvecklare. Välj omfång (se nedan). Nyckeln
visas en gång.

**2. Skapa en anslutning**, en per system ni synkar från. Systemet avgör vilken
fältmappning som gäller från början.

```bash
curl -X POST "$BAS/connections" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"name": "hubspot", "system": "hubspot", "missing_records": "mark_former_customer"}'
```

**3. Skicka kunderna**, i källsystemets eget format, högst 500 per anrop.

```bash
curl -X POST "$BAS/sync/companies" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -H "Idempotency-Key: natt-2026-11-25-sats-1" \
  -d '{"connection": "hubspot", "items": [
        {"id": "901", "updatedAt": "2026-11-20T08:00:00Z",
         "properties": {"name": "Byggarna Berggren AB", "orgnr": "556036-0793",
                        "phone": "08-123 456 78", "city": "Stockholm", "lifecyclestage": "customer"}}]}'
```

Svaret säger vad som hände med varje post:

```json
{"run": {"id": "…", "status": "completed", "counts": {"total": 1, "created": 1, "updated": 0,
         "unchanged": 0, "skipped": 0, "conflicts": 0, "removed": 0}, "errors": []},
 "counts": {"total": 1, "created": 1, "updated": 0, "unchanged": 0, "skipped": 0, "conflicts": 0, "removed": 0},
 "items": [{"index": 0, "status": "created", "id": "…", "external_id": "901"}]}
```

Skicka samma sats igen och svaret blir `unchanged`. Synken är gjord för att köras om.

CSV går också, med rubrikrad och semikolon, komma eller tabb som skiljetecken:

```bash
curl -X POST "$BAS/sync/companies?connection=export" -H "X-API-Key: $NYCKEL" \
  -H "Content-Type: text/csv; charset=utf-8" --data-binary @kunder.csv
```

## Nycklar och omfång

Nyckeln skickas i `X-API-Key`. En nyckel med omfång når bara det här API:t, ingenting
annat i Snajp.

| Omfång | Ger |
|---|---|
| `crm:las` | läsa bolag, personer, affärer, uppgifter, anteckningar, aktiviteter, bilagor, anslutningar och synkkörningar |
| `crm:skriv` | skapa, ändra, radera och återställa allt det, och ändra affärens steg |
| `crm:synk` | starta synkkörningar och skicka satser |
| `crm:admin` | skapa och ändra anslutningar och fältmappning |

En nyckel som dras in slutar gälla inom 30 sekunder.

## Hur en post känns igen

```
källans id  →  organisationsnummer  →  domän  →  namn
```

1. **Källans id.** Samma post i ert system är samma post i Snajp, också efter ett namnbyte.
2. **Organisationsnumret.** Det är unikt per kund hos Snajp. Två källor som beskriver
   samma bolag hamnar på samma post.
3. **Domän och namn** används bara för bolag utan organisationsnummer, och bara när exakt
   en post matchar. Två bolag som heter "Bygg AB" slås aldrig ihop på namnet, och
   `gmail.com` eller `telia.com` räknas aldrig som en bolagsdomän.

Personer känns igen på källans id och sedan på e-postadressen. Skicka bolagen före
personerna: en person knyts till sitt bolag genom bolagets id i källsystemet.

## Full synk

En enstaka sats kan inte veta vad som försvunnit ur källan. Det kan bara en full synk:

```bash
RUN=$(curl -s -X POST "$BAS/sync/runs" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"connection": "hubspot", "mode": "full"}' | jq -r .id)
# en eller flera satser
curl -X POST "$BAS/sync/runs/$RUN/companies" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" -d @sats1.json
curl -X POST "$BAS/sync/runs/$RUN/people"    -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" -d @personer.json
curl -X POST "$BAS/sync/runs/$RUN/complete"  -H "X-API-Key: $NYCKEL"
```

När körningen avslutas avgör anslutningens `missing_records` vad som händer med poster
som källan inte längre har:

| Värde | Betyder |
|---|---|
| `keep` (standard) | ingenting |
| `mark_former_customer` | kunder som saknas blir tidigare kunder |
| `delete` | posterna raderas (går att återställa i 30 dagar) |

En full synk utan en enda post misslyckas med `tom_full_synk` i stället för att tömma
registret: ett tomt svar från källan är oftare ett fel än en tömd kundstock.

Körningen går att följa medan den pågår och efteråt: `GET /sync/runs/{id}` ger räknarna
och de fel som uppstått. Den syns också i Snajp under CRM › Synk.

Har körningen fel som behöver rättas går hela rapporten vidare till Snajps support, och
`support` på körningen säger när (`forwarded_at`). `support.ticket` sätts nu av sig självt till
supportärendets nummer, och en anslutning som faller igen med ett ärende öppet får samma
nummer. Poster som hoppas över med flit, som privatpersoner, är inga fel och går inte vidare.

## Fältmappning per system

Varje system har en standardmappning: `GET /connections/systems` visar dem alla.
Organisationsnumret är nästan aldrig ett standardfält i utländska system, så peka ut ert:

```bash
curl -X PATCH "$BAS/connections/hubspot" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"mapping": {"bolag": {"orgnr": "properties.swedish_org_no",
                             "extra": {"kundnummer": "properties.customer_no"}}}}'
```

Det ni anger läggs ovanpå standarden, fält för fält. En källa är en sökväg
(`properties.name`), en lista av sökvägar där den första med ett värde gäller, eller ett
objekt med `fran`, `uppslag`, `standard`, `fast` eller `sammanfoga`. Sökvägar går genom
listor med index (`addresses.0.city`) eller filter (`addresses[type=Visit].city`).

Hur ett värde tolkas avgörs av fältet det hamnar i, inte av mappningen: ett
organisationsnummer kontrolleras alltid, ett telefonnummer görs alltid om till E.164.

Bara de egna fält ni räknar upp under `extra` följer med. Ingenting annat i posten sparas.

Prova en mappning utan att något skrivs:

```bash
curl -X POST "$BAS/connections/hubspot/preview" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"object": "company", "items": [ … ], "mapping": {"bolag": {"orgnr": "properties.swedish_org_no"}}}'
```

Systemen med standardmappning: `generisk`, `hubspot`, `pipedrive`, `lime`, `lime_go`,
`upsales`, `salesforce`, `twenty`, `superoffice`, `dynamics`, `fortnox`, `visma`.

## När källan och Snajp säger olika

Anslutningens `conflict_rule` avgör, fält för fält:

| Värde | Betyder |
|---|---|
| `source_wins` (standard) | källans värde gäller |
| `snajp_wins` | ett fält någon ändrat för hand i Snajp står kvar |
| `newest_wins` | det som ändrades senast gäller. Kräver en ändringstid från källan |

Ett fält som källan inte skickar rörs aldrig. En sats med bara namn och telefon tömmer
inte adressen. Fält där Snajps värde stod kvar redovisas som `kept_fields` på posten.

## Svenska format

| Fält | In | Lagras och lämnas ut som |
|---|---|---|
| Organisationsnummer | `556036-0793`, `5560360793`, `16556036-0793`, `SE556036079301` | `556036-0793`. Kontrollsiffran räknas |
| Telefon | `08-123 456 78`, `+46 (0)70 123 45 67`, `0046701234567` | `+46812345678` (E.164) |
| Postnummer | `11122`, `SE-111 22` | `111 22` |
| Datum | `2026-12-31`, `31/12/2026`, ISO med klockslag, epoktid | `2026-12-31` |
| Belopp och tal | `1 234 567 kr`, `1.234,50`, `1,234.00` | heltal |

En enskild firmas organisationsnummer är ägarens personnummer, och personnummer sparas
inte i Snajp. Bolaget skapas ändå, utan nummer och med `sole_proprietor: true`, och känns
igen på domän eller namn. I en sats redovisas det som fältfelet `orgnr_ar_personnummer`.

Ett fält som inte går att tolka hoppas över, inte posten: en kund med ett felskrivet
telefonnummer blir fortfarande en kund. Felet står i svaret som `field_errors` och sparas
på körningen.

## Privatpersoner

Snajp är ett verktyg för företagsförsäljning. En post som källan märker som privatperson
(`Type: PRIVATE` i Fortnox, `IsPrivatePerson` i Visma, eller det fält ni pekar ut som
`privatperson` i mappningen) hoppas därför över, med `reason: privatperson`.

Vill ni ha privatkunderna i registret slår ni på det på anslutningen:

```bash
curl -X PATCH "$BAS/connections/fortnox" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"include_private_persons": true}'
```

De sparas då som kunder med `private_person: true`. Personnumret sparas aldrig, och posten
är alltid `do_not_contact`: den lämnas utanför varje utskick, lista och Iris-körning, och
det går inte att ändra på posten.

## Kunder som Iris inte hämtar

Ett bolag i ert register hämtas inte som lead. Har bolaget organisationsnummer är det
numret som avgör, så att ett annat bolag med samma namn inte utesluts. En tidigare kund
(`relation: former_customer`) är fri att bearbeta igen, om inte posten är `do_not_contact`.

Ett bolag som sagt nej, eller som inte passar, märks `relation: not_relevant` (ej aktuell).
Det skiljer det från ett prospekt, och till skillnad från en tidigare kund står det kvar
bland de bolag Iris inte hämtar. Synken översätter källornas motsvarighet dit: `notinterested`
och `declined` i Lime, `disqualified` i Upsales, och värdena `ej aktuell` och `not_relevant`
i en egen fil. Filtrera med `GET /companies?relation=not_relevant`.

## Personens källa (GDPR artikel 14)

En person bär varifrån uppgiften om personen först kom, och när:

| Fält | Värde |
|---|---|
| `source_type` | `company_website` (bolagets webbplats), `registry` (ett register), `customer_provided` (ni har själva fått uppgiften av personen), `sync` (synken), `manual`, `other`, eller `null` när den inte är känd |
| `source_name` | källan med namn: webbadressen, registret eller anslutningen. Högst 300 tecken |
| `collected_at` | när uppgiften samlades in (ISO 8601) |

`source` är något annat: vilken väg posten kom in i Snajp (`manuell`, `api`, `synk`).

En person som skapas genom synken utan egen uppgift om källan får `source_type: sync`,
anslutningens namn som `source_name` och dagens tid. En person som skapas genom API:t eller
appen får dagens tid, men `source_type` lämnas tom om ni inte anger den: det ska gå att se
vilka som saknar källa. Peka ut källan i mappningen med målfälten `kalla_typ`, `kalla_namn`
och `insamlad_at`. En senare synk skriver aldrig över en källa som redan står; den fyller
bara ett tomt fält. Med API:t går källan att rätta som vilket fält som helst.

`GET /people?source_type=company_website` filtrerar på källan och
`GET /people?missing_source=true` ger personerna som saknar den. API:t tar bara värdena i
tabellen, exakt så som de står där. Varje annat värde avvisas med `invalid_fields` och
fältkoden `kalltyp_okand`, också ett svenskt namn eller versaler. Synkens mappning är
mildare: där tolkas också de svenska namnen, och ett okänt värde tappar bara fältet. Får en
ny person ingen giltig källtyp ur synken blir källan `sync` med anslutningens namn, också
när källan skickade ett eget `kalla_namn`, så att typ och namn alltid hör ihop.

## Läsa tillbaka och hålla en kopia i fas

```bash
curl "$BAS/companies?sort=updated&include_deleted=true&updated_since=2026-11-24T00:00:00Z&limit=500" \
  -H "X-API-Key: $NYCKEL"
```

Följ `next_cursor` tills den är `null`, och börja nästa gång från tidpunkten för er
senaste läsning. Raderade poster bär `deleted_at` och ska tas bort hos er också.

`sort=updated` går äldst först, för den som synkar ut. `sort=-updated` ger det senast
ändrade först, och `sort=name` bokstavsordning.

### Ändringsflödet

Ett flöde för allt, i den ordning det hände:

```bash
curl "$BAS/changes?cursor=0&limit=1000" -H "X-API-Key: $NYCKEL"
```

```json
{"data": [{"seq": 4117, "object": "company", "id": "…", "type": "updated",
           "fields": ["phone", "address.city"], "source": "synk", "actor": "anslutning:hubspot",
           "at": "2026-11-26T09:14:02+00:00"}],
 "next_cursor": 4117}
```

Läs tills listan är tom och spara `next_cursor`. Samma markör igen ger bara det som hänt
sedan dess. `type` är `created`, `updated`, `deleted`, `restored` eller `purged` (posten är
tömd för gott), och för en spärr (`object: suppression`) `created` eller `lifted`. Flödet säger vilken post och vilka fält som ändrades, inte värdena: hämta
posten för dem. `GET /companies/{id}/history` och `/people/{id}/history` ger samma
händelser för en enda post, nyast först.

## Webhooks

Vill ni hellre att Snajp säger till, registrera en adress:

```bash
curl -X POST "$BAS/webhooks" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"url": "https://ert-system.se/snajp", "events": ["company.created", "company.updated"]}'
```

Svaret bär `secret`, en enda gång. `events` är valfritt, utan det får ni allt.
`GET /webhooks/events` räknar upp händelserna: `company.*`, `person.*`, `deal.*`, `task.*`,
`note.*`, `activity.*` och `attachment.*` med `created`, `updated`, `deleted`, `restored` och
`purged`, `suppression.created` och `suppression.lifted` (se Spärren nedan), och
`sync.completed` när en synk avslutats. En bilagas händelse bär filens uppgifter, aldrig
själva filen.
Webhooks kräver omfånget `crm:admin` och en publik https-adress.

Varje leverans är ett `POST` med händelsen som JSON:

```json
{"id": "<leveransens id>", "type": "company.updated", "created_at": "2026-11-26T09:14:02+00:00",
 "data": {"object": "company", "id": "…", "record": { … hela posten … }}}
```

**Personer går ut tunna.** En händelse om en person, och om ett bolag som är en enskild
firma eller en privatperson, bär aldrig posten. Den bär vilken post, vad som hände, när och
namnen på fälten som ändrades:

```json
{"id": "<leveransens id>", "type": "person.updated", "created_at": "2026-11-27T10:02:11+00:00",
 "data": {"id": "…", "object": "person", "type": "person.updated",
          "occurred_at": "2026-11-27T10:02:11+00:00", "fields": ["phone", "title"]}}
```

Hämta posten med `GET /people/{id}` (eller `/companies/{id}`) när ni behöver värdena. Skälen:
en webhook som av misstag går till fel adress läcker då bara ett id, och har personen hunnit
raderas eller begränsas efter händelsen respekteras det när ni hämtar, i stället för att en
gammal kopia redan ligger hos er. Ett vanligt bolag bär hela posten som förut.

**Kontrollera signaturen.** Rubriken `X-Snajp-Signature: t=<unixtid>,v1=<hex>` bär en
HMAC-SHA256 över `"{t}.{kroppen}"` med er hemlighet. Räkna om den på den råa kroppen,
jämför i konstant tid och avvisa anrop som är äldre än fem minuter:

```python
import hashlib, hmac, time

def akta(hemlighet: str, rubrik: str, kropp: bytes) -> bool:
    delar = dict(d.split("=", 1) for d in rubrik.split(","))
    vantat = hmac.new(hemlighet.encode(), f"{delar['t']}.".encode() + kropp, hashlib.sha256).hexdigest()
    return hmac.compare_digest(vantat, delar["v1"]) and abs(time.time() - int(delar["t"])) < 300
```

**Svara snabbt.** Ett svar med status 2xx inom tio sekunder är en lyckad leverans. Allt
annat försöks igen efter 1, 5 och 30 minuter och 2, 6 och 24 timmar. Gör arbetet efter att
ni svarat, och tåla att samma leverans kommer två gånger: `X-Snajp-Delivery` är dess id.

**Följ leveranserna.** `GET /webhooks/{id}/deliveries` visar varje leverans med försök,
statuskod och fel i 30 dagar. `POST /webhooks/{id}/deliveries/{leverans}/retry` skickar om
en, och `POST /webhooks/{id}/test` skickar en `ping`. En webhook som misslyckats tjugo
leveranser i rad stängs av (`active: false`, `disabled_reason: for_manga_fel`). Slå på den
igen med `PATCH` när mottagaren är uppe.

## Spärren

En invändning mot direktmarknadsföring (GDPR artikel 21) gäller i varje kanal. Spärren är
en lista per arbetsyta över e-postadresser, domäner, telefonnummer och organisationsnummer
som inte får kontaktas, med kanal, orsak och datum. Snajps mejlutskick, uppföljningar och
kampanjer stoppas i sändögonblicket: på adressen, på domänen och på leadets
organisationsnummer, vilken adress leadet än bär. Ringlistan och återkopplingen tappar
spärrade nummer och organisationsnummer, och en provkörnings ringlista under Listor skrivs
utan dem.

```bash
curl -X POST "$BAS/suppressions" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"channel": "all", "kind": "email", "value": "vd@bolaget.se", "reason": "objection"}'
```

| Fält | Värden |
|---|---|
| `channel` | `email`, `phone` eller `all` (varje kanal) |
| `kind` | `email`, `domain`, `phone` eller `org_number`. E-post och domän hör till `email` eller `all`, telefon till `phone` eller `all`. Ett organisationsnummer spärrar bolaget i vilken kanal som helst |
| `value` | sparas normaliserat: e-post och domän i gemener, telefon i E.164, organisationsnummer `NNNNNN-NNNN`. En enskild firmas nummer är ett personnummer och tas inte emot |
| `reason` | `objection` (artikel 21), `unsubscribe`, `nix`, `customer_request`, `bounce`, `other` |
| `note` | valfri, högst 500 tecken. Skickas aldrig i en webhook och skrivs aldrig i en logg |
| `source` | `app`, `api`, `outcome` (utfallet kontakta inte), `import`, `sync` |

Svaret är `201` med spärren, eller `200` med den som redan gäller för samma kanal, slag och
värde. En domänspärr stoppar varje adress på domänen, men inte underdomäner.

- `GET /suppressions` listar spärrarna, senast lagd först, med `channel`, `applies_to`,
  `reason`, `q` (del av värdet; ett organisationsnummer hittas både som `556036-0793` och
  `5560360793`), `limit`, `cursor`, `include_lifted` och `only_lifted`.
  - `channel` ger exakt den kanalens spärrar. `applies_to=email` eller `applies_to=phone`
    ger spärrarna som stoppar kanalen: dess egna och de i `all`. En adress spärrad i `all`
    står alltså med under `applies_to=email`. Båda samtidigt ger `422 invalid_parameter`.
  - `only_lifted=true` ger bara de hävda, senast hävd först, med samma `limit`, `cursor` och
    `next_cursor`. `include_lifted` har då ingen betydelse.
- `DELETE /suppressions/{id}` häver spärren (`204`). Den står kvar med `lifted_at` och
  `lifted_by` som bevis, men stoppar ingenting. Att häva igen ändrar ingenting. Ett id som
  inte finns, eller inte är ett id, ger `404 suppression_not_found`.
- `POST /suppressions/import` lägger många i ett anrop, högst 10 000. Så laddar ni upp
  utfallet av er egen NIX-tvätt:

```bash
curl -X POST "$BAS/suppressions/import" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"channel": "phone", "reason": "nix", "values": ["070-123 45 67", "08-555 666 77", "123"]}'
```

```json
{"added": 2, "already_blocked": 0, "invalid": [{"index": 2, "code": "telefon_saknar_landskod"}]}
```

`added`, `already_blocked` och antalet i `invalid` är tillsammans antalet värden ni skickade.
En dubblett i samma anrop räknas som redan spärrad, och `invalid` säger platsen och skälet,
aldrig värdet. Utan `kind` är ett värde med @ en e-postadress, och annars en domän i kanalen
`email` och ett telefonnummer i `phone` och `all`.

**Är kontakten spärrad?** Fyra källor spärrar, och kontrollen läser dem tillsammans:

```bash
curl -X POST "$BAS/suppressions/check" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"channel": "phone", "phone": "070-123 45 67", "org_number": "556036-0793"}'
```

```json
{"blocked": true, "sources": ["suppression_list", "lead"], "suppression_ids": ["…"]}
```

| `sources` | Källan |
|---|---|
| `suppression_list` | spärrlistan ovan, också domän- och `all`-spärrar |
| `record` | ett bolag eller en person märkt `do_not_contact` (varje privatperson är det), eller en person hos ett sådant bolag |
| `unsubscribed` | adressen har avregistrerat sig från era utskick (bara `email`) |
| `lead` | ett lead hos Iris på samma adress, organisationsnummer eller telefonnummer har bett att slippa kontakt (till exempel utfallet Kontakta inte på ringlistan). Numret jämförs tolkat, så `070-123 45 67`, `+46701234567` och `0046701234567` är samma nummer. Står flera nummer i leadets telefonfält gäller det första, samma nummer som ringlistan spärrar |

`channel: all` frågar om något alls spärrar, i någon kanal. Svaret säger vilken källa som
spärrade, aldrig vad den visste. Ingenting kopieras mellan källorna: `do_not_contact` på en
post läses från posten. Utfallet `do_not_contact` på ett bolag (`POST
/companies/{id}/outcome`) lägger däremot spärrar i alla kanaler för bolagets e-post,
telefon och organisationsnummer, så att invändningen står kvar med datum också om posten
ändras.

Läsning och kontrollen kräver `crm:las`, att lägga, importera och häva `crm:skriv`.
`suppression.created` och `suppression.lifted` går ut som webhooks och står i
ändringsflödet (`object: suppression`). Händelsen bär `id`, `channel`, `kind`, `reason`,
`source`, `created_at` och `lifted_at`, aldrig `value` eller `note`: hämta spärren med
`GET /suppressions` om ni behöver adressen.

## Affärer, uppgifter, anteckningar, aktiviteter och bilagor

Det som händer med ett bolag bor bredvid det. Alla fem läses och skrivs som bolagen: samma
listparametrar (`limit`, `cursor`, `sort`, `q`, `include_deleted`, `only_deleted`), samma
papperskorg i 30 dagar, samma `restore`, och varje skrivning står i `GET /changes`.

Kopplingarna heter `company_id`, `person_id` och `deal_id` (en bilaga har dessutom `note_id`),
och varje lista filtrerar på dem. En koppling ska peka på en levande post hos er: annars
`company_not_found`, `person_not_found`, `deal_not_found` eller `note_not_found`.

### Affärer och tavlan

```bash
curl -X POST "$BAS/deals" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"name": "Takbyte Berggren", "company_id": "…", "amount": 125000, "expected_close_date": "2026-12-31"}'
```

`amount` är hela kronor (hela enheter av `currency`, som är `SEK` om inget annat sägs). En ny
affär hamnar sist i det första öppna steget om ni inte anger `stage_id`.

Stegen är era egna. Första gången de läses (`GET /deal-stages`) får ni en svensk standard:
Ny (10 %), Kvalificerad (25), Möte bokat (40), Offert skickad (60), Förhandling (80), Vunnen
(100) och Förlorad (0). Byt namn med `PATCH`, lägg till med `POST`, ordna om med
`POST /deal-stages/reorder` och alla stegens id i den nya ordningen. Två regler håller tavlan
användbar: ett steg med affärer i går inte att ta bort (`stage_in_use`, också om affärerna
ligger i papperskorgen), och det finns alltid minst ett öppet, ett vunnet och ett förlorat steg
(`stage_required`).

`GET /deals/board` ger hela tavlan: stegen i ordning, var och ett med sina affärer i kortens
ordning, `count` och `amount_total` (`amount_by_currency` håller isär valutorna). Flytta ett
kort med

```bash
curl -X POST "$BAS/deals/$ID/move" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"stage_id": "…", "before_id": "…"}'
```

`before_id` eller `after_id` är kortet det ska stå intill; utan någon av dem hamnar det sist.
När en affär når ett vunnet eller förlorat steg sätts `closed_at`, och flyttas den tillbaka
till ett öppet steg nollas den. `GET /deals/{id}/history` visar affärens händelser.

Varför en affär förlorades anges ur en lista, så att det går att räkna på:
`lost_reason_code` är `price`, `competitor`, `timing`, `no_need`, `no_budget`, `no_response`
eller `other`. Fritexten `lost_reason` står kvar som reserv och får sättas med vilken kod som
helst. Ett annat värde, också ett svenskt namn som `pris` eller versaler som `PRICE`, avvisas
med `invalid_fields` och fältkoden `forlustorsak_okand`, och
`null` tömmer koden. `GET /deals?lost_reason_code=price` ger affärerna som förlorades på
priset, och tidslinjens `deal_closed` bär koden i `data.lost_reason_code`.

### Uppgifter

En uppgift får stå fri eller kopplas till bolag, person och affär. `status` är `todo`,
`in_progress` eller `done`, och `completed_at` sätts när den blir `done`. `sort=due` ger den
som förfaller först överst och de utan dag sist; `status`, `owner` och `due_before` filtrerar.
Tider lagras och lämnas ut i UTC.

### Anteckningar och aktiviteter

En anteckning (`title`, `body`, `pinned`) och en loggad aktivitet (`type`: `call`, `meeting`,
`email`, `visit` eller `other`, med `subject`, `body`, `occurred_at`, `duration_minutes` och
`outcome`) hör alltid till något: utan koppling svarar API:t `target_required`. En anteckning
är högst 20 000 tecken.

### Bilagor

```bash
curl -X POST "$BAS/attachments" -H "X-API-Key: $NYCKEL" \
  -F "file=@offert.pdf;type=application/pdf" -F "company_id=…"
```

Högst 10 MB per fil (`file_too_large`) och 500 MB per arbetsyta, papperskorgen medräknad
(`storage_quota_exceeded`). En raderad fil räknas tills papperskorgen töms efter 30 dagar;
radera med `permanent=true` för att frigöra platsen direkt. Tillåtna typer är pdf, png, jpeg, webp, gif, txt, csv, docx, xlsx
och pptx, och den angivna typen ska passa filändelsen (`file_type_not_allowed`). Filnamnet
rensas från sökvägar och styrtecken.

Listor och `GET /attachments/{id}` bär bara filens uppgifter. Själva filen hämtas från
`content_url` (`GET /attachments/{id}/content`), alltid som nedladdning och aldrig sparad i
en mellanlagring.

### Töms ett bolag, en person eller en affär

Raderas ett bolag, en person eller en affär för gott (`permanent=true`, eller efter 30 dagar
i papperskorgen), töms också anteckningar, aktiviteter och bilagor som pekar på posten: de kan
bära personuppgifter. Affärer och uppgifter är era egna och står kvar, men tappar kopplingen
(när en affär töms gäller det uppgifterna). Varje sådan ändring står i `GET /changes`.

## Tidslinjen, utfall och den samlade kundlistan

Det som knyter posten till resten av Snajp.

**Tidslinjen.** `GET /companies/{id}/timeline`, `/people/{id}/timeline` och
`/deals/{id}/timeline` ger allt som hänt, nyast först: postens egna ändringar, arbetet som
knutits till posten här (anteckningar, aktiviteter, uppgifter och, på bolaget och personen,
affärerna), och det som hänt i Iris och hos supporten. `origin` säger var raden bor: `crm`,
`iris` eller `support`. Ett bolag hittar sina leads på organisationsnumret, eller på domänen
när numret saknas. En person på exakt e-postadress. Supportärenden knyts bara på exakt
adress. Affärens tidslinje bär bara det som hör till affären själv: leads och ärenden står
på bolaget och personen.

```json
{"key": "msg:…", "type": "email_sent", "at": "2026-10-01T09:00:00+00:00", "origin": "iris",
 "title": "Förslag", "text": null, "data": {}, "link": {"kind": "conversation", "id": "…"}}
```

`type` är `record_created`, `record_updated`, `record_deleted`, `record_restored`,
`lead_created`, `lead_status`, `email_sent`, `followup_sent`, `reply_received`,
`conversation_stage`, `meeting_booked`, `handed_over`, `call`, `note`, `task`,
`support_ticket`, `activity`, `deal_created` eller `deal_closed`. En anteckning eller uppgift
från CRM:et har `origin: "crm"` och länken `note` eller `task`; samma typ från ett lead har
`origin: "iris"` och länken `lead`. En aktivitet bär `activity_type` (`call`, `meeting`,
`email`, `visit`, `other`), `duration_minutes` och `result` i `data`. Raderade anteckningar,
aktiviteter och uppgifter står inte med. Tidslinjen sätts ihop när den läses, och ingenting kopieras: ett mejl
ligger kvar i konversationen och ett ärende hos supporten. Utkast som aldrig skickades är
inte med. Ett supportärende står med ämne, kanal och läge, aldrig med meddelandena. En
nyckel med omfång får inga utdrag (`text` är `null`): den får veta att något hänt och var.

**Utfall.** Ett utfall på bolaget gäller också bolagets leads:

```bash
curl -X POST "$BAS/companies/$ID/outcome" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"outcome": "do_not_contact", "note": "Bad oss sluta höra av oss."}'
```

`outcome` är `no_answer`, `call_back` (kräver `call_back_on`), `not_interested`,
`do_not_contact`, `meeting_booked` eller `won`. Väntande utskick till bolagets leads stoppas,
leadet byter läge, och `do_not_contact` spärrar adressen. `won` gör bolaget till kund. Svaret
bär posten och `lead_ids`, de leads som berördes. `note` sparas på leadets samtal när bolaget
har ett lead. Vid `won`, och för ett bolag utan lead, blir den i stället en aktivitet på
bolaget (`type: call`, utfallets namn som `subject`, och samma kod som i anropet, till exempel
`won`, som `outcome`), så att den står på tidslinjen.

Åt andra hållet: `GET /companies/{id}/iris` visar bolagets leads och vad de betyder för
posten. `leads` står äldst först, och `latest` är det senast skapade leadet (samma form som en
rad i `leads`), eller `null`. `do_not_contact` är sant där om posten säger det, eller om ett av
bolagets leads har bett att slippa kontakt. Det utfallet vinner alltid över ett värde på posten.

**Kundlistan.** `GET /customers` ger era egna kunder och de leads Iris har vunnit i en lista.
`origin` är `own` eller `iris`, och `counts` säger hur många det finns av varje. Ett vunnet
lead kopieras inte in i registret, och ett bolag som finns på båda ställen står en gång, som
`own`, med `lead_id` bredvid. Ett bolag ni märkt `not_relevant` står inte i listan, inte heller
under `iris` när Iris tidigare har vunnit det: er egen märkning går före. Filtrera med
`origin=own|iris` och `q`.

## Bolagsuppgifter ur SCB:s företagsregister

Skriv ett organisationsnummer och få resten: namn, juridisk form, status, SNI, säte, postadress,
antal anställda som storleksklass och reklamspärr. Bara bolagsnivå. Registret ger aldrig personer
här: inga firmatecknare, ingen styrelse, inga namn på innehavare. En enskild firma slås inte upp
alls, eftersom numret är innehavarens personnummer (422 `not_a_company`). Detsamma gäller ett
dödsbo.

```bash
# Slå upp utan att spara (crm:las)
curl "$BAS/lookup/companies?org_number=556036-0793" -H "X-API-Key: $NYCKEL"

# Fyll bolagets tomma fält (crm:skriv)
curl -X POST "$BAS/companies/$ID/enrich" -H "X-API-Key: $NYCKEL"
```

Uppslaget svarar `{"data": {...}}` med `org_number`, `name`, `legal_form` (AB, HB, EK …),
`legal_form_code` (SCB:s tvåsiffriga kod), `registry_status`, `sni_codes` (huvudnäringen först),
`registered_office` (`municipality`, `county`, som registret skriver dem), `postal_address`
(`street`, `co`, `postal_code`, `city`), `employee_class` (`code` och `label`, till exempel
`10-19`), `advertising_block` och `codes` (registrets råa koder för status och reklamspärr).

Berikningen fyller `name`, `legal_form`, `sni_code` och adressen där de är tomma, och svarar med
bolaget och tre listor:

| Fält | Betyder |
|---|---|
| `company` | bolaget efter berikningen |
| `filled` | fälten som fylldes |
| `skipped` | fält där registret säger något annat och bolagets eget värde stod kvar, men som `?overwrite=true` skriver över. Med `overwrite=true` alltid tom |
| `protected` | fält där registret säger något annat men bolagets värde ändrats för hand i Snajp. De skrivs aldrig över, varken med eller utan `overwrite` |
| `registry_status` | `active`, `inactive`, `never_active`, `deregistered` eller `unknown` |
| `deregistered` | `true` när registret säger att bolaget är avregistrerat, avfört, upplöst, eller att konkursen eller likvidationen är avslutad |
| `advertising_block` | `true` när bolaget har frånsagt sig reklam, `false` när det tar emot, `null` när koden inte är känd |
| `registry` | hela uppslaget, som ovan |

Ett fält som redan har ett värde skrivs aldrig över. Med `?overwrite=true` skrivs det över,
utom ett fält som någon ändrat för hand i Snajp. Berikningen märker inte sina egna fält som
ändrade för hand. Antal anställda skrivs inte: registret ger en storleksklass, och `employees`
är ett antal. Bolaget bär efteråt `registry_status`, `registry_advertising_block` och
`registry_checked_at`, också i `GET /companies/{id}`, i listorna och i webhooks för bolag.
`registry_advertising_block` är `true`, `false` eller `null` (okänt, eller aldrig hämtat) och
skrivs om vid varje berikning, så att ett bolag som tagit bort sin reklamspärr blir `false`.
När den ändras står fältnamnet i ändringsflödet, som för `registry_status`. Ett avregistrerat
bolag känns igen på `registry_status: "deregistered"`.

**Reklamspärren gör inte bolaget till kontakta inte.** Den står på bolaget och i svaret, och
vill ni att den ska spärra lägger ni en spärr under `/suppressions` (kanalen `all` eller
`phone`, slaget `org_number`).

Svarar SCB inte får ni 502 `registry_unavailable`, aldrig ett 500, och bolaget är orört. Är
uppslaget inte konfigurerat för Snajp än svarar båda vägarna 503 `enrichment_not_configured`.

## Radering och personuppgifter

`DELETE` lägger posten i papperskorgen. Den går att återställa i 30 dagar med
`POST /companies/{id}/restore`, och töms sedan på allt utom id och tider. Tömningen görs av
ett jobb som går en gång per dygn, också hos en arbetsyta som inte skriver något och hos en
arbetsyta som är pausad eller avstängd, så en post kan ligga upp till ett dygn efter `purge_at`
innan den är tömd.
`GET /companies?only_deleted=true` (och `/people`) är papperskorgen: det som går att
återställa, senast raderat först, med `purge_at` som säger när posten töms.

Har en person bett att bli raderad (GDPR artikel 17), radera direkt:

```bash
curl -X DELETE "$BAS/people/$ID?permanent=true" -H "X-API-Key: $NYCKEL"
```

En person som avregistrerat sig från era utskick i Snajp får `do_not_contact: true` när
den synkas in. En adress där behandlingen är begränsad (artikel 18) synkas inte, och en
post med en sådan adress töms inte, varken av er eller av papperskorgens trettio dagar.

Skrivande anrop kräver att personuppgiftsbiträdesavtalet med Snajp är registrerat.

## Idempotens, sidindelning och tak

- **Idempotens.** Varje `POST` tar `Idempotency-Key`. Samma nyckel och samma kropp ger
  det sparade svaret tillbaka i 24 timmar, med `Idempotent-Replayed: true`.
- **Sidindelning.** Listor tar `limit` (högst 500) och `cursor`.
- **Tak.** 600 anrop per minut och kund. Varje svar bär `X-RateLimit-Remaining`, och ett
  429 bär `Retry-After`. Använd satserna: 500 poster i ett anrop räknas som ett anrop.
- **Storlek.** En sats får vara högst 8 MB och 500 poster.

## Fel

Ett fel ser alltid ut så här. `code` är stabil och det ni grenar på, `message` är på
engelska och `meddelande` på svenska.

```json
{"detail": {"code": "invalid_fields", "message": "One or more fields could not be interpreted.",
            "meddelande": "Ett eller flera fält gick inte att tolka.",
            "fields": [{"field": "org_number", "code": "orgnr_kontrollsiffra"}]}}
```

| Status | `code` | När |
|---|---|---|
| 401 | (ingen kod) | nyckeln saknas eller är ogiltig |
| 403 | `scope_missing` | nyckeln saknar omfånget, som står i `scope` |
| 403 | `agreement_missing` | biträdesavtalet är inte registrerat |
| 403 | `addon_missing` | Snajp CRM är ett tillägg som inte är påslaget för arbetsytan, och provperioden är slut |
| 404 | `not_found` | posten finns inte |
| 404 | `connection_not_found` | anslutningen finns inte (409 om en körnings anslutning tagits bort) |
| 404 | `run_not_found` | synkkörningen finns inte |
| 404 | `webhook_not_found`, `delivery_not_found` | webhooken eller leveransen finns inte |
| 404 | `suppression_not_found` | spärren finns inte |
| 404 | `stage_not_found` | steget finns inte (422 när `stage_id` i en kropp pekar fel) |
| 404 | `company_not_in_registry` | organisationsnumret finns inte i SCB:s företagsregister |
| 409 | `conflict` | organisationsnumret, adressen eller namnet tillhör redan en annan post. `conflicting_id` är den posten, när den går att peka ut |
| 409 | `run_closed` | körningen är avslutad och tar inte emot fler satser |
| 409 | `processing_restricted` | adressen har begränsad behandling (artikel 18) och får inte tömmas |
| 409 | `stage_in_use` | steget har affärer i sig, också raderade som går att återställa |
| 409 | `stage_required` | det sista öppna, vunna eller förlorade steget kan inte tas bort eller byta typ |
| 409 | `storage_quota_exceeded` | arbetsytans 500 MB för bilagor är fyllda |
| 410 | `permanently_deleted` | posten är tömd och går inte att återställa |
| 413 | `body_too_large` | kroppen är större än 8 MB |
| 413 | `file_too_large` | bilagan är större än 10 MB |
| 422 | `invalid_fields` | fält som inte gick att tolka, uppräknade i `fields` |
| 422 | `unknown_field` | ett fält som inte finns |
| 422 | `company_not_found` | `company_id` pekar inte på ett bolag |
| 422 | `person_not_found`, `deal_not_found`, `note_not_found` | `person_id`, `deal_id` eller `note_id` pekar inte på en levande post hos er |
| 422 | `target_required` | en anteckning, aktivitet eller bilaga måste kopplas till minst ett bolag, en person eller en affär |
| 422 | `file_type_not_allowed` | filtypen tas inte emot, eller passar inte filändelsen |
| 422 | `connection_required` | `connection` saknas |
| 422 | `empty_batch` | satsen är tom |
| 422 | `too_many_items` | fler än 500 poster (50 i förhandsgranskningen, 10 000 värden i en import av spärrar) |
| 422 | `invalid_json`, `invalid_body`, `invalid_encoding` | kroppen går inte att läsa |
| 422 | `invalid_mapping` | mappningen har fel form; `meddelande` säger var |
| 422 | `invalid_url` | webhookens adress är inte en publik https-adress |
| 422 | `invalid_events`, `too_many_webhooks` | okända händelser, eller fler än tio webhooks |
| 503 | `webhooks_unavailable` | webhooks går inte att skapa just nu |
| 422 | `invalid_parameter` | `cursor` eller `updated_since` gick inte att läsa |
| 422 | `call_back_date_required` | utfallet `call_back` saknar `call_back_on` |
| 422 | `org_number_required` | bolaget saknar organisationsnummer att slå upp i registret |
| 422 | `not_a_company` | en enskild firma, ett dödsbo eller en privatperson slås inte upp i registret |
| 502 | `registry_unavailable` | SCB:s företagsregister svarade inte; försök igen senare |
| 503 | `enrichment_not_configured` | uppslag i SCB:s företagsregister är inte konfigurerade än |
| 422 | `idempotency_key_reused` | nyckeln har använts för ett annat anrop |
| 422 | `idempotency_key_too_long` | nyckeln är längre än 200 tecken |
| 429 | `rate_limited` | taket är nått; vänta enligt `Retry-After` |

Fältkoderna i `fields` för ett värde utanför sin lista: `relation_okand` (`relation`),
`rattslig_grund_okand` (`legal_basis`), `kalltyp_okand` (`source_type`) och
`forlustorsak_okand` (`lost_reason_code`).

Fältkoderna för en spärr: `slag_passar_inte_kanalen` (`kind`), `varde_saknas`,
`doman_ogiltig`, `orgnr_ar_personnummer` och samma koder som för bolagets och personens
e-post, telefon och organisationsnummer (`value`). I `POST /suppressions/check` bär felet
frågans eget fält: `email`, `phone` eller `org_number`, och `value` bara när inget av dem
angavs (`varde_saknas`).

Skälen till att en post i en sats hoppades över (`reason`): `saknar_namn`,
`saknar_namn_och_epost`, `hoppas_over_enligt_mappningen`, `privatperson` (se nedan),
`behandlingen_ar_begransad`, `redan_borta`. Konflikter:
`orgnr_tillhor_annat_bolag` (med `conflicting_id`), `finns_redan`.

Körningens fel (`errors`) bär bolagets namn, så att raden går att hitta i källan. Namnet
står aldrig med för en person eller en privatperson, och ett felaktigt organisationsnummer
sparas aldrig: det kan vara ett personnummer.

## Det som inte finns än

- Sammanslagna poster i källan (HubSpot, Pipedrive och Salesforce byter eller behåller id
  vid en sammanslagning). I dag syns den förlorande posten som raderad.
