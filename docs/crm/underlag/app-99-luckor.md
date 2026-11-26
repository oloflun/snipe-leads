# App-99: Luckgranskningen av app-01 till app-10

Granskning 2026-11-26 för flytten av hela appen till Snajp CRM
(`docs/crm/PLAN-MIGRERING.md`). Bara läst: ingen kod körd, ingen server, inga
tester, ingen git-skrivning. Underlaget är de tio läsarnas filer
`app-01` till `app-10` i den här katalogen; luckorna är lästa direkt i koden.

## Översikt

**Vad filen är till för.** Tio läsare har beskrivit var sitt område av den
nuvarande appen. Den här filen prövar att de tillsammans täcker allt: varje
sida och rutt under `app/`, varje ändpunkt i backenden, varje komponentfil
under `components/` (utom `components/crm/app`, som ÄR det nya gränssnittet,
och `components/marketing`) och varje menypost och inställningsgrupp i
`lib/routes.ts`. Det som inte täcks är öppnat och bedömt; det som bär funktion
har fått egna rader (prefix LX) med samma kolumner som läsarnas.

**Hur granskningen gjordes.**

1. Glob och `find` listade 67 `page.tsx` och 20 `route.ts` under `app/`,
   143 komponentfiler och de 39 routrarna i backenden.
2. För varje fil söktes filnamnet, vägen eller rutten i FUNKTIONSRADERNA
   (tabellrader med sju kolumner) i app-01 till app-10, inte i
   avprickningslistorna. En fil som bara nämns i en avprickningslista räknas
   inte som täckt.
3. Backendens ändpunkter räknades med Grep på dekoratorerna
   (`@router.get|post|put|patch|delete`, `@app.*`, `@mottag.*`) och jämfördes
   väg för väg mot app-10.
4. Det som inte täcktes öppnades och bedömdes: bär det funktion som en
   användare eller administratör märker?
5. Motsägelser letades i läsarnas "Rättat vid kontroll" och "Oklarheter" och
   genom riktade sökningar på tal och regler som förekommer i flera filer; de
   tre viktigaste är kontrollerade mot koden.

**Resultat i korthet.** Täckningen är mycket god. Alla 266 backendrutter, alla
20 route-filer och alla menyposter och inställningssektioner har minst en
funktionsrad. Av sidorna saknar fyra funktionsrader trots att de bär funktion
(`/demo/crm`, `/boka-demo`, `/duo-demo` och den öppna demons ruttabell); av
komponenterna saknar en funktionsrad trots att den bär funktion
(`components/crm/CrmDemo.tsx`, bara nämnd som inbäddare av Email Studio i AP15).
Resten av det otäckta är marknadssidor, juridiska sidor, förhandsvisningar,
designutkast och det nya gränssnittet, som inte ska flyttas som funktion. Tre
motsägelser mellan filerna rör sekretess eller skydd och bör rättas i
källfilerna: vem som ser webbplatsbedömningen (E1), IP-taket på den publika
chatten (E2) och driftdata i supportöversiktens svar (E3).

## Avprickningslista (granskarens egen)

| Del | Status |
|---|---|
| app-01 till app-10: översikt, avprickning, "Sådant som bara finns här", "Rättat vid kontroll", "Det jag inte hann läsa", "Oklarheter" | läst |
| app-10 avsnitt 1–10 (alla AP-rader) | läst |
| Funktionsraderna i app-01 till app-09 | sökta rad för rad med Grep per fil, väg och ID; lästa där en träff skulle bedömas |
| `app/**/page.tsx` (67) och `app/**/route.ts` (20) | avprickade (A1, A2) |
| Backendens dekoratorer i `snajp-support/app/api/*.py` och `app/main.py` | räknade och avprickade (A3) |
| `components/**` utom `components/crm/app` och `components/marketing` (143 filer) | avprickade (A4) |
| `lib/routes.ts` (appRoutes, settingsGroups, sektionsgrindar) | läst och avprickad (A5) |
| `lib/actions/*.ts` (20 filer) | avprickade mot raderna (extra kontroll) |
| `app/demo/[[...slug]]/page.tsx`, `components/crm/CrmDemo.tsx`, `app/boka-demo/page.tsx`, `lib/actions/demo.ts`, `app/duo-demo/page.tsx`, `lib/demo/sektioner.ts` (rad 1–40) | lästa (luckorna) |
| `snajp-support/app/leads/webbpool.py` rad 95–121, `app/api/chat.py` (grindarna), `app/api/snajp-support/kvitton/[[...path]]/route.ts` (grinden) | lästa (kontroll av motsägelser) |
| `components/admin/Radmarke.tsx`, `components/JsonLd.tsx` (storlek, anropare), `components/DesignDrafts.tsx` (anropare), `lib/actions/emails.ts` (export och anropare), `support-webb/app/(portal)/kontakt/page.tsx` | lästa |

## A. Avprickningen

### A1. Sidor (`app/**/page.tsx`, 67 filer)

| Sida | Täckt av |
|---|---|
| `app/page.tsx` (`/`) | AP209 (bara listad): marknadssida, se D |
| `app/admin/page.tsx` | app-09 AD-020–AD-027 |
| `app/admin/[...slug]/page.tsx` | app-09 AD-002, AD-003; app-02 OV-001 |
| `app/admin/agentanvandning/page.tsx` | app-09 AD-093; app-07 KV-172 |
| `app/admin/arbetsyta/page.tsx` | app-09 AD-003; app-02 OV-020 |
| `app/admin/bokforingsanvandning/page.tsx` | app-09 AD-093 |
| `app/admin/handelser/page.tsx` | app-09 AD-090, AD-091 |
| `app/admin/installningar/[[...slug]]/page.tsx` | app-08 IN-002, IN-008; app-09 AD-110 |
| `app/admin/korningar/page.tsx` | app-09 AD-081, AD-082 |
| `app/admin/korningar/[id]/page.tsx` | app-09 AD-083, AD-084 |
| `app/admin/kunder/page.tsx` | app-09 AD-030–AD-036 |
| `app/admin/kunder/[id]/page.tsx` | app-09 AD-040–AD-057 |
| `app/admin/kunder/[id]/data/page.tsx` | app-09 AD-060–AD-063 |
| `app/admin/kunder/[id]/insyn/page.tsx` | app-09 AD-070–AD-077 |
| `app/admin/paket/page.tsx` | app-09 AD-100–AD-105 |
| `app/admin/testkorningar/page.tsx` | app-09 AD-092; app-04 LK-134 |
| `app/ai-agenter/page.tsx` | AP209 (listad): marknadssida, se D |
| `app/ai-supportagent/page.tsx` | AP209 (listad): se D |
| `app/angerratt/page.tsx` | AP210 (listad): juridik, se D |
| `app/auth/reset/page.tsx` | app-01 SK-034–SK-036 |
| `app/avregistrera/[token]/page.tsx` | app-05 LU-141, LU-182 |
| `app/b2b-leads/page.tsx` | AP209 (listad): se D |
| `app/b2b-prospektering/page.tsx` | AP209 (listad): se D |
| `app/boka-demo/page.tsx` | **LUCKA** (bara listad i AP207): LX-010–LX-013 |
| `app/bokforing/page.tsx` | app-07 KV-05 |
| `app/chat/[tenant]/[session]/page.tsx` | app-06 SU-078, SU-079; app-01 SK-155 |
| `app/cookies/page.tsx` | AP210 (listad): se D |
| `app/crm/page.tsx`, `crm/oversikt`, `crm/bolag`, `crm/personer`, `crm/synk`, `crm/utvecklare` (6 sidor) | AP204 (listade) + API-raderna AP146–AP150c: det nya gränssnittet, se D |
| `app/dashboard/[[...slug]]/page.tsx` | app-01 SK-095; app-02 OV-001 och alla vyrader i app-02–app-07 |
| `app/demo/[[...slug]]/page.tsx` | delvis: app-01 SK-078, app-02 OV-043, app-03 LR-095, app-06 SU-115; **LUCKA** för `/demo/crm` (LX-001–LX-008) och ruttabellen (LX-014) |
| `app/design-drafts/[variant]/page.tsx` | AP212 (listad): designutkast, se D |
| `app/design-drafts/[variant]/portal/[[...slug]]/page.tsx` | AP212 (listad): se D |
| `app/duo-demo/page.tsx` | **LUCKA** (bara listad i AP207): LX-015 |
| `app/embed/[nyckel]/page.tsx` | app-06 SU-091–SU-095; app-01 SK-022 |
| `app/faq/page.tsx` | AP209 (listad): se D |
| `app/forhandsvisning/crm/[[...vy]]/page.tsx` | AP211 (listad): se D |
| `app/forhandsvisning/exempelbolag/page.tsx` | AP211: se D |
| `app/forhandsvisning/iris-granskning/page.tsx` | AP211: se D |
| `app/forhandsvisning/konversationer/page.tsx` | AP211: se D |
| `app/forhandsvisning/korningens-utkast/page.tsx` | AP211; nämnd i app-04: se D |
| `app/forhandsvisning/kundinstallningar/page.tsx` | AP211: se D |
| `app/forhandsvisning/leads-skickat/page.tsx` | AP211: se D |
| `app/forhandsvisning/leads-snabbsok/page.tsx` | AP211: se D |
| `app/forhandsvisning/listutkast/page.tsx` | AP211; nämnd i app-04: se D |
| `app/forhandsvisning/meny/page.tsx` | AP211: se D |
| `app/forhandsvisning/samtal/page.tsx` | AP211: se D |
| `app/forhandsvisning/webbpool/page.tsx` | AP211; app-09 AD-121: se D |
| `app/integritetspolicy/page.tsx` | AP210: se D (länkas från SK- och LU-rader) |
| `app/jamfor-ai-sdr/page.tsx` | AP209: se D |
| `app/jamfor-supportagenter/page.tsx` | AP209: se D |
| `app/kvitton/page.tsx` | app-07 KV-174 |
| `app/leads-i-inkorgen/page.tsx` | AP209: se D |
| `app/leads/page.tsx` (marknad) | AP208; Email Studio-exemplet i AP15: se D |
| `app/login/page.tsx` | app-01 SK-130–SK-138 |
| `app/onboarding/page.tsx` | app-01 SK-110–SK-127 |
| `app/settings/[[...slug]]/page.tsx` | app-08 IN-001–IN-009 |
| `app/support-pa-svenska/page.tsx` | AP209: se D |
| `app/support/page.tsx` (marknad) | app-06 SU-214, SU-215; AP8 |
| `app/supportchatt/page.tsx` | AP209: se D |
| `app/svensk-ai-sdr/page.tsx` | AP209: se D |
| `app/vart-team/page.tsx` | AP209: se D |
| `app/villkor/page.tsx` | AP210: se D |

Utöver sidorna: felgränser och laddningslägen (`app/**/error.tsx`,
`loading.tsx`, `not-found.tsx`, `global-error.tsx`) täcks av app-01 SK-155 och
SK-156; layouterna (`app/admin/layout.tsx`, `app/crm/layout.tsx`,
`app/dashboard/layout.tsx`, `app/settings/layout.tsx`) av SK-040, SK-041,
SK-020, AD-002 och IN-001. `app/robots.ts`, `sitemap.ts`, `manifest.ts`: AP242
och SK-010.

### A2. Rutter (`app/**/route.ts`, 20 filer)

| Rutt | Täckt av |
|---|---|
| `app/api/snajp-support/[...path]/route.ts` | AP1; SU-200–SU-202; IN-015 |
| `app/api/snajp-support/chat/route.ts` | AP2; SU-070, SU-088 |
| `app/api/snajp-support/chat/samtal/route.ts` | AP3; SU-078 |
| `app/api/snajp-support/jobs/[jobId]/route.ts` | AP4; SU-088 |
| `app/api/snajp-support/testchatt/route.ts` | AP5; SU-007 |
| `app/api/snajp-support/testchatt/samtal/route.ts` | AP6 |
| `app/api/snajp-support/testchatt/jobb/[jobId]/route.ts` | AP6 |
| `app/api/snajp-support/leads/jobb/[jobId]/route.ts` | AP7; LK-038 |
| `app/api/snajp-support/triage/route.ts` | AP8; SU-214 |
| `app/api/snajp-support/kvitton/[[...path]]/route.ts` | AP9; KV-04 |
| `app/api/snajp-support/bookkeeping/[...path]/route.ts` | AP10; KV-150 och följande |
| `app/api/admin/[...path]/route.ts` | AP11 |
| `app/api/admin/kunder/route.ts` | AP12; SK-074 |
| `app/api/agentsajt/[agent]/sso/route.ts` | AP13; SU-100, SU-218 |
| `app/api/auth/[...nextauth]/route.ts` | AP14; SK-023 och följande |
| `app/api/email-studio/route.ts` | AP15 |
| `app/api/health/route.ts` | AP16 |
| `app/chat/[tenant]/route.ts` | AP17 |
| `app/prova/[token]/route.ts` | AP18; LU-173 |
| `app/llms.txt/route.ts` | AP20 |

`proxy.ts` (inloggningsgrinden och CSP för inbäddning): AP19, SK-020.

### A3. Backendens ändpunkter (registret app-10)

Grep på dekoratorerna ger **265 rutter med `@router`/`@app`** plus **1 med
`@mottag`** (flyttmottagaren i `admin_flytt.py`) = **266 rutter** i 38
routermoduler (39 routerobjekt; `admin_flytt.py` har två). app-10 säger "39
routrar och 3 egna rutter i `app/main.py`", vilket stämmer räknat i
routerobjekt. Varje väg nedan är jämförd mot app-10; ingen saknas.

| Router (antal rutter) | Vägarna | Täckt av |
|---|---|---|
| `main.py` (3) | `/health`, `/health/live`, `/health/ready` | AP21 |
| `chat.py` (3) | POST `/api/chat`, POST `/api/chat/samtal`, GET `/api/jobs/{id}` | AP22–AP24 |
| `chattar.py` (4) | GET lista, GET en, POST svar, POST återlämna | AP25–AP28 |
| `support_config.py` (2) | GET/PUT `/api/support/config` | AP29 |
| `support_oversikt.py` (1) | GET `/api/support/oversikt` | AP30 |
| `integrationer.py` (6) | GET, POST, PATCH, DELETE, GET verktyg, POST prova | AP31, AP32; IN-160–IN-165 |
| `kanaler.py` (7) | GET, POST, PATCH, DELETE, POST prova, GET/POST webhook | AP33, AP34 |
| `triage.py` (1) | POST `/api/triage` | AP35 |
| `tickets.py` (2) | GET ärende, GET kundhistorik | AP36 |
| `keys.py` (1) | POST `/api/keys` | AP37 |
| `kb.py` (7) | GET, POST, DELETE, POST skanna, GET förslag, POST beslut, POST extrahera | AP38–AP40 |
| `inbox.py` (15) | mock, mailboxes (GET, upptäck, POST, DELETE), sync, ingest, GET inbox, sortera, klassa, GET ett, takeover, hanterad, processa-om, befordra | AP41–AP46, AP238 |
| `drafts.py` (3) | approve, omformulera, reject | AP47 |
| `rules.py` (2) | GET/PUT `/api/rules` | AP48 |
| `sending_domains_api.py` (5) | POST/GET sending-domain, verify, två Resend-webhooks | AP49, AP50 |
| `demo.py` (1) | POST `/api/demo/chat` | AP51; SU-219 |
| `analytics.py` (1) | GET weekly | AP52 |
| `usage.py` (1) | GET `/api/usage` | AP53, AP239 |
| `leads.py` (69) | context-docs (2), onboarding (3), prospects (13 inkl. fordelning, utkast, sources, befordra, degradera, PATCH, processa-om, exempel), soul (2), onskemal (4), research/step, outreach/draft, runs, svar (2), uppfoljning/svep, forslag (4), feedback (2), skickat (2), config (2), erbjudanden (2), demobesok, profil (2), jev/statistik, korningar (7 inkl. styrning och utkast), queue (7), provmejl (2), runs/batch, listor (8) | AP60–AP96, AP235–AP237 |
| `leads_suite.py` (13) | tidslinje, samtal (3), anteckningar, uppgifter (3), vyer (3), import (2) | AP100–AP105 |
| `leads_konversationer.py` (13) | konversationer (10), notiser (3) | AP106–AP109 |
| `leads_uppfoljningar.py` (3) | uppfoljningar (2), sok | AP110, AP111, AP235, AP236 |
| `leads_massatgard.py` (3) | arkivera, radera, DELETE lista | AP95, AP96 |
| `leads_kampanjer.py` (5) | lista, en, skapa, skicka, skicka-jobb | AP112 |
| `admin.py` (15) | tenants, runs (3), insyn, skills/fil, kb-prov, kedja, events, inbox, leads-underlag, drafts, usage, sandvag (2) | AP120–AP127 |
| `admin_profil.py` (9) | instruktioner (4), profil (2), aktiv, status, kb/badda-in | AP131–AP134 |
| `admin_kunddata.py` (5) | kunddata (2), kontakter (3) | AP129 |
| `admin_gallring.py` (2) | gallring, kundens gallring | AP130 |
| `admin_konvertera.py` (1) | konvertera | AP135 |
| `admin_ombedom.py` (1) | leads-ombedom | AP128 |
| `admin_webbpool.py` (2) | GET/POST bakatfyll | AP136 |
| `admin_utkastsvep.py` (1) | normalisera-utkast | AP137 |
| `admin_listor.py` (1) | till-kund | AP138 |
| `admin_flytt.py` (4 + 1) | status, kandidater, paket, skicka; `mottag`: importera | AP139, AP140, AP240 |
| `drift.py` (1) | GET `/api/drift/schema` | AP141, AP241 |
| `kvitton.py` (12) | mejlkonto, skanna, skanning (2), lista, sammanfattning, period, underlag, godkann, riktning, export.csv, chat | AP142–AP144 |
| `bookkeeping.py` (7) | underlag (2), period (2), period.sie, chat, avstamning | AP145 |
| `crm.py` (4) | nycklar (3), oversikt | AP146, AP147, AP234 |
| `crm_v1.py` (29) | me, companies (6), people (6), connections (7), sync (8), openapi.json | AP148–AP150c, AP231–AP233 |

### A4. Komponenter (143 filer)

Första tre funktionsraderna som bär filen; fler finns ofta.

| Fil | Täckt av |
|---|---|
| `components/AgentSajtKnapp.tsx` | SK-097, SU-002, SU-100 |
| `components/AgentSajtLank.tsx` | SU-100 |
| `components/AppShell.tsx` | SK-005, SK-060, SK-061 |
| `components/DesignDrafts.tsx` | **ej täckt**: designutkast, se D |
| `components/EjAktiverad.tsx` | SK-157, OV-038, OV-048 |
| `components/Felgrans.tsx` | SK-007, SK-044, SK-155 |
| `components/ImpersonationBanner.tsx` | SK-076, AD-009 |
| `components/InstalleraApp.tsx` | SK-150, SK-153 |
| `components/JsonLd.tsx` | **ej täckt**: strukturerad data för sökmotorer, se D |
| `components/Laddar.tsx` | SK-045, SK-156, OV-011 |
| `components/LasrollBanner.tsx` | SK-077, IN-014 |
| `components/Logo.tsx` | **ej täckt som fil**: loggan, se D |
| `components/SoulEditor.tsx` | SU-140, IN-040, IN-041 |
| `components/VyVaxel.tsx` | SK-075, AD-006, AD-007 |
| `components/WorkspaceViews.tsx` | OV-080, OV-101, OV-102 |
| `components/admin/AdminShell.tsx` | SK-064, SK-072, AD-002 |
| `components/admin/AdminText.tsx` | AD-150 |
| `components/admin/AdminVyhuvud.tsx` | AD-030, AD-080 |
| `components/admin/AgentAnvandning.tsx` | AD-093 |
| `components/admin/Agentinstruktioner.tsx` | IN-135, IN-136, IN-137 |
| `components/admin/Avstangning.tsx` | AD-051, AD-134 |
| `components/admin/BytKund.tsx` | SK-074, AD-006, AD-010 |
| `components/admin/FelOchEskaleringar.tsx` | AD-037, AP124 |
| `components/admin/FlyttTillMain.tsx` | SK-074, AD-053, AD-055 |
| `components/admin/HandelseOversikt.tsx` | AD-090 |
| `components/admin/Handelselista.tsx` | AD-091, AD-130, AP124 |
| `components/admin/KonverteraTestkund.tsx` | AD-050, AP135 |
| `components/admin/KorningsOversikt.tsx` | AD-082, AP121 |
| `components/admin/KostnadOversikt.tsx` | AD-093 |
| `components/admin/KundHuvud.tsx` | AD-040 |
| `components/admin/Kunddata.tsx` | SK-151, IN-142, AD-061 |
| `components/admin/KunderOversikt.tsx` | AD-031, AD-032, AD-033 |
| `components/admin/Kundprofil.tsx` | AD-042, AD-043, AD-044 |
| `components/admin/Kundtabell.tsx` | AD-034, AD-035, AP120 |
| `components/admin/OppnaArbetsyta.tsx` | AD-011 |
| `components/admin/PaketHantering.tsx` | KV-171, KV-204, AD-052 |
| `components/admin/PaketOversikt.tsx` | AD-100 |
| `components/admin/Portfoljvy.tsx` | AD-020, AD-021, AD-022 |
| `components/admin/Radgivare.tsx` | AD-026 |
| `components/admin/Radmarke.tsx` | inte nämnd vid namn, men funktionen (märkena Testarbetsyta, Inaktiv, Exempel) står i AD-024 och AD-034 |
| `components/admin/Testkorningar.tsx` | LK-134, AD-092 |
| `components/admin/Tillaggsvaljare.tsx` | AD-049 |
| `components/admin/insyn/Flodeskarta.tsx` | AD-071 |
| `components/admin/insyn/Insynsvy.tsx` | AD-072, AD-073, AD-074 |
| `components/admin/insyn/Kallmatris.tsx` | AD-075 |
| `components/admin/insyn/KbProv.tsx` | AD-077 |
| `components/admin/insyn/Lagerstapel.tsx` | AD-074, AD-084 |
| `components/auth/LoginForm.tsx` | SK-023, SK-026, SK-031 |
| `components/auth/OnboardingWizard.tsx` | SK-110, SK-111, SK-112 |
| `components/auth/ResetPasswordForm.tsx` | SK-035, SK-036, SK-137 |
| `components/auth/SignOutButton.tsx` | SK-037, SK-138, IN-011 |
| `components/crm/CrmDemo.tsx` | **LUCKA**: bara AP15 (som inbäddare av Email Studio); LX-001–LX-008 |
| `components/dashboard/AgentLast.tsx` | SK-096, OV-008, OV-016 |
| `components/dashboard/Aktivitet.tsx` | OV-020, OV-021, OV-022 |
| `components/dashboard/Analys.tsx` | OV-101, OV-107, AP52 |
| `components/dashboard/DashboardContext.tsx` | SK-042, SK-070, SK-094 |
| `components/dashboard/KomIgang.tsx` | OV-044, OV-045, OV-047 |
| `components/dashboard/OversiktPaneler.tsx` | OV-022, OV-023, OV-033 |
| `components/dashboard/StartView.tsx` | SK-095, OV-001, OV-020 |
| `components/dashboard/WorkspaceSection.tsx` | SK-043, SK-062, SK-095 |
| `components/demo/DemoBesok.tsx` | LU-173, LU-174, AP18 |
| `components/email/EmailStudioEditor.tsx` | LR-065, LU-033, AP15 |
| `components/kvitton/Integritetsnotis.tsx` | KV-12, KV-45 |
| `components/kvitton/KvittoChatt.tsx` | KV-60, KV-61, KV-62 |
| `components/kvitton/KvittoDemo.tsx` | KV-173, KV-174 |
| `components/kvitton/KvittoDemoYta.tsx` | KV-173 |
| `components/kvitton/KvittoFlikar.tsx` | KV-10 |
| `components/kvitton/KvittoOversikt.tsx` | KV-50, KV-51, KV-52 |
| `components/kvitton/KvittoVy.tsx` | KV-10, KV-11, KV-12 |
| `components/kvitton/KvittoYta.tsx` | KV-20, KV-21, KV-22 |
| `components/leads/AgentLarande.tsx` | OV-080, OV-083, OV-084 |
| `components/leads/AttGora.tsx` | OV-006, OV-060, OV-061 |
| `components/leads/BekraftaUtskick.tsx` | LR-043, LR-047, LR-057 |
| `components/leads/BolagsSok.tsx` | LR-080, LR-081, LR-082 |
| `components/leads/Bolagsregister.tsx` | OV-103, LR-100, LR-101 |
| `components/leads/Bolagssida.tsx` | OV-103, LR-110, LR-111 |
| `components/leads/CrmKundlista.tsx` | LR-011, LR-133, LK-147 |
| `components/leads/DemoKorning.tsx` | LK-015, LK-130, LK-131 |
| `components/leads/ExempelbolagDemo.tsx` | LK-132 |
| `components/leads/ImportLista.tsx` | LR-122, LK-100, LK-101 |
| `components/leads/IrisAutomation.tsx` | LK-069, LK-070, LK-071 |
| `components/leads/IrisBolag.tsx` | LR-001, LR-060, LR-063 |
| `components/leads/IrisErbjudanden.tsx` | LU-174, AP80, AP81 |
| `components/leads/IrisEskalering.tsx` | LU-117, IN-101, IN-102 |
| `components/leads/IrisGranskning.tsx` | LR-024, LU-030, LU-032 |
| `components/leads/IrisInkorg.tsx` | LU-080, IN-110, AP78 |
| `components/leads/IrisInstallningar.tsx` | IN-100, IN-107 |
| `components/leads/IrisKorningar.tsx` | OV-027, LK-020, LK-021 |
| `components/leads/IrisProdukter.tsx` | IN-103, IN-104, IN-105 |
| `components/leads/IrisProfil.tsx` | LK-060, LK-061, LK-062 |
| `components/leads/Kampanjer.tsx` | LU-160, LU-161, LU-162 |
| `components/leads/Kontakter.tsx` | OV-104, LR-113, AP63 |
| `components/leads/Konversationer.tsx` | LR-003, LU-001, LU-002 |
| `components/leads/KonversationsTrad.tsx` | LU-006, LU-007, LU-008 |
| `components/leads/KorningensUtkast.tsx` | LK-034, LK-035, LK-036 |
| `components/leads/LeadsControls.tsx` | LK-064, LK-065, LK-137 |
| `components/leads/LeadsDiagram.tsx` | OV-033, OV-036, LR-114 |
| `components/leads/LeadsOversikt.tsx` | LR-020, LR-021, LR-022 |
| `components/leads/LeadsRunForm.tsx` | LR-006, LK-001, LK-002 |
| `components/leads/LeadsSida.tsx` | LR-001, LR-003, LR-004 |
| `components/leads/LeadsSnabbsok.tsx` | LK-016, AD-092, AP90 |
| `components/leads/LeadsTabell.tsx` | LR-021, LR-030, LR-032 |
| `components/leads/LeadslistorView.tsx` | LR-120, LR-121, AD-123 |
| `components/leads/ProvmejlKnapp.tsx` | LU-037, LU-087, AP89 |
| `components/leads/Saljlista.tsx` | LK-117, LK-118, LK-148 |
| `components/leads/Samtalslista.tsx` | LU-130, LU-133, LU-134 |
| `components/leads/SkickatLista.tsx` | LR-049, LU-082, LU-083 |
| `components/leads/StrukturVal.tsx` | LR-068, LK-003, LU-159 |
| `components/leads/Svar.tsx` | LU-089, OV-105, AP74 |
| `components/leads/Tidslinje.tsx` | LR-069, LU-137, LU-171 |
| `components/leads/Uppfoljningar.tsx` | LR-044, LU-100, LU-101 |
| `components/leads/sidindelning.tsx` | LR-037, LR-058 |
| `components/leads/smal.tsx` | SK-067, SK-073, OV-066 |
| `components/leads/useRadrorelse.ts` | LR-038, LR-059 |
| `components/settings/AddonSettings.tsx` | IN-093 |
| `components/settings/Affarskontext.tsx` | IN-020, IN-021, IN-022 |
| `components/settings/AgentOnskemal.tsx` | SU-151, SU-216, IN-061 |
| `components/settings/Inkorgar.tsx` | SU-160, SU-161, IN-070 |
| `components/settings/Kunskapsbas.tsx` | SU-120, SU-121, IN-030 |
| `components/settings/NotisSettings.tsx` | IN-120, IN-121 |
| `components/settings/PlanSettings.tsx` | IN-090, IN-091, IN-092 |
| `components/settings/SettingsNav.tsx` | IN-005, IN-006, IN-008 |
| `components/settings/SettingsSection.tsx` | IN-001, IN-002, IN-007 |
| `components/settings/SupportEskalering.tsx` | SU-142, SU-143, SU-144 |
| `components/settings/SupportRegler.tsx` | SU-141, IN-050, IN-051 |
| `components/settings/TeamSettings.tsx` | IN-080, IN-081, IN-082 |
| `components/settings/TemaSettings.tsx` | IN-123, IN-124 |
| `components/settings/Tvafaktor.tsx` | SK-048, IN-130, IN-131 |
| `components/settings/Vaxel.tsx` | SU-148, IN-058 |
| `components/settings/WebbplatsForslag.tsx` | OV-045, SU-127, IN-034 |
| `components/shell/Rail.tsx` | SK-060, SK-063, AD-002 |
| `components/snajp/AgentMenu.tsx` | SK-065, SK-067, SK-068 |
| `components/snajp/Dashboard.tsx` | SU-010 och följande, OV-066, OV-067 |
| `components/snajp/DemoSupportYta.tsx` | SU-115, SU-116 |
| `components/snajp/EmbedYta.tsx` | SU-092, SU-094 |
| `components/snajp/InboxTriage.tsx` | SU-117, SU-214, AP8 |
| `components/snajp/IntegrationSection.tsx` | SU-110, SU-119, IN-109 |
| `components/snajp/JournalVy.tsx` | SU-119, AP25, AP53 |
| `components/snajp/SnajpSupportDemo.tsx` | SU-119 (oanvänd) |
| `components/snajp/SupportChat.tsx` | SU-007, SU-070, SU-071 |
| `components/snajp/SupportOversikt.tsx` | SU-050, SU-051, SU-052 |
| `components/snajp/SupportWorkspaceTabs.tsx` | SK-097, OV-010, SU-003 |
| `components/ui.tsx` | byggstenar (knappar, märken, tabeller); bärs av rader i alla filer, t.ex. SK-010, LR-036 |

### A5. Menyposter och inställningsgrupper (`lib/routes.ts`)

| Post | Täckt av |
|---|---|
| Översikt `/dashboard` | OV-020; SK-095 |
| Att göra `/dashboard/att-gora` | OV-060–OV-079 |
| Leads `/dashboard/leads` | LR-001 och hela app-03–app-05 |
| Kundtjänst `/dashboard/support` | SK-097; SU-003 och hela app-06 |
| Bolag `/dashboard/companies` (preview) | OV-103; LR-100 |
| Kontakter `/dashboard/contacts` (preview) | OV-104; LR-113 |
| Inkorg `/dashboard/inbox` (preview) | OV-105; LU-089 |
| Lärande `/dashboard/larande` (preview) | OV-080–OV-089 |
| Analys `/dashboard/analytics` (preview) | OV-101, OV-107 |
| Assistent `/dashboard/assistant` (preview) | OV-102 |
| Kvitton `/dashboard/kvitton` (vilande, `VILANDE_PRODUKTER`) | KV-01, KV-02; SK-063 |
| CRM `/crm` (`adminOnly`) | SK-061; app-01 Oklarheter (dold länk, inte grind) |
| Inställningar `/settings` | IN-001 |
| Filtret per produkt, läge och preview (`routesForProducts`) | SK-061, SK-062, OV-100 |
| `tillAdminvag` och `useArbetsvag` | SK-072, AD-003 |
| Grupp Företaget: Företaget, Vad ni säljer, Kunskapsbas, Så ska agenten låta | IN-012, IN-020, IN-030, IN-040 |
| Grupp Iris: Målgrupp och automation | IN-100; LK-060–LK-073 |
| Grupp Kundtjänst: När agenten får svara själv, Inkorgar | IN-050, IN-070; SU-141, SU-160 |
| Grupp Plattformen (`adminOnly`): Globala agentinstruktioner, Tvåstegsverifiering | IN-008, IN-130–IN-137; AD-110 |
| Grupp Kontot: Team (`doldIDemo`), Plan och fakturering, Tillägg, Notiser, Tema | IN-009, IN-080, IN-090, IN-093, IN-120, IN-123 |
| Sektionsgrindarna (`settingsSectionForSlug`, `sektionKraverAdmin`, `sektionDoldIDemo`, `productForSettingsSection`, `produktForInstallningsvag`) | IN-001, IN-007, IN-008, IN-009; SK-094 |
| `publicProductRoutes`, `protectedRoutePrefixes`, `authRoutes` | SK-020, AP19 (de publika produktsidorna: se D) |

### A6. Extra kontroll: serveråtgärderna (`lib/actions/*.ts`)

Alla 20 filer bärs av minst en funktionsrad (AP181–AP186 och läsarnas rader).
Två undantag inom filerna: `demo.ts:bokaDemo` har ingen rad (LX-011) och
`emails.ts:refineEmail`/`persistEmailDraft` har inga anropare alls (D).

## B. Luckorna och deras allvarlighet

| Lucka | Allvarlighet | Varför |
|---|---|---|
| CRM-listdemon `/demo/crm` (`components/crm/CrmDemo.tsx`) | Medel | Svarar publikt men står inte i någon meny. Det är den enda befintliga prototypen av "kundens egen CRM-lista in, en isolerad Email Studio per kund ut", alltså nära det nya CRM:ets import och utkast per bolag. Ingen läsare beskrev den; den som bygger CRM-importen och utkasten per bolag bör känna till den (eller besluta att den ska bort). |
| Demobokningen `/boka-demo` och tabellen `demo_requests` | Medel | Formuläret sparar namn, e-post, företag och meddelande från besökare, och INGEN vy läser tabellen (bara `scripts/gdpr_radera.py` rör den). Personuppgifter samlas alltså in utan att någon ser dem. Plattformsadmin i CRM:et bör få en lista, eller formuläret bytas mot Cal.com. |
| Den öppna demons ruttabell (`/demo/<sektion>`) | Låg | Vilka sektioner som finns, vilka gamla adresser som leder vidare och att `?drift=1` visar driftrutan står bara utspritt. Behövs om CRM:et ska kunna visas i demon (app-01 punkt 11). |
| `/duo-demo` | Låg | Publik sida med översikten för båda agenterna på exempeldata. Bara listad i AP207. |
| Läsrollens och kundbesökets spärr saknas i kvittoproxyn | Låg (vilande produkt) | Beskriven i AP9 men inte i app-07 (KV-04). Se E4. Ingen ny rad behövs, men KV-04 bör kompletteras. |

## C. Funktionsrader för luckorna

| ID | Funktion | Beteende och regler | Vy och komponent | Ändpunkt och lagring | Roll och sekretess | Tvåspråkig |
|---|---|---|---|---|---|---|
| LX-001 | Besökaren öppnar CRM-listdemon utan inloggning. | Adressen `/demo/crm` renderar rubriken "CRM-lista"/"CRM list" i demoskalet (samma `PageShell` och `DashboardProvider` som övriga demon, `signedIn:false`, produkterna leads och support). Posten står INTE i demons meny sedan Leads › Listor › Importera CSV tog över (`lib/demo/sektioner.ts`), men adressen svarar. På en kunds egen domän: 404 (`notFoundOnTenant`). Ingen session och ingen databas får nås. | `app/demo/[[...slug]]/page.tsx` (fallet `crm`), `components/crm/CrmDemo.tsx` | Inga backendanrop | Anonym | ja |
| LX-002 | Besökaren laddar upp en kundlista som CSV, som läses i webbläsaren. | "Välj CSV-fil". Filen läses med `fil.text()` och `lib/leads/csv.ts:parseCsv`; rubrikraden mappas på synonymer (svenska och engelska) till Företag, Kontaktperson, E-post, Orgnr, Ort, Webbplats, Telefon och Notering/signal; varje fält tas av första matchande kolumn. Rader utan företagsnamn hoppas över, dubbletter (samma företagsnamn, skiftlägesokänsligt, även mot redan inlästa) hoppas över, tak 500 kunder. Besked: "N kunder importerade" + ", N dubbletter hoppades över" + ", N rader utan företagsnamn hoppades över" + ", N rader över demons tak på 500 kunder lästes inte in", samt "Kolumner:" och "Ignorerade:". Fel: "Filen gick inte att läsa som en kundlista. Den behöver en rubrikrad och minst en rad med ett företagsnamn." / "Filen gick inte att läsa. Prova att exportera om den som CSV." Inget laddas upp till någon server. | `CrmDemo.tsx` (`importeraCsv`, `mappaRubriker`, `FALTSYNONYMER`, `MAX_KUNDER`) | – | Anonym; listan lämnar aldrig webbläsaren | ja (mejltexterna med flit svenska) |
| LX-003 | Besökaren laddar in en exempellista. | "Ladda in exempellistan" hämtar den statiska filen `/demo/crm-exempel.csv` och läser den som en uppladdad fil; "Hämtar…" under tiden, dubbelklick ignoreras. Fel: "Exempellistan gick inte att hämta just nu. Prova igen om en stund." | `CrmDemo.tsx:laddaExempel` | statisk fil `public/demo/crm-exempel.csv` | Anonym | ja |
| LX-004 | Besökaren tömmer listan med dubbelbekräftelse. | Första klicket på "Töm listan" byter knappen till röd text "Klicka igen: listan och alla utkast raderas"; andra klicket tömmer kunder, öppnade studior, valda signaler, importbeskedet och alla utkast. | `CrmDemo.tsx:tomLista` | localStorage | Anonym | ja |
| LX-005 | Listan och affärsprofilen finns kvar efter omladdning i samma webbläsare. | Sparas i `localStorage` under nyckeln `snajp-demo-crm` som `{profil, kunder}`; läses först efter första renderingen (ingen hydreringskrock). Utkasten sparas inte (de lever i editorns tillstånd). | `CrmDemo.tsx` | `localStorage` | Bara den egna webbläsaren | – |
| LX-006 | Besökaren beskriver sin produkt och affärsidé, som Email Studio läser inför varje omskrivning. | Fyra fält: "Vad ni säljer och varför" (högst 800 tecken), "Erbjudandet, i en kort fras" (160), "Er webbplats" (200), "Önskat nästa steg (CTA)" (200). Förifyllt med en exempelprofil (påhittat bolag, larm och brandskydd). Texten är bakgrund för ton och vinkel, "aldrig som text att klistra in i mejlet"; ändringar slår igenom i nästa knapptryck utan att nollställa utkasten. | `CrmDemo.tsx` (`STANDARDPROFIL`) | localStorage | Anonym | ja |
| LX-007 | Besökaren söker i kundlistan och väljer en kund (lista till vänster, detalj till höger). | Sök "Sök företag, kontakt, ort …" filtrerar på företag, kontakt, e-post, ort och notering (delsträng, skiftlägesokänsligt). Räknare "1 kund"/"N kunder". Tomläge: "Ingen lista inläst ännu. Välj en CSV-fil ovan, eller börja med exempellistan." Inga träffar: "Inga kunder matchar sökningen." Klick öppnar kundens panel bredvid listan utan att listan flyttar sig; på smal skärm (under 1024 px) ligger panelen under listan och sidan rullar dit. Utan vald kund: "Välj en kund i listan. Här visas kundens signaler och en Email studio som är isolerad till just den kunden." | `CrmDemo.tsx` (`filtrerade`, `valjKund`, `KundDetalj`) | – | Anonym | ja |
| LX-008 | Kundens panel visar fakta, signaler och en egen Email Studio. | Fakta ur listan. "Signaler och affärsmöjligheter": noteringen som signal "CRM-notering" och EN simulerad signal per bolag (vald deterministiskt ur namnet: platsannons, expansion eller nytt uppdrag), var och en med en möjlighetstext; märkningen säger att nyhets- och annonsraden är simulerad i demon. "Skriv på signalen" väljer signal; den valda märks "Används i mejlet". Studion är isolerad per kund ("Studion är isolerad till {företag} … Inget skickas från demon."): varje öppnad kunds editor hålls monterad och döljs bara, så utkast blandas aldrig. Knapparna går till Email Studio, som för anonyma alltid svarar med handskrivna exempel utan modell (AP15). | `CrmDemo.tsx`, `components/email/EmailStudioEditor.tsx` | `POST /api/email-studio` (anonym, `simulated:true`) | Anonym; inget skickas, ingen modell körs | ja |
| LX-010 | Besökaren bokar en demo via Cal.com när kalendern är inkopplad. | Med `NEXT_PUBLIC_CAL_LANK` satt visas Cal.coms bokningssida i en iframe (månadsvy, laddas lat) och en reservrad "Går kalendern inte att ladda? Mejla oss så bokar vi manuellt." med mejllänk (ämne "Boka demo"). Inga tredjepartsskript i sidan. Sidan finns inte på en kunds domän (404). | `app/boka-demo/page.tsx` | Cal.com (extern) | Anonym | delvis (sidans rubrik, ingress och punkter bara svenska) |
| LX-011 | Besökaren skickar en demoförfrågan i formuläret när Cal.com inte är inkopplad. | Fält: Namn (obligatoriskt, 120 tecken), Företag (valfritt, 160), E-post (obligatoriskt, 254, enkel formkontroll), Tid som passar (valfritt, 200, "Till exempel ”tisdag förmiddag”."), Vad vill ni titta på? (valfritt, 2000). Dold honungsfälla `webbplats`: ifylld → svaret ok utan att något sparas. Dolt fält `kalla` (sidan formuläret står på, standard `/boka-demo`). Fel: "Fyll i ditt namn.", "Fyll i din e-postadress.", "E-postadressen ser inte ut att stämma. Kontrollera den gärna.", utan databas "Vi kan inte ta emot bokningen just nu. Mejla oss så återkommer vi.", vid databasfel "Något gick fel när vi skulle spara förfrågan. Mejla oss så tar vi det den vägen." Lyckat: "Tack, vi har din förfrågan." och att en människa hör av sig. Inget bekräftelsemejl skickas (Next-appen har ingen utskicksväg för det). Integritetsrad med länk till integritetspolicyn. | `components/marketing/BokaDemoFormular.tsx`, `lib/actions/demo.ts:bokaDemo` | INSERT `public.demo_requests` (namn, foretag, epost, onskad_tid, meddelande, kalla) som webbrollen utan `returning` (insert-policy öppen, ingen select-policy; migration 050) | Anonym; personuppgifter | delvis (formuläret ja, serverns fel bara svenska) |
| LX-012 | (Saknas) Någon läser demoförfrågningarna. | Ingen vy, ingen notis och inget mejl till Snajp när en förfrågan sparas. Tabellen läses bara av GDPR-raderingen. Förfrågningar kan alltså bli liggande obesvarade. | – | `demo_requests`; `scripts/gdpr_radera.py` | Plattformsadmin borde se dem | – |
| LX-013 | Demoförfrågningar raderas vid GDPR-radering av en person. | `scripts/gdpr_radera.py` tar med `demo_requests` (på e-post). | – | `scripts/gdpr_radera.py` | Driftägaren | – |
| LX-014 | Den öppna demon har en fast uppsättning sektioner och leder gamla adresser rätt. | `/demo` → översikten; `/demo/leads` (Iris-listan, ingen undersektion), `/demo/att-gora`, `/demo/installningar` (bara Iris profil och målgrupp), `/demo/support` (kundtjänsten med kundchatt; `?drift=1` visar admins driftruta), `/demo/regler` (När agenten får svara själv), `/demo/companies`, `/demo/contacts`, `/demo/inbox`, `/demo/analytics`, `/demo/assistant`, `/demo/crm` (LX-001). Omdirigeringar: `/demo/aktivitet` → `/demo`; `/demo/iris` → `/demo/leads`, `/demo/iris/pipeline` → `/demo/leads?vy=pipeline`, `/demo/iris/granskning` → `/demo/att-gora`, `/demo/iris/installningar` → `/demo/installningar`; `/demo/emails` → `/demo/leads`; `/demo/kontroll` → `/demo/installningar`; `/demo/kvitton` och `/demo/bokforing` → `/demo` (kvitton vilande, så AgentLasts länk "Prova i demon först" för kvitton landar på översikten). Okänd sektion eller oväntad undersektion → 404. Tillståndet är en konstant (aldrig plattformsadmin, aldrig session); `DemoBesok` registrerar besök från spårade demolänkar (AP18). | `app/demo/[[...slug]]/page.tsx`, `lib/demo/sektioner.ts` | Inga (exempeldata i webbläsaren) | Anonym; får aldrig nå session eller databas | ja (rubrikerna) |
| LX-015 | Besökaren ser Duo-översikten (båda agenterna) på exempeldata. | `/duo-demo`: översikten (`StartView` med `demo`) för en påhittad arbetsyta med leads och support, utan inloggning och utan anrop; 404 på kundens domän. Metadata "Snajp Duo — båda agenterna i samma vy". Finns för säljsamtal och granskning. | `app/duo-demo/page.tsx`, `components/dashboard/StartView.tsx` | Inga | Anonym | ja (vyerna) |

## D. Filer utan användarsynlig funktion (eller utanför uppdraget)

| Fil eller grupp | Varför den inte behöver funktionsrader |
|---|---|
| Marknadssidorna `/`, `/ai-agenter`, `/ai-supportagent`, `/b2b-leads`, `/b2b-prospektering`, `/faq`, `/jamfor-ai-sdr`, `/jamfor-supportagenter`, `/leads-i-inkorgen`, `/support-pa-svenska`, `/supportchatt`, `/svensk-ai-sdr`, `/vart-team`, och produktsidorna `/leads`, `/support` | Webbplatsen, inte appen; byggs av `components/marketing` som uppdraget undantar. De delar som bär appfunktion (Email Studio-exemplet AP15, inkorgsdemon SU-214, marknadschatten SU-215) har rader. Ska inte flyttas in i CRM:et. |
| `/angerratt`, `/cookies`, `/integritetspolicy`, `/villkor` | Juridisk text. Länkas från appen (chattmenyn, onboardingen, inloggningen) och måste fortsätta finnas på samma adresser, men bär ingen funktion. |
| `/crm` och dess fem undersidor, `app/crm/layout.tsx` | Det nya gränssnittet. Komponenterna (`components/crm/app`) är undantagna i uppdraget; CRM-API:t har rader (AP146–AP150c, AP231–AP234). |
| `app/forhandsvisning/**` (12 sidor) | Förhandsvisningar för okulär granskning utan backend (projektregeln "titta med egna ögon"). Anropen besvaras i webbläsaren; ingen användare når dem i arbetet. |
| `app/design-drafts/**`, `components/DesignDrafts.tsx` | Designutkast (landningssida och portal i varianter). Ingen appfunktion. |
| `components/JsonLd.tsx` | 17 rader: skriver strukturerad data (`application/ld+json`) för sökmotorer på marknadssidorna. |
| `components/Logo.tsx` | Snajps logga som komponent (railen, onboardingen, marknaden). Utseende, inte funktion; DESIGN-CRM bestämmer loggan i CRM:et. |
| `components/admin/Radmarke.tsx` | 23 rader: neutral `Badge` bredvid ett kundnamn. Märkenas innebörd står i AD-024 och AD-034. |
| `components/ui.tsx` | Byggstenar (knappar, märken, radlistor). Beteendet beskrivs där de används. |
| `lib/actions/emails.ts` (`refineEmail`, `persistEmailDraft`) | Serveråtgärderna har inga anropare i `app/`, `components/` eller `lib/` (Email Studio går via `app/api/email-studio`). Död kod; AP15 och AP186 nämner `refineEmail` som om den användes. |
| `components/snajp/SnajpSupportDemo.tsx`, `JournalVy.tsx`, `IntegrationSection.tsx` | Oanvända enligt SU-119 (ersatta av Aktivitet 2026-10-03). |
| `support-webb/app/(portal)/kontakt/page.tsx` | Portalens kontaktsida: bara en mejllänk till Snajps kontaktadress. |
| `app/robots.ts`, `app/sitemap.ts` | Sökmotormetadata (AP242). |

## E. Motsägelser mellan läsarnas filer

| # | Motsägelse | Vad koden säger | Rättas i |
|---|---|---|---|
| E1 | app-10 (översikten, avsnittet "Sekretess, webbplatsbedömningen") säger att `webbpool.far_se` är "sann bara för plattformsadmin och webbyråkunderna". app-03 (Oklarhet 1), app-04 (rättelsen av LK-114) och app-09 (AD-120, Oklarhet 1) säger att grinden går på ARBETSYTANS slug, inte på rollen. | `webbpool.py:108–116`: `far_se` jämför tenantens slug och id mot `synliga()` (`WEBBBEDOMNING_SYNLIG` eller `SYNLIGA`, plus mottagarna och inspirationskunden). Ingen rollkontroll. Plattformsadmin ser alltså bedömningen bara i en arbetsyta vars slug står i listan, och i kundbesök hos webbyråerna. app-03/04/09 har rätt. | app-10. Viktigt: CLAUDE.md säger "BARA för plattformsadmin och kunderna Umeå Webdesign och Alunix"; det nya gränssnittet måste avgöra om plattformsadmin ska se bedömningen som ROLL (vilket koden inte gör i dag). |
| E2 | app-10 AP2 säger "rate limit per IP i backenden" för den publika chatten, och AP226 listar IP-taket "demons IP 30 svar/h" med AP2 och AP5 som vyer. app-06 SU-088 (rättad vid kontroll) säger att det INTE finns något IP-tak på `/api/chat`. | `chat.py` rad 253: `rate_limit_db.scopes_for(tenant_id, x_snajp_user, is_demo=…)`, ingen IP. IP-taket finns bara på `/api/demo/chat`, som ingen vy anropar. app-06 har rätt; en besökare kan bränna kundens timtak. | app-10 (AP2, AP226) |
| E3 | app-09 AD-138 anger Driftrutan i supportöversikten som "Bara admin (eller explicit påslaget)". app-06 SU-063 (rättad vid kontroll) säger att bara VYN är grindad: API-svaret bär `drift` (tokens, cacheandel, modell) till varje kund. | Belagt av app-06 mot `support_oversikt.py` rad 181–186. | app-09 AD-138 (Roll-kolumnen bör säga att datan når alla kunder). |
| E4 | app-07 KV-04 beskriver kvittoproxyns grind (inloggning och produkten `bookkeeping`, annars 404) utan att nämna läsroll och kundbesök. app-10 AP9 (kontroll 2026-11-26) säger att proxyn saknar läsrollsspärren och `is_test`-märkningen och gör om även POST/DELETE. | `kvitton/[[...path]]/route.ts`: `resolveDashboardState` + `requireSnajpTenant`, ingen `proxyAsTenant`; tre försök oavsett metod. AP9 har rätt. | app-07 KV-04 bör kompletteras. |
| E5 | app-01 (Oklarheter) säger att "vem som skickar notismejlen (`lead`, `escalation`) och om de respekterar `notification_preferences` avgörs i backenden, som inte lästs här". app-08 (Oklarhet 2, belagt vid kontroll) säger att INGEN kod läser tabellen: inga notismejl skickas alls. | app-08 är belagt; app-01:s oklarhet är besvarad av app-08. | app-01 kan hänvisa till app-08. |
| E6 | app-03 (rättelse 10, LR-007/LR-120) säger att `vy === "admin"` betyder den egna arbetsytan för VARJE inloggad användare. app-08 (IN-009, Oklarhet 1) säger att Team döljs för vanliga kunder eftersom `SettingsNav` sätter `vy="kund"` för alla som inte är plattformsadmin. | Båda stämmer: det finns två olika "vy"-begrepp i koden (serverns `aktivVy()` i `lib/vy.ts` och det `SettingsNav` skickar till `settingsGroupsForProducts`). Det är en inkonsekvens i koden, inte i läsningen, men det nya gränssnittet måste välja EN betydelse. | Beslut vid bygget (Anton för Team). |
| E7 | app-02 (OV-020–OV-043) räknar kostnad i kronor ur tokens till listpris; app-09 (AD-093, AD-138) räknar kostnad i USD på Vertex-listpris för en annan modell. | Två kostnadsmodeller i koden; app-09 Oklarhet 2 tar upp det, app-02 nämner det inte. | Beslut (Anton). |
| E8 | app-02 OV-016 och app-07 KV-03 anger demolänken `/demo/kvitton` ("Prova i demon först") som om den visar kvittodemon. | `app/demo/[[...slug]]/page.tsx` leder `/demo/kvitton` och `/demo/bokforing` till `/demo` (kvitton vilande). Länken landar på översikten. | app-02, app-07 (en mening). |
| E9 | app-10 säger "39 routrar"; app-10 AP-raderna räknar rutterna per fil. | 38 routermoduler, 39 routerobjekt (`admin_flytt.py` har `router` och `mottag`), 266 rutter. Ingen verklig motsägelse, men talet bör anges med enheten. | app-10 (precisering). |
| E10 | app-05 (Oklarhet 11) noterar att kön säger "vardagar från 08:00", Ändra tid "vardagar 08–16" och sändspärren "8–17"; app-10 AP88/AP237 anger bara "vardagar 08–16". | Kallmejl 08–16, svar i en svarad tråd till 17 (app-05). AP88/AP237 är riktiga för kallmejl men nämner inte svarsfönstret. | app-10 (precisering). |

Inga motsägelser hittades i jobbens tidsgräns (600 s i AP24, AP160 och KV-193),
provperioden (2 kalendermånader i AP165, AD-134 och AD-141) eller
`LISTRADSFALT` (AP138, AD-123, LR-132).

## F. Antal funktionsrader

Räknat som tabellrader med sju kolumner och unikt ID (rättelsetabeller och
sidlistan AP200–AP213 inte medräknade). Inga dubbletter av ID inom en fil.

| Fil | Prefix | Funktionsrader |
|---|---|---|
| app-01 skal, inloggning, onboarding | SK | 121 |
| app-02 översikt, att göra, lärande | OV | 85 |
| app-03 leads: översikt, pipeline, bolag | LR | 104 |
| app-04 leads: körningar, listor, källor | LK | 132 |
| app-05 leads: utkast, konversationer, samtal | LU | 129 |
| app-06 support | SU | 176 |
| app-07 kvitton | KV | 141 |
| app-08 inställningar | IN | 109 |
| app-09 adminytan | AD | 116 |
| app-10 API under ytorna | AP | 179 (+ 14 sidrader AP200–AP213) |
| app-99 luckor (denna fil) | LX | 14 |
| **Totalt** | | **1 306** (1 292 från läsarna + 14 här) |

## Det jag inte hann läsa

- Funktionsraderna i app-01 till app-09 lästes inte i sin helhet rad för rad;
  de söktes med Grep per fil, väg, rutt och ID, och lästes där en träff skulle
  bedömas. En rad som beskriver en fil med fel namn (felstavat filnamn) kan
  därför ha räknats som lucka eller missats; kontrollen av de fyra
  komponenterna som först såg otäckta ut visar att träffsäkerheten är god.
- Läsarnas egna "Det jag inte hann läsa" är inte omlästa i koden. De viktigaste
  kvarvarande: `support-webb` UI-delar (Hemligheter, Kanaler, System), stora
  delar av `support_agent.py` och `processor.py` (app-06), `discovery.py`,
  källorna och Jev i detalj (app-04), `tilltal.py`, `send_provider.py`,
  `stilkontroll.py` och `follow_up_generator` (app-05), `granskning.py`
  mitten och `bookkeeping/math.py` (app-07), `insyn.py` och renderingen i
  insynsvyn (app-09).
- `components/marketing/BokaDemoFormular.tsx` lästes bara via texterna och
  fältnamnen (LX-011), inte rad för rad.
- `lib/demo/sektioner.ts` efter rad 40 (demons menyposter) och
  `public/demo/crm-exempel.csv` (innehållet).
- `lib/` i övrigt (utöver `routes.ts`, `actions/*` och det luckorna krävde)
  avprickades inte fil för fil; det låg utanför de fyra kategorierna.

## Oklarheter

1. **Ska `/demo/crm` leva kvar?** Den står inte i menyn men svarar, och den är
   närmaste förebild för CRM:ets "egen kundlista + utkast per bolag". Behåll,
   flytta in i CRM-demon eller ta bort: Antons beslut.
2. **Demoförfrågningarna läses inte av någon** (LX-012). Ska plattformsadmin
   få en lista i CRM:ets adminsektion, ska en notis eller ett mejl gå till
   Snajp, eller ska Cal.com kopplas in (TODO i `app/boka-demo/page.tsx`: konto
   på cal.com och `NEXT_PUBLIC_CAL_LANK`)? Om tabellen redan har rader går
   bara att se i databasen.
3. **Plattformsadmin och webbplatsbedömningen** (E1): projektregeln och koden
   säger olika. Ska CRM:et grinda på roll (plattformsadmin ser alltid) eller
   fortsatt på arbetsytans slug? Antons beslut; påverkar varje ny vy som visar
   prospekt eller listrader.
4. **IP-tak på den publika chatten** (E2): routens kommentar lovar ett,
   koden har inget. Hör till widgetvägen i CRM:et.
5. **Driftdata i supportöversiktens API-svar** (E3): ska ändpunkten grinda
   `drift` på plattformsadmin innan CRM:et läser den?
6. **Död kod i `lib/actions/emails.ts`** och `lib/actions/auth.ts:startDemo`,
   `requestDemoAccess` (app-01): ska de tas bort före flytten så att ingen
   bygger på dem?
