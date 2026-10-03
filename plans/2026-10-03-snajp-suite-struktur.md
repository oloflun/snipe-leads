# Snajp Suite: en struktur i stället för tjugo sidor (2026-10-03)

Antons ord 2026-10-03: "jag kan inte se den tydliga CRM- 'Snajp- Suite' som jag bad om, allt är väldigt
rörigt och utspritt över många sidor utan någon bra överblick eller struktur. Alla Iris-sidor är nu fler
och mer spridda än någonsin. Gå igenom Twenty igen och undersök hur vi kan strukturera datan bättre och mer
proffsigt. Kundsidorna från adminvyn hade kunnat bakas ihop, översikterna för både admin och kunder är
röriga och intetsägande med många viktiga mätvärden gömda längre ned eller på andra sidor."

Underlag: Twenty-utredning (källkod `twentyhq/twenty@main` + docs.twenty.com) och en inventering av alla
rutter, menyer och mätvärden i repot, båda 2026-10-03. Läge: Tier 0 (DESIGN.md), Operate-läge.

## 1. Diagnos

Förra sessionen tog över Twentys **datamodell** (bolaget som nav, tidslinje, statusfält, sparade vyer) men
inte dess **navigation**. Twenty har en regel som vi bröt: *ett objekt = en menypost = en sida; vyer,
kanban, import och körningar ligger inuti objektet.* Vi byggde i stället en sida per vy och per arbetssteg.

Mätt i koden:

| Problem | Var |
|---|---|
| Iris har 6 undersidor + 3 flikar i Bolag + 3 segment i Listor | `lib/routes.ts:99-139`, `IrisBolag.tsx:87-95` |
| Utkast godkänns på **fem** ställen | Granskning, Översiktskortet, Bolag-detaljen, Listor-raden, `/settings/leads` |
| Två "Körningar" som läser olika tabeller (`agent_runs` vs jobbliggaren 080) | `app/admin/korningar`, `IrisKorningar.tsx` |
| Två "Inställningar"; `LeadsControls` renderas i båda | `IrisInstallningar.tsx`, `/settings/leads` |
| Iris › Inkorg är supportinkorgen med supportkategorier | `IrisInkorg.tsx` (16 rader), `Dashboard.tsx:775` |
| Kunder och Paket listar samma kunder; tillägg redigeras på två ställen; två avstängningsmekanismer (`/aktiv` och `/status`) | `Kundtabell.tsx`, `PaketHantering.tsx`, `Avstangning` |
| "Kunden" har tre destinationer: `/kunder/[id]`, `/kunder/[id]/data`, Paket-raden | `Portfoljvy`, `Kundtabell` |
| Översikten börjar med två datalösa länkkort; supportens siffror och Kvitton ligger längst ned eller saknas | `DuoSummary.tsx`, `StartView.tsx` |
| Admin Översikt: intäkt och marginal kommer först efter hela kundtabellen | `Portfoljvy.tsx:266` |
| Railen tappar flikar: klick på Iris döljer Kundtjänst och Kvitton i admin; Kvitton försvinner för Trio-kunder | `AdminShell.tsx:136`, `AppShell.tsx:88-92` |
| Rubriken på sidan stämmer inte med menyn på 10 ställen (Kunder/"Kunder & Data", Kundtjänst/"Inkorg och utkast", Bolag/"Iris" …) | inventeringen § 5 |

## 2. Principerna (ur Twenty, översatta)

1. **Ett objekt = en menypost = en sida.** Pipeline, Tabell och Listor är *vyer* av Bolag, inte sidor.
2. **Vyer väljs i en vybar på sidan**, aldrig i menyn: Lista · Tabell · Pipeline, plus sparade vyer i en väljare.
   Ändrade filter visar "Spara vy / Spara som ny".
3. **Status är ett fält; Pipeline-vyn grupperar på det** med antal per kolumn.
4. **Posten öppnas i en sidopanel** (listan behåller sitt sammanhang) med "öppna helsida". Nyckelfält till
   vänster, flikar till höger: Översikt · Utkast · Tidslinje · Uppgifter.
5. **En händelselogg** syns som Tidslinje på varje post: Iris researchade, utkast godkänt, svar inkom,
   körning X. Den ersätter Iris › Inkorg för leadsmejl (svaret hamnar på bolaget).
6. **Körningar är ett objekt i en loggsida**, inte en sida per agent.
7. **En enda Inställningar**, grupperad; per-agent-inställningar ligger där som sektioner.
8. **Import, beställ lista, kombinera, exportera** ligger i sidans ⋮-meny, inte i menyn eller överst på sidan.
9. **Översikten är en instrumentpanel**: nyckeltal överst, sedan det som väntar på dig, sedan trender.

Det enda vi medvetet avviker från: Twenty saknar en arbetskö, men Snajp säljer människa-i-loopen. Därför
finns **en** kö, "Att göra", som samlar allt som väntar på ett beslut från alla agenter.

## 3. Den nya strukturen

### 3.1 Kundportalen (och adminens egen arbetsyta, samma komponenter)

Från 10 menyposter i två nivåer till 7 platta:

```
FÖRE                                   EFTER
Översikt                               Översikt        instrumentpanel (§ 4.1)
Iris                                   Att göra   12   alla utkast + eskaleringar + nya leads + förfallna uppgifter
  Bolag  (Alla bolag|Tabell|Listor)    Leads           Lista · Tabell · Pipeline · Listor + sparade vyer
  Pipeline                               ⋮ Kör Iris · Beställ lista · Importera CSV · Kombinera listor
  Körningar                              lead: Översikt · Utkast · Tidslinje · Uppgifter
  Inkorg                               Kundtjänst      Alla · Ohanterade · Eskalerade · Överlämnade chattar
  Granskning                             ⋮ Testmail · Testchatt
  Inställningar                        Kvitton
Kundtjänst (5 flikar)                  Aktivitet       alla körningar, alla agenter (Iris-jobb + journal)
Kvitton                                Inställningar   en plats, grupperad (§ 3.3)
Inställningar (13 sektioner)
```

Gamla adresser omdirigeras (`/dashboard/iris/pipeline` → `/dashboard/leads?vy=pipeline` osv.), så inga
bokmärken eller mejllänkar går sönder.

### 3.2 Admin

Från 7 plattformssidor till 3, och kunden blir **en** post:

```
FÖRE                       EFTER
Översikt                   Översikt   KPI-rad: MRR · marginal · betalande · trials som löper ut · fel 24 h · eskaleringar
Kunder                       sedan: Kräver åtgärd, trend (nya kunder/avtal)
Paket                      Kunder     vyer: Alla · Betalande · Trial · Kräver åtgärd · Test  (paket/pris/status som kolumner)
Körningar                    post /admin/kunder/[id]:
Testkörningar                  Översikt (hälsa, användning, kostnad, marginal)
Agentanvändning                Paket och tillägg (byt paket, tillägg, kontoläge = EN avstängningsväg)
Händelser                      Uppgifter och kontakter (dagens /data)
                               Agentprofil (Kundtjänst | Iris)
                               Körningar · Händelser (filtrerade på kunden)
                               knappar: Öppna arbetsyta · Flytta till riktigt konto
                           Logg       vyer: Körningar · Händelser · Fel · Test · Kostnad per agent
                             ⋮ Ny testkörning (Iris)
Arbetsyta (egen)           Arbetsyta  samma 7 poster som kunden
```

Paket, Testkörningar, Agentanvändning och Händelser blir vyer och flikar; deras sidor omdirigeras.

### 3.3 Inställningar, en plats

```
Företaget       Företaget · Vad ni säljer · Kunskapsbas · Så ska agenten låta
Iris            Målgrupp och profil (IrisProfil + LeadsControls slås ihop, dubbletten bort)
                Hur långt Iris får gå · Automation per leadtyp · Överlämning · CRM-synk
Kundtjänst      När agenten får svara själv · Inkorgar · Integrationer · Kanaler
Konto           Team · Plan och fakturering · Tillägg · Notiser · Tema
Plattformen     Globala agentinstruktioner (bara admin)
```
Rubrikerna på sidorna blir samma ord som i menyn.

## 4. Översikterna

### 4.1 Kundens Översikt (allt viktigt ovanför vecket vid 1440×900)

```
┌ Väntar på dig 12 ┬ Nya leads 7 d ┬ Svar 7 d ┬ Möten ┬ Ärenden 7 d ┬ Klarade själv % ┐   KPI-rad, bara agenter kunden har
├──────────────────┴───────────────┴──────────┴───────┴─────────────┴─────────────────┤
│ Att göra (5 första, godkänn direkt)      │ Pipeline: antal per status (stapel)       │
├──────────────────────────────────────────┼───────────────────────────────────────────┤
│ Körs nu / senaste körningar              │ Vad ärendena handlar om                   │
└──────────────────────────────────────────┴───────────────────────────────────────────┘
statusrad längst ned: agenten jobbar · kunskapsbas N dokument · inkorg kopplad
```
Bort: "Gemensam översikt" (två datalösa länkkort), dubbla "N utkast väntar"-kort (ersätts av Att göra),
kunskapsbaskortet (flyttar till Inställningar). Siffrorna är riktiga, aldrig påhittade; en agent kunden
saknar visas inte i KPI-raden.

### 4.2 Admin Översikt
KPI-raden överst (MRR, marginal efter tokenkostnad, betalande kunder, trials som löper ut inom 14 dagar,
fel senaste dygnet, eskaleringar), sedan "Kräver åtgärd" (bara kunder med en anledning, och anledningen
utskriven), sedan trenden. Kundtabellen i sin helhet bor i Kunder, inte här.

## 5. Datan

| Ändring | Varför | Kostnad |
|---|---|---|
| `GET /api/att-gora`: samlar leads-kön, supportutkast, eskaleringar, inkorgsleads och förfallna uppgifter i en lista med typ | En kö i stället för fem | Läsning ur befintliga tabeller, ingen migration |
| `GET /api/oversikt`: KPI-raden i ett anrop | Översikten gör i dag 9 anrop och räknar i webbläsaren | Ingen migration |
| Leadsmejl (klass=lead) kopplas till bolagets tidslinje; omatchade blir "Nytt lead" i Att göra | Ersätter Iris › Inkorg | Finns redan i `leads/svar.py`, bara visningen flyttar |
| Aktivitet läser jobbliggaren (080) och `/usage`; admin-Loggen läser `agent_runs` med alla fem leadstyper | Två Körningar blir en per yta; filterdriften rättas | Ingen migration |
| **Beslut:** Listor som vyer av Bolag (§ 6 fråga 2) | Listraden är i dag en egen entitet som måste "läggas i registret" | Migration om ja |
| Admin: en avstängningsväg (`/status` med `aktiv` som härledd) | Två mekanismer kan säga emot varandra | Liten |

## 6. Frågor till Anton

1. **Godkänner du strukturen i § 3?** Den tar bort sidorna Pipeline, Körningar, Inkorg, Granskning och
   Iris-Inställningar i kundportalen och Paket, Testkörningar, Agentanvändning och Händelser i admin (alla
   omdirigeras, ingen data raderas).
2. **Listor: ska listans rader bli bolag direkt** (status "I lista", syns i Bolag via vyn Listor, ingen
   "Lägg i registret"-knapp), **eller vara kvar som egen sak** som bara nås via vyn? Rekommendation: bli bolag
   direkt. Twenty gör så, och det tar bort ett steg kunden inte förstår.
3. **Ordning:** kundportalen först (det är den som säljs), sedan admin. Eller tvärtom?

## 6b. Antons svar 2026-10-03

> Jag godkänner strukturen i sin helhet, men har några frågor. Leads ska heta leads, inte bolag. Var även
> noga med att lägga till flikar som vi enbart har funktion för, så vi inte lägger till funktioner från
> Twenty som vi inte har, vad står tex kanban för?

Följder, bindande för bygget:
- **Menyposten och objektet heter Leads** (en: Leads), posten heter "Lead". Agenten heter fortfarande Iris.
- **Ordet kanban används aldrig i gränssnittet.** Kanban är tavelvyn med en kolumn per status där korten
  dras mellan kolumnerna, alltså dagens Pipeline. Vyn heter **Pipeline**.
- **Ingen flik utan befintlig funktion.** Granskat mot koden:

| Flik / vy / åtgärd | Funktion som redan finns |
|---|---|
| Leads › Lista | `IrisBolag` Alla bolag (lista + detalj) |
| Leads › Tabell | `LeadsTabell` |
| Leads › Pipeline | `Pipeline` (statuskolumner, dra och släpp) |
| Leads › Listor (vy) | `LeadslistorView`, `/leads/listor` |
| Sparade vyer | `/leads/vyer` (migration 086) |
| ⋮ Kör Iris · Beställ lista · Importera CSV · Kombinera listor | `LeadsRunForm`, `/leads/listor`, `/leads/import`, `/leads/listor/kombinera` |
| Lead › Översikt · Utkast · Tidslinje · Uppgifter | `LeadDetail` (bedömning, källor, motivering), mejlutkastet, `/tidslinje`, `/uppgifter` (har `forfaller`) |
| Att göra | `/leads/queue`, supportutkast, eskalerade ärenden, inkorgsleads (origin `inkorg`), uppgifter med `forfaller` |
| Kundtjänst › Alla · Ohanterade · Eskalerade · Överlämnade chattar | `Dashboard` (statusfilter, "Bara ohanterade"), `/chattar` |
| Kundtjänst ⋮ Testmail · Testchatt | `?is_test=true`, `SupportChat testMode` |
| Aktivitet | `/leads/korningar` (jobbliggaren), `JournalVy` (`/usage`) |
| Översikt KPI | väntar (köerna ovan), nya leads 7 d (`created_at`), svar 7 d (inkorg klass=lead), leads i status Möte, ärenden 7 d, klarade själv % |
| Admin Kunder › vyer | `listTenants`: status, trial, hälsa, `testkund-*`, betalande (Portfoljvy räknar redan) |
| Admin kundposten, alla flikar | `Kundprofil`, `Tillaggsvaljare`, `PaketHantering`, `Kunddata`, `/runs?tenant_id`, `/events` |
| Admin Logg › Körningar · Händelser · Fel · Test · Kostnad per agent | `/admin/runs`, `/admin/events?level=`, `is_test`, `AgentAnvandning` |
| Admin Logg ⋮ Ny testkörning (bara Iris) | `Testkorningar` (`LeadsRunForm isTest`) |

**Struket för att funktionen saknas:** Exportera alla leads (bara listor har CSV-nedladdning), Ny testkörning
för Kundtjänst i admin (testchatten finns bara i kundens Kundtjänst), samt allt från Twenty som saknar
motsvarighet hos oss: Filer, Kalender, Mejlflik per lead utöver tidslinjen, Dashboards som objekt, Workflows,
Favoriter.

Fråga 2 (listrader som leads) kräver en migration och avgörs vid fas 4. Fråga 3: kundportalen först
(rekommendationen; ändras om Anton säger annat).

## 7. Faser (efter godkännande)

| Fas | Innehåll | Verifiering |
|---|---|---|
| 1 | Platt rail (rättar flikbuggarna), Bolag med vybar och sidopanel, Aktivitet, omdirigeringar, en Inställningar | tsc, rotinvarianter, INV-COPY-001, demo i 320/375/1440, axe |
| 2 | `/api/att-gora`, `/api/oversikt`, Att göra, ny Översikt | backendsviten + nya tester, pixelgranskning |
| 3 | Admin: kundposten med flikar, Logg, ny admin-Översikt, en avstängningsväg | backendsviten, pixelgranskning |
| 4 | Listor som bolag (om ja), demo-navet i takt | migration torrkörd, röktest |

Varje fas är tvåspråkig (INV-COPY-001), committas till `development` och pixelgranskas innan nästa.
Förutsättning för pixelgranskning av inloggade ytor: Docker-fixen (handoff 2026-10-02 § 4.3) och ledigt
minne (2026-10-03: 0,4 GB ledigt, en hängd `motion_capture.py` håller 10 GB).
