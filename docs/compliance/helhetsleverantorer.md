# Helhetsleverantörer för drift: Railway och alternativen

Beslutsunderlag, inte ett byte. Inget har flyttats. Källor lästa 2026-11-17/18 (hämtdatum anges som 2026-11-17 nedan).
Märkning: **[F]** fakta med källa, **[R]** egen räkning (visad), **[B]** bedömning. "Ej belagt" = ingen officiell källa hittad.
Priser exkl. moms. Valutor räknas inte om; där en jämförelse kräver det antas 1 € ≈ 1,1 $ och 11 SEK ≈ 1 € **[B, antagande]**.

## Rekommendation (kort)

1. **Stanna hos Railway, uppgradera till Pro och slå på en hård spärr (hard limit) i dag.** Spärren finns på alla planer, lägsta värde 10 $, och stoppar all förbrukning när den nås. Den löser oron för en skenande nota, men priset är att tjänsterna stängs av. [F, docs.railway.com/reference/usage-limits]
2. Sätt spärren klart över normal nota (förslag: e-postlarm 60 $, hård spärr 150 $) så den bara slår till vid ett fel, inte en bra månad. [B]
3. **Ta reda på varför fakturan blev 39 $.** Uppmätt snitt ger med Railways listpriser bara cirka 14 $. Skillnaden är oförklarad. [R]
4. Signera Railways DPA och läs underbiträdeslistan före första betalande kund. Railway är amerikanskt; DPA:n säger att infrastrukturen körs på Google Cloud. [F]
5. **Bästa EU-ägda alternativ: Clever Cloud** (Frankrike). Närmast Railway i arbetssätt, fasta instanspriser, Postgres 17 med daglig backup. Kostar ungefär lika i (a), mindre risk i (b). [F/B]
6. **Bästa "färre leverantörer"-alternativ: Google Cloud i Stockholm** (Cloud Run + Cloud SQL + Memorystore). DPA gäller automatiskt, Google finns redan i kedjan, och Memorystore stöder exakt de söktyper svarscachen använder (TAG + VECTOR). Dyrare och mer arbete. [F/B]
7. Byt inte före första kund. Pröva byte igen om notan ligger över ~150 $ flera månader, eller om kunder kräver EU-ägd drift. [B]

## Viktigt fynd om sökindexet

Svarscachen skapar sitt index med bara **TAG- och VECTOR-fält (HNSW, 1536 dim, COSINE)**, inga TEXT-fält (`snajp-support/app/cache/svarscache.py:255-282`). Den faller dessutom tillbaka tyst vid fel. Kravet är alltså svagare än "RediSearch": Valkey Search räcker. Google Memorystore for Valkey stöder VECTOR, NUMERIC och TAG men inte TEXT [F, docs.cloud.google.com/memorystore/docs/valkey/ftcreate]. Heroku Key-Value Store har Valkey Search [F, devcenter.heroku.com/articles/heroku-redis]. Hos övriga är stödet ej belagt; där körs Redis 8 som egen container med volym. [B]

## Jämförelsetabell mot kraven 1–8

Ja = uppfyllt, Delvis, Nej. Kostnad per månad; (a) dagens last två miljöer, (b) 3× last + Comp AI.

| Alternativ | 1 Dataskydd (säte/ägare, DPA, cert) | 2 Backup DB | 3 PG17 / Redis-sök | 4 Privat nät | 5 GitHub-deploy m.m. | 6 Kostnad (a) / (b), tak | 7 Driftbörda | 8 Flytt |
|---|---|---|---|---|---|---|---|---|
| **Railway Pro** (nuläge) | Delvis: USA, DPA måste signeras, SOC 2 T2 | Delvis: dagl./vecko/månad, ingen PITR, plats ej belagd | Ja som containrar (Redis 8 kör i dag) | Ja | Ja | 20–39 $ / 54–130 $; **hård spärr finns** | Låg | 0 |
| Clever Cloud | Ja: Frankrike, fransk ägd, DPA i villkoren (signering ej belagd), ISO 27001, HDS | Ja: daglig, 7 d, PITR via support | Ja PG 14–18 / Redis 8.10, sök ej belagd | Ja (Network Groups) | Ja (cron i Docker-appar: nej, egen schemaläggare) | ≈56–136 € / ≈190 €; "max-pris" vid autoskalning, hårt nota-tak ej belagt | Låg | 3–5 d |
| Scalingo | Ja: Frankrike (Strasbourg), ägare ej belagd, DPA måste signeras, ISO 27001, HDS | Ja: daglig, PITR (PG) | Ja PG 14–18 / Redis, sök ej belagd | Ej belagt i detalj | Ja (Heroku-likt) | ≈144 € / ≈345 € [R]; tak ej belagt | Låg | 3–5 d |
| Scaleway | Ja: Frankrike, Iliad, DPA i villkoren, ISO 27001, HDS | Ja: daglig 7 d, annan region; PITR ej belagd | Ja PG17 / Redis 8.4, sök ej belagd | Ja (VPC) | Delvis: bygg via Actions, bara egna/publika registries | ≈90–200 € / ≈280–440 €; bara larm | Medel | 6–10 d |
| OVHcloud | Delvis: Frankrike, DPA-URL ej belagd, ISO 27001 | Ja: daglig, 2–30 d | Ja PG17 / Valkey, sök ej belagd | Ja (vRack) | Nej: ingen PaaS, egen Kubernetes | ≈163–258 € / ≈275–420 €; bara larm | Hög | 10–15 d |
| STACKIT | Ja: Tyskland (Schwarz), ISO 27001, C5, SOC 2; DPA-form ej belagd | Ja: 30 d, PITR till klon | Ja PG17 / Valkey, sök ej belagd | Ej belagt | Delvis: Cloud Foundry eller SKE | ≈308–452 € / ≈650–750 €; tak ej belagt | Medel–hög | 10–15 d |
| Exoscale | Ja: Schweiz, A1/América Móvil, DPA automatisk, ISO 27001, SOC 2, C5 | Ja: daglig + PITR (nivåberoende) | PG17 ej belagt / Valkey, sök ej belagd | Ej belagt | Nej: Kubernetes | ≈152 € / ≈230–265 €; tak ej belagt | Hög | 10–15 d |
| UpCloud | Ja: Finland, finska ägare, DPA i villkoren, ISO 27001 | Ja: daglig + WAL 5 min, PITR | PG17 ej belagt / Valkey, sök ej belagd | Ja (SDN) | Nej: Kubernetes eller Coolify | ≈54 € / ≈104–140 € (priser ej verifierade); förbetalt saldo, kan gå negativt | Hög | 8–12 d |
| Koyeb | Delvis: Frankrike, köpt av Mistral AI 2026, DPA 2021, certifiering ej belagd | Ej belagt | Delvis PG 14–17 (motsägelse) / ingen Redis | Ja | Ja | ≈113 $ / ≈208 $; bara larm | Låg–medel | 3–5 d |
| Northflank | Delvis: Storbritannien, ingen publik DPA, SOC 2 T2, ISO oklart | Ja: tim/dag/vecka, PITR ej belagd | Ja PG 12–18 / Redis 8.10, sök ej belagd | Ja | Ja (cron, preview-miljöer) | ≈96 $ / ≈249 $; bara larm | Låg | 2–4 d |
| GleSYS | Ja: Sverige, europeisk ägare, DPA i avtalet, ISO 27001 | Ja: PITR 14 d | Delvis PG **18** (inte 17) / ingen Redis | Delvis (VM ja, DB nej) | Nej | ≈155–300 € / ≈232–449 €; tak ej belagt | Hög | 10–15 d |
| Elastx | Ja: Sverige, svenskägd, DPA på begäran, ISO 27001 | Ja: PITR 7–90 d, se-sto | Ja PG17 / Valkey | Ja | Nej | ≈3 150–5 545 SEK / ≈4 420–8 410 SEK; tak ej belagt | Hög | 10–15 d |
| Cleura | Delvis: Sverige (Iver), DPA i villkoren, ISO 27001 | Ej belagt | Ej belagt (kräver supportavtal) | Ja | Nej | Ej belagt | Hög | 10–15 d |
| Safespring | Delvis: Sverige, DPA på begäran, ISO 27001 | Ej belagt | Delvis (DBaaS via Severalnines, version ej belagd) | Ja | Nej | ≈1 770–3 930 kr / ≈2 660–6 660 kr; tak ej belagt | Hög | 10–15 d |
| Hetzner + Coolify/Dokploy | Delvis: Tyskland, DPA ingås i konsolen, ISO 27001 | Delvis: VM-backup daglig 7 platser; DB = egna dumpar till S3 | Ja som containrar | Ja | Ja via Coolify/Dokploy | ≈26–69 € / ≈33–98 €; fast pris per server | **Hög** | 5–8 d + löpande |
| Render | Delvis: USA, DPA kompletterar villkoren, ISO 27001, SOC 2 | Ja: PITR 7 d (Pro) | Ja PG 13–18 / Valkey 8, sök ej belagd | Ja | Ja | ≈164 $ / ≈322 $; tak ej belagt | Låg | 3–4 d |
| Fly.io | Delvis: USA, DPA måste signeras, SOC 2 | Ja: 10 d + PITR | Ja PG 16–17 (ej i Stockholm) / Upstash, sök ej belagd | Ja | Delvis (Actions) | ≈145 $ / ≈337 $; **inget larm, inget tak** | Medel | 4–6 d |
| DigitalOcean | Delvis: USA, DPA tillägg till villkoren, SOC 2 | Ja: daglig + PITR 7 d | Ja PG 15–18 / Valkey, sök ej belagd | Ja | Ja | ≈122–130 $ / ≈203 $; bara larm | Låg | 3–5 d |
| Heroku | Delvis: USA (Salesforce), underhållsläge sedan 2026-02 | Delvis: Essential ingen rollback | Ja PG 16–18 / **Valkey Search ja** | Delvis (Private Spaces) | Ja | ≈180 $ / ≈310 $; tak ej belagt | Låg | 3–5 d |
| Google Cloud (Stockholm) | Delvis: USA, DPA automatisk; redan underbiträde | Ja: PITR 7 d (Enterprise) | Ja PG17 / **Valkey: TAG+VECTOR ja** | Ja | Delvis (Cloud Build/Actions) | ≈150–200 $ / ≈285 $; spend cap bara för Cloud Run | Medel | 5–8 d |
| AWS / Azure (referens) | Delvis: USA, DPA i standardvillkor | Ja (RDS / Flexible Server) | Ja | Ja | Delvis | Ej räknat; bara budgetlarm | Medel–hög | 8–15 d |

## Railway (nuläget, jämförelsepunkt)

- **Säte/ägare [F]:** Railway Corporation, San Francisco, USA. DPA måste signeras via DocuSign och blir bindande först när Railway signerat. Överföring via DPF, annars SCC 2021/914. Primär behandling sker i USA (DPA 9.1). Infrastruktur: Google Cloud Platform enligt Exhibit C. Backuper "across multiple sites and regions", regioner ej namngivna. Underbiträden: trust.railway.com/item/subprocessors. (https://railway.com/legal/dpa, 2026-11-17)
- **Region [F]:** "EU West Metal", Amsterdam, id `europe-west4-drams3a`. Sidan säger inte om "Metal" betyder egen hårdvara. DPA:n säger GCP. Motsägelsen är olöst: **ej belagt**. (https://docs.railway.com/reference/deployment-regions)
- **Certifiering [F]:** SOC 2 Type 2, SOC 3, HIPAA, DPF. ISO 27001 listas inte. (https://trust.railway.com/)
- **Backup [F]:** dagligen (sparas 6 d), veckovis (27 d), månadsvis (89 d). Ingen PITR beskriven. Plats ej angiven. Debiteras som volymlagring. (https://docs.railway.com/reference/backups) Att backup kräver Pro står inte på de sidor jag läste; uppgiften kommer från er egen verifiering.
- **Pris [F]:** Hobby 5 $/mån inkl. 5 $ förbrukning; Pro 20 $/mån inkl. 20 $. vCPU 20 $/mån, RAM 10 $/GB-mån, volym 0,15 $/GB-mån, egress 0,05 $/GB. (https://docs.railway.com/reference/pricing/plans)
- **Spärr [F]:** Usage Limits på alla planer. E-postlarm (mjukt) och hård spärr som stoppar alla arbetslaster, med varning vid 75, 90 och 100 %. Railway kallar den "a possibly destructive action". Lägsta värde 10 $. När spärren höjs startas tjänsterna om automatiskt. (https://docs.railway.com/reference/usage-limits)
- **Kostnad (a) [R]:** CPU 0,09 × 20 = 1,80. RAM 1,1 × 10 = 11,00. Volym ~5 GB × 0,15 = 0,75. Backup ~3,3 GB × 0,15 = 0,50. Egress 2 × 0,05 = 0,10. **Förbrukning ≈ 14,15 $.** Hobby: 14 $. Pro: 20 $ (förbrukningen ryms i avgiften).
  - **Men fakturan var 39 $.** På Hobby är notan lika med förbrukningen när den överstiger 5 $, så förbrukningen var cirka 39 $, nästan tre gånger det uppmätta snittet. Troliga förklaringar [B]: spikar vid leadskörningar som snittet döljer, minnesreservationer, eller tjänster som inte ingick i mätningen. Kontrollera Usage-sidan per tjänst.
  - **Kalibrerat (a):** Hobby ≈ 39 $, Pro ≈ 39 $ (20 $ avgift + 19 $ över).
- **Kostnad (b) [R]:** 3 × (1,80 + 11,00) = 38,40. Comp AI: 4 små containrar + Postgres ≈ 1,25 GB RAM × 10 = 12,50, CPU ≈ 0,02 × 20 = 0,40. Lagring ~10 GB × 0,15 = 1,50. Egress ~0,30. **≈ 53 $.** Kalibrerat på fakturan: 3 × 39 + 14 ≈ **131 $**. Hobby och Pro kostar lika när förbrukningen är över 20 $. Objektlagring för Comp AI hos Railway: ej belagt; räkna med en extern S3 (t.ex. Hetzner 6,49 €).
- **Driftbörda:** låg (som i dag). **Flytt:** 0 d.

## Europeiska plattformar (PaaS) med hanterade tjänster

### Clever Cloud
- **[F]** "100% French company", Nantes, grundat 2010 (https://www.clever.cloud/sovereign-cloud/). Ingen amerikansk ägare hittad [B].
- **[F]** DPA publicerad inom de allmänna villkoren: https://www.clever.cloud/general-terms-and-conditions-of-use/clever-cloud-data-processing-agreement/. Om den gäller utan underskrift: ej belagt. Underbiträden: https://cdn.clever-cloud.com/uploads/2026/02/clever-clouds-sub-processors.pdf (ej genomläst). ISO 27001:2022 och HDS.
- **[F]** PG 14–18 (17.12 finns). Daglig backup, 7 d, gratis. PITR via pgBackRest på begäran till support. Dev-planer saknar backup. (https://www.clever.cloud/developers/doc/deploy/databases/postgresql/)
- **[F]** Redis 8.10.2; installation av moduler är begränsad (https://www.clever.cloud/developers/doc/deploy/databases/redis/). Om Redis 8:s inbyggda sökmotor är påslagen: ej belagt. Testa, annars Redis 8 som Docker-app.
- **[F]** GitHub-integration per gren, Dockerfile-bygge, privat registry, env per app, privat nät via Network Groups. Docker-appar stöder inte `cron.json`: kör schemaläggaren i containern (det gör api:t redan med sina bakgrundsloopar [B]).
- **[F]** Debitering per sekund. Prissidan: "You'll never pay more than you choose!" (https://clever.cloud/pricing/). [B] Det syftar på autoskalningens max, inte ett hårt tak på notan.
- **Priser [F]** (officiellt pris-API, https://api.clever-cloud.com/v4/billing/price-system?zone_id=par&currency=EUR): nano 0,00833 €/h (≈6 €/mån), XS 1 GiB 0,02222 €/h (≈16 €), PG XXS_SML ≈5,25 €, PG XS_TNY ≈15 €, Redis s_mono ≈5 €. RAM/disk per DB-plan ej belagt.
- **(a) [R]:** 6 tjänster nano (36) + 2 PG XXS (10,50) + 2 Redis (10) ≈ **56 €**. Med XS överallt (96) + 2 PG XS (30) + Redis (10) ≈ **136 €**.
- **(b) [R]:** XS/S-blandning ≈108 + 4 nano 24 + 3 PG XS 45 + Redis 10 + 10 GB Cellar 0,20 ≈ **190 €**.
- **Driftbörda:** låg. **Flytt [B]:** 3–5 d.

### Scalingo
- **[F]** Fransk PaaS i Strasbourg, kör på Outscale (osc-fr1; SecNumCloud-region finns). ISO 27001 (certifikat 2025-09, https://cdn.scalingo.com/documents/20250912-scalingo-iso27001-lne-certificate-38435-rev2.pdf) och HDS. Ägare: ej belagt. DPA: https://scalingo.com/data-processing-agreement; enligt Scalingos GDPR-blogg blir den bindande när den skickats signerad till dpo@scalingo.com, alltså **måste signeras**.
- **[F]** PG 14–18 (17 finns, EOL nov 2029) (https://doc.scalingo.com/databases/postgresql/start). Alla planer har daglig backup; PITR för PostgreSQL. Debitering per minut. (https://scalingo.com/pricing)
- **Priser [F, sökutdrag av scalingo.com/pricing och /databases]:** container M 512 MB 14,40 €/mån; PG Starter 512M 7,20 €; Redis Starter 256M 7,20 €, 512M 14,40 €. Container L (1 GB) ej belagt; antas 28,80 € [B].
- **(a) [R]:** 4 × M (57,60) + 2 × L (57,60) ≈ 115 €, + 2 PG 512M (14,40) + 2 Redis 256M (14,40) ≈ **144 €**.
- **(b) [R]:** ≈ 2 × (a)-compute 230 + 4 × M 57,60 + 3 PG ≈ 30 + Redis 29 ≈ **≈ 345 €**; objektlagring extern.
- Sökstöd, privat nät och tak: ej belagt. **Driftbörda:** låg. **Flytt [B]:** 3–5 d.

### Scaleway
- **[F]** Iliad-koncernen, Frankrike. DPA ingår i villkoren (GTS: DPA går först när Scaleway är biträde). Underbiträden: https://www.scaleway.com/en/subprocessorlist/. ISO 27001, HDS; SecNumCloud pågår.
- **[F]** PG17; daglig autobackup 7 d, lagras i annan region som standard. Redis 8.4 (RED1-micro ≈35 €/mån). Sök: ej belagt.
- **[F]** Serverless Containers 0,00001 €/vCPU-s, 0,000002 €/GB-s; privat nät; cron-triggers. Endast Scalewayregistry eller publika registries, ingen GitHub-integration. Billing alerts, inget tak. (scaleway.com/en/pricing/serverless/, /managed-databases-pricing/; sidorna gav 403, fakta från sökutdrag av de officiella URL:erna)
- **(a) [R]:** 6 containrar 54–109 + 2 DB-DEV-S 23 + 2 Redis 70 ≈ **147–200 €** (≈90–140 € med egen Redis). **(b):** ≈ **280–440 €**.
- **Driftbörda:** medel. **Flytt:** 6–10 d.

### OVHcloud
- **[F]** OVH Groupe SA, Roubaix, börsnoterat, Klaba-familjen kontrollerar. Ingen nordisk region. ISO 27001 för datacenter utanför USA. DPA-URL ej belagd. Web PaaS avvecklad → Managed Kubernetes. PG 15–18 (Discovery 54,46 €/nod/mån), Valkey från 47,30 €/mån. Daglig backup 2–30 d.
- (https://www.ovhcloud.com/en-ie/public-cloud/postgresql/, /valkey/, /kubernetes/; https://docs.ovhcloud.com/en/guides/public-cloud/databases/postgresql-capabilities)
- **(a) [R]:** 2 noder 54 + 2 PG 109 + 2 Valkey 95 ≈ **258 €** (163 € med egen Redis). **(b):** ≈ **275–420 €**. Driftbörda hög. Flytt 10–15 d.

### STACKIT
- **[F]** Schwarz Digits Cloud GmbH & Co. KG, Schwarz-gruppen (Lidl/Kaufland), Tyskland och Österrike. ISO 27001, BSI C5 Type 2, ISAE 3000/SOC 2. DPA: https://stackit.com/en/asset/download/34534/file/STACKIT_data_processing_agreement.pdf. PG17, backup 30 d, PITR till klon. Minsta PG 90,71 €/mån, KV Store 71,97 €/mån, SKE 71,71 €/kluster. (prislista v1.0.45)
- **(a) [R]:** ≈ **308–452 €**. **(b):** ≈ **650–750 €**. Driftbörda medel–hög. Flytt 10–15 d. Dyrast i gruppen.

### Exoscale
- **[F]** Akenes SA, Lausanne; ägs av A1 Digital → A1 Telekom Austria → majoritet América Móvil (Mexiko). DPA bindande automatiskt (https://www.exoscale.com/dpa/). ISO 27001/27017/27018, SOC 2 Type 2, C5 (https://www.exoscale.com/compliance/). Underbiträde för DBaaS: Aiven Oy.
- **[F]** Daglig backup med PITR (uppgifter om nivå motsäger varandra). Ingen PaaS, SKS Kubernetes. Compute Medium 2/4 GB ≈ 34 €/mån.
- **(a) [R]:** ≈ **152 €**. **(b):** ≈ **230–265 €**. Driftbörda hög. Flytt 10–15 d.

### UpCloud
- **[F]** UpCloud Oy, Helsingfors; finska ägare (bl.a. statliga Tesi). Stockholm och Helsingfors. DPA i användarvillkoren (https://upcloud.com/global/terms-of-service/). ISO 27001. Backup daglig + WAL var 5:e min, PITR, 3–31 d (https://upcloud.com/docs/products/managed-postgresql/backups/). Managed Valkey. Förbetalt saldo; kan gå negativt, inget tak.
- **Priser:** endast sökutdrag (prissidan gav 403), **ej verifierade**: PG 1 GB ≈ 9 €, Valkey ≈ 8 €, server 2 GB ≈ 12 €.
- **(a) [R]:** 3 × 12 + 2 × 9 ≈ **54 €**. **(b):** ≈ **104–140 €**. Ingen PaaS: Kubernetes eller Coolify. Driftbörda hög. Flytt 8–12 d.

### Koyeb
- **[F]** Koyeb SAS, Paris; köpt av Mistral AI (Frankrike) februari 2026 och går in i "Mistral Compute" (https://www.koyeb.com/pricing). DPA från 2021 (https://koyeb.com/docs/legal/data-processing-agreement); underbiträden inkl. AWS, GCP, Intercom, Slack (USA). Certifiering ej belagd. Ingen hanterad Redis. Pro 29 $ inkl. 10 $; inget hårt tak ("being worked on"), larm vid 80/100 %.
- **(a) [R]:** ≈ **113 $**. **(b):** ≈ **208 $**. [B] Avtal och plattform kan ändras efter köpet. Flytt 3–5 d.

### Northflank
- **[F]** Northflank Ltd, London. EU-regioner i Frankfurt, Nederländerna, Zürich; kör på GCP. Ingen DPA införlivad i villkoren och ingen publik DPA-URL. SOC 2 Type II; ISO 27001 motsägelsefullt. PG 12–18, Redis 8.10. Backup tim/dag/vecka. Native cron, preview-miljöer per gren, privat registry. 0,01667 $/vCPU-h, 0,00833 $/GB-h. Inget tak, bara larm. (https://northflank.com/pricing, /security, /legal/terms)
- **(a) [R]:** ≈ **96 $**. **(b):** ≈ **249 $**. [B] Bäst funktionsmatch, men UK-bolag på GCP: ingen dataskyddsvinst mot Railway. Flytt 2–4 d.

## Svenska och nordiska leverantörer

Ärligt: **ingen av dem är en plattform som Railway.** De säljer virtuella maskiner, Kubernetes och (ibland) hanterade databaser. Bygge, deploy, TLS, loggar, Redis och övervakning blir ert jobb. För två personer utan driftpersonal är det den stora kostnaden, inte fakturan. [B]

- **GleSYS [F]:** svenskt, "Nordic company with European ownership", egna datacenter i Falkenberg och Stockholm. DPA "integral part of the Agreement" (https://glesys.com/legal/data-processing-agreement/), ingen behandling utanför EU/EES. ISO 27001. Managed PostgreSQL **18** (inte 17), PITR 14 d, ingen HA, **ingen privat anslutning** (IP-allowlist + TLS). KVM 4/8 GB 77,28 €/mån; Managed DB 72,52 €. (https://glesys.com/pricing/) **(a)** ≈ 155 € (VM) – 300 € (med managed DB); **(b)** ≈ 232–449 €.
- **Elastx [F]:** svenskägt, Stockholm (3 zoner). DPA på begäran, ingen publik underbiträdeslista. ISO 27001/27017/27018, ISAE 3000 Typ II. DBaaS PG 14–17 med PITR 7–90 d i se-sto, från 1 833 SEK/mån; Valkey från 1 833 SEK. VM 4/8 GB 1 268 SEK. Managed Kubernetes ≈ 9 900 SEK/mån. (https://elastx.se/en/trust-center, /postgresql, /openstack, /kubernetes) **(a)** ≈ 3 150–5 545 SEK; **(b)** ≈ 4 420–8 410 SEK.
- **Cleura [F]:** "an Iver company", Karlskrona; regioner Karlskrona, Stockholm, Frankfurt. Standard-DPA ingår vid onlineregistrering. ISO 27001. Managed Database kräver supportavtal; priser ej belagda. **Binero** har ingen koppling till Cleura; gick 2024 ihop med Infrateq och Xpeedio (https://binero.com/en/article/a-new-exciting-era-for-binero). [B] Underbiträdet Digital Realty ingår i en amerikansk koncern.
- **Safespring [F]:** Stockholm och Oslo. ISO 27001 (RISE). DPA på begäran. DBaaS via Severalnines (Postgres, MySQL, Valkey), Tiny ≈ 1 461 SEK/mån. VM 4/8 GB 860 kr/30 d. Managed Kubernetes 4 900 SEK/mån. (https://www.safespring.com/pris/) **(a)** ≈ 1 770–3 930 kr; **(b)** ≈ 2 660–6 660 kr.
- **UpCloud:** se ovan; enda nordiska med hanterad Valkey, PITR och DPA i villkoren, men utan PaaS.
- **Driftbörda:** hög för alla. **Flytt [B]:** 10–15 d, plus att bygga deploykedja.

## Amerikanska plattformar med EU-region

- **Render [F]:** Render Services, Inc. Frankfurt enda EU-region. ISO 27001, SOC 2 T2. DPA kompletterar villkoren. PG 13–18, PITR 7 d på Pro. Key Value = Valkey 8, sök ej belagd. Pro-arbetsyta 25 $; tjänst 0,5 CPU/512 MB 7 $, 1 CPU/2 GB 25 $; PG 0,5c/1 GB 19 $; KV 256 MB 10 $. Inget tak nämnt. (https://render.com/pricing.md, /docs/postgresql-backups, /security) **(a) [R]** 25 + 4×7 + 2×25 + 2×19 + 3 + 2×10 ≈ **164 $**; **(b)** ≈ **322 $** + S3.
- **Fly.io [F]:** Stockholm (arn) finns, men hanterad Postgres bara i ams/fra. DPA "will become active when you sign it". SOC 2 T2. "We don't support billing alerts (yet)… there's no soft ceiling" (https://docs.fly.io/about/cost-management/). **(a)** ≈ **145 $**; **(b)** ≈ **337 $**. Löser inte oron.
- **DigitalOcean [F]:** DigitalOcean, LLC; App Platform i AMS/FRA. DPA tillägg till villkoren, SCC som reserv till DPF. SOC 2 T2. PG 15–18 med daglig backup + PITR 7 d. Valkey från 15 $. Instans 512 MiB 5 $, 2 GiB 25 $. PG från 15,15 $. Bara larm. (https://www.digitalocean.com/pricing/app-platform, /pricing/managed-databases) **(a)** 4×5 + 2×25 + 2×15,15 + 2×15 ≈ **130 $**; **(b)** ≈ **203 $**.
- **Heroku [F]:** Salesforce. Sedan 2026-02-06 "sustaining engineering model" (https://www.heroku.com/blog/an-update-on-heroku/). PG 16–18; Key-Value Store med **Valkey Search**. Privat nät kräver troligen Private Spaces (pris ej belagt). **(a)** ≈ **180 $**; **(b)** ≈ **310 $**. [B] Fel riktning att flytta in i en produkt i underhållsläge.

## Hyperskalarna

- **Google Cloud [F]:** CDPA "is incorporated into the Agreement(s)" (https://cloud.google.com/terms/data-processing-addendum); underbiträden https://cloud.google.com/terms/subprocessors. Cloud Run finns i europe-north2 (Stockholm). Cloud SQL PG17 (18 standard), PITR upp till 7 d i Enterprise; shared-core saknar SLA. Memorystore for Valkey: FT.CREATE med VECTOR, NUMERIC, TAG, ej TEXT (https://docs.cloud.google.com/memorystore/docs/valkey/ftcreate); shared-core-nano "only for development or testing".
  - **Tak [F]:** budgetar larmar men stoppar inte. Nytt: "spend cap"-budgetar pausar ny användning av Cloud Run, Cloud Run functions och Gemini/Vertex i ett projekt; Cloud SQL och Memorystore omfattas inte och överdrag på grund av fördröjning faktureras (https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps). Lanseringsstatus: ej belagt på sidan.
  - **Priser [F]** (https://cloud.google.com/run/pricing, /sql/pricing, /memorystore/docs/valkey/pricing): Cloud Run instansbaserat 0,000018 $/vCPU-s och 0,000002 $/GiB-s; Cloud SQL db-f1-micro 8,03 $, db-g1-small 26,86 $ (north2); Valkey shared-core-nano 24,38 $.
  - **(a) [R]:** api prod 1 vCPU/2 GiB alltid på: 2 628 000 s × (0,000018 + 2 × 0,000002) = 57,8; dev 1/1 GiB 52,6; web och support skalar till noll ≈ 0–3; Cloud SQL 26,86 + 8,03 + SSD 3,6 + backup 1 ≈ 39,5; Valkey 2 × 24,38 = 48,8 → **≈ 200 $** (≈ 150 $ om dev-api skalar till noll).
  - **(b) [R]:** prod-api 2/4 GiB 115,6 + dev 52,6 + web/support 10 + Comp AI 4 containrar ≈ 10 (skalar till noll) + Cloud SQL 48 + Valkey 48,8 + GCS ≈ 0,2 → **≈ 285 $**.
  - [B] Vinst: ingen ny leverantör (Google finns redan för Vertex), DPA automatisk, Stockholm, Valkey-sök som täcker cachens fält. Förlust: mer konfiguration (IAM, VPC-anslutning, Cloud Build), dyrare, och amerikanskt ägt som Railway.
- **AWS / Azure [B, ej verifierat denna körning]:** Stockholm resp. Sweden Central; DPA i standardvillkor; budgetlarm men inget hårt tak utan egen automation. Ingen fördel framför Google för er, som redan har Google-avtal.

## Egen drift: Hetzner + Coolify eller Dokploy

- **[F]** Hetzner Online GmbH, Tyskland (ägare ej belagd); Falkenstein, Nürnberg, Helsingfors. DPA ingås i konsolen genom kryssruta (https://docs.hetzner.com/general/company-and-policy/data-protection-at-hetzner/); underbiträden https://www.hetzner.com/AV/subunternehmer.pdf. ISO 27001:2022.
- **[F]** Nya priser från 2026-06-15: CX33 4/8 GB 8,99 €, CX43 8/16 GB 16,49 €; CPX32 4/8 GB 30,49 € (Helsingfors). Månadstak per server. Object Storage 6,49 €/mån inkl. 1 TB, virtual-hosted-style (`<bucket>.<location>.your-objectstorage.com`). Serverbackup daglig, 7 platser; backuppris ej belagt. **Varning:** prissidorna visade "currently unavailable" på EU-planer; kontrollera tillgången. (https://www.hetzner.com/cloud/cost-optimized/, https://www.hetzner.com/storage/object-storage/)
- **[F]** Coolify: GitHub App för push/PR-deploy, schemalagda Postgres-dumpar till S3 (ingen PITR, ingen Redis-backup), privata registries (https://coolify.io/docs/databases/backups). Dokploy: liknande (https://docs.dokploy.com/docs/core/auto-deploy).
- **(a) [R]:** 2 × CX33 (17,98) + 2 IPv4 (1,00) + Object Storage (6,49) ≈ **25,5 €** (+ backup). Med CPX i Helsingfors ≈ **68,5 €**. **(b):** CX43 + CX33 + 1 + 6,49 ≈ **33 €**; CPX ≈ **97,5 €**.
- **Vad ni själva måste sköta [B]:** OS-patchning, uppgradering av Coolify/Dokploy, Postgres-uppgraderingar, backup och återställningstest, PITR om ni vill ha det, Redis, övervakning och larm, brandvägg, diskutrymme, säkerhetsincidenter i plattformen. TLS sköts automatiskt av Traefik/Caddy. Räkna med några timmar i månaden och en person som kan det när något brinner. Billigast på fakturan, dyrast i tid och risk för ett personuppgiftsbiträde.

## De tre bästa ställda mot varandra

| | Railway Pro + hård spärr | Clever Cloud | Google Cloud (Stockholm) |
|---|---|---|---|
| Kostnad (a) / (b) | 20–39 $ / 54–131 $ | ≈56–136 € / ≈190 € | ≈150–200 $ / ≈285 $ |
| Vinner | Inget arbete, samma arbetssätt, hård spärr finns, billigast | EU-ägt (ingen CLOUD Act-fråga, ingen tredjelandsöverföring för drift), ISO 27001, PG17 med daglig backup gratis, fasta instanspriser | En leverantör mindre, DPA automatisk, data i Stockholm, Valkey-sök som täcker cachen, PITR |
| Förlorar | Amerikanskt, DPA måste signeras, ingen PITR, oklart om GCP eller egen hårdvara, spärren stänger allt | 3–5 dagars flytt, sökstöd i Redis måste testas, inget hårt nota-tak belagt, cron i Docker-appar saknas | 5–8 dagars flytt, mer konfiguration, 4–7 ggr dyrare i (a), tak bara för Cloud Run, amerikanskt ägt |

**Underbiträdeskedjan vid byte:**
- I dag (drift): Railway Corporation (USA) + Railways egna underbiträden (Google Cloud enligt DPA, Cloudflare m.fl. enligt trust-sidan). Oavsett val stannar Google (Vertex AI), Resend och GitHub.
- **Clever Cloud:** Railway och dess kedja försvinner. Clever Cloud SAS (Frankrike) och dess underbiträden (PDF, ej genomläst) tillkommer. Driftdatan lämnar amerikansk ägarsfär.
- **Google Cloud:** Railway och dess kedja försvinner. Inget nytt bolag tillkommer, men Google behandlar mer data än i dag (hela databasen, inte bara modellanrop).
- **Stanna:** inget ändras; signerad DPA med Railway tillkommer som dokument.

**Frågor som bara ägaren kan avgöra:**
1. Är det acceptabelt att produktionen stängs av när spärren slår till, eller väger en skenande nota lättare än driftstopp hos en kund?
2. Vilket månadsbelopp är taket i praktiken, och vid vilken nivå ska ett byte prövas på nytt?
3. Är "EU-ägd drift utan amerikanskt moderbolag" ett säljargument eller ett krav från svenska kunder, eller räcker DPF/SCC?
4. Ska data ligga i Sverige (Google Stockholm, Elastx, GleSYS) eller räcker EU?
5. Är ni beredda att lägga 3–8 dagar på en flytt före eller strax efter första betalande kund?
6. Ska Comp AI köras alls, och i så fall hos samma leverantör eller separat?

## Största osäkerheter

- Varför fakturan blev 39 $ när mätningen ger 14 $. Avgör alla kostnadsjämförelser.
- Om Railway Amsterdam körs på egen hårdvara ("Metal", Digital Realty-kod) eller GCP (DPA Exhibit C).
- Sökstöd i hanterad Redis/Valkey är ej belagt hos alla utom Google och Heroku.
- Flera priser kommer från sökutdrag av officiella sidor som blockerade direkt läsning (Scaleway, UpCloud, Scalingo).
- Flyttdagar och driftbörda är bedömningar, inte mätningar.
