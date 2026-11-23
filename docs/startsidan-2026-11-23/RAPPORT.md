# Demo för Buddy AB (Henrik)

Arbetsgren: `buddy-demo-prep`, utgår från `origin/development` vid `15227ef4` (2026-11-23).
Inget är pushat och inget rör `main`.

Dokumentet fylls på i den ordning arbetet görs. Avsnitt som ännu inte är klara är märkta **ej klart**.

## 1. Kartläggning (läst ur koden innan något ändrades)

### 1.1 Uppdragsbeskrivningen stämmer inte med koden på sex punkter

| Uppdraget säger | Koden gör |
|---|---|
| Vercel-frontend, Supabase-databas | Allt går på Railway (web, api, Postgres). Vercel är avvecklat och Supabase får inte skrivas till (`CLAUDE.md`, `DEPLOY.md`). |
| Registrering → verifiering → inloggning | Det finns ingen e-postverifiering. Kontot bekräftas direkt och användaren landar på `/onboarding` (`lib/actions/auth.ts:171-207`). |
| Fälten `icp_reason`, kontaktroll och datakälla på leadet | Fältet heter `motivering` (plus `score_breakdown` med belägg). Kontaktperson och roll visas inte i leadrutan. Källan visas som länklista, inte som en etikett. |
| Email Studio-knappen "Tydligare CTA" | Finns inte (bara i en designskiss). "Mer personlig" finns i supportinkorgen; på Iris utkast heter den "Personalisera". Övriga sex knappar finns. |
| `tests/e2e/buddy-journey.spec.ts`, Playwright | Repot har ingen Playwright-uppsättning: inget `playwright.config`, ingen `tests/e2e`, och Playwright är med flit inte ett beroende. Kundresor besiktigas i dag av fristående skript (`scripts/qa_ny_kund.mjs`, `qa_kundresa.mjs`, `qa_vyer.mjs`). |
| Sidorna Priser, Dataskydd, Kontakt | Priser är ankaret `/#priser`, Dataskydd är `/integritetspolicy`, kontakt är `mailto:` i sidfoten och `/boka-demo`. |

### 1.2 Arkitekturen i korthet

- **Webb:** Next.js 16 (app router) i repots rot. Auth.js v5 med JWT-cookie, ingen Redis på webbsidan. Databasrollen `snajp_web` kör under RLS.
- **Backend:** FastAPI i `snajp-support/`. Alla inloggade anrop går via Next-proxyn `app/api/snajp-support/[...path]` som sätter kundens API-nyckel ur sessionen (`proxyAsTenant`). Backendrollen `snajp_app` kör under RLS med `app.tenant_id`.
- **Tenant:** arbetsytan (`workspaces`) skapas av en trigger vid registreringen. Backendens tenant (`ss_tenants`, slug `kund-<8 tecken>`) skapas först när onboardingen skickas in.
- **Miljöer:** `main` (snajp.se, produktion) och `development` (spegel av produktionen, riktig kunddata). Development mejlar aldrig leads: spegelmarkören `envags` stoppar sändaren (`scheduler.py:683-700`).

### 1.3 Kundresan: registrering till arbetsyta

- `/login?mode=signup` → namn, e-post, lösenord (minst 8 tecken) → `/onboarding`.
- Onboardingen har **fem** steg: Företaget, Bransch, Kontaktperson, Målgrupp, Paket (`components/auth/OnboardingWizard.tsx`). Tonläge och integrationer frågas inte; röstdokumentet skrivs som utkast och inkorgar kopplas efteråt under Inställningar.
- Inget sparas förrän sista steget skickas in. **En omladdning mitt i flödet börjar om från steg 1.**
- Inskicket skapar tenanten, fyller standardinställningar (produkttext, röstdokument, målgrupp, erbjudanden), fyller kundregistret och startar en webbplatsskanning för kunskapsbasen. Det tar omkring 14 sekunder.
- Gratisperioden finns bara som ett datum (`workspaces.trial_slut`, två månader fram) och två påminnelsemejl. Ingenting spärras när den går ut; det gör en admin för hand.
- Paketet styr vilka agentflikar som är tända. Byta paket kan kunden inte göra själv, trots att onboardingen säger det: `/settings/billing` har bara mejllänkar.

### 1.4 Iris

- "Kör Iris" → `POST /api/leads/runs/batch` → registerfilter (allabolag) → eventuell Jev-klassning → kontaktsökning på bolagets sajt → research → utkast. Motorn fortsätter tills beställt antal **leverbara** leads finns, högst tolv undersökta per beställt lead.
- Förloppet visas i formuläret och på fliken Körningar och överlever omladdning (körningen sparas i Postgres, id:t i `localStorage`).
- En ny kund måste ha produkttext (minst 120 tecken) och målgrupp; onboardingen fyller båda.
- **Utskick:** bara "Kör Iris" kan aldrig mejla någon; utkasten väntar på granskning och autonoma utskick är avstängda. Men **"Godkänn och skicka" i produktionen skickar ett riktigt mejl direkt**, vardagar 08–16, från Snajps adress, utan bekräftelseruta på enskilda utkast och utan att en inkorg är kopplad. I development skickas aldrig något.
- Det finns ingen brytare som leder om alla mejl till en testadress. Den enda globala torrkörningen är `SNAJP_OUTBOX_DIR`.
- Kostnadsskydd: dygnsbudget per kund (40 M tokens, kontrolleras bara vid start), tak per körning, inget samtidighetslås per kund. Google Cloud-taket 8 000 kr/månad pausar Vertex för **alla** kunder i båda miljöerna.

### 1.5 Supportagenten

- Kunskapsbasen fylls under Inställningar → Kunskapsbas (klistra in, textfil, eller förslag från webbplatsskanningen). En ny kund börjar med **tom** kunskapsbas.
- Chatten är inte strömmad: 202 plus pollning med fastext ("Läser din fråga", "Söker", "Skriver"). Fem till nio modellanrop per svar, typiskt 15 sekunder.
- Överlämning avgörs i kod (INV-ESC-001). Tom kunskapsbas ger en förtydligande fråga, sedan överlämning efter två varv, eller "har inte den uppgiften" med ett fast erbjudande om en kollega.
- Testchatten finns på `/dashboard/support`, fliken Testchatt.
- **En självregistrerad kund har ingen publik chatt och ingen widget.** Det kräver en konfigurationsfil i `lib/tenants/`, en nyckel i miljön och en deploy. Den anonyma chattproxyn faller dessutom tyst tillbaka på demonyckeln för en okänd kund.

### 1.6 Startsidan (snajp.se)

- `app/page.tsx` → `ProductPage` → `LandingPhoto` (klientkomponent) med `useLandingMotion`: GSAP 3.15 och Lenis, laddade dynamiskt efter hydrering.
- All scroll ägs av Lenis på huvudtråden. Ljusmotorn skriver bakgrundsfärg på två fasta helskärmslager varje scrollbildruta, och över sextio ScrollTrigger- och SplitText-instanser uppdateras per bildruta.
- Fotona är vanliga `<img>` utan `srcset`; `haga.webp` är 524 kB. Statiska filer serveras med `Cache-Control: public, max-age=0`.
- Rotlayouten läser `headers()` och `cookies()`, så varje sida renderas på servern per förfrågan.
- Inga tredjepartsskript. `SupportChat` gör ett backendanrop vid varje sidvisning av startsidan.

### 1.7 Vad som var trasigt eller riskabelt före ändringarna

Rangordnat efter hur illa det slår i en genomgång.

1. **Ett klick på "Godkänn och skicka" i produktionen mejlar ett riktigt bolag.** Ingen bekräftelse på enskilda utkast.
2. **Startsidan tappar bildrutor vid scroll** (mätt, se avsnitt 3).
3. **Råa fel och utvecklartext kan nå kunden:** `str(exception)` i körningsfel (`leads.py:204`), "DEEPSEEK_API_KEY … Se DEPLOY_KEYS.md" (`leads.py:311`), "[object Object]" när en kunskapsbastext är för lång (`Kunskapsbas.tsx:274`), statuskoder i felrader, Postgres-feltext i onboardingen (`onboarding.ts:383`), driftinstruktioner ur `SnajpTenantError`.
4. **Testchatten för en ny kund visar Nordlys e-handelsfrågor som förslag** och rubriken "Snajp Support".
5. **Testarbetsyta ger 20 modellanrop per timme**, alltså ungefär tre chattfrågor. Buddy får inte skapas som testarbetsyta.
6. **Testchatten delar en identitet per flik:** en överlämning låser chatten i överlämnat läge i 24 timmar.
7. **Onboardingen tappar allt vid omladdning**, och texten om paketbyte stämmer inte.
8. **Lokal helstack går inte att resa på den här maskinen:** Postgres saknar pgvector, Docker kräver WSL som inte är installerat.

## 2. Vad som ändrats

**Ej klart.**

## 3. Prestanda före och efter

**Ej klart.** Mätskripten: `scripts/mat_startsida_scroll.mjs` och `scripts/mat_startsida_lighthouse.mjs`, alltid mot produktionsbygget.

## 4. Körschema för genomgången

**Ej klart.**

## 5. Plan B

**Ej klart.**

## 6. Öppna punkter och platshållare

**Ej klart.**

## 7. GO / NO-GO

**Ej klart.**
