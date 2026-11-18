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
| ISO 42001 (70) | 1 → **5** | 53 → **51** | 16 → **14** | 0 → 0 | 0 → 0 |

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
| A.5.5 | delvis | b | Kontaktlista IMY, CERT-SE, polis | Listan går att skriva, men vem som ringer är ett beslut | **Ja**: utkast `myndighetskontakter.md`, "vem kontaktar" tom |
| A.5.6 | saknas → **delvis** | b | Prenumeration på CERT-SE m.fl. med mottagare | Ett bevakningsflöde går att bygga; vem som läser är ägarens | **Ja**: `sakerhetsbevakning.yml` (CERT-SE och GitHubs advisories för stacken, ärende vid träff, reserv och dödmanskontroll). Mottagare obeslutad |
| A.5.7 | delvis | b | Rutin för att läsa larmen | – | Dependabot-läget uppdaterat (2 höga, ingen rättning finns) |
| **A.5.8** | delvis | **a** | Fast säkerhetsfråga i varje arbete | PR-mall och CI-grind | **Uppfyllt** (INV-PROC-001) |
| A.5.9 | delvis | b | Datorer, telefoner och konton med ägare | Driftens tillgångar | **Ja**: `drift-och-tillgangar.md` §1–2 |
| A.5.10 | delvis | b | Godkänd P13 | – | – |
| A.5.11 | saknas | b | Avslutsrutin | – | – |
| A.5.12 | delvis | b | Godkänd G02 | – | – |
| A.5.13 | delvis | b | Godkänd G02 | – | – |
| A.5.14 | delvis | b | Synkflytten (Railway) | Koden finns (PR 71) | – |
| A.5.15 | delvis | b | Regler för leverantörskonton | RLS verifierat i CI | **Ja** (gap om RLS-verifiering minskat) |
| A.5.16 | delvis | b | Personliga konton i stället för delade | – | – |
| A.5.17 | delvis | b | Lösenordsbyte, lösenordshanterare | – | – |
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
| A.8.2 | delvis | b | Lösenordsbyte, admins listade | GitHub-admins belagda | Ja |
| A.8.3 | delvis | b | Minimerad spegel | RLS verifierat i CI | **Ja** |
| A.8.4 | delvis | b | Grenskydd (betald plan), koppla bort Supabase-appen | Åtkomsten belagd | **Ja** (repot privat; nytt gap: grenskyddet) |
| A.8.5 | delvis | b | Tvåfaktor på konton; spärr i appen | – | – |
| A.8.6 | delvis | b | Kapacitetsövervakning, repliker | – | – |
| A.8.7 | okänt | b | Antivirus på datorerna | – | – |
| A.8.8 | delvis | b | Patchtider, kodskanning (kräver betald plan) | – | Läget uppdaterat |
| A.8.9 | delvis | b | Logg över Railway-ändringar; rutin för när baslinjen körs | Baslinjen i bevis | **Ja**: `scripts/railway_baslinje.py` (`--skriv`, `--jamfor`), `railway-baslinje.json` |
| A.8.10 | delvis | b | Gallring påslagen | Raderingen provkörd | **Ja** (CI) |
| A.8.11 | delvis | b | Merge av PR 72 | – | – |
| A.8.12 | delvis | b | Synkflytten, mönster för lösenord | – | Läget uppdaterat |
| A.8.13 | saknas | b | Railway Pro | – | – |
| A.8.14 | saknas | b | Tillgänglighetskrav | – | – |
| A.8.15 | delvis | b | Gallring av `agent_runs`; åtkomstloggen i `main` (merge) | Loggningen beskriven med belägg; åtkomstlogg för admin (PR 85); kvittotexten ur `agent_runs` (PR 83) | **Ja** (`drift-och-tillgangar.md` §5) |
| A.8.16 | delvis | b | Internlarmets variabler; extern pingtjänst | Orsaken utredd, reserv och dödmanskontroll | **Ja** (PR 84) |
| A.8.17 | okänt | b | Tidssynk på datorerna | – | – |
| A.8.18 | delvis | b | Vem som har Railway-token och psql; beslutad behörighet | Verktygslistan | **Ja**: `privilegierade-verktyg.md` (vägar, skript per grupp, förslag) |
| A.8.19 | delvis | b | Regler för programvara på datorerna | – | – |
| A.8.20 | delvis | b | Stäng Postgres publika proxy (Railway) | – | – |
| A.8.21 | delvis | b | HSTS i drift kräver merge till main | HSTS-raden kan skrivas | – (inte gjort: når inte drift utan merge) |
| A.8.22 | delvis | b | Synkflytten | – | – |
| A.8.23 | delvis | b | Webbskydd på datorerna | – | – |
| A.8.24 | delvis | b | Nyckelrotation, spegelns nycklar | – | – |
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
| A.2.3 | saknas | b | Genomgång mot övriga policyer, men policyerna är osignerade | Genomgången kan skrivas när P27 är godkänd | – |
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
| A.6.2.5 | delvis | b | Driftsättningsplan; grenskydd | – | Fynd: code owner tvingar inte längre |
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
