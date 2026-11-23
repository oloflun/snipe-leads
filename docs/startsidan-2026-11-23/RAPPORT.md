# Startsidans lagg, felvägarna och kundresan (2026-11-23)

Arbetsgren `buddy-demo-prep`, utgår från `origin/development` vid `15227ef4`.
Uppdraget kom från Sebastian. Delarna om testkunden Buddy AB ströks under arbetet
och finns inte med här.

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
| Kundresan automatiserad som e2e-test | Skrivet, inte kört | Nej, se 4 |

Sidan är tydligt snabbare att ladda och hackar inte längre i scrollen på en
långsam maskin, men den når inte uppdragets siffror. Det som återstår är
strukturellt och står i avsnitt 5.

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

Se avsnitt 6 för läget efter körningen mot development.

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

**Ej klart.** Fylls i efter push.

## 7. Det som inte gick att göra

- **Lokal helstack.** Den lokala Postgres saknar pgvector, och Docker Desktop
  startar ingen motor eftersom WSL inte är installerat. Inloggade flöden går därför
  inte att köra på utvecklingsmaskinen. `wsl --install` (admin och omstart) löser det.
- **Körning i fler webbläsare.** Testet har projekt för WebKit, telefon och
  surfplatta, men är bara tänkt att köras i Chromium tills väljarna satt sig.

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
