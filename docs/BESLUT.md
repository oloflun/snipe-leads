# Beslutslogg

Varje nytt beslut om produkten skrivs här med beslutsfattarens eget resonemang,
så att skälet går att följa efteråt (Antons regel 2026-10-10). Nyaste överst.
Ett beslut som ersätts stryks inte: det får en rad om vad som ersatte det.

Format: datum, vem, beslutet, resonemanget (så nära beslutsfattarens ord som
möjligt), vad det betyder i koden.

---

## 2026-11-18 natt — webbens databasroll får bara det webben gör (Claude (agent), på Antons uppdrag)

**Beslut.** Rollen `snajp_web` har sedan migration 126 bara de rättigheter webbens egen SQL
behöver: 13 tabeller, på flera av dem bara vissa kolumner, och ingen rättighet på tabeller
som skapas senare. `auth.users` är inte längre läsbar för PUBLIC; `snajp_app` läser bara
`id` och `email`. Ersätter formen i migration 030 ("breda grants, RLS som grind").

**Resonemanget.** Anton bad om minskningen (ISO 27001 A.8.2, A.8.3, A.5.15) men varnade för
att en för snäv rättighet bryter webben. 030 valde breda rättigheter för att likna Supabases
`authenticated`; det skälet föll när Supabase Auth togs bort, och kvar blev en roll som kunde
läsa kundens support- och leadsdata så fort en fråga satte `app.tenant_id`, och en
`auth.users` som varje roll kunde läsa. Kartläggningen visade att webben gör lite direkt mot
databasen (23 filer, 67 satser) och att resten går via api:t med kundens nyckel, så
minskningen gick att göra säkert. Skyddet mot att bryta webben är att CI kör varje sats ur
webbens källkod som `snajp_web` med EXPLAIN, som prövar rättigheterna utan att köra något;
skyddet mot att det breddas igen är att samma test jämför rollens rättigheter med en exakt
lista. `startDemo` behåller update-rätten på `workspaces.is_demo` trots att uppdateringen
redan i dag påverkar noll rader (ingen update-policy, ingen användaridentitet): att ta bort
rätten hade gjort satsen till ett fel och stoppat demon. Felet i sig är ett eget ärende.
Priset: en migration som lägger till en tabell webben ska nå måste ge rättigheten uttryckligen.

**Vad det betyder i koden.** `db/migrations/20261118160000_126_snajp_web_minsta_rattighet.sql`;
`snajp-support/tests/db/test_snajp_web_rattigheter.py` (listan `TILLATET`); `AUTH.md`
(Databasrollen); `docs/compliance/datamangder.md` §1 och fynd 3.

---

## 2026-11-18 natt — spärr mot upprepade inloggningsförsök, tvåfaktor uppskjuten (Claude (agent), på Antons uppdrag)

**Beslut.** (1) Lösenordsinloggning och begäran om lösenordsåterställning spärras
tillfälligt efter upprepade försök, per e-postadress och per klient-IP (migration 125,
`lib/auth/inloggningsregler.ts`): inloggning 5 misslyckade per adress eller 20 per IP på
15 minuter, återställning 3 per adress eller 10 per IP på en timme. Spärren är 1, 5, 15
och sedan 60 minuter för varje ny spärr inom ett dygn. Tillståndet ligger i Postgres. (2)
Tvåfaktor (TOTP) för plattformsadmin byggs inte i den här omgången.

**Resonemanget.** Anton bad om spärren (ISO 27001 A.8.5) med kravet att den inte får
avslöja om ett konto finns. Därför räknas adressen likadant med och utan konto, beskedet
är detsamma för alla, och ett spärrat försök prövar aldrig lösenordet. IP-tröskeln är
högre än adressens eftersom ett kontor delar IP bakom NAT; utan IP-gränsen hade en
angripare kunnat pröva ett lösenord mot många adresser. Postgres i stället för Redis:
webben har ingen Redis-anslutning, men har redan Postgres, och spärren behöver vara
atomisk mellan webbens repliker, vilket upserten ger. Nycklarna är HMAC med `AUTH_SECRET`
så att tabellen inte blir en lista över adresser som prövats. Spärren släpper igenom vid
databasfel (fail open) och loggar det: när databasen är nere går inloggningen ändå inte,
och en deploy som hinner före migrationen hade annars låst ute alla. Tvåfaktor kräver
lagring av krypterade hemligheter, en ny nyckel i Railway (som agenten inte får ändra),
ett inrullningsflöde med QR-kod och ett andra inloggningssteg; det är för stort för att
göras tryggt i samma veva, och Anton har inte beslutat om tvånget.

**Vad det betyder i koden.** `db/migrations/20261118150000_125_inloggningsforsok.sql`
(tabellen nås bara genom funktionerna); `lib/auth/inloggningsregler.ts`,
`lib/auth/inloggningsforsok.ts`; `authorize` i `lib/auth.ts` (gäller också direkta
anrop till `/api/auth/callback/credentials`); `requestPasswordReset` i
`lib/actions/auth.ts`; beskedet på båda språken i `components/auth/LoginForm.tsx`.
Tester: `snajp-support/tests/db/test_inloggningsforsok.py` (CI-jobbet `databas`),
`lib/auth/inloggningsregler.test.ts`.

---

## 2026-11-18 sen kväll — begränsning av behandling som spärrmarkering, licensgrind med obeslutade undantag (Claude (agent), på Antons uppdrag)

**Beslut.** (1) Begränsning av behandling (GDPR art. 18) är en markering per e-postadress
i tabellen `behandlingsbegransningar` (migration 124), **global över alla kunder**, satt
och hävd bara med `scripts/gdpr_radera.py --begransa` / `--hav-begransning`. En aktiv
markering blockerar utskick till adressen och skickar inkommande mejl till Att hantera
utan AI. Kan listan inte läsas stoppar spärren (utskicket köas om, mejlet går till en
människa). Markeringen **behålls vid radering** och en hävning lämnar raden kvar. (2)
Licensgrinden i CI godtar 18 copyleft- eller okända licenser som står i vitlistan som
**obeslutade**, så att CI är grön tills Anton beslutat.

**Resonemanget.** Anton bad om agentens delar av de krav som väntar på honom
(`docs/compliance/score-plan-2026-11-18.md`, sist). (1) Begäran gäller personen, inte en
kunds lista, och rättighetsskriptet söker och raderar redan över alla kunder, så
markeringen följer samma gräns. En spärr som släpper igenom när den inte kan prövas är
ingen spärr. En radering ska inte tyst häva en begränsning, och raden är belägget för att
begäran hanterades (art. 18.3: personen informeras före hävning). Approllerna får bara
läsa: en markering som appen kan ta bort skyddar inte mot appen. Befintliga utkast och
research stoppas inte i koden; det hade krävt ingrepp på många ställen, och skriptet ber i
stället handläggaren arkivera berörda leads. (2) Att fälla CI på de licenser som redan
används hade stoppat allt arbete för ett beslut som är Antons; att godta dem tyst hade
dolt beslutet. Vitlistan visar dem som obeslutade med agentens bedömning bredvid.

**Vad det betyder i koden.** `db/migrations/20261118140000_124_behandlingsbegransning.sql`;
`Storage.list_begransade`; `leads/scheduler.py` (`_kor_send_guard`, regel
`begransad_behandling`); `email_pipeline/processor.py` (`process_email`);
`scripts/gdpr_radera.py`; `scripts/licenser.py` och `docs/compliance/licenser-vitlista.json`.

---

## 2026-11-18 natt — åtkomstlogg för admin, ingen kvittotext i agent_runs, övervakningens reserv (Claude (agent), på Antons uppdrag)

**Beslut.** (1) Varje anrop med master-nyckeln och varje kundbesök skriver en rad i
`audit_logs`: vem, när, åtgärd, kund och ruttens mall, aldrig innehåll eller nycklar
(migration 123, INV-SEC-013). Raderna sparas i **365 dagar** och gallras automatiskt,
oberoende av kunddatans gallring. Approllerna får inte ändra eller radera dem. (2) Den
äldre bokföringsytan sparar inte kvittots text i `agent_runs`, bara längd, sha256 och
underlagets id (PR 83). (3) Övervakningen körs på två scheman, efter varje Verify och
synk, och en dödmanskontroll i CI larmar när den inte gått på tre timmar (PR 84).

**Resonemanget.** Anton bad om att åtgärda de tre fynden ur poängplanen
(`docs/compliance/score-plan-2026-11-18.md`) utan att han behöver göra något. (1)
Plattformsadmin läser och ändrar alla kunders data, och utan logg går det inte att svara
på vem som gjorde vad (ISO 27001 A.8.15, A.5.15–A.5.18, GDPR art. 32). Loggen sitter i
beroendet `require_master_key`, inte per endpoint, så att nästa admin-endpoint inte kan
glömmas. Den skrivs genom en säkerhetsdefinierad funktion, så att appen som loggas inte
kan skriva om loggen. Ett admin-id godtas bara om det står i `platform_admins`. 365 dagar
är en teknisk utgångspunkt: en säkerhetslogg ska ha en egen, bestämd lagringstid och inte
följa kunddatans period, som ännu inte är beslutad. Faller skrivningen går anropet igenom
med en varning, för en adminyta som låses av en loggstörning stoppar den som ska rätta
störningen. Läsningar under ett kundbesök loggas som besöket, inte per anrop. (2) Ingen
felsökning har behövt kvittotexten: fälten står i `bk_underlag`. Texten bär namn,
kortnummer och ibland personnummer, och `agent_runs` gallras inte förrän perioden är
beslutad (DPIA R10). (3) Schemat gav en körning av omkring 60. Orsaken är GitHubs
schemaläggare, som tappar de flesta schemalagda körningar i repot (synk.yml cirka 4 av 144
om dygnet, före och efter att repot blev privat). Det går inte att rätta i repot, så
övervakningen får en reserv som inte är ett schema, och tystnaden larmar.

**I koden.** Migration `db/migrations/20261118130000_123_adminlogg.sql`;
`snajp-support/app/api/adminlogg.py`, `deps.require_master_key`, `logga_adminatkomst` i
lagringarna; `app/api/snajp-support/_lib.ts` (`X-Snajp-Admin`). Tester:
`tests/invariants/test_inv_sec_013.py`, `snajp-support/tests/db/test_adminlogg.py`.
`app/api/bookkeeping.py:kvittotext_for_logg`, `tests/bookkeeping/test_kvittotext_logg.py`.
`.github/workflows/overvakning.yml`, `scripts/overvakning_dodman.sh`, jobbet
`overvakning-dodman` i `verify.yml`.

**Öppet för Anton.** Om 365 dagar är rätt lagringstid för åtkomstloggen. Om en extern
pingtjänst ska väcka övervakningen när inget annat händer i repot. Releasen till `main`.

**Backa.** (1) Ta bort anropet i `require_master_key`; migrationen kan stå kvar. (2) Återställ
`input_text` i `bookkeeping.py`. (3) Ta bort `workflow_run` och jobbet `overvakning-dodman`.

---

## 2026-11-18 natt — säkerhets- och AI-frågan i varje PR, och en egen modell för kvittohanteraren (Claude (agent), på Antons uppdrag)

**Beslut.** (1) Varje PR mot `development` ska besvara två frågor i
`.github/pull_request_template.md`, "Säkerhet och dataskydd" och "AI-påverkan",
och CI fäller PR:en annars (INV-PROC-001, `.github/workflows/pr-granskning.yml`).
Botar och release-PR:er mot `main` är undantagna. (2) Kvittohanteraren får egna
variabler, `KVITTO_MODEL` och `VERTEX_KVITTO_REGION`. Tomma ger dagens beteende
(`MODEL` i huvudregionen), och de sätts inte i någon miljö.

**Resonemanget.** Anton bad om att höja antalet uppfyllda compliance-krav med det
som inte kräver hans beslut (`docs/compliance/score-plan-2026-11-18.md`). Säkerhet
och AI-påverkan prövades bara när någon kom ihåg det; en fråga som CI kräver ett
svar på är det minsta som gör prövningen till en del av varje arbete (ISO 27001
A.5.8, ISO 42001 A.6.1.3). Frågan prövar att svaret finns, inte att det är rätt.
Kvittovariablerna finns för att kvittosviten föll från 37/40 till 30/40 när `MODEL`
byttes i development, med en obetald kundfaktura bokförd som klar
(`docs/compliance/modellbyte-underlag.md` avsnitt 6.4): vid ett byte ska
kvittostegen kunna stanna på en prövad modell. Vilken modell de ska ha är Antons
beslut, liksom om variablerna ska sättas.

**I koden.** `scripts/pr_granskning.py`, `tests/invariants/test_inv_proc_001.py`;
`snajp-support/app/config.py` (`kvitto_model`, `vertex_kvitto_region`,
`kvittomodell`, `kvittoregion`, kontrollerna i `llm_provider_fault`),
`app/agent/llm.py` (`get_kvitto_client`, `get_kvitto_agent_model`),
`app/kvitton/hanterare.py`. INV-DATA-006 nämner regionen. Tester:
`tests/kvitton/test_kvitto_modell.py`, `tests/invariants/test_inv_data_006.py`.

**Backa.** Ta bort arbetsflödet `pr-granskning.yml` (och INV-PROC-001). För
kvittovariablerna behövs ingen backning så länge de är osatta.

## 2026-11-18 sen kväll — provbytet i development återställt helt (Claude, på Antons uppdrag)

**Beslut.** Development kör åter samma modellinställningar som main: bara
`MODEL=gemini-2.5-flash` på `api`, inga regionvariabler och inga stegmodeller.
Variablerna från provbytet (`GOOGLE_CLOUD_REGION=eu`, `VERTEX_RESERVREGIONER`,
`VERTEX_INBADDNING_REGION`, `VERTEX_BILD_REGION`, `VERTEX_UTKAST_REGION`,
`VISION_MODEL`, `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` och `MODEL` på `web`)
är borttagna. Koden från PR #74, #76 och #78 ligger kvar och är overksam när
variablerna saknas.

**Resonemanget.** Kvittosviten föll från 37/40 till 30/40 när kvittohanteraren
gick på gemini-3.5-flash-lite (den följer `MODEL`), och ett av felen tar sig
förbi granskningen: en obetald kundfaktura bokades som klar med det egna bolaget
som motpart. Development speglar produktionen, så ett fel som bokför fel ska inte
stå kvar i en miljö med riktiga kunders data medan bytet ändå inte kan
genomföras: utkasten och bildmodellen saknar en godkänd ersättare i `eu`.
Mätningarna är gjorda och dokumenterade (modellbyte-underlag.md 3.5–3.7, 6.4,
8); provbytet har gett det det kunde ge. Supporten var bättre på lite (48/50 mot
47/50), så ett framtida byte bör ge kvittohanteraren en egen modell.

**Öppet för Anton.** Ersättare för gemini-2.5 till utkast och bilder, och om
kvittohanteraren ska få en egen modellvariabel.

---

## 2026-11-18 kväll — utkasten på gemini-3.5-flash-lite prövade i development och backade; kvittosviten körd (Claude (agent), på Antons uppdrag)

**Beslut.** Iris utkast och humanizer i development ligger kvar på
gemini-2.5-flash i europe-west1 (`LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL`,
`VERTEX_UTKAST_REGION=europe-west1`). 3.5-flash-lite i `eu` prövades och
backades samma kväll. Inga andra variabler ändrades; main är inte rörd.

**Resonemanget.** Antons grind: inga tekniska fel, och stilgrinden
(INV-LEADS-UTKAST-002) i nivå med 2.5, högst ett fall sämre. Samma 11 fall ur
`evals/iris_utkast.json` kördes på båda modellerna samma kväll, mot nya
syntetiska evalkunder. 3.5-flash-lite levererade alla 11 utan fel, på 6,5–40 s
(2.5-flash: 9 av 11, två föll på 503 i europe-west1, 11,6–84 s). Stilen höll
inte: lite hade facitets `slentrian_ingang` ("När …"-ingångar) i sex av elva
utkast, 2.5-flash i inget av sina 15 levererade utkast den dagen. Per fall är
lite sämre i fyra och bättre i ett; `bedom_iris` godkände 4 mot 7. Bara om
2.5:s två serverfel räknas som stilfel blir skillnaden ett fall (5 mot 6), och
agenten bedömde att stilgrinden ska mäta stilen, inte kapaciteten. Att
backningen inte är gratis står i underlaget: 2.5 i europe-west1 tappade två
utkast på 503 samma kväll.

**Kvittosviten.** 30/40 mot 37/40 med allt på 2.5 (2026-11-10), 0 tekniska
fel, p50 7,2 s mot 20,9 s. Sviten är text-PDF:er, så den mäter `MODEL`
(3.5-flash-lite i `eu` sedan provbytet), inte bildmodellen. Lite skickar sju
underlag till granskning som ska vara klara, och bokförde en obetald
kundfaktura som klar med det egna bolaget som motpart. Körd med en tillfällig
env-fil och en ny evalkund (`eval-11181437-kvitto`); `.env.deploy` är orörd.

**Öppet för ägaren.** Vilken modell utkasten ska ha när 2.5 stängs (lite
skriver sämre ingångar, 3.8 i `eu` saknar kapacitet utan Provisioned
Throughput), och om kvittohanteraren ska ha en egen modell i stället för
`MODEL`. Kostnad för kvällens prov: omkring 15 kr i Vertex.

**Backa/byta.** Sätt `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` =
`gemini-3.5-flash-lite` och `VERTEX_UTKAST_REGION` = `eu` på `api` och `web` i
development för att pröva lite igen. Detaljer och siffror per fall:
`modellbyte-underlag.md` avsnitt 6.4.

---

## 2026-11-18 — Supabase-spåret tas bort helt (Anton)

**Beslut.** "Ta bort supabase-spåret som ligger kvar helt." Migrationerna
flyttas från `supabase/migrations/` till `db/migrations/`. Raderat: edge
functions, `supabase/config.toml` och `schema.sql`, GoTrue-adaptern
`lib/supabase-auth.ts` med sina grenar i inloggning, registrering och demo,
`@supabase/supabase-js`, Supabase-MCP:n i `.mcp.json`, nyckeln
`PREVIEW_POSTGRES_URL` och skripten som bara talade med Supabase
(provisionering, schema, speglingen `supabase_seed_dev.py`, flytten därifrån,
preview-grenens anslutning). Utan katalogen `supabase/` går kontrollen
Supabase Preview igenom (grön på release-PR:en direkt efter pushen). Appen
Supabase är fortfarande installerad på repot hos GitHub och kan kopplas bort
där (github.com/settings/installations); det kräver Antons inloggning.

**Resonemanget.** Supabase Preview på release-PR:en var röd, för att den
körde mot en Supabase-gren som varit död sedan augusti och som vi enligt
`MIGRATIONS-PENDING.md` inte rör. Allt körs på Railway sedan dess, och det
som låg kvar var bara spår som kunde lura någon att tro att Supabase
fortfarande var en väg: en katalog med Supabase-namn, en auth-gren som
aktiverades om en gammal variabel råkade vara satt, och skript som skrev dit.

**Vad som lever kvar med flit.** Liggaren `supabase_migrations.schema_migrations`
och `auth`-schemat (`railway/000_auth_compat.sql`) är namn i Railway-databasen.
Att döpa om dem kräver en migration mot main och ändrar inget i beteendet.
Supabase står kvar som underbiträde i `lib/bolag.ts` ("avvecklas") tills
projektet hos Supabase är raderat: där ligger fortfarande gammal data, och
det är ett juridiskt påstående, inte kod. Sessionsloggar, handoffs, planer
och `email-studio/kopior` är historik och är inte omskrivna.

---

## 2026-11-18 — utkasten i development tillbaka på gemini-2.5-flash i europe-west1 efter mätningen (Claude (agent), på Antons uppdrag)

**Beslut.** Iris utkast och humanizer i development går tillbaka till
gemini-2.5-flash i europe-west1 (`LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL`,
ny `VERTEX_UTKAST_REGION`, PR #78). Chatten, triagen, leadssökningen, Email
Studio och övriga textsteg ligger kvar på gemini-3.5-flash-lite i `eu`. Main är
inte rörd.

**Resonemanget.** Antons uppdrag: pröva det som inte prövats i development,
bara mot syntetiska kunder, och backa en variabel till dagens värde om en
kärnfunktion inte fungerar. Utkasten på gemini-3.8-flash i `eu` föll i 7 av 11
fall (503, 429, svar över 120 s, jobb över femminutersgränsen) redan med tre
samtidiga jobb, och de som kom fram tog 161–277 s mot 23 s i dag. Kvaliteten
var bra, men det spelar ingen roll när de flesta utkast inte blir av. 2.5
saknas i `eu`, så utkasten behövde en egen region i koden för att kunna backas
till just dagens värde. Efter backningen: 6 av 6 utan fel, 8–21 s.
3.5-flash-lite höll i resten: supporten 48/50 (i dag 47/50) på 5,9 s i median,
leadssökningen och Email Studio svarade 200 med de nya tankeinställningarna.

**Öppet för ägaren.** Vilken modell utkasten ska ha när 2.5 stängs:
3.5-flash-lite i `eu` (billigast, 7/10 lokalt, inte prövat i development) eller
3.8-flash med reserverad kapacitet (Provisioned Throughput) i `eu`.

**Backa.** Ta bort `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` och
`VERTEX_UTKAST_REGION` på `api` och `web` i development; då ärver utkasten
`MODEL` i `eu`. Detaljer: `modellbyte-underlag.md` avsnitt 6.4.

**I koden.** `config.py` (`vertex_utkast_region`, `utkastregion`, kontrollen i
`llm_provider_fault`), `agent/step_runner.py` (`UTKASTSTEGENS_FALT`).
INV-DATA-006 nämner variabeln.

---

## 2026-11-18 — provbytet i development gjort, textmodellerna till `eu`, bildmodellen kvar (Claude (agent), på Antons uppdrag)

**Beslut.** Development kör sedan 2026-11-18 gemini-3.5-flash-lite (`MODEL`)
och gemini-3.8-flash för utkast och humanizer i Vertex-multiregionen `eu`,
utan reservregion. Bildmodellen (gemini-2.5-flash) och inbäddningarna
(gemini-embedding-001) ligger kvar i europe-west1, med den nya inställningen
`VERTEX_BILD_REGION` (PR #76) och `VERTEX_INBADDNING_REGION`. Miljön `main` är
inte rörd. Ersätter posten nedan om att provbytet inte gjordes.

**Resonemanget.** Anton bad om provbytet med bildmodellen oförändrad, så att
textmodellerna kan prövas medan bildvalet är öppet. Det krävde en egen region
för bildklienten, eftersom 2.5 saknas i `eu`. Utkasten fick 3.8-flash, som
underlaget rekommenderar: 3.5-flash-lite brister där (6/10 utan stilfynd mot
7/10 i dag, 3.8 10/10). Reservregionerna är tomma, eftersom ingen av
modellerna finns i de vanliga EU-regionerna eller i europe-west3; koden väntar
då ut ett 429 i `eu`.

Den fulla webbkalibreringen mot alla 58 facitsajter visade att ingen modell
klarar grinden på 85 %, inte heller dagens: 2.5-flash 81 %, 3.8-flash 81 %,
3.5-flash-lite 79 % med en akut sajt på bra (utan den inaktuella
sagobetong.se: 82,5, 82,5 och 80,7 %). 3.8 felar bara åt det stränga hållet
(nio bra sajter blev dåliga), de andra två åt båda håll. Grinden och facit är
inte ändrade. Vilken bildmodell som ska ersätta 2.5, och om grinden eller
prompten ska ses över, är ägarens beslut (`modellbyte-underlag.md` avsnitt 3.7).

**Kontrollen.** Deployerna lyckades, startloggen var utan
`llm_provider_fault`, och två syntetiska supportfrågor mot demotenanten gick
igenom: text till `eu`, inbäddningar och bildbeskrivning till europe-west1,
alla 200. Inga mejl, inga godkända utkast, ingen leadskörning. Kostnad:
57 ScrapeGraph-krediter och omkring 10 kr i Vertex.

**Backa.** Ta bort variablerna i `modellbyte-underlag.md` avsnitt 6.4 på `api`
och `web` i development; standardvärdena ger gemini-2.5-flash i europe-west1
så länge Google låter 2.5 svara.

**I koden.** `config.py` (`vertex_bild_region`, `bildregion`, kontrollen i
`llm_provider_fault`), `agent/llm.py:get_vision_client`. INV-DATA-006 nämner
`VERTEX_BILD_REGION`. Tester: `tests/invariants/test_inv_data_006.py`,
`tests/agent/test_modellbyte_gemini3.py`.

---

## 2026-11-18 — provbyte i development (Claude (agent), inom Antons uppdrag om EU-compliance) — inte gjort: bildmodellen klarade inte grinden

*Ersatt samma dag av posten ovan: provbytet gjordes med bildmodellen kvar på 2.5-flash.*

**Beslut.** Variablerna i `modellbyte-underlag.md` avsnitt 6.1 sattes **inte**
i Railway-miljön `development`. Development kör gemini-2.5-flash i
europe-west1 som förut. Inget i miljön `main` är rört.

**Resonemanget.** Uppdraget var att göra provbytet bara om två villkor höll:
kvoten i `eu` (under cirka 5 % 429) och att bildmodellen klarar
webbkalibreringens grind på 85 %. Kvoten höll: ingen regional kvot finns för
3.x i `eu`, och 0 av 60 samtidiga anrop per modell fick 429. Bildmodellen
klarade inte grinden. På ett urval om 30 av facitets 58 sajter, med samma
skärmbilder för alla modeller, fick gemini-3.8-flash 80 % (strängare än facit:
fem bra sajter blev dåliga) och gemini-3.5-flash-lite 83 %; dagens
gemini-2.5-flash fick 83 % och 87 % i två körningar. En bildmodell måste sättas
vid bytet, eftersom bildklienten anropas i samma region som resten och 2.5
saknas i `eu`, så bytet kan inte göras med bildmodellen kvar på 2.5. I
kvittoavläsningen läste 3.8-flash foton bäst men rättade ett avsiktligt
felsummerat kvitto (793 blev 798), och 3.5-flash-lite läste foton sämst.
Att sänka grinden eller räkna bort ett fall för att få igenom bytet är
ägarens beslut, inte agentens.

**Nästa steg.** Kalibrera 3.5-flash-lite och 3.8-flash mot alla 58 sajter
(omkring 60 ScrapeGraph-krediter till) och välj bildmodell utifrån det, eller
låt Anton avgöra på urvalet. Siffrorna står i `modellbyte-underlag.md` avsnitt
3.5 och 3.6. Mätningen kostade omkring 13 kr i Vertex och 50
ScrapeGraph-krediter.

---

## 2026-11-18 (Claude (agent), inom Antons uppdrag om EU-compliance; ändringarna väntar på Antons granskning) — Bytet från Gemini 2.5 förbereds så att det blir en ändring av variabler

**Beslut.** Koden förbereds för gemini-3.x utan att någon modell byts:
EU-multiregionen `eu` står på listan över tillåtna Vertex-regioner (med sin
egen värd, `aiplatform.eu.rep.googleapis.com`), inbäddningarna får en egen
region (`VERTEX_INBADDNING_REGION`), tänkandet skickas i den form gemini-3.x
tar, och uppstartskontrollen mot fel modellfamilj gäller också
stegmodellerna och bildmodellen. Standardvärdena (`gemini-2.5-flash`,
`europe-west1`) och alla värden i drift är orörda. Vilken modell som ska
användas är ägarens beslut; underlaget är
`docs/compliance/modellbyte-underlag.md`.

**Resonemanget.** Google anger 20 oktober 2026 som pensionsdatum för
gemini-2.5-pro, -flash och -flash-lite. Uppmätt mot projektets Vertex
2026-11-18 finns ingen av ersättarna i `europe-west1`, `europe-west4` eller
`europe-north1`: gemini-3.8-flash och gemini-3.5-flash-lite svarar bara i `eu`,
gemini-3.5-flash i `eu` och `europe-west3`. Utan `eu` på listan hade bytet till
3.8 krävt en kodändring, och listans egen kommentar sade att den skulle läggas
till i samma ändring som gör värden möjlig. `eu` är en EU-multiregion, där
Google anger att behandlingen stannar inom EU, och dataskyddsbedömningen
(`gemini-bedomning.md` avsnitt 7) föreslår själv att gå över till den.
`gemini-embedding-001` saknas i `eu`; med en egen region kommer
kunskapsbasens vektorer ur samma modell före och efter bytet. Tankebudgeten
är avvecklad för gemini-3.x: budget 0 gav ett anrop mot gemini-3.8-flash som
hängde i 90 sekunder, och 3.8 avvisar nivån MINIMAL med 400. Email Studio
skickade `reasoningEffort: "minimal"` och hade fallit på varje anrop med 3.8.

**I koden.** `config.py` (`VERTEX_EU_REGIONER`, `vertex_vard`,
`vertex_inbaddning_region`, `inbaddningsregion`, kontrollen av stegmodellerna i
`llm_provider_fault`), `agent/llm.py` (`gemini_tank_kwargs` med modell,
`lagsta_tankniva`), `agent/step_runner.py`, `agent/embeddings.py`,
`leads/discovery.py` (`_sokningens_tankande`), `leads/profil.py`,
`lib/llm/modellval.ts` (`vertexVard`, `lagstaTankande`, `eu` i `EU_REGIONER`),
`app/api/email-studio/route.ts`. Tester:
`tests/agent/test_modellbyte_gemini3.py`, `tests/invariants/test_inv_data_006.py`,
`lib/llm/modellval.test.ts`. Mätverktyget: `scripts/mat_modellbyte.py`.
INV-DATA-006 nämner `eu` och inbäddningsregionen.

## 2026-11-18 (Claude (agent), inom Antons uppdrag om synkflytten; väntar på Antons granskning) — Koden för att flytta synken till Railway, utan ändring i driften

**Beslut.** Kodstegen i `docs/compliance/synkflytt-plan.md` (smala hemligheter,
synkskriptet, läsrollen, driftavbilden) är byggda så att de kan ligga i
`development` och `main` utan att något i driften ändras. Själva flytten
(upplägg A, planens steg 0) är fortfarande Antons beslut. Handgreppen står i
`docs/compliance/synkflytt-runbook.md`.

**Resonemanget.** Synken var tionde minut ryms inte i gratisplanens 2 000
Actions-minuter (posten nedan), och planen kräver att koden finns i `main`
innan tjänsterna kan byggas där. Varje del är därför avstängd tills ägaren
slår på den:
- `synk.yml` och `migrera.yml` läser sex smala hemligheter och faller tillbaka
  på `ENV_DEPLOY` så länge de inte finns.
- Migration 122 skapar `synk_las` utan inloggning och utan lösenord. I
  development, där den körs vid pushen, går det inte att logga in som rollen.
- Synkskriptet beter sig som förut när det körs från Actions. Det tar nu ett
  rådgivande lås, som alltid är ledigt där eftersom Actions kör en synk åt
  gången. Det skriver också senaste försök och utfall i developments
  `mirror_meta`, och det sätter inte längre replica-läge på main utanför
  första synken, där main ändå är skrivskyddad. Spärrarna för körning hos
  Railway (INV-DATA-008) gäller bara när `SYNK_*_PG_URL` är satta.
- `scripts/railway_provision.py` föreslår `gemini` i stället för `deepseek` som
  startvärde för en ny miljö utan leverantör. Uppstartsspärren vägrar ändå
  DeepSeek där data är riktig, och ett startvärde ska inte peka dit.

**Inte byggt.** Planens steg 9 (PR-kontrollen över HTTPS) kräver en ny nyckel
i båda miljöerna. Steg 10 (insyn i panelen och larm) ändrar vad development
visar. Båda väntar på beslut.

---
## 2026-11-18 (Anton) — Webbplatsskanningen startas av onboardingen och kompletterar

**Beslut.** Anton, på frågan om guidens löfte att agenterna läser sajten:
"Se till att scanningen startas automatiskt, och att den kompletterar, inte
skriver över kundens egna uppgifter."

**Resonemanget.** Guiden lovade att agenterna läser webbplatsen, men
kunskapsbasen var tom efter onboardingen: skanningen (`app/kb_skanning.py`)
fanns, men inget startade den och ingenting av den sparades.

**I koden.**
- Onboardingen startar skanningen åt kunden när paketet har supportagenten
  (`lib/snajp/webbplatsskanning.ts`, anropad från `lib/actions/onboarding.ts`).
  Inloggningsvägen startar den aldrig: en ny hämtning är tillägget Synkad
  kunskapsbas, inte uppsättningen (`docs/pilot_onboarding.md`).
- Skanningen skriver FÖRSLAG, aldrig artiklar (migration 121,
  `ss_kb_forslag`). Ett förslag blir en ny artikel först när kunden lägger
  till det, genom samma väg som en handskriven artikel. Kundens egna artiklar,
  affärskontext, målgrupp och röstdokument rörs aldrig.
- "Kompletterar" är mekaniskt: ett utkast med samma rubrik som en artikel
  kunden har föreslås inte, ett avvisat utkast kommer inte tillbaka vid nästa
  skanning, och två klick blir aldrig två artiklar (`nya_forslag` i
  `app/api/kb.py`, låst av `tests/api/test_kb_forslag.py`).
- Förloppet och utfallet sparas (`ss_kb_skanningar`) och syns i Översikt ›
  Kom igång och överst i Kunskapsbas, även efter en omladdning. En skanning
  som inte kunde starta sparas med skälet. En skanning i taget.

**Agentens val, som Anton kan ändra.** Förslagen läggs inte in automatiskt.
Kunden lägger till dem, ett i taget eller alla på en gång. Skälet är
skanningsmodulens egen regel, att utkasten godkänns av en människa: en siffra
som inte står i källsidan sänker utkastets säkerhet, och agenten citerar det
som står i basen. Vill Anton att förslagen läggs in direkt är det en ändring i
`_spara_utfall`.

## 2026-11-18 (agenten, på Antons uppdrag) — Onboardingen efter den visuella genomgången

Anton beställde en genomgång av hela onboardingen, sida för sida, och att
bristerna skulle rättas tills varje steg håller för en professionell kund.
Besluten nedan är agentens, fattade under genomgången. Anton har inte godkänt
dem var för sig och kan ändra dem.

**Beslut 1: onboardingen frågar efter företagets namn.** Arbetsytan hette
"<kontots namn> workspace" (signup-triggern), och backendens kundnamn tas ur
arbetsytans namn. Uppmätt i den lokala stacken: en nyss upplagd kund hette
"Anna Testsson workspace" i `ss_tenants`, och det namnet står i sidfoten på
varje utskick. Namnet sätts genom en RPC (migration 120), eftersom
`workspaces` har radskydd utan uppdateringsregel och en vanlig UPDATE träffar
noll rader utan att fela.

**Beslut 2: fliken "Prova demo" på inloggningen är en länk till /demo.**
Fliken kunde bara svara med ett fel, eftersom mejlvägen för åtkomstlänken
aldrig kopplades (`requestDemoAccess`). Demon är öppen på /demo. Funktionen
ligger kvar i `lib/actions/auth.ts`, oanvänd, tills någon bestämmer om
åtkomstlänken ska byggas.

**Beslut 3: `/login?mode=signup` öppnar läget Skapa konto**, och de två
länkar som betyder "kom igång" pekar dit (demobannern i AppShell,
DemoKorning). Förut landade en ny kund under rubriken "Välkommen tillbaka".

**Beslut 4: Google- och Microsoft-knapparna visas bara när de är
konfigurerade** (`AUTH_GOOGLE_ID`, `AUTH_MICROSOFT_ENTRA_ID_ID`). En knapp som
alltid svarar "inte konfigurerad än" är sämre än ingen.

**Beslut 5: en arbetsyta utan aktivitet får en startruta överst på
översikten** (`components/dashboard/KomIgang.tsx`). Anton tog bort hälsningen
ur översikten 2026-10-07 och det beslutet står kvar: rutan visas bara medan
arbetsytan saknar körningar, och försvinner av sig själv. Skälet är att den
nya kunden annars landar på en statistiksida utan statistik, utan något som
säger vad nästa steg är. Varje rad leder till en sida som redan finns.

**Beslut 6: guiden validerar själv.** Formulären har `noValidate`. Alla fel
i ett steg visas på en gång vid sitt fält, webbadresser utan protokoll
godtas (webbläsarens `type="url"` nekade dem, trots att servern tar emot
dem), och postnumret ska ha fem siffror ("abc" gick igenom till fakturan).

**Öppet för Anton (besvarat samma dag, se posten ovan).** Guiden säger att
"agenterna läser er webbplats och lär sig resten själva", men skanningen
startades inte. Anton beslutade att den ska startas automatiskt.

**I koden.** `components/auth/OnboardingWizard.tsx`,
`components/auth/LoginForm.tsx` (`LoginSida`), `app/login/page.tsx`,
`lib/actions/onboarding.ts`, `components/dashboard/KomIgang.tsx`,
`components/dashboard/Aktivitet.tsx`,
`supabase/migrations/20261118090000_120_arbetsytans_namn.sql`,
`scripts/qa_ny_kund.mjs`.

## 2026-11-18 (Anton) — Repot är privat, och det som följer av det

**Beslut.** Repot `oloflun/snipe-leads` är privat sedan 2026-11-18 (Antons
beslut: "Repot ska vara privat och är ändrat till det nu, anpassa övriga beslut
efter det").

**Resonemanget.** Repot var publikt, och plattformsadminens lösenord låg i den
publika historiken. Dataskyddsgenomgången höll därför utkasten som beskriver
öppna brister utanför repot. Med ett privat repo kan de ligga där de hör hemma.

**Vad som ändrats till följd av beslutet (Claude (agent), samma dag):**
- Utkasten som hölls utanför repot är committade: `docs/pub-avtal.md`,
  DPIA:n, intresseavvägningen, incidentloggen och `docs/JURIDIK_ATGARDER.md`.
  Compliance-underlaget (ramverkskörningar, policyer, rutiner, brev, utredningar
  och bevis) ligger i `docs/compliance/`. Görs repot publikt igen ska den mappen
  flyttas ut först: den beskriver brister i detalj, och policytexterna bygger
  på AGPL-licensierade mallar ur Comp AI.
- GitHubs hemlighetsskanning, push-skydd och kodskanning finns inte för
  privata repon på gratisplanen och är avstängda. I stället skannar jobbet
  `hemligheter` i `verify.yml` varje ny commit med gitleaks. Dependabot
  fungerar som förut.
- Grenskyddet på `main` gäller inte längre (det kräver betald plan för privata
  repon). Kravet på kodägarens godkännande är alltså inte tekniskt framtvingat.
  Regeln står kvar: release till `main` är Antons handgrepp.
- Gratisplanen ger 2 000 Actions-minuter i månaden. Övervakningen går därför
  en gång i timmen i stället för var 15:e minut. Synken (`synk.yml`, var tionde
  minut) skulle ensam ta mer än kvoten om GitHub körde den som schemalagt; det
  talar för att flytta den till Railway enligt `docs/compliance/synkflytt-plan.md`.
  När kvoten är slut stannar alla workflows, även migrationerna.

**Kvar trots beslutet.** Lösenordet som låg i den publika historiken ska fortfarande
bytas: historiken kan redan vara kopierad.

---

## 2026-11-18 (Claude (agent), inom Antons uppdrag 2026-11-17 om EU-compliance) — Modellanropen maskeras och hålls i EU i koden

**Beslut.** Fem brister som dataskyddsbedömningen av Gemini på Vertex AI pekade
ut stängs i kod: personnummer maskeras också före uppsägningsklassaren och före
varje inbäddning; tjänsten vägrar starta där data är riktig om en Vertex-region
inte ligger i EU, om `LLM_BASE_URL` pekar någon annanstans än Vertex i EU, eller
om `LLM_PROVIDER` är `openai`; Email Studio väljer aldrig OpenAI eller en region
utanför EU där data är riktig; och ett test håller Googles sökgrundning kvar i
leadssökningen. Invarianterna INV-DATA-006 och INV-DATA-007.

**Resonemanget.** Bedömningen fann att DPIA:n och integritetspolicyn lovar att
personnummer maskeras, men två vägar skickade dem omaskerade till Google:
klassaren fick hela meddelandet och inbäddningarna räknades på omaskerad
kundtext. Maskeringen sitter nu där texten lämnar huset, ett ställe per väg,
så att en ny anropare inte kan glömma den. Inbäddningarna maskeras i
`embed_text`, som både skrivning och läsning går genom; text utan personnummer
går ut oförändrad, så kunskapsbasens vektorer och svarscachen påverkas inte
(svarscachen tar dessutom bara emot frågor utan personnummer). Regionerna och
bas-URL:en lästes ur miljön utan kontroll: en felaktig variabel hade tyst
flyttat behandlingen ur EU, och det skulle ingen märka. Spärren är samma sort
som DeepSeek-spärren: den kraschar hellre än varnar, och bara där data är
riktig. OpenAI står inte i underbiträdesförteckningen och leverantörsgranskningen
säger "inte för kunddata"; att släppa in det i drift är ett avtalsbeslut.
Driften använder inte OpenAI i dag (`LLM_PROVIDER=gemini` i api i båda miljöerna,
ingen `OPENAI_API_KEY`, `GOOGLE_CLOUD_REGION`, `VERTEX_RESERVREGIONER` eller
`LLM_BASE_URL` i någon tjänst enligt konfigurationsutdraget 2026-11-17), så
ingenting ändras vid deploy. Sökgrundningens frågor sparas hos Google i tre
dygn utan möjlighet att stänga av; i dag får den bara målgrupp, kriterier och
bolagsnamn, och testet hindrar att det ändras utan att någon tar ställning.

**I koden.** `snajp-support/app/config.py` (`VERTEX_EU_REGIONER`,
`bas_url_tillaten`, `Settings.llm_provider_fault`, `Settings.vertex_regioner`),
`app/agent/llm.py` (`vertex_region`, `_resolve_base_url`),
`app/agent/embeddings.py`, `app/agent/retention_classifier.py`,
`app/leads/discovery.py`, `lib/llm/modellval.ts` (`EU_REGIONER`,
`dataskyddsvarning`), `app/api/email-studio/route.ts`. Inte gjort här:
modellbytet från Gemini 2.5 (ägarens beslut), cachen i Google Cloud och ett
servicekonto per miljö (ägarens hand), fler maskeringstyper.

## 2026-11-18 (Claude (agent), inom Antons uppdrag om EU-compliance; ändringarna väntar på Antons granskning) — Render-koden tas bort ur repot

**Beslut.** Allt i repot som kan skriva till, deploya till eller hålla liv i
den avvecklade Render-stacken tas bort: skrivvägen i `scripts/keys.py`
(Render-pushen och det den anropade), driftkontrollen `scripts/verify_render.py`
och blueprinten `snajp-support/render.yaml`. Samtidigt tas `keys.py`:s
skrivväg mot appens Vercel-projekt bort (push och pull), som bara tjänade samma
döda stack. Invarianten INV-DEPLOY-001 stod mot blueprinten och skyddar nu
samma sak, byggkontexten för api, mot filen som styr Railway.

**Resonemanget.** En undersökning 2026-11-18 visade att Render inte fyller
någon funktion: ingenting i koden, hos Railway eller i DNS pekar dit, och
loggarna visar ingen kundtrafik. Koden låg ändå kvar och var farlig. Ett enda
kommando kunde skriva backend-hemligheter och DeepSeek som leverantör till
båda Render-tjänsterna och starta en deploy, alltså återinföra den
tredjelandsöverföring som spärrades 2026-08-24. Blueprinten sa själv att en
blueprint som ligger kvar är en tjänst som kan återuppstå. Kod som inte
behövs och som kan göra skada tas bort i stället för att märkas som vilande.

**Läget hos leverantörerna.** Båda Render-tjänsterna är suspenderade sedan
2026-11-17 23:46 UTC. Det gamla Vercel-projektet `snajp` är pausat 2026-11-18,
med inloggningsskydd och avstängda förhandsdeployer. Apex-omdirigeringen
(Vercel-projektet `snajp-apex`) berörs inte.

**I koden.** `scripts/keys.py` (Render- och Vercel-vägarna borta, övriga
kommandon oförändrade), `scripts/verify_render.py` och `snajp-support/render.yaml`
borttagna, `tests/invariants/test_inv_deploy_001.py` och posten i
`ARCHITECTURE_INVARIANTS.md` anpassade, nytt test
`tests/invariants/test_render_avvecklad.py` som fäller om Render-koden kommer
tillbaka. Instruktioner om Render i `DEPLOY.md`, `DEPLOY_KEYS.md`, `RAILWAY.md`,
`AUTH.md` och `snajp-support/README.md` är ersatta med en mening om att stacken
är avvecklad.

**Kvar hos ägaren.** Radera båda Render-tjänsterna (de är bara suspenderade)
och ta bort Renders åtkomst till repot (GitHub-appen). Rotera de hemligheter
som legat hos Render. Återkalla Render-API-nyckeln och ta sedan bort raderna
`RENDER_API_KEY` och `PREVIEW_RENDER_SERVICE_ID` ur `.env.deploy`. Begär en
raderingsbekräftelse från Render för tjänsterna, loggarna och
miljövariablerna.

## 2026-11-18 (Anton) — Extern övervakning, säkerhetskontakt och Dependabot

**Beslut.** Fyra luckor som en genomgång mot ISO 27001 visade fylls: en
schemalagd övervakning av produktionen som larmar via ett GitHub-ärende, en
kontaktväg för säkerhetsrapporter (`SECURITY.md`, `security.txt`), veckovisa
beroendeuppdateringar via Dependabot, och minsta möjliga rättigheter i de nya
arbetsflödena. Beställt av Anton genom genomgången; resonemanget nedan är
beställningens, inte hans egna ord.

**Resonemanget.** Tjänstens interna larm är troligen inte aktiva (sändvägens
variabler saknas i driften) och ingen extern övervakning fanns. Går
produktionen ner, eller faller den tillbaka till minnesläge för jobbkön eller
lagringen eller till simuleringsläge, får ingen veta det förrän en kund hör av
sig. Repot är publikt, Actions är gratis här och ägaren får mejl när ett
ärende skapas, så ett ärende är den billigaste larmvägen som redan når fram.

**I koden.** `.github/workflows/overvakning.yml` (var 15:e minut,
etiketten `driftlarm`, kända begränsningar i filens huvud),
`.github/dependabot.yml`, `SECURITY.md`, `public/.well-known/security.txt`.
Svarstiden för en säkerhetsrapport är inte beslutad och står som `[FYLL]`.

## 2026-11-17 (Anton) — Jobbkön flyttas till Railways egen Redis

**Beslut.** Jobbkön flyttas från Redis Cloud till Railways egen Redis, i
stället för att Redis Cloud uppgraderas. Antons ord: "Ja, flytta", som svar på
frågan om jobbkön skulle flyttas till Railways egen Redis i stället för att han
uppgraderar Redis Cloud.

**Resonemanget.** Skälen kommer ur dataskyddsgenomgången samma dag, inte ur
Antons egna ord utöver beslutet. Redis Cloud-databasen låg på gratisplanen,
som saknar stöd för krypterad anslutning, så TLS gick inte att slå på enligt
beslutet "Gör alla fyra" tidigare samma kväll. Alternativet var en betald
plan. Flytten tar bort trafiken över publikt nät, tar bort en leverantör ur
kedjan när den gamla databasen är raderad, och skiljer miljöerna åt:
produktionen och testmiljön delade tidigare samma databas. Ingen ny leverantör
tillkommer, eftersom Railway redan är underbiträde och all behandling där sker
i Amsterdam.

**I driften.** Testmiljön använder sin befintliga Redis-tjänst hos Railway. I
produktionen skapades en ny Redis-tjänst hos Railway med samma uppsättning som
testmiljöns: lösenord, egen volym, Amsterdam, ingen publik adress. Api-tjänsten
i båda miljöerna når Redis över Railways privata nätverk. Uppstartsloggen i
båda miljöerna visar att jobbkön, svarscachen, chattströmmen och leadsströmmen
kör mot Redis, och hälsokontrollen svarar ok. Pågående jobb och cache i den
gamla databasen följde inte med; jobben lever högst en timme och cachen byggs
upp igen. `lib/bolag.ts` för Redis Cloud som "avvecklas".
`scripts/redis_tls_pa.py` är inaktuellt och får inte köras.

**Kvar.** Den gamla Redis Cloud-databasen har kvar cache och arbetsminne tills
livslängden gått ut eller databasen raderas. Att radera den och säga upp kontot
är Antons beslut och inte gjort. Den gamla adressen ligger i en reservvariabel
på api-tjänsten, så att bytet går att backa; den tas bort när flytten fått gå
några dagar. Bedömningen av tiden då trafiken gick okrypterat är Antons
(`INCIDENT_RESPONSE.md`, 2026-08-29).

---

## 2026-11-17 (Claude (agent), inom Antons uppdrag 2026-11-17 om EU-compliance; ändringarna är ocommittade tills Anton godkänt) — En mottagaradress är personlig om den inte är en känd funktionsadress

**Beslut.** En mottagaradress räknas som personlig när lokaldelen inte är en
känd funktionsadress. Förut krävdes en punkt eller ett bindestreck, så
`anna@bolaget.se` och `andersson@bolaget.se` fick den korta foten utan
information enligt art. 14 och utan krav på länk till avsändarens
integritetspolicy. Nu får de den fullständiga foten. Funktionsadresser (info@,
kontakt@ och de övriga i listan) får fortfarande den korta foten enligt
beslutet 2026-10-24. `vd@` och `ceo@` räknas som personliga.

**Resonemanget.** Funktionens egen docstring säger principen: att flagga en
funktionsadress för mycket kostar ett stycke text, att missa en personlig
adress kostar ett regelbrott. Därför avgörs frågan av en lista över kända
funktionsadresser och inte av hur lokaldelen ser ut. `vd@` och `ceo@` når en
enskild, utpekbar person och är därför personliga. Poängsättningen av
kontaktvägen och rollkopplingsflaggan behåller det gamla avgörandet, så
rangordningen av leads ändras inte. Utkastens låsta facit
(INV-LEADS-UTKAST-002) är orört och dess tester går gröna.

**Följd att känna till.** Sidfoten byggs om i sändögonblicket, så redan
godkända, köade utkast till namnadresser får den fullständiga foten. En kund
som saknar `policy_url` i kundregistret får sådana utskick stoppade av
spärrens regel 2, med besked, tills `policy_url` är ifylld.

**I koden.** `snajp-support/app/leads/sources/base.py` (listan
`FUNKTIONSADRESSER` och den nya egenskapen `epost_bar_namnform`, som
poängsättningen och rollkopplingen använder), avdelningsorden i
`snajp-support/app/leads/discovery.py` (`AVDELNINGSORD`). Test:
`snajp-support/tests/leads/test_personlig_adress.py`. Inte committat eller
driftsatt.

---

## 2026-11-17 (Anton) — Kundmejl går inte till TypeSafe

**Beslut.** Kundernas kundmejl skickas inte längre till TypeSafe (modellen
Jev). Antons ord: "Gör alla fyra", som svar på frågan om kundmejl till
TypeSafe skulle stängas av, hemlighetsskanning slås på, Redis få TLS och
säkerhetskopior slås på.

**Resonemanget.** Skälen kommer ur dataskyddsgenomgången samma dag, inte ur
Antons egna ord utöver beslutet. TypeSafe var aldrig godkänd som
underbiträde och saknades i alla underbiträdesförteckningar. Leverantören
behandlar i USA utan anslutning till Data Privacy Framework. Dess avtal ger
en tidsobegränsad rätt att härleda och använda telemetri ur kunddata. Beslutet
2026-09-30 i `snajp-support/app/leads/jev.py` sa redan att Jev aldrig ser
kundmejl.

**I driften.** Inkorgsklassningen via Jev är avstängd (`INKORG_JEV` av) i main
och development sedan 2026-11-17 20:54 UTC. Nya deployer kom upp och
hälsokontrollerna svarar ok. Inkorgen sorteras nu bara av kodreglerna. Jev
används fortfarande i leadsdelen, där den får prospekts publika
bolagsuppgifter och sidutdrag utan e-postadresser, telefonnummer och
personnummer. TypeSafe-posten i `lib/bolag.ts` säger detsamma.

**Kvar.** Kundmejltext som skickades före avstängningen ligger kvar hos
TypeSafe enligt deras villkor; radering och bekräftelse är inte begärda.
Bedömning av anmälningsplikt och underrättelse till berörda kunder är Antons
(`INCIDENT_RESPONSE.md`, 2026-11-17). Beslut om leadsdelen återstår
(`docs/pub-avtal.md`, Bilaga 3). Slås inkorgsklassningen på igen ska
underbiträdeslistan ändras först.

---

## 2026-11-17 (Claude (agent), inom Antons uppdrag 2026-11-17 om EU-compliance; ändringarna är ocommittade tills Anton godkänt) — Google AI Studio får inte bära kunddata

**Beslut.** Där data är riktig vägrar tjänsten starta med gemini utan ett
läsbart servicekonto för Vertex AI, och varje reservväg till Google AI Studio
vägrar själv (INV-DATA-004). Servicekontot i main och development är
kontrollerat och klarar spärren.

**Resonemanget.** AI Studio har ingen EU-bunden behandling, och på
gratisnivån får Google använda innehållet. Nyckeln var satt i båda miljöerna,
så ett saknat servicekonto hade tyst skickat kundmejl dit. Gränsen och skälet
är desamma som för DeepSeek-spärren: en felaktig konfiguration ska dö
högljutt, inte tyst skicka kunddata vidare. Att ta tillbaka AI Studio i drift
är ett avtalsbeslut, inte ett kodbeslut.

**I koden.** `snajp-support/app/config.py`, `snajp-support/app/agent/llm.py`,
`snajp-support/app/leads/discovery.py`, `lib/llm/modellval.ts`. Spärr:
INV-DATA-004, test i `snajp-support/tests/invariants/test_inv_data_004.py`.

---

## 2026-11-17 (Claude (agent), inom Antons uppdrag 2026-11-17 om EU-compliance; ändringarna är ocommittade tills Anton godkänt) — Avtalsgrinden är standard för kunder som läggs upp manuellt

**Beslut.** En ny kund som skapas utan uttryckligt värde får avtalsgrinden på:
ingen trafik på chatt, inkommande mejl och kanaler förrän ett avtalsdatum är
registrerat. Befintliga kunder behåller sitt värde. Test-, demo- och interna
konton anger av uttryckligen. Plattformsadmin slår på och av grinden i Kunder
& Data, där det också syns när en kunds trafik är stoppad.

**Resonemanget.** Snajp är personuppgiftsbiträde och får enligt GDPR art. 28
inte behandla en kunds personuppgifter utan biträdesavtal. Som opt-in berodde
skyddet på att någon kom ihåg en SQL-sats, och bara piloten hade den satt.
Migrationen ändrar bara standardvärdet, ingen rad, så ingen levande trafik
stängs av vid deploy.

**Öppen fråga till Anton.** Självregistrerade kunder och testarbetsytor skapas
med grinden av, så att provflödet fungerar som i dag. Det betyder att en
självregistrerad kund fortfarande kan koppla en riktig inkorg utan avtal. Två
vägar: (a) låt registreringen ingå avtalet genom att villkoren och
biträdesavtalet godkänns där, och registrera datumet automatiskt, eller (b)
slå på grinden även för dem och registrera avtalet för hand. (a) kräver ett
juristgranskat biträdesavtal.

**I koden.** Migration `118_avtalsgrind_standard.sql` (ingen `update`).
`POST /api/keys` tar det valfria fältet `kraver_avtal`. Adminvyn:
`components/admin/Kunddata.tsx`, `lib/actions/kunddata.ts`,
`snajp-support/app/api/admin_kunddata.py`. Undantaget för provflödet:
`lib/snajp/testtenant.ts`, `scripts/koppla_testytor.py`. Spärr: INV-AVTAL-001,
test i `snajp-support/tests/invariants/test_inv_avtal_001.py`. Adminvyn är
inte granskad i en webbläsare, och migrationen är inte körd.

---

## 2026-11-17 (Claude (agent), inom Antons uppdrag 2026-11-17 om EU-compliance; ändringarna är ocommittade tills Anton godkänt) — AI-upplysningen garanteras av koden, inte av modellen

**Beslut.** Chatten visar "AI-assistent" i huvudet, också i kundernas
inbäddade widget. Ett supportmejl som går ut utan mänsklig granskning får en
fast rad efter signaturen om att en AI-assistent skrev svaret och hur kunden
når en människa. Ett svar som en människa godkänt får ingen rad. Den som i ett
mejl ber om en människa eskaleras av koden.

**Resonemanget.** AI-förordningen (EU 2024/1689) art. 50.1 gäller sedan
2026-08-02: den som interagerar med ett AI-system ska få veta det, om det inte
är uppenbart. Systemprompten förbjöd agenten att utge sig för att vara
människa, men sade också att den inte behövde inleda med att den är en AI. En
upplysning som hänger på modellens goda vilja är ingen upplysning. Ett
granskat svar är människans svar och får därför ingen rad. Raden lovar en
människa till den som ber om en, och ett löfte i ett mejl ska hållas av kod:
inkommande mejl prövas därför mot samma regel som chatten redan använder.
Leadsagentens utskick är inte ändrade. Om art. 50 gäller autonoma första mejl
och uppföljningar är en fråga för juristen.

**I koden.** `components/snajp/SupportChat.tsx` (huvudet).
`snajp-support/app/email_pipeline/processor.py`: `AI_UPPLYSNING`,
`med_ai_upplysning` och eskaleringen via `support_regler.ber_om_manniska`.
Spärr: INV-AI-001, test i `snajp-support/tests/invariants/test_inv_ai_001.py`.
Mejlvägen skriver alltid svenska i dag; den engelska raden finns men används
inte än. Chattens huvud är inte granskat i en webbläsare.

---

## 2026-11-17 (Claude (agent), inom Antons uppdrag 2026-11-17 om EU-compliance; ändringarna är ocommittade tills Anton godkänt) — Jev får inte se personnummer, och /villkor säger vad utskicksspärren faktiskt kontrollerar

**Beslut.** Två rättningar ur dataskyddsgenomgången inför första betalande kund:

1. Texten som går till TypeSafe (Jev) maskerar nu personnummer och
   samordningsnummer, utöver e-post och telefon.
2. Avsnittet om utskick i `/villkor` beskriver spärren som den är: den kräver
   företagsnamn och avregistreringslänk, och vid en personlig adress även
   art. 14-information och policylänk. Organisationsnummer och postadress tas
   med i sidfoten när Kunden har angett dem, och Kunden ansvarar för att ange dem.

**Resonemanget.** Jev klassar inkorgen (ämnesrad och upp till 1 500 tecken
kundmejl) och triagerar leads. Kundmejl bär ibland personnummer, och
supportagenten maskerade dem redan före sitt modellanrop medan Jev-vägen bara
tog bort e-post och telefon. Telefonmönstret åt dessutom slutet av ett
personnummer ("850101-1236" blev "85[telefon]") och lämnade födelsedatumet
kvar, så maskeringen körs före telefonmönstret. Villkoren lovade sedan Antons
beslut 2026-10-10 (org.nr och postadress stoppar aldrig ett utskick) en
kontroll som koden inte gör; en villkorstext som påstår mer än koden gör är ett
löfte till kunden som bryts.

**I koden.** `snajp-support/app/leads/jev.py:_utan_personuppgifter` anropar
`app/moderation/maskering.maskera_personnummer` (ingen ny regex), test i
`tests/leads/test_automation.py`. `app/villkor/VillkorSida.tsx`, posten
`utskick`, svenska och engelska. Spärren är oförändrad
(`app/leads/send_guard.py`, regel 1 och 2).

---

## 2026-11-16 (Anton) — Agenterna svarar bara med det som går att belägga, annars lämnar de över

**Beslut.** Anton, först: "Djupdyk i NVIDIA/auto-ontology och inkorporera det
mot vår nuvarande kunskapsbas för att förbättra träffsäkerheten samt
säkerställa att agenterna fysiskt inte kan hallucinera eller blanda ihop
information." Sedan, om det som återstod: "det måste gå att lita på den till
hundra procent, är den inte hundra procent säker måste den eskalera, men kom
ihåg att målet är alltid hantera ärenden så långt som möjligt på egen hand …
men då behöver vi ha fakta att luta oss mot, samt ett tydligt och enkelt sätt
att förklara hur det fungerar mot kund." De enskilda valen nedan gjordes i
arbetet. Inget är pushat; nivån Ordagrant är inte standard förrän den är mätt.

**Resonemanget.** Auto-ontology är en text-till-SQL-stack över
relationsdatabaser. Vår kunskapsbas är fritext per kund, så stacken passar
inte, och den hade skickat kundtext till en ny leverantör utan avtal. Det som
gick att föra över är dess mönster: modellen pekar ut och koden slår upp
ordagrant, värden prövas mot källan, kopior hålls isär, och utan belägg vägrar
systemet. Hundra procent går bara att lova om det som sägs är kundens egen
text: en omskrivning kan alltid ändra innebörden (ett struket "inte", ett
struket villkor), och ingen kod kan gå i god för en fri formulering.

**I koden, val för val.**

- **Namngivna källor** (INV-GROUND-002). Varje kontaktuppgift och varje tal
  prövas källa för källa, och körningen sparar vilken källa som bär vad.
  Kundens egen text får upprepas men bär aldrig ett pris, en procentsats, en
  frist eller en webbadress. "8 år" bär inte "8 månader". En källhänvisning
  till en artikel modellen aldrig fick gör frågan obesvarad.
- **Nivån Ordagrant** (INV-GROUND-003). Svaret byggs av kod: hälsningen,
  agentens frågor och meningar ord för ord ur en källa. Valet att bygga i kod
  och inte pröva modellens text: det enda sättet att slippa en lista över
  tillåtna ord, där varje öppet ord är ett hål. Valet att lämna över svar på
  andra språk: en översättning är en ny formulering, och Antons regel är att
  det som inte är säkert lämnas över. Valet att inte göra nivån till standard:
  den är inte mätt mot riktig modell, och den ändrar hur varje svar ser ut.
- **Iris** (INV-GROUND-004). Bara ordagrant verifierade citat och uppmätta
  webbsignaler gör ett tal eller ett namn tillåtet. Den exakta text som köas
  grindas, också ämnesraden. Två tester som låste fast hålet är ändrade;
  utkastens facit är orört.
- **Språkkorrekturen kan inte lägga till något.** Den körs efter grindarna
  (leadskön, supportmejlen), så en korrektur som tillför ett tal, en länk, ett
  kundnamn eller ett superlativ förkastas.
- **Kunskapsbasens artiklar har källa och giltighetstid** (migration 117). En
  utgången artikel används inte i svar men ligger kvar i listan. Valet att
  inte bygga en redigeringsväg eller ett fält i portalen nu: ändringen i
  portalen går inte att granska visuellt på den här maskinen i dag.
- **Svarscachen** serverar ett sparat svar bara när frågans nyckelord är
  desamma, inte bara när vektorerna ligger nära.
- **Mejlets delsvar** går genom faktagrinden innan en människa granskar det.
- **Evalsviten mäter sökträffen**: om sökningen hämtade artikeln som bär
  svaret. Det talet är taket för hur mycket agenten kan klara själv.
- **Kundförklaringen** står i `docs/SA-FUNGERAR-FAKTAKONTROLLEN.md`, och
  nivåernas beskrivning i portalen säger samma sak.

**Kvar, och varför.** Att rätt mening valdes går inte att bevisa i kod.
Vektorerna i kunskapsbasen är inte ifyllda (kräver en körning mot en delad
miljö). Portalen visar inte källa, giltighetstid eller belägg än.

---

## 2026-11-16 (Sebbe) — 100 utskick om dagen, äldst först, ett i minuten från 08:00

**Beslut.** Sebbe bad först om att "utskicken man gör inte ligger väntandes
till måndagar 08:00 … Utskicken ska hanteras 08:00 varje vardag och gå ut
varje dag 08:00. Så alla körningar jag gör ikväll ska skickas ut imorgon 08:00
automatiskt". Det som höll kvar utskicken var inte veckodagen utan dagstaket
på 50 och kön bakom det. Tillfrågad om taket och ordningen svarade Sebbe:
"100 är takt per dag, börja med de äldre utskicken. Se till att inget hamnar i
skräpposten, alltid hög kvalitet." Och: "du får godkännelse för allt som
krävs." Valen nedan gjordes i arbetet.

**Resonemanget.** Läst ur development (en spegel av main) 2026-11-16 07:30,
bara antal: sändaren skickade redan 08:00 varje vardag, men högst dagens tak,
50 sedan 11-11 (20, 25 … 50 med upptrappningen). Bakom taket stod 3 868
godkända utkast i kö, det äldsta köat 10-26, och kön skickas äldst först.
Kvällens körningar hamnade alltså ungefär 77 vardagar bak, medan listan sa
"Godkänt – skickas 08:00" om vartenda ett, och efter en helg "mån 08:00". Två
saker till syntes: dagens 50 gick ut inom samma minut 08:00, och sändaren
prövade varje köpost var för sig varje minut dygnet runt, med runt tio
databasfrågor per post (sändspärrarna, textputsen, en skrivning). Med 3 868
poster blev det tiotusentals frågor i minuten i samma process som svarar
sidorna. Det växte med antalet godkända utkast, och det kan vara en del av
laggandet 11-15.

**I koden, val för val.**

- **Taket är 100** (`send_guard.TAK_PER_DAG`). Upptrappningen står kvar, fem
  fler om dagen än den största dagsvolymen senaste veckan, så taket nås på
  ungefär tio sändardagar (55, 60 … 100) och aldrig med ett hopp. Det var
  hoppet 20 → 40 → 80 → 160 i oktober som skickade 600 mejl i skräpposten.
  Valet följer Sebbes "se till att inget hamnar i skräpposten". Vill vi upp
  till 100 direkt är det en konstant, `UPPTRAPPNING_STEG`.
- **Äldst först** som förut (`list_due_send_queue`, scheduled_at och sedan
  created_at), enligt Sebbes svar.
- **Ett mejl i minuten per kund**, med start 08:00 (`scheduler.TAKT_SEKUNDER`,
  ett per varv i `process_godkanda`). Hundra kallmejl samma sekund är ett
  maskinmönster som mottagarnas filter reagerar på oavsett text. Dagens 100
  är ute ungefär 09:40. Takten gäller också Godkänn och skicka, så att hundra
  godkännanden i listan inte heller blir hundra mejl på en minut. Det första
  går direkt, och resten står kvar som godkända och tas i tur och ordning.
  Skicka nu ur Skickat har ingen takt, för där har en människa valt det
  enskilda mejlet och tiden. Taket gäller där som förut.
- **Sändaren gör inget när inget kan gå ut** (`scheduler.sandfonster_oppet`):
  kväll, natt, helg och helgdag läses kön inte alls. Inom fönstret prövas
  kundens egna spärrar (takten, dagens tak, leveransstoppet) en gång per kund
  och varv (`send_guard.kundens_volymgrind`, `scheduler.kundens_historik`), i
  stället för en gång per köpost. De säger samma sak om varje mejl i kön.
  Efter 16 går bara svar i trådar där leadet svarat (`trad_svarad_at` i
  förfallolistan). En stoppad post (karens, suppression) släpper fram nästa,
  högst 25 per varv. Utfallet per mejl är detsamma som förut, och alla sex
  spärrar körs fortfarande på varje mejl som skickas.
- **Listan visar när varje utkast går ut** (`app/leads/sandplan.py`).
  Sändtiden är köns plan: äldst först, ett i minuten, dagens tak med
  upptrappningen, bara vardagar. "Skickas 08:00" om alla blev sant för ingen.
  Längre fram än en vecka visas datumet (`lib/leads/utkast.ts:sandtid`).
  Texterna om att godkända "skickas när sändfönstret öppnar" säger nu att de
  skickas i tur och ordning från kön. Planen är en uppskattning: ett stoppat
  utkast eller ett svar emellan flyttar resten en plats.

**Kvar.** Kön är 3 868 utkast. Med upptrappningen till 100 tar den ungefär
åtta veckor att beta av, och nya godkännanden hamnar sist. Utkasten från 10-26
är tre veckor gamla när de går. Hela ändringen gäller i main först när
release-PR:en (oloflun/snipe-leads#44) är mergad. Development skickar inget
(spegeln, `utskick_bara_i_main`).

---

## 2026-11-15 (Sebbe) — Antalet leads och körningar får inte märkas i sidan

**Beslut.** Sebbe: "Nu när vi har 4400 utkast på snajp leads så börjar sidan
gå långsamt och det laggar mer och mer … Du ska lösa uppgiften och problemet
så att antalet leads körningar inte påverkar hemsidans upplevelse. Det får
inte lagga, hacka eller gå långsamt oavsett." Och: "Du får godkännelse för att
göra allt som krävs." De enskilda valen nedan gjordes i arbetet.

**Resonemanget.** Mätt hos den största kunden i development (5 615 prospekt,
3 126 synliga leads, 1 937 godkända utkast som väntar): servern svarade i
rimlig tid per anrop, men sidorna hämtade och ritade allt. Iris-listan var
9,6 MB i sex anrop efter varandra (~3,5 s), Översiktens munkdiagram hämtade
samma 9,6 MB för att räkna, körningslistan var 2,8 MB för 100 körningar (98 %
trattens bortvalda bolag och barnjobben), och Skickat (3,2 MB, varje mejls
text) hämtades vid varje besök på Leads för två nyckeltal. I webbläsaren stod
varje lead två gånger (tabellen och korten, den ena dold) och radrörelsen läste
stilen för varje rad efter varje rendering. Med samma mängd syntetiska leads
tog ett klick i en kryssruta 4,7 s och ett tangenttryck i sökfältet 3,7 s
(utvecklingsläge). Allt det växer med antalet leads och körningar; det var
därför det blev sämre för varje körning.

**I koden, val för val.**

- **Listläget** (`GET /leads/prospects?lista=1`, `app/leads/listvy.py`): bara
  det tabellen visar per rad, upp till 5 000 rader per anrop. Researchen läses
  inte ens ur databasen. Lådan hämtar den fulla raden som förut.
- **Iris-listan, Skickat och undanvyerna visar 100 rader per sida**
  (`components/leads/sidindelning.tsx`). Valet: sidor och inte en lång lista
  med "Visa fler", eftersom det är det enda som håller sidan lika snabb hur
  många leads det än blir. Filtren, Markera alla och massåtgärderna gäller
  fortfarande hela urvalet; en länk till ett lead öppnar sidan där det står.
- **Tabell eller kort**, aldrig båda i sidan.
- **Fördelningen räknas på servern** (`GET /leads/prospects/fordelning`), med
  samma synlighetsregel som listan (`listvy.synliga`, en regel på ett ställe).
- **Körningslistan är ett sammandrag**: `tratt_antal` och `jobs_antal` i
  stället för listorna. Den utfällda raden hämtar körningen själv. `?detalj=1`
  ger det gamla svaret.
- **Skickat hämtas när det öppnas**; nyckeltalen kommer från
  `GET /leads/skickat/antal`, med samma regel för svarat och utan listans tak
  på 500 (talet kan därför bli högre än förut, och är då det riktiga).
- **Radrörelsen läser stil bara för rader som animeras**, och sorteringen
  jämför tidsstämplar som text i stället för med `localeCompare`.

Efter (samma syntetiska mängd): klicket 170 ms, tangenttrycket 82 ms, sidan
3 254 DOM-noder i stället för 99 901.

**Kvar, inte gjort.** Körningarna går i samma process som API:t (leads- och
chattarbetarna i `app/main.py`). En körning som gör tungt arbete i
händelseloopen kan därför fortfarande göra varje sida trög medan den pågår.
Det gick inte att mäta i dag: Railway-tokenen är död, så loopvaktens loggar
("står still") går inte att läsa. Med en ny token: läs loopvakten under en
körning, och flytta arbetarna till en egen tjänst om den visar stopp.

---

## 2026-11-16 (Anton) — Synken körs även när development ligger före main

**Beslut.** På frågan om synken ska få köra när development ligger före main
i schemat svarade Anton "Ja, bygg det". Det avgör den öppna punkten i
beslutet nedan: migrationer går fortfarande till main först vid releasen, och
det är synken som tål skillnaden.

**Resonemanget.** Alternativet var att skicka additiva migrationer till main
direkt efter development. Det hade ändrat produktionens schema utan en
release och utan Antons ord. Att låta synken tåla skillnaden rör bara
development, som är spegeln.

**Agentens val i bygget.**

- **Det räckte inte att släppa på versionsspärren.** Synken jämför rader med
  en kontrollsumma över alla kolumner och skriver om hela raden. Med en egen
  kolumn i development hade varje rad sett ändrad ut vid varje synk, och
  kolumnens värden hade nollats. Raderna jämförs därför på de gemensamma
  kolumnerna, en rad som skrivs över behåller developments egna värden, och
  en ny rad får kolumnernas standardvärden.
- **Spärren jämför den högsta versionen, inte mängden.** Developments liggare
  bär tre äldre poster under namn som sedan bytts (056, 066, 092). En
  mängdjämförelse hade sagt "tre migrationer före" för alltid och kunnat
  stoppa synken åt andra hållet.
- **Det som inte går att spegla stoppar som förut:** main före development,
  en kolumn som bara finns i main, och en gemensam kolumn med olika typ.
  Första synken, som skriver till main, kräver fortfarande samma schema.
- **Samma schema ger exakt den gamla skrivningen.** Den nya vägen går bara
  när development faktiskt har egna kolumner.

**I koden.** `scripts/railway_synk.py` (`schemalage`, `tabellkolumner`,
`jamfor_kolumner`, `rader(utan=…)`, `skriv(egna=…)`),
`tests/test_railway_synk.py`. Provat mot de riktiga databaserna med en
provkolumn i development i en transaktion som rullades tillbaka.

---

## 2026-11-16 (Anton) — Migrationerna körs av sig själva

**Beslut.** Anton, efter att demolänken gått live i development: "Ja, kör
migrationerna. Finns det något sätt att automatisera även det?" Migration 115
och 116 kördes mot main samma kväll, och migrationerna körs sedan av ett
arbetsflöde i stället för för hand.

**Resonemanget (agentens val inom frågan).**

- **Det glömda handgreppet hade redan kostat.** Migration 115 kördes i
  development 2026-11-10 men inte i main, och synken mellan miljöerna
  (`synk.yml`) stod röd i sex dagar, för den vägrar när schemaversionerna
  skiljer sig. Ingen såg det.
- **GitHub Actions och inte ett steg i Railways deploy.** Repot har redan
  hemligheten (`ENV_DEPLOY`, samma som synken), och skriptet är detsamma som
  körs för hand. Ett steg i Railways deploy hade krävt att migrationerna och
  ett superuser-lösenord låg i api-tjänstens avbild.
- **Development: vid pushen.** Railways bygge tar flera minuter och jobbet
  under en, så schemat ligger före koden. Det är en ordning och ingen grind,
  eftersom Railway inte väntar på GitHub Actions.
- **Main: vid mergen av release-PR:en, inte tidigare.** Mergen är Antons
  handgrepp (grenskyddet), så hans ord gäller fortfarande för varje ändring
  av produktionens schema. PR:en får en kontroll som visar vad releasen bär
  och fäller den om development har okörda migrationer: development är en
  spegel av produktionen, så en migration som gått där är provad.
- **Migrationer ska vara additiva och idempotenta**, så att schemat får ligga
  före koden. Det var redan praxis; nu är det ett krav.

**I koden.** `.github/workflows/migrera.yml`, `DEPLOY.md` ("Migrationer körs
mot Railway") och `CLAUDE.md`. Main-delen börjar gälla först när
arbetsflödet självt nått main med nästa release.

**Öppet.** Synken stannar fortfarande så länge en migration bara finns i
development. Anton avgör om additiva migrationer ska gå till main direkt
efter att de gått i development (synken hålls då vid liv, men produktionens
schema ändras utan en release), eller som nu först vid mergen.
*Avgjort samma dag: synken tål att development ligger före, se beslutet ovan.*

---

## 2026-11-15 (Anton) — Demolänk i varje utkast, spårning av besök, och A/B-mätning av Ja, Nej, Kanske och klick

**Beslut.** Anton: "Updatera alla mailutskick i utkorgen samt alla olika
erbjudanden oavsett A eller B så att de innehåller en länk till demon, med en
fras som till exempel: länk till vår demo, där ni kan se hur det
fungerar/testa mot ert företag, ett snäpp ned från resten av texten. Jag vill
även att du kollar upp och gör så att vi kan se vilka som faktiskt besökt
länken, hitta på ett bra system för detta, eller en befintlig lösning som vi
kan implementera. Se även till att lösa mätning för A/B på totala svar, andel
Ja, Nej, Kanske/Återkom och andel som klickat på länken i de olika utkasten."

**Resonemanget (agentens val inom beställningen).**

- **Raden skrivs av kod, inte av modellen.** Samma skäl som signaturen och
  foten: en URL i modellens text fälls av faktagrinden, och en rad som bara
  brukar komma med gör mätningen tyst fel. Raden står i ett eget stycke efter
  mejlets sista mening och före hälsningsfrasen.
- **Eget spårningssystem i stället för en färdig tjänst.** Mejlen går ut över
  SMTP med ren text i grunden, så en mejltjänsts klickspårning
  (Resend, Postmark, Mailgun) går inte att slå på, och den hade skrivit om
  länken till en tredjepartsdomän, vilket är en spamsignal i kalla mejl.
  Länken är `{sajten}/prova/<token>`, en token per tråd, på samma domän som
  avsändarens webbplats och med samma mönster som avregistreringslänken (046).
- **Klick och besök är två saker.** E-postskydd (Safe Links, Proofpoint,
  Mimecast) klickar på länkar i inkommande mejl innan mottagaren ser dem. Ett
  klick loggas vid vidarebefordringen och märks som skanner när user agent
  eller tiden (inom två minuter från utskicket) tyder på det. Ett besök loggas
  först när mottagaren scrollar eller klickar på demosidan. "Besökt" betyder
  alltså en människa, och det är det listan "Vilka har besökt demon" visar.
- **Kanske/Återkom är en egen svarsklass (`aterkom`).** Förut föll "inte nu,
  hör av er i vår" under fråga eller negativt. Köade uppföljningar ställs in
  och kunden aviseras: när man återkommer är en människas beslut.
- **Svarsklassen sparas på tråden.** Förut härleddes svar och positiva ur
  statusloggen. Äldre svar räknas fortfarande därifrån (möte = Ja, förlorad
  och avregistrerad = Nej, svarat = fråga), så mätningen börjar inte om.
- **A/B mäts i två dimensioner:** per erbjudande (som förut) och per
  utkaststruktur A/B, som nu sparas på tråden. Trådar från före strukturvalet
  2026-11-05 räknas inte i strukturjämförelsen, eftersom de bara kan vara A
  och hade gett A ett försprång i tid.
- **Inget i svar till den som redan svarat.** Ett svar i ett levande samtal
  bär ingen demolänk.

**I koden.** `app/leads/demolank.py` (raden, kundens val, bytet av en naken
demoadress mot "länken nedan"), `leads_tools._queue_outreach_draft_impl` och
`scheduler._fot_vid_godkannande` (raden läggs på vid köningen och vid
godkännandet), `svar.py` (klassen `aterkom`, `satt_svarsklass`),
`erbjudanden.sammanstall` och `storage.erbjudande_utfall`/`struktur_utfall`
(Ja, Nej, Kanske, frågor, klick och besök per arm), migration 116
(`outreach_threads.svarsklass`/`struktur`, `ss_demolankar`,
`ss_demolank_handelser`, `demolank_klick`, `demolank_besok`),
`app/prova/[token]/route.ts` och `components/demo/DemoBesok.tsx` (Next),
`GET /api/leads/demobesok` och fliken Leads › Erbjudanden (demolänken,
mätningen och besökslistan), `scripts/demolank_i_utkorgen.py` (raden på
utkasten som redan ligger i kön). Kundens demolänk står i
`settings.erbjudanden.demo`; utan den ändras ingenting.

**Öppet.** Synlighet: mätningen och besökslistan visas för kunden själv, om
kundens egna trådar. Dataskydd: klicket knyts till en namngiven mottagare, så
integritetspolicyn och utskicksfotens ändamålsrad bör nämna att länkar i
utskicken mäts (se `docs/JURIDIK_ATGARDER.md`). Anton avgör.

---

## 2026-11-10 (Sebbe) — Stabilitetsarbetet, fas 2 till 4: mät först, och låt mätningen välja ändringen

**Beslut.** Sebbe: "kör klart alla faser och allting du ska göra, du får
godkännelse för allt. När du är klar med ALLT så pushar du." Godkännandet
gällde också det som annars kräver ett ja först (migration, jobb med förlopp).
De enskilda valen nedan gjordes i arbetet. Slutrapporten ligger i
`docs/stabilitet-2026-11/SLUTRAPPORT.md`.

**Resonemanget.** Fas 0 gav en lista. Fas 2 till 4 byggde mätinstrument
(evalsviter mot riktig modell, ett lasttest, frågor mot databasen) och lät dem
peka ut vad som skulle ändras. Tre av de allvarligaste fynden stod inte på
listan: jobbsvaret lämnade ut agentens promptar till varje besökare, två av
fyrtio kvitton gav serverfel, och supporten lydde en inbäddad instruktion och
lovade rabatt.

**I koden, val för val.**

- **Agentsvar till kunden bär inte stegloggens texter** (`api/stegtexter.py`).
  Rensningen sker där svaret lämnas ut, inte där det sparas: kvotbokföringen
  läser det lagrade, och redan lagrade jobb täcks. `/api/leads/runs` ger ett
  sammandrag; ingen vy läste texterna.
- **`utkast_lagen` läser tabellerna en gång** när hela kunden efterfrågas, och
  har kvar uppslaget per tråd för ett enda prospekt. Den nya frågan jämfördes
  rad för rad mot development innan den infördes. Migration 115 lägger index;
  frågan är snabb även utan dem, så en miljö som inte kört migrationen går.
- **Supportens steg påminns om kontraktets två fält** sist i meddelandet.
  Triagen gjordes om i 74 % av anropen för att svaret saknade dem. Valet att
  inte släppa kravet i stället: fälten är spårbarheten, och en rad kostar
  mindre än ett omförsök. Bara supporten får raden; Iris kedja är låst mot
  facit och rörs inte utan egna prov.
- **Avhoppsklassaren går samtidigt med triagen.** Dess utslag läses först
  efter researchen.
- **20 sekunder per modellanrop i chatten** (45 förut), dubbelt för steg som
  tänker. Följden att räkna med: en trög stund hos Vertex ger fler omförsök.
- **Chatten visar fyra skeden**, inte stegens namn: namnen är interna.
- **Kvittoskanningen och massutskicken är jobb med förlopp**
  (`jobs/bakgrund.py`), som en uppgift i api-processen med en post i det
  befintliga jobblagret. Ingen ny kö. Valet har ett pris: en deploy mitt i
  avbryter arbetet, och det som hunnit göras är gjort. Båda går att starta om
  utan att något händer två gånger, och det var villkoret för valet.
- **Kundens text står inom en ram** med förklaringen FÖRE taggarna. Första
  versionen hade förklaringen inuti, och evalsviten visade följden samma dag:
  modellen läste den som kundens text och svarade med en hälsning på två av
  femtio frågor. Ett svar som bär våra instruktionsmarkörer stoppas i kod.
- **Ett beroende som är nere ger 503**, ett programfel 500.
- **Ett modellsvar utan tokenräkning fäller inte agenten.** Klienten fyller i
  fälten; kvittohanteraren läser underlaget maskinellt till granskning.
- **Evalsviterna bedöms mekaniskt**, utan en andra modell som domare: samma
  svar ska ge samma poäng. Det mallen inte kan mäta (tonen, om en ingång
  håller nivån) står kvar hos en människa. Iris signal mäts som en upplysning:
  nivån för en ingång är bolagets löfte mot momentet, inte en nyhet.
- **Sviterna körs mot egna evalkunder i development**, aldrig mot en riktig
  kunds konto och aldrig mot produktionen.

**Inte gjort, med flit.** Iris promptar och grindar (låsta mot facit, ändras
enligt referensens avsnitt 8), strömmat supportsvar, reservmodell på Vertex,
Sentry (kräver ett konto), kundnycklarna i klartext i development.

---

## 2026-11-10 (Sebbe) — Stabilitetsarbetet, fas 1 fortsatt: ett fel gäller sin egen rad, inte hela arbetet

**Beslut.** Sebbe sa ja till de återstående punkterna i fas 1 efter att den
första delen gått in i `development`. De enskilda valen nedan gjordes i arbetet.

**Resonemanget.** Det gemensamma i punkterna är att ett enda fel fick för stor
följd: ett avvisat mejl fällde hela massutskicket och försöktes sedan om i
evighet, ett trasigt kvittomejl stoppade alla mejl efter det, ett avbrott på en
sekund i Redis fällde en körning vars research redan var betald, och ett
modellsvar i fel form gav ett serverfel. Felet ska stanna vid sin rad, synas
där, och resten ska gå vidare.

**I koden, val för val.**

- **Ett utskick som mejltjänsten inte tar emot bokförs på köposten.** 400/422
  och ogiltig adress stoppas direkt med skälet (samma mejl ger samma svar nästa
  minut). Övriga fel försöks om med växande paus, 1 till 30 minuter, och
  stoppas efter 20 försök, omkring en arbetsdag i sändfönstret. Valet att inte
  stoppa på första tillfälliga felet: ett avbrott hos Resend en förmiddag ska
  inte kräva att en människa godkänner om varje utkast. Ett stoppat utkast
  prövas igen från noll med Godkänn och skicka (`leads/scheduler.py`).
- **Kvittoskanningen läser vidare.** Ett mejl som faller får utfallet "gick
  inte att läsa" och prövas igen vid nästa skanning; kontofel och slut kvot
  avbryter fortfarande hela skanningen, för de går inte över av nästa mejl. Två
  samtidiga skanningar blir en. Att skanningen fortfarande körs inne i en
  begäran, utan förlopp som finns kvar efter omladdning, är inte löst här: det
  är förslaget om skanningen som jobb, som väntar på Sebbes ja.
- **Körningens rapport gör tre försök** innan körningen fälls.
- **Modellsvar normaliseras där de läses.** Stegköraren ger alltid ett objekt.
  Supportens triage: sentimentet 0,0 betyder så argt det går och läses inte
  längre som neutralt, `"false"` inom citattecken lämnar inte över ärendet.
  Följden att räkna med: ett sentiment på exakt 0 lämnar nu över, vilket är
  vad regeln alltid sa.
- **Supportportalen ger aldrig den delade nyckeln till en kundsession som inte
  håller,** och inte till någon alls när sajten är driftsatt utan
  inloggningsvägg. Hellre utloggad än i fel kunds data.
- **Flyttpaketet bär sin tid** och main tar bara emot paket yngre än en kvart.
  Det begränsar återuppspelning. Det löser inte att nyckeln delas mellan
  development och main: den som har nyckeln kan fortfarande skriva till
  produktionen, och det är så flytten är tänkt. Kundnycklarna i klartext i
  development kräver en migration och är ett eget beslut.
- **Leadshämtarna når bara det publika nätet** (`leads/hamtvakt.py`). Samma
  regler som integrationernas nätvakt, men http tillåts: en liten firmas sajt
  saknar ibland https och ska gå att läsa ändå.
- **Leadsbudgeten förvarnar vid 80 %** i plattformshändelserna. Supportens
  dagsbudget är fortfarande avstängd som standard och kvittohanteraren har
  inget tak; att sätta dem är ett beslut om vad en kund får kosta, inte en
  kodfråga.
- **Demons IP-tak läser det sista värdet i `X-Forwarded-For`,** det kantproxyn
  lade dit. Hur Railways kant skriver huvudet är inte provat; läser den över
  besökarens värde är första och sista samma, och ändringen är ofarlig.

---

## 2026-11-09 (Sebbe) — Stabilitetsarbetet, fas 1: felen ska höras, och samma sak ska inte hända två gånger

**Beslut.** Sebbe beställde en genomgång i fyra faser ("Snajp kraschar inte,
svarar snabbt, agenterna är vassa") och sa ja till fas 1 efter kartläggningen
(`docs/fas0-2026-11-09/RAPPORT.md`). Sebbe beslutade ordningen; de enskilda
valen nedan gjordes i arbetet och ligger på grenen `stabilitet` för hans och
Antons granskning innan något går till `development`.

**Resonemanget.** Kartläggningen visade att de allvarligaste felen var tysta:
api:t gick upp i minnesläge med grön hälsokontroll när databasen inte svarade,
ett hängt modellanrop väntade i tio minuter, och supportagenten lämnade över
"Hur anmäler jag mig till en HLR-kurs?" som ett känsligt ärende. Inget av det
syntes förrän en kund mötte det.

**I koden, val för val.**

- **Uppstarten vägrar minnesläge.** En satt `DATABASE_URL` som inte går att nå
  efter fem försök fäller deployen (`main.py:_anslut_postgres`), så att
  Railway behåller föregående version. Utan `DATABASE_URL` är minnesläget kvar.
  Ersätter "degraderar gracefully till in-memory" för databasen; Redis och
  LLM-nyckeln degraderar som förut.
- **Tidsgränser.** LLM-anrop 120 s (`LLM_TIMEOUT_S`), chattens steg 45 s med
  ett omtag (`LLM_TIMEOUT_CHATT_S`), databasen 10 s att ansluta och 60 s per
  fråga, Redis 5 s att ansluta och 20 s per svar. Talen är valda ur
  mätningen i fas 0 (chattens steg låg under 20 s i p95) och går att ställa
  om med miljövariabler.
- **Ordfiltret för känsliga ärenden** fäller hotet om en anmälan och kravet på
  ersättning, inte orden `anmäl*` och `ersättning`. "Pengarna tillbaka" läggs
  till. Hotfiltret kräver ett offer för "slå" och "hitta".
- **Den anonyma chatten tar bara sessionsidentiteter**
  (`<uuid>@session.snajp.se`). En kund som vill skicka riktiga adresser gör
  det med sin egen nyckel mot api:t.
- **Samma start två gånger är en start.** En likadan beställning från samma
  kund inom 30 sekunder får samma svar (`api/dubbelstart.py`). Per process;
  fler repliker kräver Redis.
- **Utskick bär en idempotensnyckel** till Resend, byggd på meddelandets id
  och innehållets hash.
- **Varje anrop har ett id** (`X-Request-Id`, `app/sparning.py`) i svaret, i
  loggen och i `platform_events`.

Lösenordet till plattformsadminkontot togs ur skript och handoffs samma dag.
Det ligger kvar i historiken och ska bytas.

## 2026-11-09 (Anton) — Startsidan: hjälten ryms i en skärm, innehållet följer skrollen, kapitelrubrik per agent

**Beslut.** Hjältens text står med tyngdpunkten strax över skärmens mitt och hela
hjälten ryms i första skärmen; på mobil står första ytan i första skärmen. Flödet
under hjälten har ingen kö i tid: varje sak kommer i samma ögonblick som den står
i bild, och löptext reser sig rad för rad ur sin rad (den tonas inte och skrivs
inte ut som rubriken). Varje agent inleds av en kapitelrubrik: namnet i displaygrad
på bläck med ljuset från ett fönster över golvet. Fälten i de konstruerade ytorna
svarar på pekaren, och ett klick på en yta öppnar demon.

**Resonemang.** Antons ord: "Just nu är sidan laggig och dåligt anpassad,
innehållet halkar efter och dyker upp för sent och texten hamnar för långt ned i
heron och känns som att den ska ramla igenom skärmen, som är exakt det vi ska
undvika enligt reglerna i designsystemet, på mobil är det ännu värre där rutorna
hamnar långt ned på skärmen. Se till att allt blir bra timat och mjukt och att
texten dyker upp, inte ser ut som att den renderas, det är en viktig skillnad,
utan att skrivas ut på samma sätt som i rubriken. Lägg även till en tydlig
rubrik-sektion för de båda agenterna med en effektfull animation och passande
bakgrund som markerar det avsnittet, så att det inte övergångarna sker med knappt
märkbara rubriker som nu." Under arbetet: "Ser bra ut: Viktigt, gör alla fält i
rutorna interaktiva vid hovring, precis som email-studio och supportinkorgen".
Orsakerna var mätbara. Hjälten var högre än skärmen och texten låg mot dess
nederkant (på Antons skärm, 1536 × 745 i CSS-pixlar, stod rubriken 470–890 px
ned). Flödets kö (0,6 s per sak, från beställningen 2026-11-07 "en sak i taget")
lät sex saker i följd bli 3,6 s sena, och rutor som väntade dolda tills hela
höjden stod i bild lämnade tomma skärmar. "En sak i taget" kommer nu av skrollen
själv: det som står på olika höjd når bilden vid olika tillfällen.

**I koden.** `Startsida.tsx` (hjältens rutnät, `Kapitel`-delen i `AgentFlode`,
texten som `data-mo="lines" data-full`), `useLandingMotion.ts` (`steg` utan kö,
`slot`, `kapitel`, rutor med `data-full` startar vid `top 68%` och döljs aldrig,
hjältens ytor från 0,7 s, ingressen radvis, sidhuvudet från första målningen),
`globals.css` (`.hem-scrim`, `.kapitel-ljus`), `ProduktBilder.tsx` och
`AgentResultat.tsx` (fältens hovring, länken till demon). Uppmätt: text på
hjältefotot minst 10:1 på mobil, kapitelnamnet mot ljuset minst 5,9:1; efter full
skroll 0 dolda element på 1536 och 375 px. Inte mätt: bildfrekvensen i en
webbläsare med grafikkort (den huvudlösa mätningen mättar på 100 ms för både
gammal och ny sida och säger därför ingenting).

## 2026-11-09 (Anton) — Demon: ingen orange "Demokonto"-ruta, ingen statisk körning, allt klickbart gör något

**Beslut.** Den orangea rutan "Demokonto · inloggad" är förbjuden och borta ur
railen, mobilraden och railfoten; railen visar arbetsytans namn som för en kund.
Bandet överst står kvar. Översiktens statiska "Pågår just nu" är borta. Demons
leads är de sex exempelbolagen, vart och ett med bedömning, källor, utkast och
tidslinje. Ärenderaderna och luckorna i kundtjänstens översikt går att öppna.

**Resonemang.** Antons ord: "Fixa även demosidan, många av sidorna/knapparna går
inte att trycka på, till exempel ärenden från listorna i översikterna och flera
bolag i leads visar fel eller inget utkast, samt en statisk text som säger att
körning pågår, vilket inte behövs och ser väldigt fake ut, se helt enkelt till
att allt håller en högre nivå, SKIPPA den orangea "demokonto" -rutan, de är
FÖRBJUDNA." Det ersätter Sebbes markör från 2026-10-29 (demon som inloggat
demokonto): kontot finns kvar, etiketten inte. Listans bolag kom ur
`lib/mock-data`, som saknade utkast och källor och vars signaler sålde Snajp i
stället för demons avsändare; därför "Inget utkast ännu" och "Bolaget hittades
inte".

**I koden.** `AppShell.tsx`, `lib/demo/aktivitet.ts`, `lib/demo/oversikt.ts`
(`demoLeadrad`, `demoTidslinje`), `lib/demo/support-oversikt.ts`,
`SupportOversikt.tsx` (`onOppnaArende`, Granska), `Dashboard.tsx` (`oppnaId`),
`LeadsTabell.tsx`, `Tidslinje.tsx`, `IrisBolag.tsx`, `LeadsSida.tsx` (en okänd
`?lead=` i demon tas ur adressen i stället för att visa fel). Följder som Anton
bör känna till: "Kör Iris" i demon börjar nu på varianterna av exempelbolagen,
eftersom de sex handskrivna redan står i listan (varianterna är samma brev med
andra namn och kan läsas som mall sida vid sida); körningsdetaljens länk heter
"Öppna bolaget" också i arbetsytan. Inte rättat: bolagslänkarna på
`/demo/companies` och `/demo/contacts` (rutter utan menyval) leder ut ur demon
till inloggningen.

## 2026-11-08 (Sebbe) — En beställd körning levererar beställt antal; budgeten är bara en dörr

**Beslut.** "Det är en riktigt hård regel att alla leads som söks ska hittas.
Om man söker körning för 200 leads ska 200 leads hittas." Och: fortsätt
körningen som stannade.

**Resonemanget.** Två körningar på 200 i main stannade 18:43 på 33 och 68
med slutorsak "budget". Målgruppen var inte slut (0 tomma rundor, 37 av 2 400
undersökta); dygnsbudgeten för leads-tokens kontrollerades före varje bolag
inne i motorn och avslutade beställningen. `app/leads/budget.py` säger själv
att grinden är "en dörr, inte en vakt inne i rummet": den skyddar mot en
skenande kostnad (INV-JOB-002), inte mot vanligt arbete (Antons beslut
2026-10-20 nedan). En körnings kostnad är redan begränsad av taket (12
undersökta per beställt lead) och kredittaket för sidhämtningar.

**I koden.** Budgetkollen i `_fyll_pa_last` är borta; dörren vid starten
(`_kraev_leads_budget`, 429) står kvar. Nytt: `POST
/api/leads/korningar/{id}/fortsatt` öppnar en avslutad körning under målet
(inte avbruten) igen med allt den redan prövat, och knappen "Fortsätt
körningen" i körningens detalj (`IrisKorningar.tsx`). Ingen budgetdörr vid
fortsättningen: beställningen är redan tagen. Anton ska informeras: att
budgeten tog slut efter fyra körningar på 200 tyder på att förbrukningen per
körning är långt över de ~3 M tokens som låg till grund för taket 2026-10-20,
eller att `LEADS_DAILY_TOKEN_BUDGET` inte längre är satt i main.

## 2026-11-08 (Anton) — Startsidan följer inte med release #42

**Beslut.** Den enade startsidan (posten "Startsidan blir en egen sida",
2026-11-07) går inte till main med release-PR:en #42. Den är borttagen från
`development` tills PR:en är mergad, så att PR:en bara bär resten: Sebbes demo
och reel, struktur A och SEO-arbetet med jämförelsesidorna och länktexterna.

**Resonemang.** Antons ord: "Se till att ändringarna på hemsidan inte kommer
med i PR:en, SEOn arbetet och då tillhörande länkarna, inte den enade
startsidan från den här sessionen." Jämförelsesidorna hade han godkänt för
releasen dagen innan. PR:en går från `development`, så det som ska stå utanför
måste lämna grenen tills mergen är gjord; en flagga hade tagit koden till main
ändå. Pilotpriserna följer med releasen till produktionen; på frågan om de
också skulle hållas utanför svarade Anton: "Yes, let them go to production".

**I koden.** Commiten `revert(startsida): startsidan hålls utanför release #42`
återställer startsidans filer till läget före bygget (`app/page.tsx`,
`LandingPhoto.tsx`, `ProductPage.tsx`, `useLandingMotion.ts`,
`AgentResultat.tsx`, `ProduktBilder.tsx`, `UspSection.tsx`, `copy-sections.ts`,
`app/globals.css`) och tar bort `Startsida.tsx` och testet
`test_startsidan_ar_en_egen_sida`. `/` skrivs alltså om till `/leads` igen,
också i development. **Efter mergen av #42:** `git revert` av den commiten på
`development` tar tillbaka startsidan precis som den var.

**Återställd 2026-11-08.** #42 mergades 2026-11-07 23:51 UTC. Commiten
`feat(startsida): startsidan tillbaka på development efter release #42` tar
tillbaka startsidans filer; den här beslutsposten står kvar. Startsidan går
till main med nästa release.

## 2026-11-07 (Anton) — Produkten väljs efter vad som tar mest tid hos bolaget

**Beslut.** Hos Snajp får fastighetsbolag och förvaltare Supportagenten
(hyresgästernas frågor och ärenden) och byggföretag och hantverkare Iris (nya
uppdrag). Övriga bolag får den produkt som täcker det som rimligtvis tar mest
tid hos dem. Researchen avgör det själv: den skriver först vad som tar mest tid
i bolagets vardag (`tar_mest_tid`) och väljer sedan den produkt vars nytta bäst
täcker det.

**Resonemang.** Antons ord, efter att ett fastighetsbolag fått Iris och ett
mejl om "nya hyresgäster": "Ja, satsa på support för fastighetsbolag och leads
för bygg, se till att agenten bättre kan avgöra detta själv utifrån vad som
rimligtvis tar mest tid av företaget och vilken produkt som bäst täcker detta."
Produktvalet var en rad, "den som passar bolaget bäst", utan något skäl att
väga, och det gav Iris till ett bolag vars tid går åt till hyresgästerna.

**I koden.**
- `leads_research_v2._TIDSVAL` i båda produktvalen (`_PRODUKTVAL`,
  `_PRODUKTVAL_BEHOV`): väg vad som tar mest tid, välj produkten som bäst
  täcker det, kundens egna instruktioner om produktvalet går före. Gäller alla
  kunder med en produktlista.
- Nytt fält `tar_mest_tid` i researchen, före `produkt` (uppgiften och
  overlayen `leads-research-v2.md`). Det sparas i utkastets underlag
  (`sparad_research.UNDERLAGSFALT`) och når utkastet som
  `tar_mest_tid_hos_dem`, det ingången och produktmeningen tar vid ifrån.
- Snajps regel om fastighet och bygg i Iris-instruktionen
  (`scripts/snajp_malgrupp.py`), som researchen också läser.
- Låst av `tests/leads/test_produktval_tid.py`.

---

## 2026-11-07 (Anton) — A:s ingång är deras vardag, aldrig bolagets verksamhetsbeskrivning

**Beslut.** Ingången i struktur A säger det konkreta i mottagarens vardag som
produkten tar vid ifrån och som går att anta ur deras verksamhet, skrivet till
dem, som i förslag 1:s exempel ("Ni lägger de flesta golven åt fastighetsbolag
och bostadsrättsföreningar runt Göteborg. Vår agent Iris tar fram fler sådana
kunder …"): för Iris vilka kunder de säljer till, för Supportagenten vad deras
kunder hör av sig om. Bolagets namn som subjekt, "[Bolaget] erbjuder …", är
ingen ingång och fälls i kod. Ersätter "ett konstaterande om något konkret ur
deras verksamhet" i beslutet 2026-11-06 nedan; resten av det står kvar.

**Resonemang.** Antons ord om provets nio utkast: "De här inledningarna som i
princip är en repetition av företagets verksamhetsbeskrivning är exakt vad vi
ville undvika för länge sedan och blir väldigt opersonligt och mall-aktigt,
istället för att koppla direkt mot något konkret som de antagligen brottas med
i sin verksamhet, som att hitta nya företagskunder eller hantera ärenden från
hyresgäster … Det känns som att vi sorterade bort på för mycket, får inte kräva
något eller vara smickrande och landar i att det blir väldigt generellt och
opersonligt, hela strukturen tappades dessutom från det första exemplet för
Förslag 1 … som var bra som det var." Sex av nio ingångar började med bolagets
namn och sajtens beskrivning. Orsaken låg i reglerna: två av fyra
ingångsformer bad om "vad deras kunder får av dem" eller "något nytt hos dem",
personaliseringssteget förbjöd allt som liknade något de brottas med, och
stilgrindens omskrivningstips pekade fortfarande på "deras löfte".

**I koden och prompterna.**
- `erbjudanden._INGANG_A` och `leads_research_v2._INGANGSUPPGIFT`: ingången
  med "ni" eller deras kunder som subjekt, vilka kunder de säljer till (Iris)
  eller vad kunderna hör av sig om (Supportagenten), aldrig bolagets namn.
- `_INGANGSFORMER` per produktslag (`_ingangsform(prospect_id, slag)`): tre
  former för Iris, tre för Supportagenten, inga om "vad kunderna får av dem".
- `stilkontroll.kontrollera(bolag=…)` och `bolag_i_ingangen`: bolagets
  namnord bland ingångens tre första ord fälls i A (`bolagsbeskrivning`) och
  skrivs om i kedjan; köningen och `scripts/granska_utkast.py` skickar med
  namnet. Utan namn (facit, uppföljningar) prövas det inte.
- `kravande_ingang` i A fäller bara krav riktade till dem ("kräver att ni",
  "ni behöver", "måste ni"): vad deras kunder behöver får ingången säga. B
  behåller sitt bredare förbud.
- Skrivstilen (omgång 12, ingångsavsnittet med förslagets två exempel utan
  citattecken, så att en verklig golvfirma inte fälls som kopia), grundmallen
  § 10.2, Snajps Iris-instruktion och stilgrindens omskrivningstips.
- Låst av `tests/leads/test_struktur_a_kort.py`.

**Provet samma kväll** (samma nio leads, två varv, `860941c` och `648d0ae`):
ingen ingång började med bolagets namn i något varv, mot sex av nio före, och
de flesta följde förslagets form ("Era kunder vill sälja maskiner, fordon och
inventarier. Vår agent Iris hittar fler sådana företag åt er …"). Första
varvet skrev av utfallet ("40–50 nya företagskunder åt er varje vecka") i tre
av sex Iris-mejl och sa bara bolagets kategori i supportingångarna; båda
fälls nu (`_GENERISK_IRIS`, supportformerna), liksom "fler sådana
hyresgäster" (`fel_sak`). Kvar: en ingång som fortfarande beskriver bolaget
med "Ni" som subjekt (en säljbyrå), ett fastighetsbolag där researchen valt
Iris och mejlet därför lovar hyresgäster, och tunn research som ger
"företagskunder" utan bransch.

---

## 2026-11-07 (Anton) — Pilotpriser: 9 990, 12 990 och 19 990 kr i månaden

**Beslut.** Snajp Support kostar 9 990 kr i månaden, Snajp Leads 12 990 och
Snajp Duo 19 990, alla exklusive moms (var 3 990, 4 490 och 6 990). Priserna
är tillfälliga under pilotperioden och kan komma att höjas, och det står på
sidan.

**Resonemang.** Antons ord: "Ändra även priserna till 9990 ex moms för Support
och 12990 för Leads 19990 för Duo, skriv även att detta är tillfälliga priser
under pilotperioden och kan komma att höjas." Han angav inget annat skäl.

**I koden.** `lib/pricing.ts` (beloppen, och `PRISER_AR_PRELIMINARA` tillbaka
till true så att förbehållet renderas), förbehållets lydelse i
`PricingSection.tsx` (nu också "exklusive moms") och Snajps egen kunskapsbas
`snajp-support/app/tenants/snajp_kb.py`, som chatten svarar ur och som fylls på
vid nästa seedning. Titlar, sökbeskrivningar, schemat, llms.txt och
sökordssidorna räknar priset ur `lib/pricing.ts` och följer med av sig själva.
Duo sparar nu 2 990 kr i månaden (räknas fram). Inte ändrat: avtalsmallen
`docs/pilotavtal.md` och planerna i `GOALS.md`, som är Antons dokument.

## 2026-11-07 (Anton) — Startsidan blir en egen sida

**Beslut.** `/` är inte längre samma sida som `/leads`. Den har en egen hjälte
(koncept 2a: rubriken "AI-agenter för leads och kundtjänst, på svenska." på
Göteborgsfotot, med Iris utkast och supportagentens ärende svävande över
himlen) och en sektion per agent, och den skrivs inte längre om till `/leads`
i adressfältet. `/leads` och `/support` är oförändrade.

**Resonemang.** Båda adresserna renderade samma kropp och samma H1, och `/`
byttes till `/leads` med `replaceState`; Google slår ihop sådana adresser och
rankar bara en av dem. Anton valde variant 1a med rutorna från 1c, "som flyter
in över bakgrunden och svävar stilla och reagerar dynamiskt på hovring", med en
"Läs mer" under varje ruta till agentens sektion, och "samma sida för det mer
generella om vår filosofi och arbetssätt". Sedan: "bygg inte om resten av
sidan från grunden, använd endast de befintliga 3 första sektionerna för varje
agent ... fram tills Haga-bilden". Löftet ska ha resultatvyns tal och panel
nedanför sig, "ett dynamiskt scroll-drivet flöde som mjukt visar sig eftersom
användaren scrollar ned, en sak i taget, med allt i bild och inget som är
ryckigt eller börjar innan det är fullt synligt eller försvinner innan
animationen är klar", och demon ska stå med texten bredvid, "inte ta upp hela
bredden".

**I koden.** `components/marketing/Startsida.tsx` (hjälten, agentsektionerna,
gränserna för båda), läget `hem` i `LandingPhoto.tsx` och `ProductPage.tsx`,
rörelserna `svav` och `steg` i `useLandingMotion.ts`, frågorna för båda
agenterna (`hemFragor` i `copy-sections.ts`, också i startsidans FAQPage-schema).
Produktbilderna och "Så tänker vi"-bandet står inte på startsidan: ytorna bär
hjälten, och bandet var inte en av agenternas tre sektioner. INV-SEO-001
(`test_startsidan_ar_en_egen_sida`) fäller en återgång.

**Rättat samma dag (Anton).** Produktbilderna togs bort på agentens eget
initiativ, och då fylldes agentens sektion nästan bara av resultatvyn. Anton:
de två dynamiska rutorna hör till den första sektionen, och resultatet ska vara
"den sista delen innan den interaktiva rutan med Email-studio eller inkorg".
Ordningen per agent är nu: löftet, de två rutorna (`ProduktBilder`, läget
`fullt`), resultatets tal och panel, demon med texten bredvid. Bandet står
fortfarande inte med.

**Hålls utanför release #42 (Anton 2026-11-08).** Se posten "Startsidan följer
inte med release #42".

---

## 2026-11-06 (Sebbe) — Marknadsvideo för Instagram: Iris från körning till svar

**Beslut.** En kort reel (26 s, 9:16 och 4:5) som visar Iris-flödet som en
sammanhängande handling: Kör Iris, filter på stad och bransch, 50 leads
"pang", utkasten redan skrivna, ett klick, 30 svar i inkorgen. Sebbes
beställning: "DET SKA VARA EN HÄFTIG EFFEKTFULL VIDEO. MAN SKA KÄNNA ATT DET
GÅR FORT OCH ÄR ENKELT ATT FÅ NYA FÖRETAGSKUNDER I SIN INBOX FRÅN DET ATT MAN
SKAPAR KÖRNING." Tempo och grepp är hämtade ur en research av storbolagens
produktfilmer (Apple, Linear, Raycast, Stripe, Klarna med flera), se
`docs/marknad/video-research.md`.

**Resonemang.** Siffrorna 50 leads och 30 svar är en illustration av hur
flödet ser ut, inte ett utlovat utfall: raden "Illustration med påhittade
exempel" ligger i bild under kroken och svarssekvensen, och ingen text
påstår en svarsfrekvens (marknadsföringslagen). Allt innehåll är påhittat
och inget är inspelat från development eller main, eftersom båda bär
riktiga kunders data. Webbplatsbedömningen visas inte (Antons beslut
2026-10-08). Ljudet är syntetiserat från grunden så att ingen annans musik
följer med filen.

**I koden.** `marknad/video/` (Remotion, fristående; uteslutet i rotens
`tsconfig.json` och `.dockerignore` så att Railway aldrig bygger det),
`marknad/video/README.md` för hur man renderar.

---

## 2026-11-06 (agenten, på Antons uppdrag) — Jämförelsesidor med namngivna leverantörer

**Beslut.** Två nya sidor, `/jamfor-ai-sdr` och `/jamfor-supportagenter`,
jämför Snajp med namngivna leverantörer: språk, godkännande eller överlämning,
var datan lagras och pris. Jämförande reklam är ett beslut om varumärket, inte
bara om koden, så Anton skulle granska sidorna före main. **Godkänt av Anton
2026-11-07**: han läste sidorna i dev-miljön och sade ja till releasen
("Ja, öppna PR:en").

**Resonemang.** Anton: "Vi MÅSTE dyka upp på första sidan och i
AI-sammanfattningarna för samtliga, fortsätt tills det är löst." Google
AI-översikterna på "ai sdr sverige", "leadsagent sverige" och "supportbot
sverige" (Antons skärmdumpar samma dag) citerar topplistor och jämförelser
(getrebelos, revexa, businesswith, alicelabs), och Snajp står inte i någon.
En egen saklig jämförelse är den sidtyp de citerar. Den tidigare regeln i
`lib/landningssidor.ts` om att inte namnge konkurrenter var agentens egen
försiktighet, inte DESIGN.md:s (som förbjuder påhittade siffror och citat).

**Villkoren.** Varje uppgift står på leverantörens egen sajt (källa per rad,
`lib/jamforelser.ts`, underlaget i `docs/SEO-JAMFORELSER-KALLOR.md`), det
leverantören inte skriver är "Ej angivet", sidan säger att Snajp säljer ett av
verktygen, och INV-SEO-001 fäller en kontroll äldre än 120 dagar.

---

## 2026-11-06 (Anton) — Varje länk utåt heter som sökfrasen

**Beslut.** Sidornas titlar (länken i Google), sidfotens länkar, brödsmulorna
och llms.txt använder Antons fraser: "Svensk AI-SDR", "Svenska B2B-leads",
"B2B-prospektering för svenska företag", "Svenska leads i inkorgen", "Support
på svenska", "Svensk supportchatt till er hemsida", "Support som svarar på
svenska", och i samma stil "Svensk leadsagent", "Svensk AI-supportagent" och
"Svenska AI-agenter för företag". Titeln är frasen följd av "| Snajp".

**Resonemang.** Antons ord: "Se även till att all kommunikation utåt i alla
länkar är enligt det jag sa i början av konversationen … ALLA som söker på
detta i kombination med 'Sverige' eller 'svenska' ska få upp oss." En kort
titel som är exakt sökfrasen är också den Google helst använder som sidlänk.

**I koden.** Titlarna i `app/<sida>/page.tsx`, länknamnen i
`lib/landningar.ts` (`LANDNINGAR[].namn`, `FAMILJ[].lank`). Sidfoten länkar nu
även produktsidorna /leads och /support och har två kolumner från md, tre från
lg, så att de längre länknamnen ryms på en rad.

---

## 2026-11-06 (Anton) — Struktur A kortare: en mening per steg, högst 80 ord

**Beslut.** A får förslag 1 av tre: samma ordning som förut (mottagaren,
agenten, erbjudandet, inbjudan) men en mening per steg och högst 80 ord.
Ingången konstaterar en konkret sak om dem som produktmeningen tar vid ifrån,
produktmeningen bär kundens korta utfall översatt till dem, piloten står i en
eller två korta meningar och inbjudan i en. Ingen fråga i A, och erbjudandets
form B (frågan om vad som tar mest tid) är avslagen hos Snajp.

**Resonemang.** Antons ord: "Utifrån de senaste ändringarna känns just nu
alternativ B bättre då det är mer rakt på sak, där man inte riskerar att tappa
läsaren, men kan samtidigt läsas som oproffesionellt av vissa." Han bad om tre
sätt att göra A kortare och mer direkt utan att tappa den professionella
strukturen, valde det första och la till: "säkerställ att den fortfarande
anpassar utkasten efter varje kund och deras verksamhet, samt vilken produkt
som är den bästa fiten." Underlaget (Snajp i development 2026-11-01–06, 105
A-mejl): median 105 ord och 96 över formens 90 fast grinden skrev om långa mejl,
95 började "Att …", 57 sa "balansgång", 47 frågade vad som tar mest tid och
svarade själva i nästa mening, och alla slutade med två vägar i en lång mening.
Längden kom ur upplägget, inte ur orden, så ett lägre tak räckte inte. Taket är
80 och inte 70: förslagets exempel hade 76 ord, och ett tak som det godkända
exemplet inte klarar hade skickat nästan varje rätt mejl till omskrivning.

**I koden och prompterna.**
- `erbjudanden.FORMER` och `ORDTAK` (80 för form A, 90 för form B): formen
  beskriver ingången och produktmeningen, och blocket bär "Utfallet
  produktmeningen bygger på" ur kundens `kort_utfall` för produkten researchen
  valde (`Valt.utfall`, satt i `for_trad`); utan utfall bygger den på
  produktens nytta, så andra kunders produkter fungerar som förut.
- `leads_research_v2`: ingångsformerna konstaterar (vilka de arbetar för,
  något nytt hos dem, momentet, vad kunderna får), personaliseringssteget 1a
  skriver om ingången och produktmeningen ur citaten, och utfallet går in i
  faktagrindens underlag även i A. Omskrivningen och humanizern håller
  ordtaket.
- `stilkontroll.kontrollera(tak=…)`: kedjan, köningen
  (`_queue_outreach_draft_impl(ordtak=…)`) och `scripts/granska_utkast.py`
  prövar A mot formens tak; uppföljningarna behåller det allmänna taket 100.
  "Balansgång" fälls i ingången (`mallord_i_ingangen`). `agent_efter_loftet`
  jämför nu produktens första omnämnande med villkorens siffror: förut söktes
  namnet först efter första stycket, och ett A-mejl med Iris i produktmeningen
  och "pilot av Iris" efter "20" fälldes fel.
- Skrivstilen omgång 11, grundprompten § 10, katalogens gemensamma regel.
- `scripts/snajp_malgrupp.py`: bara `pilot_a` aktiv (`pilot_b` står kvar under
  `egna`), pilotvillkoret i två korta meningar utan "med alla funktioner", och
  handlingen "titta gärna på demon …, eller svara på mejlet för en kostnadsfri
  genomgång". Villkorens första mening, den B bär, har samma siffror som förut.
  Iris-instruktionen säger att produktmeningen bär effektiviseringen.
- Låst av `tests/leads/test_struktur_a_kort.py`. Facit 2026-10-16
  (INV-LEADS-UTKAST-002) passerar oförändrat; det tillåter redan `for_langt`.

**Provet i development samma kväll** (nio Snajp-leads i sex branscher, båda
produkterna, Skapa om utkast): 8 av 9 utkast (det nionde föll på
utdatakontraktet, som 2–4 % av utkasten varje dag även före ändringen), median
78 ord mot 105, ingen "balansgång" och ingen fråga, och samma produktval som
researchen gjort. Två saker rättades: "När Footnet säljer …" och "När Nälsta
Bygg …" var "När ni …"-mallen med bolagets namn, så `slentrian_ingang` fäller
nu varje ingång som börjar med "När"; och produktmeningen blev 26–30 ord i sex
av åtta, så kedjan skriver om `lang_mening` i A när villkoren inte själva har
en mening över taket. Andra varvet med samma nio leads (`0cbdbed`): 9 av 9
utkast, median 72 ord (66–89), fem utan stilfynd mot två av åtta, ingen
"När …"-ingång. Kvar och inte rättat: en ingång som ställer krav ("… kräver att
ni kontinuerligt når ut …", en fiskhandel), smicker ("visar ert engagemang",
ett it-bolag) och en översättning av utfallet som går utöver vad Iris gör ("nya
hyresgäster", ett fastighetsbolag). De två första står på köposten som "Stil: …" eller
syns i granskningen; det tredje fångar ingen grind i dag. Anton: "Ja, täpp till
dem." Alla tre fälls nu i kod och skrivs om i kedjan: `kravande_ingang` (A:s
ingång med kräver, behöver, måste eller förutsätter; uppföljningarna undantas),
`smicker` ("visar ert engagemang", "imponerande") och `fel_sak` (Iris tar fram
hyresgäster, privatpersoner, investerare, personal …; inte "uppdrag", som står i
Antons facit 2026-10-12 och fälls bara i B:s fråga). Facit 2026-10-16 och
referensen 2026-10-12 undantar `kravande_ingang` för Ö-Logistik och Consenso,
som `svara_sa_avslut` undantogs 2026-10-25, tills facit för den nya formen är
godkänt. Tredje varvet: 8 av 9, sex av åtta utan fynd, men samma två leads
öppnade "När ni …" i alla tre varven (båda med ingångsformen "vad deras kunder
får av dem", nu omskriven, och ingången är en egen huvudsats), och fyra av fem
Iris-mejl sa bara "nya företagskunder åt er": kedjan skriver nu om en sådan
mening så att den säger vilka sorters företag (`generisk_iris_mening`, bara i
kedjan, inte i stilkontrollen som facit prövas mot). Fjärde varvet: 8 av 9, sju
av åtta utan fynd, median 72 ord. Det nionde utkastet föll i varv 1, 3 och 4 på
att sista omskrivningen saknade `sources_used`, fast en godkänd version fanns,
och de fler omskrivningarna gjorde det vanligare (3 av 36 mot 2–4 % per dag).
En omskrivning eller personalisering som bryter utdatakontraktet fäller nu inte
utkastet: versionen före står kvar och köas med sina stilfynd.

**Öppet för Anton.** (1) Ett nytt facit för A tas ur de första utkasten med
den nya formen och läggs in först efter ditt ja. (2) A/B-testet är nu struktur
A mot struktur B; erbjudandets form A mot B mäts inte längre hos Snajp.
(3) Main kräver en release, och `snajp_malgrupp.py --env main --apply` efter
den.

---

## 2026-11-06 (Anton) — Supportagent i texten, supportbot bara i sökträffen

**Beslut.** Produkten heter supportagent i all text på sajten. "Supportbot"
får stå i en sidas titel och beskrivning, alltså det som syns i sökträffen och
i länkar, men då alltid tillsammans med "supportagent".

**Resonemang.** Antons ord: "Jag vill fortfarande att det står 'Supportagent' i
all text på hemsidan, även om länkar och beskrivningar till dessa kan nämna
'supportbot', men se till att även supportagent används." Supportbot är ett
ord folk söker på ("supportbot sverige"), men det är inte vad produkten heter.

**I koden.** `tests/invariants/test_inv_seo_001.py:test_supportbot_bara_i_sokträffen`
fäller ordet i sökordssidornas innehåll, marknadskomponenterna och sidornas
kropp, och en titel eller beskrivning som nämner supportbot utan supportagent.
`/supportchatt`s beskrivning: "Svensk supportagent för hemsidan: en supportbot
som svarar besökarna ur er kunskapsbas."

---

## 2026-11-05 (Sebbe) — Utskicksstruktur A och B, vald vid Kör Iris

**Beslut.** Iris första mejl får två strukturer. "A är det vi har nu som vi
skickar ut, strukturen alltså. Men B ska vara det nya lite snabbare och direkt
på", efter ett engelskt mejl på tre rader ("If I could … would that be
useful?"). Valet görs med en knapp A/B när man trycker Kör Iris, och texten i
utskicken till körningens nya leads följer valet. B utgår från de tre
exemplen per agent (Iris och Supportagenten): bara frågan, en rad om dem och
frågan, eller med piloten. Siffran för Iris är "40–50 i veckan".

**Resonemang.** Sebbes ord: reglerna att mejlet aldrig slutar med en fråga och
att piloten står i varje mejl "gäller bara en förändring i nya B
alternativ-utskicken": A står kvar som den är. Och: "Det ska vara med samma
signatur och logga som för A … lika anpassningsbar beroende på företag den
skickar till … samma disclaimer text längst ner … samma typsnitt i texten och
färg på texterna. Få in det som rutin (viktigt) för alla utskick som görs för
B … Det ska ha samma funktion rent administrativt som A men såklart
annorlunda text."

**I koden.** `app/leads/utkaststruktur.py` (blocket, förebilderna, varianterna
och `tidigare`), `run_outreach_draft_v2(struktur=…)`, stilgrinden med B:s
regler (`stilkontroll.kontrollera/mot_andra(struktur=…)`: B ska sluta med sin
fråga, högst 60 ord), `LeadsBatchRequest.struktur` → körningens tillstånd →
varje barnjobb, `ProcessaOmRequest.struktur` (utelämnad = leadets förra
struktur, så att Skapa om utkast behåller B), kundens korta utfall per produkt
(`erbjudanden.kort_utfall`, Snajps i `scripts/snajp_malgrupp.py`) och väljaren
i `components/leads/LeadsRunForm.tsx`. B köas genom samma
`_queue_outreach_draft_impl` som A, och signatur, logga, fot och
HTML-rendering är därför desamma. `tests/leads/test_utkaststruktur_b.py`
låser det: svansen efter brödtexten är byte-identisk med A:s och
stilsättningen i HTML:en densamma. A:s facit (INV-LEADS-UTKAST-002) passerar
oförändrat. Erbjudandets "form B (frågan)" är något annat: en variant av A:s
erbjudandestycke, inte struktur B. Anton ska informeras om B.

**Andra varvet, samma dag (Sebbe: "Se till att allt fungerar lika bra för
alternativ B som alternativ A … alla knappar och funktioner").** B finns nu
överallt där ett första mejl skrivs: Kör Iris, "Skapa utkast" på bolagssidan,
i Iris bolagslista och för valda i registret, "Bearbeta om", Skriv körningens
utkast, autopiloten och Flytta/Pröva mot Iris (de två sista via
`automation.struktur`, "Mejlens struktur i automatiska körningar").
Väljaren är en komponent (`components/leads/StrukturVal.tsx`) med samma
minne överallt. Email Studios knappar (Förbättra, Skriv om, Personalisera,
Kortare, A/B-varianter, Översätt) behåller B-formen när mejlet är ett B-mejl
(`lib/leads/struktur.ts:arStrukturB`), och körningslistan visar strukturen.
Provet i development: B-varianten med piloten blev 53–76 ord och upprepade
sig, så piloten är nu en mening med agenten först, villkorens första mening
utan "Handling" (`utkaststruktur.kort_villkor`), och mejlen fördelas i
tredjedelar som förebilderna. Listspårets generella utkast (`listutkast.py`)
har ingen A/B: det är inte Iris första mejl.

---

## 2026-11-05 (Sebbe) — En hängd api-process avslutar sig själv

**Beslut.** "Lös det du!! vad som än krävs", efter att www.snajp.se visade
"Assistenten har svårt att nå sin motor" på varje flik. Om api:s händelseloop
står still i 120 s skriver processen ut alla trådars stack och avslutar sig,
så att Railway startar om den.

**Resonemang.** Produktions-API:t tog emot anslutningar men svarade inte ens på
`/health`, som inte rör databas eller Redis. Processen stod alltså still. Railway
startar om en process som dör, inte en som hänger, och utan en fungerande token
kunde ingen härifrån starta om den. Loopvakten loggade redan stacken vid stopp,
men den startade aldrig om processen. Den kan inte heller köra medan en regex
håller GIL:en. Det är en sämre affär att avbryta en pågående körning (väckaren
tar upp den igen) än att låta sajten ligga nere tills någon märker det.

**I koden.** `app/loopvakt.py:starta_dodsvakt` (`faulthandler` i en C-tråd, når
fram trots GIL:en), `settings.loopvakt_dod_s` (120, 0 = av), startas i
`lifespan` och stoppas när den stängs. Tester: `tests/test_dodsvakt.py`.

---

## 2026-11-05 (Anton) — Sökordssidor, strukturerad data och priser som följer prislistan

**Beslut.** "På Snajp som sökord är vi etta med flera toppresultat och en bra
AI-sammanfattning, men i alla övriga sökord för vår verksamhet dyker vi inte upp
någonstans." Snajp ska synas på breda ord (leads, support, AI-agent), högre på
"svensk support" och "svenska leads", och högst på det specifika: "b2b-leads",
"svensk AI SDR", "leadsagent", "supportagent", "supportbot", "företagssupport".
Sidlänkar med namn som "Support på svenska", "Svenska B2B-leads", "Svensk
AI-SDR", "Svensk supportchatt till er hemsida" och "Svenska leads i inkorgen".
Samma dag: "Se till att priserna automatiskt uppdateras i länkarna vid ändring
på hemsidan."

**Resonemang.** Sajten hade tre produktadresser, ingen med sökordet i titeln och
ingen med en H1 (hjälterubriken var ett stycke). FAQ:ns svar togs ur HTML:en när
de var hopfällda, så en crawler fick bara frågorna. Ingen strukturerad data,
ingen delningsbild, ingen llms.txt. En sida rankar inte på en fråga den aldrig
ställer, och en AI-assistent citerar inte ett svar den inte kan läsa. Varje
sökordssida svarar på EN fråga med eget innehåll (inte åtta kopior, som Googles
regler om doorway-sidor fäller), och priserna räknas ur prislistan så att en
sökträff aldrig visar ett gammalt pris.

**I koden.**
- Åtta sökordssidor (`lib/landningar.ts` registret, `lib/landningssidor.ts`
  innehållet, `components/marketing/Landningssida.tsx` mallen, en mapp per sida
  under `app/`). Länkade från sidfoten på varje publik sida och i sitemapen.
- Nya titlar och beskrivningar på `/`, `/leads`, `/support`, `/faq`,
  `/vart-team` och `/boka-demo` via `lib/seo.ts:sidmeta`, med Open Graph och
  delningsbilden `public/og/snajp.jpg` (utan pris, `scripts/generera_og.py`).
- JSON-LD (`components/JsonLd.tsx`): Organization och WebSite på startsidan,
  SoftwareApplication med pris ur `lib/pricing.ts`, FAQPage och BreadcrumbList.
- Hjälterubriken är en h1; FAQ-svaren står i HTML:en med `hidden`.
- `/llms.txt` (`lib/llms.ts`) för AI-assistenter, byggd ur samma källor.
- IndexNow: nyckelfil i `public/`, `scripts/indexnow.py` och
  `.github/workflows/indexnow.yml`, som efter varje push till main väntar tills
  sajten visar priserna i `lib/pricing.ts` och sökordssidorna i
  `lib/landningar.ts`, och sedan anmäler alla adresser.
- Prisfraserna (`PER_MANAD`, `BINDNING`) bor i `lib/pricing.ts` bredvid
  beloppen, så att även bindningstiden i en sökträff följer prislistan.
- `GOOGLE_SITE_VERIFICATION` och `BING_SITE_VERIFICATION` (Railway, main) ger
  verifieringstaggarna utan kodändring.
- INV-SEO-001 fäller en sökordssida utan mapp, schema eller tenantspärr, en
  titel över 60 tecken och ett handskrivet kronbelopp i det som bär pris ut.
- Plan för det som inte är kod (Search Console, Bing, kataloger, listor, mätning
  med OpenSEO): `docs/SEO.md`.

## 2026-11-02 (Sebbe) — Skickat visar hela konversationen för ett svarat utskick

**Beslut.** "Under 'svarat' ska man se svaren på våra utskick, inte bara
utskicken som det är nu, utan man ska se hela konversationen = (utskicket och
svaret på utskicket)."

**Resonemang.** Filtret Svarat i Leads › Inkorg › Skickat visade bara mejlet vi
skickat. Svaret fanns redan sparat i tråden (`record_inbound_reply`, alla fyra
svarade leads i development har det), men ingen vy i Skickat läste det, så den
som öppnade ett svarat lead fick inte veta vad bolaget svarat.

**I koden.**
- `GET /api/leads/skickat` lägger `konversation` på varje rad vars tråd fått
  svar: trådens skickade och inkomna mejl äldst först
  (`storage.list_konversationer`); osända och kasserade utkast hör inte dit.
- `SkickatLista` visar ett utdrag ur svaret på raden och, utfälld, utskicket
  med signaturen följt av svaret i en egen ruta. Det citerade originalmejlet i
  ett svar fälls ihop (`lib/leads/konversation.ts:delaCitat`), så att vår text
  inte står två gånger. Gäller i alla filter, även ett autosvar under Väntar på
  svar.

## 2026-10-31 (Sebbe) — Uppföljningarna bär erbjudandet, ämnesraderna och stilgrinden

**Beslut.** "Ingen ändring har ju skett i main? Du måste uppdatera alla mail
under 'ny' och 'alla'." Efter att de 125 väntande första mejlen i main skrivits
om med piloten: "Ja, bygg om dem", alltså uppföljningskedjan och de 418
väntande uppföljningarna.

**Resonemang.** Granskningskön visar uppföljningar bredvid första mejlen, och
de 418 i main bar fortfarande det gamla: "svara 'pilot' så berättar jag mer",
"era fem vanligaste kundfrågor" och 20 minuters samtal. 174 hade bolagets
namn i ämnesraden, 116 slutade med en fråga och 62 blandade du och ni.
Uppföljningskedjan läste bara trådens tidigare mejl, så den fick aldrig
erbjudandet, ämnesraderna eller stilgrinden som första mejlet fått sedan
2026-10-25 och 10-29. En omskrivning utan att bygga om kedjan hade gett samma
mejl igen.

**I koden.**
- `follow_up_generator._en_uppfoljning` väljer produkten (researchens, annars
  den trådens skickade mejl nämner först; `erbjudanden.produkt_nu` hittar nu
  också "Vår Supportagent" och "vår AI-support") och kundens erbjudande för
  den (`erbjudanden.for_trad`). Villkoren står i ärendet
  (`erbjudanden.uppfoljningsblock`, uppföljningens korta form, inte formen
  A/B) och i faktagrindens underlag. Tilltalet avgörs i kod som i första
  mejlet. Ämnesraden väljs ur kundens lista och inte en som tråden redan
  burit, och "upp till" står kvar.
- Samma stilgrind som första mejlet: en omskrivning före humanizern och högst
  två varv efter, och versionen med minst fynd köas. Mätt på de 418 gamla är
  fynden verkliga fel också i en uppföljning, så inga fler än
  `lang_mening`/`samma_uppmaning` är undantagna.
- Overlayen `leads-followup.md`: erbjudandet står med, avslutet är dess
  handling och aldrig en fråga, och ämnesraden saknar bolagsnamn och produkt.
- Skapa om utkast (`processa-om`, `scope="utkast"`) skriver om ett kontaktat
  leads väntande uppföljning i stället för att hoppa över leadet
  (`_run_uppfoljningsjobb`, `skriv_om_uppfoljning`). Det gamla utkastet ställs
  in först när det nya passerat grindarna, så ett stoppat nytt lämnar det
  gamla kvar. Timsvepet hoppar över ett lead vars utkast skrivs om, annars
  kunde det skriva en andra uppföljning i samma tråd. Leads utan väntande
  uppföljning hoppas över som förut, liksom full research.

---

## 2026-10-30 (Sebbe) — Snajps Iris: upp till 200 anställda, ingen webbplats krävs, men ett riktigt företag som behöver kunder

**Beslut.** "Utskicken som Iris (Snajp) väljer bort som bortvalda måste
ändras. Stora bolag med 200+ anställda ska filtreras och väljas bort. Ändra
gränsen från 50 anställda max till 200 anställda max. … Det går bra om
företaget inte har en hemsida, men det måste vara ett riktigt företag som
behöver kunder för att kunna driva verksamheten framåt."

**Resonemang.** Snajp säljer Iris och Supportagenten till i stort sett varje
verksamt bolag som behöver nya kunder. Urvalet var för snävt: målgruppen stod
på 1–49 anställda, och i development låg 365 bortvalda. 256 av dem föll på
produktmatchningen ("Ingen av kundens produkter passar bolaget", "visar inget
behov"), bland dem takläggare och byggfirmor, och 95 på "Inget källmaterial".
Bolag utan sajt kom aldrig fram som utskick alls. De hamnade i ringlistan
eller bland ej kvalificerade.

**I koden.**
- Snajps målgrupp är 1–200 anställda (`scripts/snajp_malgrupp.py`, ICP:ns
  `size`). Större bolag fälls som förut i förfiltret, registerfiltret och
  kvalificeringsgrinden. Okänd storlek fäller inget.
- Två nya kundval i `agent_configs.settings` (PUT `/api/leads/config`), som
  följer med in i Iris-profilen via `profil.kundval`. Utan dem beter sig allt
  som förut för alla andra kunder:
  - `webbplats_kravs: false`: registrets bolags-e-post räcker för Iris även
    utan sajt (`merinfo.fordela`), och researchen läser registrets bolagsfakta
    ur allabolag (`allabolag.registerfakta`, uppslag på organisationsnumret,
    aldrig personer eller nummer). Ersätter för de här kunderna regel 10:s
    "bolaget måste fortfarande ha en webbplats" och 2026-10-15-ändringen.
    Valet är inte `utan_webbplats`, som betyder att målgruppen ÄR bolag utan
    sajt (webbyråerna) och som slår på webbmätningen.
  - `behov`: kundens behovskrav ERSÄTTER produktmatchningens fråga (kp), i
    uppgiften (`_KP_PRODUKT` byts mot `_KP_BEHOV`) och i overlayen
    `leads-research-v2.md`. Kravet prövas mot vad bolaget är och gör
    (bransch, verksamhet, omsättning, sajtens erbjudande), aldrig mot om
    produkterna passar, och produktvalet fäller aldrig. Texten står i
    Iris-profilen som kundtext (INV-SEC-009), som raden `kp [BEHOVSKRAV …]`.
    Uppfyller bolaget kravet med ett belagt citat men modellen lämnade
    produkten tom, blir det kundens första produkt. För Snajp: "Ett riktigt,
    verksamt företag som behöver kunder för att driva verksamheten framåt,
    inte en förening, stiftelse eller ett vilande bolag".
- Redan bortvalda bolag bedöms inte om av sig själva. Det kräver en ny
  research (Processa om) och kostar krediter.

**Utfallet i development (samma dag, Sebbes ja till omkörningen).** Snajps
365 bortvalda kördes om i tre omgångar, med en rättelse mellan varje: först
som ett tillägg ovanpå produktfrågan (232 blev nivå B), sedan med kravet
tolkat som vad bolaget är och gör (58 till), sist med produktfrågan helt
ersatt (45 till). Två frågor om kp i samma uppgift gav blandade svar
("på ett sätt som Snajps produkter löser"), och modellen märkte först
utslaget "BEHOVSKRAV" i stället för `kp`. Kvar som bortvalda: 27, nämligen
bostadsrättsföreningar, stiftelser, Byggnads, 9 bolag utanför Göteborg och
Umeå, två utan kontaktmejl och två vars sidor inte gick att hämta.

**Öppet för Anton.** Ändringen rör regel 8 och 10 (bolag utan webbplats till
listspåret) för de kunder som väljer bort webbplatskravet, i dag bara Snajp.

---

## 2026-10-29 (Sebbe) — Utskicken: nyast först, effektiviseringen i fokus, ämnesrader ur en lista, "upp till 50 %" och en demo utan inloggning

**Beslut.** "Alla de nyaste utskicken ska vara högst upp i listorna, så nyaste
först i listan och sedan följs den röda tråden nedåt", likadant i inkorgen,
och nya utskick ska ligga under Ny och Alla, aldrig någon annanstans. Utskicken
ska vara "varma och informerande och ge mottagaren en intressant och kort
inblick i hur vår agent fungerar och hur enkel den är att använda", med
effektiviseringen tidigt: prospekteringen för Iris, kundhanteringen för
Supportagenten. "Ändra inte mycket": mejlet till Andreas (form B) är rätt nivå.
Ämnesraderna ska handla om effektiviseringen, ur Sebbes lista per produkt, där
"Effektivisering av prospektering" och "Support 24/7 för dina kunder" är de
starkaste. "Du får 50 % rabatt" blir "Du får upp till 50 % rabatt om du stannar
efteråt". Demolänken ska ge ett inloggat demokonto där mottagaren testar Iris,
ser demosiffror och kör snabba körningar på påhittade företag, utan riktiga
körningar som kostar tokens.

**Resonemang.** En ny körnings utkast syntes bara under Körningar, och det är
slarv i det första kunden ser. Ingångar som "Era kunder förväntar sig snabb och
kunnig hjälp" klankar ner på bolaget, och "Hur ska ni kunna hantera nya kunder
samtidigt som ni har mycket jobb" är säljigt, pushande och "känns drygt och
konstigt". Det som väcker intresse är att se att jobbet blir enklare, så det ska
sägas tidigt. Modellens ämnesrader ("Fokus på varje affär", "Nya kunder med
höga krav") sa inget om vad mottagaren vinner.

**I koden och prompterna.**
- Leads › Översikt sorterar nyast först (`LeadsTabell.sortera`: senaste
  händelsen, alltså statusbytet när utkastet skrevs, annars när leadet lades
  till; research pågår överst). Ersätter poängordningen från 2026-10-07.
- Granskningskön (`list_review_queue`, Postgres och MemoryStorage) kommer
  nyaste utkastet först. Förut kom de äldsta först och gränsen på 200 klippte
  bort en ny körnings utkast. Kedjans "redan använda ingångar" tar nu de tolv
  första i stället för de tolv sista.
- Inkorgen var redan nyast först (`received_at desc`); ett test låser det.
- Ämnesrader per produkt (`erbjudanden.amnen`, PUT `/api/leads/erbjudanden`):
  koden väljer en per mejl efter att modellen skrivit det (`valj_amne`,
  deterministiskt per prospekt, den första raden i ungefär vart tredje mejl),
  i ni-form när mottagaren inte är namngiven. Utan lista står modellens
  ämnesrad kvar, så andra kunder märker ingenting. Snajps listor står i
  `scripts/snajp_malgrupp.py`.
- `erbjudanden.behall_upp_till`: står villkorens siffra som "upp till 50 %"
  sätter koden tillbaka "upp till" om mejlet tappat det.
- Stilgrinden: `kritisk_ingang` fäller också "era/dina kunder förväntar sig
  eller kräver", "hur ska ni kunna/hinna", "samtidigt som ni har mycket" och
  "tar det tid från". `effektivisera` fälls inte längre när det gäller
  prospekteringen eller kundhanteringen.
- Frågan i form B tar bara den valda produktens moment (`erbjudanden.formregler`):
  omskrivningen samma dag gav ett supportmejl med frågan "… eller att hitta nya
  kunder?" och löftet att Supportagenten "tar hand om båda delarna". Stilgrinden
  fäller fel produkts moment (`fel_moment`) och skriver om mejlet. Avslutet
  "Vill ni testa Iris direkt i demon …, eller svara på mejlet så …" är en halv
  mening och fälls som `halv_inbjudan`; pilotvillkorets handling är omskriven så
  att den inte lockar fram den.
- Ämnesradens du- eller ni-form följer den slutliga hälsningen, även efter
  hälsningspasset vid köningen (`leads_tools`), och stilgrinden
  fäller "Hon" om Iris (`iris_hon`), som Snajps instruktion redan förbjöd.
- Produkten matchas mot kundens produkter i dag (`erbjudanden.produkt_nu`):
  31 av 243 sparade research i omskrivningen saknade produkten eller bar ett
  äldre namn, så inget erbjudande valdes och mejlet tog researchens gamla
  förslag ("prova gratis i två månader"). Produktens nytta i utkastet kommer nu
  också ur dagens inställningar, inte ur researchens tid.
- Snajps inställningar: produkternas nytta börjar med effektiviseringen,
  Iris-instruktionen ber om en varm, kort inblick och förbjuder ingångar om
  vad kunderna förväntar sig, och pilotvillkoret säger "upp till 50 % rabatt
  om du stannar efteråt" och "testa direkt i demon".
- Skrivstilen omgång 8.
- Demon (`/demo`) visas som ett inloggat demokonto utan inloggningsknappar,
  och "Kör Iris" går hur många gånger som helst. Varje körning visar sina steg
  i några sekunder och lägger sedan tre nya exempelföretag med färdiga utkast
  överst under Ny. Efter de sex handskrivna bolagen blir varje omgång tre
  varianter med nytt namn, ny ort och ny kontakt (`exempelVariant`). Inget
  anrop går till modellen; Email Studio svarar med de förskrivna svaren även
  för varianterna.

**Facit.** INV-LEADS-UTKAST-002 är orört och passerar. Facits ämnesregel (två
till fem ord om deras löfte, utan produkt) gäller fortfarande för kunder utan
egen ämneslista; Snajps ämnesrader följer Sebbes lista i stället. Facits
Båtladan-ingång ("Hur hinner du med …") fälls inte av de nya mönstren.

**Öppet för Anton.** (1) Snajps ämnesrader avviker från ämnesregeln i
facit 2026-10-16 genom att vara produktnära och ibland längre än fem ord.
(2) Rabatten är nu "upp till 50 %" i stället för 50 %; den slutliga nivån per
kund avgörs vid avtalet. (3) Några ämnesrader lovar sådant Iris bara gör delvis
("Vi märker när ett bolag är redo att köpa", "varje morgon" kräver autopilot).
(4) Inställningarna och koden ligger i development; main kräver en release.

---

## 2026-10-25 (Anton) — Utkasten: mjukare ingång, inget "Svara X så …", piloten i varje mejl, A/B, egna erbjudanden och kampanjer

**Beslut.** Sebbes utkaständringar 2026-10-24 återställs. De nya Iris-mejlen
"kastar sig in direkt och berättar om 'leadsagenten' helt utan kontext,
ihoptryckt med ett hophafsat erbjudande … väldigt hastigt och svårt att sätta
sig in i och känns robotgenererat." Grunden är upplägget i produktion, med
tre ändringar. (1) Ingången ska läsas som de tre första exemplen Anton gav och
inte som de två sista: "det blir många gånger för offensivt och angripande mot
kunden, det kan träffa en öm tå eller tas som kritik." (2) Avslutet "svara med
x, så gör vi x" är "en svag CTA som läses som botmejl och massutskick och kan
sänka hela mailet, det måste förbjudas helt." (3) Piloten presenteras i VARJE
mejl: 20 företag, en kostnadsfri pilot på tre månader med alla funktioner, och
därefter 50 % för den som är nöjd och vill stanna, "inga mer detaljer där".
Den som vill veta mer går in på snajp.se/demo eller svarar på mejlet, så bokar
vi en kostnadsfri genomgång. Tonen är vardaglig, som från en person till en
annan. Form B testas mot A med lika stor andel: samma ingång, sedan frågan om
vilket som tar mest tid (hantera inkomna leads eller hitta nya; kundmejl eller
supportchattar). Erbjudandena ska styra hela utkastet, inte läggas till som ett
stycke, och kunden ska kunna lägga till egna erbjudanden, se statistik och
styra A/B/C under Leads, för alla kunder. Onboardingen ska ha en sektion för
erbjudanden, och det ska gå att skicka en kampanj till befintliga kund- och
leadslistor med lite anpassning ("Hej Namn," och sedan kampanjen).

**Resonemang.** Kritik i första meningen skapar motvilja innan erbjudandet ens
är läst. En order sist läses som massutskick. Ett tydligt erbjudande i varje
mejl, sagt vardagligt, ger mottagaren ett skäl att svara.

**Utkasten skrevs inte automatiskt (felet).** 27 av 57 researchade bolag fälldes
2026-10-24 med "Ingen av kundens produkter passar bolaget", mot 0 av 53
2026-10-22, fast researchens egen motivering sa att Snajp passar dem. Skälen
var två. Iris produkttext hade skrivits om, och kontextpaketet sa "Du har
INGA godkända erbjudanden … Erbjud därför ingenting" till varje research hos
Snajp, fast erbjudandena finns i inställningarna. Körningens lista visade dessutom
de bortvalda som leads utan utkast.

**I koden och prompterna.**
- Sebbes fyra commits (`16a121f`, `d604e51`, `2f61284`, `7508326`) är
  återställda i sin utkastdel. Leveransändringarna står kvar.
- `context_pack.py`: luckan om godkända erbjudanden försvinner när kunden har
  aktiva erbjudanden. `_korningens_leads`: bortvalda bolag står bara under
  Bortvalda.
- Skrivstilen omgång 7 (Anton), grundprompten § 10, `leads-hard-rules.md` och
  katalogens gemensamma regler: ingången är en utmaning i deras sorts arbete
  och aldrig kritik, avslutet är en vardaglig inbjudan och 60–110 ord.
- Stilgrinden: nya fynd `kritisk_ingang` och `svara_sa_avslut`. Facit
  2026-10-12 och 2026-10-16 slutar med "Svara 'pilot' …" och undantar därför
  `svara_sa_avslut`. Allt annat i facit gäller. Ett nytt facit tas fram ur
  första körningen med den nya formen och godkänns av Anton.
- `erbjudanden.py`: egna erbjudanden (`egna`) med form A (rak) eller B
  (fråga). Blocket säger att erbjudandet styr hela mejlet och översätts till
  mottagarens verksamhet. Snajp kör `pilot_a` och `pilot_b` med lika vikt
  (`scripts/snajp_malgrupp.py`).
- Leads › Erbjudanden (alla kunder med leads): erbjudandena, egna och
  katalogens, med vikt och utfall per erbjudande, samt Kampanjer. Kortet i
  Inställningar är ersatt med en länk dit.
- Onboardingen: sektionen "Erbjudandet i utskicken" i målgruppssteget. Varje
  stycke blir ett eget aktivt erbjudande och står också i affärskontexten.
- Kampanjer (`app/api/leads_kampanjer.py`, migration 114 `kampanj_id`):
  "Hej," med förnamnet satt i kod, och sedan texten, till en lista (även
  CRM-kundlistan) eller en körnings leads. Utkasten går till granskning, och
  "Godkänn och skicka" går genom alla sändspärrar. Spärren släpper ett
  kampanjmejl till kundens egna kunder, men avregistrerade, arkiverade och
  avböjda stoppas som förut.

**Tillägg samma natt, efter provkörningen (12 utkast).** Anton: "'kräver att
ni kan fokusera på varje projekt, inte på att söka upp nästa uppdrag' är
faktiskt helt okej om den förekommer ibland (i olika formuleringar), så länge
det inte är i varje mail, och även bygger på deras verksamhet och väver in
något av det i meningen, som 'att ni fokuserar på måleriet'". Greppet står inte
längre bland mallorden, men det de fokuserar på måste vara deras hantverk:
"varje projekt", "arbetet" och "verksamheten" fälls (`mallord_i_ingangen`). Har
redan två av körningens senaste ingångar greppet fälls det (`samma_grepp`).
Därtill: mejlen var 105–150 ord, och nu är taket 100 ord och ett långt mejl
skrivs om. Pilotvillkoret är kortat. Ingen förmåga får hittas på (Iris
"föreslår nya tomter"). Frågan i form B har fasta moment för Iris och för
Supportagenten.

**Öppet för Anton.** Kampanjer till befintliga kunder är marknadsföring och
inte kallkontakt. Det är lagligt B2B med avregistrering i varje mejl, men en
lista med privatpersoners adresser kräver samtycke. Ingen kod skiljer ut dem
utöver att enskilda firmor redan sållas bort i listspåren. Migration 114
behöver köras i development och main.

---

## 2026-10-24 (Sebbe) — Utskickens text: äkta, konkret, trovärdig (skrivstilens omgång 7)

> **Ersatt 2026-10-25 (Anton):** utkastdelen är återställd, se posten ovan.

**Beslut.** "Förbättra utskicken, texten. De ska sälja in vår produkt bra,
konkret, kort och tydligt. Vi måste få mer svar och bli trovärdiga och
attraktiva … De får inte bli halvdana, halvbra. De ska vara riktigt bra."
Och om Iris: den hittar företagsleads "anpassad efter det kunden söker".

**Resonemang.** Facit-ingångarna återberättade bolagets egen säljtext, som
mottagaren känner igen som sin hemsida omskriven. Erbjudandena var
abstrakta ("nya kunddialoger"), och inget i mejlet gav ett skäl att tro på
en okänd avsändare.

**I koden och prompterna.**
- `leads-skrivstil.md` omgång 7: kärnan (äkta, konkret, tryggt att svara);
  ingången väljer en händelse ur `trigger_events` först, sedan en konkret sak
  på sajten och sist löftet, och bär alltid ett konkret substantiv;
  trovärdighet bara ur underlaget; klyschlistan; konkreta ämnesrader.
- Grundprompten § 10.1–10.2 följer skrivstilen (50–90 ord, villkorens
  handling). Tidigare stod det 70–130 ord och "demo eller samtal".
- `_INGANGSUPPGIFT` och omskrivningen i `leads_research_v2.py` har samma
  ordning för underlaget.
- Stilgrinden: nytt fynd `klyscha`. Facit 2026-10-16 passerar oförändrat.
- `scripts/snajp_malgrupp.py`: Iris nytta säger att leadsen anpassas efter
  bransch, ort och storlek. Iris-mejlen får beviset att mejlet självt är
  skrivet av Iris och läst av en människa före utskick.

**Inte ändrat (Antons beslut).** Erbjudandena och deras villkor (pilotens
"20 företag", de lika vikterna) och regeln att mejlet aldrig slutar med en
fråga. "Upp till 250 leads" står inte i mejlen: en körning tar högst 200
och kunskapsbasen säger 150 prospekt per månad.

---

## 2026-10-24 (Sebbe) — Leveransen: ren text först, flack volym, stopp vid studs och klagomål, kort fot till info@

**Beslut.** "Börja med leveransdelen: ren text i första mejlet, flack
volymkurva med stopp vid studs/klagomål, kort fot till funktionsadresser."

**Resonemang.** ~600 kallmejl gav 9 svar: 2 mänskliga (båda nej) och resten
autosvar. Ett mejl som fastnar i skräpfiltret ger inget autosvar, så de få
autosvaren tyder på att många mejl aldrig nådde inkorgen. Dubblingen från
2026-10-21 (20 → 40 → 80 → 160) släppte ut större delen på några dagar från
`snajp.se`, som nästan inte hade fått några svar. Varje första mejl bar
logotyp och HTML, och en GDPR-fot lika lång som själva mejlet. Inget i
systemet visste hur många mejl som studsat eller markerats som skräppost.
Hela diagnosen: `docs/UTSKICK-SVARSFREKVENS-DIAGNOS-2026-10-24.md`.

**I koden.**
- `send_guard` regel 5d: taket är största dagsvolymen senaste sju dagarna
  + 5, lägst 20, högst `TAK_PER_DAG` = 50. Ersätter dubblingen från 2026-10-21.
- Regel 5e (ny): leveransstopp. Med fler än 0,1 % klagomål eller fler än 3 %
  studsar (minst 20 skickade) de senaste 14 dagarna står tenantens utskick
  still (köa om, även Skicka nu) tills händelserna är äldre än fönstret.
  Skälet syns på köposten.
- Resends webhook `POST /api/webhooks/resend/emails` (email.bounced,
  email.complained) skriver `outreach_messages.leverans` (migration 113) och
  lägger adressen i suppressions. Tillfälliga studsar räknas inte. Utskicken
  bär taggarna `tenant` och `meddelande` så att händelsen hittar rätt.
- Det första mejlet i en tråd går utan HTML och logotyp, och provmejlet följer
  samma regel. Uppföljningarna bär logotypen som förut.
- Kort fot till funktionsadresser: avsändare, org.nr, adress och
  avregistrering, utan art. 14-stycken. Regel 2 kräver policylänken bara vid
  en personlig adress, liksom regel 4. Personliga adresser får hela foten som
  förut.

**Kvar att göra (inte kod).** Registrera webhooken hos Resend för båda
miljöerna och sätt `RESEND_WEBHOOK_SECRET` på api. Utan den svarar webhooken
401 och stoppet ser inga händelser. Kör migration 113 i varje miljö. En
separat utskicksdomän och åtgärderna för erbjudandet (Antons beslut) ingår
inte här.

---

## 2026-10-23 (Anton) — Körningar ska leverera beställt antal: hela registret, sedan brett i området

**Beslut.** "Läs senaste committen från Sebbe och gör vad som krävs för att
körningarna ska leverera beställt antal, vad som än krävs."

**Uppmätt.** Main 2026-10-22, körning f0961755 (200, Göteborg): 18 levererade,
43 researchade, 11 rundor varav 4 tomma, `slut_pa_kandidater`. Sebbes commit
7496a97 tar bort ena orsaken (registrets fällda bolag prövades om varje runda).
Den andra var taket: kundens målgrupp gav fyra sökningar, varav två med träffar
(detaljhandel 7 003, bygg 1 396 i Göteborgs kommun), men `MAX_LISTSIDOR = 40`
lät körningen se högst 2 007 bolag. Ungefär 5 % av registrets bolag blir
Iris-kandidater (resten saknar webbplats eller kontakt och går till
listspåret, regel 8 och 15) och ~40 % av kandidaterna klarar researchen, så
200 var omöjligt per konstruktion.

**I koden.**
- `allabolag.MAX_LISTSIDOR` 40 → 400, allt allabolag bläddrar till (8 400
  bolag för samma målgrupp). Sidorna är gratis och cachas per kund.
- Första tomma rundan (utan sökfel) i kundens egna branscher sätter
  `korning["bred"]`: rundorna därefter söker de breda B2B-branscherna i SAMMA
  område (`merinfo.sok(bred=True)`, Konsulter/Byggmästare/Grossister/
  Producenter, ~20 000 bolag i Göteborg), med samma filter, Jev och research.
  Räkningen av tomma rundor börjar om, och sammanfattningen säger att
  sökningen breddades.
- Området breddas aldrig: bedömningen fäller bolag utanför målområdet ändå,
  och kunden har bett om just det området.

---

## 2026-10-21 (Anton) — Uteslutna bolag ALDRIG i sökprompten; registret på i main nu

**Beslut.** "Problemet är INTE AI Studio eftersom vi kör med Vertex … Det är
något annat som blockerar, ta reda på orsaken och gör vad som krävs för att
lösa det, det får inte finnas såna här problem längre."

**Rotorsaken, uppmätt i mains egen anropslogg (agent_runs, leads_underlag).**
Main kör Vertex (servicekontot, europe-west1, gemini-2.5-flash), och
sökanropet lyckades i alla fyra rundorna i de tre fallna körningarna (11:45,
11:48, 12:28). Men prompten bar "Uteslut dessa namn:" med de 150 första
upptagna bolagen i bokstavsordning, och modellen skrev om dem till minustermer
i Googlefrågan: 13 080 tecken ("-24seven vending sweden -2complete …"), noll
källor, tomt svar. Listan växer med varje sparat lead och varje lista, så
felet kom när tenantens upptagna bolag passerade taket. Sebbes AI Studio-spår
(404/402) gäller inte main: där används AI Studio-nyckeln inte av sökningen.
Omprövat mot mains Vertex samma dag: med listan frågor på 3 300 tecken och
0 källor, utan listan frågor på 74 tecken och 9 källor.

**I koden.** `discovery.hitta_bolag` skriver inga namn i prompten;
uteslutningen sker bara i `_rena_traffar` efter svaret (den gjorde det redan).
`_uteslut_i_prompt`, `PROMPT_UTESLUT_TAK` och `upptagna.bara_namn` är borta.

**I miljön.** `LEADS_REGISTER=allabolag` på api i main, så att registret
(gratis, inga ScrapeGraph-krediter) är huvudkällan redan innan Sebbes
standardbyte når main. Uppmätt lokalt med mains Vertex: 12 Göteborgsbolag på
89 s. Den öppna sökningen ensam är svag även utan namnlistan (modellen vägrar
lista bolag när den inte kan se storlek och kundtyp i träffarna) och är bara
utfyllnad.

## 2026-10-21 (Claude, på Sebbes beställning) — Registret på som standard; fallna sökrundor heter "sökningen föll"

**Beslut.** "LÖS DETTA … det får ej bli sånna här problem." Tre Iris-körningar
à 70 leads i main 2026-10-21 (11:45, 11:48, 12:28) stannade på 0 undersökta
med rådet "kontrollera stavningen på orterna" — fast kunden inte fyllt i
något filter alls.

**Rotorsaken, uppmätt.** Main hade varken `LEADS_MERINFO` eller
`LEADS_REGISTER`, så registret (allabolag) var av och varje sökrunda hängde
på den öppna Gemini-sökningen. Dess AI Studio-väg är dubbelt död:
`gemini-2.5-flash` är borttagen (404 "no longer available … use
models/gemini-3.8-flash") och krediten är slut (402) — uppmätt 2026-10-21 med
både main- och dev-nyckeln. Varje runda föll med DiscoveryError, men
`rond["fel"]` blev bara `stopp` vid max_rundor (105 för 70 leads), som de
fyra tomma rundorna aldrig når: körningen slutade som `inga_traffar` och
skyllde på kundens ortnamn.

**Tre lager i koden.**
1. `merinfo.aktiv()`: HELT osatt (ingen av flaggorna) betyder nu allabolag
   PÅ. Antons beslut 2026-10-15 ("Registret hämtas från allabolag") gäller
   körningarna som sådana, inte en miljö, och hämtningen är gratis och hövlig.
   En TOM sträng är fortfarande uttryckligt AV (testsvitens hermetik och
   drift-avstängning). `LEADS_MERINFO=scrapegraph`-vägarna är oförändrade.
2. `_sla_in_sokrunda` räknar fallna rundor (`k["sokfel"]`), och slutorsaken
   blir `sokningen_foll` när sökningen föll och inget levererades — kunden
   ser ett tjänstefel i rött, aldrig ett råd om stavning
   (`korning.avsluta`/`sammanfatta` följer med).
3. `discovery._sokmodell`: AI Studio-vägen byter borttagna `gemini-2.5-*`
   mot `gemini-3.8-flash` (Googles anvisade ersättare). Vertex-grenen rörs
   inte — europe-west1 har kvar 2.5 och saknar 3.8 (EU-beslutet 2026-10-16).

**Kvar utanför koden.** AI Studio-nycklarnas kredit är slut (402) — i miljöer
med Vertex-servicekontot används de inte av sökningen. Railway-tokenen i
`.env.deploy` svarar "Not Authorized" sedan 2026-10-21, så mains variabler
gick inte att läsa eller sätta härifrån; registret-på-som-standard tar bort
behovet av ett env-handgrepp i main.

## 2026-10-21 (Sebbe) — Mjuk volymupptrappning efter uppvärmningen (regel 5d)

**Beslut.** "Bygg den mjukare upptrappningen." Bakgrund: när åldersfixen
(2026-10-20) tog bort det eviga 20/dag-taket fanns inget tak alls efter
uppvärmningens 14 dagar — de ~230 köade godkända utkasten gick ut på en
förmiddag (223 skickade 2026-10-21) från en domän som dittills skickat 20 om
dagen. Mottagarfilter läser volymkurvan, inte innehållet.

**I koden.** `send_guard` regel 5d: efter uppvärmningen är dagens tak
`UPPTRAPPNING_FAKTOR` (2) gånger största dagsvolymen de senaste
`UPPTRAPPNING_FONSTER_DAGAR` (7) dagarna, aldrig under uppvärmningsgolvet
(20). Volymen får alltså dubblas per dag: 20 → 40 → 80 → 160 … Innevarande
dag räknas INTE i underlaget (`storage.storsta_dagsvolym`) — annars höjer
varje skickat mejl taket och det binder aldrig. Sju dagars fönster så att en
helg inte nollställer kurvan; efter en veckas tystnad börjar den om från 20,
vilket är rätt kurva efter ett uppehåll. Taket gäller även Skicka nu: regeln
skyddar domänens rykte mot volymen, inte mot klockslaget. Stoppet är KÖA OM —
resten av kön skickas kommande dagar, med besked i köposten.

**Beslut.** "Sänk den just nu … sikta på runt 1000." Först development, sedan main.

**Resonemanget.** 1,5 miljarder (beslutet 2026-10-20) var räknat på 500
körningar, men utan Pro räcker ett lägre tak. Ett levererat lead på flash drar
~150 k tokens (research + utkast, uppmätt i main 2026-10-20). 1 000 leads ≈
150 M tokens ≈ 60 USD per dygn om taket nås.

**I miljön.** `LEADS_DAILY_TOKEN_BUDGET=150000000` på api i development och
main (båda var 1 500 000 000). Anton: "Gör samma beslut där."

## 2026-10-21 (Anton) — Utkasten på flash i båda miljöerna; development skriver aldrig till main

**Beslut.** "Byt till flash även i development, ändra inte kedjan i övrigt."
Och: "gör så att inget skrivs från development längre, fyll bara på från main
och synka endast körningar från development via Flytta till main-funktionen."
Samt: alla leads ska synas i listan.

**Resonemanget.** Pro-bytet 2026-10-16 (nedan) stod för 1 116 av 1 419 kr på
Vertex 6–20 oktober, 10–15 gånger flash per lead, och var aldrig prövat mot
flash på den färdiga kedjan. Mätt med dagens stilgrind på utkast skrivna efter
2026-10-18: flash 16 % med fynd (56 utkast), pro 14 % (180). Ingen belagd
skillnad som motiverar priset. Kedjan i övrigt (grindar, humanizer, tilltal)
står kvar.

**I koden och miljön.**
- `LEADS_DRAFT_MODEL` och `LEADS_HUMANIZER_MODEL` borttagna på api i
  development; main hade dem aldrig. Stegen ärver `MODEL=gemini-2.5-flash`.
  Ersätter beslutet 2026-10-16 om gemini-2.5-pro.
- `scripts/railway_synk.py` öppnar main skrivskyddat utanför första synken:
  synken kan mekaniskt bara skriva till development.
- `scripts/flytta_korningar_till_main.py` tar bara körningar (batch, lista),
  inte delstegen per lead. Kontrollerat 2026-10-21: main har alla körningar,
  alla utkast och inga dubbletter (1 331 leads hos snajp).
- `GET /api/leads/prospects` bläddrar (`offset`, `fler`, `nasta`) och
  klienterna hämtar alla sidor (`allaProspekt`); Skickas snart slår upp
  prospekten med id. Förut syntes bara de 500 respektive 1 000 nyaste.

## 2026-10-20 (Anton) — Leadsbudgeten räcker till 500 körningar per dygn

**Beslut.** "Höj även tokenbudgeten för att klara motsvarande 500 körningar
per dag."

**Resonemanget.** En körning med 200 leads i main stoppades av dygnsbudgeten
(4,5 M av 2 M tokens). Taket var satt för att fånga en skenande kostnad
(INV-JOB-002), inte för att begränsa vanligt arbete. Uppmätt i
development-spegeln 2026-10-20: 58 körningar de senaste 14 dygnen drog
165 M tokens, alltså ~2,85 M per körning (~100–150 k per lead, 96 % input).
500 × ~3 M ≈ 1,5 miljarder tokens. På gemini-2.5-flash är det i värsta fall
omkring 600 USD per kund och dygn om hela taket används.

**I koden.** Ingen kodändring: `LEADS_DAILY_TOKEN_BUDGET=1500000000` på
`api` i Railway, både main (var 2 000 000) och development (var 120 000 000,
spegeln räknar också main:s körningar). Kodens standard (2 M) gäller
fortfarande en miljö utan variabeln.

## 2026-10-20 (Sebbe) — Alla körningar till main, utkasten följer med flytten, sändspärrarna lösta

**Beslut.** "Gör migration med alla körningar från development till main, inga
dubbletter får finnas, inga mail får tas bort. Alla nya körningar ska köras
från main. De körningar som görs från development ska gå att flytta till main
genom knappen." Och: "Lös 'sändspärr'."

**Resonemanget.** Första synken (2026-10-17) gjorde main till sanningen, men
körningar gjorda i development efteråt låg kvar där (494 stycken 2026-10-20),
och körningsflytten bar inte trådar, utkast eller köposter (handoffen
2026-10-17, punkt 4) — mejlen hade blivit kvar. Samtidigt stod 201 godkända
utkast i kö i main utan att gå ut: tenantens ålder lästes som en ISO-sträng
och blev 0, så uppvärmningstaket (20/dag) släppte aldrig, och 92 poster var
spärrade på skäl som redan var åtgärdbara (policy_url saknades i
kundregistret; org.nr-kravet mjukades upp redan 2026-10-10).

**I koden.**
- `admin_flytt`: varje prospekt i en körnings- eller prospektflytt bär sitt
  väntande utkast (`_utkast_for`/`_importera_utkast`); ett godkännande gjort i
  development skrivs om till `godkand_i='main'` (main skickar). En omflytt av
  en redan flyttad körning kompletterar det som saknas ("kompletterad") i
  stället för att stanna vid job_id-dubbletten, så bulkflytten går att köra
  om. Dedup-taket höjt från 500 till 5000 prospekt (snajp hade 873 — allt
  däröver hade blivit dubbletter). Kandidatlistan visar 200 körningar, inte 10.
- `scripts/flytta_korningar_till_main.py`: bulkflytt av alla dev-only
  körningar genom flyttvägen (INV-DATA-003), aldrig SQL.
- `scheduler._alder_i_dagar` parsar ISO-strängar: uppvärmningstaket gäller
  tenantens riktiga ålder, inte evigt "0 dagar".
- `utskicksfot.byt_fot` + `leads_tools.lagstadgad_fot`: en föråldrad fot
  (byggd innan kundregistret fylldes) byts mot den aktuella vid godkännande
  och i sändaren, i stället för att stå kvar och blockera regel 2 för evigt.
- `scripts/los_sandsparr.py`: godkänner om spärrade poster med åtgärdbara
  skäl via samma API som knappen "Godkänn och skicka" — spärrarna körs om i
  sändögonblicket, så inget går ut som inte passerar alla sex.

**Observera.** När åldersfixen når main släpper 20/dag-taket helt för tenants
äldre än 14 dagar: de ~200 köade utkasten går då ut samma dag inom
sändfönstret (08–17 vardagar). Det är regelverkets avsedda beteende efter
uppvärmningen, men värt att veta innan releasen mergas.

## 2026-10-19 (Anton) — Nyckeltalen räknas fram när man kommer dit

**Beslut.** "Kan du göra så att dessa siffror 'genereras' i realtid när man
kommer dit?" (resultatvyns nyckeltal på /leads och /support).

Rättat samma kväll: "De är helt fulladdade vid scroll ... det måste ske
naturligt vid scroll och när de är helt i bild, det får inte gå för snabbt."

**I koden.** `RaknaUpp` i `components/marketing/AgentResultat.tsx` räknar
varje tal från noll till sitt värde på 2,6 s, ett tal i taget med 0,28 s
mellan. Starten kommer först när talet står helt i bild ovanför skärmens
nedersta femtedel, plus 0,45 s så att raden hunnit tonas in. Enheten och decimalerna följer med ("71 %", "4,6"), och
hela värdet håller bredden så att etiketterna står still.

## 2026-10-19 (Anton) — Hjälten skrivs fram, bilderna står hela, översikten bort

**Beslut.** "Hela herotexten för support är i färg, gör så att enbart 7:an är
det. Gör även så att bilderna laddas hela, nu ser det ut som att de renderas,
som att sidan laddas långsamt. Ta även bort hela dashboard-sektionen, den
tillför inte något i nuläget och skiljer sig från de konstruerade rutorna. Se
även till att texten för Om oss-sektionen på supportsidan inte innehåller massa
leads-referenser. Gör även så att hero-texten skrivs ut på samma sätt som
rutan, fast långsammare och mer effektfullt, med betoning på sover, samma med
Support, men byt det till: Era kundärenden hanterade, 24/7." Och: "Gör även
texten i rutorna större i desktop och låt den fylla upp dem mer."

**I koden.** `HeroText` (`components/marketing/LiveText.tsx`) skriver fram
rubriken när dörren öppnas (`hero:type` från `useLandingMotion`). Paus efter
kommatecken och före det betonade ordet, som sedan skrivs i halv fart. Betoningen
ligger på "sover" och på 7:an, i den ljusare ockran (`text-ochre`), eftersom
`text-warning` försvann mot solnedgången. Fotona avtäcks inte längre med
clip-path, bara parallaxen är kvar. `DashboardIsar` är borttagen med sin
rörelse och CSS. `varforSupport` (copy.ts) ersätter `varforSnajp` på
supportsidan. Rutornas innehåll zoomas 1,12 från 1280 px och 1,25 från 1536 px
(`.case-zoom`), och minsta höjden delas med zoomen så att rutan behåller sin höjd.

## 2026-10-19 (Anton) — Live-skrivning, tydligare studs, inga tekniska referenser i demon

**Beslut.** "Testa göra skuggan i heron svagare, eller skippa den helt. Gör
även animeringarna för rutorna jämnare och mjukare, och gör
studsseffekten/tillbakafjädringen tydligare. Skapa även effekten att texten
skrivs live, för alla omgenereringar/knappval också, ta även bort alla
tekniska referenser, endast korta motiveringar."

**Resonemang (Anton).** Skuggan bakom ingressen syntes som en skugga. Studsen
var för subtil för att märkas. Demons svar ska kännas som att agenten skriver,
och motiveringarna ska läsas av en kund, inte av en utvecklare.

**I koden.** Den ovala mörkningen är borta; på mobil bär ett mjukt mörkare
band i fotot läsbarheten (5,3:1). Fjädern 0.75/0.75 → 0.66/0.95 (studs ~11 px,
mjukare glidning). `LiveText` skriver fram showcase-utkasten när rutan landat;
demons omskrivningar skrivs fram i rutan och panelen visar bara en kort
motivering (marknadssidan; arbetsytan oförändrad). Startsidans exempelmejl
fick egna svar (`lib/data/emails.ts`), förut svarade varje knapp att demot
bara fanns för andra bolag. Prompten ber inte längre modellen hänvisa till
principer och filer, och `utanReferenser` stryker meningar som ändå gör det.
Kvar: de sex /demo-bolagens motiveringar nämner "CTA" och har pilscheman.

## 2026-10-19 (Anton) — Startsidan: ytor glider in på en fjäder, två upprepande sektioner bort

**Beslut.** "Jag vill att själva rutorna rör sig in mjukt på skärmen och att
enbart den beskrivande texten revealas istället, en ruta i taget, inte båda
samtidigt … mjuk och glida in stoppa och studsa tillbaka lite, men väldigt
subtilt, tänk apple." Samma för den stora översikten. "Ta bort sektionen
längre ned med i princip samma punkter, samma sak med den andra sektionen om
Snajp, låt byggt i Göteborg-sektionen vara kvar." Rubriken "Ni ser
resultaten, inte maskineriet." blir "Förvärmda leads, levererade till er."
Hjältens ingress ljusas upp, och mellanrummet mellan löftet och första rutan
stängs.

**Resonemang (Anton).** Rutorna var "laggiga och vibrerar vid scroll, särskilt
om man scrollar fram och tillbaka", och en tonad avtäckning läste inte som att
något kom in på skärmen. "Tre steg" upprepade löftets punkter direkt under
hjälten, och "Vilka är vi" upprepade "Byggt i Göteborg". Ingressen var
"knappt läsbar mot herobilden".

**I koden.** Vibrationen hade en mätbar orsak: `.rise` lade en CSS-transition
på samma `transform` som GSAP skrubbade varje bildruta. Den skrubbade driften
och klippningen är borta; i stället `caseEntry` (`useLandingMotion.ts`,
markup `data-case`/`data-case-box`/`data-case-text`) med Apples fjäder som
GSAP-ease (`gsap.js: spring(0.75, 0.75)`), som spelar en gång och köar ytorna.
Sprängskissens linjer räknas ur perspektivet i stället för fyra
`getBoundingClientRect` per bildruta, och `anticipatePin` är borttagen.
"Tre steg" och "Vilka är vi" är borttagna ur `LandingPhoto.tsx` och copyn
(`steps`, `stepsHeading`, `vilka*`); länken "Läs mer om oss" flyttade till
Byggt i Göteborg. Regeln står i `DESIGN.md` § Ankomstfjädern.

## 2026-10-18 (Sebbe) — Körningar på upp till 200 leads, rullbar leadslista och levande lägesrad

**Beslut.** "Ändra så att man kan söka upp till 200 leads … håller lika bra
kvalitet och att företagen man filtrerar, alla 200 ska vara bra företag …
relativt snabb att hitta alla leads." Vid 50+ leads visas körningens leads i
en låda som går att rulla och dra ut i höjdled, med samma snabbklick per lead
till utkastet som förut. I körningsvyn byter "Researchar" till nya
formuleringar ("Hittar dina nästa kunder…", "Gräver i registren", …) var
tionde sekund, med en diskret intoning.

**Resonemang (Sebbe).** Taket 50 var för lågt för volymkörningar. Kvaliteten
ska inte sänkas med volymen: samma grindar (förfilter, existens, Jev,
bedömning, utkastgrindarna) per bolag som vid 50. Sidan ska inte bli
kilometerlång vid 200 leads, och väntetiden ska kännas levande, inte stå
stilla på ett ord.

**I koden.** `LeadsBatchRequest.limit` le=50 → 200 (`app/api/schemas.py`),
formulärets max/hint (`components/leads/LeadsRunForm.tsx`). Kredittaket
`korning.korningstak` höjt 600 → 2400 så 12 hämtningar/lead gäller även vid
200 — annars hade en 200-körning svalt vid 3/lead; motorns övriga tak
(`TAK_FAKTOR`, `max_rundor`, `TOMMA_RUNDOR`) skalar redan med målet, och
kvalitetsgrindarna är oförändrade per bolag. Rullbara lådan vid 50+ rader:
`KorningensUtkast.tsx` (RULLBAR_FRAN) och `IrisKorningar.tsx:rullbarLista`
(även tratten). Lägesraden: `RoterandeStatus` + fraslistorna i
`IrisKorningar.tsx`, intoningen `@keyframes statusbyte` i `app/globals.css`
(släcks av prefers-reduced-motion).

---

## 2026-10-18 (Anton) — Startsidan: Dygnets dygnsljus, mjuka övergångar, isärtagen översikt, fetare serif

**Beslut.** Startsidan behålls som den är (hjälten, bilderna, alla sektioner,
uppdelningen Leads/Support, de konstruerade produktytorna) och får ovanpå det:
Dygnets dynamiska dygnsbakgrund som börjar i soluppgång under hjälten och blir
varmvit längst ned, vackra övergångar och effekter mellan alla sektioner, en
enstaka dynamisk bild av dashboarden där elementen delas upp som i
Isärtagning men utan lutning, texten (inte rubriken) från "Varför Snajp finns"
på /vart-team under "Byggt i Göteborg", och ett fetare serif-typsnitt som inte
är Fraunces. "Gör allt detta mjukt."

**Resonemang (Anton).** Av de fem koncepten på boarden kom nummer 1 (Dygnet)
närmast estetiskt; i stället för fem nya koncept ska den riktiga sidan ta över
Dygnets ljus och ambitionsnivån i rörelsen, med befintligt innehåll.

**I koden.** `components/marketing/useLandingMotion.ts` (GSAP 3.15 + Lenis via
repots `gsap.js`/`smooth-scroll.js`, dynamiskt importerade eftersom de rör
`window` vid import): dörren, ljusmotorn (mark `--ground` + fyra ljusrutor i
multiply, hål för hjälten och produktytorna), radmaskade rubriker, klippta
avtäckningar, parallax, ord som fylls av skrollen, ritade sektionslinjer och
den pinnade sprängskissen. `components/marketing/DashboardIsar.tsx`: översikten
(demo, exempeldata) i fyra delar ur samma skärmdump. `LandingPhoto.tsx` bär
`data-mo`-markörer och `key` per produkt+språk på rubriker som SplitText
spaltar.

*Agentens val, att pröva (Anton):* serifen är **Source Serif 4** (variabel vikt
200–900, optisk storlek, äkta kursiv): lägre kontrast än Fraunces och
Newsreader, så den bär vikt över hjältefotot. Den är scopad till
marknadssidan via klassen `serif-fet`; appytorna behåller Fraunces tills Anton
säger annat. Inga nya foton lades till: beställningen tillät det men krävde det
inte, och sprängskissen använder produktens egen yta. Lenis lever kvar i
sessionen efter att man lämnat startsidan (en skrollägare, som husets regel
säger); inre skrollytor i demon behöver `data-lenis-prevent` om de visar sig
fastna. Den gamla `.rise`-avslöjningen (useReveal) används inte längre på
startsidan; klasserna står kvar och är verkningslösa där.

**Rättningar samma dag efter Antons första titt** ("dashboarden vibrerar och
hackar och hoppar åt sidan", "bakgrunden helt borta", "lägg till text",
"animationer för showcase-rutorna"): dygnet sträcks över hela sidan och når
varmvitt först vid priset (det nådde vitt redan vid demon); marken ritas på
ett eget fast lager i stället för en variabel på roten (en variabel räknade
om stilen för hela sidan varje bildruta); sprängskissens kamera drar sig inte
längre tillbaka (skalan .94 flyttade översikten 35 px i sidled och lästes som
ett hopp), ljusets hål har decimaler (hela pixlar gav kanter som hoppade) och
delarna är egna hål. Sektionen fick en rubrik och en ingress: **ny copy, inte
godkänd av Anton än** ("Hela dagen på *en skärm*." / "Översikten visar vad
agenterna gjort: körningar, levererade leads, det som väntar på en människa
och vad det kostat. Varje del uppdateras medan Iris arbetar."). Showcase-
rutorna (ProduktBilder) fick liv: delarna kommer i berättelsens ordning när
figuren avtäcks och utkasten skriver sig själva uppifrån; bara element
animeras, aldrig textnoder, eftersom React äger texten.

**Andra varvet samma dag** ("det ser fortfarande för jävligt ut": rubriker
och showcase-delar osynliga, dashboarden hackar, ingen tydlighet):

- *Avslöjandena är idempotenta.* Första versionen byggde varje avslöjande som
  en `gsap.from` med engångs-ScrollTrigger, skapad om i SplitTexts `onSplit`;
  varje omspaltning (fontbyte, storleksändring, dev-serverns hot reload) dolde
  redan visade element igen utan att en ny trigger spelade dem. Nu döljs ett
  element högst en gång och visas av `play()`, som stämplar `data-rv="1"` och
  är en no-op andra gången; ScrollTrigger, en IntersectionObserver och en
  timer kan alla kalla den. Verifierat i riktig Chromium 1920 med hjulet hela
  vägen ned: 0 dolda element.
- *Hackandet var mätt, inte gissat.* Bildrutetider i riktig Chromium med GPU:
  allt på 31 % tappade bildrutor (p95 50 ms); utan multiply-blandningen
  0,8 % (p95 17 ms). Dygnet-konceptet självt låg på stadiga 30 fps med samma
  teknik. Ljuslagret ligger nu under innehållet (ogenomskinliga ytor täcker
  det, inga hål), komponeras med vanlig alfa (rutorna målas i markens färg i
  stället för multiply), rutorna skalas med transform i stället för att byta
  bredd, och oskärpan byts i steg om 3 px. Resultat: p95 17 ms, 0,9–2 %
  över 33 ms, allt på. Lenis vaktar dessutom mot en andra instans vid hot
  reload (`smooth-scroll.js`).
- *Sprängskissen fick avsikt.* Texten står inne i det pinnade blocket till
  höger om bilden (rälen sitter till vänster: linjer från vänster försvann mot
  den), tre förklaringar tänds i tur med en ritad linje och en prick vid sin
  del, grundbilden byts mot en förblurrad tvilling (oskärpa rastrerad en gång),
  och kameran drar sig inte tillbaka. Förklaringarnas ord är produktens egna
  paneltitlar; rubrik, ingress och förklaringar är ny copy att godkänna.
- *Showcase-rutorna rör sig.* Figurerna glider mjukt mot sidan medan de
  passerar (den andra lite senare än den första), avtäcks nedifrån med en
  liten skalning, och delarna inne i ytan kommer i berättelsens ordning.

---

## 2026-10-17 (Anton) — Main blir sanningen efter första synken; körningar i development flyttas aktivt

**Beslut.** Alla körningar från development följer med till main, utom de som
är märkta som testkörningar. "Datan måste speglas sömlöst. När vi fått över
alla körningar från development blir main sanningen och synkar till
development, och körningar gjorda i development behöver flyttas aktivt enligt
tidigare principer." Ersätter tvåvägssynken (2026-10-10, nedan).

**Resonemang (Anton).** Se citatet. Development går tillbaka till att vara en
spegel av produktionen, med den skillnaden att körningarna som gjorts där
fram till releasen följer med en gång.

**I koden.** `scripts/railway_synk.py`: `--apply --forsta` för över allt
åt båda hållen med development som vinnare (som förut) och sätter
`mirror_meta.lage = 'envags'`. Därefter skriver synken bara till development:
main vinner varje skillnad, raderingar i main slår igenom, och rader som bara
finns i development står kvar tills de flyttas med Byt kund → Flytta till main
(`admin_flytt`). Provkörningar synkas aldrig.

*Agentens tolkning, att pröva (Anton):* development skickar inga utskick i det
här läget (`scheduler.skickas_har`, `utskick_bara_i_main`). En spegelrad som
development skickade hade fått tillbaka main:s status vid nästa synk och kunnat
gå ut en gång till. "Godkänn och skicka" i development svarar att utskicket görs
i main efter en flytt. Det ersätter "det måste gå att skicka utskick från
development också" (2026-10-10). Första synken skriver om `godkand_i` från
development till main på de köade utkasten (193 st., godkända 2026-10-12–16),
så att main skickar dem när sändfönstret öppnar måndag 08:00. Provmejl
påverkas inte.

*Att veta (agenten):* första försöket fyllde development-databasens volym
(500 MB, skapad på provplanen) när synken kopierade tabellerna, och Postgres
kraschade. Volymerna i båda miljöerna är nu 5 000 MB (Hobby-planens tak), utan
kostnad utöver använt utrymme.

## 2026-10-17 (Sebbe) — Duo i fokus, ingen Trio; Kvittohanteraren blir tillägg till Support

**Beslut.** "Ta bort den från marknadssidorna och priserna också. Det ska vara
en tilläggstjänst till supporten. Main fokus är att det ska finnas Snajp duo,
inte trio."

**Resonemang.** Följer beslutet nedan samma dag: Kvittohanteraren ska inte
säljas än. När den kommer tillbaka är den ett tillägg till Support, inte ett
eget paket, och paketet Snajp säljer är Duo.

**I koden.** `lib/pricing.ts`: paketen är Support, Leads och Duo; Trio och
"Snajp Kvitton" (2 690 kr) är borttagna, liksom kampanjen à 999 kr.
`KVITTO_TILLAGG` beskriver tillägget (kräver Support, pris inte satt). Adminens
paketflik har en kryssruta för tillägget; det skrivs som produkten
`bookkeeping` bredvid paketets, så en kund som hade Trio läses som Duo +
tillägget utan migration (intäktsberäkningen räknar dem som Duo tills
tillägget har ett pris). Marknadssidorna: produktväxeln och demopanelerna
visar bara Leads och Support (`saljbaraProdukter`), `/kvitton` och
`/bokforing` leder till `/support`, demolänken, FAQ-frågan om kvitton och
"alla tre agenterna" är borta, och Snajps supportchatt (`snajp_kb.py`) säger
tre paket. Kvittosidans texter och demo står kvar i koden för en lansering.
Användarvillkoren (`/villkor`) är inte ändrade.

## 2026-10-17 (Sebbe) — Kvittoagenten står på is: mörklagd för kunder, borta ur utkasten

**Beslut.** "Kvittoagenten ska inte vara i fokus för Snajp att sälja. Den ska
vara mörk till vänster i menyn på arbetsytan och som kund ska man inte kunna
klicka in på den. Den ska inte heller finnas med i utkasten. Vi i admin ska
absolut kunna använda den." Utkast som bara handlar om kvittoagenten tas bort;
utkast som också nämner en annan agent behålls, kvittotexten redigeras bort
och utkastet skickas.

**Resonemang.** Snajp ska inte sälja Kvittohanteraren än, utan hålla den på
is ett tag till. Kunden ska ändå kunna se att den finns ("man ska ändå kunna
se att det står Kvitto"), men inte öppna den.

**I koden.** `VILANDE_PRODUKTER = ["bookkeeping"]` i `lib/routes.ts`.
Kundens `products` filtreras i `resolveDashboardState` (admin behåller dem),
så menyn, `WorkspaceSection`, Att göra och kvittoproxyn säger samma sak.
Railen ritar posten som ett mörklagt `<span>` utan länk ("Kommer snart"),
och en kund som skriver adressen landar på översikten. Demon gör likadant.
Plattformsadmin når Kvitton som förut via adminytan. Kunder som har paketet i
databasen (Umeå Webbdesign och Alunix i main) behåller det där: det är
visningen som pausas, inte avtalet. Snajps Iris i development: Kvittohanteraren
borttagen ur produkterna, erbjudandevillkoren, segmenten och affärskontexten
(`scripts/snajp_malgrupp.py`), och Iris-instruktionen säger att kvitton och
bokföring aldrig nämns. 12 osända utkast som bara sålde Kvittohanteraren
avvisades (sju godkända som väntade på sändfönstret, fem i granskningen), och
uppföljningen till Investbygg fick ordet "kvittoredovisning" borttaget och
godkändes. Main hade inga kvittoutkast. Släpps igen genom att tömma listan och
lägga tillbaka produkten i `snajp_malgrupp.py`. Marknadssidorna, priserna och
supportchattens kunskapsbas säljer den fortfarande; de är inte ändrade.

Tillägg 2026-10-18: uppföljningssvepet i main skrev ändå nya
kvittouppföljningar (fyra på två dygn), eftersom det följer upp tråden och
modellen läser det tidigare mejlet. En tråd vars utgående mejl nämner en
vilande produkt följs inte längre upp (`app/leads/vilande.py`, kontrollen i
`follow_up_generator._en_uppfoljning` före modellanropen).

## 2026-10-17 (Sebbe) — Utkastkedjan köar den renaste versionen, inte den sista

**Beslut.** "Ja, kolla varför mallorden överlever grinden." Utredningen gav
rotorsaken, och fixen är att varje humaniserad version prövas av stilgrinden
och att den med minst fynd köas.

**Resonemang.** Skarpa provet på fem Snajp-leads köade "kräver fullt fokus"
(Nordic Express) och "tar tid från att" (Moogio). Stegloggen visade att båda
gått alla omskrivningsvarv och att frasen kom in i en omskrivning eller i den
sista humaniseringen, som aldrig prövades. Över 250 körningar: 194 gick alla
varv, 96 köades med kvarvarande fynd, och 60 av dem hade en tidigare version
med färre. En omskrivning kan alltså göra mejlet sämre, och kedjan behöll
ändå den sämre.

**I koden.** `run_outreach_draft_v2`: urvalet bland de humaniserade
versionerna. Kvar: omskrivningen själv skriver in nya mallord (45 av 250 har
fynd även med urvalet), och det är en promptfråga för nästa runda enligt
referensens avsnitt 8.

## 2026-10-17 (Sebbe) — Skapa om utkast skriver bara utkastet, ur sparad research

**Beslut.** "Bygg skapa om bara utkast utan ny research." Knapparna Skapa
utkast och Skapa om utkast i Iris-listan skriver nu ett nytt mejl ur leadets
sparade research i stället för att köra hela kedjan igen.

**Resonemang.** Öppen punkt i utkastreferensen (avsnitt 8.5 och 9): när 104
utkast skrevs om med Skapa om 2026-10-16 researchades bolagen om, och 23 föll
till nivå C på en ny bedömning av ett bolag som redan var godkänt. En
omskrivning av mejlet ska inte kunna ändra bedömningen, och den ska inte
betala för sidhämtning och research en gång till.

**I koden.** `scope="utkast"` på `POST /api/leads/prospects/processa-om`.
Underlaget läses av `app/leads/sparad_research.py` ur bolagets senaste
`leads_research`-körning: posten `underlag:utkast` som researchsteget skriver
sedan i dag, annars (äldre körningar) ur stegets utdata med citaten
verifierade mot källmaterialet i samma logg. Bedömningen läses ur
prospektraden och skrivs aldrig om; ett bolag utan sparad research får hela
kedjan som förut. Raden visar "Skriver utkast…" medan jobbet går, och skälet
står kvar på raden om inget utkast blev av (liggarens `error`). Processa om i
registret och kontaktjakten kör fortfarande full research.
`scripts/omskriv_utkast.py` skriver bara utkasten som standard
(`--med-research` för den gamla vägen). Ingen migration.

## 2026-10-17 (Anton) — Nivån från 2026-10-16 låses som referens

**Beslut.** "Lås in detta på samma sätt som tidigare i projektdokumentationen,
i en separat fil med exempel på outputen och exakt vad som ändrades från den
tidigare versionen och varför, se till att referera till det för nya frågor
kring output och utkast."

**I koden.** `docs/UTKASTKEDJAN-REFERENS-2026-10-16.md` är gällande referens
(den från 2026-10-12 står kvar som historik och pekar dit). Sju verkliga utkast
är facit i `tests/leads/fixtures/utkastfacit_2026-10-16.json`, låst av
INV-LEADS-UTKAST-002. Projektets CLAUDE.md och skrivstilens huvud pekar på
referensen för varje fråga om utkastens output. I samma ändring: "Hej
Brobergs," (bolagets första ord som förnamn) ger nu "Hej,".

## 2026-10-16 (Claude, på Antons beställning) — Utkasten skrivs med gemini-2.5-pro

**Beslut.** Utkast- och humanizerstegen i Iris kedja körs på `gemini-2.5-pro`
i Vertex `europe-west1` i development (`LEADS_DRAFT_MODEL`,
`LEADS_HUMANIZER_MODEL`). Research, Jev och övriga steg kör kvar på
`gemini-2.5-flash`.

**Resonemang.** Antons krav 2026-10-15: utkasten ska ligga på Christoffer-nivån
"HELA tiden". Med flash föll ingångarna tillbaka i nya mallord ("är ert löfte,
men … tar tid från det arbetet") även efter grindens två omskrivningsvarv; med
pro blev ingångarna konkreta och skrivna till bolaget. Kostnaden är ungefär
fyra gånger flash per utkaststeg och 5–8 minuter per utkast.

**Inte gjort, Antons beslut:** de nyare modellerna (`gemini-3.1-pro-preview`,
`gemini-3.8-flash`) finns bara på Vertex globala endpoint, inte i
`europe-west1`. Att flytta behandlingen ut ur EU-regionen är en
dataskyddsfråga och görs inte utan Anton. Main har inte fått modellbytet.

## 2026-10-15 (Claude, på Antons beställning) — Registret hämtas från allabolag; körningen ger inte upp under beställt antal

**Beslut.** Iris-körningar och listor ska leverera beställt antal. Registrets
sidor hämtas därför från allabolag.se, direkt och utan ScrapeGraph; urvalet
(kontroll, Jev, kontaktsökning, fördelning, listspår) är detsamma.

**Resonemang.** ScrapeGraph-kontot har en kredit kvar (gratisplanen slut,
verifierat 2026-10-15) och merinfo blockerar direkthämtning, så varje list- och
bolagssida föll och körningarna slutade på 4 och 8 leads av 50. allabolags
sökresultatsida går att hämta direkt och bär allt urvalet läser. Samma
affärsbeslut som för merinfo gäller: hövlig hämtning tills ett API-avtal finns
(prisförfrågan till allabolag).

**I koden.** `sources/allabolag.py` (sökning, geofilter, tolkning, cache),
vald i `merinfo.sok` med `LEADS_REGISTER` (osatt = allabolag när
`LEADS_MERINFO=scrapegraph`). Taken höjda för allabolag (600 bolag, 40 sidor per
sökning), kredittaket stoppar inte registret. Registret är fortfarande ett
filter: sökträffens kontaktperson blir aldrig en kontakt, och
ensam-VD-undantaget (regel 7) gäller inte allabolag-rader eftersom en sökträff
bara visar en person.

Antons beställning samma dag: "vi slutar inte förrän vi levererat det beställda
antalet PROCESSADE leads … var noga med att inte generera dubletter eller att
alla agenter söker igenom samma företag … de ska sorteras bort som bortvalda
och periodiskt blandas in". Därför också: körningen granskar upp till 12 bolag
per beställt lead (var 4) och har så många sökrundor att de ryms (50 → 75, var
11, vilket gav högst 88 bolag); den slutar när fyra rundor i rad inte gett en
ny kandidat. Bortval ur avslutade körningar (Jev, existens, research,
storlek/bransch, inte "utanför målområdet") står sig i 30 dagar och blandas
sedan in igen (`api/leads.py:_nyligen_bortvalda`). Efter första "Insufficient
credits" pausas betalda ScrapeGraph-anrop i tio minuter och räknas inte mot
taket (`sidhamtning._KREDIT_SLUT_TILL`): 350 misslyckade anrop stoppade
Göteborgskörningen. Fixturen är avidentifierad (inga personnamn, nummer eller
adresser).

Första körningen med allabolag (2026-10-15 22:00) avbröts efter några minuter:
bolag utan webbplats blev Iris-leads på registrets bolags-e-post (regel 13) och
föll i researchen på "Inget källmaterial" (9 av 11), och registrets hemsida var
ibland kedjans (giganten.se, elon.se, mio.se). Därför kräver Iris nu en
webbplats (regel 10; bolaget går annars till listspåret som "Utan webbplats"),
och en hemsida vars domän inte bär bolagets namn måste ha namnet på startsidan.

## 2026-10-15 (Anton) — Utkasten tillbaka till Christoffer-nivån; inga bolagsnamn i ämnesraden

**Beslut.** "Det första utkastet med Christoffer var det bästa (även om
ämnesraden var ren smörja) och det är den nivån och anpassningen jag förväntar
mig." Ämnesraden nämner INTE bolagets namn. Hälsningen får inte bära fel namn
("jag tror inte han som har Åkes Motor heter Delsbo"). Kvaliteten ska ligga på
den nivån hela tiden och bli bättre.

**Resonemang (Anton).** "Nu har du bytt ut 'för företag som ert' eller 'som ni
gör' till 'med er/ert/era', 'när ni', till en generisk upprabbling av deras
verksamhet, samt pinsamma ämnesrader." Båtladan-utkastet ("Hur hinner du med
att ge personlig rådgivning och service genom hela processen, från köp till
underhåll, när kundfrågorna om båtar, motorer och trailers blir många?") tar
det bolaget lovar sina kunder och ställer det mot momentet agenten löser; de
andra räknade upp sortimentet.

**I koden.** Ingången bygger på bolagets löfte (skrivstilen omgång 6,
grundmallen, personaliseringssteget, fyra nya ingångsformer utan "Med er",
"Ni" och "Era"). Stilgrinden fäller `slentrian_ingang`, `uppraknad_ingang`,
`kopierat_exempel` (fyra särskiljande ord i rad ur skrivstilens exempel),
`du_och_ni`, `agent_efter_loftet` och i ämnesraden `namn_i_amnet`,
`produkt_i_amnet`, `samma_amne`, `langt_amne`; fynden ger en omskrivning före
humanizern. `tilltal.amne_utan_namn` lyfter ut namnet som sista nät.
Förnamnet väljs mot mejladressen (`halsning.fornamn`: "Delsbo Magnus" med
magnus@ blir Magnus). Facit reviderat: Båtladan in, sex ut till `ersatta`
(Med er-öppning, uppräkning, eller agenten nämnd först efter löftet), och
ämnesraderna borttagna ur facit eftersom alla bar namnet.

## 2026-10-12 (Anton) — Utkasten är perfekta: kedjan låses som referens

*Delvis ersatt 2026-10-15: facit reviderat och ämnesraden utan bolagsnamn (se ovan).*

**Beslut.** "Alla utkast är perfekta nu, lås in detta och dokumentera exakta
upplägget, strukturen och vad du ändrade för att komma hit, lägg det i
projektmappen som referens för utkastsförbättring."

**I koden.** Tolv verkliga utkast ur Snajps granskningskö är facit
(`snajp-support/tests/leads/fixtures/utkastfacit_2026-10-12.json`), låsta av
INV-LEADS-UTKAST-001 (`tests/leads/test_utkastfacit_2026_10_12.py`): varje
facitutkast passerar stilgrinden, har ingången i andra person utan "man",
erbjudandet kvar och en handling sist; facitutkasten börjar olika; de
utpekade felen fälls fortfarande. Referensen med kedjan steg för steg,
strukturen, fel/rätt-tabellen, ändringarna och arbetsgången för vidare
förbättring: `docs/UTKASTKEDJAN-REFERENS.md`. Facitet ändras bara när Anton
godkänt nya referenser.

## 2026-10-12 (Anton) — Första utkastet ska vara det personliga, säljande utkastet; Tillbaka till Iris skriver inte om

**Beslut.** Utkastkedjan ska ge referenskvaliteten på första försöket för
varje lead: en ingång som bygger på en förståelse av verksamheten, inte på
uppräknade fakta som antal anställda och inte på samma mallfras för alla;
erbjudandet intakt; varken för kortfattat eller opersonligt. "Flytta
tillbaka" till Iris ska inte automatiskt skriva om leadsen, och alla tak på
antal markerade rader i listorna tas bort.

**Resonemang (Anton).** Två utkastkedjor följdes steg för steg (Fiskebäck
Byggservice, Härlanda Fog & Byggservice). Det platta första utkastet rabblade
registerfakta ("Med fem platschefer … är jag säker på att") eller öppnade med
"För företag som ert, som …": samma uppbyggnad för alla, opersonligt och
spammigt. Personalisera blev mer personligt men mindre säljande och tappade
erbjudandet. Förbättra blev kortare och rakare med kärnerbjudandet kvar, men
opersonligt. Först en andra Personalisera landade: det starka erbjudandet kvar
och en rimlig personalisering byggd enbart på en förståelse för verksamheten.
De ingångar som känns skrivna för varje bolag är byggda på något ur bolagets
egna ord och är inte byggda likadant. Flytta tillbaka ska inte processa om
alla; det är upp till användaren vad han vill göra, och ett tak på 50 (eller
något annat tak) hör inte hemma i någon lista.

**I koden.** Ingångens mallfraser är borta ur skrivstilen
(`agent-core/prompts/leads-skrivstil.md`, omgång 4) och grundmallen
(`leads-systemprompt.md` § 10.2); ingången bygger på en egenskap ur citaten,
och körningens redan använda ingångar läggs i ärendet. Stilgrinden
(`app/leads/stilkontroll.py`) fäller mallingång, siffror i ingången,
antaganden om mottagaren, tappat erbjudande (villkorens siffror och
produktens namn) och samma konstruktion som ett annat mejl, och
`run_outreach_draft_v2` skriver om en gång före humanizern när något fälls.
`POST /api/leads/queue/tillbaka-till-iris` avbryter bara utkasten; de
request-scheman som bar `max_length` (tillbaka till Iris, schemalägg,
processa om, flytt till main, massåtgärder) har inget tak, och
granskningskön hämtar upp till 1000 poster. Produktnamnets kortform ("Iris")
räknas som träff i produktmatchningen.

*Att veta (agenten):* de 27 av 100 Snajp-leads som saknade utkast efter
omkörningen 2026-10-11 föll i researchen som nivå C: 21 på produktmatchningen
("ingen av kundens produkter passar" eller "behovet kunde inte beläggas med
ett citat") och 6 på kriterierna om B2B- respektive B2C-kunder. Före
omkörningen var de nivå B, bara för att produktgrinden då inte såg
produktlistan.

*Utfallet 2026-10-12 (agenten):* omkörningen genom den nya kedjan gav 92 av
100 nya utkast i granskningskön (de 73 gamla godkända avbröts, inget skickat).
Två fel på vägen rättades i samma natt: profilen kompilerades om till tre
produktbundna måste-kriterier (ett bundet kriterium gäller nu bara den valda
produkten), och ett uppfyllt bundet kriterium härleder produkten när modellen
lämnar fältet tomt. Åtta faller fortfarande som nivå C efter tre försök: DS
Flexhal, Nyströms Byggtjänst, Solega, Z Marktjänst (B2B för Iris ej styrkt
med citat), Fiive, SafeTeam (B2C för Supportagenten ej styrkt), Simmis (behov
utan citat) och STINAB (modellen uteslöt bolaget som offentlig sektor fast
det bygger åt offentlig sektor). Anton avgör: lämna, Processa om, eller mjuka
upp profilens produktbundna kriterier till bör. `LEADS_DAILY_TOKEN_BUDGET` på
api i development höjdes 8 M → 32 M för natten och står kvar tills Anton
återställer den. Uppföljning: garanti- och pilotmejlen bör namnge agenten i
stycke 2 före löftet, och du/ni-blandning ska fällas av stilgrinden.

*Tillägg samma förmiddag (Anton):* "som ni gör", "som ert" och "för företag
som ert" stod kvar i nästan varje ingång; de ska anpassas på riktigt som i
referenserna, direkt i kedjan, så som en extra runda Personalisera gjorde.
**Resonemanget:** grinden fångade bara "För företag som ert" i meningens
början, och modellen skrev en allmän "när man …"-mening om branschen och
hängde på etiketten. De goda ingångarna är skrivna till mottagaren i andra
person om det som står på deras sajt. **I koden (`dda1531`):** stilgrinden
fäller etiketterna var de än står i ingången och allmänna ingångar ("man",
"den som", "ett företag som"); kedjan har ett obligatoriskt
personaliseringssteg som skriver om enbart ingången i andra person med en
detalj ur citaten, före humanizern; ingångsformerna, skrivstilen och
grundmallen säger detsamma. **Utfall:** alla 100 omkörda; 20 var redan
godkända och skickade 08:34 i den gamla stilen; 76 av de 80 övriga har nya
utkast utan etikett eller "man" i ingången; 4 faller på hårda kriterier (DS
Flexhal, Nyströms Byggtjänst, Z Marktjänst, SafeTeam). Budgeten i
development står på 48 M.

## 2026-10-10 (Anton) — Org.nr stoppar inte utskick; utskick går från development

**Beslut.** Tvåvägssynken gäller bara körningar och ärenden i databasen;
funktioner och andra ändringar stannar i development tills de pushas. Syftet är
att pålitligt kunna testa nya funktioner mot samma data. Org.nr-regeln får inte
blockera utskick, och det måste gå att skicka utskick från development också.

**I koden.** Regel 1 kräver bara företagsnamnet i sidfoten; org.nr och
postadress tas med när kundregistret har dem (`leads_tools.lagstadgad_fot`,
`utskicksfot.bygg_fot`). Varje godkänt utkast bär miljön där det godkändes
(`gate_checks.godkand_i`) och skickas bara därifrån (`scheduler.skickas_har`),
så att synken aldrig ger ett dubbelutskick. Äldre godkännanden utan miljö och
autonoma utskick skickas av main. Uppföljningssvepet, inkorgsläsningen och
autopiloten körs bara i main.

*Att veta (agenten):* e-handelslagen kräver organisationsnummer i
information från en näringsidkare. Ett utskick utan org.nr går nu ut; regeln
kräver det inte längre.

## 2026-10-10 (Anton) — Tvåvägssynk mellan development och main

*Ersatt 2026-10-17: main är sanningen efter första synken (se ovan).*

**Beslut.** Slå på och testa utskicken även i main. Allt speglas utom
specifika testkörningar, markerade som Provkörningar, som går att flytta över
till main. Alla övriga körningar och supportärenden speglas åt båda hållen med
det senaste tillägget som sanning. Vid första synken ska development vara
sanningen.

**Resonemang (Anton).** Det är en ändring från tidigare men en nödvändig sådan
för att kunna testa pålitligt.

**Fynd när beslutet genomfördes.** Den nattliga envägsspeglingen hade inte
speglat något sedan 2026-10-04: development låg på migration 110 och main på
102, skriptet avbröt, och GitHub visade grönt eftersom `tee` dolde felkoden.
Miljöerna hade glidit isär i sex dygn. Main hade under tiden fått produktions-
data som development saknade (15 kundmejl, 6 ärenden, 7 prospekt).

**I koden.** `scripts/railway_synk.py` (var tionde minut, `.github/workflows/
synk.yml`), migration 111 (`synk_andrad_at` och `synk_raderingar`).
*Agentens tolkning av "development är sanningen":* vid första synken vinner
development varje rad som finns i båda och skiljer sig, och allt som bara finns
i development kopieras till main. Det som bara finns i main raderas inte utan
kopieras till development, eftersom det är kundmejl och ärenden som annars
hade gått förlorade. En kopia av varje synkad tabell sparas före första synken.
Uppföljningar, inkorgsläsning och autopilot sker bara i main; utskick i den
miljö där utkastet godkändes (se beslutet ovan).

## 2026-10-10 (Anton) — Listornas leads stannar i listan; Flytta till Iris tas bort

**Beslut.** Alla leads från listor stannar i sina listor. Varje rad går att
klicka på och öppnar samma information och utkast som ett Iris-lead, med exakt
samma upplevelse. Knappen Flytta till Iris tas bort helt; kvar finns Processa om
och Skapa utkast, och båda går att köra på enskilda markerade rader eller alla.

**Resonemang (Anton).** Vår styrka är att alltid leverera högkvalitativa leads
och utkast. Även om listformatet låter användaren generera utkast för flera
hundra leads på en gång ska alla anpassas på exakt samma sätt som vanliga
Iris-leads. Flytta till Iris skulle göra Iris överfull och svårnavigerad, och
fungerade bara som ett stopp mellan ännu en utkastgranskning och utskicket.

**I koden.** Migration 110: `lead_list_items.prospect_id` kopplar raden till ett
bakgrundsprospekt (detaljvyn, researchen och utkastet går genom det), och
Iris-tabellen visar inte listkopplade prospekt (`GET /api/leads/prospects`).
`POST /api/leads/listor/{id}/utkast` kör samma research och utkast som Iris
(en körning med `kalla='lista'`, syns i Körningar). `till-iris` är borttagen.
De generella listutkasten (Sebbe 2026-10-07, `app/leads/listutkast.py`)
ersätts av detta.

## 2026-10-10 (Anton) — Processa om är en noggrannare omsökning

**Beslut.** Processa om anpassar en färdig lista, från en misslyckad körning
eller en annan användare, där leadsen ofta har bristfällig information. Den gör
om informationshämtningen i en noggrannare sökning och sveper bara källor som
förra agenten inte använde, så att så många källor som möjligt täcks. Hos
Alunix och Umeå Webbdesign hämtar Processa om även webbplatsinformationen på
nytt och förbereder underlag för utkast med erbjudande om hemsidor.

**Resonemang (Anton).** Det finns alltid kontaktinformation, det gäller bara
att leta tillräckligt. 200 bolag i dag blev ej kvalificerade och lämnades på
bordet för att de saknade hemsida eller lättillgänglig kontaktinformation.

**I koden.** `app/leads/omprova.py:sok` med källorna register, katalog
(hitta.se), webbplats och webbuppslag; prövade källor sparas i
`lead_list_items.kallor` (migration 110). Webbyråerna: `webbpool.bedom_en`.
Raderna uppdateras på plats, inget flyttas.

## 2026-10-10 (Anton) — Varje funktion har ett sätt att följa flödet

**Beslut.** Bygg alltid ett sätt att följa flödet för varje funktion. Fråga
alltid om det ska vara synligt för kund när det är tveksamt.

**Resonemang (Anton).** Processa om visade bara ett meddelande om att listan
processades, men det fanns inget sätt att följa aktiviteten eller veta om det
lyckades. Det ska lösas enkelt och tydligt i den befintliga miljön, inte i
ytterligare en flik om det inte är absolut nödvändigt.

**I koden.** `lead_lists.processering` (migration 110) bär förloppet för
Processa om och Skapa utkast och visas i listan, även efter en omladdning.
Regeln står i projektets CLAUDE.md.

## 2026-10-10 (Anton) — Kontaktuppgifter ur företagskatalogerna

**Beslut.** Leta i fler källor innan ett bolag blir ej kvalificerat. Hitta.se
och Eniro är där de flesta bolag fyller i sina uppgifter.

**Resonemang (Anton).** Norrtech i Skellefteå AB och Örnbergs Plåtslageri blev
"Inget kontaktsätt" respektive "Ingen namngiven VD" fast telefon, e-post och
webbplats stod öppet i katalogen och i Googles sammanfattning.

**I koden.** `app/leads/katalog.py`: hitta.se slås upp på org.nr (gratis, en
förfrågan per bolag) före webbplatsvalet i körningen och i Processa om.
Katalogens e-post är bolagsnivå (regel 13) och ger också webbplatsen via
domänen. Katalogens telefon räknas som bolagets publicerade nummer, som
sajtens, och kräver därför ingen VD i registret (`merinfo.fordela`).

*Bekräftat av Anton 2026-10-10:* regel 15 krävde en namngiven VD för
registrets nummer. Ett nummer bolaget själv publicerar i katalogen räknas som
sajtens nummer och kräver ingen VD. Så hamnar Örnbergs (070-numret, ingen VD i
registret) på ringlistan.

*Eniro:* inte inkopplad. Eniro svarar 403 på en ärlig bot-identitet och visar
numret först efter ett klick ("Visa nummer"); via ScrapeGraph kom varken
telefon eller e-post med. Vi maskerar oss inte som webbläsare.

*Gemini med Google-sökning och URL-kontext* provades för kontaktuppgifter
(Vertex, EU-regioner): 2.5-flash bytte till ett annat bolag när det sökta inte
hittades, 2.5-pro och 3.6-flash (3.6 finns bara på Vertex globala ändpunkt,
utanför EU-regionerna) gav inga träffar. För bolagshändelser och nyheter gav
2.5-flash användbara svar med länkar på bolagets egen sajt, men utan
sökkällor och med gissade datum: varje händelse måste styrkas genom att länken
hämtas innan den används.

## 2026-10-10 (Anton) — Iris sköter leads helt automatiskt inom kontots spärr

**Beslut.** Automatiseringen av leadskörningar, utkast, uppföljning och svar på
mejl ska slås på och skötas helt automatiskt av Iris, utifrån spärren som är
satt i kontot (första utkast, första mejl eller till bokat möte).

**Läget när beslutet togs (uppmätt i Railway och databasen 2026-10-10).**
Svaren hanteras redan automatiskt (inkorgen läses var femte minut i båda
miljöerna). Uppföljningar skrivs automatiskt men alltid som utkast till
granskning. Inget skickades av sig självt: `SEND_QUEUE_POLL_SECONDS` var inte
satt i någon miljö, så spärren avgjorde ingenting. Schemalagda leadskörningar
fanns inte. Bara kontot Snajp hade en spärr satt (`meeting`, till bokat möte,
som i koden beter sig som första mejl eftersom ett bokat möte kräver
överlämning); övriga stod på standard (utkast).

**I koden.** `app/leads/autopilot.py`: en Iris-körning per vardag från 06:00
med kundens `automation.autopilot.leads_per_dag` (standard 10, tak 50), när
både miljöns `LEADS_AUTOPILOT=1` och kundens `automation.autopilot.pa` är på.

*Väntar på Antons ja (agentens avgränsning):* att slå på `LEADS_AUTOPILOT`
och `SEND_QUEUE_POLL_SECONDS` i main. Development är en spegel med riktiga
kunders data och ska inte skicka mejl på egen hand till riktiga bolag; där
slås bara körningarna på, så att flödet går att följa utan utskick.

## 2026-10-10 (Anton) — Köade mejl kan skickas tidigare eller flyttas

**Beslut.** Det ska gå att markera och manuellt skicka mejl tidigare, eller
ändra den schemalagda tiden för ett eller flera mejl i kön utan att ändra
standarden.

**I koden.** Skicka nu går samma väg som Godkänn och skicka. Ändra tid:
`POST /api/leads/queue/schemalagg`; en vald tid utanför sändfönstret (vardagar
08–16) går ut när fönstret öppnar.

*Antons svar 2026-10-10:* "Gå direkt. Vanliga funktionen för att skicka
utkasten går via kön, men från kön kan man välja att skicka direkt." Skicka nu
(`POST /api/leads/queue/{id}/skicka-nu`) går därför förbi tidsgrinden och
regel 5a (kontorstid). Språkgrinden, suppression, karens, volymtak och
avsändaruppgifterna gäller fortfarande. Godkänn och skicka följer fönstret.
