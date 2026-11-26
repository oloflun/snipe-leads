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
| `crm:las` | läsa bolag, personer, anslutningar och synkkörningar |
| `crm:skriv` | skapa, ändra, radera och återställa bolag och personer |
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
tömd för gott). Flödet säger vilken post och vilka fält som ändrades, inte värdena: hämta
posten för dem. `GET /companies/{id}/history` och `/people/{id}/history` ger samma
händelser för en enda post, nyast först.

## Webhooks

Vill ni hellre att Snajp säger till, registrera en adress:

```bash
curl -X POST "$BAS/webhooks" -H "X-API-Key: $NYCKEL" -H "Content-Type: application/json" \
  -d '{"url": "https://ert-system.se/snajp", "events": ["company.created", "company.updated"]}'
```

Svaret bär `secret`, en enda gång. `events` är valfritt, utan det får ni allt.
`GET /webhooks/events` räknar upp händelserna: `company.*` och `person.*` med `created`,
`updated`, `deleted`, `restored` och `purged`, och `sync.completed` när en synk avslutats.
Webhooks kräver omfånget `crm:admin` och en publik https-adress.

Varje leverans är ett `POST` med händelsen som JSON:

```json
{"id": "<leveransens id>", "type": "company.updated", "created_at": "2026-11-26T09:14:02+00:00",
 "data": {"object": "company", "id": "…", "record": { … hela posten … }}}
```

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

## Radering och personuppgifter

`DELETE` lägger posten i papperskorgen. Den går att återställa i 30 dagar med
`POST /companies/{id}/restore`, och töms sedan på allt utom id och tider.
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
| 409 | `conflict` | organisationsnumret, adressen eller namnet tillhör redan en annan post. `conflicting_id` är den posten, när den går att peka ut |
| 409 | `run_closed` | körningen är avslutad och tar inte emot fler satser |
| 409 | `processing_restricted` | adressen har begränsad behandling (artikel 18) och får inte tömmas |
| 410 | `permanently_deleted` | posten är tömd och går inte att återställa |
| 413 | `body_too_large` | kroppen är större än 8 MB |
| 422 | `invalid_fields` | fält som inte gick att tolka, uppräknade i `fields` |
| 422 | `unknown_field` | ett fält som inte finns |
| 422 | `company_not_found` | `company_id` pekar inte på ett bolag |
| 422 | `connection_required` | `connection` saknas |
| 422 | `empty_batch` | satsen är tom |
| 422 | `too_many_items` | fler än 500 poster (50 i förhandsgranskningen) |
| 422 | `invalid_json`, `invalid_body`, `invalid_encoding` | kroppen går inte att läsa |
| 422 | `invalid_mapping` | mappningen har fel form; `meddelande` säger var |
| 422 | `invalid_url` | webhookens adress är inte en publik https-adress |
| 422 | `invalid_events`, `too_many_webhooks` | okända händelser, eller fler än tio webhooks |
| 503 | `webhooks_unavailable` | webhooks går inte att skapa just nu |
| 422 | `invalid_parameter` | `cursor` eller `updated_since` gick inte att läsa |
| 422 | `idempotency_key_reused` | nyckeln har använts för ett annat anrop |
| 422 | `idempotency_key_too_long` | nyckeln är längre än 200 tecken |
| 429 | `rate_limited` | taket är nått; vänta enligt `Retry-After` |

Skälen till att en post i en sats hoppades över (`reason`): `saknar_namn`,
`saknar_namn_och_epost`, `hoppas_over_enligt_mappningen`, `privatperson` (se nedan),
`behandlingen_ar_begransad`, `redan_borta`. Konflikter:
`orgnr_tillhor_annat_bolag` (med `conflicting_id`), `finns_redan`.

Körningens fel (`errors`) bär bolagets namn, så att raden går att hitta i källan. Namnet
står aldrig med för en person eller en privatperson, och ett felaktigt organisationsnummer
sparas aldrig: det kan vara ett personnummer.

## Det som inte finns än

- Affärer, aktiviteter och anteckningar. API:t bär bolag och personer.
- Sammanslagna poster i källan (HubSpot, Pipedrive och Salesforce byter eller behåller id
  vid en sammanslagning). I dag syns den förlorande posten som raderad.
