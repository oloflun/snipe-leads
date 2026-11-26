# Plan: hela Snajp i det nya gränssnittet

Skriven 2026-11-26 efter Antons besked samma dag. Läget följs i
[`STATUS-MIGRERING.md`](STATUS-MIGRERING.md), som uppdateras efter varje arbetspass.

## 1. Uppdraget, med Antons ord

> Jag vill att du använder samma tillvägagångssätt och grundlighet för att kartlägga HELA
> den nuvarande appen och ALL funktionalitet och migrera det, bygga in det i det nya
> gränssnittet, i ett eget worktree, då vi behöver behålla nuvarande funktionalitet och
> inte kan ersätta hela development med en halvfärdig app i flera dagar. Så du bygger
> färdigt den separata CRM-delen enligt instruktionerna, som blir separat från den
> nuvarande appen.

Tre saker följer av det:

1. **Inget i dagens app tas bort eller byggs om på plats.** Det nya växer fram bredvid,
   under `/crm`, och når samma data.
2. **Ingenting får tappas.** Måttet är en funktionslista över dagens app där varje rad
   är byggd, verifierad eller uttryckligen inte gjord. Samma mått som paritetslistan mot
   Twenty.
3. **Formen är låst.** Allt byggs ur `DESIGN-CRM.md`, verktygslådan och bilderna.

## 2. Tillvägagångssättet (det som gav version 2)

Varje del går samma väg, och ingen del hoppar över ett steg:

1. **Läs.** En läsare per område skriver en funktionsbeskrivning rad för rad, med
   avprickningslista över katalogerna, och sparar efter hand.
2. **Komplettera.** En ny läsare med friskt utrymme fyller det som saknas och stickprovar
   minst tjugo rader mot källan.
3. **Leta luckor.** Granskare prickar av hela katalogträdet och varje rutt mot listan.
4. **Bygg i följd.** En byggare i taget, som återanvänder verktygslådan, tar bilder och
   rättar mot referensen innan nästa tar vid.
5. **Kontrollera.** Avgränsad typkontroll, invarianter, sökning efter färg utanför tokens.
6. **Granska oberoende.** Tre granskare (hantverk, användbarhet, tillgänglighet) läser
   bilderna mot referenserna. Fynd med hög och medel allvarlighet rättas.
7. **Huvudsessionen ser själv.** Färska bilder i 1440 och 390 px, ljust och mörkt, lästa
   en och en. Kontrast uppmätt. Först därefter commit.
8. **Kör mot riktig backend.** Varje flöde körs en gång mot den lokala stacken
   (`python scripts/lokal_stack.py --apply`), aldrig mot development-databasen.

## 3. Gren, worktree och hur dagens app skyddas

- **Eget worktree:** `.claude/worktrees/snajp-crm-app`, gren `claude/snajp-crm-app`,
  skuren ur `claude/snajp-crm-dd0d83` (där CRM-kärnan och version 2 ligger).
- **Följer development dagligen:** `git fetch origin` och `git merge origin/development`
  i början av varje pass. Aldrig rebase. Vid konflikt: stanna och redovisa.
- **Additivt:** nya sidor under `app/crm/`, nya komponenter under `components/crm/app/`,
  nya hjälpare under `lib/crm/`. Befintliga filer ändras bara där det är oundvikligt
  (rutter, grindarnas listor), och varje sådan ändring listas i statusfilen.
- **En backend, ett API.** Det nya gränssnittet anropar samma ändpunkter som dagens.
  Affärslogik kopieras aldrig till en andra plats. Saknas en ändpunkt läggs den till
  additivt, och migrationer är additiva och omkörbara så att schemat får ligga före koden.
- **Synligt bara för plattformsadmin** (`adminOnly` i `lib/routes.ts`) tills Anton säger
  annat. CRM:et är ett tillägg med fri tillgång under provperioden: grinden byggs i fas 3.
- **Inget pushas och inget går till development utan Antons ord**, fas för fas.
- **Reglerna gäller oförändrade:** kundisolering i varje fråga, webbplatsbedömningen
  hemlig utom för plattformsadmin, Umeå Webdesign och Alunix, ingen kunddata till
  DeepSeek, tvåspråkigt, förlopp och utfall där handlingen startades.

## 4. Faserna

Varje fas har en leverans och en grind. En fas är inte klar förrän grinden håller.

### Fas 0: lås referensen och inför Antons ändringar

- Version 2 låst i `DESIGN-CRM.md`, minnesanteckning skriven, svaren i `docs/BESLUT.md`.
- Sidofältet marinblått i båda lägena, Snajps logga, ockra som accent.
- **Grind:** bilder i 1440 och 390 px, ljust och mörkt, lästa av huvudsessionen.

### Fas 1: kartlägg hela den nuvarande appen

Tio läsare, ett område var, sedan kompletterare, luckgranskare och en sammanställare.

| Nr | Område | Var i koden |
|---|---|---|
| 1 | Skal, navigering, vyväxel, lägen, notiser, inloggning, onboarding, språk, tema, app på hemskärmen | `app/layout.tsx`, `app/dashboard/layout.tsx`, `components/AppShell.tsx`, `components/shell/`, `components/auth/`, `app/onboarding/`, `lib/routes.ts`, `proxy.ts` |
| 2 | Översikt, Att göra, Lärande | `app/dashboard/`, `components/dashboard/`, `components/leads/AttGora.tsx` |
| 3 | Leads: översikt, pipeline, tabell, bolagssök, leadets detalj | `components/leads/`, `lib/leads/` |
| 4 | Leads: körningar, profil och kriterier, källor, listor, webbpool, export | `components/leads/`, `snajp-support/app/leads/` |
| 5 | Leads: utkast, utskick, konversationer, uppföljningar, samtal, möten | `components/leads/`, `snajp-support/app/leads/`, `app/api/` |
| 6 | Support: ärenden, kunskapsbas, widget, supportagentens inställningar | `components/snajp/`, `app/dashboard/support/`, `snajp-support/app/api/` |
| 7 | Kvitton | `components/kvitton/`, `app/dashboard/kvitton/` |
| 8 | Inställningar, alla sektioner | `app/settings/`, `components/settings/` |
| 9 | Adminytan | `app/admin/`, `components/admin/` |
| 10 | API:t under ytorna: varje ändpunkt och vilken vy som använder den | `snajp-support/app/api/`, `app/api/` |

Varje rad i en läsares fil: ID, funktion, beteende och regler, var i koden (vy och
ändpunkt), data, roll och sekretess, förlopp och bakgrundsjobb, tvåspråkig eller inte.

- **Leverans:** `docs/crm/underlag/app-01` till `app-10`, luckrapporten `app-99`, och
  `docs/crm/MIGRERING-FUNKTIONSLISTA.md` med varje funktion och dess plats i det nya.
- **Grind:** varje rutt under `app/` och varje ändpunkt står i minst en rad.

### Fas 2: slutför inventeringen av Twenty och paritetslistan

- Område 13 (handboken som facit), kontrolläsning av områdena 3 och 5 till 12, tre
  luckgranskare.
- **Leverans:** `docs/crm/PARITET.md`: varje rad byggd, verifierad eller inte gjord.
- **Grind:** luckgranskarna har prickat av hela trädet, och motsägelser är avgjorda.

### Fas 3: CRM-kärnan färdig

Det som står gult eller rött i statusrapporten, plus besluten 2026-11-26.

| Del | Innehåll |
|---|---|
| Besluten i koden | Tidigare kunder fria för Iris. Uteslutning på nummer när numret finns. Privatpersoner hoppas över om inte anslutningen slår på dem. Tillägget som grind, fritt under provperioden |
| Synkens två nivåer | Kunden ser förlopp och fel i enkla ord med beskedet att det gått till supporten. Hela rapporten med koder lämnas som underlag till supportärendet (den andra sessionens system) |
| API ut | Webhooks med signatur, omförsök och leveranslogg. Ändringsflöde. Sortering nyast först. Namn på felrader. Papperskorg som vy |
| Objekten som saknas | Affärer med tavla, uppgifter, anteckningar, aktiviteter, bilagor |
| Tidslinjen | Leads, utkast, konversationer, samtal, uppföljningar och supportärenden på bolagets och personens tidslinje. Utfall speglas åt båda håll |
| Samlad kundlista | Egna kunder och Iris kunder i en lista, uppdelad på Iris och Egna |
| Svensk standard | SNI-uppslag, bolagsform, SEK och svenska format i hela ytan, registerdata, NIX. Bildgranskning av Lime, Upsales, SuperOffice, Membrain och Fortnox, och sammanställningen av vad som ändras mot Twenty och varför |
| Källsystemen | Testkonton i HubSpot, Pipedrive med flera, och en synk från vart och ett. Kräver Antons ja till varje konto |
| Astryx förhandsutgåvor | Diagram och kalender som utgångspunkt där de ger mer än det som finns |

- **Grind:** varje flöde kört mot den lokala stacken, med kundisolering prövad.

### Fas 4: Leads i CRM-miljön

Antons svar: tidigare kunder ska gå att bearbeta direkt i CRM:et, med samma funktioner
som Leads har i dag och en egen översikt över alla körningar.

- Körningarnas översikt, start av körning, förlopp och utfall.
- Bolag, pipeline, listor, utkast och granskning, utskick, konversationer, uppföljningar,
  samtal och återkoppling, i CRM:ets form.
- **Grind:** raderna för Leads i funktionslistan är alla byggda och verifierade.

### Fas 5: resten av appen

Översikt och Att göra, Support, Kvitton, Lärande, Inställningar, Adminytan, inloggning
och onboarding. En del i taget, i funktionslistans ordning.

- **Grind:** funktionslistan har ingen rad som är "inte gjord" utan Antons ord.

### Fas 6: växlingen

- Båda apparna körs sida vid sida. Varje vy jämförs med sin gamla, funktion för funktion.
- Anton avgör när kunderna får det nya. Gamla adresser leder om. Gammal kod tas bort
  först efter hans ord, i en egen ändring.

## 5. Kvot och takt

Veckokvoten stod på 64 procent 2026-11-26 efter drygt ett dygn, och den delas med
nattjobben. Därför:

- Högst tre agenter åt gången. Byggare alltid i följd.
- En stor körning startas när femtimmarsfönstret är nollställt, aldrig mitt i ett.
- Huvudsessionen arbetar inte parallellt med en körning, utom för att skriva dokument.
- Fas 1 och 2 är omkring 25 agenter. Fas 3 till 5 är flera dagars bygge och ryms inte i
  den här veckans kvot. Antingen sprids de över nollställningen 2026-12-02, eller så
  slår Anton på extra användning.

## 6. Risker

| Risk | Motåtgärd |
|---|---|
| En funktion tappas i flytten | Funktionslistan är grinden, och luckgranskare prickar av varje rutt |
| Två sanningar om samma logik | En backend. Det nya gränssnittet anropar samma ändpunkter |
| Development drar ifrån | Daglig sammanslagning från development |
| Webbplatsbedömningen läcker i en ny vy | Varje vy som visar den grindas i samma ändring, och INV-SEC-008 gäller |
| Kvoten tar slut mitt i ett bygge | Varje agent skriver efter hand, och statusfilen säger var arbetet står |
| Formen glider | Låst kontrakt, verktygslåda och bildgranskning mot referensen före commit |
| Maskinen kraschar av minnesbrist | En server åt gången, avgränsad typkontroll, allt tungt på D: |

## 7. Det som väntar på Anton

1. Ja till att öppna testkonton i källsystemen (HubSpot, Pipedrive med flera).
2. Om `astryx init` får skriva sitt block i `CLAUDE.md` och `AGENTS.md`.
3. Om extra användning ska slås på, eller om fas 3 till 5 sprids över veckorna.
4. Dom över sidofältet när bilderna finns.
