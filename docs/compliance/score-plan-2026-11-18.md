# Poängplan 2026-11-18: vad som går att uppfylla utan ägaren

Datum: 2026-11-18 (kväll). Skrivet av Claude (agent) på Antons uppdrag.
Underlag: matriserna i `ramverk/{gdpr,iso27001,iso42001}/matris.md` (läget 2026-11-18,
andra genomgången) och `BESLUTSUNDERLAG-2026-11-17.md`.

**Uppdraget.** Höj antalet uppfyllda krav med det som inte kräver ett beslut eller en
handling från Anton. Statusreglerna i matriserna gäller oförändrade: *uppfyllt* kräver
belägg som finns i dag (en fil, ett test, en CI-kontroll eller ett skript som visar
läget). En policy som beskriver något som inte görs räknas inte.

**Redan blockerat på Anton, inte rört här:** Supabase-integrationen och release-PR 72,
Railway Pro och säkerhetskopior, rotering av hemligheter, radering av Render, Redis Cloud
och Supabase-projektet, signering av avtal (DPA) och besluten i `underlag/LASMIG.md`,
valet av ersättare för gemini-2.5, juristgranskning.

## Klasser

- **(a)** går att uppfylla nu med kod, CI, konfiguration i repot eller dokumentation som
  beskriver verklig drift.
- **(b)** kräver Anton: ett beslut, en signatur, en uppgift bara han har, en merge till
  `main`, en inställning i ett konto eller en betald plan.
- **(c)** kräver en extern part: jurist, leverantör, revisor eller en tredje person.

Ett krav står i den *strängaste* klassen som behövs för att det ska bli uppfyllt. Har
kravet en del agenten kan göra står den i kolumnen "Agentens del", och "Gjort" säger om
den är gjord i den här omgången (PR mot `development`, se sist).

## Resultat

| Ramverk | Uppfyllt | Delvis | Saknas | Ej tillämpligt | Okänt |
|---|---|---|---|---|---|
| GDPR (19) | 0 → **0** | 17 → **17** | 1 → **1** | 1 → 1 | – |
| ISO 27001 (119) | 0 → **3** | 74 → **72** → **73** | 25 → **24** → **23** | 8 → 8 | 12 → 12 |
| ISO 42001 (70) | 1 → **5** | 53 → **51** → **52** | 16 → **14** → **13** | 0 → 0 | 0 → 0 |

Flyttade krav:

| Ramverk | Krav | Från → till | Belägg |
|---|---|---|---|
| ISO 27001 | **A.5.8** Säkerhet i projektledning | delvis → uppfyllt | Varje PR mot `development` måste besvara säkerhets- och AI-frågan, annars fäller CI: `.github/pull_request_template.md`, `scripts/pr_granskning.py`, `.github/workflows/pr-granskning.yml`, INV-PROC-001 med test `tests/invariants/test_inv_proc_001.py` |
| ISO 27001 | **A.8.29** Säkerhetstestning i utvecklingen | delvis → uppfyllt | CI-jobbet `databas` kör nu tenantisoleringen (RLS, INV-SEC-001) och en provkörning av rättighetsskriptet mot hela migrationskedjan och fäller vid överhoppat test (`verify.yml`; `snajp-support/tests/db/test_rls_isolation.py`, `test_gdpr_radera_db.py`), utöver invarianterna och gitleaks på varje PR |
| ISO 27001 | **7.5.3** Styrning av dokumenterad information | delvis → uppfyllt | Repot är privat med två namngivna medarbetare, styrdokumenten versionshanteras i git (`bevis/github-2026-11-18.txt`; `docs/compliance/` spåras sedan PR 67) |
| ISO 27001 | **9.1.1** Övervakning och mätning | saknas → delvis | Mätt 2026-11-18: CI-utfall, öppna larm, övervakningens körningar (`bevis/github-2026-11-18.txt`, `drift-och-tillgangar.md` §4–5). Måtten är inte beslutade |
| ISO 42001 | **7.5.3** Styrning av dokumenterad information | delvis → uppfyllt | Som ISO 27001 7.5.3 |
| ISO 42001 | **A.4.2** Resursdokumentation | delvis → uppfyllt | Modell, konfigfält, standardvärde och värde i drift per steg och system: `ai-system/*.md` avsnitt 3 |
| ISO 42001 | **A.4.5** System- och beräkningsresurser | delvis → uppfyllt | Railway-tjänst, region och repliker, Vertex-regioner och Jev hos TypeSafe per system: `ai-system/*.md` avsnitt 3; `drift-och-tillgangar.md` §1 |
| ISO 42001 | **A.6.2.3** Design- och utvecklingsdokumentation | delvis → uppfyllt | Design steg för steg med kod- och invariantreferenser för alla AI-system, också supportagenten och Jev som saknade det: `ai-system/*.md` avsnitt 2 och 7 |
| ISO 42001 | **A.3.3** Anmälan av oro | saknas → delvis | Ärendemallen `.github/ISSUE_TEMPLATE/ai-oro.yml` ger den som arbetar i Snajp en väg att anmäla AI-fel och oro. P28 (skydd för den som anmäler) är osignerad |
| ISO 42001 | **A.5.5** Samhällspåverkan | saknas → delvis | Bedömningsutkast `ai-system/samhallspaverkan.md`; inte beslutat |
| ISO 42001 | **A.2.3** AI-policyns samstämmighet | saknas → delvis | Genomgång av P27 mot alla 27 andra policyer, utkast som gäller när P27 är godkänd: `ai-system/policy-samstammighet.md` (6 krockar, 19 glapp, förslag per policy). Se "Uttömt 2026-11-18" |

Inget GDPR-krav flyttade. Alla 18 öppna GDPR-krav hänger på ett beslut, en signatur, en
merge till `main` eller en juristgranskning. Agentens bidrag där är belägg som minskar
gap: rättighetsskriptet är nu provkört mot hela schemat i CI (PR-1, PR-3, PR-5, ISO 27001
A.8.10), och KVITTO_MODEL gör att kvittostegen kan stanna på en prövad modell när MODEL byts.

**Fynd som drar åt andra hållet (inte statusändrande i dag, men inskrivna i matriserna):**
- Sedan repot blev privat på gratisplanen gäller **grenskyddet och code owner-kravet på
  `main` inte längre** (GitHub svarar 403). CodeQL och GitHubs hemlighetsskanning är också
  avstängda; gitleaks i CI ersätter den senare för nya commits. Berör A.5.3, A.8.4, A.8.8,
  A.8.25, A.8.28, A.8.32 och ISO 42001 A.6.2.5.
- **Övervakningen har gett en enda schemalagd körning** (2026-11-18 04:44 UTC) trots
  timschema. Berör A.8.16 och ISO 42001 9.1, A.6.2.6. *Åtgärdat i PR 84, se sist.*
- `audit_logs` finns i schemat men skrivs inte av någon kod: ingen åtkomstlogg för admin.
  *Åtgärdat i PR 85, se sist.*
- Systembladen visar att `main` saknar INV-DATA-006/007 och maskeringen före Jev och
  inbäddningarna (de ligger i release-PR 72).

---

## GDPR: 18 öppna krav

| Krav | Status | Klass | Vad som krävs för uppfyllt | Agentens del | Gjort |
|---|---|---|---|---|---|
| AG-1 | delvis | b | Beslut a signerat, dataskyddsadress | – | – |
| AG-2 | delvis | b, c | DPA:er signerade (Railway, ScrapeGraph), PUB med kund, radering hos TypeSafe | Utkasten finns | – |
| AG-4 | delvis | b | Beslut b signerat | – | – |
| DS-1 | delvis | b | Merge av PR 72, beslut f | Spärrarna byggda | – |
| DS-2 | delvis | b | Gallringsperiod, `GALLRING_AKTIV`, Redis Cloud raderad, spegeln minimerad | Gallringen byggd och testad i CI | – |
| DS-3 | saknas | b | Utbildning hållen och kvitterad | Material finns | – |
| DS-4 | delvis | c | Juristgranskning, kundens beslut om DPIA | – | – |
| DS-5 | delvis | b | Incidentposterna bedömda, övning hållen | Övervakningens schema bör utredas | Fyndet dokumenterat |
| LBT-1 | delvis | b | Lagringstider beslutade | Åtkomstkolumn per datamängd | **Ja**: `datamangder.md` (alla 97 tabeller, roller, RLS, gallring i dag, föreslagen lagringstid) |
| LBT-2 | delvis | c | Juristgranskning av intresseavvägningen | – | – |
| LBT-3 | delvis | b, c | Merge av PR 72, gallring påslagen, org.nr, jurist | – | – |
| PR-1 | delvis | b | Rutinen signerad, loggen upplagd, `integritet@` | Provkörning av skriptet | **Ja**: provkört mot hela schemat i CI |
| PR-2 | delvis | b | Rutinen signerad | – | – |
| PR-3 | delvis | b | Rutinen, radering av gamla stacken | Provkörning av `--radera` | **Ja**: i CI, med kontroll av spärrlistan och grannraden |
| PR-4 | delvis | b | Merge av PR 72 och denna, rutin | Teknisk spärrmarkering går att bygga, men når inte drift utan merge | **Ja**: migration 124, `gdpr_radera.py --begransa/--hav-begransning`, spärr i sändningen och inkorgen, provkört i CI |
| PR-5 | delvis | b | Merge av PR 72, rutin | Provkörning av `--export` | **Ja**: i CI |
| PR-6 | delvis | b | Rutin för invändning mot annan behandling | – | – |
| PR-7 | delvis | b, c | Merge av PR 72, jurist | – | – |

## ISO 27001: 111 öppna krav

### Klausul 4–10

| Krav | Status | Klass | Vad som krävs | Agentens del | Gjort |
|---|---|---|---|---|---|
| 4.1 | delvis | b | Beslutad kontextbeskrivning | Utkast i P07 | – |
| 4.2 | delvis | b | Intressentlista beslutad | Kan sammanställas | **Ja**: utkast `intressenter.md` |
| 4.3 | saknas | b | Beslut e | – | – |
| 4.4 | saknas | b | Beslutat ledningssystem | – | – |
| 5.1 | delvis | b | Skrivet åtagande | – | – |
| 5.2 | saknas | b | Godkänd P07 | – | – |
| 5.3 | delvis | b | Beslut a | – | – |
| 6.1.1 | delvis | b | Riskmetod | – | – |
| 6.1.2 | delvis | b | Metod och acceptansnivå | Riskutkast per AI-steg | **Ja** (`ai-system/*.md` avsnitt 8) |
| 6.1.3 | delvis | b | SoA och behandlingsplan beslutade | – | – |
| 7.1 | delvis | b | Tid och budget | – | – |
| 7.2 | saknas | b | Kompetenskrav och förteckning | – | – |
| 7.3 | saknas | b | Genomgång och kvittens | – | – |
| 7.4 | delvis | b | Kommunikationsplan | – | – |
| 7.5.1 | delvis | b | Beslutade styrdokument | – | – |
| 7.5.2 | delvis | b | Godkännande av dokumenten | `docs/compliance/` versionshanteras nu | Gap minskat |
| **7.5.3** | delvis | **a** | Åtkomststyrd lagringsplats med versionshantering | Belägga privat repo och medarbetare | **Uppfyllt** |
| 8.1 | delvis | b | Drift planerad utifrån riskbehandling | – | – |
| 8.2 | saknas | b | Riskbedömning med intervall | – | – |
| 8.3 | saknas | b | Godkänd behandlingsplan | – | – |
| 9.1.1 | saknas | b | Beslutade mått | Mäta det som går | **Delvis** (mätt, inte beslutat) |
| 9.1.2 | delvis | b | Intervall för utvärdering | Den här planen | – |
| 9.2 | saknas | c | Internrevision av tredje person | – | – |
| 9.3 | saknas | b | Ledningens genomgång | – | – |
| 10.1 | delvis | b | Incidentposter bedömda | – | – |
| 10.2 | delvis | b | Förbättringsplan | – | – |

### A.5 Organisatoriska

| Krav | Status | Klass | Vad som krävs | Agentens del | Gjort |
|---|---|---|---|---|---|
| A.5.1 | saknas | b | Godkända policyer | – | – |
| A.5.2 | delvis | b | Beslut a | – | – |
| A.5.3 | delvis | b | Kompenserande kontroll för två personer; grenskydd kräver betald plan | – | Fynd: grenskyddet på main gäller inte längre |
| A.5.4 | saknas | b | Godkänd policy | – | – |
| A.5.5 | delvis | b | Kontaktlista IMY, CERT-SE, polis | Listan går att skriva, men vem som ringer är ett beslut | **Ja**: utkast `myndighetskontakter.md`, "vem kontaktar" tom; myndigheterna kontrollerade mot källan 2026-11-18 (CERT-SE:s nummer var fel) |
| A.5.6 | saknas → **delvis** | b | Prenumeration på CERT-SE m.fl. med mottagare | Ett bevakningsflöde går att bygga; vem som läser är ägarens | **Ja**: `sakerhetsbevakning.yml` (CERT-SE och GitHubs advisories för stacken, ärende vid träff, reserv och dödmanskontroll). Mottagare obeslutad |
| A.5.7 | delvis | b | Rutin för att läsa larmen | – | Dependabot-läget uppdaterat (2 höga, ingen rättning finns) |
| **A.5.8** | delvis | **a** | Fast säkerhetsfråga i varje arbete | PR-mall och CI-grind | **Uppfyllt** (INV-PROC-001) |
| A.5.9 | delvis | b | Datorer, telefoner och konton med ägare | Driftens tillgångar | **Ja**: `drift-och-tillgangar.md` §1–2 |
| A.5.10 | delvis | b | Godkänd P13 | – | – |
| A.5.11 | saknas | b | Avslutsrutin | – | – |
| A.5.12 | delvis | b | Godkänd G02 | – | – |
| A.5.13 | delvis | b | Godkänd G02 | – | – |
| A.5.14 | delvis | b | Synkflytten (Railway) | Koden finns (PR 71) | – |
| A.5.15 | delvis | b | Regler för leverantörskonton | RLS verifierat i CI; minsta rättighet för `snajp_web` | **Ja** (gap om RLS-verifiering minskat; PR 91, migration 126) |
| A.5.16 | delvis | b | Personliga konton i stället för delade | – | – |
| A.5.17 | delvis | b | Lösenordsbyte, lösenordshanterare | Tvåfaktorhemligheten krypterad, återställningskoder hashade | **Ja** (PR 93, migration 128) |
| A.5.18 | delvis | b | Förteckning och översyn | GitHub-delen belagd | **Ja** (`bevis/github-2026-11-18.txt`) |
| A.5.19 | delvis | b | Policy och beslut f | – | – |
| A.5.20 | delvis | b, c | DPA:er, breven skickade | – | – |
| A.5.21 | delvis | b | Patchtider beslutade; avfärda de två picomatch-larmen | – | Läget uppdaterat |
| A.5.22 | delvis | b | Återkommande granskning | – | – |
| A.5.23 | delvis | b | Exitplan, DPA, radering av gamla stacken | – | – |
| A.5.24 | delvis | b | Övning hållen | – | – |
| A.5.25 | saknas | b | Incidentposter bedömda | – | – |
| A.5.26 | delvis | b | Lösenordsbyte, raderingsbegäran | – | – |
| A.5.27 | delvis | b | Genomgång dokumenterad | – | – |
| A.5.28 | saknas | b | Rutin för att säkra loggar | Railways loggtid belagd | **Ja**: 3/7/30 dagar per plan (`drift-och-tillgangar.md` §5) |
| A.5.29 | saknas | b | Kontinuitetsplan | – | – |
| A.5.30 | saknas | b | Railway Pro, RTO/RPO | – | – |
| A.5.31 | delvis | b, c | Godkänd G01, signerat PUB | – | – |
| A.5.32 | delvis | b | Avtal med allabolag och hitta; beslut om de obeslutade licenserna | Licensförteckning över beroenden | **Ja**: `scripts/licenser.py`, `licenser.md`, CI-jobbet `licenser` med vitlista (18 poster obeslutade) |
| A.5.33 | delvis | b | Lagringstider för egna register | – | – |
| A.5.34 | delvis | b | Som GDPR | – | – |
| A.5.35 | saknas | c | Oberoende granskning | – | – |
| A.5.36 | saknas | b | Godkända policyer | – | – |
| A.5.37 | delvis | b | Rutin för säkerhetskopiering (kräver kopior) | `AUTH.md` inaktuell | **Ja**: `AUTH.md` skriven om mot koden (Auth.js, nycklar, roller) |

### A.6 Personal

| Krav | Status | Klass | Vad som krävs | Gjort |
|---|---|---|---|---|
| A.6.1 | saknas | b | Kontroll eller beslutat undantag | – |
| A.6.2 | okänt | b | Sebbes avtal | – |
| A.6.3 | saknas | b | Genomgång och kvittens | – |
| A.6.4 | okänt | b | Sebbes avtal | – |
| A.6.5 | okänt | b | Sebbes avtal | – |
| A.6.6 | okänt | b | Sekretessavtal | – |
| A.6.7 | delvis | b | Regler för distansarbete | – |
| A.6.8 | delvis | b | Privat sårbarhetsrapportering (inställning), svarstid i `SECURITY.md`, merge av PR 72 | – |

### A.7 Fysiska (bara de öppna)

| Krav | Status | Klass | Vad som krävs |
|---|---|---|---|
| A.7.7–A.7.10, A.7.13 | okänt | b | Uppgifter om datorerna (skärmlås, förvaring, diskkryptering, media, service) |
| A.7.14 | saknas | b | Rutin för radering av utrustning |

### A.8 Tekniska

| Krav | Status | Klass | Vad som krävs | Agentens del | Gjort |
|---|---|---|---|---|---|
| A.8.1 | okänt | b | Enhetslista | – | – |
| A.8.2 | delvis | b | Lösenordsbyte, admins listade | GitHub-admins belagda; webbens roll smalnad av | Ja (PR 91) |
| A.8.3 | delvis | b | Minimerad spegel, merge till `main` | RLS verifierat i CI; `auth.users` stängd för PUBLIC, `snajp_web` minsta rättighet | **Ja** (PR 91) |
| A.8.4 | delvis | b | Grenskydd (betald plan), koppla bort Supabase-appen | Åtkomsten belagd | **Ja** (repot privat; nytt gap: grenskyddet) |
| A.8.5 | delvis | b | Beslut om tvång, tvåfaktor på leverantörskonton; merge till `main` | Spärr mot upprepade försök; valfri TOTP för plattformsadmin | **Ja** (PR 90, migration 125; PR 93, migration 128) |
| A.8.6 | delvis | b | Kapacitetsövervakning, repliker | – | – |
| A.8.7 | okänt | b | Antivirus på datorerna | – | – |
| A.8.8 | delvis | b | Patchtider, kodskanning (kräver betald plan) | – | Läget uppdaterat |
| A.8.9 | delvis | b | Logg över Railway-ändringar; rutin för när baslinjen körs | Baslinjen i bevis | **Ja**: `scripts/railway_baslinje.py` (`--skriv`, `--jamfor`), `railway-baslinje.json`; `--jamfor` 2026-11-18 19:10 UTC: 0 avvikelser |
| A.8.10 | delvis | b | Gallring påslagen | Raderingen provkörd | **Ja** (CI) |
| A.8.11 | delvis | b | Merge av PR 72 | – | – |
| A.8.12 | delvis | b | Synkflytten, mönster för lösenord | Synkloggens innehåll (P20) | Läget uppdaterat; synkloggen granskad i koden (se Uttömt) |
| A.8.13 | saknas | b | Railway Pro | – | – |
| A.8.14 | saknas | b | Tillgänglighetskrav | – | – |
| A.8.15 | delvis | b | Gallring av `agent_runs`; åtkomstloggen i `main` (merge) | Loggningen beskriven med belägg; åtkomstlogg för admin (PR 85); kvittotexten ur `agent_runs` (PR 83) | **Ja** (`drift-och-tillgangar.md` §5) |
| A.8.16 | delvis | b | Internlarmets variabler; extern pingtjänst | Orsaken utredd, reserv och dödmanskontroll | **Ja** (PR 84) |
| A.8.17 | okänt | b | Tidssynk på datorerna | – | – |
| A.8.18 | delvis | b | Vem som har Railway-token och psql; beslutad behörighet | Verktygslistan | **Ja**: `privilegierade-verktyg.md` (vägar, skript per grupp, förslag) |
| A.8.19 | delvis | b | Regler för programvara på datorerna | – | – |
| A.8.20 | delvis | b | Stäng Postgres publika proxy (Railway) | – | – |
| A.8.21 | delvis | b | HSTS i drift kräver merge till main | HSTS-raden och mätningen | **Ja**: TLS och HSTS mätta (`bevis/tls-2026-11-18.txt`); HSTS i `next.config.ts`, i `development` |
| A.8.22 | delvis | b | Synkflytten | – | – |
| A.8.23 | delvis | b | Webbskydd på datorerna | – | – |
| A.8.24 | delvis | b | Nyckelrotation, spegelns nycklar | TLS-versioner mätta | **Ja**: TLS 1.0 och 1.1 vägras, 1.2 och 1.3 tas emot på alla publika adresser |
| A.8.25 | delvis | b | Deploy först när CI är grön (Railway), grenskydd | – | – |
| A.8.26 | delvis | b | Merge av PR 72 | – | – |
| A.8.27 | delvis | b | Stäng publika proxyn | RLS i CI | Ja |
| A.8.28 | delvis | b | Lösenordsbyte; kodskanning | – | – |
| **A.8.29** | delvis | **a** | Säkerhetstester i varje ändring | RLS och rättighetsskriptet i CI | **Uppfyllt** |
| A.8.30 | delvis | b | Sebbes avtal, AI-kodverktygens åtkomst | – | – |
| A.8.31 | delvis | b | Minimerad spegel, egna Vertex-konton | – | – |
| A.8.32 | delvis | b | Granskning före merge, logg över Railway-ändringar | PR-frågan i CI | Ja (gap minskat) |
| A.8.33 | delvis | b | Minimerad spegel | – | – |
| A.8.34 | delvis | b | Regel för revisioners åtkomst, överenskommen med ägaren | – | – |

## ISO 42001: 69 öppna krav

| Krav | Status | Klass | Vad som krävs | Agentens del | Gjort |
|---|---|---|---|---|---|
| 4.1 | delvis | b | Beslutad AI-kontext | Systembladen | Ja |
| 4.2 | delvis | b | Intressentregister beslutat | Sammanställning | **Ja**: utkast `intressenter.md` (AI-kraven ingår) |
| 4.3 | saknas | b | Beslut e | – | – |
| 4.4 | saknas | b | Beslutat AI-ledningssystem | – | – |
| 5.1 | delvis | b | Åtagande | – | – |
| 5.2 | saknas | b | Godkänd P27 | – | – |
| 5.3 | saknas | b | Roller tilldelade | – | – |
| 6.1.1 | delvis | b | Riskkriterier | – | – |
| 6.1.2 | delvis | b | Metod, godkännande | Riskutkast per AI-steg | **Ja** |
| 6.1.3 | delvis | b | Behandlingsplan, SoA | – | – |
| 6.1.4 | delvis | b | Beslutad process | Jev bedömd | **Ja** |
| 6.2 | delvis | b | AI-mål | – | – |
| 6.3 | delvis | b | Beslut f, ersättare för 2.5 | `KVITTO_MODEL` förberedd | **Ja** |
| 7.1 | delvis | b | Resurser | – | – |
| 7.2 | saknas | b | Kompetens | – | – |
| 7.3 | saknas | b | Genomgång | – | – |
| 7.4 | delvis | b | Kommunikationsplan, merge av PR 72 | – | – |
| 7.5.1 | delvis | b | Beslutade dokument | Systembladen | Ja |
| 7.5.2 | delvis | b | Godkännande | – | – |
| **7.5.3** | delvis | **a** | Åtkomststyrd lagring | Belägga | **Uppfyllt** |
| 8.1 | delvis | b | Beslut f, merge av PR 72 | – | – |
| 8.2 | delvis | b | Intervall och utlösare | Riskutkast | Ja |
| 8.3 | delvis | b | Godkänd plan | – | – |
| 8.4 | delvis | b | Intervall | Jev och webbpoolen bedömda | **Ja** |
| 9.1 | delvis | b | Mätning av AI-kvalitet i drift, internlarm | Evalresultat samlade | Ja |
| 9.2.1, 9.2.2 | saknas | c | Internrevision av tredje person | – | – |
| 9.3.1–9.3.3 | saknas | b | Ledningens genomgång | – | – |
| 10.1 | delvis | b | Förbättringslogg | – | – |
| 10.2 | delvis | b | AI-fel i incidentloggen, uppföljning | Ärendemallen | Ja |
| A.2.2 | delvis | b | Godkänd P27 | – | – |
| A.2.3 | saknas → **delvis** | b | Godkänd P27 och beslut om förslagen; genomgången upprepad mot de godkända versionerna | Genomgången som utkast | **Ja**: `ai-system/policy-samstammighet.md` |
| A.2.4 | saknas | b | Policy att se över | – | – |
| A.3.2 | delvis | b | Roller | – | – |
| A.3.3 | saknas | b | Skydd för den som anmäler (P28) | Anmälningsväg | **Delvis** (`ai-oro.yml`) |
| **A.4.2** | delvis | **a** | Förteckning per system och livscykelsteg | Systembladen | **Uppfyllt** |
| A.4.3 | delvis | b | Lagringstider per datamängd | Data in och ut per system; förslag per tabell | Ja (`datamangder.md`) |
| A.4.4 | delvis | b | Godkännande per modell, ersättare för 2.5 | Version och plats per steg | Ja |
| **A.4.5** | delvis | **a** | Beräkningsresurser dokumenterade | Systembladen, tillgångsförteckningen | **Uppfyllt** |
| A.4.6 | saknas | b | Systemägare utsedda | – | – |
| A.5.2 | delvis | b | Beslutad process | – | – |
| A.5.3 | delvis | c | Juristgranskning | – | – |
| A.5.4 | delvis | b | Godkänd bedömning; mätning av skevhet | Jev bedömd | **Ja** |
| A.5.5 | saknas | b | Godkänd bedömning | Utkast | **Delvis** (`samhallspaverkan.md`) |
| A.6.1.2 | delvis | b | Mål med mått | – | – |
| A.6.1.3 | delvis | b | Granskning före deploy av development | PR-frågan om AI i CI | Ja (gap minskat) |
| A.6.2.2 | delvis | b | Godkända krav | Krav beskrivna per system | Ja |
| **A.6.2.3** | delvis | **a** | Designdokumentation för alla system | Systembladen | **Uppfyllt** |
| A.6.2.4 | delvis | b | Godkänd releasegräns per agent | – | – |
| A.6.2.5 | delvis | b | Driftsättningsplan; grenskydd | Upptäckt av ändrade AI-variabler | Fynd: code owner tvingar inte längre. Gap minskat: baslinjen visar `INKORG_JEV`, `IRIS_JEV`, `LLM_PROVIDER`, `*_MODEL` per miljö, 0 avvikelser 2026-11-18 |
| A.6.2.6 | delvis | b | Internlarm, kvalitetsmätning i drift | – | Fynd: schemat körs inte |
| A.6.2.7 | delvis | b | Dokumentationen anpassad och lämnad till kund och tillsyn: vad som lämnas ut är ägarens val | Teknisk dokumentation per system | Ja (gap minskat) |
| A.7.2 | delvis | b | Beslutad process; Livrustnings godkännande | – | – |
| A.7.3 | delvis | b | Avtal med allabolag och hitta | – | – |
| A.7.4 | delvis | b | Kvalitetskrav per system | – | – |
| A.7.5 | delvis | b | Merge av PR 72 (migration 117) | – | – |
| A.7.6 | delvis | b | Merge av PR 72 | – | – |
| A.8.2 | delvis | b | Merge av PR 72 | – | – |
| A.8.3 | delvis | b | Uttalad väg för AI-fel utåt | – | – |
| A.8.4 | delvis | b | AI-incidenter i rutinen | – | – |
| A.8.5 | delvis | b | Beslutad lista | – | – |
| A.9.2 | delvis | b | Procedur för egen AI-användning | Mänsklig översyn per system | Ja |
| A.9.3 | delvis | b | Mål med mått | – | – |
| A.9.4 | delvis | b | Förbjudna användningar i villkoren | Avsedd användning per system | Ja |
| A.10.2 | delvis | b | Ansvarsfördelning, granskade villkor | – | – |
| A.10.3 | delvis | b | Beslut f, TypeSafe | – | – |
| A.10.4 | delvis | b | Process för kundens förväntningar | – | – |

## Det som återstår för Anton, i den ordning det flyttar flest krav

1. **Signera ledningssystemet** (beslut a och e, P07, P27, policyerna, SoA): cirka 19 krav.
2. **Merga release-PR 72**: tar bort gapet "inte i drift" i ungefär 20 krav.
3. **GitHub-plan:** gratisplanen i ett privat repo saknar grenskydd, kodskanning och
   hemlighetsskanning. Antingen en betald plan eller ett beslut om kompenserande kontroll.
4. **Övervakningen:** orsaken är utredd och reserven byggd (PR 84). Kvar för ägaren: sätt
   `INTERNLARM_SMTP_*`, och välj om en extern pingtjänst ska väcka övervakningen när
   ingen push, PR eller synk sker.
5. Resten enligt `BESLUTSUNDERLAG-2026-11-17.md` (enhetslistan, konton och tvåfaktor,
   utbildning, incidentövning, Railway Pro, leverantörerna, juristen).

## Leverans

PR mot `development` från grenen `compliance/score-2026-11-18`. CI-jobbet `databas` är
beviset för A.8.29 och för provkörningen av rättighetsskriptet.

## Natt 2026-11-18: de tre fynden åtgärdade

| PR | Fynd | Vad som gjordes | Belägg |
|---|---|---|---|
| 83 | Kvittotext i `agent_runs` | Den äldre bokföringsytan sparar bara längd, sha256 och underlagets id, och stegloggen utan text | `tests/bookkeeping/test_kvittotext_logg.py`; `ai-system/bokforingschatt.md` §4; DPIA R10 |
| 84 | Övervakningens schema | Orsak: GitHubs schemaläggare tappar schemalagda körningar i repot (synk.yml cirka 4 av 144 om dygnet), inte syntax, privat repo eller minuter. Två scheman på mindre belastade minuter, reserv efter Verify och synk, dödmanskontroll i `verify.yml` | `.github/workflows/overvakning.yml` (kommentaren), `scripts/overvakning_dodman.sh` |
| 85 | Ingen åtkomstlogg för admin | En rad i `audit_logs` per master-nyckelanrop och kundbesök (vem, när, åtgärd, kund, resurs; inget innehåll), skrivskyddad för approllerna, gallras efter 365 dagar | Migration 123; INV-SEC-013; `tests/db/test_adminlogg.py` i jobbet `databas`; `drift-och-tillgangar.md` §5 |

**Poäng före och efter:** oförändrad. GDPR 0/17/1, ISO 27001 3/72/24, ISO 42001 5/51/14
(uppfyllt/delvis/saknas). Koden ligger i `development` och räknas därför som testmiljö
(statusreglerna), och de berörda kraven (A.8.15, A.8.16, A.5.15, A.5.18, DS-2, DS-5, ISO 42001
9.1 och A.6.2.6) hänger dessutom på ägarens del: gallringsperioden för `agent_runs`,
internlarmets variabler och översyn av åtkomsten. Gapen är mindre och skrivna så i matriserna
("ändr. 11-18d"). A.8.15 blir uppfyllt när release-PR:en med migration 123 är mergad och
`agent_runs` har en beslutad gallring.

## Agentens delar av ägarens krav (2026-11-18, sen kväll)

Allt som återstår kräver Anton. Här är de delar agenten kunde bygga så att det som återstår
är ett beslut eller en signatur. Grenen `compliance/agentdelar-2026-11-18`, PR 86 mot `development`.

| Krav | Byggt | Belägg | Kvar för Anton |
|---|---|---|---|
| GDPR LBT-1 (och ISO 42001 A.4.3, ISO 27001 A.5.33) | Förteckning över alla 97 tabeller i 12 datamängder: innehåll, roller och RLS ur migrationerna, vem som ser vad, vad som gallras i dag, föreslagen lagringstid | `datamangder.md` | Besluta lagringstiderna; fynden om breda rättigheter (`snajp_web`, `auth.users`) |
| GDPR PR-4 | Spärrmarkering för begränsning av behandling: tabell `behandlingsbegransningar` (migration 124, additiv, approllerna läser men skriver inte), `gdpr_radera.py --begransa SKÄL` och `--hav-begransning SKÄL` (bekräftelse), sändningsspärren blockerar utskick till adressen hos alla kunder, inkommande mejl går till Att hantera utan AI. Spärren stoppar också när listan inte går att läsa | `tests/test_behandlingsbegransning.py`; `tests/db/test_gdpr_radera_db.py` i jobbet `databas`; `tests/test_gdpr_radera.py` körs nu i CI | Signera rutinen; merga releasen till `main`. Research och utkast som redan finns stoppas inte av koden: skriptet uppmanar handläggaren att arkivera berörda leads |
| ISO 27001 4.2, ISO 42001 4.2 | Intressenter, deras krav, hur Snajp möter dem och vad som är öppet | `intressenter.md` (utkast) | Besluta listan och översynen |
| A.5.5 | Kontaktlista: IMY, CERT-SE, polisen, kunden, leverantörernas kanaler | `myndighetskontakter.md` (utkast) | Vem kontaktar; kontrollera uppgifterna mot källan; leverantörernas säkerhetskontakter |
| A.5.6 | Schemalagd bevakning av CERT-SE och GitHubs advisories för paketen i stacken, ärende med etiketten `sakerhetsbevakning` vid träff, dedup, två scheman, reserv efter Verify och synk, dödmanskontroll (`sakerhetsbevakning-tyst`) | `.github/workflows/sakerhetsbevakning.yml`, `.github/sakerhetsbevakning.json`, `scripts/sakerhetsbevakning.py`, `tests/test_sakerhetsbevakning.py` | Vem läser ärendena och inom vilken tid |
| A.5.32 | Licensförteckning över npm (web, support-webb) och pip (backend, skript), CI-jobb som fäller på copyleft och okända licenser utanför vitlistan | `scripts/licenser.py`, `licenser.md`, `licenser-vitlista.json`, jobbet `licenser` i `verify.yml` | Godkänna eller avvisa de 18 obeslutade posterna (sharp/libvips LGPL, gsap egen licens, certifi och tqdm MPL, psycopg2-binary LGPL); avtal med allabolag och hitta |
| A.5.37 | `AUTH.md` beskriver nu det som körs: Auth.js med scrypt och JWT, återställning via token, roller, backendens nycklar | `AUTH.md` | Rutinen för säkerhetskopiering (kräver kopior) |
| A.8.9 | Konfigurationsbaslinje för Railway: per miljö och tjänst källa, gren, bygge, start, region, repliker, hälsokontroll, domäner, TCP-proxy, volymer och variabelnamn; värden bara för en vitlista av ofarliga namn. `--jamfor` visar avvikelser | `scripts/railway_baslinje.py`, `railway-baslinje.json`, `tests/test_railway_baslinje.py` | Rutin: `--jamfor` före och `--skriv` efter varje ändring. Ändrade hemligheter syns inte (inga värden sparas) |
| A.8.18 | Förteckning över åtkomstvägarna (ägarrollen, Railway-API, GitHub, master-nyckeln m.fl.) och skripten per grupp, med förslag om vem som får köra vad | `privilegierade-verktyg.md` | Besluta förslaget; belägga medlemmarna i Railway och Google Cloud |

**Statusändring:** en. ISO 27001 **A.5.6 saknas → delvis**: bevakningen körs från
standardgrenen och är alltså igång när PR:en är mergad, men ingen är utsedd att läsa ärendena.
Inget krav blir uppfyllt: varje rad ovan väntar på ett beslut eller en merge till `main`.

**Poäng före och efter:** GDPR 0/17/1 → 0/17/1. ISO 27001 3/72/24 → **3/73/23**.
ISO 42001 5/51/14 → 5/51/14 (uppfyllt/delvis/saknas).

## Natt 2026-11-18 (f): inloggningsspärr och webbens databasrättigheter

| PR | Krav | Byggt | Belägg | Kvar för Anton |
|---|---|---|---|---|
| 90 | A.8.5 | Spärr mot upprepade lösenordsinloggningar och återställningsbegäranden, per adress (5 på 15 min, 3 på 60 min) och per IP (20 resp. 10), väntetid 1, 5, 15, 60 min. Avslöjar inte om kontot finns; spärrade försök loggas utan lösenord. TOTP för plattformsadmin inte byggd (för stort i samma veva, `docs/BESLUT.md`) | Migration 125; `lib/auth/inloggningsregler.ts`; `snajp-support/tests/db/test_inloggningsforsok.py` i jobbet `databas`; `AUTH.md` | Besluta tvåfaktor (krav och tvång); merge till `main` |
| 91 | A.5.15, A.8.2, A.8.3 | `snajp_web` från LIUR på 97 tabeller (och automatiskt på nya) till det webbens 67 SQL-satser gör: 13 tabeller, kolumnvis där det går. `auth.users` inte längre läsbar för PUBLIC; `snajp_app` läser bara `id, email` | Migration 126; `snajp-support/tests/db/test_snajp_web_rattigheter.py` (exakt lista, nya tabeller, `auth.users`, varje webbsats som `snajp_web` med EXPLAIN, kontrollprov); `datamangder.md` §1 och fynd 3 | Merge till `main`; åtkomstgranskningen |

**Statusändring:** ingen. Koden ligger i `development` och räknas som testmiljö
(statusreglerna), och varje krav har en del som är ägarens (tvåfaktor på konton, regler för
leverantörskonton, listan över admins, minimerad spegel).

**Poäng före och efter:** GDPR 0/17/1 → 0/17/1. ISO 27001 3/73/23 → 3/73/23. ISO 42001
5/51/14 → 5/51/14 (uppfyllt/delvis/saknas).

## Natt 2026-11-18 (g): demofelet och tvåstegsverifiering

| PR | Krav | Byggt | Belägg | Kvar för Anton |
|---|---|---|---|---|
| 92 | A.8.2 (minsta rättighet) | `startDemo` märker arbetsytan `is_demo` genom `markera_demoarbetsyta()` med användarens identitet; webbens update-rätt på `workspaces.is_demo` borttagen | Migration 127; `snajp-support/tests/db/test_demo_markering.py` och `TILLATET` i `test_snajp_web_rattigheter.py` (jobbet `databas`) | – |
| 93 | A.8.5, A.5.17 | Valfri TOTP för plattformsadmin: QR och manuell nyckel, tio engångskoder (hashade), andra steget i `authorize` under samma spärr som lösenordet, återspelningsskydd, avstängning bara med giltig kod, hemligheten krypterad (AES-256-GCM, HKDF ur `AUTH_SECRET`), OAuth nekas för konton med tvåfaktor. Tvånget är en flagga, av | Migration 128; `lib/auth/totp.test.ts` (RFC 6238), `tvafaktor-krypto.test.ts`, `inloggningssteg.test.ts`; `snajp-support/tests/db/test_tvafaktor.py` (jobbet `databas`); lokal genomgång av adminytan och hela tvåfaktorflödet; `AUTH.md` | Besluta tvånget för plattformsadmin (`TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN`); slå på tvåfaktor på det egna adminkontot efter releasen; merge till `main` |

**Statusändring:** ingen. A.8.5 kräver också tvåfaktor på leverantörskontona och ett beslut
om tvånget, A.5.17 lösenordsbyte och lösenordshanterare, och koden räknas som testmiljö tills
den är i `main`.

**Poäng före och efter:** GDPR 0/17/1 → 0/17/1. ISO 27001 3/73/23 → 3/73/23. ISO 42001
5/51/14 → 5/51/14 (uppfyllt/delvis/saknas).

## Kväll 2026-11-18 (h): tvåstegsverifieringen provad i `development`

PR 93 provad end-to-end i Railway-miljön `development` (spegel av produktionen) med ett
syntetiskt konto (`@example.com`) som fick adminrätt i `platform_admins` 18:54:21 UTC och miste
den 18:58:37 UTC. Webbläsaren gick bara till `/settings/tvafaktor` och inloggningssidan. Nyckel,
lösenord och återställningskoder lämnade aldrig webbläsaren och ett lokalt relä på `127.0.0.1`.

| Steg | Utfall |
|---|---|
| Inrullning | Fel kod vägrades ("Koden stämmer inte"), rätt kod (RFC 6238 ur den manuella nyckeln) godtogs, tio återställningskoder visades en gång |
| Inloggning med lösenord | Andra steget visades, ingen session efter bara lösenordet |
| Andra steget | Fel kod vägrades utan session; rätt app-kod släppte in |
| Återställningskod | Släppte in i en ny inloggning (oanvända 10 → 9); samma kod en gång till vägrades |
| Avstängning | Fel kod vägrades; giltig kod stängde av ("Tvåstegsverifieringen är avstängd.") |
| Återställning | Kontot ur `platform_admins`; 0 rader i `tvafaktor` och `tvafaktor_aterstallningskoder` (SQL); utloggad, webbläsaren stängd |
| Web-loggen | Fem `CredentialsSignin` (tre för "andra steget krävs", två för vägrade koder), inget "permission denied", inga fel från tvåfaktorns actions |
| `audit_logs` | Tvåfaktorflödet skriver inte där (migration 123 loggar master-nyckeln och kundbesök). En rad (`master`, `GET /api/admin/tenants`) kom från en omdirigering till `/admin` innan provet, eftersom webbläsaren redan var inloggad |

**Statusändring:** ingen. Provet visar att koden fungerar i en driftlik miljö; kraven förblir
delvis av skälen i (g). Kvar för Anton: tvånget, egen inrullning efter releasen, `main`.
Om inloggning, avstängning och inrullning ska stå i `audit_logs` är ett eget beslut (i dag
bara web-loggen).

**Poäng före och efter:** GDPR 0/17/1 → 0/17/1. ISO 27001 3/73/23 → 3/73/23. ISO 42001
5/51/14 → 5/51/14 (uppfyllt/delvis/saknas).

## Uttömt 2026-11-18

Sista genomgången. Varje rad ovan där kolumnen "Agentens del" har innehåll eller klassen
är b eller c lästes med frågan: finns det arbete en agent kan göra nu, utan Antons
beslut, som minskar gapet med verkligt belägg (inte ytterligare en policytext utan
förankring)? Tidsram cirka 45 minuter. Gränserna för omgången: ingen ändring i `main`,
ingen skrivning till Supabase, inga Railway-variabler, inga kunddata, inga mejl.

### Gjort i omgången

| Krav | Gjort | Belägg |
|---|---|---|
| ISO 42001 **A.2.3** | Genomgången av P27 mot G01–G06, P07–P26 och P28: var de möts, 6 krockar, 19 glapp, inaktuella fakta i 13 policyer, förslag per policy och samlat. Påståendena om läget kontrollerade mot kod, CI och baslinjen. Utkast som gäller när P27 är godkänd | `ai-system/policy-samstammighet.md`; matrisen A.2.3 **saknas → delvis**; uppgift 20 `in_progress` |
| ISO 27001 A.8.21, A.8.24 | TLS-versioner och HSTS mätta på webb, api och agentsajt i båda miljöerna, `www.snajp.se` och `snajp.se`. TLS 1.0 och 1.1 vägras överallt. HSTS saknades på allt som Railway serverar; rubriken läggs nu på av appen (`next.config.ts`, två år, utan `includeSubDomains`) | `bevis/tls-2026-11-18.txt`; i `development` efter deployen, i `main` med releasen |
| ISO 27001 A.8.9, ISO 42001 A.6.2.5, 6.3 | `railway_baslinje.py --jamfor` kört mot driften: 0 avvikelser sedan 16:21 UTC. Baslinjen visar AI-variablerna per miljö, så ett obeslutat byte av modell eller leverantör syns vid nästa jämförelse | Körningen 2026-11-18 19:10 UTC (bara läsning) |
| ISO 27001 A.5.5 | IMY:s, CERT-SE:s och polisens uppgifter kontrollerade mot deras egna sidor. CERT-SE:s nummer i utkastet var fel (rätt: 010-382 80 00) | `myndighetskontakter.md`, kolumnen "Kontrollerad" |
| ISO 27001 A.8.12 (P20) | Synkloggen, som sparas som artefakt i 14 dagar, granskad i koden: den skriver tabellnamn, primärnyckel och första raden av ett Postgres-fel, aldrig radinnehåll (`scripts/railway_synk.py` rad 414, 456, 745). Ingen synkad tabell har e-post som primärnyckel. Kvar: en felrad av typen "invalid input syntax" kan bära ett enskilt värde | Koden; artefakterna lästes inte (kunddata) |

Prövat och lagt ner: att visa `LEADS_DAILY_TOKEN_BUDGET` i baslinjen. Namnet innehåller
`TOKEN`, och skriptets spärr mot hemlighetsnamn (`_ALDRIG`) ska inte luckras upp för det.

**Statusändring:** en. ISO 42001 A.2.3 saknas → delvis.

**Poäng före och efter:** GDPR 0/17/1 → 0/17/1. ISO 27001 3/73/23 → 3/73/23. ISO 42001
5/51/14 → **5/52/13** (uppfyllt/delvis/saknas).

### Det som inte gick, per rad

"Ä" = kräver Anton. "Ext." = kräver en extern part. Raderna är grupperade där skälet är
detsamma; varje krav står utskrivet.

**GDPR**

| Krav | Varför återstoden inte är agentens |
|---|---|
| AG-1, AG-4 | Ä: beslut a och b signeras; `integritet@` är en ny brevlåda i ett konto bara Anton når |
| AG-2 | Ä: DPA:erna signeras (Railway via DocuSign, ScrapeGraph med betald plan); raderingsbegäran till TypeSafe är ett mejl i Snajps namn. Ext.: PUB med kund |
| DS-1, LBT-3, PR-4, PR-5, PR-7 | Ä: merge av release-PR 72 till `main`. Agenten rör inte `main`. LBT-3 och PR-7 dessutom Ext. (jurist) |
| DS-2 | Ä: gallringsperioden beslutas, och `GALLRING_AKTIV` är en Railway-variabel; Redis Cloud raderas i ett konto; spegelns minimering är ett beslut (JA #16) |
| DS-3 | Ä: utbildningen hålls och kvitteras av Anton och Sebbe. Materialet finns |
| DS-4, LBT-2 | Ext.: juristgranskning; DS-4 också kundens beslut om DPIA |
| DS-5 | Ä: incidentposterna bedöms av incidentledaren (G03, roller); övningen kräver deltagarna |
| LBT-1 | Ä: lagringstiderna beslutas. Förslaget per tabell finns (`datamangder.md`) |
| PR-1, PR-2, PR-3, PR-6 | Ä: rutinerna signeras, begäransloggens plats beslutas, `integritet@` skapas; PR-3 också radering av Supabase och Render, som inte går att ångra. Skriptens provkörningar finns redan i CI |

**ISO 27001, klausul 4–10**

| Krav | Varför |
|---|---|
| 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3 | Ä: beslutad kontext, intressentlista, omfång (beslut e), ledningssystem, åtagande, P07 och beslut a. Utkasten finns |
| 6.1.1, 6.1.2, 6.1.3, 8.1, 8.2, 8.3 | Ä: riskmetod, acceptansnivå, SoA och behandlingsplan. Riskutkasten finns; att räkna om dem till P09:s skala hjälper först när skalan är beslutad |
| 7.1, 7.2, 7.3, 7.4, 7.5.1, 7.5.2 | Ä: tid och budget, kompetenskrav, genomgång, kommunikationsplan, godkännande av dokumenten |
| 9.1.1, 9.1.2 | Ä: måtten och intervallen beslutas. Mätningen finns |
| 9.2 | Ext.: internrevision av en tredje person (P10) |
| 9.3, 10.1, 10.2 | Ä: ledningens genomgång, bedömda incidentposter, förbättringsplan |

**ISO 27001, A.5–A.8**

| Krav | Varför |
|---|---|
| A.5.1, A.5.2, A.5.4, A.5.10, A.5.12, A.5.13, A.5.36 | Ä: policyerna och beslut a godkänns |
| A.5.3, A.8.4, A.8.8, A.8.25, A.8.28 | Ä: grenskydd, kodskanning och hemlighetsskanning kräver betald GitHub-plan eller ett beslut om kompenserande kontroll; "deploy först när CI är grön" är en Railway-inställning. A.8.28 också lösenordsbyte |
| A.5.5 | Ä: vem som kontaktar. Ext.: leverantörernas säkerhetskontakter bekräftas av leverantörerna eller i Antons konton |
| A.5.6 | Ä: vem läser bevakningens ärenden och inom vilken tid |
| A.5.7, A.5.21 | Ä: patchtider beslutas; de två picomatch-larmen avfärdas eller accepteras (ingen rättning finns uppströms) |
| A.5.9, A.8.1, A.8.7, A.8.17, A.8.19, A.8.23, A.7.7–A.7.10, A.7.13, A.7.14 | Ä och Sebbe: bara de kan kontrollera sina datorer och telefoner (kryptering, skärmlås, antivirus, tidssynk, programvara, kassering) |
| A.5.11, A.5.16, A.5.17, A.5.18, A.8.2, A.8.5 | Ä: lösenordsbyte, lösenordshanterare, personliga konton och tvåfaktor hos leverantörerna görs i kontona; tvånget för plattformsadmin är ett beslut. Koden (spärr, TOTP) finns |
| A.5.14, A.8.12, A.8.22 | Ä: synkflytten kräver Railway-variabler och att den publika proxyn stängs |
| A.5.15, A.8.18, A.8.34 | Ä: reglerna för leverantörskonton, privilegierade verktyg och revisioners åtkomst beslutas. Förslagen finns |
| A.5.19, A.5.20, A.5.22, A.5.23 | Ä: policy och beslut f, DPA:er, brev till leverantörer, exitplan, radering av gamla stacken. Ext.: leverantörernas svar |
| A.5.24, A.5.25, A.5.26, A.5.27 | Ä: övningen hålls, incidentposterna bedöms, lösenord byts, genomgången skrivs av den som bedömt |
| A.5.28 | Ä: rutin för att säkra loggar beslutas. Loggtiden är belagd |
| A.5.29, A.5.30, A.5.37, A.8.6, A.8.13, A.8.14 | Ä: Railway Pro (betald plan) ger säkerhetskopior och repliker; RTO, RPO och tillgänglighetskrav beslutas |
| A.5.31, A.5.34 | Ä: G01 signeras. Ext.: PUB med kund |
| A.5.32 | Ä: de 18 obeslutade licenserna; avtal med allabolag och hitta. Licensgrinden finns |
| A.5.33 | Ä: lagringstider för egna register |
| A.5.35 | Ext.: oberoende granskning |
| A.6.1–A.6.6 | Ä: Sebbes avtal (sekretess, följder), kontroll eller beslutat undantag, genomgång och kvittens |
| A.6.7 | Ä: regler för distansarbete beslutas |
| A.6.8 | Ä: privat sårbarhetsrapportering är en repoinställning; svarstiden i `SECURITY.md` är ett åtagande; merge av PR 72 |
| A.8.3, A.8.31, A.8.33 | Ä: minimerad eller pseudonymiserad spegel (JA #16), egna Vertex-konton per miljö |
| A.8.9 | Ä: rutinen för när baslinjen körs. Jämförelsen är körd |
| A.8.10 | Ä: `GALLRING_AKTIV` och perioden |
| A.8.11, A.8.26 | Ä: merge av PR 72 |
| A.8.15 | Ä: gallring av `agent_runs` beslutas; adminloggen når drift med releasen |
| A.8.16 | Ä: `INTERNLARM_SMTP_*` är Railway-variabler; en extern pingtjänst kräver ett konto |
| A.8.20, A.8.27 | Ä: Postgres publika proxy stängs i Railway (efter synkflytten) |
| A.8.21 | Ä: HSTS når `main` med releasen. En SSL Labs-rapport görs av den externa tjänsten och tillför bara certifikatkedja och chifferlista |
| A.8.24 | Ä: nyckelrotation (hemligheterna hanteras av Anton). Kryptering av kundnycklarna i testmiljön skriver i kunddata, utanför omgångens gränser |
| A.8.30 | Ä: Sebbes avtal; om AI-kodverktygen ska läsa spegeln (krock 2 i `ai-system/policy-samstammighet.md`) |
| A.8.32 | Ä: en andra granskare före merge; för två personer är det Sebbe. Baslinjen ersätter delvis en ändringslogg |

**ISO 42001**

| Krav | Varför |
|---|---|
| 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, A.2.2, A.3.2, A.4.6 | Ä: kontext, intressenter, omfång, ledningssystem, åtagande, P27 och rollerna. Utkasten finns |
| A.2.3 | Ä: P27 godkänd, beslut om förslagen (krock 1 och 2 är beslut i sak), ny genomgång mot godkända versioner |
| A.2.4 | Ä: en godkänd policy att se över |
| 6.1.1, 6.1.2, 6.1.3, 8.2, 8.3 | Ä: riskkriterier, metod, behandlingsplan, SoA |
| 6.1.4, 8.4, A.5.2, A.5.4, A.5.5 | Ä: processen och bedömningarna godkänns. A.5.4: att mäta skevhet mot små bolag kräver ett beslutat mått, och mätning på verkliga leads är kunddata |
| A.5.3 | Ext.: juristgranskning |
| 6.2, A.6.1.2, A.9.3 | Ä: AI-mål med mått. Förslag i P27 |
| 6.3, A.4.4, A.10.3 | Ä: beslut f signeras; ersättare för Gemini 2.5 väljs. Mätunderlaget finns |
| 7.1, 7.2, 7.3, 7.4, 7.5.1, 7.5.2 | Ä: resurser, kompetens, genomgång, kommunikationsplan, godkännande |
| 8.1, A.7.5, A.7.6, A.8.2 | Ä: merge av PR 72; beslut f |
| 9.1, A.6.2.6 | Ä: internlarmets variabler; mätning av AI-kvalitet i drift läser kundernas utfall och kräver beslutade mått |
| 9.2.1, 9.2.2 | Ext.: internrevision av en tredje person |
| 9.3.1–9.3.3, 10.1 | Ä: ledningens genomgång, förbättringslogg |
| 10.2, A.8.4 | Ä: AI-incidenter i G03 (förslag i `ai-system/policy-samstammighet.md`, G03); incidentloggen förs av incidentledaren |
| A.3.3 | Ä: P28 signeras; en väg utanför repot och en extern kontakt utses |
| A.4.3 | Ä: lagringstider |
| A.6.1.3, A.6.2.4 | Ä: en lägsta evalnivå som grind för release. En svit för Jev i inkorgen skulle skicka data till TypeSafe, som inte är godkänd |
| A.6.2.2, A.6.2.7, A.9.2, A.9.4 | Ä: kraven, dokumentationen till kund, proceduren för egen AI-användning och förbjudna användningar i villkoren beslutas. Underlaget finns i systembladen |
| A.6.2.5 | Ä: driftsättningsplan och grenskydd (GitHub-plan). Upptäckten av ändrade AI-variabler finns |
| A.7.2 | Ext.: Livrustnings godkännande av kunskapsbasen i evalsviten. Ä: processen |
| A.7.3 | Ä och Ext.: avtal med allabolag och hitta |
| A.7.4 | Ä: kvalitetskrav per system |
| A.8.3 | Ä: en väg för AI-fel på sajten är publikt innehåll i Snajps namn |
| A.8.5 | Ä: beslutad lista över rapportering |
| A.10.2, A.10.4 | Ä: ansvarsfördelning och villkor (Ext.: jurist); process för kundernas förväntningar |
