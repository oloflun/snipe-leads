# Twenty som förlaga, luckgranskning del server

Luckgranskning av inventeringsfilerna `twenty-01` till `twenty-13` mot serverns katalogträd i förlagan (Twenty CRM, commit 1da6d55, 2026-11-24, klon i `D:\snajp-crm-forlaga\twenty`). Funktionsbeskrivning med egna ord; ingen kod, inga typer, inga frågedokument ur förlagan. Sökvägar är relativa till `packages/twenty-server/src/` (förkortat: `core-modules/` = `engine/core-modules/`, `metadata-modules/` = `engine/metadata-modules/`).

## Översikt

Servern i förlagan har fyra lager som läsarna har inventerat ur olika vinklar:

1. **`modules/`**: standardobjektens affärslogik (person, bolag, affär, uppgift, anteckning, bilaga, tidslinje, arbetsflöde, mejl- och kalendersynk, dashboards, arbetsytemedlem).
2. **`engine/core-modules/`**: plattformen kring arbetsytan (inloggning, fakturering, filer, nycklar, arbetsytor, inbjudningar, sök, export, AI-verktyg, serveradminpanel, telemetri, gränser, instansens konfiguration).
3. **`engine/metadata-modules/`**: datamodellen som data (objekt, fält, alternativ, index, vyer, sidlayouter, roller och behörigheter, navigering, kommandomeny, webhooks, agenter, färdigheter, MCP-servrar, valideringsregler, formelfält, översättningar och överskuggningar). Varje område har dessutom en `flat-*`-tvilling: ett cache- och omvandlingslager som migrationsmotorn arbetar mot. Där bor ofta validerarna, men användarbeteendet beskrivs under huvudkatalogen.
4. **Övriga `engine/`-kataloger**: API-lagren (GraphQL, REST, MCP), ORM-lagret, händelseutsändning, prenumerationer, papperskorgsrensning, middleware, cachar och behörighetskontroll.

Metod: alla 244 kataloger (23 under `modules`, 97 under `core-modules`, 101 under `metadata-modules`, 18 direkt under `engine`, plus underkatalogerna i `workspace-manager` och `api`) prövades maskinellt mot ursprungskolumnen i läsarnas cirka 3 600 rader, därefter mot hela radtexten (läsarna använder förkortningar som `CE/` och `S/`) och mot läsarnas egna avprickningslistor. Det som ändå saknades öppnades i förlagan. Dessutom prövades systematiskt: fälttyper, filteroperander, behörighetsflaggor, aggregat, widgettyper, vytyper och kommandomenyns tillgänglighetstyper (alla värden nämns minst två gånger hos läsarna, ingen lucka), instansens 274 konfigurationsvariabler (135 namnges inte av någon läsare, de flesta beskrivs dock i sak), och serverns 420 kommandoradskommandon (de cirka 30 driftkommandona utanför uppgraderingskedjan saknades nästan helt).

Huvudslutsats: läsarnas täckning av det användaren och integratören ser är nästan fullständig. Luckorna ligger i (1) hur standardmetadata översätts och överskuggas per arbetsyta, (2) den publika klientkonfigurationen som styr vad webbklienten visar, (3) säkerhets- och driftlager i middleware och webbklientens dokument, och (4) driftsidan: kommandon, konfigurationsvariablernas namn och standardvärden.

Begrepp i denna fil:

| Förlagans term | Svensk term | Betydelse |
|---|---|---|
| override | överskuggning | Arbetsytans egen ändring av en egenskap på metadata som ägs av en app (standardappen eller en installerad app); appens källvärde lämnas orört |
| translation provenance | översättningens ursprung | Om ett visat värde kommer från arbetsytans egen översättning, från appens medlevererade översättning eller är oöversatt |
| client config | klientkonfiguration | Publikt svar som talar om för webbklienten vilka funktioner, leverantörer och gränser instansen har |
| maintenance mode | underhållsläge | Planerat driftstopp som visas som banderoll |
| config variable | konfigurationsvariabel | Instansinställning, i miljön eller i databasen |
| deferred workspace operation | uppskjuten arbetsyteoperation | Tung schemaändring som körs i bakgrunden efter en migration |
| täckt | | Katalogen har minst en funktionsrad hos en läsare |
| LUCKA | | Ingen läsare har en rad för katalogens användarsynliga funktion |
| intern (D) | | Katalogen saknar funktion som användare, administratör eller integratör märker, se avsnitt D |

## Avprickningslista (arbetsläge)

| Del | Status |
|---|---|
| Läsarnas filer 01–13 | läst (avprickningslistor och rader maskinellt; rader i sak där en lucka misstänktes) |
| modules/* (23) | läst |
| engine/core-modules/* (97) | läst |
| engine/metadata-modules/* (101) | läst |
| engine/* övriga, workspace-manager/*, api/* | läst |
| twenty-config/config-variables.ts (274 variabler) | läst |
| kommandoradskommandon (420) | läst på namn och beskrivning |

## A. Avprickning per katalog

Formatet i täckningskolumnen: fil (01–13): första och sista ID som nämner katalogen i ursprungskolumnen (antal rader). Intervallet är i radordning, inte numeriskt.

| Katalog | Täckt av / status |
|---|---|
| `modules/attachment` | 01: DM-057–DM-057 (1); 03: PS-146–PS-146 (1) |
| `modules/blocklist` | 01: DM-059–DM-059 (1); 05: MK-E14–MK-E15 (2) |
| `modules/calendar` | 01: DM-067–DM-067 (1); 03: PS-126–PS-161 (6); 05: MK-D01–MK-A12 (21); 07: API-424–API-424 (1) |
| `modules/call-recording` | 01: DM-062–DM-062 (1); 03: PS-186–PS-186 (1); 05: MK-J01–MK-J03 (3) |
| `modules/company` | 01: DM-050–DM-050 (1); 09: IE-162–IE-162 (1); 11: AI-315–AI-315 (1) |
| `modules/connected-account-sync-webhooks` | 05: MK-G11–MK-G13 (3) |
| `modules/connected-account` | 05: MK-A09–MK-A15 (13) |
| `modules/contact-creation-manager` | 05: MK-E08–MK-E13 (5) |
| `modules/dashboard-sync` | 10: DB-046–DB-046 (1) |
| `modules/dashboard` | 01: DM-061–DM-061 (1); 04: NAV-145–NAV-145 (1); 10: DB-039–DB-044 (15); 11: AI-403–AI-403 (1) |
| `modules/emailing` | 01: DM-063–DM-065 (3); 05: MK-H12–MK-I42 (18); 07: API-431–API-431 (1); 11: AI-411–AI-411 (2) |
| `modules/match-participant` | 05: MK-E02–MK-E05 (3) |
| `modules/messaging-webhooks` | 05: MK-G14–MK-I25 (5) |
| `modules/messaging` | 01: DM-066–DM-066 (1); 03: PS-157–PS-157 (1); 05: MK-C01–MK-C29 (23); 07: API-424–API-424 (1) |
| `modules/note` | 01: DM-055–DM-056 (2); 03: PS-128–PS-131 (3) |
| `modules/onboarding-invite-suggestions` | 05: MK-J05–MK-J05 (1) |
| `modules/onboarding-recent-messages-import` | 05: MK-J04–MK-J04 (1) |
| `modules/opportunity` | 01: DM-052–DM-052 (1) |
| `modules/person` | 01: DM-051–DM-051 (1); 09: IE-163–IE-163 (1); 11: AI-315–AI-315 (1) |
| `modules/task` | 01: DM-053–DM-054 (2); 03: PS-129–PS-131 (2) |
| `modules/timeline` | 01: DM-060–DM-170 (4); 03: PS-113–PS-192 (6); 07: API-424–API-424 (1) |
| `modules/workflow` | 01: DM-068–DM-068 (1); 04: NAV-135–NAV-142 (8); 06: AF-002–AF-514 (84); 09: IE-174–IE-174 (1); 11: AI-360–AI-402 (6) |
| `modules/workspace-member` | 01: DM-058–DM-058 (1); 08: AR-908–AR-909 (2) |
| `core-modules/__mocks__` | Intern: testdata (D) |
| `core-modules/actor` | 01: DM-186–DM-187 (2); 07: API-359–API-359 (1) |
| `core-modules/admin-panel` | 08: AR-703–AR-970 (20); 09: IE-117–IE-190 (4) |
| `core-modules/api-key` | 07: API-044–API-088 (10) |
| `core-modules/app-token` | Täckt i sak av AR-310, API-180, API-374 (08, 07); tokentyperna i LKS-036 |
| `core-modules/application` | 04: NAV-025–NAV-035 (2); 05: MK-O18–MK-M07 (2); 06: AF-803–AF-1002 (5); 07: API-348–API-429 (19); 11: AI-031–AI-435 (4) |
| `core-modules/approved-access-domain` | 08: AR-352–AR-354 (3) |
| `core-modules/auth` | 05: MK-A01–MK-D20 (9); 07: API-081–API-081 (1); 08: AR-200–AR-925 (54) |
| `core-modules/billing-webhook` | 08: AR-602–AR-615 (2) |
| `core-modules/billing` | 07: API-227–API-242 (2); 08: AR-063–AR-963 (53); 10: DB-115–DB-115 (1); 13: HB-332–HB-382 (5) |
| `core-modules/cache-lock` | Intern (D) |
| `core-modules/cache-storage` | LUCKA (driftkommando) → LKS-031 |
| `core-modules/calendar` | 01: DM-067–DM-067 (1); 03: PS-126–PS-161 (6); 05: MK-D01–MK-A12 (21); 07: API-424–API-424 (1) |
| `core-modules/captcha` | 08: AR-260–AR-261 (2) |
| `core-modules/client-config` | LUCKA → LKS-009–LKS-016 (bara API-419 nämner sökvägen) |
| `core-modules/cloudflare` | 08: AR-502–AR-504 (2) |
| `core-modules/code-interpreter` | 06: AF-617–AF-1034 (6); 11: AI-159–AI-159 (1) |
| `core-modules/company-enrichment` | Täckt: 09 IE-153–IE-161, IE-198 (förkortning CE/) |
| `core-modules/cron` | 06: AF-128–AF-808 (4) |
| `core-modules/dns-manager` | 08: AR-502–AR-063 (4) |
| `core-modules/domain` | 08: AR-500–AR-506 (4) |
| `core-modules/dpa` | 08: AR-718–AR-718 (1) |
| `core-modules/email-verification` | 05: MK-K04–MK-K04 (1); 08: AR-250–AR-251 (2) |
| `core-modules/email` | 05: MK-E12–MK-K01 (15); 07: API-242–API-242 (1) |
| `core-modules/emailing-domain` | 05: MK-H12–MK-I51 (18) |
| `core-modules/enterprise` | 04: NAV-166–NAV-166 (1); 08: AR-700–AR-700 (3); 12: UX-244–UX-244 (1) |
| `core-modules/environment` | Intern (D) |
| `core-modules/event-emitter` | 03: PS-117–PS-117 (1) |
| `core-modules/event-logs` | 08: AR-630–AR-926 (7) |
| `core-modules/exception-handler` | LUCKA (driftinställning) → LKS-041 |
| `core-modules/feature-flag` | 08: AR-701–AR-702 (2) |
| `core-modules/file-storage` | 03: PS-156–PS-156 (1) |
| `core-modules/file` | 03: PS-143–PS-154 (11); 09: IE-107–IE-176 (2) |
| `core-modules/frontend` | LUCKA → LKS-024, LKS-025 (DB-187 rör bara AI-placering av appkomponenter) |
| `core-modules/geo-map` | 02: VY-170–VY-170 (1) |
| `core-modules/getting-started` | 04: NAV-042–NAV-161 (5); 07: API-170–API-397 (7); 09: IE-160–IE-160 (1); 12: UX-162–UX-304 (22); 13: HB-001–HB-390 (17) |
| `core-modules/graphql` | 03: PS-109–PS-118 (2); 07: API-050–API-359 (9) |
| `core-modules/guard-redirect` | LUCKA (låg) → LKS-026 |
| `core-modules/health` | 08: AR-710–AR-710 (1); sökvägen i LKS-027 |
| `core-modules/i18n` | 08: AR-719–AR-977 (2) |
| `core-modules/imap-smtp-caldav-connection` | 05: MK-A06–MK-A08 (3) |
| `core-modules/impersonation` | 08: AR-320–AR-707 (6) |
| `core-modules/jwt` | 08: AR-313–AR-920 (3) |
| `core-modules/key-value-pair` | Intern lagring (D); typerna i LKS-037 |
| `core-modules/lab` | 08: AR-702–AR-815 (2) |
| `core-modules/logger` | LUCKA (driftinställning) → LKS-041 |
| `core-modules/logic-function` | 06: AF-243–AF-1037 (18); 07: API-242–API-349 (2) |
| `core-modules/message-queue` | 06: AF-601–AF-601 (1) |
| `core-modules/messaging` | 01: DM-066–DM-066 (1); 03: PS-157–PS-157 (1); 05: MK-C01–MK-C29 (20); 07: API-424–API-424 (1) |
| `core-modules/metrics` | 08: AR-949–AR-949 (1) |
| `core-modules/onboarding` | 04: NAV-036–NAV-164 (11); 09: IE-153–IE-161 (2) |
| `core-modules/open-api` | 07: API-120–API-123 (3) |
| `core-modules/pending-wake-up` | 04: NAV-051–NAV-163 (2) |
| `core-modules/public-domain` | 08: AR-505–AR-505 (1) |
| `core-modules/record-crud` | 06: AF-232–AF-234 (3); 07: API-038–API-038 (1); 09: IE-145–IE-175 (3) |
| `core-modules/record-export` | 09: IE-099–IE-109 (2) |
| `core-modules/record-position` | 01: DM-185–DM-185 (2) |
| `core-modules/record-transformer` | 03: PS-144–PS-165 (2); 10: DB-089–DB-089 (1) |
| `core-modules/redis-client` | Intern (D) |
| `core-modules/related-person-ids` | 03: PS-157–PS-157 (1) |
| `core-modules/sdk-client` | 07: API-231–API-231 (1) |
| `core-modules/search` | 04: NAV-001–NAV-060 (6) |
| `core-modules/secret-encryption` | 08: AR-720–AR-921 (2) |
| `core-modules/secure-http-client` | 06: AF-910–AF-910 (1); AF-910, API-417, AR-973 i sak; standardvärden i LKS-028 |
| `core-modules/sentry` | LUCKA (driftinställning) → LKS-041 |
| `core-modules/server-route-trigger` | 06: AF-806–AF-806 (10) |
| `core-modules/session-storage` | 08: AR-315–AR-315 (1) |
| `core-modules/short-link` | 07: API-129–API-129 (1) |
| `core-modules/sql-sanitization` | Intern (D) |
| `core-modules/sso` | 08: AR-270–AR-931 (5) |
| `core-modules/tab-presence` | 04: NAV-050–NAV-107 (2) |
| `core-modules/target` | Intern (D) |
| `core-modules/telemetry` | 08: AR-721–AR-721 (1) |
| `core-modules/throttler` | 07: API-112–API-112 (1) |
| `core-modules/tool-provider` | 07: API-144–API-163 (7); 11: AI-150–AI-154 (16) |
| `core-modules/tool` | 05: MK-F08–MK-F08 (1); 06: AF-240–AF-817 (3); 07: API-144–API-163 (7); 11: AI-150–AI-164 (17) |
| `core-modules/twenty-config` | 05: MK-A29–MK-K01 (5); 06: AF-604–AF-913 (5); 07: API-032–API-208 (5); 08: AR-211–AR-927 (9); 135 variabelnamn saknades → LKS-038–LKS-055 |
| `core-modules/two-factor-authentication` | 08: AR-240–AR-246 (11) |
| `core-modules/upgrade` | Täckt delvis: AR-711, API-250, API-367; driftkommandona i LKS-034 |
| `core-modules/usage-limit` | 05: MK-I44–MK-I44 (1); 07: API-110–API-116 (5); 08: AR-622–AR-622 (10); 11: AI-172–AI-175 (4) |
| `core-modules/usage` | 05: MK-I44–MK-I44 (1); 07: API-117–API-117 (1); 08: AR-620–AR-620 (9); 10: DB-149–DB-149 (1); 11: AI-170–AI-209 (4) |
| `core-modules/user-session` | 08: AR-300–AR-301 (8) |
| `core-modules/user-workspace` | 08: AR-334–AR-345 (4) |
| `core-modules/user` | 05: MK-A12–MK-A12 (1); 08: AR-335–AR-301 (7) |
| `core-modules/web-push` | 04: NAV-047–NAV-162 (6) |
| `core-modules/well-known` | 07: API-126–API-128 (3) |
| `core-modules/workflow` | 01: DM-068–DM-068 (1); 04: NAV-135–NAV-142 (8); 06: AF-002–AF-514 (84); 09: IE-174–IE-174 (1); 11: AI-360–AI-402 (6) |
| `core-modules/workspace-data-export` | 08: AR-717–AR-717 (1) |
| `core-modules/workspace-invitation` | 08: AR-347–AR-350 (4) |
| `core-modules/workspace` | 01: DM-184–DM-184 (1); 05: MK-L10–MK-L10 (1); 08: AR-330–AR-910 (16); 10: DB-166–DB-166 (1) |
| `metadata-modules/agent-chat-channel` | 11: AI-107–AI-107 (1) |
| `metadata-modules/ai` | 04: NAV-048–NAV-101 (2); 06: AF-1014–AF-1014 (1); 07: API-140–API-214 (6); 11: AI-001–AI-126 (51); 13: HB-239–HB-251 (7) |
| `metadata-modules/application-translation-catalog` | LUCKA → LKS-005 |
| `metadata-modules/calendar-channel` | Täckt: 05 MK-B05–MK-B14 (checklista 05) |
| `metadata-modules/command-menu-item` | 03: PS-162–PS-162 (4); 04: NAV-026–NAV-123 (15); 09: IE-042–IE-111 (7); 10: DB-112–DB-113 (2); 11: AI-490–AI-490 (1) |
| `metadata-modules/connected-account` | 05: MK-A09–MK-A15 (12) |
| `metadata-modules/data-source` | Intern (D) |
| `metadata-modules/deferred-workspace-operation` | LUCKA (drift) → LKS-035 |
| `metadata-modules/derived-field-metadata-ids` | 01: DM-160–DM-160 (1) |
| `metadata-modules/field-metadata-option` | 01: DM-130–DM-130 (1) |
| `metadata-modules/field-metadata` | 01: DM-011–DM-125 (18); 02: VY-178–VY-180 (2); 03: PS-129–PS-129 (1); 07: API-041–API-041 (1); 09: IE-162–IE-164 (3); 11: AI-405–AI-405 (1) |
| `metadata-modules/flat-agent-chat-channel-role` | Intern cache (D); funktionen i 11 (agent-chat-channel) |
| `metadata-modules/flat-agent-chat-channel` | Intern cache (D); funktionen i 11 |
| `metadata-modules/flat-agent` | 11: AI-142–AI-142 (1) |
| `metadata-modules/flat-application-variable` | Intern cache (D); funktionen i 07 API-176–API-177 |
| `metadata-modules/flat-command-menu-item` | Täckt: 04 NAV-030, NAV-031 (validerare); i övrigt cache (D) |
| `metadata-modules/flat-connection-provider` | Intern cache (D); funktionen i 07 (application/connection-provider) |
| `metadata-modules/flat-entity` | Delvis LUCKA: översättnings- och överskuggningskonstanterna → LKS-004, LKS-006 |
| `metadata-modules/flat-field-metadata-option` | Intern cache (D); funktionen i 01 (field-metadata-option) |
| `metadata-modules/flat-field-metadata` | 01: DM-111–DM-148 (21); 03: PS-087–PS-087 (1) |
| `metadata-modules/flat-field-permission` | 08: AR-411–AR-411 (1) |
| `metadata-modules/flat-front-component` | 07: API-425–API-425 (1) |
| `metadata-modules/flat-index-metadata` | 01: DM-274–DM-274 (1) |
| `metadata-modules/flat-mcp-server` | 07: API-164–API-164 (1) |
| `metadata-modules/flat-messaging-provider` | Intern cache (D); funktionen i 05 |
| `metadata-modules/flat-navigation-menu-item` | 04: NAV-013–NAV-019 (6) |
| `metadata-modules/flat-object-metadata` | 01: DM-080–DM-099 (11) |
| `metadata-modules/flat-object-permission` | Intern cache (D); funktionen i 08 |
| `metadata-modules/flat-page-layout-tab` | 03: PS-211–PS-211 (1) |
| `metadata-modules/flat-page-layout-widget` | 03: PS-211–PS-213 (3); 10: DB-081–DB-090 (9) |
| `metadata-modules/flat-page-layout` | 03: PS-211–PS-213 (3) |
| `metadata-modules/flat-permission-flag` | Intern cache (D); funktionen i 08 |
| `metadata-modules/flat-related-record-path` | 01: DM-173–DM-173 (1) |
| `metadata-modules/flat-role-permission-flag` | Intern cache (D); funktionen i 08 |
| `metadata-modules/flat-role-target` | Intern cache (D); funktionen i 08 |
| `metadata-modules/flat-role` | Täckt: 08 AR-401, AR-408, AR-912, AR-950, AR-951 (checklista 08) |
| `metadata-modules/flat-row-level-permission-predicate` | Intern cache (D); funktionen i 08 |
| `metadata-modules/flat-search-field-metadata` | Intern cache (D); funktionen i 01, 04 |
| `metadata-modules/flat-settings-menu-item` | Intern cache (D); funktionen i 04 |
| `metadata-modules/flat-skill` | 11: AI-141–AI-141 (1) |
| `metadata-modules/flat-timeline-activity-type` | Intern cache (D); funktionen i 01 |
| `metadata-modules/flat-validation-rule` | Intern cache (D); funktionen i 01 (Enterprise) |
| `metadata-modules/flat-view-field-group` | Täckt via 02 (view*, validerarna i workspace-migration) |
| `metadata-modules/flat-view-field` | Täckt via 02 (view*, validerarna i workspace-migration) |
| `metadata-modules/flat-view-filter-group` | Täckt via 02 (view*) |
| `metadata-modules/flat-view-filter` | Täckt: 02 VY-059 |
| `metadata-modules/flat-view-group` | Täckt via 02 (view*) |
| `metadata-modules/flat-view-sort` | Täckt via 02 (view*) |
| `metadata-modules/flat-view` | 02: VY-018–VY-018 (1) |
| `metadata-modules/flat-webhook` | 07: API-090–API-090 (1) |
| `metadata-modules/flat-workflow-version` | Läst av 06 på fillistor; cache (D) |
| `metadata-modules/flat-workflow` | Läst av 06 på fillistor; cache (D) |
| `metadata-modules/formula-field` | 01: DM-150–DM-254 (5) |
| `metadata-modules/front-component` | 07: API-274–API-385 (4); 10: DB-179–DB-179 (1) |
| `metadata-modules/index-metadata` | 01: DM-162–DM-274 (4) |
| `metadata-modules/logic-function-layer` | 06: AF-810–AF-810 (1) |
| `metadata-modules/logic-function` | 06: AF-243–AF-1037 (19); 07: API-242–API-349 (2) |
| `metadata-modules/mcp-server` | 07: API-164–API-165 (2); 11: AI-143–AI-147 (5) |
| `metadata-modules/message-channel` | 05: MK-B15–MK-B18 (6) |
| `metadata-modules/message-folder` | 05: MK-B11–MK-B11 (1) |
| `metadata-modules/messaging-provider` | 05: MK-B18–MK-N06 (4) |
| `metadata-modules/metadata-side-effect` | 01: DM-220–DM-083 (4); 02: VY-177–VY-178 (2); 03: PS-202–PS-202 (1) |
| `metadata-modules/metadata-translation` | LUCKA → LKS-001–LKS-004, LKS-007 (01 har bara gränssnittet i DM-211) |
| `metadata-modules/minimal-metadata` | LUCKA (låg) → LKS-017 |
| `metadata-modules/navigation-menu-item` | 04: NAV-012–NAV-158 (19); 11: AI-408–AI-408 (1) |
| `metadata-modules/object-metadata` | 01: DM-050–DM-083 (30); 02: VY-095–VY-179 (4); 03: PS-110–PS-202 (2); 07: API-040–API-040 (1); 09: IE-127–IE-152 (4); 11: AI-405–AI-405 (1) |
| `metadata-modules/object-permission` | 08: AR-410–AR-411 (2) |
| `metadata-modules/overrides` | LUCKA → LKS-006–LKS-008 (01 nämner bara överskuggning i DM-092, DM-172) |
| `metadata-modules/page-layout-tab` | 03: PS-027–PS-027 (1); 10: DB-098–DB-163 (3) |
| `metadata-modules/page-layout-widget` | 03: PS-028–PS-029 (2); 10: DB-058–DB-086 (11) |
| `metadata-modules/page-layout` | 03: PS-015–PS-042 (36); 07: API-043–API-043 (1); 10: DB-005–DB-095 (65); 11: AI-404–AI-404 (1); 12: UX-294–UX-294 (1) |
| `metadata-modules/pagination` | Täckt i sak: DM-096 (listning med filter och sidindelning); generiskt lager |
| `metadata-modules/permission-flag` | 08: AR-412–AR-414 (2) |
| `metadata-modules/related-record-path` | 01: DM-173–DM-274 (2); 08: AR-942–AR-942 (1) |
| `metadata-modules/role-permission-flag` | 08: AR-414–AR-414 (1) |
| `metadata-modules/role-target` | 08: AR-408–AR-408 (2) |
| `metadata-modules/role` | 08: AR-400–AR-912 (16); 11: AI-407–AI-407 (1) |
| `metadata-modules/route-trigger` | 06: AF-805–AF-805 (1) |
| `metadata-modules/row-level-permission-predicate` | 08: AR-420–AR-421 (2) |
| `metadata-modules/search-field-metadata` | 01: DM-160–DM-160 (1); 04: NAV-004–NAV-004 (1) |
| `metadata-modules/settings-menu-item` | 04: NAV-035–NAV-035 (1) |
| `metadata-modules/skill` | 11: AI-140–AI-141 (2) |
| `metadata-modules/timeline-activity-type` | 01: DM-170–DM-170 (5) |
| `metadata-modules/utils` | Täckt i sak: DM-085, DM-086 (namnregler, härledning ur etikett); i övrigt intern (D) |
| `metadata-modules/validation-rule` | 01: DM-155–DM-253 (6); 11: AI-405–AI-405 (1) |
| `metadata-modules/view-field-group` | 02: VY-033–VY-033 (1) |
| `metadata-modules/view-field` | 02: VY-027–VY-030 (3); 11: AI-406–AI-406 (1) |
| `metadata-modules/view-filter-group` | 02: VY-059–VY-059 (1) |
| `metadata-modules/view-filter` | 02: VY-035–VY-035 (1); 11: AI-406–AI-406 (1) |
| `metadata-modules/view-group` | 02: VY-062–VY-062 (1) |
| `metadata-modules/view-sort` | 02: VY-061–VY-097 (2); 11: AI-406–AI-406 (1) |
| `metadata-modules/view` | 02: VY-001–VY-161 (23); 03: PS-135–PS-135 (1); 07: API-042–API-042 (1); 10: DB-110–DB-110 (1); 11: AI-406–AI-406 (1) |
| `metadata-modules/webhook` | 07: API-044–API-095 (17); 11: AI-408–AI-408 (1) |
| `metadata-modules/workspace-feature-flags-map-cache` | Intern cache (D); flaggorna i 08 |
| `metadata-modules/workspace-metadata-version` | LUCKA (låg) → LKS-018 |
| `engine/api` | 01: DM-185–DM-185 (1); 03: PS-107–PS-110 (3); 07: API-050–API-024 (13); 09: IE-127–IE-041 (7); 10: DB-100–DB-189 (4); 11: AI-420–AI-422 (3); 12: UX-244–UX-244 (1) |
| `engine/constants` | LUCKA (låg): maxstorlek på anrop och standardfel → LKS-023 (den maskinella träffen var falsk, ordet "constants" förekommer överallt) |
| `engine/core-entity-cache` | Intern (D) |
| `engine/core-modules` | 01: DM-184–DM-185 (5); 02: VY-170–VY-170 (1); 03: PS-117–PS-154 (13); 04: NAV-001–NAV-163 (13); 05: MK-A01–MK-A12 (28); 06: AF-009–AF-806 (46); 07: API-032–API-429 (40); 08: AR-200–AR-246 (24); 09: IE-107–IE-176 (7); 10: DB-089–DB-166 (3); 11: AI-150–AI-164 (10) |
| `engine/dataloaders` | Intern (D) |
| `engine/decorators` | 01: DM-085–DM-269 (2); 07: API-161–API-161 (1) |
| `engine/guards` | 02: VY-010–VY-010 (1); 03: PS-194–PS-194 (1); 07: API-141–API-141 (1); 08: AR-415–AR-704 (4) |
| `engine/metadata-modules` | 01: DM-080–DM-170 (16); 02: VY-018–VY-177 (2); 03: PS-026–PS-087 (6); 04: NAV-004–NAV-035 (4); 05: MK-A16–MK-B18 (7); 06: AF-615–AF-1037 (12); 07: API-040–API-095 (17); 08: AR-400–AR-408 (18); 09: IE-127–IE-127 (1); 10: DB-058–DB-095 (8); 11: AI-020–AI-126 (13) |
| `engine/middlewares` | 07: API-140–API-140 (1); 08: AR-231–AR-231 (1); LUCKA för CSRF, avstängd arbetsyta och åtkomstlogg → LKS-019–LKS-021 |
| `engine/permissions` | 02: VY-010–VY-010 (1); 03: PS-112–PS-112 (1); 08: AR-402–AR-912 (27) |
| `engine/record-filter` | 02: VY-084–VY-176 (8) |
| `engine/subscriptions` | 07: API-067–API-430 (5) |
| `engine/trash-cleanup` | 01: DM-184–DM-184 (1) |
| `engine/twenty-orm` | 01: DM-180–DM-274 (9); 07: API-300–API-300 (1) |
| `engine/utils` | Täckt i sak via 06 (körinsikter, AF) och 07; språkrubriken saknades → LKS-022 (den maskinella träffen var falsk) |
| `engine/workspace-cache-storage` | Intern (D) |
| `engine/workspace-cache` | Intern (D) |
| `engine/workspace-datasource` | Intern (D) |
| `engine/workspace-event-emitter` | 06: AF-122–AF-122 (1); 07: API-092–API-303 (2) |
| `engine/workspace-manager` | 01: DM-042–DM-277 (4); 02: VY-022–VY-022 (1); 03: PS-110–PS-135 (3); 04: NAV-015–NAV-030 (2); 05: MK-C30–MK-B17 (2); 07: API-091–API-091 (1); 08: AR-338–AR-408 (6); 09: IE-128–IE-042 (11); 10: DB-110–DB-190 (4); 11: AI-141–AI-490 (5) |
| `engine/workspace-query-executor` | 07: API-037–API-037 (1) |
| `workspace-manager/dev-seeder` | 10: DB-190–DB-190 (1) |
| `workspace-manager/standard-objects-prefill-data` | 10: DB-111–DB-166 (2) |
| `workspace-manager/twenty-standard-application` | 01: DM-042–DM-277 (6); 03: PS-110–PS-135 (3); 08: AR-401–AR-912 (2); 09: IE-128–IE-042 (11); 10: DB-110–DB-112 (3); 11: AI-350–AI-490 (3) |
| `workspace-manager/types` | Intern: typer (D) (den maskinella träffen var falsk) |
| `workspace-manager/utils` | Täckt via 01 och 03 (standardapplikationens sidlayouter, fältbyggare); den maskinella träffen var bred |
| `workspace-manager/workspace-cleaner` | 08: AR-338–AR-338 (1) |
| `workspace-manager/workspace-migration` | 02: VY-022–VY-022 (1); 05: MK-C30–MK-B17 (2); 08: AR-943–AR-950 (2) |
| `workspace-manager/workspace-version` | Intern (D) |
| `api/__mocks__` | Intern: testdata (D) |
| `api/common` | 01: DM-066–DM-185 (4); 03: PS-107–PS-107 (1); 04: NAV-085–NAV-158 (9); 05: MK-C01–MK-A12 (11); 06: AF-501–AF-1008 (4); 07: API-007–API-424 (27); 10: DB-100–DB-189 (3) |
| `api/graphql` | 03: PS-109–PS-118 (2); 07: API-050–API-359 (9) |
| `api/mcp` | 07: API-140–API-426 (13); 11: AI-189–AI-422 (4) |
| `api/rest` | 03: PS-109–PS-109 (1); 07: API-003–API-024 (30); 09: IE-131–IE-041 (4); 10: DB-150–DB-150 (1) |
| `api/types` | Täckt enligt 07:s avprickning (api/common, utils, types läst); den maskinella träffen var falsk |
| `api/utils` | Täckt enligt 07:s avprickning; den maskinella träffen var falsk |

## B. Luckor

| Område | Vad som saknas | Var i förlagan | Hur allvarligt |
|---|---|---|---|
| Översättning av metadata | Frågan som listar översättningar per språk med ursprungsmärkning, vilka egenskaper som går att översätta per metadatatyp, och att installerade appars etiketter översätts ur appens egen katalog. 01 beskriver bara gränssnittet (DM-211) | `metadata-modules/metadata-translation`, `metadata-modules/application-translation-catalog`, `metadata-modules/flat-entity/constant` | hög (krävs för en tvåspråkig produkt och för att döpa om standardobjekt) |
| Överskuggning av app-ägd metadata | Vilka egenskaper arbetsytan får ändra på standardobjekt, standardfält, vyer, sidlayouter, kommandon, färdigheter och agenter utan att röra källan, och att ändringen överlever appuppdateringar | `metadata-modules/overrides`, `metadata-modules/flat-entity/constant` | hög |
| Klientkonfiguration | Det publika svaret `GET /client-config` och allt det styr i webbklienten: inloggningssätt, provperioder, introduktionsbelöningar, AI-katalog, leverantörsväxlar, underhållsläge | `core-modules/client-config` | medel |
| Underhållsbanderoll per användare | Att avfärdandet lagras per användare och arbetsyta och nollställs när underhållsläget sätts eller rensas, och att slut måste ligga efter start | `core-modules/client-config`, `core-modules/admin-panel/maintenance-mode.service.ts` | låg |
| Middleware och säkerhetsrubriker | CSRF-skydd för kakbaserade sessioner, vägran för avstängda arbetsytor i GraphQL, API-åtkomstlogg, språk per anrop, maxstorlek på anrop, CSP och iframe-behörigheter i webbklientens dokument | `engine/middlewares`, `engine/constants`, `engine/utils`, `core-modules/frontend` | medel |
| Felomdirigering från inloggningsskydd | Att fel i HTTP-vägarnas skydd leder om till verifieringssidan på arbetsytans domän | `core-modules/guard-redirect` | låg |
| Minimal metadata och metadataversion | Den lätta metadatafrågan med samlingshashar som klienten använder för att avgöra vad som ska laddas om | `metadata-modules/minimal-metadata`, `metadata-modules/workspace-metadata-version` | låg |
| Driftkommandon | Ett 30-tal kommandon för operatören (installera och uppgradera appar överallt, nödstopp, faktureringssynk, tömma cache, återställa kanaler, återköra uppskjutna operationer, exportera arbetsyta som SQL, skapa API-nyckel) | `core-modules/*/commands`, `database/commands`, `modules/*/commands`, `engine/workspace-manager/*/commands` | medel för egen drift, låg för användaren |
| Uppskjutna arbetsyteoperationer | Tillstånd, omförsök och återställning av tunga schemaändringar | `metadata-modules/deferred-workspace-operation`, `engine/workspace-manager/workspace-migration/workspace-migration-runner` | låg |
| Lagrade engångsnycklar och nyckel-värde-lagret | Vilka sorters engångstoken som sparas och vilka sorters nyckel-värde-poster som finns | `core-modules/app-token`, `core-modules/key-value-pair` | låg |
| Utgående HTTP, standardvärden | Tidsgräns och maxstorlek för svar, och hur undantagslistan normaliseras | `core-modules/secure-http-client` | låg |
| Hälsoendpoint | Sökväg och beteende för den publika hälsokontrollen | `core-modules/health` | låg |
| Konfigurationsvariabler utan namn hos läsarna | 135 av 274 variabler namnges inte. Många beskrivs i sak (tokenlivslängder, provperioder, rensning av arbetsytor), men lagring, databas och köer, loggning och mätning, supportchatt, kartor och adressförslag, Cloudflare, Lambda, SES och Resend, AI-leverantörsfilen och flera funktionsväxlar saknas helt | `core-modules/twenty-config/config-variables.ts` | låg till medel (bara egen drift) |
| Loggning och felrapportering | Logg- och felhanterardrivrutiner, Sentry, nivåer | `core-modules/logger`, `core-modules/exception-handler`, `core-modules/sentry` | låg |

## C. Funktionsrader för luckorna

### C1. Översättning och överskuggning av metadata

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKS-001 | Administratören kan läsa alla översättningar av ett objekts eller ett fälts texter. | GraphQL-frågan `metadataTranslations` på metadata-API:t. Kräver behörighetsflaggan DATA_MODEL. Indata: antingen `objectMetadataId` eller `fieldMetadataId`, och valfritt ett språk; utan språk returneras alla språk appen stöder. Anges varken objekt eller fält ges ett indatafel. Okänt id ger tom lista, inte fel. Egenskaper vars kanoniska värde är tomt hoppas över. | metadata-modules/metadata-translation/ | AGPL |
| LKS-002 | Varje översättningsrad visar tre värden. | Per egenskap och språk: källvärdet (det appen levererar), det kanoniska värdet (arbetsytans namnbyte för alla språk om ett sådant finns, annars källvärdet) och det effektiva värdet som användaren ser på det språket. | metadata-modules/metadata-translation/dtos/metadata-translation.dto.ts, services/metadata-translation.service.ts | AGPL |
| LKS-003 | Varje översättningsrad märks med ursprung. | Tre ursprung: WORKSPACE (arbetsytan har en egen översättning för språket), SHIPPED (ingen egen översättning, men appens medlevererade översättning skiljer sig från det kanoniska värdet), INHERITED (värdet är oöversatt och ärvt). Ordningen avgör: egen översättning går före medlevererad. | metadata-modules/metadata-translation/services/metadata-translation.service.ts | AGPL |
| LKS-004 | Vilka texter som går att översätta, per metadatatyp. | Objekt: etikett singular, etikett plural, beskrivning. Fält: etikett, beskrivning. Vy, fältgrupp i vy, navigeringspost: namn. Sidlayout: namn. Flik och widget: titel. Kommandomenyns post: etikett och kort etikett. Tidslinjens händelsetyp: etikett. Inställningsmenyns post: titel. Färdighet: etikett och beskrivning. En översättning av en annan egenskap avvisas. | twenty-shared/src/i18n/translatable-properties-by-metadata-name.ts; metadata-modules/overrides/utils/find-invalid-translation-override-properties.util.ts | MIT (twenty-shared), AGPL |
| LKS-005 | Installerade appars texter översätts ur appens egen katalog. | Etiketter som en app (även standardappen) levererar slås upp i appens översättningskatalog för språket; arbetsytans egna översättningar läggs ovanpå. Katalogen väljs via appens registrering. | metadata-modules/application-translation-catalog/ | AGPL |
| LKS-006 | Arbetsytan kan ändra utvalda egenskaper på metadata som en app äger utan att ändra appen. | Ändringen sparas som arbetsytans överskuggning på posten; källvärdet behålls och en appuppdatering skriver inte över överskuggningen. Överskuggningsbart: objekt (etiketter, beskrivning, ikon, färg, bildfält, öppningssätt för poster, aktiv); fält (etikett, beskrivning, ikon, aktiv); vy (namn, typ, ikon, position, kompakt läge, öppningssätt, kanbanaggregat och dess fält, fritextfilter, kalenderlayout och datumfält, privat, grupperingsfält, dölj tomma grupper, grupper som flikar, kolumnbredd, laddningsgräns per grupp, aktiv); fältgrupp i vy (namn, position, synlig, aktiv); vyfält (synlig, bredd, position, aggregat, grupp, etikett, aktiv); agent (etikett, ikon, avatarfärg och -form, beskrivning, instruktion, modell, svarsformat, modellinställningar, aktiv); widget (titel, position, flik, villkorad visning och tillgänglighet, aktiv); flik (titel, position, ikon, aktiv); färdighet (etikett, ikon, beskrivning, innehåll, aktiv); kommandomenyns post (etikett, ikon, kort etikett, position, fäst, tillgänglighet och dess objekt, motorkomponent, kortkommandon, sidlayout, aktiv); navigeringspost (aktiv); tidslinjens händelsetyp (etikett, ikon, aktiv); valalternativ (etikett, färg, beskrivning, position, aktiv); relaterad postväg (ärvd, aktiv). | metadata-modules/flat-entity/constant/all-entity-properties-configuration-by-metadata-name.constant.ts; metadata-modules/overrides/constants/ | AGPL |
| LKS-007 | Det användaren ser är källvärdet med överskuggning och översättning ovanpå. | Effektivt värde räknas fram i ordningen: appens källvärde, arbetsytans namnbyte för alla språk, och sist översättningen för användarens språk (arbetsytans egen, annars appens). Läsning via API returnerar det effektiva värdet (jämför DM-096). | metadata-modules/overrides/utils/ (resolve-effective-entity-property, merge-translations-into-overrides) | AGPL |
| LKS-008 | Överskuggningar har författare. | En överskuggning knyts till den som skrev den (arbetsytans egen app eller en annan app). Att aktivera eller inaktivera en app-ägd post går också via överskuggningen. Äldre överskuggningar utan författare normaliseras. Ordningen mellan flera författare räknas fram (detaljerna se Oklarheter). | metadata-modules/overrides/utils/ (compute-override-author-order, dispatch-is-active-update-to-authored-override, normalize-authored-overrides, is-legacy-non-authored-override) | AGPL |

### C2. Klientkonfiguration och underhållsläge

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKS-009 | Webbklienten hämtar instansens publika konfiguration. | `GET /client-config` utan inloggning och utan behörighetskrav. Svaret styr vilka inloggningsknappar, menyval och flöden webbklienten visar, innan någon har loggat in. Med flera arbetsytor dirigeras vägen till servern på varje arbetsytas värdnamn (jämför API-419). | core-modules/client-config/client-config.controller.ts, services/client-config.service.ts | AGPL |
| LKS-010 | Inloggning och adresser i klientkonfigurationen. | Inloggningssätt på instansnivå: Google, lösenord, Microsoft (var för sig av eller på); magisk länk alltid av; SSO-listan är tom på instansnivå (SSO hämtas per arbetsyta). Dessutom: förifylld inloggning (demo), flerarbetsyteläge, om e-postverifiering krävs, standardunderdomän, webbklientens domän, serveradress, domän för publika funktionsrutter (kan saknas), appversion. | core-modules/client-config/services/client-config.service.ts | AGPL |
| LKS-011 | Fakturering i klientkonfigurationen. | Om fakturering är på, länk när plan krävs, Stripes publika nyckel och två provperioder: med kort (standard 30 dagar) och utan kort (standard 7 dagar), var och en märkt med om kort krävs. | core-modules/client-config/services/client-config.service.ts; twenty-config/config-variables.ts (BILLING_*) | AGPL |
| LKS-012 | Belöningar i introduktionen visas bara när fakturering är på. | Krediter för att importera kontakter (standard 1 000 000 interna enheter), per inbjuden kollega (500 000), för att skapa profil (lika med provperiodens krediter utan kort, 500 000) och för att uppgradera (skillnaden mellan provperiod med och utan kort, aldrig negativ; standard 2 500 000 − 500 000). Högst 5 inbjudningar räknas. Värdena omräknas till visningskrediter innan de skickas. Utan fakturering är hela blocket tomt. | core-modules/client-config/services/client-config.service.ts; twenty-config/config-variables.ts (ONBOARDING_*, BILLING_FREE_WORKFLOW_CREDITS_*) | AGPL |
| LKS-013 | AI-katalogen följer med klientkonfigurationen. | Tre listor: valbara modeller (id, etikett, familj, SDK, pris per miljon in- och ut-token, inbyggda förmågor som webbsökning, utfasad, leverantör, kontextfönster, max ut-token, datahemvist, nolllagring, benchmarkvärden, tillgängliga ansträngningsnivåer), utvärderingsmodeller (frågetyper, max kriterier per fråga, max poängnivåer, median-svarstid, pris) och standardmodell per nivå och datapolicy (kräver viss region, kräver nolllagring). En nivå utan tillåten modell utelämnas. | core-modules/client-config/client-config.entity.ts, services/client-config.service.ts | AGPL |
| LKS-014 | Funktionsväxlar i klientkonfigurationen. | Gmail-, Google-kalender-, Microsoft-post- och Microsoft-kalendersynk; IMAP/SMTP/CalDAV; förhandsvisning av bilagor; analys; om ClickHouse är konfigurerat; Cloudflare-integration; bolagsberikning; bokningssteg i introduktionen och bokningssidans id; AI-chatt i introduktionen; låst schemaändring (DDL); avsändardomäner i demoläge; hämtning av ikoner från förlagans ikontjänst; konfiguration i databasen; om funktionsflaggor får hanteras (alltid i utvecklingsläge, när fakturering är på, eller när en särskild växel är på) och listan över publika funktionsflaggor för Labb; kakbaserad session (alltid på). | core-modules/client-config/services/client-config.service.ts | AGPL |
| LKS-015 | Drift- och integrationsuppgifter i klientkonfigurationen. | Max antal poster en mutation får påverka (standard 100), supportchattens drivrutin (ingen eller Front) och chatt-id, Sentry för webbklienten (miljö, version, adress, samplingsgrad standard 0,1), captcha (leverantör och publik nyckel), instanstyp för organisationslicensen (standard produktion) och den publika nyckeln för webbaviseringar. | core-modules/client-config/services/client-config.service.ts | AGPL |
| LKS-016 | Underhållsläget följer med klientkonfigurationen och banderollen kan avfärdas per person. | När serveradmin satt ett underhållsfönster innehåller svaret start, slut och valfri länk; annars saknas fältet. Ett fönster utan start eller slut räknas som inget. Slut måste ligga efter start (felkod INVALID_MAINTENANCE_MODE_TIME_RANGE). Inloggad användare kan avfärda banderollen (`dismissMaintenanceModeBanner`) och fråga om den är avfärdad (`isMaintenanceModeBannerDismissed`); avfärdandet gäller användaren i en viss arbetsyta och nollställs för alla när fönstret sätts eller rensas. API-nycklar, OAuth-klienter och appar når inte de två anropen. | core-modules/client-config/client-config.resolver.ts; core-modules/admin-panel/maintenance-mode.service.ts | AGPL |

### C3. Metadata för klientens cache

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKS-017 | Klienten kan hämta en minimal metadatabild. | Frågan `minimalMetadata` ger objekt (id, namn singular och plural, etiketter, ikon, färg, aktiv, system, fjärr), vyer (id, typ, nyckel, objekt) och en hash per metadatasamling så att klienten bara laddar om samlingar som ändrats. Tillåten för användarsession (ej arbetsyteoberoende), API-nyckel, OAuth-klient och app, utan behörighetsflagga, och även när arbetsytan är avstängd. Etiketterna kommer i anroparens språk. | metadata-modules/minimal-metadata/ | AGPL |
| LKS-018 | Arbetsytans metadata har ett versionsnummer. | Versionen räknas upp när datamodellen ändras, så att klienter och cachar vet att de ska läsa om. Saknas versionen ges ett eget fel. | metadata-modules/workspace-metadata-version/ | AGPL |

### C4. Middleware, säkerhetsrubriker och felomdirigering

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKS-019 | Kakbaserade sessioner skyddas mot förfalskade anrop (CSRF). | Gäller bara ändrande anrop (inte GET, HEAD, OPTIONS) som saknar bärartoken men har en sessionskaka. Ursprungsrubriken (`Origin`) måste finnas och vara ett tillåtet ursprung (jämför API-419); saknas den vägras anropet ändå. Vägran: HTTP 403 med felkoden CSRF_ORIGIN_MISMATCH. Anrop med bärartoken berörs inte. | engine/middlewares/cookie-session-csrf.middleware.ts | AGPL |
| LKS-020 | En avstängd arbetsyta får inga GraphQL-svar. | Anrop mot en arbetsyta som är suspenderad eller raderad besvaras med felet WORKSPACE_SUSPENDED. Undantag: åtgärder som uttryckligen tillåts för avstängda arbetsytor (t.ex. LKS-017 och fakturering för att kunna återaktivera). | engine/middlewares/graphql-refuse-suspended-workspace.middleware.ts; engine/decorators/auth/allow-suspended-workspace.decorator.ts | AGPL |
| LKS-021 | Operatören kan slå på en åtkomstlogg för API:t. | Av som standard (API_ACCESS_LOG_ENABLED). En rad per anrop i nyckel=värde-format: metod, sökväg utan frågesträng, körda GraphQL-rotresolvers (högst 512 tecken), MCP-metod och verktyg, HTTP-status eller markering att anropet avbröts, varaktighet i ms, aktör (användare, API-nyckel, app), imitatörens id, autentiseringssätt och tokentyp, samt anropets id (högst 128 tecken, bara bokstäver, siffror och `_.:-`). Raden skrivs en gång även om anropet både avslutas och stängs. | engine/middlewares/api-access-log.middleware.ts, utils/build-api-access-log-line.util.ts; engine/utils/to-logfmt.util.ts | AGPL |
| LKS-022 | Anropets språk sätts med en rubrik. | Rubriken `x-locale` anger språk för felmeddelanden och översatta etiketter; värdet normaliseras till ett av appens språk, annars standardspråket. | engine/utils/get-request-locale-from-header.util.ts; engine/decorators/locale/request-locale.decorator.ts | AGPL |
| LKS-023 | Anrop har en maxstorlek och ett neutralt standardfel. | Anropskroppen får vara högst 100 MB. Oväntade fel visas för användaren som "An error occurred." (översatt) och interna fel som "Internal server error". | engine/constants/max-request-body-size.constant.ts, standard-error-message.constant.ts; engine/middlewares/constants/default-error-message.constant.ts | AGPL |
| LKS-024 | Webbklientens startsida skickas med säkerhetsrubriker. | Servern serverar webbklientens dokument med en innehållspolicy som förbjuder inbäddade objekt, låser basadressen till det egna ursprunget och tillåter manifest bara från det egna ursprunget. | core-modules/frontend/constants/document-content-security-policy-directives.constant.ts, frontend.service.ts | AGPL |
| LKS-025 | Installerade appar kan få kamera, mikrofon och liknande i sina inbäddade ramar. | Dokumentets behörighetspolicy (`Permissions-Policy`) byggs av de iframe-mediebehörigheter som installerade, ej raderade appar beviljats i arbetsytan. Policyn får vara högst 2 048 byte; blir den större kortas den så att den ryms. | core-modules/frontend/utils/ (build-iframe-media-permissions-policy, fit-iframe-media-permissions-to-policy-size-limit, get-active-application-iframe-media-permissions), constants/max-iframe-media-permissions-policy-bytes.constant.ts | AGPL |
| LKS-026 | Fel i inloggningsskyddet på HTTP-vägar leder om användaren. | För vanliga HTTP-vägar (t.ex. OAuth-återanrop) leder ett fel om till verifieringssidan på arbetsytans domän (egen domän om aktiverad, annars underdomän) med felet i adressen; arbetsytan tas från anropets Referer, annars standardunderdomänen. För GraphQL kastas felet i stället. Felet rapporteras till felhanteraren. | core-modules/guard-redirect/services/guard-redirect.service.ts | AGPL |
| LKS-027 | Publik hälsokontroll för övervakning. | `GET /healthz` utan inloggning och utan behörighet; svarar OK när servern är uppe (inga beroenden kontrolleras i den publika vägen; detaljerad hälsa finns i serveradminpanelen, AR-710). | core-modules/health/controllers/health.controller.ts; twenty-shared/src/types/ApiPath.ts | AGPL |
| LKS-028 | Utgående HTTP har fasta standardgränser. | Tidsgräns 60 s och svar högst 50 MB om inget annat anges av anroparen (webhooks har egen tidsgräns, API-097). Poster i undantagslistan för interna värdar kan skrivas som värd, värd:port eller hel adress; de normaliseras till värdnamnet (porten ignoreras, IPv6-hakparenteser tas bort, gemener). En tillåten värd får nå privata nät men aldrig länklokala adresser, så molnets metadataadress förblir spärrad även om DNS ändras. Webbadresser i loggar maskeras. | core-modules/secure-http-client/constants/, utils/normalize-allowed-internal-host.util.ts, utils/get-is-blocked-ip.util.ts, utils/redact-outbound-request-url.util.ts | AGPL |

### C5. Drift: kommandon, uppskjutna operationer och lagring

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKS-029 | Operatören hanterar appar på alla arbetsytor från kommandoraden. | `application:install` installerar en app på varje arbetsyta som saknar den (redan installerade lämnas); `application:upgrade` köar ett uppgraderingsjobb per arbetsyta till senaste version; `application:kill-switch` stoppar (standard) eller släpper en apps funktionskörningar överallt; `install-pre-installed-apps` installerar alla registreringar märkta förinstallerade (idempotent); `marketplace:catalog-sync` synkar marknadsplatsens katalog; `application:rebuild-default-deps` laddar upp standardberoendena igen. | core-modules/application/*/commands/, database/commands/ | AGPL |
| LKS-030 | Operatören synkar fakturering mot Stripe. | `billing:sync-plans-data` hämtar produkter och priser; `billing:sync-customer-data` hämtar kunddata för aktiva arbetsytor; `billing:sync-entitlements` stämmer av rättigheter för alla arbetsytor; `billing:update-subscription-price` byter pris på prenumerationer. | core-modules/billing/commands/, core-modules/billing-webhook/commands/ | AGPL |
| LKS-031 | Operatören tömmer cachar. | `cache:flush` tömmer Redis-cachen för en namnrymd och ett mönster (standard alla namnrymder, mönster `*`; prefixet läggs på automatiskt; okänd namnrymd ger fel med listan över giltiga); `cache:flat-cache-invalidate` tömmer metadatacachen för valda metadatanamn och arbetsytor. | core-modules/cache-storage/commands/flush-cache.command.ts; workspace-manager/workspace-migration/workspace-migration-runner/commands/flat-cache-invalidate.command.ts | AGPL |
| LKS-032 | Operatören styr synken från kommandoraden. | `messaging:trigger-message-list-fetch` och `calendar:trigger-event-list-fetch` startar hämtning direkt utan att vänta på schemat; `messaging:reset-channel` nollställer en kanal (eller alla i arbetsytan) för full omsynk; `messaging:message-cleaner-remove-orphans` tar bort föräldralösa meddelanden och trådar; `connected-account:create-webhook-subscription` flyttar Google- och Microsoft-kanaler från avfrågning till webhookprenumeration, utspritt i tid. | modules/messaging/*/commands/, modules/calendar/*/commands/, modules/connected-account/webhook-subscription-manager/commands/ | AGPL |
| LKS-033 | Operatören hanterar arbetsytor från kommandoraden. | `workspace:clean` (suspenderade), `workspace:clean:onboarding` (fast i introduktionen), `workspace:destroy`, `workspace:export` (hela arbetsytan som SQL-insättningar), `workspace:generate-api-key` (skriver ut en ny nyckel), `workspace:list-and-delete-orphaned-entities` (rader som pekar på borttagen arbetsyta), `workspace:rebuild-object` (bygger om en objekttabell för att frigöra kolumnplatser; databasen tillåter 1 600 kolumner per tabell och återanvänder aldrig borttagna), `feature-flag:update` (en flagga på en arbetsyta, en sats eller alla), `workflow:delete-workflow-runs`, `workflow:handle-staled-runs`, `access-groups:recompute-record-access-group-ids` och `channel-visibility:revoke-role-wide-access`. | engine/workspace-manager/*/commands/, database/commands/, core-modules/api-key/commands/, modules/workflow/*/command/, engine/permissions/*/commands/ | AGPL |
| LKS-034 | Operatören ser och kör uppgraderingen. | `upgrade:status` visar uppgraderingsstatus för instans och arbetsytor härledd ur migrationshistoriken; `run-instance-commands` kör instansens migrationer och kommandon; därtill ett hundratal versionsmärkta engångskommandon (`upgrade:<version>:<namn>`) som inte är funktioner i sig. Hälsoläget för en uppgradering är ett uppräknat värde som visas i serveradminpanelen (AR-711). | core-modules/upgrade/ | AGPL |
| LKS-035 | Tunga schemaändringar körs som uppskjutna operationer. | Varje operation sparas med arbetsyta, typ, data, ordning, status (standard PENDING), antal försök (start 0), senaste fel och tidpunkter. Ett schemalagt jobb återupptar avbrutna operationer; `workspace:retry-failed-deferred-workspace-operations` sätter FAILED till PENDING och köar dem igen, för en arbetsyta eller alla. | metadata-modules/deferred-workspace-operation/deferred-workspace-operation.entity.ts; workspace-manager/workspace-migration/workspace-migration-runner/ | AGPL |
| LKS-036 | Engångsnycklar sparas med typ. | Elva typer: förnyelsetoken, kodutmaning och auktoriseringskod (OAuth med PKCE), lösenordsåterställning, inbjudan, inbjudan i introduktionen, e-postverifiering, organisationslicensens giltighet, SSO-växling, tvåfaktorns återställningskod och tvåfaktorns reservkod. Livslängder i AR-310. | core-modules/app-token/app-token.entity.ts | AGPL |
| LKS-037 | Instansens små inställningar lagras som nyckel-värde-poster. | Fyra typer: användarvariabel (t.ex. avfärdade banderoller), funktionsflagga, konfigurationsvariabel (även underhållsläget) och appvariabel. Nyckeln är unik per arbetsyta, per användare, globalt respektive per app. | core-modules/key-value-pair/key-value-pair.entity.ts | AGPL |

### C6. Konfigurationsvariabler som ingen läsare namnger

Standardvärden inom parentes. Variabler märkta med (bara miljö) kan inte ändras i serveradminpanelen; (känslig) visas maskerad.

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKS-038 | Filagring konfigureras på instansen. | STORAGE_TYPE (lokal; alternativ S3), STORAGE_LOCAL_PATH (`.local-storage`), STORAGE_S3_REGION, STORAGE_S3_NAME, STORAGE_S3_ENDPOINT, STORAGE_S3_ACCESS_KEY_ID och STORAGE_S3_SECRET_ACCESS_KEY (känsliga), STORAGE_S3_PRESIGNED_URL_ENABLED (av), STORAGE_S3_PRESIGNED_URL_BASE, STORAGE_S3_PRESIGNED_URL_EXPIRES_IN (900 s), MAX_TARBALL_UPLOAD_SIZE_BYTES (100 MB, appaket). | core-modules/twenty-config/config-variables.ts (STORAGE_CONFIG) | AGPL |
| LKS-039 | Databas, Redis och köer konfigureras på instansen. | PG_DATABASE_URL och REDIS_URL (bara miljö, känsliga), PG_DATABASE_REPLICA_URL, PG_DATABASE_PRIMARY_TIMEOUT_MS och PG_DATABASE_REPLICA_TIMEOUT_MS (10 000), PG_POOL_MAX_CONNECTIONS (10), PG_POOL_IDLE_TIMEOUT_MS (600 000), PG_POOL_ALLOW_EXIT_ON_IDLE (på), PG_SSL_ALLOW_SELF_SIGNED (av), REDIS_CACHE_PREFIX (tom), REDIS_QUEUE_URL, REDIS_QUEUE_PREFIX (`bull`), WORKER_ENABLED_QUEUES och WORKER_EXCLUDED_QUEUES (tomma: alla köer), JOB_QUEUE_MEMORY_SHARE_BY_WORKSPACE_ID (0,4), JOB_QUEUE_MEMORY_SHARE_BY_APPLICATION_UNIVERSAL_IDENTIFIER (0,6), JOB_QUEUE_MEMORY_RESERVE (0,1), WORKSPACE_SCHEMA_DDL_LOCKED (av; spärrar schemaändringar). | core-modules/twenty-config/config-variables.ts (SERVER_CONFIG, ADVANCED_SETTINGS) | AGPL |
| LKS-040 | Serverns nätverk och identitet konfigureras. | NODE_ENV (produktion), NODE_PORT (3000), SERVER_KEEP_ALIVE_TIMEOUT_MS (65 000), TRUST_PROXY (loopback, länklokala och unika lokala nät), SERVER_INTERNAL_URL, SERVER_ID, FRONTEND_INDEX_URL, PUBLIC_DOMAIN_URL, DEFAULT_SUBDOMAIN (`app`), ADDITIONAL_RESERVED_SUBDOMAINS (tom), IS_MULTIWORKSPACE_ENABLED (av), AI_STREAM_SHUTDOWN_DRAIN_MS (300 000: pågående AI-strömmar får avslutas vid omstart), DPA_DEPLOYMENT_REGION (EU), ENTERPRISE_KEY (känslig), ENTERPRISE_API_URL, ENTERPRISE_INSTANCE_TYPE (produktion), SSL_KEY_PATH och SSL_CERT_PATH (egen HTTPS), SERVER_ADMIN_WORKSPACE_ID och SERVER_ADMIN_IDENTITY_ASSERTION_HEADER, _JWKS_URL, _ISSUER, _AUDIENCE (bara miljö; reglerna i AR-230, AR-925). | core-modules/twenty-config/config-variables.ts (SERVER_CONFIG, SSL) | AGPL (organisationslicensens delar Enterprise, se 08) |
| LKS-041 | Loggning, felrapportering och mätning konfigureras. | LOGGER_DRIVER (konsol), LOG_LEVELS (log, error, warn, performance), LOGGER_IS_BUFFER_ENABLED (på), EXCEPTION_HANDLER_DRIVER (konsol eller Sentry), SENTRY_DSN och SENTRY_FRONT_DSN (känsliga), SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE (0,1), SENTRY_PROFILES_SAMPLE_RATE (0,01), SENTRY_FRONT_TRACES_SAMPLE_RATE (0,1), TYPEORM_LOGGING (bara fel), METER_DRIVER (inga), METER_EXPORT_INTERVAL_MS (30 000), METER_TEMPORALITY (delta), EVENT_SINKS (ClickHouse), API_ACCESS_LOG_ENABLED (av, LKS-021). Sentry-händelser märks med arbetsyta också från bakgrundsjobb. | core-modules/twenty-config/config-variables.ts (LOGGING); core-modules/logger/, exception-handler/, sentry/ | AGPL |
| LKS-042 | Analys och användningsmätning konfigureras. | ANALYTICS_ENABLED (av), CLICKHOUSE_URL (känslig), USAGE_ROLLUP_FLUSH_INTERVAL_MS (60 000), BILLING_USAGE_CAP_CLICKHOUSE_ENABLED (av), HEALTH_METRICS_TIME_WINDOW_IN_MINUTES (5: fönstret för serveradminpanelens hälsomått). | core-modules/twenty-config/config-variables.ts (ANALYTICS_CONFIG, BILLING_CONFIG, ADVANCED_SETTINGS) | AGPL |
| LKS-043 | Supportchatt i appen kan slås på. | SUPPORT_DRIVER (ingen; alternativ Front), SUPPORT_FRONT_CHAT_ID och SUPPORT_FRONT_HMAC_KEY (känsliga; HMAC används för att identifiera användaren i chatten). | core-modules/twenty-config/config-variables.ts (SUPPORT_CHAT_CONFIG) | AGPL |
| LKS-044 | Funktionsväxlar på instansnivå. | IS_ATTACHMENT_PREVIEW_ENABLED (på), IS_MAPS_AND_ADDRESS_AUTOCOMPLETE_ENABLED (av) med ADDRESS_AUTOCOMPLETE_DRIVER och GOOGLE_MAP_API_KEY (känslig), IS_ONBOARDING_AI_CHAT_ENABLED (av), IS_IMAP_SMTP_CALDAV_ENABLED (på), IS_IMAP_SMTP_CALDAV_CONNECTION_TEST_ENABLED (på), IMAP_SMTP_ALLOW_SELF_SIGNED (av), MARKETPLACE_CATALOG_SYNC_CRON_ENABLED (på), SHOULD_SEED_STANDARD_RECORD_PAGE_LAYOUTS (på), IS_WORKSPACE_CREATION_LIMITED_TO_SERVER_ADMINS (på, AR-211), MAX_NUMBER_OF_WORKSPACES_DELETED_PER_EXECUTION (5), PEOPLE_DATA_LABS_API_KEY (känslig, berikning), IS_CLOUDFLARE_GEOLOCATION_ENABLED (av). | core-modules/twenty-config/config-variables.ts (ADVANCED_SETTINGS, CLOUDFLARE_CONFIG) | AGPL |
| LKS-045 | Appregistret och appanspråk konfigureras. | APP_REGISTRY_URL (npm:s publika register), APP_REGISTRY_CDN_URL (unpkg), APP_REGISTRY_TOKEN (känslig), APP_CLAIM_GITHUB_CLIENT_ID och APP_CLAIM_GITHUB_CLIENT_SECRET (känslig; används när en utvecklare gör anspråk på en app via GitHub). | core-modules/twenty-config/config-variables.ts (ADVANCED_SETTINGS) | AGPL |
| LKS-046 | Inloggnings- och synkleverantörer konfigureras. | Google: AUTH_GOOGLE_CLIENT_ID, AUTH_GOOGLE_CLIENT_SECRET (känslig), AUTH_GOOGLE_CALLBACK_URL (inloggning), AUTH_GOOGLE_APIS_CALLBACK_URL (kontoanslutning), MESSAGING_PROVIDER_GMAIL_ENABLED och CALENDAR_PROVIDER_GOOGLE_ENABLED (av), MESSAGING_GMAIL_PUBSUB_TOPIC och MESSAGING_GMAIL_PUBSUB_VERIFICATION_EMAIL. Microsoft: AUTH_MICROSOFT_CLIENT_ID, _CLIENT_SECRET (känslig), _CALLBACK_URL, _APIS_CALLBACK_URL, MESSAGING_PROVIDER_MICROSOFT_ENABLED och CALENDAR_PROVIDER_MICROSOFT_ENABLED (av). Reglerna i MK-A29. | core-modules/twenty-config/config-variables.ts (GOOGLE_AUTH, MICROSOFT_AUTH) | AGPL |
| LKS-047 | Systemmejlens drivrutin konfigureras. | EMAIL_DRIVER (logg; alternativ SMTP), EMAIL_SMTP_HOST, EMAIL_SMTP_PORT (587), EMAIL_SMTP_USER och EMAIL_SMTP_PASSWORD (känsliga), EMAIL_SMTP_NO_TLS (av), EMAIL_SMTP_NAME, EMAIL_FROM_ADDRESS och EMAIL_FROM_NAME (förlagans egna platshållare som standard; ska alltid sättas). | core-modules/twenty-config/config-variables.ts (EMAIL_SETTINGS) | AGPL |
| LKS-048 | Utskicksleverantörer konfigureras. | EMAILING_DOMAIN_DRIVER (logg; alternativ SES eller Resend), AWS_SES_REGION, AWS_SES_ACCOUNT_ID, AWS_SES_ACCESS_KEY_ID, AWS_SES_SECRET_ACCESS_KEY och AWS_SES_SESSION_TOKEN (känsliga), INBOUND_EMAIL_DOMAIN (domän för delade inkorgars vidarebefordringsadresser), SES_SNS_TOPIC_ARN_ALLOWLIST, SES_OUTBOUND_SNS_TOPIC_ARN, TATAMI_SES_WEBHOOK_URL (känslig) och TATAMI_SNS_TOPIC_ARN, RESEND_API_KEY och RESEND_WEBHOOK_SIGNING_SECRET (känsliga), RESEND_DOMAIN_REGION. Reglerna för utskick i 05 (MK-H, MK-I). | core-modules/twenty-config/config-variables.ts (AWS_SES_SETTINGS, RESEND_SETTINGS) | AGPL |
| LKS-049 | Captcha och Cloudflare konfigureras. | CAPTCHA_DRIVER, CAPTCHA_SITE_KEY, CAPTCHA_SECRET_KEY (känslig), CAPTCHA_MIN_SCORE (0). CLOUDFLARE_API_KEY och CLOUDFLARE_WEBHOOK_SECRET (känsliga), CLOUDFLARE_ZONE_ID (egna domäner), CLOUDFLARE_PUBLIC_DOMAIN_ZONE_ID (publika domäner), CLOUDFLARE_DCV_DELEGATION_ID (certifikatvalidering). | core-modules/twenty-config/config-variables.ts (CAPTCHA_CONFIG, CLOUDFLARE_CONFIG) | AGPL |
| LKS-050 | Körmiljön för logikfunktioner och kodtolken konfigureras. | LOGIC_FUNCTION_LAMBDA_REGION, _ROLE, _SUBHOSTING_ROLE, _RESOURCE_TAGS (tom), _ACCESS_KEY_ID och _SECRET_ACCESS_KEY (känsliga), _LAYER_BUCKET, _LAYER_BUCKET_REGION, _ENDPOINT; E2B_TEMPLATE (`code-interpreter-v1`); CODE_INTERPRETER_TIMEOUT_MS, _IDLE_TIMEOUT_MS (300 000) och _SESSION_MAX_AGE_MS (86 400 000), jämför AF-617, AF-822. | core-modules/twenty-config/config-variables.ts (LOGIC_FUNCTION_CONFIG, CODE_INTERPRETER_CONFIG) | AGPL |
| LKS-051 | AI-leverantörer kan ersättas och kompletteras med en egen fil. | AI_PROVIDERS (känslig): en post med samma namn som en inbyggd leverantör ersätter den och behåller bara de modeller den listar; används för egna adresser, fler regioner eller nycklar satta i panelen. AI_CATALOG_STORAGE_PATH: hämtar hela modellkatalogen från filagringen vid start. AI_SIGNED_FILE_URLS_ENABLED (på): skickar signerade fillänkar till leverantören när servern är publik, annars skickas filinnehållet. IS_OPENAI_REASONING_SUMMARY_ENABLED (på; stängs av om OpenAI-organisationen inte är verifierad). GROQ_API_KEY och TYPESAFE_AI_API_KEY (klassificeringsmodeller). | core-modules/twenty-config/config-variables.ts (LLM) | AGPL |
| LKS-052 | Tokenlivslängder har egna variabelnamn. | ACCESS_TOKEN_EXPIRES_IN (30m), WORKSPACE_AGNOSTIC_TOKEN_EXPIRES_IN (30m), REFRESH_TOKEN_EXPIRES_IN (60d), REFRESH_TOKEN_REUSE_GRACE_PERIOD (1m: en förnyelsetoken får återanvändas inom en minut), LOGIN_TOKEN_EXPIRES_IN (15m), FILE_TOKEN_EXPIRES_IN (1d), INVITATION_TOKEN_EXPIRES_IN (30d), SHORT_TERM_TOKEN_EXPIRES_IN (5m), APPLICATION_ACCESS_TOKEN_EXPIRES_IN (30m), APPLICATION_REFRESH_TOKEN_EXPIRES_IN (60d), PLAYGROUND_TOKEN_EXPIRES_IN (2h), TWO_FACTOR_AUTHENTICATION_RECOVERY_CODE_EXPIRES_IN (1h), CACHE_STORAGE_TTL (7 dygn). Varaktigheter måste vara positiva. Värdena står redan i AR-310; nyheten här är namnen, återanvändningsfönstret och cachetiden. | core-modules/twenty-config/config-variables.ts (TOKENS_DURATION), validators/positive-duration.validator.ts | AGPL |
| LKS-053 | Gränser för utskick, inbjudningar och appjobb har egna variabelnamn. | EMAIL_SEND_RATE_LIMITING_LIMIT och _TTL_IN_MS (100 per 10 s, hela servern), EMAIL_SEND_WORKSPACE_RATE_LIMITING_LIMIT och _TTL_IN_MS (100 per 10 s per arbetsyta), EMAIL_SEND_WORKSPACE_DAILY_LIMIT (1 000), INVITATION_SENDING_BY_EMAIL_THROTTLE_LIMIT (10) och INVITATION_SENDING_BY_WORKSPACE_THROTTLE_LIMIT (500), båda per 7 dygn; APPLICATION_JOB_ENQUEUE_RATE_LIMITING_LIMIT (500 per 60 s) och APPLICATION_REGISTRATION_JOB_ENQUEUE_RATE_LIMITING_LIMIT (2 000). Värdena för e-post och inbjudningar finns i MK-I44, MK-K13; köläggningsgränsen för appjobb saknas hos läsarna. | core-modules/twenty-config/config-variables.ts (RATE_LIMITING) | AGPL |
| LKS-054 | Fakturering och provperioder har egna variabelnamn. | BILLING_STRIPE_API_KEY och BILLING_STRIPE_WEBHOOK_SECRET (känsliga), BILLING_STRIPE_PUBLISHABLE_KEY, BILLING_PLAN_REQUIRED_LINK, BILLING_FREE_TRIAL_WITH_CREDIT_CARD_DURATION_IN_DAYS (30), _WITHOUT_CREDIT_CARD_ (7), BILLING_FREE_WORKFLOW_CREDITS_FOR_TRIAL_PERIOD_WITH_CREDIT_CARD (2 500 000) och _WITHOUT_ (500 000), BILLING_TRIAL_WITH_CREDIT_CARD_REMINDER_DAYS_BEFORE (7), BILLING_TRIAL_WITHOUT_CREDIT_CARD_REMINDER_DAYS_BEFORE (1), BILLING_SUBSCRIPTION_RENEWAL_REMINDER_DAYS_BEFORE (7), BILLING_TRIAL_LIMIT_EXEMPT_EMAIL_DOMAINS (tom: domäner som slipper provperiodsspärren), ONBOARDING_ENRICHMENT_CREDIT_REWARD_TIERS (belöningsnivåer för berikning). | core-modules/twenty-config/config-variables.ts (BILLING_CONFIG) | AGPL |
| LKS-055 | Rensning av inaktiva arbetsytor har egna variabelnamn. | WORKSPACE_INACTIVE_DAYS_BEFORE_NOTIFICATION (7), _BEFORE_SOFT_DELETION (14), _BEFORE_DELETION (21); reglerna i AR-338. | core-modules/twenty-config/config-variables.ts (ADVANCED_SETTINGS) | AGPL |

## D. Kataloger utan användarsynlig funktion

| Katalog | Varför |
|---|---|
| `core-modules/__mocks__`, `api/__mocks__` | Testdata. |
| `core-modules/cache-lock` | Lås i Redis som hindrar att samma jobb körs dubbelt; märks bara som att dubbelkörningar uteblir. |
| `core-modules/environment` | Tom modul som laddar miljövariabler; själva variablerna i `twenty-config`. |
| `core-modules/redis-client` | Delad Redis-anslutning. |
| `core-modules/sql-sanitization` | Kontroll att värden som byggs in i SQL bara innehåller tillåtna tecken; skydd utan eget beteende. |
| `core-modules/target` | Avgör under uppgradering om kopplingsobjekten för mejl och kalender finns ännu; övergångslogik. |
| `core-modules/key-value-pair` | Lagringstabell; typerna beskrivs i LKS-037. |
| `metadata-modules/data-source` | Äldre koppling arbetsyta till databasschema. |
| `metadata-modules/workspace-feature-flags-map-cache` | Cache av funktionsflaggor; flaggorna i 08. |
| `metadata-modules/flat-*` (utom de som räknas som täckta i A) | Cache- och omvandlingslager för respektive metadata; reglerna användaren möter beskrivs under huvudkatalogen och i validerarna i `workspace-manager/workspace-migration`, som läsarna 01, 02, 03, 04, 08 och 10 har läst. |
| `metadata-modules/pagination` | Generisk markörbaserad sidindelning för metadatalistor; beteendet för integratören står i DM-096 och 07. |
| `metadata-modules/utils` | Hjälpfunktioner; namnreglerna (DM-085, DM-086) är redan beskrivna. |
| `engine/core-entity-cache`, `engine/workspace-cache`, `engine/workspace-cache-storage` | Cacheslager för kärnentiteter och arbetsytans metadata. |
| `engine/dataloaders` | Satsvis inläsning av fält och index i GraphQL; prestanda. |
| `engine/workspace-datasource` | Namn på arbetsytans databasschema och anslutning. |
| `engine/workspace-manager/workspace-version` | Håller reda på arbetsytans version för uppgraderingskedjan. |

## E. Motsägelser och formfel mellan läsarnas filer

| Var | Vad | Bedömning |
|---|---|---|
| API-417 (07) mot AR-973 (08) | 07 säger att undantagslistan för interna värdar tar "värdnamn eller IP", 08 att den "matchas bara på värdnamn". | Båda stämmer delvis: posten normaliseras till värdnamnet (en IP-adress räknas som värdnamn), port och schema ignoreras. Se LKS-028. |
| API-417 (07) och AR-973 (08) | Samma funktion beskrivs två gånger med nästan samma text. | Dubblett, ingen motsägelse. Snajp bör välja ett ID som kanoniskt. |
| AR-721 (08) | Raden förekommer två gånger: först "PÅ som standard", sedan en rättelserad. | Rättelsen bekräftar PÅ. Ingen motsägelse i sak. |
| ID-dubbletter i 01, 02, 03, 05, 06, 08, 09, 10, 11, 12 | Rättelsetabellerna längst ned använder samma ID-format som funktionsraderna (t.ex. DM-005 två gånger, MK-A12 och MK-I42 två gånger i 05). | Formfel, inte motsägelse: en maskinell räkning av rader eller en hänvisning till ett ID träffar två rader. Antalet unika ID i F är det säkra måttet. |
| Numrering i 06, 07, 08, 11 | ID-serierna har stora hopp (AF går till AF-1039 med 291 unika, AR till AR-977 med 346 unika, AI till AI-493 med 271 unika). | Inte fel, men hopp kan misstas för borttagna rader. |
| MK-I42 (05) | Gränsen 3 testmejl per dygn finns bara i dokumentationen, inte i serverkoden (läsaren påpekar det själv). | Handboken och koden säger olika; Snajp får välja. |
| DM-096 (01) mot LKS-017 | DM-096 beskriver bara den fulla metadatalistningen; klientens lätta fråga med hashar fanns inte. | Komplettering, ingen motsägelse. |

## F. Antal funktionsrader

Räknat som tabellrader vars första cell är ett ID (inklusive rättelserader) och som unika ID.

| Fil | Rader med ID | Unika ID |
|---|---|---|
| twenty-01-datamodell-falt-relationer.md | 218 | 210 |
| twenty-02-vyer-filter-sortering-gruppering.md | 211 | 208 |
| twenty-03-postsida-tidslinje-anteckningar-uppgifter.md | 231 | 213 |
| twenty-04-navigering-kommandomeny-sok-favoriter.md | 170 | 166 |
| twenty-05-mejl-kalender-synk-utskick.md | 358 | 347 |
| twenty-06-arbetsfloden-automationer.md | 310 | 291 |
| twenty-07-api-webhooks-appar-mcp.md | 353 | 351 |
| twenty-08-inloggning-arbetsyta-roller-sakerhet.md | 358 | 346 |
| twenty-09-import-export-dubbletter-berikning.md | 212 | 203 |
| twenty-10-dashboards-diagram.md | 202 | 192 |
| twenty-11-ai-agenter-och-fardiga-appar.md | 280 | 271 |
| twenty-12-ui-system-och-anvandarfloden.md | 316 | 304 |
| twenty-13-handboken-som-facit.md | 393 | 393 |
| **Summa 01–13** | **3 612** | **3 495** |
| twenty-99b-luckor-server.md (denna fil) | 55 | 55 |
| **Totalt** | **3 667** | **3 550** |

## Det jag inte hann läsa

- Läsarnas rader i sak: de cirka 3 600 raderna prövades maskinellt mot katalognamn och med riktade sökningar per misstänkt lucka; jag har inte läst varje rad i sin helhet, så motsägelser i detaljer (gränsvärden som skiljer sig mellan filerna) kan finnas kvar utöver dem i E.
- `metadata-modules/overrides/utils`: bara filnamn och de två konstantfilerna; exakt hur flera författares överskuggningar ordnas (LKS-008).
- `metadata-modules/workspace-metadata-version`: bara filnamn; när versionen räknas upp (LKS-018).
- De cirka 300 versionsmärkta uppgraderingskommandona: bara namnen. Några namn tyder på beteendeändringar som läsarna redan har (t.ex. delning av poster, privata poster), men alla har inte kontrollerats.
- Schemalagda jobb (cirka 40 `cron:*`): namnen kontrollerade mot läsarnas text bara stickprovsvis; läsarna beskriver flera i sak (08 räknar nattliga jobb, 05 synkjobben, 06 arbetsflödesjobben) men utan jobbnamn.
- `twenty-config`: masknings- och konverteringsreglerna (hur känsliga värden döljs, hur listor och tal tolkas) och uppdateringsintervallet för databaslagrade värden (08 anger ca 15 s ur dokumentationen).
- `engine/api/graphql/workspace-schema-builder` och `twenty-orm` på detaljnivå (07 och 01 har läst dem på regelnivå).

## Oklarheter

- Översättningarnas ytor: i vilken inställningsvy administratören ser ursprungsmärkningen (WORKSPACE, SHIPPED, INHERITED), och om en medlevererad översättning går att återställa efter att arbetsytan skrivit över den. Avgörs i den körande appen.
- Om en överskuggning av en standardvy (t.ex. dess filter i fritext eller gruppering) syns för alla medlemmar eller bara i arbetsytans egen kopia; koden lagrar den per arbetsyta, men hur det samspelar med privata vyer syns först i appen.
- Hur introduktionsbelöningarna (LKS-012) omräknas till visade krediter; omräkningsfaktorn ligger i en delad hjälpfunktion som inte lästes.
- Om underhållsbanderollen visas för alla arbetsytor på instansen samtidigt (lagringen är global, avfärdandet per arbetsyta).
- Om den publika hälsokontrollen (LKS-027) någonsin svarar annat än OK när databasen är nere; den anropar inga indikatorer.
- Vilka åtgärder utöver minimal metadata och fakturering som är tillåtna för en avstängd arbetsyta (LKS-020); markeringen sitter per resolver.
