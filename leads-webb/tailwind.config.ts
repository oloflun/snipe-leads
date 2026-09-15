import type { Config } from "tailwindcss";

/**
 * Samma tokenuppsättning som huvudappens tailwind.config.ts — Snajp Bokföring
 * är en egen sajt men samma varumärke, och en avvikande palett här hade läst
 * som en annan firma. Ändras tokens görs det i DESIGN.md först.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "oklch(var(--ink) / <alpha-value>)",
        ink2: "oklch(var(--ink2) / <alpha-value>)",
        paper: "oklch(var(--paper) / <alpha-value>)",
        paper2: "oklch(var(--paper2) / <alpha-value>)",
        mineral: "oklch(var(--mineral) / <alpha-value>)",
        seal: "oklch(var(--seal) / <alpha-value>)",
        ochre: "oklch(var(--ochre) / <alpha-value>)",
        moss: "oklch(var(--moss) / <alpha-value>)",
        danger: "oklch(var(--danger) / <alpha-value>)",
        warning: "oklch(var(--warning) / <alpha-value>)"
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-geist)", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      borderRadius: {
        panel: "20px",
        card: "12px",
        input: "8px"
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)"
      },
      boxShadow: {
        hairline: "0 0 0 1px oklch(var(--ink) / 0.09)",
        lift: "0 24px 70px oklch(var(--ink) / 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
