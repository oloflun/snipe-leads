# Juridik — vad som är gjort och vad som är kvar

Motsvarar implementeringsplanen i `GDPR-Integritet-Rapport-Snajp.md`.
Statusen här är sanningen; planen är avsikten.

Uppdaterad 2026-08-24.

---

## Klart i kod, och verifierat

Verifierat betyder **prövat mot en körande miljö**, inte "testerna är gröna".
Den här sessionen har tre gånger sett en grön hälsokontroll ovanpå ett trasigt
system, så skillnaden står här med flit.

| Punkt | Vad som byggdes | Hur det bevisades |
|---|---|---|
| **P0.1** | Startspärr: DeepSeek får inte köras i miljöer med kunddata. `Settings.llm_provider_fault()`, enforcad i `app/main.py` och `agent/llm.py` | Deployen till development föll med `CRITICAL Startvägran:` i loggen |
| **P0.1 (2)** | Okända providernamn fäller uppstarten i stället för att tyst degradera till simuleringsläge | Regressionstest + felet reproducerat skarpt |
| **P0.1 (3)** | Ett modellnamn från fel provider fäller uppstarten | Felet reproducerat skarpt: `404 models/deepseek-v4-flash is not found` medan hälsokontrollen sa `live` |
| **P0.3** | `/integritetspolicy`, `/villkor`, `/cookies` med delat skal | Lästa i webbläsaren, lokalt och på development |
| **P0.4** | `components/marketing/Sidfot.tsx` — bolagsidentifikation och juridiska länkar | Renderad, länkarna verifierade |
| **P0.5** | Dataskyddstexten säger nu att mejltexten bearbetas av en AI-leverantör | Läst i webbläsaren |
| **P1.1** | Gallringsmekanism: [`048_gallring.sql`](../supabase/migrations/048_gallring.sql) + [`gallra.py`](../scripts/gallra.py) | Migrationen körd i development, tabell och funktion verifierade i katalogen |
| **P1.2** | [`gdpr_radera.py`](../scripts/gdpr_radera.py) — sök, registerutdrag, radering per adress | Skriptet finns; ej kört skarpt (raderar data) |
| **P1.3** | Art. 14-sidfoten byggs i **kod**, inte av modellen: [`utskicksfot.py`](../snajp-support/app/leads/utskicksfot.py) | Test kör `send_guard` på det foten producerar |
| **P1.3 (2)** | Avregistreringslänken fungerar hela vägen | **Klickad skarpt på development:** token → sida → server action → `avregistrerad`, och `redan_avregistrerad` vid andra klicket. Testraderna städade |
| **P1.4** | Åtkomstskyddet mätt, och indexeringsluckan stängd | Se nedan |
| **P1.5** | [`INCIDENT_RESPONSE.md`](../INCIDENT_RESPONSE.md) | — |
| **P2** | [Registerförteckning](registerforteckning.md), [DPIA](dpia_supportagenten.md), [intresseavvägning](intresseavvagning_kallmejl.md) | Utkast, ska läsas av jurist |

### P1.4 i detalj — mätt, inte antaget

Oinloggad mot `web-development-6c85.up.railway.app`:

```
/                           200   (marknadssidan — ska vara publik)
/dashboard                  307 -> /login
/settings                   307 -> /login
/admin/kunder               404   (fail-closed)
/api/snajp-support/tickets  401
```

**Kunddata är alltså inte nåbar utan inloggning.** Appens egen grind håller,
och det är den substantiella frågan.

Men Vercels SSO skyddade en sak till, och den ersättningen saknades: dev-miljön
hade **ingen robots.txt alls och ingen `X-Robots-Tag`**. En fullständig spegel
av säljsajten — med en inloggning som leder till riktig kunddata — låg fritt
indexerbar. Åtgärdat med [`app/robots.ts`](../app/robots.ts) och en
`noindex`-tagg i [`app/layout.tsx`](../app/layout.tsx), båda styrda av
[`lib/miljo.ts`](../lib/miljo.ts). De hör ihop: robots.txt hindrar ny
indexering, `noindex` tar bort det som redan hunnit in.

Båda riktningarna är provade: okänd miljö ger `Disallow: /` och
`noindex, nofollow`; `RAILWAY_ENVIRONMENT_NAME=main` ger `Allow: /` och ingen
noindex-tagg. Den andra riktningen är den farliga — en spärr som råkar
av-indexera produktionen vore värre än den lucka den lagar.

### Buggar som hittades genom att köra skarpt

Två fel som inget test fångade, eftersom båda krävde riktig data:

1. **`avregistrera_via_token` reste ett undantag** för en tenant utan
   arbetsyta. Mottagaren hade fått "Något gick fel" och stått kvar i
   utskickslistan.
2. **`add_suppression` skrev tyst noll rader** i samma läge — en
   `insert ... select` utan träffar. Ingen krasch, ingen avregistrering.
   Kommentaren på plats påstod att en saknad arbetsyta vore "ett riktigt fel";
   den var värre än så, den var ingenting alls.

Båda rättade i [`049`](../supabase/migrations/049_avregistrering_utan_arbetsyta.sql).
`suppressions.workspace_id` är nullbar sedan dess — skyddet läses via
`tenant_id`, så en NULL döljer raden i dashboarden men inte för spärren.

---

## Kvar — kräver dig

### P0.1c · Gemini-nyckeln ligger på gratisnivån  🔴 BLOCKERANDE

**AVGJORD 2026-08-24 kväll. Inga indicier kvar — Google svarar rakt ut.**

Hela felet ur produktionsloggen:

```
quotaId:     GenerateRequestsPerDayPerProjectPerModel-FreeTier
quotaMetric: generativelanguage.googleapis.com/generate_content_free_tier_requests
quotaValue:  20
model:       gemini-3.6-flash
status:      RESOURCE_EXHAUSTED
```

`FreeTier` i kvot-id:t, och **tjugo anrop per dygn** per projekt och modell.
Det stämmer med vad kodbasen själv säger om nyckeln ("vald för gratisnivån",
se `config.py` och `scripts/keys.py`).

Dagens handfull demo-anrop åt upp hela dygnsransonen för BÅDA miljöerna,
eftersom de delar nyckel.

**Två följder, båda allvarliga.**

*Juridiskt:* gratisnivån tillåter Google att använda det som skickas in för att
förbättra sina produkter, inklusive mänsklig granskning. Riktiga kundmejl går
dit sedan produktionen lagades i kväll. Det är en behandling vi varken har
avtalat om eller informerat kunden om — och till skillnad från DeepSeek-läget,
där grunden saknades för en överföring, har vi här aktivt lämnat bort
innehållet.

*Operativt:* produktionen kommer att svara 429 under all verklig belastning.
En agent som slår i kvoten mitt i en arbetsdag är ingen produkt.

**Dessutom: `GEMINI_API_KEY` är SAMMA nyckel i main och development.** Alltså
samma kvot. Dev-trafik bränner produktionens tak, och en provkörning i dev kan
ta ner produktionen. Repot varnar redan för precis det här mönstret — se
`PER_ENV_SECRETS` i `scripts/railway_provision.py`, där kommentaren kallar en
delad hemlighet "tyst korskoppling". `GEMINI_API_KEY` står inte med i den
listan och borde göra det.

**Åtgärd, i ordning:**

1. Bekräfta nivån i Google Cloud-konsolen.
2. Aktivera fakturering på Google-projektet, eller byt provider. Betald nivå
   respektive Vertex AI ger normalt ett åtagande om att innehållet inte
   används för produktförbättring — gratisnivån gör det inte.
3. Skaffa en EGEN nyckel per miljö. Samma nyckel i två miljöer är en
   korskoppling oavsett vad den kostar.
4. Teckna DPA med Google för den nivån, och fastställ dataregion och
   överföringsmekanism (DPF eller SCC).

Växlingen till en annan provider är ett kommando när nyckeln finns:

```bash
python scripts/llm_provider.py --satt openai --apply
```

Tills detta är löst säger `/integritetspolicy` **inte** att leverantören "inte
tränar på texten". Det påståendet togs bort, och det ska inte skrivas tillbaka
förrän avtalet säger det.

**PAUSEN HÄVDES, UTAN ATT ÅTGÄRDSLISTAN NEDAN GENOMFÖRDES (upptäckt 2026-08-26).**
`main` sattes till simuleringsläge 2026-08-24 23:5x av just det skälet som står
ovan. Mätt igen 2026-08-26: **både `main` och `development` svarar `mode: live`.**
`GEMINI_API_KEY` delas fortfarande mellan miljöerna. Kvoten är fortfarande
FreeTier (`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, 6 anrop/minut
— en betald nivå har inte den kvotklassen). Ingen av de fyra åtgärderna nedan
(bekräfta nivå, aktivera fakturering/byt provider, egen nyckel per miljö, DPA)
är genomförd. Vem som körde om `--satt gemini` och när är inte känt — bara att
det skedde mellan 24:e kvällen och 26:e. Riktiga kundmejl går just nu till
gratisnivån igen. Spårat som `snipe-a1c`, flaggat till Anton direkt.

```bash
python scripts/llm_provider.py --env main --pausa --apply
```

pausar igen, om det beslutet tas innan åtgärdslistan är klar.

`GEMINI_API_KEY` är orörd — den driver även embeddings och bildbeskrivning,
som inte är chattanrop och inte omfattas av dygnskvoten.

Fyll i `region` för Google i [`lib/bolag.ts`](../lib/bolag.ts) och i
[registerförteckningen](registerforteckning.md) när svaret finns.

### P0.1d · Produktionen svarade kunder med regelmotorn  ✅ ÅTGÄRDAD

Produktionen körde `mode: simulation` — riktiga kunder fick den deterministiska
regelmotorns svar i stället för agentens, medan `/health/ready` rapporterade
`status: ok`.

**Rättat med en kirurgisk hotfix**, inte med en full merge. Produktionen
deployar från grenen `railway-main` (inte `main`, som är den döda
Vercel-grenen — se [`RAILWAY.md`](../RAILWAY.md)), och den låg 37 commits efter
`development`. Att skicka alla 37 för att laga en tom nyckel hade varit fel
växling.

Hotfixen är `78c900e` på `railway-main`, 39 rader i två filer:

- `active_llm_key` blir en uppslagskarta med `gemini` i. Fallbacken till en tom
  sträng är **behållen med flit** — den gör att en felkonfiguration syns som
  simuleringsläge i stället för att tyst gå till fel leverantör.
- `_resolve_base_url` pekar `gemini` på Geminis endpoint.
- `gpt`-defaulten skrivs om till vision-sidovagnens modellnamn när providern är
  gemini.

745 tester gröna på produktionsgrenen med patchen. Railway-variablerna står på
`LLM_PROVIDER=gemini`, `MODEL=gemini-3.6-flash`.

**Det som INTE följde med** och som kommer med nästa riktiga deploy:
uppstartsspärrarna mot okänd provider och fel modellfamilj, de juridiska
sidorna, avregistreringskedjan, gallringen. Produktionen bär alltså i dag
rättningen men inte skydden.

Rullas tillbaka med `git revert 78c900e` på `railway-main`.

### P0.2b · Den gamla Render-stacken lever och kör DeepSeek  🔴 AKUT

**Uppmätt 2026-08-24, inte antaget.** `CLAUDE.md` beskriver Vercel + Render +
Supabase som den gamla, döda stacken. Render-delen är inte död:

| Tjänst | Gren | Status | Startlogg |
|---|---|---|---|
| `snajp-support` | `main` | Live, ej suspenderad | `provider=deepseek, modell=deepseek-v4-flash` |
| `snajp-support-dev` | `development` | Live, ej suspenderad | `provider=deepseek, modell=deepseek-v4-flash` |

Båda svarar `{"storage":"postgres","mode":"live"}`, alltså kopplade till en
riktig databas med en fungerande DeepSeek-nyckel. Båda har `autoDeploy: yes`
— **varje push till `main` eller `development` deployar dit**, inklusive
dagens.

Ingen Postgres finns i Render-kontot, så databasen är någon annanstans. Vilken
går inte att läsa ur API:t, och jag gissar inte.

Ingen trafik och ingen inkorgspollning syns i loggarna de senaste tre dygnen.
Det är svagt bevis — request-loggar kan saknas på gratisplanen — så läs det som
"ingen aktivitet upptäckt", inte "ingen aktivitet skedde".

Notera: `snajp-support` (main) varnar **inte** för att IMAP saknas, vilket
`snajp-support-dev` gör. IMAP-uppgifter är alltså konfigurerade där.

**Följden för dataskyddsarbetet:** DeepSeek-överföringen som stoppades på
Railway i dag var aldrig stoppad överallt. Den här ytan fanns inte i någon
dokumentation, i registerförteckningen eller i min egen bedömning.

**Vad jag har gjort:**

`snajp-support/render.yaml` deklarerade `LLM_PROVIDER: deepseek` för BÅDA
tjänsterna. Det var källan — en blueprint-synk hade återställt providern även
om någon ändrat den i dashboarden. DeepSeek är borttagen därifrån, och
blueprinten deklarerar nu ingen provider alls: utan providernyckel startar
tjänsten i simuleringsläge, vilket är det enda säkra viloläget för en stack
ingen använder.

**DEEPSEEK-FLÖDET ÄR STOPPAT** (2026-08-24 23:29). `DEEPSEEK_API_KEY` är
blankad på båda tjänsterna, och båda rapporterar nu `mode: simulation`.
Bekräftat i uppstartsloggen, inte bara i hälsokontrollen:

```
snajp-support      LLM-nyckel saknas/platshållare — SIMULERINGSLÄGE aktivt.
snajp-support-dev  LLM-nyckel saknas/platshållare — SIMULERINGSLÄGE aktivt.
```

Dev-tjänsten fällde dessförinnan på uppstartsspärren, som namngav orsaken:
`DATABASE_URL pekar på en databas som inte kör på den här maskinen
(aws-1-eu-west-1.pooler.supabase.com)`.

**Det svaret krymper incidenten.** Render-stacken pratade med den GAMLA
Supabase-databasen, inte med Railway-databasen där dagens kunder ligger. Hur
mycket riktig persondata den bär är fortfarande en fråga för bedömningen —
Supabase-grenen står enligt `CLAUDE.md` i `MIGRATIONS_FAILED` — men det är en
annan och mindre fråga än "produktionens kunddata gick till Kina".

**Vad jag INTE kunde göra:**

*Stänga av tjänsterna.* Render-verktyget har varken suspend eller delete —
det finns bara i dashboarden. Tjänsterna lever alltså vidare, men i
simuleringsläge.

*Städa `LLM_PROVIDER` på produktionstjänsten.* Skrivningen stoppades av
behörighetskontrollen. Den är kosmetisk: med tom nyckel går tjänsten till
simulering oavsett vad providern heter.

**Åtgärd, i tur och ordning:**

1. Blanka `DEEPSEEK_API_KEY` på båda tjänsterna. Stoppar flödet snabbast.
2. Suspendera eller radera tjänsterna. Suspendering är reversibel och räcker.
3. Raderas de ska `snajp-support/render.yaml` bort också — en blueprint som
   ligger kvar är en tjänst som kan återuppstå.
4. Bedöm enligt [`INCIDENT_RESPONSE.md`](../INCIDENT_RESPONSE.md) om någon
   kunddata faktiskt passerade. Frågan att besvara först: vilken databas pekar
   deras `DATABASE_URL` på?

**Notera att koden redan hindrar en ÅTERKOMST.** `snajp-support-dev` deployar
från `development` och vägrar numera starta — bekräftat i loggen 23:01. Men
Render låter, precis som Railway, den gamla deployen ligga kvar när den nya
faller. Det som snurrar just nu snurrar vidare tills någon rör det.

**Spärren i koden är däremot lagad.** `har_riktig_kunddata()` grindade på
miljönamnet, med motiveringen att Railway alltid sätter
`RAILWAY_ENVIRONMENT_NAME`. Sant, och ändå fel: det antog att Railway är den
enda värden. På Render var miljönamnet tomt, alltså läste spärren det som
utveckling och släppte igenom.

Regeln keyar nu på **databasen** i stället: en fjärrdatabas betyder riktig
data, oavsett vem som kör processen. Loopback (`127.0.0.1`, `localhost`) är
undantaget, eftersom `scripts/lokal_stack.py` kör där och den stacken är tom.
Sju regressionstester, och `snajp-support-dev` kommer att vägra starta nästa
gång den deployar från `development`.

### P0.2 · Rotera den läckta Render-nyckeln

Nycklar och lösenord är undantaget i `CLAUDE.md` — jag rör dem inte.

1. Rotera nyckeln i Render.
2. Uppdatera `.env.deploy`.
3. **Bedöm om nyckeln gav åtkomst till persondata.** Om ja: kör
   [`INCIDENT_RESPONSE.md`](../INCIDENT_RESPONSE.md) punkt 2–6. Posten ligger
   redan i incidentloggen där.

### P0.3b · Fyll i bolagsuppgifterna

[`lib/bolag.ts`](../lib/bolag.ts) bär platshållare. Jag gissar inte ett
organisationsnummer — ett påhittat org.nr kan tillhöra ett annat bolag, och
jag känner inte ens till den registrerade firman.

Fyll i: `namn`, `orgnr`, `postadress`, `policyUppdaterad`, `DATASKYDD_MEJL`,
och `region` för Google och Railway i `UNDERLEVERANTORER`.

Så länge de är platshållare visar sidfoten en gul varningsruta på varje publik
sida. Den försvinner av sig själv när fälten är ifyllda.

### P0.3c · Låt en jurist läsa texterna

Gäller de tre sidorna plus [DPIA:n](dpia_supportagenten.md) och
[intresseavvägningen](intresseavvagning_kallmejl.md). Varje juridisk sida
visar en gul "Förstautkast"-ruta tills någon tar bort den i
`JuridiskSida.tsx`. Ta inte bort den innan — särskilt inte
ansvarsbegränsningen i `/villkor`, som står tom med flit.

### P0.3d · Skaffa en riktig kontaktadress

`Snajpsupport@gmail.com` duger som svarsadress men inte som ett företags enda
officiella kontaktväg på en B2B-säljsida, och inte alls som adressen dit en
registrerad skickar sin begäran. Sätt upp `integritet@snajp.se` och lägg den i
`DATASKYDD_MEJL`.

DNS går att automatisera med [`scripts/loopia_dns.py`](../scripts/loopia_dns.py),
men själva brevlådan kräver ett konto hos en mejlleverantör.

### P1.1b · Besluta retentionsperioden

Mekanismen finns, talet gör det inte — och ska inte gissas. Vanligt: 24–36
månader efter senaste aktivitet på ärendet. Ingen kund har någon policy satt
i dag, alltså gallras ingenting.

```bash
python scripts/gallra.py --env railway-main --tenant <slug> --satt-policy 730 --beslutad-av "Anton"
python scripts/gallra.py --env railway-main          # torrkörning, granska siffrorna
python scripts/gallra.py --env railway-main --apply  # först när de stämmer
```

Fyll därefter i perioden i `/integritetspolicy` (bär en platshållare), i
[registerförteckningen](registerforteckning.md) och i PUB-avtalet.

### P2 · Löpande

- **DPIA och intresseavvägning** — utkast finns, ska granskas och beslutas.
  DPIA:ns R1 är blockerad av P0.1c.
- **Kundens ansvar för autonominivån** in i villkoren (DPIA R4).
- **Textmall till kunden** för deras egen artikel 13-information (DPIA R5).
- **Maskering av personnummermönster** före modellanropet — utred (DPIA R1).
- **NextAuth/Supabase Auth-hybriden** — färre parallella auth-vägar.
- **Cookiebanner** — behövs inte i dag. Bygg den inte i förväg för en cookie
  som inte kräver den.

**Utloggningsknappen är klar** — finns i både `AppShell` och `AdminShell`.

---

## Inte gjort, och varför

- **PUB-avtalet** (`PUB-avtal-mall-Snajp.md`) — filen finns inte i repot, så
  jag har inte kunnat skriva mot den. Villkorssidan, registerförteckningen och
  DPIA:n refererar till avtalet; texten måste skrivas separat.
- **Engelska versioner av de juridiska sidorna** — medvetet utelämnade. Två
  språkversioner av ett avtal är två lydelser, och den dag de säger olika
  saker är frågan vilken som gäller.
- **`supabase/functions/generate-outreach`** — planen pekade ut den för
  art. 14-sidfoten. Den returnerar konserverad exempeltext på den döda
  Supabase-stacken; en juridisk sidfot i en attrapp hade sett ut som en åtgärd
  utan att vara en. Den riktiga vägen är `snajp-support/app/leads/`.
- **`gdpr_radera.py` körd skarpt** — skriptet raderar data, och det finns
  ingen begäran att uppfylla. Sökläget är ofarligt och kan köras när som helst.
