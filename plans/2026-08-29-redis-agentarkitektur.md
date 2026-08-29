# Redis-arkitekturen: överlevande körningar, semantisk cache, arbetsminne

**Datum:** 2026-08-29 · **Gren:** `development` · **Status:** IMPLEMENTERAD och pushad 2026-08-29 (R0–R4; R5 spärrad §8.1a, R6-sandbox väntar på kontosteg) — utfall i `../HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md`
**Strategival:** A — självbyggt på egen EU-Redis nu; managed Iris-tjänster utvärderas i sandbox
med syntetisk data och adopteras först bakom juridik-gates (§5.1).
**Spårning:** `snipe-wo0` (R0) · `snipe-lr7` (R1) · `snipe-cku` (R2) · `snipe-7mk` (R3) ·
`snipe-2xj` (R4) · `snipe-5ck` (R5, spärrad) · `snipe-952` (R6)

Systerplan: [2026-08-28-skarpa-korningar-och-produktion.md](2026-08-28-skarpa-korningar-och-produktion.md)
— produktionsspärren §8.1a där gäller oförändrat för allt i det här dokumentet.

---

## 1. Diagnosen: vad som överlever en deploy, och vad som inte gör det

| Data | Var den bor | Överlever deploy? |
|---|---|---|
| Chatthistorik | Postgres `ss_tickets`/messages (RLS; kund per syntetisk sessionsadress, [SupportChat.tsx:186](../components/snajp/SupportChat.tsx)) | **JA** — redan löst |
| Besökarens sessionsidentitet | `sessionStorage` per flik | JA (ny flik = nytt samtal, avsiktligt) |
| Jobbstatus (202+polling) | Redis `crm:job:<id>`, TTL 1 h | JA — sedan 2026-08-29 |
| **Pågående agentkörning** | `asyncio.create_task` i processen ([chat.py](../snajp-support/app/api/chat.py)) | **NEJ** — dör med processen; kunden får timeout-fel efter 5 min |
| Kundminne (fakta) | Postgres `customer_memory` (052, ADD-only, INV-MEM-001) | JA |
| Rullande samtalsförståelse | Finns inte — prompten ser max 3 ärenden/8 turer | — |

Requirements-kommentaren säger det själv: *"tappar varje pågående chattjobb vid
nästa deploy."* Jobbstore-steget 2026-08-29 räddade jobbPOSTEN, inte körningen.

Två driftfynd oavsett resten: `REDIS_URL` var `redis://` utan TLS med riktiga
kundsvar i posterna, och regionen var overifierad. Åtgärdas i Fas R0; Redis
Cloud och Resend är införda som underbiträden i `docs/JURIDIK_ATGARDER.md`
P1.2, `docs/registerforteckning.md` och `lib/bolag.ts`.

## 2. Produktdomarna (Redis Iris, lästa ur Redis egen dokumentation 2026-08-29)

Iris = managed-paraplyet på Redis Cloud: **Agent Memory**, **LangCache**,
**Context Retriever**, **Data Integration** — alla public preview, REST +
Python-SDK:er. **Vector Search** ingår i själva databasen (Redis 8 bär Query
Engine i alla databaser, även gratis-30MB:n).

| Produkt | Dom | Varför |
|---|---|---|
| **Agent Memory** (managed) | Mönstret adopteras självbyggt (R3); tjänsten bakom gates (§5.1) | Tvånivåminne + automatisk summering är exakt rätt idé. Men: preview; sessionsinnehåll skickas till en extraktions-LLM (Redis-managed eller BYOK) och Redis dokumentation säger uttryckligen att känsligt innehåll når modelleverantören även med exkluderingar ("advisory", dessutom bakom "selected accounts"); automatisk extraktion läser båda parters repliker — krockar med INV-MEM-001 (bara kundens egna utsagor). |
| **Vector Search** | JA — för svarscachen och embeddingcachen (R2). NEJ för kunskapsbasen | KB-retrieval är nyss ombyggd (hybrid RRF k=60 i Postgres, verifierad live 2026-08-27) och tar millisekunder på 30–50 artiklar; LLM-stegen tar sekunder. En andra vektorlagring = noll mätbar vinst, ny synk-/isoleringsyta (RLS finns i Postgres, inte Redis). |
| **LangCache** (managed) | Behovet är äkta och störst av allt — men byggs självt (R2); managed omprövas vid GA + publicerat pris + DPA | Attributmodellen (tenant-scoping, delete-by-attributes) är precis rätt. Men: preview, opublicerat pris, och prompttexten lämnar huset till ännu en part (tjänstens embeddings). Självbyggt med husets `embed_text()` ger samma effekt utan ny underbiträdeskedja. |
| **Context Retriever** | Ingen träffyta i dag — bevaka | Schema-först-verktyg över affärsdata via MCP. Snajps agenter har redan typade lagringsmetoder med RLS som enda datayta och KB som faktakälla. Blir relevant när agenten ska slå upp KUNDENS operativa data (orderstatus m.m.). |
| **Data Integration (RDI)** | Nej | CDC-spegling Postgres→Redis för långsamma källdatabaser. Vår Postgres är liten och snabb. |

## 3. Arkitekturbeslutet

**Postgres förblir system of record** (ärenden, meddelanden, kundminne, KB —
RLS, gallring, GDPR-radering). **Redis är tre saker och inget annat:**

1. **Hållbar körningskö** — Redis Streams + consumer group + `XAUTOCLAIM`-återtag.
2. **Hastighetslager** — tenant-skopad semantisk svarscache + embeddingcache.
3. **Arbetsminne** — rullande samtalssummering med TTL.

Allt i Redis bär TTL och tål att försvinna — rekonstruerbart ur Postgres.
Ingen kunddata får Redis som enda hem. Varje förmåga byggs som Memory+Redis-par
bakom samma protokoll (INV-STORE-mönstret), så sviten är grön utan Redis och
`fakeredis` täcker streams-logiken i CI.

```
Widget ──POST /api/chat──► API ──XADD──► Redis Stream «crm:jobb:chatt»
                            │                 │ (consumer group, N workers i processen,
                            │                 │  XAUTOCLAIM vid uppstart = överlevnad)
                            ▼                 ▼
                       jobbstatus ◄────── agentkörning
                       (Redis, 1h)   ├─ 0. semantisk svarscache (träff ⇒ klart ~0,4 s, 0 LLM-anrop)
                                     ├─ 1. embeddingcache (hash→vektor, 30 d)
                                     ├─ 2. hybrid KB-retrieval (Postgres, ORÖRD)
                                     ├─ 3. arbetsminne (rullande summering, TTL 72 h)
                                     └─ 4. 6–7-stegskedjan (ORÖRD) ──► svar ⇒ ev. cache-store
```

## 4. Nya invarianter

* **INV-JOB-001** — en chattkörning som avbryts av en omstart fullföljs av
  nästa process och lämnar exakt ETT ärende och EN inkommande meddelanderad.
  Mekanik: jobbposten annoteras med `ticket_id`/`conversation_id` när ärendet
  skapats; ett återtag återanvänder dem i stället för att skapa nytt.
* **INV-CACHE-001** — en cachad chattreplik är en ren funktion av
  (tenant, fråga, KB-version, konfigversion) och ingenting annat. Mekaniskt:
  cachea bara när `turn_count == 0`, inga bilagor, personnummermaskeringen
  inte slagit till, kunden saknar minnesfakta, svaret inte eskalerade och
  kategorin är cachebar (aldrig betalning/juridik/klagomål/retention).
  Versionsbump vid KB-/instruktions-/SOUL-ändring gör gamla poster omatchbara.
  `SEMANTIC_CACHE=off|shadow|on` — shadow mäter utan att servera, och är
  default tills träffkvaliteten inspekterats. Evalharnessen kör ALLTID cache av.
* INV-SEC-009, INV-MEM-001, INV-LEARN-001 skärps eller lämnas orörda — aldrig
  försvagas. Summeringen (R3) wrappas alltid som opålitligt innehåll i
  user-position och återger bara vad kunden sagt och vad som lovats.

## 5. Faserna

**R0 hygien:** regionkontroll (`scripts/redis_kontroll.py`, fäller vid
icke-EU), TLS/`rediss://` i `redis_konfig.py` (konsol-togglen är Antons hand),
underbiträdesraderna (gjort), `fakeredis` som testberoende.
**R1 överlevande körningar:** streams-kön enligt §3, `chat_workers`-tak (=
kvotskydd: max N samtidiga LLM-kedjor, burstar köar i strömmen).
**R2 cache:** embeddingcache + svarscache + INV-CACHE-001 + versionsbump +
shadow-läge.
**R3 arbetsminne:** summering + de 8 senaste turerna när samtalet passerar 12
turer; uppdateras asynkront efter svaret (~1 extra anrop per 10 turer).
**R4 leads/mejlpipan på strömmen:** ett jobb per prospekt, prospekt-id som
idempotensnyckel — en halvkörd batch fortsätter efter deploy.
**R5 produktion (SPÄRRAD §8.1a):** `scripts/redis_provisionera.py` förberedd;
egen databas åt `main` (aldrig delad — samma tysta-korskopplings-regel som
`GEMINI_API_KEY`), EU, TLS, Essentials 250 MB (första nivån med persistens/HA;
gratis-30MB saknar båda och tål 30 anslutningar/100 ops/s — duger i dev, inte
i drift).
**R6 sandbox-eval:** Agent Memory + LangCache mot ENBART syntetisk data;
utfallet är ett gate-dokument, ingen driftkod.

### 5.1 Gates för managed Iris i drift

GA (inte preview) · Redis DPA tecknad · EU-region bekräftad · BYOK med
leverantör ur den godkända listan i `docs/JURIDIK_ATGARDER.md` · exkluderingar
allmänt tillgängliga · extraktionskontrakt förenligt med INV-MEM-001 ·
underbiträdeslistan uppdaterad före första riktiga kunddatabiten.

## 6. Avvisade alternativ, med motivering

KB-vektorer till Redis (§2) · managed LangCache/Agent Memory i drift nu (§2) ·
Context Retriever & RDI (§2) · arq/Celery/RQ (Streams räcker; ett köramverk är
en ny körmodell för ~100 raders vinst) · Redis-baserad rate limiting
(DB-varianten fungerar; R1:s worker-tak löser burst-problemet) · semantisk
router förbi triagen (flyttar ett säkerhetsbeslut till en likhetströskel) ·
semantisk sökning över kundminnet nu (12 fakta ryms hela i prompten; byggs i
Postgres/pgvector först när någon kund passerar ~30 fakta).

## 7. Verifiering

1. Hela sviten grön (backend + rotvakter + tsc), nya invarianttester med.
2. **Deploy-överlevnadstestet:** starta en chatt, döda processen mitt i,
   starta om — svaret fullbordas, exakt ett ärende. Skriptat i testerna
   (fakeredis) och körbart mot dev efter deploy.
3. Cachen i shadow-läge i dev; träffkvot + stickprov av 10 skulle-träffar
   granskas innan `on`.
4. `python scripts/kor_evals.py` — 7/7 golden, cache förbi-kopplad.
5. `python scripts/redis_kontroll.py` — EU-region + TLS svart på vitt.
