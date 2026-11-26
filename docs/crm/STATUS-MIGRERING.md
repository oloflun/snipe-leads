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
| Sökikon i mobilens toppfält | inte påbörjat | Försvann när loggan kom in. Sökningen finns i lådan |

## Fas 1: kartläggning av den nuvarande appen

| Område | Läst | Kompletterat | Not |
|---|---|---|---|
| 1 Skal, inloggning, onboarding | inte påbörjat | | |
| 2 Översikt, Att göra, Lärande | inte påbörjat | | |
| 3 Leads: översikt, pipeline, bolag | inte påbörjat | | |
| 4 Leads: körningar, listor, källor | inte påbörjat | | |
| 5 Leads: utkast, konversationer, samtal | inte påbörjat | | |
| 6 Support | inte påbörjat | | |
| 7 Kvitton | inte påbörjat | | |
| 8 Inställningar | inte påbörjat | | |
| 9 Adminytan | inte påbörjat | | |
| 10 API:t under ytorna | inte påbörjat | | |
| Luckgranskning | inte påbörjat | | |
| Funktionslistan | inte påbörjat | | `MIGRERING-FUNKTIONSLISTA.md` |

Startas när femtimmarsfönstret är nollställt.

## Fas 2: Twenty-inventeringen

| Del | Läge | Not |
|---|---|---|
| Områdena 1, 2, 4 | klart | Lästa och kontrollästa |
| Område 3 | pågår | Läst, kontrolläsningen avbruten |
| Områdena 5 till 12 | pågår | Lästa, inte kontrollästa |
| Område 13, handboken som facit | inte påbörjat | |
| Luckgranskning | inte påbörjat | |
| Paritetslistan `PARITET.md` | inte påbörjat | |
| rea | klart | 484 operationer ur webbklienten. Servern gav inget |
| craft-anything | klart | Hoppas över enligt Antons svar. Skäl i `docs/BESLUT.md` |

## Fas 3: CRM-kärnan

| Del | Läge | Not |
|---|---|---|
| Kundsynken in som API | klart | `/api/crm/v1`, 110 tester i minnet, 9 mot SQL |
| Databasvägen i drift (asyncpg) | väntar | Bara prövad i ett CI-jobb som inte körts, eftersom inget är pushat |
| Gränssnitt: översikt, bolag, personer, synk, utvecklare | klart | Version 2, godkänd. Inte kört mot riktig backend |
| Körning mot den lokala stacken | inte påbörjat | |
| Tidigare kunder fria för Iris | inte påbörjat | Ändring i `upptagna` |
| Uteslutning på nummer när numret finns | inte påbörjat | |
| Privatpersoner hoppas över som standard | inte påbörjat | |
| Tillägget som grind, fritt under provperiod | inte påbörjat | |
| Synkens två nivåer och underlag till supportärende | inte påbörjat | Supportsystemet byggs av en annan session |
| Webhooks ut | inte påbörjat | |
| Sortering nyast först, namn på felrader, papperskorg | inte påbörjat | |
| Affärer med tavla | inte påbörjat | |
| Uppgifter, anteckningar, aktiviteter, bilagor | inte påbörjat | |
| Tidslinje mot leads, konversationer, samtal, ärenden | inte påbörjat | |
| Utfall speglas åt båda håll | inte påbörjat | |
| Samlad kundlista, Iris och Egna | inte påbörjat | |
| Svensk standard i koden: SNI, SEK, bolagsform, register, NIX | pågår | Organisationsnummer, moms, telefon och postnummer klara |
| Bildgranskning av de svenska CRM-systemen | inte påbörjat | Texten finns i `svensk-03` |
| Sammanställning: vad som ändras mot Twenty och varför | inte påbörjat | |
| Bild på varje vy i Twentys hostade app | pågår | 17 bilder, mobilvyn gick inte att fånga |
| Testkonton i källsystemen | väntar | Kräver Antons ja per konto |
| Buddy | väntar | Inget avtalsdatum. Körs mot testkonto |

## Fas 4: Leads i CRM-miljön

Inte påbörjat. Raderna skrivs in när funktionslistan från fas 1 finns.

## Fas 5: resten av appen

Inte påbörjat. Raderna skrivs in när funktionslistan från fas 1 finns.

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
