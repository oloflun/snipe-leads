/**
 * Snajps tema för Astryx (designsystemet Snajp CRM byggs med).
 *
 * Varje färg pekar på Snajps egna OKLCH-variabler i app/globals.css. Kundens
 * palett (lib/tenants: paletteToCss) och mörkt läge (:root[data-theme="dark"])
 * följer därför med utan en rad här: byts tokens byts allt, samma regel som i
 * resten av appen. Astryx räknar inte ut status- och kontrastroller ur ett värde
 * som inte är en konkret färg, så varje roll sätts för hand och är uppmätt.
 *
 * Formen följer docs/crm/DESIGN-CRM.md § Tema (version 2, 2026-11-26): ljus
 * navigering på tvätten, innehållet som ett upphöjt blad, radier 6 / 10 / 16 / 24,
 * kontroller 32 / 36 / 44 och 14 px löptext. Den mörka railen är borta.
 *
 * Filen är KÄLLAN. Det appen laddar är utdata bredvid: snajp.css och snajp.js.
 * Bygg om efter varje ändring här och efter varje uppgradering av Astryx:
 *
 *   node node_modules/@astryxdesign/cli/clients/cli/bin/astryx.mjs theme build lib/crm/astryx/snajpTema.ts
 *
 * Underlag: docs/crm/underlag/astryx-designsystemet.md § 3.
 */
import { defineTheme } from "@astryxdesign/core/theme";
import { neutralTheme } from "@astryxdesign/theme-neutral";

/** En Snajp-token som färg, med eller utan alfa. */
const c = (namn: string, alfa?: number) =>
  alfa == null ? `oklch(var(${namn}))` : `oklch(var(${namn}) / ${alfa})`;

/** Mörk text i båda lägena: --ink är mörk i ljust läge, --paper i mörkt. */
const MORK = `light-dark(${c("--ink")}, ${c("--paper")})`;

/**
 * Tvätten och bladet (DESIGN-CRM.md § Tema). I ljust läge är tvätten --paper2
 * och bladet --paper. I mörkt läge är --paper2 den ljusare tonen, så paret byter
 * plats: bladet ska alltid vara ytan som ligger närmast läsaren, som i Astryx
 * egen mörka `elevated`.
 */
const TVATT = `light-dark(${c("--paper2")}, ${c("--paper")})`;
const BLAD = `light-dark(${c("--paper")}, ${c("--paper2")})`;
/**
 * Diagrammens och objektens blå. --chart-blue klarar 4,5:1 som text mot ljust
 * papper; i mörkt läge bär det ljusare rampsteget texten.
 */
const BLA_TEXT = `light-dark(${c("--chart-blue")}, ${c("--chart-ramp-5")})`;

/** Mjuk, bred skugga i sigill, med låg alfa (kontraktet: 6 till 10 procent). */
const HARLINJE = `0 0 0 1px ${c("--ink", 0.08)}`;

/**
 * Typsnitt och rubrikstorlekar. next/font ger variablerna (lib/fonts.ts), och
 * Fraunces bär bara rubriker: sidrubriken (h1, 1,625 rem) och postens namn i
 * panelen (h2, 1,375 rem). De står i en egen konstant för att de behövs två
 * gånger: neutral-temat, som det här ärver, räknar om HELA typografin på
 * pekskärm under 1024 px och skriver då tillbaka sitt eget typsnitt. Regeln för
 * pekskärm längre ner sätter därför tillbaka Snajps.
 */
const TYPOGRAFI = {
  "--font-family-body": "var(--font-sans)",
  "--font-family-heading": "var(--font-serif)",
  "--font-family-code": "var(--font-mono)",
  "--text-heading-1-size": "1.625rem",
  "--text-heading-1-weight": "400",
  "--text-heading-2-size": "1.375rem",
  "--text-heading-2-weight": "400",
  "--text-heading-3-size": "1.0625rem",
  "--text-label-size": "0.8125rem",
  "--text-supporting-size": "0.8125rem"
} as const;

export const colorModes = ["light", "dark"] as const;

export const snajpTema = defineTheme({
  name: "snajp",
  extends: neutralTheme,

  // CRM:ets löptext är 14 px på skrivbord (DESIGN-CRM.md § Tema). Pekskärm under
  // 1024 px får 16 px av neutral-temats ärvda regel, så att iOS inte zoomar i fält.
  typography: { scale: { base: 14, ratio: 1.2 } },

  // Snajps två tider: 180 ms för små lägesbyten, 300 ms för paneler.
  motion: { fast: 180, medium: 300, ratio: 0.75 },

  adaptations: {
    rules: [
      {
        // Pekskärm: kontrollerna 44 / 44 / 48 px. Även de små (menyns ⋯, Visa fler,
        // ikonknappar i huvudet) når 44 px, kontraktets tryckyta (DESIGN.md).
        when: { pointer: "coarse" },
        value: {
          tokens: {
            ...TYPOGRAFI,
            "--size-element-sm": "44px",
            "--size-element-md": "44px",
            "--size-element-lg": "48px"
          }
        }
      }
    ]
  },

  tokens: {
    ...TYPOGRAFI,

    // Kontroller: 32 / 36 / 44 px på skrivbord (Astryx större former).
    "--size-element-sm": "32px",
    "--size-element-md": "36px",
    "--size-element-lg": "44px",

    // Ockra är den enda accenten: det valda, fokus och förlopp.
    "--color-accent": c("--ochre"),
    "--color-accent-muted": c("--ochre", 0.14),
    "--color-on-accent": MORK,
    "--color-neutral": c("--ink", 0.07),
    "--color-overlay": c("--ink", 0.4),
    "--color-overlay-hover": c("--ink", 0.05),
    "--color-overlay-pressed": c("--ink", 0.1),
    "--color-tint-hover": c("--ink", 0.04),

    // Ytor. Tvätten bakom navigeringen, bladet för innehållet. Papper, aldrig vitt.
    "--color-background-body": TVATT,
    "--color-background-surface": BLAD,
    "--color-background-card": BLAD,
    "--color-background-popover": BLAD,
    "--color-background-muted": TVATT,
    "--color-background-inverted": c("--ink"),
    "--color-background-error-inverted": c("--danger"),

    // Text. Dämpad text är alltid en token, aldrig opacitet.
    "--color-text-primary": c("--ink"),
    "--color-text-secondary": c("--ink-muted"),
    "--color-text-disabled": c("--mineral"),
    "--color-text-accent": c("--warning"),

    // Ikoner. Ockra klarar inte 3:1 mot papper, den textsäkra varianten gör det.
    "--color-icon-primary": c("--ink"),
    "--color-icon-secondary": c("--ink-muted"),
    "--color-icon-disabled": c("--mineral"),
    "--color-icon-accent": c("--warning"),

    // Hårlinjerna ordnar men syns knappt (Twentys finish): ink/10 för kort och
    // tabeller. Den betonade linjen är fältens och kryssrutornas kant, det enda
    // som visar var kontrollen finns: den ska nå 3:1 mot både papper och tvätt
    // i båda lägena (WCAG 1.4.11). ink/0.22 mätte 1,46:1.
    "--color-border": c("--ink", 0.1),
    "--color-border-emphasized": c("--ink", 0.52),

    "--color-skeleton": c("--ink", 0.08),
    "--color-track": c("--ink", 0.1),
    "--color-shadow": c("--seal", 0.1),

    // Status. Mossa för klart, fara för fel, den textsäkra ockran för varning.
    "--color-success": c("--moss"),
    "--color-on-success": c("--paper"),
    "--color-success-muted": c("--moss", 0.14),
    "--color-on-success-muted": c("--moss"),
    "--color-text-success": c("--moss"),
    "--color-error": c("--danger"),
    "--color-on-error": c("--paper"),
    // 0.07, inte 0.12: fara som text mot en 12-procentig platta mätte 4.36:1.
    "--color-error-muted": c("--danger", 0.07),
    "--color-on-error-muted": c("--danger"),
    "--color-text-error": c("--danger"),
    "--color-warning": c("--ochre"),
    "--color-on-warning": MORK,
    "--color-warning-muted": c("--ochre", 0.12),
    "--color-on-warning-muted": c("--warning"),
    "--color-text-warning": c("--warning"),
    "--color-info": c("--seal"),
    "--color-on-info": c("--paper"),
    "--color-info-muted": c("--seal", 0.12),
    "--color-on-info-muted": c("--seal"),
    "--color-text-info": c("--seal"),

    // Kategorifärgerna som Badge, Token, Card och Icon läser. Blått är Bolags
    // objektfärg (--chart-blue), inte sigillet.
    "--color-background-gray": c("--ink", 0.07),
    "--color-border-gray": c("--mineral"),
    "--color-icon-gray": c("--ink-muted"),
    "--color-text-gray": c("--ink"),
    "--color-background-green": c("--moss", 0.14),
    "--color-border-green": c("--moss"),
    "--color-icon-green": c("--moss"),
    "--color-text-green": c("--moss"),
    "--color-background-red": c("--danger", 0.07),
    "--color-border-red": c("--danger"),
    "--color-icon-red": c("--danger"),
    "--color-text-red": c("--danger"),
    "--color-background-yellow": c("--ochre", 0.14),
    "--color-border-yellow": c("--ochre"),
    "--color-icon-yellow": c("--warning"),
    "--color-text-yellow": c("--warning"),
    "--color-background-blue": c("--chart-blue", 0.14),
    "--color-border-blue": c("--chart-blue"),
    "--color-icon-blue": BLA_TEXT,
    "--color-text-blue": BLA_TEXT,

    // Fokus: ockra, 2 px, 2 px avstånd, utan undantag (DESIGN.md § Accessibility floor).
    // I ljust läge ger --focus bara 2,16:1 mot papper; den textsäkra ockran
    // (--warning, 5,6:1) är samma kulör. Mörkt läge behåller --focus (9,6:1).
    "--focus-outline-color": `light-dark(${c("--warning")}, ${c("--focus")})`,
    "--focus-outline-width": "2px",
    "--focus-outline-offset": "2px",

    // Radier (Astryx, större än arbetsytans): inre 6, element 10, behållare 16, sida 24.
    "--radius-inner": "6px",
    "--radius-element": "10px",
    "--radius-container": "16px",
    "--radius-page": "24px",

    // Låg = en hårlinje. Med och hög = hårlinje plus en mjuk, bred skugga i
    // sigill, för det som svävar: kort i rörelse, menyer, paneler och dialoger.
    "--shadow-low": HARLINJE,
    "--shadow-med": `${HARLINJE}, 0 8px 24px ${c("--seal", 0.08)}`,
    "--shadow-high": `${HARLINJE}, 0 24px 64px ${c("--seal", 0.1)}`,
    "--shadow-inset-hover": `inset 0 0 0 2px ${c("--ink", 0.12)}`,
    "--shadow-inset-selected": `inset 0 0 0 2px ${c("--ochre", 0.55)}`,
    "--shadow-inset-error": `inset 0 0 0 2px ${c("--danger", 0.45)}`,
    "--shadow-inset-success": `inset 0 0 0 2px ${c("--moss", 0.45)}`,
    "--shadow-inset-warning": `inset 0 0 0 2px ${c("--ochre", 0.55)}`,

    // Snajps enda kurva.
    "--ease-standard": "var(--ease-out)",
    "--ease-entrance": "var(--ease-out)",
    "--ease-move": "var(--ease-out)"
  },

  components: {
    button: {
      // Primärknappen är bläck, som i dagens arbetsyta (btnPrimary i
      // components/ui.tsx). Ockran sparas åt det valda och åt fokus.
      "variant:primary": { backgroundColor: c("--ink"), color: c("--paper") }
    },
    // Navigeringen ligger på tvätten. Bredden 248 px sätts i
    // components/crm/app/crm.css, bara för utfällt läge.
    "side-nav": { base: { backgroundColor: TVATT } },
    // Vald menypost: en mjuk platta i bläck, texten i bläck och halvfet.
    "side-nav-item": {
      base: { color: c("--ink2") },
      selected: { color: c("--ink"), backgroundColor: c("--ink", 0.07), fontWeight: "600" }
    }
  }
});
