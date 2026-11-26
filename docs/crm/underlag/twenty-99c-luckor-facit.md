# Twenty 99c: luckgranskning mot facit (ID-prefix LKF)

Luckgranskning av inventeringsfilerna `twenty-01` till `twenty-13` mot förlagan
(Twenty, `D:\snajp-crm-forlaga\twenty`, commit 1da6d55), handboken, e2e-flödena,
webbplatsens funktionslista och genomgången av den hostade appen
(`twenty-app-kartlaggning.md`). Allt är skrivet med egna ord; ingen kod, inga
typdefinitioner och inga längre textstycken är kopierade. Granskad 2026-11-26.

## Översikt

Läsarna delade förlagan i tolv områden (datamodell DM, vyer VY, postsida PS,
navigering NAV, mejl/kalender MK, arbetsflöden AF, API, inloggning/roller AR,
import/export IE, dashboards DB, AI/appar AI, UI-system och flöden UX) och en
trettonde läsare prickade av handboken (HB). Den här filen kontrollerar att varje
paket under `packages/`, varje handboksrad, varje e2e-flöde, webbplatsens
funktionslista och varje iakttagelse i den hostade appen har minst en
funktionsrad med rätt ursprung. Där det saknas står raden här, med prefix LKF.

**Metod.** Alla 3 666 tabellrader i de tretton filerna lästes maskinellt in
(ID, funktion, regler, ursprung). Varje katalog under `packages/*` och på andra
nivån i `twenty-server/src/engine/{core-modules,metadata-modules}`,
`twenty-server/src/modules`, `twenty-front/src/modules`,
`twenty-front/src/modules/settings`, `twenty-front/src/modules/object-record`
och `twenty-front/src/pages(/settings)` söktes mot raderna på katalognamn. Kataloger
med noll eller en träff öppnades och jämfördes mot raderna på begrepp (inte bara
sökväg). Handboksraderna (HB) matchades mot kodläsarnas rader via den
.mdx-fil de citerar; de 25 som saknade träff granskades för hand. Därtill
kontrollerades fullständigheten för sex uppräkningar mot källan:
behörighetsflaggor (26), vyfilteroperander (15), widgettyper (27),
arbetsflödessteg (23), och stickprov på webhook-/gränsvärden.

**Slutsats.** Läsarnas täckning är mycket hög. Fem verkliga luckor hittades:
loggkonsolen (Ctrl/Cmd+J), appövervakningens yta, egen drift (installation,
uppgradering, säkerhetskopiering, driftartefakter, felsökning), mediebehörighetens
yta i appen (indikator och påslagsknapp) och några mindre inställningsdetaljer
(webbläsarnotisernas uppsättningsdialog, filtret "Mostly empty" i datamodellen,
Claude-färdigheten i `twenty-claude-skills`). De fylls med LKF-001 till LKF-052.

Begrepp: *lucka* = funktion som en användare, administratör eller integratör märker
men som saknar rad; *täckt* = minst en rad med rätt ursprung; *loggkonsol* (log
console) = nedfällbar händelselogg längst ned i appen; *appövervakning*
(application monitoring) = statistik per registrerad app; *egen drift*
(self-hosting) = kunden kör Twenty på egen server.

## Avprickningslista (arbetsstatus)

| Källa | Status |
|---|---|
| twenty-01 … twenty-13 (läsarnas filer) | läst maskinellt i sin helhet (alla tabellrader); översikter, "Det jag inte hann läsa" och "Oklarheter" i twenty-13 och twenty-12 lästa manuellt |
| packages/* (21 paket) | läst (katalognivå 1–2, luckor öppnade) |
| twenty-13 handboksrader (393) | läst |
| e2e-flöden (twenty-e2e-testing, 9 spec-filer) | läst |
| webbplatsens funktionslista (twenty-12 UX-218–UX-274) | läst |
| twenty-app-kartlaggning.md | läst |

## (A) Avprickningstabell

### A1. Paket under `packages/`

| Källa | Täckt av (fil och ID-intervall) eller LUCKA |
|---|---|
| create-twenty-app | twenty-07 API-240, API-396 |
| twenty-agent-skills | twenty-11 AI-343 |
| twenty-apps | twenty-11 AI-300–AI-315 |
| twenty-claude-skills | LUCKA (låg) → LKF-052 |
| twenty-cli | twenty-07 API-245–API-412 (21 rader) |
| twenty-client-sdk | twenty-07 API-244, API-396 |
| twenty-companion | twenty-11 AI-340–AI-489 (6 rader) |
| twenty-docker | LUCKA (medel) → LKF-030–LKF-044 |
| twenty-docs/user-guide + getting-started | twenty-13 HB-001–HB-393; därtill 180+ rader i twenty-01–12 som citerar handboken |
| twenty-docs/developers/extend | twenty-07 (API), twenty-06 (AF-8xx), twenty-11 |
| twenty-docs/developers/self-host/capabilities/setup.mdx, key-rotation.mdx, security.mdx (vägzoner) | twenty-07 API-398–API-400, API-416–API-419; twenty-08 AR-922 |
| twenty-docs/developers/self-host/capabilities/docker-compose.mdx, upgrade-guide.mdx, troubleshooting.mdx, security.mdx (uppsättningsval, kontroll, checklista) | LUCKA (medel) → LKF-030–LKF-044 |
| twenty-docs/developers/contribute | twenty-07 API-421 (delvis); i övrigt (D) |
| twenty-e2e-testing | twenty-12 UX-175–UX-217, UX-267 |
| twenty-emails | twenty-05 MK-K02–MK-O42 (14 rader, mallarna i MK-O32) |
| twenty-front | se A2; luckor: `modules/log-console`, `modules/settings/application-monitoring`, `modules/media-access`, delar av `modules/settings/experience`, filtret i `modules/settings/data-model/object-details` |
| twenty-front-component-renderer | twenty-07 API-209, API-273 |
| twenty-oxlint-rules | (D) |
| twenty-sdk | twenty-07 API-227–API-403 (8 rader) |
| twenty-server | se A2; lucka: `metadata-modules/object-metadata` (mostly-empty) och övervakningens yta (servern täckt av API-353) |
| twenty-shared | 238 rader i alla filer; uppräkningarna kontrollerade (A4) |
| twenty-ui | twenty-12 UX-003–UX-099 m.fl. |
| twenty-utils | (D) |
| twenty-website | twenty-12 UX-218–UX-274 |
| twenty-zapier | twenty-07 API-251–API-254 |

### A2. Kataloger i `twenty-front` och `twenty-server` som hade 0–2 träffar och därför öppnades

| Källa | Täckt av eller LUCKA |
|---|---|
| front `modules/log-console` (0 träffar på sökväg; NAV-098 beskriver bara växeln) | LUCKA (medel) → LKF-001–LKF-011 |
| front `modules/settings/application-monitoring` + `pages/settings/applications/SettingsApplicationRegistrationMonitoring.tsx` + adminvarianten | LUCKA (medel; serverns API täckt av API-353) → LKF-012–LKF-019 |
| front `modules/media-access` | LUCKA (låg–medel; regler täckta av API-184, AR-336, AR-901, DB-147) → LKF-020–LKF-023 |
| front `modules/settings/experience` (Browser-notification-komponenterna) | delvis: nivåer och förhandsvisning i NAV-048, NAV-106; uppsättningsdialogen saknas → LKF-024–LKF-026 |
| front `modules/settings/data-model/object-details` (filtret "Mostly empty") + server `object-metadata/mostly-empty-fields.service.ts` | LUCKA (låg) → LKF-027–LKF-028; antal poster per objekt täckt av DM-097 |
| front `modules/settings/unsubscribers` | täckt av twenty-05 MK-I20, MK-L12; sidstorlek saknas → LKF-029 |
| front `modules/salesfarce` | twenty-12 UX-246 |
| front `modules/settings/application-registrations` | twenty-07 API-220–API-224, API-357, API-379 |
| front `modules/settings/unsubscribe-topics` | twenty-05 MK-I17, MK-L12 |
| front `modules/settings/lab` | twenty-08 AR-702, AR-815 |
| front `modules/settings/privacy` | twenty-08 AR-811; twenty-11 AI-034 |
| front `modules/settings/app-preferences` | twenty-07 API-351; twenty-05 MK-L13 |
| front `modules/object-record/record-sharing` | twenty-03 PS-112; twenty-08 AR-423–AR-426 |
| front `modules/object-record/record-seeded-draft` | twenty-03 PS-185 |
| front `modules/object-record/multiple-objects` | twenty-03 PS-210 |
| front `modules/object-record/spreadsheet-import` | twenty-09 IE-0xx (importflödet) |
| front `modules/mention` | twenty-03 PS-145 |
| front `modules/skill-suggestion` | twenty-11 (färdigheter i chatten) |
| front `modules/information-banner` | twenty-04 NAV-108, NAV-166; twenty-03 PS-163 |
| front `modules/keyboard-shortcut-menu` | twenty-12 UX-265, UX-266 |
| front `modules/tab-presence` | twenty-04 NAV-050, NAV-107 |
| front `modules/geo-map` | twenty-02 VY-170 |
| front `pages/mobile-home` | twenty-04 (mobilnavigering) |
| front `pages/settings/layout` | twenty-08 AR-923 |
| front `modules/settings/data-model/graph-overview` | twenty-01 DM-201 |
| front `modules/sign-in-background-mock`, `apollo`, `browser-event`, `metadata-store`, `metadata-error-handler`, `dropdown-context-state-management` | (D) |
| server `core-modules/tab-presence`, `pending-wake-up` | twenty-04 NAV-050, NAV-051, NAV-163 |
| server `core-modules/short-link` | twenty-07 API-129; twenty-05 MK-I37 |
| server `core-modules/public-domain` | twenty-08 AR-505 |
| server `core-modules/dpa` | twenty-08 AR-079, AR-718 |
| server `core-modules/lab`, `feature-flag` | twenty-08 AR-702 |
| server `core-modules/telemetry` | twenty-08 AR-721 |
| server `core-modules/event-logs` | twenty-08 AR-630–AR-633, AR-818 |
| server `core-modules/application/application-monitoring` | twenty-07 API-353 |
| server `core-modules/key-value-pair` | twenty-05 MK-A12 (återanslutningslistor); twenty-04 NAV-108 (avfärdade banderoller) |
| server `core-modules/app-token` | twenty-08 AR-221 (återställningslänk); twenty-05 MK-O31 |
| server `core-modules/throttler` | twenty-07 API-110 |
| server `core-modules/health` | twenty-08 AR-710 |
| server `engine/trash-cleanup` | twenty-01 DM-184 |
| server `metadata-modules/application-translation-catalog`, `metadata-translation` | twenty-01 DM-211; twenty-07 API-342, API-355 |
| server `modules/onboarding-invite-suggestions`, `onboarding-recent-messages-import` | twenty-04 NAV-039; twenty-05 MK-J04, MK-J05 |
| server `modules/dashboard-sync` | twenty-10 DB-046 |
| server `modules/match-participant` | twenty-05 MK-E02–MK-E05 |
| server `metadata-modules/flat-*`, `data-source`, `deferred-workspace-operation`, `pagination`, `overrides`, `minimal-metadata`, `workspace-metadata-version`, `workspace-feature-flags-map-cache` | (D) |
| server `core-modules/{cache-lock,cache-storage,redis-client,environment,exception-handler,guard-redirect,logger,sentry,sql-sanitization,secure-http-client,message-queue,session-storage}`; `engine/{core-entity-cache,dataloaders,workspace-cache,workspace-cache-storage,workspace-datasource}` | (D) |

### A3. Övriga källor

| Källa | Täckt av eller LUCKA |
|---|---|
| twenty-13 handboksrader HB-001–HB-393 | 368 rader har en kodrad i twenty-01–12 som citerar samma .mdx-fil. De 25 utan sådan träff är avgjorda här: HB-010–HB-012 → twenty-02 VY-016, VY-102, VY-117–VY-121, VY-012–VY-017; HB-079 → twenty-01 DM-156; HB-148 → twenty-05 MK-H04; HB-225 → twenty-01 DM-050–DM-056, twenty-03 PS-128–PS-130; HB-226 → twenty-03 PS-145 (motsägelse, se E2); HB-231 → twenty-01 DM-150–DM-153 (motsägelse, se E1); HB-271 → twenty-02 VY-107, VY-113; HB-284 → twenty-02 (kanban), twenty-01 (opportunity); HB-227–HB-230, HB-232, HB-235–HB-237, HB-285, HB-286 är recept som kombinerar befintliga steg (twenty-06 AF-2xx) och saknar egen funktion; HB-041, HB-389, HB-391, HB-392, HB-393 är presentations-, navigerings- och tjänstesidor (D) |
| twenty-13 "Uppräkningar i handboken" | täckta; kodens uppräkningar är större än handbokens (se A4) |
| e2e: `tests/authentication/onboarding.spec.ts` | twenty-12 UX-176, UX-200 |
| e2e: `tests/authentication/return-to-path.spec.ts` | twenty-12 UX-177, UX-178 |
| e2e: `tests/authentication/signup_invite_email.spec.ts` | twenty-12 UX-179–UX-181 |
| e2e: `tests/create-kanban-view.spec.ts` | twenty-12 UX-182–UX-184 |
| e2e: `tests/create-record.spec.ts` | twenty-12 UX-185, UX-186 |
| e2e: `tests/workflow-creation.spec.ts` | twenty-12 UX-187 |
| e2e: `tests/workflow-visualizer.spec.ts` | twenty-12 UX-188–UX-192 |
| e2e: `tests/workflow-use-as-draft.spec.ts` | twenty-12 UX-193–UX-195, UX-198 |
| e2e: `tests/workflow-run.spec.ts` | twenty-12 UX-196, UX-197 |
| e2e: `tests/login.setup.ts`, `lib/pom/**` | twenty-12 UX-175, UX-199–UX-217 |
| Webbplatsens funktionskort och produktsidor | twenty-12 UX-218–UX-233 |
| Webbplatsens prissida och planjämförelse | twenty-12 UX-234–UX-242; kodmotsvarighet: AR-60x (plan), AI-172 (AI-kvot), API-110 (API-gräns), AR-630–AR-633 (loggar). Enterprise-löften utan kod (SCIM, IP-vitlistning, LTS, luftgapad drift, VPN, dedikerad beräkning): se Oklarheter 1 |
| Webbplatsens licensnyckel, jämförelser, marknadsplats, partner | twenty-12 UX-243–UX-251, UX-268–UX-274 |
| App: vänsterrail, sidhuvud, vyrad, Options, Filter med dolda fält | twenty-04 NAV-0xx; twenty-02 VY-0xx |
| App: Kom igång (räknare, stege, AI-guide, HubSpot-importkort) | twenty-04 NAV-039–NAV-046, NAV-119, NAV-132; twenty-12 UX-297–UX-301 |
| App: tabellens sidfot "Calculate", tavlans kolumnsummor, tomläge | twenty-02 VY-183, VY-137, VY-169; twenty-10 DB-116, DB-118 |
| App: post i sidopanel med `?panel=`, flikar, helsida med föregående/nästa | twenty-03 PS-001, PS-016, PS-199; twenty-02 VY-023, VY-139 |
| App: kommandomenyns sju avsnitt, G-genvägar | twenty-04 NAV-052–NAV-1xx; twenty-12 UX-266 |
| App: kommandomenyns "Developer › Show logs" | LUCKA → LKF-001 |
| App: arbetsflödeslistan och redigeraren | twenty-06 AF-018, AF-019, AF-7xx |
| App: dashboard med widgetar | twenty-10 DB-0xx–DB-1xx |
| App: Inställningar › Profile, Experience | twenty-08 AR-07x, AR-810, AR-908 |
| App: Inställningar › Apps preferences | twenty-07 API-351; twenty-05 MK-L13 |
| App: Inställningar › General (med Security) | twenty-08 AR-811, AR-812, AR-933 |
| App: Inställningar › Data model (Name, App, Fields, Records, Visualize) | twenty-01 DM-097, DM-201; "Mostly empty"-filtret → LKF-027 |
| App: Inställningar › Layout (Customize, sammanräkning) | twenty-08 AR-923; twenty-04 NAV-088 |
| App: Inställningar › Members (Team, Invite, Roles) | twenty-08 AR-0xx–AR-4xx |
| App: Inställningar › Billing | twenty-08 AR-603–AR-609, AR-813 |
| App: Inställningar › Developers (API, Webhooks, Apps, CLI; lekplats) | twenty-07 API-003, API-125, API-264; twenty-08 AR-226 |
| App: Inställningar › Apps (marknadsplats, installerade) | twenty-07; twenty-11 AI-300–AI-315 |
| App: Inställningar › AI (MCP, Models, Skills, Tools, Usage) | twenty-11 AI-008–AI-013, AI-146, AI-186–AI-191 |
| App: Inställningar › Communication (Emails, Whatsapp snart, Calls snart) | twenty-05 MK-L10–MK-L13, MK-M07 |
| App: Inställningar › Community / Support / Documentation / Logout | twenty-08 AR-815; twenty-04 |
| App: API-kartan (FindMany, Aggregate, GroupBy, metadata-anrop) | twenty-07 API-0xx; twenty-02 VY-013, VY-064 |
| App: realtid via `AddQueryToEventStream` / `RemoveQueryFromEventStream` | twenty-07 API-066–API-068 |
| App: `ObjectRecordCounts`, `MostlyEmptyFieldMetadataIds` | DM-097; LKF-027–LKF-028 |
| App: `GetIframeWidgetMediaPermissions` | DB-036, DB-147; ytan → LKF-020–LKF-023 |

### A4. Uppräkningar kontrollerade mot källan

| Uppräkning (källa) | Antal i källan | Resultat |
|---|---|---|
| Behörighetsflaggor (`twenty-shared/src/constants/PermissionFlagType.ts`) | 26 | Alla 26 finns i rader (API-371, AR-412, AR-413 m.fl.) |
| Vyfilteroperander (`twenty-shared/src/types/ViewFilterOperand.ts`) | 15 | Alla finns (DM-278, VY-036, U-02) |
| Widgettyper (`twenty-shared/src/types/page-layout/WidgetType.ts`) | 27 | Alla finns i PS-028/U-03/U-27; MESSAGE_CAMPAIGN_BODY, MESSAGE_CAMPAIGN_DETAILS och WORKFLOW_RUN har bara uppräkning, beteendet står i PS-201 och MK-I12 (godtaget) |
| Arbetsflödessteg (`twenty-shared/src/workflow/types/WorkflowActionType.ts`) | 23 | Alla finns (AF-1006, AF-1026, AF-2xx) |

## (B) Luckor

| Område | Vad som saknas | Var i förlagan | Hur allvarligt |
|---|---|---|---|
| Loggkonsol | Hela den nedfällbara loggkonsolen: kortkommando, sex källor, tidsintervall, nivåer, kolumner och filter per källa, detaljpanel, lagringstid, helskärm. NAV-098 beskriver bara en kosmetisk växel och AR-818 bara inställningsvyn. | `twenty-front/src/modules/log-console/`; data från `twenty-server/src/engine/core-modules/event-logs/` | medel |
| Appövervakning | Ytan för att följa en registrerad apps körningar, fel, versioner, krediter och livscykel; perioder, tomlägen och kravet på ClickHouse. | `twenty-front/src/modules/settings/application-monitoring/`, `pages/settings/applications/SettingsApplicationRegistrationMonitoring.tsx`, `pages/settings/admin-panel/SettingsAdminApplicationRegistrationMonitoring.tsx` | medel |
| Mediebehörighet i appen | Indikatorn i appen för mikrofon/kamera, påslagsknappen i inbäddade ramar, åtgärderna stäng av / avbryt / stoppa. | `twenty-front/src/modules/media-access/` | låg–medel |
| Webbläsarnotiser | Uppsättningsdialogen med testnotis och hänvisning till systeminställningar, tillstånden "stöds inte"/"blockerad"/"klar". | `twenty-front/src/modules/settings/experience/components/Browser*`, `SettingsExperienceNotificationsSection.tsx`, `InboxNotificationPreferences.tsx` | låg |
| Datamodell | Filtret "Mostly empty" i objektets fältlista och tröskelregeln. | `twenty-front/src/modules/settings/data-model/object-details/`, `twenty-server/src/engine/metadata-modules/object-metadata/mostly-empty-fields.service.ts`, `constants/mostly-empty-*.constant.ts` | låg |
| Avregistrerade | Sidstorlek i listan. | `twenty-front/src/modules/settings/unsubscribers/constants/` | låg |
| Egen drift | Installation (skript och manuellt), systemkrav, SERVER_URL och SSL, beständighet, säkerhetskopiering, uppgradering och `upgrade:status`, cacheprefix, krypteringsbyte vid uppgradering, tre uppsättningsval för nätverk, kontroll och checklista, driftartefakter (Helm, Kubernetes, Terraform, Podman, Grafana, OpenTelemetry), känd felsökning. | `twenty-docs/developers/self-host/capabilities/{docker-compose,upgrade-guide,troubleshooting,security}.mdx`, `twenty-docker/` | medel (låg för Snajp som SaaS, men varje integratör/driftare märker det) |
| Claude-färdighet | Färdigheten som presenterar poster läsbart via MCP. | `twenty-claude-skills/skills/twenty-record-presentation/` | låg |
| Händelseloggens lagringstid | AR-633 anger standard 3 dagar men inte att planer utan rättigheten Audit logs bara behåller 2 timmar. | `twenty-shared/src/utils` (lagringstidsberäkningen), `twenty-shared/src/constants` | låg (rättas av LKF-004) |

## (C) Funktionsrader som fyller luckorna

### C1. Loggkonsolen

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-001 | Öppna och stänga loggkonsolen. | Kortkommando Ctrl+J (Windows/Linux) eller Cmd+J (Mac) växlar konsolen, även på inställningssidorna; den nås också via kommandomenyns avsnitt Developer ("Show logs"). Konsolen visas längst ned i appen ovanför innehållet. Bara för den som har behörighetsflaggan SECURITY och aldrig på mobil; för andra finns varken kortkommando eller kommando. | twenty-front/src/modules/log-console/components/LogConsoleToggleHotkeyEffect.tsx, hooks/useIsLogConsoleAllowed.ts, hooks/useSetIsLogConsoleEnabled.ts | Enterprise (datakällan `event-logs` är Enterprise-märkt; konsolens front är AGPL) |
| LKF-002 | Välja logkälla i konsolen. | Sex källor som flikar: Record changes (posthändelser), Security (arbetsytehändelser), App logs (applikationsloggar), Webhooks (webhooksvar), Page views (sidvisningar), Usage (användningshändelser). Record changes och App logs kräver inte planrättigheten Audit logs; Security, Webhooks, Page views och Usage gör det. Vald källa minns under sessionen. | twenty-front/src/modules/log-console/constants/LogConsoleSources.tsx, states/logConsoleActiveSourceIdState.ts | Enterprise |
| LKF-003 | Välja tidsintervall. | Förval: senaste 15 minuter, 1 timme, 4 timmar, 24 timmar, 7 dagar, 30 dagar, 90 dagar. Intervallet begränsas i praktiken av lagringstiden (LKF-004). Tidpunkter visas i en vald tidszon (konsolens eget val, standard användarens). | constants/LogConsoleTimeRangePresets.ts, components/LogConsoleTimeRangeDropdown.tsx, hooks/useLogConsoleTimeZone.ts, states/logConsoleTimeRangeState.ts | Enterprise |
| LKF-004 | Se hur länge loggar sparas. | Utan planrättigheten Audit logs: 2 timmar, ej inställbart. Med rättigheten: arbetsytans inställda lagringstid, standard 3 dagar, inom 1–1 095 dagar. Konsolen skriver "Loggar sparas N timmar/dagar" (timmar under ett dygn, annars dagar). | hooks/useLogConsoleRetention.ts; twenty-shared/src/constants (EVENT_LOG_RETENTION), twenty-shared/src/utils (lagringstidsberäkningen) | Enterprise |
| LKF-005 | Se posthändelser (Record changes). | Kolumner: tid, åtgärd, aktör, objekt, post. Åtgärder med färg och etikett: Skapad (grön; visar "Initiala värden"; aktör = skapare), Uppdaterad (blå; visar ändringar; aktör = senaste ändrare), Upsert (lila), Raderad (röd; "Flyttad till papperskorgen"; visar värden före radering), Återställd (turkos; "Återställd från papperskorgen"), Permanent raderad (röd; "Inga värden sparas"; visar värden före radering). Filter: åtgärd, aktör, objekt. Kopierbara ID: post-ID, användar-ID. | constants/LogConsoleRecordActions.ts, LogConsoleRecordChangeColumns.tsx, LogConsoleRecordChangeFilterFields.tsx, components/LogConsoleRecordChangeDetail.tsx | Enterprise |
| LKF-006 | Se säkerhetshändelser (Security). | Kolumner: tid, händelse, aktör; filter på händelse och aktör; kopierbart användar-ID. Händelserna är arbetsytehändelserna i AR-630 (inloggning, imitation, domän, export m.fl.). Kräver Audit logs. | constants/LogConsoleSecurityColumns.tsx, LogConsoleSecurityEventColumn.tsx, LogConsoleSecurityFilterFields.tsx | Enterprise |
| LKF-007 | Se appars loggar (App logs). | Kolumner: tid, nivå, källa, felkod, version, app, körning (funktion eller händelse). Nivåer: Error (röd, allvarlighet fel), Warning (orange, varning), Info (blå), Debug (grå). Källor: logikfunktion, installation, uppgradering, avinstallation, API-hastighetsgräns, jobbhastighetsgräns, serverrutt. Filter på motsvarande fält. | constants/LogConsoleApplicationLogColumns.tsx, LogConsoleApplicationLogAppColumn.tsx, LogConsoleApplicationLogFilterFields.tsx, LogConsoleLevels.ts; settings/application-monitoring/constants/ApplicationLogSourceLabels.ts | Enterprise |
| LKF-008 | Se webhookleveranser (Webhooks). | Kolumner: tid, status (som statusmärke), händelse, endpoint-URL (värdnamnet visas, länk till webhookens inställningssida); kopierbart webhook-ID. Kräver Audit logs. | constants/LogConsoleWebhookColumns.tsx, LogConsoleWebhookStatusColumn.tsx, components/LogConsoleWebhookEndpointLink.tsx | Enterprise |
| LKF-009 | Se sidvisningar och användning. | Page views: tid, medlem; filter på medlem; kopierbart användar-ID och sessions-ID. Usage: tid, betalare (spender), kvantitet, användningstyp (operationstyp) och krediter; kopierbart användar-arbetsyte-ID. Båda kräver Audit logs. | constants/LogConsolePageViewColumns.tsx, LogConsoleUsageEventColumns.tsx, LogConsoleUsageOperationColumn.tsx, components/LogConsoleCredits*.tsx | Enterprise |
| LKF-010 | Öppna en loggrad i detaljpanel. | Klick på en rad visar en detaljpanel med tid, källans fält, aktörschip med avatar, länk till posten och för posthändelser före/efter-värden fält för fält. | components/LogConsoleDetailPanel.tsx, LogConsoleFieldsCard.tsx, LogConsoleRecordCell.tsx, states/logConsoleSelectedLogState.ts | Enterprise |
| LKF-011 | Anpassa konsolens storlek och kolumner. | Höjden dras med handtag, minst 200 px; helskärmsläge kan slås på; kolumnbredder dras inom min/max-gränser och hålls per kolumn i klientens tillstånd; smalt läge för smala fönster. | constants/LogConsoleHeightConstraints.ts, LogConsoleColumnWidthConstraints.ts, LogConsoleNarrowBodyMaxWidth.ts, states/isLogConsoleFullScreenState.ts, logConsoleColumnWidthsFamilyState.ts, logConsoleHeightState.ts | Enterprise |

### C2. Appövervakning

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-012 | Öppna övervakning för en registrerad app. | Under Inställningar › Applications › (registrering) › Monitoring för den arbetsyta som äger registreringen (kräver API_KEYS_AND_WEBHOOKS enligt API-353); instansadministratören har en motsvarande sida i adminpanelen som visar alla installationer och en kolumn per arbetsyta. | twenty-front/src/pages/settings/applications/SettingsApplicationRegistrationMonitoring.tsx, pages/settings/admin-panel/SettingsAdminApplicationRegistrationMonitoring.tsx, modules/settings/application-monitoring/components/ApplicationMonitoring.tsx | AGPL |
| LKF-013 | Välja period. | Senaste 2 timmar, 24 timmar, 7 dagar (standard enligt API-353), 30 dagar, 90 dagar. Diagrammens tidsaxel går från äldst till nyast. Utan planrättigheten Audit logs visas bara de senaste timmarna enligt planen, med upplysning om att den fulla lagringstiden syns med rättigheten. | modules/settings/application-monitoring/constants/ApplicationMonitoringPeriods.ts, components/ApplicationMonitoringPeriodSelect.tsx, utils/buildApplicationMonitoringPeriodRange.ts | AGPL |
| LKF-014 | Se nyckeltal. | Funktionskörningar och misslyckade körningar ("X av Y körningar misslyckades"), p95-tid i ms, fel, hastighetsbegränsade anrop/jobb, installationer/uppgraderingar/avinstallationer, förbrukade krediter. | components/ApplicationMonitoringKpis.tsx | AGPL |
| LKF-015 | Se diagram över aktivitet, krediter och livscykel. | Linjediagram: körningar och fel över tid; krediter per operationstyp (för ägaren: över alla installationer); livscykel (installationer, uppgraderingar, avinstallationer och deras fel). Heltalsticks på axlarna. | components/ApplicationMonitoringLineChart.tsx, ApplicationMonitoringCreditsSection.tsx, utils/buildApplicationMonitoring{Activity,Credit,Lifecycle}ChartData.ts | AGPL |
| LKF-016 | Se tabeller över funktioner, fel och versioner. | Funktioner: körningar, fel, p95. Toppfel och varningar grupperade per felkod och funktion med nivå och "senast sedd". Versioner: körningar och fel per version. Varje tabell visar högst 10 rader (API-353). | components/ApplicationMonitoringFunctionsTable.tsx, ApplicationMonitoringIssuesTable.tsx, ApplicationMonitoringVersionsTable.tsx | AGPL |
| LKF-017 | Hastighetsgränser i övervakningen. | Visar API-anrop som avvisats och utlösarjobb som hoppats över för att appen nått sin hastighetsgräns; tomt läge "ingen gräns nådd under perioden". | components/ApplicationMonitoring.tsx | AGPL |
| LKF-018 | Tomlägen och fel i övervakningen. | Egna tomlägen per sektion (ingen aktivitet, inga krediter, inga fel eller varningar, ingen funktion körd, ingen installation, ingen version). Laddningsfel ger "kunde inte ladda" och knappen Uppdatera; krediter som inte kunde laddas har eget meddelande. | components/ApplicationMonitoring*.tsx, ApplicationMonitoringFallback.tsx | AGPL |
| LKF-019 | Övervakning kräver analysdatabas. | Utan ClickHouse konfigurerad på servern visas en upplysning om att variabeln för ClickHouse-adressen måste sättas för att samla apploggar och mätvärden; inga diagram visas. | components/ApplicationMonitoringFallback.tsx | AGPL |

### C3. Mediebehörighet i appen

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-020 | Slå på mikrofon/kamera för en inbäddad ram. | En frontkomponent eller iframe-widget som begär media visar en knapp i ramen: "Slå på mikrofon", "Slå på kamera" eller "Slå på mikrofon och kamera". Bekräftelse "Slå på mediaåtkomst för <ägare>?". Bara rättigheter som arbetsytan eller appen godkänt (API-184, AR-336) kan beviljas; en begäran utöver det begränsas. | twenty-front/src/modules/media-access/components/ManagedIframe*.tsx, utils/getManagedIframeMediaPermission.ts, restrictIframeMediaPermission.ts, isIframeMediaPermissionCovered.ts | AGPL |
| LKF-021 | Se att mikrofon eller kamera används. | En indikator (punkt) i appen syns när någon mediasession finns. Rubrik: "Mikrofon eller kamera används" (någon spelar in; punkten markerad), "Begäran om mediaåtkomst" (väntande begäran) eller "Mediaåtkomst påslagen". Hovring öppnar en lista med sessioner grupperade per ägare (app, eller delegerat ursprung). | components/MediaAccessIndicator.tsx, MediaAccessSessionRow.tsx, states/mediaAccessSessionsState.ts | AGPL |
| LKF-022 | Stänga av, avbryta eller stoppa mediaåtkomst. | Per session: "Stäng av mediaåtkomst" (påslagen), "Avbryt mediabegäran" (väntande), "Stoppa inspelning" (pågående). Sessionens tillstånd: väntande, påslagen, inspelning, delegerad. | components/MediaAccessSessionRow.tsx, types/MediaAccessSession.ts | AGPL |
| LKF-023 | Mediaåtkomst följer sidan. | Varje hanterad ram har en egen mediasession som registreras i appens lista över sessioner (troligen så länge ramen är monterad; inte kontrollerat i detalj). Delegerade ursprung (en ram inuti en app) visas separat per ursprung. | components/ManagedIframeMediaAccessSessionEffect.tsx, ManagedIframeSession.tsx, utils/getDelegatedIframeMediaPermission.ts | AGPL |

### C4. Webbläsarnotiser, datamodellfilter och avregistrerade

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-024 | Slå på webbläsarnotiser under Upplevelse. | Kort med tillstånd: "Den här webbläsaren kan inte visa notiser" (stöds inte), "Blockerad i den här webbläsaren" (med uppmaning att tillåta i webbläsarens inställningar), "Notiser är uppsatta", annars knappen "Slå på notiser". | twenty-front/src/modules/settings/experience/components/BrowserNotificationPermissionCard.tsx, SettingsExperienceNotificationsSection.tsx | AGPL |
| LKF-025 | Testa notiser i en uppsättningsdialog. | Dialogen skickar en testnotis och frågar "Såg du en testnotis?". Nej leder till anvisning för systeminställningar (macOS eller Windows, med knapp "Öppna systeminställningar") och en ny test ("Såg du den nu?"); fortfarande nej leder till hjälpguiden. Okänt operativsystem: testknappen är huvudval. | components/BrowserNotificationSetupDialog.tsx, hooks/useSendBrowserTestNotification.tsx, types/BrowserNotificationSetupStep.ts, utils/openInboxNotificationsHelp.ts | AGPL |
| LKF-026 | Välja notisnivå och förhandstext i gränssnittet. | Tre val: "Alla chattar du följer" (varje nytt meddelande i chatt man deltar i eller följer), "Direktmeddelanden och omnämnanden" (inkl. chattar tilldelade en själv), "Av". Reglaget "Visa meddelandeförhandsvisning" visar avsändare, chatt och text; rådet är att ha det av på delade skärmar. (Motsvarar nivåerna i NAV-048.) | components/InboxNotificationPreferences.tsx | AGPL |
| LKF-027 | Filtrera fram nästan tomma fält i datamodellen. | I objektets fältlista finns, utöver "Inaktiva" och "Systemfält", filtret "Mostly empty"; det visas bara när minst ett fält är nästan tomt (eller filtret redan är på). Uppgiften är ungefärlig och bygger på databasens statistik; vid fel visas inget filter. | twenty-front/src/modules/settings/data-model/object-details/components/SettingsObjectFieldTable.tsx, hooks/useMostlyEmptyFieldMetadataIds.ts | AGPL |
| LKF-028 | Regel för "nästan tomt". | Ett fält räknas som nästan tomt när minst 95 % av raderna saknar värde (null eller tomt standardvärde) och objektet har minst 100 poster. Bygger på planerarens statistik, inte en räkning. Kräver läsrätt till poststatistik. | twenty-server/src/engine/metadata-modules/object-metadata/mostly-empty-fields.service.ts, constants/mostly-empty-fraction-threshold.constant.ts, constants/mostly-empty-minimum-row-count.constant.ts, object-metadata.resolver.ts | AGPL |
| LKF-029 | Bläddra i listan över avregistrerade. | Listan hämtas i sidor om 30; tomt läge "Inga avregistrerade hittades"; sök på adress och filter på skäl och ämne enligt MK-L12. | twenty-front/src/modules/settings/unsubscribers/constants/MessageSuppressionsPageSize.ts, components/SettingsUnsubscribersList.tsx | AGPL |

### C5. Egen drift

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-030 | Systemkrav och tjänster vid egen drift. | Minst 2 GB RAM; Docker och Docker Compose. Fyra tjänster: server, worker (bakgrundsjobb; utan den skickas t.ex. inga mejl), databas (PostgreSQL; compose-filen använder version 16) och Redis. Två beständiga volymer: databasdata och serverns lokala lagring. Postgres och Redis publiceras inte utåt i standardfilen. | twenty-docs/developers/self-host/capabilities/docker-compose.mdx; twenty-docker/docker-compose.yml | AGPL |
| LKF-031 | Installera med ett enradsskript. | Skriptet installerar senaste stabila versionen. En viss version anges som fullständig versionstagg (t.ex. v2.38.1); alias som "v2" eller "latest" godtas inte. Versioner till och med v2.9.0 kan inte installeras med skriptet. Ett grenval hämtar konfigurationsfilerna från en gren men behåller senaste avbildningen om inte version också anges. | docker-compose.mdx; twenty-docker/scripts/install.sh, 1-click.sh | AGPL |
| LKF-032 | Installera manuellt. | Steg: skapa miljöfil från exemplet, generera krypteringsnyckel (slumpad, 32 byte), sätt databaslösenord, hämta compose-filen, starta. Förloras krypteringsnyckeln förloras åtkomsten till alla krypterade hemligheter (OAuth-token, appvariabler, tvåfaktorhemligheter). Databaslösenordet får inte innehålla specialtecken eftersom det sätts okodat i anslutningsadressen. Variabler utan standardvärde når servern som tom sträng om de saknas. | docker-compose.mdx | AGPL |
| LKF-033 | Ange serverns adress (SERVER_URL). | Standard localhost:3000. Adressen ska motsvara exakt hur användarna når appen (protokoll, domän/IP, port utom 80/443). Gränssnittet hittar API:t via webbläsarens eget ursprung men SERVER_URL används för länkar m.m. Omstart krävs efter ändring. Bakom omvänd proxy: vidarebefordra till intern port och sätt rätt huvuden. | docker-compose.mdx; troubleshooting.mdx | AGPL |
| LKF-034 | HTTPS krävs för vissa funktioner. | Utan säker kontext fungerar inte t.ex. urklipp (kopieringsknappar). Rekommendation: omvänd proxy med SSL-terminering. | docker-compose.mdx | AGPL |
| LKF-035 | Beständighet. | Volymer håller databas och filer; i tillståndslösa miljöer måste extern lagring (t.ex. S3-kompatibel) konfigureras. | docker-compose.mdx | AGPL |
| LKF-036 | Säkerhetskopiera och återställa. | Databasdump manuellt eller schemalagt dagligen; återställning: stoppa appen, läs in dumpen, starta. Råd: testa återställning, lagra utanför servern, kryptera, behåll dagliga/veckovisa/månatliga kopior. | docker-compose.mdx | AGPL |
| LKF-037 | Uppgradera en egen instans. | Ta säkerhetskopia först; stoppa, byt versionstagg i miljöfilen, starta. Servern kör alla uppgraderingsmigreringar själv vid start. Från v1.23 kan man hoppa direkt till senaste version; äldre instanser måste uppgraderas stegvis per taggad version upp till v1.23. Från v2.34 krävs PostgreSQL 15 eller senare. Misslyckas en arbetsyta stannar servern på det steget och omstart försöker igen. | twenty-docs/developers/self-host/capabilities/upgrade-guide.mdx | AGPL |
| LKF-038 | Se uppgraderingsstatus. | Kommandot `upgrade:status` visar instansens och varje arbetsytas härledda version, senaste körda uppgraderingssteg, status (aktuell, efter, misslyckad), vilken version som körde det och när, plus en sammanfattning. Val: filtrera på arbetsyte-ID (flera gånger), bara efter/misslyckade, och fullständiga identifierare (annars förkortas namn till tre tecken och ID till första delen). | upgrade-guide.mdx | AGPL |
| LKF-039 | Byte till nytt krypteringsformat vid uppgradering. | Från v2.5 lagras hemligheter i ett versionerat krypterat kuvert; första start efter uppgradering skriver om befintliga rader. Omskrivningen är idempotent och återupptas efter avbrott men kan ta tid. Krypteringsnyckeln ska sättas före uppgraderingen; byte efteråt kräver rotation (API-399). | upgrade-guide.mdx | AGPL |
| LKF-040 | Prefix för Redis-cache. | Valfritt, standard tomt (oförändrade nycklar). För klusterade Redis-tjänster som klagar på nycklar i olika fack sätts ett prefix inom klammer på alla servrar, arbetare och kommandon. Byte av prefix ger en ny cachenamnrymd; stoppa alla processer först, gamla poster lämnas orörda. | upgrade-guide.mdx | AGPL |
| LKF-041 | Välja nätverksuppsättning för en privat instans. | Tre val med jämförelse: Tailscale (helt privat, inga öppna portar, inga publika webhooks, inga moln-AI-kopplingar), Cloudflare Tunnel och Access (inga öppna portar, inloggning via identitetsleverantör, publika vägar där det behövs), egen omvänd proxy (port 443, IP-vitlistor, kontor/VPN). Följd av privat instans: molnbaserade automationsverktyg (Zapier, Make, n8n Cloud) når den inte. Vägzonerna i API-400. | twenty-docs/developers/self-host/capabilities/security.mdx | AGPL |
| LKF-042 | Kontrollera uppsättningen och följa checklistan. | Test utifrån: appen, `/graphql` och `/authorize` blockerade; port 3000 nås inte. Inifrån: appen och lokal AI-klient fungerar; ett MCP-anrop utan token ger 401 med upptäcktsadress på den publika HTTPS-adressen (annars vidarebefordrar proxyn inte värd- och protokollhuvudena). Checklista: Postgres/Redis ej publicerade, inget går förbi proxyn (porten bunden till lokal adress), långa slumpade hemligheter, SSO eller tvåfaktor för medlemmar, schemalagd och testad säkerhetskopia, låst versionstagg. Säkerhetsrättelser installeras samma dag vid kritiska fel. | security.mdx | AGPL |
| LKF-043 | Driftartefakter utöver Docker Compose. | Helm-diagram med värdeschema och snabbstart; Kubernetes-manifest (driftsättningar för databas, Redis, server och arbetare; ingress; beständiga volymer) och samma i Terraform; Podman (compose-fil och systemd-tjänst för användare); en Postgres-avbildning baserad på Spilo; provisionering för Grafana och konfiguration för OpenTelemetry-insamlare (mätvärden och spårning). | twenty-docker/helm/twenty/, k8s/manifests/, k8s/terraform/, podman/, twenty-postgres-spilo/, grafana/provisioning/, otel-collector/ | AGPL |
| LKF-044 | Känd felsökning vid egen drift. | Lösenordsfel för databasen vid första installationen: lösenordet sparas i volymen, byte kräver att volymen raderas (bara ny installation). Inga mejl skickas: arbetaren körs inte. Microsoft 365 går inte att ansluta: licens saknas eller personligt konto (stöds inte). Adminpanelen nås inte: användaren måste markeras som full administratör i databasen. Arbetsflöde fallerar med "logikfunktioner avstängda": sätt körmiljön (API-416). AI-chatten svarar först efter omladdning: proxyn buffrar strömmande svar och måste stänga av buffring för strömvägarna. Bilduppladdning nekas: datakatalogens ägare på värden. Kontroll av att arbetaren körs: skapa en webhook (via reglaget Avancerat i inställningarna) och se att en post ger anrop. | twenty-docs/developers/self-host/capabilities/troubleshooting.mdx | AGPL |

### C6. Övrigt

| ID | Funktion | Beteende och regler | Ursprung i förlagan | Licens i förlagan |
|---|---|---|---|---|
| LKF-045 | Planrättigheten Audit logs styr loggarnas räckvidd i flera ytor. | Samma rättighet avgör lagringstid (LKF-004), vilka källor loggkonsolen visar (LKF-002) och hur långt bakåt appövervakningen visar (LKF-013). Utan den: posthändelser och apploggar syns, övrigt inte; 2 timmars lagring. | twenty-front/src/modules/log-console/hooks/useLogConsoleRetention.ts, constants/LogConsoleSources.tsx; modules/settings/application-monitoring | Enterprise |
| LKF-046 | Konsolens posthändelser är fria på alla planer. | Källan Record changes kräver inte Audit logs och fungerar därmed som enkel ändringslogg per post för alla administratörer med SECURITY. (Stämmer med AR-631.) | constants/LogConsoleSources.tsx | Enterprise |
| LKF-047 | Apploggarnas källor. | Sju källtyper med fasta etiketter: logikfunktion, installation, uppgradering, avinstallation, API-hastighetsgräns, jobbhastighetsgräns, serverrutt. Används i både loggkonsolen och appövervakningen. | twenty-front/src/modules/settings/application-monitoring/constants/ApplicationLogSourceLabels.ts | AGPL |
| LKF-048 | Konsolens tidszon. | Konsolen har ett eget tidszonsval som påverkar visade tidpunkter och intervall, oberoende av användarens formatval. | hooks/useLogConsoleTimeZone.ts, states/logConsoleTimeZoneState.ts | Enterprise |
| LKF-049 | Konsolens visningslägen. | Konsolen har ett visningsläge (normal/helskärm), en aktiv källa, valda filter och ett valt tidsintervall som separata tillstånd i klienten. Hur filtren beter sig vid källbyte är inte kontrollerat (se Det jag inte hann läsa). | states/logConsoleDisplayModeState.ts, logConsoleFiltersState.ts | Enterprise |
| LKF-050 | Uppgradering och säkerhetsrättelser för egen drift bevakas manuellt. | Inget inbyggt varningssystem: driftaren ska bevaka releaser och uppgradera samma dag vid kritiska säkerhetsrättelser; sårbarheter rapporteras via säkerhetsadress, inte publika ärenden. | security.mdx | AGPL |
| LKF-051 | Certifierade driftpartner. | Den som inte vill driva själv hänvisas till certifierade värdpartner (partnerkatalogen, UX-248). | docker-compose.mdx | AGPL |
| LKF-052 | Claude-färdighet för att presentera poster. | En färdighet för AI-assistenter som via den anslutna MCP-servern hämtar relevanta poster, upptäcker fält, formaterar datum och värden, bygger postlänkar och svarar som läsbar sammanfattning eller tabell i stället för rå API-utdata. | twenty-claude-skills/skills/twenty-record-presentation/ | AGPL |

## (D) Kataloger utan användarsynlig funktion

| Katalog | Varför |
|---|---|
| twenty-oxlint-rules | Lintregler för förlagans egen kod; ingen användare eller integratör märker dem. |
| twenty-utils | Byggskript (Danger, översättningskontroll, introspektionsfråga, utvecklarmiljö) för förlagans eget projekt. |
| twenty-docs/developers/contribute | Bidragsguide för förlagans utvecklare (lokal miljö, stil, kommandon); ingen produktfunktion. |
| twenty-e2e-testing/lib (utom POM) | Testramverk; beteendet det verifierar står i UX-175–UX-217. |
| front `apollo`, `browser-event`, `metadata-store`, `metadata-error-handler`, `dropdown-context-state-management` | Klientens interna data- och tillståndslager. |
| front `sign-in-background-mock` | Dekorativ bakgrund på inloggningssidan (falsk tabell bakom formuläret); ingen funktion. |
| server `metadata-modules/flat-*`, `data-source`, `deferred-workspace-operation`, `pagination`, `overrides`, `minimal-metadata`, `workspace-metadata-version`, `workspace-feature-flags-map-cache` | Interna cache- och migreringsstrukturer för metadata; beteendet syns via DM-raderna. |
| server `core-modules/{cache-lock,cache-storage,redis-client,environment,exception-handler,guard-redirect,logger,sentry,sql-sanitization,secure-http-client,message-queue,session-storage}` | Infrastruktur; användarsynliga följder (SSRF-skydd, köminne) står i API-417, API-418. |
| server `engine/{core-entity-cache,dataloaders,workspace-cache,workspace-cache-storage,workspace-datasource}` | Prestanda- och anslutningslager. |
| twenty-docs HB-041, HB-389, HB-391–HB-393 | Presentations-, tjänste- och navigeringssidor utan funktion. |
| twenty-docs recept HB-227–HB-230, HB-232, HB-235–HB-237, HB-285, HB-286 | Recept som kombinerar befintliga arbetsflödessteg (twenty-06); ingen egen funktion att bygga. |

## (E) Motsägelser mellan läsarnas filer

| Nr | Motsägelse | Rader | Bedömning |
|---|---|---|---|
| E1 | Formelfält: handboken säger att inbyggda formelfält "kommer 2026" och att formler görs via arbetsflöde; datamodelläsaren beskriver formelfält som finns i koden (uttryck kompileras till SQL, följer namnbyten, egna fel). | HB-067, HB-231 mot DM-150–DM-153 (och DM-156) | Koden går före; troligen bakom flagga eller ej släppt. Avgörs i appen (Oklarheter 3). |
| E2 | @-omnämnanden: handboken säger att de inte stöds i anteckningar och uppgifter; postsidans läsare beskriver "@"-förslag i rik text (kollegor högst 5, poster högst 50), och komponenten används i postens rik text-fält. | HB-226 mot PS-145 | Koden går före; handboken är äldre. |
| E3 | Poster per massanrop: handboken (import) anger 60 poster per batch; koden och exportens FAQ anger tak 200 per anrop och 60 som standardsida. | HB-119, IE-041 mot DM-190, VY-132 | 60 = standard, 200 = tak. Båda kan vara sanna; skriv båda i Snajp-specen. |
| E4 | API-gräns: koden ger 100 anrop/min per arbetsyta (åsidosättbart), webbplatsen 50 (Pro) respektive 100 (Organization). | API-110 mot UX-241, HB-119 | Planskillnaden syns inte i den rad som läst koden; troligen per arbetsyta-inställning i molnet. |
| E5 | Händelseloggens lagringstid: AR-633 anger standard 3 dagar (1–1 095) utan förbehåll; webbplatsen anger 2 timmar på lägre plan. | AR-633 mot UX-240 | Båda stämmer: 2 timmar utan Audit logs, annars 3 dagar som standard. Rättat i LKF-004. |
| E6 | Loggvisning: NAV-098 kallar loggväxeln ren kosmetik; i själva verket öppnar loggfunktionen en fullständig loggkonsol. | NAV-098 mot LKF-001–LKF-011 | NAV-098 beskriver bara växlingsanimationen; konsolen saknades. |
| E7 | Licens för händelseloggen: AR-630 anger "AGPL (insamling) / Enterprise (vy)", AR-818 "Enterprise". | AR-630, AR-818 | Förenligt: insamlingen är AGPL, läsning/rensning (`event-logs.resolver.ts`, `event-logs.service.ts`, `cleanup/`) är Enterprise-märkt. |
| E8 | Fälttyper: handbokens tabell har 18 typer och "20+" utlovas; datamodelläsaren har den slutna uppräkningen i koden. | HB-053, HB-026 mot DM-001 | Kodens uppräkning gäller (twenty-13 Oklarheter 21). |

## (F) Antal funktionsrader

Räknat maskinellt som tabellrader vars första cell är ett ID. "Unika" räknar varje
ID en gång (vissa filer har rättelse- och uppräkningstabeller där ID upprepas) och
utan uppräkningsraderna med prefix U-.

| Fil | Tabellrader med ID | Unika funktions-ID | Uppräkningsrader (U-) |
|---|---|---|---|
| twenty-01 datamodell | 218 | 210 | 0 |
| twenty-02 vyer | 236 | 208 | 25 |
| twenty-03 postsida | 260 | 213 | 29 |
| twenty-04 navigering | 170 | 166 | 0 |
| twenty-05 mejl/kalender | 358 | 347 | 0 |
| twenty-06 arbetsflöden | 310 | 291 | 0 |
| twenty-07 API | 353 | 351 | 0 |
| twenty-08 inloggning/roller | 358 | 346 | 0 |
| twenty-09 import/export | 212 | 203 | 0 |
| twenty-10 dashboards | 202 | 192 | 0 |
| twenty-11 AI/appar | 280 | 271 | 0 |
| twenty-12 UI/flöden | 316 | 304 | 0 |
| twenty-13 handboken | 393 | 393 | 0 |
| **Summa läsare** | **3 666** | **3 495** | **54** |
| twenty-99c (denna fil, LKF) | 52 | 52 | 0 |
| **Totalt** | **3 718** | **3 547** | **54** |

## Det jag inte hann läsa

- Läsarnas filer lästes maskinellt (alla tabellrader) men inte rad för rad med
  ögonen; motsägelser hittades genom riktade sökningar på tal, gränser och
  begrepp. Fler motsägelser kan finnas i regeltexten.
- Täckningen av kataloger avgjordes på katalognamn och begrepp. En katalog med
  många träffar kan ändå ha enskilda filer utan rad; bara kataloger med 0–2
  träffar öppnades.
- Helm-diagrammets värden, Kubernetes-/Terraform-filerna, Podman-tjänsten,
  Grafana-provisioneringen och OpenTelemetry-konfigurationen är bara listade, inte
  lästa i detalj (LKF-043).
- `troubleshooting.mdx` lästes för egen drift; avsnitten om lokal utvecklarmiljö
  (lint, nx, yarn) hoppades över som (D).
- Loggkonsolens `LogConsoleSources.tsx` lästes för etiketter och krav; exakt
  vilka säkerhetshändelser som visas i Security-källan och om konsolen följer
  händelser live (AR-632) har inte kontrollerats i konsolens kod.
- Licensmarkeringen "@license Enterprise" söktes i loggkonsolen,
  appövervakningen, mediebehörigheten, upplevelseinställningarna och serverns
  `event-logs` och `application-monitoring`; träffar bara i `event-logs`.
- Utvecklardokumentationen under `developers/extend` lästes inte om; den täcks av
  twenty-06, twenty-07 och twenty-11 enligt citaten.

## Oklarheter

1. **Enterprise-löften utan kod.** Webbplatsen (UX-237, UX-240) lovar SCIM,
   IP-vitlistning, LTS-versioner, luftgapad drift, VPN, dedikerad beräkning och
   egna API-gränser. Ingen motsvarande katalog finns i `twenty-server/src/engine/core-modules`
   (SCIM och IP-vitlistning söktes utan träff i `auth`, `workspace`, `sso`,
   `enterprise`). Troligen avtals- och driftåtaganden, inte produktfunktioner.
   Snajp behöver inte bygga dem för paritet, men bör veta att de inte finns.
2. **Loggkonsolens live-läge** och om Security-källan visar samma
   händelsetyper som AR-630 räknar upp syns bara i den körande appen med
   Audit logs påslaget.
3. **Formelfält (E1):** finns i koden men handboken säger "kommer". Om fälttypen
   går att välja under "+ New Field" syns bara i appen (twenty-13 Oklarheter 21).
4. **API-gräns per plan (E4):** var planskillnaden 50/100 sätts (konfiguration per
   arbetsyta i molnet eller annan kod) går inte att se i de rader som läst koden.
5. **Appövervakningen** kräver ClickHouse; om den hostade appen har den påslagen
   för vanliga kunder (eller bara för appägare) syns bara i appen.
6. **"Mostly empty"** bygger på databasens statistik och kan visa fel nära
   tröskeln eller efter stora importer innan statistiken uppdaterats; hur ofta
   det sker syns bara i drift.
