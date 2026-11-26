# Paritet 08: Inloggning, arbetsyta, roller och säkerhet

Området är skalet runt CRM-datan i Twenty: konto och arbetsyta, inloggning med tvåfaktor och SSO, medlemmar och inbjudningar, roller med behörighet per objekt, fält och rad, sessioner, fakturering, händelseloggar och serveradmin. Snajp CRM har ingen egen inloggning utan delar Snajps (`lib/auth.ts`, grindad av `proxy.ts` och `app/crm/layout.tsx`), så inloggningens mekanik räknas som byggd när den gäller för CRM:et, medan inställningssidor som bara finns i dagens `/settings` (nås via CRM-menyns Inställningar) räknas som delvis med fas 5, där planen flyttar dem in i den nya ytan.

Antal per läge: ANTAL_RAD

## De största luckorna

LUCKOR_HAR

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| AR-001 | Varje arbetsyta har två inbyggda roller, Admin och Member, och minst en Admin måste alltid finnas. | delvis | Rollerna owner, member och viewer finns på profilen (`lib/actions/team.ts`, `ROLES`), och bara ägaren bjuder in. Saknas: skyddet mot att arbetsytan blir utan ägare, och roller i CRM:ets egen yta. | 5 |
| AR-002 | Admin kan skapa en egen roll med namn och behörigheter. | inte gjord | Inga egna roller; rollen är ett av tre fasta textvärden. | ej planerad |
| AR-003 | Admin kan radera en egen roll, och dess medlemmar flyttas till standardrollen. | inte gjord | Inga egna roller att radera. | ej planerad |
| AR-004 | Admin ser alla roller och hur många medlemmar som har var och en. | delvis | Team-sidan listar varje medlem med sin roll (`components/settings/TeamSettings.tsx`, `listTeam` i `lib/actions/team.ts`). Saknas: rollista med antal. | 5 |
| AR-005 | Admin tilldelar en roll till en befintlig medlem från rollens sida. | inte gjord | Rollen sätts bara i inbjudan; ingen tilldelning i efterhand. | 5 |
| AR-006 | Admin byter en medlems roll från medlemmens profilsida. | inte gjord | Ingen funktion för rollbyte i `lib/actions/team.ts`. | 5 |
| AR-007 | Admin väljer vilken roll nya medlemmar får som standard. | inte gjord | Ingen valbar standardroll; en ny registrering blir ägare av sin egen arbetsyta och en inbjuden får inbjudans roll. | ej planerad |
| AR-008 | En roll har grundbehörigheter för att se, ändra, radera och förstöra poster i alla objekt. | delvis | Läsa och skriva skiljs åt: API-nyckelns omfång `crm:las` och `crm:skriv` (`snajp-support/app/crm/nycklar.py`) och läsrollen `viewer` som spärrar varje skrivning i webbens proxy (`app/api/snajp-support/_auth.ts`). Saknas: egna rättigheter för mjukradering och permanent radering, och behörighet per roll. | ej planerad |
| AR-009 | En roll kan ha undantag per objekt som går före grundbehörigheten. | inte gjord | Ingen behörighet per objekt. | ej planerad |
| AR-010 | Inom en objektregel kan läsa och ändra sättas per fält. | inte gjord | Ingen behörighet per fält. | ej planerad |
| AR-011 | Behörigheter ärvs från alla objekt till objekt till fält, och det mest specifika vinner. | inte gjord | Ingen ärvd behörighetsmodell. | ej planerad |
| AR-012 | En roll kan begränsas till vissa poster med radvillkor. | avstår | Enterprise-fil i förlagan. Kundisoleringen (radskydd per kund på varje CRM-tabell) är en annan sak och berörs inte. | |
| AR-013 | En roll kan få åtkomst till inställningar, allt eller per område. | delvis | Omfånget `crm:admin` styr anslutningar, mappning och webhooks (`kraev("crm:admin")` i `snajp-support/app/api/crm_v1.py`), och bara ägaren bjuder in (`lib/actions/team.ts`). Saknas: rättighetsflaggor per roll för användare. | ej planerad |
| AR-014 | En roll kan få åtkomst till verktyg som e-post, CSV-import och CSV-export, allt eller per verktyg. | inte gjord | Inga verktygsrättigheter; CRM:et har varken import eller export i gränssnittet. | ej planerad |
| AR-015 | En roll kan tilldelas en API-nyckel så att nyckelns anrop begränsas av rollen. | avstår | Ersätts av omfång på nyckeln (`snajp-support/app/crm/nycklar.py`, prövat i `test_varje_omfang_oppnar_bara_sitt` i `snajp-support/tests/crm/test_api.py`). | |
| AR-016 | En roll kan tilldelas en AI-agent. | inte gjord | CRM:et har inga AI-agenter och anropar ingen språkmodell (`docs/crm/SVENSK-STANDARD.md` § 2.6). | ej planerad |
| AR-017 | Rättigheten att imitera låter en medlem se arbetsytan som en annan medlem. | delvis | Bara plattformsadmin kan besöka en kund via vyväxeln (`bytVy` i `lib/actions/vy.ts`), och CRM:et visar då den kundens data (`app/crm/layout.tsx`). Saknas: rättigheten per roll och imitation av en enskild medlem. | ej planerad |
| AR-018 | Rättigheten Ask AI kan tas bort från en roll för att stänga av AI. | inte gjord | CRM:et har ingen AI att stänga av. | ej planerad |
| AR-030 | Admin bjuder in en person med e-post och vald roll, och personen får ett mejl. | delvis | `inviteMember(email, role)` i `lib/actions/team.ts`, Team-sidan nås via CRM-menyns Inställningar. Saknas: mejlet (koden säger själv att inbjudan inte mejlas än) och sidan i CRM:ets yta. | 5 |
| AR-031 | Admin kopierar en delbar inbjudningslänk för arbetsytan. | inte gjord | Ingen publik inbjudningslänk. | senare |
| AR-032 | Admin ser aktiva medlemmar och väntande inbjudningar. | delvis | `listTeam` visar medlemmar och obrukade inbjudningar i en lista (`lib/actions/team.ts`, `components/settings/TeamSettings.tsx`). Saknas: sidan i CRM:ets yta. | 5 |
| AR-033 | Admin skickar om eller återkallar en väntande inbjudan. | delvis | Återkalla finns (`revokeInvite` i `lib/actions/team.ts`). Saknas: skicka om. | 5 |
| AR-034 | Admin ändrar en medlems namn och profilbild. | inte gjord | Ingen profilredigering av andra medlemmar. | senare |
| AR-035 | Admin imiterar en medlem från medlemmens profilsida. | delvis | Plattformsadmin besöker en hel kund via vyväxeln (`lib/actions/vy.ts`). Saknas: imitation av en enskild medlem inifrån arbetsytan. | senare |
| AR-036 | Admin tar bort en medlem ur arbetsytan och medlemmens poster ligger kvar. | inte gjord | `lib/actions/team.ts` har ingen borttagning av medlem. | senare |
| AR-037 | Admin ger en medlem en engångskod för att återställa tvåfaktor. | inte gjord | Ingen admin-utfärdad återställningskod. | senare |
| AR-038 | Medlem utan autentiseringsapp loggar in med en återställningskod och sätter upp tvåfaktor på nytt. | delvis | Kontots egna återställningskoder godtas en gång vid inloggning (`provaOchForbruka` i `lib/auth/tvafaktor.ts`, testet "återställningskod loggar in en gång, sedan inte igen" i `lib/auth/inloggningssteg.test.ts`). Saknas: kod utfärdad av admin, och att metoden tas bort och sessionerna loggas ut. | senare |
| AR-039 | Användaren ändrar sitt visningsnamn och sin profilbild. | inte gjord | Ingen profilsida; namnet sätts vid registreringen. | senare |
| AR-040 | Användaren byter inloggningsadress efter verifiering av den nya. | inte gjord | Inget e-postbyte. | senare |
| AR-041 | Användaren aktiverar tvåfaktor med autentiseringsapp och QR-kod. | delvis | Finns för plattformsadmin på `/admin/installningar/tvafaktor` (`components/settings/Tvafaktor.tsx`, `lib/actions/tvafaktor.ts`). Saknas: för kundens användare och i CRM:ets yta. | 5 |
| AR-042 | Användaren byter lösenord, minst 8 tecken. | delvis | `updatePassword` i `lib/actions/auth.ts` med minst 8 tecken, nås via återställningslänken (`app/auth/reset`, `components/auth/ResetPasswordForm.tsx`). Saknas: byte i inloggat läge från en inställningssida. | 5 |
| AR-043 | Användaren raderar sitt konto efter att ha skrivit sin e-postadress. | inte gjord | Ingen självradering av konto. | senare |
| AR-044 | Användaren ser sina inloggade enheter och sessioner. | inte gjord | Sessionen är en JWT utan serverlagrad rad (`lib/auth.ts`), så det finns ingen lista att visa. | ej planerad |
