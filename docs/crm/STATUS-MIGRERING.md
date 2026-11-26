# Status: hela Snajp i det nya gränssnittet

Uppdateras efter varje arbetspass. Planen: [`PLAN-MIGRERING.md`](PLAN-MIGRERING.md).
Senast uppdaterad: 2026-11-26.

Lägen: **klart** (byggt och verifierat), **pågår**, **väntar** (på kvot eller på Anton),
**inte påbörjat**.

## Fas 0: referensen och Antons ändringar

| Del | Läge | Not |
|---|---|---|
| Version 2 låst som referens | klart | `DESIGN-CRM.md`, minnesanteckning, bilder i `docs/crm/bilder/app/` |
| Antons tretton svar som beslut | klart | `docs/BESLUT.md` 2026-11-26 |
| Sidofältet marinblått i båda lägena | klart | Byggt och granskat i bild 2026-11-26. Väntar på Antons dom |
| Snajps logga i sidofältet | klart | Överst, leder till översikten. Väntar på Antons dom |
| Ockra som accent | klart | Markör och ikon för vald menypost. Väntar på Antons dom |
| Sökikon i mobilens toppfält | klart | Tillbaka i toppfältet (commit `bd1b5b81`) |

## Fas 1: kartläggning av den nuvarande appen

| Område | Läst | Kompletterat | Not |
|---|---|---|---|
| 1 Skal, inloggning, onboarding | klart | klart | `underlag/app-01`, 121 rader (SK). Kompletterat i "Tillägg vid kontrolläsningen" |
| 2 Översikt, Att göra, Lärande | klart | klart | `underlag/app-02`, 85 rader (OV). "Rättat vid kontroll" och stickprov |
| 3 Leads: översikt, pipeline, bolag | klart | klart | `underlag/app-03`, 104 rader (LR) |
| 4 Leads: körningar, listor, källor | klart | klart | `underlag/app-04`, 132 rader (LK) |
| 5 Leads: utkast, konversationer, samtal | klart | klart | `underlag/app-05`, 129 rader (LU). Kompletteringar i avsnitt K |
| 6 Support | klart | klart | `underlag/app-06`, 176 rader (SU). Kompletteringar i avsnitt M. `support-webb` delvis läst |
| 7 Kvitton | klart | klart | `underlag/app-07`, 141 rader (KV). Tillägg 2026-11-26 |
| 8 Inställningar | klart | klart | `underlag/app-08`, 109 rader (IN) |
| 9 Adminytan | klart | klart | `underlag/app-09`, 116 rader (AD) |
| 10 API:t under ytorna | klart | klart | `underlag/app-10`, 179 rader (AP) och 14 sidrader. 266 backendrutter |
| Luckgranskning | klart | | `underlag/app-99`: alla sidor, rutter, ändpunkter, komponenter och menyposter prickade; 14 rader för luckorna (LX), tio motsägelser (E1–E10) |
| Funktionslistan | klart | | `MIGRERING-FUNKTIONSLISTA.md`: 1 306 rader med plats, fas, backend och läge; 23 i fas 3, 480 i fas 4, 803 i fas 5. Navigering, nya mönster, ordningen och sekretessen |

Grinden för fas 1 (varje rutt under `app/` och varje ändpunkt i minst en rad) håller
enligt `app-99`. Kvar att avgöra av Anton: oklarheterna i funktionslistans sista avsnitt,
främst om webbplatsbedömningen grindas per roll eller per arbetsyta (E1). Läckan i
`signal_detalj` (LR-128) och driftdatan i supportöversiktens svar (E3) ska rättas före
fas 4 respektive fas 5.

## Fas 2: Twenty-inventeringen

| Del | Läge | Not |
|---|---|---|
| Områdena 1 till 13 | klart | Lästa och kontrollästa mot källan, 3 666 funktionsrader. Område 13 är handboken som facit (commit `7b9f7b14`) |
| Luckgranskning | klart | Tre granskare (front, server, facit). Fem verkliga luckor, fyllda med egna rader |
| Paritetslistan `PARITET.md` | pågår | Tio av sexton delar har läge (2 581 rader: 83 verifierade, 50 byggda, 480 delvis, 1 856 inte gjorda, 112 avstår). Bara område 12 är kontrollerat. Stoppat av veckogränsen för Opus, som nollställs 2 december |
| rea | klart | 484 operationer ur webbklienten. Servern gav inget |
| craft-anything | klart | Hoppas över enligt Antons svar. Skäl i `docs/BESLUT.md` |

## Fas 3: CRM-kärnan

| Del | Läge | Not |
|---|---|---|
| Kundsynken in som API | klart | `/api/crm/v1`. 180 tester i minnet och 16 mot Postgres |
| Migrationerna 160 till 164 mot Postgres | klart | Körda två gånger var mot PGlite (Postgres 17) genom psycopg2, och lagrets frågor prövade där |
| Databasvägen i drift (asyncpg) | väntar | Hur asyncpg tolkar parametrarna är bara prövat i ett CI-jobb som inte körts, eftersom inget är pushat |
| Körning med inloggning mot den lokala stacken | inte påbörjat | Kräver Docker med Postgres och hela migrationskedjan. Vyerna är bara sedda i förhandsvisningen |
| Gränssnitt: översikt, bolag, personer, synk, utvecklare | klart | Version 2, godkänd |
| Tidigare kunder fria för Iris, uteslutning på nummer | klart | Bara backend, ingen yta behövs. `tests/crm/test_beslut.py` |
| Privatpersoner hoppas över som standard | klart | Migration 161 och växeln på anslutningen. Bilder i `docs/crm/bilder/fas3/` |
| Kontakta inte i CRM:et stoppar utskick | klart | Gäller också kampanjutskick och personerna hos ett märkt bolag |
| Tillägget som grind, fritt under provperiod | klart | `app/crm/tillgang.py`. Helsideläget när tillägget saknas är byggt. Ingen väg förbi för admin |
| Händelselogg, ändringsflöde och historik i postpanelen | klart | Migration 162. Bär fältens namn, aldrig värdena |
| Webhooks ut | klart | Backend och vyn under Utvecklare. Inte kört mot en riktig mottagare |
| Sortering nyast först, papperskorg, krockens id, namn på felrader | klart | Backend och vyer |
| Synkens två nivåer och underlag till supportärende | klart | Migration 163 och vyn. Se "Var supportsystemet kopplar in" nedan |
| Affärer med steg och tavla | klart i backend | Migration 164, commit `2fa09eb3`. Granskat ur tre vinklar och rättat. **Inget gränssnitt än** |
| Uppgifter, anteckningar, aktiviteter, bilagor | klart i backend | Samma commit. Bilagor i databasen, 10 MB per fil och 500 MB per kund (agentens val, behöver Antons dom). **Inget gränssnitt än** |
| Tidslinje mot leads, mejl, samtal och ärenden | klart i backend | `tidslinje.py`. Komponeras vid läsning. **Inget gränssnitt än** |
| Utfall speglas åt båda håll | klart i backend | `utfall.py`. **Inget gränssnitt än** |
| Samlad kundlista, Iris och Egna | klart i backend | `kundlista.py`, `GET /customers`. **Inget gränssnitt än** |
| Svensk standard i koden | pågår | Klart: organisationsnummer, moms, telefon, postnummer, bolagsform, SNI, privatperson. Inte gjort: SEK-format i hela ytan, registeruppslag, NIX |
| Sammanställning: vad som ändras mot Twenty och varför | klart | `docs/crm/SVENSK-STANDARD.md`, 81 rader och tio frågor till Anton |
| Bildgranskning av de svenska CRM-systemen | inte påbörjat | Texten finns i `svensk-03` |
| Oberoende granskning av gränssnittet i fas 3 del 1 | inte gjord | Byggaren stoppades av veckogränsen före sin rapport, och granskarna hann inte köra. Orkestratorn har läst 21 färska bilder och byggarens panelbilder |
| Ett schemalagt jobb som tömmer papperskorgen | inte påbörjat | I dag töms den vid nästa skrivning hos kunden, så löftet om 30 dagar håller inte för en kund som aldrig skriver |
| Bild på varje vy i Twentys hostade app | pågår | 17 bilder, mobilvyn gick inte att fånga |
| Testkonton i källsystemen | väntar | Kräver Antons ja per konto |
| Buddy | väntar | Inget avtalsdatum. Körs mot testkonto |

### Var supportsystemet kopplar in

CRM:et lämnar ifrån sig en rapport för varje synkkörning som slutar med fel. Sessionen som
bygger supportärendena läser den här och svarar med ärendets nummer:

- `GET /api/admin/crm/supportrapporter?utan_arende=true` (huvudnyckeln): rapporter som inget
  ärende tagit emot än, hos alla kunder, nyast först.
- `GET /api/admin/crm/supportrapporter/{kund}/{körning}`: hela rapporten. Räknare,
  anslutningens inställningar och gällande mappning, antal per felkod och varje felrad
  med kod. Felaktiga värden står med sin form (`99 99 99 9`), aldrig med innehållet.
- `POST /api/admin/crm/supportrapporter/{kund}/{körning}/arende` med `{"nummer": "F-7KQ2"}`:
  numret visas sedan för kunden på körningen.

Plattformsärendena (migration 156) kräver i dag en rapportör och en arbetsyta ur en
inloggad session, och synken har ingen: den startas av en API-nyckel. Därför skapar CRM:et
inget ärende själv. Antingen får ärendetabellen en systemrapportör, eller så hämtar ett
jobb på supportsidan rapporterna härifrån. Det valet är supportsessionens.
Kod: `snajp-support/app/crm/supportrapport.py`, `snajp-support/app/api/admin_crm.py`.

### Det Anton behöver veta om tillägget

Också plattformsadmin möts av "tillägget saknas" i CRM:et för en kund vars provperiod är
slut. Slå på tillägget Snajp CRM på kunden under Admin, kunden, Tillägg. Det slår igenom
inom en minut. Kunderna ser inte tillägget i sin lista förrän CRM:et öppnas för dem.

## Fas 4: Leads i CRM-miljön

En rad per vy, i byggordningen ur funktionslistans avsnitt "Ordningen" (där steg 4.7 här är delat i två och bolagssöket står som eget steg). Raderna i
funktionslistan som hör till vyn står i noten.

| Steg | Vy | Läge | Not |
|---|---|---|---|
| 4.1 | Skalets förutsättningar: gruppen Iris, banderollen, notisräknaren, läsroll och kundbesök i `app/crm/layout.tsx` | inte påbörjat | SK-038–SK-045, SK-064, SK-067–SK-079, SK-155–SK-157, AD-005, AD-008–AD-011 |
| 4.2 | `/crm/iris/leads` med panelen `?lead=` | inte påbörjat | LR-001–LR-075, LR-090–LR-114. Webbgrinden byggs här; `signal_detalj` rättas först |
| 4.3 | Utkastredigeraren och `/crm/iris/utkast` (Att granska, Skickas snart, Skickat) | inte påbörjat | LU-030–LU-070, LU-080–LU-088, LU-150–LU-159, LU-172–LU-183, AP15 |
| 4.4 | `/crm/iris/korningar` och `/crm/iris/korningar/[id]`, dialogen Kör Iris | inte påbörjat | LK-001–LK-057, LK-130–LK-138, OV-031–OV-037 |
| 4.5 | `/crm/installningar/iris` | inte påbörjat | LK-060–LK-073, IN-100–IN-112, IN-144 |
| 4.6 | Tråd- och inkorgsvyn och `/crm/iris/konversationer` | inte påbörjat | LU-001–LU-024, LU-081, LU-089, LU-110–LU-122, OV-105 |
| 4.7 | `/crm/iris/uppfoljningar` | inte påbörjat | LU-100–LU-107 |
| 4.8 | `/crm/iris/samtal` | inte påbörjat | LU-130–LU-138, LU-170, LU-171 |
| 4.9 | `/crm/iris/listor` med import och säljlista | inte påbörjat | LR-120–LR-135, LK-100–LK-118, LK-142–LK-151 |
| 4.10 | `/crm/iris/kampanjer` | inte påbörjat | LU-160–LU-162 |
| 4.11 | `/crm/iris` Iris-översikten | inte påbörjat | LR-020–LR-027, LU-024, LU-032, LU-174 |
| 4.12 | Bolagssöket i kommandopaletten | inte påbörjat | LR-080–LR-082 |

## Fas 5: resten av appen

| Steg | Vy | Läge | Not |
|---|---|---|---|
| 5.1 | Inställningsskalet `/crm/installningar` | inte påbörjat | IN-001–IN-018 |
| 5.2 | Inställningar: Företaget, Vad ni säljer, Kunskapsbas, Så ska agenten låta | inte påbörjat | IN-012, IN-020–IN-042, SU-120–SU-133, IN-146 |
| 5.3 | Inställningar: När agenten får svara själv, Inkorgar | inte påbörjat | IN-050–IN-076, SU-140–SU-168 |
| 5.4 | Inställningar: Kanaler, Integrationer (nya ytor) | inte påbörjat | SU-105–SU-107, SU-212, SU-213, IN-160–IN-166 |
| 5.5 | Inställningar: Team, Plan och fakturering, Tillägg, Notiser, Tema, Dataskydd, Kvitton | inte påbörjat | IN-080–IN-095, IN-120–IN-125, IN-143, IN-145. IN-083 saknar ändpunkt |
| 5.6 | Inställningar: Plattformen (instruktioner, tvåstegsverifiering) | inte påbörjat | IN-130–IN-137, AD-110–AD-116, SK-048 |
| 5.7 | `/crm/kundtjanst` med Översikt, Ärenden, Testmail, Dolda | inte påbörjat | SU-001–SU-064. Driftdatan (E3) grindas i backenden först |
| 5.8 | `/crm/kundtjanst/testchatt` (chattvyn) | inte påbörjat | SU-007, SU-070–SU-088 |
| 5.9 | `/crm/kundtjanst/overlamnade` | inte påbörjat | SU-100–SU-110, SU-207–SU-211, SU-218. Beslut om portalen väntar på Anton |
| 5.10 | `/crm/att-gora` | inte påbörjat | OV-060–OV-079, KV-170 |
| 5.11 | `/crm/larande` | inte påbörjat | OV-080–OV-091 |
| 5.12 | `/crm` Översikt utökad med agentavsnitt och Kom igång | inte påbörjat | OV-020–OV-048, OV-101, SU-126, SU-190, AD-138 |
| 5.13 | `/crm/kvitton` (Översikt, Kvitton, assistenten) | inte påbörjat | KV-01–KV-208. Vilande, bara plattformsadmin |
| 5.14 | `/crm/admin` Admin-översikt | inte påbörjat | AD-020–AD-027 |
| 5.15 | `/crm/admin/kunder` och `/crm/admin/kunder/[id]` (fyra flikar) | inte påbörjat | AD-030–AD-077, LK-126, LK-127 |
| 5.16 | `/crm/admin/paket` | inte påbörjat | AD-100–AD-105, IN-094, IN-095, KV-171 |
| 5.17 | `/crm/admin/logg` och `/crm/admin/logg/[id]` | inte påbörjat | AD-080–AD-094, AD-130, AD-131, LK-134, KV-172 |
| 5.18 | Plattformsadmin i skalet: Byt kund, Admin/Demo, driftkort | inte påbörjat | AD-001–AD-018, AD-137–AD-139b |
| 5.19 | `/login` och `/auth/reset` i CRM:ets form | inte påbörjat | SK-020–SK-037, SK-130–SK-138, SK-175–SK-188 |
| 5.20 | `/onboarding` i CRM:ets form | inte påbörjat | SK-110–SK-127, SU-190–SU-192 |
| 5.21 | Installera som app, offline, kundens domän | inte påbörjat | SK-001–SK-010, SK-150–SK-154, SK-170–SK-174 |
| 5.22 | Luckorna: demon, Duo-demon, demobokningen | inte påbörjat | LX-001–LX-015. Väntar på Antons beslut |

## Fas 6: växlingen

Inte påbörjat.

## Befintliga filer som ändrats utanför CRM:ets egna mappar

| Fil | Ändring | Commit |
|---|---|---|
| `app/globals.css` | Tailwinds grundstilar i kaskadlagret `tw-base` | e86d6675 |
| `lib/routes.ts`, `proxy.ts`, `lib/i18n.tsx`, `components/AppShell.tsx` | Rutten `/crm`, menyposten för plattformsadmin | e86d6675 |
| `tests/invariants/test_inv_ui_001.py` | `app/crm` och `components/crm/app` i grindens lista | e86d6675 |
| `snajp-support/app/api/deps.py`, `main.py`, `storage/*.py`, `leads/scheduler.py` | Nycklar med omfång, CRM-bolag som upptagna, kundadresser i sändspärren | 1cc6ff4d |
| `scripts/gdpr_radera.py`, `.github/workflows/verify.yml` | CRM-tabellerna i raderingen och i databastesterna | 1cc6ff4d |

## Kvoten

Veckokvoten 64 procent 2026-11-26. Se planens avsnitt 5.
