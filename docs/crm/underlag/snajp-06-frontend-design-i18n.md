# Underlag 06: frontend, design, i18n (inför Snajp CRM)

Skrivet 2026-11-25 i worktree `claude/snajp-crm-dd0d83` (HEAD 9970d304). Allt med
`fil:rad` är **läst** i den här worktreen. Det som står under rubriker eller i
meningar märkta **Antagande** eller **Förslag** är mina slutsatser, inte kod.

Inga befintliga filer är ändrade. Inga tunga processer har körts.

---

## 0. Det viktigaste först (för den som ska bygga CRM:et)

1. **Stacken:** Next `16.4.6`, React `19.3.1`, Tailwind `^3.4.19` (v3, inte v4,
   PostCSS-plugin), TypeScript `^7.0.2`, next-auth `^5.0.0-beta.32`, lucide-react
   `^0.468.0`, recharts `^3.11.0`, gsap `3.15.1`, lenis `1.3.27`
   (`package.json:13-36`). **Inget komponentbibliotek, ingen SWR/React Query, ingen
   tailwind-merge.** Allt UI är egna klassträngar i `components/ui.tsx`.
2. **Tokens är OKLCH-tripletter** i CSS-variabler (`app/globals.css:7-79`), mörkt
   läge byter bara tokens under `:root[data-theme="dark"]` (`app/globals.css:112-169`).
   Tailwind läser dem som `oklch(var(--x) / <alpha-value>)` (`tailwind.config.ts:8-29`).
   Skriv aldrig en färg direkt i en komponent (`app/globals.css:91-92`).
3. **Appytor har EN fast typskala** (`components/ui.tsx:97-155`, DESIGN.md
   § App surfaces). `INV-UI-001` (`tests/invariants/test_inv_ui_001.py:54-60`)
   fäller `kicker`, `uppercase`, spärrning `tracking-[0.06+]`, kursiv displayrubrik
   och em-streck (U+2014) i app-ytans källa.
4. **Tvåspråkighet är en mekanisk grind** (`tests/invariants/test_inv_copy_001.py`):
   svenska bokstäver (å, ä, ö) i en sträng eller JSX-text utan att stå på en
   `sv:`/`en:`-rad fäller testet. Skuldlistan är **tom** (`test_inv_copy_001.py:172-173`).
5. **En ny `app/crm/` täcks INTE av någon av grindarna i dag.** `APPYTOR`
   (`test_inv_ui_001.py:25-50`) listar `app/admin`, `app/dashboard`, `app/settings`
   och `components/{admin,dashboard,leads,settings,kvitton,snajp,shell}`.
   `YTOR` (`test_inv_copy_001.py:46-71`) lägger till bl.a. `components/crm` (rad 58)
   men inte `app/crm`. **`components/crm` står alltså i copy-grinden men inte i
   UI-grinden.** Lägg till `app/crm` i båda listorna och `components/crm` i
   `APPYTOR` i samma commit som ytan byggs.
6. **Skyddade rutter:** proxyn (`proxy.ts:56-61`) skickar oinloggade till `/login`
   bara för prefixen i `protectedRoutePrefixes = ["/dashboard", "/settings", "/onboarding"]`
   (`lib/routes.ts:493`) och bara för sökvägar i matchern (`proxy.ts:91-105`).
   En ny `/crm` måste läggas till på **båda** ställena, och layouten måste själv
   anropa `requireOnboarded()` + `resolveDashboardState()` som
   `app/dashboard/layout.tsx` gör.
7. **Datahämtning i klienten:** ren `fetch` mot Next-proxyn
   `/api/snajp-support/<väg>` som vidarebefordrar till FastAPI `/api/<väg>` med
   tenantens nyckel ur sessionen (`app/api/snajp-support/[...path]/route.ts`,
   `app/api/snajp-support/_auth.ts:20`). Hjälparen är `leadsAnrop<T>(vag, init)`
   (`lib/leads/suite.ts:126`) eller `readJson`/`readJsonBody` (`lib/http/json.ts:67,108`).
   State med `useState`/`useEffect`, uppdatering via fönsterhändelser och
   `setInterval` (`lib/leads/konversationer.ts:240-266`).
8. **Förhandsvisning utan databas** = en klientsida under `app/forhandsvisning/<namn>/page.tsx`
   som byter ut `window.fetch` mot syntetiska svar för `/api/snajp-support/*`
   (`app/forhandsvisning/konversationer/page.tsx:122-154`). Sidorna är **publika**
   (inte i proxyns matcher), så bara påhittade data.
9. **Skrivspärr på UI-filer:** pluginet anti-slop-design kör `design-gate.py` som
   PreToolUse på `Write|Edit|MultiEdit|NotebookEdit` och på `Bash|PowerShell`.
   `DESIGN_GATE_BLOCKING=1` är satt i `~/.claude/settings.json` → kontraktsbrott
   (färg, typsnitt, typstorlek, radie som inte är DESIGN.md:s) **nekas**. UI-filer
   får inte skrivas via skal (heredoc, `>`, `Set-Content`) i en armad session.

---

## 1. Tokens: färg, typsnitt, radier, avstånd, rörelse

### 1.1 Färger, ordagrant ur `app/globals.css`

Värdena är OKLCH-tripletter `L C H` (används som `oklch(var(--x))`). Hex-kolumnerna
är **beräknade av mig** (OKLCH → sRGB, avrundat, utan `#`-prefix) för att kunna mata
ett externt tema; de står inte i koden. Kontroll: `--paper` ger `f6f3ed`, vilket är
exakt `themeColor` i `app/layout.tsx:94`, så omräkningen stämmer.

| Token | Ljust (`:root`, rad) | hex ljust | Mörkt (`[data-theme="dark"]`, rad) | hex mörkt | Roll (DESIGN.md / kommentar) |
|---|---|---|---|---|---|
| `--ink` | `0.20 0.018 252` (8) | 10171e | `0.94 0.006 88` (117) | edebe7 | primär text, primär fyllning |
| `--ink2` | `0.28 0.018 252` (9) | 232a32 | `0.99 0.004 88` (122) | fdfcf9 | hover på primärknapp (`hover:bg-ink2`) |
| `--paper` | `0.965 0.008 88` (10) | f6f3ed | `0.185 0.010 252` (123) | 101317 | sidans grund, "warm, never #fff" |
| `--paper2` | `0.93 0.012 88` (11) | ebe8df | `0.245 0.012 252` (127) | 1c2126 | upphöjt plan, alltid MED hårlinje |
| `--ochre` | `0.74 0.16 64` (12) | ef911d | `0.80 0.15 64` (131) | ffa748 | den enda accenten (ej text på paper: 2.17:1) |
| `--warning` | `0.50 0.16 64` (61) | 9f4700 | `0.86 0.12 64` (166) | ffc07a | textsäker ochre på ljusa ytor |
| `--mineral` | `0.50 0.015 252` (17) | 5d646c | `0.68 0.016 252` (134) | 9199a2 | dämpad text, kickerfärg |
| `--ink-muted` | `0.42 0.018 252` (48) | 464e57 | `0.72 0.006 88` (140) | a6a4a0 | sekundär text på paper (7.63:1) |
| `--ink-subtle` | `0.48 0.018 252` (49) | 565e68 | `0.62 0.006 88` (141) | 888682 | tertiär/meta på paper (5.90:1) |
| `--paper-muted` | `0.72 0.008 88` (50) | a7a49f | `0.42 0.010 252` (142) | 494e53 | sekundär text på ink-railen |
| `--paper-subtle` | `0.62 0.008 88` (51) | 888681 | `0.48 0.010 252` (143) | 5a5e63 | tertiär text på ink-railen |
| `--seal` | `0.42 0.022 252` (18) | 454e59 | `0.80 0.020 252` (147) | b5bfcb | djupt plan på mörka sektioner |
| `--moss` | `0.42 0.071 142` (32) | 365732 | `0.74 0.10 142` (159) | 86bb80 | lyckat/success |
| `--danger` | `0.53 0.18 27` (34) | be2f2c | `0.71 0.17 27` (160) | f97165 | fel, eskalering |
| `--focus` | `0.74 0.16 64` (35) | ef911d | `0.80 0.15 64` (161) | ffa748 | fokusring (= ochre) |
| `--chart-blue` | `0.48 0.12 252` (22) | 205f9f | `0.62 0.12 252` (150) | 4c89cc | andra dataserien |
| `--chart-ochre` | `0.74 0.16 64` (23) | ef911d | `0.66 0.15 64` (151) | d07b00 | första dataserien |
| `--chart-ramp-1..6` | `0.86 0.04 252`, `0.76 0.07 252`, `0.64 0.10 252`, `0.52 0.12 252`, `0.40 0.11 252`, `0.30 0.08 252` (26-31) | | `0.36 0.05 252` … `0.86 0.05 252` (153-158) | | sekventiell rampa, pipelinens steg |

Observera: **DESIGN.md:90 säger `--danger 0.57 0.18 27`, men koden har `0.53`**
(`app/globals.css:33-34`, sänkt efter a11y-audit 2026-10-02). Koden gäller.

Tailwind-namn (`tailwind.config.ts:8-29`): `ink`, `ink2`, `paper`, `paper2`, `mineral`,
`seal`, `ochre`, `moss`, `danger`, `warning`, `chart-blue`, `chart-ochre`, `ink-muted`,
`ink-subtle`, `paper-muted`, `paper-subtle`, plus alias `linen`=paper2, `frost`=paper2,
`steel`=mineral, `copper`=ochre. Alla tar alfa: `border-ink/12`, `bg-ochre/10`.

**Regler för färg (ordagrant eller nära):**
- "Muted text uses tokens, never `ink/xx` or `paper/xx` opacity." (DESIGN.md:103).
  Använd `text-ink-muted`, `text-ink-subtle`, `text-paper-muted`, `text-paper-subtle`
  eller `text-mineral`.
- `text-ochre` är bara för icke-text eller text på den mörka railen; textochre på ljus
  yta är `text-warning` (DESIGN.md:137-145).
- Hårlinjer skrivs som alfa på ink: `border-ink/10`, `/12`, `/15` (överallt i
  `components/ui.tsx`, t.ex. rad 117, 126, 361, 380). I mörkt läge blir samma klass en
  ljus linje automatiskt (`app/globals.css:85-89`).
- Accent ca 3-5 % av en vy: primär CTA, aktuellt val, fokusring, statusindikatorer
  (DESIGN.md:94-96).

### 1.2 Typsnitt

| Variabel | Typsnitt | Källa | Tailwind |
|---|---|---|---|
| `--font-geist` | Geist (Google) | `lib/fonts.ts:29-33` | `font-sans` (standard) |
| `--font-fraunces` | Fraunces, axlar `SOFT`,`opsz`, normal+kursiv, `preload: false` | `lib/fonts.ts:12-27` | `font-display` |
| `--font-jetbrains` | JetBrains Mono | `lib/fonts.ts:35-39` | `font-mono` (bara maskin-id:n) |
| `--font-source-serif` | Source Serif 4 | `lib/fonts.ts:49-59` | bara marknadssidor via `.serif-fet` |

- Variablerna sätts på `<html>` via `fontVariables` (`lib/fonts.ts:61`, `app/layout.tsx:122`).
- **Appytor förladdar Fraunces** genom `import "@/lib/fonts-rubrik";` i layouten
  (`app/dashboard/layout.tsx:6`, `app/admin/layout.tsx:7`, `lib/fonts-rubrik.ts:11-17`).
  En CRM-layout ska göra samma import.
- `.font-display` sätter `font-variation-settings: "opsz" 144, "SOFT" 30`
  (`app/globals.css:253-256`). `.num` sätter `font-feature-settings: "tnum", "ss01"`
  (`app/globals.css:279-281`).

### 1.3 Appytornas typskala (det CRM:et ska använda)

Från `components/ui.tsx` (klassträngar, exporterade) och DESIGN.md:172-186:

| Roll | Primitiv | Klass ordagrant | Rad |
|---|---|---|---|
| Sidrubrik | `Sidhuvud`, `rubrikSida` | `font-display text-[1.75rem] font-semibold leading-tight tracking-[-0.02em]` | 97, 157 |
| Sektionsrubrik | `Sektion`, `rubrikSektion` | `font-display text-[1.5rem] leading-tight tracking-[-0.015em]` | 98, 171 |
| Panel-/kort-/radrubrik | `rubrikPanel` | `text-[1.0625rem] font-semibold leading-snug text-ink` | 99 |
| Brödtext | | Geist `0.9375rem`, `ink`/`ink-muted` | DESIGN.md:177 |
| Etikett (fält, kolumn, nyckeltal) | `etikett` | `text-[0.8125rem] font-medium text-ink-muted` | 106 |
| Meta (datum, domän, antal) | `meta` | `text-[0.8125rem] text-ink-subtle` | 109 |
| Nyckeltal | `Nyckeltal` | värde `num mt-2 font-display text-[2rem] leading-none tracking-[-0.02em]`, 1-5 poster | 229-256 |
| Nyckeltal i panel | `Talrad` | värde `text-[1.5rem] font-semibold tabular-nums` | 213-227 |
| Kort/panel | `panelKort` | `rounded-card border border-ink/12 bg-paper p-4 sm:p-5` | 117 |
| Flikar | `fliklista`, `flik`, `flikAktiv`, `flikInaktiv` | understrykning, ochre 2px under vald, 44px träffyta | 126-130 |
| Filter | `chiplista`, `chip`, `chipAktiv`, `chipInaktiv` | `min-h-9 rounded-full`, aktiv `bg-ink text-paper` | 144-148 |
| Fält i verktygsrad | `faltTatt` | `h-9 … text-[1rem] … [@media(pointer:fine)]:text-[0.875rem]` | 154-155 |
| Val i datarad | `faltDiskret` | `h-8 … border-transparent …` | 151-152 |
| Tabell | `Tabell`, `Cell`, `tabellRad`, `TabellKolumn` | `table-fixed`, `<colgroup>`, `text-[0.875rem]`, celler `py-2.5`, `minBredd` 720 | 324-418 |
| Rad-handling | `radLank` | tyst länk `min-h-8 … text-[0.8125rem]` | 387-388 |
| Lista utan kolumner | `Radlista`, `Rad` | `divide-y divide-ink/12 border-y border-ink/15`, `py-3` | 425-442 |
| Tomt läge | `Tomt` (`EmptyState` äldre) | en mening på `paper2` med hårlinje, ingen ikon | 259-283 |
| Knappar | `btnBase`, `btnPrimary`, `btnSecondary`, `btnLiten` | `min-h-11 rounded-input px-4 text-[0.875rem] font-semibold`; primär `bg-ink text-paper hover:bg-ink2` | 13-40 |
| Badge | `Badge tone="neutral|good|warn|danger"` | `rounded-[6px] border px-2.5 py-1 text-xs` | 42-59 |
| Laddning | `SkeletonRows`, `LoadingToast` | | 285-302 |

`cn()` är ett rent `join(" ")` **utan tailwind-merge**: två motstridiga klasser avgörs
av CSS-filens ordning, inte av ordningen i strängen (`components/ui.tsx:33-39`,
366-368). Därför bär `btnLiten` `!`.

### 1.4 Radier, skuggor, avstånd

| Token | Värde | Källa |
|---|---|---|
| `--radius-panel` / `rounded-panel` | `20px` | `app/globals.css:69`, `tailwind.config.ts:38` |
| `--radius-card` / `rounded-card` | `12px` | `app/globals.css:70`, `tailwind.config.ts:39` |
| `--radius-input` / `rounded-input` | `8px` | `app/globals.css:71`, `tailwind.config.ts:40` |
| Badge | `rounded-[6px]` | `components/ui.tsx:55` |
| Chip | `rounded-full` | `components/ui.tsx:146` |
| `shadow-hairline` | `0 0 0 1px oklch(var(--ink) / 0.09)` (mörkt: `oklch(1 0 0 / 0.1)`) | `tailwind.config.ts:47`, `app/globals.css:177-179` |
| `shadow-lift` | `0 24px 70px oklch(var(--ink) / 0.12)` (mörkt: `oklch(0 0 0 / 0.55)`) | `tailwind.config.ts:48`, `app/globals.css:181-183` |

Avstånd har inga egna tokens; Tailwinds standardskala används. Mönster som återkommer:
sidcontainer `mx-auto w-full max-w-[1200px] px-4 py-6 md:px-8 md:py-8`
(`components/AppShell.tsx:622`), adminens `max-w-[1400px] px-4 py-8 md:px-6 md:py-10`
(`app/admin/layout.tsx:59`), rubrik→innehåll `mt-6` (`AppShell.tsx:638`),
sektion `mt-12 first:mt-0`, rubrik→innehåll i sektion `mt-4` (`ui.tsx:183,188`).
Railen är `w-[64px]` under `lg`, `lg:w-[260px]` (`components/shell/Rail.tsx`, `Rail`).
Träffytor: 44px för navigering, flikar, primärknappar; 32-36px för kontroller i datarader
(DESIGN.md:193-194). Fält aldrig under 16px text på pekskärm (DESIGN.md:217).

### 1.5 Rörelse

| Token | Värde | Källa |
|---|---|---|
| `--ease-out` / `ease-out` (Tailwind) | `cubic-bezier(0.16, 1, 0.3, 1)` | `app/globals.css:63`, `tailwind.config.ts:43` |
| `--ease-editorial` | alias till `--ease-out` | `app/globals.css:65` |
| `--dur-short` | `180ms` | `app/globals.css:66` |
| `--dur-mid` | `300ms` | `app/globals.css:67` |

- Appytor: "no hero, no reveals, no imagery" (DESIGN.md:71). Rörelse i appen är
  färg-/transformövergångar på hover (`transition-colors`), inga scroll-reveals.
- `prefers-reduced-motion` hanteras globalt (`app/globals.css:554-567`); ingen
  komponent behöver egen fallback (DESIGN.md:262).
- Hover bara med riktig pekare: Tailwind-varianten `peka:` =
  `@media (hover: hover) and (pointer: fine) { &:hover }` (`tailwind.config.ts:52-56`).
- Fokusring: `outline 2px`, `offset 2px`, färg `color-mix(in oklch, oklch(var(--focus)), black 18%)`,
  global via `:where(a, button, input, textarea, select, [tabindex]):focus-visible`
  (`app/globals.css:373-393`). Klassen `focus-ring` finns också.
- Menyer/popovers: dämpning 1.0, ingen studs (DESIGN.md:285-286).

### 1.6 Tema-mappning till ett externt komponentbibliotek (förslag)

**Förslag, inte kod.** Om ett externt bibliotek (t.ex. för datatabell eller tidslinje)
ska användas: mappa dess tema mot CSS-variablerna, aldrig mot hex, så att mörkt läge
och kundpaletten (`paletteToCss`, `app/layout.tsx:143`) följer med:

| Bibliotekets roll | Snajp-värde |
|---|---|
| background | `oklch(var(--paper))` |
| surface / card | `oklch(var(--paper))` + `border: 1px solid oklch(var(--ink) / 0.12)`; upphöjt: `oklch(var(--paper2))` |
| foreground | `oklch(var(--ink))` |
| muted-foreground | `oklch(var(--ink-muted))`, meta `oklch(var(--ink-subtle))` |
| border / divider | `oklch(var(--ink) / 0.12)`, starkare `/0.15` |
| primary | `oklch(var(--ink))` med text `oklch(var(--paper))`, hover `oklch(var(--ink2))` |
| accent / selected / ring | `oklch(var(--ochre))`; ring = `color-mix(in oklch, oklch(var(--focus)), black 18%)` |
| accent som text | `oklch(var(--warning))` |
| success / danger | `oklch(var(--moss))` / `oklch(var(--danger))` |
| radius sm / md / lg | `8px` / `12px` / `20px` |
| font-sans / heading / mono | `var(--font-geist)` / `var(--font-fraunces)` / `var(--font-jetbrains)` |
| duration / easing | `180ms`, `300ms`, `cubic-bezier(0.16, 1, 0.3, 1)` |

Tema väljs via cookie `snajp.tema` (`lib/tema.ts:28`, värden `"ljust" | "morkt"`,
rad 30) och stämplas på servern som `data-theme="dark"` på `<html>`
(`app/layout.tsx:117-125`). Inget `prefers-color-scheme` med flit (`app/globals.css:102-108`).

---

## 2. Vad DESIGN.md kräver och förbjuder för appytor

### 2.1 Familjen "App"

DESIGN.md:71, ordagrant: "Workbench: fast ink-vänsterrail (ikonrail <lg, ochre-markör
på aktiv flik — sidans EN tonala inversion), dense rows, fasta tabeller
(`Tabell`/`Radlista` i components/ui.tsx: deklarerade kolumnbredder, etikett-huvuden,
tnum), fixed type scale (se § App surfaces), ingen mikrotext, no hero, no reveals, no
imagery."

Gäller `/dashboard/*`, `/settings/*`, `/demo/*` i tabellen. **Antagande:** `/crm` blir
en ny rad i den familjen; tabellen i DESIGN.md:68-73 bör få raden när ytan byggs.

### 2.2 § App surfaces, sammandrag med de bärande meningarna

- En fast skala för `/admin`, `/dashboard`, `/settings` (och `/demo`), exporterad ur
  `components/ui.tsx` (DESIGN.md:167-170). Tabellen återges i 1.3 ovan.
- Referenslåset: "The reference lock is Twenty (dominant: object name small, a view
  row, dense tables) with Mailchimp's console (serif title on a dense surface,
  underlined tabs)." (DESIGN.md:192-193). Bra nyhet för ett CRM: Twenty är redan
  husets förebild för appytor.
- Tidigare fel som inte får komma tillbaka (DESIGN.md:189-192): pill-flikar i 44px ink
  som läste som primärknappar; tabeller med `py-4` i 15px; två knappar per rad; 44px
  fält som dubblade radhöjden.
- "**Tap targets:** 44px holds for navigation, tabs and primary buttons; controls
  inside data rows are 32–36px, which clears WCAG 2.2 AA (24px)." (DESIGN.md:193-194)
- "**One tonal inversion:** the rail. Nothing in the content column is an ink plate."
  (DESIGN.md:196)
- "**A new feature is integrated into the surface, never stacked on it** (Anton
  2026-11-24). A page has ONE row of key figures, in the order the work flows."
  (DESIGN.md:198-199). Nya tal går in i den befintliga raden; listor blir en panel
  bland de befintliga, med samma huvud (titel, antal, tyst länk till hela vyn).
  Samma regel står i CLAUDE.md ("En ny funktion byggs in i den befintliga ytan").
- Kickern är ersatt av `etikett`; "Ledes under headings are gone (F-016, F-018);
  information a user needs to act lives in the label, the value, or one plain sentence
  where it is used." (DESIGN.md:210-213)
- "`tests/invariants/test_inv_ui_001.py` (INV-UI-001) fails on `kicker`, `uppercase`,
  tracked spacing, italic display headings and em-dashes anywhere in the app-surface
  source." (DESIGN.md:214-215)
- "**Inputs never below 16px.**" (DESIGN.md:217)
- `PageShell` tar bara `title`, `action`, `children`; `kicker`/`description` borttagna
  2026-09-28 (`components/AppShell.tsx:594-610`).

### 2.3 Övrigt bindande för appytor

- "No em-dashes in any visible string, in either language." (DESIGN.md:333)
- Varje komponent med användarvänd text tvåspråkig, "Headings, buttons, empty states,
  errors, `aria-label`s and CSV headers included." (DESIGN.md:335-338)
- "Every interactive element ships all 8 states. Focus ring is ochre, 2px, 2px offset,
  no exceptions." (DESIGN.md:348)
- Honest-proof: mock/seed-data krävs i demo och dashboard men får inte citeras som
  resultat; "Two sources of truth on one surface is one too many" (DESIGN.md:316-321).
- Verifiering: "A screenshot you did not read does not count." (DESIGN.md:355). CLAUDE.md:
  rendera och titta på desktop och mobil före varje synlig commit; kräver ytan inloggning
  → bygg en förhandsvisning under `app/forhandsvisning/`.
- Kicker som etikett är `<p>`/`<span>`, aldrig rubrik (DESIGN.md:342-346).
- Fönstret mäts med elementgränser vid 320/375/390/414/768/1024/1440/1920 (DESIGN.md:350-351).

---

## 3. Var en egen CRM-app läggs i samma Next-projekt

### 3.1 Ruttträdet i dag (läst med `ls`)

`app/` på toppnivå: `layout.tsx` (rot), `page.tsx`, `globals.css`, `error.tsx`,
`global-error.tsx`, `not-found.tsx`, `manifest.ts`, `robots.ts`, `sitemap.ts`, och
mapparna `admin`, `ai-agenter`, `ai-supportagent`, `angerratt`, `api`, `auth`,
`avregistrera`, `b2b-leads`, `b2b-prospektering`, `boka-demo`, `bokforing`, `chat`,
`cookies`, `dashboard`, `demo`, `design-drafts`, `duo-demo`, `embed`, `faq`,
`forhandsvisning`, `integritetspolicy`, `jamfor-ai-sdr`, `jamfor-supportagenter`,
`kvitton`, `leads`, `leads-i-inkorgen`, `login`, `onboarding`, `prova`, `settings`,
`support`, `supportchatt`, `support-pa-svenska`, `svensk-ai-sdr`, `vart-team`, `villkor`.
**Inga ruttgrupper `(…)` används.** Varje yta har sin egen mapp och layout.

Layouter som spelar roll:

| Rutt | Layout | Vad den gör |
|---|---|---|
| alla | `app/layout.tsx` | server: läser tema-cookie, tenantpalett, `<LocaleProvider>` runt allt (rad 146), `lang="sv"` |
| `/dashboard/[[...slug]]` | `app/dashboard/layout.tsx` | `resolveDashboardState()`; plattformsadmin i `vy === "admin"` → `redirect("/admin")` (rad 32-34); `requireOnboarded()` om inte demovy (rad 43-45); `<DashboardProvider>` |
| `/settings/[[...slug]]` | `app/settings/layout.tsx` | `requireOnboarded()` + `resolveDashboardState()` + `<DashboardProvider>` (rad 35-41) |
| `/admin/...` | `app/admin/layout.tsx` | `getPlatformAdmin()` annars `notFound()` (rad 42-45); demovy → `/dashboard`; `<DashboardProvider><AdminShell>`; `dynamic = "force-dynamic"` |
| `/demo/[[...slug]]` | ingen egen layout | sidan lägger `<DashboardProvider state={DEMO_STATE}>` (`app/demo/[[...slug]]/page.tsx:63-104`), aldrig session eller databas |
| `/forhandsvisning/*` | ingen | klientsidor, publika |

Varje vy ritar sitt eget skal: `PageShell` → `AppShell` (`components/AppShell.tsx:602-641`).
Skalet är `<div className="appyta min-h-screen bg-paper text-ink">` + `Rail` + mobilrad +
`<main>` (`AppShell.tsx:382-590`). Under `/admin` returnerar `AppShell` bara barnen
(`AppShell.tsx:274-276`) eftersom `AdminShell` äger skalet där.

`/dashboard` är en dispatcher: `app/dashboard/[[...slug]]/page.tsx` →
`WorkspaceSection` (`components/dashboard/WorkspaceSection.tsx:57-209`), som också är
**entitlement-grinden** (rad 120-140: `products.includes(product)`, annars
`AgentLast`-upsell eller `notFound()`).

### 3.2 Så kontrolleras inloggning i dag (tre lager)

1. **Proxy (Edge, ingen databas):** `proxy.ts:50-61`
   ```ts
   const token = await getToken({ req: request, secret: process.env.AUTH_SECRET, secureCookie: request.nextUrl.protocol === "https:" });
   if (isProtectedRoute(pathname) && !token) {
     const loginUrl = request.nextUrl.clone();
     loginUrl.pathname = "/login";
     loginUrl.searchParams.set("next", pathname);
     return NextResponse.redirect(loginUrl);
   }
   ```
   Utan `AUTH_SECRET` skickas skyddade rutter också till `/login` (fail-closed,
   `proxy.ts:40-48`). Matchern: `"/dashboard/:path*", "/settings/:path*",
   "/onboarding/:path*", "/admin/:path*", "/login", "/embed/:path*"` (`proxy.ts:91-105`).
   Exporten måste heta `config` (`proxy.ts:83-87`, minnesanteckningen om Next 16).
   **`/api` får aldrig in i matchern** (`tests/invariants/test_inv_sec_010.py:146-170`).
2. **Layout (server, färskt ur databasen):** `requireOnboarded()`
   (`lib/auth/onboarding-gate.ts:26-50`): `auth()` → ingen användare `redirect("/login")`;
   plattformsadmin passerar; utan `businessContext` → `redirect("/onboarding")`.
   `resolveDashboardState()` (`lib/data/dashboard.ts:171`, React-`cache`) ger
   `DashboardState` (`lib/data/dashboard.ts:23-80`): `products`, `addons`,
   `workspaceName`, `userEmail`, `signedIn`, `isDemo`, `isPlatformAdmin`, `vy`,
   `impersonation`, `arLasare`, `initialScope`.
3. **API-routen:** `proxyAsTenant()` (`app/api/snajp-support/_auth.ts:20-60`) kräver
   `requireSnajpTenant()` (`lib/snajp/tenant.ts:150`), spärrar skrivningar för läsrollen
   (`roll === LASROLL` → 403, rad 35-37) och märker adminens skrivningar i kundvy som
   test (`is_test=true`, rad 39-57).

### 3.3 Förslag: `app/crm/` som egen yta med egen layout, samma session

**Förslag (inte byggt).** Samma Next-projekt, samma Auth.js-cookie, egen mapp som
`/admin`. Ingen ruttgrupp behövs: en vanlig mapp `app/crm/` ger en egen layout och en
egen URL (`/crm`). En ruttgrupp `(crm)` hade bara gett layout utan prefix och krockat
med befintliga toppnivåsidor.

Filer som behövs (namn är förslag):

```
app/crm/layout.tsx            server: grind + DashboardProvider + CrmShell
app/crm/loading.tsx           <LaddarArbetsyta />   (components/Laddar.tsx:35)
app/crm/error.tsx             "use client"; <FelArbetsyta {...props} /> (components/Felgrans.tsx:81)
app/crm/[[...slug]]/page.tsx  tunn dispatcher, som app/dashboard/[[...slug]]/page.tsx
components/crm/CrmShell.tsx   "use client"; komponerar Rail (components/shell/Rail.tsx) som AdminShell gör
components/crm/...            vyerna (Foretag, Personer, Tidslinje, Synk)
```

Layouten, modellerad på `app/dashboard/layout.tsx` och `app/settings/layout.tsx`:

```tsx
// app/crm/layout.tsx  (FÖRSLAG)
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { CrmShell } from "@/components/crm/CrmShell";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireOnboarded } from "@/lib/auth/onboarding-gate";
import "@/lib/fonts-rubrik";

export const dynamic = "force-dynamic";

export default async function CrmLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await requireOnboarded();                 // /login eller /onboarding, färskt ur databasen
  const state = await resolveDashboardState();
  // Grinden för själva CRM:et: produkt eller tillägg. Utan rätt: notFound() eller en
  // upsell-vy, samma mönster som WorkspaceSection.tsx:130-140.
  return (
    <DashboardProvider state={state}>
      <CrmShell>{children}</CrmShell>
    </DashboardProvider>
  );
}
```

Och för att proxyn ska skicka oinloggade till `/login`:
- `lib/routes.ts:493`: `protectedRoutePrefixes` får `"/crm"`.
- `proxy.ts:91-105`: matchern får `"/crm/:path*"` (och `"/crm"`; `:path*` matchar även
  roten i Next).

Fällor att känna till (lästa i koden):
- **Plattformsadmin:** `app/dashboard/layout.tsx:32-34` skickar admin till `/admin`.
  CRM-layouten ska **inte** göra det, annars kan Anton/Sebbe aldrig öppna CRM:et i
  kundskalet. `tillAdminvag()` (`lib/routes.ts:184-190`) lämnar `/crm` orörd, så länkar
  dit fungerar från `/admin` också.
- **Kundvy och demovy:** `state.vy` är `"admin" | "demo" | "kund"`; i `"kund"` är
  `impersonation` satt och alla skrivningar via `proxyAsTenant` blir test. CRM:ets
  synkknappar ärver det automatiskt om de går via `/api/snajp-support/*`.
- **`AppShell` direkt i CRM ger fel meny:** `PageShell`/`AppShell` ritar arbetsytans
  rail (`routesForProducts`) och har sin egen "strandad"-logik bara för `/dashboard/`
  (`AppShell.tsx:239-262`). En egen `CrmShell` som använder `Rail` direkt (samma väg
  som `AdminShell`, `components/admin/AdminShell.tsx:141-209`) ger CRM:et en egen meny
  utan att röra arbetsytan. Skalet ska bära klassen `appyta` (för `.appyta .kicker`,
  `app/globals.css:294-300`) och railen är sidans enda tonala inversion.
- **`DashboardProvider` måste finnas**, annars faller `useDashboard()` på den permissiva
  `FALLBACK` (`components/dashboard/DashboardContext.tsx:19-36, 87-98`) och visar fel saker.
- `next.config.ts:34` `staleTimes: { dynamic: 30 }`: vyer måste hämta sina data vid mount,
  inte lita på serverrenderat innehåll som kan vara 30 s gammalt.

### 3.4 Så läggs en länk i dashboardens sidomeny

Railens poster kommer ur `appRoutes` (`lib/routes.ts:124-150`). En ny post kräver:

1. **Rutten** i `appRoutes`, t.ex. `{ href: "/crm", labelKey: "nav.crm", product: "shared" }`.
   `product` styr synlighet via `routesForProducts` (`lib/routes.ts:152-171`). Ordningen i
   arrayen är menyns ordning (`AppShell.tsx:372-379`). `/settings` dras ut till railens fot
   (`AppShell.tsx:284-285, 413-420`).
2. **Etiketten** som `CopyKey` i `commonCopy` (`lib/i18n.tsx:16-44`), t.ex.
   `"nav.crm": { sv: "CRM", en: "CRM" }`. `labelKey` är typad som `CopyKey` (`lib/routes.ts:63`).
3. **Ikonen** i `RUTT_IKONER` (`components/AppShell.tsx:102-115`, lucide). Saknas den blir
   det `LayoutDashboard`. `AdminShell` läser samma karta.
4. **Demon:** `DEMO_VAGAR` (`components/AppShell.tsx:64-76`) mappar `/dashboard/*` till
   `/demo/*`. En `/crm`-länk i demon skulle utan post leda till `/login`. Demons meny är en
   egen lista `DEMO_NAV` (`lib/demo/sektioner.ts:43-51`); i dag finns en CRM-demo på
   `/demo/crm` (`app/demo/[[...slug]]/page.tsx` case `"crm"`, `components/crm/CrmDemo.tsx`).
5. **Adminytan** bygger sin "Arbetsyta"-grupp ur samma `routesForProducts`
   (`AdminShell.tsx:141-150`) och kör `href` genom `tillAdminvag`, så `/crm` dyker upp där
   utan extra kod.

**Om CRM:et ska vara en egen produkt:** `ProductKey = "leads" | "support" | "bookkeeping"`
(`lib/routes.ts:28-30`) är databasens värde i `workspaces.products`. En fjärde nyckel ger
typfel i varje `Record<ProductKey, …>` (kommentaren `lib/routes.ts:80-85` beskriver just
det vid bokföringen). Alternativ: `product: "leads"` eller ett tillägg (`lib/addons.ts`,
`DashboardState.addons`). Beslutet hör till Anton och ska skrivas i `docs/BESLUT.md`.

**Mörklagd post:** agenter arbetsytan saknar visas nedtonade och leder till upsell
(`AppShell.tsx:203-209, 349-360`); vilande produkter syns men går inte att klicka
(`lib/routes.ts:48`, `Rail.tsx` `vilande`). Samma mekanism kan användas för CRM:et om det
säljs separat.

### 3.5 Leads-ytan på hög nivå (det CRM:et ska kopplas till)

- `components/leads/LeadsSida.tsx` exporterar `IrisBolag` (rad 123): en sida med flikar
  i `?vy=` (`Segment = "oversikt" | "konversationer" | "uppfoljningar" | "inkorg" |
  "samtal" | "listor" | "korningar" | "erbjudanden"`, rad 45), detaljlåda i `?lead=`.
  Gamla adresser mappas (`GAMLA`, rad 69-75). Listfliken har delarna
  `"listor" | "saljlista" | "kunder"` (rad 77).
- `components/leads/CrmKundlista.tsx` ("Ladda upp befintlig CRM-kundlista", rad 8-18):
  kundens befintliga kunder sparas som lista med `kalla='crm'` (migration 098) och blir
  en **uteslutningsmängd** för Iris (`snajp-support/app/leads/upptagna.py`). Den visar
  `ImportLista kalla="crm"`. **Det här är dagens manuella väg som Buddy inte vill använda**;
  API-synken ska fylla samma uteslutning.
- `components/leads/ImportLista.tsx`: fyra steg `"fil" | "kolumner" | "granska" | "klart"`
  (rad 33-34), läser filen i webbläsaren, `POST /leads/import/granska` (rad 306) ger
  flaggor `"kund" | "lead" | "sparrad"`, `POST /leads/import` (rad 347) i satser om 500,
  tak 5000 rader (rad 29-30). Kvittot sparas som `lead_lists.importinfo` (migration 152,
  typen `Importinfo` rad 41-52).
- `components/leads/LeadslistorView.tsx`: listor, backendkontraktet i kommentaren
  rad 13-24 (`POST/GET /leads/listor`, `GET/DELETE /leads/listor/{id}`, `omprova`,
  `utkast`, `items/{item}/prospekt`), `Lista.status` `bestalld | byggs | klar | fel`,
  `kalla` `'sok' | 'kombinerad' | 'import' | 'crm'`, förlopp i `processering`
  (`typ: "processa" | "utkast"`, `status: "pagar" | "klar" | "fallen"`). Står på
  INV-UI-001:s skuldlista (`test_inv_ui_001.py:103`).
- `components/leads/Tidslinje.tsx`, `Konversationer.tsx`, `KonversationsTrad.tsx`,
  `Samtalslista.tsx`, `Uppfoljningar.tsx` finns och bär det som ska synas på bolagets
  tidslinje i CRM:et (inte läst i detalj här).

---

## 4. i18n-mönstret

### 4.1 API ordagrant

`lib/i18n.tsx` (klientmodul, `"use client"`, rad 1):

```ts
export type Locale = "sv" | "en";                          // rad 5
export type Localized = { sv: string; en: string };        // rad 6
type LocaleContextValue = {
  locale: Locale; setLocale(l: Locale): void; toggleLocale(): void;
  text: (value: Localized) => string;                      // rad 12
  t: (key: CopyKey) => string;                             // rad 13
};
export type CopyKey = keyof typeof commonCopy;             // rad 46, nycklar rad 16-44
export function LocaleProvider(...)                        // rad 63, sitter i app/layout.tsx:146
export function useLocale()                                // rad 110, kastar utanför provider
export function sv(value: Localized)                       // rad 118, svenska för servern
```

- Första renderingen är alltid `"sv"` (hydrering), valet läses ur `localStorage`
  `"snajp.locale"` efter mount (rad 57, 64-77). `document.documentElement.lang` följer
  valet (rad 91-93).
- **Servern känner inte språkvalet.** Serverkomponenter som visar text gör det via en liten
  klientkomponent: mönstret `AdminText` (`components/admin/AdminText.tsx:18-21`).
- `commonCopy` är för gemensam copy (navigation, statusord). Ytans egna texter ligger som
  modulkonstanter `const T = {...} satisfies Record<string, Localized>`
  (`components/leads/CrmKundlista.tsx:20-27`, `components/leads/ImportLista.tsx` `T`).
- Adminytan: `lib/admin/sprak.ts` har `ADMIN: Record<string, Localized>` (rad 21),
  `a(nyckel, locale)` (rad 534), `ordagrant(text)` (rad 544), `datum`, `tidpunkt`,
  `antal` (rad 572-597).
- `lib/http/json.ts` felmeddelanden är **bara svenska** (t.ex. rad 37-56, 131-143) och
  filen står inte i `YTOR`. Ett CRM som visar `felmeddelande(e)` visar svenska även i EN.

### 4.2 Hur INV-COPY-001 fäller (`tests/invariants/test_inv_copy_001.py`)

- Vilka filer: `YTOR` (rad 46-71) = `APPYTOR` ur INV-UI-001 + `app/demo`, `app/kvitton`,
  `app/support`, `app/leads`, de juridiska sidorna, `components/marketing`,
  `components/crm`, `components/auth`, `lib/demo/sektioner.ts`, sökordssidorna.
- Undantag (`UNDANTAG`, rad 74-79): `lib/i18n.tsx`, `lib/admin/sprak.ts`,
  `components/marketing/copy.ts`, `components/DesignDrafts.tsx`.
- Fynd (`_synlig_svenska`, rad 96-105): kommentarer stryks först (block- och `//`-kommentarer
  efter blanktecken, `test_inv_ui_001.py:62-70`). En rad är **ren** om den matchar
  `\b(?:sv|en)\s*:\s*["'`]` (halvan av ett par, rad 83) eller ett namnfält
  `namn|name|company_name|avsandare:` (rad 93). Annars är den ett **fynd** om någon
  strängliteral innehåller `[åäöÅÄÖ]`, eller om raden efter att strängar, taggar,
  `{uttryck}` och `obj.medlem` strukits fortfarande har å/ä/ö och inte ser ut som kod
  (`[=(;]` eller börjar med `import|export|const|let|type|interface|return`, rad 87).
- Listor över flera rader: `sv: [` … `]` hoppas över (rad 91, 127-134).
- `export const metadata = {...}` stryks (rad 110, 123).
- Rad med `// inte-copy` hoppas över (rad 113-116, 121, 135-136): för data som råkar vara
  svensk (fixturnycklar, backendfraser, mejltext till svenska bolag; se `CrmDemo.tsx:49-54`).
- Skuldlistan `_SKULD_2026_10_02` är tom (rad 172-173). `test_skulden_ar_fortfarande_skuld`
  (rad 190-199) kräver att en fil stryks när den blivit ren.
- **Lucka:** grinden ser bara å/ä/ö. Engelsk eller svensk text utan å/ä/ö
  ("Kontakta oss" i `AppShell.tsx:580`) passerar oöversatt. Regeln gäller ändå.
- Testet körs (lätt, bara filläsning): `python -m pytest tests/invariants/test_inv_copy_001.py tests/invariants/test_inv_ui_001.py -q`.

### 4.3 Minimalt komplett exempel som klarar INV-COPY-001 och INV-UI-001

**Förslag**, skrivet efter mönstren ovan. Inga em-streck, ingen kicker, ingen
`uppercase`, ingen kursiv rubrik; varje synlig sträng är ett par.

```tsx
"use client";

import { useEffect, useState } from "react";
import { Cell, Sektion, Tabell, Tomt, meta, radLank, tabellRad } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { LeadsFel, leadsAnrop } from "@/lib/leads/suite";

type Foretag = { id: string; namn: string; orgnr: string | null; senast: string | null };

const T = {
  rubrik: { sv: "Företag", en: "Companies" },
  tabell: { sv: "Företag i CRM:et", en: "Companies in the CRM" },
  kolNamn: { sv: "Företag", en: "Company" },
  kolOrgnr: { sv: "Org.nr", en: "Reg. no." },
  kolSenast: { sv: "Senaste händelse", en: "Latest event" },
  oppna: { sv: "Öppna", en: "Open" },
  laddar: { sv: "Hämtar företagen…", en: "Loading companies…" },
  tomt: {
    sv: "Inga företag ännu. Koppla ert CRM så hämtas kunderna hit.",
    en: "No companies yet. Connect your CRM and the customers will appear here."
  },
  fel: { sv: "Företagen gick inte att hämta.", en: "The companies could not be loaded." }
} satisfies Record<string, Localized>;

export function CrmForetag() {
  const { text, locale } = useLocale();
  const [rader, setRader] = useState<Foretag[] | null>(null);
  const [fel, setFel] = useState(false);

  useEffect(() => {
    let aktiv = true;
    leadsAnrop<{ foretag: Foretag[] }>("/crm/foretag")
      .then((svar) => aktiv && setRader(svar.foretag))
      .catch((orsak: unknown) => {
        if (aktiv) setFel(orsak instanceof LeadsFel || orsak instanceof Error);
      });
    return () => {
      aktiv = false;
    };
  }, []);

  return (
    <Sektion title={text(T.rubrik)}>
      {fel ? (
        <Tomt>{text(T.fel)}</Tomt>
      ) : rader === null ? (
        <p className={meta}>{text(T.laddar)}</p>
      ) : rader.length === 0 ? (
        <Tomt>{text(T.tomt)}</Tomt>
      ) : (
        <Tabell
          ariaLabel={text(T.tabell)}
          kolumner={[
            { rubrik: text(T.kolNamn), bredd: "44%" },
            { rubrik: text(T.kolOrgnr), bredd: "20%" },
            { rubrik: text(T.kolSenast), bredd: "24%" },
            { rubrik: text(T.oppna), bredd: "12%", srOnly: true }
          ]}
        >
          {rader.map((rad) => (
            <tr key={rad.id} className={tabellRad}>
              <Cell titel>{rad.namn}</Cell>
              <Cell className="num">{rad.orgnr ?? ""}</Cell>
              <Cell className={meta}>
                {rad.senast ? new Date(rad.senast).toLocaleDateString(locale === "sv" ? "sv-SE" : "en-GB") : ""}
              </Cell>
              <Cell hoger>
                <a href={`/crm/foretag/${rad.id}`} className={radLank}>
                  {text(T.oppna)}
                </a>
              </Cell>
            </tr>
          ))}
        </Tabell>
      )}
    </Sektion>
  );
}
```

Varför den klarar grinden: varje rad med å/ä/ö står på en `sv:`-rad eller saknar
svenska bokstäver i strängar. `/crm/foretag` är en **påhittad** backendväg; den finns
inte i dag. Felmeddelandet tas ur `T`, inte ur `LeadsFel.message` (som är backendens
svenska text).

---

## 5. Förhandsvisningsmönstret (utan databas)

### 5.1 Hur det fungerar i dag

- Mappen: `app/forhandsvisning/{exempelbolag, iris-granskning, konversationer,
  korningens-utkast, kundinstallningar, leads-skickat, leads-snabbsok, listutkast, meny,
  samtal, webbpool}/page.tsx`.
- **Publika:** inte i proxyns matcher (`proxy.ts:91-105`), ingen layout, ingen session.
  Därför bara syntetiska data (`.test`-domäner, `000000-0000`, "Fiktiv Telefoni AB").
  CLAUDE.md förbjuder skärmdumpar med kunddata och att peka en lokal server mot
  development-databasen (den är en spegel av produktionen).
- Två varianter:
  1. **Komponenten har ett `demo`-läge** och läser fixturer själv:
     `app/forhandsvisning/samtal/page.tsx:10-15` renderar `<Samtalslista demo />` i
     `<main className="appyta mx-auto min-h-dvh max-w-6xl bg-paper px-4 py-10 text-ink sm:px-8">`.
  2. **`window.fetch` byts ut** så att den riktiga komponenten kör oförändrad och får
     svar från webbläsaren: `installeraFetch()` i `konversationer` (rad 126-154),
     `iris-granskning` (75), `korningens-utkast` (43), `kundinstallningar` (49),
     `leads-skickat` (154), `listutkast` (65), `webbpool` (58). Den släpper igenom allt som
     inte innehåller `/api/snajp-support/` (rad 132) och sätter en flagga
     `window.__forhandsvisning` så att den bara installeras en gång (rad 127-128).
- Sidorna står **inte** i INV-COPY-001:s `YTOR`; `konversationer/page.tsx:165` har en
  hårdkodad rubrik `Leads`.
- Sidorna lägger inte `DashboardProvider` runt; komponenterna får då `FALLBACK`
  (`signedIn: false`, alla produkter). Behöver vyn en viss state: lägg
  `<DashboardProvider state={...}>` runt, som `app/demo/[[...slug]]/page.tsx:63-104` gör.

### 5.2 Komplett exempel (förslag) för en CRM-vy

```tsx
// app/forhandsvisning/crm-foretag/page.tsx  (FÖRSLAG)
"use client";

import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { CrmForetag } from "@/components/crm/CrmForetag";
import { rubrikSida } from "@/components/ui";
import { useLocale } from "@/lib/i18n";

/**
 * Förhandsvisning: CRM › Företag med syntetiska bolag, ingen databas. Anropen mot
 * /api/snajp-support/ besvaras här i webbläsaren, samma mönster som
 * /forhandsvisning/konversationer.
 */

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();

const FORETAG = {
  foretag: [
    { id: "f1", namn: "Fiktiv Telefoni AB", orgnr: "000000-0001", senast: iso(5) },
    { id: "f2", namn: "Exempelflytt AB", orgnr: "000000-0002", senast: iso(50) },
    { id: "f3", namn: "Testmåleri AB", orgnr: null, senast: null }
  ]
};

const STATE = {
  products: ["leads", "support"] as ("leads" | "support")[],
  addons: [],
  workspaceName: "Exempelbolaget AB",
  userEmail: null,
  signedIn: true,
  isDemo: false,
  isPlatformAdmin: false,
  vy: "admin" as const,
  impersonation: null,
  arLasare: false,
  initialScope: "both" as const
};

function svar(kropp: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } }));
}

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    if (url.includes("/crm/foretag")) return svar(FORETAG);
    return svar({});
  };
}

export default function Page() {
  installeraFetch();
  const { text } = useLocale();
  return (
    <main className="appyta mx-auto min-h-dvh max-w-6xl bg-paper px-4 py-10 text-ink sm:px-8">
      <h1 className={rubrikSida}>{text({ sv: "CRM", en: "CRM" })}</h1>
      <div className="mt-6">
        <DashboardProvider state={STATE}>
          <CrmForetag />
        </DashboardProvider>
      </div>
    </main>
  );
}
```

Den som vill se hela skalet (railen) ska rendera `CrmShell` runt vyn i förhandsvisningen
också; railen är det som avgör om sidan ser ut som en app. "Testmåleri AB" ligger i ett
`namn:`-fält och fälls därför inte av copy-grinden även om mappen läggs i `YTOR`.

Kör: `.claude/launch.json` har `"web"` = `npm run dev` på port 3005 (`autoPort`) och
`"web-prod"` = `npm run start -- -p 3100`. Under ~4 GB ledigt virtuellt minne: en server
i taget, stäng direkt efter bilderna (CLAUDE.md).

---

## 6. Skrivspärrar som gäller UI-filer

### 6.1 Projektets egna hookar

`.claude/settings.json` har bara `SessionStart` (`bd prime --hook-json`,
`bash scripts/grenstatus.sh`, plugin-bootstrap i molnet). **Inga PreToolUse/PostToolUse
i projektet.** `~/.claude/settings.json` har tomma `hooks`-listor men
`env.DESIGN_GATE_BLOCKING = "1"`.

### 6.2 anti-slop-design (plugin 1.2.3) – det som faktiskt spärrar

`~/.claude/plugins/cache/anti-slop-design/anti-slop-design/1.2.3/hooks/hooks.json`:

| Händelse | Matcher | Skript | Effekt |
|---|---|---|---|
| PreToolUse | `Write|Edit|MultiEdit|NotebookEdit` | `design-gate.py` | kontraktskontroll, **nekar** när `DESIGN_GATE_BLOCKING=1` |
| PreToolUse | `Bash|PowerShell` | `design-gate.py` | nekar skalskrivning av UI-filer i en armad session |
| PreToolUse | `mcp__Claude_Browser__.*`, `mcp__claude-in-chrome__.*` | `design-verify-gate.py` | påminnelse om inspektionsdisciplin, blockerar aldrig |
| PostToolUse | `Write|Edit|…` | `design-route.py` | rådgivande: vilken skill som hör till filen, detektorfynd |
| PostToolUse | `Skill`, `Read`, inspo/ui-skills | telemetri, `design-vision-track.py` | loggar |
| UserPromptSubmit | | `design-intent.py` | klassar uppdraget (`.impeccable/.design-verb-<session>`) |
| Stop | | `design-stop.py` | detektorkörning över rörda UI-filer + rapport |

Vad `design-gate.py` gör (läst):
- UI-fil = `.tsx .jsx .vue .svelte .astro .html .htm .css .scss .sass .less` alltid;
  `.ts .js .mjs .cjs` bara om innehållet har JSX-signal (stängande tagg)
  (`design_hook_lib.py:590-660`). Andra filändelser räknas också som UI (rad 660).
- Med `DESIGN.md` i projektroten (finns här) körs **kontraktsreglerna**
  `design-system-color`, `design-system-font`, `design-system-font-size`,
  `design-system-radius` (`design-gate.py:40-45`) via detektorn på en skuggkopia av det
  inkommande innehållet (rad 388-410), plus "gate 60" (en annan skills hårdkodade palett,
  rad 374-382). Fynd → `deny` med listan av lästa tokens (rad 427-443).
- Referensgolvet (Skill(design), TASTE.md, katalogval) gäller **bara utan** DESIGN.md
  (rad 363-366) och berör alltså inte det här repot.
- Skal: omdirigering, heredoc, `tee`, `sed -i`, `Set-Content`/`Out-File` till en UI-fil
  nekas i armad session; `cp`/`mv`/`Copy-Item` är tillåtet (rad 335-354).

**Så passerar man:** skriv UI med Write/Edit; använd bara tokenklasser (`bg-paper`,
`text-ink-muted`, `border-ink/12`, `rounded-card`/`rounded-input`/`rounded-panel`,
`font-display`/`font-sans`, typskalans värden ur `components/ui.tsx`); inga hexvärden,
inga godtyckliga typsnitt eller radier. Är ett värde verkligen nytt: lägg det i DESIGN.md
först (meddelandet säger det ordagrant, rad 432-435). Detektorfynd i PostToolUse-raden
"Deep detector" ska bedömas på sakskäl, inte avfärdas (minnesanteckningen
`impeccable-route-gap-hook.md`); `ROUTE GAP`-räknaren får avfärdas.

### 6.3 Mekaniska grindar i testsviten som rör UI

| Test | Vad det fäller |
|---|---|
| `tests/invariants/test_inv_ui_001.py` | `kicker`, `uppercase`, `tracking-[0.06…]`, kursiv displayrubrik, em-streck i `APPYTOR` (skuld: 25 filer, rad 101-127) |
| `tests/invariants/test_inv_copy_001.py` | svenska utan engelskt par i `YTOR` |
| `tests/invariants/test_inv_sec_010.py` | varje `app/api/**/route.ts` måste ha sessionskontroll eller stå i `ANON_ALLOWLIST` med skäl; matchern får inte täcka `/api` |
| `tests/test_bokforing_atkomst.py` | `adminOnly`-mekanismen i `appRoutes` |

Webbbedömningen (webbrevision, webbnivå, betyg, `lan`) får bara visas för plattformsadmin,
Umeå Webdesign och Alunix; varje ny yta som visar den ska grindas i samma commit (CLAUDE.md).
Det gäller också CRM:ets bolagssida om den visar sådana fält.

---

## 7. Datahämtning i klientkomponenter i dag

**Inget bibliotek.** `grep` efter `useSWR`, `@tanstack`, `react-query` i `components`,
`lib`, `app` ger noll träffar. Mönstret är:

1. **Väg:** klienten anropar `/api/snajp-support/<väg>` (samma origin, cookien följer med).
   Catch-all-routen `app/api/snajp-support/[...path]/route.ts` har `GET`, `POST`, `PUT`,
   `PATCH`, `DELETE`, `runtime = "nodejs"`, `maxDuration = 60`, och skickar till
   backendens `/api/<väg>` via `proxyAsTenant` (sessionens tenant, läsrollsspärr,
   test-märkning i kundvy). Svaret komprimeras (`lib/http/komprimera.ts`). Specifika
   routes (`chat`, `jobs`, `triage`, `kvitton`, `leads`, `testchatt`, `bookkeeping`)
   ligger bredvid och matchar först.
2. **Hjälpare:**
   - `leadsAnrop<T>(vag, init?)` (`lib/leads/suite.ts:126-140`):
     ```ts
     const response = await fetch(`/api/snajp-support${vag}`, {
       cache: "no-store",
       ...init,
       headers: init?.body ? { "Content-Type": "application/json" } : undefined
     });
     const kropp = await readJsonBody<T>(response);
     if (!response.ok) throw new LeadsFel(detaljtext(kropp) ?? `HTTP ${response.status}`, response.status, arEjAktiverad(response.status, kropp));
     return kropp as T;
     ```
     `LeadsFel` (rad 94-102) bär `status` och `ejAktiverad` (409 `ej_aktiverad`).
     `detaljtext` (rad 104-124) läser FastAPI:s `detail` som sträng, objekt
     (`message`, `saknas`) eller pydantic-lista. 33 filer i `components/leads` importerar
     `@/lib/http/json`, 20 importerar `@/lib/leads/suite`.
   - `readJsonBody` / `readJson` / `felmeddelande` / `HttpJsonError`
     (`lib/http/json.ts:23, 67, 108, 131`): läser kroppen som text först så att tom kropp,
     HTML-felsida och 204 inte kraschar; `kroppsbesked()` (`lib/http/besked.ts:16`).
   - Lokala varianter finns, t.ex. `anropa<T>` i `LeadslistorView.tsx:399-410`.
   - Sidindelning: `allaProspekt` (`lib/leads/suite.ts:147-165`, `limit`/`offset`,
     svaret `{prospects, fler, nasta}`), `listansProspekt` (rad 167-173, upp till 5000).
3. **State och uppdatering:** `useState` + `useEffect`, egna hookar, fönsterhändelser och
   intervall som bara körs när fliken syns. Exempel `useNotisantal`
   (`lib/leads/konversationer.ts:240-266`):
   ```ts
   const hamta = useCallback(async () => {
     try { const svar = await leadsAnrop<{ olasta?: number }>("/leads/notiser/antal"); setAntal(svar.olasta ?? 0); }
     catch { /* en räknare som inte går att läsa visar ingenting */ }
   }, []);
   useEffect(() => {
     if (!aktiv) return;
     void hamta();
     window.addEventListener(NOTISER_UPPDATERADE, uppdatera);
     window.addEventListener(LEADS_UPPDATERADE, uppdatera);
     const id = window.setInterval(() => { if (document.visibilityState === "visible") void hamta(); }, 60_000);
     return () => { /* ta bort lyssnare, clearInterval */ };
   }, [aktiv, hamta]);
   ```
   Förlopp för bakgrundsjobb: `taligHamtning(hamta, maxFelIRad = 5)`
   (`lib/leads/pollning.ts:12-30`) tål enstaka fel i en pollslinga. Förloppet sparas på
   serverobjektet (t.ex. `Lista.processering`, `importinfo`) så att det står kvar efter
   omladdning, vilket CLAUDE.md kräver ("Varje funktion har ett sätt att följa flödet").
4. **Server actions** finns för vissa skrivningar (`lib/actions/*`, t.ex.
   `signOut` i `AppShell.tsx:25,443`, `@/lib/actions/saljlista`), men listdata hämtas i
   klienten.
5. **Demo/förhandsvisning:** komponenterna tar `demo`-prop och läser fixturer
   (`lib/demo/*`) i stället för att anropa API:t, eller så byts `window.fetch` ut (avsnitt 5).

**Förslag för CRM:et:** en egen `crmAnrop<T>` som kopia av `leadsAnrop` mot
`/api/snajp-support/crm/...` (catch-all-routen räcker; inget nytt API-lager i Next behövs
för inloggad trafik). Tvåvägs-API:t utåt (Buddys system → Snajp) går **inte** via den här
proxyn: den kräver en inloggad session. Det behöver en egen FastAPI-endpoint med
API-nyckel per tenant, och om en Next-route läggs till måste den stå i
`ANON_ALLOWLIST` med skäl (`test_inv_sec_010.py`).

---

## 8. Öppna frågor och risker (frontend)

- **Produkt eller tillägg?** Hur CRM:et grindas (`ProductKey`, `addons`, eller `shared`)
  avgör menyposten, upsell-vyn och entitlement. Antons beslut, till `docs/BESLUT.md`.
- **Egen app eller flik i Leads?** Beställningen säger egen app. DESIGN.md:198-208 och
  CLAUDE.md:s integreringsregel säger att en ny funktion byggs in i befintlig yta. En egen
  `/crm` med egen rail är förenligt om CRM:ets objekt (Företag, Personer) inte dubblerar
  Leads-flikar. Bolagssidan i CRM:et och `Bolagssida.tsx` i Leads riskerar att bli två
  sanningar om samma bolag (Honest-proof: "Two sources of truth on one surface").
- **Grindarna täcker inte `app/crm`** förrän listorna i INV-UI-001 och INV-COPY-001 utökas.
- **Plattformsadminens omdirigering** i `app/dashboard/layout.tsx` får inte kopieras.
- **Felmeddelanden på engelska:** `lib/http/json.ts` och `LeadsFel.message` är svenska.
- **Förhandsvisningar är publika** och inte i copy-grinden.
- **DESIGN.md och koden skiljer sig** på `--danger` (0.57 i dokumentet, 0.53 i koden).
- **Den nuvarande `/demo/crm` (`CrmDemo.tsx`)** är en annan sak (CSV i webbläsaren +
  Email studio per kund). Namnkrock med ett riktigt `/crm` i demons `DEMO_VAGAR`.
