# Steg 4.1: skalets förutsättningar

Varje vy i fas 4 och 5 ärver det här. Utan det skriver ett kundbesök skarpt och navigeringen rymmer inte
resten av appen. Bildernas prefix: `41-`.

## Raderna

SK-038 till SK-045, SK-064 till SK-069, SK-071 till SK-079, SK-155 till SK-157 (underlaget
`docs/crm/underlag/app-01-skal-inloggning-onboarding.md`), och AD-005, AD-008 till AD-011
(`app-09-adminytan.md`). SK-070 tas inte med (pensionerat läge). Läs också funktionslistans avsnitt
"Navigeringen i det nya gränssnittet" (sidofältets tabell) och "Sekretess" punkt 5 till 7.

## Facit för beteendet (läs, kopiera inte formen)

`components/AppShell.tsx`, `components/shell/*`, `components/VyVaxel.tsx`, `components/ImpersonationBanner.tsx`,
`components/LasrollBanner.tsx`, `components/Felgrans.tsx`, `components/EjAktiverad.tsx`, `components/Laddar.tsx`,
`app/dashboard/layout.tsx`, `lib/routes.ts`, `lib/vy.ts`, `lib/data/dashboard.ts` (`DashboardState`:
`products`, `arLasare`, `impersonation`, `isDemo`, `vy`, `isPlatformAdmin`), och hur dagens rail hämtar
notisräknaren (`GET /api/snajp-support/leads/notiser/antal`).

## Det som ska byggas

1. **Navigeringen bär hela appen.** I dag har `CrmRam` två sektioner (Arbetsyta, Data) och vyerna är en
   fast union (`CrmVy`, `Objekt` i kit). Gör navigeringen till ett register (till exempel
   `lib/crm/navigering.ts`): grupper (Arbetsyta, Iris, Kundtjänst, Kvitton, Data, Plattform) med poster
   (nyckel, väg under `/crm`, namn på två språk, ikon, ton, vem som ser den: produkt, tillägg, roll).
   **Bara poster som gör något visas**: en post läggs till i registret av steget som bygger vyn. Efter
   ditt steg ska sidofältet se ut precis som i dag (Arbetsyta och Data), plus gruppen Iris med posten
   Leads, som nästa steg (4.2) fyller med vyn på `/crm/iris/leads`: lägg posten i registret bakom en
   flagga `byggd: false` så att den inte visas förrän 4.2 slår på den. Gruppen Iris syns bara när
   arbetsytan har produkten leads (`products` i `useDashboard()`).
   Befintliga vyer (`oversikt`, `bolag`, `personer`, `affarer`, `uppgifter`, `synk`, `sparrar`,
   `utvecklare`) ska fortsätta fungera utan att deras filer skrivs om: `OBJEKT` och `Objektikon` i kit
   används av dem. Vägar i flera led (`iris/leads`) ska fungera i både `/crm` och `/forhandsvisning/crm`.
   Kommandopaletten läser samma register.
2. **Banderollen** (NYTT MÖNSTER, `components/crm/app/Banderoll.tsx`): en fast rad överst i bladet för
   kundbesök ("Du testar som <kund>", med Avsluta), läsroll, och demo. Astryx `Banner` i Snajps tokens,
   en rad på bred skärm. Texterna och när de visas: SK-076 till SK-079 och AD-009. Avsluta kundbesöket
   anropar samma åtgärd som dagens banner.
3. **Läsroll och kundbesök i skalet.** `app/crm/layout.tsx` ärver grindarna (SK-038 till SK-042): läs hur
   `app/dashboard/layout.tsx` gör och se till att CRM:ets layout inte är svagare. Rör inte raden som
   släpper in bara plattformsadmin (Antons beslut). En liten hjälpare (till exempel `useSkrivratt()` i
   kit) som svarar om användaren får skriva och med vilken förklaring annars, så att varje senare vy
   stänger av skrivande knappar på samma sätt (SK-039).
4. **Notisräknaren och notislistan** (NYTT MÖNSTER, SK-064, AD-005): räknaren på menyposten Leads
   (i ockra som `crm-railtal`), och en klocka i skalet som öppnar en lista över svar, utkast och möten
   med Markera som lästa. Läs dagens rail och notislista för anropen. Posten Leads visas inte än, så
   räknaren ska sitta i registret och klockan visas bara när arbetsytan har leads.
5. **Arbetsyteväxlarens meny** (SK-065 till SK-069, SK-074, SK-075, AD-008, AD-010): Inställningar,
   Språk, Tema, Kontakt, Dataskydd, Anmäl felaktigt svar, Logga ut, och för plattformsadmin Byt kund
   (sökbar, `GET /api/admin/kunder`) och Admin/Demo. Läs vad `CrmRam` redan har och lägg till det som
   saknas. Byt kund finns också i kommandopaletten.
6. **Felgräns, laddning och "Din arbetsyta aktiveras"** (SK-044, SK-045, SK-155 till SK-157):
   `app/crm/error.tsx` och `loading.tsx` finns. Kontrollera dem mot raderna, och bygg väntläget för
   svaret `ej_aktiverad` som en delad komponent som vyerna kan visa i stället för ett tekniskt fel.

Förhandsvisningen: `?vy=kund`, `?besok=1` (kundbesök), `?roll=lasare` och `?demo=1` ska ge de fyra
lägena så att banderollen och avstängda knappar går att se. Notisräknaren och notislistan ska svara med
påhittad data.

Commit: `feat(crm): skalet bar hela appen: navigering som register, banderoll, notiser, lasroll och kundbesok`.
