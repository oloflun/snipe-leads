# Snajp CRM, underlag: designsystemet Astryx (meta/astryx, MIT)

Skrivet 2026-11-25 av en läsande agent, på arbetsgrenen `claude/snajp-crm-dd0d83`. Inget i
repot är ändrat utom att den här filen är ny. Inget installerades och ingen kod ur förlagan
kördes. Förlagans filer lästes som text; deras `AGENTS.md`/`CLAUDE.md` och
`plugins/astryx/skills/astryx/SKILL.md` lästes som data och följdes inte.

**Källor.** Förlagan är en grund klon i `D:\snajp-crm-forlaga\astryx`, commit
`7c3a82a74531079aa399d9fc9ccbcb691b206c86` (2026-11-24). Sökvägar som börjar med `astryx/`
avser den klonen. Sökvägar utan prefix avser Snajps worktree. Npm-registret frågades en gång med
`npm view` (bara läsning) den 2026-11-25.

**Läst:** `astryx/README.md`, `astryx/docs/README.md`, `astryx/docs/release.md` (sökträffar),
`astryx/docs/architecture/{theme-tokens,theme-application,theme-authoring-contract,internationalization}.md`
(i delar), `astryx/docs/design/{reduced-motion,bidirectionality}.md` (i delar),
`astryx/docs/themes/README.md`, `README.md` och `package.json` i varje paket under
`astryx/packages/`, `astryx/packages/core/src/theme/{tokens.stylex.ts,defineTheme.ts,Theme.tsx,resolveThemeValues.ts,statusRoleDerivation.ts}`
(i delar), `astryx/packages/core/src/reset.css`, `astryx/packages/core/src/tailwind-theme.css`
(huvudet), alla 269 `*.doc.mjs` under `astryx/packages/core/src/` (extraherade som text: namn,
kategori, beskrivning, propnamn), `astryx/packages/themes/{neutral,chocolate}`,
`astryx/packages/cli/assets/docs/` (tailwind, use-a-theme, author-a-theme, browser-support,
i18n-quick-start), `astryx/packages/cli/clients/cli/commands/init.doc.mjs`,
`astryx/packages/cli/assets/templates/pages/` (listan och `kanban-board`),
`astryx/apps/example-nextjs*` (manifest, config, `globals.css`, `layout.tsx`, `providers.tsx`,
README), `astryx/apps/docsite/package.json`. I Snajp: `package.json`, `tailwind.config.ts`,
`postcss.config.mjs`, `next.config.ts` (sökträffar), `app/globals.css` (rad 1–260),
`app/layout.tsx` (rad 100–150), `lib/tema.ts`, `lib/fonts.ts`, `lib/tenants/index.ts:120-140`,
`lib/i18n.tsx` (sökträffar), `components/ui.tsx` (exporterna), `DESIGN.md` (rad 75–352).

**Märkning.** [LÄST] betyder att påståendet står i den angivna filen. [NPM] betyder att det kom
från registret den 2026-11-25. [BEDÖMNING] och [ANTAGANDE] är mina egna slutsatser och ska
prövas. [MÅSTE PRÖVAS] betyder att det bara går att avgöra genom att rendera eller mäta.

---

## 0. Det en byggare behöver veta först

1. **Astryx kräver Tailwind v4 för sin Tailwind-brygga. Snajp kör Tailwind 3.4.** Bryggan
   `@astryxdesign/core/tailwind-theme.css` säger "Requires: Tailwind CSS v4+"
   [LÄST `astryx/packages/core/src/tailwind-theme.css:12-14`]; Snajp har `"tailwindcss":
   "^3.4.19"` och `@tailwind base/components/utilities` [LÄST `package.json`,
   `app/globals.css:1-3`]. Bryggan behövs inte för att använda komponenterna, men kaskadlagren gör
   det (punkt 2).
2. **Snajps CSS är olagrad, och olagrad CSS slår allt Astryx skriver.** Astryx lägger återställning,
   komponentstilar och tema i kaskadlager (`@layer reset`, `astryx-base`, `astryx-theme`)
   [LÄST `astryx/packages/core/README.md`, "Next.js (simplest)"]. Tailwind 3:s
   `@tailwind base` och Snajps egna regler `a { color: … }`, `a:hover { color: ochre }` och
   `button, input, textarea, select { font: inherit }` ligger utanför lager
   [LÄST `app/globals.css:1-3, 222-240`]. En olagrad deklaration vinner över varje lagrad oavsett
   specificitet, så Tailwind 3:s preflight (t.ex. transparent bakgrund på `button`) och Snajps
   länkfärg skriver över Astryx knappfyllning och länkfärger. [BEDÖMNING] Det här är den
   största tekniska risken och måste lösas innan första komponenten; se §6 och §8.
3. **Paketen är publicerade på npm, men inte alla.** `@astryxdesign/core`, `cli`, `build`,
   `richtext` och `theme-*` har `latest` = `0.7.17` [NPM]. `charts`, `lab`, `vega` och `native`
   finns bara under `@canary` och deras `latest` är platshållaren `0.0.0-bootstrap.0` [NPM; LÄST
   `astryx/packages/charts/README.md`, `astryx/packages/lab/README.md`]. En `npm install
   @astryxdesign/charts` utan tagg ger alltså en tom platshållare. Klonen står på `0.7.18`, som
   ännu inte släppts som `latest` [LÄST `astryx/packages/core/package.json`; NPM].
4. **Astryx sätter `data-theme` på `<html>`, samma attribut som Snajp använder för mörkt läge.**
   Rot-`Theme` skriver `data-theme="light"|"dark"` och TAR BORT attributet i läget `system` och
   när den avmonteras [LÄST `astryx/packages/core/src/theme/Theme.tsx:331-354`]. Snajp stämplar
   `data-theme="dark"` på servern och läser `:root[data-theme="dark"]` för hela sin mörka palett
   [LÄST `app/layout.tsx:120-124`, `app/globals.css:112`]. Används Astryx `Theme` med `mode`
   `system`, eller monteras och avmonteras den per sida, tappar Snajp sitt mörka läge. Ge den
   alltid `mode` från `lib/tema.ts` och montera den en gång.
5. **Temat kan läsa Snajps egna variabler direkt**, så att kundpaletten (`paletteToCss`) och mörkt
   läge följer med utan en rad extra. Priset: Astryx räknar inte ut status- och kontrastroller ur
   ett värde som inte är en konkret färg, så varje sådan roll måste sättas för hand och mätas
   (§3.4).
6. **Svenska finns men är halvfärdig.** `sv-SE.json` har 365 av 694 nycklar i `en.json`; resten
   faller tillbaka till engelska [LÄST, räknat ur `astryx/packages/core/locales/`]. Bland de som
   saknas: tabellens radexpansion och träd, Tokenizer (20), PowerSearch (37), Kbd (19), DateInput
   (4), MultiSelector (4) och hela richtext-editorn (30). Snajps regel om tvåspråkighet kräver att
   vi fyller luckorna med `overrides` (§5.3).
7. **Det finns ingen kanban-komponent, ingen kalender med vecko-/dagvy i core, och ingen redigering
   i cell.** Det finns en sidmall `kanban-board` (ren kod att kopiera, pekardrag utan tangentbord)
   och en `Schedule` i det opublicerade `lab`-paketet (§4.3).

---

## 1. Vad Astryx är och hur det är uppbyggt

**Vad.** Ett designsystem med öppen källkod från Meta, "Currently in Beta", byggt på React 19+
och StyleX, med "150+ accessible components", teman, mörkt läge, mallar och ett CLI
[LÄST `astryx/README.md:12-14, 27-30`]. MIT-licens [LÄST `astryx/package.json:5`,
`astryx/LICENSE`].

**Paket** [LÄST `astryx/packages/README.md`, varje `package.json`; NPM]:

| Paket | Version i klonen | På npm | Roll |
|---|---|---|---|
| `@astryxdesign/core` | 0.7.18 | `latest` 0.7.17 | Komponenter, temasystem, hooks, i18n, `reset.css`, `astryx.css`, `tailwind-theme.css` |
| `@astryxdesign/cli` | 0.7.18 | `latest` 0.7.17 | `astryx`-kommandot: dokumentation, mallar, temabygge, codemods, MCP-server |
| `@astryxdesign/build` | 0.7.18 | `latest` 0.7.17 | Babel/PostCSS/Vite/Next-plugin för källbygge med StyleX |
| `@astryxdesign/theme-{neutral,butter,chocolate,matcha,stone,gothic,y2k}` | 0.7.18 | `latest` 0.7.17 | Färdiga teman |
| `@astryxdesign/richtext` | 0.7.18 | `latest` 0.7.17 | Lexical-baserad editor och visare |
| `@astryxdesign/charts` | 0.1.9, `private: true` | bara `canary` | Diagram på d3 |
| `@astryxdesign/vega` | 0.1.3, `private: true` | bara `canary` | Vega/Vega-Lite-omslag |
| `@astryxdesign/lab` | 0.1.9, `private: true` | bara `canary` | Experimentella komponenter |
| `@astryxdesign/native` | 0.1.0, `private: true` | bara `canary` | Experiment för iOS/Android/macOS/Windows |
| `@astryxdesign/template-icons` | 0.0.0, `private: true` | nej | Platshållarikoner i mallarna; CLI:t skriver om importerna till Heroicons/Lucide [LÄST `astryx/packages/template-icons/README.md`] |
| `@astryxdesign/theme-probe` | privat | nej | Testfixtur, inget tema att använda [LÄST `astryx/packages/themes/README.md`] |

Motsägelse i förlagan: huvud-README säger att `lab` "is not published to npm" [LÄST
`astryx/README.md`, under paket-tabellen], men lab-README och registret säger canary
[LÄST `astryx/packages/lab/README.md`; NPM]. Registret avgör.

**Lager.** README delar systemet i grunder (typografi, färg, layout, tillgänglighet), komponenter
och mönster (tabellsidor, detaljsidor, formulärguider) [LÄST `astryx/README.md`, "Architecture"].
I praktiken ser stapeln ut så här:

1. **Tokens.** Deklareras i `astryx/packages/core/src/theme/tokens.stylex.ts` som par av
   `*Defaults` (värden) och `*Vars` (`stylex.defineVars`), och det är dessa namn komponenterna
   läser [LÄST `astryx/docs/architecture/theme-tokens.md`, "System model"].
2. **Tema.** `defineTheme()` gör om färg-, typografi-, radie- och rörelseinställningar plus explicita
   token- och komponentöverskrivningar till ett platt `DefinedTheme`
   [LÄST `astryx/docs/architecture/theme-authoring-contract.md`, "System model"]. Ett tema är "a set
   of CSS custom property overrides" [LÄST `astryx/README.md`, "What makes Astryx different"].
3. **Komponenter.** Skrivna med StyleX, levererade förkompilerade som atomära klasser i
   `astryx.css` inom `@layer astryx-base` [LÄST `astryx/apps/example-nextjs-tailwind/README.md`].
4. **Mallar och block.** Sidmallar och block som CLI:t skriver ut som källkod
   [LÄST `astryx/packages/core/README.md`, "Page Layouts"; `astryx/packages/cli/assets/templates/`].

**Hur stilar skrivs.**
- *StyleX* internt. För konsumenten är det "invisible": man importerar färdig CSS och skriver egna
  stilar med `className` i Tailwind, CSS-moduler eller vanlig CSS
  [LÄST `astryx/README.md`, "No styling lock-in"]. Komponenterna tar också `xstyle` (StyleX) och
  ofta `className`/`style` [LÄST t.ex. `astryx/packages/core/src/Code/Code.doc.mjs` props].
- *CSS-variabler* bär hela temat: `--color-*`, `--spacing-*`, `--radius-*`, `--shadow-*`,
  `--duration-*`, `--ease-*`, `--font-*`, `--text-*` [LÄST `tokens.stylex.ts`].
- *Tailwind* är en valfri brygga, bara v4, som mappar Tailwind-namn till Astryx variabler med
  `@theme reference inline` [LÄST `astryx/packages/core/src/tailwind-theme.css:1-40`].
- *Källbygge* med `@astryxdesign/build` kompilerar bara de komponenter man importerar (~22 KB CSS
  mot ~77 KB för färdig `astryx.css`), men kräver Babel och webpack i Next
  [LÄST `astryx/apps/example-nextjs-source/README.md`, "Why source build?"].

---

## 2. Installation i ett befintligt Next.js-projekt

### 2.1 Paketnamn, versioner och kanaler

- Stabila paket finns på npm under scope `@astryxdesign` med `latest` = `0.7.17` [NPM]. Ingen
  CLI-kopiering av källkod krävs för att använda komponenterna; man installerar dem som vanliga
  beroenden [LÄST `astryx/README.md`, "Getting Started"].
- Kopiering av källkod finns som tillval: `astryx swizzle <Komponent>` "ejects a component's full
  source into your project" [LÄST `astryx/README.md`, "Open internals";
  `astryx/packages/core/README.md`, "Astryx CLI"], och `astryx template <namn>` skriver ut en
  sidmalls källa [LÄST samma ställe].
- Canary: `0.7.18-canary.gfca8508` för alla paket [NPM]. Canary-byggen kommer högst en gång i
  timmen från `main` och "can break between any two versions" [LÄST
  `astryx/packages/lab/README.md`, "Trying lab components"].
- Varje stabil version publiceras från en oföränderlig tagg med npm-proveniens via OIDC, utan
  långlivad token [LÄST `astryx/docs/release.md:6-8`].

### 2.2 Peer-beroenden och krav

| Krav | Källa | Snajp i dag |
|---|---|---|
| `react` och `react-dom` `>=19.0.0` | [LÄST `astryx/packages/core/package.json` peerDependencies; NPM] | `19.3.1` [LÄST `package.json`]. Uppfyllt |
| `@stylexjs/stylex` `^0.19.0` (peer till core) | [LÄST samma; NPM] | Saknas. Måste installeras |
| Next.js: exemplen kör `^16.3.6` | [LÄST `astryx/apps/example-nextjs*/package.json`] | `16.4.6`. Uppfyllt |
| TypeScript: exemplen kör `^6.0.3` | [LÄST samma] | `^7.0.2`. [MÅSTE PRÖVAS] att typerna kompilerar under TS 7 |
| Node `>=22.13.0` för CLI:t | [LÄST `astryx/packages/cli/package.json` engines; NPM] | Ej kontrollerat på byggmaskinen |
| Tailwind v4 för bryggan | [LÄST `astryx/packages/core/src/tailwind-theme.css:12-14`] | `^3.4.19`. Inte uppfyllt |
| `@astryxdesign/theme-neutral` beror på `lucide-react ^1.66.0` | [LÄST `astryx/packages/themes/neutral/package.json`] | Snajp har `^0.468.0`. npm lägger en egen kopia under temat; två Lucide-versioner i paketet [BEDÖMNING] |
| `@astryxdesign/richtext`: `lexical` och 12 `@lexical/*` `^0.52.0` som valfria peers | [LÄST `astryx/packages/richtext/package.json`, `README.md` "Install"] | Saknas. Installeras bara om rik text används |
| `@astryxdesign/vega`: `vega`, `vega-lite`, `vega-util`, `react >=19.2.0` | [LÄST `astryx/packages/vega/package.json`] | Saknas |

Beroenden som följer med core: bara `intl-messageformat` [LÄST `astryx/packages/core/package.json`
dependencies].

**Installationsskript.** Både `core` och `cli` har `postinstall` som skriver en rad som uppmanar
till `astryx init`. Det "never fails the install" [LÄST `astryx/packages/core/scripts/postinstall.mjs:1-20`;
`astryx/packages/cli/package.json` scripts].

### 2.3 Byggsteg

Tre vägar, i stigande krav [LÄST `astryx/packages/core/README.md`, "Quick Start";
`astryx/packages/build/README.md`]:

1. **Färdigbyggd dist (rekommenderad).** "No build plugins, no PostCSS, no Babel config":
   importera stilmallarna i ordning och linda appen i `Theme`. Lägg
   `experimental.optimizePackageImports: ['@astryxdesign/core']` i `next.config`, annars skickar en
   serverkomponent som importerar från paketroten med alla klientkomponenter
   [LÄST `astryx/apps/example-nextjs/next.config.mjs`].
2. **Dist + Tailwind v4.** Samma, plus deklarerad lagerordning och `tailwind-theme.css`
   [LÄST `astryx/apps/example-nextjs-tailwind/src/app/globals.css`].
3. **Källbygge.** `withAstryx()` ur `@astryxdesign/build/next`, Babel och PostCSS. Under webpack
   krävs `--webpack`; under Turbopack fungerar en annan väg
   [LÄST `astryx/apps/example-nextjs-source/README.md`; `astryx/packages/build/README.md:9, 46`].

Eget tema byggs i förväg med `astryx theme build <fil>`, som ger `<namn>.css`, `<namn>.js` (med
`__built: true`), `.d.ts` och `.css.d.ts`. Det rekommenderas för SSR, "where styles must be present
on first paint"; ett obyggt tema kompileras i webbläsaren av `Theme` [LÄST
`astryx/packages/cli/assets/docs/author-a-theme.doc.mjs:122-135`;
`astryx/docs/architecture/theme-application.md`, INV4]. Efter varje uppgradering av Astryx måste
eget tema byggas om; körtiden "will not repair stale CSS from an older build" [LÄST
`author-a-theme.doc.mjs:136`].

### 2.4 React Server Components

- Varje fil som använder ett klient-API i React (`useState`, `useContext`, `createContext` m.fl.)
  har `'use client'` som första sats, och det vaktas av `scripts/check-use-client.mjs` och
  `packages/core/src/serverSafeComponents.test.ts`, som också fäller ett onödigt direktiv [LÄST
  båda filernas huvuden]. `Table`, `TabList`, `Button` och `Text` har direktivet [LÄST första
  raderna i respektive `.tsx`]. Man kan alltså importera dem i en serverkomponent; de blir
  klientgränser.
- `Theme` och `LinkProvider` ska ligga i en egen `'use client'`-fil (`providers.tsx`) [LÄST
  `astryx/packages/core/README.md`, "Next.js (simplest)"]. Ett tema med funktioner i sitt
  ikonregister får inte skickas som prop från server till klient
  [LÄST `astryx/docs/architecture/theme-application.md`, "System model"].
- Mörkt läge vid första målningen: "A server-rendered app also sets `<html data-theme="dark">` in
  its root layout" [LÄST `astryx/packages/cli/assets/docs/use-a-theme.doc.mjs`]. Snajp gör redan
  det [LÄST `app/layout.tsx:123`].
- I18n på servern: "A server/RSC translation runtime … remain[s] separate decisions" [LÄST
  `astryx/docs/architecture/internationalization.md`, "Compatibility/readiness"]. Komponenternas
  egna strängar översätts alltså i klienten.
- Rik text: "Server rendering outputs no document content" i `RichTextView`/`RichTextEditor`; för
  serverrenderad text används core `Markdown` [LÄST `astryx/packages/richtext/README.md`].

---

## 3. Temasystemet

### 3.1 Vad ett tema består av

`defineTheme(input)` tar [LÄST `astryx/packages/core/src/theme/defineTheme.ts:275-610`]:

| Fält | Format | Vad det gör |
|---|---|---|
| `name` | sträng | Blir `data-astryx-theme="<name>"`, som temats CSS är scopad till |
| `extends` | ett `DefinedTheme` | Ärver allt; resultatet är platt, en självständig CSS-fil |
| `typography` | `{scale: {base, ratio}, body, heading, code}`; varje roll `{family, fallbacks, weight, weights}` | Genererar `--font-size-*`, `--text-*` och `--font-family-*`. Teckensnitt laddas av konsumenten |
| `motion` | `{tempo, character}` och/eller `{fast, medium, slow?, ratio}` | Genererar `--duration-*` och kurvorna `--ease-entrance`/`--ease-move` |
| `radius` | `{base, multiplier}` | Genererar `--radius-inner` … `--radius-page` |
| `color` | `{accent: hex \| [ljus, mörk], neutralStyle, contrast}` | Genererar accent- och neutralroller ur ett frö (HCT). Bara `#RRGGBB` [LÄST `expandColorScale.ts:67-96`] |
| `palette` | `themePalette({accent, neutral})` ur `@astryxdesign/core/palette` | Färdiga färgtokens plus kontrastlyft för sekundär text |
| `tokens` | `{'--namn': sträng \| [ljus, mörk]}` | Explicita överskrivningar; vinner över allt genererat. En tuple blir `light-dark()` [LÄST `theme-tokens.md` INV4] |
| `localTokens` | samma format | Temats egna namn utanför standardvokabulären |
| `components` | `{komponent: {base, 'variant:x', '@light', '@dark', …}}` | Överskriver CSS-egenskaper per komponentmål. Privata `--_`-variabler är förbjudna: "theme build will error" [LÄST `author-a-theme.doc.mjs:84`] |
| `icons`, `componentIcons`, `iconVariants`, `indicators` | register | Ikoner per tema |
| `syntax` | `defineSyntaxTheme` | Kodfärger |
| `onDark`, `onLight` | överskrivningar | Ytor ovanpå media |
| `adaptations` | regler `{when: {pointer, width}, value}` | Blir mediefrågor, t.ex. större bas på pekskärm |

Företräde: bastema → genererade skalor → palett → explicita `tokens` → komponenter → media →
lokala tokens → ikoner [LÄST `theme-authoring-contract.md`, "Normalization follows one precedence
order"].

### 3.2 Tokenrollerna

Alla med standardvärde i `astryx/packages/core/src/theme/tokens.stylex.ts` [LÄST]:

**Färg** (rad 25–179). Grammatiken har fem former: `--color-<egenskap>-<roll>` där egenskapen är
`text`, `icon`, `background` eller `border`; `--color-<avsikt>` (`accent`, `neutral`, `info`,
`success`, `warning`, `error`); en variant med `-muted`, `-emphasized`, `-hover`, `-pressed`,
`-inverted`; `--color-on-<fyllning>`; och domänlager `--color-data-*`, `--color-syntax-*` [LÄST
`theme-tokens.md` INV10].
- Kärna: `--color-accent`, `-accent-muted`, `--color-on-accent`, `--color-neutral`,
  `--color-overlay` (+`-hover`, `-pressed`).
- Ytor: `--color-background-{surface,body,muted,card,popover,inverted,error-inverted}`.
- Text: `--color-text-{primary,secondary,disabled,accent}`, `--color-on-dark`, `--color-on-light`.
- Ikon: `--color-icon-{accent,primary,secondary,disabled}`.
- Status ×4 (`info`, `success`, `warning`, `error`): stark fyllning `--color-<s>`, innehåll på den
  `--color-on-<s>`, blek fyllning `--color-<s>-muted`, innehåll på den `--color-on-<s>-muted`,
  statustext `--color-text-<s>`, och `--color-icon-<s>`/`--color-border-<s>` som standard pekar på
  texten. Kontrastgolv: 4,5:1 för text och innehåll [LÄST `theme-tokens.md` INV11].
- Kanter: `--color-border`, `--color-border-emphasized`, och `--color-border-control` för fältens
  kant, som ska hålla 3:1 [LÄST `theme-tokens.md` INV13, DEC-2].
- Effekter: `--color-skeleton`, `--color-track`, `--color-shadow`, `--color-tint-hover`.
- Kategorifärger ×10 nyanser (blue, cyan, gray, green, orange, pink, purple, red, teal, yellow),
  var och en med `background`, `border`, `icon`, `text`.

**Avstånd** (rad 190–206): `--spacing-0` … `--spacing-12` med halvsteg, i `rem`
(`--spacing-4` = 1rem) [LÄST; `theme-tokens.md` INV9].
**Storlek** (214–218): `--size-element-{sm,md,lg}` = 28/32/36px.
**Kant** (226): `--border-width`.
**Fokus** (243–248): `--focus-outline-{width,style,color,offset}` = 2px, solid, accent, 3px. Villkoret
`:focus-visible` ligger kvar i core, så ett tema kan styla ringen men inte visa den för musanvändare
[LÄST kommentaren rad 237–241].
**Radie** (256–264): `--radius-{none,inner,element,container,page,chat,full}`.
**Skugga** (275–290): `--shadow-{low,med,high}` och de inre `--shadow-inset-{hover,selected,success,warning,error}`.
**Rörelse** (302–341): `--duration-{fast,medium,slow}` med `-min`/`-max`, `--duration-exit`,
`--ease-{standard,entrance,move,exit}`.
**Typografi** (350–481): `--font-family-{body,code,heading}`, `--font-size-4xs` … `-5xl`,
`--font-weight-{normal,medium,semibold,bold}`, och semantiska roller
`--text-{heading-1..6,body,large,label,code,supporting,display-1..3}-{size,weight,leading}`.
Standardskala: bas 14px, kvot 1,2.

### 3.3 Ljust och mörkt läge

- Ett lägesberoende värde är EN token med `light-dark()` eller en tuple `[ljus, mörk]` [LÄST
  `theme-tokens.md` INV4].
- `light-dark()` löses av CSS-egenskapen `color-scheme`. `reset.css` sätter den ur `<html
  data-theme>`: `light`, `dark`, och `light dark` när attributet saknas [LÄST
  `astryx/packages/core/src/reset.css:381-391`].
- `<Theme mode>` tar `'system'` (standard), `'light'` eller `'dark'`. Rot-`Theme` skriver
  `data-theme` och `data-astryx-theme` på `<html>`, tar bort `data-theme` i `system`, och städar
  båda vid avmontering. Inbäddade `Theme` rör inte `<html>` [LÄST `Theme.tsx:320-356`;
  `theme-application.md` INV2].
- Ett tema kan exportera `colorModes` (`['light','dark']`, eller ett läge) [LÄST
  `author-a-theme.doc.mjs:53`; `chocolateTheme.ts`, `export const colorModes`].
- `MediaTheme` markerar en lokal yta som mörk eller ljus utan att byta tema [LÄST
  `theme-application.md`, "System model"].

### 3.4 Två sätt att avbilda Snajps OKLCH-tokens, och valet

Snajp skriver färgerna som tripletter `L C H` i `:root` och använder dem som
`oklch(var(--ink))`, med alfa `oklch(var(--ink) / 0.12)`. Mörkt läge byter värdena under
`:root[data-theme="dark"]`, och en kunds palett skrivs över `:root` i en `<style>` [LÄST
`app/globals.css:7-72, 112-166`; `lib/tenants/index.ts:120-140`; `app/layout.tsx:143`].

**A. Peka på Snajps variabler** (`'--color-text-primary': 'oklch(var(--ink))'`). Kundpaletten och
mörkt läge följer med automatiskt, eftersom Snajps variabler redan byter värde. Astryx tar emot
värdet: en token är bara en sträng som måste gå att skriva som en enda CSS-deklaration [LÄST
`declarationBoundary.ts:1-29`; `defineTheme.ts:172` `TokenValue`]. **Men** Astryx härleder
statusrollerna (`--color-on-<s>`, `--color-text-<s>`) bara ur konkreta färger: "When one is not (an
oklch() value, an unknown reference), the status keeps its scoped aliases instead of a guess"
[LÄST `statusRoleDerivation.ts:180-182`]. Kontrasttesterna i förlagan gäller dessutom bara
Astryx egna teman: "a value a third-party theme sets is that theme's own" [LÄST
`theme-tokens.md` INV11]. Alla roller måste alltså sättas för hand och mätas av oss.

**B. Skriva ut konkreta värden** (`['oklch(0.20 0.018 252)', 'oklch(0.94 0.006 88)']`). Astryx kan
då härleda och kontrollera mer, men en kunds palett når inte komponenterna, och två sanningar om
samma färg måste hållas i takt.

[BEDÖMNING] **Välj A.** Snajps hela temamodell bygger på att "Byts tokens byts därför allt"
[LÄST `app/globals.css:83-89`], och kundpaletten är en produktfunktion. B bryter båda. Kostnaden
för A är en mätning, som Snajp ändå kräver ("Contrast is measured, not estimated", [LÄST
`DESIGN.md:96`]).

Följd av A: värden som ska vara samma i båda lägena men vända (innehåll på accent, skuggor,
scrim) kan inte bara peka på `--ink`, eftersom `--ink` är ljus i mörkt läge [LÄST
`app/globals.css:117`]. De skrivs som tuple eller med `light-dark()` inne i strängen, som core
själv gör för skuggor [LÄST `tokens.stylex.ts:277-282`]. Det kräver att `color-scheme` stämmer,
vilket det gör eftersom Snajp sätter `style={{colorScheme}}` på `<html>` [LÄST
`app/layout.tsx:124`] och `Theme` sätter `colorScheme` på sitt omslag [LÄST `Theme.tsx:106-114`].

### 3.5 Utkast: Snajp-temat

Filen: `lib/crm/astryx/snajpTema.ts`. Den ärver `neutralTheme` för ikonregister, komponentregler
och kategorifärger, och skriver över allt som syns som Snajp [BEDÖMNING]. Värdena är ett utkast:
varje rad märkt `MÄT` ska kontrastmätas i ljust och mörkt läge innan första commit, enligt
`DESIGN.md` § Accessibility floor.

```ts
// lib/crm/astryx/snajpTema.ts
// Snajps tema för Astryx. Varje färg pekar på Snajps egna OKLCH-variabler i app/globals.css,
// så kundens palett (lib/tenants paletteToCss) och mörkt läge (:root[data-theme="dark"])
// följer med utan kod här. Se docs/crm/underlag/astryx-designsystemet.md §3.4.
import {defineTheme} from '@astryxdesign/core/theme';
import {neutralTheme} from '@astryxdesign/theme-neutral';

const c = (v: string, a?: number) => (a == null ? `oklch(var(${v}))` : `oklch(var(${v}) / ${a})`);
// Fasta mörka och ljusa värden där rollen inte får vända med --ink/--paper.
const INK_FAST = 'oklch(0.20 0.018 252)';
const PAPER_FAST = 'oklch(0.965 0.008 88)';

export const colorModes = ['light', 'dark'] as const;

export const snajpTema = defineTheme({
  name: 'snajp',
  extends: neutralTheme,

  typography: {
    // Appytornas löptext är 0.9375rem (DESIGN.md § App surfaces). Rubrikerna sätts
    // nedan i tokens, eftersom skalan inte träffar Snajps 1.75/1.5/1.0625rem.
    scale: {base: 15, ratio: 1.2},
    heading: {weights: {1: 'semibold', 2: 'normal', 3: 'semibold'}},
  },

  // Fält under 16px zoomas av iOS (DESIGN.md "Inputs never below 16px").
  // Samma mönster som chocolate-temat (packages/themes/chocolate/src/chocolateTheme.ts).
  adaptations: {
    rules: [{when: {pointer: 'coarse', width: {below: 'lg'}}, value: {typography: {scale: {base: 16, ratio: 1.2}}}}],
  },

  motion: {fast: 180, medium: 300, slow: 700, ratio: 0.75},

  tokens: {
    // Typsnitt: next/font ger variablerna (lib/fonts.ts). Fraunces bara för rubriker.
    '--font-family-body': 'var(--font-geist), ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
    '--font-family-heading': 'var(--font-fraunces), ui-serif, Georgia, serif',
    '--font-family-code': 'var(--font-jetbrains), ui-monospace, "SFMono-Regular", monospace',
    '--text-heading-1-size': '1.75rem',   // Sidhuvud, rubrikSida
    '--text-heading-2-size': '1.5rem',    // Sektion, rubrikSektion
    '--text-heading-3-size': '1.0625rem', // rubrikPanel (Geist i Snajp; se §3.6)
    '--text-label-size': '0.8125rem',     // etikett
    '--text-supporting-size': '0.8125rem',// meta

    // Kärna. Ochre är den enda accenten (DESIGN.md "Accent discipline").
    '--color-accent': c('--ochre'),
    '--color-accent-muted': c('--ochre', 0.14),
    '--color-on-accent': [INK_FAST, 'oklch(0.185 0.010 252)'],          // MÄT: ink på ochre 7.56:1 enligt DESIGN.md
    '--color-neutral': c('--ink', 0.07),
    '--color-overlay': ['oklch(0.20 0.018 252 / 0.40)', 'oklch(0 0 0 / 0.60)'],
    '--color-overlay-hover': c('--ink', 0.05),
    '--color-overlay-pressed': c('--ink', 0.10),

    // Ytor. Papper är aldrig #fff; paper2 alltid med hårlinje.
    '--color-background-body': c('--paper'),
    '--color-background-surface': c('--paper'),
    '--color-background-card': c('--paper'),
    '--color-background-popover': c('--paper'),
    '--color-background-muted': c('--paper2'),
    '--color-background-inverted': c('--ink'),
    '--color-background-error-inverted': c('--danger'),

    // Text. Dämpad text alltid som token, aldrig opacitet (DESIGN.md).
    '--color-text-primary': c('--ink'),
    '--color-text-secondary': c('--ink-muted'),                         // 7.63:1 / paper2 6.87:1
    '--color-text-disabled': c('--paper-subtle'),                       // inaktiv text har inget AA-krav
    '--color-text-accent': c('--warning'),                              // textsäker ochre, 5.63:1
    '--color-on-dark': PAPER_FAST,
    '--color-on-light': INK_FAST,

    // Ikoner. Ochre (2.17:1) klarar inte 3:1 för en ikon på papper; warning gör det.
    '--color-icon-primary': c('--ink'),
    '--color-icon-secondary': c('--ink-muted'),
    '--color-icon-disabled': c('--paper-subtle'),
    '--color-icon-accent': c('--warning'),

    // Kanter. Hårlinjen är ink/12 som i panelKort (components/ui.tsx).
    '--color-border': c('--ink', 0.12),
    '--color-border-emphasized': c('--ink', 0.25),
    '--color-border-control': c('--mineral'),                           // 3:1-kravet: mineral 5.41:1 / paper2 4.88:1

    // Effekter. Skuggan får inte bli ett ljust sken i mörkt läge (app/globals.css:171-186).
    '--color-skeleton': c('--ink', 0.08),
    '--color-track': c('--ink', 0.15),
    '--color-shadow': ['oklch(0.20 0.018 252 / 0.12)', 'oklch(0 0 0 / 0.50)'],

    // Status. Varje roll sätts för hand: Astryx härleder inte ur oklch(var(...)).
    '--color-success': c('--moss'),
    '--color-on-success': c('--paper'),                                 // MÄT båda lägen
    '--color-success-muted': c('--moss', 0.14),
    '--color-on-success-muted': c('--moss'),                            // MÄT
    '--color-text-success': c('--moss'),                                // MÄT
    '--color-error': c('--danger'),
    '--color-on-error': c('--paper'),                                   // 5.22:1 i ljust; MÄT mörkt
    '--color-error-muted': c('--danger', 0.12),
    '--color-on-error-muted': c('--danger'),                            // MÄT
    '--color-text-error': c('--danger'),                                // 5.22:1 / paper2 4.72:1
    '--color-warning': c('--ochre'),
    '--color-on-warning': [INK_FAST, 'oklch(0.185 0.010 252)'],         // MÄT
    '--color-warning-muted': c('--ochre', 0.12),
    '--color-on-warning-muted': c('--warning'),                         // 5.13:1 på ochre/12
    '--color-text-warning': c('--warning'),
    '--color-info': c('--chart-blue'),                                  // Snajp har ingen info-färg; MÄT
    '--color-on-info': c('--paper'),                                    // MÄT
    '--color-info-muted': c('--chart-blue', 0.12),
    '--color-on-info-muted': c('--chart-blue'),                         // MÄT
    '--color-text-info': c('--chart-blue'),                             // MÄT

    // Kategorifärgerna som Badge/Token/StatusDot läser. Resten ärvs från neutral.
    '--color-background-gray': c('--ink', 0.08),
    '--color-border-gray': c('--mineral'),
    '--color-icon-gray': c('--ink-muted'),
    '--color-text-gray': c('--ink'),
    '--color-background-green': c('--moss', 0.14),
    '--color-border-green': c('--moss'),
    '--color-icon-green': c('--moss'),
    '--color-text-green': c('--moss'),                                  // MÄT
    '--color-background-red': c('--danger', 0.12),
    '--color-border-red': c('--danger'),
    '--color-icon-red': c('--danger'),
    '--color-text-red': c('--danger'),
    '--color-background-yellow': c('--ochre', 0.14),
    '--color-border-yellow': c('--ochre'),
    '--color-icon-yellow': c('--warning'),
    '--color-text-yellow': c('--warning'),
    '--color-background-blue': c('--chart-blue', 0.12),
    '--color-border-blue': c('--chart-blue'),
    '--color-icon-blue': c('--chart-blue'),
    '--color-text-blue': c('--chart-blue'),                             // MÄT

    // Fokus: ochre, 2px, 2px avstånd, inga undantag (DESIGN.md § Accessibility floor).
    // --focus följer kundens ochre (lib/tenants/index.ts:136-137).
    '--focus-outline-color': c('--focus'),
    '--focus-outline-width': '2px',
    '--focus-outline-offset': '2px',

    // Radier: input 8, kort 12, panel 20 (tailwind.config.ts borderRadius).
    '--radius-inner': '4px',
    '--radius-element': '8px',
    '--radius-container': '12px',
    '--radius-page': '20px',

    // Skuggor: bara produktytor (DESIGN.md). Färgen i light-dark() per skuggled.
    '--shadow-low': '0 0 0 1px light-dark(oklch(0.20 0.018 252 / 0.09), oklch(1 0 0 / 0.10))',
    '--shadow-med': '0 4px 16px light-dark(oklch(0.20 0.018 252 / 0.08), oklch(0 0 0 / 0.45))',
    '--shadow-high': '0 24px 70px light-dark(oklch(0.20 0.018 252 / 0.12), oklch(0 0 0 / 0.55))',
    '--shadow-inset-selected': 'inset 0 0 0 2px oklch(var(--ochre) / 0.55)',
    '--shadow-inset-error': 'inset 0 0 0 2px oklch(var(--danger) / 0.45)',
    '--shadow-inset-success': 'inset 0 0 0 2px oklch(var(--moss) / 0.45)',
    '--shadow-inset-warning': 'inset 0 0 0 2px oklch(var(--ochre) / 0.55)',

    // Rörelse: Snajps enda kurva (DESIGN.md § Motion). Utgången behåller Astryx accelererande kurva.
    '--ease-standard': 'cubic-bezier(0.16, 1, 0.3, 1)',
    '--ease-entrance': 'cubic-bezier(0.16, 1, 0.3, 1)',
    '--ease-move': 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
});
```

Avbildningen som tabell (Snajp-token → Astryx-roll):

| Snajp | Astryx-roll(er) | Anmärkning |
|---|---|---|
| `--ink` | `text-primary`, `icon-primary`, `background-inverted`, `text-gray`; alfa för `border`, `neutral`, `overlay-hover/pressed`, `skeleton`, `track` | Vänder i mörkt läge |
| `--ink2` | ingen direkt roll | Snajp använder den för hovring på primärknapp (`btnPrimary`, `components/ui.tsx:16`). Kan bli `components.button['variant:primary'][':hover']` [ANTAGANDE om nyckelformen] |
| `--paper` | `background-body`, `-surface`, `-card`, `-popover`; `on-success`, `on-error`, `on-info` | |
| `--paper2` | `background-muted` | "Raised plane, always WITH a hairline" |
| `--mineral` | `border-control`, `border-gray` | Kickerfärg i Snajp; här kant för fält |
| `--ink-muted` | `text-secondary`, `icon-secondary`, `icon-gray` | |
| `--ink-subtle` | ingen direkt roll | Snajps `meta`; Astryx har bara en sekundär textnivå. Sätt på `Text color` eller med `className` |
| `--paper-muted`, `--paper-subtle` | `text-disabled`, `icon-disabled` (subtle) | I Snajp avsedda för den mörka railen. `paper-muted` får ingen roll |
| `--seal` | ingen | Djupt plan på mörka sektioner, utanför CRM:et |
| `--ochre` | `accent`, `accent-muted`, `warning`, kategorin `yellow`; via `--focus` fokusringen | |
| `--warning` (textsäker ochre) | `text-accent`, `icon-accent`, `text-warning`, `on-warning-muted` | |
| `--moss` | `success` och dess roller, kategorin `green` | |
| `--danger` | `error` och dess roller, `background-error-inverted`, kategorin `red` | |
| `--chart-blue` | `info` och dess roller, kategorin `blue` | Lånad; Snajp har ingen info-färg [BEDÖMNING] |
| Fraunces | `--font-family-heading` | Via `var(--font-fraunces)` |
| Geist | `--font-family-body` | Via `var(--font-geist)` |
| JetBrains Mono | `--font-family-code` | |
| `--radius-input/card/panel` | `--radius-element/container/page` | 8/12/20px |
| `--ease-out`, `--dur-short`, `--dur-mid` | `--ease-standard/entrance/move`, `motion.fast/medium` | 180/300ms |
| `--focus` | `--focus-outline-color` | Offset 2px i stället för Astryx 3px |

### 3.6 Det temat inte kan uttrycka

- **Rubrikteckensnitt per nivå.** Astryx har ett `--font-family-heading` för alla nivåer
  [LÄST `tokens.stylex.ts:350-356`]. Snajp sätter sidtitel och sektion i Fraunces men paneltitlar i
  Geist [LÄST `DESIGN.md:172-176`]. Antingen `Heading level={3}` med `className="font-sans"`, eller
  en komponentöverskrivning för `heading` på nivå 3 om ett sådant mål finns. [MÅSTE PRÖVAS] med
  `astryx component Heading --detail full`, som listar målen [LÄST `author-a-theme.doc.mjs:84`].
- **Två nivåer dämpad text.** Se `--ink-subtle` ovan.
- **Primärknappen.** Astryx primärknapp fylls med `--color-accent` och skriver med
  `--color-on-accent` [LÄST `astryx/packages/core/src/Button/Button.tsx:329-332`]. Med ochre som
  accent blir den ochre med mörk text, vilket stämmer med DESIGN.md ("Ochre on: the primary
  CTA", [LÄST `DESIGN.md:93`]) men inte med `btnPrimary` i `components/ui.tsx:16`, som är ink.
  Anton bör välja. Vill han ha ink: `components.button['variant:primary']` med `backgroundColor`
  och `color`, inte de privata `--_button-fill`-variablerna [LÄST `author-a-theme.doc.mjs:84`].
- **Flikarna** markerar vald flik med `--color-accent` [LÄST `astryx/packages/core/src/TabList/Tab.tsx:208`],
  alltså ochre, som Snajps `flikAktiv` [LÄST `components/ui.tsx:129`]. Höjden 44px och understrykningens
  tjocklek är [MÅSTE PRÖVAS].

---

## 4. Komponentkatalogen

Källa för varje rad: komponentens `.doc.mjs` under `astryx/packages/core/src/<Namn>/` (namn,
kategori, beskrivning, propnamn, extraherade som text). Kategorierna är förlagans egna. Props
anges som namn; typerna står i respektive `.doc.mjs`.

### 4.1 Core, per kategori

**Action**
| Komponent | Vad den gör | Viktigaste props |
|---|---|---|
| `Button` | Knapp | `label`, `variant` (`primary`/`secondary`/`ghost`/`destructive`), `size` (`sm`/`md`/`lg`), `icon`, `isLoading`, `isDisabled`, `onClick`, `href`, `tooltip`, `endContent` |
| `IconButton` | Bara ikon, kräver `label` | `label`, `icon`, `variant`, `size`, `tooltip`, `onClick` |
| `ButtonGroup` | Sammanfogade knappar | barn |
| `ToggleButton`, `ToggleButtonGroup` | Av/på, ensam eller grupp (single/multi) | `isPressed`, `onPressedChange`; gruppen `type`, `value`, `onChange` |
| `SegmentedControl` (+`Item`) | Segmentväljare | `value`, `onChange`, `label`, `size`, `layout` |
| `DropdownMenu` (+`Item`, `CheckboxItem`, `RadioGroup`, `RadioItem`, `Group`, `Divider`, `SubMenu`) | Åtgärdsmeny med trigger | `button`, `renderTrigger`, `items`, `presentation`, `placement`, `header`, `footer` |
| `MoreMenu` | "…"-meny | `items`, `label`, `placement`, `presentation` |
| `ContextMenu` (+`Item`) | Högerklicksmeny | `items`, `menuContent`, `onOpenChange` |
| `Toolbar` | Vågrät rad med start/mitt/slut | `startContent`, `centerContent`, `endContent`, `size`, `variant`, `dividers` |
| `Link`, `LinkProvider`, `useLinkify` | Länk; ramverkslänk för alla komponenter | `LinkProvider component={NextLink}` |

**Container**
| `Card` | Yta | `padding`, `variant` (kategorifärger), `elevation`, `width`, `maxWidth` |
|---|---|---|
| `ClickableCard`, `SelectableCard` | Klickbart kort; valbart kort | nästlade kontroller fungerar för sig |
| `Collapsible`, `CollapsibleGroup` | Fällbart innehåll | `trigger`, `isOpen`, `defaultIsOpen`, `onOpenChange`; gruppen `type` single/multiple |
| `Carousel` | Vågrät rullning med snäpp | barn |

**Content**
| `Text`, `Heading` | Text och rubrik med typroller | `type`, `size`, `color`, `weight`, `maxLines`, `hasTabularNumbers`; `Heading level` |
|---|---|---|
| `Avatar`, `AvatarGroup`, `AvatarGroupOverflow`, `AvatarStatusDot` | Avatar med initialer och status | `src`, `name`, `size`, `shape`, `status` |
| `Token` | Chip/tagg, kan tas bort | `label`, `color`, `icon`, `onRemove`, `onClick`, `href` |
| `Badge` | Status- eller kategoritagg, inte metadata | `variant`, `label`, `icon` |
| `EmptyState` | Tomläge | `title`, `description`, `icon`, `actions`, `isCompact` |
| `Icon`, `Kbd`, `Code`, `CodeBlock`, `Blockquote`, `Citation`, `Thumbnail` | Ikon, tangent, kod, citat, miniatyr | — |
| `Markdown` | Markdown-renderare, serverbar | `children`, `plugins`, `isStreaming` |
| `Timestamp`, `Timer` | Tid och förfluten tid | `value`, `format`, `timezoneID`, `isLive` |

**Feedback & Status**
| `Banner` | Statusbanner | `status`, `title`, `description`, `isDismissable`, `onDismiss` |
|---|---|---|
| `ProgressBar` | Förlopp, bestämt eller obestämt | `value`, `max`, `isIndeterminate`, `label` |
| `Skeleton` | Skelett | `width`, `height`, `radius`, `index` |
| `Spinner`, `StatusDot`, `InfoTip` | Snurra, statusprick, info-ikon | `label` |

**Form Controls**
| `TextInput`, `TextArea`, `NumberInput` | Textfält | `label`, `value`, `onChange`, `status`, `description`, `isRequired`, `hasClear`, `placeholder` |
|---|---|---|
| `Selector` (+`SelectorOption`) | Select, med valfri sökning (combobox) | `options`, `value`, `onChange`, `hasSearch`, `renderOption`, `presentation` |
| `MultiSelector` | Flerval med kryssrutor | `options`, `value`, `onChange`, `hasSearch`, `hasSelectAll`, `hasCreate`, `maxBadges` |
| `ComplexSelector` | Skal för egna rika väljare | `triggerLabel`, `children`, `value`, `onChange` |
| `Typeahead`, `BaseTypeahead`, `TypeaheadItem` | Autokomplettering mot en sökkälla | `searchSource`, `value`, `onChange`, `renderItem`, `debounceMs` |
| `Tokenizer` | Flera värden som chips, med sökning och skapa | `searchSource`, `value`, `onChange`, `hasCreate`, `renderToken`, `maxEntries` |
| `PowerSearch` | Filterfält med operatorer (fält, operator, värde) | `config`, `filters`, `onChange`; `usePowerSearchConfig` |
| `DateInput`, `DateRangeInput`, `DateTimeInput`, `TimeInput` | Datum/tid, med kalenderpopover och förval | `value`, `onChange`, `min`, `max`, `presets`, `weekStartsOn`, `calendar`, `nativePicker` |
| `Calendar` | Månadskalender för val av datum eller intervall | `mode`, `value`, `onChange`, `numberOfMonths`, `hasWeekNumbers`, `weekStartsOn` |
| `CheckboxInput`, `CheckboxList`, `RadioList`, `Switch`, `Slider` | Val | `value`, `onChange`, `label` |
| `FileInput` | Filuppladdning | `accept`, `isMultiple`, `maxSize`, `maxFiles` |
| `Field`, `FieldLabel`, `FieldStatus`, `InputGroup`, `InputGroupText` | Fältskal, etikett, valideringsmeddelande (live-region), prefix/suffix | — |
| `Indicator` | Markeringsgrafik (kryss, radio) | utbytbar via tema |

**Layout**
| `AppShell` | Appskal med toppnav, sidonav, mobilnav, banner | `topNav`, `sideNav`, `mobileNav`, `banner`, `contentPadding` |
|---|---|---|
| `Layout` (+`LayoutHeader`, `LayoutContent`, `LayoutPanel`, `LayoutFooter`) | Fem fack: header, start, innehåll, slut, footer | `header`, `start`, `content`, `end`, `footer`; `LayoutPanel resizable` |
| `Stack`, `HStack`, `VStack`, `StackItem`, `Grid`, `GridSpan`, `Center` | Flex och grid med tokenavstånd | `gap` (0–10), `align`, `justify`, `padding`, `columns` |
| `Section`, `Divider`, `AspectRatio`, `ScrollableArea`, `Resizable`/`useResizable` | Sektioner, avdelare, rullyta, storleksändring | `useResizable` sparar storlek i localStorage |
| `FormLayout` | Formulärlayout | `direction`, `defaultOptionality` |

**Navigation**
| `TopNav` (+`TopNavHeading`, `TopNavItem`, `TopNavMenu`, `TopNavMegaMenu`) | Toppnavigering | `heading`, `startContent`, `endContent` |
|---|---|---|
| `SideNav` (+`SideNavHeading`, `SideNavSection`, `SideNavItem`, `SideNavCollapseButton`) | Sidonavigering, fällbar och storleksändringsbar ("navigationsrail") | `header`, `footer`, `collapsible`, `resizable`; `SideNavItem label, icon, href, isSelected` |
| `MobileNav`, `MobileNavToggle` | Utdragsmeny för mobil | barn som SideNav |
| `TabList`, `Tab`, `TabMenu` | Flikar; nav-landmärke eller WAI-ARIA tablist | `value`, `onChange`, `size`, `layout`, `role`, `overflow`; `Tab value, label, href, panelId` |
| `Breadcrumbs`, `BreadcrumbItem` | Brödsmulor | `separator`, `label`; `href`, `isCurrent`, `menu` |
| `Pagination` | Sidnumrering | `page`, `onChange`, `totalItems`, `pageSize`, `pageSizeOptions` |
| `Stepper`, `Step` | Stegföljd | `activeStep`; `label`, `status` |
| `Outline`, `NavIcon`, `NavHeadingMenu` | Innehållsförteckning, navikoner | — |

**Overlay**
| `Dialog` (+`DialogHeader`, `useImperativeDialog`) | Modal på native `<dialog>` | `isOpen`, `onOpenChange`, `width`, `purpose`, `padding` |
|---|---|---|
| `AlertDialog`, `useImperativeAlertDialog` | Bekräfta destruktiv åtgärd | `title`, `description`, `actionLabel`, `onAction`, `cancelLabel` |
| `Drawer` (+`DrawerHeader`) | Sidopanel från start- eller slutkanten, på `<dialog>`, flyttar inte layouten | `isOpen`, `onOpenChange`, `side`, `width`, `hasScrim`, `label` |
| `BottomSheet` | Mobilark nerifrån med snäpppunkter | `snapPoints`, `height` |
| `CommandPalette` (+`Input`, `List`, `Group`, `Item`, `Empty`, `Footer`) | Kommandopalett | `isOpen`, `onOpenChange`, `searchSource`, `renderItem` |
| `Popover`, `usePopover` | Klickpopover, knapp+dialog-mönstret | `content`, `isOpen`, `placement`, `hasLightDismiss`, `isModal` |
| `HoverCard`, `useHoverCard` | Rik förhandsvisning vid hovring/fokus | `content`, `delay`, `placement` |
| `Tooltip`, `useTooltip` | Kort text vid hovring/fokus | `content`, `delay`, `placement` |
| `Toast`, `useToast` | Toast; ingen provider krävs | `body`, `type`, `isAutoHide`, `autoHideDuration` |
| `Overlay`, `Lightbox`, `Layer`/`useLayer` | Lager över media, bildvisare, positioneringskärna | `useLayer` bygger på Popover-API och CSS anchor positioning |

**Table & List**
| `Table` (+`TableHeader`, `TableBody`, `TableFooter`, `TableRow`, `TableCell`, `TableHeaderCell`, `TableSelectionToolbar`) | Datastyrd tabell med insticksprogram | `data`, `columns`, `idKey`, `density`, `dividers`, `isStriped`, `hasHover`, `virtualization`, `plugins`, `emptyState` |
|---|---|---|
| `List`, `ListItem`, `Item` | Lista med täthet, avdelare, svep, omordning | `density`, `hasDividers`, `reorderable`; `label`, `description`, `startContent`, `endContent` |
| `MetadataList`, `MetadataListItem` | Etikett–värde-par i kolumner | `columns`, `orientation`, `maxNumOfItems` |
| `TreeList` | Träd med expandering | `items`, `density`, `variant` |
| `OverflowList` | Visa så många som får plats, resten i "+n" | `overflowRenderer`, `maxVisibleItems` |

**Chat** (`Chat`, `ChatLayout`, `ChatComposer`, `ChatComposerInput`, `ChatMessage`,
`ChatMessageBubble`, `ChatMessageList`, `ChatSystemMessage`, `ChatToolCalls`, m.fl.): byggstenar för
konversationsgränssnitt, `ChatMessageList` har `role="log"` och `aria-live="polite"`.

**Utility och i18n**: `Theme`, `MediaTheme`, `SyntaxTheme`, `useTheme`, `useThemeName`,
`InternationalizationProvider`, `useTranslator`, `useLocale`, `useDirection`, `useCollator`,
`VisuallyHidden`.

**Hooks** (urval): `useHotkeys`, `useFocusTrap`, `useListFocus`, `useGridFocus`, `useTreeFocus`,
`useTypeahead`, `useCombobox`, `useMultiCombobox`, `useAnnounce`, `useClipboard`,
`useContainerReveal` ("row actions appear on hover"), `useMediaQuery`, `useScrollLock`,
`useOverflow`, `useTruncation`, `useLongPress`, `createReorderable`, `useAnimator`,
`useEntryAnimation` [LÄST respektive `.doc.mjs` under `astryx/packages/core/src/hooks/` m.fl.].

### 4.2 Det ett CRM behöver, punkt för punkt

| Behov | Finns? | Var och hur |
|---|---|---|
| **Datatabell** | Ja | `Table` [LÄST `Table/Table.doc.mjs`] |
| · virtualisering | Ja | `useTableRowsVirtualization({rowHeight, initialViewportHeight})` (fast radhöjd) och `useTableColumnsVirtualization`. Kräver `idKey` och en förälder med höjd. **En kolumn med `renderCell` stänger av fönstringen och renderar alla rader** [LÄST `Table.doc.mjs:264-267, 363`] |
| · kolumnbredd | Ja | `width: proportional(n, {minWidth})` eller `pixel(n)` per kolumn [LÄST `Table/types.ts:107-133`]; dragbar bredd med `useTableColumnResize`; synlighet och ordning med `useTableColumnSettings`; fasta kolumner med `useTableStickyColumns` |
| · sortering | Ja | `sortable: true` på kolumnen plus `useTableSortable` (bara rubrikerna; du sorterar själv, t.ex. på servern) eller `useTableSortableState` (sorterar i minnet, `sortedData`, Skift+klick för flera nycklar) [LÄST `plugins/sortable/useTableSortableState.doc.mjs`] |
| · markering | Ja | `useTableSelection` + `useTableSelectionState`, kryssrutor, markera alla, `aria-selected`; `TableSelectionToolbar` för massåtgärder |
| · redigering i cell | **Nej** | Ingen plugin eller prop för redigering finns i `Table/` [LÄST fillistan; sökning på "edit" i `Table.doc.mjs` gav inget]. Byggs med `renderCell` som lägger ett fält i cellen, eller med `transformBodyCell` i en egen `TablePlugin` [LÄST `Table.doc.mjs:270-273`]. Tangentbordsnavigering mellan celler: `useGridFocus` |
| · övrigt | Ja | Filter (`useTableFiltering`, `useTableFilterState`), sidnumrering, oändlig rullning, gruppering, radexpansion, radstatus, radnummer, träd, högerklicksmeny per cell. Ingen `onRowClick`: öppna en rad med `Link` eller `Button` i huvudcellen [LÄST `Table.doc.mjs:363`] |
| **Tavla/kanban** | Nej som komponent | Sidmallen `kanban-board` (881 rader, `'use client'`): kolumner, kort, pekardrag med tröskel 5px [LÄST `astryx/packages/cli/assets/templates/pages/kanban-board/page.tsx:3, 225-227`]. Inget tangentbordsalternativ till draget hittades i mallen [MÅSTE PRÖVAS]. `List reorderable` med `createReorderable` ordnar om inom en lista |
| **Kalender** | Delvis | `Calendar` är en datumväljare med månadsvy. En kalender med dag-, vecko-, månads- och listvy finns som `Schedule` i `lab` (`DayView`, `TimeGridView`, `MonthlyView`, `ListView`) [LÄST `astryx/packages/lab/src/Schedule/`], bara canary, inte tillgänglighetshärdad [LÄST `astryx/packages/lab/README.md`] |
| **Flikar** | Ja | `TabList` + `Tab`; `role="tablist"` och `panelId` när fliken byter panel på plats [LÄST `TabList/TabList.doc.mjs:76, 127`] |
| **Dialog** | Ja | `Dialog`, `AlertDialog`, `useImperativeDialog` |
| **Sidopanel/drawer** | Ja | `Drawer side`, eller `LayoutPanel` för en fast panel som tar plats i layouten |
| **Kommandopalett** | Ja | `CommandPalette` + `useHotkeys` |
| **Meny** | Ja | `DropdownMenu`, `MoreMenu`, `ContextMenu` |
| **Popover** | Ja | `Popover`, `HoverCard` |
| **Tooltip** | Ja | `Tooltip`, `InfoTip`, och `tooltip`-prop på knappar |
| **Toast** | Ja | `useToast` |
| **Formulärfält** | Ja | `TextInput`, `TextArea`, `NumberInput`, `Field`, `FormLayout`, `FieldStatus` |
| **Select/combobox** | Ja | `Selector hasSearch`, `MultiSelector`, `Typeahead`, `Tokenizer`, hooks `useCombobox`/`useMultiCombobox` |
| **Datumväljare** | Ja | `DateInput`, `DateRangeInput` med `presets`, `DateTimeInput`, `TimeInput` |
| **Taggar/chips** | Ja | `Token`, `Badge`, `Tokenizer` |
| **Avatar** | Ja | `Avatar`, `AvatarGroup` |
| **Brödsmulor** | Ja | `Breadcrumbs` |
| **Sidhuvud** | Ja | `LayoutHeader`, `TopNav`, `DialogHeader`; sidmallar `detail-page`, `table-page` |
| **Navigationsrail** | Ja | `SideNav collapsible` i `AppShell sideNav` |
| **Tomläge** | Ja | `EmptyState`, och `Table emptyState` |
| **Skelett** | Ja | `Skeleton`, och tabellens laddningsläge via plugins |
| **Diagram** | Bara canary | `@astryxdesign/charts`: `Chart` med märken `bar`, `line`, `area`, `dot`, `band`, `candlestick`, `errorBar`, `referenceLine`, WebGL-varianter, `ChartAxis`, `ChartGrid`, `ChartLegend`, `ChartTooltip` [LÄST `astryx/packages/charts/README.md`]. `@astryxdesign/vega`: `VegaChart` för Vega/Vega-Lite-specar [LÄST `astryx/packages/vega/README.md`]. KPI-ruta: `Stat` i lab |
| **Rik text** | Ja (stabil) | `@astryxdesign/richtext`: `RichTextEditor`, `RichTextView`, `RichTextEditorToolbar`, Markdown in och ut, på Lexical 0.52 [LÄST `astryx/packages/richtext/README.md`] |

### 4.3 Det som saknas och måste byggas ovanpå primitiverna

[BEDÖMNING utifrån §4.2]
1. **Kanban-tavla** för affärsflödet: utgå från mallen `kanban-board`, men lägg till
   tangentbordsflytt (t.ex. `MoreMenu` "Flytta till…" per kort, eller `useListFocus` + pilar) och
   skärmläsarmeddelanden med `useAnnounce`. Mallens drag är bara pekare.
2. **Redigering i cell**: en `TablePlugin` med `transformBodyCell` som byter visning mot
   `TextInput`/`Selector`/`DateInput` vid Enter eller dubbelklick, `useGridFocus` för navigering,
   `Escape` för att avbryta. Krocken med virtualisering (renderCell stänger av den) måste mätas.
3. **Kalender med dag/vecka** för möten och uppgifter: `Schedule` ur lab är canary och ohärdad.
   Antingen pinna en exakt canary-version och ta risken, eller bygga en enkel agenda med `List`
   och `Calendar`.
4. **Diagram**: `charts` och `vega` är canary. Snajp har redan `recharts` i `package.json` [LÄST].
   [BEDÖMNING] Behåll recharts för CRM:ets diagram tills `charts` får en stabil version, och färga
   det med Snajps tokens som i dag.
5. **KPI-rad**: `Stat` finns bara i lab. Snajps `Nyckeltal`/`Talrad` (`components/ui.tsx:213-258`)
   eller en `Grid` med `Text`/`Heading` gör samma sak.
6. **Aktivitetstidslinje** (mejl, samtal, anteckningar på en kontakt): ingen komponent; byggs med
   `List`, `Item`, `Timestamp`, `Avatar`. `Comments`/`CommentComposer` finns i lab.
7. **Sparade vyer och filterchips** ovanför en tabell: `PowerSearch` täcker filtret,
   vyväxlaren byggs med `TabList` eller `Selector`.

---

## 5. Tillgänglighet, tangentbord, fokus, rörelse, RTL och i18n

### 5.1 Tillgänglighet, tangentbord och fokus
- Fokusringen är en token-definition för hela systemet, och `:focus-visible` ligger i core så ett
  tema inte kan visa ringen för musanvändare [LÄST `tokens.stylex.ts:234-248`].
- Tangentbordsmodeller finns som delade hooks enligt WAI-ARIA: lista/meny (`useListFocus`),
  rutnät (`useGridFocus`), träd (`useTreeFocus`), fokusfälla för dialoger (`useFocusTrap`),
  typ-för-att-hoppa (`useTypeahead`), comboboxar (`useCombobox`, `useMultiCombobox`) [LÄST
  respektive `.doc.mjs`].
- `Dialog` och `Drawer` bygger på native `<dialog>` [LÄST `Dialog.doc.mjs`, `Drawer.doc.mjs`].
- Valideringsmeddelanden annonseras via beständiga live-regioner, assertive för fel
  (`FieldStatus`) [LÄST `FieldStatus.doc.mjs`]; `useAnnounce` för egna meddelanden.
- Status bärs aldrig bara av färg: i forced-colors ersätts statusroller av systemfärger och behåller
  en kant och en etikett eller ikon [LÄST `theme-tokens.md` INV11]; `AvatarStatusDot` ger varje
  status en egen form [LÄST `AvatarStatusDot.doc.mjs`].
- Fältens kant ska hålla 3:1 (`--color-border-control`) [LÄST `theme-tokens.md` INV13].
- Repot har tillgänglighetskontrakt i Playwright (`test:a11y-contract`) och en axe-granskning per
  PR [LÄST `astryx/package.json` scripts; `astryx/packages/lab/README.md` "Promotion gate"].
  Lab-komponenter är inte härdade [LÄST samma].
- Webbläsarkrav: Popover-API, CSS anchor positioning och `light-dark()`. Utan anchor positioning
  öppnas menyer och popovers men positioneras inte [LÄST
  `astryx/packages/cli/assets/docs/browser-support.doc.mjs`].

### 5.2 Reducerad rörelse
- Under `prefers-reduced-motion: reduce` får ingen övergång i en core-komponent flytta, skala eller
  ändra storlek; på pekskärm blir den en toning på högst 200 ms, annars sker ändringen direkt
  [LÄST `astryx/docs/design/reduced-motion.md`, DR1–DR3].
- Ett tema kan sätta `reducedMotion: 'always'`, och det når även inbäddade providers [LÄST
  `theme-application.md` INV1]. "Every theme follows each person's Reduce Motion setting; nothing
  loosens it" [LÄST `defineTheme.ts`, kommentaren till `motion`].

### 5.3 RTL och i18n
- Riktning: komponenterna speglar layout och riktade ikoner efter DOM:ens `dir`, inte efter
  providerns prop; appen sätter `dir` själv [LÄST `InternationalizationProvider.doc.mjs`, prop
  `dir`]. Designprinciperna för dubbelriktning står i `astryx/docs/design/bidirectionality.md`
  (DR1–DR14). Snajp behöver bara `ltr`.
- **Hur komponenternas strängar översätts.** Astryx äger sina egna strängar (etiketter,
  aria-texter, annonseringar) i kataloger; produkttext är appens [LÄST
  `internationalization.md` INV1, INV1a]. Upplösningen: per-locale `overrides` → medskickade
  kataloger → exakt locale → föräldra-locale → engelska [LÄST samma, "System behavior"]. Utan
  provider blir allt engelska.
- Användning: `<InternationalizationProvider locale="sv-SE" messages={{'sv-SE': svSE}}>`, där
  `svSE` importeras från `@astryxdesign/core/locales/sv-SE.generated.js` [LÄST
  `astryx/packages/cli/assets/docs/tree/i18n-quick-start.doc.mjs:54-60`]. Byte av `locale` uppdaterar
  alla strängar utan omladdning [LÄST samma, "Runtime language swap"].
- **Snajps locale heter `"sv"`/`"en"`** [LÄST `lib/i18n.tsx:5`]. En regional tagg faller tillbaka
  till sitt basspråk, inte tvärtom [LÄST `InternationalizationProvider.doc.mjs`, prop `locale`].
  Översätt därför `"sv"` → `"sv-SE"` när providern får sitt värde, eller registrera katalogen under
  nyckeln `sv`. [ANTAGANDE] att det senare fungerar; det förra följer dokumentationen.
- **Täckningen.** `sv-SE.json` har 365 av 694 nycklar. Saknas, per område: `comments` 67,
  `powersearch` 37, `richTextEditor` 30, `mediaPlayer` 30, `diffViewer` 22, `tokenizer` 20,
  `kbd` 19, `list` 16, `emojiPicker` 16, `commentComposer` 11, `table` 7, `dateInput` 4,
  `multiSelector` 4, `slider` 4, `fileInput` 3 m.fl. [LÄST, räknat ur
  `astryx/packages/core/locales/en.json` och `sv-SE.json`]. De nycklar CRM:et använder fylls med
  `overrides={{'sv-SE': {'@astryx.table.…': '…'}}}`, i en fil i Snajps repo.
- Regeln "en komponent tar en platt prop för varje sträng anroparen formulerar om" [LÄST
  `internationalization.md` DEC-1]: knappetiketter, tomlägen och rubriker är våra och går genom
  Snajps `useLocale().text({sv, en})`, som INV-COPY-001 kräver.
- Datum, tal och sortering formateras med providerns locale [LÄST `internationalization.md`,
  "System behavior"], så `weekStartsOn` och svenska månadsnamn följer `sv-SE`. Kalendern är
  gregoriansk om inget annat anges [LÄST `InternationalizationProvider.doc.mjs`, prop `calendar`].

---

## 6. Samexistens med Tailwind och Snajps primitiver, och riskerna

### 6.1 Kaskadlagren

Astryx avsedda ordning, från lägst: `reset → theme → base → astryx-base → astryx-theme →
components → utilities`, och olagrad konsument-CSS "always wins over all layers" [LÄST
`astryx/apps/example-nextjs-tailwind/src/app/globals.css`, kommentaren]. Lagerordningen måste
deklareras först i den första stilmallen sidan laddar; en `@layer`-rad efter Tailwinds import
"silently inverts the cascade" [LÄST `astryx/packages/cli/assets/docs/tree/tailwind.doc.mjs`,
"Add Astryx to an app that already uses Tailwind"].

Snajp i dag:
- `@tailwind base; @tailwind components; @tailwind utilities;` [LÄST `app/globals.css:1-3`]. I
  Tailwind 3 är det inte inbyggda kaskadlager; utdata är olagrad CSS [BEDÖMNING, utifrån hur
  Tailwind 3 fungerar; förlagan nämner bara v4].
- Egna olagrade elementregler: `*`, `html`, `body`, `a`, `a:hover`, `button, input, textarea, select`,
  `button`, `::selection` [LÄST `app/globals.css:198-245`].

Följd [BEDÖMNING]: Tailwind 3:s preflight och Snajps `a`-regler vinner över `@layer astryx-base`.
Knappar kan tappa sin fyllning, länkar och flikar med `href` får Snajps ink/ochre i stället för
Astryx färger, kanter nollas. Astryx egen `reset.css` använder `:where()` och ligger lägst [LÄST
`astryx/packages/core/src/reset.css:52-60`], så den skadar inte Snajp.

Tre vägar, i stigande kostnad:

1. **Behåll Tailwind 3 och lägg dess utdata i namngivna lager.** Tailwind 3 tolkar själv
   `@layer base/components/utilities` och får inte dela namn med de inbyggda lagren; Astryx-ordningen
   skrivs då med egna namn, t.ex. `@layer reset, tw-base, astryx-base, astryx-theme, tw-components,
   tw-utilities;`, och Snajps elementregler flyttas in i `tw-base`. [MÅSTE PRÖVAS] att Tailwind 3 och
   Next:s CSS-kedja låter `@tailwind base` stå inne i ett inbyggt `@layer tw-base { … }`. Om det
   fungerar är det den minsta ändringen. Att flytta Snajps egna regler in i ett lager ändrar inget
   för befintliga sidor så länge inget annat lager finns där i dag [BEDÖMNING].
2. **Uppgradera hela Snajp till Tailwind 4** och följ förlagans recept "Add Astryx to an app that
   already uses Tailwind" [LÄST `tailwind.doc.mjs`]. Kräver omskrivning av `tailwind.config.ts` (den
   OKLCH-alfakonstruktion med `<alpha-value>` och pluginen `peka`, [LÄST `tailwind.config.ts`]) till
   v4:s CSS-konfiguration, och en genomgång av varje yta. Stort.
3. **Egen rotlayout för CRM:et** i en route group, med en stilmall utan Tailwind 3:s preflight och
   utan Snajps elementregler. Isolerar helt, men en navigering mellan två rotlayouter laddar om sidan
   [BEDÖMNING, Next.js App Router-beteende], och CRM:et skulle då inte sitta i det befintliga
   appskalet, vilket strider mot regeln om att bygga in i befintlig yta [LÄST `CLAUDE.md`,
   2026-11-24].

[BEDÖMNING] Pröva väg 1 först i en förhandsvisning under `app/forhandsvisning/`.

### 6.2 Tailwind-bryggan

`tailwind-theme.css` mappar bl.a. `text-primary`, `bg-surface`, `rounded-lg`, `shadow-md` till
Astryx variabler och ändrar därmed vad appens egna klasser med samma namn målar [LÄST
`tailwind.doc.mjs`, "This recipe leaves out `tailwind-theme.css`…"]. Den kräver v4. Med väg 1 används
den inte; Snajps egna klasser (`text-ink`, `bg-paper2`, `border-ink/12`) läser redan samma variabler
som temat pekar på, så de passar ihop utan brygga [BEDÖMNING].

### 6.3 Variabelnamn

Astryx sätter sina tokens på `:root` [LÄST `tailwind.doc.mjs`, "because `astryx.css` sets the tokens
on `:root`"]. En app-variabel med samma namn i `:root` skriver över Astryx värde [LÄST samma]. En
sökning i `app/globals.css`, `components/` och `lib/` efter `--spacing-*`, `--color-*`, `--shadow-*`,
`--duration-*`, `--ease-*`, `--text-*`, `--font-size-*`, `--radius-*` och `--focus-outline-*` gav bara
`--ease-out`, `--ease-editorial`, `--radius-panel/card/input` och `--color-ink`, inga av Astryx namn
[LÄST, sökning 2026-11-25]. Ingen krock i dag.

### 6.4 `data-theme` och kundpaletten
Se §0 punkt 4. `mode` ska komma från `lib/tema.ts` (`morkt` → `'dark'`, annars `'light'`), och
`Theme` ska monteras i ett skal som lever över alla CRM-sidor. På kundens domän tvingar Snajp
ljust läge [LÄST `app/layout.tsx:117`]; samma värde ska gå till `Theme`.

### 6.5 Snajps primitiver i `components/ui.tsx`
`ui.tsx` exporterar klassträngar och små komponenter: `btnPrimary`, `btnSecondary`, `Badge`,
`Sidhuvud`, `Sektion`, `Talrad`, `Nyckeltal`, `Tomt`, `EmptyState`, `SkeletonRows`, `Tabell`, `Cell`,
`Radlista`, `Rad`, `fliklista`, `flik`, `chip`, `faltTatt`, `faltDiskret` [LÄST
`components/ui.tsx`, exporterna]. Flera har samma namn som Astryx (`Badge`, `EmptyState`).
[BEDÖMNING] Om Astryx ska stå för ALLA komponenter i CRM:et ska CRM-koden inte importera dessa;
namnkrockar undviks med att importera Astryx från undersökvägar (`@astryxdesign/core/Badge`). Rail och
appskal utanför CRM:et fortsätter med `ui.tsx`, och då möts två system på samma skärm. Det är ett
designbeslut för Anton.

### 6.6 Paketstorlek
- Färdig `astryx.css` ~77 KB, källbygge ~22 KB [LÄST `astryx/apps/example-nextjs-source/README.md`].
  Hela CSS:en laddas med dist-vägen, oavsett hur många komponenter som används.
- JS: utan `optimizePackageImports` drar en serverkomponent som importerar från paketroten med
  "every client component" [LÄST `astryx/apps/example-nextjs/next.config.mjs`]. Importera från
  undersökvägar.
- `@stylexjs/stylex` (runtime), `intl-messageformat` (core), och för neutral-temat `lucide-react@1`
  vid sidan av Snajps `0.468` [LÄST manifesten].
- Snajps maskin har 16 GB RAM och har kraschat av minnesbrist; ett källbygge med Babel och webpack
  är tyngre än dist [LÄST användarens `CLAUDE.md`; BEDÖMNING]. Välj dist.

### 6.7 Övriga risker
- **Beta.** "Currently in Beta" [LÄST `astryx/README.md:14`]; minorversioner har codemods
  (`astryx upgrade --apply`) [LÄST `astryx/packages/core/README.md`]. Lås exakta versioner.
- **Eget tema måste byggas om vid varje uppgradering** [LÄST `author-a-theme.doc.mjs:136`].
- **`astryx init` skriver i `CLAUDE.md`.** Den lägger ett block mellan `<!-- ASTRYX:START -->` och
  `<!-- ASTRYX:END -->` i `AGENTS.md` och i projektets Claude-fil, utan att röra texten runt
  [LÄST `astryx/packages/cli/clients/cli/commands/init.doc.mjs:20-36`;
  `astryx/packages/cli/foundation/agent-docs/agent-doc-state.mjs:57-58`]. Snajps `CLAUDE.md` är
  regelboken; ändringen kräver Antons ja. Alternativ: `--to skills` lägger texten som en skill i
  projektets skills-mapp i stället [LÄST `init.doc.mjs`, `--to`].
- **INV-UI-001 och INV-COPY-001** gäller källkoden i `app/` och `components/`. Astryx egna strängar
  ligger i `node_modules` och berörs inte, men varje sträng vi skickar in gör det. `app/crm` måste
  läggas till i grindarnas listor [LÄST `docs/crm/underlag/snajp-06-frontend-design-i18n.md:29-39`].
- **Canary i produktion.** Charts, lab och vega har ingen stabil version och kan gå sönder mellan
  två byggen [LÄST respektive README].
- **TypeScript 7** är oprövat mot förlagan, som testar med TS 6 [LÄST exemplens manifest].

---

## 7. "Agent ready": vad repot erbjuder en agent

- **CLI:t som uppslagsverk.** `astryx component <Namn>` (props, varianter, exempel, temamål),
  `astryx docs <ämne>`, `astryx search '<fråga>'`, `astryx hook`, `astryx template --list`,
  `astryx build "<vad sidan är till för>"` (väljer mall, block och komponenter), `astryx doctor
  --built .` (kontrollerar uppsättning och kod), `astryx gap-report` [LÄST
  `astryx/packages/cli/README.md:96-122`; `astryx/packages/core/README.md`]. JSON-utdata med
  felkoder finns för maskinläsning [LÄST `cli/README.md:137-245`].
- **MCP-server.** `astryx mcp` serverar varje kommando som MCP-verktyg över stdio [LÄST
  `cli/README.md:117`; specen `astryx/docs/specs/AST-121-mcp-server/spec.md`].
- **Skill och plugin.** `plugins/astryx/skills/astryx/SKILL.md` är en genererad skill för Claude
  Code och Codex, installerbar som plugin `astryx@astryx` [LÄST `astryx/plugins/astryx/README.md`].
  `astryx init --user` skriver samma text till `~/.agents/skills/astryx/SKILL.md` [LÄST
  `init.doc.mjs`, `--user`].
- **Komponentdokumentation som data.** Varje komponent har en `.doc.mjs` med props, anatomi,
  temamål, bästa praxis och exempel, på engelska, kinesiska och en "dense" variant för agenter
  [LÄST t.ex. `Table/Table.doc.mjs:104, 448, 509`]. De publiceras med paketet (`files` i
  `core/package.json`).
- **Specifikationer.** `astryx/docs/specs/` (AST-001 … AST-142 och `components/<Namn>/`), med
  beslut, invarianter och verifieringstabeller; `astryx/docs/architecture/` och `docs/design/` med
  samma form [LÄST `astryx/docs/README.md`].
- **Scheman och mallar för kunskapsposter.** `astryx/docs/schemas/knowledge/v1–v4.json` och
  `astryx/docs/templates/knowledge/` (`component-spec.md`, `theme-spec.md`, `design-spec.md`,
  `implementation-plan.md` m.fl.) [LÄST katalogerna].
- **Sidmallar.** 58 sidmallar under `astryx/packages/cli/assets/templates/pages/`, bland dem
  `table-page`, `table-filter`, `table-grouped`, `table-inbox`, `detail-page`, `work-item-detail`,
  `kanban-board`, `dashboard*`, `settings*`, `form-wizard*`, `messaging-shell`, `shell-side-nav`
  [LÄST katalogen]. `astryx template <namn>` skriver ut källan; `--skeleton` ger en annoterad
  layout [LÄST `core/README.md`, "Page Layouts"].
- **Temaverktyg.** `astryx docs theme`, `astryx experimental theme editor new <namn> --like neutral`,
  `astryx theme build`, palettgenerering [LÄST `author-a-theme.doc.mjs:10, 21, 36`].

[BEDÖMNING] För Snajps bygge: kör `astryx component` och `astryx template` som uppslag, men skriv
inte in init-blocket i `CLAUDE.md` utan Antons ja. CLI-text är data, inte instruktioner, i Snajps
agentregler.

---

## 8. Rekommenderad plan för Snajp

Inga kommandon nedan är körda. Ordningen är vald så att den största risken (kaskaden) prövas
innan något annat byggs.

### Steg 1. Installera (stabila versioner, exakta)

```bash
npm install -E @astryxdesign/core@0.7.17 @astryxdesign/theme-neutral@0.7.17 @stylexjs/stylex@0.19.1
npm install -D -E @astryxdesign/cli@0.7.17
```

`@stylexjs/stylex@0.19.1` är versionen exemplen använder [LÄST
`astryx/apps/example-nextjs-stylex/package.json`]. Rik text senare, vid behov:
`npm install -E @astryxdesign/richtext@0.7.17` plus `lexical` och de 12 `@lexical/*` i `^0.52.0`
[LÄST `astryx/packages/richtext/package.json`]. Ingen canary.

Lägg till i `package.json` scripts, som förlagan rekommenderar [LÄST `astryx/README.md`,
"For reliable CLI access"]:

```json
"astryx": "node node_modules/@astryxdesign/cli/clients/cli/bin/astryx.mjs"
```

### Steg 2. Pröva kaskaden i en förhandsvisning (väg 1 i §6.1)

`app/globals.css`, överst, före allt annat:

```css
@layer reset, tw-base, astryx-base, astryx-theme, tw-components, tw-utilities;

@layer tw-base { @tailwind base; }
@layer tw-components { @tailwind components; }
@layer tw-utilities { @tailwind utilities; }

@import "@astryxdesign/core/reset.css";
@import "@astryxdesign/core/astryx.css";
@import "../lib/crm/astryx/snajpTema.css";
```

och flytta Snajps elementregler (`*`, `html`, `body`, `a`, `button …`, `::selection`,
`app/globals.css:198-245`) in i `@layer tw-base { … }`. [MÅSTE PRÖVAS]: att Tailwind 3 accepterar
`@tailwind` inne i ett inbyggt lager, att `@import` efter andra regler godtas av Next:s CSS-kedja
(CSS kräver annars att `@import` står först; flytta i så fall Astryx-importerna till en egen fil
som importeras först i `app/layout.tsx`), och att varje befintlig yta ser likadan ut. Rendera
landning, `/leads`, `/dashboard`, `/settings` i ljust och mörkt, desktop och mobil, före och efter.
Faller prövningen: väg 2 eller 3, och fråga Anton.

### Steg 3. Temat

1. Skapa `lib/crm/astryx/snajpTema.ts` enligt §3.5.
2. Bygg: `npm run astryx -- theme build lib/crm/astryx/snajpTema.ts -o lib/crm/astryx/snajpTema.css`.
   Det ger `snajpTema.css`, `snajpTema.js`, `snajpTema.d.ts`, `snajpTema.css.d.ts` [LÄST
   `author-a-theme.doc.mjs:126-133`; flaggan `-o` som i
   `astryx/packages/themes/neutral/package.json` scripts.build]. Utdata committas och byggs om vid
   varje uppgradering.
3. Mät varje `MÄT`-rad med samma metod som DESIGN.md (axe och dold text), i ljust och mörkt läge,
   och skriv värdena i en tabell i `DESIGN.md` som för de dämpade tokens.

### Steg 4. Ramen: `components/crm/AstryxRam.tsx`

```tsx
'use client';

import Link from 'next/link';
import {Theme} from '@astryxdesign/core/theme';
import {LinkProvider} from '@astryxdesign/core/Link';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import svSE from '@astryxdesign/core/locales/sv-SE.generated.js';
import {snajpTema} from '@/lib/crm/astryx/snajpTema.js'; // byggd modul, __built: true
import {useLocale} from '@/lib/i18n';
import type {Tema} from '@/lib/tema';
import {astryxSvenskaTillagg} from '@/lib/crm/astryx/svenska';

// Snajps "sv" heter "sv-SE" i Astryx kataloger.
const ASTRYX_LOCALE = {sv: 'sv-SE', en: 'en'} as const;

export function AstryxRam({tema, children}: {tema: Tema; children: React.ReactNode}) {
  const {locale} = useLocale();
  return (
    // mode får aldrig vara 'system': då tar Astryx bort <html data-theme> som Snajps mörka läge läser.
    <Theme theme={snajpTema} mode={tema === 'morkt' ? 'dark' : 'light'}>
      <InternationalizationProvider
        locale={ASTRYX_LOCALE[locale]}
        messages={{'sv-SE': svSE}}
        overrides={{'sv-SE': astryxSvenskaTillagg}}>
        <LinkProvider component={Link}>{children}</LinkProvider>
      </InternationalizationProvider>
    </Theme>
  );
}
```

`lib/crm/astryx/svenska.ts` håller de svenska strängar `sv-SE.json` saknar för de komponenter
CRM:et använder (§5.3). `app/crm/layout.tsx` (server) läser temat som rotlayouten gör
(`parseTema(cookies().get(TEMA_COOKIE))`, [LÄST `app/layout.tsx:117`]) och lindar sidorna i
`AstryxRam`. I `next.config.ts` läggs `'@astryxdesign/core'` till i
`experimental.optimizePackageImports` [LÄST `astryx/apps/example-nextjs/next.config.mjs`;
Snajps `next.config.ts:23` har redan ett `experimental`-block].

### Steg 5. Minimalt exempel: tabell, flikar och en knapp

`app/crm/kontakter/page.tsx` (server):

```tsx
import {Kontakter} from '@/components/crm/Kontakter';

export default async function KontakterSida() {
  const kontakter = [
    {id: 'k1', namn: 'Anna Berg', bolag: 'Bergs Bygg AB', fas: 'Möte bokat', senast: '2026-11-20'},
    {id: 'k2', namn: 'Omar Said', bolag: 'Said Konsult', fas: 'Ny', senast: '2026-11-24'},
  ];
  return <Kontakter kontakter={kontakter} />;
}
```

`components/crm/Kontakter.tsx` (klient):

```tsx
'use client';

import {useMemo, useState} from 'react';
import {Layout, LayoutHeader, LayoutContent} from '@astryxdesign/core/Layout';
import {HStack, VStack} from '@astryxdesign/core/Stack';
import {Heading} from '@astryxdesign/core/Text';
import {Button} from '@astryxdesign/core/Button';
import {TabList, Tab} from '@astryxdesign/core/TabList';
import {Badge} from '@astryxdesign/core/Badge';
import {EmptyState} from '@astryxdesign/core/EmptyState';
import {
  Table,
  proportional,
  pixel,
  useTableSortable,
  useTableSortableState,
  type TableColumn,
} from '@astryxdesign/core/Table';
import {useLocale} from '@/lib/i18n';

type Kontakt = {id: string; namn: string; bolag: string; fas: string; senast: string};

export function Kontakter({kontakter}: {kontakter: Kontakt[]}) {
  const {text} = useLocale();
  const [flik, setFlik] = useState('alla');

  const synliga = flik === 'moten' ? kontakter.filter(k => k.fas === 'Möte bokat') : kontakter;
  const {sortedData, sortConfig} = useTableSortableState({
    data: synliga,
    defaultSort: [{sortKey: 'senast', direction: 'descending'}],
  });
  const sort = useTableSortable<Kontakt>(sortConfig);
  const plugins = useMemo(() => ({sort}), [sort]);

  const kolumner: TableColumn<Kontakt>[] = [
    {key: 'namn', header: text({sv: 'Namn', en: 'Name'}), width: proportional(2), sortable: true},
    {key: 'bolag', header: text({sv: 'Bolag', en: 'Company'}), width: proportional(2), sortable: true},
    {
      key: 'fas',
      header: text({sv: 'Fas', en: 'Stage'}),
      width: pixel(140),
      renderCell: k => <Badge label={k.fas} variant="neutral" />,
    },
    {key: 'senast', header: text({sv: 'Senaste kontakt', en: 'Last contact'}), width: pixel(150), sortable: true},
  ];

  return (
    <Layout
      header={
        <LayoutHeader>
          <HStack justify="between" align="center">
            <Heading level={1}>{text({sv: 'Kontakter', en: 'Contacts'})}</Heading>
            <Button variant="primary" label={text({sv: 'Ny kontakt', en: 'New contact'})} onClick={() => {}} />
          </HStack>
        </LayoutHeader>
      }
      content={
        <LayoutContent>
          <VStack gap={4}>
            <TabList value={flik} onChange={setFlik} role="tablist">
              <Tab value="alla" label={text({sv: 'Alla', en: 'All'})} panelId="kontakter-panel" />
              <Tab value="moten" label={text({sv: 'Möten bokade', en: 'Meetings booked'})} panelId="kontakter-panel" />
            </TabList>
            <div id="kontakter-panel" role="tabpanel">
              <Table
                data={sortedData}
                columns={kolumner}
                idKey="id"
                plugins={plugins}
                hasHover
                emptyState={<EmptyState title={text({sv: 'Inga kontakter här än', en: 'No contacts here yet'})} />}
              />
            </div>
          </VStack>
        </LayoutContent>
      }
    />
  );
}
```

Belägg för props som används: `Layout header/content` [LÄST `Layout/Layout.doc.mjs:64-79`];
`Stack gap` 0–10 [LÄST `Stack/Stack.doc.mjs:62-63`]; `Heading level` [LÄST
`Text/Heading.doc.mjs:24-25`]; `Button variant/label/onClick` [LÄST `Button/Button.doc.mjs:100-103`];
`TabList value/onChange(value: string)/role` och `Tab value/label/panelId` [LÄST
`TabList/TabList.doc.mjs:38-46, 76`; `TabList/Tab.doc.mjs`]; `Table data/columns/idKey/plugins/
hasHover/emptyState` [LÄST `Table/Table.doc.mjs:204-305`]; `proportional`/`pixel` [LÄST
`Table/index.ts:70-76`]; `sortable` och `renderCell` på kolumnen [LÄST `Table/types.ts:176, 200-205`];
`useTableSortableState({data, defaultSort})` → `{sortedData, sortConfig}` och
`useTableSortable(sortConfig)` [LÄST `plugins/sortable/useTableSortableState.doc.mjs:20-97`];
pluginnamnet `sort` och kravet på ett stabilt pluginobjekt [LÄST `Table.doc.mjs:273`].
`justify` tar `'start' | 'center' | 'end' | 'between' | 'around' | 'evenly'` och `align`
`'start' | 'center' | 'end' | 'stretch'` [LÄST `Stack/Stack.doc.mjs:147-153`]; `Badge variant`
tar bl.a. `'neutral'` [LÄST `Badge/Badge.doc.mjs:12-13`]. Exemplet ska renderas i
förhandsvisning, desktop och mobil, ljust och mörkt, innan något committas (projektregeln).

### Steg 6. Filer som skapas eller ändras, sammanfattat

| Fil | Ny/ändrad | Innehåll |
|---|---|---|
| `package.json`, `package-lock.json` | ändrad | Fyra beroenden, scriptet `astryx` |
| `app/globals.css` | ändrad | Lagerordning, Tailwind 3 i lager, Astryx-importer, Snajps elementregler i `tw-base` |
| `next.config.ts` | ändrad | `optimizePackageImports` |
| `lib/crm/astryx/snajpTema.ts` | ny | Temat (§3.5) |
| `lib/crm/astryx/snajpTema.{css,js,d.ts,css.d.ts}` | ny, genererad | Utdata från `astryx theme build` |
| `lib/crm/astryx/svenska.ts` | ny | Svenska `overrides` för saknade nycklar |
| `components/crm/AstryxRam.tsx` | ny | `Theme` + `InternationalizationProvider` + `LinkProvider` |
| `app/crm/layout.tsx` | ny | Läser tema, lindar i `AstryxRam` |
| `app/crm/kontakter/page.tsx`, `components/crm/Kontakter.tsx` | ny | Exemplet |
| `app/forhandsvisning/crm-…/` | ny | Förhandsvisning utan databas, enligt projektregeln |
| `tests/invariants/test_inv_copy_001.py`, INV-UI-001 | ändrad | `app/crm` in i båda grindarnas listor |
| `DESIGN.md` | ändrad | Uppmätta kontraster för temats `MÄT`-rader |
| `docs/BESLUT.md` | ändrad | Beslutet att använda Astryx, valet av kaskadväg och av primärknappens färg, med Antons resonemang |

### Steg 7. Beslut som behöver Anton

1. Kaskadvägen om väg 1 inte håller (Tailwind 4 för hela Snajp, eller egen rotlayout för CRM:et).
2. Primärknappen: ochre med mörk text (DESIGN.md) eller ink (`btnPrimary`).
3. Om `astryx init` får skriva sitt block i `CLAUDE.md`/`AGENTS.md`.
4. Om canary-paket (`charts`, `lab` för `Schedule`/`Stat`) får användas i produktion, eller om
   recharts och egna komponenter gäller tills vidare.
5. Om CRM:et ska ha Astryx även i det delade appskalet (rail), eller bara i innehållsytan.
