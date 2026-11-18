# Kodskanningens 61 larm — triage 2026-11-17/18

Repo: oloflun/snipe-leads, analys av development @ 981dd90f. Gren: compliance/kodskanning
(bygger på compliance/2026-11-17, PR #45). Lokal fil, inte i repot: här står varför ett
larm är verkligt och hur det hade kunnat utnyttjas.

Klasser: (a) verkligt, (b) låg risk men rättat, (c) falskt larm, (L) löst av PR #45.

## (a) Verkliga

### #41 py/stack-trace-exposure — snajp-support/app/main.py:620 (/health/ready)
`/health/ready` är öppen utan nyckel (hälsokontroll för Railway). När lagringen inte
svarade lades `str(error)` från databasdrivrutinen i `warnings` och returnerades.
asyncpg/psycopg-fel bär typiskt värdnamn (Railways interna namn), IP, port, databas-
och användarnamn ("password authentication failed for user …"). Den som pollar
endpointen under ett databasavbrott får alltså en karta över det interna nätet och
kontonamnet. Inget lösenord i normala felformer, och bara när databasen är nere.
Rättning: texten till serverloggen, bara feltypen i svaret. Test:
`tests/test_health.py::test_readiness_lamnar_inte_ut_lagringens_feltext`.
Exponering: ja i princip, om någon pollat under ett avbrott. Inga personuppgifter,
ingen hemlighet; infrastrukturnamn. Ägaren bedömer om det räknas som incident
(troligen inte; ingen personuppgift).

## (b) Låg risk, rättat

### #28, #29 js/insecure-randomness — components/snajp/SupportChat.tsx (källa lib/sessionslagring.ts)
Chattens sessions-id är en bärarnyckel: `/api/chat/samtal` lämnar ut hela samtalet
(även medarbetarens svar) till den som vet id:t (`<id>@session.snajp.se`).
Huvudvägen är `crypto.randomUUID` (122 bitar). Reserven när den saknas var
`Date.now` + två `Math.random`. randomUUID saknas i en osäker kontext — och en iframe
är osäker om NÅGON förälder är http, alltså när widgeten bäddas in på en kunds
http-sajt. Math.random är inte kryptografisk men seedas per webbläsarprocess; att
gissa en annan besökares värde kräver att man känner hens generatortillstånd, så
praktiskt utnyttjande är osannolikt. Rättat ändå (nyckeln ska vara oförutsägbar):
reserven använder `crypto.getRandomValues`, som finns även i osäker kontext.
Test: `lib/sessionslagring.test.ts` (Math.random låst, randomUUID borttagen).

### ReDoS: #43, #44 (halsning.py), #46 (outreach_playbook.py), #47, #48 (signatur.py),
### #49 (text_delta.py), #50 (textkvalitet.py), #52 (tilltal.py)
Uppmätt lokalt på 10–20 000 tecken: 2–11 s per anrop, `snyggt_bolagsnamn` 89 s på
60 000 tecken (slingan tar bort en bolagsform per varv och kör uttrycken på hela
namnet varje gång). Koden är synkron i async-arbetaren, så ett anrop blockerar
eventloopen. Indata: utkast och supportsvar (modellutdata som bygger på inkommande
mejl och hämtade webbsidor, eller en kunds egen redigering) och bolagsnamn (register
eller research). Ingen av dem tar rå inkommande mejltext direkt; en utomstående
påverkar bara indirekt via modellen, vars utdata är begränsad av max-tokens. Därför
(b), inte (a). En redigerad text på tiotusentals blanksteg från en inloggad kund
kunde däremot låsa en arbetare i sekunder.
Rättningar (samma träffar som förut, visat av tester som körts mot gammal och ny kod):
- textkvalitet.py: `(?<![ \t])[ \t]+([,.!?;:])` — matchning börjar bara vid radens start.
- text_delta.py: `(?<![.!?…])` före skiljeteckensgruppen.
- outreach_playbook.py `_ANONYM_HALSNING`: `\s*(?:[,!]\s*)?$` i stället för två `\s*` runt `[,!]?`.
- signatur.py `_AVSLUTNING`: `[ \t]*(?:[,!.][ \t]*)?$` (täcker #47 och #48, samma uttryck).
- tilltal.py `_pronomen`: `rstrip` + sista tecknet i stället för `[.!?:\n]\s*$`.
- halsning.py `snyggt_bolagsnamn`: längdtak 200 tecken (efter blankstegsnormalisering)
  → `None`, alltså tilltal utan bolagsnamn. Beteendeändring bara för "namn" > 200 tecken,
  som inte är riktiga bolagsnamn. #44 (`_ORTSLED`) nås bara härifrån.
  Kodskanningen kan fortsätta flagga #43/#44 eftersom uttrycken är oförändrade.
Test: `snajp-support/tests/test_redos_texter.py` (6 tidstester föll före: 3,8–89 s; nu < 0,5 s).

### #53 py/cookie-injection — snajp-support/app/api/demo.py:52
Klientens cookie skrevs tillbaka oförändrad i Set-Cookie och blev nyckel i
processminnets sessionstak. Ingen header-injektion (Starlette citerar värdet och CR/LF
kan inte komma in via Cookie), bara spegling av godtycklig text och godtycklig
nyckellängd i minnet. Rättat: bara ett UUID godtas, annars nytt id (som en rensad
cookie). Test: `tests/api/test_demo_api.py::test_en_sessionscookie_som_inte_ar_ett_uuid_ersatts`.

### #36 py/clear-text-logging-sensitive-data — scripts/lokal_stack.py:76
Lokalt skript som skriver ut inloggningsuppgifterna för den lokala stacken. Om
`SNAJP_ADMIN_PASSWORD` var satt i miljön (Fas 0-fyndet K1: det var förut det riktiga
adminlösenordet) skrevs det ut i terminalen. Nu skrivs bara det lokala standardvärdet;
ett värde ur miljön visas som en hänvisning. Inget test (lokalt skript, tre rader).

### #1, #3, #4, #5, #6, #7 actions/missing-workflow-permissions
Repots standard för GITHUB_TOKEN är redan `read` (gh api actions/permissions/workflow),
så ingen workflow har haft skrivrätt i praktiken. Explicit `permissions: contents: read`
skyddar mot att standarden ändras. Lagt på toppnivå i synk.yml, indexnow.yml, verify.yml.
Behovet lästes ur stegen: checkout, git fetch, setup-python/node, pip/npm, upload-artifact
(använder körningens runtime-token, inte GITHUB_TOKEN). Inget skript anropar GitHubs API.
synk.yml rör produktionsdata via ENV_DEPLOY (inte GITHUB_TOKEN); `contents: read` räcker
för checkout. migrera.yml har redan `permissions: contents: read` och larmades inte.

## (L) Löst av PR #45
- #2 keep-backend-awake.yml: filen är borttagen på compliance/2026-11-17.

## (c) Falska larm

- #8–#14 js/clear-text-logging, agent-core/skills/mk/_tools/clis/{amplitude,hunter,instantly,kit,
  mailchimp,meta-ads,similarweb}.js, och #15–#21 samma filer under
  references/marketingskills-main/tools/clis/ (byte för byte lika). Leverantörens (marketingskills)
  CLI-verktyg; körs aldrig av appen (bara textkorpus i skills-corpus.json). Nyckeln maskeras
  redan med '***' i --dry-run (URL, Authorization, api_key i kroppen); i skarpt läge skrivs
  API:ets svar ut, inte nyckeln. Mailchimps datacenter-suffix och Metas kontonummer är inte
  hemligheter. CodeQL följer smittan genom `.replace(KEY,'***')`.
- #22 scripts/test-db-connection.mjs:20: skriver lösenordets LÄNGD, inte lösenordet. Lokalt skript.
- #23 components/admin/insyn/Insynsvy.tsx:291: värdet är ett körnings-id ur en <select> och sätts
  efter den fasta sökvägen `/admin/korningar/` i en Next-Link; kan inte bli javascript:-URL eller
  HTML. Adminyta.
- #24 components/kvitton/KvittoYta.tsx:786: datumfält in i en relativ export-URL efter fast
  prefix; ingen HTML-tolkning, påverkar bara användarens egen nedladdning.
- #25 lib/db.ts:46: DATABASE_URL är betrodd driftkonfiguration; kontrollen väljer bara TLS-läge.
- #26, #27 lib/tenants/widget.test.ts, #55–#60 snajp-support/tests/…: testpåståenden
  (`includes`/`in` på förväntade strängar), ingen URL-sanering.
- #30–#34 py/clear-text-storage: scripts/create_preview_snajp_web.py, scripts/keys.py:220,
  snajp-support/evals/kor.py:84, scripts/set_preview_postgres_url.py, scripts/set_railway_token.py.
  Avsiktlig lagring i de lokala, gitignorerade nyckelfilerna (.env.deploy, snajp-support/.env,
  evals/.env*; `.gitignore:63 .env*`, keys.py kontrollerar gitignore innan skrivning). Det är
  projektets nyckellager enligt api-key-setup; inga värden skrivs ut.
- #35 scripts/keys.py:671: skriver längd och sista fyra tecknen av TYPESAFE_API_KEY — avsiktligt
  fingeravtryck för att känna igen nyckeln, lokalt skript, inte nyckeln.
- #37 scripts/web_mailvag.py:49: SHA-256 (10 hex) används som fingeravtryck för att jämföra en
  API-nyckel mellan miljöer, inte som lösenordslagring; nyckeln har hög entropi.
- #38 snajp-support/app/api/admin_flytt.py:430: bara plattformsadmin (`require_master_key` på
  routern); `str(fel)[:200]` är feltext, inget stackspår (spåret går till loggen).
- #39 chattar.py:81 och #40 kanaler.py:206: `KanalFel` är en kurerad feltyp vars texter skrivs för
  kundens medarbetare (statuskod, kanalnamn, nätvaktens besked); inget stackspår; mottagaren
  är kundens egen inloggade personal och anslutningen är kundens egen.
- #42 snajp-support/app/api/leads.py:4956: `error` kommer från `LanguageGateError` (kurerat
  språkgrindsbesked) eller fasta texter i leads_tools._queue_outreach_draft_impl.
- #45 halsning.py:166: raden längdkontrolleras (≤ 80 tecken) på raden före.
- #51 tilltal.py:40: körs på `text[:400]`; uppmätt 0,08 s på värsta fall.
- #54 snajp-support/evals/bedomning.py:22: emojiklassen med astrala tecken (U+1F300…) tolkas
  rätt av Python 3; CodeQL läser dem som surrogatpar. Evalskript, körs inte i drift.
- #61 snajp-support/app/leads/send_provider.py:209: DryRunMailer (bara när SNAJP_OUTBOX_DIR är
  satt, aldrig i drift). Filnamnet saneras med `[^A-Za-z0-9._-]` → `_` (inga snedstreck) och
  föregås av en tidsstämpel, så `..` kan inte bli ett katalogsteg.

## CI och kodskanningen på PR #49
- Körning 1 (05325c76): allt grönt utom CodeQL-kontrollen: lookbehind-rättningarna i
  text_delta.py och textkvalitet.py kändes inte igen och flaggades som nya larm.
- Körning 2 (8cc9a6b4): uttrycken omskrivna så att de alltid matchar hela raden och villkoret
  prövas efteråt; differentialtest mot gamla koden på 30 000 slumptexter vardera, 0 skillnader.
  text_delta hade också en egen kvadratisk del (förkortningskontrollen delade hela texten
  fram till varje gräns: 114 s på 20 000 korta meningar), rättad. Alla kontroller gröna.
- PR-analysen är diff-informerad (results_count 0 för python/js/actions på 8cc9a6b4): den
  säger att ändrad kod inte bär några larm, men stänger inte de gamla. Vilka som stängs syns
  först när development analyseras efter merge. Väntat: #1, #3–#7, #28, #29, #36, #41, #46–#50,
  #52, #53 (och #2 via #45). #43/#44 står troligen kvar (uttrycken oförändrade, längdtak).

## Annat
- tests/test_lagg_pa_utskicksfot.py (rotens tests/) faller lokalt på
  `TenantHistorik.__init__` saknar argument — orelaterat till den här grenen.
