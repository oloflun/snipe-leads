# Handoff: adminfliken Kunder & Data — kundregister, statistik, felöversikt

Skriven 2026-08-29 (natt) av Sebbe/Claude, på Sebbes uppdrag. Deployad till
`development` enligt den omlagda kedjan (en push, ingen spegelgren).

**Status: byggd, migrerad, deployad och besiktigad live i development.**
16 filer, 2 006 rader. 1 505 backendtester gröna, tsc rent, `qa_vyer.mjs`
grönt mot körande dev-miljö. **`main` är INTE rörd.**

Live: https://web-development-6c85.up.railway.app/admin/kunder

---

## 1. Vad som byggdes, och varför just så

Sebbe ville ha en flik som svarar på "vilka är kunderna, vad har vi avtalat,
hur går försäljningen, vad går sönder". Fliken **Kunder fanns redan** — den är
utbyggd i stället för kopierad, eftersom en andra kundvy hade betytt två
sanningar om samma kunder. Sidtiteln är `Snajp - Kunder&Data`, rubriken
"Kunder & Data".

### Fas 1 — kundregistret (migration 053)

Två nya tabeller: `ss_customer_details` (orgnr, faktureringsadress,
faktureringsmejl, telefon, företagsadress, `kund_sedan`, `avtal_signerat`) och
`ss_customer_contacts` (namn, roll, mejl, telefon per kund).

**Det viktigaste beslutet i hela bygget: varje fält bär sin KÄLLA.** Bara två
av sju uppgifter går att fylla i automatiskt i dag — organisationsnumret ur
onboardingens affärskontext (`Organisationsnummer: NNNNNN-NNNN`, skriven av
`lib/actions/onboarding.ts`) och kund-sedan-datumet ur `ss_tenants.created_at`.
Resten finns inte i någon datakälla och måste skrivas för hand.

I ett formulär ser ett härlett och ett bekräftat värde likadana ut. API:t
returnerar därför `{varde, kalla}` per fält — `manuell`, `onboarding`, `system`
eller `null` (saknas) — och vyn ritar ett märke vid varje etikett. Ett
faktureringsunderlag där en gissning ser handkontrollerad ut är precis det
felet som kostar pengar hos någon annan.

Följdbeslut av samma sort: **klienten skickar bara ÄNDRADE fält.** Backenden
skiljer på utelämnat (rör inte) och tom sträng (nollställ), som agentprofilen
gör. Skickades hela formuläret varje gång blev varje härlett värde manuellt
vid första sparning — datumet ur registreringen hade plötsligt sett
handbekräftat ut utan att någon rört det.

**Avtal är ett datum, inte en boolean.** Null = inget avtal registrerat, ett
datum = avtal finns och signerades då. Två fält som kan säga emot varandra är
ett fält för mycket.

### Fas 2 — statistik

Nyckeltal (avtal i dag/vecka/månad/år), veckograf över nya kunder och
signerade avtal (12 veckor, server-renderad SVG, legend + direktetiketter +
tabellversion bakom `<details>`), och en försäljningstakt.

Demo- och testytor (`nordlys-handel`, `public-demo`, `testkund-*`) räknas
**aldrig** som kunder — samma regel som `is_test` i körningsvolymen. De göms
inte: vyn skriver ut hur många som filtrerats bort.

Räknandet ligger i `lib/admin/statistik.ts`, skilt från renderingen, och
matas med SAMMA tenantrader som tabellen ovanför. Två uträkningar av samma tal
blir förr eller senare två olika tal, och här hade skillnaden synts som att
sidan säger emot sig själv.

### Fas 3 — intäkter/utgifter: BYGGD SOM EN FLAGGA, INTE SOM SIFFROR

**Det finns ingen riktig ekonomisk datakälla i kodbasen.** Betalsätten i
migration 044 är Stripes publicerade testkort mot en simulerad provider utan
växel; fakturor, nummerserie och moms finns inte i kod. Sidan säger det rakt ut
och pekar på Översiktens befintliga uppskattningar (MRR ur härlett paket +
tokenkostnad, båda märkta som uppskattningar).

Sebbes instruktion var uttrycklig: hitta inte på siffror, flagga i stället.
Det är gjort. **Datakällan är ditt och Sebbes beslut** — se §5.

### Fas 4 — fel & eskaleringar

Sammanfattar det som REDAN loggas: `platform_events` (samma data som fliken
Händelser, grupperad på källa + meddelande) och `ss_tickets` med status
`escalated`, som nu följer med i `list_tenants_with_stats` i båda lagringarna.
Inget nytt felsystem, ingen ny tabell, ingen Sentry — och en länk till
Händelser i stället för en andra kopia av listan.

En detalj värd att känna till: händelserna hämtas med tak (300). Är svaret
fullt prefixas talen "minst N". En trunkerad räkning som presenteras som
fullständig är samma klass av lögn som en uppskattning utan förbehåll.

---

## 2. Åtkomst och isolering — inget nytt släpptes på

Ingen ny inloggning, inga nya konton, ingen ny grind. Läsningen går genom
`getPlatformAdmin()` + masternyckeln precis som resten av `/admin`.

Skrivningen kunde inte gå via adminproxyn: `app/api/admin/[...path]` är
**GET-only med flit** ("en adminvy som kan ändra kunddata gör det förr eller
senare av misstag"). Den regeln är inte uppluckrad. Skrivvägen är i stället
server actions (`lib/actions/kunddata.ts`) med `getPlatformAdmin()` i varje
funktion — samma mönster som `agentinstruktioner.ts` valde av samma skäl: en
action är inte adresserbar och tar inga vägparametrar.

Backendmodulen är egen (`api/admin_kunddata.py`) och inte inbakad i
`admin.py`, som bär regeln "ingen endpoint här skriver", eller i
`admin_profil.py`, som ändrar hur agenten BETER sig. Fakturauppgifter och
promptinnehåll har olika blastradie; den som granskar en ändring i
agentinstruktionerna ska inte behöva läsa förbi ett telefonnummerfält.

**RLS:** båda tabellerna följer 029-mönstret — `snajp_app` kommer bara åt dem
när INGEN tenant-kontext är satt. Varje kundvänd kodväg sätter kontexten via
`_scoped()`, så registret är oåtkomligt därifrån per konstruktion. `snajp_web`
får inga rättigheter alls.

Fältlistan (`KUNDDATA_FALT`) och valideringen (`normalisera_kunddata`) bor i
`storage/base.py` och delas av båda lagringarna. Tre kopior av en fältlista
blir tre olika listor — det var precis så `agent_type`-buggen överlevde ett
halvår med grön svit.

---

## 3. Verifierat, och hur

- **1 505 backendtester gröna** (1 498 före mergen med din Resend-gren, 13 nya
  för registret: nyckelgrind, härledda källor, delvis sparning som inte
  nollställer, felformat datum → 422 med fältnamn, och ett kontakt-id ur EN
  kunds lista som INTE får mutera en annans).
- **tsc rent.**
- **`qa_vyer.mjs` mot körande dev: GRÖNT, inga avvikelser.** Anonym och kund
  får 404 på hela adminytan, admin når alla 17 vyer, `/admin/kunder` bär nya
  rubriken.
- **Nya detaljvyn besiktigad inloggad som admin:** 12 kundlänkar, alla
  sektioner renderar, bläddringen finns, 7 källmärken, noll JS-fel, noll
  4xx/5xx under laddning.
- **Nya API-routen bakom grinden:** anonymt anrop svarar 401.
- **Migration 053 applicerad före pushen**, så koden aldrig mötte en databas
  utan sina tabeller. Verifierad som `=` i liggaren efteråt.

**Vad som INTE gick att verifiera, och varför:** den lokala fullstacken
(`scripts/lokal_stack.py`) går inte att resa på maskinen — pgvector saknas i
lokala PostgreSQL 17, ingen Docker och ingen MSVC att bygga tillägget med.
UI:t granskades i stället genom en tillfällig preview-route med syntetisk data
plus Playwright-fullpage på 1440 och 375 px (noll konsolfel, noll horisontell
overflow, ljust och mörkt läge). Preview-routen är **inte** committad.
Skärmdumpar av dev-miljön togs medvetet inte: development speglar
produktionen och bär riktiga kunders uppgifter.

---

## 4. Att veta innan du rör koden

**Mergen med din Resend-gren gjordes i mitt led.** `development` hade flyttat
sig under kvällen (`dd12bfe`, HTTPS-sändvägen). Ren merge, inga konflikter —
men båda grenarna rörde `snajp-support/app/main.py` (du: Resend-konfig, jag:
routerregistrering). Båda överlevde, verifierat i kod och i sviten.

**Migration 053 är körd i development men INTE i main.** Går `main`-cutovern
någon gång måste den med i samma kedja.

**Nya kolumner i `list_tenants_with_stats`:** `kund_sedan`, `avtal_signerat`,
`escalated`. Rör du frågan — den finns i båda lagringarna — måste minnet
spegla Postgres exakt, annars är sviten grön mot en vy som visar fel tal i
drift.

---

## 5. Öppna frågor som är DINA, inte kodens

1. **Datakällan för intäkter och utgifter.** Fas 3 väntar på ett beslut, inte
   på kod: Stripe på riktigt, ett bokföringssystem (Fortnox?), eller en
   manuell rutin som matas in. Registret har nu strukturerade fält för
   kundens fakturauppgifter, vilket var ett av hindren i
   NO-GO-listans punkt 2 — men nummerserie, moms och betalleverantör saknas
   fortfarande, så faktureringskedjan är inte komplett.
2. **Definitionen av försäljningstakt.** Jag valde *nya kunder + signerade
   avtal per vecka, senaste fyra veckorna mot de fyra före*. Definitionen står
   utskriven i vyn så att den kan ifrågasättas, och den är en rad att ändra.
   Det finns ingen orderdata att räkna på, så varje annan definition kräver en
   annan datakälla.
3. **Snajps eget organisationsnummer är fortfarande `000000-0000`**
   (`lib/tenants/snajp.ts`). Orört av det här bygget — registret gäller
   KUNDERNAS uppgifter. Punkten står kvar från 27:e: `send_guard` blockerar
   första riktiga utskicket tills det är ifyllt.

## 6. Det som inte flyttade sig i kväll

SMTP-attrappen är din tråd och den rördes inte här. Gemini-kvoten
(`snipe-a1c`, P0) står kvar. `main` ligger kvar där den låg.

---

Kommitter: `694cf88` (fas 1) · `841e63e` (fas 2) · `4a23f7e` (fas 3+4) ·
`29411e4` (bläddring + kompaktare skala) · `a7127a8` (merge).
Grenen `feature/kunder-data` pekar på samma commit som `development`.
