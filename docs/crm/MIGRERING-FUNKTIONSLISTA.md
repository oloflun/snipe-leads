# Funktionslistan för flytten till Snajp CRM

Skriven 2026-11-26 av sammanställaren i fas 1 av
[`PLAN-MIGRERING.md`](PLAN-MIGRERING.md). Läget följs i
[`STATUS-MIGRERING.md`](STATUS-MIGRERING.md). Formen är låst i
[`DESIGN-CRM.md`](DESIGN-CRM.md).

## Vad listan är till för

Det här är listan som avgör när flytten är klar. Varje funktion som finns i dagens app
(arbetsytan under `/dashboard`, inställningarna under `/settings`, adminytan under
`/admin`, inloggning och onboarding, och API:t under ytorna) står här som en rad, med
platsen den får i det nya gränssnittet under `/crm`, fasen den byggs i, om backenden
redan bär den och läget. Planens grind för fas 5 är att ingen rad står som "inte gjord"
utan Antons ord.

**Källorna.** Raderna är läsarnas, med deras ID, ur de elva underlagen i
[`underlag/`](underlag/): `app-01` till `app-10` och luckgranskningen `app-99`. Där en
funktion beskrivs i detalj (beteende, gränser, felmeddelanden, tomlägen, roll,
tvåspråkighet) står det i läsarens fil under samma ID. Den här listan upprepar inte det;
den säger var funktionen hamnar. Den som bygger en vy läser läsarens rader för vyn innan
hen börjar.

**Antal.** 1 306 rader: 1 292 från läsarna och 14 från luckgranskningen. Samma tal som
`app-99` avsnitt F. Inga ID-dubbletter.

## Hur kolumnerna ska läsas

| Kolumn | Betydelse |
|---|---|
| ID | Läsarens ID. Prefixet säger filen: SK app-01, OV app-02, LR app-03, LK app-04, LU app-05, SU app-06, KV app-07, IN app-08, AD app-09, AP app-10, LX app-99. |
| Funktion | Läsarens rubrik för funktionen, ordagrant (kortad efter 200 tecken). |
| Plats i det nya gränssnittet | Vyn under `/crm`, om den är **ny** eller **befintlig** i dag, och mönstret ur verktygslådan som den byggs med (efter punkten). **Ingen egen vy** betyder att funktionen bor i backenden eller i en grind och bara ska fortsätta fungera; den syns som utfall där raden säger. **Utanför `/crm`** betyder att ytan behålls där den är (widgeten, publika länkar, marknadssidor). |
| Fas | 3, 4 eller 5 enligt planen. Fas 3 är CRM-kärnan (besluten 2026-11-26, tidslinje, synk, samlad kundlista), fas 4 Leads i CRM-miljön, fas 5 resten av appen. |
| Backend | **finns** med den första ändpunkten, funktionen eller tabellen läsarens rad nämner; **behövs ingen** när funktionen bara lever i webbläsaren; **saknas** eller **delvis** med vad som fattas. Det nya gränssnittet anropar samma ändpunkter som dagens (planens avsnitt 3: en backend, ett API). |
| Läge | Alla rader börjar som **inte gjord**. Byggaren sätter **byggd** när vyn finns och **verifierad** när flödet körts mot den lokala stacken och granskats i bild. |

**Mönstren** är de låsta ur `DESIGN-CRM.md`: **BolagVy** (lista med markering,
vyrad, `TableSelectionToolbar`, fot, sista raden "Lägg till", mobil som rader),
**BolagPanel** (postens panel från höger med flikar och fält i grupper), **BolagFormular**
(dialog med fältfel vid rätt fält), **OversiktVy** (rutnät av kort, nyckeltal och
diagram), **SynkVy** (förlopp och utfall), **Kommandopalett**, **CrmRam** (skalet) och
**Sida** (sidhuvud och vyrad). Det som inte går att bygga med dem är märkt
**NYTT MÖNSTER** och beskrivs i avsnittet "Nya mönster som måste byggas".

## Navigeringen i det nya gränssnittet

Förslaget när allt är flyttat. Grupperat som Twenty: arbetsyteväxlare och sökning överst,
objekten i grupper, data och plattform längst ner. Bara poster som gör något: en grupp
syns bara när arbetsytan har produkten (Iris, Kundtjänst, Kvitton), och en agent kunden
inte har står mörklagd med en säljvy i stället för 404, som i dag (SK-062, OV-016).

### Sidofältet

| Plats | Post | Adress | Vem ser den | Ersätter i dag |
|---|---|---|---|---|
| Överst | Arbetsyteväxlaren (Snajps logga, arbetsytans namn). Menyn: Inställningar, Språk, Tema, Kontakt, Dataskydd, Anmäl felaktigt svar, Logga ut. För plattformsadmin också Byt kund och Admin/Demo | – | alla; Byt kund och Admin/Demo bara plattformsadmin | railens fot och menyn (SK-065, SK-067, SK-074, SK-075, AD-006) |
| Överst | Sök eller hoppa till (Ctrl K) | Kommandopaletten | alla | bolagssöket i Leads sidhuvud (LR-080) och kunduppslaget |
| Arbetsyta | Översikt | `/crm` | alla | `/dashboard` (OV-020) och CRM:ets översikt |
| Arbetsyta | Att göra (räknare) | `/crm/att-gora` | alla | `/dashboard/att-gora` |
| Arbetsyta | Bolag | `/crm/bolag` (segment Egna, Iris, Alla) | alla med CRM-tillägget | CRM:ets Bolag, `/dashboard/companies`, Leads › Listor › Befintliga kunder |
| Arbetsyta | Personer | `/crm/personer` | alla med CRM-tillägget | CRM:ets Personer, `/dashboard/contacts` |
| Arbetsyta | Lärande | `/crm/larande` | alla (i dag utanför menyn; Anton avgör) | `/dashboard/larande` |
| Iris | Översikt | `/crm/iris` | produkten Leads | Leads › Översikt |
| Iris | Leads | `/crm/iris/leads` (vyer: Att bearbeta per status, Bortvalda, Arkiverade, Testyta; `?lead=` öppnar panelen) | produkten Leads | Iris-listan, statusremsan (Pipeline), lådan |
| Iris | Körningar | `/crm/iris/korningar`, `/crm/iris/korningar/[id]` | produkten Leads | Leads › Körningar, Kör Iris, körningsrutan, Aktivitet |
| Iris | Utkast | `/crm/iris/utkast` (vyer: Att granska, Skickas snart, Skickat) | produkten Leads | utkastrutan och granskningskön, Leads › Inkorg › Skickat |
| Iris | Konversationer (räknare) | `/crm/iris/konversationer` (vyer: Att göra, Alla, Inkommande) | produkten Leads | Leads › Konversationer, Leads › Inkorg › Inkommande, `/dashboard/inbox` |
| Iris | Uppföljningar | `/crm/iris/uppfoljningar` | produkten Leads | Leads › Uppföljningar |
| Iris | Samtal | `/crm/iris/samtal` (vyer: Återkoppling, Ringlista) | produkten Leads | Leads › Samtal |
| Iris | Listor | `/crm/iris/listor` (vyer: Listor, Säljlista; Importera och Beställ som handlingar) | produkten Leads; beställning och säljlista kräver `leadlists` | Leads › Listor |
| Iris | Kampanjer | `/crm/iris/kampanjer` (vyer: Kampanjer, Erbjudanden) | produkten Leads | Leads › Erbjudanden |
| Kundtjänst | Översikt | `/crm/kundtjanst` | produkten Support | Kundtjänst › Översikt |
| Kundtjänst | Ärenden | `/crm/kundtjanst/arenden` (vyer: Ärenden, Testmail, Dolda) | produkten Support | Kundtjänst › Ärenden, Testmail, Dolda |
| Kundtjänst | Överlämnade | `/crm/kundtjanst/overlamnade` | produkten Support | supportportalen `support-webb` (Inkorg, svar som medarbetare) |
| Kundtjänst | Testchatt | `/crm/kundtjanst/testchatt` | produkten Support, ej läsroll | Kundtjänst › Testchatt |
| Kvitton | Kvitton | `/crm/kvitton` (vyer: Översikt, Kvitton) | bara plattformsadmin så länge produkten är vilande | `/dashboard/kvitton` |
| Data | Synk | `/crm/synk` | alla med CRM-tillägget | befintlig |
| Data | Utvecklare | `/crm/utvecklare` | alla med CRM-tillägget | befintlig |
| Plattform | Admin-översikt | `/crm/admin` | bara plattformsadmin | `/admin` |
| Plattform | Kunder | `/crm/admin/kunder`, `/crm/admin/kunder/[id]` (flikar: Agentprofil och tillägg, Uppgifter och kontakter, Underlag och flöde, Flytt till main) | bara plattformsadmin | `/admin/kunder`, `/admin/kunder/[id]`, `/data`, `/insyn` |
| Plattform | Paket och avtal | `/crm/admin/paket` | bara plattformsadmin | `/admin/paket` |
| Plattform | Logg | `/crm/admin/logg` (vyer: Körningar, Händelser, Testkörningar, Kostnad), `/crm/admin/logg/[id]` | bara plattformsadmin | `/admin/korningar`, `/handelser`, `/testkorningar`, `/agentanvandning`, `/bokforingsanvandning` |
| Nederst | Synkkortet (senaste synkens läge) | – | alla med CRM-tillägget | befintligt |
| Nederst | Inställningar | `/crm/installningar` | alla | `/settings`, `/admin/installningar` |

Plattformsadmin har ett enda skal. Dagens dubbla adresser (`/admin/leads` bredvid
`/dashboard/leads`, AD-003, SK-072) behövs inte: samma `/crm`-adress, och skalet visar
gruppen Plattform och banderollen för kundbesök utifrån sessionen.

### Inställningarna

`/crm/installningar/<sektion>`, med en grupperad undermeny i samma ordning som i dag
(`lib/routes.ts:settingsGroups`) och de sektioner som saknas i dag tillagda:

| Grupp | Sektioner (adress) | Nytt mot i dag |
|---|---|---|
| Företaget | Företaget (`foretaget`), Vad ni säljer (`vad-ni-saljer`), Kunskapsbas (`kunskapsbas`), Så ska agenten låta (`rost`) | Företaget får redigerbara bolagsuppgifter (IN-146) |
| Iris | Målgrupp och automation (`iris`), med avsnitten Profil, Målgrupp, Automation, Önskemål, Utskick | Utskick (avsändare, signatur, schema, spärrlista; IN-110, IN-144, LU-179) och kundvalen ur API:t (IN-111, LK-067, LK-068) |
| Kundtjänst | När agenten får svara själv (`kundtjanst`), Inkorgar (`inkorgar`), Kanaler (`kanaler`), Integrationer (`integrationer`) | Kanaler och Integrationer (i dag bara backend och `support-webb`; SU-105, SU-107, IN-160–IN-166) |
| Kontot | Team (`team`), Plan och fakturering (`plan`), Tillägg (`tillagg`), Notiser (`notiser`), Tema (`tema`), Dataskydd (`dataskydd`), Kvitton (`kvitton`, bara med produkten) | Dataskydd (IN-143), rollbyte i Team (IN-083), Kvitton (IN-145) |
| Plattformen | Globala agentinstruktioner (`plattformen/instruktioner`), Tvåstegsverifiering (`plattformen/tvasteg`) | Bara plattformsadmin, som i dag |

### Var varje gammal adress hamnar

Omdirigeringarna slås på först i fas 6, när Anton säger till. Fram till dess lever båda
adresserna.

| Gammal adress | Ny adress |
|---|---|
| `/dashboard`, `/admin/arbetsyta` | `/crm` |
| `/dashboard/att-gora` | `/crm/att-gora` |
| `/dashboard/larande` | `/crm/larande` |
| `/dashboard/leads`, `?vy=oversikt` | `/crm/iris` |
| `/dashboard/leads?vy=pipeline` eller `tabell` (leder i dag till Översikt) | `/crm/iris/leads` |
| `/dashboard/leads?lead=<id>` (på vilken flik som helst) | `/crm/iris/leads?lead=<id>` |
| `?vy=korningar` | `/crm/iris/korningar` |
| `?vy=konversationer` (`&trad=`) | `/crm/iris/konversationer` (`?trad=`) |
| `?vy=uppfoljningar` | `/crm/iris/uppfoljningar` |
| `?vy=inkorg` (Inkommande) | `/crm/iris/konversationer?vy=inkommande` |
| `?vy=inkorg` (Skickat) | `/crm/iris/utkast?vy=skickat` |
| `?vy=samtal` | `/crm/iris/samtal` |
| `?vy=listor&del=listor`, `&del=saljlista` | `/crm/iris/listor`, `?vy=saljlista` |
| `?vy=listor&del=befintliga` | `/crm/bolag?segment=egna` |
| `?vy=erbjudanden` | `/crm/iris/kampanjer` |
| `/dashboard/companies`, `/dashboard/contacts` | `/crm/bolag?segment=iris`, `/crm/personer?segment=iris` |
| `/dashboard/inbox` | `/crm/iris/konversationer` |
| `/dashboard/analytics` | `/crm` (kortet för veckans utfall) |
| `/dashboard/assistant` | ingen (exempelvy; Anton avgör) |
| `/dashboard/support` och flikarna | `/crm/kundtjanst`, `/crm/kundtjanst/arenden?vy=…`, `/crm/kundtjanst/testchatt` |
| `/dashboard/kvitton`, `/dashboard/bokforing` (KV-190) | `/crm/kvitton` |
| De äldre omledningarna i OV-007 och LR-002 (`emails`, `aktivitet`, `iris/...`, `leads/listor`, `leads/kontroll`, `iris/granskning` med flera) | samma mål som raderna ovan, i ett steg |
| `/settings/<sektion>`, `/admin/installningar/<sektion>` | `/crm/installningar/<sektion>` |
| `/admin` | `/crm/admin` |
| `/admin/kunder`, `/admin/kunder/[id]`, `/data`, `/insyn` | `/crm/admin/kunder`, `/crm/admin/kunder/[id]?flik=…` |
| `/admin/paket` | `/crm/admin/paket` |
| `/admin/korningar`, `/admin/korningar/[id]` | `/crm/admin/logg?vy=korningar`, `/crm/admin/logg/[id]` |
| `/admin/handelser`, `/admin/testkorningar` | `/crm/admin/logg?vy=handelser`, `?vy=testkorningar` |
| `/admin/agentanvandning`, `/admin/bokforingsanvandning` | `/crm/admin/logg?vy=kostnad` |
| `/admin/<kundens vy>` (adminprefixet) | samma adress under `/crm`; skalet avgör |
| `support-webb` (portalen, "Kör agent") | `/crm/kundtjanst/overlamnade`, `/crm/installningar/kanaler`, `/integrationer`; portalen lever kvar tills Anton säger annat |
| `/login`, `/auth/reset`, `/onboarding` | samma adresser, i CRM:ets form |
| `/embed/[nyckel]`, `/chat/...`, `/avregistrera/[token]`, `/prova/[token]`, `/demo/...`, `/duo-demo`, `/boka-demo`, marknads- och juridiksidorna | oförändrade, utanför `/crm` |

## Funktionerna per område

En tabell per läsares fil, i läsarens ordning. Kolumnerna förklaras ovan.

### Skal, inloggning, onboarding (app-01, 121 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| SK-001 | Sidorna indexeras bara i produktionen | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-002 | Kundens egen domän får kundens titel och inget Snajp-manifest | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | finns: `lib/tenants/server.ts` | inte gjord |
| SK-003 | Ljust eller mörkt läge stämplas på servern | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-004 | Kundens palett på kundens domän | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | finns: `lib/tenants/*` | inte gjord |
| SK-005 | Viewport för mobil och notch | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-006 | Språkleverantören omsluter hela appen | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-007 | Yttersta felgränsen | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-008 | Sista skyddsnätet vid fel i rotlayouten | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-009 | 404-sida, två varianter | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | behövs ingen (klient) | inte gjord |
| SK-010 | Appmanifest för installation | Rotlayouten delas; `CrmRam` (befintlig) ärver | 5 | finns: `public/icons/*` | inte gjord |
| SK-020 | Skyddade sidor kräver session | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `getToken` | inte gjord |
| SK-021 | Inloggad som öppnar /login skickas till arbetsytan | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-022 | Widgetens inbäddningssida får per-kund CSP | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `lib/tenants` | inte gjord |
| SK-023 | Inloggning med e-post och lösenord | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `/api/auth/callback/credentials` | inte gjord |
| SK-024 | Felbesked vid inloggning avslöjar inte vilka konton som finns | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-025 | Spärr mot upprepade inloggningsförsök | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `inloggningsforsok_sparrad/registrera/nollstall` | inte gjord |
| SK-026 | Tvåstegsverifiering (TOTP) vid inloggning | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `tvafaktor_las` | inte gjord |
| SK-027 | Google- och Microsoft-inloggning (av i drift) | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `/api/auth/callback/google` | inte gjord |
| SK-028 | Tillbaka till rätt sida efter inloggning | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-029 | Plattformsadmin landar på /admin | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `platform_admins` | inte gjord |
| SK-030 | Självläkning av konto utan arbetsyta | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `profiles` | inte gjord |
| SK-031 | Skapa konto (registrering) | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `auth.users` | inte gjord |
| SK-032 | Starta demo utan konto | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `auth.users` | inte gjord |
| SK-033 | Begär demoåtkomst via mejl (inte kopplad) | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-034 | Glömt lösenord, steg 1: begär länk | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `password_reset_tokens` | inte gjord |
| SK-035 | Glömt lösenord, steg 2: välj nytt | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `password_reset_tokens` | inte gjord |
| SK-036 | Byt lösenord inloggad | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `auth.users` | inte gjord |
| SK-037 | Logga ut | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: Auth.js | inte gjord |
| SK-038 | Plattformsadmin avgörs fail closed | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | finns: `platform_admins` | inte gjord |
| SK-039 | Läsrollen (viewer) får inte skriva | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | finns: `profiles.role` | inte gjord |
| SK-040 | Onboardinggrinden | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | finns: `business_contexts` | inte gjord |
| SK-041 | Admin i skarpt läge kan inte stå i kundens arbetsyta | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | finns: `lib/vy.ts` | inte gjord |
| SK-042 | Arbetsytans tillstånd avgörs en gång per request | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | finns: se lib/data/dashboard.ts | inte gjord |
| SK-043 | En enda rutt för alla arbetsytans vyer | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | behövs ingen (klient) | inte gjord |
| SK-044 | Fel i en vy behåller menyn | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | behövs ingen (klient) | inte gjord |
| SK-045 | Laddningsläge vid varje flikbyte | `app/crm/layout.tsx` (befintlig, ärver grinden) · Sida | 4 | behövs ingen (klient) | inte gjord |
| SK-046 | Onboardingsidan förifylls med kontot | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: `lib/snajp/standard` | inte gjord |
| SK-048 | Tvåstegsverifiering: inrullning och avstängning (plattformsadmin) | `/crm/installningar/plattformen` (ny) · BolagFormular | 5 | finns: `tvafaktor_paborja/aktivera/avbryt_inrullning/avaktivera` | inte gjord |
| SK-047 | Auth.js egna ändpunkter är anonyma | `/login` och `app/crm/layout.tsx` · BolagFormular | 5 | finns: Auth.js | inte gjord |
| SK-060 | Vänsterrail som enda navigering | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-061 | Menyposterna och deras ordning | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | finns: `workspaces.products` | inte gjord |
| SK-062 | Agenter kunden inte har syns mörklagda | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | finns: `workspaces.products` | inte gjord |
| SK-063 | Vilande agenter | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-064 | Notisräknare på Leads | `CrmRam` (befintlig): räknare på menyposten · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `GET /api/snajp-support/leads/notiser/antal` | inte gjord |
| SK-065 | Railens fot: inställningar och konto | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-066 | Mobilrad överst | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-067 | Menyn: kontakt, språk, dataskydd, anmäl felaktigt svar | `CrmRam` (befintlig): arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-068 | Språkväxling | `CrmRam` (befintlig): arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-069 | Ljust och mörkt läge | `CrmRam` (befintlig): arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-070 | Läget (scope) Duo/Leads/Support är pensionerat men finns kvar | Tas inte med (pensionerat läge); Antons ord krävs för att ta bort | 5 | behövs ingen (klient) | inte gjord |
| SK-071 | Skydd mot att bli strandad på en sida | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-072 | Samma vyer på tre ytor | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-073 | Sidram för varje vy | `CrmRam` (befintlig): sidofältet och arbetsyteväxlarens meny · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| SK-074 | Kunduppslag "Byt kund" och kundbesök | `CrmRam` (befintlig): arbetsyteväxlaren (Byt kund, Admin/Demo) · CrmRam + Kommandopalett | 4 | finns: `GET /api/admin/kunder` | inte gjord |
| SK-075 | Vyväxeln Admin / Demo | `CrmRam` (befintlig): arbetsyteväxlaren (Byt kund, Admin/Demo) · CrmRam + Kommandopalett | 4 | behövs ingen (klient) | inte gjord |
| SK-076 | Banner "Du testar som <kund>" | `CrmRam` (befintlig) · NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | behövs ingen (klient) | inte gjord |
| SK-077 | Banner för läsroll | `CrmRam` (befintlig) · NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | finns: `profiles.role` | inte gjord |
| SK-078 | Demoband i den öppna demon | `CrmRam` (befintlig) · NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | behövs ingen (klient) | inte gjord |
| SK-079 | Demoband i en demoarbetsyta och i demovyn | `CrmRam` (befintlig) · NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | finns: `workspaces.is_demo` | inte gjord |
| SK-090 | Arbetsytans kontext per request | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | finns: `profiles` | inte gjord |
| SK-091 | Produkter och tillägg avgörs fail closed | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | finns: `workspaces.products` | inte gjord |
| SK-092 | Kundbesökets tillstånd | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | finns: `GET /api/admin/tenants` | inte gjord |
| SK-093 | Demovyns tillstånd | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | finns: demonyckeln | inte gjord |
| SK-094 | Läget vid första renderingen | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | behövs ingen (klient) | inte gjord |
| SK-095 | Dispatcher för arbetsytans vyer | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | behövs ingen (klient) | inte gjord |
| SK-096 | Produktgrinden på servern | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | finns: `resolveDashboardState` | inte gjord |
| SK-097 | Kundtjänstsidan i skalet | `app/crm/layout.tsx` och vyernas sidor (befintlig) · Sida | 4 | finns: se område 6 | inte gjord |
| SK-110 | Stegrad och framsteg | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-111 | Validering per steg | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-112 | Steg 1 Företaget | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-113 | Steg 2 Bransch | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-114 | Steg 3 Kontaktperson | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-115 | Steg 4 Målgrupp för Iris | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-116 | Steg 5 Röst och ton | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-117 | Steg 6 Paket, villkor och notiser | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-118 | Väntan medan arbetsytan läggs upp | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-119 | Villkorslänkar på varje steg | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-120 | Inskickning: validering på servern | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-121 | Inskickning: affärskontexten sparas | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `business_contexts` | inte gjord |
| SK-122 | Inskickning: arbetsytans namn och paket | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `workspaces.name` | inte gjord |
| SK-123 | Inskickning: notissvaret | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `notification_preferences` | inte gjord |
| SK-124 | Inskickning: arbetsytan får sin backend-kund | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `POST /api/keys` | inte gjord |
| SK-125 | Inskickning: kundregistret fylls | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `ss_customer_details` | inte gjord |
| SK-126 | Inskickning: webbplatsskanningen startar | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: backend, kunskapsbasens förslag | inte gjord |
| SK-127 | Inskickning avslutas i arbetsytan | `/onboarding` i CRM:ets form · BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SK-130 | Inloggningssidans uppbyggnad | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | finns: `public/photos/goteborg-golden.webp` | inte gjord |
| SK-131 | Tre lägen: Logga in, Skapa konto, Återställ | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-132 | Fält och klientvalidering | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-133 | Knappen och vad som händer medan det pågår | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | finns: `lib/actions/auth.ts` | inte gjord |
| SK-134 | Kodsteget vid tvåstegsverifiering | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | finns: `signInWithPassword(email, lösenord, next, kod)` | inte gjord |
| SK-135 | Besked från adressfältet | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SK-136 | Återställningsbesked | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | finns: `requestPasswordReset` | inte gjord |
| SK-137 | Formuläret för nytt lösenord | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | finns: `updatePassword` | inte gjord |
| SK-138 | Fristående utloggningsknapp | `/login`, `/auth/reset` i CRM:ets form · BolagFormular | 5 | finns: `signOut` | inte gjord |
| SK-150 | Service workern registreras | Hela appen; `CrmRam` (befintlig) får manifest, offline och felgränser · Tabellskelett | 5 | finns: `public/sw.js` | inte gjord |
| SK-151 | Kunddata cachas aldrig | Hela appen; `CrmRam` (befintlig) får manifest, offline och felgränser · Tabellskelett | 5 | finns: Cache Storage i webbläsaren | inte gjord |
| SK-152 | Offline-sidan | Hela appen; `CrmRam` (befintlig) får manifest, offline och felgränser · Tabellskelett | 5 | behövs ingen (klient) | inte gjord |
| SK-153 | Installationsrutan | Hela appen; `CrmRam` (befintlig) får manifest, offline och felgränser · Tabellskelett | 5 | behövs ingen (klient) | inte gjord |
| SK-154 | En delad källa för installationen | Hela appen; `CrmRam` (befintlig) får manifest, offline och felgränser · Tabellskelett | 5 | behövs ingen (klient) | inte gjord |
| SK-155 | Felgränser per yta | `CrmRam` (befintlig): felgräns, laddning och väntläge i varje vy · Tabellskelett + EmptyState | 4 | behövs ingen (klient) | inte gjord |
| SK-156 | Laddningsskelett | `CrmRam` (befintlig): felgräns, laddning och väntläge i varje vy · Tabellskelett + EmptyState | 4 | behövs ingen (klient) | inte gjord |
| SK-157 | "Din arbetsyta aktiveras" i stället för ett tekniskt 409 | `CrmRam` (befintlig): felgräns, laddning och väntläge i varje vy · Tabellskelett + EmptyState | 4 | finns: `ej_aktiverad` | inte gjord |
| SK-170 | Mejlnotiser per användare | `/crm/installningar/notiser` (ny) · BolagFormular | 5 | finns: `notification_preferences` | inte gjord |
| SK-171 | Notisräknaren i appen | `CrmRam` (befintlig): räknare på menyposten · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `/api/leads/notiser/antal` | inte gjord |
| SK-172 | Kundens domän känns igen på värdnamnet | Ingen egen vy: under ytan, oförändrad backend; CRM:et svarar aldrig på kundens domän | 5 | finns: kod | inte gjord |
| SK-173 | Snajps sidor finns inte på kundens domän | Ingen egen vy: under ytan, oförändrad backend; CRM:et svarar aldrig på kundens domän | 5 | behövs ingen (klient) | inte gjord |
| SK-174 | Widgetens publika nyckel | Ingen egen vy: under ytan, oförändrad backend; CRM:et svarar aldrig på kundens domän | 5 | finns: kod | inte gjord |
| SK-175 | Lösenord lagras som scrypt med egna parametrar | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `auth.users.encrypted_password` | inte gjord |
| SK-176 | Återställningslänkens token | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `password_reset_tokens` | inte gjord |
| SK-177 | TOTP-parametrarna | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| SK-178 | Återställningskoderna | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: tvåfaktortabellerna (migration 128) | inte gjord |
| SK-179 | Krypteringen av tvåfaktorhemligheten | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: se läsarens rad | inte gjord |
| SK-180 | Vilken miljö appen kör i | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: miljövariabler | inte gjord |
| SK-181 | Egen felgräns för onboardingen | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| SK-182 | De tre registrerade tenants | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `SNAJP_KEY_*` | inte gjord |
| SK-183 | Värdnamnsregeln och Railway-adresserna | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `host` | inte gjord |
| SK-184 | Guidens stegdetaljer som inte står ovan | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| SK-185 | Ingen spärr eller serverkontroll vid registrering | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `auth.users` | inte gjord |
| SK-186 | Lösenordsbyte inloggad kräver inte det gamla lösenordet och loggar inte ut andra sessioner | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `auth.users` | inte gjord |
| SK-187 | OAuth-inloggning kopplas till ett befintligt konto på samma adress | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `auth.users` | inte gjord |
| SK-188 | Chattens sessionsidentitet tål blockerad lagring | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: sessionStorage | inte gjord |

### Översikt, Att göra, Lärande (app-02, 85 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| OV-001 | Arbetsytans sektioner nås via en enda dispatcher, delad mellan kundens yta och adminytan. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-002 | Plattformsadmin skickas från `/dashboard` till `/admin`. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: `resolveDashboardState()` | inte gjord |
| OV-003 | Onboardinggrind för arbetsytan. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: Onboardingstatus i databasen | inte gjord |
| OV-004 | Arbetsytans tillstånd (produkter, demo/färsk, namn, adminflagga) avgörs en gång per anrop på servern och ges till klientträdet. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: `lib/data/dashboard.ts:resolveDashboardState` | inte gjord |
| OV-005 | Lärande grindas bara på inloggning, inte på produkt. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: se Lärande nedan | inte gjord |
| OV-006 | Att göra grindas bara på inloggning; kön visar bara agenter arbetsytan har. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: se Att göra nedan | inte gjord |
| OV-007 | Gamla adresser omdirigeras. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-008 | Produktgrind (entitlement) på servern. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: `resolveDashboardState().products` | inte gjord |
| OV-009 | Vilande produkt (i dag Kvitton) är mörklagd för kunden. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-010 | Kundtjänstsektionen visar inkorg/utkast och Testchatt som flikar under rubriken "Kundtjänst". | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-011 | Laddningsskelett vid varje flikbyte. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-012 | Ett fel i en vy stannar i vyn. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-013 | Arbetsytans tillstånd i olika lägen. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: `workspaces` | inte gjord |
| OV-014 | Läget Duo/bara Leads/bara Support (scope) väljs och kommer ihåg i ett år. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | behövs ingen (klient) | inte gjord |
| OV-015 | Läsroll (extern läsare) får full läsrätt och ingen skrivrätt. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: `profiles.role` | inte gjord |
| OV-016 | Saknad agent visar en säljvy i stället för 404. | `app/crm/layout.tsx` och vyernas sidor · Sida | 5 | finns: `lib/pricing.ts:PAKET` | inte gjord |
| OV-020 | Översikten är startsidan och visar alla agenters körningar på ett ställe. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `GET /api/snajp-support/leads/korningar?limit=100` | inte gjord |
| OV-021 | Översikten anpassas efter vilka agenter arbetsytan har. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-022 | Fyra nyckeltalskort överst, olika uppsättning per produktkombination. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: se OV-020 | inte gjord |
| OV-023 | Nyckeltalskortets form. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-024 | Nyckeltal Körningar. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `leads_jobs` | inte gjord |
| OV-025 | Nyckeltal Leads levererade. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `GET /leads/korningar` | inte gjord |
| OV-026 | Nyckeltal Leveransgrad. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-027 | Nyckeltal Pågår nu. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-028 | Nyckeltal Till en människa (överlämnade samtal). | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `GET /api/chattar` | inte gjord |
| OV-029 | Nyckeltal Uppskattad kostnad. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `GET /api/usage` | inte gjord |
| OV-030 | Nyckeltal Dygnsbudget. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `GET /api/usage` | inte gjord |
| OV-031 | "Pågår just nu": förlopp för Iris-körningar som pågår. | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | finns: `GET /leads/korningar` | inte gjord |
| OV-032 | Översikten laddas om när en körning rör sig. | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | behövs ingen (klient) | inte gjord |
| OV-033 | Avsnittet "Iris, leadsagenten". | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | finns: `GET /leads/korningar` | inte gjord |
| OV-034 | Munkdiagram "Hur körningarna slutade". | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | behövs ingen (klient) | inte gjord |
| OV-035 | Munkdiagram "Typ av körning". | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | behövs ingen (klient) | inte gjord |
| OV-036 | Leadsdiagrammen i översikten. | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | finns: se leadsområdet | inte gjord |
| OV-037 | Tabellen "Alla Iris-körningar" med styrning. | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | 4 | finns: `GET /leads/korningar` | inte gjord |
| OV-038 | Avsnittet "Kundtjänsten". | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/usage?days=60` | inte gjord |
| OV-039 | Panel "Dygnsbudget" med ring och fördelning av överlämnade samtal. | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/usage` | inte gjord |
| OV-040 | Lista "Överlämnade samtal". | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/chattar` | inte gjord |
| OV-041 | Lista "Per dag". | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/usage` | inte gjord |
| OV-042 | Laddningsläge och fel per panel. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-043 | Demoläge för översikten. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-044 | Tomläge för ny arbetsyta: "Kom igång". | `/crm` (befintlig) Översikt, kortet Kom igång · OversiktVy + SynkVy | 5 | behövs ingen (klient) | inte gjord |
| OV-045 | Kom igång visar förloppet för webbplatsskanningen från onboardingen. | `/crm` (befintlig) Översikt, kortet Kom igång · OversiktVy + SynkVy | 5 | finns: se WebbplatsForslag (skanningens ändpunkt, kunskapsförslag) | inte gjord |
| OV-046 | Diagrambyggstenar som följer temat. | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| OV-047 | Skanningens förlopp i Kom igång uppdateras av sig självt. | `/crm` (befintlig) Översikt, kortet Kom igång · OversiktVy + SynkVy | 5 | finns: `GET /api/snajp-support/kb/forslag` | inte gjord |
| OV-048 | Översiktens hämtningar tolkar "offline" och "ej aktiverad". | `/crm` (befintlig) Översikt, utökad med agentavsnitt · OversiktVy | 5 | finns: `app/api/snajp-support/[...path]/route.ts` | inte gjord |
| OV-060 | Att göra samlar allt som väntar på ett beslut från en människa, från alla agenter arbetsytan har. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: se OV-061–OV-073 | inte gjord |
| OV-061 | Nyckeltal "Väntar på dig". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-062 | Nyckeltal per agent. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-063 | Tomläge "Inget väntar på dig". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-064 | Munkdiagram "Vad som väntar" per kö. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-065 | Åldershinkar "Hur länge det väntat". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-066 | Kön "Eskalerat till dig" (kundtjänst). | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/inbox?status=escalated` | inte gjord |
| OV-067 | Kön "Svar att godkänna" (kundtjänst). | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/inbox?status=awaiting_approval` | inte gjord |
| OV-068 | Kön "Larm" (kundtjänst). | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/inbox?status=att_hantera` | inte gjord |
| OV-069 | Bocka av ett ärende som hanterat. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `POST /api/inbox/{id}/hanterad` | inte gjord |
| OV-070 | Leadsrutan: tre länkrader. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: se OV-071–OV-073 | inte gjord |
| OV-071 | Räkning "Svar från leads". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/inbox?klass=lead&limit=200` | inte gjord |
| OV-072 | Räkning "Leadsutkast att godkänna". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/leads/queue` | inte gjord |
| OV-073 | Räkning "Samtal att ringa i dag". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/leads/samtal/antal` | inte gjord |
| OV-074 | Kvittorutan "Kvitton att granska". | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | finns: `GET /api/snajp-support/kvitton?fran=&till=` | inte gjord |
| OV-075 | Kolumnlayout och fel per kö. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-076 | Ingen automatisk omhämtning. | `/crm/att-gora` (ny) · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden (BolagVy + BolagPanel) | 5 | behövs ingen (klient) | inte gjord |
| OV-077 | Ärendets detaljpanel i kön. | `/crm/att-gora` (ny) · BolagPanel | 5 | finns: `GET /api/inbox/{id}` | inte gjord |
| OV-078 | Ta över ett ärende. | `/crm/att-gora` (ny) · BolagPanel | 5 | finns: `POST /api/inbox/{id}/takeover` | inte gjord |
| OV-079 | "Sortera bort utskick" i den eskalerade kön (backend). | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `POST /api/inbox/sortera` | inte gjord |
| OV-080 | Lärande visar det agenterna lärt sig som förslag, för en människa att godkänna eller avfärda. | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `GET /api/snajp-support/agent/forslag?status=ny` | inte gjord |
| OV-081 | Supportagenten föreslår KB-artiklar ur ärenden (bakgrund). | Ingen egen vy: under ytan, oförändrad backend; förslagen syns i `/crm/larande` | 5 | finns: `snajp-support/app/agent/support_agent.py` | inte gjord |
| OV-082 | Leadsagenten föreslår marknadsinsikter ur researchvarv (bakgrund). | Ingen egen vy: under ytan, oförändrad backend; förslagen syns i `/crm/larande` | 5 | finns: `snajp-support/app/agent/leads_agent.py` | inte gjord |
| OV-083 | Avsnittet "Väntar på ditt beslut". | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `GET /api/agent/forslag?status=ny` | inte gjord |
| OV-084 | Godkänna ett förslag. | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `POST /api/agent/forslag/{id}/godkann` | inte gjord |
| OV-085 | Avfärda ett förslag. | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `POST /api/agent/forslag/{id}/avfard` | inte gjord |
| OV-086 | Avsnittet "Domar från teamet" (läsvy). | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `GET /api/agent/feedback` | inte gjord |
| OV-087 | En dom "Fel" med rättad text blir ett eval-fall (bakgrund). | Ingen egen vy: under ytan, oförändrad backend; förslagen syns i `/crm/larande` | 5 | finns: `POST /api/agent/feedback` | inte gjord |
| OV-088 | Öppna ett förslag som undersökningsärende. | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `POST /api/agent/forslag/{id}/arende` | inte gjord |
| OV-090 | Skrivningar i kundbesök blir testdata (gäller Att göra och Lärande). | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `app/api/snajp-support/_auth.ts:proxyAsTenant` | inte gjord |
| OV-091 | Läsrollen stoppas på servern även i Att göra och Lärande. | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | finns: `_auth.ts:proxyAsTenant` | inte gjord |
| OV-089 | Lägen för Lärande-vyn. | `/crm/larande` (ny) · BolagVy + BolagPanel | 5 | behövs ingen (klient) | inte gjord |
| OV-100 | Förhandsvyerna nås bara med direkt adress. | Tas inte med som egen vy utan Antons ord | 5 | behövs ingen (klient) | inte gjord |
| OV-101 | Analys: veckovis utfall för kundens egen arbetsyta. | `/crm` (befintlig) Översikt, kort för veckans utfall · OversiktVy | 5 | finns: `GET /api/snajp-support/analytics/weekly?weeks=8` | inte gjord |
| OV-102 | Assistent: exempelsamtal, märkt som exempel. | Tas inte med som egen vy utan Antons ord | 5 | behövs ingen (klient) | inte gjord |
| OV-103 | Bolag: kundens egna prospekt i ett register. | `/crm/bolag` (befintlig) segment Iris · BolagVy | 3 | finns: `GET /api/leads/prospects` | inte gjord |
| OV-104 | Kontakter: personerna bakom prospekten. | `/crm/personer` (befintlig) segment Iris · BolagVy | 3 | finns: `GET /api/snajp-support/leads/prospects?limit=1000` | inte gjord |
| OV-105 | Inkorg (Svar): vad prospekten svarat. | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 4 | finns: `GET /api/snajp-support/leads/svar` | inte gjord |
| OV-107 | Analysens källor och avgränsning (backend). | `/crm` (befintlig) Översikt, kort för veckans utfall · OversiktVy | 5 | finns: `snajp-support/app/storage/postgres.py:weekly_analytics` | inte gjord |
| OV-106 | Visningsvyn för laddnings-, tom- och fellägen. | Tas inte med som egen vy utan Antons ord | 5 | behövs ingen (klient) | inte gjord |

### Leads: översikt, pipeline, bolag (app-03, 104 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| LR-001 | Öppna Leads från menyn | `/crm/iris` (ny) och sidofältets grupp Iris · Sida + Vyrad | 4 | finns: `resolveDashboardState()` | inte gjord |
| LR-002 | Gamla adresser leder rätt | `/crm/iris` (ny) och sidofältets grupp Iris · Sida + Vyrad | 4 | behövs ingen (klient) | inte gjord |
| LR-003 | Byta flik i Leads | `/crm/iris` (ny) och sidofältets grupp Iris · Sida + Vyrad | 4 | behövs ingen (klient) | inte gjord |
| LR-004 | Se antal olästa notiser på fliken Konversationer | `CrmRam` (befintlig) och sidhuvudet i Iris · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `GET /leads/notiser/antal` | inte gjord |
| LR-005 | Notiser i sidhuvudet | `CrmRam` (befintlig) och sidhuvudet i Iris · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `GET /leads/notiser?limit=30` | inte gjord |
| LR-006 | Starta en Iris-körning från sidhuvudet (Kör Iris) | `/crm/iris/korningar` (ny) primär handling, dialog · BolagFormular | 4 | finns: se läsarens rad | inte gjord |
| LR-007 | Beställa leadslista från sidhuvudet | `/crm/iris/listor` (ny) primär handling, dialog · BolagFormular | 4 | finns: se läsarens rad | inte gjord |
| LR-008 | Öppna ett lead i en låda från höger | `/crm/iris/leads` (ny)`?lead=` · BolagPanel | 4 | behövs ingen (klient) | inte gjord |
| LR-009 | Okänt lead i demo städas bort | `/crm/iris/leads` (ny)`?lead=` · BolagPanel | 4 | behövs ingen (klient) | inte gjord |
| LR-010 | Provköra Iris i demon | `/crm/iris` (ny) och sidofältets grupp Iris · Sida + Vyrad | 4 | finns: inget (lokalt) | inte gjord |
| LR-011 | Listfliken utan listtillägg | `/crm/iris/listor` (ny) · EmptyState med tilläggets förklaring | 4 | finns: se avsnitt G | inte gjord |
| LR-020 | Se trattens nyckeltal på en rad | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: `onAntal` | inte gjord |
| LR-021 | Talen i nyckeltalen säger samma sak som listorna | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: `GET /leads/skickat/antal?dagar=28` | inte gjord |
| LR-022 | Se konversationer som väntar | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: se läsarens rad | inte gjord |
| LR-023 | Se pågående och senaste körning | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: `GET /leads/korningar` | inte gjord |
| LR-024 | Se de senaste utkasten | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: se läsarens rad | inte gjord |
| LR-025 | Se Iris-leads i full bredd | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: se avsnitt C | inte gjord |
| LR-026 | Se listorna i översikten | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: `GET /leads/listor` | inte gjord |
| LR-027 | Flytta leads till main (bara plattformsadmin) | `/crm/iris/leads` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | 4 | behövs ingen (klient) | inte gjord |
| LR-030 | Hämta alla leads | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `GET /leads/prospects?lista=1&limit=5000&offset=N` | inte gjord |
| LR-031 | Servern filtrerar vad listan får | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `GET /leads/prospects` | inte gjord |
| LR-032 | Sortering: nyaste överst | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-033 | Filtrera på status med statusremsan | `/crm/iris/leads` (ny) · BolagVy (vyrad) + NYTT MÖNSTER: tavla (kanban) för statusar som alternativ vy | 4 | behövs ingen (klient) | inte gjord |
| LR-034 | Filtrera på nivå, typ och sök | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-035 | Spara, använda och radera sparade vyer | `/crm/iris/leads` (ny) · NYTT MÖNSTER: sparade vyer i vyraden | 4 | finns: `GET/POST /leads/vyer` | inte gjord |
| LR-036 | Se raderna i tabell (desktop) eller kort (mobil) | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-037 | Bläddra sida för sida | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-038 | Följa listan live under en körning | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `GET /leads/prospects?lista=1` | inte gjord |
| LR-039 | Byta status direkt i raden | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `PATCH /leads/prospects/{id}` | inte gjord |
| LR-040 | Se utkastets status i raden | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `list_prospects` | inte gjord |
| LR-041 | Markera rader | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-042 | Massåtgärd: Skapa utkast / Skapa om utkast | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `POST /leads/prospects/processa-om` | inte gjord |
| LR-043 | Massåtgärd: Skicka utkast (primär) | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `POST /leads/prospects/{id}/befordra` | inte gjord |
| LR-044 | Massåtgärd: Skapa uppföljning | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: se läsarens rad | inte gjord |
| LR-045 | Massåtgärd: Arkivera och Återställ | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `POST /leads/prospects/arkivera` | inte gjord |
| LR-046 | Massåtgärd: Ta bort för gott | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `POST /leads/prospects/radera` | inte gjord |
| LR-047 | En massåtgärd i taget | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-048 | Flytta markerade leads till main | `/crm/iris/leads` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | 4 | finns: `lib/actions/flytt.ts:flyttaProspektTillMain` | inte gjord |
| LR-049 | Se Skickat-listan i Leads | `/crm/iris/utkast` (ny) vyn Skickat · BolagVy | 4 | finns: `GET /leads/skickat?limit=500` | inte gjord |
| LR-050 | Se bortvalda bolag (nivå C) | `/crm/iris/leads` (ny) vyerna Bortvalda och Arkiverade · BolagVy | 4 | finns: `GET /leads/prospects?lista=1&bortvalda=1` | inte gjord |
| LR-051 | Se arkiverade leads | `/crm/iris/leads` (ny) vyerna Bortvalda och Arkiverade · BolagVy | 4 | finns: `GET /leads/prospects?lista=1&arkiverade=1` | inte gjord |
| LR-053 | Statusbyte skrivs i statusloggen och speglas till kundens CRM | Ingen egen vy: under ytan, oförändrad backend; speglingen mot kundens CRM hör till synken · SynkVy | 3 | finns; spegling åt båda håll mot CRM:ets egna objekt saknas (fas 3) | inte gjord |
| LR-052 | Demons uppspelade körning | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `lib/demo/oversikt.ts` | inte gjord |
| LR-054 | Arkivering stoppar utskick | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `leads_massatgard.py:arkivera_prospekt` | inte gjord |
| LR-055 | Radering vägras för kontaktade | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `leads_massatgard.py:radera_prospekt` | inte gjord |
| LR-056 | Utkastets status räknas fram på samma sätt överallt | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `app/leads/utkaststatus.py:harled, med_utkastjobb` | inte gjord |
| LR-057 | Bekräfta en massåtgärd på sidan | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-058 | Sidväljaren och tabell eller kort | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-059 | Se rader flytta när listan uppdateras live | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | behövs ingen (klient) | inte gjord |
| LR-096 | Servern skyddar Skapa utkast mot dubbelkörning och mot att skriva om kontaktade | `/crm/iris/leads` (ny) · BolagVy (statusremsan som vyrad, massåtgärder i TableSelectionToolbar) | 4 | finns: `POST /leads/prospects/processa-om` | inte gjord |
| LR-120 | Byta mellan Listor, Säljlista och Befintliga kunder | `/crm/iris/listor` (ny) · BolagVy | 4 | behövs ingen (klient) | inte gjord |
| LR-121 | Se sina listor | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `GET /leads/listor` | inte gjord |
| LR-122 | Importera en lista / beställa en lista | `/crm/iris/listor` (ny) › Importera och Beställ · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) + BolagFormular | 4 | finns: `POST /leads/listor` | inte gjord |
| LR-123 | Kombinera listor | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `POST /leads/listor/kombinera {titel, list_ids, kontaktfilter}` | inte gjord |
| LR-124 | Öppna en lista och se raderna | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `GET /leads/listor/{id}` | inte gjord |
| LR-125 | Filtrera och sortera en lista | `/crm/iris/listor` (ny) · BolagVy | 4 | behövs ingen (klient) | inte gjord |
| LR-126 | Öppna en listrad som lead | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `POST /leads/listor/{id}/items/{item}/prospekt` | inte gjord |
| LR-127 | Skapa utkast / Processa om för listans rader | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `POST /leads/listor/{id}/utkast {item_ids}` | inte gjord |
| LR-128 | Radens signal | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `signal` | inte gjord |
| LR-129 | Ladda ner en lista som CSV | `/crm/iris/listor` (ny) · BolagVy | 4 | behövs ingen (klient) | inte gjord |
| LR-130 | Ta bort en lista | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `DELETE /leads/listor/{id}` | inte gjord |
| LR-131 | Kopiera eller flytta en lista till en annan kund | `/crm/iris/listor` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | 4 | finns: `lib/actions/listor.ts:listaTillKund` | inte gjord |
| LR-132 | Fält som med flit INTE följer med en kopierad lista | `/crm/iris/listor` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | 4 | finns: `admin_listor.py:LISTRADSFALT` | inte gjord |
| LR-133 | Ladda upp befintliga kunder (CRM-kundlistan) | `/crm/bolag` (befintlig) segment Egna (CRM-kundlistan går upp i CRM:ets bolag) · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 3 | finns (`lead_lists.kalla='crm'`); ska gå upp i CRM:ets bolag, väg saknas | inte gjord |
| LR-134 | Listans rader läses med utkaststatus och bestående förlopp | `/crm/iris/listor` (ny) · BolagVy | 4 | finns: `leads.py:hamta_leadslista` | inte gjord |
| LR-135 | Listornas förlopp tål tillfälliga fel | `/crm/iris/listor` (ny) · BolagVy | 4 | behövs ingen (klient) | inte gjord |
| LR-090 | Se webbplatsens betyg i Iris-listan | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | 4 | finns: `webbrevision` | inte gjord |
| LR-091 | Servern döljer bedömningen för alla andra | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | 4 | finns: `snajp-support/app/leads/webbpool.py:far_se, dolj, SYNLIGA, DOLDA_FALT` | inte gjord |
| LR-092 | Webbnivå och län i listor | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | 4 | finns: `GET /leads/listor/{id}` | inte gjord |
| LR-093 | Läsroll kan inte skriva | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | 4 | finns: `app/api/snajp-support/_auth.ts:proxyAsTenant` | inte gjord |
| LR-094 | Kundbesök (plattformsadmin tittar som kund) skriver som test | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | 4 | finns: `_auth.ts:proxyAsTenant` | inte gjord |
| LR-097 | Flytt till main och lista till kund går bara genom serveractions | `/crm/iris/leads` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | 4 | finns: `lib/actions/flytt.ts` | inte gjord |
| LR-095 | Demoläget gör inga anrop | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | 4 | behövs ingen (klient) | inte gjord |
| LR-080 | Söka ett bolag bland ALLA leads | Kommandopalett (befintlig), grupp Leads · Kommandopalett | 4 | finns: `GET /leads/sok?q=` | inte gjord |
| LR-081 | Se träffarna | Kommandopalett (befintlig), grupp Leads · Kommandopalett | 4 | finns: svarsfält `id, company_name, ort, contact_name, contact_email, orgnr,… | inte gjord |
| LR-082 | Öppna träffen | Kommandopalett (befintlig), grupp Leads · Kommandopalett | 4 | behövs ingen (klient) | inte gjord |
| LR-060 | Hämta leadet | `/crm/iris/leads` (ny)`?lead=` · BolagPanel (flikar Bedömning, Mejlutkast, Tidslinje) | 4 | finns: `GET /leads/prospects/{id}` | inte gjord |
| LR-061 | Se leadets huvud | `/crm/iris/leads` (ny)`?lead=` · BolagPanel (flikar Bedömning, Mejlutkast, Tidslinje) | 4 | behövs ingen (klient) | inte gjord |
| LR-062 | Läsa bedömningen | `/crm/iris/leads` (ny)`?lead=` · BolagPanel (flikar Bedömning, Mejlutkast, Tidslinje) | 4 | finns: `score_breakdown` | inte gjord |
| LR-063 | Se Jevs förbedömning | `/crm/iris/leads` (ny)`?lead=` · BolagPanel (flikar Bedömning, Mejlutkast, Tidslinje) | 4 | finns: `jev.triage` | inte gjord |
| LR-064 | Se källorna | `/crm/iris/leads` (ny)`?lead=` · BolagPanel (flikar Bedömning, Mejlutkast, Tidslinje) | 4 | finns: `sources` | inte gjord |
| LR-065 | Se och redigera mejlutkastet | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `GET /leads/prospects/{id}/utkast` | inte gjord |
| LR-066 | Spara en ändring i utkastet | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `PUT /leads/queue/{queue_item_id}` | inte gjord |
| LR-067 | Godkänna och skicka ett utkast från lådan | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /leads/queue/{id}/approve` | inte gjord |
| LR-068 | Skapa ett utkast för ett lead utan utkast | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /leads/prospects/processa-om {scope:"research"}` | inte gjord |
| LR-069 | Se och skriva på leadets tidslinje | `/crm/iris/leads` (ny)`?lead=` fliken Tidslinje · BolagPanel + NYTT MÖNSTER: tidslinje på posten (händelser, anteckningar, uppgifter) | 3 | finns (`/leads/bolag/.../tidslinje`); CRM:ets tidslinje saknas (fas 3) | inte gjord |
| LR-071 | Godkännandet uppdaterar resten av sidan | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | behövs ingen (klient) | inte gjord |
| LR-072 | Regler när utkastets text sparas | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `PUT /leads/queue/{id}` | inte gjord |
| LR-073 | Serverns besked efter Godkänn och skicka | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /leads/queue/{id}/approve` | inte gjord |
| LR-074 | Välja utkastets struktur A eller B | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `struktur` | inte gjord |
| LR-075 | Utkast kräver erbjudandetext | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `lib/actions/affarskontext.ts:lasOffertForUtkast` | inte gjord |
| LR-070 | Vad som går att ändra i lådan | `/crm/iris/leads` (ny)`?lead=` fliken Mejlutkast · BolagPanel + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | behövs ingen (klient) | inte gjord |
| LR-100 | Se bolagsregistret | `/crm/bolag` (befintlig) segment Iris · BolagVy + BolagPanel | 4 | finns: `GET /leads/prospects?limit=1000&offset=N` | inte gjord |
| LR-101 | Visa eller dölja testkörningar | `/crm/bolag` (befintlig) segment Iris · BolagVy + BolagPanel | 4 | behövs ingen (klient) | inte gjord |
| LR-102 | Flytta markerade till testytan | `/crm/iris/leads` (ny) vyn Testyta · TableSelectionToolbar | 4 | finns: `POST /leads/prospects/{id}/degradera` | inte gjord |
| LR-103 | Flytta markerade till skarpa listan | `/crm/iris/leads` (ny) vyn Testyta · TableSelectionToolbar | 4 | finns: `POST /leads/prospects/{id}/befordra` | inte gjord |
| LR-104 | Fylla i det som saknas för befordran | `/crm/iris/leads` (ny) vyn Testyta · TableSelectionToolbar | 4 | finns: `POST /leads/prospects/{id}/befordra` | inte gjord |
| LR-105 | Skapa utkast för markerade | `/crm/iris/leads` (ny) vyn Testyta · TableSelectionToolbar | 4 | finns: `POST /leads/outreach/draft` | inte gjord |
| LR-106 | Bearbeta om markerade (research och utkast) | `/crm/iris/leads` (ny) vyn Testyta · TableSelectionToolbar | 4 | finns: `POST /leads/prospects/processa-om {prospect_ids, scope:"research_and_draft", struktur}` | inte gjord |
| LR-110 | Se ett bolags sida | `/crm/iris/leads` (ny)`?lead=` · BolagPanel | 4 | finns: `GET /leads/prospects/{id}` | inte gjord |
| LR-111 | Skapa och godkänna utkast på bolagssidan | `/crm/iris/leads` (ny)`?lead=` · BolagPanel | 4 | finns: `POST /leads/outreach/draft` | inte gjord |
| LR-113 | Se kontaktpersonerna | `/crm/iris/leads` (ny)`?lead=` · BolagPanel | 4 | finns: `GET /leads/prospects?limit=1000` | inte gjord |
| LR-114 | Se leadsens diagram (på Aktivitet, inte i Leads) | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: `GET /leads/prospects/fordelning` | inte gjord |
| LR-112 | Slå på automatiskt utskick efter ett godkännande | `/crm/iris/leads` (ny)`?lead=` · BolagPanel (dialog efter godkännande) | 4 | finns: `PUT /leads/config {autonomy}` | inte gjord |

### Leads: körningar, listor, källor (app-04, 132 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| LK-001 | Ange antal leads | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `POST /leads/runs/batch {limit}` | inte gjord |
| LK-002 | Välja omfattning | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `scope: research_and_draft \| research \| sok` | inte gjord |
| LK-003 | Välja utkastens struktur A eller B | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `struktur: "a"\|"b"` | inte gjord |
| LK-004 | Filtrera körningen (överskrivningar) | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: ` (` | inte gjord |
| LK-005 | Ange egna bolag | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `company_names[]` | inte gjord |
| LK-006 | Starta körningen | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `POST /leads/runs/batch` | inte gjord |
| LK-007 | Dubbelklick ger samma körning | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `api/dubbelstart.py:en_gang` | inte gjord |
| LK-008 | Spärrar vid start | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `leads.py:_require_live_llm` | inte gjord |
| LK-009 | Dygnsbudgeten och förvarningen | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `app/leads/budget.py:kontrollera_leads_budget` | inte gjord |
| LK-010 | Följa sökningen | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `GET /leads/jobb/{id}` | inte gjord |
| LK-011 | Följa körningen steg för steg | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `GET /leads/korningar/{id}` | inte gjord |
| LK-012 | Körningen överlever en omladdning | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `GET /leads/korningar/{id}` | inte gjord |
| LK-013 | Se vad körningen kördes med | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `overrides` | inte gjord |
| LK-014 | Egna bolag: jobb för jobb | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `result.jobs` | inte gjord |
| LK-016 | Snabbsökning utan research (`scope=sok`) | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `POST /leads/runs/batch {scope:"sok"}` | inte gjord |
| LK-017 | Var Kör Iris finns | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | behövs ingen (klient) | inte gjord |
| LK-015 | Demons exempelkörning | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | behövs ingen (klient) | inte gjord |
| LK-135 | Strukturväljaren A/B (en komponent överallt) | `/crm/iris/korningar` (ny): dialogen Kör Iris · BolagFormular, förloppet · SynkVy | 4 | finns: `struktur` | inte gjord |
| LK-020 | Se alla körningar | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `GET /leads/korningar?limit=30` | inte gjord |
| LK-021 | Körningens typ | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `scope` | inte gjord |
| LK-022 | Körningens status i kundens ord | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `status` | inte gjord |
| LK-023 | Utfallskolumnen | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `error` | inte gjord |
| LK-024 | Slutorsakerna | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `korning.slut_orsak` | inte gjord |
| LK-025 | Pollning medan något pågår | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `GET /leads/korningar` | inte gjord |
| LK-026 | Öppna en körnings detalj | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | behövs ingen (klient) | inte gjord |
| LK-027 | Se en pågående körning live | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `GET /leads/korningar` | inte gjord |
| LK-028 | Pausa och återuppta en körning | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `POST /leads/korningar/{id}/pausa` | inte gjord |
| LK-029 | Avbryta en körning | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `POST /leads/korningar/{id}/avbryt` | inte gjord |
| LK-030 | Fortsätta en körning som levererade under målet | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `POST /leads/korningar/{id}/fortsatt` | inte gjord |
| LK-031 | Se de bortvalda bolagen | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `GET /leads/korningar/{id}` | inte gjord |
| LK-032 | Se körningens leads (demon och listjobb) | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | behövs ingen (klient) | inte gjord |
| LK-033 | Körningens arbetsminne lämnar aldrig API:t | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | 4 | finns: `leads.py:_ARBETSMINNE, _utan_kandidater` | inte gjord |
| LK-034 | Körningens leads och utkast | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) + SynkVy | 4 | finns: `GET /leads/korningar/{id}/utkast` | inte gjord |
| LK-035 | Läsa ett utkast i körningen | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) + SynkVy | 4 | finns: se läsarens rad | inte gjord |
| LK-036 | Godkänna eller avvisa ett utkast i körningen | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) + SynkVy | 4 | finns: `POST /leads/queue/{id}/approve` | inte gjord |
| LK-037 | Skriva utkast till körningens leads som saknar | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) + SynkVy | 4 | finns: `POST /leads/korningar/{id}/utkast/skriv` | inte gjord |
| LK-038 | Godkänna och skicka alla väntande | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) + SynkVy | 4 | finns: `POST /leads/korningar/{id}/utkast/skicka-jobb` | inte gjord |
| LK-040 | Beställt antal = leverbara leads | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_leverbarhet, _run_batch_prospect, _komplettera_orgnr` | inte gjord |
| LK-041 | Sökrundor i geo-ringar | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `korning.py:sokrunda, MAX_PER_RUNDA` | inte gjord |
| LK-042 | Tratten: förfilter, existens, Jev, research | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `korning.py:sokrunda, utslag` | inte gjord |
| LK-043 | Inget bolag prövas två gånger | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_andra_korningars_bolag, _nyligen_bortvalda (BORTVAL_DAGAR=3… | inte gjord |
| LK-044 | När körningen slutar | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `korning.py:avsluta, max_rundor, TAK_FAKTOR, TOMMA_RUNDOR, har_malgrupp` | inte gjord |
| LK-045 | Kredittaket för sidhämtningar | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `korning.py:korningstak` | inte gjord |
| LK-046 | Sökningen breddas när kundens branscher tar slut | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_sla_in_sokrunda` | inte gjord |
| LK-047 | Körningens sammanfattning | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `korning.py:sammanfatta, fordelning` | inte gjord |
| LK-048 | Fördelningen efter körningen (listspåret) | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_spara_listspar` | inte gjord |
| LK-049 | Webbpoolen startas efter körningen | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `webbpool.efter_korning` | inte gjord |
| LK-050 | Prospekt ur en kandidat | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_skapa_prospekt_ur_kandidat` | inte gjord |
| LK-051 | Researchjobbet per bolag | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_run_batch_prospect` | inte gjord |
| LK-052 | Tillfällig kvot hos modellen | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:KVOT_OMFORSOK, KVOT_PAUS_S, _ar_tillfallig_kvot` | inte gjord |
| LK-053 | Kreditslut larmar Snajp | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_larma_vid_kreditslut, _jobbfeltext` | inte gjord |
| LK-054 | Körningen överlever deploy och krasch | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_ateruppta_korning, _rapportera_till_korning, _markera_korni… | inte gjord |
| LK-055 | Väckaren för körningar som står still | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:vack_stillastaende_korningar` | inte gjord |
| LK-057 | Processa om / Skapa om utkast för sparade leads | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `POST /leads/prospects/processa-om {prospect_ids, scope, ersatt?, struktur, is_test}` | inte gjord |
| LK-056 | Flera körningar samtidigt | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `leads.py:_korningslas` | inte gjord |
| LK-136 | Städaren ger hängande körningar och listor ett ärligt slut | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/korningar` · SynkVy | 4 | finns: `; ` | inte gjord |
| LK-060 | Se hur Iris tolkat kunden (Iris-profilen) | `/crm/installningar/iris` (ny) kortet Iris-profilen · OversiktVy (kort) + BolagFormular | 4 | finns: `GET /leads/profil` | inte gjord |
| LK-061 | Profilen tolkas om när underlaget ändras | `/crm/installningar/iris` (ny) kortet Iris-profilen · OversiktVy (kort) + BolagFormular | 4 | finns: `; modell ` | inte gjord |
| LK-062 | Tolka om profilen | `/crm/installningar/iris` (ny) kortet Iris-profilen · OversiktVy (kort) + BolagFormular | 4 | finns: `POST /leads/profil/tolka-om` | inte gjord |
| LK-063 | Se Jevs träffsäkerhet | `/crm/installningar/iris` (ny) kortet Iris-profilen · OversiktVy (kort) + BolagFormular | 4 | finns: `GET /leads/jev/statistik` | inte gjord |
| LK-064 | Välja hur långt agenterna får gå (autonomi) | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `GET/PUT /leads/config {autonomy}` | inte gjord |
| LK-065 | Spara målgruppen (ICP) | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `PUT /leads/config {icp}` | inte gjord |
| LK-066 | Region- och SNI-val ur backenden | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `GET /leads/config` | inte gjord |
| LK-067 | Kundval: webbplatskrav och behovskrav (regel 22) | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `PUT /leads/config {webbplats_kravs, behov}` | inte gjord |
| LK-068 | Kundval: egna målsegment och offentlig sektor | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `PUT /leads/config {segment, offentlig_sektor}` | inte gjord |
| LK-069 | Autopilot: en körning varje vardag | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `PUT /leads/config {automation:{autopilot:{pa, leads_per_dag}}}` | inte gjord |
| LK-070 | Struktur i automatiska körningar | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `automation.struktur` | inte gjord |
| LK-071 | Automation per typ av lead | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `automation.per_typ` | inte gjord |
| LK-072 | Låt Jev välja bort automatiskt | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `automation.jev_bortval` | inte gjord |
| LK-073 | Synk till CRM | `/crm/synk` (befintlig) · SynkVy | 3 | finns: `PUT /leads/config {crm_synk}` | inte gjord |
| LK-137 | Målgruppens validering och tak | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `app/leads/icp.py:validate_icp, normalize_icp, MAX_ITEMS_PER_FIELD, MA… | inte gjord |
| LK-138 | Autopilotens körning skiljer sig från Kör Iris | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `app/leads/autopilot.py:ska_kora, svep, _starta, KORTIMME=6` | inte gjord |
| LK-080 | Registret som filter (regel 1) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `sources/merinfo.py:sok, aktiv, register` | inte gjord |
| LK-081 | Registrets kodfilter | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `merinfo.kontrollera` | inte gjord |
| LK-082 | Jev som första filter (regel 2) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `jev.py:triage, lage, motor, _utan_personuppgifter` | inte gjord |
| LK-083 | Rangordning av registerbolag | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `merinfo._kodpoang, PROV_PER_LEAD` | inte gjord |
| LK-084 | Hitta bolagets webbplats (regel 4, 12) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `merinfo._webbplats, _ligger_annorstades` | inte gjord |
| LK-085 | Parkerade och avvecklade bolag | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `platshallare.ar_platshallare, AVVECKLAT` | inte gjord |
| LK-086 | Kontaktsökningen på bolagets sajt (regel 12) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `discovery.hamta_person_kontakt, kontakt_ur_sidor, extrahera_kontaktlankar` | inte gjord |
| LK-087 | Vilken adress och vilket tilltal (regler 13, 14) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `discovery.bolagsadress_i_text, bolagstelefon_i_text, ar_saljadress (_… | inte gjord |
| LK-088 | Fördelningen efter kontaktsökningen (regler 12–16, 22) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `merinfo.fordela, iris_kandidat, ringrad, _listrad, _komplettera_iris` | inte gjord |
| LK-089 | Iris-adress utanför bolagets domän | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `discovery.mottagare, SAJTENS_HARKOMSTER` | inte gjord |
| LK-090 | Listornas VD-krav (regel 5, 7) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `merinfo._komplettera (lage="lista"), ensam_vd_telefon` | inte gjord |
| LK-091 | Inga privatpersonsidor (regel 6) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `merinfo.bolagsfakta_text, bolagsfakta_ur` | inte gjord |
| LK-092 | Sökkedjan fyller på (regel 11) | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `discovery.hitta_bolag, _sok_registrerade_kallor, _gemini_med_sokning, _rena_traffar` | inte gjord |
| LK-093 | Existensgrinden | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `existens.styrk` | inte gjord |
| LK-139 | Förfiltrets regler och skäl | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `app/leads/forfilter.py:forfiltrera, ar_enskild_firma` | inte gjord |
| LK-140 | Existensgrindens skäl | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `app/leads/existens.py:styrk, REGISTERKALLOR` | inte gjord |
| LK-141 | Platshållare och avvecklade sajter känns igen | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · SynkVy | 4 | finns: `app/leads/platshallare.py:platshallarskal, platshallare_for_webbplats… | inte gjord |
| LK-100 | Se var i importen man är | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | behövs ingen (klient) | inte gjord |
| LK-101 | Välja eller släppa en fil | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | behövs ingen (klient) | inte gjord |
| LK-102 | Koppla kolumner till fält | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | behövs ingen (klient) | inte gjord |
| LK-103 | Värdena kontrolleras | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | behövs ingen (klient) | inte gjord |
| LK-104 | Granska vad som importeras | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `POST /leads/import/granska {kalla, rader[{company_name, orgnr, contact_email}]}` | inte gjord |
| LK-105 | Importera i delar med förlopp | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `POST /leads/import {titel, rader, kalla, list_id?, importinfo?, ta_med_leads}` | inte gjord |
| LK-106 | Kvittot | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `lead_lists.importinfo` | inte gjord |
| LK-107 | Befintliga kunder utesluts överallt | Ingen egen vy: under ytan, oförändrad backend; ändras i fas 3 enligt besluten 2026-11-26 | 3 | finns; ändras i fas 3: tidigare kunder räknas inte som upptagna (beslut 2026-11-26) | inte gjord |
| LK-108 | Upptagna bolag: ett bolag, ett ställe | Ingen egen vy: under ytan, oförändrad backend; ändras i fas 3 enligt besluten 2026-11-26 | 3 | finns; ändras i fas 3: CRM-bolag med org.nr utesluts bara på numret | inte gjord |
| LK-143 | Filen läses i webbläsaren, oavsett kodning | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `lib/leads/importfil.ts:avkoda, MAX_FILSTORLEK` | inte gjord |
| LK-144 | Rubrikraden och skräpraderna hittas själv | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `lib/leads/importmallar.ts:hittaRubrikrad, tolkaTabell, FOT, SUMMA` | inte gjord |
| LK-145 | Kolumnerna föreslås ur rubrik OCH innehåll | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `lib/leads/importmallar.ts:gissaKolumner, flervalsordning, bytKolumnva… | inte gjord |
| LK-146 | Raderna byggs och dubbletter i filen slås ihop | `/crm/iris/listor` (ny) › Importera · NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 4 | finns: `lib/leads/importrader.ts:tolkaRader, bolagsnyckel, sammanfatta, importrader` | inte gjord |
| LK-147 | Panelen för befintliga kunder (CRM-kundlistan) | `/crm/bolag` (befintlig) segment Egna · BolagVy + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 3 | finns (`lead_lists.kalla='crm'`); ska gå upp i CRM:ets bolag, väg saknas | inte gjord |
| LK-110 | Beställa en lista (listbygget) | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `POST /leads/listor` | inte gjord |
| LK-111 | Listan byggs i bakgrunden | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `leads.py:_run_list_job` | inte gjord |
| LK-112 | Listbygget matar webbpoolen | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `webbpool.bolagsrad(…, "lista")` | inte gjord |
| LK-113 | Listspåret "Ej kvalificerade, Iris <datum>" | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `leads.py:_spara_listspar` | inte gjord |
| LK-114 | Processa om en lista | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `POST /leads/listor/{id}/omprova {item_ids?}` | inte gjord |
| LK-115 | Skapa utkast för en listas bolag | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `POST /leads/listor/{id}/utkast {item_ids?}` | inte gjord |
| LK-116 | Äldre generella listutkast kan köas | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `POST /leads/listor/{id}/items/{item}/koa {email, subject?, body?}` | inte gjord |
| LK-117 | Säljlistan: CRM över bolagen man ringt | `/crm/iris/listor` (ny) vyn Säljlista · BolagVy + NYTT MÖNSTER: redigerbara celler i tabellen | 4 | finns: `lib/actions/saljlista.ts` | inte gjord |
| LK-118 | Beställ leads-lista till säljlistan | `/crm/iris/listor` (ny) vyn Säljlista · BolagVy + NYTT MÖNSTER: redigerbara celler i tabellen | 4 | finns: `POST /leads/listor {titel, antal, mal:"saljlista", overrides:{must_have:[titel]}}` | inte gjord |
| LK-142 | Listbyggets kontaktskörd utan modell | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `discovery.hamta_kontaktvag, plocka_arbetsmejl, extrahera_kontaktlankar, sla_upp_webbplats` | inte gjord |
| LK-148 | Säljlistans fältregler | `/crm/iris/listor` (ny) vyn Säljlista · BolagVy + NYTT MÖNSTER: redigerbara celler i tabellen | 4 | finns: `uppdateraSaljrad` | inte gjord |
| LK-149 | Varning för samma bolag två gånger i säljlistan | `/crm/iris/listor` (ny) vyn Säljlista · BolagVy + NYTT MÖNSTER: redigerbara celler i tabellen | 4 | finns: `lib/leads/saljlista.ts:dubblettnycklar` | inte gjord |
| LK-150 | Säljlistan på telefon, statusförklaring och CSV | `/crm/iris/listor` (ny) vyn Säljlista · BolagVy + NYTT MÖNSTER: redigerbara celler i tabellen | 4 | finns: `lib/leads/saljlista.ts:byggSaljCsv` | inte gjord |
| LK-151 | Säljlistans grind sitter i varje server action | `/crm/iris/listor` (ny) vyn Säljlista · BolagVy + NYTT MÖNSTER: redigerbara celler i tabellen | 4 | finns: `; tabell ` | inte gjord |
| LK-120 | Webbrevision av ett bolags startsida | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | finns: `app/leads/webbrevision.py:revidera, pagespeed, skarmbild_via_scrapegraph, startsida` | inte gjord |
| LK-121 | Fyra webbnivåer, inget gränsfall (regel 18) | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | finns: `webbrevision.webbniva, AKUT_HOGST, DALIG_HOGST, BRA_HOGST, KATALOGDOMANER` | inte gjord |
| LK-122 | Webbkriterier avgörs i kod (regel 9) | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | finns: `bedomning.webbutslag` | inte gjord |
| LK-123 | Webbpoolen samlar varje körnings bolag | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | finns: `webbpool.bolagsrad, mata_in, utesluten_kalla, POOLFALT, PERSONFALT` | inte gjord |
| LK-124 | Bedömning efter körningen | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | finns: `webbpool.efter_korning, bedom, bedom_en, farsk_revision, FARSK` | inte gjord |
| LK-125 | Fördelning efter län (regel 20) | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | finns: `webbpool.fordela, _lagg_i_lista, _veckolista, _signal, lan_for, lan_ur_postnr` | inte gjord |
| LK-126 | Bakåtfyllnad av gamla leads (plattformsadmin) | `/crm/admin/kunder` (ny) åtgärd, bara plattformsadmin · BolagFormular + SynkVy | 5 | finns: `GET/POST /api/admin/webbpool/bakatfyll {apply, max_bedom, utan_kreditkontroll}` | inte gjord |
| LK-127 | Ombedömning av sparade Iris-leads (plattformsadmin) | `/crm/admin/kunder` (ny) åtgärd, bara plattformsadmin · BolagFormular + SynkVy | 5 | finns: `POST /api/admin/tenants/{tenant_id}/leads-ombedom` | inte gjord |
| LK-128 | Förhandsvisning av en webbpoollista | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | 4 | behövs ingen (klient) | inte gjord |
| LK-130 | Demons märkta exempelkörning | Demon och `/forhandsvisning/crm/...` med exempeldata · samma mönster som vyn | 4 | finns: `lib/demo/leads-korning.ts` | inte gjord |
| LK-131 | Iris › Bolag i demon: exempelbolagen överst i listan | Demon och `/forhandsvisning/crm/...` med exempeldata · samma mönster som vyn | 4 | behövs ingen (klient) | inte gjord |
| LK-132 | Exempelbolag med pitchar (förhandsvisning och demokunden) | Demon och `/forhandsvisning/crm/...` med exempeldata · samma mönster som vyn | 4 | finns: `POST /leads/prospects/exempel {limit, overrides, fro}` | inte gjord |
| LK-133 | Demokundens körning använder exempelbolagen | Demon och `/forhandsvisning/crm/...` med exempeldata · samma mönster som vyn | 4 | finns: `leads.py:_samla_korningens_prospekt, _validera_batch_kan_starta` | inte gjord |
| LK-134 | Adminens Testkörningar | `/crm/admin/logg` (ny) vyn Testkörningar · BolagFormular + SynkVy | 5 | finns: `POST /leads/runs/batch {is_test:true}` | inte gjord |
| LK-152 | Förhandsvisning av en körnings leads och utkast | Demon och `/forhandsvisning/crm/...` med exempeldata · samma mönster som vyn | 4 | behövs ingen (klient) | inte gjord |

### Leads: utkast, konversationer, samtal (app-05, 129 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| LU-001 | Se alla konversationer (bolag som svarat) i en lista, senast aktiva först | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `GET /api/leads/konversationer` | inte gjord |
| LU-002 | Filtrera konversationerna | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: se läsarens rad | inte gjord |
| LU-003 | Systemet avgör vad som är "Att göra" | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `app/leads/konversation.py:att_gora` | inte gjord |
| LU-004 | Systemet härleder konversationens steg | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `konversation.steg` | inte gjord |
| LU-005 | Öppna en konversation; den öppna står i adressen | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | behövs ingen (klient) | inte gjord |
| LU-006 | Att öppna en tråd markerar dess notiser lästa | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/konversationer/{id}/last` | inte gjord |
| LU-007 | Se trådens huvud: bolag, kontaktperson, roll, mejl (mailto) och telefon (tel) | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `GET /api/leads/konversationer/{id}` | inte gjord |
| LU-008 | Läsa hela konversationen i tidsordning | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: se läsarens rad | inte gjord |
| LU-009 | Byta konversationens steg (Svarat, Möte bokat, Återkom, Ej intresserad, Kontakta inte) | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/konversationer/{id}/steg` | inte gjord |
| LU-010 | Se mejl som skickats utanför Snajp | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `konversation.externa_ur_citat` | inte gjord |
| LU-011 | Lägga in ett mejl skickat eller mottaget utanför Snajp för hand | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/konversationer/{id}/extern` | inte gjord |
| LU-012 | Se och återställa kasserade utkast | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/konversationer/{id}/utkast/{message_id}/aterstall` | inte gjord |
| LU-013 | Redigera svarsutkastet (ämne och text) i utkaststudion | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `PUT /api/leads/konversationer/{id}/utkast` | inte gjord |
| LU-014 | Spärr: utkast som påstår en redan gjord handling måste bekräftas | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `konversation.handlingspastaenden` | inte gjord |
| LU-015 | Godkänna och skicka svarsutkastet | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/konversationer/{id}/utkast/skicka` | inte gjord |
| LU-016 | Kassera svarsutkastet | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST …/utkast/kassera` | inte gjord |
| LU-017 | Låta Iris skriva om utkastet, eller skriva ett nytt, med ett valfritt önskemål | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST …/utkast/generera` | inte gjord |
| LU-018 | Tomläge när inget utkast väntar | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | behövs ingen (klient) | inte gjord |
| LU-019 | Förslag: markera Möte bokat när ett mejl säger att en inbjudan skickats | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `konversation.ser_ut_som_bokat_mote` | inte gjord |
| LU-020 | Påminnelse om återkontakt när datumet passerat, med utkast på begäran | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST …/utkast/generera` | inte gjord |
| LU-021 | Se konversationens händelselogg | `/crm/iris/konversationer` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `lead_handelser` | inte gjord |
| LU-022 | Notisklockan i Leads sidhuvud | `CrmRam` (befintlig) och sidhuvudet i Iris · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `GET /api/leads/notiser?limit=30` | inte gjord |
| LU-023 | Räknaren för olästa notiser | `CrmRam` (befintlig) och sidhuvudet i Iris · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `GET /api/leads/notiser/antal` | inte gjord |
| LU-024 | Panelen "Konversationer som väntar" på Leads › Översikt | `/crm/iris` (ny) Iris-översikt · OversiktVy | 4 | finns: `GET /api/leads/konversationer` | inte gjord |
| LU-030 | Se alla utkast som väntar på granskning, nyast först | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `GET /api/snajp-support/leads/queue` | inte gjord |
| LU-031 | Systemet rättar äldre utkast när de läses i kön | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `list_review_queue` | inte gjord |
| LU-032 | Kompakt utkastruta på Leads › Översikt | `/crm/iris` (ny) Iris-översikt, kortet Utkast · OversiktVy | 4 | finns: se läsarens rad | inte gjord |
| LU-033 | Öppna och redigera ett utkast i mejlstudion | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `PUT /api/leads/queue/{id}` | inte gjord |
| LU-034 | Godkänna och skicka ett utkast | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/queue/{id}/approve` | inte gjord |
| LU-035 | Avvisa ett utkast | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `POST /api/leads/queue/{id}/reject` | inte gjord |
| LU-036 | Godkänna eller avvisa flera utkast på en gång, med bekräftelse | `/crm/iris/utkast` (ny) · TableSelectionToolbar + bekräftelsedialog | 4 | finns: se läsarens rad | inte gjord |
| LU-037 | Skicka ett provmejl av utkastet (eller ett skickat mejl) till sig själv | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `GET /api/leads/provmejl/mottagare` | inte gjord |
| LU-038 | Se signatur, logga och lagstadgad fot som mottagaren ser dem | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `GET /api/leads/queue` | inte gjord |
| LU-039 | Demoläge för granskningen | `/crm/iris/utkast` (ny) vyn Att granska · BolagVy + NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | behövs ingen (klient) | inte gjord |
| LU-050 | Systemet skickar bara det en människa godkänt | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler.process_godkanda` | inte gjord |
| LU-051 | Sändfönster och tidsgrind | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `timing_gate.check_cold_outreach_gate` | inte gjord |
| LU-052 | Takt: ett mejl i taget | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler.for_tatt` | inte gjord |
| LU-053 | Spärr 0: begränsad behandling (GDPR art. 18) | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler._kor_send_guard` | inte gjord |
| LU-054 | Spärr 0: exempelbolag, provkörning, ej styrkt, arkiverat, avslutat | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `_kor_send_guard` | inte gjord |
| LU-055 | Sändspärr regel 3: spärrlista och egna kunder | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `send_guard._regel_3_suppression` | inte gjord |
| LU-056 | Sändspärr regel 1: avsändaren ska gå att identifiera | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `_regel_1_avsandaridentifikation` | inte gjord |
| LU-057 | Sändspärr regel 2: avregistreringslänk och integritetspolicy | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `_regel_2_avregistrering` | inte gjord |
| LU-058 | Sändspärr regel 4: GDPR art. 14-information vid personlig adress | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `_regel_4_personuppgiftsflagga` | inte gjord |
| LU-059 | Sändspärr regel 5: karens, volymtak och leveransstopp | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `_regel_5_volymtak` | inte gjord |
| LU-060 | Sändspärr regel 6: de tre första utskicken granskas | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `_regel_6_granskningsko` | inte gjord |
| LU-061 | Språkgrind | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `send_decision.check_send_gate` | inte gjord |
| LU-062 | Sändfel: mejltjänsten tar inte emot | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler._process_due_item` | inte gjord |
| LU-063 | Vid utskick: avsändare, svarsadress, HTML med signatur, taggar | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler._avsandaridentitet` | inte gjord |
| LU-064 | Vid utskick: hälsning, signatur, demolänk och lagstadgad fot sätts på | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler._fot_vid_godkannande` | inte gjord |
| LU-065 | Efter utskick: status Kontaktad och kopia i kundens Skickat | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `mark_outreach_message_sent` | inte gjord |
| LU-066 | Utskick bara från miljön där det godkändes | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `scheduler.skickas_har` | inte gjord |
| LU-067 | Ändra utskickstiden för markerade godkända utkast | `/crm/iris/utkast` (ny) vyn Skickas snart · TableSelectionToolbar | 4 | finns: `POST /api/leads/queue/schemalagg` | inte gjord |
| LU-068 | Skicka nu ur kön | `/crm/iris/utkast` (ny) vyn Skickas snart · TableSelectionToolbar | 4 | finns: `POST /api/leads/queue/{id}/skicka-nu` | inte gjord |
| LU-069 | Flytta markerade utkast tillbaka till Iris | `/crm/iris/utkast` (ny) vyn Skickas snart · TableSelectionToolbar | 4 | finns: `POST /api/leads/queue/tillbaka-till-iris` | inte gjord |
| LU-070 | Studsar och klagomål från mejltjänsten | Ingen egen vy: under ytan, oförändrad backend; utfall och skäl syns i `/crm/iris/utkast` · SynkVy | 4 | finns: `POST /api/webhooks/resend/emails` | inte gjord |
| LU-080 | Växla mellan Inkommande och Skickat i Leads › Inkorg | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: `GET /api/leads/skickat?limit=500` | inte gjord |
| LU-081 | Inkommande: kundtjänstinkorgen filtrerad på leads | `/crm/iris/konversationer` (ny) vyn Inkommande · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 4 | finns: `GET /api/inbox` | inte gjord |
| LU-082 | Se alla skickade leadsmejl med leadets nuvarande status | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: `GET /api/leads/skickat` | inte gjord |
| LU-083 | Filtrera Skickat på läge | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | behövs ingen (klient) | inte gjord |
| LU-084 | Se godkända utkast som väntar på sändfönstret överst ("Skickas snart") | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: `_schemalagda_utskick` | inte gjord |
| LU-085 | Skicka nu, Ändra tid och Tillbaka till Iris för markerade schemalagda | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: se LU-067–LU-069 | inte gjord |
| LU-086 | Skapa uppföljning för markerade bolag som väntar på svar | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: `POST /api/leads/uppfoljningar/skapa` | inte gjord |
| LU-087 | Skicka provmejl av ett skickat eller schemalagt mejl | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: `POST /api/leads/provmejl` | inte gjord |
| LU-088 | Nyckeltalen skickade och svar (senaste 28 dagarna) | `/crm/iris/utkast` (ny) vyerna Skickas snart och Skickat · BolagVy | 4 | finns: `GET /api/leads/skickat/antal?dagar=` | inte gjord |
| LU-089 | Äldre Svar-flik: lista inkomna svar | `/crm/iris/konversationer` (ny) vyn Inkommande · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 4 | finns: `GET /api/leads/svar` | inte gjord |
| LU-090 | Ta emot ett prospektsvar via API (utan inkorg) | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `POST /api/leads/svar` | inte gjord |
| LU-100 | Se uppföljningarnas läge per lead i arbetsordning | `/crm/iris/uppfoljningar` (ny) · BolagVy + BolagPanel | 4 | finns: `GET /api/leads/uppfoljningar` | inte gjord |
| LU-101 | Godkänna, avvisa och läsa en uppföljning som väntar | `/crm/iris/uppfoljningar` (ny) · BolagVy + BolagPanel | 4 | finns: `POST /api/leads/queue/{id}/approve\|reject` | inte gjord |
| LU-102 | Se när nästa uppföljning blir aktuell | `/crm/iris/uppfoljningar` (ny) · BolagVy + BolagPanel | 4 | finns: `fordela` | inte gjord |
| LU-103 | Skapa uppföljning nu för markerade leads | `/crm/iris/uppfoljningar` (ny) · BolagVy + BolagPanel | 4 | finns: `POST /api/leads/uppfoljningar/skapa` | inte gjord |
| LU-104 | Se skickade uppföljningar de senaste 30 dagarna | `/crm/iris/uppfoljningar` (ny) · BolagVy + BolagPanel | 4 | finns: `skickade_uppfoljningar` | inte gjord |
| LU-105 | Systemet skriver förfallna uppföljningar (bevakningen) | Ingen egen vy: under ytan, oförändrad backend; syns i `/crm/iris/uppfoljningar` | 4 | finns: `scheduler.sweep_follow_ups` | inte gjord |
| LU-106 | Köra uppföljningssvepet för den egna kunden på begäran | `/crm/iris/uppfoljningar` (ny) · BolagVy + BolagPanel | 4 | finns: `POST /api/leads/uppfoljning/svep` | inte gjord |
| LU-107 | Ett svar stoppar uppföljningarna | Ingen egen vy: under ytan, oförändrad backend; syns i `/crm/iris/uppfoljningar` | 4 | finns: `follow_up_generator._AVSLUTADE` | inte gjord |
| LU-110 | Systemet knyter ett inkommande mejl till rätt lead | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `email_pipeline/klassning.py` | inte gjord |
| LU-111 | Svaret sparas och notis skapas direkt | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `svar.hantera_prospektsvar` | inte gjord |
| LU-112 | Påhopp eller missbruk avbryter samtalet | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `moderation/abuse_gate.check_abuse` | inte gjord |
| LU-113 | Iris klassar svaret | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `svar.py` | inte gjord |
| LU-114 | Positivt svar: människan tar över | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `svar.py` | inte gjord |
| LU-115 | Återkom-svar: datum och påminnelse | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `svar.py` | inte gjord |
| LU-116 | Invändning eller fråga: svarsutkast till granskning | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `svar._skriv_svarsutkast` | inte gjord |
| LU-117 | Eskaleringsregler: pris, juridik och nej går till en människa | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `app/leads/eskalering.py` | inte gjord |
| LU-118 | Negativt svar: Ej intresserad med en återkontakt | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `svar.py` | inte gjord |
| LU-119 | Avregistrering via svar: Kontakta inte | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `storage.add_suppression` | inte gjord |
| LU-120 | Autosvar skjuter kön en vecka | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `reschedule_pending_sends` | inte gjord |
| LU-121 | Prioriterat mejl när ett svar behöver en människa (RÄTTAD: går till Snajp, inte till kunden) | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `notifications/prioriterat_mejl.py` | inte gjord |
| LU-122 | Varje svarshantering loggas som agentkörning | Ingen egen vy: under ytan, oförändrad backend; resultatet syns i `/crm/iris/konversationer` | 4 | finns: `storage.log_agent_run` | inte gjord |
| LU-130 | Växla mellan Återkoppling och Ringlista | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `GET /api/leads/samtal?lista=aterkoppling\|ring` | inte gjord |
| LU-131 | Vilka som står i återkopplingslistan | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `samtal.samtalslista` | inte gjord |
| LU-132 | Vilka som står i ringlistan | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `samtal.samtalslista` | inte gjord |
| LU-133 | Se varje bolag att ringa: tabell på bred skärm, kort på telefon | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `samtalslista` | inte gjord |
| LU-134 | Registrera ett samtal med utfall | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `POST /api/leads/prospects/{id}/samtal` | inte gjord |
| LU-135 | Systemet verkställer samtalsutfallet | Ingen egen vy: under ytan, oförändrad backend; utfallet syns i listan och på tidslinjen | 4 | finns: `samtal.registrera` | inte gjord |
| LU-136 | Antal att ringa i dag per lista | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `GET /api/leads/samtal/antal` | inte gjord |
| LU-137 | Samtalen syns i konversationen och på leadets tidslinje | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | finns: `lead_samtal` | inte gjord |
| LU-138 | Demoläge för samtalslistan | `/crm/iris/samtal` (ny) · BolagVy (mobil: rader) + BolagFormular (utfall) | 4 | behövs ingen (klient) | inte gjord |
| LU-140 | Varje utskick bär en avregistreringslänk och en lagstadgad fot, byggd i kod | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `app/leads/utskicksfot.py` | inte gjord |
| LU-141 | Mottagaren avregistrerar sig på den publika sidan | Utanför `/crm`: publika `/avregistrera/[token]` behålls | 5 | finns: `public.avregistrera_via_token(token)` | inte gjord |
| LU-142 | Spärrlistan (suppressions) gäller hela kunden och permanent | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `storage.add_suppression` | inte gjord |
| LU-143 | Begränsad behandling (GDPR art. 18) stoppar allt hos alla kunder | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `behandlingsbegransningar` | inte gjord |
| LU-144 | Gallring efter kundens beslutade period | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `app/jobs/gallring.py` | inte gjord |
| LU-145 | Arkivering och avslutade leads stoppar utskick | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `scheduler.avbryt_utskick_for_prospekt` | inte gjord |
| LU-150 | Mallförbudet: varje utkast genereras för just det bolaget | `/crm/iris/leads` (ny) och `/crm/iris/korningar/[id]` · TableSelectionToolbar + SynkVy | 4 | finns: `app/agent/leads_research_v2.run_outreach_draft_v2` | inte gjord |
| LU-151 | Utkastkedjan, steg för steg | `/crm/iris/leads` (ny) och `/crm/iris/korningar/[id]` · TableSelectionToolbar + SynkVy | 4 | finns: `leads_research_v2.py` | inte gjord |
| LU-152 | Skapa utkast för ett lead som bakgrundsjobb | `/crm/iris/leads` (ny)`?lead=` · BolagPanel + SynkVy | 4 | finns: `POST /api/leads/outreach/draft` | inte gjord |
| LU-153 | Se leadets senaste utkast med riktig status | `/crm/iris/leads` (ny)`?lead=` · BolagPanel + SynkVy | 4 | finns: `GET /api/leads/prospects/{id}/utkast` | inte gjord |
| LU-154 | Utkast i mängd från Iris-listan och registret, med förlopp | `/crm/iris/leads` (ny) · TableSelectionToolbar + SynkVy | 4 | finns: `POST /api/leads/runs/batch` | inte gjord |
| LU-155 | En körnings leads och utkast på körningssidan | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + SynkVy | 4 | finns: `GET /api/leads/korningar/{job_id}/utkast` | inte gjord |
| LU-156 | Skriv utkast till körningens leads som saknar | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + SynkVy | 4 | finns: `POST /api/leads/korningar/{job_id}/utkast/skriv` | inte gjord |
| LU-157 | Godkänn och skicka alla körningens väntande utkast, med förlopp | `/crm/iris/korningar/[id]` (ny) fliken Utkast · BolagVy + SynkVy | 4 | finns: `POST /api/leads/korningar/{job_id}/utkast/skicka-jobb` | inte gjord |
| LU-158 | Listspårets utkast ("Utan webbplats") | `/crm/iris/listor` (ny) · BolagVy + SynkVy | 4 | finns: `app/leads/listutkast.py` | inte gjord |
| LU-159 | Välja mejlens struktur A eller B | `/crm/installningar/iris` (ny) och dialogen Kör Iris · BolagFormular | 4 | finns: `outreach_threads.struktur` | inte gjord |
| LU-160 | Skapa en kampanj till en befintlig lista eller en körnings leads | `/crm/iris/kampanjer` (ny) · BolagVy + BolagFormular + SynkVy | 4 | finns: `POST /api/leads/kampanjer` | inte gjord |
| LU-161 | Följa kampanjens förlopp och utfall | `/crm/iris/kampanjer` (ny) · BolagVy + BolagFormular + SynkVy | 4 | finns: `GET /api/leads/kampanjer` | inte gjord |
| LU-162 | Godkänna och skicka en kampanjs väntande utkast | `/crm/iris/kampanjer` (ny) · BolagVy + BolagFormular + SynkVy | 4 | finns: `POST /api/leads/kampanjer/{id}/skicka-jobb` | inte gjord |
| LU-170 | Registrera ett samtal via API (vägen bakom "Ringd") | `/crm/iris/leads` (ny)`?lead=` fliken Tidslinje · NYTT MÖNSTER: tidslinje på posten (händelser, anteckningar, uppgifter) | 4 | finns: `POST /api/leads/prospects/{id}/samtal` | inte gjord |
| LU-171 | Samtalen på leadets tidslinje | `/crm/iris/leads` (ny)`?lead=` fliken Tidslinje · NYTT MÖNSTER: tidslinje på posten (händelser, anteckningar, uppgifter) | 4 | finns: `GET /api/leads/prospects/{id}/tidslinje` | inte gjord |
| LU-172 | Demolänken läggs i varje utkast när kunden har en demo | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `app/leads/demolank.py` | inte gjord |
| LU-173 | Mottagaren klickar demolänken | Utanför `/crm`: `/prova/[token]` behålls | 4 | finns: `public.demolank_klick` | inte gjord |
| LU-174 | Se vilka som klickat demolänken och vilka som besökt demon | `/crm/iris` (ny) Iris-översikt, kortet Demolänken · OversiktVy | 4 | finns: `GET /api/leads/demobesok?limit=` | inte gjord |
| LU-175 | Tidsgrindens helgdagar | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `app/leads/timing_gate.py` | inte gjord |
| LU-176 | Uppskattad sändtid per godkänt utkast ("Skickas <tid>") | `/crm/iris/utkast` (ny) vyn Skickas snart · BolagVy | 4 | finns: `app/leads/sandplan.py` | inte gjord |
| LU-177 | Språkläget i tråden och språkgrinden | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `app/leads/language_gate.py` | inte gjord |
| LU-178 | Hälsningsraden och tilltalet rättas i kod | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `app/leads/halsning.py` | inte gjord |
| LU-179 | Signaturen: vad kunden kan fylla i och hur den läggs på | `/crm/installningar/iris` (ny) avsnittet Utskick · BolagFormular | 4 | finns: `app/leads/signatur.py` | inte gjord |
| LU-180 | Bekräftelserutan för massåtgärder | `/crm/iris/utkast` (ny) · TableSelectionToolbar + bekräftelsedialog | 4 | behövs ingen (klient) | inte gjord |
| LU-181 | Svepet som rättar alla osända utkast efter nya hälsnings- och signaturregler | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `POST /api/admin/leads/normalisera-utkast` | inte gjord |
| LU-182 | Avregistreringen stämplar länken och upprepas utan dubbletter | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `public.avregistrera_via_token` | inte gjord |
| LU-183 | Autosvarets uppskjutning gäller bara godkända köposter | Ingen egen vy: under ytan, oförändrad backend | 4 | finns: `storage.reschedule_pending_sends` | inte gjord |

### Support (app-06, 176 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| SU-001 | Kunden öppnar Kundtjänst från menyn | `/crm/kundtjanst` (ny) · Sida + Vyrad (Översikt, Ärenden, Testmail, Dolda, Testchatt) | 5 | finns: `resolveDashboardState()` | inte gjord |
| SU-002 | Knapp till agentens fristående sajt ovanför flikarna | `/crm/kundtjanst` (ny) sidhuvudets ikonknapp Kör agent · Sida | 5 | finns: se SU-100 | inte gjord |
| SU-003 | Flikrad: Översikt, Ärenden, (Testmail), Dolda, Testchatt | `/crm/kundtjanst` (ny) · Sida + Vyrad (Översikt, Ärenden, Testmail, Dolda, Testchatt) | 5 | finns: `GET /api/inbox` | inte gjord |
| SU-004 | Fliken Ärenden = mejlinkorgen för supportärenden | `/crm/kundtjanst` (ny) · Sida + Vyrad (Översikt, Ärenden, Testmail, Dolda, Testchatt) | 5 | finns: se B | inte gjord |
| SU-005 | Fliken Testmail = bara testärenden | `/crm/kundtjanst` (ny) · Sida + Vyrad (Översikt, Ärenden, Testmail, Dolda, Testchatt) | 5 | finns: `GET /api/inbox?is_test=true` | inte gjord |
| SU-006 | Fliken Dolda = det klassningen sorterade bort | `/crm/kundtjanst` (ny) · Sida + Vyrad (Översikt, Ärenden, Testmail, Dolda, Testchatt) | 5 | finns: `GET /api/inbox?klass=ej_relaterat` | inte gjord |
| SU-007 | Fliken Testchatt = prova agenten på riktigt | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `/api/snajp-support/testchatt` | inte gjord |
| SU-008 | Ej aktiverad arbetsyta visar väntläge, inte fel | `/crm/kundtjanst` (ny) · Sida + Vyrad (Översikt, Ärenden, Testmail, Dolda, Testchatt) | 5 | finns: `requireSnajpTenant()` | inte gjord |
| SU-010 | Lista inkommande kundmejl | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox?status&category&q&limit&is_test&klass` | inte gjord |
| SU-011 | Statusvärden och deras färg | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `ss_emails.status` | inte gjord |
| SU-012 | Sök i inkorgen | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox?q=` | inte gjord |
| SU-013 | Filtrera på status | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox?status=` | inte gjord |
| SU-014 | Filtrera på fack (kategori) med antal | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox?category=` | inte gjord |
| SU-015 | Visa bara ohanterade | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | behövs ingen (klient) | inte gjord |
| SU-016 | Summering "n väntar på dig · n eskalerade" | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | behövs ingen (klient) | inte gjord |
| SU-017 | Öppna ett mejl i detaljpanel | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox/{id}` | inte gjord |
| SU-018 | Brevlådans läge syns på mejlet | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `ss_emails.last_i_brevladan` | inte gjord |
| SU-019 | Pilotflaggor Offert och Utbildning | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `ss_classifications.offertforfragan` | inte gjord |
| SU-020 | Se agentens klassning | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `ss_classifications` | inte gjord |
| SU-021 | Granska AI-utkastet | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `ss_drafts` | inte gjord |
| SU-022 | Godkänn och skicka svaret | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/drafts/{id}/approve` | inte gjord |
| SU-023 | Avvisa utkastet | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/drafts/{id}/reject` | inte gjord |
| SU-024 | Ta över ärendet manuellt | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/{id}/takeover` | inte gjord |
| SU-025 | Skriv om utkastet: Förbättra, Kortare, Mer personlig | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/drafts/{id}/omformulera` | inte gjord |
| SU-026 | Bocka av som hanterat / ohanterat | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/{id}/hanterad` | inte gjord |
| SU-027 | Flytta ett testmejl till skarpa ärenden | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/{id}/befordra` | inte gjord |
| SU-028 | Flytta tillbaka från Dolda till kundtjänst | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/{id}/klassa` | inte gjord |
| SU-029 | Omklassa ett mejl manuellt (lead, ej relaterat, support) | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/{id}/klassa` | inte gjord |
| SU-030 | Provsortera de synliga mejlen | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/sortera` | inte gjord |
| SU-031 | Tillämpa provsorteringen | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/sortera` | inte gjord |
| SU-032 | Sortera bort utskick ur den eskalerade kön | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/sortera` | inte gjord |
| SU-033 | Hämta testmail (sandlåda) | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/mock` | inte gjord |
| SU-034 | Uppdatera | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox` | inte gjord |
| SU-035 | Synka inkorg nu | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox/mailboxes` | inte gjord |
| SU-036 | Förlopp medan agenten arbetar i bakgrunden | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox` | inte gjord |
| SU-037 | Koppla inkorg-genväg | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `/settings/mailboxes` | inte gjord |
| SU-038 | Genväg till reglerna | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | behövs ingen (klient) | inte gjord |
| SU-039 | Beslutslogg per mejl | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `ss_decision_log` | inte gjord |
| SU-040 | Tomlägen | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | behövs ingen (klient) | inte gjord |
| SU-041 | Felrutor | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `offline` | inte gjord |
| SU-042 | Larm grupperas (Att hantera) | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `GET /api/inbox?status=att_hantera` | inte gjord |
| SU-043 | Kör om ett mejl som fastnat | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/{id}/processa-om` | inte gjord |
| SU-044 | Externa system postar mejl in (API-first) | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | finns: `POST /api/inbox/ingest` | inte gjord |
| SU-045 | Demoläge för inkorgen | `/crm/kundtjanst/arenden` (ny) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) + BolagPanel | 5 | behövs ingen (klient) | inte gjord |
| SU-050 | Nyckeltal: Inkomna ärenden | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/support/oversikt` | inte gjord |
| SU-051 | Nyckeltal: Utkast att godkänna | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `vantande.antal` | inte gjord |
| SU-052 | Nyckeltal: Besvarat av agenten | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `nu.auto / nu.inkomna` | inte gjord |
| SU-053 | Nyckeltal: Svarstid, median | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `nu.svarstid_median` | inte gjord |
| SU-054 | Ärenden per vecka (diagram) | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `veckor[]` | inte gjord |
| SU-055 | Fördelning: hur ärendena besvarades | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `nu.auto/godkant/manniska/vantar` | inte gjord |
| SU-056 | Fördelning per kategori | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `kategorier[]` | inte gjord |
| SU-057 | Utkast som väntar (lista) | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/inbox?status=awaiting_approval&limit=30` | inte gjord |
| SU-058 | Svarstidsfördelning | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `svarstider[]` | inte gjord |
| SU-059 | Senaste ärendena | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/inbox?limit=8` | inte gjord |
| SU-060 | Kunskapsbasens träffbild | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `nu.kb_traff` | inte gjord |
| SU-061 | Luckor att fylla | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `storage.list_agent_suggestions(status="ny")` | inte gjord |
| SU-062 | Till en människa, per kategori | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: `kategorier[].eskalerade` | inte gjord |
| SU-063 | Driftruta (körningar, kostnad, modell) | `/crm/kundtjanst` (ny) vyn Översikt, kort bara för plattformsadmin · OversiktVy | 5 | finns: `drift{korningar,tokens_in,tokens_out,cache,modell}` | inte gjord |
| SU-064 | Översiktens laddning och fel | `/crm/kundtjanst` (ny) vyn Översikt · OversiktVy | 5 | finns: tre parallella anrop | inte gjord |
| SU-070 | Skicka en fråga till supportagenten | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `POST /api/snajp-support/chat` | inte gjord |
| SU-071 | Vänta på svaret med synligt skede | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `GET /api/snajp-support/jobs/{id}?tenant=` | inte gjord |
| SU-072 | Kallstart: assistenten vaknar | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `offline` | inte gjord |
| SU-073 | Felmeddelanden skrivna för människor | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `app/api/chat.py:_process` | inte gjord |
| SU-074 | Bifoga en bild | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `attachments[]` | inte gjord |
| SU-075 | Startläge med förslag på frågor | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `lib/tenants.ts` | inte gjord |
| SU-076 | Huvudet: AI-upplysning och status | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | behövs ingen (klient) | inte gjord |
| SU-077 | Rena svarsbubblor utan intern bedömning | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `result.meta` | inte gjord |
| SU-078 | Sömlös överlämning till en människa | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `POST /api/snajp-support/chat/samtal` | inte gjord |
| SU-079 | Samtalet finns kvar efter omladdning | `SupportChat` delas; testchatten i `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `POST /api/chat/samtal` | inte gjord |
| SU-081 | Testchatt: tumme upp/ned på varje svar | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `POST /api/snajp-support/agent/feedback` | inte gjord |
| SU-082 | Testchatt: lägg ett dokument i kunskapsbasen från chatten | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `POST /api/snajp-support/kb/extrahera` | inte gjord |
| SU-083 | Testchatt: agentens förslag dyker upp i flödet | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `GET /api/snajp-support/agent/forslag?status=ny` | inte gjord |
| SU-084 | Testchatten räknas aldrig som kundtrafik | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `schemas.ChatRequest.is_test` | inte gjord |
| SU-080 | Chattmenyn: språk, kontakt, dataskydd, anmäl fel svar | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | behövs ingen (klient) | inte gjord |
| SU-085 | Backendens grindar före varje chattsvar | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `POST /api/chat` | inte gjord |
| SU-086 | Ärliga felbesked när modellen inte svarar | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `chat.py:_process` | inte gjord |
| SU-087 | Arbetsytans nyckeltal i testchatten | `/crm/kundtjanst/testchatt` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `app/api/snajp-support/testchatt/route.ts` | inte gjord |
| SU-088 | Den publika chattvägen är anonym men smal | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/api/snajp-support/chat/route.ts` | inte gjord |
| SU-090 | Det kunden klistrar in på sin sajt | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | finns: statisk fil | inte gjord |
| SU-091 | Chattknappen och panelen på kundens sida | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | behövs ingen (klient) | inte gjord |
| SU-092 | Inbjudningsbubbla | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | finns: `lib/tenants/<kund>.ts` | inte gjord |
| SU-093 | Vänligt fel om chatten inte laddar | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | behövs ingen (klient) | inte gjord |
| SU-094 | Widgetens innehåll i iframen | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | finns: `lib/tenants` | inte gjord |
| SU-095 | Vilka domäner som får visa widgeten (CSP per kund) | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | finns: `lib/tenants/<kund>.ts` | inte gjord |
| SU-096 | Widgetkonfigurationen bor i kod, per kund | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | behövs ingen (klient) | inte gjord |
| SU-097 | Publik chattsida med sessionslänk | Utanför `/crm`: widgeten, `/embed`, `/chat` behålls oförändrade | 5 | finns: `lib/tenants` | inte gjord |
| SU-100 | "Kör agent": öppna supportportalen inloggad | `/crm/kundtjanst` (ny) sidhuvudets ikonknapp Kör agent · Sida | 5 | finns: `GET /api/agentsajt/[agent]/sso` | inte gjord |
| SU-101 | Lista samtal som agenten lämnat över till en människa | `/crm/kundtjanst/overlamnade` (ny) och `/crm/installningar/kanaler` (i dag bara i `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `GET /api/chattar` | inte gjord |
| SU-102 | Läsa hela samtalet | `/crm/kundtjanst/overlamnade` (ny) och `/crm/installningar/kanaler` (i dag bara i `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `GET /api/chattar/{customer_id}` | inte gjord |
| SU-103 | Svara kunden som medarbetare | `/crm/kundtjanst/overlamnade` (ny) och `/crm/installningar/kanaler` (i dag bara i `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `POST /api/chattar/{customer_id}/svar` | inte gjord |
| SU-104 | Lämna tillbaka samtalet till agenten | `/crm/kundtjanst/overlamnade` (ny) och `/crm/installningar/kanaler` (i dag bara i `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `POST /api/chattar/{customer_id}/aterlamna` | inte gjord |
| SU-105 | Koppla kanaler: WhatsApp, Messenger, Slack, Teams | `/crm/installningar/kanaler` (ny) · BolagVy + BolagFormular | 5 | finns: `GET/POST /api/kanaler` | inte gjord |
| SU-106 | Ta emot meddelanden från kanalerna | `/crm/installningar/kanaler` (ny) · BolagVy + BolagFormular | 5 | finns: `GET/POST /api/kanaler/{kanal}/{tenant_id}/{anslutning_id}/webhook` | inte gjord |
| SU-107 | Koppla kundens egna system som agentverktyg (HTTP och MCP) | `/crm/installningar/integrationer` (ny) · BolagVy + BolagFormular | 5 | finns: `GET/POST /api/integrationer` | inte gjord |
| SU-108 | Portalens inställningar (läsvy) | Portalens sidor; motsvarigheten finns i `/crm/installningar` | 5 | finns: `GET /api/rules` | inte gjord |
| SU-109 | Portalens övriga sidor | Portalens sidor; motsvarigheten finns i `/crm/installningar` | 5 | finns: `/api/ag/*` | inte gjord |
| SU-110 | Medarbetarsvar och tidigare kundhistorik via API | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `GET /api/tickets/{id}` | inte gjord |
| SU-115 | Demons kundtjänst | Utanför `/crm`: demon och marknadssidorna behålls | 5 | finns: `lib/demo/support-inbox.ts` | inte gjord |
| SU-116 | Demons kundchatt med förladdade svar | Utanför `/crm`: demon och marknadssidorna behålls | 5 | finns: `lib/demo/support-chatt.ts` | inte gjord |
| SU-117 | Marknadssidans supportvisning | Utanför `/crm`: demon och marknadssidorna behålls | 5 | finns: `POST /api/snajp-support/triage` | inte gjord |
| SU-118 | Publik produktsida för support | Utanför `/crm`: demon och marknadssidorna behålls | 5 | behövs ingen (klient) | inte gjord |
| SU-119 | Oanvända supportkomponenter | Tas inte med (oanvänd kod) | 5 | finns: `GET /api/usage` | inte gjord |
| SU-120 | Se artiklarna i kunskapsbasen | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `GET /api/kb` | inte gjord |
| SU-121 | Ladda upp textfiler som artiklar | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `POST /api/kb` | inte gjord |
| SU-122 | Skriva eller klistra in en artikel | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `POST /api/kb` | inte gjord |
| SU-123 | Svar om vektorn saknas | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `POST /api/kb` | inte gjord |
| SU-124 | Ta bort en artikel | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `DELETE /api/kb/{artikel_id}` | inte gjord |
| SU-125 | Artikelns giltighetstid och platshållare | Ingen egen vy: under ytan, oförändrad backend; syns i kunskapsbasen | 5 | finns: `ss_knowledge_base.giltig_till` | inte gjord |
| SU-126 | Kunskapsbaskort på startsidan | `/crm` (befintlig) Översikt, kortet Kunskapsbas · OversiktVy | 5 | finns: `GET/POST /api/kb` | inte gjord |
| SU-127 | Läs in webbplatsen till förslag (start) | `/crm/installningar/kunskapsbas` (ny) · SynkVy + BolagVy | 5 | finns: `POST /api/kb/skanna` | inte gjord |
| SU-128 | Följa skanningen | `/crm/installningar/kunskapsbas` (ny) · SynkVy + BolagVy | 5 | finns: `GET /api/kb/forslag` | inte gjord |
| SU-129 | Granska förslagen från webbplatsen | `/crm/installningar/kunskapsbas` (ny) · SynkVy + BolagVy | 5 | finns: `ss_kb_forslag` | inte gjord |
| SU-130 | Lägga till eller avvisa förslag | `/crm/installningar/kunskapsbas` (ny) · SynkVy + BolagVy | 5 | finns: `POST /api/kb/forslag/beslut` | inte gjord |
| SU-131 | Extrahera text ur PDF | Ingen egen vy: under ytan, oförändrad backend; syns i kunskapsbasen | 5 | finns: `POST /api/kb/extrahera` | inte gjord |
| SU-132 | Kunskapsbasens luckor som förslag i lärloopen | Ingen egen vy: under ytan, oförändrad backend; syns i kunskapsbasen | 5 | finns: `GET /api/agent/forslag` | inte gjord |
| SU-133 | Exempelartiklar bara för testarbetsytor | Ingen egen vy: under ytan, oförändrad backend; syns i kunskapsbasen | 5 | finns: `scripts/seed_kb.ensure_tenant_kb` | inte gjord |
| SU-140 | Skriva agentens röstdokument (SOUL) | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `GET/PUT /api/snajp-support/leads/soul` | inte gjord |
| SU-141 | Autosvarsregler per fack | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `GET/PUT /api/rules` | inte gjord |
| SU-142 | Tonläge | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `GET/PUT /api/support/config` | inte gjord |
| SU-143 | Svarsspråk | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{sprak}` | inte gjord |
| SU-144 | Faktakontroll | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{faktakontroll}` | inte gjord |
| SU-145 | Misslyckade försök innan överlämning | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{eskalering:{max_misslyckade}}` | inte gjord |
| SU-146 | Lämna över vid missnöje | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{eskalering:{sentimentgrans}}` | inte gjord |
| SU-147 | Frågor utanför ämnesområdet | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{eskalering:{utanfor_amnet}}` | inte gjord |
| SU-148 | Räkna frustration som misslyckat försök | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{eskalering:{frustration_raknas}}` | inte gjord |
| SU-149 | Vad agenten ska hjälpa till med (ämnesområde) | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{amnesomrade}` | inte gjord |
| SU-150 | Inställningarnas laddning och fel | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| SU-151 | Era önskemål till supportagenten | `/crm/installningar/kundtjanst` (ny) avsnittet Önskemål · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `GET /api/agent/onskemal/support` | inte gjord |
| SU-152 | Globala agentinstruktioner (plattformen) | `/crm/installningar/plattformen` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `agentcore/instruktioner.las_agent_mall` | inte gjord |
| SU-153 | Överlämningsorsaker | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `agent/support_regler.ORSAKER` | inte gjord |
| SU-160 | Lista kopplade inkorgar | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `GET /api/inbox/mailboxes` | inte gjord |
| SU-161 | Koppla en inkorg, steg 1: adressen | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `GET /api/inbox/mailboxes/upptack?adress=` | inte gjord |
| SU-162 | Koppla en inkorg, steg 2: app-lösenord | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| SU-163 | Koppla en inkorg, steg 3: prova och spara | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `POST /api/inbox/mailboxes` | inte gjord |
| SU-164 | Koppla ur en inkorg | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `DELETE /api/inbox/mailboxes/{id}` | inte gjord |
| SU-165 | Automatisk hämtning av nya mejl | Ingen egen vy: under ytan, oförändrad backend; syns som ärenden | 5 | finns: `email_pipeline/poller.run_poller` | inte gjord |
| SU-166 | Inkommande mejls väg genom pipelinen | Ingen egen vy: under ytan, oförändrad backend; syns som ärenden | 5 | finns: `email_pipeline/processor.process_email` | inte gjord |
| SU-167 | Utgående svar | Ingen egen vy: under ytan, oförändrad backend; syns som ärenden | 5 | finns: `email_pipeline/sender.skicka_supportsvar` | inte gjord |
| SU-168 | Mejl som väntar på avtal eller budget | Ingen egen vy: under ytan, oförändrad backend; syns som ärenden | 5 | finns: `avtalsgrind.py` | inte gjord |
| SU-170 | Ett ärende per meddelande, samtalet per slutkund | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `agent/support_agent.py` | inte gjord |
| SU-171 | Agenten svarar i steg och loggar kedjan | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `support_agent.run_support_agent` | inte gjord |
| SU-172 | Påhopp och hot stoppas i kod | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `moderation/abuse_gate.py` | inte gjord |
| SU-173 | Personnummer maskeras på väg till modellen | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `moderation/maskering.py` | inte gjord |
| SU-174 | Bilder i chatten tolkas | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `agent/vision.describe_image` | inte gjord |
| SU-175 | Uppsägningsrisk upptäcks | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `agent/retention_classifier.py` | inte gjord |
| SU-176 | Kunskapsbas, faktagrind och svarscache | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `support_faktagrind.py` | inte gjord |
| SU-177 | Kundens egna system som verktyg | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `integrationer/uppslag.py` | inte gjord |
| SU-178 | Överlämning till människa i chatten | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `support_agent.py` | inte gjord |
| SU-179 | Mejl till Snajp när ett ärende eskaleras | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `notifications/prioriterat_mejl.skicka_prioriterat` | inte gjord |
| SU-180 | Ärende skapas i kundens eget ärendesystem vid eskalering | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `integrationer/handelser.py` | inte gjord |
| SU-181 | Kundens fakta sparas som kundminne | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `customer_memory` | inte gjord |
| SU-182 | Svar på frågor om arbetsytans egna siffror | Ingen egen vy: under ytan, oförändrad backend; syns i ärendet | 5 | finns: `agent/arbetsyta_siffror.py` | inte gjord |
| SU-190 | Kom igång-stegen för support | `/crm` (befintlig) Översikt, kortet Kom igång · OversiktVy | 5 | finns: `GET /api/kb/forslag` | inte gjord |
| SU-191 | Webbplatsskanningen startas av onboardingen | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `POST /api/kb/skanna` | inte gjord |
| SU-192 | Supportens backendtenant provisioneras | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| SU-193 | Publik produktsida | Utanför `/crm`: marknadssidorna behålls | 5 | behövs ingen (klient) | inte gjord |
| SU-200 | Läsrollen kan följa men inte ändra | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | finns: `/api/snajp-support/*` | inte gjord |
| SU-201 | Plattformsadmin som tittar som kund skriver bara test | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | finns: se läsarens rad | inte gjord |
| SU-202 | Proxyns felbeteende som kunden möter | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | behövs ingen (klient) | inte gjord |
| SU-203 | Anonym chatt för en kund som inte är färdigaktiverad | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | finns: `lib/tenants` | inte gjord |
| SU-204 | Tak och budget gäller alla supportvägar | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | finns: `api/rate_limit_db.py` | inte gjord |
| SU-205 | Autosvar på mejl: villkor och AI-upplysning | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | finns: `email_pipeline/processor.py` | inte gjord |
| SU-206 | Proxyn rör aldrig fel tenant | Ingen egen vy: under ytan, oförändrad backend; CRM-vyerna ärver proxyns grindar | 5 | behövs ingen (klient) | inte gjord |
| SU-207 | Portalens Inkorg | `/crm/kundtjanst/overlamnade` (ny) (i dag `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `GET /api/inbox?limit=100` | inte gjord |
| SU-208 | Portalens Översikt | `/crm/kundtjanst/overlamnade` (ny) (i dag `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `GET /api/inbox?limit=100` | inte gjord |
| SU-209 | Portalens Kunskapsbas | `/crm/kundtjanst/overlamnade` (ny) (i dag `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `POST /api/kb/skanna` | inte gjord |
| SU-210 | Portalens Testchatt | `/crm/kundtjanst/overlamnade` (ny) (i dag `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `POST /api/chat` | inte gjord |
| SU-211 | Medarbetaren kliver in i ett samtal som inte är överlämnat | `/crm/kundtjanst/overlamnade` (ny) (i dag `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | finns: `agent/overlamning.medarbetarsvar` | inte gjord |
| SU-212 | Kanalanslutningarnas regler | `/crm/installningar/kanaler` (ny) · BolagVy + BolagFormular | 5 | finns: `api/kanaler.py` | inte gjord |
| SU-213 | Kundens egna system: säkerhetsregler | `/crm/installningar/integrationer` (ny) · BolagVy + BolagFormular | 5 | finns: `api/integrationer.py` | inte gjord |
| SU-214 | Marknadssidans inkorgsdemo ("Sortera inkorgen") | Utanför `/crm`: marknadssidorna behålls | 5 | finns: `POST /api/snajp-support/triage` | inte gjord |
| SU-215 | Marknadssidans chatt | Utanför `/crm`: marknadssidorna behålls | 5 | finns: `/api/snajp-support/chat` | inte gjord |
| SU-216 | Önskemålens rendering | `/crm/installningar/kundtjanst` (ny) avsnittet Önskemål · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: se SU-151 | inte gjord |
| SU-217 | Kunskapsbasens valideringsgränser | `/crm/installningar/kunskapsbas` (ny) · BolagFormular (fältfel) | 5 | finns: `api/schemas.py` | inte gjord |
| SU-218 | "Kör agent"-biljettens innehåll och läsrollsspärr | `/crm/kundtjanst/overlamnade` (ny) (i dag `support-webb`) · NYTT MÖNSTER: tråd- och inkorgsvy (lista, tråd, svarsruta) | 5 | behövs ingen (klient) | inte gjord |
| SU-219 | Backendens fristående demochatt (oanvänd) | Tas inte med (oanvänd kod) | 5 | finns: `snajp-support/app/api/demo.py` | inte gjord |

### Kvitton (app-07, 141 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| KV-01 | Menyposten "Kvitton" visas bara för plattformsadmin. | `/crm/kvitton` (ny) grinden (vilande, bara plattformsadmin) · Sida | 5 | finns: `workspaces.products` | inte gjord |
| KV-02 | Den som skriver adressen `/dashboard/kvitton` själv skickas till översikten om hon inte är plattformsadmin. | `/crm/kvitton` (ny) grinden (vilande, bara plattformsadmin) · Sida | 5 | behövs ingen (klient) | inte gjord |
| KV-03 | Saknas produkten i arbetsytan visas en förklaring i stället för en 404. | `/crm/kvitton` (ny) grinden (vilande, bara plattformsadmin) · Sida | 5 | saknas | inte gjord |
| KV-04 | All trafik till kvittomotorn går genom en grindad proxy som döljer att ytan finns. | `/crm/kvitton` (ny) grinden (vilande, bara plattformsadmin) · Sida | 5 | finns: `app/api/snajp-support/kvitton/[[...path]]/route.ts` | inte gjord |
| KV-05 | Den gamla adressen `/bokforing` leder till Supports produktsida. | `/crm/kvitton` (ny) grinden (vilande, bara plattformsadmin) · Sida | 5 | behövs ingen (klient) | inte gjord |
| KV-10 | Kvittosidan har två flikar: Översikt och Kvitton. | `/crm/kvitton` (ny) · Sida + Vyrad (Översikt, Kvitton) | 5 | behövs ingen (klient) | inte gjord |
| KV-11 | Kvitton-fliken är tvåkolumnig: arbetet till vänster, sammanfattning och assistent till höger. | `/crm/kvitton` (ny) · Sida + Vyrad (Översikt, Kvitton) | 5 | behövs ingen (klient) | inte gjord |
| KV-12 | Ett hopfällt förbehåll säger att beloppen är förslag, inte bokföring. | `/crm/kvitton` (ny) · Sida + Vyrad (Översikt, Kvitton) | 5 | behövs ingen (klient) | inte gjord |
| KV-13 | Användaren kan felanmäla en avläsning med ett förifyllt mejl. | `/crm/kvitton` (ny) · BolagPanel (felanmälan) | 5 | finns: mejlklient | inte gjord |
| KV-20 | Användaren väljer en period med två datumfält. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | behövs ingen (klient) | inte gjord |
| KV-21 | Arbetsytan laddar mejlkonto, kvittolista och sammanfattning parallellt. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `/api/snajp-support/kvitton…` | inte gjord |
| KV-22 | Användaren ser vilken inkorg som är kopplad, eller hur man får en kopplad. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `GET /api/kvitton/mejlkonto` | inte gjord |
| KV-23 | Användaren startar en skanning av inkorgen. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `POST /api/kvitton/skanning` | inte gjord |
| KV-24 | Skanningens förlopp syns på knappen och följs till slut. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `GET /api/kvitton/skanning/{job_id}` | inte gjord |
| KV-25 | Efter skanningen spelas varje genomläst mejl upp i en inkorgsruta. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `handelser` | inte gjord |
| KV-26 | Användaren laddar upp ett eller flera kvitton som filer. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `POST /api/kvitton/underlag` | inte gjord |
| KV-27 | Användaren laddar upp en kundfaktura (intäkt) i stället för ett kvitto. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `POST /api/kvitton/underlag` | inte gjord |
| KV-28 | Misslyckade uppladdningar redovisas per fil. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | behövs ingen (klient) | inte gjord |
| KV-29 | Användaren exporterar periodens kvitton som CSV. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `GET /api/kvitton/export.csv` | inte gjord |
| KV-30 | Användaren rensar alla kvitton i perioden. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `DELETE /api/kvitton/period` | inte gjord |
| KV-31 | Kvitton som väntar på människan samlas i ett mörkt Att göra-kort ovanför tabellen. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | behövs ingen (klient) | inte gjord |
| KV-32 | Tabellen "Kvitton i perioden" listar alla underlag i perioden. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `GET /api/kvitton` | inte gjord |
| KV-33 | Statusmärket per kvitto visar det skarpaste skälet. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `kvitton.granskningsstatus` | inte gjord |
| KV-34 | Flaggor från granskningen visas som små etiketter. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | finns: `kvitton.flaggor` | inte gjord |
| KV-35 | Användaren godkänner ett flaggat kvitto och fyller i det som saknas. | `/crm/kvitton` (ny) · BolagPanel + BolagFormular | 5 | finns: `POST /api/kvitton/{id}/godkann` | inte gjord |
| KV-36 | Användaren byter ett underlag i granskning mellan kvitto (kostnad) och kundfaktura (intäkt). | `/crm/kvitton` (ny) · BolagPanel + BolagFormular | 5 | finns: `POST /api/kvitton/{id}/riktning` | inte gjord |
| KV-37 | Integritetsnotisen visas i sammanfattningsrutan. | `/crm/kvitton` (ny) vyn Kvitton · BolagVy + SynkVy (skanning) + NYTT MÖNSTER: uppladdning och import i steg (fil, kolumnkoppling, granskning, förlopp) | 5 | behövs ingen (klient) | inte gjord |
| KV-40 | Högerkolumnen sammanfattar innevarande månad. | `/crm/kvitton` (ny) vyn Kvitton, kort · OversiktVy (Nyckeltalskort) | 5 | finns: `GET /api/kvitton/sammanfattning` | inte gjord |
| KV-41 | Rutan visar totalsumma, antal och ingående moms. | `/crm/kvitton` (ny) vyn Kvitton, kort · OversiktVy (Nyckeltalskort) | 5 | behövs ingen (klient) | inte gjord |
| KV-42 | Fakturerat (intäkter) visas som egen rad när det finns. | `/crm/kvitton` (ny) vyn Kvitton, kort · OversiktVy (Nyckeltalskort) | 5 | finns: `sammanfattning.intakter` | inte gjord |
| KV-43 | Summor per kategori listas. | `/crm/kvitton` (ny) vyn Kvitton, kort · OversiktVy (Nyckeltalskort) | 5 | finns: `sammanfattning.per_kategori` | inte gjord |
| KV-44 | En fritextsammanfattning visas om backenden gett en. | `/crm/kvitton` (ny) vyn Kvitton, kort · OversiktVy (Nyckeltalskort) | 5 | behövs ingen (klient) | inte gjord |
| KV-45 | En integritetsnotis står synligt i rutan och i demon. | `/crm/kvitton` (ny) vyn Kvitton, kort · OversiktVy (Nyckeltalskort) | 5 | finns: `kvitto_agent.INTEGRITETSNOTIS` | inte gjord |
| KV-50 | Översikten visar kopplad inkorg och en genväg till skanningen. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | finns: `GET /api/kvitton` | inte gjord |
| KV-51 | Fyra nyckeltalskort sammanfattar de senaste fyra veckorna. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | finns: , sparkline per vecka, text "att betala in, senaste 4 veckorna" eller… | inte gjord |
| KV-52 | Ett stapeldiagram visar in och ut per vecka i tolv veckor. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-53 | Tre munkdiagram visar fördelningen de senaste fyra veckorna. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-54 | Rutan "Att granska" listar underlag som väntar, med godkännande direkt på raden. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | finns: `POST /api/kvitton/{id}/godkann` | inte gjord |
| KV-55 | Rutan "Moms per sats" ger underlag till momsdeklarationen. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-56 | "Senaste underlagen" listar de 15 senaste kvittona och fakturorna. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-57 | "Kunder och leverantörer" visar vart pengarna gick och varifrån de kom, med en kort text. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-58 | Avläsningsrutan visar för plattformsadmin hur väl agenten läser. | `/crm/kvitton` (ny) vyn Översikt, kort bara för plattformsadmin · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-59 | Fel vid hämtning syns som en rad, utan att sidan blir tom. | `/crm/kvitton` (ny) vyn Översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-59b | Översikten fungerar som demo utan backend. | Demon och `/forhandsvisning/crm/...` · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| KV-60 | Användaren ställer frågor om sina kvitton till en assistent. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `POST /api/kvitton/chat` | inte gjord |
| KV-61 | Tomläget föreslår tre frågor. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | behövs ingen (klient) | inte gjord |
| KV-62 | Medan svaret hämtas visas en rad med snurra. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | behövs ingen (klient) | inte gjord |
| KV-63 | Ett svar med en siffra som inte gått att härleda märks. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `app/bookkeeping/beloppsgrind.py` | inte gjord |
| KV-64 | Ett misslyckat anrop återställer frågan så att den kan skickas igen. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | behövs ingen (klient) | inte gjord |
| KV-70 | Systemet svarar vilken inkorg som är kopplad. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `GET /api/kvitton/mejlkonto` | inte gjord |
| KV-71 | Skanningen körs som bakgrundsjobb med förlopp. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/jobs/bakgrund.py` | inte gjord |
| KV-72 | En äldre synkron skanningsväg finns kvar. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `POST /api/kvitton/skanna` | inte gjord |
| KV-73 | Skanningens resultat bär allt vyn behöver i ett svar. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `skanna_inkorg` | inte gjord |
| KV-74 | Listan returnerar alla underlag i perioden utan tak. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-75 | Sammanfattningen räknar periodens summor. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `kvitton/sammanfattning.py:sammanstall` | inte gjord |
| KV-76 | Rensningen raderar periodens underlag på riktigt. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-77 | En uppladdad fil kontrolleras, läses av och kastas; bara fälten sparas. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-78 | Godkännandet låter människan komplettera och kör grinden igen. | `/crm/kvitton` (ny) · BolagPanel + BolagFormular | 5 | finns: `bk_underlag` | inte gjord |
| KV-79 | Byte mellan kvitto och kundfaktura går bara i granskningskön. | `/crm/kvitton` (ny) · BolagPanel + BolagFormular | 5 | finns: `bk_underlag` | inte gjord |
| KV-80 | CSV-exporten ger periodens underlag för Excel eller vidare import. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-81 | Assistenten svarar med grundade siffror. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `agent/kvitto_agent.py` | inte gjord |
| KV-82 | Kvot- och kreditfel ger ett tydligt besked om att kvittot inte sparades. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvotfel.py` | inte gjord |
| KV-90 | Kvittohanteraren läser en kopplad inkorg, aldrig skriver i den. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/mejl.py` | inte gjord |
| KV-91 | Kopplingen görs av Snajp åt kunden, inte i appen. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: miljövariabler | inte gjord |
| KV-92 | En inkorg kan aldrig hamna hos fel kund. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `mejl.py:valj_mejlkonto` | inte gjord |
| KV-93 | Demoinkorgen har påhittade men realistiska mejl. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `mejl.py:FEJKMEJL` | inte gjord |
| KV-94 | Mejlens HTML görs om till läsbar text och bilagor plockas ut. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `mejl.py` | inte gjord |
| KV-95 | Fel i kopplingen beskrivs för kunden. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `MejlkontofelError` | inte gjord |
| KV-96 | Skanningen läser upp till 50 mejl och visar en händelse per mejl. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/skanning.py` | inte gjord |
| KV-97 | Ett mejl som inte går att läsa stoppar inte de andra. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `skanning.py:_galler_hela_skanningen` | inte gjord |
| KV-98 | Mejlets innehåll sparas aldrig. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-99 | Dubbletter stoppas hårt på samma mejl och flaggas mjukt på samma innehåll. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `granskning.verifiera` | inte gjord |
| KV-100 | Varje meddelande (mejl eller uppladdad fil) läses av en agent utifrån en grundprompt. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/hanterare.py:hantera` | inte gjord |
| KV-101 | Agenten utreder själv i stället för att lämna över till människan. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `hanterare.py:VERKTYG` | inte gjord |
| KV-102 | Kärnfälten läses två gånger, oberoende. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `hanterare.py:_kontrollas` | inte gjord |
| KV-103 | Faller modellen läses kvittot maskinellt och går till granskning. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `hanterare.py:deterministiskt_resultat` | inte gjord |
| KV-104 | Ett meddelande klassas efter var underlaget finns. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `granskning.py` | inte gjord |
| KV-105 | Uppladdning som kundfaktura vinner över igenkänningen. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `hanterare.py` | inte gjord |
| KV-106 | Samma fil hos kunden flaggas som möjlig dubblett. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag.sha256` | inte gjord |
| KV-107 | Bara säkra kronbelopp hamnar i summorna. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `hanterare.py:spara` | inte gjord |
| KV-108 | Ett kvitto blir klart och får ett verifikatförslag bara om både granskningen och verifieringsgrinden säger ja. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-110 | Fälten som läses ur varje underlag. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag.granskning` | inte gjord |
| KV-111 | Varje belopp och nummer måste stå i texten. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-112 | Beloppen kontrollräknas med Decimal och ±1 kr tolerans. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-113 | Kontrollsiffror prövas. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `kvitton/kontrollsiffror.py` | inte gjord |
| KV-114 | Förfallodagar räknas mot dagens datum. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-115 | Moms, valuta och kreditfakturor kontrolleras. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-116 | Kundfaktura eller kostnad avgörs i kod. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: profilens orgnummer och företagsnamn | inte gjord |
| KV-117 | Ändrade betalningsuppgifter flaggas som möjligt bedrägeri. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-118 | Text riktad till en AI i ett kvitto följs aldrig och flaggas. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-119 | Granskningsstatus räknas ur flaggor och säkerhet. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag.granskningsstatus` | inte gjord |
| KV-119b | Dubblettnoteringen beskriver originalet i ord. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-120 | Varje avläsning utgår från en fast, kundlevererad grundprompt som kan bytas utan kodändring. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/systemprompt.py` | inte gjord |
| KV-121 | Kundföretagets profil hämtas automatiskt. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `tenants` | inte gjord |
| KV-122 | Mejlets innehåll behandlas som opålitlig data. | Ingen egen vy: under ytan, oförändrad backend | 5 | behövs ingen (klient) | inte gjord |
| KV-130 | En uträkning av summorna används av API, skanning och chatt. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/sammanfattning.py` | inte gjord |
| KV-131 | Kategorinycklarna har fasta svenska etiketter. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `KATEGORIETIKETTER` | inte gjord |
| KV-132 | Sammanfattningstexten byggs av kod, aldrig av en modell. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `summeringstext` | inte gjord |
| KV-133 | Utan språkmodell svarar assistenten med kod. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `svara_utan_modell` | inte gjord |
| KV-140 | Assistenten räknar aldrig själv; varje siffra hämtas med verktyg i samma tur. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `agent/kvitto_agent.py` | inte gjord |
| KV-141 | Beloppsgrinden fäller svar med tal som inte hämtats. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `bookkeeping/beloppsgrind.py` | inte gjord |
| KV-142 | Elak eller kränkande ton påverkar svarstonen. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `moderation/abuse_gate.py` | inte gjord |
| KV-143 | Assistentens fem verktyg läser bara kundens egna kvitton. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `agent/kvitto_chat_tools.py` | inte gjord |
| KV-144 | Förbehåll och integritetsnotis följer med API-svaren. | `/crm/kvitton` (ny) · NYTT MÖNSTER: chattvy med jobbpollning och skeden | 5 | finns: `kvitto_agent.py` | inte gjord |
| KV-150 | SIE4-export till kundens bokföringsprogram (Fortnox, Visma, Bokio m.fl.). | Ingen vy i dag; SIE4 och avstämning som åtgärd i `/crm/kvitton` bara med Antons ord | 5 | finns: `app/bookkeeping/sie4.py` | inte gjord |
| KV-151 | Periodrapport med grind. | Ingen vy i dag; SIE4 och avstämning som åtgärd i `/crm/kvitton` bara med Antons ord | 5 | finns: `period.py:berakna_period` | inte gjord |
| KV-152 | Avstämning av ett kontoutdrag mot periodens underlag. | Ingen vy i dag; SIE4 och avstämning som åtgärd i `/crm/kvitton` bara med Antons ord | 5 | finns: `app/bookkeeping/kontoutdrag.py` | inte gjord |
| KV-153 | Bokföringsassistenten (den äldre chatten) och dess uppladdning. | Ingen vy i dag; SIE4 och avstämning som åtgärd i `/crm/kvitton` bara med Antons ord | 5 | finns: `agent/bookkeeping_agent.py` | inte gjord |
| KV-160 | Kategorierna motsvarar fasta BAS-konton. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/bookkeeping/kontoplan.py` | inte gjord |
| KV-161 | Verifikatet balanserar av konstruktion. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `kontoplan.py` | inte gjord |
| KV-162 | Verifieringsgrinden kräver de fält beräkningen behöver. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bookkeeping/verifieringsgrind.py` | inte gjord |
| KV-163 | Filer som tas emot är begränsade i typ och storlek. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bookkeeping/underlag.py` | inte gjord |
| KV-170 | Att göra-kön visar kvitton att granska bredvid de andra agenternas köer. | `/crm/att-gora` (ny) gruppen Kvitton · NYTT MÖNSTER: kö med grupper och åtgärd direkt i raden | 5 | finns: `GET /api/kvitton?fran=<idag−365>&till=<idag>` | inte gjord |
| KV-171 | Plattformsadmin slår på kvittotillägget per kund. | `/crm/admin/paket` (ny) · BolagFormular | 5 | finns: `workspaces.products` | inte gjord |
| KV-172 | Plattformsadmin ser kvittoagentens körningar i agentanvändningen. | `/crm/admin/logg` (ny) vyn Kostnad · OversiktVy | 5 | finns: `agent_runs` | inte gjord |
| KV-173 | En interaktiv demo visar skanningen utan backend. | Demon; kvitton är vilande, så demon leder till översikten | 5 | behövs ingen (klient) | inte gjord |
| KV-174 | Den publika produktsidan är nedlagd. | Tas inte med (nedlagd) | 5 | behövs ingen (klient) | inte gjord |
| KV-175 | Lokal utvecklingsbackend för kvitton i minnesläge. | Utvecklingsverktyg, ingen vy | 5 | finns: MemoryStorage | inte gjord |
| KV-180 | Kvitton lagras som underlag med avlästa fält, aldrig filen. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-181 | Verifikat lagras per klart kvitto. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_verifikat` | inte gjord |
| KV-182 | Lästa mejl utan underlag minns så att de inte läses om. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `kvitto_mejl_lasta` | inte gjord |
| KV-183 | Kvittodata gallras inte automatiskt. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `…_119_gallring_alla_kategorier.sql` | inte gjord |
| KV-190 | Den gamla arbetsyteadressen leder till Kvitton. | `/crm/kvitton` (ny) (adressen leder hit) | 5 | behövs ingen (klient) | inte gjord |
| KV-191 | Underlag utan datum syns i varje period och rensas av varje periodrensning. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag.datum` | inte gjord |
| KV-192 | Skanningen hämtar de senaste mejlen, inte periodens. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/mejl.py:hamta_mejl` | inte gjord |
| KV-193 | Bakgrundsjobbet har livslängd och tidsgräns. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/jobs/bakgrund.py` | inte gjord |
| KV-194 | Systemet avgör vilka mejl som ens är kvittokandidater, utan modell. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/tolkning.py:ar_kvittokandidat` | inte gjord |
| KV-195 | Den maskinella läsaren (utan modell eller när modellen faller) utelämnar hellre än gissar. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `tolkning.py:tolka_deterministiskt` | inte gjord |
| KV-196 | Kronbelopp i utländsk valuta räknas aldrig om, inte heller när modellen läst. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `tolkning.py:valutaspärr` | inte gjord |
| KV-197 | Kontrollsiffrorna prövas med fasta regler. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/kvitton/kontrollsiffror.py` | inte gjord |
| KV-198 | Efter "Rensa" läses mejl som gav kvitton om vid nästa skanning, men inte mejl som saknade underlag. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `bk_underlag` | inte gjord |
| KV-199 | En fälld bokföringsperiod larmar Snajp via mejl. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/bookkeeping/period.py` | inte gjord |
| KV-200 | SIE4-filen har fast innehåll. | Ingen vy i dag; SIE4 och avstämning som åtgärd i `/crm/kvitton` bara med Antons ord | 5 | finns: `app/bookkeeping/sie4.py` | inte gjord |
| KV-201 | Avstämningen mot kontoutdrag läser bankens CSV. | Ingen vy i dag; SIE4 och avstämning som åtgärd i `/crm/kvitton` bara med Antons ord | 5 | finns: `app/bookkeeping/kontoutdrag.py` | inte gjord |
| KV-202 | Assistenterna slår upp Snajps egen kunskapstext. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/bookkeeping/kunskap.py` | inte gjord |
| KV-203 | Beloppsgrindens räckvidd är känd och begränsad. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `app/bookkeeping/beloppsgrind.py` | inte gjord |
| KV-204 | Kvittotillägget följer bara med ett paket som har Support. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `workspaces.products` | inte gjord |
| KV-205 | Demons data är fasta. | Demon; kvitton är vilande, så demon leder till översikten | 5 | finns: `lib/demo/kvitton.ts` | inte gjord |
| KV-206 | Snajp fångar kundens samtycke till inkorgen med ett lokalt skript. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `KVITTO_OAUTH_*` | inte gjord |
| KV-207 | Databasen spärrar ogiltiga värden och skiljer kunderna åt. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: migrationer 045, 062, 096 | inte gjord |
| KV-208 | Kvot- eller kreditslut under en bakgrundsskanning. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `api/kvitton.py:_skanna` | inte gjord |

### Inställningar (app-08, 109 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| IN-001 | Användaren når alla inställningar på en adress, `/settings/<sektion>`. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-002 | Plattformsadmin ser exakt samma sidor inne i adminskalet. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-003 | Inställningarna kräver inloggning och avslutad onboarding. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | finns: `resolveDashboardState` | inte gjord |
| IN-004 | Medan en sektion laddas visas arbetsytans laddningsläge; ett fel stannar i vyn. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-005 | Inställningarna är grupperade efter vilken fråga de svarar på, i en vänsterkolumn. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-006 | Menyn visar bara poster för produkter arbetsytan har OCH som läget visar just nu. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-007 | Servern vägrar en sektion arbetsytan inte har produkten för, oavsett meny. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-008 | Plattformens sektioner syns och öppnas bara för plattformsadmin. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | finns: `platform_admins` | inte gjord |
| IN-009 | Team döljs i demovyn och i kundläge. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-010 | Varje sektion har en titel och vid behov en kort beskrivning under. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-011 | Användaren loggar ut från inställningarnas vänsterkolumn. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| IN-012 | Företaget: användaren ser arbetsytans namn, paket och en länk till bolagsuppgifterna. | `/crm/installningar/foretaget` (ny) · BolagFormular | 5 | finns: DashboardContext (workspaces) | inte gjord |
| IN-013 | Temat läses på servern så att växeln stämmer från första bilden. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-014 | Ett konto med läsroll kan se allt men inte spara. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | finns: `profiles.role` | inte gjord |
| IN-015 | Allt inställningarna skickar till backenden går genom en inloggad proxy som sätter kundens nyckel ur sessionen. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | finns: Proxy → backend med X-API-Key | inte gjord |
| IN-016 | En arbetsyta som inte är klar eller inte är kopplad till backenden får ett begripligt fel i varje sektion som läser backenden. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-017 | När plattformsadmin tittar som en kund märks allt som skrivs som test. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | finns: `is_test` | inte gjord |
| IN-018 | Plattformens menyposter leder alltid in i adminskalet. | `/crm/installningar` (ny) · NYTT MÖNSTER: inställningsskal med grupperad undermeny + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-020 | Användaren beskriver vad bolaget säljer, i fyra fritextfält, som båda agenterna läser. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: `hamtaAffarskontext` | inte gjord |
| IN-021 | Medan texten hämtas visas fyra pulserande block; hämtningsfel ger tomma fält och en felrad. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: `business_contexts` | inte gjord |
| IN-022 | Användaren sparar affärskontexten med en knapp. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: `business_contexts` | inte gjord |
| IN-023 | Texten skickas vidare till agenterna som kontextdokument; går det inte blir det en varning, inte ett fel. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: `agent_context_docs` | inte gjord |
| IN-024 | I demovyn och vid kundbesök läses och skrivs affärskontexten bara mot den besökta tenantens kontextdokument. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: Backend /api/leads/context-docs | inte gjord |
| IN-025 | Utkastkedjan använder samma affärskontext; saknas den får användaren veta var den fylls i. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| IN-026 | Den sparade affärskontexten blir också agentens produktunderlag. | `/crm/installningar/vad-ni-saljer` (ny) · BolagFormular | 5 | finns: `agent_context_docs` | inte gjord |
| IN-030 | Användaren ser alla dokument i kunskapsbasen. | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + SynkVy | 5 | finns: `ss_knowledge_base` | inte gjord |
| IN-031 | Användaren laddar upp textfiler som blir artiklar. | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + SynkVy | 5 | finns: `{articles:[{title,content}]}` | inte gjord |
| IN-032 | Användaren skriver eller klistrar in en artikel för hand. | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + SynkVy | 5 | finns: se läsarens rad | inte gjord |
| IN-033 | Startsidan har ett genvägskort till affärskontext och kunskapsbas. | `/crm` (befintlig) Översikt, kortet Kunskapsbas · OversiktVy | 5 | finns: se läsarens rad | inte gjord |
| IN-034 | Användaren startar en inläsning av den egna webbplatsen som ger förslag till kunskapsbasen. | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + SynkVy | 5 | finns: `{webbplats, spara:true, startad_av:"kund"}` | inte gjord |
| IN-035 | Webbplatsen valideras innan något läses. | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + SynkVy | 5 | finns: `skanna_webbplats` | inte gjord |
| IN-036 | Användaren följer skanningens förlopp på sidan, även efter omladdning. | `/crm/installningar/kunskapsbas` (ny) · SynkVy | 5 | finns: `skanning` | inte gjord |
| IN-037 | Användaren lägger till eller avvisar förslag, ett och ett eller alla. | `/crm/installningar/kunskapsbas` (ny) · BolagVy + BolagFormular + SynkVy | 5 | finns: `{ids, beslut:"lagg_till"\|"avvisa"}` | inte gjord |
| IN-040 | Användaren skriver ett röstdokument som styr tonen i utskick och svar för båda agenterna. | `/crm/installningar/rost` (ny) · BolagFormular | 5 | finns: `/api/leads/soul` | inte gjord |
| IN-041 | En teckenräknare visar längden mot taket 4000 tecken. | `/crm/installningar/rost` (ny) · BolagFormular | 5 | finns: Backend SOUL_MAX_CHARS = 4000 | inte gjord |
| IN-042 | Röstdokumentet kan bara skrivas av kunden, aldrig av en agent. | `/crm/installningar/rost` (ny) · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-050 | Användaren väljer per fack om kundtjänstagenten skickar själv, gör utkast eller alltid eskalerar. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `{category, mode}` | inte gjord |
| IN-051 | Inkorgen länkar hit för reglerna, och samma komponent kan köras i demoläge mot en lokal låtsas-API. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-052 | Användaren väljer tonläge för kundtjänstagenten. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `/api/support/config` | inte gjord |
| IN-053 | Användaren väljer svarsspråk. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| IN-054 | Användaren väljer hur strängt agentens svar kontrolleras mot kunskapsbasen. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| IN-055 | Användaren sätter hur många misslyckade försök som får gå innan en människa tar över. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `settings.eskalering.max_misslyckade` | inte gjord |
| IN-056 | Användaren sätter missnöjesgränsen för överlämning. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `settings.eskalering.sentimentgrans` | inte gjord |
| IN-057 | Användaren väljer vad som händer med frågor utanför ämnesområdet. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `settings.eskalering.utanfor_amnet` | inte gjord |
| IN-058 | Användaren slår av eller på att frustration räknas som ett misslyckat försök. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `settings.eskalering.frustration_raknas` | inte gjord |
| IN-059 | Användaren beskriver vad agenten ska hjälpa till med. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | finns: `settings.amnesomrade` | inte gjord |
| IN-060 | Om inställningarna inte går att hämta får användaren ett fel och en knapp för att försöka igen. | `/crm/installningar/kundtjanst` (ny) · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-061 | Användaren skriver önskemål till sin agent med egna ord och förhandsgranskar ändringarna innan de sparas. | `/crm/installningar/kundtjanst` (ny) avsnittet Önskemål · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `leadsAnrop` | inte gjord |
| IN-062 | Användaren godkänner och sparar den förhandsgranskade versionen. | `/crm/installningar/kundtjanst` (ny) avsnittet Önskemål · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `{feedback, dokument}` | inte gjord |
| IN-063 | Användaren ser tidigare versioner och kan återställa en. | `/crm/installningar/kundtjanst` (ny) avsnittet Önskemål · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: POST /api/snajp-support/agent/onskemal/{agent}/aterstall/{id}; GET …/o… | inte gjord |
| IN-070 | Användaren ser vilka inkorgar som är kopplade och om de går att synka. | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `ss_mailboxes` | inte gjord |
| IN-071 | Tomläge när ingen inkorg är kopplad. | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| IN-072 | Steg 1: användaren anger adressen dit kundmailen kommer och vad brevlådan ska användas till. | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: GET /api/snajp-support/inbox/mailboxes/upptack?adress= → backend (fri… | inte gjord |
| IN-073 | Steg 2: användaren får leverantörsspecifik vägledning för att skapa ett app-lösenord. | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | behövs ingen (klient) | inte gjord |
| IN-074 | Steg 3: användaren klistrar in app-lösenordet och kopplar inkorgen; inloggningen provas innan något sparas. | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `{address, app_losenord, syfte, imap_host?}` | inte gjord |
| IN-075 | Direkt efter kopplingen hämtas olästa mejl, och användaren får veta utfallet. | `/crm/installningar/inkorgar` (ny) · SynkVy | 5 | finns: `/api/inbox/sync` | inte gjord |
| IN-076 | Användaren kopplar ur en inkorg. | `/crm/installningar/inkorgar` (ny) · BolagVy + BolagFormular + NYTT MÖNSTER: stegguide (onboarding, koppla inkorg) | 5 | finns: `ss_mailboxes` | inte gjord |
| IN-100 | Sidan samlar alla Iris-inställningar på en plats; i demon visas bara profil och målgrupp. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: /api/snajp-support/leads/config | inte gjord |
| IN-101 | Användaren styr när Iris lämnar över till en människa i stället för att hantera vidare själv. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `{eskalering:{…}}` | inte gjord |
| IN-102 | Användaren sätter träffsäkerhetströskeln för osäker kvalificering. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `settings.eskalering.kvalificeringstroskel` | inte gjord |
| IN-103 | Användaren listar sina egna produkter så att Iris kan välja den som passar varje bolag. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `{produkter:[{namn,nytta}]}` | inte gjord |
| IN-104 | Användaren rangordnar målsegment, bäst först. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `settings.segment` | inte gjord |
| IN-105 | Användaren anger om bolaget säljer till offentlig sektor och skolor. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `settings.offentlig_sektor` | inte gjord |
| IN-106 | Borttagna rader går att ångra, och allt sparas med en knapp. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | behövs ingen (klient) | inte gjord |
| IN-107 | Användaren hänvisas till Leads › Erbjudanden för erbjudanden och kampanjer. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | behövs ingen (klient) | inte gjord |
| IN-108 | Användaren skriver önskemål till Iris med förhandsgranskning, godkännande och versionshistorik. | `/crm/installningar/iris` (ny) avsnittet Önskemål · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 4 | finns: /api/snajp-support/agent/onskemal/leads… | inte gjord |
| IN-109 | CRM-synkens val hänvisar till "Inställningar › Integrationer", men den sidan finns inte. | `/crm/synk` (befintlig) · SynkVy | 3 | finns i backend; inställningssidan saknas | inte gjord |
| IN-110 | (Bara backend och skript) Iris mejlsignatur. | `/crm/installningar/iris` (ny) avsnittet Utskick · BolagFormular | 4 | finns: `{signatur}` | inte gjord |
| IN-111 | (Bara backend) Webbplatskravet och behovskravet per kund. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `agent_configs.settings` | inte gjord |
| IN-112 | Iris-konfigen sparas fältvis och vägrar automatiskt utskick tills underlaget finns. | `/crm/installningar/iris` (ny) · BolagFormular | 4 | finns: `agent_configs` | inte gjord |
| IN-160 | Kunden listar sina integrationer. | `/crm/installningar/integrationer` (ny) (yta saknas i dag) · BolagVy + BolagFormular | 5 | finns: `ss_integrations` | inte gjord |
| IN-161 | Kunden lägger till en integration av typen HTTP eller MCP. | `/crm/installningar/integrationer` (ny) (yta saknas i dag) · BolagVy + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-162 | Kunden ändrar en integration, eller byter enstaka hemligheter. | `/crm/installningar/integrationer` (ny) (yta saknas i dag) · BolagVy + BolagFormular | 5 | finns: PATCH /api/integrationer/{id} | inte gjord |
| IN-163 | Kunden tar bort en integration. | `/crm/installningar/integrationer` (ny) (yta saknas i dag) · BolagVy + BolagFormular | 5 | finns: DELETE /api/integrationer/{id} | inte gjord |
| IN-164 | Kunden ser vilka verktyg agenten får av en integration. | `/crm/installningar/integrationer` (ny) (yta saknas i dag) · BolagVy + BolagFormular | 5 | finns: GET /api/integrationer/{id}/verktyg | inte gjord |
| IN-165 | Kunden provkör en förfrågan eller ett MCP-verktyg på riktigt. | `/crm/installningar/integrationer` (ny) (yta saknas i dag) · BolagVy + BolagFormular | 5 | finns: POST /api/integrationer/{id}/prova | inte gjord |
| IN-166 | Agenten använder integrationerna under ett ärende. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: app/integrationer/* | inte gjord |
| IN-080 | Användaren ser alla som har åtkomst till arbetsytan, medlemmar och väntande inbjudningar i samma lista. | `/crm/installningar/team` (ny) · BolagVy + BolagFormular | 5 | finns: `listTeam` | inte gjord |
| IN-081 | Ägaren bjuder in en ny person med e-post och roll. | `/crm/installningar/team` (ny) · BolagVy + BolagFormular | 5 | finns: `inviteMember` | inte gjord |
| IN-082 | Ägaren tar bort en väntande inbjudan. | `/crm/installningar/team` (ny) · BolagVy + BolagFormular | 5 | finns: `revokeInvite` | inte gjord |
| IN-083 | (Saknas i dag) Byta roll på en befintlig medlem eller ta bort en medlem. | `/crm/installningar/team` (ny) · BolagVy + BolagFormular | 5 | saknas: ändpunkt för rollbyte och borttagning av medlem | inte gjord |
| IN-090 | Användaren ser vilket paket arbetsytan har och vad det kostar. | `/crm/installningar/plan` (ny) · OversiktVy (kort) + BolagVy | 5 | finns: `products` | inte gjord |
| IN-091 | Användaren ser vad som ingår i paketet och vilka tillägg som är aktiva. | `/crm/installningar/plan` (ny) · OversiktVy (kort) + BolagVy | 5 | finns: `workspaces.addons` | inte gjord |
| IN-092 | Användaren ber om paketbyte eller ändrade fakturauppgifter via mejl. | `/crm/installningar/plan` (ny) · OversiktVy (kort) + BolagVy | 5 | finns: mailto | inte gjord |
| IN-093 | Användaren ser alla tilläggstjänster, med vilka som ingår och vilka som är tillval. | `/crm/installningar/plan` (ny) · OversiktVy (kort) + BolagVy | 5 | finns: `workspaces.addons` | inte gjord |
| IN-094 | Plattformsadmin slår på och av tillägg per kund (från adminytan, inte från kundens inställningar). | `/crm/admin/paket` (ny) · BolagFormular | 5 | finns: `admin_workspace_addons` | inte gjord |
| IN-095 | Plattformsadmin byter paket för en kund (adminytan). | `/crm/admin/paket` (ny) · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-120 | Användaren väljer om hen vill få mejlnotiser, och om vad. Valet gäller bara den inloggade personen. | `/crm/installningar/notiser` (ny) och `/tema` · BolagFormular | 5 | finns: `hamtaNotiser` | inte gjord |
| IN-121 | Användaren sparar notisvalen med en knapp. | `/crm/installningar/notiser` (ny) och `/tema` · BolagFormular | 5 | finns: `sparaNotiser` | inte gjord |
| IN-122 | Onboardingen frågar om notiser och skriver samma rad. | `/crm/installningar/notiser` (ny) och `/tema` · BolagFormular | 5 | finns: `notification_preferences` | inte gjord |
| IN-123 | Användaren växlar mellan ljust och mörkt läge. | `/crm/installningar/notiser` (ny) och `/tema` · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-124 | En provbit visar hur ytorna ser ut i valt tema. | `/crm/installningar/notiser` (ny) och `/tema` · BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| IN-125 | (Saknas i inställningarna) Byte av språk. | `CrmRam` (befintlig): arbetsyteväxlarens meny (språk) · CrmRam | 4 | behövs ingen (språket i webbläsaren) | inte gjord |
| IN-130 | Plattformsadmin ser om tvåstegsverifiering är på för det egna kontot. | `/crm/installningar/plattformen/tvasteg` (ny) · BolagFormular | 5 | finns: `hamtaTvafaktorStatus` | inte gjord |
| IN-131 | Plattformsadmin slår på tvåstegsverifiering efter att ha angett lösenordet igen. | `/crm/installningar/plattformen/tvasteg` (ny) · BolagFormular | 5 | finns: `paborjaInrullning` | inte gjord |
| IN-132 | Plattformsadmin skannar en QR-kod och bekräftar med en kod ur appen. | `/crm/installningar/plattformen/tvasteg` (ny) · BolagFormular | 5 | finns: `bekraftaInrullning` | inte gjord |
| IN-133 | Efter aktiveringen visas tio återställningskoder en enda gång. | `/crm/installningar/plattformen/tvasteg` (ny) · BolagFormular | 5 | finns: `ANTAL_ATERSTALLNINGSKODER = 10` | inte gjord |
| IN-134 | Plattformsadmin stänger av tvåstegsverifieringen med en giltig kod. | `/crm/installningar/plattformen/tvasteg` (ny) · BolagFormular | 5 | finns: `avaktiveraMedKod` | inte gjord |
| IN-135 | Plattformsadmin redigerar de globala agentinstruktionerna som alla agenter läser först, för varje kund. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `/api/admin/instruktioner?agent=` | inte gjord |
| IN-136 | Plattformsadmin skriver feedback, förhandsgranskar ändringarna och sparar. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `forhandsgranskaInstruktioner` | inte gjord |
| IN-137 | Plattformsadmin ser historiken och återställer en tidigare version. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: POST /api/admin/instruktioner/{id}/aterstall | inte gjord |
| IN-138 | (Adminytan, inte inställningarna) Plattformsadmin redigerar en kunds profil: instruktioner, ton, SOUL och affärskontext. | `/crm/admin/kunder/[id]` (ny) · BolagFormular | 5 | finns: GET/PUT /api/admin/tenants/{id}/profil | inte gjord |
| IN-140 | Integrationer (Fortnox, HubSpot, Pipedrive, kalender m.fl.) | `/crm/synk` (befintlig) anslutningar · SynkVy + BolagFormular | 3 | delvis: CRM-API:ts anslutningar finns, adaptrar mot källsystemen saknas | inte gjord |
| IN-141 | API-nycklar | `/crm/utvecklare` (befintlig) · BolagVy + BolagFormular | 3 | finns för CRM-API:t (`/api/crm-nycklar`) | inte gjord |
| IN-142 | Avtal och biträdesavtal (avtalsgrinden) | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter · BolagFormular | 5 | finns (avtalsgrinden i kundregistret) | inte gjord |
| IN-143 | GDPR-verktyg (radera, exportera) | `/crm/installningar/dataskydd` (ny) · BolagFormular + SynkVy | 5 | saknas som ändpunkt (bara `scripts/gdpr_radera.py`) | inte gjord |
| IN-144 | Avsändare, signatur, schema, spärrlistor för leads | `/crm/installningar/iris` (ny) avsnittet Utskick · BolagFormular + BolagVy | 4 | delvis (signatur i Iris-konfigen); avsändare, schema och spärrlista saknar ändpunkt för kunden | inte gjord |
| IN-145 | Kvittoinställningar | `/crm/installningar/kvitton` (ny) · BolagFormular | 5 | saknas | inte gjord |
| IN-146 | Ändra bolagsuppgifter, byta språk, radera kontot, säga upp | `/crm/installningar/foretaget` (ny) · BolagFormular | 5 | saknas | inte gjord |

### Adminytan (app-09, 116 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| AD-001 | Adminytan finns bara för plattformsadmin. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | finns: `lib/auth/admin.ts` | inte gjord |
| AD-002 | Admin är en superset av kundens arbetsyta: plattformsposterna överst, kundens arbetsyta under. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | behövs ingen (klient) | inte gjord |
| AD-003 | Kundens vyer nås med `/admin`-prefix så att admin aldrig lämnar sitt skal. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | finns: se läsarens rad | inte gjord |
| AD-004 | Adminrutter som bara admin ser i kundens nav (adminOnly) och vilande produkter. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | behövs ingen (klient) | inte gjord |
| AD-005 | Olästa leadsnotiser räknas på Leads-posten i adminrailen. | `CrmRam` (befintlig): räknare på menyposten · NYTT MÖNSTER: notislista från sidhuvudet med olästräknare | 4 | finns: `lib/leads/konversationer` | inte gjord |
| AD-006 | Railens fot: kundväxel, vyväxel, kontaktmeny, inloggad adress, utloggning och språkval. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | finns: `lib/actions/auth.ts:signOut` | inte gjord |
| AD-007 | Vyväxeln Admin/Demo. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | behövs ingen (klient) | inte gjord |
| AD-008 | Kundbesök: öppna en namngiven kunds arbetsyta i läsläge/testläge. | `CrmRam` (befintlig): arbetsyteväxlaren Byt kund och banderollen · CrmRam + NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | finns: `log_admin_impersonation` | inte gjord |
| AD-009 | Gul banner under hela kundbesöket. | `CrmRam` (befintlig): arbetsyteväxlaren Byt kund och banderollen · CrmRam + NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | behövs ingen (klient) | inte gjord |
| AD-010 | "Byt kund": sökbar kundväxel. | `CrmRam` (befintlig): arbetsyteväxlaren Byt kund och banderollen · CrmRam + NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | finns: `app/api/admin/kunder/route.ts` | inte gjord |
| AD-011 | "Öppna" på en kundrad: samma kundbesök som Byt kund. | `CrmRam` (befintlig): arbetsyteväxlaren Byt kund och banderollen · CrmRam + NYTT MÖNSTER: banderoll överst i bladet (kundbesök, läsroll, demo) | 4 | finns: se läsarens rad | inte gjord |
| AD-012 | Fel och laddning stannar i vyn. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | behövs ingen (klient) | inte gjord |
| AD-013 | Adminens läsproxy mot backenden. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `/api/admin/*` | inte gjord |
| AD-014 | Mejlvägsdiagnos (ingen yta). | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `snajp-support/app/api/admin.py` | inte gjord |
| AD-015 | Leadsunderlag per kund (ingen yta, för skript). | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `admin.py` | inte gjord |
| AD-017 | Vilket skal admin hamnar i beroende på läget. | `CrmRam` (befintlig): sidofältets grupp Plattform, arbetsyteväxlaren med Byt kund och Admin/Demo · CrmRam + Kommandopalett | 5 | behövs ingen (klient) | inte gjord |
| AD-018 | Varje master-anrop bär adminens identitet. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `audit_logs` | inte gjord |
| AD-016 | Kundens inkorg och utkastkö läsbara för admin (ingen egen yta). | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `admin.py` | inte gjord |
| AD-020 | Hela kundportföljen på en sida, i ordningen "vad admin ska göra". | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | finns: `GET /api/admin/tenants` | inte gjord |
| AD-021 | Nyckeltal: månadsintäkt, uppskattad tokenkostnad, marginal, kräver åtgärd. | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | finns: `lib/admin/halsa.ts` | inte gjord |
| AD-022 | Hälsobedömning per kund. | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| AD-023 | Diagramrad: kundernas hälsa, intäkt per paket, marginal. | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| AD-024 | "Kräver åtgärd": tabell med bara de kunder som har dålig marginal eller är tysta. | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| AD-025 | Topplistor "Störst tokenkostnad" och "Mest aktivitet". | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| AD-026 | Rådgivaren "Fråga om siffrorna": en regelbaserad frågeruta över samma rader. | `/crm/admin` (ny) · NYTT MÖNSTER: frågeruta med regelbaserat svar | 5 | behövs ingen (räknas i klienten) | inte gjord |
| AD-027 | Exempeldata på tomma rader så att vyn går att bedöma. | `/crm/admin` (ny) Admin-översikt · OversiktVy | 5 | behövs ingen (klient) | inte gjord |
| AD-030 | Objektet Kunder med vyflikarna "Alla kunder" och "Paket och avtal". | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | finns: `GET /api/admin/tenants` | inte gjord |
| AD-031 | Nyckeltal för kundbasen. | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | finns: `lib/admin/statistik.ts:beraknaKundstatistik` | inte gjord |
| AD-032 | Kurva "Nya kunder och signerade avtal" per vecka, 12 veckor. | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | behövs ingen (klient) | inte gjord |
| AD-033 | Fördelning: kontoläge, avtal/provperiod och paket. | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | finns: `ss_tenants.status` | inte gjord |
| AD-034 | Tabellen Alla kunder. | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | behövs ingen (klient) | inte gjord |
| AD-035 | Provperiodens status per kund. | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | finns: `workspaces.trial_slut` | inte gjord |
| AD-036 | Panelen Provperioder. | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | behövs ingen (klient) | inte gjord |
| AD-037 | Panelen Fel och eskaleringar (senaste 7 dagarna). | `/crm/admin/kunder` (ny) · BolagVy + OversiktVy (kort) | 5 | finns: `GET /api/admin/events` | inte gjord |
| AD-040 | Kundsidans huvud och vyflikar. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| AD-041 | Välj vilken agents profil som visas: Kundtjänst eller Leads. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `GET /api/admin/tenants/{id}/profil?agent_type=` | inte gjord |
| AD-042 | Profilens faktarad. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `admin_profil.py:hamta_profil` | inte gjord |
| AD-043 | Skriv kundspecifika instruktioner (regler i systemposition). | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `PUT /api/admin/tenants/{id}/profil` | inte gjord |
| AD-044 | Sätt tonläge. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| AD-045 | Skriv kundens röstdokument (SOUL). | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| AD-046 | Skriv kundens affärskontext. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| AD-047 | Ett fält sparas i taget, utan att röra de andra. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| AD-048 | Se exakt vad agenten läser för kunden. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| AD-049 | Slå på och av tillägg per kund. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `public.admin_workspace_addons(uuid)` | inte gjord |
| AD-050 | Flytta en testkund till ett riktigt konto. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `POST /api/admin/konvertera` | inte gjord |
| AD-051 | Stäng av eller återaktivera ett kundkonto (manuell trial-konvertering). | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `PUT /api/admin/tenants/{id}/aktiv` | inte gjord |
| AD-052 | Sätt kontoläge aktiv / pausad / avslutad. | `/crm/admin/kunder/[id]` (ny) fliken Agentprofil och tillägg · BolagPanel + BolagFormular | 5 | finns: `PUT /api/admin/tenants/{id}/status` | inte gjord |
| AD-053 | Flytta till main: välj mejl, leadskörningar och listor i development och spara dem till produktionen. | `/crm/admin/kunder/[id]` (ny) fliken Flytt till main och TableSelectionToolbar i `/crm/iris/leads` · BolagVy + SynkVy | 5 | finns: `GET /api/admin/flytt/status` | inte gjord |
| AD-054 | Flytta markerade leads till main direkt ur leadsvyn. | `/crm/admin/kunder/[id]` (ny) fliken Flytt till main och TableSelectionToolbar i `/crm/iris/leads` · BolagVy + SynkVy | 5 | finns: `lib/actions/flytt.ts:flyttaProspektTillMain` | inte gjord |
| AD-055 | Det flyttade blir skarpt i main, med bedömning och väntande utkast. | `/crm/admin/kunder/[id]` (ny) fliken Flytt till main och TableSelectionToolbar i `/crm/iris/leads` · BolagVy + SynkVy | 5 | finns: `admin_flytt.py:_bygg_paket` | inte gjord |
| AD-056 | Granska ett flyttpaket utan att skicka (ingen yta). | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `admin_flytt.py` | inte gjord |
| AD-057 | Mottagaren i main tar emot utan master-nyckel. | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `admin_flytt.py:mottag` | inte gjord |
| AD-060 | Bläddra mellan kunder i registret. | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: `GET /api/admin/tenants` | inte gjord |
| AD-061 | Kontaktpersoner hos kunden (Snajps egna kontakter, inte leads). | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: `POST /api/admin/tenants/{id}/kontakter` | inte gjord |
| AD-062 | Kunduppgifter (faktureringsregistret). | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: `PUT /api/admin/tenants/{id}/kunddata` | inte gjord |
| AD-063 | Avtalsgrinden: kräv signerat avtal innan trafik släpps fram. | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: se läsarens rad | inte gjord |
| AD-064 | Varningen "Trafiken är stoppad" visar det sparade läget, inte rutans. | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: `ss_tenants.kraver_avtal` | inte gjord |
| AD-065 | Onboardingen fyller adminens kundregister åt kunden. | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: `lib/snajp/kundregister.ts:registreraKunduppgifter` | inte gjord |
| AD-066 | Kontaktpersonernas fält och fel. | `/crm/admin/kunder/[id]` (ny) fliken Uppgifter och kontakter · BolagFormular + BolagVy | 5 | finns: `admin_kunddata.py` | inte gjord |
| AD-070 | Välj agent och se vilken kedja som körs. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `GET /api/admin/tenants/{id}/insyn?agent=leads\|support` | inte gjord |
| AD-071 | Flödeskarta: varje playbook som en bana med stegen i körordning och kodgrindarna som egna noder. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `insyn.banor` | inte gjord |
| AD-072 | Välj en körning att lägga över kartan. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `GET /api/admin/runs?tenant_id=&limit=80` | inte gjord |
| AD-073 | Steginfo för valt steg. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `insyn.banor[].noder[]` | inte gjord |
| AD-074 | Lagerstapeln: prompten exakt som den byggs, lager för lager. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `step_log[].lager` | inte gjord |
| AD-075 | Källmatrisen: varje underlag mot varje steg. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `insyn.matris` | inte gjord |
| AD-076 | Skills som lästes i en vald körning. | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · NYTT MÖNSTER: flödeskarta och lagerstapel (insyn) | 5 | finns: `kedja.skills` | inte gjord |
| AD-077 | Prova en fråga mot kundens kunskapsbas (bara Kundtjänst). | `/crm/admin/kunder/[id]` (ny) fliken Underlag och flöde · BolagFormular | 5 | finns: `POST /api/admin/tenants/{id}/insyn/kb-prov` | inte gjord |
| AD-080 | Objektet Logg med vyflikarna Körningar, Händelser, Testkörningar, Kostnad per agent. | `/crm/admin/logg` (ny) vyn Körningar och `/crm/admin/logg/[id]` · BolagVy + NYTT MÖNSTER: stegspår för en körning | 5 | behövs ingen (klient) | inte gjord |
| AD-081 | Filtrera agentkörningar per agenttyp. | `/crm/admin/logg` (ny) vyn Körningar och `/crm/admin/logg/[id]` · BolagVy + NYTT MÖNSTER: stegspår för en körning | 5 | finns: `GET /api/admin/runs?tenant_id=&agent_type=&limit=200&sammandrag=true` | inte gjord |
| AD-082 | Nyckeltal och diagram över de hämtade körningarna (upp till 200). | `/crm/admin/logg` (ny) vyn Körningar och `/crm/admin/logg/[id]` · BolagVy + NYTT MÖNSTER: stegspår för en körning | 5 | finns: se läsarens rad | inte gjord |
| AD-083 | Tabellen Körningar. | `/crm/admin/logg` (ny) vyn Körningar och `/crm/admin/logg/[id]` · BolagVy + NYTT MÖNSTER: stegspår för en körning | 5 | behövs ingen (klient) | inte gjord |
| AD-084 | Spåret för en körning, steg för steg. | `/crm/admin/logg` (ny) vyn Körningar och `/crm/admin/logg/[id]` · BolagVy + NYTT MÖNSTER: stegspår för en körning | 5 | finns: `GET /api/admin/runs/{id}` | inte gjord |
| AD-090 | Händelser (notiscentret) över alla kunder och plattformen. | `/crm/admin/logg` (ny) vyerna Händelser, Testkörningar, Kostnad · BolagVy + OversiktVy | 5 | finns: `GET /api/admin/events?level=&limit=300` | inte gjord |
| AD-091 | Grupperad händelselista med begriplig rubrik och teknisk råtext. | `/crm/admin/logg` (ny) vyerna Händelser, Testkörningar, Kostnad · BolagVy + OversiktVy | 5 | finns: `platform_events` | inte gjord |
| AD-092 | Testkörningar: starta Iris-körningar och snabbsök som test från adminytan. | `/crm/admin/logg` (ny) vyerna Händelser, Testkörningar, Kostnad · BolagVy + OversiktVy | 5 | finns: `/api/snajp-support/leads/*` | inte gjord |
| AD-093 | Kostnad per agent: Iris, Kundtjänst och Kvitton sida vid sida. | `/crm/admin/logg` (ny) vyerna Händelser, Testkörningar, Kostnad · BolagVy + OversiktVy | 5 | finns: `GET /api/admin/runs?agent_type=…&limit=200&sammandrag=true` | inte gjord |
| AD-094 | Förbrukning per kund som maskinläsbar lista (ingen egen yta). | `/crm/admin/logg` (ny) vyerna Händelser, Testkörningar, Kostnad · BolagVy + OversiktVy | 5 | finns: `admin.py:usage` | inte gjord |
| AD-100 | Översikt över paket och kontolägen. | `/crm/admin/paket` (ny) · BolagVy + BolagFormular | 5 | finns: `GET /api/admin/tenants` | inte gjord |
| AD-101 | Tabellen Kundernas paket. | `/crm/admin/paket` (ny) · BolagVy + BolagFormular | 5 | behövs ingen (klient) | inte gjord |
| AD-102 | Byt kundens paket. | `/crm/admin/paket` (ny) · BolagVy + BolagFormular | 5 | finns: `public.admin_set_workspace_products(...)` | inte gjord |
| AD-103 | Slå på kvittohanteraren som tillägg till Support. | `/crm/admin/paket` (ny) · BolagVy + BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| AD-104 | Tillägg i paketpanelen. | `/crm/admin/paket` (ny) · BolagVy + BolagFormular | 5 | finns: se läsarens rad | inte gjord |
| AD-105 | Pausa, avsluta eller återaktivera kontot. | `/crm/admin/paket` (ny) · BolagVy + BolagFormular | 5 | finns: `PUT /api/admin/tenants/{id}/status` | inte gjord |
| AD-110 | Inställningsgruppen "Plattformen" (bara admin). | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | behövs ingen (klient) | inte gjord |
| AD-111 | Välj promptlager: Gemensamt, Supportagenten, Iris. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `GET /api/admin/instruktioner?agent=alla\|support\|leads` | inte gjord |
| AD-112 | Se vad agenten läser just nu. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `global_instructions` | inte gjord |
| AD-113 | Skriv feedback och förhandsgranska hur den bakas in. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `POST /api/admin/instruktioner/forhandsgranska` | inte gjord |
| AD-114 | Spara och aktivera en ny version. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `PUT /api/admin/instruktioner` | inte gjord |
| AD-115 | Historik och återställning. | `/crm/installningar/plattformen/instruktioner` (ny) · NYTT MÖNSTER: förhandsgranskning med versioner (före, efter, återställ) | 5 | finns: `POST /api/admin/instruktioner/{id}/aterstall` | inte gjord |
| AD-116 | Tvåstegsverifiering för plattformsadmin. | `/crm/installningar/plattformen/tvasteg` (ny) · BolagFormular | 5 | finns: migration 128 | inte gjord |
| AD-117 | Bädda in kunskapsartiklar som saknar vektor (ingen yta). | Ingen egen vy: under ytan, oförändrad backend | 5 | finns: `admin_profil.py:badda_in_kb` | inte gjord |
| AD-120 | Grinden för webbplatsbedömningen. | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | 5 | finns: `snajp-support/app/leads/webbpool.py` | inte gjord |
| AD-121 | Webbpoolen: varje körnings bolag bedöms och fördelas tyst till webbyråerna. | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | 5 | finns: `app/leads/webbpool.py` | inte gjord |
| AD-122 | Bakåtfyllnad av webbpoolen för alla kunders gamla leads (ingen yta). | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | 5 | finns: `admin_webbpool.py` | inte gjord |
| AD-123 | Kopiera eller flytta en färdig leadslista till en annan kund. | `/crm/iris/listor` (ny) · TableSelectionToolbar, bara plattformsadmin | 4 | finns: `POST /api/admin/listor/{id}/till-kund` | inte gjord |
| AD-124 | Ombedömning av sparade Iris-leads med dagens regler (ingen yta). | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | 5 | finns: `admin_ombedom.py` | inte gjord |
| AD-125 | Utkastsvepet: hälsnings- och signaturreglerna på alla osända leadsutkast hos alla kunder (ingen yta). | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | 5 | finns: `admin_utkastsvep.py` | inte gjord |
| AD-126 | Gallringens insyn (ingen yta i appen). | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | 5 | finns: `admin_gallring.py` | inte gjord |
| AD-130 | Händelseloggen som spårbarhet för varje adminskrivning. | `/crm/admin/logg` (ny) vyn Händelser · BolagVy | 5 | finns: `platform_events` | inte gjord |
| AD-131 | Kundbesöken loggas. | `/crm/admin/logg` (ny) vyn Händelser · BolagVy | 5 | finns: `platform_events` | inte gjord |
| AD-132 | Synkvakten larmar när speglingen main → development står still. | Ingen egen vy: under ytan, oförändrad backend; händelserna i `/crm/admin/logg` | 5 | finns: `app/jobs/synkvakt.py` | inte gjord |
| AD-133 | Övervakning av produktionen med mejllarm. | Ingen egen vy: under ytan, oförändrad backend; händelserna i `/crm/admin/logg` | 5 | finns: `scripts/overvakning.py` | inte gjord |
| AD-134 | Trial-påminnelser till kunden. | Ingen egen vy: under ytan, oförändrad backend; händelserna i `/crm/admin/logg` | 5 | finns: `app/jobs/trial_paminnare.py` | inte gjord |
| AD-135 | Städaren avslutar hängande leadsjobb och listor ärligt. | Ingen egen vy: under ytan, oförändrad backend; händelserna i `/crm/admin/logg` | 5 | finns: `app/jobs/stadare.py` | inte gjord |
| AD-136 | Åtkomstlogg för varje anrop med master-nyckeln. | Ingen egen vy: under ytan, oförändrad backend; händelserna i `/crm/admin/logg` | 5 | finns: `snajp-support/app/api/adminlogg.py` | inte gjord |
| AD-137 | Kundväxel och vyväxel också i kundskalet. | `CrmRam` (befintlig): arbetsyteväxlaren · CrmRam | 4 | behövs ingen (klient) | inte gjord |
| AD-138 | Driftrutor i översikterna. | `/crm` (befintlig), `/crm/iris` och `/crm/kundtjanst`: driftkort bara för plattformsadmin · OversiktVy | 5 | finns: `drift` | inte gjord |
| AD-139 | Vilande produkter går att öppna för admin. | `CrmRam` (befintlig) och vyerna, synligt bara för plattformsadmin | 5 | behövs ingen (klient) | inte gjord |
| AD-139b | Flytta till main från leadsöversikten. | `/crm/admin/kunder/[id]` (ny) fliken Flytt till main och TableSelectionToolbar i `/crm/iris/leads` · BolagVy + SynkVy | 5 | behövs ingen (klient) | inte gjord |
| AD-140 | Lägg upp en namngiven kund (skript, ingen yta). | Ingen egen vy: under ytan, oförändrad backend (skript) | 5 | finns: `POST /api/keys` | inte gjord |
| AD-141 | Självregistrerad kund får egen tenant och provperiod. | Ingen egen vy: under ytan, oförändrad backend (skript) | 5 | finns: migration 061, 074 | inte gjord |
| AD-142 | Övriga adminkommandon utan yta (urval). | Ingen egen vy: under ytan, oförändrad backend (skript) | 5 | finns: `scripts/*.py` | inte gjord |
| AD-143 | Fler driftkommandon utan yta (kontrolläsarens komplettering). | Ingen egen vy: under ytan, oförändrad backend (skript) | 5 | finns: `scripts/*.py` | inte gjord |
| AD-150 | Adminytans egen ordbok. | Hela CRM:et via `lib/i18n.tsx`; adminordboken `lib/admin/sprak.ts` följer med | 5 | behövs ingen (klient) | inte gjord |
| AD-151 | Datum, tider och tal. | Hela CRM:et via `lib/i18n.tsx`; adminordboken `lib/admin/sprak.ts` följer med | 5 | behövs ingen (klient) | inte gjord |
| AD-152 | Kända luckor i tvåspråkigheten. | Hela CRM:et via `lib/i18n.tsx`; adminordboken `lib/admin/sprak.ts` följer med | 5 | behövs ingen (klient) | inte gjord |

### API:t under ytorna (app-10, 179 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| AP1 | Inloggad kunds väg till hela backenden (inkorg, utkast, regler, kunskapsbas, leads, agent, CRM, usage, analys) | Ingen vy; proxyn som alla CRM-vyer anropar (finns) | 4 | finns: `app/api/snajp-support/[...path]/route.ts` | inte gjord |
| AP2 | Publik supportchatt startar ett chattjobb | Utanför `/crm`: widgetens och den publika chattens väg | 5 | finns: `app/api/snajp-support/chat/route.ts` | inte gjord |
| AP3 | Publik chatt hämtar sitt eget samtal (medarbetarens svar efter överlämning) | Utanför `/crm`: widgetens och den publika chattens väg | 5 | finns: `chat/samtal/route.ts` | inte gjord |
| AP4 | Publik chatt pollar sitt jobb | Utanför `/crm`: widgetens och den publika chattens väg | 5 | finns: `jobs/[jobId]/route.ts` | inte gjord |
| AP5 | Testchatten för den inloggade kunden | Ingen vy; anropas av `/crm/kundtjanst/testchatt` | 5 | finns: `testchatt/route.ts` | inte gjord |
| AP6 | Testchatten hämtar samtal och pollar jobb | Ingen vy; anropas av `/crm/kundtjanst/testchatt` | 5 | finns: `testchatt/samtal/route.ts` | inte gjord |
| AP7 | Inloggad pollning av leadsjobb (körning, utkast, utskick) | Ingen vy; förloppet i `/crm/iris/...` · SynkVy | 4 | finns: `leads/jobb/[jobId]/route.ts` | inte gjord |
| AP8 | Sortera-inkorgen-demon på den publika supportsidan | Utanför `/crm`: marknadssidorna | 5 | finns: `triage/route.ts` | inte gjord |
| AP9 | Kvittohanterarens proxy (binärsäker) | Ingen vy; anropas av `/crm/kvitton` | 5 | finns: `kvitton/[[...path]]/route.ts` | inte gjord |
| AP10 | Bokföringens proxy (SIE4, underlag, chatt, avstämning) | Ingen vy; anropas av `/crm/kvitton` | 5 | finns: `bookkeeping/[...path]/route.ts` | inte gjord |
| AP11 | Admins läsväg till `/api/admin/*` | Ingen vy; anropas av `/crm/admin/...` och Byt kund | 5 | finns: `app/api/admin/[...path]/route.ts` | inte gjord |
| AP12 | Lista kunder som "Byt kund" kan öppna | Ingen vy; anropas av `/crm/admin/...` och Byt kund | 5 | finns: `app/api/admin/kunder/route.ts` | inte gjord |
| AP13 | "Kör agent"-knappen till agentsajten (supportportalen) med engångsbiljett | Ingen vy; Kör agent i `/crm/kundtjanst` | 5 | finns: `app/api/agentsajt/[agent]/sso/route.ts` | inte gjord |
| AP14 | Inloggning (Auth.js) | Ingen vy; inloggningen | 5 | finns: `app/api/auth/[...nextauth]/route.ts` | inte gjord |
| AP15 | Email Studio: skriv om ett mejl med AI (kortare, skriv om, förbättra, personalisera, översätt, A/B, uppföljning, analysera, längre) | Ingen vy; används av NYTT MÖNSTER: utkastredigerare (ämne, text, signatur och fot som mottagaren ser dem) | 4 | finns: `app/api/email-studio/route.ts` | inte gjord |
| AP16 | Hälsokontroll för webbtjänsten | Ingen vy (hälsa) | 5 | finns: `app/api/health/route.ts` | inte gjord |
| AP17 | Publik supportlänk skapar en ny chattsession | Utanför `/crm`: widgetens och den publika chattens väg | 5 | finns: `app/chat/[tenant]/route.ts` | inte gjord |
| AP18 | Spårad demolänk i utskick: klick och besök | Utanför `/crm`: `/prova/[token]`; besöken syns i `/crm/iris` | 4 | finns: `app/prova/[token]/route.ts` | inte gjord |
| AP19 | Inloggningsgrind och CSP för inbäddning | Ingen vy; proxyn som alla CRM-vyer anropar (finns) | 4 | finns: `proxy.ts` | inte gjord |
| AP20 | `llms.txt` för AI-sökmotorer | Utanför `/crm`: marknadssidorna | 5 | finns: `app/llms.txt/route.ts` | inte gjord |
| AP21 | Hälsa, liveness och readiness | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `main.py` | inte gjord |
| AP22 | Starta ett chattsvar från agenten (publik, testchatt, egen integration) | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chat.py` | inte gjord |
| AP23 | Läs tillbaka ett samtal | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chat.py` | inte gjord |
| AP24 | Läs ett jobbs läge | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chat.py` | inte gjord |
| AP25 | Lista överlämnade chattar med orsakstext | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chattar.py` | inte gjord |
| AP26 | Öppna en överlämnad chatt | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chattar.py` | inte gjord |
| AP27 | Medarbetaren svarar i en överlämnad chatt | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chattar.py` | inte gjord |
| AP28 | Lämna tillbaka chatten till agenten | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `chattar.py` | inte gjord |
| AP29 | Läs och spara supportagentens eskaleringsregler | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `support_config.py` | inte gjord |
| AP30 | Supportöversiktens tal och veckograf | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `support_oversikt.py` | inte gjord |
| AP31 | Kundens egna system (HTTP-verktyg, MCP): lista, skapa, ändra, ta bort | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `integrationer.py` | inte gjord |
| AP32 | Lista en integrations verktyg och prova den | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `integrationer.py` | inte gjord |
| AP33 | Kanalanslutningar (WhatsApp, Messenger, Slack, Teams): lista, skapa, ändra, ta bort, prova | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `kanaler.py` | inte gjord |
| AP34 | Ta emot kanalwebhooks | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `kanaler.py` | inte gjord |
| AP35 | Klassa mejl (demo och API) | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `triage.py` | inte gjord |
| AP36 | Hämta ärende med historik / kundens historik | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `tickets.py` | inte gjord |
| AP37 | Skapa tenant och API-nyckel | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `keys.py` | inte gjord |
| AP38 | Kunskapsbasen: lista, lägg till, ta bort artikel | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `kb.py` | inte gjord |
| AP39 | Skanna kundens webbplats till artikelförslag | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `kb.py` | inte gjord |
| AP40 | Läs text ur en PDF till kunskapsbasen | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `kb.py` | inte gjord |
| AP41 | Inkorgar: lista, upptäck inställningar, koppla, koppla ur | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `inbox.py` | inte gjord |
| AP42 | Synka inkorgen nu | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `inbox.py` | inte gjord |
| AP43 | Lägg in exempelmejl / externt mejl | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `inbox.py` | inte gjord |
| AP44 | Lista inkorgen med räknare | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `inbox.py` | inte gjord |
| AP45 | Provsortera mejl i realtid | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `inbox.py` | inte gjord |
| AP46 | Åtgärder på ett mejl: läs, klassa om, ta över, markera hanterat, processa om, befordra testmejl | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `inbox.py` | inte gjord |
| AP47 | Supportutkast: godkänn och skicka, omformulera, avvisa | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `drafts.py` | inte gjord |
| AP48 | Kategoriregler (automatiskt / granska) | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `rules.py` | inte gjord |
| AP49 | Avsändardomän: skapa, läs, verifiera | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `sending_domains_api.py` | inte gjord |
| AP50 | Resend-webhooks: domänstatus, studs och klagomål | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `sending_domains_api.py` | inte gjord |
| AP51 | Publik demochatt med kaksession | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `demo.py` | inte gjord |
| AP52 | Veckoanalys | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `analytics.py` | inte gjord |
| AP53 | Kundens förbrukning per dag och budget | Ingen vy (ändpunkt); anropas av `/crm/kundtjanst/...` | 5 | finns: `usage.py` | inte gjord |
| AP60 | Affärskontext (produktmarknadsföring) som dokument | Ingen vy (ändpunkt); anropas av `/crm/installningar` och onboardingen | 5 | finns: `leads.py` | inte gjord |
| AP61 | Onboardingläge, kontextpaket och onboardingchatt för Iris | Ingen vy (ändpunkt); anropas av `/crm/installningar` och onboardingen | 5 | finns: `leads.py` | inte gjord |
| AP62 | Skapa ett prospekt för hand / exempelprospekt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP63 | Lista prospekt (leads) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP64 | Fördelningen av prospekt (Iris, ringlista, ej kvalificerade, utan webbplats) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP65 | Läs ett prospekt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP66 | Lägg till en källa på ett prospekt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP67 | Senaste utkastet för ett prospekt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP68 | Befordra ett lead (listspår → Iris) / degradera | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP69 | Ändra prospektets bedömning/status (PATCH) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP70 | Iris röstdokument (soul) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP71 | Önskemål till agenten (fritext som bakas in i instruktionen) med förhandsgranskning och versioner | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP72 | Kör ett researchsteg / skriv ett utkast för ett prospekt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP73 | Lista körningar (äldre format) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP74 | Svar från prospekt: registrera och lista | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP75 | Kör uppföljningssvepet nu | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP76 | Agentens förbättringsförslag: lista, godkänn, öppna som ärende, avfärda | Ingen vy (ändpunkt); anropas av `/crm/larande` | 5 | finns: `leads.py` | inte gjord |
| AP77 | Feedback till agenten | Ingen vy (ändpunkt); anropas av `/crm/larande` | 5 | finns: `leads.py` | inte gjord |
| AP78 | Skickade utskick och antal | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP79 | Leadsinställningar (autonomi, sändning, automation, autopilot, produkter, eskalering) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP80 | Erbjudanden (offerter till utkasten) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP81 | Vilka har besökt demon (spårade länkar) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP82 | Iris-profilen (målgrupp) och omtolkning | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP83 | Jevs statistik (första filtret) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP84 | Körningar: lista och läsa en | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP85 | Styr en körning: pausa, återuppta, avbryt, fortsätt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP86 | Körningens utkast: lista, skriv, skicka (synkront eller som jobb med förlopp) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP87 | Granskningskön: lista, ändra text, godkänn, avvisa | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP88 | Schemalägg, skicka nu, tillbaka till Iris | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP89 | Provmejl till sig själv | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP90 | Starta en Iris-körning | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP91 | Processa om valda prospekt (skriv utkast ur befintlig research) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP92 | Beställ en leadslista (listspåret) / kombinera listor | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP93 | Lista och läsa leadslistor | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP94 | Listrad → lead, utkast för listan, köa en rads utkast, pröva om listan | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP95 | Ta bort en lista | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_massatgard.py` | inte gjord |
| AP96 | Arkivera eller radera prospekt i mängd | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_massatgard.py` | inte gjord |
| AP100 | Bolagets tidslinje | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_suite.py` | inte gjord |
| AP101 | Logga ett samtal (utfall Ej svar, Återkom, Ej intresserad, Kontakta inte, Möte bokat) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_suite.py` | inte gjord |
| AP102 | Ringlistan och återkopplingslistan, med antal för i dag | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_suite.py` | inte gjord |
| AP103 | Anteckningar och uppgifter på ett bolag | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_suite.py` | inte gjord |
| AP104 | Sparade vyer i leadstabellen | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_suite.py` | inte gjord |
| AP105 | Importera kundens egen fil (annat CRM, kalkylblad) med förhandsgranskning | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_suite.py` | inte gjord |
| AP106 | Konversationer: lista med räknare, läsa tråd, markera läst | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_konversationer.py` | inte gjord |
| AP107 | Svarsutkast i en tråd: spara, skicka, kassera, återställ, skriv om med Iris | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_konversationer.py` | inte gjord |
| AP108 | Byt steg i tråden / lägg in en extern händelse | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_konversationer.py` | inte gjord |
| AP109 | Notiser: lista, antal i navigationen, markera lästa | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_konversationer.py` | inte gjord |
| AP110 | Uppföljningar: lista och skriv nu för markerade | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_uppfoljningar.py` | inte gjord |
| AP111 | Bolagssökning över alla leads | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_uppfoljningar.py` | inte gjord |
| AP112 | Kampanjer: lista med utfall, läsa, skapa, skicka | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_kampanjer.py` | inte gjord |
| AP120 | Alla kunder med nyckeltal (aktiv, produkter, körningar, ärenden, senaste aktivitet) | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP121 | Agentkörningar: per kund, alla (filter, `sammandrag=true`), en körning med steg | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP122 | Insyn: vad agenten ser för en kund (instruktioner, skills, kunskapsbas), skillfil, kb-prov | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP123 | En körnings kedja för ett bolag (utfall per nod, grindar, var den stannade) | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP124 | Plattformshändelser (fel, varningar) | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP125 | Kundens inkorg, utkast och leadsunderlag sett av admin | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP126 | Förbrukning per kund (fakturering och kostnad) | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP127 | Diagnos av mejlvägen och provmejl | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin.py` | inte gjord |
| AP128 | Ombedöm sparade Iris-leads efter regelskärpning | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_ombedom.py` | inte gjord |
| AP129 | Kundregistret: läsa, spara, kontaktpersoner | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_kunddata.py` | inte gjord |
| AP130 | Gallringens insyn: översikt och logg per kund | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_gallring.py` | inte gjord |
| AP131 | Agentinstruktionerna (gemensamt lager, support, leads): läsa, förhandsgranska feedback, spara, återställ version | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_profil.py` | inte gjord |
| AP132 | Kundens agentprofil: läsa alla fält och var de hamnar i prompten, spara skickade fält | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_profil.py` | inte gjord |
| AP133 | Stäng av / slå på en kund, sätt kundstatus | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_profil.py` | inte gjord |
| AP134 | Bädda in kunskapsartiklar som saknar vektor | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_profil.py` | inte gjord |
| AP135 | Konvertera en testkund till en riktig kund | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_konvertera.py` | inte gjord |
| AP136 | Webbpoolens bakåtfyllnad: läge och kör | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_webbpool.py` | inte gjord |
| AP137 | Normalisera utkast hos alla kunder (svep) | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_utkastsvep.py` | inte gjord |
| AP138 | Kopiera eller flytta en leadslista till en annan kund | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_listor.py` | inte gjord |
| AP139 | Flytt från spegeln (development) till main: status, kandidater, paket, skicka | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_flytt.py` | inte gjord |
| AP140 | Ta emot ett flyttpaket i main | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `admin_flytt.py` | inte gjord |
| AP141 | Migrationsliggarens versioner för PR-kontrollen | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | 5 | finns: `drift.py` | inte gjord |
| AP142 | Kvitton: kopplat mejlkonto, skanna inkorgen (synkront och som jobb med förlopp) | Ingen vy (ändpunkt); anropas av `/crm/kvitton` | 5 | finns: `kvitton.py` | inte gjord |
| AP143 | Kvitton: lista, sammanfattning, rensa period, ladda upp underlag | Ingen vy (ändpunkt); anropas av `/crm/kvitton` | 5 | finns: `kvitton.py` | inte gjord |
| AP144 | Kvitton: godkänn, byt riktning (in/ut), exportera CSV, kvittochatt | Ingen vy (ändpunkt); anropas av `/crm/kvitton` | 5 | finns: `kvitton.py` | inte gjord |
| AP145 | Bokföringsmotorn: underlag, periodrapport, rensa period, SIE4-export, chatt, avstämning | Ingen vy (ändpunkt); anropas av `/crm/kvitton` | 5 | finns: `bookkeeping.py` | inte gjord |
| AP146 | CRM-appens API-nycklar: lista, skapa (klartext en gång), återkalla | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm.py` | inte gjord |
| AP147 | CRM-översikten (antal bolag per relation, personer, anslutningar, senaste synkkörningar) | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm.py` | inte gjord |
| AP148 | CRM-API v1, bolag: lista (sök, sortera, markör), skapa eller uppdatera på org.nr, läsa, ändra, ta bort (mjukt), återställa | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm_v1.py` | inte gjord |
| AP149 | CRM-API v1, personer: samma operationer, upsert på e-post | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm_v1.py` | inte gjord |
| AP150a | CRM-API v1, anslutningar och mappning | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm_v1.py` | inte gjord |
| AP150b | CRM-API v1, synkkörningar: starta, lista, läsa med räknare och fel, skicka satser, slutföra; satssynk i ett anrop | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm_v1.py` | inte gjord |
| AP150c | CRM-API v1, nyckeln som används och specifikationen | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `crm_v1.py` | inte gjord |
| AP160 | Chattjobben överlever en deploy | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `main.py` | inte gjord |
| AP161 | Leadskörningarnas per-prospektjobb överlever en deploy | Ingen vy (bakgrundsjobb); förlopp och utfall i `/crm/iris/...` | 4 | finns: `main.py` | inte gjord |
| AP162 | Sändaren för godkända utkast och bevakningen | Ingen vy (bakgrundsjobb); förlopp och utfall i `/crm/iris/...` | 4 | finns: `leads/scheduler.py` | inte gjord |
| AP163 | Den gamla schemaläggaren för autonoma utskick | Ingen vy (bakgrundsjobb); förlopp och utfall i `/crm/iris/...` | 4 | finns: `leads/scheduler.py` | inte gjord |
| AP164 | Leads-städaren, väckaren och autopiloten | Ingen vy (bakgrundsjobb); förlopp och utfall i `/crm/iris/...` | 4 | finns: `jobs/stadare.py` | inte gjord |
| AP165 | Trial-påminnaren | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `jobs/trial_paminnare.py` | inte gjord |
| AP166 | Gallringen | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `jobs/gallring.py` | inte gjord |
| AP167 | Inkorgspollern | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `email_pipeline/poller.py` | inte gjord |
| AP168 | Vertex-token hålls färsk | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `agent/llm.py:varm_vertex_token` | inte gjord |
| AP169 | Jobb med förlopp (`jobs.bakgrund`) | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `jobs/bakgrund.py` | inte gjord |
| AP170 | Lösa bakgrundsuppgifter utan förloppsväg | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: Se respektive ändpunkt | inte gjord |
| AP171 | Webhooks in | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: Se respektive | inte gjord |
| AP172 | GitHub Actions mot drift | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | 5 | finns: `.github/workflows/` | inte gjord |
| AP180 | Adminläsning för serverrenderade sidor | Ingen vy (serveråtgärd); anropas av vyn som raden nämner | 5 | finns: `lib/data/admin.ts` | inte gjord |
| AP181 | Agentinstruktioner och kundprofil | Ingen vy (serveråtgärd); anropas av vyn som raden nämner | 5 | finns: `lib/actions/agentinstruktioner.ts` | inte gjord |
| AP182 | Kundregister och kontakter | Ingen vy (serveråtgärd); anropas av vyn som raden nämner | 5 | finns: `lib/actions/kunddata.ts` | inte gjord |
| AP183 | Avstängning, kundstatus, konvertering, listflytt, flytt till main, insyn | Ingen vy (serveråtgärd); anropas av vyn som raden nämner | 5 | finns: `lib/actions/avstangning.ts` | inte gjord |
| AP184 | Provisionering och standardvärden för ny kund | Ingen vy (serveråtgärd); anropas av vyn som raden nämner | 5 | finns: `lib/actions/onboarding.ts` | inte gjord |
| AP185 | Affärskontexten | Ingen vy (serveråtgärd); `/crm/installningar/vad-ni-saljer` | 5 | finns: `lib/actions/affarskontext.ts` | inte gjord |
| AP186 | Serveråtgärder som bara rör Next-databasen | Ingen vy (serveråtgärd); anropas av vyn som raden nämner | 5 | finns: `lib/actions/*` | inte gjord |
| AP220 | Startvägran när miljön är fel konfigurerad | Ingen vy (ändpunkt eller grind) | 5 | finns: `main.py:lifespan` | inte gjord |
| AP221 | Uppstartens självläkning | Ingen vy (ändpunkt eller grind) | 5 | finns: `main.py` | inte gjord |
| AP222 | Loopvakt och dödsvakt | Ingen vy (ändpunkt eller grind) | 5 | finns: `loopvakt.py` | inte gjord |
| AP223 | Ohanterade fel blir händelser, kvotfel blir 429 | Ingen vy (ändpunkt eller grind) | 5 | finns: `api/events.py` | inte gjord |
| AP224 | Mätning och spårning per anrop | Ingen vy (ändpunkt eller grind) | 5 | finns: `sparning.py` | inte gjord |
| AP225 | CORS för kundens egen webbapp | Ingen vy (ändpunkt eller grind) | 5 | finns: `main.py` | inte gjord |
| AP226 | Tak på LLM-anrop per timme (överlever omstart) | Ingen vy (ändpunkt eller grind) | 5 | finns: `api/rate_limit_db.py` | inte gjord |
| AP227 | Chattens grindar före jobbet | Ingen vy (ändpunkt eller grind) | 5 | finns: `api/chat.py` | inte gjord |
| AP228 | Dubbelklicksspärren för starter | Ingen vy (ändpunkt eller grind) | 5 | finns: `api/dubbelstart.py` | inte gjord |
| AP229 | Stegloggarnas texter lämnar aldrig backenden | Ingen vy (ändpunkt eller grind) | 5 | finns: `api/stegtexter.py` | inte gjord |
| AP230 | Åtkomstloggen för master-nyckeln | Ingen vy (ändpunkt eller grind) | 5 | finns: `api/adminlogg.py` | inte gjord |
| AP231 | CRM-API v1: tak, idempotens och sidindelning | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `api/crm_v1.py` | inte gjord |
| AP232 | CRM-API v1: avtalsgrind och felkoder vid skrivning | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `api/crm_v1.py` | inte gjord |
| AP233 | CRM-API v1: anslutningar och synksatser, gränser | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `api/crm_v1.py` | inte gjord |
| AP234 | CRM-nycklar: validering | Ingen vy (ändpunkt); anropas av `/crm`, `/crm/bolag`, `/crm/personer`, `/crm/synk`, `/crm/utvecklare` (befintliga) | 3 | finns: `api/crm.py` | inte gjord |
| AP235 | Bolagssökningen: gränser | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_uppfoljningar.py` | inte gjord |
| AP236 | Uppföljningar: skriv nu, med skäl för det som hoppas över | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads_uppfoljningar.py` | inte gjord |
| AP237 | Sändlistans schemaläggning och "tillbaka till Iris" | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | 4 | finns: `leads.py` | inte gjord |
| AP238 | Koppla inkorg: felmeddelanden | Ingen vy (ändpunkt eller grind) | 5 | finns: `inbox.py` | inte gjord |
| AP239 | Förbrukningens fönster | Ingen vy (ändpunkt eller grind) | 5 | finns: `usage.py` | inte gjord |
| AP240 | Flytten till main: grindar på båda sidor | Ingen vy (ändpunkt eller grind) | 5 | finns: `admin_flytt.py` | inte gjord |
| AP241 | Schemaläsningen för PR-kontrollen | Ingen vy (ändpunkt eller grind) | 5 | finns: `drift.py` | inte gjord |
| AP242 | Publika metadatarutter | Ingen vy (ändpunkt eller grind) | 5 | finns: `app/robots.ts` | inte gjord |

### Luckorna (demo och demobokning) (app-99, 14 rader)

| ID | Funktion | Plats i det nya gränssnittet | Fas | Backend | Läge |
|---|---|---|---|---|---|
| LX-001 | Besökaren öppnar CRM-listdemon utan inloggning. | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |
| LX-002 | Besökaren laddar upp en kundlista som CSV, som läses i webbläsaren. | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |
| LX-003 | Besökaren laddar in en exempellista. | Utanför `/crm` (publik demo); beslut Anton | 5 | finns: `public/demo/crm-exempel.csv` | inte gjord |
| LX-004 | Besökaren tömmer listan med dubbelbekräftelse. | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |
| LX-005 | Listan och affärsprofilen finns kvar efter omladdning i samma webbläsare. | Utanför `/crm` (publik demo); beslut Anton | 5 | finns: `localStorage` | inte gjord |
| LX-006 | Besökaren beskriver sin produkt och affärsidé, som Email Studio läser inför varje omskrivning. | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |
| LX-007 | Besökaren söker i kundlistan och väljer en kund (lista till vänster, detalj till höger). | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |
| LX-008 | Kundens panel visar fakta, signaler och en egen Email Studio. | Utanför `/crm` (publik demo); beslut Anton | 5 | finns: `POST /api/email-studio` | inte gjord |
| LX-010 | Besökaren bokar en demo via Cal.com när kalendern är inkopplad. | Utanför `/crm` (publik demo); beslut Anton | 5 | finns: Cal.com (extern) | inte gjord |
| LX-011 | Besökaren skickar en demoförfrågan i formuläret när Cal.com inte är inkopplad. | Utanför `/crm` (publik demo); beslut Anton | 5 | finns: `public.demo_requests` | inte gjord |
| LX-012 | (Saknas) Någon läser demoförfrågningarna. | Utanför `/crm` (publik demo); beslut Anton | 5 | saknas: läsning av `demo_requests` | inte gjord |
| LX-013 | Demoförfrågningar raderas vid GDPR-radering av en person. | Utanför `/crm` (publik demo); beslut Anton | 5 | finns: `scripts/gdpr_radera.py` | inte gjord |
| LX-014 | Den öppna demon har en fast uppsättning sektioner och leder gamla adresser rätt. | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |
| LX-015 | Besökaren ser Duo-översikten (båda agenterna) på exempeldata. | Utanför `/crm` (publik demo); beslut Anton | 5 | behövs ingen (klient) | inte gjord |

## Nya mönster som måste byggas

Verktygslådan (`components/crm/app/kit.tsx`, `Sida.tsx` och de fem mönstervyerna) bär det
mesta: av 1 306 rader är 422 "ingen egen vy", 38 ligger utanför `/crm`, och av resten
byggs alla utom 275 helt med BolagVy, BolagPanel, BolagFormular, OversiktVy och SynkVy. Det som inte går att bygga med dem står
nedan. Enligt `DESIGN-CRM.md` utökar ett nytt mönster verktygslådan i samma form (radier,
chips, piller, tokens), och det byggs en gång och återanvänds.

| Mönster | Vad som saknas i dag | Rader som behöver det | Utgångspunkt |
|---|---|---|---|
| Tråd- och inkorgsvy | Lista till vänster och öppen tråd till höger (på mobil: listan, sedan tråden), meddelanden i tidsordning med avsändare och tid, steg som piller, svarsruta med utkastet nederst, oläst-markering, den öppna tråden i adressen | LU-001–LU-021, LU-081, LU-089, OV-105, SU-010–SU-045 (ärendeinkorgen), SU-101–SU-104, SU-207–SU-211 (överlämnade chattar) | Twentys mejlvy (`twenty-05`), Astryx `Layout` och `List` |
| Utkastredigerare | Ämne och text som går att redigera, signatur, logga och lagstadgad fot som mottagaren ser dem, spara före godkänn, struktur A/B, handlingskontrollen före Skicka, Skriv om med önskemål, provmejl, förlopp medan Iris skriver | LR-065–LR-075, LU-013–LU-017, LU-033–LU-038, LK-034–LK-038, AP15, SU-021–SU-025 | Dagens `components/email/EmailStudioEditor.tsx` (beteendet), Astryx `TextArea` och `Card` |
| Uppladdning och import i steg | Fil in (dra och släpp, välj), kolumnkoppling med förslag, värdekontroll, granskning mot kunder, leads och spärrar, import i satser med förlopp och kvitto | LK-100–LK-106, LK-143–LK-147, LR-122, LR-133, SU-121, IN-031, KV-26–KV-28 | `lib/leads/importfil.ts`, `importmallar.ts`, `importrader.ts` (återanvänds, byggs inte om; app-04 punkt 11), `twenty-09` |
| Tidslinje på posten | Händelser (utkast, utskick, svar, samtal, uppföljning, statusbyte, ärenden) och anteckningar och uppgifter i en tidsordnad flik i BolagPanel, med skrivfält | LR-069, LU-137, LU-170, LU-171, AP100, AP103; fas 3:s tidslinje och objekt | `twenty-03` (postsida, tidslinje, anteckningar, uppgifter) |
| Chattvy | Meddelandebubblor, skeden medan jobbet går (pollning), kallstart, bild som bilaga, tumme upp och ned, förslag i flödet, felbesked för människor | SU-007, SU-070–SU-087 (testchatten), KV-60–KV-64 (kvitto-assistenten) | Dagens `SupportChat` (beteendet), Astryx `Card` och `TextArea` |
| Förhandsgranskning med versioner | Fritext in, förhandsgranskning av hur den bakas in, godkänn och spara, historik och återställ | IN-061–IN-063, IN-108, IN-135–IN-137, SU-151, SU-152, SU-216, AD-110–AD-115 | Astryx `Dialog` med `Layout`, sida vid sida på bred skärm |
| Kö med grupper och åtgärd i raden | Flera köer på en sida (per agent), räknare och åldershinkar ovanför, åtgärd direkt i raden (godkänn, bocka av, ta över), detalj i panel | OV-060–OV-079, KV-170 | BolagVy-raden plus Astryx `Badge` och `StatusDot` |
| Notislista | Klocka i sidhuvudet med olästräknare, lista över svar, utkast och möten, markera lästa, räknare på menyposten | SK-064, SK-171, LR-004, LR-005, LU-022, LU-023, AD-005 | Astryx `Popover`/`HoverCard` och `Badge` |
| Banderoll | Fast rad överst i bladet för kundbesök ("Du testar som"), läsroll och demo | SK-076–SK-079, AD-009 | Astryx `Banner` i Snajps tokens |
| Stegguide | Steg med framsteg, validering per steg, fortsätt och tillbaka | SK-110–SK-127 (onboardingen), SU-161–SU-163 och IN-072–IN-075 (koppla inkorg) | BolagFormular i en `Layout` med stegrad |
| Inställningsskal | Grupperad undermeny för `/crm/installningar`, sektionsgrind på servern, titel och beskrivning per sektion | IN-001–IN-018 | Twentys inställningssidor (`twenty-12`), `Sida` |
| Sparade vyer | Spara, välja och ta bort en vy (filter och sortering) i vyraden | LR-035, AP104 | Twentys vyer (`twenty-02`), `SegmentedControl` i vyraden |
| Redigerbara celler | Ändra status, anteckning och datum direkt i tabellen, med varning för dubbletter | LK-117, LK-148–LK-151 (säljlistan), LR-039 (status i raden) | Twentys tabell (`twenty-02`) |
| Tavla (kanban) | Leads per status som kolumner (pipelinen) som alternativ vy; samma tavla behövs för fas 3:s affärer | LR-033 (som alternativ), fas 3 Affärer med tavla | `twenty-02`, Astryx förhandsutgåva om den bär |
| Stegspår för en körning | En körnings steg i ordning med utfall, grindar och var den stannade | AD-084, AP123, LK-027 (live) | SynkVy:s förloppsrader utökade |
| Flödeskarta och lagerstapel | Playbooks som banor med steg och kodgrindar, promptens lager, källmatris | AD-070–AD-076 | Ingen förebild; ren SVG i tokens |
| Frågeruta med regelbaserat svar | Fråga om siffrorna i admin-översikten | AD-026 | Astryx `TextInput` och `Card` |

## Ordningen

Byggarna går i följd (planens avsnitt 5), så ordningen avgör hur tidigt något går att
pröva. Principen: först det andra vilar på (grindar, skal, mönster), sedan den yta som
återanvänder mest av det som redan finns, och sist det som läser allt annat (översikter).

### Före fas 4: det fas 3 måste lämna

1. **Besluten i `upptagna`** (LK-107, LK-108): tidigare kunder fria för Iris och
   uteslutning på nummer. Annars bygger Leads i CRM:et på fel mängd.
2. **CRM-tillägget som grind** och **samlad kundlista** (Bolag med segmenten Egna och Iris;
   OV-103, OV-104, LR-133, LK-147). Annars har Leads ingen plats att lägga bolagen i
   `/crm/bolag`.
3. **Tidslinjen och objekten** (anteckningar, uppgifter; LR-069, AP100, AP103): leadets
   panel och konversationerna skriver dit.

### Fas 4: Leads, i den här följden

| Steg | Del | Beror på | Varför här |
|---|---|---|---|
| 4.1 | Skalets förutsättningar: gruppen Iris i sidofältet, banderollen, notisräknaren, läsroll och kundbesök i `app/crm/layout.tsx`, felgräns och laddning (SK-038–SK-045, SK-064, SK-074–SK-079, SK-155–SK-157) | – | Varje vy efter ärver grindarna; utan dem skriver ett kundbesök skarpt |
| 4.2 | `/crm/iris/leads` med panelen (LR-030–LR-075, LR-090–LR-097) | 4.1, fas 3 punkt 2 | Mest återbruk av BolagVy och BolagPanel; grunden som körningar, utkast och listor öppnar poster i. Webbgrinden byggs här en gång |
| 4.3 | Utkastredigeraren (nytt mönster) och `/crm/iris/utkast` (LU-030–LU-070, LU-080–LU-088, LU-150–LU-159, LU-172–LU-183) | 4.2 | Panelen, körningarna och konversationerna använder samma redigerare |
| 4.4 | `/crm/iris/korningar` och Kör Iris (LK-001–LK-057, LK-135–LK-138) | 4.2, 4.3 | Körningens leads och utkast öppnas i panelen och redigeraren; SynkVy bär förloppet |
| 4.5 | `/crm/installningar/iris` (LK-060–LK-073, IN-100–IN-112) | 4.4 | Körningen läser profilen och automationen; byggs bredvid men behöver inställningsskalet (kan byggas utan det i en enkel sida och flyttas in i fas 5) |
| 4.6 | Tråd- och inkorgsvyn (nytt mönster) och `/crm/iris/konversationer` (LU-001–LU-024, LU-110–LU-122) | 4.3, fas 3 punkt 3 | Återanvänds av Kundtjänst i fas 5 |
| 4.7 | `/crm/iris/uppfoljningar` och `/crm/iris/samtal` (LU-100–LU-107, LU-130–LU-138, LU-170, LU-171) | 4.6 | Små listvyer på BolagVy; utfallen skriver till tidslinjen och tråden |
| 4.8 | `/crm/iris/listor` med import och säljlista (LR-120–LR-135, LK-100–LK-118, LK-142–LK-151) | 4.2, 4.3 | Importen är ett nytt mönster som också Kundtjänst och Kvitton behöver |
| 4.9 | `/crm/iris/kampanjer` (LU-160–LU-162) | 4.8 | Kampanjer går till listor |
| 4.10 | `/crm/iris` Iris-översikten (LR-020–LR-027, OV-031–OV-037, LU-024, LU-032, LU-174) | allt ovan | Läser alla andra; byggs sist så att talen säger samma sak som listorna (LR-021) |

### Fas 5: resten, i den här följden

| Steg | Del | Beror på | Varför här |
|---|---|---|---|
| 5.1 | Inställningsskalet och alla sektioner (IN-001–IN-146, SU-120–SU-168 i inställningsdelen) | 4.1 | Kundtjänst och Att göra länkar till reglerna och inkorgarna |
| 5.2 | `/crm/kundtjanst` med Ärenden, Testmail, Dolda (SU-001–SU-064) | 4.6, 4.3, 5.1 | Återanvänder trådvyn och redigeraren |
| 5.3 | Testchatten (chattvyn) och Överlämnade (SU-070–SU-110, SU-207–SU-213) | 5.2 | Chattvyn byggs här och återanvänds av Kvitton |
| 5.4 | `/crm/att-gora` (OV-060–OV-079) | 4.3, 4.6, 5.2 | Kön samlar Iris och Kundtjänst; byggs när båda finns |
| 5.5 | `/crm/larande` (OV-080–OV-091) | 5.2 | Förslag från båda agenterna |
| 5.6 | `/crm` Översikt utökad med agentavsnitten och Kom igång (OV-020–OV-048, SU-126, SU-190) | 4.10, 5.2 | Läser allt |
| 5.7 | `/crm/kvitton` (KV-01–KV-208) | 5.3, importen ur 4.8 | Vilande produkt, bara plattformsadmin; därför sent |
| 5.8 | Plattform: `/crm/admin`, Kunder, Paket, Logg (AD-001–AD-152) | 4.1, 5.1 | Plattformsadmin använder i övergången dagens `/admin` |
| 5.9 | Inloggning, återställning och onboarding i CRM:ets form (SK-020–SK-048, SK-110–SK-138, SK-175–SK-188) | 5.1 | Egna sidor utanför skalet; dagens fungerar tills växlingen |
| 5.10 | Luckorna: demon, Duo-demon, demobokningen (LX-001–LX-015), efter Antons beslut | – | Publika sidor; påverkar inte kunderna |

## Sekretess

### Reglerna som gäller varje ny vy

1. **Webbplatsbedömningen** (webbrevision, webbnivå, betyg, brister, platshållarskäl,
   webbpoolens listor och `lan`) syns bara där backendens grind `webbpool.far_se` släpper
   fram den. Det nya gränssnittet räknar aldrig ut den själv och visar en kolumn, ett
   filter, en sortering, en diagramserie, en tooltip eller en panelflik om bedömningen
   **bara när svaret bär fälten**. Saknas fältet finns inget val att visa, inte heller i
   sparade vyer, CSV-export, kopiering till en annan kund, kommandopaletten eller ett
   utkast. Varje ställe som visar eller skickar vidare bedömningen grindas i samma ändring
   (CLAUDE.md, INV-SEC-008).
2. **En öppen fråga för Anton (E1 i `app-99`):** koden grindar på arbetsytans slug, inte på
   rollen. Plattformsadmin ser i dag bedömningen bara i en arbetsyta som står i listan och
   i kundbesök hos webbyråerna; CLAUDE.md säger "bara för plattformsadmin och kunderna Umeå
   Webdesign och Alunix". Det nya gränssnittet ska följa koden tills Anton avgjort, och
   besluten skrivs i `docs/BESLUT.md`.
3. **En läcka att rätta före fas 4 (LR-128):** servern tar bort `webbniva` och
   `webbrevision` för övriga kunder, men webbpoolsradens `signal_detalj` bär samma bedömning
   i klartext ("Akut · modernitet 3/10 …", `webbpool._signal`). Grinden måste omfatta
   `signal_detalj` innan listvyn i CRM:et visar signalen.
4. **Driftdata (E3):** supportöversiktens svar bär `drift` (tokens, cacheandel, modell) till
   varje kund; bara vyn är grindad (SU-063, AD-138). Grinda i backenden på plattformsadmin
   innan CRM:ets kundtjänstöversikt läser ändpunkten.
5. **Plattformsadmin:** gruppen Plattform, Byt kund, Admin/Demo, driftkorten, flytt till
   main, kopiera lista till kund, bakåtfyllnad och ombedömning grindas på servern
   (`getPlatformAdmin`, master-nyckeln bakom serveråtgärder). Att menyn döljer dem är
   hövlighet, inte grind (SK-038, AD-001).
6. **Läsrollen** ärver proxyns 403 på varje skrivning; vyerna stänger av skrivande
   knappar med en förklaring i stället för att låta anropet falla (SK-039, SU-200).
7. **Kundbesök** märker varje skrivning `is_test` i proxyn och visar banderollen; det nya
   skalet får aldrig gå förbi proxyn (SK-092, AP1).
8. **Tillägg och produkter:** `leadlists` för beställning och säljlista, `bookkeeping` för
   Kvitton (vilande), CRM-tillägget för Bolag, Personer, Synk och Utvecklare (fas 3).
   Grinden sitter i servern och i varje serveråtgärd (LK-151).
9. **Hemligheter** visas aldrig: sessionsadressen `…@session.snajp.se`, app-lösenord för
   inkorgar, kanal- och integrationshemligheter, tvåfaktorns hemlighet. En CRM-nyckel och
   återställningskoderna visas en enda gång.
10. **Kundisolering och DeepSeek** gäller oförändrat: kunden härleds ur sessionen i varje
    anrop, och ingen ny väg skickar kunddata till DeepSeek.

### Raderna som rör webbplatsbedömningen

Hittade med sökord (webbrevision, webbnivå, webbpool, bedömningen, `far_se`, län,
INV-SEC-008, webbyrå) i radens alla kolumner. Några träffar nämner bedömningen bara för att
säga att den inte förekommer; de står med så att ingen behöver leta igen.

| ID | Funktion | Plats | Hur den grindas i dag (läsarens rollkolumn) |
|---|---|---|---|
| OV-037 | Tabellen "Alla Iris-körningar" med styrning. | `/crm/iris` (ny) Iris-översikt och `/crm/iris/korningar` · OversiktVy + SynkVy | Kund med leads; webbpoolens länfördelning syns aldrig här |
| LR-121 | Se sina listor | `/crm/iris/listor` (ny) · BolagVy | kund |
| LR-123 | Kombinera listor | `/crm/iris/listor` (ny) · BolagVy | kund |
| LR-125 | Filtrera och sortera en lista | `/crm/iris/listor` (ny) · BolagVy | kund; webbnivå bara de som får se webbbedömningen |
| LR-126 | Öppna en listrad som lead | `/crm/iris/listor` (ny) · BolagVy | kund |
| LR-128 | Radens signal | `/crm/iris/listor` (ny) · BolagVy | webbnivå/modernitet: bara plattformsadmin, Umeå Webdesign, Alunix. OBS: servern tar bort `webbniva`/`webbrevision` för övriga, men webbpoolsradens `signal_detalj` är samma bedömning i klartext ("Akut · modernitet 3/10 · brist", `webbpool._signal`) och tas INTE… |
| LR-129 | Ladda ner en lista som CSV | `/crm/iris/listor` (ny) · BolagVy | kund |
| LR-131 | Kopiera eller flytta en lista till en annan kund | `/crm/iris/listor` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | bara plattformsadmin |
| LR-132 | Fält som med flit INTE följer med en kopierad lista | `/crm/iris/listor` (ny) · TableSelectionToolbar, åtgärden bara för plattformsadmin | regel INV-SEC-008 och Antons beslut 2026-10-08 |
| LR-134 | Listans rader läses med utkaststatus och bestående förlopp | `/crm/iris/listor` (ny) · BolagVy | kund |
| LR-090 | Se webbplatsens betyg i Iris-listan | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | Bara kunder som får se bedömningen (se LR-091) |
| LR-091 | Servern döljer bedömningen för alla andra | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | Plattformsadmin ser den bara via en kund som får se den (grinden går på kunden, inte på rollen; se Oklarheter) |
| LR-092 | Webbnivå och län i listor | Alla Iris-vyer: kolumn och panelflik bakom grind · BolagVy + BolagPanel | webbyråerna och plattformsadmin; se Oklarheter om `lan` |
| LR-081 | Se träffarna | Kommandopalett (befintlig), grupp Leads · Kommandopalett | kund |
| LK-033 | Körningens arbetsminne lämnar aldrig API:t | `/crm/iris/korningar` (ny) och `/crm/iris/korningar/[id]` · BolagVy + SynkVy | webbpoolens län: bara plattformsadmin och webbyråkunderna |
| LK-042 | Tratten: förfilter, existens, Jev, research | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/ko… | – |
| LK-049 | Webbpoolen startas efter körningen | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/ko… | osynligt för källkunden |
| LK-050 | Prospekt ur en kandidat | Ingen egen vy: under ytan, oförändrad backend; syns som förlopp och utfall i `/crm/iris/ko… | – |
| LK-141 | Platshållare och avvecklade sajter känns igen | Ingen egen vy: under ytan, oförändrad backend; syns som skäl i körningens Bortvalda · Synk… | platshållarskälet är del av den hemliga bedömningen |
| LK-107 | Befintliga kunder utesluts överallt | Ingen egen vy: under ytan, oförändrad backend; ändras i fas 3 enligt besluten 2026-11-26 | kund |
| LK-112 | Listbygget matar webbpoolen | `/crm/iris/listor` (ny) · BolagVy + SynkVy | osynligt för källkunden |
| LK-114 | Processa om en lista | `/crm/iris/listor` (ny) · BolagVy + SynkVy | kund; ombedömningen styrs av KUNDEN (`webbpool.far_se` på arbetsytans kund), inte av rollen: plattformsadmin i ett kundbesök får samma som kunden |
| LK-120 | Webbrevision av ett bolags startsida | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | resultatet hemligt |
| LK-121 | Fyra webbnivåer, inget gränsfall (regel 18) | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | hemligt |
| LK-123 | Webbpoolen samlar varje körnings bolag | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | ingen kund ser poolen direkt |
| LK-124 | Bedömning efter körningen | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | – |
| LK-125 | Fördelning efter län (regel 20) | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | bara mottagarna och plattformsadmin |
| LK-126 | Bakåtfyllnad av gamla leads (plattformsadmin) | `/crm/admin/kunder` (ny) åtgärd, bara plattformsadmin · BolagFormular + SynkVy | bara plattformsadmin |
| LK-128 | Förhandsvisning av en webbpoollista | Ingen egen vy: under ytan, oförändrad backend; i vyerna bara bakom grinden (se Sekretess) | utvecklare |
| IN-166 | Agenten använder integrationerna under ett ärende. | Ingen egen vy: under ytan, oförändrad backend | Kunddata stannar hos kunden; inget här rör webbplatsbedömningen |
| AD-055 | Det flyttade blir skarpt i main, med bedömning och väntande utkast. | `/crm/admin/kunder/[id]` (ny) fliken Flytt till main och TableSelectionToolbar i `/crm/iri… | Bara admin. Webbplatsbedömningen följer med inom samma kund, aldrig till en annan. |
| AD-120 | Grinden för webbplatsbedömningen. | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | HEMLIG: bara de synliga arbetsytorna. Allt nytt som visar eller skickar vidare bedömningen ska grindas här. |
| AD-121 | Webbpoolen: varje körnings bolag bedöms och fördelas tyst till webbyråerna. | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | Mottagarna ser sina listor; ingen annan kund märker något. |
| AD-122 | Bakåtfyllnad av webbpoolen för alla kunders gamla leads (ingen yta). | Ingen egen vy: under ytan, oförändrad backend; åtgärderna bara för plattformsadmin | Bara master-nyckel. |
| AD-123 | Kopiera eller flytta en färdig leadslista till en annan kund. | `/crm/iris/listor` (ny) · TableSelectionToolbar, bara plattformsadmin | Bara plattformsadmin; källkunden härleds ur sessionen. |
| AD-130 | Händelseloggen som spårbarhet för varje adminskrivning. | `/crm/admin/logg` (ny) vyn Händelser · BolagVy | Bara admin. |
| AD-143 | Fler driftkommandon utan yta (kontrolläsarens komplettering). | Ingen egen vy: under ytan, oförändrad backend (skript) | Driftägaren. |
| AP63 | Lista prospekt (leads) | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | Kund; webbfälten bara admin/webbyråer |
| AP65 | Läs ett prospekt | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | Kund; webbfälten bara admin/webbyråer |
| AP93 | Lista och läsa leadslistor | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | Kund; webbfälten bara admin/webbyråer |
| AP94 | Listrad → lead, utkast för listan, köa en rads utkast, pröva om listan | Ingen vy (ändpunkt); anropas av `/crm/iris/...` | Kund |
| AP136 | Webbpoolens bakåtfyllnad: läge och kör | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | Plattformsadmin; rör webbplatsbedömningen |
| AP138 | Kopiera eller flytta en leadslista till en annan kund | Ingen vy (ändpunkt); anropas av `/crm/admin/...` | Plattformsadmin |
| AP170 | Lösa bakgrundsuppgifter utan förloppsväg | Ingen vy (bakgrundsjobb); förlopp där jobbet startas | Webbpoolens utfall bara för admin/webbyråer |
| AP229 | Stegloggarnas texter lämnar aldrig backenden | Ingen vy (ändpunkt eller grind) | Texterna bara plattformsadmin |

### Övriga grindade rader

Hittade med sökord i läsarens rollkolumn (och för hemligheterna i hela raden). Grindas
enligt reglerna 5 till 9 ovan. Listorna är ett stöd för byggaren, inte en uttömmande
bedömning: läs läsarens rad för den exakta grinden.

- **Bara plattformsadmin eller master-nyckeln** (108 rader): SK-029, SK-038, SK-041, SK-048, SK-061, SK-065, SK-074, SK-075, SK-076, SK-092, SK-093, SK-125, SK-178, SK-179, OV-002, OV-090, LR-027, LR-048, LR-128, LR-131, LR-091, LR-094, LR-097, LK-009, LK-016, LK-033, LK-126, LK-127, LK-134, LU-066, LU-121, LU-122, LU-144, LU-181, SU-152, SU-201, KV-58, KV-91, KV-171, KV-172, KV-199, KV-204, KV-206, IN-002, IN-008, IN-017, IN-018, IN-024, IN-094, IN-095, IN-130, IN-131, IN-132, IN-133, IN-134, IN-135, IN-136, IN-137, IN-138, IN-142, AD-001, AD-002, AD-013, AD-014, AD-015, AD-049, AD-056, AD-094, AD-102, AD-117, AD-122, AD-123, AD-124, AD-125, AD-126, AD-140, AP11, AP12, AP37, AP120, AP121, AP122, AP123, AP124, AP125, AP126, AP127, AP128, AP129, AP130, AP131, AP132, AP133, AP134, AP135, AP136, AP137, AP138, AP139, AP140, AP180, AP181, AP182, AP183, AP229, AP230, AP240, LX-012
- **Läsrollen (viewer) får läsa men inte skriva** (21 rader): SK-039, SK-077, SK-120, OV-015, OV-091, LR-093, LK-117, SU-007, SU-100, SU-163, SU-164, SU-200, SU-218, IN-014, IN-020, IN-022, IN-072, IN-074, IN-076, AP9, AP13
- **Kundbesök: plattformsadmin som tittar som kund, skrivningar blir test** (18 rader): SK-074, SK-092, OV-090, LR-007, LR-120, LR-094, LK-147, LK-114, LK-117, SU-201, IN-017, IN-024, AD-008, AD-009, AD-011, AD-131, AP1, AP9
- **Grindat på tillägg eller produkt (leadlists, bookkeeping med flera)** (10 rader): LK-110, LK-117, LK-118, LK-148, LK-149, LK-150, LK-151, KV-04, AP142, AP145
- **Hemligheter som aldrig får visas eller visas en gång (sessionsadress, app-lösenord, nycklar, tvåfaktor)** (41 rader): SK-026, SK-048, SK-134, SK-177, SK-178, SK-179, LK-073, SU-070, SU-078, SU-088, SU-100, SU-105, SU-107, SU-162, SU-163, SU-164, SU-212, SU-213, SU-218, IN-073, IN-074, IN-076, IN-160, IN-161, IN-162, IN-163, IN-164, IN-165, IN-166, IN-131, IN-132, IN-133, IN-134, IN-140, AP2, AP13, AP31, AP37, AP146, AP167, AP238

## Sammanräkning per område och fas

Rader per område och fas. Alla står som inte gjord.

| Område | Fas 3 | Fas 4 | Fas 5 | Summa |
|---|---|---|---|---|
| Skal, inloggning, onboarding (SK) | 0 | 39 | 82 | 121 |
| Översikt, Att göra, Lärande (OV) | 2 | 8 | 75 | 85 |
| Leads: översikt, pipeline, bolag (LR) | 3 | 101 | 0 | 104 |
| Leads: körningar, listor, källor (LK) | 4 | 125 | 3 | 132 |
| Leads: utkast, konversationer, samtal (LU) | 0 | 128 | 1 | 129 |
| Support (SU) | 0 | 0 | 176 | 176 |
| Kvitton (KV) | 0 | 0 | 141 | 141 |
| Inställningar (IN) | 3 | 14 | 92 | 109 |
| Adminytan (AD) | 0 | 7 | 109 | 116 |
| API:t under ytorna (AP) | 11 | 58 | 110 | 179 |
| Luckorna (demo och demobokning) (LX) | 0 | 0 | 14 | 14 |
| **Totalt** | **23** | **480** | **803** | **1306** |

## Det jag inte hann läsa

- Läsarnas kolumn "Beteende och regler" är inte omläst rad för rad. Platsen är satt per
  avsnitt i läsarens fil och justerad rad för rad där funktionens rubrik visar att den hör
  hemma någon annanstans (326 avsteg). En rad vars beteende avviker från rubriken kan
  därför ha fått avsnittets plats; byggaren läser läsarens rad innan vyn byggs.
- Backendkolumnen är läsarens första ändpunkt, funktion eller tabell, inte en egen kontroll
  i koden. "finns" betyder att läsaren belagt en väg, inte att den räcker för det nya.
- Inget i koden är öppnat av sammanställaren; allt bygger på `app-01` till `app-10`,
  `app-99`, `DESIGN-CRM.md`, `PLAN-MIGRERING.md` och `docs/BESLUT.md` 2026-11-26.
- Läsarnas egna luckor står kvar (se `app-99` "Det jag inte hann läsa"): `support-webb`,
  delar av `support_agent.py` och `processor.py`, `discovery.py` och Jev i detalj,
  `tilltal.py`, `send_provider.py`, `granskning.py` i mitten, `insyn.py`.

## Oklarheter

Sådant som bara Anton kan avgöra eller som måste prövas i den körande appen.

1. **Webbplatsbedömningen per roll eller per arbetsyta** (E1). Se Sekretess punkt 2.
2. **Driftdata i supportöversiktens svar** (E3). Grinda i backenden före fas 5.2?
3. **Två "vy"-begrepp för Team** (E6): serverns `aktivVy()` och `SettingsNav` säger olika
   om vem som ser Team. Det nya inställningsskalet måste välja ett.
4. **Två kostnadsmodeller** (E7): kronor ur tokens i översikten, USD på Vertex-listpris i
   adminytan. Vilken ska CRM:ets översikt och adminlogg visa?
5. **Lärande i menyn?** Den står inte i dagens meny. Förslaget ovan sätter den under
   Arbetsyta.
6. **Assistent- och Analysvyerna** (OV-101, OV-102) är förhandsvyer utanför menyn. Förslaget
   tar med Analys som ett kort och lämnar Assistent; Anton avgör.
7. **Den gamla bokföringsytan** (KV-150–KV-153, SIE4 och avstämning) har ingen vy i dag.
   Ska den få en i `/crm/kvitton`?
8. **Supportportalen `support-webb`**: ska Överlämnade, Kanaler och Integrationer flytta in i
   CRM:et och portalen läggas ner, eller leva sida vid sida?
9. **CRM-kundlistan in i CRM:ets bolag** (LR-133, LK-147): dagens uppladdade lista
   (`lead_lists.kalla='crm'`) och CRM:ets bolag är två register för samma sak. Ska listan
   flyttas över i fas 3, och hur hålls de isär från Iris-kunderna (beslutet 2026-11-26:
   separata nu, samlad lista senare)?
10. **`/demo/crm` och demoförfrågningarna** (LX-001–LX-013, `app-99` oklarhet 1 och 2).
11. **Pipelinen som tavla**: dagens Pipeline är en statusremsa. Ska `/crm/iris/leads` få en
    tavla som alternativ vy, när fas 3 ändå bygger tavlan för affärer?
12. **Kunderna och CRM:et**: länken syns bara för plattformsadmin. När kunderna får Iris i
    CRM:et i stället för i `/dashboard/leads` avgörs i fas 6.
