# Twenty-förlagan 99a: luckgranskning av fronten (ID-prefix LKF)

Granskad mot förlagan `D:\snajp-crm-forlaga\twenty` (commit 1da6d55) och de tretton
inventeringsfilerna `twenty-01` till `twenty-13` i samma katalog som den här filen.
Allt nedan är en funktionsbeskrivning med egna ord. Ingen kod, inga typdefinitioner och
inga längre textstycken ur förlagan är kopierade; publika namn (behörighetsflaggor,
händelsenamn, filteroperander) nämns där en integratör behöver dem.

## Översikt

Uppdraget var att pricka av varje katalog under `packages/twenty-front/src/modules`
(alla, med underkatalogerna ett steg ner i `object-record`, `settings`, `ui`, `workflow`
och `activities`) och varje katalog under `packages/twenty-front/src/pages`, inklusive
varje undersida under `pages/settings`, mot funktionsraderna i de tretton filerna.

**Metod.** Alla tabellrader med ID i de tretton filerna (3 666 rader inklusive
rättelse- och uppräkningsrader) lästes maskinellt, och ursprungskolumnen matchades mot
varje katalognamn (även förkortade sökvägar som `OR/`, `front/`, `SI/`). Kataloger med
noll eller enstaka träffar öppnades och lästes: deras användartexter, konstanter, krokar
och komponenter. Sidorna under `pages/` matchades dessutom på filnamn. Varje filers
avsnitt "Det jag inte hann läsa" lästes i sin helhet, och misstänkta luckor kontrollerades
med nyckelordssökning över alla rader (till exempel loggkonsol, kontogrupp, mediaåtkomst,
relaterade poststigar, inställningsmeny, DDL, gränser).

**Resultat i korthet.** Fronten är väl täckt: 154 av 187 modulkataloger har minst en
funktionsrad med rätt ursprung, och alla 29 sidkataloger är täckta på funktionsnivå.
Elva verkliga luckor hittades. Den största är **loggkonsolen** (`modules/log-console`,
87 filer), som i läsarnas filer bara nämns som ett lager i z-ordningen och ett
kortkommando, trots att den är en egen yta med sex loggkällor, filter, tidsintervall,
detaljpanel och planspärr. Övriga luckor gäller mediaåtkomst för inbäddade ytor,
gränssnittet för relaterade poststigar, kontogrupper i appinställningarna, hur
inställningsmenyn grindas av behörighetsflaggor, klientkonfigurationens funktionsspärrar
(bland annat låst datamodell), gränssidans regler, användningssidans perioder,
arbetsflödessidorna i objektkärnan, serveradminpanelens AI-leverantörsformulär och
detaljsidorna per innehållstyp för installerade appar. Alla luckor är fyllda med
LKF-rader i avsnitt C.

### Begrepp och förslag på svensk term

| Förlagans term | Svensk term | Kort |
|---|---|---|
| log console | loggkonsol | Nedfällbar loggyta längst ned i appen (Ctrl/Cmd+J) |
| log source | loggkälla | En av loggkonsolens sex flikar (poständringar, säkerhet, applogg, webhooks, sidvisningar, användning) |
| retention | lagringstid | Hur länge loggar sparas; styr vilka tidsintervall som går att välja |
| media access session | mediaåtkomst (session) | En inbäddad yta som begär, använder eller fått delegerad mikrofon/kamera |
| related record path | relaterad poststig | Kedja av relationer längs vilken postbehörighet sprids |
| account group | kontogrupp | Ett anslutet konto som delas mellan flera appar |
| app preferences | appinställningar (personliga) | Medlemmens egna inställningar för installerade appar och konton |
| client config | klientkonfiguration | Instansens inställningar som fronten läser vid start och som slår av och på funktioner |
| DDL lock | låst datamodell | Instansläge där schemat inte får ändras |
| usage limit | användningsgräns (utgiftstak) | Tak för vad arbetsytan eller en förbrukare får spendera |
| core workflow | arbetsflöde (kärnlistan) | Arbetsflödeslistan och arbetsflödessidan som ligger i objektkärnan |

## A. Avprickning

En rad per katalog. Status: **täckt** (minst en funktionsrad med rätt ursprung), **täckt indirekt** (beteendet beskrivet under en annan katalogs ursprung), **täckt + lucka** / **LUCKA** (luckan fylld i avsnitt C), **D** (ingen användarsynlig funktion, se avsnitt D), **delvis**. Kolumnen "Täckt av" anger fil (t01 = twenty-01 osv.), ID och antal rader vars ursprung nämner katalogen. För `modules/types`, `app`, `auth`, `ai` och `workspace` är namnträffen brusig eftersom samma katalognamn finns på servern; de är kontrollerade för hand och täckta.

### A1. packages/twenty-front/src/modules

| Katalog | Status | Täckt av |
|---|---|---|
| modules/accounts | täckt | t05 MK-E17, MK-L01, MK-L02, MK-L11, MK-L13, MK-L14 (6 rader) |
| modules/activities/calendar | täckt | t03 PS-160, PS-161 (3 rader); t05 MK-F21, MK-M08, MK-M14, MK-M15, MK-M16 (5 rader) |
| modules/activities/components | täckt | t03 PS-137, PS-138 (2 rader) |
| modules/activities/emails | täckt | t03 PS-158, PS-159 (2 rader); t05 MK-F19, MK-F20, MK-F21, MK-F22, MK-F23, MK-I52 … (10 rader) |
| modules/activities/files | täckt | t03 PS-147, PS-151 (2 rader) |
| modules/activities/graphql | D | – |
| modules/activities/hooks | täckt | t03 PS-022, PS-132 (2 rader); t04 NAV-154 (1 rader) |
| modules/activities/notes | täckt | t03 PS-130, PS-136 (2 rader) |
| modules/activities/states | D | – |
| modules/activities/tasks | täckt | t03 PS-133, PS-134 (3 rader) |
| modules/activities/timeline-activities | täckt | t03 PS-118, PS-119, PS-121, PS-127 (4 rader) |
| modules/activities/types | D | – |
| modules/activities/utils | täckt indirekt | bilagornas sökvägar; beteendet i t03 PS-147–PS-151 |
| modules/advanced-text-editor | täckt | t03 PS-139, PS-144, PS-153 (3 rader) |
| modules/ai | täckt | (tokenträffen är brusig, avser delvis serverns katalog) t04 NAV-048, NAV-101 (2 rader); t06 AF-1014 (1 rader); t07 API-140, API-141, API-142, API-145, API-160, API-214 (6 rader); t11 AI-001, AI-002, AI-003, AI-004, AI-008, AI-020 … (52 rader); t12 UX-297 (1 rader); t13 HB-034, HB-035, HB-239, HB-240, HB-241, HB-242 … (9 rader) |
| modules/ai-chat | täckt | t11 AI-080, AI-082, AI-085, AI-088, AI-089, AI-107 … (24 rader) |
| modules/analytics | delvis | t10 DB-149; sidvisningsloggen LKF-006; t10 DB-149 (1 rader) |
| modules/apollo | D | felmeddelande vid misslyckad fråga täcks av t12 UX-098ff |
| modules/app | täckt | (tokenträffen är brusig, avser delvis serverns katalog) t04 NAV-121, NAV-122, NAV-126, NAV-159 (5 rader); t07 API-170, API-173, API-175, API-177, API-179, API-180 … (28 rader); t12 UX-152, UX-232, UX-233, UX-244, UX-245, UX-247 … (9 rader) |
| modules/applications | täckt | t07 API-266, API-267, API-268, API-269, API-270, API-427 (6 rader) |
| modules/auth | täckt | (tokenträffen är brusig, avser delvis serverns katalog) t05 MK-A01, MK-A02, MK-A03, MK-A04, MK-A05, MK-A11 … (9 rader); t07 API-081 (1 rader); t08 AR-200, AR-201, AR-202, AR-203, AR-204, AR-205 … (54 rader) |
| modules/browser-event | D | – |
| modules/captcha | täckt | t08 AR-260, AR-261 (2 rader) |
| modules/chat | täckt | t03 PS-189 (1 rader); t11 AI-207, AI-317, AI-480, AI-481, AI-482, AI-483 … (7 rader) |
| modules/client-config | LUCKA | LKF-020–LKF-022 |
| modules/command-menu | täckt | t04 NAV-052, NAV-053, NAV-054, NAV-055, NAV-060, NAV-061 … (8 rader); t12 UX-163, UX-266 (2 rader) |
| modules/command-menu-item | täckt | t03 PS-162, PS-163, PS-164 (4 rader); t04 NAV-026, NAV-027, NAV-028, NAV-029, NAV-030, NAV-031 … (21 rader); t09 IE-042, IE-089, IE-109, IE-111, IE-133 (7 rader); t10 DB-112, DB-113 (2 rader); t11 AI-490 (1 rader) |
| modules/companies | D | – |
| modules/context-store | täckt | t04 NAV-078, NAV-079 (2 rader) |
| modules/dashboards | täckt | t10 DB-001, DB-002, DB-003, DB-004, DB-005, DB-009 … (8 rader); t12 UX-300 (1 rader); t13 HB-033, HB-287, HB-289, HB-290, HB-291, HB-292 … (8 rader) |
| modules/domain-manager | täckt | t08 AR-907 (1 rader) |
| modules/dropdown-context-state-management | D | – |
| modules/error-handler | täckt | t04 NAV-128, NAV-129, NAV-130 (3 rader) |
| modules/file | täckt | t03 PS-143, PS-152, PS-153, PS-154, PS-155, PS-164 … (10 rader); t09 IE-107, IE-176 (2 rader) |
| modules/file-upload | täckt | t03 PS-152, PS-153, PS-193, PS-194 (4 rader) |
| modules/front-components | täckt | t07 API-209, API-210, API-211, API-212, API-213, API-215 … (20 rader); t10 DB-180 (1 rader); t11 AI-302, AI-304, AI-309 (3 rader) |
| modules/geo-map | täckt | t02 VY-170 (1 rader) |
| modules/getting-started | täckt | t04 NAV-042, NAV-045, NAV-046, NAV-119, NAV-120, NAV-123 … (7 rader); t07 API-170, API-240, API-244, API-250, API-395, API-396 … (7 rader); t09 IE-160 (1 rader); t12 UX-162, UX-163, UX-164, UX-165, UX-166, UX-167 … (22 rader); t13 HB-001, HB-002, HB-003, HB-004, HB-014, HB-025 … (17 rader) |
| modules/inbox | täckt | t04 NAV-100, NAV-101, NAV-102, NAV-103, NAV-104, NAV-105 … (9 rader); t07 API-242, API-328, API-329 (3 rader); t12 UX-266 (1 rader) |
| modules/information-banner | täckt | t03 PS-163 (1 rader); t04 NAV-108, NAV-166 (3 rader) |
| modules/keyboard-shortcut-menu | täckt | t04 NAV-055, NAV-069, NAV-080, NAV-081 (4 rader); t12 UX-265 (1 rader) |
| modules/layout-customization | täckt | t03 PS-051, PS-052 (2 rader) |
| modules/legacy-ai-chat | täckt | t11 AI-200; omdirigeringen LKF-032; t11 AI-200 (1 rader) |
| modules/localization | täckt | t08 AR-810, AR-975, AR-976 (3 rader); t12 UX-260 (1 rader) |
| modules/log-console | LUCKA | bara nämnd i t12 UX-091, UX-266; fylld i LKF-001–LKF-011; t12 UX-266 (1 rader) |
| modules/logic-functions | täckt | t06 AF-801, AF-802, AF-803, AF-804, AF-805, AF-806 … (25 rader); t07 API-179, API-183, API-189, API-200, API-201, API-202 … (12 rader); t11 AI-300, AI-303, AI-304, AI-306, AI-307, AI-308 … (27 rader) |
| modules/marketplace | täckt | t07 API-269, API-362 (2 rader); t09 IE-116 (1 rader) |
| modules/mcp-servers | täckt | t07 API-271, API-361 (2 rader); t11 AI-190, AI-312 (2 rader) |
| modules/media-access | LUCKA | LKF-012–LKF-016 |
| modules/mention | täckt | t03 PS-145 (1 rader); t11 AI-491 (1 rader) |
| modules/metadata-error-handler | D | – |
| modules/metadata-store | D | omladdning av metadata vid ändring täcks av t07 API-272 |
| modules/navigation | täckt | t04 NAV-082, NAV-083, NAV-084, NAV-088, NAV-094, NAV-096 … (14 rader); t12 UX-051, UX-052, UX-053, UX-063, UX-064, UX-065 … (20 rader); t13 HB-253, HB-254, HB-255, HB-256, HB-257, HB-258 … (8 rader) |
| modules/navigation-menu-item | täckt | t04 NAV-012, NAV-013, NAV-015, NAV-016, NAV-019, NAV-020 … (22 rader); t11 AI-408 (1 rader) |
| modules/object-core | täckt + lucka | t11 AI-430–AI-435, t03 PS-002; arbetsflödessidorna LKF-031; t03 PS-002 (1 rader); t11 AI-430, AI-431, AI-432, AI-434, AI-435 (5 rader) |
| modules/object-metadata | täckt | t01 DM-050, DM-074, DM-080, DM-081, DM-082, DM-083 … (30 rader); t02 VY-095, VY-101, VY-177, VY-179 (4 rader); t03 PS-110, PS-202 (2 rader); t07 API-040 (1 rader); t09 IE-127, IE-128, IE-129, IE-152 (4 rader); t11 AI-405 (1 rader) |
| modules/object-record/advanced-filter | täckt | t02 VY-089, VY-090, VY-091, VY-092, VY-093 (5 rader) |
| modules/object-record/cache | täckt | t12 UX-161 (1 rader) |
| modules/object-record/components | D | postchip täcks av t02/t03 |
| modules/object-record/constants | täckt | t03 PS-162 (1 rader) |
| modules/object-record/graphql | D | – |
| modules/object-record/hooks | täckt | t09 IE-084, IE-086, IE-132, IE-146 (4 rader) |
| modules/object-record/multiple-objects | täckt | t03 PS-210 (1 rader) |
| modules/object-record/object-filter-dropdown | täckt | t02 VY-085, VY-086, VY-087, VY-088 (4 rader) |
| modules/object-record/object-options-dropdown | täckt | t02 VY-103, VY-104, VY-105, VY-106, VY-107, VY-108 … (16 rader); t09 IE-098 (1 rader) |
| modules/object-record/object-sort-dropdown | täckt | t02 VY-096, VY-097, VY-098, VY-099 (4 rader) |
| modules/object-record/read-only | täckt | t02 VY-204, VY-205 (2 rader); t03 PS-066, PS-163 (2 rader) |
| modules/object-record/record-aggregate | täckt | t02 VY-142 (1 rader) |
| modules/object-record/record-board | täckt | t02 VY-140, VY-142, VY-145, VY-146, VY-147, VY-148 … (13 rader); t12 UX-266 (1 rader) |
| modules/object-record/record-board-widget | täckt | t02 VY-185 (1 rader); t03 PS-207 (1 rader) |
| modules/object-record/record-calendar | täckt | t02 VY-070, VY-161, VY-162, VY-163, VY-164, VY-165 … (9 rader); t10 DB-123, DB-182 (2 rader) |
| modules/object-record/record-calendar-widget | täckt | t02 VY-186 (1 rader); t03 PS-207 (1 rader) |
| modules/object-record/record-card | täckt indirekt | läst av t03:s andra kontrolläsare, beteendet i t02 VY-140–VY-155 (kanbankort) |
| modules/object-record/record-column-lookup | täckt | t02 VY-189, VY-190, VY-191 (3 rader) |
| modules/object-record/record-column-scope | täckt | t02 VY-188, VY-192, VY-193, VY-194, VY-195 (5 rader) |
| modules/object-record/record-column-summary | täckt | t02 VY-143 (1 rader) |
| modules/object-record/record-drag | täckt | t02 VY-131, VY-145, VY-166 (3 rader) |
| modules/object-record/record-field | täckt | t02 VY-135 (1 rader); t03 PS-061, PS-063, PS-064, PS-065, PS-067, PS-084 (6 rader) |
| modules/object-record/record-field-list | täckt | t03 PS-097, PS-098 (2 rader) |
| modules/object-record/record-filter | täckt | t02 VY-084, VY-085, VY-089, VY-094, VY-173, VY-174 … (8 rader) |
| modules/object-record/record-filter-group | täckt | t02 VY-200, VY-201 (2 rader) |
| modules/object-record/record-form | täckt | t03 PS-179, PS-180, PS-181, PS-183 (4 rader) |
| modules/object-record/record-group | täckt | t02 VY-069, VY-108, VY-136, VY-144, VY-147, VY-152 … (12 rader) |
| modules/object-record/record-index | täckt | t02 VY-114, VY-115, VY-120, VY-129, VY-131, VY-134 … (11 rader) |
| modules/object-record/record-inline-cell | täckt | t03 PS-061, PS-062, PS-063 (3 rader) |
| modules/object-record/record-list | täckt | t02 VY-169 (1 rader) |
| modules/object-record/record-list-widget | täckt | t02 VY-187 (1 rader); t03 PS-207 (1 rader) |
| modules/object-record/record-merge | täckt | t03 PS-104, PS-105, PS-106 (3 rader) |
| modules/object-record/record-picker | täckt | t02 VY-171, VY-172 (2 rader); t03 PS-101, PS-102 (3 rader); t04 NAV-156 (1 rader) |
| modules/object-record/record-seeded-draft | täckt | t03 PS-185 (1 rader) |
| modules/object-record/record-selection | täckt | t02 VY-128, VY-129, VY-130 (3 rader) |
| modules/object-record/record-sharing | täckt | t03 PS-112 (1 rader) |
| modules/object-record/record-show | täckt | t03 PS-001, PS-003, PS-004, PS-005, PS-007, PS-008 … (9 rader); t09 IE-111 (1 rader) |
| modules/object-record/record-sort | täckt | t02 VY-096–VY-099 (sorteringsmenyn), VY-020ff (datamodell) |
| modules/object-record/record-store | täckt | t03 PS-209 (1 rader) |
| modules/object-record/record-table | täckt | t02 VY-094, VY-102, VY-116, VY-117, VY-118, VY-119 … (26 rader); t03 PS-043, PS-174 (2 rader); t10 DB-017, DB-123, DB-135, DB-159, DB-167, DB-182 … (9 rader); t12 UX-266, UX-284 (2 rader) |
| modules/object-record/record-table-widget | täckt | t02 VY-181, VY-182, VY-183, VY-184 (4 rader); t03 PS-204, PS-205, PS-206 (3 rader) |
| modules/object-record/record-title-cell | täckt | t03 PS-058, PS-059, PS-060 (3 rader) |
| modules/object-record/record-update-multiple | täckt | t03 U-11, PS-184 (2 rader) |
| modules/object-record/select | täckt | t03 PS-208 (1 rader) |
| modules/object-record/spreadsheet-import | täckt | t09 IE-134ff |
| modules/object-record/states | D | – |
| modules/object-record/types | D | – |
| modules/object-record/utils | D | summeringar och positioner beskrivs i t02 VY-142, VY-131 |
| modules/onboarding | täckt | t04 NAV-036, NAV-037, NAV-038, NAV-039, NAV-040, NAV-110 … (15 rader); t09 IE-153, IE-161 (2 rader); t12 UX-176 (1 rader) |
| modules/page-layout | täckt | t03 PS-015, PS-026, PS-027, PS-028, PS-029, PS-030 … (37 rader); t07 API-043 (1 rader); t10 DB-005, DB-010, DB-011, DB-012, DB-016, DB-018 … (63 rader); t11 AI-404 (1 rader); t12 UX-294 (1 rader) |
| modules/people | D | – |
| modules/queue-job | täckt | t09 IE-112, IE-113, IE-114, IE-115 (4 rader) |
| modules/record-export | täckt | t09 IE-099, IE-101, IE-102, IE-103, IE-104, IE-105 … (11 rader) |
| modules/related-record-paths | LUCKA (gränssnittet) | servern i t01 DM-173, t08 AR-942; gränssnittet LKF-017–LKF-019 |
| modules/salesfarce | täckt | t12 UX-246; detaljer LKF-033 |
| modules/settings/accounts | täckt | t05 MK-E17, MK-L01, MK-L02, MK-L11, MK-L13 (5 rader) |
| modules/settings/admin-panel | täckt | t08 AR-817, AR-968 (2 rader); t09 IE-117, IE-123, IE-124, IE-190 (4 rader) |
| modules/settings/ai | täckt | t11 AI-180, AI-181, AI-182, AI-183, AI-185, AI-187 … (7 rader) |
| modules/settings/app-preferences | LUCKA (delvis) | t05 MK-L13, t07 API-351; kontogrupper och appinställningsflikar LKF-023–LKF-026 |
| modules/settings/application-monitoring | täckt | t07 API-353 (1 rader) |
| modules/settings/application-registrations | täckt | t07 API-267, API-353, t08 AR-716 |
| modules/settings/applications | täckt | t07 API-266, API-267, API-268, API-269 (4 rader) |
| modules/settings/billing | täckt + lucka | t08 AR-600–AR-625, AR-813; gränssidans regler LKF-029; t08 AR-813, AR-961, AR-962, AR-963 (4 rader); t10 DB-115 (1 rader) |
| modules/settings/components | täckt | t06 AF-713 (1 rader) |
| modules/settings/config-variables | täckt | t05 MK-A29, MK-C28, MK-I44, MK-K01, MK-K13, MK-O35 (6 rader); t06 AF-604, AF-609, AF-617, AF-817, AF-822, AF-913 (6 rader); t07 API-032, API-100, API-110, API-114, API-208 (5 rader); t08 AR-211, AR-214, AR-228, AR-310, AR-721, AR-927 … (8 rader) |
| modules/settings/constants | D | – |
| modules/settings/data-model | täckt | t01 DM-008, DM-200, DM-201, DM-202, DM-203, DM-204 … (16 rader); t03 PS-069, PS-084 (2 rader); t09 IE-201, IE-203 (2 rader) |
| modules/settings/developers | täckt | t07 API-260, API-261, API-262, API-263, API-264, API-265 … (8 rader) |
| modules/settings/domains | täckt | t08 AR-063, AR-933 (3 rader) |
| modules/settings/emailing-domains | täckt + lucka | t05 MK-H13, MK-H14, MK-L11; AI-hjälpen LKF-027 |
| modules/settings/enterprise | täckt | t08 AR-814 (1 rader) |
| modules/settings/event-logs | täckt | t08 AR-630, AR-631, AR-632, AR-633, AR-818, AR-902 … (7 rader) |
| modules/settings/experience | täckt | t08 AR-810 (1 rader) |
| modules/settings/hooks | LUCKA | inställningsmenyns grindning LKF-028 |
| modules/settings/lab | täckt | t08 AR-815 (1 rader) |
| modules/settings/layout | täckt | t08 AR-923 (1 rader) |
| modules/settings/legal | täckt | t08 AR-816 (1 rader) |
| modules/settings/logic-functions | täckt | t06 AF-801, AF-802, AF-803, AF-820 (4 rader) |
| modules/settings/mcp | täckt | t07 API-360 (1 rader); t11 AI-189 (1 rader) |
| modules/settings/mcp-servers | täckt | t07 API-361 (1 rader); t11 AI-190 (1 rader) |
| modules/settings/members | täckt | t08 AR-805, AR-806, AR-807 (3 rader) |
| modules/settings/privacy | täckt | t08 AR-811 (1 rader) |
| modules/settings/profile | täckt | t08 AR-808, AR-809 (2 rader) |
| modules/settings/roles | täckt | t08 AR-001–AR-0xx, AR-807, AR-911–AR-918; t08 AR-807 (1 rader) |
| modules/settings/security | täckt | t08 AR-812, AR-931, AR-932 (3 rader) |
| modules/settings/translations | täckt | t01 DM-211 |
| modules/settings/two-factor-authentication | täckt | t08 AR-240, AR-241, AR-242, AR-243, AR-244, AR-245 … (11 rader) |
| modules/settings/types | D | – |
| modules/settings/unsubscribe-topics | täckt | t05 MK-L12, MK-I-avsnittet |
| modules/settings/unsubscribers | täckt | t05 MK-L12 |
| modules/settings/usage | täckt + lucka | t08 AR-621, t11 AI-188; perioder och operationstyper LKF-030; t08 AR-813, AR-963 (2 rader) |
| modules/settings/utils | D | – |
| modules/settings/workspace | täckt | t05 MK-L10 (1 rader); t08 AR-811 (1 rader) |
| modules/settings/workspace-member | täckt | t01 DM-058 (1 rader); t08 AR-908, AR-909 (2 rader) |
| modules/side-panel | täckt | t03 PS-016, PS-103, PS-159, PS-179, PS-182, PS-183 (7 rader); t04 NAV-052, NAV-058, NAV-060, NAV-154 (4 rader); t06 AF-702, AF-707, AF-713, AF-718, AF-729 (5 rader); t09 IE-116, IE-134, IE-135 (3 rader); t10 DB-121, DB-123, DB-124, DB-125, DB-126, DB-127 … (16 rader); t12 UX-106, UX-266, UX-284 (3 rader) |
| modules/sign-in-background-mock | D | – |
| modules/skill-suggestion | täckt | t11 AI-202, AI-491 (2 rader) |
| modules/spreadsheet-import | täckt | t09 IE-134–IE-190 (förkortat SI/) |
| modules/sse-db-event | täckt | t07 API-272 (1 rader); t09 IE-112 (1 rader) |
| modules/support | täckt | t04 NAV-109 (1 rader); t12 UX-250 (1 rader) |
| modules/tab-presence | täckt | t04 NAV-050, NAV-107 (2 rader) |
| modules/types | täckt | (tokenträffen är brusig, avser delvis serverns katalog) t01 DM-001, DM-002, DM-003, DM-004, DM-005, DM-006 … (40 rader); t02 VY-012, VY-014, VY-022, VY-023, VY-031, VY-035 … (15 rader); t03 PS-026, PS-028, PS-069, PS-092, PS-111, PS-152 … (11 rader); t04 NAV-013, NAV-014, NAV-028, NAV-037, NAV-041, NAV-049 … (10 rader); t05 MK-A12, MK-A27, MK-B01, MK-C29, MK-H13, MK-I27 … (16 rader); t06 AF-202, AF-252, AF-404, AF-503, AF-805, AF-1002 … (10 rader); t07 API-316 (1 rader); t08 AR-231, AR-305, AR-330, AR-334, AR-421, AR-425 … (10 rader); t09 IE-043, IE-088, IE-113, IE-179 (4 rader); t10 DB-005, DB-010, DB-011, DB-012, DB-016, DB-017 … (12 rader); t11 AI-034, AI-037, AI-038, AI-041, AI-044, AI-045 … (12 rader); t12 UX-035, UX-113, UX-147, UX-151, UX-264, UX-294 (6 rader) |
| modules/ui/feedback | täckt | t12 UX-098, UX-121, UX-122, UX-123, UX-124, UX-125 … (8 rader) |
| modules/ui/field | täckt | t03 PS-068, PS-070, PS-073, PS-081, PS-092, PS-150 (6 rader); t12 UX-127, UX-128, UX-129, UX-130, UX-131, UX-132 … (31 rader) |
| modules/ui/icon | täckt | t12 UX-160 (1 rader) |
| modules/ui/input | täckt | t12 UX-123, UX-139, UX-143, UX-144, UX-145, UX-146 … (21 rader) |
| modules/ui/layout | täckt | t04 NAV-133 (1 rader); t12 UX-090, UX-091, UX-092, UX-093, UX-094, UX-095 … (24 rader) |
| modules/ui/navigation | täckt | t04 NAV-123, NAV-124, NAV-125, NAV-134 (4 rader); t12 UX-111, UX-112, UX-113, UX-114, UX-115, UX-116 … (10 rader) |
| modules/ui/suggestion | täckt | t12 UX-150 (1 rader) |
| modules/ui/theme | täckt | t12 UX-001, UX-002, UX-011, UX-246 (4 rader) |
| modules/ui/types | D | – |
| modules/ui/utilities | täckt | t04 NAV-081, NAV-122, NAV-159 (3 rader); t12 UX-151, UX-152, UX-153, UX-154, UX-155, UX-156 … (12 rader) |
| modules/users | D | kontoradering täcks av t08 AR-808 |
| modules/validation-rules | täckt | t01 DM-029, DM-115, DM-155, DM-157, DM-158, DM-212 (6 rader); t07 API-307, API-308 (2 rader); t11 AI-490 (1 rader); t13 HB-077, HB-078, HB-079, HB-080, HB-081, HB-082 … (9 rader) |
| modules/views | täckt | t02 VY-038, VY-065, VY-066, VY-067, VY-068, VY-071 … (27 rader); t07 API-314, API-315, API-316 (3 rader); t11 AI-315 (1 rader) |
| modules/web-push | täckt | t04 NAV-047, NAV-048, NAV-049, NAV-105, NAV-106, NAV-162 (6 rader) |
| modules/workflow/components | täckt | t04 NAV-135, NAV-136, NAV-137, NAV-138, NAV-139, NAV-140 … (8 rader); t06 AF-727 (1 rader) |
| modules/workflow/constants | täckt | t06 AF-002, AF-113, AF-230, AF-301, AF-608, AF-725 … (10 rader); t09 IE-174 (1 rader); t11 AI-361 (1 rader) |
| modules/workflow/graphql | täckt | t06 AF-5xx (stoppa, försök om, formulärsteg) |
| modules/workflow/hooks | täckt | t06 AF-026, AF-728, AF-730 (3 rader) |
| modules/workflow/states | D | – |
| modules/workflow/types | täckt | t06 AF-503, AF-1006, AF-1009 (3 rader) |
| modules/workflow/utils | täckt | t06 AF-020, AF-022 (2 rader) |
| modules/workflow/workflow-diagram | täckt | t06 AF-701, AF-708, AF-709, AF-711, AF-717, AF-729 (7 rader) |
| modules/workflow/workflow-steps | täckt | t06 AF-707, AF-712, AF-714, AF-717, AF-718, AF-720 … (13 rader) |
| modules/workflow/workflow-trigger | täckt | t06 AF-011, AF-118, AF-120, AF-121, AF-122, AF-125 … (19 rader) |
| modules/workflow/workflow-variables | täckt | t06 AF-719 (1 rader) |
| modules/workflow/workflow-version | täckt | t06 AF-010, AF-724, AF-1007 (3 rader) |
| modules/workspace | täckt | (tokenträffen är brusig, avser delvis serverns katalog) t01 DM-184 (1 rader); t05 MK-L10 (1 rader); t08 AR-330, AR-331, AR-332, AR-333, AR-334, AR-335 … (16 rader); t10 DB-166 (1 rader) |
| modules/workspace-invitation | täckt | t08 AR-347, AR-348, AR-349, AR-350 (4 rader) |
| modules/workspace-member | täckt | t01 DM-058 (1 rader); t08 AR-908, AR-909 (2 rader) |

### A2. packages/twenty-front/src/pages

| Katalog | Status | Täckt av |
|---|---|---|
| pages/auth | täckt | t08 AR-800–AR-805, AR-924 (SignInUp = stegmaskinen AR-800); t08 AR-804, AR-924 (2 rader) |
| pages/getting-started | täckt | t04 NAV-119 (1 rader) |
| pages/inbox | täckt | t04 NAV-100 (1 rader) |
| pages/legacy-ai-chat | täckt + lucka | t11 AI-200; LKF-032 |
| pages/mobile-home | täckt | t04 NAV-132 (1 rader) |
| pages/not-found | täckt | t04 NAV-127 (1 rader) |
| pages/object-core | täckt + lucka | t11 AI-430, AI-431; t06 AF-009–AF-025; LKF-031; t11 AI-430, AI-431 (2 rader) |
| pages/object-record | täckt | t03 PS-001ff (postsida), t02 VY-001ff (listsidan RecordIndexPage); t03 PS-001 (1 rader) |
| pages/onboarding | täckt | t04 NAV-110–NAV-116; Verify = inloggningstoken t08 AR-804; t04 NAV-110, NAV-111, NAV-112, NAV-113, NAV-114, NAV-115 … (7 rader) |
| pages/page-layout | täckt | t03 U-19, PS-015 (2 rader); t10 DB-121, DB-123, DB-124, DB-125, DB-126, DB-127 … (16 rader) |
| pages/settings/__stories__ | D | stories |
| pages/settings/accounts | täckt + lucka | t05 MK-L01–MK-L13; appinställningar LKF-023–LKF-026; t05 MK-L01, MK-L04, MK-L08, MK-L11, MK-L13 (5 rader) |
| pages/settings/admin-panel | täckt (serversidan) + lucka | t08 AR-704–AR-717, AR-817, AR-968; gränssnittets detaljer LKF-034; t08 AR-817 (1 rader) |
| pages/settings/ai | täckt | t11 AI-180–AI-191; t11 AI-180, AI-181, AI-182, AI-183, AI-184, AI-185 … (12 rader) |
| pages/settings/applications | täckt + lucka | t07 API-266–API-269, API-362; detaljsidor per innehållstyp LKF-035; t07 API-266, API-267, API-268, API-269 (4 rader) |
| pages/settings/billing | täckt + lucka | t08 AR-813, AR-600–AR-625; LKF-029, LKF-030; t08 AR-813 (1 rader) |
| pages/settings/communications | täckt | t05 MK-L09–MK-L12; t05 MK-L10, MK-L11, MK-L12 (3 rader) |
| pages/settings/community | täckt | t08 AR-815; t08 AR-815 (1 rader) |
| pages/settings/data-model | täckt | t01 DM-200–DM-212, DM-268; t01 DM-200, DM-201, DM-202, DM-203, DM-205, DM-208 … (11 rader) |
| pages/settings/developers | täckt | t07 API-260–API-266 (webhooks API-263, playground API-264); t07 API-260, API-261, API-262, API-264, API-265, API-266 … (7 rader) |
| pages/settings/domains | täckt | t08 AR-063, AR-933; t08 AR-063, AR-933 (3 rader) |
| pages/settings/enterprise | täckt | t08 AR-814; t08 AR-814 (1 rader) |
| pages/settings/general | täckt | t08 AR-811; t08 AR-811 (1 rader) |
| pages/settings/layout | täckt | t08 AR-923 (behörighetsflaggan avgjord i LKF-028); t08 AR-923 (1 rader) |
| pages/settings/legal | täckt | t08 AR-816; t08 AR-816 (1 rader) |
| pages/settings/logic-functions | täckt | t06 AF-801; t06 AF-801 (1 rader) |
| pages/settings/members | täckt | t08 AR-805–AR-807, AR-001ff; t08 AR-805, AR-806, AR-807 (3 rader) |
| pages/settings/profile | täckt | t08 AR-808–AR-810, t12 UX-001–UX-002; t08 AR-808 (1 rader) |
| pages/settings/security | täckt | t08 AR-812, AR-931, AR-932; t08 AR-812, AR-932 (2 rader) |

## B. Luckor

| Område | Vad som saknas | Var i förlagan | Hur allvarligt |
|---|---|---|---|
| Loggkonsolen | Hela ytan: sex loggkällor, filter, tidsintervall inom lagringstid, detaljpanel, livläge, kopiering, storlek och helskärm, planspärr. Läsarna nämner den bara som z-lager (UX-091) och kortkommando (UX-266); AR-818 beskriver en äldre händelseloggsvy. | `twenty-front/src/modules/log-console` | hög |
| Mediaåtkomst för inbäddade ytor | Indikatorn i appen, statusarna väntar/spelar in/delegerad, aktivering per ägare och avstängning, begränsning mot arbetsytans tillåtna ursprung. API-363/API-393 och AR-901 täcker frontkomponentens regler och inställningen, inte gränssnittet. | `modules/media-access` | medel |
| Relaterade poststigar i gränssnittet | Var stigarna redigeras, högsta antal steg i väljaren, planspärren RLS, tomlägen. Servern täcks av DM-173 och AR-942. | `modules/related-record-paths` | medel |
| Klientkonfigurationens spärrar | Att låst datamodell gör datamodellsidorna skrivskyddade, och vilka funktioner som slås av och på av instansens inställningar. | `modules/client-config`, `modules/settings/data-model/object-details` | medel |
| Appinställningar och kontogrupper | Konton som delas mellan appar, flikarna Apps och Accounts, inbyggda kontoappar med behörighetslista, massborttagning av anslutningar med delresultat, omdirigering från de gamla kontoadresserna. | `modules/settings/app-preferences`, `pages/settings/accounts/SettingsAppPreferences*` | medel |
| Inställningsmenyns grindning | Vilken behörighetsflagga eller villkor som döljer varje menypost. UX-208 bygger på en äldre e2e-sida och stämmer inte med dagens meny. | `modules/settings/hooks/useSettingsNavigationItems.tsx` | medel |
| Avsändardomän: DNS med AI | Knappen som kopierar en färdig uppmaning för att låta ett AI-verktyg lägga in DNS-posterna. | `modules/settings/emailing-domains` | låg |
| Gränssidan (utgiftstak) | Mallar att börja från, Organization-krav för gränser på medlemmar, API-nycklar och appar, avaktiverat läge, sök och filter. Servern täcks av AR-622–AR-625 och API-113–API-116. | `modules/settings/billing` (limits), `pages/settings/billing/SettingsBillingLimit*`, `SettingsBillingNewLimit.tsx` | låg |
| Användningssidan | Perioderna 7/30/90 dagar, uppdelning per typ, app och användare, de 16 operationstypernas namn, krav på ClickHouse. | `modules/settings/usage`, `pages/settings/billing/SettingsUsage*.tsx` | låg |
| Arbetsflödessidorna i objektkärnan | Listans kolumner, synlighet, markering och massradering, arbetsflödessidans flikar och statistik. Servern täcks av AF-009–AF-025. | `pages/object-core/WorkflowCore*.tsx`, `modules/object-core/workflows` | låg |
| Serveradmin: AI-leverantörer | Formulären för ny leverantör och ny modell (autentiseringssätt, prissättning, gränser, inmatningstyper, datahemvist). AR-714 nämner bara funktionen. | `pages/settings/admin-panel/SettingsAdminNewAiProvider.tsx`, `SettingsAdminNewAiModel.tsx`, `SettingsAdminAiProviderDetail.tsx`, `modules/settings/admin-panel/ai` | låg |
| Installerad app: detaljsidor per innehållstyp | Egna sidor för kommandopost, frontkomponent (förhandsvisning), tidslinjehändelsetyp och OAuth-anslutning. API-268 nämner bara innehållsöversikten. | `pages/settings/applications/SettingsApplication*Detail.tsx`, `tabs/` | låg |

## C. Funktionsrader som fyller luckorna

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-001 | Användaren öppnar och stänger loggkonsolen med ett kortkommando. | Ctrl+J (Windows/Linux) eller Cmd+J (Mac) växlar konsolen; kortkommandot fungerar även på inställningssidorna. Konsolen är en panel som fälls upp längst ned i appen, under sidopanelen i lagerordningen. | `modules/log-console/components/LogConsoleToggleHotkeyEffect.tsx`, `states/isLogConsoleEnabledState.ts` | AGPL |
| LKF-002 | Loggkonsolen är bara tillgänglig för den som får se säkerhet, och inte på mobil. | Kräver behörighetsflaggan SECURITY i rollen och en skärm som inte räknas som mobil. Utan behörighet finns varken kortkommando eller yta. | `modules/log-console/hooks/useIsLogConsoleAllowed.ts` | AGPL |
| LKF-003 | Användaren väljer bland sex loggkällor i konsolen. | Poständringar (posthändelser), Säkerhet (arbetsytehändelser), Applogg (appars loggar), Webhooks (arbetsytehändelser av webhooktyp), Sidvisningar och Användning (användningshändelser). Varje källa har egna kolumner, egna filterfält, egna id-fält i detaljpanelen och en egen räknetext ("N changes" osv.). | `modules/log-console/constants/LogConsoleSources.tsx`, `types/LogConsoleSource.ts` | AGPL |
| LKF-004 | Poständringar och applogg är fria; övriga källor kräver revisionsloggar i planen. | Säkerhet, Webhooks, Sidvisningar och Användning är märkta som krävande planrättigheten AUDIT_LOGS. Utan den visas en uppmaning: poständringar och applogg finns i nuvarande plan, övriga loggtyper kräver Organization, med knappen Uppgradera. Saknar instansen ClickHouse visas att loggar kräver ClickHouse och att man ska kontakta administratören. | `LogConsoleSources.tsx` (requiresAuditLogs), komponenterna i `modules/log-console/components` | AGPL |
| LKF-005 | Poständringar visar vad som hände med en post och vem som gjorde det. | Sex åtgärder med egen färg och etikett: skapad (visar initialvärden), uppdaterad och upsert (visar ändringar), raderad (flyttad till papperskorgen, visar värden före radering), återställd (från papperskorgen), permanent raderad (inga värden sparas; texten "Permanently deleted records keep no values"). Aktören hämtas ur createdBy vid skapande och updatedBy vid uppdatering. Detaljpanelen visar åtgärd, tid, aktör, objekt, ändrade fält som före/efter, samt post-id och användar-id; posten kan öppnas därifrån. | `constants/LogConsoleRecordActions.ts`, `components/LogConsoleRecordChangeDetail.tsx`, `utils/getLogConsoleRecordChangeFieldDiffs.ts`, `utils/getLogConsoleRecordChangeActor.ts` | AGPL |
| LKF-006 | Sidvisningar loggas per medlem och session. | Varje sidbyte registreras som en sidvisning (spårningsanrop från fronten). I konsolen: medlem, sida, tid, användar-id och sessions-id; filtret heter Medlem. | `modules/analytics/components/TrackPageViewEffect.tsx`, `hooks/useEventTracker.ts`, `log-console/constants/LogConsolePageViewColumns.tsx` | AGPL |
| LKF-007 | Applogg, webhooks och användning har egna kolumner. | Applogg: nivå (Error röd, Warning orange, Info blå, Debug grå), källa, felkod, appversion, app och körning (funktion). Webhooks: status, händelse, endpoint-URL (värdnamnet visas, länk om giltig), webhook-id. Användning: förbrukare, kvantitet, användningstyp och operation, krediter, användar-id i arbetsytan. Säkerhet: händelse och aktör. | `constants/LogConsoleLevels.ts`, `LogConsoleApplicationLog*`, `LogConsoleWebhook*`, `LogConsoleUsage*`, `LogConsoleSecurity*` | AGPL |
| LKF-008 | Användaren väljer tidsintervall, och valet hålls inom lagringstiden. | Förval: senaste 15 minuter, 1 timme, 4 timmar, 24 timmar, 7 dagar, 30 dagar, 90 dagar. Ett förval som går längre bak än arbetsytans lagringstid är inte valbart; ett sparat förval utanför lagringstiden byts mot det längsta som ryms (annars 15 minuter). Lagringstiden visas som "Logs are kept N hours/days": utan revisionsrättigheten gäller en fast kort tid i timmar, med den arbetsytans inställda antal dagar (standard enligt händelseloggens regler, AR-633). Tidszon för tidsstämplarna kan väljas; "Today"/"Yesterday" används i tidsvisningen. | `constants/LogConsoleTimeRangePresets.ts`, `utils/getLogConsoleTimeRangeWithinRetention.ts`, `hooks/useLogConsoleRetention.ts`, `hooks/useLogConsoleTimeZone.ts` | AGPL |
| LKF-009 | Användaren filtrerar loggarna per fält. | Filterfält beror på källan (t.ex. åtgärd, aktör, objekt för poständringar). Varje filter har operanden IS eller IS_NOT och kan ta flera värden ("N options"); "Clear" rensar. Sökfält för att hitta filterfält. Tomt resultat: "No event logs found" / "No results"; fel: "Something went wrong while loading logs". | `components/LogConsoleToolbar.tsx`, `constants/*FilterFields.tsx`, `utils/getLogConsoleFieldFilters.ts`, `states/logConsoleFiltersState.ts` | AGPL |
| LKF-010 | Konsolen kan följa loggen live, pausas och uppdateras. | Knapparna Pause/Resume styr livläget (nya händelser strömmar in, se AR-632) och Refresh hämtar om. | `components/LogConsoleToolbar.tsx`, `LogConsoleResults.tsx` | AGPL |
| LKF-011 | Användaren läser och kopierar en enskild logg och anpassar ytan. | Klick på en rad öppnar en detaljpanel med fält, id-fält med kopieringsknapp och rå händelse; "Copy as JSON" kopierar hela loggen ("Log copied as JSON"). Konsolens höjd kan dras (minst 200 px), kolumnbredder och detaljpanelens bredd kan dras och sparas, helskärm kan slås på och av. Tomma värden visas som "Empty", tom sträng, tom lista eller tomt objekt. | `components/LogConsoleDetailPanel.tsx`, `LogConsoleFieldsCard.tsx`, `constants/LogConsoleHeightConstraints.ts`, `LogConsoleColumnWidthConstraints.ts`, `states/isLogConsoleFullScreenState.ts`, `logConsoleColumnWidthsFamilyState.ts` | AGPL |
| LKF-012 | Appen visar en indikator när en inbäddad yta har mikrofon- eller kameraåtkomst. | En liten knapp med prick syns bara när minst en mediaåtkomst finns. Rubriken är "Microphone or camera in use" när något spelar in (pricken markerar inspelning), "Media access requests" när en begäran väntar, annars "Media access enabled". Hovring öppnar en lista grupperad per ägare (en ägare är en widget i arbetsytan eller en app). | `modules/media-access/components/MediaAccessIndicator.tsx`, `MediaAccessSessionRow.tsx`, `types/MediaAccessSession.ts`, `types/MediaAccessOwner.ts` | AGPL |
| LKF-013 | En mediaåtkomst har tre tillstånd. | Väntar (begäran ej besvarad, "Waiting for permission", kan avbrytas), spelar in (kan stoppas, "Stop capture"), delegerad (rättigheten är vidaregiven till ett inbäddat ursprung och visas per ursprung; kan stängas av, "Disable media access"). Medietyp per session: mikrofon, kamera eller båda, med egna etiketter ("Microphone access enabled" osv.). | `types/MediaAccessSession.ts`, `components/MediaAccessSessionRow.tsx` | AGPL |
| LKF-014 | Användaren aktiverar mikrofon/kamera för en inbäddad yta med en knapp. | En inbäddad ruta som behöver media visar en knapp ("Enable microphone", "Enable camera" eller "Enable microphone and camera"); bekräftelse "Enable media access for {ägare}?". Utan aktivering får rutan ingen åtkomst. | `components/ManagedIframe.tsx`, `ManagedIframeEnableButton.tsx`, `ManagedIframeSession.tsx` | AGPL |
| LKF-015 | Den inbäddade rutan får aldrig mer än arbetsytan tillåter. | Rutans rättighet är snittet av vad den begär och vad arbetsytans inbäddningsinställning ger det ursprunget (AR-336, AR-901): mikrofon bara om båda tillåter mikrofon, kamera likaså; blir inget kvar ges ingen rättighet. En redan given rättighet för samma ursprung som täcker både mikrofon och kamera som behövs räcker, annars krävs ny aktivering. | `utils/restrictIframeMediaPermission.ts`, `isIframeMediaPermissionCovered.ts`, `limitToDocumentIframeMediaPermissions.ts`, `hooks/useWorkspaceIframeMediaPermissions.ts` | AGPL |
| LKF-016 | Mediaåtkomsterna är gemensamma för hela appfönstret. | Alla aktiva sessioner hålls i ett gemensamt tillstånd så att indikatorn visar dem oavsett var ytan sitter (widget på postsida, instrumentpanel, appens frontkomponent). | `states/mediaAccessSessionsState.ts`, `components/ManagedIframeMediaAccessSessionEffect.tsx` | AGPL |
| LKF-017 | Administratören hanterar relaterade poststigar på objektets inställningssida. | Ett avsnitt listar objektets stigar som rader (objekt och relation per steg); "Add path" öppnar en väljare där man stegar fram via relationer ("Search relations", "Back") och lägger till med "Add this path"; en stig raderas från raden. Tomt läge: "No related records follow this object yet". Ett objekt som inte går att nå visas som "Unavailable object"; objekt utan relationer ger "No relations". | `modules/related-record-paths/components/*`, `hooks/useRelatedRecordPathMutations.ts`, `hooks/useRelatedRecordPaths.ts` | AGPL |
| LKF-018 | En stig får högst tre steg i gränssnittet. | Väljaren erbjuder bara relationer tills stigen har tre fält; nästa steg räknas fram från relationens målobjekt. Stämmer med serverns gräns (AR-942). | `constants/RelatedRecordPathMaximumFieldCount.ts`, `utils/getRelatedRecordPathNextFieldMetadataItems.ts`, `utils/findRelationTargetObjectMetadataItem.ts` | AGPL |
| LKF-019 | Relaterade poststigar kräver planrättigheten för radbehörighet. | Avsnittet styrs av rättigheten RLS (samma som radregler); utan den går stigar inte att lägga till. | `hooks/useHasRelatedRecordPathsEntitlement.ts` | AGPL |
| LKF-020 | Datamodellen blir skrivskyddad när instansen låser schemat. | När instansen rapporterar låst datamodell (DDL-lås, t.ex. under uppgradering) visas objektens fält, relationer, inställningar och om-formulär som skrivskyddade, precis som för ett skrivskyddat objekt. | `modules/client-config/states/isDDLLockedState.ts`, `modules/settings/data-model/object-details/components/tabs/ObjectFields.tsx`, `ObjectSettings.tsx`, `SettingsUpdateDataModelObjectAboutForm.tsx` | AGPL |
| LKF-021 | Instansens inställningar slår av och på funktioner i fronten. | Fronten läser vid start bl.a.: om Google- respektive Microsoft-mejl och -kalender och IMAP/SMTP/CalDAV är påslagna (styr vilka anslutningsknappar som visas), om e-postverifiering krävs, om flera arbetsytor är tillåtna, om förhandsvisning av bilagor är på, om bolagsberikning är på, om ClickHouse finns (loggar, användning), om avsändardomäner körs i demoläge, om Cloudflare-integrationen är på, om introduktionen har steget "boka samtal" och AI-chatt, kalenderbokningssida, captcha, supportchatt, Sentry, appversion, publika labbflaggor, om funktionsflaggor får hanteras, om ikoner får hämtas från extern ikontjänst, underhållsläge och instanstyp. Läsningen cachas med en versionsnyckel och kan misslyckas med ett eget felläge. | `modules/client-config/states/*`, `hooks/useClientConfig.ts`, `constants/ClientConfigCacheVersion.ts` | AGPL |
| LKF-022 | Utvecklarinstans kan förifylla inloggningen. | Är instansen konfigurerad för det fylls inloggningsformuläret i med standarduppgifter för demo/utveckling. Ska aldrig vara på i drift. | `modules/client-config/states/isDeveloperDefaultSignInPrefilledState.ts` | AGPL |
| LKF-023 | Medlemmen har en egen sida "Apps preferences" med flikarna Apps och Accounts. | Nås från Användare › Apps preferences; dold utan behörighetsflaggan CONNECTED_ACCOUNTS. Apps: appar som administratören installerat och som har personliga inställningar ("Choose your preferences for the apps installed on your workspace by the admin"). Accounts: medlemmens anslutna konton. De gamla adresserna under Konton omdirigeras hit. | `modules/settings/app-preferences/components/SettingsAppPreferencesGeneralTab.tsx`, `SettingsAppPreferencesAccountsTab.tsx`, `constants/SettingsAppPreferencesTabIds.ts`, `constants/AppPreferencesPathByLegacyAccountsPath.ts`, `components/SettingsLegacyAccountsRedirect.tsx`, `pages/settings/accounts/SettingsApplicationPreferences.tsx` | AGPL |
| LKF-024 | Ett anslutet konto kan delas mellan flera appar (kontogrupp). | Avsnittet "Accounts – Shared accounts between apps" listar varje konto med status (Synced, Importing N %, Sync paused, Setup incomplete, Not synced) och vilka appar som använder det ("Used by"). Inbyggda kontoappar: Gmail och Kalender (Google), Outlook (Microsoft) och IMAP; varje inbyggd app visar sina behörigheter (läsa mejl, skicka mejl, hantera händelser) och vilka leverantörsomfång de motsvarar. Tomt läge erbjuder anslutning. | `components/SettingsAccountGroupsSection.tsx`, `SettingsAccountGroupTableRow.tsx`, `SettingsAccountGroupUsedBy.tsx`, `SettingsConnectedAccountSyncStatus.tsx`, `constants/BuiltInAccountApps.ts` | AGPL |
| LKF-025 | Medlemmen ansluter ett eget konto som en app använder åt hen. | Appar med anslutningsleverantör visar kort "Connect with {leverantör}": kontot är medlemmens eget och appen agerar för hens räkning. Kontots e-postinställningar nås härifrån (synlighet, kontaktskapande, uteslut gruppadresser och icke-professionella adresser, pausa import; spärrlistan gäller alltid). Ett ogiltigt certifikat på e-postservern visas som eget fel. | `components/SettingsApplicationConnectCard(s).tsx`, `SettingsAppPreferencesMessageChannelDetails.tsx`, `pages/settings/accounts/SettingsAppPreferencesSelectedMessageChannelDetails.tsx` | AGPL |
| LKF-026 | Flera anslutningar kan kopplas från eller raderas på en gång, med delresultat. | Radmenyn: Reconnect, Disconnect account, Delete account and data (bekräftelse "Delete account and synced data?"), Remove connection (bekräftelse). Vid flera markerade redovisas utfallet "N av M" med namnen på dem som inte gick. Laddningsfel för appar och anslutningar visas med egna texter. Appens hälsokontroll kan köras för den egna användaren (API-351). | `components/SettingsAppPreferencesRowDropdownMenu.tsx`, `SettingsAppPreferencesConnectionRowDropdownMenu.tsx`, `SettingsAppPreferencesRemoveConnectionDialog.tsx`, `graphql/mutations/runMyApplicationHealthCheck.ts` | AGPL |
| LKF-027 | Avsändardomänens DNS-poster kan läggas in med hjälp av ett AI-verktyg. | Knappen "Set up DNS with AI" kopierar en färdig uppmaning med domänen och varje post (typ, namn, värde, ev. prioritet) till urklipp, avsedd för ett AI-verktyg med webbläsaren öppen hos Cloudflare. Uppmaningen säger åt verktyget att bara röra den domänen, behandla posterna som data, inte ändra andra poster och visa ändringarna för bekräftelse. Visas bara när Cloudflare-integrationen är påslagen; kan avfärdas. DNS-posterna grupperas (domänautentisering, avregistreringslänk, DMARC-policy) med status Verified, Pending, Failed, Temporary Failure, Not set. | `modules/settings/emailing-domains/components/SettingsEmailingDomainAiSetup.tsx`, `utils/buildEmailingDomainAiSetupPrompt.ts`, `constants/VerificationRecordGroupDisplayOrder.ts`, `utils/getVerificationRecordGroupStatusDisplay.ts` | AGPL |
| LKF-028 | Inställningsmenyn visar bara de sidor rollen får se. | Användare: Profil, Experience (alltid), Apps preferences (kräver CONNECTED_ACCOUNTS). Arbetsyta: General (WORKSPACE), Data model (DATA_MODEL), Layout (LAYOUTS), Members (WORKSPACE_MEMBERS), Billing (fakturering påslagen på instansen och BILLING), Developers (API_KEYS_AND_WEBHOOKS), Apps (APPLICATIONS), AI (AI_SETTINGS), Communication (WORKSPACE). Övrigt: Admin Panel (användaren får imitera eller har full adminpanel), Community (WORKSPACE), Support (bara om supportchatten är av typen Front och har ett chatt-id), Documentation, Logout. En post för Integrationer finns men är avstängd. Säkerhet och Roller har ingen egen menypost här (roller nås via Members). | `modules/settings/hooks/useSettingsNavigationItems.tsx` | AGPL |
| LKF-029 | Administratören skapar utgiftstak från mallar eller från grunden. | Gränssidan beskriver taken och vem de gäller; "New limit" erbjuder vanliga mallar eller "Start from scratch". Formulär: användning (operation, "All operations" möjligt), förbrukare (arbetsytan, medlem, API-nyckel, app; "Choose a spender"), belopp och period (hur ofta det nollställs), enhet. Gränser för medlemmar, API-nycklar och appar kräver Organization-planen ("Upgrade to Organization"). Listan har sök och filter, visar använt mot tak ("Nothing counted against this scope yet" när inget förbrukats) och avaktiverade gränser. Radering har farozon och bekräftelse; texten förklarar att utan gränsen begränsas förbrukningen bara av planens tilldelning och övriga gränser. Kvitton: "Limit created/updated/deleted" och felmeddelanden. | `modules/settings/billing/components/SettingsBillingLimit*.tsx`, `components/internal/SettingsBillingLimit*.tsx`, `pages/settings/billing/SettingsBillingLimits.tsx`, `SettingsBillingNewLimit.tsx`, `SettingsBillingLimitEdit.tsx` | AGPL (gränssnittet; servern Enterprise enligt AR-622ff) |
| LKF-030 | Användningssidan visar kreditförbrukning över valbar period. | Perioder: senaste 7, 30 eller 90 dagar. Avsnitt: förbrukning över tid, daglig användning, uppdelning per typ, per app och per användare (klick på användare ger dennes dagliga fördelning; sökbar). Operationstyperna som visas: API-anrop, agentens webbsökning, agenter, appoperation, samtalsinspelning, kampanjutskick, chattar, kodkörning, e-postutskick, fillagring, poster, prenumeration, webbsökning, webhookanrop, arbetsflödeskörning (plus "alla operationer"). Kräver ClickHouse ("Usage analytics requires ClickHouse"); tomlägen "No usage data yet". | `modules/settings/usage/*`, `constants/UsageOperationTypeLabels.ts`, `utils/getPeriodOptions.ts`, `pages/settings/billing/SettingsUsage.tsx`, `SettingsUsageUserDetail.tsx` | AGPL |
| LKF-031 | Arbetsflödeslistan och arbetsflödessidan i objektkärnan. | Listan: namn, statusar (Draft, Active, Deactivated, Archived), synlighet (Everyone/Workspace, Only you/Private, System), senaste körning, senast uppdaterad, körningar och misslyckade senaste 14 dagarna; sidindelad, sortering, filter, markering av rader och massradering med bekräftelse som säger att körhistoriken raderas permanent. Utan rätt: "You do not have permission to access workflows". Arbetsflödessidan har sektionerna Översikt (körningar per dag, felfrekvens, medeltid, senaste misslyckade körningar), Flöde, Versioner (återställ som utkast med varning om befintligt utkast skrivs över) och Körningar. Appstyrda arbetsflöden är skrivskyddade. Sidan uppdateras när arbetsflödet ändras någon annanstans. Den äldre postadressen för ett arbetsflöde omdirigeras hit. | `pages/object-core/WorkflowCoreIndexPage.tsx`, `WorkflowCoreShowPage.tsx`, `WorkflowCoreObjectShowPage.tsx`, `modules/object-core/workflows/*` | AGPL |
| LKF-032 | Gamla AI-chattadresser omdirigeras till inkorgen. | En äldre chattadress med tråd-id leder till motsvarande tråd i inkorgen när en sådan finns; ogiltigt eller saknat id öppnar en ny tråd. På mobil visas en stängknapp. | `pages/legacy-ai-chat/LegacyAiChatPage.tsx`, `modules/legacy-ai-chat` | AGPL |
| LKF-033 | Skämtläget "Salesfarce" är ett tillfälligt tema. | Aktiveras via en särskild begäran, sparas bara för sessionen, tvingar ljust färgschema, byter fliktitelns ändelse och favicon och visar ett märke. | `modules/salesfarce/*` | AGPL |
| LKF-034 | Serveradmin lägger till AI-leverantörer och modeller. | Ny leverantör: välj känd leverantör ur en katalog eller skapa egen (OpenAI-kompatibel med bas-URL); etikett krävs och måste innehålla minst ett alfanumeriskt tecken. Autentisering: API-nyckel, åtkomstnyckelpar eller instansens IAM-roll (Bedrock: region krävs; nyckel eller nyckelpar, aldrig båda; båda nycklarna eller ingen). Valfri datahemvist (region där inferensen sker). Inbyggda leverantörer får sin nyckel via sin egen sida. Leverantörens modeller slås på/av; borttagning kopplar loss alla dess modeller. Ny modell: välj känd eller egen modell-id, visningsnamn, pris per miljon token in/ut och för cacheläsning/-skrivning (USD), kontextfönster och max utdata (positiva heltal), resonemang ja/nej, inmatningstyper utöver text (bild, ljud, video, PDF). | `pages/settings/admin-panel/SettingsAdminNewAiProvider.tsx`, `SettingsAdminNewAiModel.tsx`, `SettingsAdminAiProviderDetail.tsx`, `modules/settings/admin-panel/ai/*` | AGPL |
| LKF-035 | Installerad app har en detaljsida per innehållstyp. | Kommandopost: etikett, kort etikett, ikon, fäst, villkorad tillgänglighet och konfiguration. Frontkomponent: detaljer och förhandsvisning (en komponent utan gränssnitt visar "runs without a UI"). Tidslinjehändelsetyp: visa i postens tidslinje på/av, med återställning till appens förval. OAuth-anslutning: leverantör, handtag, beviljade omfång, senast uppdaterad/inloggad, autentiseringsfel och orsak, återanslut eller ta bort. Okänd anslutning ger "Connection not found". | `pages/settings/applications/SettingsApplicationCommandMenuItemDetail.tsx`, `SettingsApplicationFrontComponentDetail.tsx`, `SettingsApplicationTimelineActivityTypeDetail.tsx`, `SettingsApplicationConnectionDetail.tsx`, `SettingsApplicationContentTypeDetail.tsx`, `tabs/*SettingsTab.tsx`, `tabs/SettingsApplicationFrontComponentPreviewTab.tsx` | AGPL |

## D. Kataloger utan användarsynlig funktion

| Katalog | Varför |
|---|---|
| `modules/activities/graphql`, `states`, `types` | Frågor, klienttillstånd och typer för anteckningar, uppgifter och tidslinje; beteendet står i t03. |
| `modules/apollo` | Klienten mot API:t och optimistiska cacheuppdateringar; ingen egen funktion (felrutor vid misslyckad fråga följer t12:s återkopplingsmönster). |
| `modules/browser-event` | Intern händelsebuss i fliken som meddelar andra delar när poster eller metadata ändrats. |
| `modules/companies`, `modules/people` | Bara en typdefinition var. |
| `modules/dropdown-context-state-management` | Två hjälpkrokar för rullgardinsmenyers tillstånd. |
| `modules/metadata-error-handler` | Klassar metadatafel till meddelanden; texterna står i t01:s felkoder. |
| `modules/metadata-store` | Klientens lager och cache för metadata; att det laddas om vid ändring täcks av t07 API-272. |
| `modules/sign-in-background-mock` | Dekorativ låtsastabell bakom inloggningsrutan. |
| `modules/users` | Laddar inloggad användare; kontoradering och lämna arbetsyta i t08 AR-808, AR-809. |
| `modules/object-record/components`, `graphql`, `states`, `types`, `utils` | Postchip, frågebyggare, tillstånd och hjälpfunktioner; beteendet (summeringar, positioner, chip) är beskrivet i t02 och t03. |
| `modules/settings/constants`, `types`, `utils` | Bredd på innehållsytan, ankarattribut och typer. |
| `modules/ui/types` | Gemensamma typer. |
| `modules/workflow/states` | Klienttillstånd för redigeraren (pågående sparning, utkast, senast skapat steg). |
| `pages/settings/__stories__` | Storybook-berättelser. |

## E. Motsägelser mellan läsarnas filer

| Var | Motsägelse | Vad koden säger |
|---|---|---|
| t08 AR-923 mot t12 UX-208 | AR-923 lämnar öppet vilken behörighetsflagga som krävs för Layout ("troligen LAYOUTS: obelagt"). UX-208 listar menysektionerna Konton, Mejl, Kalendrar, Integrationer, Säkerhet, Roller, Webhooks, Labb, Versioner. | Layout kräver LAYOUTS. Dagens meny har inte de sektioner UX-208 räknar upp (UX-208 bygger på en e2e-sida som släpar efter); se LKF-028. |
| t08 AR-818 mot t08 AR-631 och fronten | AR-818 beskriver "händelseloggsvyn" som en tabell i `modules/settings/event-logs` och märker den Enterprise. | Användarens yta för händelseloggarna är i dag loggkonsolen (LKF-001–LKF-011). Ingen fil i `modules/log-console` eller `modules/settings/event-logs` bär Enterprise-märkningen; Enterprise gäller serverns vy (AR-631). |
| t08 AR-631 mot fronten | AR-631 nämner att objekthändelser är fria men inte applikationsloggar. | Även applogg är fri i konsolen (LKF-004). Värt att belägga på servern. |
| t05 MK-L01–MK-L13 mot fronten | Kontolistan beskrivs som en egen sida under Inställningar › Konton. | De gamla kontoadresserna omdirigeras till Apps preferences (LKF-023); innehållet i MK-L stämmer men platsen har flyttat. |
| t02 Det jag inte hann läsa mot t03 | t02 anger `record-card` som oläst; t03 anger den som läst av andra kontrolläsaren. | Ingen motsägelse i sak, men ingen rad i någon fil har `record-card` som ursprung; kanbankortets beteende står i VY-140–VY-155. |

Inga motsägelser hittades i stickprov på papperskorgens standardtid (14 dagar: AR-333, AR-900), provperiodernas längd (30/7 dagar: AR-603, UX-171, HB-002) och kortkommandona (UX-266 mot U-11, U-23, U-24, NAV-052).

## F. Antal funktionsrader

Räknat som unika ID på rader med full funktionsrads-bredd (minst fem kolumner). Rättelserader (fyra kolumner) och uppräkningsrader med prefix U ingår inte.

| Fil | Prefix | Funktionsrader |
|---|---|---|
| twenty-01 datamodell | DM | 210 |
| twenty-02 vyer | VY | 208 (+25 uppräkningar U) |
| twenty-03 postsida | PS | 213 (+29 uppräkningar U) |
| twenty-04 navigering | NAV | 166 |
| twenty-05 mejl och kalender | MK | 347 |
| twenty-06 arbetsflöden | AF | 291 |
| twenty-07 API, webhooks, appar | API | 351 |
| twenty-08 inloggning, roller | AR | 346 |
| twenty-09 import, export | IE | 203 |
| twenty-10 dashboards | DB | 192 |
| twenty-11 AI och appar | AI | 271 |
| twenty-12 UI-system | UX | 304 |
| twenty-13 handboken | HB | 393 |
| **Summa 01–13** | | **3 495** |
| twenty-99a (denna fil) | LKF | 35 |
| **Totalt** | | **3 530** |

## Det jag inte hann läsa

- Loggkonsolens enskilda komponenter rad för rad: exakt hur livläget strömmar in och sidbläddras, vilka filterfält varje källa har i detalj, och var konsolen öppnas utöver kortkommandot (sökningen efter anropare över hela `modules` tog för lång tid på disken och avbröts).
- `modules/settings/admin-panel` utöver AI-leverantörerna: arbetsytedetalj, chattrådsvisaren, ködetalj och appregistreringarnas sidor är bara avprickade mot serverraderna AR-704–AR-717, inte lästa i gränssnittet.
- `modules/settings/billing` utöver gränssidan (200 filer): planjämförelsen, kreditpaketväljaren och betalkortsdialogen är bara avprickade mot AR-813 och AR-6xx.
- `modules/settings/roles` (149 filer) och `modules/inbox` (167 filer) är bara avprickade mot befintliga rader, inte lästa på nytt.
- `modules/client-config`: var varje flagga faktiskt används i fronten är inte spårat för alla flaggor, bara för låst datamodell.
- Täckningen avgjordes per katalog. En katalog med minst en träff räknas som täckt även om enskilda filer i den inte har egen rad; djupet i stora kataloger (`object-record/record-table`, `page-layout`, `ui/*`) är läsarnas ansvar och har inte prövats fil för fil.
- Licenskontrollen mot `@license Enterprise` gjordes bara i luckkatalogerna (och träffade då bara `settings/security`, SSO). Hela `twenty-front` söktes inte, eftersom sökningen överskred tidsgränsen.

## Oklarheter

- Om loggkonsolen även nås från en meny eller knapp (inte bara Ctrl/Cmd+J), och om den ersatt `modules/settings/event-logs` helt eller om båda finns.
- Hur lång den fasta lagringstiden i loggkonsolen är utan revisionsrättigheten (AR-812 säger 2 timmar för Pro; konsolen räknar i timmar men värdet kommer från en delad funktion som inte lästes).
- Var säkerhetssidan och rollsidan nås i dagens meny, eftersom de saknar egna menyposter (via Members-fliken och General, eller bara via direkta adresser).
- Vilka mallar gränssidan erbjuder under "Start from a common limit".
- Hur Salesfarce-läget startas i praktiken (vilken begäran som räknas).
- Om indikatorn för mediaåtkomst syns på mobil.
