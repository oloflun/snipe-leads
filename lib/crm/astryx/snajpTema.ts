/**
 * Snajps tema för Astryx (designsystemet Snajp CRM byggs med).
 *
 * Varje färg pekar på Snajps egna OKLCH-variabler i app/globals.css. Kundens
 * palett (lib/tenants: paletteToCss) och mörkt läge (:root[data-theme="dark"])
 * följer därför med utan en rad här: byts tokens byts allt, samma regel som i
 * resten av appen. Astryx räknar inte ut status- och kontrastroller ur ett värde
 * som inte är en konkret färg, så varje roll sätts för hand och är uppmätt
 * (tabellen i DESIGN.md § App surfaces, Astryx-temat).
 *
 * Filen är KÄLLAN. Det appen laddar är utdata bredvid: snajp.css och snajp.js.
 * Bygg om efter varje ändring här och efter varje uppgradering av Astryx:
 *
 *   npm run astryx -- theme build lib/crm/astryx/snajpTema.ts
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
/** Ljus text i båda lägena, av samma skäl. */
const LJUS = `light-dark(${c("--paper")}, ${c("--ink")})`;

/**
 * Typsnitt och rubrikstorlekar. next/font ger variablerna (lib/fonts.ts), och
 * Fraunces bär bara rubriker. De står i en egen konstant för att de behövs två
 * gånger: neutral-temat, som det här ärver, räknar om HELA typografin på
 * pekskärm under 1024 px och skriver då tillbaka sitt eget typsnitt. Regeln för
 * pekskärm längre ner sätter därför tillbaka Snajps.
 */
const TYPOGRAFI = {
  "--font-family-body": "var(--font-sans)",
  "--font-family-heading": "var(--font-serif)",
  "--font-family-code": "var(--font-mono)",
  "--text-heading-1-size": "1.75rem",
  "--text-heading-1-weight": "400",
  "--text-heading-2-size": "1.5rem",
  "--text-heading-2-weight": "400",
  "--text-heading-3-size": "1.0625rem"
} as const;

export const colorModes = ["light", "dark"] as const;

export const snajpTema = defineTheme({
  name: "snajp",
  extends: neutralTheme,

  // Appytornas löptext är 0.9375rem (DESIGN.md § App surfaces).
  typography: { scale: { base: 15, ratio: 1.2 } },

  // Snajps två tider: 180 ms för små lägesbyten, 300 ms för paneler.
  motion: { fast: 180, medium: 300, ratio: 0.75 },

  adaptations: {
    rules: [
      {
        // Pekskärm: tryckytor på 44 px. Löptexten blir 16 px av neutral-temats
        // ärvda regel, så att iOS inte zoomar i fält.
        when: { pointer: "coarse" },
        value: {
          tokens: {
            ...TYPOGRAFI,
            "--size-element-sm": "36px",
            "--size-element-md": "44px",
            "--size-element-lg": "48px"
          }
        }
      }
    ]
  },

  tokens: {
    ...TYPOGRAFI,
    "--text-label-size": "0.8125rem",
    "--text-supporting-size": "0.8125rem",

    // Ockra är den enda accenten: det valda, fokus och förlopp.
    "--color-accent": c("--ochre"),
    "--color-accent-muted": c("--ochre", 0.14),
    "--color-on-accent": MORK,
    "--color-neutral": c("--ink", 0.07),
    "--color-overlay": c("--ink", 0.4),
    "--color-overlay-hover": c("--ink", 0.05),
    "--color-overlay-pressed": c("--ink", 0.1),
    "--color-tint-hover": c("--ink", 0.04),

    // Ytor. Papper, aldrig vitt; det upphöjda planet alltid med hårlinje.
    "--color-background-body": c("--paper"),
    "--color-background-surface": c("--paper"),
    "--color-background-card": c("--paper"),
    "--color-background-popover": c("--paper"),
    "--color-background-muted": c("--paper2"),
    "--color-background-inverted": c("--ink"),
    "--color-background-error-inverted": c("--danger"),

    // Text. Dämpad text är alltid en token, aldrig opacitet.
    "--color-text-primary": c("--ink"),
    "--color-text-secondary": c("--ink-muted"),
    "--color-text-disabled": c("--mineral"),
    "--color-text-accent": c("--warning"),
    "--color-on-dark": LJUS,
    "--color-on-light": MORK,

    // Ikoner. Ockra klarar inte 3:1 mot papper, den textsäkra varianten gör det.
    "--color-icon-primary": c("--ink"),
    "--color-icon-secondary": c("--ink-muted"),
    "--color-icon-disabled": c("--mineral"),
    "--color-icon-accent": c("--warning"),

    // Hårlinjen är ink/12 som i panelKort (components/ui.tsx). Fältens kant är
    // den betonade linjen, ett steg starkare än faltTatt (ink/15). Astryx 0.7.17
    // har ingen egen roll för fältkanter; den kommer i 0.7.18 (--color-border-control).
    "--color-border": c("--ink", 0.12),
    "--color-border-emphasized": c("--ink", 0.25),

    "--color-skeleton": c("--ink", 0.08),
    "--color-track": c("--ink", 0.15),
    "--color-shadow": c("--ink", 0.12),

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

    // Kategorifärgerna som Badge och Token läser. Bara de CRM:et använder; resten ärvs.
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
    "--color-background-blue": c("--seal", 0.12),
    "--color-border-blue": c("--seal"),
    "--color-icon-blue": c("--seal"),
    "--color-text-blue": c("--seal"),

    // Fokus: ockra, 2 px, 2 px avstånd, utan undantag (DESIGN.md § Accessibility floor).
    "--focus-outline-color": c("--focus"),
    "--focus-outline-width": "2px",
    "--focus-outline-offset": "2px",

    // Radier: fält 8, kort 12, panel 20 (samma som tailwind.config.ts).
    "--radius-inner": "4px",
    "--radius-element": "var(--radius-input)",
    "--radius-container": "var(--radius-card)",
    "--radius-page": "var(--radius-panel)",

    // Arbetsytan bär hårlinjer, inte skuggor. Det som flyter (meny, dialog) får
    // en hårlinje och en svag skugga i bläck.
    "--shadow-low": `0 0 0 1px ${c("--ink", 0.09)}`,
    "--shadow-med": `0 0 0 1px ${c("--ink", 0.09)}, 0 6px 20px ${c("--seal", 0.14)}`,
    "--shadow-high": `0 0 0 1px ${c("--ink", 0.09)}, 0 24px 70px ${c("--seal", 0.18)}`,
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
    }
  },

  // Innehåll på bläck: railen. Samma par som Snajps mörka rail har i dag
  // (paper-muted 7.29:1 och paper-subtle 4.97:1 mot ink; ockra 7.56:1).
  onDark: rail(c("--ochre")),
  // Samma rail i Snajps mörka läge, där bläcket är ljust. Rollerna pekar på
  // samma variabler och vänder sig själva; det enda som skiljer är det valda,
  // som inte kan vara ockra på en ljus yta (under 2:1) och därför är papperets
  // mörka ton på en platta.
  onLight: rail(c("--paper"))
});

/** Railens roller. `valt` är färgen på den valda menyposten. */
function rail(valt: string) {
  return {
    tokens: {
      "--color-background-body": c("--ink"),
      "--color-background-surface": c("--ink"),
      "--color-background-card": c("--ink"),
      "--color-background-muted": c("--ink2"),
      "--color-text-primary": c("--paper"),
      "--color-text-secondary": c("--paper-muted"),
      "--color-text-disabled": c("--paper-subtle"),
      "--color-text-accent": c("--ochre"),
      "--color-icon-primary": c("--paper"),
      "--color-icon-secondary": c("--paper-muted"),
      "--color-icon-disabled": c("--paper-subtle"),
      "--color-icon-accent": c("--ochre"),
      "--color-border": c("--paper", 0.14),
      "--color-border-emphasized": c("--paper", 0.28),
      "--color-neutral": c("--paper", 0.1),
      "--color-overlay-hover": c("--paper", 0.07),
      "--color-overlay-pressed": c("--paper", 0.12),
      "--color-tint-hover": c("--paper", 0.06),
      "--color-accent": c("--ochre"),
      "--color-accent-muted": c("--ochre", 0.18)
    },
    components: {
      // Astryx målar ingen egen bakgrund på sidnavigeringen: skalet gör det,
      // utanför den vända ytan. Bläcket sätts därför här.
      "side-nav": { base: { backgroundColor: c("--ink") } },
      // Det valda står på en svagt lyft platta.
      "side-nav-item": { selected: { color: valt, backgroundColor: c("--paper", 0.1) } }
    }
  };
}
