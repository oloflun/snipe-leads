# Steg 5.1: inställningsskalet `/crm/installningar`

Bildernas prefix: `51-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

IN-001 till IN-018 (`docs/crm/underlag/app-08-installningar.md`, avsnitt A), och funktionslistans avsnitt "Inställningarna" (tabellen med
grupper, sektioner och adresser).

## Facit för beteendet (läs, kopiera inte formen)

`app/settings/[[...slug]]/page.tsx`, `app/settings/layout.tsx`, `components/settings/SettingsNav.tsx`,
`SettingsSection.tsx`, `lib/routes.ts` (`settingsGroups`, `settingsGroupsForProducts`: vem som ser vilken
sektion, `adminOnly`, `doldIDemo`, produktgrinden).

## Det som ska byggas

1. **Inställningsskalet** (NYTT MÖNSTER, `components/crm/app/installningar/Installningsskal.tsx`): en
   grupperad undermeny till vänster i bladet (på telefon: ett val överst), titel och beskrivning per
   sektion, och sektionens innehåll till höger. Twentys inställningssidor är förebilden
   (`docs/crm/underlag/twenty-12-ui-system-och-anvandarfloden.md`). Sektionerna är ett register
   (`lib/crm/installningar.ts`) i samma anda som navigeringsregistret: grupp, nyckel, adress, namn på två
   språk, vem som ser den (produkt, tillägg, roll, `adminOnly`), och `byggd`. Bara byggda sektioner visas.
2. **Sektionsgrinden på servern** (IN-00x om åtkomst): `app/crm/installningar/[[...sektion]]/page.tsx`
   avgör på servern om användaren får öppna sektionen, som dagens sida gör. En sektion man inte får se
   ger samma svar som en som inte finns.
3. **Lyft in Iris inställningar** från steg 4.5 (`/crm/installningar/iris`) i skalet utan att skriva om
   sektionerna: de ska ligga under gruppen Iris.
4. **Vägen dit:** posten Inställningar nederst i sidofältet (funktionslistans tabell), arbetsytemenyns
   Inställningar pekar om från `/settings` till `/crm/installningar`, och kommandopaletten får
   "Inställningar" med sektionerna som mål.
5. Sektionerna som inte är byggda än nås inte. Lägg INTE in länkar till dagens `/settings` för dem i
   skalet: skriv i rapporten vilka som återstår.

Commit: `feat(crm): installningsskalet med sektionsregister och Iris installningar inlyfta`.
