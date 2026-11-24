# Startsidans lagg, felvägarna och kundresan (2026-11-23)

Arbetsgren `buddy-demo-prep`, utgår från `origin/development` vid `15227ef4`,
ihopslagen med `development` 2026-11-24 och pushad dit. Uppdraget kom från
Sebastian. Delarna om en särskild testkund ströks under arbetet och finns inte
med här.

## 1. Bedömning mot målen

| Mål i uppdraget | Utfall | Nått |
|---|---|---|
| Lighthouse mobil ≥ 90 (startsidan) | 51 → 73 | Nej |
| Lighthouse desktop ≥ 95 (startsidan) | 90 → 94 | Nej, en poäng ifrån |
| LCP < 2,5 s (mobil) | 7,6 → 5,3 s | Nej |
| TBT < 200 ms (mobil) | 936 → 260 ms | Nej, nära |
| CLS < 0,1 | 0 → 0 | Ja |
| Stabila 60 bilder per sekund vid fyra gångers CPU-strypning | 24 % → 23,5 % sena huvudtrådsrutor | Nej, se 3.2 |
| Inga synliga fel, statuskoder eller teknisk text för kunden | Sexton kända läckor stängda | Ja för de kända, se 2.2 |
| Kundresan automatiserad som e2e-test | 11 steg, tre gröna körningar i rad mot development | Ja, i Chromium |
| Iris hittar leads och skriver utkast för en ny kund | Ett lead på nivå A med utkast på 45 s | Ja, se 6 |
| Supportagenten svarar ur kundens egen kunskapsbas | Ja, på 6 s | Ja, en fråga prövad |

Sidan är tydligt snabbare att ladda och hackar inte längre i scrollen på en
långsam maskin, men den når inte uppdragets siffror på mobil. I development når
desktop målet (97). Det som återstår är strukturellt och står i avsnitt 5.

## 2. Vad som ändrats

### 2.1 Startsidan

1. **Mjukscrollen lämnar över när den inte hinner** (`smooth-scroll.js`). Lenis
   flyttar sidan från huvudtråden, och varje scrollad bildruta kostar runt 17 ms
   där vid fyra gångers strypning även när ingenting rör sig. Med webbläsarens egen
   scroll kostar samma bildruta en tredjedel och scrollen sköts av kompositorn.
   Lenis står kvar som hustakt, men lämnar över när bildrutor tappas: under de
   första fyra sekunderna vid 35 % tappade av sextio, därefter under scroll vid
   20 %. Valet minns för webbläsarsessionen. Beslutet står i `docs/BESLUT.md` och
   väntar på Antons ord.
2. **Dygnsljuset målar inte om sidan varje bildruta** (`useLandingMotion.ts`,
   `globals.css`). Färgerna skrivs i steg om 0,0025 i OKLab, och marken och
   ljuslagret har egna kompositlager. Dokumentet målades om 499 gånger under en
   scroll; i vila med allt avtäckt målas det nu ett tiotal gånger.
3. **Rörelsen ställs upp i två omgångar.** Det som ligger inom en och en halv
   skärm direkt, resten i pass om åtta millisekunder. Den längsta uppgiften vid
   laddning gick från 1 137 till 259 ms (fyra gångers strypning).
4. **Text som skrivs fram uppdateras högst var trettionde millisekund**
   (`lib/skrivs.ts`): 1 214 målningar av produktpanelerna blev 652.
5. **`gsap.js` laddar tre delar i stället för arton.** 68 kB oanvänd kod bort.
6. **Typsnitt förladdas per sida** (`lib/fonts.ts`, `lib/fonts-rubrik.ts`,
   `lib/fonts-landning.ts`). Förut förladdade varje sida sex filer, 580 kB.
   Startsidan förladdar nu 316 kB, övriga sidor 333 kB.
7. **Foton i rätt bredd** (`photoSet` i `copy-sections.ts`): smalare varianter och
   `srcset`. Gatufotot 524 → 211 kB, hjältefotot 152 → 63 kB på en telefon. De två
   fotobanden var CSS-bakgrunder som hämtades med sidan och är nu latladdade bilder.
8. **Cache för `public/`** (`next.config.ts`): foton, ikoner och logotyper
   serverades med `max-age=0` och cachas nu en vecka.
9. **Chatten frågar inte backenden i onödan** (`SupportChat.tsx`): en besökare
   utan tidigare samtal i fliken har inget att hämta. Förut gick ett anrop per
   visning av startsidan, och ett rött konsolfel visades om backenden startade om.

Utseendet är oförändrat. `scripts/jamfor_startsida.mjs` jämförde den gamla och den
nya versionen bild för bild på `/`, `/leads` och `/support` i 1440 och 390 punkters
bredd: sidhöjden är densamma, inget element står kvar dolt, och bilderna skiljer
bara i fotona (den smalare varianten) och med en nivå per färgkanal i bakgrunden.

### 2.2 Felvägarna

Det här kunde nå en kund före ändringarna:

| Vad kunden såg | Var | Nu |
|---|---|---|
| `[object Object]` i rött | Kunskapsbasen vid för lång text, och femton ställen till som läste `detail` rakt av | `kroppsbesked()` i `lib/http/besked.ts` ger alltid en mening |
| `'NoneType' object has no attribute 'get'` | Körningsrutan vid programfel (`leads.py`) | Reservmeningen; egna domänfel passerar som förut |
| "Kräver en riktig LLM-nyckel (DEEPSEEK_API_KEY). Se DEPLOY_KEYS.md" | Kör Iris utan modellnyckel | "Iris kan inte köras just nu. Felet ligger hos oss" |
| "Fyll product_marketing ... TENANTS.md steg 5" | Utkastets anteckning | Hänvisar till Inställningar, Vad ni säljer |
| Resends råa JSON | Provmejl som föll | Fast mening, originalet i loggen |
| pypdf:s feltext, "(TypeError)" | PDF-läsning, avbruten webbplatsskanning | Fasta meningar |
| "Timtaket för tenant är nått (400/400 LLM-anrop)" | Chatten vid timtak | "Agenten har nått sitt tak för den här timmen" |
| Postgres feltext, Auth.js typnamn | Registrering, onboarding | Fasta meningar, originalet i loggen |
| "Kör scripts/railway_tenantnyckel.py", "SNAJP_MASTER_API_KEY är inte satt" | Varje inloggad yta när arbetsytan inte gick att öppna | `kundbesked` på `SnajpTenantError`; driftens text loggas |
| Statuskoder i felrader ("Kunde inte spara (422)") | Kunskapsbas, inkorgar, regler, webbplatsförslag, PDF | Meningar utan kod |

Två saker till i samma genomgång:

- **Öppen omdirigering.** `/login?next=https://annan-sajt.se` loggade in
  användaren och lämnade av den på den främmande sajten. `sakerNasta()` i
  `lib/auth/nasta.ts` släpper bara igenom vägar på den egna sajten.
- **Testchatten föreslog en påhittad butiks frågor** ("felkod E-101 i kassan",
  "pengarna tillbaka NU!") för en nyregistrerad kund. Den sista lämnar dessutom
  över samtalet till en människa och låser testchatten. Nya kunder får neutrala
  förslag.

## 3. Mätningar

Allt är mätt mot produktionsbygget (`npm run build && npx next start -p 3100`) på
samma maskin, medianen över flera körningar. Rådata ligger i `matning/`.

### 3.1 Laddning (Lighthouse)

Startsidan, fem körningar per enhet:

| | Poäng | FCP | LCP | TBT | CLS | Speed Index | Vikt |
|---|---|---|---|---|---|---|---|
| Mobil före | 51 | 1,30 s | 7,56 s | 936 ms | 0 | 4,95 s | 1 306 kB |
| Mobil efter | 73 | 1,23 s | 5,27 s | 260 ms | 0 | 4,19 s | 734 kB |
| Desktop före | 90 | 0,29 s | 1,53 s | 125 ms | 0,001 | 1,91 s | 1 306 kB |
| Desktop efter | 94 | 0,30 s | 1,45 s | 1 ms | 0,001 | 1,38 s | 821 kB |

Övriga publika sidor, tre körningar per enhet (poäng, LCP):

| Sida | Mobil före | Mobil efter | Desktop före | Desktop efter |
|---|---|---|---|---|
| `/leads` | 54, 7,5 s | 67, 5,8 s | 94, 1,4 s | 98, 1,1 s |
| `/support` | 60, 7,5 s | 67, 5,8 s | 95, 1,4 s | 98, 1,1 s |
| `/faq` | 77, 5,9 s | 82, 4,5 s | 98, 1,1 s | 99, 0,9 s |
| `/login` | 77, 5,9 s | 82, 4,5 s | 98, 1,1 s | 99, 0,9 s |
| `/integritetspolicy` | 76, 5,9 s | 82, 4,5 s | 98, 1,2 s | 99, 0,9 s |

`/leads` och `/support` är mätta innan deras fotoband gjordes om till en latladdad
bild (sista ändringen), så deras vikt och LCP är något bättre än tabellen visar.

Lighthouse simulerar en långsam telefon ur en snabb körning. LCP-siffran på mobil
består till fyra femtedelar av "render delay": hjältefotot är nedladdat tidigt, men
den första bilden av sidan ritas först när sidan räknat ut sin layout och kört sina
skript. Se avsnitt 5.

### 3.2 Scroll

Hela sidan scrollad uppifrån och ned och tillbaka, fem körningar. "Sena" är
bildrutor på huvudtråden som tog över 25 ms.

| | Sena bildrutor | Hack över 50 ms | Långa uppgifter | Vem äger scrollen |
|---|---|---|---|---|
| Desktop, 4× strypning, före | 24 % | 0 | 0 | Lenis |
| Desktop, 4× strypning, efter | 23,5 % | 5 | 0 | Webbläsaren i 5 av 5 |
| Desktop, 6× strypning, före | 43,9 % | 50 | 18 st, 1 012 ms | Lenis |
| Desktop, 6× strypning, efter | 36,9 % | 49 | 23 st, 1 295 ms | Webbläsaren i 5 av 5 |
| Telefon (svepgester), 4×, före | 0,9 % | 5 | 3 st, 207 ms | Webbläsaren |
| Telefon (svepgester), 4×, efter | 0,3 % | 0 | 0 | Webbläsaren |

**Siffrorna för desktop ska läsas rätt.** Andelen sena huvudtrådsrutor är i stort
sett oförändrad. Det som ändrats är vad en sen bildruta betyder. Före var varje
sen bildruta ett ryck i scrollen, eftersom huvudtråden flyttade sidan. Efter har
scrollen lämnats över till webbläsaren i alla fem körningar, och då står scrollen
stadigt medan animationerna på sidan kan släpa. Att scrollen faktiskt ritas jämnt
efter överlämningen har jag **inte kunnat mäta**: webbläsarens egen bildruterapport
visade sig oanvändbar i ett fönster som styrs av Playwright (den rapporterar 98 %
uteblivna bildrutor även när sidan går felfritt). Påståendet vilar på hur
webbläsaren är byggd, inte på en mätning här. Utan strypning behåller sidan
mjukscrollen.

På telefon är förbättringen mätt: inga hack och inga långa uppgifter under scroll.

### 3.3 Vad huvudtråden gör (spårning, 4× strypning)

| | Före | Efter |
|---|---|---|
| Längsta uppgift vid laddning | 998–1 137 ms | 834 ms (första layouten) |
| Rörelsens uppsättning | 1 137 ms i ett svep | 259 ms, resten i korta pass |
| Långa uppgifter vid laddning | 6 st, 2 636 ms | 4 st, 1 343 ms |
| Målningar av dokumentet under scroll | 499 | 295 |
| Målningar av produktpanelerna under scroll | 1 214 | 652 |
| Målningar i vila med allt avtäckt | 28 per fem sekunder | 3–13 |

## 4. Kundresan som test

`tests/e2e/kundresa.spec.ts` går registrering, onboardingens sex steg, arbetsytans
vyer, isolering, kunskapsbasen, testchatten, Iris körformulär och sessionen. Det
fäller på varje konsolfel och varje svar med 4xx eller 5xx, och avbryter varje
anrop till en sändväg så att inget mejl kan lämna huset.

Det är kört mot development: tre gröna körningar i rad, varav en med riktiga
modellanrop (`KUNDRESA_LIVE=1`). Utfallet står i avsnitt 6.

Repot har ingen Playwright i `package.json`, med flit (samma val som
`scripts/qa_*.mjs`): `npm i --no-save @playwright/test` före körning.

## 5. Vad som återstår för att nå målen

Rangordnat efter hur mycket det väger.

1. **Hydreringen av startsidan.** `LandingPhoto` är en enda klientkomponent som
   bär hela sidan, med e-postredigeraren, chatten och inkorgsdemon inuti. Allt
   hydreras vid laddning, och det är det som håller hjältefotot från att ritas.
   Demoytorna under vecket bör laddas och hydreras först när de närmar sig bilden.
2. **Första layouten** tar runt 740 ms vid strypning. `text-wrap: pretty` på
   `body` står för ungefär en tredjedel, mest inne i demopanelerna där den inte gör
   nytta. Att begränsa den till löptexten är en liten ändring men rör
   radbrytningen, alltså ett typografiskt val för Anton.
3. **Den fasta kostnaden per bildruta under mjukscroll.** Säkringen tar hand om
   maskiner som inte hinner, men en besökare på en sådan maskin får webbläsarens
   scroll i stället för hustakten.
4. **Typsnittens storlek.** Source Serif 4 och Fraunces med optisk storlek som axel
   är 118–146 kB per fil. Kursiven förladdas fast den används på enstaka ord.

## 6. Verifiering i development

Efter push till `development` (2026-11-24 00:25), mot
`web-development-6c85.up.railway.app`.

**Kundresan** (`BASE=<development> npx playwright test -c tests/e2e --project=chromium`),
en nyskapad testkund per körning med adress under `example.com`:

| Steg | Utfall |
|---|---|
| Publika sidor laddar utan konsolfel eller felsvar (nio sidor) | Godkänt |
| Registrering landar i onboardingen | Godkänt |
| Onboarding: tomt formulär, ogiltigt organisationsnummer, omladdning mitt i | Godkänt |
| Onboarding: sex steg, Tillbaka bär kvar värdena, dubbelklick på sista knappen | Godkänt |
| Arbetsytan bär kundens egen text och börjar tom (inga andras leads, körningar, kunskap) | Godkänt |
| Tjugoen vyer i arbetsytan och inställningarna öppnas utan fel eller teknisk text | Godkänt |
| Isolering: okända id ger 404, utan session 401, adminytan 404 | Godkänt |
| Kunskapsbasen: spara, och för lång text ger en mening i stället för `[object Object]` | Godkänt |
| Supportagenten svarar i testchatten | Godkänt, riktigt svar |
| Iris: körning på ett lead ger lead och utkast | Godkänt, riktig körning |
| Utloggning, skyddad sida utan session, `?next=` till annan sajt, två flikar | Godkänt |

Tre körningar i rad gick igenom: en med alla elva stegen, två där de två stegen med
modellanrop hoppades över (nio av nio). Inget anrop till en sändväg försöktes.

Vad de riktiga anropen gav:

- **Supportagenten**, frågan "Hur kommer jag i kontakt med er?", svar på sex
  sekunder: "Du når oss på vardagar mellan 08 och 17. Ställ din fråga här i chatten
  så hjälper vi dig vidare." Uppgiften kommer ur artikeln testet just sparat i
  kundens kunskapsbas.
- **Iris**, ett beställt lead: klar på 45 sekunder, två bolag undersökta, ett
  levererat med motivering och utkast med ämnesrad och brödtext. En tidigare
  körning undersökte fyra bolag och levererade ett på nivå A med citat från bolagets
  sajt som belägg, och lade fyra bolag i ringlistan.

Det här är en fråga och två körningar, alltså ett bevis på att kedjan fungerar för
en nyregistrerad kund, inte en bedömning av kvaliteten över många fall.

**Publika sidor** (`scripts/jamfor_startsida.mjs` mot development): `/`, `/leads`
och `/support` i 1440 och 390 punkters bredd. Inget element kvar dolt, inga
konsolfel, ingen `will-change` kvar efter att rörelsen lagt sig.

**Lighthouse**, startsidan, tre körningar per enhet:

| | Poäng | FCP | LCP | TBT | Vikt |
|---|---|---|---|---|---|
| Produktionen i dag (snajp.se, gamla koden), mobil | 59 | 2,13 s | 6,65 s | 515 ms | 1 294 kB |
| Development med ändringarna, mobil | 79 | 1,25 s | 4,15 s | 267 ms | 723 kB |
| Produktionen i dag, desktop | 92 | 0,61 s | 1,39 s | 81 ms | 1 294 kB |
| Development med ändringarna, desktop | 97 | 0,38 s | 1,13 s | 34 ms | 810 kB |

**Testkonton som ligger kvar i development.** Varje körning skapade ett konto
`e2e-kund+<åtta siffror>@example.com` med arbetsytan "E2E Testbolaget <siffror> AB",
sex stycken. Notismejlen är avslagna och adressen kan inte ta emot mejl.
`scripts/qa_radera_konto.py` vägrar radera dem, med rätta: de bär en egen
kunskapsbasartikel och två av dem har leads. Jag har inte raderat något för hand i
en databas som speglar produktionen. De försvinner vid nästa spegling, eller tas
bort med `scripts/gdpr_radera.py`.

## 7. Det som inte gick att göra

- **Lokal helstack.** Den lokala Postgres saknar pgvector, och Docker Desktop
  startar ingen motor eftersom WSL inte är installerat. Inloggade flöden går därför
  inte att köra på utvecklingsmaskinen. `wsl --install` (admin och omstart) löser det.
- **Körning i fler webbläsare.** Testet har projekt för WebKit, telefon och
  surfplatta, men är bara kört i Chromium. Utloggningen på smal skärm ligger i en
  meny, och den vägen är oprövad.
- **Supportagentens kvalitet över många frågor** (uppdraget nämnde femton) och
  chattwidgeten på en kunds sajt. En självregistrerad kund har ingen publik chatt
  förrän den lagts upp i `lib/tenants/`, så det finns ingen widget att pröva för en
  ny kund.
- **Varje knapp i varje vy.** Testet öppnar alla vyer och fäller på fel, men
  klickar inte på varje knapp i dem.

## 8. Mäta om

```
npm run build && npx next start -p 3100
npm i --no-save playwright lighthouse
node scripts/mat_startsida_lighthouse.mjs          # median över fem körningar
node scripts/mat_startsida_scroll.mjs              # bildrutor under scroll, 4x och 6x
node scripts/mat_startsida_spar.mjs                # vad huvudtråden gör
node scripts/mat_startsida_detalj.mjs /            # LCP-faser, vikt, typsnitt
FORE=<gammal> EFTER=<ny> node scripts/jamfor_startsida.mjs   # bild för bild
```

Mät aldrig med något annat tungt igång på maskinen: en ensam körning varierar
30–50 %. I Git Bash behövs `export MSYS_NO_PATHCONV=1`, annars görs `/` om till en
Windows-sökväg.
