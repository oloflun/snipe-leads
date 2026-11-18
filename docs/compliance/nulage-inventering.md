# Nulägesinventering: dataskydd och regelefterlevnad, Snajp

**Repo:** `C:\Users\Anton L\snipe-leads`, gren `development`, HEAD `545dca1b` (2026-11-17 18:56).
**Gjord:** 2026-11-17, endast läsning. Inga skript, migrationer eller anrop mot development/main har körts. Inga hemligheter har lästs: `.env`-filer har bara listats på variabelnamn.
**Syfte:** underlag för Comp AI (leverantörer, risker, policyer, bevis) inför första betalande kund.

**Metod och begränsningar.**
- Påståenden är belagda med fil och radnummer. Där belägg saknas står "inget belägg hittat".
- Allt som bara går att se i Railway, Google Cloud, Redis Cloud, Resend eller Render (regioner, avtal, variabelvärden, om en tjänst lever) är **inte verifierat** här. Repot visar avsikt och historik, inte driftläget.
- `bd` (beads) gick inte att fråga: `bd search` svarar "Dolt server unreachable … dolt is not installed", och `.beads/issues.jsonl` saknas. Ärendestatus (t.ex. `snipe-a1c`) är därför inte kontrollerad.
- `docs/JURIDIK_ATGARDER.md` är daterad 2026-08-24 (rad 6) och har inte ändrats sedan dess, enligt `git log`. Flera av dess påståenden har passerats av senare händelser, se avsnitt 3.

---

## 1. Bolaget

### 1.1 Bolagsuppgifterna i `lib/bolag.ts`

| Fält | Värde | Status | Belägg |
|---|---|---|---|
| `namn` | "Snajp" (enskild firma) | Ifyllt | `lib/bolag.ts:37-38`; ändrat av Sebbe 2026-10-17 (`f04134f6`, "firmanamnet är Snajp (enskild firma), inte Snajp AB") |
| `orgnr` | `[XXXXXX-XXXX]` | **Platshållare** | `lib/bolag.ts:39` |
| `postadress` | `[Gatuadress, postnummer, ort]` | **Platshållare** | `lib/bolag.ts:40` |
| `policyUppdaterad` | `[DATUM]` | **Platshållare** | `lib/bolag.ts:42` |
| `DATASKYDD_MEJL` | `[integritet@snajp.se]` | **Platshållare** | `lib/bolag.ts:46` |
| `bolagsuppgifterna_klara` | `false` | Följd av ovan | `lib/bolag.ts:102-106`; bekräftas i `components/marketing/Sidfot.tsx:34` |
| Region för alla underleverantörer utom Supabase | Platshållare med interna anvisningar | **Platshållare** | `lib/bolag.ts:130-133, 139, 149, 157-159, 166-168, 181-183` |

**Notera:** firman är en enskild firma. Dess organisationsnummer är ägarens personnummer. Att publicera det på sajten och i varje utskick är ett beslut som bara ägaren kan fatta. Alternativet är att bolagisera (AB) innan kunder tas in.

### 1.2 Kontaktadressen
- Publik kontaktadress är numera `kontakt@snajp.se` (`components/marketing/copy.ts:35`, införd `b8534989` 2026-08-29). P0.3d i JURIDIK_ATGARDER (som säger att `Snajpsupport@gmail.com` är enda kontaktväg) är därmed **delvis passerad**.
- `DATASKYDD_MEJL` är fortfarande platshållare. `dataskyddKontakt()` faller därför tillbaka på `kontakt@snajp.se` (`lib/bolag.ts:77-79`; `app/integritetspolicy/IntegritetspolicySida.tsx:109`).
- Widgetens eskalering och supportadress är fortfarande Gmail: `SNAJP_SUPPORT_EPOST = "snajpsupport@gmail.com"` (`components/snajp/AgentMenu.tsx:28`). Interna larm skickas via `smtp.gmail.com` (`snajp-support/app/notifications/prioriterat_mejl.py:80`).

### 1.3 Varningsrutor och "Förstautkast"
- **Den gula utkastrutan är borttagen** ur `/integritetspolicy`, `/villkor` och `/cookies` (`components/marketing/JuridiskSida.tsx:14-16`, "borttagen på begäran (2026-08-25)").
- **Sidfotens platshållarruta är också borttagen.** Platshållare utelämnas i stället (`lib/bolag.ts:13-24`; `components/marketing/Sidfot.tsx:29-34`).
- JURIDIK_ATGARDER påstår fortfarande att rutorna visas (rad 308-309 och 314-317). **Det stämmer inte längre.**
- **Följden:** de juridiska sidorna ser färdiga ut för en besökare men är inte juristgranskade. Den enda markeringen är en TODO för utvecklare (`app/integritetspolicy/page.tsx:20-33`). "Senast uppdaterad" visas inte alls (`JuridiskSida.tsx:49-58`).
- `/villkor` säger öppet att "Pris och betalning", "Ansvarsbegränsning" och "Uppsägningstid" inte är fastställda (`app/villkor/VillkorSida.tsx:59-61, 76-79, 81-84`; motivering i `app/villkor/page.tsx:17-30`).

---

## 2. Underbiträden och leverantörer (härlett ur koden)

Källor: `snajp-support/requirements.txt`, `package.json`, `snajp-support/app/config.py` (fält rad 158-559), variabelnamn i koden och i `.env.deploy` (bara namn), samt utgående värdnamn i koden.

Kolumner:
- **bolag.ts** = finns i `UNDERLEVERANTORER` (`lib/bolag.ts:124-185`).
- **Reg.** = finns i `docs/registerforteckning.md`.
- **PA B1** = finns i pilotavtalets Bilaga 1 (`docs/pilotavtal.md:149-161`).

### 2.1 Underbiträden som behandlar kunddata eller personuppgifter i drift

| # | Leverantör | Vad som går dit | Region (känd) | DPA/SCC/DPF dokumenterad? | bolag.ts | Reg. | PA B1 | Belägg |
|---|---|---|---|---|---|---|---|---|
| 1 | **Google Cloud, Vertex AI** (Gemini 2.5 flash/pro, embeddings, vision) | **Kundens kundmejl** (supportagenten, maskerat personnummer), chattar, kvitton och bilder, leads-research (prospekts sidor, kontaktnamn), utkast | `europe-west1`, reserv `europe-west4`, `europe-north1` (bara EU enligt kod). Main bekräftat på Vertex europe-west1 i BESLUT 2026-10-21 | **Nej.** Ingen DPA/CDPA-bekräftelse i repot. Faktureringskonto kopplat enligt GOALS.md:80-87 | Ja, men som "Google (Gemini)" med platshållarregion | Ja ("Google/Gemini"), utan region | Ja ("verifieras") | `config.py:179-186`; `agent/llm.py:24-36, 183-201, 309-325`; `docs/BESLUT.md:1469-1471, 1993-2009`; `HANDOFF-2026-09-12-VERTEX-AI.md:14-21, 41-44` |
| 1b | **Google, Gemini grounded search** (`google_search`-verktyget på Vertex) | Sökprompter i leads-discovery (bolagskriterier, ort). Ingen kundmejltext | Anropet går till europe-west1. Groundingens egen behandling: **ej verifierad** | Nej | (ingår i 1) | Nej | Nej | `leads/discovery.py:484-517` |
| 1c | **Google AI Studio** (`GEMINI_API_KEY`, `generativelanguage.googleapis.com`) | Reservväg för chatt, vision, embeddings och sökning när service account saknas | Ej angiven. **Gratisnivå** enligt HANDOFF-2026-09-12 rad 5-12; BESLUT 2026-10-21 rad 1501-1503 och 1523 säger "krediten är slut (402)" | Nej | Nej (som egen post) | Nej | Nej | `agent/llm.py:55, 321-336`; `leads/discovery.py:502-507`; `config.py:172-173` |
| 2 | **Railway** | All drift: web, api och Postgres med all kunddata, i två miljöer (`main` plus `development`, som är en fullständig spegel) | **Okänd.** `scripts/railway_region.py` gav "okänd" 2026-09-13 (`docs/pilotavtal.md:154`) | Nej | Ja, platshållarregion | Ja, "[fylls i]" | Ja | `DEPLOY.md`; `CLAUDE.md` (dev = spegel); `scripts/railway_provision.py:330` |
| 3 | **Redis Cloud (Redis Ltd)** | Jobbkö och cache: pågående chatt- och leadsjobb inklusive agentens svar (TTL 1 h), arbetsminne och svarscache | `europe-west1` (verifierat 2026-08-29 enligt JURIDIK rad 359-360). **TLS av** vid senaste belägg (`HANDOFF-2026-08-31-TESTISOLERING.md:47, 80`) | **Nej**, DPA ej tecknad enligt JURIDIK rad 362 | Ja, platshållare | Ja | Ja | `config.py:254`; `requirements.txt` (redis) |
| 4 | **Resend** | Utgående mejl: supportsvar till slutkunder, kallmejl från leads, interna larm. Webhook för studs och klagomål | Domäner skapas med `region: eu-west-1` (`sending_domains.py:50`). Bolaget är amerikanskt | **Nej** | Ja, platshållare | Ja | Ja ("Resend (EU)") | `leads/send_provider.py:252-268, 329-374`; `sending_domains.py:8, 50`; `docs/BESLUT.md:1415-1418` |
| 5 | **ScrapeGraphAI** | Prospekts publika sidor (kontakt och om oss: namn, titlar, arbetsmejl), skärmbilder för webbrevision, merinfo-sidor | Ej bekräftad | **Nej** ("flaggat till Anton 2026-09-02") | Ja | Ja (A2b) | Ja | `agent/research_tools.py`; `leads/sidhamtning.py`; `leads/webbrevision.py`; `lib/bolag.ts:170-184`. Kontot har nästan slut på krediter (BESLUT rad 2017) |
| 6 | **TypeSafe (api.typesafe.ai), modellen "Jev"** | Leads: prospekts bolagsdata och sidutdrag med e-post och telefon bortfiltrerade. **Inkorg, om `INKORG_JEV` är prov eller auto: kundmejlens text** utan adresser, plus avsändardomänen | **Okänd** | **Nej** | **NEJ, saknas** | **NEJ** | **NEJ** | `leads/jev.py:1-35, 51, 63-77, 88-95`; `email_pipeline/klassning.py:23-30, 111-116`; `config.py:339-344` |
| 7 | **GitHub (Microsoft)**, Actions-runners | **Produktionens persondata passerar runnern var tionde minut** (`synk.yml`: tvåvägssynk main↔development). Hela `.env.deploy` med alla nycklar ligger som Actions-secret `ENV_DEPLOY`. Dessutom källkod och migrationskörning | USA (GitHub-hostade runners) | Nej | **NEJ** | **NEJ** | **NEJ** | `.github/workflows/synk.yml:15-17, 37-44`; `migrera.yml:79-81`; `docs/BESLUT.md:2212-2218` |
| 8 | **Supabase** | Historisk databas och GoTrue-auth från den gamla stacken. Används bara om `NEXT_PUBLIC_SUPABASE_URL` är satt (`lib/supabase-auth.ts:3-10`). Gamla Supabase-databasen (`aws-1-eu-west-1.pooler.supabase.com`, JURIDIK rad 244) **innehåller sannolikt historisk kunddata**, och Supabase-grenen står i MIGRATIONS_FAILED | Irland, EU | Nej | Ja, som "Databaslagring och autentisering" (troligen inaktuellt) | Ja (A1, A2, B1) | Nej (bilagan säger "stryk eller lägg till") | `lib/bolag.ts:141-145`; `docs/pilotavtal.md:159-161`; `AUTH.md` (Supabase-flödet beskrivs fortfarande) |
| 9 | **Render** (gamla stacken) | Två tjänster (`snajp-support`, `snajp-support-dev`) med DeepSeek-nyckeln blankad, simuleringsläge, kopplade till gamla Supabase. **Inget belägg för att de är suspenderade eller raderade** | USA (troligen) | Nej | **NEJ** | **NEJ** | Nej | JURIDIK rad 195-287; `STATUS.md:1045-1046` ("tystade men inte avstängda"); `snajp-support/render.yaml` ligger kvar; `RENDER_API_KEY` och `PREVIEW_RENDER_SERVICE_ID` finns kvar i `.env.deploy` (bara namn lästa) |

### 2.2 Leverantörer och källor som inte behandlar kunddata för kundens räkning (Snajp är ansvarig eller det rör bara offentlig bolagsdata)

| Leverantör/källa | Vad | Personuppgifter? | I dokumenten? | Belägg |
|---|---|---|---|---|
| allabolag.se (direkthämtning, inget avtal) | Bolagsregistret, filter. "Hövlig hämtning tills ett API-avtal finns" | Bolagsnivå. Personnamn i sökträffar används inte som kontakt | Nej (bara i BESLUT) | `leads/sources/allabolag.py`; `docs/BESLUT.md:2011-2030`; `docs/utkast-allabolag-api-forfragan.md` (otrackad) |
| merinfo.se (via ScrapeGraph) | Register, filter | Bolagsfakta; personuppgifter filtreras bort (`bolagsfakta_text`) | Nej | `leads/sources/merinfo.py`; CLAUDE.md leadsregel 1, 6, 9 |
| hitta.se (direkthämtning) | Kontaktkälla på org.nr (telefon, e-post) | Ja, kan vara en persons nummer | Nej | `leads/katalog.py:1-106` |
| JobTech (Arbetsförmedlingen) | Platsannonser som köpsignal | Nej (offentliga annonser) | Nej | `leads/sources/jobtech.py` |
| Nyheter/RSS, Mynewsdesk | Bolagshändelser | Kan innehålla namn | Nej | `leads/sources/nyheter.py` |
| Google PageSpeed Insights | Publik URL | Nej (`config.py:250-252`) | Nej | `leads/webbrevision.py` |
| Cloudflare DNS-over-HTTPS | DNS-uppslag i mejlpollern | Domännamn | Nej | `email_pipeline/poller.py` (cloudflare-dns.com) |
| Loopia | DNS för snajp.se | Nej | Nej | `scripts/loopia_dns.py` |
| IndexNow | Sitemap-pingar | Nej | Nej | `scripts/indexnow.py` |
| Cal.com (villkorad iframe) | Demobokning om `NEXT_PUBLIC_CAL_LANK` är satt | Ja (besökarens bokning) | Nej | `app/boka-demo/page.tsx:20-27, 43, 70` |
| Google och Microsoft Entra ID (inloggning) | OAuth-inloggning om `AUTH_GOOGLE_ID` eller `AUTH_MICROSOFT_ENTRA_ID_ID` är satt | Ja (identitet) | Nej | `lib/auth.ts:3-4, 143-144` |
| Anthropic | Bara benchmarkskript mot syntetiska fixtures | Nej i drift | Nej | `scripts/benchmark_leads_kedja.py:1-31` |
| OpenAI | Konfigurerad men "inte i drift" | Nej i drift (ej verifierat) | Ja i bolag.ts | `lib/bolag.ts:135-140`; `lib/llm/modellval.ts` (OpenAI först i ordningen om en nyckel sätts) |
| DeepSeek | Spärrad i varje miljö med riktig data | Nej (spärr) | Ja (CLAUDE.md) | `config.py:609-700`; `lib/llm/modellval.ts:189-197` |
| Stripe | Borttaget; manuell fakturering | – | – | `supabase/migrations/20260921110000_076_stripe_bort.sql:1-15` |
| Sentry/felspårning, analys | **Finns inte** | – | – | `docs/BESLUT.md:390`; `docs/stabilitet-2026-11/SLUTRAPPORT.md:164`; cookiesidan säger "inga analyscookies" |

### 2.3 Integrationer som kunden själv slår på (kundens egna konton)
Detta är mottagare på kundens instruktion, inte Snajps underbiträden. De bör ändå nämnas i PUB-avtalet (GOALS.md:263-267 ställer samma fråga).
- **IMAP och OAuth mot Gmail och Microsoft 365**: kundens inkorg och kvittomejl. `config.py:400-425`; `kvitton/mejl.py` (gmail.googleapis.com, graph.microsoft.com).
- **Meta (WhatsApp och Messenger), Slack, Microsoft Teams**: `kanaler/meta.py`, `kanaler/slack.py`, `kanaler/teams.py`.
- **HubSpot och Pipedrive**: envägssynk av bolag och anteckningar. `leads/crm_synk.py:1-27`.
- **Kundens egna MCP- och HTTP-integrationer**: `integrationer/mcp_klient.py`. Nycklarna är krypterade med Fernet (`GOALS.md:255-262`).

### 2.4 Diskrepanser

**I koden men saknas i dokumenten:**
1. **TypeSafe/Jev** saknas i bolag.ts, registerförteckningen, pilotavtalets bilaga och integritetspolicyn. Den kan få kundmejltext (inkorgsläget).
2. **GitHub Actions** flyttar produktionsdata var tionde minut. Leverantören står inte någonstans.
3. **Render** kan fortfarande leva och saknas i alla förteckningar.
4. **Vertex AI** står som "Google (Gemini)". Avtalsnivån skiljer sig mellan Vertex och AI Studio, och den reservväg mot AI Studio som finns kvar nämns inte.
5. **Development-spegeln** är en andra fullständig kopia av all kunddata. Den nämns inte i registerförteckningen eller i PUB-utkastet.
6. Kanaler och CRM (avsnitt 2.3) saknas i PUB-utkastet.
7. Källorna **hitta.se, allabolag.se och JobTech** saknas i registerförteckningen (A2 anger "offentliga källor" generellt).
8. **Demolänkens spårning** knyter klick och besök till en namngiven mottagare (`docs/BESLUT.md:271-330`, migration 116). Detta saknas i integritetspolicyn. Cookiesidan säger "Vi mäter inte ditt beteende på sidan" (`app/cookies/CookiesSida.tsx:26`), men `components/demo/DemoBesok.tsx:48-63` mäter besök med `sessionStorage`. BESLUT rad 327-330 noterar själv att detta är öppet.

**I dokumenten men inte (längre) i drift:**
1. **Supabase** står som databas och autentisering i bolag.ts, i registerförteckningen (A1 "Mottagare: Supabase") och i DPIA:ns underbiträdeslista. Driften ligger på Railway Postgres. Supabase-auth används bara om URL:en är satt. Statusen behöver bekräftas och listorna rättas. Den gamla Supabase-databasens innehåll ska gallras eller dokumenteras.
2. **OpenAI** står i bolag.ts som "inte i drift".
3. **DPIA:n** säger att produktionen kör simuleringsläge och att ingen kundtext går till någon modelleverantör (`docs/dpia_supportagenten.md:90-92`). Det är **fel sedan 2026-09-12**: main kör Vertex live.

---

## 3. Öppna punkter från JURIDIK_ATGARDER.md: vad stämmer i dag

| Punkt | Läge 2026-08-24 enligt dokumentet | Belägg sedan dess | Bedömning |
|---|---|---|---|
| **P0.1c** Gemini gratisnivå, delad nyckel | Blockerande. Gratisnivå, samma nyckel i main och dev | Chattvägen flyttad till **Vertex AI** (betald GCP, europe-west1) i båda miljöerna 2026-09-12 (`HANDOFF-2026-09-12-VERTEX-AI.md:14-21`; `agent/llm.py:24-36`; BESLUT rad 1469-1471). Faktureringskontot kopplat 2026-08-28 (GOALS.md:80-87). **Men:** (a) samma service account `snajp-vertex` används i båda miljöerna och lokalt hos utvecklarna (HANDOFF-2026-09-12 rad 41-44), så korskopplingen finns kvar; (b) ingen bekräftelse av Googles DPA (Cloud Data Processing Addendum) i repot; (c) reservvägen till AI Studio och gratisnivån finns kvar i koden (`llm.py:321-336`, `discovery.py:502-507`); (d) GOALS.md punkt 9 är fortfarande okryssad; (e) region i bolag.ts och registerförteckningen är inte ifylld | **Delvis löst.** Gratisnivåproblemet i chatten är tekniskt borta. Avtalsdelen och separationen per miljö är öppna. DPIA R1 står fortfarande som öppen (`dpia_supportagenten.md:199-202`) och beskriver ett inaktuellt läge |
| **P0.2** rotera läckt Render-nyckel | Öppen | `RENDER_API_KEY` finns kvar i `.env.deploy` (bara namn kontrollerat). Inget belägg för rotation. Incidentloggen står fortfarande "Öppen", "ej bedömd" (`INCIDENT_RESPONSE.md:85`) | **Öppen, inget belägg för åtgärd** |
| **P0.2b** Render-stacken lever | DeepSeek-nyckeln blankad, simuleringsläge; tjänsterna inte avstängda | `snajp-support/render.yaml` ligger kvar ("VILANDE", rad 1-22). STATUS.md:1045 säger "tystade men inte avstängda". Inget belägg för suspendering eller radering. Incidentposten är "Öppen, ej bedömd" (`INCIDENT_RESPONSE.md:86`). Spärren i koden är lagad (`config.py:609-648`) | **Delvis.** Flödet är stoppat, men tjänsterna och incidentbedömningen är inte stängda |
| **P0.3b** bolagsuppgifter | Platshållare | Fortfarande platshållare utom namnet (`lib/bolag.ts:38-46`) | **Öppen** |
| **P0.3c** juristgranskning | Öppen | Inget belägg för juristgranskning. Pilotavtalet (rad 3-6), DPIA (rad 6-7, 216) och intresseavvägningen (rad 10-11, 128) står som ogranskade. Utkastrutan har tagits bort ur vyn **utan** granskning (`JuridiskSida.tsx:14-16`), trots att JURIDIK rad 316-317 säger att den inte ska tas bort innan | **Öppen.** Läget har förvärrats synligt: sidorna ser färdiga ut |
| **P0.3d** kontaktadress | Gmail som enda väg | `kontakt@snajp.se` är publik (`copy.ts:35`). `integritet@` finns inte (`bolag.ts:46`). Widgeten och larmen använder fortfarande Gmail (`AgentMenu.tsx:28`; `prioriterat_mejl.py:80`) | **Delvis löst** |
| **P1.1b** retentionsperiod | Ej beslutad, ingen policy satt | **Motsägelse:** integritetspolicyn säger att 24 månader är beslutat och att gallringen "är automatiserad och loggas" (`IntegritetspolicySida.tsx:86-90, 196-204`). Men: inget gallringsjobb är schemalagt (inget i `.github/workflows/`, `railway/` innehåller bara `000_auth_compat.sql`; `scripts/gallra.py:23-26` säger "tänkt som ett Railway-cronjobb"); inget belägg för att `--satt-policy` körts för någon kund; GOALS.md:114-117 säger "ingen period betyder ingen gallring". Gallringen omfattar dessutom bara `ss_emails` med kaskad (`048_gallring.sql:16-19, 93`), inte leads, `agent_runs` (som lagrar fulla promptar, `agentcore/insyn.py:56-85`), chattar eller kampanjer | **Öppen**, och den publicerade policyn påstår något som inte stämmer (art. 5.1 a och 13.2 a) |
| **P1.2** Redis TLS och DPA, Resend DPA | TLS av, DPA saknas | Senaste belägg: TLS av (`HANDOFF-2026-08-31-TESTISOLERING.md:47, 80`). Ingen `rediss://` i appkoden. `redis_tls_pa.py` har inte ändrats sedan 2026-08-29. Resend-domäner skapas i `eu-west-1` (`sending_domains.py:50`), men DPA och DPF är inte bekräftade. Webhookhemligheten "kvar att göra" (BESLUT rad 1426-1428), med okänd status | **Öppen** (Resends region är delvis belagd) |
| **P2** DPIA och intresseavvägning | Utkast | Inte uppdaterade sedan 2026-08-24. DPIA:ns underbiträdeslista och R1 är inaktuella. Intresseavvägningens steg 4 beskriver spärrar som har **ändrats**: regel 1 kräver inte längre org.nr och postadress (`send_guard.py:210-222`; BESLUT 2026-10-10 rad 2181-2191); volymtaket är 100 per dag, inte "20/dag" (`send_guard.py:66`); art. 14-foten gäller bara personliga adresser (`send_guard.py:272-276`). Avvägningen säger själv att den ska göras om när spärrarna mjukas upp (`intresseavvagning_kallmejl.md:119-124`) | **Öppen och inaktuell** |
| P2 kundens ansvar för autonominivån i villkoren | – | Finns (`VillkorSida.tsx:34-41`) | **Löst i text** (ogranskad) |
| P2 textmall art. 13 till kunden | – | Finns (`docs/kundmall_informationstext.md`) | **Löst** (ingår inte i onboardingskriptet, se 5) |
| P2 personnummermaskering | Utreds | Byggd: `moderation/maskering.py`, används i `agent/support_agent.py:37, 1215` och `demo_agent.py:45` | **Löst** |
| P2 NextAuth/Supabase-hybriden | – | Kvar: `lib/auth.ts` (Credentials, Google, Entra) plus `lib/supabase-auth.ts` | **Öppen** (låg prio) |
| P2 cookiebanner | Behövs inte | Cookiesidan säger en enda cookie. Demolänkens `sessionStorage`-mätning och en eventuell Cal.com-iframe är inte bedömda | **Ompröva** |
| **PUB-avtalet** | Filen saknas | Inget fristående PUB-avtal. Det enda är **§5 i `docs/pilotavtal.md`** (rad 83-113, utkast 2026-09-13, ogranskat, med hakparenteser) med Bilaga 1. `/villkor` och integritetspolicyn hänvisar till ett "separat personuppgiftsbiträdesavtal" (`VillkorSida.tsx:52-56`; `IntegritetspolicySida.tsx:43-45`) som inte finns | **Öppen** |
| Incidentlogg | Två öppna poster | Båda står fortfarande "Öppen, ej bedömd" (`INCIDENT_RESPONSE.md:85-86`). Sedan dess har nya säkerhetshändelser loggats i BESLUT men **inte i incidentloggen**: agentpromptar lämnades ut i jobbsvaret (BESLUT rad 344-347), plattformsadminlösenordet låg i skript och handoffs och "ska bytas" (BESLUT rad 488-489), och ~600 kallmejl hamnade i skräpposten (BESLUT rad 1399-1406) | **Öppen** |

---

## 4. Tekniska skydd som går att visa upp som bevis

| Skydd | Vad som finns | Bevis (fil:rad) | Svaghet eller lucka |
|---|---|---|---|
| Tenantisolering, RLS | Approll `snajp_app` utan BYPASSRLS; RLS-policyer; Railways `DATABASE_URL` använder `snajp_app` | `ARCHITECTURE_INVARIANTS.md:205-217` (INV-SEC-001); `scripts/railway_provision.py:330`; test `snajp-support/tests/db/test_rls_isolation.py` | Den manuella verifieringen gjordes mot **Supabase** 2026-08-07. Ingen verifiering mot Railway-produktionen hittad. Testet hoppas över utan `DATABASE_URL` |
| Tenant kan inte styras av modellen | Verktygsscheman saknar tenant-parametrar | `ARCHITECTURE_INVARIANTS.md:194-203` (INV-SEC-002) | – |
| Promptinjektionsskydd | Opålitlig text i användarposition, avgränsade ramar | INV-SEC-003, 009, 012 (`ARCHITECTURE_INVARIANTS.md:219-228, 259, 293`); BESLUT rad 374-377 | – |
| Modellen kan inte skicka | Bara kod skickar | INV-SEC-004 (`ARCHITECTURE_INVARIANTS.md:137`); `leads/send_provider.py:1-4` | – |
| Utgående nät allowlistat | Leadshämtare bara mot publikt nät | INV-SEC-005; `leads/hamtvakt.py` (BESLUT rad 435-437); `integrationer/natvakt.py` | – |
| Webbbedömningen grindad (hemlig) | Bara plattformsadmin, Umeå Webbdesign och Alunix | CLAUDE.md; `app/api/admin_listor.py:LISTRADSFALT`; INV-SEC-008 (`ARCHITECTURE_INVARIANTS.md:176`) | – |
| DeepSeek-spärr | Uppstarten fälls om data är riktig (fjärrdatabas eller känt miljönamn) | `config.py:609-700`; `app/main.py`; Next: `lib/llm/modellval.ts:82-97, 189-197` | `lib/agent/llm.ts:22-49` har DeepSeek som default utan spärr, men `refineEmail` har ingen anropare (död kod, bör tas bort) |
| Avtalsgrind | Tenant med `kraver_avtal` får ingen trafik utan registrerat avtalsdatum | `snajp-support/app/avtalsgrind.py:1-31`; migration `20260919210000_070_avtalsgrind.sql:17-25` | **Opt-in, default `false`.** Bara Livrustning satt. En ny kund får trafik utan PUB om ingen slår på flaggan |
| Personnummermaskering | Datum- och Luhn-kontroll före modellanrop | `moderation/maskering.py`; `agent/support_agent.py:1215` | Hälsouppgifter i löptext går igenom (DPIA R1) |
| Bilder och kvitton lagras inte | Vision-beskrivning; bara sha256 för kvitton | `dpia_supportagenten.md:58-63`; migration `045_bookkeeping.sql` | – |
| Kryptering i transit | `ssl_kontext()` för utgående HTTPS; Resend och Vertex över HTTPS | `snajp-support/app/tls.py:19` | **Redis utan TLS** (senaste belägg); Postgres-TLS mot Railway inte verifierad |
| Kryptering i vila | Kundintegrationsnycklar krypteras med Fernet (`INTEGRATION_NYCKEL`) | `config.py:529`; `integrationer/hemligheter.py`; GOALS.md:255-262 | **Kundnycklarna i klartext i development** (BESLUT rad 390, 433-434; SLUTRAPPORT rad 166). Diskkryptering hos Railway inte dokumenterad |
| Spårbarhet och loggning | `X-Request-Id` i svar, logg och `platform_events`; `agent_runs` med steglogg; `ss_decision_log` | `app/sparning.py`; BESLUT rad 485-486; `dpia_supportagenten.md:131-133` | Fulla promptar med persondata i `agent_runs` (`agentcore/insyn.py:75-85`) utan gallring. Ingen åtkomstlogg för admin hittad |
| Gallring | SQL-funktion och skript med torrkörning | `supabase/migrations/048_gallring.sql`; `scripts/gallra.py` | Ingen policy satt, inget schema, bara `ss_emails` (se 3) |
| Registerutdrag och radering | Sök, utdrag och radering per adress; spärrlistan behålls | `scripts/gdpr_radera.py:58-67, 185-212`; `scripts/gdpr_verktyg.py` | **Inte uppdaterat sedan 2026-08-25** (`1dbc5cd3`). Täcker inte senare tabeller med persondata: t.ex. ringlistan och samtal (107), listor och CRM (060, 082, 098, 110), demolänkar (116), kundminne (052), kvitton (063), kampanjer (114). Aldrig kört skarpt. Miljönamnen `production`/`preview` är från gamla stacken (`gdpr_verktyg.py:20-25`). Kopior i Redis, development-spegeln och gamla Supabase nås inte |
| Avregistrering och suppression | Tokenlänk → `avregistrera_via_token` (security definer); gäller hela tenanten; kontrolleras i sändögonblicket | `app/avregistrera/[token]/page.tsx:37-54`; `send_guard.py:288-329`; migrationer 046 och 049; skarpt klickad (JURIDIK rad 27) | – |
| Sändspärrar | 6 regler: suppression, avsändarnamn, opt-out- och policylänk, art. 14, volym, karens, kontorstid, leveransstopp, granskning av de 3 första | `send_guard.py:172-192`, konstanter `:48-93` | Regel 1 kräver bara namn (org.nr och adress valfria) |
| Art. 14-fot | Byggs i kod; full fot vid personlig adress, kort fot vid funktionsadress | `leads/utskicksfot.py:66-96`; `send_guard.py:334-374` | Org.nr saknas i foten så länge kundregistret saknar det (för Snajp själv: platshållare) |
| Leveransskydd | Studs och klagomål via Resend-webhook → suppression och stopp | `send_guard.py:68-79`; BESLUT rad 1409-1418 | Webhookhemligheten har okänd status (BESLUT rad 1426-1428) |
| Incidentrutin | 72 h, vem bedömer, underrättelse till kund | `INCIDENT_RESPONSE.md:1-77` | Loggen är inte uppdaterad; två poster öppna sedan 2026-08-24 |
| Backup och återställning | **Inget belägg hittat** för backuprutin, PITR eller återställningsprov | Synken sparar en kopia före första synken (BESLUT rad 2218) | Pilotavtalets "[X] dagar" för säkerhetskopior är oifyllt (`pilotavtal.md:132-133`) |
| Hemlighetshantering | `.env*` gitignorerat (`.gitignore:63`); `scripts/keys.py`; test mot reservlösenord (`tests/invariants/test_inga_reservlosenord.py`); master-nyckelns default fäller uppstarten (`config.py:724-736`) | – | Hela `.env.deploy` som en GitHub-secret; plattformsadminlösenordet i git-historiken och ännu inte bytt (BESLUT rad 488-489); delat Vertex-servicekonto; Railway-token "Not Authorized" (BESLUT rad 1524-1526) |
| CI-grindar | `verify.yml`: pytest, invariants (inklusive `waivers.yml`), vendor-bump-grind, Docker-smoketest, Node-bygge; CODEOWNERS `@oloflun`; branch protection på main; `migrera.yml` | `.github/workflows/verify.yml:33-148`; `.github/CODEOWNERS` | Ingen hemlighetsskanning (gitleaks), ingen beroendeskanning (Dependabot eller CodeQL) hittad |
| Indexering av dev | `robots.ts` och `noindex` styrda av miljön | JURIDIK rad 47-58; `app/robots.ts`; `lib/miljo.ts` | – |
| Åtkomstkontroll i web | Oinloggad → `/login`; admin fail-closed (404) | JURIDIK rad 34-45 (mätt 2026-08-24) | Inte ommätt sedan dess |

---

## 5. Kundavtalskedjan

| Del | Finns? | Belägg | Lucka |
|---|---|---|---|
| PUB-avtal/DPA-mall | **Bara som §5 i pilotavtalsutkastet** | `docs/pilotavtal.md:83-113` | Inget fristående PUB. Saknar art. 28.3-element: instruktioner bortom "avtalet och inställningar", sekretess för personal, säkerhetsåtgärder (art. 32-bilaga), revisionsrätt, hjälp med DPIA och förhandssamråd, bevisning av efterlevnad. 5.2a (Snajps egen användning av bolagsdata, webbpoolen) är "preliminär, ej juridiskt granskad" |
| Underbiträdesförteckning till kunden | Bilaga 1 med 5 rader, alla regioner och avtal "verifieras" | `docs/pilotavtal.md:149-161` | Saknar TypeSafe, GitHub, development-spegeln och AI Studio-reserven; Supabase och OpenAI oklara. Integritetspolicyn renderar listan från bolag.ts utan regioner (`IntegritetspolicySida.tsx:181-193`) |
| Villkor med ansvarsbegränsning | **Nej** på /villkor ("inte fastställt", `VillkorSida.tsx:76-79`). Pilotavtalet har en (begränsat till pilotavgiften, `pilotavtal.md:115-123`) | – | Inga ordinarie SaaS-villkor: pris och betalning, uppsägning och ansvar saknas |
| Villkorens påståenden stämmer mot koden? | **Nej** | `/villkor` säger att Snajp i kod kontrollerar och blockerar utskick som saknar "organisationsnummer, postadress" (`VillkorSida.tsx:42-45`). Koden kräver bara namn sedan 2026-10-10 (`send_guard.py:210-222`) | Felaktigt avtalslöfte |
| Art. 13-mall för kundens slutkunder | Ja | `docs/kundmall_informationstext.md`; krav i `/villkor` (`VillkorSida.tsx:30-33`) | Inte inbyggd i onboardingen. Mallen nämner "[leverantör]" och ska fyllas i med Google |
| AI-transparens mot mottagaren | **Delvis** | Prompt: "får aldrig påstå eller antyda att du är en människa" men "behöver inte inleda varje svar med att du är en AI-assistent" (`agent/support_systemprompt.py:159-162`). Widgetens meny talar om "Snajp-agenten" och har en dataskyddsflik (`AgentMenu.tsx:36-72`). Utkast märks "AI-utkast" internt (`InboxTriage.tsx:230`) | AI-förordningen art. 50.1 (gäller från 2026-08-02) kräver att den som interagerar med ett AI-system informeras om det, om det inte är uppenbart. Ingen obligatorisk, kodstyrd upplysning i chattens första svar eller i **automatiskt** skickade mejlsvar (kategorier i läget `auto`) hittades. Iris automatiska svar i leadstrådar är inte bedömda |
| Onboardingrutin | Teknisk: `scripts/onboard_tenant.py`, `scripts/pilot_kb_utkast.py`, `docs/pilot_onboarding.md` | – | **Inga juridiska steg**: inget om PUB-signering, `kraver_avtal`, art. 13-mallen, `policy_url`, kundens org.nr och adress i kundregistret, eller gallringspolicyn. `onboard_tenant.py:319-334` pekar fortfarande på Supabase (GOALS.md:111-113: "pekar på den gamla, döda Vercel-kedjan") |
| Avtalsregistrering i systemet | Ja: `ss_customer_details.avtal_signerat` plus grinden | `avtalsgrind.py:13-20` | Grinden är opt-in |

**Vad som saknas för att skriva avtal med första kunden (minimum):**
1. Riktiga bolagsuppgifter (org.nr och adress) eller ett AB.
2. Ett juristgranskat PUB-avtal med art. 28.3-innehåll och komplett, sann underbiträdesbilaga med regioner och överföringsmekanismer.
3. Bekräftade DPA:er med Google Cloud, Railway, Redis och Resend (plus TypeSafe och ScrapeGraph, eller avstängning av dem för kunddata).
4. SaaS-villkor med pris och betalning, uppsägning och ansvarsbegränsning (eller ett pilotavtal som täcker dem).
5. Beslutad och genomförd retention.
6. Avtalsgrinden påslagen för kunden.
7. Art. 13-texten levererad till kunden.

---

## 6. Leads och kallmejl

### 6.1 Rättslig grund som den är dokumenterad
- **Snajps egna kallmejl (Snajp ansvarig):** berättigat intresse enligt art. 6.1 f, intresseavvägningen i `docs/intresseavvagning_kallmejl.md` (utkast 2026-08-24, ogranskat).
- **Kundernas leadsutskick (Snajp biträde):** registerförteckningen B2 (`registerforteckning.md:88-92`).
- **E-postmarknadsföring (MFL 19 §, LEK):** till juridiska personer krävs inget samtycke. Enskilda firmor (fysiska personer) fälls i kod.

### 6.2 Skydd i praktiken (belagda)

| Skydd | Belägg |
|---|---|
| Enskilda firmor fälls före research (MFL 19 §) och går aldrig till ringlistan (NIX) | `leads/forfilter.py:25-44`; `leads/sources/merinfo.py:550-556, 1122-1140`; `leads/katalog.py:96`; `leads/webbpool.py:175-188` |
| Avregistreringslänk krävs i varje mejl; gäller hela tenanten, permanent | `send_guard.py:246-271, 288-307` |
| Spärrlista överlever radering | `gdpr_radera.py:67, 185-200` |
| Art. 14-information vid personlig adress, policylänk krävs | `send_guard.py:272-282, 334-374` |
| Karens 90 dagar per bolag | `send_guard.py:81-85, 419-424` |
| Volym: uppvärmning 20/dag i 14 dagar, upptrappning +5/dag, tak 100/dag/tenant, ett mejl per minut från 08:00 | `send_guard.py:44-66`; BESLUT rad 98-113 |
| Kontorstid 08-17 vardagar; inga utskick kväll, natt, helg | `send_guard.py:87-90`; BESLUT rad 114-122 |
| Leveransstopp vid >0,1 % klagomål eller >3 % studs | `send_guard.py:68-79` |
| De tre första utskicken för ny tenant granskas av människa | `send_guard.py:92-93, 503` |
| Registrets personer och privatsidor används inte som kontakter | CLAUDE.md leadsregel 1, 6; `merinfo.bolagsfakta_text` |
| Befintliga kunder kallmejlas inte | `send_guard.py:314-320` |

### 6.3 Vad som saknas eller är svagt
1. **Avsändaridentifiering:** e-handelslagen 8 § kräver org.nr. Regel 1 kräver bara namn sedan 2026-10-10 (BESLUT rad 2181-2191, som själv noterar e-handelslagen). Snajps eget org.nr är platshållare, så **Snajps egna kallmejl går ut utan org.nr och postadress**, om inte kundregistret i databasen har dem (inte verifierat).
2. **Intresseavvägningen är inaktuell:** den bygger på 20/dag och full identifiering (`intresseavvagning_kallmejl.md:86-96`). Volymen är nu upp till 100/dag per tenant, med ~3 868 godkända utkast i kö (BESLUT rad 83-89). Mejlen skrivs helt automatiskt av Iris med autopilot och demolänkspårning. Avvägningen ska enligt egen text göras om (rad 119-124).
3. **Kort fot till funktionsadresser** utan art. 14-stycken (BESLUT rad 1421-1424). Det är försvarbart för info@, men gränsdragningen "personlig adress" görs av en heuristik (`Prospect.epost_ar_personlig`).
4. **Spårning av klick och besök per namngiven mottagare** (demolänken) saknas i integritetspolicyn och i utskicksfoten. Cookiesidan säger motsatsen. `sessionStorage` omfattas av LEK 9 kap. 28 § (BESLUT rad 327-330 lämnar det till Anton).
5. **Kampanjer till kundens egna listor** kan nå privatpersoner, och ingen kod skiljer ut dem (BESLUT rad 1351-1355).
6. **Utskick från development** är tillåtna (BESLUT rad 2174-2191). Det är en testmiljö med riktiga mottagare.
7. **Leveransproblem:** ~600 kallmejl i skräpposten i oktober (BESLUT rad 1399-1406). Det är en indikation på klagomålsrisk. Webhookens hemlighet har okänd status.
8. **Lagringstid för prospekt och kontakter** är inte beslutad (`registerforteckning.md:42`; `intresseavvagning_kallmejl.md:129-130`). Bortvalda bolag blandas in igen efter 30 dagar (BESLUT rad 2038-2040).
9. **Webbpoolen**: Snajp återanvänder bolagsdata som samlats in vid kund A:s körningar för kund B (Alunix och Umeå Webbdesign). Det bygger på en preliminär klausul (`pilotavtal.md:92-99`; `VillkorSida.tsx:46-50`) och en preliminär registerpost (A2b). Skärmbilder via ScrapeGraph.
10. **Skrapning av allabolag och hitta utan avtal** är ett användarvillkors- och databasrättsfrågetecken snarare än GDPR (BESLUT rad 2020-2022).

---

## 7. Prioriterad gap-lista

Kolumner:
- **Allvar:** B = blockerar första kund; F = bör fixas före; V = kan vänta.
- **Vem:** A = agent (kod eller dokument); Ä = kräver ägarens hand (underskrift, betalning, lösenord, juristbeslut).

| # | Gap | Belägg | Allvar | Vem |
|---|---|---|---|---|
| 1 | Inget juristgranskat PUB-avtal; bara pilotavtalets §5, som saknar art. 28.3-element. Villkoren hänvisar till ett avtal som inte finns | `pilotavtal.md:83-113`; `VillkorSida.tsx:52-56` | **B** | A kan skriva utkast; Ä: jurist och underskrift |
| 2 | Bolagsuppgifter saknas (org.nr, adress, dataskyddsadress); beslut om enskild firma eller AB | `lib/bolag.ts:39-46` | **B** | Ä (beslut och uppgifter); A fyller i sedan |
| 3 | DPA/avtalsnivå och region obekräftade för Google Vertex, Railway, Redis och Resend; Railways region okänd | `lib/bolag.ts:130-168`; `registerforteckning.md:111-116`; `pilotavtal.md:153-157` | **B** | Ä (godkänna DPA i konsoler, läsa regioner); A kan köra `railway_region.py` och `redis_kontroll.py` när Ä tillåter |
| 4 | Underbiträdeslistan är ofullständig och delvis fel: TypeSafe, GitHub Actions (prod-data var 10:e min), development-spegeln, AI Studio-reserven och Render saknas; Supabase och OpenAI troligen inaktuella. Samma lista finns på tre ställen plus i policyn | Avsnitt 2.4 | **B** | A (dokument); Ä beslutar om TypeSafe och ScrapeGraph ska behållas för kunddata |
| 5 | Integritetspolicyn påstår 24 månaders automatisk gallring som inte finns; ingen policy satt, inget schema, gallringen täcker bara supportmejl | `IntegritetspolicySida.tsx:86-90, 196-204`; `gallra.py:23-26`; `048_gallring.sql:16-19` | **B** | Ä beslutar period; A bygger schemalagt jobb och utökar till leads och `agent_runs` |
| 6 | Avtalsgrinden är opt-in (default false): en ny kund får trafik utan signerat PUB | `migration 070:17-25`; `avtalsgrind.py` | **B** | A (default true för nya tenants plus onboardingsteg) |
| 7 | /villkor saknar ansvarsbegränsning, betalvillkor och uppsägning; påstår felaktigt att org.nr och adress krävs i kod | `VillkorSida.tsx:42-45, 59-84`; `send_guard.py:210-222` | **B** | Ä/jurist (klausuler); A rättar faktapåståendet |
| 8 | Samma Vertex-servicekonto i main, development och lokalt hos utvecklare; reservväg till AI Studio (gratisnivå) finns kvar i koden | `HANDOFF-2026-09-12-VERTEX-AI.md:41-44`; `llm.py:321-336`; `discovery.py:502-507` | **F** | Ä skapar separata servicekonton; A spärrar AI Studio-vägen där data är riktig (samma mönster som DeepSeek-spärren) |
| 9 | Development är en fullständig kopia av produktionens persondata, synkas via GitHub, och utkast kan skickas därifrån; kundnycklar i klartext i dev | CLAUDE.md; `synk.yml:15-44`; BESLUT rad 390, 2174-2191 | **F** | Ä beslutar (minimering eller pseudonymisering); A bygger |
| 10 | Redis-trafik okrypterad (TLS av) och Redis DPA ej tecknad | `HANDOFF-2026-08-31-TESTISOLERING.md:47`; JURIDIK rad 354-362 | **F** | Ä (kör `redis_tls_pa.py --apply`, teckna DPA) |
| 11 | Render-stacken (P0.2b) inte suspenderad eller raderad; Render-nyckeln inte belagd som roterad; två incidentposter öppna sedan 2026-08-24; den gamla Supabase-databasens persondata inte bedömd eller gallrad | `INCIDENT_RESPONSE.md:85-86`; `render.yaml`; JURIDIK rad 244-251 | **F** | Ä (dashboard, rotation, incidentbedömning); A kan ta bort `render.yaml` och uppdatera loggen |
| 12 | DPIA och intresseavvägning inaktuella (DPIA säger produktion i simuleringsläge; avvägningen bygger på 20/dag och full identifiering) och ogranskade | `dpia_supportagenten.md:90-92`; `intresseavvagning_kallmejl.md:86-96, 119-124` | **F** | A uppdaterar utkasten; Ä/jurist beslutar |
| 13 | AI-förordningen art. 50.1: ingen kodstyrd upplysning om AI i chatt och automatiska mejlsvar | `support_systemprompt.py:159-162` | **F** | A (fast AI-rad i widgeten och i auto-mejl) |
| 14 | Kallmejl utan org.nr (regel 1 lättad); Snajps egna utskick saknar sannolikt org.nr och adress | `send_guard.py:210-222`; BESLUT rad 2189-2191 | **F** | Ä (uppgifterna, beslut att återinföra kravet); A (regeln) |
| 15 | Demolänkens personknutna klick- och besöksspårning är inte informerad; cookiesidan säger motsatsen | `CookiesSida.tsx:26`; `DemoBesok.tsx:48-63`; BESLUT rad 327-330 | **F** | Ä beslutar; A uppdaterar policy, fot och cookiesida |
| 16 | `gdpr_radera.py` täcker inte tabeller tillkomna efter augusti; aldrig provkört | `gdpr_radera.py:58-67`; `git log` 2026-08-25 | **F** | A (utöka plus torrkörning lokalt mot `lokal_stack`) |
| 17 | Ingen dokumenterad backup- eller återställningsrutin | Inget belägg hittat | **F** | Ä (Railway-plan och inställning); A dokumenterar och provar |
| 18 | Onboarding saknar juridiska steg (PUB, art. 13-mall, grind, policy_url, retention) och pekar på gammal stack | `onboard_tenant.py:319-334`; GOALS.md:111-113 | **F** | A |
| 19 | Juridiska sidor ser färdiga ut utan granskning; "Senast uppdaterad" saknas | `JuridiskSida.tsx:14-16, 49-58` | **F** | Ä/jurist |
| 20 | Hemligheter: plattformsadminlösenord i git-historiken ej bytt; hela `.env.deploy` som en GitHub-secret; ingen hemlighetsskanning i CI | BESLUT rad 488-489; `synk.yml:37-39`; `verify.yml` | **F** | Ä (byte av lösenord och rotation); A (gitleaks i CI, smalare secrets) |
| 21 | Incidentloggen uppdateras inte med senare säkerhetshändelser (promptläckan, lösenordet, skräppostvågen) | BESLUT rad 344-347, 488-489, 1399-1406 vs `INCIDENT_RESPONSE.md:83-86` | **F** | A (logga); Ä bedömer |
| 22 | `DATASKYDD_MEJL` (integritet@) saknas; widgeten och larmen använder Gmail | `bolag.ts:46`; `AgentMenu.tsx:28`; `prioriterat_mejl.py:80` | **V** (en fungerande reserv finns) | Ä (brevlåda); A byter adresser |
| 23 | Kanaler och CRM (Meta, Slack, Teams, HubSpot, Pipedrive, Gmail/Graph) inte beskrivna i PUB | GOALS.md:263-267 | **V** (bli **B** när en kund aktiverar en kanal) | A (text); Ä/jurist |
| 24 | INV-SEC-001 (RLS) bara verifierat mot Supabase, inte Railway-produktionen | `ARCHITECTURE_INVARIANTS.md:205-217` | **V** | A kan köra testet mot `lokal_stack`; mot prod kräver Ä |
| 25 | Webbpoolen och klausul 5.2a är preliminära; Snajp agerar ansvarig för data insamlad i kunduppdrag | `pilotavtal.md:92-99`; `registerforteckning.md:45-55` | **V** | Ä/jurist |
| 26 | Skrapning av allabolag och hitta utan avtal | BESLUT rad 2020-2022 | **V** | Ä (API-avtal) |
| 27 | Död kod med DeepSeek som default utan spärr (`lib/agent/llm.ts`) | `lib/agent/llm.ts:22-49` | **V** | A (ta bort) |
| 28 | Nextauth/Supabase-hybrid; AUTH.md beskriver Supabase-flödet | `lib/auth.ts`; `lib/supabase-auth.ts`; `AUTH.md` | **V** | A |
| 29 | Utvecklarverktyg (AI-kodagenter) läser development-spegeln med riktig kunddata (t.ex. räkningar i BESLUT 2026-11-16) | BESLUT rad 83 | **V/F** | Ä beslutar policy |
