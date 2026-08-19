# Inställningar, navigation och isolerade testkunder

2026-08-19. Underlag: adminytan mot `railway-development`, skärmdump av
kundtjänstvyn där sex av sex ärenden var eskalerade.

Planen täcker tre saker som hänger ihop mer än de ser ut att göra:

1. **Navigationen** — vad som är startsida, vad som är inställning, och varför
   dagens uppdelning blir ogenomtränglig för en kund med båda paketen.
2. **Inställningarnas struktur** — förslaget, med motivering per flytt.
3. **Testkundernas isolering** — en kunskapsbas per testkund, och en profil som
   följer med vid konvertering.

---

## 1. Det som är trasigt idag

| # | Symtom | Orsak i koden |
|---|---|---|
| A | I adminytan försvinner plattformsflikarna när man klickar **Inställningar** | `AdminShell.tillAdminväg()` lämnar `/settings` orörd. `/settings` renderar `AppShell`, alltså KUNDENS skal. Admin ramlar ur adminytan. |
| B | **Röst och tonläge** under Leads-agenten leder till översikten | Gruppen "Leads-agenten" blandar två ytor: `/settings/soul` och `/dashboard/leads/kontroll`. Den senare är en `/dashboard/*`-väg, och `app/dashboard/layout.tsx` skickar plattformsadmin rakt till `/admin`. En inställningslänk som lämnar inställningarna kan inte bli rätt på båda ytorna. |
| C | **Arbetsytan** under Inställningar visas för supportkunder | `settingsGroups` lägger den under `product: "shared"`. Innehållet (ICP, erbjudande, CTA) är leads-agentens indata. |
| D | Sex av sex ärenden **Eskalerat** | `processor.py` steg 2: `not articles` → tvingad eskalering. Testkundernas delade KB matchar inte deras mail, alltså noll träffar, alltså eskalering på allt. Symtomet är KB-delningen, inte pipelinen. |
| E | **Hämta testmail** ger samma sex mail, staplade | `build_mock_emails()` returnerar en fast lista; endpointen lägger till, rensar aldrig. |
| F | **Discovery** under Leads är helt statisk | `LeadsView` renderar `lib/mock-data.ts`. Knappen "Kör discovery" går till assistentvyn, som också är mock. |

---

## 2. Navigationen

### Principen

En kund ska ha **en startsida som är arbetet**, inte en sammanfattning av
arbetet. Dagens `/dashboard` ("Min arbetsyta") är en mock-panel med
"Veckans läge" ovanför de riktiga vyerna — den lägger ett steg mellan kunden
och det de loggade in för att göra.

### Förändringen

| Kundtyp | Startsida idag | Startsida efter |
|---|---|---|
| Bara Leads | Min arbetsyta (mock) | **Översikt** = leads-vyn |
| Bara Support | Min arbetsyta (mock) | **Översikt** = kundtjänstvyn |
| Båda | Min arbetsyta (mock + båda) | **Översikt** = båda, styrt av scope-växeln |

- Flikarna "Leads" och "Kundtjänst" finns kvar **bara** för duo-kunder — för
  en enproduktskund är de samma sida som Översikt, och två flikar till samma
  vy är en gissningslek.
- "Min arbetsyta" (den gamla översikten) flyttas i sin helhet till
  `/settings/arbetsyta`. Den är en sammanfattning, inte ett arbetsläge.
- Adminytans arbetsytesrad byter etikett `Min arbetsyta` → `Översikt`, och
  pekar på `/admin/arbetsyta` som förut.

---

## 3. Inställningarna — förslaget

### Varför dagens struktur inte håller

Sex sidor grupperade i tre rubriker, där grupperingen är **vem som använder
inställningen** (Allmänt / Kundtjänstagenten / Leads-agenten). Det låter rätt
tills en kund har båda paketen: då står "Arbetsytan" (som i praktiken är
leads-ICP), "Röst och tonläge" (som styr leads-mejl) och "Inkorgar" (som styr
supportmail) i tre olika grupper, medan **kunskapsbasen** — det enda båda
agenterna faktiskt delar — inte har någon sida alls.

Dessutom pekar en av posterna ut ur inställningarna (`/dashboard/leads/kontroll`).

### Föreslagen struktur

```
Inställningar
├── Arbetsytan               (delad)
│   ├── Företaget            org.nr, webbplats, kontaktuppgifter
│   ├── Min arbetsyta        ← flyttad hit från /dashboard
│   ├── Team
│   ├── Plan och fakturering
│   └── Tillägg
│
├── Kunskap                  (delad — båda agenterna läser härifrån)
│   ├── Affärskontext        vad ni säljer, till vem, erbjudande, CTA
│   └── Kunskapsbas          uppladdade dokument + artiklar   ← NY
│
├── Leads-agenten            (bara leads)
│   ├── Målgrupp och urval   ← flyttad in från /dashboard/leads/kontroll
│   ├── Röst och tonläge     SOUL
│   └── Autonomi             vad agenten får skicka utan godkännande
│
└── Kundtjänstagenten        (bara support)
    ├── Inkorgar             avsändaradresser, skickhälsa
    └── Regler per fack      ← flyttad in från panelen i inkorgsvyn
```

### Motivering per flytt

- **Kunskap som egen grupp.** Affärskontext och kunskapsbas är *underlag*, inte
  agentinställningar. Båda agenterna läser dem, och en kund som lagt in sina
  villkor en gång ska inte behöva göra det per agent. Det är också där
  dokumentuppladdningen hör hemma.
- **Affärskontext ut ur "Arbetsytan".** Dagens sida heter Arbetsytan men
  innehåller ICP och CTA. Namnet beskriver inte innehållet, vilket är varför
  den råkade markeras som delad.
- **Målgrupp och urval in i inställningarna.** `/dashboard/leads/kontroll` är
  en inställningssida som råkat hamna i arbetsflödet. Att den låg kvar under
  `/dashboard` är också hela orsaken till fel B.
- **Regler per fack in i inställningarna.** De ligger idag bakom ett kugghjul i
  inkorgsvyn. Regeln avgör om agenten autosvarar eller eskalerar — det är en
  policy, inte ett listfilter.
- **Grupperna filtreras på entitlement** som förut. En supportkund ser varken
  Leads-gruppen eller leads-ICP:t.

### Vad som INTE ändras

Inga sidor tas bort och ingen URL slutar fungera: gamla vägar 308:ar till de
nya. En inställning som flyttas men försvinner är värre än en som ligger fel.

---

## 4. Testkunder: isolerad kunskapsbas

### Problemet, konkret

Alla testkonton pekar på tenanten `testkund` (`lib/tenants/testkund.ts`). De
delar därmed inkorg, kunskapsbas och röstdokument. Två följder:

1. **Felsvar.** Kund A:s ångerrätt kan grunda ett svar till kund B:s kund.
   Kunskapsbasen växer med policys från olika bolag, och grundningsgrinden kan
   inte se att artikeln kom från fel företag — den ser bara en träff.
2. **Ingen konverteringsparitet.** När en testkund blir kund byter de tenant,
   och allt de konfigurerat under testet ligger kvar i den delade.

### Varför det inte löstes förut

En egen tenant krävde en configfil i `lib/tenants/` **och** en miljövariabel
för API-nyckeln (`requireSnajpTenant()` läser `process.env[tenant.supportKeyEnv]`).
Alltså en kodändring och en deploy per testkonto — precis den friktion
testarbetsytan fanns för att ta bort.

### Lösningen: tenant vid registrering, nyckel i databasen

Backenden kan redan skapa tenants i drift: `POST /api/keys` med master-nyckeln
skapar tenant + nyckel. Det som saknas är att *frontenden* kan använda en
nyckel som inte står i en miljövariabel.

```
onboarding (testkund ikryssad)
  └─> POST /api/keys (master)        skapar tenant "testkund-<ws8>"
        └─> nyckeln sparas i public.workspace_tenant_keys
              └─> requireSnajpTenant() läser env FÖRST, databasen sen
```

- **Configfilen behövs inte.** Slugar som börjar med `testkund-` härleds från
  `testkund`-mallen — samma utseende, egen data.
- **Nyckeln i databasen** ligger i en egen tabell utan läspolicy för appen;
  den läses genom en security definer-funktion, samma mönster som
  `link_testkund_workspace()` i migration 038. Motivet är detsamma: appen ska
  kunna göra EN sak, inte äga tabellen.
- **Seedning.** Varje ny testtenant seedas med en liten, sammanhängande KB
  (Snajps egna villkor) så att agenten har något att grunda i från första
  mailet. Det är också vad som gör att sex av sex inte längre eskalerar.

### Konvertering: profilen skrivs över, inte sammanfogas

När en testkund blir riktig kund körs `onboard_tenant.py` som förut och skapar
kundens egen tenant. Därefter **skrivs den nya tenantens profil över** med
testtenantens: kunskapsbas, röstdokument, affärskontext, kategoriregler och
autonomiinställningar. Överskrivning och inte sammanfogning, med flit — en
sammanfogning gör att det som fungerade i testet inte nödvändigtvis är det som
körs i drift, och skillnaden syns först när ett svar blir fel.

Riktning: `testkund-<ws> ──> kundens tenant`, en gång, vid konvertering.
Aldrig tillbaka.

---

## 5. Testmailen

- **Rotation.** En pool på ~24 scenarier i `mock.py`, uppdelade per fack.
  Varje "Hämta testmail" tar ett nytt urval — inkorgen *byts ut*, inte fylls på:
  tidigare mock-mail (provider = `mock`) rensas först.
- **Blandat utfall.** Urvalet väljs så att facken täcker regler med både
  `auto` och `draft`, och seedningen ser till att KB:n har täckning. Följden är
  en lista där agenten synligt har svarat på några, väntar på godkännande för
  andra och eskalerat de som verkligen ska eskaleras (pengar, juridik, ilska).
  Det är produktens poäng — en lista där allt är rött visar inte att den
  fungerar, den visar att den inte gör det.

---

## 6. Leads-agenten: discovery på riktigt

- `LeadsView` får samma formulär och samma alternativ som adminytans
  **Testkörningar** (bransch, geografi, roller, signaler, diskvalificerare,
  storleksspann, omfattning, antal) — samma komponent, inte en kopia.
- **Prospekt när inga finns.** Idag svarar `POST /api/leads/runs/batch` 422 om
  tenanten saknar prospekt. Två vägar in läggs till:
  1. **Exempelbolag** — agenten genererar bolag som *passar produkten* utifrån
     ICP:t. De märks som exempel (`is_example`) så att de aldrig kan
     förväxlas med ett riktigt prospekt eller mejlas.
  2. **Egna bolag** — kunden fyller i bolag de själva äger eller vill träffa,
     och de blir prospekt direkt.
- Båda vägarna körs från samma knapp: *Starta testkörning* med ifyllt formulär
  ska aldrig sluta i "Inga prospekt att köra på".

---

## 7. Ordning

1. Navigation + inställningsstruktur (frontend, ingen backend).
2. Kunskapsbas-sidan och uppladdningen på startsidan.
3. Testmail: rotation och blandat utfall.
4. Leads discovery: formulär + exempelbolag.
5. Testkundernas egna tenants + konverteringsöverskrivningen.

Ordningen är vald så att varje steg går att verifiera i previewen för sig.
Steg 5 rör migration och backend och läggs sist med flit — det är det enda
steget som inte går att ångra genom att backa en commit.
