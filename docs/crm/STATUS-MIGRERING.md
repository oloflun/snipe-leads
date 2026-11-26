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
