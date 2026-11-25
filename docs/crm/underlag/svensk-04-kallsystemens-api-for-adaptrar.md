# Källsystemens API:er för Snajp CRM:s inflödesadaptrar

Underlag 2026-11-25. Research i leverantörernas egen dokumentation (WebSearch/WebFetch).
Inget i den här filen är kopierat ur Twenty CRM:s kod. Twentys fältnamn är hämtade ur
källfilerna bara för att adaptern ska kunna läsa en Twenty-instans (interoperabilitet,
licensval A står kvar).

## Hur filen ska läsas

- **[Läst]** = står i den källa som länkas på samma rad eller i sektionens källista.
- **[Sekundär]** = läst, men i en tredjepartskälla (klientbibliotek, integrationsplattform,
  forum). Ska verifieras mot leverantören innan det blir kod.
- **[Antaget]** = min slutsats eller mitt minne, inte uppslaget. Får inte gå in i kod
  utan kontroll mot en riktig instans.
- Påståenden om Snajps egen kod har fil:rad. Jag har läst
  `snajp-support/app/crm/falt.py`, `snajp-support/app/crm/adaptrar.py` och
  `db/migrations/20261125090000_153_crm_grund.sql`. Inget annat i repot.

Flera leverantörer blockerade hämtningen (Salesforce svarade 403 på varje
developer.salesforce.com-sida, Upsales dokumentation är en Postman-sida som inte
renderas utan JavaScript, Lime CRM:s plattformsdokumentation kräver inloggning för
vissa sidor). Där bygger avsnittet på sökmotorns utdrag ur samma officiella sidor, och
det står vid varje påstående.

## Sammanfattning för den som bygger först

| System | Inkrementell synk | Webhook-signering | Radering syns som | Största fällan |
|---|---|---|---|---|
| HubSpot | Search API, `hs_lastmodifieddate`/`lastmodifieddate` GTE, max 10 000 träffar per sökning | v1 SHA-256(secret+body), v3 HMAC-SHA256 base64 | `archived: true`, `*.deletion`-händelse | Merge skapar NYTT id; associationer i v4 |
| Pipedrive | v2 `updated_since` (RFC 3339), cursor, `limit` ≤ 500 | Ingen signering, bara Basic auth | `is_deleted: true`, mjuk i 30 dagar | Egna fält = 40-teckens hashnycklar |
| Lime CRM | Per installation (`/api/v1/docs/`) | HMAC-SHA256, `X-Lime-Signature` (v1 `sha256=`, v2 `v2=`) | `<limetype>.delete`-händelse | Datamodellen skiljer sig per kund |
| Lime Go | Ingen ändringsström dokumenterad | Ej dokumenterad | Ej dokumenterad | 10 anrop/minut på organisations-POST |
| Upsales | `id=gt:` + `sort=id`, filter `attr=gt:värde` | Ej hittad | `active` (antaget) | Officiella fältschemat ej åtkomligt |
| Salesforce | `sobjects/{X}/updated` (30 dagar, 600 000 id), CDC 72 h | CDC via Pub/Sub (gRPC), ingen HTTP-signatur | `getDeleted`, `IsDeleted` via `queryAll`, `MasterRecordId` | API-version i URL:en, sandlåda på annan värd |
| Twenty | `updatedAt` i filter (antaget), cursor | HMAC-SHA256 hex över `{timestamp}:{body}` | `*.deleted`, `deletedAt` | 100 anrop/minut, 60 poster per batch |
| SuperOffice | OData `$filter` på `updatedDate` (antaget form) | HMAC-SHA256 base64, `X-SuperOffice-Signature` | `contact.softdeleted` och `contact.deleted` | API-värden flyttar (sod2, online4…) |
| Dynamics 365 | `Prefer: odata.track-changes`, `$deltatoken` | Ingen signering; nyckel i header eller `?code=` | `$deletedEntity` med `reason: "deleted"` | Ändringsspårning måste slås på per tabell, 7 dagars token |
| Fortnox | `lastmodified=YYYY-MM-DD HH:MM`, `limit` ≤ 500 | WebSocket, inte HTTP-webhook | `customer-deleted-v1` på WebSocket | Kundregistret innehåller privatpersoner (`Type`) |
| Visma eEkonomi/Spiris | `ChangedUtc` (filterform ej verifierad) | Ej verifierad | `IsActive: false` (antaget) | Kräver partneravtal |
| Visma.net | `lastModifiedDateTime` + `lastModifiedDateTimeCondition` | Ej dokumenterad | `Customer_Deleted`-händelse (antaget namn) | Hemlig timgräns, sidparametrar obligatoriska |

Det första en byggare behöver:

1. **Externt id är `(anslutning_id, objekt, externt_id)`** i `crm_externa_id`
   (`db/migrations/20261125090000_153_crm_grund.sql:154-173`). Tre system byter id vid
   sammanslagning (HubSpot skapar ett nytt, Pipedrive och Salesforce behåller vinnarens).
   Tabellen behöver därför ett sätt att peka gamla id på den överlevande posten, se
   avsnitt 13.4.
2. **Organisationsnumret är nästan aldrig ett standardfält.** Bara Lime Go
   (`registrationNumber`), SuperOffice (`OrgNr`), Fortnox (`OrganisationNumber`) och Visma
   eEkonomi (`CorporateIdentityNumber`) har det som eget fält. HubSpot, Pipedrive,
   Salesforce, Twenty och Dynamics kräver ett kundspecifikt eget fält. Mappningen måste
   alltså vara kundens att peka om, vilket `adaptrar.py` redan gör (`adaptrar.py:32-34`).
3. **Signering skiljer sig helt.** Pipedrive och Dynamics signerar inte alls. Webhook-
   mottagaren måste då kräva en hemlig nyckel i URL eller header per anslutning.
4. **Hastighetsgränserna är små hos Twenty (100/min), Fortnox (25 per 5 s), Lime Go
   (10/min på skrivning) och Lime CRM Cloud (3 000 per 5 min per IP).** En synk mot dem
   måste kunna pausas och återupptas, och förloppet visas för användaren enligt
   projektregeln om att följa flödet.

---

## 1. HubSpot (CRM API v3/v4, nu datumversionerat)

Källor:
- Companies: https://developers.hubspot.com/docs/api/crm/companies
- Contacts: https://developers.hubspot.com/docs/api/crm/contacts
- Search: https://developers.hubspot.com/docs/api/crm/search
- Gränser: https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines
- Associations v4: https://developers.hubspot.com/docs/guides/api/crm/associations/associations-v4
- Webhooks: https://developers.hubspot.com/docs/api-reference/latest/webhooks/guide.md
- Signering: https://developers.hubspot.com/docs/guides/apps/authentication/validating-requests
- OAuth-token: https://developers.hubspot.com/docs/api-reference/legacy/authentication/oauth-tokens/v1/guide.md
- OAuth-flöde: https://developers.hubspot.com/docs/guides/apps/authentication/working-with-oauth
- Merge: https://developers.hubspot.com/docs/api-reference/2026-03/crm/objects/contacts/merge-contacts.md

### 1.1 Autentisering och bas-URL

- Bas-URL: `https://api.hubapi.com` [Läst, merge-sidan anger `POST https://api.hubapi.com/crm/objects/2026-03/contacts/merge`].
- **Versionering har bytts.** Nyare sidor visar datumversionerade sökvägar:
  `/crm/objects/2026-09/{object}/search`, `/crm/objects/2026-03/contacts/merge`,
  `/crm/objects/2026-09/{fromObjectType}/{objectId}/associations/{toObjectType}` [Läst].
  De äldre sidorna visar fortfarande `/crm/v3/objects/...` [Läst]. Adaptern ska ha
  versionen som en konstant per anslutning, inte hårdkodad i varje anrop [Antaget].
- OAuth (offentlig app): authorize `https://app.hubspot.com/oauth/authorize`
  (`client_id`, `redirect_uri`, `scope` mellanslagsseparerat, valfritt `optional_scope`,
  `state`) [Läst]. Token: `POST https://api.hubapi.com/oauth/v1/token`,
  `application/x-www-form-urlencoded`, `grant_type=authorization_code` eller
  `refresh_token`. Svaret har `token_type`, `access_token`, `refresh_token`,
  `expires_in` (exemplet: `1800`, alltså 30 minuter) [Läst]. OAuth v1 ska avvecklas
  **16 februari 2027** [Läst, tokensidan].
- Privat app / privat distribution: en åtkomsttoken som `Authorization: Bearer <token>`
  [Antaget; sidorna jag läste nämner inte headern för privata appar].
- Omfång: namnen `crm.objects.companies.read`, `crm.objects.contacts.read`,
  `crm.objects.deals.read` står inte på OAuth-sidan jag läste [Antaget, ska slås upp i
  scopes-referensen].

### 1.2 Objekt och endpoints

| Objekt | Lista | En post | Sök | Batch-läs |
|---|---|---|---|---|
| Företag | `GET /crm/v3/objects/companies` | `GET /crm/v3/objects/companies/{companyId}` | `POST /crm/objects/2026-09/companies/search` | `POST /crm/v3/objects/companies/batch/read` |
| Kontakt | `GET /crm/v3/objects/contacts` | `GET /crm/v3/objects/contacts/{recordId}` eller `{email}?idProperty=email` | `.../contacts/search` | `POST /crm/v3/objects/contacts/batch/read` |
| Affär | `.../deals` | | `.../deals/search` | |
| Aktivitet | calls, emails, meetings, notes, tasks som egna objekt [Antaget] | | | |

Frågeparametrar på hämtning och lista: `properties`, `propertiesWithHistory`,
`associations` [Läst]. Batch-läsning tar `properties`, `inputs: [{id}]` och valfritt
`idProperty`; den returnerar **inga associationer** [Läst].

Egenskapsdefinitioner: `GET /crm/v3/properties/companies` [Läst].

### 1.3 JSON-form

Kontakt, ordagrant ur dokumentationens listsvar [Läst, contacts-sidan]:

```json
{
  "results": [
    {
      "id": "33451",
      "properties": {
        "createdate": "2022-06-01T14:31:48.469Z",
        "email": "lorelai@thedragonfly.com",
        "firstname": "Lorelai",
        "hs_object_id": "33451",
        "lastmodifieddate": "2025-07-07T20:27:17.947Z",
        "lastname": "Gilmore"
      },
      "createdAt": "2022-06-01T14:31:48.469Z",
      "updatedAt": "2025-07-07T20:27:17.947Z",
      "archived": false
    }
  ],
  "paging": { "next": { "after": "33452", "link": "https://api.hubspot.com/crm/objects/v3/contacts?limit=1" } }
}
```

Företag: sidan visar bara en skapa-kropp [Läst]:

```json
{ "properties": { "name": "HubSpot", "domain": "hubspot.com", "city": "Cambridge",
  "industry": "Technology", "phone": "555-555-555", "state": "Massachusetts",
  "lifecyclestage": "51439524" } }
```

Var fälten ligger:
- Allt utom `id`, `createdAt`, `updatedAt`, `archived` ligger under `properties`, och
  alla värden är strängar [Läst i exemplen].
- **Orgnr:** finns inte som standardegenskap. Kunden har ett eget fält med eget internt
  namn [Antaget, inget standardfält hittat bland de dokumenterade].
- **Momsnr:** inget standardfält [Antaget].
- **Domän:** `domain`, fler domäner i `hs_additional_domains` semikolonseparerade [Läst].
  "domain names are the primary unique identifier" för företag [Läst].
- **Telefon:** `phone` (företag), `phone`/`mobilephone` (kontakt) [Läst].
- **Adress:** företag `city`, `state` [Läst]; `address`, `zip`, `country` [Antaget för
  företag; på kontakt är `address`, `city`, `state`, `country`, `zip` dokumenterade].
- **Ägare:** `hubspot_owner_id` [Antaget, nämns inte på sidorna jag läste].
- **Livscykel:** `lifecyclestage`. Exemplet har värdet `"51439524"`, alltså ett internt
  id för ett eget steg, inte `customer` [Läst]. Uppslaget i `adaptrar.py:150-153`
  (`customer`, `lead` …) träffar därför inte kunder som har egna livscykelsteg.
- **Egna fält:** egna egenskaper ligger platt i `properties` med kundens interna namn
  [Antaget].
- **Sammanslagning:** `hs_merged_object_ids` innehåller id för poster som slagits in
  [Sekundär, HubSpot-forum och kunskapsbas; se 1.6].

### 1.4 Inkrementell synk, sidindelning, gränser

- Lista: `limit` max 100, nästa sida med `after` = `paging.next.after` [Läst, contacts].
- Search: `filterGroups[].filters[]` med `propertyName`, `operator`, `value`
  (`values` för `IN`/`NOT_IN`, `highValue` för `BETWEEN`) [Läst]. Operatorer: `LT`,
  `LTE`, `GT`, `GTE`, `EQ`, `NEQ`, `BETWEEN`, `IN`, `NOT_IN`, `HAS_PROPERTY`,
  `NOT_HAS_PROPERTY`, `CONTAINS_TOKEN`, `NOT_CONTAINS_TOKEN` [Läst]. Högst 5 grupper,
  6 filter per grupp, 18 totalt [Läst]. En sorteringsregel [Läst]. `limit` standard 10,
  max 200 [Läst]. **Högst 10 000 träffar per sökning; sida bortom ger 400** [Läst].
  **5 anrop per sekund per konto** [Läst]. Svaren har inga gränsrubriker [Läst].
- Tidsstämpel: företag returnerar `hs_lastmodifieddate`, kontakter `lastmodifieddate`
  [Läst].
- Delta-recept [Antaget, följer av gränserna ovan]: sök `hs_lastmodifieddate GTE
  <senaste vattenmärke>`, sortera stigande på samma fält, och när 10 000 nås: starta en
  ny sökning från den sista postens tidsstämpel. Spara vattenmärket i
  `crm_externa_id.extern_uppdaterad_at` (`153_crm_grund.sql:162`) eller på anslutningen.
- Privat distribuerade appar [Läst]:

| Nivå | Per 10 s (per app) | Per dag (per konto) |
|---|---|---|
| Free och Starter | 100 | 250 000 |
| Professional | 190 | 625 000 |
| Enterprise | 190 | 1 000 000 |
| Med API Limit Increase | 250 | +1 000 000 per köp (högst två) |

- Offentliga OAuth-appar: **110 anrop per 10 s per installerande konto**; Search
  räknas inte in [Läst]. Överskridning ger `429`; felen bör hållas under 5 % av dagens
  anrop [Läst]. Dagsgränsen nollställs vid midnatt i kontots tidszon [Läst].
  `X-HubSpot-RateLimit-Secondly` är avvecklad [Läst].
- Associations har egna gränser: 100/10 s (Free/Starter), 150/10 s (Pro/Enterprise),
  200/10 s med limit increase; 500 000 per dag för Pro/Enterprise [Läst]. Batch-läsning
  av associationer: 1 000 id per anrop [Läst].

### 1.5 Webhooks

- Registrering (äldre offentliga appar): `GET|PUT /app-webhooks/2026-09/{appId}/settings`
  (`targetUrl`, `throttling.maxConcurrentRequests`), `GET|POST
  /app-webhooks/2026-09/{appId}/subscriptions`, `PUT|DELETE .../subscriptions/{subscriptionId}`,
  med en Developer API-nyckel [Läst]. Högst 1 000 prenumerationer per app [Läst].
  Leveranser räknas inte mot API-gränsen [Läst].
- Projektbaserade appar (nya plattformen) använder i stället Webhooks Journal API (beta)
  med klientcredentials-token; åtgärder `CREATE`, `UPDATE`, `DELETE`, `MERGE`,
  `RESTORE`, `ASSOCIATION_ADDED`, `ASSOCIATION_REMOVED`, `SNAPSHOT`; objekttyper
  `0-1` kontakt, `0-2` företag, `0-3` affär [Läst,
  https://developers.hubspot.com/docs/guides/api/app-management/webhooks]. Journal 100
  anrop/s, prenumerationer 50/s, snapshots 10/s per app [Läst].
- Händelsetyper (äldre): `contact.creation`, `contact.deletion`, `contact.merge`,
  `contact.associationChange`, `contact.restore`, `contact.privacyDeletion`,
  `contact.propertyChange`; `company.creation`, `company.deletion`,
  `company.propertyChange`, `company.associationChange`, `company.restore`,
  `company.merge`; motsvarande `deal.*` [Läst]. Privata appar nämns inte [Läst].
- Nyttolast: en JSON-array, varje post t.ex. [Läst]:

```json
{ "objectId": 1246965, "propertyName": "lifecyclestage", "propertyValue": "subscriber",
  "changeSource": "ACADEMY", "eventId": 3816279340, "subscriptionId": 25, "portalId": 33,
  "appId": 1160452, "occurredAt": 1462216307945, "eventType": "contact.propertyChange",
  "attemptNumber": 0 }
```

  Merge- och associationshändelser har `primaryObjectId`, `mergedObjectIds`,
  `fromObjectId`, `toObjectId`, `associationRemoved` [Läst]. Batchen är "under 100"
  respektive "up to 100" händelser; sidan säger båda [Läst].
- Signering [Läst]:
  - v1: `X-HubSpot-Signature-Version: v1`, `X-HubSpot-Signature` = hex SHA-256 av
    `client_secret + body`.
  - v2: SHA-256 av `client_secret + metod + URI + body`.
  - v3: `X-HubSpot-Signature-v3` = base64(HMAC-SHA256(client_secret, metod + URI + body
    + timestamp)), `X-HubSpot-Request-Timestamp`; avvisa äldre än 5 minuter; jämför i
    konstant tid. URI:n ska avkodas för `%3A %2F %3F %40 %21 %24 %27 %28 %29 %2A %2C %3B`.
- Återförsök: upp till 10 gånger under 24 timmar vid anslutningsfel, timeout över
  **5 sekunder**, och varje 4xx/5xx [Läst]. `maxConcurrentRequests` måste vara större än 5,
  standard 10 [Läst].

### 1.6 Radering och sammanslagning

- Radering: listor och hämtningar visar `archived` [Läst i svarsformen]; `*.deletion`-
  händelse [Läst]. Att lista arkiverade med `archived=true` är inte dokumenterat på sidorna
  jag läste [Antaget att det finns].
- Merge-endpoint: `POST /crm/objects/2026-03/contacts/merge` med `primaryObjectId` och
  `objectIdToMerge` [Läst].
- **Sammanslagning ger ett nytt record-id** som inte fanns förut; gamla id slår igenom till
  den nya posten vid hämtning [Sekundär: HubSpots utvecklarforum och kunskapsbas,
  https://community.hubspot.com/t5/Developer-Announcements/Updated-Merge-Functionality-for-CRM-Objects-including-Contacts/m-p/1049313].
  `hs_merged_object_ids` behåller de gamla id:na [Sekundär]. Följd för Snajp: ett
  `company.merge` ska flytta båda gamla externa id till den nya posten i
  `crm_externa_id` och inte skapa ett tredje bolag.

### 1.7 Fällor

- **Associationer.** Kontaktens bolag är ingen egenskap utan en association. Standard-
  typ-id [Läst, associations-v4]: kontakt→företag 279 (primärt 1), företag→kontakt 280
  (primär kontakt 2), affär→kontakt 3, affär→företag 341 (primärt 5), företag→affär 342
  (6). `adaptrar.py:166` läser `properties.associatedcompanyid`; den egenskapen står inte
  i något jag läst [Antaget att den finns på äldre konton]. Säkrare: hämta kontakter med
  `associations=companies` eller batch-läs v4-associationer och välj typ 1.
- Batch-läsning returnerar inga associationer [Läst]; listanrop med `associations` gör det.
- `lifecyclestage` kan vara ett numeriskt id [Läst i exemplet].
- 10 000-taket i Search kräver vattenmärkesstegning.
- OAuth v1 försvinner 2027-02-16 [Läst].

---

## 2. Pipedrive (API v1 och v2)

Källor:
- v2-översikt: https://pipedrive.readme.io/docs/pipedrive-api-v2
- Migrationsguide v1→v2: https://pipedrive.readme.io/docs/pipedrive-api-v2-migration-guide
- Gränser: https://pipedrive.readme.io/docs/core-api-concepts-rate-limiting
- Organisationer: https://developers.pipedrive.com/docs/api/v1/Organizations
- Personer: https://developers.pipedrive.com/docs/api/v1/Persons
- Egna fält: https://pipedrive.readme.io/docs/core-api-concepts-custom-fields
- Webhooks v2: https://pipedrive.readme.io/docs/guide-for-webhooks-v2
- OAuth: https://pipedrive.readme.io/docs/marketplace-oauth-authorization

### 2.1 Autentisering och bas-URL

- Bas-URL: `https://{companydomain}.pipedrive.com/api/v2/...` (v1: `/api/v1/...`) [Läst].
  OAuth-svaret har `api_domain` = bas-URL:en med företagsdomänen [Läst].
- API-token: exemplet på egna fält-sidan skickar `x-api-token` som header [Läst].
- OAuth: authorize `https://oauth.pipedrive.com/oauth/authorize` (`client_id`,
  `redirect_uri`, `state`); token `POST https://oauth.pipedrive.com/oauth/token`, klient
  via HTTP Basic base64(`client_id:client_secret`) [Läst]. Svar: `access_token`,
  `token_type`, `refresh_token`, `scope`, `expires_in`, `api_domain` [Läst]. Åtkomsttoken
  gäller 60 minuter, refresh-token går ut efter 60 dagar utan användning (förnyas vid
  varje användning), koden efter 5 minuter [Läst].
- Omfångsnamn står på en separat sida [Läst att de finns; namnen ej lästa].

### 2.2 Objekt och endpoints (v2 där det finns)

| Objekt | Lista | En post | Sök | Kostnad (token) |
|---|---|---|---|---|
| Organisation | `GET /api/v2/organizations` | `GET /api/v2/organizations/{id}` | `GET /api/v2/organizations/search` | 10 / 1 / 20 |
| Person | `GET /api/v2/persons` | `GET /api/v2/persons/{id}` | | 10 / 1 |
| Affär | `GET /api/v2/deals` | | | |
| Aktivitet | `GET /api/v2/activities` | | | |
| Anteckning | v1 `notes` [Antaget] | | | |

v2 finns för Organizations, Persons, Deals, Activities, Search, Fields, Pipelines/Stages,
Products m.fl. [Läst]. v1 får minst ett års avvecklingstid när det markeras [Läst].

### 2.3 JSON-form

Ingen fullständig svarsexempel gick att läsa (svaren är ihopfällda på referenssidan).
Fältnamnen nedan kommer ur migrationsguiden och parameterlistorna [Läst]; exemplet är
**ihopsatt av mig** ur dem [Antaget form]:

```json
{
  "id": 1,
  "name": "Exempelbolaget AB",
  "owner_id": 123,
  "add_time": "2024-07-01T05:46:33Z",
  "update_time": "2025-01-01T10:20:00Z",
  "visible_to": 3,
  "label_ids": [5],
  "is_deleted": false,
  "address": {
    "value": "Storgatan 1, 903 26 Umeå", "street_number": "1", "route": "Storgatan",
    "sublocality": null, "subpremise": null, "locality": "Umeå",
    "admin_area_level_1": "Västerbottens län", "admin_area_level_2": null,
    "country": "Sverige", "postal_code": "903 26", "formatted_address": "..."
  },
  "custom_fields": { "dcf558aac1ae4e8c4f849ba5e668430d8df9be12": "556824-9022" }
}
```

Person (v2) [Läst fältnamn]: `org_id` som heltal ("No longer an object"), `is_deleted`
(negationen av gamla `active_flag`), `emails` och `phones` som listor av
`{ "value", "label", "primary" }`, `owner_id` som heltal. `job_title` (och `ims`,
`postal_address`, `notes`, `birthday`) kommer bara när kontaktsynk är påslagen hos
bolaget [Läst, Persons-sidan].

- **Orgnr/momsnr:** inga standardfält; kundens eget fält under `custom_fields` med hash-
  nyckel [Läst att egna fält ligger där; att orgnr saknas som standardfält är Antaget].
- **Domän:** organisationen har ett webbplatsfält i nyare konton [Antaget; `adaptrar.py:176`
  läser `website`].
- **Ägare:** `owner_id` (heltal i v2) [Läst].
- **Kundstatus:** inget livscykelfält; etiketter i `label_ids` [Läst].

### 2.4 Inkrementell synk, sidindelning, gränser

- `GET /api/v2/organizations` och `/persons`: `updated_since` (RFC 3339, "at or after"),
  `updated_until`, `sort_by` = `id` | `update_time` | `add_time`, `sort_direction`,
  `include_fields`, `custom_fields` (max 15 nycklar), `limit` (standard 100, **max 500**),
  `cursor` [Läst]. Namnet på nästa-markören i svaret (`additional_data.next_cursor`) är
  ihopfällt i dokumentationen [Antaget].
- Delta-recept: `updated_since=<vattenmärke>&sort_by=update_time&sort_direction=asc&limit=500`
  och följ cursorn [Antaget, följer av parametrarna].
- Dagsbudget [Läst]: 30 000 bas-token × planmultiplikator × antal licenser
  (Lite 1, Growth 2, Premium 5, Ultimate 7), gemensam för hela bolaget, nollställs vid
  midnatt i serverns tidszon. Kostnad v2 enligt tabellen ovan; generella exempel: hämta en
  2, lista 20, uppdatera 10, radera 6, sök 40 [Läst].
- Burst per användare och 2-sekundersfönster [Läst]: Lite 20/80, Growth 40/160, Premium
  100/400, Ultimate 120/480 (API-token / OAuth). **Search: 10 per 2 s** på alla planer.
- Rubriker: `x-ratelimit-limit`, `x-ratelimit-remaining`, `x-ratelimit-reset`,
  `x-daily-requests-left` (bara API-token) [Läst]. Slut på budget ger `429` till nästa
  nollställning; fortsatt trafik efter 429 kan ge en Cloudflare-`403` [Läst].

### 2.5 Webhooks (v2)

- Registrering: `POST /v1/webhooks` med `subscription_url`, `event_action`,
  `event_object`, valfritt `version` (standard `2.0`), `user_id`, `http_auth_user`,
  `http_auth_password`, `name` [Läst]. Högst **40 webhooks per användare** [Läst].
  Notiser skickas bara om den auktoriserade användaren ser objektet [Läst].
- Åtgärder `create`, `change`, `delete`, `*`; objekt bl.a. `activity`, `deal`, `lead`,
  `note`, `organization`, `person`, `pipeline`, `product`, `stage`, `user`, `*` [Läst].
- Nyttolast: `meta`, `data`, `previous` [Läst]. `meta` har `action`, `entity`,
  `entity_id`, `id`, `timestamp`, `version`, `change_source` (`app`|`api`),
  `is_bulk_edit`, `correlation_id`, `user_id`, `company_id`, `webhook_id`,
  `webhook_owner_id`, `attempt`, `host`, `type`, och `permitted_user_ids` [Läst].
  `data` är null vid delete; `previous` har bara ändrade fält vid change [Läst].
- **Signering: ingen.** Bara valfri HTTP Basic [Läst]. Mottagaren ska kräva Basic-
  uppgifter per anslutning.
- Timeout 10 s; tre återförsök efter 3, 30 och 150 s; webhooken raderas efter 3 dygn
  utan lyckad leverans; tio misslyckade första försök ger 30 minuters avstängning och
  händelser under avstängningen går förlorade [Läst]. Därför måste en periodisk
  delta-synk alltid gå parallellt med webhooks [Antaget slutsats].

### 2.6 Radering och sammanslagning

- Radering är mjuk: `is_deleted: true`, slutgiltigt borta efter 30 dagar [Läst].
- Merge: `PUT /api/v1/organizations/{id}/merge` och `PUT /api/v1/persons/{id}/merge` med
  `merge_with_id`, kostnad 40 [Läst]. I webhooken får den förlorande posten en delete-
  händelse med `meta.merged_to_id`, och den överlevande en change-händelse med
  `meta.merged_from_id` [Läst].

### 2.7 Fällor

- **Egna fält är 40-teckens hashar** (`dcf558aac1ae4e8c4f849ba5e668430d8df9be12`), olika
  per konto [Läst]. Mappningen ska lagra hashen, och gränssnittet ska visa fältnamnet ur
  fältdefinitionerna (`/organizationFields`, `/personFields`). Identifiera egna fält med
  `edit_flag: true` [Läst]. Fälttyper: `varchar`, `varchar_auto`, `text`, `double`,
  `monetary`, `set`, `enum`, `user`, `org`, `people`, `phone`, `time`, `timerange`,
  `date`, `daterange`, `address` [Läst]. I v2 är enkelval ett tal och flerval en lista av
  tal: värdet måste slås upp mot fältets alternativ [Läst].
- v1 och v2 har olika former för samma fält (`org_id` objekt mot heltal, `phone` mot
  `phones`, `active_flag` mot `is_deleted`). `adaptrar.py:174-197` läser båda formerna,
  men `adaptrar.py:181` försöker `owner_id.name`, som inte finns i v2 där `owner_id` är
  ett heltal [Läst om v2-formen].

---

## 3. Lime CRM (REST-API:er, självhostad eller Lime Cloud)

Källor:
- https://docs.lime-crm.com/integration/rest-apis/start
- Webhooks: https://platform.docs.lime-crm.com/projects/webhooks/en/latest/
- Webhook-API: https://platform.docs.lime-crm.com/projects/webhooks/en/latest/api/
- Webhook-konfiguration: https://platform.docs.lime-crm.com/projects/webhooks/en/latest/configuration/
- Lime query: https://platform.docs.lime-crm.com/en/latest/development/lime-query/

### 3.1 Autentisering och bas-URL

- Interaktiv dokumentation per applikation: `https://<domän>/<applikation>/api/v1/docs/`,
  t.ex. `https://lime.example.com/Lime%20CRM/api/v1/docs/` [Läst]. Bas-URL alltså
  `https://<domän>/<applikation>/api/v1/` [Läst mönstret].
- API-nyckel knuten till en användare av typen API, skapas i LISA (Databases > Security >
  Users); nyckeln visas en gång, en ny ogiltigförklarar den gamla, användarens policyer
  gäller [Läst]. Headern `x-api-key` [Sekundär, en leverantörs exempel `curl -H
  "x-api-key: ABC123"`].

### 3.2 Objekt och endpoints

- API:er: Limetype API (metadata), Limeobject API (skapa, uppdatera, radera), File API,
  Query API (komplexa frågor och stora volymer) [Läst].
- **Endpoints och operationer varierar per applikation eftersom datamodellen gör det**
  [Läst]. Sökvägar som `/api/v1/limeobject/company/` och `/api/v1/limeobject/person/` är
  [Antaget]; de måste läsas ur kundens `/api/v1/docs/`.
- Filter-endpoints: `<DOMÄN>/<APP>/api/v1/filter` och `/api/v1/filter/<FILTER-ID>` [Läst].
- Lime query (Python-gränssnittet, HTTP-formen ej dokumenterad där) [Läst]:

```python
{ 'limetype': 'deal',
  'responseFormat': {'object': {'name': None, 'value': {'_alias': 'deal_value'},
                                'company': {'name': None}}},
  'filter': {...},
  'orderBy': [{'company.name': 'ASC'}, {'probability': 'DESC'}],
  'limit': 50, 'offset': 10 }
```

  Filteruttryck `key`, `op`, `exp`; `op` ∈ `AND`, `OR`, `=?` (börjar med), `=`, `>`,
  `>=`, `IN`, `<`, `<=`, `?`, `!=`, `!`; punktnotation över `belongsto`-relationer;
  `limit` standard 100; MSSQL kräver `orderBy` med offset [Läst].

### 3.3 JSON-form

Inget officiellt exempel gick att läsa. Standardmodellen i Lime (limetypen `company` med
`name`, `registrationno`, `phone`, `www`, `visitingaddress1`, `buyingstatus`, `coworker`;
`person` med `firstname`, `lastname`, `email`, `mobilephone`, `position`, `company`) är
**[Antaget]** och står så i `adaptrar.py:200-231`. Systemfälten `_id` och `_timestamp`
(`adaptrar.py:202-203`) är också [Antaget]. Varje kund kan ha andra namn.

### 3.4 Inkrementell synk, sidindelning, gränser

- Lime CRM Cloud: **3 000 anrop per 5 minuter per IP**; konfigurerbart på egen server [Läst].
- Sidindelning i Query: `limit`/`offset` [Läst]. REST-listornas sidparametrar [Antaget,
  läs i `/api/v1/docs/`].
- Ändringsfilter: ett filter på en uppdateringstidsstämpel via Query API [Antaget att ett
  sådant fält finns och går att filtrera på].

### 3.5 Webhooks

- Kräver Lime CRM server 13.2 eller nyare; ingår i Lime CRM Cloud; användaren ska vara
  administratör eller i gruppen Webhook Users [Sekundär, sökutdrag ur Limes dokumentation].
- Prenumerations-API, samma prenumerationer på båda [Läst]:
  `https://{app_url}/{app}/api/v1/subscription/` (signaturversion v1) och
  `.../api/v2/subscription/` (v2; en server utan v2 svarar `404`).
  `GET /subscription/available/`, `GET /subscription/`, `POST /subscription/`,
  `PUT /subscription/:id`, `GET /subscription/:id`, `DELETE /subscription/:id`.
- Skapa [Läst]:

```json
{ "events": ["company.new"], "target_url": "https://example.org/hook/123", "secret": "SuperSecret123" }
```

  Svar: `{ "id": 1, "events": ["company.new"], "target_url": "...", "enabled": true,
  "signature_version": "v2" }` [Läst].
- Händelser: new, update, delete och restore per limetyp, systemhändelser och egna
  händelser [Läst]. Formen `<limetype>.new` är belagd; `.update`, `.delete`, `.restore`
  är [Antaget] efter samma mönster. Systemhändelser `webhook.webhook.disabled`,
  `webhook.msg_dropped` [Läst].
- Rubriker vid leverans: `X-Lime-Webhook-Id`, `X-Lime-Delivery-Id`, `X-Lime-Message-Id`,
  `X-Lime-Delivery-Timestamp`, `X-Lime-Signature` [Läst].
- Signering (bara när secret är satt) [Läst]:
  - v1: `X-Lime-Signature: sha256=<hex>` = HMAC-SHA256 av råa kroppen.
  - v2: `X-Lime-Signature: v2=<hex>` = HMAC-SHA256 av
    `v2:<delivery id>:<timestamp>:<SHA-256 hex av kroppen>`; mottagaren avvisar äldre än
    300 sekunder och dubbletter av delivery id.
- Återförsök [Läst]: `delivery_attempts` standard **0** (inga återförsök), `delivery_backoff`
  10 s, väntan `(2^n)*backoff`; med standardbackoff 10, 30, 70, 150, 310 s; rekommenderat
  högst 4 försök med v2. `dont_disable_on_failed_delivery` standard `True`.
- Nyttolastens kropp är inte dokumenterad på sidorna jag läste [Läst att den saknas].

### 3.6 Radering och sammanslagning

`<limetype>.delete` och `.restore` som händelser [Läst att typerna finns]. Hur en
sammanslagning syns: inte dokumenterat [Antaget: som en update på vinnaren och en delete
på förloraren].

### 3.7 Fällor

- **Dynamisk objektmodell per kund** [Läst]. Adaptern ska läsa limetypernas metadata
  (Limetype API) vid anslutning och låta kunden peka ut vilket fält som är orgnr.
  Standardmappningen i `adaptrar.py:205` (`registrationno`, `corporateidentitynumber`,
  `orgnr`) är en gissning.
- Webhooks utan secret signeras inte; kräv secret när Snajp skapar prenumerationen.
- `delivery_attempts: 0` betyder att en enda misslyckad leverans tappas; delta-synk behövs.

---

## 4. Lime Go

Källor:
- https://lime-go.readme.io
- https://lime-go.readme.io/reference/organization.md
- https://lime-go.readme.io/reference/organizations-1.md
- https://lime-go.readme.io/reference/eventsubscription.md
- FAQ: https://faq.lime-go.com/en/questions-and-answers-faq/integrations-and-api-keys

### 4.1 Autentisering och bas-URL

- `https://api.lime-go.com/v:version/...` [Läst]; versionsvärdet anges inte [Läst].
- `Authorization: go-api:<API_KEY>` utan mellanslag efter kolon, eller `apikey` som
  frågeparameter [Läst]. Nyckeln skapas under Settings > Integrations > Lime Go API-Keys
  [Läst]. En personlig nyckel begränsas av kontots rättigheter; en nyckel för icke-
  personliga åtgärder exponerar bara namn, e-post, taggar och egna fält för personer,
  **inte telefonnummer** [Sekundär, sökutdrag ur lime-go.readme.io].

### 4.2 Objekt och endpoints

- `GET /v:version/organizations` med frågeparametrar `name`, `registrationNumber`, `city`;
  söker först bland appens organisationer, sedan bland Bisnodes [Läst].
- `POST /v:version/organizations` (skapa) [Läst].
- `/deals` [Läst att den finns], personer via GraphQL [Läst; endpointens sökväg anges inte].
- `POST /v:version/event/subscription` [Läst].

### 4.3 JSON-form

Organisation, ordagrant ur referensen [Läst]:

```json
{ "id": "string", "name": "string", "registrationNumber": "string", "erpCustomerNumber": "string",
  "responsibleCoworker": "string", "phone": "string", "email": "string", "relation": 0,
  "postalAddress": { "street": "string", "zipCode": "string", "city": "string", "countryCode": "string" },
  "visitingAddress": { "street": "string", "zipCode": "string", "city": "string", "countryCode": "string" },
  "webSite": "string", "fax": "string" }
```

Skapa-kroppen använder PascalCase och `Relation` som sträng, t.ex. `"NoRelation"`, samt
`OrganizationNumber`, `IntegrationId`, `ListId`, `Tags` [Läst]:

```json
{ "Name": "Company Name", "OrganizationNumber": "111111-1111", "WebSite": "https://organizationswebsite.org",
  "Phone": "+46 1 111 111", "Email": "info@organizationswebsite.org", "ResponsibleCoworker": "Responsible Coworker",
  "PostalAddress": { "Street": "Street Name", "City": "City", "ZipCode": "111 11", "CountryCode": "SE" },
  "IntegrationId": "External system identity", "ListId": 1111, "Relation": "NoRelation", "Tags": ["tag1", "tag2"] }
```

- Orgnr: `registrationNumber` (läs) / `OrganizationNumber` (skriv) [Läst].
- Ägare: `responsibleCoworker` [Läst]. Kundstatus: `relation` (tal vid läsning, sträng
  vid skrivning) [Läst]. Talens betydelse är inte dokumenterad [Antaget: följer
  händelsenamnen nedan, NoRelation, WorkingOnIt, IsACustomer, WasACustomer, BeenInTouch].
- Tidsstämplar och egna fält finns inte i schemat [Läst].

### 4.4 Inkrementell synk och gränser

- Ingen ändringsström eller `updatedSince` dokumenterad [Läst att den saknas]. Readme:n
  nämner en "pull model" där man pollar API:t med jämna mellanrum [Sekundär].
- **10 anrop per minut** på `POST /organizations` [Läst]. Andra gränser ej dokumenterade.

### 4.5 Webhooks

- `POST https://api.lime-go.com/v:version/event/subscription`, kropp `targeturl`
  (absolut URL) och `events` (tom lista = alla; schemats standard `["All"]`) [Läst].
  Svar `{"id": SUBSCRIPTION_ID}`, `400` vid ogiltig URL [Läst].
- Händelser, ordagrant [Läst]: `OrganizationBeenInTouch`, `OrganizationHasNoRelation`,
  `OrganizationIsACustomer`, `OrganizationWasACustomer`, `OrganizationWorkingOnIt`,
  `DealWon`, `DealLost`, `DealStatusChange`, `CallPositive`, `CallNegative`,
  `MeetingBooked`, `MeetingReported`, `MeetingCancelled`.
- Nyttolast, signering, återförsök: inte dokumenterat [Läst att det saknas].

### 4.6 Radering och sammanslagning

Inte dokumenterat. Det finns ingen raderingshändelse bland händelserna [Läst].

### 4.7 Fällor

- Lime Go och Lime CRM är två olika produkter med olika API:er. `adaptrar.py:47-50` har
  bara `lime`; Lime Go behöver ett eget systemvärde, och CHECK-villkoret i
  `153_crm_grund.sql:54-56` måste då utökas.
- Händelserna handlar om relationsbyten, inte om ändrade fält: bra för "blev kund"/"slutade
  vara kund" (Iris-uteslutningen), dåliga för fältsynk.
- Utan ändringsfilter blir delta-synken en full läsning; med 10 skrivningar per minut är
  Lime Go olämplig som mål för utsynk [Antaget slutsats].

---

## 5. Upsales (API v2)

Källor:
- https://api.upsales.com/view/metadata/RW87rVf1 (Postman-dokumentation)
- Nango: https://nango.dev/docs/api-integrations/upsales.md
- Pipedream: https://pipedream.com/apps/upsales.md

### 5.1 Autentisering och bas-URL

- Bas-URL `https://integration.upsales.com/api/v2` [Läst ur exempel-URL:erna].
- Hemlig API-nyckel, hanteras under Settings av admin [Läst]. Hur den skickas står inte på
  sidan jag fick läsa [Läst att det saknas]; Pipedream skickar den som `Authorization:
  Bearer` via sin proxy [Sekundär]; `?token=` som frågeparameter är [Antaget].
- Testanrop: `GET /api/v2/self` [Sekundär, Pipedream].

### 5.2 Objekt och endpoints

`/accounts` (bolag), `/contacts`, `/order` [Läst]. Möjligheter, aktiviteter och möten
finns som objekt i Pipedreams åtgärder (appointment, opportunity, activity, phone call)
[Sekundär]; sökvägarna är [Antaget].

### 5.3 JSON-form

**Det officiella fältschemat gick inte att läsa.** Fältnamnen i `adaptrar.py:233-270`
(`orgNo`, `modDate`, `webpage`, `sniCode`, `addresses[type=Visit]`, `noEmployees`,
`turnover`, `journeyStep`, `users`, `active`, `firstName`, `cellPhone`, `client.id`) är
alla [Antaget] ur mitt perspektiv. Det enda bekräftade är `name`, `phone`, `users` på
bolag [Sekundär, Pipedream create-company] och `clientId`/`users` på möten [Sekundär].
**Öppen fråga:** be Buddy eller en Upsales-kund om ett riktigt `GET /accounts/{id}`-svar
innan Upsales-adaptern byggs.

### 5.4 Inkrementell synk, sidindelning, gränser

- Filter: `attribut=jämförelse:värde`, utan jämförelse = lika med; flera värden
  `attribut=jämförelse:1,2,3`; jämförelser `eq`, `ne`, `gt`, `gte`, `lt`, `lte` [Läst].
- Relaterade fält: `/contacts?client.custom=eq:4:1` [Läst]. Egna fält:
  `custom=jämförelse:fältId:värde`, t.ex. `custom=gte:1:2016-01-01` [Läst].
- Sidor: `limit` standard 1 000, **max 2 000**; `offset`; för fullständig hämtning sortera
  på id och filtrera `id=gt:SISTA_ID` [Läst].
- Filter på `modDate` står inte [Läst att det saknas]; `modDate=gte:<datum>` följer
  syntaxen men fältnamnet är [Antaget].
- Gränser per API-nyckel, fasta fönster [Läst]:

| Fönster | Gäller | Gräns |
|---|---|---|
| 10 s | alla anrop | 200 |
| 10 min | alla anrop | 6 000 |
| 1 h | alla anrop | 20 000 |
| 10 min | skrivningar | 2 000 |
| 1 h | skrivningar | 5 000 |

  Rubriker `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (sekunder);
  överskridning ger `429` med `ThrottleLimit` (errorCode 4) [Läst].

### 5.5 Webhooks

Inte hittat i API-dokumentationen. Pipedream har noll triggers för Upsales [Sekundär].
Upsales har automationer i produkten som kan anropa en URL [Antaget, ej uppslaget].

### 5.6 Radering och sammanslagning

Inte dokumenterat på sidorna jag läste. `DELETE` räknas som skrivning [Läst].

### 5.7 Fällor

- Egna fält adresseras med numeriskt `fieldId` [Läst i filtersyntaxen]; i posten ligger de
  troligen som en lista `custom: [{fieldId, value}]` [Antaget]. Mappningen måste lagra
  `fieldId`, och `adaptrar.py:529`-sökvägar som `custom[fieldId=12].value` fungerar redan
  syntaktiskt.
- Utan dokumenterat ändringsfält är `id=gt:`-stegning bara bra för nya poster; ändrade
  poster kräver `modDate` (overifierat) eller full läsning.

---

## 6. Salesforce (REST, Bulk API 2.0, Change Data Capture)

Varje developer.salesforce.com-sida svarade 403 på hämtning. Allt nedan är sökmotorns
utdrag ur de officiella sidorna; URL:en är den officiella sidans.

Källor:
- Get Updated: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_getupdated.htm
- Get Deleted: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_getdeleted.htm
- queryAll och merge: https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_calls_queryall.htm, https://developer.salesforce.com/docs/atlas.en-us.api.meta/object_ref/sforce_api_calls_merge.htm
- CDC-huvud: https://developer.salesforce.com/docs/atlas.en-us.change_data_capture.meta/change_data_capture/cdc_event_fields_header.htm
- Gap/overflow: https://developer.salesforce.com/docs/platform/change-data-capture/guide/cdc-other-events-gap.html
- Hållbarhet: https://developer.salesforce.com/docs/platform/pub-sub-api/guide/event-message-durability.html
- Bulk 2.0: https://developer.salesforce.com/docs/platform/salesforce-app-limits-cheatsheet/guide/salesforce-app-limits-platform-bulkapi.html, https://developer.salesforce.com/docs/platform/api-asynch/guide/query-get-job-results.html
- API-gränser: https://developer.salesforce.com/docs/platform/salesforce-app-limits-cheatsheet/guide/salesforce-app-limits-platform-api.html, https://developer.salesforce.com/docs/platform/api-rest/guide/headers-api-usage.html
- Versionspolicy: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/api_rest_eol.htm
- Utgåvor: https://developer.salesforce.com/blogs/2026/10/developers-guide-to-the-winter-27-release
- OAuth: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/quickstart_oauth.htm

### 6.1 Autentisering och bas-URL

- Token: `POST https://login.salesforce.com/services/oauth2/token`; **sandlåda
  `https://test.salesforce.com/services/oauth2/token`** [Läst i utdrag]. Svaret har
  `access_token` och `instance_url`; alla REST-anrop går till `instance_url`
  (My Domain, t.ex. `https://MyDomainName.my.salesforce.com`), sandlådor har formen
  `MyDomainName--SandboxName.sandbox.my.salesforce.com` [Läst i utdrag].
- JWT bearer: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`, JWT i
  `assertion` [Läst i utdrag]; ger ingen refresh-token [Sekundär].
- Webbserverflöde med `refresh_token`-omfång och klientcredentials-flöde finns [Antaget].
- Bas: `{instance_url}/services/data/vXX.X/` [Antaget mönster].

### 6.2 Objekt och endpoints

| Objekt | sObject | Exempel |
|---|---|---|
| Företag | `Account` | `GET /services/data/v66.0/sobjects/Account/{Id}` [Antaget] |
| Person | `Contact` (och `Lead`) | |
| Affär | `Opportunity` | |
| Aktivitet | `Task`, `Event` | |

SOQL: `GET /services/data/vXX.X/query?q=...`, `queryAll` för raderade [Antaget sökväg;
queryAll-semantiken Läst i utdrag].

### 6.3 JSON-form

Inte läst ordagrant (403). Standardfält [Antaget, men stämmer med `adaptrar.py:272-308`]:
`Id`, `Name`, `Phone`, `Website`, `BillingStreet`, `BillingPostalCode`, `BillingCity`,
`BillingCountry`/`BillingCountryCode`, `OwnerId`, `Type`, `NumberOfEmployees`,
`AnnualRevenue`, `LastModifiedDate`, `SystemModstamp`, `IsDeleted`, `MasterRecordId`.
REST-svaret har `attributes: {type, url}` överst [Antaget].
- **Orgnr och momsnr:** egna fält med suffixet `__c` [Antaget; namnen i `adaptrar.py:278-279`
  är gissningar].

### 6.4 Inkrementell synk, sidindelning, gränser

- **Get Updated:** `sobjects/{sObject}/updated/?start=…&end=…` ger id för tillagda/ändrade
  poster; finns från v31.0 (äldre sidor säger 29.0); högst 600 000 id annars
  `EXCEEDED_ID_LIMIT`; högst 30 dagar bakåt; använder `SystemModstamp` (annars
  `LastModifiedDate`); sekunder ignoreras; svaret har `ids` och `latestDateCovered`;
  full replikering kräver "View All Data" [Läst i utdrag].
- **Get Deleted:** `sobjects/{sObject}/deleted/?start=…&end=…` [Antaget form]; svaret
  `deletedRecords[{id, deletedDate}]`, `earliestDateAvailable`, `latestDateCovered`
  [Antaget].
- **SOQL-delta:** `WHERE SystemModstamp > :vattenmärke ORDER BY SystemModstamp` [Antaget].
- **Bulk API 2.0:** frågejobb förbrukar inte batcher (bara ingest gör det);
  1 TB resultat per rullande 24 h; resultat sidas med `maxRecords` och `Sforce-Locator`
  tills den är strängen `'null'` [Läst i utdrag]. Antal frågejobb per dygn finns i
  `/limits` som `DailyBulkV2QueryJobs` [Läst i utdrag; talet ej bekräftat].
- **API-gräns:** Enterprise Edition 100 000 anrop per rullande 24 h plus 1 000 per
  Salesforce-licens (15 licenser ger 115 000) [Läst i utdrag]. Rubriken
  `Sforce-Limit-Info: api-usage=10018/100000` [Läst i utdrag]. Över gränsen: `403` med
  `REQUEST_LIMIT_EXCEEDED` [Läst i utdrag, Salesforce-bloggen].

### 6.5 Change Data Capture (i stället för webhooks)

- CDC levereras via Pub/Sub API (gRPC) eller Streaming API (CometD), inte som HTTP-POST
  [Antaget, följer av dokumentationens upplägg]. Ingen HTTP-signatur behövs; klienten är
  autentiserad mot Salesforce.
- `ChangeEventHeader` [Läst i utdrag]: `entityName`, `recordIds`, `changeType`
  (`CREATE`, `UPDATE`, `DELETE`, `UNDELETE`, samt `GAP_CREATE`, `GAP_UPDATE`,
  `GAP_DELETE`, `GAP_UNDELETE`, `GAP_OVERFLOW`), `changeOrigin`, `transactionKey`,
  `sequenceNumber`, `commitTimestamp` (ms sedan 1970), `commitUser`, `commitNumber`,
  `nulledFields`, `diffFields`, `changedFields`.
- `recordIds` kan ha flera id när samma ändring gjorts på flera poster inom en sekund i
  samma transaktion [Läst i utdrag].
- Gap-händelser bär inga fältvärden: hämta posten [Läst i utdrag]. Över 100 000 ändringar
  i en transaktion ger overflow-händelser utan id [Läst i utdrag].
- `changeOrigin` används för att upptäcka egna ändringar och undvika slingor [Läst i
  utdrag]; viktigt när Snajp senare skriver tillbaka.
- **Lagring: 72 timmar** (inte garanterat längre); replay-id ska sparas som bytes, är
  opaka och inte löpande; `EARLIEST`/`LATEST` i `ReplayPreset` [Läst i utdrag].

### 6.6 Radering och sammanslagning

- `queryAll()` hittar poster raderade genom merge eller delete; Salesforce föreslår
  `isDeleted = true AND masterRecordId != null` med filter på `SystemModstamp` [Läst i
  utdrag]. Merge tar upp till tre poster per begäran [Läst i utdrag].
- Följd: en förlorare i merge syns som raderad med `MasterRecordId` = vinnaren. Adaptern
  ska då flytta det externa id:t till vinnarens post.

### 6.7 Fällor

- **API-version i URL:en.** v21.0–v30.0 är pensionerade sedan Summer '25 (REST ger
  `410 GONE`); v31.0–v40.0 blir ostödda Summer '27 och pensioneras Summer '28 [Läst i
  utdrag]. Aktuella: Spring '26 = v66.0, Summer '26 = v67.0, Winter '27 = v68.0 [Läst i
  utdrag]. Välj en version per anslutning och logga den.
- **Sandlåda** loggar in på annan värd och har annan My Domain [Läst i utdrag].
  Anslutningen behöver fältet "sandlåda ja/nej".
- `Get Updated` är begränsat till 30 dagar: en anslutning som stått still längre måste
  göra full synk.
- CDC måste slås på per objekt i Setup och finns i högre utgåvor [Antaget].
- `IsDeleted` syns bara via `queryAll`; `adaptrar.py:276` läser fältet men en vanlig
  `query` returnerar aldrig raderade poster [Antaget slutsats].

---

## 7. Twenty CRM (REST och GraphQL)

Källor:
- API: https://docs.twenty.com/developers/extend/api.md
- Import via API: https://docs.twenty.com/user-guide/data-migration/how-tos/import-data-via-api
- Webhooks: https://docs.twenty.com/developers/extend/webhooks.md
- Fältnamn (källkod, bara för interoperabilitet):
  https://raw.githubusercontent.com/twentyhq/twenty/main/packages/twenty-server/src/modules/company/standard-objects/company.workspace-entity.ts,
  https://raw.githubusercontent.com/twentyhq/twenty/main/packages/twenty-server/src/modules/person/standard-objects/person.workspace-entity.ts,
  och sammansatta typer under `packages/twenty-shared/src/types/composite-types/`
  (`address`, `links`, `emails`, `phones`).
- OpenAPI-speglar: https://apis.io/apis/twenty/twenty-companies-api/

### 7.1 Autentisering och bas-URL

- Moln `https://api.twenty.com/`, egen drift `https://{domän}/` [Läst].
- Core REST `/rest/`, Core GraphQL `/graphql/`, Metadata REST `/rest/metadata/`,
  Metadata GraphQL `/metadata/` [Läst].
- `Authorization: Bearer <API-nyckel>`; nyckeln skapas under Settings → Developers → API
  och visas en gång; kan begränsas med roll [Läst]. OAuth för appar som agerar åt
  användare finns men beskrivs inte [Läst].

### 7.2 Objekt och endpoints

- `GET /rest/companies`, `/rest/people`, `/rest/opportunities`, `/rest/notes`,
  `/rest/tasks` [Antaget utom companies och people, som är Lästa i exempel/spegel].
- `fields`-parameter: `GET /rest/people?fields=id,name,emails,company`; `id` kommer alltid;
  sammansatta fält väljs med föräldranamnet; många-till-en ger join-kolumnen (`companyId`)
  vid `depth=0`; en-till-många bara vid `depth=1` [Läst]. Okänt fält ger `400` [Läst].
  Utan `fields` på objekt med över 200 läsbara fält kommer 200 standardfält, inklusive
  `id`, `createdAt`, `updatedAt`, `deletedAt`, `position` [Läst].
- GraphQL: batch-upsert med pluralnamn som `CreateCompanies` [Läst].
- Arbetsytans egen API-dokumentation och lekplats finns under Settings → Developers → API
  [Läst].

### 7.3 JSON-form

Fältnamn ur källkoden [Läst i källkod]; exemplet är **ihopsatt av mig**:

```json
{
  "id": "6f1c…", "name": "Exempelbolaget AB",
  "domainName": { "primaryLinkUrl": "https://exempel.se", "primaryLinkLabel": "", "secondaryLinks": [] },
  "address": { "addressStreet1": "Storgatan 1", "addressStreet2": null, "addressCity": "Umeå",
               "addressPostcode": "90326", "addressState": null, "addressCountry": "Sweden",
               "addressLat": null, "addressLng": null },
  "linkedinLink": { "primaryLinkUrl": "", "primaryLinkLabel": "", "secondaryLinks": [] },
  "annualRevenue": { "amountMicros": null, "currencyCode": "SEK" },
  "accountOwnerId": "…", "createdAt": "…", "updatedAt": "…", "deletedAt": null
}
```

Person: `name` (`firstName`, `lastName`), `emails` (`primaryEmail`, `additionalEmails`),
`phones` (`primaryPhoneNumber`, `primaryPhoneCountryCode`, `primaryPhoneCallingCode`,
`additionalPhones`), `jobTitle`, `companyId`, `linkedinLink` [Läst i källkod]. Undertypen
för valuta (`amountMicros`, `currencyCode`) är [Antaget].

- Orgnr/momsnr: inga standardfält; eget fält i arbetsytan [Antaget].
- Domän: `domainName.primaryLinkUrl`; domäner är unika inom Companies, e-post unik inom
  People [Läst, llms-full.txt].
- Ägare: `accountOwnerId` → arbetsytemedlem [Läst i källkod].
- Kundstatus: inget standardfält [Läst i källkod; `idealCustomerProfile` finns inte på
  main].
- **`employees` finns inte på `CompanyWorkspaceEntity` i main** [Läst i källkod].
  `adaptrar.py:323` läser `employees`, vilket då bara träffar arbetsytor som har ett eget
  fält med det namnet.
- `phones` lagrar landskoden separat; `adaptrar.py:334` sammanfogar
  `primaryPhoneCallingCode` + `primaryPhoneNumber`, vilket stämmer med typen.

### 7.4 Inkrementell synk, sidindelning, gränser

- **100 anrop per minut; upp till 60 poster per anrop** för skapa/uppdatera/radera i både
  REST och GraphQL; ≈ 6 000 poster per minut; minst 600 ms mellan anrop vid långa
  importer; exponentiell backoff på `429` [Läst].
- Sidindelning: speglade OpenAPI-specar visar `limit`, `starting_after`, `ending_before`
  och svaret `pageInfo` (`hasNextPage`, `startCursor`, `endCursor`) samt `totalCount`
  [Sekundär]. En annan spegel visar `after` i stället [Sekundär]. **Verifiera mot
  arbetsytans egen dokumentation.**
- Filter: `filter=updatedAt[gte]:"…"`-liknande syntax [Antaget; speglarna visar
  `name[eq]:Acme` respektive `filter[email][contains]`].

### 7.5 Webhooks

- Skapas i Settings → Developers → Webhooks; aktiv direkt; inget API beskrivs [Läst].
  Alla händelsetyper skickas, filtrering "may be added in future releases" [Läst].
- Händelser `{objekt}.{åtgärd}`: `person.created`, `company.created`, `note.created`,
  `person.updated`, `company.updated`, `opportunity.updated`, `person.deleted`,
  `company.deleted` [Läst]. `.destroyed`/`.restored` nämns inte [Läst att de saknas].
- Nyttolast, ordagrant [Läst]:

```json
{ "event": "person.created",
  "data": { "id": "abc12345", "firstName": "Alice", "lastName": "Doe", "email": "alice@example.com",
            "createdAt": "2025-02-10T15:30:45Z", "createdBy": "user_123" },
  "timestamp": "2025-02-10T15:30:50Z" }
```

  Observera att exemplet har platta `firstName`/`email`, medan REST har sammansatta
  `name.firstName`/`emails.primaryEmail` [Läst båda]. Adaptern ska hämta posten via REST
  efter en webhook i stället för att lita på nyttolastens form [Antaget slutsats].
- Signering [Läst]: `X-Twenty-Webhook-Signature` = hex HMAC-SHA256(secret,
  `{timestamp}:{JSON}`), `X-Twenty-Webhook-Timestamp`. Hookdeck anger tidsstämpeln i
  millisekunder [Sekundär]. Signeras bara när webhooken har en secret [Sekundär].
- Återförsök: inte beskrivna; icke-2xx loggas som misslyckad leverans [Läst].

### 7.6 Radering och sammanslagning

Mjuk radering via `deletedAt` [Läst att fältet finns]. `*.deleted` som händelse [Läst].
Sammanslagning: inte dokumenterad för API:t [Läst att det saknas].

### 7.7 Fällor

- Låg gräns: en kund med 50 000 poster tar ≈ 9 minuter i bästa fall bara att läsa
  (500 sidor om 60 är [Antaget]; läsningens sidstorlek är inte dokumenterad).
- Webhook-nyttolasten följer inte REST-formen.
- Arbetsytor kan ha egna objekt och fält; Metadata-API:t ger dem.

---

## 8. SuperOffice (REST WebAPI, webhooks)

Källor:
- Contact: https://docs.superoffice.com/en/api/reference/restful/rest/contact/get-contact-entity.md
- REST-index: https://docs.superoffice.com/en/api/reference/restful/rest/index.html
- OData-sök: https://docs.superoffice.com/en/api/search/odata.md
- Webhook-notiser: https://docs.superoffice.com/en/automation/webhook/dev/notification.md
- Webhook-säkerhet: https://docs.superoffice.com/en/automation/webhook/dev/security.md
- Kontakthändelser: https://docs.superoffice.com/en/automation/webhook/reference/contact-events.md
- Person-/säljhändelser: https://docs.superoffice.com/en/automation/webhook/reference/person-events.md, https://docs.superoffice.com/en/automation/webhook/reference/sale-events.html
- Autentisering online: https://docs.superoffice.com/en/api/authentication/online
- Miljöer: https://docs.superoffice.com/en/developer-portal/getting-started/app-envir.html
- Arkivleverantören Contact: https://docs.superoffice.com/en/api/archive-providers/reference/contact.md

### 8.1 Autentisering och bas-URL

- CRM Online: OAuth 2.0/OpenID Connect för användare; **System User-flödet** för
  bakgrundsintegrationer [Läst i utdrag]. Icke-interaktivt: `SOTicket`-header plus
  app-token (`SO-AppToken`) [Läst i utdrag].
- Bas-URL per kund (context identifier, t.ex. `Cust12345`): utveckling
  `https://sod.superoffice.com/Cust12345`, stage `https://qaonline.superoffice.com/...`,
  produktion `https://online.superoffice.com/Cust12345` [Läst i utdrag]. Värdnamn utan
  siffra är reserverade för inloggning; API-anrop ska gå till kundens numrerade värd, som
  slås upp via `https://[miljö].superoffice.com/api/state/[Cust00000]` [Läst i utdrag].
- Authorize: `https://sod.superoffice.com/login/{contextIdentifier}/oauth/authorize`
  [Läst i utdrag].
- Contact-sidan listar SOPassword (Basic) och SuperId (OAuth2 implicit, bearer) [Läst].
  Rubriker `Accept-Language`, `SO-Language`, `SO-Culture`, `SO-TimeZone`, `SO-AppToken`
  [Läst].

### 8.2 Objekt och endpoints

- `GET /api/v1/Contact/{id}` (bolag), med `$select` och `fk`; `304` vid If-Modified-Since
  [Läst]. `/api/v1/Contact/default` ger tom entitet, `/api/v1/Contact/123/Simple` en
  förenklad som inte kan ändras [Läst i utdrag].
- `/api/v1/Contact` ger ett OData-flöde; `$select`, `$filter`, ordning; exempel
  `$filter=registeredDate before '2021-1-1'&$select=name,category` [Läst i utdrag].
  `$top`, `$skip` [Läst i utdrag].
- Person `/api/v1/Person`, försäljning `/api/v1/Sale`, aktivitet `/api/v1/Appointment`
  [Antaget efter mönstret].

### 8.3 JSON-form

`ContactEntityWithLinks` [Läst fältnamn]: `ContactId`, `Name`, `Department`, `OrgNr`,
`Number1`, `Number2`, `UpdatedDate`, `CreatedDate`, `Emails`, `Urls`, `Phones`, `Faxes`
(listor av `{Value, StrippedValue, Description}`), `Associate`, `CreatedBy`, `UpdatedBy`,
`Business`, `Category`, `Country`, `Address` (`Street`, `Postal`, `Formatted`,
`Wgs84Latitude`, `Wgs84Longitude`), `ActiveStatusMonitorId`, `Deleted`, `CustomFields`
(gällande), `UserDefinedFields` och `ExtraFields` (båda föråldrade), `Persons`,
`Description`, `_Links`. `OrgNr` beskrivs som "VAT number or similar" och exempelvärden är
`"987654321"`, `"1723426"`, `""` [Läst i utdrag].

Utdrag i den formen (värden från dokumentationens exempel, resten utelämnat):

```json
{ "ContactId": 994863, "Name": "…", "Department": "", "OrgNr": "987654321", "Number1": "…",
  "UpdatedDate": "…", "Phones": [{ "Value": "…", "StrippedValue": "…", "Description": "" }],
  "Category": { … }, "Associate": { … }, "Deleted": false, "CustomFields": { … } }
```

- Orgnr: `OrgNr` [Läst]. Momsnr: inget eget fält; `OrgNr` kan innehålla momsnumret
  ("VAT number or similar") [Läst]. `falt.orgnr` (`falt.py:64-86`) tar redan
  `SE556824902201`.
- Ägare: `Associate` [Läst]. Kundstatus: `Category` (kundens egen lista) [Läst fältet;
  att den används som kundstatus är Antaget].
- Underfälten i `Address.Street`/`Address.Postal` (`Address1`, `Zipcode`, `City`) och
  `Country.TwoLetterISOCountry`, `Associate.FullName` är [Antaget], som i
  `adaptrar.py:347-355`.

### 8.4 Inkrementell synk, sidindelning, gränser

- `updatedDate` finns i arkivleverantören Contact som "date/time the data was last
  updated in UTC" [Läst i utdrag]. Delta via `$filter=updatedDate afterTime '…'` [Antaget
  operatornamn; dokumentationen visar `before`].
- Sidor: `$top`, `$skip` [Läst i utdrag].
- Hastighetsgränser: inga siffror hittade [Läst att de saknas]. Bästa praxis: kontrollera
  kundens tillstånd innan anrop [Läst i utdrag].

### 8.5 Webhooks

- Händelser för Contact [Läst]: `contact.created`, `contact.changed`,
  `contact.softdeleted` (raderad i gränssnittet), `contact.deleted` (permanent raderad
  av systemet). Person: `person.created`, `person.deleted`, `person.consented`,
  `person.unconsented` m.fl.; Sale: `sale.created`, `sale.changed`, `sale.deleted`,
  `sale.sold`, `sale.lost`, `sale.completed` [Läst i utdrag]. Entiteter: Activity,
  Associate, Contact, Chat, Document, Person, Project, ProjectMember, Quote, Sale,
  SaleStakeholder, Ticket [Läst].
- Nyttolast (`WebhookPayload`) [Läst]: `EventId`, `Timestamp`, `Event`, `Entity`,
  `PrimaryKey`, `Changes`, `FieldValues`, `ContextIdentifier`, `ChangedByAssociateId`,
  `WebhookName`. Utdrag ur dokumentationen [Läst]:

```json
"EventId": "8337ae4a-1dd6-40fd-8dc7-a050664a0af7", "Event": "contact.changed",
"PrimaryKey": 994863, "Entity": "contact", "ContextIdentifier": "Cust1234", "ChangedByAssociateId": 316
```

- Rubriker: `X-SuperOffice-Event`, `X-SuperOffice-EventId`, `X-SuperOffice-Retry`,
  `X-SuperOffice-Signature` [Läst].
- Signering: när webhooken har en secret, base64(HMAC-SHA256(secret, JSON-kroppen)) i
  `X-SuperOffice-Signature` [Läst i utdrag].
- Återförsök [Läst]: tre försök per cykel (andra efter 1 s, tredje efter 4 s), sedan längst
  bak i kön; nio misslyckade i följd sätter tillståndet `TooManyErrors (3)`; mottagaren
  måste sätta `Active (1)` igen; efter tre misslyckade försök kastas händelsen och nästa
  försök får nytt EventId.
- Personändringar kan ge `contact.changed` med `Event = person.changed` och dubbletter
  [Sekundär, SuperOffice-forum].

### 8.6 Radering och sammanslagning

Två nivåer: `contact.softdeleted` (papperskorg) och `contact.deleted` (permanent) [Läst].
`Deleted` på entiteten [Läst]. Sammanslagning: ingen merge-händelse dokumenterad [Läst
att den saknas].

### 8.7 Fällor

- Kundens API-värd kan flytta; slå upp den via state-URL:en i stället för att lagra den
  fast.
- `contact.softdeleted` ska ge `raderad_at` men kunna ångras; `contact.deleted` är slutlig.
- `UserDefinedFields`/`ExtraFields` är föråldrade men finns i äldre installationer; läs
  `CustomFields` först.

---

## 9. Microsoft Dynamics 365 (Dataverse Web API)

Källor:
- Ändringsspårning: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/use-change-tracking-synchronize-data-external-systems
- Skyddsgränser: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/api-limits
- Dagsgränser: https://learn.microsoft.com/en-us/power-platform/admin/api-request-limits-allocations
- Webhooks: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/use-webhooks, https://learn.microsoft.com/en-us/power-apps/developer/data-platform/register-web-hook
- Account: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/account
- OAuth: https://learn.microsoft.com/powerapps/developer/data-platform/authenticate-oauth

### 9.1 Autentisering och bas-URL

- Bas-URL `[Organization URI]/api/data/v9.2/` (exemplen använder även `v9.0`) [Läst].
- Server-till-server: en applikationsanvändare kopplad till Entra ID-registreringen måste
  skapas i varje Dataverse-miljö och få säkerhetsroller; delegerade behörigheter behövs
  inte [Läst i utdrag, Microsoft Learn-modulen]. Omfång `<miljö-URL>/.default` mot
  `login.microsoftonline.com/{tenant}/oauth2/v2.0/token` [Sekundär, n8n och Microsoft Q&A].
  Kontrollera med `WhoAmI` [Sekundär].

### 9.2 Objekt och endpoints

`accounts`, `contacts`, `opportunities`, aktiviteter (`activitypointers`, `phonecalls`,
`emails`, `appointments`, `tasks`), anteckningar `annotations` [Antaget utom `accounts`,
som är Läst i exemplen].

### 9.3 JSON-form

Account, ordagrant ur ändringsspårningsexemplet [Läst]:

```json
{ "@odata.context": "[Organization URI]/api/data/v9.0/$metadata#accounts(name,accountnumber,telephone1,fax)",
  "@odata.deltaLink": "[Organization URI]/api/data/v9.0/accounts?$select=name,accountnumber,telephone1,fax&$deltatoken=919042%2108%2f22%2f2017%2008%3a10%3a44",
  "value": [ { "@odata.etag": "W/\"915244\"", "name": "Monte Orton", "accountnumber": null,
               "telephone1": "555000", "fax": "10101", "accountid": "60c4e274-0d87-e711-80e5-00155db19e6d" } ] }
```

Kolumner på `account` [Läst]: `accountid`, `name` (max 160), `accountnumber` (max 20),
`telephone1`, `emailaddress1`, `websiteurl`, `address1_line1`, `address1_city`,
`address1_postalcode`, `address1_country`, `ownerid` (systemuser eller team), `statecode`
(0 Active, 1 Inactive), `statuscode` (1 Active, 2 Inactive), `customertypecode` (1–12:
Competitor, Consultant, Customer, Investor, Partner, Influencer, Press, Prospect,
Reseller, Supplier, Vendor, Other), `modifiedon`, `createdon`, `masterid`, `merged`,
`parentaccountid`, `numberofemployees`, `primarycontactid`.

- Orgnr/momsnr: inga standardkolumner; `accountnumber` är kundnummer [Antaget]. Egen
  kolumn med prefix, t.ex. `new_orgnr` [Antaget].
- Ägare i Web API: `_ownerid_value` [Antaget, OData-konventionen].
- Contact: `firstname`, `lastname`, `emailaddress1`, `telephone1`, `mobilephone`,
  `jobtitle`, `_parentcustomerid_value`, `donotemail` [Antaget] (som `adaptrar.py:391-402`).

### 9.4 Inkrementell synk, sidindelning, gränser

- Slå på **Track changes** per tabell (`EntityMetadata.ChangeTrackingEnabled = true`);
  går inte att stänga av igen [Läst]. Kontroll:
  `GET .../EntityDefinitions?$select=SchemaName&$filter=ChangeTrackingEnabled eq true` [Läst].
- Första anropet med `Prefer: odata.track-changes` ger `@odata.deltaLink` med
  `$deltatoken`; nästa anrop på länken ger ändringar och en ny länk [Läst].
- `$filter`, `$orderby`, `$expand`, `$top` stöds inte med ändringsspårning [Läst].
- Token gäller som standard **7 dagar** (`Organization.ExpireChangeTrackingInDays`); äldre
  ger undantag [Läst]. Nya/ändrade kommer före raderade [Läst]. Antal ändringar:
  `accounts/$count?$deltatoken=…` [Läst].
- Skyddsgränser per användare och webbserver, 5 minuters glidande fönster [Läst]:
  6 000 anrop, 20 minuter (1 200 s) sammanlagd körtid, 52 samtidiga anrop. Fel: `429` med
  `Retry-After` i sekunder; koder `-2147015902`, `-2147015903`, `-2147015898` [Läst].
  Rubriker `x-ms-ratelimit-burst-remaining-xrm-requests`,
  `x-ms-ratelimit-time-remaining-xrm-requests` (bara för felsökning) [Läst]. Batch upp
  till 1 000 operationer [Läst].
- Dagsgränser: applikationsanvändare delar tenantens pool, Dynamics 365 Enterprise/
  Professional: 500 000 bas + 5 000 per licens, högst 10 000 000 per 24 h [Läst].

### 9.5 Webhooks

- Registreras med Plug-in Registration Tool (Register New WebHook): namn, URL,
  autentisering; bara port 80/443 [Läst]. Lagras i `serviceendpoint` med `contract = 8`
  [Läst]. Steg registreras per meddelande (Create, Update, Delete …) och tabell, med
  filterattribut, steg i pipelinen och läge synkront/asynkront [Läst].
- Autentisering [Läst]: `HttpHeader` (nyckel-värdepar i header), `WebhookKey`
  (`?code=…`), `HttpQueryString`. **Ingen signering**; mottagaren ansvarar för att avvisa
  fel nyckel [Läst].
- Rubriker [Läst]: `x-ms-dynamics-organization`, `x-ms-dynamics-entity-name`,
  `x-ms-dynamics-request-name`, `x-ms-correlation-request-id`,
  `x-ms-dynamics-msg-size-exceeded` (vid över 256 KB, då tas `ParentContext`,
  `InputParameters`, `PreEntityImages`, `PostEntityImages` bort).
- Kropp: JSON av `RemoteExecutionContext`: `MessageName`, `PrimaryEntityName`,
  `PrimaryEntityId`, `InputParameters[{key:"Target", value:{Attributes:[{key,value}],
  LogicalName, Id}}]`, `PreEntityImages`, `PostEntityImages`, `OperationCreatedOn`
  (`"\/Date(1506409448000-0700)\/"`), `UserId`, `OrganizationId`, `Stage`, `Mode`
  [Läst, se hela exemplet på sidan].
- Timeout 60 s; bara `502`, `503`, `504` ger ett enda nytt försök; asynkrona fel syns i
  System Jobs (`asyncoperations`, `statuscode eq 31`) [Läst].

### 9.6 Radering och sammanslagning

- I delta: `{ "@odata.context": ".../$metadata#accounts/$deletedEntity", "id": "…",
  "reason": "deleted" }` [Läst].
- Merge: meddelandet `Merge` finns på account [Läst]; `merged` (bool) och `masterid`
  (lookup till vinnaren) visar att en post slagits ihop [Läst]. Att förloraren
  inaktiveras (`statecode = 1`) är [Antaget].

### 9.7 Fällor

- `adaptrar.py:374` och `:394` tolkar `statecode = 1` som raderad. Det betyder
  **inaktiv**, inte raderad [Läst om statecode]. En inaktiv kund är snarare
  `tidigare_kund`; raderad kommer som `$deletedEntity`.
- `customertypecode` är en lista med tal; uppslaget i `adaptrar.py:386-388` (3 kund,
  8 prospekt, 5 och 9 partner, 10 och 11 leverantör, 12 övrigt) stämmer med ordningen i
  referensen om talen följer listan 1–12 [Läst ordningen; att talen är 1..12 i den ordningen
  är Läst som "Values 1–12"].
- 7-dagarstoken: en anslutning som stått still längre måste göra full läsning.
- Webhooks kräver Plug-in Registration Tool hos kunden; det är kundens admin som gör det.

---

## 10. Fortnox (kundregistret, `/3/customers`)

Källor:
- Gränser: https://www.fortnox.se/developer/guides-and-good-to-know/rate-limits-for-fortnox-api
- Parametrar: https://fortnox.se/developer/guides-and-good-to-know/parameters
- WebSockets: https://fortnox.se/developer/guides-and-good-to-know/websockets
- Auktorisering: https://fortnox.se/developer/authorization, https://www.fortnox.se/developer/authorization/get-access-token-using-client-credentials, https://www.fortnox.se/developer/guides-and-good-to-know/scopes
- API-referens: https://api.fortnox.se/apidocs
- Fältnamn: Ruby-klienten accodeing/fortnox-api, https://raw.githubusercontent.com/accodeing/fortnox-api/master/lib/fortnox/api/models/customer.rb

### 10.1 Autentisering och bas-URL

- Bas `https://api.fortnox.se/3/`, kunder `/3/customers` [Sekundär, apis.io; parametersidans
  exempel använder `https://api.fortnox.se/3/invoices/`, Läst].
- OAuth: authorize `https://apps.fortnox.se/oauth-v1/auth`, token
  `POST https://apps.fortnox.se/oauth-v1/token` med base64(client_id:client_secret)
  [Läst i utdrag]. Åtkomsttoken 1 timme, refresh-token 45 dagar och roterar vid varje
  förnyelse (den gamla blir ogiltig) [Läst i utdrag]. Ett klientcredentials-flöde för
  tjänstekonton finns [Läst att sidan finns]. Omfång mellanslagsseparerade, skiftläges-
  känsliga, t.ex. `customer`, `companyinformation` [Läst i utdrag].

### 10.2 Objekt och endpoints

`GET /3/customers` (lista), `GET /3/customers/{CustomerNumber}`, `POST`, `PUT`, `DELETE`
[Läst operationsnamnen; sökvägarna Antaget efter mönstret]. Fortnox har ingen person-,
affärs- eller aktivitetsmodell i kundregistret; kontaktuppgifter ligger på kunden
[Antaget].

### 10.3 JSON-form

Fältnamn ur Ruby-klienten [Sekundär]: `Url` (skrivskyddad, i JSON `@url` [Antaget]),
`CustomerNumber`, `Name`, `OrganisationNumber`, `VATNumber`, `VATType`, `Type`,
`Address1`, `Address2`, `ZipCode`, `City`, `Country` (skrivskyddad), `CountryCode`,
`Phone1`, `Phone2`, `Fax`, `Email`, `EmailInvoice`, `VisitAddress`, `VisitZipCode`,
`VisitCity`, `VisitingCountryCode`, `DeliveryAddress1` …, `OurReference`,
`YourReference`, `Currency`, `PriceList`, `TermsOfPaymentCode`, `Comments`.
`Active` är bekräftat i en annan integrations mappning [Sekundär, Younium]. **`WWW` står
inte i Ruby-modellen** [Sekundär]; `adaptrar.py:415` läser `WWW` [Antaget att fältet finns].
Inget ändringsdatum på kunden.

Exempel, **ihopsatt av mig** ur namnen:

```json
{ "Customer": { "CustomerNumber": "1001", "Name": "Exempelbolaget AB", "OrganisationNumber": "556824-9022",
  "VATNumber": "SE556824902201", "Type": "COMPANY", "Active": true, "Address1": "Storgatan 1",
  "ZipCode": "903 26", "City": "Umeå", "CountryCode": "SE", "Phone1": "090-12 34 56",
  "Email": "info@exempel.se", "OurReference": "Anna" } }
```

`Type`-värdena (`COMPANY`/`PRIVATE`) är [Antaget]; `adaptrar.py:409` hoppar över
`private`.

### 10.4 Inkrementell synk, sidindelning, gränser

- `lastmodified=2019-03-10 12:30` (format `YYYY-MM-DD HH:MM`) ger poster ändrade sedan dess,
  kan kombineras med resursens `filter`; sökparametrar bara med gemener [Läst].
- `limit` standard 100, 1–500; `offset` standard 0; `page`; `sortby`, `sortorder`
  (`ascending`/`descending`) [Läst]. Kundfiltret `active`/`inactive` [Sekundär].
  `MetaInformation` med `@TotalPages` [Sekundär, exempel för fakturor].
- **300 anrop per minut per klient-id och tenant, glidande 5-sekundersfönster = 25 per
  5 s**; gränsen är per åtkomsttoken, inte per IP; `429` vid överskridning [Läst].

### 10.5 Ändringshändelser (WebSocket, inte webhook)

- `wss://ws.fortnox.se/topics-v1` [Läst]. Kommandot `add-tenants-v1` har
  `clientSecret`, `accessTokens` (`"Bearer …"`), `includeChildTenants`; svar `tenantIds`
  eller `invalidTokens` [Läst]. Därefter lägga till ämnen och starta prenumeration
  (kommandonamnen visas inte) [Läst].
- Meddelande: `topic`, `offset`, `type`, `tenantId`, `entityId`, `timestamp` [Läst].
- Kundhändelser: `customer-created-v1`, `customer-updated-v2`, `customer-deleted-v1` [Läst].
- Minst en gång-leverans (dubbletter möjliga), ordning garanterad per ämne, unik offset;
  replay upp till **14 dagar** bakåt med sparad offset [Läst].
- Ingen signering behövs; anslutningen är autentiserad [Antaget slutsats].

### 10.6 Radering och sammanslagning

`customer-deleted-v1` [Läst]. Ingen merge i Fortnox [Antaget]. Inaktiverade kunder har
`Active: false` [Sekundär].

### 10.7 Fällor

- Kundregistret innehåller privatpersoner; de är personuppgifter och ska inte in som bolag
  utan rättslig grund. `Type` är nyckeln [Antaget värde].
- `CustomerNumber` är kundens egen nummerserie och kan ändras [Antaget]; den är ändå det
  enda id:t.
- En WebSocket-lyssnare måste vara en långlivad process. Backend kör på Railway; en
  sådan process kräver en egen tjänst eller ett jobb som återansluter med sparad offset
  [Antaget, ej undersökt i repot].

---

## 11. Visma eEkonomi (Spiris, eAccounting API v2) och Visma.net ERP

Två olika produkter. `adaptrar.py:425-445` har ett gemensamt `visma` som följer eEkonomis
fältnamn; Visma.net behöver en egen mappning.

### 11.1 Visma eEkonomi / Spiris

Källor:
- Migrationsguide: https://developer.vismaonline.com/docs/v2-migration-guide
- Autentisering: https://developer.vismaonline.com/docs/authentication, https://developer.vismaonline.com/docs/change-to-our-new-identity-server
- Fältnamn: Python-klienten `visma`, https://visma.readthedocs.io/en/latest/_modules/visma/models.html
- Integrationsguide: https://www.apideck.com/blog/visma-eaccounting-api-integration

Autentisering och bas-URL:
- `https://eaccountingapi.vismaonline.com/v2/customers`; v1 avvecklades 30 juni 2023;
  `GET /v1/customerlistitems` motsvaras av `GET /v2/customers` [Läst i utdrag].
- OAuth via `identity.vismaonline.com/connect/authorize`, `response_type=code`;
  obligatoriska omfång `ea:api` och `offline_access`; valbara `ea:sales`, `ea:purchase`,
  `ea:accounting` och `_readonly`-varianter [Läst i utdrag]. Kräver medlemskap i Spiris
  partnerprogram [Sekundär]. Produkten heter Spiris i vissa marknader [Sekundär].

JSON-form, fältnamn [Sekundär]: `Id`, `CustomerNumber`, `CorporateIdentityNumber`,
`VatNumber`, `Name`, `EmailAddress`, `EmailAddresses`, `Telephone`, `MobilePhone`,
`WwwAddress`, `InvoiceAddress1`, `InvoiceAddress2`, `InvoicePostalCode`, `InvoiceCity`,
`InvoiceCountryCode`, `DeliveryAddress1` …, `ContactPersonName`, `ContactPersonEmail`,
`ContactPersonPhone`, `ContactPersonMobile`, `IsPrivatePerson`, `IsActive`, `ChangedUtc`,
`LastInvoiceDate`, `CustomerLabels`, `Note`. Svaret har en `Data`-lista plus
sidmetadata [Sekundär].

Synk och gränser: `ChangedUtc` är ändringsfältet [Sekundär]; filtersyntaxen (OData
`$filter=ChangedUtc gt …`, sidparametrar) är [Antaget]. 600 anrop per minut per klient
och endpoint, felkod 4010 [Sekundär].

Webhooks: en betasida finns (developer.vismaonline.com/docs/webhooks) men svarade 404;
eEkonomi "will send a HTTP POST payload to the URL configured in your subscription"
[Läst i utdrag]. Signering ej verifierad.

Radering: `IsActive: false` för inaktiverade [Antaget]; hur en raderad kund syns är inte
dokumenterat i det jag läste.

### 11.2 Visma.net ERP (Financials)

Källor:
- Kund: https://docs.vismasoftware.no/vismanetapi/how-tos/customerledgerendpoint/customer/
- Sidor: https://docs.vismasoftware.no/vismanetapi/how-tos/pagination/
- Datumvillkor: https://docs.vismasoftware.no/vismanetapi/how-tos/date-time-condition-operators/
- Gränser: https://docs.vismasoftware.no/vismanetapi/ratelimits/
- Webhooks: https://docs.vismasoftware.no/vismanetapi/webhooks/, https://docs.vismasoftware.no/vismanetapi/webhooks/event-and-entities/
- OAuth: https://docs.vismasoftware.no/vismanetapi/authentication/oauth/

- Bas `https://api.finance.visma.net/v1/customer` [Läst i utdrag]. Gammal domän strypt till
  500 anrop per timme per applikation [Läst i utdrag].
- Ändringar: `lastModifiedDateTime` (format `YYYY-MM-DD`) + `lastModifiedDateTimeCondition`
  (t.ex. `>=`); samma operatorer för `createdDateTimeCondition` [Läst i utdrag].
- Sidor: `pageSize` och `pageNumber` är **obligatoriska** på listor; ett exempel använder
  `pageNum` [Läst i utdrag]. Max `pageSize` ej angivet.
- Gräns: "X requests per hour" per bolag och klient, talet hemligt, aktuellt läge i
  svarsrubrikerna [Läst i utdrag]. Äldre siffror 15 000/h (produktion, 2020) och 500/h
  (testklient, 2021) [Sekundär, Visma-forum].
- Webhooks via Visma Developer Portal [Läst]. Kundhändelser: `Customer, Changed`
  (skapad eller uppdaterad), `Customer, Created`, `Customer, Updated`, `Customer, Action
  Triggered` [Läst]. `Changed`-nyttolasten: `NotificationId`, `contextId`, `event`,
  `action`, `resourceId`, `resourceUri`, `relativeResourceUri`, `timeStamp`, `ApiClientId`,
  `TenantId`, `IsScheduler`, `ConnectId`. Created/Updated/Deleted: `event`, `companyId`,
  `entityId`, `notificationId`, `entityLocation` (under `api/v1/customer/`), `erpEvent`,
  `erpDocumentStatus`, `documentStatus`, `UserId`, `timeStamp`, `apiClientId`,
  `TenantId`, `ConnectId`, `ischeduler`; t.ex. `"event": "Customer_Updated"` [Läst].
  Avsändar-IP: 18.202.121.26, 34.242.104.102, 54.220.26.45 [Läst]. Signering och
  återförsök: ej nämnda [Läst att de saknas]. Visma Connect beskriver HMAC-SHA256 base64
  med webhook-secret [Sekundär, https://docs.connect.visma.com/using-a-webhook-secret];
  rubrikens namn ej funnet.
- Kundens fältnamn (`number`, `name`, `corporateId`, `vatRegistrationId`, `mainAddress`,
  `mainContact`) är [Antaget]; ingen sida med kundens JSON gick att läsa.

---

## 12. Kanonisk inflödesmodell

### 12.1 Principer

1. **Externt id = `(anslutning_id, objekt, externt_id)`**, som i `crm_externa_id`
   (`153_crm_grund.sql:154-173`). `anslutning_id` bär källsystemet
   (`crm_anslutningar.system`, `153_crm_grund.sql:42`). Det kanoniska objektet har därför
   `kalla = {system, anslutning_id, externt_id}`.
2. **Orgnr är matchningsnyckeln** för bolag: `orgnr_nyckel` tio siffror, unik per tenant
   bland levande rader (`153_crm_grund.sql:113-115`), framtagen av `falt.orgnr`
   (`falt.py:64-86`). Utan orgnr matchas i ordningen externt id → domän
   (`crm_bolag_doman_idx`, `:117`) → namnnyckel (`:116`). Personer matchas på e-post
   (`crm_personer_epost_uq`, `:146-148`).
3. **Fältet styr tolkningen**, inte mappningen (`adaptrar.py:25-27`): orgnr går alltid
   genom `falt.orgnr`, telefon genom `falt.telefon` (`falt.py:115`).
4. **Ett fält som inte går att tolka hoppas över, inte posten** (`falt.py:9-12`,
   `adaptrar.py:626-627`).

### 12.2 CanonicalCompany (motsvarar `crm_bolag`)

| Fält | Typ | Kommentar |
|---|---|---|
| `kalla.system` | text | `hubspot`, `pipedrive`, `lime`, `upsales`, `salesforce`, `twenty`, `superoffice`, `dynamics`, `fortnox`, `visma` (+ föreslagna `lime_go`, `visma_net`) |
| `kalla.externt_id` | text ≤ 200 | källans id som sträng |
| `kalla.uppdaterad` | timestamptz | källans ändringstid, `falt.tidpunkt` (`falt.py:246`) |
| `kalla.raderad` | bool | |
| `kalla.sammanslagen_till` | text, null | **ny**: vinnarens externa id vid merge |
| `kalla.tidigare_id` | text[] | **ny**: id som slagits in (HubSpot `hs_merged_object_ids`) |
| `namn` | text ≤ 300 | krav |
| `orgnr` / `orgnr_nyckel` / `enskild_firma` | text / text(10) / bool | ur `falt.orgnr` |
| `momsnr` | text | `falt.momsnr` |
| `bolagsform`, `sni` | text | |
| `webbplats`, `doman` | text | ur `falt.webbplats` |
| `epost`, `telefon` | text | E.164 |
| `gatuadress`, `co`, `postnr`, `postort`, `land` | text | `land` ISO-2, standard `SE` |
| `anstallda`, `omsattning` | int, bigint | |
| `relation` | enum | `kund`, `tidigare_kund`, `prospekt`, `partner`, `leverantor`, `ovrigt` (`153_crm_grund.sql:105-107`) |
| `kund_sedan`, `avtalsslut` | date | |
| `ansvarig` | text | källans ägarnamn eller id |
| `kontakta_inte` | bool | |
| `extra` | jsonb ≤ 50 nycklar | uppräknade egna fält (`adaptrar.py:29-30`) |

### 12.3 CanonicalPerson (motsvarar `crm_personer`)

| Fält | Typ | Kommentar |
|---|---|---|
| `kalla.*` | som ovan | |
| `fornamn`, `efternamn` | text ≤ 120 | `namn` delas om de saknas (`adaptrar.py:705-710`) |
| `titel` | text | |
| `epost` | text, gemener | matchningsnyckel |
| `telefon`, `mobil` | E.164 | |
| `bolag_externt_id` | text | källans bolags-id; löses mot `crm_externa_id` |
| `bolag_orgnr_nyckel` | text(10) | reserv när källan bär orgnr på personen |
| `rattslig_grund` | enum | `avtal`, `berattigat_intresse`, `samtycke` |
| `kontakta_inte` | bool | |
| `extra` | jsonb | |

### 12.4 CanonicalDeal (ny; ingen tabell finns i `153_crm_grund.sql`)

| Fält | Typ | Kommentar |
|---|---|---|
| `kalla.*` | | |
| `namn` | text | |
| `bolag_externt_id`, `person_externt_id` | text | primärt bolag/person |
| `belopp_ore` | bigint | heltal i minsta enhet; HubSpot `amount`, Pipedrive `value`, Salesforce `Amount`, Twenty `amountMicros/10000` [Antaget fältnamn utom Twenty-typen] |
| `valuta` | text ISO-4217 | |
| `pipeline`, `steg` | text | källans namn, inte id |
| `status` | enum | `oppen`, `vunnen`, `forlorad` (Pipedrive `open`/`won`/`lost` [Läst]; Lime Go `DealWon`/`DealLost` [Läst]; Salesforce `IsWon`/`IsClosed` [Antaget]) |
| `sannolikhet` | int 0–100 | |
| `forvantat_avslut`, `stangd_at` | date, timestamptz | |
| `ansvarig` | text | |
| `extra` | jsonb | |

### 12.5 CanonicalActivity (ny)

| Fält | Typ | Kommentar |
|---|---|---|
| `kalla.*` | | |
| `typ` | enum | `samtal`, `mote`, `mejl`, `uppgift`, `anteckning`, `ovrigt` |
| `rubrik` | text | |
| `text` | text | anteckningens/mötets innehåll; dataminimeras |
| `tidpunkt` | timestamptz | när det hände eller förfaller |
| `klar` | bool | |
| `bolag_externt_id`, `person_externt_id`, `affar_externt_id` | text | |
| `ansvarig` | text | |
| `utfall` | text | samtalsutfall; Lime Go `CallPositive`/`CallNegative` [Läst] |

Tidslinjen (bolagets och personens) ska slå ihop CanonicalActivity med Snajps egna
konversationer, utkast, samtal, uppföljningar och supportärenden; det är underlag
snajp-02 och snajp-03 som beskriver de tabellerna.

---

## 13. Mappningstabell, källsystem → kanonisk modell

Nyckel: `—` = inget standardfält. `eget` = kundens eget fält. Kursiv = [Antaget] enligt
avsnitten ovan.

### 13.1 Bolag

| Kanoniskt | HubSpot | Pipedrive v2 | Lime CRM | Lime Go | Upsales | Salesforce | Twenty | SuperOffice | Dynamics | Fortnox | Visma eEk. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| externt_id | `id` | `id` | *`_id`* | `id` | *`id`* | *`Id`* | `id` | `ContactId` | `accountid` | *`CustomerNumber`* | `Id` |
| uppdaterad | `properties.hs_lastmodifieddate` / `updatedAt` | `update_time` | *`_timestamp`* | — | *`modDate`* | *`SystemModstamp`* | `updatedAt` | `UpdatedDate` | `modifiedon` | — (`lastmodified` i frågan) | `ChangedUtc` |
| raderad | `archived` | `is_deleted` | händelse `.delete` | — | *`active`=false* | *`IsDeleted`* (queryAll) | `deletedAt` ≠ null | `Deleted` / händelse | `$deletedEntity` | händelse `customer-deleted-v1` | *`IsActive`=false* |
| sammanslagen_till | ny post via webhook `company.merge` | `meta.merged_to_id` | — | — | — | *`MasterRecordId`* | — | — | `masterid` | — | — |
| namn | `properties.name` | `name` | *`name`* | `name` | *`name`* | *`Name`* | `name` | `Name` | `name` | `Name` | `Name` |
| orgnr | eget | eget (`custom_fields.<hash>`) | *`registrationno`* | `registrationNumber` | *`orgNo`* | eget `__c` | eget | `OrgNr` | eget | `OrganisationNumber` | `CorporateIdentityNumber` |
| momsnr | eget | eget | *`vatno`* | — | — | eget | eget | (`OrgNr`) | eget | `VATNumber` | `VatNumber` |
| webbplats | `properties.domain` / *`website`* | *`website`* | *`www`* | `webSite` | *`webpage`* | *`Website`* | `domainName.primaryLinkUrl` | `Urls[0].Value` | `websiteurl` | *`WWW`* | `WwwAddress` |
| epost | — | — | *`email`* | `email` | — | — | — | `Emails[0].Value` | `emailaddress1` | `Email` | `EmailAddress` |
| telefon | `properties.phone` | — | *`phone`* | `phone` | *`phone`* | *`Phone`* | — | `Phones[0].Value` | `telephone1` | `Phone1` | `Telephone` |
| gatuadress | *`properties.address`* | `address.route`+`street_number` | *`visitingaddress1`* | `visitingAddress.street` | *`addresses[type=Visit].address`* | *`BillingStreet`* | `address.addressStreet1` | *`Address.Street.Address1`* | `address1_line1` | `Address1` | `InvoiceAddress1` |
| postnr | *`properties.zip`* | `address.postal_code` | *`visitingzipcode`* | `visitingAddress.zipCode` | *`…zipcode`* | *`BillingPostalCode`* | `address.addressPostcode` | *`Address.Street.Zipcode`* | `address1_postalcode` | `ZipCode` | `InvoicePostalCode` |
| postort | `properties.city` | `address.locality` | *`visitingcity`* | `visitingAddress.city` | *`…city`* | *`BillingCity`* | `address.addressCity` | *`Address.Street.City`* | `address1_city` | `City` | `InvoiceCity` |
| land | *`properties.country`* | `address.country` | *`country`* | `…countryCode` | *`…country`* | *`BillingCountryCode`* | `address.addressCountry` | *`Country.TwoLetterISOCountry`* | `address1_country` | `CountryCode` | `InvoiceCountryCode` |
| anstallda | *`properties.numberofemployees`* | — | — | — | *`noEmployees`* | *`NumberOfEmployees`* | — (eget) | — | `numberofemployees` | — | — |
| relation | `properties.lifecyclestage` (kan vara id) | `label_ids` (uppslag) | *`buyingstatus`* | `relation` | *`journeyStep`* | *`Type`* | — | `Category` | `customertypecode` / `statecode` | fast `kund` | fast `kund` |
| ansvarig | *`properties.hubspot_owner_id`* | `owner_id` (tal) | *`coworker`* | `responsibleCoworker` | *`users[0]`* | *`OwnerId`* | `accountOwnerId` | `Associate` | `_ownerid_value` | `OurReference` | — |
| hoppa_over | — | — | — | — | — | — | — | — | — | *`Type`=PRIVATE* | `IsPrivatePerson` |

### 13.2 Person

| Kanoniskt | HubSpot | Pipedrive v2 | Twenty | SuperOffice | Dynamics | Salesforce | Lime CRM | Upsales |
|---|---|---|---|---|---|---|---|---|
| externt_id | `id` | `id` | `id` | *`PersonId`* | *`contactid`* | *`Id`* | *`_id`* | *`id`* |
| fornamn | `properties.firstname` | *`first_name`* | `name.firstName` | *`Firstname`* | *`firstname`* | *`FirstName`* | *`firstname`* | *`firstName`* |
| efternamn | `properties.lastname` | *`last_name`* | `name.lastName` | *`Lastname`* | *`lastname`* | *`LastName`* | *`lastname`* | *`lastName`* |
| titel | `properties.jobtitle` | `job_title` (bara med kontaktsynk) | `jobTitle` | *`Title`* | *`jobtitle`* | *`Title`* | *`position`* | *`title`* |
| epost | `properties.email` | `emails[primary=true].value` | `emails.primaryEmail` | *`Emails[0].Value`* | *`emailaddress1`* | *`Email`* | *`email`* | *`email`* |
| telefon | `properties.phone` | `phones[primary=true].value` | `phones.primaryPhoneCallingCode`+`primaryPhoneNumber` | *`OfficePhones[0].Value`* | *`telephone1`* | *`Phone`* | *`phone`* | *`phone`* |
| mobil | `properties.mobilephone` | (`phones[label=mobile]`) | — | *`MobilePhones[0].Value`* | *`mobilephone`* | *`MobilePhone`* | *`mobilephone`* | *`cellPhone`* |
| bolag_externt_id | association typ 1/279 | `org_id` | `companyId` | *`Contact.ContactId`* | *`_parentcustomerid_value`* | *`AccountId`* | *`company`* | *`client.id`* |

Fortnox och Visma eEkonomi har inga personer, bara kontaktfält på kunden
(Visma `ContactPersonName`, `ContactPersonEmail` … [Sekundär]). Lime Go har personer via
GraphQL med begränsad exponering [Sekundär].

### 13.3 Affär och aktivitet (översikt)

| Kanoniskt | HubSpot | Pipedrive | Salesforce | Dynamics | Twenty | Lime Go | SuperOffice |
|---|---|---|---|---|---|---|---|
| Affär | `deals` | `deals` (`status` open/won/lost) | `Opportunity` | `opportunities` | `opportunities` | `/deals`, `DealWon`/`DealLost` | `Sale` (`sale.sold`/`sale.lost`) |
| Aktivitet | calls/meetings/notes/tasks | `activities`, `notes` | `Task`, `Event` | `activitypointers`, `annotations` | `notes`, `tasks` | `CallPositive` …, `MeetingBooked` … | `Appointment` |

Allt i 13.3 utom de händelsenamn som står i avsnitt 2, 4 och 8 är [Antaget].

### 13.4 Vad tabellerna behöver för sammanslagning

`crm_externa_id` har ingen kolumn för "slogs ihop med" (`153_crm_grund.sql:154-166`).
Förslag: när en merge-händelse kommer, peka det förlorande externa id:t på vinnarens
`post_id` (samma tabell, samma unika nyckel `(anslutning_id, objekt, externt_id)`), så att
en sen händelse på det gamla id:t landar rätt. För HubSpot, där vinnaren får ett nytt id,
skapas en tredje rad för det nya id:t mot samma `post_id` [Antaget design].

---

## 14. Förslag: deklarativ mappningskonfiguration per källsystem

### 14.1 Form

Bygger vidare på formen i `adaptrar.py:8-27` (sökväg, lista av sökvägar, objekt med
`fran`, `uppslag`, `standard`, `fast`, `sammanfoga`) och lägger till två nycklar:

- `transform`: en lista av steg som körs före målfältets egen tolkning:
  `trim`, `lower`, `upper`, `orgnr`, `momsnr`, `telefon`, `datum`, `tidpunkt`,
  `heltal`, `ore` (belopp till öre), `dela:<tecken>:<index>`, `ta_bort_prefix:<text>`,
  `uppslag` (tabellen i `uppslag`). Målfältets tolkning körs ändå efteråt, så kunden
  kan inte stänga av kontrollen (`adaptrar.py:25-27`).
- `konflikt`: per fält, ett av `kallan_vinner`, `snajp_vinner`, `nyast_vinner`, samma
  värden som `crm_anslutningar.konfliktregel` (`153_crm_grund.sql:57-59`), plus
  `fyll_tomt` (skriv bara om Snajps värde är tomt). Saknas den gäller anslutningens regel.
  Fält som en användare ändrat för hand står i `manuellt_andrade` (`:97`, `:135`) och
  skyddas av `snajp_vinner`.

**Kod som måste ändras för det:** `_validera_kalla` avvisar okända nycklar
(`adaptrar.py:490-492`); `transform` och `konflikt` måste läggas till där och i `_los`
(`adaptrar.py:576-604`).

Sökvägarna är punktvägar med listfilter, inte full JSONPath: `addresses[type=Visit].city`,
`emails[primary=true].value`, `Phones.0.Value` (`adaptrar.py:20-23`, `:538-569`). Det
räcker för alla system ovan utom Dynamics webhook-kropp (`InputParameters[key=Target].
value.Attributes[key=name].value`), som syntaxen också klarar.

Gemensamma toppnycklar:

```json
{
  "system": "hubspot",
  "api_version": "2026-09",
  "objekt": { "bolag": { … }, "person": { … }, "affar": { … }, "aktivitet": { … } },
  "relation_vid_saknad": "tidigare_kund",
  "konflikt": "kallan_vinner"
}
```

`relation_vid_saknad` motsvarar `crm_anslutningar.saknade` (`behall`, `tidigare_kund`,
`ta_bort`, `153_crm_grund.sql:60-62`).

### 14.2 HubSpot

```json
{
  "system": "hubspot",
  "api_version": "2026-09",
  "objekt": {
    "bolag": {
      "externt_id": "id",
      "uppdaterad": ["properties.hs_lastmodifieddate", "updatedAt"],
      "raderad": "archived",
      "tidigare_id": { "fran": "properties.hs_merged_object_ids", "transform": ["dela:;:*"] },
      "namn": { "fran": "properties.name", "transform": ["trim"], "konflikt": "fyll_tomt" },
      "orgnr": { "fran": "properties.organisationsnummer", "transform": ["orgnr"], "konflikt": "kallan_vinner" },
      "webbplats": ["properties.domain", "properties.website"],
      "telefon": { "fran": "properties.phone", "transform": ["telefon"] },
      "postort": "properties.city",
      "relation": { "fran": "properties.lifecyclestage",
                    "uppslag": { "customer": "kund", "51439524": "kund", "lead": "prospekt" },
                    "standard": "prospekt" },
      "ansvarig": "properties.hubspot_owner_id",
      "extra": { "bransch": "properties.industry" }
    },
    "person": {
      "externt_id": "id",
      "uppdaterad": ["properties.lastmodifieddate", "updatedAt"],
      "raderad": "archived",
      "fornamn": "properties.firstname",
      "efternamn": "properties.lastname",
      "epost": { "fran": "properties.email", "transform": ["trim", "lower"] },
      "bolag_externt_id": "associations.companies.results[type=contact_to_company].id"
    }
  }
}
```

`properties.organisationsnummer` är ett exempel; kunden pekar ut sitt eget fält.
Associationsvägen förutsätter att adaptern hämtar med `associations=companies`; den
exakta svarsformen för v3-listans `associations` är [Antaget].

### 14.3 Pipedrive

```json
{
  "system": "pipedrive",
  "api_version": "v2",
  "objekt": {
    "bolag": {
      "externt_id": "id",
      "uppdaterad": "update_time",
      "raderad": "is_deleted",
      "sammanslagen_till": "meta.merged_to_id",
      "namn": "name",
      "orgnr": { "fran": "custom_fields.dcf558aac1ae4e8c4f849ba5e668430d8df9be12", "transform": ["orgnr"] },
      "gatuadress": { "sammanfoga": ["address.route", "address.street_number"] },
      "postnr": "address.postal_code",
      "postort": "address.locality",
      "land": "address.country",
      "relation": { "fran": "label_ids.0", "uppslag": { "5": "kund", "6": "prospekt" }, "standard": "prospekt" },
      "ansvarig": "owner_id"
    },
    "person": {
      "externt_id": "id",
      "uppdaterad": "update_time",
      "raderad": "is_deleted",
      "namn": "name",
      "epost": "emails[primary=true].value",
      "telefon": "phones[primary=true].value",
      "bolag_externt_id": "org_id"
    }
  }
}
```

`sammanfoga` lägger ihop utan mellanslag (`adaptrar.py:591-594`); för gatuadress behövs
ett avgränsare-tillval, eller så används `address.value` [Antaget behov].

### 14.4 Lime CRM

```json
{
  "system": "lime",
  "api_version": "v1",
  "limetyper": { "bolag": "company", "person": "person" },
  "objekt": {
    "bolag": {
      "externt_id": "_id",
      "uppdaterad": "_timestamp",
      "namn": "name",
      "orgnr": { "fran": ["registrationno", "orgnr"], "transform": ["orgnr"] },
      "telefon": "phone",
      "webbplats": "www",
      "relation": { "fran": "buyingstatus.key", "uppslag": { "active": "kund", "excustomer": "tidigare_kund" } },
      "ansvarig": "coworker.name"
    },
    "person": { "externt_id": "_id", "fornamn": "firstname", "efternamn": "lastname",
                "epost": "email", "bolag_externt_id": "company" }
  }
}
```

`limetyper` är ny: Lime låter kunden döpa om limetyperna [Läst att modellen varierar].

### 14.5 Lime Go

```json
{
  "system": "lime_go",
  "objekt": {
    "bolag": {
      "externt_id": "id",
      "namn": "name",
      "orgnr": { "fran": "registrationNumber", "transform": ["orgnr"] },
      "telefon": "phone", "epost": "email", "webbplats": "webSite",
      "gatuadress": ["visitingAddress.street", "postalAddress.street"],
      "postnr": ["visitingAddress.zipCode", "postalAddress.zipCode"],
      "postort": ["visitingAddress.city", "postalAddress.city"],
      "land": ["visitingAddress.countryCode", "postalAddress.countryCode"],
      "relation": { "fran": "relation", "uppslag": { "IsACustomer": "kund", "WasACustomer": "tidigare_kund",
                    "WorkingOnIt": "prospekt", "BeenInTouch": "prospekt", "NoRelation": "ovrigt" } },
      "ansvarig": "responsibleCoworker"
    }
  }
}
```

`relation` returneras som tal vid läsning [Läst]; talens betydelse är okänd, så uppslaget
ovan gäller bara om API:t skickar namnet [Antaget].

### 14.6 Upsales

```json
{
  "system": "upsales",
  "objekt": {
    "bolag": {
      "externt_id": "id",
      "uppdaterad": "modDate",
      "raderad": { "fran": "active", "uppslag": { "false": true, "true": false } },
      "namn": "name",
      "orgnr": { "fran": ["orgNo", "custom[fieldId=12].value"], "transform": ["orgnr"] },
      "telefon": "phone",
      "relation": { "fran": "journeyStep", "uppslag": { "customer": "kund", "lost_customer": "tidigare_kund" },
                    "standard": "prospekt" }
    }
  }
}
```

Hela Upsales-mappningen är overifierad (avsnitt 5.3).

### 14.7 Salesforce

```json
{
  "system": "salesforce",
  "api_version": "v66.0",
  "sandlada": false,
  "objekt": {
    "bolag": {
      "externt_id": "Id",
      "uppdaterad": "SystemModstamp",
      "raderad": "IsDeleted",
      "sammanslagen_till": "MasterRecordId",
      "namn": "Name",
      "orgnr": { "fran": "Organisationsnummer__c", "transform": ["orgnr"] },
      "webbplats": "Website", "telefon": "Phone",
      "gatuadress": "BillingStreet", "postnr": "BillingPostalCode", "postort": "BillingCity",
      "land": ["BillingCountryCode", "BillingCountry"],
      "relation": { "fran": "Type", "uppslag": { "Customer - Direct": "kund", "Prospect": "prospekt" } },
      "ansvarig": "Owner.Name"
    },
    "person": { "externt_id": "Id", "fornamn": "FirstName", "efternamn": "LastName", "epost": "Email",
                "bolag_externt_id": "AccountId", "kontakta_inte": "HasOptedOutOfEmail" }
  }
}
```

### 14.8 Twenty

```json
{
  "system": "twenty",
  "objekt": {
    "bolag": {
      "externt_id": "id", "uppdaterad": "updatedAt",
      "raderad": { "fran": "deletedAt", "transform": ["finns"] },
      "namn": "name",
      "orgnr": { "fran": "orgnr", "transform": ["orgnr"] },
      "webbplats": "domainName.primaryLinkUrl",
      "gatuadress": "address.addressStreet1", "co": "address.addressStreet2",
      "postnr": "address.addressPostcode", "postort": "address.addressCity", "land": "address.addressCountry",
      "ansvarig": "accountOwnerId"
    },
    "person": {
      "externt_id": "id", "uppdaterad": "updatedAt",
      "fornamn": "name.firstName", "efternamn": "name.lastName", "titel": "jobTitle",
      "epost": "emails.primaryEmail",
      "telefon": { "sammanfoga": ["phones.primaryPhoneCallingCode", "phones.primaryPhoneNumber"] },
      "bolag_externt_id": "companyId"
    }
  }
}
```

`finns` (sant om värdet inte är null) är en ny transform. I dag ger `_sann` på en
tidsstämpelsträng falskt (`adaptrar.py:607-610`), så `raderad: "deletedAt"`
(`adaptrar.py:314`, `:329`) markerar aldrig en Twenty-post som raderad [Läst i koden].

### 14.9 SuperOffice

```json
{
  "system": "superoffice",
  "objekt": {
    "bolag": {
      "externt_id": "ContactId", "uppdaterad": "UpdatedDate", "raderad": "Deleted",
      "namn": "Name",
      "orgnr": { "fran": "OrgNr", "transform": ["trim", "orgnr"] },
      "momsnr": { "fran": "OrgNr", "transform": ["momsnr"], "konflikt": "fyll_tomt" },
      "webbplats": "Urls.0.Value", "telefon": "Phones.0.Value", "epost": "Emails.0.Value",
      "relation": { "fran": "Category.Value", "uppslag": { "Kund": "kund", "Prospekt": "prospekt" } },
      "ansvarig": "Associate.FullName",
      "extra": { "kundnummer": "Number1" }
    }
  }
}
```

`adaptrar.py:338-357` saknar `raderad` för SuperOffice; `Deleted` finns på entiteten [Läst].

### 14.10 Dynamics 365

```json
{
  "system": "dynamics",
  "api_version": "v9.2",
  "objekt": {
    "bolag": {
      "externt_id": "accountid", "uppdaterad": "modifiedon",
      "raderad": { "fran": "reason", "uppslag": { "deleted": true } },
      "sammanslagen_till": "_masterid_value",
      "namn": "name",
      "orgnr": { "fran": "new_orgnr", "transform": ["orgnr"] },
      "webbplats": "websiteurl", "telefon": "telephone1", "epost": "emailaddress1",
      "gatuadress": "address1_line1", "postnr": "address1_postalcode", "postort": "address1_city",
      "land": "address1_country", "anstallda": "numberofemployees",
      "relation": [
        { "fran": "statecode", "uppslag": { "1": "tidigare_kund" } },
        { "fran": "customertypecode", "uppslag": { "3": "kund", "8": "prospekt", "5": "partner",
          "9": "partner", "10": "leverantor", "11": "leverantor", "12": "ovrigt" } }
      ],
      "ansvarig": "_ownerid_value"
    }
  }
}
```

`reason` ligger på `$deletedEntity`-raden [Läst]. `_masterid_value` är OData-formen för
uppslaget `masterid` [Antaget]. `new_orgnr` är ett exempel på ett eget fält.

### 14.11 Fortnox

```json
{
  "system": "fortnox",
  "objekt": {
    "bolag": {
      "externt_id": "CustomerNumber",
      "raderad": { "fran": "Active", "uppslag": { "false": true, "true": false } },
      "hoppa_over": { "fran": "Type", "uppslag": { "PRIVATE": true } },
      "namn": "Name",
      "orgnr": { "fran": "OrganisationNumber", "transform": ["orgnr"], "konflikt": "kallan_vinner" },
      "momsnr": "VATNumber",
      "epost": "Email", "telefon": ["Phone1", "Phone2"], "webbplats": "WWW",
      "gatuadress": "Address1", "co": "Address2", "postnr": "ZipCode", "postort": "City", "land": "CountryCode",
      "ansvarig": "OurReference",
      "relation": { "fast": "kund" }
    }
  }
}
```

Fortnox är ett kundregister: allt som står där är en kund, därför `fast: kund`. Det är
den källa som bäst svarar på Iris-frågan "är bolaget redan kund?".

### 14.12 Visma eEkonomi och Visma.net

```json
{
  "system": "visma",
  "objekt": {
    "bolag": {
      "externt_id": "Id", "uppdaterad": "ChangedUtc",
      "raderad": { "fran": "IsActive", "uppslag": { "false": true, "true": false } },
      "hoppa_over": "IsPrivatePerson",
      "namn": "Name",
      "orgnr": { "fran": "CorporateIdentityNumber", "transform": ["orgnr"] },
      "momsnr": "VatNumber", "epost": "EmailAddress", "telefon": ["Telephone", "MobilePhone"],
      "webbplats": "WwwAddress",
      "gatuadress": "InvoiceAddress1", "postnr": "InvoicePostalCode", "postort": "InvoiceCity",
      "land": "InvoiceCountryCode",
      "relation": { "fast": "kund" },
      "extra": { "kontaktperson": "ContactPersonName", "kontaktperson_epost": "ContactPersonEmail" }
    }
  }
}
```

Visma.net (`"system": "visma_net"`) behöver egna sökvägar när kundens JSON är verifierad.

### 14.13 Konfliktregler per fält, föreslagen standard

| Fält | Standard | Skäl |
|---|---|---|
| `orgnr` | `kallan_vinner` om källan är ett ekonomisystem (Fortnox, Visma), annars `fyll_tomt` | Bokföringen har det kontrollerade numret [Antaget skäl] |
| `relation` | `kallan_vinner` | Det är syftet med Buddys synk: kundstatus avgör Iris-uteslutningen |
| `namn`, `webbplats`, `telefon`, `epost` | `nyast_vinner` | |
| `ansvarig` | `kallan_vinner` | |
| fält i `manuellt_andrade` | `snajp_vinner` | En säljares egen ändring ska inte skrivas över av nästa synk |

---

## 15. Öppna frågor och risker

Öppna frågor:
1. Vilket CRM eller ekonomisystem har Buddy? Beställningen nämner bara "kundsynk IN via
   API". Svaret avgör vilken adapter som byggs först.
2. Upsales fältschema: kräver ett riktigt svar från en kunds konto.
3. Lime CRM: ska Snajp läsa via Limeobject-REST eller Query API, och hur ser kundens
   `/api/v1/docs/` ut?
4. Lime Go och Visma.net behöver egna systemvärden; CHECK-villkoret i
   `153_crm_grund.sql:54-56` och `SYSTEM` i `adaptrar.py:47-50` måste utökas.
5. Fortnox WebSocket kräver en långlivad process; finns plats för den på Railway?
6. Ska Snajp vara en offentlig HubSpot/Pipedrive-app (OAuth, marknadsplats) eller räcker
   kundens egen privata nyckel? Påverkar gränser (HubSpot 110 vs 190 per 10 s) och
   webhook-möjligheter.

Risker:
1. Fältnamn märkta [Antaget] i `adaptrar.py` kan ge tomma fält utan fel: mappningen
   tystnar i stället för att larma. En testkörning per system mot ett riktigt konto
   behövs innan en kund ansluter.
2. `adaptrar.py:374`/`:394` (Dynamics `statecode` som raderad) och `adaptrar.py:314`/`:329`
   (Twenty `deletedAt` som aldrig blir sann) ger fel raderingsstatus.
3. Pipedrive och Dynamics signerar inte webhooks; utan hemlig nyckel per anslutning kan
   vem som helst skicka falska ändringar.
4. Sammanslagningar som inte hanteras ger dubbla bolag (HubSpot) eller tappade id.
5. Låga gränser (Twenty, Fortnox, Lime Cloud) gör en första full synk lång; förloppet
   måste synas där användaren startade den, och finnas kvar efter omladdning.
6. Kundregister i Fortnox/Visma innehåller privatpersoner; att låta dem passera som bolag
   vore en personuppgiftsbehandling utan grund.
7. Salesforce-dokumentationen kunde inte läsas direkt; siffrorna kommer ur sökutdrag.
